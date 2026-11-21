"""Iteration 23: the impact-layer, evidence-confidence, country-system, Compare and What's New findings
of the iteration-23 red teams that were bugs, documentation drift or a misleading display.

Each test names its finding. Pipeline rules are called directly; the frontend is bundled from
web/src and run in Node (tests/test_iteration21_testarch.py), so the mutation campaign
(scripts/mutation_campaign.py, ITER23_IMPACT_MUTATIONS) breaks the code a reader's browser runs.
Served-data checks read the committed payloads.
"""
import copy
import json
import re
from pathlib import Path

import pytest

from pipeline import build_systems as B
from pipeline import evidence_confidence as EC
from pipeline import global_impacts as G
from pipeline import systems as S
from pipeline import whats_new as W
from tests.test_iteration21_testarch import WEB, needs_bundler, needs_payload, run_ts

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
CURATED = ROOT / "data" / "curated"
WORLD = PROCESSED / "global" / "world.geojson"

MODULES = {
    "chip": "global/impacts/ConfidenceChip.tsx", "insp": "global/impacts/ImpactInspector.tsx",
    "model": "global/impacts/model.ts", "vocab": "global/impacts/vocab.ts", "ctxt": "global/impacts/ContextTimeline.tsx",
    "summary": "global/ConfidenceSummary.tsx", "csv": "global/recordCsv.ts", "cf": "global/countryFilters.ts",
    "compare": "global/compare.ts", "ov": "global/countryOverview.ts", "ev": "global/evidence.ts",
    "wn": "global/whatsNewText.ts", "manifest": "global/manifest.ts", "review": "global/reviewText.ts",
}
PRELUDE = """
const h = React.createElement;
const text = (el) => renderToStaticMarkup(el).replace(/<[^>]+>/g, " ").replace(/&amp;/g, "&").replace(/&#x27;/g, "'")
  .replace(/&quot;/g, '"').replace(/\\s+/g, " ").trim();
"""


def _ts(tmp_path_factory, body, payload=None):
    return run_ts(tmp_path_factory, MODULES, PRELUDE + body, payload)


def _read(rel):
    return json.loads((WEB / rel).read_text(encoding="utf-8"))


def _country_ids():
    return [s["id"] for s in _read("global/manifest.json")["systems"] if s["kind"] == "country"]


def _method():
    return json.loads((ROOT / "methodology" / "evidence_confidence.json").read_text(encoding="utf-8"))


# ---- F5 / IA-10: the provisional status says run 1 was performed and did not pass ----------------

def test_f5_the_served_status_says_the_first_calibration_was_run_and_did_not_pass():
    status = EC.calibration_status()
    assert status.startswith("provisional"), status
    assert "calibration run 1" in status and "did not pass" in status, status
    assert EC.method()["status"] == status


@needs_payload
def test_f5_every_served_copy_of_the_status_is_the_same_words():
    status = EC.calibration_status()
    assert _read("global/evidence_confidence.json")["status"] == status
    for sid in _country_ids():
        assert _read(f"systems/{sid}/system.json")["evidence_confidence_summary"]["status"] == status, sid


CONF = {"category": "MODERATE", "label": "Moderate", "score": 63, "disputed": False, "reason": None, "cap": "origins_not_reviewed",
        "components": {"directness": {"tier": "independent", "points": 28}, "origins": {"count": 2, "points": 16, "basis": "publishers"},
                       "effect": {"specificity": "described", "points": 8}, "opened": {"points": 0},
                       "contemporaneous": {"points": 0, "dated": "not_recorded"}},
        "reasons": ["Press or third-party reporting", "2 distinct publishers cited"]}


@needs_bundler
def test_f5_eci08_the_chip_says_provisional_and_that_it_does_not_cover_the_cause(tmp_path_factory):
    m = _method()
    out = _ts(tmp_path_factory, """
      const render = () => text(h(chip.ConfidenceChip, { value: input.conf }));
      vocab.forgetVocabularies();
      const before = render();
      vocab.registerMethod({ ...input.method, status: input.status });
      const provisional = render();
      vocab.forgetVocabularies();
      vocab.registerMethod({ ...input.method, status: "calibrated against blind reviewer labels" });
      const calibrated = render();
      return { before, provisional, calibrated, cause: model.CONFIDENCE_NOT_CAUSE };
    """, {"conf": CONF, "status": EC.calibration_status(),
          "method": {"categories": m["categories"], "components": [], "statement": m["statement"]}})
    assert "provisional method" in out["provisional"] and EC.calibration_status() in out["provisional"]
    assert "provisional method" not in out["calibrated"], "a calibrated status is not called provisional"
    assert "provisional method" not in out["before"], "no status is invented before the method is read"
    for t in (out["before"], out["provisional"], out["calibrated"]):
        assert out["cause"] in t, "the card says the category does not cover the cause"
    assert "does not cover the cause" in out["cause"]


# ---- ECI-15 / F13 / F2: the breakdown -------------------------------------------------------------

