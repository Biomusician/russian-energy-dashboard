import { Suspense, lazy, useEffect, useMemo, useState } from "react";
import SystemSwitcher from "../SystemSwitcher";
import { GlobalNavBar } from "../GlobalNav";
import { PanelBoundary } from "../../components/ViewBoundary";
import { RecordFilterBar } from "../RecordFilterBar";
import {
  applyFilters, decodeFilters, describeFilters, encodeFilters, toggleChoice, withFilterQuery,
  type FilterState,
} from "../recordFilters";
import { IMPACT_COLUMNS, IMPACT_FIELDS, csvFilename, impactRecordsCsv, readmeFilename, readmeText } from "../recordCsv";
import { LOCATION_EVENT } from "../router";
import { downloadBlob } from "../../download";
import { localISODate } from "../../freshness";
import { fmtDate } from "../../data";
import { ImpactCard } from "./ImpactCard";
import { loadConfidenceMethod, loadImpacts } from "./load";
import { attempts as attemptsOf, disruptions, monthHeading } from "./model";
import {
  PAGE, activePreset, atlasFilterDefs, atlasPresets, corpusSummary, countriesPresent, groupByMonth, presenceCodes, presetQuery,
} from "./atlasModel";
import { labelOf } from "./vocab";
import type { ConfidenceMethod, ImpactRecord, ImpactsPayload } from "./types";
import "../../styles/home.css";
import "../../styles/impacts.css";

// MapLibre is about a megabyte: the map is its own chunk, fetched only when the map is shown.
const PresenceMap = lazy(() => import("./ImpactPresenceMap"));

/** The Impact Atlas (iteration 22): the cross-country corpus of reviewed impact records.
 *
 *  WHAT IT REFUSES TO SHOW. No count per country, no ranking, no "most affected", no sort by any
 *  figure. The timeline is chronological and nothing else. The map marks presence in one colour.
 *  Attempts sit in their own collapsed section and are in no count.
 *
 *  STATE. The address is the only state: every filter and preset writes `f.<id>=` parameters and
 *  the view re-reads them, so a copied link, a reload and Back all show the same thing. A preset
 *  or a country pick is a new history entry; an edit inside the filter bar replaces the current one,
 *  so Back leaves the edit instead of stepping through every checkbox.
 */

export const BIAS_NOTE = "Counts are published records in this corpus, not rates. Disclosure laws differ, operators may not "
  + "disclose, and conflicts distort reporting, so a count says how much was found and reviewed, not how much happened.";

/** Beside the filter bar's count, where the full note is a screen above. */
export const BIAS_SHORT = "A count of published records in this corpus, not a rate: what is disclosed and reported differs by country.";

type Load = { status: "loading" } | { status: "failed"; message: string } | { status: "ready"; payload: ImpactsPayload };

function useSearch(): string {
  const [search, setSearch] = useState(() => window.location.search);
  useEffect(() => {
    const sync = () => setSearch(window.location.search);
    window.addEventListener("popstate", sync);
    window.addEventListener(LOCATION_EVENT, sync);
    return () => { window.removeEventListener("popstate", sync); window.removeEventListener(LOCATION_EVENT, sync); };
  }, []);
  return search;
}

function go(query: string, push: boolean) {
  const url = `${window.location.pathname}${query ? `?${query}` : ""}`;
  if (push) window.history.pushState(null, "", url); else window.history.replaceState(null, "", url);
  window.dispatchEvent(new Event(LOCATION_EVENT));
}

/** A link that moves inside the atlas on a plain click and stays a real link otherwise. */
function plainClick(e: React.MouseEvent): boolean {
  return e.button === 0 && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey;
}

