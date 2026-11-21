/** What the Impact Atlas shows, worked out without React (iteration 22).
 *
 *  Pure functions over the served payload, so the Python tests run them in Node as they ship.
 *
 *  THE RULES THESE HOLD.
 *  - The timeline and every count are DISRUPTIONS only. An attempt is never in either.
 *  - Nothing is ordered by a figure: records are in the served date order, countries alphabetical.
 *  - No per-country count exists anywhere here. The country filter declines the option counts the
 *    shared bar would print, and the presence map is built from a set of country codes: a country
 *    with one record and a country with forty are drawn the same.
 *  - "Cyber" is a malicious cyber cause. A non-malicious IT failure has its own filter and label
 *    and is in no cyber preset.
 *  - The default view is every published record. No preset or default hides low-confidence records.
 */
import {
  NO_FILTERS, applyFilters, encodeFilters,
  type ChoiceFilter, type FilterDef, type FilterOption, type FilterState,
} from "../recordFilters";
import {
  IT_OUTAGE, NOT_ASSESSED, NOT_ASSESSED_LABEL, confidenceBucket, countryCodes, disruptions, endDay, isItFailure, startDay,
} from "./model";
import type { ConfidenceMethod, ImpactCountry, ImpactRecord, ImpactsPayload, VocabEntry } from "./types";

/** How many cards the timeline shows before "Show 50 more". */
export const PAGE = 50;

const options = (entries: readonly VocabEntry[] | undefined): FilterOption[] =>
  (entries ?? []).map((e) => ({ value: String(e.id), label: e.label }));

/** The countries with at least one DISRUPTION among `records`, in the served (alphabetical) order.
 *  A list of names and codes: it carries no count. */
export function countriesPresent(records: readonly ImpactRecord[], all: readonly ImpactCountry[]): ImpactCountry[] {
  const seen = new Set<string>();
  for (const r of records) for (const c of countryCodes(r)) seen.add(c);
  return all.filter((c) => seen.has(c.a3));
}

/** The evidence-confidence categories, in the method's order where it is loaded, else in the order
 *  the records first show them. Labels are the served ones either way. */
function confidenceOptions(records: readonly ImpactRecord[], method: ConfidenceMethod | null): FilterOption[] {
  const out: FilterOption[] = method ? method.categories.map((c) => ({ value: c.id, label: c.label })) : [];
  if (!method) {
    for (const r of records) {
      const c = r.evidence_confidence;
      if (c && c.category != null && !out.some((o) => o.value === c.category)) out.push({ value: c.category, label: c.label ?? c.category });
    }
  }
  // Records whose evidence was not assessed are their own bucket, offered whenever one exists:
  // they are not Preliminary and they are not left out of the filter.
  if (records.some((r) => confidenceBucket(r.evidence_confidence) === NOT_ASSESSED) && !out.some((o) => o.value === NOT_ASSESSED)) {
    out.push({ value: NOT_ASSESSED, label: NOT_ASSESSED_LABEL });
  }
  return out;
}

export const IT_FAILURE_VALUE = "yes";

