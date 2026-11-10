import { useEffect, useState } from "react";
import SystemSwitcher from "./SystemSwitcher";
import WorldContext from "./WorldContext";
import { DataQualityPanel, RecentEvidencePanel, laneChips } from "./GlobalPanels";
import {
  ENVIRONMENT_LABEL, READINESS_LABEL, labelFor, loadManifest, loadWorld,
  type Manifest, type ManifestSystem,
} from "./manifest";
import { navigate } from "./router";
import { fmtDate, fmtNum } from "../data";

/** The global home (iteration 14).
 *
 *  WHAT IT REFUSES TO SHOW. No event counts per system, no scores side by side, no ordering by
 *  any disruption figure. Six systems with six reporting environments cannot be compared on
 *  disruption, and a page of cards with a number on each is read as a league table whatever the
 *  caption says (GLOBAL_METHODOLOGY §6).
 *
 *  THREE LEVELS (iteration 18), kept apart: the world's national energy picture (context only),
 *  the six monitored systems, and recent evidence inside them. National energy data never mixes
 *  with disruption data on one scale.
 */

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

        <p className="home-lead">
          Five countries, plus the Russia, Belarus &amp; Crimea area, are systematically monitored for
          qualifying disruptions. Other countries are shown only for national energy context: an
          unmonitored country has no disruption record here, which is not the same as no disruptions.
        </p>

        <WorldContext world={world} worldError={error} manifest={manifest} />

        <h2 className="level-head">Monitored systems</h2>
        <section aria-label="Monitored systems" className="sys-cards">
          {manifest?.systems.map((s) => <SystemCard key={s.id} s={s} manifest={manifest} />)}
        </section>

        <RecentEvidencePanel />

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
        <DataQualityPanel />
        {manifest?.corpus && (
          <section className="panel global-note corpus-totals" aria-label="Country record, all five together">
            <h2 className="eyebrow">The country record so far, all five countries together</h2>
            <p className="small">
              {manifest.corpus.records} reported disruptions in {manifest.corpus.episodes} episodes;{" "}
              {manifest.corpus.independently_reviewed} independently reviewed ({manifest.corpus.blind_reviewed} blind
              by three reviewers). {manifest.corpus.records_with_observed_recovery} with a cited report that the
              facility or service came back at least in part ({manifest.corpus.records_reported_fully_back} of them
              fully); {manifest.corpus.records_with_recovery_estimate_only} with only an estimate. {manifest.corpus.registry_sources} registry sources. Research process across{" "}
              {manifest.corpus.research_lanes} source groups: {laneChips(manifest.corpus.research_lane_states ?? {})}.
            </p>
            <p className="small dim">{manifest.corpus.note}</p>
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
      <div className="small dim">Site rebuilt {fmtDate(s.as_of)}</div>
      <button className="ghost" onClick={() => navigate(s.id)}>Open {s.name}</button>
    </article>
  );
}
