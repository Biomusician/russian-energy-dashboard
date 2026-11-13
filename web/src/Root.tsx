import { Suspense, lazy, useEffect } from "react";
import { useRoute, type Route } from "./global/router";
import GlobalHome from "./global/GlobalHome";
import { ViewBoundary } from "./components/ViewBoundary";
import { importCountryView, importGroupView, importTheatre, prefetchRoute } from "./global/prefetch";

// Each view is its own chunk. The global home must not download the theatre's map stack, and a
// country view must not download the theatre at all: payload discipline per system is the point
// of the manifest (iteration 14).
const TheatreApp = lazy(importTheatre);
const CountryView = lazy(importCountryView);
const GroupView = lazy(importGroupView);

/** What the error boundary calls a view, and its address without saved state. A route this does not
 *  name still gets a boundary, under the generic label. */
function describe(route: Route): { key: string; label: string; cleanHref?: string } {
  switch (route.view) {
    case "home": return { key: "home", label: "The overview" };
    case "theatre": return { key: "theatre", label: "The Russia, Belarus & Crimea view", cleanHref: "?sys=ru" };
    case "country": return { key: `country:${route.id}`, label: "This country's page", cleanHref: `?sys=${encodeURIComponent(route.id)}` };
    case "group": return { key: `group:${route.id}`, label: "This regional overview", cleanHref: `?group=${encodeURIComponent(route.id)}` };
    default: return { key: (route as { view: string }).view, label: "This view" };
  }
}

export default function Root() {
  const route = useRoute();
  // Start the route's data now, in parallel with its chunk, rather than after the view mounts.
  useEffect(() => { prefetchRoute(route); }, [route]);
  const view = describe(route);
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
      </Suspense>
    </ViewBoundary>
  );
}
