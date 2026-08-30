/** Loads the static JSON payload the Python pipeline writes into public/data/.
 *  There is no API: every file here is a build artifact served straight off the CDN.
 *
 *  Deploy-window resilience (iteration 5): on a static CDN, a freshly deployed bundle can
 *  briefly fetch data files an edge node has not caught up to. Core files stay required and
 *  fail loudly if genuinely absent; optional context layers degrade to empty rather than
 *  white-screening the whole dashboard; and a one-version schema skew (N or N-1) is
 *  tolerated. See docs/DEPLOYMENT.md. */

import type { Bundle, SchemaCheck } from "./types";

const BASE = `${import.meta.env.BASE_URL}data`;

/** Schema this frontend build was written for, and the oldest it still renders. */
export const SUPPORTED_SCHEMA = 2;
export const MIN_SUPPORTED_SCHEMA = 1;

const EMPTY_FC: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

/** Decide whether a payload of `dataVersion` is safe for an app built for `appVersion`.
 *  The static-CDN deploy window means new code briefly reading old data (back-compat) or,
 *  more rarely, old code reading new data (forward). We render in every case and only flag
 *  a genuine skew: a one-day-stale dashboard beats a white screen. A payload with no
 *  schema_version predates the field and is version 1 by definition. */
export function schemaCompatibility(
  dataVersion: number | undefined | null,
  appVersion: number = SUPPORTED_SCHEMA,
  minVersion: number = MIN_SUPPORTED_SCHEMA,
): SchemaCheck {
  const v = dataVersion ?? 1;
  let mode: SchemaCheck["mode"];
  if (v === appVersion) mode = "exact";
  else if (v > appVersion) mode = "forward";
  else mode = v >= minVersion ? "back" : "unsupported";
  return { dataVersion: v, appVersion, ok: mode !== "unsupported", mode };
}

async function grab<T>(name: string): Promise<T> {
  const res = await fetch(`${BASE}/${name}`);
  if (!res.ok) {
    throw new Error(`could not load ${name} (HTTP ${res.status}) — run the pipeline first`);
  }
  return (await res.json()) as T;
}

/** Load a file that may legitimately be absent: an optional context layer, or a file a
 *  stale CDN edge has not caught up to during a deploy. Returns `fallback` instead of
 *  throwing, so a missing optional layer degrades the map rather than crashing the app. */
export async function grabOptional<T>(name: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(`${BASE}/${name}`);
    if (!res.ok) {
      console.warn(`optional layer ${name} absent (HTTP ${res.status}); continuing without it`);
      return fallback;
    }
    return (await res.json()) as T;
  } catch (err) {
    console.warn(`optional layer ${name} failed to load; continuing without it`, err);
    return fallback;
  }
}

export async function loadBundle(): Promise<Bundle> {
  const [
    snapshot, national, regional, incidents, regions, assets, taxonomy,
    regionsGeo, linesGeo, contextLand, contextBorders, ocean,
  ] = await Promise.all([
    grab<Bundle["snapshot"]>("snapshot.json"),
    grab<Bundle["national"]>("index_national.json"),
    grab<Bundle["regional"]>("index_regional.json"),
    grab<Bundle["incidents"]>("incidents.json"),
    grab<Bundle["regions"]>("regions.json"),
    grab<Bundle["assets"]>("assets.json"),
    grab<Bundle["taxonomy"]>("taxonomy.json"),
    grab<Bundle["regionsGeo"]>("regions.geojson"),
    grab<Bundle["linesGeo"]>("assets_lines.geojson"),
    grab<Bundle["contextLand"]>("context_land.geojson"),
    grab<Bundle["contextBorders"]>("context_borders.geojson"),
    grab<Bundle["ocean"]>("ocean.geojson"),
  ]);

  // Optional context layers (iteration 5): absent on older data or a lagging edge -> empty.
  // Rivers and the continental pipeline networks are NOT loaded here. They are off by
  // default and can be large, so they lazy-load on first toggle via loadContextLayer()
  // below — keeping the analytic dashboard's first paint fast (§16).
  const schema = schemaCompatibility(snapshot.schema_version);
  if (schema.mode !== "exact") {
    console.warn(
      `data schema ${schema.dataVersion} vs app schema ${schema.appVersion} (${schema.mode}); ` +
        "rendering best-effort",
    );
  }

  return {
    snapshot, national, regional, incidents, regions, assets, taxonomy,
    regionsGeo, linesGeo, contextLand, contextBorders, ocean,
    schema,
  };
}

/** Lazy-load an optional context layer (rivers or a pipeline network) on first use, then
 *  cache it for the session. Absent/late files degrade to an empty FeatureCollection rather
 *  than throwing, so the core dashboard never depends on them (§16, §35). */
const contextLayerCache = new Map<string, GeoJSON.FeatureCollection>();
export async function loadContextLayer(file: string): Promise<GeoJSON.FeatureCollection> {
  const cached = contextLayerCache.get(file);
  if (cached) return cached;
  const fc = await grabOptional<GeoJSON.FeatureCollection>(file, EMPTY_FC);
  contextLayerCache.set(file, fc);
  return fc;
}

