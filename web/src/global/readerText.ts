/**
 * Provenance text as a reader sees it.
 *
 * The served JSON keeps its references for an analyst reading it: methodology file names and
 * section numbers, the project's release labels, the research tools a pass used, vocabulary keys.
 * A page shows the same sentence without the parts a reader cannot follow. Nothing here changes a
 * fact: it removes references and replaces internal phrases with plain words. The data is unchanged.
 *
 * Every surface that shows served free text (notes, reasons, limitations, pass scopes) runs it
 * through readerText. readerText.test.ts walks every country system's served text and fails if a
 * developer term survives.
 */
const PATH = String.raw`(?:[\w.-]+\/)*`;
const FILE = String.raw`${PATH}[A-Z][A-Z0-9_]*\.md(?:\s*§[\d.]+(?:\s*(?:and|,)\s*§[\d.]+)*)?`;

const RULES: [RegExp, string | ((m: string) => string)][] = [
  // "(GLOBAL_METHODOLOGY.md §2 and §8.3)", "(data/candidates/README.md)", "(docs/countries/AE_SYSTEMATIC_SWEEP.md)"
  [new RegExp(String.raw`\s*\((?:see\s+)?${FILE}\)`, "g"), ""],
  // "See GLOBAL_METHODOLOGY.md §5.1 for the full red-team."; "See docs/countries/CN_SOURCE_AUDIT.md."
  [new RegExp(String.raw`\s*See\s+${FILE}[^.]*\.`, "g"), ""],
  // "work order in docs/countries/GULF_CONTINUATION_PLAN_20.md" is a second plan reference in one sentence
  [new RegExp(String.raw`,?\s*work order in ${FILE}`, "g"), ""],
  // a file name left inside a sentence: "lanes as declared in docs/countries/AE_SYSTEMATIC_SWEEP.md"
  [new RegExp(FILE, "g"), "the published research plan"],
  // a plan clause cited bare: "(plan A.1: no census source; ...)" keeps its reason, drops the number
  [/\bplan [A-Z]\.\d+:\s*/g, ""],

  // Release labels. A reader sees pass dates beside these sentences; the label adds nothing.
  // "(since iteration 17)", "(iteration 19, Wave A)", "(iteration 20)"
  [/\s*\((?:since\s+)?iteration[- ]\d+[^)]*\)/g, ""],
  // "outside this system's geography this iteration;": a release label, not a date
  [/\s+(?:in |for )?this iteration\b/g, ""],
  // a pass signed "iteration-19 Gulf research pass" reads "Gulf research pass"; its date is beside it
  [/^iteration-\d+\s+/, ""],
  // "continuation of the iteration-19 pass"
  [/\bthe iteration-\d+ pass\b/g, "the earlier pass"],
  // "iteration 17's finding", "iteration-16 dispositions", "since iteration 17", "Iteration 20 added"
  // "Seven Gulf states were added in iteration 19 as a geographic expansion"
  [/\badded in iteration \d+\b/g, "added later"],
  [/\biteration \d+'s\b/g, "an earlier pass's"],
  [/\bin iteration \d+\b/g, "in an earlier pass"],
  [/\biteration-\d+\b/g, "earlier-pass"],
  [/\bIteration \d+\b/g, "A later pass"],
  [/\biteration \d+\b/g, "an earlier pass"],

  // Research tools and process roles, in plain words. The limitation each states is kept.
  [/\bthis agent's first search\b/g, "the first search of this source group"],
  [/through WebFetch, which returns a model's reading of the page rather than the raw text; the model declined/g,
    "through an automated reader that returns a summary of the page rather than its raw text, and the reader declined"],
  [/\bThe shared search allowance ran out\b/g, "The pass reached its search limit"],
  [/\bshared search (?:allowance|budget) exhausted\b/g, "the pass's search limit was reached"],
  [/\bsearch allowance\b/g, "search limit"],
  [/\bsource-audit lane\b/g, "source audit"],
  [/\bThe lead's reading of public reporting\b/g, "A reading of public reporting"],
  [/\bproposed, awaiting owner approval\b/g, "proposed, not yet approved"],
  [/\buntil the owner (?:rules|decides)\b/g, "until a ruling is made"],
  [/\bif the owner accepts it\b/g, "if it is accepted"],

  // Vocabulary keys and shouted labels a reader would have to decode
  [/ in the two-dimension vocabulary/g, " in the current vocabulary"],
  [/\bthe two-dimension name\b/g, "the current name"],
  [/\bThe execution value\b/g, "This state"],
  [/\benumerated_complete\b/g, "fully enumerated"],
  [/\bdeclared_search_complete\b/g, "declared search complete"],
  [/\bCONTEXT ONLY\b/g, "Context only"],
  [/\b([Aa]) SYSTEMATIC pass\b/g, "$1 systematic pass"],
  [/\b([Aa]) TARGETED pass\b/g, "$1 targeted pass"],
  [/\bis PARTIAL\b/g, "is partial"],
  // readiness and sector-state keys inside a sentence read as the label the page gives them
  [/\bINDEX_READY\b/g, "index-ready"],
  [/\bEXPERIMENTAL\b/g, "experimental"],
  [/\bSCORED\b/g, "scored"],
  [/\bCONTEXT_ONLY\b/g, "context only"],
  [/\bINSUFFICIENT_EVIDENCE\b/g, "insufficient evidence"],
  [/\bThe served-data gates recurse into every country payload\b/g, "The safety checks on published data cover every country"],
  [/\ballowed_domains works\b/g, "a domain filter works"],
  // any other snake_case key left in a sentence ("covered_through is null", "crude_oil_production"):
  // the words, without the underscores. Not inside an address or file name.
  [/(?<![\w/.-])[a-z]+(?:_[a-z]+)+(?![\w/.-])/g, (m) => m.replace(/_/g, " ")],
];

export function readerText(s: string | null | undefined): string {
  if (!s) return s ?? "";
  let out = s;
  for (const [re, to] of RULES) out = typeof to === "string" ? out.replace(re, to) : out.replace(re, to);
  return out.replace(/\s{2,}/g, " ").replace(/\s+([.,;:])/g, "$1").trim();
}
