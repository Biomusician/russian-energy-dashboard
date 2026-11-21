"""Iteration 22 methodology red team: the pinning tests for its findings on Evidence Confidence v2.

The report reproduced each failure on the real functions. Case ids (B1, F15, ...) are the report's.
Each test here pins the behaviour the lead ruled on, so the failure cannot come back quietly.

  1  "Read by a reviewer" was the research lane's flag, and contradicted the record's review block.
  2  "N independent originating statements" was a count of publishers, and relays reached High.
  3  A self-claim exceeded CLAIM_ONLY in its commonest shapes, and the gate refused the honest status.
  4  A record cited only through Wikipedia read as "Preliminary": a research state shown as evidence.
  5  The methodology said the thresholds were calibrated; no calibration had been run.
"""
import copy
import json
import random
import re
from pathlib import Path

import pytest

from pipeline import build_systems as B, evidence_confidence as EC, systems
from tests.test_iteration22_confidence import (
    EVENT, REVIEWED, _built, _served, asrc, att, post, src)

ROOT = Path(__file__).resolve().parent.parent
needs_build = pytest.mark.skipif(not _built(), reason="the served country payloads predate this version of evidence confidence; run pipeline.run")
UNREVIEWED = {"roles": {"evidence": "accept", "safety": "accept", "taxonomy": "accept"}}     # a country record's review


def assess(sources, specificity="quantified", review=REVIEWED, **kw):
    return EC.assess(sources, EVENT, None, specificity, kw.get("dispute"), review=review)


def ministry(**kw):
    return src("government", site="ministry.example", publisher="Ministry", ref="s1", **kw)


def outlet(n, **kw):
    return src("media", site=f"paper-{n}.example", publisher=f"Paper {n}", **kw)


def served_events():
    for sid in systems.COUNTRY_SYSTEMS:
        for e in _served(sid, "events.json")["events"]:
            yield sid, e


# --- 1. opened during research or review ---------------------------------------------------------------

def test_the_opened_points_come_from_the_source_flag_or_from_the_records_own_review_block():
    unrecorded = [outlet("a", opened=None), outlet("b", opened=None)]
    opened = lambda r: r["components"]["opened"]["points"]                                # noqa: E731
    assert opened(assess(unrecorded, review=None)) == 0
    assert opened(assess(unrecorded, review={"sources_opened_by_reviewer": 0})) == 0
    by_review = assess(unrecorded, review={"sources_opened_by_reviewer": 3})
    assert opened(by_review) == 10
    assert "A cited source was opened during research or review" in by_review["reasons"]
    # Either is enough, and "not recorded" on a source is never read as "not opened".
    assert opened(assess([outlet("a", opened=True)], review=None)) == 10
    assert assess([outlet("a", opened=None)], review={"sources_opened_by_reviewer": 1}) == \
        assess([outlet("a", opened=True)], review={"sources_opened_by_reviewer": 1})
    # A reviewer who opened an anonymous post has still only read an unverified claim.
    assert opened(assess([post("S4", identity=None, opened=None)], review={"sources_opened_by_reviewer": 1})) == 0
    assert opened(assess(unrecorded, review={"sources_opened_by_reviewer": "three"})) == 0


def test_nothing_served_calls_the_component_read_by_a_reviewer():
    m = EC.method()
    assert next(c for c in m["components"] if c["id"] == "opened")["label"] == "Opened during research or review"
    assert "read by a reviewer" not in json.dumps(m).lower()
    assert "read by a reviewer" not in " ".join(assess([outlet("a")])["reasons"]).lower()


@needs_build
def test_no_served_record_whose_review_says_a_reviewer_opened_sources_earns_nothing_for_it():
    checked = 0
    for _sid, e in served_events():
        ec = e["evidence_confidence"]
        if ec["category"] is None or not (e["review"].get("sources_opened_by_reviewer") or 0) > 0:
            continue
        checked += 1
        assert ec["components"]["opened"]["points"] > 0, e["event_id"]
        # ...and the lane's unrecorded flags decide nothing on such a record.
        flagged = copy.deepcopy(e)
        for s in flagged["sources"]:
            if s.get("opened") is None:
                s["opened"] = True
        again = EC.assess(flagged["sources"], e["date"], e.get("date_end"), B.effect_specificity(e), review=e["review"])
        assert again["category"] == ec["category"] and again["score"] == ec["score"], e["event_id"]
    assert checked > 100


# --- 2. independence -----------------------------------------------------------------------------------

def test_b1_to_b4_a_relay_never_adds_an_origin():
    alone = assess([ministry()])
    assert (alone["category"], alone["components"]["origins"]["count"]) == ("MODERATE", 1)
    b1 = assess([ministry(), outlet("a", relays="s1")])
    b2 = assess([ministry(), outlet("a", relays="s1"), outlet("b", relays="s1"), outlet("c", relays="s1")])
    for r in (b1, b2):
        assert (r["category"], r["score"], r["components"]["origins"]["count"]) == ("MODERATE", 75, 1), r
        assert "One originating statement" in r["reasons"]
    # B3, B4: the statement itself is not cited. Two relays of it, declared or grouped by a shared
    # origin, are still that one statement.
    b3 = assess([outlet("a", relays="ministry statement"), outlet("b", relays="ministry statement")])
    b3_origin = assess([outlet("a", origin="ministry statement"), outlet("b", origin="ministry statement")])
    b4 = assess([outlet(n, relays="one statement", opened=None) for n in "abc"])
    for r in (b3, b3_origin, b4):
        assert r["components"]["origins"]["count"] == 1 and r["category"] != "HIGH", r
    # A relay beside a genuinely separate report: two, not three.
    assert assess([ministry(), outlet("a", relays="s1"), outlet("b")])["components"]["origins"]["count"] == 2


