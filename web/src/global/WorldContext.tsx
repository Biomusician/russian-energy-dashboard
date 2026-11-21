import { useEffect, useMemo, useRef, useState } from "react";
import type maplibregl from "maplibre-gl";
import SimpleMap, { withoutHighlight } from "./SimpleMap";
import { loadContext, modesFor, type EnergyContext, type MapMode } from "./context";
import { composeContextFrame, contextFilename } from "./contextExport";
import { loadWorld, type Manifest } from "./manifest";
import { MapGeometryPlaceholder } from "../components/MapLoadIndicator";
import { downloadBlob, exportMapPng } from "../mapExport";
import { MAP_COLOURS, NAV_FILL, NAV_HATCH, UNIT_EXPR, hoverLabel, type Bbox, type WorldIndex } from "./homeSelection";

// The country pages read the national figures from here; they now live beside the table.
export { NationalFigures } from "./NationalContext";

/** The home page's world map (iteration 18; map-first since iteration 23).
 *
 *  TWO MODES, ONE MAP. "Where to explore" (the default) colours only what one click does: a
 *  monitored system, in one neutral colour for the theatre and the countries alike; Crimea and
 *  Sevastopol with the occupied hatch; everything else the base colour. Nothing is coloured by a
 *  count, a score, an index value or a maturity, and impact-record presence is told on hover and in
 *  the selection card, never painted. "National energy" is the iteration-18 context map unchanged:
 *  a national figure for colour, monitoring as a separate thick outline, a PNG export.
 *
 *  The map is never the only route. The panel beside it lists every destination as text and the
 *  search finds every country; this component is loaded lazily and the page works without it.
 */

export type HomeMapMode = "explore" | "energy";

const WORLD_BOUNDS: Bbox = [-170, -50, 179, 78];
const NOTHING = ["==", ["get", "a3"], "\u0000"];
const MONITORED = ["!=", ["get", "system_id"], null];
// A place drawn smaller than this, in CSS pixels, gets a ring when it is pointed at.
const SMALL_PX = 14;

