import { localISODate } from "../freshness";
import { useEffect, useMemo, useRef, useState } from "react";
import type maplibregl from "maplibre-gl";
import SimpleMap from "./SimpleMap";
import SystemSwitcher from "./SystemSwitcher";
import ResearchCoverage from "./ResearchCoverage";
import {
  CAMPAIGN_STATE_LABEL, LANGUAGE_LABEL, languageNames, ENVIRONMENT_LABEL, READINESS_LABEL, RECOVERY_KIND_LABEL, RECOVERY_LABEL, RESEARCH_COMPLETENESS_LABEL,
  SECTOR_STATE_LABEL, labelFor, type CountrySystem, type SourceEntry, loadCountry, loadManifest, type CountryBundle, type CountryEvent, type Episode,
  type ManifestSystem, type SourceHealth,
} from "./manifest";
import { EventCard, fmtEventDate } from "./EventCard";
import { EmptyCorpus } from "./EmptyCorpus";
import { Disclosure, ResearchPreviewBadge } from "./Disclosure";
import { NO_SCORE_NOT_ZERO, RESEARCH_PREVIEW_DEFINITION, RESEARCH_PREVIEW_LABEL, inSentence, noScorePlain } from "./countryCopy";
import { confidenceOptions, eventAnchor } from "./evidence";
import { ConfidenceSummary } from "./ConfidenceSummary";
import { laneLine } from "./laneCoverage";
import { PLACEMENT_LABEL } from "./placement";
import { loadContext, rowForSystem, type EnergyContext } from "./context";
import { NationalFigures } from "./WorldContext";
import { LOCATION_EVENT, navigate, navigateCompare } from "./router";
import { PanelBoundary } from "../components/ViewBoundary";
import { COUNTRY_EXPORT_FIT_PADDING, COUNTRY_EXPORT_SUMMARY_PADDING, composeCountryFrame, countryFilename } from "./countryExport";
import { DISPUTED, NO_EVENTS, fillFor, scaleFor, type Scale } from "./countryScale";
import { downloadBlob, exportMapPng } from "../mapExport";
import { daysBetween, fmtDate } from "../data";
import { readerText } from "./readerText";
import { CountryNav } from "./GlobalNav";
import { registerCountryRegions } from "./searchIndex";
import { RecordFilterBar } from "./RecordFilterBar";
import {
  applyFilters, activeFilters, decodeFilters, describeFilters, encodeFilters, filterQueryOf, hidingFilters, withoutFilters,
  type FilterState,
} from "./recordFilters";
import { countryExport, countryFilters, countrySearch, exportOrder, type CountryFilters } from "./countryFilters";
import { downloadBlob as downloadFile } from "../download";
import {
  DEFAULT_TAB, TAB_LABEL, regionalGroupFor, resolveTab, tabFromSearch, tabsFor, withTab, type RegionalGroup, type Tab,
} from "./countryTabs";
import { CountryOverview } from "./OverviewBlock";
import { CountryImpacts, impactPresence, useCountryImpacts } from "./CountryImpacts";
import { CountryRegional } from "./CountryRegional";
import { loadConfidenceMethod } from "./impacts";
import { impactExportSummary } from "./countryImpactModel";
import "../styles/countryOverview.css";
import { ImpactBriefButton } from "./impacts/brief/ImpactBriefButton";

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
 *
 *  Iteration 22: the page opens with "What this page can tell you" (countryOverview.ts), the side
 *  tabs are linkable (`tab=`, countryTabs.ts), and two tabs show corpora that are NOT this
 *  country's published record: the impact layer's records for the country, and the Gulf regional
 *  context. Neither changes a count shown anywhere else on the page.
 */

function initialRegion(): string | null {
  return new URLSearchParams(window.location.search).get("r");
}

/** `#ev-<key>` from the address, for a link to one record (see `eventAnchor`). */
function initialAnchor(): string | null {
  const h = window.location.hash.slice(1);
  return h.startsWith("ev-") ? h : null;
}

/** `#tab-<name>` from the address opens the page on that tab (iteration 22): the home page's
 *  What's new panel links a coverage or method change to the tab that explains it. Read once, when
 *  the page opens, and only when the address carries no `tab=`; any other value opens the default tab. */
function initialTab(): Tab {
  const t = window.location.hash.slice(1);
  return t === "tab-research" ? "research" : t === "tab-method" ? "method" : DEFAULT_TAB;
}

