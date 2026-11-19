import { DIM, INK, SANS, fillFitted } from "./canvasText";
import { ENVIRONMENT_LABEL, labelFor, type CountrySystem } from "./manifest";
import { DISPUTED, NO_EVENTS, type Scale } from "./countryScale";
import { fmtValue, type ContextRow, type EnergyContext } from "./context";
import { RESEARCH_PREVIEW_EXPORT_LINE, inSentence } from "./countryCopy";
import { fmtDate } from "../data";
import { PLACEMENT_LABEL } from "./placement";
import type { ImpactExportSummary } from "./countryImpactModel";

/** The frame drawn into a country PNG.
 *
 *  An exported image travels without the page around it, so whatever the page says to stop a
 *  misreading has to be in the pixels: that there is no index, what the colours count, and that
 *  the figures are not comparable with any other country. The theatre's briefing frame learned
 *  this in iteration 11; this is the same rule for a view with no headline number.
 */

const BAND = "rgba(7, 9, 12, 0.88)";

/** The country export frames the country itself, clear of the title band (96 px), the footer (up to
 *  98 px: four lines) and the colour key at top right (about 354 px wide). Copying the reader's camera tied the
 *  image to the shape of the reader's window: a short phone-width map left a small country as a few
 *  unshaded pixels in a 1600x900 frame, and the blank-capture check refused it (iteration 21). */
export const COUNTRY_EXPORT_FIT_PADDING = { top: 112, right: 380, bottom: 120, left: 32 };

/** With the impact summary drawn down the left of the image, the country is framed to its right. */
const SUMMARY_WIDTH = 640;
export const COUNTRY_EXPORT_SUMMARY_PADDING = { ...COUNTRY_EXPORT_FIT_PADDING, left: 32 + SUMMARY_WIDTH + 32 };

/** The research-preview caveat as an image carries it: the page's own definition (countryCopy.ts),
 *  without its pointer to a tab. Null for a system that is not a preview. */
export function exportPreviewLine(sys: Pick<CountrySystem, "maturity">): string | null {
  if (sys.maturity !== "research_preview") return null;
  return RESEARCH_PREVIEW_EXPORT_LINE;
}

/** Break `text` into lines no wider than `maxWidth`, measured in the live font. */
function wrap(c: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const lines: string[] = [];
  let line = "";
  for (const w of text.split(/\s+/).filter(Boolean)) {
    const next = line ? `${line} ${w}` : w;
    if (!line || c.measureText(next).width <= maxWidth) line = next;
    else { lines.push(line); line = w; }
  }
  if (line) lines.push(line);
  return lines;
}

/** The impact tab's summary, down the left of the image under the title band. Every line the
 *  model gives is drawn, wrapped to the panel: none is cut. */
function drawImpactSummary(c: CanvasRenderingContext2D, summary: ImpactExportSummary, s: number, pad: number, top: number) {
  const width = Math.round(SUMMARY_WIDTH * s);
  const inner = width - Math.round(24 * s);
  const lh = Math.round(18 * s);
  const x = pad + Math.round(12 * s);
  c.font = `600 ${Math.round(15 * s)}px ${SANS}`;
  const title = wrap(c, summary.title, inner);
  c.font = `${Math.round(13 * s)}px ${SANS}`;
  const body = summary.lines.map((l) => wrap(c, l, inner));
  const rowsHead = summary.rows.length > 0 ? 1 : 0;
  const count = title.length + body.reduce((n, b) => n + b.length, 0) + rowsHead + summary.rows.length + (summary.more ? 1 : 0);
  const gaps = body.length + rowsHead;
  c.fillStyle = BAND;
  c.fillRect(pad, top, width, count * lh + gaps * Math.round(6 * s) + Math.round(22 * s));
  let y = top + Math.round(22 * s);
  c.fillStyle = INK;
  c.font = `600 ${Math.round(15 * s)}px ${SANS}`;
  for (const l of title) { c.fillText(l, x, y); y += lh; }
  c.font = `${Math.round(13 * s)}px ${SANS}`;
  for (const b of body) {
    y += Math.round(6 * s);
    c.fillStyle = DIM;
    for (const l of b) { c.fillText(l, x, y); y += lh; }
  }
  if (summary.rows.length > 0) {
    y += Math.round(6 * s);
    c.fillStyle = DIM;
    c.fillText("Newest records: date · sector · cause · place published", x, y);
    y += lh;
    c.fillStyle = INK;
    for (const r of summary.rows) { fillFitted(c, r, x, y, inner); y += lh; }
    if (summary.more) { c.fillStyle = DIM; c.fillText(summary.more, x, y); }
  }
}

