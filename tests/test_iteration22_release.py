"""Iteration 22 release closure: two guards the test-architecture red team found missing.

Both were held back while the corpus still broke them. Rounds 2 and 3 of the lead rulings
normalised those records, and the served corpus now passes both guards, so they gate import and build.

  affected is the scale affected (methodology section 4): an affected unit that is a duration, a
      recovery time or a restoration share ("hours until supply was restored", "percent restored")
      is refused. Time and restoration belong in duration_text or the effect text.
  basis 2 needs a figure: "large population affected, in the source's own figure and unit". A
      record with no affected figure meets basis 4 or another basis, or none. A country-wide loss
      never needs an invented count.
"""
import copy
import json
from pathlib import Path

import pytest

from pipeline import global_impacts as G

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "impacts22"
WORLD = ROOT / "data" / "processed" / "global" / "world.geojson"
SERVED = ROOT / "data" / "processed" / "global" / "impacts.json"
UNIT_NAMES = {"ir": ["khuzestan", "tehran", "bushehr"], "iq": ["basrah", "al basrah", "kurdistan"],
              "sa": ["eastern province"], "ae": ["abu dhabi"], "bh": [], "kw": [], "om": [], "qa": []}
FRA = "imp-2025-03-05-fra-electricity-synthetic-grid-ransomware"   # basis 2, 120,000 customers


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rec(impact_id):
    return copy.deepcopy(next(r for r in _json(FIXTURE / "events.json")["records"] if r["impact_id"] == impact_id))


def problems(record):
    states = _json(FIXTURE / "link_health.json")["link_states"]
    return G.one_record_problems(record, G.load_context(WORLD, unit_names=copy.deepcopy(UNIT_NAMES), link_states=states))


def test_the_fixture_record_is_clean():
    assert problems(rec(FRA)) == []


@pytest.mark.parametrize("unit", [
    "hours until supply was restored", "percent of internet service restored", "days", "hours",
    "minutes without service", "weeks", "customers restored", "percent recovered",
])
def test_an_affected_figure_that_is_a_duration_or_a_restoration_is_refused(unit):
    r = rec(FRA)
    r["civilian_service_impact"][0]["affected"]["unit"] = unit
    assert any("is a duration or a restoration figure" in p for p in problems(r)), unit


@pytest.mark.parametrize("unit", [
    "customers", "households", "homes, farms and businesses", "residents", "properties", "subscribers",
    "daily passengers", "hospitals",
])
def test_a_scale_unit_is_accepted(unit):
    r = rec(FRA)
    r["civilian_service_impact"][0]["affected"]["unit"] = unit
    assert not [p for p in problems(r) if "duration or a restoration" in p], unit


def test_basis_2_without_a_figure_is_refused():
    r = rec(FRA)
    r["civilian_service_impact"][0]["affected"] = {"value": "unknown", "unit": "customers", "qualifier": None,
                                                   "source_says": "customers across the region (no figure given)"}
    assert any("inclusion_basis 2" in p for p in problems(r))
    r["civilian_service_impact"] = []
    r["effect_specificity"] = "described"
    assert any("inclusion_basis 2" in p for p in problems(r))


def test_the_same_record_without_a_figure_is_accepted_on_basis_4():
    r = rec(FRA)
    r["civilian_service_impact"][0]["affected"] = {"value": "unknown", "unit": "customers", "qualifier": None,
                                                   "source_says": "customers across the region (no figure given)"}
    r["inclusion_basis"] = 4
    assert not [p for p in problems(r) if "inclusion_basis" in p]


def test_the_served_corpus_passes_both_guards():
    doc = _json(SERVED)
    for r in doc["records"]:
        figures = []
        for c in r["civilian_service_impact"]:
            a = c["affected"]
            if isinstance(a, dict) and isinstance(a.get("value"), (int, float)):
                figures.append(a)
                assert not G.AFFECTED_NOT_A_SCALE.search(a.get("unit") or ""), r["impact_id"]
        if r["inclusion_basis"] == 2:
            assert figures, r["impact_id"]