export default function CountryView({ id }: { id: string }) {
  const [entry, setEntry] = useState<ManifestSystem | null>(null);
  const [bundle, setBundle] = useState<CountryBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  // The tab the address or the reader asked for. `tab`, below, is the one shown: a tab this system
  // does not have (the regional context outside its group) falls back to the country's own record.
  const [askedTab, setTab] = useState<Tab>(() => tabFromSearch(window.location.search) ?? initialTab());
  const [regional, setRegional] = useState<RegionalGroup | null>(null);
  const tabs = useMemo(() => tabsFor(regional), [regional]);
  const tab = resolveTab(askedTab, tabs);
  const [region, setRegion] = useState<string | null>(initialRegion);
  // The event filters live in the address (iteration 22). Kept as the address's own text until the
  // country has loaded, because only its records say which filters and values this page has.
  const [filterQuery, setFilterQuery] = useState(() => filterQueryOf(window.location.search));
  const [clearedNote, setClearedNote] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportMsg, setExportMsg] = useState<string | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [ctx, setCtx] = useState<EnergyContext | null>(null);
  const [ctxFailed, setCtxFailed] = useState(false);

  // National context is a separate file: if it fails, the country's own record is untouched. It is
  // read only by the context and sources tabs and the PNG brief, so it is fetched when one of those
  // is opened, not with the page (iteration 21: 160 KB the default view never showed).
  const needsCtx = tab === "context" || tab === "sources";
  useEffect(() => {
    if (!needsCtx) return;
    let live = true;
    setCtxFailed(false);
    loadContext().then((c) => { if (live) setCtx(c); }).catch(() => { if (live) setCtxFailed(true); });
    return () => { live = false; };
  }, [needsCtx]);

  // Load this country. A reader who has already moved on never sees the answer: the view is keyed
  // on the id, and `ctl` marks this mount as left.
  useEffect(() => {
    const ctl = new AbortController();
    setBundle(null);
    setEntry(null);
    setError(null);
    setRegional(null);
    loadManifest()
      .then((m) => {
        const e = m.systems.find((s) => s.id === id && s.kind === "country");
        if (!e) throw new Error(`"${id}" is not a monitored country system.`);
        if (ctl.signal.aborted) return null;
        setEntry(e);
        // Whether this system has the regional-context tab is the manifest's group table, read here.
        setRegional(regionalGroupFor(m, id));
        return loadCountry(e);
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

  // This country's region names join the global search for the rest of the session: already
  // loaded, so they cost nothing (iteration 21).
  useEffect(() => {
    if (!bundle) return;
    const geo = bundle.system.geography as CountrySystem["geography"] & {
      display_names?: Record<string, string>; unit_aliases?: Record<string, string[]> };
    registerCountryRegions({
      systemId: bundle.system.system_id, systemName: bundle.system.name, unitLabel: geo.unit_label,
      units: bundle.regions.features.map((f) => ({ code: String(f.properties?.code ?? ""), name: String(f.properties?.name ?? "") }))
        .filter((u) => u.code && u.name),
      displayNames: geo.display_names, aliases: geo.unit_aliases,
    });
  }, [bundle]);

  // A search result for a region of this same country moves the URL without remounting the view.
  useEffect(() => {
    const sync = () => {
      setRegion(initialRegion());
      setFilterQuery(filterQueryOf(window.location.search));
      // An address without a tab is the country's own record: a search result for a region must
      // not leave the reader on another tab.
      setTab(tabFromSearch(window.location.search) ?? initialTab());
    };
    window.addEventListener(LOCATION_EVENT, sync);
    window.addEventListener("popstate", sync);
    return () => { window.removeEventListener(LOCATION_EVENT, sync); window.removeEventListener("popstate", sync); };
  }, []);

  // Region selection, the open tab and the event filters are shareable, like the theatre's view
  // state. The entry is replaced, not pushed: Back leaves the page instead of undoing one checkbox
  // at a time, and coming back to the page (Back, Forward, a reload, a shared link) shows the same list.
  // Until the country has loaded, the tab the address asked for is kept as asked: which tabs this
  // system has is not known yet, and a deep link must survive a reload during the wait.
  const urlTab = bundle ? tab : askedTab;
  useEffect(() => {
    // The record anchor survives: a link to one record must still point at it after this rewrite.
    window.history.replaceState(null, "", `${window.location.pathname}?${withTab(countrySearch(id, region, filterQuery), urlTab)}${window.location.hash}`);
  }, [id, region, filterQuery, urlTab]);

  // The impact corpus is a separate file, read when its tab is first opened. A page with no
  // published record has nothing else to show, so it asks at once: its overview then says whether
  // the corpus holds anything for this country instead of sending the reader to find out.
  const noRecords = bundle ? bundle.system.event_summary.recorded_events === 0 : false;
  const impacts = useCountryImpacts(id, tab === "impacts" || noRecords, tab);

  // A link in the overview opens its tab and moves the reader to it: on a phone the tabs are a
  // screen or more below the overview.
  const detailsRef = useRef<HTMLElement | null>(null);
  const [jump, setJump] = useState(0);
  const openTab = (t: Tab) => { setTab(t); setJump((n) => n + 1); };
  useEffect(() => {
    if (jump === 0) return;
    detailsRef.current?.scrollIntoView({ block: "start" });
    detailsRef.current?.focus({ preventScroll: true });
  }, [jump]);

  const today = localISODate(new Date());
  // The confidence filter lists its categories in the method's own order (iteration 22).
  const filters = useMemo<CountryFilters | null>(() => (bundle
    ? countryFilters(bundle.system, bundle.events, confidenceOptions(bundle.system, bundle.events)) : null), [bundle]);
  const decoded = useMemo(() => (filters ? decodeFilters(filterQuery, filters.defs) : null), [filters, filterQuery]);
  const setFilters = (next: FilterState) => {
    if (!filters) return;
    setClearedNote(null);
    setFilterQuery(encodeFilters(filters.defs, next));
  };

  // A link to one record: show it in the full list, scroll it into view and mark it.
  const [anchor, setAnchor] = useState<string | null>(initialAnchor);
  useEffect(() => {
    // A link to another record of the same country changes only the hash: no reload, no remount.
    const onHash = () => setAnchor(initialAnchor());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const target = useMemo(() => (bundle && anchor
    ? bundle.events.find((e) => eventAnchor(e, bundle.system.system_id) === anchor) ?? null : null), [bundle, anchor]);
  useEffect(() => {
    if (!target) return;
    setRegion(null);
    setTab("events");
    // A link to a record the filters hide still opens it: the filters that hide it are cleared, and
    // the page says which. Run once per linked record, so the reader can filter again afterwards.
    if (filters && decoded) {
      const hiding = hidingFilters(target, filters.defs, decoded.state, today);
      if (hiding.length > 0) {
        const labels = filters.defs.filter((d) => hiding.includes(d.id)).map((d) => d.label);
        setFilterQuery(encodeFilters(filters.defs, withoutFilters(decoded.state, hiding)));
        setClearedNote(`The linked record was hidden by the ${labels.join(" and ")} ${labels.length === 1 ? "filter" : "filters"}, so ${labels.length === 1 ? "that filter was" : "those filters were"} cleared to show it.`);
      }
    }
    // After the list has rendered, with the record in it.
    const t = window.setTimeout(() => document.getElementById(anchor!)?.scrollIntoView({ block: "center" }), 0);
    return () => window.clearTimeout(t);
    // Only a new linked record runs this: a later filter change must not be undone.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, anchor]);

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
    ? daysBetween(sys.record_reviewed, localISODate(new Date())) : null;
  const stale = reviewAge != null && reviewAge > sys.review_freshness_days;

  const runExport = async () => {
    const m = mapRef.current;
    if (!m) { setExportMsg("The map is not ready yet."); return; }
    setExporting(true);
    setExportMsg(null);
    try {
      // The brief carries the national figures; without the context file it is drawn without them.
      const national = ctx ?? await loadContext().catch(() => null);
      // With the impact tab open, the picture carries that list's summary: what the reader was
      // looking at when they asked for it. Built from the same records the tab lists.
      let impactSummary = null;
      if (tab === "impacts" && impacts.state === "ready") {
        // The served sentence about what confidence is; the summary has its own if the file fails.
        const method = await loadConfidenceMethod().catch(() => null);
        impactSummary = impactExportSummary(sys.name, impacts.records, impacts.attempts, impacts.payload, method?.statement);
      }
      const res = await exportMapPng({
        source: m, width: 1600, height: 900, pixelRatio: 1,
        fit: { bounds: sys.geography.view_bounds ?? sys.geography.bounds,
               padding: impactSummary ? COUNTRY_EXPORT_SUMMARY_PADDING : COUNTRY_EXPORT_FIT_PADDING },
        compose: (c) => composeCountryFrame(c, sys, scale, national ? { row: rowForSystem(national, sys.system_id), ctx: national } : null, impactSummary),
      });
      downloadBlob(res.blob, impactSummary ? countryFilename(sys).replace(/\.png$/, "-impacts.png") : countryFilename(sys));
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

      {/* One main landmark per view: everything below the shared header and navigation bar. */}
      <main className="country-main">
      {/* On a phone the map comes before the full statements (iteration 20, §78). This line keeps
          the caveats in the first screen and leads to them. Hidden on wider screens. */}
      <p className="small phone-only phone-caveats">
        {sys.maturity === "research_preview" && <><ResearchPreviewBadge />{" "}</>}
        {sys.campaign_state && sys.campaign_state.state !== "NO_ACTIVE_CAMPAIGN" && (
          <><span className="badge context-only-badge">Active-campaign safeguards apply</span>{" "}</>
        )}
        No index · {sys.event_summary.recorded_events === 0 ? "no qualifying records yet" : `${sys.event_summary.recorded_events} qualifying records`}.{" "}
        <a href="#notices">What this page can and cannot tell you</a>
      </p>

      {/* What is published, what else is here, what is withheld: before the detail, on every system. */}
      <CountryOverview sys={sys} impacts={impactPresence(impacts)} regional={regional} onTab={openTab} />

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
              dataset, not {inSentence(sys.name)}: it does not mean nothing happened. Reporting environment:{" "}
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
            <p className="small research-preview-statement">
              {/* The one definition, stated in full where the page explains itself. */}
              <span className="badge research-partial">{RESEARCH_PREVIEW_LABEL}</span>{" "}
              {RESEARCH_PREVIEW_DEFINITION}
            </p>
          )}
          {sys.campaign_state && sys.campaign_state.state !== "NO_ACTIVE_CAMPAIGN" && (
            <p className="small">
              <span className="badge context-only-badge">Active-campaign publication safeguards apply</span>{" "}
              <strong>{labelFor(CAMPAIGN_STATE_LABEL, sys.campaign_state.state)}.</strong>{" "}
              {readerText(sys.campaign_state.basis)} Checked {fmtDate(sys.campaign_state.checked)}. While that holds, an attack
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
              {sys.name}'s older records keep an earlier convention: an attack record here names its facility and its
              region. The newer Gulf country pages record an attack for the country as a whole, with no facility or
              region. Pages that list several countries together show these records the newer way, as
              “{PLACEMENT_LABEL.national_safeguarded}”, with no facility, region or effect.
            </p>
          )}
        </section>
      )}

      <div className="country-body">
        {/* With no record placed in any region the map shows geography only: it stays, smaller, so the
            records and the reason come first instead of a full-height empty map. */}
        <section className={`country-map${sys.event_summary.placed_in_a_region === 0 ? " is-unplaced" : ""}`} aria-label="Map">
          <SimpleMap
            data={bundle.regions}
            bounds={sys.geography.view_bounds ?? sys.geography.bounds}
            idProp="code"
            selected={validRegion}
            fill={fillFor(scale) as maplibregl.ExpressionSpecification}
            onPick={(code) => { setRegion((cur) => (cur === code ? null : code)); setTab("events"); }}
            ariaLabel={`Map of ${sys.name} by ${sys.geography.unit_label}. Select one to list its events.`}
            emptyMessage={scale.thresholds.length === 0 ? `No record is placed in any ${sys.geography.unit_label}, so nothing is shaded. An unshaded map is not a quiet country.` : null}
            attribution="Boundaries: Natural Earth (public domain), line of actual control. Events: cited public reporting."
            alternative="The list of reported events beside it does not need the map."
            onMap={(m) => { mapRef.current = m; }}
          />
          {/* A filter that cannot filter anything is replaced by the reason (iteration 21). */}
          {sys.event_summary.placed_in_a_region === 0 ? (
            <p className="small dim region-select-reason">
              {sys.geography.precision_policy?.other === "country"
                ? `Every record here is kept for the country as a whole, so there is no ${sys.geography.unit_label} filter.`
                : sys.event_summary.recorded_events === 0
                  ? `No records yet, so there is nothing to filter by ${sys.geography.unit_label}.`
                  : `No record is placed in a single ${sys.geography.unit_label}, so there is nothing to filter by ${sys.geography.unit_label}.`}
            </p>
          ) : (
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
          )}
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
                {sys.event_summary.country_level > 0 && <>{" "}Records marked {PLACEMENT_LABEL.national} or {PLACEMENT_LABEL.several_regions}, listed but not drawn: {sys.event_summary.country_level}.</>} What was reported and found — not a rate of disruption, and not comparable
                with any other country.</span>
            )}
            {sys.geography.precision_policy?.kinetic === "country" && sys.event_summary.recorded_events > 0 && (
              <span className="small dim">Attacks and sabotage are recorded for the country as a whole here and
                are never drawn in a {sys.geography.unit_label}.</span>
            )}
          </div>
        </section>

        <section className="country-side panel" aria-label="Details" id="country-details" tabIndex={-1} ref={detailsRef}>
          <TabRow tabs={tabs} tab={tab} onTab={setTab} />
          {/* Keyed on the tab: a tab that fails costs that tab, and the others still open. */}
          <PanelBoundary key={tab} label={`The ${TAB_LABEL[tab]} tab`}>
          {tab === "events" && (
            <EventsPanel
              events={events} region={validRegion} regionName={regionName}
              regionStatus={regionStatus} onClear={() => setRegion(null)} bundle={bundle}
              ctx={ctx} onTab={setTab} target={target?.event_id ?? null}
              filters={filters!} filterState={decoded!.state} onFilters={setFilters} today={today}
              filterNotes={[...(clearedNote ? [clearedNote] : []), ...decoded!.notes]}
            />
          )}
          {/* A one-page image of this country's impact-layer evidence, with its own caveats; for a Gulf
              member it adds the newest dated regional statements (iteration 22). It sits with the
              records it summarises, not in the header: a fourth header button pushed the map out of a
              phone's first screen. */}
          {tab === "impacts" && <div className="impact-brief-row"><ImpactBriefButton systemId={id} /></div>}
          {tab === "impacts" && <CountryImpacts sys={sys} impacts={impacts} today={today} />}
          {tab === "regional" && regional && <CountryRegional sys={sys} group={regional} />}
          {tab === "sectors" && <SectorsPanel bundle={bundle} />}
          {tab === "context" && <ContextPanel bundle={bundle} ctx={ctx} ctxFailed={ctxFailed} />}
          {tab === "research" && <ResearchCoverage bundle={bundle} />}
          {tab === "sources" && <SourcesPanel bundle={bundle} ctx={ctx} />}
          {tab === "method" && <MethodPanel bundle={bundle} />}
          </PanelBoundary>
          {exportMsg && <p className="small" role="status">{exportMsg}</p>}
        </section>
      </div>
      </main>
    </div>
  );
}

/** The side tabs. One row that scrolls sideways on a phone (eight tabs wrap into four rows at
 *  390 px and push the content a screen down); the open tab is brought into the row's view, so a
 *  deep link to a later tab never opens with its own tab out of sight. Ordinary buttons with
 *  aria-pressed: the open tab is said in words, not only by its colour. */
function TabRow({ tabs, tab, onTab }: { tabs: readonly Tab[]; tab: Tab; onTab: (t: Tab) => void }) {
  const row = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = row.current;
    const on = el?.querySelector<HTMLElement>('[aria-pressed="true"]');
    if (!el || !on) return;
    // Only the row is scrolled, never the page: scrollIntoView would also move the window.
    const left = on.offsetLeft - el.offsetLeft;
    if (left < el.scrollLeft) el.scrollLeft = left;
    else if (left + on.offsetWidth > el.scrollLeft + el.clientWidth) el.scrollLeft = left + on.offsetWidth - el.clientWidth;
  }, [tab, tabs]);
  return (
    <div className="tabs" role="group" aria-label="Detail views" ref={row}>
      {tabs.map((t) => (
        <button key={t} className="ghost" aria-pressed={tab === t} data-tab={t} onClick={() => onTab(t)}>
          {TAB_LABEL[t]}
        </button>
      ))}
    </div>
  );
}

