import { describe, it, expect } from "vitest";
import { windowRef, daysBetween, addDays, displayName } from "./data";

/** The real series is WEEKLY, which is the whole point of these tests: a "30-day change" can
 *  never be an exact 30-day observation, and the UI must be able to say what it really compared.
 *  Built here rather than loaded so the boundary cases (series start, scrubbing) are explicit. */
function weekly(startISO: string, n: number): string[] {
  return Array.from({ length: n }, (_, i) => addDays(startISO, i * 7));
}

describe("windowRef — weekly-series comparison semantics (§5)", () => {
  const dates = weekly("2026-01-02", 40); // 2026-01-02 .. 2026-10-01

  it("resolves a 30-day request to the nearest EARLIER weekly step, never later", () => {
    const step = dates.length - 1;
    const r = windowRef(dates, step, 30);
    expect(r.requestedWindowDays).toBe(30);
    // Weekly grid: the nearest earlier step is 35 days back, not 30.
    expect(r.actualComparisonDays).toBe(35);
    expect(r.comparisonDate).toBe(dates[step - 5]);
    expect(r.actualComparisonDays).toBeGreaterThanOrEqual(30);
  });

  it("resolves a 90-day request the same way", () => {
    const step = dates.length - 1;
    const r = windowRef(dates, step, 90);
    expect(r.actualComparisonDays).toBe(91); // 13 weekly steps
    expect(r.comparisonDate).toBe(dates[step - 13]);
  });

  it("never reaches past the scrubber (no future leakage) at any position", () => {
    for (let step = 0; step < dates.length; step++) {
      for (const win of [30, 90]) {
        const r = windowRef(dates, step, win);
        expect(r.comparisonStep).toBeLessThanOrEqual(step);
        expect(r.comparisonDate <= dates[step]).toBe(true);
      }
    }
  });

  it("honours a scrubbed HISTORICAL position rather than the latest date", () => {
    const step = 20;
    const r = windowRef(dates, step, 30);
    expect(r.comparisonStep).toBe(15);
    expect(r.comparisonDate).toBe(dates[15]);
    // and is unrelated to the end of the series
    expect(r.comparisonDate).not.toBe(dates[dates.length - 1]);
  });

  it("clamps at the beginning of the series and flags the truncation", () => {
    const r = windowRef(dates, 2, 90); // only 14 days of series exist before step 2
    expect(r.comparisonStep).toBe(0);
    expect(r.comparisonDate).toBe(dates[0]);
    expect(r.actualComparisonDays).toBe(14);
    expect(r.truncatedBySeriesStart).toBe(true);
  });

  it("does not flag truncation when a full window is available", () => {
    expect(windowRef(dates, 30, 30).truncatedBySeriesStart).toBe(false);
  });

  it("is a no-op at step 0 (nothing earlier to compare with)", () => {
    const r = windowRef(dates, 0, 30);
    expect(r.comparisonStep).toBe(0);
    expect(r.actualComparisonDays).toBe(0);
  });

  it("clamps an out-of-range step instead of returning undefined dates", () => {
    expect(windowRef(dates, 999, 30).comparisonDate).toBeTruthy();
    expect(windowRef(dates, -5, 30).comparisonStep).toBe(0);
  });
});

describe("daysBetween", () => {
  it("counts whole days forward", () => expect(daysBetween("2026-08-01", "2026-08-31")).toBe(30));
  it("is negative when b precedes a", () => expect(daysBetween("2026-08-31", "2026-08-01")).toBe(-30));
  it("is zero for the same day", () => expect(daysBetween("2026-08-01", "2026-08-01")).toBe(0));
  it("crosses a year boundary", () => expect(daysBetween("2025-12-31", "2026-01-01")).toBe(1));
});

describe("displayName — multi-line corpus names (render hazard)", () => {
  it("keeps a plain name unchanged", () => {
    expect(displayName("Kuibyshev refinery")).toBe("Kuibyshev refinery");
  });
  it("takes the head of a multi-line complex and counts the rest", () => {
    const raw = "Ust-Luga Multimodal Complex\n* Ust-Luga Oil JSC terminal\n* Nevskaya OPC terminal";
    expect(displayName(raw)).toBe("Ust-Luga Multimodal Complex (+2)");
  });
  it("ignores trailing blank lines", () => {
    expect(displayName("Taman terminal\n\n")).toBe("Taman terminal");
  });
  it("handles null/empty", () => {
    expect(displayName(null)).toBe("");
    expect(displayName("")).toBe("");
  });
});
