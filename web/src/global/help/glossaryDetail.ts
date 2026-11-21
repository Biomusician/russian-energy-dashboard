/** The glossary's longer half (iteration 23): each term's detail, its served definition, and "How
 *  this works". Loaded with the Help page only: the home page needs a term's name and plain
 *  definition (glossary.ts) for search and Start here, never this. Keyed by glossary id; a test fails
 *  if an id is in one file and not the other. Reader copy, under the same rules as glossary.ts.
 */
import { PLACEMENTS, PLACEMENT_LABEL, PLACEMENT_MEANING } from "../placement";
import { stateList } from "./glossary";

/** The served Evidence Confidence method, as far as the glossary reads it: the statement, the
 *  category and attribution-confidence meanings, and the definitions of the served vocabularies. */
export interface ServedMethod {
  statement: string;
  version?: string;
  status?: string | null;
  categories: { id: string; label: string; meaning: string }[];
  attribution: { labels: Record<string, string>; meanings: Record<string, string> };
  labels: Record<string, { id: string | number; label: string; definition?: string }[]>;
}

export interface GlossaryDetail {
  detail: string;
  /** The served definition, where the build publishes one. Shown as the detail once the method
   *  has loaded, so the glossary and the record cards cannot drift apart. */
  served?: (m: ServedMethod) => string | null;
}

function definition(m: ServedMethod, vocab: string, id: string): string | null {
  return m.labels?.[vocab]?.find((e) => String(e.id) === id)?.definition ?? null;
}

/** "Label: meaning" for each key, in the order given, skipping what the method does not carry. */
function meanings(labels: Record<string, string>, texts: Record<string, string>, keys: string[]): string | null {
  const own = (o: object, k: string) => Object.prototype.hasOwnProperty.call(o, k);
  const out = keys.filter((k) => own(labels ?? {}, k) && own(texts ?? {}, k)).map((k) => `${labels[k]}: ${texts[k]}`);
  return out.length > 0 ? out.join(" ") : null;
}

