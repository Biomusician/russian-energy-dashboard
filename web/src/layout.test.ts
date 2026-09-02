/** Responsive layout regression tests (hotfix §18/§24).
 *
 *  These exist because the failure they guard against is silent: at 1280x720 the dashboard threw
 *  no errors, overlapped nothing and passed every existing test — it simply handed the map 241px
 *  of height and 27% of the viewport. Nothing in the build could tell that the map-first product
 *  had stopped being map-first.
 */

import { describe, expect, it } from "vitest";
import { classifyLayout } from "./useLayoutMode";
import { checkLayout, mapAreaTarget, type LayoutMetrics } from "./layoutMetrics";

describe("classifyLayout", () => {
  it("keeps both rails docked only where they still fit", () => {
    expect(classifyLayout(2560, 1440)).toBe("wide");
    expect(classifyLayout(1920, 1080)).toBe("wide");
    expect(classifyLayout(1600, 900)).toBe("wide");
  });

  it("undocks the dossier before the map falls below target", () => {
    // 1536x864 is a 1080p display at 125% scaling — the case that failed in the demo.
    expect(classifyLayout(1536, 864)).toBe("compact");
    expect(classifyLayout(1440, 900)).toBe("compact");
    expect(classifyLayout(1366, 768)).toBe("compact");
    // 1280x720 is a 1080p display at 150% scaling.
    expect(classifyLayout(1280, 720)).toBe("compact");
  });

  it("undocks both rails when even one is too expensive", () => {
    expect(classifyLayout(1024, 768)).toBe("narrow");
    expect(classifyLayout(900, 900)).toBe("narrow");
  });

  it("classifies on HEIGHT as well as width", () => {
    // The whole point of not using width-only media queries: the ribbon and timeline cost the
    // same absolute pixels at every width, so a short viewport cannot afford the same chrome.
    expect(classifyLayout(1920, 1080)).toBe("wide");
    expect(classifyLayout(1920, 700)).toBe("compact");
    expect(classifyLayout(1920, 500)).toBe("narrow");
  });

  it("is monotonic — shrinking a viewport never restores a heavier layout", () => {
    const rank = { wide: 3, compact: 2, narrow: 1 } as const;
    let prev = 4;
    for (const w of [2560, 1920, 1600, 1536, 1440, 1366, 1280, 1100, 900]) {
      const r = rank[classifyLayout(w, 900)];
      expect(r).toBeLessThanOrEqual(prev);
      prev = r;
    }
  });
});

describe("mapAreaTarget", () => {
  it("demands a HIGHER share on smaller screens", () => {
    // Chrome is near-fixed in absolute terms, so a small viewport that only matches a big
    // viewport's percentage has actually given proportionally more away.
    expect(mapAreaTarget(1280, 720)).toBeGreaterThan(mapAreaTarget(1920, 1080));
    expect(mapAreaTarget(1366, 768)).toBeGreaterThan(mapAreaTarget(2560, 1440));
  });
});

/** Measurements taken from the real browser against the shipped hotfix. If a future change
 *  regresses the layout, these are the numbers that will stop matching. */
const MEASURED: Array<[string, Partial<LayoutMetrics>]> = [
  ["2560x1440", { viewportWidth: 2560, viewportHeight: 1440, mapWidth: 1914, mapHeight: 1212 }],
  ["1920x1080", { viewportWidth: 1920, viewportHeight: 1080, mapWidth: 1289, mapHeight: 845 }],
  ["1600x900", { viewportWidth: 1600, viewportHeight: 900, mapWidth: 1070, mapHeight: 753 }],
  ["1536x864", { viewportWidth: 1536, viewportHeight: 864, mapWidth: 1320, mapHeight: 717 }],
  ["1440x900", { viewportWidth: 1440, viewportHeight: 900, mapWidth: 1227, mapHeight: 753 }],
  ["1366x768", { viewportWidth: 1366, viewportHeight: 768, mapWidth: 1153, mapHeight: 621 }],
  ["1280x720", { viewportWidth: 1280, viewportHeight: 720, mapWidth: 1067, mapHeight: 562 }],
  ["1024x768", { viewportWidth: 1024, viewportHeight: 768, mapWidth: 1024, mapHeight: 595 }],
];

function metrics(p: Partial<LayoutMetrics>): LayoutMetrics {
  const vw = p.viewportWidth!;
  const vh = p.viewportHeight!;
  const mw = p.mapWidth!;
  const mh = p.mapHeight!;
  return {
    viewportWidth: vw, viewportHeight: vh, devicePixelRatio: 1,
    mapWidth: mw, mapHeight: mh,
    mapAreaRatio: (mw * mh) / (vw * vh),
    persistentUiRatio: 0, horizontalOverflow: 0,
    ribbonHeight: 99, timelineHeight: 46,
    filtersVisibleWidth: 0, dossierVisibleWidth: 0,
    overlayObstructionRatio: 0,
    canvasWidth: mw, canvasHeight: mh, canvasMatchesContainer: true,
    mode: null,
    ...p,
  };
}

