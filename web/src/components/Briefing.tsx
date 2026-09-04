/** Briefing Mode and PNG export (iteration 11 P8).
 *
 *  BRIEFING MODE IS A PRODUCT STATE, not screenshot CSS. Map Focus strips chrome so someone can
 *  explore; Briefing Mode strips chrome AND adds the framing an audience needs — what the metric
 *  is, what date it describes, what scope it covers, and what it must not be read as. It stays
 *  fully interactive before export, and leaving it restores the panel state the reader had.
 *
 *  EVERY EXPORT CARRIES ITS OWN CONTEXT. The frame drawn here is the frame that gets captured, so
 *  the caveat, scope note and provenance footer are in the pixels rather than in a tooltip the
 *  image leaves behind.
 */

import { useState } from "react";
import type { BriefingContext, BriefingOptions } from "../briefing";
import { briefingFilename } from "../briefing";
import { fmtDate } from "../data";

export default function Briefing({
  ctx, options, onOptions, onExit, onExport, busy, error, lastResult,
}: {
  ctx: BriefingContext;
  options: BriefingOptions;
  onOptions: (o: BriefingOptions) => void;
  onExit: () => void;
  onExport: (size: ExportSize) => void;
  busy: boolean;
  error: string | null;
  lastResult: string | null;
}) {
  const [panelOpen, setPanelOpen] = useState(false);

  return (
    <>
      {/* The presentation frame. This is what the export captures, so everything a detached
          reader needs is here rather than in the surrounding application. */}
      <div className="briefing-frame" aria-hidden={false}>
        {options.title && (
          <header className="brief-head">
            <div>
              <h1>{ctx.title}</h1>
              <p className="brief-metric">{ctx.metricLabel}</p>
            </div>
            <div className="brief-dates">
              {ctx.metricValue && <span className="brief-value">{ctx.metricValue}</span>}
              <span className="brief-asof">
                {ctx.analyticalDate
                  ? <>analytical date {fmtDate(ctx.analyticalDate)}<br />
                      <span className="dim">data as of {fmtDate(ctx.asOf)}</span></>
                  : <>as of {fmtDate(ctx.asOf)}</>}
              </span>
            </div>
          </header>
        )}

        {options.comparisonSummary && ctx.comparison && (
          <div className="brief-compare">
            <div><span className="eyebrow">Date A</span>
              <span className="mono">{fmtDate(ctx.comparison.aResolved)}</span>
              <strong>{ctx.comparison.aValue}</strong></div>
            <div><span className="eyebrow">Date B</span>
              <span className="mono">{fmtDate(ctx.comparison.bResolved)}</span>
              <strong>{ctx.comparison.bValue}</strong></div>
            <div><span className="eyebrow">Δ = B − A</span>
              <span className="mono">&nbsp;</span>
              <strong>{ctx.comparison.delta}</strong></div>
            {ctx.comparison.resolvedNote && (
              <p className="brief-resolved">{ctx.comparison.resolvedNote}</p>
            )}
          </div>
        )}

        {ctx.episode && (
          <div className="brief-episode">
            <span className="eyebrow">Recovery episode</span>
            <strong>{ctx.episode.facility}</strong>
            <span className="dim">
              {ctx.episode.assetClass ? `${ctx.episode.assetClass} · ` : ""}
              disrupted {fmtDate(ctx.episode.disruptionDate)}
            </span>
            <span>{ctx.episode.familyLabel} — {ctx.episode.outcome}</span>
          </div>
        )}

        {options.selectionLabel && ctx.selection && (
          <div className="brief-selection">{ctx.selection}</div>
        )}

        <footer className="brief-foot">
          <p className="brief-caveat">{ctx.caveat}</p>
          {options.scopeNote && <p>{ctx.scopeNote}</p>}
          {options.scopeNote && ctx.crimeaNote && <p>{ctx.crimeaNote}</p>}
          {/* §16: only present when lineage is provable. Absence is silent, never "no prior
              build" — that is a fact about a git repository, not an analytical finding. */}
          {ctx.buildDelta && (
            <p>
              Since last build ({fmtDate(ctx.buildDelta.previousAsOf)} →{" "}
              {fmtDate(ctx.buildDelta.currentAsOf)}): {ctx.buildDelta.delta}
            </p>
          )}
          {options.sourceFooter && <p className="brief-sources">{ctx.sourceFooter}</p>}
        </footer>
      </div>

      {/* Controls. Excluded from the capture and from print. */}
      <div className="brief-controls" data-export-exclude="true">
        <button className="drawer-btn" onClick={onExit}>Exit briefing</button>
        <button className="drawer-btn" aria-pressed={panelOpen}
                onClick={() => setPanelOpen((v) => !v)}>
          Export options
        </button>
        <button className="drawer-btn primary" disabled={busy}
                onClick={() => onExport("viewport")}>
          {busy ? "Rendering…" : "Download PNG"}
        </button>
      </div>

      {panelOpen && (
        <div className="brief-panel" data-export-exclude="true">
          <div className="section-head">
            <h2 style={{ fontSize: 12 }}>Export options</h2>
            <button className="ghost" onClick={() => setPanelOpen(false)}>close</button>
          </div>
          <div className="brief-panel-body">
            <span className="eyebrow">Size</span>
            <div className="cmp-modes">
              {(["viewport", "1920x1080", "2560x1440"] as ExportSize[]).map((s) => (
                <button key={s} className="seg" disabled={busy} onClick={() => onExport(s)}>
                  {s === "viewport" ? "Current viewport" : s.replace("x", " × ")}
                </button>
              ))}
            </div>

            <span className="eyebrow">Include</span>
            {(Object.keys(options) as (keyof BriefingOptions)[]).map((k) => (
              <label key={k} className="brief-opt">
                <input type="checkbox" checked={options[k]}
                       onChange={(e) => onOptions({ ...options, [k]: e.target.checked })} />
                {OPTION_LABEL[k]}
              </label>
            ))}

            <p className="small">
              Filename: <span className="mono">{briefingFilename(ctx)}</span>
            </p>
            {error && <p className="small warn-text">{error}</p>}
            {lastResult && <p className="small">{lastResult}</p>}
          </div>
        </div>
      )}
    </>
  );
}

export type ExportSize = "viewport" | "1920x1080" | "2560x1440";

const OPTION_LABEL: Record<keyof BriefingOptions, string> = {
  title: "Title and headline",
  selectionLabel: "Selected-item label",
  scopeNote: "Scope note",
  legend: "Legend",
  sourceFooter: "Source footer",
  comparisonSummary: "Comparison summary",
};
