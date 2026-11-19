"""Iteration 22: what a map says while it loads, and the theatre's line network, executed as shipped.

Every map used to sit blank for two to three seconds. The words that now fill the map box come from
one reducer (web/src/mapLoad.ts) that only real load events drive: there is no timer in it. These
tests bundle the shipped TypeScript with esbuild and run it in Node (the pattern of
tests/test_iteration21_testarch.py), so the mutation campaign breaks the code the browser runs.

The theatre's loader (web/src/data.ts) is run the same way against a stand-in `fetch` whose answer
for the 2.4 MB line file is held open: the dashboard's bundle must resolve while that file is still
in flight. The browser-level proof, with a real held request, is web/e2e/maploading.e2e.ts.
"""
import re

import pytest

from tests.test_iteration21_testarch import SRC, needs_bundler, run_ts

LOAD = {"ml": "mapLoad.ts"}
INDICATOR = {"ml": "mapLoad.ts", "ind": "components/MapLoadIndicator.tsx"}
DATA = {"data": "data.ts"}

RUN = """
const run = (events) => {
  let s = ml.MAP_LOAD_INITIAL;
  const said = [ml.mapLoadMessage(s)];
  for (const e of events) { s = ml.mapLoadReducer(s, e); said.push(ml.mapLoadMessage(s)); }
  return { said, phase: ml.mapLoadPhase(s), retry: ml.mapLoadCanRetry(s), error: s.error };
};
"""
LINES = {"id": "lines", "label": "network lines"}


@needs_bundler
def test_map_loading_says_geometry_then_data_then_nothing(tmp_path_factory):
    out = run_ts(tmp_path_factory, LOAD, RUN + "return run(input);",
                 [{"type": "geometry_loaded"}, {"type": "idle"}, {"type": "idle"}])
    assert out["said"] == ["Loading map geometry…", "Loading data…", None, None]
    assert out["phase"] == "ready" and out["retry"] is False


@needs_bundler
def test_map_loading_waits_for_the_callers_own_data_file_over_a_drawn_map(tmp_path_factory):
    out = run_ts(tmp_path_factory, LOAD, RUN + "return run(input);",
                 [{"type": "data_pending", "pending": True}, {"type": "geometry_loaded"}, {"type": "idle"},
                  {"type": "data_pending", "pending": False}])
    assert out["said"] == ["Loading map geometry…", "Loading map geometry…", "Loading data…", "Loading data…", None]


@needs_bundler
def test_map_loading_names_a_late_file_until_it_arrives_and_says_when_it_fails(tmp_path_factory):
    out = run_ts(tmp_path_factory, LOAD, RUN + """
      return { arrives: run([input.idle, input.req, input.arrived]),
               fails: run([input.idle, input.req, input.failed]),
               early: run([input.req, { type: "geometry_loaded" }]) };
    """, {"idle": {"type": "idle"}, "req": {"type": "late_requested", **LINES},
          "arrived": {"type": "late_arrived", "id": "lines"}, "failed": {"type": "late_failed", **LINES}})
    assert out["arrives"]["said"] == ["Loading map geometry…", None, "Loading network lines…", None]
    assert out["fails"]["said"][-1] == "Network lines could not be loaded. The rest of the map is complete."
    assert out["fails"]["phase"] == "late_failed" and out["fails"]["retry"] is True
    # A late file never hides that the map itself is still loading.
    assert out["early"]["said"][-1] == "Loading data…"


@needs_bundler
def test_map_loading_a_failure_is_an_error_with_a_retry_but_never_covers_a_drawn_map(tmp_path_factory):
    out = run_ts(tmp_path_factory, LOAD, RUN + """
      return { before: run([{ type: "failed", message: "no WebGL" }]),
               after: run([{ type: "geometry_loaded" }, { type: "idle" }, { type: "failed", message: "one layer" }]),
               recovered: run([{ type: "failed", message: "x" }, { type: "idle" }]),
               retried: run([{ type: "failed", message: "x" }, { type: "retry" }]) };
    """)
    assert out["before"]["said"][-1] == "The map could not be drawn."
    assert out["before"]["phase"] == "failed" and out["before"]["retry"] is True and out["before"]["error"] == "no WebGL"
    assert out["after"]["phase"] == "ready" and out["after"]["said"][-1] is None, "an error covered a map that was drawn"
    assert out["recovered"]["phase"] == "ready"
    assert out["retried"]["phase"] == "geometry" and out["retried"]["error"] is None


