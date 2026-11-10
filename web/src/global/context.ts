/** The national energy context layer (iteration 18).
 *
 *  National aggregates from one source and one year, for context. A country here is NOT thereby
 *  monitored: `system_id` comes from the registry and is the only thing that says so. A missing
 *  value is null and renders "no data", never 0.
 *
 *  The colour scale is its own sequential ramp. It is deliberately unlike the ESDI palette, whose
 *  ambers and reds mean disruption; a large producer must not look like a damaged one.
 */

const BASE = `${import.meta.env.BASE_URL}data`;

export interface ContextRow {
  a3: string;
  name: string;
  on_map: boolean;
  system_id: string | null;
  values: Record<string, number | null>;
  newer: Record<string, { year: number; value: number }>;
  roles: { overall: Role; by_commodity: Record<string, Role> };
}
export type Role = "net_producer" | "net_consumer" | "about_balanced" | null;

export interface EnergyContext {
  schema_version: number;
  kind: string;
  statement: string;
  not_scoring: string;
  source: { id: string; name: string; url: string; release: string; retrieved: string; licence: string;
            attribution: string; update_cadence: string };
  comparison_year: number;
  comparison_year_reason: string;
  balance_band: number;
  map_metrics: string[];
  metrics: Record<string, { label: string; unit: string; definition: string; source_series: string }>;
  coverage: Record<string, number>;
  world: { values: Record<string, number | null> };
  countries: ContextRow[];
}

let contextPromise: Promise<EnergyContext> | null = null;

/** Fetched once per page. A failure is not cached, and never takes a monitored system with it. */
export function loadContext(): Promise<EnergyContext> {
  if (!contextPromise) {
    contextPromise = fetch(`${BASE}/global/energy_context.json`, { cache: "no-cache" })
      .then((r) => {
        if (!r.ok) throw new Error(`energy context: HTTP ${r.status}`);
        return r.json() as Promise<EnergyContext>;
      })
      .then((c) => {
        const bad = contextProblems(c);
        if (bad.length) throw new Error(`energy context malformed (${bad.join(", ")})`);
        return c;
      })
      .catch((err) => { contextPromise = null; throw err; });
  }
  return contextPromise;
}

/** Parts the views read unguarded. A malformed file is refused, so it fails as "unavailable". */
export function contextProblems(x: unknown): string[] {
  const c = (x ?? {}) as Partial<EnergyContext>;
  const out: string[] = [];
  if (!Number.isInteger(c.comparison_year)) out.push("no comparison year");
  if (!c.source || !c.source.name || !c.source.release) out.push("no source or release");
  if (!c.metrics || typeof c.metrics !== "object") out.push("no metrics");
  if (!Array.isArray(c.map_metrics)) out.push("no map metrics");
  if (!Array.isArray(c.countries) || c.countries.some((r) => !r || typeof r.a3 !== "string" || typeof r.values !== "object" || !r.values || !r.roles)) {
    out.push("bad country rows");
  }
  return out;
}

export const UNIT_SHORT: Record<string, string> = {
  "quadrillion Btu": "quad Btu",
  "thousand barrels per day": "kb/d",
  "billion cubic metres": "bcm",
  "million tonnes": "Mt",
  "terawatt-hours": "TWh",
};

/** A value in its unit, or "no data". Zero stays zero: it is the source's own figure. */
export function fmtValue(v: number | null | undefined, unit: string): string {
  if (v == null) return "no data";
  // A very small figure keeps its significant digits rather than printing as a false zero.
  if (v !== 0 && Math.abs(v) < 0.01) return `${Number(v.toPrecision(2))} ${UNIT_SHORT[unit] ?? unit}`;
  const digits = v !== 0 && Math.abs(v) < 10 ? 2 : v !== 0 && Math.abs(v) < 100 ? 1 : 0;
  return `${v.toLocaleString("en-GB", { maximumFractionDigits: digits })} ${UNIT_SHORT[unit] ?? unit}`;
}

// Grey for "no data" and near-black for a reported zero, so neither can pass for the other or for
// the lowest class at a glance.
export const NO_DATA = "#5a5e66";
export const ZERO = "#10161f";
const RAMP = ["#2a4466", "#27517a", "#2a7596", "#3c9aa5", "#69bea6", "#a9dba4", "#ecf4ad"];

export const MIX_FUELS: [string, string, string][] = [
  ["prod_coal", "Coal", "#8d8373"],
  ["prod_gas", "Natural gas", "#5aa9e6"],
  ["prod_oil", "Oil and liquids", "#c9a227"],
  ["prod_nuclear", "Nuclear", "#b48ef0"],
  ["prod_renewables", "Renewables and other", "#6cc46b"],
];
export const ELEC_FUELS: [string, string][] = [
  ["elec_coal", "Coal"], ["elec_gas", "Natural gas"], ["elec_oil", "Petroleum"], ["elec_nuclear", "Nuclear"],
  ["elec_hydro", "Hydro"], ["elec_wind", "Wind"], ["elec_solar", "Solar"],
];
export const ROLE_LABEL: Record<string, string> = {
  net_producer: "Produces more than it consumes",
  net_consumer: "Consumes more than it produces",
  about_balanced: "Production and consumption about balanced",
};
const ROLE_COLOR: Record<string, string> = { net_producer: "#3c9aa5", net_consumer: "#7a6fb0", about_balanced: "#8a93a0" };