export default function ImpactAtlas() {
  const [load, setLoad] = useState<Load>({ status: "loading" });
  const [method, setMethod] = useState<ConfidenceMethod | null>(null);
  // The filters are drawn once the method has arrived or failed: it names the confidence
  // categories, and a filter list that changed a moment after a link was read would flash a note
  // about a value "this list does not have".
  const [methodSettled, setMethodSettled] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => { document.title = "Energy Disruption Monitor — impact atlas"; }, []);
  useEffect(() => {
    let live = true;
    setLoad({ status: "loading" });
    loadImpacts()
      .then((payload) => { if (live) setLoad({ status: "ready", payload }); })
      .catch((e) => { if (live) setLoad({ status: "failed", message: e instanceof Error ? e.message : String(e) }); });
    // The method names the confidence categories and answers "Why?". The atlas works without it.
    loadConfidenceMethod().then((m) => { if (live) setMethod(m); }).catch(() => undefined)
      .finally(() => { if (live) setMethodSettled(true); });
    return () => { live = false; };
  }, [attempt]);

  return (
    <div className="global-page atlas-page">
      <header className="site-head">
        <GlobalNavBar trail={[{ label: "Impact atlas" }]} extra={<SystemSwitcher current={null} />} />
      </header>
      <div className="page-title">
        <div>
          <h1 className="ribbon-title">Impact atlas</h1>
          <div className="ribbon-sub">Reviewed, publicly reported disruptions to energy and essential civilian services · no score</div>
        </div>
        <span className="atlas-badge">Expanding corpus, not a census</span>
      </div>
      <main className="global-main atlas-main">
        {(load.status === "loading" || (load.status === "ready" && !methodSettled)) && <p className="dim" role="status">Loading the impact corpus…</p>}
        {load.status === "failed" && (
          <section className="panel view-failed" role="alert" aria-label="The impact corpus could not be loaded">
            <h2 className="home-h2">The impact corpus could not be loaded</h2>
            <p>The file that holds the impact records is missing or malformed, so no record is shown. Nothing else on the
              site depends on it: the overview, the country pages and the Russia, Belarus &amp; Crimea view still work.</p>
            <p className="small dim">{load.message}</p>
            <p>
              <button type="button" className="ghost" onClick={() => setAttempt((n) => n + 1)}>Try again</button>{" "}
              <a href={window.location.pathname}>Open the overview</a>
            </p>
          </section>
        )}
        {load.status === "ready" && methodSettled && (
          <PanelBoundary label="The impact atlas">
            <AtlasBody payload={load.payload} method={method} />
          </PanelBoundary>
        )}
      </main>
    </div>
  );
}

