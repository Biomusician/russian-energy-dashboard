"""Final test-architecture red team, iteration 23 (review §25): code paths no test exercised.

T-1  the theatre's effect embargo was only ever asked "is anything still withheld today?", which a
     version that withheld nothing answers best;
T-3  CI's Python job skipped every test that bundles the shipped TypeScript;
T-6  the strike-table parser was reached only with the raw cache, so a row reader that picked up the
     source's distance column again would have passed every test.
T-2, T-4 and T-5 are gate rules, tested beside the gate in tests/test_iteration22_impacts.py.
"""

import json
import re
from pathlib import Path

from pipeline import fetch_wikipedia as FW
from pipeline import recovery as R

ROOT = Path(__file__).resolve().parent.parent


# ---- T-1: the embargo withholds what it should, on a synthetic campaign ---------------------------

CAMPAIGN = {"member_rule": {"causes": ["drone_strike"], "from": "2025-01-01"}}
INCIDENTS = [
    {"incident_id": "member", "cause": "drone_strike", "date": "2026-11-01"},
    {"incident_id": "before", "cause": "drone_strike", "date": "2024-06-01"},
    {"incident_id": "other_cause", "cause": "accident", "date": "2026-11-01"},
]


def _effects():
    return {
        "member": [{"id": "at_the_time", "as_of_date": "2026-11-03"},
                   {"id": "later", "as_of_date": "2026-11-15"},
                   {"id": "undated", "as_of_date": None}],
        "before": [{"id": "old_undated", "as_of_date": None}],
        "other_cause": [{"id": "accident_undated", "as_of_date": None}],
        "unknown_incident": [{"id": "orphan", "as_of_date": None}],
    }


def _ids(kept):
    return {iid: [e["id"] for e in effects] for iid, effects in kept.items()}


def test_t1_the_embargo_holds_a_later_report_and_never_releases_an_undated_one(monkeypatch):
    monkeypatch.setattr(R, "theatre_campaign", lambda: CAMPAIGN)
    kept, withheld, ids = R.embargo_effects(_effects(), INCIDENTS, "2026-11-20", embargo_days=30)
    assert _ids(kept) == {"member": ["at_the_time"], "before": ["old_undated"],
                          "other_cause": ["accident_undated"], "unknown_incident": ["orphan"]}
    assert (withheld, ids) == (2, ["member"])
    # After the delay the later report is released; the undated one never is.
    kept, withheld, ids = R.embargo_effects(_effects(), INCIDENTS, "2026-12-15", embargo_days=30)
    assert _ids(kept)["member"] == ["at_the_time", "later"] and (withheld, ids) == (1, ["member"])
    # The day before release it is still held.
    kept, _, _ = R.embargo_effects(_effects(), INCIDENTS, "2026-12-14", embargo_days=30)
    assert _ids(kept)["member"] == ["at_the_time"]


def test_t1_an_inactive_campaign_withholds_nothing(monkeypatch):
    monkeypatch.setattr(R, "theatre_campaign", lambda: None)
    by = _effects()
    assert R.embargo_effects(by, INCIDENTS, "2026-11-20", embargo_days=30) == (by, 0, [])


# ---- T-3: the Python job installs the bundler and refuses to skip without it -----------------------

def test_t3_ci_python_job_installs_the_bundler_and_requires_it():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    job = ci[:ci.index("\n  frontend:")]
    install, run = job.index("npm ci"), job.index("python -m pytest")
    assert install < run, "node_modules must exist before the suite runs"
    assert 'EDM_REQUIRE_BUNDLER: "1"' in job[install:run + 40]
    src = (ROOT / "tests" / "test_iteration21_testarch.py").read_text(encoding="utf-8")
    assert 'not os.environ.get("EDM_REQUIRE_BUNDLER")' in src


# ---- T-6: the strike-table parser never reads the distance column ----------------------------------

ROW = ("| Synthetic Refinery || Belgorod Oblast || Synthetic Operator || 5.0 || 987654 || "
       "15 March 2025<ref>{{{{cite web |url=https://news.example/synthetic/{n} |title=Synthetic report "
       "|date=15 March 2025}}}}</ref>\n")
TABLE = ("{{| class=\"wikitable\"\n! Facility !! Region !! Operator !! Capacity by Mtpa !! Distance (km) !! "
         "Date of strike(s)\n|-\n" + ROW + "|}}\n")
WIKITEXT = ("Intro.\n" + FW.SECTION_HEADING + " ==\n" + TABLE.format(n="a") + "\nText.\n" + TABLE.format(n="b")
            + "\n== Next section ==\n")


def _keys(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from _keys(v)
    elif isinstance(node, list):
        for v in node:
            yield from _keys(v)


def test_t6_the_parser_reads_the_row_and_never_its_distance(monkeypatch):
    monkeypatch.setattr(FW, "load_wikitext", lambda as_of=None, max_age_hours=12: (WIKITEXT, 1))
    facilities, incidents, warnings, _ = FW.build()
    assert len(facilities) == 2 and facilities[0]["name"] == "Synthetic Refinery"
    assert facilities[0]["capacity_mtpa"] == 5.0 and facilities[0]["operator"] == "Synthetic Operator"
    assert incidents, "the dated strike becomes an incident"
    out = json.dumps([facilities, incidents, warnings], ensure_ascii=False)
    assert "987654" not in out, "the distance column's value reached the parser's output"
    for k in set(_keys([facilities, incidents])):
        assert not re.search(r"distance|range|reach|km", k, re.I), k
