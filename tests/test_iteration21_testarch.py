"""Iteration 21, test-architecture red team: the shipped frontend, executed.

The iteration-21 features are guarded in pytest mostly by reading their source, because the mutation
campaign has no browser and no node_modules. A source guard pins one spelling: the same broken
behaviour written another way passes it. The red team's mutants that no layer caught, or that only
vitest or Playwright caught, are pinned here by RUNNING the code that ships.

How: each test bundles the module under test straight from web/src with esbuild (found in a
web/node_modules of this checkout, the checkout the campaign was started from, or a parent of
either) and runs the bundle in Node. React components render with react-dom/server; an export
frame draws into a recording canvas, so the test reads the text the PNG would carry. Nothing is
mocked in the code under test: a mutant in compare.ts, groupMap.ts, ResearchCoverage.tsx, ... is a
mutant in what these tests execute.

The browser-level proof of the same rules stays in vitest (web/src/**/*.test.ts) and Playwright
(web/e2e/); this file is the part the campaign can see.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GIT_ROOT = Path(os.environ.get("EDM_GIT_ROOT", ROOT))
SRC = ROOT / "web" / "src"
WEB = ROOT / "web" / "public" / "data"


def _find(rel, names):
    for base in (ROOT, GIT_ROOT):
        for d in (base, *base.parents):
            for name in names:
                p = d / rel / name
                if p.exists():
                    return p
    return None


def _node():
    if os.environ.get("EDM_NODE"):
        return os.environ["EDM_NODE"]
    p = _find("tools/node", ("node.exe", "node"))
    return str(p) if p else shutil.which("node")


NODE = _node()
_ESBUILD = _find("web/node_modules", ("esbuild",))
NODE_MODULES = _ESBUILD.parent if _ESBUILD else None
needs_bundler = pytest.mark.skipif(NODE is None or NODE_MODULES is None,
                                   reason="no Node or no web/node_modules/esbuild to run the shipped TypeScript")
needs_payload = pytest.mark.skipif(not (WEB / "global" / "manifest.json").exists(), reason="no built payload")

# A canvas that records what is drawn, so an export test reads the PNG's text, not the input object.
FAKE_DOM = """
globalThis.__drawn = [];
const ctx2d = () => ({
  font: "16px sans", fillStyle: "#000", strokeStyle: "#000", lineWidth: 1, textAlign: "left", textBaseline: "alphabetic",
  measureText(t) { const m = /(\\d+(?:\\.\\d+)?)px/.exec(this.font); return { width: String(t).length * (m ? Number(m[1]) : 16) * 0.5 }; },
  fillText(t, x, y) { globalThis.__drawn.push({ t: String(t), x, y, fill: this.fillStyle }); },
  fillRect() {}, strokeRect() {}, drawImage() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {}, fill() {},
  save() {}, restore() {}, setLineDash() {}, arc() {}, closePath() {}, rect() {}, clip() {}, translate() {}, scale() {},
});
globalThis.document = { createElement: () => ({ width: 0, height: 0, getContext: () => ctx2d() }) };
"""


_BUNDLES = {}


def _bundle(modules, out_dir):
    """Bundle the shipped `modules` (alias -> path under web/src), React and react-dom/server into
    one ES module, once per module set per session. Each test's own body imports it."""
    if modules in _BUNDLES:
        return _BUNDLES[modules]
    out_dir = Path(out_dir)
    exports = "\n".join(f"export * as {alias} from {json.dumps((SRC / rel).as_posix())};" for alias, rel in modules)
    entry = out_dir / "entry.mjs"
    entry.write_text(
        'export * as React from "react";\n'
        'export { renderToStaticMarkup } from "react-dom/server";\n'
        f"{exports}\n", encoding="utf-8")
    prelude = out_dir / "prelude.mjs"
    prelude.write_text(FAKE_DOM, encoding="utf-8")
    script = f"""
const esbuild = require({json.dumps(str(NODE_MODULES / "esbuild"))});
esbuild.buildSync({{ entryPoints: [{json.dumps(str(entry))}], bundle: true, format: "esm", platform: "node",
  outfile: {json.dumps(str(out_dir / "out.mjs"))}, nodePaths: [{json.dumps(str(NODE_MODULES))}],
  inject: [{json.dumps(str(prelude))}], jsx: "automatic", loader: {{ ".css": "empty" }},
  banner: {{ js: 'import {{ createRequire as __cr }} from "node:module"; const require = __cr(import.meta.url);' }},
  define: {{ "import.meta.env.BASE_URL": '"/"', "import.meta.env.DEV": "false", "import.meta.env.PROD": "true",
            "process.env.NODE_ENV": '"production"' }}, logLevel: "error" }});
"""
    r = subprocess.run([NODE, "-e", script], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-3000:]
    _BUNDLES[modules] = out_dir / "out.mjs"
    return _BUNDLES[modules]


def run_ts(tmp_path_factory, modules, body, payload=None):
    """Run `body` (an async function body that returns JSON) against the shipped modules, which it
    sees under their aliases, with `input` (the payload), `React` and `renderToStaticMarkup`."""
    out_dir = tmp_path_factory.mktemp("ts")
    lib = _bundle(tuple(modules.items()), str(out_dir))
    names = ", ".join(["React", "renderToStaticMarkup", *modules])
    run = out_dir / "run.mjs"
    run.write_text(
        'import { readFileSync } from "node:fs";\n'
        f"import {{ {names} }} from {json.dumps(lib.as_uri())};\n"
        "const input = JSON.parse(readFileSync(0, \"utf-8\"));\n"
        f"const out = await (async () => {{ {body} }})();\n"
        "process.stdout.write(JSON.stringify(out));\n", encoding="utf-8")
    r = subprocess.run([NODE, str(run)], input=json.dumps(payload if payload is not None else {}),
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout)


def _read(rel):
    return json.loads((WEB / rel).read_text(encoding="utf-8"))


def _manifest():
    return _read("global/manifest.json")


def _countries():
    return [s for s in _manifest()["systems"] if s["kind"] == "country"]


def _systems():
    return {s["id"]: _read(f"systems/{s['id']}/system.json") for s in _countries()}


# ---------------- Compare ----------------

COMPARE = {"cmp": "global/compare.ts"}
# Columns as the page builds them: the manifest entry plus the country's own system.json.
COLUMNS_JS = """
const cols = (ids, loaded) => ids.map((id) => {
  const entry = input.manifest.systems.find((s) => s.id === id);
  if (entry.kind === "theatre") return { entry, system: null, status: "theatre" };
  return loaded ? { entry, system: input.systems[id], status: "loaded" } : { entry, system: null, status: "loading" };
});
"""


@needs_bundler
@needs_payload
def test_compare_a_repeated_id_is_one_column(tmp_path_factory):
    out = run_ts(tmp_path_factory, COMPARE, """
      const r = cmp.resolveCompare(["us", "us", "ca", "us"], input.manifest);
      return { cols: r.columns.map((s) => s.id), unknown: r.unknown, over: r.over };
    """, {"manifest": _manifest()})
    assert out == {"cols": ["us", "ca"], "unknown": [], "over": []}