@needs_bundler
def test_f13_not_earned_is_said_as_not_recorded_never_as_no(tmp_path_factory):
    no_strong = copy.deepcopy(CONF)
    no_strong["components"]["directness"] = {"tier": "secondary", "points": 15}
    no_strong["components"]["origins"] = {"count": 0, "points": 0, "basis": "publishers"}
    out = _ts(tmp_path_factory, """
      const why = (v) => text(h(chip.ConfidenceBreakdown, { value: v, method: null }));
      return { press: why(input.press), none: why(input.none) };
    """, {"press": CONF, "none": no_strong})
    assert "not recorded as opened" in out["press"] and "not recorded: no cited source carries a date" in out["press"]
    assert out["none"].count("not counted: no first-party source or press report") == 2
    for t in out.values():
        assert not re.search(r"\bno\s+0\b", t), "a component not earned is never a bare 'no'"


@needs_bundler
def test_eci15_f2_no_total_and_the_two_origin_counts_say_what_they_count(tmp_path_factory):
    out = _ts(tmp_path_factory, """
      return { why: text(h(chip.ConfidenceBreakdown, { value: input.conf, method: null })),
               all: model.allCitationsOriginsText(3, "reviewed", 5), comp: model.componentOriginsText(2, "reviewed") };
    """, {"conf": CONF})
    assert not re.search(r"(?<!up to )\b63 points", out["why"]), "the total is not shown (ECI-15)"
    assert "among the first-party and press sources for the event and its effect" in out["why"]
    assert out["all"].startswith("Across all 5 citations, for any claim") and out["all"] != out["comp"]
    assert out["comp"].endswith("among the first-party and press sources for the event and its effect")


@needs_bundler
def test_f2_f4_the_inspector_labels_both_counts_and_says_who_the_reviewers_were(tmp_path_factory):
    m = _method()
    rec = {"impact_id": "imp-x", "record_kind": "disruption", "date": "2024-01-02", "date_precision": "day", "date_end": None,
           "country_a3": "USA", "country_name": "United States", "admin1": None, "geographic_precision": "country",
           "domain": "energy", "sector": "electricity", "technology": None, "cause_family": "natural_hazard",
           "contributing_factors": [], "cyber_mechanism": None, "summary": "s", "effect": "e", "effect_specificity": "described",
           "inclusion_basis": None, "civilian_service_impact": [], "attribution": {"status": "NOT_APPLICABLE"},
           "ai_involvement": {"status": "NONE_REPORTED"}, "dispute": None, "publication_policy": "standard",
           "sources": [{"ref": "s1", "url": "https://a.example/x", "publisher": "A", "source_role": "media", "medium": "web",
                        "supports": ["occurrence", "effect"]}],
           "review": {"reviewed_at": "2026-11-19", "roles": {}}, "first_published": "2026-11-20",
           "evidence_confidence": CONF, "origin_count": 1}
    out = _ts(tmp_path_factory, """
      vocab.forgetVocabularies();
      return { t: text(h(insp.ImpactInspector, { record: input.rec })), same: review.REVIEWERS_SAME_MODEL };
    """, {"rec": rec, "method": m})
    assert "Across all 1 citation, for any claim" in out["t"]
    assert "can differ" in out["t"]
    assert out["same"] in out["t"], "the reviewers are said to be sessions of the same AI model"
    assert "three independent roles" not in out["t"]


# ---- F14 / C3: the per-country summary ------------------------------------------------------------

@needs_bundler
@needs_payload
def test_f14_f5_the_country_summary_says_its_status_and_that_high_is_unreachable(tmp_path_factory):
    sid = "us"
    sys_, events = _read(f"systems/{sid}/system.json"), _read(f"systems/{sid}/events.json")["events"]
    reviewed = copy.deepcopy(events)
    for e in reviewed:
        if e["evidence_confidence"]["category"] is not None:
            e["evidence_confidence"]["components"]["origins"]["basis"] = "reviewed"
            break
    out = _ts(tmp_path_factory, """
      const render = (events) => text(h(summary.ConfidenceSummary, { bundle: { system: input.sys, events, episodes: [] } }));
      return { served: render(input.events), reviewed: render(input.reviewed), high: summary.HIGH_UNREACHABLE };
    """, {"sys": sys_, "events": events, "reviewed": reviewed})
    assert f"Method status: {EC.calibration_status()}." in out["served"]
    assert out["high"] in out["served"], "every assessed US record is counted by publishers: High is unreachable"
    assert out["high"] not in out["reviewed"], "said only when it is true of every assessed record"


def test_f14_no_comparison_view_reads_a_countrys_confidence_distribution():
    """Two countries' confidence distributions are never set side by side (C3, §103): Compare reads
    no evidence-confidence field at all."""
    for rel in ("compare.ts", "compareExport.ts", "CompareView.tsx"):
        src = (ROOT / "web" / "src" / "global" / rel).read_text(encoding="utf-8")
        assert "evidence_confidence" not in src and "confidenceCounts" not in src and "ConfidenceSummary" not in src, rel


# ---- CSV dictionaries carry the served status (F5), the origins count (F2), the reviewers (F4) ----

