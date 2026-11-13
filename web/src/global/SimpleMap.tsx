import { useEffect, useRef, type MouseEvent } from "react";
import maplibregl from "maplibre-gl";
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
 *  and this reader, so an exported image leaves them out (see `withoutHighlight`). */
export const HIGHLIGHT_LAYERS = ["sel", "hl"];

/** A copy of a map style with the reader's own selection and hover marks removed. */
export function withoutHighlight(style: maplibregl.StyleSpecification): maplibregl.StyleSpecification {
  return { ...style, layers: style.layers.filter((l) => !HIGHLIGHT_LAYERS.includes(l.id)) };
}

const FIT_PADDING = 24;
const NONE = "\u0000";

export interface SimpleMapProps {
  data: GeoJSON.FeatureCollection;
  bounds: [number, number, number, number];
  fill: maplibregl.ExpressionSpecification | string;
  /** Feature property that identifies a feature for picking and selection. */
  idProp: string;
  selected?: string | null;
  /** A lighter, dashed mark for what the reader is pointing at in a list beside the map. */
  highlighted?: string | null;
  onPick?: (id: string | null, props: Record<string, unknown> | null) => void;
  /** A filter on which features may be picked (e.g. only monitored countries). */
  pickable?: (props: Record<string, unknown>) => boolean;
  /** Features drawn with a thick outline: a mark independent of fill colour. */
  outlineFilter?: maplibregl.ExpressionSpecification;
  onHover?: (props: Record<string, unknown> | null) => void;
  ariaLabel: string;
  attribution: string;
  /** Said over the map when nothing on it is shaded, so an empty map is never read as a quiet one. */
  emptyMessage?: string | null;
  /** A short line laid on the map saying what state it is in (e.g. geography only). */
  note?: string | null;
  /** The table that carries the same figures, for a reader who cannot or would rather not use the map. */
  tableHref?: string;
  onMap?: (m: maplibregl.Map | null) => void;
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

  useEffect(() => {
    if (!box.current) return;
    const m = new maplibregl.Map({
      container: box.current,
      style: EMPTY_STYLE,
      bounds: props.bounds,
      fitBoundsOptions: { padding: FIT_PADDING },
      attributionControl: false,
      maxZoom: 8,
      dragRotate: false,
      renderWorldCopies: false,
    });
    map.current = m;
    m.touchZoomRotate.disableRotation();
    // The same readiness signal the theatre map publishes, so the browser tests can wait for a
    // genuinely drawn map rather than a timeout.
    const el = m.getContainer();
    el.dataset.mapState = "loading";
    m.on("movestart", () => { el.dataset.mapState = "moving"; });
    m.on("idle", () => { el.dataset.mapState = "idle"; });

    m.on("load", () => {
      const { idProp } = latest.current;
      m.addSource("polys", { type: "geojson", data: latest.current.data });
      m.addLayer({ id: "fill", type: "fill", source: "polys",
                   paint: { "fill-color": latest.current.fill as maplibregl.ExpressionSpecification,
                            "fill-opacity": 0.92 } });
      m.addLayer({ id: "line", type: "line", source: "polys",
                   paint: { "line-color": "#2a3846", "line-width": 0.6 } });
      if (latest.current.outlineFilter) {
        m.addLayer({ id: "outline", type: "line", source: "polys", filter: latest.current.outlineFilter,
                     paint: { "line-color": "#f4f7fb", "line-width": 2 } });
      }
      // Above the outline, so a chosen member is visible even where every member is outlined.
      m.addLayer({ id: "hl", type: "line", source: "polys",
                   filter: ["==", ["get", idProp], latest.current.highlighted ?? NONE],
                   paint: { "line-color": "#9beaf7", "line-width": 2.5, "line-dasharray": [2, 1] } });
      m.addLayer({ id: "sel", type: "line", source: "polys",
                   filter: ["==", ["get", idProp], latest.current.selected ?? NONE],
                   paint: { "line-color": "#2ad4ee", "line-width": 3.5 } });
      latest.current.onMap?.(m);
    });

    m.on("click", "fill", (e) => {
      const f = e.features?.[0];
      const p = (f?.properties ?? null) as Record<string, unknown> | null;
      const { pickable, onPick, idProp } = latest.current;
      if (!p || (pickable && !pickable(p))) return;
      onPick?.(String(p[idProp]), p);
    });
    m.on("mousemove", "fill", (e) => {
      const p = e.features?.[0]?.properties as Record<string, unknown> | undefined;
      const ok = !!p && (!latest.current.pickable || latest.current.pickable(p));
      m.getCanvas().style.cursor = ok ? "pointer" : "";
      latest.current.onHover?.(p ?? null);
    });
    m.on("mouseleave", "fill", () => { m.getCanvas().style.cursor = ""; latest.current.onHover?.(null); });

    return () => {
      latest.current.onMap?.(null);
      m.remove();
      map.current = null;
    };
    // Created once per mount; data and selection changes are applied below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const m = map.current;
    if (!m || !m.getLayer("sel")) return;
    m.setFilter("sel", ["==", ["get", props.idProp], props.selected ?? NONE]);
  }, [props.selected, props.idProp]);

  useEffect(() => {
    const m = map.current;
    if (!m || !m.getLayer("hl")) return;
    m.setFilter("hl", ["==", ["get", props.idProp], props.highlighted ?? NONE]);
  }, [props.highlighted, props.idProp]);

  // The colour may change after load (a metric selector); the map is not recreated for it.
  useEffect(() => {
    const m = map.current;
    if (!m || !m.getLayer("fill")) return;
    m.setPaintProperty("fill", "fill-color", props.fill as maplibregl.ExpressionSpecification);
  }, [props.fill]);

  const zoomBy = (d: number) => { const m = map.current; if (m) (d > 0 ? m.zoomIn() : m.zoomOut()); };
  const reset = () => map.current?.fitBounds(latest.current.bounds, { padding: FIT_PADDING });

  return (
    <div className="simple-map-shell">
      <div className="simple-map-stage">
        <div ref={box} className="simple-map" role="region" aria-label={props.ariaLabel} />
        <div className="map-tools" role="group" aria-label="Map view">
          <button type="button" className="map-tool" aria-label="Zoom in" title="Zoom in" onClick={() => zoomBy(1)}>+</button>
          <button type="button" className="map-tool" aria-label="Zoom out" title="Zoom out" onClick={() => zoomBy(-1)}>−</button>
          <button type="button" className="map-tool map-tool-text" title="Fit the whole map in view" onClick={reset}>Reset view</button>
        </div>
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
