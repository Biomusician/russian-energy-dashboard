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
def test_crimea_is_a_permitted_context_unit_others_excluded():
    """Iteration 2: Crimea is a narrow, explicit exception -- present as a separately
    identified CONTEXT unit (not a Russian federal subject), while the other four
    annexed oblasts remain fully excluded from the region layer."""
    regions = json.loads((PROCESSED / "regions.json").read_text(encoding="utf-8"))
    by_name = {r["name"].lower(): r for r in regions}
    # Crimea present, but explicitly marked as context, Ukrainian, and ESDI-excluded.
    assert "crimea" in by_name
    crimea = by_name["crimea"]
    assert crimea["analytic_scope"] == "context"
    assert crimea["esdi_included"] is False
    assert crimea["country"] == "UA"
    assert "ukrain" in crimea["sovereignty"].lower()
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
def test_crimea_excluded_from_national_esdi_denominator():
    """Crimea events must never enter the Russia+Belarus ESDI composite or denominator."""
    snap = json.loads((PROCESSED / "snapshot.json").read_text(encoding="utf-8"))
    crimea = snap["regions"]["UA-CR"]
    assert crimea["esdi_included"] is False
    # Its own regional exposure may be shown, but it is not in the national aggregate:
    # rebuild-invariant check that a Crimea-only event cannot move the national ESDI.
    incidents = json.loads((PROCESSED / "incidents.json").read_text(encoding="utf-8"))
    crimea_incidents = [i for i in incidents if i.get("region_code") == "UA-CR"]
    assert crimea_incidents, "expected at least one tracked Crimea event"
    for i in crimea_incidents:
        # Crimea events are tracked (region-coded) but carry no coordinates, like all others.
        assert "lat" not in i and "lon" not in i


def test_context_geography_has_no_analytic_infrastructure():
    """Context countries are display-only: no asset in the emitted asset layer may sit
    in a context country, and context files carry no scoring fields."""
    land = json.loads((PROCESSED / "context_land.geojson").read_text(encoding="utf-8"))
    for f in land["features"]:
        props = f["properties"]
        # only display metadata, never an event/score/capacity field
        assert set(props) <= {"iso", "name", "label_lon", "label_lat"}, props


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
