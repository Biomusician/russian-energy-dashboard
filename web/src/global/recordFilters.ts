/** Shared record filters (iteration 22).
 *
 *  One small, pure filter model for every list of published records: a country system's events and
 *  the global impact layer's records. No React, no DOM and no value import, so the Python tests run
 *  this file in Node exactly as it ships.
 *
 *  THE CALLER CHOOSES THE FILTERS. A filter appears only where its vocabulary means the same thing:
 *  a country page offers date, cause, asset class and evidence confidence; the impact atlas adds
 *  domain, sector, technology, cyber mechanism, attribution status, AI involvement and country.
 *  Nothing here knows a vocabulary: a definition carries how to read a record and the options, whose
 *  labels the caller takes from served taxonomy data.
 *
 *  RULES THAT ARE TESTED.
 *  - Filters only ever hide records of the one list they are given. `optionCounts` counts inside
 *    that list ("n of the records shown") and is never a figure to set beside another country's.
 *  - Within one filter the chosen values are alternatives (any of them); filters combine (all).
 *  - The URL form is stable, short and independent of the order things were chosen in.
 *  - A link that names a filter or a value this page does not have is not obeyed silently and not
 *    dropped silently: decoding returns a note for the page to show.
 */

export interface FilterOption {
  value: string;
  label: string;
}

/** Pick any of several values. `values` returns what the record carries: several for a record with
 *  more than one (a multi-country record), none for a record that carries none. */
export interface ChoiceFilter<R> {
  kind: "choice";
  /** Short and URL-safe ([a-z0-9]+): the address key is `f.<id>`. */
  id: string;
  label: string;
  /** The vocabulary on this page, in the order to list it, with labels from served data. */
  options: readonly FilterOption[];
  values: (record: R) => readonly string[];
}

/** A date range. A record with an end date matches when any part of its span is in the range. */
export interface DateFilter<R> {
  kind: "date";
  id: string;
  label: string;
  /** ISO calendar day the record starts on. */
  start: (record: R) => string;
  end?: (record: R) => string | null | undefined;
}

export type FilterDef<R> = ChoiceFilter<R> | DateFilter<R>;

/** The presets, in the order they are offered. "since 2022" is the start of the monitored period. */
export const DATE_PRESETS = [
  { id: "30d", label: "Last 30 days", days: 30 },
  { id: "90d", label: "Last 90 days", days: 90 },
  { id: "1y", label: "Last year", days: 365 },
  { id: "2022", label: "Since 2022", days: null },
] as const;
export type DatePreset = (typeof DATE_PRESETS)[number]["id"];
export const SINCE_2022 = "2022-01-01";

/** A preset, or a custom range in which either end may be open. */
export type DateChoice = { preset: DatePreset } | { from: string | null; to: string | null };

/** What the reader has chosen, by filter id. An absent id is a filter that is off. */
export interface FilterState {
  choices: Record<string, string[]>;
  dates: Record<string, DateChoice>;
}

export const NO_FILTERS: FilterState = { choices: {}, dates: {} };

const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;
const own = (o: object, k: string) => Object.prototype.hasOwnProperty.call(o, k);

/** A real calendar day, not just the right shape: "2024-02-31" is refused. */
export function isIsoDay(s: string): boolean {
  if (!ISO_DAY.test(s)) return false;
  const d = new Date(`${s}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === s;
}

/** `days` before an ISO day, by the calendar, never through a local clock. */
export function daysBefore(day: string, days: number): string {
  const d = new Date(`${day}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - days);
  return d.toISOString().slice(0, 10);
}

/** The first and last day a choice admits; null is an open end. `today` is the reader's day: a
 *  "last 30 days" link means the 30 days before it is opened, and the page says the dates. */
export function dateBounds(choice: DateChoice, today: string): { from: string | null; to: string | null } {
  if ("preset" in choice) {
    const p = DATE_PRESETS.find((x) => x.id === choice.preset);
    if (!p) return { from: null, to: null };
    return { from: p.days == null ? SINCE_2022 : daysBefore(today, p.days), to: null };
  }
  return { from: choice.from, to: choice.to };
}

function chosen<R>(def: FilterDef<R>, state: FilterState): string[] | DateChoice | null {
  if (def.kind === "choice") {
    const v = own(state.choices, def.id) ? state.choices[def.id] : [];
    return v.length > 0 ? v : null;
  }
  return own(state.dates, def.id) ? state.dates[def.id] : null;
}

/** Whether one filter admits a record. A filter that is off admits everything. */
export function admits<R>(def: FilterDef<R>, state: FilterState, record: R, today: string): boolean {
  const c = chosen(def, state);
  if (c == null) return true;
  if (def.kind === "choice") {
    const picked = c as string[];
    return def.values(record).some((v) => picked.includes(v));
  }
  const { from, to } = dateBounds(c as DateChoice, today);
  const start = def.start(record);
  const end = def.end?.(record) || start;
  return (to == null || start <= to) && (from == null || end >= from);
}

