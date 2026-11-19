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
needs_build = pytest.mark.skipif(not _built(), reason="the served country payloads predate evidence confidence; run pipeline.run")
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

PROVISIONAL = "provisional: thresholds not calibrated"


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
    not_run = "Not yet run" in results
    assert not_run == EC.METHOD["version"].endswith("-draft"), "the results block and the version disagree"
    if not not_run:
        return
    texts = [p for p in (ROOT / "docs").glob("*.md")] + [ROOT / "methodology" / "evidence_confidence.json",
                                                          ROOT / "pipeline" / "evidence_confidence.py"]
    for path in texts:
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"[^.\n]*\b(?:were|was|are|is|been) calibrated\b[^.\n]*", text):
            sentence = m.group(0).lower()
            if "threshold" in sentence and "not" not in sentence:
                raise AssertionError(f"{path.name} says a calibration happened: {m.group(0).strip()!r}")
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
