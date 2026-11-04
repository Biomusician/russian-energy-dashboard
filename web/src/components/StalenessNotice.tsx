/** "This page is not current" (iteration 12 P2).
 *
 *  The counterweight to the eleven-day outage of 2026-09-21, when the dashboard served a frozen
 *  payload and said nothing. It renders only when there is something to say, so a healthy build
 *  costs the layout nothing — the grid row it occupies collapses to zero height.
 *
 *  Why it is not hidden by map focus, briefing mode or print: a reader who has stripped the
 *  chrome, or who is holding a printout weeks later, has fewer ways to notice the date than one
 *  looking at the full dashboard. A shipped artifact must carry its own context.
 */

import { assessFreshness, type FreshnessAssessment } from "../freshness";
import type { Snapshot } from "../types";

export default function StalenessNotice({ snapshot, now }: {
  snapshot: Snapshot;
  /** Injected so a test can drive the component at a chosen date. */
  now?: Date;
}) {
  const f: FreshnessAssessment = assessFreshness(
    snapshot.as_of, snapshot.publication_freshness, now ?? new Date());

  // The drawer toggles used to float over the shell and covered "NOT CURRENT" at narrow widths,
  // so this component measured itself into --staleness-h. Since iteration 17 they are anchored to
  // the map's grid area (theme.css .drawer-toggles), which is below this row by construction.


  if (!f.banner) return null;

  const cadenceSource = snapshot.publication_freshness?.cadence_source;
  return (
    <div
      className={`staleness${f.severe ? " severe" : ""}`}
      // A reader arriving on a stale page needs to be told, not to discover it; a quieter
      // ageing notice is status, not an interruption.
      role={f.severe ? "alert" : "status"}
      title={cadenceSource ? `Build cadence: ${cadenceSource}` : undefined}
    >
      {f.banner}
      {f.days != null && f.level !== "clock_behind" && (
        <>
          {" "}
          <span className="staleness-age">
            ({f.days} {f.days === 1 ? "day" : "days"} since {snapshot.as_of})
          </span>
        </>
      )}
    </div>
  );
}
