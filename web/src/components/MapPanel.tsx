import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import type { FilterState, FlyTarget } from "../App";
import type { Asset, Bundle, Incident } from "../types";
import { CLASS_COLOR, ESDI_DELTA_STOPS, SEVERITY_STOPS } from "../palette";
import { addDays, fmtDelta, fmtNum, loadContextLayer, stepFor } from "../data";
import { iconImageId, prewarmIcons } from "../icons";
import { AssetHoverCard } from "./AssetDetail";
import type { CameraState } from "../urlState";

/** The map deliberately has no basemap.
 *
 *  Every tile provider worth using needs an API key, a billing relationship, or an
 *  attribution banner, and none of them would add anything: this is a choropleth of
 *  administrative regions, and streets and terrain underneath it are noise. Rendering
 *  our own GeoJSON on a flat dark ground means the deployed page makes zero external
 *  network requests, works offline, and cannot break when someone else's tile server
 *  changes its terms.
 *
 *  TEXT symbol layers are still avoided — MapLibre text needs a glyph endpoint, which would
 *  reintroduce that external dependency, so region/sea/country names stay HTML overlays.
 *  ICON-ONLY symbol layers, however, need no glyph service: the infrastructure icons
 *  (iteration 8) are rasterised locally from inline SVG and registered with addImage(), so
 *  the zero-third-party-request invariant is fully preserved (see src/icons.ts). */

const EMPTY_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: "bg", type: "background", paint: { "background-color": "#05070a" } }],
};

// Two camera presets (iteration 2). Full AOI frames Belarus through the Siberian FD;
// West/Black Sea zooms the western theatre where most disruption and Crimea sit.
const AOI_BOUNDS: [number, number, number, number] = [17.5, 40.0, 120.0, 74.0];
const WEST_BOUNDS: [number, number, number, number] = [20.0, 41.0, 62.0, 62.0];
// Russia–Europe Network (iteration 5): frames the continental oil/gas trunk context, from
// Atlantic Europe to the Russian Far East. The default view stays the analytic Full AOI —
// this is an on-demand context frame, not the dashboard's home (§12).
const NETWORK_BOUNDS: [number, number, number, number] = [-8.0, 36.0, 145.0, 73.0];

// Context-country label anchors worth showing, plus the sea labels. Kept short so the
// map does not turn into a name soup; positioned as HTML overlays (no glyph endpoint).
const SEA_LABELS: { name: string; lon: number; lat: number; size: number }[] = [
  { name: "BLACK SEA", lon: 34.0, lat: 43.3, size: 12 },
  { name: "CASPIAN SEA", lon: 50.5, lat: 41.5, size: 11 },
  { name: "BALTIC SEA", lon: 19.5, lat: 57.6, size: 10 },
  { name: "BARENTS SEA", lon: 40.0, lat: 71.5, size: 10 },
];

// Country label reveal-zoom is data-driven (iteration 5): each context feature carries a
// `label_min_zoom` derived from Natural Earth's LABELRANK (see pipeline/build_context.py),
// so label priority lives in the data, not a hand-maintained list here. Major states show
// at continental scale; smaller ones appear on zoom-in; the greedy de-overlap below then
// drops any that would collide.
const DEFAULT_COUNTRY_MINZOOM = 3.4;

