import { useEffect, useMemo, useState } from "react";
import { addDays, loadBundle, stepFor } from "./data";
import type { Asset, Bundle, Incident } from "./types";
import { decodeDeepLink, encodeDeepLink, type CameraState } from "./urlState";
import Ribbon from "./components/Ribbon";
import Filters from "./components/Filters";
import MapPanel from "./components/MapPanel";
import Dossier from "./components/Dossier";
import Timeline from "./components/Timeline";
import Methodology from "./components/Methodology";
import ComparisonTray from "./components/ComparisonTray";

/** Choropleth surfaces. The two "esdi_delta" surfaces are a DIVERGING change view (§14-15):
 *  how much a region's exposure index rose or fell over the trailing window, never a claim of
 *  physical damage. */
export type Metric = "esdi" | "incidents" | "esdi_delta_30d" | "esdi_delta_90d";

/** Recent-activity halo window (§16). "activity" = new recorded events in the trailing window;
 *  it is NOT current impairment and NOT damage. "cumulative" is every event to the scrubber. */
export type ActivityWindow = "cumulative" | "30d" | "90d";

export interface FilterState {
  classes: Set<string>;
  causes: Set<string>;
  confidences: Set<string>;
  showLines: boolean;
  showAssets: boolean;
  showRivers: boolean;
  showGasNetwork: boolean;
  showOilNetwork: boolean;
  metric: Metric;
  activityWindow: ActivityWindow;
}

const ALL_CONFIDENCES = ["confirmed", "probable", "possible", "unverified"];

