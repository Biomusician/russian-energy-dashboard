import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  COUNTRY_BRIEF_CAVEATS, GULF_BRIEF_CAVEATS, MAX_BRIEF_STATEMENTS, briefRecords, briefStatements, briefText,
  countryImpactBrief, gulfImpactBrief, metricText, tallyImpacts,
  type BriefImpacts, type BriefSourceEntry, type BriefVocabularies, type CountryBriefInput, type GulfBriefInput,
} from "./impactBrief";
import { IMPACT_BRIEF, drawCountryImpactBrief, drawGulfImpactBrief, wrapText } from "./drawImpactBrief";

/** The impact briefs, read as the pixels would carry them (iteration 22).
 *
 *  The compositor draws into a canvas that records every fillText, so each test reads what a
 *  forwarded image says, not what its input object held. */

interface Drawn { t: string; x: number; y: number }
let drawn: Drawn[] = [];
let canvases: { width: number; height: number }[] = [];
const g = globalThis as unknown as { document?: unknown };
let before: unknown;

beforeEach(() => {
  drawn = [];
  canvases = [];
  before = g.document;
  const ctx = () => ({
    font: "16px sans", fillStyle: "#000",
    measureText(this: { font: string }, t: string) {
      const m = /(\d+(?:\.\d+)?)px/.exec(this.font);
      return { width: t.length * (m ? Number(m[1]) : 16) * 0.5 };
    },
    fillText(t: string, x: number, y: number) { drawn.push({ t, x, y }); },
    fillRect() {},
  });
  g.document = { createElement: () => { const c = { width: 0, height: 0, getContext: () => ctx() }; canvases.push(c); return c; } };
});
afterEach(() => { g.document = before; });

// A sentence may be wrapped over several drawn lines, so the page is read as one run of words.
const text = () => drawn.map((d) => d.t).join(" ");

const VOCAB: BriefVocabularies = {
  cause_families: [
    { id: "kinetic", label: "Kinetic attack" }, { id: "cyber", label: "Cyber" },
    { id: "industrial_technical", label: "Industrial or technical failure" }, { id: "natural_hazard", label: "Natural hazard" },
  ],
  sectors: [{ id: "electricity", label: "Electricity" }, { id: "water", label: "Water" }, { id: "telecom", label: "Telecommunications" }],
  digital_categories: [{ id: "cyber", label: "Cyber" }, { id: "it_failure", label: "IT failure" }],
};

/** Served-shaped records carrying everything a brief must not repeat. */
const SERVED = [
  { cause_family: "kinetic", digital_category: null, civilian_service_impact: [{ service: "electricity" }],
    country_name: "Qatar", system_id: "qa", admin1: { code: "QA-ZZ", name: "Secretville" }, summary: "Strike on the Hidden Works terminal.",
    sources: [{ url: "https://example.test/hidden-works", title_en: "Hidden Works hit" }] },
  { cause_family: "cyber", digital_category: "cyber", civilian_service_impact: [{ service: "water" }, { service: "water" }, { service: "telecom" }],
    country_name: "Oman", system_id: "om", attribution: { actor: "Example Group" } },
  { cause_family: "industrial_technical", digital_category: "it_failure", civilian_service_impact: [],
    country_name: "Oman", system_id: "om" },
  { cause_family: "natural_hazard", civilian_service_impact: null, country_name: "Kuwait", system_id: "kw" },
];

const impactsOf = (records = SERVED): BriefImpacts => ({
  records: briefRecords(records), vocab: VOCAB, window: { start: "2022-01-01", end: "present" },
  limitations: ["Official sites in two countries could not be read."], latestResearch: "2026-11-19",
});

const ENTRIES: BriefSourceEntry[] = [
  { as_of: "2026-03-05", context_type: "shipping_status", claim: "Older shipping statement.", metric: null,
    sources: [{ publisher: "Agency A" }], is_latest_of_type: false },
  { as_of: "2026-09-22", context_type: "shipping_status", claim: "Transit traffic remained below its usual level.", metric: null,
    sources: [{ publisher: "Agency A" }], is_latest_of_type: true },
  { as_of: "2026-04-10", context_type: "aggregate_supply", claim: "Exports were lower than a year earlier.",
    metric: { value: 2, value_upper: 3, qualifier: "range", unit: "mb/d", basis: "estimated fall" }, sources: [{ publisher: "Agency B" }, { publisher: "Wire C" }] },
];
const TYPES = [{ id: "shipping_status", label: "Shipping, in aggregate" }, { id: "aggregate_supply", label: "Supply, in aggregate" }];