@needs_bundler
@needs_payload
def test_f5_f2_f4_both_csv_dictionaries_say_the_served_status(tmp_path_factory):
    sys_ = _read("systems/us/system.json")
    out = _ts(tmp_path_factory, """
      const base = { title: "t", csvName: "x.csv", scope: "s", buildDate: "b", downloaded: "d", shown: 0, total: 0, filters: [], limitations: [] };
      return {
        impact: csv.readmeText({ ...base, columns: csv.IMPACT_COLUMNS, fields: csv.IMPACT_FIELDS, confidenceStatus: input.status }),
        missing: csv.readmeText({ ...base, columns: csv.IMPACT_COLUMNS, fields: csv.IMPACT_FIELDS }),
        country: cf.countryExport(input.sys, [], 0, [], null, "2026-11-20").readme,
        origins: csv.IMPACT_FIELDS.originating_statements, score: csv.IMPACT_FIELDS.evidence_confidence_score,
        review: csv.COUNTRY_EVENT_FIELDS.review_status, same: review.REVIEWERS_SAME_MODEL,
      };
    """, {"status": EC.calibration_status(), "sys": sys_})
    line = f"Method status as served when this file was made: {EC.calibration_status()}."
    assert line in out["impact"] and line in out["country"]
    assert "Method status as served when this file was made: not available" in out["missing"]
    assert "for any claim" in out["origins"] and "Not the evidence-confidence component's count" in out["origins"]
    assert "0 to 100" not in out["score"] and "points, not a percentage" in out["score"]
    assert out["same"] in out["review"]


# ---- F4 / C12: the reviewers are sessions of one model --------------------------------------------

@needs_bundler
def test_f4_every_review_label_says_the_reviewers_were_one_model(tmp_path_factory):
    out = _ts(tmp_path_factory, "return manifest.REVIEW_STATUS_LABEL;")
    for status in ("blind_reviewed", "dual_reviewed"):
        assert "same AI model" in out[status] and "independent in context, not in model" in out[status], status
    assert "independent reviewers" not in json.dumps(out)


def test_f4_the_served_review_text_says_who_the_reviewers_were():
    blind = {"review_status": "blind_reviewed", "process": "Reviewed blind by three independent reviewers."}
    once = B._disclosed_review(blind)
    assert once["process"].endswith(B.REVIEWER_DISCLOSURE) and "same AI model" in B.REVIEWER_DISCLOSURE
    assert B._disclosed_review(once) == once, "said once, however often the build runs"
    assert blind["process"] == "Reviewed blind by three independent reviewers.", "the curated block is not mutated"
    assert B._disclosed_review({"review_status": "dual_reviewed", "process": ""})["process"] == B.REVIEWER_DISCLOSURE
    legacy = {"review_status": "legacy_single_review", "process": "One reviewer."}
    assert B._disclosed_review(legacy) == legacy, "a single review claims no independence"


@needs_payload
def test_f4_every_served_independent_review_carries_the_disclosure():
    for sid in _country_ids():
        for e in _read(f"systems/{sid}/events.json")["events"]:
            if e["review"]["review_status"] != "legacy_single_review":
                assert e["review"]["process"].endswith(B.REVIEWER_DISCLOSURE), e["event_id"]
        assert B.REVIEWER_DISCLOSURE in _read(f"systems/{sid}/system.json")["review_summary"]["note"], sid


# ---- F3: one list of first-party roles, and an origin rule that says what it does ----------------

def test_f3_first_party_roles_are_the_methods_direct_tier():
    direct = [r for r, t in EC.METHOD["role_tier"].items() if t == "direct"]
    assert list(B.FIRST_PARTY_ROLES) == direct
    assert "dataset" not in B.FIRST_PARTY_ROLES and {"cert", "law_enforcement", "court_record"} <= set(B.FIRST_PARTY_ROLES)


def test_f3_the_served_origin_rule_says_it_can_overstate_independence():
    rule = B.source_health([{"sources": [{"source_role": "media", "language": "en", "publisher": "A", "url": "https://a.example/1"}]}])["origin_rule"]
    assert "can overstate independence" in rule and "not overstate" not in rule
    assert "evidence-confidence count" in rule, "the second count on the page is named, and why it can be lower"


# ---- ECI-14: a wire's short name is not the start of another name --------------------------------

# (publisher, the country systems' origin, the evidence-confidence origin). The country table has no
# "AP"; the method's own wire list adds it, so the two differ there by design.
AP = "wire:Associated Press"
WIRE_CASES = [
    ("IANS Research", None, None), ("Sakshi Post (IANS)", "wire:IANS", "wire:IANS"), ("Day Spa", None, None),
    ("Spa Hotel News", None, None), ("Wam Wam Burgers", None, None),
    ("Al-Eqtisadiah (republishing SPA)", "wire:Saudi Press Agency", "wire:Saudi Press Agency"),
    ("AFP via Dawn", "wire:AFP", "wire:AFP"), ("The New Arab (AFP and agencies)", "wire:AFP", "wire:AFP"),
    ("PBS NewsHour (AP copy)", None, AP), ("Fox Business (AP contributed)", None, AP), ("CBS News (CBS/AP)", None, AP),
    ("Reuters (via Kitco)", "wire:Reuters", "wire:Reuters"), ("Associated Press (published by Fortune)", AP, AP),
    ("Global News (The Canadian Press)", "wire:The Canadian Press", "wire:The Canadian Press"),
    ("RIA Novosti", None, "wire:RIA Novosti"), ("Ria Fashion Daily", None, None),
]