export default function App() {
  // Deep-link the sender was looking at (§20-22), read once. Absent keys fall back to defaults.
  const initial = useMemo(() => decodeDeepLink(window.location.search), []);

  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [selected, setSelected] = useState<string | null>(initial.selected ?? null);
  const [selectedAsset, setSelectedAsset] = useState<{ asset: Asset; key: string } | null>(null);
  const [methodOpen, setMethodOpen] = useState(false);
  // Region comparison tray (§17): up to three pinned regions; a fourth pushes out the oldest.
  const [compareRegions, setCompareRegions] = useState<string[]>(initial.compare ?? []);
  const toggleCompare = (code: string) =>
    setCompareRegions((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code)
      : prev.length >= 3 ? [...prev.slice(1), code]
      : [...prev, code]);
  // Camera is first-class shareable state (§22): seeded from the link, then kept in sync as
  // the user pans/zooms so the URL always reproduces the current frame.
  const [camera, setCamera] = useState<CameraState | null>(initial.camera ?? null);

  const [filters, setFilters] = useState<FilterState>({
    classes: new Set(),
    causes: new Set(),
    confidences: new Set(),
    showLines: initial.showLines ?? false,
    showAssets: initial.showAssets ?? true,
    showRivers: initial.showRivers ?? false,
    showGasNetwork: initial.showGasNetwork ?? false,
    showOilNetwork: initial.showOilNetwork ?? false,
    metric: initial.metric ?? "esdi",
    activityWindow: initial.activityWindow ?? "cumulative",
  });

  useEffect(() => {
    loadBundle()
      .then((b) => {
        setBundle(b);
        // Open at the deep-linked date if any, else at the present — the question a monitoring
        // dashboard is usually asked; the scrubber is there to walk backwards.
        setStep(initial.date ? stepFor(b.national.dates, initial.date) : b.national.dates.length - 1);
        const allClasses = Object.keys(b.taxonomy.asset_classes);
        const allCauses = Object.keys(b.taxonomy.causes);
        // A link may pin a filter SUBSET; otherwise everything is on. Intersect with the real
        // key universe so a stale link can never inject a key the taxonomy no longer has.
        const pick = (linked: string[] | undefined, all: string[]) =>
          linked ? new Set(linked.filter((k) => all.includes(k))) : new Set(all);
        setFilters((f) => ({
          ...f,
          classes: pick(initial.classes, allClasses),
          causes: pick(initial.causes, allCauses),
          confidences: pick(initial.confidences, ALL_CONFIDENCES),
        }));
      })
      .catch((e) => setError(String(e.message ?? e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const currentDate = bundle ? bundle.national.dates[step] : "";

  /** Incidents up to the scrubber position that pass every active filter. */
  const visibleIncidents = useMemo<Incident[]>(() => {
    if (!bundle) return [];
    return bundle.incidents.filter(
      (i) =>
        i.date <= currentDate &&
        (!i.asset_class || filters.classes.has(i.asset_class)) &&
        filters.causes.has(i.cause) &&
        filters.confidences.has(i.confidence),
    );
  }, [bundle, currentDate, filters]);

  const incidentsByRegion = useMemo(() => {
    const m = new Map<string, Incident[]>();
    for (const i of visibleIncidents) {
      if (!i.region_code) continue;
      const list = m.get(i.region_code);
      if (list) list.push(i);
      else m.set(i.region_code, [i]);
    }
    return m;
  }, [visibleIncidents]);

  // Asset ids named anywhere in disruption reporting (identity, not a location) — lets the
  // dossier sub-card say whether the selected asset appears in events.
  const struckAssetIds = useMemo(
    () => (bundle ? new Set(bundle.incidents.map((i) => i.asset_id).filter(Boolean)) : new Set<string>()),
    [bundle],
  );

  // Recent-activity halos (§16): count only the events RECORDED inside the trailing window,
  // ending at the scrubber. This is "activity" (new reports), never current impairment. In
  // "cumulative" mode we return undefined so the map keeps its original every-event-to-date
  // halo. Windows are relative to the scrubber date, so they stay meaningful while scrubbing.
  const haloByRegion = useMemo<Map<string, number> | undefined>(() => {
    if (filters.activityWindow === "cumulative" || !currentDate) return undefined;
    const days = filters.activityWindow === "30d" ? 30 : 90;
    const windowStart = addDays(currentDate, -days);
    const m = new Map<string, number>();
    for (const i of visibleIncidents) {
      if (!i.region_code || i.date <= windowStart) continue;
      m.set(i.region_code, (m.get(i.region_code) ?? 0) + 1);
    }
    return m;
  }, [filters.activityWindow, visibleIncidents, currentDate]);

  // Selecting a region clears a stale asset sub-card unless the asset belongs to that region
  // (the asset-click path selects the asset's own region, so its sub-card is preserved).
  const selectRegion = (code: string | null) => {
    setSelected(code);
    setSelectedAsset((a) => (a && a.asset.region_code === code ? a : null));
  };

  // Mirror the shareable view into the URL (§20-22). replaceState, so scrubbing and panning
  // never floods browser history; only NON-DEFAULT state is written, so an untouched dashboard
  // keeps a clean URL. Runs after the bundle is loaded, so the key universes are known.
  useEffect(() => {
    if (!bundle) return;
    const dates = bundle.national.dates;
    const q = encodeDeepLink({
      metric: filters.metric,
      activityWindow: filters.activityWindow,
      date: dates[step] ?? null,
      latestDate: dates[dates.length - 1],
      selected,
      classes: filters.classes,
      causes: filters.causes,
      confidences: filters.confidences,
      allClasses: Object.keys(bundle.taxonomy.asset_classes),
      allCauses: Object.keys(bundle.taxonomy.causes),
      allConfidences: ALL_CONFIDENCES,
      showLines: filters.showLines,
      showAssets: filters.showAssets,
      showRivers: filters.showRivers,
      showGasNetwork: filters.showGasNetwork,
      showOilNetwork: filters.showOilNetwork,
      camera,
      compare: compareRegions,
    });
    window.history.replaceState(null, "", q ? `${window.location.pathname}?${q}` : window.location.pathname);
  }, [bundle, filters, selected, step, camera, compareRegions]);

  if (error) {
    return (
      <div className="empty" style={{ padding: 40 }}>
        <div className="eyebrow">Data unavailable</div>
        <p style={{ maxWidth: 560, lineHeight: 1.6 }}>{error}</p>
        <p style={{ color: "var(--text-faint)" }}>
          Build the dataset with <code>python -m pipeline.run</code> from the repository
          root, then reload.
        </p>
      </div>
    );
  }

  if (!bundle) {
    return (
      <div className="empty" style={{ padding: 40 }}>
        <div className="eyebrow">Loading</div>
        <p>Reading dataset…</p>
      </div>
    );
  }

  return (
    <div className="shell">
      <Ribbon
        bundle={bundle}
        step={step}
        currentDate={currentDate}
        onOpenMethodology={() => setMethodOpen(true)}
      />
      <Filters
        bundle={bundle}
        filters={filters}
        setFilters={setFilters}
        visibleIncidents={visibleIncidents}
      />
      <MapPanel
        bundle={bundle}
        step={step}
        filters={filters}
        selected={selected}
        onSelect={selectRegion}
        incidentsByRegion={incidentsByRegion}
        haloByRegion={haloByRegion}
        selectedAssetKey={selectedAsset?.key ?? null}
        onSelectAsset={(asset, key) => setSelectedAsset(asset && key ? { asset, key } : null)}
        initialCamera={initial.camera ?? null}
        onCamera={setCamera}
      />
      <Dossier
        bundle={bundle}
        step={step}
        selected={selected}
        currentDate={currentDate}
        incidentsByRegion={incidentsByRegion}
        visibleIncidents={visibleIncidents}
        onSelect={selectRegion}
        selectedAsset={selectedAsset?.asset ?? null}
        onClearAsset={() => setSelectedAsset(null)}
        assetStruck={selectedAsset ? struckAssetIds.has(selectedAsset.asset.asset_id) : undefined}
        compareRegions={compareRegions}
        onToggleCompare={toggleCompare}
      />
      <Timeline
        bundle={bundle}
        step={step}
        setStep={setStep}
        selected={selected}
        visibleIncidents={visibleIncidents}
      />
      <ComparisonTray
        bundle={bundle}
        step={step}
        codes={compareRegions}
        onRemove={(code) => setCompareRegions((p) => p.filter((c) => c !== code))}
        onClear={() => setCompareRegions([])}
        onSelect={selectRegion}
      />
      {methodOpen && <Methodology bundle={bundle} onClose={() => setMethodOpen(false)} />}
    </div>
  );
}
