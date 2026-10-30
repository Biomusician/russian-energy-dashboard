import { useEffect, useState } from "react";
import SimpleMap from "./SimpleMap";
import SystemSwitcher from "./SystemSwitcher";
import {
  ENVIRONMENT_LABEL, READINESS_LABEL, labelFor, loadManifest, loadWorld,
  type Manifest, type ManifestSystem,
} from "./manifest";
import { navigate } from "./router";
import { fmtDate, fmtNum } from "../data";

/** The global home (iteration 14).
 *
 *  WHAT IT REFUSES TO SHOW. No event counts, no scores side by side, no ordering by any figure.
 *  Six systems with six reporting environments cannot be compared on disruption, and a page of
 *  cards with a number on each is read as a league table whatever the caption says
 *  (GLOBAL_METHODOLOGY §6). Each card says what that system's evidence supports and nothing a
 *  reader could rank. Every monitored system is drawn in the same colour: the map shows WHERE is
 *  monitored, not how much happened there.
 */

const MONITORED = "#1e5560";
const OCCUPIED = "#5b4a1e";
const OTHER = "#141c25";

export default function GlobalHome() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [world, setWorld] = useState<GeoJSON.FeatureCollection | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ctl = new AbortController();
    loadManifest().then(setManifest).catch((e) => setError(String(e)));
    loadWorld(ctl.signal).then(setWorld).catch((e) => {
      if (!ctl.signal.aborted) setError(String(e));
    });
    return () => ctl.abort();
  }, []);

  useEffect(() => { document.title = "Energy Disruption Monitor — overview"; }, []);

  return (
    <div className="global-page">
      <header className="global-head">
        <div>
          <h1 className="ribbon-title">Energy Disruption Monitor</h1>
          <div className="ribbon-sub">
            Publicly reported disruption to energy infrastructure, aggregated to first-level
            administrative regions · open sources only
          </div>
        </div>
        <SystemSwitcher current={null} />
      </header>

      <main className="global-main">
        {manifest && (
          <p className="comparability" role="note">{manifest.comparability_statement}</p>
        )}
        {error && !manifest && (
          <p className="warn-text" role="alert">
            The list of monitored systems could not be loaded ({error}). The Russia, Belarus &amp;
            Crimea view is still available: <a href="?sys=ru">open it</a>.
          </p>
        )}

        <section className="global-map-wrap" aria-label="Monitored systems map">
          {world ? (
            <SimpleMap
              data={world}
              bounds={[-170, -50, 179, 78]}
              idProp="system_id"
              fill={["case",
                ["==", ["get", "status"], "occupied"], OCCUPIED,
                ["!=", ["get", "system_id"], null], MONITORED,
                OTHER]}
              pickable={(p) => !!p.system_id}
              onPick={(id) => id && navigate(id)}
              ariaLabel="World map. Monitored systems are highlighted; select one to open it."
              attribution="Boundaries: Natural Earth (public domain). Crimea is drawn as Ukrainian territory under Russian occupation."
            />
          ) : (
            <div className="simple-map placeholder">{error ? "Map unavailable" : "Loading map…"}</div>
          )}
          <div className="map-legend-mini">
            <span><i style={{ background: MONITORED }} /> monitored system (same colour for all — not a measure)</span>
            <span><i style={{ background: OCCUPIED }} /> Crimea: Ukrainian, occupied; monitored within the Russia theatre</span>
          </div>
        </section>

        <section aria-label="Monitored systems" className="sys-cards">
          {manifest?.systems.map((s) => <SystemCard key={s.id} s={s} manifest={manifest} />)}
        </section>

        {manifest && (
          <section className="panel global-note">
            <div className="eyebrow">Why these systems</div>
            <p>
              {manifest.selection.rule} Source:{" "}
              <a href={manifest.selection.source_url} target="_blank" rel="noreferrer">
                {manifest.selection.source}
              </a>.
            </p>
            <p className="small">{manifest.selection.caveat}</p>
            <p className="small">
              The original Russia, Belarus &amp; Crimea theatre is the only system with an index.
              The five countries are shown with reported major disruptions and energy-system
              context: the index's weights and recovery model were built for a strike campaign
              and do not transfer.
            </p>
          </section>
        )}
      </main>
    </div>
  );
}

function SystemCard({ s, manifest }: { s: ManifestSystem; manifest: Manifest }) {
  return (
    <article className="sys-card panel" aria-label={s.name}>
      <h2>{s.name}</h2>
      <div className={`badge readiness-${s.evidence_readiness.toLowerCase()}`}>
        {READINESS_LABEL[s.evidence_readiness]}
      </div>
      {s.headline ? (
        <div className="sys-headline">
          <span className="num">{fmtNum(s.headline.value, 1)}</span>{" "}
          <span className="small">{s.headline.label} · {fmtDate(s.headline.as_of)}</span>
          <div className="small dim">{s.headline.meaning}</div>
        </div>
      ) : (
        <div className="sys-headline none">
          <span className="small">No index — reported events and context only</span>
        </div>
      )}
      <div className="small dim" title={manifest.reporting_environments[s.reporting_environment]}>
        Reporting: {labelFor(ENVIRONMENT_LABEL, s.reporting_environment)}
      </div>
      <div className="small dim">Data as of {fmtDate(s.as_of)}</div>
      <button className="ghost" onClick={() => navigate(s.id)}>Open {s.name}</button>
    </article>
  );
}
