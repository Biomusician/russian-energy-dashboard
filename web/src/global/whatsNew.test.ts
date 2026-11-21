import { describe, expect, it } from "vitest";
import { readFileSync, existsSync } from "node:fs";
import { whatsNewShapeProblems, type CountryEvent, type WhatsNew, type WhatsNewImpactItem } from "./manifest";
import { eventAnchor } from "./evidence";
import {
  buildAgeText, changeLink, changeSummary, impactItemText, impactSummary, indexText, itemText, recordHref, statusWord,
} from "./whatsNewText";

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

describe("record and section links (iteration 22)", () => {
  const row = { key: "us-change-01", date: "2023-02-23", date_precision: "day", region: "Texas", class: "Oil refinery" };

  it("links a row to the record's own anchor, and only when the file carries its id", () => {
    const id = "us-2023-02-23-refinery fire/unit 2";
    const href = recordHref("us", { ...row, record_id: id });
    expect(href).toBe("?sys=us#ev-us-2023-02-23-refinery-fire-unit-2");
    // The same anchor the record's own "Link to this record" gives.
    expect(href).toBe(`?sys=us#${eventAnchor({ event_id: id, publication: null } as CountryEvent, "us")}`);
    // Under the campaign rule the file carries no id: the row is plain text, never a guessed link.
    expect(recordHref("sa", row)).toBeNull();
    expect(recordHref("sa", { ...row, record_id: "" })).toBeNull();
  });

  it("links a coverage change to the country's tab, a rule change to the Help page, and nothing else", () => {
    expect(changeLink({ category: "research_coverage", notes: [], link: { system_id: "us", tab: "research" } }))
      .toEqual({ href: "?sys=us#tab-research", label: "Open Research coverage", samePage: false });
    expect(changeLink({ category: "methodology", notes: [], link: { system_id: "us", tab: "method" } }))
      .toEqual({ href: "?sys=us#tab-method", label: "How this country is assessed", samePage: false });
    expect(changeLink({ category: "methodology", notes: [], link: { help: "whats-new" } }))
      .toEqual({ href: "?view=help#whats-new", label: "How this works", samePage: false });
    // The home section it used to name explains how systems were chosen (IA-06): no longer a target.
    expect(changeLink({ category: "methodology", notes: [], link: { anchor: "why-head" } as never })).toBeNull();
    expect(changeLink({ category: "methodology", notes: [] })).toBeNull();
    // A link the panel does not know is dropped, never followed: no tab it has not heard of, no script.
    expect(changeLink({ category: "x", notes: [], link: { system_id: "us", tab: "events" } })).toBeNull();
    expect(changeLink({ category: "x", notes: [], link: { help: "javascript:alert(1)" } })).toBeNull();
  });

  it("accepts the new fields and refuses a malformed impact layer", () => {
    const d = minimal();
    d.categories.push({ id: "impact_record_added", label: "Impact records added", meaning: "m" });
    d.systems[0].changes[0].items![0].record_id = "us-a";
    d.systems[0].changes[0].link = { system_id: "us", tab: "research" };
    d.impact_layer = [{ category: "impact_record_added", notes: ["First release of the impact layer."], first_release: true }];
    expect(whatsNewShapeProblems(d)).toEqual([]);
    expect(whatsNewShapeProblems({ ...d, impact_layer: null })).toEqual([]);
    expect(whatsNewShapeProblems({ ...d, impact_layer: "x" })).toContain("impact_layer is malformed");
    expect(whatsNewShapeProblems({ ...d, impact_layer: [{ category: "made_up", notes: [] }] })).toContain("impact_layer is malformed");
    const badId = minimal() as unknown as { systems: { changes: { items: { record_id: unknown }[] }[] }[] };
    badId.systems[0].changes[0].items[0].record_id = 7;
    expect(whatsNewShapeProblems(badId)).toContain("systems is malformed");
  });
});

describe("impact layer wording (iteration 22)", () => {
  const item: WhatsNewImpactItem = { key: "impact-change-01", impact_id: "imp-a", date: "2023-12-12", date_precision: "day",
    country: "Ukraine", sector: "fuel_supply" };

  it("tells a backfilled historical record from a new event, and says neither when it cannot tell", () => {
    expect(impactItemText({ ...item, timing: "backfill", first_published: "2026-11-20" }, "impact_record_added"))
      .toBe("12 Dec 2023 · Ukraine · fuel supply — historical record found by research, not a new event; first published 20 Nov 2026");
    expect(impactItemText({ ...item, date: "2026-11-18", timing: "new_event", first_published: "2026-11-20" }, "impact_record_added"))
      .toBe("18 Nov 2026 · Ukraine · fuel supply — new event; first published 20 Nov 2026");
    const unknown = impactItemText({ ...item, timing: "unknown", first_published: null }, "impact_record_added");
    expect(unknown).toBe("12 Dec 2023 · Ukraine · fuel supply");
    expect(unknown).not.toMatch(/new event|historical/);
  });

  it("calls an attribution or AI update an update to an existing record, never a new incident", () => {
    expect(impactItemText({ ...item, from: "CLAIMED", to: "ATTRIBUTED" }, "attribution_updated"))
      .toBe("12 Dec 2023 · Ukraine · fuel supply — attribution: Claimed → Attributed (existing record, not a new incident)");
    expect(impactItemText({ ...item, from: "NONE_REPORTED", to: "SUSPECTED" }, "ai_status_updated"))
      .toBe("12 Dec 2023 · Ukraine · fuel supply — AI involvement: None reported → Suspected (existing record, not a new incident)");
    expect(impactItemText({ ...item, from: "MODERATE", to: "HIGH" }, "evidence_strengthened"))
      .toBe("12 Dec 2023 · Ukraine · fuel supply — evidence confidence: Moderate → High");
    expect(statusWord("NOT_APPLICABLE")).toBe("Not applicable");
    expect(statusWord(null)).toBe("not stated");
  });

  it("summarises a set as historical or new only when every record in it is, and a first release not at all", () => {
    const c = { category: "impact_record_added", notes: [] };
    expect(impactSummary({ ...c, all_backfill: true })).toMatch(/the record catching up, not new events/);
    expect(impactSummary({ ...c, all_new_events: true })).toBe("Events dated within 30 days of first publication.");
    expect(impactSummary({ ...c, all_backfill: false, all_new_events: false })).toMatch(/each row says which/);
    expect(impactSummary({ ...c, first_release: true, notes: ["First release of the impact layer."] })).toBe("");
    expect(impactSummary({ category: "attribution_updated", notes: [] })).toBe("");
  });
});
