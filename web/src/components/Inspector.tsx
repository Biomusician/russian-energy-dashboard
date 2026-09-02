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
  Bundle, ContributingFacility, Incident, RegionExplanation, SectorExplanation,
} from "../types";
import { fmtDate, fmtNum, loadRegionalExplanations, titleCase } from "../data";
import { severityColor } from "../palette";
import { EvidenceChip, RecoveryLine, hostOf } from "./ui";

export type InspectTarget =
  | { kind: "headline" }
  | { kind: "sector"; sector: string }
  | { kind: "region"; code: string }
  | { kind: "facility"; assetId: string }
  | { kind: "incident"; incidentId: string };

export function targetKey(t: InspectTarget): string {
  return t.kind === "sector" ? `sector:${t.sector}`
    : t.kind === "region" ? `region:${t.code}`
    : t.kind === "facility" ? `facility:${t.assetId}`
    : t.kind === "incident" ? `incident:${t.incidentId}`
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
          {!ex && current.kind !== "incident" && current.kind !== "region" ? (
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
      case "facility": return bundle.assets.find((a) => a.asset_id === t.assetId)?.name ?? t.assetId;
      case "incident": return "Event";
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
  return (
    <button className="contrib-row" onClick={onClick}>
      <span className="contrib-name">
        {c.name ?? c.asset_id}
        {c.evidence_kind && <EvidenceChip kind={c.evidence_kind} />}
      </span>
      <span className="contrib-math mono">
        {fmtNum(c.capacity_share_pct, 2)}% × {c.disruption_weight.toFixed(3)}
      </span>
      <span className="contrib-bar">
        <i style={{ width: `${max > 0 ? (c.sector_points / max) * 100 : 0}%`,
                    background: "var(--accent-dim)" }} />
      </span>
      <span className="contrib-pts mono">{fmtNum(c.sector_points, 2)}</span>
    </button>
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
          <p className={ex.zero_basis === "impairment_present_but_unscorable" ? "warn-text" : "lede"}>
            {ex.zero_note}
          </p>
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
            Contributes <span className="mono">{fmtNum(contrib.sector_points, 2)}</span> percentage
            points to {bundle.taxonomy.sectors[inSector] ?? titleCase(inSector)}: it is
            {" "}<span className="mono">{fmtNum(contrib.capacity_share_pct, 2)}%</span> of that
            sector's capacity base, carrying a disruption weight of
            {" "}<span className="mono">{contrib.disruption_weight.toFixed(3)}</span>.
          </p>
        ) : (
          <p className="lede">
            This facility is not currently contributing to the index. It may have recovered, decayed
            out of the scoring window, or sit in a sector with no capacity base.
          </p>
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
