"""Iteration 20: Gulf maturity and data-integrity hardening.

Parsers that fail closed, capacity figures that carry their uncertainty, one month-date form, the
strict reading of the inclusion clauses applied to every system, and a mutation harness that
reports every outcome. Payload tests read what was emitted.
"""
import importlib.util
import json
import random
import re
from pathlib import Path

import pytest

from pipeline import build_systems as B, calendars as C

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web" / "public" / "data"
CURATED = ROOT / "data" / "curated" / "systems"
COUNTRIES = ("ae", "bh", "ca", "cn", "in", "iq", "ir", "kw", "om", "qa", "sa", "us")
needs_payload = pytest.mark.skipif(not (WEB / "global" / "manifest.json").exists(), reason="no built payload")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _curated(sid):
    return json.loads((CURATED / sid / "events.json").read_text(encoding="utf-8"))["events"]


def _served(sid):
    return json.loads((WEB / "systems" / sid / "events.json").read_text(encoding="utf-8"))["events"]


# --- §52 parse_number fails closed -------------------------------------------------------------------

@pytest.mark.parametrize("text,want", [
    ("1500", 1500), ("1,500", 1500), ("1 500", 1500), ("12,345,678", 12345678), ("2.5", 2.5),
    ("۱۵۰۰", 1500), ("١٬٥٠٠", 1500), ("٢٫٥", 2.5), ("-40", -40), ("0", 0), ("0.75", 0.75),
])
def test_an_unambiguous_number_is_read(text, want):
    assert C.parse_number(text) == want


@pytest.mark.parametrize("text", [
    "1.500", "1,5", "12,34", "1.234.567", "10 20", "2025 2026", "5، 300", "5،300", "0,500", "007",
    "1,500 2,000", "1,50,000", "1 500,000", "1,500.000.1", "", "   ", "abc", "1,", ",500", "1..5", "+-5",
])
def test_ambiguous_number_forms_are_refused(text):
    # Each of these is a guess in at least one reading convention; the parser refuses rather than
    # pick one (iteration 20 §52).
    assert C.parse_number(text) is None


def test_parse_number_fuzz_never_raises_and_never_reads_two_numbers_as_one():
    rng = random.Random(20)
    alphabet = "0123456789,. ،٬٫۱۲٣-+"
    for _ in range(5000):
        s = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 9)))
        n = C.parse_number(s)
        assert n is None or isinstance(n, (int, float)), s
        if n is not None:
            # A number was read only from one unbroken numeral: never across an Arabic comma or
            # two decimal marks.
            assert "،" not in s and C.western_digits(s).replace("٫", ".").count(".") <= 1, s


# --- §50-51 normalize_date fails closed; Solar Hijri months keep month precision ---------------------

@pytest.mark.parametrize("text,cal,want", [
    ("2025-06-15", "gregorian", "2025-06-15"),
    ("15/06/2025", "gregorian", "2025-06-15"),
    ("2025-03-14T10:00:00Z", "gregorian", "2025-03-14"),
    ("2025-06", "gregorian", "2025-06"),
    ("۲۵ خرداد ۱۴۰۴", "solar_hijri", "2025-06-15"),
])
def test_an_unambiguous_date_is_normalised(text, cal, want):
    assert C.normalize_date(text, cal)["normalized_date"] == want


@pytest.mark.parametrize("text,cal", [
    ("05/06/2025", "gregorian"),     # day and month both 12 or below: ambiguous
    ("15/06/25", "gregorian"),       # two-digit year
    ("2025-13-01", "gregorian"),
    ("2025-02-30", "gregorian"),
    ("0/06/2025", "gregorian"),
    ("1404-03-25", "gregorian"),     # a Solar Hijri year read as Gregorian
    ("2025-06-15", "solar_hijri"),   # a Gregorian year read as Solar Hijri
    ("30 صفر 1446", "hijri"),         # Safar has 29 days in the tabular calendar
    ("15 June 2025 and 16 June 2025", "gregorian"),
    ("", "gregorian"),
])
def test_an_ambiguous_or_impossible_date_is_refused(text, cal):
    with pytest.raises(ValueError):
        C.normalize_date(text, cal)


def test_a_solar_hijri_month_keeps_month_precision_with_its_gregorian_range():
    n = C.normalize_date("مرداد ۱۴۰۴", "solar_hijri")
    # Mordad spans two Gregorian months; a Gregorian month would be an invented precision.
    assert n["normalized_date"] is None
    assert n["gregorian_range"] == ["2025-07-23", "2025-08-22"]
    assert "month precision" in n["conversion_basis"]


def test_the_import_holds_a_month_it_cannot_place():
    ic = _load("import_candidates")
    r = {"date": "2025-07", "date_precision": "month", "date_calendar": "solar_hijri", "source_date_text": "مرداد ۱۴۰۴"}
    assert ic.date_problem(r)


def test_the_hijri_month_lengths_follow_the_tabular_calendar():
    assert [C.hijri_month_length(1446, m) for m in range(1, 12)] == [30, 29] * 5 + [30]
    leap = [y for y in range(1441, 1471) if C.hijri_month_length(y, 12) == 30]
    assert len(leap) == 11


