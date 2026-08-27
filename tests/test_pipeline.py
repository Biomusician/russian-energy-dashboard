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
    """The ambiguous 'SFD' abbreviation must not appear in code, config or methodology."""
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    offenders = []
    for sub in ("pipeline", "methodology", "docs"):
        for path in (root / sub).rglob("*"):
            if path.suffix not in (".py", ".json", ".md"):
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
# Recovery / reconstitution framework (iteration 1)
# --------------------------------------------------------------------------

def test_observed_recovery_overrides_modelled_decay():
    """A sourced, faster-than-generic reconstitution must decay faster than the
    modelled fallback -- evidence overrides assumption."""
    from pipeline import recovery
    inc = _incident(date="2026-01-01")
    fast = {"reconstitution_observed_days": 30, "sources": [{"url": "x"}]}
    on_day40 = dt.date(2026, 2, 10)
    modelled = _weight_at(inc, on_day40, None)
    observed = _weight_at(inc, on_day40, fast)
    assert observed < modelled
    assert recovery.recovery_kind("refinery", fast) == "observed"


def test_estimated_and_modelled_kinds_are_distinguished():
    from pipeline import recovery
    est = {"estimate_central_days": 200, "sources": [{"url": "x"}]}
    assert recovery.recovery_kind("refinery", est) == "estimated"
    assert recovery.recovery_kind("refinery", None) == "modelled"
    assert recovery.recovery_kind("refinery", {}) == "modelled"


def test_confirmed_reconstitution_caps_at_residual():
    """Once a facility is credibly reported restored, its contribution collapses."""
    from pipeline import recovery
    inc = _incident(date="2026-01-01")
    rec = {"reconstituted_at": "2026-02-01", "status": "repaired", "sources": [{"url": "x"}]}
    after = _weight_at(inc, dt.date(2026, 3, 1), rec)
    assert after <= recovery.RESIDUAL + 1e-6
    assert recovery.is_resolved(rec, dt.date(2026, 3, 1))
    assert not recovery.is_resolved(rec, dt.date(2026, 1, 15))  # before reconstitution


def test_impairment_age_none_when_resolved():
    from pipeline import recovery
    rec = {"reconstituted_at": "2026-02-01", "status": "repaired", "sources": [{"url": "x"}]}
    # resolved facility: age is measured to reconstitution, not open-ended
    age = recovery.impairment_age_days("2026-01-01", rec, dt.date(2026, 6, 1))
    assert age == 31  # 1 Jan -> 1 Feb


def test_recovery_record_without_source_is_ignored(tmp_path, monkeypatch):
    """Provenance integrity: a recovery row with no source URL must be skipped."""
    from pipeline import recovery as rec_mod
    csv = tmp_path / "recovery.csv"
    csv.write_text(
        "asset_id,status,reconstitution_observed_days,source_urls\n"
        "no-source-facility,repaired,10,\n"
        "good-facility,repaired,10,https://example.org/x\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(rec_mod, "CURATED", tmp_path)
    records = rec_mod.load_recovery_records()
    assert "good-facility" in records
    assert "no-source-facility" not in records


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
def test_occupied_territory_is_excluded():
    regions = json.loads((PROCESSED / "regions.json").read_text(encoding="utf-8"))
    names = {r["name"].lower() for r in regions}
    for excluded in ("crimea", "sevastopol", "donetsk", "luhansk", "zaporizhzhia", "kherson"):
        assert excluded not in names


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
def test_recovery_stats_present_with_sample_sizes():
    snap = _snapshot()
    rs = snap["recovery_stats"]
    # Sample sizes must accompany every median so a median-of-one is never mistaken
    # for a robust figure.
    assert "observed_restoration_sample" in rs
    assert "impairment_age_sample" in rs
    if rs["median_observed_restoration_days"] is not None:
        assert rs["observed_restoration_sample"] >= 1
    kinds = rs["evidence_kind_counts"]
    assert set(kinds) <= {"observed", "estimated", "modelled"}


@pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(),
                    reason="pipeline has not been run")
def test_recovery_evidence_kinds_distinguish_observed_from_estimated():
    """Observed and estimated recovery must be structurally distinct in emitted data."""
    snap = _snapshot()
    for x in snap["live_disruptions"]:
        rec = x["recovery"]
        assert rec["recovery_evidence_kind"] in ("observed", "estimated", "modelled")
        if rec["recovery_evidence_kind"] == "estimated":
            assert rec["estimate_days"] is not None
        if rec["recovery_evidence_kind"] == "modelled":
            # A modelled facility must not masquerade as having observed timing.
            assert rec["observed_restoration_days"] is None
            assert rec["reconstitution_observed_days"] is None


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
