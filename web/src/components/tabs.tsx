/** The seven analytical tabs of the right-hand panel. Each is a pure function of the
 *  bundle plus the current timeline position and selection. The central map stays the
 *  primary visualization; these give it depth. */

import { useMemo, useState } from "react";
import type { Bundle, Incident, LiveDisruption, RegionSnapshot } from "../types";
import { fmtDate, fmtNum, titleCase } from "../data";
import { classColor, evidence, severityColor } from "../palette";
import { Bar, EventRow, EvidenceChip, RecoveryLine, Tile, pct } from "./ui";

export interface TabProps {
  bundle: Bundle;
  step: number;
  selected: string | null;
  currentDate: string;
  incidentsByRegion: Map<string, Incident[]>;
  visibleIncidents: Incident[];
  onSelect: (code: string | null) => void;
  onTab: (tab: string) => void;
}

function Block({ title, right, children }: { title: string; right?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section style={{ padding: "10px 14px 14px", borderBottom: "1px solid var(--line-soft)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
        <div className="eyebrow">{title}</div>
        {right}
      </div>
      {children}
    </section>
  );
}

function KV({ k, v, hint }: { k: string; v: React.ReactNode; hint?: string }) {
  return (
    <div className="kv" title={hint}>
      <span className="k">{k}</span>
      <span className="v">{v}</span>
    </div>
  );
}

function Note({ children, warn }: { children: React.ReactNode; warn?: boolean }) {
  return <div className={`note${warn ? " warn" : ""}`}>{children}</div>;
}

// ============================================================ OVERVIEW

export function OverviewTab(p: TabProps) {
  const { bundle, step, selected, currentDate, incidentsByRegion, onSelect } = p;
  const region = selected ? bundle.snapshot.regions[selected] : null;

  if (!region) {
    const ranked = Object.values(bundle.snapshot.regions)
      .map((r) => ({ r, value: bundle.regional.regions[r.code]?.esdi[step] ?? 0 }))
      .filter((x) => x.value > 0 || (incidentsByRegion.get(x.r.code)?.length ?? 0) > 0)
      .sort((a, b) => b.value - a.value)
      .slice(0, 12);
    return (
      <div className="tab-body">
        <Block title="National picture">
          <KV k="Disruption exposure (ESDI)" v={fmtNum(bundle.national.esdi[step], 1)} />
          <KV k="Events to date" v={p.visibleIncidents.length} />
          <KV k="Facilities currently impaired" v={bundle.snapshot.recovery_stats.unresolved_count} />
          <KV k="Refining base tracked" v={`${fmtNum(bundle.snapshot.denominators.refining_mtpa, 0)} MTPA`} />
        </Block>
        <Block title="Most affected regions" right={<button className="ghost" style={{ padding: "1px 6px", fontSize: 10 }} onClick={() => p.onTab("Rankings")}>rankings ›</button>}>
          {ranked.length === 0 && <div className="empty">No recorded disruption at this point in the timeline.</div>}
          {ranked.map(({ r, value }) => (
            <RegionMini key={r.code} region={r} value={value} count={incidentsByRegion.get(r.code)?.length ?? 0} onSelect={onSelect} />
          ))}
        </Block>
      </div>
    );
  }

  const esdiNow = bundle.regional.regions[region.code]?.esdi[step] ?? 0;
  const regionIncidents = incidentsByRegion.get(region.code) ?? [];
  return (
    <div className="tab-body">
      <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--line-soft)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div className="num" style={{ fontSize: 32, color: severityColor(esdiNow) }}>{fmtNum(esdiNow, 1)}</div>
          <div>
            <div className="eyebrow">Disruption exposure</div>
            <div style={{ fontSize: 11, color: "var(--text-dim)" }}>as at {fmtDate(currentDate)}</div>
          </div>
        </div>
        <div className="meter"><i style={{ width: `${Math.min(100, esdiNow * 4)}%`, background: severityColor(esdiNow) }} /></div>
      </div>

      <Block title="Recorded activity">
        <KV k="Events to date" v={regionIncidents.length} />
        <KV k="Facilities affected" v={region.struck_facility_count} />
        <KV k="Currently impaired (unresolved)" v={region.unresolved_count} />
        <KV k="Installed generation" v={`${region.installed_mw.toLocaleString("en-GB")} MW`} />
      </Block>

      <Block title="Effects (summary)" right={<button className="ghost" style={{ padding: "1px 6px", fontSize: 10 }} onClick={() => p.onTab("Effects")}>full ›</button>}>
        <KV k="Generation margin" v={pct(region.effects.generation_margin)} />
        <KV k="Fuel production" v={pct(region.effects.fuel_production)} />
        <KV k="Repair burden (unresolved)" v={region.effects.repair_burden} />
        <KV k="Recurrence" v={fmtNum(region.effects.recurrence, 2)} />
      </Block>

      <Block title={`Events (${regionIncidents.length})`}>
        <div style={{ margin: "0 -14px" }}>
          {regionIncidents.length === 0 && <div className="empty">No events recorded here up to {fmtDate(currentDate)}.</div>}
          {[...regionIncidents].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 40).map((i) => (
            <EventRow key={i.incident_id} incident={i} />
          ))}
        </div>
      </Block>
    </div>
  );
}

