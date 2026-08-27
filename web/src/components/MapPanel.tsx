import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import type { FilterState } from "../App";
import type { Bundle, Incident } from "../types";
import { CLASS_COLOR, SEVERITY_STOPS } from "../palette";
import { fmtNum } from "../data";

/** The map deliberately has no basemap.
 *
 *  Every tile provider worth using needs an API key, a billing relationship, or an
 *  attribution banner, and none of them would add anything: this is a choropleth of
 *  administrative regions, and streets and terrain underneath it are noise. Rendering
 *  our own GeoJSON on a flat dark ground means the deployed page makes zero external
 *  network requests, works offline, and cannot break when someone else's tile server
 *  changes its terms.
 *
 *  No symbol layers either -- text rendering in MapLibre needs a glyph endpoint, which
 *  would reintroduce exactly that external dependency. Region names live in the
 *  hover card and the dossier instead. */

const EMPTY_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: "bg", type: "background", paint: { "background-color": "#05070a" } }],
};

// Two camera presets (iteration 2). Full AOI frames Belarus through the Siberian FD;
// West/Black Sea zooms the western theatre where most disruption and Crimea sit.
const AOI_BOUNDS: [number, number, number, number] = [17.5, 40.0, 120.0, 74.0];
const WEST_BOUNDS: [number, number, number, number] = [20.0, 41.0, 62.0, 62.0];

// Context-country label anchors worth showing, plus the sea labels. Kept short so the
// map does not turn into a name soup; positioned as HTML overlays (no glyph endpoint).
const SEA_LABELS: { name: string; lon: number; lat: number; size: number }[] = [
  { name: "BLACK SEA", lon: 34.0, lat: 43.3, size: 12 },
  { name: "CASPIAN SEA", lon: 50.5, lat: 41.5, size: 11 },
  { name: "BALTIC SEA", lon: 19.5, lat: 57.6, size: 10 },
  { name: "BARENTS SEA", lon: 40.0, lat: 71.5, size: 10 },
];

// Reveal zoom per context country: the major theatre states show at continental scale;
// smaller/overlapping ones appear only as you zoom in. Deterministic label priority.
const COUNTRY_MINZOOM: Record<string, number> = {
  Ukraine: 0, Kazakhstan: 0, Turkey: 0, Finland: 0, Poland: 0, China: 0, Mongolia: 0,
  Georgia: 2.6, Romania: 2.6, Norway: 2.6, Sweden: 2.8, Azerbaijan: 3.0, Moldova: 3.4,
  Lithuania: 3.4, Latvia: 3.6, Estonia: 3.6, Bulgaria: 3.6, Armenia: 3.6,
  Slovakia: 4.2, Hungary: 4.2, Czechia: 4.2, Germany: 4.2,
  Kyrgyzstan: 4.0, Uzbekistan: 4.0, Turkmenistan: 4.0,
};

interface HoverInfo {
  x: number;
  y: number;
  code: string;
  name: string;
  district: string;
  value: number;
  incidents: number;
  special: boolean;
}

interface ScreenLabel { name: string; x: number; y: number; size: number; kind: "country" | "sea" }