# --- §53 one month-date form; formatting never parses through Date ------------------------------------

def test_every_curated_date_is_written_at_its_precision():
    for sid in COUNTRIES:
        for e in _curated(sid):
            assert B.date_problems(e["event_id"], e) == [], e["event_id"]


def test_the_build_refuses_the_old_month_form_and_impossible_dates():
    assert B.date_problems("x", {"date": "2026-04-01", "date_precision": "month"})
    assert B.date_problems("x", {"date": "2026-04", "date_precision": "day"})
    assert B.date_problems("x", {"date": "2026-02-30", "date_precision": "day"})
    assert B.date_problems("x", {"date": "2026-04", "date_precision": "week"})
    assert B.date_problems("x", {"date": "2026-04-05", "date_precision": "day", "date_end": "2026-04-01"})
    assert B.date_problems("x", {"date": "2026-04", "date_precision": "month"}) == []


def test_the_compatibility_path_canonicalises_queue_dates():
    assert B.canonical_date("2026-04-01", "month") == "2026-04"
    assert B.canonical_date("2026-04-01", "year") == "2026"
    assert B.canonical_date("2026-04-01", "day") == "2026-04-01"


def test_month_dates_survive_late_citation_and_ordering():
    e = {"date": "2026-04", "date_precision": "month"}
    assert not B.late_citation(e, {"date": "2026-05-06"})
    assert B.late_citation(e, {"date": "2026-05-10"})
    assert sorted(["2026-04-05", "2026-04", "2026-03-30"]) == ["2026-03-30", "2026-04", "2026-04-05"]


def test_no_event_or_episode_date_is_formatted_through_the_browser_date_parser():
    for rel in ("CountryView.tsx", "GlobalPanels.tsx", "GroupView.tsx"):
        src = (ROOT / "web" / "src" / "global" / rel).read_text(encoding="utf-8")
        assert not re.search(r"new Date\(`\$\{(e\.date|ep\.first_date)", src), rel


def test_a_generated_sentence_writes_a_date_as_the_page_does():
    assert B.reader_date("2026-11-01") == "1 Nov 2026"
    assert B.reader_date("2022-01-31") == "31 Jan 2022"


@needs_payload
def test_no_generated_gate_note_carries_an_iso_date():
    for sid in COUNTRIES:
        s = json.loads((WEB / "systems" / sid / "system.json").read_text(encoding="utf-8"))
        for item in s["onboarding_gate"]:
            assert not re.search(r"\(20\d\d-\d\d-\d\d\)", item.get("note") or ""), (sid, item.get("note"))


@needs_payload
def test_served_month_records_carry_the_canonical_form():
    seen = 0
    for sid in COUNTRIES:
        for e in _served(sid):
            if e["date_precision"] == "month":
                seen += 1
                assert re.fullmatch(r"\d{4}-\d{2}", e["date"]), e["event_id"]
    assert seen >= 1


# --- §26-27 capacity carries its uncertainty -----------------------------------------------------

@pytest.mark.parametrize("says,want", [
    ("more than 350,000 customers", "at_least"),
    ("at least 319,000 boe/d", "at_least"),
    ("Plus de 115 000 clients", "at_least"),
    ("خسارة الشبكة أكثر من 6 آلاف ميغاواط", "at_least"),
    ("As many as 300,000 people", "at_most"),
    ("approximately 135,000 customers", "about"),
    ("près de 540 000 clients", "about"),
    ("ما يقارب 480 ألف برميل يوميًا", "about"),
    ("ما بين 4 آلاف و4500 ميغاواط", "range"),
    ("between 4,000 and 4,500 MW", "range"),
    ("586,000 Hydro One outages", "exact"),
    ("reduced demand by approximately 350 MW over an hour", "about"),
    ("over 2,000 MW of generation", "at_least"),
])
def test_the_capacity_qualifier_follows_the_source_words(says, want):
    assert B.capacity_qualifier(says) == want


def test_a_bound_is_never_left_as_a_point_value():
    lo = B.normalize_capacity({"value": 6000, "unit": "MW", "source_says": "أكثر من 6 آلاف ميغاواط"})
    assert lo["value"] is None and lo["value_min"] == 6000 and lo["qualifier"] == "at_least"
    hi = B.normalize_capacity({"value": 300000, "unit": "people", "source_says": "as many as 300,000"})
    assert hi["value"] is None and hi["value_max"] == 300000
    d = B.normalize_capacity({"value": 440000, "unit": "b/d", "source_says": "x", "qualifier": "disputed"})
    assert d["value"] is None and d["value_min"] is None and d["value_max"] is None


