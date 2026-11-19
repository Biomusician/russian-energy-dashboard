/** The "Cyber & civilian services" tab of a country page, as plain functions (iteration 22).
 *
 *  The impact layer is a separate, non-scored corpus (docs/GLOBAL_IMPACT_METHODOLOGY.md). This
 *  module picks one country's records out of it, defines the tab's filters, counts the records by
 *  cause family INSIDE that country, and builds the lines an exported image carries. Nothing here
 *  reads or changes the country's own published-record count.
 *
 *  No React and no DOM: the Python tests run this file in Node as it ships.
 */
import { attempts as allAttempts, isAbstracted, isItFailure, startDay } from "./impacts/model";
import { impactsFor } from "./impacts/load";
import type { ImpactRecord, ImpactsPayload, VocabEntry } from "./impacts/types";
import type { FilterDef, FilterOption } from "./recordFilters";
import { IMPACT_COLUMNS, IMPACT_FIELDS, csvFilename, impactRecordsCsv, readmeFilename, readmeText } from "./recordCsv";
import { IMPACT_CORPUS_LINE, noImpactRecordText } from "./countryOverview";
import { CONFIDENCE_IS_NOT, inSentence } from "./countryCopy";
import { NOT_ASSESSED, confidenceBucket, confidenceLabel } from "./impacts/model";

export interface CountryImpactRecords {
  /** Disruptions for this country, in the served order: event date, newest first. */
  records: ImpactRecord[];
  /** Documented attempts with no reported service disruption: listed apart, never counted. */
  attempts: ImpactRecord[];
}

function belongsTo(r: ImpactRecord, systemId: string): boolean {
  return r.system_id === systemId || (r.countries ?? []).some((c) => c.system_id === systemId);
}

/** This system's impact records. By the system id the build puts on each record, so a
 *  multi-country record that includes this country is listed here too. */
export function countryImpacts(payload: ImpactsPayload, systemId: string): CountryImpactRecords {
  return {
    records: impactsFor(payload, { systemIds: [systemId] }),
    attempts: allAttempts(payload).filter((r) => belongsTo(r, systemId)),
  };
}

// ---- vocabulary ----------------------------------------------------------------------------------

function entries(payload: Pick<ImpactsPayload, "vocabularies">, name: string): VocabEntry[] {
  const v = payload.vocabularies?.[name];
  return Array.isArray(v) ? v : [];
}

const plain = (id: string) => { const s = id.replace(/_/g, " ").toLowerCase(); return s.charAt(0).toUpperCase() + s.slice(1); };

/** The served label of a key; the key in plain words if the payload has none. */
export function servedLabel(payload: Pick<ImpactsPayload, "vocabularies">, name: string, id: string): string {
  const e = entries(payload, name).find((x) => String(x.id) === id);
  return e ? e.label : plain(id);
}

/** A vocabulary's entries that at least one record carries, in the served order, then any value a
 *  record carries that the vocabulary does not name: no record is left that no option can select. */
function optionsFor(payload: Pick<ImpactsPayload, "vocabularies">, name: string, records: readonly ImpactRecord[],
                    values: (r: ImpactRecord) => string[]): FilterOption[] {
  const seen = new Set<string>();
  for (const r of records) for (const v of values(r)) seen.add(v);
  const out: FilterOption[] = entries(payload, name).filter((e) => seen.has(String(e.id))).map((e) => ({ value: String(e.id), label: e.label }));
  for (const v of seen) if (!out.some((o) => o.value === v)) out.push({ value: v, label: plain(v) });
  return out;
}

// ---- filters --------------------------------------------------------------------------------------

export const IT_FAILURE_LABEL = "IT failure";
const IT_FAILURE_OPTION: FilterOption = { value: "it_failure", label: "IT failure (not a cyberattack)" };

/** The tab's filters: cause, IT failure, sector, technology, attribution, AI involvement and
 *  evidence confidence. A filter with fewer than two possible values in this country's list
 *  filters nothing and is left out.
 *
 *  "Cyber" in the cause filter is the malicious cyber cause family only. A non-malicious, digitally
 *  triggered failure is a technical cause with its own label and its own filter (methodology §4).
 *
 *  `confidenceOrder`: the method's categories in its own order, when the page has loaded it. */
