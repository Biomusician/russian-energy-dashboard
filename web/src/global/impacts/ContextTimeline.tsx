import { fmtDate } from "../../data";
import { anyTie, latestCounts, latestEntries } from "./latestOfType";
import { definitionOf, labelOf, lowerLabel, useImpactVocab } from "./vocab";
import type { ContextEntry, ContextMetric, ImpactSource, RegionalContext } from "./types";
import "../../styles/impacts.css";

/** The regional context timeline: the Gulf and the Strait of Hormuz (iteration 22, §10).
 *
 *  Dated statements, newest first, each "<date> · <source> · <claim>". There is NO status flag:
 *  nothing here says "open" or "closed". The newest statement of each type is marked "as of" its
 *  own date; where several share the newest date, every one is marked and the copy says so in the
 *  plural (latestOfType.ts). Older ones are marked "historical statement". A figure is shown with its unit and with
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

/** Where the newest statements of a type sit in the list, seen from an older one. */
export type LaterPlace = "above" | "below" | "above and below";

/** For each older entry, where its type's newest statements are in `ordered` (the list as drawn).
 *  The list is in statement-date order and "latest" goes by "as of", so the newest of a type is not
 *  always above an older one (iteration 23, XL-01: two cards said "listed above" of an entry drawn
 *  below them). */
export function laterPlaces<T extends Pick<ContextEntry, "context_type">>(ordered: readonly T[], latest: Set<T>): Map<T, LaterPlace> {
  const out = new Map<T, LaterPlace>();
  ordered.forEach((e, i) => {
    if (latest.has(e)) return;
    const at = ordered.flatMap((x, j) => (latest.has(x) && x.context_type === e.context_type ? [j] : []));
    const above = at.some((j) => j < i);
    const below = at.some((j) => j > i);
    if (above || below) out.set(e, above && below ? "above and below" : above ? "above" : "below");
  });
  return out;
}

/** The "as of" line. `latestOfType` is how many statements share the type's newest place: 0 for
 *  an older statement, 1 for the one newest, more when several share the newest date. `later` is
 *  where an older statement's newer ones are drawn; without it the line names no direction. */
export function asOfText(e: Pick<ContextEntry, "as_of" | "context_type">, latestOfType: number, later?: LaterPlace): string {
  const type = lowerLabel("context_types", e.context_type);
  if (latestOfType > 1) return `As of ${fmtDate(e.as_of)}: one of the ${latestOfType} most recent ${type} statements on record. Not a current status.`;
  if (latestOfType === 1) return `As of ${fmtDate(e.as_of)}: the most recent ${type} statement on record. Not a current status.`;
  return `Historical statement, as of ${fmtDate(e.as_of)}. ${later ? `A later statement of this type is listed ${later}.` : "A later statement of this type is on record."}`;
}

function Entry({ e, latestOfType, later }: { e: ContextEntry; latestOfType: number; later?: LaterPlace }) {
  const metric = e.metric ? metricText(e.metric) : null;
  return (
    <li className={`ctx-entry${latestOfType > 0 ? " ctx-latest" : " ctx-historical"}`}>
      <div className="ctx-head">
        {/* "As of" leads: it is the date the statement describes. The statement's own date comes
            second, and only where it differs. */}
        <span className="mono ctx-date">As of {fmtDate(e.as_of)}</span>
        {e.date !== e.as_of && <span className="ctx-published"> · statement dated {fmtDate(e.date)}</span>}
        <span className="ctx-source"> · {publishers(e.sources)} · </span>
        <span className="event-tag">{labelOf("context_types", e.context_type)}</span>
      </div>
      <p className="ctx-claim">{e.claim}</p>
      {metric && e.metric && (
        <p className="ctx-metric small">Figure: <strong>{metric}</strong>{e.metric.basis ? ` — ${e.metric.basis}` : ""}</p>
      )}
      <p className="small ctx-asof">{asOfText(e, latestOfType, later)}</p>
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
  const latest = latestEntries(entries, ctx.latest_by_type);
  const counts = latestCounts(entries, latest);
  const later = laterPlaces(entries, latest);
  const tie = anyTie(counts);
  return (
    <section className="ctx-timeline" aria-label={ctx.label}>
      <p className="small">{ctx.statement}</p>
      <div className="ctx-caveat small" role="note">
        <p><strong>{CONTEXT_CAVEAT}</strong></p>
        <p>{ctx.not_built}</p>
      </div>
      {entries.length === 0
        ? <p className="small dim">{ctx.empty_reason ?? "No reviewed statement is published yet. That is an absence of published statements, not a statement that nothing was said."}</p>
        : <ol className="ctx-entries">{entries.map((e) => <Entry key={e.id} e={e} latestOfType={latest.has(e) ? counts.get(e.context_type) ?? 1 : 0} later={later.get(e)} />)}</ol>}
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
      {ctx.latest_note && <p className="small dim">{tie
        ? "“As of” marks the newest statements of each kind by their own date; where several share the newest date, every one of them is marked. Each is among the most recent statements on record, not a current status."
        : "“As of” marks the newest statement of each kind by its own date; it is the most recent statement on record, not a current status."}</p>}
    </section>
  );
}

export default ContextTimeline;
