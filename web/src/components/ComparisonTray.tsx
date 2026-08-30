import { useState } from "react";
import type { Bundle } from "../types";
import { fmtDelta, fmtNum, titleCase, windowRef } from "../data";
import { severityColor } from "../palette";
import { Sparkline } from "./ui";

/** Region comparison tray (§17). Pins 2-3 regions side by side so an analyst can read the same
 *  measures across them at once — exposure, 90-day change, events, unresolved impairments, top
 *  affected sector, and the ESDI trajectory — without flipping the single-region dossier back
 *  and forth. Pure aggregated public metrics; nothing operational. */
export default function ComparisonTray({
  bundle, step, codes, onRemove, onClear, onSelect,
}: {
  bundle: Bundle;
  step: number;
  codes: string[];
  onRemove: (code: string) => void;
  onClear: () => void;
  onSelect: (code: string) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  if (codes.length < 2) return null;
  const dates = bundle.national.dates;
  // Same weekly-series resolution as every other change view, so the columns are comparable.
  const ref = windowRef(dates, step, 90);
  const refStep = ref.comparisonStep;

  const cols = codes.map((code) => {
    const snap = bundle.snapshot.regions[code];
    const series = bundle.regional.regions[code]?.esdi;
    const esdiNow = series?.[step] ?? 0;
    const change = series ? esdiNow - (series[refStep] ?? 0) : 0;
    const topSector = snap
      ? Object.entries(snap.sectors).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1])[0]
      : undefined;
    const occupied = snap ? snap.analytic_scope !== "aoi" : false;
    return { code, snap, series, esdiNow, change, topSector, occupied };
  });

  return (
    <div className="compare-tray">
      <div className="compare-head">
        <span className="eyebrow">Region comparison</span>
        <div style={{ display: "flex", gap: 4 }}>
          <button className="ghost" style={{ padding: "1px 7px", fontSize: 10 }}
                  title={collapsed ? "Show the comparison columns" : "Collapse — keeps the pinned regions"}
                  onClick={() => setCollapsed((c) => !c)}>
            {collapsed ? `show (${codes.length})` : "collapse"}
          </button>
          <button className="ghost" style={{ padding: "1px 7px", fontSize: 10 }} onClick={onClear}>clear all</button>
        </div>
      </div>
      {collapsed ? null : (
      <div className="compare-cols">
        {cols.map(({ code, snap, series, esdiNow, change, topSector, occupied }) => {
          const color = occupied ? "var(--violet)" : severityColor(esdiNow);
          const changeColor = change > 0.05 ? "#e08a5a" : change < -0.05 ? "#4a9fd4" : "var(--text-dim)";
          return (
            <div key={code} className="compare-col">
              <div className="compare-col-head">
                <button className="linklike" style={{ fontSize: 12, padding: 0 }} onClick={() => onSelect(code)}>
                  {snap?.name ?? code}
                </button>
                <button className="compare-x" title="Remove" onClick={() => onRemove(code)}>×</button>
              </div>
              <div className="num" style={{ fontSize: 22, color, lineHeight: 1.1 }}>{fmtNum(esdiNow, 1)}</div>
              <div className="eyebrow" style={{ marginBottom: 4 }}>ESDI{occupied ? " · occupied" : ""}</div>
              <Sparkline values={(series ?? []).slice(0, step + 1)} markIndex={step} width={150} height={30} color={color} ariaLabel={`${snap?.name ?? code} ESDI trajectory`} />
              <div className="compare-kv" title={`Weekly series: compared with ${ref.comparisonDate}, ${ref.actualComparisonDays} days back.`}>
                <span>90-day change</span><span className="num" style={{ color: changeColor }}>{fmtDelta(change)}</span>
              </div>
              <div className="compare-kv"><span>Events to date</span><span className="num">{snap?.incident_count ?? 0}</span></div>
              <div className="compare-kv"><span>Unresolved</span><span className="num">{snap?.unresolved_count ?? 0}</span></div>
              <div className="compare-kv">
                <span>Top sector</span>
                <span className="num" style={{ fontSize: 11 }}>{topSector ? `${titleCase(topSector[0])} ${fmtNum(topSector[1], 1)}` : "—"}</span>
              </div>
            </div>
          );
        })}
      </div>
      )}
    </div>
  );
}