describe("measured layout meets its target at every supported viewport", () => {
  for (const [label, m] of MEASURED) {
    it(label, () => {
      const result = checkLayout(metrics(m));
      expect(result.failures).toEqual([]);
      expect(result.ok).toBe(true);
    });
  }
});

describe("checkLayout catches the regressions this hotfix fixed", () => {
  it("fails the pre-hotfix 1280x720 layout", () => {
    // The exact production measurement that prompted this work: 1039x241, 27% of the viewport.
    const r = checkLayout(metrics({
      viewportWidth: 1280, viewportHeight: 720, mapWidth: 1039, mapHeight: 241,
    }));
    expect(r.ok).toBe(false);
    expect(r.failures.join(" ")).toMatch(/27\.2% of the viewport|only 241px tall/);
  });

  it("fails a page that scrolls sideways", () => {
    const r = checkLayout(metrics({
      viewportWidth: 1024, viewportHeight: 768, mapWidth: 1024, mapHeight: 610,
      horizontalOverflow: 156,
    }));
    expect(r.failures.join(" ")).toMatch(/scrolls horizontally/);
  });

  it("fails a MapLibre canvas that did not follow its container", () => {
    // The symptom of a missing resize: canvas keeps the size it was built at.
    const r = checkLayout(metrics({
      viewportWidth: 1280, viewportHeight: 720, mapWidth: 1067, mapHeight: 573,
      canvasWidth: 766, canvasHeight: 457, canvasMatchesContainer: false,
    }));
    expect(r.failures.join(" ")).toMatch(/does not fill container/);
  });

  it("fails when overlays swallow the map", () => {
    const r = checkLayout(metrics({
      viewportWidth: 1280, viewportHeight: 720, mapWidth: 1067, mapHeight: 573,
      overlayObstructionRatio: 0.5,
    }));
    expect(r.failures.join(" ")).toMatch(/overlays cover/);
  });
});


/** Evidence Inspector overlay policy (iteration 11, addendum §1).
 *
 *  The Inspector is a fixed overlay, so it steals no layout width and the map-area targets above
 *  are unaffected by it — the same reasoning that excludes the dossier and filter drawers from
 *  persistent chrome. But "costs zero grid width" is not the same as "costs the reader nothing":
 *  a 460px panel is 7% of a 1920-wide map and would be half of a 1024-wide one, so its width
 *  follows the established per-mode drawer convention rather than one fixed number.
 *
 *  Measured in the browser against this build, with the Inspector open at each viewport. */
const INSPECTOR_MEASURED: Array<[string, { mode: string; width: number; coversMapPct: number }]> = [
  ["1920x1080", { mode: "wide", width: 460, coversMapPct: 7.3 }],
  ["1536x864", { mode: "compact", width: 400, coversMapPct: 30.3 }],
  ["1366x768", { mode: "compact", width: 400, coversMapPct: 34.7 }],
  ["1280x720", { mode: "compact", width: 400, coversMapPct: 37.5 }],
  ["1024x768", { mode: "narrow", width: 520, coversMapPct: 50.8 }],
];

describe("evidence inspector overlay", () => {
  it("never exceeds the dossier drawer's width in compact mode", () => {
    // The dossier drawer is min(400px, 92vw). An explanation panel that was wider than the
    // panel it sits beside would be the widest thing on a small screen, for the least
    // frequently used task.
    for (const [, m] of INSPECTOR_MEASURED) {
      if (m.mode === "compact") expect(m.width).toBeLessThanOrEqual(400);
    }
  });

  it("keeps a usable map beside it wherever a rail is still docked", () => {
    // In wide and compact modes the map remains the workspace: the overlay must leave most of
    // it visible. Narrow is the deliberate exception — there the reader is fully in explanation
    // mode and the map is one dismissal away.
    for (const [label, m] of INSPECTOR_MEASURED) {
      if (m.mode !== "narrow") {
        expect(m.coversMapPct, label).toBeLessThan(40);
      }
    }
  });

  it("does not change the map-area verdict at any viewport", () => {
    // The overlay is dismissible, so it is not persistent chrome. Every viewport still meets
    // its target with the Inspector open, which is what these recorded pairs assert.
    for (const [label, m] of MEASURED) {
      const result = checkLayout(metrics(m));
      expect(result.ok, `${label} with inspector open`).toBe(true);
    }
  });
});