@needs_bundler
@needs_payload
def test_compare_safeguards_follow_the_manifest_flag_for_every_campaign_system(tmp_path_factory):
    """Every system under the campaign rule says Yes, whether or not its own file has loaded, and
    whatever its campaign state: UNCERTAIN counts as active (five Gulf systems are UNCERTAIN)."""
    systems = _systems()
    ids = sorted(systems)
    out = run_ts(tmp_path_factory, COMPARE, COLUMNS_JS + """
      const res = {};
      for (const loaded of [false, true]) {
        const rows = cmp.compareRows(cols(input.ids, loaded), null, input.manifest);
        const row = rows.find((r) => r.id === "safeguards");
        res[loaded ? "loaded" : "loading"] = Object.fromEntries(input.ids.map((id, i) => [id, row.cells[i].text]));
      }
      return res;
    """, {"manifest": _manifest(), "systems": systems, "ids": ids})
    flagged = {s["id"] for s in _countries() if s.get("campaign_restricted")}
    uncertain = {i for i, s in systems.items() if (s.get("campaign_state") or {}).get("state") == "UNCERTAIN"}
    assert flagged and uncertain, "the served data has no campaign or no UNCERTAIN system, so this checks nothing"
    for state in ("loading", "loaded"):
        for sid in ids:
            want = "Yes" if sid in flagged else "No"
            assert out[state][sid] == want, (state, sid, out[state][sid])


@needs_bundler
@needs_payload
def test_compare_caps_at_four_and_names_what_it_left_out(tmp_path_factory):
    out = run_ts(tmp_path_factory, COMPARE, """
      const r = cmp.resolveCompare(["us", "ca", "zz", "cn", "in", "sa"], input.manifest);
      return { cols: r.columns.map((s) => s.id), unknown: r.unknown, over: r.over };
    """, {"manifest": _manifest()})
    names = {s["id"]: s["name"] for s in _manifest()["systems"]}
    assert out == {"cols": ["us", "ca", "cn", "in"], "unknown": ["zz"], "over": [names["sa"]]}


@needs_bundler
@needs_payload
def test_compare_placement_states_each_systems_own_rule(tmp_path_factory):
    """A system whose attack records are kept at country level never reads as 'first-level region'."""
    systems = _systems()
    ids = sorted(systems)
    out = run_ts(tmp_path_factory, COMPARE, COLUMNS_JS + """
      const row = cmp.compareRows(cols(input.ids, true), null, input.manifest).find((r) => r.id === "placement");
      return Object.fromEntries(input.ids.map((id, i) => [id, row.cells[i].text]));
    """, {"manifest": _manifest(), "systems": systems, "ids": ids})
    kinds = {"all": 0, "attacks": 0, "region": 0}
    for sid, s in systems.items():
        pp = s["geography"].get("precision_policy") or {}
        if pp.get("kinetic") == "country" and pp.get("other") == "country":
            assert out[sid] == "Country as a whole, for every record", (sid, out[sid])
            kinds["all"] += 1
        elif pp.get("kinetic") == "country":
            assert out[sid].startswith("Attack records: country as a whole."), (sid, out[sid])
            kinds["attacks"] += 1
        else:
            assert out[sid].startswith("First-level region"), (sid, out[sid])
            kinds["region"] += 1
    assert all(kinds.values()), f"the served data no longer has every placement rule: {kinds}"


@needs_bundler
def test_compare_lane_buckets_never_call_a_blocked_or_stopped_lane_complete(tmp_path_factory):
    out = run_ts(tmp_path_factory, COMPARE, """
      const b = cmp.laneBuckets({ universe_searched: 1, blocked_by_source: 2, stopped_by_search_limit: 3,
                                  partially_searched: 4, not_started: 5, some_older_state: 6 });
      // Each bucket's count, keyed by the build state it holds, so the test does not pin the wording.
      return { n: b.map((x) => x.n), states: cmp.LANE_BUCKETS.map((x) => x.states) };
    """)
    by_state = {tuple(s): n for s, n in zip(out["states"], out["n"])}
    assert by_state[("universe_searched", "current_through_latest_release", "declared_query_set_run")] == 1
    assert by_state[("partially_searched",)] == 4 and by_state[("not_started",)] == 5
    assert by_state[("stopped_by_search_limit",)] == 3 and by_state[("blocked_by_source",)] == 2
    assert len(out["n"]) == 6 and out["n"][5] == 6, "an unknown state is kept under its own label, never dropped"


@needs_bundler
@needs_payload
def test_compare_lane_cells_agree_with_each_served_systems_own_counts(tmp_path_factory):
    systems = _systems()
    ids = sorted(systems)
    out = run_ts(tmp_path_factory, COMPARE, COLUMNS_JS + """
      const row = cmp.compareRows(cols(input.ids, true), null, input.manifest).find((r) => r.id === "lanes");
      const label = (state) => cmp.LANE_BUCKETS.find((b) => b.states.includes(state)).label;
      return { labels: { blocked: label("blocked_by_source"), stopped: label("stopped_by_search_limit"), done: label("universe_searched") },
               cells: Object.fromEntries(input.ids.map((id, i) => [id, row.cells[i].lines ?? []])) };
    """, {"manifest": _manifest(), "systems": systems, "ids": ids})
    lab = out["labels"]
    checked = 0
    for sid, s in systems.items():
        ls = s["research_freshness"].get("lane_states") or {}
        if not ls:
            continue
        words = dict((" ".join(w.split()[1:]), int(w.split()[0])) for w in out["cells"][sid])
        assert words[lab["blocked"]] == ls.get("blocked_by_source", 0), sid
        assert words[lab["stopped"]] == ls.get("stopped_by_search_limit", 0), sid
        assert words[lab["done"]] == s["research_freshness"]["lanes_complete"], sid
        checked += 1
    assert checked > 0


@needs_bundler
@needs_payload
def test_compare_a_failed_file_says_so_and_a_loading_one_says_loading(tmp_path_factory):
    out = run_ts(tmp_path_factory, COMPARE, """
      const entry = (id) => input.manifest.systems.find((s) => s.id === id);
      const rows = cmp.compareRows([{ entry: entry("us"), system: null, status: "loading" },
                                    { entry: entry("ca"), system: null, status: "failed" }], null, input.manifest, true);
      const pick = (id) => rows.find((r) => r.id === id).cells.map((c) => c.kind);
      return { lanes: pick("lanes"), placement: pick("placement"), sourcing: pick("sourcing"), ctx: pick("ctx_total_production") };
    """, {"manifest": _manifest()})
    for row in ("lanes", "placement", "sourcing"):
        assert out[row] == ["loading", "unavailable"], (row, out[row])
    assert out["ctx"] == ["unavailable", "unavailable"]


@needs_bundler
@needs_payload
def test_compare_sourcing_shares_are_never_rounded_to_none_or_all(tmp_path_factory):
    """One record in thirty is 'fewer than 1 in 10', never 'about 0 in 10'; 29 in 30 is never 'all'."""
    sys_ = _systems()["us"]
    sys_["source_health"] = {**sys_["source_health"], "events": 30, "citations": 60, "single_origin_events": 1,
                             "events_with_first_party_source": 29}
    out = run_ts(tmp_path_factory, COMPARE, COLUMNS_JS + """
      const row = cmp.compareRows(cols(["us", "ca"], true), null, input.manifest).find((r) => r.id === "sourcing");
      return row.cells[0].text;
    """, {"manifest": _manifest(), "systems": {"us": sys_, "ca": _systems()["ca"]}})
    assert "fewer than 1 in 10 rest on a single originating statement" in out, out
    assert "more than 9 in 10 cite a first-party source" in out, out


@needs_bundler
@needs_payload
def test_compare_export_rows_are_research_state_and_context_only(tmp_path_factory):
    systems = _systems()
    out = run_ts(tmp_path_factory, {**COMPARE, "ctxm": "global/context.ts"}, COLUMNS_JS + """
      const c = cols(["us", "sa", "ru"], true);
      const b = cmp.compareBriefLines(c, cmp.compareRows(c, input.ctx, input.manifest), input.ctx, input.manifest.build_time);
      return { rows: b.rows.map((r) => r.label.join(" ")), bases: b.rows.map((r) => r.basis), ids: cmp.EXPORT_ROW_IDS };
    """, {"manifest": _manifest(), "systems": systems, "ctx": _read("global/energy_context.json")})
    assert "within" not in out["bases"]
    assert len(out["rows"]) == len(out["ids"]) == 12
    assert not any(w in " ".join(out["rows"]) for w in ("sourced", "Reporting environment", "last checked"))


