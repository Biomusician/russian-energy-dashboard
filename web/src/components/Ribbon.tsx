import type { Bundle } from "../types";
import { fmtDate, fmtNum } from "../data";
import { severityColor } from "../palette";

/** National summary strip. Iteration 1 adds recovery headline metrics and consolidates
 *  the two denominator-less sectors (gas, coal) into one compact cell, so the ribbon
 *  leads with what it can actually measure without hiding what it cannot. */
export default function Ribbon({
  bundle, step, currentDate, onOpenMethodology,
}: {
  bundle: Bundle;
  step: number;
  currentDate: string;
  onOpenMethodology: () => void;
}) {
  const { national, snapshot, taxonomy } = bundle;
  const esdi = national.esdi[step] ?? 0;
  const isLatest = step === national.dates.length - 1;
  const coverage = snapshot.coverage;
  const rs = snapshot.recovery_stats;

  const coveredSectors = snapshot.sectors_covered;
  const uncovered = snapshot.sectors_uncovered;

  return (
    <header className="ribbon">
      <div className="ribbon-brand">
        <h1 className="ribbon-title">Energy Disruption Monitor</h1>
        <div className="ribbon-sub">Western Russia, Siberia &amp; Belarus · admin-region level</div>
        <button className="ghost" style={{ marginTop: 8, alignSelf: "flex-start" }} onClick={onOpenMethodology}>
          Methodology &amp; caveats
        </button>
      </div>

      <div className="esdi-block">
        <div className="esdi-value" style={{ color: severityColor(esdi) }}>{fmtNum(esdi, 1)}</div>
        <div className="esdi-meta">
          <div className="eyebrow">Disruption Exposure Index</div>
          <div style={{ fontSize: 11, color: "var(--text-dim)" }}>
            {fmtDate(currentDate)} {isLatest && <span style={{ color: "var(--accent)" }}>· live</span>}
          </div>
          <div style={{ fontSize: 10.5, color: "var(--text-faint)", maxWidth: 180, lineHeight: 1.4 }}>
            Capacity at disrupted sites — not measured loss
          </div>
        </div>
      </div>

      {/* Recovery headline. The median is shown only once the observed sample is large
          enough (n>=min); below that it is reported honestly as a raw case count, never
          dressed up as a descriptive median. */}
      <div className="esdi-block" style={{ gap: 20 }}>
        <RecoveryStat value={rs.unresolved_count} label="Unresolved impairments" color="var(--amber)" />
        {rs.median_meaningful ? (
          <RecoveryStat
            value={`${rs.median_observed_restoration_days}d`}
            label="Median observed restoration"
            sub={`${rs.observed_restoration_episodes} episodes`}
            color="var(--green)"
          />
        ) : (
          <RecoveryStat
            value={`${rs.recovery_record_count} / ${rs.observed_restoration_episodes}`}
            label="Observed recovery: records / episodes"
            sub={`< ${rs.min_median_episodes} episodes — no median`}
            color="var(--green)"
          />
        )}
        <RecoveryStat value={rs.full_reconstitution_episodes} label="Reconstitution episodes" color="var(--green)" />
      </div>

      <div className="sector-strip">
        {coveredSectors.map((key) => {
          const value = national.sectors[key]?.[step] ?? 0;
          return (
            <div key={key} className="sector-cell">
              <div className="eyebrow">{taxonomy.sectors[key] ?? key}</div>
              <div className="num" style={{ fontSize: 19, marginTop: 4, color: severityColor(value) }}>{fmtNum(value, 1)}</div>
              <div className="sector-bar"><i style={{ width: `${Math.min(100, value)}%`, background: severityColor(value) }} /></div>
            </div>
          );
        })}
        {uncovered.length > 0 && (
          <div className="sector-cell uncovered" title="No published capacity base, so these sectors are shown but not scored.">
            <div className="eyebrow">Unquantified</div>
            <div style={{ fontSize: 12, marginTop: 6, color: "var(--text-dim)" }}>
              {uncovered.map((s) => taxonomy.sectors[s] ?? s).join(", ")}
            </div>
            <div style={{ fontSize: 9.5, color: "var(--text-faint)", marginTop: 4 }}>no capacity base</div>
          </div>
        )}
      </div>

      <div className="ribbon-coverage">
        <div className="eyebrow">Dataset coverage</div>
        {coverage ? (
          <>
            <div className="num" style={{ fontSize: 17 }}>
              {coverage.enumerated_in_this_dataset}
              <span style={{ color: "var(--text-faint)", fontSize: 13 }}> / {coverage.reported_total_strikes}</span>
            </div>
            <div style={{ fontSize: 10, color: "var(--text-dim)", lineHeight: 1.4 }}>
              enumerated vs reported strikes ({Math.round(coverage.coverage_ratio * 100)}%)
            </div>
          </>
        ) : (
          <div style={{ fontSize: 11, color: "var(--text-faint)" }}>benchmark unavailable</div>
        )}
        <div style={{ fontSize: 10, color: "var(--text-faint)" }}>
          {snapshot.incidents_with_quantified_capacity} of {snapshot.incident_total} have quantified capacity effect
        </div>
      </div>
    </header>
  );
}

function RecoveryStat({ value, label, sub, color }: { value: React.ReactNode; label: string; sub?: string; color: string }) {
  return (
    <div className="esdi-meta" style={{ gap: 2 }}>
      <div className="num" style={{ fontSize: 26, lineHeight: 1, color }}>{value}</div>
      <div className="eyebrow" style={{ maxWidth: 96, lineHeight: 1.3 }}>{label}</div>
      {sub && <div style={{ fontSize: 9.5, color: "var(--text-faint)", fontFamily: "var(--mono)" }}>{sub}</div>}
    </div>
  );
}
