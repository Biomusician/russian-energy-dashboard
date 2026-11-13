import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  PLAIN_BASIS, PLAIN_BASIS_VERSION, capacityFigure, countLine, eventAnchor, eventOrigins, headlinesAllowed, isOpaqueAttackId,
  notEstablished, originSummary, originTotals, placementKind, plainBasis, registeredDomain, sourceOrigin,
} from "./evidence";
import { EMPTY_CORPUS_LEAD, RESEARCH_PREVIEW_DEFINITION, noScorePlain } from "./countryCopy";
import type { CountryEvent, CountrySystem } from "./manifest";

const DATA = new URL("../../public/data/", import.meta.url);
const read = (p: string) => JSON.parse(readFileSync(fileURLToPath(new URL(p, DATA)), "utf-8"));
const countryIds = (): string[] =>
  (read("global/manifest.json").systems as { id: string; kind: string }[]).filter((s) => s.kind === "country").map((s) => s.id);

describe("originating statements mirror the pipeline rule", () => {
  it("counts the registered domain, not the address", () => {
    expect(registeredDomain("https://www.example.com/a/b")).toBe("example.com");
    expect(registeredDomain("https://news.bbc.co.uk/x")).toBe("bbc.co.uk");
    expect(registeredDomain("https://pib.gov.in:443/x")).toBe("pib.gov.in");
    expect(registeredDomain("no-scheme.example.org/path")).toBe("example.org");
    const e = { sources: [{ url: "https://agency.gov/a" }, { url: "https://www.agency.gov/b" }, { url: "https://sub.agency.gov/c" }] };
    expect(originSummary(e)).toMatchObject({ pages: 3, origins: ["agency.gov"] });
  });

  it("a wire story republished by several outlets is one origin", () => {
    const e = { sources: [
      { url: "https://boereport.com/x", publisher: "BOE Report (Reuters)" },
      { url: "https://www.theglobeandmail.com/y", publisher: "Globe and Mail / Reuters" },
    ] };
    expect([...eventOrigins(e)]).toEqual(["wire:Reuters"]);
    expect(countLine(originSummary(e))).toBe("2 cited pages · 1 originating statement");
  });

  it("Wikipedia and content aggregators count as no origin", () => {
    expect(sourceOrigin({ url: "https://en.wikipedia.org/wiki/X", publisher: "Wikipedia" })).toBeNull();
    expect(sourceOrigin({ url: "https://example.net/x", publisher: "Wikipedia (English)" })).toBeNull();
    expect(sourceOrigin({ url: "https://www.indexbox.io/blog/x" })).toBeNull();
    const s = originSummary({ sources: [{ url: "https://en.wikipedia.org/wiki/X", publisher: "Wikipedia" }] });
    expect(s).toMatchObject({ pages: 1, origins: [], discoveryOnly: true });
    expect(countLine(s)).toBe("1 cited page · no originating statement");
  });

  it("a short publisher word is matched as a whole word, never inside another", () => {
    expect(sourceOrigin({ url: "https://spacenews.com/x", publisher: "SpaceNews" })).toBe("spacenews.com");
    expect(sourceOrigin({ url: "https://aleqt.com/x", publisher: "Al-Eqtisadiah (republishing SPA)" })).toBe("wire:Saudi Press Agency");
  });

  it("recomputes every served system's source-health totals exactly", () => {
    let checked = 0;
    for (const id of countryIds()) {
      const sys = read(`systems/${id}/system.json`);
      const events = read(`systems/${id}/events.json`).events;
      if (!sys.source_health || sys.source_health.single_origin_events === undefined) continue;
      expect(originTotals(events), id).toEqual({
        single_origin_events: sys.source_health.single_origin_events,
        discovery_only_events: sys.source_health.discovery_only_events,
      });
      checked += events.length;
    }
    expect(checked, "no served record was recounted").toBeGreaterThan(0);
  });
});

const threshold = { version: PLAIN_BASIS_VERSION, rule: "r", clauses: { 1: "Refinery shut.", 9: "Served ninth clause." } as Record<string, string> };

