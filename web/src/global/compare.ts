import { localDayOf } from "../freshness";
import { fmtValue, rowForSystem, type EnergyContext } from "./context";
import {
  CAMPAIGN_STATE_LABEL, ENVIRONMENT_LABEL, LANE_STATE_LABEL, labelFor,
  type CountrySystem, type Manifest, type ManifestSystem,
} from "./manifest";
import { MAX_COMPARE } from "./router";
import { RESEARCH_PREVIEW_DEFINITION, RESEARCH_PREVIEW_LABEL } from "./countryCopy";
import { fmtDate } from "../data";
import { laneChips } from "./homeModel";

/** The comparison workspace's rows (iteration 21), apart from the page so a test can read them.
 *
 *  WHAT IS COMPARED. Only what has a common basis: a definition that means the same thing in every
 *  system (whether it has an index, how far its research has got, which publication safeguards
 *  apply, how precisely it places a record), and national energy context from one source and one
 *  year. What a system says about its own sourcing is shown too, but labelled as true within that
 *  system only.
 *
 *  WHAT IS NEVER COMPARED. Event counts, attack counts, records held back, severity, and any order
 *  of systems but the reader's own. Those depend on each system's reporting environment and
 *  research state, so setting them side by side would read as a ranking of disruption. No row here
 *  reads them, and the columns are never re-ordered by a figure.
 *
 *  A missing figure is a cell that says why ("no data", "not on this basis", "could not be
 *  loaded"), never a zero.
 */

export interface CompareColumn {
  entry: ManifestSystem;
  /** The country's own system.json. Null for the theatre, which has none, and until it loads. */
  system: CountrySystem | null;
  status: "theatre" | "loading" | "loaded" | "failed";
}

/** value: a stated fact. no_data: the source has no figure. not_applicable: the dimension does not
 *  describe this kind of system. unavailable: a file failed. loading: not yet known. */
export type CellKind = "value" | "no_data" | "not_applicable" | "unavailable" | "loading";
export interface Cell {
  kind: CellKind;
  text: string;
  detail?: string;
  /** Shorter lines for the exported image, where a column is 300 pixels wide. */
  lines?: string[];
}

/** common: one definition for every system. context: one source and one year for every country.
 *  within: true inside this system only, never a comparison between columns. */
export type RowBasis = "common" | "context" | "within";

export const COMPARE_ROW_IDS = [
  "view_type", "as_of", "index", "maturity", "last_pass", "lanes", "safeguards", "placement",
  "ctx_total_production", "ctx_crude_production", "ctx_gas_production", "ctx_electricity_generation",
  "reporting", "sourcing", "source_checks",
] as const;
export type CompareRowId = (typeof COMPARE_ROW_IDS)[number];

export interface CompareRow {
  id: CompareRowId;
  label: string;
  basis: RowBasis;
  /** What the row measures and why it can sit across columns (or why it cannot). */
  basisNote: string;
  cells: Cell[];
}

/** National context shown here: the figures every country has on the same definition. */
export const CONTEXT_METRICS = ["total_production", "crude_production", "gas_production", "electricity_generation"] as const;

export const MATURITY_DEFINITION = `${RESEARCH_PREVIEW_DEFINITION} Monitored means a country has left that stage; ` +
  "its search can still be partial, as the source-group row shows.";

export const NO_INDEX_MEANING = "No index is not a zero.";

const GENERIC_NO_INDEX =
  "Only one monitored area on this site has a disruption index. Its weights and recovery assumptions were designed " +
  "for that area and are not transferred to other countries. No index is not a zero.";

/** Lane states in the five words a reader can compare. The finer state stays in the detail. */
export const LANE_BUCKETS: { label: string; states: string[] }[] = [
  { label: "declared complete", states: ["universe_searched", "current_through_latest_release", "declared_query_set_run"] },
  { label: "partial", states: ["partially_searched"] },
  { label: "not started", states: ["not_started"] },
  { label: "stopped by search limit", states: ["stopped_by_search_limit"] },
  { label: "source unavailable", states: ["blocked_by_source"] },
];

/** Counts per bucket in a fixed order, zeros included so every column names the same categories.
 *  A state outside the five (an older log format) is kept under its own label, never dropped. */