@pytest.mark.parametrize("cap", [
    {"value": 4000, "value_min": None, "value_max": None, "qualifier": "range", "measure": "affected", "unit": "MW", "source_says": "x"},
    {"value": None, "value_min": 4500, "value_max": 4000, "qualifier": "range", "measure": "affected", "unit": "MW", "source_says": "x"},
    {"value": 6000, "value_min": None, "value_max": None, "qualifier": "at_least", "measure": "affected", "unit": "MW", "source_says": "x"},
    {"value": 440000, "value_min": None, "value_max": None, "qualifier": "disputed", "measure": "affected", "unit": "b/d", "source_says": "x"},
    {"value": 300, "value_min": None, "value_max": None, "qualifier": "guess", "measure": "affected", "unit": "MW", "source_says": "x"},
    {"value": 300, "value_min": None, "value_max": None, "qualifier": "exact", "measure": "loss", "unit": "MW", "source_says": "x"},
    {"value": -3, "value_min": None, "value_max": None, "qualifier": "exact", "measure": "affected", "unit": "MW", "source_says": "x"},
    {"value": 300, "value_min": None, "value_max": None, "qualifier": "exact", "measure": "affected", "unit": "", "source_says": "x"},
    {"value": 300, "unit": "MW", "source_says": "x"},
])
def test_the_build_refuses_a_capacity_block_whose_shape_contradicts_its_qualifier(cap):
    assert B.capacity_problems("x", cap)


def test_every_curated_capacity_block_has_the_iteration_20_shape():
    seen = {}
    for sid in COUNTRIES:
        for e in _curated(sid):
            cap = e.get("capacity_affected")
            if cap:
                assert B.capacity_problems(e["event_id"], cap) == [], e["event_id"]
                seen[cap["qualifier"]] = seen.get(cap["qualifier"], 0) + 1
    # The migration found every kind of figure in the corpus at least once.
    for q in ("exact", "about", "at_least", "range", "component_only", "disputed"):
        assert seen.get(q), q


def test_the_iteration_19_examples_are_migrated_as_the_brief_requires():
    iq = {e["event_id"]: e for e in _curated("iq")}
    kw = {e["event_id"]: e for e in _curated("kw")}
    rng = iq["iq-2025-12-23-imported-gas-halt-generation-loss"]["capacity_affected"]
    assert (rng["qualifier"], rng["value"], rng["value_min"], rng["value_max"]) == ("range", None, 4000, 4500)
    unit = kw["kw-2024-06-19-programmed-power-cuts-generation-shortfall"]["capacity_affected"]
    assert unit["qualifier"] == "component_only"


def test_a_nameplate_is_marked_as_the_facility_size_not_the_loss():
    us = {e["event_id"]: e for e in _curated("us")}
    assert us["us-2022-06-08-freeport-lng-explosion"]["capacity_affected"]["measure"] == "facility_size"


def test_nothing_sums_capacity_figures():
    # Nothing downstream may total these until the methodology says how (§26).
    for p in list((ROOT / "pipeline").glob("*.py")) + list((ROOT / "web" / "src").rglob("*.ts*")):
        src = p.read_text(encoding="utf-8")
        # The theatre's own capacity_affected_mw fields are a different, documented measure.
        assert not re.search(r"sum\([^)]*capacity_affected(?!_)|capacity_affected(?!_)[^;\n]*\breduce\(", src), p.name


# --- §13-24, §99 strict reading, every system ---------------------------------------------------

STRICT_HOLDS = {
    "iq-2025-12-08-west-qurna-2-production-halt-leak", "iq-2025-08-11-national-grid-collapse",
    "iq-2026-03-04-national-grid-total-blackout", "kw-2025-04-09-programmed-power-cuts-demand-above-generation",
    "kw-2026-03-20-refinery-attack-1", "om-2022-09-05-main-grid-partial-blackout",
    "us-2024-09-11-hurricane-francine-louisiana-outages",
    "us-2023-08-25-marathon-garyville-tank-fire", "us-2025-10-02-chevron-el-segundo-fire",
    "us-2025-05-07-hunt-tuscaloosa-coker-fire", "us-2025-06-14-marathon-galveston-bay-fire",
    "us-2025-08-14-phillips66-linden-fcc-fire", "in-2022-02-21-chandigarh-power-strike-blackout",
    "in-2023-06-15-biparjoy-gujarat-power-outage", "us-2022-12-23-pjm-forced-outages-elliott",
    # Methodology red team, round two (§13): fail the written rule, or analogous records are held.
    "us-2022-12-24-gulf-coast-refineries-cold-shutdowns", "cn-2023-02-22-alxa-xinjing-open-pit-collapse",
    "us-2023-02-23-pemex-deer-park-crude-unit-fire", "us-2024-10-10-pemex-deer-park-h2s-release",
    "us-2022-06-10-california-firm-load-shed", "us-2024-04-28-texas-new-mexico-firm-load-shed",
    "us-2025-04-02-louisiana-firm-load-shed", "us-2025-04-26-louisiana-firm-load-shed",
    "us-2024-02-03-tgp-line-100-1-mississippi", "us-2025-03-30-michigan-ice-storm-outages",
    "us-2023-03-03-michigan-storm-outages", "us-2022-12-23-winter-storm-elliott-maine-outages",
    "us-2026-01-24-winter-storm-fern-mississippi-outages", "us-2026-10-09-hurricane-isaias-outages",
    "in-2024-10-23-cyclone-dana-odisha-port-suspensions",
    "sa-2026-09-11-east-west-pipeline-shutdown",
    # Safety red team (D-10): facility-named records of a class with attack records in the campaign window.
    "kw-2025-10-21-refinery-fire-partial-shutdown", "kw-2023-11-12-refinery-production-halt-fuel-gas-loss",
}
# Held attack records whose ids name their facility, by digest: a public file names no held attack
# record (§48). sha256 of the id, first 16 hex digits.
STRICT_HOLD_DIGESTS = {"sa": {"4b75cfb9dd7a27db", "edf86f907a9f2e2b"}}


