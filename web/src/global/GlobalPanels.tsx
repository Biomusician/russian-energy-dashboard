import { useEffect, useMemo, useState } from "react";
import {
  ENVIRONMENT_LABEL, LANE_STATE_LABEL, LANE_WINDOW_LABEL, labelFor, loadRecentEvidence,
  type DataQuality, type Manifest, type RecentEvidence, type RecentEpisode,
} from "./manifest";
import { navigate } from "./router";
import { prefetchOn } from "./prefetch";
import { daysBetween, fmtDate } from "../data";
import { readerText } from "./readerText";
import { collapseCovered, dated, placementOf, type FeedRow } from "./homeModel";
import { openGlossary } from "./GlobalNav";

/** Recent evidence and Data Quality on the global home (iteration 18; rewritten iteration 21). */

function fmtSpan(first: string, last: string, precision: string): string {
  // From the string itself: a browser's Date parser reads "2026-04" differently across engines.
  if (precision === "month") {
    const a = fmtDate(first.slice(0, 7));
    const b = fmtDate(last.slice(0, 7));
    return a === b ? a : `${a} – ${b}`;
  }
  return first === last ? fmtDate(first) : `${fmtDate(first)} – ${fmtDate(last)}`;
}

function fmtEpisodeDate(ep: RecentEpisode): string {
  return fmtSpan(ep.first_date, ep.last_date, ep.date_precision);
}

function countryHref(id: string): string {
  return `?sys=${encodeURIComponent(id)}`;
}

function CountryLink({ id, name }: { id: string; name: string }) {
  return (
    <a className="feed-country" href={countryHref(id)} {...prefetchOn(id)}
      onClick={(e) => { if (e.button === 0 && !e.metaKey && !e.ctrlKey && !e.shiftKey) { e.preventDefault(); navigate(id); } }}>
      {name}
    </a>
  );
}

