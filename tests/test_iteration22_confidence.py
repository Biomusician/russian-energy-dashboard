"""Iteration 22: Evidence Confidence v2 (pipeline/evidence_confidence.py), hardened.

The model answers three separate questions (docs/GLOBAL_IMPACT_METHODOLOGY.md §8): did it happen
and is the reported effect supported; how strong is the evidence about who did it; does a source
tie AI to this incident. The properties here are the ones a reader relies on without knowing it:
that a pile of links is not corroboration, that an official statement is not marked down for
standing alone, that a claim of responsibility is only a claim, and that "nobody knows who" is not
a low score.

Random cases use a seeded generator, so a failure is reproducible and the suite is deterministic.

Also here: evidence confidence as served on country records (job A), and the pin that keeps all of
it out of the theatre's scoring multiplier.
"""
import copy
import hashlib
import inspect
import json
import random
import subprocess
import sys
from pathlib import Path

import pytest

from pipeline import build_index, build_systems as B, evidence_confidence as EC, fetch_wikipedia, systems

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web" / "public" / "data"
RANK = {"PRELIMINARY": 0, "LIMITED": 1, "MODERATE": 2, "HIGH": 3}
EVENT = "2024-03-01"


def src(role="media", site="daily.example", publisher=None, date="2024-03-02", opened=True, path="a", **kw):
    s = {"url": f"https://{site}/{path}", "publisher": publisher or site, "date": date, "language": "en",
         "source_role": role, "medium": "web", "opened": opened}
    s.update(kw)
    return s


def post(tier, role="operator", handle="gridco", publisher="GridCo", identity="listed on the operator's own website", **kw):
    social = {"platform": "x", "handle": handle, "display_name": publisher, "account_tier": tier}
    if identity:
        social["identity_basis"] = identity
    return src(role, site="x.com", publisher=publisher, path=f"{handle}/status/1", medium="social", social=social, **kw)


def wire_copy(i, wire="Reuters"):
    return src("media", site=f"outlet{i}.example", publisher=f"{wire} via Outlet {i}")


# A review block that says the source-and-attribution reviewer checked which sources relay which:
# the only state in which the origin count is a count of independent statements and High is open.
# The tests of the points use it; what happens without it has tests of its own
# (tests/test_iteration22_redteam.py).
REVIEWED = {"roles": {"evidence": "accept", "attribution_source": "accept", "safety": "accept"}}


def assess(sources, specificity="described", dispute=None, date=EVENT, date_end=None, review=REVIEWED):
    return EC.assess(sources, date, date_end, specificity, dispute, review=review)


# --- a seeded generator of source sets -----------------------------------------------------------------

ROLES = sorted(EC.METHOD["role_tier"]) + ["unheard_of_role"]
SITES = ["gridco.example", "ministry.example", "daily.example", "herald.example", "tradepress.example",
         "en.wikipedia.org", "feeds.example"]
PUBLISHERS = ["GridCo", "Ministry of Energy", "The Daily", "The Herald", "Reuters", "Reuters via The Herald",
              "AFP", "Wikipedia", None]
DATES = ["2024-03-01", "2024-03-02", "2024-03-20", "2024-04-15", "2025-01-01", "2024-02-01", "2024-03", None, "undated"]
SUPPORTS = [None, ["occurrence"], ["effect"], ["occurrence", "effect"], ["attribution"], ["ai_involvement"], []]


def random_source(rng):
    s = src(rng.choice(ROLES), site=rng.choice(SITES), publisher=rng.choice(PUBLISHERS), date=rng.choice(DATES),
            opened=rng.choice([True, False, None]), path=str(rng.randrange(4)))
    supports = rng.choice(SUPPORTS)
    if supports is not None:
        s["supports"] = supports
    if rng.random() < 0.3:
        s["medium"] = "social"
        s["social"] = {"platform": rng.choice(["x", "telegram"]), "handle": rng.choice(["gridco", "anon123", "reporter"]),
                       "account_tier": rng.choice(["S1", "S2", "S3", "S4", None])}
        if rng.random() < 0.6:
            s["social"]["identity_basis"] = rng.choice(["listed on the organisation's site", "platform_badge"])
    if rng.random() < 0.1:
        s["origin"] = rng.choice(["wire:Reuters", "gridco statement"])
    return s


def random_set(rng, most=6):
    return [random_source(rng) for _ in range(rng.randrange(most + 1))]


def _points(result):
    return {k: v["points"] for k, v in result["components"].items()}


# --- monotonicity ----------------------------------------------------------------------------------

def _counted(sources):
    """The sources the origin count is taken over: direct or independent, backing the record."""
    return [s for s in sources if (EC._supports(s, "occurrence") or EC._supports(s, "effect"))
            and EC.tier_of(s) in EC.METHOD["corroborating_tiers"]]


def _joins_two_groups(base, extra):
    """`extra` shares an identity with sources of `base` that were counted as separate."""
    linked = [s for s in _counted(base) if EC.origin_keys(s) & EC.origin_keys(extra)]
    return EC.independent_origins(linked) >= 2


def test_adding_a_source_lowers_nothing_unless_it_shows_two_sources_are_one():
    """Every component but the origin count is a maximum or an "any", so a new source cannot lower
    it. The origin count can fall, and only one way: the new citation shares an origin, a publisher
    or an organisation with two sources that had been counted apart. That is a correction."""
    rng = random.Random(22)
    fell = 0
    for _ in range(3000):
        base, extra = random_set(rng), random_source(rng)
        spec = rng.choice(EC.EFFECT_SPECIFICITY)
        before, after = assess(base, spec), assess(base + [extra], spec)
        if before["category"] is None or after["category"] is None:
            continue                       # not assessed: nothing to compare (tested apart)
        for k, v in _points(before).items():
            if k != "origins":
                assert _points(after)[k] >= v, (k, base, extra)
        if after["components"]["origins"]["count"] < before["components"]["origins"]["count"]:
            fell += 1
            assert _joins_two_groups(base, extra), (base, extra)
        else:
            assert after["score"] >= before["score"], (base, extra)
            assert RANK[after["category"]] >= RANK[before["category"]], (base, extra)
    assert fell, "the generator never produced a citation that joins two groups"


def test_where_each_site_has_one_publisher_adding_a_source_never_lowers_anything():
    """With nothing to reveal (every site speaks under one name, no declared origin), the score,
    every component and the category can only rise."""
    rng = random.Random(23)
    for _ in range(1500):
        pool = []
        for _n in range(rng.randrange(7) + 1):
            s = random_source(rng)
            s.pop("origin", None)
            s["publisher"] = "Publisher of " + s["url"].split("/")[2]
            if s.get("social"):
                s["social"]["handle"] = s["url"].split("/")[2]
            pool.append(s)
        base, extra = pool[:-1], pool[-1]
        before, after = assess(base), assess(base + [extra])
        if before["category"] is None or after["category"] is None:
            continue
        assert after["score"] >= before["score"], (base, extra)
        assert RANK[after["category"]] >= RANK[before["category"]], (base, extra)
        assert after["components"]["origins"]["count"] >= before["components"]["origins"]["count"]


def test_removing_a_source_raises_nothing_unless_it_was_joining_two_groups():
    rng = random.Random(2022)
    for _ in range(600):
        full = random_set(rng, most=7)
        whole = assess(full)
        for i in range(len(full)):
            rest = full[:i] + full[i + 1:]
            part = assess(rest)
            if whole["category"] is None or part["category"] is None:
                continue
            if part["components"]["origins"]["count"] > whole["components"]["origins"]["count"]:
                assert _joins_two_groups(rest, full[i]), (full, i)
            else:
                assert part["score"] <= whole["score"], (full, i)
                assert RANK[part["category"]] <= RANK[whole["category"]], (full, i)


