import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { beforeAll, describe, expect, it } from "vitest";
import { NO_FILTERS, activeFilters, applyFilters, decodeFilters, describeFilters, encodeFilters, toggleChoice, withFilterQuery } from "../recordFilters";
import { IMPACT_COLUMNS, impactRecordsCsv } from "../recordCsv";
import { GLOSSARY, glossaryDetail } from "../glossary";
import { hrefFor, impactsHref, routeFor } from "../router";
import { CONCEPT_ENTRIES, IMPACT_ENTRIES, VIEW_ENTRIES, regionalContextEntries, searchEntries } from "../searchIndex";
import type { Manifest } from "../manifest";
import {
  PAGE, PRESENCE_MARK, PRESENCE_NONE, activePreset, atlasFilterDefs, atlasPresets, corpusSummary, countriesPresent, groupByMonth,
  presenceCodes, presenceFill, presetQuery, presetState,
} from "./atlasModel";
import { disruptions, endDay, impactDateText, isCyber, monthHeading, startDay } from "./model";
import { forgetVocabularies, registerMethod, registerVocabularies } from "./vocab";
import type { ConfidenceMethod, ImpactRecord, ImpactsPayload } from "./types";

/** The Impact Atlas's model, routing, search and glossary (iteration 22), against the pipeline's
 *  synthetic corpus as served. Component states are in components.test.tsx; the browser is in
 *  web/e2e/impacts.e2e.ts; the mutation campaign's twins are in tests/test_iteration22_atlas.py. */

const FIX = new URL("../../../e2e/fixtures/impacts22/global/", import.meta.url);
const read = <T,>(name: string): T => JSON.parse(readFileSync(fileURLToPath(new URL(name, FIX)), "utf-8")) as T;
const payload = read<ImpactsPayload>("impacts.json");
const method = read<ConfidenceMethod>("evidence_confidence.json");
const records = disruptions(payload);
const defs = atlasFilterDefs(payload, method);
const presets = atlasPresets(payload);
const TODAY = "2026-11-19";
const shown = (query: string) => applyFilters(records, defs, decodeFilters(query, defs).state, TODAY);

beforeAll(() => {
  forgetVocabularies();
  registerVocabularies(payload.vocabularies);
  registerMethod(method);
});

describe("route", () => {
  it("?view=impacts opens the atlas, with or without filters; sys, group and compare win", () => {
    expect(routeFor("?view=impacts")).toEqual({ view: "impacts" });
    expect(routeFor("?view=impacts&f.cause=cyber")).toEqual({ view: "impacts" });
    expect(routeFor("?VIEW=impacts").view).toBe("home");
    expect(routeFor("?view=IMPACTS").view).toBe("impacts");
    expect(routeFor("?sys=us&view=impacts").view).toBe("country");
    expect(routeFor("?group=gulf&view=impacts").view).toBe("group");
    expect(routeFor("?compare=us,ca&view=impacts").view).toBe("compare");
    expect(routeFor("?view=other").view).toBe("home");
    expect(impactsHref()).toBe("?view=impacts");
    expect(impactsHref("f.cause=cyber")).toBe("?view=impacts&f.cause=cyber");
    expect(hrefFor(null)).toBe("?");
  });

  it("a filter edit keeps the view parameter", () => {
    const next = encodeFilters(defs, toggleChoice(NO_FILTERS, "cause", "cyber"));
    expect(withFilterQuery("view=impacts", next)).toBe("view=impacts&f.cause=cyber");
    expect(withFilterQuery("view=impacts&f.cause=cyber", "")).toBe("view=impacts");
  });
});

