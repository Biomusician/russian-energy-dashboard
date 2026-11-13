/**
 * Provenance text as a reader sees it (iteration 20, §69, §119).
 *
 * The served JSON keeps its references for an analyst reading it: methodology file names and
 * section numbers, the project's iteration labels, the research tools a pass used. A page shows
 * the same sentence without the parts a reader cannot follow. Nothing here changes a fact: it
 * removes references and replaces three tool phrases with plain words. The data is unchanged.
 */
const PATH = String.raw`(?:[\w.-]+\/)*`;
const FILE = String.raw`${PATH}[A-Z][A-Z0-9_]*\.md(?:\s*§[\d.]+(?:\s*(?:and|,)\s*§[\d.]+)*)?`;

const RULES: [RegExp, string][] = [
  // "(GLOBAL_METHODOLOGY.md §2 and §8.3)", "(data/candidates/README.md)", "(docs/countries/AE_SYSTEMATIC_SWEEP.md)"
  [new RegExp(String.raw`\s*\((?:see\s+)?${FILE}\)`, "g"), ""],
  // "See GLOBAL_METHODOLOGY.md §5.1 for the full red-team."
  [new RegExp(String.raw`\s*See\s+${FILE}[^.]*\.`, "g"), ""],
  // a file name left inside a sentence: "lanes as declared in docs/countries/AE_SYSTEMATIC_SWEEP.md"
  [new RegExp(FILE, "g"), "the published research plan"],
  // "(since iteration 17)", "(iteration 19, Wave A)"
  [/\s*\((?:since\s+)?iteration[- ]\d+[^)]*\)/g, ""],
  // "outside this system's geography this iteration;" (iteration 21): a release label, not a date
  [/\s+(?:in |for )?this iteration\b/g, ""],
  // a pass signed "iteration-19 Gulf research pass" reads "Gulf research pass"; its date is beside it
  [/^iteration-\d+\s+/, ""],
  [/\bthis agent's first search\b/g, "the first search of this source group"],
  [/through WebFetch, which returns a model's reading of the page rather than the raw text; the model declined/g,
    "through an automated reader that returns a summary of the page rather than its raw text, and the reader declined"],
  [/ in the two-dimension vocabulary/g, " in the current vocabulary"],
];

export function readerText(s: string | null | undefined): string {
  if (!s) return s ?? "";
  let out = s;
  for (const [re, to] of RULES) out = out.replace(re, to);
  return out.replace(/\s{2,}/g, " ").replace(/\s+([.,;:])/g, "$1").trim();
}