function RegionMini({ region, value, count, onSelect }: { region: RegionSnapshot; value: number; count: number; onSelect: (c: string) => void }) {
  return (
    <div className="kv" style={{ cursor: "pointer", alignItems: "center" }} onClick={() => onSelect(region.code)}>
      <span className="k" style={{ flex: 1 }}>
        {region.name}
        <span style={{ color: "var(--text-faint)", fontSize: 10.5 }}> · {count} events · {region.district}</span>
      </span>
      <span style={{ width: 62 }}>
        <span className="meter" style={{ marginTop: 0 }}>
          <i style={{ width: `${Math.min(100, value * 12)}%`, background: severityColor(value) }} />
        </span>
      </span>
      <span className="v" style={{ width: 40, textAlign: "right" }}>{fmtNum(value, 1)}</span>
    </div>
  );
}

// ============================================================ RANKINGS

interface Metric {
  key: string;
  label: string;
  desc: string;
  value: (code: string, ctx: RankCtx) => number;
  fmt?: (v: number) => string;
  current?: boolean; // reflects "now" rather than the timeline position
}

interface RankCtx {
  bundle: Bundle;
  step: number;
  incidentsByRegion: Map<string, Incident[]>;
  currentDate: string;
}

const RANK_METRICS: Metric[] = [
  {
    key: "exposure",
    label: "Disruption exposure",
    desc: "Share of tracked capacity at disrupted sites, evidence- and recency-weighted, at the selected time. NOT measured capacity loss.",
    value: (code, c) => c.bundle.regional.regions[code]?.esdi[c.step] ?? 0,
    fmt: (v) => fmtNum(v, 1),
  },
  {
    key: "unresolved",
    label: "Unresolved disruptions",
    desc: "Facilities currently impaired with no credible restoration reported. Reflects the present, not the timeline position.",
    value: (code, c) => c.bundle.snapshot.regions[code]?.unresolved_count ?? 0,
    current: true,
  },
  {
    key: "recent",
    label: "Recent events (90 days)",
    desc: "Count of recorded events in the 90 days up to the selected date. A recency signal, not a severity measure.",
    value: (code, c) => {
      const cutoff = shift(c.currentDate, -90);
      return (c.incidentsByRegion.get(code) ?? []).filter((i) => i.date > cutoff).length;
    },
  },
  {
    key: "cumulative",
    label: "Cumulative events",
    desc: "Total recorded events in the region up to the selected date.",
    value: (code, c) => (c.incidentsByRegion.get(code) ?? []).length,
  },
  {
    key: "recurrence",
    label: "Recurrence (events / facility)",
    desc: "Mean recorded events per affected facility — how repeatedly the region's sites are hit.",
    value: (code, c) => {
      const inc = c.incidentsByRegion.get(code) ?? [];
      const fac = new Set(inc.map((i) => i.asset_id)).size;
      return fac ? inc.length / fac : 0;
    },
    fmt: (v) => fmtNum(v, 2),
  },
  {
    key: "confidence",
    label: "Data confidence",
    desc: "Share of the region's events sourced at 'confirmed' or 'probable'. A high value means well-corroborated reporting, NOT necessarily more disruption.",
    value: (code, c) => {
      const inc = c.incidentsByRegion.get(code) ?? [];
      if (!inc.length) return 0;
      const strong = inc.filter((i) => i.confidence === "confirmed" || i.confidence === "probable").length;
      return (strong / inc.length) * 100;
    },
    fmt: (v) => `${fmtNum(v, 0)}%`,
  },
];

