/** Draw the briefing frame INTO the exported image (iteration 11 P10).
 *
 *  WHY THIS FILE EXISTS. P8 shipped an exporter that captured the MapLibre canvas and wrote it
 *  straight to a file. The framing — metric, dates, caveat, scope, Crimea note, sources — lived
 *  in DOM sitting on top of the map, so it was on the reader's screen and NOT in the PNG. The
 *  file that left the application was a bare choropleth: a coloured map of Russia with no
 *  statement anywhere that it measures exposure rather than damage. That is the precise failure
 *  the whole feature was built to prevent, and it survived because the live overlay was checked
 *  instead of the exported pixels.
 *
 *  Everything is drawn with the 2D canvas API. No DOM rasteriser, no library, no external font —
 *  the project forbids runtime dependencies, and a text layout this simple does not need one.
 *  Fonts are system stacks, so an export renders with whatever the reader's machine has; the
 *  layout is measured at draw time rather than assumed, so a wider or narrower face still fits.
 *
 *  The frame is drawn at a scale derived from the image width, so a 2560-wide export gets
 *  proportionally sized text rather than the same pixel heights floating in a bigger picture.
 */

import type { BriefingContext, BriefingOptions } from "./briefing";
import { fmtDate } from "./data";

const SANS = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
const MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace';

const INK = "#e8edf2";
const DIM = "#93a4b5";
const FAINT = "#6f8296";
const AMBER = "#f0b429";
const PANEL = "rgba(3, 5, 7, 0.82)";

/** Wrap `text` to `maxWidth`, returning the lines. Measured against the live context, so it is
 *  correct for whichever font actually resolved rather than an assumed character width. */
function wrap(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let line = "";
  for (const w of words) {
    const next = line ? `${line} ${w}` : w;
    if (ctx.measureText(next).width <= maxWidth || !line) {
      line = next;
    } else {
      lines.push(line);
      line = w;
    }
  }
  if (line) lines.push(line);
  return lines;
}

/** A soft dark band behind text so it stays readable over any choropleth colour. */
function band(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number) {
  ctx.fillStyle = PANEL;
  ctx.fillRect(x, y, w, h);
}

interface DrawnLine {
  text: string;
  font: string;
  color: string;
  lineHeight: number;
  gapBefore?: number;
}

/** Compose the map bitmap and the briefing frame into one image.
 *
 *  Returns a NEW canvas; the source canvas is never mutated, because it belongs to a MapLibre
 *  instance that is about to be destroyed and may be read again for verification first.
 */
