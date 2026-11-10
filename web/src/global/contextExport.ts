import type { EnergyContext, MapMode } from "./context";

/** The frame drawn into a world-context PNG. An image travels without the page, so the caveats
 *  are in the pixels: what the colour is, its year and source, which systems are monitored, and
 *  that a coloured country is not a monitored one (iteration 18). */

const INK = "#d4dfea";
const DIM = "#93a5b3";
const BAND = "rgba(7, 9, 12, 0.88)";
const SANS = '"Inter", system-ui, sans-serif';

export function composeContextFrame(map: HTMLCanvasElement, ctx: EnergyContext, mode: MapMode,
                                    monitored: string[]): HTMLCanvasElement {
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
  c.fillStyle = BAND;
  c.fillRect(0, 0, W, Math.round(96 * s));
  c.fillStyle = INK;
  c.font = `600 ${Math.round(30 * s)}px ${SANS}`;
  c.fillText(`Global energy context: ${mode.title}`, pad, Math.round(42 * s));
  c.fillStyle = DIM;
  c.font = `${Math.round(16 * s)}px ${SANS}`;
  c.fillText(`${mode.unitNote}. National statistics, ${ctx.comparison_year}. ${ctx.source.name}, release of ${ctx.source.release}.`,
             pad, Math.round(74 * s));

  const kx = W - pad - Math.round(300 * s);
  let ky = Math.round(120 * s);
  c.fillStyle = BAND;
  c.fillRect(kx - Math.round(10 * s), ky - Math.round(22 * s), Math.round(310 * s), Math.round((mode.legend.length * 20 + 56) * s));
  c.fillStyle = DIM;
  c.font = `${Math.round(13 * s)}px ${SANS}`;
  c.fillText("Colour key", kx, ky);
  for (const l of mode.legend) {
    ky += Math.round(20 * s);
    c.fillStyle = l.color;
    c.fillRect(kx, ky - Math.round(11 * s), Math.round(14 * s), Math.round(14 * s));
    c.fillStyle = INK;
    c.fillText(l.label, kx + Math.round(22 * s), ky);
  }
  ky += Math.round(22 * s);
  c.strokeStyle = "#f4f7fb";
  c.lineWidth = Math.max(2, Math.round(2.5 * s));
  c.strokeRect(kx, ky - Math.round(11 * s), Math.round(14 * s), Math.round(14 * s));
  c.fillStyle = INK;
  c.fillText("Systematically monitored", kx + Math.round(22 * s), ky);

  const fh = Math.round(58 * s);
  c.fillStyle = BAND;
  c.fillRect(0, H - fh, W, fh);
  c.fillStyle = DIM;
  c.font = `${Math.round(13 * s)}px ${SANS}`;
  c.fillText(`Monitored for disruptions: ${monitored.join(", ")}. Other countries are context only: no disruption record, not zero disruptions.`,
             pad, H - Math.round(34 * s));
  c.fillText("Energy production is context, never a measure of disruption, importance or exposure. Energy Disruption Monitor · boundaries: Natural Earth (line of actual control); Crimea drawn as Ukrainian, occupied",
             pad, H - Math.round(14 * s));
  return out;
}

export function contextFilename(ctx: EnergyContext, mode: MapMode): string {
  return `global-energy-context-${mode.id}-${ctx.comparison_year}.png`;
}
