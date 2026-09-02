/** Evidence Inspector — "explain this number" (iteration 11 §2-§6).
 *
 *  WHY IT EXISTS. The dashboard asks a reader to act on a composite built from weights,
 *  renormalisation, capacity shares, a saturation constant, damage multipliers and time decay.
 *  Until now the only way to find out what was inside 17.27 was to read the methodology page and
 *  take it on trust. This panel makes the number openable: headline → sector → facility →
 *  incident → the source URL a human can go and read.
 *
 *  WHAT IT DELIBERATELY DOES NOT DO. It performs no methodology arithmetic. Every figure below is
 *  read from `snapshot.explanations`, emitted by pipeline/explain.py beside the code that
 *  computes the index. The one calculation here is a bar width. If this file ever starts
 *  deriving a weight or a share, the product has two scoring models and the explanation will
 *  eventually describe a number that no longer exists.
 *
 *  It is a fixed overlay, not a docked rail. The map is the primary workspace, and an
 *  explanation panel that permanently narrowed it would trade a real problem for a worse one.
 */

import { useEffect, useState } from "react";
import type {
  Bundle, BuildChange, BuildChanges, ChangeNature, ContributingFacility, DataQuality, Incident,
  RegionExplanation, SectorExplanation, SourceRecord, ZeroBasis,
} from "../types";
import {
  fmtDate, fmtDelta, fmtNum, loadDataQuality, loadRegionalExplanations, titleCase,
} from "../data";
import { severityColor } from "../palette";
import { EvidenceChip, RecoveryLine, hostOf } from "./ui";

export type InspectTarget =
  | { kind: "headline" }
  | { kind: "sector"; sector: string }
  | { kind: "region"; code: string }
  | { kind: "facility"; assetId: string }
  | { kind: "incident"; incidentId: string }
  /** The build-to-build change ledger (§7-§10). It lives here rather than in a ninth dossier
   *  tab because "why did this number move" is the same question the Inspector already answers,
   *  and the tab bar has no room left that would not cost the map. */
  | { kind: "build" }
  /** Data quality, source freshness, and what the dashboard cannot tell you (§5). */
  | { kind: "quality" };

export function targetKey(t: InspectTarget): string {
  return t.kind === "sector" ? `sector:${t.sector}`
    : t.kind === "region" ? `region:${t.code}`
    : t.kind === "facility" ? `facility:${t.assetId}`
    : t.kind === "incident" ? `incident:${t.incidentId}`
    : t.kind === "build" ? "build"
    : t.kind === "quality" ? "quality"
    : "headline";
}

export default function Inspector({
  bundle, target, onNavigate, onClose,
}: {
  bundle: Bundle;
  /** The navigation stack, oldest first. The last entry is what is shown. */
  target: InspectTarget[];
  onNavigate: (t: InspectTarget[]) => void;
  onClose: () => void;
}) {
  const current = target[target.length - 1];
  const ex = bundle.snapshot.explanations;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      // Escape steps back through the drill-down before it closes the panel: a reader four
      // levels deep into a source trail should not lose the whole trail to one keypress.
      if (target.length > 1) onNavigate(target.slice(0, -1));
      else onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [target, onNavigate, onClose]);

  const push = (t: InspectTarget) => onNavigate([...target, t]);

  return (
    <>
      <button className="inspector-scrim" aria-label="Close inspector" onClick={onClose} />
      <aside className="inspector" role="dialog" aria-label="Evidence inspector">
        <div className="section-head inspector-head">
          <div style={{ minWidth: 0 }}>
            <div className="eyebrow">Evidence inspector</div>
            <Breadcrumb target={target} onNavigate={onNavigate} bundle={bundle} />
          </div>
          <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
            {target.length > 1 && (
              <button className="ghost" onClick={() => onNavigate(target.slice(0, -1))}>back</button>
            )}
            <button className="ghost" onClick={onClose}>close</button>
          </div>
        </div>

        <div className="inspector-body">
          {current.kind === "quality" ? (
            <DataQualityView bundle={bundle} onDrill={push} />
          ) : current.kind === "build" ? (
            <BuildLedgerView bundle={bundle} onDrill={push} />
          ) : !ex && current.kind !== "incident" && current.kind !== "region" ? (
            <Unavailable />
          ) : current.kind === "headline" ? (
            <HeadlineView bundle={bundle} onDrill={push} />
          ) : current.kind === "sector" ? (
            <SectorView bundle={bundle} sector={current.sector} onDrill={push} />
          ) : current.kind === "region" ? (
            <RegionView bundle={bundle} code={current.code} onDrill={push} />
          ) : current.kind === "facility" ? (
            <FacilityView bundle={bundle} assetId={current.assetId} onDrill={push} />
          ) : (
            <IncidentView bundle={bundle} incidentId={current.incidentId} onDrill={push} />
          )}
        </div>
      </aside>
    </>
  );
}

function Unavailable() {
  return (
    <div className="empty" style={{ padding: 24 }}>
      <div className="eyebrow">Explanation unavailable</div>
      <p style={{ lineHeight: 1.6, color: "var(--text-dim)" }}>
        This build's data payload predates the explanation emitter, so there is nothing to
        decompose. The published numbers are still valid — the trace behind them is not
        available in this payload.
      </p>
    </div>
  );
}

