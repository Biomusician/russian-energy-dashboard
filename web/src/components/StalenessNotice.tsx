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

import { useLayoutEffect, useRef } from "react";
import { assessFreshness, type FreshnessAssessment } from "../freshness";
import type { Snapshot } from "../types";

export default function StalenessNotice({ snapshot, now }: {
  snapshot: Snapshot;
  /** Injected so a test can drive the component at a chosen date. */
  now?: Date;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const f: FreshnessAssessment = assessFreshness(
    snapshot.as_of, snapshot.publication_freshness, now ?? new Date());

  // The drawer toggles float over the top-left and top-right of the shell. Before this they sat
  // on top of the warning and covered the words "NOT CURRENT" at narrow widths — caught in the
  // browser, not by a test. The height is measured rather than assumed because the text wraps to
  // one line at desktop width and four on a phone.
  useLayoutEffect(() => {
    const el = ref.current;
    const root = document.documentElement;
    if (!el) {
      root.style.removeProperty("--staleness-h");
      return;
    }
    const publish = () => root.style.setProperty("--staleness-h", `${el.offsetHeight}px`);
    publish();
    // ResizeObserver is the reliable signal (the text rewraps without a window resize), but the
    // window listener keeps it correct in environments that do not deliver observations.
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(publish) : null;
    ro?.observe(el);
    window.addEventListener("resize", publish);
    return () => {
      ro?.disconnect();
      window.removeEventListener("resize", publish);
      root.style.removeProperty("--staleness-h");
    };
  }, [f.banner]);

  if (!f.banner) return null;

  const cadenceSource = snapshot.publication_freshness?.cadence_source;
  return (
    <div
      ref={ref}
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