@pytest.mark.parametrize("publisher,build,eci", WIRE_CASES)
def test_eci14_wire_matching_reads_whole_names(publisher, build, eci):
    source = {"publisher": publisher, "url": "https://outlet.example/story"}
    assert B.source_origin(source) == (build or "outlet.example"), publisher
    assert EC.origin_of(source) == (eci or "outlet.example"), publisher


def test_eci14_an_explicit_origin_is_read_without_its_case():
    assert EC.origin_of({"publisher": "X", "url": "https://x.example/1", "origin": "afp"}) == "wire:AFP"
    assert EC.origin_of({"publisher": "X", "url": "https://x.example/1", "origin": "Rostelecom statement via TASS"}) == "wire:TASS"
    assert EC.origin_of({"publisher": "X", "url": "https://x.example/1", "origin": "IANS Research"}) == "ians research"


@needs_bundler
def test_eci14_the_card_matches_wires_exactly_as_the_build_does(tmp_path_factory):
    out = _ts(tmp_path_factory, """
      return input.cases.map((p) => ev.sourceOrigin({ publisher: p, url: "https://outlet.example/story" }));
    """, {"cases": [p for p, _, _ in WIRE_CASES]})
    assert out == [w or "outlet.example" for _, w, _ in WIRE_CASES]


# ---- F11 / F10: a region belongs to its country; the campaign set comes from the data ------------

@pytest.fixture(scope="module")
def ctx():
    return G.load_context(WORLD, unit_names={})


def _geo(a3, code, precision="admin1"):
    return {"country_a3": a3, "geographic_precision": precision, "admin1": {"code": code, "name": "Somewhere"},
            "cause_family": "natural_hazard", "contributing_factors": []}


@needs_payload
def test_f11_the_gate_refuses_a_region_of_another_country(ctx):
    assert G.geography_problems(_geo("RUS", "RU-MOS"), ctx) == []
    assert G.geography_problems(_geo("USA", "US-TX"), ctx) == []
    for a3, code in (("RUS", "UA-43"), ("RUS", "UA-40"), ("USA", "CA-ON"), ("UKR", "RU-MOS")):
        problems = G.geography_problems(_geo(a3, code), ctx)
        assert any("is not a first-level region of" in p for p in problems), (a3, code, problems)
    lost = {**ctx, "a2": {k: v for k, v in ctx["a2"].items() if k != "USA"}}
    assert any("cannot be checked" in p for p in G.geography_problems(_geo("USA", "US-TX"), lost))


def test_f11_the_alpha_two_code_falls_back_where_natural_earth_marks_it_unassigned():
    assert B._iso_a2({"ISO_A2": "ZW"}) == "ZW"
    assert B._iso_a2({"ISO_A2": "-99", "ISO_A2_EH": "FR"}) == "FR"
    assert B._iso_a2({"ISO_A2": "-99", "ISO_A2_EH": "-99"}) is None


@needs_payload
def test_f11_the_served_world_carries_the_alpha_two_code_and_crimea_is_ukrainian():
    feats = json.loads(WORLD.read_text(encoding="utf-8"))["features"]
    occupied = [f["properties"] for f in feats if f["properties"].get("status") == "occupied"]
    assert occupied and all(p["a2"] == "UA" for p in occupied)
    assert {f["properties"]["a2"] for f in feats if f["properties"]["a3"] == "RUS"} == {"RU"}
    served = json.loads((PROCESSED / "global" / "impacts.json").read_text(encoding="utf-8"))
    a2 = G.load_context(WORLD, unit_names={})["a2"]
    for r in served["records"] + served["attempts"]:
        if r.get("admin1"):
            assert r["admin1"]["code"].startswith(a2[r["country_a3"]] + "-"), r["impact_id"]


def _campaign_a3():
    """The countries of every campaign-restricted country system, read from the curated register."""
    states = B.load_campaigns().get("system_states") or {}
    return {a3 for s in S.SYSTEMS if s["kind"] == "country" and (states.get(s["id"]) or {}).get("state") in B.RESTRICTING_STATES
            for a3 in s["admin0_a3"]}


@needs_payload
def test_f10_no_record_of_a_campaign_restricted_country_system_carries_a_region():
    campaign = _campaign_a3()
    assert campaign, "no campaign-restricted country system is recorded: retire this guard deliberately"
    served = json.loads((PROCESSED / "global" / "impacts.json").read_text(encoding="utf-8"))
    for r in served["records"] + served["attempts"]:
        a3 = r["country_a3"]
        if (set(r.get("countries_a3") or []) | {a3}) & campaign:
            assert r.get("admin1") is None, r["impact_id"]