function Breadcrumb({
  target, onNavigate, bundle,
}: { target: InspectTarget[]; onNavigate: (t: InspectTarget[]) => void; bundle: Bundle }) {
  const label = (t: InspectTarget): string => {
    switch (t.kind) {
      case "headline": return "ESDI";
      case "sector": return bundle.taxonomy.sectors[t.sector] ?? titleCase(t.sector);
      case "region": return bundle.regions.find((r) => r.code === t.code)?.name ?? t.code;
      case "facility":
        // Not every scored facility is in the asset inventory — curated incidents can name one
        // no source table lists. Fall back through the live-disruption record before showing a
        // raw asset id, which reads as a bug.
        return bundle.assets.find((a) => a.asset_id === t.assetId)?.name
          ?? (bundle.snapshot.live_disruptions ?? []).find((d) => d.asset_id === t.assetId)?.name
          ?? t.assetId;
      case "incident": return "Event";
      case "build": return "Since last build";
      case "quality": return "Data quality";
    }
  };
  return (
    <div className="inspector-crumb">
      {target.map((t, i) => (
        <span key={targetKey(t) + i}>
          {i > 0 && <span className="sep">›</span>}
          {i === target.length - 1 ? (
            <span className="here">{label(t)}</span>
          ) : (
            <button className="linkish" onClick={() => onNavigate(target.slice(0, i + 1))}>
              {label(t)}
            </button>
          )}
        </span>
      ))}
    </div>
  );
}

/** The reconciliation line. Shown on every decomposition, and shown even when it fails —
 *  a silent failure would leave a reader trusting a total that no longer adds up. */
function Reconciles({ sum, value, unit = "" }: { sum: number; value: number; unit?: string }) {
  const ok = Math.abs(sum - value) <= 0.02;
  return (
    <div className={`reconcile ${ok ? "ok" : "bad"}`}>
      <span className="mono">{fmtNum(sum, 2)}{unit}</span>
      <span>{ok ? "=" : "≠"}</span>
      <span className="mono">{fmtNum(value, 2)}{unit}</span>
      <span className="note">
        {ok ? "components reconcile to the published figure"
            : "components DO NOT reconcile — treat this decomposition as unreliable"}
      </span>
    </div>
  );
}

