import { useEffect, useState } from "react";
import type { CountrySystem } from "./manifest";
import { ContextTimeline, loadRegionalContext, type RegionalContext } from "./impacts";
import { anyTie, latestCounts, latestEntries } from "./impacts/latestOfType";
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

/** The newest statements of each kind, as the build marks them: the country page's compact view.
 *  The served `latest_by_type` (or, in an older payload, the served flags and the statements tied
 *  with them) is used as it is. Several statements of one kind can share the newest date; all of
 *  them are kept, never one picked over the others. */
export function latestOfEachType(ctx: RegionalContext): RegionalContext {
  const latest = latestEntries(ctx.entries, ctx.latest_by_type);
  return { ...ctx, entries: ctx.entries.filter((e) => latest.has(e)) };
}

/** The sentence above the compact view: plural when a kind has more than one newest statement. */
export function compactLead(compact: RegionalContext, older: number): string {
  const tie = anyTie(latestCounts(compact.entries, latestEntries(compact.entries, compact.latest_by_type)));
  const lead = tie ? "The newest statements of each kind (where several share the newest date, all are shown)" : "The newest statement of each kind";
  return older > 0 ? `${lead}; ${older} earlier ${older === 1 ? "statement is" : "statements are"} on the full timeline.` : `${lead}.`;
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
            <p className="small dim regional-lead">{compactLead(compact, older)}</p>
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
