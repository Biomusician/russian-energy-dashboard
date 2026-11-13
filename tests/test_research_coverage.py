"""The Research Coverage Explorer: lane states as a reader is told them.

The state mapping lives in web/src/global/laneCoverage.ts and is the code that ships. It has only
type imports, so plain Node runs it as it is (Node 24 strips the types). These tests execute it
against every served country system and against made-up lanes for the cases the served data does
not contain, so the mutation campaign can catch a broken rule in the frontend, not only in the
build. The rules:

- the states are the build's own eight (`lane_summary_state`), counted exactly as the build counts
  them, so every page that shows source-group states says the same thing;
- a source that refused access is "Source unavailable", however much else the lane did;
- a lane stopped by our own search allowance is never one of the three done states;
- a done state only where the lane's own execution says so, every required language ran and the
  source was readable, and the three never merge into one "complete"; a missing language is always
  shown;
- under the attack-campaign rule no count of candidates, held records or outcomes is rendered;
- research coverage is kept apart from source health.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from pipeline import build_systems as B

ROOT = Path(__file__).resolve().parent.parent
GIT_ROOT = Path(os.environ.get("EDM_GIT_ROOT", ROOT))
WEB = ROOT / "web" / "public" / "data"
MODULE = ROOT / "web" / "src" / "global" / "laneCoverage.ts"
COMPONENT = ROOT / "web" / "src" / "global" / "ResearchCoverage.tsx"


def _node():
    """The project's portable Node (tools/node, not on PATH), found from this checkout, the checkout
    the mutation campaign was started from, or any parent (a worktree sits inside the main
    checkout); else a Node on PATH."""
    if os.environ.get("EDM_NODE"):
        return os.environ["EDM_NODE"]
    for base in (ROOT, GIT_ROOT):
        for d in (base, *base.parents):
            for name in ("node.exe", "node"):
                p = d / "tools" / "node" / name
                if p.is_file():
                    return str(p)
    return shutil.which("node")


NODE = _node()
needs_node = pytest.mark.skipif(NODE is None, reason="no Node to run the shipped TypeScript")
needs_payload = pytest.mark.skipif(not (WEB / "global" / "manifest.json").exists(), reason="no built payload")

HARNESS = """
import { readFileSync } from "node:fs";
const m = await import(process.argv[2]);
const input = JSON.parse(readFileSync(0, "utf-8"));
const out = {};
out.states = input.lanes.map((l) => m.coverageState(l));
out.missing = input.lanes.map((l) => m.missingLanguages(l));
out.systems = {};
for (const [id, sys] of Object.entries(input.systems)) {
  const rows = m.latestLanes(sys.research_log.passes);
  const restricted = m.isCampaignRestricted(sys);
  out.systems[id] = {
    rows: rows.map((r) => ({ lane: r.lane.lane, state: r.state, pass: r.pass.date })),
    counts: m.countStates(rows),
    summary: m.coverageSummary(rows, sys.research_log.passes.length),
    restricted,
    review: m.reviewLine(sys),
    outcomes: sys.research_log.passes.map((p) => m.passOutcomeText(p, restricted)),
  };
}
process.stdout.write(JSON.stringify(out));
"""


def _run(lanes=(), systems=None, tmp_path=None):
    harness = tmp_path / "harness.mjs"
    harness.write_text(HARNESS, encoding="utf-8")
    payload = json.dumps({"lanes": list(lanes), "systems": systems or {}})
    r = subprocess.run([NODE, str(harness), MODULE.as_uri()], input=payload, capture_output=True,
                       text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _lane(**kw):
    base = {"lane": "T1", "universe_kind": "declared_query_set", "execution": "declared_search_complete",
            "source_window": "no_census_exists", "languages_required": ["en"], "languages_executed": ["en"],
            "queries_declared": 4, "queries_run": 4}
    return {**base, **kw}


def _served_systems():
    manifest = json.loads((WEB / "global" / "manifest.json").read_text(encoding="utf-8"))
    out = {}
    for s in manifest["systems"]:
        if s["kind"] == "country":
            out[s["id"]] = json.loads((WEB / "systems" / s["id"] / "system.json").read_text(encoding="utf-8"))
    return out


DONE = ("universe_searched", "current_through_latest_release", "declared_query_set_run")


def _done(lane):
    """The build's own `_lane_done`, plus the language rule its validator enforces at build time."""
    return (lane["execution"] in ("enumerated_complete", "declared_search_complete")
            and lane["source_window"] not in ("inaccessible", "unknown")
            and set(lane.get("languages_required") or []) <= set(lane.get("languages_executed") or []))


@needs_node
def test_blocked_and_stopped_lanes_are_never_complete(tmp_path):
    lanes = [
        _lane(execution="partial", source_window="inaccessible"),
        _lane(execution="not_started", source_window="inaccessible"),
        _lane(execution="declared_search_complete", source_window="inaccessible"),
        _lane(execution="partial", stopped_by="search_limit"),
        _lane(execution="declared_search_complete", stopped_by="search_limit"),
        _lane(execution="partial", source_window="rolling_archive_gap", stopped_by="search_limit"),
        _lane(execution="partial", source_window="rolling_archive_gap"),
        _lane(execution="not_started"),
        _lane(),
    ]
    out = _run(lanes, tmp_path=tmp_path)
    assert out["states"] == ["blocked_by_source", "blocked_by_source", "blocked_by_source",
                             "stopped_by_search_limit", "stopped_by_search_limit", "stopped_by_search_limit",
                             "partially_searched", "not_started", "declared_query_set_run"]