@needs_bundler
@needs_payload
def test_compare_export_waits_for_every_column_and_a_move_swaps_one_neighbour(tmp_path_factory):
    systems = _systems()
    out = run_ts(tmp_path_factory, COMPARE, COLUMNS_JS + """
      return {
        one: cmp.exportBlocker(cols(["us"], true), true, false),
        loading: cmp.exportBlocker(cols(["us", "ca"], false), true, false),
        noCtx: cmp.exportBlocker(cols(["us", "ca"], true), false, false),
        ctxFailed: cmp.exportBlocker(cols(["us", "ca"], true), false, true),
        ready: cmp.exportBlocker(cols(["us", "ca", "ru"], true), true, false),
        left: cmp.moveColumn(["us", "ca", "sa"], 1, -1), right: cmp.moveColumn(["us", "ca", "sa"], 1, 1),
        edge: cmp.moveColumn(["us", "ca"], 0, -1),
      };
    """, {"manifest": _manifest(), "systems": systems})
    assert "at least two" in out["one"]
    assert "Still loading" in out["loading"] and "Still loading" in out["noCtx"]
    assert out["ctxFailed"] is None and out["ready"] is None
    assert out["left"] == ["ca", "us", "sa"] and out["right"] == ["us", "sa", "ca"] and out["edge"] == ["us", "ca"]


@needs_bundler
def test_every_country_view_gets_its_own_error_boundary_key(tmp_path_factory):
    """Root keys the view boundary per route and per id, so a failed country never carries its
    failure into the next one (resilience.e2e.ts shows it in the browser)."""
    out = run_ts(tmp_path_factory, {"root": "Root.tsx"}, """
      globalThis.window = globalThis.window ?? { location: { search: "" }, addEventListener() {}, removeEventListener() {} };
      const routes = [{ view: "home" }, { view: "theatre" }, { view: "country", id: "kw" }, { view: "country", id: "om" },
                      { view: "group", id: "gulf" }, { view: "compare", ids: ["us"] }];
      return routes.map((r) => root.describe(r).key);
    """)
    assert len(set(out)) == len(out), out


@needs_bundler
@needs_payload
def test_compare_png_draws_every_caveat_and_the_columns_in_the_readers_order(tmp_path_factory):
    """The drawn frame, read back from a recording canvas: what the PNG carries, not its input."""
    systems = _systems()
    out = run_ts(tmp_path_factory, {**COMPARE, "draw": "global/compareExport.ts"}, COLUMNS_JS + """
      const c = cols(["sa", "us", "ca"], true);
      const b = cmp.compareBriefLines(c, cmp.compareRows(c, input.ctx, input.manifest), input.ctx, input.manifest.build_time);
      globalThis.__drawn.length = 0;
      draw.drawCompareFrame(b);
      return { drawn: globalThis.__drawn, foot: b.foot, names: b.names, sub: b.sub, title: b.title };
    """, {"manifest": _manifest(), "systems": systems, "ctx": _read("global/energy_context.json")})
    texts = [d["t"] for d in out["drawn"]]
    assert out["foot"] and len(out["foot"]) >= 4
    for line in out["foot"] + [out["title"], out["sub"]]:
        assert line in texts, f"the PNG does not draw: {line[:80]}"
    assert any(t.startswith("Not comparable") for t in texts)
    xs = [next(d["x"] for d in out["drawn"] if d["t"] == n) for n in out["names"]]
    assert out["names"] == [systems[i]["name"] for i in ("sa", "us", "ca")]
    assert xs == sorted(xs) and len(set(xs)) == 3, f"columns drawn out of the reader's order: {xs}"


# ---------------- Research coverage ----------------

LANES = {"lc": "global/laneCoverage.ts"}
RC = {"rc": "global/ResearchCoverage.tsx", "lc": "global/laneCoverage.ts"}
RENDER_RC_JS = """
const render = (sys, events = []) => renderToStaticMarkup(React.createElement(rc.default, {
  bundle: { system: sys, events, episodes: [], regions: { type: "FeatureCollection", features: [] } } }));
const text = (html) => html.replace(/<[^>]+>/g, " ").replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/\\s+/g, " ");
const history = (html) => text(html.slice(html.indexOf('class="small rc-history"')));
"""
SEEDED = {"candidates": 4817, "held": 3929, "rejected": 5743, "accepted": 6151}


def _campaign_systems():
    return {sid: s for sid, s in _systems().items()
            if any(c.get("policy_applied") for c in s["publication_policy"]["campaigns"])}


@needs_bundler
@needs_payload
def test_research_any_one_campaign_signal_restricts(tmp_path_factory):
    """Restricting more than needed is safe, less is not: each signal alone is enough."""
    base = json.loads(json.dumps(_systems()["us"]))
    base["campaign_state"] = None
    base["publication_policy"]["campaigns"] = []
    for p in base["research_log"]["passes"]:
        p.pop("under_review", None)
    by_state = json.loads(json.dumps(base))
    by_state["campaign_state"] = {"state": "UNCERTAIN"}
    by_policy = json.loads(json.dumps(base))
    by_policy["publication_policy"]["campaigns"] = [{"policy_applied": True}]
    by_review = json.loads(json.dumps(base))
    by_review["research_log"]["passes"][-1]["under_review"] = False
    out = run_ts(tmp_path_factory, LANES, """
      return Object.fromEntries(Object.entries(input).map(([k, s]) => [k, lc.isCampaignRestricted(s)]));
    """, {"none": base, "state": by_state, "policy": by_policy, "review": by_review})
    assert out == {"none": False, "state": True, "policy": True, "review": True}


@needs_bundler
@needs_payload
def test_research_tab_renders_no_count_for_a_campaign_system_whatever_the_log_carries(tmp_path_factory):
    systems = _campaign_systems()
    assert systems, "no system is under the campaign policy, so this checks nothing"
    for s in systems.values():
        for p in s["research_log"]["passes"]:
            p["outcome"] = dict(SEEDED)
    out = run_ts(tmp_path_factory, RC, RENDER_RC_JS + """
      return Object.fromEntries(Object.entries(input).map(([id, s]) => [id, text(render(s))]));
    """, systems)
    for sid, t in out.items():
        for n in SEEDED.values():
            assert str(n) not in t and f"{n:,}" not in t, (sid, n)
        assert "Counts are not published" in t or "under review" in t, sid


@needs_bundler
@needs_payload
def test_research_history_says_remain_under_review_only_on_the_newest_systematic_pass(tmp_path_factory):
    systems = _campaign_systems()
    out = run_ts(tmp_path_factory, RC, RENDER_RC_JS + """
      return Object.fromEntries(Object.entries(input).map(([id, s]) => { const h = render(s); return [id, [history(h), text(h)]]; }));
    """, systems)
    checked = 0
    for sid, s in systems.items():
        hist, full = out[sid]
        out[sid] = hist
        newest = [p for p in s["research_log"]["passes"] if p["kind"] == "systematic"][-1]
        # The summary's review line plus the newest pass's row, or neither.
        assert full.count("Additional candidates remain under review") == (2 if newest.get("under_review") else 0), sid
        newest = [p for p in s["research_log"]["passes"] if p["kind"] == "systematic"][-1]
        older_flagged = sum(1 for p in s["research_log"]["passes"] if p.get("under_review") and p is not newest)
        now = out[sid].count("Additional candidates remain under review")
        assert now == (1 if newest.get("under_review") else 0), (sid, now)
        assert out[sid].count("Candidates were under review when this pass was logged") == older_flagged, sid
        checked += older_flagged
    assert checked > 0, "no older pass is flagged under review, so the tense rule is untested"