def test_b26_b40_and_one_department_are_one_organisation(monkeypatch):
    irna = src("wire", site="en.irna.ir", publisher="IRNA")
    shana = src("government", site="www.shana.ir", publisher="Shana (Petroleum Ministry)")
    assert EC.organisation_of(irna) == EC.organisation_of(shana) == "state-ir"
    assert EC.independent_origins([irna, shana]) == 1                                               # B26
    assert assess([irna, shana])["category"] == "MODERATE"
    doe = src("government", site="www.energy.gov", publisher="U.S. Department of Energy")
    eia = src("government", site="www.eia.gov", publisher="U.S. Energy Information Administration")
    assert EC.independent_origins([doe, eia]) == 1
    # A table entry with a parent: a state utility and the ministry that owns it (B40).
    method = copy.deepcopy(EC.METHOD)
    method["origins"]["organisations"] += [
        {"id": "ministry-x", "domains": ["ministry.example"]},
        {"id": "state-utility", "domains": ["utility.example"], "parent": "ministry-x"}]
    utility = src("operator", site="utility.example", publisher="Utility Co")
    assert EC.independent_origins([utility, ministry()]) == 2, "unknown to the table: two publishers"
    monkeypatch.setattr(EC, "METHOD", method)
    assert EC.organisation_of(utility) == "ministry-x"
    assert EC.independent_origins([utility, ministry()]) == 1
    assert assess([utility, ministry()])["category"] == "MODERATE"
    # Unrelated publishers the table does not know stay apart.
    assert EC.organisation_of(outlet("a")) is None and EC.independent_origins([outlet("a"), outlet("b")]) == 2


def test_a_form_filed_by_an_operator_belongs_to_the_operator_when_the_record_cites_it_too():
    oe417 = src("government", site="doe417.pnnl.gov", publisher="U.S. Department of Energy (CESER), Form OE-417 annual summary",
                path="summaries/2022_Annual_Summary.xls", date=None)
    utility = src("operator", site="mlgw.example", publisher="Memphis Light, Gas and Water")
    assert EC.independent_origins([oe417, utility]) == 1
    assert assess([oe417, utility])["category"] == "MODERATE", "the form and its filer reached High as two origins"
    # Without the filer the form is one origin of its own; beside the press it is a second.
    assert EC.independent_origins([oe417]) == 1
    assert EC.independent_origins([oe417, outlet("a")]) == 2


@needs_build
def test_the_served_oe417_records_are_not_high_on_a_form_and_its_filer():
    for eid in ("us-2022-02-03-tennessee-ice-storm-outages", "us-2022-11-05-michigan-wind-storm-outages",
                "us-2023-04-29-texas-storm-outages"):
        e = next(e for _sid, e in served_events() if e["event_id"] == eid)
        assert e["evidence_confidence"]["components"]["origins"]["count"] == 1, eid
        assert e["evidence_confidence"]["category"] == "MODERATE", eid


def test_b31_a_citation_at_an_origin_already_counted_does_not_raise_the_count():
    site = src("operator", site="utility.example", publisher="Utility Co")
    account = post("S1", handle="utilityco", publisher="Utility Co")
    assert assess([site, account])["components"]["origins"]["count"] == 1                           # B31a
    press_office = src("operator", site="utility.example", publisher="Utility Co press office", path="press/2")
    b31b = assess([site, account, press_office])
    assert b31b["components"]["origins"]["count"] == 1 and b31b["category"] == "MODERATE"
    assert b31b["score"] == assess([site, account])["score"]


def test_a_count_nobody_reviewed_is_a_count_of_publishers_and_is_said_as_one():
    sources = [ministry(), outlet("a"), outlet("b")]
    reviewed, unreviewed, none = assess(sources), assess(sources, review=UNREVIEWED), assess(sources, review=None)
    assert reviewed["components"]["origins"] == {"count": 3, "points": 25, "basis": "reviewed"}
    assert "3 independent originating statements" in reviewed["reasons"] and reviewed["category"] == "HIGH"
    for r in (unreviewed, none):
        assert r["components"]["origins"] == {"count": 3, "points": 25, "basis": "publishers"}
        assert "3 distinct publishers cited; whether they relay one statement was not reviewed" in r["reasons"]
        assert "independent originating" not in json.dumps(r)
    one = assess([outlet("a")], review=None)
    assert "One publisher cited" in one["reasons"]
    assert set(EC.method()["origin_bases"]) == set(EC.ORIGIN_BASES)


def test_a_record_whose_origins_were_not_reviewed_cannot_be_high():
    sources = [ministry(), outlet("a"), outlet("b")]
    r = assess(sources, review=UNREVIEWED)
    assert (r["category"], r["cap"], r["score"]) == ("MODERATE", "origins_not_reviewed", 100)
    assert any("independence of the cited sources has not been reviewed" in x for x in r["reasons"])
    assert assess(sources)["cap"] is None
    # A record that was not going to be High is not touched by the cap.
    low = assess([outlet("a")], "vague", review=UNREVIEWED)
    assert low["cap"] is None and not any("has not been reviewed" in x for x in low["reasons"])
    rng = random.Random(31)
    from tests.test_iteration22_confidence import random_set
    high = 0
    for _ in range(1500):
        s = random_set(rng)
        assert assess(s, review=rng.choice([None, UNREVIEWED, {}]))["category"] != "HIGH", s
        high += assess(s)["category"] == "HIGH"
    assert high, "the generator never produced a record that is High once reviewed"


def test_who_counts_as_having_reviewed_the_origins():
    assert EC.origins_reviewed(REVIEWED)
    assert EC.origins_reviewed({"roles": {"attribution_source": "accept_with_correction"}})
    for review in (None, {}, UNREVIEWED, {"roles": {"attribution_source": "reject"}}, {"roles": None},
                   {"review_status": "blind_reviewed", "sources_opened_by_reviewer": 3}):
        assert not EC.origins_reviewed(review), review


@needs_build
def test_no_served_country_record_claims_independence_or_reaches_high():
    seen = 0
    for sid, e in served_events():
        ec = e["evidence_confidence"]
        seen += 1
        assert ec["components"]["origins"]["basis"] == "publishers", e["event_id"]
        assert ec["category"] != "HIGH", e["event_id"]
        assert "independent originating" not in json.dumps(ec), e["event_id"]
        assert "authoritative" not in json.dumps(ec).lower(), e["event_id"]
    assert seen > 100
    for sid in systems.COUNTRY_SYSTEMS:
        assert _served(sid, "system.json")["evidence_confidence_summary"]["by_category"]["HIGH"] == 0


