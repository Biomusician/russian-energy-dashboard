/** The seven analytical tabs of the right-hand panel. Each is a pure function of the
 *  bundle plus the current timeline position and selection. The central map stays the
 *  primary visualization; these give it depth. */

import { useMemo, useState } from "react";
import type { Bundle, CoverageDetail, Incident, LiveDisruption, RegionSnapshot } from "../types";
import { addDays, fmtDate, fmtDelta, fmtNum, stepFor, titleCase } from "../data";
import { classColor, evidence, severityColor } from "../palette";
import { Bar, EventRow, EvidenceChip, RecoveryLine, Sparkline, Tile } from "./ui";

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

function Block({ title, right, children }: { title: React.ReactNode; right?: React.ReactNode; children: React.ReactNode }) {
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

/** Inline ESDI trajectory (§18-19). Shows the series only UP TO the scrubber — never "future"
 *  relative to the selected date — with the current point marked, the 90-day change, and the
 *  peak-to-date. A trend at a glance without leaving the dossier. */
function TrajectorySpark({ series, dates, step, color }: { series: number[] | undefined; dates: string[]; step: number; color?: string }) {
  if (!series || series.length < 2) return null;
  const upto = series.slice(0, step + 1);
  if (upto.length < 2) return null;
  const now = upto[upto.length - 1];
  const refStep = stepFor(dates, addDays(dates[step], -90));
  const change = now - (series[refStep] ?? 0);
  const peak = Math.max(...upto);
  const changeColor = change > 0.05 ? "#e08a5a" : change < -0.05 ? "#4a9fd4" : "var(--text-dim)";
  return (
    <div style={{ padding: "10px 14px", borderBottom: "1px solid var(--line-soft)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 5 }}>
        <span className="eyebrow">ESDI trajectory</span>
        <span style={{ fontSize: 10.5, color: "var(--text-faint)" }}>{fmtDate(dates[0])} → {fmtDate(dates[step])}</span>
      </div>
      <Sparkline values={upto} markIndex={step} color={color ?? "var(--accent)"} ariaLabel="ESDI trajectory" />
      <div style={{ display: "flex", gap: 16, marginTop: 6, fontSize: 10.5, color: "var(--text-dim)" }}>
        <span>90-day change <span className="num" style={{ color: changeColor }}>{fmtDelta(change)}</span></span>
        <span>peak to date <span className="num">{fmtNum(peak, 1)}</span></span>
      </div>
    </div>
  );
}

// ============================================================ WHAT CHANGED

/** §13/§23 — the trailing-window "what changed" digest. Three DELIBERATELY separate measures
 *  over the last 7 / 30 / 90 days to the scrubber: new recorded events, new restoration
 *  evidence, and the change in the exposure index. They are never merged into one number
 *  because they answer different questions and are not additive. Scopes to the selected region
 *  when one is chosen, otherwise the whole monitored area. */
export function WhatChangedTab(p: TabProps) {
  const { bundle, step, selected, currentDate, onTab } = p;
  const [win, setWin] = useState<number>(30);
  const dates = bundle.national.dates;
  const windowStart = addDays(currentDate, -win);
  const refStep = stepFor(dates, windowStart);
  const scope = selected ? bundle.snapshot.regions[selected] : null;
  const regionName = (code: string | null | undefined) =>
    (code && bundle.snapshot.regions[code]?.name) || undefined;

  const newEvents = useMemo(
    () => bundle.incidents
      .filter((i) => i.date > windowStart && i.date <= currentDate && (!selected || i.region_code === selected))
      .sort((a, b) => b.date.localeCompare(a.date)),
    [bundle.incidents, windowStart, currentDate, selected],
  );

  const newRecovery = useMemo(
    () => bundle.snapshot.live_disruptions.filter((d) => {
      const od = d.recovery.observed_date;
      return !!od && od > windowStart && od <= currentDate && (!selected || d.region_code === selected);
    }),
    [bundle.snapshot.live_disruptions, windowStart, currentDate, selected],
  );

  const series = selected ? bundle.regional.regions[selected]?.esdi : bundle.national.esdi;
  const esdiNow = series?.[step] ?? 0;
  const esdiThen = series?.[refStep] ?? 0;
  const esdiDelta = esdiNow - esdiThen;
  const deltaColor = esdiDelta > 0.05 ? "#e08a5a" : esdiDelta < -0.05 ? "#4a9fd4" : "var(--text-dim)";

  return (
    <>
      <Block
        title="What changed"
        right={
          <div className="seg">
            {[7, 30, 90].map((w) => (
              <button key={w} className={`seg-btn${win === w ? " on" : ""}`} onClick={() => setWin(w)}>
                {w}d
              </button>
            ))}
          </div>
        }
      >
        <Note>
          Three independent measures over the {win} days to {fmtDate(currentDate)}
          {scope ? ` in ${scope.name}` : " across the monitored area"}. Shown separately on
          purpose: a new event, a new restoration, and a change in the exposure index are
          different things and never sum.
        </Note>
      </Block>

      <Block title="New recorded events" right={<span className="num" style={{ fontSize: 15 }}>{newEvents.length}</span>}>
        {newEvents.length === 0 ? (
          <Note>No events recorded in this window.</Note>
        ) : (
          <>
            {newEvents.slice(0, 6).map((i) => (
              <EventRow key={i.incident_id} incident={i} showRegion={!selected} regionName={regionName(i.region_code)} />
            ))}
            {newEvents.length > 6 && (
              <button className="linklike" onClick={() => onTab("Recent")}>
                +{newEvents.length - 6} more — open the Recent tab
              </button>
            )}
          </>
        )}
      </Block>

      <Block
        title="New restoration evidence"
        right={<span className="num" style={{ fontSize: 15, color: "var(--green)" }}>{newRecovery.length}</span>}
      >
        {newRecovery.length === 0 ? (
          <Note>No restoration observed in this window. Absence of evidence is not restoration.</Note>
        ) : (
          newRecovery.slice(0, 6).map((d, i) => (
            <div key={i} style={{ padding: "6px 0", borderBottom: i < Math.min(6, newRecovery.length) - 1 ? "1px solid var(--line-soft)" : undefined }}>
              <div className="event-top">
                <span className="event-name">{d.name ?? titleCase(d.asset_class ?? "facility")}</span>
                <span className="num" style={{ fontSize: 11, color: "var(--text-dim)" }}>{fmtDate(d.recovery.observed_date!)}</span>
              </div>
              {!selected && d.region_code && <div className="eyebrow" style={{ marginTop: 2 }}>{regionName(d.region_code)}</div>}
              <RecoveryLine r={d.recovery} />
            </div>
          ))
        )}
      </Block>

      <Block title="Change in exposure index (ESDI)">
        <KV k={scope ? `${scope.name} — now` : "Monitored area — now"} v={<span className="num">{fmtNum(esdiNow, 2)}</span>} />
        <KV k={`${win} days ago · ${fmtDate(dates[refStep])}`} v={<span className="num">{fmtNum(esdiThen, 2)}</span>} />
        <KV k="Change over the window" v={<span className="num" style={{ color: deltaColor }}>{fmtDelta(esdiDelta)}</span>} />
        <Note>
          A modelled change in the exposure index — driven by new events and by recovery
          decay — not a measure of observed physical damage. On the map, the “Change in ESDI”
          choropleth shows this per region (blue = fell, red = rose).
        </Note>
      </Block>
    </>
  );
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
        <TrajectorySpark series={bundle.national.esdi} dates={bundle.national.dates} step={step} />
        <Block title="Monitored-area picture">
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
  // Occupied-territory treatment is independent of index inclusion: Crimea is now IN the
  // Monitored-Area index but keeps its distinct violet styling and sovereignty banner.
  const isOccupied = region.analytic_scope !== "aoi";
  return (
    <div className="tab-body">
      {isOccupied && (
        <div className="context-banner">
          <div className="eyebrow" style={{ color: "var(--violet)" }}>Occupied territory — in the index, shown separately</div>
          <div style={{ fontSize: 11.5, marginTop: 4, lineHeight: 1.5 }}>
            <strong>Sovereignty:</strong> {region.sovereignty}<br />
            <strong>De-facto control:</strong> {region.de_facto_control}
          </div>
          {region.status_note && (
            <div style={{ fontSize: 10.5, color: "var(--text-dim)", marginTop: 5, lineHeight: 1.45 }}>{region.status_note}</div>
          )}
        </div>
      )}
      <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--line-soft)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div className="num" style={{ fontSize: 32, color: isOccupied ? "var(--violet)" : severityColor(esdiNow) }}>{fmtNum(esdiNow, 1)}</div>
          <div>
            <div className="eyebrow">Disruption exposure{isOccupied && " · occupied"}</div>
            <div style={{ fontSize: 11, color: "var(--text-dim)" }}>as at {fmtDate(currentDate)}</div>
          </div>
        </div>
        <div className="meter"><i style={{ width: `${Math.min(100, esdiNow * 4)}%`, background: isOccupied ? "var(--violet)" : severityColor(esdiNow) }} /></div>
      </div>

      <TrajectorySpark
        series={bundle.regional.regions[region.code]?.esdi}
        dates={bundle.national.dates}
        step={step}
        color={isOccupied ? "var(--violet)" : severityColor(esdiNow)}
      />

      <Block title="Recorded activity">
        <KV k="Events to date" v={regionIncidents.length} />
        <KV k="Facilities affected" v={region.struck_facility_count} />
        <KV k="Currently impaired (unresolved)" v={region.unresolved_count} />
        <KV k="Reconstitution backlog" v={`${region.reconstitution_backlog_days} d`} hint="summed remaining reconstitution time across unresolved facilities" />
      </Block>

      <Block title="Regional intensity vs national contribution">
        <KV k="Contribution to national exposure" v={fmtNum(esdiNow, 1)} hint="this region's share of the national disrupted-capacity exposure" />
        <KV
          k="Regional disruption intensity"
          v={region.regional_intensity?.composite != null ? fmtNum(region.regional_intensity.composite, 1) : "—"}
          hint="disruption vs the region's own tracked base (generation + transmission)"
        />
        {(region.regional_intensity?.missing_sectors.length ?? 0) > 0 && (
          <div style={{ fontSize: 10, color: "var(--amber)", marginTop: 4 }}>
            No regional denominator for {region.regional_intensity!.missing_sectors.map((s) => titleCase(s)).join(", ")} — excluded from intensity, not counted as zero.
          </div>
        )}
      </Block>

      <Block title="Network & sectors" right={<button className="ghost" style={{ padding: "1px 6px", fontSize: 10 }} onClick={() => p.onTab("Effects")}>effects ›</button>}>
        <KV k="Installed generation" v={`${region.installed_mw.toLocaleString("en-GB")} MW`} />
        <KV k="Tracked substations (≥220 kV)" v={region.tracked_substations} />
        <KV k="Tracked HV lines (≥330 kV)" v={region.tracked_transmission_lines} />
        <KV k="Transmission burden" v={fmtNum(region.effects.transmission_burden, 2)} hint="weighted burden of recently-disrupted transmission facilities (not % offline)" />
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
    label: "Contribution to National Exposure",
    desc: "This region's share of the NATIONAL disrupted-capacity exposure, evidence- and recency-weighted. A large region can rank high without being intensely disrupted itself. NOT measured capacity loss.",
    value: (code, c) => c.bundle.regional.regions[code]?.esdi[c.step] ?? 0,
    fmt: (v) => fmtNum(v, 1),
  },
  {
    key: "intensity",
    label: "Regional Disruption Intensity",
    desc: "Disruption relative to the REGION's OWN tracked base (generation MW + transmission burden). Refining/oil-logistics have no regional denominator and are excluded, shown as 'missing' — never counted as zero. Current.",
    value: (code, c) => c.bundle.snapshot.regions[code]?.regional_intensity?.composite ?? 0,
    fmt: (v) => fmtNum(v, 1),
    current: true,
  },
  {
    key: "unresolved",
    label: "Unresolved disruptions",
    desc: "Facilities currently impaired with no credible restoration reported. Reflects the present, not the timeline position.",
    value: (code, c) => c.bundle.snapshot.regions[code]?.unresolved_count ?? 0,
    current: true,
  },
  {
    key: "backlog",
    label: "Reconstitution backlog (days)",
    desc: "Summed remaining reconstitution time across the region's unresolved facilities (horizon minus elapsed). Modelled/estimated where no observed timing exists. Current.",
    value: (code, c) => c.bundle.snapshot.regions[code]?.reconstitution_backlog_days ?? 0,
    current: true,
  },
  {
    key: "recent",
    label: "Recent activity (90 days)",
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
    label: "Data coverage / confidence",
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
  const [view, setView] = useState<"ranked" | "burden">("ranked");
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

  if (view === "burden") return <ActiveBurdenTable p={p} onBack={() => setView("ranked")} />;

  return (
    <div className="tab-body">
      <div className="ranking-picker">
        <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 6 }}>
          <button className="ghost" aria-pressed={true}>Ranked</button>
          <button className="ghost" onClick={() => setView("burden")} title="Where is the unresolved burden greatest right now?">Active burden ›</button>
        </div>
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
            <div className="rank-name">
              {x.r.name}
              {x.r.analytic_scope !== "aoi" && <span className="tag context" style={{ marginLeft: 6 }}>occupied</span>}
            </div>
            <div className="rank-sub">
              {x.r.district} · {x.r.incident_count} events
              {metricKey === "intensity" && (x.r.regional_intensity?.missing_sectors.length ?? 0) > 0 && (
                <span style={{ color: "var(--amber)" }}> · no regional base: {x.r.regional_intensity!.missing_sectors.map((s) => titleCase(s)).join(", ")}</span>
              )}
            </div>
            <div className="rank-bar"><i style={{ width: `${(x.value / max) * 100}%`, background: metricKey === "confidence" ? "var(--accent)" : severityColor(metricKey === "exposure" || metricKey === "intensity" ? x.value : Math.min(12, x.value)) }} /></div>
          </span>
          <span className="rank-val">{(metric.fmt ?? ((v) => String(Math.round(v))))(x.value)}</span>
        </div>
      ))}
      <Note>Rankings only ever include regions with recorded disruption. Undamaged infrastructure is never ranked, and no ranking represents target value. "Contribution to National Exposure" and "Regional Intensity" answer different questions — a big region can top the first without topping the second.</Note>
    </div>
  );
}

