/** The regional overview's sections (iteration 22): one page, more evidence, no second dashboard.
 *
 *  The page is one document that scrolls. A section is a heading a reader can jump to and link to:
 *  `?group=gulf&section=context` opens the page at that section and moves focus to its heading.
 *  Nothing is hidden behind a tab, so a reader, a printout and a screen reader all get the whole page.
 *
 *  No React and no DOM here, so the Python tests run this file in Node exactly as it ships.
 *
 *  WORDING RULE (methodology §10). Only the section `context` may carry aggregate wording about the
 *  strait and shipping. Every label and every line in this file is shown OUTSIDE that section (the
 *  navigation and the Overview), so none of them names a ship, a path or a dependence; the one
 *  heading that names the strait is the context section's own.
 */

export type SectionId = "overview" | "energy" | "systems" | "impacts" | "services" | "context" | "coverage";

export interface Section {
  id: SectionId;
  /** The words in the navigation and in the section's heading. */
  label: string;
  /** The id of the element the navigation scrolls to and focuses. */
  anchor: string;
}

/** In page order. The order is the page's reading order, never an order of importance. */
export const SECTIONS: readonly Section[] = [
  { id: "overview", label: "Overview", anchor: "sec-overview" },
  { id: "energy", label: "Energy context", anchor: "sec-energy" },
  { id: "systems", label: "Monitored systems", anchor: "sec-systems" },
  { id: "impacts", label: "Reported impacts", anchor: "sec-impacts" },
  { id: "services", label: "Cyber & civilian services", anchor: "sec-services" },
  { id: "context", label: "Gulf & Hormuz context", anchor: "sec-context" },
  { id: "coverage", label: "Research coverage", anchor: "sec-coverage" },
];

const BY_ID = new Map(SECTIONS.map((s) => [s.id as string, s]));

function pairs(search: string): [string, string][] {
  const q = search.startsWith("?") ? search.slice(1) : search;
  return q.split("&").filter(Boolean).map((part) => {
    const i = part.indexOf("=");
    return i < 0 ? [part, ""] : [part.slice(0, i), part.slice(i + 1)];
  });
}

/** The section an address names, or null. An unknown name is null, never a guess: the page then
 *  opens at its top, which is where a reader of a mistyped link expects to be. */
export function sectionFrom(search: string): Section | null {
  for (const [k, v] of pairs(search)) {
    if (k !== "section") continue;
    let name = v;
    try { name = decodeURIComponent(v); } catch { /* a malformed escape is just an unknown name */ }
    return BY_ID.get(name.trim().toLowerCase()) ?? null;
  }
  return null;
}

/** `search` with its section set (or removed for the page's top). Every other parameter and its
 *  order is kept, so the group, the record filters and a linked record survive a jump. */
export function withSection(search: string, id: SectionId | null): string {
  const kept = pairs(search).filter(([k]) => k !== "section").map(([k, v]) => (v === "" ? k : `${k}=${v}`));
  // The overview is the page's top: its address is the page's own, with no section.
  if (id && id !== "overview") kept.push(`section=${id}`);
  return kept.length ? `?${kept.join("&")}` : "";
}

/** One line of "What this page can tell you": a question, a plain answer, and the section that
 *  holds the evidence. */
export interface TellLine {
  id: string;
  question: string;
  answer: string;
  section: SectionId;
}

/** What the overview needs to know to answer in words. Counts of records never enter: the lines say
 *  what KIND of evidence is on the page, and each section says how much. */
export interface TellFacts {
  /** The group's label and how many systems it has. */
  label: string;
  members: number;
  /** Labels of the national figures on the page, in their served order. */
  metrics: string[];
  /** "loading", "unavailable", "empty" (loaded, no record for these members) or "some". */
  impacts: "loading" | "unavailable" | "empty" | "some";
  context: "loading" | "unavailable" | "empty" | "some";
}

const STATE_WORDS = {
  loading: "Loading.",
  unavailable: "Could not be loaded just now; the rest of the page is unaffected.",
} as const;

/** The eight questions, in the page's reading order. Each answer is a statement about this page,
 *  not about the region: an empty section is a fact about the reviewed corpus. */
export function tellLines(f: TellFacts): TellLine[] {
  const impacts = (some: string, empty: string) =>
    f.impacts === "some" ? some : f.impacts === "empty" ? empty : STATE_WORDS[f.impacts];
  return [
    { id: "energy", section: "energy", question: "Which energy systems are represented?",
      answer: `National annual totals for ${f.members} countries${f.metrics.length ? `: ${f.metrics.join(", ").toLowerCase()}` : ""}. One source, one year, countries only.` },
    { id: "systems", section: "systems", question: "Which countries are monitored?",
      answer: `All ${f.members} ${f.label} systems, listed alphabetically, each with its own reviewed record and its own page. None has an index or a score.` },
    { id: "evidence", section: "impacts", question: "What disruption evidence is published?",
      answer: impacts(
        "Reviewed impact records for these countries, in date order, from a separate corpus that is not scored, and the country systems' reviewed energy events.",
        "No impact record for these countries in the current reviewed corpus, which describes the corpus and not the region. The country systems' reviewed energy events are listed.") },
    { id: "context", section: "context", question: "What regional context does credible reporting document?",
      answer: f.context === "some" ? "Dated, sourced statements in aggregate, each shown as of its own date. No single status is given."
        : f.context === "empty" ? "No reviewed statement has been published yet." : STATE_WORDS[f.context] },
    { id: "services", section: "services", question: "Which civilian services have documented effects?",
      answer: impacts(
        "Records grouped by the service affected (electricity, water, telecommunications, healthcare, transport and others), in each source's own units.",
        "None in the current reviewed corpus for these countries. That is not a finding that no service was affected.") },
    { id: "causes", section: "services", question: "What is cyber, what is kinetic, what is something else?",
      answer: "Every record names one reported cause. A cyber record is a malicious act through computer systems; an IT failure is not an attack and is labelled apart; an armed attack is published for the country only." },
    { id: "certainty", section: "impacts", question: "How certain are the claims?",
      answer: "Each record carries an evidence confidence and, separately, how firmly anyone is publicly said to be responsible. Neither is a probability or a measure of severity." },
    { id: "withheld", section: "coverage", question: "What is withheld?",
      answer: "For an attack: the place, facility, operator, method, headline and any later status. For everything: coordinates and anything finer than a first-level region. Nothing here orders countries by any figure." },
  ];
}