export function impactFilters(payload: Pick<ImpactsPayload, "vocabularies">, records: readonly ImpactRecord[],
                              confidenceOrder?: readonly string[]): FilterDef<ImpactRecord>[] {
  const defs: FilterDef<ImpactRecord>[] = [];
  const add = (id: string, label: string, options: FilterOption[], values: (r: ImpactRecord) => string[]) => {
    if (options.length > 1) defs.push({ kind: "choice", id, label, options, values });
  };
  const cause = (r: ImpactRecord) => [r.cause_family];
  add("cause", "Cause", optionsFor(payload, "cause_families", records, cause), cause);
  // Offered when some records are IT failures and some are not: otherwise it filters nothing.
  const it = records.filter(isItFailure).length;
  if (it > 0 && it < records.length) {
    defs.push({ kind: "choice", id: "it", label: IT_FAILURE_LABEL, options: [IT_FAILURE_OPTION],
                values: (r) => (isItFailure(r) ? [IT_FAILURE_OPTION.value] : []) });
  }
  const sector = (r: ImpactRecord) => [r.sector];
  add("sector", "Sector", optionsFor(payload, "sectors", records, sector), sector);
  // Null outside energy: not applicable, so such a record carries no technology to choose.
  const tech = (r: ImpactRecord) => (r.technology ? [r.technology] : []);
  add("tech", "Technology", optionsFor(payload, "technologies", records, tech), tech);
  const attr = (r: ImpactRecord) => [r.attribution.status];
  add("attr", "Attribution", optionsFor(payload, "attribution_statuses", records, attr), attr);
  const ai = (r: ImpactRecord) => [r.ai_involvement.status];
  add("ai", "AI involvement", optionsFor(payload, "ai_statuses", records, ai), ai);

  // A record the build did not assess (category null) is its own choice, "Not assessed", listed
  // last: never under a category, and never left where no choice can select it.
  const conf = (r: ImpactRecord) => [confidenceBucket(r.evidence_confidence)];
  const labels = new Map<string, string>();
  for (const r of records) {
    const b = confidenceBucket(r.evidence_confidence);
    if (!labels.has(b)) labels.set(b, confidenceLabel(r.evidence_confidence));
  }
  const present = [...labels].map(([value, label]) => ({ value, label }));
  const ordered = confidenceOrder
    ? [...present].sort((a, b) => rank(confidenceOrder, a.value) - rank(confidenceOrder, b.value))
    : [...present].sort((a, b) => rank([], a.value) - rank([], b.value) || a.label.localeCompare(b.label));
  add("conf", "Evidence confidence", ordered, conf);
  return defs;
}

/** A category's place in the method's order; one the method does not name follows those it does,
 *  and "Not assessed" is always last. */
function rank(order: readonly string[], v: string): number {
  if (v === NOT_ASSESSED) return order.length + 1;
  const i = order.indexOf(v);
  return i < 0 ? order.length : i;
}

/** Newest first, then by id: the served order, re-applied so the list and the file agree. */
export function impactOrder(records: readonly ImpactRecord[]): ImpactRecord[] {
  return [...records].sort((a, b) => {
    const x = startDay(a), y = startDay(b);
    return x < y ? 1 : x > y ? -1 : a.impact_id < b.impact_id ? -1 : a.impact_id > b.impact_id ? 1 : 0;
  });
}

// ---- counts inside one country --------------------------------------------------------------------

export interface CauseCount { id: string; label: string; n: number }

/** How this country's impact records fall across the cause families, in the vocabulary's order
 *  (never by size). A count inside one country's list: not a rate, and not for comparison. */
export function causeCounts(payload: Pick<ImpactsPayload, "vocabularies">, records: readonly ImpactRecord[]): CauseCount[] {
  const n = new Map<string, number>();
  for (const r of records) n.set(r.cause_family, (n.get(r.cause_family) ?? 0) + 1);
  const known = entries(payload, "cause_families").map((e) => String(e.id)).filter((id) => n.has(id));
  const rest = [...n.keys()].filter((id) => !known.includes(id)).sort();
  return [...known, ...rest].map((id) => ({ id, label: servedLabel(payload, "cause_families", id), n: n.get(id) ?? 0 }));
}

// ---- the exported image's summary -----------------------------------------------------------------

