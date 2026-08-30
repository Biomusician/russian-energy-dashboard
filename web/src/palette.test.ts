import { describe, it, expect } from "vitest";
import { esdiDeltaColor, ESDI_DELTA_STOPS } from "./palette";

// §14-15 diverging ramp. The invariants that matter: it is symmetric-in-meaning (a fall is
// distinctly cooler than a rise), saturates at the ends, and its neutral is the zero stop —
// so "improved" (blue) can never be confused with "low exposure" on the sequential ramp.
describe("esdiDeltaColor", () => {
  const blueEnd = ESDI_DELTA_STOPS[0][1];
  const redEnd = ESDI_DELTA_STOPS[ESDI_DELTA_STOPS.length - 1][1];

  it("saturates to the blue end for a large fall", () => {
    expect(esdiDeltaColor(-5)).toBe(blueEnd);
    expect(esdiDeltaColor(-3)).toBe(blueEnd);
  });

  it("saturates to the red end for a large rise", () => {
    expect(esdiDeltaColor(5)).toBe(redEnd);
    expect(esdiDeltaColor(3)).toBe(redEnd);
  });

  it("uses the zero-stop neutral at exactly zero", () => {
    const zeroStop = ESDI_DELTA_STOPS.find(([s]) => s === 0)![1];
    expect(esdiDeltaColor(0)).toBe(zeroStop);
  });

  it("gives a fall and a rise of equal magnitude different colours", () => {
    expect(esdiDeltaColor(-1)).not.toBe(esdiDeltaColor(1));
  });
});