@needs_bundler
@needs_payload
def test_research_lanes_come_from_the_newest_systematic_pass_only(tmp_path_factory):
    us = json.loads(json.dumps(_systems()["us"]))
    passes = us["research_log"]["passes"]
    newest = [p for p in passes if p["kind"] == "systematic"][-1]
    lane = dict(newest["lanes"][0])
    # An older systematic pass and a later targeted pass that each say the opposite.
    passes.insert(0, {**newest, "date": "2020-01-01", "lanes": [{**lane, "execution": "not_started"}]})
    passes.append({**newest, "kind": "targeted", "date": "2099-01-01",
                   "lanes": [{**lane, "execution": "not_started"}, {**lane, "lane": "ZZ-TARGETED"}]})
    out = run_ts(tmp_path_factory, LANES, """
      return lc.latestLanes(input.passes).map((r) => ({ lane: r.lane.lane, state: r.state, date: r.pass.date }));
    """, {"passes": passes})
    first = next(r for r in out if r["lane"] == lane["lane"])
    assert first["date"] == newest["date"]
    assert "ZZ-TARGETED" not in [r["lane"] for r in out]


@needs_bundler
def test_research_complete_needs_a_readable_source_and_every_language(tmp_path_factory):
    base = {"lane": "T1", "universe_kind": "declared_query_set", "execution": "declared_search_complete",
            "source_window": "no_census_exists", "languages_required": ["en"], "languages_executed": ["en"]}
    lanes = [base, {**base, "source_window": "unknown"}, {**base, "execution": None},
             {**base, "execution": "not_started", "source_window": "inaccessible"}]
    out = run_ts(tmp_path_factory, LANES, "return input.map((l) => lc.coverageState(l));", lanes)
    assert out == ["complete", "partial", "earlier_format", "unavailable"]


@needs_bundler
@needs_payload
def test_research_summary_names_every_shortfall(tmp_path_factory):
    base = {"lane": "T1", "universe_kind": "declared_query_set", "execution": "declared_search_complete",
            "source_window": "no_census_exists", "languages_required": ["en"], "languages_executed": ["en"]}
    lanes = [base, {**base, "lane": "T2", "source_window": "inaccessible"}, {**base, "lane": "T3", "stopped_by": "search_limit"},
             {**base, "lane": "T4", "execution": "not_started"}]
    out = run_ts(tmp_path_factory, LANES, """
      const rows = lc.latestLanes([{ kind: "systematic", date: "2026-01-01", lanes: input }]);
      return lc.coverageSummary(rows, 1);
    """, lanes)
    import re
    assert re.fullmatch(r"1 of 4 lanes declared complete; 1 stopped by the search \w+; "
                        r"1 with the source unavailable; 1 not started\.", out), out


@needs_bundler
@needs_payload
def test_research_tab_states_what_it_owes_marks_missing_languages_and_lists_no_zeros(tmp_path_factory):
    us = json.loads(json.dumps(_systems()["us"]))
    assert us["research_freshness"]["completeness"] != "complete" and us["research_freshness"].get("next_due")
    newest = [p for p in us["research_log"]["passes"] if p["kind"] == "systematic"][-1]
    newest["lanes"][0]["languages_required"] = ["en", "fa"]
    newest["lanes"][0]["languages_executed"] = ["en"]
    events = _read("systems/us/events.json")["events"]
    out = run_ts(tmp_path_factory, RC, RENDER_RC_JS + """
      return { empty: text(render(input.sys, [])), full: text(render(input.sys, input.events)) };
    """, {"sys": us, "events": events})
    assert "The unfinished lanes are owed now" in out["full"] and "Next full search due" not in out["full"]
    assert "Not run in: Persian" in out["full"]
    assert "Recovery research" not in out["empty"] and "Observed report of recovery" not in out["empty"]
    assert "Recovery research" in out["full"]


# ---------------- Gulf map ----------------

GROUP = {"gm": "global/groupMap.ts", "ge": "global/groupExport.ts"}


def _gulf():
    return _read("global/gulf.json")


@needs_bundler
@needs_payload
def test_gulf_fill_keeps_no_data_zero_filtered_and_geography_apart(tmp_path_factory):
    g = _gulf()
    metric = next(iter(g["metrics"]))
    g["systems"][0]["values"][metric] = None
    g["systems"][1]["values"][metric] = 0
    out = run_ts(tmp_path_factory, GROUP, """
      const colour = (fill, a3) => fill[fill.indexOf(a3) + 1];
      const keep = (s) => s.a3 !== input.g.systems[2].a3;
      const f = gm.groupFill(input.g.systems, input.metric, keep);
      const geo = gm.groupFill(input.g.systems, null, () => true);
      return {
        noData: colour(f, input.g.systems[0].a3), zero: colour(f, input.g.systems[1].a3), filtered: colour(f, input.g.systems[2].a3),
        valued: input.g.systems.slice(3).map((s) => colour(f, s.a3)), geo: input.g.systems.map((s) => colour(geo, s.a3)),
        other: f[f.length - 1], special: gm.specialValues(input.g.systems, input.metric, keep),
        K: { NO_DATA: gm.NO_DATA, ZERO: gm.ZERO, FILTERED: gm.FILTERED, NEUTRAL: gm.NEUTRAL, OTHER: gm.OTHER, RAMP: gm.MEMBER_RAMP },
      };
    """, {"g": g, "metric": metric})
    K = out["K"]
    assert len(out["valued"]) >= 1
    assert (out["noData"], out["zero"], out["filtered"], out["other"]) == (K["NO_DATA"], K["ZERO"], K["FILTERED"], K["OTHER"])
    assert all(c in K["RAMP"] for c in out["valued"])
    assert set(out["geo"]) == {K["NEUTRAL"]}
    assert out["special"] == {"zero": True, "noData": True}


@needs_bundler
@needs_payload
def test_gulf_brief_draws_every_member_in_name_order_with_its_caveats(tmp_path_factory):
    g = _gulf()
    metric = next(iter(g["metrics"]))
    out = run_ts(tmp_path_factory, GROUP, """
      const lines = ge.groupBriefLines(input.g, input.metric);
      globalThis.__drawn.length = 0;
      ge.composeGroupFrame({ width: 1600, height: 900 }, input.g, input.metric);
      return { lines, drawn: globalThis.__drawn.map((d) => d.t) };
    """, {"g": g, "metric": metric})
    rows = out["lines"]["rows"]
    names = [r.split(":")[0] for r in rows]
    assert names == sorted(names) == sorted(s["name"] for s in g["systems"]), names
    drawn = out["drawn"]
    for line in rows + out["lines"]["foot"] + [out["lines"]["title"], out["lines"]["sub"], out["lines"]["key"]]:
        assert line in drawn, f"the brief does not draw: {line[:80]}"
    foot = " ".join(out["lines"]["foot"])
    for must in ("Event counts are not comparable between countries", "No index is published",
                 "no facilities, no routes or shipping, no current status of any facility", "alphabetical order"):
        assert must in foot, must


def _episode(sid, i, withheld):
    return {"system_id": sid, "country": sid.upper(), "episode_id": f"{sid}-row-{i:02d}",
            "first_date": f"2026-0{i}-01", "last_date": f"2026-0{i}-01", "date_precision": "day",
            "classes": ["c"], "causes": ["k"], "records": 1, "episode_name": None,
            "members": [{"date": f"2026-0{i}-01", "region": "National", "withheld": withheld, "effect": None}]}