# --- 3. a self-claim, in the shapes it really takes -----------------------------------------------------

CLAIM = asrc("actor_self_claim", "t.me", publisher="Group X")
STATE_ACTOR = dict(actor="State Y Security Service", actor_type="state")
STATE_CLAIM = asrc("government", "security-service.example", publisher="State Y Security Service")


def test_f2_a_claim_plus_an_outlet_reporting_it_is_claimed_claim_only_and_accepted():
    sources = [CLAIM, asrc("media", "paper-a.example", publisher="Paper a")]
    assert EC.attribution_confidence(att("CLAIMED"), sources) == "CLAIM_ONLY"
    assert EC.attribution_problems(att("CLAIMED"), sources) == [], "the gate refused the honest status"
    for status in ("SUSPECTED", "ASSESSED", "ATTRIBUTED"):                                          # F3, F4
        many = sources + [asrc("wire", "wire-b.example", publisher="Wire b")]
        assert EC.attribution_confidence(att(status), many) == "CLAIM_ONLY"
        assert EC.attribution_problems(att(status), many), status


def test_f8_the_actors_own_outlet_is_the_actors_claim_whatever_role_it_is_given():
    own = asrc("media", "groupx-news.example", publisher="Group X News")
    assert EC.attribution_confidence(att("SUSPECTED"), [own]) == "CLAIM_ONLY"
    assert EC.attribution_problems(att("SUSPECTED"), [own])
    assert EC.attribution_problems(att("CLAIMED"), [own]) == []
    # A name the record lists for the actor is the actor too.
    alias = asrc("media", "resistance-media.example", publisher="Resistance Media Front")
    assert EC.attribution_confidence(att("SUSPECTED"), [alias]) == "LOW"
    assert EC.attribution_confidence(att("SUSPECTED", actor_aliases=["Resistance Media Front"]), [alias]) == "CLAIM_ONLY"
    # A one-word actor is matched whole, never inside another publisher's name.
    assert EC.attribution_confidence(att("SUSPECTED", actor="Aurora"), [asrc("media", "aurora-daily.example", publisher="Aurora Daily")]) == "LOW"
    assert EC.attribution_confidence(att("SUSPECTED", actor="Aurora"), [asrc("media", "aurora.example", publisher="Aurora")]) == "CLAIM_ONLY"


def test_f15_f17_a_state_actors_own_announcement_is_a_claim_not_a_formal_attribution():
    assert EC.attribution_confidence(att("ATTRIBUTED", **STATE_ACTOR), [STATE_CLAIM]) == "CLAIM_ONLY"      # F15
    assert any("ATTRIBUTED needs a formal government" in p or "no credible source" in p
               for p in EC.attribution_problems(att("ATTRIBUTED", **STATE_ACTOR), [STATE_CLAIM]))
    assert EC.attribution_problems(att("CLAIMED", **STATE_ACTOR), [STATE_CLAIM]) == []
    # F16: a wire carrying the claim under a borrowed basis is still press coverage of the claim...
    wire = asrc("wire", "wire-a.example", publisher="Wire a")
    # F17: a firm that only notes the claim, declared as such, is the claim again.
    noting = asrc("cyber_firm", "firm-a.example", publisher="Firm a", attribution_basis="actor_self_claim")
    for sources in ([STATE_CLAIM, wire], [STATE_CLAIM, noting], [STATE_CLAIM, wire, noting]):
        assert EC.attribution_confidence(att("ATTRIBUTED", **STATE_ACTOR), sources) == "CLAIM_ONLY", sources
        assert EC.attribution_problems(att("ATTRIBUTED", **STATE_ACTOR), sources), sources
    # A firm with a finding of its own, beside the claim, is one technical attribution: Low, and
    # never the formal attribution ATTRIBUTED needs.
    finding = asrc("cyber_firm", "firm-a.example", publisher="Firm a")
    assert EC.attribution_confidence(att("ASSESSED", **STATE_ACTOR), [STATE_CLAIM, finding]) == "LOW"
    assert EC.attribution_problems(att("ATTRIBUTED", **STATE_ACTOR), [STATE_CLAIM, finding])


def test_the_shape_reviewers_were_given_for_a_reported_claim_validates_as_claim_only():
    """A wire or media report of a claim, marked `attribution_basis: actor_self_claim`, with the
    record's basis listed as ["actor_self_claim"]: no claim source of the actor's own is cited."""
    reported = [asrc("wire", "wire-a.example", publisher="Wire a", attribution_basis="actor_self_claim"),
                asrc("media", "paper-b.example", publisher="Paper b", attribution_basis="actor_self_claim")]
    a = att("CLAIMED", basis=["actor_self_claim"])
    assert EC.attribution_confidence(a, reported) == "CLAIM_ONLY"
    assert EC.attribution_problems(a, reported) == []
    assert EC.attribution_problems(att("ATTRIBUTED", basis=["actor_self_claim"]), reported)


def test_claimed_understates_only_when_a_source_has_a_finding_of_its_own():
    undeclared = asrc("media", "paper-a.example", publisher="Paper a")
    understates = lambda sources: any("understates" in p for p in EC.attribution_problems(att("CLAIMED"), sources))  # noqa: E731
    assert not understates([CLAIM, undeclared])
    assert not understates([CLAIM, dict(undeclared, source_role="aggregator")])
    for own in (dict(undeclared, attribution_basis="media_investigation"), dict(undeclared, attribution_basis="government"),
                asrc("government", "ministry.example"), asrc("law_enforcement", "police.example"),
                asrc("cert", "cert.example"), asrc("cyber_firm", "firm.example"), asrc("researcher", "uni.example")):
        assert understates([CLAIM, own]), own