def test_the_order_sources_are_listed_in_changes_nothing():
    rng = random.Random(7)
    for _ in range(300):
        s = random_set(rng)
        shuffled = s[:]
        rng.shuffle(shuffled)
        assert assess(s) == assess(shuffled)


# --- duplicates, same origin, count ------------------------------------------------------------------

def test_a_duplicate_citation_changes_nothing():
    rng = random.Random(3)
    for _ in range(600):
        s = random_set(rng, most=5)
        if s:
            assert assess(s + [copy.deepcopy(rng.choice(s))]) == assess(s)


def test_a_second_citation_from_the_same_origin_changes_nothing():
    rng = random.Random(4)
    for _ in range(600):
        s = random_set(rng, most=5)
        if not s:
            continue
        again = copy.deepcopy(rng.choice(s))
        again["url"] = again["url"].rsplit("/", 1)[0] + "/a-second-release"
        again["title_en"] = "A second release from the same publisher"
        assert assess(s + [again]) == assess(s), (s, again)


def test_three_releases_from_one_utility_are_one_origin():
    one = [src("operator", site="gridco.example", publisher="GridCo")]
    three = one + [src("operator", site="gridco.example", publisher="GridCo", path=p, date=d)
                   for p, d in (("update-2", "2024-03-03"), ("update-3", "2024-03-05"))]
    assert assess(three) == assess(one)
    assert assess(three)["components"]["origins"] == {"count": 1, "points": 0, "basis": "reviewed"}


def test_source_count_never_enters_only_who_speaks_and_how_many_origins():
    """Each citation repeated twenty times under new addresses: the same result, whatever the set."""
    rng = random.Random(5)
    for _ in range(200):
        s = random_set(rng, most=4)
        padded = []
        for x in s:
            for n in range(20):
                y = copy.deepcopy(x)
                y["url"] = f"{x['url']}-copy{n}"
                padded.append(y)
        assert assess(padded) == assess(s)


def test_ten_syndicated_copies_of_a_wire_story_are_one_origin():
    one = assess([wire_copy(0)])
    ten = assess([wire_copy(i) for i in range(10)])
    assert ten == one
    assert ten["components"]["origins"]["count"] == 1 and ten["components"]["origins"]["points"] == 0
    # ...and the wire itself beside its copies is still that one origin.
    assert assess([src("wire", site="reuters.example", publisher="Reuters")] + [wire_copy(i) for i in range(10)])["score"] == one["score"]


def test_one_publisher_on_two_sites_or_on_its_site_and_its_account_is_one_origin():
    site = src("operator", site="gridco.example", publisher="GridCo")
    mirror = src("operator", site="gridco-newsroom.example", publisher="GridCo")
    account = post("S1")
    assert EC.independent_origins([site, mirror]) == 1
    assert EC.independent_origins([site, account]) == 1
    assert assess([site, account])["components"]["origins"]["points"] == 0
    # A different organisation is a second origin, on any medium.
    assert EC.independent_origins([site, post("S1", role="government", handle="energymin", publisher="Ministry of Energy")]) == 2


def test_an_aggregator_or_a_discovery_aid_is_never_an_origin():
    media = src("media")
    aggregator = src("aggregator", site="feeds.example", publisher="Energy Feed")
    wikipedia = src("media", site="en.wikipedia.org", publisher="Wikipedia")
    assert EC.tier_of(aggregator) == "secondary" and EC.tier_of(wikipedia) == "secondary"
    assert EC.origin_of(wikipedia) is None
    assert assess([media, aggregator, wikipedia]) == assess([media])
    # Beside a secondary source that is not a discovery aid (a dataset), they still add nothing,
    # and a secondary source establishes neither the effect nor a date nor a reading.
    dataset = src("dataset", site="eventdata.example", publisher="An event database")
    thin = assess([dataset, aggregator, wikipedia], "quantified")
    assert thin == assess([dataset], "quantified")
    assert thin["components"]["origins"]["count"] == 0 and thin["category"] == "PRELIMINARY"
    assert thin["components"]["effect"]["points"] == 0, "a secondary source does not establish the effect"
    assert thin["components"]["opened"]["points"] == 0 and thin["components"]["contemporaneous"]["points"] == 0


def test_a_dataset_restating_others_is_secondary_and_no_role_is_promoted_in_code():
    assert EC.tier_of(src("dataset", site="eventdata.example", publisher="An event database")) == "secondary"
    for role, tier in EC.METHOD["role_tier"].items():
        assert EC.tier_of(src(role, site="somewhere.example")) == tier, role
    assert EC.tier_of(src("unheard_of_role")) == "secondary"


# --- directness and corroboration are separate -------------------------------------------------------

def test_an_official_source_alone_beats_an_anonymous_post_alone():
    official = assess([src("operator", site="gridco.example", publisher="GridCo")], "quantified")
    anonymous = assess([post("S4", role="operator", handle="anon123", publisher="anon123", identity=None)], "quantified")
    assert official["score"] > anonymous["score"]
    assert RANK[official["category"]] > RANK[anonymous["category"]]
    assert official["category"] == "MODERATE" and anonymous["category"] == "PRELIMINARY"
    # Not marked down for corroboration it could not have: every component but origins is full.
    assert _points(official) == {"directness": 40, "origins": 0, "effect": 15, "opened": 10, "contemporaneous": 10}


def test_two_independent_credible_origins_are_worth_more_than_one():
    one = assess([src("media")])
    two = assess([src("media"), src("media", site="herald.example")])
    three = assess([src("media"), src("media", site="herald.example"), src("wire", site="afp.example", publisher="AFP")])
    assert one["score"] < two["score"] < three["score"]
    assert [x["components"]["origins"]["points"] for x in (one, two, three)] == [0, 16, 25]
    four = assess([src("media", site=f"paper{i}.example") for i in range(4)])
    assert four["score"] == three["score"], "three or more is the ceiling: a fourth outlet adds nothing"


def test_the_effect_counts_only_when_a_direct_or_independent_source_supports_it():
    occurrence_only = src("media", supports=["occurrence"])
    assert assess([occurrence_only], "quantified")["components"]["effect"] == {"specificity": None, "points": 0}
    with_effect = assess([occurrence_only, src("operator", site="gridco.example", supports=["effect"])], "quantified")
    assert with_effect["components"]["effect"] == {"specificity": "quantified", "points": 15}
    q, d, v = (assess([src("media")], s)["components"]["effect"]["points"] for s in ("quantified", "described", "vague"))
    assert (q, d, v) == (15, 8, 0)


def test_a_source_that_supports_only_attribution_or_ai_adds_nothing_to_evidence_confidence():
    base = [src("media")]
    firm = src("cyber_firm", site="threatlab.example", supports=["attribution"])
    advisory = src("government", site="cert.example", supports=["ai_involvement"])
    assert assess(base + [firm, advisory]) == assess(base)
    assert assess([firm, advisory])["score"] == 0


def test_only_a_source_a_reviewer_opened_earns_the_opened_points():
    for opened, points in ((True, 10), (False, 0), (None, 0)):
        assert assess([src("media", opened=opened)])["components"]["opened"]["points"] == points
    # An unverified post a reviewer read is still unverified.
    assert assess([post("S4", identity=None, opened=True)])["components"]["opened"]["points"] == 0