@needs_bundler
@needs_payload
def test_record_feeds_fold_only_one_countrys_covered_runs_and_drop_nothing(tmp_path_factory):
    """The fold both the home list and the Gulf list use (homeModel.collapseCovered), on made cases
    and on both served lists: every record is still there, alone or inside a run of one country."""
    made = [_episode("aa", 9, True), _episode("aa", 8, True), _episode("bb", 7, True), _episode("bb", 6, True),
            _episode("aa", 5, False), _episode("aa", 4, True)]
    lists = {"gulf": _gulf()["recent"]["episodes"], "home": _read("global/recent_evidence.json")["episodes"]}
    out = run_ts(tmp_path_factory, {"hm": "global/homeModel.ts"}, """
      const shape = (rows) => rows.map((r) => r.kind === "item" ? ["item", r.ep.episode_id] : ["run", r.system_id, r.key]);
      return { made: shape(hm.collapseCovered(input.made)),
               served: Object.fromEntries(Object.entries(input.lists).map(([k, eps]) => [k, shape(hm.collapseCovered(eps))])),
               covered: Object.fromEntries(Object.entries(input.lists).map(([k, eps]) => [k, eps.map((e) => hm.isCovered(e))])) };
    """, {"made": made, "lists": lists})
    assert [r[:2] for r in out["made"]] == [["run", "aa"], ["run", "bb"], ["item", "aa-row-05"], ["item", "aa-row-04"]]
    runs = 0
    for name, eps in lists.items():
        rows, covered = out["served"][name], out["covered"][name]
        assert eps, f"the {name} list is empty, so this checks nothing"
        # Walk the list as the fold does: a run swallows the maximal covered stretch of one country.
        i = 0
        for row in rows:
            if row[0] == "item":
                assert eps[i]["episode_id"] == row[1], (name, i)
                i += 1
                continue
            runs += 1
            j = i
            while j < len(eps) and covered[j] and eps[j]["system_id"] == row[1]:
                j += 1
            assert j - i >= 2, (name, row)
            i = j
        assert i == len(eps), f"{name}: {len(eps) - i} records fell off the list"
    assert runs > 0, "no served list has a covered run, so the fold is untested on served data"


@needs_bundler
def test_gulf_a_lone_covered_record_says_it_is_not_summarised_whatever_the_payload_carries(tmp_path_factory):
    """No served Gulf feed has a covered record on a line of its own (they fold into one run), so
    only a made record reaches this branch: the page's own line of defence if the build ever let an
    effect through."""
    ep = {**_episode("sa", 4, True), "members": [{"date": "2026-04-01", "date_precision": "day", "region": "National",
                                                 "effect": "Refinery back in service at 60%.", "effect_on_country_page": False,
                                                 "withheld": True}]}
    out = run_ts(tmp_path_factory, {"gv": "global/GroupView.tsx"}, """
      return renderToStaticMarkup(React.createElement("ul", null, React.createElement(gv.EpisodeItem, { ep: input })));
    """, ep)
    assert "Not summarised in this list" in out
    assert "back in service" not in out and "60%" not in out and "no effect text" not in out


def test_gulf_view_never_turns_a_missing_figure_into_zero():
    """Structural, for the campaign: the behaviour is proven in Playwright (gulf.e2e.ts, "a missing
    national value is words"), which removes one value in the browser and reads the table and the
    selected member's line. No served Gulf value is null today, so only that injected case reaches it."""
    import re
    checked = 0
    for rel in ("global/GroupView.tsx", "global/groupMap.ts", "global/groupExport.ts"):
        text = re.sub(r"/\*.*?\*/", " ", (SRC / rel).read_text(encoding="utf-8"), flags=re.S)
        code = re.sub(r"(^|\s)//.*$", " ", text, flags=re.M)
        assert not re.search(r"\?\?\s*0\b|\|\|\s*0\b", code), f"{rel} turns a missing value into zero"
        checked += 1
    assert checked == 3


def test_gulf_brief_refuses_an_uncoloured_map():
    """Structural, for the campaign; proven in Playwright (gulf.e2e.ts, "a brief needs a chosen figure")."""
    import re
    view = (SRC / "global" / "GroupView.tsx").read_text(encoding="utf-8")
    run = re.search(r"const runExport = async \(\) => \{.*?\n  \};", view, re.S).group(0)
    guard = run.index("if (!colourBy) { setExportMsg(")
    assert guard < run.index("exportMapPng("), "the brief is drawn before the uncoloured map is refused"


# ---------------- Performance and containment ----------------

LOADERS = {"mf": "global/manifest.ts", "cx": "global/context.ts", "si": "global/searchIndex.ts", "pf": "global/prefetch.ts"}
# A fetch that serves the built files from the payload (`input.files`), counts every request, and
# fails the first `input.failFirst[path]` requests for a path.
FETCH_JS = """
const calls = [];
const fails = { ...(input.failFirst ?? {}) };
globalThis.fetch = async (url) => {
  const path = String(url).replace(/^.*?data\\//, "");
  calls.push(path);
  if (fails[path] > 0) { fails[path] -= 1; return { ok: false, status: 503, json: async () => null }; }
  if (!(path in input.files)) return { ok: false, status: 404, json: async () => null };
  return { ok: true, status: 200, json: async () => structuredClone(input.files[path]) };
};
const settle = async (p) => { try { await p; return "ok"; } catch (e) { return "failed"; } };
const tick = () => new Promise((r) => setTimeout(r, 30));
"""


@needs_bundler
@needs_payload
def test_loaders_keep_a_success_and_retry_a_failure(tmp_path_factory):
    files = {"global/manifest.json": _manifest(), "global/energy_context.json": _read("global/energy_context.json"),
             "regions.json": _read("regions.json")}
    out = run_ts(tmp_path_factory, LOADERS, FETCH_JS + """
      const r = {};
      for (const [name, load, path] of [["manifest", mf.loadManifest, "global/manifest.json"],
                                        ["context", cx.loadContext, "global/energy_context.json"],
                                        ["regions", si.loadTheatreRegions, "regions.json"]]) {
        const first = await settle(load());
        const second = await settle(load());
        const third = await settle(load());
        r[name] = { results: [first, second, third], requests: calls.filter((c) => c === path).length };
      }
      return r;
    """, {"files": files, "failFirst": {"global/manifest.json": 1, "global/energy_context.json": 1, "regions.json": 1}})
    for name, r in out.items():
        # A failure is retried by the next caller; a success is kept and never fetched again.
        assert r == {"results": ["failed", "ok", "ok"], "requests": 2}, (name, r)


@needs_bundler
@needs_payload
def test_a_country_route_prefetches_that_country_alone(tmp_path_factory):
    m = _manifest()
    files = {"global/manifest.json": m}
    for s in _countries():
        root = s["root"].split("data/", 1)[-1]
        for f in ("system.json", "events.json", "regions.geojson"):
            files[f"{root}/{f}"] = {}
    out = run_ts(tmp_path_factory, LOADERS, FETCH_JS + """
      pf.prefetchRoute({ view: "country", id: "kw" });
      for (let i = 0; i < 10; i++) await tick();
      return calls;
    """, {"files": files})
    systems = sorted({c.split("/")[1] for c in out if c.startswith("systems/")})
    assert systems == ["kw"], out