function FeedItem({ row }: { row: FeedRow }) {
  if (row.kind === "covered-run") {
    return (
      <li className="feed-item covered-run">
        <div className="feed-line">
          <span className="mono small">{fmtSpan(row.first_date, row.last_date, row.date_precision)}</span>
          <CountryLink id={row.system_id} name={row.country} />
          <span className="feed-place small">National</span>
        </div>
        <div className="small dim">{row.classes.join(", ")} · {row.causes.join(", ")}</div>
        <div className="small">Records under active-campaign safeguards — see the country page.</div>
      </li>
    );
  }
  const ep = row.ep;
  const place = placementOf(ep);
  const covered = place.level === "National";
  return (
    <li className="feed-item">
      <div className="feed-line">
        <span className="mono small">{fmtEpisodeDate(ep)}</span>
        <CountryLink id={ep.system_id} name={ep.country} />
        <span className="feed-place small">{place.level}{place.names.length > 0 && <span className="dim">: {place.names.join(", ")}</span>}</span>
        {covered && <span className="mono small dim" title="A neutral row key, used instead of the record's own name in lists that set countries side by side">row {ep.episode_id}</span>}
      </div>
      <div className="small dim">{ep.classes.join(", ")} · {ep.causes.join(", ")}</div>
      {ep.episode_name && <div className="small">{ep.episode_name} <span className="dim">(one episode)</span></div>}
      {covered && <div className="small dim">Published under active-campaign safeguards — see the country page.</div>}
    </li>
  );
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
  const rows = collapseCovered(shown);
  return (
    <section className="panel global-note recent-evidence" aria-label="Recent evidence">
      <h2 className="home-h2">Recent published evidence</h2>
      {failed && <p className="small warn-text" role="alert">The recent list could not be loaded. Each country's own page still lists its record.</p>}
      {data && (
        <>
          <p className="small"><strong>Newest is not worst, and a country with no item here is not a quiet country.</strong>{" "}
            <span className="dim">Newest first, by event date. {data.scope} {readerText(data.note)}</span></p>
          <div className="map-control-row">
            <label className="small">Country{" "}
              <select aria-label="Filter recent evidence by country" value={country} onChange={(e) => setCountry(e.target.value)}>
                <option value="all">all countries</option>
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
            {rows.map((r) => <FeedItem key={r.kind === "item" ? `${r.ep.system_id}:${r.ep.episode_id}` : r.key} row={r} />)}
            {shown.length === 0 && <li className="small dim">Nothing in the recent list matches these filters.</li>}
          </ol>
          <p className="small dim">Each item opens its country's page, where the full record, its sources and its review are listed.{" "}
            <button className="linklike" type="button" onClick={() => openGlossary("publication-safeguard")}>What “National” means</button></p>
        </>
      )}
    </section>
  );
}

// Every state the build can emit, so no lane vanishes from a summary line (iteration 19: a lane
// stopped by the search allowance was counted in the total and named nowhere).
const LANE_ORDER = ["universe_searched", "current_through_latest_release", "declared_query_set_run",
                    "partially_searched", "blocked_by_source", "stopped_by_search_limit", "not_started", "legacy"];

export function laneChips(states: Record<string, number>): string {
  return LANE_ORDER.filter((k) => states[k]).map((k) => `${states[k]} ${labelFor(LANE_STATE_LABEL, k).toLowerCase()}`).join(" · ");
}

/** Data quality as the separate questions a reader actually has. Process and vintage only; no
 *  disruption count appears here, and nothing is ranked. */
export function DataQualityPanel({ data, failed, manifest, today }: {
  data: DataQuality | null; failed: boolean; manifest: Manifest | null; today: string;
}) {
  const buildDay = manifest?.build_time?.slice(0, 10) ?? null;
  const safeguarded = (manifest?.systems ?? []).filter((s) => s.campaign_restricted);
  return (
    <section className="panel global-note data-quality-panel" aria-label="Data quality">
      <h2 className="home-h2">Data freshness and quality</h2>
      {failed && <p className="small warn-text" role="alert">The data-quality summary could not be loaded.</p>}
      <dl className="dq-questions">
        <dt>When was the site last rebuilt?</dt>
        <dd className="small">{buildDay ? dated("Rebuilt", buildDay, today) : "Not known yet."}{" "}
          <span className="dim">The site rebuilds daily. A rebuild re-runs the method on the stored records; it does not
            mean every source was re-read that day.</span></dd>

        <dt>How recently were the sources checked?</dt>
        <dd className="small">{data ? (() => {
          const late = data.systems.filter((s) => s.sources_checked.some((x) => x.last_checked && x.stale_after_days != null
            && daysBetween(x.last_checked, today) > x.stale_after_days)).map((s) => s.name);
          return late.length ? `Some listed sources are past their re-check date in: ${late.join(", ")}.` : "Every listed source is within its re-check date.";
        })() : "Loading…"}{" "}
          <span className="dim">Each country keeps a list of sources (regulators, ministries, operators and similar
            publishers) that are re-read on a schedule. Checked on time says nothing about how much of the search is done.</span></dd>

        <dt>How complete is the research?</dt>
        <dd className="small">It differs by country and is shown in words, never as a percentage. Open a country:</dd>
      </dl>
      {data && data.systems.map((s) => {
        const blocked = s.lanes.filter((l) => l.state === "blocked_by_source");
        const waiting = s.lanes.filter((l) => l.source_window === "publisher_not_yet_released");
        const stopped = s.lanes.filter((l) => l.state === "stopped_by_search_limit");
        const partial = s.lanes.filter((l) => l.state === "partially_searched" || l.state === "not_started");
        return (
          <details key={s.system_id} className="dq-system">
            <summary>
              <strong>{s.name}</strong>{" "}
              <span className="small dim">{laneChips(s.lane_states)}</span>
            </summary>
            <p className="small">Reporting environment: {labelFor(ENVIRONMENT_LABEL, s.reporting_environment)}.
              Source families cited: {Object.values(s.source_families).join(", ") || "none"}.
              Newest systematic search {fmtDate(s.last_systematic_pass)}; first {fmtDate(s.first_systematic_pass)}.</p>
            {[["Blocked by the source", blocked], ["Stopped when the search allowance ran out", stopped], ["Publisher has not yet released the rest", waiting], ["Partly searched or not started", partial]].map(([title, ls]) => (
              (ls as typeof blocked).length > 0 && (
                <div key={title as string}>
                  <div className="eyebrow">{title as string}</div>
                  <ul className="lane-list small">
                    {(ls as typeof blocked).map((l) => <li key={l.lane}><span className="mono">{l.lane}</span>: {readerText(l.limitation)}</li>)}
                  </ul>
                </div>
              )
            ))}
          </details>
        );
      })}
      <dl className="dq-questions">
        <dt>What is observed and what is modelled?</dt>
        <dd className="small">Records are what sources reported. The theatre's index is a model of exposure built on those
          reports, not a measurement of output lost. A recovery date is shown as observed only when a source reported it;
          an estimate is labelled as an estimate.</dd>

        <dt>What is withheld?</dt>
        <dd className="small">{safeguarded.length
          ? `While attacks on energy facilities are being reported, some detail is not published for: ${safeguarded.map((s) => s.name).join(", ")}.`
          : "No system is under publication safeguards."}{" "}
          <span className="dim">The record still shows its date, class and cause; the facility's later status is not published.</span></dd>

        <dt>Can countries be compared?</dt>
        <dd className="small">No. Countries report under very different rules, so counts and dates are not comparable between
          them, and nothing on this site ranks them.</dd>

        <dt>How old is the national energy context?</dt>
        <dd className="small">{data
          ? <>Global energy context: {data.context_vintage.comparison_year} figures from {data.context_vintage.source}, release
            of {fmtDate(data.context_vintage.release)}, retrieved {fmtDate(data.context_vintage.retrieved)}. <span className="dim">Updated {data.context_vintage.update_cadence}; separate from how recently each country's record was researched.</span></>
          : "Loading…"}</dd>
      </dl>
      {data && (
        <details className="dq-system">
          <summary className="small">Recovery evidence by infrastructure class, monitored countries together</summary>
          <p className="small dim">{data.recovery_by_class.note}</p>
          <table className="sector-table">
            <caption className="sr-only">Recovery evidence by infrastructure class, monitored countries together</caption>
            <thead><tr><th scope="col">Class</th><th scope="col">Reported as</th><th scope="col">Cases</th><th scope="col">Days to report</th></tr></thead>
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
      )}
    </section>
  );
}

export { LANE_WINDOW_LABEL };