@pytest.mark.parametrize("cited,timely", [
    ("2024-03-01", True), ("2024-02-29", True), ("2024-03-31", True), ("2024-04-01", False),
    ("2026-03-01", False), ("2024-02-01", False), (None, False), ("12 March 2024", False), ("2024-03", True)])
def test_contemporaneous_is_within_thirty_days_after_the_event_never_before_it(cited, timely):
    got = assess([src("media", date=cited)])["components"]["contemporaneous"]["points"]
    assert got == (10 if timely else 0)


def test_a_long_event_is_contemporaneous_to_its_end_and_a_month_dated_event_to_the_month():
    assert assess([src("media", date="2024-06-20")], date_end="2024-06-01")["components"]["contemporaneous"]["points"] == 10
    assert assess([src("media", date="2024-08-20")], date_end="2024-06-01")["components"]["contemporaneous"]["points"] == 0
    assert assess([src("media", date="2024-04-25")], date="2024-03")["components"]["contemporaneous"]["points"] == 10
    assert assess([src("media", date="2024-05-25")], date="2024-03")["components"]["contemporaneous"]["points"] == 0


def test_categories_follow_the_published_thresholds():
    cuts = {c["id"]: c["min"] for c in EC.METHOD["categories"]}
    assert cuts == {"HIGH": 78, "MODERATE": 55, "LIMITED": 35, "PRELIMINARY": 0}
    assert EC.METHOD["contemporaneous_days"] == 30
    assert EC.METHOD["origin_points"] == {"1": 0, "2": 16, "3": 25}
    # One independent report, effect only general, read at the time: 28 + 0 + 10 + 10.
    assert (assess([src("media")], "vague")["score"], assess([src("media")], "vague")["category"]) == (48, "LIMITED")
    # Two official origins, quantified, read, at the time: the maximum short of a third origin.
    top = assess([src("operator", site="gridco.example"), src("regulator", site="regulator.example")], "quantified")
    assert (top["score"], top["category"]) == (91, "HIGH")


# --- claims and unverified posts ----------------------------------------------------------------------

def test_a_self_claim_alone_cannot_support_occurrence_above_preliminary():
    claims = [src("actor_self_claim", site=f"channel{i}.example", publisher=f"Channel {i}") for i in range(8)]
    r = assess(claims, "quantified")
    assert r["category"] == "PRELIMINARY" and "Rests on unverified claims only" in r["reasons"]
    assert r["components"]["origins"]["count"] == 0, "eight channels carrying one boast are no corroboration"
    assert r["score"] == EC.METHOD["tiers"]["unverified"]["points"]


def test_the_unverified_cap_holds_whatever_the_points_say(monkeypatch):
    """The cap is a rule of its own, not a consequence of today's numbers."""
    method = copy.deepcopy(EC.METHOD)
    method["tiers"]["unverified"]["points"] = 95
    method["tiers"]["researcher_social"]["points"] = 95
    monkeypatch.setattr(EC, "METHOD", method)
    assert assess([src("actor_self_claim")])["category"] == "PRELIMINARY"
    assert assess([post("S3", role="researcher", handle="osint", publisher="An OSINT account")])["category"] == "PRELIMINARY"
    assert assess([post("S4", identity=None)])["category"] == "PRELIMINARY"
    assert assess([])["category"] == "PRELIMINARY"


def test_no_sources_is_preliminary_with_a_zero_score_and_says_why():
    r = assess([])
    assert (r["category"], r["score"]) == ("PRELIMINARY", 0)
    assert "No first-party source and no press report" in r["reasons"]


# --- social media is a medium, not a quality level ------------------------------------------------------

def test_an_established_official_account_counts_as_its_organisation():
    for role in ("operator", "government", "regulator"):
        assert EC.tier_of(post("S1", role=role)) == "direct"
    r = assess([post("S1")], "quantified")
    assert r["components"]["directness"] == {"tier": "direct", "points": 40} and r["category"] == "MODERATE"
    assert r == assess([src("operator", site="gridco.example", publisher="GridCo")], "quantified")


def test_an_anonymous_account_never_counts_as_an_organisation_whatever_role_it_is_given():
    for role in ROLES:
        assert EC.tier_of(post("S4", role=role, handle="anon123", publisher="anon123", identity=None)) == "unverified", role
        # ...even one that says who it is: the tier is what the reviewer established.
        assert EC.tier_of(post("S4", role=role, handle="anon123", publisher="GridCo", identity="says it is GridCo")) == "unverified"
    assert EC.tier_of(post(None, identity=None)) == "unverified", "a post with no tier is not an official one"
    assert EC.tier_of(post("S3", role="operator")) == "researcher_social"
    assert EC.tier_of(post("S2", role="operator")) == "secondary"


@pytest.mark.parametrize("tier", ["S1", "S2", "S3", "S4", None])
def test_a_platform_badge_changes_nothing(tier):
    plain = post(tier, identity=None)
    badged = copy.deepcopy(plain)
    badged["verified"] = True
    badged["social"].update({"verified": True, "badge": "blue", "platform_verified": True})
    assert EC.tier_of(badged) == EC.tier_of(plain)
    assert assess([badged], "quantified") == assess([plain], "quantified")


def test_an_official_tier_without_an_established_identity_is_not_official():
    assert EC.tier_of(post("S1", identity=None)) == "unverified"
    for badge in ("platform_badge", "verified_badge", "Verified", "blue_check"):
        assert EC.tier_of(post("S1", identity=badge)) == "unverified", badge
    assert EC.tier_of(post("S1", identity="linked from the ministry's own website")) == "direct"


# --- disputes --------------------------------------------------------------------------------------------

STRONG = [src("operator", site="gridco.example", publisher="GridCo"), src("regulator", site="regulator.example", publisher="Regulator"),
          src("wire", site="afp.example", publisher="AFP")]


@pytest.mark.parametrize("dispute", [{"about": "occurrence"}, {"about": "effect"}, {"about": ["effect", "attribution"]},
                                     {"note": "accounts differ"}, "accounts differ"])
def test_a_dispute_overrides_the_score(dispute):
    settled, contested = assess(STRONG, "quantified"), assess(STRONG, "quantified", dispute)
    assert settled["category"] == "HIGH" and settled["disputed"] is False
    assert contested["category"] == "DISPUTED" and contested["disputed"] is True
    assert contested["score"] == settled["score"], "the score is still shown; the category is what changes"
    assert "Credible sources disagree" in contested["reasons"]


def test_a_dispute_about_who_did_it_does_not_dispute_that_it_happened():
    assert assess(STRONG, "quantified", {"about": "attribution"})["category"] == "HIGH"
    assert assess(STRONG, "quantified", None)["category"] == "HIGH"


def test_a_credible_source_recorded_as_disputing_the_record_makes_it_disputed():
    denial = src("government", site="othergov.example", publisher="Another ministry", supports=[], disputes=["occurrence"])
    assert assess(STRONG + [denial], "quantified")["category"] == "DISPUTED"
    # An anonymous denial is not credible disagreement.
    troll = post("S4", identity=None, supports=[], disputes=["occurrence"])
    assert assess(STRONG + [troll], "quantified")["category"] == "HIGH"
    assert assess(STRONG + [dict(denial, disputes=["attribution"])], "quantified")["category"] == "HIGH"


# --- attribution confidence -------------------------------------------------------------------------------