/** The atlas's filters, with every label taken from the served vocabularies. */
export function atlasFilterDefs(payload: ImpactsPayload, method: ConfidenceMethod | null = null): FilterDef<ImpactRecord>[] {
  const v = payload.vocabularies;
  const records = disruptions(payload);
  const choice = (id: string, label: string, opts: FilterOption[], values: (r: ImpactRecord) => readonly string[],
                  extra: Partial<ChoiceFilter<ImpactRecord>> = {}): ChoiceFilter<ImpactRecord> =>
    ({ kind: "choice", id, label, options: opts, values, ...extra });
  const itLabel = v.cyber_mechanisms?.find((m) => m.id === IT_OUTAGE)?.label ?? "IT outage affecting operations";
  const defs: FilterDef<ImpactRecord>[] = [
    { kind: "date", id: "date", label: "Date", start: startDay, end: endDay },
    // No count beside a country: a number per country is a league table whatever the caption says.
    choice("country", "Country", countriesPresent(records, payload.countries).map((c) => ({ value: c.a3, label: c.name })),
           countryCodes, { counts: false }),
    choice("domain", "Domain", options(v.domains), (r) => [r.domain]),
    choice("sector", "Sector", options(v.sectors), (r) => [r.sector]),
    choice("tech", "Technology", options(v.technologies), (r) => (r.technology ? [r.technology] : [])),
    choice("cause", "Cause family", options(v.cause_families), (r) => [r.cause_family]),
    // An IT failure's mechanism is not a cyber mechanism: it is not offered under this filter.
    choice("mech", "Cyber mechanism", options(v.cyber_mechanisms).filter((o) => o.value !== IT_OUTAGE || records.some((r) => r.cause_family === "cyber" && r.cyber_mechanism === IT_OUTAGE)),
           (r) => (r.cyber_mechanism && !isItFailure(r) ? [r.cyber_mechanism] : [])),
    choice("it", "IT failure", [{ value: IT_FAILURE_VALUE, label: `${itLabel} (not a cyberattack)` }],
           (r) => (isItFailure(r) ? [IT_FAILURE_VALUE] : [])),
    choice("attr", "Attribution", options(v.attribution_statuses), (r) => [r.attribution.status]),
    choice("ai", "AI involvement", options(v.ai_statuses), (r) => [r.ai_involvement.status]),
    choice("conf", "Evidence confidence", confidenceOptions(records, method), (r) => [confidenceBucket(r.evidence_confidence)]),
  ];
  // A filter with nothing to choose from is not offered.
  return defs.filter((d) => d.kind === "date" || d.options.length > 0);
}

export interface AtlasPreset {
  id: string;
  label: string;
  /** What the preset selects, in words, for the chip's description. */
  meaning: string;
  choices: Record<string, string[]>;
}

/** The preset chips, in the order they are offered. Each is nothing more than a named filter state:
 *  choosing one writes ordinary filters into the address, and the bar says which are on.
 *  Every "cyber" preset is `cause = cyber`, so none of them includes an IT failure. */
export function atlasPresets(payload: ImpactsPayload): AtlasPreset[] {
  const aiReported = (payload.vocabularies.ai_statuses ?? []).map((s) => String(s.id)).filter((s) => s !== "NONE_REPORTED");
  const cyber = { cause: ["cyber"] };
  return [
    { id: "cyber", label: "Cyber", choices: { ...cyber },
      meaning: "Records whose reported cause is a malicious cyber incident. IT failures are not included." },
    { id: "ai", label: "AI involved", choices: { ai: aiReported },
      meaning: "Records where a source ties AI to the incident, however firmly. Expect few; none is a correct answer." },
    { id: "attributed-cyber", label: "Attributed cyber", choices: { ...cyber, attr: ["ASSESSED", "ATTRIBUTED"] },
      meaning: "Cyber records where a competent body assessed or formally attributed an actor. Claims, suspicions and disputes are separate values of the Attribution filter." },
    { id: "grid-cyber", label: "Power-grid cyber", choices: { ...cyber, sector: ["electricity"] },
      meaning: "Cyber records in the electricity sector." },
    { id: "renewable-cyber", label: "Renewable cyber", choices: { ...cyber, tech: ["hydro_generation", "wind_generation", "solar_generation"] },
      meaning: "Cyber records at hydro, wind or solar generation." },
    { id: "civilian-cyber", label: "Civilian-service cyber", choices: { ...cyber, domain: ["civilian_service"] },
      meaning: "Cyber records affecting water, telecommunications, healthcare, transport and other civilian services." },
    { id: "it-failure", label: "IT failure", choices: { it: [IT_FAILURE_VALUE] },
      meaning: "Disruptions triggered by a non-malicious IT failure, such as a faulty update. Not cyberattacks, and in no cyber preset." },
  ];
}

/** The filter state a preset stands for, limited to the filters and values this page has. */
export function presetState(preset: AtlasPreset, defs: readonly FilterDef<ImpactRecord>[]): FilterState {
  const choices: Record<string, string[]> = {};
  for (const [id, values] of Object.entries(preset.choices)) {
    const def = defs.find((d) => d.id === id);
    if (!def || def.kind !== "choice") continue;
    const known = values.filter((x) => def.options.some((o) => o.value === x)).sort();
    if (known.length > 0) choices[id] = known;
  }
  return { choices, dates: {} };
}

/** How many published records a preset shows (iteration 22 closure), so a chip that leads to an
 *  empty view says so before it is chosen. A preset whose filter is not on this page shows none:
 *  dropping that filter would count every record. A count of records, never of a country's. */
