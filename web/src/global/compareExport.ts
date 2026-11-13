import { fillFitted } from "./canvasText";
import type { CompareBrief } from "./compare";

/** The comparison PNG (iteration 21). There is no map: the image is the table, and like every export
 *  on this site it carries what it is and is not in its own pixels, because it travels without the
 *  page. Drawn from `compareBriefLines`, which a test reads; this file only places text. */

const BG = "#07090c";
const PANEL = "#0d1218";
const LINE = "#1b2530";
const INK = "#d4dfea";
const DIM = "#93a5b3";
const ACCENT = "#2ad4ee";
const SANS = '"Inter", system-ui, sans-serif';

export const COMPARE_PNG = { width: 1600, height: 900 } as const;

export function drawCompareFrame(brief: CompareBrief): HTMLCanvasElement {
  const W = COMPARE_PNG.width;
  const H = COMPARE_PNG.height;
  const out = document.createElement("canvas");
  out.width = W;
  out.height = H;
  const c = out.getContext("2d");
  if (!c) throw new Error("could not create a 2D context to draw the comparison");
  const pad = 24;
  const fit = (t: string, x: number, y: number, w: number) => fillFitted(c, t, x, y, w);

  c.fillStyle = BG;
  c.fillRect(0, 0, W, H);
  c.fillStyle = PANEL;
  c.fillRect(0, 0, W, 96);
  c.fillStyle = INK;
  c.font = `600 30px ${SANS}`;
  fit(brief.title, pad, 42, W - 2 * pad);
  c.fillStyle = DIM;
  c.font = `16px ${SANS}`;
  fit(brief.sub, pad, 74, W - 2 * pad);

  // Footer first, so the table knows how much room it has.
  const footLine = 20;
  const fh = brief.foot.length * footLine + 18;
  c.fillStyle = PANEL;
  c.fillRect(0, H - fh, W, fh);
  c.font = `13px ${SANS}`;
  brief.foot.forEach((t, i) => {
    // The line that says what is not comparable is the reason the image may travel: drawn in ink.
    c.fillStyle = t.startsWith("Not comparable") ? INK : DIM;
    fit(t, pad, H - fh + 22 + i * footLine, W - 2 * pad);
  });

  const labelW = 330;
  const n = Math.max(brief.names.length, 1);
  const colW = Math.floor((W - 2 * pad - labelW) / n);
  const colX = (i: number) => pad + labelW + i * colW;
  let y = 128;
  c.font = `600 17px ${SANS}`;
  c.fillStyle = ACCENT;
  brief.names.forEach((name, i) => fit(name, colX(i), y, colW - 14));
  y += 14;

  const top = y;
  const bottom = H - fh - 10;
  // A heading line above the first row of each kind, so the image keeps the page's distinction
  // between a common definition and national context.
  const heads = brief.rows.map((r, i) => i === 0 || brief.rows[i - 1].basis !== r.basis);
  const linesPerRow = brief.rows.map((r) => Math.max(r.label.length, ...r.cells.map((cl) => cl.length)));
  const total = linesPerRow.reduce((a, b) => a + b, 0) + heads.filter(Boolean).length * 1.6;
  // Rows share the space between header and footer; the line height shrinks before anything is cut.
  const gap = 8;
  const lineH = Math.min(19, (bottom - top - gap * brief.rows.length) / total);
  const size = Math.max(10, Math.round(lineH * 0.74));
  brief.rows.forEach((r, ri) => {
    if (heads[ri]) {
      c.font = `600 ${size}px ${SANS}`;
      c.fillStyle = ACCENT;
      fit(brief.groupTitles[r.basis].toUpperCase(), pad, y + lineH * 1.15, W - 2 * pad);
      y += lineH * 1.6;
    }
    c.font = `${size}px ${SANS}`;
    c.fillStyle = LINE;
    c.fillRect(pad, y, W - 2 * pad, 1);
    const base = y + gap / 2 + lineH * 0.8;
    c.fillStyle = DIM;
    r.label.forEach((t, li) => fit(t, pad, base + li * lineH, labelW - 16));
    c.fillStyle = INK;
    r.cells.forEach((cl, i) => cl.forEach((t, li) => fit(t, colX(i), base + li * lineH, colW - 14)));
    y += linesPerRow[ri] * lineH + gap;
  });
  return out;
}

export function canvasPng(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("the browser could not encode the image"))), "image/png");
  });
}
