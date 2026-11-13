import { useEffect, useMemo, useRef, useState } from "react";
import type maplibregl from "maplibre-gl";
import SimpleMap from "./SimpleMap";
import SystemSwitcher from "./SystemSwitcher";
import {
  CALENDAR_LABEL, CAMPAIGN_STATE_LABEL, LANGUAGE_LABEL, languageNames, ENVIRONMENT_LABEL, READINESS_LABEL, dirFor, RECOVERY_KIND_LABEL, RECOVERY_LABEL, RESEARCH_COMPLETENESS_LABEL,
  REVIEW_STATUS_LABEL, SECTOR_STATE_LABEL, LANE_EXECUTION_LABEL, LANE_STATE_LABEL, LANE_WINDOW_LABEL, labelFor, type CountrySystem, type SourceEntry, loadCountry, loadManifest, type CountryBundle, type CountryEvent, type Episode,
  type ManifestSystem, type ResearchLane, type ResearchPass, type SourceHealth,
} from "./manifest";
import { loadContext, rowForSystem, type EnergyContext } from "./context";
import { NationalFigures } from "./WorldContext";
import { navigate, navigateCompare } from "./router";
import { composeCountryFrame, countryFilename } from "./countryExport";
import { DISPUTED, NO_EVENTS, fillFor, scaleFor, type Scale } from "./countryScale";
import { downloadBlob, exportMapPng } from "../mapExport";
import { daysBetween, fmtDate } from "../data";
import { readerText } from "./readerText";

/** One country system (iteration 14).
 *
 *  WHAT A READER GETS. Reported major disruptions, aggregated to first-level regions; each
 *  sector's evidence state with its reason; sourced energy-system context; and the sources and
 *  gaps behind all of it. WHAT THEY DO NOT GET is a score: the header says "No index" and why,
 *  in the place the theatre shows its ESDI, so the absence is stated rather than left blank and
 *  never drawn as a zero.
 *
 *  Switching countries aborts the previous load, so a slow response for the country just left
 *  can never paint over the one just opened.
 */

type Tab = "events" | "sectors" | "context" | "research" | "sources" | "method";

function initialRegion(): string | null {
  return new URLSearchParams(window.location.search).get("r");
}

/** A month-precision date is shown as a month: printing "1 Apr" would invent a day. */
function fmtEventDate(e: CountryEvent): string {
  // Formatted from the string, never through the browser's Date parser (iteration 20).
  const d = e.date_precision === "month" ? fmtDate(e.date.slice(0, 7)) : fmtDate(e.date);
  return e.date_end ? `${d} – ${fmtDate(e.date_end)}` : d;
}