export function drawBriefingFrame(
  map: HTMLCanvasElement, ctx0: BriefingContext, options: BriefingOptions,
): HTMLCanvasElement {
  const W = map.width;
  const H = map.height;
  const out = document.createElement("canvas");
  out.width = W;
  out.height = H;
  const c = out.getContext("2d");
  if (!c) throw new Error("could not create a 2D context to draw the briefing frame");

  c.drawImage(map, 0, 0, W, H);

  // One scale factor for the whole frame, so a 2560-wide export is proportionally typeset
  // rather than the 1920 layout adrift in a larger canvas.
  const s = W / 1920;
  const pad = Math.round(28 * s);
  const maxText = W - pad * 2;

  // ---- header -------------------------------------------------------------------------
  let headerBottom = 0;
  if (options.title) {
    const titleFont = `600 ${Math.round(34 * s)}px ${SANS}`;
    const metricFont = `${Math.round(17 * s)}px ${SANS}`;
    const valueFont = `600 ${Math.round(40 * s)}px ${MONO}`;
    const dateFont = `${Math.round(15 * s)}px ${SANS}`;

    const hBand = Math.round(112 * s);
    band(c, 0, 0, W, hBand);

    c.textBaseline = "alphabetic";
    c.fillStyle = INK;
    c.font = titleFont;
    c.fillText(ctx0.title, pad, Math.round(46 * s));

    c.fillStyle = DIM;
    c.font = metricFont;
    c.fillText(ctx0.metricLabel, pad, Math.round(74 * s));

    // Right-hand block: the number, then the dates it describes.
    c.textAlign = "right";
    let ry = Math.round(50 * s);
    if (ctx0.metricValue) {
      c.fillStyle = INK;
      c.font = valueFont;
      c.fillText(ctx0.metricValue, W - pad, ry);
      ry += Math.round(24 * s);
    }
    c.font = dateFont;
    c.fillStyle = DIM;
    if (ctx0.analyticalDate) {
      // §4: a scrubbed view is a historical value and the image must never read as current.
      c.fillText(`analytical date ${fmtDate(ctx0.analyticalDate)}`, W - pad, ry);
      c.fillStyle = FAINT;
      c.fillText(`data as of ${fmtDate(ctx0.asOf)}`, W - pad, ry + Math.round(20 * s));
      ry += Math.round(20 * s);
    } else {
      c.fillText(`as of ${fmtDate(ctx0.asOf)}`, W - pad, ry);
    }
    c.textAlign = "left";
    headerBottom = hBand;
  }

  // ---- comparison / episode / selection blocks ----------------------------------------
  let y = headerBottom + Math.round(18 * s);
  const blockFont = `${Math.round(16 * s)}px ${SANS}`;
  const eyebrowFont = `600 ${Math.round(11 * s)}px ${SANS}`;
  const strongFont = `600 ${Math.round(22 * s)}px ${MONO}`;

  if (options.comparisonSummary && ctx0.comparison) {
    const cmp = ctx0.comparison;
    const cells: [string, string, string][] = [
      ["DATE A", fmtDate(cmp.aResolved), cmp.aValue],
      ["DATE B", fmtDate(cmp.bResolved), cmp.bValue],
      ["Δ = B − A", "", cmp.delta],
    ];
    const cellW = Math.round(210 * s);
    const hBlock = Math.round(78 * s);
    band(c, pad, y, cellW * cells.length + Math.round(24 * s), hBlock);
    let cx = pad + Math.round(12 * s);
    for (const [label, date, value] of cells) {
      c.fillStyle = FAINT;
      c.font = eyebrowFont;
      c.fillText(label.toUpperCase(), cx, y + Math.round(20 * s));
      c.fillStyle = DIM;
      c.font = `${Math.round(13 * s)}px ${MONO}`;
      if (date) c.fillText(date, cx, y + Math.round(40 * s));
      c.fillStyle = INK;
      c.font = strongFont;
      c.fillText(value, cx, y + Math.round(66 * s));
      cx += cellW;
    }
    y += hBlock + Math.round(8 * s);
    if (cmp.resolvedNote) {
      c.fillStyle = AMBER;
      c.font = `${Math.round(13 * s)}px ${SANS}`;
      for (const ln of wrap(c, cmp.resolvedNote, maxText)) {
        c.fillText(ln, pad, y + Math.round(13 * s));
        y += Math.round(18 * s);
      }
      y += Math.round(6 * s);
    }
  }

  if (ctx0.episode) {
    const e = ctx0.episode;
    const lines = [
      { text: "RECOVERY EPISODE", font: eyebrowFont, color: FAINT },
      { text: e.facility, font: `600 ${Math.round(19 * s)}px ${SANS}`, color: INK },
      {
        text: `${e.assetClass ? `${e.assetClass} · ` : ""}disrupted ${fmtDate(e.disruptionDate)}`,
        font: `${Math.round(14 * s)}px ${SANS}`, color: FAINT,
      },
      // The family and the outcome are the point: "service restored" is not "facility rebuilt",
      // and an estimated horizon is not an observation.
      { text: `${e.familyLabel} — ${e.outcome}`, font: blockFont, color: DIM },
    ];
    let wBlock = 0;
    for (const l of lines) { c.font = l.font; wBlock = Math.max(wBlock, c.measureText(l.text).width); }
    const hBlock = Math.round(24 * s) * lines.length + Math.round(16 * s);
    band(c, pad, y, Math.min(maxText, wBlock + Math.round(24 * s)), hBlock);
    c.fillStyle = AMBER;
    c.fillRect(pad, y, Math.round(3 * s), hBlock);
    let ly = y + Math.round(26 * s);
    for (const l of lines) {
      c.font = l.font;
      c.fillStyle = l.color;
      c.fillText(l.text, pad + Math.round(12 * s), ly);
      ly += Math.round(24 * s);
    }
    y += hBlock + Math.round(10 * s);
  }

  if (options.selectionLabel && ctx0.selection) {
    c.font = blockFont;
    const wSel = c.measureText(ctx0.selection).width + Math.round(24 * s);
    const hSel = Math.round(34 * s);
    band(c, pad, y, Math.min(maxText, wSel), hSel);
    c.fillStyle = INK;
    c.fillText(ctx0.selection, pad + Math.round(12 * s), y + Math.round(23 * s));
    y += hSel + Math.round(10 * s);
  }

  if (ctx0.buildDelta) {
    // §16: present only when lineage is provable. Its absence is silent by design.
    const t = `Since last build (${fmtDate(ctx0.buildDelta.previousAsOf)} → `
      + `${fmtDate(ctx0.buildDelta.currentAsOf)}): ${ctx0.buildDelta.delta}`;
    c.font = `${Math.round(14 * s)}px ${SANS}`;
    const wB = c.measureText(t).width + Math.round(24 * s);
    const hB = Math.round(30 * s);
    band(c, pad, y, Math.min(maxText, wB), hB);
    c.fillStyle = DIM;
    c.fillText(t, pad + Math.round(12 * s), y + Math.round(20 * s));
  }

  // ---- footer: the part that must never be croppable ------------------------------------
  const footLines: DrawnLine[] = [];
  const caveatFont = `600 ${Math.round(15 * s)}px ${SANS}`;
  const noteFont = `${Math.round(13 * s)}px ${SANS}`;

  c.font = caveatFont;
  for (const ln of wrap(c, ctx0.caveat, maxText)) {
    footLines.push({ text: ln, font: caveatFont, color: AMBER, lineHeight: Math.round(21 * s) });
  }
  if (options.scopeNote) {
    c.font = noteFont;
    for (const ln of wrap(c, ctx0.scopeNote, maxText)) {
      footLines.push({ text: ln, font: noteFont, color: DIM, lineHeight: Math.round(18 * s) });
    }
    if (ctx0.crimeaNote) {
      for (const ln of wrap(c, ctx0.crimeaNote, maxText)) {
        footLines.push({ text: ln, font: noteFont, color: DIM, lineHeight: Math.round(18 * s) });
      }
    }
  }
  if (options.sourceFooter) {
    const srcFont = `${Math.round(12 * s)}px ${SANS}`;
    c.font = srcFont;
    for (const ln of wrap(c, ctx0.sourceFooter, maxText)) {
      footLines.push({ text: ln, font: srcFont, color: FAINT, lineHeight: Math.round(16 * s) });
    }
  }

  const footH = footLines.reduce((a, l) => a + l.lineHeight, 0) + Math.round(26 * s);
  const footTop = H - footH;
  // A gradient rather than a hard edge, so the map reads continuously into the caption.
  const grad = c.createLinearGradient(0, footTop - Math.round(40 * s), 0, footTop);
  grad.addColorStop(0, "rgba(3, 5, 7, 0)");
  grad.addColorStop(1, PANEL);
  c.fillStyle = grad;
  c.fillRect(0, footTop - Math.round(40 * s), W, Math.round(40 * s));
  band(c, 0, footTop, W, footH);

  let fy = footTop + Math.round(20 * s);
  for (const l of footLines) {
    c.font = l.font;
    c.fillStyle = l.color;
    c.fillText(l.text, pad, fy);
    fy += l.lineHeight;
  }

  return out;
}
