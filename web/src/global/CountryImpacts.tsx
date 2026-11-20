import { useEffect, useMemo, useRef, useState } from "react";
import type { CountrySystem } from "./manifest";
import { ImpactCard, loadImpacts, type ImpactRecord, type ImpactsPayload } from "./impacts";
import { confidenceMethod, labelOf, useImpactVocab } from "./impacts/vocab";
import { RecordFilterBar } from "./RecordFilterBar";
import { NO_FILTERS, activeFilters, applyFilters, describeFilters, type FilterState } from "./recordFilters";
import { countryImpacts, impactFiles, impactFilters, impactOrder } from "./countryImpactModel";
import { IMPACT_CORPUS_LINE, IMPACT_INCLUSION_LINE, noImpactRecordText, type ImpactPresence } from "./countryOverview";
import { TAB_LABEL } from "./countryTabs";
import { inSentence } from "./countryCopy";
import { downloadBlob } from "../download";
import { fmtDate } from "../data";
import "../styles/country.css";
import "../styles/countryOverview.css";

/** The "Impact records (not scored)" tab of a country page (iteration 22).
 *
 *  This country's records from the global impact layer: a separate, non-scored corpus. The tab
 *  says so before it lists anything, and nothing here reaches the country's published-record
 *  count, its map or any index.
 *
 *  The corpus is one file for every country, fetched when this tab is first opened (and at once on
 *  a page with no published record, whose overview would otherwise have nothing to say about it).
 */

export type CountryImpactsState =
  | { state: "not_loaded" }
  | { state: "loading" }
  | { state: "failed" }
  | { state: "ready"; payload: ImpactsPayload; records: ImpactRecord[]; attempts: ImpactRecord[] };

/** This country's impact records, asked for once `wanted` is true. A failure is not kept: when
 *  `retryKey` changes (the reader opens another tab, or this one again) the file is asked for again.
 *  The view is keyed on the system, so one mounted hook only ever serves one country. */
export function useCountryImpacts(systemId: string, wanted: boolean, retryKey: string): CountryImpactsState {
  const [s, setS] = useState<CountryImpactsState>({ state: "not_loaded" });
  const now = useRef(s.state);
  now.current = s.state;
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    if (!wanted || now.current === "ready" || now.current === "loading") return;
    setS({ state: "loading" });
    // Not cancelled when the tab changes: the answer is wanted whichever tab is open by then.
    loadImpacts()
      .then((payload) => { if (mounted.current) setS({ state: "ready", payload, ...countryImpacts(payload, systemId) }); })
      .catch(() => { if (mounted.current) setS({ state: "failed" }); });
  }, [wanted, retryKey, systemId]);
  return s;
}

/** What the overview needs to know about the corpus, and nothing more. */
export function impactPresence(s: CountryImpactsState): ImpactPresence {
  if (s.state !== "ready") return { state: s.state };
  return { state: "ready", records: s.records.length, attempts: s.attempts.length, latestResearch: s.payload.research?.latest_research_date ?? null };
}

/** When the impact research last ran, in a sentence. Never a claim that the corpus is complete. */
export function researchRanText(payload: Pick<ImpactsPayload, "research">): string {
  const d = payload.research?.latest_research_date;
  return d ? `The impact research last ran on ${fmtDate(d)}. The corpus is still being built and is not a census.`
    : "No impact research pass has been logged yet.";
}

export function CountryImpacts({ sys, impacts, today }: { sys: CountrySystem; impacts: CountryImpactsState; today: string }) {
  useImpactVocab();
  return (
    <div className="country-impacts">
      <h2>{TAB_LABEL.impacts}</h2>
      <p className="small impacts-what" role="note">{IMPACT_CORPUS_LINE}</p>
      <p className="small impacts-inclusion">{IMPACT_INCLUSION_LINE}</p>
      {(impacts.state === "not_loaded" || impacts.state === "loading") && <p className="small dim" role="status">Loading the impact corpus…</p>}
      {impacts.state === "failed" && (
        <p className="small warn-text" role="alert">The impact corpus could not be loaded. The rest of this page is not affected; reopen this tab to try again.</p>
      )}
      {impacts.state === "ready" && <ImpactList sys={sys} payload={impacts.payload} records={impacts.records} attempts={impacts.attempts} today={today} />}
    </div>
  );
}

