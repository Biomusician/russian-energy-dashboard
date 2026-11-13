/** The theatre's three views, named for what a reader is doing.
 *
 *  They are not new state. "Map focus" and "Briefing" already existed as two booleans in App, and
 *  a first-time reader had to find them in two different places (a button on the map and one in
 *  the ribbon) without being told that Briefing sits on top of Map focus. The mode is DERIVED from
 *  those booleans, so nothing about the existing behaviour, restore-on-exit, or URL state changes:
 *
 *    analyze  panels docked where the screen allows — the default workspace
 *    focus    the map maximised; panels become drawers
 *    brief    presentation framing and export, on top of map focus
 *
 *  None of the three is written to the URL, and switching between them never touches the
 *  selection, filters, date, camera or comparison tray — a shared link reproduces the same view
 *  whichever mode its sender was in.
 */

export type TheatreMode = "analyze" | "focus" | "brief";

export function modeOf(mapFocus: boolean, briefing: boolean): TheatreMode {
  if (briefing) return "brief";
  return mapFocus ? "focus" : "analyze";
}

export const MODE_LABEL: Record<TheatreMode, { label: string; short: string; hint: string }> = {
  analyze: {
    label: "Analyze",
    short: "Analyze",
    hint: "Layers, map and the region dossier side by side where the screen allows.",
  },
  focus: {
    label: "Map focus",
    short: "Focus",
    hint: "Maximise the map. Layers and the dossier open as drawers.",
  },
  brief: {
    label: "Briefing & export",
    short: "Brief",
    hint: "Presentation frame with its caveats, sources and date, and PNG export.",
  },
};

export const MODES: TheatreMode[] = ["analyze", "focus", "brief"];
