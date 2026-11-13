/** Research coverage as a reader is told it: the ONE vocabulary for source-group states, and the
 *  lane logic of the Research Coverage tab (ResearchCoverage.tsx).
 *
 *  The question this answers is "how well has this country actually been searched?", group by
 *  group. A source group ("lane" in the data) is one family of sources searched as a unit. Each
 *  carries two independent dimensions in the served log: what the analyst did (`execution`) and
 *  what the source allows (`source_window`). The build turns them into one of eight states
 *  (`lane_summary_state` in pipeline/build_systems.py) and counts them; `coverageState` below is the
 *  same rule, so the home page, the country header, the Research coverage tab, Compare and the Gulf
 *  cards show one set of states in one set of words. Never a percentage, never a score, never a
 *  moral colour, and never one word ("complete", "finished") for states that mean different
 *  things: a planned set of searches run in full is not every published item read.
 *
 *  Every surface takes its words from here. Do not add a second label map elsewhere.
 *
 *  SELF-CONTAINED ON PURPOSE. Only type imports, which are erased, so the shipped file runs as it is
 *  under plain Node: the Python suite executes it against every served system (tests/
 *  test_research_coverage.py) and the mutation campaign can therefore catch a broken rule here.
 *  Language names and source-window wording live in manifest.ts and are applied by the component.
 */
import type { CountrySystem, ResearchLane, ResearchPass } from "./manifest";

/** What a reader calls a lane, everywhere. */
export const SOURCE_GROUP = "source group";
export const SOURCE_GROUPS = "source groups";
export function sourceGroups(n: number): string {
  return n === 1 ? SOURCE_GROUP : SOURCE_GROUPS;
}

/** The build's eight states. */
export type CoverageState =
  | "universe_searched" | "current_through_latest_release" | "declared_query_set_run" | "partially_searched"
  | "blocked_by_source" | "stopped_by_search_limit" | "not_started" | "legacy";

/** The order the states are explained and counted in, on every surface. */
export const COVERAGE_STATES: CoverageState[] = [
  "universe_searched", "current_through_latest_release", "declared_query_set_run", "partially_searched",
  "blocked_by_source", "stopped_by_search_limit", "not_started", "legacy",
];

/** The three states in which all of a group's planned work was done. They stay three: none of them
 *  means every event was found, and a planned set of searches is not an exhaustive list. */
export const DONE_STATES: CoverageState[] = ["universe_searched", "current_through_latest_release", "declared_query_set_run"];

/** One reader term per state: as a label ("Partly searched") and, lower-cased, in a count. */
export const LANE_STATE_LABEL: Record<CoverageState, string> = {
  universe_searched: "Every published item read",
  current_through_latest_release: "Searched through the publisher's latest release",
  declared_query_set_run: "Planned searches run (not exhaustive)",
  partially_searched: "Partly searched",
  blocked_by_source: "Source unavailable",
  stopped_by_search_limit: "Stopped at this site's search limit",
  not_started: "Not started",
  legacy: "Logged in an earlier format",
};

/** In a count, "5 planned searches run" reads as five searches when it means five source groups;
 *  "with" keeps the number on the group. */
const COUNT_PHRASE: Partial<Record<CoverageState, string>> = {
  universe_searched: "with every published item read",
  declared_query_set_run: "with planned searches run (not exhaustive)",
  blocked_by_source: "with the source unavailable",
};

export const COVERAGE_STATE_MEANING: Record<CoverageState, string> = {
  universe_searched: "The source is a complete official list or a publisher's archive, and every item in it for the "
    + "search period was listed or read, in every language the group requires. The list was read; that does not "
    + "mean the list holds every event.",
  current_through_latest_release: "Every item the publisher has released so far was read, in every language the group "
    + "requires, but the publisher has not yet released the rest of the search period.",
  declared_query_set_run: "Every search planned for this group was run, in every language it requires. No complete "
    + "list of events exists for it, so the searches can miss what they did not ask for: run, not exhaustive.",
  partially_searched: "Some of the planned work was done and some was not; the group's note says what is missing. "
    + "This can be a truthful end state rather than unfinished work: where the publisher keeps only a recent window, "
    + "or no complete public list of events exists, no amount of searching makes the record complete.",
  blocked_by_source: "The source refused automated access or could not be read, for example a listing built by "
    + "script in the browser. It was not worked around, so the source itself is unread, whatever else the group ran.",
  stopped_by_search_limit: "This site's own search limit for the pass was reached before every planned search was run. "
    + "The limit is ours, not the publisher's: the remaining searches can still be run.",
  not_started: "Planned, but no search has been run in it yet.",
  legacy: "This group was last logged before the current vocabulary existed and is shown as it was logged then.",
};

