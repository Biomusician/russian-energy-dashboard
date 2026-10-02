/** Three different facts must stop rendering as the same "0.00" (iteration 12).
 *
 *  The zero taxonomy existed from iteration 11 but was readable only in the Evidence Inspector,
 *  which fetches explanations_regional.json lazily. Every other surface that prints a region's
 *  zero — the map hover card, a rankings row, the exported selection label — had no access to it
 *  and printed a bare number. A region impaired in a sector the index cannot size looked exactly
 *  like a region that was looked at and found quiet.
 */

import { describe, it, expect } from "vitest";
import { ZERO_SHORT, zeroIsUnmeasured } from "./palette";

const ALL = [
  "NO_RECORDED_IMPAIRMENT",
  "IMPAIRMENT_ONLY_IN_UNCOVERED_SECTOR",
  "COVERED_IMPAIRMENT_WITH_NO_CAPACITY_FIGURE",
  "COVERED_SECTOR_SIGNAL_ROUNDS_TO_ZERO",
  "NOT_APPLICABLE",
];

describe("every kind of zero has words of its own", () => {
  it("covers every category the pipeline can emit", () => {
    // Mirrors ZERO_NOTES in pipeline/explain.py. A category added there without a phrase here
    // would render as a bare 0.00 again, which is the whole defect.
    for (const basis of ALL) {
      expect(ZERO_SHORT[basis], basis).toBeTruthy();
    }
    expect(Object.keys(ZERO_SHORT).sort()).toEqual([...ALL].sort());
  });

  it("gives each one a distinct phrase", () => {
    expect(new Set(Object.values(ZERO_SHORT)).size).toBe(ALL.length);
  });

  it("never describes an unmeasured zero as an absence of damage", () => {
    for (const basis of ALL) {
      if (zeroIsUnmeasured(basis)) {
        expect(ZERO_SHORT[basis]).toMatch(/impaired|not defined/);
        expect(ZERO_SHORT[basis]).not.toMatch(/nothing/);
      }
    }
  });
});

describe("unmeasured and absent are kept apart", () => {
  it("flags the two 'we cannot measure this' categories and not the others", () => {
    expect(zeroIsUnmeasured("IMPAIRMENT_ONLY_IN_UNCOVERED_SECTOR")).toBe(true);
    expect(zeroIsUnmeasured("COVERED_IMPAIRMENT_WITH_NO_CAPACITY_FIGURE")).toBe(true);
    expect(zeroIsUnmeasured("NOT_APPLICABLE")).toBe(true);
    // A real contribution below display resolution is MEASURED — it is just small. Flagging it
    // as unmeasured would overstate the uncertainty, which is its own kind of dishonesty.
    expect(zeroIsUnmeasured("COVERED_SECTOR_SIGNAL_ROUNDS_TO_ZERO")).toBe(false);
    expect(zeroIsUnmeasured("NO_RECORDED_IMPAIRMENT")).toBe(false);
  });

  it("says nothing rather than guessing for an unknown or absent basis", () => {
    expect(zeroIsUnmeasured(null)).toBe(false);
    expect(zeroIsUnmeasured(undefined)).toBe(false);
    expect(ZERO_SHORT["SOMETHING_NEW"]).toBeUndefined();
  });
});