const gulf = (over: Partial<GulfBriefInput> = {}): GulfBriefInput => ({
  group: { label: "Gulf littoral", members: 8 },
  energy: { label: "Crude oil production", unit: "thousand barrels per day", year: 2024, source: "U.S. EIA",
            rows: [{ name: "Kuwait", value: "2,700 kb/d" }, { name: "Oman", value: "1,000 kb/d" }, { name: "Qatar", value: "1,300 kb/d" }],
            total: "5,000 kb/d, 6% of the world total", totalReason: null },
  impacts: impactsOf(),
  statements: briefStatements(ENTRIES, TYPES),
  confidence: { statement: "Evidence confidence describes the quality of the public evidence for this record. It is not a probability, not a measure of severity.",
                categories: [{ label: "High", meaning: "Corroborated." }, { label: "Preliminary", meaning: "Unverified." }] },
  buildDate: "2026-11-19",
  ...over,
});

const country = (over: Partial<CountryBriefInput> = {}): CountryBriefInput => ({
  name: "Iran", buildDate: "2026-11-19",
  national: { label: "Total primary energy production", value: "17 quad Btu", year: 2024, source: "U.S. EIA" },
  system: { energyEvents: 0, reportingEnvironment: "restricted", coverage: "4 of 9 source groups searched.", campaignLine: "Active-campaign safeguards apply." },
  impacts: impactsOf([]),
  regional: { label: "The Gulf and the Strait of Hormuz", statements: briefStatements(ENTRIES, TYPES) },
  confidence: null,
  ...over,
});

describe("what a brief may know about a record", () => {
  it("a brief record has a cause, an IT-failure flag and services, and nothing else", () => {
    for (const r of briefRecords(SERVED)) expect(Object.keys(r).sort()).toEqual(["cause", "itFailure", "services"]);
    expect(briefRecords(SERVED)[1].services).toEqual(["water", "telecom"]);
  });

  it("the tally follows the vocabulary's order, never the counts, and an IT failure is never cyber", () => {
    const many = [...SERVED, SERVED[3], SERVED[3], SERVED[3]];
    const t = tallyImpacts(briefRecords(many), VOCAB);
    expect(t.total).toBe(7);
    expect(t.byCause.map((r) => r.id)).toEqual(["kinetic", "cyber", "natural_hazard", "it_failure"]);
    expect(t.byCause.find((r) => r.id === "cyber")!.n).toBe(1);
    expect(t.byCause.find((r) => r.id === "it_failure")!.label).toBe("IT failure (not an attack)");
    expect(t.byCause.some((r) => r.id === "industrial_technical")).toBe(false);
    expect(t.byCause.reduce((a, r) => a + r.n, 0)).toBe(t.total);
    expect(t.byService.map((r) => [r.id, r.n])).toEqual([["electricity", 1], ["water", 1], ["telecom", 1]]);
  });

  it("a cause the vocabulary lacks is still counted, under its own id", () => {
    const t = tallyImpacts(briefRecords([{ cause_family: "new_family" }]), VOCAB);
    expect(t.byCause).toEqual([{ id: "new_family", label: "new_family", n: 1 }]);
  });
});

