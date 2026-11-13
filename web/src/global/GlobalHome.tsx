import { Suspense, lazy, useEffect, useRef, useState } from "react";
import SystemSwitcher from "./SystemSwitcher";
import StartHere from "./StartHere";
import WhatsNew from "./WhatsNew";
import { DataQualityPanel, RecentEvidencePanel, laneChips } from "./GlobalPanels";
import { GlobalNavBar, GlobalSearch, openGlossary } from "./GlobalNav";
import {
  ENVIRONMENT_LABEL, labelFor, loadDataQuality, loadManifest, loadWorld,
  type DataQuality, type Manifest, type ManifestSystem,
} from "./manifest";
import { loadContext, type EnergyContext } from "./context";
import { navigate, navigateGroup, navigateTo } from "./router";
import { prefetchOn } from "./prefetch";
import { PanelBoundary } from "../components/ViewBoundary";
import { dated, recordLine } from "./homeModel";
import { localISODate } from "../freshness";
import { Disclosure } from "./Disclosure";
import { RESEARCH_PREVIEW_DEFINITION, RESEARCH_PREVIEW_LABEL } from "./countryCopy";
import { fmtDate, fmtNum } from "../data";
import { readerText } from "./readerText";
import "../styles/home.css";

// The world map is below the fold and brings MapLibre with it: its own chunk, so the first screen
// (purpose, search, actions, systems) does not wait for a megabyte of map code.
const WorldContext = lazy(() => import("./WorldContext"));

/** The global home (iteration 14; first screen redesigned in iteration 21).
 *
 *  WHAT IT REFUSES TO SHOW. No event counts per system, no scores side by side, no ordering by
 *  any disruption figure. Systems with different reporting environments cannot be compared on
 *  disruption, and a page of cards with a number on each is read as a league table whatever the
 *  caption says (GLOBAL_METHODOLOGY §6).
 *
 *  THE ORDER OF THE PAGE. What this is and what to do next (purpose, search, four actions, the
 *  comparability caveat); how to read it (Start here); the indexed theatre, then the country
 *  systems in the manifest's alphabetical order; research and context state; recent published
 *  evidence; data freshness. The theatre leads because it is a different kind of system (the one
 *  with an index), not because of any figure.
 */