@needs_node
def test_a_lane_missing_a_language_is_shown_missing_and_never_complete(tmp_path):
    lanes = [
        _lane(languages_required=["en", "fa"], languages_executed=["en"]),
        _lane(universe_kind="census", execution="enumerated_complete", source_window="current_through_end_date",
              languages_required=["ar", "en"], languages_executed=["en"]),
        _lane(languages_required=["ar"], languages_executed=None),
    ]
    out = _run(lanes, tmp_path=tmp_path)
    assert out["missing"] == [["fa"], ["ar"], ["ar"]]
    assert not set(out["states"]) & set(DONE), out["states"]


@needs_node
@needs_payload
def test_every_served_system_maps_its_lanes_as_the_build_counts_them(tmp_path):
    systems = _served_systems()
    out = _run(systems=systems, tmp_path=tmp_path)
    checked = 0
    for sid, sys in systems.items():
        got = out["systems"][sid]
        assert got["rows"], f"{sid}: no lane reached the reader"
        newest = [p for p in sys["research_log"]["passes"] if p["kind"] == "systematic"][-1]
        lanes = {l["lane"]: l for l in newest["lanes"]}
        rf = sys["research_freshness"]
        if {r["lane"] for r in got["rows"]} == set(lanes):
            # State for state, the counts every other page reads from the build.
            assert {k: v for k, v in got["counts"].items() if v} == rf["lane_states"], sid
            assert sum(got["counts"][k] for k in DONE) == rf["lanes_complete"], sid
        for r in got["rows"]:
            lane = lanes.get(r["lane"])
            if lane is None:
                continue
            checked += 1
            if lane.get("source_window") == "inaccessible":
                assert r["state"] == "blocked_by_source", (sid, r)
            elif lane.get("stopped_by") == "search_limit":
                assert r["state"] == "stopped_by_search_limit", (sid, r)
            assert r["state"] == B.lane_summary_state(lane), (sid, r)
            assert (r["state"] in DONE) == _done(lane), (sid, r, lane.get("execution"))
        n = len(got["rows"])
        assert got["summary"].startswith(f"{n} source group{'' if n == 1 else 's'}: "), sid
        assert "%" not in got["summary"] and "complete" not in got["summary"]
    assert checked > 0


@needs_node
@needs_payload
def test_campaign_systems_render_no_count_from_the_research_outcome(tmp_path):
    systems = _served_systems()
    restricted = {sid for sid, s in systems.items()
                  if any(c.get("policy_applied") for c in s["publication_policy"]["campaigns"])}
    assert restricted, "no system is under the campaign policy, so this test checks nothing"
    # Whatever the served log carries, a count must not reach the reader: give every pass counts.
    seeded = {}
    for sid in restricted:
        s = json.loads(json.dumps(systems[sid]))
        for p in s["research_log"]["passes"]:
            p["outcome"] = {"candidates": 4817, "held": 3929, "rejected": 5743, "accepted": 6151}
        seeded[sid] = s
    out = _run(systems=seeded, tmp_path=tmp_path)
    for sid in restricted:
        got = out["systems"][sid]
        assert got["restricted"], sid
        for text in got["outcomes"] + [got["review"] or ""]:
            assert not any(ch.isdigit() for ch in text), (sid, text)
        newest = [p for p in systems[sid]["research_log"]["passes"] if p["kind"] == "systematic"][-1]
        assert (got["review"] is not None) == bool(newest.get("under_review")), sid
    # Outside the policy the history keeps its counts: the guard is the policy, not a blanket rule.
    free = sorted(set(systems) - restricted)
    if free:
        out = _run(systems={free[0]: systems[free[0]]}, tmp_path=tmp_path)
        assert any(any(ch.isdigit() for ch in t) for t in out["systems"][free[0]]["outcomes"])


def test_research_coverage_is_kept_apart_from_source_health():
    """The tab answers one question, how far the search got. The citation block it carries is
    headed as source health and says it is not research coverage; the lane logic never reads the
    citation or source-health blocks."""
    text = COMPONENT.read_text(encoding="utf-8")
    assert text.count("<h2") == 1 and '<h2 id="rc-heading">Research coverage</h2>' in text
    assert "Neither implies the other." in text
    assert 'className="eyebrow rc-sh-head">Source health: the citations behind the published events</h3>' in text
    assert "Not part of research coverage." in text
    # Source health is never drawn inside the lane list or the summary.
    head, _, tail = text.partition('<aside className="rc-source-health"')
    assert tail, "the citation block is no longer set apart"
    before_aside = head.split("return (", 1)[1]
    assert "source_health" not in text and "cq." not in before_aside
    logic = MODULE.read_text(encoding="utf-8")
    assert "source_health" not in logic and "citation_quality" not in logic
    # One colour for every state: no traffic-light classes or colour tokens in the explorer's styles.
    css = (ROOT / "web" / "src" / "styles" / "research.css").read_text(encoding="utf-8")
    for token in ("--green", "--amber", "--red", "research-complete", "research-partial"):
        assert token not in css and token not in text, token


def test_the_tab_mounts_the_explorer():
    view = (ROOT / "web" / "src" / "global" / "CountryView.tsx").read_text(encoding="utf-8")
    assert '{tab === "research" && <ResearchCoverage bundle={bundle} />}' in view