export function laneBuckets(states: Record<string, number>): { label: string; n: number }[] {
  // A state the pass does not list has no lanes in it: here zero is a count, not a missing figure.
  const own = (k: string) => {
    const n = Object.prototype.hasOwnProperty.call(states, k) ? Number(states[k]) : NaN;
    return Number.isFinite(n) ? n : 0;
  };
  const known = new Set(LANE_BUCKETS.flatMap((b) => b.states));
  const out = LANE_BUCKETS.map((b) => ({ label: b.label, n: b.states.reduce((a, k) => a + own(k), 0) }));
  for (const k of Object.keys(states)) {
    if (!known.has(k) && own(k) > 0) out.push({ label: labelFor(LANE_STATE_LABEL, k).toLowerCase(), n: own(k) });
  }
  return out;
}

export interface Resolved {
  /** Known systems, in the reader's order, at most MAX_COMPARE. */
  columns: ManifestSystem[];
  /** Ids the manifest does not know, as typed (already lower-cased by the router). */
  unknown: string[];
  /** Known systems past the limit, by name. */
  over: string[];
}

/** Match the URL's ids against the manifest. A Map, not an object, so `__proto__` is just unknown. */
export function resolveCompare(ids: string[], m: Manifest): Resolved {
  const byId = new Map(m.systems.map((s) => [s.id, s]));
  const known: ManifestSystem[] = [];
  const unknown: string[] = [];
  for (const id of ids) {
    const s = byId.get(id);
    if (!s) unknown.push(id);
    else if (!known.includes(s)) known.push(s);
  }
  return { columns: known.slice(0, MAX_COMPARE), unknown, over: known.slice(MAX_COMPARE).map((s) => s.name) };
}

const NOT_ON_BASIS = "Not on this basis";
const THEATRE_OWN = "This monitored area is described by its own coverage and quantified-capacity ratios on its page.";

function value(text: string, detail?: string, lines?: string[]): Cell {
  return { kind: "value", text, detail, lines };
}
function notApplicable(detail: string): Cell {
  return { kind: "not_applicable", text: NOT_ON_BASIS, detail, lines: ["Not on this basis"] };
}

const UNAVAILABLE: Cell = { kind: "unavailable", text: "Could not be loaded",
  detail: "This system's file could not be read. The other columns are unaffected.", lines: ["Could not be loaded"] };
const LOADING: Cell = { kind: "loading", text: "Loading…", lines: ["Loading"] };

/** A cell that needs the country's own file: loading, failed or theatre are answered here. */
function fromSystem(col: CompareColumn, theatre: () => Cell, f: (s: CountrySystem) => Cell): Cell {
  if (col.status === "theatre") return theatre();
  if (col.status === "failed" || (col.status === "loaded" && !col.system)) return UNAVAILABLE;
  if (!col.system) return LOADING;
  return f(col.system);
}

/** "about 6 in 10", from a part of a whole within one system. Never a percentage of research. */
function inTen(part: number, whole: number): string {
  const r = Math.round((10 * part) / whole);
  if (part > 0 && r === 0) return "fewer than 1 in 10";
  if (part < whole && r === 10) return "more than 9 in 10";
  return part === whole ? "all" : part === 0 ? "none" : `about ${r} in 10`;
}

function indexCell(col: CompareColumn): Cell {
  if (col.entry.index) {
    // The theatre's index value is never placed in a row beside systems that have none: the two are
    // not commensurable, and a number next to "No index" reads as a score next to a zero.
    return value(`Has its own index (${col.entry.index.name}), not comparable`,
      "Built for this monitored area alone: its weights, decay and transmission measure do not transfer to any other " +
      "system, so its value is not shown beside systems without one. Open the area's page for the value and what it means.",
      ["Own index: not comparable,", "value not shown here"]);
  }
  return value("No index", col.system?.no_index_reason ?? GENERIC_NO_INDEX, ["No index (not a zero)"]);
}

function lanesCell(s: CountrySystem): Cell {
  const states = s.research_freshness.lane_states ?? {};
  if (!Object.keys(states).length) {
    return value("No source groups logged yet", "No systematic pass has declared its source groups yet.", ["No source groups logged yet"]);
  }
  const buckets = laneBuckets(states);
  const words = buckets.map((b) => `${b.n} ${b.label}`);
  const finer = laneChips(states).split(" · ").join("; ");
  return value(words.join(" · "), `In the latest systematic pass, source groups by state: ${finer}.`, words);
}

