import { useState } from "react";
import type { Bundle } from "../types";
import { fmtDate, fmtDelta, fmtNum } from "../data";
import { buildDeltaTitle, fmtIndex } from "../indexText";
import { assessFreshness } from "../freshness";
import { HEADLINE_SHARE, HEADLINE_WEIGHTING, TRANSMISSION_CAVEAT, reconstructionLabel } from "../briefing";
import { severityColor } from "../palette";
import { noReportMeaning } from "../statusDelay";
import type { InspectTarget } from "./Inspector";
import TheatreBar, { type TheatreTool } from "./TheatreBar";
import type { TheatreMode } from "../theatreMode";
import "../styles/theatre.css";

/** Plain-language reading of a sector's measurement basis, keyed on the basis the build itself
 *  publishes for that sector (`explanations.sectors[key].basis`). Not a sector definition: it
 *  says what KIND of number the cell is, so "transmission burden" stops being opaque jargon. */
const BASIS_GLOSS: Record<string, { short: string; long: string }> = {
  capacity_mtpa: {
    short: "capacity share",
    long: "Share of the tracked capacity base sitting at recently disrupted sites. Modelled exposure, not measured loss.",
  },
  capacity_mw: {
    short: "capacity share",
    long: "Share of the tracked capacity base sitting at recently disrupted sites. Modelled exposure, not measured loss.",
  },
  event_burden: {
    short: "event-burden proxy",
    long: `A count of disrupted substations and lines against a fixed saturation point. ${TRANSMISSION_CAVEAT}`,
  },
};

/** The highest index value up to `step`, with its date. Null when the series has no value. */
function peakTo(series: (number | null)[], dates: string[], step: number): { value: number; date: string } | null {
  let best: { value: number; date: string } | null = null;
  for (let i = 0; i <= step && i < series.length; i++) {
    const v = series[i];
    if (v == null) continue;
    if (!best || v > best.value) best = { value: v, date: dates[i] };
  }
  return best;
}

/** National summary strip.
 *
 *  Reading order is the order a first-time analyst needs: where am I and how do I leave (the bar),
 *  the headline and what it means, then how much of the picture is known — the two coverage
 *  ratios, kept beside the headline at the same weight and never scrolled out of view — then the
 *  per-sector scores and the recovery evidence. Labels are plain language and WRAP; nothing in
 *  this header scrolls sideways or truncates. */
