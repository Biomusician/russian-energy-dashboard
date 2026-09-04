import { useEffect, useState } from "react";
import type { Asset, Bundle, Incident } from "../types";
import {
  CostsTab, EffectsTab, OverviewTab, RankingsTab, RecentTab,
  ReconstitutionTab, SourcesTab, WhatChangedTab, type TabProps,
} from "./tabs";
import { AssetAttributes } from "./AssetDetail";
import { ExplainButton } from "./ui";
import type { InspectTarget } from "./Inspector";
import Comparison, { type CompareState } from "./Comparison";
import Lifecycle from "./Lifecycle";

/** The right rail is a tabbed analytical panel. The central map stays the primary
 *  visualization; these tabs give it analytical depth without displacing it. Tab
 *  identity is data so adding one is a single entry. */
// Tab bodies are rendered as JSX components (`<Comp {...props} />`), never called as
// plain functions — each uses hooks, and calling them directly would attach those
// hooks to Dossier's own hook list and blow up on tab switch.
const TABS: {
  key: string;
  label: string;
  Comp: (p: TabProps) => React.ReactElement;
  badge?: (p: TabProps) => number | null;
}[] = [
  { key: "Overview", label: "Overview", Comp: OverviewTab },
  { key: "WhatChanged", label: "What changed", Comp: WhatChangedTab },
  { key: "Rankings", label: "Rankings", Comp: RankingsTab },
  { key: "Recent", label: "Recent", Comp: RecentTab, badge: (p) => Math.min(10, p.visibleIncidents.length) },
  { key: "Reconstitution", label: "Recovery", Comp: ReconstitutionTab, badge: (p) => p.bundle.snapshot.recovery_stats.unresolved_count },
  { key: "Effects", label: "Effects", Comp: EffectsTab },
  { key: "Costs", label: "Repair burden", Comp: CostsTab },
  { key: "Sources", label: "Sources", Comp: SourcesTab },
];

