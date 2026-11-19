import { daysBetween, fmtDate } from "../data";
import { indexMoveText } from "../indexText";
import type { WhatsNewChange, WhatsNewImpactChange, WhatsNewImpactItem, WhatsNewItem, WhatsNewSystem } from "./manifest";
import { itemPlace } from "./placement";

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
  let s = `${recordDate(it.date)} · ${itemPlace(it.region)} · ${it.class}`;
  if (it.fields?.length) s += ` — corrected: ${it.fields.join(", ")}`;
  if (it.recovery_kind) {
    s += ` — ${it.recovery_kind}`;
    if (it.evidence_date) s += `; the report describes ${recordDate(it.evidence_date)}`;
  }
  return s;
}

// ---- record and section links (iteration 22) ------------------------------------------------------

/** The link to one record on its country page: `?sys=<id>#ev-<record id>`, the address the
 *  record's own "Link to this record" gives (`eventAnchor` in evidence.ts; a test holds the two
 *  together). Null without an id: under the campaign rule the file carries none, and the row is
 *  plain text. */
export function recordHref(systemId: string, it: WhatsNewItem): string | null {
  if (!it.record_id) return null;
  return `?sys=${encodeURIComponent(systemId)}#ev-${it.record_id.replace(/[^A-Za-z0-9_-]/g, "-")}`;
}

/** Where the page explains a kind of change: a tab of the country's own page, or a section of
 *  this one. Null when the file names none. Never a record. */
export function changeLink(c: WhatsNewChange): { href: string; label: string; samePage: boolean } | null {
  const l = c.link;
  if (!l) return null;
  if (l.system_id && l.tab === "research") {
    return { href: `?sys=${encodeURIComponent(l.system_id)}#tab-research`, label: "Open Research coverage", samePage: false };
  }
  if (l.system_id && l.tab === "method") {
    return { href: `?sys=${encodeURIComponent(l.system_id)}#tab-method`, label: "How this country is assessed", samePage: false };
  }
  if (l.anchor && /^[A-Za-z][A-Za-z0-9_-]*$/.test(l.anchor)) {
    return { href: `#${l.anchor}`, label: "How this works", samePage: true };
  }
  return null;
}

// ---- the impact layer (iteration 22) ------------------------------------------------------------------

/** "Moderate" from "MODERATE", "Not applicable" from "NOT_APPLICABLE": the vocabulary is data, so
 *  an id this build has not met is still shown in words, never dropped. */
export function statusWord(id: string | null | undefined): string {
  if (!id) return "not stated";
  const s = id.replace(/_/g, " ").toLowerCase();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** The line under an impact category. A set is called historical, or new, only when every record
 *  in it is; a first release is its one sentence and nothing else. */
export function impactSummary(c: WhatsNewImpactChange): string {
  if (c.category !== "impact_record_added" || c.first_release) return "";
  if (c.all_backfill) return "All are historical records found by research: the record catching up, not new events.";
  if (c.all_new_events) return "Events dated within 30 days of first publication.";
  return "Some are historical records found by research and some are new events; each row says which.";
}

export function impactItemText(it: WhatsNewImpactItem, category: string): string {
  const where = [it.country, it.sector ? it.sector.replace(/_/g, " ") : null].filter(Boolean).join(" · ");
  let s = `${recordDate(it.date)}${where ? ` · ${where}` : ""}`;
  if (category === "impact_record_added") {
    // "Unknown" says nothing either way: neither date supports a claim.
    if (it.timing === "backfill") s += " — historical record found by research, not a new event";
    else if (it.timing === "new_event") s += " — new event";
    if (it.timing && it.timing !== "unknown" && it.first_published) s += `; first published ${recordDate(it.first_published)}`;
  } else if (it.from && it.to) {
    const what = category === "attribution_updated" ? "attribution"
      : category === "ai_status_updated" ? "AI involvement" : "evidence confidence";
    s += ` — ${what}: ${statusWord(it.from)} → ${statusWord(it.to)}`;
    // An update to what is known about an event that was already published.
    if (category === "attribution_updated" || category === "ai_status_updated") s += " (existing record, not a new incident)";
  }
  return s;
}

/** The theatre's index before and after, with what the movement can and cannot be read as. */
export function indexText(row: WhatsNewSystem): string | null {
  const ix = row.index;
  if (!ix || ix.before == null || ix.after == null) return null;
  return indexMoveText(ix.label, ix.before, ix.after, ix.separable);
}