def att(status, **kw):
    a = {"status": status, "actor": "Group X", "actor_type": "state_linked", "as_of": "2024-04-01", "basis": [], "competing": []}
    a.update(kw)
    return a


def asrc(role, site, **kw):
    return src(role, site=site, publisher=kw.pop("publisher", site), supports=["attribution"], **kw)


GOV = asrc("government", "security-service.example")
POLICE = asrc("law_enforcement", "police.example")
VICTIM = asrc("operator", "gridco.example")
FIRM = asrc("cyber_firm", "threatlab.example")
FIRM2 = asrc("cyber_firm", "otherlab.example")
PRESS = asrc("media", "daily.example")
PRESS2 = asrc("wire", "afp.example")
CLAIM = asrc("actor_self_claim", "channel.example")


def test_unknown_attribution_is_not_established_never_low():
    unknown = {"status": "UNKNOWN", "actor": None}
    assert EC.attribution_confidence(unknown, []) == "NOT_ESTABLISHED"
    assert EC.attribution_confidence(unknown, [src("media")]) == "NOT_ESTABLISHED"
    assert EC.attribution_problems(unknown, [src("media")]) == []
    assert EC.METHOD["attribution"]["labels"]["NOT_ESTABLISHED"] == "Not established"
    assert "not a low confidence" in EC.METHOD["attribution"]["meanings"]["NOT_ESTABLISHED"]
    assert EC.attribution_confidence({"status": "NOT_APPLICABLE"}, []) is None
    assert EC.attribution_confidence(None, []) is None


@pytest.mark.parametrize("sources,expected", [
    ([GOV, FIRM], "HIGH"), ([POLICE, VICTIM], "HIGH"), ([GOV, POLICE], "HIGH"),
    ([GOV], "MODERATE"), ([VICTIM], "MODERATE"), ([FIRM, FIRM2], "MODERATE"),
    ([GOV, dict(GOV, url="https://security-service.example/second-statement")], "MODERATE"),
    ([FIRM], "LOW"), ([PRESS], "LOW"), ([asrc("researcher", "uni.example")], "LOW"),
    ([CLAIM], "CLAIM_ONLY"), ([], "NOT_ESTABLISHED"),
])
def test_attribution_confidence_by_who_attributes(sources, expected):
    assert EC.attribution_confidence(att("ASSESSED"), sources) == expected


def test_a_self_claim_alone_cannot_exceed_claim_only():
    many = [asrc("actor_self_claim", f"channel{i}.example") for i in range(6)]
    borrowed = dict(CLAIM, attribution_basis="government")
    as_claimed_basis = asrc("media", "daily.example", attribution_basis="actor_self_claim")
    for status in ("CLAIMED", "SUSPECTED", "ASSESSED", "ATTRIBUTED"):
        for sources in (many, [borrowed], [CLAIM, as_claimed_basis]):
            assert EC.attribution_confidence(att(status), sources) == "CLAIM_ONLY", (status, sources)
    assert EC.attribution_problems(att("CLAIMED"), many) == []
    for status in ("SUSPECTED", "ASSESSED", "ATTRIBUTED"):
        assert EC.attribution_problems(att(status), many), status
        assert EC.attribution_problems(att(status), [borrowed]), status


def test_attributed_without_an_official_basis_is_refused():
    assert EC.attribution_problems(att("ATTRIBUTED"), [GOV]) == []
    assert EC.attribution_problems(att("ATTRIBUTED"), [POLICE, FIRM]) == []
    # A wire story carrying a government's attribution, declared as such, is an official basis.
    assert EC.attribution_problems(att("ATTRIBUTED"), [dict(PRESS2, attribution_basis="government")]) == []
    for sources in ([VICTIM], [FIRM, FIRM2], [PRESS, PRESS2],
                    [FIRM, FIRM2, asrc("cyber_firm", "thirdlab.example"), asrc("researcher", "uni.example")], [CLAIM]):
        problems = EC.attribution_problems(att("ATTRIBUTED"), sources)
        assert any("ATTRIBUTED needs a formal government" in p for p in problems), sources
        assert EC.attribution_problems(att("ASSESSED"), sources) == [] or sources == [CLAIM]


def test_claimed_needs_the_claim_and_nothing_firmer():
    assert EC.attribution_problems(att("CLAIMED"), [CLAIM]) == []
    assert any("CLAIMED needs the actor's own claim" in p for p in EC.attribution_problems(att("CLAIMED"), [PRESS]))
    assert any("understates" in p for p in EC.attribution_problems(att("CLAIMED"), [CLAIM, GOV]))


def test_news_coverage_restating_an_attribution_is_not_a_second_attribution():
    """Two outlets repeating one statement are not two attributions, and an outlet beside the
    government it quotes does not make the attribution High."""
    assert EC.attribution_confidence(att("ATTRIBUTED"), [GOV, PRESS]) == "MODERATE"
    assert EC.attribution_confidence(att("ATTRIBUTED"), [GOV, PRESS, PRESS2]) == "MODERATE"
    assert EC.attribution_confidence(att("SUSPECTED"), [PRESS, PRESS2]) == "LOW"
    # Declared as an investigation of its own, press counts.
    own = [dict(PRESS, attribution_basis="media_investigation"), dict(PRESS2, attribution_basis="media_investigation")]
    assert EC.attribution_confidence(att("ASSESSED"), own) == "MODERATE"
    assert EC.attribution_confidence(att("ATTRIBUTED"), [GOV, own[0]]) == "HIGH"
    # One government statement carried by two outlets is one basis, however it is cited.
    carried = [dict(PRESS, attribution_basis="government"), dict(PRESS2, attribution_basis="government")]
    assert EC.attribution_confidence(att("ATTRIBUTED"), carried) == "MODERATE"


def test_an_anonymous_post_or_a_discovery_aid_attributes_nothing():
    anon = post("S4", role="government", handle="anon123", publisher="anon123", identity=None, supports=["attribution"])
    wikipedia = src("media", site="en.wikipedia.org", publisher="Wikipedia", supports=["attribution"])
    for sources in ([anon], [wikipedia], [anon, wikipedia]):
        assert EC.attribution_confidence(att("ATTRIBUTED"), sources) == "NOT_ESTABLISHED"
        assert EC.attribution_problems(att("SUSPECTED"), sources)
    # A post cannot borrow a government's authority through the override either.
    borrowed = post("S3", role="researcher", handle="osint", publisher="An OSINT account", supports=["attribution"],
                    attribution_basis="government")
    assert EC.attribution_confidence(att("ATTRIBUTED"), [borrowed]) == "LOW"
    assert EC.attribution_problems(att("ATTRIBUTED"), [borrowed])


def test_adding_an_attribution_source_never_lowers_attribution_confidence():
    """Among third-party attributions. (A self-claim is different: once the claim itself is cited,
    press coverage that declares no finding of its own is seen to be the claim again.)"""
    order = ["NOT_ESTABLISHED", "CLAIM_ONLY", "LOW", "MODERATE", "HIGH"]
    pool = [GOV, POLICE, VICTIM, FIRM, FIRM2, PRESS, PRESS2, dict(PRESS, attribution_basis="government"),
            src("media", supports=["occurrence"])]
    rng = random.Random(11)
    for _ in range(800):
        base = [rng.choice(pool) for _ in range(rng.randrange(5))]
        a, b = (EC.attribution_confidence(att("ATTRIBUTED"), s) for s in (base, base + [rng.choice(pool)]))
        assert order.index(b) >= order.index(a), base
    # Citing the claim beside undeclared press coverage shows the coverage for what it is.
    assert EC.attribution_confidence(att("SUSPECTED"), [PRESS]) == "LOW"
    assert EC.attribution_confidence(att("SUSPECTED"), [PRESS, CLAIM]) == "CLAIM_ONLY"