export function presetCount(preset: AtlasPreset, defs: readonly FilterDef<ImpactRecord>[], records: readonly ImpactRecord[], today: string): number {
  const state = presetState(preset, defs);
  if (Object.keys(preset.choices).some((id) => !state.choices[id])) return 0;
  return applyFilters(records, defs, state, today).length;
}

/** The line under a chosen preset that matches nothing: an empty result is a correct answer. */
export function presetEmptyText(preset: AtlasPreset): string {
  return preset.id === "ai"
    ? "No reviewed record currently reports AI involvement. That is a statement about this corpus, not a finding that AI played no part anywhere."
    : "No published record currently matches this preset. That is a statement about this corpus, which is not a census.";
}

/** The address fragment for a preset ("f.cause=cyber&f.sector=electricity"). */
export function presetQuery(preset: AtlasPreset, defs: readonly FilterDef<ImpactRecord>[]): string {
  return encodeFilters(defs, presetState(preset, defs));
}

/** The preset the current filters are exactly, if any: its chip is shown as chosen. */
export function activePreset(presets: readonly AtlasPreset[], defs: readonly FilterDef<ImpactRecord>[], state: FilterState): string | null {
  const now = encodeFilters(defs, state);
  if (now === encodeFilters(defs, NO_FILTERS)) return null;
  return presets.find((p) => presetQuery(p, defs) === now)?.id ?? null;
}

export interface CorpusSummary {
  /** Published disruptions in the corpus. Attempts are not in this number. */
  records: number;
  /** Countries with at least one disruption. */
  countries: number;
  first: string | null;
  last: string | null;
  researched: string | null;
}

/** The header line's facts: how many records, how many countries, the span, the last research run.
 *  One count for the whole corpus; never one per country. */
export function corpusSummary(payload: ImpactsPayload): CorpusSummary {
  const records = disruptions(payload);
  const days = records.map(startDay).sort();
  // The span at the precision the records give (iteration 23, AN-11): a month-precision record is
  // "Jan 2022", never "1 Jan 2022". Where records on the end day differ, a full date wins.
  const asDated = (day: string | undefined) => {
    if (!day) return null;
    const same = records.filter((r) => startDay(r) === day);
    return same.find((r) => r.date === day)?.date ?? same[0]?.date ?? day;
  };
  return {
    records: records.length,
    countries: countriesPresent(records, payload.countries).length,
    first: asDated(days[0]),
    last: asDated(days[days.length - 1]),
    researched: payload.research?.latest_research_date ?? null,
  };
}

export interface MonthGroup { ym: string; records: ImpactRecord[] }
export interface YearGroup { year: string; months: MonthGroup[] }

/** The records grouped by year and month, keeping the order they came in (newest first). Grouping
 *  never reorders: a record stays where the served date order put it. */
export function groupByMonth(records: readonly ImpactRecord[]): YearGroup[] {
  const years: YearGroup[] = [];
  for (const r of records) {
    const ym = startDay(r).slice(0, 7);
    const year = ym.slice(0, 4);
    let y = years[years.length - 1];
    if (!y || y.year !== year) { y = { year, months: [] }; years.push(y); }
    let m = y.months[y.months.length - 1];
    if (!m || m.ym !== ym) { m = { ym, records: [] }; y.months.push(m); }
    m.records.push(r);
  }
  return years;
}

// ---- the presence map ----------------------------------------------------------------------------

/** One mark colour and one "no record in this view" colour. There is no third. */
export const PRESENCE_MARK = "#3f8f9b";
export const PRESENCE_NONE = "#141c25";

/** The country codes to mark: those with at least one disruption in the view. A SET, sorted so the
 *  same view always gives the same value; how many records each country has is not kept. */
export function presenceCodes(records: readonly ImpactRecord[]): string[] {
  const seen = new Set<string>();
  for (const r of records) {
    if (r.record_kind !== "disruption") continue;
    for (const c of countryCodes(r)) seen.add(c);
  }
  return [...seen].sort();
}

/** The map's fill: marked or not. Built from the code set alone, so it cannot encode a count. */
export function presenceFill(codes: readonly string[]): unknown[] | string {
  if (codes.length === 0) return PRESENCE_NONE;
  return ["case", ["in", ["get", "a3"], ["literal", [...codes]]], PRESENCE_MARK, PRESENCE_NONE];
}
