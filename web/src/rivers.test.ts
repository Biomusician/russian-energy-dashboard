import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { RIVER_REVEAL_STEPS, buildRiverOpacity } from "./components/MapPanel";

/** The rivers layer is context geography, but it has now produced two real defects, so both are
 *  pinned here.
 *
 *  1. Iteration 5 shipped `["zoom"]` nested inside a `case`. MapLibre rejects that and reports it
 *     through the error EVENT rather than throwing, so the layer was silently absent for three
 *     iterations and its toggle errored.
 *  2. The first fix reformulated it as an `interpolate` whose STOP OUTPUTS carried the gate —
 *     but interpolation blends between those outputs, so a river was already ~30% opaque below
 *     its own reveal zoom. The gate the comment promised was not the gate that shipped.
 *
 *  The shipped form is a `step` whose bucket boundaries are the distinct reveal_zoom values the
 *  pipeline emits. That is exact, but it couples style to data — which is what this guards. */

const RIVERS = JSON.parse(readFileSync(new URL("../public/data/rivers.geojson", import.meta.url), "utf-8")) as {
  features: { properties: { reveal_zoom?: number } }[];
};

const dataThresholds = [...new Set(RIVERS.features.map((f) => f.properties.reveal_zoom ?? 0))].sort((a, b) => a - b);

/** What the shipped expression actually yields, evaluated the way MapLibre would. */
function opacityAt(zoom: number, revealZoom: number): number {
  const expr = buildRiverOpacity();
  let out = expr[2] as unknown[];                       // default output, below first boundary
  for (let i = 3; i < expr.length; i += 2) {
    if (zoom >= (expr[i] as number)) out = expr[i + 1] as unknown[];
    else break;
  }
  const [, cond, whenTrue, whenFalse] = out as [string, [string, number, unknown], number, number];
  return cond[1] >= revealZoom ? whenTrue : whenFalse;
}

describe("rivers reveal gate", () => {
  it("covers every reveal threshold present in the shipped data", () => {
    // If the pipeline starts emitting a new reveal_zoom, the style must gain a matching bucket
    // or those rivers reveal late (the bug this replaced).
    for (const t of dataThresholds) {
      expect(RIVER_REVEAL_STEPS, `data threshold ${t} has no matching style bucket`).toContain(t);
    }
  });

  it("shows a river at its own reveal zoom, and not before", () => {
    for (const t of dataThresholds) {
      if (t > 0) expect(opacityAt(t - 0.2, t), `river revealed early at ${t}`).toBe(0);
      expect(opacityAt(t, t), `river not revealed at its own zoom ${t}`).toBeGreaterThan(0);
      expect(opacityAt(t + 2, t)).toBeGreaterThan(0);
    }
  });

  it("is a hard gate — never a partial fade below the reveal zoom", () => {
    for (const t of dataThresholds) {
      for (let z = 0; z < t; z += 0.2) {
        expect(opacityAt(z, t), `partial opacity at z${z.toFixed(1)} for reveal ${t}`).toBe(0);
      }
    }
  });

  it("keeps every river visible once fully zoomed in", () => {
    for (const t of dataThresholds) expect(opacityAt(9, t)).toBeGreaterThan(0);
  });

  it("never emits an opacity outside [0,1]", () => {
    for (const t of dataThresholds) {
      for (let z = 0; z <= 9; z += 0.5) {
        const o = opacityAt(z, t);
        expect(o).toBeGreaterThanOrEqual(0);
        expect(o).toBeLessThanOrEqual(1);
      }
    }
  });

  it("uses zoom only as the direct input to the top-level step (the iteration-5 defect)", () => {
    const expr = buildRiverOpacity();
    expect(expr[0]).toBe("step");
    expect(expr[1]).toEqual(["zoom"]);
    // No nested ["zoom"] anywhere in the outputs — that is what MapLibre rejects.
    expect(JSON.stringify(expr.slice(2))).not.toContain('["zoom"]');
  });
});