export default function CountryView({ id }: { id: string }) {
  const [entry, setEntry] = useState<ManifestSystem | null>(null);
  const [bundle, setBundle] = useState<CountryBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("events");
  const [region, setRegion] = useState<string | null>(initialRegion);
  const [exporting, setExporting] = useState(false);
  const [exportMsg, setExportMsg] = useState<string | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [ctx, setCtx] = useState<EnergyContext | null>(null);
  const [ctxFailed, setCtxFailed] = useState(false);

  // National context is a separate file: if it fails, the country's own record is untouched.
  useEffect(() => {
    let live = true;
    loadContext().then((c) => { if (live) setCtx(c); }).catch(() => { if (live) setCtxFailed(true); });
    return () => { live = false; };
  }, []);

  // Load this country, abandoning any load still in flight for the previous one.
  useEffect(() => {
    const ctl = new AbortController();
    setBundle(null);
    setEntry(null);
    setError(null);
    loadManifest()
      .then((m) => {
        const e = m.systems.find((s) => s.id === id && s.kind === "country");
        if (!e) throw new Error(`"${id}" is not a monitored country system.`);
        if (ctl.signal.aborted) return null;
        setEntry(e);
        return loadCountry(e, ctl.signal);
      })
      .then((b) => { if (b && !ctl.signal.aborted) setBundle(b); })
      .catch((err) => {
        if (ctl.signal.aborted) return;
        setError(err instanceof Error ? err.message : String(err));
      });
    return () => ctl.abort();
  }, [id]);

  useEffect(() => {
    document.title = `Energy Disruption Monitor — ${entry?.name ?? id.toUpperCase()}`;
  }, [entry, id]);

  // Region selection is shareable, like the theatre's.
  useEffect(() => {
    const q = new URLSearchParams({ sys: id });
    if (region) q.set("r", region);
    window.history.replaceState(null, "", `${window.location.pathname}?${q.toString()}`);
  }, [id, region]);

  const validRegion = useMemo(() => {
    if (!bundle || !region) return null;
    return bundle.regions.features.some((f) => f.properties?.code === region) ? region : null;
  }, [bundle, region]);

  const scale = useMemo<Scale>(() => scaleFor(
    (bundle?.regions.features ?? []).map((f) => Number(f.properties?.recorded_events ?? 0))), [bundle]);

  if (error) {
    return (
      <div className="global-page">
        <CountryHeader name={entry?.name ?? id.toUpperCase()} id={id} />
        <main className="global-main">
          <div className="panel" role="alert">
            <h2>This system could not be loaded</h2>
            <p>{error}</p>
            <p className="small">Other systems are unaffected. Choose another from the list above,
              or return to the <a href="?" onClick={(e) => { e.preventDefault(); navigate(null); }}>overview</a>.</p>
          </div>
        </main>
      </div>
    );
  }

  if (!bundle) {
    return (
      <div className="global-page">
        <CountryHeader name={entry?.name ?? id.toUpperCase()} id={id} />
        <main className="global-main"><p className="dim" role="status">Loading…</p></main>
      </div>
    );
  }

  const { system: sys, events } = bundle;
  const feature = validRegion ? bundle.regions.features.find((f) => f.properties?.code === validRegion) : null;
  const regionName = feature ? String(feature.properties?.name ?? validRegion) : null;
  // "not_placed": the system records everything for the country, or the unit is drawn for
  // reference only. An empty list there is "not applicable", never "none found".
  const regionStatus = feature
    ? (feature.properties?.status === "disputed_unassigned" ? "disputed_unassigned"
       : feature.properties?.records_placed === false ? "not_placed" : String(feature.properties?.status ?? "normal"))
    : null;
  // The reader's clock, like the theatre's freshness notice: the record is curated by hand and
  // does not change when the site rebuilds, so the warning must not depend on the build date.
  const reviewAge = sys.record_reviewed
    ? daysBetween(sys.record_reviewed, new Date().toISOString().slice(0, 10)) : null;
  const stale = reviewAge != null && reviewAge > sys.review_freshness_days;

  const runExport = async () => {
    const m = mapRef.current;
    if (!m) { setExportMsg("The map is not ready yet."); return; }
    setExporting(true);
    setExportMsg(null);
    try {
      const res = await exportMapPng({
        source: m, width: 1600, height: 900, pixelRatio: 1,
        compose: (c) => composeCountryFrame(c, sys, scale, ctx ? { row: rowForSystem(ctx, sys.system_id), ctx } : null),
      });
      downloadBlob(res.blob, countryFilename(sys));
      setExportMsg(`Exported ${res.width}×${res.height}.`);
    } catch (err) {
      setExportMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="global-page country-page">
      <CountryHeader name={sys.name} id={id} wholeCountry={sys.geography.precision_policy?.other === "country"}
                     attacksWhole={sys.geography.precision_policy?.kinetic === "country"}>
        {/* Opens the comparison workspace with this country chosen; the reader adds the others there. */}
        <button className="ghost" onClick={() => navigateCompare([id])} aria-label={`Compare ${sys.name} with other systems`}>Compare</button>
        <button className="ghost" onClick={runExport} disabled={exporting}>
          {exporting ? "Rendering…" : "Download PNG"}
        </button>
        <button className="ghost" onClick={() => window.print()}>Print / PDF</button>
      </CountryHeader>

      {/* On a phone the map comes before the full statements (iteration 20, §78). This line keeps
          the caveats in the first screen and leads to them. Hidden on wider screens. */}
      <p className="small phone-only phone-caveats">
        {sys.maturity === "research_preview" && <><span className="badge research-partial">Research preview</span>{" "}</>}
        {sys.campaign_state && sys.campaign_state.state !== "NO_ACTIVE_CAMPAIGN" && (
          <><span className="badge context-only-badge">Active-campaign safeguards apply</span>{" "}</>
        )}
        No index · {sys.event_summary.recorded_events === 0 ? "no qualifying records yet" : `${sys.event_summary.recorded_events} qualifying records`}.{" "}
        <a href="#notices">What this page can and cannot tell you</a>
      </p>

      {stale && (
        <div className="stale-note" role="status">
          This country's event record was last reviewed on {fmtDate(sys.record_reviewed)},
          more than {sys.review_freshness_days} days ago. Events since then are not included.
        </div>
      )}

      <section className="country-ribbon" id="notices" aria-label="Headline">
        <div className="no-index">
          <div className="no-index-value" aria-label="No index">No index</div>
          {/* Said once, plainly (iteration 20, §70). */}
          <div className="small no-index-plain">{sys.no_index_reason}</div>
        </div>
        <div>
          <div className="eyebrow">Evidence readiness</div>
          <div className={`badge readiness-${sys.evidence_readiness.toLowerCase()}`}>
            {READINESS_LABEL[sys.evidence_readiness]}
          </div>
        </div>
        <div>
          <div className="eyebrow">Recorded</div>
          {sys.event_summary.recorded_events === 0 ? (
            <div className="small">
              {/* Never "0 disruptions": nothing found in a search that has barely started is not a finding. */}
              <strong>No qualifying records in the current reviewed corpus.</strong> That describes this
              dataset, not {sys.name}: it does not mean nothing happened. Reporting environment:{" "}
              {labelFor(ENVIRONMENT_LABEL, sys.reporting_environment)}.
              {sys.campaign_state && sys.campaign_state.state !== "NO_ACTIVE_CAMPAIGN" && (
                <> Attacks are reported in the news; a record is published only once a reported event meets the
                  inclusion rule and has passed review, and none has yet.</>
              )}
              <HeldLine sys={sys} />
            </div>
          ) : (
            <div className="small">
              <strong>{sys.event_summary.recorded_events}</strong> qualifying events recorded
              {" "}in <strong>{sys.event_summary.episodes}</strong> episodes ·
              reporting environment: {labelFor(ENVIRONMENT_LABEL, sys.reporting_environment)}.
              {" "}{readerText(sys.event_summary.note)}
              <HeldLine sys={sys} />
            </div>
          )}
          <div className="small dim">{sys.reporting_environment_text}</div>
          <div className="small dim">
            {sys.record_reviewed ? `Event record reviewed ${fmtDate(sys.record_reviewed)}` : "No published record, so no review date"} · site rebuilt {fmtDate(sys.as_of)}
          </div>
          {(sys.recovery_coverage?.withheld_active_campaign ?? 0) > 0 && (
            <div className="small">
              Recovery status is withheld for {sys.recovery_coverage?.withheld_active_campaign} of {sys.event_summary.recorded_events} records
              while an attack campaign is active. See the Research coverage tab.
            </div>
          )}
        </div>
        <ResearchStatus sys={sys} />
      </section>

      <p className="comparability" role="note">{sys.comparability_statement}</p>

      {(sys.maturity === "research_preview" || sys.campaign_state || sys.geography.precision_policy) && (
        <section className="panel global-note system-notices" aria-label="How to read this country">
          {sys.maturity === "research_preview" && (
            <p className="small">
              <span className="badge research-partial">Research preview</span>{" "}
              {sys.name} was added recently and has had one first research pass. The systematic search is still
              incomplete, so the absence of a record is not evidence that no disruption occurred. Sources were
              searched for a limited time and some could not be read at all; the Research coverage tab says which.
            </p>
          )}
          {sys.campaign_state && sys.campaign_state.state !== "NO_ACTIVE_CAMPAIGN" && (
            <p className="small">
              <span className="badge context-only-badge">Active-campaign publication safeguards apply</span>{" "}
              <strong>{labelFor(CAMPAIGN_STATE_LABEL, sys.campaign_state.state)}.</strong>{" "}
              {sys.campaign_state.basis} Checked {fmtDate(sys.campaign_state.checked)}. While that holds, an attack
              is recorded as having happened, with its date, the kind of infrastructure and the effect reported at
              the time. Whether a facility has been repaired, restarted or is operating is not published.
            </p>
          )}
          {sys.geography.precision_policy && (
            <p className="small dim">How precisely events are placed: {readerText(sys.geography.precision_policy.reason)}</p>
          )}
          {/* A system under the campaign policy that still places attack records in a region (Saudi
              Arabia, onboarded in iteration 14): said plainly, by rule rather than by name (iteration 20, §79). */}
          {sys.campaign_state && sys.campaign_state.state !== "NO_ACTIVE_CAMPAIGN"
            && sys.geography.precision_policy?.kinetic !== "country" && sys.event_summary.recorded_events > 0 && (
            <p className="small legacy-convention">
              {sys.name} was onboarded before the newer rule for the Gulf countries, under which an attack record is
              published for the country as a whole, with no facility or region. Its older published records keep the
              earlier geography convention: an attack record here names its facility and its region. Whether that
              changes is an open decision, set out in the Why no score tab.
            </p>
          )}
        </section>
      )}

      <div className="country-body">
        <section className="country-map" aria-label="Map">
          <SimpleMap
            data={bundle.regions}
            bounds={sys.geography.view_bounds ?? sys.geography.bounds}
            idProp="code"
            selected={validRegion}
            fill={fillFor(scale) as maplibregl.ExpressionSpecification}
            onPick={(code) => { setRegion((cur) => (cur === code ? null : code)); setTab("events"); }}
            ariaLabel={`Map of ${sys.name} by ${sys.geography.unit_label}. Select one to list its events.`}
            attribution="Boundaries: Natural Earth (public domain), line of actual control. Events: cited public reporting."
            onMap={(m) => { mapRef.current = m; }}
          />
          <label className="small region-select">Show one {sys.geography.unit_label}{" "}
            <select aria-label={`Choose a ${sys.geography.unit_label}`} value={validRegion ?? ""}
              onChange={(e) => { setRegion(e.target.value || null); setTab("events"); }}>
              <option value="">All</option>
              {bundle.regions.features
                .map((f) => f.properties as { code?: string; name?: string } | null)
                .filter((p): p is { code: string; name: string } => !!p?.code && !!p?.name)
                .sort((a, b) => a.name.localeCompare(b.name))
                .map((p) => <option key={p.code} value={p.code}>{p.name}</option>)}
            </select>
          </label>
          <div className="map-legend-mini">
            <span className="eyebrow">Qualifying events recorded per {sys.geography.unit_label}</span>
            <span><i style={{ background: NO_EVENTS }} /> none recorded</span>
            {scale.labels.map((label, i) => (
              <span key={label}><i style={{ background: scale.colors[i] }} />{label}</span>
            ))}
            <span><i style={{ background: DISPUTED }} /> no record is placed here (disputed, or recorded for the country as a whole)</span>
            {sys.event_summary.recorded_events === 0 ? (
              <span className="small dim">No records yet, so nothing is shaded. An unshaded map is an empty
                dataset, not a quiet country.</span>
            ) : (
              <span className="small dim">This country's own range, not a shared scale.
                {" "}National or multi-region events listed but not drawn: {sys.event_summary.country_level}. What was reported and found — not a rate of disruption, and not comparable
                with any other country.</span>
            )}
            {sys.geography.precision_policy?.kinetic === "country" && sys.event_summary.recorded_events > 0 && (
              <span className="small dim">Attacks and sabotage are recorded for the country as a whole here and
                are never drawn in a {sys.geography.unit_label}.</span>
            )}
          </div>
        </section>

        <section className="country-side panel" aria-label="Details">
          <div className="tabs" role="group" aria-label="Detail views">
            {(["events", "sectors", "context", "research", "sources", "method"] as Tab[]).map((t) => (
              <button key={t} className="ghost" aria-pressed={tab === t} onClick={() => setTab(t)}>
                {TAB_LABEL[t]}
              </button>
            ))}
          </div>
          {tab === "events" && (
            <EventsPanel
              events={events} region={validRegion} regionName={regionName}
              regionStatus={regionStatus} onClear={() => setRegion(null)} bundle={bundle}
            />
          )}
          {tab === "sectors" && <SectorsPanel bundle={bundle} />}
          {tab === "context" && <ContextPanel bundle={bundle} ctx={ctx} ctxFailed={ctxFailed} />}
          {tab === "research" && <ResearchPanel bundle={bundle} />}
          {tab === "sources" && <SourcesPanel bundle={bundle} ctx={ctx} />}
          {tab === "method" && <MethodPanel bundle={bundle} />}
          {exportMsg && <p className="small" role="status">{exportMsg}</p>}
        </section>
      </div>
    </div>
  );
}

const TAB_LABEL: Record<Tab, string> = {
  events: "Reported events",
  sectors: "Sectors",
  context: "Energy context",
  research: "Research coverage",
  sources: "Sources & data quality",
  method: "Why no score",
};

/** Sources past their stale limit, on the reader's clock. Display only: never an analytic input. */
function staleSources(sources: SourceEntry[], today: string): SourceEntry[] {
  return sources.filter((x) => x.last_checked && x.stale_after_days != null
    && daysBetween(x.last_checked, today) > x.stale_after_days);
}

/** Two INDEPENDENT axes, shown side by side so neither reads as the other: are the sources
 *  current, and was the event search systematic? "Sources current, research incomplete" is a
 *  normal, non-contradictory state. */
function ResearchStatus({ sys }: { sys: CountrySystem }) {
  const today = new Date().toISOString().slice(0, 10);
  const rf = sys.research_freshness;
  const used = sys.sources.filter((x) => !x.role.startsWith("rejected"));
  const late = staleSources(used, today);
  const overdue = rf.next_due != null && rf.next_due < today;
  return (
    <div className="research-status" aria-label="Research status">
      {/* Two questions, two labelled answers (iteration 20, §68): how much of the planned search is
          done, and whether the registered sources were checked on schedule. */}
      <div className="eyebrow">Research coverage <span className="dim">· how much of the planned historical search is done</span></div>
      <div className="small">
        <span className={`badge research-${rf.completeness}`}>
          {sys.research_log.passes.length === 0 ? "No search has been run yet" : RESEARCH_COMPLETENESS_LABEL[rf.completeness]}
        </span>
        {/* Separate counts, not "3 of 9": a lane waiting on a publisher and a lane barely begun are not the same shortfall. */}
        {rf.lane_states && Object.keys(rf.lane_states).length > 0 && (
          <ul className="lane-state-list">
            {Object.entries(rf.lane_states).map(([k, n]) => (
              <li key={k}><span className="mono">{n}</span> {n === 1 ? "source group" : "source groups"}: {labelFor(LANE_STATE_LABEL, k).toLowerCase()}</li>
            ))}
          </ul>
        )}
        {rf.last_systematic_pass && rf.coverage_window && (
          <span className="dim"> · research period {fmtDate(rf.coverage_window[0])} – {fmtDate(rf.coverage_window[1])};
            last worked on {fmtDate(rf.last_systematic_pass)}; {rf.lanes_complete} of {rf.lanes_declared} source groups finished{overdue ? " (a new pass is due)" : ""}</span>
        )}
      </div>
      <div className="eyebrow">Source health <span className="dim">· whether the registered sources were checked on schedule</span></div>
      <div className="small">
        <span className={`source-freshness sources-${late.length ? "stale" : "current"}`}>
          {late.length
            ? `${late.length} of ${used.length} registered sources overdue for a check`
            : `All ${used.length} registered sources checked on schedule`}
        </span>
      </div>
      <div className="small dim">One does not imply the other: sources checked on schedule say nothing about how
        much of the search is done. A source group is one family of sources searched as a unit, for example one
        ministry's statements; see the Research coverage tab.</div>
    </div>
  );
}

function CountryHeader({ name, id, wholeCountry, attacksWhole, children }: { name: string; id: string; wholeCountry?: boolean; attacksWhole?: boolean; children?: React.ReactNode }) {
  return (
    <header className="global-head">
      <div>
        <h1 className="ribbon-title">{name}</h1>
        <div className="ribbon-sub">Energy Disruption Monitor · reported major disruptions{wholeCountry ? ", recorded for the country as a whole"
          : attacksWhole ? " by first-level region; attacks recorded for the country as a whole" : " by first-level region"}</div>
      </div>
      <div className="head-actions">
        {children}
        <SystemSwitcher current={id} />
      </div>
    </header>
  );
}

function EventsPanel({ events, region, regionName, regionStatus, onClear, bundle }: {
  events: CountryEvent[]; region: string | null; regionName: string | null;
  regionStatus: string | null; onClear: () => void; bundle: CountryBundle;
}) {
  const unit = bundle.system.geography.unit_label;
  const [year, setYear] = useState("");
  const [cls, setCls] = useState("");
  if (region && regionName) {
    const placed = events.filter((e) => e.region_code === region);
    // A multi-region event that names this region is listed here too, never counted here: the
    // region view must not say "none found" when the payload records one that reached it.
    const shared = events.filter((e) => e.geography_precision !== "admin1" && e.regions_affected.includes(region));
    return (
      <div className="events-panel">
        <div className="section-head">
          <h2>{regionName}</h2>
          <button className="ghost" onClick={onClear}>Show all</button>
        </div>
        {regionStatus === "disputed_unassigned" ? (
          <p className="small dim">Disputed and not assigned to any system's events: no events are
            recorded here by design. This is "not applicable", not "nothing happened".</p>
        ) : regionStatus === "not_placed" ? (
          <p className="small dim">No record is placed in {regionName}: records here are kept for the country as a
            whole, or this area is drawn for reference only. This is "not applicable", not "nothing happened".</p>
        ) : placed.length === 0 && shared.length === 0 ? (
          <p className="small dim">No qualifying events recorded for {regionName}. That means none
            were found in the sources monitored. It is not evidence that none occurred.</p>
        ) : null}
        <ol className="event-list">
          {[...placed].reverse().map((e) => <EventItem key={e.event_id} e={e} bundle={bundle} />)}
        </ol>
        {shared.length > 0 && (
          <>
            <h3 className="eyebrow">Multi-region events that included {regionName}</h3>
            <p className="small dim">Listed, not counted on the map for this {unit}.</p>
            <ol className="event-list">
              {[...shared].reverse().map((e) => <EventItem key={e.event_id} e={e} bundle={bundle} />)}
            </ol>
          </>
        )}
      </div>
    );
  }
  const grouped = new Set(bundle.episodes.filter((ep) => ep.records > 1).flatMap((ep) => ep.event_ids));
  const placed = events.filter((e) => e.geography_precision === "admin1" && !grouped.has(e.event_id));
  const countryLevel = events.filter((e) => e.geography_precision !== "admin1" && !grouped.has(e.event_id));
  // Newest first, episodes and single records interleaved by date.
  const rows: ({ kind: "event"; e: CountryEvent; date: string } | { kind: "episode"; ep: Episode; date: string })[] = [
    ...placed.map((e) => ({ kind: "event" as const, e, date: e.date })),
    ...bundle.episodes.filter((ep) => ep.records > 1).map((ep) => ({ kind: "episode" as const, ep, date: ep.first_date })),
  ].sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
  const eventById = new Map(events.map((e) => [e.event_id, e]));
  return (
    <div className="events-panel">
      <h2>All reported events</h2>
      <div className="event-filters small">
        <label>Year{" "}
          <select aria-label="Filter events by year" value={year} onChange={(e) => setYear(e.target.value)}>
            <option value="">All</option>
            {[...new Set(events.map((e) => e.date.slice(0, 4)))].sort().reverse().map((y) => <option key={y} value={y}>{y}</option>)}
          </select>
        </label>{" "}
        <label>Type{" "}
          <select aria-label="Filter events by infrastructure type" value={cls} onChange={(e) => setCls(e.target.value)}>
            <option value="">All</option>
            {[...new Set(events.map((e) => e.asset_class))].sort().map((c) => (
              <option key={c} value={c}>{labelFor(bundle.system.taxonomy.asset_classes, c)}</option>
            ))}
          </select>
        </label>
      </div>
      <p className="small dim">A record is a publicly reported event that meets the inclusion rule (Why no score tab): it is what was reported and found, not everything that happened.</p>
      {(year || cls) && (
        <ol className="event-list">
          {[...events].filter((e) => (!year || e.date.startsWith(year)) && (!cls || e.asset_class === cls))
            .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0))
            .map((e) => <EventItem key={e.event_id} e={e} bundle={bundle} />)}
        </ol>
      )}
      {!year && !cls && (<>
      {/* An empty page says what was searched and what is incomplete; the episode definition belongs
          beside episodes (iteration 20, §75). */}
      <p className="small dim">{events.length === 0
        ? "No qualifying records in the current reviewed corpus. The Research coverage tab says what was searched, in which languages, and what could not be read."
        : `${events.length} records in ${bundle.episodes.length} episodes. An episode is one named hazard or one event a source explicitly identifies as common; a record linked to no other is an episode of one.`}</p>
      <ol className="event-list">
        {rows.map((row) => row.kind === "event"
          ? <EventItem key={row.e.event_id} e={row.e} bundle={bundle} />
          : (
            <li key={row.ep.episode_id} className="episode-group">
              <div className="episode-head">
                <span className="eyebrow">Episode · {row.ep.records} records</span>
                <strong>{row.ep.name}</strong>
                <span className="small dim">{labelFor(bundle.system.episode_bases, row.ep.basis)}</span>
              </div>
              <ol className="event-list">
                {row.ep.event_ids.map((id) => eventById.get(id)).filter((e): e is CountryEvent => !!e)
                  .map((e) => <EventItem key={e.event_id} e={e} bundle={bundle} inEpisode />)}
              </ol>
            </li>
          ))}
      </ol>

      {countryLevel.length > 0 && (
        <>
          <h3 className="eyebrow">Not placed in one {unit}</h3>
          <p className="small dim">National, offshore or multi-region events. They are listed, never
            counted against any single region.</p>
          <ol className="event-list">
            {[...countryLevel].reverse().map((e) => <EventItem key={e.event_id} e={e} bundle={bundle} />)}
          </ol>
        </>
      )}
      </>)}
    </div>
  );
}

