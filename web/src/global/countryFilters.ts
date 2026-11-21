/** The country page's event filters, its address and its export (iteration 22).
 *
 *  The first consumer of the shared modules (recordFilters.ts, recordCsv.ts). Pure, with type
 *  imports only from the manifest, so the Python tests run it in Node against the served payloads.
 *
 *  A country page offers the filters whose vocabulary is this country's own: date, cause, kind of
 *  infrastructure and, when the served events carry it, evidence confidence. A filter with a single
 *  possible value filters nothing and is replaced by a sentence saying what that value is.
 */
import type { CountryEvent, CountrySystem } from "./manifest";
import { optionsPresent, withFilterQuery, type FilterDef, type FilterOption } from "./recordFilters";
import {
  COUNTRY_EVENT_COLUMNS, COUNTRY_EVENT_FIELDS, countryEventsCsv, csvFilename, isRestrictedEvent, readmeFilename, readmeText,
} from "./recordCsv";

import { bucketLabel, confidenceBucket } from "./evidence";

/** The taxonomy's entries as options, in the served order, plus any value a record carries that the
 *  taxonomy does not name, so no record is left that no option can select. */
function vocabulary(map: Record<string, string>, events: readonly CountryEvent[], value: (e: CountryEvent) => string): FilterOption[] {
  const out: FilterOption[] = Object.keys(map).map((k) => ({ value: k, label: map[k] }));
  for (const e of events) {
    const v = value(e);
    if (v && !out.some((o) => o.value === v)) out.push({ value: v, label: v.replace(/_/g, " ") });
  }
  return optionsPresent(out, events, (e) => [value(e)]);
}

export interface CountryFilters {
  defs: FilterDef<CountryEvent>[];
  /** In place of a filter that has one possible value: what that value is. */
  fixed: string[];
}

/** `confidenceOrder`: the served method's categories in its own order, when the caller has loaded
 *  it. Without it the categories present are listed alphabetically by their served label. */
export function countryFilters(sys: CountrySystem, events: readonly CountryEvent[], confidenceOrder?: readonly FilterOption[]): CountryFilters {
  const defs: FilterDef<CountryEvent>[] = [
    { kind: "date", id: "date", label: "Date", start: (e) => e.date, end: (e) => e.date_end },
  ];
  const fixed: string[] = [];
  const add = (id: string, label: string, options: FilterOption[], values: (e: CountryEvent) => string[], one: (o: FilterOption) => string) => {
    if (options.length > 1) defs.push({ kind: "choice", id, label, options, values });
    else if (options.length === 1) fixed.push(one(options[0]));
  };
  add("cause", "Cause", vocabulary(sys.taxonomy.causes, events, (e) => e.cause), (e) => [e.cause],
    (o) => `All records have one reported cause: ${o.label}.`);
  add("class", "Infrastructure", vocabulary(sys.taxonomy.asset_classes, events, (e) => e.asset_class), (e) => [e.asset_class],
    (o) => `All records are of one kind of infrastructure: ${o.label}.`);

  // Evidence confidence is offered only when the build serves it on these events. A record the
  // build did not assess (category null) is its own choice, "Not assessed": it is never listed
  // under a category and never left where no choice can select it.
  const present = new Map<string, string>();
  for (const e of events) {
    const bucket = confidenceBucket(e);
    if (bucket && !present.has(bucket)) present.set(bucket, bucketLabel(e));
  }
  if (present.size > 0) {
    const options = confidenceOrder
      ? confidenceOrder.filter((o) => present.has(o.value))
      : [...present].map(([value, label]) => ({ value, label })).sort((a, b) => a.label.localeCompare(b.label));
    add("conf", "Evidence confidence", options, (e) => { const b = confidenceBucket(e); return b ? [b] : []; },
      (o) => `All records have one evidence confidence: ${o.label}.`);
  }
  return { defs, fixed };
}

/** The country page's query string: the system, the chosen region, then the filters. Everything a
 *  reload or a shared link needs to show the same list. */
export function countrySearch(id: string, region: string | null, filterQuery: string): string {
  const q = new URLSearchParams({ sys: id });
  if (region) q.set("r", region);
  return withFilterQuery(q.toString(), filterQuery);
}

/** Newest first, then by id, so the same list always exports the same file. */
export function exportOrder(events: readonly CountryEvent[]): CountryEvent[] {
  return [...events].sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : a.event_id < b.event_id ? -1 : a.event_id > b.event_id ? 1 : 0));
}

export interface CountryExport {
  csvName: string;
  csv: string;
  readmeName: string;
  readme: string;
}

/** The two files for the records shown. `shown` is the list on screen after the filters; `total`
 *  is how many published records that list had before them. */
export function countryExport(sys: CountrySystem, shown: readonly CountryEvent[], total: number,
                              filterLines: readonly string[], regionName: string | null, today: string): CountryExport {
  const csvName = csvFilename(sys.system_id, "events", sys.as_of);
  const rows = exportOrder(shown);
  const safeguarded = rows.some((e) => isRestrictedEvent(e, sys));
  const readme = readmeText({
    title: `Reported energy disruption records: ${sys.name}${regionName ? `, ${regionName}` : ""}`,
    csvName,
    scope: `${sys.system_id} (${sys.name})`,
    buildDate: sys.as_of,
    downloaded: today,
    shown: rows.length,
    total,
    filters: filterLines,
    limitations: [
      sys.comparability_statement,
      sys.event_summary.note,
      sys.reporting_environment_text,
      sys.no_index_reason,
      safeguarded
        ? "Some rows are published under attack-campaign safeguards. Their region, facility, operator, source headlines and later status are empty in this file, and publication_note says why."
        : "",
    ],
    columns: COUNTRY_EVENT_COLUMNS,
    fields: COUNTRY_EVENT_FIELDS,
    confidenceStatus: (sys as { evidence_confidence_summary?: { status?: string } }).evidence_confidence_summary?.status ?? null,
  });
  return { csvName, csv: countryEventsCsv(rows, sys), readmeName: readmeFilename(csvName), readme };
}