def test_f10_f9_the_documents_say_what_the_code_enforces():
    impact = (ROOT / "docs" / "GLOBAL_IMPACT_METHODOLOGY.md").read_text(encoding="utf-8")
    assert "never** for any record in a system under the campaign policy" not in impact
    assert "**never** for any record of a **country system** under the campaign policy" in impact
    policy = (ROOT / "docs" / "CURRENT_EVENT_PUBLICATION_POLICY.md").read_text(encoding="utf-8")
    assert "**Applied now:** Saudi Arabia" not in policy and "UNCERTAIN restricts exactly as ACTIVE does" in policy
    assert "| yes, admin-1 only |" not in policy
    eci = (ROOT / "docs" / "EVIDENCE_CONFIDENCE_V2.md").read_text(encoding="utf-8")
    assert "plus optional `actor_aliases`" not in eci and "actor_aliases" not in G.ATTRIBUTION_FIELDS


# ---- ECI-06: the Limited meaning describes what the thresholds produce ---------------------------

def test_eci06_one_press_origin_without_a_figure_is_moderate_and_the_meaning_says_so():
    press = [{"ref": "s1", "url": "https://paper.example/a", "publisher": "Paper", "source_role": "media", "medium": "web",
              "date": "2024-03-02", "opened": True}]
    assert EC.assess(press, "2024-03-01", effect_specificity="described")["category"] == "MODERATE"
    limited = next(c for c in EC.METHOD["categories"] if c["id"] == "LIMITED")["meaning"]
    assert "one origin, no figure" not in limited
    assert "Moderate, not Limited" in limited


# ---- XL-04 / XL-05 / XL-02: What's New -----------------------------------------------------------

@pytest.mark.parametrize("date,expected", [("2026-11", False), ("2026-10", True), ("2026-11-10", True), ("2026-11-19", False),
                                           ("2026", False), ("2025", True), ("soon", False)])
def test_xl04_a_month_is_historical_only_when_the_whole_month_is_before(date, expected):
    assert W._wholly_before(date, "2026-11-19") is expected


@pytest.mark.parametrize("record,timing", [
    ({"date": "2026-09-20", "date_end": "2026-11-01", "first_published": "2026-11-20"}, "new_event"),
    ({"date": "2026-09-20", "date_end": "2026-10-01", "first_published": "2026-11-20"}, "backfill"),
    ({"date": "2026-09", "date_end": None, "first_published": "2026-11-20"}, "backfill"),
    ({"date": "2026-10", "date_end": None, "first_published": "2026-11-20"}, "new_event"),
])
def test_xl05_the_backfill_rule_reads_the_observed_end(record, timing):
    assert W.impact_timing(record) == timing


@needs_bundler
@needs_payload
def test_xl05_the_panel_and_the_card_call_the_same_records_historical(tmp_path_factory):
    served = json.loads((PROCESSED / "global" / "impacts.json").read_text(encoding="utf-8"))
    made = [{"date": "2026-09-20", "date_end": "2026-11-01", "first_published": "2026-11-20"},
            {"date": "2026-09-20", "date_end": "2026-10-01", "first_published": "2026-11-20"},
            {"date": "2026-09", "date_end": None, "first_published": "2026-11-20"},
            {"date": "2026-10-19", "date_end": None, "first_published": "2026-11-19"}]
    records = [{k: r.get(k) for k in ("date", "date_end", "first_published")} for r in served["records"]] + made
    records = [r for r in records if r.get("first_published")]
    out = _ts(tmp_path_factory, "return input.records.map((r) => model.isHistoricalAddition(r));", {"records": records})
    python = [W.impact_timing(r) == "backfill" for r in records]
    assert out == python


def test_xl02_a_first_release_keeps_the_context_sentence():
    prev = {"impacts": None, "regional_context": None}
    curr = {"impacts": {"records": []}, "regional_context": {"entries": [{"id": "ctx-1"}]}}
    out = W.impact_changes(prev, curr)
    assert [c["category"] for c in out] == ["impact_record_added", "regional_context_updated"]
    assert out[1]["notes"] == [W.FIRST_CONTEXT_RELEASE]
    only_layer = W.impact_changes(prev, {"impacts": {"records": []}, "regional_context": None})
    assert [c["category"] for c in only_layer] == ["impact_record_added"]


@needs_bundler
def test_ia06_the_method_link_opens_help(tmp_path_factory):
    out = _ts(tmp_path_factory, """
      return [wn.changeLink({ category: "methodology", notes: [], link: { help: "whats-new" } }),
              wn.changeLink({ category: "methodology", notes: [], link: { anchor: "why-head" } }),
              wn.changeLink({ category: "x", notes: [], link: { help: "javascript:alert(1)" } })];
    """)
    assert out[0] == {"href": "?view=help#whats-new", "label": "Learn more in Help", "samePage": False}
    assert out[1] is None and out[2] is None


# ---- XL-08: Compare says what the Saudi page publishes -------------------------------------------