def test_a_declared_relay_of_a_claim_is_the_claim():
    claim = dict(CLAIM, ref="c1")
    relay = asrc("cyber_firm", "firm-a.example", publisher="Firm a", relays="c1", ref="c2")
    second = asrc("researcher", "lab.example", publisher="Lab", relays="c2")
    assert EC.attribution_confidence(att("ASSESSED"), [claim, relay, second]) == "CLAIM_ONLY"
    assert EC.attribution_confidence(att("ASSESSED"), [claim, dict(relay, relays=None)]) == "LOW"


def test_no_set_of_claims_and_relays_of_a_claim_yields_more_than_claim_only():
    rng = random.Random(33)
    roles = ["actor_self_claim", "wire", "media", "specialist_media", "industry", "aggregator", "government", "cyber_firm",
             "researcher", "operator", "law_enforcement"]
    for _ in range(1500):
        sources = [dict(CLAIM, ref="c0")]
        for n in range(rng.randrange(1, 6)):
            role = rng.choice(roles)
            s = asrc(role, f"site{n}.example", publisher=f"Publisher {n}", ref=f"r{n}")
            kind = rng.choice(["declared", "relays", "by_actor", "undeclared_press"])
            if kind == "declared":
                s["attribution_basis"] = "actor_self_claim"
            elif kind == "relays":
                s["relays"] = rng.choice(["c0"] + [x["ref"] for x in sources if x.get("ref")])
            elif kind == "by_actor":
                s["publisher"] = rng.choice(["Group X", "Group X Media Office"])
            else:
                s["source_role"] = rng.choice(["wire", "media", "specialist_media", "industry", "aggregator"])
            sources.append(s)
        rng.shuffle(sources)
        for status in ("CLAIMED", "SUSPECTED", "ASSESSED", "ATTRIBUTED"):
            assert EC.attribution_confidence(att(status), sources) == "CLAIM_ONLY", (status, sources)
        assert EC.attribution_problems(att("ATTRIBUTED"), sources), sources
        assert EC.attribution_problems(att("CLAIMED"), sources) == [], sources


# --- 4. cited through a discovery aid only -------------------------------------------------------------

WIKIPEDIA = src("media", site="en.wikipedia.org", publisher="Wikipedia", date="2026-10-30")
NOT_YET = "cited through a discovery aid only; a primary source is not yet attached"


@pytest.mark.parametrize("sources", [
    [WIKIPEDIA], [dict(WIKIPEDIA, source_role="dataset")], [dict(WIKIPEDIA, origin="its own reporting")],
    [src("aggregator", site="feeds.example", publisher="Energy Feed")],
    [WIKIPEDIA, src("aggregator", site="feeds.example", publisher="Energy Feed")],
    [WIKIPEDIA, src("media", site="indexbox.io", publisher="IndexBox")]])
def test_a_record_cited_only_through_a_discovery_aid_is_not_assessed_never_preliminary(sources):
    for review in (None, REVIEWED, {"sources_opened_by_reviewer": 2}):
        r = assess(sources, review=review)
        assert r["category"] is None and r["reason"] == NOT_YET
        assert r["label"] == "Not assessed" and r["score"] is None and r["cap"] is None
        assert "PRELIMINARY" not in json.dumps(r) and "Preliminary" not in json.dumps(r)
        assert set(v["points"] for v in r["components"].values()) == {None}, "not assessed is null, never zero"


def test_one_real_source_beside_the_discovery_aid_is_assessed():
    assert assess([WIKIPEDIA, src("media")])["category"] is not None
    assert assess([WIKIPEDIA, post("S4", identity=None)])["category"] == "PRELIMINARY"
    assert assess([WIKIPEDIA, src("dataset", site="eventdata.example")])["category"] == "PRELIMINARY"
    assert assess([src("media")])["reason"] is None
    # A source that backs neither occurrence nor effect does not make a discovery-aid record assessed.
    assert assess([WIKIPEDIA, src("cyber_firm", site="lab.example", supports=["attribution"])])["category"] is None


def test_the_statement_says_what_the_category_describes_and_what_it_does_not():
    statement = EC.method()["statement"]
    assert "describes the sources this record cites, not everything published about the event" in statement
    assert "does not cover the cause, or who was responsible" in statement
    assert "quality of the public evidence" not in statement
    assert EC.method()["not_assessed"]["discovery_aid_only"] == NOT_YET


def test_the_country_summary_counts_not_assessed_apart_from_every_category():
    events = [{"evidence_confidence": assess([WIKIPEDIA])}, {"evidence_confidence": assess([src("media")], review=None)},
              {"evidence_confidence": assess([WIKIPEDIA])}]
    s = B.evidence_confidence_summary(events)
    assert s["not_assessed"] == 2 and sum(s["by_category"].values()) == 1
    assert s["by_category"]["PRELIMINARY"] == 0 and s["not_assessed_reason"] == NOT_YET
    assert "researched" in s["note"]


@needs_build
def test_no_served_record_whose_only_citations_are_discovery_aids_carries_a_category():
    found = 0
    for sid, e in served_events():
        only_aids = all(EC.is_discovery_aid(s) for s in e["sources"])
        ec = e["evidence_confidence"]
        assert (ec["category"] is None) == only_aids, e["event_id"]
        if only_aids:
            found += 1
            assert ec["reason"] == NOT_YET and ec["score"] is None
    assert found, "no discovery-aid-only record is served any more: retire this guard deliberately"
    for sid in systems.COUNTRY_SYSTEMS:
        system = _served(sid, "system.json")
        assert "this record cites" in system["evidence_confidence_summary"]["statement"]


# --- 5. nothing says the thresholds were calibrated until a calibration is recorded --------------------

# Iteration 23 (F5): the status says the first run was performed and did not pass, not only that the
# thresholds are uncalibrated, which read as if no calibration had been attempted.
PROVISIONAL = "provisional: thresholds not calibrated; calibration run 1 (19 November 2026) was performed and did not pass"


def test_while_the_version_is_a_draft_the_method_is_served_as_provisional(monkeypatch):
    assert EC.METHOD["version"].endswith("-draft"), "a calibration was recorded: update the results block and this test"
    assert EC.method()["status"] == PROVISIONAL == EC.calibration_status()
    released = copy.deepcopy(EC.METHOD)
    released["version"] = "2.0"
    monkeypatch.setattr(EC, "METHOD", released)
    assert EC.method()["status"] != PROVISIONAL and "calibrated" in EC.method()["status"]


