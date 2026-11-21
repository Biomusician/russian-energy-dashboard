import { useEffect, useReducer, useRef, useState, type MouseEvent } from "react";
import maplibregl from "maplibre-gl";
import { MapLoadIndicator } from "../components/MapLoadIndicator";
import { MAP_LOAD_INITIAL, mapLoadReducer } from "../mapLoad";
import type { MapHits } from "./homeSelection";
import "../styles/map.css";

/** A plain polygon map for the global home, the country views and the regional view.
 *
 *  Deliberately small. The theatre's MapPanel carries a decade of Russia-specific layers
 *  (pipelines, assets, halos, Crimea framing); a country view needs none of them, and reusing it
 *  would drag every one of its assumptions into five new places. No basemap, no external
 *  requests: the polygons are the map, as everywhere else in this project. Labels, credits and
 *  controls are HTML around the canvas, never map symbol layers (those need a glyph server).
 *
 *  `fill` is a MapLibre expression over feature properties. It is the caller's decision what the
 *  colour means, and the caller writes the legend that says so.
 */

const EMPTY_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: "bg", type: "background", paint: { "background-color": "#05070a" } }],
};

/** The layers that mark what the reader is pointing at or has chosen. They belong to this screen
 *  and this reader, so an exported image leaves them out (see `withoutHighlight`). The small
 *  systems' dots (iteration 23) are a way to click, not data, so an export leaves them out too. */
export const HIGHLIGHT_LAYERS = ["sel", "hl", "sel-cover", "hl-cover", "locator", "markers", "markers-hit"];

/** A copy of a map style with the reader's own selection and hover marks removed. */
export function withoutHighlight(style: maplibregl.StyleSpecification): maplibregl.StyleSpecification {
  return { ...style, layers: style.layers.filter((l) => !HIGHLIGHT_LAYERS.includes(l.id)) };
}

const FIT_PADDING = 24;
// How far from a marker's centre a click still means it, in CSS pixels.
const MARKER_REACH = 12;
const NONE = "\u0000";
const NO_FEATURE: maplibregl.ExpressionSpecification = ["==", ["get", "a3"], NONE];

/** A filter matching features whose `expr` is `value`, or is any of `value` when it is a list. */
function matchFilter(expr: unknown, value: string | string[] | null | undefined): maplibregl.ExpressionSpecification {
  if (Array.isArray(value)) return (value.length ? ["in", expr, ["literal", value]] : NO_FEATURE) as maplibregl.ExpressionSpecification;
  return ["==", expr, value ?? NONE] as maplibregl.ExpressionSpecification;
}

/** Diagonal lines for the occupied hatch, drawn once into an image: a texture, not a colour, so the
 *  status is not carried by colour alone. */
function hatchImage(color: string): ImageData | null {
  const n = 8;
  const c = document.createElement("canvas");
  c.width = n; c.height = n;
  const g = c.getContext("2d");
  if (!g) return null;
  g.strokeStyle = color;
  g.lineWidth = 1.5;
  g.beginPath();
  g.moveTo(0, n); g.lineTo(n, 0);
  g.moveTo(-n / 2, n / 2); g.lineTo(n / 2, -n / 2);
  g.moveTo(n / 2, n * 1.5); g.lineTo(n * 1.5, n / 2);
  g.stroke();
  return g.getImageData(0, 0, n, n);
}

function setLocator(m: maplibregl.Map, at: [number, number] | null | undefined) {
  const src = m.getSource("locator") as maplibregl.GeoJSONSource | undefined;
  src?.setData({ type: "FeatureCollection",
                 features: at ? [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: at } }] : [] });
}

const NO_POINTS: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

