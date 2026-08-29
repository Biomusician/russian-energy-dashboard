/** Small shared presentational atoms for the analytical panel. Kept in one file so the
 *  observed/estimated/unknown visual language is defined once and reused everywhere. */

import type { Incident, RecoveryState } from "../types";
import { CAUSE_COLOR, evidence, severityColor } from "../palette";
import { fmtDate, fmtNum, titleCase } from "../data";

export function EvidenceChip({ kind, text }: { kind: string; text?: string }) {
  const e = evidence(kind);
  return (
    <span className={`ev ${kind}`} style={{ color: e.color }} title={`${e.label} value`}>
      <span className="glyph">{e.glyph}</span>
      {text ?? e.label}
    </span>
  );
}

export function Tile({
  label, value, unit, n, kind, null: isNull, small,
}: {
  label: string;
  value: React.ReactNode;
  unit?: string;
  n?: number | null;
  kind?: string;
  null?: boolean;
  small?: boolean;
}) {
  return (
    <div className={`tile${isNull ? " tile-null" : ""}`}>
      <div className={`tile-val${small ? " small" : ""}`}>
        {value}
        {unit && !isNull && <span style={{ fontSize: 11, color: "var(--text-dim)" }}> {unit}</span>}
      </div>
      <div className="tile-label">{label}</div>
      <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 3 }}>
        {kind && <EvidenceChip kind={kind} />}
        {n !== undefined && n !== null && <span className="tile-n">n = {n}</span>}
      </div>
    </div>
  );
}

export function Bar({
  label, value, max, color, suffix,
}: {
  label: string;
  value: number;
  max: number;
  color?: string;
  suffix?: string;
}) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="bar-row">
      <span style={{ color: "var(--text-dim)" }}>{label}</span>
      <span className="bar-track">
        <i style={{ width: `${pct}%`, background: color ?? severityColor(value) }} />
      </span>
      <span className="bar-num">{typeof value === "number" ? fmtNum(value, value < 10 ? 1 : 0) : value}{suffix ?? ""}</span>
    </div>
  );
}

const STATUS_LABEL: Record<string, string> = {
  impaired: "Impaired",
  partial_restart: "Partial restart",
  substantially_restored: "Substantially restored",
  fully_reconstituted: "Fully reconstituted",
  unknown: "Unknown",
};

/** Compact recovery line: observed / estimated / modelled, always tagged, and never
 *  presenting a partial restart or a low-confidence estimate as full recovery. */
export function RecoveryLine({ r }: { r: RecoveryState }) {
  const kind = r.scoring_evidence_kind;
  if (r.resolved) {
    return (
      <div className="rc-recovery">
        <EvidenceChip kind="observed" text="Reconstituted" />
        {r.observed_date && <span style={{ color: "var(--text-dim)" }}>by {fmtDate(r.observed_date)}</span>}
        {r.observed_days != null && <span style={{ color: "var(--green)" }}>{r.observed_days} d observed</span>}
        {r.recovery_kind && <RecoveryKind kind={r.recovery_kind} />}
      </div>
    );
  }
  return (
    <div className="rc-recovery">
      <EvidenceChip kind={kind} />
      <span style={{ color: "var(--text-dim)" }}>{STATUS_LABEL[r.recovery_status] ?? r.recovery_status}</span>
      {r.recovery_kind && <RecoveryKind kind={r.recovery_kind} />}
      {r.impairment_age_days != null && (
        <span style={{ color: "var(--text-dim)" }}>impaired {r.impairment_age_days} d</span>
      )}
      {r.recovery_status === "partial_restart" && r.partial_operations_resumed_at && (
        <span style={{ color: "var(--amber)" }}>
          partial restart {fmtDate(r.partial_operations_resumed_at)} — not full reconstitution
        </span>
      )}
      {r.estimate_days?.central != null && (
        <span style={{ color: r.estimate_days.used_for_scoring ? "var(--amber)" : "var(--text-faint)" }}>
          est. ~{r.estimate_days.central} d
          {r.estimate_days.lower != null && r.estimate_days.upper != null &&
            ` (${r.estimate_days.lower}–${r.estimate_days.upper})`}
          {!r.estimate_days.used_for_scoring && " · low conf, not scored"}
        </span>
      )}
      {kind === "modelled" && r.recovery_status !== "partial_restart" && !r.estimate_days && (
        <span style={{ color: "var(--text-faint)" }}>
          modelled horizon ~{r.reconstitution_horizon_days} d (assumption)
        </span>
      )}
    </div>
  );
}

/** §13: the granular "what the source proves" token. Flow-rerouted / partial-throughput kinds
 *  are amber because they are explicitly NOT facility reconstitution; unit repairs are neutral. */
function RecoveryKind({ kind }: { kind: string }) {
  const flowOnly = /flow_rerouted|partial_throughput|partial_operations|interim|loadings_resumed/.test(kind);
  return (
    <span
      title="What the source establishes (distinct from the scoring bucket)"
      style={{
        fontSize: 9.5, letterSpacing: 0.2, padding: "0 5px", borderRadius: 2,
        border: "1px solid var(--line)",
        color: flowOnly ? "var(--amber)" : "var(--text-faint)",
      }}
    >
      {kind.replace(/_/g, " ")}
    </span>
  );
}

/** Event row shared by Overview, Recent and Sources tabs. */
export function EventRow({
  incident, showRegion, regionName,
}: {
  incident: Incident;
  showRegion?: boolean;
  regionName?: string;
}) {
  return (
    <div className="event">
      <div className="event-top">
        <span className="event-name">{incident.asset_name ?? "Unnamed facility"}</span>
        <span className="num" style={{ fontSize: 11, color: "var(--text-dim)", whiteSpace: "nowrap" }}>
          {fmtDate(incident.date)}
        </span>
      </div>
      <div className="event-meta">
        <span className="tag" style={{ color: CAUSE_COLOR[incident.cause], borderColor: "var(--line)" }}>
          {titleCase(incident.cause)}
        </span>
        <span className={`tag ${incident.confidence}`}>{incident.confidence}</span>
        {incident.date_precision === "month" && <span className="tag">month precision</span>}
        {incident.conflicting_reports && <span className="tag conflict">sources conflict</span>}
        {incident.part_of_unenumerated_series && <span className="tag">series undercounted</span>}
        {showRegion && regionName && <span className="tag">{regionName}</span>}
      </div>
      {incident.attribution === "reported_ukrainian_strike" && (
        <div style={{ fontSize: 10.5, color: "var(--text-faint)", marginTop: 4 }}>
          Attribution: reported Ukrainian strike ({incident.attribution_confidence}) — reported, not independently confirmed
        </div>
      )}
      {incident.notes && (
        <div style={{ fontSize: 10.5, color: "var(--text-dim)", marginTop: 4, lineHeight: 1.45 }}>
          {incident.notes}
        </div>
      )}
      {incident.sources.length > 0 ? (
        <div className="src-list">
          {incident.sources.slice(0, 3).map((s, n) => (
            <a key={n} href={s.url} target="_blank" rel="noreferrer noopener">
              ↗ {s.publisher || s.title || hostOf(s.url)}
            </a>
          ))}
        </div>
      ) : (
        <div style={{ fontSize: 10, color: "var(--text-faint)", marginTop: 4 }}>
          No direct citation captured — listed in source table without a per-event reference
        </div>
      )}
    </div>
  );
}

export function pct(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${fmtNum(value, 2)}%`;
}

export function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url.slice(0, 40);
  }
}
