import { useEffect, useRef, useState } from "react";
import WhatsNew from "./WhatsNew";
import { DataQualityPanel, RecentEvidencePanel } from "./GlobalPanels";
import { GlobalNavBar, GlobalSearch, goWhatsNew, openGlossary, WHATS_NEW_ID } from "./GlobalNav";
import { loadDataQuality, loadManifest, loadWorld, type DataQuality, type Manifest } from "./manifest";
import { loadContext, type EnergyContext } from "./context";
import { PanelBoundary } from "../components/ViewBoundary";
import { laneLine } from "./laneCoverage";
import { localDayOf, localISODate } from "../freshness";
import { fmtDate } from "../data";
import { readerText } from "./readerText";
import HomeStage from "./HomeStage";
import { WorldProfile } from "./NationalContext";
import { openFromHome, readHomeState, selectOnHome } from "./homeSelection";
import "../styles/home.css";

/** The global home (iteration 14; map-first since iteration 23).
 *
 *  WHAT THE FIRST SCREEN ANSWERS. What this is (one sentence), where one can explore (the map and,
 *  beside it, the same places as text), the one index's headline, what other evidence exists (the
 *  Impact Atlas row) and when the data was built. Everything an analyst needs beyond that is one
 *  click away below, each part collapsed: recent evidence, what changed, data quality, why these
 *  systems, the country record and the national figures table.
 *
 *  WHAT IT REFUSES TO SHOW. No event counts per system, no scores side by side, no ordering by any
 *  disruption figure, no maturity label on a list of places, and no map colour for impact records:
 *  systems with different reporting environments cannot be compared on disruption, and a list or a
 *  map with a figure on each is read as a league table whatever the caption says
 *  (GLOBAL_METHODOLOGY §6).
 *
 *  WHAT THE FIRST SCREEN WAITS FOR. The manifest only. The map is its own chunk and draws into a
 *  box of fixed size, so it never moves the page and never holds up the panel or the search; the
 *  data-quality summary, the recent list and the national figures load when their part is opened.
 */
export default function GlobalHome() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [world, setWorld] = useState<GeoJSON.FeatureCollection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [worldError, setWorldError] = useState<string | null>(null);
  const [manifestSettled, setManifestSettled] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const searchRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    let live = true;
    loadManifest().then((m) => { if (live) setManifest(m); })
      .catch((e) => { if (live) setError(String(e)); })
      .finally(() => { if (live) setManifestSettled(true); });
    loadWorld().then((w) => { if (live) setWorld(w); }).catch((e) => { if (live) setWorldError(String(e)); });
    return () => { live = false; };
  }, []);

  useEffect(() => { document.title = "Energy Disruption Monitor — overview"; }, []);

  const theatre = manifest?.systems.find((s) => s.kind === "theatre") ?? null;
  const dataDay = theatre?.as_of ?? localDayOf(manifest?.build_time);
  const leave = (href: string, ret: string) => (e: React.MouseEvent) => {
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    openFromHome(href, readHomeState().focus, ret);
  };

  return (
    <div className="global-page home-page">
      <header className="home-head">
        {/* No system picker here: the panel below is the same list, visible. Other views keep it. */}
        <GlobalNavBar trail={[]} search={false} />
      </header>

      {!manifestSettled ? (
        <main className="global-main home-main"><p className="dim" role="status">Loading…</p></main>
      ) : (
      <main className="global-main home-main">
        <section className="home-strip" aria-labelledby="home-title">
          <div className="home-strip-text">
            <h1 id="home-title" className="home-title">Energy Disruption Monitor</h1>
            <p className="home-purpose">
              What public sources report about disruption to energy infrastructure, by region, with every gap and limit
              stated. Choose a place on the map or from the list.
            </p>
            <p className="home-meta small">
              {dataDay && <>Data as of {fmtDate(dataDay)} · rebuilt daily · </>}
              <a href={`#${WHATS_NEW_ID}`} onClick={(e) => { e.preventDefault(); goWhatsNew(); }}>What's new</a>
              {" · "}
              <a className="home-newhere" href="?view=help#start-here" onClick={leave("?view=help#start-here", "newhere")} data-ret="newhere">New here? How to use this dashboard</a>
            </p>
          </div>
          <GlobalSearch inputRef={searchRef} onPreview={setPreview} />
        </section>

        {error && !manifest && (
          <p className="warn-text" role="alert">
            The list of monitored systems could not be loaded ({error}). The Russia, Belarus &amp; Crimea view is still
            available: <a href="?sys=ru">open it</a>.
          </p>
        )}

        {manifest && <HomeStage manifest={manifest} world={world} worldError={worldError} preview={preview} />}

        <div className="home-below">
          <Fold title="Recent published evidence" id="fold-recent">
            <PanelBoundary label="Recent evidence"><RecentEvidencePanel /></PanelBoundary>
          </Fold>
          {/* Mounted while closed, so the site bar's "What's new" can open it and move focus there. */}
          <Fold title="What's new in the data" id="fold-whats-new" eager openOnHash={`#${WHATS_NEW_ID}`}>
            <PanelBoundary label="What's new in the data"><WhatsNew /></PanelBoundary>
          </Fold>
          <Fold title="Data freshness and quality" id="fold-quality">
            <PanelBoundary label="Data quality"><QualityFold manifest={manifest} /></PanelBoundary>
          </Fold>
          {manifest && (
            <Fold title="Why these systems, and how this works" id="fold-why" openOnHash="#why-head">
              <section className="panel global-note" aria-labelledby="why-head">
                <h2 id="why-head" className="home-h2">Why these systems, and how this works</h2>
                <p>
                  {readerText(manifest.selection.rule)} Source:{" "}
                  <a href={manifest.selection.source_url} target="_blank" rel="noreferrer">
                    {manifest.selection.source}
                  </a>.
                </p>
                {manifest.selection.regional_rule && <p>{readerText(manifest.selection.regional_rule)}</p>}
                <p className="small">{readerText(manifest.selection.caveat)}</p>
                <p className="small">
                  The original Russia, Belarus &amp; Crimea theatre is the only system with an index. The countries are shown
                  with reported major disruptions and energy-system context: the index's weights and recovery model were built
                  for a strike campaign and do not transfer.{" "}
                  <button className="linklike" type="button" onClick={() => openGlossary("how-it-works")}>How this works, in six steps</button>
                </p>
                <p className="small comparability-line">{manifest.comparability_statement}</p>
              </section>
            </Fold>
          )}
          {manifest?.corpus && (
            <Fold title="The country record so far" id="fold-corpus">
              <section className="panel global-note corpus-totals" aria-label="Country record, all countries together">
                <h2 className="eyebrow">The country record so far, all {manifest.corpus.countries} countries together</h2>
                <p className="small">
                  {manifest.corpus.records} reported disruptions in {manifest.corpus.episodes} episodes. Research process:{" "}
                  {laneLine(manifest.corpus.research_lane_states ?? {}, manifest.corpus.research_lanes)}
                  {" "}{manifest.corpus.registry_sources} sources are on the countries' check lists: the regulators, ministries,
                  operators and other publishers that are re-read on a schedule.
                </p>
                {/* Iteration 23: the recovery and review sub-totals are gone from here. Nearly all of them
                    come from the systems with regulatory reporting, so beside "all countries together"
                    they read as a rate for every country. Each country page keeps its own. */}
                <p className="small">{reportingLine(manifest)}</p>
                <p className="small dim">{readerText(manifest.corpus.note)}</p>
              </section>
            </Fold>
          )}
          <Fold title="National energy figures table" id="fold-national">
            <PanelBoundary label="National energy figures"><NationalFold manifest={manifest} world={world} /></PanelBoundary>
          </Fold>
        </div>
      </main>
      )}
    </div>
  );
}