def _digest(eid):
    import hashlib
    return hashlib.sha256(eid.encode("utf-8")).hexdigest()[:16]


EXTENT = re.compile(r"extent-based|by extent|all governorates|across .* governorates|thousands of villages", re.I)
EMERGENCY_FOOTING = re.compile(r"emergency footing|بحالة الطوارئ|emergency plans", re.I)


def test_no_record_held_on_a_strict_reading_is_published():
    published = {e["event_id"] for sid in COUNTRIES for e in _curated(sid)}
    assert not STRICT_HOLDS & published
    for sid, digests in STRICT_HOLD_DIGESTS.items():
        assert not {_digest(e["event_id"]) for e in _curated(sid)} & digests, sid


RESTRICTED = ("ae", "bh", "iq", "ir", "kw", "om", "qa", "sa")
TAG = re.compile(r"\[(C[1-7]-[A-Z]+|ROUTE|NO-EFFECT|SHARE-ONLY|TAXONOMY|SINGLE-SITE|D-10)\]")


def test_every_strict_hold_is_on_file_with_its_tag():
    # Outside the campaign policy the hold is a public review edit with its tag. Under it the public
    # file keeps nothing for an unpublished record, so the hold and its reason are in the local queue
    # (checked where the queue exists; it is gitignored, so not in CI).
    edits = json.loads((CURATED / "review_edits.json").read_text(encoding="utf-8"))["edits"]
    held = {e["event_id"]: e["reason"] for e in edits if e["field"] == "suggested_disposition" and e["set"] == "held"}
    for eid in STRICT_HOLDS:
        cc = eid.split("-")[0]
        if cc not in RESTRICTED:
            assert TAG.search(held.get(eid, "")), eid
            continue
        assert eid not in held, f"{eid}: a restricted system's hold is never a public edit"
        qp = ROOT / "data" / "candidates" / f"{cc}.json"
        if qp.exists():
            r = next(x for x in json.loads(qp.read_text(encoding="utf-8")) if x.get("candidate_id") == eid)
            assert r["suggested_disposition"] == "held" and TAG.search(r["disposition_reason"]), eid
    for cc, digests in STRICT_HOLD_DIGESTS.items():
        assert not [e for e in edits if _digest(e["event_id"]) in digests], cc
        qp = ROOT / "data" / "candidates" / f"{cc}.json"
        if qp.exists():
            held = [x for x in json.loads(qp.read_text(encoding="utf-8")) if _digest(x.get("candidate_id") or "") in digests]
            assert len(held) == len(digests), cc
            assert all(x["suggested_disposition"] == "held" and TAG.search(x["disposition_reason"]) for x in held), cc


def test_no_public_document_of_this_iteration_names_a_held_attack_record():
    # The documents written for iteration 20 name a held attack record by country and year only.
    for p in (ROOT / "docs").glob("*_20.md"):
        text = p.read_text(encoding="utf-8")
        for token in re.findall(r"\b(?:ae|bh|iq|ir|kw|om|qa|sa)-20\d\d-[\w-]+", text):
            for digests in STRICT_HOLD_DIGESTS.values():
                assert _digest(token) not in digests, (p.name, "names a held attack record")


def test_no_published_clause_5_record_rests_on_extent_or_emergency_footing_alone():
    for sid in COUNTRIES:
        for e in _curated(sid):
            if e["criterion_met"] != 5:
                continue
            basis = e.get("threshold_basis") or ""
            if EXTENT.search(basis) or EMERGENCY_FOOTING.search(basis):
                # Allowed only where the basis also states a count or a formal declaration.
                assert re.search(r"\d{3},\d{3}|\d{3} \d{3}|million|EEA ?3|EEA Level 3|declar|load shed", basis, re.I), e["event_id"]


def test_no_published_clause_5_record_counts_people_as_customers():
    for sid in COUNTRIES:
        for e in _curated(sid):
            if e["criterion_met"] == 5:
                cap = e.get("capacity_affected") or {}
                basis = e.get("threshold_basis") or ""
                if cap.get("unit") == "people":
                    assert "customers" in basis or "outages" in basis, e["event_id"]
                # The basis, not only the unit field: "200,000 people" written up as customers.
                if re.search(r"\bpeople\b", basis) and not re.search(r"customers|outages|accounts|connections|households", basis):
                    raise AssertionError(f"{e['event_id']}: clause 5 on a count of people")


def test_no_published_clause_4_record_rests_on_demand_alone():
    for sid in COUNTRIES:
        for e in _curated(sid):
            if e["criterion_met"] == 4 and re.search(r"load rise|demand (peak|rise)|(peak|rising) demand", e.get("threshold_basis") or "", re.I):
                assert re.search(r"shortfall|unable|deficit|out of service|lost|offline", e.get("effect") or "", re.I), e["event_id"]