describe("filters", () => {
  it("offers the ten filters of the brief plus IT failure, with served labels", () => {
    expect(defs.map((d) => d.id)).toEqual(["date", "country", "domain", "sector", "tech", "cause", "mech", "it", "attr", "ai", "conf"]);
    const cause = defs.find((d) => d.id === "cause")!;
    expect(cause.kind === "choice" && cause.options.map((o) => o.label)).toEqual(payload.vocabularies.cause_families.map((c) => c.label));
    const conf = defs.find((d) => d.id === "conf")!;
    expect(conf.kind === "choice" && conf.options.map((o) => o.label)).toEqual(method.categories.map((c) => c.label));
  });

  it("without the method, the confidence filter still has the categories the records carry", () => {
    const conf = atlasFilterDefs(payload, null).find((d) => d.id === "conf")!;
    expect(conf.kind === "choice" && conf.options.map((o) => o.value).sort()).toEqual([...new Set(records.map((r) => r.evidence_confidence!.category))].sort());
  });

  it("the default shows every published record; nothing is hidden until the reader asks", () => {
    expect(shown("?view=impacts")).toHaveLength(records.length);
    expect(activeFilters(defs, decodeFilters("?view=impacts", defs).state)).toEqual([]);
  });

  it("the country filter is alphabetical, has no count, and a multi-country record matches each of its countries", () => {
    const country = defs.find((d) => d.id === "country")!;
    if (country.kind !== "choice") throw new Error("country is a choice filter");
    expect(country.counts).toBe(false);
    const names = country.options.map((o) => o.label);
    expect(names).toEqual(payload.countries.filter((c) => names.includes(c.name)).map((c) => c.name));
    const multi = records.find((r) => r.country_a3 === "MULTI")!;
    for (const a3 of multi.countries_a3!) expect(shown(`?f.country=${a3}`)).toContain(multi);
  });

  it("a month-precision record matches a range anywhere in its month, and nothing outside it", () => {
    const r = records.find((x) => x.date_precision === "month")!;
    expect(startDay(r)).toBe(`${r.date}-01`);
    expect(endDay(r).slice(0, 7)).toBe(r.date);
    expect(shown(`?f.date=${r.date}-15..${r.date}-20`)).toContain(r);
    expect(shown(`?f.date=..${r.date.slice(0, 4)}-01-01`).includes(r)).toBe(r.date.endsWith("-01") ? true : false);
    expect(impactDateText(r)).not.toMatch(/^\d{1,2} /);
  });

  it("records whose evidence was not assessed are their own filter bucket, not Preliminary and not dropped", () => {
    const na = { category: null, label: null, score: null, disputed: false, reason: "Cited through a discovery aid only." } as unknown as ImpactRecord["evidence_confidence"];
    const p: ImpactsPayload = { ...payload, records: records.map((r, i) => (i < 2 ? { ...r, evidence_confidence: na } : r)) };
    for (const m of [method, null]) {
      const d = atlasFilterDefs(p, m);
      const conf = d.find((x) => x.id === "conf")!;
      if (conf.kind !== "choice") throw new Error("conf is a choice filter");
      expect(conf.options.filter((o) => o.value === "NOT_ASSESSED")).toEqual([{ value: "NOT_ASSESSED", label: "Not assessed" }]);
      const only = applyFilters(disruptions(p), d, decodeFilters("?f.conf=NOT_ASSESSED", d).state, TODAY);
      expect(only.map((r) => r.impact_id)).toEqual(records.slice(0, 2).map((r) => r.impact_id));
      expect(applyFilters(disruptions(p), d, decodeFilters("?f.conf=PRELIMINARY", d).state, TODAY).some((r) => r.evidence_confidence!.category == null)).toBe(false);
      // Every record is in exactly one bucket: the buckets add up to the corpus.
      const total = conf.options.reduce((n, o) => n + applyFilters(disruptions(p), d, decodeFilters(`?f.conf=${o.value}`, d).state, TODAY).length, 0);
      expect(total).toBe(records.length);
    }
    // No such record, no such option.
    const plain = defs.find((x) => x.id === "conf")!;
    expect(plain.kind === "choice" && plain.options.some((o) => o.value === "NOT_ASSESSED")).toBe(false);
  });

  it("a cause family the taxonomy adds later is offered without a code change", () => {
    const p: ImpactsPayload = { ...payload, vocabularies: { ...payload.vocabularies,
      cause_families: [...payload.vocabularies.cause_families, { id: "authority_order", label: "Ordered by an authority", definition: "x" }] },
      records: [{ ...records[0], cause_family: "authority_order" }, ...records.slice(1)] };
    const d = atlasFilterDefs(p, method);
    const cause = d.find((x) => x.id === "cause")!;
    expect(cause.kind === "choice" && cause.options.map((o) => o.label)).toContain("Ordered by an authority");
    expect(applyFilters(disruptions(p), d, decodeFilters("?f.cause=authority_order", d).state, TODAY)).toHaveLength(1);
  });

  it("a link's unknown value is reported, not obeyed and not dropped silently", () => {
    const { state, notes } = decodeFilters("?view=impacts&f.cause=cyber,meteor&f.nosuch=1", defs);
    expect(state.choices.cause).toEqual(["cyber"]);
    expect(notes).toHaveLength(2);
  });
});

