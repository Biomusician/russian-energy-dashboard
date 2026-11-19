import { fmtDate } from "../../data";
import { definitionOf, labelOf, lowerLabel, useImpactVocab } from "./vocab";
import type { ContextEntry, ContextMetric, ImpactSource, RegionalContext } from "./types";
import "../../styles/impacts.css";

/** The regional context timeline: the Gulf and the Strait of Hormuz (iteration 22, §10).
 *
 *  Dated statements, newest first, each "<date> · <source> · <claim>". There is NO status flag:
 *  nothing here says "open" or "closed". The newest statement of each type is marked "as of" its
 *  own date; older ones are marked "historical statement". A figure is shown with its unit and with
 *  what it measures, in the source's words.
 *
 *  The caveat block is fixed and always rendered: aggregate regional context only; no vessels,
 *  routes or bypass capacity are collected, and why.
 */

export const CONTEXT_CAVEAT = "Aggregate regional context only. No vessels, routes or bypass capacity are collected, "
  + "because this site records publicly stated aggregate effects and is never a tool for tracking shipping or for judging what matters most.";

function hostOf(url: string): string {
  try { return new URL(url).hostname; } catch { return url; }
}

function publishers(sources: readonly ImpactSource[]): string {
  const names: string[] = [];
  for (const s of sources) {
    const n = s.publisher ?? hostOf(s.url);
    if (!names.includes(n)) names.push(n);
  }
  return names.join(", ") || "source not named";
}

/** "about 2.5 mb/d" or "between 2 and 3 mb/d": the figure with the source's unit, never converted. */
export function metricText(m: ContextMetric): string | null {
  if (m.value == null) return null;
  const n = (v: number) => v.toLocaleString("en-GB");
  const unit = m.unit ? ` ${m.unit}` : "";
  if (m.qualifier === "range" && m.value_upper != null) return `between ${n(m.value)} and ${n(m.value_upper)}${unit}`;
  const q = m.qualifier ? labelOf("affected_qualifiers", m.qualifier) : "";
  return `${q ? `${q} ` : ""}${n(m.value)}${unit}`;
}

function Entry({ e }: { e: ContextEntry }) {
  const metric = e.metric ? metricText(e.metric) : null;
  return (
    <li className={`ctx-entry${e.is_latest_of_type ? " ctx-latest" : " ctx-historical"}`}>
      <div className="ctx-head">
        <span className="mono ctx-date">{fmtDate(e.date)}</span>
        <span className="ctx-source"> · {publishers(e.sources)} · </span>
        <span className="event-tag">{labelOf("context_types", e.context_type)}</span>
      </div>
      <p className="ctx-claim">{e.claim}</p>
      {metric && e.metric && (
        <p className="ctx-metric small">Figure: <strong>{metric}</strong>{e.metric.basis ? ` — ${e.metric.basis}` : ""}</p>
      )}
      <p className="small ctx-asof">
        {e.is_latest_of_type
          ? <>As of {fmtDate(e.as_of)}: the most recent {lowerLabel("context_types", e.context_type)} statement on record. Not a current status.</>
          : <>Historical statement, as of {fmtDate(e.as_of)}. A later statement of this type is listed above.</>}
      </p>
      <ul className="ctx-sources small">
        {e.sources.map((s) => (
          <li key={s.ref}>
            <a href={s.url} target="_blank" rel="noopener noreferrer">{s.publisher ?? hostOf(s.url)}</a>
            <span className="dim"> — {lowerLabel("source_roles", s.source_role)}, {lowerLabel("media", s.medium)}
              {s.date ? `, ${fmtDate(s.date)}` : ""}{s.link_check ? `, link ${lowerLabel("link_states", s.link_check)}` : ""}</span>
          </li>
        ))}
      </ul>
    </li>
  );
}

export function ContextTimeline({ ctx }: { ctx: RegionalContext }) {
  useImpactVocab();
  // Newest first by statement date, then id: the served order, re-applied so a reordered file
  // cannot put an old statement on top.
  const entries = [...ctx.entries].sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : a.id < b.id ? -1 : 1));
  const types = ctx.context_types.filter((t) => entries.some((e) => e.context_type === String(t.id)));
  return (
    <section className="ctx-timeline" aria-label={ctx.label}>
      <p className="small">{ctx.statement}</p>
      <div className="ctx-caveat small" role="note">
        <p><strong>{CONTEXT_CAVEAT}</strong></p>
        <p>{ctx.not_built}</p>
      </div>
      {entries.length === 0
        ? <p className="small dim">{ctx.empty_reason ?? "No reviewed statement is published yet. That is an absence of published statements, not a statement that nothing was said."}</p>
        : <ol className="ctx-entries">{entries.map((e) => <Entry key={e.id} e={e} />)}</ol>}
      {types.length > 0 && (
        <details className="ctx-types small">
          <summary>What each kind of statement means</summary>
          <dl>
            {types.map((t) => (
              <div key={String(t.id)}><dt>{t.label}</dt><dd>{definitionOf("context_types", t.id) ?? t.definition ?? ""}</dd></div>
            ))}
          </dl>
        </details>
      )}
      {ctx.latest_note && <p className="small dim">“As of” marks the newest statement of each kind by its own date; it is the most recent statement on record, not a current status.</p>}
    </section>
  );
}

export default ContextTimeline;