function isState(k: string): k is CoverageState {
  return (COVERAGE_STATES as string[]).includes(k);
}

/** "3 partly searched", "5 with planned searches run (not exhaustive)". The number counts source groups. */
export function laneStatePhrase(state: string, n: number): string {
  if (!isState(state)) return `${n} ${state.replace(/_/g, " ")}`;
  return `${n} ${COUNT_PHRASE[state] ?? LANE_STATE_LABEL[state].toLowerCase()}`;
}

/** Counts by state as one line, in the fixed order; a state this file does not know follows, never
 *  dropped. A state with no group is left out. */
export function laneChips(states: Record<string, number>): string {
  const known = COVERAGE_STATES.filter((k) => states[k]);
  const extra = Object.keys(states).filter((k) => states[k] && !isState(k)).sort();
  return [...known, ...extra].map((k) => laneStatePhrase(k, states[k])).join(" · ");
}

/** "6 source groups: 5 with planned searches run (not exhaustive) · 1 partly searched." The one
 *  summary line, wherever a system's (or every country's) groups are summed up. */
export function laneLine(states: Record<string, number>, total?: number): string {
  const n = total ?? Object.values(states).reduce((a, b) => a + (Number(b) || 0), 0);
  const chips = laneChips(states);
  return chips ? `${n} ${sourceGroups(n)}: ${chips}.` : `${n} ${sourceGroups(n)}.`;
}

/** How a group's universe is searched, in plain words. */
export const UNIVERSE_TEXT: Record<string, string> = {
  census: "A complete official list, read entry by entry",
  report_archive: "A publisher's archive of reports, read item by item",
  declared_query_set: "Planned searches; no complete list of events exists",
};

function list(x: unknown): string[] {
  return Array.isArray(x) ? x.filter((v): v is string => typeof v === "string") : [];
}

/** Languages the lane requires that it did not run in. Empty when every required language ran. */
export function missingLanguages(lane: ResearchLane): string[] {
  const ran = new Set(list(lane.languages_executed));
  return list(lane.languages_required).filter((c) => !ran.has(c));
}

/** The state a reader is told for one lane: the build's `lane_summary_state`, rule for rule.
 *
 *  Order matters: a source that refused access reads as unavailable however much else was done,
 *  and a lane stopped by our search limit is never a done state. A done state is only ever what the
 *  lane's own execution says, and, as a second line of defence behind the build's validator, only
 *  when every required language ran and the source window is known. Anything else is partly
 *  searched: never promoted. */
export function coverageState(lane: ResearchLane): CoverageState {
  if (!lane.execution) {
    return "legacy";
  }
  const ex = lane.execution;
  const win = lane.source_window;
  if (ex === "not_started") return win === "inaccessible" ? "blocked_by_source" : "not_started";
  if (win === "inaccessible") return "blocked_by_source";
  if (lane.stopped_by === "search_limit") return "stopped_by_search_limit";
  const doneOk = win !== "unknown" && missingLanguages(lane).length === 0;
  if (ex === "enumerated_complete" && doneOk) {
    return win === "publisher_not_yet_released" ? "current_through_latest_release" : "universe_searched";
  }
  if (ex === "declared_search_complete" && doneOk) return "declared_query_set_run";
  return "partially_searched";
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

/** The tab's summary line: the same line every other surface shows, from the same states. Counts
 *  in words, never a ratio turned into a percentage, and no "N of M complete": the done states are
 *  three different claims and are never added up into one. */
export function coverageSummary(rows: LaneRow[], passCount: number): string {
  if (passCount === 0) return "No search has been run yet.";
  if (rows.length === 0) return "No systematic search with declared source groups has been run yet: every search so far was targeted at named gaps and leads.";
  return laneLine(countStates(rows), rows.length);
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
export const WAS_UNDER_REVIEW_TEXT = "Candidates were under review when this pass was logged; none is shown.";

/** What one pass found, for the pass history. Under the campaign policy no count of any kind is
 *  given, whatever the log carries: beside a short list of published attack records, a count of
 *  candidates looked at or held is a hint of the campaign's scale. */
export function passOutcomeText(p: ResearchPass, restricted: boolean, current = true): string {
  if (restricted) {
    // "Remain under review" is a claim about now, so only the newest systematic pass may make it;
    // an older pass's flag is history, said in the past tense.
    if (p.under_review) return current ? UNDER_REVIEW_TEXT : WAS_UNDER_REVIEW_TEXT;
    return "Counts are not published for this country while attacks on energy facilities are reported.";
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