def _text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html)).strip()


@needs_bundler
def test_map_indicator_is_a_polite_live_region_with_a_retry_and_the_alternative_on_failure(tmp_path_factory):
    out = run_ts(tmp_path_factory, INDICATOR, """
      const at = (events) => events.reduce(ml.mapLoadReducer, ml.MAP_LOAD_INITIAL);
      const html = (s) => renderToStaticMarkup(React.createElement(ind.MapLoadIndicator,
        { state: s, onRetry() {}, alternative: "The table below has the same data." }));
      return { loading: html(at([])), data: html(at([{ type: "geometry_loaded" }])), ready: html(at([{ type: "idle" }])),
               failed: html(at([{ type: "failed", message: "x" }])),
               waiting: renderToStaticMarkup(React.createElement(ind.MapGeometryPlaceholder, { failed: false })),
               unavailable: renderToStaticMarkup(React.createElement(ind.MapGeometryPlaceholder,
                 { failed: true, onRetry() {}, alternative: "The table below has every figure." })) };
    """)
    for key in ("loading", "data", "ready", "failed", "waiting", "unavailable"):
        assert 'role="status"' in out[key], f"{key}: the map box has no polite live region"
    assert _text(out["loading"]) == "Loading map geometry…"
    assert _text(out["data"]) == "Loading data…"
    assert _text(out["ready"]) == "" and "<button" not in out["ready"], "a drawn map still says something"
    assert _text(out["failed"]) == "The map could not be drawn. The table below has the same data.Try again"
    assert re.search(r"<button[^>]*>Try again</button>", out["failed"])
    assert _text(out["waiting"]) == "Loading map geometry…" and "<button" not in out["waiting"]
    assert _text(out["unavailable"]) == "Map unavailable. The table below has every figure.Try again"


# ---------------- the theatre's line network ----------------

# A stand-in fetch: every file answers at once except the line file, which stays in flight until
# the test releases it (or fails when told to). Nothing in the code under test is replaced.
FETCH = """
const requested = [];
let releaseLines;
let failLines = false;
globalThis.fetch = (url) => {
  const name = String(url).replace(/^.*\\/data\\//, "");
  requested.push(name);
  const body = name === "snapshot.json" ? { schema_version: 2 } : name.endsWith(".geojson") ? { type: "FeatureCollection", features: [] } : {};
  const ok = { ok: true, status: 200, json: async () => body };
  if (name !== "assets_lines.geojson") return Promise.resolve(ok);
  if (failLines) return Promise.resolve({ ok: false, status: 503, json: async () => ({}) });
  return new Promise((resolve) => { releaseLines = () => resolve({ ok: true, status: 200, json: async () => ({ type: "FeatureCollection", features: [{ type: "Feature" }] }) }); });
};
console.warn = () => {};
"""


@needs_bundler
def test_theatre_bundle_does_not_wait_for_the_line_network(tmp_path_factory):
    out = run_ts(tmp_path_factory, DATA, FETCH + """
      const bundle = await data.loadBundle();
      const inFlight = requested.filter((n) => n === "assets_lines.geojson").length;
      const hasLines = "linesGeo" in bundle;
      let landed = false;
      const lines = data.loadLines().then((fc) => { landed = true; return fc; });
      await new Promise((r) => setTimeout(r, 20));
      const landedBeforeRelease = landed;
      releaseLines();
      const fc = await lines;
      return { inFlight, hasLines, landedBeforeRelease, features: fc.features.length,
               again: requested.filter((n) => n === "assets_lines.geojson").length,
               core: ["snapshot.json", "regions.geojson", "index_regional.json"].every((n) => requested.includes(n)) };
    """)
    assert out["core"], "the theatre's core files were not requested"
    # The bundle resolved while the 2.4 MB file was still held: the map does not wait for it.
    assert out["landedBeforeRelease"] is False
    assert out["hasLines"] is False
    # It was asked for at the same moment as the rest, exactly once, and the same request is reused.
    assert out["inFlight"] == 1, "the line file was not started alongside the core files"
    assert out["again"] == 1, "the line file was requested twice"
    assert out["features"] == 1