/** How many candidate records the latest research pass found and did not publish. A count and
 *  nothing else: what they are stays in review. Without it, a country whose every candidate was
 *  held reads exactly like a country nobody looked at (iteration 19: two systems ended their first pass that way). */
function HeldLine({ sys }: { sys: CountryBundle["system"] }) {
  const passes = sys.research_log.passes.filter((p) => p.kind === "systematic");
  const last = passes[passes.length - 1];
  // Under the campaign policy the page gives no count of what is held: beside one published attack
  // record a count is a hint of scale (iteration 20). It says only that review continues.
  if (last?.under_review !== undefined) {
    return last.under_review
      ? <span className="held-line"> Additional candidates remain under review and are not shown. See the Research coverage tab.</span>
      : null;
  }
  const o = last?.outcome;
  if (!o || !o.candidates) return null;
  const held = o.held ?? 0;
  return (
    <span className="held-line">
      {" "}The latest research pass looked at {o.candidates} candidate records for this country;{" "}
      {held > 0 ? `${held} of them are not shown because a reviewer, the publication rules or an undecided rule question holds them back` : "none is held back"},
      and the rest were rejected, duplicates, out of scope or published. See the Research coverage tab.
    </span>
  );
}

function recoveryText(e: CountryEvent): string {
  const r = e.recovery;
  if (r.research_status === "EVIDENCE_FOUND" && r.kind) return labelFor(RECOVERY_KIND_LABEL, r.kind);
  return labelFor(RECOVERY_LABEL, r.research_status);
}