def test_no_document_says_the_thresholds_were_calibrated_while_the_results_are_not_recorded():
    doc = (ROOT / "docs" / "EVIDENCE_CONFIDENCE_V2.md").read_text(encoding="utf-8")
    results = doc.split("<!-- calibration-results:begin -->")[1].split("<!-- calibration-results:end -->")[0]
    # A run that failed keeps the draft; only a recorded pass may drop it.
    passed = re.search(r"Result:\s*calibrated", results) is not None
    assert (not passed) == EC.METHOD["version"].endswith("-draft"), "the results block and the version disagree"
    if passed:
        return
    texts = [p for p in (ROOT / "docs").glob("*.md")] + [ROOT / "methodology" / "evidence_confidence.json",
                                                          ROOT / "pipeline" / "evidence_confidence.py"]
    for path in texts:
        text = path.read_text(encoding="utf-8")
        # The claim itself, wherever it sits: a "not" elsewhere in the sentence does not excuse it
        # (a mutant that put the claim beside the word "provisional" used to survive this test).
        m = re.search(r"threshold\w*\s+(?:were|was|are|is|have\s+been|has\s+been)\s+calibrated", text, re.I)
        assert not m, f"{path.name} says a calibration happened: {m.group(0)!r}"
    assert "provisional" in (ROOT / "docs" / "GLOBAL_IMPACT_METHODOLOGY.md").read_text(encoding="utf-8")


# --- 14. a dispute: the denier is not support, and nothing off the scale outweighs the scale ------------

def test_d8_a_source_that_disputes_a_claim_never_backs_it():
    reports = [outlet("a"), outlet("b")]
    denial = src("operator", site="gridco.example", publisher="GridCo", disputes=["occurrence"])
    d8 = assess(reports + [denial])                                   # `supports` unset: it used to back the event
    d9 = assess(reports + [dict(denial, supports=[])])
    assert d8 == d9 and d8["category"] == "DISPUTED"
    # The 40 points and the third origin were the denial. Neither is there now.
    assert d8["components"]["directness"] == {"tier": "independent", "points": 28}
    assert d8["components"]["origins"]["count"] == 2
    # It disputes the occurrence and still says what the effect was not: it backs neither claim it disputes.
    both = dict(denial, disputes=["occurrence", "effect"], supports=["occurrence", "effect"])
    assert assess(reports + [both])["components"]["directness"]["tier"] == "independent"


def test_no_shadow_weight_for_an_incident_off_the_scale_exceeds_the_lowest_mapped_category():
    from tests.test_iteration22_confidence import _script
    study = _script("confidence_shadow_study")
    assert set(study.OFF_SCALE) == {"DISPUTED", "NOT_ASSESSED"} == set(study.OFF_SCALE_WEIGHTS)
    assert max(study.OFF_SCALE_WEIGHTS.values()) <= min(study.CANDIDATE_WEIGHTS.values())
    assert set(study.SHADOW_WEIGHTS) == set(study.V2_LABELS)
    strike = {"date": "2024-01-24", "status": "unknown", "sources": [{"url": "https://en.wikipedia.org/wiki/X", "date": "25 January 2024"}]}
    assert study.shadow(strike)["category"] is None, "a strike cited through Wikipedia only is not assessed"


def test_a_disputed_record_shows_no_total_and_says_it_is_contested_first():
    sources = [ministry(), outlet("a"), outlet("b")]
    r = assess(sources, dispute={"about": "effect"})
    assert r["category"] == "DISPUTED" and r["score"] is None, "a contested record showed a total"
    assert r["reasons"][0] == "Credible sources disagree" and "not a settled reading" in r["reasons"][1]
    assert not any("Held at" in x for x in assess(sources, review=UNREVIEWED, dispute={"about": "effect"})["reasons"])
    # D6 and a value outside the vocabulary are read as a dispute about the record; a dispute about
    # the cause or about who did it is not one about whether it happened.
    for about in ("Effect", "figure", ["effect", "cause"]):
        assert assess(sources, dispute={"about": about})["category"] == "DISPUTED", about
    for about in ("cause", "attribution", "ai_involvement"):
        assert assess(sources, dispute={"about": about})["category"] == "HIGH", about
    # D13: a string is one claim, not something to ignore.
    denial = src("operator", site="gridco.example", publisher="GridCo", disputes="occurrence", supports=[])
    assert assess([outlet("a"), denial])["category"] == "DISPUTED"
    assert EC.dispute_problems({"about": "figure"}) and EC.dispute_problems("accounts differ") and EC.dispute_problems({})
    assert EC.dispute_problems({"about": ["effect", "cause"]}) == [] == EC.dispute_problems(None)


# --- 9. who is speaking is said plainly -----------------------------------------------------------------

PARTY = "The first-party source is the affected party itself"


def test_no_label_calls_a_source_authoritative_or_independent_and_a_partys_own_account_is_said():
    for tier in EC.METHOD["tiers"].values():
        assert "authoritative" not in tier["label"].lower() and "independent" not in tier["label"].lower()
    operator = src("operator", site="gridco.example", publisher="GridCo")
    assert PARTY in assess([operator])["reasons"]
    assert PARTY in assess([operator, outlet("a")])["reasons"], "press beside the operator does not make it a third party"
    for sources in ([src("regulator", site="reg.example")], [outlet("a")], [operator, src("regulator", site="reg.example")]):
        assert PARTY not in assess(sources)["reasons"], sources


# --- 13, 11, 12. attribution: the status, relays, and who may corroborate -------------------------------

A_GOV = asrc("government", "ministry.example", publisher="Ministry", ref="g1")
A_FIRM = asrc("cyber_firm", "firm-a.example", publisher="Firm a")
conf = EC.attribution_confidence