function AtlasBody({ payload, method }: { payload: ImpactsPayload; method: ConfidenceMethod | null }) {
  const search = useSearch();
  const today = localISODate(new Date());
  const records = useMemo(() => disruptions(payload), [payload]);
  const attempts = useMemo(() => attemptsOf(payload), [payload]);
  const defs = useMemo(() => atlasFilterDefs(payload, method), [payload, method]);
  const presets = useMemo(() => atlasPresets(payload), [payload]);
  const { state, notes } = useMemo(() => decodeFilters(search, defs), [search, defs]);
  const shown = useMemo(() => applyFilters(records, defs, state, today), [records, defs, state, today]);
  const shownAttempts = useMemo(() => applyFilters(attempts, defs, state, today), [attempts, defs, state, today]);
  const summary = useMemo(() => corpusSummary(payload), [payload]);
  const filterKey = encodeFilters(defs, state);
  const [limit, setLimit] = useState(PAGE);
  useEffect(() => { setLimit(PAGE); }, [filterKey]);

  const setFilters = (next: FilterState, push = false) =>
    go(withFilterQuery(window.location.search.replace(/^\?/, ""), encodeFilters(defs, next)), push);
  const hrefFor = (filterQuery: string) => `?${withFilterQuery(search.replace(/^\?/, ""), filterQuery)}`;
  const chosenPreset = activePreset(presets, defs, state);
  const chosenCountries = state.choices.country ?? [];
  const inView = countriesPresent(shown, payload.countries);
  const allCountries = countriesPresent(records, payload.countries);
  const page = shown.slice(0, limit);
  const filterLines = describeFilters(defs, state, today);

  const downloadCsv = () => {
    downloadBlob(new Blob([impactRecordsCsv(shown)], { type: "text/csv;charset=utf-8" }), csvFilename("impacts", "records", payload.as_of));
  };
  const downloadReadme = () => {
    const name = csvFilename("impacts", "records", payload.as_of);
    const text = readmeText({
      title: "Impact atlas: reviewed, publicly reported disruptions to energy and essential civilian services",
      csvName: name, scope: "impact atlas (all countries in the corpus)", buildDate: payload.as_of, downloaded: today,
      shown: shown.length, total: records.length, filters: filterLines,
      limitations: [
        ...payload.caveats,
        "Documented attempts with no reported service disruption are listed apart on the site and are not in this file.",
        ...(payload.research.limitations ?? []),
      ],
      columns: IMPACT_COLUMNS, fields: IMPACT_FIELDS,
    });
    downloadBlob(new Blob([text], { type: "text/plain;charset=utf-8" }), readmeFilename(name));
  };

  return (
    <>
      <section className="panel global-note atlas-intro" aria-label="What the impact atlas is">
        <p>{payload.scope_statement}</p>
        <ul className="atlas-caveats small">
          {payload.caveats.slice(0, 2).map((c) => <li key={c}>{c}</li>)}
        </ul>
        <p className="atlas-summary" data-testid="atlas-summary">
          <strong>{summary.records}</strong> published {summary.records === 1 ? "record" : "records"} in this corpus
          {" · "}<strong>{summary.countries}</strong> {summary.countries === 1 ? "country" : "countries"}
          {summary.first && summary.last && <>{" · "}records from {fmtDate(summary.first)} to {fmtDate(summary.last)}</>}
          {" · "}research last run {summary.researched ? fmtDate(summary.researched) : "not recorded"}
        </p>
        <p className="small dim atlas-bias" role="note">{BIAS_NOTE}</p>
        <details className="atlas-what small">
          <summary>What this is / is not</summary>
          <p><strong>It is</strong> a reviewed, expanding corpus: each record passed three independent reviews before it
            was published, and says what service was affected, what kind of cause is reported, who is publicly said to
            be responsible and how firmly, and how strong the public evidence is.</p>
          <p><strong>It is not:</strong></p>
          <ul>{payload.caveats.map((c) => <li key={c}>{c}</li>)}</ul>
          {payload.order && <p className="dim">{payload.order}</p>}
        </details>
        <details className="atlas-coverage small">
          <summary>Research coverage</summary>
          <p>Status: {payload.research.status ?? "not recorded"}
            {payload.research.window && <>; window {fmtDate(payload.research.window.start)} to {payload.research.window.end === "present" ? "the present" : fmtDate(payload.research.window.end)}</>}.</p>
          <h3 className="eyebrow">Source families searched</h3>
          <ul>
            {payload.research.source_families.map((f, i) => (
              <li key={i}>
                <strong>{f.family}</strong>{f.window ? ` (${f.window})` : ""}{f.status ? `: ${f.status}` : ""}.
                {f.method && <> {f.method}</>}
                {f.limitation && <span className="dim"> Limitation: {f.limitation}</span>}
              </li>
            ))}
            {payload.research.source_families.length === 0 && <li>None recorded yet.</li>}
          </ul>
          <h3 className="eyebrow">Regions worked</h3>
          <p>{(payload.research.regions_worked ?? []).join("; ") || "None recorded yet."} A region not listed was not searched:
            the absence of a record there says nothing about what happened there.</p>
          <h3 className="eyebrow">Known limitations</h3>
          <ul>
            {(payload.research.limitations ?? []).map((l) => <li key={l}>{l}</li>)}
            {(payload.research.limitations ?? []).length === 0 && <li>None recorded yet.</li>}
          </ul>
        </details>
      </section>

      {records.length === 0 ? (
        <section className="panel" aria-label="No published records">
          <h2 className="home-h2">No reviewed record is published yet</h2>
          <p>{payload.empty_reason ?? "The corpus has no published record yet. That is the state of this site's review, not a finding that nothing happened."}</p>
        </section>
      ) : (
        <>
          <nav className="atlas-presets" aria-label="Preset views">
            <span className="small dim">Preset views:</span>
            {presets.map((p) => {
              const on = chosenPreset === p.id;
              const href = hrefFor(on ? "" : presetQuery(p, defs));
              return (
                <a key={p.id} className={`atlas-preset${on ? " is-on" : ""}`} href={href} aria-current={on ? "true" : undefined}
                   title={p.meaning}
                   onClick={(e) => { if (!plainClick(e)) return; e.preventDefault(); go(href.slice(1), true); }}>
                  {/* The tick is decoration: "chosen" is said in words and by aria-current. */}
                  {on && <span aria-hidden="true">✓&nbsp;</span>}{p.label}{on && <span className="sr-only"> (chosen; activate to clear)</span>}
                </a>
              );
            })}
          </nav>
          {chosenPreset && <p className="small dim atlas-preset-meaning">{presets.find((p) => p.id === chosenPreset)?.meaning}</p>}

          <RecordFilterBar defs={defs} state={state} onChange={(next) => setFilters(next)} records={records} shown={shown.length}
                           today={today} noun="published records" notes={notes}>
            <button type="button" className="ghost" onClick={downloadCsv} disabled={shown.length === 0}>Download CSV</button>
            <button type="button" className="ghost" onClick={downloadReadme}>About this file</button>
          </RecordFilterBar>
          <p className="small dim atlas-bias" role="note">{BIAS_SHORT}</p>

          <AtlasCountries all={allCountries} inView={inView} chosen={chosenCountries} codes={presenceCodes(shown)}
                          onPick={(a3) => setFilters(toggleChoice(state, "country", a3), true)} />

          <section className="atlas-timeline" aria-label="Timeline of published records, newest first">
            <h2 className="home-h2">Timeline, newest first</h2>
            {shown.length === 0 ? (
              <div className="panel atlas-empty">
                <p>No published record matches these filters. That is a statement about this corpus, which is not a
                  census: it does not mean nothing of the kind happened.</p>
                <button type="button" className="ghost" onClick={() => setFilters({ choices: {}, dates: {} }, true)}>Clear filters</button>
              </div>
            ) : (
              <>
                {groupByMonth(page).map((y) => (
                  <section key={y.year} className="atlas-year" aria-label={y.year}>
                    <h3 className="atlas-year-head">{y.year}</h3>
                    {y.months.map((m) => (
                      <div key={m.ym} className="atlas-month">
                        <h4 className="atlas-month-head">{monthHeading(m.ym)}</h4>
                        <ol className="atlas-cards">
                          {m.records.map((r) => <li key={r.impact_id} className="atlas-card"><ImpactCard record={r} /></li>)}
                        </ol>
                      </div>
                    ))}
                  </section>
                ))}
                {shown.length > page.length && (
                  <p className="atlas-more">
                    <span className="small dim" role="status">Showing the newest {page.length} of {shown.length} records in this view. </span>
                    <button type="button" className="ghost" onClick={() => setLimit((n) => n + PAGE)}>
                      Show {Math.min(PAGE, shown.length - page.length)} more
                    </button>
                  </p>
                )}
              </>
            )}
          </section>
        </>
      )}

      <AttemptsSection label={payload.attempts_label ?? labelOf("record_kinds", "attempt_no_service_impact")}
                       note={payload.field_notes?.attempts ?? null} all={attempts} shown={shownAttempts} filtered={filterLines.length > 0} />
    </>
  );
}

