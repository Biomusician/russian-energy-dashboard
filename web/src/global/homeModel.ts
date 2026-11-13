/** Pure helpers for the global home (iteration 21), kept out of the components so they can be
 *  tested directly. None of them produces a figure about disruption: dates, ages and placement
 *  levels only. */

import { daysBetween, fmtDate } from "../data";
import type { RecentEpisode } from "./manifest";
import { PLACEMENT_LABEL, type Placement } from "./placement";

/** "today", "1 day ago", "12 days ago", on the reader's own calendar day. A date in the reader's
 *  future (their clock is behind the build's) gets no age rather than a negative one. */
export function ageText(iso: string | null | undefined, today: string): string {
  if (!iso || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return "";
  const n = daysBetween(iso, today);
  if (n < 0) return "";
  return n === 0 ? "today" : n === 1 ? "1 day ago" : `${n} days ago`;
}

export function dated(label: string, iso: string, today: string): string {
  const age = ageText(iso, today);
  return `${label} ${fmtDate(iso)}${age ? ` · ${age}` : ""}`;
}

/** What a country card says about its record. `undefined` = the build predates the field, so
 *  the card says nothing rather than guess; `null` = the system has no qualifying record. */
export function recordLine(recordReviewed: string | null | undefined, today: string): string | null {
  if (recordReviewed === undefined) return null;
  if (recordReviewed === null) return "No qualifying records yet";
  return dated("Record reviewed", recordReviewed, today);
}

/** A record published under an attack campaign's safeguards. In a list that sets countries side
 *  by side it carries "National" and a row key instead of its own id and place.
 *
 *  Read from the members' `withheld` flag, never from the row key: the Gulf littoral list gives
 *  every row a key, campaign-covered or not, so a key alone would label an ordinary grid fault as
 *  an attack-campaign record. On the home list the two agree row for row. */
export function isCovered(ep: RecentEpisode): boolean {
  return ep.members.some((m) => m.withheld);
}

/** How precisely an item is placed, in the shared placement words (placement.ts). Region names
 *  are given only where the list itself carries them, never for a covered record. An episode whose
 *  records sit in different places says each kind ("National + One region"); `kind` is null then. */
export function placementOf(ep: RecentEpisode): { level: string; names: string[]; kind: Placement | null } {
  const one = (k: Placement, names: string[] = []) => ({ level: PLACEMENT_LABEL[k], names, kind: k });
  if (isCovered(ep)) return one("national_safeguarded");
  const regions = [...new Set(ep.members.map((m) => m.region))];
  const national = regions.includes("National");
  const multi = regions.includes("Multiple regions");
  const named = regions.filter((r) => r !== "National" && r !== "Multiple regions");
  if (named.length === 0) return one(multi && !national ? "several_regions" : "national");
  if (named.length === 1 && !national && !multi) return one("one_region", named);
  const parts: string[] = [];
  if (national) parts.push(PLACEMENT_LABEL.national);
  if (multi) parts.push(PLACEMENT_LABEL.several_regions);
  parts.push(named.length === 1 ? PLACEMENT_LABEL.one_region : `${PLACEMENT_LABEL.one_region} per record`);
  return { level: parts.join(" + "), names: named, kind: null };
}

export type FeedRow =
  | { kind: "item"; ep: RecentEpisode }
  // Consecutive covered items of one country, as one line. Deliberately no count: a run of
  // "National" rows is itself a tally of an attack campaign.
  | { kind: "covered-run"; system_id: string; country: string; first_date: string; last_date: string;
      date_precision: string; classes: string[]; causes: string[]; key: string };

/** The feed with each run of two or more consecutive covered items of one country collapsed. */
export function collapseCovered(episodes: RecentEpisode[]): FeedRow[] {
  const out: FeedRow[] = [];
  let i = 0;
  while (i < episodes.length) {
    const ep = episodes[i];
    if (!isCovered(ep)) { out.push({ kind: "item", ep }); i++; continue; }
    let j = i + 1;
    while (j < episodes.length && isCovered(episodes[j]) && episodes[j].system_id === ep.system_id) j++;
    if (j - i === 1) { out.push({ kind: "item", ep }); i = j; continue; }
    const run = episodes.slice(i, j);
    // The feed is newest first, so the run's last item is its earliest.
    out.push({
      kind: "covered-run", system_id: ep.system_id, country: ep.country,
      first_date: run[run.length - 1].first_date, last_date: ep.last_date,
      date_precision: run.some((r) => r.date_precision === "month") ? "month" : "day",
      classes: [...new Set(run.flatMap((r) => r.classes))].sort(),
      causes: [...new Set(run.flatMap((r) => r.causes))].sort(),
      key: `${ep.system_id}:run:${ep.last_date}:${i}`,
    });
    i = j;
  }
  return out;
}
