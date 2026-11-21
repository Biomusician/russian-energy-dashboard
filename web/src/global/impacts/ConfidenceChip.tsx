import { useEffect, useId, useState } from "react";
import { loadConfidenceMethod } from "./load";
import { LearnMore } from "../help/LearnMore";
import { CONFIDENCE_NOT_CAUSE, NO_CONFIDENCE_REASON, componentOriginsText, confidenceLabel, isProvisional } from "./model";
import { confidenceMethod, lowerLabel, useImpactVocab } from "./vocab";
import type { ConfidenceMethod, EvidenceConfidence } from "./types";
import "../../styles/impacts.css";

/** Evidence confidence, in words, with its reasons one click away (iteration 22).
 *
 *  The category is TEXT ("Evidence confidence: High"); the tint behind it only repeats the word.
 *  Beside it, while the served method status says so, "provisional method" (iteration 23, F5/IA-10:
 *  the status used to be one click away), and under it the sentence that the category does not
 *  cover the cause, which every card shows next to it (ECI-08). "Why?" lists the served reasons
 *  and the components that produced the category, the method's full status, and the served
 *  sentence that confidence is evidence quality: not severity, not probability, not importance.
 *  No total is shown (ECI-15): a bare "79 points" beside components whose maxima add to a hundred
 *  reads as 79 out of 100, a precision the method does not have.
 *
 *  A record whose evidence was not assessed (a null category) gets a neutral "Not assessed" chip
 *  with the served reason: never "Preliminary", never an empty chip.
 *
 *  The same shape is served on impact records and on country events, so this works for both.
 */

/** The method, once a page has it. Every chip asks for it, because the provisional status beside
 *  the category comes from it; the request cache holds one request however many cards ask. */
export function useConfidenceMethod(wanted: boolean): { method: ConfidenceMethod | null; failed: boolean } {
  useImpactVocab();
  const [failed, setFailed] = useState(false);
  const have = confidenceMethod();
  useEffect(() => {
    if (!wanted || have) return;
    let live = true;
    loadConfidenceMethod().catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, [wanted, have]);
  return { method: have, failed };
}

const COMPONENT_ORDER = ["directness", "origins", "effect", "opened", "contemporaneous"] as const;

/** What one component contributed, in words taken from the method and the record. */
function componentDetail(id: (typeof COMPONENT_ORDER)[number], value: EvidenceConfidence, method: ConfidenceMethod | null): string {
  const c = value.components;
  if (id === "directness") {
    const tier = method?.components.find((x) => x.id === "directness")?.tiers?.find((t) => t.id === c.directness.tier);
    return tier?.label ?? (c.directness.tier ? c.directness.tier.replace(/_/g, " ") : "no supporting source");
  }
  if (id === "origins") return componentOriginsText(c.origins.count, c.origins.basis);
  if (id === "effect") return c.effect.specificity ? lowerLabel("effect_specificity", c.effect.specificity) : "no direct or independent source for the effect";
  // Not earned is not "no" (F13): a source not recorded as opened may have been opened, an undated
  // source is not a late one, and with no first-party source or press report nothing was counted.
  if (c.directness.tier !== "direct" && c.directness.tier !== "independent") return "not counted: no first-party source or press report";
  if (id === "opened") return c.opened.points > 0 ? "yes" : "not recorded as opened";
  const dated = c.contemporaneous.dated;
  if (dated === "at_the_time") return "yes, reported at the time";
  if (dated === "later_formal_account") return "yes, a dated formal account published later";
  if (dated === "outside_window") return "no: the cited sources are dated outside the window";
  if (dated === "not_recorded") return "not recorded: no cited source carries a date";
  return c.contemporaneous.points > 0 ? "yes" : "not recorded";
}

/** The reasons, the components and the caveats. Shared by the chip's disclosure and the inspector.
 *
 *  The category is the finding. Each component's points show how it was reached; their total is
 *  not shown at all (ECI-15), never out of a hundred and never as a percentage, which would read
 *  as a probability. The reasons are the served strings; nothing here rewords them. */
export function ConfidenceBreakdown({ value, method, failed = false }: { value: EvidenceConfidence; method: ConfidenceMethod | null; failed?: boolean }) {
  const category = method?.categories.find((c) => c.id === value.category);
  return (
    <div className="conf-breakdown">
      {category && <p>{confidenceLabel(value)}: {category.meaning}</p>}
      {value.reason && <p className="conf-reason">{value.reason}</p>}
      <ul className="conf-reasons">
        {(value.reasons ?? []).map((r, i) => <li key={i}>{r}</li>)}
      </ul>
      {value.components && (
        <table className="conf-components">
          <caption className="sr-only">What produced the evidence confidence category</caption>
          <thead><tr><th scope="col">Component</th><th scope="col">This record</th><th scope="col">Points</th></tr></thead>
          <tbody>
            {COMPONENT_ORDER.map((id) => {
              const m = method?.components.find((x) => x.id === id);
              const points = value.components[id]?.points ?? 0;
              return (
                <tr key={id}>
                  <th scope="row">{m?.label ?? id.replace(/_/g, " ")}{m ? <span className="dim"> (up to {m.max} points)</span> : null}</th>
                  <td>{value.components[id] ? componentDetail(id, value, method) : "not recorded"}</td>
                  <td className="mono">{points}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      {value.components && (
        <p className="conf-score">The category above is the finding. The points only show how it was reached: they are not a
          probability, and records are never ranked by them.</p>
      )}
      {value.disputed && <p className="conf-disputed">Disputed overrides the score: credible sources disagree, and this site does not choose.</p>}
      {method?.status && <p className="conf-status">Method status: {method.status}.</p>}
      {method ? <p className="conf-statement">{method.statement}</p>
        : <p className="conf-statement dim" role="status">{failed ? "The method description could not be loaded." : "Loading the method…"}</p>}
      <p className="conf-learn"><LearnMore anchor="evidence-confidence" /></p>
    </div>
  );
}

export function ConfidenceChip({ value }: { value: EvidenceConfidence | null | undefined }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const { method, failed } = useConfidenceMethod(true);
  const label = confidenceLabel(value);
  const status = method?.status ?? null;
  // Not assessed is its own state, said in words with its reason. It is never shown as the lowest
  // category, and never as a chip with nothing in it.
  if (!value || value.category == null) {
    return (
      <div className="conf">
        <span className="conf-chip conf-none">Evidence confidence: <strong>{label}</strong></span>{" "}
        <span className="conf-reason small">{value?.reason ?? NO_CONFIDENCE_REASON}</span>
      </div>
    );
  }
  return (
    <div className="conf">
      <span className={`conf-chip conf-${value.category.toLowerCase()}`}>Evidence confidence: <strong>{label}</strong></span>{" "}
      {isProvisional(status) && (
        <><span className="conf-provisional" title={status ?? undefined}>provisional method<span className="sr-only">: {status}</span></span>{" "}</>
      )}
      <button type="button" className="disclosure-button linklike conf-why" aria-expanded={open} aria-controls={id}
              onClick={() => setOpen((o) => !o)}
              onKeyDown={(e) => { if (e.key === "Escape" && open) { e.preventDefault(); e.stopPropagation(); setOpen(false); } }}>
        {open ? "Hide why" : "Why?"}<span className="sr-only"> Evidence confidence: {label}</span>
      </button>
      <div className="conf-scope small">{CONFIDENCE_NOT_CAUSE}</div>
      {open && (
        <div id={id} role="note" className="conf-panel small">
          <ConfidenceBreakdown value={value} method={method} failed={failed} />
        </div>
      )}
    </div>
  );
}

export default ConfidenceChip;
