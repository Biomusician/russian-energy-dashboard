/** Responsive layout classification (hotfix §3/§4).
 *
 *  WHY A HOOK AND NOT PURE MEDIA QUERIES. Two reasons, both structural:
 *
 *  1. The mode depends on HEIGHT as well as width. A 1600x700 viewport and a 1600x1000 one must
 *     not get the same chrome — the ribbon and timeline cost the same absolute pixels in both,
 *     so they eat twice the proportion of the short one. Width-only rules cannot see that.
 *  2. The mode drives React behaviour (docked panel vs overlay drawer, and whether MapLibre must
 *     be told to resize), not just paint. Deriving it twice — once in CSS, once in JS — is how
 *     the two quietly disagree.
 *
 *  So it is computed once here, written to `document.documentElement[data-layout]` for CSS to
 *  react to, and returned for components to branch on.
 *
 *  THRESHOLDS ARE DERIVED, NOT CHOSEN. See docs/RESPONSIVE_LAYOUT_HOTFIX.md. The rule is: a mode
 *  is only allowed if it still meets the map-area target for that viewport class. `wide` keeps
 *  both rails docked, which costs ~530-640px of width; below ~1560px that leaves the map under
 *  its target, so the dossier undocks. Below ~1120px even one rail is too expensive, so both do.
 */

import { useEffect, useState } from "react";

export type LayoutMode = "wide" | "compact" | "narrow";

/** Below this width, two docked rails push the map under its area target. */
const WIDE_MIN_WIDTH = 1560;
/** Below this height, the fixed-cost ribbon + timeline make a docked dossier too expensive. */
const WIDE_MIN_HEIGHT = 760;
/** Below either of these, even the filters rail must undock. */
const NARROW_MAX_WIDTH = 1120;
const NARROW_MAX_HEIGHT = 560;

export function classifyLayout(width: number, height: number): LayoutMode {
  if (width < NARROW_MAX_WIDTH || height < NARROW_MAX_HEIGHT) return "narrow";
  if (width < WIDE_MIN_WIDTH || height < WIDE_MIN_HEIGHT) return "compact";
  return "wide";
}

function currentMode(): LayoutMode {
  if (typeof window === "undefined") return "wide";
  return classifyLayout(window.innerWidth, window.innerHeight);
}

export function useLayoutMode(): LayoutMode {
  const [mode, setMode] = useState<LayoutMode>(currentMode);

  useEffect(() => {
    let timer = 0;
    const update = () => {
      window.clearTimeout(timer);
      // Coalesce: a live window drag fires resize continuously, and re-rendering the whole shell
      // per event is how a smooth drag becomes a stutter.
      //
      // A TIMER, not requestAnimationFrame. rAF does not run in a hidden or background tab, so a
      // rAF-coalesced classifier silently stops classifying whenever the tab is not visible —
      // and then paints a stale layout on the frame the user returns to.
      timer = window.setTimeout(
        () => setMode(classifyLayout(window.innerWidth, window.innerHeight)), 16);
    };
    window.addEventListener("resize", update);
    window.addEventListener("orientationchange", update);
    // A ResizeObserver on the root element as well as the resize event. The event is not fired
    // in every situation that changes the CSS viewport — browser zoom and devtools/emulated
    // viewport changes can alter innerWidth/innerHeight without one — and a layout that only
    // reclassifies on `resize` then keeps a mode that no longer fits the screen.
    const ro = new ResizeObserver(update);
    ro.observe(document.documentElement);
    update();
    return () => {
      window.clearTimeout(timer);
      ro.disconnect();
      window.removeEventListener("resize", update);
      window.removeEventListener("orientationchange", update);
    };
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-layout", mode);
  }, [mode]);

  return mode;
}