export interface LegendEntry { color: string; label: string }
export interface MapMode {
  id: string;
  title: string;          // "Total primary energy production — 2024"
  unitNote: string;       // "quadrillion Btu"
  legend: LegendEntry[];
  fill: unknown[];
  /** How one row reads in this mode, for the hover line and the card. */
  describe: (r: ContextRow | undefined) => string;
}

function sig2(x: number): number {
  return Number(x.toPrecision(2));
}

/** Seven classes on a roughly logarithmic ladder down from the largest value, because national
 *  energy figures span six orders of magnitude and a linear scale would colour nearly every
 *  country the same. Classes are of magnitude; the map never labels a position. */
export function breaksFor(values: number[]): number[] {
  const max = Math.max(...values, 0);
  if (max <= 0) return [];
  return [1 / 3000, 1 / 1000, 1 / 300, 1 / 100, 1 / 30, 1 / 5].map((f) => sig2(max * f));
}

function matchFill(colorOf: (r: ContextRow) => string, rows: ContextRow[]): unknown[] {
  const groups = new Map<string, string[]>();
  for (const r of rows) {
    const c = colorOf(r);
    groups.set(c, [...(groups.get(c) ?? []), r.a3]);
  }
  const out: unknown[] = ["match", ["get", "a3"]];
  for (const [color, a3s] of groups) out.push(a3s, color);
  out.push(NO_DATA);
  return out;
}

export function numericMode(ctx: EnergyContext, metric: string): MapMode {
  const m = ctx.metrics[metric];
  const values = ctx.countries.map((r) => r.values[metric]).filter((v): v is number => v != null && v > 0);
  const breaks = breaksFor(values);
  const classOf = (v: number) => {
    let i = 0;
    while (i < breaks.length && v >= breaks[i]) i += 1;
    return i;
  };
  const colorOf = (r: ContextRow) => {
    const v = r.values[metric];
    if (v == null) return NO_DATA;
    return v === 0 ? ZERO : RAMP[classOf(v)];
  };
  const fmt = (x: number) => x.toLocaleString("en-GB");
  const legend: LegendEntry[] = [
    { color: NO_DATA, label: "no data for this year" },
    { color: ZERO, label: "zero reported" },
    ...RAMP.map((color, i) => ({
      color,
      label: i === 0 ? `under ${fmt(breaks[0])}` : i === RAMP.length - 1 ? `${fmt(breaks[i - 1])} or more`
        : `${fmt(breaks[i - 1])} to ${fmt(breaks[i])}`,
    })),
  ];
  return {
    id: metric, title: `${m.label} — ${ctx.comparison_year}`, unitNote: m.unit, legend,
    fill: matchFill(colorOf, ctx.countries),
    describe: (r) => (r ? fmtValue(r.values[metric], m.unit) : "no data"),
  };
}

export function dominantFuel(r: ContextRow): string | null {
  const total = r.values.total_production;
  if (!total) return null;
  let best: string | null = null;
  let bestV = 0;
  for (const [id] of MIX_FUELS) {
    const v = r.values[id];
    if (v != null && v > bestV) { best = id; bestV = v; }
  }
  return best;
}

export function mixMode(ctx: EnergyContext): MapMode {
  const color = Object.fromEntries(MIX_FUELS.map(([id, , c]) => [id, c]));
  const name = Object.fromEntries(MIX_FUELS.map(([id, n]) => [id, n]));
  return {
    id: "mix", title: `Largest source in energy production — ${ctx.comparison_year}`, unitNote: "category: the largest fuel by energy content",
    legend: [{ color: NO_DATA, label: "no data or no production" }, ...MIX_FUELS.map(([, label, c]) => ({ color: c, label }))],
    fill: matchFill((r) => { const f = dominantFuel(r); return f ? color[f] : NO_DATA; }, ctx.countries),
    describe: (r) => {
      if (r?.values.total_production === 0) return "no production reported";
      const f = r && dominantFuel(r);
      return f ? `largest source: ${name[f].toLowerCase()}` : "no data";
    },
  };
}

export function roleMode(ctx: EnergyContext): MapMode {
  return {
    id: "role", title: `Energy production against consumption — ${ctx.comparison_year}`,
    unitNote: `within ${Math.round(ctx.balance_band * 100)}% counts as about balanced; this compares production with consumption, not trade`,
    legend: [{ color: NO_DATA, label: "no data" },
      ...Object.entries(ROLE_LABEL).map(([k, label]) => ({ color: ROLE_COLOR[k], label }))],
    fill: matchFill((r) => (r.roles.overall ? ROLE_COLOR[r.roles.overall] : NO_DATA), ctx.countries),
    describe: (r) => (r?.roles.overall ? ROLE_LABEL[r.roles.overall].toLowerCase() : "no data"),
  };
}

export function modesFor(ctx: EnergyContext): MapMode[] {
  return [...ctx.map_metrics.map((m) => numericMode(ctx, m)), mixMode(ctx), roleMode(ctx)];
}

/** The row for a monitored system: its largest national row. China's system also holds Hong Kong
 *  and Macau, which EIA reports separately. */
export function rowForSystem(ctx: EnergyContext, id: string): ContextRow | null {
  const rows = ctx.countries.filter((r) => r.system_id === id);
  if (!rows.length) return null;
  return rows.reduce((a, b) => ((b.values.total_production ?? 0) > (a.values.total_production ?? 0) ? b : a));
}

export function mixShares(r: ContextRow): { id: string; label: string; share: number; color: string }[] {
  const total = r.values.total_production;
  if (!total) return [];
  return MIX_FUELS.map(([id, label, color]) => ({ id, label, color, share: (r.values[id] ?? 0) / total }))
    .filter((x) => x.share > 0.0005);
}