function safeguardsCell(col: CompareColumn): Cell {
  if (col.status === "theatre") {
    return notApplicable("This monitored area follows its own publication rules: records are kept by administrative region and never carry coordinates.");
  }
  const state = col.system?.campaign_state?.state;
  const on = col.entry.campaign_restricted === true || (state != null && state !== "NO_ACTIVE_CAMPAIGN");
  // The manifest states the flag for every country; without it, wait for (or report) the country's file.
  if (col.entry.campaign_restricted === undefined && !col.system) return col.status === "failed" ? UNAVAILABLE : LOADING;
  return on
    ? value("Yes", `${state ? `${labelFor(CAMPAIGN_STATE_LABEL, state)}. ` : ""}An attack is published as an event, but the later repair, restart ` +
        "or operating status of the attacked facility is not, and no list repeats what such a record says.", ["Yes: later status of attacked", "facilities not published"])
    : value("No", "No attack campaign is recorded, so recovery evidence is published where it is found.", ["No"]);
}

function placementCell(col: CompareColumn): Cell {
  return fromSystem(col,
    () => value("Administrative region", "Records are kept by administrative region and never carry coordinates.", ["Administrative region"]),
    (s) => {
      const pp = s.geography.precision_policy;
      const unit = s.geography.unit_label;
      if (pp?.kinetic === "country" && pp?.other === "country") {
        return value("Country as a whole, for every record", "No record is placed below the country.", ["Country as a whole"]);
      }
      if (pp?.kinetic === "country") {
        return value(`Attack records: country as a whole. Other records: ${unit} at most`,
          "An attack or sabotage record has no region, facility or operator. Other records are placed no more precisely than a first-level region.",
          ["Attacks: country as a whole", `Other records: ${unit} at most`]);
      }
      // Some systems call their first-level unit simply "region"; "First-level region (region)" says nothing.
      const named = unit && unit !== "region" ? ` (${unit})` : "";
      return value(`First-level region${named} at most`, "No record is placed more precisely than a first-level region.",
        [`First-level region${named} at most`]);
    });
}

function sourcingCell(col: CompareColumn): Cell {
  return fromSystem(col, () => notApplicable(THEATRE_OWN), (s) => {
    const sh = s.source_health;
    if (!sh) return { kind: "no_data", text: "Not described", lines: ["Not described"] };
    if (sh.events === 0) {
      return value("No published records to describe", "That describes this dataset, not the country: a record not found is not a disruption that did not happen.");
    }
    const parts = [`${(sh.citations / sh.events).toFixed(1)} citations per published record`];
    if (sh.single_origin_events != null) parts.push(`${inTen(sh.single_origin_events, sh.events)} rest on a single originating statement`);
    parts.push(`${inTen(sh.events_with_first_party_source, sh.events)} cite a first-party source`);
    return value(parts.join("; "),
      `${sh.origin_rule ?? ""} First-party here means: ${sh.first_party_roles.join(", ")}${sh.first_party_excludes ? `, excluding ${sh.first_party_excludes}` : ""}.`.trim());
  });
}

function checksCell(col: CompareColumn): Cell {
  return fromSystem(col, () => notApplicable(THEATRE_OWN), (s) => {
    let lo: string | null = null;
    let hi: string | null = null;
    for (const src of s.sources) {
      const d = src.last_checked;
      if (!d) continue;
      if (lo === null || d < lo) lo = d;
      if (hi === null || d > hi) hi = d;
    }
    if (!lo || !hi) return { kind: "no_data", text: "No check date recorded", lines: ["No check date recorded"] };
    return value(lo === hi ? `All checked on ${fmtDate(lo)}` : `Last checked between ${fmtDate(lo)} and ${fmtDate(hi)}`,
      "When each registered source was last read. A check says a source was read then, not that it reports everything.");
  });
}

function contextCell(col: CompareColumn, ctx: EnergyContext | null, ctxFailed: boolean, metric: string): Cell {
  if (col.entry.kind === "theatre") {
    return { kind: "not_applicable", text: "No single national figure",
      detail: "This monitored area spans parts of several countries, so no one national row describes it.", lines: ["No single national figure"] };
  }
  if (!ctx) {
    return ctxFailed ? { kind: "unavailable", text: "Context could not be loaded", lines: ["Context could not be loaded"] }
      : { kind: "loading", text: "Loading…", lines: ["Loading"] };
  }
  const m = ctx.metrics[metric];
  const row = rowForSystem(ctx, col.entry.id);
  if (!m || !row) return { kind: "no_data", text: "no data", detail: "The source has no row for this country.", lines: ["no data"] };
  const v = Object.prototype.hasOwnProperty.call(row.values, metric) ? row.values[metric] : null;
  const notes: string[] = [];
  const others = ctx.countries.filter((r) => r.system_id === col.entry.id && r.a3 !== row.a3).map((r) => r.name);
  if (others.length) notes.push(`The source reports ${others.join(" and ")} separately; not included.`);
  if (row.scope_note && (!row.scope_note.startsWith("Electricity") || metric === "electricity_generation")) notes.push(row.scope_note);
  // Null stays "no data": a missing figure is not a reported zero.
  if (v == null) return { kind: "no_data", text: "no data", detail: notes.join(" ") || undefined, lines: ["no data"] };
  return value(fmtValue(v, m.unit), notes.join(" ") || undefined);
}