/** The countries with a record in the view: the map's text alternative, and the country filter.
 *  Alphabetical, names only. No count stands beside a name. */
function AtlasCountries({ all, inView, chosen, codes, onPick }: {
  all: { a3: string; name: string }[]; inView: { a3: string; name: string }[]; chosen: string[]; codes: string[];
  onPick: (a3: string) => void;
}) {
  const [map, setMap] = useState(() => typeof window !== "undefined" && !!window.matchMedia && window.matchMedia("(min-width: 900px)").matches);
  const present = new Set(inView.map((c) => c.a3));
  return (
    <section className="panel atlas-countries" aria-labelledby="atlas-countries-head">
      <div className="home-section-head">
        <h2 id="atlas-countries-head" className="home-h2">Countries with a published record in this view</h2>
        <button type="button" className="ghost" aria-expanded={map} onClick={() => setMap((v) => !v)}>{map ? "Hide map" : "Show map"}</button>
      </div>
      <p className="small dim">Alphabetical. A country is listed, and marked on the map, when it has at least one published record in the
        current view. The mark is the same whether there is one record or many. A country that is not listed was not
        necessarily searched.</p>
      {map && (
        <PanelBoundary label="The presence map">
          <Suspense fallback={<div className="simple-map placeholder atlas-map">Loading map…</div>}>
            <PresenceMap codes={codes} selected={chosen.length === 1 ? chosen[0] : null} onPick={onPick} />
          </Suspense>
        </PanelBoundary>
      )}
      <ul className="atlas-country-list" id="atlas-country-list" aria-label="Countries with a published record in this view">
        {all.filter((c) => present.has(c.a3) || chosen.includes(c.a3)).map((c) => {
          const on = chosen.includes(c.a3);
          return (
            <li key={c.a3}>
              <button type="button" className={`atlas-country${on ? " is-on" : ""}`} aria-pressed={on} onClick={() => onPick(c.a3)}>
                {on && <span aria-hidden="true">✓&nbsp;</span>}{c.name}<span className="sr-only">{on ? ": remove from the country filter" : ": show only this country"}</span>
              </button>
            </li>
          );
        })}
      </ul>
      {inView.length === 0 && chosen.length === 0 && <p className="small dim">No country has a record in this view.</p>}
    </section>
  );
}

/** Attempts: their own collapsed section, labelled in the served words, never in the timeline. */
function AttemptsSection({ label, note, all, shown, filtered }: {
  label: string; note: string | null; all: ImpactRecord[]; shown: ImpactRecord[]; filtered: boolean;
}) {
  if (all.length === 0) return null;
  return (
    <details className="panel atlas-attempts">
      <summary>
        <span className="impact-attempt-label">{label}</span>{" "}
        <span className="small dim">Listed apart. Not in the timeline and not in any count.</span>
      </summary>
      {note && <p className="small dim">{note}</p>}
      <p className="small" role="status">
        {filtered ? `${shown.length} of ${all.length} documented ${all.length === 1 ? "attempt" : "attempts"} match the filters.`
          : `${all.length} documented ${all.length === 1 ? "attempt" : "attempts"}.`}
      </p>
      <ol className="atlas-cards">
        {shown.map((r) => <li key={r.impact_id} className="atlas-card"><ImpactCard record={r} /></li>)}
      </ol>
    </details>
  );
}