def test_disputed_attribution_is_disputed_and_needs_the_competing_view():
    assert EC.attribution_confidence(att("DISPUTED"), [GOV, FIRM]) == "DISPUTED"
    assert any("competing" in p for p in EC.attribution_problems(att("DISPUTED"), [GOV]))
    assert EC.attribution_problems(att("DISPUTED", competing=[{"actor": "Group Y"}]), [GOV]) == []


# --- AI involvement -------------------------------------------------------------------------------------------

def ai(status, **kw):
    a = {"status": status, "relation": "ai_assisted", "role": "social_engineering_generation", "as_of": "2024-05-01"}
    a.update(kw)
    return a


NONE = {"status": "NONE_REPORTED", "relation": None, "role": None, "as_of": None, "statement": None, "source_refs": []}
AI_OPERATOR = src("operator", site="gridco.example", supports=["ai_involvement"])
AI_FIRM = src("cyber_firm", site="threatlab.example", supports=["ai_involvement"])


@pytest.mark.parametrize("status", ["CLAIMED", "SUSPECTED", "ASSESSED", "CONFIRMED"])
def test_an_ai_status_without_an_incident_specific_source_is_refused(status):
    general = src("government", site="cert.example", supports=["occurrence"])
    for sources in ([], [general], [src("media")]):
        assert any("no source that ties AI to this incident" in p for p in EC.ai_problems(ai(status), sources)), sources


def test_confirmed_ai_needs_a_direct_source_and_assessed_an_investigator():
    assert EC.ai_problems(ai("CONFIRMED"), [AI_OPERATOR]) == []
    for weaker in ([AI_FIRM], [src("media", supports=["ai_involvement"])],
                   [post("S2", role="media", handle="reporter", publisher="A reporter", supports=["ai_involvement"])]):
        assert any("CONFIRMED needs a direct authoritative source" in p for p in EC.ai_problems(ai("CONFIRMED"), weaker))
    assert EC.ai_problems(ai("ASSESSED"), [AI_FIRM]) == []
    aggregator = src("aggregator", site="feeds.example", supports=["ai_involvement"])
    assert any("ASSESSED needs" in p for p in EC.ai_problems(ai("ASSESSED"), [aggregator]))
    assert EC.ai_problems(ai("SUSPECTED"), [aggregator]) == []


def test_none_reported_with_a_role_a_relation_or_an_ai_source_is_refused():
    assert EC.ai_problems(NONE, [src("media")]) == []
    assert EC.ai_problems({**NONE, "role": "attacker_assistance"}, [])
    assert EC.ai_problems({**NONE, "relation": "ai_assisted"}, [])
    assert EC.ai_problems(NONE, [AI_FIRM])


def test_an_ai_finding_needs_a_relation_because_assistance_is_not_causation():
    assert any("relation" in p for p in EC.ai_problems(ai("SUSPECTED", relation=None), [AI_FIRM]))
    assert any("role" in p for p in EC.ai_problems(ai("SUSPECTED", role="very_clever"), [AI_FIRM]))
    assert EC.ai_problems({"status": "PROBABLY"}, [])


def test_an_anonymous_post_is_never_the_sole_evidence_of_ai_involvement():
    anon = post("S4", identity=None, supports=["ai_involvement"])
    for status in ("CLAIMED", "SUSPECTED", "ASSESSED", "CONFIRMED"):
        assert any("never sole evidence" in p for p in EC.ai_problems(ai(status), [anon])), status
    boast = src("actor_self_claim", site="channel.example", supports=["ai_involvement"])
    assert EC.ai_problems(ai("CLAIMED"), [boast]) == []
    assert EC.ai_problems(ai("SUSPECTED"), [boast])


# --- the ten adversarial cases of the owner's brief ----------------------------------------------------------

def test_case_01_five_syndicated_copies_of_one_wire_report_are_one_report():
    r = assess([wire_copy(i) for i in range(5)])
    assert (r["category"], r["score"]) == ("MODERATE", 56)
    assert r["components"]["origins"] == {"count": 1, "points": 0, "basis": "reviewed"}
    assert r == assess([wire_copy(0)]), "five copies say exactly what one says"
    assert "One originating statement" in r["reasons"]


def test_case_02_one_official_operator_notice_is_moderate_not_marked_down_and_not_high():
    r = assess([src("operator", site="gridco.example", publisher="GridCo")], "quantified")
    assert (r["category"], r["score"]) == ("MODERATE", 75)
    assert r["components"]["directness"]["tier"] == "direct"
    assert r["score"] > assess([wire_copy(i) for i in range(5)], "quantified")["score"], "one operator beats five copies"


def test_case_03_one_anonymous_social_post_is_preliminary():
    r = assess([post("S4", role="media", handle="anon123", publisher="anon123", identity=None)], "quantified")
    assert (r["category"], r["score"]) == ("PRELIMINARY", 4)
    assert "Rests on unverified claims only" in r["reasons"]


def test_case_04_an_attacker_claim_with_no_victim_confirmation_is_a_claim_only():
    claim = src("actor_self_claim", site="channel.example", supports=["occurrence", "effect", "attribution"])
    assert assess([claim], "quantified")["category"] == "PRELIMINARY"
    assert EC.attribution_confidence(att("CLAIMED"), [claim]) == "CLAIM_ONLY"
    assert EC.attribution_problems(att("CLAIMED"), [claim]) == []
    for status in ("SUSPECTED", "ASSESSED", "ATTRIBUTED"):
        assert EC.attribution_problems(att(status), [claim]), f"a claim alone is not {status}"


def test_case_05_an_official_attribution_plus_a_technical_report_is_high_attribution():
    assert EC.attribution_confidence(att("ATTRIBUTED"), [GOV, FIRM]) == "HIGH"
    assert EC.attribution_problems(att("ATTRIBUTED"), [GOV, FIRM]) == []
    # ...and says nothing about whether the outage happened: those sources support attribution only.
    assert assess([GOV, FIRM])["score"] == 0


def test_case_06_conflicting_official_accounts_are_disputed_not_averaged():
    says = src("government", site="ministry.example", publisher="Ministry of Energy")
    denies = src("operator", site="gridco.example", publisher="GridCo", supports=[], disputes=["effect"])
    r = assess([says, denies], "quantified")
    assert r["category"] == "DISPUTED" and r["label"] == "Disputed"
    assert assess([says, src("operator", site="gridco.example", publisher="GridCo")], "quantified",
                  {"about": "effect"})["category"] == "DISPUTED"


def test_case_07_a_deleted_official_post_plus_an_archived_reputable_report_still_stands():
    deleted = post("S1", opened=False, link_check="deleted")
    archived = src("media", link_check="archived_copy")
    r = assess([deleted, archived])
    assert (r["category"], r["score"]) == ("HIGH", 84)
    assert r["components"]["directness"]["tier"] == "direct" and r["components"]["origins"]["count"] == 2
    live = assess([dict(deleted, link_check="reachable"), dict(archived, link_check="reachable")])
    assert r == live, "a deleted post does not erase a corroborated claim; link state never enters"