export default function MapPanel({
  bundle, step, filters, selected, onSelect, incidentsByRegion,
}: {
  bundle: Bundle;
  step: number;
  filters: FilterState;
  selected: string | null;
  onSelect: (code: string | null) => void;
  incidentsByRegion: Map<string, Incident[]>;
}) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [ready, setReady] = useState(false);
  const [hover, setHover] = useState<HoverInfo | null>(null);
  const [labels, setLabels] = useState<ScreenLabel[]>([]);

  const regionMeta = useMemo(
    () => new Map(bundle.regions.map((r) => [r.code, r])),
    [bundle.regions],
  );

  /** Points for the infrastructure overlay, rebuilt when the class filter changes. */
  const assetPoints = useMemo<GeoJSON.FeatureCollection>(() => ({
    type: "FeatureCollection",
    features: bundle.assets
      .filter((a) => filters.classes.has(a.asset_class))
      .map((a) => ({
        type: "Feature" as const,
        properties: {
          asset_class: a.asset_class,
          name: a.name ?? "",
          capacity_mw: a.capacity_mw ?? 0,
          region_code: a.region_code,
        },
        geometry: { type: "Point" as const, coordinates: [a.lon, a.lat] },
      })),
  }), [bundle.assets, filters.classes]);

  /** One marker per region that has recorded events, sized by how many.
   *  Placed on the region centroid: these are region-scoped records, and putting a
   *  dot on a facility's real coordinates would imply a precision the dataset does
   *  not have and the scope boundary does not want. */
  const disruptionPoints = useMemo<GeoJSON.FeatureCollection>(() => {
    const feats: GeoJSON.Feature[] = [];
    for (const [code, list] of incidentsByRegion) {
      const meta = regionMeta.get(code);
      if (!meta) continue;
      feats.push({
        type: "Feature",
        properties: { code, count: list.length, name: meta.name },
        geometry: { type: "Point", coordinates: meta.centroid },
      });
    }
    return { type: "FeatureCollection", features: feats };
  }, [incidentsByRegion, regionMeta]);

  // --- init ---------------------------------------------------------------
  useEffect(() => {
    if (!container.current || map.current) return;
    const m = new maplibregl.Map({
      container: container.current,
      style: EMPTY_STYLE,
      bounds: AOI_BOUNDS,
      fitBoundsOptions: { padding: 28 },
      attributionControl: false,
      maxZoom: 9,
      dragRotate: false,
    });
    map.current = m;
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
    m.addControl(
      new maplibregl.AttributionControl({
        customAttribution:
          "Boundaries: Natural Earth (public domain) · Grid &amp; pipelines: OpenStreetMap (ODbL) · " +
          "Generation: WRI Global Power Plant Database (CC BY 4.0) · Events: Wikipedia (CC BY-SA 4.0)",
      }),
      "bottom-right",
    );

    m.on("load", () => {
      // --- context geography (drawn first, underneath everything analytic) ---
      m.addSource("ocean", { type: "geojson", data: bundle.ocean });
      m.addSource("context-land", { type: "geojson", data: bundle.contextLand });
      m.addSource("context-borders", { type: "geojson", data: bundle.contextBorders });

      // Context geography is deliberately subordinate: darker than the analytic surface,
      // faint borders. The sea is a distinct, slightly-blue dark so the Black Sea reads
      // as water rather than void.
      m.addLayer({ id: "ocean-fill", type: "fill", source: "ocean",
        paint: { "fill-color": "#0a1622", "fill-opacity": 1 } });
      m.addLayer({ id: "context-fill", type: "fill", source: "context-land",
        paint: { "fill-color": "#0c1116", "fill-opacity": 1 } });
      m.addLayer({ id: "context-line", type: "line", source: "context-borders",
        paint: { "line-color": "#1a242f", "line-width": 0.5 } });

      m.addSource("regions", {
        type: "geojson",
        data: bundle.regionsGeo,
        promoteId: "code",
      });
      m.addSource("lines", { type: "geojson", data: bundle.linesGeo });
      m.addSource("assets", { type: "geojson", data: assetPoints });
      m.addSource("disruptions", { type: "geojson", data: disruptionPoints });

      // Analytic (Russia+Belarus) regions carry the severity choropleth.
      m.addLayer({
        id: "regions-fill",
        type: "fill",
        source: "regions",
        filter: ["!=", ["get", "special"], true],
        paint: {
          "fill-color": [
            "interpolate", ["linear"], ["coalesce", ["feature-state", "value"], 0],
            ...SEVERITY_STOPS.flatMap(([stop, color]) => [stop, color]),
          ] as unknown as maplibregl.ExpressionSpecification,
          "fill-opacity": 0.92,
        },
      });

      // Crimea (and any context unit): deliberately NOT the Russian-region choropleth.
      // A neutral slate fill with a distinct dashed violet outline marks it as a
      // separately-identified context unit without adjudicating sovereignty by colour.
      m.addLayer({
        id: "special-fill",
        type: "fill",
        source: "regions",
        filter: ["==", ["get", "special"], true],
        paint: { "fill-color": "#2a2438", "fill-opacity": 0.72 },
      });
      m.addLayer({
        id: "special-line",
        type: "line",
        source: "regions",
        filter: ["==", ["get", "special"], true],
        paint: {
          "line-color": [
            "case",
            ["boolean", ["feature-state", "selected"], false], "#c4b5fd",
            "#a98bfa",
          ] as unknown as maplibregl.ExpressionSpecification,
          "line-width": 1.4,
          "line-dasharray": [3, 2],
        },
      });

      m.addLayer({
        id: "regions-line",
        type: "line",
        source: "regions",
        filter: ["!=", ["get", "special"], true],
        paint: {
          "line-color": [
            "case",
            ["boolean", ["feature-state", "selected"], false], "#2ad4ee",
            ["boolean", ["feature-state", "hover"], false], "#7fe3f2",
            "#3a5064",
          ] as unknown as maplibregl.ExpressionSpecification,
          "line-width": [
            "case",
            ["boolean", ["feature-state", "selected"], false], 2.2,
            ["boolean", ["feature-state", "hover"], false], 1.4,
            0.5,
          ] as unknown as maplibregl.ExpressionSpecification,
        },
      });

      m.addLayer({
        id: "network",
        type: "line",
        source: "lines",
        layout: { visibility: "none" },
        paint: {
          "line-color": [
            "match", ["get", "asset_class"],
            "transmission_line", CLASS_COLOR.transmission_line,
            "pipeline_gas", CLASS_COLOR.pipeline_gas,
            "pipeline_oil", CLASS_COLOR.pipeline_oil,
            "#40566a",
          ] as unknown as maplibregl.ExpressionSpecification,
          "line-width": 0.6,
          "line-opacity": 0.5,
        },
      });

      // Individual infrastructure sites only appear once zoomed past the continental
      // scale (iteration 3 declutter). At Full AOI the choropleth + event halos carry
      // the signal; thousands of equally-prominent dots would bury it. As you zoom in,
      // big plants fade in first (minzoom 3.6), then the rest (minzoom 4.6).
      m.addLayer({
        id: "asset-dots",
        type: "circle",
        source: "assets",
        minzoom: 3.6,
        paint: {
          "circle-radius": [
            "interpolate", ["linear"], ["zoom"],
            3.6, ["case", [">", ["get", "capacity_mw"], 1000], 1.8, 0.8],
            8, ["case", [">", ["get", "capacity_mw"], 1000], 7, 3.4],
          ] as unknown as maplibregl.ExpressionSpecification,
          "circle-color": [
            "match", ["get", "asset_class"],
            ...Object.entries(CLASS_COLOR).flatMap(([k, v]) => [k, v]),
            "#5b6b78",
          ] as unknown as maplibregl.ExpressionSpecification,
          // Fade the smaller sites in gradually so the transition is not a hard pop, and
          // keep big plants more prominent than minor ones.
          "circle-opacity": [
            "interpolate", ["linear"], ["zoom"],
            3.6, ["case", [">", ["get", "capacity_mw"], 1000], 0.7, 0.0],
            5.0, 0.85,
          ] as unknown as maplibregl.ExpressionSpecification,
          "circle-stroke-width": 0.4,
          "circle-stroke-color": "#05070a",
        },
      });

      m.addLayer({
        id: "disruption-halo",
        type: "circle",
        source: "disruptions",
        paint: {
          "circle-radius": [
            "interpolate", ["linear"], ["get", "count"],
            1, 5, 10, 11, 40, 20,
          ] as unknown as maplibregl.ExpressionSpecification,
          "circle-color": "#f0534a",
          "circle-opacity": 0.14,
          "circle-stroke-width": 1,
          "circle-stroke-color": "#f0534a",
          "circle-stroke-opacity": 0.62,
        },
      });

      setReady(true);
    });

    return () => {
      m.remove();
      map.current = null;
    };
    // Sources are seeded once; later changes are pushed by the effects below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- interaction --------------------------------------------------------
  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    let hovered: string | null = null;

    const move = (e: maplibregl.MapLayerMouseEvent) => {
      const f = e.features?.[0];
      if (!f) return;
      const code = String(f.id ?? f.properties?.code ?? "");
      if (hovered && hovered !== code) {
        m.setFeatureState({ source: "regions", id: hovered }, { hover: false });
      }
      hovered = code;
      m.setFeatureState({ source: "regions", id: code }, { hover: true });
      m.getCanvas().style.cursor = "pointer";
      const meta = regionMeta.get(code);
      const state = m.getFeatureState({ source: "regions", id: code }) as { value?: number };
      setHover({
        x: e.point.x,
        y: e.point.y,
        code,
        name: meta?.name ?? code,
        district: meta?.district ?? "",
        value: state?.value ?? 0,
        incidents: incidentsByRegion.get(code)?.length ?? 0,
        special: Boolean((f.properties as { special?: boolean } | undefined)?.special),
      });
    };

    const leave = () => {
      if (hovered) m.setFeatureState({ source: "regions", id: hovered }, { hover: false });
      hovered = null;
      m.getCanvas().style.cursor = "";
      setHover(null);
    };

    const click = (e: maplibregl.MapLayerMouseEvent) => {
      const f = e.features?.[0];
      if (!f) return;
      const code = String(f.id ?? f.properties?.code ?? "");
      onSelect(code === selected ? null : code);
    };

    // Both the analytic choropleth and the Crimea context unit are interactive.
    const layers = ["regions-fill", "special-fill"];
    for (const layer of layers) {
      m.on("mousemove", layer, move);
      m.on("mouseleave", layer, leave);
      m.on("click", layer, click);
    }
    return () => {
      for (const layer of layers) {
        m.off("mousemove", layer, move);
        m.off("mouseleave", layer, leave);
        m.off("click", layer, click);
      }
    };
  }, [ready, selected, onSelect, regionMeta, incidentsByRegion]);

  // --- choropleth values --------------------------------------------------
  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    for (const r of bundle.regions) {
      const value =
        filters.metric === "esdi"
          ? bundle.regional.regions[r.code]?.esdi[step] ?? 0
          : incidentsByRegion.get(r.code)?.length ?? 0;
      m.setFeatureState({ source: "regions", id: r.code }, { value });
    }
  }, [ready, step, filters.metric, bundle.regions, bundle.regional, incidentsByRegion]);

  // --- selection ----------------------------------------------------------
  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    for (const r of bundle.regions) {
      m.setFeatureState({ source: "regions", id: r.code }, { selected: r.code === selected });
    }
  }, [ready, selected, bundle.regions]);

  // --- overlay data & visibility -----------------------------------------
  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    (m.getSource("assets") as maplibregl.GeoJSONSource)?.setData(assetPoints);
  }, [ready, assetPoints]);

  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    (m.getSource("disruptions") as maplibregl.GeoJSONSource)?.setData(disruptionPoints);
  }, [ready, disruptionPoints]);

  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    m.setLayoutProperty("network", "visibility", filters.showLines ? "visible" : "none");
    m.setLayoutProperty("asset-dots", "visibility", filters.showAssets ? "visible" : "none");
    if (filters.showLines) {
      m.setFilter("network", ["in", ["get", "asset_class"], ["literal", [...filters.classes]]]);
    }
  }, [ready, filters.showLines, filters.showAssets, filters.classes]);

  // --- context labels, projected to screen coordinates on every move --------
  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    const countryAnchors = bundle.contextLand.features.map((f) => ({
      name: (f.properties?.name as string) ?? "",
      lon: (f.properties?.label_lon as number) ?? 0,
      lat: (f.properties?.label_lat as number) ?? 0,
    }));

    const recompute = () => {
      const b = m.getBounds();
      const z = m.getZoom();
      const W = m.getContainer().clientWidth;
      const H = m.getContainer().clientHeight;
      const inView = (lon: number, lat: number) =>
        lon >= b.getWest() && lon <= b.getEast() && lat >= b.getSouth() && lat <= b.getNorth();

      // Scale-dependent priority: at continental zoom show only the major surrounding
      // states; reveal minor and overlapping ones as you zoom in. Deterministic, not
      // arbitrary hiding.
      const minZoomFor = (name: string): number =>
        COUNTRY_MINZOOM[name] ?? 3.2;

      type Cand = { name: string; x: number; y: number; size: number; kind: "country" | "sea"; prio: number };
      const cands: Cand[] = [];
      for (const s of SEA_LABELS) {
        if (!inView(s.lon, s.lat)) continue;
        const p = m.project([s.lon, s.lat]);
        cands.push({ name: s.name, x: p.x, y: p.y, size: s.size, kind: "sea", prio: 0 });
      }
      for (const a of countryAnchors) {
        if (!a.name || !inView(a.lon, a.lat) || z < minZoomFor(a.name)) continue;
        const p = m.project([a.lon, a.lat]);
        if (p.x < 4 || p.x > W - 4 || p.y < 4 || p.y > H - 4) continue;
        cands.push({ name: a.name.toUpperCase(), x: p.x, y: p.y, size: 10, kind: "country", prio: minZoomFor(a.name) });
      }

      // Greedy de-overlap: seas first, then by ascending reveal-zoom (most important
      // first). Skip any label whose box collides with one already placed.
      cands.sort((u, v) => u.prio - v.prio);
      const placed: { x: number; y: number; w: number; h: number }[] = [];
      const out: ScreenLabel[] = [];
      for (const c of cands) {
        const w = c.name.length * c.size * 0.62 + 6;
        const h = c.size + 6;
        const box = { x: c.x - w / 2, y: c.y - h / 2, w, h };
        const clash = placed.some((q) =>
          box.x < q.x + q.w && box.x + box.w > q.x && box.y < q.y + q.h && box.y + box.h > q.y);
        if (clash) continue;
        placed.push(box);
        out.push({ name: c.name, x: c.x, y: c.y, size: c.size, kind: c.kind });
      }
      setLabels(out);
    };

    recompute();
    m.on("move", recompute);
    m.on("resize", recompute);
    return () => {
      m.off("move", recompute);
      m.off("resize", recompute);
    };
  }, [ready, bundle.contextLand]);

  const flyTo = (bounds: [number, number, number, number]) => {
    map.current?.fitBounds(bounds, { padding: 28, duration: 700 });
  };

  // Current Activity preset: the bounding box of the ADMIN REGIONS that currently carry
  // unresolved disruption, unioned from region bboxes. No incident coordinates — this
  // operates only on admin-region geography, preserving the precision ceiling.
  const currentActivityBounds = useMemo<[number, number, number, number] | null>(() => {
    let minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity;
    let any = false;
    for (const r of Object.values(bundle.snapshot.regions)) {
      if (r.unresolved_count <= 0) continue;
      const meta = regionMeta.get(r.code);
      if (!meta?.bbox) continue;
      const [x0, y0, x1, y1] = meta.bbox;
      minx = Math.min(minx, x0); miny = Math.min(miny, y0);
      maxx = Math.max(maxx, x1); maxy = Math.max(maxy, y1);
      any = true;
    }
    if (!any) return null;
    // Guard against a degenerate/oversized frame; fall back to Full AOI if it spans
    // almost the whole width (unstable framing per the brief).
    if (maxx - minx > 95) return null;
    return [minx, miny, maxx, maxy];
  }, [bundle.snapshot.regions, regionMeta]);

  const metricLabel = filters.metric === "esdi" ? "Disruption exposure" : "Recorded events";

  return (
    <div className="mapwrap">
      <div ref={container} className="map" />

      {/* Context geography labels — HTML overlays, so the map needs no glyph endpoint. */}
      {labels.map((l, i) => (
        <div
          key={`${l.name}-${i}`}
          className={`geo-label ${l.kind}`}
          style={{ left: l.x, top: l.y, fontSize: l.size }}
        >
          {l.name}
        </div>
      ))}

      <div className="camera-controls">
        <button className="ghost" onClick={() => flyTo(AOI_BOUNDS)}>Full AOI</button>
        <button className="ghost" onClick={() => flyTo(WEST_BOUNDS)}>West / Black Sea</button>
        {currentActivityBounds && (
          <button className="ghost" onClick={() => flyTo(currentActivityBounds)}
                  title="Fit the administrative regions with unresolved disruption">
            Current activity
          </button>
        )}
      </div>

      <div className="map-scope-note">
        Permanent and administrative basing only, aggregated to administrative region.
        This is a damage-assessment view of publicly reported disruption — it holds no
        current unit positions, readiness or operational status.
        <span style={{ display: "block", marginTop: 4, color: "var(--violet)" }}>
          Crimea (dashed outline) is internationally recognised as Ukraine and is shown as
          a separate context unit, excluded from the Russia+Belarus index.
        </span>
      </div>

      <div className="map-legend">
        <div className="eyebrow">{metricLabel}</div>
        <div className="legend-scale">
          {SEVERITY_STOPS.map(([stop, color]) => (
            <i key={stop} style={{ background: color }} title={`≥ ${stop}`} />
          ))}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9.5, color: "var(--text-faint)", marginTop: 3 }}>
          <span>low</span>
          <span>high</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 7, borderTop: "1px solid var(--line)", paddingTop: 6 }}>
          <span style={{ width: 16, height: 8, border: "1px dashed #a98bfa", background: "#2a2438" }} />
          <span style={{ fontSize: 9.5, color: "var(--text-faint)" }}>Crimea — context (excl. index)</span>
        </div>
      </div>

      {hover && (
        <div className="map-hover" style={{ left: hover.x, top: hover.y, borderColor: hover.special ? "#a98bfa" : undefined }}>
          <div style={{ fontSize: 12 }}>{hover.name}</div>
          <div className="eyebrow" style={{ marginTop: 2 }}>{hover.district}</div>
          {hover.special ? (
            <div style={{ fontSize: 10.5, color: "var(--violet)", marginTop: 5, lineHeight: 1.4 }}>
              Context unit — internationally Ukraine, excluded from the index.<br />
              Events to date: <span className="num">{hover.incidents}</span>
            </div>
          ) : (
            <>
              <div className="kv" style={{ marginTop: 5 }}>
                <span className="k">{metricLabel}</span>
                <span className="v">{filters.metric === "esdi" ? fmtNum(hover.value, 2) : hover.value}</span>
              </div>
              <div className="kv">
                <span className="k">Events to date</span>
                <span className="v">{hover.incidents}</span>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