export default function GlobalHome() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [world, setWorld] = useState<GeoJSON.FeatureCollection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dq, setDq] = useState<DataQuality | null>(null);
  const [dqFailed, setDqFailed] = useState(false);
  const [groupFilter, setGroupFilter] = useState("all");
  const [ctx, setCtx] = useState<EnergyContext | null>(null);
  const [ctxError, setCtxError] = useState<string | null>(null);
  // The first screen waits until the manifest and the data-quality summary have each arrived or
  // failed: each adds lines to it (the cards' record and research dates), and drawing them as they
  // landed moved the whole screen (layout shift 0.86 before iteration 21). The world map is below
  // the fold, draws into a box of fixed size, and does not wait.
  const [manifestSettled, setManifestSettled] = useState(false);
  const [dqSettled, setDqSettled] = useState(false);
  const searchRef = useRef<HTMLInputElement | null>(null);
  // The reader's own calendar day: ages are computed here, never shipped precomputed.
  const today = localISODate(new Date());

  useEffect(() => {
    let live = true;
    loadManifest().then((m) => { if (live) setManifest(m); })
      .catch((e) => { if (live) setError(String(e)); })
      .finally(() => { if (live) setManifestSettled(true); });
    loadDataQuality().then((d) => { if (live) setDq(d); })
      .catch(() => { if (live) setDqFailed(true); })
      .finally(() => { if (live) setDqSettled(true); });
    loadContext().then((c) => { if (live) setCtx(c); })
      .catch((e) => { if (live) setCtxError(e instanceof Error ? e.message : String(e)); });
    loadWorld().then((w) => { if (live) setWorld(w); }).catch((e) => {
      if (live) setError(String(e));
    });
    return () => { live = false; };
  }, []);

  useEffect(() => { document.title = "Energy Disruption Monitor — overview"; }, []);

  const groups = Object.entries(manifest?.groups ?? {});
  const gulf = groups.find(([, g]) => g.slug && g.context)?.[1] ?? null;
  const filterGroup = groupFilter === "all" ? null : manifest?.groups?.[groupFilter] ?? null;
  const inFilter = (s: ManifestSystem) => !filterGroup || filterGroup.members.includes(s.id);
  const theatre = manifest?.systems.find((s) => s.kind === "theatre") ?? null;
  // The manifest's own (alphabetical) order. Never re-sorted here.
  const countries = manifest?.systems.filter((s) => s.kind === "country" && inFilter(s)) ?? [];
  const lastPass = new Map((dq?.systems ?? []).map((s) => [s.system_id, s.last_systematic_pass]));

  return (
    <div className="global-page home-page">
      <header className="home-head">
        <GlobalNavBar trail={[]} search={false} extra={<SystemSwitcher current={null} />} />
      </header>

      {!(manifestSettled && dqSettled) ? (
        <main className="global-main"><p className="dim" role="status">Loading…</p></main>
      ) : (
      <main className="global-main">
        <section className="home-hero" aria-labelledby="home-title">
          <h1 id="home-title" className="home-title">Energy Disruption Monitor</h1>
          <p className="home-purpose">
            What public sources report about disruption to energy infrastructure, by region, with every gap and
            limit stated. One system has an index; the others are reviewed evidence and context, with no score.
          </p>
          <GlobalSearch inputRef={searchRef} />
          <nav className="home-actions" aria-label="Main actions">
            <button type="button" className="home-action" onClick={() => searchRef.current?.focus()}>Search systems</button>
            {gulf?.slug
              ? <a className="home-action" href={`?group=${gulf.slug}`} onClick={(e) => { e.preventDefault(); navigateGroup(gulf.slug as string); }}>Explore the {gulf.label} →</a>
              : <span className="home-action disabled">Regional overview loading…</span>}
            <a className="home-action" href="?compare=" onClick={(e) => { e.preventDefault(); navigateTo("?compare="); }}>Compare systems →</a>
            <a className="home-action primary" href="?sys=ru" onClick={(e) => { e.preventDefault(); navigate("ru"); }}>Russia theatre (indexed) →</a>
          </nav>
          {manifest && <p className="comparability compact" role="note">{manifest.comparability_statement}</p>}
          {error && !manifest && (
            <p className="warn-text" role="alert">
              The list of monitored systems could not be loaded ({error}). The Russia, Belarus &amp; Crimea view is still
              available: <a href="?sys=ru">open it</a>.
            </p>
          )}
        </section>

        <StartHere gulfSlug={gulf?.slug ?? null} gulfLabel={gulf?.label ?? null} />

        <PanelBoundary label="The list of monitored systems">
        <section aria-label="Monitored systems" className="home-systems">
          <div className="home-section-head">
            <h2 className="home-h2">Monitored systems</h2>
            {groups.length > 0 && (
              <div className="map-control-row">
                <label className="small">Show{" "}
                  <select aria-label="Filter the system cards by group" value={groupFilter} onChange={(e) => setGroupFilter(e.target.value)}>
                    <option value="all">all systems</option>
                    {groups.map(([id, g]) => <option key={id} value={id}>{g.label}{g.kind === "membership" ? " members" : " states"}</option>)}
                  </select>
                </label>
                {groups.filter(([, g]) => g.slug && g.context).map(([id, g]) => (
                  <button key={id} className="ghost" onClick={() => navigateGroup(g.slug as string)}>Open the {g.label} overview</button>
                ))}
                {filterGroup && <span className="small dim">{filterGroup.note}</span>}
              </div>
            )}
          </div>
          {theatre && inFilter(theatre) && <TheatreEntry s={theatre} today={today} />}
          <div className="sys-cards home-cards">
            {manifest && countries.map((s) => (
              <SystemCard key={s.id} s={s} manifest={manifest} lastPass={lastPass.get(s.id)} today={today} />
            ))}
          </div>
        </section>
        </PanelBoundary>

        <section className="home-research" aria-labelledby="research-head">
          <h2 id="research-head" className="home-h2">Research and national context</h2>
          <p className="small dim home-lead">
            The world map is coloured by national energy statistics, for background only; a thick outline marks a
            monitored system. Other countries are shown only for national energy context: an unmonitored country has no
            disruption record here, which is not the same as no disruptions.
          </p>
          <PanelBoundary label="The world energy map">
            <Suspense fallback={<div className="simple-map placeholder">Loading map…</div>}>
              <WorldContext world={world} worldError={error} manifest={manifest} ctx={ctx} ctxError={ctxError} />
            </Suspense>
          </PanelBoundary>
        </section>

        <PanelBoundary label="Recent evidence">
          <RecentEvidencePanel />
        </PanelBoundary>

        <PanelBoundary label="What's new in the data">
          <WhatsNew />
        </PanelBoundary>

        <PanelBoundary label="Data quality">
          <DataQualityPanel data={dq} failed={dqFailed} manifest={manifest} today={today} />
        </PanelBoundary>

        {manifest && (
          <section className="panel global-note" aria-labelledby="why-head">
            <h2 id="why-head" className="home-h2">Why these systems, and how this works</h2>
            <p>
              {manifest.selection.rule} Source:{" "}
              <a href={manifest.selection.source_url} target="_blank" rel="noreferrer">
                {manifest.selection.source}
              </a>.
            </p>
            {manifest.selection.regional_rule && <p>{readerText(manifest.selection.regional_rule)}</p>}
            <p className="small">{manifest.selection.caveat}</p>
            <p className="small">
              The original Russia, Belarus &amp; Crimea theatre is the only system with an index. The countries are shown
              with reported major disruptions and energy-system context: the index's weights and recovery model were built
              for a strike campaign and do not transfer.{" "}
              <button className="linklike" type="button" onClick={() => openGlossary("how-it-works")}>How this works, in six steps</button>
            </p>
          </section>
        )}
        {manifest?.corpus && (
          <section className="panel global-note corpus-totals" aria-label="Country record, all countries together">
            <h2 className="eyebrow">The country record so far, all {manifest.corpus.countries} countries together</h2>
            <p className="small">
              {manifest.corpus.records} reported disruptions in {manifest.corpus.episodes} episodes;{" "}
              {manifest.corpus.independently_reviewed} independently reviewed ({manifest.corpus.blind_reviewed} blind
              by three reviewers). {manifest.corpus.records_with_observed_recovery} with a cited report that the
              facility or service came back at least in part ({manifest.corpus.records_reported_fully_back} of them
              fully); {manifest.corpus.records_with_recovery_estimate_only} with only an estimate. Research process across{" "}
              {manifest.corpus.research_lanes} source groups: {laneChips(manifest.corpus.research_lane_states ?? {})}.
              {" "}{manifest.corpus.registry_sources} sources are on the countries' check lists: the regulators, ministries,
              operators and other publishers that are re-read on a schedule.
            </p>
            <p className="small dim">{manifest.corpus.note}</p>
          </section>
        )}
      </main>
      )}
    </div>
  );
}