export function composeCountryFrame(map: HTMLCanvasElement, sys: CountrySystem, scale: Scale,
                                    national?: { row: ContextRow | null; ctx: EnergyContext } | null,
                                    impacts?: ImpactExportSummary | null): HTMLCanvasElement {
  const W = map.width;
  const H = map.height;
  const out = document.createElement("canvas");
  out.width = W;
  out.height = H;
  const c = out.getContext("2d");
  if (!c) throw new Error("could not create a 2D context to draw the export frame");
  c.drawImage(map, 0, 0, W, H);

  const s = W / 1600;
  const pad = Math.round(24 * s);
  // Every line fits the image whatever font the browser substitutes (canvasText.ts).
  const fit = (t: string, x: number, y: number) => fillFitted(c, t, x, y, W - x - pad);
  c.fillStyle = BAND;
  c.fillRect(0, 0, W, Math.round(96 * s));
  c.fillStyle = INK;
  c.font = `600 ${Math.round(30 * s)}px ${SANS}`;
  fit(`${sys.name} — reported major energy disruptions`, pad, Math.round(42 * s));
  c.fillStyle = DIM;
  c.font = `${Math.round(16 * s)}px ${SANS}`;
  // The count never travels without the reporting environment that produced it (§6.4).
  const env = labelFor(ENVIRONMENT_LABEL, sys.reporting_environment).toLowerCase();
  // An empty record is never "0 qualifying events ... reviewed null": the picture travels without
  // the page, so it carries the page's own sentence (release methodology red team, iteration 19).
  const passes = sys.research_log.passes.filter((p) => p.kind === "systematic");
  const last = passes[passes.length - 1];
  const held = last?.under_review !== undefined ? 0 : last?.outcome?.held ?? 0;
  const reviewing = last?.under_review === true;
  fit(
    sys.event_summary.recorded_events === 0
      ? `No index. No qualifying records in the current reviewed corpus (reporting: ${env}). ` +
        `That describes this dataset, not ${inSentence(sys.name)}` + (held > 0 ? `; ${held} candidate records are held back and not shown.` : reviewing ? "; additional candidates remain under review." : ".")
      : `No index. ${sys.event_summary.recorded_events} qualifying events in ${sys.event_summary.episodes} episodes ` +
        `(reporting: ${env}); ` +
        `records marked ${PLACEMENT_LABEL.national} or ${PLACEMENT_LABEL.several_regions}, not drawn: ${sys.event_summary.country_level}. Record reviewed ${sys.record_reviewed ? fmtDate(sys.record_reviewed) : "not yet"}.`,
    pad, Math.round(74 * s));

  // Colour key: this country's own classes, so the picture cannot be read on another's scale.
  const keys: [string, string][] = [[NO_EVENTS, "none recorded"],
    ...scale.labels.map((l, i) => [scale.colors[i], l] as [string, string]), [DISPUTED, "disputed"]];
  const kx = W - pad - Math.round(330 * s);
  let ky = Math.round(120 * s);
  c.fillStyle = BAND;
  c.fillRect(kx - Math.round(10 * s), ky - Math.round(22 * s), Math.round(340 * s), Math.round((keys.length * 20 + 34) * s));
  c.fillStyle = DIM;
  c.font = `${Math.round(13 * s)}px ${SANS}`;
  fit(`Events recorded per ${sys.geography.unit_label} (this country's range)`, kx, ky);
  for (const [color, label] of keys) {
    ky += Math.round(20 * s);
    c.fillStyle = color;
    c.fillRect(kx, ky - Math.round(11 * s), Math.round(14 * s), Math.round(14 * s));
    c.fillStyle = INK;
    fit(label, kx + Math.round(22 * s), ky);
  }

  if (impacts) drawImpactSummary(c, impacts, s, pad, Math.round(108 * s));

  // The page's badges travel with the image too: the campaign safeguards (iteration 20, production
  // export QA) and the research-preview caveat (iteration 22), each where the page shows it.
  const nat = national?.row
    ? `National energy production ${fmtValue(national.row.values.total_production, national.ctx.metrics.total_production.unit)} (${national.ctx.comparison_year}, ${national.ctx.source.name}) is context only. `
    : "";
  const footer = [
    exportPreviewLine(sys),
    exportCampaignLine(sys),
    "What was reported and found, not a rate of disruption. Counts reflect this country's " +
      "reporting rules; not comparable across countries; never ranked.",
    `${nat}Energy Disruption Monitor · open sources · boundaries: Natural Earth (line of actual control)`,
  ].filter((l): l is string => !!l);
  const fh = Math.round((18 + 20 * footer.length) * s);
  c.fillStyle = BAND;
  c.fillRect(0, H - fh, W, fh);
  c.fillStyle = DIM;
  c.font = `${Math.round(13 * s)}px ${SANS}`;
  footer.forEach((line, i) => fit(line, pad, H - Math.round((14 + 20 * (footer.length - 1 - i)) * s)));
  return out;
}

/** The campaign caveat for an exported image, or null where no campaign applies. Same condition
 *  as the page's "Active-campaign safeguards apply" badge. */
export function exportCampaignLine(sys: Pick<CountrySystem, "campaign_state">): string | null {
  if (!sys.campaign_state || sys.campaign_state.state === "NO_ACTIVE_CAMPAIGN") return null;
  return "Active-campaign safeguards apply: no restart, recovery or operating status of an attacked facility is published.";
}

export function countryFilename(sys: CountrySystem): string {
  return `energy-disruption-${sys.system_id}-${sys.as_of}.png`;
}
