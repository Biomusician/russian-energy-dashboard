/** Reader copy that more than one surface must say identically (iteration 21).
 *
 *  One definition per idea, so a badge, its explanation and a caption can never drift apart:
 *  the research-preview definition used to exist in three wordings on three pages, one of them
 *  a hover-only tooltip. No imports, so the Python tests can load this module directly.
 */

export const RESEARCH_PREVIEW_LABEL = "Research preview";

export const RESEARCH_PREVIEW_DEFINITION =
  "A research preview is a country added recently whose systematic search is still incomplete: some source "
  + "groups have not been fully searched and some sources could not be read at all, so the absence of a record is "
  + "not evidence that no disruption occurred. The Research coverage tab says what was searched.";

/** The first thing an empty country page says. Never a count, never "no disruptions". */
export const EMPTY_CORPUS_LEAD =
  "No qualifying records in the current reviewed corpus — this is not evidence that no disruption occurred.";

/** The plain first paragraph of "Why no score". */
export function noScorePlain(country: string): string {
  return `The disruption score on the Russia, Belarus & Crimea page was designed for one conflict and one energy system. `
    + `Its weights, and its assumptions about how quickly damaged infrastructure comes back, do not transfer to `
    + `${country}. Showing that score here would imply a precision this evidence does not have, so no score is `
    + `calculated for this country.`;
}

export const NO_SCORE_NOT_ZERO =
  "A zero would mean \"measured, and nothing wrong\". Here nothing has been measured on that scale at all, so "
  + "the page shows no number in its place. A blank score is an absence of measurement, not a good result.";
