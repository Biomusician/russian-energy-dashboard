/** Two-date comparison workspace (iteration 11 P6).
 *
 *  WHAT THIS COMPARES, AND WHAT IT DOES NOT. It answers "what does today's dataset and model
 *  estimate for the system at date A versus date B". It does NOT answer "what did the dashboard
 *  say on date A" — that would need an archive of past builds, and none exists. The distinction
 *  is stated at the top of the panel in the pipeline's own words rather than paraphrased here,
 *  because a paraphrase can drift from what the pipeline actually did.
 *
 *  WHERE THE NUMBERS COME FROM. `history_series.json`, computed inside the scoring loop. This
 *  component performs no methodology arithmetic: it subtracts two published figures to show a
 *  delta and formats the result. It never reconstructs a historical score from incidents, which
 *  is the path by which future evidence leaks into a past date.
 *
 *  VOCABULARY. Deltas are described as modelled exposure moving up or down, never as damage or
 *  repair. A falling index can mean impairment aged out with no repair whatsoever, and the whole
 *  point of this project is not to let a reader assume otherwise.
 */

import { useEffect, useState } from "react";
import type { Bundle, HistorySeries, Incident, ResolvedPoint } from "../types";
import { fmtDate, fmtDelta, fmtNum, loadHistorySeries, resolvePoint, titleCase } from "../data";
import type { InspectTarget } from "./Inspector";

export type CompareMode = "A" | "B" | "delta";

export interface CompareState {
  a: string;
  b: string;
  mode: CompareMode;
}

/** Neutral by construction. "Improved" and "worsened" are claims about the world; these are
 *  claims about a model, which is all the data supports. */
function deltaWord(delta: number): string {
  if (delta > 0) return "higher modelled disruption exposure at B";
  if (delta < 0) return "lower modelled disruption exposure at B";
  return "no change in modelled exposure";
}

