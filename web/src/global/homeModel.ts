/** Pure helpers for the global home (iteration 21), kept out of the components so they can be
 *  tested directly. None of them produces a figure about disruption: dates, ages and placement
 *  levels only. */

import { daysBetween, fmtDate } from "../data";
import { LANE_STATE_LABEL, labelFor, type RecentEpisode } from "./manifest";

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
 *  by side it carries "National" and a row key instead of its own id and place. */
export function isCovered(ep: RecentEpisode): boolean {
  return /-row-\d+$/.test(ep.episode_id) || ep.members.some((m) => m.withheld);
}

/** How precisely an item is placed, in words. Region names are given only where the list itself
 *  carries them (never for a covered record). */
export function placementOf(ep: RecentEpisode): { level: string; names: string[] } {
  if (isCovered(ep)) return { level: "National", names: [] };
  const regions = [...new Set(ep.members.map((m) => m.region))];
  if (regions.every((r) => r === "National")) return { level: "Country level", names: [] };
  if (regions.includes("Multiple regions")) return { level: "Several regions", names: [] };
  const named = regions.filter((r) => r !== "National");
  return { level: named.length > 1 ? "First-level regions" : "First-level region", names: named };
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

// Every state the build can emit, so no lane vanishes from a summary line (iteration 19: a lane
// stopped by the search allowance was counted in the total and named nowhere). The same order on
// the home page and the Gulf cards.
const LANE_ORDER = ["universe_searched", "current_through_latest_release", "declared_query_set_run",
                    "partially_searched", "blocked_by_source", "stopped_by_search_limit", "not_started", "legacy"];

/** "3 partly searched", "5 with planned searches run (not exhaustive)". The number counts source
 *  groups. Two labels describe the searches rather than the group, and "5 planned searches run"
 *  read as five searches when it meant five source groups; "with" keeps the number on the group. */
export function laneStatePhrase(state: string, n: number): string {
  const label = labelFor(LANE_STATE_LABEL, state).toLowerCase();
  const describesSearches = state === "declared_query_set_run" || state === "universe_searched";
  return `${n} ${describesSearches ? `with ${label}` : label}`;
}

/** Lane states as one line, in the fixed order above; unknown states follow, never dropped. */
export function laneChips(states: Record<string, number>): string {
  const known = LANE_ORDER.filter((k) => states[k]);
  const extra = Object.keys(states).filter((k) => states[k] && !LANE_ORDER.includes(k)).sort();
  return [...known, ...extra].map((k) => laneStatePhrase(k, states[k])).join(" · ");
}
