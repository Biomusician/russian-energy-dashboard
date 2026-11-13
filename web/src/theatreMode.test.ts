import { describe, expect, it } from "vitest";
import { MODES, MODE_LABEL, modeOf } from "./theatreMode";

describe("theatre mode", () => {
  it("is derived from the two existing booleans, and briefing wins", () => {
    expect(modeOf(false, false)).toBe("analyze");
    expect(modeOf(true, false)).toBe("focus");
    expect(modeOf(true, true)).toBe("brief");
    // Briefing always implies map focus in App, but the derivation must not depend on it.
    expect(modeOf(false, true)).toBe("brief");
  });

  it("keeps the accessible names existing links and tests rely on", () => {
    expect(MODES).toEqual(["analyze", "focus", "brief"]);
    expect(MODE_LABEL.focus.label).toBe("Map focus");
    expect(MODE_LABEL.brief.label).toBe("Briefing & export");
    // The short phone label must be contained in the accessible name (label in name).
    for (const m of MODES) expect(MODE_LABEL[m].label.toLowerCase()).toContain(MODE_LABEL[m].short.toLowerCase());
  });
});
