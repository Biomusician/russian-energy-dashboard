import type { CountryBundle } from "./manifest";
import { CONFIDENCE_SUMMARY_NOTE, confidenceCounts } from "./evidence";
import { CONFIDENCE_IS_NOT } from "./countryCopy";
import { readerText } from "./readerText";

/** Said when no record of this country could reach High, and why (iteration 23, F14/C3). Read from
 *  the records: shown only when every assessed record's originating statements were counted as
 *  publishers, because no reviewer checked which of its sources relay which. */
export const HIGH_UNREACHABLE =
  "High is not reachable for this country's records. High needs a reviewer to have checked which cited sources relay "
  + "which; the country systems' review does not include that check, so each record's sources are counted as distinct "
  + "publishers and the record is held at Moderate at most. Moderate here is therefore not a step below the High shown on "
  + "some impact records: it is the most a country record can be.";

type Served = { evidence_confidence_summary?: { note?: string; status?: string } };
type WithOrigins = { evidence_confidence?: { category?: string | null; components?: { origins?: { basis?: string | null } } } | null };

/** Every assessed record's origins were counted as publishers: none of them could be High. */
export function highUnreachable(events: readonly WithOrigins[]): boolean {
  const assessed = events.filter((e) => e.evidence_confidence?.category != null);
  return assessed.length > 0 && assessed.every((e) => e.evidence_confidence?.components?.origins?.basis === "publishers");
}

/** How this country's published records fall across the evidence-confidence categories (iteration
 *  22). Shown on the country's own Sources & data quality tab and nowhere else: inside the
 *  country, beside its source health, in the method's order (never by size), with "Not assessed"
 *  as its own line and the sentence that it describes the citations these records carry and is not
 *  comparable across countries. No view sets two countries' summaries side by side: Compare reads
 *  none of it (a test holds that). Nothing is drawn when no record carries the field.
 *
 *  Iteration 23: the served method status is said here (F5), in its own words, which say that the
 *  first calibration run did not pass; and where High could not be reached, that is said, with why
 *  (F14). */
export function ConfidenceSummary({ bundle }: { bundle: CountryBundle }) {
  const counts = confidenceCounts(bundle.system, bundle.events);
  if (counts.length === 0) return null;
  const summary = (bundle.system as Served).evidence_confidence_summary;
  return (
    <div className="confidence-summary">
      <h3 className="eyebrow">Evidence confidence of the published records</h3>
      <ul className="small">
        {counts.map((c) => <li key={c.value}>{c.label}: {c.n}</li>)}
      </ul>
      {summary?.status && <p className="small conf-status">Method status: {summary.status}.</p>}
      {highUnreachable(bundle.events as readonly WithOrigins[]) && <p className="small">{HIGH_UNREACHABLE}</p>}
      {summary?.note && <p className="small dim">{readerText(summary.note)}</p>}
      {/* The sentence travels with the counts whatever the build's own note says. */}
      <p className="small dim">{CONFIDENCE_SUMMARY_NOTE}</p>
      <p className="small dim">{CONFIDENCE_IS_NOT} “Not assessed” is not a low category: no category has been given.</p>
    </div>
  );
}

export default ConfidenceSummary;
