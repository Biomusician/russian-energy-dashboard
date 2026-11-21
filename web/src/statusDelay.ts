/** Words for the theatre's delayed facility-status rule (iteration 21).
 *
 *  WHY. During the active campaign a restoration report is used only once it is a set number of
 *  days old (`snapshot.campaign_policy.evidence_embargo_days`). So a count of "facilities with no
 *  restoration report" is a count of reported disruptions with no report dated before that
 *  cut-off: some of them may already be working again. A first-time reader saw labels such as
 *  "Facilities awaiting reconstitution" and "Median impairment age" and concluded the site lists
 *  which facilities are down now. Every surface that shows these counts takes its words from
 *  here, and the delay is read from the served data, never written into the code.
 */

import { addDays, fmtDate } from "./data";

/** The served policy fields this module reads. Absent in an old build or with no campaign. */
export interface StatusPolicy {
  applied?: boolean;
  evidence_embargo_days?: number;
}

/** Days a restoration report must age before it is used, or null when no delay applies. */
export function statusDelayDays(policy: StatusPolicy | null | undefined): number | null {
  if (!policy?.applied) return null;
  const d = policy.evidence_embargo_days;
  return typeof d === "number" && Number.isFinite(d) && d >= 0 ? d : null;
}

/** The status cut-off date: reports describing anything after it are not yet used. */
export function statusCutoff(asOf: string | null | undefined, policy: StatusPolicy | null | undefined): string | null {
  const days = statusDelayDays(policy);
  if (days == null || !asOf || !/^\d{4}-\d{2}-\d{2}$/.test(asOf)) return null;
  return addDays(asOf, -days);
}

/** Short label for the count (`unresolved_count`). It is a MODEL count: facilities whose modelled
 *  exposure is still above the index's cut-off and that no usable full-restoration report has
 *  closed. Iteration 23 (ESDI-03): it used to read "No restoration report by the cut-off", but six
 *  of the fifty facilities it counted carried a partial-restart or restoration report, and struck
 *  facilities whose modelled exposure had decayed away were not counted at all. */
export const NO_REPORT_LABEL = "Still in the index, no full-restoration report by the cut-off";

/** The rule in one clause, with the number only when the served data carries it. */
export function delayRule(policy: StatusPolicy | null | undefined): string {
  const days = statusDelayDays(policy);
  if (days != null) return `a restoration report is used only once it is ${days} days old`;
  if (policy?.applied) return "a restoration report is used only after a delay";
  return "";
}

/** The home page's one line for the theatre under "What is withheld?". It reads the delay from
 *  the manifest's theatre entry (the home page does not load the theatre snapshot). A number
 *  only when the build carries one; the rule in words when the field is absent (older build);
 *  nothing when the build says no campaign policy applies (null). */
export function theatreDelayLine(
  manifest: { systems: { kind: string; name: string; status_delay_days?: number | null }[] } | null | undefined,
): string | null {
  const t = manifest?.systems.find((s) => s.kind === "theatre");
  if (!t || t.status_delay_days === null) return null;
  const days = statusDelayDays({ applied: true, evidence_embargo_days: t.status_delay_days });
  const when = days != null ? `only once it is ${days} days old` : "only after a delay";
  return `${t.name}: while attacks on energy facilities are being reported, a facility's restoration or `
    + `repair report is used ${when}. The site never shows whether a facility is working now.`;
}

/** What the count means, in full. `withReport` is the served number of counted facilities that
 *  do carry a partial-restart or restoration report (`unresolved_with_recovery_report`); omitted
 *  where the build serves no such figure (a region, a sector), and then no number is claimed. */
export function noReportMeaning(
  asOf: string | null | undefined, policy: StatusPolicy | null | undefined, withReport?: number | null,
): string {
  const cutoff = statusCutoff(asOf, policy);
  const rule = delayRule(policy);
  const head = "A model count, not a reporting fact: facilities whose modelled exposure has not yet "
    + "decayed below the index's cut-off and that no usable report of full restoration has closed";
  const partial = withReport == null
    ? " Some may carry a partial-restart or restoration report that did not close the disruption."
    : withReport > 0
      ? ` ${withReport} of them ${withReport === 1 ? "carries" : "carry"} a partial-restart or restoration report that did not close the disruption.`
      : " None of them carries a partial-restart or restoration report.";
  const decayed = " A struck facility whose modelled exposure has decayed away is not counted, whether or not anyone reported it restored.";
  if (!rule) {
    return `${head}.${partial}${decayed} It is not an observed operating status.`;
  }
  return `${head}, by the status cut-off${cutoff ? ` (${fmtDate(cutoff)})` : ""}.${partial}${decayed} `
    + `While attacks on energy facilities are being reported, ${rule}, so a facility counted here may already be working again. `
    + "It is not a list of facilities that are down now.";
}
