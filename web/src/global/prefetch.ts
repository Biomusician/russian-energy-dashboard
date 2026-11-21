/** Starting downloads earlier, without downloading more (iteration 21).
 *
 *  WHY. Measured before this file existed, a country link opened as a chain: the app script, then
 *  the view's chunk, then the manifest, then the country's files, each waiting for the one before.
 *  Each step here starts as soon as the route is known, in parallel with the view's code:
 *
 *  - `prefetchRoute` runs when a route is entered and fetches exactly the files that route's view
 *    will ask for. The views still ask; they get the same request (manifest.ts holds one per file).
 *  - `prefetchSystem` runs on an explicit hover or focus of a link to one system: that system's
 *    view code and payload, never every system's.
 *
 *  A prefetch never reports a failure. The view's own load does, and a failed request is not kept.
 */

import { groupBySlug, loadCountry, loadGroupContext, loadManifest, loadWorld, prefetchCountry } from "./manifest";
import { prefetchBundle } from "../data";
import type { Route } from "./router";

// The lazy views' chunks. Root builds its lazy components from these, so a prefetch and a render
// ask the module loader for the same chunk.
export const importTheatre = () => import("../App");
export const importCountryView = () => import("./CountryView");
export const importGroupView = () => import("./GroupView");

const quiet = (p: Promise<unknown>) => { p.catch(() => undefined); };

export function prefetchRoute(route: Route): void {
  // Every view's header has the system picker, which reads the manifest.
  quiet(loadManifest());
  if (route.view === "home") {
    // Not the national figures (iteration 23): the default map does not use them, so they load
    // when the reader turns to the national-energy mode or opens a part that shows them.
    quiet(loadWorld());
  } else if (route.view === "country") {
    quiet(loadManifest().then((m) => {
      const e = m.systems.find((s) => s.id === route.id && s.kind === "country");
      return e ? loadCountry(e) : undefined;
    }));
  } else if (route.view === "group") {
    quiet(loadWorld());
    quiet(loadManifest().then((m) => {
      const g = groupBySlug(m, route.id);
      return g?.group.context ? loadGroupContext(g.group.context) : undefined;
    }));
  } else if (route.view === "theatre") {
    prefetchBundle();
  } else if (route.view === "impacts") {
    // The corpus starts downloading beside the atlas's code. A dynamic import, so the loader is in
    // no other route's bundle, and this is the ONLY branch that asks for the impact files: the
    // home page fetches none of them.
    quiet(import("./impacts/load").then((m) => m.loadImpacts()));
  } else if (route.view === "help") {
    // Help's own small file, beside its code. Never the snapshot or the impact corpus.
    quiet(import("./help/facts").then((m) => m.loadHelpFacts()));
  }
}

/** For a link to one system: its view's code and, for a country, its three files. The theatre's
 *  data is 3 MB, so a hover fetches only its code. */
export function prefetchSystem(id: string): void {
  if (id === "ru") {
    quiet(importTheatre());
    return;
  }
  quiet(importCountryView());
  prefetchCountry(id);
}

/** Props for any element that opens a system: prefetch on pointer hover or keyboard focus. */
export function prefetchOn(id: string) {
  return { onPointerEnter: () => prefetchSystem(id), onFocus: () => prefetchSystem(id) };
}
