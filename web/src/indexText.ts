import { fmtDate, fmtNum } from "./data";
import { localDayOf } from "./freshness";

/** Reader text for the theatre's index values (iteration 21 methodology red team). Pure, so the
 *  rules that keep a small value from reading as a zero are tested without a browser. */

/** An index or sector value at the headline's one decimal, except that a value above zero but
 *  below 0.05 reads "<0.1", not "0.0". "0.0" would claim "measured, nothing disrupted" for a
 *  region or sector that has a live contribution (electric generation at 0.03, a region at 0.01).
 *  An exact zero stays "0.0": that one was measured. Null stays a dash: never computed. */
export function fmtIndex(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  if (v > 0 && v < 0.05) return "<0.1";
  return fmtNum(v, 1);
}

/** Why an unscored sector's events are not in the headline, without claiming events that do not
 *  exist. The Russia corpus has gas events and no coal events; the old sentence said both had
 *  "documented events". `eventCount` is the build's own per-sector count (coverage matrix);
 *  undefined when the build did not publish one, and then nothing is claimed either way. */
export function excludedSectorEventsText(eventCount: number | null | undefined): string {
  if (eventCount == null) return "Any events recorded in this sector are not scored.";
  if (eventCount === 0) {
    return "No event in this sector is recorded. The sector is not measured, so that is not evidence that none occurred.";
  }
  return `${eventCount} recorded ${eventCount === 1 ? "event" : "events"} in this sector ${eventCount === 1 ? "is" : "are"} not scored.`;
}

/** The ribbon's "since last build" baseline is the build immediately before this one, which can
 *  share this build's data date. "What's new" on the home page compares with the last build dated
 *  before this one, so the two can show different movements on the same day (±0.00 here, 6.8 to
 *  6.7 there). The tooltip names this baseline so an analyst can tell which is which. */
export function buildDeltaTitle(previousBuild: string | null | undefined): string {
  const day = localDayOf(previousBuild);
  return `What changed since the previous build${day ? ` (built ${fmtDate(day)})` : ""}. ` +
    "The home page's What's new compares with the last build dated before this one, so its movement can differ.";
}

/** The theatre row of "What's new": levels at the headline's one decimal, the movement at two.
 *  The headline is published to one decimal because the modelled decay does not support a second
 *  ("Why this number?" says so); printing the levels as "6.80 to 6.69" contradicted that. The
 *  change keeps two decimals so a small movement is not rounded away to "±0.0". */
export function indexMoveText(label: string, before: number, after: number, separable: boolean): string {
  const d = +(after - before).toFixed(2);
  if (d === 0) return `${label} unchanged at ${fmtNum(after, 1)}.`;
  const sign = d > 0 ? "+" : "−";
  const base = `${label} ${fmtNum(before, 1)} to ${fmtNum(after, 1)} (${sign}${Math.abs(d).toFixed(2)}).`;
  return separable ? base : `${base} The method changed too, so the movement cannot be split between data and method.`;
}
