/** Responsive chrome: drawer toggles, the Map focus control, and the dismissal scrim.
 *
 *  Kept in one small component rather than scattered through App so there is a single place
 *  that answers "what controls exist in this layout mode, and what do they do". Everything here
 *  is presentation over state that lives in App — no panel state is duplicated (§7).
 *
 *  Accessibility (§22): every control is a real <button> with `aria-expanded`/`aria-controls`
 *  or `aria-pressed`. The drawers are non-modal, so focus is NOT trapped — Escape dismisses
 *  (handled in App) and the scrim gives a pointer route out.
 *
 *  Focus return (iteration 17): when a drawer closes by any route -- its close button, Escape, the
 *  scrim -- focus goes back to the toggle that opens it, if focus was inside the drawer or lost to
 *  <body>. Without it a keyboard reader who pressed Escape landed at the top of the document.
 */

import { useEffect, useRef } from "react";
import type { LayoutMode } from "../useLayoutMode";

/** Return focus to `toggle` when `open` goes true -> false and focus was in `panelId` or lost. */
function useFocusReturn(open: boolean, panelId: string, toggle: React.RefObject<HTMLButtonElement | null>) {
  const was = useRef(open);
  useEffect(() => {
    if (was.current && !open) {
      const active = document.activeElement;
      const panel = document.getElementById(panelId);
      if (!active || active === document.body || (panel && panel.contains(active))) {
        toggle.current?.focus();
      }
    }
    was.current = open;
  }, [open, panelId, toggle]);
}

export function LayoutChrome({
  mode,
  mapFocus,
  onToggleMapFocus,
  filtersIsDrawer,
  dossierIsDrawer,
  filtersOpen,
  dossierOpen,
  onToggleFilters,
  onToggleDossier,
  onCloseDrawers,
  activeFilterCount,
  hasSelection,
}: {
  mode: LayoutMode;
  mapFocus: boolean;
  onToggleMapFocus: () => void;
  filtersIsDrawer: boolean;
  dossierIsDrawer: boolean;
  filtersOpen: boolean;
  dossierOpen: boolean;
  onToggleFilters: () => void;
  onToggleDossier: () => void;
  onCloseDrawers: () => void;
  activeFilterCount: number;
  hasSelection: boolean;
}) {
  const filtersToggle = useRef<HTMLButtonElement | null>(null);
  const dossierToggle = useRef<HTMLButtonElement | null>(null);
  useFocusReturn(filtersOpen, "filters-panel", filtersToggle);
  useFocusReturn(dossierOpen, "dossier-panel", dossierToggle);
  const anyDrawerOpen = (filtersIsDrawer && filtersOpen) || (dossierIsDrawer && dossierOpen);

  return (
    <>
      {/* The scrim sits inside the shell (which is position:relative), so it darkens the map
          without covering the ribbon or the timeline scrubber — both stay usable with a drawer
          open. It is a button so it is reachable and announced, not a bare clickable div. */}
      {anyDrawerOpen && (
        <button
          className="drawer-scrim"
          aria-label="Close panel"
          onClick={onCloseDrawers}
        />
      )}

      <div className="drawer-toggles">
        {filtersIsDrawer && (
          <button
            ref={filtersToggle}
            className="drawer-btn"
            aria-expanded={filtersOpen}
            aria-controls="filters-panel"
            onClick={onToggleFilters}
          >
            Layers
            {activeFilterCount > 0 && <span className="count">{activeFilterCount}</span>}
          </button>
        )}
      </div>

      <div className="drawer-toggles right">
        {dossierIsDrawer && (
          <button
            ref={dossierToggle}
            className="drawer-btn"
            aria-expanded={dossierOpen}
            aria-controls="dossier-panel"
            onClick={onToggleDossier}
          >
            {hasSelection ? "Dossier" : "Overview"}
          </button>
        )}
        {/* Visible control is mandatory, not just the shortcut — a demo operator should not have
            to know a keybinding. The shortcut is a convenience on top. */}
        <button
          className="drawer-btn"
          aria-pressed={mapFocus}
          title="Maximise the map (M)"
          onClick={onToggleMapFocus}
        >
          {mapFocus ? "Exit map focus" : "Map focus"}
        </button>
      </div>

      <span className="sr-only" aria-live="polite">
        {`Layout: ${mode}${mapFocus ? ", map focus on" : ""}`}
      </span>
    </>
  );
}