def test_no_published_clause_1_record_rests_on_an_unquantified_partial_effect():
    vague = re.compile(r"\b(some units|a number of units|several process units|reduced (operating )?rates|cut back|"
                       r"temporary reduction|affected exports|production outage)\b", re.I)
    shut = re.compile(r"\b(refinery (fully )?shut|whole|entire|sitewide|full refinery shutdown|shut down|"
                      r"knocked out of production|b/d|bpd|Bcf/d|crude unit|trains?|thousand tonnes|operations were suspended)\b", re.I)
    for sid in COUNTRIES:
        for e in _curated(sid):
            if e["criterion_met"] == 1 and vague.search(e.get("effect") or ""):
                assert shut.search(e.get("effect") or ""), e["event_id"]


# --- §46 campaign text, every country system ----------------------------------------------------

def _campaign_doc(sid="us", **fields):
    c = {"campaign_id": f"{sid}-x", "system_id": sid, "name": "Attacks on energy facilities, 2026",
         "status_basis": "Attacks on energy facilities were reported in 2026. No end is reported.",
         "member_rule": {}, "status_sources": [{"publisher": "P", "published": "2026-11-02"}]}
    c.update(fields)
    return {"campaigns": [c], "system_states": {sid: {"basis": "Attacks on energy facilities were reported in 2026."}}}


def test_the_campaign_text_rule_reads_every_country_system_and_every_field():
    """Iteration 19 read the Gulf group's bases only. A campaign of any country system is served
    on its page, and its name and notes are printed as plainly as its basis."""
    assert B.campaign_text_problems(_campaign_doc()) == []
    for field, bad in (("status_basis", "Attacks were reported; the refinery has restarted."),
                       ("name", "Attacks on the northern refineries, 2026"),
                       ("notes", "Repairs are under way at two sites."),
                       ("status_basis", "Attacks were reported; output is back to normal.")):
        assert B.campaign_text_problems(_campaign_doc(**{field: bad})), (field, bad)
    doc = _campaign_doc()
    doc["system_states"]["us"]["notes"] = "Production resumed in October."
    assert B.campaign_text_problems(doc)
    # The theatre has its own embargo and publishes occurrence by region; this rule is not its rule.
    assert B.campaign_text_problems(_campaign_doc("russia_theatre", status_basis="Strikes on refineries continue.")) == []


# --- §42, §47 held counts beside a campaign ------------------------------------------------------

LOG = {"passes": [{"date": "2026-11-11", "kind": "systematic", "outcome": {"records": 1, "held": 4, "rejected": 9}},
                  {"date": "2026-11-12", "kind": "systematic", "outcome": {"records": 2, "insufficient_evidence": 3}},
                  {"date": "2026-11-13", "kind": "systematic", "outcome": {"records": 2}}]}


def test_a_campaign_page_says_candidates_remain_under_review_never_how_many():
    assert B.public_research_log(LOG, False) is LOG
    out = B.public_research_log(LOG, True)
    assert [p["outcome"] for p in out["passes"]] == [{}, {}, {}]
    assert [p["under_review"] for p in out["passes"]] == [True, True, False]
    assert LOG["passes"][0]["outcome"]["held"] == 4, "the canonical log is not changed"


@needs_payload
def test_no_served_research_log_under_the_campaign_policy_carries_a_held_count():
    seen = 0
    for sid in COUNTRIES:
        s = json.loads((WEB / "systems" / sid / "system.json").read_text(encoding="utf-8"))
        restricted = (s.get("campaign_state") or {}).get("state") in B.RESTRICTING_STATES
        for p in s["research_log"]["passes"]:
            if restricted:
                seen += 1
                assert set(p.get("outcome") or {}) <= set(B.PUBLIC_OUTCOME_UNDER_CAMPAIGN), (sid, p.get("date"))
                assert isinstance(p.get("under_review"), bool), (sid, p.get("date"))
            else:
                assert "under_review" not in p, sid
    assert seen, "no system under the campaign policy was read"


# --- §43 newer national totals ------------------------------------------------------------------

@needs_payload
def test_a_country_under_the_campaign_policy_shows_the_comparison_year_only():
    served = json.loads((WEB / "global" / "energy_context.json").read_text(encoding="utf-8"))
    curated = {c["a3"]: c for c in json.loads((ROOT / "data" / "curated" / "global_context" / "energy_context.json")
                                               .read_text(encoding="utf-8"))["countries"]}
    states = B.load_campaigns().get("system_states") or {}
    guarded = 0
    for row in served["countries"]:
        restricted = (states.get(row["system_id"]) or {}).get("state") in B.RESTRICTING_STATES
        if restricted:
            assert row["newer"] == {}, row["a3"]
            guarded += bool(curated[row["a3"]].get("newer"))
        else:
            assert row["newer"] == (curated[row["a3"]].get("newer") or {}), row["a3"]
    assert guarded, "no restricted country had a newer value to withhold: this test proved nothing"


