/** Briefing context: everything an exported image needs to survive detached from the app.
 *
 *  THE GOVERNING RULE. A PNG that leaves this application carries no tooltips, no methodology
 *  page and no operator. Whatever it fails to say, a reader will guess — and the guesses are
 *  predictable: that the index measures capacity lost, that a falling number means repairs, that
 *  a transmission figure is percent-of-grid-offline. So the caveat travels in the image, chosen
 *  for the metric actually displayed rather than a single disclaimer applied to everything.
 *
 *  Pure functions over authoritative state. No component computes a caveat or a filename inline;
 *  this module is the one place either is decided, and it is unit-tested.
 */

import type { Bundle, HistorySeries, ResolvedPoint } from "./types";
import { fmtDate, fmtNum } from "./data";

export interface BriefingOptions {
  title: boolean;
  selectionLabel: boolean;
  scopeNote: boolean;
  legend: boolean;
  sourceFooter: boolean;
  comparisonSummary: boolean;
}

/** Defaults produce a clean analytical graphic. Deliberately few switches (§9). */
export const DEFAULT_OPTIONS: BriefingOptions = {
  title: true,
  selectionLabel: true,
  scopeNote: true,
  legend: true,
  sourceFooter: true,
  comparisonSummary: true,
};

export interface BriefingContext {
  title: string;
  metricId: string;
  metricLabel: string;
  metricValue: string | null;
  /** What the dataset itself is current to. */
  asOf: string;
  /** The analytical date being displayed, when it differs from as-of. */
  analyticalDate: string | null;
  exportedAt: string;
  caveat: string;
  scopeNote: string;
  crimeaNote: string | null;
  sourceFooter: string;
  comparison: ComparisonSummary | null;
  buildDelta: BuildDeltaSummary | null;
  selection: string | null;
  provenance: Record<string, string | null>;
}

export interface ComparisonSummary {
  aRequested: string;
  aResolved: string;
  bRequested: string;
  bResolved: string;
  aValue: string;
  bValue: string;
  delta: string;
  resolvedNote: string | null;
  mode: string;
}

export interface BuildDeltaSummary {
  previousAsOf: string;
  currentAsOf: string;
  delta: string;
}

export const METRIC_LABEL: Record<string, string> = {
  esdi: "Energy System Disruption Exposure Index",
  esdi_delta_30d: "Change in modelled disruption exposure · 30 days",
  esdi_delta_90d: "Change in modelled disruption exposure · 90 days",
  incidents: "Recorded events",
};

/** One caveat per metric, not one disclaimer for everything (§7). Each names the specific
 *  misreading that metric invites. */
export const METRIC_CAVEAT: Record<string, string> = {
  esdi: "Modelled disruption exposure — capacity AT disrupted sites, not measured capacity loss.",
  esdi_delta_30d:
    "Change in modelled disruption exposure. Not necessarily observed physical damage or repair; "
    + "impairment also decays with time.",
  esdi_delta_90d:
    "Change in modelled disruption exposure. Not necessarily observed physical damage or repair; "
    + "impairment also decays with time.",
  incidents: "Count of recorded events. Not a measure of severity or of capacity affected.",
};

export const TRANSMISSION_CAVEAT =
  "Transmission disruption burden is an event-burden proxy, not percent of grid offline.";

export const PIPELINE_CAVEAT =
  "Pipeline routes combine mapped, generalised and schematic source geometry; generalised "
  + "segments are not precise surveyed routes.";

export const HISTORICAL_CAVEAT =
  "Reconstructed with the current dataset and methodology. Not an archive of what was known at "
  + "those dates.";

/** §8: concise, and never dropped for a tidier graphic. */
export const CRIMEA_NOTE =
  "Crimea is internationally recognised as part of Ukraine and is shown separately; its "
  + "inclusion in the Monitored-Area index is an analytical choice.";

export const SCOPE_NOTE =
  "Monitored area: Belarus, western Russia and the Siberian Federal District, plus occupied "
  + "Crimea. Aggregated to administrative region.";

export const SOURCE_FOOTER =
  "Public open sources only. Boundaries: Natural Earth. Grid and pipelines: OpenStreetMap "
  + "(ODbL), cross-referenced with Global Energy Monitor. Generation: WRI GPPD (CC BY 4.0). "
  + "Events: Wikipedia (CC BY-SA 4.0).";