def test_case_08_a_well_evidenced_event_with_an_unknown_actor_keeps_both_answers_apart():
    r = assess(STRONG, "quantified")
    assert r["category"] == "HIGH"
    unknown = {"status": "UNKNOWN", "actor": None}
    assert EC.attribution_confidence(unknown, STRONG) == "NOT_ESTABLISHED"
    assert EC.attribution_problems(unknown, STRONG) == []


def test_case_09_a_known_actor_with_an_uncertain_effect_keeps_both_answers_apart():
    sources = [src("media", supports=["occurrence"]), GOV, FIRM]
    r = assess(sources, "vague")
    assert (r["category"], r["score"]) == ("LIMITED", 48)
    assert EC.attribution_confidence(att("ATTRIBUTED"), sources) == "HIGH"
    assert r == assess(sources[:1], "vague"), "a firm attribution does not firm up the effect"


def test_case_10_a_generic_ai_warning_with_no_incident_evidence_supports_no_ai_label():
    warning = src("government", site="cert.example", publisher="National cyber agency", supports=[])
    for status in ("CLAIMED", "SUSPECTED", "ASSESSED", "CONFIRMED"):
        assert EC.ai_problems(ai(status), [warning, src("media")]), status
    assert EC.ai_problems(NONE, [warning, src("media")]) == []
    assert assess([warning, src("media")]) == assess([src("media")]), "a general warning is not evidence of this event"


# --- the output shape other modules rely on --------------------------------------------------------------------

def test_the_public_names_and_the_output_shape_are_kept():
    for name in ("assess", "attribution_confidence", "attribution_problems", "ai_problems", "method", "origin_of", "tier_of"):
        assert callable(getattr(EC, name)), name
    r = assess(STRONG, "quantified")
    # Every key of the first version is still there; `reason` and `cap` were added by the red-team fixes.
    assert set(r) == {"category", "label", "score", "disputed", "components", "reasons", "reason", "cap"}
    assert set(r["components"]) == {"directness", "origins", "effect", "opened", "contemporaneous"}
    assert set(r["components"]["origins"]) == {"count", "points", "basis"}
    assert isinstance(r["score"], int) and 0 <= r["score"] <= 100
    # A record that is not assessed keeps the same keys, with nulls where there is nothing to say.
    na = assess([src("media", site="en.wikipedia.org", publisher="Wikipedia")])
    assert set(na) == set(r) and set(na["components"]) == set(r["components"])
    m = EC.method()
    assert [c["id"] for c in m["categories"]] == ["HIGH", "MODERATE", "LIMITED", "PRELIMINARY", "DISPUTED"]
    assert sum(c["max"] for c in m["components"]) == 100
    assert "not a probability" in m["statement"]


def test_no_score_can_exceed_one_hundred_or_fall_below_zero():
    rng = random.Random(9)
    for _ in range(500):
        r = assess(random_set(rng), rng.choice(EC.EFFECT_SPECIFICITY))
        if r["category"] is None:
            assert r["score"] is None and set(_points(r).values()) == {None}, "not assessed is null, never zero"
        else:
            assert 0 <= r["score"] <= 100 and r["score"] == sum(_points(r).values())


# --- job A: evidence confidence on country records ----------------------------------------------------------

def _cap(**kw):
    return {"value": None, "value_min": None, "value_max": None, "qualifier": "exact", "measure": "affected",
            "unit": "customers", "source_says": "s", **kw}


def test_effect_is_quantified_only_by_a_figure_for_what_was_affected():
    assert B.effect_specificity({"capacity_affected": None}) == "described"
    assert B.effect_specificity({"capacity_affected": _cap(value=120000)}) == "quantified"
    assert B.effect_specificity({"capacity_affected": _cap(value_min=100000, qualifier="at_least")}) == "quantified"
    assert B.effect_specificity({"capacity_affected": _cap(value_max=5, qualifier="at_most")}) == "quantified"
    assert B.effect_specificity({"capacity_affected": _cap(value=3500, measure="other")}) == "quantified"
    # A plant's nameplate is not the amount lost; a disputed figure carries no value.
    assert B.effect_specificity({"capacity_affected": _cap(value=15, measure="facility_size")}) == "described"
    assert B.effect_specificity({"capacity_affected": _cap(qualifier="disputed")}) == "described"
    assert B.effect_specificity({"capacity_affected": _cap(value=0)}) == "quantified", "a reported zero is a figure"


def test_a_country_record_gains_evidence_confidence_and_keeps_every_other_field():
    e = {"event_id": "xx-1", "date": "2024-03-01", "date_end": None, "capacity_affected": _cap(value=120000),
         "sources": [{"url": "https://gridco.example/a", "publisher": "GridCo", "date": "2024-03-02", "language": "en",
                      "source_role": "operator", "opened": True}]}
    before = copy.deepcopy(e)
    B.attach_evidence_confidence([e])
    assert {k: v for k, v in e.items() if k != "evidence_confidence"} == before
    assert e["evidence_confidence"] == EC.assess(before["sources"], "2024-03-01", None, "quantified")
    assert e["evidence_confidence"]["category"] == "MODERATE"
    summary = B.evidence_confidence_summary([e])
    assert summary["by_category"] == {"HIGH": 0, "MODERATE": 1, "LIMITED": 0, "PRELIMINARY": 0, "DISPUTED": 0}


def _served(sid, name):
    p = WEB / systems.root(sid) / name
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def _built():
    doc = _served(systems.COUNTRY_SYSTEMS[0], "events.json")
    return bool(doc) and all("evidence_confidence" in e for e in doc["events"])


needs_build = pytest.mark.skipif(not _built(), reason="the served country payloads predate evidence confidence; run pipeline.run")


@needs_build
def test_every_served_country_record_carries_a_confidence_that_its_own_public_fields_reproduce():
    """The served value is a function of the served record alone: its published citations, its dates,
    whether it carries a figure and its published review block. So it says nothing those do not, on
    a campaign-covered record as on any other."""
    covered = 0
    for sid in systems.COUNTRY_SYSTEMS:
        for e in _served(sid, "events.json")["events"]:
            again = EC.assess(e["sources"], e["date"], e.get("date_end"), B.effect_specificity(e), review=e.get("review"))
            assert e["evidence_confidence"] == again, e["event_id"]
            assert e["evidence_confidence"]["category"] in (*EC.CATEGORIES, None)
            covered += bool(e.get("publication"))
    assert covered, "no campaign-covered record was checked"


@needs_build
def test_serving_confidence_changed_no_record_no_count_and_no_other_field():
    for sid in systems.COUNTRY_SYSTEMS:
        curated = {e["event_id"]: e for e in json.loads(
            (B.SYSTEMS_CURATED / sid / "events.json").read_text(encoding="utf-8"))["events"]}
        doc, system = _served(sid, "events.json"), _served(sid, "system.json")
        assert {e["event_id"] for e in doc["events"]} <= set(curated), sid
        assert system["event_summary"]["recorded_events"] == len(doc["events"])
        for e in doc["events"]:
            raw = curated[e["event_id"]]
            assert set(e) - set(B.DERIVED_EVENT_FIELDS) <= set(B.EVENT_FIELDS) | set(B.OPTIONAL_EVENT_FIELDS), e["event_id"]
            for k in ("date", "date_end", "summary", "effect", "capacity_affected", "asset_class", "cause"):
                assert e[k] == raw.get(k), (e["event_id"], k)
            assert [s["url"] for s in e["sources"]] == [s["url"] for s in raw["sources"]]
        summary = system["evidence_confidence_summary"]
        by = summary["by_category"]
        assert sum(by.values()) + summary["not_assessed"] == len(doc["events"])
        assert by == {c: sum(1 for e in doc["events"] if e["evidence_confidence"]["category"] == c) for c in EC.CATEGORIES}
        assert summary["not_assessed"] == sum(1 for e in doc["events"] if e["evidence_confidence"]["category"] is None)


