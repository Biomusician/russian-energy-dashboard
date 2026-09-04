import type { Dispatch, SetStateAction } from "react";
import type { FilterState } from "../App";
import type { Asset, Bundle, FacetCounts, Incident, NetworkCoverageClass } from "../types";
import { CAUSE_COLOR, classColor } from "../palette";
import { titleCase } from "../data";
import { iconSVG } from "../icons";
import SearchBox from "./SearchBox";

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
  bundle, filters, setFilters, onPickRegion, onPickAsset, compareCount = 0,
  drawer = false, open = false, onCloseDrawer,
}: {
  bundle: Bundle;
  filters: FilterState;
  setFilters: Dispatch<SetStateAction<FilterState>>;
  visibleIncidents: Incident[];
  onPickRegion: (code: string) => void;
  onPickAsset: (asset: Asset, index: number) => void;
  /** How many regions are pinned to the comparison tray, for the rail hint. */
  compareCount?: number;
  /** True when this rail is presented as an overlay drawer rather than docked. */
  drawer?: boolean;
  open?: boolean;
  onCloseDrawer?: () => void;
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
  const coverage = bundle.snapshot.network_coverage;
  const gasCtx = fc.context_route_class?.pipeline_gas ?? 0;
  const oilCtx = fc.context_route_class?.pipeline_oil ?? 0;

  return (
    <aside
      id="filters-panel"
      className={`panel filters${drawer && open ? " drawer-open" : ""}`}
      aria-hidden={drawer && !open} inert={drawer && !open ? true : undefined}>
      {drawer && (
        <div className="drawer-close">
          <button className="ghost" onClick={onCloseDrawer} aria-label="Close layers panel">close ✕</button>
        </div>
      )}
      <div className="section-head">
        <h2 style={{ fontSize: 12 }}>Layers &amp; filters</h2>
      </div>

      <div className="ctl-group">
        <SearchBox bundle={bundle} onPickRegion={onPickRegion} onPickAsset={onPickAsset} />
        {/* The comparison tray's only entry point was a button that appears after a region is
            selected, so the feature was invisible until you happened to find it. */}
        <div className="note" style={{ marginTop: 8 }}>
          Search a region or facility to jump to it. Select a region, then
          <b> + compare</b> in its header, to pin up to three side by side
          {compareCount > 0 && <> — <b>{compareCount} pinned</b></>}.
        </div>
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
          <option value="esdi_delta_30d">Change in ESDI · last 30 days</option>
          <option value="esdi_delta_90d">Change in ESDI · last 90 days</option>
        </select>
        {(filters.metric === "esdi_delta_30d" || filters.metric === "esdi_delta_90d") && (
          <div className="note" style={{ marginTop: 6 }}>
            Diverging scale: blue where the index fell, red where it rose. A modelled change in
            exposure, not observed physical damage — a region with <em>no new recorded events
            always falls</em>, because the index decays on a modelled half-life. Falling is not
            observed repair.
          </div>
        )}
      </div>

      <div className="ctl-group">
        <div className="eyebrow" style={{ marginBottom: 6 }}>Recent-activity halos</div>
        <select
          className="ghost"
          value={filters.activityWindow}
          onChange={(e) => setFilters((f) => ({ ...f, activityWindow: e.target.value as FilterState["activityWindow"] }))}
        >
          <option value="cumulative">All recorded events (to date)</option>
          <option value="30d">Activity · last 30 days</option>
          <option value="90d">Activity · last 90 days</option>
        </select>
        <div className="note" style={{ marginTop: 6 }}>
          Halos size to how many events were <em>recorded</em> in the window ending at the
          scrubber — recent activity, not current impairment or damage.
        </div>
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
            Continental trunk routes reconstructed from OpenStreetMap pipeline route relations,
            shown as geographic context — never scored, never counted as incidents.
          </div>
          {/* Network SOURCE COVERAGE (§21) — how completely the network is sourced, which is a
              different question from how much disruption there is. Only rendered for a layer the
              reader has actually turned on, and only when the data carries it. */}
          {coverage && (filters.showGasNetwork || filters.showOilNetwork) && (
            <div className="net-coverage">
              <div className="eyebrow" style={{ marginBottom: 4 }}>Route source coverage</div>
              {filters.showGasNetwork && <CoverageRow label="Gas" c={coverage.pipeline_gas} />}
              {filters.showOilNetwork && <CoverageRow label="Oil" c={coverage.pipeline_oil} />}
              <div className="note" style={{ marginTop: 6 }}>
                “Continuous” means the route assembled into one unbroken piece from its source
                geometry. A fragmented route is missing mapping, not necessarily missing pipe —
                and a continuous route is not therefore an accurate one.
              </div>
            </div>
          )}
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
        icon={(k) => k}
      />

      {/* Icon grammar legend (§11): these same glyphs mark the map, so shape = function and
          colour = class identity are learned once and read everywhere. The precision frame is
          the one piece the map adds that the rows cannot show, so it is spelled out here. */}
      <div className="ctl-group icon-key">
        <div className="eyebrow" style={{ marginBottom: 6 }}>Reading the map markers</div>
        <div className="note" style={{ marginTop: 0 }}>
          Shape shows the infrastructure function; colour repeats the type identity above.
          Disruption is never drawn on the marker — it stays on the region shading and halo.
        </div>
        <div className="precision-key">
          <span className="pk-swatch" aria-hidden="true"
                dangerouslySetInnerHTML={{ __html: iconSVG("refinery", { size: 20 }) }} />
          <span>Solid — a mapped public facility coordinate.</span>
        </div>
        <div className="precision-key">
          <span className="pk-swatch" aria-hidden="true"
                dangerouslySetInnerHTML={{ __html: iconSVG("refinery", { size: 20, region: true }) }} />
          <span>Dashed frame — placed on its administrative region, not a facility location.</span>
        </div>
      </div>

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
  title, keys, labels, active, onToggle, onAll, color, tally, icon,
}: {
  title: string;
  keys: string[];
  labels: Record<string, string>;
  active: Set<string>;
  onToggle: (k: string) => void;
  onAll: (on: boolean) => void;
  color: (k: string) => string;
  tally: (k: string) => number;
  /** When set, the row shows the infrastructure ICON glyph (same registry as the map) for
   *  this class instead of a plain colour swatch (§11). */
  icon?: (k: string) => string;
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
          {icon
            ? <span className="asset-glyph" aria-hidden="true"
                    dangerouslySetInnerHTML={{ __html: iconSVG(icon(k), { size: 15 }) }} />
            : <span className="swatch" style={{ background: color(k) }} />}
          {labels[k] ?? k}
          <span className="tally">{tally(k)}</span>
        </label>
      ))}
    </div>
  );
}