/** The records every active filter admits, in the order given. Never reorders, never adds. */
export function applyFilters<R>(records: readonly R[], defs: readonly FilterDef<R>[], state: FilterState, today: string): R[] {
  return records.filter((r) => defs.every((d) => admits(d, state, r, today)));
}

/** Ids of the filters that are on, in the definitions' order. */
export function activeFilters<R>(defs: readonly FilterDef<R>[], state: FilterState): string[] {
  return defs.filter((d) => chosen(d, state) != null).map((d) => d.id);
}

/** The filters that hide this record: what a link to a filtered-out record has to clear. */
export function hidingFilters<R>(record: R, defs: readonly FilterDef<R>[], state: FilterState, today: string): string[] {
  return defs.filter((d) => !admits(d, state, record, today)).map((d) => d.id);
}

/** For one choice filter: how many records of THIS list carry each option, among the records the
 *  other filters admit. So the number beside an option is what choosing it alone would show. It is
 *  a count inside one list on one page; it is not a rate and not for comparison across countries. */
export function optionCounts<R>(records: readonly R[], defs: readonly FilterDef<R>[], state: FilterState,
                                today: string, id: string): Map<string, number> {
  const out = new Map<string, number>();
  const def = defs.find((d) => d.id === id);
  if (!def || def.kind !== "choice") return out;
  for (const o of def.options) out.set(o.value, 0);
  const others = defs.filter((d) => d.id !== id);
  for (const r of records) {
    if (!others.every((d) => admits(d, state, r, today))) continue;
    for (const v of new Set(def.values(r))) {
      if (out.has(v)) out.set(v, (out.get(v) ?? 0) + 1);
    }
  }
  return out;
}

/** The options at least one record of the list carries, in the vocabulary's order: a page lists
 *  what can be chosen here, not a taxonomy's every key. */
export function optionsPresent<R>(options: readonly FilterOption[], records: readonly R[],
                                  values: (r: R) => readonly string[]): FilterOption[] {
  const seen = new Set<string>();
  for (const r of records) for (const v of values(r)) seen.add(v);
  return options.filter((o) => seen.has(o.value));
}

// ---- editing the state (each returns a new state) ---------------------------------------------

export function toggleChoice(state: FilterState, id: string, value: string): FilterState {
  const cur = own(state.choices, id) ? state.choices[id] : [];
  const next = cur.includes(value) ? cur.filter((v) => v !== value) : [...cur, value];
  const choices = { ...state.choices };
  if (next.length > 0) choices[id] = next; else delete choices[id];
  return { ...state, choices };
}

export function setDate(state: FilterState, id: string, choice: DateChoice | null): FilterState {
  const dates = { ...state.dates };
  // A custom range with both ends open filters nothing: it is the filter switched off.
  if (choice == null || (!("preset" in choice) && !choice.from && !choice.to)) delete dates[id];
  else dates[id] = choice;
  return { ...state, dates };
}

export function withoutFilters(state: FilterState, ids: readonly string[]): FilterState {
  const choices = { ...state.choices };
  const dates = { ...state.dates };
  for (const id of ids) { delete choices[id]; delete dates[id]; }
  return { choices, dates };
}

// ---- the address ---------------------------------------------------------------------------------
//
// One parameter per active filter: `f.cause=technical,unknown&f.date=90d`. The `f.` prefix keeps
// these apart from every key a view already owns (sys, r, group, compare and the theatre's). Keys
// follow the filter ids' alphabetical order and values are sorted, so two readers who chose the
// same things in a different order share one address.

const PREFIX = "f.";

function parsePairs(search: string): [string, string][] {
  const q = search.startsWith("?") ? search.slice(1) : search;
  const out: [string, string][] = [];
  for (const part of q.split("&")) {
    if (!part) continue;
    const i = part.indexOf("=");
    out.push(i < 0 ? [part, ""] : [part.slice(0, i), part.slice(i + 1)]);
  }
  return out;
}

function decode(s: string): string {
  try { return decodeURIComponent(s.replace(/\+/g, " ")); } catch { return s; }
}

function encodeDate(c: DateChoice): string {
  return "preset" in c ? c.preset : `${c.from ?? ""}..${c.to ?? ""}`;
}

/** The query fragment (no leading "?") for the active filters; "" when none is on. */
export function encodeFilters<R>(defs: readonly FilterDef<R>[], state: FilterState): string {
  const parts: string[] = [];
  for (const def of [...defs].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0))) {
    const c = chosen(def, state);
    if (c == null) continue;
    const value = def.kind === "choice"
      ? [...(c as string[])].sort().map(encodeURIComponent).join(",")
      : encodeDate(c as DateChoice);
    parts.push(`${PREFIX}${encodeURIComponent(def.id)}=${value}`);
  }
  return parts.join("&");
}

/** The filter parameters of an address, untouched, so a view can carry them forward before the
 *  data that defines its filters has loaded. */
