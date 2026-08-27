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
    aoi = aoi_regions()
    assert len(aoi) == 69
    by_district = {}
    for _, (_, _, district, _) in aoi.items():
        by_district[district] = by_district.get(district, 0) + 1
    assert by_district == {
        "Central": 18, "Northwestern": 11, "Southern": 6,
        "North Caucasian": 7, "Volga": 14, "Ural": 6, "Belarus": 7,
    }


def test_region_codes_are_unique():
    codes = [v[0] for v in RU_REGIONS.values()]
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
        ("Omsk Oblast", "out_of_aoi", None),
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
    assert resolve("Krasnoyarsk Krai")[0] == "out_of_aoi"
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


def test_weight_decays_by_half_life():
    inc = _incident()
    day0 = _weight_at(inc, dt.date(2026, 1, 1))
    # refinery half-life is 45 days
    day45 = _weight_at(inc, dt.date(2026, 2, 15))
    assert day0 == pytest.approx(1.0, abs=1e-9)
    assert day45 == pytest.approx(0.5, abs=0.01)


def test_future_events_do_not_contribute():
    assert _weight_at(_incident(date="2026-06-01"), dt.date(2026, 1, 1)) == 0.0


def test_confidence_and_cause_reduce_weight():
    strong = _weight_at(_incident(), dt.date(2026, 1, 1))
    weak = _weight_at(_incident(confidence="possible"), dt.date(2026, 1, 1))
    planned = _weight_at(_incident(cause="maintenance"), dt.date(2026, 1, 1))
    assert weak < strong
    assert planned < weak


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