/** One class's route-source coverage. Reports topology completeness (did the route assemble
 *  into one piece?) and geometry provenance separately — a generalized route can be
 *  topologically complete and still geographically approximate. */
function CoverageRow({ label, c }: { label: string; c?: NetworkCoverageClass }) {
  if (!c) return null;
  const mapped = c.route_quality.osm_mapped ?? 0;
  // Report the DE-DUPLICATED extent as the headline. Summing route lengths double-counts every
  // corridor modelled both as a system and as its constituent strings — a correct hierarchy, not
  // a duplicate, but presenting the sum as "km of pipeline" overstates the network. The overlap
  // shown below is `total_length_km - distinct_network_km`; do not quote a constant here, it
  // changes with the data (an earlier comment said 17,870 while the line rendered 23,228).
  const distinct = c.distinct_network_km;
  const overlap = distinct != null ? Math.max(0, c.total_length_km - distinct) : null;
  return (
    <div className="cov-row">
      <div className="cov-head">
        <span>{label}</span>
        <span className="num">
          {c.canonical_entities ?? c.routes} pipelines · {Math.round(distinct ?? c.total_length_km).toLocaleString("en-GB")} km
        </span>
      </div>
      {overlap != null && overlap > 1 && (
        <div className="cov-kv" title={
          "Route lengths sum to " + Math.round(c.total_length_km).toLocaleString("en-GB") +
          " km, but a system and the strings inside it are both modelled, so that total counts " +
          "shared pipe more than once. The figure above counts each kilometre once."
        }>
          <span>Shared pipe, not counted twice</span>
          <span className="num">−{Math.round(overlap).toLocaleString("en-GB")} km</span>
        </div>
      )}
      <div className="cov-kv"><span>Continuous end to end</span>
        <span className="num">{c.single_component_routes}</span></div>
      <div className="cov-kv"><span>With unmapped gaps</span>
        <span className="num">{c.multi_component_routes}</span></div>
      <div className="cov-kv"><span>Traced geometry</span>
        <span className="num">{mapped}</span></div>
      <div className="cov-kv"><span>Generalized / schematic</span>
        <span className="num">{c.routes - mapped}</span></div>
    </div>
  );
}