export function filterQueryOf(search: string): string {
  return parsePairs(search).filter(([k]) => decode(k).startsWith(PREFIX)).map(([k, v]) => `${k}=${v}`).join("&");
}

/** `search` with its filter parameters replaced by `filterQuery`. Every other parameter and its
 *  order is kept, so a view's own state (system, region, ...) survives a filter edit. */
export function withFilterQuery(search: string, filterQuery: string): string {
  const kept = parsePairs(search).filter(([k]) => !decode(k).startsWith(PREFIX)).map(([k, v]) => (v === "" ? k : `${k}=${v}`));
  return [...kept, ...(filterQuery ? [filterQuery] : [])].join("&");
}

const quoted = (s: string) => `“${s.length > 40 ? `${s.slice(0, 40)}…` : s}”`;

function parseDate(raw: string): DateChoice | null {
  if (DATE_PRESETS.some((p) => p.id === raw)) return { preset: raw as DatePreset };
  const m = /^(\d{4}-\d{2}-\d{2})?\.\.(\d{4}-\d{2}-\d{2})?$/.exec(raw);
  if (!m || (!m[1] && !m[2])) return null;
  if ((m[1] && !isIsoDay(m[1])) || (m[2] && !isIsoDay(m[2]))) return null;
  if (m[1] && m[2] && m[1] > m[2]) return null;
  return { from: m[1] ?? null, to: m[2] ?? null };
}

/** Read the filters out of an address. What this page cannot honour is left out of the state and
 *  described in `notes`, which the page shows: a reader is never left believing a filter is on
 *  when it is not, or wondering why a shared link shows something else. */
export function decodeFilters<R>(search: string, defs: readonly FilterDef<R>[]): { state: FilterState; notes: string[] } {
  const state: FilterState = { choices: {}, dates: {} };
  const notes: string[] = [];
  const unknownIds: string[] = [];
  for (const [rawKey, rawValue] of parsePairs(search)) {
    const key = decode(rawKey);
    if (!key.startsWith(PREFIX)) continue;
    const id = key.slice(PREFIX.length);
    const def = defs.find((d) => d.id === id);
    if (!def) { if (!unknownIds.includes(id)) unknownIds.push(id); continue; }
    if (def.kind === "date") {
      const text = decode(rawValue);
      const c = parseDate(text);
      if (c) state.dates[def.id] = c;
      else notes.push(`This link's ${def.label} filter is not a date range this page can read (${quoted(text)}). It was ignored.`);
      continue;
    }
    const known = new Set(def.options.map((o) => o.value));
    const good: string[] = own(state.choices, def.id) ? state.choices[def.id] : [];
    const bad: string[] = [];
    // Decoded first: a link written by URLSearchParams carries its commas as %2C. A vocabulary key
    // never holds a comma, so the comma is always the separator.
    for (const v of decode(rawValue).split(",").filter(Boolean)) {
      if (known.has(v)) { if (!good.includes(v)) good.push(v); } else if (!bad.includes(v)) bad.push(v);
    }
    if (good.length > 0) state.choices[def.id] = good.sort();
    if (bad.length > 0) {
      notes.push(`This link's ${def.label} filter names ${bad.length === 1 ? "a value" : "values"} this list does not have (${bad.map(quoted).join(", ")}). `
        + `${bad.length === 1 ? "It was" : "They were"} ignored${good.length === 0 ? ", so that filter is off" : ""}.`);
    }
  }
  if (unknownIds.length > 0) {
    notes.push(`This link asks for ${unknownIds.length === 1 ? "a filter" : "filters"} this page does not have (${unknownIds.map(quoted).join(", ")}). `
      + `${unknownIds.length === 1 ? "It was" : "They were"} ignored.`);
  }
  return { state, notes };
}

// ---- saying what is on ---------------------------------------------------------------------------

export function dateChoiceText(choice: DateChoice, today: string): string {
  const { from, to } = dateBounds(choice, today);
  if ("preset" in choice) {
    const p = DATE_PRESETS.find((x) => x.id === choice.preset);
    return `${p?.label ?? choice.preset} (from ${from})`;
  }
  if (from && to) return `${from} to ${to}`;
  return from ? `from ${from}` : `up to ${to}`;
}

/** One line per active filter, in the definitions' order: "Cause: Technical accident, Unknown".
 *  Used by the page's summary and by the note that travels with an exported file. */
export function describeFilters<R>(defs: readonly FilterDef<R>[], state: FilterState, today: string): string[] {
  const out: string[] = [];
  for (const def of defs) {
    const c = chosen(def, state);
    if (c == null) continue;
    if (def.kind === "date") { out.push(`${def.label}: ${dateChoiceText(c as DateChoice, today)}`); continue; }
    const picked = c as string[];
    const labels = def.options.filter((o) => picked.includes(o.value)).map((o) => o.label);
    out.push(`${def.label}: ${labels.join(", ")}`);
  }
  return out;
}
