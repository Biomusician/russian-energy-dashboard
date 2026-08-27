import { useMemo } from "react";
import type { Bundle, Incident, RegionSnapshot } from "../types";
import { fmtDate, fmtNum, titleCase } from "../data";
import { CAUSE_COLOR, severityColor } from "../palette";

/** Right rail: the selected region's dossier, or the national picture when nothing
 *  is selected. Effect categories the MVP cannot derive are rendered explicitly as
 *  "not modelled" with the reason, rather than omitted — a missing row reads as
 *  "nothing happening", which is a different and wrong claim. */
export default function Dossier({
  bundle, step, selected, currentDate, incidentsByRegion, visibleIncidents, onSelect,
}: {
  bundle: Bundle;
  step: number;
  selected: string | null;
  currentDate: string;
  incidentsByRegion: Map<string, Incident[]>;
  visibleIncidents: Incident[];
  onSelect: (code: string | null) => void;
}) {
  const region = selected ? bundle.snapshot.regions[selected] : null;
  const regionIncidents = useMemo(
    () => (selected ? incidentsByRegion.get(selected) ?? [] : []),
    [selected, incidentsByRegion],
  );

  if (!region) {
    return <NationalDossier bundle={bundle} step={step} visibleIncidents={visibleIncidents} onSelect={onSelect} incidentsByRegion={incidentsByRegion} />;
  }

  const esdiNow = bundle.regional.regions[region.code]?.esdi[step] ?? 0;

  return (
    <aside className="panel dossier">
      <div className="section-head">
        <div>
          <h2 style={{ fontSize: 13 }}>{region.name}</h2>
          <div className="eyebrow" style={{ marginTop: 3 }}>
            {region.district} · {region.country === "RU" ? "Russia" : "Belarus"}
          </div>
        </div>
        <button className="ghost" onClick={() => onSelect(null)}>close</button>
      </div>

      <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--line-soft)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div className="num" style={{ fontSize: 32, color: severityColor(esdiNow) }}>
            {fmtNum(esdiNow, 1)}
          </div>
          <div>
            <div className="eyebrow">Disruption exposure</div>
            <div style={{ fontSize: 11, color: "var(--text-dim)" }}>as at {fmtDate(currentDate)}</div>
          </div>
        </div>
        <div className="meter">
          <i style={{ width: `${Math.min(100, esdiNow * 4)}%`, background: severityColor(esdiNow) }} />
        </div>
      </div>

      <Block title="Recorded activity">
        <KV k="Events to date" v={regionIncidents.length} />
        <KV k="Facilities affected" v={region.struck_facility_count} />
        <KV k="Currently impaired (est.)" v={region.live_disruption_count} />
        <KV k="Installed generation" v={`${region.installed_mw.toLocaleString("en-GB")} MW`} />
      </Block>

      <Block title="Effects by category">
        <KV k="Generation margin" v={pct(region.effects.generation_margin)} hint="share of the region's own installed MW at impaired plants" />
        <KV k="Fuel production" v={pct(region.effects.fuel_production)} hint="share of national refining capacity impaired here" />
        <KV k="Logistics" v={fmtNum(region.effects.logistics, 2)} hint="weighted count of impaired oil-logistics nodes" />
        <KV
          k="Heating season exposure"
          v={bundle.snapshot.heating_season ? pct(region.effects.heating_season_exposure) : "out of season"}
          hint="thermal generation impaired during the Oct–Apr heating season"
        />
        <KV k="Repair burden" v={region.effects.repair_burden} hint="facilities with impairment still decaying" />
        <KV k="Recurrence" v={fmtNum(region.effects.recurrence, 2)} hint="mean recorded events per affected facility" />
        {Object.entries(bundle.snapshot.not_modelled).map(([key, reason]) => (
          <div className="kv" key={key} title={reason}>
            <span className="k">{titleCase(key)}</span>
            <span className="v null">not modelled</span>
          </div>
        ))}
      </Block>

      <div className="note warn">
        “Not modelled” means this MVP has no open data source for that category, so no
        figure is shown. It does not mean the effect is absent. Reasons are in the
        methodology panel.
      </div>

      <Block title={`Events (${regionIncidents.length})`}>
        <div style={{ margin: "0 -14px" }}>
          {regionIncidents.length === 0 && (
            <div className="empty">No events recorded in this region up to {fmtDate(currentDate)} under the current filters.</div>
          )}
          {[...regionIncidents]
            .sort((a, b) => b.date.localeCompare(a.date))
            .slice(0, 60)
            .map((i) => <EventRow key={i.incident_id} incident={i} />)}
        </div>
      </Block>
    </aside>
  );
}

