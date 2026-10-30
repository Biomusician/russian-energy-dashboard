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
 *  - a bare URL: the global home.
 *
 *  Nothing here reads a value from the query string as an object key, so `sys=constructor`
 *  and friends are just unknown ids.
 */

import { useEffect, useState } from "react";

export type Route =
  | { view: "home" }
  | { view: "theatre" }
  | { view: "country"; id: string };

// Every key the theatre's URL state has ever written (urlState.ts). Order is irrelevant.
const THEATRE_KEYS = ["m", "a", "d", "r", "cls", "cau", "con", "ly", "cam", "cmp"];

export function routeFor(search: string): Route {
  const p = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const sys = (p.get("sys") ?? "").trim().toLowerCase();
  if (sys === "ru") return { view: "theatre" };
  if (sys) return { view: "country", id: sys };
  if (THEATRE_KEYS.some((k) => p.has(k))) return { view: "theatre" };
  return { view: "home" };
}

/** The query string that opens a system. The home is the bare path. */
export function hrefFor(systemId: string | null): string {
  return systemId ? `?sys=${encodeURIComponent(systemId)}` : "?";
}

const CHANGE = "edm:locationchange";

/** Move to another view, as a new history entry so Back returns to where the reader was. */
export function navigate(systemId: string | null) {
  const q = hrefFor(systemId);
  window.history.pushState(null, "", q === "?" ? window.location.pathname : `${window.location.pathname}${q}`);
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
