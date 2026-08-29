import { useEffect, useMemo, useState } from "react";
import { loadBundle } from "./data";
import type { Bundle, Incident } from "./types";
import Ribbon from "./components/Ribbon";
import Filters from "./components/Filters";
import MapPanel from "./components/MapPanel";
import Dossier from "./components/Dossier";
import Timeline from "./components/Timeline";
import Methodology from "./components/Methodology";

export interface FilterState {
  classes: Set<string>;
  causes: Set<string>;
  confidences: Set<string>;
  showLines: boolean;
  showAssets: boolean;
  showRivers: boolean;
  showGasNetwork: boolean;
  showOilNetwork: boolean;
  metric: "esdi" | "incidents";
}

export default function App() {
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [methodOpen, setMethodOpen] = useState(false);

  const [filters, setFilters] = useState<FilterState>({
    classes: new Set(),
    causes: new Set(),
    confidences: new Set(),
    showLines: false,
    showAssets: true,
    showRivers: false,
    showGasNetwork: false,
    showOilNetwork: false,
    metric: "esdi",
  });

  useEffect(() => {
    loadBundle()
      .then((b) => {
        setBundle(b);
        // Open at the present, which is the question a monitoring dashboard is
        // usually asked; the scrubber is there to walk backwards.
        setStep(b.national.dates.length - 1);
        setFilters((f) => ({
          ...f,
          classes: new Set(Object.keys(b.taxonomy.asset_classes)),
          causes: new Set(Object.keys(b.taxonomy.causes)),
          confidences: new Set(["confirmed", "probable", "possible", "unverified"]),
        }));
      })
      .catch((e) => setError(String(e.message ?? e)));
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
        onSelect={setSelected}
        incidentsByRegion={incidentsByRegion}
      />
      <Dossier
        bundle={bundle}
        step={step}
        selected={selected}
        currentDate={currentDate}
        incidentsByRegion={incidentsByRegion}
        visibleIncidents={visibleIncidents}
        onSelect={setSelected}
      />
      <Timeline
        bundle={bundle}
        step={step}
        setStep={setStep}
        selected={selected}
        visibleIncidents={visibleIncidents}
      />
      {methodOpen && <Methodology bundle={bundle} onClose={() => setMethodOpen(false)} />}
    </div>
  );
}