/** A first-level unit's name for a code, from the system's own regions; the code if unknown. */
function unitName(bundle: CountryBundle, code: string): string {
  const f = bundle.regions.features.find((x) => (x.properties as { code?: string } | null)?.code === code);
  return ((f?.properties as { name?: string } | null)?.name) ?? code;
}

/** `inEpisode`: drawn inside its episode's group, which already names the episode. */
function EventItem({ e, bundle, inEpisode = false }: { e: CountryEvent; bundle: CountryBundle; inEpisode?: boolean }) {
  const tax = bundle.system.taxonomy;
  const recClass = e.recovery.kind ?? e.recovery.research_status;
  const ep = bundle.episodes.find((x) => x.episode_id === e.episode_id);
  return (
    <li className="event-item">
      <div className="event-head">
        <span className="mono small">{fmtEventDate(e)}</span>
        <span className="small dim">{labelFor(tax.asset_classes, e.asset_class)} · {labelFor(tax.causes, e.cause)}</span>
      </div>
      <div className="event-title">{e.facility_name ?? e.region_name ?? bundle.system.name}</div>
      <p className="small">{e.summary}</p>
      {e.source_date_text && e.date_calendar && e.date_calendar !== "gregorian" && (
        <p className="small dim">
          Date in the source: <bdi lang={e.date_calendar === "solar_hijri" ? "fa" : "ar"}>{e.source_date_text}</bdi>{" "}
          ({labelFor(CALENDAR_LABEL, e.date_calendar)}). {e.conversion_basis}
        </p>
      )}
      {e.effect && <p className="small"><span className="dim">Reported effect: </span>{e.effect}</p>}
      {e.regions_affected.length > 0 && (
        <p className="small dim">Regions affected: {e.regions_affected.map((c) => unitName(bundle, c)).join(", ")}</p>
      )}
      {ep && ep.records > 1 && !inEpisode && (
        <p className="small dim episode-note">Part of an episode: {ep.name} ({ep.records} records)</p>
      )}
      {(!ep || ep.records <= 1) && (
        <p className="small dim episode-note">Standalone: not linked to any other record (an episode of one).</p>
      )}
      <p className="small">
        <span className={`rec rec-${recClass.toLowerCase()}`}>{recoveryText(e)}</span>
        {e.recovery.date && <span className="dim"> ({fmtDate(e.recovery.date)})</span>}
        {e.recovery.evidence && <span className="dim"> — {e.recovery.evidence}</span>}
      </p>
      {e.publication && <p className="small dim withheld-note">{e.publication.note}</p>}
      <p className="small dim review-note">
        <span className={`review-${e.review.review_status}`}>{labelFor(REVIEW_STATUS_LABEL, e.review.review_status)}</span>
        {e.review.review_status !== "legacy_single_review" && e.review.disposition === "corrected" && " · corrected on review"}
      </p>
      <p className="small sources">
        {e.sources.map((s, i) => (
          <a key={i} href={s.url} target="_blank" rel="noreferrer">{s.publisher ?? new URL(s.url).hostname}</a>
        ))}
        {/* A non-English source keeps its own headline, in its own script and direction, with a gloss. */}
        {e.sources.filter((s) => s.title_original).map((s, i) => (
          <span key={`t${i}`} className="source-title">
            <bdi lang={s.language} dir={dirFor(s.language)}>{s.title_original}</bdi>
            {s.title_en && <span className="dim"> ({s.title_en})</span>}
            <span className="dim"> · {s.publisher}</span>
          </span>
        ))}
        <span className="dim">{e.review.source_access === "not recorded by the research lane"
          ? (e.review.review_status === "legacy_single_review"
            ? "· whether these were read was not recorded"
            : "· the researcher's reading was not recorded; the independent review opened them") : ""}</span>
      </p>
    </li>
  );
}

