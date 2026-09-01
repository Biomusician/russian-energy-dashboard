import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import type { FilterState, FlyTarget } from "../App";
import type { Asset, Bundle, Incident, PipelineRegistry } from "../types";
import { CLASS_COLOR, ESDI_DELTA_STOPS, SEVERITY_STOPS } from "../palette";
import { displayName, fmtDelta, fmtNum, loadContextLayer, loadPipelineRegistry, titleCase, windowRef } from "../data";
import { iconImageId, prewarmIcons } from "../icons";
import { AssetHoverCard } from "./AssetDetail";
import { RouteDetail } from "./RouteDetail";
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
// Tightened in iteration 8: the old frame reached to 145°E, zooming out far enough to show China
// and Korea, at which scale the trunk lines (0.5px at 28% opacity) were invisible — a named
// preset that produced an apparently empty map. This frames the Europe–western-Russia corridor
// where the trunks actually run.
const NETWORK_BOUNDS: [number, number, number, number] = [-2.0, 39.0, 90.0, 70.0];

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

/** Zoom thresholds at which rivers reveal, mirroring the distinct `reveal_zoom` values
 *  build_context.py derives from Natural Earth's scalerank. Exported so a test can assert the
 *  shipped data never grows a threshold the style would silently swallow. */
export const RIVER_REVEAL_STEPS = [0, 2.6, 3.4, 4.2, 5.0] as const;
const RIVER_OPACITY = [0.42, 0.46, 0.5, 0.55, 0.6] as const;

/** A top-level `step` on zoom whose every bucket boundary IS a real reveal threshold, so the
 *  constant compared against `reveal_zoom` inside each bucket is exact. */
export function buildRiverOpacity(): unknown[] {
  const expr: unknown[] = ["step", ["zoom"]];
  RIVER_REVEAL_STEPS.forEach((z, i) => {
    const output = ["case", [">=", z, ["get", "reveal_zoom"]], RIVER_OPACITY[i], 0];
    if (i === 0) expr.push(output);            // default, below the first boundary
    else expr.push(z, output);
  });
  return expr;
}

/** Deterministic declutter priority: lower wins a collision, and also decides which member of a
 *  shared administrative centroid represents the stack. Class salience first, then published
 *  capacity/voltage, then whether the asset appears in disruption reporting, then precision.
 *  DISPLAY ordering only — never a ranking of target value. */
function assetPrio(a: Asset, struck: Set<string>): number {
  const classBase = (CLASS_PRIO[a.asset_class] ?? 6) * 1000;
  const capBoost = Math.min(400, (a.capacity_mw ?? 0) / 12 + (a.capacity_mtpa ?? 0) * 25 + (a.capacity_bcm_y ?? 0) * 20);
  const vBoost = Math.min(300, (a.voltage_kv ?? 0) / 2);
  return Math.round(
    classBase - capBoost - vBoost - (struck.has(a.asset_id) ? 600 : 0) - (a.precision === "region" ? 250 : 0),
  );
}

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

/** Properties carried by a context pipeline route component. Public route attributes only —
 *  no coordinate readout, no distance, no vulnerability measure. */
interface RouteProps {
  pipeline_id: string;
  canonical_pipeline_id: string | null;
  canonical_name: string | null;
  drawn_length_km: number;
  name: string | null;
  asset_class: string;
  operator: string | null;
  status: string | null;
  route_quality: string;
  geometry_source: string;
  substance_basis: string;
  analytic_overlap: boolean;
  route_length_km: number;
  component_index: number;
  component_count: number;
}

/** How each route-quality value should be described to a reader. Deliberately explicit that a
 *  generalized or schematic route is NOT a surveyed line. */
const ROUTE_QUALITY_LABEL: Record<string, string> = {
  osm_mapped: "Mapped — traced route geometry (OpenStreetMap)",
  osm_generalized: "Generalized — sparsely traced, approximate between vertices",
  gem_traced: "Source-traced route geometry",
  gem_generalized: "Generalized route — approximate, not a surveyed line",
  topology_only: "Connection known; geographic route unresolved",
  unresolved: "Route geometry unresolved",
};

