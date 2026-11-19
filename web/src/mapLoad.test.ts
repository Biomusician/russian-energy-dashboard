import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import { describe, expect, it } from "vitest";
import {
  MAP_LOAD_INITIAL, mapLoadCanRetry, mapLoadMessage, mapLoadPhase, mapLoadReducer, type MapLoadEvent, type MapLoadState,
} from "./mapLoad";
import { MapGeometryPlaceholder, MapLoadIndicator } from "./components/MapLoadIndicator";

/** Iteration 22: what a map says while it loads. The reducer is driven only by real events, so the
 *  tests feed it the sequences MapLibre and the load promises actually produce. */

const run = (events: MapLoadEvent[], from: MapLoadState = MAP_LOAD_INITIAL) => events.reduce(mapLoadReducer, from);
const LINES = { id: "lines", label: "network lines" };

describe("the map loading state", () => {
  it("says geometry, then data, then nothing, in the order the map really loads", () => {
    let s = MAP_LOAD_INITIAL;
    expect(mapLoadMessage(s)).toBe("Loading map geometry…");
    s = mapLoadReducer(s, { type: "geometry_loaded" });
    expect(mapLoadMessage(s)).toBe("Loading data…");
    s = mapLoadReducer(s, { type: "idle" });
    expect(mapLoadMessage(s)).toBeNull();
    expect(mapLoadPhase(s)).toBe("ready");
  });

  it("stays on geometry until the geometry is in, however many other events arrive", () => {
    const s = run([{ type: "data_pending", pending: true }, { type: "late_requested", ...LINES }, { type: "data_pending", pending: false }]);
    expect(mapLoadPhase(s)).toBe("geometry");
  });

  it("idle alone is enough: a map that is drawn has its geometry", () => {
    expect(mapLoadPhase(run([{ type: "idle" }]))).toBe("ready");
  });

  it("keeps saying 'Loading data…' over a drawn map while the caller's own data file is pending", () => {
    let s = run([{ type: "data_pending", pending: true }, { type: "geometry_loaded" }, { type: "idle" }]);
    expect(mapLoadMessage(s)).toBe("Loading data…");
    s = mapLoadReducer(s, { type: "data_pending", pending: false });
    expect(mapLoadMessage(s)).toBeNull();
  });

  it("names a file that arrives after the first paint, and stops when it has arrived", () => {
    let s = run([{ type: "idle" }, { type: "late_requested", ...LINES }]);
    expect(mapLoadPhase(s)).toBe("late");
    expect(mapLoadMessage(s)).toBe("Loading network lines…");
    s = mapLoadReducer(s, { type: "late_arrived", id: "lines" });
    expect(mapLoadMessage(s)).toBeNull();
    // Asked for twice, it is still one thing to wait for.
    s = run([{ type: "late_requested", ...LINES }, { type: "late_requested", ...LINES }], s);
    expect(s.late).toHaveLength(1);
  });

  it("a late file never hides that the map itself is still loading", () => {
    const s = run([{ type: "late_requested", ...LINES }, { type: "geometry_loaded" }]);
    expect(mapLoadMessage(s)).toBe("Loading data…");
  });

  it("a late file that fails is said, with a retry, and the map stays", () => {
    let s = run([{ type: "idle" }, { type: "late_requested", ...LINES }, { type: "late_failed", ...LINES }]);
    expect(mapLoadPhase(s)).toBe("late_failed");
    expect(mapLoadMessage(s)).toBe("Network lines could not be loaded. The rest of the map is complete.");
    expect(mapLoadCanRetry(s)).toBe(true);
    // Asked for again: loading, then gone.
    s = run([{ type: "late_requested", ...LINES }], s);
    expect(mapLoadMessage(s)).toBe("Loading network lines…");
    // A failure reported for a layer switched on only afterwards is still said.
    expect(mapLoadPhase(run([{ type: "idle" }, { type: "late_failed", ...LINES }]))).toBe("late_failed");
  });

  it("a failure before the map is drawn is an error with a retry", () => {
    const s = run([{ type: "failed", message: "WebGL is not available" }]);
    expect(mapLoadPhase(s)).toBe("failed");
    expect(mapLoadMessage(s)).toBe("The map could not be drawn.");
    expect(mapLoadCanRetry(s)).toBe(true);
    expect(s.error).toBe("WebGL is not available");
  });

  it("a map that is drawn is never covered by a later error", () => {
    const s = run([{ type: "geometry_loaded" }, { type: "idle" }, { type: "failed", message: "one layer failed" }]);
    expect(mapLoadPhase(s)).toBe("ready");
    expect(s.error).toBeNull();
  });

  it("a map that draws after an error was reported is a drawn map", () => {
    const s = run([{ type: "failed", message: "x" }, { type: "idle" }]);
    expect(mapLoadPhase(s)).toBe("ready");
  });

  it("retry starts the map again and keeps what the caller is still waiting for", () => {
    const s = run([{ type: "data_pending", pending: true }, { type: "failed", message: "x" }, { type: "retry" }]);
    expect(mapLoadPhase(s)).toBe("geometry");
    expect(s.dataPending).toBe(true);
    expect(s.error).toBeNull();
  });

  it("an event that changes nothing returns the same state, so the map does not re-render on every idle", () => {
    const s = run([{ type: "geometry_loaded" }, { type: "idle" }]);
    expect(mapLoadReducer(s, { type: "idle" })).toBe(s);
    expect(mapLoadReducer(s, { type: "geometry_loaded" })).toBe(s);
    expect(mapLoadReducer(s, { type: "data_pending", pending: false })).toBe(s);
  });
});

describe("the indicator", () => {
  const html = (s: MapLoadState, alternative?: string) =>
    renderToStaticMarkup(createElement(MapLoadIndicator, { state: s, onRetry: () => undefined, alternative }));

  it("is a polite live region that is in the page before, during and after loading", () => {
    for (const s of [MAP_LOAD_INITIAL, run([{ type: "geometry_loaded" }]), run([{ type: "idle" }])]) {
      expect(html(s)).toMatch(/<p class="map-load-text" role="status">/);
    }
    expect(html(MAP_LOAD_INITIAL)).toContain("Loading map geometry…");
    expect(html(MAP_LOAD_INITIAL)).toContain('data-map-load="geometry"');
    expect(html(run([{ type: "geometry_loaded" }]))).toContain("Loading data…");
  });

  it("says nothing and offers no button once the map is drawn", () => {
    const out = html(run([{ type: "idle" }]));
    expect(out).toContain('data-map-load="ready"');
    expect(out).toMatch(/<p class="map-load-text" role="status"><\/p>/);
    expect(out).not.toContain("<button");
    expect(out).not.toContain("is-on");
  });

  it("on failure says so, names the alternative and offers Try again", () => {
    const out = html(run([{ type: "failed", message: "x" }]), "The table below has the same data.");
    expect(out).toContain("The map could not be drawn. The table below has the same data.");
    expect(out).toMatch(/<button[^>]*>Try again<\/button>/);
  });

  it("the placeholder before a map exists says the geometry is loading, or that the map is unavailable", () => {
    const wait = renderToStaticMarkup(createElement(MapGeometryPlaceholder, { failed: false }));
    expect(wait).toContain("Loading map geometry…");
    expect(wait).toContain('role="status"');
    expect(wait).not.toContain("<button");
    const failed = renderToStaticMarkup(createElement(MapGeometryPlaceholder, { failed: true, onRetry: () => undefined, alternative: "The table below has every figure." }));
    expect(failed).toContain("Map unavailable. The table below has every figure.");
    expect(failed).toMatch(/<button[^>]*>Try again<\/button>/);
  });
});