function SectorsPanel({ bundle }: { bundle: CountryBundle }) {
  return (
    <div>
      <h2>Sectors</h2>
      <p className="small dim">Every sector has an explicit published state. "Tracked, not scored"
        means events are listed and context is shown, but no value is computed. The
        researchers' assessment is what the evidence <em>could</em> support after the decisions in the
        methodology; it is not a published state and no value exists behind it.</p>
      <table className="sector-table">
        <thead><tr><th>Sector</th><th>Published state</th><th>Researchers' assessment (not published)</th></tr></thead>
        <tbody>
          {bundle.system.sectors.map((s) => (
            <tr key={s.sector}>
              <td>{s.label}</td>
              <td><span className={`badge state-${s.state.toLowerCase()}`}>{SECTOR_STATE_LABEL[s.state]}</span></td>
              <td className="small">could reach: {s.assessed_readiness.replace(/_/g, " ").toLowerCase()}<div className="dim">{readerText(s.reason)}</div></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ContextPanel({ bundle, ctx, ctxFailed }: { bundle: CountryBundle; ctx: EnergyContext | null; ctxFailed: boolean }) {
  const p = bundle.system.profile;
  const row = ctx ? rowForSystem(ctx, bundle.system.system_id) : null;
  return (
    <div>
      <h2>National energy picture</h2>
      {ctxFailed && <p className="small warn-text" role="alert">Global energy context unavailable. The rest of this page is not affected.</p>}
      {row && ctx && (
        <div className="national-block">
          <NationalFigures row={row} ctx={ctx} />
          {Object.keys(row.newer).length > 0 && (
            <p className="small dim">Newer than the comparison year: {Object.entries(row.newer).filter(([m]) => m === "oil_production" || m === "crude_production").map(([m, n]) => `${ctx.metrics[m].label} ${n.value.toLocaleString("en-GB")} ${ctx.metrics[m].unit}, ${n.year}`).join("; ")}.</p>
          )}
          <p className="small dim">{ctx.comparison_year} figures. <a href={ctx.source.url} target="_blank" rel="noreferrer">{ctx.source.name}</a>, release
            of {fmtDate(ctx.source.release)}. The same source and year as the world map, so these are comparable across countries. They describe the
            size of the energy system and never weight, rank or qualify an event.</p>
        </div>
      )}
      <h2>Energy-system context</h2>
      <p className="small dim">Sourced statistics for reading the events, never a scoring input and
        never a ranking of infrastructure. Bases and vintages differ by row: read the basis before
        putting two rows together.</p>
      {p.significance && (
        <ul className="small">{p.significance.map((s, i) => <li key={i}>{s}</li>)}</ul>
      )}
      <table className="sector-table">
        <tbody>
          {p.metrics.map((m) => (
            <tr key={m.metric}>
              <td>{m.metric.replace(/_/g, " ")}</td>
              <td className="mono">{typeof m.value === "number" ? m.value.toLocaleString("en-GB") : m.value ?? "—"}</td>
              <td className="small">{m.unit}{m.year ? ` · ${m.year}` : ""}
                <div className="dim">{m.url ? <a href={m.url} target="_blank" rel="noreferrer">{m.source}</a> : m.source}</div>
                {m.basis && <div className="dim">Basis: {m.basis}</div>}
                {m.note && <div className="dim">{readerText(m.note)}</div>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {p.as_of_note && <p className="small dim">{readerText(p.as_of_note)}</p>}
    </div>
  );
}

function laneDisplay(l: ResearchLane): string {
  const q = l.queries_declared != null ? `${l.queries_run ?? 0} of ${l.queries_declared} declared queries` : null;
  const items = l.items_enumerated != null ? `${l.items_enumerated}${l.items_in_universe != null ? ` of ${l.items_in_universe}` : ""} items listed or read` : null;
  return [q, items].filter(Boolean).join("; ");
}

/** Known gaps generated from lane states, so this cannot drift from the log. */
function ResearchPanel({ bundle }: { bundle: CountryBundle }) {
  const s = bundle.system;
  const rf = s.research_freshness;
  const passes = s.research_log.passes.filter((p) => p.kind === "systematic");
  const newest: ResearchPass | undefined = passes[passes.length - 1];
  const lanes = newest?.lanes ?? [];
  const v2 = lanes.filter((l) => l.execution);
  const rc = s.recovery_coverage;
  const cq = s.citation_quality;
  const languages = [...new Set(v2.flatMap((l) => l.languages_required ?? []))].sort();
  const gaps = v2.filter((l) => l.limitation);
  return (
    <div>
      <h2>Research coverage</h2>
      <p className="small">Two questions kept apart for every lane: how far the analyst got, and what the publisher has made
        available. A fully executed procedure is not complete knowledge: events the sources never reported are still missing.</p>
      <p className="small dim">Events can date back to 2022, but systematic research for this country began
        {rf.first_systematic_pass ? ` on ${fmtDate(rf.first_systematic_pass)}` : " later"}. Older records were found afterwards, not monitored as they happened.</p>
      <p className="small">Reporting environment: <strong>{labelFor(ENVIRONMENT_LABEL, s.reporting_environment)}</strong>. {s.reporting_environment_text}</p>
      {s.source_families && <p className="small">Source families cited: {Object.values(s.source_families.labels).join(", ") || "none"}. <span className="dim">{s.source_families.note}</span></p>}
      {languages.length > 0 && <p className="small">Languages the research plan requires: {languageNames(languages)}.
        {" "}{(() => {
          const short = v2.filter((l) => (l.languages_required ?? []).some((x) => !(l.languages_executed ?? []).includes(x))).map((l) => l.lane);
          return short.length ? `${short.join(", ")} did not run in every required language.` : "Every source group ran in every language it requires.";
        })()}</p>}
      <table className="sector-table lane-table">
        <thead><tr><th>Lane</th><th>What the analyst did</th><th>What the source allows</th><th>Furthest date reached</th></tr></thead>
        <tbody>
          {v2.map((l) => (
            <tr key={l.lane}>
              <td className="small"><span className="mono">{l.lane}</span><div className="dim">{l.source_family}</div></td>
              <td className="small">{labelFor(LANE_EXECUTION_LABEL, l.execution ?? "")}<div className="dim">{laneDisplay(l)}</div></td>
              <td className="small">{labelFor(LANE_WINDOW_LABEL, l.source_window ?? "")}</td>
              <td className="small">{l.covered_through ? fmtDate(l.covered_through) : "not reached"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h3 className="eyebrow">Known gaps, from the source groups above</h3>
      <ul className="small">{gaps.map((l) => <li key={l.lane}><span className="mono">{l.lane}</span>: {readerText(l.limitation)}</li>)}</ul>
      {s.research_gaps.length > 0 && (<>
        <h3 className="eyebrow">Other gaps</h3>
        <ul className="small">{s.research_gaps.map((g, i) => <li key={i}>{g}</li>)}</ul>
      </>)}
      {v2.some((l) => l.finding) && (<>
        <h3 className="eyebrow">Findings about the sources</h3>
        <ul className="small">{v2.filter((l) => l.finding).map((l) => <li key={l.lane}><span className="mono">{l.lane}</span>: {readerText(l.finding)}</li>)}</ul>
      </>)}
      {rc && (<>
        <h3 className="eyebrow">Recovery research</h3>
        <ul className="small recovery-coverage">
          <li>Observed report of recovery: {rc.observed}</li>
          <li>Sourced estimate only: {rc.estimate}</li>
          {rc.other_statement > 0 && <li>Statement that supply was unaffected or nothing was lost: {rc.other_statement}</li>}
          <li>Researched, no public evidence: {rc.researched_no_public_evidence}</li>
          <li>Not yet researched: {rc.not_researched}</li>
          {rc.withheld_active_campaign > 0 && <li>Status withheld while an attack campaign is active: {rc.withheld_active_campaign}</li>}
        </ul>
        {Object.keys(rc.unresearched_by_class).length > 0 && (
          <p className="small dim">Still to research: {Object.entries(rc.unresearched_by_class).map(([k, n]) => `${n} ${labelFor(s.taxonomy.asset_classes, k).toLowerCase()}`).join(", ")}.</p>
        )}
        <p className="small dim">{rc.policy}</p>
      </>)}
      {cq && (<>
        <h3 className="eyebrow">Citations behind the published events</h3>
        <ul className="small citation-quality">
          <li>{cq.citations} citations; {cq.with_publication_date} carry a publication date stated by the source.</li>
          <li>Languages: {Object.entries(cq.languages).map(([k, n]) => `${LANGUAGE_LABEL[k] ?? k} ${n}`).join(", ")}.</li>
          <li>Event dates: {Object.entries(cq.event_date_precision).map(([k, n]) => `${n} to the ${k}`).join(", ")}.</li>
          {cq.link_check && <li>Automated link check, {fmtDate(cq.link_check_date ?? "")}: {cq.link_check.reachable} reachable, {cq.link_check.redirected} redirected, {cq.link_check.blocked} refused the check, {cq.link_check.dead} gone, {cq.link_check.error} failed to load.</li>}
        </ul>
        {cq.link_check_note && <p className="small dim">{cq.link_check_note}</p>}
      </>)}
      <details className="small"><summary>Earlier passes, as they were logged</summary>
        <table className="sector-table research-log">
          <thead><tr><th>Pass</th><th>Status then</th><th>Outcome</th></tr></thead>
          <tbody>
            {s.research_log.passes.map((p) => (
              <tr key={`${p.date}-${p.by}`}>
                <td className="small">{fmtDate(p.date)}<div className="dim">{readerText(p.by)}</div></td>
                <td className="small">{p.kind === "targeted" ? "targeted search" : p.status}{p.status_reason && <div className="dim">{readerText(p.status_reason)}</div>}</td>
                <td className="small">{Object.entries(p.outcome).map(([k, n]) => `${k.replace(/_/g, " ")} ${n}`).join(" · ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}

function SourcesPanel({ bundle, ctx }: { bundle: CountryBundle; ctx: EnergyContext | null }) {
  const s = bundle.system;
  const rec = s.event_summary.recovery_research;
  const kinds = Object.entries(s.event_summary.recovery_kinds).filter(([, n]) => n > 0);
  const unrecorded = bundle.events.filter((e) => e.review.source_access === "not recorded by the research lane").length;
  const today = new Date().toISOString().slice(0, 10);
  return (
    <div>
      <h2>Sources &amp; data quality</h2>
      <p className="small">{s.reporting_note}</p>
      <table className="sector-table source-table">
        <thead><tr><th>Source</th><th>Use</th><th>Licence</th><th>Last checked</th></tr></thead>
        <tbody>
          {s.sources.map((x) => {
            const late = staleSources([x], today).length > 0;
            const pol = x.stale_policy ? s.stale_policies[x.stale_policy] : null;
            return (
              <tr key={x.name}>
                <td>{x.name}</td>
                <td className="small">{x.role}</td>
                <td className="small dim">{x.licence}</td>
                <td className="small">
                  {x.last_checked ? fmtDate(x.last_checked) : "never"}
                  {x.publication_cadence && <div className="dim">Publishes: {x.publication_cadence}</div>}
                  {pol && <div className="dim">Re-check within {pol.days} days ({x.stale_policy?.replace(/_/g, " ")}: {pol.rationale})</div>}
                  {late && <div className="stale-flag">Past its {x.stale_after_days}-day limit: re-check before relying on it</div>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="small dim">Re-check limits are display policy: they never decide whether an event
        is included and never enter a number.</p>
      {s.source_health && <SourceHealthBlock h={s.source_health} />}
      <SourceBrowser bundle={bundle} ctx={ctx} />
      <p className="small research-coverage">
        <strong>{s.research_log.passes.length === 0 ? "No search has been run yet" : RESEARCH_COMPLETENESS_LABEL[s.research_freshness.completeness]}.</strong>{" "}
        {s.research_freshness.last_systematic_pass
          ? `Last systematic pass ${fmtDate(s.research_freshness.last_systematic_pass)}, over a declared window of ${fmtDate(s.research_freshness.coverage_window?.[0] ?? null)} – ${fmtDate(s.research_freshness.coverage_window?.[1] ?? null)}. Source group by source group under Research coverage.`
          : s.research_log.passes.length === 0 ? "No research pass has been logged for this country."
            : "Every pass so far was targeted at named gaps and leads."}
      </p>
      <p className="small dim">{readerText(s.research_freshness.note)}</p>
      <h3 className="eyebrow">Recovery evidence across the recorded events</h3>
      <p className="small dim recovery-meaning">"Recovery" on these pages means a cited public report
        that a facility or service came back, fully or partly. Nothing is modelled: with no such report
        the event says so, and an estimate is labelled an estimate. For an attack campaign still under
        way, facility status is deliberately not published at all.</p>
      <ul className="small">
        {Object.entries(rec).map(([k, n]) => <li key={k}>{labelFor(RECOVERY_LABEL, k)}: {n}</li>)}
      </ul>
      {kinds.length > 0 && (
        <>
          <div className="small dim">Of the evidence found, by kind — these are different claims:</div>
          <ul className="small">{kinds.map(([k, n]) => <li key={k}>{labelFor(RECOVERY_KIND_LABEL, k)}: {n}</li>)}</ul>
        </>
      )}
      <h3 className="eyebrow">Review</h3>
      <p className="small review-summary">{(s.review_summary.blind_reviewed ?? 0) + s.review_summary.dual_reviewed} of {bundle.events.length} events
        independently reviewed ({s.review_summary.blind_reviewed ?? 0} blind by three reviewers,{" "}
        {s.review_summary.dual_reviewed} by one); {s.review_summary.legacy_single_review} published before independent
        review was required.</p>
      <p className="small dim">{readerText(s.review_summary.note)}
        {unrecorded > 0 && ` For ${unrecorded} of ${bundle.events.length} events the researchers did not record whether they read the cited sources.`}</p>
    </div>
  );
}

const ROLE_TEXT: Record<string, string> = {
  official: "official body", government: "government", regulator: "regulator", operator: "operator",
  dataset: "dataset", media: "news media", industry: "industry press",
};

/** What the citations behind this country's events are, inside this country only. */
function SourceHealthBlock({ h }: { h: SourceHealth }) {
  const roles = Object.entries(h.by_role).map(([k, n]) => `${labelFor(ROLE_TEXT, k)} ${n}`).join(" · ");
  const langs = Object.entries(h.by_language).map(([k, n]) => `${LANGUAGE_LABEL[k] ?? k} ${n}`).join(" · ");
  return (
    <div className="source-health">
      <h3 className="eyebrow">Source health: the citations behind the events</h3>
      <ul className="small">
        <li>{h.citations} citations from {h.publishers} publishers, across {h.events} events.</li>
        <li>By role: {roles}.</li>
        <li>{h.events_with_first_party_source} of {h.events} events cite at least one first-party
          source (the operator, a regulator, a government body or a dataset; Wikipedia does not count); {h.single_source_events} rest
          on a single citation.</li>
        {h.single_origin_events !== undefined && (
          <li>Counted by origin rather than by citation: {h.single_origin_events} events rest on a single originating
            statement{h.discovery_only_events ? <>, and {h.discovery_only_events} only on Wikipedia or a content aggregator</> : null}.{" "}
            <span className="dim">{h.origin_rule}</span></li>
        )}
        <li>Opened by the researcher: {h.opened.opened} recorded opened, {h.opened.not_opened} recorded
          not opened, {h.opened.not_recorded} not recorded.</li>
        <li>{h.dated} of {h.citations} citations carry their own publication date. Languages: {langs}.</li>
      </ul>
      <p className="small dim">{h.note}</p>
    </div>
  );
}

/** Browse the citations by publisher. Display only: filters what is listed, never what is counted. */
const SOURCE_KIND_LABEL: Record<string, string> = {
  incident: "Incident citations",
  recovery: "Recovery evidence",
  context: "Energy-system context",
  global: "National energy context (world map)",
  registry: "Search registry (what the source groups searched)",
};

function SourceBrowser({ bundle, ctx }: { bundle: CountryBundle; ctx: EnergyContext | null }) {
  const events = bundle.events;
  const [kind, setKind] = useState("incident");
  const [role, setRole] = useState("all");
  const [open, setOpen] = useState<string | null>(null);
  const otherRows = useMemo(() => {
    if (kind === "recovery") {
      const by = new Map<string, { label: string; url: string | null; note: string }>();
      for (const e of events) {
        if (e.recovery.url) by.set(e.recovery.url, { label: new URL(e.recovery.url).hostname, url: e.recovery.url, note: fmtEventDate(e) + ": " + labelFor(RECOVERY_KIND_LABEL, e.recovery.kind ?? e.recovery.research_status) });
      }
      return [...by.values()].sort((a, b) => a.label.localeCompare(b.label));
    }
    if (kind === "context") {
      return bundle.system.profile.metrics.filter((m) => m.source).map((m) => ({ label: String(m.source), url: m.url ?? null, note: m.metric.replace(/_/g, " ") }))
        .sort((a, b) => a.label.localeCompare(b.label));
    }
    if (kind === "global") {
      return ctx ? [{ label: ctx.source.name, url: ctx.source.url, note: `Release of ${fmtDate(ctx.source.release)}; national aggregates; ${ctx.source.licence}` }] : [];
    }
    if (kind === "registry") {
      return bundle.system.sources.map((x) => ({ label: x.name, url: null, note: x.role })).sort((a, b) => a.label.localeCompare(b.label));
    }
    return [];
  }, [kind, events, bundle, ctx]);
  const rows = useMemo(() => {
    const by = new Map<string, { publisher: string; roles: Set<string>; langs: Set<string>;
                                 events: CountryEvent[]; urls: Set<string> }>();
    for (const e of events) {
      for (const src of e.sources) {
        const key = src.publisher || "(publisher not recorded)";
        const r = by.get(key) ?? { publisher: key, roles: new Set(), langs: new Set(), events: [], urls: new Set() };
        if (src.source_role) r.roles.add(src.source_role);
        if (src.language) r.langs.add(src.language);
        if (!r.events.includes(e)) r.events.push(e);
        r.urls.add(src.url);
        by.set(key, r);
      }
    }
    // Alphabetical, never by count: a list ordered by how often a publisher is cited would read
    // as a ranking of sources.
    return [...by.values()].sort((a, b) => a.publisher.localeCompare(b.publisher));
  }, [events]);
  const allRoles = [...new Set(rows.flatMap((r) => [...r.roles]))].sort();
  const shown = role === "all" ? rows : rows.filter((r) => r.roles.has(role));
  return (
    <div className="source-browser">
      <h3 className="eyebrow">Source browser</h3>
      <label className="small">Show{" "}
        <select value={kind} onChange={(ev) => { setKind(ev.target.value); setOpen(null); }} aria-label="Source type">
          {Object.entries(SOURCE_KIND_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </label>{" "}
      {kind !== "incident" ? (
        <ul className="small lane-list source-other">
          {otherRows.map((r, i) => <li key={i}>{r.url ? <a href={r.url} target="_blank" rel="noopener noreferrer">{r.label}</a> : r.label} <span className="dim">{r.note}</span></li>)}
          {otherRows.length === 0 && <li className="dim">Nothing of this type is cited for this country.</li>}
        </ul>
      ) : (<>
      <label className="small">Role{" "}
        <select value={role} onChange={(ev) => { setRole(ev.target.value); setOpen(null); }} aria-label="Filter sources by role">
          <option value="all">all roles</option>
          {allRoles.map((r) => <option key={r} value={r}>{labelFor(ROLE_TEXT, r)}</option>)}
        </select>
      </label>
      <span className="small dim"> {shown.length} of {rows.length} publishers, alphabetical</span>
      <table className="sector-table source-browser-table">
        <thead><tr><th>Publisher</th><th>Role</th><th>Events citing it</th></tr></thead>
        <tbody>
          {shown.map((r) => (
            <tr key={r.publisher}>
              <td className="small">{r.publisher}
                {r.langs.size > 0 && <span className="dim"> ({languageNames(r.langs)})</span>}</td>
              <td className="small dim">{[...r.roles].map((x) => labelFor(ROLE_TEXT, x)).join(", ")}</td>
              <td className="small">
                <button type="button" className="linklike" aria-expanded={open === r.publisher}
                  aria-label={`${r.events.length} event${r.events.length === 1 ? "" : "s"} citing ${r.publisher}`}
                  onClick={() => setOpen(open === r.publisher ? null : r.publisher)}>
                  {r.events.length} event{r.events.length === 1 ? "" : "s"}
                </button>
                {open === r.publisher && (
                  <ul className="dim lane-list">
                    {r.events.map((e) => <li key={e.event_id}>{fmtEventDate(e)}: {e.summary}</li>)}
                    {[...r.urls].map((u) => <li key={u}><a href={u} target="_blank" rel="noopener noreferrer">{u}</a></li>)}
                  </ul>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </>)}
    </div>
  );
}

function MethodPanel({ bundle }: { bundle: CountryBundle }) {
  const s = bundle.system;
  const unmet = s.onboarding_gate.filter((g) => g.status !== "met").length;
  return (
    <div>
      <h2>Why no score</h2>
      <p className="small">The disruption score was built for one strike campaign against one energy system; its
            weights and recovery model do not transfer to this country's system, so applying it would mislead.
            No score is shown, and that is not a score of zero.</p>
      <p className="small dim">{s.no_index_reason}</p>
      <p className="small">Reporting environment — {labelFor(ENVIRONMENT_LABEL, s.reporting_environment)}:
        {" "}{s.reporting_environment_text}</p>
      <h3 className="eyebrow">Publication checklist</h3>
      <p className="small dim">
        {unmet === 0
          ? "Every item of the publication checklist is met."
          : s.maturity === "research_preview"
            ? `Shown as a research preview (added recently, one first research pass): ${unmet} of ${s.onboarding_gate.length} items of the publication checklist are not met or only partly met.`
            : `${unmet} of ${s.onboarding_gate.length} items of the publication checklist are not met or only partly met; each says why below.`}
      </p>
      <table className="sector-table">
        <tbody>
          {s.onboarding_gate.map((g) => (
            <tr key={g.item}>
              <td className="small">{g.item}. {g.label}</td>
              <td><span className={`badge gate-${g.status}`}>{g.status}</span></td>
              <td className="small dim">{readerText(g.note)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h3 className="eyebrow">Inclusion threshold (version {s.inclusion_threshold.version})</h3>
      <p className="small">{s.inclusion_threshold.rule}</p>
      <ol className="small">
        {Object.entries(s.inclusion_threshold.clauses).map(([k, v]) => <li key={k} value={Number(k)}>{v}</li>)}
      </ol>
      <h3 className="eyebrow">Geography</h3>
      <p className="small">{readerText(s.geography.note)}</p>
      {s.geography.rulings.length > 0 && (
        <ul className="small">{s.geography.rulings.map((r) => <li key={r.code}><span className="mono">{r.code}</span>: {readerText(r.note)}</li>)}</ul>
      )}
      {s.campaign_state && s.campaign_state.state !== "NO_ACTIVE_CAMPAIGN" && s.geography.precision_policy?.kinetic !== "country" && (
        <p className="small">
          Attack records here keep the convention this country was onboarded under: facility and region named. The
          other Gulf countries publish attack records for the country as a whole. Whether this country's records move
          to that rule while an attack campaign is recorded is an open decision for the project owner. Until it is
          made, lists that set several countries side by side (the home page and the Gulf littoral overview) show
          these records as country level, with no facility, region or effect, and every record's later status is
          withheld here as everywhere.
        </p>
      )}
      <p className="small dim">Audits: {s.audit_docs.join(", ")} in the project repository.</p>
    </div>
  );
}
