import { useEffect, useState } from "react";
import type { CountrySystem } from "./manifest";
import { ContextTimeline, loadRegionalContext, type RegionalContext } from "./impacts";
import { TAB_LABEL, type RegionalGroup } from "./countryTabs";
import { inSentence } from "./countryCopy";
import { navigateGroup } from "./router";
import "../styles/country.css";
import "../styles/countryOverview.css";

/** The "Gulf & Hormuz context" tab of a country page (iteration 22).
 *
 *  Shown only for a system the manifest puts in the regional-context group. It is the region's
 *  context, not this country's record: the newest dated statement of each kind, each "as of" its
 *  own date, with the full timeline one link away on the regional page.
 *
 *  It says nothing about any facility in this country, and the tab says so first.
 */

/** The newest statement of each kind, as the build marks them: the country page's compact view.
 *  The served flag is used as it is; nothing here decides what is newest. */
export function latestOfEachType(ctx: RegionalContext): RegionalContext {
  return { ...ctx, entries: ctx.entries.filter((e) => e.is_latest_of_type) };
}

export function regionalNote(name: string): string {
  return `Aggregate regional context. It describes the region as a whole and says nothing about any facility in ${inSentence(name)}. `
    + `It is not part of ${inSentence(name)}'s published record and enters no count or index.`;
}

export function CountryRegional({ sys, group }: { sys: CountrySystem; group: RegionalGroup }) {
  const [ctx, setCtx] = useState<RegionalContext | null>(null);
  const [failed, setFailed] = useState(false);
  // Fetched when the tab is opened: the component is rendered only while its tab is.
  useEffect(() => {
    let live = true;
    loadRegionalContext().then((c) => { if (live) setCtx(c); }).catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, []);
  const compact = ctx ? latestOfEachType(ctx) : null;
  const older = ctx && compact ? ctx.entries.length - compact.entries.length : 0;
  return (
    <div className="country-regional">
      <h2>{TAB_LABEL.regional}</h2>
      <p className="small regional-note" role="note">{regionalNote(sys.name)}</p>
      {!ctx && !failed && <p className="small dim" role="status">Loading the regional context…</p>}
      {failed && <p className="small warn-text" role="alert">The regional context could not be loaded. The rest of this page is not affected.</p>}
      {compact && (
        <>
          {compact.entries.length > 0 && (
            <p className="small dim">The newest statement of each kind
              {older > 0 ? `; ${older} earlier ${older === 1 ? "statement is" : "statements are"} on the full timeline.` : "."}</p>
          )}
          <ContextTimeline ctx={compact} />
        </>
      )}
      <p className="small">
        <a href={`?group=${encodeURIComponent(group.slug)}`}
           onClick={(e) => {
             if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
             e.preventDefault();
             navigateGroup(group.slug);
           }}>Full timeline on the {group.label} page</a>
      </p>
    </div>
  );
}

export default CountryRegional;