/** Index of the timeline step at or before `date`. */
export function stepFor(dates: string[], date: string): number {
  let lo = 0;
  let hi = dates.length - 1;
  if (date <= dates[0]) return 0;
  if (date >= dates[hi]) return hi;
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2);
    if (dates[mid] <= date) lo = mid;
    else hi = mid - 1;
  }
  return lo;
}

/** ISO date `delta` days from `iso` (delta may be negative). Deterministic — used for the
 *  trend windows, which are always relative to the scrubber position, never wall-clock now. */
export function addDays(iso: string, delta: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso; // empty/malformed -> pass through rather than throw
  const dt = new Date(Date.UTC(y, m - 1, d));
  dt.setUTCDate(dt.getUTCDate() + delta);
  return dt.toISOString().slice(0, 10);
}

export function fmtDate(iso: string): string {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const mon = months[Number(m) - 1] ?? m;
  return d ? `${Number(d)} ${mon} ${y}` : `${mon} ${y}`;
}

export function fmtNum(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toLocaleString("en-GB", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

/** Acronyms that must not be sentence-cased ("Lng Terminal" reads as a typo, and the left rail
 *  spells the same class "LNG terminal"). */
const ACRONYMS: Record<string, string> = { lng: "LNG", gpp: "GPP", chp: "CHP", npp: "NPP", hv: "HV" };

export function titleCase(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w+/g, (w) => ACRONYMS[w.toLowerCase()] ?? w.charAt(0).toUpperCase() + w.slice(1));
}

/** "1 event" / "2 events" — an unconditional plural is a small tell that nobody read the output. */
export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}

/** Signed, fixed-precision delta (e.g. "+1.21", "−0.69", "±0.00") for the change views. Uses a
 *  real minus sign so a negative never looks like a hyphenated range. */
export function fmtDelta(v: number, digits = 2): string {
  return (v > 0 ? "+" : v < 0 ? "−" : "±") + Math.abs(v).toFixed(digits);
}

/** What a "last N days" comparison ACTUALLY resolved to.
 *
 *  The index series is weekly, so a "30-day change" is really a comparison against the nearest
 *  earlier weekly step — typically 28 or 35 days back, and less near the start of the series.
 *  Every consumer gets the real numbers so the UI can label a 28-day comparison honestly instead
 *  of asserting an exact 30-day observation. `comparisonStep <= step` always, so a window can
 *  never reach into the future of the scrubber. */
export interface WindowRef {
  requestedWindowDays: number;
  actualComparisonDays: number;
  comparisonDate: string;
  comparisonStep: number;
  /** True when the series starts less than the requested window before the scrubber, so the
   *  comparison is necessarily shorter than asked for. */
  truncatedBySeriesStart: boolean;
}

export function windowRef(dates: string[], step: number, requestedWindowDays: number): WindowRef {
  const here = Math.max(0, Math.min(dates.length - 1, step));
  const target = addDays(dates[here], -requestedWindowDays);
  const comparisonStep = Math.min(here, stepFor(dates, target));
  const comparisonDate = dates[comparisonStep];
  return {
    requestedWindowDays,
    actualComparisonDays: daysBetween(comparisonDate, dates[here]),
    comparisonDate,
    comparisonStep,
    truncatedBySeriesStart: comparisonStep === 0 && dates[0] > target,
  };
}

/** Whole days from `a` to `b` (negative if b precedes a). */
export function daysBetween(a: string, b: string): number {
  const p = (iso: string) => {
    const [y, m, d] = iso.split("-").map(Number);
    return Date.UTC(y, m - 1, d);
  };
  return Math.round((p(b) - p(a)) / 86400000);
}

/** Rows whose date falls in the half-open trailing window (windowStart, windowEnd].
 *
 *  Half-open on purpose: the window END is the scrubber date and is INCLUDED (something recorded
 *  today is "what changed today"), while the start boundary is excluded so adjacent windows do
 *  not double-count a row. Nothing dated after the scrubber can ever pass, which is what keeps
 *  the panel honest when the reader scrubs into history. */
export function inWindow<T>(
  rows: readonly T[],
  dateOf: (row: T) => string | null | undefined,
  windowStart: string,
  windowEnd: string,
  keep?: (row: T) => boolean,
): T[] {
  return rows.filter((r) => {
    const d = dateOf(r);
    if (!d || d <= windowStart || d > windowEnd) return false;
    return keep ? keep(r) : true;
  });
}

/** First line of a name, for single-line UI rows.
 *
 *  A few curated corpus entries are multi-line complexes ("Ust-Luga Multimodal Complex\n* Ust-Luga
 *  Oil JSC terminal\n* ..."). Rendered raw in a compact row that collapses into an unreadable run
 *  of text, so rows take the head and mark that more is folded in. The underlying data is left
 *  alone — this is presentation only. */
export function displayName(name: string | null | undefined): string {
  if (!name) return "";
  const [head, ...rest] = name.split("\n");
  const trimmed = head.trim();
  return rest.some((r) => r.trim()) ? `${trimmed} (+${rest.filter((r) => r.trim()).length})` : trimmed;
}
