/** The Help page's prose (iteration 23): the one reader explanation of the whole site.
 *
 *  Content only, no React, and a lazy chunk: only the Help page imports it. Section ids and titles
 *  come from anchors.ts (the list every "Learn more" link is checked against); glossary terms come
 *  from glossary.ts.
 *
 *  NEVER A LIVE VALUE IN PROSE. Anything that moves with a build (the index, a date, a version, a
 *  method status, a count, which sectors are left out, the saturation point, a served definition)
 *  is a `derived` block that the page fills from the served files, so this file cannot go stale.
 *  The Evidence Confidence method's provisional status in particular is shown from the served
 *  status, never typed here. A test forbids digits outside a short allow-list, file names, internal
 *  ids, build vocabulary and first person in every string below.
 *
 *  Each section opens with a one-sentence answer, then detail; technical depth sits in `details`.
 *  Page order is a reading order, never a ranking.
 */
import type { HelpSectionId } from "./anchors";

export type HelpBlock =
  | { kind: "p"; text: string }
  | { kind: "list"; items: string[] }
  | { kind: "details"; summary: string; blocks: HelpBlock[] }
  | { kind: "derived"; key: DerivedKey };

/** Every live value the page fills in. HelpDerived.tsx renders each one from served data. */
export type DerivedKey =
  | "start.points" | "how.steps" | "systems.list" | "country.tabs" | "selection"
  | "esdi.headline" | "esdi.contributions" | "esdi.weights" | "esdi.uncovered" | "esdi.saturation" | "esdi.sensitivity"
  | "impacts.scope" | "impacts.caveats" | "impacts.research"
  | "eci.status" | "eci.statement" | "eci.categories" | "eci.overrides"
  | "attribution.statuses" | "attribution.meanings" | "ai.relations" | "ai.statuses"
  | "coverage.states" | "theatre.coverage"
  | "build.date" | "build.note" | "reporting.environments" | "context.vintage"
  | "whatsnew.comparison" | "whatsnew.categories" | "whatsnew.note"
  | "history.first" | "groups" | "context.statement" | "context.not_built" | "cyber.mechanisms"
  | "absence.words" | "placement.meanings" | "theatre.delay" | "comparability" | "theatre.cannot";

export interface HelpSubsection { id: "how-it-works" | "recovery"; blocks: HelpBlock[] }

export interface HelpSection {
  id: HelpSectionId;
  /** The one-sentence answer, shown first. */
  answer: string;
  blocks: HelpBlock[];
  subsections?: HelpSubsection[];
  seeAlso?: HelpSectionId[];
}

