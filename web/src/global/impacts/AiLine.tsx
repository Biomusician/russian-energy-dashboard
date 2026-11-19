import { fmtDate } from "../../data";
import { aiReported } from "./model";
import { definitionOf, labelOf, lowerLabel, useImpactVocab } from "./vocab";
import type { AiInvolvement } from "./types";
import "../../styles/impacts.css";

/** AI involvement, only where a source reports it (iteration 22).
 *
 *  Renders NOTHING for NONE_REPORTED: an ordinary cyber record carries no AI line, so the absence
 *  of one never reads as a finding. Where a source does tie AI to the incident the line keeps two
 *  things apart that are easy to merge: an attacker who used AI tooling ("AI-assisted", which is
 *  not "AI-caused") and an AI system in operations that itself failed ("AI as operational cause").
 */

// What each relation must never be read as. Keyed on the served relation; the label is served.
const RELATION_GUARD: Record<string, string> = {
  ai_assisted: "not AI-caused",
  ai_operational_cause: "AI as operational cause",
};

export function AiLine({ ai }: { ai: AiInvolvement | null | undefined }) {
  useImpactVocab();
  if (!ai || !aiReported(ai)) return null;
  const guard = ai.relation && Object.prototype.hasOwnProperty.call(RELATION_GUARD, ai.relation) ? RELATION_GUARD[ai.relation] : null;
  const relation = ai.relation ? `${labelOf("ai_relations", ai.relation)}${guard ? ` (${guard})` : ""}` : "relation not stated";
  const parts = [
    lowerLabel("ai_statuses", ai.status),
    ai.role ? lowerLabel("ai_roles", ai.role) : null,
    relation,
    ai.as_of ? `as of ${fmtDate(ai.as_of)}` : null,
  ].filter(Boolean);
  const meaning = ai.relation ? definitionOf("ai_relations", ai.relation) : null;
  return (
    <div className={`ai-line ai-${ai.status.toLowerCase()} small`}>
      <span className="impact-line-label">AI involvement:</span> {parts.join(" · ")}
      {ai.statement && <div className="ai-statement">{ai.statement}</div>}
      {meaning && <div className="dim">{meaning}</div>}
    </div>
  );
}

export default AiLine;