export default function Comparison({
  bundle, state, onChange, onClose, selected, onExplain,
}: {
  bundle: Bundle;
  state: CompareState;
  onChange: (s: CompareState) => void;
  onClose: () => void;
  selected: string | null;
  onExplain: (t: InspectTarget) => void;
}) {
  const [history, setHistory] = useState<HistorySeries | null | "loading">("loading");
  useEffect(() => {
    let live = true;
    loadHistorySeries().then((h) => { if (live) setHistory(h); });
    return () => { live = false; };
  }, []);

  if (history === "loading") {
    return <div className="empty" style={{ padding: 24 }}>Loading historical series…</div>;
  }
  if (!history) {
    return (
      <div className="empty" style={{ padding: 24 }}>
        <div className="eyebrow">Comparison unavailable</div>
        <p style={{ lineHeight: 1.6, color: "var(--text-dim)" }}>
          This payload carries no historical series, so there is nothing to compare. Rebuilding
          the dataset will produce one.
        </p>
      </div>
    );
  }

  const A = resolvePoint(history.dates, state.a);
  const B = resolvePoint(history.dates, state.b);
  if (!A || !B) return null;

  const esdiA = history.esdi[A.step];
  const esdiB = history.esdi[B.step];
  const esdiDelta = +(esdiB - esdiA).toFixed(2);

  const region = selected ? bundle.snapshot.regions[selected] : null;
  const regionSeries = selected ? bundle.regional.regions[selected]?.esdi : null;

  // Analytical-time event lists (§14). These describe when things HAPPENED, not when the record
  // learned about them — that is the Build Change Ledger's job, and merging the two would make
  // "added this build" indistinguishable from "occurred this period".
  const between = bundle.incidents.filter(
    (i) => i.date > A.resolved_series_date && i.date <= B.resolved_series_date);
  const contribA = new Set(history.contributing_asset_ids[A.step] ?? []);
  const contribB = new Set(history.contributing_asset_ids[B.step] ?? []);
  const startedContributing = [...contribB].filter((id) => !contribA.has(id));
  const stoppedContributing = [...contribA].filter((id) => !contribB.has(id));

  const nameOf = (id: string) =>
    bundle.assets.find((a) => a.asset_id === id)?.name
    ?? (bundle.snapshot.live_disruptions ?? []).find((d) => d.asset_id === id)?.name
    ?? id;

  return (
    <div className="comparison">
      <div className="section-head">
        <div>
          <h2 style={{ fontSize: 13 }}>Compare system state</h2>
          <div className="eyebrow" style={{ marginTop: 3 }}>two analytical dates</div>
        </div>
        <button className="ghost" onClick={onClose}>close</button>
      </div>

      {/* The single sentence that prevents the major misunderstanding (§9). Rendered from the
          pipeline's own text so the UI cannot describe the comparison differently. */}
      <div className="semantics-note">{history.semantics.headline}</div>

      <div className="cmp-dates">
        <label>
          <span className="eyebrow">Date A</span>
          <input type="date" value={state.a} min={history.dates[0]}
                 max={history.dates[history.dates.length - 1]}
                 onChange={(e) => onChange({ ...state, a: e.target.value })} />
          <ResolvedNote point={A} stepDays={history.step_days} />
        </label>
        <label>
          <span className="eyebrow">Date B</span>
          <input type="date" value={state.b} min={history.dates[0]}
                 max={history.dates[history.dates.length - 1]}
                 onChange={(e) => onChange({ ...state, b: e.target.value })} />
          <ResolvedNote point={B} stepDays={history.step_days} />
        </label>
      </div>

      <div className="cmp-modes" role="group" aria-label="Map view">
        <span className="eyebrow">Map shows</span>
        {(["A", "B", "delta"] as CompareMode[]).map((m) => (
          <button
            key={m}
            className={`seg${state.mode === m ? " on" : ""}`}
            aria-pressed={state.mode === m}
            onClick={() => onChange({ ...state, mode: m })}
          >
            {m === "delta" ? "Δ (B − A)" : `Date ${m}`}
          </button>
        ))}
      </div>

      <section className="cmp-block">
        <h3>Monitored-area ESDI</h3>
        <div className="cmp-headline">
          <div><span className="eyebrow">A</span><span className="mono big">{fmtNum(esdiA, 2)}</span></div>
          <div><span className="eyebrow">B</span><span className="mono big">{fmtNum(esdiB, 2)}</span></div>
          <div>
            <span className="eyebrow">Δ</span>
            <span className={`mono big ${esdiDelta > 0 ? "up" : esdiDelta < 0 ? "down" : ""}`}>
              {fmtDelta(esdiDelta)}
            </span>
          </div>
        </div>
        <p className="cmp-read">{deltaWord(esdiDelta)}.</p>
        <p className="small">{history.semantics.delta_convention}</p>
        <div className="cmp-explain">
          <button className="ghost" onClick={() => onExplain({ kind: "historical", step: A.step })}>
            Explain A
          </button>
          <button className="ghost" onClick={() => onExplain({ kind: "historical", step: B.step })}>
            Explain B
          </button>
        </div>
      </section>

      <section className="cmp-block">
        <h3>Sectors</h3>
        <table className="mini">
          <thead><tr><th>Sector</th><th>A</th><th>B</th><th>Δ</th></tr></thead>
          <tbody>
            {history.covered.map((s) => {
              const a = history.sector_values[s][A.step];
              const b = history.sector_values[s][B.step];
              return (
                <tr key={s}>
                  <td>{bundle.taxonomy.sectors[s] ?? titleCase(s)}</td>
                  <td className="mono">{fmtNum(a, 2)}</td>
                  <td className="mono">{fmtNum(b, 2)}</td>
                  <td className="mono">{fmtDelta(b - a)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="small">
          Sectors with no capacity denominator are excluded from the composite at both dates and
          are not listed here. Their absence is not a zero.
        </p>
      </section>

      {region && regionSeries && (
        <section className="cmp-block">
          <h3>{region.name}</h3>
          <div className="cmp-headline">
            <div><span className="eyebrow">A</span><span className="mono big">{fmtNum(regionSeries[A.step] ?? 0, 2)}</span></div>
            <div><span className="eyebrow">B</span><span className="mono big">{fmtNum(regionSeries[B.step] ?? 0, 2)}</span></div>
            <div>
              <span className="eyebrow">Δ</span>
              <span className="mono big">
                {fmtDelta((regionSeries[B.step] ?? 0) - (regionSeries[A.step] ?? 0))}
              </span>
            </div>
          </div>
          <button className="ghost"
                  onClick={() => onExplain({ kind: "region", code: region.code })}>
            Explain this region at the latest build
          </button>
        </section>
      )}

      <section className="cmp-block">
        <h3>Evidence available by each date</h3>
        <table className="mini">
          <thead><tr><th></th><th>A</th><th>B</th><th>Δ</th></tr></thead>
          <tbody>
            <Row label="Events recorded" a={history.incidents_to_date[A.step]}
                 b={history.incidents_to_date[B.step]} />
            <Row label="Facilities contributing" a={history.contributing_facilities[A.step]}
                 b={history.contributing_facilities[B.step]} />
            <Row label="Recovery observations" a={history.recovery_evidence_to_date[A.step]}
                 b={history.recovery_evidence_to_date[B.step]} />
            <Row label="Full reconstitutions" a={history.reconstitutions_to_date[A.step]}
                 b={history.reconstitutions_to_date[B.step]} />
          </tbody>
        </table>
        <p className="small">
          Counted by when each thing HAPPENED, not by when this dataset learned of it. When a
          record was added or corrected is a separate question, answered by the build ledger.
        </p>
      </section>

      <section className="cmp-block">
        <h3>Between the two dates</h3>
        <EventList
          title={`Events occurring after A and by B (${between.length})`}
          empty="No events occurred in this interval."
          rows={between.slice(0, 25).map((i: Incident) => ({
            key: i.incident_id,
            main: i.asset_name ?? i.asset_id,
            meta: `${fmtDate(i.date)} · ${titleCase(i.cause)}`,
            onClick: () => onExplain({ kind: "incident", incidentId: i.incident_id }),
          }))}
          more={between.length > 25 ? between.length - 25 : 0}
        />
        <EventList
          title={`Contributing at B but not at A (${startedContributing.length})`}
          empty="No facility began contributing in this interval."
          rows={startedContributing.slice(0, 25).map((id) => ({
            key: id, main: nameOf(id), meta: "",
            onClick: () => onExplain({ kind: "facility", assetId: id }),
          }))}
          more={startedContributing.length > 25 ? startedContributing.length - 25 : 0}
        />
        <EventList
          title={`Contributing at A but not at B (${stoppedContributing.length})`}
          empty="No facility stopped contributing in this interval."
          note={"A facility can stop contributing because its impairment decayed with time, not "
                + "only because it was repaired. Decay is not evidence of repair."}
          rows={stoppedContributing.slice(0, 25).map((id) => ({
            key: id, main: nameOf(id), meta: "",
            onClick: () => onExplain({ kind: "facility", assetId: id }),
          }))}
          more={stoppedContributing.length > 25 ? stoppedContributing.length - 25 : 0}
        />
      </section>

      <section className="cmp-block">
        <h3>What controls each date</h3>
        <dl className="kv">
          {history.semantics.controlling_dates.map((c) => (
            <span key={c.concept}>
              <dt>{c.concept}</dt>
              <dd>
                <span className="mono small">{c.field}</span>
                <p className="small">{c.rule}</p>
              </dd>
            </span>
          ))}
        </dl>
        <p className="small warn-text">{history.semantics.what_this_does_not_answer}</p>
      </section>
    </div>
  );
}

function Row({ label, a, b }: { label: string; a: number; b: number }) {
  return (
    <tr>
      <td>{label}</td>
      <td className="mono">{a}</td>
      <td className="mono">{b}</td>
      <td className="mono">{b === a ? "±0" : (b > a ? "+" : "−") + Math.abs(b - a)}</td>
    </tr>
  );
}

function ResolvedNote({ point, stepDays }: { point: ResolvedPoint; stepDays: number | null }) {
  if (point.exact) return <span className="resolved exact">series point</span>;
  return (
    <span className="resolved">
      resolved to {fmtDate(point.resolved_series_date)}
      {stepDays ? ` · ${stepDays}-day series` : ""}
    </span>
  );
}

function EventList({
  title, rows, empty, more, note,
}: {
  title: string;
  rows: { key: string; main: string; meta: string; onClick: () => void }[];
  empty: string;
  more: number;
  note?: string;
}) {
  return (
    <div className="cmp-list">
      <h4>{title}</h4>
      {note && <p className="small">{note}</p>}
      {rows.length === 0 ? (
        <p className="small">{empty}</p>
      ) : (
        <div className="contrib-list">
          {rows.map((r) => (
            <button key={r.key} className="contrib-row plain" onClick={r.onClick}>
              <span className="contrib-name">{r.main}</span>
              <span className="contrib-math">{r.meta}</span>
            </button>
          ))}
        </div>
      )}
      {more > 0 && <p className="small">…and {more} more.</p>}
    </div>
  );
}