function shift(date: string, days: number): string {
  const d = new Date(date + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export function RankingsTab(p: TabProps) {
  const [metricKey, setMetricKey] = useState("exposure");
  const [desc, setDesc] = useState(true);
  const metric = RANK_METRICS.find((m) => m.key === metricKey)!;
  const ctx: RankCtx = { bundle: p.bundle, step: p.step, incidentsByRegion: p.incidentsByRegion, currentDate: p.currentDate };

  const rows = useMemo(() => {
    return Object.values(p.bundle.snapshot.regions)
      .map((r) => ({ r, value: metric.value(r.code, ctx) }))
      // Only regions that have actually been affected are ever ranked. Never rank
      // undamaged infrastructure.
      .filter((x) => (p.incidentsByRegion.get(x.r.code)?.length ?? 0) > 0 || x.value > 0)
      .sort((a, b) => (desc ? b.value - a.value : a.value - b.value))
      .slice(0, 40);
  }, [metricKey, desc, p.step, p.incidentsByRegion]);

  const max = Math.max(1, ...rows.map((x) => x.value));

  return (
    <div className="tab-body">
      <div className="ranking-picker">
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <select className="ghost" value={metricKey} onChange={(e) => setMetricKey(e.target.value)}>
            {RANK_METRICS.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
          </select>
          <button className="ghost" onClick={() => setDesc((d) => !d)} title="Toggle order" style={{ flex: "none" }}>
            {desc ? "▼ high→low" : "▲ low→high"}
          </button>
        </div>
        <div className="ranking-desc">
          {metric.desc}
          {metric.current && <strong style={{ color: "var(--amber)" }}> (current, not timeline-linked)</strong>}
        </div>
      </div>

      {rows.length === 0 && <div className="empty">No affected regions to rank at this point in the timeline.</div>}
      {rows.map((x, i) => (
        <div
          key={x.r.code}
          className="rank"
          data-selected={x.r.code === p.selected}
          onClick={() => p.onSelect(x.r.code === p.selected ? null : x.r.code)}
        >
          <span className="rank-idx">{i + 1}</span>
          <span>
            <div className="rank-name">{x.r.name}</div>
            <div className="rank-sub">{x.r.district} · {x.r.incident_count} events</div>
            <div className="rank-bar"><i style={{ width: `${(x.value / max) * 100}%`, background: metricKey === "confidence" ? "var(--accent)" : severityColor(metricKey === "exposure" ? x.value : Math.min(12, x.value)) }} /></div>
          </span>
          <span className="rank-val">{(metric.fmt ?? ((v) => String(Math.round(v))))(x.value)}</span>
        </div>
      ))}
      <Note>Rankings only ever include regions with recorded disruption. Undamaged infrastructure is never ranked, and no ranking represents target value.</Note>
    </div>
  );
}

// ============================================================ RECENT

export function RecentTab(p: TabProps) {
  const recoveryByAsset = useMemo(
    () => new Map(p.bundle.snapshot.live_disruptions.map((d) => [d.asset_id, d])),
    [p.bundle.snapshot.live_disruptions],
  );
  const regionName = (code: string | null) => (code ? p.bundle.snapshot.regions[code]?.name : null);

  const recent = useMemo(() => {
    const pool = p.selected
      ? p.visibleIncidents.filter((i) => i.region_code === p.selected)
      : p.visibleIncidents;
    return [...pool].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 10);
  }, [p.visibleIncidents, p.selected]);

  return (
    <div className="tab-body">
      <div className="section-head" style={{ position: "static" }}>
        <h2 style={{ fontSize: 12 }}>Top 10 most recent{p.selected ? " (region)" : ""}</h2>
        <span className="eyebrow">to {fmtDate(p.currentDate)}</span>
      </div>
      {recent.length === 0 && <div className="empty">No events match the current filters and timeline position.</div>}
      {recent.map((i) => {
        const live = recoveryByAsset.get(i.asset_id);
        return (
          <div key={i.incident_id} className="rc" onClick={() => i.region_code && p.onSelect(i.region_code)}>
            <div className="rc-head">
              <span className="rc-title">{i.asset_name ?? "Unnamed facility"}</span>
              <span className="num" style={{ fontSize: 11, color: "var(--text-dim)" }}>{fmtDate(i.date)}</span>
            </div>
            <div className="rc-region">{regionName(i.region_code) ?? "—"} · {titleCase(i.asset_class ?? "")}</div>
            <div className="rc-meta">
              <span className="tag" style={{ color: classColor(i.asset_class), borderColor: "var(--line)" }}>{titleCase(i.cause)}</span>
              <span className={`tag ${i.confidence}`}>{i.confidence}</span>
              {i.conflicting_reports && <span className="tag conflict">sources conflict</span>}
            </div>
            <div className="rc-summary">{summarise(i, regionName(i.region_code))}</div>
            {live && <RecoveryLine r={live.recovery} />}
            {i.sources.length > 0 && (
              <div className="src-list" style={{ marginTop: 6 }}>
                {i.sources.slice(0, 2).map((s, n) => (
                  <a key={n} href={s.url} target="_blank" rel="noreferrer noopener">↗ {s.publisher || hostname(s.url)}</a>
                ))}
              </div>
            )}
          </div>
        );
      })}
      <Note>Summaries are generated deterministically from structured fields — never free prose. Recovery status shows observed, estimated or modelled explicitly.</Note>
    </div>
  );
}

/** Deterministic one-line summary from structured fields. No generative prose. */
function summarise(i: Incident, region: string | null): string {
  const cause = {
    kinetic_strike: "Reported kinetic strike",
    sabotage: "Reported sabotage",
    cyber: "Reported cyber incident",
    technical: "Technical incident",
    sanctions: "Sanctions / supply-chain constraint",
    maintenance: "Scheduled maintenance",
    unknown: "Disruption of unknown cause",
  }[i.cause] ?? "Disruption";
  const cls = titleCase(i.asset_class ?? "facility").toLowerCase();
  const loc = region ? ` in ${region}` : "";
  const conf = i.confidence === "confirmed" ? "corroborated by multiple sources"
    : i.confidence === "probable" ? "single-source reported"
    : "unconfirmed report";
  return `${cause} affecting a ${cls}${loc}, ${fmtDate(i.date)} (${conf}).`;
}

function hostname(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return url.slice(0, 30); }
}

// ============================================================ RECONSTITUTION

export function ReconstitutionTab(p: TabProps) {
  const rs = p.bundle.snapshot.recovery_stats;
  const kinds = rs.evidence_kind_counts;
  const totalKinds = Object.values(kinds).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="tab-body">
      <div className="concept-key">
        <span>Recovery evidence:</span>
        <EvidenceChip kind="observed" /><EvidenceChip kind="estimated" /><EvidenceChip kind="modelled" />
      </div>

      <div className="tiles">
        <Tile label="Unresolved disruptions" value={rs.unresolved_count} />
        <Tile label="Restored (observed)" value={rs.resolved_count} />
        <Tile
          label="Median observed restoration"
          value={rs.median_observed_restoration_days != null ? rs.median_observed_restoration_days : "—"}
          unit={rs.median_observed_restoration_days != null ? "days" : undefined}
          kind={rs.median_observed_restoration_days != null ? "observed" : undefined}
          n={rs.observed_restoration_sample}
          null={rs.median_observed_restoration_days == null}
        />
        <Tile
          label="Median impairment age"
          value={rs.median_impairment_age_days != null ? rs.median_impairment_age_days : "—"}
          unit={rs.median_impairment_age_days != null ? "days" : undefined}
          n={rs.impairment_age_sample}
          null={rs.median_impairment_age_days == null}
        />
      </div>

      <Block title="Recovery evidence mix">
        <div className="bars">
          {["observed", "estimated", "modelled"].map((k) => (
            <div className="bar-row" key={k}>
              <span style={{ color: evidence(k).color }}>{evidence(k).label}</span>
              <span className="bar-track"><i style={{ width: `${((kinds[k] ?? 0) / totalKinds) * 100}%`, background: evidence(k).color }} /></span>
              <span className="bar-num">{kinds[k] ?? 0}</span>
            </div>
          ))}
        </div>
        <div style={{ fontSize: 10.5, color: "var(--text-faint)", padding: "0 14px" }}>
          'Modelled' means no source-reported timing exists and a generic per-sector assumption was used.
        </div>
      </Block>

      <Block title="By sector">
        {Object.keys(rs.by_sector).length === 0 && <div className="empty">No disrupted facilities to summarise.</div>}
        {Object.entries(rs.by_sector).map(([sector, s]) => (
          <div key={sector} className="kv" style={{ alignItems: "center" }}>
            <span className="k" style={{ flex: 1 }}>
              {titleCase(sector)}
              <span style={{ color: "var(--text-faint)", fontSize: 10 }}> · {s.unresolved}/{s.disrupted_facilities} unresolved</span>
            </span>
            <span className="v">
              {s.median_observed_restoration_days != null
                ? <><span style={{ color: "var(--green)" }}>{s.median_observed_restoration_days}d</span> <span className="tile-n">n={s.observed_restoration_sample}</span></>
                : <span style={{ color: "var(--text-faint)", fontStyle: "italic", fontSize: 11 }}>no observed data</span>}
            </span>
          </div>
        ))}
      </Block>

      <Block title="Facilities with recovery evidence">
        <div style={{ margin: "0 -14px" }}>
          {p.bundle.snapshot.live_disruptions
            .filter((d) => d.recovery.recovery_evidence_kind !== "modelled" || d.recovery.resolved)
            .slice(0, 20)
            .map((d) => <RecoveryFacility key={d.asset_id} d={d} regionName={p.bundle.snapshot.regions[d.region_code ?? ""]?.name} />)}
        </div>
      </Block>

      <Note>{rs.note}</Note>
    </div>
  );
}