function ev(over: Partial<CountryEvent> = {}): CountryEvent {
  return {
    event_id: "xx-2024-01-01-a", date: "2024-01-01", date_precision: "day", date_end: null, region_code: null, region_name: null,
    geography_precision: "country", regions_affected: [], facility_name: null, facility_name_local: null, operator: null,
    asset_class: "refinery", cause: "technical", summary: "s", effect: null, inclusion_basis: "reported_effect",
    criterion_met: 1, threshold_basis: "Clause 1: x.", capacity_affected: null, sources: [{ url: "https://a.com/x" }],
    recovery: { research_status: "NOT_YET_RESEARCHED", kind: null, date: null, evidence: null, url: null },
    review: { reviewed_at: "2026-11-01", review_status: "blind_reviewed", primary_review_complete: true, independent_review_complete: true,
              reviewer_count: 4, disposition: "confirmed", source_count: 1, sources_opened_by_reviewer: 1, process: "p",
              threshold_version: PLAIN_BASIS_VERSION, source_access: "opened" },
    episode_id: "xx-2024-01-01-a", hazard_name: null, publication: null, ...over,
  };
}
function sys(policy?: CountrySystem["geography"]["precision_policy"]): CountrySystem {
  return { system_id: "xx", geography: { precision_policy: policy } } as unknown as CountrySystem;
}

describe("plain-language basis", () => {
  it("speaks every clause without a clause number", () => {
    for (const n of [1, 2, 3, 4, 5, 6, 7]) {
      const t = plainBasis(ev({ criterion_met: n }), threshold);
      expect(t).toBe(PLAIN_BASIS[n]);
      expect(t).not.toMatch(/clause|\b\d\b|§/i);
    }
  });
  it("falls back to the served rule when the rule version changed, and never invents a part", () => {
    expect(plainBasis(ev({ criterion_met: 1 }), { ...threshold, version: "2099-01-01.1" })).toBe("Refinery shut.");
    expect(plainBasis(ev({ criterion_met: 9 }), threshold)).toBe("Served ninth clause.");
    expect(plainBasis(ev({ criterion_met: null }), threshold)).toMatch(/not recorded/);
  });
  it("the served rule is the version the sentences were written for", () => {
    let checked = 0;
    for (const id of countryIds()) {
      expect(read(`systems/${id}/system.json`).inclusion_threshold.version, id).toBe(PLAIN_BASIS_VERSION);
      checked += 1;
    }
    expect(checked).toBeGreaterThan(0);
  });
});

describe("what a record does not establish", () => {
  it("carries the measure and the qualifier of a capacity figure", () => {
    const cap = { value: 550000, value_min: null, value_max: null, qualifier: "exact" as const, measure: "facility_size" as const, unit: "bbl/d", source_says: "x" };
    const lines = notEstablished(ev({ capacity_affected: cap }));
    expect(lines[0]).toContain("550,000 bbl/d");
    expect(lines[0]).toContain("the facility's size, not the amount lost");
    expect(capacityFigure({ ...cap, qualifier: "at_least", measure: "affected" })).toBe("at least 550,000 bbl/d");
    expect(capacityFigure({ ...cap, value: null, value_min: 10, value_max: 20, qualifier: "range" })).toBe("10–20 bbl/d");
    expect(capacityFigure({ ...cap, value: null, qualifier: "disputed" })).toBeNull();
  });
  it("under campaign safeguards shows no figure and no later status", () => {
    const cap = { value: 300000, value_min: null, value_max: null, qualifier: "about" as const, measure: "affected" as const, unit: "bbl/d", source_says: "x" };
    const covered = ev({ capacity_affected: cap, cause: "kinetic_strike",
      recovery: { research_status: "WITHHELD_ACTIVE_CAMPAIGN", kind: null, date: null, evidence: null, url: null },
      publication: { rule: "r", campaign_id: "c", withheld: ["recovery"], note: "n" } });
    const text = notEstablished(covered).join(" ");
    expect(text).not.toContain("300,000");
    expect(text).not.toMatch(/restart|resum|recover|restor|came back|back online/i);
    expect(text).toContain("not published");
  });
  it("says an estimate is not an observed restoration and a month is not a day", () => {
    const lines = notEstablished(ev({ date_precision: "month", recovery: { research_status: "EVIDENCE_FOUND", kind: "estimate", date: null, evidence: null, url: null } }));
    expect(lines.join(" ")).toContain("not an observed restoration");
    expect(lines.join(" ")).toContain("only the month");
  });
});

