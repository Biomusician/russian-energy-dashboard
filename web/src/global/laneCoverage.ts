/** Lane states for the Research Coverage Explorer (ResearchCoverage.tsx): research coverage as a reader is told it.
 *
 *  The question this answers is "how well has this country actually been searched?", lane by lane.
 *  A lane is one family of sources searched as a unit. Each lane already carries two independent
 *  dimensions in the served log: what the analyst did (`execution`) and what the source allows
 *  (`source_window`). This file turns them into one of a few categorical states, each shown as text
 *  plus a shape. Never a percentage, never a score, never a moral colour.
 *
 *  SELF-CONTAINED ON PURPOSE. Only type imports, which are erased, so the shipped file runs as it is
 *  under plain Node: the Python suite executes it against every served system (tests/
 *  test_research_coverage.py) and the mutation campaign can therefore catch a broken rule here.
 *  Language names and source-window wording live in manifest.ts and are applied by the component.
 */
import type { CountrySystem, ResearchLane, ResearchPass } from "./manifest";

export type CoverageState =
  | "complete" | "partial" | "not_started" | "unavailable" | "stopped" | "archive_limit" | "earlier_format";

/** The order the states are explained and counted in. */
export const COVERAGE_STATES: CoverageState[] = [
  "complete", "partial", "not_started", "unavailable", "stopped", "archive_limit", "earlier_format",
];

export const COVERAGE_STATE_TEXT: Record<CoverageState, string> = {
  complete: "Declared search complete",
  partial: "Partial",
  not_started: "Not started",
  unavailable: "Source unavailable",
  stopped: "Stopped by search allowance",
  archive_limit: "Archive or listing limitation",
  earlier_format: "Logged in an earlier format",
};

export const COVERAGE_STATE_MEANING: Record<CoverageState, string> = {
  complete: "Every search or listing declared for this lane was run, in every language the lane requires. "
    + "It means the declared sources were searched, not that nothing else happened.",
  partial: "Some of the declared work was done and some was not; the lane's note says what is missing. "
    + "A partial lane can be a truthful end state rather than unfinished work: where no complete public "
    + "list of events exists, no amount of searching makes the record complete.",
  not_started: "Declared in the research plan, but no search has been run in it yet.",
  unavailable: "The source refused automated access or could not be read, for example a listing built by "
    + "script in the browser. It was not worked around, so the source itself is unread, whatever else "
    + "the lane ran.",
  stopped: "This project's own search allowance for the pass ran out before every declared search was run. "
    + "The limit is ours, not the publisher's: the remaining searches can still be run.",
  archive_limit: "The publisher keeps only a recent window of items, or lists them in a way that cannot be "
    + "read back to the start of the period, so older items could not be reached.",
  earlier_format: "This lane was last logged before the current vocabulary existed and is shown as it was "
    + "logged then.",
};

/** How a lane's universe is searched, in plain words. */
export const UNIVERSE_TEXT: Record<string, string> = {
  census: "A complete official list, read entry by entry",
  report_archive: "A publisher's archive of reports, read item by item",
  declared_query_set: "Planned searches; no complete list of events exists",
};

const COMPLETE_EXECUTION = ["enumerated_complete", "declared_search_complete"];

function list(x: unknown): string[] {
  return Array.isArray(x) ? x.filter((v): v is string => typeof v === "string") : [];
}

/** Languages the lane requires that it did not run in. Empty when every required language ran. */
export function missingLanguages(lane: ResearchLane): string[] {
  const ran = new Set(list(lane.languages_executed));
  return list(lane.languages_required).filter((c) => !ran.has(c));
}

/** The state a reader is told for one lane.
 *
 *  Order matters, and follows the build's own `lane_summary_state`: a source that refused access
 *  reads as unavailable however much else was done, and a lane stopped by our allowance is never
 *  complete. "Complete" is only ever what the lane's own execution says, and only when every
 *  required language ran and the source was readable. Anything else that is not one of the named
 *  shortfalls is partial: never promoted. */
export function coverageState(lane: ResearchLane): CoverageState {
  if (!lane.execution) {
    return "earlier_format";
  }
  const ex = lane.execution;
  const win = lane.source_window;
  if (ex === "not_started") return win === "inaccessible" ? "unavailable" : "not_started";
  if (win === "inaccessible") return "unavailable";
  if (lane.stopped_by === "search_limit") return "stopped";
  if (COMPLETE_EXECUTION.includes(ex) && win !== "unknown" && missingLanguages(lane).length === 0) {
    return "complete";
  }
  if (win === "rolling_archive_gap") return "archive_limit";
  return "partial";
}

export interface LaneRow {
  lane: ResearchLane;
  /** The pass this lane was last logged in. */
  pass: ResearchPass;
  state: CoverageState;
}

/** Each lane as it stands in the latest systematic pass that logged it. Two passes can share a
 *  date (a continuation written the day of the pass it continues); the later in the log is the
 *  newer, as in the build. Lanes keep the order of the pass that last logged them. */
export function latestLanes(passes: ResearchPass[]): LaneRow[] {
  const byLane = new Map<string, LaneRow>();
  const ordered = passes
    .map((p, i) => ({ p, i }))
    .filter(({ p }) => p.kind === "systematic")
    .sort((a, b) => (a.p.date < b.p.date ? -1 : a.p.date > b.p.date ? 1 : a.i - b.i));
  for (const { p } of ordered) {
    for (const lane of Array.isArray(p.lanes) ? p.lanes : []) {
      // Re-inserting moves the lane to the end, so delete first and the newest pass sets the order.
      byLane.delete(lane.lane);
      byLane.set(lane.lane, { lane, pass: p, state: coverageState(lane) });
    }
  }
  return [...byLane.values()];
}

