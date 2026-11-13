/** The in-product glossary: plain language first, the technical detail one click further.
 *
 *  Reader copy, so it speaks to the reader: no file names, internal ids or build vocabulary. Each
 *  entry keeps the distinctions the site exists to keep (exposure is not loss, no index is not
 *  zero, unknown is not none). Order is alphabetical by term; nothing here is ranked.
 *
 *  The words for research states and for placement are not typed here: they come from the one
 *  module each (laneCoverage.ts, placement.ts) that every other page uses too.
 */
import { COVERAGE_STATES, LANE_STATE_LABEL } from "./laneCoverage";
import { PLACEMENTS, PLACEMENT_LABEL, PLACEMENT_MEANING } from "./placement";

/** "every published item read; searched through …; … or not started" from the shared labels. */
function stateList(): string {
  const words = COVERAGE_STATES.filter((k) => k !== "legacy").map((k) => LANE_STATE_LABEL[k].toLowerCase());
  return `${words.slice(0, -1).join("; ")}; or ${words[words.length - 1]}`;
}

export interface GlossaryEntry {
  id: string;
  term: string;
  /** Other words a reader might search for. Matching only. */
  aliases: string[];
  plain: string;
  detail: string;
}

export const GLOSSARY: GlossaryEntry[] = [
  {
    id: "as-published",
    term: "As published vs current-evidence reconstruction",
    aliases: ["as published", "reconstruction", "history", "past date", "timeline"],
    plain: "Two different answers to \"what did it look like on that day?\". As published is what the site actually showed on that day. A current-evidence reconstruction is today's evidence and method applied to that past date.",
    detail: "They differ whenever a report about an old event was found later, or the method changed. A reconstruction places a late-found event on its own date; the published history shows when the site first displayed it. Published history is available only from late August 2026 and is never filled in for earlier days.",
  },
  {
    id: "episode",
    term: "Episode",
    aliases: ["episodes", "named hazard", "storm", "wave"],
    plain: "A group of records that share one cause the sources name: one storm, one heatwave, one coordinated wave. Records without such a link are each their own episode.",
    detail: "Records join an episode only when a cited source names the shared hazard or event, or says one event continued another. Counting episodes instead of records stops a single storm that touched many regions from looking like many separate disruptions.",
  },
  {
    id: "esdi",
    term: "ESDI (Energy System Disruption Exposure Index)",
    aliases: ["index", "exposure index", "monitored-area esdi", "score", "headline"],
    plain: "The one index on this site, published only for the Russia, Belarus & Crimea theatre. On a 0 to 100 scale it shows how much of the tracked energy capacity sits at facilities disrupted recently enough to be plausibly still affected.",
    detail: "It weighs each facility's published capacity by evidence strength, cause and time elapsed, sector by sector, then combines sectors with fixed weights. A sector with no capacity base is left out and the weights are rescaled; it is not counted as zero. It is a measure of exposure, not of output lost.",
  },
  {
    id: "exposure",
    term: "Exposure",
    aliases: ["capacity at disrupted sites", "capacity loss", "loss"],
    plain: "How much capacity sits at sites that were reported disrupted. It is not how much output was lost: open reporting rarely says that, so the site does not estimate it.",
    detail: "A refinery reported hit counts with its published capacity, decaying with time, whether or not the report said how much production stopped. Where a source does quantify the effect, that figure is shown on the record but does not drive the index.",
  },
  {
    id: "national-context",
    term: "National energy context",
    aliases: ["context", "context only", "world map", "energy production", "national figures"],
    plain: "National energy statistics (production, consumption, electricity mix) for a country, from one source and one year. It describes the energy system; it says nothing about disruption or about importance.",
    detail: "Every country on the world map has context figures. Only monitored systems have a disruption record. A country shown with context only was not searched for disruptions, so nothing can be said about what did or did not happen there.",
  },
  {
    id: "no-index",
    term: "No index",
    aliases: ["no score", "null", "not scored", "zero"],
    plain: "The country systems have no index and no score. \"No index\" means no figure is computed; it never means zero, and it never means nothing happened.",
    detail: "The index's weights, time decay and transmission measure were built for a strike campaign and do not transfer to other countries' reporting. Countries show reviewed records, sector evidence states and context instead.",
  },
  {
    id: "originating-statement",
    term: "Originating statement vs citation",
    aliases: ["citation", "origin", "source", "wire service", "corroboration"],
    plain: "A citation is a link to a report. An originating statement is where the information first came from. Ten articles repeating one news-agency report are ten citations but one originating statement.",
    detail: "Corroboration is counted in originating statements, not links. An origin is the wire service a citation names, otherwise the website it appears on, so a record with many links can still rest on a single statement, and the country page says so.",
  },
  {
    id: "placement",
    term: "Placement: National, Several regions, One region",
    aliases: ["national", "several regions", "multiple regions", "country level", "one region", "first-level region", "where", "placed"],
    plain: "How precisely a record is placed. Every page uses the same four words.",
    detail: PLACEMENTS.map((k) => `${PLACEMENT_LABEL[k]}: ${PLACEMENT_MEANING[k]}`).join(" ")
      + " A record is never placed more precisely than one first-level region, and never at a facility's coordinates.",
  },
  {
    id: "publication-safeguard",
    term: "Publication safeguard",
    aliases: ["withheld", "campaign", "row key", "list entry", "safeguard", "attack campaign", "under safeguards"],
    plain: `While attacks on a country's energy facilities are being reported, some detail is not published: the facility's current status, and in some countries where the attack happened inside the country. Such records appear as "${PLACEMENT_LABEL.national_safeguarded}".`,
    detail: "The record still shows that something was reported, its date, its broad class and its cause. Lists that put records from several countries side by side show such a record for the country as a whole, with a list entry number instead of its own name. Historical evidence may be published once the campaign is over.",
  },
  {
    id: "research-coverage",
    term: "Research coverage vs source health",
    aliases: ["coverage", "source health", "research state", "lanes", "source groups"],
    plain: "Research coverage says how much of the planned search for events has been done. Source health says whether the registered sources were checked on schedule. One does not imply the other.",
    detail: `Research is organised in source groups (for example one regulator's notices). Each group is in one state: ${stateList()}. "Planned searches run" means every planned search was run, not that every event was found. These are shown as words, never as a percentage or a "complete" count, and differ from country to country.`,
  },
  {
    id: "research-preview",
    term: "Research preview",
    aliases: ["preview", "early stage", "incomplete research"],
    plain: "A country whose systematic search is still incomplete. A missing record there is not evidence that nothing happened.",
    detail: "Each country page lists the state of every source group (for example planned searches run, partly searched, source unavailable or not started) and through which date.",
  },
  {
    id: "sector-state",
    term: "Sector state",
    aliases: ["sector", "tracked not scored", "not yet researched", "not applicable", "unknown"],
    plain: "What the evidence supports for one sector of one system: scored, tracked but not scored, unknown, not applicable, or not yet researched.",
    detail: "These are kept apart on purpose. Unknown means the evidence does not settle it; not applicable means the sector does not exist there; not yet researched means nobody has looked. None of them is a zero.",
  },
  {
    id: "transmission-burden",
    term: "Transmission burden",
    aliases: ["transmission", "grid", "substations", "power lines"],
    plain: "In Russia, Belarus & Crimea, the transmission part of the index counts recently disrupted substations and lines, weighted by voltage. It is a count of disrupted equipment, not a share of the grid out of service.",
    detail: "No open source gives a transmission capacity base, so the count is scored against a fixed saturation point (eight weighted concurrent disruptions reach the top of the scale). The network map is context; it is not the base of this measure.",
  },
];

/** "How this works": the method in six plain steps, shown at the top of the glossary. */
export const HOW_IT_WORKS: { step: string; text: string }[] = [
  { step: "Open sources only", text: "Everything comes from public reporting: regulators, ministries, operators, news agencies and newspapers. Nothing classified, nothing private." },
  { step: "A planned search per country", text: "Each country has a list of source groups to search. Each group's state is shown in words, such as planned searches run (not exhaustive), partly searched, source unavailable or not started." },
  { step: "Reviewed records", text: "A reported disruption becomes a record only if it passes a stated threshold and independent reviewers agree. Records are placed by first-level region at most, never at a facility's coordinates." },
  { step: "One index, one theatre", text: "Only the Russia, Belarus & Crimea theatre has an index. It measures exposure (capacity at recently disrupted sites), not output lost. Countries get no score." },
  { step: "Safeguards", text: "While attacks on a country's energy facilities are being reported, some detail is not published, such as a facility's current status. Such records still show their date, class and cause." },
  { step: "Context kept apart", text: "National energy statistics are shown for background and never mixed with disruption records. Counts are never compared between countries." },
];

export function glossaryEntry(id: string): GlossaryEntry | null {
  return GLOSSARY.find((g) => g.id === id) ?? null;
}