@needs_bundler
@needs_payload
def test_a_malformed_system_file_is_refused_and_a_malformed_manifest_part_dropped(tmp_path_factory):
    m = json.loads(json.dumps(_manifest()))
    m["corpus"] = "corrupt"
    m["systems"][0]["aliases"] = 7
    m["systems"][0]["bounds"] = ["x"]
    kw = next(s for s in m["systems"] if s["id"] == "kw")
    root = kw["root"].split("data/", 1)[-1]
    bad = {**_systems()["kw"], "source_health": "corrupt"}
    out = run_ts(tmp_path_factory, LOADERS, FETCH_JS + """
      const man = await mf.loadManifest();
      const kw = man.systems.find((s) => s.id === "kw");
      return { corpus: "corpus" in man, aliases: "aliases" in man.systems[0], bounds: "bounds" in man.systems[0],
               system: await settle(mf.loadCountrySystem(kw)) };
    """, {"files": {"global/manifest.json": m, f"{root}/system.json": bad}})
    assert out == {"corpus": False, "aliases": False, "bounds": False, "system": "failed"}


@needs_bundler
def test_boundaries_replace_a_failed_view_or_panel_and_say_why(tmp_path_factory):
    """The boundary classes driven as React drives them after a throw: derive the state from the
    error, then render. (Server rendering has no error boundaries, so the class is called directly;
    the in-browser proof is resilience.e2e.ts.)"""
    out = run_ts(tmp_path_factory, {"vb": "components/ViewBoundary.tsx"}, """
      globalThis.window = { location: { search: input.search } };
      const child = React.createElement("p", null, "CHILD CONTENT");
      const draw = (Cls, props, err) => {
        const b = new Cls({ ...props, children: child });
        b.state = Cls.getDerivedStateFromError(err);
        return renderToStaticMarkup(b.render());
      };
      const ok = (Cls, props) => { const b = new Cls({ ...props, children: child }); return renderToStaticMarkup(b.render()); };
      const view = { label: "This country's page", cleanHref: "?sys=kw" };
      return {
        panel: draw(vb.PanelBoundary, { label: "Recent evidence" }, new Error("boom")),
        panelOk: ok(vb.PanelBoundary, { label: "Recent evidence" }),
        chunk: draw(vb.ViewBoundary, view, new TypeError("Failed to fetch dynamically imported module: /assets/CountryView.js")),
        drawn: draw(vb.ViewBoundary, view, new Error("x is undefined")),
      };
    """, {"search": "?sys=kw&r=KW-KU"})
    assert "CHILD CONTENT" in out["panelOk"]
    assert "CHILD CONTENT" not in out["panel"] and "Recent evidence could not be shown" in out["panel"]
    assert "could not be downloaded" in out["chunk"] and "failed while it was being drawn" not in out["chunk"]
    assert "failed while it was being drawn" in out["drawn"]
    for html in (out["chunk"], out["drawn"]):
        assert "CHILD CONTENT" not in html and "Return to the overview" in html
        assert "Open this view without it" in html, "a deep link's saved state is offered a clean way back"


# ---------------- Home ----------------

HOME ={"hm": "global/homeModel.ts", "si": "global/searchIndex.ts", "sn": "global/searchNormalize.ts"}


def _member(region, withheld):
    return {"date": "2026-01-01", "date_precision": "day", "region": region, "effect": None,
            "effect_on_country_page": False, "withheld": withheld}


@needs_bundler
def test_home_covered_is_read_from_withheld_members_never_from_the_row_key(tmp_path_factory):
    """A withheld member makes a record "National" with no region name, whatever its id. A row key
    alone does not: the Gulf list keys every row, so a key would label a grid fault a campaign record."""
    keyed_fault = {**_episode("kw", 3, False), "members": [_member("Al Ahmadi", False)]}
    keyless_withheld = {**_episode("sa", 2, True), "episode_id": "sa-2026-02-01-ras-tanura-refinery-shutdown",
                        "members": [_member("Eastern Province", True)]}
    plain = {**_episode("us", 1, False), "episode_id": "us-2026-01-01-x", "members": [_member("Texas", False)]}
    out = run_ts(tmp_path_factory, HOME, """
      return input.map((ep) => ({ covered: hm.isCovered(ep), place: hm.placementOf(ep) }));
    """, [keyed_fault, keyless_withheld, plain])
    assert [o["covered"] for o in out] == [False, True, False]
    assert out[1]["place"] == {"level": "National", "names": []}
    assert out[0]["place"] == {"level": "First-level region", "names": ["Al Ahmadi"]}
    assert out[2]["place"] == {"level": "First-level region", "names": ["Texas"]}


@needs_bundler
@needs_payload
def test_home_feed_runs_never_cross_countries_and_served_covered_items_name_no_place(tmp_path_factory):
    made = [_episode("aa", 9, True), _episode("aa", 8, True), _episode("bb", 7, True), _episode("bb", 6, True)]
    eps = _read("global/recent_evidence.json")["episodes"]
    out = run_ts(tmp_path_factory, HOME, """
      const rows = hm.collapseCovered(input.made).map((r) => r.kind === "item" ? ["item", r.ep.episode_id] : ["run", r.system_id]);
      const served = input.eps.filter((e) => hm.isCovered(e)).map((e) => hm.placementOf(e));
      return { rows, served };
    """, {"made": made, "eps": eps})
    assert out["rows"] == [["run", "aa"], ["run", "bb"]]
    assert out["served"] and all(p == {"level": "National", "names": []} for p in out["served"])


@needs_bundler
def test_home_dates_and_record_lines_never_invent_a_figure(tmp_path_factory):
    out = run_ts(tmp_path_factory, HOME, """
      return { future: hm.ageText("2026-11-20", "2026-11-12"), today: hm.ageText("2026-11-12", "2026-11-12"),
               none: hm.recordLine(null, "2026-11-12"), old: hm.recordLine(undefined, "2026-11-12") };
    """)
    assert out == {"future": "", "today": "today", "none": "No qualifying records yet", "old": None}


@needs_bundler
@needs_payload
def test_home_search_folds_keyboard_variants_ranks_by_match_and_never_calls_crimea_russian(tmp_path_factory):
    regions = _read("regions.json")
    out = run_ts(tmp_path_factory, HOME, """
      const fold = ["\\u0627\\u06cc\\u0631\\u0627\\u0646", "\\u0627\\u064a\\u0631\\u0627\\u0646"].map(sn.normalizeForSearch);
      const entries = [
        si.makeEntry({ key: "a", kind: "system", label: "Iranian grid", sub: "", terms: ["Iranian grid"], action: { type: "system", id: "x" } }),
        si.makeEntry({ key: "b", kind: "concept", label: "Iran", sub: "", terms: ["Iran"], action: { type: "concept", id: "y" } }),
      ];
      const order = si.searchEntries(entries, "iran").map((h) => h.entry.key);
      const regions = si.theatreRegionEntries(input.regions, "Russia, Belarus & Crimea").map((e) => [e.key, e.sub]);
      return { fold, order, regions };
    """, {"regions": regions})
    assert out["fold"][0] == out["fold"][1]
    assert out["order"] == ["b", "a"], "an exact match outranks a better kind"
    ua = [sub for key, sub in out["regions"] if key.startswith("region:ru:UA")]
    assert ua, "Crimea is not in the served region list"
    assert all(s.startswith("Occupied unit, internationally Ukrainian") for s in ua), ua


# ---------------- Country: evidence ----------------

EVIDENCE = {"ev": "global/evidence.ts"}


def _events(sid):
    return _read(f"systems/{sid}/events.json")["events"]


