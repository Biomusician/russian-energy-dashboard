/** "What this page can tell you": the overview at the top of every country page (iteration 22).
 *
 *  A reader who opens a country with no published record used to meet an empty list. The overview
 *  says, in this order: what is published here and why it may be nothing; what else the page holds
 *  (one line and one link each); and what is not published, with the reason.
 *
 *  It is one model for every system, driven by what the build serves: how many records are
 *  published, whether the attack-campaign safeguards apply, whether the impact corpus has been read
 *  and holds anything for this country, whether the system belongs to the regional-context group.
 *  No country is named in the code.
 *
 *  SHORT ON PURPOSE. The whole block has to fit above the map on a phone, so each part is a
 *  sentence or a one-line link. The long explanations stay where they were: the notices under the
 *  headline, the empty-corpus page and the Research coverage tab.
 *
 *  TWO RULES THE TESTS RUN.
 *  - Under the attack-campaign safeguards nothing here depends on what a research pass logged about
 *    candidates or held records: not a count, and not whether any exist. The same words are
 *    rendered whatever the log carries.
 *  - The impact corpus is separate. Its count is said beside the words "separate, non-scored
 *    corpus" and never added to, or shown in place of, the country's published-record count.
 *
 *  Pure, with type imports and import-free vocabulary modules only: the Python tests run this file
 *  in Node as it ships.
 */
import type { CountrySystem } from "./manifest";
import { inSentence } from "./countryCopy";
import { isCampaignRestricted } from "./laneCoverage";
import { TAB_LABEL, type RegionalGroup, type Tab } from "./countryTabs";

/** What the page knows about the impact corpus for this country. The file is fetched on demand, so
 *  "not read yet" is a state of its own and is never shown as "none". */
export type ImpactPresence =
  | { state: "not_loaded" }
  | { state: "loading" }
  | { state: "failed" }
  | { state: "ready"; records: number; attempts: number; latestResearch: string | null };

type OverviewSystem = Pick<CountrySystem,
  "name" | "event_summary" | "campaign_state" | "publication_policy" | "research_log" | "research_freshness" | "geography">;

export interface OverviewLink {
  tab: Tab;
  label: string;
  line: string;
}

export interface Overview {
  /** What is published for this country: one sentence. */
  published: string;
  /** Why that may be nothing, or what the published records are. */
  publishedNote: string;
  known: OverviewLink[];
  /** What is not published, each with its reason. */
  withheld: string[];
}

export const OVERVIEW_TITLE = "What this page can tell you";
export const NO_RECORD_IS_NOT_NO_DISRUPTION = "No record is not no disruption.";

const plural = (n: number, one: string, many: string) => (n === 1 ? one : many);

function listOf(parts: string[]): string {
  if (parts.length <= 1) return parts[0] ?? "";
  return `${parts.slice(0, -1).join(", ")} and ${parts[parts.length - 1]}`;
}

/** The impact tab's own empty sentence. */
export function noImpactRecordText(name: string): string {
  return `No reviewed impact record is published for ${inSentence(name)} yet. That describes this corpus, not ${inSentence(name)}.`;
}

/** What the impact tab says before it lists anything, and what an export of it carries. */
export const IMPACT_CORPUS_LINE =
  "Reviewed impact records from a separate, non-scored corpus. They are not part of this country's published "
  + "energy-disruption record and enter no count or index.";

/** Why an event can be in the impact tab and not in the country's own record (iteration 22 closure).
 *
 *  Iteration 23 (XL-07, C11): this used to give the impact layer's broader contract as the reason,
 *  beside a country whose own search could not read its main sources. Two layers have two searches
 *  as well as two rules, and the line names both. */
export const IMPACT_INCLUSION_LINE =
  "This country's published energy disruptions follow the country system's own inclusion rule and its own research passes. "
  + "The impact layer has its own contract (energy and essential civilian services, cyber, technical and natural causes) and its own "
  + "research, so an event can appear here and not there: because the impact layer covers more, or because the country's own search "
  + "did not reach or could not read the sources that report it. Impact records never enter a score.";

/** One line about the impact corpus, by what is known. A count only once the file has been read,
 *  and always beside the words that say it is another corpus. */
export function impactLine(name: string, impacts: ImpactPresence): string {
  if (impacts.state === "failed") return "the impact corpus could not be loaded; the rest of this page is unaffected.";
  if (impacts.state !== "ready") return "reviewed impact records, in a separate, non-scored corpus.";
  if (impacts.records === 0 && impacts.attempts === 0) return `no impact record yet, which describes that corpus, not ${inSentence(name)}.`;
  const parts: string[] = [];
  if (impacts.records > 0) parts.push(`${impacts.records} reviewed impact ${plural(impacts.records, "record", "records")}`);
  if (impacts.attempts > 0) parts.push(`${impacts.attempts} documented ${plural(impacts.attempts, "attempt", "attempts")}`);
  return `${parts.join(" and ")}, in a separate, non-scored corpus.`;
}