def test_xl08_attack_record_detail_is_read_from_the_records():
    assert B.attack_record_detail([{"cause": "accident"}]) is None
    got = B.attack_record_detail([{"cause": "kinetic_strike", "region_code": "SA-04", "facility_name": None, "publication": None},
                                  {"cause": "sabotage", "region_code": None, "facility_name": "F", "publication": {"rule": "x"}}])
    assert got == {"region": True, "facility": True, "campaign_covered": True}
    assert B.attack_record_detail([{"cause": "kinetic_strike", "region_code": None, "facility_name": None}]) == \
        {"region": False, "facility": False, "campaign_covered": False}
    assert B.attack_record_detail([{"cause": "kinetic_strike", "region_code": "SA-04", "facility_name": None}]) == \
        {"region": True, "facility": False, "campaign_covered": False}


@needs_bundler
@needs_payload
def test_xl08_compare_discloses_a_country_page_finer_than_one_region_at_most(tmp_path_factory):
    man = _read("global/manifest.json")
    cols = [{"entry": next(s for s in man["systems"] if s["id"] == sid), "system": _read(f"systems/{sid}/system.json"),
             "status": "loaded"} for sid in ("sa", "us", "ir")]
    out = _ts(tmp_path_factory, """
      const rows = compare.compareRows(input.cols, null, input.man);
      return rows.find((r) => r.id === "placement").cells;
    """, {"cols": cols, "man": man})
    sa, us, ir = out
    assert "attack records on this country's own page: first-level region, with the facility named" in sa["text"]
    assert "under the owner's current decision" in sa["detail"] and "for the country only" in sa["detail"]
    assert "attack records" not in us["text"], "a system serving no attack record says nothing about them"
    assert ir["text"].startswith("Attack records:"), "a country-level attack policy keeps its own wording"


@needs_payload
def test_xl08_the_saudi_page_serves_the_flags_it_shows():
    assert _read("systems/sa/system.json")["attack_records"] == {"region": True, "facility": True, "campaign_covered": True}
    assert _read("systems/us/system.json")["attack_records"] is None


# ---- C10 / C11: the Iran page ------------------------------------------------------------------

@needs_bundler
@needs_payload
def test_c10_c11_registry_rechecks_and_unread_sources_are_said_as_they_are(tmp_path_factory):
    sys_ = _read("systems/ir/system.json")
    out = _ts(tmp_path_factory, """
      return { line: ov.sourceCheckLine(8, 0, 1), clean: ov.sourceCheckLine(8, 0, 0), late: ov.sourceCheckLine(8, 2, 0),
               note: ov.countryOverview(input.sys, { state: "not_loaded" }, null).publishedNote, inclusion: ov.IMPACT_INCLUSION_LINE };
    """, {"sys": sys_})
    assert out["line"] == "All 8 registry entries re-checked on schedule · 1 source group unreadable in the latest search"
    assert out["clean"] == "All 8 registry entries re-checked on schedule"
    assert out["late"] == "2 of 8 registry entries overdue for a re-check"
    assert out["note"].startswith("Why: a source group could not be read in the latest search"), out["note"]
    assert "strict" not in out["note"]
    assert "could not read the sources" in out["inclusion"] and "broader contract" not in out["inclusion"]


# ---- T-A7 / T-A8: the grid clause and the served rule text --------------------------------------

@needs_bundler
@needs_payload
def test_ta7_the_grid_clause_says_which_limb_the_record_met(tmp_path_factory):
    sys_ = _read("systems/us/system.json")
    e = next(x for x in _read("systems/us/events.json")["events"] if x["event_id"] == "us-2024-09-06-california-firm-load-shed")
    out = _ts(tmp_path_factory, "return ev.plainBasis(input.e, input.sys.inclusion_threshold);", {"e": e, "sys": sys_})
    assert out.startswith("It met one of two tests for power grids") and "Which of the two is in the recorded basis" in out
    assert not re.search(r"clause|\b\d\b|§", out.replace("100,000", "")), "plain words, no clause number"


def test_ta8_the_served_rule_text_matches_what_the_build_does():
    rule = json.loads((CURATED / "systems" / "inclusion_threshold.json").read_text(encoding="utf-8"))
    assert not any("not yet grouped" in w for w in rule["known_weaknesses"]), "episodes are grouped since iteration 15"
    us = json.loads((CURATED / "systems" / "us" / "events.json").read_text(encoding="utf-8"))["events"]
    assert not any("names EEA3 explicitly" in (e.get("threshold_basis") or "") for e in us), "clause 5 names no alert level"


# ---- XL-01: the context timeline says where a later statement is ------------------------------

