import { daysBetween, fmtDate, fmtNum } from "../data";
import type { WhatsNewChange, WhatsNewItem, WhatsNewSystem } from "./manifest";

/** Reader-facing text for the "What's new in the data" panel (iteration 21). Pure, so the
 *  wording that carries the panel's distinctions is tested without a browser. */

/** How old this build is, on the reader's own clock. Never computed at build time: a build-time
 *  age reads "today" for ever on a page that has stopped rebuilding. */
export function buildAgeText(currentAsOf: string | null, readerToday: string): string {
  if (!currentAsOf || !/^\d{4}-\d{2}-\d{2}$/.test(currentAsOf) || !/^\d{4}-\d{2}-\d{2}$/.test(readerToday)) return "";
  const d = daysBetween(currentAsOf, readerToday);
  if (d < -1) return "dated after today on your device's clock";
  if (d <= 0) return "built today, by your device's clock";
  return `built ${d} ${d === 1 ? "day" : "days"} ago, by your device's clock`;
}

/** A record's date at the precision it has: "Apr 2026" for a month, never a made-up day. */
export function recordDate(date: string | null | undefined): string {
  return fmtDate(date ?? null);
}

/** The line under a category: dates for new records, never a count. */
export function changeSummary(c: WhatsNewChange): string {
  if (c.category === "records_added" && c.event_dates) {
    const [a, b] = c.event_dates;
    const span = a === b ? `dated ${recordDate(a)}` : `dated ${recordDate(a)} to ${recordDate(b)}`;
    return c.all_predate_previous_build
      ? `${span}. All dated before the previous build: the record catching up, not new disruption.`
      : `${span}. Found by research; the dates are when the events happened.`;
  }
  return "";
}

export function itemText(it: WhatsNewItem): string {
  let s = `${recordDate(it.date)} · ${it.region} · ${it.class}`;
  if (it.fields?.length) s += ` — corrected: ${it.fields.join(", ")}`;
  if (it.recovery_kind) {
    s += ` — ${it.recovery_kind}`;
    if (it.evidence_date) s += `; the report describes ${recordDate(it.evidence_date)}`;
  }
  return s;
}

/** The theatre's index before and after, with what the movement can and cannot be read as. */
export function indexText(row: WhatsNewSystem): string | null {
  const ix = row.index;
  if (!ix || ix.before == null || ix.after == null) return null;
  if (ix.before === ix.after) return `${ix.label} unchanged at ${fmtNum(ix.after, 2)}.`;
  const base = `${ix.label} ${fmtNum(ix.before, 2)} to ${fmtNum(ix.after, 2)}.`;
  return ix.separable ? base : `${base} The method changed too, so the movement cannot be split between data and method.`;
}