/** Every row, in a fixed order, one cell per column in the reader's order. */
export function compareRows(cols: CompareColumn[], ctx: EnergyContext | null, manifest: Manifest | null, ctxFailed = false): CompareRow[] {
  const envText = (k: string) => (manifest && Object.prototype.hasOwnProperty.call(manifest.reporting_environments, k) ? manifest.reporting_environments[k] : undefined);
  const rows: CompareRow[] = [
    { id: "view_type", label: "What it is", basis: "common",
      basisNote: "A country system covers one country. A monitored area covers parts of several countries and is built differently.",
      cells: cols.map((c) => c.entry.kind === "theatre"
        ? value("Monitored area spanning several countries", undefined, ["Monitored area,", "several countries"])
        : value("Country system", undefined, ["Country system"])) },
    { id: "as_of", label: "Record as of", basis: "common", basisNote: "The date each system's published record describes.",
      cells: cols.map((c) => value(fmtDate(c.entry.as_of), undefined, [fmtDate(c.entry.as_of)])) },
    { id: "index", label: "Index", basis: "common",
      basisNote: `Whether a disruption index is published. ${NO_INDEX_MEANING} An index built for one area is not comparable with any other system.`,
      cells: cols.map(indexCell) },
    { id: "maturity", label: "Research maturity", basis: "common", basisNote: MATURITY_DEFINITION,
      cells: cols.map((c) => c.entry.kind === "theatre" ? notApplicable(THEATRE_OWN)
        : c.entry.maturity === "research_preview" ? value(RESEARCH_PREVIEW_LABEL, undefined, [RESEARCH_PREVIEW_LABEL])
          : c.entry.maturity === "monitored" ? value("Monitored", undefined, ["Monitored"])
            : { kind: "no_data", text: "Not stated", lines: ["Not stated"] }) },
    { id: "last_pass", label: "Latest systematic research pass", basis: "common",
      basisNote: "The date of the newest search run across every source group the system's research plan declares.",
      cells: cols.map((c) => fromSystem(c, () => notApplicable(THEATRE_OWN), (s) => {
        const rf = s.research_freshness;
        if (!rf.last_systematic_pass) return value("No systematic pass yet", "Only targeted searches so far.", ["No systematic pass yet"]);
        return value(fmtDate(rf.last_systematic_pass),
          rf.coverage_window ? `Research period ${fmtDate(rf.coverage_window[0])} to ${fmtDate(rf.coverage_window[1])}.` : undefined,
          [fmtDate(rf.last_systematic_pass)]);
      })) },
    { id: "lanes", label: "Source groups in that pass", basis: "common",
      basisNote: "A source group is one family of sources searched as a unit. Counted by state, in words: never a percentage or a grade, because a group waiting on a publisher and a group barely begun are different shortfalls.",
      cells: cols.map((c) => fromSystem(c, () => notApplicable(THEATRE_OWN), lanesCell)) },
    { id: "safeguards", label: "Active-campaign publication safeguards", basis: "common",
      basisNote: "Whether attack-campaign rules restrict what is published. Where they apply, an attack is published as an event, but the attacked facility's later status is not.",
      cells: cols.map(safeguardsCell) },
    { id: "placement", label: "Most precise placement of a record", basis: "common",
      basisNote: "A first-level region is a maximum, not an entitlement: where a region and a kind of facility together could name one site, attacks are kept at country level.",
      cells: cols.map(placementCell) },
    ...CONTEXT_METRICS.map((k): CompareRow => {
      const m = ctx?.metrics[k];
      return {
        id: `ctx_${k}` as CompareRowId,
        label: m ? `${m.label} (${m.unit}, ${ctx!.comparison_year})` : k.replace(/_/g, " "),
        basis: "context",
        basisNote: m ? `${m.definition}${k === "total_production" && ctx?.accounting_convention ? ` ${ctx.accounting_convention}` : ""}` : "National energy context.",
        cells: cols.map((c) => contextCell(c, ctx, ctxFailed, k)),
      };
    }),
    { id: "reporting", label: "Reporting environment", basis: "within",
      basisNote: "Which channels report disruption in this system. It shapes what can be found there; it is not a quality grade.",
      cells: cols.map((c) => value(labelFor(ENVIRONMENT_LABEL, c.entry.reporting_environment), envText(c.entry.reporting_environment))) },
    { id: "sourcing", label: "How its published records are sourced", basis: "within",
      basisNote: "Citations and originating statements behind this system's own records. A description of this record, not of the country's reporting, and not a comparison between columns.",
      cells: cols.map(sourcingCell) },
    { id: "source_checks", label: "Registered sources last checked", basis: "within",
      basisNote: "The vintage of this system's source checks. Sources checked on schedule say nothing about how much of the search is done.",
      cells: cols.map(checksCell) },
  ];
  return rows;
}

