import { describe, expect, it } from "vitest";
import { withArticle } from "./data";
import { statusWithheld } from "./components/ui";
import type { RecoveryState } from "./types";

describe("withArticle", () => {
  it("reads taxonomy labels as sentence fragments with the right article", () => {
    expect(withArticle("Oil refinery")).toBe("an oil refinery");
    expect(withArticle("Oil terminal / storage")).toBe("an oil terminal / storage");
    expect(withArticle("Oil pipeline")).toBe("an oil pipeline");
    expect(withArticle("LNG terminal")).toBe("an LNG terminal");
    expect(withArticle("Thermal power plant")).toBe("a thermal power plant");
    expect(withArticle("Gas processing")).toBe("a gas processing site");
    expect(withArticle("Other generation")).toBe("an other generation site");
    expect(withArticle("Major substation")).toBe("a major substation");
  });
});

const base = {
  incident_id: "x", recovery_status: "impaired", resolved: false, scoring_evidence_kind: "modelled",
  reconstitution_horizon_days: 150, impairment_age_days: 30,
} as unknown as RecoveryState;

describe("statusWithheld", () => {
  const note = "Current facility status withheld during active campaign; historical recovery evidence may be published later.";

  it("is true for a campaign record with nothing released", () => {
    expect(statusWithheld({ ...base, publication_note: note })).toBe(true);
    expect(statusWithheld({ ...base, recovery_status: "unknown", publication_note: note } as RecoveryState)).toBe(true);
  });

  it("is false where released, dated evidence is shown, and for records outside the campaign", () => {
    expect(statusWithheld({ ...base, recovery_status: "partial_restart",
      publication_note: "Status shown is as of 2026-08-01; anything later is withheld." } as RecoveryState)).toBe(false);
    expect(statusWithheld({ ...base })).toBe(false);
    expect(statusWithheld({ ...base, resolved: true, publication_note: note })).toBe(false);
  });
});