export default function MapPanel({
  bundle, step, filters, selected, onSelect, incidentsByRegion,
  selectedAssetKey, onSelectAsset, haloByRegion, initialCamera, onCamera, flyTarget,
  layoutSignal,
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
  /** Changes whenever the responsive mode or a dock/undock alters the container.
   *  Used only to trigger a resize — the map is never recreated. */
  layoutSignal?: string;
}) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const assetClickRef = useRef(false);
  const selectedAssetIdRef = useRef<number | null>(null);
  const [ready, setReady] = useState(false);
  const [assetLayersReady, setAssetLayersReady] = useState(false);
  const [hover, setHover] = useState<HoverInfo | null>(null);
  const [assetHover, setAssetHover] = useState<{ x: number; y: number; asset: Asset; alsoHere: Asset[] } | null>(null);
  const [routeHover, setRouteHover] = useState<{ x: number; y: number; props: RouteProps } | null>(null);
  // Clicking a route opens the canonical detail panel (§16). The registry is fetched on the
  // FIRST click rather than at load: it is entity-level metadata nobody needs until they ask.
  const [selectedRoute, setSelectedRoute] = useState<RouteProps | null>(null);
  const [registry, setRegistry] = useState<PipelineRegistry | null>(null);
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
  /** Region-precision assets placed on the SAME administrative centroid, grouped by that exact
   *  point (§9 audit). 14 of 35 curated assets share a centroid with another — four LNG terminals
   *  land on one Leningrad point — so with collision-declutter on, only one would ever draw and
   *  the map would assert a facility that is actually several. One marker per centroid is drawn,
   *  flagged "stacked", and the card names every member. The members are NOT displaced: inventing
   *  offsets would fabricate geography the dataset does not have. */
  const centroidGroups = useMemo(() => {
    const byPoint = new Map<string, number[]>();
    bundle.assets.forEach((a, i) => {
      if (a.precision !== "region") return;
      const k = `${a.lon},${a.lat}`;
      const list = byPoint.get(k);
      if (list) list.push(i);
      else byPoint.set(k, [i]);
    });
    // The representative is the most analytically salient member that PASSES THE ACTIVE CLASS
    // FILTER, not simply the first one. Groups are class-mixed in the real data — Novoshakhtinsk
    // Refinery shares a centroid with Port of Azov coal terminal, Orsk Refinery with Orenburg GPP
    // — so a fixed first-member rep both drew a refinery as a coal-terminal glyph and made those
    // two struck refineries vanish entirely under a "refineries only" filter. Picking by
    // declutter priority (which already ranks class, capacity and struck-ness) fixes both.
    const info = new Map<number, { count: number; members: number[]; rep: number | null }>();
    for (const members of byPoint.values()) {
      const eligible = members.filter((i) => filters.classes.has(bundle.assets[i].asset_class));
      const rep = eligible.length
        ? eligible.reduce((best, i) => (assetPrio(bundle.assets[i], struckAssetIds) < assetPrio(bundle.assets[best], struckAssetIds) ? i : best))
        : null;
      for (const i of members) info.set(i, { count: members.length, members, rep });
    }
    return info;
  }, [bundle.assets, filters.classes, struckAssetIds]);

  const assetPoints = useMemo<GeoJSON.FeatureCollection>(() => ({
    type: "FeatureCollection",
    features: bundle.assets.map((a, i) => {
      const region = a.precision === "region";
      const struck = struckAssetIds.has(a.asset_id);
      const group = centroidGroups.get(i);
      const stacked = (group?.count ?? 1) > 1;
      // Only the group representative is drawn/hit-tested; the rest stay in the source so their
      // feature ids (and therefore selection state) remain stable and addressable from search.
      const rep = !group || group.rep === i;
      const prio = assetPrio(a, struckAssetIds);
      return {
        type: "Feature" as const,
        id: i,
        properties: {
          key: `${a.asset_id}:${i}`,
          asset_class: a.asset_class,
          name: a.name ?? "",
          region_code: a.region_code,
          img: iconImageId(a.asset_class, region, stacked),
          region: region ? 1 : 0,
          struck: struck ? 1 : 0,
          rep: rep ? 1 : 0,
          stack: group?.count ?? 1,
          prio: Math.round(prio),
        },
        geometry: { type: "Point" as const, coordinates: [a.lon, a.lat] },
      };
    }),
  }), [bundle.assets, struckAssetIds, centroidGroups]);

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
          // Lifted from #3f6b8c, which sat inside the choropleth's own teal range and made rivers
          // hard to pick out over exactly the regions being analysed.
          "line-color": "#6fa8cc",
          "line-width": [
            "interpolate", ["linear"], ["zoom"],
            2, ["case", ["<=", ["get", "scalerank"], 2], 0.7, 0.35],
            8, ["case", ["<=", ["get", "scalerank"], 2], 2.4, 1.1],
          ] as unknown as maplibregl.ExpressionSpecification,
          // Per-feature reveal: a river stays invisible until the zoom passes its own
          // reveal_zoom. MapLibre only allows ["zoom"] as the direct input to a top-level
          // interpolate/step (nesting it inside a "case" is rejected and the whole layer is
          // silently dropped — the iteration-5 defect), so the gate lives in the outputs.
          // "step" rather than "interpolate": interpolating BETWEEN gated outputs blends across
          // the gate, so a river showed at ~30% opacity below its own reveal zoom.
          // The bucket boundaries are the DISTINCT reveal_zoom values the pipeline emits, which
          // makes the comparison inside each bucket exact rather than approximate. A test
          // (rivers.test.ts) fails if the data grows a threshold these buckets do not cover.
          "line-opacity": buildRiverOpacity() as unknown as maplibregl.ExpressionSpecification,
        },
      });

      // Continental oil/gas CONTEXT network: trunk export/transit routes, scope "context",
      // never scored. Deliberately subordinate — faint and thin at continental zoom, firmer on
      // zoom-in — so the degradation surface dominates the analytic view.
      //
      // Iteration 9: these are now canonical ROUTES reconstructed from OSM relations rather
      // than loose ways, and the layer is SELF-CONTAINED — it carries routes the analytic feed
      // also has, because its toggle is independent. Overlap is marked, not deleted; the
      // double-draw is handled here (see the analytic-overlap filter in the visibility effect)
      // rather than by withholding data from the file.
      //
      // Dash pattern encodes ROUTE QUALITY, so an approximate route can never look mapped:
      //   solid   osm_mapped / gem_traced     — a traced route
      //   dashed  gem_generalized             — a generalized or endpoint-derived route
      //   dotted  topology_only               — connection known, geographic route unresolved
      // Only osm_mapped exists in the data today; the other cases are styled but will not
      // appear until a source that carries them is ingested (the whole-corpus-zero rule).
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
            // Lifted at continental zoom so the trunks are actually visible in the network
            // preset; still subordinate to the analytic surface.
            "line-width": [
              "interpolate", ["linear"], ["zoom"], 2, 0.9, 5, 1.4, 8, 2.1,
            ] as unknown as maplibregl.ExpressionSpecification,
            "line-opacity": [
              "interpolate", ["linear"], ["zoom"], 2, 0.5, 4, 0.6, 8, 0.72,
            ] as unknown as maplibregl.ExpressionSpecification,
            "line-dasharray": [
              "match", ["get", "route_quality"],
              "osm_generalized", ["literal", [3, 2]],
              "gem_generalized", ["literal", [3, 2]],
              "topology_only", ["literal", [1, 2.5]],
              ["literal", [1]],
            ] as unknown as maplibregl.ExpressionSpecification,
          },
        });
        // Transparent wide hit target: a 1–2 px line is unhoverable at continental zoom.
        m.addLayer({
          id: `${id}-hit`,
          type: "line",
          source: src,
          layout: { visibility: "none", "line-cap": "round", "line-join": "round" },
          paint: { "line-color": "#000000", "line-opacity": 0, "line-width": 12 },
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
          // At the Full-AOI home view the old 0.26 scale rendered a 6 px smudge at 50% opacity,
          // where shape, the dashed precision frame and the stacked backplate are all
          // imperceptible — i.e. the whole symbology grammar was shown at a size that cannot
          // carry it, including the precision distinction the scope rules require.
          "icon-size": ["interpolate", ["linear"], ["zoom"], 2, 0.42, 3.4, 0.5, 6, 0.62, 9, 0.8] as unknown as maplibregl.ExpressionSpecification,
          "icon-padding": 2,
          "visibility": filters.showAssets ? "visible" : "none",
        },
        paint: {
          "icon-opacity": ["interpolate", ["linear"], ["zoom"], 2, 0.75, 5.0, 0.95] as unknown as maplibregl.ExpressionSpecification,
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
        paint: {
          // A flat 10 px target around ~1,900 assets tiled most of the AOI at low zoom and stole
          // every region hover, making the choropleth's per-region value unreadable — the
          // choropleth is the primary analytic surface. Scale the target with zoom so assets
          // only win the pointer once they are actually separable.
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 2, 3.5, 4, 6, 6, 10] as unknown as maplibregl.ExpressionSpecification,
          "circle-color": "#000000",
          "circle-opacity": 0,
        },
      }, m.getLayer("disruption-halo") ? "disruption-halo" : undefined);

      setAssetLayersReady(true);
    });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);

  // --- container resize (hotfix §12) --------------------------------------------------------
  // MapLibre sizes its canvas from the container at construction and then only on window
  // resize. Every new path in this hotfix changes the container WITHOUT a window resize —
  // docking or undocking a rail, entering map focus, crossing a responsive breakpoint — and a
  // canvas that has not caught up renders a stale, letterboxed, or blank strip.
  //
  // A ResizeObserver on the actual element is the reliable signal. Observations are coalesced
  // into one resize per animation frame: dragging a window edge fires continuously, and calling
  // resize() per event is how a smooth drag becomes a stutter.
  useEffect(() => {
    const el = container.current;
    if (!el) return;
    // Deliberately NOT gated on `ready`. The failure this guards against is a container that is
    // 0x0 when MapLibre is constructed — in that state the style never finishes and `ready`
    // never becomes true, so an observer waiting for `ready` could never rescue it. It attaches
    // as soon as the element exists and calls resize() on whatever map instance is present.
    let timer = 0;
    let lastW = 0;
    let lastH = 0;
    const observer = new ResizeObserver((entries) => {
      const box = entries[0]?.contentRect;
      if (!box) return;
      // Sub-pixel jitter from a CSS transition should not queue work.
      if (Math.abs(box.width - lastW) < 1 && Math.abs(box.height - lastH) < 1) return;
      lastW = box.width;
      lastH = box.height;
      // Debounced with a TIMER rather than rAF: rAF is suspended in a hidden tab, so a
      // rAF-scheduled resize would never run for a container that changed while the tab was in
      // the background — exactly when a resize is most likely to have been missed.
      window.clearTimeout(timer);
      timer = window.setTimeout(() => {
        // A container can legitimately be 0x0 mid-transition; resizing to that produces the
        // blank-canvas failure this project has already hit once.
        if (box.width > 0 && box.height > 0) map.current?.resize();
      }, 32);
    });
    observer.observe(el);
    return () => {
      window.clearTimeout(timer);
      observer.disconnect();
    };
  }, []);

  // Drawer transitions animate for ~160ms, so the container's final size is not known when the
  // mode flips. Resize once at the end rather than on every intermediate frame; the observer
  // above catches the intermediate states anyway, this just guarantees the last one.
  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    const t = window.setTimeout(() => m.resize(), 200);
    return () => window.clearTimeout(t);
  }, [ready, layoutSignal]);

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
      // A stacked centroid marker stands for several assets; name the others so the marker is
      // never read as the only facility there.
      const idx = Number(String(f.properties?.key ?? "").split(":").pop());
      const group = centroidGroups.get(idx);
      const alsoHere = group
        ? group.members.filter((j) => j !== idx).map((j) => bundle.assets[j]).filter(Boolean)
        : [];
      setAssetHover({ x: e.point.x, y: e.point.y, asset, alsoHere });
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
    // Leaving the canvas entirely does not fire the layer's mouseleave, so the card would hang
    // over the UI indefinitely after the pointer moved to the left rail.
    const canvas = m.getCanvasContainer();
    canvas.addEventListener("mouseleave", leave);
    return () => {
      m.off("mousemove", "asset-hit", move);
      m.off("mouseleave", "asset-hit", leave);
      m.off("click", "asset-hit", click);
      canvas.removeEventListener("mouseleave", leave);
    };
  }, [ready, assetLayersReady, assetByKey, onSelectAsset, onSelect, selectedAssetKey]);

  // --- context pipeline route hover (§19) ---------------------------------
  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    const layers = ["context-gas-net-hit", "context-oil-net-hit"];
    const move = (e: maplibregl.MapLayerMouseEvent) => {
      const f = e.features?.[0];
      if (!f) return;
      m.getCanvas().style.cursor = "pointer";
      setRouteHover({ x: e.point.x, y: e.point.y, props: f.properties as unknown as RouteProps });
    };
    const leave = () => { setRouteHover(null); m.getCanvas().style.cursor = ""; };
    const click = (e: maplibregl.MapLayerMouseEvent) => {
      const f = e.features?.[0];
      if (!f) return;
      // Stop the region choropleth underneath from also toggling, exactly as an asset click does.
      assetClickRef.current = true;
      window.setTimeout(() => { assetClickRef.current = false; }, 0);
      const props = f.properties as unknown as RouteProps;
      setSelectedRoute((prev) => (prev?.pipeline_id === props.pipeline_id ? null : props));
      void loadPipelineRegistry().then(setRegistry);
    };
    const present = layers.filter((l) => m.getLayer(l));
    for (const l of present) {
      m.on("mousemove", l, move);
      m.on("mouseleave", l, leave);
      m.on("click", l, click);
    }
    const canvas = m.getCanvasContainer();
    canvas.addEventListener("mouseleave", leave);
    return () => {
      for (const l of present) {
        m.off("mousemove", l, move);
        m.off("mouseleave", l, leave);
        m.off("click", l, click);
      }
      canvas.removeEventListener("mouseleave", leave);
    };
  }, [ready]);

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
    const picked = idOf(selectedAssetKey);
    // Selecting a member hidden behind a shared centroid must highlight the marker that is
    // actually drawn for it — the group representative — or the halo would land on nothing.
    const id = picked != null ? (centroidGroups.get(picked)?.rep ?? picked) : null;
    if (id != null) m.setFeatureState({ source: "assets", id }, { selected: true });
    selectedAssetIdRef.current = id;
  }, [ready, selectedAssetKey, centroidGroups]);

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
    // Weekly series: resolve to the nearest earlier step, never past the scrubber.
    const refStep = deltaDays ? windowRef(dates, step, deltaDays).comparisonStep : step;
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
      // Only the representative of a shared administrative centroid is drawn or hit-tested, so a
      // stack renders as one honest marker rather than N identical glyphs fighting for the pixel.
      const classFilter = [
        "all",
        ["in", ["get", "asset_class"], ["literal", [...filters.classes]]],
        ["==", ["get", "rep"], 1],
      ] as unknown as maplibregl.FilterSpecification;
      m.setFilter("asset-symbols", classFilter);
      m.setFilter("asset-hit", classFilter);
    }
    m.setLayoutProperty("rivers", "visibility", filters.showRivers ? "visible" : "none");
    // The context layer is complete on its own, so when the ANALYTIC line layer is also on the
    // shared corridors would draw twice. Suppress the overlapping context routes in that case
    // only — the data still contains them, and turning the analytic layer off restores them.
    // This is the §2 rule: the frontend decides what to draw, the pipeline does not decide what
    // to withhold.
    const overlapFilter = filters.showLines
      ? (["!=", ["get", "analytic_overlap"], true] as unknown as maplibregl.FilterSpecification)
      : null;
    for (const [id, on] of [["context-gas-net", filters.showGasNetwork],
                            ["context-oil-net", filters.showOilNetwork]] as const) {
      for (const layer of [id, `${id}-hit`]) {
        if (!m.getLayer(layer)) continue;
        m.setLayoutProperty(layer, "visibility", on ? "visible" : "none");
        m.setFilter(layer, overlapFilter);
      }
    }
    if (filters.showLines) {
      m.setFilter("network", ["in", ["get", "asset_class"], ["literal", [...filters.classes]]]);
    }
  }, [ready, assetLayersReady, filters.showLines, filters.showAssets, filters.showRivers,
      filters.showGasNetwork, filters.showOilNetwork, filters.classes, assetLayersReady]);

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

  // Route-quality values actually present in the built network, for the legend.
  const routeQualities = useMemo(() => {
    const cov = bundle.snapshot.network_coverage;
    if (!cov) return [];
    const seen = new Set<string>();
    for (const [cls, v] of Object.entries(cov)) {
      const on = cls === "pipeline_gas" ? filters.showGasNetwork : filters.showOilNetwork;
      if (on) for (const q of Object.keys(v.route_quality ?? {})) seen.add(q);
    }
    return [...seen].sort();
  }, [bundle.snapshot.network_coverage, filters.showGasNetwork, filters.showOilNetwork]);

  const isDelta = filters.metric === "esdi_delta_30d" || filters.metric === "esdi_delta_90d";
  const deltaSpanDays = isDelta
    ? windowRef(bundle.national.dates, step, filters.metric === "esdi_delta_30d" ? 30 : 90).actualComparisonDays
    : 0;
  // ESDI (and its deltas) are precomputed per region over every class; only the event-count
  // surface responds to the type filter.
  const indexIgnoresClassFilter =
    filters.metric !== "incidents"
    && filters.classes.size < Object.keys(bundle.taxonomy.asset_classes).length;
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
        {/* This note must disclaim what THIS product actually is. It previously carried
            order-of-battle vocabulary ("basing", "unit positions", "readiness") inherited from a
            sibling project, which disclaimed things that do not exist here and omitted the two
            caveats that matter: centroid placement and a modelled index. */}
        Publicly reported disruption to energy infrastructure, aggregated to administrative
        region. Facility markers show published permanent locations; a dashed marker is placed
        on an administrative centroid and is not a facility location. Exposure is a modelled
        index of capacity at disrupted sites — not measured loss, and never an assessment of
        undamaged infrastructure.
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
        {/* Numeric ticks: without them a reader cannot tell a 0.26 move from a 2.8 move, and the
            saturating ends are invisible. */}
        {isDelta && (
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, color: "var(--text-faint)", marginTop: 2, fontFamily: "var(--mono)" }}>
            <span>≤−3</span><span>0</span><span>≥+3</span>
          </div>
        )}
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9.5, color: "var(--text-faint)", marginTop: 3 }}>
          {/* "improved / worsened" invites a judgement about the world; the index only fell or
              rose, and it falls on its own through decay. */}
          <span>{isDelta ? "index fell" : "low"}</span>
          <span>{isDelta ? "index rose" : "high"}</span>
        </div>
        {isDelta && (
          <div style={{ fontSize: 9, color: "var(--text-faint)", marginTop: 3, lineHeight: 1.35 }}>
            Modelled index change over the window — not observed physical damage.
            {/* The series is weekly, so say the span actually compared rather than implying
                an exact 30/90-day observation. */}
            <br />Actual span compared: {deltaSpanDays} days.
            {/* A region with no new events always falls, because the index decays on a modelled
                half-life. Without this the most available reading of a blue map is "things got
                better", which the data does not support. */}
            <br />A region with no new recorded events always falls: the index decays on a
            modelled half-life. Falling is not observed repair.
          </div>
        )}
        {/* The exposure index is precomputed per region across ALL classes; it cannot follow the
            type filter without redefining the measure. Say so rather than let a filtered view be
            read as "refinery exposure". The event-count surface DOES follow the filter. */}
        {indexIgnoresClassFilter && (
          <div style={{ fontSize: 9, color: "var(--amber)", marginTop: 4, lineHeight: 1.35 }}>
            Infrastructure-type filter is active, but this index covers <b>all</b> classes —
            the shading does not narrow to your selection. Switch to “Recorded events” for a
            filtered surface.
          </div>
        )}
        {/* Route-quality key (§20). Rendered ONLY for qualities the built data actually
            contains, and only while a network layer is on — inventing a "generalized" swatch to
            fill out the legend would advertise a distinction the corpus does not make. */}
        {(filters.showGasNetwork || filters.showOilNetwork) && routeQualities.length > 0 && (
          <div style={{ marginTop: 7, borderTop: "1px solid var(--line)", paddingTop: 6 }}>
            <div className="eyebrow" style={{ marginBottom: 4 }}>Pipeline route geometry</div>
            {routeQualities.map((q) => (
              <div key={q} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3 }}>
                <svg width="20" height="6" style={{ flex: "0 0 auto" }} aria-hidden="true">
                  <line x1="0" y1="3" x2="20" y2="3" stroke="var(--text-dim)" strokeWidth="1.6"
                        strokeDasharray={q === "gem_generalized" || q === "osm_generalized" ? "4 2" : q === "topology_only" ? "1 2" : undefined} />
                </svg>
                <span style={{ fontSize: 9.5, color: "var(--text-faint)", lineHeight: 1.3 }}>
                  {ROUTE_QUALITY_LABEL[q] ?? q}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* The halo is the loudest mark on the map and was the only channel with no key. */}
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 7, borderTop: "1px solid var(--line)", paddingTop: 6 }}>
          <span style={{ width: 14, height: 14, borderRadius: "50%", border: "1px solid #f0534a", background: "rgba(240,83,74,0.14)", flex: "0 0 auto" }} />
          <span style={{ fontSize: 9.5, color: "var(--text-faint)", lineHeight: 1.3 }}>
            Recorded events, sized by count, on the region centroid — activity, not current damage
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 5 }}>
          <span style={{ width: 16, height: 8, border: "1px dashed #a98bfa", background: "#2a2438", flex: "0 0 auto" }} />
          <span style={{ fontSize: 9.5, color: "var(--text-faint)" }}>Crimea — Ukraine, occupied (in index)</span>
        </div>
      </div>

      {hover && !assetHover && !routeHover && (
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
              {/* A region with nothing ever recorded also reads ±0.00 on the delta surface. That
                  is "no basis to change", not "measured as unchanged" — unknown is not zero. */}
              {isDelta && hover.incidents === 0 && (
                <div style={{ fontSize: 10, color: "var(--amber)", marginTop: 5, lineHeight: 1.4 }}>
                  No recorded events here — nothing to change, not a measured zero.
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Card precedence: the most specific thing under the cursor wins. All three layers fire
          their own mousemove, so without this a region, a route and an asset card stack on top
          of one another at the same point. */}
      {routeHover && !assetHover && !selectedRoute && <RouteHoverCard {...routeHover} />}
      {selectedRoute && (
        <RouteDetail
          entity={registry?.entities[selectedRoute.canonical_pipeline_id ?? ""] ?? null}
          routeLengthKm={selectedRoute.route_length_km}
          drawnLengthKm={selectedRoute.drawn_length_km}
          componentCount={selectedRoute.component_count}
          onClose={() => setSelectedRoute(null)}
        />
      )}

      {assetHover && (
        <AssetHoverCard
          asset={assetHover.asset}
          x={assetHover.x}
          y={assetHover.y}
          regionName={regionMeta.get(assetHover.asset.region_code)?.name}
          alsoHere={assetHover.alsoHere}
        />
      )}
    </div>
  );
}

/** Context pipeline route detail (§19). Public route attributes only: name, commodity, status,
 *  operator, and — importantly — how good the drawn geometry actually is. Never a coordinate,
 *  a distance, a range, or any measure of consequence. */
function RouteHoverCard({ x, y, props }: { x: number; y: number; props: RouteProps }) {
  const color = CLASS_COLOR[props.asset_class] ?? "#5b6b78";
  const commodity = props.asset_class === "pipeline_oil" ? "Crude oil / liquids" : "Natural gas";
  const fragmented = Number(props.component_count) > 1;
  return (
    <div className="map-hover" style={{ left: x, top: y, borderColor: color, maxWidth: 258 }}>
      <div style={{ fontSize: 12, lineHeight: 1.25 }}>{displayName(props.name) || "Unnamed route"}</div>
      <div className="eyebrow" style={{ marginTop: 3 }}>{commodity} · context route</div>
      <div className="kv"><span className="k">Route length</span>
        <span className="v">{fmtNum(props.route_length_km, 0)} km</span></div>
      {props.operator && (
        <div className="kv"><span className="k">Operator</span><span className="v">{props.operator}</span></div>
      )}
      {props.status && (
        <div className="kv"><span className="k">Status</span><span className="v">{titleCase(props.status)}</span></div>
      )}
      <div className="kv"><span className="k">Geometry</span>
        <span className="v" style={{ fontSize: 10 }}>
          {props.geometry_source === "osm_relation" ? "OSM route relation" : "OSM named ways"}
        </span></div>
      <div style={{ fontSize: 10, color: "var(--text-dim)", marginTop: 5, lineHeight: 1.4 }}>
        {ROUTE_QUALITY_LABEL[props.route_quality] ?? props.route_quality}
      </div>
      {fragmented && (
        // Say plainly that the drawn piece is part of a route with unmapped gaps, rather than
        // letting a reader assume the corridor simply ends here.
        <div style={{ fontSize: 10, color: "var(--amber)", marginTop: 4, lineHeight: 1.4 }}>
          Drawn in {props.component_count} pieces — the gaps are unmapped in the source, not
          breaks in the pipeline.
        </div>
      )}
      <div style={{ fontSize: 9.5, color: "var(--text-faint)", marginTop: 5, lineHeight: 1.35 }}>
        Geographic context only — never scored, and not an operational status.
      </div>
    </div>
  );
}