export const GLOSSARY_DETAIL: Record<string, GlossaryDetail> = {
  "ai-involvement": {
    detail: "Two different things are kept apart. AI-assisted means an attacker used AI tools; it does not mean AI caused the outage. AI in operations means an AI system used to run the service made the wrong decision, or an AI service the operation relied on failed. Modern, automated or sophisticated is not AI, and a defender's use of AI is not involvement: a source has to say so about this incident.",
    served: (m) => [definition(m, "ai_relations", "ai_assisted"), definition(m, "ai_relations", "ai_operational_cause"), definition(m, "ai_statuses", "NONE_REPORTED")]
      .filter(Boolean).join(" ") || null,
  },
  "as-published": {
    detail: "They differ whenever a report about an old event was found later, or the method changed. A reconstruction places a late-found event on its own date; the published history shows when the site first displayed it. Published history starts at the earliest build that can be shown to have been served, and is never filled in for earlier days.",
  },
  "assessed": {
    detail: "The record says who made the assessment and on what date. An assessment made months after the event is shown with its own date, never as something known at the time. Agreement among technical or press attributions, however many, is Assessed, not Attributed.",
    served: (m) => definition(m, "attribution_statuses", "ASSESSED"),
  },
  "attempt": {
    detail: "Only attempts documented in an official or operator statement qualify. They are kept apart so that the timeline and every count describe real interruptions of a service, not intrusions that were stopped.",
    served: (m) => definition(m, "record_kinds", "attempt_no_service_impact"),
  },
  "attributed": {
    detail: "Records always read “X attributed this to Y”, never “Y did it”. An attribution needs at least one official source, and its date is shown because attributions often come long after the event.",
    served: (m) => definition(m, "attribution_statuses", "ATTRIBUTED"),
  },
  "attribution": {
    detail: "An attribution is one of: not applicable (not a malicious act), not established (no credible public attribution, which is not a low confidence), claimed, suspected, assessed, attributed or disputed. When sources disagree, every competing attribution is listed and the site does not choose.",
    served: (m) => ["UNKNOWN", "CLAIMED", "SUSPECTED", "ASSESSED", "ATTRIBUTED", "DISPUTED"]
      .map((k) => { const d = definition(m, "attribution_statuses", k); const l = m.labels?.attribution_statuses?.find((e) => e.id === k)?.label; return d && l ? `${l}: ${d}` : null; })
      .filter(Boolean).join(" ") || null,
  },
  "attribution-confidence": {
    detail: "High needs a formal government or law-enforcement attribution plus a second attribution of a different kind from a separate organisation. An actor's own claim is never more than claim only. Suspected is at most low and assessed at most moderate. An unknown attribution has no confidence level: it is not established, which is different from low.",
    served: (m) => meanings(m.attribution?.labels, m.attribution?.meanings, ["HIGH", "MODERATE", "LOW", "CLAIM_ONLY", "DISPUTED", "NOT_ESTABLISHED"]),
  },
  "civilian-service-impact": {
    detail: "Figures keep the source's own unit. People are not customers, customers are not households, and households are not subscribers, so nothing is converted or added up. Where no source gives a figure the record says so; it is never shown as zero.",
  },
  "claimed": {
    detail: "Groups claim attacks they did not carry out and exaggerate ones they did. However many outlets repeat a claim, it stays a claim. A record resting only on an actor's own claim has attribution confidence claim only, and its evidence confidence can be no higher than preliminary.",
    served: (m) => definition(m, "attribution_statuses", "CLAIMED"),
  },
  "cyber-disruption": {
    detail: "A failure that was digital but not malicious, such as a faulty software update that stopped operations, is an IT failure: it is filed as a technical failure, has its own filter, and is never counted as a cyberattack. No record says how access was gained or carries any other exploit detail.",
    served: (m) => definition(m, "cause_families", "cyber"),
  },
  "disputed": {
    detail: "A record disputed on whether it happened or on its effect is labelled disputed whatever its evidence points would otherwise be. A disputed attribution lists every competing attribution with who made it.",
    served: (m) => [m.categories?.find((c) => c.id === "DISPUTED")?.meaning, definition(m, "attribution_statuses", "DISPUTED")].filter(Boolean).join(" ") || null,
  },
  "episode": {
    detail: "Records join an episode only when a cited source names the shared hazard or event, or says one event continued another. Counting episodes instead of records stops a single storm that touched many regions from looking like many separate disruptions.",
  },
  "esdi": {
    detail: "It weighs each facility's published capacity by evidence strength, cause, reported damage severity and time elapsed, sector by sector, then combines sectors with fixed weights. It measures exposure, not output lost and not current damage. A sector with no capacity base is left out and the remaining weights are rescaled; it is not counted as zero. It depends heavily on assumed recovery times, and its transmission part is a count of disrupted equipment, not a share of the grid.",
  },
  "evidence-confidence": {
    detail: "It counts independent originating statements, never links, and weighs who is speaking (an operator or official body counts for more than a repost), how specific the reported effect is, whether a source was opened during research or review, and whether it was dated at the time. The category is the finding; the points behind it are not a percentage. Each record shows its reasons under “Why?”.",
    served: (m) => [m.status ? `Method status: ${m.status}.` : null, m.statement, ...(m.categories ?? []).map((c) => `${c.label}: ${c.meaning}`)].filter(Boolean).join(" "),
  },
  "exposure": {
    detail: "A refinery reported hit counts with its published capacity, fading with time, whether or not the report said how much production stopped. Where a source does quantify the effect, that figure is shown on the record but does not drive the index.",
  },
  "gulf-littoral": {
    detail: "The view shows national figures, memberships and a date-ordered list of records, with no score, no rank, no count per country and no trend. Its regional context is dated, sourced statements in aggregate, never a current status.",
  },
  "impact-atlas": {
    detail: "It is an expanding collection, not a census: disclosure laws differ, operators may not disclose and conflicts distort reporting. Its counts are published records, never rates, and are never compared or ranked between countries. A country that appears only there is not a monitored system.",
  },
  "impact-record-country": {
    detail: "It has no index, no claim about how far its research has got, and no implied complete set of records: the atlas lists what was reviewed and published, not everything that happened there. In the atlas's country list the monitored systems carry a “monitored system” tag; a country without the tag is an impact-record country.",
  },
  "monitored-system": {
    detail: "Only Russia, Belarus & Crimea has an index. The country systems show reviewed records, what the evidence supports sector by sector, research coverage and context, with no score. A monitored system's search is still partial.",
  },
  "national-context": {
    detail: "Every country on the world map has context figures. Only monitored systems have a disruption record. A country shown with context only was not searched for disruptions, so nothing can be said about what did or did not happen there.",
  },
  "no-index": {
    detail: "The index's weights, recovery assumptions and transmission measure were built for one strike campaign against one energy system and do not transfer to other countries' reporting. Countries show reviewed records, what the evidence supports sector by sector, and context instead.",
  },
  "originating-statement": {
    detail: "Corroboration is counted in originating statements, not links. An origin is the wire service a citation names, otherwise the website it appears on, so a record with many links can still rest on a single statement. Where nobody reviewed which sources relay which, the count is of distinct publishers, which is an upper bound.",
  },
  "placement": {
    detail: PLACEMENTS.map((k) => `${PLACEMENT_LABEL[k]}: ${PLACEMENT_MEANING[k]}`).join(" ")
      + " A record is never placed more precisely than one first-level region, and never at a facility's coordinates.",
  },
  "publication-safeguard": {
    detail: "The record still shows that something was reported, its date, its broad class and its cause. Lists that put records from several countries side by side show such a record for the country as a whole, with a list entry number instead of its own name. When evidence held this way may be published is not yet decided for the country systems.",
  },
  "recovery-evidence": {
    detail: "The kind travels with every figure and the three are never merged. Modelled recovery is used only in the indexed area; the country systems show reported restorations and labelled estimates only. “No restoration report by the cut-off” is not “known to be still offline”, and a reported restart is not full recovery.",
  },
  "reported-effect": {
    detail: "Each record says how specific the report is: quantified (a source gives a figure), described (a concrete effect without a figure) or general terms only. A reported effect is not capacity lost and is never turned into a score.",
    served: (m) => ["quantified", "described", "vague"]
      .map((k) => { const e = m.labels?.effect_specificity?.find((x) => x.id === k); return e?.definition ? `${e.label}: ${e.definition}` : null; })
      .filter(Boolean).join(" ") || null,
  },
  "reporting-environment": {
    detail: "It shapes what can be found at all, which is one reason counts are never compared between countries. Each country page names its environment, and its counts appear beside it.",
  },
  "research-coverage": {
    detail: `Research is organised in source groups (for example one regulator's notices). Each group is in one state: ${stateList()}. “Planned searches run” means every planned search was run, not that every event was found. The states differ from country to country and are never added up into one “complete” figure.`,
  },
  "research-preview": {
    detail: "A missing record in any country is not evidence that nothing happened. Each country page lists the state of every source group and through which date it was searched.",
  },
  "sector-state": {
    detail: "These are kept apart on purpose. Unknown means the evidence does not settle it; not applicable means the sector does not exist there; not yet researched means nobody has looked. None of them is a zero, and no country's sector carries a score.",
  },
  "source-freshness": {
    detail: "A fresh build can rest on old sources, and an old build on fresh ones. A rebuild is not a re-read of the sources.",
  },
  "source-health": {
    detail: "Sources checked on time say nothing about how complete the search is. A site that refuses the automated checker is not a dead page, and a deleted post does not erase a claim that other sources corroborate.",
  },
  "transmission-burden": {
    detail: "No open source gives a transmission capacity base, so the count is measured against a fixed saturation point: a set number of weighted concurrent disruptions reaches the top of the scale. The point is a documented judgement, and the Help section on the index shows its current value. The network map is context; it is not the base of this measure.",
  },
};

