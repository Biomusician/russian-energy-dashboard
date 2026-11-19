import { DIM, INK, SANS, fillFitted } from "../../canvasText";
import { countryImpactBrief, gulfImpactBrief, type CountryBriefInput, type GulfBriefInput, type ImpactBrief } from "./impactBrief";

/** The impact brief as an image (iteration 22). There is no map: the brief is text, and like every
 *  export on this site it carries what it is and is not in its own pixels, because it is forwarded
 *  without the page. This file only places the lines `impactBrief.ts` wrote.
 *
 *  A claim is wrapped, never cut: half a sourced sentence is a different sentence. The image grows
 *  downwards to hold what it has to say; the caveat band is drawn last, at the foot, on every brief.
 */

const BG = "#07090c";
const PANEL = "#0d1218";
const LINE = "#1b2530";
const ACCENT = "#2ad4ee";

export const IMPACT_BRIEF = { width: 1600, minHeight: 900 } as const;

const PAD = 24;
const HEAD_H = 96;
const LINE_H = 21;
const HEADING_H = 26;
const BLOCK_GAP = 18;
const FOOT_LINE = 21;
const BODY = `14px ${SANS}`;
const STRONG = `600 14px ${SANS}`;
const HEADING = `600 14px ${SANS}`;

/** Break `text` into lines no wider than `maxWidth`, at spaces only. A single word wider than the
 *  line stays whole on its own line; `fillFitted` then shrinks that line rather than cut it. */
export function wrapText(c: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const out: string[] = [];
  let line = "";
  for (const word of text.split(/\s+/).filter(Boolean)) {
    const next = line ? `${line} ${word}` : word;
    if (line && c.measureText(next).width > maxWidth) {
      out.push(line);
      line = word;
    } else {
      line = next;
    }
  }
  if (line) out.push(line);
  return out;
}

interface Placed { text: string; x: number; y: number; font: string; fill: string; rule?: boolean }

function layoutColumn(c: CanvasRenderingContext2D, blocks: ImpactBrief["columns"][number], x: number, width: number, top: number): { ops: Placed[]; bottom: number } {
  const ops: Placed[] = [];
  let y = top;
  for (const b of blocks) {
    ops.push({ text: b.heading.toUpperCase(), x, y: y + 16, font: HEADING, fill: ACCENT, rule: true });
    y += HEADING_H;
    for (const l of b.lines) {
      const font = l.strong ? STRONG : BODY;
      c.font = font;
      for (const t of wrapText(c, l.text, width)) {
        ops.push({ text: t, x, y: y + 15, font, fill: l.dim ? DIM : INK });
        y += LINE_H;
      }
    }
    y += BLOCK_GAP;
  }
  return { ops, bottom: y };
}

export function drawImpactBrief(brief: ImpactBrief): HTMLCanvasElement {
  const W = IMPACT_BRIEF.width;
  const out = document.createElement("canvas");
  out.width = W;
  out.height = IMPACT_BRIEF.minHeight;
  const measure = out.getContext("2d");
  if (!measure) throw new Error("could not create a 2D context to draw the impact brief");

  // Measure first: the height follows the text, so no statement is cut to fit a fixed page.
  const colW = Math.floor((W - 3 * PAD) / 2);
  const left = layoutColumn(measure, brief.columns[0], PAD, colW, HEAD_H + 20);
  const right = layoutColumn(measure, brief.columns[1], PAD * 2 + colW, colW, HEAD_H + 20);
  const footH = brief.caveats.length * FOOT_LINE + 20;
  const H = Math.max(IMPACT_BRIEF.minHeight, Math.ceil(Math.max(left.bottom, right.bottom)) + footH);

  // Resizing a canvas clears it and resets its context, so the drawing starts from a known state.
  out.height = H;
  const c = out.getContext("2d");
  if (!c) throw new Error("could not create a 2D context to draw the impact brief");
  c.fillStyle = BG;
  c.fillRect(0, 0, W, H);
  c.fillStyle = PANEL;
  c.fillRect(0, 0, W, HEAD_H);
  c.fillStyle = INK;
  c.font = `600 30px ${SANS}`;
  fillFitted(c, brief.title, PAD, 42, W - 2 * PAD);
  c.fillStyle = DIM;
  c.font = `16px ${SANS}`;
  fillFitted(c, brief.sub, PAD, 74, W - 2 * PAD);

  for (const op of [...left.ops, ...right.ops]) {
    if (op.rule) {
      c.fillStyle = LINE;
      c.fillRect(op.x, op.y + 6, colW, 1);
    }
    c.font = op.font;
    c.fillStyle = op.fill;
    fillFitted(c, op.text, op.x, op.y, colW);
  }

  // The caveat band: every line, whole, in ink. It is the reason the image may be forwarded.
  c.fillStyle = PANEL;
  c.fillRect(0, H - footH, W, footH);
  c.fillStyle = ACCENT;
  c.fillRect(0, H - footH, W, 2);
  c.font = `13px ${SANS}`;
  brief.caveats.forEach((t, i) => {
    c.fillStyle = i === brief.caveats.length - 1 ? DIM : INK;
    fillFitted(c, t, PAD, H - footH + 24 + i * FOOT_LINE, W - 2 * PAD);
  });
  return out;
}

export function drawGulfImpactBrief(input: GulfBriefInput): HTMLCanvasElement {
  return drawImpactBrief(gulfImpactBrief(input));
}

/** Usable for any system, and for a country that is not a monitored system at all. */
export function drawCountryImpactBrief(input: CountryBriefInput): HTMLCanvasElement {
  return drawImpactBrief(countryImpactBrief(input));
}
