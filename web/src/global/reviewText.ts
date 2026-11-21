/** Who the reviewers were, in one sentence every review label shares (iteration 23, F4/C12).
 *
 *  "Three independent reviewers" reads as three people. They were separate sessions of the same AI
 *  model as the researcher, each given the record but not the researcher's reasoning
 *  (docs/REVIEW_GOVERNANCE.md §4): independent in context, not in model. The build adds the same
 *  sentence to every served review that claims independence (pipeline/build_systems.py
 *  REVIEWER_DISCLOSURE). Import-free, so the Python tests run it in Node as it ships. */
export const REVIEWERS_SAME_MODEL =
  "The reviewers were separate sessions of the same AI model as the researcher: independent in context, not in model.";