/** Active Burden: a transparent sortable table (columns, not a composite) answering
 *  "where is the unresolved energy-disruption burden greatest right now?". */
function ActiveBurdenTable({ p, onBack }: { p: TabProps; onBack: () => void }) {
  type Col = { key: string; label: string; get: (r: RegionSnapshot) => number };
  const cols: Col[] = [
    { key: "unresolved_count", label: "Unresolved", get: (r) => r.unresolved_count },
    { key: "oldest_unresolved_days", label: "Oldest (d)", get: (r) => r.oldest_unresolved_days },
    { key: "median_unresolved_age_days", label: "Median age (d)", get: (r) => r.median_unresolved_age_days ?? 0 },
    { key: "reconstitution_backlog_days", label: "Backlog (d)", get: (r) => r.reconstitution_backlog_days },
  ];
  const [sortKey, setSortKey] = useState("unresolved_count");
  const active = cols.find((c) => c.key === sortKey)!;
  const rows = Object.values(p.bundle.snapshot.regions)
    .filter((r) => r.unresolved_count > 0)
    .sort((a, b) => active.get(b) - active.get(a))
    .slice(0, 40);

  return (
    <div className="tab-body">
      <div className="ranking-picker">
        <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 6 }}>
          <button className="ghost" onClick={onBack}>‹ Ranked</button>
          <button className="ghost" aria-pressed={true}>Active burden</button>
        </div>
        <div className="ranking-desc">
          Unresolved-disruption burden, by region, decomposed into transparent columns.
          Click a column to sort; click a region to select it. No hidden composite.
        </div>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table className="burden-table">
          <thead>
            <tr>
              <th style={{ textAlign: "left" }}>Region</th>
              {cols.map((c) => (
                <th key={c.key} onClick={() => setSortKey(c.key)}
                    aria-sort={sortKey === c.key ? "descending" : undefined}>
                  {c.label}{sortKey === c.key ? " ▼" : ""}
                </th>
              ))}
              <th style={{ textAlign: "left" }}>Sectors</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.code} onClick={() => p.onSelect(r.code)} className={r.code === p.selected ? "sel" : ""}>
                <td style={{ textAlign: "left" }}>
                  {r.name}{r.analytic_scope !== "aoi" && <span className="tag context" style={{ marginLeft: 5 }}>UA</span>}
                </td>
                {cols.map((c) => <td key={c.key} className="num">{c.get(r) || "—"}</td>)}
                <td style={{ textAlign: "left", color: "var(--text-dim)", fontSize: 10 }}>
                  {r.affected_sectors.map((s) => titleCase(s).replace("Electric ", "")).join(", ") || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <div className="empty">No unresolved disruptions currently recorded.</div>}
      <Note>Backlog = summed remaining reconstitution time (horizon − elapsed) across unresolved facilities, modelled/estimated where no observed timing exists. A transparent burden view, not a score.</Note>
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

  const isOccupiedRegion = (code: string | null) =>
    code ? p.bundle.snapshot.regions[code]?.analytic_scope !== "aoi" : false;

  return (
    <div className="tab-body">
      <div className="section-head" style={{ position: "static" }}>
        <h2 style={{ fontSize: 12 }}>Top 10 most recent</h2>
        <div style={{ display: "flex", gap: 5 }}>
          <button className="ghost" aria-pressed={!p.selected} onClick={() => p.onSelect(null)}>National</button>
          {p.selected && (
            <button className="ghost" aria-pressed={true}>
              {p.bundle.snapshot.regions[p.selected]?.name ?? "Region"}
            </button>
          )}
        </div>
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
              {isOccupiedRegion(i.region_code) && <span className="tag context">Ukraine · occupied</span>}
              {i.conflicting_reports && <span className="tag conflict">sources conflict</span>}
              {live && live.event_count > 1 && (
                <span className="tag repeat" title={`This facility has ${live.event_count} recorded disruption events — a repeatedly targeted site, not a one-off.`}>
                  struck ×{live.event_count}
                </span>
              )}
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
        <Tile label="Currently reconstituted" value={rs.resolved_count} />
        <Tile
          label="Observed-restoration evidence"
          value={rs.observed_restoration_episodes}
          unit="episodes" kind="observed"
        />
        <Tile
          label="Reconstitution / partial-restart episodes"
          value={`${rs.full_reconstitution_episodes} / ${rs.partial_restart_episodes}`}
          small
        />
      </div>

      <Note warn={rs.observed_restoration_episodes < (rs.min_sector_median_episodes ?? 3)}>
        National observed-restoration evidence rests on{" "}
        <b>{rs.observed_restoration_episodes} independent episodes</b> (episodes, not records: a
        multi-day strike counts once). No single "typical" repair time is claimed — a ~2-day
        oil-terminal restart and a ~205-day gas-plant repair are different repair problems, so a
        median is shown for an infrastructure class only once that class has ≥{" "}
        {rs.min_sector_median_episodes ?? 3} of its own observed episodes (see <i>By
        infrastructure class</i> below).
      </Note>

      {rs.median_observed_restoration_days != null && (
        <Note>
          <b>Mixed-infrastructure reference only:</b> the pooled median across all{" "}
          {rs.observed_restoration_episodes} episodes is {rs.median_observed_restoration_days}{" "}
          days. It mixes facility classes and blends first-restart with full-reconstitution
          evidence, so it is deliberately <i>not</i> used as a headline figure or a per-sector
          norm.
        </Note>
      )}
      {rs.observed_restoration_values.length > 0 && (
        <div style={{ padding: "0 14px 8px", fontSize: 11, color: "var(--text-dim)" }}>
          Observed restoration durations (days), by episode:{" "}
          <span className="num" style={{ color: "var(--green)" }}>{rs.observed_restoration_values.join(", ")}</span>
        </div>
      )}

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

      {rs.evidence_family_counts && Object.keys(rs.evidence_family_counts).length > 0 && (
        <Block title="Evidence families">
          {([
            ["facility_reconstitution", "Facility reconstitution", "var(--green)", "the damaged equipment itself returned to service"],
            ["unit_restart", "Unit restart", "var(--text)", "a damaged unit resumed, full repair not always confirmed"],
            ["service_restoration", "Service restoration", "var(--amber)", "supply re-energised, often around a still-damaged node"],
            ["flow_rerouting", "Flow rerouting", "var(--amber)", "throughput restored by rerouting, node not repaired"],
            ["estimate", "Repair estimate", "var(--text-dim)", "a sourced repair-time projection, no restart yet"],
          ] as const).filter(([k]) => (rs.evidence_family_counts?.[k] ?? 0) > 0).map(([k, label, color, hint]) => (
            <div key={k} className="kv" title={hint} style={{ alignItems: "center" }}>
              <span className="k" style={{ flex: 1, color }}>{label}</span>
              <span className="v"><span className="num" style={{ color }}>{rs.evidence_family_counts?.[k]}</span></span>
            </div>
          ))}
          <div style={{ fontSize: 10.5, color: "var(--text-faint)", padding: "4px 14px 0", lineHeight: 1.45 }}>
            Only <b style={{ color: "var(--green)" }}>facility reconstitution</b> means the struck
            equipment returned. Service restoration and flow rerouting bring supply back around a
            node that may still be destroyed — never read as a repair.
          </div>
        </Block>
      )}

      <Block title="By infrastructure class">
        {Object.keys(rs.by_sector).length === 0 && <div className="empty">No disrupted facilities to summarise.</div>}
        {Object.entries(rs.by_sector).map(([sector, s]) => (
          <div key={sector} className="kv" style={{ alignItems: "center" }}>
            <span className="k" style={{ flex: 1 }}>
              {titleCase(sector)}
              <span style={{ color: "var(--text-faint)", fontSize: 10 }}> · {s.unresolved}/{s.disrupted_facilities} unresolved</span>
            </span>
            <span className="v">
              {s.median_observed_restoration_days != null
                ? <><span style={{ color: "var(--green)" }} title="Median of this class's own observed episodes">{s.median_observed_restoration_days}d median</span> <span className="tile-n">n={s.observed_restoration_episodes}</span></>
                : s.observed_restoration_episodes > 0
                  ? <span className="tile-n" title={`Below the ${rs.min_sector_median_episodes ?? 3}-episode gate for a class median`}>
                      {(s.observed_restoration_values ?? []).join(", ")}d · n={s.observed_restoration_episodes} (below median gate)
                    </span>
                  : (s.partial_restart_episodes ?? 0) > 0
                    ? <span className="tile-n" style={{ color: "var(--amber)" }} title="Partial restarts observed, but no full-restoration duration">
                        {s.partial_restart_episodes} partial restart(s), no full-restoration duration
                      </span>
                    : <span style={{ color: "var(--text-faint)", fontStyle: "italic", fontSize: 11 }}>no observed data</span>}
            </span>
          </div>
        ))}
        <div style={{ fontSize: 10.5, color: "var(--text-faint)", padding: "4px 14px 0" }}>
          A class shows a median only at ≥{rs.min_sector_median_episodes ?? 3} of its own
          observed episodes; below that, the individual durations are listed rather than a
          median that a small sample cannot support.
        </div>
      </Block>

      <Block title="Facilities with recovery evidence">
        <div style={{ margin: "0 -14px" }}>
          {p.bundle.snapshot.live_disruptions
            .filter((d) => d.recovery.scoring_evidence_kind !== "modelled" ||
              d.recovery.resolved || d.recovery.recovery_status === "partial_restart" ||
              d.recovery.estimate_days != null)
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

const EFFECT_LABEL: Record<string, string> = {
  production_halt: "Production halt", throughput_reduction: "Throughput reduction",
  power_outage: "Power outage", customers_affected: "Customers affected",
  heating_disruption: "Heating disruption", fuel_shortage: "Fuel shortage",
  export_interruption: "Export interruption", repair_cost: "Repair cost",
  war_effort_macro: "Strategic / macro effect",
};

/** One source-backed observed consequence (§25-28). The evidence tag governs its authority;
 *  the figure is shown only when a source gave one, never inferred. */
export function EffectItem({ e }: { e: import("../types").StrategicEffect }) {
  const n = e.value_numeric;
  const val = n != null
    ? `${Number.isInteger(n) ? n.toLocaleString("en-GB") : n}${e.value_unit ? " " + e.value_unit : ""}`
    : null;
  const cost = e.effect_type === "repair_cost" && e.value_numeric != null
    ? `${e.currency ?? ""} ${fmtNum(e.value_numeric, 0)}${e.cost_year ? ` (${e.cost_year})` : ""}`.trim()
    : null;
  return (
    <div className="event" style={{ borderLeft: "2px solid var(--line)", paddingLeft: 8 }}>
      <div className="event-top" style={{ gap: 6, flexWrap: "wrap" }}>
        <span className="event-name">{EFFECT_LABEL[e.effect_type] ?? titleCase(e.effect_type)}</span>
        <EvidenceChip kind={e.evidence_kind === "observed" ? "observed" : e.evidence_kind === "estimated" ? "estimated" : "modelled"} />
        {(cost ?? val) && <span className="num" style={{ color: "var(--text)", fontSize: 11 }}>{cost ?? val}</span>}
        {e.as_of_date && <span className="num" style={{ color: "var(--text-faint)", fontSize: 10 }}>{fmtDate(e.as_of_date)}</span>}
      </div>
      {e.value_text && <div style={{ fontSize: 11, color: "var(--text-dim)", lineHeight: 1.5, marginTop: 2 }}>{e.value_text}</div>}
      {e.source_url && (
        <div className="src-list" style={{ marginTop: 3, display: "flex", gap: 8, alignItems: "center" }}>
          <a href={e.source_url} target="_blank" rel="noreferrer noopener">↗ {hostname(e.source_url)}</a>
          {e.source_quality && (
            <span style={{ fontSize: 9.5, color: "var(--text-faint)", letterSpacing: 0.2 }}
                  title="Source-quality tier (triage/provenance, not a confidence score)">
              {e.source_quality.replace(/_/g, " ")}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/** Layer badge: the three-layer distinction the brief insists on. A proxy must never
 *  carry the same visual authority as a measured observation. */
function LayerBadge({ layer }: { layer: "observed" | "structural" | "proxy" }) {
  const cfg = {
    observed: { c: "var(--green)", t: "Observed" },
    structural: { c: "var(--accent)", t: "Structural context" },
    proxy: { c: "var(--amber)", t: "Analytic proxy" },
  }[layer];
  return <span className={`layer-badge ${layer}`} style={{ color: cfg.c }}>{cfg.t}</span>;
}

export function EffectsTab(p: TabProps) {
  const { bundle, selected, step } = p;
  const region = selected ? bundle.snapshot.regions[selected] : null;
  const heating = bundle.snapshot.heating_season;
  const sectorNow = (s: string) => (region ? region.sectors[s] ?? 0 : bundle.national.sectors[s]?.[step] ?? 0);
  const ad = bundle.snapshot.assessed_degradation;
  const econ = bundle.snapshot.economic_context;

  return (
    <div className="tab-body">
      <div className="section-head" style={{ position: "static" }}>
        <h2 style={{ fontSize: 12 }}>{region ? region.name : "National"} — effects</h2>
        {!region && <span className="eyebrow">select a region for detail</span>}
      </div>

      <div className="concept-key" style={{ gap: 8 }}>
        <LayerBadge layer="observed" /><LayerBadge layer="structural" /><LayerBadge layer="proxy" />
        <span style={{ fontSize: 9.5 }}>— a proxy is never shown with the authority of a measurement.</span>
      </div>

      {/* LAYER 1: OBSERVED */}
      <Block title={<><LayerBadge layer="observed" /> Observed effect</>}>
        <KV k="Quantified capacity effect (events)" v={`${ad.quantified_incident_count} of ${ad.total_incident_count}`} hint="events whose sources quantified the capacity lost" />
        <KV k="Quantified refining lost" v={ad.quantified_mtpa > 0 ? `${fmtNum(ad.quantified_mtpa, 1)} MTPA` : "—"} />
        {region && (
          <KV k="Currently impaired facilities" v={region.unresolved_count} hint="a directly recorded, unresolved disruption count" />
        )}
        <div style={{ fontSize: 10, color: "var(--text-faint)", marginTop: 4, lineHeight: 1.45 }}>
          Directly reported consequences only. Open reporting rarely quantifies lost output, so this layer is deliberately sparse — it is not padded with model output.
        </div>
      </Block>

      {/* LAYER 1b: SOURCE-BACKED OBSERVED EFFECTS (§25-28) */}
      {(() => {
        const se = bundle.snapshot.strategic_effects;
        if (!se) return null;
        const national = se.national ?? [];
        // Per-incident effects for the selected region's incidents.
        const regionEffects = region
          ? bundle.incidents
              .filter((i) => i.region_code === region.code)
              .flatMap((i) => (se.by_incident[i.incident_id] ?? []).map((e) => ({ e, i })))
          : [];
        if (national.length === 0 && regionEffects.length === 0) return null;
        return (
          <Block title={<><LayerBadge layer="observed" /> {region ? "Observed effects in region" : "Observed strategic & macro effects"}</>}>
            <div style={{ margin: "0 -6px" }}>
              {region
                ? regionEffects.map(({ e, i }, n) => (
                    <div key={n}>
                      <div style={{ fontSize: 10, color: "var(--text-faint)", padding: "2px 8px 0" }}>{i.asset_name}</div>
                      <EffectItem e={e} />
                    </div>
                  ))
                : national.map((e, n) => <EffectItem key={n} e={e} />)}
            </div>
            <div style={{ fontSize: 10, color: "var(--text-faint)", marginTop: 6, lineHeight: 1.45 }}>
              Each effect is a single sourced consequence carrying its own evidence tag. Macro
              effects are strategic aggregates only. A civilian figure appears only when a source
              states people or customers were actually affected — never a region's population.
            </div>
          </Block>
        );
      })()}

      {/* LAYER 2: STRUCTURAL CONTEXT */}
      <Block title={<><LayerBadge layer="structural" /> Structural exposure / context</>}>
        {region ? (
          <>
            <KV k="Region population" v={region.population_millions != null ? `${fmtNum(region.population_millions, 1)} m` : "—"} hint="population POTENTIALLY exposed — not population actually affected" />
            <KV k="Installed generation" v={`${region.installed_mw.toLocaleString("en-GB")} MW`} />
            <KV k="Tracked substations / HV lines" v={`${region.tracked_substations} / ${region.tracked_transmission_lines}`} />
            <KV k="Heating season" v={heating ? "active (Oct–Apr)" : "out of season"} />
          </>
        ) : (
          <>
            <KV k="Tracked refining base" v={`${fmtNum(bundle.snapshot.denominators.refining_mtpa, 0)} MTPA`} />
            <KV k="Tracked generation base" v={`${bundle.snapshot.denominators.electric_generation_mw.toLocaleString("en-GB")} MW`} />
            <KV k="Heating season" v={heating ? "active (Oct–Apr)" : "out of season"} />
          </>
        )}
        <div style={{ fontSize: 10, color: "var(--text-faint)", marginTop: 4, lineHeight: 1.45 }}>
          Factors that could make disruption consequential. Population is potentially exposed, never a claim that people were affected.
        </div>
      </Block>

      {/* LAYER 3: ANALYTIC PROXY */}
      <Block title={<><LayerBadge layer="proxy" /> Analytic proxy — sector exposure</>}>
        <div className="bars">
          {Object.entries(bundle.taxonomy.sectors).map(([k, label]) => {
            const covered = bundle.snapshot.sectors_covered.includes(k);
            return covered
              ? <Bar key={k} label={label} value={sectorNow(k)} max={100} color="var(--amber)" suffix="" />
              : (
                <div className="bar-row" key={k}>
                  <span style={{ color: "var(--text-faint)" }}>{label}</span>
                  <span style={{ gridColumn: "2 / span 2", color: "var(--text-faint)", fontStyle: "italic", fontSize: 10.5 }}>no capacity base — not scored</span>
                </div>
              );
          })}
        </div>
        <div style={{ fontSize: 10, color: "var(--text-faint)", marginTop: 6, lineHeight: 1.45 }}>
          Model-derived exposure, NOT a measured effect. Refining and logistics exposure proxy the war-sustainment channel (fuel supply, export revenue) — strategic only, never tactical unit-supply inference.
        </div>
      </Block>

      {/* Observed external economic context (CREA), distinct from the proxy */}
      {econ && !region && (
        <Block title={<><LayerBadge layer="observed" /> Observed economic context (CREA)</>}>
          <EconContext econ={econ} />
        </Block>
      )}

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

function EconContext({ econ }: { econ: NonNullable<Bundle["snapshot"]["economic_context"]> }) {
  const series = econ.metrics["total_fossil_export_revenue"] ?? [];
  const max = Math.max(1, ...series.map((x) => x.value ?? 0));
  return (
    <>
      <div style={{ fontSize: 10.5, color: "var(--text-dim)", marginBottom: 6, lineHeight: 1.5 }}>
        Russian total fossil-fuel export revenue (EUR mn/day), monthly, from CREA. An
        observed external indicator — <strong>not</strong> attributed to strikes.
      </div>
      <div className="bars">
        {series.map((s) => (
          <div className="bar-row" key={s.reporting_month}>
            <span style={{ color: "var(--text-dim)" }}>{s.reporting_month}</span>
            <span className="bar-track"><i style={{ width: `${((s.value ?? 0) / max) * 100}%`, background: "var(--accent-dim)" }} /></span>
            <span className="bar-num">
              <a href={s.source_url ?? "#"} target="_blank" rel="noreferrer noopener" style={{ color: "var(--text-dim)" }}>{s.value}</a>
            </span>
          </div>
        ))}
      </div>
      <div style={{ fontSize: 10, color: "var(--text-faint)", marginTop: 6, lineHeight: 1.45 }}>{econ.caveat}</div>
    </>
  );
}

// ============================================================ COSTS

export function CostsTab(p: TabProps) {
  const { bundle, selected } = p;
  const rs = bundle.snapshot.recovery_stats;
  const region = selected ? bundle.snapshot.regions[selected] : null;

  // Reconstitution burden aggregated without inventing a single dollar figure.
  const regionList = Object.values(bundle.snapshot.regions);
  const nationalBacklog = regionList.reduce((a, r) => a + (r.reconstitution_backlog_days || 0), 0);
  const backlogSource = region ? region.reconstitution_backlog_days : nationalBacklog;
  const unresolved = region ? region.unresolved_count : rs.unresolved_count;
  const withCost = bundle.incidents.filter(
    (i) => i.repair_cost_reported_usd_m != null || i.repair_cost_estimate_low_usd_m != null,
  );
  return (
    <div className="tab-body">
      <div className="section-head" style={{ position: "static" }}>
        <h2 style={{ fontSize: 12 }}>{region ? region.name : "National"} — costs &amp; reconstitution</h2>
        <span className="eyebrow">repair burden</span>
      </div>

      <div className="tiles">
        <Tile label="Facilities awaiting reconstitution" value={unresolved} />
        <Tile label="Reconstitution backlog (days)" value={backlogSource} small />
        <Tile label="Median impairment age (days)" value={rs.median_impairment_age_days ?? "—"} small />
        <Tile label="Full reconstitutions observed" value={rs.full_reconstitution_episodes} small />
      </div>

      <Block title="Reconstitution burden — the non-monetary cost">
        <div style={{ fontSize: 10.5, color: "var(--text-dim)", marginBottom: 8, lineHeight: 1.5 }}>
          Where repair-cost figures are absent, the recoverable cost signal is the
          <em> reconstitution burden</em>: how many facilities remain impaired and how long
          they have stayed that way. This is directly observed, not modelled or priced.
        </div>
        <KV k="Facilities still impaired" v={unresolved} hint="open, unresolved disruptions" />
        <KV k="Summed remaining reconstitution time" v={`${backlogSource} d`} hint="sum of evidence-graded remaining reconstitution horizons across open facilities" />
        <KV k="Partial restarts (not yet full)" v={rs.partial_restart_episodes} hint="operations resumed but reconstitution incomplete" />
        <KV k="Observed full reconstitutions" v={rs.full_reconstitution_episodes} />
      </Block>

      <Note warn>
        Monetary repair-cost and economic-consequence figures are populated only from public
        sources, and almost none exist today, so most dollar values are deliberately absent.
        Reported, externally-estimated and modelled costs are kept structurally distinct and
        none are invented. The reconstitution burden above stands in as the defensible,
        source-grounded cost measure.
      </Note>

      <div className="tiles">
        <Tile label="Incidents with a reported repair cost" value={withCost.filter((i) => i.repair_cost_reported_usd_m != null).length} small />
        <Tile label="Incidents with a cost estimate" value={withCost.filter((i) => i.repair_cost_estimate_low_usd_m != null).length} small />
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

/** Evidence coverage heatmap: for each sector, how much evidence of each kind exists.
 *  The point is to separate "low disruption" (few events, but we would see them) from
 *  "little data" (a sector we simply have not populated) — a blank cell is not a zero. */
function EvidenceMatrix({ detail, sectors }: { detail: CoverageDetail; sectors: Record<string, string> }) {
  const matrix = detail.evidence_matrix ?? {};
  const cols: { key: "events" | "recovery" | "cost"; label: string }[] = [
    { key: "events", label: "Events" },
    { key: "recovery", label: "Recovery" },
    { key: "cost", label: "Cost" },
  ];
  const rows = Object.keys(sectors).filter((s) => matrix[s]);
  // Per-column max so intensity is comparable within a column, not across kinds.
  const colMax = (k: "events" | "recovery" | "cost") => Math.max(1, ...rows.map((s) => matrix[s]?.[k] ?? 0));
  const cell = (n: number, max: number) => {
    if (n === 0) return { background: "var(--line-soft)", color: "var(--text-faint)" };
    const t = 0.18 + 0.82 * (n / max);
    return { background: `color-mix(in srgb, var(--accent) ${Math.round(t * 100)}%, transparent)`, color: t > 0.55 ? "#04121f" : "var(--text)" };
  };
  return (
    <Block title="Evidence coverage matrix">
      <div style={{ fontSize: 10.5, color: "var(--text-dim)", margin: "0 14px 8px", lineHeight: 1.5 }}>
        How much evidence of each kind exists per sector. A faint cell means <em>little data
        here</em>, which is not the same as <em>low disruption</em> — read it as coverage, not effect.
      </div>
      <div className="ev-matrix" style={{ padding: "0 14px 4px" }}>
        <div className="ev-row ev-head">
          <span className="ev-sector" />
          {cols.map((c) => <span key={c.key} className="ev-cell-h">{c.label}</span>)}
        </div>
        {rows.map((s) => (
          <div className="ev-row" key={s}>
            <span className="ev-sector">{sectors[s]}</span>
            {cols.map((c) => {
              const n = matrix[s]?.[c.key] ?? 0;
              return <span key={c.key} className="ev-cell" style={cell(n, colMax(c.key))}>{n}</span>;
            })}
          </div>
        ))}
      </div>
    </Block>
  );
}

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

      <EvidenceMatrix detail={detail} sectors={bundle.taxonomy.sectors} />

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
