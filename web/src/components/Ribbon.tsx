import type { Bundle } from "../types";
import { fmtDate, fmtNum, titleCase } from "../data";
import { severityColor } from "../palette";

/** National summary strip: the composite index, its sub-indexes, and — given equal
 *  billing rather than buried in a footnote — how much of the reported event
 *  universe this dataset actually enumerates. */
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

  return (
    <header className="ribbon">
      <div className="ribbon-brand">
        <h1 className="ribbon-title">Energy Disruption Monitor</h1>
        <div className="ribbon-sub">Western Russia &amp; Belarus · admin-region level</div>
        <button
          className="ghost"
          style={{ marginTop: 8, alignSelf: "flex-start" }}
          onClick={onOpenMethodology}
        >
          Methodology &amp; caveats
        </button>
      </div>

      <div className="esdi-block">
        <div className="esdi-value" style={{ color: severityColor(esdi) }}>
          {fmtNum(esdi, 1)}
        </div>
        <div className="esdi-meta">
          <div className="eyebrow">Disruption Exposure Index</div>
          <div style={{ fontSize: 11, color: "var(--text-dim)" }}>
            {fmtDate(currentDate)} {isLatest && <span style={{ color: "var(--accent)" }}>· live</span>}
          </div>
          <div style={{ fontSize: 10.5, color: "var(--text-faint)", maxWidth: 190, lineHeight: 1.4 }}>
            Share of tracked capacity at disrupted sites — not measured capacity loss
          </div>
        </div>
      </div>

      <div className="sector-strip">
        {Object.entries(taxonomy.sectors).map(([key, label]) => {
          const value = national.sectors[key]?.[step] ?? 0;
          const covered = snapshot.sectors_covered.includes(key);
          return (
            <div key={key} className={`sector-cell${covered ? "" : " uncovered"}`}>
              <div className="eyebrow">{label}</div>
              <div className="num" style={{ fontSize: 19, marginTop: 4, color: covered ? severityColor(value) : "var(--text-faint)" }}>
                {covered ? fmtNum(value, 1) : "n/a"}
              </div>
              <div className="sector-bar">
                <i style={{ width: `${Math.min(100, value)}%`, background: severityColor(value) }} />
              </div>
              {!covered && (
                <div style={{ fontSize: 9.5, color: "var(--text-faint)", marginTop: 4 }}>
                  no capacity base
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="ribbon-coverage">
        <div className="eyebrow">Dataset coverage</div>
        {coverage ? (
          <>
            <div className="num" style={{ fontSize: 17 }}>
              {coverage.enumerated_in_this_dataset}
              <span style={{ color: "var(--text-faint)", fontSize: 13 }}>
                {" "}/ {coverage.reported_total_strikes}
              </span>
            </div>
            <div style={{ fontSize: 10, color: "var(--text-dim)", lineHeight: 1.4 }}>
              events enumerated against reported strike total
              {" "}({Math.round(coverage.coverage_ratio * 100)}%)
            </div>
          </>
        ) : (
          <div style={{ fontSize: 11, color: "var(--text-faint)" }}>benchmark unavailable</div>
        )}
        <div style={{ fontSize: 10, color: "var(--text-faint)" }}>
          {snapshot.incidents_with_quantified_capacity} of {snapshot.incident_total}{" "}
          have quantified capacity effect
        </div>
      </div>
    </header>
  );
}

export { titleCase };
