import { useEffect, useId, useState } from "react";
import { loadConfidenceMethod } from "./load";
import { confidenceMethod, labelOf, lowerLabel, useImpactVocab } from "./vocab";
import type { ConfidenceMethod, EvidenceConfidence } from "./types";
import "../../styles/impacts.css";

/** Evidence confidence, in words, with its reasons one click away (iteration 22).
 *
 *  The category is TEXT ("Evidence confidence: High"); the tint behind it only repeats the word.
 *  "Why?" lists the reasons and the components that produced the category, the ordinal score with
 *  the words "not a probability" beside it, and the served sentence that confidence is evidence
 *  quality: not severity, not probability, not importance.
 *
 *  The same shape is served on impact records and on country events, so this works for both.
 */

/** The method, once a page has it. Asked for only when a reader opens a "Why?": the request cache
 *  holds one request however many cards ask. */
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
  if (id === "origins") return `${c.origins.count} originating ${c.origins.count === 1 ? "statement" : "statements"}`;
  if (id === "effect") return c.effect.specificity ? lowerLabel("effect_specificity", c.effect.specificity) : "no direct or independent source for the effect";
  return c[id].points > 0 ? "yes" : "no";
}

/** The reasons, the components and the caveats. Shared by the chip's disclosure and the inspector. */
export function ConfidenceBreakdown({ value, method, failed = false }: { value: EvidenceConfidence; method: ConfidenceMethod | null; failed?: boolean }) {
  const category = method?.categories.find((c) => c.id === value.category);
  return (
    <div className="conf-breakdown">
      {category && <p>{value.label}: {category.meaning}</p>}
      <ul className="conf-reasons">
        {value.reasons.map((r, i) => <li key={i}>{r}</li>)}
      </ul>
      <table className="conf-components">
        <caption className="sr-only">Components of the evidence confidence score</caption>
        <thead><tr><th scope="col">Component</th><th scope="col">This record</th><th scope="col">Points</th></tr></thead>
        <tbody>
          {COMPONENT_ORDER.map((id) => {
            const m = method?.components.find((x) => x.id === id);
            const points = value.components[id]?.points ?? 0;
            return (
              <tr key={id}>
                <th scope="row">{m?.label ?? id.replace(/_/g, " ")}</th>
                <td>{componentDetail(id, value, method)}</td>
                <td className="mono">{points}{m ? ` of ${m.max}` : ""}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="conf-score">
        <span className="mono">{value.score} of 100</span>: ordinal score, not a probability.
        {value.disputed && " Disputed overrides the score: credible sources disagree, and this site does not choose."}
      </p>
      {method ? <p className="conf-statement">{method.statement}</p>
        : <p className="conf-statement dim" role="status">{failed ? "The method description could not be loaded." : "Loading the method…"}</p>}
    </div>
  );
}

export function ConfidenceChip({ value }: { value: EvidenceConfidence | null | undefined }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const { method, failed } = useConfidenceMethod(open);
  // Absent is said as absent. It is never shown as the lowest category.
  if (!value) return <span className="conf-chip conf-none small">Evidence confidence: not computed for this record</span>;
  const label = value.label || labelOf("confidence_categories", value.category);
  return (
    <div className="conf">
      <span className={`conf-chip conf-${value.category.toLowerCase()}`}>Evidence confidence: <strong>{label}</strong></span>{" "}
      <button type="button" className="disclosure-button linklike conf-why" aria-expanded={open} aria-controls={id}
              onClick={() => setOpen((o) => !o)}
              onKeyDown={(e) => { if (e.key === "Escape" && open) { e.preventDefault(); e.stopPropagation(); setOpen(false); } }}>
        {open ? "Hide why" : "Why?"}<span className="sr-only"> Evidence confidence: {label}</span>
      </button>
      {open && (
        <div id={id} role="note" className="conf-panel small">
          <ConfidenceBreakdown value={value} method={method} failed={failed} />
        </div>
      )}
    </div>
  );
}

export default ConfidenceChip;
