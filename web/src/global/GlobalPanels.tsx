import { useEffect, useMemo, useState } from "react";
import {
  ENVIRONMENT_LABEL, LANE_STATE_LABEL, LANE_WINDOW_LABEL, labelFor, loadDataQuality, loadRecentEvidence,
  type DataQuality, type RecentEvidence, type RecentEpisode,
} from "./manifest";
import { navigate } from "./router";
import { daysBetween, fmtDate } from "../data";

/** Recent evidence and Data Quality on the global home (iteration 18). */

function fmtEpisodeDate(ep: RecentEpisode): string {
  if (ep.date_precision === "month") {
    return new Date(`${ep.first_date}T00:00:00Z`).toLocaleDateString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" });
  }
  return ep.first_date === ep.last_date ? fmtDate(ep.first_date) : `${fmtDate(ep.first_date)} – ${fmtDate(ep.last_date)}`;
}

/** Newest first, with filters. There is deliberately no sort control: a severity or size order
 *  would turn this into a board of the worst hits. */
export function RecentEvidencePanel() {
  const [data, setData] = useState<RecentEvidence | null>(null);
  const [failed, setFailed] = useState(false);
  const [country, setCountry] = useState("all");
  const [cls, setCls] = useState("all");
  useEffect(() => {
    let live = true;
    loadRecentEvidence().then((d) => { if (live) setData(d); }).catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, []);
  const countries = useMemo(() => [...new Map((data?.episodes ?? []).map((e) => [e.system_id, e.country])).entries()]
    .sort((a, b) => a[1].localeCompare(b[1])), [data]);
  const classes = useMemo(() => [...new Set((data?.episodes ?? []).flatMap((e) => e.classes))].sort(), [data]);
  const shown = (data?.episodes ?? []).filter((e) => (country === "all" || e.system_id === country)
    && (cls === "all" || e.classes.includes(cls)));
  return (
    <section className="panel global-note recent-evidence" aria-label="Recent evidence">
      <h2 className="eyebrow">Recent evidence in the monitored countries</h2>
      {failed && <p className="small warn-text" role="alert">The recent list could not be loaded. Each country's own page still lists its record.</p>}
      {data && (
        <>
          <p className="small dim">{data.scope} Newest first. {data.note}</p>
          <div className="map-control-row">
            <label className="small">Country{" "}
              <select aria-label="Filter recent evidence by country" value={country} onChange={(e) => setCountry(e.target.value)}>
                <option value="all">all five</option>
                {countries.map(([id, n]) => <option key={id} value={id}>{n}</option>)}
              </select>
            </label>
            <label className="small">Class{" "}
              <select aria-label="Filter recent evidence by class" value={cls} onChange={(e) => setCls(e.target.value)}>
                <option value="all">all classes</option>
                {classes.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
          </div>
          <ol className="feed">
            {shown.map((ep) => (
              <li key={`${ep.system_id}:${ep.episode_id}`} className="feed-item">
                <div className="event-head">
                  <span className="mono small">{fmtEpisodeDate(ep)}</span>
                  <button className="linklike small" onClick={() => navigate(ep.system_id)}>{ep.country}</button>
                  <span className="small dim">{ep.classes.join(", ")} · {ep.causes.join(", ")}</span>
                </div>
                {ep.episode_name && <div className="small"><strong>{ep.episode_name}</strong> <span className="dim">({ep.records} records, one episode)</span></div>}
                <ul className="lane-list small">
                  {ep.members.map((m, i) => (
                    <li key={i}>
                      <span className="dim">{m.region}: </span>
                      {m.withheld ? <span className="dim">Effect and facility status are not shown here while an attack campaign is active; see the country page.</span> : m.effect ?? "Effect not stated."}
                    </li>
                  ))}
                  {ep.more_members > 0 && <li className="dim">and {ep.more_members} more on the country page</li>}
                </ul>
              </li>
            ))}
            {shown.length === 0 && <li className="small dim">Nothing in the recent list matches these filters.</li>}
          </ol>
        </>
      )}
    </section>
  );
}

const LANE_ORDER = ["universe_searched", "current_through_latest_release", "declared_query_set_run",
                    "partially_searched", "blocked_by_source", "not_started"];

export function laneChips(states: Record<string, number>): string {
  return LANE_ORDER.filter((k) => states[k]).map((k) => `${states[k]} ${labelFor(LANE_STATE_LABEL, k).toLowerCase()}`).join(" · ");
}

/** Process and vintage, side by side in a fixed order. No disruption count appears here. */
export function DataQualityPanel() {
  const [data, setData] = useState<DataQuality | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let live = true;
    loadDataQuality().then((d) => { if (live) setData(d); }).catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, []);
  const today = new Date().toISOString().slice(0, 10);
  return (
    <section className="panel global-note data-quality-panel" aria-label="Data quality">
      <h2 className="eyebrow">Data quality</h2>
      {failed && <p className="small warn-text" role="alert">The data-quality summary could not be loaded.</p>}
      {data && (
        <>
          <p className="small dim">{data.note}</p>
          <p className="small">
            <strong>Global energy context:</strong> {data.context_vintage.comparison_year} figures,{" "}
            {data.context_vintage.source}, release of {fmtDate(data.context_vintage.release)}, retrieved{" "}
            {fmtDate(data.context_vintage.retrieved)}; {data.context_vintage.countries} countries and territories.{" "}
            <span className="dim">{data.context_vintage.note} Updated {data.context_vintage.update_cadence}.</span>
          </p>
          {data.systems.map((s) => {
            const late = s.sources_checked.filter((x) => x.last_checked && x.stale_after_days != null
              && daysBetween(x.last_checked, today) > x.stale_after_days);
            const blocked = s.lanes.filter((l) => l.state === "blocked_by_source");
            const waiting = s.lanes.filter((l) => l.source_window === "publisher_not_yet_released");
            const partial = s.lanes.filter((l) => l.state === "partially_searched" || l.state === "not_started");
            return (
              <details key={s.system_id} className="dq-system">
                <summary>
                  <strong>{s.name}</strong>{" "}
                  <span className="small dim">{laneChips(s.lane_states)}</span>
                </summary>
                <p className="small">Reporting environment: {labelFor(ENVIRONMENT_LABEL, s.reporting_environment)}.
                  Source families cited: {Object.values(s.source_families).join(", ") || "none"}.
                  Newest systematic pass {fmtDate(s.last_systematic_pass)}; first {fmtDate(s.first_systematic_pass)}.
                  {" "}{late.length ? `${late.length} listed sources are past their re-check limit.` : "No listed source is past its re-check limit."}</p>
                {[["Blocked by the source", blocked], ["Publisher has not yet released the rest", waiting], ["Partly searched or not started", partial]].map(([title, ls]) => (
                  (ls as typeof blocked).length > 0 && (
                    <div key={title as string}>
                      <div className="eyebrow">{title as string}</div>
                      <ul className="lane-list small">
                        {(ls as typeof blocked).map((l) => <li key={l.lane}><span className="mono">{l.lane}</span>: {l.limitation}</li>)}
                      </ul>
                    </div>
                  )
                ))}
              </details>
            );
          })}
          <details className="dq-system">
            <summary className="small">Recovery evidence by infrastructure class, five countries together</summary>
            <p className="small dim">{data.recovery_by_class.note}</p>
            <table className="sector-table">
              <thead><tr><th>Class</th><th>Reported as</th><th>Cases</th><th>Days to report</th></tr></thead>
              <tbody>
                {data.recovery_by_class.rows.map((r) => (
                  <tr key={`${r.class}-${r.kind}`}>
                    <td className="small">{r.class_label}</td>
                    <td className="small dim">{r.kind.replace(/_/g, " ")}</td>
                    <td className="mono small">{r.n}</td>
                    <td className="mono small">{r.median_days != null ? `median ${r.median_days}; ${r.range_days?.[0]}–${r.range_days?.[1]}`
                      : r.range_days ? `${r.range_days[0]}–${r.range_days[1]}` : r.cases_days?.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </>
      )}
    </section>
  );
}

export { LANE_WINDOW_LABEL };