@needs_bundler
@needs_payload
def test_xl01_a_historical_statement_points_where_its_newer_statement_is_drawn(tmp_path_factory):
    ctx = _read("global/regional_context.json")
    out = _ts(tmp_path_factory, """
      vocab.forgetVocabularies();
      const page = text(h(ctxt.ContextTimeline, { ctx: input.ctx }));
      const entries = [...input.ctx.entries].sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : a.id < b.id ? -1 : 1));
      const latest = new Set(entries.filter((e) => (input.ctx.latest_by_type[e.context_type] || []).includes(e.id)));
      const places = ctxt.laterPlaces(entries, latest);
      return { page, rows: entries.map((e, i) => ({ id: e.id, type: e.context_type, latest: latest.has(e), place: places.get(e) || null })) };
    """, {"ctx": ctx})
    rows = out["rows"]
    for i, r in enumerate(rows):
        if r["latest"]:
            continue
        newer = [j for j, x in enumerate(rows) if x["latest"] and x["type"] == r["type"]]
        want = ("above and below" if any(j < i for j in newer) and any(j > i for j in newer)
                else "above" if any(j < i for j in newer) else "below")
        assert r["place"] == want, r
    below = [r for r in rows if r["place"] == "below"]
    if below:
        assert "A later statement of this type is listed below." in out["page"]


# ---- Record corrections (production red team; XL-15, XL-01, T-B2): the gate rules behind them ------

def _served_records():
    doc = _read("global/impacts.json")
    return doc["records"] + doc.get("attempts", [])


def _one_abstracted():
    return copy.deepcopy(next(r for r in _served_records() if r.get("publication_policy") == G.ABSTRACTED
                              and r.get("date_precision") == "day"))


@needs_payload
def test_an_abstracted_record_states_no_duration(ctx):
    """A German sabotage record said its outage lasted "several days": how long service was out is
    the same later status as an end date, which an abstracted record never carries."""
    r = _one_abstracted()
    assert not [p for p in G.abstraction_problems(r, ctx) if "duration" in p]
    r["civilian_service_impact"][0]["duration_text"] = "several days"
    assert any("states no duration" in p for p in G.abstraction_problems(r, ctx))
    for word in ("withheld", "unknown", None):
        r["civilian_service_impact"][0]["duration_text"] = word
        assert not [p for p in G.abstraction_problems(r, ctx) if "duration" in p], word


@needs_payload
def test_xl15_an_abstracted_record_carries_no_late_citation(ctx):
    """The country systems' late-citation rule, now on abstracted impact records: a report from more
    than seven days after the event, an undated one, or one dated only to a month is refused."""
    import datetime as dt
    r = _one_abstracted()
    start = dt.date.fromisoformat(r["date"])
    s = r["sources"][0]
    for date, late in (((start + dt.timedelta(days=7)).isoformat(), False),
                       ((start + dt.timedelta(days=8)).isoformat(), True),
                       (None, True), (r["date"][:7], True)):
        s["date"] = date
        hit = [p for p in G.abstraction_problems(r, ctx) if "days of the event" in p]
        assert bool(hit) is late, (date, hit)


@needs_payload
def test_served_abstracted_records_pass_the_duration_and_late_citation_rules(ctx):
    for r in _served_records():
        if r.get("publication_policy") == G.ABSTRACTED:
            bad = [p for p in G.abstraction_problems(r, ctx) if "duration" in p or "days of the event" in p]
            assert not bad, (r["impact_id"], bad)


@needs_payload
def test_the_import_withholds_an_abstracted_records_duration():
    """The import writes any duration on an abstracted record as withheld, as it removes an end
    date; an absence word is kept as it is."""
    import scripts.import_impacts as I
    r = _one_abstracted()
    r["civilian_service_impact"][0]["duration_text"] = "several days"
    notes = []
    out = I.shape(r, "imp-test-original-id", b"test-key-not-the-real-one", False, notes)
    assert out["civilian_service_impact"][0]["duration_text"] == "withheld"
    assert any("duration written as withheld" in n for n in notes)
    r["civilian_service_impact"][0]["duration_text"] = "unknown"
    assert I.shape(r, "imp-test-original-id", b"k", False, [])["civilian_service_impact"][0]["duration_text"] == "unknown"


def test_tb2_basis_four_needs_a_national_or_regional_scope():
    """Basis 4 is a national or regional service lost; it had been claimed for one hospital, one
    airport and one island community, all recorded as local."""
    r = copy.deepcopy(next(x for x in _served_records() if x.get("inclusion_basis") == 4))
    assert not [p for p in G.vocabulary_problems(r) if "inclusion_basis 4" in p]
    for c in r["civilian_service_impact"]:
        c["geographic_scope"] = "local"
    assert any("inclusion_basis 4" in p for p in G.vocabulary_problems(r))
    taxonomy = json.loads((ROOT / "methodology" / "impact_taxonomy.json").read_text(encoding="utf-8"))
    scopes = {s["id"] for s in taxonomy["geographic_scopes"]}
    assert set(G.WIDE_SCOPES) <= scopes and "local" not in G.WIDE_SCOPES


def test_tb2_no_served_basis_four_record_is_local_only():
    for r in _served_records():
        if r.get("inclusion_basis") == 4:
            assert any(c.get("geographic_scope") in G.WIDE_SCOPES for c in r["civilian_service_impact"]), r["impact_id"]