export const HELP_SECTIONS: HelpSection[] = [
  {
    id: "start-here",
    answer: "This site gathers publicly reported disruptions to energy systems and essential civilian services, places each one no more precisely than a first-level region, and says plainly what it does not know.",
    blocks: [
      { kind: "p", text: "Everything comes from public, open sources: regulators, ministries, operators, news agencies and newspapers. Nothing is classified and nothing is private. The site is a research and monitoring instrument. Its main product is an honest account of what is and is not known, with maps attached." },
      { kind: "derived", key: "start.points" },
      { kind: "p", text: "The site holds four different kinds of thing, and they are never mixed:" },
      { kind: "list", items: [
        "One indexed area, Russia, Belarus & Crimea, with one number: an exposure index called the ESDI.",
        "Country systems: countries searched systematically for major disruptions to energy infrastructure. Each shows reviewed records, what the evidence supports sector by sector, and background figures. None has a score.",
        "Impact records: a separate, reviewed collection of disruptions to energy and essential civilian services in any country. Never scored, and never counted into anything else.",
        "National energy context: production, consumption and electricity figures for every country on the world map. Background only; it says nothing about disruption.",
      ] },
      { kind: "derived", key: "systems.list" },
      { kind: "p", text: "Three habits make the rest of the site easy to read. A missing number is not a zero. A missing record is not evidence that nothing happened. A count is the number of records published here: never a rate, a risk level or a measure of resilience, and never compared between countries." },
      { kind: "p", text: "Russia, Belarus & Crimea includes Crimea, which is Ukrainian territory under Russian occupation. Crimea is included in the index as an analytic choice about where disruption is measured, not as a statement about sovereignty." },
    ],
    subsections: [
      { id: "how-it-works", blocks: [{ kind: "derived", key: "how.steps" }] },
    ],
    seeAlso: ["navigating-the-map", "product-types", "do-not-infer"],
  },
  {
    id: "navigating-the-map",
    answer: "Every page can be reached three ways, by the map, by search or by a list, and none of them depends on the others.",
    blocks: [
      { kind: "p", text: "On the world map, selecting a monitored system opens its page. Selecting any other country shows its national energy figures, which are context only: such a country was not searched for disruptions, so its map shading and figures say nothing about what did or did not happen there." },
      { kind: "p", text: "The Gulf littoral is the one regional view. It sets the eight Gulf states side by side as a regional energy picture, with no score, no ranking and no count per country." },
      { kind: "p", text: "Search is a full alternative to the map, not a shortcut. Press “/” anywhere outside a text field to go to search. Search finds the monitored systems under their other names and spellings, regions, the Gulf view and the terms explained on this page. Every page has a breadcrumb back home, and the browser's Back button works throughout." },
      { kind: "p", text: "The maps are never the only way in. Search, the breadcrumb and the lists on each page reach everything a map does, so the site works without a mouse and without seeing a map. Each map also says in words what it shows." },
      { kind: "p", text: "The maps answer different questions, and each legend says which:" },
      { kind: "list", items: [
        "The world map is shaded by a national energy figure. That is context, not disruption. A thick outline marks a monitored system; the shading says nothing about monitoring.",
        "A country map is shaded by where that country's records were placed. An unshaded region has no record placed in it. It is an empty dataset, not a quiet region.",
        "The Russia, Belarus & Crimea map shows exposure: capacity at recently disrupted sites. It is not a map of damage or of current impairment.",
      ] },
      { kind: "p", text: "On a scrolling page the mouse wheel moves the page. To zoom a map, hold Ctrl (⌘ on a Mac) while scrolling, or use the map's own zoom buttons. On a touch screen, move a map with two fingers." },
      { kind: "p", text: "Borders come from a standard public base map. Where territory is disputed, the map follows the line of actual control. That is an analytic choice, not a ruling on sovereignty." },
    ],
    seeAlso: ["what-to-click", "product-types", "absence"],
  },
  {
    id: "what-to-click",
    answer: "Every figure and label can be traced to its reasons: records have “Why?” and a link of their own, country pages have tabs for evidence, research and method, and the indexed area has “Why this number?”.",
    blocks: [
      { kind: "list", items: [
        "“Why?” beside an evidence-confidence category lists the reasons and the parts of the method that produced it.",
        "“Link to this record” gives an address that opens the page at that record. Use it to cite or share a single record.",
        "Country pages are split into tabs, listed below. “Why no score” explains why the country has no index.",
        "On the Russia, Belarus & Crimea page, “Why this number?” opens the Evidence Inspector: every factor behind the index, the data-quality notes, and a list of what the page cannot tell you.",
        "Compare sets a few systems side by side on what can fairly be compared: research coverage, source checks, reporting environment and context. It never compares counts or scores.",
        "“Copy view link” copies an address that reopens exactly the current view, filters included.",
        "“Learn more” beside an explanation opens the matching section of this page.",
      ] },
      { kind: "derived", key: "country.tabs" },
      { kind: "p", text: "Filters change what is shown, not what exists. When filters hide every record, the page says so: that describes the filters, not the country." },
    ],
    seeAlso: ["exports", "evidence-confidence", "esdi"],
  },
  {
    id: "product-types",
    answer: "One indexed area, a set of country systems, a separate collection of impact records, and national context: each answers a different question and follows its own rules.",
    blocks: [
      { kind: "p", text: "The indexed area. Russia, Belarus & Crimea is the only place with an index. Its records cover reported disruption to energy infrastructure since 2022, aggregated to administrative region." },
      { kind: "p", text: "Country systems. Countries searched systematically for major disruptions to energy infrastructure. Each record met a stated rule for inclusion and was reviewed independently before publication, the newer ones blind by three reviewers with separate roles. The reviewers are separate sessions of the same AI model that did the research: independent in what they were shown, not in model. A country page shows its records, what the evidence supports sector by sector, how far its research has got, how that country reports outages, and background figures. There is no score." },
      { kind: "p", text: "Impact records. A separate, reviewed collection of disruptions to energy systems and essential civilian services, such as electricity, water, telecommunications, healthcare and transport, in any country. Each record says which service was affected, what kind of cause was reported, who is publicly said to be responsible and how strong the evidence is. Nothing in it is scored or counted into anything else. A country that appears only there is an impact-record country, not a monitored system." },
      { kind: "p", text: "Context. National energy figures for every country, from one source and one year, and, for the Gulf, dated statements about the region in aggregate. Context never enters a record, a count or an index." },
      { kind: "p", text: "The three record collections are counted separately, under different rules, and are never added together. A total across them would mean nothing." },
      { kind: "details", summary: "Why these systems", blocks: [
        { kind: "derived", key: "selection" },
        { kind: "p", text: "The countries were chosen by a stated rule, not by how much disruption was expected. No order among them is shown, because the order depends on which statistical source is used." },
      ] },
    ],
    seeAlso: ["esdi", "why-no-country-score", "impact-records", "gulf-context"],
  },
  {
    id: "esdi",
    answer: "The ESDI is a 0 to 100 figure for Russia, Belarus & Crimea showing how much tracked energy capacity sits at recently disrupted sites, weighted by evidence, cause and time elapsed; it measures exposure, not output lost and not current damage.",
    blocks: [
      { kind: "derived", key: "esdi.headline" },
      { kind: "p", text: "Read these limits before the number:" },
      { kind: "list", items: [
        "It measures exposure, not loss. Open reporting says that a facility was hit and when, but almost never how much output stopped or for how long. The site does not estimate that figure.",
        "Most of the number can come from one sector. The breakdown below shows how many points each sector adds.",
        "It depends heavily on assumed recovery times. Very few disruptions have a published restoration report, so most contributions fade on a modelled assumption about how long that type of facility takes to recover. A different assumption would give a very different figure.",
        "The transmission part is a count of disrupted substations and lines, weighted by voltage. It is not a share of the grid out of service.",
        "Its evidence weighting is the site's older method, not the Evidence Confidence shown on country and impact records.",
        "Its records come from an older curated workflow, partly parsed from a public table of strikes. They did not pass through the three-role review that country records do, and the country systems' rule for inclusion is not applied to them.",
        "Sectors without a capacity base are left out and the remaining weights rescaled. They are not counted as zero.",
      ] },
      { kind: "derived", key: "esdi.contributions" },
      { kind: "p", text: "How the number is built, step by step:" },
      { kind: "list", items: [
        "Reported disruptions. Each reported disruption at a facility in the area, with its date, its cause and the strength of its evidence.",
        "Sector exposure. For refining, power generation and oil logistics, the facility's published capacity as a share of that sector's tracked capacity. For transmission, a voltage-weighted count of disrupted substations and lines, measured against a fixed saturation point.",
        "Confidence and cause weights. Weaker evidence counts for less. Scheduled maintenance counts for very little; other causes count for more. A facility reported as degraded counts for less than one reported destroyed or shut down.",
        "Recovery decay. Each contribution fades with time. How fast is set by the best recovery evidence available: an observed restoration first, then a credible sourced estimate, then a modelled assumption for that type of facility.",
        "Sector totals. For each facility only its strongest live disruption counts, so repeated strikes cannot make one site more than fully disrupted. Facilities are added up per sector, and a sector cannot exceed the top of its scale.",
        "The headline. Sectors are combined with fixed weights, which are a judgement about importance, not a measurement. Sectors with no capacity base are left out and the weights of the rest rescaled.",
      ] },
      { kind: "p", text: "The area covered is Belarus, the six western federal districts of Russia and the Siberian Federal District. The Russian Far East is not included. Crimea, Ukrainian territory under Russian occupation, is included in the index as an analytic choice, not a statement about sovereignty. It contributes only through the sectors where it has qualifying events and a compatible base, keeps its own styling, and is never labelled a Russian region. The four other Ukrainian regions Russia claims are excluded entirely." },
      { kind: "details", summary: "Technical detail: the index formula", blocks: [
        { kind: "p", text: "Each event, at an evaluation date, carries a weight: its confidence weight × its cause weight × its damage severity × 0.5 raised to the power (days elapsed ÷ half-life)." },
        { kind: "p", text: "Damage severity is always applied and is independent of recovery. Recovery evidence changes only the decay and the tail: once a credible full reconstitution has been observed, the contribution is capped at a small residual of its first value. A contribution below a small cut-off is dropped, so the series carries no long meaningless tail." },
        { kind: "p", text: "The half-life comes from a recovery horizon, the time from disruption to substantial restoration: half-life = horizon ÷ 3.3219, so that only the small residual remains at the horizon. The horizon comes from an observed restoration, else a credible sourced estimate of at least medium confidence, else the modelled horizon for that class of facility. A partial restart is shown but does not speed the decay. A low-confidence estimate is shown but does not drive it." },
        { kind: "p", text: "Each facility counts once: its weight is the largest single live event weight among its events, never their sum." },
        { kind: "p", text: "A capacity sector's exposure is the sum, over its facilities, of the facility's capacity ÷ the sector's tracked base × the facility's weight, capped at the top of the scale. Oil logistics has no published throughput base and uses the refining base as a stated proxy. A facility whose capacity is not recorded adds nothing to its sector; the site lists such facilities rather than guessing a capacity." },
        { kind: "p", text: "Transmission is the sum, over disrupted transmission facilities, of voltage weight × facility weight, divided by the saturation point and capped at the top of the scale." },
        { kind: "derived", key: "esdi.saturation" },
        { kind: "p", text: "The headline is the weighted average of the covered sectors: each sector's weight × its value, summed, divided by the sum of the weights of covered sectors only." },
        { kind: "derived", key: "esdi.weights" },
        { kind: "derived", key: "esdi.uncovered" },
        { kind: "derived", key: "esdi.sensitivity" },
      ] },
    ],
    subsections: [
      { id: "recovery", blocks: [
        { kind: "p", text: "Every recovery figure carries its kind, and the three kinds are never merged into one figure:" },
        { kind: "list", items: [
          "Observed means a source reported the restoration.",
          "Estimated means a source gave an expected repair time.",
          "Modelled means no source said anything, and an assumption for that type of facility is used. A modelled value is never shown in the words of a report.",
        ] },
        { kind: "p", text: "A reported restart is not full reconstitution. “Operations resumed” is recorded as a partial restart and never turned into a restored-capacity percentage." },
        { kind: "p", text: "“No restoration report by the cut-off” means none was found. It does not mean the facility is known to be still offline." },
        { kind: "p", text: "A fall in the index over time is mostly modelled decay. It is not evidence that anything was repaired." },
        { kind: "p", text: "Modelled recovery is used only in the indexed area. The country systems show reported restorations and labelled estimates only: an event with no report says so and never ages out as recovered." },
      ] },
    ],
    seeAlso: ["why-no-country-score", "history", "withheld", "do-not-infer"],
  },
  {
    id: "why-no-country-score",
    answer: "Countries have no score because the index was built around one area's capacity bases, recovery assumptions and pattern of disruption, which do not transfer; no index is not zero.",
    blocks: [
      { kind: "p", text: "Each piece of the index fits one situation: a strike campaign against one energy system. Its sector weights are a judgement made for that system. Its recovery assumptions were set on repeated strikes, with little public reporting of restarts. Its transmission measure reaches the top of its scale after a small number of disrupted substations, so any country that reports grid events routinely would sit at the top permanently. Its capacity bases exist for that area and not, in comparable form, for every other country." },
      { kind: "p", text: "Applied elsewhere, it would produce numbers that look comparable and are not. So no figure is computed for any country." },
      { kind: "p", text: "“No score” means nothing was measured on that scale. A zero would mean “measured, and nothing wrong”. A country without a score is not rated calm, safe or resilient: a missing index is not a zero." },
      { kind: "p", text: "Instead, each country page shows its reviewed records, what the evidence supports sector by sector, how far its research has got, how that country reports outages, and national context." },
      { kind: "p", text: "A country score would need a method designed for it and a decision by the project owner. Neither exists, so none is shown." },
    ],
    seeAlso: ["esdi", "research-coverage", "absence"],
  },
  {
    id: "impact-records",
    answer: "An impact record is a reviewed, publicly reported disruption to an energy system or an essential civilian service, in any country, described by service, cause, attribution and evidence, and never scored or counted into anything.",
    blocks: [
      { kind: "derived", key: "impacts.scope" },
      { kind: "p", text: "The impact records are not a complete list of disruptions in any country. They are an expanding, reviewed sample: what research found and reviewers accepted." },
      { kind: "p", text: "A record is included when public sources establish a real interruption or degradation that is not trivial in scale or duration: for example an emergency declaration, a service cut for a large population, a stated loss of power or fuel output, or days of disruption to an essential service. A warning, a forecast, an exercise, a vulnerability notice or a data breach with no effect on a service is not included." },
      { kind: "p", text: "Attempts with no reported effect on the service are listed in their own section, labelled as attempts, and never counted with disruptions." },
      { kind: "p", text: "Each record passed three blind reviews: one for the evidence, one for attribution and sources, one for safety. None of the reviewers saw the researcher's reasoning or each other's verdict, and any one of them could hold or reject the record. The reviewers are separate sessions of the same AI model that did the research. They are independent in what they were shown and in reading the sources for themselves, not independent in model. A person reading a sample of reviewed records would be a stronger check; that remains an option and is not part of the current review." },
      { kind: "derived", key: "impacts.caveats" },
      { kind: "p", text: "Counts are not rates. A number of impact records is a number of published records in this collection: never a rate, and never compared or ranked between countries." },
      { kind: "p", text: "A record held back from a country system never reappears here, whatever the reason it was held. An attack or sabotage record is published for the country only, in every country." },
      { kind: "details", summary: "Technical detail: units, episodes and research", blocks: [
        { kind: "p", text: "Civilian-service figures keep the source's own unit. People are not customers, customers are not households, and households are not subscribers, so nothing is converted or added up. Where no source gives a figure, the record says so; it is never shown as zero." },
        { kind: "p", text: "Records that share one cause a source names, such as one storm or one coordinated wave, form an episode. Counting episodes stops one storm that touched many regions from looking like many separate disruptions." },
        { kind: "p", text: "Each record shows the date it was first published here. Combined with the event date, that separates a newly found old event from a new one." },
        { kind: "derived", key: "impacts.research" },
      ] },
    ],
    seeAlso: ["evidence-confidence", "attribution", "ai-involvement", "cyber", "absence"],
  },
  {
    id: "evidence-confidence",
    answer: "Evidence confidence says how strongly the sources a record cites support that the disruption happened and that its reported effect is right; it is not a probability, not severity, not importance, and it does not cover cause or who was responsible.",
    blocks: [
      { kind: "derived", key: "eci.status" },
      { kind: "derived", key: "eci.statement" },
      { kind: "derived", key: "eci.categories" },
      { kind: "p", text: "It counts independent originating statements, not links. Ten articles repeating one news-agency report are ten links but one originating statement. Adding more copies of the same report changes nothing." },
      { kind: "p", text: "It does not measure how important the infrastructure is, how severe the disruption was, how likely anything is, or how thoroughly a country was researched. It does not cover cause or responsibility: a well-evidenced outage can have an uncertain cause or an unknown actor." },
      { kind: "p", text: "The Russia, Belarus & Crimea index does not use this method. It still uses the site's older evidence weighting." },
      { kind: "details", summary: "Technical detail: how a category is worked out", blocks: [
        { kind: "p", text: "The category is worked out from five things about the sources that support occurrence or effect: who is speaking (an operator or official body counts for more than a repost); how many separate originating statements there are; how specific the reported effect is; whether a source was opened during research or review; and whether a source is dated at the time or is a later formal account. The number of links never enters." },
        { kind: "p", text: "The points behind a category are ordinal. They put records in order by what their citations show. They are not a percentage and not a probability, and no list on this site is ordered by them." },
        { kind: "derived", key: "eci.overrides" },
        { kind: "p", text: "Where nobody reviewed which sources relay which, the originating-statement count is a count of distinct publishers. That is an upper bound. A record cited only through an encyclopedia or an aggregator is Not assessed: that says a primary citation is not yet attached, not that the event is poorly documented." },
        { kind: "p", text: "The category describes the sources this record cites, not everything ever published about the event." },
      ] },
    ],
    seeAlso: ["attribution", "ai-involvement", "impact-records", "source-health"],
  },
  {
    id: "attribution",
    answer: "Attribution records who publicly says who was responsible, how firmly and when; the site reports attributions and never makes one itself.",
    blocks: [
      { kind: "p", text: "Attribution is a separate question from whether a disruption happened and from what caused it. Records read “X attributed this to Y”, never “Y did it”." },
      { kind: "p", text: "The statuses, from no attribution to the firmest, each with the definition the record cards use:" },
      { kind: "derived", key: "attribution.statuses" },
      { kind: "p", text: "Not established is not a low confidence. It is an absence: nobody credible has said publicly who was responsible. A claim is recorded as a claim. It is not corroboration, however many outlets repeat it." },
      { kind: "p", text: "Each attribution names who made it and gives its date. Attributions often come months after the event. A later attribution is shown with its own date, never as something known at the time." },
      { kind: "p", text: "Attribution confidence says how strong the public evidence about responsibility is. It is worked out from who made each attribution, never typed by hand. An actor's own claim is never more than claim only. The status caps it: suspected is at most low, and assessed at most moderate." },
      { kind: "derived", key: "attribution.meanings" },
      { kind: "p", text: "A ransomware or malware name identifies a tool, not an actor. Actor types such as state, state-linked or criminal are the source's words. State-linked does not mean state-controlled." },
    ],
    seeAlso: ["evidence-confidence", "ai-involvement", "cyber"],
  },
  {
    id: "ai-involvement",
    answer: "AI involvement records whether a cited source ties artificial intelligence to this particular incident, and how firmly; “None reported” means no cited source meets that standard, not that AI was absent.",
    blocks: [
      { kind: "p", text: "“None reported” is the default. It means no cited source ties AI to that incident in a way that meets the standard. It does not mean AI played no part: most incident reporting does not say either way." },
      { kind: "p", text: "Two different things are kept apart and never merged. AI-assisted means an attacker used AI tools; it does not mean AI caused the outage. AI in operations means an AI system used to run the service made the wrong decision, or an AI service the operation relied on failed." },
      { kind: "derived", key: "ai.relations" },
      { kind: "derived", key: "ai.statuses" },
      { kind: "p", text: "Not involvement: a defender using AI to detect or respond to an attack; a general warning that attackers may use AI; an attack described as modern, automated or sophisticated. A source has to say it about this incident." },
      { kind: "p", text: "Few records are expected to carry an AI line. An empty result for an AI filter is a correct answer, not a gap in the page." },
    ],
    seeAlso: ["attribution", "cyber", "evidence-confidence"],
  },
  {
    id: "research-coverage",
    answer: "Research coverage says how much of the planned search for disruptions has been done in each country, in words, never as a percentage; and “planned searches run” does not mean every event was found.",
    blocks: [
      { kind: "p", text: "Each country's research is organised in source groups, for example one regulator's notices or one country's press by year. Each group is in one state, shown in the same words everywhere on the site:" },
      { kind: "derived", key: "coverage.states" },
      { kind: "p", text: "“Planned searches run” means every planned search was run. It does not mean every event was found: a planned set of searches is not an exhaustive list. Where no complete public list of events exists, a search that finds nothing does not show a quiet year. The states are never added up into one “complete” figure." },
      { kind: "p", text: "Research preview marks the country systems whose systematic search is at an earlier stage: more of their source groups are partly searched, unavailable or not started. It does not mean the other countries are complete. Every country's search is partial in some way, preview or not, and the Research coverage tab says how." },
      { kind: "p", text: "A country can have no records because nothing met the rule for inclusion, because its sources could not be read, or because its reporting rarely discloses outages. The Research coverage tab shows which applies." },
      { kind: "p", text: "Russia, Belarus & Crimea states its coverage differently: how many reported oil-sector strikes it has enumerated against a public benchmark, and how many of its disruptions have a quantified capacity effect. Both appear in its top ribbon at the same weight as the index. Its other sectors have no benchmark." },
      { kind: "derived", key: "theatre.coverage" },
      { kind: "p", text: "Research coverage is not source health, not source freshness and not evidence confidence." },
    ],
    seeAlso: ["source-health", "absence", "evidence-confidence"],
  },
  {
    id: "source-health",
    answer: "Four different questions get four different answers: how fresh the sources are, whether they are being checked, how much research has been done, and how strong the evidence is for one record.",
    blocks: [
      { kind: "list", items: [
        "Source freshness: how old the information is. The build date says when the page was generated. Each source has its own release and retrieval dates. Each record has its own event date.",
        "Source health: whether the registered sources were re-checked on schedule, and whether cited pages still loaded at the last automated check.",
        "Research coverage: how much of the planned search for events has been done.",
        "Evidence confidence: how strong the evidence is for one record.",
      ] },
      { kind: "p", text: "None of them implies another. Sources checked on time say nothing about how complete the search is. A fresh build can rest on old sources, and an old build on fresh ones. A rebuild is not a re-read: the site is rebuilt regularly, but a source is read again only when its own check comes round." },
      { kind: "derived", key: "build.date" },
      { kind: "derived", key: "build.note" },
      { kind: "p", text: "A site that refuses the automated link checker is shown as refusing the checker. That does not mean the page is gone. A deleted post does not erase a claim that other sources corroborate." },
      { kind: "p", text: "How a country reports outages shapes what can be found there at all. Each country page names its reporting environment:" },
      { kind: "derived", key: "reporting.environments" },
      { kind: "p", text: "National energy context has its own vintage, separate from how recently any country's records were researched:" },
      { kind: "derived", key: "context.vintage" },
    ],
    seeAlso: ["research-coverage", "evidence-confidence", "whats-new"],
  },
  {
    id: "whats-new",
    answer: "What's new lists what changed in the published data since the last published build, each change named by its cause, so that a newly found old event, a rule change or the passage of time is never mistaken for a new disruption.",
    blocks: [
      { kind: "derived", key: "whatsnew.comparison" },
      { kind: "p", text: "Read it this way:" },
      { kind: "list", items: [
        "A record added now may describe an event long ago. A historical record found by research is not an event today. The date shown is when the event happened.",
        "Strengthened evidence is not a new event. Only what is known about it changed.",
        "An attribution update is not a new attack. What changed is who is reported to attribute it, and how firmly.",
        "A rule change is not an improvement or a deterioration. It can change what is shown with nothing changing in the world.",
        "A fall in the index from time decay alone is not repair. No input changed; modelled impairment aged.",
        "A withdrawn record means the record changed, not the world.",
      ] },
      { kind: "derived", key: "whatsnew.categories" },
      { kind: "derived", key: "whatsnew.note" },
      { kind: "p", text: "No counts are shown, and systems are listed alphabetically. For countries under the publication safeguards, recovery and re-review changes are not shown, and withdrawn or held records are mentioned in one sentence without a count or a date." },
    ],
    seeAlso: ["history", "withheld", "source-health"],
  },
  {
    id: "history",
    answer: "A past date can be answered in two ways, by what the site actually showed that day or by what today's evidence says about that day, and the two often differ.",
    blocks: [
      { kind: "p", text: "An example. A disruption happens on 1 March, but no report of it reaches the site until 10 April. Asked what the index looked like in mid-March, one answer is that it did not include this disruption, because the site did not yet know of it. The other answer is that it did, because the disruption had already happened. Both are true. They answer different questions." },
      { kind: "p", text: "The first answer is the as-published history: what the site actually served on each day. The second is a current-evidence reconstruction: today's evidence and today's method applied to that past date. Every chart and comparison of past dates says which one it shows. A reconstruction is never presented as what was published." },
      { kind: "p", text: "Published history starts at the earliest build that can be shown to have been served. It is never filled in for earlier days." },
      { kind: "derived", key: "history.first" },
      { kind: "p", text: "A reconstruction uses today's method too. If the method changes, a reconstruction of an old date changes with it; the as-published value does not. A reconstruction also lets later knowledge reach back: a restoration reported weeks later sets how fast that disruption is modelled to fade across its whole history. That makes it a better estimate, and not a record of what was known at the time." },
      { kind: "p", text: "The top ribbon's “since last build” change compares this build's index with the previous build's. What's new compares with the last published build dated before this one, so the two can differ. Neither change is, by itself, evidence of new damage or of repair." },
      { kind: "details", summary: "Technical detail: weekly points and first appearance", blocks: [
        { kind: "p", text: "The reconstructed series is computed at fixed weekly points. A requested date is resolved to the point at or before it, and both dates are reported, so a weekly point is never mistaken for a daily observation." },
        { kind: "p", text: "When a record was first shown is taken from the as-published history, never inferred from its event date. A record already present in the first reliable build is marked as present before tracking began, and no date is claimed for it." },
      ] },
    ],
    seeAlso: ["whats-new", "esdi"],
  },
  {
    id: "gulf-context",
    answer: "The Gulf littoral view sets the eight Gulf states side by side as a regional energy picture with no index and no ranking, and its Gulf and Strait of Hormuz context is a list of dated, sourced statements in aggregate; the latest statement is not the current status.",
    blocks: [
      { kind: "p", text: "The Gulf littoral is a geographic group: the eight states on the Gulf. It is not the GCC and not OPEC, which appear only as membership facts. National totals are context, never importance." },
      { kind: "derived", key: "groups" },
      { kind: "p", text: "The view shows national annual figures, memberships and a date-ordered list of records. It has no score, no rank, no count per country and no trend. Every Gulf country system is under the publication safeguards, so an attack record there is published for the country only." },
      { kind: "derived", key: "context.statement" },
      { kind: "p", text: "Each statement is as of its own date and names its source. “Latest” means the newest statement of that type in this collection. The latest statement is not the current status, and its age is shown beside it. Where several statements of one type share the newest date, all are marked and none is chosen." },
      { kind: "derived", key: "context.not_built" },
      { kind: "p", text: "The context section never shows a ship, a count of ships, a position, a path or an alternative to one, how much could go another way, which facility depends on the strait, or a single open-or-closed flag. A market movement is never presented as infrastructure loss, and a cause is stated only where the source states it." },
      { kind: "p", text: "The context collection is partial. Some publishers refused automated access; their statements are taken second-hand from media that reported them, and the research notes say so." },
    ],
    seeAlso: ["withheld", "product-types", "why-no-country-score"],
  },
  {
    id: "cyber",
    answer: "A cyber record is a disruption whose reported cause is a malicious act through computer systems; it names at most a broad mechanism and the effect on the service, and the site is deliberately not a vulnerability database.",
    blocks: [
      { kind: "p", text: "Cyber means a malicious act carried out through computer systems or networks. A digital failure without malice, such as a faulty software update that stopped operations, is an IT failure. IT failures are filed as technical failures, have their own filter, and are never counted as cyberattacks." },
      { kind: "derived", key: "cyber.mechanisms" },
      { kind: "p", text: "Never published: how access was gained, network addresses, vulnerability identifiers, device makes or models, protocols, credentials, tools, malware family names outside a quoted attribution statement, or anything about a named victim's defences. That is deliberate. The site records which service was affected and how, not how the attack could be repeated." },
      { kind: "p", text: "The cyber cause comes from the sources. Evidence confidence does not cover cause, so a well-evidenced outage can rest on a weaker claim that it was an attack. The attribution line and its sources show what supports it." },
      { kind: "p", text: "Attempts with no effect on a service are listed separately and never counted with disruptions." },
    ],
    seeAlso: ["attribution", "ai-involvement", "impact-records", "withheld"],
  },
  {
    id: "absence",
    answer: "An empty space on this site always has a reason, and the reasons are kept apart: a blank, a zero, unknown, not yet researched, source inaccessible, not applicable and withheld are different statements.",
    blocks: [
      { kind: "list", items: [
        "Blank: nothing was measured, or nothing applies. A blank is never a zero.",
        "Zero: measured, and the answer was none. Used only where a measurement exists.",
        "Not applicable: the question does not arise, for example a sector that does not exist in that country.",
      ] },
      { kind: "p", text: "Record cards use these words for what is not known, each with its own meaning:" },
      { kind: "derived", key: "absence.words" },
      { kind: "p", text: "No record is not no disruption. “No qualifying records in the current reviewed corpus” is not evidence that no disruption occurred. Reporting rules differ, some sources cannot be read, and every search is partial." },
      { kind: "p", text: "An unshaded region on a country map is an empty dataset, not a quiet region. A country with context figures only was not searched for disruptions, so nothing can be said about what did or did not happen there. A country with impact records but no monitored system carries no claim that its record is complete." },
      { kind: "p", text: "Recovery has absences of its own. No restoration report is not known still offline: “no restoration report by the cut-off” means none was found, not that the facility is known to be out of service. In the country systems no recovery is modelled, so an event with no report says so and never ages out as recovered." },
      { kind: "p", text: "Where the publication safeguards apply, recovery is withheld. That is a different statement from “not reported”." },
    ],
    seeAlso: ["withheld", "research-coverage", "do-not-infer"],
  },
  {
    id: "withheld",
    answer: "Some detail is deliberately not published so that the site can never serve as a targeting or facility-status tool: no coordinates, nothing finer than a first-level region, and no later status of attacked facilities while attacks are being reported.",
    blocks: [
      { kind: "p", text: "Never published, anywhere on the site or in any download:" },
      { kind: "list", items: [
        "Coordinates of any incident, or any place finer than a first-level region such as a state, province or oblast.",
        "The current operating, repair or restart status, or remaining capacity, of an attacked facility.",
        "Any ranking of facilities by importance, weakness or vulnerability, or any list of undamaged assets.",
        "Which facility or port depends on another, and the names, positions or tracks of ships.",
        "Weapon or attack-method detail, or the distance from any point to a target. The public strike table's distance column is deliberately not read.",
        "Exploit detail of any kind, and personal data of any kind.",
      ] },
      { kind: "p", text: "Publication safeguards. While attacks on a country's energy facilities are being reported, an attack record there still shows that something was reported, its date, its broad class and its cause. What is not published is the later status of the facility and, in most safeguarded countries, where in the country it happened, the operator and the facility. A country whose situation is uncertain is treated as under the safeguards." },
      { kind: "derived", key: "placement.meanings" },
      { kind: "p", text: "In Russia, Belarus & Crimea, recovery evidence is used, for display and for the index alike, only once it is old enough and any repair estimate it carries has run its course. Until then the index uses the modelled recovery assumption, which tends to overstate exposure for that period, and the disruption says that its current status is withheld. That note appears on every such disruption, so its presence reveals nothing about any one facility." },
      { kind: "derived", key: "theatre.delay" },
      { kind: "p", text: "For the country systems, when held evidence may be published has not yet been decided." },
      { kind: "p", text: "Every record cites a public source, and that page may name what the record does not. The safeguards limit what this site gathers and states. They cannot change what a cited report says." },
      { kind: "p", text: "Out of scope by design: unit positions, readiness, fuel or ammunition state, assessments of defensive gaps, and anything with targeting value. These are not withheld data. They were never collected." },
    ],
    seeAlso: ["absence", "exports", "do-not-infer"],
  },
  {
    id: "exports",
    answer: "Downloads and images carry their date, their sources and their caveats inside the file, so a table or picture taken off the site keeps the context that makes it honest.",
    blocks: [
      { kind: "list", items: [
        "Download CSV, on country pages and in the Impact atlas: the records shown, after filters. Where a page offers “About this file”, it downloads a note explaining the columns and limits: these are the published records in this collection, not a census, and counts are not comparable across countries.",
        "Images: the Russia, Belarus & Crimea briefing, the Gulf brief, impact briefs, comparisons and maps. Each carries its title, its date and its caveats inside the picture. In the briefing, some parts can be switched off; the caveat cannot.",
        "Print / PDF, on country pages, prints the page as shown.",
        "“Copy view link” and “Link to this record” give addresses that reopen a view or a single record. An address carries the view, never personal data.",
      ] },
      { kind: "p", text: "A filtered export says so. The figures in it describe the subset shown, not the whole collection." },
      { kind: "p", text: "Exports follow the same publication safeguards as the pages. Nothing in a download is more precise than what the page shows." },
    ],
    seeAlso: ["withheld", "do-not-infer", "what-to-click"],
  },
  {
    id: "do-not-infer",
    answer: "Nothing here ranks countries, measures risk or resilience, or says how much output was lost; most wrong readings come from treating an absence, a count or a context figure as a measurement it is not.",
    blocks: [
      { kind: "derived", key: "comparability" },
      { kind: "list", items: [
        "Fewer records does not mean safer, more resilient or less disrupted. Reporting rules differ from country to country.",
        "Counts are not rates. A count is the number of records published here. It is never a rate, a risk level, a resilience measure or a measure of completeness.",
        "Countries are listed alphabetically. No list on this site is a ranking.",
        "Newest is not worst. Lists are in date order.",
        "National energy context is not importance and not disruption.",
        "Exposure is not loss. The index shows capacity at disrupted sites, not output stopped.",
        "A fall in the index is not repair. Modelled impairment fades with time whether or not anything was fixed.",
        "A restart report is not full recovery, and no restoration report is not known still offline.",
        "Evidence confidence is not severity, not a probability and not importance, and it does not cover cause or responsibility.",
        "A claim of responsibility is not an attribution, and an attribution reported here is not this site's own finding.",
        "In the indexed area, rankings include only regions with reported disruption. They are not lists of targets and say nothing about undamaged infrastructure.",
        "Latest is not current. The latest Gulf context statement is not the current status.",
      ] },
      { kind: "p", text: "What the Russia, Belarus & Crimea page cannot tell you, each with its reason:" },
      { kind: "derived", key: "theatre.cannot" },
    ],
    seeAlso: ["absence", "esdi", "withheld", "glossary"],
  },
  {
    id: "glossary",
    answer: "Every term the site uses, with one plain definition each and a link of its own.",
    blocks: [
      { kind: "p", text: "Terms are listed alphabetically. Each gives a plain definition first and more detail after it. Where a definition depends on the method in force, the detail shows the definition the record cards use." },
    ],
    seeAlso: ["start-here"],
  },
];
