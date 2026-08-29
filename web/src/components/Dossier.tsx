import { useEffect, useState } from "react";
import type { Bundle, Incident } from "../types";
import {
  CostsTab, EffectsTab, OverviewTab, RankingsTab, RecentTab,
  ReconstitutionTab, SourcesTab, type TabProps,
} from "./tabs";

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
  { key: "Rankings", label: "Rankings", Comp: RankingsTab },
  { key: "Recent", label: "Recent", Comp: RecentTab, badge: (p) => Math.min(10, p.visibleIncidents.length) },
  { key: "Reconstitution", label: "Recovery", Comp: ReconstitutionTab, badge: (p) => p.bundle.snapshot.recovery_stats.unresolved_count },
  { key: "Effects", label: "Effects", Comp: EffectsTab },
  { key: "Costs", label: "Repair burden", Comp: CostsTab },
  { key: "Sources", label: "Sources", Comp: SourcesTab },
];

export default function Dossier({
  bundle, step, selected, currentDate, incidentsByRegion, visibleIncidents, onSelect,
}: {
  bundle: Bundle;
  step: number;
  selected: string | null;
  currentDate: string;
  incidentsByRegion: Map<string, Incident[]>;
  visibleIncidents: Incident[];
  onSelect: (code: string | null) => void;
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

  const props: TabProps = {
    bundle, step, selected, currentDate, incidentsByRegion, visibleIncidents,
    onSelect, onTab: setTab,
  };
  const active = TABS.find((t) => t.key === tab) ?? TABS[0];
  const region = selected ? bundle.snapshot.regions[selected] : null;

  return (
    <aside className="panel dossier">
      <div className="section-head">
        <div>
          <h2 style={{ fontSize: 13 }}>{region ? region.name : "Monitored-area picture"}</h2>
          <div className="eyebrow" style={{ marginTop: 3 }}>
            {region ? `${region.district} · ${region.country === "RU" ? "Russia" : region.country === "BY" ? "Belarus" : "Ukraine (occupied)"}` : "Belarus, western Russia & Siberia + occupied Crimea"}
          </div>
        </div>
        {region && <button className="ghost" onClick={() => onSelect(null)}>close</button>}
      </div>

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
    </aside>
  );
}