def _walk_keys(x):
    if isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(x, list):
        for v in x:
            yield from _walk_keys(v)


@needs_build
def test_no_confidence_figure_reaches_the_manifest_or_any_cross_country_file():
    """A count of High-confidence records beside each country is a league table of reporting."""
    for name in ("manifest.json", "gulf.json", "data_quality.json", "recent_evidence.json"):
        p = WEB / "global" / name
        if p.is_file():
            keys = set(_walk_keys(json.loads(p.read_text(encoding="utf-8"))))
            assert not keys & {"evidence_confidence", "evidence_confidence_summary", "by_category"}, name


# --- the theatre's scoring multiplier is a different thing, and unchanged ----------------------------------------

def _sha(text):
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


THEATRE_PINS = {
    "weights": "c96b93aa9b4a15e26f4e93cdde37f69b8547b65c188bcb3e2b188706da01d842",
    "weight_trace": "5fdb10f963e0250b84adfd37a7fd9942922fb75260a04b14580b14a81eb9d8e5",
    "wikipedia_confidence": "41167cade701956596815779ba2a17be5271b6031b323412e230fa2833886faf",
}
REPLACING_IT = ("This is the theatre's scoring multiplier. Evidence Confidence v2 does not replace it; "
                "doing so is a separate decision with its own bar (docs/EVIDENCE_CONFIDENCE_V2.md).")


def test_the_theatres_confidence_multiplier_is_byte_for_byte_unchanged():
    weights = json.loads((ROOT / "methodology" / "scoring.json").read_text(encoding="utf-8"))["confidence_weights"]
    assert {k: v for k, v in weights.items() if k != "_comment"} == {
        "confirmed": 1.0, "probable": 0.75, "possible": 0.45, "unverified": 0.2}, REPLACING_IT
    assert _sha(json.dumps(weights, sort_keys=True, ensure_ascii=False)) == THEATRE_PINS["weights"], REPLACING_IT
    assert _sha(inspect.getsource(build_index._weight_trace)) == THEATRE_PINS["weight_trace"], REPLACING_IT
    assert _sha(inspect.getsource(fetch_wikipedia._confidence)) == THEATRE_PINS["wikipedia_confidence"], REPLACING_IT


def test_the_theatre_weight_reads_the_v1_label_and_ignores_a_v2_category():
    import datetime as dt
    when = dt.date(2024, 3, 1)
    inc = {"date": "2024-03-01", "cause": "kinetic_strike", "status": "unknown", "asset_class": "refinery"}
    for label, weight in (("confirmed", 1.0), ("probable", 0.75), ("possible", 0.45), ("unverified", 0.2), (None, 0.45)):
        plain = build_index._weight_trace({**inc, "confidence": label}, when)
        assert plain["confidence_weight"] == weight
        shadowed = build_index._weight_trace(
            {**inc, "confidence": label, "evidence_confidence": {"category": "PRELIMINARY", "score": 0}}, when)
        assert shadowed == plain
    cite = lambda host: {"url": f"https://{host}/x"}  # noqa: E731
    assert fetch_wikipedia._confidence([cite("a.example"), cite("b.example")]) == "confirmed"
    assert fetch_wikipedia._confidence([cite("a.example"), cite("www.a.example")]) == "probable"
    assert fetch_wikipedia._confidence([]) == "possible"


def test_the_theatre_index_never_imports_evidence_confidence():
    """Checked in a fresh interpreter, so an import by any module the index pulls in counts too."""
    code = ("import sys, pipeline.build_index, pipeline.recovery, pipeline.fetch_wikipedia\n"
            "bad = sorted(m for m in sys.modules if m.endswith('evidence_confidence'))\n"
            "print(','.join(bad))\n")
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-2000:]
    assert r.stdout.strip() == "", f"the theatre index imports {r.stdout.strip()}"
    for module in (build_index, fetch_wikipedia):
        assert "evidence_confidence" not in inspect.getsource(module), module.__name__


def test_a_confidence_typed_into_a_curated_record_is_never_copied():
    raw = {"event_id": "xx-1", "date": "2024-03-01", "region_code": None, "evidence_confidence": {"category": "HIGH"},
           "sources": [{"url": "https://a.example/x", "publisher": "A", "date": None, "language": "en",
                        "source_role": "media", "opened": None}]}
    assert "evidence_confidence" not in B._event(raw, {})
    assert "evidence_confidence" in B.DERIVED_EVENT_FIELDS and "evidence_confidence" not in B.EVENT_FIELDS


# --- the calibration tool (scripts/eci_calibration.py) -----------------------------------------------------

