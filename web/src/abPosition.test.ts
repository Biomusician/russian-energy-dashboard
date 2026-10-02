/** Which side of an A/B comparison a recovery milestone falls on (iteration 12).
 *
 *  Previously untested, and wrong. `compare.a`/`compare.b` are what the reader typed; the map and
 *  the A and B figures are read from the nearest earlier WEEKLY series point, which can be six
 *  days earlier. Comparing milestones against the typed dates labelled a milestone in that gap
 *  "by A" while the A value printed beside it excluded the very same milestone.
 */

import { describe, it, expect } from "vitest";
import { abPosition, resolveAB } from "./components/Lifecycle";

// A weekly series, like the real one.
const DATES = [
  "2026-08-06", "2026-08-13", "2026-08-20", "2026-08-27", "2026-09-03", "2026-09-10",
];

const cmp = (a: string, b: string) => ({ a, b, mode: "delta" as const });

describe("milestones are placed against the dates the comparison actually shows", () => {
  it("resolves both ends back to the series, not to what was typed", () => {
    expect(resolveAB(DATES, cmp("2026-08-25", "2026-09-08")))
      .toEqual({ a: "2026-08-20", b: "2026-09-03" });
  });

  it("THE DEFECT: a milestone inside the resolution gap is not claimed by A", () => {
    // Typed A is 25 Aug; the displayed A is the 20 Aug point. A milestone on the 22nd is NOT in
    // the A figure, so it must read as movement between A and B.
    const ab = resolveAB(DATES, cmp("2026-08-25", "2026-09-08"));
    expect(abPosition("2026-08-22", ab)).toBe("between");
    // Against the typed dates — the old behaviour — this was "by_a".
    expect("2026-08-22" <= "2026-08-25").toBe(true);
  });

  it("places milestones on, before and after each resolved end", () => {
    const ab = resolveAB(DATES, cmp("2026-08-20", "2026-09-03"));
    expect(abPosition("2026-08-19", ab)).toBe("by_a");
    expect(abPosition("2026-08-20", ab)).toBe("by_a");      // the A point itself is IN A
    expect(abPosition("2026-08-21", ab)).toBe("between");
    expect(abPosition("2026-09-03", ab)).toBe("between");   // the B point itself is IN B
    expect(abPosition("2026-09-04", ab)).toBe("after_b");
  });

  it("answers nothing rather than guessing when there is no comparison or no date", () => {
    expect(resolveAB(DATES, null)).toBeNull();
    expect(abPosition("2026-08-21", null)).toBeNull();
    expect(abPosition(null, resolveAB(DATES, cmp("2026-08-20", "2026-09-03")))).toBeNull();
  });

  it("handles a date before the whole series without inventing a position", () => {
    const ab = resolveAB(DATES, cmp("2020-01-01", "2026-09-03"));
    // resolvePoint cannot go earlier than the series start, so A clamps to it; a milestone
    // before that is still "by A", which is true: it is already inside the A figure.
    if (ab) expect(abPosition("2019-01-01", ab)).toBe("by_a");
  });
});
