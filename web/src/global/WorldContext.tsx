import { useEffect, useMemo, useRef, useState } from "react";
import type maplibregl from "maplibre-gl";
import SimpleMap from "./SimpleMap";
import {
  ELEC_FUELS, ROLE_LABEL, UNIT_SHORT, fmtValue, loadContext, mixShares, modesFor,
  type ContextRow, type EnergyContext, type MapMode,
} from "./context";
import { composeContextFrame, contextFilename } from "./contextExport";
import type { Manifest } from "./manifest";
import { navigate } from "./router";
import { downloadBlob, exportMapPng } from "../mapExport";
import { fmtDate } from "../data";

/** The world map of national energy context (iteration 18).
 *
 *  THE WORLD PICTURE IS NOT THE WORLD INCIDENT CORPUS. Fill colour is a national energy figure;
 *  monitoring is a separate mark, a thick outline, named in the legend. Selecting a context-only
 *  country opens a small card of national figures and fetches nothing else: no dossier, no event
 *  count, no zero. Selecting a monitored system opens it.
 */

const MONITORED_FALLBACK = "#1e5560";
const OCCUPIED = "#5b4a1e";
const OTHER = "#141c25";
// Names people type that are not in a country's name.
const SEARCH_ALIASES: Record<string, string> = {
  us: "united states", usa: "united states", uk: "united kingdom", uae: "united arab emirates",
};

function Figure({ label, value }: { label: string; value: string }) {
  return <div className="ctx-fig"><span className="dim">{label}</span><span className="mono">{value}</span></div>;
}

export function NationalFigures({ row, ctx }: { row: ContextRow; ctx: EnergyContext }) {
  const m = ctx.metrics;
  const v = row.values;
  const shares = mixShares(row);
  const elecTotal = v.electricity_generation;
  const roles = Object.entries(row.roles.by_commodity).filter(([, r]) => r);
  return (
    <>
      <div className="ctx-figs">
        <Figure label={`Energy production, ${ctx.comparison_year}`} value={fmtValue(v.total_production, m.total_production.unit)} />
        <Figure label={`Energy consumption, ${ctx.comparison_year}`} value={fmtValue(v.total_consumption, m.total_consumption.unit)} />
        <Figure label={`Crude oil, ${ctx.comparison_year}`} value={fmtValue(v.crude_production, m.crude_production.unit)} />
        <Figure label={`Natural gas, ${ctx.comparison_year}`} value={fmtValue(v.gas_production, m.gas_production.unit)} />
        <Figure label={`Coal, ${ctx.comparison_year}`} value={fmtValue(v.coal_production, m.coal_production.unit)} />
        <Figure label={`Electricity, ${ctx.comparison_year}`} value={fmtValue(elecTotal, m.electricity_generation.unit)} />
      </div>
      {shares.length > 0 && (
        <div>
          <div className="eyebrow">Production mix</div>
          <div className="mix-bar" role="img"
            aria-label={shares.map((s) => `${s.label} ${Math.round(s.share * 100)}%`).join(", ")}>
            {shares.map((s) => <span key={s.id} style={{ width: `${s.share * 100}%`, background: s.color }} />)}
          </div>
          <div className="small dim">{shares.map((s) => `${s.label} ${Math.round(s.share * 100)}%`).join(" · ")}</div>
        </div>
      )}
      {elecTotal != null && elecTotal > 0 && (
        <div className="small dim">Electricity by source: {ELEC_FUELS
          .map(([id, label]) => [label, (v[id] ?? 0) / elecTotal] as const)
          .filter(([, s]) => s >= 0.01)
          .map(([label, s]) => `${label} ${Math.round(s * 100)}%`).join(" · ")}</div>
      )}
      {row.roles.overall && (
        <div className="small">{ROLE_LABEL[row.roles.overall]}
          {roles.length > 0 && <span className="dim"> ({roles.map(([k, r]) => `${k}: ${String(r).replace("net_", "").replace("about_", "")}`).join(", ")}; oil here counts all liquids, including refinery gain)</span>}
        </div>
      )}
    </>
  );
}

function SourceLine({ ctx }: { ctx: EnergyContext }) {
  return (
    <div className="small dim">
      {ctx.comparison_year} figures. Source: <a href={ctx.source.url} target="_blank" rel="noreferrer">{ctx.source.name}</a>,
      release of {fmtDate(ctx.source.release)}.
    </div>
  );
}