/** The rows the exported image carries: research state and national context only. */
export const EXPORT_ROW_IDS: CompareRowId[] = ["view_type", "as_of", "index", "maturity", "last_pass", "lanes",
  "safeguards", "placement", "ctx_total_production", "ctx_crude_production", "ctx_gas_production", "ctx_electricity_generation"];

export const EXPORT_NOT_COMPARABLE = "Not comparable: event counts; this is context and research state only.";
export const EXPORT_CONTEXT_CAVEAT = "National energy figures are context: a larger figure is not a more important or more disrupted country.";

export interface CompareBrief {
  title: string;
  sub: string;
  names: string[];
  /** `label` is one or two lines: a context row puts its unit and year on the second. */
  rows: { label: string[]; basis: RowBasis; cells: string[][] }[];
  /** The heading drawn above the first row of each kind. */
  groupTitles: Record<RowBasis, string>;
  foot: string[];
}

/** The text of the exported comparison, apart from the drawing so a test can read it. */
export function compareBriefLines(cols: CompareColumn[], rows: CompareRow[], ctx: EnergyContext | null, built: string): CompareBrief {
  const names = cols.map((c) => c.entry.name);
  const ctxLine = ctx
    ? `National context ${ctx.comparison_year}, one source for every country: ${ctx.source.name}, release of ${fmtDate(ctx.source.release)}.`
    : "National context could not be loaded, so no national figure is shown.";
  return {
    title: `Comparing monitored systems: ${names.join(", ")}`,
    sub: `Built ${fmtDate(localDayOf(built))}. ${ctxLine} Columns in the order chosen, never ranked.`,
    names,
    rows: rows.filter((r) => EXPORT_ROW_IDS.includes(r.id)).map((r) => {
      const unit = /^(.*) (\([^()]*\))$/.exec(r.label);
      return { label: unit ? [unit[1], unit[2]] : [r.label], basis: r.basis, cells: r.cells.map((c) => c.lines ?? [c.text]) };
    }),
    groupTitles: {
      common: "Common basis: one definition for every system",
      context: ctx ? `National energy context: ${ctx.comparison_year}, same source for every country, annual national totals` : "National energy context",
      within: "Within each system only",
    },
    foot: [
      "Research coverage differs by system and is incomplete everywhere: a missing record is not evidence that nothing happened, and a research preview's search has not yet run as far as planned.",
      `${NO_INDEX_MEANING} The one index on this site belongs to a single monitored area, is built for it alone and is not comparable, so no index value is shown here.`,
      EXPORT_NOT_COMPARABLE,
      // The page says this above the context rows; the image travels without the page.
      ...(ctx ? [EXPORT_CONTEXT_CAVEAT] : []),
      `Energy Disruption Monitor · open sources${ctx ? ` · ${ctx.source.attribution}` : ""}`,
    ],
  };
}

/** Why the comparison cannot be exported yet, or null when it can. An image drawn while a column
 *  still says "Loading" would travel with that word in it as if it were a finding. */
export function exportBlocker(cols: CompareColumn[], ctxLoaded: boolean, ctxFailed: boolean): string | null {
  if (cols.length < 2) return "Choose at least two systems first.";
  if (cols.some((c) => c.status === "loading") || (!ctxLoaded && !ctxFailed)) return "Still loading; try again in a moment.";
  return null;
}

/** The reader's order with column `i` swapped with its neighbour in direction `d`. Off either end,
 *  the order is unchanged. */
export function moveColumn(ids: string[], i: number, d: -1 | 1): string[] {
  const j = i + d;
  if (i < 0 || j < 0 || i >= ids.length || j >= ids.length) return [...ids];
  const next = [...ids];
  [next[i], next[j]] = [next[j], next[i]];
  return next;
}

export function compareFilename(cols: CompareColumn[], built: string): string {
  return `energy-systems-compared-${cols.map((c) => c.entry.id).join("-")}-${localDayOf(built) ?? "undated"}.png`;
}
