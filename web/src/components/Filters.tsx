import type { Dispatch, SetStateAction } from "react";
import type { FilterState } from "../App";
import type { Bundle, Incident } from "../types";
import { CAUSE_COLOR, classColor } from "../palette";
import { titleCase } from "../data";

/** Left rail. Every toggle carries a live tally so an empty layer reads as
 *  "nothing recorded here" rather than as a broken filter. */
export default function Filters({
  bundle, filters, setFilters, visibleIncidents,
}: {
  bundle: Bundle;
  filters: FilterState;
  setFilters: Dispatch<SetStateAction<FilterState>>;
  visibleIncidents: Incident[];
}) {
  const { taxonomy, assets, incidents } = bundle;

  const assetTally = tally(assets.map((a) => a.asset_class));
  const incidentTally = tally(incidents.map((i) => i.asset_class ?? "unknown"));
  // Lines live in their own GeoJSON layer, not assets.json. Without them the
  // transmission and pipeline rows read "0", which the note below would then
  // wrongly explain as "nothing recorded".
  const lineTally = tally(
    bundle.linesGeo.features.map((f) => (f.properties?.asset_class as string) ?? null),
  );
  const causeTally = tally(visibleIncidents.map((i) => i.cause));
  const confTally = tally(visibleIncidents.map((i) => i.confidence));

  const toggle = (field: "classes" | "causes" | "confidences", key: string) =>
    setFilters((f) => {
      const next = new Set(f[field]);
      next.has(key) ? next.delete(key) : next.add(key);
      return { ...f, [field]: next };
    });

  const setAll = (field: "classes" | "causes" | "confidences", keys: string[], on: boolean) =>
    setFilters((f) => ({ ...f, [field]: on ? new Set(keys) : new Set() }));

  const classKeys = Object.keys(taxonomy.asset_classes);
  const causeKeys = Object.keys(taxonomy.causes);
  const confKeys = ["confirmed", "probable", "possible", "unverified"];

  return (
    <aside className="panel filters">
      <div className="section-head">
        <h2 style={{ fontSize: 12 }}>Layers &amp; filters</h2>
      </div>

      <div className="ctl-group">
        <div className="eyebrow" style={{ marginBottom: 6 }}>Choropleth</div>
        <select
          className="ghost"
          value={filters.metric}
          onChange={(e) => setFilters((f) => ({ ...f, metric: e.target.value as FilterState["metric"] }))}
        >
          <option value="esdi">Disruption exposure (ESDI)</option>
          <option value="incidents">Recorded events (count)</option>
        </select>
      </div>

      <div className="ctl-group">
        <div className="eyebrow" style={{ marginBottom: 6 }}>Map overlays</div>
        <label className="check">
          <input
            type="checkbox"
            checked={filters.showAssets}
            onChange={() => setFilters((f) => ({ ...f, showAssets: !f.showAssets }))}
          />
          Infrastructure sites
          <span className="tally">{assets.length}</span>
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={filters.showLines}
            onChange={() => setFilters((f) => ({ ...f, showLines: !f.showLines }))}
          />
          Grid &amp; pipeline network
        </label>
      </div>

      <Group
        title="Infrastructure type"
        keys={classKeys}
        labels={taxonomy.asset_classes}
        active={filters.classes}
        onToggle={(k) => toggle("classes", k)}
        onAll={(on) => setAll("classes", classKeys, on)}
        color={(k) => classColor(k)}
        tally={(k) =>
          (assetTally.get(k) ?? 0) + (incidentTally.get(k) ?? 0) + (lineTally.get(k) ?? 0)
        }
      />

      <Group
        title="Disruption cause"
        keys={causeKeys}
        labels={taxonomy.causes}
        active={filters.causes}
        onToggle={(k) => toggle("causes", k)}
        onAll={(on) => setAll("causes", causeKeys, on)}
        color={(k) => CAUSE_COLOR[k] ?? "#4e5f6d"}
        tally={(k) => causeTally.get(k) ?? 0}
      />

      <Group
        title="Confidence"
        keys={confKeys}
        labels={Object.fromEntries(confKeys.map((k) => [k, titleCase(k)]))}
        active={filters.confidences}
        onToggle={(k) => toggle("confidences", k)}
        onAll={(on) => setAll("confidences", confKeys, on)}
        color={() => "transparent"}
        tally={(k) => confTally.get(k) ?? 0}
      />

      <div className="note">
        Counts beside infrastructure types combine inventoried sites with facilities
        named in disruption reporting. A zero means nothing is recorded for that class
        in this dataset, not that nothing exists.
      </div>
    </aside>
  );
}

function Group({
  title, keys, labels, active, onToggle, onAll, color, tally,
}: {
  title: string;
  keys: string[];
  labels: Record<string, string>;
  active: Set<string>;
  onToggle: (k: string) => void;
  onAll: (on: boolean) => void;
  color: (k: string) => string;
  tally: (k: string) => number;
}) {
  return (
    <div className="ctl-group">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
        <div className="eyebrow">{title}</div>
        <div style={{ display: "flex", gap: 4 }}>
          <button className="ghost" style={{ padding: "1px 6px", fontSize: 10 }} onClick={() => onAll(true)}>all</button>
          <button className="ghost" style={{ padding: "1px 6px", fontSize: 10 }} onClick={() => onAll(false)}>none</button>
        </div>
      </div>
      {keys.map((k) => (
        <label key={k} className="check">
          <input type="checkbox" checked={active.has(k)} onChange={() => onToggle(k)} />
          <span className="swatch" style={{ background: color(k) }} />
          {labels[k] ?? k}
          <span className="tally">{tally(k)}</span>
        </label>
      ))}
    </div>
  );
}

function tally(values: (string | null)[]): Map<string, number> {
  const m = new Map<string, number>();
  for (const v of values) {
    if (!v) continue;
    m.set(v, (m.get(v) ?? 0) + 1);
  }
  return m;
}