function ContextCard({ row, ctx, note, onClose }: { row: ContextRow; ctx: EnergyContext; note?: string | null; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const opener = useRef<Element | null>(null);
  useEffect(() => {
    opener.current = document.activeElement;
    closeRef.current?.focus();
  }, [row.a3]);
  const close = () => { onClose(); (opener.current as HTMLElement | null)?.focus?.(); };
  // Part of a monitored country lies outside its monitored area (eastern Russia). Saying "not
  // searched" there would be false for the country and is not what the map means.
  const partial = !!row.system_id;
  return (
    <aside className="context-card panel" role="region" aria-label={`${row.name}: national energy context`}
      onKeyDown={(e) => { if (e.key === "Escape") close(); }}>
      <div className="section-head">
        <h3>{row.name}</h3>
        <button ref={closeRef} className="ghost" onClick={close} aria-label={`Close ${row.name}`}>Close</button>
      </div>
      <div className="badge context-only-badge">{partial ? "This area is outside the monitored part of the country" : "Not systematically monitored for disruptions"}</div>
      <NationalFigures row={row} ctx={ctx} />
      {note && <p className="small dim">{note}</p>}
      {partial ? (
        <p className="small dim">National energy statistics for the whole country. Events are recorded only for the monitored
          area. <button className="linklike" onClick={() => navigate(row.system_id as string)}>Open the monitored area</button></p>
      ) : (
        <p className="small dim">National energy statistics only. This site has no disruption record for {row.name}:
          it was not searched, so nothing can be said here about what has or has not happened there.</p>
      )}
      <SourceLine ctx={ctx} />
    </aside>
  );
}

function NationalTable({ ctx, partly, onContext }: { ctx: EnergyContext; partly: Set<string>; onContext: (a3: string) => void }) {
  const [sort, setSort] = useState<string | null>(null);
  const cols = ctx.map_metrics;
  const rows = useMemo(() => {
    if (!sort) return ctx.countries;
    // Sorting is the reader's own request. The default order is alphabetical, and nulls stay last.
    return [...ctx.countries].sort((a, b) => (b.values[sort] ?? -1) - (a.values[sort] ?? -1));
  }, [ctx, sort]);
  return (
    <div className="table-scroll">
      <p className="small dim">One source, one year ({ctx.comparison_year}). Alphabetical by default; choose a column to
        sort by that national figure. "No data" is not zero. Energy production says nothing about disruption or importance.</p>
      <table className="sector-table national-table">
        <thead>
          <tr>
            <th aria-sort={sort ? "none" : "ascending"}><button className="linklike" onClick={() => setSort(null)}>Country</button></th>
            <th>Status</th>
            {cols.map((c) => (
              <th key={c} aria-sort={sort === c ? "descending" : "none"}>
                <button className="linklike" onClick={() => setSort(c)}>
                  {ctx.metrics[c].label} ({UNIT_SHORT[ctx.metrics[c].unit]})
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.a3}>
              <td>
                <button className="linklike" onClick={() => { if (r.system_id) navigate(r.system_id); else onContext(r.a3); }}>{r.name}</button>
              </td>
              <td className="small dim">{partly.has(r.a3) ? "Partly monitored" : r.system_id ? "Monitored" : "Context only"}</td>
              {cols.map((c) => <td key={c} className="mono small">{fmtValue(r.values[c], ctx.metrics[c].unit).replace(/ .*$/, (s) => (s === " data" ? " data" : ""))}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CountrySearch({ ctx, onContext }: { ctx: EnergyContext; onContext: (a3: string) => void }) {
  const [q, setQ] = useState("");
  const hits = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (s.length < 2) return [];
    const alias = SEARCH_ALIASES[s];
    const match = (r: ContextRow) => r.name.toLowerCase().includes(s) || r.a3.toLowerCase() === s;
    const named = alias ? ctx.countries.filter((r) => r.name.toLowerCase() === alias) : [];
    return [...named, ...ctx.countries.filter((r) => match(r) && !named.includes(r))].slice(0, 8);
  }, [q, ctx]);
  return (
    <div className="country-search">
      <label className="small">Find a country{" "}
        <input type="search" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Find a country" placeholder="e.g. Australia" />
      </label>
      {hits.length > 0 && (
        <ul className="search-hits">
          {hits.map((r) => (
            <li key={r.a3}>
              <button className="linklike" onClick={() => { setQ(""); if (r.system_id) navigate(r.system_id); else onContext(r.a3); }}>
                {r.name}
              </button>
              <span className="small dim"> {r.system_id ? "· Monitored system" : "· Global energy context · Not systematically monitored"}</span>
            </li>
          ))}
        </ul>
      )}
      {q.trim().length >= 2 && hits.length === 0 && <div className="small dim">No country by that name in this dataset.</div>}
    </div>
  );
}

export default function WorldContext({ world, worldError, manifest }: {
  world: GeoJSON.FeatureCollection | null; worldError: string | null; manifest: Manifest | null;
}) {
  const [ctx, setCtx] = useState<EnergyContext | null>(null);
  const [ctxError, setCtxError] = useState<string | null>(null);
  const [modeId, setModeId] = useState<string | null>(null);
  const [cardA3, setCardA3] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const [exportMsg, setExportMsg] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    let live = true;
    loadContext().then((c) => { if (live) setCtx(c); })
      .catch((e) => { if (live) setCtxError(e instanceof Error ? e.message : String(e)); });
    return () => { live = false; };
  }, []);

  const modes = useMemo(() => (ctx ? modesFor(ctx) : []), [ctx]);
  const mode: MapMode | null = modes.find((m) => m.id === modeId) ?? modes[0] ?? null;
  const byA3 = useMemo(() => new Map((ctx?.countries ?? []).map((r) => [r.a3, r])), [ctx]);
  const noteOf = useMemo(() => {
    const out = new Map<string, string>();
    for (const f of world?.features ?? []) {
      const p = f.properties as { a3?: string; note?: string | null; status?: string } | null;
      // Crimea's feature carries a3 UKR. Its note is about Crimea and must not reach Ukraine's card.
      if (p?.a3 && p.note && p.status !== "occupied" && !out.has(p.a3)) out.set(p.a3, p.note);
    }
    return out;
  }, [world]);
  // A country drawn both with and without a system id is monitored in part.
  const partly = useMemo(() => {
    const monitored = new Set<string>();
    const not = new Set<string>();
    for (const f of world?.features ?? []) {
      const p = f.properties as { a3?: string; system_id?: string | null; status?: string } | null;
      if (!p?.a3 || p.status === "occupied") continue;
      (p.system_id ? monitored : not).add(p.a3);
    }
    return new Set([...monitored].filter((a) => not.has(a)));
  }, [world]);

  // Without the context file the map falls back to showing only where is monitored.
  const fill = (mode?.fill ?? ["case",
    ["==", ["get", "status"], "occupied"], OCCUPIED,
    ["!=", ["get", "system_id"], null], MONITORED_FALLBACK,
    OTHER]) as maplibregl.ExpressionSpecification;

  const monitoredNames = manifest?.systems.map((s) => s.name) ?? [];
  const card = cardA3 ? byA3.get(cardA3) : undefined;

  const runExport = async () => {
    const m = mapRef.current;
    if (!m || !ctx || !mode) { setExportMsg("The map is not ready yet."); return; }
    setExporting(true);
    setExportMsg(null);
    try {
      const res = await exportMapPng({ source: m, width: 1600, height: 900, pixelRatio: 1,
                                       compose: (c) => composeContextFrame(c, ctx, mode, monitoredNames) });
      downloadBlob(res.blob, contextFilename(ctx, mode));
      setExportMsg(`Exported ${res.width}×${res.height}.`);
    } catch (err) {
      setExportMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setExporting(false);
    }
  };

  return (
    <section aria-label="World energy context" className="world-context">
      <div className="section-head">
        <h2>World energy context</h2>
        {ctx && <button className="ghost" onClick={runExport} disabled={exporting}>{exporting ? "Rendering…" : "Download PNG"}</button>}
      </div>
      {ctxError && (
        <p className="warn-text" role="alert">Global energy context unavailable. The monitored systems below are not affected.</p>
      )}
      {ctx && mode && (
        <details className="map-controls" open>
          <summary>Map controls</summary>
          <div className="map-control-row">
            <label className="small">Colour the map by{" "}
              <select aria-label="Map metric" value={mode.id} onChange={(e) => setModeId(e.target.value)}>
                {modes.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}
              </select>
            </label>
            <CountrySearch ctx={ctx} onContext={setCardA3} />
          </div>
        </details>
      )}
      <div className="global-map-wrap">
        {world ? (
          <SimpleMap
            data={world}
            bounds={[-170, -50, 179, 78]}
            idProp="a3"
            selected={cardA3}
            fill={fill}
            outlineFilter={["!=", ["get", "system_id"], null]}
            pickable={(p) => !!p.system_id || byA3.has(String(p.a3))}
            onPick={(id, p) => {
              const sid = p?.system_id as string | null | undefined;
              if (sid) navigate(sid);
              else if (id) setCardA3(id);
            }}
            onHover={(p) => {
              if (!p) { setHover(null); return; }
              const row = byA3.get(String(p.a3));
              const value = mode ? mode.describe(row) : "";
              // The figure belongs to the country; Crimea has no national figure of its own.
              const occupied = p.status === "occupied";
              const name = occupied ? `${row?.name ?? "Ukraine"} (national figure)` : String(p.name ?? p.a3);
              const where = p.system_id ? (occupied ? "Crimea: monitored within the Russia theatre, select to open" : "monitored, select to open")
                : row?.system_id ? "outside the monitored area" : "context only, not monitored";
              setHover(`${name}${value ? `: ${value}` : ""} · ${where}`);
            }}
            ariaLabel={mode
              ? `World map coloured by ${mode.title}. Monitored systems have a thick outline. For a keyboard route use the search box, or the national figures table in the world profile.`
              : "World map. Monitored systems are highlighted; select one to open it."}
            attribution="Energy data: U.S. EIA International Energy Statistics. Boundaries: Natural Earth (public domain), line of actual control. Crimea is drawn as Ukrainian territory under Russian occupation."
            onMap={(m) => { mapRef.current = m; }}
          />
        ) : (
          <div className="simple-map placeholder">{worldError ? "Map unavailable" : "Loading map…"}</div>
        )}
        <div className="map-hover small mono" aria-live="off">{hover ?? " "}</div>
      </div>
      {mode && ctx ? (
        <div className="map-legend-mini" aria-label="Map legend">
          <span className="legend-title"><strong>{mode.title}</strong> <span className="dim">({mode.unitNote})</span></span>
          {mode.legend.map((l) => <span key={l.label}><i style={{ background: l.color }} />{l.label}</span>)}
          <span className="legend-monitored"><i className="outline-swatch" /> Thick outline: systematically monitored. Colour says nothing about monitoring.</span>
          <span className="small dim">Crimea is Ukrainian, occupied, and monitored within the Russia theatre; only the monitored parts of Russia are outlined.</span>
        </div>
      ) : (
        <div className="map-legend-mini">
          <span><i style={{ background: MONITORED_FALLBACK }} /> monitored system (same colour for all — not a measure)</span>
          <span><i style={{ background: OCCUPIED }} /> Crimea: Ukrainian, occupied; monitored within the Russia theatre</span>
        </div>
      )}
      {exportMsg && <p className="small" role="status">{exportMsg}</p>}
      {card && ctx && <ContextCard row={card} ctx={ctx} note={noteOf.get(card.a3)} onClose={() => setCardA3(null)} />}
      {ctx && <WorldProfile ctx={ctx} partly={partly} onContext={setCardA3} />}
    </section>
  );
}

function WorldProfile({ ctx, partly, onContext }: { ctx: EnergyContext; partly: Set<string>; onContext: (a3: string) => void }) {
  const w = ctx.world.values;
  const total = w.total_production;
  const monitored = ctx.countries.filter((r) => r.system_id).reduce((a, r) => a + (r.values.total_production ?? 0), 0);
  const fake: ContextRow = { a3: "WLD", name: "World", on_map: false, system_id: null, values: w, newer: {}, roles: { overall: null, by_commodity: {} } };
  const shares = mixShares(fake);
  // Alphabetical, so the answer to "who produces the most" carries no position.
  const largest = [...ctx.countries].sort((a, b) => (b.values.total_production ?? 0) - (a.values.total_production ?? 0))
    .slice(0, 6).map((r) => r.name).sort((a, b) => a.localeCompare(b));
  return (
    <div className="panel global-note world-profile">
      <div className="eyebrow">World energy profile, {ctx.comparison_year}</div>
      <p className="small">
        World production: {fmtValue(total, ctx.metrics.total_production.unit)}.{" "}
        {shares.map((s) => `${s.label} ${Math.round(s.share * 100)}%`).join(" · ")}.
        {total ? ` The countries containing the six monitored systems produced ${Math.round((monitored / total) * 100)}% of it; the map shows the rest for context only.` : ""}
      </p>
      <p className="small">Six largest producers in {ctx.comparison_year}, alphabetically: {largest.join(", ")}. Size says nothing about disruption.</p>
      <details>
        <summary className="small">National figures table ({ctx.countries.length} countries and territories)</summary>
        <NationalTable ctx={ctx} partly={partly} onContext={onContext} />
      </details>
      <SourceLine ctx={ctx} />
      <p className="small dim">{ctx.not_scoring}</p>
    </div>
  );
}
