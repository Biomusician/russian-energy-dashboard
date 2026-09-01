/** Responsive chrome: drawer toggles, the Map focus control, and the dismissal scrim.
 *
 *  Kept in one small component rather than scattered through App so there is a single place
 *  that answers "what controls exist in this layout mode, and what do they do". Everything here
 *  is presentation over state that lives in App — no panel state is duplicated (§7).
 *
 *  Accessibility (§22): every control is a real <button> with `aria-expanded`/`aria-controls`
 *  or `aria-pressed`. The drawers are non-modal, so focus is NOT trapped — Escape dismisses
 *  (handled in App) and the scrim gives a pointer route out.
 */

import type { LayoutMode } from "../useLayoutMode";

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
