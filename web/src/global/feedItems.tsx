import "../styles/feed.css";
import { fmtDate } from "../data";
import { navigate } from "./router";
import { prefetchOn } from "./prefetch";
import type { RecentEpisode } from "./manifest";
import type { FeedRow } from "./homeModel";

/** Pieces of the dated record lists that the home page and the Gulf littoral view both show.
 *  One wording and one layout for a run of campaign-covered records, wherever it appears. */

export function fmtSpan(first: string, last: string, precision: string): string {
  // From the string itself: a browser's Date parser reads "2026-04" differently across engines.
  if (precision === "month") {
    const a = fmtDate(first.slice(0, 7));
    const b = fmtDate(last.slice(0, 7));
    return a === b ? a : `${a} – ${b}`;
  }
  return first === last ? fmtDate(first) : `${fmtDate(first)} – ${fmtDate(last)}`;
}

export function fmtEpisodeDate(ep: RecentEpisode): string {
  return fmtSpan(ep.first_date, ep.last_date, ep.date_precision);
}

export function CountryLink({ id, name }: { id: string; name: string }) {
  return (
    <a className="feed-country" href={`?sys=${encodeURIComponent(id)}`} {...prefetchOn(id)}
      onClick={(e) => { if (e.button === 0 && !e.metaKey && !e.ctrlKey && !e.shiftKey) { e.preventDefault(); navigate(id); } }}>
      {name}
    </a>
  );
}

/** Wording for a campaign-covered record in a list that sets countries side by side. No count:
 *  a run of "National" rows is itself a tally of an attack campaign. */
export const COVERED_RUN_TEXT = "Records under active-campaign safeguards — see the country page.";

/** Consecutive covered records of one country, as one line (homeModel.collapseCovered). */
export function CoveredRunItem({ row }: { row: Extract<FeedRow, { kind: "covered-run" }> }) {
  return (
    <li className="feed-item covered-run">
      <div className="feed-line">
        <span className="mono small">{fmtSpan(row.first_date, row.last_date, row.date_precision)}</span>
        <CountryLink id={row.system_id} name={row.country} />
        <span className="feed-place small">National</span>
      </div>
      <div className="small dim">{row.classes.join(", ")} · {row.causes.join(", ")}</div>
      <div className="small">{COVERED_RUN_TEXT}</div>
    </li>
  );
}