@needs_bundler
def test_theatre_a_failed_line_file_never_fails_the_dashboard_and_is_asked_for_again(tmp_path_factory):
    out = run_ts(tmp_path_factory, DATA, FETCH + """
      failLines = true;
      const bundle = await data.loadBundle();
      const asked = () => requested.filter((n) => n === "assets_lines.geojson").length;
      const first = await data.loadLines().then(() => "ok", () => "failed");
      failLines = false;
      const before = asked();
      const retry = data.loadLines();
      const after = asked();
      releaseLines();
      const second = await retry.then(() => "ok", () => "failed");
      // Once it has loaded, the answer is kept: no further request.
      await data.loadLines();
      return { loaded: !!bundle.snapshot, first, second, before, after, end: asked() };
    """)
    assert out["loaded"] is True, "a missing line file took the whole theatre down"
    assert out["first"] == "failed" and out["second"] == "ok"
    assert out["after"] == out["before"] + 1, "a failed line request was kept, so 'Try again' could never work"
    assert out["end"] == out["after"], "a loaded line file was requested again"


# ---------------- wiring (source guards) ----------------
# The maps themselves need WebGL; web/e2e/maploading.e2e.ts runs them. These keep the campaign able
# to see the lines that connect the tested reducer and loader to each map.

@pytest.mark.repo_hygiene
def test_map_loading_is_driven_by_real_events_and_never_by_a_timer():
    reducer = (SRC / "mapLoad.ts").read_text(encoding="utf-8")
    assert not re.search(r"setTimeout|setInterval|Date\.now|performance\.now", reducer), "the loading state uses a clock"
    for rel, source in (("global/SimpleMap.tsx", "polys"), ("components/MapPanel.tsx", "regions")):
        src = (SRC / rel).read_text(encoding="utf-8")
        assert f'm.on("sourcedata", (e) => {{ if (e.sourceId === "{source}" && e.isSourceLoaded) dispatch({{ type: "geometry_loaded" }}); }});' in src, rel
        assert f'      if (m.getSource("{source}")) dispatch({{ type: "idle" }});' in src, f"{rel}: 'drawn' is not MapLibre's idle event"
        assert not re.search(r"set(Timeout|Interval)\([^;]*dispatch\(", src), f"{rel}: a loading state is set from a timer"
        assert "<MapLoadIndicator state={load}" in src, f"{rel} draws no loading indicator"
        assert re.search(r"catch \(err\) \{[^}]*dispatch\(\{ type: \"failed\"", src, re.S), f"{rel}: a map that cannot be built is not reported"


@pytest.mark.repo_hygiene
def test_theatre_png_export_waits_for_the_lines_when_their_layer_is_on():
    app = (SRC / "App.tsx").read_text(encoding="utf-8")
    assert re.search(r"if \(filters\.showLines\) \{\s*try \{\s*lineData = await loadLines\(\);", app), \
        "the export does not wait for the line file"
    assert 'transformStyle: lineData ? (style) => withSourceData(style, "lines", lineData) : undefined' in app, \
        "the export does not carry the line data it waited for"
    panel = (SRC / "components" / "MapPanel.tsx").read_text(encoding="utf-8")
    assert 'm.addSource("lines", { type: "geojson", data: linesRef.current ?? EMPTY_FC });' in panel
    assert "src.setData(lines);" in panel, "the lines are never handed to the map when they arrive"
