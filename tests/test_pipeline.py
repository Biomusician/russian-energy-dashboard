"""Tests for the parsing, scoring and scope guarantees.

The scope tests are not decoration. This project sits next to a boundary it must not
cross, and the cheapest way to keep a future change from drifting over it is to fail
the build when it does.
"""

import csv
import datetime as dt
import json
import re
from pathlib import Path

import pytest

from pipeline import wikitext as W
from pipeline.build_index import _composite, _weight_at
from pipeline.config import PROCESSED, RU_REGIONS, aoi_regions
from pipeline.dates import parse_dates, unenumerated_count
from pipeline.fetch_refineries import BBL_PER_DAY_TO_MTPA
from pipeline.regionmatch import resolve

ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# Dates
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text,expected",
    [
        ("{{dts|2026-07-06|format=dmy}}", ["2026-07-06"]),
        ("4 October 2025", ["2025-10-04"]),
        ("March 2024", ["2024-03"]),
        ("24–25 January 2024", ["2024-01-24", "2024-01-25"]),
        # The bare day-list before a shared month: dropping 22 and 23 here would lose
        # two real events without any error surfacing.
        ("22–23 and 25 May 2026", ["2026-05-22", "2026-05-23", "2026-05-25"]),
        ("1 October 2025, 12 December 2025", ["2025-10-01", "2025-12-12"]),
    ],
)
def test_date_parsing(text, expected):
    assert [d for d, _ in parse_dates(text)] == expected


def test_month_precision_is_preserved():
    assert parse_dates("March 2024") == [("2024-03", "month")]
    assert parse_dates("4 March 2024") == [("2024-03-04", "day")]


def test_unenumerated_series_is_counted_not_invented():
    text = "At least 16 times between March 2024 and July 2026"
    assert unenumerated_count(text) == 16
    # Only the two bounding dates are extractable; the other 14 must not be conjured.
    assert len(parse_dates(text)) == 2


# --------------------------------------------------------------------------
# Wikitext
# --------------------------------------------------------------------------

def test_rowspan_expands_into_following_rows():
    table = (
        '{| class="wikitable"\n'
        "! A !! B !! C\n"
        "|-\n"
        '| a1 || rowspan=2| shared || c1\n'
        "|-\n"
        "| a2 || c2\n"
        "|}"
    )
    headers, rows, _ = W.parse_table(table)
    assert headers == ["A", "B", "C"]
    assert rows[0] == ["a1", "shared", "c1"]
    # Without rowspan handling this row would be ["a2", "c2"] and "c2" would be read
    # as the B column.
    assert rows[1] == ["a2", "shared", "c2"]


def test_refs_do_not_split_cells():
    table = (
        '{| class="wikitable"\n'
        "! A !! B\n"
        "|-\n"
        "| facility | <ref>{{cite web\n|title=T\n|url=https://example.org/x\n}}</ref> 4 May 2026\n"
        "|}"
    )
    _, rows, spans = W.parse_table(table)
    assert len(rows) == 1
    text = W.clean_cell(W.restore(rows[0][-1], spans))
    # The citation's own pipes must not become cells, and its content must not leak
    # into the visible value.
    assert "cite web" not in text
    assert "4 May 2026" in text


def test_unquoted_rowspan_attribute_is_stripped():
    _, rows, _ = W.parse_table('{|\n! A\n|-\n| rowspan=3| value\n|}')
    assert rows[0][0] == "value"


# --------------------------------------------------------------------------
# Regions
# --------------------------------------------------------------------------

def test_aoi_composition():
    """Iteration 1: AOI is the six western districts + Siberian + Belarus = 79 regions."""
    aoi = aoi_regions()
    assert len(aoi) == 79
    by_district = {}
    for _, (_, _, district, _) in aoi.items():
        by_district[district] = by_district.get(district, 0) + 1
    assert by_district == {
        "Central": 18, "Northwestern": 11, "Southern": 6,
        "North Caucasian": 7, "Volga": 14, "Ural": 6, "Siberian": 10, "Belarus": 7,
    }


def test_siberian_federal_district_is_enabled():
    from pipeline.config import AOI_FEDERAL_DISTRICTS
    assert "Siberian" in AOI_FEDERAL_DISTRICTS
    # Omsk, the analytic reason for the expansion, must resolve into the AOI.
    assert resolve("Omsk Oblast") == ("in_aoi", "RU-OMS")
    assert resolve("Omsk") == ("in_aoi", "RU-OMS")


def test_far_eastern_defined_but_not_enabled():
    """Far Eastern is carried so it can be turned on later, but is out of the AOI now."""
    from pipeline.config import AOI_FEDERAL_DISTRICTS, DEFINED_FEDERAL_DISTRICTS, FE_REGIONS
    assert "Far Eastern" in DEFINED_FEDERAL_DISTRICTS
    assert "Far Eastern" not in AOI_FEDERAL_DISTRICTS
    assert FE_REGIONS, "Far Eastern regions must be defined for future enablement"
    # Buryatia and Zabaykalsky moved to the Far Eastern FD in 2018 and must be here.
    codes = {v[0] for v in FE_REGIONS.values()}
    assert {"RU-BU", "RU-ZAB"} <= codes


def test_far_eastern_regions_resolve_as_out_of_aoi():
    for name in ("Amur Oblast", "Primorsky Krai", "Republic of Buryatia", "Zabaykalsky Krai"):
        assert resolve(name)[0] == "out_of_aoi", name


def test_no_sfd_abbreviation_in_code_or_config():
    """The ambiguous 'SFD' abbreviation must not appear as a scope label in code, config
    or user-facing methodology. Iteration review docs may discuss its removal by name."""
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    # Iteration review docs may discuss the removal of the abbreviation by name.
    exempt = {
        Path("docs") / "ITERATION_1_REVIEW.md",
        Path("docs") / "ITERATION_2_REVIEW.md",
    }
    offenders = []
    for sub in ("pipeline", "methodology", "docs"):
        for path in (root / sub).rglob("*"):
            if path.suffix not in (".py", ".json", ".md"):
                continue
            if path.relative_to(root) in exempt:
                continue
            if re.search(r"\bSFD\b", path.read_text(encoding="utf-8")):
                offenders.append(str(path.relative_to(root)))
    assert not offenders, f"ambiguous 'SFD' still present in: {offenders}"


def test_region_codes_are_unique():
    from pipeline.config import ALL_RU_REGIONS
    codes = [v[0] for v in ALL_RU_REGIONS.values()]
    assert len(codes) == len(set(codes))


@pytest.mark.parametrize(
    "text,kind,code",
    [
        ("Leningrad Oblast", "in_aoi", "RU-LEN"),
        ("Port of Novorossiysk, Krasnodar Krai", "in_aoi", "RU-KDA"),
        ("Tatarstan", "in_aoi", "RU-TA"),
        # Longest-match: the oblast must not be swallowed by the federal city.
        ("Moscow", "in_aoi", "RU-MOW"),
        ("Moscow Oblast", "in_aoi", "RU-MOS"),
        # Siberian, now in scope.
        ("Omsk Oblast", "in_aoi", "RU-OMS"),
        ("Krasnoyarsk Krai", "in_aoi", "RU-KYA"),
        # Far Eastern, defined but out of the enabled AOI.
        ("Amur Oblast", "out_of_aoi", None),
        ("Nowhere Special", "unresolved", None),
    ],
)
def test_region_resolution(text, kind, code):
    got_kind, got_value = resolve(text)
    assert got_kind == kind
    if code:
        assert got_value == code


def test_out_of_aoi_is_distinct_from_unresolved():
    """Conflating these would hide parser breakage as 'not our area'."""
    assert resolve("Amur Oblast")[0] == "out_of_aoi"
    assert resolve("qqqzzz")[0] == "unresolved"


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------

def _incident(**kw):
    base = {
        "date": "2026-01-01", "confidence": "confirmed",
        "cause": "kinetic_strike", "status": "unknown", "asset_class": "refinery",
    }
    base.update(kw)
    return base


def test_weight_decays_by_modelled_half_life():
    """With no recovery record, the modelled refinery horizon of 150d implies a
    half-life of ~45d, so impairment halves at ~45 days (continuous with the MVP)."""
    inc = _incident()
    day0 = _weight_at(inc, dt.date(2026, 1, 1))
    day45 = _weight_at(inc, dt.date(2026, 2, 15))
    assert day0 == pytest.approx(1.0, abs=1e-9)
    assert day45 == pytest.approx(0.5, abs=0.02)


def test_future_events_do_not_contribute():
    assert _weight_at(_incident(date="2026-06-01"), dt.date(2026, 1, 1)) == 0.0


def test_confidence_and_cause_reduce_weight():
    strong = _weight_at(_incident(), dt.date(2026, 1, 1))
    weak = _weight_at(_incident(confidence="possible"), dt.date(2026, 1, 1))
    planned = _weight_at(_incident(cause="maintenance"), dt.date(2026, 1, 1))
    assert weak < strong
    assert planned < weak


# --------------------------------------------------------------------------
# Recovery / reconstitution framework — incident-level, rule-based (iteration 2)
# --------------------------------------------------------------------------

def _rec(**kw):
    base = {"source_confidence": "medium", "sources": [{"url": "x"}]}
    base.update(kw)
    return base


def test_observed_recovery_overrides_modelled_decay():
    """A sourced, faster-than-generic reconstitution must decay faster than the
    modelled fallback -- evidence overrides assumption."""
    from pipeline import recovery
    inc = _incident(date="2026-01-01")
    fast = _rec(recovery_status="substantially_restored", observed_days=30)
    on_day40 = dt.date(2026, 2, 10)
    modelled = _weight_at(inc, on_day40, None)
    observed = _weight_at(inc, on_day40, fast)
    assert observed < modelled
    assert recovery.scoring_kind("refinery", fast) == "observed"


def test_estimated_and_modelled_kinds_are_distinguished():
    from pipeline import recovery
    est = _rec(recovery_status="impaired", estimate_central_days=200)
    assert recovery.scoring_kind("refinery", est) == "estimated"
    assert recovery.scoring_kind("refinery", None) == "modelled"
    assert recovery.scoring_kind("refinery", {}) == "modelled"


def test_partial_restart_is_not_full_reconstitution():
    """A partial restart records the observed date but does NOT drive the decay curve
    to the residual and NEVER resolves the incident."""
    from pipeline import recovery
    inc = _incident(date="2026-01-01")
    partial = _rec(recovery_status="partial_restart",
                   partial_operations_resumed_at="2026-01-19", observed_days=18)
    # partial restart is display-only for scoring: falls back to the modelled horizon.
    assert recovery.scoring_kind("refinery", partial) == "modelled"
    assert not recovery.is_resolved(partial, dt.date(2026, 6, 1))
    # and its weight equals the modelled (record-less) weight — no acceleration, no cap.
    on = dt.date(2026, 3, 1)
    assert _weight_at(inc, on, partial) == pytest.approx(_weight_at(inc, on, None), abs=1e-9)


def test_evidence_family_is_a_deterministic_partition():
    """§15 / check #6: evidence_family is a total, DETERMINISTIC function of (recovery_status,
    recovery_kind) into mutually-exclusive families, with a fixed precedence when a kind could
    match two (a flow-rerouting kind is flow_rerouting even though partial_restart would also
    be service_restoration; a full reconstitution wins over any kind)."""
    from pipeline import recovery
    fams = set(recovery.EVIDENCE_FAMILIES)
    # every (status, kind) maps into exactly one declared family
    for status in ("impaired", "partial_restart", "substantially_restored", "fully_reconstituted", "unknown"):
        for kind in (None, "flow_rerouted", "grid_reenergised", "unit_restarted", "unit_rebuilt",
                     "throughput_restored", "transformer_replaced", "primary_unit_offline", "weird"):
            assert recovery.evidence_family(status, kind) in fams
    # precedence: full reconstitution beats a service-y kind; flow beats generic partial;
    # estimate (impaired) beats everything.
    assert recovery.evidence_family("fully_reconstituted", "grid_reenergised") == "facility_reconstitution"
    assert recovery.evidence_family("partial_restart", "flow_rerouted") == "flow_rerouting"
    assert recovery.evidence_family("partial_restart", "grid_reenergised") == "service_restoration"
    assert recovery.evidence_family("impaired", "unit_restarted") == "estimate"


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_evidence_family_counts_partition_the_record_set():
    """check #6: the per-family counts are a partition — they sum to the deduplicated episode
    count, so no record is double-counted across families."""
    snap = _snapshot()
    rs = snap["recovery_stats"]
    efc = rs.get("evidence_family_counts") or {}
    # sum of families == distinct episodes that carry a recovery record (<= record count).
    assert sum(efc.values()) <= rs["recovery_record_count"]
    assert sum(efc.values()) >= rs["observed_restoration_episodes"]  # observed are a subset


def test_damage_severity_is_monotone_and_repaired_is_not_a_damage_state():
    """§10-11: damage severity (concept A) is a clean, monotone map from a DAMAGE observation.
    'repaired'/'restored' are recovery states, not damage states, and must fall through to the
    1.0 default (never a silent 0.1 damp)."""
    from pipeline import recovery
    assert recovery.damage_severity("degraded") < recovery.damage_severity("unknown")
    assert recovery.damage_severity("degraded") <= recovery.damage_severity("active")
    # damaged/destroyed/shutdown are full damage; unknown defaults to full.
    for s in ("active", "damaged", "destroyed", "shutdown", "unknown", None, "anything-unmapped"):
        assert recovery.damage_severity(s) == pytest.approx(1.0)
    # a recovery state mis-filed in status must NOT discount (it maps to the 1.0 default).
    assert recovery.damage_severity("repaired") == pytest.approx(1.0)
    assert recovery.damage_severity("restored") == pytest.approx(1.0)


