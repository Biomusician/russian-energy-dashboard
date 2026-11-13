import { useEffect, useMemo, useRef, useState } from "react";
import SystemSwitcher from "./SystemSwitcher";
import { loadContext, type EnergyContext } from "./context";
import { loadCountrySystem, loadManifest, type CountrySystem, type Manifest } from "./manifest";
import { MAX_COMPARE, hrefFor, navigate, navigateCompare } from "./router";
import {
  compareBriefLines, compareFilename, compareRows, resolveCompare, MATURITY_DEFINITION,
  type CompareColumn, type CompareRow, type RowBasis,
} from "./compare";
import { canvasPng, drawCompareFrame } from "./compareExport";
import { downloadBlob } from "../mapExport";
import { fmtDate } from "../data";
import "../styles/compare.css";

/** The comparison workspace (iteration 21): two to four monitored systems side by side, on the
 *  dimensions that mean the same thing in each. See compare.ts for what is never compared and why.
 *
 *  The URL is the only state: every edit rewrites `?compare=` and the view re-reads it, so what the
 *  reader sees is always what a copied link opens. Columns stay in the reader's order. */

const GROUP_HEAD: Record<RowBasis, { title: string; note: string }> = {
  common: { title: "Common basis: one definition for every system",
            note: "Each row means the same thing in every column." },
  context: { title: "National energy context: one source, one year",
             note: "Annual national totals, for context only. A larger figure is not a more important or more disrupted country." },
  within: { title: "Within each system only: not a comparison",
            note: "True inside its own column. Shown so a reader can judge each record, not to set the columns against each other." },
};

type Loaded = Record<string, { status: "loaded" | "failed"; system: CountrySystem | null }>;