// Declutter priority by class (§7): the analytically dense classes (refineries, gas/LNG,
// generation) win collisions over the substation swarm. This is DISPLAY decluttering only —
// capacity/voltage refine it, and it is never a target-value ranking.
const CLASS_PRIO: Record<string, number> = {
  refinery: 0, gas_processing: 1, lng_terminal: 1, oil_terminal: 2,
  power_plant_nuclear: 2, power_plant_hydro: 3, power_plant_thermal: 3,
  coal_terminal: 4, coal_mine: 4, interconnector: 4, power_plant_other: 5,
  substation: 7,
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

interface ScreenLabel { name: string; x: number; y: number; size: number; kind: "country" | "sea" | "river" }

export default function MapPanel({
  bundle, step, filters, selected, onSelect, incidentsByRegion,
  selectedAssetKey, onSelectAsset, haloByRegion, initialCamera, onCamera, flyTarget,
}: {
  bundle: Bundle;
  step: number;
  filters: FilterState;
  selected: string | null;
  onSelect: (code: string | null) => void;
  incidentsByRegion: Map<string, Incident[]>;
  selectedAssetKey?: string | null;
  onSelectAsset?: (asset: Asset | null, key: string | null) => void;
  haloByRegion?: Map<string, number>;
  /** Camera to open at (§22), from a shared link. Absent = the default Full-AOI frame. */
  initialCamera?: CameraState | null;
  /** Reports the settled camera after each pan/zoom so App can mirror it into the URL. */
  onCamera?: (cam: CameraState) => void;
  /** One-shot request to frame a search hit (§21); re-triggered by its nonce. */
  flyTarget?: FlyTarget | null;
}) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const assetClickRef = useRef(false);
  const selectedAssetIdRef = useRef<number | null>(null);
  const [ready, setReady] = useState(false);
  const [assetLayersReady, setAssetLayersReady] = useState(false);
  const [hover, setHover] = useState<HoverInfo | null>(null);
  const [assetHover, setAssetHover] = useState<{ x: number; y: number; asset: Asset } | null>(null);
  const [labels, setLabels] = useState<ScreenLabel[]>([]);
  // Lazy-loaded context layers (§16): which files we've fetched, and the rivers FC (needed
  // for the HTML label overlay, which the map source alone can't drive).
  const loadedRef = useRef<Set<string>>(new Set());
  const [ctxRivers, setCtxRivers] = useState<GeoJSON.FeatureCollection | null>(null);

  const regionMeta = useMemo(
    () => new Map(bundle.regions.map((r) => [r.code, r])),
    [bundle.regions],
  );

  // Asset ids that appear in disruption reporting — feeds the declutter priority and the
  // asset card's "recorded incidents" line. Canonical-identity, not coordinates.
  const struckAssetIds = useMemo(
    () => new Set(bundle.incidents.map((i) => i.asset_id).filter(Boolean)),
    [bundle.incidents],
  );
  const assetByKey = useMemo(
    () => new Map(bundle.assets.map((a, i) => [`${a.asset_id}:${i}`, a])),
    [bundle.assets],
  );

  /** Points for the infrastructure overlay — ALL assets (class visibility is applied by the
   *  layer filter, not by rebuilding this source, so hover keys stay stable and toggling a
   *  class is cheap). Each feature carries its precision-aware icon image, and a deterministic
   *  declutter priority (§7: lower = placed first, wins collisions) from class → capacity/
   *  voltage → struck → region-precision. Priority is DISPLAY decluttering only, never target
   *  value. */
  const assetPoints = useMemo<GeoJSON.FeatureCollection>(() => ({
    type: "FeatureCollection",
    features: bundle.assets.map((a, i) => {
      const region = a.precision === "region";
      const struck = struckAssetIds.has(a.asset_id);
      const classBase = (CLASS_PRIO[a.asset_class] ?? 6) * 1000;
      const capBoost = Math.min(400, (a.capacity_mw ?? 0) / 12 + (a.capacity_mtpa ?? 0) * 25 + (a.capacity_bcm_y ?? 0) * 20);
      const vBoost = Math.min(300, (a.voltage_kv ?? 0) / 2);
      const prio = classBase - capBoost - vBoost - (struck ? 600 : 0) - (region ? 250 : 0);
      return {
        type: "Feature" as const,
        id: i,
        properties: {
          key: `${a.asset_id}:${i}`,
          asset_class: a.asset_class,
          name: a.name ?? "",
          region_code: a.region_code,
          img: iconImageId(a.asset_class, region),
          region: region ? 1 : 0,
          struck: struck ? 1 : 0,
          prio: Math.round(prio),
        },
        geometry: { type: "Point" as const, coordinates: [a.lon, a.lat] },
      };
    }),
  }), [bundle.assets, struckAssetIds]);

  /** One marker per region that has recorded events, sized by how many.
   *  Placed on the region centroid: these are region-scoped records, and putting a
   *  dot on a facility's real coordinates would imply a precision the dataset does
   *  not have and the scope boundary does not want. */
  const disruptionPoints = useMemo<GeoJSON.FeatureCollection>(() => {
    // Halo size is the ACTIVITY count for the chosen window (§16), supplied by the app; when
    // absent it falls back to the cumulative filtered event count (the original behaviour).
    const counts = haloByRegion
      ?? new Map([...incidentsByRegion].map(([code, list]) => [code, list.length]));
    const feats: GeoJSON.Feature[] = [];
    for (const [code, count] of counts) {
      const meta = regionMeta.get(code);
      if (!meta || count <= 0) continue;
      feats.push({
        type: "Feature",
        properties: { code, count, name: meta.name },
        geometry: { type: "Point", coordinates: meta.centroid },
      });
    }
    return { type: "FeatureCollection", features: feats };
  }, [incidentsByRegion, regionMeta, haloByRegion]);

  // --- init ---------------------------------------------------------------
  useEffect(() => {
    if (!container.current || map.current) return;
    // A shared link opens at its saved frame (§22); otherwise fit the Full-AOI bounds.
    const cam = initialCamera;
    const m = new maplibregl.Map({
      container: container.current,
      style: EMPTY_STYLE,
      ...(cam
        ? { center: [cam.lng, cam.lat] as [number, number], zoom: cam.zoom }
        : { bounds: AOI_BOUNDS, fitBoundsOptions: { padding: 28 } }),
      attributionControl: false,
      maxZoom: 9,
      dragRotate: false,
    });
    map.current = m;
    if (import.meta.env.DEV) (window as unknown as { __map?: maplibregl.Map }).__map = m;
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
    m.addControl(
      new maplibregl.AttributionControl({
        customAttribution:
          "Boundaries &amp; rivers: Natural Earth (public domain) · Grid, pipelines &amp; network " +
          "context: OpenStreetMap (ODbL), cross-referenced with Global Energy Monitor GGIT/GOIT · " +
          "Generation: WRI Global Power Plant Database (CC BY 4.0) · Events: Wikipedia (CC BY-SA 4.0)",
      }),
      "bottom-right",
    );

    m.on("load", () => {
      // The infrastructure SYMBOL layers are intentionally NOT added here. A symbol layer that
      // references not-yet-registered icon images keeps isStyleLoaded() false, which stalls the
      // whole map. They are added later (see the icon effect) once the images are registered.
      // --- context geography (drawn first, underneath everything analytic) ---
      m.addSource("ocean", { type: "geojson", data: bundle.ocean });
      m.addSource("context-land", { type: "geojson", data: bundle.contextLand });
      m.addSource("context-borders", { type: "geojson", data: bundle.contextBorders });
      // Optional context layers start empty; they are lazy-loaded on first toggle (§16).
      const EMPTY_FC: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
      m.addSource("rivers", { type: "geojson", data: EMPTY_FC });
      m.addSource("context-gas-net", { type: "geojson", data: EMPTY_FC });
      m.addSource("context-oil-net", { type: "geojson", data: EMPTY_FC });

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

      // Analytic (monitored-area) regions carry the severity choropleth.
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

      // Rivers: geographic context only, never scored. Each feature reveals at its own
      // scalerank-derived zoom, so the largest systems show at continental scale and smaller
      // ones appear on zoom-in. Deliberately subordinate: thin, low-opacity, desaturated
      // blue that reads as water without competing with the choropleth. Off by default.
      m.addLayer({
        id: "rivers",
        type: "line",
        source: "rivers",
        layout: { visibility: "none" },
        paint: {
          "line-color": "#3f6b8c",
          "line-width": [
            "interpolate", ["linear"], ["zoom"],
            2, ["case", ["<=", ["get", "scalerank"], 2], 0.7, 0.35],
            8, ["case", ["<=", ["get", "scalerank"], 2], 2.4, 1.1],
          ] as unknown as maplibregl.ExpressionSpecification,
          // Per-feature reveal: a river stays invisible until the zoom passes its own
          // reveal_zoom, then fades in. MapLibre only allows ["zoom"] as the direct input to
          // a top-level interpolate/step (nesting it inside a "case" is rejected and the whole
          // layer is dropped), so the per-feature gate lives in the interpolate STOP OUTPUTS.
          "line-opacity": [
            "interpolate", ["linear"], ["zoom"],
            2.5, ["case", [">=", 2.5, ["get", "reveal_zoom"]], 0.3, 0],
            7, ["case", [">=", 7, ["get", "reveal_zoom"]], 0.55, 0],
            9, ["case", [">=", 9, ["get", "reveal_zoom"]], 0.55, 0],
          ] as unknown as maplibregl.ExpressionSpecification,
        },
      });

      // Continental oil/gas CONTEXT network (§3-§8): trunk export/transit routes, scope
      // "context", never scored. Deliberately subordinate — faint and thin at continental
      // zoom, firmer on zoom-in — so the degradation surface dominates the analytic view
      // and the trunks read at the Russia–Europe Network preset (§29). All OSM geometry is
      // traced ("osm_mapped") and drawn solid; a route_quality="approximate" companion
      // treatment (dashed) is reserved for a future GEM snapshot (§5). Off by default.
      for (const [id, src, color] of [
        ["context-gas-net", "context-gas-net", CLASS_COLOR.pipeline_gas],
        ["context-oil-net", "context-oil-net", CLASS_COLOR.pipeline_oil],
      ] as const) {
        m.addLayer({
          id,
          type: "line",
          source: src,
          layout: { visibility: "none", "line-cap": "round", "line-join": "round" },
          paint: {
            "line-color": color,
            "line-width": [
              "interpolate", ["linear"], ["zoom"], 2, 0.5, 5, 1.0, 8, 1.9,
            ] as unknown as maplibregl.ExpressionSpecification,
            "line-opacity": [
              "interpolate", ["linear"], ["zoom"], 2, 0.28, 4, 0.42, 8, 0.62,
            ] as unknown as maplibregl.ExpressionSpecification,
          },
        });
      }

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

  // Mirror the settled camera to the parent for the URL (§22). Armed on a short delay so the
  // one-off initial fit does NOT write a camera into an otherwise-default link; every real pan,
  // zoom, or camera-preset flyTo after that is reported on moveend.
  useEffect(() => {
    const m = map.current;
    if (!m || !ready || !onCamera) return;
    let armed = false;
    const arm = window.setTimeout(() => { armed = true; }, 500);
    const report = () => {
      if (!armed) return;
      const c = m.getCenter();
      onCamera({ lng: c.lng, lat: c.lat, zoom: m.getZoom() });
    };
    m.on("moveend", report);
    return () => { window.clearTimeout(arm); m.off("moveend", report); };
  }, [ready, onCamera]);

  // Frame a search hit (§21): fit a region's bbox, or centre an asset's public point. Keyed on
  // the target nonce so re-picking the same place flies again. Capped zoom keeps region-precision
  // framing honest — a centroid asset never zooms in as if it were a precise facility fix.
  useEffect(() => {
    const m = map.current;
    if (!m || !ready || !flyTarget) return;
    if (flyTarget.bounds) m.fitBounds(flyTarget.bounds, { padding: 50, duration: 800, maxZoom: 7.5 });
    else if (flyTarget.center) m.flyTo({ center: flyTarget.center, zoom: flyTarget.zoom ?? 7, duration: 800 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, flyTarget?.nonce]);

  // --- infrastructure icons + symbol layers (added AFTER the style loads and the images are
  //     registered, so a symbol layer never references a missing image and stalls the map) ---
  useEffect(() => {
    const m = map.current;
    if (!m || !ready || m.getLayer("asset-symbols")) return;
    let cancelled = false;
    prewarmIcons().then((imgs) => {
      if (cancelled || !map.current) return;
      for (const { id, data } of imgs) {
        try { if (!m.hasImage(id)) m.addImage(id, data, { pixelRatio: 3 }); } catch { /* raced */ }
      }
      // SHAPE = infrastructure type. `symbol-sort-key` = the per-feature priority so the dense
      // substation swarm yields collisions to refineries/plants/terminals; icon-allow-overlap
      // false lets MapLibre drop colliding low-priority icons (no allow-overlap-everywhere clutter).
      m.addLayer({
        id: "asset-symbols",
        type: "symbol",
        source: "assets",
        // minzoom matches the Full-AOI home view (~z2.1): at the wide view the collision
        // declutter (icon-allow-overlap:false + symbol-sort-key) shows only the highest-
        // priority icons; more reveal on zoom-in. A higher floor would leave the home view
        // with no infrastructure at all, which is the opposite of §2's intent.
        minzoom: 2,
        layout: {
          "icon-image": ["get", "img"] as unknown as maplibregl.ExpressionSpecification,
          "icon-allow-overlap": false,
          "symbol-sort-key": ["get", "prio"] as unknown as maplibregl.ExpressionSpecification,
          "icon-size": ["interpolate", ["linear"], ["zoom"], 2, 0.26, 3.4, 0.34, 6, 0.5, 9, 0.72] as unknown as maplibregl.ExpressionSpecification,
          "icon-padding": 2,
          "visibility": filters.showAssets ? "visible" : "none",
        },
        paint: {
          "icon-opacity": ["interpolate", ["linear"], ["zoom"], 2, 0.5, 5.0, 0.95] as unknown as maplibregl.ExpressionSpecification,
          "icon-halo-color": ["case", ["boolean", ["feature-state", "selected"], false], "#2ad4ee", "#05070a"] as unknown as maplibregl.ExpressionSpecification,
          "icon-halo-width": ["case", ["boolean", ["feature-state", "selected"], false], 2.2, 0.7] as unknown as maplibregl.ExpressionSpecification,
          "icon-halo-blur": 0.4,
        },
      }, m.getLayer("disruption-halo") ? "disruption-halo" : undefined);

      // Transparent generous hit target under the icons for reliable hover/click. No dots return.
      m.addLayer({
        id: "asset-hit",
        type: "circle",
        source: "assets",
        minzoom: 2,
        layout: { "visibility": filters.showAssets ? "visible" : "none" },
        paint: { "circle-radius": 10, "circle-color": "#000000", "circle-opacity": 0 },
      }, m.getLayer("disruption-halo") ? "disruption-halo" : undefined);

      setAssetLayersReady(true);
    });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);

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
      // An asset click (topmost layer, fires first) sets this flag so the region click
      // beneath it does not also toggle and cancel the selection.
      if (assetClickRef.current) return;
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

  // --- asset (infrastructure icon) interaction ----------------------------
  useEffect(() => {
    const m = map.current;
    if (!m || !ready || !assetLayersReady) return;
    const move = (e: maplibregl.MapLayerMouseEvent) => {
      const f = e.features?.[0];
      const asset = f && assetByKey.get(String(f.properties?.key ?? ""));
      if (!asset) return;
      m.getCanvas().style.cursor = "pointer";
      setAssetHover({ x: e.point.x, y: e.point.y, asset });
    };
    const leave = () => { setAssetHover(null); m.getCanvas().style.cursor = ""; };
    const click = (e: maplibregl.MapLayerMouseEvent) => {
      const f = e.features?.[0];
      const key = f ? String(f.properties?.key ?? "") : "";
      const asset = assetByKey.get(key);
      if (!asset) return;
      assetClickRef.current = true;
      window.setTimeout(() => { assetClickRef.current = false; }, 0);
      const deselect = key === selectedAssetKey;
      onSelectAsset?.(deselect ? null : asset, deselect ? null : key);
      // Open the containing region dossier alongside the asset card (§10).
      if (!deselect && asset.region_code) onSelect(asset.region_code);
    };
    m.on("mousemove", "asset-hit", move);
    m.on("mouseleave", "asset-hit", leave);
    m.on("click", "asset-hit", click);
    return () => {
      m.off("mousemove", "asset-hit", move);
      m.off("mouseleave", "asset-hit", leave);
      m.off("click", "asset-hit", click);
    };
  }, [ready, assetLayersReady, assetByKey, onSelectAsset, onSelect, selectedAssetKey]);

  // Selected-asset feature-state drives the icon halo. The key encodes the feature id (index).
  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    const idOf = (key: string | null | undefined) => {
      if (!key) return null;
      const n = Number(key.slice(key.lastIndexOf(":") + 1));
      return Number.isFinite(n) ? n : null;
    };
    // Clear all, then set the selected one (the asset set is small enough that a targeted
    // clear-and-set is cheaper than iterating; we track the previous id in a ref).
    const prev = selectedAssetIdRef.current;
    if (prev != null) m.setFeatureState({ source: "assets", id: prev }, { selected: false });
    const id = idOf(selectedAssetKey);
    if (id != null) m.setFeatureState({ source: "assets", id }, { selected: true });
    selectedAssetIdRef.current = id;
  }, [ready, selectedAssetKey]);

  // --- choropleth values --------------------------------------------------
  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    // For a "change in ESDI" surface, the reference step is the timeline position `window`
    // days before the scrubber; the value is the signed difference of the region's own ESDI
    // series between then and now. This is a modelled index delta, never physical damage.
    const dates = bundle.national.dates;
    const deltaDays =
      filters.metric === "esdi_delta_30d" ? 30 : filters.metric === "esdi_delta_90d" ? 90 : 0;
    const refStep = deltaDays ? stepFor(dates, addDays(dates[step], -deltaDays)) : step;
    for (const r of bundle.regions) {
      const series = bundle.regional.regions[r.code]?.esdi;
      let value: number;
      if (deltaDays) value = series ? (series[step] ?? 0) - (series[refStep] ?? 0) : 0;
      else if (filters.metric === "esdi") value = series?.[step] ?? 0;
      else value = incidentsByRegion.get(r.code)?.length ?? 0;
      m.setFeatureState({ source: "regions", id: r.code }, { value });
    }
  }, [ready, step, filters.metric, bundle.regions, bundle.regional, bundle.national.dates, incidentsByRegion]);

  // Swap the choropleth ramp when the surface flips between sequential exposure/events and the
  // DIVERGING change view, so "improved" (blue) can never read as "low exposure" (§14-15).
  useEffect(() => {
    const m = map.current;
    if (!m || !ready || !m.getLayer("regions-fill")) return;
    const isDelta = filters.metric === "esdi_delta_30d" || filters.metric === "esdi_delta_90d";
    const stops = isDelta ? ESDI_DELTA_STOPS : SEVERITY_STOPS;
    m.setPaintProperty("regions-fill", "fill-color", [
      "interpolate", ["linear"], ["coalesce", ["feature-state", "value"], 0],
      ...stops.flatMap(([stop, color]) => [stop, color]),
    ] as unknown as maplibregl.ExpressionSpecification);
  }, [ready, filters.metric]);

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
    if (m.getLayer("asset-symbols")) {
      const assetVis = filters.showAssets ? "visible" : "none";
      m.setLayoutProperty("asset-symbols", "visibility", assetVis);
      m.setLayoutProperty("asset-hit", "visibility", assetVis);
      // Class visibility is applied as a layer filter (the source holds every asset).
      const classFilter = ["in", ["get", "asset_class"], ["literal", [...filters.classes]]] as unknown as maplibregl.FilterSpecification;
      m.setFilter("asset-symbols", classFilter);
      m.setFilter("asset-hit", classFilter);
    }
    m.setLayoutProperty("rivers", "visibility", filters.showRivers ? "visible" : "none");
    m.setLayoutProperty("context-gas-net", "visibility", filters.showGasNetwork ? "visible" : "none");
    m.setLayoutProperty("context-oil-net", "visibility", filters.showOilNetwork ? "visible" : "none");
    if (filters.showLines) {
      m.setFilter("network", ["in", ["get", "asset_class"], ["literal", [...filters.classes]]]);
    }
  }, [ready, assetLayersReady, filters.showLines, filters.showAssets, filters.showRivers,
      filters.showGasNetwork, filters.showOilNetwork, filters.classes]);

  // Lazy-load optional context layers on first toggle, then cache. Missing/late files
  // degrade to empty; the core dashboard never waits on them (§16, §35).
  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    const wanted: [boolean, string, string][] = [
      [filters.showRivers, "rivers.geojson", "rivers"],
      [filters.showGasNetwork, "context_gas_network.geojson", "context-gas-net"],
      [filters.showOilNetwork, "context_oil_network.geojson", "context-oil-net"],
    ];
    for (const [on, file, src] of wanted) {
      if (!on || loadedRef.current.has(file)) continue;
      loadedRef.current.add(file);
      loadContextLayer(file).then((fc) => {
        (m.getSource(src) as maplibregl.GeoJSONSource | undefined)?.setData(fc);
        if (file === "rivers.geojson") setCtxRivers(fc);
      });
    }
  }, [ready, filters.showRivers, filters.showGasNetwork, filters.showOilNetwork]);

  // --- context labels, projected to screen coordinates on every move --------
  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    // Country label anchors carry a data-driven reveal zoom (label_min_zoom) from the
    // pipeline; the frontend no longer hardcodes per-country priority.
    const countryAnchors = bundle.contextLand.features.map((f) => ({
      name: (f.properties?.name as string) ?? "",
      lon: (f.properties?.label_lon as number) ?? 0,
      lat: (f.properties?.label_lat as number) ?? 0,
      minZoom: (f.properties?.label_min_zoom as number) ?? DEFAULT_COUNTRY_MINZOOM,
    }));
    // River label anchors: only the major named systems carry one (see build_context.py).
    // Rivers are lazy-loaded, so this reads the loaded FC (empty until the toggle is on).
    const riverAnchors = (ctxRivers?.features ?? [])
      .filter((f) => f.properties?.label_name)
      .map((f) => ({
        name: (f.properties?.label_name as string) ?? "",
        lon: (f.properties?.label_lon as number) ?? 0,
        lat: (f.properties?.label_lat as number) ?? 0,
        minZoom: (f.properties?.label_zoom as number) ?? 4.5,
      }));

    const recompute = () => {
      const b = m.getBounds();
      const z = m.getZoom();
      const W = m.getContainer().clientWidth;
      const H = m.getContainer().clientHeight;
      const inView = (lon: number, lat: number) =>
        lon >= b.getWest() && lon <= b.getEast() && lat >= b.getSouth() && lat <= b.getNorth();
      const onScreen = (x: number, y: number) => x >= 4 && x <= W - 4 && y >= 4 && y <= H - 4;

      type Cand = { name: string; x: number; y: number; size: number; kind: "country" | "sea" | "river"; prio: number };
      const cands: Cand[] = [];
      // Seas first (prio 0), then countries by their reveal zoom, then rivers last so a
      // river label never displaces a country label in a collision.
      for (const s of SEA_LABELS) {
        if (!inView(s.lon, s.lat)) continue;
        const p = m.project([s.lon, s.lat]);
        cands.push({ name: s.name, x: p.x, y: p.y, size: s.size, kind: "sea", prio: 0 });
      }
      for (const a of countryAnchors) {
        if (!a.name || !inView(a.lon, a.lat) || z < a.minZoom) continue;
        const p = m.project([a.lon, a.lat]);
        if (!onScreen(p.x, p.y)) continue;
        cands.push({ name: a.name.toUpperCase(), x: p.x, y: p.y, size: 10, kind: "country", prio: a.minZoom });
      }
      if (filters.showRivers) {
        for (const r of riverAnchors) {
          if (!r.name || !inView(r.lon, r.lat) || z < r.minZoom) continue;
          const p = m.project([r.lon, r.lat]);
          if (!onScreen(p.x, p.y)) continue;
          cands.push({ name: r.name, x: p.x, y: p.y, size: 9, kind: "river", prio: 100 + r.minZoom });
        }
      }

      // Greedy de-overlap: seas first, then by ascending reveal-zoom (most important
      // first), rivers last. Skip any label whose box collides with one already placed.
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
  }, [ready, bundle.contextLand, ctxRivers, filters.showRivers]);

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

  const isDelta = filters.metric === "esdi_delta_30d" || filters.metric === "esdi_delta_90d";
  const metricLabel =
    filters.metric === "esdi" ? "Disruption exposure"
    : filters.metric === "incidents" ? "Recorded events"
    : filters.metric === "esdi_delta_30d" ? "Change in ESDI · 30 days"
    : "Change in ESDI · 90 days";

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
        <button className="ghost" onClick={() => flyTo(NETWORK_BOUNDS)}
                title="Frame the Russia–Europe oil &amp; gas trunk network context">
          Russia–Europe Network
        </button>
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
          Crimea (dashed outline) is internationally recognised as Ukraine, under Russian
          occupation. It is shown as a separate unit and is included in the Monitored-Area
          index — inclusion is an analytic choice, not a statement about sovereignty.
        </span>
      </div>

      <div className="map-legend">
        <div className="eyebrow">{isDelta ? "Change in ESDI" : metricLabel}</div>
        <div className="legend-scale">
          {(isDelta ? ESDI_DELTA_STOPS : SEVERITY_STOPS).map(([stop, color]) => (
            <i key={stop} style={{ background: color }} title={isDelta ? `${stop > 0 ? "+" : ""}${stop}` : `≥ ${stop}`} />
          ))}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9.5, color: "var(--text-faint)", marginTop: 3 }}>
          <span>{isDelta ? "improved" : "low"}</span>
          <span>{isDelta ? "worsened" : "high"}</span>
        </div>
        {isDelta && (
          <div style={{ fontSize: 9, color: "var(--text-faint)", marginTop: 3, lineHeight: 1.35 }}>
            Modelled index change over the window — not observed physical damage.
          </div>
        )}
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 7, borderTop: "1px solid var(--line)", paddingTop: 6 }}>
          <span style={{ width: 16, height: 8, border: "1px dashed #a98bfa", background: "#2a2438" }} />
          <span style={{ fontSize: 9.5, color: "var(--text-faint)" }}>Crimea — Ukraine, occupied (in index)</span>
        </div>
      </div>

      {hover && (
        <div className="map-hover" style={{ left: hover.x, top: hover.y, borderColor: hover.special ? "#a98bfa" : undefined }}>
          <div style={{ fontSize: 12 }}>{hover.name}</div>
          <div className="eyebrow" style={{ marginTop: 2 }}>{hover.district}</div>
          {hover.special ? (
            <div style={{ fontSize: 10.5, color: "var(--violet)", marginTop: 5, lineHeight: 1.4 }}>
              Internationally Ukraine, under Russian occupation. Included in the index; shown separately.<br />
              Events to date: <span className="num">{hover.incidents}</span>
            </div>
          ) : (
            <>
              <div className="kv" style={{ marginTop: 5 }}>
                <span className="k">{metricLabel}</span>
                <span className="v">
                  {isDelta ? fmtDelta(hover.value) : filters.metric === "esdi" ? fmtNum(hover.value, 2) : hover.value}
                </span>
              </div>
              <div className="kv">
                <span className="k">Events to date</span>
                <span className="v">{hover.incidents}</span>
              </div>
            </>
          )}
        </div>
      )}

      {assetHover && (
        <AssetHoverCard
          asset={assetHover.asset}
          x={assetHover.x}
          y={assetHover.y}
          regionName={regionMeta.get(assetHover.asset.region_code)?.name}
        />
      )}
    </div>
  );
}
