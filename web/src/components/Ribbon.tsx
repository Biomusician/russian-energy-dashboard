import type { Bundle } from "../types";
import { fmtDate, fmtDelta, fmtNum } from "../data";
import { severityColor } from "../palette";
import { ExplainButton } from "./ui";
import type { InspectTarget } from "./Inspector";

/** National summary strip. Iteration 1 adds recovery headline metrics and consolidates
 *  the two denominator-less sectors (gas, coal) into one compact cell, so the ribbon
 *  leads with what it can actually measure without hiding what it cannot. */
export default function Ribbon({
  bundle, step, currentDate, onOpenMethodology, onExplain, onCompare, comparing,
  onLifecycle, lifecycleOpen, onBriefing,
}: {
  bundle: Bundle;
  step: number;
  currentDate: string;
  onOpenMethodology: () => void;
  /** Opens the Evidence Inspector on a target. Iteration 11 §2: the headline and every scored
   *  sector must be openable, not merely documented elsewhere. */
  onExplain: (t: InspectTarget) => void;
  /** Opens the two-date comparison workspace in the dossier rail (P6). */
  onCompare?: () => void;
  comparing?: boolean;
  /** The lifecycle explorer is also reachable from the Recovery tab, but that entry lives
   *  inside the tabbed rail — which is replaced while the comparison workspace is open. Without
   *  a ribbon entry there is no way to reach it while comparing. */
  onLifecycle?: () => void;
  lifecycleOpen?: boolean;
  /** Enters Briefing Mode: presentation framing on top of map focus (P8). */
  onBriefing?: () => void;
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
        <div className="ribbon-sub">Belarus, western Russia &amp; Siberia + occupied Crimea · admin-region level</div>
        <div style={{ display: "flex", gap: 6, marginTop: 8, flexWrap: "wrap" }}>
          <button className="ghost" onClick={onOpenMethodology}>Methodology &amp; caveats</button>
          <button className="ghost" onClick={() => onExplain({ kind: "quality" })}>
            Data quality
          </button>
          {onCompare && (
            <button className="ghost" aria-pressed={!!comparing} onClick={onCompare}>
              {comparing ? "✓ comparing dates" : "Compare dates"}
            </button>
          )}
          {onBriefing && (
            <button className="ghost" onClick={onBriefing}>Briefing &amp; export</button>
          )}
          {onLifecycle && (
            <button className="ghost" aria-pressed={!!lifecycleOpen} onClick={onLifecycle}>
              {lifecycleOpen ? "✓ recovery lifecycle" : "Recovery lifecycle"}
            </button>
          )}
        </div>
      </div>

      <div className="esdi-block">
        <div className="esdi-value" style={{ color: severityColor(esdi) }}>{fmtNum(esdi, 1)}</div>
        <div className="esdi-meta">
          <div className="eyebrow">Monitored-Area ESDI</div>
          <div style={{ fontSize: 11, color: "var(--text-dim)" }}>
            {fmtDate(currentDate)} {isLatest && <span style={{ color: "var(--accent)" }}>· live</span>}
          </div>
          <div style={{ fontSize: 10.5, color: "var(--text-faint)", maxWidth: 180, lineHeight: 1.4 }}>
            Belarus + monitored Russian regions + Crimea. Capacity at disrupted sites — not measured loss.
          </div>
          <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
            <ExplainButton label="the Monitored-Area ESDI" onClick={() => onExplain({ kind: "headline" })} />
            <BuildDelta bundle={bundle} isLatest={isLatest} onExplain={onExplain} />
          </div>
        </div>
      </div>

      {/* Recovery headline. §11: the headline is the national EVIDENCE COUNT, not the pooled
          cross-class median — a 2-day terminal restart and a 205-day gas-plant repair are not
          one repair time. The mixed median is shown only as a caveated sub-line, never the
          lead number; per-class medians live in the Recovery tab. */}
      {/* These three are as-at-build snapshot counts; only the ESDI to their left follows the
          scrubber. Scrubbed to 2024 the ribbon otherwise showed a 2024 index beside 2026 recovery
          counts with nothing to tell them apart — an arithmetically impossible reading. */}
      <div className="ribbon-scroll">
      <div className="esdi-block" style={{ gap: 20 }} title="Current as at the latest build — these do not follow the timeline scrubber.">
        <RecoveryStat value={rs.unresolved_count} label="Unresolved impairments" color="var(--amber)" current />
        <RecoveryStat
          value={`${rs.observed_restoration_episodes}`}
          label="Observed-restoration episodes"
          sub={rs.median_observed_restoration_days != null
            ? `mixed-infra median ${rs.median_observed_restoration_days}d — not a per-sector norm`
            : `< ${rs.min_median_episodes} for a pooled median`}
          color="var(--green)"
          current
        />
        <RecoveryStat value={rs.full_reconstitution_episodes} label="Reconstitution episodes" color="var(--green)" current />
      </div>

      <div className="sector-strip">
        {coveredSectors.map((key) => {
          const value = national.sectors[key]?.[step] ?? 0;
          return (
            <button
              key={key}
              className="sector-cell as-button"
              onClick={() => onExplain({ kind: "sector", sector: key })}
              title={`Explain ${taxonomy.sectors[key] ?? key}`}
            >
              <div className="eyebrow">{taxonomy.sectors[key] ?? key}</div>
              <div className="num" style={{ fontSize: 19, marginTop: 4, color: severityColor(value) }}>{fmtNum(value, 1)}</div>
              <div className="sector-bar"><i style={{ width: `${Math.min(100, value)}%`, background: severityColor(value) }} /></div>
              <span className="cell-explain">explain</span>
            </button>
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
        <div className="eyebrow">Oil-strike benchmark coverage</div>
        {coverage ? (
          <>
            <div className="num" style={{ fontSize: 17 }}>
              {coverage.enumerated_in_this_dataset}
              <span style={{ color: "var(--text-faint)", fontSize: 13 }}> / {coverage.reported_total_strikes}</span>
              <span style={{ color: "var(--text-dim)", fontSize: 13 }}> ({Math.round(coverage.coverage_ratio * 100)}%)</span>
            </div>
            <div style={{ fontSize: 10, color: "var(--text-dim)", lineHeight: 1.4 }}
                 title={coverage.numerator_definition ?? undefined}>
              oil-sector strikes vs the reported oil-strike benchmark. Other sectors are
              unbenchmarked{coverage.total_events_all_sectors
                ? ` (${coverage.total_events_all_sectors} events across all sectors)` : ""}.
            </div>
          </>
        ) : (
          <div style={{ fontSize: 11, color: "var(--text-faint)" }}>benchmark unavailable</div>
        )}
        <div style={{ fontSize: 10, color: "var(--text-faint)" }}>
          {snapshot.incidents_with_quantified_capacity} of {snapshot.incident_total} have quantified capacity effect
        </div>
      </div>
      </div>
    </header>
  );
}

function RecoveryStat({
  value, label, sub, color, current,
}: {
  value: React.ReactNode; label: string; sub?: string; color: string;
  /** Marks a value that is as-at-build and does NOT follow the timeline scrubber. */
  current?: boolean;
}) {
  return (
    <div className="esdi-meta" style={{ gap: 2 }}>
      <div className="num" style={{ fontSize: 26, lineHeight: 1, color }}>{value}</div>
      <div className="eyebrow" style={{ maxWidth: 96, lineHeight: 1.3 }}>
        {label}
        {current && <span style={{ color: "var(--amber)" }}> · current</span>}
      </div>
      {sub && <div style={{ fontSize: 9.5, color: "var(--text-faint)", fontFamily: "var(--mono)" }}>{sub}</div>}
    </div>
  );
}

/** Movement since the previous build, and the way into the change ledger (§7-§10).
 *
 *  Shown only at the live end of the timeline. Scrubbed into the past the headline is a
 *  historical value, and a "since last build" delta beside it would be comparing two different
 *  things — exactly the mistake the recovery counters were caveated for.
 */
function BuildDelta({
  bundle, isLatest, onExplain,
}: { bundle: Bundle; isLatest: boolean; onExplain: (t: InspectTarget) => void }) {
  const bc = bundle.buildChanges;
  if (!isLatest || !bc) return null;

  // No previous build is not the same as a build in which nothing changed.
  if (bc.esdi_delta === null) {
    return (
      <button className="explain-btn" onClick={() => onExplain({ kind: "build" })}>
        no prior build
      </button>
    );
  }

  const substantive = bc.change_count;
  const label = bc.time_progression_only
    ? "date moved only"
    : substantive === 0
      ? "no changes"
      : `${substantive} change${substantive === 1 ? "" : "s"}`;

  return (
    <button
      className="explain-btn build-delta"
      onClick={() => onExplain({ kind: "build" })}
      title="What changed since the previous build"
    >
      <span className={bc.esdi_delta > 0 ? "up" : bc.esdi_delta < 0 ? "down" : ""}>
        {fmtDelta(bc.esdi_delta)}
      </span>
      {" "}since last build · {label}
    </button>
  );
}