describe("presets", () => {
  it("are the six of the brief, then IT failure, each an ordinary filter state", () => {
    expect(presets.map((p) => p.label)).toEqual(["Cyber", "AI involved", "Attributed cyber", "Power-grid cyber", "Renewable cyber", "Civilian-service cyber", "IT failure"]);
    for (const p of presets) {
      const state = presetState(p, defs);
      expect(Object.keys(state.dates)).toEqual([]);
      expect(decodeFilters(`?view=impacts&${presetQuery(p, defs)}`, defs)).toEqual({ state, notes: [] });
      expect(activePreset(presets, defs, state)).toBe(p.id);
      expect(describeFilters(defs, state, TODAY).length).toBeGreaterThan(0);
    }
    expect(activePreset(presets, defs, NO_FILTERS)).toBeNull();
  });

  it("every cyber preset is a subset of the malicious-cyber records", () => {
    const cyber = records.filter(isCyber);
    expect(shown(`?${presetQuery(presets[0], defs)}`)).toEqual(cyber);
    for (const p of presets.filter((x) => /cyber/.test(x.id))) {
      for (const r of shown(`?${presetQuery(p, defs)}`)) expect(cyber).toContain(r);
    }
  });

  it("'AI involved' is every status but none-reported, and an empty result is a valid answer", () => {
    const ai = presets.find((p) => p.id === "ai")!;
    expect(ai.choices.ai.sort()).toEqual(payload.vocabularies.ai_statuses.map((s) => String(s.id)).filter((s) => s !== "NONE_REPORTED").sort());
    const none: ImpactsPayload = { ...payload, records: records.filter((r) => r.ai_involvement.status === "NONE_REPORTED") };
    const d = atlasFilterDefs(none, method);
    expect(applyFilters(disruptions(none), d, presetState(ai, d), TODAY)).toEqual([]);
  });

  it("no preset filters on evidence confidence or on a date", () => {
    for (const p of presets) expect(Object.keys(p.choices)).not.toContain("conf");
  });
});