function sanitize(part: string): string {
  return part.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

/** Deterministic, informative, filesystem-safe (§20). */
export function briefingFilename(ctx: BriefingContext, ext = "png"): string {
  const base = "energy-disruption-monitor";
  if (ctx.comparison) {
    return `${base}_${sanitize(ctx.comparison.aResolved)}_to_`
      + `${sanitize(ctx.comparison.bResolved)}.${ext}`;
  }
  const date = ctx.analyticalDate ?? ctx.asOf;
  const metric = ctx.metricId === "esdi_delta_30d" ? "30d-change"
    : ctx.metricId === "esdi_delta_90d" ? "90d-change"
    : sanitize(ctx.metricId);
  return `${base}_${sanitize(date)}_${metric}.${ext}`;
}

/** Which caveats a given view needs. Order matters: the metric's own caveat leads. */
export function caveatsFor(opts: {
  metricId: string;
  transmissionVisible: boolean;
  pipelinesVisible: boolean;
  historical: boolean;
}): string[] {
  const out = [METRIC_CAVEAT[opts.metricId] ?? METRIC_CAVEAT.esdi];
  if (opts.transmissionVisible) out.push(TRANSMISSION_CAVEAT);
  if (opts.pipelinesVisible) out.push(PIPELINE_CAVEAT);
  if (opts.historical) out.push(HISTORICAL_CAVEAT);
  return out;
}

export function buildBriefingContext(args: {
  bundle: Bundle;
  step: number;
  currentDate: string;
  metricId: string;
  selectedRegion: string | null;
  selectionLabel: string | null;
  pipelinesVisible: boolean;
  history: HistorySeries | null;
  compare: { a: string; b: string; mode: string } | null;
  pointA: ResolvedPoint | null;
  pointB: ResolvedPoint | null;
  /** Wall-clock at export time. Passed in rather than read here so the function stays pure. */
  now: string;
}): BriefingContext {
  const { bundle, step, currentDate, metricId, compare, pointA, pointB, history } = args;
  const asOf = bundle.snapshot.as_of;
  const isLive = currentDate === asOf;

  let metricValue: string | null = null;
  if (metricId === "esdi") {
    metricValue = fmtNum(bundle.national.esdi[step] ?? 0, 2);
  } else if (metricId === "incidents") {
    metricValue = String(bundle.snapshot.incident_total ?? "");
  }

  let comparison: ComparisonSummary | null = null;
  if (compare && pointA && pointB && history) {
    const a = history.esdi[pointA.step] ?? 0;
    const b = history.esdi[pointB.step] ?? 0;
    const d = +(b - a).toFixed(2);
    comparison = {
      aRequested: compare.a,
      aResolved: pointA.resolved_series_date,
      bRequested: compare.b,
      bResolved: pointB.resolved_series_date,
      aValue: fmtNum(a, 2),
      bValue: fmtNum(b, 2),
      delta: (d > 0 ? "+" : d < 0 ? "−" : "±") + Math.abs(d).toFixed(2),
      // Only stated when a requested day actually differed from the series point used.
      resolvedNote: (!pointA.exact || !pointB.exact)
        ? `Weekly series: requested ${compare.a} and ${compare.b} resolved to `
          + `${pointA.resolved_series_date} and ${pointB.resolved_series_date}.`
        : null,
      mode: compare.mode,
    };
  }

  // §16: a build delta is exported ONLY with provable lineage. "No prior build" is a fact about
  // this repository's git state, not an analytical finding, and must never leave the app as one.
  const bc = bundle.buildChanges;
  const buildDelta = (bc && bc.lineage?.valid && bc.esdi_delta !== null
    && bc.previous_as_of && bc.current_as_of)
    ? {
      previousAsOf: bc.previous_as_of,
      currentAsOf: bc.current_as_of,
      delta: (bc.esdi_delta > 0 ? "+" : bc.esdi_delta < 0 ? "−" : "±")
        + Math.abs(bc.esdi_delta).toFixed(2),
    }
    : null;

  const transmissionVisible = (bundle.snapshot.sectors_covered ?? []).includes("transmission");
  const caveats = caveatsFor({
    metricId,
    transmissionVisible: transmissionVisible && metricId === "esdi",
    pipelinesVisible: args.pipelinesVisible,
    historical: !!comparison || !isLive,
  });

  // Crimea is in the monitored area and contributes to the index, so the note applies whenever
  // the monitored-area figure is shown. It is never dropped to tidy the graphic.
  const crimeaInScope = bundle.regions.some((r) => /crimea/i.test(r.name));

  return {
    title: "Energy Disruption Monitor",
    metricId,
    metricLabel: METRIC_LABEL[metricId] ?? metricId,
    metricValue,
    asOf,
    analyticalDate: isLive ? null : currentDate,
    exportedAt: args.now,
    caveat: caveats.join(" "),
    scopeNote: SCOPE_NOTE,
    crimeaNote: crimeaInScope ? CRIMEA_NOTE : null,
    sourceFooter: SOURCE_FOOTER,
    comparison,
    buildDelta,
    selection: args.selectionLabel,
    provenance: {
      build_sha: bc?.lineage?.current_commit ?? null,
      data_as_of: asOf,
      analytical_date: isLive ? asOf : currentDate,
      exported_at: args.now,
      metric: metricId,
      schema_version: String(bundle.snapshot.schema_version ?? ""),
    },
  };
}

/** Human-readable summary line, used in the print header and as the image alt text. */
export function briefingSummaryLine(ctx: BriefingContext): string {
  const parts = [ctx.metricLabel];
  if (ctx.metricValue) parts.push(ctx.metricValue);
  parts.push(ctx.analyticalDate
    ? `analytical date ${fmtDate(ctx.analyticalDate)} (data as of ${fmtDate(ctx.asOf)})`
    : `as of ${fmtDate(ctx.asOf)}`);
  return parts.join(" · ");
}


/** Pixel dimensions and device ratio for an export request (§11, §12).
 *
 *  A NAMED size means those pixels. Multiplying 1920x1080 by a 1.25 device ratio produced a
 *  2400x1350 file — sharper, but not what someone building a 1920x1080 slide asked for. The
 *  viewport option is the opposite case: it should match what the reader is looking at, at their
 *  screen's sharpness, so it keeps the device ratio.
 *
 *  Either way the map renders at the final pixel count directly; nothing is captured small and
 *  scaled up afterwards, which is what makes an export look soft.
 */
export function exportPixelSize(
  size: string, viewportW: number, viewportH: number, dpr: number,
): { width: number; height: number; pixelRatio: number } {
  if (size === "viewport") {
    return {
      width: viewportW,
      height: viewportH,
      pixelRatio: Math.max(1, Math.min(2, dpr || 1)),
    };
  }
  const [w, h] = size.split("x").map(Number);
  return { width: w, height: h, pixelRatio: 1 };
}