@needs_bundler
@needs_payload
def test_country_no_anchor_from_a_named_campaign_id_and_no_headline_on_a_country_attack(tmp_path_factory):
    systems = _systems()
    sa = _events("sa")
    kw = systems["kw"]
    assert kw["geography"]["precision_policy"]["kinetic"] == "country"
    base = dict(_events("kw")[0])
    attack = {**base, "cause": "kinetic_strike", "publication": None, "asset_class": "oil_refinery",
              "event_id": f"kw-{base['date']}-oil-refinery-attack-a1", "geography_precision": "country", "region_code": None}
    lookalike = {**attack, "event_id": f"kw-{base['date']}-oil-refinery-attack-ras-tanura", "publication": {"campaign": "x"}}
    opaque_covered = {**attack, "publication": {"campaign": "x"}}
    out = run_ts(tmp_path_factory, EVIDENCE, """
      const sa = input.sa.map((e) => ({ anchor: ev.eventAnchor(e, "sa"), headline: ev.headlinesAllowed(e, input.sys.sa) }));
      return { sa,
        attack: { kind: ev.placementKind(input.attack, input.sys.kw), headline: ev.headlinesAllowed(input.attack, input.sys.kw),
                  anchor: ev.eventAnchor(input.attack, "kw") },
        lookalike: ev.eventAnchor(input.lookalike, "kw"), opaque: ev.eventAnchor(input.opaque, "kw"),
        foreign: ev.eventAnchor(input.opaque, "sa") };
    """, {"sa": sa, "sys": {"sa": systems["sa"], "kw": kw}, "attack": attack, "lookalike": lookalike, "opaque": opaque_covered})
    covered = [x for e, x in zip(sa, out["sa"]) if e.get("publication")]
    assert covered, "Saudi Arabia has no campaign-covered record, so this checks nothing"
    assert all(x["anchor"] is None and x["headline"] is False for x in covered)
    assert out["attack"] == {"kind": "country_attack", "headline": False, "anchor": f"ev-{attack['event_id']}"}
    assert out["lookalike"] is None and out["foreign"] is None
    assert out["opaque"] == f"ev-{attack['event_id']}"


@needs_bundler
@needs_payload
def test_country_what_a_record_does_not_establish_keeps_its_uncertainty(tmp_path_factory):
    sa = [e for e in _events("sa") if e.get("publication") and (e.get("capacity_affected") or {}).get("value")]
    assert sa, "no covered record carries a figure, so this checks nothing"
    cap = {"value": 1000, "value_min": None, "value_max": None, "qualifier": "at_least", "measure": "affected", "unit": "MW",
           "source_says": "x"}
    out = run_ts(tmp_path_factory, EVIDENCE, """
      return {
        covered: input.sa.map((e) => ev.notEstablished(e).join(" ")),
        atLeast: ev.capacityFigure(input.cap),
        none: ev.recoveryNotEstablished({ recovery: { research_status: "RESEARCHED_NO_PUBLIC_EVIDENCE" } }),
        wiki: ev.originSummary({ sources: [{ url: "https://en.wikipedia.org/wiki/X", publisher: "Wikipedia" }] }).discoveryOnly,
      };
    """, {"sa": sa, "cap": cap})
    for e, text in zip(sa, out["covered"]):
        v = e["capacity_affected"]["value"]
        assert f"{v:,}" not in text and str(v) not in text, (e["event_id"], text)
    assert out["atLeast"] == "at least 1,000 MW"
    assert "not a finding that it did not" in out["none"]
    assert out["wiki"] is True


@needs_bundler
@needs_payload
def test_country_inspector_says_not_link_checked_where_no_check_was_recorded(tmp_path_factory):
    us = _systems()["us"]
    events = _events("us")
    e = json.loads(json.dumps(next(x for x in events if len(x["sources"]) >= 1)))
    e["sources"] = [{**e["sources"][0], "url": "https://checked.example/a", "link_check": "dead"},
                    {**e["sources"][0], "url": "https://unchecked.example/b"}]
    e["sources"][1].pop("link_check", None)
    out = run_ts(tmp_path_factory, {"ec": "global/EventCard.tsx"}, """
      const bundle = { system: input.sys, events: [input.e], episodes: [], regions: { type: "FeatureCollection", features: [] } };
      return renderToStaticMarkup(React.createElement(ec.EvidenceInspector, { id: "x", e: input.e, bundle, onClose() {} }))
        .replace(/<[^>]+>/g, " ").replace(/\\s+/g, " ");
    """, {"sys": us, "e": e})
    assert "gone at the last automated check" in out
    assert "not link-checked" in out
    assert out.count("reachable at the last automated check") == 0, "an unchecked citation reads as reachable"


@needs_bundler
@needs_payload
def test_country_empty_page_states_the_safeguards_of_every_campaign_state(tmp_path_factory):
    """Every empty country page under an attack-campaign state, UNCERTAIN included, says what is not
    published; none prints a zero."""
    systems = {sid: s for sid, s in _systems().items() if not _events(sid)}
    campaign = {sid for sid, s in systems.items() if (s.get("campaign_state") or {}).get("state") not in (None, "NO_ACTIVE_CAMPAIGN")}
    assert any(systems[s]["campaign_state"]["state"] == "UNCERTAIN" for s in campaign), "no empty UNCERTAIN system to check"
    out = run_ts(tmp_path_factory, {"ec": "global/EmptyCorpus.tsx"}, """
      globalThis.window = globalThis.window ?? { location: { search: "" } };
      const r = {};
      for (const [id, sys] of Object.entries(input.systems)) {
        const bundle = { system: sys, events: [], episodes: [], regions: { type: "FeatureCollection", features: [] } };
        r[id] = renderToStaticMarkup(React.createElement(ec.EmptyCorpus, { bundle, ctx: null, onTab() {} })).replace(/<[^>]+>/g, " ");
      }
      return r;
    """, {"systems": systems})
    for sid, text in out.items():
        if sid in campaign:
            assert "is not published" in text, sid
        assert not __import__("re").search(r"\b0 (records|events|disruptions)\b", text), sid


def test_country_link_states_are_attached_only_where_a_known_state_was_recorded():
    """The build step itself, not the served file it produced: an unchecked citation carries no
    field (read as "not link-checked"), and nothing but one of the five states leaves the local file."""
    from pipeline import build_systems as B
    events = [{"sources": [{"url": "https://a.example/1"}, {"url": "https://b.example/2"}, {"url": "https://c.example/3"},
                           {"url": "https://d.example/4"}]}]
    states = {"https://a.example/1": "dead", "https://b.example/2": "https://elsewhere.example/moved",
              "https://c.example/3": None}
    B.attach_link_states(events, states)
    got = [s.get("link_check", "absent") for s in events[0]["sources"]]
    assert got == ["dead", "absent", "absent", "absent"]


# ---------------- Russia theatre ----------------

THEATRE = {"ui": "components/ui.tsx", "tm": "theatreMode.ts"}


@needs_bundler
@needs_payload
def test_theatre_withheld_rows_render_nothing_but_status_withheld(tmp_path_factory):
    snap = _read("snapshot.json")
    withheld = [d["recovery"] for d in snap["live_disruptions"] if d["recovery"].get("publication_note")]
    assert withheld, "no record carries a publication note, so this checks nothing"
    absent = {k: v for k, v in withheld[0].items() if k != "recovery_status"}
    released = dict(next(r for r in withheld if r.get("recovery_status") == "partial_restart"))
    released.update(impairment_age_days=4321, reconstitution_horizon_days=8765, scoring_evidence_kind="modelled", estimate_days=None)
    plain = {**withheld[0], "publication_note": None, "resolved": False, "recovery_status": "impaired"}
    out = run_ts(tmp_path_factory, THEATRE, """
      const html = (r) => renderToStaticMarkup(React.createElement(ui.RecoveryLine, { r }));
      return { rows: input.withheld.map((r) => [ui.statusWithheld(r), html(r)]), absent: [ui.statusWithheld(input.absent), html(input.absent)],
               released: html(input.released), plain: ui.statusWithheld(input.plain),
               modes: [tm.modeOf(false, false), tm.modeOf(true, false), tm.modeOf(true, true), tm.modeOf(false, true)] };
    """, {"withheld": withheld, "absent": absent, "released": released, "plain": plain})
    for (is_withheld, html), r in zip(out["rows"] + [out["absent"]], withheld + [absent]):
        if r.get("recovery_status") in (None, "impaired", "unknown") and not r.get("resolved"):
            assert is_withheld, r
            assert "Status withheld" in html and r["publication_note"] in html
            assert "impaired " not in html and "modelled horizon" not in html and "evidence-chip" not in html
    assert out["plain"] is False, "a record without a note is not withheld"
    assert "4321" not in out["released"] and "8765" not in out["released"], "a released record shows the facility now"
    assert out["modes"] == ["analyze", "focus", "brief", "brief"]