@needs_payload
def test_a_campaign_country_page_shows_no_profile_figure_newer_than_the_comparison_year():
    year = json.loads((ROOT / "data" / "curated" / "global_context" / "energy_context.json").read_text(encoding="utf-8"))["comparison_year"]
    assert B.load_campaigns()["profile_year_cap"]["year"] == year, "the cap follows the context comparison year"
    states = B.load_campaigns().get("system_states") or {}
    guarded = 0
    for sid in COUNTRIES:
        s = json.loads((WEB / "systems" / sid / "system.json").read_text(encoding="utf-8"))
        curated = json.loads((CURATED / sid / "profile.json").read_text(encoding="utf-8"))
        newer = [m for m in curated["metrics"] if isinstance(m.get("year"), int) and m["year"] > year]
        if (states.get(sid) or {}).get("state") in B.RESTRICTING_STATES:
            assert all(not (isinstance(m.get("year"), int) and m["year"] > year) for m in s["profile"]["metrics"]), sid
            guarded += bool(newer)
        else:
            assert len(s["profile"]["metrics"]) == len(curated["metrics"]), sid
    assert guarded, "no campaign country had a newer figure to withhold: this test proved nothing"


def test_the_committed_research_log_of_a_campaign_system_carries_no_counts():
    states = B.load_campaigns().get("system_states") or {}
    for sid in COUNTRIES:
        if (states.get(sid) or {}).get("state") not in B.RESTRICTING_STATES:
            continue
        for p in json.loads((CURATED / sid / "research_log.json").read_text(encoding="utf-8"))["passes"]:
            assert p.get("outcome") == {}, (sid, p["date"])
            assert isinstance(p.get("under_review"), bool), (sid, p["date"])


# --- §44 single-site classes ---------------------------------------------------------------------

def _single_site_doc(classes):
    return {"geography": {"precision_policy": {"kinetic": "country", "reason": "r", "single_site_classes": classes}}}


def test_an_attack_record_of_a_class_the_country_has_one_site_of_is_refused():
    doc = _single_site_doc({"lng_terminal": {"basis": "one complex"}})
    attack = {"event_id": "qa-2026-03-01-energy-attack-1", "cause": "kinetic_strike", "asset_class": "lng_terminal",
              "geography_precision": "country", "region_code": None, "regions_affected": [], "episode_id": None}
    assert any("one site of" in p for p in B.precision_problems("qa", doc, [attack]))
    other = {**attack, "asset_class": "power_plant"}
    assert B.precision_problems("qa", doc, [other]) == []
    accident = {**attack, "event_id": "qa-2024-01-01-fire", "cause": "technical"}
    assert B.precision_problems("qa", doc, [accident]) == []
    assert any("states no basis" in p for p in B.precision_problems("qa", _single_site_doc({"lng_terminal": {}}), []))
    assert any("not an asset class" in p for p in B.precision_problems("qa", _single_site_doc({"gas_thing": {"basis": "b"}}), []))


def test_the_import_gate_holds_an_attack_record_of_a_single_site_class():
    imp = _load("import_candidates")
    policy = {"kinetic": "country", "reason": "r", "single_site_classes": {"refinery": {"basis": "one refinery"}}}
    r = {"candidate_id": "bh-2026-03-01-refinery-attack-1", "date": "2026-03-01", "date_precision": "day",
         "admin1_code": None, "geography_precision": "country", "admin1_codes_affected": [], "facility_name": None,
         "facility_name_local": None, "operator": None, "asset_class": "refinery", "cause": "kinetic_strike",
         "summary": "An attack on energy infrastructure was reported.", "effect": "A shutdown was reported.",
         "threshold_basis": "clause 1", "suggested_disposition": "accept", "threshold_clause": 1,
         "capacity_affected": None, "hazard_name": None,
         "recovery": {"research_status": "NOT_YET_RESEARCHED", "kind": None, "date": None, "evidence": None, "url": None},
         "independent_review": {"completed": "2026-11-11", "disposition": "confirmed", "sources_opened": 1},
         "sources": [{"url": "https://example.org/news/energy-attack-reported", "publisher": "Example", "date": "2026-03-01",
                      "language": "en", "source_role": "media", "opened": True}]}
    why = imp.review("bh", r, set(), policy=policy)
    assert why and "[SINGLE-SITE]" in why
    assert imp.review("bh", {**r, "asset_class": "power_plant"}, set(), policy=policy) != why


def test_every_declared_single_site_class_is_a_class_with_a_basis():
    for sid in COUNTRIES:
        doc = json.loads((CURATED / sid / "system.json").read_text(encoding="utf-8"))
        assert not [p for p in B.precision_problems(sid, doc, []) if "single-site" in p], sid
    declared = {sid: set(((json.loads((CURATED / sid / "system.json").read_text(encoding="utf-8")).get("geography") or {})
                          .get("precision_policy") or {}).get("single_site_classes") or {}) for sid in COUNTRIES}
    assert "lng_terminal" in declared["qa"] and "refinery" in declared["bh"]


# --- §10 canonical citation addresses -----------------------------------------------------------