describe("regional context statements in a brief", () => {
  it("carries the newest statement of each type, newest first, with its date and source", () => {
    const s = briefStatements(ENTRIES, TYPES);
    expect(s.map((x) => [x.asOf, x.type])).toEqual([["2026-09-22", "Shipping, in aggregate"], ["2026-04-10", "Supply, in aggregate"]]);
    expect(s[1].source).toBe("Agency B; Wire C");
    expect(s[1].figure).toBe("2 to 3 mb/d (estimated fall)");
  });

  it("never carries more than five", () => {
    const many = Array.from({ length: 9 }, (_, i) => ({ as_of: `2026-0${i + 1}-01`, context_type: `t${i}`, claim: "c", sources: [{ publisher: "P" }] }));
    expect(briefStatements(many, [])).toHaveLength(MAX_BRIEF_STATEMENTS);
    expect(briefStatements(many, [])[0].asOf).toBe("2026-09-01");
  });

  it("a figure keeps the source's unit and qualifier", () => {
    expect(metricText({ value: 60, unit: "million barrels", basis: null })).toBe("60 million barrels");
    expect(metricText({ value: 9, qualifier: "about", unit: "percent" })).toBe("about 9 percent");
    expect(metricText({ value: 1.5, qualifier: "at_most", unit: "mb/d" })).toBe("up to 1.5 mb/d");
  });
});

describe("the Gulf impact brief, as drawn", () => {
  it("draws every caveat line, whole, and says the context is aggregate", () => {
    drawGulfImpactBrief(gulf());
    for (const c of GULF_BRIEF_CAVEATS) expect(drawn.some((d) => d.t === c), c).toBe(true);
    expect(text()).toMatch(/Aggregate regional context only/);
    expect(text()).toMatch(/no facilities, no routes, no vessels/);
    expect(text()).toMatch(/not comparable across countries/);
    expect(text()).toMatch(/later status of attacked facilities is not published/i);
    expect(text()).toMatch(/not a probability/);
    expect(text()).toMatch(/Built 19 Nov 2026/);
    expect(text()).toMatch(/Evidence window 1 Jan 2022 to the present/);
  });

  it("the caveat band is the last thing on the page, below both columns", () => {
    drawGulfImpactBrief(gulf());
    const caveatY = drawn.filter((d) => (GULF_BRIEF_CAVEATS as readonly string[]).includes(d.t)).map((d) => d.y);
    const bodyY = drawn.filter((d) => /Kuwait:|As of 22 Sep 2026/.test(d.t)).map((d) => d.y);
    expect(caveatY).toHaveLength(GULF_BRIEF_CAVEATS.length);
    expect(Math.min(...caveatY)).toBeGreaterThan(Math.max(...bodyY));
    expect(canvases[0].height).toBeGreaterThanOrEqual(IMPACT_BRIEF.minHeight);
    expect(Math.max(...drawn.map((d) => d.y))).toBeLessThan(canvases[0].height);
  });

  it("never draws a withheld place, a headline, an address or an actor: the compositor never receives them", () => {
    drawGulfImpactBrief(gulf());
    expect(text()).not.toMatch(/Secretville|Hidden Works|example\.test|Example Group|QA-ZZ/);
  });

  it("draws no per-country impact figure: moving every record to one country changes nothing", () => {
    drawGulfImpactBrief(gulf());
    const spread = text();
    drawn = [];
    drawGulfImpactBrief(gulf({ impacts: impactsOf(SERVED.map((r) => ({ ...r, country_name: "Qatar", system_id: "qa" }))) }));
    expect(text()).toBe(spread);
    // A member is named only on its national energy line.
    for (const d of drawn) if (/Kuwait|Oman|Qatar/.test(d.t)) expect(d.t).toMatch(/^(Kuwait|Oman|Qatar): [\d,]+ kb\/d$/);
    expect(text()).toMatch(/4 published records for the 8 countries together/);
  });

  it("dates every context statement and names its source; no status word is drawn", () => {
    drawGulfImpactBrief(gulf());
    expect(text()).toMatch(/As of 22 Sep 2026 · Shipping, in aggregate/);
    expect(text()).toMatch(/Source: Agency A/);
    expect(text()).not.toMatch(/Older shipping statement/);
    expect(text()).toMatch(/not a current status/);
    expect(text()).not.toMatch(/\b(is|remains|now) (open|closed)\b/i);
  });

  it("an empty corpus, a failed download and a failed context file are three different sentences, none a zero", () => {
    drawGulfImpactBrief(gulf({ impacts: impactsOf([]) }));
    expect(text()).toMatch(/No published impact record for these 8 countries.*describes this dataset, not the region/);
    expect(text()).not.toMatch(/\b0 published/);
    drawn = [];
    drawGulfImpactBrief(gulf({ impacts: "unavailable", statements: null, confidence: null }));
    expect(text()).toMatch(/impact records could not be loaded.*not a finding/);
    expect(text()).toMatch(/regional context statements could not be loaded/);
    expect(text()).toMatch(/not a probability/);
    for (const c of GULF_BRIEF_CAVEATS) expect(drawn.some((d) => d.t === c), c).toBe(true);
  });

  it("a long claim is wrapped, never cut", () => {
    const claim = Array.from({ length: 60 }, (_, i) => `word${i}`).join(" ");
    drawGulfImpactBrief(gulf({ statements: [{ asOf: "2026-09-22", type: "Shipping, in aggregate", claim, figure: null, source: "Agency A" }] }));
    const words = text().match(/word\d+/g) ?? [];
    expect(words).toHaveLength(60);
    expect(drawn.filter((d) => /word\d+/.test(d.t)).length).toBeGreaterThan(1);
  });
});

