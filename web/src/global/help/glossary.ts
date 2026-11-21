/** The one reader glossary (iteration 23; it was global/glossary.ts): each term's id, name, search
 *  aliases and plain definition, and the Start-here points. The Help page, the home page's Start
 *  here and the search all read it, so a definition exists once. Each term's longer detail, its
 *  served definition and "How this works" are in glossaryDetail.ts, which loads with Help only.
 *
 *  Reader copy, so it speaks to the reader: no file names, internal ids, build vocabulary, first
 *  person, or live figures (a count, a date, a version is a derived value on the Help page, never
 *  typed here). Each entry keeps the distinctions the site exists to keep (exposure is not loss, no
 *  index is not zero, unknown is not none). Alphabetical by term; nothing here is ranked.
 *
 *  This file is in the home page's bundle (search and Start here need it), so it holds only what
 *  they show; the rest is lazy (glossaryDetail.ts, content.ts), and a test holds the two halves
 *  together. The words for research states and for placement come from the one module each that
 *  every other page uses (laneCoverage.ts, placement.ts).
 */
import { COVERAGE_STATES, LANE_STATE_LABEL } from "../laneCoverage";
import { PLACEMENT_LABEL, PLACEMENTS } from "../placement";
import type { HelpSectionId } from "./anchors";

/** "every published item read; searched through …; … or not started" from the shared labels. */
export function stateList(): string {
  const words = COVERAGE_STATES.filter((k) => k !== "legacy").map((k) => LANE_STATE_LABEL[k].toLowerCase());
  return `${words.slice(0, -1).join("; ")}; or ${words[words.length - 1]}`;
}

export interface GlossaryEntry {
  id: string;
  term: string;
  /** Other words a reader might search for. Matching only. */
  aliases: string[];
  /** The plain definition: what search shows and what Help leads with. */
  plain: string;
  /** The Help section that explains the term at length. */
  see: HelpSectionId;
}