function RecoveryFacility({ d, regionName }: { d: LiveDisruption; regionName?: string }) {
  return (
    <div className="event">
      <div className="event-top">
        <span className="event-name">{d.name}</span>
        <span className="num" style={{ fontSize: 10.5, color: "var(--text-dim)" }}>{regionName}</span>
      </div>
      <RecoveryLine r={d.recovery} />
      {d.recovery.recovery_sources.length > 0 && (
        <div className="src-list" style={{ marginTop: 5 }}>
          {d.recovery.recovery_sources.slice(0, 2).map((s, n) => (
            <a key={n} href={s.url} target="_blank" rel="noreferrer noopener">↗ {hostname(s.url)}</a>
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================ EFFECTS

const STRATEGIC = [
  { key: "fuel_market_pressure", label: "Domestic fuel-market pressure", from: "refining" },
  { key: "refining_utilization", label: "Refining utilization pressure", from: "refining" },
  { key: "export_revenue", label: "Export / revenue effect", from: "oil_logistics" },
];

export function EffectsTab(p: TabProps) {
  const { bundle, selected, step } = p;
  const region = selected ? bundle.snapshot.regions[selected] : null;
  const heating = bundle.snapshot.heating_season;

  // National sector exposures at the current step, reused for the strategic panel.
  const sectorNow = (s: string) => (region ? region.sectors[s] ?? 0 : bundle.national.sectors[s]?.[step] ?? 0);

  const effects = region?.effects;

  return (
    <div className="tab-body">
      <div className="section-head" style={{ position: "static" }}>
        <h2 style={{ fontSize: 12 }}>{region ? region.name : "National"} — effects</h2>
        {!region && <span className="eyebrow">select a region for detail</span>}
      </div>

      {region ? (
        <>
          <Block title="Physical / operational effects">
            <EffectRow k="Generation margin" v={pct(effects!.generation_margin)} hint="share of the region's own installed MW at impaired plants" />
            <EffectRow k="Fuel production" v={pct(effects!.fuel_production)} hint="share of national refining capacity impaired here" />
            <EffectRow k="Logistics / transport" v={fmtNum(effects!.logistics, 2)} hint="weighted count of impaired oil-logistics nodes" />
            <EffectRow k="Heating exposure" v={heating ? pct(effects!.heating_season_exposure) : "out of season"} hint="thermal generation impaired during Oct–Apr" />
            <EffectRow k="Repair burden" v={effects!.repair_burden} hint="facilities with impairment still unresolved" />
            <EffectRow k="Recurrence" v={fmtNum(effects!.recurrence, 2)} hint="mean recorded events per affected facility" />
          </Block>
        </>
      ) : (
        <Block title="Sector exposure (national)">
          <div className="bars">
            {Object.entries(bundle.taxonomy.sectors).map(([k, label]) => {
              const covered = bundle.snapshot.sectors_covered.includes(k);
              return covered
                ? <Bar key={k} label={label} value={sectorNow(k)} max={100} suffix="" />
                : (
                  <div className="bar-row" key={k}>
                    <span style={{ color: "var(--text-faint)" }}>{label}</span>
                    <span style={{ gridColumn: "2 / span 2", color: "var(--text-faint)", fontStyle: "italic", fontSize: 10.5 }}>no capacity base — not scored</span>
                  </div>
                );
            })}
          </div>
        </Block>
      )}

      <Block title="Strategic / war-sustainment pressure">
        <div style={{ fontSize: 10.5, color: "var(--text-dim)", marginBottom: 8, lineHeight: 1.5 }}>
          Macro-level indicators derived from refining and logistics exposure. Deliberately strategic, never tactical: no unit-supply inference.
        </div>
        {STRATEGIC.map((s) => {
          const v = sectorNow(s.from);
          return <Bar key={s.key} label={s.label} value={v} max={100} color={severityColor(v)} suffix="" />;
        })}
        <div style={{ fontSize: 10, color: "var(--text-faint)", marginTop: 8, lineHeight: 1.45 }}>
          These track exposure in the refining and export-logistics sectors as a proxy for pressure on fuel supply and hydrocarbon export revenue — the open-source-observable channels through which energy disruption bears on war sustainment.
        </div>
      </Block>

      <Block title="Not modelled">
        {Object.entries(bundle.snapshot.not_modelled).map(([k, reason]) => (
          <div className="kv" key={k} title={reason}>
            <span className="k">{titleCase(k)}</span>
            <span className="v null">not modelled</span>
          </div>
        ))}
        <div style={{ fontSize: 10.5, color: "var(--text-faint)", marginTop: 6, lineHeight: 1.45 }}>
          These require data sources not yet ingested. Shown explicitly so a blank is never read as "no effect".
        </div>
      </Block>
    </div>
  );
}

function EffectRow({ k, v, hint }: { k: string; v: React.ReactNode; hint?: string }) {
  return (
    <div className="kv" title={hint}>
      <span className="k">{k}</span>
      <span className="v">{v}</span>
    </div>
  );
}

// ============================================================ COSTS

export function CostsTab(p: TabProps) {
  const withCost = p.bundle.incidents.filter(
    (i) => i.repair_cost_reported_usd_m != null || i.repair_cost_estimate_low_usd_m != null,
  );
  return (
    <div className="tab-body">
      <div className="section-head" style={{ position: "static" }}>
        <h2 style={{ fontSize: 12 }}>Costs & economic effects</h2>
        <span className="eyebrow">early view</span>
      </div>

      <Note warn>
        This is a data-model foundation. Repair-cost and economic-consequence figures are
        populated only from sources, and almost none are public today, so most values are
        deliberately absent. Reported, externally-estimated and modelled costs are kept
        structurally distinct and none are invented to fill the view.
      </Note>

      <div className="tiles">
        <Tile label="Incidents with a reported repair cost" value={withCost.filter((i) => i.repair_cost_reported_usd_m != null).length} />
        <Tile label="Incidents with a cost estimate" value={withCost.filter((i) => i.repair_cost_estimate_low_usd_m != null).length} />
      </div>

      {withCost.length === 0 ? (
        <div className="empty">
          No repair-cost figures are yet ingested from public sources. The schema supports
          <code> reported</code>, <code> estimated (low/high)</code> and <code> basis</code>
          fields per incident; they populate as sourced figures become available.
        </div>
      ) : (
        withCost.map((i) => (
          <div key={i.incident_id} className="event">
            <div className="event-top">
              <span className="event-name">{i.asset_name}</span>
              <span className="num" style={{ fontSize: 11 }}>{fmtDate(i.date)}</span>
            </div>
            <div style={{ fontSize: 11, marginTop: 4 }}>
              {i.repair_cost_reported_usd_m != null
                ? <><EvidenceChip kind="observed" text="Reported" /> ${i.repair_cost_reported_usd_m}M</>
                : <><EvidenceChip kind="estimated" text="Estimated" /> ${i.repair_cost_estimate_low_usd_m}–{i.repair_cost_estimate_high_usd_m}M</>}
            </div>
            {i.cost_basis && <div style={{ fontSize: 10.5, color: "var(--text-dim)", marginTop: 4 }}>{i.cost_basis}</div>}
          </div>
        ))
      )}

      <Block title="Planned economic indicators">
        {["Reported repair cost", "Estimated repair-cost range", "Export / revenue effect", "Civilian economic consequence"].map((label) => (
          <div className="kv" key={label}>
            <span className="k">{label}</span>
            <span className="v null">schema ready · unpopulated</span>
          </div>
        ))}
      </Block>
      <Note>See docs/COST_SOURCES.md for candidate open sources and their access constraints.</Note>
    </div>
  );
}

// ============================================================ SOURCES / CONFIDENCE

export function SourcesTab(p: TabProps) {
  const { bundle } = p;
  const cov = bundle.snapshot.coverage;
  const detail = bundle.snapshot.coverage_detail;
  const pool = p.selected ? p.visibleIncidents.filter((i) => i.region_code === p.selected) : p.visibleIncidents;

  const confCounts = pool.reduce<Record<string, number>>((a, i) => { a[i.confidence] = (a[i.confidence] ?? 0) + 1; return a; }, {});
  const conflicts = pool.filter((i) => i.conflicting_reports);
  const totalSources = pool.reduce((a, i) => a + i.sources.length, 0);

  const maxYear = Math.max(1, ...Object.values(detail.by_year));

  return (
    <div className="tab-body">
      {cov && (
        <div className="tiles">
          <Tile label="Events enumerated" value={cov.enumerated_in_this_dataset} />
          <Tile label="Reported strike total" value={cov.reported_total_strikes} />
          <Tile label="Coverage" value={`${Math.round(cov.coverage_ratio * 100)}%`} small />
          <Tile label="Citations (in view)" value={totalSources} small />
        </div>
      )}

      <Block title="Confidence mix (in view)">
        <div className="bars">
          {["confirmed", "probable", "possible", "unverified"].map((c) => (
            <div className="bar-row" key={c}>
              <span style={{ color: "var(--text-dim)" }}>{titleCase(c)}</span>
              <span className="bar-track"><i style={{ width: `${((confCounts[c] ?? 0) / (pool.length || 1)) * 100}%`, background: c === "confirmed" ? "var(--green)" : c === "probable" ? "var(--accent)" : c === "possible" ? "var(--amber)" : "var(--text-faint)" }} /></span>
              <span className="bar-num">{confCounts[c] ?? 0}</span>
            </div>
          ))}
        </div>
        {conflicts.length > 0 && (
          <div style={{ padding: "4px 14px", fontSize: 10.5, color: "var(--red)" }}>
            {conflicts.length} event(s) flagged with conflicting reports.
          </div>
        )}
      </Block>

      <Block title="Coverage by year">
        <div className="bars">
          {Object.entries(detail.by_year).map(([y, n]) => (
            <div className="bar-row" key={y}>
              <span style={{ color: "var(--text-dim)" }}>{y}</span>
              <span className="bar-track"><i style={{ width: `${(n / maxYear) * 100}%`, background: "var(--accent-dim)" }} /></span>
              <span className="bar-num">{n}</span>
            </div>
          ))}
        </div>
      </Block>

      <Block title="Coverage by district">
        <div className="bars">
          {Object.entries(detail.by_district).sort((a, b) => b[1] - a[1]).map(([d, n]) => (
            <div className="bar-row" key={d}>
              <span style={{ color: "var(--text-dim)", fontSize: 10.5 }}>{d}</span>
              <span className="bar-track"><i style={{ width: `${(n / Math.max(1, ...Object.values(detail.by_district))) * 100}%`, background: "var(--accent-dim)" }} /></span>
              <span className="bar-num">{n}</span>
            </div>
          ))}
        </div>
      </Block>

      <Note>{detail.note}</Note>

      <Block title="Source registry">
        {["Natural Earth 10m admin-1 — public domain",
          "WRI Global Power Plant DB v1.3 — CC BY 4.0",
          "OpenStreetMap via Overpass — ODbL",
          "English Wikipedia (Deep strike campaign, List of oil refineries) — CC BY-SA 4.0",
          "Curated incident & recovery files — per-row source URLs"].map((s) => (
          <div key={s} style={{ fontSize: 11, color: "var(--text-dim)", padding: "3px 0", borderTop: "1px solid var(--line-soft)" }}>{s}</div>
        ))}
      </Block>
    </div>
  );
}