/** Which country systems have regulatory outage reporting, by name, from the manifest: a total
 *  across countries mostly says how much each one reports. */
function reportingLine(m: Manifest): string {
  const regulated = m.systems.filter((s) => s.kind === "country" && s.reporting_environment.endsWith("_regulatory")).map((s) => s.name);
  const list = regulated.length > 1 ? `${regulated.slice(0, -1).join(", ")} and ${regulated[regulated.length - 1]}` : regulated[0] ?? "";
  return `These totals mostly reflect how much each country reports publicly, not how much happened.${list
    ? ` ${list} ${regulated.length > 1 ? "have" : "has"} some mandatory outage reporting; the others rely on company, ministry and press statements, so they add far fewer records.` : ""}`;
}

/** A collapsed part of the home below the first screen. Its content is mounted the first time it
 *  is opened (so a closed part fetches nothing), unless `eager`. `openOnHash` opens it when the
 *  address points inside it. */
function Fold({ title, id, children, eager = false, openOnHash }: {
  title: string; id: string; children: React.ReactNode; eager?: boolean; openOnHash?: string;
}) {
  const ref = useRef<HTMLDetailsElement | null>(null);
  const [opened, setOpened] = useState(() => !!openOnHash && window.location.hash === openOnHash);
  useEffect(() => { if (opened && ref.current && !ref.current.open) ref.current.open = true; }, [opened]);
  return (
    <details ref={ref} className="home-fold" id={id} onToggle={() => { if (ref.current?.open) setOpened(true); }}>
      <summary><span className="home-fold-title">{title}</span></summary>
      {(opened || eager) && <div className="home-fold-body">{children}</div>}
    </details>
  );
}

function QualityFold({ manifest }: { manifest: Manifest | null }) {
  const [dq, setDq] = useState<DataQuality | null>(null);
  const [failed, setFailed] = useState(false);
  // The reader's own calendar day: ages are computed here, never shipped precomputed.
  const today = localISODate(new Date());
  useEffect(() => {
    let live = true;
    loadDataQuality().then((d) => { if (live) setDq(d); }).catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, []);
  return <DataQualityPanel data={dq} failed={failed} manifest={manifest} today={today} />;
}

function NationalFold({ manifest, world }: { manifest: Manifest | null; world: GeoJSON.FeatureCollection | null }) {
  const [ctx, setCtx] = useState<EnergyContext | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let live = true;
    loadContext().then((c) => { if (live) setCtx(c); }).catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, []);
  // A country drawn both with and without a system id is monitored in part.
  const partly = new Set<string>();
  const seen = new Map<string, Set<boolean>>();
  for (const f of world?.features ?? []) {
    const p = f.properties as { a3?: string; system_id?: string | null; status?: string } | null;
    if (!p?.a3 || p.status === "occupied") continue;
    seen.set(p.a3, (seen.get(p.a3) ?? new Set()).add(!!p.system_id));
  }
  for (const [a3, s] of seen) if (s.size > 1) partly.add(a3);
  if (failed) return <p className="warn-text small" role="alert">Global energy context unavailable. The monitored systems are not affected.</p>;
  if (!ctx) return <p className="small dim" role="status">Loading…</p>;
  return (
    <WorldProfile ctx={ctx} partly={partly} tableOpen
      onContext={(a3) => { selectOnHome(a3); document.querySelector(".home-stage")?.scrollIntoView({ block: "start" }); }}
      systemNames={Object.fromEntries((manifest?.systems ?? []).map((s) => [s.id, s.name]))} />
  );
}