def _script(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _record(i, sources):
    return {"event_id": f"xx-2024-0{i}-named-plant-fire", "summary": f"Summary {i}", "effect": "Effect.",
            "date": f"2024-0{i}-01", "date_end": None, "capacity_affected": None, "sources": sources,
            "evidence_confidence": {"category": "HIGH", "score": 99}, "review": {"disposition": "confirmed"}}


def test_a_blind_packet_never_carries_the_result_the_record_id_or_a_source_address():
    cal = _script("eci_calibration")
    rows = []
    for i, sources in enumerate(([src("operator", site="gridco.example", publisher="GridCo"),
                                  src("wire", site="reuters.example", publisher="Reuters")],
                                 [wire_copy(1)], [post("S4", identity=None)]), start=1):
        record = _record(i, sources)
        rows.append(("country_event", "xx", record["event_id"], record, assess(sources)))
    picked = cal.sample(rows, target=10, seed=22)
    assert sorted(r[2] for r in picked) == sorted(r[2] for r in rows)
    packets = [cal.packet(cal.packet_id(22, r[0], r[2]), r[3]) for r in picked]
    text = json.dumps(packets)
    for p in packets:
        assert set(p) == set(cal.PACKET_FIELDS)
        assert all(set(s) == set(cal.PACKET_SOURCE_FIELDS) for s in p["sources"])
        assert p["packet_id"].startswith("pkt-") and "named-plant" not in p["packet_id"]
    for leak in ("category", "score", "evidence_confidence", "HIGH", "MODERATE", "PRELIMINARY", "http", ".example",
                 "named-plant", "opened", "disposition", "components"):
        assert leak not in text, leak
    wire = next(s for p in packets for s in p["sources"] if s["publisher"] == "Reuters via Outlet 1")
    assert wire["carries_wire"] == "Reuters" and wire["supports"] == ["occurrence", "effect"]
    assert any(s["social_tier"] == "S4" for p in packets for s in p["sources"])
    # The same seed gives the same ids, so labels already written are not orphaned by a re-run.
    assert cal.packet_id(22, "country_event", "a") == cal.packet_id(22, "country_event", "a")
    assert cal.packet_id(22, "country_event", "a") != cal.packet_id(23, "country_event", "a")


def test_cohens_kappa_and_within_one_agreement_are_computed_as_defined():
    cal = _script("eci_calibration")
    a = {f"p{i}": lab for i, lab in enumerate(["HIGH"] * 5 + ["LIMITED"] * 5)}
    assert cal.kappa(a, a) == 1.0
    assert cal.kappa(a, {k: "HIGH" for k in a}) == 0.0, "agreement no better than chance"
    b = dict(a, p0="LIMITED", p5="HIGH")              # 8 of 10 agree; chance agreement is one half
    assert cal.kappa(a, b) == 0.6
    assert cal.kappa(a, {}) is None and cal.kappa({"p0": "HIGH"}, {"p0": "HIGH"}) is None
    assert cal.within_one("HIGH", "MODERATE") and cal.within_one("LIMITED", "PRELIMINARY")
    assert not cal.within_one("HIGH", "LIMITED")
    assert not cal.within_one("DISPUTED", "PRELIMINARY"), "Disputed is off the scale"
    got = cal.agreement(a, b)
    assert (got["packets"], got["exact"], got["within_one"]) == (10, 0.8, 0.8)
    assert got["confusion"]["HIGH"]["LIMITED"] == 1 and got["confusion"]["LIMITED"]["HIGH"] == 1


def test_compare_lists_the_packets_where_two_reviewers_agree_and_the_model_differs():
    cal = _script("eci_calibration")
    model = lambda cat: {"category": cat, "score": 50, "components": {}}  # noqa: E731
    key = {"p1": {"record_id": "r1", "stratum": "xx", "model": model("HIGH")},
           "p2": {"record_id": "r2", "stratum": "xx", "model": model("MODERATE")},
           "p3": {"record_id": "r3", "stratum": "yy", "model": model("LIMITED")}}
    labels = {"ana": {"p1": "HIGH", "p2": "LIMITED", "p3": "LIMITED"},
              "ben": {"p1": "HIGH", "p2": "LIMITED", "p3": "MODERATE"},
              "cy": {"p1": "MODERATE", "p2": "MODERATE"}}
    out = cal.compare(key, labels, {"ana": {"p2": "single origin"}})
    assert [(r["packet_id"], r["reviewers"], r["reviewer_label"], r["model_label"]) for r in out["reviewers_agree_model_differs"]] \
        == [("p2", ["ana", "ben"], "LIMITED", "MODERATE")]
    assert out["reviewers_agree_model_differs"][0]["reasons"]["ana"] == "single origin"
    assert out["reviewer_vs_model"]["ana"]["exact"] == round(2 / 3, 3)
    assert set(out["reviewer_vs_reviewer"]) == {"ana vs ben", "ana vs cy", "ben vs cy"}
    assert out["reviewer_vs_reviewer"]["ana vs cy"]["packets"] == 2
    assert "p2" in cal.markdown(out)


def test_a_label_outside_the_vocabulary_or_for_an_unknown_packet_is_refused(tmp_path):
    cal = _script("eci_calibration")
    (tmp_path / "labels_ana.json").write_text(json.dumps(
        {"p1": {"label": "HIGH", "reason": "r"}, "p2": {"label": "VERY HIGH"}, "p9": {"label": "LOW"}}), encoding="utf-8")
    labels, _reasons, problems = cal.load_labels(tmp_path, {"p1": {}, "p2": {}})
    assert labels == {"ana": {"p1": "HIGH"}} and len(problems) == 2


# --- the theatre shadow study (scripts/confidence_shadow_study.py) --------------------------------------------

def test_the_shadow_study_reads_theatre_citations_conservatively():
    study = _script("confidence_shadow_study")
    assert study.CANDIDATE_WEIGHTS == {"HIGH": 1.0, "MODERATE": 0.75, "LIMITED": 0.45, "PRELIMINARY": 0.2}
    assert study.iso_date("25 January 2024") == "2024-01-25" and study.iso_date("January 25, 2024") == "2024-01-25"
    assert study.iso_date("January 2024") == "2024-01" and study.iso_date("2024-01-25") == "2024-01-25"
    assert study.iso_date("last winter") is None and study.iso_date(None) is None
    assert study.official_domain("https://minenergo.gov.ru/x") and study.official_domain("http://kremlin.ru/events/1")
    for press in ("https://tass.com/x", "https://www.governor-news.example/x", "https://themoscowtimes.com/gov/x"):
        assert not study.official_domain(press), press
    s = study.v2_source({"url": "https://tass.com/x", "publisher": "TASS", "date": "25 January 2024"})
    assert (s["source_role"], s["date"], s["opened"]) == ("media", "2024-01-25", None)
    strike = {"date": "2024-01-24", "status": "unknown", "sources": [
        {"url": "https://a.example/1", "date": "25 January 2024"}, {"url": "https://b.example/2", "date": "25 January 2024"}]}
    r = study.shadow(strike)
    # Two independent reports at the time, no supported effect, nobody recorded opening them: 28 + 16 + 10.
    assert (r["score"], r["category"]) == (54, "LIMITED")
    assert study.effect_specificity({"capacity_affected_mtpa": 2.0}) == "quantified"
    assert study.effect_specificity({"status": "damaged"}) == "described"
    assert study.shadow(dict(strike, conflicting_reports=True))["category"] == "DISPUTED"


def test_the_shadow_study_substitutes_weights_only_for_one_call_and_restores_them(monkeypatch):
    study = _script("confidence_shadow_study")
    before = copy.deepcopy(build_index.SCORING["confidence_weights"])
    seen = {}

    def fake_build(**kwargs):
        seen["weights"] = dict(build_index.SCORING["confidence_weights"])
        seen["labels"] = [i["confidence"] for i in kwargs["incidents"]]
        if kwargs.get("as_of") == "explode":
            raise RuntimeError("the builder failed")
        return ({"esdi": [1.0]},)

    monkeypatch.setattr(build_index, "build", fake_build)
    incidents = [{"incident_id": "a", "confidence": "confirmed"}]
    study.run_index({"incidents": incidents, "as_of": "x"}, {**before, **study.CANDIDATE_WEIGHTS}, {"a": "LIMITED"})
    assert seen["weights"]["LIMITED"] == 0.45 and seen["labels"] == ["LIMITED"]
    assert build_index.SCORING["confidence_weights"] == before, "the substituted weights were left in place"
    assert incidents[0]["confidence"] == "confirmed", "the caller's incidents were relabelled"
    with pytest.raises(RuntimeError):
        study.run_index({"incidents": incidents, "as_of": "explode"}, {**before, **study.CANDIDATE_WEIGHTS}, {"a": "HIGH"})
    assert build_index.SCORING["confidence_weights"] == before, "a failed run left the weights substituted"
    # Without substitution the builder sees exactly the declared weights and labels.
    study.run_index({"incidents": incidents, "as_of": "x"})
    assert seen["weights"] == before and seen["labels"] == ["confirmed"]


def test_the_shadow_study_and_the_calibration_tool_write_no_payload():
    for name in ("confidence_shadow_study", "eci_calibration"):
        text = (ROOT / "scripts" / f"{name}.py").read_text(encoding="utf-8")
        assert "write_json" not in text and "WEB_DATA" not in text and "_mirror_to_web" not in text, name
    study = (ROOT / "scripts" / "confidence_shadow_study.py").read_text(encoding="utf-8")
    assert 'outputs.plan("fixture"' in study, "the study must run as a fixture build, which may not touch data/processed"
    doc = (ROOT / "docs" / "EVIDENCE_CONFIDENCE_V2.md").read_text(encoding="utf-8")
    for marker in ("<!-- shadow-study:begin -->", "<!-- shadow-study:end -->", "<!-- calibration-results:begin -->",
                   "The bar for ever replacing the theatre multiplier", '"theatre_shadow"'):
        assert marker in doc, marker