/** One record as a line of the exported image: date, sector, cause, and the place the record
 *  publishes. An abstracted (attack or sabotage) record is its country and nothing finer, whatever
 *  the record carries: no region, no operator, no headline, and no summary text, which could name
 *  any of them. Nothing but these four fields is ever drawn for any record. */
export function impactExportRow(payload: Pick<ImpactsPayload, "vocabularies">, r: ImpactRecord): string {
  const cause = isItFailure(r) ? `${servedLabel(payload, "cause_families", r.cause_family)} (${IT_FAILURE_LABEL.toLowerCase()})`
    : servedLabel(payload, "cause_families", r.cause_family);
  const place = isAbstracted(r) ? "country level, place withheld"
    : r.admin1?.name ? r.admin1.name : "country level";
  return `${r.date} · ${servedLabel(payload, "sectors", r.sector)} · ${cause} · ${place}`;
}

export interface ImpactExportSummary {
  title: string;
  /** The caveats and the counts, in the order they are drawn. */
  lines: string[];
  /** The newest records, one line each. */
  rows: string[];
  /** Said under the rows when not every record fits. */
  more: string | null;
}

export const EXPORT_ROW_LIMIT = 6;

/** What a country image carries when it is exported from the impact tab: that the list is a
 *  separate, non-scored corpus; this country's counts by cause family; what evidence confidence is
 *  and is not; and the newest records by date. `statement` is the served method's own sentence. */
export function impactExportSummary(name: string, records: readonly ImpactRecord[], attempts: readonly ImpactRecord[],
                                    payload: Pick<ImpactsPayload, "vocabularies">, statement?: string | null): ImpactExportSummary {
  const lines: string[] = [IMPACT_CORPUS_LINE];
  if (records.length === 0) {
    lines.push(noImpactRecordText(name));
  } else {
    const by = causeCounts(payload, records).map((c) => `${c.label} ${c.n}`).join(" · ");
    lines.push(`${records.length} reviewed impact ${records.length === 1 ? "record" : "records"} for ${inSentence(name)}, by cause family: ${by}.`);
    const it = records.filter(isItFailure).length;
    if (it > 0) lines.push(`Of these, ${it} ${it === 1 ? "is an IT failure" : "are IT failures"}: digitally triggered without malice, not a cyberattack.`);
    lines.push("Counts inside this country only: published records in this corpus, never a rate, and not comparable across countries.");
  }
  if (attempts.length > 0) {
    lines.push(`${attempts.length} documented ${attempts.length === 1 ? "attempt" : "attempts"} with no reported service disruption, listed apart and not counted above.`);
  }
  lines.push(statement || CONFIDENCE_IS_NOT);
  const ordered = impactOrder(records);
  const rows = ordered.slice(0, EXPORT_ROW_LIMIT).map((r) => impactExportRow(payload, r));
  const left = ordered.length - rows.length;
  return {
    title: `Cyber & civilian services: reviewed impact records for ${inSentence(name)}`,
    lines,
    rows,
    more: left > 0 ? `and ${left} earlier ${left === 1 ? "record" : "records"}, listed on the page.` : null,
  };
}

// ---- CSV -------------------------------------------------------------------------------------------

export interface ImpactFiles { csvName: string; csv: string; readmeName: string; readme: string }

/** The two files for the impact records shown: the CSV, and the note that explains it. */
export function impactFiles(systemId: string, name: string, shown: readonly ImpactRecord[], total: number,
                            filterLines: readonly string[], payload: Pick<ImpactsPayload, "as_of" | "caveats">, today: string): ImpactFiles {
  const csvName = csvFilename(systemId, "impacts", payload.as_of);
  const rows = impactOrder(shown);
  const readme = readmeText({
    title: `Reviewed impact records (cyber and civilian services): ${name}`,
    csvName,
    scope: `${systemId} (${name}), global impact layer`,
    buildDate: payload.as_of,
    downloaded: today,
    shown: rows.length,
    total,
    filters: filterLines,
    limitations: [
      IMPACT_CORPUS_LINE,
      ...(payload.caveats ?? []),
      rows.some(isAbstracted)
        ? "Some rows are attack or sabotage records published at country level. Their region, facility, operator and source headlines are empty in this file, and publication_note says why."
        : "",
    ],
    columns: IMPACT_COLUMNS,
    fields: IMPACT_FIELDS,
  });
  return { csvName, csv: impactRecordsCsv(rows), readmeName: readmeFilename(csvName), readme };
}