function reducedMotion(): boolean {
  return !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

export interface SimpleMapProps {
  data: GeoJSON.FeatureCollection;
  bounds: [number, number, number, number];
  fill: maplibregl.ExpressionSpecification | string;
  /** Feature property that identifies a feature for picking and selection. */
  idProp: string;
  /** One id, or (iteration 23) several, such as a regional group's members. */
  selected?: string | string[] | null;
  /** A lighter, dashed mark for what the reader is pointing at in a list beside the map. */
  highlighted?: string | string[] | null;
  /** Iteration 23: what `selected` and `highlighted` are compared with, when it is not simply the
   *  `idProp` property (the home compares a feature's system, else its country). */
  matchExpr?: unknown;
  /** Iteration 23: draw the hover and selection marks around the whole matched unit, with its
   *  internal borders hidden, so a unit of many polygons reads as one shape. */
  dissolve?: boolean;
  /** Iteration 23: features drawn with a hatch (a filter), in this colour. Null draws none. */
  hatch?: { filter: unknown; color: string } | null;
  /** Iteration 23: a ring at this point, for a place too small to see at the current zoom. */
  locator?: [number, number] | null;
  /** Iteration 23: move the view to this box whenever it changes. */
  fitTo?: [number, number, number, number] | null;
  /** Iteration 23 (MU-01): fixed-size dots, in `color`, for places too small to click at the
   *  current zoom, each with a wider invisible area around it that takes the click. Each point
   *  carries the same properties as its place's polygons. Null draws none. */
  markers?: { data: GeoJSON.FeatureCollection; color: string } | null;
  /** A click within reach of a marker: the markers drawn under the pointer (`core`), the markers
   *  in reach (`near`) and the polygon under it (`under`). The caller decides between one place and
   *  a choice. */
  onPickMany?: (hits: MapHits, how: { touch: boolean }) => void;
  /** `how.touch` says whether the click came from a finger, where the caller may preview rather
   *  than open. */
  onPick?: (id: string | null, props: Record<string, unknown> | null, how?: { touch: boolean }) => void;
  /** A filter on which features may be picked (e.g. only monitored countries). */
  pickable?: (props: Record<string, unknown>) => boolean;
  /** Features drawn with a thick outline: a mark independent of fill colour. */
  outlineFilter?: maplibregl.ExpressionSpecification;
  /** `hits`: what is in reach of the pointer, when a marker is. */
  onHover?: (props: Record<string, unknown> | null, hits?: MapHits) => void;
  ariaLabel: string;
  attribution: string;
  /** Said over the map when nothing on it is shaded, so an empty map is never read as a quiet one. */
  emptyMessage?: string | null;
  /** A short line laid on the map saying what state it is in (e.g. geography only). */
  note?: string | null;
  /** The table that carries the same figures, for a reader who cannot or would rather not use the map. */
  tableHref?: string;
  onMap?: (m: maplibregl.Map | null) => void;
  /** Iteration 21: on a scrolling page the wheel scrolls the page. The map zooms with Ctrl/⌘ and
   *  the wheel, with the buttons, or with the plain wheel after the reader clicks into it, until
   *  the pointer leaves. Touch needs two fingers to move the map. */
  pageScrollsFirst?: boolean;
  /** The caller's own data file (the figures that colour the map) has not arrived yet: the map box
   *  says "Loading data…" until it does, even when the polygons are already drawn. */
  loadingData?: boolean;
  /** Where the same information is without the map, said if the map cannot be drawn. */
  alternative?: string;
}

/** Follow an in-page link to a table that may sit inside a closed disclosure. */
function openTable(href: string, e: MouseEvent) {
  const target = document.querySelector<HTMLElement>(href);
  if (!target) return;
  e.preventDefault();
  const details = target.closest("details");
  if (details) details.open = true;
  target.scrollIntoView({ block: "start" });
  if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
  target.focus({ preventScroll: true });
}

export default function SimpleMap(props: SimpleMapProps) {
  const box = useRef<HTMLDivElement | null>(null);
  const map = useRef<maplibregl.Map | null>(null);
  // The latest callbacks, so the map is created once and still calls the current handlers.
  const latest = useRef(props);
  latest.current = props;
  // What the map box is waiting for (iteration 22). Driven by MapLibre's own events below and by
  // the caller's load promise, never by a timer.
  const [load, dispatch] = useReducer(mapLoadReducer, MAP_LOAD_INITIAL);
  // "Try again" builds the map afresh.
  const [attempt, setAttempt] = useState(0);

  useEffect(() => { dispatch({ type: "data_pending", pending: !!props.loadingData }); }, [props.loadingData]);

  useEffect(() => {
    if (!box.current) return;
    let m: maplibregl.Map;
    try {
      m = new maplibregl.Map({
        container: box.current,
        style: EMPTY_STYLE,
        bounds: props.bounds,
        fitBoundsOptions: { padding: FIT_PADDING },
        attributionControl: false,
        maxZoom: 8,
        dragRotate: false,
        renderWorldCopies: false,
        cooperativeGestures: !!props.pageScrollsFirst,
      });
    } catch (err) {
      // No WebGL, or the browser refused a context. The box says so instead of staying blank; the
      // list or table beside the map does not need it.
      dispatch({ type: "failed", message: err instanceof Error ? err.message : String(err) });
      return;
    }
    map.current = m;
    m.touchZoomRotate.disableRotation();
    if (props.pageScrollsFirst) {
      // A click is a request to use the map: plain-wheel zoom until the pointer leaves it.
      m.getCanvasContainer().addEventListener("mousedown", () => m.cooperativeGestures.disable());
      m.getContainer().addEventListener("mouseleave", () => m.cooperativeGestures.enable());
    }
    // The same readiness signal the theatre map publishes, so the browser tests can wait for a
    // genuinely drawn map rather than a timeout.
    const el = m.getContainer();
    el.dataset.mapState = "loading";
    m.on("movestart", () => { el.dataset.mapState = "moving"; });
    m.on("idle", () => {
      el.dataset.mapState = "idle";
      // Where the view rests (iteration 23), so a browser test can find a place on the canvas.
      const c = m.getCenter();
      el.dataset.mapView = `${c.lng},${c.lat},${m.getZoom()}`;
      // Idle before the polygons were handed over is an empty style at rest, not a drawn map.
      if (m.getSource("polys")) dispatch({ type: "idle" });
    });
    m.on("sourcedata", (e) => { if (e.sourceId === "polys" && e.isSourceLoaded) dispatch({ type: "geometry_loaded" }); });
    m.on("error", (e) => dispatch({ type: "failed", message: e.error?.message ?? "the map reported an error" }));

    m.on("load", () => {
      const cur = latest.current;
      const expr = cur.matchExpr ?? ["get", cur.idProp];
      m.addSource("polys", { type: "geojson", data: cur.data });
      m.addLayer({ id: "fill", type: "fill", source: "polys",
                   paint: { "fill-color": cur.fill as maplibregl.ExpressionSpecification,
                            "fill-opacity": 0.92 } });
      m.addLayer({ id: "line", type: "line", source: "polys",
                   paint: { "line-color": "#2a3846", "line-width": 0.6 } });
      if (cur.outlineFilter) {
        m.addLayer({ id: "outline", type: "line", source: "polys", filter: cur.outlineFilter,
                     paint: { "line-color": "#f4f7fb", "line-width": 2 } });
      }
      if (cur.dissolve) {
        // Neutral marks, never a data colour: dashed for pointing, solid and wider for chosen. Each
        // line is drawn twice as wide and the unit's own fill laid back over it, which hides the
        // inner half of the line and every border inside the unit (iteration 23).
        m.addLayer({ id: "hl", type: "line", source: "polys", filter: matchFilter(expr, cur.highlighted),
                     paint: { "line-color": "#e6edf5", "line-width": 4, "line-dasharray": [2, 1.2] } });
        m.addLayer({ id: "hl-cover", type: "fill", source: "polys", filter: matchFilter(expr, cur.highlighted),
                     paint: { "fill-color": cur.fill as maplibregl.ExpressionSpecification, "fill-opacity": 0.92 } });
        m.addLayer({ id: "sel", type: "line", source: "polys", filter: matchFilter(expr, cur.selected),
                     paint: { "line-color": "#ffffff", "line-width": 6 } });
        m.addLayer({ id: "sel-cover", type: "fill", source: "polys", filter: matchFilter(expr, cur.selected),
                     paint: { "fill-color": cur.fill as maplibregl.ExpressionSpecification, "fill-opacity": 0.92 } });
      } else {
        // Above the outline, so a chosen member is visible even where every member is outlined.
        m.addLayer({ id: "hl", type: "line", source: "polys", filter: matchFilter(expr, cur.highlighted),
                     paint: { "line-color": "#9beaf7", "line-width": 2.5, "line-dasharray": [2, 1] } });
        m.addLayer({ id: "sel", type: "line", source: "polys", filter: matchFilter(expr, cur.selected),
                     paint: { "line-color": "#2ad4ee", "line-width": 3.5 } });
      }
      if (cur.hatch !== undefined) {
        const img = hatchImage(cur.hatch?.color ?? "#cccccc");
        if (img) m.addImage("hatch", img);
        m.addLayer({ id: "hatch", type: "fill", source: "polys",
                     filter: (cur.hatch?.filter ?? NO_FEATURE) as maplibregl.ExpressionSpecification,
                     paint: { "fill-pattern": "hatch" } });
      }
      if (cur.markers !== undefined) {
        m.addSource("markers", { type: "geojson", data: cur.markers?.data ?? NO_POINTS });
        // The hit area is a transparent circle wider than the dot: a finger needs more than a dot.
        m.addLayer({ id: "markers-hit", type: "circle", source: "markers",
                     paint: { "circle-radius": MARKER_REACH, "circle-color": "rgba(0,0,0,0)" } });
        m.addLayer({ id: "markers", type: "circle", source: "markers",
                     paint: { "circle-radius": 5, "circle-color": cur.markers?.color ?? "#8a96a3", "circle-opacity": 0.92,
                              "circle-stroke-color": "#2a3846", "circle-stroke-width": 1 } });
      }
      if (cur.locator !== undefined) {
        m.addSource("locator", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
        m.addLayer({ id: "locator", type: "circle", source: "locator",
                     paint: { "circle-radius": 13, "circle-color": "rgba(0,0,0,0)", "circle-stroke-color": "#ffffff", "circle-stroke-width": 2 } });
        setLocator(m, cur.locator);
      }
      cur.onMap?.(m);
    });

    // What lies under a point: markers in reach first (a dot is what the reader aimed at), then the
    // one polygon under the pointer. Without markers this is exactly the polygon, as before.
    const reach = (pt: maplibregl.PointLike) => {
      const { pickable } = latest.current;
      const at = (layer: string) => (m.getLayer(layer) ? m.queryRenderedFeatures(pt, { layers: [layer] }) : [])
        .map((f) => f.properties as Record<string, unknown>)
        .filter((p) => !!p && (!pickable || pickable(p)));
      return { core: at("markers"), near: at("markers-hit"), under: at("fill").slice(0, 1) };
    };
    m.on("click", (e) => {
      const { onPick, onPickMany, idProp } = latest.current;
      const hits = reach(e.point);
      const { near, under } = hits;
      // A finger on a phone or tablet: the caller may show what was tapped before opening it.
      const ev = e.originalEvent as PointerEvent | undefined;
      const touch = ev?.pointerType === "touch" || ev?.pointerType === "pen" || !!window.matchMedia?.("(hover: none)").matches;
      if (near.length > 0 && onPickMany) { onPickMany(hits, { touch }); return; }
      const p = near[0] ?? under[0];
      if (p) onPick?.(String(p[idProp]), p, { touch });
    });
    m.on("mousemove", (e) => {
      const hits = reach(e.point);
      const all = [...hits.near, ...hits.under];
      m.getCanvas().style.cursor = all.length ? "pointer" : "";
      latest.current.onHover?.(all[0] ?? null, hits.near.length ? hits : undefined);
    });
    m.getCanvas().addEventListener("mouseleave", () => { m.getCanvas().style.cursor = ""; latest.current.onHover?.(null); });

    return () => {
      latest.current.onMap?.(null);
      m.remove();
      map.current = null;
    };
    // Created once per mount, and again on "Try again"; data and selection changes are applied below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt]);

  // Compared as text: a caller that builds a new list on every render does not refilter the map.
  const selKey = JSON.stringify(props.selected ?? null);
  const hlKey = JSON.stringify(props.highlighted ?? null);
  useEffect(() => {
    const m = map.current;
    if (!m || !m.getLayer("sel")) return;
    const f = matchFilter(props.matchExpr ?? ["get", props.idProp], props.selected);
    m.setFilter("sel", f);
    if (m.getLayer("sel-cover")) m.setFilter("sel-cover", f);
  }, [selKey, props.idProp]);  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const m = map.current;
    if (!m || !m.getLayer("hl")) return;
    const f = matchFilter(props.matchExpr ?? ["get", props.idProp], props.highlighted);
    m.setFilter("hl", f);
    if (m.getLayer("hl-cover")) m.setFilter("hl-cover", f);
  }, [hlKey, props.idProp]);  // eslint-disable-line react-hooks/exhaustive-deps

  // The colour may change after load (a metric selector); the map is not recreated for it.
  useEffect(() => {
    const m = map.current;
    if (!m || !m.getLayer("fill")) return;
    m.setPaintProperty("fill", "fill-color", props.fill as maplibregl.ExpressionSpecification);
    for (const id of ["hl-cover", "sel-cover"]) {
      if (m.getLayer(id)) m.setPaintProperty(id, "fill-color", props.fill as maplibregl.ExpressionSpecification);
    }
  }, [props.fill]);

  // Iteration 23: what changes with the home map's mode, applied without recreating the map.
  const outlineKey = JSON.stringify(props.outlineFilter ?? null);
  useEffect(() => {
    const m = map.current;
    if (!m || !m.getLayer("outline") || !props.outlineFilter) return;
    m.setFilter("outline", props.outlineFilter);
  }, [outlineKey]);  // eslint-disable-line react-hooks/exhaustive-deps

  const hatchKey = JSON.stringify(props.hatch?.filter ?? null);
  useEffect(() => {
    const m = map.current;
    if (!m || !m.getLayer("hatch")) return;
    m.setFilter("hatch", (props.hatch?.filter ?? NO_FEATURE) as maplibregl.ExpressionSpecification);
  }, [hatchKey]);  // eslint-disable-line react-hooks/exhaustive-deps

  const markersKey = JSON.stringify(props.markers ?? null);
  useEffect(() => {
    const m = map.current;
    const src = m?.getSource("markers") as maplibregl.GeoJSONSource | undefined;
    src?.setData(props.markers?.data ?? NO_POINTS);
  }, [markersKey]);  // eslint-disable-line react-hooks/exhaustive-deps

  const locatorKey = JSON.stringify(props.locator ?? null);
  useEffect(() => {
    const m = map.current;
    if (m && m.getSource("locator")) setLocator(m, props.locator ?? null);
  }, [locatorKey]);  // eslint-disable-line react-hooks/exhaustive-deps

  const fitKey = JSON.stringify(props.fitTo ?? null);
  useEffect(() => {
    const m = map.current;
    if (!m || !props.fitTo) return;
    // A phone-width map keeps little padding, or a group's smallest member is a few pixels wide.
    const padding = m.getContainer().clientWidth < 600 ? FIT_PADDING / 2 : FIT_PADDING * 2;
    m.fitBounds(props.fitTo, { padding, maxZoom: 5.5, duration: reducedMotion() ? 0 : 600 });
  }, [fitKey]);  // eslint-disable-line react-hooks/exhaustive-deps

  const zoomBy = (d: number) => { const m = map.current; if (m) (d > 0 ? m.zoomIn() : m.zoomOut()); };
  const reset = () => map.current?.fitBounds(latest.current.bounds, { padding: FIT_PADDING });
  const retry = () => { dispatch({ type: "retry" }); setAttempt((a) => a + 1); };

  return (
    <div className="simple-map-shell">
      <div className="simple-map-stage">
        <div ref={box} className="simple-map" role="region" aria-label={props.ariaLabel} />
        <div className="map-tools" role="group" aria-label="Map view">
          <button type="button" className="map-tool" aria-label="Zoom in" title="Zoom in" onClick={() => zoomBy(1)}>+</button>
          <button type="button" className="map-tool" aria-label="Zoom out" title="Zoom out" onClick={() => zoomBy(-1)}>−</button>
          <button type="button" className="map-tool map-tool-text" title="Fit the whole map in view" onClick={reset}>Reset view</button>
        </div>
        <MapLoadIndicator state={load} onRetry={retry}
          alternative={props.alternative ?? (props.tableHref ? "The table below has the same data." : undefined)} />
        {props.emptyMessage ? <div className="map-empty-note" role="status">{props.emptyMessage}</div>
          : props.note ? <div className="map-empty-note map-state-note">{props.note}</div> : null}
      </div>
      <p className="map-credits">
        {props.attribution}
        {props.tableHref && <>{" "}<a href={props.tableHref} onClick={(e) => openTable(props.tableHref!, e)}>Same data as a table</a></>}
      </p>
    </div>
  );
}
