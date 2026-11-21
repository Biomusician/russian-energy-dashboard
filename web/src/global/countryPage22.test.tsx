import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it } from "vitest";
import type { CountryBundle, CountryEvent, CountrySystem, Manifest } from "./manifest";
import { isCampaignRestricted } from "./laneCoverage";
import {
  DEFAULT_TAB, TAB_LABEL, TAB_ORDER, regionalGroupFor, resolveTab, tabFromSearch, tabHref, tabsFor, withTab, type RegionalGroup,
} from "./countryTabs";
import { NO_RECORD_IS_NOT_NO_DISRUPTION, countryOverview, impactLine, overviewText, type ImpactPresence } from "./countryOverview";
import { CountryOverview } from "./OverviewBlock";
import { EventCard, EvidenceInspector } from "./EventCard";
import { NOT_ASSESSED, NOT_ASSESSED_FALLBACK_REASON, NOT_ASSESSED_LABEL, confidenceBucket, confidenceCounts, confidenceOptions, eventConfidence, isAssessed } from "./evidence";
import { ConfidenceSummary } from "./ConfidenceSummary";
import { countryFilters } from "./countryFilters";
import { CONFIDENCE_IS_NOT, RESEARCH_PREVIEW_DEFINITION } from "./countryCopy";
import {
  ATTEMPTS_NOT_IN_FILE, EXPORT_ROW_LIMIT, causeCounts, countryImpacts, impactExportRow, impactExportSummary, impactFiles, impactFilters, impactOrder,
} from "./countryImpactModel";
import { CountryImpacts, impactPresence, researchRanText } from "./CountryImpacts";
import { latestOfEachType, regionalNote } from "./CountryRegional";
import { exportPreviewLine } from "./countryExport";
import { applyFilters, toggleChoice, NO_FILTERS } from "./recordFilters";
import * as sharedModel from "./impacts/model";
import { forgetVocabularies, registerMethod, registerVocabularies } from "./impacts/vocab";
import type { ConfidenceMethod, EvidenceConfidence, ImpactRecord, ImpactsPayload, RegionalContext } from "./impacts/types";

/** Country pages, iteration 22: the overview block's states, the tab's place in the address, the
 *  optional confidence chip, and the impact tab's model.
 *
 *  Systems are the served payloads (the layer that ships); impact records are the pipeline's
 *  synthetic fixture as served (web/e2e/fixtures/impacts22). Every impact record here is invented. */

const DATA = new URL("../../public/data/", import.meta.url);
const FIX = new URL("../../e2e/fixtures/impacts22/global/", import.meta.url);
const readAt = <T,>(base: URL, p: string): T => JSON.parse(readFileSync(fileURLToPath(new URL(p, base)), "utf-8")) as T;
const manifest = readAt<Manifest>(DATA, "global/manifest.json");
const COUNTRIES = manifest.systems.filter((s) => s.kind === "country").map((s) => s.id);
const system = (id: string) => readAt<CountrySystem>(DATA, `systems/${id}/system.json`);
const events = (id: string) => readAt<{ events: CountryEvent[] }>(DATA, `systems/${id}/events.json`).events;
const payload = readAt<ImpactsPayload>(FIX, "impacts.json");
const context = readAt<RegionalContext>(FIX, "regional_context.json");
const method = readAt<ConfidenceMethod>(FIX, "evidence_confidence.json");

