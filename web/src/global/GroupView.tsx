import { useEffect, useMemo, useRef, useState } from "react";
import type maplibregl from "maplibre-gl";
import SimpleMap, { withoutHighlight } from "./SimpleMap";
import SystemSwitcher from "./SystemSwitcher";
import { fmtValue } from "./context";
import { GROUP_BRIEF_FIT_PADDING, composeGroupFrame } from "./groupExport";
import {
  FILTERED, MEMBER_RAMP, NEUTRAL, NO_DATA, OTHER, ZERO, groupFill, memberColour, membersAlphabetical, metricFacts, specialValues,
} from "./groupMap";
import {
  ENVIRONMENT_LABEL, groupBySlug, languageNames, labelFor, laneChips, loadGroupContext, loadManifest, loadWorld,
  type GroupContext, type GroupSystem, type Manifest, type RecentEpisode,
} from "./manifest";
import { navigate } from "./router";
import { prefetchOn } from "./prefetch";
import { PanelBoundary } from "../components/ViewBoundary";
import { Disclosure, ResearchPreviewBadge } from "./Disclosure";
import { downloadBlob, exportMapPng } from "../mapExport";
import { fmtDate } from "../data";
import { readerText } from "./readerText";
import { collapseCovered, isCovered } from "./homeModel";
import { CountryLink, CoveredRunItem, fmtEpisodeDate } from "./feedItems";
import "../styles/gulf.css";
import { GlobalNavBar } from "./GlobalNav";

/** A regional overview (iteration 19): the Gulf.
 *
 *  A REGIONAL ENERGY PICTURE, NOT A TARGET SET. Everything on this page is a country: its annual
 *  national energy figures, whether it is monitored, how far its research has got, and its
 *  reviewed historical events in date order. There is no facility layer, no route, no strait, no
 *  shipping, and no ordering of countries by anything but name.
 *
 *  The first screen is the product: what the view is, the members, the map and the one control
 *  that colours it. The longer statements follow the map, one click from the caveat line above it.
 */

type Box = [number, number, number, number];

/** The box that holds every member, from the manifest. A typed-in box cropped two members on a
 *  tall phone, and would be a country list in the frontend by another name. */
function unionBounds(boxes: Box[]): Box | null {
  if (!boxes.length) return null;
  const pad = 1;
  return [Math.min(...boxes.map((b) => b[0])) - pad, Math.min(...boxes.map((b) => b[1])) - pad,
          Math.max(...boxes.map((b) => b[2])) + pad, Math.max(...boxes.map((b) => b[3])) + pad];
}

/** The brief's map: no reader marks, and every member coloured whatever the page's membership
 *  filter shows, because the brief's rows list every member and its key names only the five classes. */
function briefStyle(style: maplibregl.StyleSpecification, ctx: GroupContext, metricId: string): maplibregl.StyleSpecification {
  const clean = withoutHighlight(style);
  const fill = groupFill(ctx.systems, metricId, () => true) as maplibregl.ExpressionSpecification;
  return { ...clean, layers: clean.layers.map((l) => (l.id === "fill" && l.type === "fill" ? { ...l, paint: { ...l.paint, "fill-color": fill } } : l)) };
}

function EpisodeItem({ ep }: { ep: RecentEpisode }) {
  const covered = isCovered(ep);
  return (
    <li className="feed-item">
      <div className="event-head">
        <span className="mono small">{fmtEpisodeDate(ep)}</span>
        <CountryLink id={ep.system_id} name={ep.country} />
        <span className="small dim">{ep.classes.join(", ")} · {ep.causes.join(", ")}</span>
      </div>
      {covered && <div className="small dim">Published under active-campaign safeguards — see the country page.</div>}
      {ep.episode_name && <div className="small"><strong>{ep.episode_name}</strong> <span className="dim">({ep.records} records, one episode)</span></div>}
      <ul className="lane-list small">
        {ep.members.map((mm, i) => (
          <li key={i}><span className="dim">{mm.region}: </span>
            {mm.withheld ? <span className="dim">Not summarised in this list while an attack campaign is active or recent. The country page gives the effect reported at the time; later status is not published anywhere.</span> : mm.effect_on_country_page ? <span className="dim">Effect: on the country page.</span> : (mm.effect ?? <span className="dim">no effect text</span>)}
          </li>
        ))}
      </ul>
    </li>
  );
}