describe("counts, order and the presence map", () => {
  it("the summary is one count for the corpus and the span of the records", () => {
    const s = corpusSummary(payload);
    expect(s.records).toBe(records.length);
    expect(s.countries).toBe(countriesPresent(records, payload.countries).length);
    expect(s.first! <= s.last!).toBe(true);
    expect(s.researched).toBe(payload.research.latest_research_date);
    expect(corpusSummary({ ...payload, records: [], attempts: payload.attempts })).toMatchObject({ records: 0, countries: 0, first: null, last: null });
  });

  it("groups by year and month without reordering; headings are in words", () => {
    const groups = groupByMonth(records);
    expect(groups.flatMap((y) => y.months.flatMap((m) => m.records))).toEqual(records);
    expect(monthHeading("2026-05")).toBe("May 2026");
    expect(PAGE).toBe(50);
  });

  it("the map marks a set of countries in one colour, whatever the counts", () => {
    const codes = presenceCodes(records);
    expect(codes).toEqual([...new Set(codes)].sort());
    const fill = presenceFill(codes);
    expect(JSON.stringify(fill).match(/#[0-9a-f]{6}/gi)).toEqual([PRESENCE_MARK, PRESENCE_NONE]);
    const doubled = presenceFill(presenceCodes([...records, ...records]));
    expect(doubled).toEqual(fill);
    expect(presenceFill([])).toBe(PRESENCE_NONE);
    expect(presenceCodes(payload.attempts)).toEqual([]);
  });
});

describe("CSV of the shown records", () => {
  it("has one row per shown record, in the shown order, from the impact allow-list", () => {
    const cyber = shown("?f.cause=cyber");
    const lines = impactRecordsCsv(cyber).slice(1).split("\r\n").filter(Boolean);
    expect(lines[0].split(",")).toEqual([...IMPACT_COLUMNS]);
    expect(lines.slice(1).map((l) => l.split(",")[0])).toEqual(cyber.map((r: ImpactRecord) => r.impact_id));
  });
});

describe("search", () => {
  const all = [...VIEW_ENTRIES, ...CONCEPT_ENTRIES];
  const first = (q: string) => searchEntries(all, q)[0]?.entry;

  it("finds the atlas and its preset views; each address is the one the preset writes", () => {
    expect(first("impact atlas")?.action).toEqual({ type: "href", href: "?view=impacts" });
    expect(first("cyber disruptions")?.action).toEqual({ type: "href", href: `?view=impacts&${presetQuery(presets[0], defs)}` });
    expect(first("AI involved")?.action).toEqual({ type: "href", href: `?view=impacts&${presetQuery(presets[1], defs)}` });
    expect(IMPACT_ENTRIES.find((e) => e.key === "view:impacts:attributed")?.action).toEqual({ type: "href", href: `?view=impacts&${presetQuery(presets[2], defs)}` });
    for (const e of IMPACT_ENTRIES) expect(routeFor((e.action as { href: string }).href).view).toBe("impacts");
  });

  it("finds the glossary's attribution and evidence-confidence entries", () => {
    expect(searchEntries(all, "evidence confidence").some((h) => h.entry.action.type === "concept" && h.entry.action.id === "evidence-confidence")).toBe(true);
    expect(searchEntries(all, "attribution").some((h) => h.entry.action.type === "concept" && h.entry.action.id === "attribution")).toBe(true);
  });

  it("offers the Gulf and Hormuz context only where the manifest has that overview", () => {
    const m = { systems: [], groups: { gulf: { label: "Gulf littoral", slug: "gulf", context: "global/gulf.json", regional_context: "global/regional_context.json", members: [], kind: "region" } } } as unknown as Manifest;
    const e = regionalContextEntries(m);
    expect(e).toHaveLength(1);
    expect(searchEntries(e, "hormuz")[0].entry.action).toEqual({ type: "group", slug: "gulf" });
    expect(e[0].label).toBe("Gulf and Hormuz context");
    expect(regionalContextEntries({ systems: [], groups: {} } as unknown as Manifest)).toEqual([]);
    expect(regionalContextEntries({ systems: [], groups: { gcc: { label: "GCC", members: [], kind: "membership" } } } as unknown as Manifest)).toEqual([]);
    // An overview page without the dated regional statements offers no such entry.
    expect(regionalContextEntries({ systems: [], groups: { gulf: { label: "Gulf littoral", slug: "gulf", context: "global/gulf.json", members: [], kind: "region" } } } as unknown as Manifest)).toEqual([]);
  });
});

describe("glossary", () => {
  const ids = ["evidence-confidence", "attribution", "attribution-confidence", "ai-involvement", "cyber-disruption", "civilian-service-impact",
    "reported-effect", "claimed", "assessed", "attributed", "disputed", "attempt", "originating-statement", "impact-atlas"];

  it("has every impact term, in plain language", () => {
    for (const id of ids) {
      const g = GLOSSARY.find((x) => x.id === id);
      expect(g, id).toBeTruthy();
      expect(g!.plain.length).toBeGreaterThan(60);
      expect(`${g!.plain} ${g!.detail}`).not.toMatch(/cyberwar|crippled|\bconfirmed\b/i);
    }
  });

  it("uses the served definition as the detail once the method has loaded, and its own wording before", () => {
    const g = GLOSSARY.find((x) => x.id === "evidence-confidence")!;
    expect(glossaryDetail(g, null)).toBe(g.detail);
    expect(glossaryDetail(g, method)).toContain(method.statement);
    const attr = GLOSSARY.find((x) => x.id === "attribution-confidence")!;
    expect(glossaryDetail(attr, method)).toContain(method.attribution.meanings.NOT_ESTABLISHED);
    const unknown = GLOSSARY.find((x) => x.id === "attribution")!;
    expect(glossaryDetail(unknown, method)).toContain("Not established");
    // A method that lacks what an entry reads falls back to the entry's own wording.
    expect(glossaryDetail(g, { statement: "", categories: [], attribution: { labels: {}, meanings: {} }, labels: {} })).toBeTruthy();
    expect(glossaryDetail(attr, { statement: "", categories: [], attribution: { labels: {}, meanings: {} }, labels: {} })).toBe(attr.detail);
  });
});
