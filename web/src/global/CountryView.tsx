import { useEffect, useMemo, useRef, useState } from "react";
import type maplibregl from "maplibre-gl";
import SimpleMap from "./SimpleMap";
import SystemSwitcher from "./SystemSwitcher";
import {
  ENVIRONMENT_LABEL, READINESS_LABEL, RECOVERY_KIND_LABEL, RECOVERY_LABEL, SECTOR_STATE_LABEL,
  labelFor, loadCountry, loadManifest, type CountryBundle, type CountryEvent, type Episode,
  type ManifestSystem,
} from "./manifest";
import { navigate } from "./router";
import { composeCountryFrame, countryFilename } from "./countryExport";
import { DISPUTED, NO_EVENTS, fillFor, scaleFor, type Scale } from "./countryScale";
import { downloadBlob, exportMapPng } from "../mapExport";
import { daysBetween, fmtDate } from "../data";

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

type Tab = "events" | "sectors" | "context" | "sources" | "method";

function initialRegion(): string | null {
  return new URLSearchParams(window.location.search).get("r");
}

/** A month-precision date is shown as a month: printing "1 Apr" would invent a day. */
function fmtEventDate(e: CountryEvent): string {
  const d = e.date_precision === "month"
    ? new Date(`${e.date}T00:00:00Z`).toLocaleDateString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" })
    : fmtDate(e.date);
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
  const regionStatus = feature ? String(feature.properties?.status ?? "normal") : null;
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
        compose: (c) => composeCountryFrame(c, sys, scale),
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
      <CountryHeader name={sys.name} id={id}>
        <button className="ghost" onClick={runExport} disabled={exporting}>
          {exporting ? "Rendering…" : "Download PNG"}
        </button>
        <button className="ghost" onClick={() => window.print()}>Print / PDF</button>
      </CountryHeader>

      {stale && (
        <div className="stale-note" role="status">
          This country's event record was last reviewed on {fmtDate(sys.record_reviewed)},
          more than {sys.review_freshness_days} days ago. Events since then are not included.
        </div>
      )}

      <section className="country-ribbon" aria-label="Headline">
        <div className="no-index">
          <div className="no-index-value" aria-label="No index">No index</div>
          <div className="small dim">{sys.no_index_reason}</div>
        </div>
        <div>
          <div className="eyebrow">Evidence readiness</div>
          <div className={`badge readiness-${sys.evidence_readiness.toLowerCase()}`}>
            {READINESS_LABEL[sys.evidence_readiness]}
          </div>
        </div>
        <div>
          <div className="eyebrow">Recorded</div>
          <div className="small">
            <strong>{sys.event_summary.recorded_events}</strong> qualifying events recorded
            {" "}in <strong>{sys.event_summary.episodes}</strong> episodes ·
            reporting environment: {labelFor(ENVIRONMENT_LABEL, sys.reporting_environment)}.
            {" "}{sys.event_summary.note}
          </div>
          <div className="small dim">
            Event record reviewed {fmtDate(sys.record_reviewed)} · site rebuilt {fmtDate(sys.as_of)}
          </div>
        </div>
      </section>

      <p className="comparability" role="note">{sys.comparability_statement}</p>

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
          <div className="map-legend-mini">
            <span className="eyebrow">Qualifying events recorded per {sys.geography.unit_label}</span>
            <span><i style={{ background: NO_EVENTS }} /> none recorded</span>
            {scale.labels.map((label, i) => (
              <span key={label}><i style={{ background: scale.colors[i] }} />{label}</span>
            ))}
            <span><i style={{ background: DISPUTED }} /> disputed, unassigned</span>
            <span className="small dim">This country's own range, not a shared scale.
              {" "}{sys.event_summary.country_level} national or multi-region events are listed but
              not drawn. What was reported and found — not a rate of disruption, and not comparable
              with any other country.</span>
          </div>
        </section>

        <section className="country-side panel" aria-label="Details">
          <div className="tabs" role="group" aria-label="Detail views">
            {(["events", "sectors", "context", "sources", "method"] as Tab[]).map((t) => (
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
          {tab === "context" && <ContextPanel bundle={bundle} />}
          {tab === "sources" && <SourcesPanel bundle={bundle} />}
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
  sources: "Sources & data quality",
  method: "Why no score",
};

function CountryHeader({ name, id, children }: { name: string; id: string; children?: React.ReactNode }) {
  return (
    <header className="global-head">
      <div>
        <h1 className="ribbon-title">{name}</h1>
        <div className="ribbon-sub">Energy Disruption Monitor · reported major disruptions by first-level region</div>
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
      <p className="small dim">{events.length} records in {bundle.episodes.length} episodes. An episode
        is one hazard or one source statement: a storm that cut power in four states is one episode
        of four records.</p>
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
    </div>
  );
}

function recoveryText(e: CountryEvent): string {
  const r = e.recovery;
  if (r.research_status === "EVIDENCE_FOUND" && r.kind) return labelFor(RECOVERY_KIND_LABEL, r.kind);
  return labelFor(RECOVERY_LABEL, r.research_status);
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
      {e.effect && <p className="small"><span className="dim">Reported effect: </span>{e.effect}</p>}
      {e.regions_affected.length > 0 && (
        <p className="small dim">Regions affected: {e.regions_affected.join(", ")}</p>
      )}
      {ep && ep.records > 1 && !inEpisode && (
        <p className="small dim episode-note">Part of an episode: {ep.name} ({ep.records} records)</p>
      )}
      <p className="small">
        <span className={`rec rec-${recClass.toLowerCase()}`}>{recoveryText(e)}</span>
        {e.recovery.date && <span className="dim"> ({fmtDate(e.recovery.date)})</span>}
        {e.recovery.evidence && <span className="dim"> — {e.recovery.evidence}</span>}
      </p>
      <p className="small sources">
        {e.sources.map((s, i) => (
          <a key={i} href={s.url} target="_blank" rel="noreferrer">{s.publisher ?? new URL(s.url).hostname}</a>
        ))}
        <span className="dim">{e.review.source_access === "not recorded by the research lane"
          ? "· whether these were read was not recorded" : ""}</span>
      </p>
    </li>
  );
}

function SectorsPanel({ bundle }: { bundle: CountryBundle }) {
  return (
    <div>
      <h2>Sectors</h2>
      <p className="small dim">Every sector has an explicit published state. "Tracked, not scored"
        means events are listed and context is shown, but no value is computed. The research
        lane's assessment is what the evidence <em>could</em> support after the decisions in the
        methodology; it is not a published state and no value exists behind it.</p>
      <table className="sector-table">
        <thead><tr><th>Sector</th><th>Published state</th><th>Research lane's assessment (not published)</th></tr></thead>
        <tbody>
          {bundle.system.sectors.map((s) => (
            <tr key={s.sector}>
              <td>{s.label}</td>
              <td><span className={`badge state-${s.state.toLowerCase()}`}>{SECTOR_STATE_LABEL[s.state]}</span></td>
              <td className="small">could reach: {s.assessed_readiness.replace(/_/g, " ").toLowerCase()}<div className="dim">{s.reason}</div></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ContextPanel({ bundle }: { bundle: CountryBundle }) {
  const p = bundle.system.profile;
  return (
    <div>
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
                {m.note && <div className="dim">{m.note}</div>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {p.as_of_note && <p className="small dim">{p.as_of_note}</p>}
    </div>
  );
}

function SourcesPanel({ bundle }: { bundle: CountryBundle }) {
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
            const age = x.checked ? daysBetween(x.checked, today) : null;
            const late = age != null && x.stale_after_days != null && age > x.stale_after_days;
            return (
              <tr key={x.name}>
                <td>{x.name}</td>
                <td className="small">{x.role}</td>
                <td className="small dim">{x.licence}</td>
                <td className="small">
                  {x.checked ? fmtDate(x.checked) : "never"}
                  {x.cadence && <div className="dim">Publishes: {x.cadence}</div>}
                  {late && <div className="stale-flag">Past its {x.stale_after_days}-day limit: re-check before relying on it</div>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <h3 className="eyebrow">How far the event search got</h3>
      <p className="small dim">{s.research_log.note}</p>
      <table className="sector-table research-log">
        <thead><tr><th>Pass</th><th>Window searched</th><th>Status</th><th>Outcome</th></tr></thead>
        <tbody>
          {s.research_log.passes.map((p) => (
            <tr key={`${p.date}-${p.by}`}>
              <td className="small">{fmtDate(p.date)}<div className="dim">{p.by}</div></td>
              <td className="small">{fmtDate(p.window[0])} – {fmtDate(p.window[1])}<div className="dim">{p.scope}</div></td>
              <td className="small"><span className={`badge gate-${p.status === "complete" ? "met" : "partial"}`}>{p.status}</span>
                {p.status_reason && <div className="dim">{p.status_reason}</div>}</td>
              <td className="small">{Object.entries(p.outcome).map(([k, n]) => `${k.replace(/_/g, " ")} ${n}`).join(" · ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h3 className="eyebrow">Recovery evidence across the recorded events</h3>
      <ul className="small">
        {Object.entries(rec).map(([k, n]) => <li key={k}>{labelFor(RECOVERY_LABEL, k)}: {n}</li>)}
      </ul>
      {kinds.length > 0 && (
        <>
          <div className="small dim">Of the evidence found, by kind — these are different claims:</div>
          <ul className="small">{kinds.map(([k, n]) => <li key={k}>{labelFor(RECOVERY_KIND_LABEL, k)}: {n}</li>)}</ul>
        </>
      )}
      <h3 className="eyebrow">Known gaps</h3>
      <ul className="small">{s.research_gaps.map((g, i) => <li key={i}>{g}</li>)}</ul>
      <p className="small dim">Events were gathered by the open-source research passes above and reviewed
        against the inclusion threshold, source rules and a scope scan. Claims were not
        independently re-verified beyond the cited sources.
        {unrecorded > 0 && ` For ${unrecorded} of ${bundle.events.length} events the research lane did not record whether it read the cited sources.`}</p>
    </div>
  );
}

function MethodPanel({ bundle }: { bundle: CountryBundle }) {
  const s = bundle.system;
  const unmet = s.onboarding_gate.filter((g) => g.status !== "met").length;
  return (
    <div>
      <h2>Why no score</h2>
      <p className="small">{s.no_index_reason}</p>
      <p className="small">Reporting environment — {labelFor(ENVIRONMENT_LABEL, s.reporting_environment)}:
        {" "}{s.reporting_environment_text}</p>
      <h3 className="eyebrow">Onboarding gate</h3>
      <p className="small dim">
        {unmet > 0
          ? `Shown as a research preview: ${unmet} of ${s.onboarding_gate.length} items of the onboarding gate are only partly met.`
          : "Every item of the onboarding gate is met."}
      </p>
      <table className="sector-table">
        <tbody>
          {s.onboarding_gate.map((g) => (
            <tr key={g.item}>
              <td className="small">{g.item}. {g.label}</td>
              <td><span className={`badge gate-${g.status}`}>{g.status}</span></td>
              <td className="small dim">{g.note}</td>
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
      <p className="small">{s.geography.note}</p>
      {s.geography.rulings.length > 0 && (
        <ul className="small">{s.geography.rulings.map((r) => <li key={r.code}><span className="mono">{r.code}</span>: {r.note}</li>)}</ul>
      )}
      <p className="small dim">Audits: {s.audit_docs.join(", ")} in the project repository.</p>
    </div>
  );
}
