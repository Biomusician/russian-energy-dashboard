/** The Help page's addresses (iteration 23): `?view=help#<anchor>`.
 *
 *  The section list lives here, not beside the Help prose, because every page links into Help and
 *  the prose is a lazy chunk: a "Learn more" on the home page must not download the whole Help text
 *  to know where it points. The prose module takes its titles from this list, so a section cannot be
 *  renamed in one place and not the other, and `HelpAnchor` makes a link to a section that does not
 *  exist a type error. Glossary entries are `g-<id>`; a test checks every one resolves.
 *
 *  Order is a reading order, never a ranking. Pure: the Python tests run this file as it ships.
 */

export const HELP_VIEW = "help";

export const HELP_SECTIONS_TOC = [
  { id: "start-here", title: "Start here" },
  { id: "navigating-the-map", title: "Navigating the site and its maps" },
  { id: "what-to-click", title: "What to click" },
  { id: "product-types", title: "Four kinds of thing on this site" },
  { id: "esdi", title: "The exposure index (ESDI)" },
  { id: "why-no-country-score", title: "Why Russia, Belarus & Crimea has a number and countries do not" },
  { id: "impact-records", title: "Impact records" },
  { id: "evidence-confidence", title: "Evidence confidence" },
  { id: "attribution", title: "Who is said to be responsible" },
  { id: "ai-involvement", title: "AI involvement" },
  { id: "research-coverage", title: "Research coverage" },
  { id: "source-health", title: "Source health and freshness" },
  { id: "whats-new", title: "What's new" },
  { id: "history", title: "Dates, history and changes in the indexed area" },
  { id: "gulf-context", title: "The Gulf littoral and its regional context" },
  { id: "cyber", title: "Cyber and IT failures" },
  { id: "absence", title: "When there is nothing to show" },
  { id: "withheld", title: "What is withheld, and why" },
  { id: "exports", title: "Exports and sharing" },
  { id: "do-not-infer", title: "What not to infer" },
  { id: "glossary", title: "Glossary (A–Z)" },
] as const;

/** Subsections with an address of their own, each inside the section named. */
export const HELP_SUBSECTIONS = [
  { id: "how-it-works", title: "How this works, in six steps", parent: "start-here" },
  { id: "recovery", title: "Recovery: observed, estimated, modelled", parent: "esdi" },
] as const;

export type HelpSectionId = (typeof HELP_SECTIONS_TOC)[number]["id"];
export type HelpAnchor = HelpSectionId | (typeof HELP_SUBSECTIONS)[number]["id"] | `g-${string}`;

export function helpTitle(id: HelpSectionId): string {
  return HELP_SECTIONS_TOC.find((s) => s.id === id)!.title;
}

/** What a link names: the section or subsection title, or for a glossary entry the glossary. */
export function anchorTitle(anchor: HelpAnchor): string {
  const s = HELP_SECTIONS_TOC.find((x) => x.id === anchor) ?? HELP_SUBSECTIONS.find((x) => x.id === anchor);
  return s ? s.title : "the glossary";
}

/** The address of Help, optionally at one anchor. */
export function helpHref(anchor?: HelpAnchor): string {
  return `?view=${HELP_VIEW}${anchor ? `#${anchor}` : ""}`;
}

/** Every address on the Help page that a link may name, glossary entries excluded. */
export function helpAnchors(): string[] {
  return [...HELP_SECTIONS_TOC.map((s) => s.id), ...HELP_SUBSECTIONS.map((s) => s.id)];
}