def test_h1_h2_attribution_confidence_never_says_more_than_the_status():
    assert conf(att("ATTRIBUTED"), [A_GOV, A_FIRM]) == "HIGH"
    assert conf(att("ASSESSED"), [A_GOV, A_FIRM]) == "MODERATE"
    assert conf(att("SUSPECTED"), [A_GOV, A_FIRM]) == "LOW"                                          # H1
    assert conf(att("SUSPECTED"), [CLAIM]) == "CLAIM_ONLY" and conf(att("SUSPECTED"), []) == "NOT_ESTABLISHED"
    assert set(EC.METHOD["attribution"]["status_ceiling"]) == {"SUSPECTED", "ASSESSED"}
    # H2: a competing attribution on the record is a dispute, whatever the status says.
    assert conf(att("ATTRIBUTED", competing=[{"actor": "Group Y"}]), [A_GOV, A_FIRM]) == "DISPUTED"


def test_g1_to_g8_a_relayed_attribution_is_one_attribution_and_never_a_second(monkeypatch):
    wire_gov = asrc("wire", "wire-a.example", publisher="Wire a", attribution_basis="government")
    wire_police = asrc("wire", "wire-b.example", publisher="Wire b", attribution_basis="law_enforcement")
    outlet_victim = asrc("media", "paper-c.example", publisher="Paper c", attribution_basis="victim_operator")
    a = att("ATTRIBUTED")
    assert conf(a, [wire_gov]) == "MODERATE"                                                         # G1
    assert conf(a, [wire_gov, wire_police]) == "MODERATE", "two outlets on one press conference"     # G2
    assert conf(a, [wire_gov, outlet_victim]) == "MODERATE"                                          # G3
    assert conf(a, [wire_gov, wire_police, outlet_victim]) == "MODERATE"
    # A carried official attribution beside a firm's own finding is two attributions.
    assert conf(a, [wire_gov, A_FIRM]) == "HIGH"
    # G5, G6: a source that says it relays the cited statement is that statement again.
    relay = asrc("wire", "wire-a.example", publisher="Wire a", attribution_basis="media_investigation", relays="g1")
    assert conf(a, [A_GOV, relay]) == "MODERATE"
    assert conf(a, [A_GOV, dict(A_FIRM, relays="g1")]) == "MODERATE"
    assert conf(a, [A_GOV, dict(A_FIRM, relays="something not cited")]) == "HIGH"
    # G7: one joint advisory on two agencies' sites, grouped by the reviewer.
    joint = [asrc("government", "agency-a.example", publisher="Agency A", origin="joint advisory"),
             asrc("law_enforcement", "agency-b.example", publisher="Agency B", origin="joint advisory")]
    assert conf(a, joint) == "MODERATE"
    # G8: a ministry and the state utility it owns.
    utility = asrc("operator", "utility.example", publisher="Utility Co")
    assert conf(a, [A_GOV, utility]) == "HIGH", "unknown to the table: two organisations"
    method = copy.deepcopy(EC.METHOD)
    method["origins"]["organisations"] += [{"id": "ministry-x", "domains": ["ministry.example"]},
                                           {"id": "state-utility", "domains": ["utility.example"], "parent": "ministry-x"}]
    monkeypatch.setattr(EC, "METHOD", method)
    assert conf(a, [A_GOV, utility]) == "MODERATE"


def test_f12_f13_posts_datasets_and_unknown_roles_never_corroborate_an_attribution():
    a = att("ASSESSED")
    s3 = lambda h: post("S3", role="researcher", handle=h, publisher=h, supports=["attribution"])     # noqa: E731
    assert conf(a, [s3("osint1"), s3("osint2")]) == "LOW"                                            # F12
    assert conf(a, [asrc("dataset", "data.example", publisher="Data"), asrc("think_tank", "tank.example", publisher="Tank")]) == "LOW"
    assert conf(a, [asrc("think_tank", "a.example", publisher="A"), asrc("think_tank", "b.example", publisher="B")]) == "LOW"  # G16
    # H8, H9: one firm on its blog and its own account, or on a second domain, is one firm.
    firm_post = post("S1", role="cyber_firm", handle="firma", publisher="Firm a", supports=["attribution"])
    assert conf(a, [A_FIRM, firm_post]) == "LOW"
    assert conf(a, [A_FIRM, asrc("cyber_firm", "firm-a-reports.example", publisher="Firm a")]) == "LOW"
    assert conf(a, [A_FIRM, asrc("cyber_firm", "firm-b.example", publisher="Firm b")]) == "MODERATE"


# --- 10. a later formal account, and a missing date -----------------------------------------------------

def test_c2_a_later_formal_account_is_not_marked_down_against_a_same_day_line():
    dated = lambda r: r["components"]["contemporaneous"]                                             # noqa: E731
    final = assess([src("regulator", site="reg.example", publisher="Regulator", date="2024-11-10")])
    same_day = assess([src("operator", site="gridco.example", publisher="GridCo", date="2024-03-01")])
    assert final["score"] >= same_day["score"], "a regulator's final report scored below a same-day line"   # C2, C3
    assert dated(final) == {"points": 10, "dated": "later_formal_account"}
    assert "A dated formal account, published later" in final["reasons"] and "Reported at the time" not in final["reasons"]
    assert dated(same_day) == {"points": 10, "dated": "at_the_time"}
    # Press months later, an operator's later line, and a forecast are not formal accounts.
    assert dated(assess([src("media", date="2024-11-10")])) == {"points": 0, "dated": "outside_window"}
    late_operator = src("operator", site="gridco.example", publisher="GridCo", date="2024-11-10")
    assert dated(assess([late_operator]))["dated"] == "outside_window"
    assert dated(assess([src("government", site="gov.example", date="2024-01-01")]))["dated"] == "outside_window"
    # ...unless the source says it is one (an operator's regulatory filing).
    assert dated(assess([dict(late_operator, formal_account=True)]))["dated"] == "later_formal_account"
    # A missing date is not recorded, and said.
    undated = assess([src("media", date=None)])
    assert dated(undated) == {"points": 0, "dated": "not_recorded"}
    assert "No cited source carries a date: not recorded" in undated["reasons"]
    assert EC.source_problems(src("media", date="12 December 2023")), "an unreadable date silently lost the points"   # C11


