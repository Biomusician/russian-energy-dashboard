/** Which view a URL opens (iteration 14).
 *
 *  THE RULES, AND WHY.
 *  - `?sys=ru`            the Russia/Belarus/Crimea theatre.
 *  - `?sys=<country>`     that country system. Validated against the manifest by the view, not
 *                         here, so a theatre link never waits on the manifest to open.
 *  - no `sys`, but any parameter the theatre has ever written: the theatre. Every link shared
 *    before iteration 14 that carried view state looks like this, and must still open what its
 *    sender saw. A pre-14 link to the theatre's untouched default view was a bare URL; it carried
 *    no state and now opens the home page, one click from the theatre. That is the one cost of
 *    giving the home page the bare URL.
 *  - `?group=<slug>`      a regional overview (iteration 19), e.g. `?group=gulf`. Validated against
 *                         the manifest by the view. `sys` wins if both are present.
 *  - `?compare=us,ca,sa`  the comparison workspace (iteration 21): 2 to 4 systems, in the order
 *                         the reader chose. Ids are lower-cased and de-duplicated here; whether
 *                         each one exists is decided by the view against the manifest, which
 *                         drops an unknown id with a visible note. `sys` and `group` win.
 *  - a bare URL: the global home.
 *
 *  Nothing here reads a value from the query string as an object key, so `sys=constructor`
 *  and friends are just unknown ids.
 */

import { useEffect, useState } from "react";

export type Route =
  | { view: "home" }
  | { view: "theatre" }
  | { view: "country"; id: string }
  | { view: "group"; id: string }
  | { view: "compare"; ids: string[] };

/** At most this many systems side by side: past four a table of prose stops being readable. */
export const MAX_COMPARE = 4;
// How many ids a compare link may carry before the view resolves them. More than MAX_COMPARE, so an
// unknown id early in a hand-edited link cannot push a real one out before the view can say so.
const MAX_COMPARE_TOKENS = 12;

// Every key the theatre's URL state has ever written (urlState.ts). Order is irrelevant.
const THEATRE_KEYS = ["m", "a", "d", "r", "cls", "cau", "con", "ly", "cam", "cmp"];

export function routeFor(search: string): Route {
  const p = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const sys = (p.get("sys") ?? "").trim().toLowerCase();
  if (sys === "ru") return { view: "theatre" };
  if (sys) return { view: "country", id: sys };
  const group = (p.get("group") ?? "").trim().toLowerCase();
  if (group) return { view: "group", id: group };
  // getAll: `?compare=us&compare=ca` reads as `?compare=us,ca` instead of silently losing one.
  if (p.has("compare")) return { view: "compare", ids: compareIdsFrom(p.getAll("compare").join(",")) };
  if (THEATRE_KEYS.some((k) => p.has(k))) return { view: "theatre" };
  return { view: "home" };
}

/** The query string that opens a system. The home is the bare path. */
export function hrefFor(systemId: string | null): string {
  return systemId ? `?sys=${encodeURIComponent(systemId)}` : "?";
}

/** The ids a `compare` value names: trimmed, lower-cased, de-duplicated, in the reader's order,
 *  which is never re-sorted. URLSearchParams has already decoded `%2C`, so an encoded comma
 *  separates ids exactly as a literal one does. */
export function compareIdsFrom(raw: string): string[] {
  const out: string[] = [];
  for (const t of raw.split(",")) {
    const id = t.trim().toLowerCase();
    if (id && !out.includes(id)) out.push(id);
    if (out.length >= MAX_COMPARE_TOKENS) break;
  }
  return out;
}

/** The link that opens the comparison workspace with these systems, in this order. Only the
 *  selection is written: the view has no other state worth sharing, so no defaults are serialised. */
export function compareHref(ids: string[]): string {
  return `?compare=${compareIdsFrom(ids.join(",")).slice(0, MAX_COMPARE).map(encodeURIComponent).join(",")}`;
}

const CHANGE = "edm:locationchange";

/** Move to another view, as a new history entry so Back returns to where the reader was. */
export function navigate(systemId: string | null) {
  const q = hrefFor(systemId);
  window.history.pushState(null, "", q === "?" ? window.location.pathname : `${window.location.pathname}${q}`);
  window.dispatchEvent(new Event(CHANGE));
}

/** Open a regional overview, as a new history entry. */
export function navigateGroup(slug: string) {
  window.history.pushState(null, "", `${window.location.pathname}?group=${encodeURIComponent(slug)}`);
  window.dispatchEvent(new Event(CHANGE));
}

/** Open the comparison workspace, or with `replace` edit its selection. An edit replaces the history
 *  entry, so Back leaves the workspace instead of stepping through every column the reader added. */
export function navigateCompare(ids: string[], replace = false) {
  const url = `${window.location.pathname}${compareHref(ids)}`;
  if (replace) window.history.replaceState(null, "", url);
  else window.history.pushState(null, "", url);
  window.dispatchEvent(new Event(CHANGE));
}

/** The current route, kept in step with Back/Forward and with navigate(). */
export function useRoute(): Route {
  const [route, setRoute] = useState(() => routeFor(window.location.search));
  useEffect(() => {
    const update = () => setRoute(routeFor(window.location.search));
    window.addEventListener("popstate", update);
    window.addEventListener(CHANGE, update);
    return () => {
      window.removeEventListener("popstate", update);
      window.removeEventListener(CHANGE, update);
    };
  }, []);
  return route;
}
