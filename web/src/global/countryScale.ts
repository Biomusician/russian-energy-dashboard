/** Colour classes for one country's recorded-event counts (iteration 14).
 *
 *  WHY PER COUNTRY. One fixed scale (0 / 1 / 2-3 / 4-6 / 7+) for every country put two PNGs side
 *  by side on a shared axis: Saudi Arabia and Canada drew hot while China, with a media-only
 *  reporting environment, could not. That is the cross-country comparison the methodology
 *  forbids (GLOBAL_METHODOLOGY §6.4, rule 2), drawn in colour. So each country's classes come
 *  from its own range, and the legend prints the numbers each colour stands for.
 */

export const NO_EVENTS = "#16202a";
export const DISPUTED = "#2b2b33";
const POSITIVE = ["#14484f", "#157c7f", "#a8871f", "#c26326"];

export interface Scale {
  /** Lower bound of each positive class, strictly increasing, starting at 1. */
  thresholds: number[];
  colors: string[];
  labels: string[];
}

export function scaleFor(counts: number[]): Scale {
  const max = Math.max(0, ...counts);
  if (max === 0) return { thresholds: [], colors: [], labels: [] };
  const n = Math.min(POSITIVE.length, max);
  const thresholds = Array.from({ length: n }, (_, i) => 1 + Math.floor((i * max) / n));
  const colors = POSITIVE.slice(POSITIVE.length - n);
  const labels = thresholds.map((t, i) => {
    const hi = i + 1 < n ? thresholds[i + 1] - 1 : max;
    return hi === t ? `${t}` : `${t}–${hi}`;
  });
  return { thresholds, colors, labels };
}

/** The MapLibre fill expression for a scale: null (disputed, unassigned) apart, 0 its own colour. */
export function fillFor(scale: Scale): unknown[] | string {
  const step: unknown[] = ["step", ["get", "recorded_events"], NO_EVENTS];
  scale.thresholds.forEach((t, i) => step.push(t, scale.colors[i]));
  return ["case", ["==", ["get", "recorded_events"], null], DISPUTED, step];
}
