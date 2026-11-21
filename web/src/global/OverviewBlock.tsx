import type { CountrySystem } from "./manifest";
import { OVERVIEW_TITLE, countryOverview, type ImpactPresence, type ListedPresence } from "./countryOverview";
import { tabHref, type RegionalGroup, type Tab } from "./countryTabs";
import "../styles/country.css";
import "../styles/countryOverview.css";

/** "What this page can tell you" (iteration 22): the first thing a country page says after its
 *  title. Three short parts, always in this order: what is published, what else is here, what is
 *  not published and why. The words come from countryOverview.ts; this draws them.
 *
 *  Each destination is a real link to its tab (`?sys=ir&tab=impacts`), so it can be copied or opened
 *  in a new window; a plain click switches the tab in place.
 */
export function CountryOverview({ sys, impacts, regional, listed = null, onTab }: {
  sys: CountrySystem; impacts: ImpactPresence; regional: RegionalGroup | null; listed?: ListedPresence; onTab: (t: Tab) => void;
}) {
  const o = countryOverview(sys, impacts, regional, listed);
  return (
    <section className="country-overview" aria-labelledby="country-overview-title">
      <h2 id="country-overview-title">{OVERVIEW_TITLE}</h2>
      <div className="overview-parts">
        <div className="overview-part overview-published">
          <h3 className="eyebrow">Published here</h3>
          <p className="small"><strong className="overview-lead">{o.published}</strong> {o.publishedNote}</p>
        </div>
        <div className="overview-part overview-known">
          <h3 className="eyebrow">Also on this page</h3>
          <ul className="small overview-links">
            {o.known.map((k) => (
              <li key={k.tab}>
                <a href={tabHref(sys.system_id, k.tab)} data-tab={k.tab}
                   onClick={(e) => {
                     // A modified click (new tab, new window) keeps the browser's own behaviour.
                     if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
                     e.preventDefault();
                     onTab(k.tab);
                   }}>{k.label}</a>
                <span className="overview-link-line">: {k.line}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="overview-part overview-withheld">
          <h3 className="eyebrow">Not published, and why</h3>
          <p className="small">{o.withheld.join(" ")}</p>
        </div>
      </div>
    </section>
  );
}

export default CountryOverview;
