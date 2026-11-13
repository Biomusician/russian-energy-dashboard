import { Suspense, lazy, useLayoutEffect } from "react";
import { routeFor, useRoute } from "./global/router";
import GlobalHome from "./global/GlobalHome";

// Each view is its own chunk. The global home must not download the theatre's map stack, and a
// country view must not download the theatre at all: payload discipline per system is the point
// of the manifest (iteration 14).
const TheatreApp = lazy(() => import("./App"));
const CountryView = lazy(() => import("./global/CountryView"));
const GroupView = lazy(() => import("./global/GroupView"));

/** The tab title a route starts with (iteration 21: it stayed "overview" after opening the
 *  theatre). A view that knows more, such as a country's name, refines it in its own effect. */
export function defaultTitle(route: ReturnType<typeof routeFor>): string {
  const base = "Energy Disruption Monitor";
  switch (route.view) {
    case "home": return `${base} — overview`;
    case "theatre": return `${base} — Russia, Belarus & Crimea`;
    case "group": return `${base} — regional overview`;
    case "country": return `${base} — country system`;
    default: return base;
  }
}

export default function Root() {
  const route = useRoute();
  // A layout effect runs before every view's ordinary effects, so a view's own, more specific
  // title always wins, and every route change still resets a stale one.
  // Keyed on the view and id, not the route object: a search that only changes a country's
  // selected region must not reset that country's own title.
  const routeKey = `${route.view}:${"id" in route ? route.id : ""}`;
  useLayoutEffect(() => { document.title = defaultTitle(route); }, [routeKey]);  // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <Suspense fallback={<p className="dim" role="status" style={{ padding: 20 }}>Loading…</p>}>
      {route.view === "home" && <GlobalHome />}
      {route.view === "theatre" && <TheatreApp />}
      {/* Keyed on the id so switching countries remounts cleanly and aborts the old load. */}
      {route.view === "country" && <CountryView key={route.id} id={route.id} />}
      {route.view === "group" && <GroupView key={route.id} id={route.id} />}
    </Suspense>
  );
}