# --- 17. the points are points --------------------------------------------------------------------------

def test_nothing_served_presents_the_points_as_a_percentage_or_out_of_a_hundred():
    served = json.dumps([EC.method(), assess([ministry(), outlet("a")]), assess([outlet("a")], review=None),
                         B.evidence_confidence_summary([])])
    for bad in ("/100", "/ 100", "out of 100", "%", "percent of", "per cent"):
        assert bad not in served, bad
    assert "not a percentage" in json.dumps(EC.method()["properties"])
    meaning = {c["id"]: c["meaning"] for c in EC.METHOD["categories"]}
    # The meanings describe what the rules produce (C1, A5): High is about reviewed independence,
    # not a specific effect, and Preliminary includes a single bare report.
    assert "reviewer has checked" in meaning["HIGH"] and "specific reported effect" not in meaning["HIGH"]
    assert "single report" in meaning["PRELIMINARY"] and "not been reviewed" in meaning["MODERATE"]


# --- 6, 8, 21. one statement under two addresses, and typing that is cross-checked ----------------------

def test_b9_to_b21_one_statement_cited_twice_is_one_origin():
    count = lambda *s: EC.independent_origins(list(s))                                               # noqa: E731
    reuters = src("wire", site="www.reuters.com", publisher="Reuters")
    archived = src("media", site="web.archive.org", path="web/20240302000000/https://www.reuters.com/a", publisher="Internet Archive")
    amp = src("media", site="www-reuters-com.cdn.ampproject.org", path="c/s/www.reuters.com/a", publisher="AMP cache")
    assert EC.origin_of(archived) == EC.origin_of(amp) == EC.origin_of(reuters) == "wire:Reuters"   # B10, B11
    assert count(reuters, src("media", site="www.msn.com", publisher="MSN")) == 1                    # B12
    assert count(reuters, src("media", site="bit.ly", publisher=""), src("media", site="t.co", publisher="")) == 1   # B32
    assert count(src("wire", site="apnews.com", publisher="AP News"), src("media", site="paper.example", publisher="The Paper (AP)")) == 1  # B13
    assert count(src("wire", site="tass.com", publisher="TASS"), src("media", site="o1.example", publisher="Outlet 1 (TASS)"),
                 src("media", site="o2.example", publisher="Outlet 2, citing TASS")) == 1          # B14
    assert count(src("official", site="spa.gov.sa", publisher="Saudi Press Agency"),
                 src("media", site="o1.example", publisher="Outlet 1 (SPA)")) == 1                   # B15
    assert count(reuters, src("media", site="o1.example", publisher="Outlet 1", origin="Reuters")) == 1   # B16
    assert count(outlet("a"), dict(WIKIPEDIA, origin="its own reporting")) == 1                      # B19
    for aid in ("news.google.com", "www.wikiwand.com"):                                              # B20, B21
        assert count(outlet("a"), src("media", site=aid, publisher="A mirror")) == 1, aid
    # B9, B36: one account under two platform names, with and without its @.
    x = post("S1", handle="@UtilityCo ", publisher="Utility Co on X")
    twitter = post("S1", handle="utilityco", publisher="UtilityCo (Twitter)")
    twitter["social"]["platform"], twitter["url"] = "twitter", "https://twitter.com/utilityco/status/1"
    assert EC.origin_of(x) == EC.origin_of(twitter) == "social:x:utilityco" and count(x, twitter) == 1


def test_b22_b24_a_channel_typed_as_a_website_is_still_a_channel():
    channel = src("media", site="t.me", path="anon_channel/123", publisher="Anon channel")           # typed web
    r = assess([channel])
    assert (r["category"], r["components"]["directness"]["tier"]) == ("PRELIMINARY", "unverified")  # B22
    assert assess([channel, outlet("a")])["components"]["origins"]["count"] == 1                     # B23b
    other = src("media", site="t.me", path="s/other_channel/5", publisher="Other")
    assert EC.origin_of(channel) == "social:telegram:anon_channel" != EC.origin_of(other)            # B23
    b24 = post("S4", role="government", identity=None)
    b24["medium"] = "Social"
    assert EC.tier_of(b24) == "unverified"
    # C18, C19: a basis made of badge words establishes nothing.
    for basis in ("Verified account", "blue tick", "verified_badge", "Official account on X", "has the gold checkmark"):
        assert EC.tier_of(post("S1", identity=basis)) == "unverified", basis
    assert EC.tier_of(post("S1", identity="linked from the operator's own website")) == "direct"
    # The gate refuses what scoring can only read conservatively.
    for bad in (channel, src("media", medium="Podcast"), src("think_tank"), src("media", supports="no_attribution"),
                src("media", disputes="occurrence"), src("media", site="bit.ly"), post("S9")):
        assert EC.source_problems(bad), bad
    assert EC.source_problems(src("media")) == [] == EC.source_problems(post("S2"))


def test_b34_b35_hosts_under_a_shared_suffix_are_separate_publishers():
    count = lambda *s: EC.independent_origins(list(s))                                               # noqa: E731
    a = src("government", site="ecologie.gouv.fr", publisher="Ministry A")
    b = src("government", site="www.interieur.gouv.fr", publisher="Ministry B")
    assert count(a, b) == 2                                                                          # B34
    assert count(a, src("government", site="www.ecologie.gouv.fr", publisher="Ministry A", path="second")) == 1
    assert count(src("media", site="writer-one.substack.com", publisher="Writer One"),
                 src("media", site="writer-two.substack.com", publisher="Writer Two")) == 2          # B35
    # The organisation table still makes one state's bodies one voice.
    assert count(src("government", site="moe.gov.sa", publisher="Ministry of Energy"),
                 src("official", site="www.spa.gov.sa", publisher="Saudi Press Agency")) == 1


# --- the calibration that would lift "provisional" (finding 16) -----------------------------------------

def _cal():
    from tests.test_iteration22_confidence import _script
    return _script("eci_calibration")


