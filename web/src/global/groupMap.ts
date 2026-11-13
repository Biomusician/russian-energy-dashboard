import type { GroupContext, GroupSystem } from "./manifest";

/** The regional map's colours, order and figure facts, apart from the view so a test can read them.
 *
 *  Every colour stands for exactly one thing, and the legend names each one. A member with no
 *  figure, a member whose figure is zero, a member the membership filter has set aside and a
 *  country that is not a member at all are four different statements, so they are four colours.
 */

export const MEMBER_RAMP = ["#27517a", "#2a7596", "#3c9aa5", "#69bea6", "#a9dba4"];
/** A member the source gives no figure for. Not zero. */
export const NO_DATA = "#6d6f75";
/** A member whose figure is zero: measured, and none. */
export const ZERO = "#4a4033";
/** A member the GCC/OPEC filter has set aside. Still a member; just not in this view. */
export const FILTERED = "#1d2631";
/** Every other country: geography for orientation only. */
export const OTHER = "#141c25";
/** The one colour of every member while the map shows geography only: plainly a member, plainly
 *  not a value (a grey first map was read as a broken one). */
export const NEUTRAL = "#3b5f80";

type Expr = unknown[];

/** Members in name order. The list beside the map is a way to find a country, never an order of
 *  anything: no figure takes part in it. */
export function membersAlphabetical(systems: GroupSystem[]): GroupSystem[] {
  return [...systems].sort((a, b) => a.name.localeCompare(b.name, "en"));
}

function classOf(v: number, max: number): number {
  // Five classes of magnitude down from the group's largest value. Classes, not positions.
  const f = v / max;
  return f >= 0.5 ? 4 : f >= 0.2 ? 3 : f >= 0.08 ? 2 : f >= 0.02 ? 1 : 0;
}

/** The colour of one member. `metricId` null means geography only: one colour for every member. */
export function memberColour(s: GroupSystem, metricId: string | null, inView: boolean, max: number): string {
  if (!inView) return FILTERED;
  if (!metricId) return NEUTRAL;
  const v = s.values[metricId];
  if (v == null) return NO_DATA;
  if (v === 0) return ZERO;
  return max > 0 ? MEMBER_RAMP[classOf(v, max)] : MEMBER_RAMP[0];
}

/** The MapLibre fill for the regional map. Until a reader chooses a figure it is geography only. */
export function groupFill(systems: GroupSystem[], metricId: string | null, inView: (s: GroupSystem) => boolean): Expr | string {
  if (!systems.length) return OTHER;
  const vals = metricId ? systems.map((s) => s.values[metricId]).filter((v): v is number => v != null && v > 0) : [];
  const max = Math.max(...vals, 0);
  const expr: Expr = ["match", ["get", "a3"]];
  for (const s of systems) expr.push(s.a3, memberColour(s, metricId, inView(s), max));
  expr.push(OTHER);
  return expr;
}

export interface MetricFacts {
  label: string;
  year: number;
  unit: string;
  definition: string;
  source: string;
  sourceUrl: string | null;
  release: string | null;
  /** How the source counts energy in one unit. Stated with every figure: it changes what a total means. */
  accounting: string | null;
}

/** What a reader must see beside the control whenever a figure colours the map. */
export function metricFacts(ctx: GroupContext, metricId: string): MetricFacts | null {
  const m = ctx.metrics[metricId];
  if (!m) return null;
  const src = ctx.sources[m.source_id];
  return {
    label: m.label,
    year: m.year,
    unit: m.unit,
    definition: m.definition,
    source: src?.name ?? "source not stated",
    sourceUrl: src?.url ?? null,
    release: src?.release ?? null,
    accounting: ctx.accounting_convention ?? null,
  };
}

/** Which of zero and no-data occur among the members in view, so the legend names what is drawn. */
export function specialValues(systems: GroupSystem[], metricId: string, inView: (s: GroupSystem) => boolean): { zero: boolean; noData: boolean } {
  const shown = systems.filter(inView);
  return { zero: shown.some((s) => s.values[metricId] === 0), noData: shown.some((s) => s.values[metricId] == null) };
}