/** The one indexed system, ahead of the countries because it is a different kind of view. */
function TheatreEntry({ s, today }: { s: ManifestSystem; today: string }) {
  return (
    <article className="theatre-entry panel" aria-label={s.name}>
      <div className="theatre-entry-text">
        <div className="eyebrow">Indexed system · the only one with a score</div>
        <h2>{s.name}</h2>
        {s.headline && (
          <p className="theatre-headline">
            <span className="num">{fmtNum(s.headline.value, 1)}</span>{" "}
            <span>{s.headline.label}, {fmtDate(s.headline.as_of)}</span>
            <span className="small dim"> (scale 0 to 100) — {s.headline.meaning}</span>
          </p>
        )}
        {/* The number sits above a row of cards that have none. Said here, beside it, so the row
            does not read as a scale with one value filled in. */}
        <p className="small dim theatre-entry-alone">
          Built for this area alone. No country below has an index, so there is nothing on this page to set
          this number against.
        </p>
        <div className="small dim">Reporting: {labelFor(ENVIRONMENT_LABEL, s.reporting_environment)} · {dated("Data as of", s.as_of, today)}</div>
      </div>
      <button className="home-action primary" onClick={() => navigate(s.id)} {...prefetchOn(s.id)}>Open {s.name}</button>
    </article>
  );
}

/** A country system. Name, kind of view, "No index", research stage, record and research dates,
 *  reporting environment. Never a count, a score, a held number or a status colour. */
function SystemCard({ s, manifest, lastPass, today }: {
  s: ManifestSystem; manifest: Manifest; lastPass: string | null | undefined; today: string;
}) {
  const record = recordLine(s.record_reviewed, today);
  const region = Object.values(manifest.groups ?? {}).find((g) => g.slug && g.context && g.members.includes(s.id));
  return (
    <article className="sys-card panel home-card" aria-label={s.name}>
      <h2>{s.name}</h2>
      <div className="small">Country evidence system · <strong>No index</strong></div>
      <div className="home-tags">
        {/* Tap disclosures, not hover titles: a touch screen has no hover. */}
        {s.maturity === "research_preview" && (
          // The country page's definition, in the cards' neutral tag style: no status colour on a card.
          <Disclosure label={RESEARCH_PREVIEW_LABEL} text={RESEARCH_PREVIEW_DEFINITION} className="home-tag home-tag-preview" />
        )}
        {region && <span className="home-tag home-tag-region">{region.label}</span>}
        {s.campaign_restricted && (
          <Disclosure label="Publication safeguards" className="home-tag home-tag-safeguard"
            text="While attacks on energy facilities are being reported, some detail, such as a facility's later status, is not published." />
        )}
      </div>
      {record && <div className="small">{record}</div>}
      <div className="small dim">{lastPass ? dated("Last researched", lastPass, today) : lastPass === null ? "No systematic search yet" : ""}</div>
      <div className="small dim">
        Reporting: <Disclosure label={labelFor(ENVIRONMENT_LABEL, s.reporting_environment)}
          text={manifest.reporting_environments[s.reporting_environment] ?? ""} className="linklike" />
      </div>
      <button className="ghost" onClick={() => navigate(s.id)} {...prefetchOn(s.id)}>Open {s.name}</button>
    </article>
  );
}