export default function Dossier({
    drawer = false, open = false, onCloseDrawer,
bundle, step, selected, currentDate, incidentsByRegion, visibleIncidents, onSelect,
  selectedAsset, onClearAsset, assetStruck, assetAlsoHere, activeClasses,
  compareRegions, onToggleCompare, onExplain, compare, onCompareChange, onCloseCompare,
  lifecycleOpen, onCloseLifecycle, lifecycleEpisode, onSelectEpisode, onOpenLifecycle,
}: {
  /** True when the dossier is presented as an overlay drawer rather than docked. */
  drawer?: boolean;
  open?: boolean;
  onCloseDrawer?: () => void;
  bundle: Bundle;
  step: number;
  selected: string | null;
  currentDate: string;
  incidentsByRegion: Map<string, Incident[]>;
  visibleIncidents: Incident[];
  onSelect: (code: string | null) => void;
  /** The infrastructure asset chosen on the map (§10). Shown as a sub-card above the
   *  region tabs; null when nothing is selected. */
  selectedAsset?: Asset | null;
  onClearAsset?: () => void;
  /** Whether the selected asset is named in disruption reporting (identity, not a location). */
  assetStruck?: boolean;
  /** Other assets on the same administrative centroid as the selected one (§9). */
  assetAlsoHere?: Asset[];
  /** Active infrastructure-class filter, so panel counts match the rest of the dashboard. */
  activeClasses?: Set<string>;
  /** Regions pinned to the comparison tray (§17), and the toggle for the current one. */
  compareRegions?: string[];
  onToggleCompare?: (code: string) => void;
  /** Opens the Evidence Inspector (iteration 11 §2). A region's index is a composite like the
   *  headline, so it must be openable in the same way rather than only the national figure. */
  onExplain?: (t: InspectTarget) => void;
  /** When set, the rail becomes the comparison workspace (P6 §12). A MODE, not a ninth tab:
   *  the tab bar has no room left that would not cost the map, and a comparison is a different
   *  activity rather than another view of the same selection. */
  compare?: CompareState | null;
  onCompareChange?: (s: CompareState) => void;
  onCloseCompare?: () => void;
  /** Recovery lifecycle explorer, also a rail MODE rather than a ninth tab (P7 §18). */
  lifecycleOpen?: boolean;
  onCloseLifecycle?: () => void;
  lifecycleEpisode?: string | null;
  onSelectEpisode?: (id: string | null) => void;
  onOpenLifecycle?: () => void;
}) {
  // Initial tab may be seeded from the URL hash (#tab=Recovery) — used for headless
  // visual QA of individual tabs; harmless in normal use.
  const initialTab = (() => {
    const m = /[#&]tab=(\w+)/.exec(window.location.hash);
    return m ? m[1] : "Overview";
  })();
  const [tab, setTab] = useState(initialTab);

  // Selecting a region on the map should surface its detail, not strand the reader on
  // a national-only tab.
  useEffect(() => {
    if (selected) setTab((t) => (t === "Rankings" ? "Overview" : t));
  }, [selected]);

  const openLifecycle = onOpenLifecycle;
  const props: TabProps = {
    bundle, step, selected, currentDate, incidentsByRegion, visibleIncidents,
    onSelect, onTab: setTab, activeClasses,
  };
  const active = TABS.find((t) => t.key === tab) ?? TABS[0];
  const region = selected ? bundle.snapshot.regions[selected] : null;

  return (
    <aside
      id="dossier-panel"
      className={`panel dossier${drawer && open ? " drawer-open" : ""}`}
      aria-hidden={drawer && !open} inert={drawer && !open ? true : undefined}>
      {drawer && (
        <div className="drawer-close">
          <button className="ghost" onClick={onCloseDrawer} aria-label="Close dossier">close ✕</button>
        </div>
      )}
      <div className="section-head">
        <div>
          <h2 style={{ fontSize: 13 }}>{region ? region.name : "Monitored-area picture"}</h2>
          <div className="eyebrow" style={{ marginTop: 3 }}>
            {region ? `${region.district} · ${region.country === "RU" ? "Russia" : region.country === "BY" ? "Belarus" : "Ukraine (occupied)"}` : "Belarus, western Russia & Siberia + occupied Crimea"}
          </div>
        </div>
        {region && (
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            {onExplain && (
              <ExplainButton
                label={`${region.name}'s index`}
                onClick={() => onExplain({ kind: "region", code: region.code })}
              />
            )}
            {onToggleCompare && (
              <button
                className="ghost"
                title="Pin this region to the comparison tray"
                onClick={() => onToggleCompare(region.code)}
              >
                {compareRegions?.includes(region.code) ? "✓ comparing" : "+ compare"}
              </button>
            )}
            <button className="ghost" onClick={() => onSelect(null)}>close</button>
          </div>
        )}
      </div>

      {selectedAsset && (
        <div className="asset-subcard">
          <div className="asset-subcard-head">
            <span className="eyebrow">Selected infrastructure</span>
            {onClearAsset && (
              <button className="ghost" style={{ padding: "1px 7px", fontSize: 10 }} onClick={onClearAsset}>
                clear
              </button>
            )}
          </div>
          <AssetAttributes
            asset={selectedAsset}
            regionName={bundle.snapshot.regions[selectedAsset.region_code]?.name}
            struck={assetStruck}
            alsoHere={assetAlsoHere}
          />
        </div>
      )}

      {lifecycleOpen && onCloseLifecycle && onSelectEpisode ? (
        <Lifecycle
          bundle={bundle}
          onClose={onCloseLifecycle}
          onExplain={onExplain ?? (() => {})}
          compare={compare ?? null}
          selectedEpisode={lifecycleEpisode ?? null}
          onSelectEpisode={onSelectEpisode}
        />
      ) : compare && onCompareChange && onCloseCompare ? (
        <Comparison
          bundle={bundle}
          state={compare}
          onChange={onCompareChange}
          onClose={onCloseCompare}
          selected={selected}
          onExplain={onExplain ?? (() => {})}
        />
      ) : (
      <>
      {openLifecycle && (
        <div className="rail-actions">
          <button className="ghost" onClick={openLifecycle}>Recovery lifecycle explorer</button>
        </div>
      )}
      <div className="tabbar" role="tablist">
        {TABS.map((t) => {
          const badge = t.badge?.(props);
          return (
            <button
              key={t.key}
              role="tab"
              aria-selected={t.key === tab}
              className="tab"
              onClick={() => setTab(t.key)}
            >
              {t.label}
              {badge != null && badge > 0 && <span className="badge">{badge}</span>}
            </button>
          );
        })}
      </div>

      <active.Comp key={active.key} {...props} />
      </>
      )}
    </aside>
  );
}