describe("the country impact brief, as drawn", () => {
  it("stays meaningful with no energy record and no impact record", () => {
    drawCountryImpactBrief(country());
    expect(text()).toMatch(/No published energy disruption record\. That describes this dataset, not Iran\./);
    expect(text()).toMatch(/No published impact record for Iran in the current reviewed corpus/);
    expect(text()).not.toMatch(/\b0 (published|records|events)/);
    expect(text()).toMatch(/Total primary energy production: 17 quad Btu \(2024, U\.S\. EIA\)/);
    expect(text()).toMatch(/4 of 9 source groups searched/);
    expect(text()).toMatch(/Active-campaign safeguards apply/);
    expect(text()).toMatch(/place, facility, operator, method, headline and any later status/);
    for (const c of COUNTRY_BRIEF_CAVEATS) expect(drawn.some((d) => d.t === c), c).toBe(true);
  });

  it("counts are said to be inside this country, and regional statements are dated", () => {
    drawCountryImpactBrief(country({ system: { energyEvents: 12, reportingEnvironment: "restricted", coverage: null, campaignLine: null }, impacts: impactsOf() }));
    expect(text()).toMatch(/12 published energy disruption records in this country's reviewed record/);
    expect(text()).toMatch(/4 published records inside Iran/);
    expect(text()).toMatch(/As of 22 Sep 2026/);
    expect(text()).not.toMatch(/Secretville|Hidden Works|Example Group/);
  });

  it("a country that is not a monitored system says so, and has no regional block unless given one", () => {
    drawCountryImpactBrief(country({ name: "United Kingdom", system: null, regional: null, national: null }));
    expect(text()).toMatch(/United Kingdom is not a monitored system on this site/);
    expect(text()).toMatch(/No published impact record for the United Kingdom/);
    expect(text()).toMatch(/a missing figure, not a zero/);
    expect(text()).not.toMatch(/REGIONAL CONTEXT/);
  });
});

describe("the brief's lines", () => {
  it("briefText reads every block in order, caveats last", () => {
    const lines = briefText(gulfImpactBrief(gulf()));
    expect(lines[0]).toBe("Gulf littoral: reported impacts and regional context");
    expect(lines.slice(-4, -1)).toEqual([...GULF_BRIEF_CAVEATS]);
    expect(briefText(countryImpactBrief(country())).slice(-3, -1)).toEqual([...COUNTRY_BRIEF_CAVEATS]);
  });

  it("wrapText breaks at spaces and keeps a long word whole", () => {
    const c = { font: "10px sans", measureText: (t: string) => ({ width: t.length * 5 }) } as unknown as CanvasRenderingContext2D;
    expect(wrapText(c, "aaaa bbbb cccc", 50)).toEqual(["aaaa bbbb", "cccc"]);
    expect(wrapText(c, "aaaaaaaaaaaaaaaaaaaaaaaa bb", 50)).toEqual(["aaaaaaaaaaaaaaaaaaaaaaaa", "bb"]);
    expect(wrapText(c, "", 50)).toEqual([]);
  });
});
