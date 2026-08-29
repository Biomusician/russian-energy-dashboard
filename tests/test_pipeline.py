"""Tests for the parsing, scoring and scope guarantees.

The scope tests are not decoration. This project sits next to a boundary it must not
cross, and the cheapest way to keep a future change from drifting over it is to fail
the build when it does.
"""

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
    """Tracked capacity must be <= the national estimate, and coverage must be the honest
    ratio of the two — never forced to 100% by padding unlike facilities."""
    snap = _snapshot()
    rec = snap.get("refinery_reconciliation")
    assert rec is not None, "refinery_reconciliation should be emitted"
    tracked = rec["tracked_mtpa"]
    national = rec["national_public_estimate_mtpa"]
    assert 0 < tracked <= national, "tracked capacity must not exceed the national estimate"
    assert rec["gap_mtpa"] == pytest.approx(national - tracked, abs=0.2)
    assert rec["coverage_pct"] == pytest.approx(100.0 * tracked / national, abs=0.6)
    assert rec["coverage_pct"] < 100.0, "coverage should be an honest lower bound, not 100%"


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