def test_a_citation_is_published_at_the_address_a_reader_lands_on(monkeypatch):
    imp = _load("import_candidates")
    monkeypatch.setattr(imp, "FINAL_ADDRESSES", {"https://ex.org/?p=12": "https://ex.org/2026/03/power-cut-in-city"})
    assert imp.canonical_url("https://ex.org/?p=12") == "https://ex.org/2026/03/power-cut-in-city"
    assert imp.canonical_url("https://ex.org/news/a-b-c/amp/") == "https://ex.org/news/a-b-c/"
    assert imp.canonical_url("https://ex.org/news/a-b-c?amp") == "https://ex.org/news/a-b-c"
    assert imp.canonical_url("https://amp.ex.org/news/a-b-c") == "https://ex.org/news/a-b-c"
    assert imp.canonical_url("https://ex.org/amp/news/a-b-c") == "https://ex.org/news/a-b-c"
    assert imp.canonical_url("https://ex.org/ampArticle/123456") == "https://ex.org/article/123456"
    assert imp.canonical_url(None) is None


def test_a_citation_is_judged_by_where_it_lands(monkeypatch):
    imp = _load("import_candidates")
    monkeypatch.setattr(imp, "FINAL_ADDRESSES", {"https://ex.org/node/2636397": "https://ex.org/news/drone-attack-on-laffan"})
    tokens = {"laffan"}
    assert imp.unpublishable_address("https://ex.org/node/2636397", tokens), "the address it lands on names the place"
    assert imp.unpublishable_address("https://ex.org/article/744381", tokens), "an opaque link never read"
    assert imp.unpublishable_address("https://ex.org/?p=500001", tokens), "a short link never read"
    assert not imp.unpublishable_address("https://ex.org/news/power-cuts-reported-nationwide", tokens)
    assert imp.opaque_unresolved("https://ex.org/ar/article/74438")
    assert not imp.opaque_unresolved("https://ex.org/node/2636397")
    assert not imp.opaque_unresolved("https://ex.org/news/power-cut-2026")


def test_a_redirect_is_classed_as_article_listing_or_refusal():
    lc = _load("check_source_links")
    assert lc.classify_redirect("u", "https://ex.org/cdn-cgi/challenge?x=1") == "challenge"
    assert lc.classify_redirect("u", "https://ex.org/") == "general_page"
    assert lc.classify_redirect("u", "https://ex.org/news/") == "general_page"
    assert lc.classify_redirect("u", "https://ex.org/news/power-cut-in-city.html") == "canonical"
    assert lc.classify_redirect("u", "https://www.sec.gov/Archives/edgar/data/1534504/000153450426000029/a991.htm") == "canonical"
    assert lc.clean_final("https://ex.org:443/a-b-c?utm_source=x&id=5") == "https://ex.org/a-b-c?id=5"


# --- pass order ------------------------------------------------------------------------------------

def test_of_two_passes_on_one_day_the_later_in_the_log_is_the_newer():
    log = {"passes": [{"date": "2026-11-11", "kind": "systematic", "status": "partial", "window": ["2022-01-01", "2026-11-11"], "lanes": []},
                      {"date": "2026-11-11", "kind": "systematic", "status": "complete", "window": ["2022-01-01", "2026-11-11"], "lanes": []}]}
    assert B.research_freshness(log)["completeness"] == "complete"
    log["passes"].reverse()
    assert B.research_freshness(log)["completeness"] == "partial"


# --- §70 the absent index ------------------------------------------------------------------------

@needs_payload
def test_every_country_page_says_no_index_is_not_a_zero():
    for sid in COUNTRIES:
        s = json.loads((WEB / "systems" / sid / "system.json").read_text(encoding="utf-8"))
        assert s["index"] is None and s["headline"] is None, sid
        assert "not a zero" in s["no_index_reason"] and ".json" not in s["no_index_reason"], sid


# --- §49 review edits --------------------------------------------------------------------------------

def test_the_public_review_edits_keep_nothing_for_an_unpublished_record_under_the_campaign_policy():
    edits = json.loads((CURATED / "review_edits.json").read_text(encoding="utf-8"))["edits"]
    for cc in RESTRICTED:
        published = {e["event_id"] for e in _curated(cc)}
        for e in edits:
            if e["event_id"].split("-")[0] == cc:
                assert e["event_id"] in published, e["event_id"]
                assert e["reason"].endswith(_load("apply_reviews").GENERIC_REASON), e["event_id"]


# --- §26 capacity, as served -----------------------------------------------------------------------

@needs_payload
def test_every_served_capacity_block_has_one_shape_per_qualifier():
    seen = 0
    for sid in COUNTRIES:
        for e in _served(sid):
            cap = e.get("capacity_affected")
            if cap:
                seen += 1
                assert B.capacity_problems(e["event_id"], cap) == [], e["event_id"]
    assert seen


# --- the address gate reads every spelling (geography red team, round two) -----------------------