function NationalDossier({
  bundle, step, visibleIncidents, onSelect, incidentsByRegion,
}: {
  bundle: Bundle;
  step: number;
  visibleIncidents: Incident[];
  onSelect: (code: string | null) => void;
  incidentsByRegion: Map<string, Incident[]>;
}) {
  const ranked = useMemo(() => {
    return Object.values(bundle.snapshot.regions)
      .map((r) => ({ r, value: bundle.regional.regions[r.code]?.esdi[step] ?? 0 }))
      .filter((x) => x.value > 0 || (incidentsByRegion.get(x.r.code)?.length ?? 0) > 0)
      .sort((a, b) => b.value - a.value)
      .slice(0, 14);
  }, [bundle, step, incidentsByRegion]);

  const recent = useMemo(
    () => [...visibleIncidents].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 25),
    [visibleIncidents],
  );

  return (
    <aside className="panel dossier">
      <div className="section-head">
        <h2 style={{ fontSize: 13 }}>National picture</h2>
        <span className="eyebrow">select a region</span>
      </div>

      <Block title="Most affected regions">
        {ranked.length === 0 && <div className="empty">No recorded disruption at this point in the timeline.</div>}
        {ranked.map(({ r, value }) => (
          <RegionRow key={r.code} region={r} value={value} count={incidentsByRegion.get(r.code)?.length ?? 0} onSelect={onSelect} />
        ))}
      </Block>

      <Block title={`Recent events (${visibleIncidents.length} total)`}>
        <div style={{ margin: "0 -14px" }}>
          {recent.map((i) => <EventRow key={i.incident_id} incident={i} showRegion regions={bundle.snapshot.regions} />)}
        </div>
      </Block>
    </aside>
  );
}

function RegionRow({
  region, value, count, onSelect,
}: {
  region: RegionSnapshot;
  value: number;
  count: number;
  onSelect: (c: string) => void;
}) {
  return (
    <div
      className="kv"
      style={{ cursor: "pointer", alignItems: "center" }}
      onClick={() => onSelect(region.code)}
    >
      <span className="k" style={{ flex: 1 }}>
        {region.name}
        <span style={{ color: "var(--text-faint)", fontSize: 10.5 }}> · {count} events</span>
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

function EventRow({
  incident, showRegion, regions,
}: {
  incident: Incident;
  showRegion?: boolean;
  regions?: Record<string, RegionSnapshot>;
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
        {showRegion && incident.region_code && regions?.[incident.region_code] && (
          <span className="tag">{regions[incident.region_code].name}</span>
        )}
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
      {incident.sources.length > 0 && (
        <div className="src-list">
          {incident.sources.slice(0, 3).map((s, n) => (
            <a key={n} href={s.url} target="_blank" rel="noreferrer noopener">
              ↗ {s.publisher || s.title || hostOf(s.url)}
            </a>
          ))}
        </div>
      )}
      {incident.sources.length === 0 && (
        <div style={{ fontSize: 10, color: "var(--text-faint)", marginTop: 4 }}>
          No direct citation captured — listed in source table without a per-event reference
        </div>
      )}
    </div>
  );
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ padding: "10px 14px 14px", borderBottom: "1px solid var(--line-soft)" }}>
      <div className="eyebrow" style={{ marginBottom: 6 }}>{title}</div>
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

function pct(value: number | null): string {
  return value === null ? "—" : `${fmtNum(value, 2)}%`;
}

function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url.slice(0, 40);
  }
}