/** The detail to show for a term: the served definition when there is one, else its own. */
export function glossaryDetail(id: string, served: ServedMethod | null): string {
  const g = GLOSSARY_DETAIL[id];
  if (!g) return "";
  if (!served || !g.served) return g.detail;
  try { return g.served(served) || g.detail; } catch { return g.detail; }
}

/** "How this works": the method in six plain steps. */
export const HOW_IT_WORKS: { step: string; text: string }[] = [
  { step: "Open sources only", text: "Everything comes from public reporting: regulators, ministries, operators, news agencies and newspapers. Nothing classified, nothing private." },
  { step: "A planned search per country", text: `Each country has a list of source groups to search. Each group's state is shown in words: ${stateList()}. No country's search is complete.` },
  { step: "Reviewed records", text: "A reported disruption becomes a record only if it meets a stated rule for inclusion and passes independent review. The reviewers are separate sessions of the same AI model that did the research: independent in what they were shown, not in model. Records are placed by first-level region at most, never at a facility's coordinates." },
  { step: "One index, one area", text: "Only Russia, Belarus & Crimea has an index. It measures exposure (capacity at recently disrupted sites), not output lost, and leans heavily on assumed recovery times. Countries get no score, and no score is not zero." },
  { step: "Safeguards", text: "While attacks on a country's energy facilities are being reported, some detail is not published, such as the later status of an attacked facility. Such records still show their date, class and cause." },
  { step: "Context and counts kept apart", text: "National energy statistics are background and never mixed with disruption records. A count is the number of records published here: never a rate, and never compared between countries." },
];
