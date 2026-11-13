import { Suspense, lazy } from "react";
import { useRoute } from "./global/router";
import GlobalHome from "./global/GlobalHome";

// Each view is its own chunk. The global home must not download the theatre's map stack, and a
// country view must not download the theatre at all: payload discipline per system is the point
// of the manifest (iteration 14).
const TheatreApp = lazy(() => import("./App"));
const CountryView = lazy(() => import("./global/CountryView"));
const GroupView = lazy(() => import("./global/GroupView"));
const CompareView = lazy(() => import("./global/CompareView"));

export default function Root() {
  const route = useRoute();
  return (
    <Suspense fallback={<p className="dim" role="status" style={{ padding: 20 }}>Loading…</p>}>
      {route.view === "home" && <GlobalHome />}
      {route.view === "theatre" && <TheatreApp />}
      {/* Keyed on the id so switching countries remounts cleanly and aborts the old load. */}
      {route.view === "country" && <CountryView key={route.id} id={route.id} />}
      {route.view === "group" && <GroupView key={route.id} id={route.id} />}
      {/* Not keyed: an edit to the selection keeps the countries already loaded. */}
      {route.view === "compare" && <CompareView ids={route.ids} />}
    </Suspense>
  );
}