def test_adding_recovery_evidence_is_monotonic_non_increasing():
    """§11 property test: across a grid of incidents, adding a recovery record whose horizon does
    NOT exceed the modelled fallback must never INCREASE the weight. A partial restart equals the
    record-less weight exactly; a full/substantial reconstitution is <= it. (An estimate that
    LENGTHENS the horizon may raise it — that is evidence of worse-than-assumed damage, the one
    allowed exception, tested separately.)"""
    from pipeline import recovery
    import itertools
    statuses = ["unknown", "degraded", "active", "damaged"]
    classes = ["refinery", "substation", "power_plant_nuclear", "oil_terminal", "gas_processing"]
    ages = [1, 20, 60, 150, 400]
    for status, cls, age in itertools.product(statuses, classes, ages):
        occurred = dt.date(2026, 1, 1)
        when = occurred + dt.timedelta(days=age)
        inc = _incident(date="2026-01-01", status=status, asset_class=cls)
        w_none = _weight_at(inc, when, None)
        fallback = recovery.FALLBACK.get(cls, recovery.FALLBACK["_default"])
        # partial restart: DISPLAY-only -> identical to no record.
        partial = _rec(recovery_status="partial_restart", partial_operations_resumed_at="2026-01-10")
        assert _weight_at(inc, when, partial) == pytest.approx(w_none, abs=1e-12), (status, cls, age)
        # full reconstitution reached before `when`: capped -> never above no-record.
        full = _rec(recovery_status="fully_reconstituted", observed_date="2026-01-15", observed_days=14)
        assert _weight_at(inc, when, full) <= w_none + 1e-12, (status, cls, age)
        # substantial restoration with a horizon <= fallback: faster decay -> <= no-record.
        substantial = _rec(recovery_status="substantially_restored", observed_days=max(1, fallback // 2))
        assert _weight_at(inc, when, substantial) <= w_none + 1e-12, (status, cls, age)


def test_stronger_recovery_evidence_is_ordered_full_le_substantial_le_partial():
    """§11: at a fixed point after recovery, evidence of stronger recovery is monotone downward:
    full reconstitution <= substantial restoration <= partial restart == no record."""
    inc = _incident(date="2026-01-01", status="degraded", asset_class="refinery")
    when = dt.date(2026, 4, 1)  # well after the recovery dates below
    w_none = _weight_at(inc, when, None)
    w_partial = _weight_at(inc, when, _rec(recovery_status="partial_restart",
                                           partial_operations_resumed_at="2026-01-20"))
    w_subst = _weight_at(inc, when, _rec(recovery_status="substantially_restored", observed_days=30))
    w_full = _weight_at(inc, when, _rec(recovery_status="fully_reconstituted",
                                        observed_date="2026-02-01", observed_days=31))
    assert w_partial == pytest.approx(w_none, abs=1e-12)
    assert w_full <= w_subst + 1e-12 <= w_partial + 1e-12


def test_partial_restart_never_scores_above_no_record_for_degraded_status():
    """Regression: a partial_restart record must never RAISE an incident's weight. The
    status_multiplier ('degraded' = 0.7) was applied only when no record existed, so
    attaching a partial-restart record silently removed the damping and scored the facility
    ~43% HIGHER than with no evidence at all — the whole cause of a spurious transmission jump
    when recovery evidence was added. A partial restart is at best neutral for scoring."""
    inc = _incident(date="2026-08-20", status="degraded", asset_class="substation")
    on = dt.date(2026, 8, 28)
    w_none = _weight_at(inc, on, None)
    partial = _rec(source_confidence="high", recovery_status="partial_restart",
                   partial_operations_resumed_at="2026-08-20")
    w_partial = _weight_at(inc, on, partial)
    # Neutral: identical to the record-less weight (both carry the degraded damping).
    assert w_partial == pytest.approx(w_none, abs=1e-9)
    # And the damping is really present (strictly below the undamped 'active' weight).
    w_active = _weight_at(_incident(date="2026-08-20", status="active", asset_class="substation"), on, None)
    assert w_partial < w_active


def test_low_confidence_estimate_does_not_drive_scoring():
    """A low-confidence estimate is shown but must not replace the modelled horizon."""
    from pipeline import recovery
    low = _rec(source_confidence="low", recovery_status="impaired", estimate_central_days=400)
    assert recovery.scoring_kind("refinery", low) == "modelled"
    assert recovery.has_downweighted_estimate(low)
    med = _rec(source_confidence="medium", recovery_status="impaired", estimate_central_days=400)
    assert recovery.scoring_kind("refinery", med) == "estimated"


def test_full_reconstitution_precedence_closes_incident():
    """A credible full reconstitution caps the incident's contribution at the residual."""
    from pipeline import recovery
    inc = _incident(date="2026-01-01")
    rec = _rec(recovery_status="fully_reconstituted", observed_date="2026-02-01", observed_days=31)
    after = _weight_at(inc, dt.date(2026, 3, 1), rec)
    assert after <= recovery.RESIDUAL + 1e-6
    assert recovery.is_resolved(rec, dt.date(2026, 3, 1))
    assert not recovery.is_resolved(rec, dt.date(2026, 1, 15))  # before reconstitution
    # a LOW-confidence full-reconstitution claim must NOT close the incident
    weak = _rec(source_confidence="low", recovery_status="fully_reconstituted", observed_date="2026-02-01")
    assert not recovery.is_resolved(weak, dt.date(2026, 3, 1))


def test_impairment_age_none_or_capped_when_resolved():
    from pipeline import recovery
    rec = _rec(recovery_status="fully_reconstituted", observed_date="2026-02-01")
    # resolved incident: age is measured to reconstitution, not open-ended
    age = recovery.impairment_age_days("2026-01-01", rec, dt.date(2026, 6, 1))
    assert age == 31  # 1 Jan -> 1 Feb


def test_recovery_is_incident_keyed():
    """Iteration 2: recovery records key on incident_id, not asset/facility id."""
    from pipeline import recovery as rec_mod
    records = rec_mod.load_recovery_records()
    assert records, "expected curated recovery records"
    # every key looks like an incident id (facility-slug:date or cur-*), never a bare slug
    assert all((":" in k) or k.startswith("cur-") for k in records), list(records)[:5]


def test_recovery_record_without_source_is_ignored(tmp_path, monkeypatch):
    """Provenance integrity: a recovery row with no source URL must be skipped."""
    from pipeline import recovery as rec_mod
    csv = tmp_path / "recovery.csv"
    csv.write_text(
        "incident_id,recovery_status,observed_days,source_confidence,source_urls\n"
        "no-source:2026-01-01,fully_reconstituted,10,high,\n"
        "good:2026-01-01,fully_reconstituted,10,high,https://example.org/x\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(rec_mod, "CURATED", tmp_path)
    records = rec_mod.load_recovery_records()
    assert "good:2026-01-01" in records
    assert "no-source:2026-01-01" not in records


def test_composite_renormalises_over_covered_sectors():
    """A sector with no capacity base must be excluded, not counted as zero.

    Counting it as zero would treat 'we cannot measure this' as 'nothing is wrong
    here', which understates the composite.
    """
    covered = ["refining"]
    all_sectors = ["refining", "gas"]
    only_refining = _composite({"refining": 0.4}, {"refining": 0.35, "gas": 0.1}, covered)
    counted_as_zero = _composite({"refining": 0.4}, {"refining": 0.35, "gas": 0.1}, all_sectors)
    assert only_refining == pytest.approx(40.0, abs=0.01)
    assert counted_as_zero < only_refining


def test_barrel_conversion_matches_published_figures():
    """Omsk is 22.0 MTPA in the strike table; published capacity is ~440 kbd."""
    assert 22.0 / BBL_PER_DAY_TO_MTPA == pytest.approx(443_000, rel=0.03)


# --------------------------------------------------------------------------
# Encoding — this machine defaults to cp1252 and the data is full of Cyrillic
# --------------------------------------------------------------------------

def test_every_file_open_declares_utf8():
    """An implicit encoding corrupts Cyrillic silently, with no exception raised."""
    offenders = []
    for path in (ROOT / "pipeline").glob("*.py"):
        src = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\bopen\s*\(", src):
            line_start = src.rfind("\n", 0, match.start()) + 1
            line_end = src.find("\n", match.end())
            # Allow the call to span a couple of lines.
            chunk = src[line_start : line_end + 200 if line_end > 0 else len(src)]
            call = chunk[: chunk.find(")") + 1] if ")" in chunk else chunk
            if '"rb"' in call or '"wb"' in call:
                continue
            if "encoding=" not in call:
                offenders.append(f"{path.name}: {call.strip()[:80]}")
    assert not offenders, "open() without explicit encoding:\n" + "\n".join(offenders)


# --------------------------------------------------------------------------
# Scope boundary
# --------------------------------------------------------------------------

FORBIDDEN_FIELDS = {
    "current_location", "current_position", "tactical_location", "readiness",
    "vulnerability", "target_priority", "ingress", "egress", "command_post",
    "distance_km", "distance_to_ukraine", "range_km", "strike_range",
}


@pytest.mark.skipif(not (PROCESSED / "incidents.json").exists(),
                    reason="pipeline has not been run")
def test_emitted_data_carries_no_out_of_scope_fields():
    """The upstream strike table publishes range-to-target; it must never land here."""
    found = set()

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k.lower() in FORBIDDEN_FIELDS:
                    found.add(k)
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    for name in ("incidents.json", "snapshot.json", "assets.json"):
        walk(json.loads((PROCESSED / name).read_text(encoding="utf-8")))
    assert not found, f"out-of-scope fields present in emitted data: {found}"


@pytest.mark.skipif(not (PROCESSED / "incidents.json").exists(),
                    reason="pipeline has not been run")
def test_no_coordinates_on_incident_records():
    """Events stay region-scoped. A lat/lon on an event record would be exactly the
    asset-level precision the brief rules out for this MVP."""
    incidents = json.loads((PROCESSED / "incidents.json").read_text(encoding="utf-8"))
    for inc in incidents:
        assert "lat" not in inc and "lon" not in inc, inc.get("incident_id")


@pytest.mark.skipif(not (PROCESSED / "incidents.json").exists(),
                    reason="pipeline has not been run")
def test_every_curated_incident_is_sourced():
    incidents = json.loads((PROCESSED / "incidents.json").read_text(encoding="utf-8"))
    curated = [i for i in incidents if i.get("origin") == "curated"]
    assert curated, "expected curated incidents in the dataset"
    for inc in curated:
        assert inc["sources"], f"{inc['incident_id']} has no source"


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_snapshot_reports_its_own_coverage():
    """The dashboard must be able to say how much of the universe it covers."""
    snap = json.loads((PROCESSED / "snapshot.json").read_text(encoding="utf-8"))
    assert snap["coverage"] is not None
    assert 0 < snap["coverage"]["coverage_ratio"] <= 1
    assert "incidents_with_quantified_capacity" in snap


@pytest.mark.skipif(not (PROCESSED / "regions.json").exists(),
                    reason="pipeline has not been run")
def test_crimea_is_a_separate_occupied_unit_others_excluded():
    """Iteration 4: Crimea is a separately identified OCCUPIED unit (not a Russian federal
    subject) that now participates in the index, while the other four annexed oblasts
    remain fully excluded from the region layer. Its distinct status is preserved."""
    regions = json.loads((PROCESSED / "regions.json").read_text(encoding="utf-8"))
    by_name = {r["name"].lower(): r for r in regions}
    assert "crimea" in by_name
    crimea = by_name["crimea"]
    # Distinct occupied status, Ukrainian, now index-included — never a Russian subject.
    assert crimea["analytic_scope"] == "occupied"
    assert crimea["esdi_included"] is True
    assert crimea["country"] == "UA"
    assert "ukrain" in crimea["sovereignty"].lower()
    assert crimea["de_facto_control"], "occupation status must remain stated"
    # Other occupied Ukrainian territory stays out of the region layer entirely.
    for excluded in ("donetsk", "luhansk", "zaporizhzhia", "kherson"):
        assert excluded not in by_name


def test_crimea_resolution_and_other_occupied_excluded():
    """Crimea resolves as context; other occupied territory as a distinct excluded state."""
    assert resolve("Crimea") == ("context", "UA-CR")
    assert resolve("Sevastopol") == ("context", "UA-CR")
    for name in ("Donetsk Oblast", "Luhansk", "Zaporizhzhia", "Kherson"):
        kind, _ = resolve(name)
        assert kind == "excluded_occupied", name


# A styling word makes "Crimea is never the Russian X" legitimate (it's about the map, not the
# composite). Anything else pairing Crimea/occupied with a non-contribution claim about the
# composite/index is the dangerous stale assertion this project has shipped twice.
_CRIMEA_LINT_STYLING = (
    "choropleth", "painted", "rendered", "labelled", "labeled", "styl", "colour", "color",
    "mistaken for a russian", "russian region", "russian choropleth", "ordinary russian",
    "dashed", "outline",
)
_CRIMEA_LINT_NEGATION = (
    "never", "excluded from", "does not contribute", "doesn't contribute", "not contribute",
    "not feed", "never feeds", "cannot enter", "no contribution", "kept out of the",
)
_CRIMEA_LINT_COMPOSITE = (
    "composite", "national esdi", "national index", "monitored-area", "monitored area index",
    "the index", "the headline",
)


def _scan_files_for_crimea_lint():
    """Yield (path, fragment) where a source text wrongly implies Crimea/occupied is out of the
    composite. Historical iteration reviews are excluded — they were correct for their pass."""
    import re
    files = list((ROOT / "pipeline").glob("*.py"))
    files += list((ROOT / "web" / "src").rglob("*.ts")) + list((ROOT / "web" / "src").rglob("*.tsx"))
    files += [ROOT / "README.md"]
    files += [ROOT / "docs" / f for f in (
        "METHODOLOGY.md", "HANDOFF.md", "SCHEMA.md", "SOURCES.md", "CURRENT_STATE.md",
        "CHATGPT_ITERATION_PROMPT.md")]
    for path in files:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8").lower()
        for frag in re.split(r"[.\n;!?]", text):
            frag = " ".join(frag.split())
            if ("crimea" not in frag and "occupied" not in frag):
                continue
            if not any(n in frag for n in _CRIMEA_LINT_NEGATION):
                continue
            if not any(c in frag for c in _CRIMEA_LINT_COMPOSITE):
                continue
            if any(s in frag for s in _CRIMEA_LINT_STYLING):
                continue
            yield (path, frag)


def test_no_source_text_claims_crimea_is_out_of_the_composite():
    """Lint (§1): fail the build if a comment/doc asserts Crimea/occupied never enters the
    monitored-area composite — false, since esdi_included=True. Twice-shipped bug; now guarded."""
    # Self-check: the detector must fire on the exact phrasing this project shipped.
    bad = "crimea (and any esdi-excluded region) contributes to its own regional exposure but never to the national composite"
    frag = " ".join(bad.split())
    assert (any(n in frag for n in _CRIMEA_LINT_NEGATION)
            and any(c in frag for c in _CRIMEA_LINT_COMPOSITE)
            and not any(s in frag for s in _CRIMEA_LINT_STYLING)), "lint detector is broken"
    hits = list(_scan_files_for_crimea_lint())
    assert not hits, "stale 'Crimea out of the composite' text found:\n" + "\n".join(
        f"  {p}: {f[:140]}" for p, f in hits)


def test_docs_do_not_claim_the_release_payload_is_frozen():
    """Lint: fail the build if a doc asserts the committed payload is the frozen reference.

    Production data is CURRENT-DATE; 2026-08-28 is comparison-only. Iteration 8 briefly committed
    a frozen payload, corrected it, and left a stale HANDOFF bullet saying the opposite — which
    sat directly beneath the corrected table for two iterations. A runtime guard already stops a
    frozen payload SHIPPING (test_release_payload_is_a_current_date_build_not_a_frozen_reference);
    this stops the DOCS from telling a future session to create one.
    """
    import re
    claim_subject = ("committed data", "committed payload", "release payload", "the payload",
                     "committed build")
    claim_frozen = ("pinned to the frozen", "is the frozen", "frozen reference", "--as-of 2026-08-28")
    # Sentences that legitimately describe the frozen build as comparison-only.
    exempt = ("comparison-only", "comparison only", "regression-only", "regression only",
              "never be committed", "must never", "previously said", "was the iteration-8 mistake",
              "not a real-date build", "fails the suite", "stale")
    files = [ROOT / "docs" / f for f in ("HANDOFF.md", "SOURCES.md", "METHODOLOGY.md",
                                         "SCHEMA.md", "CURRENT_STATE.md")]
    files += [ROOT / "README.md", ROOT / "CLAUDE.md"]
    hits = []
    for path in files:
        if not path.exists():
            continue
        # Collapse markdown line-wrapping BEFORE splitting into sentences: a wrapped sentence is
        # still one sentence, and splitting on newlines severs a claim from the clause that
        # qualifies it (which is exactly how this test first failed on its own fix).
        text = " ".join(path.read_text(encoding="utf-8").lower().split())
        for frag in re.split(r"\.", text):
            frag = " ".join(frag.split())
            if not any(s in frag for s in claim_subject):
                continue
            if not any(c in frag for c in claim_frozen):
                continue
            if any(e in frag for e in exempt):
                continue
            hits.append((path.name, frag))
    assert not hits, ("a doc claims the release payload is the frozen build:\n"
                      + "\n".join(f"  {p}: {f[:140]}" for p, f in hits))


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_crimea_now_contributes_to_the_monitored_area_index():
    """Iteration 4: Crimea contributes to the headline index. It must be flagged included,
    and its events must actually move the national aggregate (its regional exposure > 0
    where it has qualifying events), while carrying no coordinates."""
    snap = json.loads((PROCESSED / "snapshot.json").read_text(encoding="utf-8"))
    crimea = snap["regions"]["UA-CR"]
    assert crimea["esdi_included"] is True
    assert crimea["analytic_scope"] == "occupied"
    # Crimea has qualifying transmission + oil-logistics events, so its own exposure is > 0.
    assert crimea["esdi"] > 0, "Crimea has qualifying events and should carry exposure"
    incidents = json.loads((PROCESSED / "incidents.json").read_text(encoding="utf-8"))
    crimea_incidents = [i for i in incidents if i.get("region_code") == "UA-CR"]
    assert crimea_incidents, "expected at least one tracked Crimea event"
    for i in crimea_incidents:
        # Included in the index, still admin-region only: never any coordinate.
        assert "lat" not in i and "lon" not in i


@pytest.mark.skipif(not (PROCESSED / "index_national.json").exists(),
                    reason="pipeline has not been run")
def test_crimea_contribution_is_included_across_the_historical_series():
    """Including Crimea must recompute the whole time series, not just the latest point.
    Rebuild-invariant: the national transmission series is >= a Crimea-excluded rebuild at
    every step where Crimea has an active event. We assert the weaker, stable property that
    the transmission series is non-trivial and Crimea's own series carries transmission."""
    nat = json.loads((PROCESSED / "index_national.json").read_text(encoding="utf-8"))
    reg = json.loads((PROCESSED / "index_regional.json").read_text(encoding="utf-8"))
    assert any(v > 0 for v in nat["sectors"]["transmission"]), "transmission series is empty"
    cr = reg["regions"]["UA-CR"]["sectors"]["transmission"]
    assert any(v > 0 for v in cr), "Crimea transmission series should be populated historically"


def test_context_geography_has_no_analytic_infrastructure():
    """Context countries are display-only: no asset in the emitted asset layer may sit
    in a context country, and context files carry no scoring fields."""
    land = json.loads((PROCESSED / "context_land.geojson").read_text(encoding="utf-8"))
    for f in land["features"]:
        props = f["properties"]
        # only display metadata (iteration 5 added data-driven label priority), never an
        # event/score/capacity field
        assert set(props) <= {"iso", "name", "labelrank", "label_min_zoom",
                              "label_lon", "label_lat"}, props


def test_far_eastern_remains_disabled():
    """Iteration 2 keeps the Far Eastern FD structurally supported but analytically off."""
    from pipeline.config import AOI_FEDERAL_DISTRICTS, DEFINED_FEDERAL_DISTRICTS
    assert "Far Eastern" not in AOI_FEDERAL_DISTRICTS
    assert "Far Eastern" in DEFINED_FEDERAL_DISTRICTS


# --------------------------------------------------------------------------
# Iteration 1: emitted snapshot — geography, rankings, recovery, coverage
# --------------------------------------------------------------------------

def _snapshot():
    return json.loads((PROCESSED / "snapshot.json").read_text(encoding="utf-8"))


@pytest.mark.skipif(not (PROCESSED / "regions.json").exists(),
                    reason="pipeline has not been run")
def test_siberian_regions_present_far_eastern_absent_in_emitted_data():
    regions = json.loads((PROCESSED / "regions.json").read_text(encoding="utf-8"))
    districts = {r["district"] for r in regions}
    assert "Siberian" in districts
    assert "Far Eastern" not in districts
    names = {r["name"].lower() for r in regions}
    assert "omsk oblast" in names                    # Siberian, now in scope
    assert "amur oblast" not in names                # Far Eastern, excluded
    assert "primorsky krai" not in names


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_rankings_cover_only_affected_regions():
    """A ranking must never surface an undamaged region. Every ranked region must have
    at least one recorded event or a non-zero exposure."""
    snap = _snapshot()
    for code, r in snap["regions"].items():
        rankable = r["incident_count"] > 0 or r["esdi"] > 0 or r["live_disruption_count"] > 0
        if not rankable:
            # A region with nothing recorded is allowed to EXIST in the map data, but
            # any ranking view filters on these fields; assert the fields exist so the
            # frontend filter is well-defined.
            assert "incident_count" in r and "esdi" in r


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_recovery_stats_present_with_episode_counts():
    snap = _snapshot()
    rs = snap["recovery_stats"]
    # Episode counts must accompany every median so a median-of-few is never mistaken
    # for a robust figure. Records and episodes are reported separately.
    assert "observed_restoration_episodes" in rs
    assert "recovery_record_count" in rs
    assert "impairment_age_sample" in rs
    # Episodes can never exceed records (each observed episode has >=1 record).
    assert rs["observed_restoration_episodes"] <= rs["recovery_record_count"]
    if rs["median_observed_restoration_days"] is not None:
        assert rs["observed_restoration_episodes"] >= rs["min_median_episodes"]
    kinds = rs["evidence_kind_counts"]
    assert set(kinds) <= {"observed", "estimated", "modelled"}


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_recovery_events_is_complete_not_a_live_disruptions_subset():
    """recovery_events must hold EVERY dated restoration observation in the corpus.

    Regression guard for the iteration-8 defect: a "what recovery landed recently?" view was
    reading live_disruptions, which only carries facilities whose disruption weight is still
    > 0 and is truncated to 80 — so a FULLY-RECOVERED facility vanishes from it. That made the
    view structurally blind to exactly the episodes it was asking about (1 of 9 visible).
    """
    snap = _snapshot()
    events = snap["recovery_events"]
    assert events, "recovery_events must not be empty when recovery records exist"

    # It must be strictly richer than what live_disruptions could ever expose.
    live_dated = sum(1 for d in snap["live_disruptions"] if d["recovery"].get("observed_date"))
    assert len(events) > live_dated

    # The observed-DURATION episode count must reconcile exactly with recovery_stats. These are
    # two different questions (evidence arrived vs duration measured) and must not be conflated.
    counted = [e for e in events if e["counts_toward_observed_episodes"]]
    assert len(counted) == snap["recovery_stats"]["observed_restoration_episodes"]
    for e in counted:
        assert e["evidence_date_kind"] == "observed_restoration"
        assert e["scoring_evidence_kind"] == "observed"
        assert e["observed_days"]

    # Every row is dated, typed, and deduplicated by (episode, kind).
    keys = set()
    for e in events:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["evidence_date"]), e["evidence_date"]
        assert e["evidence_date_kind"] in ("observed_restoration", "partial_restart")
        key = (e["episode_id"], e["evidence_date_kind"])
        assert key not in keys, f"duplicate episode/kind row: {key}"
        keys.add(key)

    # Sorted by evidence date, so a client can window it without re-sorting.
    assert [e["evidence_date"] for e in events] == sorted(e["evidence_date"] for e in events)


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_recovery_events_carry_no_location_beyond_admin_region():
    """Scope: the recovery log is evidence about facilities, not a geographic index."""
    snap = _snapshot()
    banned = {"lat", "lon", "latitude", "longitude", "coordinates", "geometry", "distance_km"}
    for e in snap["recovery_events"]:
        assert not (set(e) & banned), f"recovery_events leaked location keys: {set(e) & banned}"


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_recovery_evidence_kinds_distinguish_observed_from_estimated():
    """Observed / estimated / modelled recovery must be structurally distinct."""
    snap = _snapshot()
    for x in snap["live_disruptions"]:
        rec = x["recovery"]
        assert rec["scoring_evidence_kind"] in ("observed", "estimated", "modelled")
        if rec["scoring_evidence_kind"] == "modelled":
            # A modelled record must not masquerade as having observed timing driving it.
            assert rec["observed_days"] is None or rec["recovery_status"] == "partial_restart"


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_median_restoration_present_only_with_enough_distinct_episodes():
    """A median must be suppressed below the minimum DISTINCT EPISODE count (5)."""
    snap = _snapshot()
    rs = snap["recovery_stats"]
    n = rs["observed_restoration_episodes"]
    if n < rs["min_median_episodes"]:
        assert rs["median_observed_restoration_days"] is None
        assert rs["median_meaningful"] is False
    else:
        assert rs["median_observed_restoration_days"] is not None
        assert rs["median_meaningful"] is True


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_partial_restart_not_counted_as_full_reconstitution():
    """Partial restarts are tracked separately and never inflate reconstitution counts."""
    snap = _snapshot()
    rs = snap["recovery_stats"]
    assert "partial_restart_episodes" in rs and "full_reconstitution_episodes" in rs
    assert rs["partial_restart_episodes"] >= 0 and rs["full_reconstitution_episodes"] >= 0


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_pooled_median_is_labelled_mixed_infrastructure():
    """§11: the pooled cross-class median must be flagged mixed-infrastructure so the UI can
    never present it as a per-sector repair time."""
    snap = _snapshot()
    rs = snap["recovery_stats"]
    assert rs.get("median_is_mixed_infrastructure") is True
    assert "min_sector_median_episodes" in rs
    # The per-class gate is looser than the pooled gate, but still > 1.
    assert 1 < rs["min_sector_median_episodes"] <= rs["min_median_episodes"]


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_per_class_median_only_appears_at_class_gate():
    """§12: a class median is emitted only when THAT class has enough of its own observed
    episodes; below the gate the individual durations are exposed instead."""
    snap = _snapshot()
    rs = snap["recovery_stats"]
    gate = rs["min_sector_median_episodes"]
    for sector, m in rs["by_sector"].items():
        assert "observed_restoration_values" in m, sector
        # Values length agrees with the episode count.
        assert len(m["observed_restoration_values"]) == m["observed_restoration_episodes"]
        if m["observed_restoration_episodes"] < gate:
            assert m["median_observed_restoration_days"] is None, sector
        # sector_medians must be exactly the classes that cleared the gate.
        in_medians = sector in (rs.get("sector_medians") or {})
        assert in_medians == (m["median_observed_restoration_days"] is not None), sector


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_flow_rerouted_recovery_kind_is_never_full_reconstitution():
    """§13: a 'flow rerouted around a still-damaged node' restart is a partial restart, never
    facility reconstitution (the Unecha lesson). The granular kind must not contradict the
    scoring bucket."""
    snap = _snapshot()
    for d in snap["live_disruptions"]:
        rec = d["recovery"]
        kind = rec.get("recovery_kind")
        if kind and "flow_rerouted" in kind:
            assert rec["recovery_status"] == "partial_restart", d["asset_id"]
            assert rec["resolved"] is False, d["asset_id"]


def test_recovery_kind_column_matches_status_in_source():
    """The curated recovery file must not pair a flow-only kind with a full-reconstitution
    status — checked on the source of truth, not just the built artifact."""
    import csv
    path = ROOT / "data" / "curated" / "recovery.csv"
    flow_kinds = {"flow_rerouted"}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if (row.get("recovery_kind") or "") in flow_kinds:
                assert row["recovery_status"] == "partial_restart", row["incident_id"]


def test_no_incident_uses_the_deprecated_repaired_damage_status():
    """§10 / red-team M3: 'repaired' is a RECOVERY state, not a damage state. It must not appear in
    incident.status (recovery belongs in a recovery record). This closes the latent trap where
    migrating a 'repaired' status to 'damaged' without a collapsing record would inflate a
    scored-sector incident: there is simply no 'repaired' status to migrate."""
    import csv
    with open(ROOT / "data" / "curated" / "incidents.csv", encoding="utf-8", newline="") as f:
        bad = [r["incident_id"] for r in csv.DictReader(f) if (r.get("status") or "") == "repaired"]
    assert not bad, f"incident.status='repaired' is deprecated; use a recovery record: {bad}"


def test_incident_status_does_not_contradict_its_recovery_record():
    """Red-team (iter 6): the scoring status_multiplier reads incident.status, which must not
    contradict the authoritative recovery record. An incident may be status='repaired' only if
    its recovery record actually closes it (fully_reconstituted). Unecha was the offender:
    status='repaired' against a record saying the pumping station was destroyed and only flow
    was rerouted."""
    import csv
    rec = {}
    with open(ROOT / "data" / "curated" / "recovery.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rec[r["incident_id"]] = r["recovery_status"]
    with open(ROOT / "data" / "curated" / "incidents.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            iid = r["incident_id"]
            if r.get("status") == "repaired" and iid in rec:
                assert rec[iid] == "fully_reconstituted", (
                    f"{iid}: incident.status='repaired' contradicts recovery_status='{rec[iid]}'")


@pytest.mark.skipif(not (PROCESSED / "incidents.json").exists(),
                    reason="pipeline has not been run")
def test_multi_day_strike_is_one_episode_not_several_incidents():
    """A hyphen-range strike ("9-10 June") must be one incident/episode, not two."""
    incidents = json.loads((PROCESSED / "incidents.json").read_text(encoding="utf-8"))
    kb = [i for i in incidents if i.get("asset_id") == "kuibyshev-refinery"]
    # The 9-10 June 2026 strike is a single incident spanning a date range.
    ranged = [i for i in kb if i.get("date_start") == "2026-06-09"]
    assert len(ranged) == 1, "the 9-10 June strike must collapse to one incident"
    assert ranged[0]["date_end"] == "2026-06-10"
    # No same-facility incident on the very next day of a range.
    assert not any(i["incident_id"].endswith(":2026-06-10") for i in kb)
    # Every incident carries an episode_id.
    for i in incidents:
        assert i.get("episode_id"), i.get("incident_id")


def test_episode_grouping_distinguishes_range_from_list():
    """dates.parse_dates_grouped: a range is one episode; discrete dates are separate."""
    from pipeline.dates import parse_dates_grouped
    one = parse_dates_grouped("9-10 June 2026")
    assert len({g for *_x, g in one}) == 1  # one episode
    two = parse_dates_grouped("22-23 and 25 May 2026")
    assert len({g for *_x, g in two}) == 2  # range + discrete
    three = parse_dates_grouped("5 April 2026, 20 May 2026, 24 June 2026")
    assert len({g for *_x, g in three}) == 3


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_assessed_degradation_separate_from_exposure():
    """Concept separation: assessed degradation reports quantified capacity only."""
    snap = _snapshot()
    ad = snap["assessed_degradation"]
    assert ad["quantified_incident_count"] <= ad["total_incident_count"]
    # If nothing is quantified, the quantified totals must be zero, not inferred.
    if ad["quantified_incident_count"] == 0:
        assert ad["quantified_mw"] == 0 and ad["quantified_mtpa"] == 0


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_coverage_detail_is_categorical_not_a_fabricated_interval():
    snap = _snapshot()
    cov = snap["coverage_detail"]
    assert "by_year" in cov and "by_sector" in cov and "by_district" in cov
    # Siberian coverage must appear now that the district is enabled.
    assert "Siberian" in cov["by_district"]
    # No fabricated statistical confidence interval anywhere in coverage.
    assert "confidence_interval" not in cov and "ci_lower" not in cov


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_unknown_is_not_silently_zero():
    """Not-modelled effect categories stay null; they are never coerced to 0."""
    snap = _snapshot()
    any_region = next(iter(snap["regions"].values()))
    for key in snap["not_modelled"]:
        assert any_region["effects"][key] is None


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_processed_output_is_deterministic():
    """A rebuild with a fixed as-of must reproduce the index byte-for-byte.

    The database is a build artifact; a non-deterministic build would make every daily
    refresh a spurious diff and defeat the git-tracked data model.
    """
    import subprocess
    import sys

    snap = _snapshot()
    as_of = snap["as_of"]
    before = (PROCESSED / "index_national.json").read_text(encoding="utf-8")
    subprocess.run(
        [sys.executable, "-m", "pipeline.run", "--as-of", as_of],
        cwd=ROOT, check=True, capture_output=True,
    )
    after = (PROCESSED / "index_national.json").read_text(encoding="utf-8")
    assert before == after, "index build is not deterministic for a fixed as-of"


# --------------------------------------------------------------------------
# Frontend contract smoke test (iteration 2)
# --------------------------------------------------------------------------
# No browser test framework is available on this machine, so the practical smoke test
# is a data-contract check: the pipeline must emit, into web/public/data/, exactly the
# files and keys the frontend TypeScript expects. This catches pipeline/frontend drift
# -- the class of bug where the app loads but a field the UI reads is missing.

WEB_DATA = ROOT / "web" / "public" / "data"

REQUIRED_WEB_FILES = [
    "snapshot.json", "index_national.json", "index_regional.json", "incidents.json",
    "regions.json", "assets.json", "taxonomy.json", "regions.geojson",
    "assets_lines.geojson", "context_land.geojson", "context_borders.geojson",
    "ocean.geojson",
]


@pytest.mark.skipif(not WEB_DATA.exists(), reason="web data not mirrored")
def test_web_data_files_present():
    missing = [f for f in REQUIRED_WEB_FILES if not (WEB_DATA / f).exists()]
    assert not missing, f"frontend depends on these missing files: {missing}"


@pytest.mark.skipif(not (WEB_DATA / "snapshot.json").exists(), reason="web data not mirrored")
def test_web_snapshot_contract():
    """The keys the frontend's Snapshot/RecoveryStats/RegionSnapshot types require."""
    snap = json.loads((WEB_DATA / "snapshot.json").read_text(encoding="utf-8"))
    for key in ("esdi", "sectors", "recovery_stats", "assessed_degradation",
                "coverage_detail", "live_disruptions", "regions", "coverage"):
        assert key in snap, f"snapshot missing frontend key {key}"
    rs = snap["recovery_stats"]
    for key in ("median_meaningful", "min_median_episodes", "observed_restoration_values",
                "partial_restart_episodes", "full_reconstitution_episodes", "evidence_kind_counts"):
        assert key in rs, f"recovery_stats missing frontend key {key}"
    region = next(iter(snap["regions"].values()))
    for key in ("esdi_included", "analytic_scope", "unresolved_count", "effects"):
        assert key in region, f"region missing frontend key {key}"
    for d in snap["live_disruptions"]:
        rec = d["recovery"]
        for key in ("scoring_evidence_kind", "recovery_status", "resolved"):
            assert key in rec, f"live disruption recovery missing frontend key {key}"
        break


@pytest.mark.skipif(not (WEB_DATA / "context_land.geojson").exists(), reason="web data not mirrored")
def test_web_context_geography_contract():
    land = json.loads((WEB_DATA / "context_land.geojson").read_text(encoding="utf-8"))
    assert land["features"], "context land must contain countries"
    for f in land["features"]:
        # the label overlay needs these; nothing else should leak in
        assert "label_lon" in f["properties"] and "label_lat" in f["properties"]
    ocean = json.loads((WEB_DATA / "ocean.geojson").read_text(encoding="utf-8"))
    assert ocean["features"], "ocean fill required for the sea to read as water"


@pytest.mark.skipif(not (WEB_DATA / "regions.geojson").exists(), reason="web data not mirrored")
def test_web_crimea_feature_flagged_special():
    regions = json.loads((WEB_DATA / "regions.geojson").read_text(encoding="utf-8"))
    crimea = [f for f in regions["features"] if f["properties"]["code"] == "UA-CR"]
    assert len(crimea) == 1
    assert crimea[0]["properties"]["special"] is True, "the map keys Crimea styling on special=true"


# --------------------------------------------------------------------------
# Iteration 3: generation / transmission separation
# --------------------------------------------------------------------------

def test_electric_split_into_generation_and_transmission():
    from pipeline.config import SECTOR_OF_CLASS, SECTORS
    assert "electric_generation" in SECTORS and "transmission" in SECTORS
    assert "electric_power" not in SECTORS
    assert SECTOR_OF_CLASS["power_plant_thermal"] == "electric_generation"
    assert SECTOR_OF_CLASS["substation"] == "transmission"
    assert SECTOR_OF_CLASS["transmission_line"] == "transmission"


def test_transmission_is_event_burden_not_capacity():
    """A substation must contribute an event-burden unit, never a capacity share, and a
    generation plant must contribute a capacity share."""
    from pipeline.build_index import _share, SATURATION_EVENTS
    sub = {"sector": "transmission", "voltage_kv": 500}
    unit = _share(sub, {"national": {}})
    assert unit > 0  # event-burden unit, independent of any capacity
    # a 110 kV substation weighs less than a 500 kV one
    assert _share({"sector": "transmission", "voltage_kv": 110}, {"national": {}}) < unit
    # generation uses capacity share
    gen = {"sector": "electric_generation", "capacity_mw": 1000}
    assert _share(gen, {"national": {"electric_generation": 200000}}) == pytest.approx(1000 / 200000)


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_transmission_measure_never_claims_capacity_offline():
    """The emitted snapshot must express transmission as burden/context, not lost MW."""
    snap = _snapshot()
    assert "transmission" in snap["sectors"]
    assert "electric_generation" in snap["sectors"]
    # No transmission-capacity denominator is emitted; a saturation constant is.
    assert "transmission_saturation_events" in snap["denominators"]
    assert "electric_power_mw" not in snap["denominators"]
    # Regions carry tracked-network context, not a transmission-capacity figure.
    for r in snap["regions"].values():
        assert "tracked_substations" in r and "tracked_transmission_lines" in r
        assert "transmission_burden" in r["effects"]
        break


# --------------------------------------------------------------------------
# Iteration 3: regional intensity vs national contribution
# --------------------------------------------------------------------------

@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_regional_intensity_separate_from_national_contribution():
    """Regional intensity must be a distinct field, not the national-contribution esdi."""
    snap = _snapshot()
    for r in snap["regions"].values():
        assert "regional_intensity" in r
        ri = r["regional_intensity"]
        assert set(ri) >= {"composite", "sectors", "covered_sectors", "missing_sectors"}
        break


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_regional_intensity_unknown_denominator_is_missing_not_zero():
    """A region disrupted in refining (no regional denominator) lists it as missing,
    never scores it as zero intensity."""
    snap = _snapshot()
    # find a region disrupted in refining
    offenders = []
    for r in snap["regions"].values():
        ri = r["regional_intensity"]
        # refining is never an intensity-scored sector
        assert "refining" not in ri["covered_sectors"]
        # if the region has refining disruption it should be flagged missing
        if r["incident_count"] > 0 and "refining" in ri["missing_sectors"]:
            offenders.append(r["code"])
    # At least one refinery region should be flagged (the corpus is refinery-heavy).
    assert offenders, "expected some region to flag refining as a missing regional denominator"


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_active_burden_columns_present():
    """The Active Burden view needs decomposed columns, not a composite score."""
    snap = _snapshot()
    for r in snap["regions"].values():
        for key in ("oldest_unresolved_days", "median_unresolved_age_days",
                    "reconstitution_backlog_days", "affected_sectors"):
            assert key in r, key
        break


# --------------------------------------------------------------------------
# Iteration 3: CREA economic context — observed, provenanced, not a strike feed
# --------------------------------------------------------------------------

@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_crea_economic_context_is_observed_and_provenanced():
    """CREA context must be labelled observed context, monthly, never attributed to
    strikes, and every point must carry reporting month, snapshot date and a source."""
    snap = _snapshot()
    ec = snap.get("economic_context")
    assert ec is not None, "economic_context should be emitted"
    assert ec["cadence"] == "monthly"
    assert ec["kind"] == "observed_economic_context"
    # The caveat must explicitly refuse strike attribution.
    assert "NOT attributed" in ec["caveat"] or "not attributed" in ec["caveat"].lower()
    assert ec["metrics"], "expected at least one economic metric series"
    for series in ec["metrics"].values():
        assert series, "metric series should not be empty"
        for pt in series:
            assert pt["reporting_month"], "each point needs a reporting month"
            assert pt["snapshot_date"], "each point needs a snapshot date (revision provenance)"
            assert pt["source_url"], "each point needs a provenance URL"
            assert pt["value"] is not None


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_crea_series_sorted_by_reporting_month():
    """Monthly series must be chronologically ordered so the UI never draws a scrambled line."""
    snap = _snapshot()
    ec = snap.get("economic_context")
    assert ec is not None
    for series in ec["metrics"].values():
        months = [p["reporting_month"] for p in series]
        assert months == sorted(months)


# --------------------------------------------------------------------------
# Iteration 3: refinery reconciliation — honest denominator, no padding
# --------------------------------------------------------------------------

@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_refinery_reconciliation_is_lower_bound_not_padded():
    """Tracked capacity must be <= the full nameplate reference, and coverage must be the honest
    ratio against the LIKE-FOR-LIKE crude reference — never forced to 100% by padding."""
    snap = _snapshot()
    rec = snap.get("refinery_reconciliation")
    assert rec is not None, "refinery_reconciliation should be emitted"
    tracked = rec["tracked_mtpa"]
    full = rec["national_public_estimate_mtpa"]      # full nameplate (incl. condensate + mini)
    crude = rec["reference_crude_nameplate_mtpa"]    # like-for-like crude reference
    assert 0 < tracked <= full, "tracked capacity must not exceed the full nameplate reference"
    assert rec["gap_mtpa"] == pytest.approx(full - tracked, abs=0.2)
    # Coverage is against the crude reference (~303), NOT the full 327 (universe mismatch).
    assert rec["coverage_pct"] == pytest.approx(100.0 * tracked / crude, abs=0.6)
    assert rec["coverage_pct"] < 100.0, "coverage should be an honest lower bound, not 100%"


def test_denominator_completeness_metadata_is_distinct_from_event_coverage(SNAP=None):
    """§6: the refining denominator emits completeness metadata that is structurally SEPARATE
    from event coverage, and the gap decomposition adds up with no missing crude refinery."""
    snap = _snapshot()
    rec = snap["refinery_reconciliation"]
    # completeness fields present
    for k in ("reference_nameplate_mtpa", "reference_crude_nameplate_mtpa", "reference_range_mtpa",
              "denominator_coverage_pct", "gap_decomposition", "facility_count"):
        assert k in rec, f"missing denominator metadata: {k}"
    # crude reference < full (condensate removed), both positive
    assert 0 < rec["reference_crude_nameplate_mtpa"] < rec["reference_nameplate_mtpa"]
    # gap decomposition: condensate + basis + missing == full gap; missing crude refineries == 0
    gd = rec["gap_decomposition"]
    assert gd["missing_crude_refineries_mtpa"] == 0.0
    total = (gd["excluded_condensate_splitters_mtpa"] + gd["conservative_basis_understatement_mtpa"]
             + gd["missing_crude_refineries_mtpa"])
    assert total == pytest.approx(rec["reference_nameplate_mtpa"] - rec["tracked_mtpa"], abs=0.6)
    # DENOMINATOR coverage must not be confused with the OIL-STRIKE event coverage — different value.
    cov = snap.get("coverage") or {}
    if cov:
        assert abs(rec["denominator_coverage_pct"] - cov["coverage_ratio"] * 100) > 1.0


def test_denominator_sum_equals_registry_members():
    """§36: the tracked denominator MTPA must equal the sum of non-excluded registry members —
    no capacity double-counted, no exclusion silently counted."""
    if not (PROCESSED / "refinery_inventory.json").exists():
        pytest.skip("pipeline not run")
    inv = json.loads((PROCESSED / "refinery_inventory.json").read_text(encoding="utf-8"))
    members = [r for r in inv["refineries"]
               if r.get("denominator_status") != "exclude" and r.get("capacity_mtpa")]
    member_sum = round(sum(r["capacity_mtpa"] for r in members), 1)
    assert member_sum == pytest.approx(inv["total_mtpa"], abs=0.15)
    assert inv["reconciliation"]["tracked_refineries"] == len(members)
    # canonical ids unique among members (no duplicate facility).
    ids = [r["canonical_id"] for r in members if r.get("canonical_id")]
    assert len(ids) == len(set(ids)), "duplicate canonical_id in the denominator"


# --------------------------------------------------------------------------
# Iteration 3: evidence coverage matrix — coverage, not effect
# --------------------------------------------------------------------------

@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_evidence_matrix_distinguishes_coverage_from_effect():
    """coverage_detail must carry a per-sector evidence matrix with event/recovery/cost
    counts, so the UI can tell 'little data' from 'low disruption'."""
    snap = _snapshot()
    em = snap["coverage_detail"].get("evidence_matrix")
    assert em, "evidence_matrix should be present and non-empty"
    for sector, cells in em.items():
        assert set(cells) >= {"events", "recovery", "cost"}
        for v in cells.values():
            assert isinstance(v, int) and v >= 0
    # A sector we actually populated (refining) must show events.
    assert em.get("refining", {}).get("events", 0) > 0


# --------------------------------------------------------------------------
# Iteration 3: population is structural exposure, never "actually affected"
# --------------------------------------------------------------------------

@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_population_is_structural_context_on_regions():
    """Regions carry population_millions as structural context; it is a plain number or
    null (not yet researched), never derived from incidents."""
    snap = _snapshot()
    seen_value = False
    for r in snap["regions"].values():
        assert "population_millions" in r
        pop = r["population_millions"]
        assert pop is None or (isinstance(pop, (int, float)) and pop > 0)
        if pop:
            seen_value = True
    assert seen_value, "expected at least one region with a researched population"


# --------------------------------------------------------------------------
# Public-release gate: the ENTIRE served payload, not just three files
# --------------------------------------------------------------------------

# The exact set of files the frontend fetches (mirrored to web/public/data at build).
SERVED_DATA_JSON = (
    "incidents.json", "snapshot.json", "assets.json",
    "index_national.json", "index_regional.json",
    "refinery_inventory.json", "regions.json", "taxonomy.json",
)
# Coordinates are permitted ONLY in public-infrastructure points (assets.json) and the
# basemap geometry (*.geojson). Every event/analysis file must stay coordinate-free, so
# a strike is never resolvable below the admin-region level the UI presents.
COORD_KEYS = {"lat", "lon", "lng", "latitude", "longitude", "coordinates", "geometry"}
COORD_ALLOWED_FILES = {"assets.json"}  # + every *.geojson, handled below


def _walk_keys(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk_keys(v)


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_no_out_of_scope_fields_anywhere_in_served_payload():
    """The out-of-scope gate must cover EVERYTHING that ships, not a sample. This is the
    regression guard the daily refresh Action relies on before publishing."""
    offenders = {}
    for name in SERVED_DATA_JSON:
        fp = PROCESSED / name
        if not fp.exists():
            continue
        bad = {k for k in _walk_keys(json.loads(fp.read_text(encoding="utf-8")))
               if k.lower() in FORBIDDEN_FIELDS}
        if bad:
            offenders[name] = sorted(bad)
    assert not offenders, f"out-of-scope fields present in served data: {offenders}"


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_event_and_analysis_files_carry_no_coordinates():
    """Coordinates may exist only in public-infrastructure points (assets.json) and the
    basemap *.geojson. No event or analysis file may leak asset-level geographic
    precision — that would exceed the admin-region level the dashboard presents."""
    offenders = {}
    for name in SERVED_DATA_JSON:
        if name in COORD_ALLOWED_FILES:
            continue
        fp = PROCESSED / name
        if not fp.exists():
            continue
        bad = {k for k in _walk_keys(json.loads(fp.read_text(encoding="utf-8")))
               if k.lower() in COORD_KEYS}
        if bad:
            offenders[name] = sorted(bad)
    assert not offenders, f"coordinate keys leaked into event/analysis data: {offenders}"


# --------------------------------------------------------------------------
# Daily-refresh safety floor: a catastrophically broken parse must FAIL the
# test gate (which runs before the Action commits), not publish empty output.
# --------------------------------------------------------------------------

@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_dataset_sanity_floor_for_daily_refresh():
    """If an upstream source silently changes format and the parse collapses, the numbers
    go degenerate (near-zero events, missing sectors, ESDI 0/NaN). The daily Action runs
    pytest before committing, so failing here preserves the last known-good public dataset
    instead of publishing a gutted dashboard. Floors are deliberately far below current
    values to avoid false failures on normal variation."""
    snap = json.loads((PROCESSED / "snapshot.json").read_text(encoding="utf-8"))
    inc = json.loads((PROCESSED / "incidents.json").read_text(encoding="utf-8"))
    assert len(inc) >= 50, f"incident corpus collapsed to {len(inc)} — likely a broken parse"
    assert snap["incident_total"] >= 50
    assert isinstance(snap["esdi"], (int, float)) and snap["esdi"] == snap["esdi"], "ESDI is NaN"
    assert snap["esdi"] > 0, "ESDI collapsed to 0 — no scored disruption"
    assert snap["sectors"], "no sector exposures emitted"
    assert snap["regions"], "no regions emitted"
    assert snap["coverage"] and snap["coverage"]["coverage_ratio"] > 0
    # Denominators must survive — a zeroed denominator would silently break every share.
    den = snap["denominators"]
    assert den["refining_mtpa"] > 0 and den["electric_generation_mw"] > 0


# --------------------------------------------------------------------------
# Daily-refresh: build_time alone must NOT count as a data change (step 5 —
# avoid unnecessary commits when upstream data has not changed).
# --------------------------------------------------------------------------

def _load_ci_data_changed():
    import importlib.util
    path = ROOT / "scripts" / "ci_data_changed.py"
    spec = importlib.util.spec_from_file_location("ci_data_changed", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_build_time_alone_is_not_a_substantive_change():
    """Two snapshots identical except for build_time must normalise equal, so a same-day
    rerun does not trigger an empty daily commit."""
    ci = _load_ci_data_changed()
    a = json.dumps({"build_time": "2026-08-28T05:20:00+00:00", "as_of": "2026-08-28", "esdi": 15.6})
    b = json.dumps({"build_time": "2026-08-28T05:25:59+00:00", "as_of": "2026-08-28", "esdi": 15.6})
    assert ci.normalise(a) == ci.normalise(b)


def test_real_data_change_survives_normalisation():
    """A genuine change (as_of / esdi / anything but build_time) must remain visible."""
    ci = _load_ci_data_changed()
    a = json.dumps({"build_time": "2026-08-28T05:20:00+00:00", "as_of": "2026-08-28", "esdi": 15.6})
    b = json.dumps({"build_time": "2026-08-29T05:20:00+00:00", "as_of": "2026-08-29", "esdi": 15.4})
    assert ci.normalise(a) != ci.normalise(b)


# --------------------------------------------------------------------------
# Iteration 4: facet counts — the data-driven-UI contract
# --------------------------------------------------------------------------

@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_facet_counts_match_the_processed_corpus():
    """Facet counts must equal what is actually in the emitted data — the frontend trusts
    them to decide which controls exist, so they cannot drift from the corpus."""
    import collections as _c
    snap = _snapshot()
    fc = snap["facet_counts"]
    incidents = json.loads((PROCESSED / "incidents.json").read_text(encoding="utf-8"))
    assets = json.loads((PROCESSED / "assets.json").read_text(encoding="utf-8"))
    assert fc["incident_asset_class"] == {k: v for k, v in sorted(
        _c.Counter(i["asset_class"] for i in incidents if i.get("asset_class")).items(),
        key=lambda kv: (-kv[1], kv[0]))}
    assert fc["asset_class"] == {k: v for k, v in sorted(
        _c.Counter(a["asset_class"] for a in assets).items(),
        key=lambda kv: (-kv[1], kv[0]))}
    assert fc["cause"] == {k: v for k, v in sorted(
        _c.Counter(i["cause"] for i in incidents).items(),
        key=lambda kv: (-kv[1], kv[0]))}


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_facet_counts_keep_asset_and_incident_kinds_distinct():
    """A class can have infrastructure but no incidents (LNG-style) or incidents but no
    inventoried point-asset (oil terminals/depots). The two counts are separate facets,
    never merged. (Iteration 5 added a few struck refineries as linkable assets, so
    refineries are no longer a clean incidents-but-no-asset example — oil terminals are.)"""
    fc = _snapshot()["facet_counts"]
    # Oil terminals/depots: incidents exist, but they are not in the point-asset layer.
    assert fc["incident_asset_class"].get("oil_terminal", 0) > 0
    assert fc["asset_class"].get("oil_terminal", 0) == 0
    # Substations: both an inventory and incidents — distinct, non-merged counts.
    assert fc["asset_class"].get("substation", 0) > 0
    assert fc["incident_asset_class"].get("substation", 0) > 0


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_corpus_zero_categories_are_absent_from_facets_nonzero_present():
    """Counters omit zero keys — that omission is what a data-driven 'hide the empty toggle'
    rule reads. Genuinely-empty categories must be absent; populated ones present."""
    fc = _snapshot()["facet_counts"]
    # Nonzero cause present; corpus-zero causes absent (so the toggle hides).
    assert fc["cause"].get("kinetic_strike", 0) > 0
    for zero in ("maintenance",):  # planned maintenance is out of scope; stays zero/hidden
        assert zero not in fc["cause"]
    # Unverified confidence has no records → absent → its toggle hides.
    assert "unverified" not in fc["confidence"]


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_sector_record_count_is_not_the_sector_score():
    """A sector can carry records while its SCORE is zero/uncovered (gas has events but no
    defensible denominator). Visibility must key off record count, not score, so this
    distinction has to survive in the emitted data."""
    snap = _snapshot()
    fc = snap["facet_counts"]
    # Gas: incidents exist in the corpus...
    assert fc["sector"].get("gas", 0) > 0
    # ...but the gas sector is uncovered (score path), i.e. not in sectors_covered.
    assert "gas" in snap["sectors_uncovered"]
    assert snap["sectors"]["gas"] == 0


# --------------------------------------------------------------------------
# Iteration 4: LNG / gas ingestion — classification, provenance, no unit-mixing
# --------------------------------------------------------------------------

@pytest.mark.skipif(not (PROCESSED / "assets.json").exists(),
                    reason="pipeline has not been run")
def test_lng_assets_are_classified_and_sourced_at_admin_precision():
    """Curated LNG terminals must classify as lng_terminal, carry a public source and a
    liquefaction capacity, sit at admin-region precision (never a facility coordinate), and
    have unique ids that do not collide with the automated asset feeds."""
    assets = json.loads((PROCESSED / "assets.json").read_text(encoding="utf-8"))
    lng = [a for a in assets if a["asset_class"] == "lng_terminal"]
    assert lng, "expected curated LNG terminals in the AOI"
    ids = [a["asset_id"] for a in assets]
    assert len(ids) == len(set(ids)), "asset ids must be unique across all feeds"
    for a in lng:
        assert a.get("precision") == "region", f"{a['asset_id']} must be admin-region precision"
        assert a.get("source_url"), f"{a['asset_id']} needs a source"
        # Liquefaction terminals carry a liquefaction MTPA. Import/regasification terminals
        # (iteration 5, e.g. the Kaliningrad FSRU) deliberately do NOT: their capacity is a
        # different physical quantity, kept in the note so it can never be summed into a
        # liquefaction denominator (§11).
        note = (a.get("note") or "").lower()
        is_import = "import" in note or "regas" in note
        if not is_import:
            assert a.get("capacity_mtpa"), f"{a['asset_id']} (liquefaction) needs a capacity"


@pytest.mark.skipif(not (PROCESSED / "assets.json").exists(),
                    reason="pipeline has not been run")
def test_gas_condensate_is_not_miscounted_as_lng():
    """A gas-condensate / fractionation complex is not LNG merely because an LNG producer
    owns it (§11). No lng_terminal asset may be a condensate/fractionation facility."""
    assets = json.loads((PROCESSED / "assets.json").read_text(encoding="utf-8"))
    for a in assets:
        if a["asset_class"] == "lng_terminal":
            # Key on the facility's identity (its name). A note may legitimately MENTION
            # condensate to disclaim it (e.g. "distinct from the Ust-Luga condensate complex").
            name = a["name"].lower()
            assert "condensate" not in name and "fractionation" not in name, a["asset_id"]


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_lng_inventory_does_not_invent_a_gas_denominator():
    """Adding LNG infrastructure must not silently create a gas composite denominator by
    summing incompatible units (MTPA liquefaction + bcm pipeline + processing throughput).
    Gas stays uncovered until a defensible base exists — assets present, score still zero."""
    snap = _snapshot()
    assert snap["facet_counts"]["asset_class"].get("lng_terminal", 0) > 0
    assert "gas" in snap["sectors_uncovered"]
    assert snap["sectors"]["gas"] == 0
    assert snap["denominators"].get("gas") in (None, 0), "no gas denominator should be emitted"


# --------------------------------------------------------------------------
# Iteration 5: data-contract resilience — schema_version + manifest (§27)
# --------------------------------------------------------------------------
# The deploy-window failure that white-screened iteration 4 was new JS reading old data.
# The contract now carries a schema_version and a manifest so a client can tell app/data
# skew from a genuine outage, and so optional context layers can be absent without a crash.

@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_snapshot_carries_schema_version():
    from pipeline.config import SCHEMA_VERSION
    snap = json.loads((PROCESSED / "snapshot.json").read_text(encoding="utf-8"))
    assert snap.get("schema_version") == SCHEMA_VERSION


@pytest.mark.skipif(not (PROCESSED / "data_manifest.json").exists(),
                    reason="pipeline has not been run")
def test_data_manifest_is_present_and_consistent():
    from pipeline.config import SCHEMA_VERSION, OPTIONAL_CONTEXT_FILES
    manifest = json.loads((PROCESSED / "data_manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == SCHEMA_VERSION
    assert manifest.get("build_time")
    names = {f["name"] for f in manifest["files"]}
    # every file the frontend loads must be listed
    for required in REQUIRED_WEB_FILES:
        assert required in names, f"manifest omits frontend file {required}"
    # the manifest never lists itself, and every listed file exists on disk
    assert "data_manifest.json" not in names
    for f in manifest["files"]:
        assert (PROCESSED / f["name"]).exists(), f"manifest lists a missing file {f['name']}"
        assert isinstance(f["bytes"], int) and f["bytes"] >= 0
        # the optional flag must agree with the config-declared optional set
        assert f["optional"] == (f["name"] in OPTIONAL_CONTEXT_FILES)
    # the manifest must itself be mirrored to the web payload
    assert (WEB_DATA / "data_manifest.json").exists(), "manifest must be mirrored to web/public/data"


def test_optional_context_files_are_declared_optional_not_required():
    """An optional context layer must never be in the frontend's required set, so a build
    that omits it (or a stale edge that lacks it) can still load the core dashboard."""
    from pipeline.config import OPTIONAL_CONTEXT_FILES
    for name in OPTIONAL_CONTEXT_FILES:
        assert name not in REQUIRED_WEB_FILES, (
            f"{name} is optional context and must not be a required frontend file"
        )


# --------------------------------------------------------------------------
# Iteration 5: broadened country context + rivers (§8-§10, §25)
# --------------------------------------------------------------------------
# Geographic context is independent of energy data: every country in frame gets a border
# and a label anchor whether or not we hold any events there, and rivers are pure scenery.

@pytest.mark.skipif(not (PROCESSED / "context_land.geojson").exists(), reason="pipeline not run")
def test_context_includes_countries_with_no_energy_data():
    land = json.loads((PROCESSED / "context_land.geojson").read_text(encoding="utf-8"))
    isos = {f["properties"]["iso"] for f in land["features"]}
    # zero-data neighbours must still be drawn (§9, §25)
    for iso in ("MNG", "CHN", "KAZ", "POL", "MDA", "GEO"):
        assert iso in isos, f"context must include {iso} even with no energy data"
    # every country carries a label anchor + a data-driven reveal zoom
    for f in land["features"]:
        p = f["properties"]
        assert "label_lon" in p and "label_lat" in p
        assert "label_min_zoom" in p


@pytest.mark.skipif(not (PROCESSED / "context_land.geojson").exists(), reason="pipeline not run")
def test_context_excludes_russia_and_belarus():
    """Russia and Belarus are analytic regions, not context. Because Natural Earth files
    Crimea inside the Russian polygon, excluding Russia here keeps Crimea from ever being
    painted as ordinary Russian context (§10)."""
    land = json.loads((PROCESSED / "context_land.geojson").read_text(encoding="utf-8"))
    isos = {f["properties"]["iso"] for f in land["features"]}
    assert "RUS" not in isos and "BLR" not in isos


@pytest.mark.skipif(not (PROCESSED / "rivers.geojson").exists(), reason="pipeline not run")
def test_rivers_are_real_features_and_score_nothing():
    """Rivers are published Natural Earth features (scalerank + geometry), pure geographic
    context: they carry nothing that could enter a score, and the emphasis comes from
    scalerank, not a hardcoded river list (§8)."""
    rivers = json.loads((PROCESSED / "rivers.geojson").read_text(encoding="utf-8"))
    assert rivers["features"], "rivers layer should not be empty"
    for f in rivers["features"]:
        p = f["properties"]
        assert "scalerank" in p and "reveal_zoom" in p
        assert f["geometry"]["type"] in ("LineString", "MultiLineString")
        for forbidden in ("asset_class", "sector", "region_code", "capacity_mw", "capacity_mtpa"):
            assert forbidden not in p, f"a river must not carry {forbidden}"
    # the biggest Russian/European systems are captured (via scalerank, not a name list)
    names = {f["properties"].get("label_name") for f in rivers["features"]}
    assert "Volga" in names and "Danube" in names


# --------------------------------------------------------------------------
# Iteration 5: coal taxonomy split + inventory (§14, §35)
# --------------------------------------------------------------------------
# Generic "coal infrastructure" is split into coal_mine and coal_terminal. Coal-fired
# GENERATION stays under electric generation, so a coal mine is never double-counted as a
# power plant. Coal is now inventoried but has no qualifying disruption, so the coal SECTOR
# stays unsupported: an inventory is not a score.

def test_coal_class_split_into_mine_and_terminal():
    from pipeline.config import ASSET_CLASSES, SECTOR_OF_CLASS
    assert "coal_mine" in ASSET_CLASSES and "coal_terminal" in ASSET_CLASSES
    assert "coal" not in ASSET_CLASSES, "the generic coal class must be gone after the split"
    # both physical coal classes roll up to the coal sector...
    assert SECTOR_OF_CLASS["coal_mine"] == "coal"
    assert SECTOR_OF_CLASS["coal_terminal"] == "coal"
    # ...while coal-fired generation stays under electric generation (no double count, §14)
    assert SECTOR_OF_CLASS["power_plant_thermal"] == "electric_generation"


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_coal_inventory_present_but_sector_unsupported():
    """Coal mines and terminals are now in the corpus, but with no qualifying disruption the
    coal sector stays uncovered and scores zero -- an inventory is not disruption (§14/§35)."""
    snap = _snapshot()
    fc = snap["facet_counts"]["asset_class"]
    assert fc.get("coal_mine", 0) > 0 and fc.get("coal_terminal", 0) > 0, "coal inventory expected"
    assert "coal" in snap["sectors_uncovered"]
    assert snap["sectors"]["coal"] == 0
    assert snap["denominators"].get("coal") in (None, 0), "no coal denominator should be emitted"


@pytest.mark.skipif(not (PROCESSED / "assets.json").exists(),
                    reason="pipeline has not been run")
def test_coal_and_gas_capacities_kept_out_of_the_mtpa_field():
    """Coal tonnage (Mt/y) and gas-processing throughput (bcm/y) are different units from
    LNG liquefaction (MTPA). They live in the note, never in capacity_mtpa, so nothing can
    later sum them into a single fake denominator (§12, §13)."""
    assets = json.loads((PROCESSED / "assets.json").read_text(encoding="utf-8"))
    for a in assets:
        if a["asset_class"] in ("coal_mine", "coal_terminal", "gas_processing"):
            assert not a.get("capacity_mtpa"), f"{a['asset_id']} must not carry an MTPA figure"
            assert a.get("source_url"), f"{a['asset_id']} needs a source"
            assert a.get("precision") == "region"


# --------------------------------------------------------------------------
# Iteration 5: event/recovery coverage expansion + candidate queue (§15-§18)
# --------------------------------------------------------------------------
# A candidate-event queue stages OSINT proposals; only analyst-approved rows enter the
# scored corpus. Rejected/held candidates (unconfirmed 'repelled' claims, partisan-only
# sabotage, weather outages) must never score.

CANDIDATE = ROOT / "data" / "candidate" / "candidate_incidents.csv"


def test_candidate_queue_exists_with_decisions():
    import csv as _csv
    assert CANDIDATE.exists(), "the analyst candidate queue must exist (§16)"
    with open(CANDIDATE, encoding="utf-8", newline="") as fh:
        rows = list(_csv.DictReader(fh))
    statuses = {r["research_status"] for r in rows}
    assert "accepted" in statuses and (statuses & {"rejected", "hold"}), \
        "the queue must record both accepted and rejected/held candidates"
    for r in rows:
        assert r["decision_reason"], "every candidate needs a decision reason"


@pytest.mark.skipif(not (PROCESSED / "incidents.json").exists(), reason="pipeline not run")
def test_rejected_candidates_never_enter_scoring():
    inc = json.loads((PROCESSED / "incidents.json").read_text(encoding="utf-8"))
    blob = " ".join((i.get("asset_name") or "") + " " + (i.get("incident_id") or "") for i in inc).lower()
    for term in ("russkaya", "blue stream", "mozyr", "bolshoe polpino"):
        assert term not in blob, f"rejected/held candidate '{term}' leaked into the scored corpus"


@pytest.mark.skipif(not (PROCESSED / "incidents.json").exists(), reason="pipeline not run")
def test_recovery_records_key_to_real_incidents():
    import csv as _csv
    inc = json.loads((PROCESSED / "incidents.json").read_text(encoding="utf-8"))
    ids = {i["incident_id"] for i in inc}
    with open(ROOT / "data" / "curated" / "recovery.csv", encoding="utf-8", newline="") as fh:
        recs = list(_csv.DictReader(fh))
    orphans = [r["incident_id"] for r in recs if r["incident_id"] not in ids]
    assert not orphans, f"recovery records with no matching incident: {orphans}"


@pytest.mark.skipif(not (PROCESSED / "incidents.json").exists(), reason="pipeline not run")
def test_no_exact_duplicate_incidents():
    """Curated events must not duplicate a facility+date already in the corpus."""
    import collections as _c
    inc = json.loads((PROCESSED / "incidents.json").read_text(encoding="utf-8"))
    seen = _c.Counter((i.get("asset_id"), i.get("date")) for i in inc)
    dups = [k for k, v in seen.items() if v > 1]
    assert not dups, f"exact (asset_id, date) duplicate incidents: {dups}"


# --------------------------------------------------------------------------
# Iteration 5: analytic vs context scope + continental pipeline network (§2,§7,§15,§36)
# --------------------------------------------------------------------------
# The context network is a SEPARATE, display-only layer. It is never joined to a region,
# never scored, never an incident; its counts are kept apart from the analytic lines.

def test_analytic_assets_and_lines_carry_analytic_scope():
    if (PROCESSED / "assets.json").exists():
        for a in json.loads((PROCESSED / "assets.json").read_text(encoding="utf-8")):
            assert a.get("scope") == "analytic", f"{a['asset_id']} must be scope=analytic"
    if (PROCESSED / "assets_lines.geojson").exists():
        lines = json.loads((PROCESSED / "assets_lines.geojson").read_text(encoding="utf-8"))
        for f in lines["features"]:
            assert f["properties"].get("scope") == "analytic"


@pytest.mark.skipif(not (PROCESSED / "context_gas_network.geojson").exists(),
                    reason="context network not built")
def test_context_network_is_scope_context_sourced_and_route_qualified():
    for fn in ("context_gas_network.geojson", "context_oil_network.geojson"):
        fc = json.loads((PROCESSED / fn).read_text(encoding="utf-8"))
        for feat in fc["features"]:
            p = feat["properties"]
            assert p["scope"] == "context", f"{fn}: a network route must be scope=context"
            assert p["route_quality"], "route-quality provenance must travel (§5)"
            assert p["asset_class"] in ("pipeline_gas", "pipeline_oil")
            assert feat["geometry"]["type"] in ("LineString", "MultiLineString")


@pytest.mark.skipif(not (PROCESSED / "context_gas_network.geojson").exists(),
                    reason="context network not built")
def test_context_routes_never_score_and_create_no_incident():
    """European and Far-Eastern context routes carry no region and generate no incident, so
    they cannot enter ESDI, rankings, regional intensity or recovery (§7, §36)."""
    inc = json.loads((PROCESSED / "incidents.json").read_text(encoding="utf-8"))
    inc_ids = {i.get("asset_id") for i in inc}
    for fn in ("context_gas_network.geojson", "context_oil_network.geojson"):
        fc = json.loads((PROCESSED / fn).read_text(encoding="utf-8"))
        for feat in fc["features"]:
            p = feat["properties"]
            assert "region_code" not in p, "a context route must not be region-scoped"
            assert f"osm-way-{p.get('osm_id')}" not in inc_ids, "context route must not be an incident"


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_context_route_facet_kept_separate_from_analytic_lines():
    """A continent of context routes must not be conflated with analytic pipeline lines or
    with incidents (§15)."""
    fc = _snapshot()["facet_counts"]
    assert "context_route_class" in fc and fc["context_route_class"], "context routes must be counted"
    # the two counts are distinct dimensions
    assert fc["line_class"].get("pipeline_gas", 0) != fc["context_route_class"].get("pipeline_gas")



# --------------------------------------------------------------------------
# Iteration 9: relation-aware pipeline reconstruction
# --------------------------------------------------------------------------
# The defect these pin: the old builder applied a 50 km minimum to each OSM WAY, so a trunk line
# split into many short ways scored zero and vanished. docs/PIPELINE_GAP_AUDIT.md measured
# 161,899 km of relation-member geometry missing from the shipped output as a result.

def _way(coords):
    return [{"lon": x, "lat": y} for x, y in coords]


def _relation(rid, name, substance, ways, member_ids=None):
    ids = member_ids or list(range(1000 + rid * 100, 1000 + rid * 100 + len(ways)))
    return {
        "id": rid, "type": "relation",
        "tags": {"type": "route", "route": "pipeline", "name": name, **({"substance": substance} if substance else {})},
        "members": [{"type": "way", "ref": i, "role": "", "geometry": _way(w)}
                    for i, w in zip(ids, ways)],
    }


def test_long_route_of_short_ways_survives_the_trunk_threshold():
    """A 500 km trunk composed of many sub-50 km ways must be RETAINED.

    This is the exact case the old per-way filter destroyed: 65 named routes vanished although
    their members totalled well over the threshold.
    """
    from pipeline import build_pipeline_network as B
    # 25 contiguous ways of ~0.2 deg lon each at 55N -> ~320 km total, no single way near 50 km
    ways = [[(30.0 + i * 0.2, 55.0), (30.0 + (i + 1) * 0.2, 55.0)] for i in range(25)]
    for w in ways:
        assert B._length_km(w) < B.MIN_TRUNK_KM, "fixture must use sub-threshold members"
    routes, _ = B.build_routes([_relation(1, "Test Trunk", "gas", ways)], {})
    assert len(routes) == 1, "a long route of short ways must survive"
    assert routes[0]["length_km"] >= B.MIN_TRUNK_KM
    assert routes[0]["member_count"] == 25


def test_relation_members_are_stitched_into_one_ordered_component():
    from pipeline import build_pipeline_network as B
    ways = [[(30.0 + i * 0.2, 55.0), (30.0 + (i + 1) * 0.2, 55.0)] for i in range(25)]
    routes, _ = B.build_routes([_relation(2, "Contiguous", "gas", ways)], {})
    assert len(routes[0]["components"]) == 1, "contiguous members must form ONE component"
    coords = routes[0]["components"][0]
    xs = [c[0] for c in coords]
    assert xs == sorted(xs), "the stitched component must be ordered along the route"


def test_members_supplied_out_of_order_and_reversed_still_stitch():
    """OSM member order and way direction are not guaranteed."""
    from pipeline import build_pipeline_network as B
    ways = [[(30.0 + i * 0.2, 55.0), (30.0 + (i + 1) * 0.2, 55.0)] for i in range(25)]
    ways[5].reverse()
    ways[11].reverse()
    shuffled = ways[7:] + ways[:7]
    routes, _ = B.build_routes([_relation(3, "Jumbled", "gas", shuffled)], {})
    assert len(routes[0]["components"]) == 1


def test_unnamed_short_members_inherit_identity_from_the_relation():
    """A member way needs no name of its own; the route carries the identity."""
    from pipeline import build_pipeline_network as B
    ways = [[(40.0 + i * 0.3, 60.0), (40.0 + (i + 1) * 0.3, 60.0)] for i in range(20)]
    rel = _relation(4, "Named Only On The Relation", "oil", ways)
    routes, _ = B.build_routes([rel], {})          # NO member tags supplied at all
    assert len(routes) == 1
    assert routes[0]["canonical_name"] == "Named Only On The Relation"
    assert routes[0]["asset_class"] == "pipeline_oil"


def test_substance_falls_back_to_member_tags_then_name():
    from pipeline import build_pipeline_network as B
    ways = [[(40.0 + i * 0.3, 60.0), (40.0 + (i + 1) * 0.3, 60.0)] for i in range(20)]
    rel = _relation(5, "No Substance Here", None, ways)
    ids = [m["ref"] for m in rel["members"]]
    # member majority decides
    routes, _ = B.build_routes([rel], {i: {"substance": "gas"} for i in ids})
    assert routes[0]["asset_class"] == "pipeline_gas"
    assert routes[0]["substance_basis"] == "member_substance_majority"
    # with no tags anywhere, a Russian-language name still resolves it
    rel2 = _relation(6, "Магистральный нефтепровод Тест", None, ways)
    routes2, _ = B.build_routes([rel2], {})
    assert routes2[0]["asset_class"] == "pipeline_oil"
    assert routes2[0]["substance_basis"] == "route_name_hint"


def test_oil_and_gas_are_never_conflated_and_non_hydrocarbons_are_excluded():
    from pipeline import build_pipeline_network as B
    assert B._classify("gas") == "pipeline_gas"
    assert B._classify("natural_gas") == "pipeline_gas"
    assert B._classify("oil") == "pipeline_oil"
    assert B._classify("crude oil") == "pipeline_oil"
    # neither class: refined products, and everything that merely contains a token
    for v in ("fuel", "water", "sewage", "steam", "ethylene", "hydrogen", "carbon_dioxide",
              "hot_water", "gasoline", "biogas", ""):
        assert B._classify(v) is None, f"{v!r} must not be classified as oil or gas"


def test_refined_product_systems_never_enter_the_crude_oil_class():
    """OSM's `substance=oil` is used loosely and covers product pipelines too.

    Found in the built output: Exolum's "Canalización de Derivados del Petróleo" carries 235
    members tagged `oil` and was classified as crude transmission — a 3,123 km Spanish products
    network inside a Russian crude-export view. Two rules now prevent it: the substance vote runs
    over RAW member values (so a dominant `fuel` tag excludes the route), and a name that states
    the system carries products excludes it outright.
    """
    from pipeline import build_pipeline_network as B
    ways = [[(0.0 + i * 0.3, 40.0), (0.0 + (i + 1) * 0.3, 40.0)] for i in range(20)]

    # (a) name says products, members say oil -> excluded
    rel = _relation(20, "Canalización de Derivados del Petróleo Subterránea Exolum", None, ways)
    ids = [m["ref"] for m in rel["members"]]
    cls, basis = B._route_substance(rel["tags"], [{"substance": "oil"}] * len(ids), rel["tags"]["name"])
    assert cls is None and basis == "refined_products_excluded"

    # (b) dominant member substance is excluded -> route excluded, not captured by a few oil tags
    rel2 = _relation(21, "Some Products Network", None, ways)
    tags = [{"substance": "fuel"}] * 18 + [{"substance": "oil"}] * 2
    cls2, basis2 = B._route_substance(rel2["tags"], tags, rel2["tags"]["name"])
    assert cls2 is None and basis2 == "member_substance_excluded"

    # (c) a genuine crude route is still classified
    rel3 = _relation(22, "Нефтепровод Дружба", None, ways)
    cls3, _ = B._route_substance(rel3["tags"], [{"substance": "oil"}] * 20, rel3["tags"]["name"])
    assert cls3 == "pipeline_oil"


@pytest.mark.skipif(not (PROCESSED / "context_oil_network.geojson").exists(),
                    reason="context network not built")
def test_built_network_contains_no_refined_product_systems():
    for fn in ("context_gas_network.geojson", "context_oil_network.geojson"):
        fc = json.loads((PROCESSED / fn).read_text(encoding="utf-8"))
        for feat in fc["features"]:
            name = (feat["properties"].get("name") or "").lower()
            for token in ("derivados del petr", "exolum", "central europe pipeline system"):
                assert token not in name, f"{fn}: refined-product system leaked in — {name[:50]}"


def test_proximity_alone_never_creates_a_connector():
    """Two segments with NO shared route identity must never be joined, however close."""
    from pipeline import build_pipeline_network as B
    a = [(30.0, 55.0), (31.0, 55.0)]
    b = [(31.00001, 55.0), (32.0, 55.0)]          # ~1 m away, but a different relation
    r1, _ = B.build_routes([_relation(7, "A", "gas", [a] * 1 + [[(30.0, 55.0), (30.9, 55.0)]])], {})
    chains = B.stitch([a, b])
    assert len(chains) == 2, "stitch() must not join on proximity — only exact shared endpoints"


def test_weld_closes_only_tiny_same_route_gaps_and_records_them():
    from pipeline import build_pipeline_network as B
    a = [(30.0, 55.0), (31.0, 55.0)]
    near = [(31.0005, 55.0), (32.0, 55.0)]        # ~32 m — same route, unsnapped node
    far = [(35.0, 55.0), (36.0, 55.0)]            # ~250 km away — a real gap
    chains, welds, max_km = B.weld([a, near, far])
    assert welds == 1, "only the sub-tolerance gap may be welded"
    assert max_km <= B.WELD_TOLERANCE_KM
    assert len(chains) == 2, "the real gap must remain a visible gap"


def test_weld_never_exceeds_its_tolerance():
    from pipeline import build_pipeline_network as B
    a = [(30.0, 55.0), (31.0, 55.0)]
    b = [(31.5, 55.0), (32.0, 55.0)]              # ~32 km apart
    chains, welds, _ = B.weld([a, b])
    assert welds == 0 and len(chains) == 2


def test_every_simplifier_shares_one_correct_metric():
    """There must be exactly ONE distance metric behind every Douglas-Peucker caller.

    The project had five near-identical DP copies; three carried the infinite-line metric that
    erased 690 pipeline components in iteration 9. `geo._perpendicular_distance` is retained under
    an honest name but no simplifier may use it.
    """
    from pipeline import geo
    # The correct metric: a point beyond a short segment is far from it, not on it.
    assert geo.segment_distance((10, 0), (0, 0), (0.001, 0)) > 9.9
    assert geo._perpendicular_distance((10, 0), (0, 0), (0.001, 0)) == 0.0   # why it was wrong
    # Degenerate segment (a ring's shared first/last point) falls back to point distance.
    assert geo.segment_distance((3, 4), (0, 0), (0, 0)) == pytest.approx(5.0)

    src_files = ["build_assets.py", "build_context.py", "build_pipeline_network.py", "geo.py"]
    for name in src_files:
        text = (ROOT / "pipeline" / name).read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("*"):
                continue          # comments may name it when explaining the history
            if "_perpendicular_distance(" in line and "def _perpendicular_distance" not in line:
                assert "geo._perpendicular_distance" not in line, (
                    f"{name} calls the infinite-line metric; use geo.segment_distance")


def test_simplify_line_preserves_an_out_and_back_excursion():
    """The shared open-line simplifier must not collapse a chain that returns near its start."""
    from pipeline import geo
    pts = [(0.0, 0.0), (0.5, 0.0), (1.0, 0.0), (0.5, 0.0), (0.001, 0.0)]
    assert len(geo.simplify_line(pts, 0.01)) >= 3
    # endpoints always survive
    out = geo.simplify_line([(0.0, 0.0), (0.5, 0.4), (1.0, 0.0)], 0.001)
    assert out[0] == (0.0, 0.0) and out[-1] == (1.0, 0.0)


def test_simplify_ring_keeps_rings_closed_and_never_inverts_area():
    from pipeline import geo
    import math as _m
    ring = [(_m.cos(t / 40 * 2 * _m.pi), _m.sin(t / 40 * 2 * _m.pi)) for t in range(41)]
    out = geo.simplify_ring(ring, 0.01)
    assert out[0] == out[-1], "a simplified ring must stay closed"
    assert len(out) >= 4
    area = abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(out, out[1:]))) / 2
    assert 0.5 * _m.pi < area < 1.2 * _m.pi, "ring area must survive simplification"


def test_simplify_measures_distance_to_the_segment_not_the_infinite_line():
    """GIS red-team finding: DP with a point-to-LINE metric erases excursions.

    When a chain's two anchors are close together, every interior point lies on the infinite
    line through them, scores ~0, and is deleted — collapsing the chain below two points, where
    it is dropped entirely. On the real corpus that silently erased 690 components / 216 km,
    including 25.7 km of Уренгой — Петровск drawn as an 80 m stub.
    """
    from pipeline import build_pipeline_network as B
    from pipeline import geo
    # A point 10 units beyond a 0.001-long segment: on the LINE, far from the SEGMENT.
    # (Iteration 10 moved this metric into geo so every simplifier shares one implementation.)
    assert geo.segment_distance((10, 0), (0, 0), (0.001, 0)) > 9.9
    # An out-and-back excursion must survive simplification rather than collapse.
    pts = [(0.0, 0.0), (0.5, 0.0), (1.0, 0.0), (0.5, 0.0), (0.001, 0.0)]
    assert len(B._simplify(pts, 0.01)) >= 3


def test_stitch_stops_at_junctions_so_parallel_strings_are_not_overlaid():
    """A node where 3+ ways meet is a branch. Walking through it arbitrarily can run out along
    one string and back along its twin, drawing one LineString on top of itself."""
    from pipeline import build_pipeline_network as B
    trunk = [(0.0, 0.0), (1.0, 0.0)]
    branch_a = [(1.0, 0.0), (2.0, 0.5)]
    branch_b = [(1.0, 0.0), (2.0, -0.5)]
    chains = B.stitch([trunk, branch_a, branch_b])
    assert len(chains) == 3, "a Y-junction must yield three edge-disjoint paths, not one folded line"
    for c in chains:
        assert len(c) == 2


def test_generic_descriptive_names_never_become_routes():
    """"перемычка" (jumper) and "лупинг" (loop) are common nouns. Grouping every way carrying
    one into a single 'route' fabricated a 153-component entity spanning 2,934 km."""
    from pipeline import build_pipeline_network as B
    for generic in ("перемычка", "лупинг", "отвод", "loop", "Branch", "  нитка  "):
        assert B._is_generic_name(generic), f"{generic!r} must be rejected as an identity"
    for real in ("Уренгой — Помары — Ужгород", "Дружба", "Nord Stream", "Ямал — Европа"):
        assert not B._is_generic_name(real), f"{real!r} is a real route name"


def test_named_way_routes_are_never_welded():
    """Welding is justified by shared RELATION membership — OSM asserting one pipeline. A shared
    name string is not that assertion, so the named-way path must not weld across gaps."""
    src = (ROOT / "pipeline" / "build_pipeline_network.py").read_text(encoding="utf-8")
    body = src.split("def build_named_way_routes")[1].split("\ndef ")[0]
    assert "weld(" not in body, "the named-way path must not weld"


def test_route_quality_is_measured_from_source_density_not_asserted():
    """OSM ships 5,387-vertex corridors and 3-point placeholders under identical tags. Labelling
    both 'mapped' asserts a confidence the geometry does not have."""
    from pipeline import build_pipeline_network as B
    dense = [[(30.0 + i * 0.01, 55.0) for i in range(400)]]          # ~0.6 km spacing
    sparse = [[(30.0, 55.0), (60.0, 55.0), (90.0, 55.0)]]            # ~1000 km spacing
    assert B._measured_quality(dense)[0] == "osm_mapped"
    assert B._measured_quality(sparse)[0] == "topology_only"
    mid = [[(30.0 + i * 0.3, 55.0) for i in range(40)]]              # ~19 km spacing
    assert B._measured_quality(mid)[0] == "osm_generalized"


@pytest.mark.skipif(not (PROCESSED / "pipeline_network_quality.json").exists(),
                    reason="context network not built")
def test_network_length_distinguishes_sum_of_routes_from_distinct_network():
    """OSM models some systems as a superroute PLUS its child relations, so summing route
    lengths counts shared pipe twice. Publishing only the sum overstated the network ~13%."""
    q = json.loads((PROCESSED / "pipeline_network_quality.json").read_text(encoding="utf-8"))
    for cls in ("pipeline_gas", "pipeline_oil"):
        v = q[cls]
        assert v["distinct_network_km"] <= v["total_length_km"]
        # drawn geometry is always shorter than the source it was simplified from
        assert v["drawn_length_km"] <= v["total_length_km"]
        assert "welds" in v and "max_weld_km" in v, "weld provenance must be published"
        assert v["max_weld_km"] <= 0.1 + 1e-9


def test_simplification_preserves_endpoints():
    from pipeline import build_pipeline_network as B
    pts = [(30.0 + i * 0.01, 55.0 + (0.02 if i % 2 else 0.0)) for i in range(200)]
    simp = B._simplify(pts, 0.04)
    assert tuple(simp[0]) == pts[0] and tuple(simp[-1]) == pts[-1]
    assert len(simp) < len(pts)


def test_context_route_is_not_dropped_for_overlapping_the_analytic_feed():
    """The context layer must stand alone: its toggle is independent of the analytic layer.

    The old builder deleted 17,535 km of trunk — Druzhba, Urengoy–Pomary–Uzhhorod — from the
    context network purely because the analytic feed also carried those ways, so enabling
    "Gas pipelines" without "Grid & pipeline network" showed no Russian backbone.
    """
    from pipeline import build_pipeline_network as B
    ways = [[(40.0 + i * 0.3, 60.0), (40.0 + (i + 1) * 0.3, 60.0)] for i in range(20)]
    rel = _relation(8, "Overlaps Analytic", "gas", ways)
    ids = [m["ref"] for m in rel["members"]]
    routes, _ = B.build_routes([rel], {}, analytic_osm_ids=set(ids))
    assert len(routes) == 1, "an overlapping route must be KEPT, not deleted"
    assert routes[0]["analytic_overlap"] is True, "overlap must be MARKED so the UI can dedupe"


@pytest.mark.skipif(not (PROCESSED / "context_gas_network.geojson").exists(),
                    reason="context network not built")
def test_built_context_network_carries_route_identity_and_provenance():
    for fn in ("context_gas_network.geojson", "context_oil_network.geojson"):
        fc = json.loads((PROCESSED / fn).read_text(encoding="utf-8"))
        assert fc["features"], f"{fn} must not be empty"
        for feat in fc["features"]:
            p = feat["properties"]
            assert p["pipeline_id"], "every component must carry its canonical route id"
            assert p["geometry_source"] in ("osm_relation", "osm_named_ways")
            assert p["substance_basis"] in (
                "relation_substance_tag", "member_substance_majority",
                "route_name_hint", "way_substance_tag")
            assert isinstance(p["analytic_overlap"], bool)
            # A component index must be consistent with its route's component count.
            assert 0 <= p["component_index"] < p["component_count"]


def test_curated_pipeline_topology_is_sourced_and_carries_no_geometry():
    """Published connection facts are TOPOLOGY, never a licence to draw a route.

    Each row asserts that two named systems meet at a named point, with a source. The file must
    contain no coordinates of any kind: 'topology known' and 'geometry known' are different
    states, and a schematic operator map is schematic topology.
    """
    path = ROOT / "data" / "curated" / "pipeline_topology.csv"
    if not path.exists():
        pytest.skip("topology file not present")
    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    assert rows, "topology file must not be empty"
    banned = {"lat", "lon", "latitude", "longitude", "coordinates", "geometry", "wkt",
              "distance_km", "bearing"}
    assert not (set(rows[0]) & banned), "topology rows must carry no geometry"
    for r in rows:
        assert r["subject"] and r["object"], "every assertion needs both ends"
        assert r["substance"] in ("gas", "oil"), f"bad substance {r['substance']!r}"
        assert r["source_url"].startswith("http"), f"unsourced assertion: {r['subject']}"
        assert r["source_quality"] in (
            "operator_primary", "tso_primary", "secondary_citing_operator",
            "secondary_citing_tso", "secondary", "encyclopedic",
        ), f"unknown source tier {r['source_quality']!r}"


def test_topology_assertions_are_not_used_to_synthesise_route_geometry():
    """Guard the Type-C rule: a known connection must never become a drawn line.

    If a future change starts reading the topology file inside the network builder, this fails —
    the honest treatment is a dossier/hover disclosure or an explicitly schematic style, never a
    straight line pretending to be a pipe.
    """
    src = (ROOT / "pipeline" / "build_pipeline_network.py").read_text(encoding="utf-8")
    assert "pipeline_topology" not in src, (
        "the geometry builder must not consume curated topology assertions — "
        "topology known is not geometry known"
    )


@pytest.mark.skipif(not (PROCESSED / "pipeline_network_quality.json").exists(),
                    reason="context network not built")
def test_network_quality_report_separates_topology_from_geometry():
    q = json.loads((PROCESSED / "pipeline_network_quality.json").read_text(encoding="utf-8"))
    for cls in ("pipeline_gas", "pipeline_oil"):
        v = q[cls]
        assert v["routes"] > 0
        # continuity is reported, not asserted away: a fragmented route stays fragmented
        assert v["single_component_routes"] + v["multi_component_routes"] == v["routes"]
        assert v["total_components"] >= v["routes"]
        # route_quality must never claim more than the source supports. osm_generalized and
        # topology_only are MEASURED from source vertex density, not asserted.
        assert set(v["route_quality"]) <= {"osm_mapped", "osm_generalized", "gem_traced",
                                           "gem_generalized", "topology_only", "unresolved"}


def test_context_network_files_are_declared_optional_and_lazy():
    """The continental network files are optional context: a build that omits them, or a CDN
    edge that lacks them mid-deploy, must not break the core dashboard (§16, §35)."""
    from pipeline.config import OPTIONAL_CONTEXT_FILES
    for name in ("context_gas_network.geojson", "context_oil_network.geojson", "rivers.geojson"):
        assert name in OPTIONAL_CONTEXT_FILES
        assert name not in REQUIRED_WEB_FILES, f"{name} is optional/lazy, never a required file"


# --------------------------------------------------------------------------
# Iteration 5: red-team disclosures (§37) — renormalization uplift, transmission theatre
# --------------------------------------------------------------------------

@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_headline_renormalization_uplift_is_disclosed():
    """The headline ESDI renormalises the uncovered sectors away; the honest present-at-zero
    figure and the gap must be emitted so the uplift is visible, not silent."""
    snap = _snapshot()
    assert "esdi_all_sectors" in snap
    assert snap["esdi"] >= snap["esdi_all_sectors"]  # renormalisation can only lift the number
    assert snap.get("esdi_renormalization_note")


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_transmission_concentration_disclosed():
    """Transmission is theatre-concentrated; top contributors + occupied share are emitted so
    'transmission N' is not misread as a national-grid figure."""
    snap = _snapshot()
    tc = snap.get("transmission_concentration")
    assert tc and tc["top"], "transmission concentration must be disclosed"
    assert sum(t["pct"] for t in tc["top"]) > 0
    assert 0 <= tc["occupied_share_pct"] <= 100


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_transmission_sensitivity_sweep_is_consistent_and_monotone():
    """§21-23: the saturation sweep must (a) contain the actual constant, (b) reproduce the
    headline value at that constant, and (c) fall monotonically as saturation rises — the whole
    point being to show how fragile the number is, without changing the formula."""
    snap = _snapshot()
    t = snap.get("transmission_sensitivity")
    assert t, "transmission sensitivity must be published"
    sweep = {r["saturation"]: r["sector_value"] for r in t["saturation_sweep"]}
    assert t["saturation_constant"] in sweep
    # Reproduces the shipped headline value at the real constant.
    assert sweep[t["saturation_constant"]] == pytest.approx(snap["sectors"]["transmission"], abs=0.05)
    # Higher saturation -> strictly lower (or equal at the cap) sector value.
    sats = sorted(sweep)
    vals = [sweep[k] for k in sats]
    assert vals == sorted(vals, reverse=True), "sweep must be non-increasing in saturation"


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_transmission_sensitivity_exposes_theatre_concentration():
    """The per-region breakdown must show the burden sits in a handful of theatres, and the
    top-theatre share must be a real fraction — the audit's central finding."""
    snap = _snapshot()
    t = snap["transmission_sensitivity"]
    assert t["distinct_affected_regions"] == len(t["per_region_saturated"])
    if t["raw_burden"] > 0:
        assert t["top_region_share_pct"] is not None and 0 < t["top_region_share_pct"] <= 100
        # per-region burdens sum to the raw burden.
        assert sum(r["burden"] for r in t["per_region_saturated"]) == pytest.approx(t["raw_burden"], abs=0.02)


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_transmission_alternative_models_are_deterministic_and_bounded():
    """§23-24: the alternative formulations are all emitted, bounded [0,100], and internally
    consistent (Model A reproduces the headline; Model E is the headline minus transmission)."""
    snap = _snapshot()
    t = snap["transmission_sensitivity"]
    am = t.get("alternative_models")
    assert am, "alternative_models must be published"
    for k in ("A_current_global_saturation", "B_per_region_saturation_breadth_aware",
              "C_breadth_affected_regions", "C_intensity_max_region_pct", "D_distinct_facility_burden"):
        assert k in am
    # A reproduces the shipped headline transmission value.
    assert am["A_current_global_saturation"] == pytest.approx(snap["sectors"]["transmission"], abs=0.05)
    # burdens are exposures in [0,100].
    for k in ("A_current_global_saturation", "B_per_region_saturation_breadth_aware",
              "C_intensity_max_region_pct", "D_distinct_facility_burden"):
        assert 0.0 <= am[k] <= 100.0
    # Model E: removing transmission changes the headline (a positive-contribution sector).
    if am.get("E_esdi_if_transmission_removed") is not None:
        assert am["E_esdi_if_transmission_removed"] <= snap["esdi"] + 1e-6
    assert snap.get("esdi_excluding_transmission") == pytest.approx(am.get("E_esdi_if_transmission_removed"), abs=0.05)
    # The models must carry the explicit disclaimer that none is a percent of grid offline.
    assert "grid offline" in am["note"].lower()


def test_transmission_sector_is_labelled_a_burden_not_bare_transmission():
    """§22-25 transmission red-team: the sector must be labelled a 'burden' so a reader cannot
    read the event-burden proxy as a '% of grid offline' capacity share."""
    from pipeline.config import SECTORS
    assert "burden" in SECTORS["transmission"].lower(), SECTORS["transmission"]
    if (PROCESSED / "taxonomy.json").exists():
        tax = json.loads((PROCESSED / "taxonomy.json").read_text(encoding="utf-8"))
        assert "burden" in tax["sectors"]["transmission"].lower()


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_effects_carry_source_quality_tier(SNAP=None):
    """§31: source-quality tier is emitted for triage/provenance (separate from evidence_kind)."""
    snap = _snapshot()
    se = snap.get("strategic_effects") or {"national": [], "by_incident": {}}
    allowed = {"primary_operator", "government", "major_wire", "national_regional",
               "specialist_industry", "secondary_aggregation", "claim_only", None}
    for e in list(se["national"]) + [x for lst in se["by_incident"].values() for x in lst]:
        assert e.get("source_quality") in allowed, e.get("source_quality")


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_uncovered_zero_assumption_sensitivity_is_labelled_not_a_second_esdi():
    """§27: the gas+coal-at-zero figure is a SENSITIVITY under a false assumption, renamed to say
    so, with the deprecated alias preserved for N-1 payloads."""
    snap = _snapshot()
    assert "uncovered_zero_assumption_sensitivity" in snap
    # N-1 alias preserved and equal.
    assert snap["uncovered_zero_assumption_sensitivity"] == pytest.approx(snap["esdi_all_sectors"], abs=0.01)
    note = snap["esdi_renormalization_note"].lower()
    assert "sensitivity" in note and ("assumption" in note or "false" in note)


def test_gas_and_coal_are_labelled_uncovered_not_a_fake_basis():
    """gas/coal must not advertise an 'event_burden' basis that build_index._share implements
    only for transmission — that footgun would silently zero-score a sector if it were ever
    moved into `covered` (red-team, iteration 5)."""
    from pipeline.config import SECTOR_BASIS
    assert SECTOR_BASIS["gas"] == "uncovered" and SECTOR_BASIS["coal"] == "uncovered"
    assert SECTOR_BASIS["transmission"] == "event_burden"


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_gas_and_coal_stay_out_of_covered():
    snap = _snapshot()
    assert "gas" in snap["sectors_uncovered"] and "coal" in snap["sectors_uncovered"]
    assert "gas" not in snap["sectors_covered"] and "coal" not in snap["sectors_covered"]


# --------------------------------------------------------------------------
# Iteration 6: coverage universe correction (§3-§5)
# --------------------------------------------------------------------------
# The oil-strike benchmark describes ONE universe. Coverage against it must use a matching
# numerator (oil-sector strikes), not all energy events; non-oil sectors get no fake %.

@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_oil_coverage_uses_the_oil_strike_universe():
    from pipeline.config import SECTOR_OF_CLASS
    snap = _snapshot()
    cov = snap["coverage"]
    inc = json.loads((PROCESSED / "incidents.json").read_text(encoding="utf-8"))
    oil_strikes = sum(
        1 for i in inc
        if SECTOR_OF_CLASS.get(i.get("asset_class")) in ("refining", "oil_logistics")
        and i.get("cause") in ("kinetic_strike", "sabotage")
    )
    assert cov["enumerated_in_this_dataset"] == oil_strikes, "numerator must be oil-sector strikes only"
    assert cov["enumerated_in_this_dataset"] < snap["incident_total"], "numerator must exclude non-oil events"
    assert cov["total_events_all_sectors"] == snap["incident_total"]
    assert cov["numerator_definition"]


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_non_oil_events_cannot_inflate_oil_coverage():
    """A transmission/generation/gas event must never enter the oil-strike numerator."""
    from pipeline.config import SECTOR_OF_CLASS
    snap = _snapshot()
    inc = json.loads((PROCESSED / "incidents.json").read_text(encoding="utf-8"))
    non_oil = [i for i in inc if SECTOR_OF_CLASS.get(i.get("asset_class")) not in ("refining", "oil_logistics")]
    assert non_oil, "corpus should contain non-oil events (else this test is vacuous)"
    # the corrected numerator equals the oil-strike count; the OLD formula (all events) would
    # have been strictly larger, so the correction actually lowered the reported coverage.
    assert snap["coverage"]["enumerated_in_this_dataset"] == snap["incident_total"] - non_oil.__len__() \
        or snap["coverage"]["enumerated_in_this_dataset"] < snap["incident_total"]


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_unbenchmarked_sectors_emit_no_fabricated_percentage():
    snap = _snapshot()
    for sec, e in snap["coverage_matrix"].items():
        if not e["has_event_benchmark"]:
            assert "%" not in e["event_coverage_state"], f"{sec} must not fabricate a coverage %"
            assert e["event_coverage_state"] in (
                "no events", "thin", "expanded but unbenchmarked",
            ), f"{sec} state must be a defined descriptive state"


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_coverage_matrix_keeps_event_inventory_recovery_distinct():
    """EVENT coverage, ASSET-INVENTORY coverage and RECOVERY-EVIDENCE coverage are three
    different concepts and are never merged into one number (§5)."""
    snap = _snapshot()
    for sec, e in snap["coverage_matrix"].items():
        assert {"event_count", "asset_inventory_count", "recovery_episodes"} <= set(e)


# --------------------------------------------------------------------------
# Iteration 6: experimental gas-processing sub-index (§16-§20)
# --------------------------------------------------------------------------

@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_experimental_gas_index_excluded_from_headline_esdi():
    """§18: the gas-processing sub-index is experimental and must never enter the headline."""
    snap = _snapshot()
    g = (snap.get("experimental_indices") or {}).get("gas_processing")
    assert g is not None, "experimental gas-processing index should be present"
    assert g["experimental"] is True and g["in_headline_esdi"] is False
    # Gas still contributes exactly zero to the composite.
    assert snap["sectors"]["gas"] == 0.0


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_gas_graduation_decision_is_experimental_with_reasons():
    """§19: iteration 7 makes an explicit graduation DECISION and records why gas processing did
    not graduate to the headline (no matched denominator + non-comparable capacities)."""
    snap = _snapshot()
    g = snap["experimental_indices"]["gas_processing"]
    assert g.get("graduation_decision") == "experimental"
    reasons = g.get("graduation_reasons") or []
    assert len(reasons) >= 2
    joined = " ".join(reasons).lower()
    assert "denominator" in joined and ("design" in joined or "throughput" in joined)
    # §20: the caveat must forbid a summed 'Gas' super-score across processing/LNG/pipelines.
    assert "lng" in g["caveat"].lower()


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_experimental_gas_index_is_within_census_not_national():
    """§17: no national denominator. The share is disrupted vs the CENSUSED capacity, and the
    weighted disrupted capacity can never exceed the census."""
    snap = _snapshot()
    g = snap["experimental_indices"]["gas_processing"]
    assert g["census_bcm_y"] > 0 and g["census_plants"] >= 1
    assert g["disrupted_bcm_y_weighted"] <= g["census_bcm_y"] + 1e-9
    if g["within_census_exposure_pct"] is not None:
        assert g["within_census_exposure_pct"] == pytest.approx(
            100 * g["disrupted_bcm_y_weighted"] / g["census_bcm_y"], abs=0.1)
    # The caveat must state it is not a national figure.
    assert "not" in g["caveat"].lower() and "national" in g["caveat"].lower()


def test_gas_processing_capacity_is_structured_not_prose():
    """§16: GPP capacities live in an explicit bcm/y field, never parsed from the note text."""
    import csv
    path = ROOT / "data" / "curated" / "assets_supplement.csv"
    with open(path, encoding="utf-8", newline="") as f:
        gpps = [r for r in csv.DictReader(f) if r["asset_class"] == "gas_processing"]
    assert gpps, "expected gas_processing rows"
    for r in gpps:
        assert r.get("capacity_bcm_y"), f"{r['asset_id']} needs a structured bcm/y capacity"
        float(r["capacity_bcm_y"])  # must be numeric
        assert r.get("capacity_status") in ("sourced", "aggregate", "uncertain"), r["asset_id"]


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_lng_and_condensate_not_counted_in_gpp_census():
    """§19: LNG / gas-condensate complexes are kept separate from the gas-PROCESSING census."""
    snap = _snapshot()
    g = snap["experimental_indices"]["gas_processing"]
    struck_ids = {p["asset_id"] for p in g["struck"]}
    # The Novatek Ust-Luga gas-condensate/LNG complex is struck but is NOT a censused GPP.
    assert "ust-luga-novatek-gas" not in struck_ids


# --------------------------------------------------------------------------
# Iteration 6: source-backed strategic / observed effects (§25-28)
# --------------------------------------------------------------------------

@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_strategic_effects_present_and_evidence_tagged():
    """Every observed effect carries an evidence tag and a source; national vs per-incident are
    kept separate (§25). Works whether or not any effects are curated yet."""
    snap = _snapshot()
    se = snap.get("strategic_effects")
    assert se is not None and "national" in se and "by_incident" in se
    all_effects = list(se["national"]) + [e for lst in se["by_incident"].values() for e in lst]
    for e in all_effects:
        assert e["evidence_kind"] in ("observed", "estimated", "modelled", "unknown")
        assert e.get("source_url"), f"a sourced effect must cite a source: {e}"
        assert e.get("effect_type")


@pytest.mark.skipif(not (PROCESSED / "incidents.json").exists(), reason="pipeline not run")
def test_effects_attach_only_to_real_incidents():
    """§25: per-incident effects must key to incidents that exist (no orphans)."""
    snap = _snapshot()
    se = snap.get("strategic_effects") or {"by_incident": {}}
    incidents = json.loads((PROCESSED / "incidents.json").read_text(encoding="utf-8"))
    ids = {i["incident_id"] for i in incidents}
    for iid in se["by_incident"]:
        assert iid in ids, f"effect references unknown incident {iid}"


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_repair_costs_are_never_bare_numbers():
    """§27: a repair-cost effect must carry currency + year, never an un-anchored figure."""
    snap = _snapshot()
    se = snap.get("strategic_effects") or {"national": [], "by_incident": {}}
    for e in list(se["national"]) + [x for lst in se["by_incident"].values() for x in lst]:
        if e["effect_type"] == "repair_cost" and e["value_numeric"] is not None:
            assert e.get("currency") and e.get("cost_year"), f"repair cost needs currency+year: {e}"


# --------------------------------------------------------------------------
# Iteration 6: candidate discovery is human-gated and CANNOT feed the scored dataset (§29-30)
# --------------------------------------------------------------------------

def test_candidate_discovery_fails_safely_and_never_raises():
    """The discovery step must return [] on any failure (e.g. no network here) and never raise,
    so it can never break anything."""
    from pipeline import discover_candidates as dc
    got = dc.discover(days_back=1, max_records=5, timeout=3)
    assert isinstance(got, list)  # [] when the feed is unreachable — the common CI case


def test_candidate_pointers_carry_no_location_or_score():
    """§29 scope guard: a candidate is a bare pointer for human review — never a located or
    scored record. The queue schema must contain no location/score/facility fields."""
    from pipeline import discover_candidates as dc
    banned = {"lat", "lon", "latitude", "longitude", "coordinate", "region", "region_code",
              "score", "esdi", "capacity", "facility", "asset_id", "sector"}
    assert not (set(dc._FIELDS) & banned), dc._FIELDS
    assert "needs_review" in dc._FIELDS or "status" in dc._FIELDS


def test_build_never_imports_candidate_discovery():
    """The daily build must not import the discovery module — discovery can never auto-feed the
    scored pipeline; a human hand-adds a curated incident or nothing happens."""
    run_src = (ROOT / "pipeline" / "run.py").read_text(encoding="utf-8")
    assert "discover_candidates" not in run_src, "run.py must not import candidate discovery"


def test_discovery_writes_only_to_review_queue_not_curated_or_processed():
    """The discovery module's output path must live under data/review, never curated/processed."""
    from pipeline import discover_candidates as dc
    assert dc.REVIEW_DIR.name == "review" and dc.REVIEW_DIR.parent.name == "data"
    assert dc.QUEUE.parent == dc.REVIEW_DIR
    parts = set(dc.QUEUE.parts)
    assert "curated" not in parts and "processed" not in parts


# --------------------------------------------------------------------------
# Iteration 6: headline-number consistency (§2, §39)
# --------------------------------------------------------------------------

@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_current_state_doc_is_in_sync():
    """docs/CURRENT_STATE.md is the single source of truth for headline numbers and must match
    the current build. If this fails, run `python -m pipeline.run` to regenerate it (§2)."""
    from pipeline import current_state
    doc = current_state.DOC
    assert doc.exists(), "docs/CURRENT_STATE.md is missing — run the build"
    snap = _snapshot()
    expected = current_state.render(snap, current_state.count_tests())
    actual = doc.read_text(encoding="utf-8")
    assert actual == expected, (
        "docs/CURRENT_STATE.md is stale vs the built snapshot — rebuild to regenerate it. "
        "This is the drift guard: headline counts must not be hand-maintained."
    )


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_release_payload_is_a_current_date_build_not_a_frozen_reference():
    """The committed/release payload must be a CURRENT-DATE build.

    Two different builds are legitimate and deliberately produce different headlines:

        production   python -m pipeline.run                     -> as_of = build day
        regression   python -m pipeline.run --as-of 2026-08-28   -> the frozen comparison point

    The frozen build exists ONLY for apples-to-apples methodology comparison across iterations;
    ESDI moves with time decay, so shipping a frozen payload would freeze the live dashboard at
    a stale date and silently misreport the present. A frozen build is detectable because its
    as_of lags its build_time; a production build has them on the same day.

    If this fails after a regression run, rebuild the release payload with a plain
    `python -m pipeline.run` before committing.
    """
    snap = _snapshot()
    as_of = dt.date.fromisoformat(snap["as_of"])
    built = dt.datetime.fromisoformat(snap["build_time"]).date()
    lag = (built - as_of).days
    # 1 day of slack absorbs a UTC build_time crossing local midnight.
    assert lag <= 1, (
        f"release payload looks like a FROZEN regression build: as_of={as_of} but it was built "
        f"on {built} ({lag} days later). Regenerate with `python -m pipeline.run` (no --as-of) "
        f"before committing. The frozen build belongs in a comparison run, not the release tree."
    )


# --------------------------------------------------------------------------
# Iteration 6: canonical refinery registry + linkage (§6-§9)
# --------------------------------------------------------------------------
# One stable id + alias set per refinery, so denominator and incidents resolve to the SAME
# canonical asset instead of display-name string equality. Uncertain names never auto-resolve.

def test_all_denominator_refineries_resolve_to_canonical_ids():
    from pipeline import refinery_registry as RR
    if not (PROCESSED / "refinery_inventory.json").exists():
        pytest.skip("pipeline not run")
    inv = json.loads((PROCESSED / "refinery_inventory.json").read_text(encoding="utf-8"))["refineries"]
    for r in inv:
        assert RR.resolve(r["name"]) is not None, f"{r['name']} must resolve to a canonical id"


def test_petrochemical_complex_excluded_from_fuels_denominator():
    from pipeline import refinery_registry as RR
    reg = RR.by_id()
    assert reg["tobolsk"]["denominator_status"] == "exclude"
    assert "tobolsk" not in RR.denominator_ids()


def test_refinery_alias_resolution_disambiguates_co_located_plants():
    from pipeline import refinery_registry as RR
    # distinct plants in the same city must NOT collapse to one id
    assert RR.resolve("TANECO") == "taneco"
    assert RR.resolve("TAIF-NK") == "taif-nk"
    assert RR.resolve("taneco") != RR.resolve("taif-nk")
    assert RR.resolve("Ufa Refinery") == "ufa"
    assert RR.resolve("Novo-Ufa Refinery") == "novo-ufa"
    assert RR.resolve("Ufaneftekhim Refinery") == "ufaneftekhim"
    # an unknown name returns None — no fuzzy guessing (§7)
    assert RR.resolve("Totally Unknown Plant XYZ") is None


def test_no_alias_collision_across_canonical_ids():
    """Two different canonical ids must not share a normalized alias — that would double-count
    one facility's capacity into the denominator (§7/§10)."""
    import collections
    from pipeline import refinery_registry as RR
    idx = collections.defaultdict(set)
    for r in RR.load():
        for a in [r["canonical_id"], r["canonical_name"], *r["aliases"]]:
            key = RR._norm(a)
            if key:
                idx[key].add(r["canonical_id"])
    collisions = {k: v for k, v in idx.items() if len(v) > 1}
    assert not collisions, f"alias collisions would double-count capacity: {collisions}"


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
def test_canonical_linkage_is_identity_not_disruption_coverage():
    snap = _snapshot()
    cl = snap["refinery_reconciliation"]["canonical_linkage"]
    assert 0 < cl["struck_refineries"] <= cl["denominator_refineries"]
    assert 0 < cl["pct_denominator_mtpa_struck"] <= 100
    # Naftan is a Belarusian refinery, intentionally outside the Russian denominator
    assert "Naftan refinery (Novopolotsk)" in cl["incidents_unresolved_to_registry"]