GATE_CASES = [
    ("ir", "https://www.mehrnews.com/news/6509376/%D8%A8%D8%B1%D9%82-%D8%AA%D9%87%D8%B1%D8%A7%D9%86"),
    ("ir", "https://example.ir/news/qom-oil-depot-fire"), ("ir", "https://example.ir/fa/آتش-سوزی-در-بوشهر"),
    ("iq", "https://example.com/dhi-qar-power-station-fire"), ("iq", "https://example.com/thi-qar-oil"),
    ("iq", "https://example.com/حريق-بالبصرة"), ("iq", "https://example.com/البصره"), ("iq", "https://example.com/إربيل-x"),
    ("iq", "https://basra.example.com/news/2025/fire"), ("iq", "https://example.com/attack-on-kurdistan-region-gas-field"),
    ("bh", "https://example.com/manama-power-outage"), ("bh", "https://example.com/muharraq-fire"),
    ("qa", "https://example.com/al-khor-industrial-fire"), ("qa", "https://example.com/الخور"),
    ("kw", "https://example.com/jahra-power-station"),
    ("kw", "https://example.com/%25D8%25A7%25D9%2584%25D8%25A3%25D8%25AD%25D9%2585%25D8%25AF%25D9%258A"),
    ("ae", "https://example.com/ras-al-khaima-fire"), ("ae", "https://example.com/أبو-ظبي"), ("ae", "https://example.com/حريق-بالفجيرة"),
    ("om", "https://example.com/ظفار"), ("om", "https://example.com/sharqiya-fire"),
]


def _gate_words(cc):
    imp = _load("import_candidates")
    doc = json.loads((CURATED / cc / "system.json").read_text(encoding="utf-8"))
    feats = json.loads((WEB / "systems" / cc / "regions.geojson").read_text(encoding="utf-8"))["features"]
    us = [(f["properties"]["code"], f["properties"]["name"], None) for f in feats]
    return imp, set(imp.unit_words(B.unit_name_rows(doc, us))) | {B.fold(w) for w in doc["geography"]["precision_policy"].get("region_words") or []}


@needs_payload
@pytest.mark.parametrize("cc,url", GATE_CASES)
def test_the_gate_reads_a_place_in_any_common_spelling(cc, url):
    imp, words = _gate_words(cc)
    assert imp.unpublishable_address(url, words), url


@needs_payload
@pytest.mark.parametrize("cc,url", [("kw", "https://example.com/news/power-cuts-reported-nationwide"),
                                    ("ir", "https://example.com/news/electricity-outages-national-grid"),
                                    ("ae", "https://example.com/news/energy-ministry-statement-on-supply")])
def test_the_gate_still_publishes_an_address_that_names_no_place(cc, url):
    imp, words = _gate_words(cc)
    assert not imp.unpublishable_address(url, words), url


def test_fold_makes_one_word_of_every_spelling():
    assert B.fold("Al Muḩarraq") == "al muharraq"
    assert B.fold("إربيل") == B.fold("اربيل")
    assert B.fold("البصرة") == B.fold("البصره")
    assert B.fold("کرکوک") == B.fold("كركوك")
    assert B.fold("الأنـبار") == B.fold("الانبار")
    assert B.fold("%25D8%25A8") == B.fold("ب")


def test_method_and_route_wording_is_read_after_folding():
    for u in ("/mortar-attack-on-gas-field", "/ied-blast-at-power-line", "/artillery-hits-refinery", "/airstrike-on-refinery",
              "/%D9%82%D8%B5%D9%81-%D9%85%D8%B5%D9%81%D8%A7%D8%A9", "/بمُسيّرة", "/مسیرة", "/بمباران"):
        assert B.method_in_address(u), u
    assert B.ROUTE_WORDING.search(B.address_words("/نفت‌کش"))
    assert not B.ROUTE_WORDING.search(B.address_words("/hormozgan-power-outage"))


def test_every_unit_of_a_country_policy_system_has_a_native_script_and_a_latin_name():
    for cc in ("ae", "bh", "iq", "ir", "kw", "om", "qa"):
        doc = json.loads((CURATED / cc / "system.json").read_text(encoding="utf-8"))
        al = doc["geography"].get("unit_aliases") or {}
        feats = json.loads((WEB / "systems" / cc / "regions.geojson").read_text(encoding="utf-8"))["features"]
        for f in feats:
            code = f["properties"]["code"]
            if code.endswith("~"):
                continue
            names = [f["properties"]["name"], *al.get(code, [])]
            assert any(n.isascii() for n in names), (cc, code)
            assert any(not n.isascii() for n in names), (cc, code, "no name in Arabic or Persian script")


# --- §110 mutation harness ----------------------------------------------------------------------

def test_the_mutation_harness_validates_anchors_before_running():
    mc = _load("mutation_campaign")
    assert mc.invalid_anchors() == []
    assert "tests/test_iteration20.py" in mc.TEST_FILES


def test_the_mutation_harness_classifies_every_outcome():
    mc = _load("mutation_campaign")
    assert mc.classify(1, "1 failed, 3 passed in 1.2s") == "caught"
    assert mc.classify(0, "4 passed in 1.2s") == "survived"
    assert mc.classify(2, "1 error in 0.5s") == "errored"
    assert mc.classify(5, "no tests ran in 0.1s") == "errored"
    assert mc.classify(1, "1 error in 0.5s") == "errored"


def test_the_mutation_campaign_is_at_least_175_meaningful_mutants():
    mc = _load("mutation_campaign")
    names = [n for n, _, _ in mc.MUTATIONS]
    assert len(names) == len(set(names))
    assert len(names) >= 175
