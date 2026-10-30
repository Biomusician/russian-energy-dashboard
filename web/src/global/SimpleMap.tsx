import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";

/** A plain polygon map for the global home and the country views.
 *
 *  Deliberately small. The theatre's MapPanel carries a decade of Russia-specific layers
 *  (pipelines, assets, halos, Crimea framing); a country view needs none of them, and reusing it
 *  would drag every one of its assumptions into five new places. No basemap, no external
 *  requests: the polygons are the map, as everywhere else in this project.
 *
 *  `fill` is a MapLibre expression over feature properties. It is the caller's decision what the
 *  colour means, and the caller writes the legend that says so.
 */

const EMPTY_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: "bg", type: "background", paint: { "background-color": "#05070a" } }],
};

export interface SimpleMapProps {
  data: GeoJSON.FeatureCollection;
  bounds: [number, number, number, number];
  fill: maplibregl.ExpressionSpecification | string;
  /** Feature property that identifies a feature for picking and selection. */
  idProp: string;
  selected?: string | null;
  onPick?: (id: string | null, props: Record<string, unknown> | null) => void;
  /** A filter on which features may be picked (e.g. only monitored countries). */
  pickable?: (props: Record<string, unknown>) => boolean;
  ariaLabel: string;
  attribution: string;
  onMap?: (m: maplibregl.Map | null) => void;
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
      fitBoundsOptions: { padding: 24 },
      attributionControl: false,
      maxZoom: 8,
      dragRotate: false,
      renderWorldCopies: false,
    });
    map.current = m;
    // The same readiness signal the theatre map publishes, so the browser tests can wait for a
    // genuinely drawn map rather than a timeout.
    const el = m.getContainer();
    el.dataset.mapState = "loading";
    m.on("movestart", () => { el.dataset.mapState = "moving"; });
    m.on("idle", () => { el.dataset.mapState = "idle"; });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
    m.addControl(new maplibregl.AttributionControl({ customAttribution: props.attribution, compact: true }));

    m.on("load", () => {
      m.addSource("polys", { type: "geojson", data: latest.current.data });
      m.addLayer({ id: "fill", type: "fill", source: "polys",
                   paint: { "fill-color": latest.current.fill as maplibregl.ExpressionSpecification,
                            "fill-opacity": 0.92 } });
      m.addLayer({ id: "line", type: "line", source: "polys",
                   paint: { "line-color": "#2a3846", "line-width": 0.6 } });
      m.addLayer({ id: "sel", type: "line", source: "polys",
                   filter: ["==", ["get", latest.current.idProp], latest.current.selected ?? "\u0000"],
                   paint: { "line-color": "#2ad4ee", "line-width": 2 } });
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
    });
    m.on("mouseleave", "fill", () => { m.getCanvas().style.cursor = ""; });

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
    m.setFilter("sel", ["==", ["get", props.idProp], props.selected ?? "\u0000"]);
  }, [props.selected, props.idProp]);

  return <div ref={box} className="simple-map" role="region" aria-label={props.ariaLabel} />;
}
