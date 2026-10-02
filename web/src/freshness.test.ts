/** The staleness safeguard (iteration 12 P2).
 *
 *  The eleven-day outage these tests exist for was invisible because the only freshness signal on
 *  the page, "· live", meant "the scrubber is at the last step" rather than "this build is
 *  current". So the first test here is the regression: an eleven-day-old build must not read live.
 */

import { describe, expect, it } from "vitest";
import { assessFreshness, type PublicationCadence } from "./freshness";

const CADENCE: PublicationCadence = {
  as_of: "2026-10-01",
  build_time: "2026-10-01T05:31:00+00:00",
  expected_cadence_days: 1,
  cadence_source: ".github/workflows/refresh.yml (schedule: cron '20 5 * * *')",
  ageing_after_days: 2,
  stale_after_days: 3,
  badly_stale_after_days: 7,
};

/** A local-midnight Date, so the day arithmetic is exercised the way a browser sees it. */
function day(iso: string, hour = 12): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d, hour);
}

describe("THE REGRESSION: a frozen build cannot describe itself as live", () => {
  it("does not say live for the actual eleven-day outage", () => {
    const a = assessFreshness("2026-09-20", CADENCE, day("2026-10-01"));
    expect(a.days).toBe(11);
    expect(a.level).toBe("badly_stale");
    expect(a.shortLabel).not.toContain("live");
    expect(a.banner).toContain("NOT CURRENT");
    expect(a.severe).toBe(true);
  });

  it("says the outage is a failure, not a slip, and quantifies the missed updates", () => {
    const a = assessFreshness("2026-09-20", CADENCE, day("2026-10-01"));
    expect(a.banner).toContain("has failed rather than merely slipped");
    expect(a.banner).toContain("missed at least 10 days");
  });

  it("warns that later events are absent, so the reader cannot read it as current", () => {
    const a = assessFreshness("2026-09-20", CADENCE, day("2026-10-01"));
    expect(a.banner).toContain("Events after the date shown are not in these figures");
  });

  it("reads as English at every level", () => {
    // Caught in the browser, not by a test: "has not rebuilt in 11 days ago". The age is built
    // from two pieces and only one of them carries "ago".
    for (const today of ["2026-10-03", "2026-10-05", "2026-10-12", "2026-11-20"]) {
      const b = assessFreshness("2026-10-01", CADENCE, day(today)).banner!;
      expect(b).not.toMatch(/\bin \d+ days? ago\b/);
      expect(b).not.toMatch(/\bago\b.*\bago\b/);
    }
  });
});

describe("the thresholds the payload publishes", () => {
  it("is live on the build day and the day after", () => {
    for (const today of ["2026-10-01", "2026-10-02"]) {
      const a = assessFreshness("2026-10-01", CADENCE, day(today));
      expect(a.level).toBe("fresh");
      expect(a.shortLabel).toBe("live");
      expect(a.banner).toBeNull();
    }
  });

  it("is ageing, with no alarm, at one plausibly-missed run", () => {
    const a = assessFreshness("2026-10-01", CADENCE, day("2026-10-03"));
    expect(a.level).toBe("ageing");
    expect(a.days).toBe(2);
    expect(a.severe).toBe(false);
    expect(a.banner).toContain("last rebuilt 2 days ago");
    expect(a.banner).not.toContain("NOT CURRENT");
  });

  it("warns at headline weight once several runs are missed", () => {
    const a = assessFreshness("2026-10-01", CADENCE, day("2026-10-04"));
    expect(a.level).toBe("stale");
    expect(a.severe).toBe(true);
    expect(a.banner).toContain("NOT CURRENT");
  });

  it("escalates at the badly-stale threshold and not before it", () => {
    expect(assessFreshness("2026-10-01", CADENCE, day("2026-10-07")).level).toBe("stale");
    expect(assessFreshness("2026-10-01", CADENCE, day("2026-10-08")).level).toBe("badly_stale");
  });

  it("reads its thresholds from the payload rather than hardcoding them", () => {
    // Same age, a cadence that tolerates far more: the verdict must follow the payload.
    const lax = { ...CADENCE, ageing_after_days: 30, stale_after_days: 60, badly_stale_after_days: 90 };
    expect(assessFreshness("2026-10-01", lax, day("2026-10-20")).level).toBe("fresh");
  });
});

describe("unknown, unclassifiable and stale stay three different answers", () => {
  it("gives a factual age but no verdict when the payload states no thresholds", () => {
    const a = assessFreshness("2026-09-20", { as_of: "2026-09-20" }, day("2026-10-01"));
    expect(a.level).toBe("unclassified");
    expect(a.days).toBe(11);
    expect(a.shortLabel).toBe("built 11 days ago");
    // No thresholds were published, so no judgement is available -- and inventing one here would
    // be the component hardcoding a number the payload is supposed to own.
    expect(a.banner).toBeNull();
    expect(a.shortLabel).not.toContain("live");
  });

  it("neither claims freshness nor claims staleness when there is no readable date", () => {
    for (const bad of [null, undefined, "", "not-a-date", "2026-13-45x"]) {
      const a = assessFreshness(bad, CADENCE, day("2026-10-01"));
      expect(a.level).toBe("unknown");
      expect(a.days).toBeNull();
      expect(a.shortLabel).not.toContain("live");
      expect(a.banner).toBeNull();
    }
  });

  it("tolerates a one-day timezone offset instead of calling it a clock error", () => {
    // A reader west of the build machine is legitimately a calendar day behind its as-of date.
    const a = assessFreshness("2026-10-02", CADENCE, day("2026-10-01"));
    expect(a.days).toBe(-1);
    expect(a.level).toBe("fresh");
  });

  it("refuses to compute an age against a clock set well before the build", () => {
    const a = assessFreshness("2026-10-01", CADENCE, day("2026-09-01"));
    expect(a.level).toBe("clock_behind");
    expect(a.severe).toBe(false);
    expect(a.shortLabel).not.toContain("live");
    expect(a.banner).toContain("cannot be checked here");
  });
});

describe("the day count is calendar-based, not 24-hour-based", () => {
  it("does not drift with the time of day", () => {
    for (const hour of [0, 1, 11, 12, 23]) {
      expect(assessFreshness("2026-10-01", CADENCE, day("2026-10-04", hour)).days).toBe(3);
    }
  });

  it("counts across a month and a year boundary", () => {
    expect(assessFreshness("2026-10-28", CADENCE, day("2026-11-02")).days).toBe(5);
    expect(assessFreshness("2026-12-29", CADENCE, day("2027-01-03")).days).toBe(5);
  });

  it("uses the singular for exactly one day", () => {
    const lax = { ...CADENCE, ageing_after_days: 1, stale_after_days: 5, badly_stale_after_days: 9 };
    const a = assessFreshness("2026-10-01", lax, day("2026-10-02"));
    expect(a.shortLabel).toBe("built 1 day ago");
  });
});
