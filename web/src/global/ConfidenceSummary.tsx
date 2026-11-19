import type { CountryBundle } from "./manifest";
import { CONFIDENCE_SUMMARY_NOTE, confidenceCounts } from "./evidence";
import { CONFIDENCE_IS_NOT } from "./countryCopy";
import { readerText } from "./readerText";

/** How this country's published records fall across the evidence-confidence categories (iteration
 *  22). Shown on the country's own Sources & data quality tab and nowhere else: inside the
 *  country, beside its source health, in the method's order (never by size), with "Not assessed"
 *  as its own line and the sentence that it describes the citations these records carry and is not
 *  comparable across countries. Nothing is drawn when no record carries the field. */
export function ConfidenceSummary({ bundle }: { bundle: CountryBundle }) {
  const counts = confidenceCounts(bundle.system, bundle.events);
  if (counts.length === 0) return null;
  const served = (bundle.system as { evidence_confidence_summary?: { note?: string } }).evidence_confidence_summary?.note;
  return (
    <div className="confidence-summary">
      <h3 className="eyebrow">Evidence confidence of the published records</h3>
      <ul className="small">
        {counts.map((c) => <li key={c.value}>{c.label}: {c.n}</li>)}
      </ul>
      {served && <p className="small dim">{readerText(served)}</p>}
      {/* The sentence travels with the counts whatever the build's own note says. */}
      <p className="small dim">{CONFIDENCE_SUMMARY_NOTE}</p>
      <p className="small dim">{CONFIDENCE_IS_NOT} “Not assessed” is not a low category: no category has been given.</p>
    </div>
  );
}

export default ConfidenceSummary;