export default function CompareView({ ids }: { ids: string[] }) {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [manifestFailed, setManifestFailed] = useState(false);
  const [ctx, setCtx] = useState<EnergyContext | null>(null);
  const [ctxFailed, setCtxFailed] = useState(false);
  const [loaded, setLoaded] = useState<Loaded>({});
  const [exportMsg, setExportMsg] = useState<string | null>(null);

  useEffect(() => {
    document.title = "Energy Disruption Monitor — compare systems";
    loadManifest().then(setManifest).catch(() => setManifestFailed(true));
    loadContext().then(setCtx).catch(() => setCtxFailed(true));
  }, []);

  const resolved = useMemo(() => (manifest ? resolveCompare(ids, manifest) : null), [ids, manifest]);
  const columnIds = (resolved?.columns ?? []).map((s) => s.id).join(",");

  // Each country's own system.json, once per visit. Adding, removing or moving a column never
  // reloads or abandons another: a load in flight finishes even if its column was removed (the file
  // is small, and it is ready if the reader adds it back). Only leaving the page aborts.
  const started = useRef(new Set<string>());
  const ctl = useRef(new AbortController());
  useEffect(() => {
    const c = new AbortController();
    ctl.current = c;
    started.current.clear();
    return () => c.abort();
  }, []);
  useEffect(() => {
    if (!resolved) return;
    const signal = ctl.current.signal;
    for (const entry of resolved.columns) {
      if (entry.kind !== "country" || started.current.has(entry.id)) continue;
      started.current.add(entry.id);
      loadCountrySystem(entry)
        .then((system) => setLoaded((l) => ({ ...l, [entry.id]: { status: "loaded", system } })))
        .catch(() => {
          if (!signal.aborted) setLoaded((l) => ({ ...l, [entry.id]: { status: "failed", system: null } }));
        });
    }
  }, [columnIds]);  // eslint-disable-line react-hooks/exhaustive-deps

  const cols: CompareColumn[] = (resolved?.columns ?? []).map((entry) => {
    if (entry.kind === "theatre") return { entry, system: null, status: "theatre" };
    const l = Object.prototype.hasOwnProperty.call(loaded, entry.id) ? loaded[entry.id] : null;
    return { entry, system: l?.system ?? null, status: l?.status ?? "loading" };
  });
  const rows = compareRows(cols, ctx, manifest, ctxFailed);
  const chosen = cols.map((c) => c.entry.id);
  const addable = (manifest?.systems ?? []).filter((s) => !chosen.includes(s.id));

  const edit = (next: string[]) => { setExportMsg(null); navigateCompare(next, true); };
  const move = (i: number, d: -1 | 1) => {
    const next = [...chosen];
    [next[i], next[i + d]] = [next[i + d], next[i]];
    edit(next);
  };

  const runExport = async () => {
    if (!manifest || cols.length < 2) { setExportMsg("Choose at least two systems first."); return; }
    if (cols.some((c) => c.status === "loading") || (!ctx && !ctxFailed)) { setExportMsg("Still loading; try again in a moment."); return; }
    try {
      const brief = compareBriefLines(cols, rows, ctx, manifest.build_time);
      const blob = await canvasPng(drawCompareFrame(brief));
      downloadBlob(blob, compareFilename(cols, manifest.build_time));
      setExportMsg("Exported 1600×900.");
    } catch (err) {
      setExportMsg(err instanceof Error ? err.message : String(err));
    }
  };

  const groups: RowBasis[] = ["common", "context", "within"];

  return (
    <div className="global-page compare-page">
      <header className="global-head">
        <div>
          <h1 className="ribbon-title">Compare systems</h1>
          <div className="ribbon-sub">Energy Disruption Monitor · research state and national context, side by side · open sources only</div>
        </div>
        <div className="head-actions">
          <button className="ghost" onClick={runExport} disabled={cols.length < 2}>Download comparison (PNG)</button>
          <SystemSwitcher current={null} />
        </div>
      </header>
      <main className="global-main">
        <section className="panel global-note compare-intro" aria-label="What this comparison is">
          <p>
            <strong>Up to {MAX_COMPARE} systems, in the order you choose.</strong> Only dimensions with a common basis sit
            across the columns: whether an index exists, how far research has got, which publication safeguards apply,
            how precisely a record is placed, and national energy context from one source and one year.
          </p>
          <p className="small"><strong>Not compared here:</strong> event counts, attack counts, records held back,
            severity, and any order of systems. They depend on each system's reporting rules and research, so side by
            side they would read as a ranking of disruption. Each system's own page has its record.</p>
          <p className="small dim">{NO_INDEX_NOTE}</p>
        </section>

        {manifestFailed && <p className="warn-text" role="alert">The list of systems could not be loaded, so nothing can be compared. <a href="?">Open the overview</a>.</p>}
        {resolved && resolved.unknown.length > 0 && (
          <p className="warn-text small" role="status">
            Not recognised and left out: {resolved.unknown.map((u) => `“${u.length > 32 ? `${u.slice(0, 32)}…` : u}”`).join(", ")}.
            Choose a system from the list below.
          </p>
        )}
        {resolved && resolved.over.length > 0 && (
          <p className="warn-text small" role="status">At most {MAX_COMPARE} systems can be compared at once; left out: {resolved.over.join(", ")}.</p>
        )}

        <div className="compare-picker">
          <label className="small">Add a system{" "}
            <select aria-label="Add a system to compare" value="" disabled={!manifest || chosen.length >= MAX_COMPARE}
                    onChange={(e) => { if (e.target.value) edit([...chosen, e.target.value]); }}>
              <option value="">{chosen.length >= MAX_COMPARE ? `${MAX_COMPARE} chosen (the most)` : "Choose…"}</option>
              {addable.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </label>
          {manifest && cols.length < 2 && (
            <p className="small" role="status">Choose at least two systems to compare{cols.length === 1 ? `: ${cols[0].entry.name} is chosen` : ""}.</p>
          )}
        </div>
        {exportMsg && <p className="small" role="status">{exportMsg}</p>}

        {cols.length >= 2 && (
          <section aria-label="Comparison table" className="compare-section">
            <p className="small phone-only compare-scroll-cue" aria-hidden="true">Scroll sideways to see every system →</p>
            <div className="compare-scroll" tabIndex={0} role="region" aria-label="Comparison table, scrolls sideways on a narrow screen">
              <table className="compare-table">
                <caption className="small dim">
                  Columns in the order you chose, never sorted by a figure. A cell that has no figure says why; none is a zero.
                </caption>
                <thead>
                  <tr>
                    <th scope="col" className="compare-corner">Dimension</th>
                    {cols.map((c, i) => (
                      <th scope="col" key={c.entry.id} className="compare-colhead">
                        <a href={hrefFor(c.entry.id)} onClick={(e) => { if (!e.ctrlKey && !e.metaKey && !e.shiftKey) { e.preventDefault(); navigate(c.entry.id); } }}>
                          {c.entry.name}
                        </a>
                        <div className="compare-col-actions">
                          <button className="ghost" onClick={() => move(i, -1)} disabled={i === 0}
                                  aria-label={`Move ${c.entry.name} left`} title="Move left">←</button>
                          <button className="ghost" onClick={() => move(i, 1)} disabled={i === cols.length - 1}
                                  aria-label={`Move ${c.entry.name} right`} title="Move right">→</button>
                          <button className="ghost" onClick={() => edit(chosen.filter((x) => x !== c.entry.id))}
                                  aria-label={`Remove ${c.entry.name}`}>Remove</button>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                {groups.map((g) => (
                  <tbody key={g} className={`compare-group compare-basis-${g}`}>
                    <tr className="compare-group-head">
                      <th scope="colgroup" colSpan={cols.length + 1}>
                        <div className="compare-group-inner">
                        <span className="compare-group-title">{GROUP_HEAD[g].title}</span>{" "}
                        <span className="dim">{GROUP_HEAD[g].note}</span>
                        {g === "context" && ctx && (
                          <div className="small dim">
                            Source: <a href={ctx.source.url} target="_blank" rel="noreferrer">{ctx.source.name}</a>, release of {fmtDate(ctx.source.release)};
                            year {ctx.comparison_year} for every country. "No data" is not zero.
                          </div>
                        )}
                        {g === "context" && ctxFailed && <div className="small warn-text">National context could not be loaded.</div>}
                        </div>
                      </th>
                    </tr>
                    {rows.filter((r) => r.basis === g).map((r) => <RowView key={r.id} row={r} />)}
                  </tbody>
                ))}
              </table>
            </div>
            <details className="small">
              <summary>Research preview and monitored: what the words mean</summary>
              <p>{MATURITY_DEFINITION}</p>
            </details>
          </section>
        )}
      </main>
    </div>
  );
}

const NO_INDEX_NOTE = "No index is not a zero. The one index on this site belongs to a single monitored area and is " +
  "built for it alone; it is not comparable with any other system, so its value is not shown here.";

function RowView({ row }: { row: CompareRow }) {
  return (
    <tr className={`compare-row compare-row-${row.basis}`} data-row={row.id}>
      <th scope="row">
        <span className="compare-row-label">{row.label}</span>
        <span className={`compare-basis-tag basis-${row.basis}`}>
          {row.basis === "common" ? "Common basis" : row.basis === "context" ? "Same source and year" : "Within this system"}
        </span>
        <details className="compare-def">
          <summary>Definition</summary>
          <span>{row.basisNote}</span>
        </details>
      </th>
      {row.cells.map((cell, i) => (
        <td key={i} data-kind={cell.kind}>
          <span className="compare-cell-text">{cell.text}</span>
          {cell.detail && (
            <details className="compare-more">
              <summary>More</summary>
              <span>{cell.detail}</span>
            </details>
          )}
        </td>
      ))}
    </tr>
  );
}
