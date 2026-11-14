/** The theatre's status-delay wording (iteration 21). A first-time reader took "Facilities
 *  awaiting reconstitution" for a list of facilities down now; these words must say what is
 *  known instead, with the delay read from served data, never written into the code. */

import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { NO_REPORT_LABEL, delayRule, noReportMeaning, statusCutoff, statusDelayDays, theatreDelayLine } from "./statusDelay";

const POLICY = { applied: true, evidence_embargo_days: 60 };

describe("the delay comes from the policy, never from the code", () => {
  it("reads the days only when the policy is applied", () => {
    expect(statusDelayDays(POLICY)).toBe(60);
    expect(statusDelayDays({ applied: true, evidence_embargo_days: 45 })).toBe(45);
    expect(statusDelayDays({ applied: false, evidence_embargo_days: 60 })).toBeNull();
    expect(statusDelayDays(undefined)).toBeNull();
    expect(statusDelayDays({ applied: true })).toBeNull();
  });

  it("the cut-off is the publication date minus the delay", () => {
    expect(statusCutoff("2026-11-13", POLICY)).toBe("2026-09-14");
    expect(statusCutoff("2026-03-01", { applied: true, evidence_embargo_days: 1 })).toBe("2026-02-28");
    expect(statusCutoff("2026-11-13", undefined)).toBeNull();
    expect(statusCutoff(undefined, POLICY)).toBeNull();
    expect(statusCutoff("13 Nov 2026", POLICY)).toBeNull();
  });
});

describe("a no-report count never reads as an operating status", () => {
  it("with the policy: states the rule, the cut-off, and that it is not a list of facilities down now", () => {
    const s = noReportMeaning("2026-11-13", POLICY);
    expect(s).toContain("60 days old");
    expect(s).toContain("14 Sep 2026");
    expect(s).toContain("may already be working again");
    expect(s).toContain("not a list of facilities that are down now");
  });

  it("a different served delay changes the words", () => {
    expect(noReportMeaning("2026-11-13", { applied: true, evidence_embargo_days: 30 })).toContain("30 days old");
    expect(delayRule({ applied: true, evidence_embargo_days: 30 })).not.toContain("60");
  });

  it("with the policy but no number: the rule in words, no invented figure", () => {
    const s = noReportMeaning("2026-11-13", { applied: true });
    expect(s).toContain("only after a delay");
    expect(s).not.toMatch(/\d+ days old/);
  });

  it("without a campaign policy: modelled, not observed, and no delay claimed", () => {
    const s = noReportMeaning("2026-11-13", { applied: false });
    expect(s).toContain("not an observed operating status");
    expect(s).not.toMatch(/delay|days old|cut-off \(/);
  });

  it("the label carries no status word", () => {
    expect(NO_REPORT_LABEL).not.toMatch(/impair|awaiting|unresolved|down|offline|current/i);
  });
});

describe("the home page's theatre line", () => {
  const sys = (extra: object) => ({ systems: [{ kind: "country", name: "Canada" }, { kind: "theatre", name: "Russia, Belarus & Crimea", ...extra }] });

  it("states the served delay", () => {
    const line = theatreDelayLine(sys({ status_delay_days: 60 }))!;
    expect(line).toContain("Russia, Belarus & Crimea");
    expect(line).toContain("60 days old");
    expect(line).toContain("never shows whether a facility is working now");
  });

  it("states the rule without a number when an older build has no field", () => {
    const line = theatreDelayLine(sys({}))!;
    expect(line).toContain("only after a delay");
    expect(line).not.toMatch(/\d/);
  });

  it("says nothing when the build says no policy applies, or there is no theatre", () => {
    expect(theatreDelayLine(sys({ status_delay_days: null }))).toBeNull();
    expect(theatreDelayLine({ systems: [{ kind: "country", name: "Canada" }] })).toBeNull();
    expect(theatreDelayLine(null)).toBeNull();
  });
});

describe("the served payload carries what these words read", () => {
  // The layer that ships: the committed theatre snapshot and global manifest.
  const data = resolve(__dirname, "../public/data");
  const snap = JSON.parse(readFileSync(resolve(data, "snapshot.json"), "utf-8"));
  const manifest = JSON.parse(readFileSync(resolve(data, "global/manifest.json"), "utf-8"));

  it("the snapshot's policy gives a delay and a cut-off", () => {
    expect(statusDelayDays(snap.campaign_policy)).toBeGreaterThan(0);
    expect(statusCutoff(snap.as_of, snap.campaign_policy)).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("the manifest's theatre entry, when it carries the delay, agrees with the snapshot", () => {
    const t = manifest.systems.find((s: { kind: string }) => s.kind === "theatre");
    expect(t).toBeTruthy();
    // Absent until the pipeline that adds it has run; then it must match the snapshot.
    if (t.status_delay_days !== undefined) {
      expect(t.status_delay_days).toBe(statusDelayDays(snap.campaign_policy));
    }
    expect(theatreDelayLine(manifest)).toContain(t.name);
  });
});