export default function WorldContext({ world, worldError, manifest, index, mode, onMode, selected, highlighted, fitTo, onPick }: {
  world: GeoJSON.FeatureCollection | null; worldError: string | null; manifest: Manifest | null; index: WorldIndex | null;
  mode: HomeMapMode; onMode: (m: HomeMapMode) => void;
  selected: string[]; highlighted: string | string[] | null; fitTo: Bbox | null;
  onPick: (props: Record<string, unknown>, how: { touch: boolean }) => void;
}) {
  const [ctx, setCtx] = useState<EnergyContext | null>(null);
  const [ctxError, setCtxError] = useState<string | null>(null);
  const [metric, setMetric] = useState<string | null>(null);
  const [hover, setHover] = useState<{ unit: string; text: string } | null>(null);
  const [exportMsg, setExportMsg] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [moved, setMoved] = useState(0);
  const mapRef = useRef<maplibregl.Map | null>(null);
  // "Try again" on a map file that failed (iteration 22): asked for again here. The loader never
  // keeps a failed request, so this is a new one, and the page's own state is left alone.
  const [retried, setRetried] = useState<GeoJSON.FeatureCollection | null>(null);
  const [retrying, setRetrying] = useState(false);
  const retryWorld = () => {
    setRetrying(true);
    loadWorld().then(setRetried).catch(() => undefined).finally(() => setRetrying(false));
  };
  const shownWorld = world ?? retried;

  // The national figures are fetched only when the reader asks for them (iteration 23): the
  // default map does not use them, and they are 165 kB.
  useEffect(() => {
    if (mode !== "energy" || ctx) return;
    let live = true;
    setCtxError(null);
    loadContext().then((c) => { if (live) setCtx(c); })
      .catch((e) => { if (live) setCtxError(e instanceof Error ? e.message : String(e)); });
    return () => { live = false; };
  }, [mode, ctx]);

  const modes = useMemo(() => (ctx ? modesFor(ctx) : []), [ctx]);
  const energy: MapMode | null = modes.find((m) => m.id === metric) ?? modes[0] ?? null;
  const byA3 = useMemo(() => new Map((ctx?.countries ?? []).map((r) => [r.a3, r])), [ctx]);
  const explore = mode === "explore";
  const fill = (explore || !energy ? NAV_FILL : energy.fill) as maplibregl.ExpressionSpecification;

  // What the pointer is over is outlined as a whole unit; otherwise whatever the panel points at.
  const pointed = hover?.unit ?? highlighted;
  // A ring for one small place pointed at or chosen (Bahrain is a few pixels wide at world zoom).
  const ringUnit = typeof pointed === "string" ? pointed : selected.length === 1 ? selected[0] : null;
  const locator = useMemo((): [number, number] | null => {
    const m = mapRef.current;
    const b = ringUnit ? index?.bounds.get(ringUnit) : undefined;
    if (!m || !b) return null;
    const a = m.project([b[0], b[1]]);
    const c = m.project([b[2], b[3]]);
    if (Math.max(Math.abs(c.x - a.x), Math.abs(c.y - a.y)) >= SMALL_PX) return null;
    return [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2];
  }, [ringUnit, index, moved]);  // eslint-disable-line react-hooks/exhaustive-deps

  const runExport = async () => {
    const m = mapRef.current;
    if (!m || !ctx || !energy) { setExportMsg("The map is not ready yet."); return; }
    setExporting(true);
    setExportMsg(null);
    try {
      const res = await exportMapPng({
        source: m, width: 1600, height: 900, pixelRatio: 1,
        // The reader's own hover and selection marks stay on the screen, not in the file.
        transformStyle: (s) => { const clean = withoutHighlight(s); return { ...clean, layers: clean.layers.filter((l) => l.id !== "hatch") }; },
        compose: (c) => composeContextFrame(c, ctx, energy, manifest?.systems.map((s) => s.name) ?? []),
      });
      downloadBlob(res.blob, contextFilename(ctx, energy));
      setExportMsg(`Exported ${res.width}×${res.height}.`);
    } catch (err) {
      setExportMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setExporting(false);
    }
  };

  const describeEnergy = (p: Record<string, unknown>) => {
    const row = byA3.get(String(p.a3));
    const value = energy ? energy.describe(row) : "";
    // The figure belongs to the country; Crimea has no national figure of its own.
    const occupied = p.status === "occupied";
    const name = occupied ? `${row?.name ?? String(p.a3)} (national figure)` : String(p.name ?? p.a3);
    return `${name}${value ? `: ${value}` : ""}`;
  };

  return (
    <section aria-label="World map" className="home-map">
      <div className="home-map-bar">
        <div className="home-mode" role="group" aria-label="Map mode">
          <button type="button" className="ghost" aria-pressed={explore} onClick={() => onMode("explore")}>Where to explore</button>
          <button type="button" className="ghost" aria-pressed={!explore} onClick={() => onMode("energy")}>National energy</button>
        </div>
        {!explore && energy && (
          <>
            <label className="small">Colour by{" "}
              <select aria-label="Map metric" value={energy.id} onChange={(e) => setMetric(e.target.value)}>
                {modes.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}
              </select>
            </label>
            <button className="ghost" type="button" onClick={runExport} disabled={exporting}>{exporting ? "Rendering…" : "Download PNG"}</button>
          </>
        )}
      </div>
      {!explore && ctxError && (
        <p className="warn-text small" role="alert">Global energy context unavailable. The monitored systems are not affected.</p>
      )}
      <div className="home-map-box">
        {shownWorld ? (
          <SimpleMap
            data={shownWorld}
            bounds={WORLD_BOUNDS}
            loadingData={!explore && !ctx && !ctxError}
            alternative="The list beside the map has every destination, and the search finds every country."
            idProp="a3"
            matchExpr={UNIT_EXPR}
            dissolve
            selected={selected}
            highlighted={pointed}
            fill={fill}
            outlineFilter={(explore ? NOTHING : MONITORED) as maplibregl.ExpressionSpecification}
            hatch={explore ? { filter: NAV_HATCH, color: MAP_COLOURS.hatch } : null}
            locator={locator}
            fitTo={fitTo}
            onPick={(_id, p, how) => { if (p) onPick(p, how ?? { touch: false }); }}
            onHover={(p) => {
              if (!p || !manifest) { setHover(null); return; }
              const unit = p.system_id ? String(p.system_id) : String(p.a3);
              setHover({ unit, text: explore ? hoverLabel(p, index, manifest) : describeEnergy(p) });
            }}
            ariaLabel={explore
              ? "World map: where to explore. Monitored systems share one colour. The list “Where to explore” beside the map has every destination as text, and the search finds every country."
              : `World map coloured by ${energy?.title ?? "national energy figures"}. Monitored systems have a thick outline. The national figures table below the map has every figure.`}
            attribution={`${explore ? "" : "Energy data: U.S. EIA International Energy Statistics. "}Boundaries: Natural Earth, line of actual control; Crimea drawn as Ukrainian territory under Russian occupation. Ctrl (⌘) + scroll zooms.`}
            onMap={(m) => {
              mapRef.current = m;
              m?.on("moveend", () => setMoved((n) => n + 1));
              setMoved((n) => n + 1);
            }}
            pageScrollsFirst
          />
        ) : (
          <MapGeometryPlaceholder failed={!!worldError && !retrying} onRetry={retryWorld}
            alternative="The list beside the map has every destination, and the search finds every country." />
        )}
        {/* Pointer only, and said again in the panel and the card: aria-hidden so it is not read twice. */}
        <div className="home-map-label small" aria-hidden="true">{hover?.text ?? ""}</div>
      </div>
      {explore ? (
        <div className="map-legend-mini home-legend" aria-label="Map legend">
          <span><i style={{ background: MAP_COLOURS.monitored }} />Monitored system: the theatre or a country system (one colour; not a measure)</span>
          <span><i className="hatch-swatch" />Crimea and Sevastopol: Ukrainian territory under Russian occupation, monitored in the theatre</span>
          <span><i style={{ background: MAP_COLOURS.base }} />No monitored system: select a country to see what this site holds for it</span>
        </div>
      ) : energy ? (
        <div className="map-legend-mini" aria-label="Map legend">
          <span className="legend-title"><strong>{energy.title}</strong> <span className="dim">({energy.unitNote})</span></span>
          {energy.legend.map((l) => <span key={l.label}><i style={{ background: l.color }} />{l.label}</span>)}
          <span className="legend-monitored"><i className="outline-swatch" /> Thick outline: systematically monitored. Colour says nothing about monitoring.</span>
          <span className="small dim">Crimea is Ukrainian, occupied, and monitored in the Russia, Belarus &amp; Crimea view; only the monitored parts of Russia are outlined.</span>
        </div>
      ) : (
        <div className="map-legend-mini" aria-label="Map legend"><span className="dim">{ctxError ? "National energy figures could not be loaded." : "Loading national energy figures…"}</span></div>
      )}
      {exportMsg && <p className="small" role="status">{exportMsg}</p>}
    </section>
  );
}
