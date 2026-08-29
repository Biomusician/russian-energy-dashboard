import type { Dispatch, SetStateAction } from "react";
import type { FilterState } from "../App";
import type { Bundle, FacetCounts, Incident } from "../types";
import { CAUSE_COLOR, classColor } from "../palette";
import { titleCase } from "../data";

/** Recompute facet counts from the raw bundle when snapshot.facet_counts is absent — a
 *  resilience fallback for the brief deploy window where the CDN may serve an older
 *  snapshot.json to the newer bundle. Sector/recovery/evidence facets aren't needed by the
 *  left rail, so they are left empty here. */
function fallbackFacets(bundle: Bundle): FacetCounts {
  const c = (arr: (string | null | undefined)[]): Record<string, number> => {
    const m: Record<string, number> = {};
    for (const v of arr) if (v) m[v] = (m[v] ?? 0) + 1;
    return m;
  };
  return {
    asset_class: c(bundle.assets.map((a) => a.asset_class)),
    line_class: c(bundle.linesGeo.features.map((f) => f.properties?.asset_class as string)),
    incident_asset_class: c(bundle.incidents.map((i) => i.asset_class)),
    sector: {},
    cause: c(bundle.incidents.map((i) => i.cause)),
    confidence: c(bundle.incidents.map((i) => i.confidence)),
    recovery_state: {},
    evidence_kind: {},
  };
}

/** Left rail. Every toggle carries a live tally so an empty layer reads as
 *  "nothing recorded here" rather than as a broken filter. */
export default function Filters({
  bundle, filters, setFilters,
}: {
  bundle: Bundle;
  filters: FilterState;
  setFilters: Dispatch<SetStateAction<FilterState>>;
  visibleIncidents: Incident[];
}) {
  const { taxonomy } = bundle;
  // Normally the pipeline emits facet_counts. During a deploy the CDN can briefly serve an
  // older snapshot.json (pre-facet_counts) to the new bundle; rather than white-screen, fall
  // back to counts computed from the raw corpus so the controls still render correctly.
  const fc = bundle.snapshot.facet_counts ?? fallbackFacets(bundle);

  // Corpus-wide totals (iteration 4). Toggle VISIBILITY is data-driven off these — a
  // control exists iff the whole current dataset has a record for it — never off the
  // moving timeline/filter slice, which would make controls flicker in and out. An
  // infrastructure class counts assets + network lines + incidents; a cause or confidence
  // tier counts incidents. A newly-nonzero category appears automatically after a rebuild,
  // with no frontend edit, because the filter state already holds every taxonomy key.
  const classTotal = (k: string) =>
    (fc.asset_class[k] ?? 0) + (fc.line_class[k] ?? 0) + (fc.incident_asset_class[k] ?? 0);
  const causeTotal = (k: string) => fc.cause[k] ?? 0;
  const confTotal = (k: string) => fc.confidence[k] ?? 0;

  const toggle = (field: "classes" | "causes" | "confidences", key: string) =>
    setFilters((f) => {
      const next = new Set(f[field]);
      next.has(key) ? next.delete(key) : next.add(key);
      return { ...f, [field]: next };
    });

  const setAll = (field: "classes" | "causes" | "confidences", keys: string[], on: boolean) =>
    setFilters((f) => ({ ...f, [field]: on ? new Set(keys) : new Set() }));

  const classKeys = Object.keys(taxonomy.asset_classes).filter((k) => classTotal(k) > 0);
  const causeKeys = Object.keys(taxonomy.causes).filter((k) => causeTotal(k) > 0);
  const confKeys = ["confirmed", "probable", "possible", "unverified"].filter((k) => confTotal(k) > 0);

  // Context trunk-route counts are a SEPARATE facet from analytic line_class (§15). A
  // network toggle appears only if the corpus actually holds context routes for it.
  const gasCtx = fc.context_route_class?.pipeline_gas ?? 0;
  const oilCtx = fc.context_route_class?.pipeline_oil ?? 0;

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
        <div className="eyebrow" style={{ marginBottom: 6 }}>Analytic infrastructure</div>
        <label className="check">
          <input
            type="checkbox"
            checked={filters.showAssets}
            onChange={() => setFilters((f) => ({ ...f, showAssets: !f.showAssets }))}
          />
          Infrastructure sites
          <span className="tally">{bundle.assets.length}</span>
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

      {(gasCtx > 0 || oilCtx > 0) && (
        <div className="ctl-group">
          <div className="eyebrow" style={{ marginBottom: 6 }}>Network context</div>
          {gasCtx > 0 && (
            <label className="check">
              <input
                type="checkbox"
                checked={filters.showGasNetwork}
                onChange={() => setFilters((f) => ({ ...f, showGasNetwork: !f.showGasNetwork }))}
              />
              <span className="swatch" style={{ background: classColor("pipeline_gas") }} />
              Gas pipelines
              <span className="tally">{gasCtx}</span>
            </label>
          )}
          {oilCtx > 0 && (
            <label className="check">
              <input
                type="checkbox"
                checked={filters.showOilNetwork}
                onChange={() => setFilters((f) => ({ ...f, showOilNetwork: !f.showOilNetwork }))}
              />
              <span className="swatch" style={{ background: classColor("pipeline_oil") }} />
              Oil pipelines
              <span className="tally">{oilCtx}</span>
            </label>
          )}
          <div className="note" style={{ marginTop: 4 }}>
            Continental trunk routes (OSM, cross-referenced with GEM) shown as geographic
            context — never scored, never counted as incidents.
          </div>
        </div>
      )}

      <div className="ctl-group">
        <div className="eyebrow" style={{ marginBottom: 6 }}>Geographic context</div>
        <label className="check">
          <input
            type="checkbox"
            checked={filters.showRivers}
            onChange={() => setFilters((f) => ({ ...f, showRivers: !f.showRivers }))}
          />
          Major rivers
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
        tally={classTotal}
      />

      <Group
        title="Disruption cause"
        keys={causeKeys}
        labels={taxonomy.causes}
        active={filters.causes}
        onToggle={(k) => toggle("causes", k)}
        onAll={(on) => setAll("causes", causeKeys, on)}
        color={(k) => CAUSE_COLOR[k] ?? "#4e5f6d"}
        tally={causeTotal}
      />

      <Group
        title="Confidence"
        keys={confKeys}
        labels={Object.fromEntries(confKeys.map((k) => [k, titleCase(k)]))}
        active={filters.confidences}
        onToggle={(k) => toggle("confidences", k)}
        onAll={(on) => setAll("confidences", confKeys, on)}
        color={() => "transparent"}
        tally={confTotal}
      />

      <div className="note">
        Counts are whole-corpus totals: infrastructure rows combine inventoried sites and
        network lines with facilities named in disruption reporting; cause and confidence
        rows count events. Filters with no records anywhere in the current dataset are
        hidden automatically, and reappear on their own once a sourced record arrives.
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