# ---------------- What's new (reader text) ----------------

WNT = {"wn": "global/whatsNewText.ts"}


@needs_bundler
def test_whats_new_text_keeps_backfill_method_and_clock_distinctions(tmp_path_factory):
    out = run_ts(tmp_path_factory, WNT, """
      const added = (predates) => wn.changeSummary({ category: "records_added", notes: [], event_dates: ["2022-03-01", "2024-05-01"],
                                                     all_predate_previous_build: predates });
      const ix = (separable) => wn.indexText({ index: { label: "ESDI", before: 6.8, after: 6.69, separable } });
      return { back: added(true), fresh: added(false), sep: ix(true), mixed: ix(false),
               future: wn.buildAgeText("2026-11-20", "2026-11-12"), today: wn.buildAgeText("2026-11-12", "2026-11-12") };
    """)
    assert "the record catching up, not new disruption" in out["back"] and "catching up" not in out["fresh"]
    assert "Found by research" in out["fresh"]
    assert "method changed" not in out["sep"] and "method changed" in out["mixed"]
    assert out["future"] == "dated after today on your device's clock" and out["today"].startswith("built today")


@needs_bundler
@needs_payload
def test_whats_new_panel_never_shows_unknown_as_unchanged_or_nothing_changed(tmp_path_factory):
    served = _read("global/whats_new.json")
    data = json.loads(json.dumps(served))
    data["available"] = True
    data["comparison"] = {"previous_as_of": "2026-11-11", "current_as_of": "2026-11-12", "mode": "production", "basis": "b"}
    data["systems"] = [{"system_id": "ru", "name": "Russia, Belarus & Crimea", "kind": "theatre", "changes": [],
                        "unavailable": "the previous build's theatre records could not be read"}]
    data["unchanged"] = [{"system_id": "us", "name": "United States"}]
    none = {**data, "available": False, "unavailable_reason": "no baseline", "systems": [], "global": [], "unchanged": []}
    out = run_ts(tmp_path_factory, {"wp": "global/WhatsNew.tsx"}, """
      globalThis.window = { location: { search: "" }, history: { pushState() {}, replaceState() {} }, addEventListener() {} };
      const html = (d) => renderToStaticMarkup(React.createElement(wp.WhatsNewPanel, { data: d, failed: false, now: new Date("2026-11-12T12:00:00Z") }));
      return { one: html(input.data), none: html(input.none) };
    """, {"data": data, "none": none})
    ru = out["one"][out["one"].index('data-system="ru"'):]
    assert "could not be compared" in ru and "not the same as unchanged" in ru
    assert "Russia" not in out["one"][out["one"].find("wn-unchanged"):], "an uncompared system is listed as unchanged"
    assert "That is not the same as nothing having changed." in out["none"]
    assert "Nothing changed" not in out["none"]


# ---------------- What's new (pipeline) ----------------

def _wn():
    from tests import test_whats_new as T
    return T


def test_whats_new_restriction_is_read_from_either_build_and_from_any_covered_record():
    """A covered record alone restricts a system, and a system leaving the rule stays restricted for
    the comparison that spans the change, so nothing the rule covered is itemised on the way out."""
    from pipeline import whats_new as W
    T = _wn()
    quiet_sys = T._system("om")
    covered = T._state(om=(quiet_sys, [T._event("om-1", "2026-03-01", publication=T.COVERED)]))
    plain = T._state(om=(T._system("om"), [T._event("om-1", "2026-03-01")]))
    assert W.restricted(covered["systems"]["om"], covered["systems"]["om"]) is True
    leaving_prev = T._state(om=(T._system("om", campaign=T.ACTIVE), [T._event("om-1", "2026-03-01"), T._event("om-2", "2026-03-05")]))
    leaving_curr = T._bump(T._state(om=(T._system("om"), [T._event("om-2", "2026-03-05")])))
    assert W.restricted(leaving_prev["systems"]["om"], leaving_curr["systems"]["om"]) is True
    assert W.restricted(plain["systems"]["om"], plain["systems"]["om"]) is False
    w = T._cat(T._changes(W.derive(leaving_prev, leaving_curr, T.QUIET, T.CMP), "om"), "records_withdrawn")
    assert w["aggregated"] is True and "items" not in w


def test_whats_new_order_is_by_name_however_much_each_system_changed():
    from pipeline import whats_new as W
    T = _wn()
    prev = T._state(us=(T._system("us"), []), bh=(T._system("bh"), []), cn=(T._system("cn"), []))
    curr = T._bump(prev)
    us = curr["systems"]["us"]["system"]
    curr["systems"]["us"]["events"]["events"] = [T._event("us-1", "2022-01-01")]
    us["research_gaps"] = ["new gap"]
    us["citation_quality"] = {"link_check_date": "2026-11-12"}
    us["reporting_environment"] = "official_and_media"
    curr["systems"]["cn"]["system"]["research_gaps"] = ["new gap"]
    rows = W.derive(prev, curr, T.QUIET, T.CMP)["systems"]
    assert [len(r["changes"]) for r in rows if r["system_id"] == "us"][0] >= 3
    assert [r["name"] for r in rows] == ["China", "United States"]


def test_whats_new_a_campaign_systems_hidden_fields_never_surface_as_a_wording_change():
    from pipeline import whats_new as W
    T = _wn()
    prev = T._state(qa=(T._system("qa", campaign=T.ACTIVE, recovery_coverage={"observed": 0}),
                        [T._event("qa-1", "2026-03-01", publication=T.COVERED)]))
    curr = T._bump(prev)
    curr["systems"]["qa"]["system"]["recovery_coverage"] = {"observed": 1}
    curr["systems"]["qa"]["system"]["event_summary"] = {"withheld": 3}
    d = W.derive(prev, curr, T.QUIET, T.CMP)
    assert T._changes(d, "qa") == [] and "qa" in [u["system_id"] for u in d["unchanged"]]


def test_whats_new_refuses_a_baseline_on_a_diverged_history(tmp_path, monkeypatch):
    import subprocess
    from pipeline import lineage
    monkeypatch.delenv("PRODUCTION_REF", raising=False)
    run = lambda *a: subprocess.run(["git", *a], cwd=tmp_path, capture_output=True, check=True)  # noqa: E731
    run("init", "-q", "-b", "main")
    run("config", "user.email", "t@example.org")
    run("config", "user.name", "T")
    data = tmp_path / "web" / "public" / "data"
    data.mkdir(parents=True)
    (data / "snapshot.json").write_text(json.dumps({"as_of": "2026-11-10"}), encoding="utf-8")
    run("add", "-A")
    run("commit", "-qm", "main build")
    run("checkout", "-q", "--orphan", "elsewhere")
    (data / "snapshot.json").write_text(json.dumps({"as_of": "2026-11-11"}), encoding="utf-8")
    run("add", "-A")
    run("commit", "-qm", "unrelated history")
    sha, meta = lineage.previous_dated_build(tmp_path, "2026-11-12")
    assert sha is None and "not an ancestor" in meta["reason"]