def test_xl01_a_context_entry_cannot_describe_a_day_after_it_was_made():
    entries = copy.deepcopy(_read("global/regional_context.json")["entries"])
    assert not [p for p in G.context_problems(entries) if "is after date" in p], "the served file passes"
    e = next(x for x in entries if x["as_of"] == x["date"])
    e["as_of"] = "2099-01-01"
    assert any("is after date" in p for p in G.context_problems(entries))


def test_a_lead_correction_carries_its_own_date():
    """A correction added to a lane's lead file later is dated alone: restamping the lane's date had
    marked some sixty untouched records as revised (found applying the iteration-23 corrections)."""
    import scripts.import_impacts as I
    reviews = {I.LEAD: {"lane": {"reviewed_at": "2026-11-19", "verdicts": {
        "a": {"verdict": "accept_with_correction", "set": {}},
        "b": {"verdict": "accept_with_correction", "set": {}, "reviewed_at": "2026-11-21"}}}}}
    assert I.lead_patch(reviews, "lane", "a")[1] == "2026-11-19"
    assert I.lead_patch(reviews, "lane", "b")[1] == "2026-11-21"
    assert "reviewed_at" in I.LEAD_KEYS


def test_an01_whats_new_is_built_after_the_impact_layer_it_reads():
    """AN-01 (analyst red team). What's New reads impacts.json and regional_context.json from the
    processed folder; built before the impact layer wrote them, it compared the previous run's
    files, so the release that withdrew four impact records reported no withdrawal."""
    src = (ROOT / "pipeline" / "run.py").read_text(encoding="utf-8")
    impact_build = src.index("impact_payloads = global_impacts.build(")
    panel_build = src.index("whats_new.build(ROOT, outputs.processed()")
    assert impact_build < panel_build, "What's New must run after the impact layer has written its payloads"
    assert src.count("whats_new.build(") == 1


def test_an05_a_country_record_never_names_an_encyclopedia_as_a_source():
    """AN-05 (analyst red team). Three records still said "(Wikipedia)" beside a figure after the
    Wikipedia-only records were held; an encyclopedia is a discovery aid, never a source."""
    ok = {"event_id": "x-1", "summary": "A storm.", "effect": "The utility reported 165,000 customers out.", "threshold_basis": None}
    assert B.encyclopedia_attribution_problems([ok]) == []
    for field, text in (("effect", "over 200,000 customers lost power statewide (Wikipedia)."),
                        ("summary", "the encyclopaedia says 80% of customers"), ("threshold_basis", "per Encyclopedia Britannica")):
        bad = {**ok, field: text}
        assert any("names an encyclopedia as a source" in p for p in B.encyclopedia_attribution_problems([bad])), field
    for sid in S.COUNTRY_SYSTEMS:
        events = _read(f"systems/{sid}/events.json")["events"]
        assert B.encyclopedia_attribution_problems(events) == [], sid


def test_an05_the_build_refuses_a_record_that_names_an_encyclopedia():
    """The rule is in the list the build runs, not only callable: build_system raises on whatever
    record_problems returns, and record_problems refuses a US record whose effect cites Wikipedia."""
    src = (ROOT / "pipeline" / "build_systems.py").read_text(encoding="utf-8")
    body = src[src.index("def build_system("):src.index("def build_world(")]
    assert "problems = record_problems(system_id, doc, events, profile, campaigns, research_log)" in body
    cur = CURATED / "systems" / "us"
    doc, profile = (json.loads((cur / f).read_text(encoding="utf-8")) for f in ("system.json", "profile.json"))
    log = json.loads((cur / "research_log.json").read_text(encoding="utf-8"))
    events = copy.deepcopy(_read("systems/us/events.json")["events"])
    assert B.record_problems("us", doc, events, profile, B.load_campaigns(), log) == []
    events[0]["effect"] = str(events[0].get("effect") or "") + " (Wikipedia)"
    assert any("names an encyclopedia as a source" in p
               for p in B.record_problems("us", doc, events, profile, B.load_campaigns(), log))


@needs_payload
def test_f1_an_abstracted_record_states_no_duration_in_any_prose(ctx):
    """Final methodology red team F-1. The German sabotage record's duration field was withheld but
    its summary said "for several days" and a source's derived claim "a multi-day outage"."""
    r = _one_abstracted()
    assert not [p for p in G.abstraction_problems(r, ctx) if "how long service was out" in p]
    for where, text in (("summary", "Households lost power for several days."),
                        ("effect", "Supply was cut; a multi-day outage followed."),
                        ("derived", "Reports customers had been without power since the Saturday."),
                        ("derived", "Reports a three-week-long outage."), ("summary", "Lost power for 36 hours.")):
        bad = copy.deepcopy(r)
        if where == "derived":
            bad["sources"][0]["derived_claim"] = text
        else:
            bad[where] = text
        assert any("how long service was out" in p for p in G.abstraction_problems(bad, ctx)), text
    for r in _served_records():
        if r.get("publication_policy") == G.ABSTRACTED:
            assert not [p for p in G.abstraction_problems(r, ctx) if "how long service was out" in p], r["impact_id"]