describe("placement, headlines and anchors", () => {
  const titled = { url: "https://a.com/x", title_original: "عنوان", title_en: "Headline", language: "ar" };
  it("a campaign-covered record never shows a headline", () => {
    const covered = ev({ sources: [titled], publication: { rule: "r", campaign_id: "c", withheld: [], note: "n" } });
    expect(headlinesAllowed(covered, sys())).toBe(false);
    expect(headlinesAllowed(ev({ sources: [titled] }), sys())).toBe(true);
  });
  it("a country-level attack record is placed for the country and shows no headline", () => {
    const attack = ev({ cause: "kinetic_strike", sources: [titled] });
    expect(placementKind(attack, sys({ kinetic: "country", reason: "r" }))).toBe("country_attack");
    expect(headlinesAllowed(attack, sys({ kinetic: "country", reason: "r" }))).toBe(false);
    expect(placementKind(ev({ geography_precision: "admin1", region_code: "XX-1" }), sys())).toBe("region");
    expect(placementKind(ev(), sys({ other: "country", reason: "r" }))).toBe("country_rule");
  });
  it("an anchor is the event id; a campaign-covered record gets one only if its id is opaque", () => {
    const pub = { rule: "r", campaign_id: "c", withheld: [], note: "n" };
    const named = ev({ event_id: "sa-2026-03-02-ras-tanura-refinery-shutdown", date: "2026-03-02", publication: pub });
    const opaque = ev({ event_id: "kw-2026-03-01-refinery-attack-zz", date: "2026-03-01", asset_class: "refinery",
                        cause: "kinetic_strike", publication: pub });
    const lookalike = ev({ event_id: "kw-2026-03-01-refinery-attack-ahmadi-port", date: "2026-03-01", asset_class: "refinery",
                           cause: "kinetic_strike", publication: pub });
    expect(eventAnchor(ev({ event_id: "us-2024-01-01-x" }), "us")).toBe("ev-us-2024-01-01-x");
    expect(eventAnchor(named, "sa")).toBeNull();
    expect(eventAnchor(opaque, "kw")).toBe("ev-kw-2026-03-01-refinery-attack-zz");
    // The build's opaque token is one to six letters or digits; anything else may be a name.
    expect(eventAnchor(lookalike, "kw")).toBeNull();
    expect(eventAnchor(opaque, "sa"), "an id from another system is not opaque here").toBeNull();
  });
  it("every served anchor is unique within its country and no covered record's named id becomes one", () => {
    let checked = 0;
    for (const id of countryIds()) {
      const events = read(`systems/${id}/events.json`).events as CountryEvent[];
      const anchors = events.map((e) => eventAnchor(e, id)).filter((x): x is string => x !== null);
      expect(new Set(anchors).size, id).toBe(anchors.length);
      for (const e of events) {
        if (e.publication && !isOpaqueAttackId(e, id)) expect(eventAnchor(e, id)).toBeNull();
        if (!e.publication) expect(eventAnchor(e, id)).toBe(`ev-${e.event_id}`);
      }
      checked += events.length;
    }
    expect(checked).toBeGreaterThan(0);
  });
});

describe("shared reader copy", () => {
  it("never says zero or no disruptions, and keeps the absence-of-evidence sentence", () => {
    for (const t of [EMPTY_CORPUS_LEAD, RESEARCH_PREVIEW_DEFINITION, noScorePlain("Bahrain")]) {
      expect(t).not.toMatch(/\b0 (disruptions|events|records)\b|no disruptions/i);
    }
    expect(EMPTY_CORPUS_LEAD).toContain("not evidence that no disruption occurred");
    expect(RESEARCH_PREVIEW_DEFINITION).toContain("the absence of a record is not evidence that no disruption occurred");
    expect(noScorePlain("Bahrain")).not.toMatch(/iteration|payload|pipeline|§/);
  });
});
