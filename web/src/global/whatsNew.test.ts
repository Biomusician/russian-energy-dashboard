import { describe, expect, it } from "vitest";
import { readFileSync, existsSync } from "node:fs";
import { whatsNewShapeProblems, type WhatsNew } from "./manifest";
import { buildAgeText, changeSummary, indexText, itemText } from "./whatsNewText";

const SERVED = new URL("../../public/data/global/whats_new.json", import.meta.url);

function minimal(): WhatsNew {
  return {
    schema_version: 1, available: true, unavailable_reason: null,
    comparison: { previous_as_of: "2026-11-11", current_as_of: "2026-11-12", mode: "production", basis: "b" },
    categories: [{ id: "records_added", label: "New published records", meaning: "m" },
                 { id: "records_withdrawn", label: "Records withdrawn or held on review", meaning: "m" }],
    order: "o", note: "n",
    global: [],
    systems: [{ system_id: "us", name: "United States", kind: "country", changes: [
      { category: "records_added", notes: [], event_dates: ["2022-02-03", "2023-01-01"], all_predate_previous_build: true,
        items: [{ key: "us-change-01", date: "2022-02-03", date_precision: "day", region: "Texas", class: "Oil refinery" }], more: false },
    ] }],
    unchanged: [{ system_id: "ca", name: "Canada" }],
  };
}

describe("whats_new.json shape", () => {
  it("accepts a well-formed file", () => {
    expect(whatsNewShapeProblems(minimal())).toEqual([]);
  });

  it("refuses the malformed shapes the panel would otherwise throw on", () => {
    expect(whatsNewShapeProblems(null)).toEqual(["not an object"]);
    const noList = { ...minimal(), systems: "x" };
    expect(whatsNewShapeProblems(noList)).toContain("systems is malformed");
    const unknownCat = minimal();
    unknownCat.systems[0].changes[0].category = "new_disruption_today";
    expect(whatsNewShapeProblems(unknownCat)).toContain("systems is malformed");
    const badItem = minimal() as unknown as { systems: { changes: { items: unknown[] }[] }[] };
    badItem.systems[0].changes[0].items = [{ key: "k" }];
    expect(whatsNewShapeProblems(badItem)).toContain("systems is malformed");
    expect(whatsNewShapeProblems({ ...minimal(), unchanged: ["ca"] })).toContain("unchanged is malformed");
    expect(whatsNewShapeProblems({ ...minimal(), available: "yes" })).toContain("available is not a boolean");
  });

  it.skipIf(!existsSync(SERVED))("accepts the served file", () => {
    const d = JSON.parse(readFileSync(SERVED, "utf-8"));
    expect(whatsNewShapeProblems(d)).toEqual([]);
  });
});

describe("panel wording", () => {
  it("computes the build's age on the reader's clock, never at build time", () => {
    expect(buildAgeText("2026-11-12", "2026-11-12")).toBe("built today, by your device's clock");
    expect(buildAgeText("2026-11-12", "2026-11-13")).toBe("built 1 day ago, by your device's clock");
    expect(buildAgeText("2026-11-12", "2026-12-02")).toBe("built 20 days ago, by your device's clock");
    expect(buildAgeText("2026-11-12", "2026-11-11")).toBe("built today, by your device's clock");
    expect(buildAgeText("2026-11-12", "2026-11-01")).toMatch(/after today/);
    expect(buildAgeText(null, "2026-11-12")).toBe("");
  });

  it("calls a backfill the record catching up, with the event dates, never new disruption", () => {
    const c = minimal().systems[0].changes[0];
    expect(changeSummary(c)).toBe("dated 3 Feb 2022 to 1 Jan 2023. All dated before the previous build: the record catching up, not new disruption.");
    const recent = { ...c, event_dates: ["2026-11-11", "2026-11-11"] as [string, string], all_predate_previous_build: false };
    expect(changeSummary(recent)).toBe("dated 11 Nov 2026. Found by research; the dates are when the events happened.");
    expect(changeSummary(recent)).not.toMatch(/new disruption|today|breaking/i);
  });

  it("prints a month-precision date as a month and never names an id", () => {
    expect(itemText({ key: "sa-change-01", date: "2026-04", date_precision: "month", region: "National", class: "Upstream production" }))
      .toBe("Apr 2026 · National · Upstream production");
    expect(itemText({ key: "us-change-02", date: "2023-05-29", date_precision: "day", region: "Assam", class: "Oil refinery",
      fields: ["reported figure", "sources"] })).toBe("29 May 2023 · Assam · Oil refinery — corrected: reported figure, sources");
    expect(itemText({ key: "k", date: "2022-02-03", date_precision: "day", region: "Texas", class: "Oil refinery",
      recovery_kind: "full restart reported", evidence_date: "2022-03-01" }))
      .toBe("3 Feb 2022 · Texas · Oil refinery — full restart reported; the report describes 1 Mar 2022");
  });

  it("says when the theatre's index movement cannot be split between data and method", () => {
    const row = { system_id: "ru", name: "R", kind: "theatre", changes: [],
      index: { label: "Monitored-Area ESDI", before: 6.8, after: 6.69, separable: false } };
    // Levels at the headline's one decimal (the decay does not support a second), the movement at two.
    expect(indexText(row)).toBe("Monitored-Area ESDI 6.8 to 6.7 (−0.11). The method changed too, so the movement cannot be split between data and method.");
    expect(indexText({ ...row, index: { ...row.index, separable: true } })).toBe("Monitored-Area ESDI 6.8 to 6.7 (−0.11).");
    // Unchanged is decided on the movement, and the level is printed like the headline.
    expect(indexText({ ...row, index: { ...row.index, before: 6.69 } })).toBe("Monitored-Area ESDI unchanged at 6.7.");
    // A movement too small to show at one decimal still shows, at two.
    expect(indexText({ ...row, index: { ...row.index, before: 6.66, separable: true } })).toBe("Monitored-Area ESDI 6.7 to 6.7 (+0.03).");
    expect(indexText({ ...row, index: undefined })).toBeNull();
  });
});