function memberships(s: GroupSystem): string {
  return `${s.gcc_member ? "GCC member" : "not a GCC member"} · ${s.opec_member ? "OPEC member" : "not an OPEC member"}`;
}

export default function GroupView({ id }: { id: string }) {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [ctx, setCtx] = useState<GroupContext | null>(null);
  const [ctxFailed, setCtxFailed] = useState(false);
  const [world, setWorld] = useState<GeoJSON.FeatureCollection | null>(null);
  const [worldFailed, setWorldFailed] = useState(false);
  const [metric, setMetric] = useState<string | null>(null);
  const [subset, setSubset] = useState<"all" | "gcc" | "opec">("all");
  const [hover, setHover] = useState<string | null>(null);
  // The member the reader is pointing at (list or map) and the one they chose. Screen state only:
  // neither reaches the brief.
  const [pointA3, setPointA3] = useState<string | null>(null);
  const [selA3, setSelA3] = useState<string | null>(null);
  const [exportMsg, setExportMsg] = useState<string | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    let live = true;
    loadManifest().then((m) => {
      if (!live) return;
      setManifest(m);
      const found = groupBySlug(m, id);
      // The manifest names the context file; the view never builds a path from the URL.
      if (found?.group.context) {
        loadGroupContext(found.group.context).then((c) => { if (live) setCtx(c); })
          .catch(() => { if (live) setCtxFailed(true); });
      }
    }).catch(() => { if (live) setCtxFailed(true); });
    loadWorld().then((w) => { if (live) setWorld(w); }).catch(() => { if (live) setWorldFailed(true); });
    return () => { live = false; };
  }, [id]);

  const group = manifest ? groupBySlug(manifest, id)?.group : undefined;
  useEffect(() => { document.title = `Energy Disruption Monitor — ${group?.label ?? "regional"} overview`; }, [group]);

  // The map is coloured only once a reader chooses a metric; until then it is geography. The table,
  // the regional total and the brief still describe a metric, the first one, so they have one.
  const colourBy = metric && ctx?.metrics[metric] ? metric : null;
  const metricId = colourBy ?? (ctx ? Object.keys(ctx.metrics)[0] : null);
  const m = ctx && metricId ? ctx.metrics[metricId] : null;
  const facts = ctx && colourBy ? metricFacts(ctx, colourBy) : null;
  const inSubset = (s: GroupSystem) => subset === "all" || (subset === "gcc" ? s.gcc_member : s.opec_member);
  const shown = useMemo(() => (ctx?.systems ?? []).filter(inSubset), [ctx, subset]);  // eslint-disable-line react-hooks/exhaustive-deps
  const listed = useMemo(() => membersAlphabetical(shown), [shown]);
  const byA3 = useMemo(() => new Map((ctx?.systems ?? []).map((s) => [s.a3, s])), [ctx]);
  const boundsOf = useMemo(() => new Map((manifest?.systems ?? []).filter((s) => s.bounds).map((s) => [s.id, s.bounds as Box])), [manifest]);

  const fill = useMemo(
    () => (ctx ? groupFill(ctx.systems, colourBy, inSubset) : OTHER) as maplibregl.ExpressionSpecification | string,
    [ctx, colourBy, subset]);  // eslint-disable-line react-hooks/exhaustive-deps
  const special = ctx && colourBy ? specialValues(ctx.systems, colourBy, inSubset) : null;

  const memberA3 = (ctx?.systems ?? []).map((s) => s.a3);
  const bounds = useMemo(() => {
    const ids = new Set((ctx?.systems ?? []).map((s) => s.system_id));
    return unionBounds((manifest?.systems ?? []).filter((s) => ids.has(s.id) && s.bounds).map((s) => s.bounds!));
  }, [ctx, manifest]);
  const region = ctx && metricId ? ctx.region[metricId] : null;
  const subsetNote = subset === "gcc" ? ctx?.memberships.gcc.note : subset === "opec" ? ctx?.memberships.opec.note : ctx?.note;

  // A member the filter has just set aside is no longer chosen.
  const sel = selA3 && shown.some((s) => s.a3 === selA3) ? byA3.get(selA3) ?? null : null;

  const describe = (s: GroupSystem) => (colourBy && m ? `${s.name}: ${fmtValue(s.values[colourBy], m.unit)} (${m.year}, national total)` : s.name);

  const zoomTo = (s: GroupSystem) => {
    const b = boundsOf.get(s.system_id);
    // Only the manifest's own box for the country. No box, no zoom: a guessed frame is invented geometry.
    if (b) mapRef.current?.fitBounds(b, { padding: 48, maxZoom: 7 });
  };
  const choose = (s: GroupSystem) => {
    if (sel?.a3 === s.a3) { setSelA3(null); return; }
    setSelA3(s.a3);
    zoomTo(s);
  };
  const resetView = () => { if (bounds) mapRef.current?.fitBounds(bounds, { padding: 24 }); };

  const runExport = async () => {
    const map = mapRef.current;
    if (!map || !ctx || !m || !metricId || !bounds) { setExportMsg("The map is not ready yet."); return; }
    // A brief names the metric its colours show; an uncoloured map has none to name.
    if (!colourBy) { setExportMsg("Choose a metric under \"Colour the map by\" first: the brief describes the colours it shows."); return; }
    try {
      // The brief frames the whole group and drops the reader's selection: a highlighted member in
      // an image that travels alone would read as the one that matters.
      const res = await exportMapPng({ source: map, width: 1600, height: 900, pixelRatio: 1,
                                       fit: { bounds, padding: GROUP_BRIEF_FIT_PADDING },
                                       transformStyle: (st) => briefStyle(st, ctx, metricId),
                                       compose: (c) => composeGroupFrame(c, ctx, metricId) });
      downloadBlob(res.blob, `gulf-energy-context-${metricId}-${m.year}.png`);
      setExportMsg(`Exported ${res.width}×${res.height}. The brief shows the whole group; your selection and zoom are not part of it.`);
    } catch (err) {
      setExportMsg(err instanceof Error ? err.message : String(err));
    }
  };

  if (manifest && !group) {
    return (
      <div className="global-page">
        <header className="global-head"><h1 className="ribbon-title">Energy Disruption Monitor</h1><SystemSwitcher current={null} /></header>
        <GlobalNavBar trail={[{ label: "Regional overview not found" }]} />
        <main className="global-main"><p className="warn-text" role="alert">There is no regional view called "{id}". <a href="?">Open the overview</a>.</p></main>
      </div>
    );
  }

  return (
    <div className="global-page group-page">
      <header className="global-head">
        <div>
          <h1 className="ribbon-title">{group?.label ?? "Regional"} overview</h1>
          <div className="ribbon-sub">Energy Disruption Monitor · national energy context and reviewed historical events · open sources only</div>
        </div>
        <SystemSwitcher current={null} group={id} />
      </header>
      <GlobalNavBar trail={[{ label: group?.label ?? "Regional overview" }]} />
      <main className="global-main">
        {ctx && (
          <section className="group-top" aria-label="What this view is">
            <p className="group-purpose">
              <strong>{ctx.label}:</strong> national energy figures for {ctx.systems.length} countries, for context, each
              linked to its own reviewed record of reported disruptions.
            </p>
            <p className="group-caveat-line small">
              National context only · not comparable between countries · no index or score, and nothing here is an order of importance.{" "}
              <a href="#group-notes">Notes and caveats</a>
            </p>
          </section>
        )}
        {ctxFailed && <p className="warn-text" role="alert">The regional context could not be loaded. Each country's own page still works.</p>}

        <PanelBoundary label="The regional energy context">
        {ctx && m && metricId && (
          <section aria-label="Regional energy context" className="group-context">
            <div className="group-stage">
              <div className={`group-controls map-control-row${colourBy ? "" : " is-neutral"}`}>
                <label className="small">Colour the map by{" "}
                  <select aria-label="Regional map metric" value={colourBy ?? "none"} onChange={(e) => setMetric(e.target.value === "none" ? null : e.target.value)}>
                    <option value="none">nothing (geography only)</option>
                    {Object.entries(ctx.metrics).map(([k, x]) => <option key={k} value={k}>{x.label} — {x.year}</option>)}
                  </select>
                </label>
                <label className="small">Show{" "}
                  <select aria-label="Membership filter" value={subset} onChange={(e) => setSubset(e.target.value as "all" | "gcc" | "opec")}>
                    <option value="all">all {ctx.systems.length} {ctx.label} systems</option>
                    <option value="gcc">GCC members only</option>
                    <option value="opec">OPEC members only</option>
                  </select>
                </label>
              </div>

              <aside className="group-side">
                {facts ? (
                  <section className="metric-facts panel" aria-label="About this figure" aria-live="polite">
                    <h3>{facts.label}</h3>
                    <dl className="metric-facts-list small">
                      <div><dt>Year</dt><dd>{facts.year}</dd></div>
                      <div><dt>Unit</dt><dd>{facts.unit}</dd></div>
                      <div><dt>Scope</dt><dd>national annual totals</dd></div>
                      <div><dt>Source</dt><dd>{facts.sourceUrl ? <a href={facts.sourceUrl} target="_blank" rel="noreferrer">{facts.source}</a> : facts.source}{facts.release ? `, release of ${fmtDate(facts.release)}` : ""}</dd></div>
                    </dl>
                    <p className="metric-definition small">{facts.definition}</p>
                    {facts.accounting && <p className="metric-accounting small dim"><strong>Accounting convention.</strong> {facts.accounting}</p>}
                  </section>
                ) : (
                  <p className="metric-facts metric-facts-empty small dim">
                    The map shows geography only. Choose a figure under "Colour the map by": its definition, year, unit and source appear here.
                  </p>
                )}

                <nav className="member-list" aria-label="Members">
                  <div className="member-list-head small"><strong>Members</strong> <span className="dim">({listed.length}, alphabetical)</span></div>
                  <p className="member-list-note small dim">{subsetNote}</p>
                  <ul onKeyDown={(e) => { if (e.key === "Escape") setSelA3(null); }}>
                    {listed.map((s) => (
                      <li key={s.system_id}>
                        <button type="button" className={`member-btn${pointA3 === s.a3 ? " is-pointed" : ""}`} aria-pressed={sel?.a3 === s.a3}
                          title={`${memberships(s)}. Select to highlight and zoom to it on the map.`}
                          onMouseEnter={() => setPointA3(s.a3)} onMouseLeave={() => setPointA3(null)}
                          onFocus={() => setPointA3(s.a3)} onBlur={() => setPointA3(null)}
                          onClick={() => choose(s)}>
                          {s.name}
                        </button>
                      </li>
                    ))}
                  </ul>
                </nav>
              </aside>

              <div className="group-map-col">
                <div className="global-map-wrap group-map-wrap">
                  {world && bounds ? (
                    <SimpleMap
                      data={world}
                      bounds={bounds}
                      idProp="a3"
                      fill={fill}
                      selected={sel?.a3 ?? null}
                      highlighted={pointA3}
                      outlineFilter={["in", ["get", "a3"], ["literal", memberA3]]}
                      pickable={(p) => byA3.has(String(p.a3))}
                      // A tap does what a hover does and more: it chooses the member and says what it is.
                      // Opening the country is a separate, named button.
                      onPick={(a3) => { const s = a3 ? byA3.get(a3) : null; if (s && inSubset(s)) setSelA3(sel?.a3 === s.a3 ? null : s.a3); }}
                      onHover={(p) => {
                        const s = p ? byA3.get(String(p.a3)) : null;
                        setPointA3(s ? s.a3 : null);
                        setHover(s ? describe(s) : null);
                      }}
                      ariaLabel={colourBy ? `Map of the ${ctx.label} coloured by ${m.label}, ${m.year}. Countries only. Use the member list or the table for a keyboard route.`
                        : `Map of the ${ctx.label}, every country in one colour. Countries only. Use the member list or the table for a keyboard route.`}
                      attribution="Boundaries: Natural Earth (public domain), line of actual control. Countries only: no facilities, routes or incident points."
                      tableHref="#group-table"
                      note={colourBy ? null : "Geography only — choose a national figure to colour the map"}
                      onMap={(mm) => { mapRef.current = mm; }}
                    />
                  ) : <div className="simple-map placeholder">{worldFailed ? "Map unavailable. The table below has every figure." : "Loading map…"}</div>}
                </div>
                <div className="map-hover-line small mono" aria-live="off">{hover ?? " "}</div>
                {sel ? (
                  <div className="member-detail panel" role="status" aria-label="Selected member">
                    <span><strong>{sel.name}</strong> <span className="dim">· {memberships(sel)}</span>
                      {colourBy && m && <> · {m.label}: {fmtValue(sel.values[colourBy], m.unit)} <span className="dim">({m.year}, national total)</span></>}</span>
                    <span className="member-detail-actions">
                      <button className="ghost" onClick={() => navigate(sel.system_id)}>Open {sel.name}</button>
                      {boundsOf.has(sel.system_id) && <button className="ghost" onClick={() => zoomTo(sel)}>Zoom to {sel.name}</button>}
                      <button className="ghost" onClick={resetView}>Show all members</button>
                      <button className="ghost" onClick={() => setSelA3(null)}>Clear selection</button>
                    </span>
                  </div>
                ) : (
                  <p className="member-detail-hint small dim">Point at, tap or choose a country in the list to highlight it; small members are easiest found from the list.</p>
                )}
                {colourBy ? (
                  <div className="map-legend-mini" aria-label="Map legend">
                    <span className="legend-title"><strong>{m.label} — {m.year}</strong> <span className="dim">({m.unit}; national totals)</span></span>
                    <span className="legend-ramp">{MEMBER_RAMP.map((c) => <i key={c} className="member-swatch" style={{ background: c }} />)} smaller to larger, within this group</span>
                    {special?.zero && <span><i className="member-swatch" style={{ background: ZERO }} />zero reported (measured, none)</span>}
                    {special?.noData && <span><i className="member-swatch" style={{ background: NO_DATA }} />no data (not zero)</span>}
                    {subset !== "all" && <span><i className="member-swatch" style={{ background: memberColour(ctx.systems[0], null, false, 0) }} />member, outside this filter</span>}
                    <span><i style={{ background: OTHER }} />other countries: geography only</span>
                    <span><i className="sel-swatch" />selected</span>
                    {special && !special.zero && !special.noData && <span className="small dim">No member in view has a zero or a missing figure; either would have its own colour.</span>}
                    <span className="small dim">Colour is a national energy figure. It says nothing about disruption, and a larger figure is not a more important country.</span>
                  </div>
                ) : (
                  <div className="map-legend-mini" aria-label="Map legend">
                    <span><i className="member-swatch" style={{ background: NEUTRAL }} />member, in this view</span>
                    {subset !== "all" && <span><i className="member-swatch" style={{ background: FILTERED }} />member, outside this filter</span>}
                    <span><i style={{ background: OTHER }} />other countries: geography only</span>
                    <span><i className="sel-swatch" />selected</span>
                    <span className="small dim">Geography only. To colour the countries by a national energy figure, choose one above; the colours never show disruption.</span>
                  </div>
                )}
                <div className="group-brief-row">
                  <button className="ghost group-brief-btn" onClick={runExport}>Download brief (PNG)</button>
                  <span className="small dim">The brief shows the whole group with the chosen figure, its year, source and caveats.</span>
                </div>
                {exportMsg && <p className="small" role="status">{exportMsg}</p>}
              </div>
            </div>

            <div className="group-notes" id="group-notes">
              {manifest && <p className="comparability" id="comparability" role="note">{manifest.comparability_statement}</p>}
              <details className="group-howto">
                <summary className="small">How to read this view (memberships, no score, two recording rules)</summary>
                <p className="small">{ctx.statement}</p>
                <p className="small">“Gulf littoral” is a geographic label for the states on the Gulf's coast. It is used instead of
                  “Gulf” alone, which on this site also names the United States Gulf coast.</p>
                <p className="small"><strong>Gulf littoral, GCC and OPEC are three different things.</strong></p>
                <ul className="small group-kinds">
                  <li><strong>{ctx.label}{ctx.member_names ? `: ${ctx.member_names.join(", ")}` : ""}.</strong> {readerText(ctx.note)}</li>
                  <li><strong>{ctx.memberships.gcc.label}{ctx.memberships.gcc.member_names ? `: ${ctx.memberships.gcc.member_names.join(", ")}` : ""}.</strong> {readerText(ctx.memberships.gcc.note)}
                    {ctx.memberships.gcc.basis && <span className="dim"> {readerText(ctx.memberships.gcc.basis)}</span>}</li>
                  <li><strong>{ctx.memberships.opec.label}{ctx.memberships.opec.member_names ? `: ${ctx.memberships.opec.member_names.join(", ")}` : ""}.</strong> {readerText(ctx.memberships.opec.note)}</li>
                </ul>
                <p className="small"><strong>No country here has an index or a score.</strong> The one index on this site was built
                  for a single attack campaign elsewhere, and its weights and assumptions do not carry over. A missing index is not a zero.</p>
                <p className="small"><strong>Countries are recorded under two rules.</strong> In the systems added most recently an attack is
                  recorded for the country as a whole, with no region, facility or operator, because in a small or concentrated
                  system a region and a kind of facility together can name one site. A system added earlier still places attacks
                  by region and names the facility, and keeps that convention for its records for now.
                  Each card below says which rule applies.</p>
                <p className="small dim">{readerText(ctx.not_built)}</p>
              </details>
            </div>

            <h3 className="group-table-head" id="group-table" tabIndex={-1}>National figures, alphabetical</h3>
            <div className="table-scroll">
              <table className="sector-table group-table">
                <caption className="small dim">Alphabetical. National annual totals; "no data" is not zero. Source and year under the table.</caption>
                <thead>
                  <tr>
                    <th>Country</th><th>GCC</th><th>OPEC</th>
                    {Object.entries(ctx.metrics).map(([k, x]) => <th key={k} title={x.definition}>{x.label} ({x.unit}, {x.year})</th>)}
                  </tr>
                </thead>
                <tbody>
                  {shown.map((s) => (
                    <tr key={s.system_id}>
                      <td><button className="linklike" onClick={() => navigate(s.system_id)} {...prefetchOn(s.system_id)}>{s.name}</button></td>
                      <td className="small">{s.gcc_member ? "member" : "not a member"}</td>
                      <td className="small">{s.opec_member ? "member" : "not a member"}</td>
                      {Object.entries(ctx.metrics).map(([k, x]) => <td key={k} className="mono small">{fmtValue(s.values[k], x.unit)}</td>)}
                    </tr>
                  ))}
                </tbody>
                {subset === "all" && (
                  <tfoot>
                    <tr>
                      <td colSpan={3} className="small">All {ctx.systems.length} together</td>
                      {Object.entries(ctx.metrics).map(([k, x]) => {
                        const r = ctx.region[k];
                        return (
                          <td key={k} className="mono small">
                            {r.value == null ? <span className="dim">not summed: {readerText(r.reason)}</span>
                              : <>{fmtValue(r.value, x.unit)}{r.world_share != null && <span className="dim"> · {Math.round(r.world_share * 1000) / 10}% of world</span>}</>}
                          </td>
                        );
                      })}
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
            {region && region.value != null && region.world_share != null && subset === "all" && (
              <p className="small">All {ctx.systems.length} together: {fmtValue(region.value, m.unit)} of {m.label.toLowerCase()} in {m.year}, {Math.round(region.world_share * 1000) / 10}% of the world total. A descriptive annual figure.</p>
            )}
            <p className="small dim">
              {Object.entries(ctx.sources).map(([k, s]) => <span key={k}>Source: <a href={s.url} target="_blank" rel="noreferrer">{s.name}</a>{s.release ? `, release of ${fmtDate(s.release)}` : ""}. </span>)}
              Each column is one source and one year. Metrics with no common redistributable source are left out, not estimated.
              {ctx.accounting_convention && <> {ctx.accounting_convention}</>}
            </p>
            <details className="small">
              <summary>What each column measures</summary>
              <ul>{Object.entries(ctx.metrics).map(([k, x]) => <li key={k}><strong>{x.label}.</strong> {x.definition}</li>)}</ul>
            </details>
          </section>
        )}
        </PanelBoundary>

        <h2 className="level-head">Monitored systems in this view</h2>
        <section aria-label="Monitored systems in this view" className="sys-cards">
          {shown.map((s) => (
            <article key={s.system_id} className="sys-card panel" aria-label={s.name}>
              <h2>{s.name}</h2>
              <div className="small">
                {s.gcc_member ? "GCC member" : "Not a GCC member"} · {s.opec_member ? "OPEC member" : "Not an OPEC member"}
              </div>
              {s.maturity === "research_preview" && <div><ResearchPreviewBadge /></div>}
              {s.recovery_status_withheld && (
                <div><Disclosure label="Later status of attacked facilities is not published" className="badge context-only-badge"
                  text="While attacks on energy facilities are still being reported, or it is uncertain whether they have ended, an attack is published as an event but the facility's later repair, restart or operating status is not." /></div>
              )}
              <div className="sys-headline none"><span className="small">No index. Reviewed historical events and context only.</span></div>
              <div className="small dim">Reporting: {labelFor(ENVIRONMENT_LABEL, s.reporting_environment)}</div>
              {s.attack_records_placed && (
                <div className="small dim">
                  {s.attack_records_placed === "country"
                    ? "Attacks are recorded for the country as a whole, with no region or facility."
                    : "Attacks are recorded by first-level region with the facility named: the earlier rule, under which this system was added."}
                </div>
              )}
              <div className="small dim">
                {s.last_systematic_pass ? `Latest systematic research pass ${fmtDate(s.last_systematic_pass)}` : "No systematic research pass yet"}
                {Object.keys(s.lane_states).length > 0 && `: ${laneChips(s.lane_states)}`}
              </div>
              {s.languages_required.length > 0 && (
                <div className="small dim">Languages the search plan requires: {languageNames(s.languages_required)}. Used in at least one source group so far: {languageNames(s.languages_executed) || "none"}.</div>
              )}
              <button className="ghost" onClick={() => navigate(s.system_id)} {...prefetchOn(s.system_id)}>Open {s.name}</button>
            </article>
          ))}
        </section>

        <PanelBoundary label="The recent list">
        {ctx?.recent && (
          <section className="panel global-note recent-evidence" aria-label="Recent reviewed events in this region">
            <h2 className="eyebrow">Reviewed events in this region, newest first</h2>
            <p className="small dim">Date order only. No severity, size or country order. Most of these records were added as a historical
              backfill when the countries were added: a long list is a larger dataset, not a deteriorating region.
              A country with few records has few records found, which is not few disruptions.</p>
            <p className="small dim feed-national-note">“National” in this list: a record covered by the attack-campaign safeguards
              is shown here for the country as a whole. Its country page may still name a region and facility, where that country's
              records were published under the earlier rule (each card above says which rule applies).</p>
            <ol className="feed">
              {collapseCovered(ctx.recent.episodes.filter((ep) => shown.some((s) => s.system_id === ep.system_id))).map((row) => row.kind === "covered-run"
                ? <CoveredRunItem key={row.key} row={row} />
                : <EpisodeItem key={`${row.ep.system_id}:${row.ep.episode_id}`} ep={row.ep} />)}
              {ctx.recent.episodes.length === 0 && <li className="small dim">No qualifying records in the current reviewed corpus for this region.</li>}
            </ol>
          </section>
        )}
        </PanelBoundary>
      </main>
    </div>
  );
}
