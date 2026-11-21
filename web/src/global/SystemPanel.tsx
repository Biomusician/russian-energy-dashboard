import type { Manifest } from "./manifest";
import { prefetchOn } from "./prefetch";
import { THEATRE_MEANING, panelRows, systemOf, type PanelRow, type WorldIndex } from "./homeSelection";
import { fmtDate, fmtNum } from "../data";

/** "Where to explore": the text equivalent of the home map (iteration 23).
 *
 *  Every place the map can open is a real link here, and every country on the map is a button in
 *  "All countries, A to Z", so nothing needs the map. The order is the manifest's: the one indexed
 *  system, then the Impact Atlas, the regional overview, the country systems alphabetically, and
 *  Compare. No count, no score, no maturity label: those are on each system's own page, and on a
 *  list that sets places side by side they read as a ranking.
 *
 *  Pointing at a row (hover or keyboard focus) outlines the same place on the map. */

export default function SystemPanel({ manifest, index, opened, onHighlight, onOpen, onShowGroup, onPickCountry, card }: {
  manifest: Manifest; index: WorldIndex | null; opened: string | null;
  onHighlight: (key: string | null) => void;
  onOpen: (row: PanelRow) => void;
  onShowGroup: (groupId: string, ret: string) => void;
  onPickCountry: (unit: string, ret: string) => void;
  card: React.ReactNode;
}) {
  const rows = panelRows(manifest);
  const section = (s: PanelRow["section"]) => rows.filter((r) => r.section === s);
  const point = (key: string | null) => ({
    onMouseEnter: () => onHighlight(key), onMouseLeave: () => onHighlight(null),
    onBlur: () => onHighlight(null),
  });
  const rowLink = (r: PanelRow, body: React.ReactNode, cls = "") => {
    const pre = r.systemId ? prefetchOn(r.systemId) : null;
    const hl = r.systemId ?? (r.groupId ? `group:${r.groupId}` : null);
    return (
      <a className={`hp-row${cls}${opened === r.key ? " opened" : ""}`} href={r.href} data-ret={r.key}
         {...point(hl)}
         onPointerEnter={pre?.onPointerEnter}
         onFocus={() => { onHighlight(hl); pre?.onFocus(); }}
         onClick={(e) => {
           if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
           e.preventDefault();
           onOpen(r);
         }}>
        {body}
        {opened === r.key && <span className="sr-only"> (last opened)</span>}
      </a>
    );
  };
  return (
    <aside className="home-panel" id="where-to-explore" aria-labelledby="where-to-explore-title" tabIndex={-1}>
      <div className="hp-head">
        <h2 id="where-to-explore-title" className="home-h2">Where to explore</h2>
        <p className="small dim">Never ranked or compared: the indexed system first, then the rest alphabetically.</p>
      </div>
      {card}
      <div className="hp-body">
        {section("indexed").map((r) => {
          const s = systemOf(manifest, r.systemId as string);
          return (
            <div className="hp-section" key={r.key}>
              <h3 className="eyebrow">Indexed system</h3>
              {rowLink(r, (
                <>
                  <span className="hp-name">{r.label}</span>
                  {s?.headline && (
                    <span className="hp-headline"><span className="home-headline-num">{fmtNum(s.headline.value, 1)}</span>{" "}
                      {s.headline.label} · {fmtDate(s.headline.as_of)}</span>
                  )}
                  <span className="hp-sub small">{THEATRE_MEANING}</span>
                </>
              ), " hp-theatre")}
            </div>
          );
        })}
        <div className="hp-section">
          <h3 className="eyebrow">Evidence beyond the systems</h3>
          {section("beyond").map((r) => rowLink(r, (
            <>
              <span className="hp-name">{r.label}</span>
              <span className="hp-sub small">Records from any country · no score, not a census</span>
            </>
          )))}
        </div>
        {section("regional").length > 0 && (
          <div className="hp-section">
            <h3 className="eyebrow">Regional overview</h3>
            {section("regional").map((r) => (
              <div className="hp-group" key={r.key}>
                {rowLink(r, (
                  <>
                    <span className="hp-name">{r.label}</span>
                    <span className="hp-sub small">Its members side by side</span>
                  </>
                ))}
                <button type="button" className="ghost hp-show" data-ret={`show:${r.groupId}`}
                  {...point(`group:${r.groupId}`)} onFocus={() => onHighlight(`group:${r.groupId}`)}
                  onClick={() => onShowGroup(r.groupId as string, `show:${r.groupId}`)}>
                  Show on map<span className="sr-only">: {r.label}</span>
                </button>
              </div>
            ))}
          </div>
        )}
        <div className="hp-section">
          <h3 className="eyebrow">Country systems · no index</h3>
          <ul className="hp-list">
            {section("countries").map((r) => (
              <li key={r.key}>{rowLink(r, (
                <>
                  <span className="hp-name">{r.label}</span>
                  {r.tag && <span className="hp-tag">{r.tag}</span>}
                </>
              ))}</li>
            ))}
          </ul>
        </div>
        <div className="hp-section">
          <h3 className="eyebrow">Tools</h3>
          {section("tools").map((r) => rowLink(r, <span className="hp-name">{r.label}</span>))}
          <AllCountries index={index} onPick={onPickCountry} onHighlight={onHighlight} />
        </div>
      </div>
    </aside>
  );
}

/** Every country on the map, A to Z: the keyboard and screen-reader route to any of them. A country
 *  with no system is selected exactly as a click on the map would select it. */
function AllCountries({ index, onPick, onHighlight }: {
  index: WorldIndex | null; onPick: (unit: string, ret: string) => void; onHighlight: (key: string | null) => void;
}) {
  // No filter box: the search above the map finds every country already, and a second search with
  // a different scope was one of the things this page used to get wrong.
  return (
    <details className="hp-az">
      <summary>All countries, A–Z</summary>
      {!index ? <p className="small dim" role="status">Loading the list of countries…</p> : (
        <ul className="hp-az-list" aria-label="All countries">
          {index.countries.map((c) => (
            <li key={c.a3}>
              <button type="button" className="linklike hp-az-item" data-ret={`az:${c.a3}`}
                onMouseEnter={() => onHighlight(c.unit)} onMouseLeave={() => onHighlight(null)}
                onFocus={() => onHighlight(c.unit)} onBlur={() => onHighlight(null)}
                onClick={() => onPick(c.unit, `az:${c.a3}`)}>{c.name}</button>
            </li>
          ))}
        </ul>
      )}
    </details>
  );
}
