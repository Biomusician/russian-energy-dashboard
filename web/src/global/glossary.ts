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

/** The served Evidence Confidence method, as far as the glossary reads it: the statement, the
 *  category and attribution-confidence meanings, and the definitions of the served vocabularies. */
export interface ServedMethod {
  statement: string;
  /** Present while the method is provisional. */
  status?: string | null;
  categories: { id: string; label: string; meaning: string }[];
  attribution: { labels: Record<string, string>; meanings: Record<string, string> };
  labels: Record<string, { id: string | number; label: string; definition?: string }[]>;
}

export interface GlossaryEntry {
  id: string;
  term: string;
  /** Other words a reader might search for. Matching only. */
  aliases: string[];
  plain: string;
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

/** The detail to show for an entry: the served definition when there is one, else the entry's own. */
export function glossaryDetail(g: GlossaryEntry, served: ServedMethod | null): string {
  if (!served || !g.served) return g.detail;
  try { return g.served(served) || g.detail; } catch { return g.detail; }
}

export const GLOSSARY: GlossaryEntry[] = [
  {
    id: "ai-involvement",
    term: "AI involvement",
    aliases: ["ai", "artificial intelligence", "ai-assisted", "ai involved", "ai-caused", "machine learning"],
    plain: "Whether a cited source ties artificial intelligence to this particular incident, and how firmly. Most records carry no AI line at all, because no source reports any.",
    detail: "Two different things are kept apart. AI-assisted means an attacker used AI tooling; it does not mean AI caused the outage. AI as operational cause means an AI system used in operations made the wrong decision, or an AI service the operation relied on failed. Modern, automated or sophisticated is not AI: a source has to say so about this incident.",
    served: (m) => [definition(m, "ai_relations", "ai_assisted"), definition(m, "ai_relations", "ai_operational_cause"), definition(m, "ai_statuses", "NONE_REPORTED")]
      .filter(Boolean).join(" ") || null,
  },
  {
    id: "as-published",
    term: "As published vs current-evidence reconstruction",
    aliases: ["as published", "reconstruction", "history", "past date", "timeline"],
    plain: "Two different answers to \"what did it look like on that day?\". As published is what the site actually showed on that day. A current-evidence reconstruction is today's evidence and method applied to that past date.",
    detail: "They differ whenever a report about an old event was found later, or the method changed. A reconstruction places a late-found event on its own date; the published history shows when the site first displayed it. Published history is available only from late August 2026 and is never filled in for earlier days.",
  },
  {
    id: "assessed",
    term: "Assessed",
    aliases: ["assessment", "assessed attribution"],
    plain: "A competent body, such as a government agency, the affected operator or a technical investigator, has assessed who was responsible or whether AI was involved. Firmer than suspected; less than a formal attribution.",
    detail: "The record says who made the assessment and on what date. An assessment made months after the event is shown with its own date, never as something known at the time.",
    served: (m) => definition(m, "attribution_statuses", "ASSESSED"),
  },
  {
    id: "attempt",
    term: "Attempt (no reported service disruption)",
    aliases: ["attempt", "attempted attack", "foiled", "no service impact"],
    plain: "A clearly documented attempt on an essential service where no effect on the service was reported. Attempts are listed in their own section and are never counted with disruptions.",
    detail: "Only attempts documented in an official or operator statement qualify. They are kept apart so that the timeline and every count describe real interruptions of a service, not intrusions that were stopped.",
    served: (m) => definition(m, "record_kinds", "attempt_no_service_impact"),
  },
  {
    id: "attributed",
    term: "Attributed",
    aliases: ["formal attribution", "attributed attack"],
    plain: "A government or law-enforcement body has formally attributed the incident to an actor, or several independent credible sources attribute it to the same one. The site reports who attributes; it asserts nothing itself.",
    detail: "Records always read \"X attributed this to Y\", never \"Y did it\". An attribution needs at least one official source, and its date is shown because attributions often come long after the event.",
    served: (m) => definition(m, "attribution_statuses", "ATTRIBUTED"),
  },
  {
    id: "attribution",
    term: "Attribution",
    aliases: ["who did it", "responsible", "actor", "perpetrator", "blame", "unknown attribution", "not established"],
    plain: "Who is publicly said to be responsible for a malicious act, and by whom. It is separate from what caused the disruption and from whether it happened.",
    detail: "An attribution is one of: not applicable (not a malicious act), unknown (no credible public attribution, which is not a low confidence), claimed, suspected, assessed, attributed or disputed. When sources disagree, every competing attribution is listed and the site does not choose.",
    served: (m) => ["UNKNOWN", "CLAIMED", "SUSPECTED", "ASSESSED", "ATTRIBUTED", "DISPUTED"]
      .map((k) => { const d = definition(m, "attribution_statuses", k); const l = m.labels?.attribution_statuses?.find((e) => e.id === k)?.label; return d && l ? `${l}: ${d}` : null; })
      .filter(Boolean).join(" ") || null,
  },
  {
    id: "attribution-confidence",
    term: "Attribution confidence",
    aliases: ["attribution strength", "claim only", "how sure"],
    plain: "How strong the public evidence is about who was responsible: high, moderate, low, claim only or disputed. It is worked out from who made the attribution, never typed by hand.",
    detail: "High needs a formal government or law-enforcement attribution plus a second independent one of a different kind. An actor's own claim can never be more than claim only. Unknown attribution has no confidence level: it is not established, which is different from low.",
    served: (m) => meanings(m.attribution?.labels, m.attribution?.meanings, ["HIGH", "MODERATE", "LOW", "CLAIM_ONLY", "DISPUTED", "NOT_ESTABLISHED"]),
  },
  {
    id: "civilian-service-impact",
    term: "Civilian-service impact",
    aliases: ["civilian impact", "service impact", "customers affected", "people affected", "households", "subscribers"],
    plain: "Which everyday service was interrupted (electricity, water, telecommunications, healthcare, transport and others), how widely, and for how long, as the sources report it.",
    detail: "Figures keep the source's own unit. People are not customers, customers are not households, and households are not subscribers, so nothing is converted or added up. Where no source gives a figure the record says so; it is never shown as zero.",
  },
  {
    id: "claimed",
    term: "Claimed",
    aliases: ["claim", "claim of responsibility", "self-claim", "took credit"],
    plain: "An actor said it was responsible, or a source claimed AI was involved, without independent support. A claim is recorded as a claim; it is not corroboration.",
    detail: "Groups claim attacks they did not carry out and exaggerate ones they did. A record resting only on an actor's own claim is marked claim only, and its evidence confidence can be no higher than preliminary.",
    served: (m) => definition(m, "attribution_statuses", "CLAIMED"),
  },
  {
    id: "cyber-disruption",
    term: "Cyber disruption",
    aliases: ["cyber", "cyberattack", "cyber attack", "hack", "ransomware", "it failure", "it outage", "mechanism"],
    plain: "A disruption whose reported cause is a malicious act through computer systems or networks. A record may name the broad kind (ransomware, denial of service, destructive malware) when it was publicly reported.",
    detail: "A failure that was digital but not malicious, such as a faulty software update that stopped operations, is an IT failure: it is filed as a technical failure, has its own filter, and is never counted as a cyberattack. No record says how access was gained.",
    served: (m) => definition(m, "cause_families", "cyber"),
  },
  {
    id: "disputed",
    term: "Disputed",
    aliases: ["dispute", "contested", "competing attributions", "disagree"],
    plain: "Credible sources materially disagree: about whether the disruption happened, what its effect was, or who was responsible. The site lists what each says and does not choose between them.",
    detail: "A disputed record is labelled disputed whatever its evidence score would otherwise be. A disputed attribution lists every competing attribution with who made it.",
    served: (m) => [m.categories?.find((c) => c.id === "DISPUTED")?.meaning, definition(m, "attribution_statuses", "DISPUTED")].filter(Boolean).join(" ") || null,
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
    id: "evidence-confidence",
    term: "Evidence confidence",
    aliases: ["confidence", "evidence quality", "high", "moderate", "limited", "preliminary", "ordinal score", "how reliable"],
    plain: "How strong the public evidence is that a disruption happened and that its reported effect is right: high, moderate, limited, preliminary or disputed. A record whose evidence has not been assessed says \"Not assessed\", with the reason. It is not a probability, not a measure of severity and not a statement about how important the infrastructure is.",
    detail: "It is worked out from who is speaking (an operator or official body counts for more than a repost), how many separate sources stand behind the report, how specific the reported effect is, whether a reviewer read the source, and whether it was reported at the time. The number of links never enters. The category is the finding; the points behind it are not a percentage. Each record shows its reasons under \"Why?\".",
    served: (m) => [m.status ? `Method status: ${m.status}.` : null, m.statement, ...(m.categories ?? []).map((c) => `${c.label}: ${c.meaning}`)].filter(Boolean).join(" "),
  },
  {
    id: "exposure",
    term: "Exposure",
    aliases: ["capacity at disrupted sites", "capacity loss", "loss"],
    plain: "How much capacity sits at sites that were reported disrupted. It is not how much output was lost: open reporting rarely says that, so the site does not estimate it.",
    detail: "A refinery reported hit counts with its published capacity, decaying with time, whether or not the report said how much production stopped. Where a source does quantify the effect, that figure is shown on the record but does not drive the index.",
  },
  {
    id: "impact-atlas",
    term: "Impact atlas",
    aliases: ["impacts", "impact records", "atlas", "cross-country", "global impact"],
    plain: "A separate collection of reviewed, publicly reported disruptions to energy systems and essential civilian services, in any country. It has no score and feeds no index.",
    detail: "It is an expanding corpus, not a census: disclosure laws differ, operators may not disclose and conflicts distort reporting. Its counts are published records, never rates, and are never compared or ranked between countries. A country that appears only there is not a monitored system.",
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
    aliases: ["citation", "origin", "source", "wire service", "corroboration", "originating statement", "independent sources", "republication"],
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
    id: "reported-effect",
    term: "Reported effect",
    aliases: ["effect", "quantified", "described", "what happened", "consequence"],
    plain: "What the cited sources say the disruption did, in neutral words. It is what was reported at the time, not a measurement and not the state of the service today.",
    detail: "Each record says how specific the report is: quantified (a source gives a figure), described (a concrete effect without a figure) or general terms only. A reported effect is not capacity lost and is never turned into a score.",
    served: (m) => ["quantified", "described", "vague"]
      .map((k) => { const e = m.labels?.effect_specificity?.find((x) => x.id === k); return e?.definition ? `${e.label}: ${e.definition}` : null; })
      .filter(Boolean).join(" ") || null,
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