export function countStates(rows: LaneRow[]): Record<CoverageState, number> {
  const out = Object.fromEntries(COVERAGE_STATES.map((s) => [s, 0])) as Record<CoverageState, number>;
  for (const r of rows) out[r.state] += 1;
  return out;
}

const CLAUSE: Record<Exclude<CoverageState, "complete">, string> = {
  stopped: "stopped by the search allowance",
  unavailable: "with the source unavailable",
  archive_limit: "limited by the source's archive or listing",
  partial: "partial",
  not_started: "not started",
  earlier_format: "logged in an earlier format",
};
const CLAUSE_ORDER: Exclude<CoverageState, "complete">[] =
  ["stopped", "unavailable", "archive_limit", "partial", "not_started", "earlier_format"];

/** "2 of 9 lanes declared complete; 2 stopped by the search allowance; …" — in words, never a ratio
 *  turned into a percentage. A state with no lane is left out rather than listed as zero, except the
 *  first clause, which is always stated. */
export function coverageSummary(rows: LaneRow[], passCount: number): string {
  if (passCount === 0) return "No search has been run yet.";
  if (rows.length === 0) return "No systematic search with declared lanes has been run yet: every search so far was targeted at named gaps and leads.";
  const n = countStates(rows);
  const parts = [`${n.complete} of ${rows.length} ${rows.length === 1 ? "lane" : "lanes"} declared complete`];
  for (const s of CLAUSE_ORDER) if (n[s] > 0) parts.push(`${n[s]} ${CLAUSE[s]}`);
  return parts.join("; ") + ".";
}

/** True for a system under the attack-campaign publication rule. Any one signal is enough:
 *  restricting more than needed is safe, restricting less is not. */
export function isCampaignRestricted(sys: Pick<CountrySystem, "research_log" | "publication_policy" | "campaign_state">): boolean {
  const passes = Array.isArray(sys.research_log?.passes) ? sys.research_log.passes : [];
  if (passes.some((p) => p.under_review !== undefined)) return true;
  if ((sys.publication_policy?.campaigns ?? []).some((c) => c.policy_applied)) return true;
  return !!sys.campaign_state && sys.campaign_state.state !== "NO_ACTIVE_CAMPAIGN";
}

export const UNDER_REVIEW_TEXT = "Additional candidates remain under review and are not shown.";

/** What one pass found, for the pass history. Under the campaign policy no count of any kind is
 *  given, whatever the log carries: beside a short list of published attack records, a count of
 *  candidates looked at or held is a hint of the campaign's scale. */
export function passOutcomeText(p: ResearchPass, restricted: boolean): string {
  if (restricted) {
    return p.under_review ? UNDER_REVIEW_TEXT : "Counts are not published for this country while attacks on energy facilities are reported.";
  }
  const o = p.outcome && typeof p.outcome === "object" ? p.outcome : {};
  const parts = Object.entries(o).map(([k, n]) => `${k.replace(/_/g, " ")} ${n}`);
  return parts.length ? parts.join(" · ") : "No counts logged.";
}

/** The review line under the summary: only the fact that review continues, and only where the
 *  newest systematic pass says so. Never a number. Outside the campaign policy, null: the event
 *  list already gives the counts there. */
export function reviewLine(sys: Pick<CountrySystem, "research_log" | "publication_policy" | "campaign_state">): string | null {
  if (!isCampaignRestricted(sys)) return null;
  const sys_ = (Array.isArray(sys.research_log?.passes) ? sys.research_log.passes : []).filter((p) => p.kind === "systematic");
  const newest = sys_[sys_.length - 1];
  return newest?.under_review ? UNDER_REVIEW_TEXT : null;
}

/** "12 of 12 planned searches run; 11,401 items listed or read". Process counts only. */
export function workDone(lane: ResearchLane): string {
  const parts: string[] = [];
  // "0 of 0 planned searches" says nothing: a census or archive lane declares no searches.
  if (typeof lane.queries_declared === "number" && lane.queries_declared > 0) {
    parts.push(`${lane.queries_run ?? 0} of ${lane.queries_declared} planned searches run`);
  }
  if (typeof lane.items_enumerated === "number") {
    const of = typeof lane.items_in_universe === "number" ? ` of ${lane.items_in_universe.toLocaleString("en-GB")}` : "";
    parts.push(`${lane.items_enumerated.toLocaleString("en-GB")}${of} items listed or read`);
  }
  return parts.join("; ");
}

// Lane notes are fixed sentences or logged provenance. These rewrite only the project's internal
// references (pass numbering, vocabulary keys) into words a reader can follow; no fact changes.
const NOTE_RULES: [RegExp, string][] = [
  [/\biteration \d+'s\b/g, "an earlier pass's"],
  [/\biteration-\d+\b/g, "earlier-pass"],
  [/\biteration \d+\b/g, "an earlier pass"],
  [/\benumerated_complete\b/g, "fully enumerated"],
  [/\bdeclared_search_complete\b/g, "declared search complete"],
  [/\bThe execution value\b/g, "This state"],
  [/\bthe two-dimension name\b/g, "the current name"],
];

export function laneNote(s: string | null | undefined): string {
  let out = s ?? "";
  for (const [re, to] of NOTE_RULES) out = out.replace(re, to);
  return out;
}
