import { useId, useRef, useState } from "react";
import { fmtDate } from "../../data";
import { AiLine } from "./AiLine";
import { AttributionLine } from "./AttributionLine";
import { ConfidenceChip } from "./ConfidenceChip";
import { ImpactInspector } from "./ImpactInspector";
import { DISRUPTION, impactDateText, isAbstracted, isHistoricalAddition, isItFailure, placeText, serviceLine } from "./model";
import { definitionOf, isAbsenceWord, labelOf, lowerLabel, useImpactVocab } from "./vocab";
import type { ImpactRecord } from "./types";
import "../../styles/country.css";
import "../../styles/impacts.css";

/** One impact record (iteration 22).
 *
 *  Read top to bottom: when, where (country, and the first-level region when one is published),
 *  what kind of service and cause, what was reported, who it affected in the source's own unit,
 *  who is said to be responsible, whether a source ties AI to it, and how strong the evidence is.
 *  "Sources (n)" opens the Evidence Inspector.
 *
 *  An abstracted (attack or sabotage) record shows the country and nothing finer, with a note
 *  that the place is withheld. An attempt is labelled as one, in words.
 */
export function ImpactCard({ record }: { record: ImpactRecord }) {
  useImpactVocab();
  const r = record;
  const [open, setOpen] = useState(false);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();
  const abstracted = isAbstracted(r);
  const when = impactDateText(r);
  const place = placeText(r);
  const attempt = r.record_kind !== DISRUPTION;
  // An absence word in the technology field says why there is none; null (outside energy) says nothing.
  const technology = r.technology == null ? null
    : isAbsenceWord(r.technology) ? `Technology: ${lowerLabel("absence_words", r.technology)}` : labelOf("technologies", r.technology);
  const mechanism = r.cyber_mechanism ? lowerLabel("cyber_mechanisms", r.cyber_mechanism) : null;
  return (
    <article className={`impact-card${attempt ? " impact-attempt" : ""}`} aria-label={`${when}, ${place}`}>
      {attempt && <p className="impact-attempt-label">{labelOf("record_kinds", r.record_kind)}</p>}
      <div className="event-head">
        <span className="event-date mono">{when}</span>
        <span className="impact-place">{place}</span>
      </div>
      <div className="event-tags impact-tags">
        <span className="event-tag">{labelOf("domains", r.domain)}</span>
        <span className="event-tag">{labelOf("sectors", r.sector)}</span>
        {technology && <span className="event-tag">{technology}</span>}
        <span className="event-tag impact-cause">Cause: {lowerLabel("cause_families", r.cause_family)}</span>
        {mechanism && <span className="event-tag">{isItFailure(r) ? "IT failure" : "Mechanism"}: {mechanism}</span>}
        {r.contributing_factors.map((c) => <span key={c} className="event-tag">Contributing: {lowerLabel("cause_families", c)}</span>)}
      </div>
      <p className="small event-summary">{r.summary}</p>
      <dl className="event-facts small">
        {r.effect && (
          <div>
            <dt>Reported effect</dt>
            <dd>{r.effect}{r.effect_specificity && <span className="dim"> ({lowerLabel("effect_specificity", r.effect_specificity)})</span>}</dd>
          </div>
        )}
        {r.civilian_service_impact.length > 0 && (
          <div>
            <dt>Civilian-service impact</dt>
            <dd>
              <ul className="impact-services">
                {r.civilian_service_impact.map((s, i) => {
                  const line = serviceLine(s);
                  return (
                    <li key={i}>
                      <strong>{line.service}</strong> · {line.scope.toLowerCase()}
                      {line.affected && <> · affected: {line.affected}</>}
                      {line.unitNote && <span className="dim"> ({line.unitNote}; not converted)</span>}
                      {line.duration && <> · duration: {line.duration}</>}
                    </li>
                  );
                })}
              </ul>
            </dd>
          </div>
        )}
      </dl>
      {r.dispute && (
        <p className="small impact-dispute">
          <span className="impact-line-label">Disputed:</span> {lowerLabel("dispute_about", r.dispute.about)}. {r.dispute.statement}
        </p>
      )}
      <AttributionLine a={r.attribution} />
      <AiLine ai={r.ai_involvement} />
      <ConfidenceChip value={r.evidence_confidence} />
      {abstracted && (
        <p className="small dim withheld-note">Published under safeguards: place withheld.{" "}
          {definitionOf("publication_policies", "country_abstracted") ?? "An attack or sabotage record is published for the country only."}</p>
      )}
      {isHistoricalAddition(r) && r.first_published && (
        <p className="small dim impact-historical">Historical record added {fmtDate(r.first_published)}.</p>
      )}
      <button ref={toggleRef} type="button" className="ghost ev-inspector-toggle" aria-expanded={open} aria-controls={panelId}
              onClick={() => setOpen((o) => !o)}
              onKeyDown={(e) => { if (e.key === "Escape" && open) { e.preventDefault(); e.stopPropagation(); setOpen(false); } }}>
        {open ? "Close evidence inspector" : `Sources (${r.sources.length})`}
        <span className="sr-only">: evidence inspector for {when}, {place}</span>
      </button>
      {open && <ImpactInspector id={panelId} record={r} onClose={() => { setOpen(false); toggleRef.current?.focus(); }} />}
    </article>
  );
}

export default ImpactCard;
