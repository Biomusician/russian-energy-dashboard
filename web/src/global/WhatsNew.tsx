import { useEffect, useState } from "react";
import { loadWhatsNew, type WhatsNew as WhatsNewData, type WhatsNewChange } from "./manifest";
import { navigate } from "./router";
import { WHATS_NEW_ID, showWhatsNew } from "./GlobalNav";
import { fmtDate } from "../data";
import { localISODate } from "../freshness";
import { readerText } from "./readerText";
import { buildAgeText, changeSummary, indexText, itemText } from "./whatsNewText";
import "../styles/whatsnew.css";

/** What changed in the published data since the previous published build (iteration 21).
 *
 *  Every row names its cause from a closed list, so a historical record found by research is never
 *  shown as news, a rule change never as a country improving, and the theatre's daily decay never
 *  as a source event. No counts: systems are listed alphabetically, and only those that changed.
 *  The age of the build is worked out here, on the reader's clock. */
export default function WhatsNew({ now }: { now?: Date } = {}) {
  const [data, setData] = useState<WhatsNewData | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let live = true;
    loadWhatsNew().then((d) => { if (live) setData(d); }).catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, []);
  // Arriving from the site bar's "What's new" (or a link to #whats-new): once the panel has its
  // content, and so its final height, bring it into view.
  useEffect(() => {
    if ((data || failed) && window.location.hash === `#${WHATS_NEW_ID}`) showWhatsNew();
  }, [data, failed]);
  return <WhatsNewPanel data={data} failed={failed} now={now} />;
}

/** The panel for a loaded (or failed) file, apart from the loading so a test can render it. */
export function WhatsNewPanel({ data, failed, now }: { data: WhatsNewData | null; failed: boolean; now?: Date }) {
  const labels = new Map((data?.categories ?? []).map((c) => [c.id, c]));
  const age = data ? buildAgeText(data.comparison.current_as_of, localISODate(now ?? new Date())) : "";

  const change = (c: WhatsNewChange, i: number) => {
    const cat = labels.get(c.category);
    const summary = changeSummary(c);
    return (
      <li key={`${c.category}-${i}`} className="wn-change" data-category={c.category}>
        <span className="wn-cat" title={cat?.meaning}>{cat?.label ?? c.category}</span>
        {summary && <span className="small"> {summary}</span>}
        {c.notes.map((n, j) => <div key={j} className="small">{readerText(n)}</div>)}
        {c.items && c.items.length > 0 && (
          <ul className="wn-items small">
            {c.items.map((it) => <li key={it.key} data-row={it.key}>{itemText(it)}</li>)}
            {c.more && <li className="dim">and more on the country page</li>}
          </ul>
        )}
      </li>
    );
  };

  return (
    <section id={WHATS_NEW_ID} className="panel global-note whats-new" aria-labelledby={`${WHATS_NEW_ID}-heading`}>
      <h2 id={`${WHATS_NEW_ID}-heading`} className="eyebrow" tabIndex={-1}>What's new in the data</h2>
      {failed && <p className="small warn-text" role="alert">The list of changes could not be loaded. Each system's own page is unaffected.</p>}
      {data && !data.available && (
        <p className="small dim" title={data.unavailable_reason ?? undefined}>
          No comparison with an earlier published build is available for this build, so no changes are listed. That is not the same as nothing having changed.
        </p>
      )}
      {data && data.available && (
        <>
          <p className="small dim wn-basis">
            Changes since the published build of {fmtDate(data.comparison.previous_as_of)}. This build is
            dated {fmtDate(data.comparison.current_as_of)}{age ? ` (${age})` : ""}.
          </p>
          {data.comparison.note && <p className="small warn-text">{readerText(data.comparison.note)}</p>}
          {data.global.length > 0 && (
            <div className="wn-system wn-global" aria-label="Changes that apply to every country">
              <h3 className="wn-heading">Every country</h3>
              <ul className="wn-changes">{data.global.map(change)}</ul>
            </div>
          )}
          {/* One closed line per system, naming its kinds of change, so thirteen systems stay a short
              list; the detail opens on demand. */}
          {data.systems.map((s) => (
            <details key={s.system_id} className="wn-system" data-system={s.system_id} aria-label={`Changes: ${s.name}`}>
              <summary>
                <span className="wn-name">{s.name}</span>{" "}
                <span className="small dim wn-kinds">
                  {s.unavailable ? "could not be compared" : s.changes.map((c) => labels.get(c.category)?.label ?? c.category).join(" · ")}
                </span>
              </summary>
              {s.unavailable && <p className="small dim">Could not be compared with the previous build; this is not the same as unchanged.</p>}
              {indexText(s) && <p className="small">{indexText(s)}</p>}
              <ul className="wn-changes">{s.changes.map(change)}</ul>
              <button className="linklike small" onClick={() => navigate(s.system_id)}>Go to the {s.name} page</button>
            </details>
          ))}
          {data.unchanged.length > 0 && (
            <p className="small dim wn-unchanged">
              No published change: {data.unchanged.map((u) => u.name).join(", ")}.
            </p>
          )}
          <details className="wn-legend small">
            <summary>What each kind of change means</summary>
            <dl>
              {data.categories.map((c) => (
                <div key={c.id}><dt>{c.label}</dt><dd>{c.meaning}</dd></div>
              ))}
            </dl>
          </details>
          <p className="small dim">{readerText(data.note)}</p>
        </>
      )}
    </section>
  );
}
