/** Two-date comparison workspace (iteration 11 P6; two histories since iteration 16).
 *
 *  TWO QUESTIONS, NEVER ONE SERIES. "Current reconstruction" answers "what does today's dataset
 *  and model estimate for the system at date A versus date B" (history_series.json). "As
 *  published" answers "what did the dashboard actually serve on date A and on date B"
 *  (production_history.json, read from deployed commits). The reader picks one; the panel says
 *  which, in the pipeline's own words, and the two are never drawn as one line. Before the first
 *  deployed build, as-published is "unavailable" — never a reconstruction relabelled.
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
import type { Bundle, HistorySeries, Incident, ProductionHistory, PublishedBuild, ResolvedPoint } from "../types";
import {
  asPublishedOn, firstServedBetween, fmtDate, fmtDelta, fmtNum, loadHistorySeries,
  loadProductionHistory, resolvePoint, titleCase,
} from "../data";
import type { InspectTarget } from "./Inspector";

export type CompareMode = "A" | "B" | "delta";
/** Which historical question the workspace answers. Defaults to the reconstruction. */
export type HistoryConcept = "reconstruction" | "published";

export interface CompareState {
  a: string;
  b: string;
  mode: CompareMode;
  history?: HistoryConcept;
}

export const CONCEPT_LABEL: Record<HistoryConcept, string> = {
  reconstruction: "Current reconstruction",
  published: "As published",
};

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
  const [published, setPublished] = useState<ProductionHistory | null | "loading">("loading");
  useEffect(() => {
    let live = true;
    loadHistorySeries().then((h) => { if (live) setHistory(h); });
    loadProductionHistory().then((h) => { if (live) setPublished(h); });
    return () => { live = false; };
  }, []);
  const concept: HistoryConcept = state.history ?? "reconstruction";

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

  const selector = (
    <div className="cmp-modes history-concept" role="group" aria-label="Which history">
      <span className="eyebrow">History</span>
      {(["reconstruction", "published"] as HistoryConcept[]).map((c) => (
        <button key={c} className={`seg${concept === c ? " on" : ""}`} aria-pressed={concept === c}
                onClick={() => onChange({ ...state, history: c })}>
          {CONCEPT_LABEL[c]}
        </button>
      ))}
    </div>
  );

  if (concept === "published") {
    return (
      <div className="comparison">
        <div className="section-head">
          <div>
            <h2 style={{ fontSize: 13 }}>Compare system state</h2>
            <div className="eyebrow" style={{ marginTop: 3 }}>what the dashboard served on two dates</div>
          </div>
          <button className="ghost" onClick={onClose}>close</button>
        </div>
        {selector}
        <PublishedComparison published={published} a={state.a} b={state.b}
                             onChange={(a, b) => onChange({ ...state, a, b })} />
      </div>
    );
  }

  return (
    <div className="comparison">
      <div className="section-head">
        <div>
          <h2 style={{ fontSize: 13 }}>Compare system state</h2>
          <div className="eyebrow" style={{ marginTop: 3 }}>current-evidence reconstruction at two dates</div>
        </div>
        <button className="ghost" onClick={onClose}>close</button>
      </div>
      {selector}

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

const LINEAGE_LABEL: Record<PublishedBuild["lineage"], string> = {
  deployed: "deploy recorded by Vercel",
  deploy_status_unverified: "deploy recorded; final status not fetched",
  bot_refresh_presumed_deployed: "daily refresh, presumed deployed (not yet in the ledger)",
};

/** As published: the builds actually served on A and on B, read from deployed commits. Headline
 *  figures only — no regional map exists for a past build, so none is drawn. */
function PublishedComparison({ published, a, b, onChange }: {
  published: ProductionHistory | null | "loading";
  a: string;
  b: string;
  onChange: (a: string, b: string) => void;
}) {
  if (published === "loading") return <div className="empty" style={{ padding: 16 }}>Loading publication history…</div>;
  if (!published || !published.entries.length) {
    return (
      <div className="semantics-note published-unavailable">
        As-published history is not available in this payload
        {published?.unavailable_reason ? `: ${published.unavailable_reason}` : "."}
      </div>
    );
  }
  const first = published.earliest_reliable_as_published_date ?? published.entries[0].served_from.slice(0, 10);
  const A = asPublishedOn(published, a);
  const B = asPublishedOn(published, b);
  const learned = A && B ? firstServedBetween(published, a, b) : [];
  const d = A && B && A.esdi != null && B.esdi != null ? +(B.esdi - A.esdi).toFixed(2) : null;
  return (
    <>
      <div className="semantics-note">{published.what_this_answers} It is not today's evidence about
        those dates: that is the current reconstruction. Reliable from {fmtDate(first)}, the first
        build recorded as deployed; before that it is unavailable, not reconstructed.</div>
      <div className="cmp-dates">
        {([["A", a], ["B", b]] as const).map(([label, day]) => (
          <label key={label}>
            <span className="eyebrow">Date {label}</span>
            <input type="date" value={day} min={first}
                   onChange={(e) => onChange(label === "A" ? e.target.value : a, label === "B" ? e.target.value : b)} />
          </label>
        ))}
      </div>
      <section className="cmp-block published-builds">
        <h3>Monitored-area ESDI as published</h3>
        <div className="cmp-headline">
          <PublishedCell label="A" day={a} build={A} first={first} />
          <PublishedCell label="B" day={b} build={B} first={first} />
          <div>
            <span className="eyebrow">Δ</span>
            <span className="mono big">{d == null ? "—" : fmtDelta(d)}</span>
          </div>
        </div>
        <p className="small">A published delta mixes everything that changed between two builds:
          time passing, new events, corrections and methodology. The build ledger separates them
          for consecutive builds; across a longer span they are not separable.</p>
      </section>
      {A && B && (
        <section className="cmp-block">
          <h3>Events the dashboard first served after A and by B ({learned.length})</h3>
          <p className="small">Counted by when the dashboard LEARNED of each event, not when it happened.
            An event dated months earlier appears here if research found it in this interval.</p>
          {learned.length > 0 && (
            <ul className="small mono published-learned">{learned.slice(0, 25).map((id) => <li key={id}>{id}</li>)}</ul>
          )}
          {learned.length > 25 && <p className="small">…and {learned.length - 25} more.</p>}
        </section>
      )}
      <p className="small warn-text">The map shows the current build: a past build's regional figures are
        not archived, and a reconstruction drawn under this label would be the confusion this view exists to prevent.</p>
    </>
  );
}

function PublishedCell({ label, day, build, first }: {
  label: string; day: string; build: PublishedBuild | null; first: string;
}) {
  if (!build) {
    return (
      <div className="published-cell unavailable">
        <span className="eyebrow">{label}</span>
        <span className="mono big">—</span>
        <span className="small">Unavailable on {fmtDate(day)}: the first published build was served on {fmtDate(first)}.</span>
      </div>
    );
  }
  return (
    <div className="published-cell">
      <span className="eyebrow">{label} · as published on {fmtDate(day)}</span>
      <span className="mono big">{fmtNum(build.esdi, 2)}</span>
      <span className="small">analytical date {fmtDate(build.as_of)} · {build.incident_total ?? "—"} events</span>
      <span className="small dim">build {build.sha.slice(0, 7)} served from {fmtDate(build.served_from.slice(0, 10))} ·
        {" "}{LINEAGE_LABEL[build.lineage]}</span>
      <span className="small dim">methodology {build.methodology_fingerprint?.slice(0, 8) ?? "not recorded"} ·
        schema {build.schema_version ?? "not recorded"} ·
        {" "}source inputs {build.inputs_fingerprint?.slice(0, 8) ?? "not recorded"} ·
        {" "}event set {build.event_ids_fingerprint?.slice(0, 8) ?? "not recorded"}</span>
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
