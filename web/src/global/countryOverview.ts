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
 *  TWO RULES THE TESTS RUN.
 *  - Under the attack-campaign safeguards nothing here depends on what a research pass logged about
 *    candidates or held records: not a count, and not whether any exist. The same page is rendered
 *    whatever the log carries.
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

export const IMPACTS_NOT_LOADED: ImpactPresence = { state: "not_loaded" };

type OverviewSystem = Pick<CountrySystem,
  "name" | "event_summary" | "campaign_state" | "publication_policy" | "research_log" | "research_freshness" | "geography">;

export interface OverviewLink {
  tab: Tab;
  label: string;
  line: string;
}

export interface Overview {
  /** The first sentence: what is published for this country. */
  published: string;
  /** With no published record: why that may be. Empty when records are published. */
  reasons: string[];
  /** The sentence that closes the first part. */
  publishedNote: string;
  known: OverviewLink[];
  withheld: string[];
}

export const OVERVIEW_TITLE = "What this page can tell you";
export const NO_RECORD_IS_NOT_NO_DISRUPTION = "No record is not no disruption.";

const plural = (n: number, one: string, many: string) => (n === 1 ? one : many);

/** The impact tab's own empty sentence, shared with the overview so the two cannot drift. */
export function noImpactRecordText(name: string): string {
  return `No reviewed impact record is published for ${inSentence(name)} yet. That describes this corpus, not ${inSentence(name)}.`;
}

export const IMPACT_CORPUS_LINE =
  "Reviewed impact records from a separate, non-scored corpus. They are not part of this country's published "
  + "energy-disruption record and enter no count or index.";

/** One line about the impact corpus, by what is known. A count only once the file has been read. */
export function impactLine(name: string, impacts: ImpactPresence): string {
  if (impacts.state === "failed") return "The impact corpus could not be loaded. The rest of this page is unaffected.";
  if (impacts.state !== "ready") {
    return "Disruptions to civilian services and cyber incidents, from a separate, non-scored corpus. Open it to see what is published.";
  }
  if (impacts.records === 0 && impacts.attempts === 0) return noImpactRecordText(name);
  const parts: string[] = [];
  if (impacts.records > 0) parts.push(`${impacts.records} reviewed impact ${plural(impacts.records, "record", "records")}`);
  if (impacts.attempts > 0) parts.push(`${impacts.attempts} documented ${plural(impacts.attempts, "attempt", "attempts")} with no reported service disruption`);
  return `${parts.join(" and ")} in a separate, non-scored corpus: not part of the published record above, and in no count or index.`;
}

/** Why the search may have missed things, from the served research state. Null when every declared
 *  source group was searched. */
function searchReason(sys: OverviewSystem): string | null {
  if (sys.research_log.passes.length === 0) return "No systematic search has been run yet.";
  const rf = sys.research_freshness;
  const states = rf.lane_states ?? {};
  if ((states.blocked_by_source ?? 0) > 0) {
    return "Sources are hard to reach: at least one source group could not be read at all, and the search is unfinished.";
  }
  if (rf.completeness !== "complete") return "The search is unfinished: not every source group has been fully searched.";
  return null;
}

export function countryOverview(sys: OverviewSystem, impacts: ImpactPresence, regional: RegionalGroup | null): Overview {
  const name = inSentence(sys.name);
  const n = sys.event_summary.recorded_events;
  const restricted = isCampaignRestricted(sys);
  const attacksWhole = sys.geography.precision_policy?.kinetic === "country";

  let published: string;
  const reasons: string[] = [];
  let publishedNote: string;
  if (n === 0) {
    published = `No energy-disruption record is published for ${name} yet.`;
    reasons.push("The inclusion rule is strict: a reported event is published only when it meets the rule and passes independent review.");
    if (restricted) {
      reasons.push(attacksWhole
        ? "Attack-campaign safeguards apply: a reported attack is published only as a record for the country as a whole, with nothing about the facility's later status."
        : "Attack-campaign safeguards apply: a reported attack is published with nothing about the facility's later status.");
    }
    const search = searchReason(sys);
    if (search) reasons.push(search);
    publishedNote = `${NO_RECORD_IS_NOT_NO_DISRUPTION} That describes this dataset, not ${name}.`;
  } else {
    const eps = sys.event_summary.episodes;
    published = `${n} reviewed energy-disruption ${plural(n, "record is", "records are")} published for ${name}, in ${eps} ${plural(eps, "episode", "episodes")}.`;
    publishedNote = restricted
      ? "They are what was reported and found, not everything that happened. Attack records are published under attack-campaign safeguards."
      : "They are what was reported and found, not everything that happened.";
  }

  const known: OverviewLink[] = [
    { tab: "impacts", label: TAB_LABEL.impacts, line: impactLine(sys.name, impacts) },
  ];
  if (regional) {
    known.push({
      tab: "regional", label: TAB_LABEL.regional,
      line: `Dated, sourced statements about the region in aggregate. They say nothing about any facility in ${name}.`,
    });
  }
  known.push({
    tab: "context", label: TAB_LABEL.context,
    line: "The size of the national energy system, from one source and one year. Context, never disruption.",
  });
  known.push({
    tab: "research", label: TAB_LABEL.research,
    line: "What was searched, in which languages, and what could not be read.",
  });

  const withheld: string[] = [];
  if (restricted) {
    withheld.push("Whether an attacked facility has been repaired, restarted or is operating: not published while attacks on energy facilities are being reported, because a current list of what works would describe the damage.");
    if (attacksWhole) withheld.push("Where inside the country an attack happened, and at which facility or operator: an attack record is kept for the country as a whole.");
    // Identical whatever the research log holds: beside a short list of published attack records, a
    // count of what is in review, or even the fact that something is, hints at the campaign's scale.
    withheld.push("Records still in review: never shown, and under these safeguards this page does not say how many there are, or whether there are any.");
  } else {
    withheld.push("Records still in review: not shown until they pass. The Research coverage tab gives the counts.");
  }
  withheld.push("Coordinates and anything finer than a first-level region: never collected or published, for any record.");

  return { published, reasons, publishedNote, known, withheld };
}

/** Every sentence of the overview, in reading order: what a test, or an export, reads. */
export function overviewText(o: Overview): string[] {
  return [o.published, ...o.reasons, o.publishedNote, ...o.known.map((k) => `${k.label}: ${k.line}`), ...o.withheld];
}
