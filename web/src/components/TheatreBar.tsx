/** The theatre's top bar: where am I, how do I get back, which view am I in, and the tools.
 *
 *  A first-time reader could not answer any of those four from the old ribbon. The way home was
 *  an option inside the system picker; Map focus was a button on the map and Briefing a button in
 *  the ribbon, with nothing saying they were related; and five equal-weight buttons carried no
 *  hierarchy. This bar is presentation only — every control calls state that lives in App.
 */

import { useEffect, useRef, useState } from "react";
import SystemSwitcher from "../global/SystemSwitcher";
import { loadManifest } from "../global/manifest";
import { navigate } from "../global/router";
import { MODES, MODE_LABEL, type TheatreMode } from "../theatreMode";

/** The theatre's reader-facing name. Read from the manifest so the header, the system picker
 *  and the document title can never disagree; the fallback is only for the moment before the
 *  manifest arrives (or if it fails), and matches the manifest's own entry. */
export const THEATRE_FALLBACK_NAME = "Russia, Belarus & Crimea";

export function useTheatreName(): string {
  const [name, setName] = useState(THEATRE_FALLBACK_NAME);
  useEffect(() => {
    let live = true;
    loadManifest()
      .then((m) => {
        const entry = m.systems.find((s) => s.kind === "theatre");
        if (live && entry?.name) setName(entry.name);
      })
      .catch(() => {});
    return () => { live = false; };
  }, []);
  return name;
}

export interface TheatreTool {
  label: string;
  /** What the button reads while its panel is open, so the reader sees what is on. */
  pressedLabel?: string;
  onClick: () => void;
  pressed?: boolean;
}

export default function TheatreBar({
  name, mode, onMode, tools,
}: {
  name: string;
  mode: TheatreMode;
  onMode: (m: TheatreMode) => void;
  tools: TheatreTool[];
}) {
  // On narrow screens the tools fold behind one toggle. On wide screens the toggle is hidden by
  // CSS and the tools are always shown, so this flag only matters where the toggle exists.
  const [toolsOpen, setToolsOpen] = useState(false);
  const toolsRef = useRef<HTMLDivElement | null>(null);

  const toggleRef = useRef<HTMLButtonElement | null>(null);
  // Closing the folded menu hides the button that had focus. Without this the focus fell to
  // <body>, and a panel opened from the menu then had nothing to return focus to (iteration 21).
  const closeTools = () => {
    const inMenu = !!toolsRef.current?.contains(document.activeElement);
    setToolsOpen(false);
    if (inMenu && toggleRef.current && toggleRef.current.offsetParent !== null) toggleRef.current.focus();
  };

  useEffect(() => {
    if (!toolsOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") closeTools(); };
    const onDown = (e: MouseEvent) => {
      const t = e.target as Node;
      if (toolsRef.current && !toolsRef.current.contains(t)
          && !(t instanceof Element && t.closest(".tb-tools-toggle"))) setToolsOpen(false);
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onDown);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onDown);
    };
  }, [toolsOpen]);

  return (
    <div className="theatre-bar">
      <div className="tb-where">
        <h1 className="tb-title">Energy Disruption Monitor</h1>
        <nav aria-label="Breadcrumb" className="tb-crumbs">
          <a href="?" onClick={(e) => { e.preventDefault(); navigate(null); }}
             title="Overview of every monitored system">Home</a>
          <span aria-hidden="true" className="tb-sep">›</span>
          <span aria-current="page" className="tb-here"
                title="Belarus, western Russia and the Siberian Federal District, plus occupied Crimea, at administrative-region level">
            {name}
          </span>
        </nav>
      </div>

      <SystemSwitcher current="ru" />

      <div className="mode-switch" role="group" aria-label="View">
        {MODES.map((m) => (
          <button
            key={m}
            type="button"
            aria-pressed={mode === m}
            aria-label={MODE_LABEL[m].label}
            title={MODE_LABEL[m].hint}
            onClick={() => onMode(m)}
          >
            <span className="ms-long" aria-hidden="true">{MODE_LABEL[m].label}</span>
            <span className="ms-short" aria-hidden="true">{MODE_LABEL[m].short}</span>
          </button>
        ))}
      </div>

      <button
        ref={toggleRef}
        type="button"
        className="tb-tools-toggle"
        aria-expanded={toolsOpen}
        aria-controls="theatre-tools"
        onClick={() => setToolsOpen((v) => !v)}
      >
        Tools
      </button>
      <div id="theatre-tools" ref={toolsRef} className={`tb-tools${toolsOpen ? " open" : ""}`}>
        {tools.map((t) => (
          <button
            key={t.label}
            type="button"
            className="ghost"
            aria-pressed={t.pressed}
            onClick={() => { closeTools(); t.onClick(); }}
          >
            {t.pressed && t.pressedLabel ? t.pressedLabel : t.label}
          </button>
        ))}
      </div>
    </div>
  );
}
