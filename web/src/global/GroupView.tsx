import { useEffect, useMemo, useRef, useState } from "react";
import type maplibregl from "maplibre-gl";
import SimpleMap from "./SimpleMap";
import SystemSwitcher from "./SystemSwitcher";
import { fmtValue } from "./context";
import { composeGroupFrame } from "./groupExport";
import {
  ENVIRONMENT_LABEL, LANE_STATE_LABEL, groupBySlug, languageNames, labelFor, loadGroupContext, loadManifest, loadWorld,
  type GroupContext, type GroupSystem, type Manifest, type RecentEpisode,
} from "./manifest";
import { navigate } from "./router";
import { Disclosure, ResearchPreviewBadge } from "./Disclosure";
import { downloadBlob, exportMapPng } from "../mapExport";
import { fmtDate } from "../data";

/** A regional overview (iteration 19): the Gulf.
 *
 *  A REGIONAL ENERGY PICTURE, NOT A TARGET SET. Everything on this page is a country: its annual
 *  national energy figures, whether it is monitored, how far its research has got, and its
 *  reviewed historical events in date order. There is no facility layer, no route, no strait, no
 *  shipping, and no ordering of countries by anything but name.
 */

const MEMBER_RAMP = ["#27517a", "#2a7596", "#3c9aa5", "#69bea6", "#a9dba4"];
const NO_DATA = "#5a5e66";
const OTHER = "#141c25";
// The one colour of every member while the map shows geography only (iteration 20, §38).
const NEUTRAL = "#33475b";

/** The box that holds every member, from the manifest. A typed-in box cropped two members on a
 *  tall phone, and would be a country list in the frontend by another name. */
function unionBounds(boxes: [number, number, number, number][]): [number, number, number, number] | null {
  if (!boxes.length) return null;
  const pad = 1;
  return [Math.min(...boxes.map((b) => b[0])) - pad, Math.min(...boxes.map((b) => b[1])) - pad,
          Math.max(...boxes.map((b) => b[2])) + pad, Math.max(...boxes.map((b) => b[3])) + pad];
}

function classOf(v: number, max: number): number {
  // Five classes of magnitude down from the group's largest value. Classes, not positions.
  const f = v / max;
  return f >= 0.5 ? 4 : f >= 0.2 ? 3 : f >= 0.08 ? 2 : f >= 0.02 ? 1 : 0;
}

function fmtEpisodeDate(ep: RecentEpisode): string {
  // From the string itself: a browser's Date parser reads "2026-04" differently across engines.
  if (ep.date_precision === "month") return fmtDate(ep.first_date.slice(0, 7));
  return ep.first_date === ep.last_date ? fmtDate(ep.first_date) : `${fmtDate(ep.first_date)} – ${fmtDate(ep.last_date)}`;
}

function laneLine(states: Record<string, number>): string {
  return Object.entries(states).map(([k, n]) => `${n} ${labelFor(LANE_STATE_LABEL, k).toLowerCase()}`).join(" · ");
}