function ImpactList({ sys, payload, records, attempts, today }: {
  sys: CountrySystem; payload: ImpactsPayload; records: ImpactRecord[]; attempts: ImpactRecord[]; today: string;
}) {
  // Local to the tab: the address's filter keys belong to the country's own published record.
  const [state, setState] = useState<FilterState>(NO_FILTERS);
  const [exportMsg, setExportMsg] = useState<string | null>(null);
  const method = confidenceMethod();
  const defs = useMemo(() => impactFilters(payload, records, method?.categories.map((c) => c.id)), [payload, records, method]);
  const shown = useMemo(() => impactOrder(applyFilters(records, defs, state, today)), [records, defs, state, today]);
  const filtering = activeFilters(defs, state).length > 0;
  const name = inSentence(sys.name);

  const save = (which: "csv" | "readme") => {
    const out = impactFiles(sys.system_id, sys.name, shown, records.length, describeFilters(defs, state, today), payload, today);
    if (which === "csv") {
      downloadBlob(new Blob([out.csv], { type: "text/csv;charset=utf-8" }), out.csvName);
      setExportMsg(`Saved ${out.csvName}: ${shown.length} of ${records.length} impact records.`);
    } else {
      downloadBlob(new Blob([out.readme], { type: "text/plain;charset=utf-8" }), out.readmeName);
      setExportMsg(`Saved ${out.readmeName}.`);
    }
  };

  return (
    <>
      {records.length === 0 ? (
        <div className="impacts-empty">
          <p className="empty-lead">{noImpactRecordText(sys.name)}</p>
          {payload.empty_reason && <p className="small">{payload.empty_reason}</p>}
          <p className="small">{researchRanText(payload)}</p>
        </div>
      ) : (
        <>
          <RecordFilterBar defs={defs} state={state} onChange={setState} records={records} shown={shown.length}
                           today={today} noun={`reviewed impact records for ${name}`}>
            <span className="record-export" role="group" aria-label="Download the impact records shown">
              <button type="button" className="ghost" onClick={() => save("csv")} disabled={shown.length === 0}
                      aria-label={`Download CSV of the ${shown.length} impact ${shown.length === 1 ? "record" : "records"} shown`}>Download CSV</button>
              <button type="button" className="ghost" onClick={() => save("readme")}
                      aria-label="About this file: download the note that explains the impact CSV">About this file</button>
            </span>
          </RecordFilterBar>
          {exportMsg && <p className="small" role="status">{exportMsg}</p>}
          {filtering && shown.length === 0 && (
            <p className="small filter-empty" role="status">No impact record in this list matches the filters. That describes the
              filters, not {name}. Clear the filters to see {records.length === 1 ? "the record" : `all ${records.length} records`}.</p>
          )}
          <ol className="event-list impact-list" aria-label={`Reviewed impact records for ${name}, newest first`}>
            {shown.map((r) => <li key={r.impact_id} className="event-item"><ImpactCard record={r} /></li>)}
          </ol>
          <p className="small dim">{researchRanText(payload)}</p>
        </>
      )}
      {attempts.length > 0 && (
        <section className="impact-attempts" aria-labelledby="impact-attempts-title">
          <h3 className="eyebrow" id="impact-attempts-title">{payload.attempts_label ?? labelOf("record_kinds", "attempt_no_service_impact")}</h3>
          <p className="small dim">Documented attempts with no reported service disruption. Listed apart, and never counted with the records above.</p>
          <ol className="event-list impact-list">
            {impactOrder(attempts).map((r) => <li key={r.impact_id} className="event-item"><ImpactCard record={r} /></li>)}
          </ol>
        </section>
      )}
      {payload.caveats.length > 0 && (
        <details className="small impacts-caveats">
          <summary>What this corpus is, and is not</summary>
          <p>{payload.scope_statement}</p>
          <ul>{payload.caveats.map((c) => <li key={c}>{c}</li>)}</ul>
        </details>
      )}
    </>
  );
}

export default CountryImpacts;
