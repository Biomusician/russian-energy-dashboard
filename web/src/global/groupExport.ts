import { fillFitted } from "./canvasText";
import { fmtValue } from "./context";
import type { GroupContext } from "./manifest";

/** The frame drawn into a regional brief PNG (iteration 19). An image travels without the page,
 *  so what it is and is not is written into the pixels: national totals, one year, one source,
 *  no facilities, no routes, and no status of anything. */

const INK = "#d4dfea";
const DIM = "#93a5b3";
const BAND = "rgba(7, 9, 12, 0.9)";
const SANS = '"Inter", system-ui, sans-serif';

/** The text lines of the brief, apart from the drawing so a test can read them. */
export function groupBriefLines(ctx: GroupContext, metricId: string): { title: string; sub: string; rows: string[]; foot: string[] } {
  const m = ctx.metrics[metricId];
  const src = ctx.sources[m.source_id];
  const r = ctx.region[metricId];
  return {
    title: `${ctx.label} energy context: ${m.label}, ${m.year}`,
    sub: `${m.unit}. National annual totals. ${src?.name ?? "source not stated"}${src?.release ? `, release of ${src.release}` : ""}.`,
    rows: ctx.systems.map((s) => `${s.name}: ${fmtValue(s.values[metricId], m.unit)}`
      + `${s.gcc_member ? " · GCC" : ""}${s.opec_member ? " · OPEC" : ""}`
      + `${s.maturity === "research_preview" ? " · research preview" : ""}`),
    foot: [
      // The share travels on the same line as what it is not, because the image travels without the
      // page (iteration 20, owner question D-24).
      r.value != null ? `All ${ctx.systems.length} together: ${fmtValue(r.value, m.unit)}${r.world_share != null ? `, ${Math.round(r.world_share * 1000) / 10}% of the world total (a descriptive annual share for the group, not an order of importance or exposure)` : ""}.`
        // A share of an energy total depends on how nuclear and renewables are counted (iteration 20).
        + (m.unit === "quadrillion Btu" && r.world_share != null ? " EIA accounting: nuclear counted by its heat, wind, solar and hydro by their electricity." : "")
        : `Not summed: ${r.reason}.`,
      "Countries in alphabetical order. No index is published for any of them. Event counts are not comparable between countries.",
      "National context only: no facilities, no routes or shipping, no current status of any facility. Energy Disruption Monitor · boundaries: Natural Earth (line of actual control).",
    ],
  };
}

export function composeGroupFrame(map: HTMLCanvasElement, ctx: GroupContext, metricId: string): HTMLCanvasElement {
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
  const lines = groupBriefLines(ctx, metricId);
  c.fillStyle = BAND;
  c.fillRect(0, 0, W, Math.round(96 * s));
  c.fillStyle = INK;
  c.font = `600 ${Math.round(30 * s)}px ${SANS}`;
  fit(lines.title, pad, Math.round(42 * s));
  c.fillStyle = DIM;
  c.font = `${Math.round(16 * s)}px ${SANS}`;
  fit(lines.sub, pad, Math.round(74 * s));

  const kw = Math.round(430 * s);
  const kx = W - pad - kw;
  let ky = Math.round(130 * s);
  c.fillStyle = BAND;
  c.fillRect(kx - Math.round(12 * s), ky - Math.round(24 * s), kw + Math.round(12 * s), Math.round((lines.rows.length * 24 + 20) * s));
  c.font = `${Math.round(15 * s)}px ${SANS}`;
  c.fillStyle = INK;
  for (const row of lines.rows) {
    fit(row, kx, ky);
    ky += Math.round(24 * s);
  }

  const fh = Math.round(82 * s);
  c.fillStyle = BAND;
  c.fillRect(0, H - fh, W, fh);
  c.fillStyle = DIM;
  c.font = `${Math.round(13 * s)}px ${SANS}`;
  lines.foot.forEach((t, i) => fit(t, pad, H - fh + Math.round((22 + i * 20) * s)));
  return out;
}