const text = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/&amp;/g, "&").replace(/&#x27;/g, "'").replace(/&quot;/g, "\"").replace(/\s+/g, " ").trim();
const NOT_LOADED: ImpactPresence = { state: "not_loaded" };
const ready = (records: number, attempts = 0): ImpactPresence => ({ state: "ready", records, attempts, latestResearch: "2026-11-19" });
const GULF: RegionalGroup = { id: "gulf_littoral", label: "Gulf littoral", slug: "gulf" };

const SYSTEMS = Object.fromEntries(COUNTRIES.map((id) => [id, system(id)]));
const zeroRestricted = COUNTRIES.map((id) => SYSTEMS[id]).filter((s) => s.event_summary.recorded_events === 0 && isCampaignRestricted(s));
const withRecords = COUNTRIES.map((id) => SYSTEMS[id]).filter((s) => s.event_summary.recorded_events > 0);
const unrestricted = withRecords.filter((s) => !isCampaignRestricted(s));

/** A country with no published record and no campaign: none is served today, so one is made from a
 *  served unrestricted system by emptying its record. */
function zeroUnrestricted(): CountrySystem {
  const s = structuredClone(unrestricted[0]);
  s.event_summary = { ...s.event_summary, recorded_events: 0, episodes: 0 };
  return s;
}

const CONF = {
  category: "HIGH", label: "High", score: 84, disputed: false,
  components: {
    directness: { tier: "direct", points: 40 }, origins: { count: 2, points: 16, basis: "publishers" }, effect: { specificity: "described", points: 8 },
    opened: { points: 10 }, contemporaneous: { points: 10 },
  },
  reasons: ["Direct authoritative statement", "2 publishers cited; their origins are not yet reviewed"],
} as EvidenceConfidence;

/** The served form of a record the build did not assess. */
const NOT_ASSESSED_VALUE = { category: null, reason: "Cited through a discovery aid only; a primary source is not yet attached." };

beforeAll(() => {
  forgetVocabularies();
  registerVocabularies(payload.vocabularies);
  registerMethod(method);
});

describe("overview: what is published", () => {
  it("the served payload has the cases these tests rest on", () => {
    expect(zeroRestricted.length).toBeGreaterThan(0);
    expect(unrestricted.length).toBeGreaterThan(0);
  });

  it("no record under campaign safeguards: says so, says why, and that no record is not no disruption", () => {
    for (const s of zeroRestricted) {
      const o = countryOverview(s, NOT_LOADED, null);
      expect(o.published).toMatch(/^No energy-disruption record is published for /);
      expect(o.publishedNote).toContain("only disruptions that meet the inclusion rule are published");
      expect(o.publishedNote).not.toContain("strict");
      expect(o.publishedNote).toContain("attack-campaign safeguards apply");
      expect(o.publishedNote).toContain(NO_RECORD_IS_NOT_NO_DISRUPTION);
      // Nothing is counted on a page with no record: not records, not anything held.
      expect(overviewText(o).join(" ")).not.toMatch(/\d/);
    }
  });

  it("no record and no campaign: the same lead, with no safeguard given as a reason", () => {
    const o = countryOverview(zeroUnrestricted(), NOT_LOADED, null);
    expect(o.published).toMatch(/^No energy-disruption record is published for /);
    expect(o.publishedNote).toContain("only disruptions that meet the inclusion rule are published");
    expect(o.publishedNote).not.toContain("safeguards");
    expect(o.publishedNote).toContain(NO_RECORD_IS_NOT_NO_DISRUPTION);
    expect(o.withheld.join(" ")).not.toContain("attacks");
    expect(o.withheld.join(" ")).toContain("Records still in review");
  });

  it("an unfinished or blocked search is given as a reason; a finished one is not", () => {
    const s = zeroUnrestricted();
    s.research_freshness = { ...s.research_freshness, completeness: "complete", lane_states: { declared_query_set_run: 3 } };
    expect(countryOverview(s, NOT_LOADED, null).publishedNote).toBe(`Why: only disruptions that meet the inclusion rule are published. ${NO_RECORD_IS_NOT_NO_DISRUPTION}`);
    s.research_freshness = { ...s.research_freshness, completeness: "partial" };
    // The research state comes first: it is the most specific reason (iteration 23, C11).
    expect(countryOverview(s, NOT_LOADED, null).publishedNote).toMatch(/^Why: the latest search pass is partial and only disruptions/);
    s.research_freshness = { ...s.research_freshness, lane_states: { blocked_by_source: 1 } };
    expect(countryOverview(s, NOT_LOADED, null).publishedNote).toMatch(/^Why: a source group could not be read in the latest search/);
    s.research_log = { ...s.research_log, passes: [] };
    expect(countryOverview(s, NOT_LOADED, null).publishedNote).toContain("no systematic search has been run yet");
  });

  it("with records: the served count, and never the empty-page sentence", () => {
    for (const s of withRecords) {
      const o = countryOverview(s, NOT_LOADED, null);
      expect(o.published.startsWith(`${s.event_summary.recorded_events} reviewed energy-disruption record`)).toBe(true);
      expect(overviewText(o).join(" ")).not.toContain(NO_RECORD_IS_NOT_NO_DISRUPTION);
      // The campaign limits are said once, in the part about what is not published.
      expect(o.withheld.join(" ").includes("While attacks on energy facilities are reported")).toBe(isCampaignRestricted(s));
      expect(o.publishedNote).toBe("What was reported and found, not everything that happened.");
    }
  });
});

describe("overview: what else is here", () => {
  const s = SYSTEMS[zeroRestricted[0].system_id];

  it("the impact line has a state for not read, none, some and failed, and counts only once read", () => {
    expect(impactLine(s.name, NOT_LOADED)).not.toMatch(/\d/);
    expect(impactLine(s.name, { state: "loading" })).toBe(impactLine(s.name, NOT_LOADED));
    expect(impactLine(s.name, ready(0))).toMatch(/^no impact record yet/);
    expect(impactLine(s.name, ready(0))).not.toMatch(/\d/);
    expect(impactLine(s.name, ready(1))).toBe("1 reviewed impact record, in a separate, non-scored corpus.");
    expect(impactLine(s.name, ready(12, 1))).toBe("12 reviewed impact records and 1 documented attempt, in a separate, non-scored corpus.");
    expect(impactLine(s.name, { state: "failed" })).toContain("could not be loaded");
  });

  it("an attempt alone is never said to be a record", () => {
    expect(impactLine(s.name, ready(0, 2))).toBe("2 documented attempts, in a separate, non-scored corpus.");
  });

  it("the regional link is there only for a system in the regional group, second in the list", () => {
    const withIt = countryOverview(s, NOT_LOADED, GULF).known.map((k) => k.tab);
    const without = countryOverview(s, NOT_LOADED, null).known.map((k) => k.tab);
    expect(withIt).toEqual(["impacts", "regional", "context", "research"]);
    expect(without).toEqual(["impacts", "context", "research"]);
  });

  it("the impact count never replaces or joins the published count", () => {
    for (const sys of withRecords) {
      const a = countryOverview(sys, NOT_LOADED, null);
      const b = countryOverview(sys, ready(987, 3), null);
      expect(b.published).toBe(a.published);
      expect(b.publishedNote).toBe(a.publishedNote);
      expect(b.published).not.toContain("987");
    }
  });
});

describe("overview: what is withheld", () => {
  it("under campaign safeguards it is the same whatever a research pass logged", () => {
    const restricted = COUNTRIES.map((id) => SYSTEMS[id]).filter(isCampaignRestricted);
    expect(restricted.length).toBeGreaterThan(0);
    for (const s of restricted) {
      const plain = overviewText(countryOverview(s, NOT_LOADED, GULF));
      for (const underReview of [true, false, undefined]) {
        const seeded = structuredClone(s);
        seeded.research_log.passes = seeded.research_log.passes.map((p) => ({
          ...p, outcome: { candidates: 4817, held: 3929, rejected: 5743, accepted: 6151 },
          ...(underReview === undefined ? {} : { under_review: underReview }),
        }));
        const got = overviewText(countryOverview(seeded, NOT_LOADED, GULF));
        expect(got, `${s.system_id} under_review=${underReview}`).toEqual(plain);
        expect(got.join(" ")).not.toMatch(/4817|3929|5743|6151/);
      }
      expect(plain.join(" ")).toContain("whether, or how many, records are in review");
    }
  });

  it("the place of an attack is listed as withheld only where the system keeps attacks at country level", () => {
    for (const id of COUNTRIES) {
      const s = SYSTEMS[id];
      const w = countryOverview(s, NOT_LOADED, null).withheld.join(" ");
      expect(w.includes("where in the country an attack happened"), id)
        .toBe(isCampaignRestricted(s) && s.geography.precision_policy?.kinetic === "country");
      expect(w).toContain("coordinates");
    }
  });

  it("the rendered block has the three parts in order, and links that are real addresses", () => {
    const s = zeroRestricted[0];
    const html = renderToStaticMarkup(<CountryOverview sys={s} impacts={ready(1)} regional={GULF} onTab={() => undefined} />);
    const t = text(html);
    const at = (x: string) => t.indexOf(x);
    expect(at("Published here")).toBeGreaterThan(-1);
    expect(at("Published here")).toBeLessThan(at("Also on this page"));
    expect(at("Also on this page")).toBeLessThan(at("Not published, and why"));
    expect(html).toContain(`href="?sys=${s.system_id}&amp;tab=impacts"`);
    expect(html).toContain(`href="?sys=${s.system_id}&amp;tab=regional"`);
    // Links, not buttons: a tab's own button keeps its name to itself.
    expect(html).not.toContain("<button");
  });
});

describe("tabs in the address", () => {
  it("reads a tab, ignores one that does not exist, and never throws on reader input", () => {
    expect(tabFromSearch("?sys=ir&tab=impacts")).toBe("impacts");
    expect(tabFromSearch("sys=ir&tab=REGIONAL")).toBe("regional");
    expect(tabFromSearch("?sys=ir")).toBeNull();
    expect(tabFromSearch("?sys=ir&tab=constructor")).toBeNull();
    expect(tabFromSearch("?sys=ir&tab=")).toBeNull();
  });

  it("writes the tab without touching the other parameters, and never writes the default", () => {
    expect(withTab("sys=us&r=US-TX&f.cause=technical,unknown&f.date=90d", "impacts"))
      .toBe("sys=us&r=US-TX&f.cause=technical,unknown&f.date=90d&tab=impacts");
    expect(withTab("sys=us&tab=impacts&r=US-TX", DEFAULT_TAB)).toBe("sys=us&r=US-TX");
    expect(withTab("?sys=us&tab=impacts", "research")).toBe("sys=us&tab=research");
    expect(tabHref("ir", "impacts")).toBe("?sys=ir&tab=impacts");
    expect(tabHref("ir", DEFAULT_TAB)).toBe("?sys=ir");
    // Round trip for every tab.
    for (const t of TAB_ORDER) expect(tabFromSearch(withTab("sys=ir", t)) ?? DEFAULT_TAB).toBe(t);
  });

  it("the regional tab exists exactly for the members of the manifest's regional group", () => {
    const group = Object.values(manifest.groups ?? {}).find((g) => g.slug === "gulf");
    expect(group, "the served manifest has no group with the regional overview").toBeTruthy();
    for (const id of COUNTRIES) {
      const g = regionalGroupFor(manifest, id);
      expect(!!g, id).toBe(group!.members.includes(id));
      expect(tabsFor(g).includes("regional"), id).toBe(group!.members.includes(id));
    }
    expect(regionalGroupFor({ groups: undefined }, "ir")).toBeNull();
    expect(regionalGroupFor(null, "ir")).toBeNull();
  });

  it("a tab this system does not have falls back to the country's own record", () => {
    expect(resolveTab("regional", tabsFor(null))).toBe("events");
    expect(resolveTab("regional", tabsFor(GULF))).toBe("regional");
    expect(resolveTab(null, tabsFor(null))).toBe("events");
    expect(TAB_LABEL.events).toBe("Published energy disruptions");
  });
});

describe("evidence confidence on a country event", () => {
  const id = unrestricted[0].system_id;
  const sys = SYSTEMS[id];
  const all = events(id);
  const bundle = { system: sys, events: all, episodes: [], regions: { type: "FeatureCollection", features: [] } } as CountryBundle;
  const bare = (e: CountryEvent): CountryEvent => { const c = { ...e } as CountryEvent & { evidence_confidence?: unknown }; delete c.evidence_confidence; return c; };
  const withConf = (e: CountryEvent, c: unknown): CountryEvent => ({ ...e, evidence_confidence: c } as CountryEvent);
  const card = (e: CountryEvent) => text(renderToStaticMarkup(<ul><EventCard e={e} bundle={bundle} /></ul>));

  it("no chip when the field is absent, null or malformed: absent is never drawn as a category", () => {
    const e = bare(all[0]);
    expect(eventConfidence(e)).toBeNull();
    expect(card(e)).not.toContain("Evidence confidence");
    expect(card(withConf(e, null))).not.toContain("Evidence confidence");
    expect(card(withConf(e, { category: "HIGH" }))).not.toContain("Evidence confidence");
    expect(card(withConf(e, { ...CONF, category: "" }))).not.toContain("Evidence confidence");
  });

  it("the chip states the category in words when the field is served", () => {
    const t = card(withConf(bare(all[0]), CONF));
    expect(t).toContain("Evidence confidence: High");
    expect(t).toContain("Why?");
  });

  it("the inspector lists the five components and always carries the sentence about what confidence is not", () => {
    const e = withConf(bare(all[0]), CONF);
    const t = text(renderToStaticMarkup(<EvidenceInspector id="x" e={e} bundle={bundle} onClose={() => undefined} />));
    expect(t).toContain("How strong the evidence is");
    for (const c of method.components) expect(t, c.id).toContain(c.label);
    // The record's own served reasons, as served: nothing about origins is composed here.
    for (const r of CONF.reasons) expect(t).toContain(r);
    expect(t).toContain("not a probability");
    expect(t).toContain(method.statement);
    // Before the method file is read, the fixed copy stands in.
    forgetVocabularies();
    const before = text(renderToStaticMarkup(<EvidenceInspector id="x" e={e} bundle={bundle} onClose={() => undefined} />));
    expect(before).toContain(CONFIDENCE_IS_NOT);
    registerVocabularies(payload.vocabularies);
    registerMethod(method);
    // And a record without the field has no such section.
    const none = text(renderToStaticMarkup(<EvidenceInspector id="x" e={bare(all[0])} bundle={bundle} onClose={() => undefined} />));
    expect(none).not.toContain("How strong the evidence is");
  });

  it("the confidence filter lists its categories in the method's order, from the served summary", () => {
    const cats = ["PRELIMINARY", "HIGH", "DISPUTED", "MODERATE"];
    const evs = all.slice(0, 4).map((e, i) => withConf(bare(e), { ...CONF, category: cats[i], label: cats[i][0] + cats[i].slice(1).toLowerCase() }));
    const served = { ...sys, evidence_confidence_summary: { by_category: { HIGH: 1, MODERATE: 1, LIMITED: 0, PRELIMINARY: 1, DISPUTED: 1 } } } as CountrySystem;
    const order = confidenceOptions(served, evs);
    expect(order?.map((o) => o.value)).toEqual(["HIGH", "MODERATE", "PRELIMINARY", "DISPUTED"]);
    const def = countryFilters(served, evs, order).defs.find((d) => d.id === "conf");
    expect(def && def.kind === "choice" ? def.options.map((o) => o.label) : null).toEqual(["High", "Moderate", "Preliminary", "Disputed"]);
    // No summary served: the caller passes nothing and the filter keeps its own (alphabetical) order.
    expect(confidenceOptions({ ...sys, evidence_confidence_summary: undefined } as CountrySystem, evs)).toBeUndefined();
    const plain = countryFilters(sys, evs).defs.find((d) => d.id === "conf");
    expect(plain && plain.kind === "choice" ? plain.options.map((o) => o.label) : null).toEqual(["Disputed", "High", "Moderate", "Preliminary"]);
  });

  describe("a record the build did not assess (category null)", () => {
    const na = withConf(bare(all[0]), NOT_ASSESSED_VALUE);

    it("is a state of its own: not absent, and not a category", () => {
      const c = eventConfidence(na);
      expect(c).toEqual({ category: null, reason: NOT_ASSESSED_VALUE.reason });
      expect(c && isAssessed(c)).toBe(false);
      expect(confidenceBucket(na)).toBe(NOT_ASSESSED);
      expect(confidenceBucket(bare(all[0]))).toBeNull();
      expect(confidenceBucket(withConf(bare(all[0]), CONF))).toBe("HIGH");
    });

    it("the card says Not assessed and why, and never names a category", () => {
      const t = card(na);
      expect(t).toContain("Evidence confidence: Not assessed");
      expect(t).toContain(NOT_ASSESSED_VALUE.reason);
      expect(t).not.toMatch(/Evidence confidence: (Preliminary|Limited|Moderate|High|Disputed)/);
      expect(t).not.toMatch(/\/\s?100|\d\s?%/);
      // No reason served: still Not assessed, and it says no reason was given.
      const noReason = card(withConf(bare(all[0]), { category: null }));
      expect(noReason).toContain("Evidence confidence: Not assessed");
      expect(noReason).toContain(NOT_ASSESSED_FALLBACK_REASON);
    });

    it("the inspector says Not assessed with the reason and the sentence about what confidence is not", () => {
      const t = text(renderToStaticMarkup(<EvidenceInspector id="x" e={na} bundle={bundle} onClose={() => undefined} />));
      expect(t).toContain("How strong the evidence is");
      expect(t).toContain("Evidence confidence: Not assessed");
      expect(t).toContain(NOT_ASSESSED_VALUE.reason);
      expect(t).toContain("Not assessed is not a low category");
      expect(t).toContain(method.statement);
      expect(t).not.toMatch(/Evidence confidence: (Preliminary|Limited|Moderate|High|Disputed)/);
    });

    it("is its own choice in the filter, listed last, and selects exactly those records", () => {
      const evs = [withConf(bare(all[0]), CONF), withConf(bare(all[1]), { ...CONF, category: "PRELIMINARY", label: "Preliminary" }),
        withConf(bare(all[2]), NOT_ASSESSED_VALUE), bare(all[3])];
      const served = { ...sys, evidence_confidence_summary: { by_category: { HIGH: 1, MODERATE: 0, LIMITED: 0, PRELIMINARY: 1, DISPUTED: 0 } } } as CountrySystem;
      const order = confidenceOptions(served, evs);
      expect(order).toEqual([{ value: "HIGH", label: "High" }, { value: "PRELIMINARY", label: "Preliminary" }, { value: NOT_ASSESSED, label: "Not assessed" }]);
      const filters = countryFilters(served, evs, order);
      const picked = (v: string) => applyFilters(evs, filters.defs, toggleChoice(NO_FILTERS, "conf", v), "2026-11-19");
      expect(picked(NOT_ASSESSED)).toEqual([evs[2]]);
      expect(picked("PRELIMINARY")).toEqual([evs[1]]);
      // Without a served order the bucket is still offered.
      const plain = countryFilters(sys, evs).defs.find((d) => d.id === "conf");
      expect(plain && plain.kind === "choice" ? plain.options.map((o) => o.value).sort() : null).toEqual(["HIGH", NOT_ASSESSED, "PRELIMINARY"].sort());
    });

    it("the per-country summary counts it on its own line, in the method's order, with the not-comparable sentence", () => {
      const evs = [withConf(bare(all[0]), CONF), withConf(bare(all[1]), { ...CONF, category: "PRELIMINARY", label: "Preliminary" }),
        withConf(bare(all[2]), NOT_ASSESSED_VALUE), withConf(bare(all[3]), NOT_ASSESSED_VALUE), bare(all[4])];
      const served = { ...sys, evidence_confidence_summary: { by_category: { HIGH: 1, MODERATE: 0, LIMITED: 0, PRELIMINARY: 1, DISPUTED: 0 } } } as CountrySystem;
      expect(confidenceCounts(served, evs)).toEqual([
        { value: "HIGH", label: "High", n: 1 }, { value: "PRELIMINARY", label: "Preliminary", n: 1 }, { value: NOT_ASSESSED, label: "Not assessed", n: 2 },
      ]);
      const t = text(renderToStaticMarkup(<ConfidenceSummary bundle={{ ...bundle, system: served, events: evs }} />));
      expect(t).toContain("High: 1");
      expect(t).toContain("Preliminary: 1");
      expect(t).toContain("Not assessed: 2");
      expect(t).toContain("describes the citations these records carry");
      expect(t).toContain("not comparable across countries");
      expect(t).not.toMatch(/\/\s?100|\d\s?%/);
      // No record carries the field: no summary at all, not a row of zeros.
      expect(renderToStaticMarkup(<ConfidenceSummary bundle={{ ...bundle, events: evs.map(bare) }} />)).toBe("");
    });
  });
});

describe("the impact tab's model", () => {
  /** Every fixture record moved into one system, so a country has a list worth filtering. */
  const many: ImpactsPayload = { ...payload, records: payload.records.map((r) => ({ ...r, system_id: "ir" })),
                                 attempts: payload.attempts.map((r) => ({ ...r, system_id: "ir" })) };
  const itFailure = (r: ImpactRecord): ImpactRecord => ({ ...r, cause_family: "industrial_technical", cyber_mechanism: "it_outage_affecting_operations" });

  it("a system gets its own records in date order, and attempts apart", () => {
    for (const id of COUNTRIES) {
      const { records, attempts } = countryImpacts(payload, id);
      expect(records.every((r) => r.system_id === id && r.record_kind === "disruption"), id).toBe(true);
      expect(attempts.every((r) => r.record_kind !== "disruption")).toBe(true);
    }
    expect(countryImpacts(payload, "ir").records.length).toBe(payload.records.filter((r) => r.system_id === "ir").length);
    const got = countryImpacts(many, "ir");
    expect(got.records.length).toBe(payload.records.length);
    expect(got.attempts.length).toBe(payload.attempts.length);
    expect(got.records.some((r) => got.attempts.includes(r))).toBe(false);
    const order = impactOrder(got.records).map((r) => r.date);
    expect(order).toEqual([...order].sort().reverse());
  });

  it("a system with no impact record gets an empty list, not someone else's", () => {
    expect(countryImpacts(payload, "zz")).toEqual({ records: [], attempts: [] });
  });

  it("the filters are cause, sector, technology, attribution, AI and confidence, each only where it can filter", () => {
    const { records } = countryImpacts(many, "ir");
    const ids = impactFilters(many, records, method.categories.map((c) => c.id)).map((d) => d.id);
    // "it" is the shared IT-failure filter: a separate choice from the malicious cause, never inside it.
    expect(ids).toEqual(["cause", "it", "sector", "tech", "attr", "ai", "conf"]);
    // One record: nothing can be filtered, so no filter is offered.
    expect(impactFilters(payload, countryImpacts(payload, "ir").records)).toEqual([]);
    const conf = impactFilters(many, records, method.categories.map((c) => c.id)).find((d) => d.id === "conf");
    const order = method.categories.map((c) => c.id);
    const got = conf && conf.kind === "choice" ? conf.options.map((o) => o.value) : [];
    expect(got).toEqual(order.filter((c) => got.includes(c)));
  });

  it("an IT failure is not cyber: its own filter, and the cyber choice leaves it out", () => {
    const base = countryImpacts(many, "ir").records;
    const records = [itFailure(base[0]), ...base.slice(1)];
    const defs = impactFilters(many, records);
    expect(defs.map((d) => d.id)).toContain("it");
    const cyber = applyFilters(records, defs, toggleChoice(NO_FILTERS, "cause", "cyber"), "2026-11-19");
    expect(cyber.length).toBeGreaterThan(0);
    expect(cyber.every((r) => r.cause_family === "cyber")).toBe(true);
    expect(cyber).not.toContain(records[0]);
    const it_ = applyFilters(records, defs, toggleChoice(NO_FILTERS, "it", "it_failure"), "2026-11-19");
    expect(it_).toEqual([records[0]]);
    // No IT failure in the list: no IT-failure filter.
    expect(impactFilters(many, base.filter((r) => r.cyber_mechanism !== "it_outage_affecting_operations" || r.cause_family === "cyber")).map((d) => d.id)).not.toContain("it");
  });

  it("an impact record that was not assessed is its own choice in the confidence filter, listed last", () => {
    const base = countryImpacts(many, "ir").records;
    const na = { ...base[0], evidence_confidence: { ...base[0].evidence_confidence!, category: null, label: null, score: null, reason: "Not yet assessed." } } as ImpactRecord;
    const records = [na, ...base.slice(1)];
    const defs = impactFilters(many, records, method.categories.map((c) => c.id));
    const conf = defs.find((d) => d.id === "conf");
    const options = conf && conf.kind === "choice" ? conf.options : [];
    expect(options[options.length - 1]).toEqual({ value: NOT_ASSESSED, label: "Not assessed" });
    expect(applyFilters(records, defs, toggleChoice(NO_FILTERS, "conf", NOT_ASSESSED), "2026-11-19")).toEqual([na]);
    expect(applyFilters(records, defs, toggleChoice(NO_FILTERS, "conf", "PRELIMINARY"), "2026-11-19")).not.toContain(na);
    // The country pages and the shared impact components use one key and one label for it.
    expect(NOT_ASSESSED).toBe(sharedModel.NOT_ASSESSED);
    expect(NOT_ASSESSED_LABEL).toBe(sharedModel.NOT_ASSESSED_LABEL);
  });

  it("no cause family is typed here: one the taxonomy adds later is counted and can be chosen", () => {
    const base = countryImpacts(many, "ir").records;
    const withNew: ImpactsPayload = { ...many, vocabularies: { ...many.vocabularies,
      cause_families: [...(many.vocabularies.cause_families ?? []), { id: "example_new_family", label: "Example new family" }] } };
    const records = [{ ...base[0], cause_family: "example_new_family" }, ...base.slice(1)];
    expect(causeCounts(withNew, records).find((c) => c.id === "example_new_family")).toEqual({ id: "example_new_family", label: "Example new family", n: 1 });
    const cause = impactFilters(withNew, records).find((d) => d.id === "cause");
    expect(cause && cause.kind === "choice" ? cause.options.some((o) => o.value === "example_new_family" && o.label === "Example new family") : false).toBe(true);
    // Not yet in the served vocabulary: still counted and selectable, under the key in plain words.
    expect(causeCounts(many, records).find((c) => c.id === "example_new_family")?.label).toBe("Example new family");
    expect(impactExportRow(withNew, records[0])).toContain("Example new family");
  });

  it("cause counts are inside the list, in the vocabulary's order, and add up", () => {
    const { records } = countryImpacts(many, "ir");
    const counts = causeCounts(many, records);
    expect(counts.reduce((n, c) => n + c.n, 0)).toBe(records.length);
    const vocab = (many.vocabularies.cause_families ?? []).map((e) => String(e.id));
    expect(counts.map((c) => c.id)).toEqual(vocab.filter((id) => counts.some((c) => c.id === id)));
    expect(counts.every((c) => c.n > 0)).toBe(true);
  });

  it("an abstracted record's export row has no place, operator or headline, whatever the record carries", () => {
    const kinetic = payload.records.find((r) => r.publication_policy === "country_abstracted");
    expect(kinetic).toBeTruthy();
    const leaky: ImpactRecord = {
      ...kinetic!, admin1: { code: "XX-01", name: "SECRETPROVINCE" }, summary: "SECRETOPERATOR plant at SECRETTOWN was hit.",
      sources: kinetic!.sources.map((s) => ({ ...s, title_original: "SECRETHEADLINE", title_en: "SECRETHEADLINE", publisher: "SECRETPUBLISHER" })),
    };
    const row = impactExportRow(payload, leaky);
    expect(row).not.toMatch(/SECRET/);
    expect(row).toContain("place withheld");
    // The policy field alone is enough, and so is the cause alone.
    expect(impactExportRow(payload, { ...leaky, cause_family: "industrial_technical" })).not.toMatch(/SECRET/);
    expect(impactExportRow(payload, { ...leaky, publication_policy: "standard" })).not.toMatch(/SECRET/);
    const summary = impactExportSummary("Ukraine", [leaky], [], payload, method.statement);
    expect([summary.title, ...summary.lines, ...summary.rows, summary.more ?? ""].join(" ")).not.toMatch(/SECRET/);
  });

  it("the export summary carries the separate-corpus line, the counts, the confidence sentence and a bounded list", () => {
    const { records, attempts } = countryImpacts(many, "ir");
    const s = impactExportSummary("Iran", records, attempts, many, method.statement);
    const all = s.lines.join(" ");
    expect(all).toContain("separate, non-scored corpus");
    expect(all).toContain(`${records.length} reviewed impact records for Iran, by cause family`);
    expect(all).toContain("not comparable across countries");
    expect(all).toContain(method.statement);
    expect(all).toContain("listed apart and not counted above");
    expect(s.rows.length).toBe(EXPORT_ROW_LIMIT);
    expect(s.more).toContain(String(records.length - EXPORT_ROW_LIMIT));
    // No statement served: the fixed sentence stands in. No record: said as the corpus's state.
    expect(impactExportSummary("Iran", records, [], many).lines.join(" ")).toContain(CONFIDENCE_IS_NOT);
    const none = impactExportSummary("Canada", [], [], many);
    expect(none.lines.join(" ")).toContain("No reviewed impact record is published for Canada yet");
    expect(none.rows).toEqual([]);
    expect(none.lines.join(" ")).not.toMatch(/\b0\b/);
  });

  it("the CSV holds the records shown and its note names the corpus", () => {
    const { records } = countryImpacts(many, "ir");
    const f = impactFiles("ir", "Iran", records.slice(0, 3), records.length, ["Cause: Cyber"], many, "2026-11-19");
    expect(f.csvName).toBe(`edm-ir-impacts-${many.as_of}.csv`);
    expect(f.csv.trim().split("\r\n").length).toBe(4);
    expect(f.readme).toContain(`Records in this file: 3 of ${records.length}`);
    expect(f.readme).toContain("separate, non-scored corpus");
    expect(f.readme).toContain("- Cause: Cyber");
  });

  it("the README says attempts are not in the file and carries the corpus research limitations (cyber S-5)", () => {
    const { records } = countryImpacts(many, "ir");
    const limits = ["The corpus is a sample, not a census: a test limitation.", "A second research limitation."];
    const f = impactFiles("ir", "Iran", records.slice(0, 2), records.length, [],
                          { ...many, research: { ...many.research, limitations: limits } }, "2026-11-19");
    expect(f.readme).toContain(`- ${ATTEMPTS_NOT_IN_FILE}`);
    expect(ATTEMPTS_NOT_IN_FILE).toContain("not in this file");
    for (const l of limits) expect(f.readme).toContain(`- ${l}`);
    // A payload that carries no research block still gets the attempts line, and nothing breaks.
    const bare = impactFiles("ir", "Iran", [], 0, [], { as_of: many.as_of, caveats: many.caveats }, "2026-11-19");
    expect(bare.readme).toContain(ATTEMPTS_NOT_IN_FILE);
  });
});

describe("the impact and regional tabs", () => {
  const sys = SYSTEMS[zeroRestricted[0].system_id];
  const render = (el: React.ReactElement) => text(renderToStaticMarkup(el));

  it("the tab says what the list is before it lists anything, in every state", () => {
    for (const state of [{ state: "not_loaded" }, { state: "loading" }, { state: "failed" }] as const) {
      const t = render(<CountryImpacts sys={sys} impacts={state} today="2026-11-19" />);
      expect(t).toContain("separate, non-scored corpus");
      expect(t).toContain("enter no count or index");
    }
    expect(render(<CountryImpacts sys={sys} impacts={{ state: "failed" }} today="2026-11-19" />)).toContain("could not be loaded");
  });

  it("an empty list describes the corpus, not the country, and says when the research last ran", () => {
    const t = render(<CountryImpacts sys={sys} impacts={{ state: "ready", payload, records: [], attempts: [] }} today="2026-11-19" />);
    expect(t).toContain(`No reviewed impact record is published for ${sys.name} yet. That describes this corpus, not ${sys.name}.`);
    expect(t).toContain("The impact research last ran on 19 Nov 2026");
    expect(t).not.toMatch(/\b0 (records|impact)/);
    expect(researchRanText({ research: { ...payload.research, latest_research_date: null } })).toBe("No impact research pass has been logged yet.");
  });

  it("attempts are listed under their own heading and never in the count", () => {
    const records = payload.records.slice(0, 2);
    const t = render(<CountryImpacts sys={sys} impacts={{ state: "ready", payload, records, attempts: payload.attempts }} today="2026-11-19" />);
    expect(t).toContain("Showing 2 of 2 reviewed impact records");
    expect(t).toContain(payload.attempts_label ?? "ATTEMPT");
    expect(impactPresence({ state: "ready", payload, records, attempts: payload.attempts })).toEqual({ state: "ready", records: 2, attempts: 1, latestResearch: payload.research.latest_research_date });
  });

  it("the regional tab's compact view is the newest statement of each kind, as the build marks them", () => {
    const compact = latestOfEachType(context);
    expect(compact.entries.length).toBeGreaterThan(0);
    expect(compact.entries.every((e) => e.is_latest_of_type)).toBe(true);
    const types = compact.entries.map((e) => e.context_type);
    expect(new Set(types).size).toBe(types.length);
    expect(new Set(types)).toEqual(new Set(context.entries.map((e) => e.context_type)));
    expect(regionalNote("Iran")).toContain("says nothing about any facility in Iran");
  });

  it("the research-preview caveat is exported exactly where the page shows the badge", () => {
    for (const id of COUNTRIES) {
      const line = exportPreviewLine(SYSTEMS[id]);
      expect(!!line, id).toBe(SYSTEMS[id].maturity === "research_preview");
      // The image carries the page's one definition, less its pointer to a tab the image has not got.
      if (line) { expect(RESEARCH_PREVIEW_DEFINITION.startsWith(line)).toBe(true); expect(line).toContain("not evidence that no disruption occurred"); }
    }
  });
});