/** Sources past their stale limit, on the reader's clock. Display only: never an analytic input. */
function staleSources(sources: SourceEntry[], today: string): SourceEntry[] {
  return sources.filter((x) => x.last_checked && x.stale_after_days != null
    && daysBetween(x.last_checked, today) > x.stale_after_days);
}

/** Two INDEPENDENT axes, shown side by side so neither reads as the other: are the sources
 *  current, and was the event search systematic? "Sources current, research incomplete" is a
 *  normal, non-contradictory state. */
function ResearchStatus({ sys }: { sys: CountrySystem }) {
  const today = localISODate(new Date());
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
        {/* Separate counts by state, never "3 of 9 finished": a group waiting on a publisher, a group
            barely begun and a planned search set run in full are different states (laneCoverage.ts). */}
        {rf.lane_states && Object.keys(rf.lane_states).length > 0 && (
          <p className="lane-state-line">{laneLine(rf.lane_states, rf.lanes_declared)}</p>
        )}
        {rf.last_systematic_pass && rf.coverage_window && (
          <span className="dim">Research period {fmtDate(rf.coverage_window[0])} – {fmtDate(rf.coverage_window[1])};
            last worked on {fmtDate(rf.last_systematic_pass)}{overdue ? "; a new pass is due" : ""}.</span>
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
    <>
    {/* One header per page: the site bar (home, breadcrumb, tools, system picker), then the page's
        own title and actions as plain content. Two stacked bars cost a phone a third of its screen. */}
    <header className="site-head">
      <CountryNav id={id} name={name} extra={<SystemSwitcher current={id} />} />
    </header>
    <div className="page-title">
      <div>
        <h1 className="ribbon-title">{name}</h1>
        <div className="ribbon-sub">Reported major disruptions{wholeCountry ? ", recorded for the country as a whole"
          : attacksWhole ? " by first-level region; attacks recorded for the country as a whole" : " by first-level region"}</div>
      </div>
      {children && <div className="head-actions">{children}</div>}
    </div>
    </>
  );
}

function EventsPanel({ events, region, regionName, regionStatus, onClear, bundle, ctx, onTab, target, filters, filterState, onFilters, today, filterNotes }: {
  events: CountryEvent[]; region: string | null; regionName: string | null;
  regionStatus: string | null; onClear: () => void; bundle: CountryBundle;
  ctx: EnergyContext | null; onTab: (t: Tab) => void; target: string | null;
  filters: CountryFilters; filterState: FilterState; onFilters: (next: FilterState) => void; today: string;
  filterNotes: string[];
}) {
  const unit = bundle.system.geography.unit_label;
  const [exportMsg, setExportMsg] = useState<string | null>(null);
  if (events.length === 0 && !region) {
    return (
      <div className="events-panel">
        <h2>All reported events</h2>
        <EmptyCorpus bundle={bundle} ctx={ctx} onTab={onTab} />
      </div>
    );
  }
  const inRegion = !!(region && regionName);
  // A multi-region event that names this region is listed here too, never counted here: the
  // region view must not say "none found" when the payload records one that reached it.
  const regionPlaced = inRegion ? events.filter((e) => e.region_code === region) : [];
  const regionShared = inRegion ? events.filter((e) => e.geography_precision !== "admin1" && e.regions_affected.includes(region!)) : [];
  // The one list the filters act on: this region's records, or all of the country's.
  const scope = inRegion ? [...regionPlaced, ...regionShared] : events;
  const shown = applyFilters(scope, filters.defs, filterState, today);
  const shownIds = new Set(shown.map((e) => e.event_id));
  const filtering = activeFilters(filters.defs, filterState).length > 0;
  const noun = inRegion ? `published records for ${regionName}` : "published records";

  // The two files are built on the click, from the list on screen and nothing else.
  const save = (which: "csv" | "readme") => {
    const out = countryExport(bundle.system, shown, scope.length, describeFilters(filters.defs, filterState, today), regionName, today);
    if (which === "csv") {
      downloadFile(new Blob([out.csv], { type: "text/csv;charset=utf-8" }), out.csvName);
      setExportMsg(`Saved ${out.csvName}: ${shown.length} of ${scope.length} ${noun}.`);
    } else {
      downloadFile(new Blob([out.readme], { type: "text/plain;charset=utf-8" }), out.readmeName);
      setExportMsg(`Saved ${out.readmeName}.`);
    }
  };
  const filterBar = scope.length > 0 && (
    <>
      <RecordFilterBar defs={filters.defs} state={filterState} onChange={onFilters} records={scope} shown={shown.length}
                       today={today} noun={noun} notes={filterNotes} fixed={filters.fixed}>
        <span className="record-export" role="group" aria-label="Download the records shown">
          <button type="button" className="ghost" onClick={() => save("csv")} disabled={shown.length === 0}
                  aria-label={`Download CSV of the ${shown.length} ${shown.length === 1 ? "record" : "records"} shown`}>Download CSV</button>
          <button type="button" className="ghost" onClick={() => save("readme")}
                  aria-label="About this file: download the note that explains the CSV">About this file</button>
        </span>
      </RecordFilterBar>
      <p className="small dim record-export-note">The CSV holds the records shown here, after the filters. “About this file” explains its
        columns and limits: these are the published records in this corpus, not a census, and counts are not comparable across countries.</p>
      {exportMsg && <p className="small" role="status">{exportMsg}</p>}
      {filtering && shown.length === 0 && (
        <p className="small filter-empty" role="status">No published record in this list matches the filters. That describes the
          filters, not {inRegion ? regionName : inSentence(bundle.system.name)}: {scope.length} {scope.length === 1 ? "record is" : "records are"} hidden by them.
          Clear the filters to see {scope.length === 1 ? "it" : "them"}.</p>
      )}
    </>
  );

  if (inRegion) {
    const placed = regionPlaced.filter((e) => shownIds.has(e.event_id));
    const shared = regionShared.filter((e) => shownIds.has(e.event_id));
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
        ) : scope.length === 0 ? (
          <p className="small dim">No qualifying events recorded for {regionName}. That means none
            were found in the sources monitored. It is not evidence that none occurred.</p>
        ) : null}
        {filterBar}
        <ol className="event-list">
          {[...placed].reverse().map((e) => <EventCard key={e.event_id} e={e} bundle={bundle} targeted={e.event_id === target} />)}
        </ol>
        {shared.length > 0 && (
          <>
            <h3 className="eyebrow">{PLACEMENT_LABEL.several_regions}: records that included {regionName}</h3>
            <p className="small dim">Listed, not counted on the map for this {unit}.</p>
            <ol className="event-list">
              {[...shared].reverse().map((e) => <EventCard key={e.event_id} e={e} bundle={bundle} targeted={e.event_id === target} />)}
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
      {filterBar}
      <p className="small dim">A record is a publicly reported event that meets the inclusion rule (Why no score tab): it is what was reported and found, not everything that happened.</p>
      {/* With a filter on, one flat list, newest first: an episode group with some of its records
          hidden would read as a smaller episode. */}
      {filtering && (
        <ol className="event-list">
          {exportOrder(shown).map((e) => <EventCard key={e.event_id} e={e} bundle={bundle} targeted={e.event_id === target} />)}
        </ol>
      )}
      {!filtering && (<>
      {/* An empty page says what was searched and what is incomplete; the episode definition belongs
          beside episodes (iteration 20, §75). */}
      <p className="small dim">{`${events.length} records in ${bundle.episodes.length} episodes. An episode is one named hazard or one event a source explicitly identifies as common; a record linked to no other is an episode of one.`}</p>
      <ol className="event-list">
        {rows.map((row) => row.kind === "event"
          ? <EventCard key={row.e.event_id} e={row.e} bundle={bundle} targeted={row.e.event_id === target} />
          : (
            <li key={row.ep.episode_id} className="episode-group">
              <div className="episode-head">
                <span className="eyebrow">Episode · {row.ep.records} records</span>
                <strong>{row.ep.name}</strong>
                <span className="small dim">{labelFor(bundle.system.episode_bases, row.ep.basis)}</span>
              </div>
              <ol className="event-list">
                {row.ep.event_ids.map((id) => eventById.get(id)).filter((e): e is CountryEvent => !!e)
                  .map((e) => <EventCard key={e.event_id} e={e} bundle={bundle} targeted={e.event_id === target} inEpisode />)}
              </ol>
            </li>
          ))}
      </ol>

      {countryLevel.length > 0 && (
        <>
          <h3 className="eyebrow">Not placed in one {unit}</h3>
          <p className="small dim">Records marked {PLACEMENT_LABEL.national} (including offshore) or {PLACEMENT_LABEL.several_regions}.
            They are listed, never counted against any single region.</p>
          <ol className="event-list">
            {[...countryLevel].reverse().map((e) => <EventCard key={e.event_id} e={e} bundle={bundle} targeted={e.event_id === target} />)}
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
                {m.basis && <div className="dim">Basis: {readerText(m.basis)}</div>}
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

function SourcesPanel({ bundle, ctx }: { bundle: CountryBundle; ctx: EnergyContext | null }) {
  const s = bundle.system;
  const rec = s.event_summary.recovery_research;
  const kinds = Object.entries(s.event_summary.recovery_kinds).filter(([, n]) => n > 0);
  const unrecorded = bundle.events.filter((e) => e.review.source_access === "not recorded by the research lane").length;
  const today = localISODate(new Date());
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
                <td className="small dim">{readerText(x.licence)}</td>
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
      {s.source_health && bundle.events.length > 0 && <SourceHealthBlock h={s.source_health} />}
      <ConfidenceSummary bundle={bundle} />
      <SourceBrowser bundle={bundle} ctx={ctx} />
      <p className="small research-coverage">
        <strong>{s.research_log.passes.length === 0 ? "No search has been run yet" : RESEARCH_COMPLETENESS_LABEL[s.research_freshness.completeness]}.</strong>{" "}
        {s.research_freshness.last_systematic_pass
          ? `Last systematic pass ${fmtDate(s.research_freshness.last_systematic_pass)}, over a declared window of ${fmtDate(s.research_freshness.coverage_window?.[0] ?? null)} – ${fmtDate(s.research_freshness.coverage_window?.[1] ?? null)}. Source group by source group under Research coverage.`
          : s.research_log.passes.length === 0 ? "No research pass has been logged for this country."
            : "Every pass so far was targeted at named gaps and leads."}
      </p>
      <p className="small dim">{readerText(s.research_freshness.note)}</p>
      {/* No published record: no recovery evidence and no review to total, and a row of zeros would
          read as a finding (iteration 21). */}
      {bundle.events.length === 0 ? (
        <p className="small dim">No record is published yet, so there is no recovery evidence and no review to describe.</p>
      ) : (<>
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
      </>)}
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
      <p className="small dim">{readerText(h.note)}</p>
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

/** The best plain explanation on the site of why a country has no score (iteration 21): what the
 *  score was built for and why it does not transfer, then why a missing score is not a zero, then
 *  the technical detail for a reader who wants it. */
function MethodPanel({ bundle }: { bundle: CountryBundle }) {
  const s = bundle.system;
  const unmet = s.onboarding_gate.filter((g) => g.status !== "met").length;
  const legacy = s.campaign_state && s.campaign_state.state !== "NO_ACTIVE_CAMPAIGN" && s.geography.precision_policy?.kinetic !== "country";
  return (
    <div className="why-no-score">
      <h2>Why no score</h2>
      <p className="no-score-plain">{noScorePlain(s.name)}</p>
      <h3>No score is not a score of zero</h3>
      <p className="small">{NO_SCORE_NOT_ZERO}</p>
      <p className="small dim">{s.no_index_reason}</p>
      <h3>What this page shows instead</h3>
      <ul className="small">
        <li>Reported disruptions that meet the inclusion rule and have passed review, each with its sources.</li>
        <li>For each sector, what state the evidence is in, and why.</li>
        <li>The national energy picture, as context: it describes the size of the energy system, never how disrupted it is.</li>
        <li>What the research searched, and what it could not read or has not reached yet.</li>
      </ul>
      <p className="small">How {inSentence(s.name)} reports disruptions — <Disclosure label={labelFor(ENVIRONMENT_LABEL, s.reporting_environment)}
        text={s.reporting_environment_text} className="linklike" />. That shapes what can be found here as much as what happened.</p>

      <details className="small no-score-technical">
        <summary>Technical detail: why the Russia, Belarus &amp; Crimea method does not transfer</summary>
        <p>The Russia, Belarus &amp; Crimea index combines reported damage by sector, weighting each sector by its share of the monitored
          capacity, lets each event's weight fade with a fixed half-life, and adds a measure of the power-transmission
          network. Each of those parts was set for that one area: its weights come from that infrastructure, the half-life
          from how that campaign's damage was reported and repaired, and the transmission measure from that grid.</p>
        <p>Here none of the three has a basis. There is no shared capacity denominator for the records, so a weight per
          sector would be invented. Recovery evidence is uneven and, for attacked facilities under the campaign
          safeguards, deliberately unpublished, so a fixed fading rate would stand in for evidence that does not exist.
          Reporting rules differ between countries, so the same number would mean different things in each.</p>
        <p>A sector can only carry a value once code computes one from evidence that supports it; until then every
          sector says "tracked, not scored" or why it is unknown. The Sectors tab shows each one.</p>
      </details>

      <details className="small">
        <summary>How a record is included</summary>
        <p>{readerText(s.inclusion_threshold.rule)}</p>
        <ol>
          {Object.entries(s.inclusion_threshold.clauses).map(([k, v]) => <li key={k} value={Number(k)}>{readerText(v)}</li>)}
        </ol>
        <p className="dim">Inclusion rule version {s.inclusion_threshold.version}.</p>
      </details>

      <details className="small">
        <summary>Publication checklist</summary>
        <p className="dim">
          {unmet === 0
            ? "Every item of the publication checklist is met."
            : `${unmet} of ${s.onboarding_gate.length} items of the publication checklist are not met or only partly met; each says why below.`}
        </p>
        <table className="sector-table">
          <tbody>
            {s.onboarding_gate.map((g) => (
              <tr key={g.item}>
                <td className="small">{g.label}</td>
                <td><span className={`badge gate-${g.status}`}>{g.status}</span></td>
                <td className="small dim">{readerText(g.note)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>

      <details className="small">
        <summary>How records are placed on the map</summary>
        <p>{readerText(s.geography.note)}</p>
        {s.geography.rulings.length > 0 && (
          <ul>{s.geography.rulings.map((r) => <li key={r.code}>{readerText(r.note)}</li>)}</ul>
        )}
        {legacy && (
          <p>
            Attack records here keep the earlier convention of naming the facility and the region. The newer Gulf
            country pages publish an attack record for the country as a whole. Lists that set several countries side
            by side (the home page and the Gulf littoral overview) show these records the newer way, with no facility,
            region or effect, and every attacked facility's later status is withheld here as everywhere.
          </p>
        )}
      </details>
    </div>
  );
}