export default function Ribbon({
  bundle, step, currentDate, onOpenMethodology, onExplain, onCompare, comparing,
  onLifecycle, lifecycleOpen, theatreName, mode, onMode,
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
  theatreName: string;
  mode: TheatreMode;
  onMode: (m: TheatreMode) => void;
}) {
  const { national, snapshot, taxonomy } = bundle;
  // null, never 0, when the series has no value at this step: 0 would claim "measured, nothing
  // wrong" for a date the index was never computed on (iteration 14 found the `?? 0`).
  const esdi = national.esdi[step] ?? null;
  const isLatest = step === national.dates.length - 1;
  const payloadReconstructed = (bundle.snapshot.history_concept?.mode ?? "current_build") !== "current_build";
  const coverage = snapshot.coverage;
  const rs = snapshot.recovery_stats;
  const peak = peakTo(national.esdi, national.dates, step);

  const coveredSectors = snapshot.sectors_covered;
  const uncovered = snapshot.sectors_uncovered;
  const fresh = assessFreshness(snapshot.as_of, snapshot.publication_freshness, new Date());
  // Phones only: the sector and recovery row folds behind one labelled toggle (CSS hides the
  // toggle and always shows the row on wider screens).
  const [detailOpen, setDetailOpen] = useState(false);
  const explainHeadline = () => onExplain(isLatest ? { kind: "headline" } : { kind: "historical", step });

  const tools: TheatreTool[] = [];
  if (onCompare) tools.push({ label: "Compare dates", pressedLabel: "✓ comparing dates", onClick: onCompare, pressed: !!comparing });
  if (onLifecycle) tools.push({ label: "Recovery lifecycle", pressedLabel: "✓ recovery lifecycle", onClick: onLifecycle, pressed: !!lifecycleOpen });
  tools.push({ label: "Data quality", onClick: () => onExplain({ kind: "quality" }) });
  tools.push({ label: "Methodology & caveats", onClick: onOpenMethodology });

  return (
    <header className={`ribbon theatre-ribbon${detailOpen ? " show-sectors" : ""}`}>
      <TheatreBar name={theatreName} mode={mode} onMode={onMode} tools={tools} />

      <div className="ribbon-metrics">
        <section className="hl-block" aria-label="Headline">
          <div className="esdi-value" style={{ color: esdi == null ? "var(--text-faint)" : severityColor(esdi) }}
               title={esdi == null ? "No index value exists for this date." : undefined}>
            {fmtNum(esdi, 1)}
          </div>
          <div className="esdi-meta">
            <p className="hl-name">
              <span className="eyebrow">Monitored-Area ESDI</span>
              {/* The way into the Evidence Inspector sits ON the headline, in words a reader
                  would use. The accessible name keeps "Explain the Monitored-Area ESDI" so the
                  older label still finds it. */}
              <button type="button" className="why-btn"
                      aria-label="Why this number? Explain the Monitored-Area ESDI"
                      onClick={explainHeadline}>
                Why this number?
              </button>
            </p>
            <p className="hl-scale" title="Belarus, the monitored Russian regions and occupied Crimea.">
              {/* METHODOLOGY §1 in one line: a share, weighted, and exposure rather than loss. */}
              0–100 exposure index: {HEADLINE_SHARE}<span className="hl-scale-weight">, {HEADLINE_WEIGHTING}</span> — not measured loss.
            </p>
            {/* P2: "live" used to mean nothing more than "the scrubber is at the last timeline
                step", which is equally true of a payload that stopped rebuilding eleven days ago.
                The word is now earned: it appears only when the build's own age is inside the
                cadence the payload publishes. */}
            <p className="hl-date">
              <span>
                {fmtDate(currentDate)}
                {isLatest && !payloadReconstructed && (
                  <span style={{ color: fresh.level === "fresh" ? "var(--accent)" : "var(--amber)" }}>
                    {" "}· {fresh.shortLabel}
                  </span>
                )}
              </span>
              {peak && <span>peak to date <span className="num">{fmtNum(peak.value, 1)}</span> ({fmtDate(peak.date)})</span>}
              <BuildDelta bundle={bundle} isLatest={isLatest} onExplain={onExplain} />
            </p>
            {/* Iteration 16: a past date on this ribbon is today's evidence evaluated at that date,
                never what the dashboard published then. A shared `d=` link lands here, so the label
                travels with the number rather than living only in exports. */}
            {(!isLatest || payloadReconstructed) && (
              <p className="reconstruction-tag" title="Today's code and evidence evaluated at this date. What the dashboard actually published on a date is under Compare dates → As published.">
                {payloadReconstructed && isLatest
                  ? bundle.snapshot.history_concept!.label
                  : reconstructionLabel(currentDate)}
              </p>
            )}
          </div>
        </section>

        {/* The two coverage ratios: how much of the picture the headline can see. Same type size
            as each other and pinned beside the headline at every width. */}
        <section className="known-block" aria-label="How much is known">
          <div className="known-item">
            <span className="eyebrow" title="Oil-strike benchmark coverage">Oil-strike coverage</span>
            {coverage ? (
              <>
                <span className="known-num num">
                  {coverage.enumerated_in_this_dataset}
                  <span className="dimmer"> / {coverage.reported_total_strikes}</span>
                  <span className="dim"> ({Math.round(coverage.coverage_ratio * 100)}%)</span>
                </span>
                <span className="known-label" title={coverage.numerator_definition ?? undefined}>
                  oil-sector strikes recorded, of the reported total; other sectors have no
                  benchmark{coverage.total_events_all_sectors
                    ? ` (${coverage.total_events_all_sectors} events in all)` : ""}.
                </span>
              </>
            ) : (
              <span className="known-label">benchmark unavailable</span>
            )}
          </div>
          <div className="known-item">
            <span className="eyebrow">Capacity quantified</span>
            <span className="known-num num">
              {snapshot.incidents_with_quantified_capacity}
              <span className="dimmer"> of {snapshot.incident_total}</span>
            </span>
            <span className="known-label"
                  title="The index measures exposure, not loss, because so few events state a capacity effect.">
              events state how much capacity they removed.
            </span>
          </div>
        </section>

        <button type="button" className="ribbon-more-toggle" aria-expanded={detailOpen}
                aria-controls="ribbon-detail" onClick={() => setDetailOpen((v) => !v)}
                onKeyDown={(e) => { if (e.key === "Escape" && detailOpen) { e.preventDefault(); e.stopPropagation(); setDetailOpen(false); } }}>
          {detailOpen ? "Hide sectors & recovery" : "Sector scores & recovery"}
        </button>

        {/* Sector scores, then recovery evidence. These WRAP onto a second line when the header is
            narrow; they used to scroll sideways, and at 1600px the sector cells measured 0px wide. */}
        <div className="ribbon-scroll" id="ribbon-detail">
          <div className="sector-strip" role="group" aria-label="Sector scores in the index">
            {coveredSectors.map((key) => {
              const value = national.sectors[key]?.[step] ?? null;
              const color = value == null ? "var(--text-faint)" : severityColor(value);
              const basis = snapshot.explanations?.sectors?.[key]?.basis ?? null;
              const gloss = basis ? BASIS_GLOSS[basis] : undefined;
              const name = taxonomy.sectors[key] ?? key;
              return (
                <button
                  key={key}
                  type="button"
                  className="sector-cell as-button"
                  onClick={() => onExplain({ kind: "sector", sector: key })}
                  title={gloss ? `${name}: ${gloss.long} Click to see how it is built.` : `Explain ${name}`}
                  aria-label={`Explain ${name}: ${fmtIndex(value)}${gloss ? `, ${gloss.short}` : ""}`}
                >
                  <span className="sc-top">
                    <span className="sc-name">{name}</span>
                    <span className="num sc-value" style={{ color }}>{fmtIndex(value)}</span>
                  </span>
                  <span className="sector-bar"><i style={{ width: `${Math.min(100, value ?? 0)}%`, background: color }} /></span>
                  {gloss && <span className="sc-basis">{gloss.short}</span>}
                </button>
              );
            })}
            {uncovered.length > 0 && (
              <div className="sector-cell uncovered" title="No published capacity base, so these sectors are shown but not scored. Their weight is shared among the scored sectors; excluded is not zero.">
                <span className="sc-top">
                  <span className="sc-name">Not scored</span>
                  <span className="sc-uncovered">{uncovered.map((s) => taxonomy.sectors[s] ?? s).join(", ")}</span>
                </span>
                <span className="sc-basis">no capacity base — excluded, not zero</span>
              </div>
            )}
          </div>

          {/* Recovery headline. §11: the headline is the national EVIDENCE COUNT, not the pooled
              cross-class median — a 2-day terminal restart and a 205-day gas-plant repair are not
              one repair time. These are as-at-build counts; only the ESDI follows the scrubber, so
              the group says so once, in words, instead of on every label. */}
          <div className="recovery-group" title="Counted at the publication date — these do not follow the timeline scrubber; only the index does.">
            <span className="rg-head">Recovery evidence · <span className="warn-text">not timeline-linked</span></span>
            <div className="rg-stats">
              <RecoveryStat value={rs.unresolved_count} color="var(--amber)"
                            label="with no restoration report by the cut-off"
                            title={noReportMeaning(snapshot.as_of, snapshot.campaign_policy)} />
              <RecoveryStat
                value={rs.observed_restoration_episodes}
                color="var(--green)"
                label="observed-restoration episodes"
                title={rs.median_observed_restoration_days != null
                  ? `Median ${rs.median_observed_restoration_days} days across all infrastructure types mixed — not a norm for any one sector. Per-type medians are in the Recovery tab.`
                  : `Fewer than ${rs.min_median_episodes} episodes, too few for a pooled median.`}
              />
              <RecoveryStat value={rs.full_reconstitution_episodes} color="var(--green)"
                            label="reconstitution episodes" />
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

function RecoveryStat({
  value, label, title, color,
}: {
  value: React.ReactNode; label: string; title?: string; color: string;
}) {
  return (
    <div className="rstat" title={title}>
      <span className="num rstat-value" style={{ color }}>{value}</span>
      <span className="rstat-label">{label}</span>
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
      title={buildDeltaTitle(bc.previous_build)}
    >
      <span className={bc.esdi_delta > 0 ? "up" : bc.esdi_delta < 0 ? "down" : ""}>
        {fmtDelta(bc.esdi_delta)}
      </span>
      {" "}since last build · {label}
    </button>
  );
}