/** Why the search may have missed things, from the served research state: the most specific cause
 *  first. Empty when every declared source group was searched.
 *
 *  Iteration 23 (C11): an empty page used to lead with "the inclusion rule is strict" where the
 *  served research state says source groups could not be read. */
function searchReasons(sys: OverviewSystem): string[] {
  if (sys.research_log.passes.length === 0) return ["no systematic search has been run yet"];
  const rf = sys.research_freshness;
  const blocked = (rf.lane_states ?? {}).blocked_by_source ?? 0;
  const out: string[] = [];
  // No number: the overview counts nothing on a page with no record, and the Research coverage
  // tab gives the groups by state.
  if (blocked > 0) {
    out.push(`${blocked === 1 ? "a source group" : "some source groups"} could not be read in the latest search `
      + "(the source refused automated access or did not load)");
  }
  if (rf.completeness !== "complete") out.push("the latest search pass is partial");
  return out;
}

/** The registered-source line of the Research status block (iteration 23, C10). A registry
 *  re-check confirms each source's entry and its terms are current; it is not a reading of the
 *  source, so the words say "re-checked in the registry", and a source group the latest search
 *  could not read is said beside it rather than hidden behind a green "all checked". */
export function sourceCheckLine(registered: number, overdue: number, blockedGroups: number): string {
  const head = overdue > 0
    ? `${overdue} of ${registered} registered sources overdue for a registry re-check`
    : `All ${registered} registered sources re-checked in the registry on schedule`;
  const blocked = blockedGroups > 0
    ? ` A registry re-check is not a reading of the source: ${blockedGroups} source ${blockedGroups === 1 ? "group" : "groups"} could not be read in the latest search.`
    : "";
  return `${head}.${blocked}`;
}

export function countryOverview(sys: OverviewSystem, impacts: ImpactPresence, regional: RegionalGroup | null): Overview {
  const name = inSentence(sys.name);
  const n = sys.event_summary.recorded_events;
  const restricted = isCampaignRestricted(sys);
  const attacksWhole = sys.geography.precision_policy?.kinetic === "country";

  let published: string;
  let publishedNote: string;
  if (n === 0) {
    published = `No energy-disruption record is published for ${name} yet.`;
    // What the research state says comes first; the rule and the safeguards are conditions, not
    // a finding that nothing qualified.
    const why = [...searchReasons(sys), "only disruptions that meet the inclusion rule are published"];
    if (restricted) why.push("attack-campaign safeguards apply");
    publishedNote = `Why: ${listOf(why)}. ${NO_RECORD_IS_NOT_NO_DISRUPTION}`;
  } else {
    published = `${n} reviewed energy-disruption ${plural(n, "record is", "records are")} published for ${name}.`;
    // The safeguards are named once, under "Not published, and why": the block has to stay short.
    publishedNote = "What was reported and found, not everything that happened.";
  }

  const known: OverviewLink[] = [{ tab: "impacts", label: TAB_LABEL.impacts, line: impactLine(sys.name, impacts) }];
  if (regional) known.push({ tab: "regional", label: TAB_LABEL.regional, line: "regional statements; no facility named." });
  known.push({ tab: "context", label: TAB_LABEL.context, line: "system size, never disruption." });
  known.push({ tab: "research", label: TAB_LABEL.research, line: "what was and was not searched." });

  const withheld: string[] = [];
  if (restricted) {
    // Identical whatever the research log holds: beside a short list of published attack records, a
    // count of what is in review, or even the fact that something is, hints at the campaign's scale.
    const items = attacksWhole
      ? ["where in the country an attack happened", "the facility's later status"]
      : ["an attacked facility's later status"];
    items.push("whether, or how many, records are in review");
    withheld.push(`While attacks on energy facilities are reported: ${listOf(items)}.`);
  } else {
    withheld.push("Records still in review, until they pass review.");
  }
  withheld.push("Never: coordinates, or anything finer than a region.");

  return { published, publishedNote, known, withheld };
}

/** Every sentence of the overview, in reading order: what a test reads. */
export function overviewText(o: Overview): string[] {
  return [o.published, o.publishedNote, ...o.known.map((k) => `${k.label}: ${k.line}`), ...o.withheld];
}