export const GLOSSARY: GlossaryEntry[] = [
  {
    id: "ai-involvement",
    term: "AI involvement",
    aliases: ["ai", "artificial intelligence", "ai-assisted", "ai involved", "ai-caused", "machine learning"],
    plain: "Whether a cited source ties artificial intelligence to this particular incident, and how firmly. “None reported”, the default, means no cited source meets that standard; it does not mean AI was absent.",
    see: "ai-involvement",
  },
  {
    id: "as-published",
    term: "As published vs current-evidence reconstruction",
    aliases: ["as published", "reconstruction", "history", "past date", "timeline"],
    plain: "Two different answers to “what did it look like on that day?”. As published is what the site actually showed on that day. A current-evidence reconstruction is today's evidence and method applied to that past date.",
    see: "history",
  },
  {
    id: "assessed",
    term: "Assessed",
    aliases: ["assessment", "assessed attribution"],
    plain: "A government body, the affected operator or a technical investigator has assessed who was responsible, or whether AI was involved. Firmer than suspected; less than a formal attribution.",
    see: "attribution",
  },
  {
    id: "attempt",
    term: "Attempt (no reported service disruption)",
    aliases: ["attempt", "attempted attack", "foiled", "no service impact"],
    plain: "A clearly documented attempt on an essential service where no effect on the service was reported. Attempts are listed in their own section and are never counted with disruptions.",
    see: "impact-records",
  },
  {
    id: "attributed",
    term: "Attributed",
    aliases: ["formal attribution", "attributed attack"],
    plain: "A government or law-enforcement body has formally attributed the incident to an actor: at least one source supporting the attribution has a government or law-enforcement basis. Agreement among other sources, however many, is not enough on its own. The site reports who attributes; it asserts nothing itself.",
    see: "attribution",
  },
  {
    id: "attribution",
    term: "Attribution",
    aliases: ["who did it", "responsible", "actor", "perpetrator", "blame", "unknown attribution", "not established"],
    plain: "Who is publicly said to be responsible for a malicious act, by whom, and when. It is separate from whether the disruption happened and from what caused it.",
    see: "attribution",
  },
  {
    id: "attribution-confidence",
    term: "Attribution confidence",
    aliases: ["attribution strength", "claim only", "how sure"],
    plain: "How strong the public evidence is about who was responsible: high, moderate, low, claim only or disputed. It is worked out from who made each attribution, never typed by hand.",
    see: "attribution",
  },
  {
    id: "civilian-service-impact",
    term: "Civilian-service impact",
    aliases: ["civilian impact", "service impact", "customers affected", "people affected", "households", "subscribers"],
    plain: "Which everyday service was interrupted (electricity, water, telecommunications, healthcare, transport and others), how widely, and for how long, as the sources report it.",
    see: "impact-records",
  },
  {
    id: "claimed",
    term: "Claimed",
    aliases: ["claim", "claim of responsibility", "self-claim", "took credit"],
    plain: "An actor said it was responsible, or someone claimed AI was involved, without independent support. A claim is recorded as a claim; it is not corroboration.",
    see: "attribution",
  },
  {
    id: "cyber-disruption",
    term: "Cyber disruption",
    aliases: ["cyber", "cyberattack", "cyber attack", "hack", "ransomware", "it failure", "it outage", "mechanism"],
    plain: "A disruption whose reported cause is a malicious act through computer systems or networks. A record may name the broad kind (ransomware, denial of service, destructive malware) when it was publicly reported.",
    see: "cyber",
  },
  {
    id: "disputed",
    term: "Disputed",
    aliases: ["dispute", "contested", "competing attributions", "disagree"],
    plain: "Credible sources materially disagree: about whether the disruption happened, what its effect was, or who was responsible. The site lists what each says and does not choose between them.",
    see: "evidence-confidence",
  },
  {
    id: "episode",
    term: "Episode",
    aliases: ["episodes", "named hazard", "storm", "wave"],
    plain: "A group of records that share one cause the sources name: one storm, one heatwave, one coordinated wave. A record without such a link is its own episode.",
    see: "impact-records",
  },
  {
    id: "esdi",
    term: "ESDI (Energy System Disruption Exposure Index)",
    aliases: ["index", "exposure index", "monitored-area esdi", "score", "headline"],
    plain: "The one index on this site, published only for Russia, Belarus & Crimea. On a 0 to 100 scale it shows how much tracked energy capacity sits at recently disrupted sites, weighted by evidence, cause and time elapsed.",
    see: "esdi",
  },
  {
    id: "evidence-confidence",
    term: "Evidence confidence",
    aliases: ["confidence", "evidence quality", "high", "moderate", "limited", "preliminary", "ordinal score", "how reliable"],
    plain: "How strongly the sources a record cites support that the disruption happened and that its reported effect is right: high, moderate, limited, preliminary or disputed, or “Not assessed” with the reason. It is not a probability, not severity, not importance and not research completeness, and it does not cover the cause or who was responsible.",
    see: "evidence-confidence",
  },
  {
    id: "exposure",
    term: "Exposure",
    aliases: ["capacity at disrupted sites", "capacity loss", "loss"],
    plain: "How much capacity sits at sites that were reported disrupted. It is not how much output was lost: open reporting rarely says that, so the site does not estimate it.",
    see: "esdi",
  },
  {
    id: "gulf-littoral",
    term: "Gulf littoral",
    aliases: ["littoral"],
    plain: "The eight states on the Gulf, shown together as one regional view. A geographic group, not an organisation: it is not the GCC and not OPEC, which appear only as membership facts.",
    see: "gulf-context",
  },
  {
    id: "impact-atlas",
    term: "Impact atlas",
    aliases: ["impacts", "impact records", "atlas", "cross-country", "global impact"],
    plain: "A separate collection of reviewed, publicly reported disruptions to energy systems and essential civilian services, in any country. It has no score and feeds no index.",
    see: "impact-records",
  },
  {
    id: "impact-record-country",
    term: "Impact-record country",
    aliases: ["impact record country", "not monitored", "impact layer only", "atlas only"],
    plain: "A country that appears only in the impact atlas, because a reviewed impact record names it. It is not one of the monitored systems.",
    see: "product-types",
  },
  {
    id: "monitored-system",
    term: "Monitored system",
    aliases: ["monitored system", "monitored", "country system", "system"],
    plain: "A place searched systematically, with a page of its own: Russia, Belarus & Crimea, or one of the country systems. A thick outline marks it on the world map.",
    see: "product-types",
  },
  {
    id: "national-context",
    term: "National energy context",
    aliases: ["context", "context only", "world map", "energy production", "national figures"],
    plain: "National energy statistics (production, consumption, electricity mix) for a country, from one source and one year. It describes the energy system; it says nothing about disruption or about importance.",
    see: "product-types",
  },
  {
    id: "no-index",
    term: "No index",
    aliases: ["no score", "null", "not scored", "zero"],
    plain: "The country systems have no index and no score. “No index” means no figure was computed; it never means zero, and it never means nothing happened.",
    see: "why-no-country-score",
  },
  {
    id: "originating-statement",
    term: "Originating statement vs citation",
    aliases: ["citation", "origin", "source", "wire service", "corroboration", "originating statement", "independent sources", "republication"],
    plain: "A citation is a link to a report. An originating statement is where the information first came from. Ten articles repeating one news-agency report are ten citations but one originating statement.",
    see: "evidence-confidence",
  },
  {
    id: "placement",
    term: "Placement",
    aliases: ["national", "several regions", "multiple regions", "country level", "one region", "first-level region", "where", "placed"],
    plain: `How precisely a record is placed. Every page uses the same four placements: ${PLACEMENTS.map((k) => PLACEMENT_LABEL[k]).join("; ")}.`,
    see: "withheld",
  },
  {
    id: "publication-safeguard",
    term: "Publication safeguards",
    aliases: ["withheld", "campaign", "row key", "list entry", "safeguard", "attack campaign", "under safeguards", "campaign policy"],
    plain: `While attacks on a country's energy facilities are being reported, some detail is not published: the later status of an attacked facility and, in most such countries, where in the country the attack happened. Such records appear as “${PLACEMENT_LABEL.national_safeguarded}”.`,
    see: "withheld",
  },
  {
    id: "recovery-evidence",
    term: "Recovery evidence: observed, estimated, modelled",
    aliases: ["recovery", "restoration", "repair", "restart", "modelled", "observed", "estimated"],
    plain: "How a recovery figure is known. Observed: a source reported the restoration. Estimated: a source gave an expected repair time. Modelled: no source said, and an assumption for that type of facility is used.",
    see: "esdi",
  },
  {
    id: "reported-effect",
    term: "Reported effect",
    aliases: ["effect", "quantified", "described", "what happened", "consequence"],
    plain: "What the cited sources say the disruption did, in neutral words. It is what was reported at the time, not a measurement and not the state of the service today.",
    see: "evidence-confidence",
  },
  {
    id: "reporting-environment",
    term: "Reporting environment",
    aliases: ["reporting environment", "how a country reports", "disclosure", "regulatory reporting"],
    plain: "How a country's outages come to be reported: by mandatory regulatory filings, by a mix of filings and the press, by company and ministry statements, by the media alone, or under wartime restrictions.",
    see: "source-health",
  },
  {
    id: "research-coverage",
    term: "Research coverage",
    aliases: ["coverage", "research state", "lanes", "source groups", "planned searches"],
    plain: "How much of the planned search for disruptions has been done in a country, shown in words, never as a percentage. It is not source health and not evidence confidence.",
    see: "research-coverage",
  },
  {
    id: "research-preview",
    term: "Research preview",
    aliases: ["preview", "early stage", "incomplete research"],
    plain: "A mark on the country systems whose systematic search is at an earlier stage. It does not mean the other countries are complete: every country's search is partial in some way.",
    see: "research-coverage",
  },
  {
    id: "sector-state",
    term: "Sector state",
    aliases: ["sector", "tracked not scored", "not yet researched", "not applicable", "unknown"],
    plain: "What the evidence supports for one sector of one country: tracked but not scored, unknown, not applicable, or not yet researched.",
    see: "absence",
  },
  {
    id: "source-freshness",
    term: "Source freshness",
    aliases: ["freshness", "how old", "build date", "release date", "retrieved"],
    plain: "How old the information is. The build date says when the page was generated; each source has its own release and retrieval dates; each record has its own event date.",
    see: "source-health",
  },
  {
    id: "source-health",
    term: "Source health",
    aliases: ["source health", "link check", "checked on schedule", "overdue", "dead link"],
    plain: "Whether the registered sources were re-checked on schedule, and whether cited pages still loaded at the last automated check.",
    see: "source-health",
  },
  {
    id: "transmission-burden",
    term: "Transmission burden",
    aliases: ["transmission", "grid", "substations", "power lines"],
    plain: "In Russia, Belarus & Crimea, the transmission part of the index counts recently disrupted substations and lines, weighted by voltage. It is a count of disrupted equipment, not a share of the grid out of service.",
    see: "esdi",
  },
];

/** "Start here": six things a first-time reader needs. The home page's panel and the Help page's
 *  first section show this one list. */
export const START_HERE: { title: string; text: string }[] = [
  { title: "One system has an index.", text: "Russia, Belarus & Crimea is the only system with a number, the exposure index (ESDI). It measures exposure, not output lost." },
  { title: "The other systems are countries with evidence and context, and no score.", text: "Each shows reviewed reports of major disruptions and sourced background." },
  { title: "No index is not zero.", text: "A country without an index has no figure computed; it is not rated as calm or safe." },
  { title: "Research coverage differs by country.", text: "Some are research previews. A missing record is not evidence that nothing happened." },
  { title: "National energy context is not disruption.", text: "Production and consumption figures describe an energy system; they say nothing about damage or importance." },
  { title: "Maps mean different things by view.", text: "The world map is coloured by a national energy figure; a country map is coloured by where records were placed; the Russia, Belarus & Crimea map shows exposure. Each map's legend says which." },
];

export function glossaryEntry(id: string): GlossaryEntry | null {
  return GLOSSARY.find((g) => g.id === id) ?? null;
}