export default function GroupView({ id }: { id: string }) {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [ctx, setCtx] = useState<GroupContext | null>(null);
  const [ctxFailed, setCtxFailed] = useState(false);
  const [world, setWorld] = useState<GeoJSON.FeatureCollection | null>(null);
  const [metric, setMetric] = useState<string | null>(null);
  const [subset, setSubset] = useState<"all" | "gcc" | "opec">("all");
  const [hover, setHover] = useState<string | null>(null);
  const [exportMsg, setExportMsg] = useState<string | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    const ctl = new AbortController();
    loadManifest().then((m) => {
      setManifest(m);
      const found = groupBySlug(m, id);
      // The manifest names the context file; the view never builds a path from the URL.
      if (found?.group.context) {
        loadGroupContext(found.group.context, ctl.signal).then(setCtx)
          .catch(() => { if (!ctl.signal.aborted) setCtxFailed(true); });
      }
    }).catch(() => setCtxFailed(true));
    loadWorld(ctl.signal).then(setWorld).catch(() => undefined);
    return () => ctl.abort();
  }, [id]);

  const group = manifest ? groupBySlug(manifest, id)?.group : undefined;
  useEffect(() => { document.title = `Energy Disruption Monitor — ${group?.label ?? "regional"} overview`; }, [group]);

  // The map is coloured only once a reader chooses a metric; until then it is geography. The table,
  // the regional total and the brief still describe a metric, the first one, so they have one.
  const colourBy = metric && ctx?.metrics[metric] ? metric : null;
  const metricId = colourBy ?? (ctx ? Object.keys(ctx.metrics)[0] : null);
  const m = ctx && metricId ? ctx.metrics[metricId] : null;
  const inSubset = (s: GroupSystem) => subset === "all" || (subset === "gcc" ? s.gcc_member : s.opec_member);
  const shown = useMemo(() => (ctx?.systems ?? []).filter(inSubset), [ctx, subset]);  // eslint-disable-line react-hooks/exhaustive-deps
  const byA3 = useMemo(() => new Map((ctx?.systems ?? []).map((s) => [s.a3, s])), [ctx]);

  const fill = useMemo(() => {
    if (!ctx || !metricId) return OTHER;
    if (!colourBy) {
      const neutral: unknown[] = ["match", ["get", "a3"]];
      for (const s of ctx.systems) neutral.push(s.a3, inSubset(s) ? NEUTRAL : OTHER);
      neutral.push(OTHER);
      return neutral as maplibregl.ExpressionSpecification;
    }
    const vals = ctx.systems.map((s) => s.values[metricId]).filter((v): v is number => v != null && v > 0);
    const max = Math.max(...vals, 0);
    const expr: unknown[] = ["match", ["get", "a3"]];
    for (const s of ctx.systems) {
      const v = s.values[metricId];
      expr.push(s.a3, !inSubset(s) ? OTHER : v == null ? NO_DATA : max > 0 ? MEMBER_RAMP[classOf(v, max)] : MEMBER_RAMP[0]);
    }
    expr.push(OTHER);
    return expr as maplibregl.ExpressionSpecification;
  }, [ctx, metricId, colourBy, subset]);  // eslint-disable-line react-hooks/exhaustive-deps

  const memberA3 = (ctx?.systems ?? []).map((s) => s.a3);
  const bounds = useMemo(() => {
    const ids = new Set((ctx?.systems ?? []).map((s) => s.system_id));
    return unionBounds((manifest?.systems ?? []).filter((s) => ids.has(s.id) && s.bounds).map((s) => s.bounds!));
  }, [ctx, manifest]);
  const region = ctx && metricId ? ctx.region[metricId] : null;
  const subsetNote = subset === "gcc" ? ctx?.memberships.gcc.note : subset === "opec" ? ctx?.memberships.opec.note : ctx?.note;

  const runExport = async () => {
    const map = mapRef.current;
    if (!map || !ctx || !m || !metricId) { setExportMsg("The map is not ready yet."); return; }
    // A brief names the metric its colours show; an uncoloured map has none to name.
    if (!colourBy) { setExportMsg("Choose a metric under \"Colour the map by\" first: the brief describes the colours it shows."); return; }
    try {
      const res = await exportMapPng({ source: map, width: 1600, height: 900, pixelRatio: 1,
                                       compose: (c) => composeGroupFrame(c, ctx, metricId) });
      downloadBlob(res.blob, `gulf-energy-context-${metricId}-${m.year}.png`);
      setExportMsg(`Exported ${res.width}×${res.height}.`);
    } catch (err) {
      setExportMsg(err instanceof Error ? err.message : String(err));
    }
  };

  if (manifest && !group) {
    return (
      <div className="global-page">
        <header className="global-head"><h1 className="ribbon-title">Energy Disruption Monitor</h1><SystemSwitcher current={null} /></header>
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
      <main className="global-main">
        {manifest && <p className="comparability" id="comparability" role="note">{manifest.comparability_statement}</p>}
        {ctx && (
          <section className="panel global-note group-intro" aria-label="What this view is">
            <p>
              <strong>{ctx.label}{ctx.member_names ? `: ${ctx.member_names.join(", ")}` : ""}.</strong>{" "}
              National energy figures for each country, for context, and links to each country's reviewed
              record of reported disruptions. The map starts uncoloured; choose a figure to colour it, or open a country.
            </p>
            <p className="small phone-only"><a href="#comparability">Event counts are not comparable between countries: why</a></p>
            <details className="group-howto">
              <summary className="small">How to read this view (memberships, no score, two recording rules)</summary>
            <p className="small">{ctx.statement}</p>
            <p className="small">“Gulf littoral” is a geographic label for the states on the Gulf's coast. It is used instead of
              “Gulf” alone, which on this site also names the United States Gulf coast.</p>
            <p className="small"><strong>Gulf littoral, GCC and OPEC are three different things.</strong></p>
            <ul className="small group-kinds">
              <li><strong>{ctx.label}{ctx.member_names ? `: ${ctx.member_names.join(", ")}` : ""}.</strong> {ctx.note}</li>
              <li><strong>{ctx.memberships.gcc.label}{ctx.memberships.gcc.member_names ? `: ${ctx.memberships.gcc.member_names.join(", ")}` : ""}.</strong> {ctx.memberships.gcc.note}
                {ctx.memberships.gcc.basis && <span className="dim"> {ctx.memberships.gcc.basis}</span>}</li>
              <li><strong>{ctx.memberships.opec.label}{ctx.memberships.opec.member_names ? `: ${ctx.memberships.opec.member_names.join(", ")}` : ""}.</strong> {ctx.memberships.opec.note}</li>
            </ul>
            <p className="small"><strong>No country here has an index or a score.</strong> The one index on this site was built
              for a single attack campaign elsewhere, and its weights and assumptions do not carry over. A missing index is not a zero.</p>
            <p className="small"><strong>Countries are recorded under two rules.</strong> In the systems added most recently an attack is
              recorded for the country as a whole, with no region, facility or operator, because in a small or concentrated
              system a region and a kind of facility together can name one site. A system added earlier still places attacks
              by region and names the facility; whether to bring its older records under the newer rule is an open decision.
              Each card below says which rule applies.</p>
            <p className="small dim">{ctx.not_built}</p>
            </details>
          </section>
        )}
        {ctxFailed && <p className="warn-text" role="alert">The regional context could not be loaded. Each country's own page still works.</p>}

        {ctx && m && metricId && (
          <section aria-label="Regional energy context" className="world-context">
            <div className="section-head">
              <h2>National energy context</h2>
              <button className="ghost" onClick={runExport}>Download brief (PNG)</button>
            </div>
            <div className="map-control-row">
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
            <p className="small dim">{subsetNote}</p>
            <div className="global-map-wrap">
              {world && bounds ? (
                <SimpleMap
                  data={world}
                  bounds={bounds}
                  idProp="a3"
                  fill={fill}
                  outlineFilter={["in", ["get", "a3"], ["literal", memberA3]]}
                  pickable={(p) => byA3.has(String(p.a3))}
                  onPick={(a3) => { const s = a3 ? byA3.get(a3) : null; if (s) navigate(s.system_id); }}
                  onHover={(p) => {
                    const s = p ? byA3.get(String(p.a3)) : null;
                    setHover(s ? (colourBy ? `${s.name}: ${fmtValue(s.values[metricId], m.unit)} (${m.year}, national total)` : s.name) : null);
                  }}
                  ariaLabel={colourBy ? `Map of the ${ctx.label} coloured by ${m.label}, ${m.year}. Countries only. Use the table below for a keyboard route.`
                    : `Map of the ${ctx.label}, every country in one colour. Countries only. Use the table below for a keyboard route.`}
                  attribution="Boundaries: Natural Earth (public domain), line of actual control. Countries only: no facilities, routes or incident points."
                  onMap={(mm) => { mapRef.current = mm; }}
                />
              ) : <div className="simple-map placeholder">Loading map…</div>}
              <div className="map-hover-line small mono" aria-live="off">{hover ?? " "}</div>
            </div>
            {colourBy ? (
              <div className="map-legend-mini" aria-label="Map legend">
                <span className="legend-title"><strong>{m.label} — {m.year}</strong> <span className="dim">({m.unit}; national totals)</span></span>
                <span><i style={{ background: MEMBER_RAMP[0] }} />smaller</span>
                <span><i style={{ background: MEMBER_RAMP[4] }} />larger, within this group</span>
                <span><i style={{ background: NO_DATA }} />no data</span>
                <span><i style={{ background: OTHER }} />not in this view</span>
                <span className="small dim">Colour is a national energy figure. It says nothing about disruption, and a larger figure is not a more important country.</span>
              </div>
            ) : (
              <div className="map-legend-mini" aria-label="Map legend">
                <span><i style={{ background: NEUTRAL }} />in this view</span>
                <span><i style={{ background: OTHER }} />not in this view</span>
                <span className="small dim">Geography only. To colour the countries by a national energy figure, choose one above; the colours never show disruption.</span>
              </div>
            )}
            {exportMsg && <p className="small" role="status">{exportMsg}</p>}

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
                      <td><button className="linklike" onClick={() => navigate(s.system_id)}>{s.name}</button></td>
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
                            {r.value == null ? <span className="dim">not summed: {r.reason}</span>
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
                {Object.keys(s.lane_states).length > 0 && `: ${laneLine(s.lane_states)}`}
              </div>
              {s.languages_required.length > 0 && (
                <div className="small dim">Languages the search plan requires: {languageNames(s.languages_required)}. Used in at least one source group so far: {languageNames(s.languages_executed) || "none"}.</div>
              )}
              <button className="ghost" onClick={() => navigate(s.system_id)}>Open {s.name}</button>
            </article>
          ))}
        </section>

        {ctx?.recent && (
          <section className="panel global-note recent-evidence" aria-label="Recent reviewed events in this region">
            <h2 className="eyebrow">Reviewed events in this region, newest first</h2>
            <p className="small dim">Date order only. No severity, size or country order. Most of these records were added as a historical
              backfill when the countries were onboarded: a long list is a larger dataset, not a deteriorating region.
              A country with few records has few records found, which is not few disruptions.</p>
            <ol className="feed">
              {ctx.recent.episodes.filter((ep) => shown.some((s) => s.system_id === ep.system_id)).map((ep) => (
                <li key={`${ep.system_id}:${ep.episode_id}`} className="feed-item">
                  <div className="event-head">
                    <span className="mono small">{fmtEpisodeDate(ep)}</span>
                    <button className="linklike small" onClick={() => navigate(ep.system_id)}>{ep.country}</button>
                    <span className="small dim">{ep.classes.join(", ")} · {ep.causes.join(", ")}</span>
                  </div>
                  {ep.episode_name && <div className="small"><strong>{ep.episode_name}</strong> <span className="dim">({ep.records} records, one episode)</span></div>}
                  <ul className="lane-list small">
                    {ep.members.map((mm, i) => (
                      <li key={i}><span className="dim">{mm.region}: </span>
                        {mm.withheld ? <span className="dim">Not summarised in this list while an attack campaign is active or recent. The country page gives the effect reported at the time; later status is not published anywhere.</span> : mm.effect_on_country_page ? <span className="dim">Effect: on the country page.</span> : (mm.effect ?? <span className="dim">no effect text</span>)}
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
              {ctx.recent.episodes.length === 0 && <li className="small dim">No qualifying records in the current reviewed corpus for this region.</li>}
            </ol>
          </section>
        )}
      </main>
    </div>
  );
}