function HeadlineView({ bundle, onDrill }: { bundle: Bundle; onDrill: (t: InspectTarget) => void }) {
  const h = bundle.snapshot.explanations!.headline;
  const { taxonomy } = bundle;
  const included = h.contributions.filter((c) => c.included);
  const excluded = h.contributions.filter((c) => !c.included);
  const maxPts = Math.max(0.0001, ...included.map((c) => c.index_points));

  return (
    <>
      <Block title="How this number is built">
        <p className="lede">
          Each covered sector contributes its own value multiplied by its effective weight. The
          contributions below are the whole index — nothing else is added.
        </p>
        <div className="contrib-list">
          {included.map((c) => (
            <button key={c.sector} className="contrib-row"
                    onClick={() => onDrill({ kind: "sector", sector: c.sector })}>
              <span className="contrib-name">{taxonomy.sectors[c.sector] ?? titleCase(c.sector)}</span>
              <span className="contrib-math mono">
                {fmtNum(c.sector_value, 2)} × {c.effective_weight.toFixed(4)}
              </span>
              <span className="contrib-bar">
                <i style={{ width: `${(c.index_points / maxPts) * 100}%`,
                            background: severityColor(c.sector_value) }} />
              </span>
              <span className="contrib-pts mono">{fmtNum(c.index_points, 2)}</span>
            </button>
          ))}
        </div>
        <Reconciles sum={h.sum_of_contributions} value={h.value} />
        {h.rounding_note && (
          <p className="small rounding-note">{h.rounding_note}</p>
        )}
      </Block>

      <Block title="Why the weights are not the published weights">
        <p>{h.renormalisation_note}</p>
        <table className="mini">
          <thead><tr><th>Sector</th><th>Nominal</th><th>Effective</th></tr></thead>
          <tbody>
            {h.contributions.map((c) => (
              <tr key={c.sector} className={c.included ? "" : "dim"}>
                <td>{taxonomy.sectors[c.sector] ?? titleCase(c.sector)}</td>
                <td className="mono">{c.nominal_weight.toFixed(2)}</td>
                <td className="mono">{c.included ? c.effective_weight.toFixed(4) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Block>

      {excluded.length > 0 && (
        <Block title="What is not in this number" tone="warn">
          {excluded.map((c) => (
            <p key={c.sector}>
              <strong>{taxonomy.sectors[c.sector] ?? titleCase(c.sector)}</strong> — {c.excluded_reason}.
              {" "}Documented events in this sector exist and are <em>not</em> scored.
              Excluded is not the same as zero.
            </p>
          ))}
          {h.sensitivities.zero_assumption != null && (
            <p className="mono small">
              If the excluded sectors were assumed to be at zero disruption — an assumption known
              to be false — the index would read {fmtNum(h.sensitivities.zero_assumption, 2)}.
            </p>
          )}
        </Block>
      )}

      <Block title="Why the number falls on its own">
        <p>{h.decay.note}</p>
        <p className="mono small">{h.decay.form}</p>
        <p className="small">Half-life source: {h.decay.half_life_source}.</p>
      </Block>

      {h.sensitivities.excluding_transmission != null && (
        <Block title="How much rests on one judgement">
          <p>
            Removing transmission — the sector scored against a chosen saturation constant rather
            than a measured capacity base — gives {fmtNum(h.sensitivities.excluding_transmission, 2)}
            {" "}against the published {fmtNum(h.value, 2)}.
          </p>
        </Block>
      )}
    </>
  );
}

function SectorView({
  bundle, sector, onDrill,
}: { bundle: Bundle; sector: string; onDrill: (t: InspectTarget) => void }) {
  const e: SectorExplanation | undefined = bundle.snapshot.explanations!.sectors[sector];
  if (!e) return <Unavailable />;
  const label = bundle.taxonomy.sectors[sector] ?? titleCase(sector);

  return (
    <>
      <Block title={`${label} — ${fmtNum(e.value, 2)}`}>
        {e.proxy_warning && <div className="proxy-warn">{e.proxy_warning}</div>}
        <ZeroExplanation basis={e.zero_basis} note={e.zero_note} raw={e.raw_value} />
        {e.denominator ? (
          <>
            <p className="lede">
              This is a share of a denominator. What it divides by decides what it means.
            </p>
            <dl className="kv">
              <dt>Denominator</dt>
              <dd className="mono">{fmtNum(e.denominator.value, 1)} {e.denominator.unit}</dd>
              <dt>Source</dt>
              <dd>{e.denominator.source ?? "not stated"}</dd>
              <dt>Census vintage</dt>
              <dd>{e.denominator.vintage ?? <span className="unknown">not stated</span>}</dd>
              {e.denominator.facility_count != null && (
                <><dt>Facilities in base</dt><dd className="mono">{e.denominator.facility_count}</dd></>
              )}
              {e.denominator.completeness_pct != null && (
                <><dt>Base completeness</dt>
                  <dd className="mono">{fmtNum(e.denominator.completeness_pct, 1)}%</dd></>
              )}
              {e.denominator.known_bias && (
                <><dt>Known bias</dt><dd className="warn-text">{e.denominator.known_bias}</dd></>
              )}
            </dl>
          </>
        ) : (
          <p className="lede">This sector has no denominator, so it is not scored at all.</p>
        )}
      </Block>

      <Block title="What this figure cannot tell you" tone="warn">
        <ul className="tight">{e.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul>
      </Block>

      {e.saturation_sweep && e.saturation_sweep.length > 0 && (
        <Block title="How much the chosen constant matters">
          <table className="mini">
            <thead><tr><th>Saturation constant</th><th>Sector value</th></tr></thead>
            <tbody>
              {e.saturation_sweep.map((s) => (
                <tr key={s.saturation}>
                  <td className="mono">{s.saturation}</td>
                  <td className="mono">{fmtNum(s.sector_value, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {e.raw_burden != null && (
            <p className="small mono">raw weighted event burden {fmtNum(e.raw_burden, 2)}</p>
          )}
        </Block>
      )}

      <Block title={`Contributing facilities (${e.contributing_count})`}>
        {e.contributing.length === 0 ? (
          <p className="lede">
            Nothing is contributing to this sector on this date. That is an absence of scored
            impairment, not a statement that the sector is intact.
          </p>
        ) : (
          <>
            <div className="contrib-list">
              {e.contributing.map((c) => (
                <FacilityRow key={c.asset_id} c={c} max={e.contributing[0].sector_points}
                             onClick={() => onDrill({ kind: "facility", assetId: c.asset_id })} />
              ))}
            </div>
            <Reconciles sum={e.sum_of_contributions} value={e.value} />
          </>
        )}
      </Block>
    </>
  );
}

function FacilityRow({
  c, max, onClick,
}: { c: ContributingFacility; max: number; onClick: () => void }) {
  // The left-hand factor differs by mechanism, and labelling an event-burden count as a
  // percentage share is exactly how a reader comes to believe transmission measures
  // percent-of-grid-offline.
  const factor = c.mechanism === "event_burden"
    ? `${fmtNum(c.event_burden_units, 2)} burden`
    : `${fmtNum(c.capacity_share_pct, 2)}%`;
  return (
    <button className="contrib-row" onClick={onClick}>
      <span className="contrib-name">
        {c.name ?? c.asset_id}
        {c.evidence_kind && <EvidenceChip kind={c.evidence_kind} />}
      </span>
      <span className="contrib-math mono">
        {factor} × {c.impairment_weight.toFixed(3)}
      </span>
      <span className="contrib-bar">
        <i style={{ width: `${max > 0 ? (c.sector_points / max) * 100 : 0}%`,
                    background: "var(--accent-dim)" }} />
      </span>
      <span className="contrib-pts mono">{fmtNum(c.sector_points, 2)}</span>
    </button>
  );
}

/** The four ways a 0.00 arises, rendered so a reader can tell which one they are looking at.
 *  A signal that merely rounds away is the one most likely to be misread as absence, so it
 *  shows its raw value. */
function ZeroExplanation({
  basis, note, raw,
}: { basis: ZeroBasis; note: string | null; raw: number }) {
  if (!basis) return null;
  const alarming = basis === "IMPAIRMENT_ONLY_IN_UNCOVERED_SECTOR";
  return (
    <div className={`zero-basis ${alarming ? "warn" : ""}`}>
      <span className="flag">{basis.replace(/_/g, " ").toLowerCase()}</span>
      <p>{note}</p>
      {basis === "COVERED_SECTOR_SIGNAL_ROUNDS_TO_ZERO" && (
        <p className="mono small">raw value {raw.toExponential(2)} — not zero</p>
      )}
    </div>
  );
}

/** The factors behind one facility's impairment multiplier. Shown on demand rather than in the
 *  row, because five numbers per facility across twenty-four facilities is a wall, not a trace. */
function ImpairmentTraceBlock({ c }: { c: ContributingFacility }) {
  const t = c.impairment_trace;
  if (!t) return null;
  return (
    <dl className="kv trace">
      <dt>Attestation</dt>
      <dd className="mono">{t.confidence_weight.toFixed(2)} confidence × {t.cause_weight.toFixed(2)} cause</dd>
      <dt>Damage severity</dt><dd className="mono">{t.damage_severity.toFixed(2)}</dd>
      <dt>Initial impairment</dt><dd className="mono">{t.initial_impairment.toFixed(3)}</dd>
      <dt>Elapsed</dt>
      <dd className="mono">
        {t.days_elapsed} d against a {fmtNum(t.half_life_days, 1)} d half-life
        <span className="flag">{t.half_life_kind}</span>
      </dd>
      <dt>Decay factor</dt><dd className="mono">× {t.decay_factor.toFixed(4)}</dd>
      {t.reconstitution_cap_applied && (
        <><dt>Cap</dt><dd className="warn-text">capped at the reconstitution residual</dd></>
      )}
      <dt>Result</dt><dd className="mono">{c.impairment_weight.toFixed(4)}</dd>
    </dl>
  );
}

function RegionView({
  bundle, code, onDrill,
}: { bundle: Bundle; code: string; onDrill: (t: InspectTarget) => void }) {
  const [ex, setEx] = useState<RegionExplanation | null | "loading">("loading");
  useEffect(() => {
    let live = true;
    loadRegionalExplanations().then((all) => { if (live) setEx(all[code] ?? null); });
    return () => { live = false; };
  }, [code]);

  const region = bundle.regions.find((r) => r.code === code);
  const facilities = (bundle.snapshot.live_disruptions ?? []).filter((d) => d.region_code === code);

  if (ex === "loading") return <div className="empty" style={{ padding: 24 }}>Loading…</div>;
  if (!ex) return <Unavailable />;

  const included = ex.contributions.filter((c) => c.index_points > 0);
  const max = Math.max(0.0001, ...ex.contributions.map((c) => c.index_points));

  return (
    <>
      <Block title={`${region?.name ?? code} — ${fmtNum(ex.value, 2)}`}>
        {ex.zero_basis ? (
          <ZeroExplanation basis={ex.zero_basis} note={ex.zero_note} raw={ex.raw_value} />
        ) : (
          <>
            <div className="contrib-list">
              {included.map((c) => (
                <button key={c.sector} className="contrib-row"
                        onClick={() => onDrill({ kind: "sector", sector: c.sector })}>
                  <span className="contrib-name">
                    {bundle.taxonomy.sectors[c.sector] ?? titleCase(c.sector)}
                  </span>
                  <span className="contrib-math mono">
                    {fmtNum(c.sector_value, 2)} × {c.effective_weight.toFixed(4)}
                  </span>
                  <span className="contrib-bar">
                    <i style={{ width: `${(c.index_points / max) * 100}%`,
                                background: severityColor(c.sector_value) }} />
                  </span>
                  <span className="contrib-pts mono">{fmtNum(c.index_points, 2)}</span>
                </button>
              ))}
            </div>
            <Reconciles sum={ex.sum_of_contributions} value={ex.value} />
          </>
        )}
        {ex.unscored_sectors.length > 0 && (
          <p className="small warn-text">
            Also impaired here but unscorable: {ex.unscored_sectors.join(", ")}.
          </p>
        )}
      </Block>

      {facilities.length > 0 && (
        <Block title={`Facilities driving this region (${facilities.length})`}>
          <div className="contrib-list">
            {facilities.map((f) => (
              <button key={f.asset_id} className="contrib-row plain"
                      onClick={() => onDrill({ kind: "facility", assetId: f.asset_id })}>
                <span className="contrib-name">{f.name ?? f.asset_id}</span>
                <span className="contrib-math mono">weight {f.disruption_weight.toFixed(3)}</span>
                <span className="contrib-pts small">{fmtDate(f.latest)}</span>
              </button>
            ))}
          </div>
        </Block>
      )}
    </>
  );
}

function FacilityView({
  bundle, assetId, onDrill,
}: { bundle: Bundle; assetId: string; onDrill: (t: InspectTarget) => void }) {
  const asset = bundle.assets.find((a) => a.asset_id === assetId);
  const live = (bundle.snapshot.live_disruptions ?? []).find((d) => d.asset_id === assetId);
  const incidents = bundle.incidents
    .filter((i) => i.asset_id === assetId)
    .sort((a, b) => (a.date < b.date ? 1 : -1));

  // Which sector explanation lists it, so the facility's own contribution can be shown in the
  // same units the sector panel used.
  let contrib: ContributingFacility | undefined;
  let inSector: string | undefined;
  const sectors = bundle.snapshot.explanations?.sectors ?? {};
  for (const [s, e] of Object.entries(sectors)) {
    const hit = e.contributing.find((c) => c.asset_id === assetId);
    if (hit) { contrib = hit; inSector = s; break; }
  }

  return (
    <>
      <Block title={asset?.name ?? live?.name ?? assetId}>
        <dl className="kv">
          <dt>Class</dt><dd>{titleCase(asset?.asset_class ?? live?.asset_class ?? "unknown")}</dd>
          <dt>Sector</dt>
          <dd>{inSector ? (bundle.taxonomy.sectors[inSector] ?? titleCase(inSector)) : "—"}</dd>
          <dt>Events on record</dt><dd className="mono">{incidents.length}</dd>
        </dl>
        {contrib && inSector ? (
          <p className="lede">
            Contributes <span className="mono">{fmtNum(contrib.sector_points, 2)}</span> points to
            {" "}{bundle.taxonomy.sectors[inSector] ?? titleCase(inSector)}:{" "}
            {/* The sentence differs by mechanism because the arithmetic does. Transmission has
                no capacity base, and describing its burden count as a share of one would be the
                percent-of-grid-offline misreading in prose. */}
            {contrib.mechanism === "event_burden" ? (
              <>
                it is <span className="mono">{fmtNum(contrib.event_burden_units, 2)}</span> units of
                event burden against the saturation constant — not a share of any capacity base —
              </>
            ) : (
              <>
                it is <span className="mono">{fmtNum(contrib.capacity_share_pct, 2)}%</span> of that
                sector's capacity base,
              </>
            )}
            {" "}carrying an impairment weight of
            {" "}<span className="mono">{contrib.impairment_weight.toFixed(3)}</span>.
          </p>
        ) : (
          <p className="lede">
            This facility is not currently contributing to the index. It may have recovered, decayed
            out of the scoring window, or sit in a sector with no capacity base.
          </p>
        )}
        {contrib && <ImpairmentTraceBlock c={contrib} />}
        {contrib?.mechanism === "event_burden" && contrib.burden_note && (
          <p className="small warn-text">{contrib.burden_note}</p>
        )}
        {live?.recovery && <RecoveryLine r={live.recovery} />}
      </Block>

      <Block title={`Events (${incidents.length})`}>
        {incidents.length === 0 ? (
          <p className="lede">No events on record for this facility.</p>
        ) : (
          <div className="contrib-list">
            {incidents.map((i) => (
              <button key={i.incident_id} className="contrib-row plain"
                      onClick={() => onDrill({ kind: "incident", incidentId: i.incident_id })}>
                <span className="contrib-name">{fmtDate(i.date)} · {titleCase(i.cause)}</span>
                <span className="contrib-math">{i.confidence}</span>
                <span className="contrib-pts small">
                  {i.sources.length} {i.sources.length === 1 ? "source" : "sources"}
                </span>
              </button>
            ))}
          </div>
        )}
      </Block>
    </>
  );
}

function IncidentView({
  bundle, incidentId, onDrill,
}: { bundle: Bundle; incidentId: string; onDrill: (t: InspectTarget) => void }) {
  const inc: Incident | undefined = bundle.incidents.find((i) => i.incident_id === incidentId);
  if (!inc) return <Unavailable />;

  // Capacity fields are shown ONLY where the source stated one. An em-dash here is a real
  // finding: most open reporting never says how much capacity an event removed.
  const quantified: [string, string][] = [];
  if (inc.capacity_affected_mw != null)
    quantified.push(["Capacity affected", `${fmtNum(inc.capacity_affected_mw, 0)} MW`]);
  if (inc.capacity_affected_mtpa != null)
    quantified.push(["Capacity affected", `${fmtNum(inc.capacity_affected_mtpa, 2)} MTPA`]);
  if (inc.capacity_affected_pct != null)
    quantified.push(["Share of facility", `${fmtNum(inc.capacity_affected_pct, 0)}%`]);

  return (
    <>
      <Block title={`${fmtDate(inc.date)} — ${titleCase(inc.cause)}`}>
        <dl className="kv">
          <dt>Facility</dt>
          <dd>
            <button className="linkish"
                    onClick={() => onDrill({ kind: "facility", assetId: inc.asset_id })}>
              {inc.asset_name ?? inc.asset_id}
            </button>
          </dd>
          <dt>Date precision</dt>
          <dd>{inc.date_precision === "month" ? "month only" : "exact day"}</dd>
          <dt>Attribution</dt>
          <dd>{titleCase(inc.attribution)} <span className="small">({inc.attribution_confidence})</span></dd>
          <dt>Confidence</dt><dd>{inc.confidence}</dd>
          {inc.status && <><dt>Status</dt><dd>{titleCase(inc.status)}</dd></>}
          {quantified.map(([k, v]) => <span key={k + v}><dt>{k}</dt><dd className="mono">{v}</dd></span>)}
        </dl>
        {quantified.length === 0 && (
          <p className="small">
            No source quantified the capacity effect of this event. The index scores it by
            evidence strength and cause, never by an invented tonnage.
          </p>
        )}
        {inc.conflicting_reports && (
          <p className="warn-text">
            Sources disagree about this event. The disagreement is preserved rather than resolved.
          </p>
        )}
        {inc.notes && <p>{inc.notes}</p>}
      </Block>

      <Block title={`Sources (${inc.sources.length})`}>
        {inc.sources.length === 0 ? (
          <p className="warn-text">This event carries no source.</p>
        ) : (
          <ul className="tight">
            {inc.sources.map((s, i) => (
              <li key={i}>
                <a href={s.url} target="_blank" rel="noreferrer noopener">
                  {s.title ?? hostOf(s.url)}
                </a>
                <span className="small"> · {hostOf(s.url)}{s.date ? ` · ${fmtDate(s.date)}` : ""}</span>
              </li>
            ))}
          </ul>
        )}
      </Block>
    </>
  );
}

function Block({
  title, children, tone,
}: { title: string; children: React.ReactNode; tone?: "warn" }) {
  return (
    <section className={`inspector-block${tone ? ` ${tone}` : ""}`}>
      <h3>{title}</h3>
      {children}
    </section>
  );
}


const NATURE_COPY: Record<ChangeNature, { label: string; blurb: string }> = {
  world: {
    label: "The world changed",
    blurb: "Something happened and was reported: a new event, or an observed restoration.",
  },
  data: {
    label: "The record changed",
    blurb: "What we assert changed; the world did not. A correction, a new source, a withdrawal.",
  },
  methodology: {
    label: "The measurement changed",
    blurb: "We changed how the index is computed. Movement here is ours, not the world's.",
  },
  time_progression: {
    label: "Time passed",
    blurb: "Modelled impairment ages with the evaluation date. Never evidence of repair.",
  },
};

const RECORD_CLASS_LABEL: Record<string, string> = {
  current_event: "happened since the last build",
  historical_record_added: "older event, added now",
  historical_evidence_added: "older evidence, arrived now",
  correction: "correction",
  withdrawal: "withdrawn",
  input_change: "build input",
};

/** Which builds are being compared, and whether that can be proven (addendum §19).
 *  During development this is deliberately loud: a branch/testing mistake should be visible
 *  rather than inferred from a delta that looks plausible. */
function LineageBadge({ bc }: { bc: BuildChanges }) {
  const l = bc.lineage;
  if (!l) return null;
  const tone = l.mode === "production" ? "ok" : l.valid ? "dev" : "bad";
  const label = l.mode === "production" ? "production ancestor"
    : l.mode === "development" ? "development comparison"
    : l.mode === "backward" ? "backwards comparison"
    : "lineage unproven";
  return (
    <div className={`lineage ${tone}`}>
      <span className="flag">{label}</span>
      {l.previous_commit && (
        <span className="mono small">
          {l.baseline_ref} @ {l.previous_commit.slice(0, 8)}
          {l.current_branch ? ` · built on ${l.current_branch}` : ""}
        </span>
      )}
      {l.previous_commit_subject && (
        <p className="small">baseline: {l.previous_commit_subject}</p>
      )}
      {l.reason && <p className="small">{l.reason}</p>}
      {l.worktree_payload_differs_from_baseline && (
        <p className="small">
          The payload in this working tree differs from the committed baseline. The commit was
          used; the local copy was not.
        </p>
      )}
    </div>
  );
}

function BuildLedgerView({
  bundle, onDrill,
}: { bundle: Bundle; onDrill: (t: InspectTarget) => void }) {
  const bc = bundle.buildChanges;
  if (!bc) {
    return (
      <div className="empty" style={{ padding: 24 }}>
        <div className="eyebrow">No comparison available</div>
        <p style={{ lineHeight: 1.6, color: "var(--text-dim)" }}>
          This payload carries no change ledger, so there is nothing to compare this build
          against. That is not the same as a build in which nothing changed.
        </p>
      </div>
    );
  }

  if (bc.unavailable_reason) {
    return (
      <>
        <Block title="No provable comparison" tone="warn">
          <p className="lede">
            This build has no provable production ancestor, so there is nothing to compare it
            against: {bc.unavailable_reason}. A delta of zero would claim a quiet build that was
            never actually compared.
          </p>
        </Block>
        <Block title="Lineage"><LineageBadge bc={bc} /></Block>
      </>
    );
  }

  const byNature = (n: ChangeNature) => bc.changes.filter((c) => c.nature === n);
  const orderedNatures: ChangeNature[] = ["world", "data", "methodology"];

  return (
    <>
      <Block title="What moved">
        <div className="ledger-head">
          <span className="mono big">{fmtNum(bc.esdi_before, 2)}</span>
          <span className="arrow">→</span>
          <span className="mono big">{fmtNum(bc.esdi_after, 2)}</span>
          <span className={`mono delta ${(bc.esdi_delta ?? 0) > 0 ? "up" : (bc.esdi_delta ?? 0) < 0 ? "down" : ""}`}>
            {bc.esdi_delta === null ? "—" : fmtDelta(bc.esdi_delta)}
          </span>
        </div>
        <p className="small">
          {bc.previous_as_of} → {bc.current_as_of}
          {bc.as_of_direction === "backward" && " (evaluated at an EARLIER date)"}
          {bc.previous_build && ` · built ${bc.previous_build.slice(0, 10)} → ${(bc.current_build ?? "").slice(0, 10)}`}
        </p>
        {bc.time_progression_only && (
          <p className="decay-note">{bc.time_progression_note}</p>
        )}
        {!bc.time_progression_only && bc.change_count === 0 && bc.esdi_delta === 0 && (
          <p className="lede">Nothing changed and the index did not move.</p>
        )}
        {!bc.input_fingerprints_comparable && (
          <p className="small">
            The baseline build carries no input fingerprint, so "nothing changed" cannot be
            proven for it — only that nothing turned up in the payloads compared here.
          </p>
        )}
        {!bc.attribution_separable && bc.non_separable_reason && (
          <p className="decay-note">{bc.non_separable_reason}</p>
        )}
        <LineageBadge bc={bc} />
      </Block>

      {bc.change_count > 0 && (
        <Block title={`Changes (${bc.change_count})`}>
          <p className="lede">
            Grouped by what kind of fact each one is. A change to the record is not a change in
            the world, and the ledger never merges the two.
          </p>
          {orderedNatures.map((n) => {
            const rows = byNature(n);
            if (!rows.length) return null;
            return (
              <div key={n} className={`nature-group ${n}`}>
                <h4>
                  {NATURE_COPY[n].label}
                  <span className="count">{rows.length}</span>
                </h4>
                <p className="small">{NATURE_COPY[n].blurb}</p>
                <div className="contrib-list">
                  {rows.map((c) => <ChangeRow key={`${c.category}:${c.id}`} c={c} onDrill={onDrill} />)}
                </div>
              </div>
            );
          })}
        </Block>
      )}

      {!bc.sector_attribution && (
        <Block title="Where the movement sits">
          <p className="lede">
            The baseline build published no decomposition, so this movement cannot be attributed
            to sectors or facilities. Showing its contributors as newly arrived would invent a
            story about a build that simply could not report them.
          </p>
        </Block>
      )}

      {bc.sector_attribution && bc.sector_attribution.rows.length > 0 && (
        <Block title="Where the movement sits">
          <table className="mini">
            <thead>
              <tr><th>Sector</th><th>Before</th><th>After</th><th>Δ index pts</th></tr>
            </thead>
            <tbody>
              {bc.sector_attribution.rows.map((r) => (
                <tr key={r.sector} className={r.delta === 0 ? "dim" : ""}>
                  <td>
                    {bundle.taxonomy.sectors[r.sector] ?? titleCase(r.sector)}
                    {r.rescaled && <span className="flag" title="denominator or weight changed">rescaled</span>}
                  </td>
                  <td className="mono">{fmtNum(r.index_points_before, 2)}</td>
                  <td className="mono">{fmtNum(r.index_points_after, 2)}</td>
                  <td className="mono">{fmtDelta(r.delta)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Reconciles
            sum={bc.sector_attribution.sum_of_sector_deltas}
            value={bc.sector_attribution.headline_delta}
          />
        </Block>
      )}

      {bc.facility_attribution.length > 0 && (
        <Block title={`Facility movement (${bc.facility_attribution.length})`} tone="warn">
          <p className="small">{bc.attribution_note}</p>
          <div className="contrib-list">
            {bc.facility_attribution.slice(0, 40).map((r) => (
              <button
                key={`${r.sector}:${r.asset_id}`}
                className="contrib-row plain"
                onClick={() => onDrill({ kind: "facility", assetId: r.asset_id })}
              >
                <span className="contrib-name">
                  {r.name ?? r.asset_id}
                  {r.entered && <span className="flag">entered</span>}
                  {r.left && <span className="flag">left</span>}
                  {!r.attribution_exact && (
                    <span className="flag warn" title={r.non_additive_reason ?? undefined}>
                      not attributable
                    </span>
                  )}
                </span>
                <span className="contrib-math mono">
                  {fmtNum(r.sector_points_before, 2)} → {fmtNum(r.sector_points_after, 2)}
                </span>
                <span className="contrib-pts mono">{fmtDelta(r.delta)}</span>
              </button>
            ))}
          </div>
          {bc.facility_attribution.length > 40 && (
            <p className="small">
              Showing the 40 largest movements of {bc.facility_attribution.length}.
            </p>
          )}
        </Block>
      )}
    </>
  );
}

function ChangeRow({
  c, onDrill,
}: { c: BuildChange; onDrill: (t: InspectTarget) => void }) {
  const drillable = c.category.startsWith("incident") || c.category === "source_added";
  const go = () => {
    if (drillable) onDrill({ kind: "incident", incidentId: c.id });
    else if (c.asset_id) onDrill({ kind: "facility", assetId: c.asset_id });
  };
  const clickable = drillable || !!c.asset_id;
  return (
    <button className="contrib-row plain change-row" onClick={go} disabled={!clickable}>
      <span className="contrib-name">
        {c.label}
        <span className="flag">{c.category.replace(/_/g, " ")}</span>
      </span>
      <span className="contrib-math">
        {c.effective_date ? fmtDate(c.effective_date) : ""}
        <span className="flag">{RECORD_CLASS_LABEL[c.record_class] ?? c.record_class}</span>
      </span>
      <span className="change-detail">{c.detail}</span>
    </button>
  );
}


const STATE_COPY: Record<string, { label: string; blurb: string }> = {
  scored: {
    label: "Scored",
    blurb: "Measured against a published capacity base.",
  },
  experimental: {
    label: "Experimental",
    blurb: "Scored against a chosen constant, not a measured capacity base. Read the caveat.",
  },
  uncovered: {
    label: "Not scored",
    blurb: "No capacity denominator exists, so this sector is excluded and its weight " +
           "redistributed. Documented strikes here are NOT counted. Excluded is not zero.",
  },
};

const CITABILITY_COPY: Record<string, string> = {
  citable_release: "citable release",
  snapshot_of_a_live_source: "snapshot of a live source",
  internal_versioned_by_repo: "internal, versioned in this repository",
  release_expected_but_absent: "no release identifier recorded",
};

/** Data quality, source freshness, and the limits of the dataset (§5, addendum §14/§15).
 *
 *  Ordered the way the addendum prioritises it: sector state first, then what the dashboard
 *  cannot tell you, then full per-source provenance. None of it is badged over the map — a
 *  reader who wants the provenance comes here, and everyone else keeps the map. */
function DataQualityView({
  bundle, onDrill,
}: { bundle: Bundle; onDrill: (t: InspectTarget) => void }) {
  const [dq, setDq] = useState<DataQuality | null | "loading">("loading");
  useEffect(() => {
    let live = true;
    loadDataQuality().then((d) => { if (live) setDq(d); });
    return () => { live = false; };
  }, []);

  if (dq === "loading") return <div className="empty" style={{ padding: 24 }}>Loading…</div>;
  if (!dq) {
    return (
      <Block title="Quality report unavailable" tone="warn">
        <p className="lede">
          This payload carries no quality report. That is not a clean bill of health — it means
          the freshness and limitation data was not emitted by the build that produced it.
        </p>
      </Block>
    );
  }

  const byRole = new Map<string, SourceRecord[]>();
  for (const src of dq.sources) {
    if (!byRole.has(src.role)) byRole.set(src.role, []);
    byRole.get(src.role)!.push(src);
  }

  return (
    <>
      <Block title="What each sector is measured against">
        <p className="lede">
          Three states, and the difference between them decides how the number should be read.
        </p>
        {dq.sector_states.map((s) => (
          <div key={s.sector} className={`sector-state ${s.state}`}>
            <div className="sector-state-head">
              <button className="linkish"
                      onClick={() => onDrill({ kind: "sector", sector: s.sector })}>
                {bundle.taxonomy.sectors[s.sector] ?? titleCase(s.sector)}
              </button>
              <span className="flag">{STATE_COPY[s.state].label}</span>
              {s.value != null && <span className="mono">{fmtNum(s.value, 2)}</span>}
            </div>
            <p className="small">{STATE_COPY[s.state].blurb}</p>
            {s.denominator_value != null && (
              <p className="small mono">
                ÷ {fmtNum(s.denominator_value, 1)} {s.denominator_unit}
                {s.denominator_vintage ? ` · vintage ${s.denominator_vintage}` : ""}
              </p>
            )}
            {s.known_bias && <p className="small warn-text">Known bias: {s.known_bias}</p>}
          </div>
        ))}
      </Block>

      <Block title="What this dashboard cannot tell you" tone="warn">
        <p className="lede">
          Derived from this build, not written by hand — so the list shrinks by itself when a gap
          closes, instead of outliving it.
        </p>
        {dq.cannot_tell_you.map((c) => (
          <div key={c.question} className="cannot">
            <h4>{c.question}</h4>
            <p>{c.answer}</p>
          </div>
        ))}
      </Block>

      <Block title="Three dates that are not the same">
        <p>{dq.build_date_is_not_a_source_date}</p>
        <p className="small">{dq.citability_note}</p>
        {dq.sources_without_release_identifier.length > 0 && (
          <p className="small warn-text">
            {dq.sources_without_release_identifier.length} source(s) come from publishers that do
            issue identifiable releases, but were read without one:{" "}
            {dq.sources_without_release_identifier.join(", ")}. They cannot be cited as dated
            publications.
          </p>
        )}
      </Block>

      {[...byRole.entries()].map(([role, sources]) => (
        <Block key={role} title={`${titleCase(role)} sources (${sources.length})`}>
          {sources.map((src) => <SourceCard key={src.source_id} src={src} />)}
        </Block>
      ))}
    </>
  );
}

function SourceCard({ src }: { src: SourceRecord }) {
  return (
    <div className={`source-card ${src.freshness.status}`}>
      <div className="source-head">
        <strong>{src.name}</strong>
        <span className="flag">{src.freshness.status}</span>
      </div>
      <p className="small">{src.publisher}{src.licence ? ` · ${src.licence}` : ""}</p>
      <dl className="kv">
        <dt>Release</dt>
        <dd>
          {src.release_identifier ?? <span className="unknown">none recorded</span>}
          <span className="flag">{CITABILITY_COPY[src.citability]}</span>
        </dd>
        <dt>Retrieved</dt>
        <dd>
          {src.retrieved_at ? fmtDate(src.retrieved_at) : <span className="unknown">—</span>}
          {/* Said out loud because a cache-file timestamp on a fresh clone reads as today for a
              file that was never actually downloaded. */}
          <span className="small"> ({src.retrieval_basis})</span>
        </dd>
        <dt>Describes</dt>
        <dd>{src.content_vintage ?? <span className="unknown">not stated</span>}</dd>
      </dl>
      <p className="small">{src.freshness.note}</p>
      {src.limitations.length > 0 && (
        <ul className="tight">{src.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul>
      )}
      {src.url && (
        <p className="small">
          <a href={src.url} target="_blank" rel="noreferrer noopener">{hostOf(src.url)}</a>
        </p>
      )}
    </div>
  );
}