def test_the_reviewer_is_given_the_question_and_neutral_labels_not_the_models_rubric():
    cal = _cal()
    text = cal.INSTRUCTIONS.lower()
    for label in cal.LABELS:
        assert label.lower() in text
    # Nothing of the rubric: no rule about origins, wires or tiers, no points and no threshold.
    for rubric in ("originating", "wire", "independent", "corroborat", "first-party", "official", "secondary",
                   "unverified", "points", "threshold", "single-origin", "quantified"):
        assert rubric not in text, rubric
    assert not re.search(r"\d", cal.INSTRUCTIONS.replace("labels_<your name>.json", "")), "a number in the instructions"
    for c in EC.METHOD["categories"] + [EC.METHOD["disputed"]]:
        for sentence in c["meaning"].split(". "):
            assert sentence.strip(". ").lower() not in text, sentence
    assert "not who or what caused it" in text and "method file" in text


def _rows(n, model_category):
    rows = []
    for i in range(n):
        sources = [src("operator", site=f"op{i}.example", publisher=f"Operator {i}")] if i % 2 else \
            [src("media", site=f"paper{i}.example", publisher=f"Paper {i}")]
        if i % 7 == 0:
            sources = [post("S4", identity=None, handle=f"anon{i}", publisher=f"Anon {i}")]
        record = {"event_id": f"r{i:03d}", "summary": "s", "effect": "e", "date": EVENT, "sources": sources}
        rows.append(("country_event", "xx" if i % 3 else "yy", record["event_id"], record, {"category": model_category(i)}))
    return rows


def test_the_calibration_sample_is_never_drawn_by_the_models_own_category():
    cal = _cal()
    assert cal.TARGET >= 60
    one = cal.sample(_rows(200, lambda i: "HIGH"), cal.TARGET, 22)
    other = cal.sample(_rows(200, lambda i: ("HIGH", "MODERATE", "LIMITED", "PRELIMINARY")[i % 4]), cal.TARGET, 22)
    assert [r[2] for r in one] == [r[2] for r in other], "the draw moved when only the model's labels changed"
    assert len(one) == cal.TARGET == len({r[2] for r in one})
    # Every country and every kind of citation present is in front of the reviewers.
    assert {(r[1], cal.source_profile(r[3])) for r in one} == {(r[1], cal.source_profile(r[3])) for r in _rows(200, lambda i: "HIGH")}
    assert cal.sample(_rows(200, lambda i: "HIGH"), cal.TARGET, 23) != one
    # A record the model does not assess has no label to compare and is left out.
    some = cal.sample(_rows(10, lambda i: None if i < 4 else "LIMITED"), cal.TARGET, 22)
    assert sorted(r[2] for r in some) == [f"r{i:03d}" for i in range(4, 10)]


def test_the_source_profile_reads_the_typed_fields_only():
    cal = _cal()
    press = {"sources": [src("media")]}
    assert cal.source_profile(press) == "press_or_secondary"
    assert cal.source_profile({"sources": [src("media"), src("regulator", site="reg.example")]}) == "first_party"
    assert cal.source_profile({"sources": [src("actor_self_claim", site="t.me")]}) == "actor_claim"
    assert cal.source_profile({"sources": [src("media"), post("S3")]}) == "social"
    assert cal.source_profile({"sources": [src("media", disputes=["occurrence"])]}) == "disputed"
    assert cal.source_profile(dict(press, dispute={"about": "effect"})) == "disputed"
    assert cal.source_profile(dict(press, evidence_confidence={"category": "HIGH"})) == "press_or_secondary"


def test_the_calibration_draws_on_imported_impact_records_when_the_corpus_is_there(tmp_path):
    cal = _cal()
    assert cal.IMPACT_CURATED == ROOT / "data" / "curated" / "global_impacts" / "events.json"
    assert list(cal.impact_records(tmp_path / "absent.json")) == []
    record = {"impact_id": "imp-1", "country_a3": "UKR", "date": EVENT, "effect_specificity": "quantified",
              "sources": [ministry(), outlet("a"), outlet("b")], "review": REVIEWED, "dispute": None}
    path = tmp_path / "events.json"
    path.write_text(json.dumps({"events": [record, {"impact_id": "no-sources", "date": EVENT, "sources": []}]}), encoding="utf-8")
    (kind, stratum, rid, _record, model), = list(cal.impact_records(path))
    assert (kind, stratum, rid) == ("impact_record", "UKR", "imp-1")
    # Its own review block is read: the source-and-attribution reviewer checked its origins.
    assert model["components"]["origins"]["basis"] == "reviewed" and model["category"] == "HIGH"
    # A candidate already imported is not drawn twice.
    lane = tmp_path / "queue" / "lane"
    lane.mkdir(parents=True)
    (lane / "candidates.json").write_text(json.dumps([record, dict(record, impact_id="imp-2")]), encoding="utf-8")
    assert [r[2] for r in cal.impact_candidates(tmp_path / "queue", imported={"imp-1"})] == ["imp-2"]


def test_compare_writes_a_result_that_names_no_record():
    cal = _cal()
    model = lambda cat: {"category": cat, "score": 50, "components": {}}                              # noqa: E731
    key = {"method_version": EC.METHOD["version"], "target": 60, "sample": {"population": 3},
           "packets": {"pkt-1": {"record_id": "xx-named-plant", "stratum": "xx", "model": model("MODERATE")},
                       "pkt-2": {"record_id": "yy-named-plant", "stratum": "yy", "model": model("LIMITED")}}}
    labels = {"ana": {"pkt-1": "MODERATE", "pkt-2": "MODERATE"}, "ben": {"pkt-1": "MODERATE", "pkt-2": "MODERATE"}}
    block = cal.result_block(cal.compare(key["packets"], labels), key, "2026-11-19")
    assert block["packets"] == 2 and block["reviewers"] == 2 and block["reviewers_agree_model_differs"] == 1
    assert block["model_labels"]["MODERATE"] == 1 and block["reviewer_vs_model"]["ana"]["exact"] == 0.5
    assert block["decision"] is None, "the tool does not decide; the owner does"
    assert "named-plant" not in json.dumps(block) and "pkt-" not in json.dumps(block)
    assert len(block["limits"]) == 2
