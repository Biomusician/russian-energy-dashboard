import { Suspense, lazy, useEffect, useLayoutEffect } from "react";
import { routeFor, useRoute, type Route } from "./global/router";
import GlobalHome from "./global/GlobalHome";
import { ViewBoundary } from "./components/ViewBoundary";
import { importCountryView, importGroupView, importTheatre, prefetchRoute } from "./global/prefetch";

// Each view is its own chunk. The global home must not download the theatre's map stack, and a
// country view must not download the theatre at all: payload discipline per system is the point
// of the manifest (iteration 14).
const TheatreApp = lazy(importTheatre);
const CountryView = lazy(importCountryView);
const GroupView = lazy(importGroupView);
const CompareView = lazy(() => import("./global/CompareView"));

/** What the error boundary calls a view, and its address without saved state. A route this does not
 *  name still gets a boundary, under the generic label. */
function describe(route: Route): { key: string; label: string; cleanHref?: string } {
  switch (route.view) {
    case "home": return { key: "home", label: "The overview" };
    case "theatre": return { key: "theatre", label: "The Russia, Belarus & Crimea view", cleanHref: "?sys=ru" };
    case "country": return { key: `country:${route.id}`, label: "This country's page", cleanHref: `?sys=${encodeURIComponent(route.id)}` };
    case "group": return { key: `group:${route.id}`, label: "This regional overview", cleanHref: `?group=${encodeURIComponent(route.id)}` };
    // Not keyed on the selection: an edit to the compared systems keeps the boundary and the loaded columns.
    case "compare": return { key: "compare", label: "The comparison", cleanHref: "?compare=" };
    default: return { key: (route as { view: string }).view, label: "This view" };
  }
}

/** The tab title a route starts with (iteration 21: it stayed "overview" after opening the
 *  theatre). A view that knows more, such as a country's name, refines it in its own effect. */
export function defaultTitle(route: ReturnType<typeof routeFor>): string {
  const base = "Energy Disruption Monitor";
  switch (route.view) {
    case "home": return `${base} — overview`;
    case "theatre": return `${base} — Russia, Belarus & Crimea`;
    case "group": return `${base} — regional overview`;
    case "country": return `${base} — country system`;
    case "compare": return `${base} — compare systems`;
    default: return base;
  }
}

export default function Root() {
  const route = useRoute();
  // Start the route's data now, in parallel with its chunk, rather than after the view mounts.
  useEffect(() => { prefetchRoute(route); }, [route]);
  const view = describe(route);
  // A layout effect runs before every view's ordinary effects, so a view's own, more specific
  // title always wins, and every route change still resets a stale one.
  // Keyed on the view and id, not the route object: a search that only changes a country's
  // selected region must not reset that country's own title.
  const routeKey = `${route.view}:${"id" in route ? route.id : ""}`;
  useLayoutEffect(() => { document.title = defaultTitle(route); }, [routeKey]);  // eslint-disable-line react-hooks/exhaustive-deps
  return (
    // Keyed on the route: a failure stays with the view that failed, and any other view mounts
    // with a fresh boundary. Every route rendered inside is contained, including ones added later.
    <ViewBoundary key={view.key} label={view.label} cleanHref={view.cleanHref} home={route.view === "home"}>
      <Suspense fallback={<p className="dim" role="status" style={{ padding: 20 }}>Loading…</p>}>
        {route.view === "home" && <GlobalHome />}
        {route.view === "theatre" && <TheatreApp />}
        {/* Keyed on the id so switching countries remounts cleanly and the old load is ignored. */}
        {route.view === "country" && <CountryView key={route.id} id={route.id} />}
        {route.view === "group" && <GroupView key={route.id} id={route.id} />}
        {/* Not keyed: an edit to the selection keeps the countries already loaded. */}
        {route.view === "compare" && <CompareView ids={route.ids} />}
      </Suspense>
    </ViewBoundary>
  );
}
