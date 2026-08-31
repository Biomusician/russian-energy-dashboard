/** Canonical detail for one pipeline route (iteration 10 §16/§17).
 *
 *  The hover card answers "what is this line". This panel answers the harder questions the
 *  registry exists to make answerable: which real-world entity is it, which sources say so and
 *  how confidently, what was true WHEN, and how much of it is actually mapped.
 *
 *  Three separations are load-bearing here and must not be collapsed in a later tidy-up:
 *
 *   1. TOPOLOGY vs GEOMETRY. `route_length_km` is the route's length as the source describes it;
 *      `drawn_length_km` is what is rendered. The difference is unmapped, not missing pipe.
 *   2. PHYSICAL vs OPERATIONAL vs COMMERCIAL FLOW status. A pipeline can be intact, available,
 *      and carrying nothing, all at the same time. Yamal–Europe is exactly that, and one
 *      "status" field would have to pick a lie.
 *   3. SOURCE IDENTITY vs NAME. Every mapping shows its relationship, confidence and evidence,
 *      so a reader can see that an entity was matched on shareholders or endpoints rather than
 *      on a name that merely looked similar.
 */

import type { PipelineEntity, PipelineStatusRecord } from "../types";
import { fmtNum, titleCase } from "../data";

/** What each status kind actually asserts. Spelled out because the distinction is the point. */
const STATUS_KIND_LABEL: Record<string, { label: string; hint: string }> = {
  physical: { label: "Physical", hint: "Whether the pipe itself is intact. Says nothing about use." },
  operational: { label: "Operational", hint: "Whether it is available to run. Says nothing about volumes." },
  commercial_flow: { label: "Commercial flow", hint: "Whether gas or oil is actually moving under contract." },
};

const CONFIDENCE_COLOR: Record<string, string> = {
  exact: "var(--green, #4a8)",
  strong: "var(--green, #4a8)",
  possible: "var(--amber)",
  unresolved: "var(--amber)",
};

function fmtInterval(s: PipelineStatusRecord) {
  const from = s.valid_from ?? "—";
  const to = s.valid_to ?? "present";
  return `${from} → ${to}`;
}

/** Latest interval per kind, by start date. Deliberately does NOT hide the superseded ones:
 *  the history is the reason the intervals exist. */
function groupStatus(status: PipelineStatusRecord[]) {
  const byKind = new Map<string, PipelineStatusRecord[]>();
  for (const s of status) {
    const list = byKind.get(s.status_kind) ?? [];
    list.push(s);
    byKind.set(s.status_kind, list);
  }
  for (const list of byKind.values()) {
    list.sort((a, b) => (b.valid_from ?? "").localeCompare(a.valid_from ?? ""));
  }
  return byKind;
}

export function RouteDetail({
  entity,
  routeLengthKm,
  drawnLengthKm,
  componentCount,
  onClose,
}: {
  entity: PipelineEntity | null;
  routeLengthKm?: number | null;
  drawnLengthKm?: number | null;
  componentCount?: number | null;
  onClose: () => void;
}) {
  if (!entity) return null;
  const g = entity.geometry;
  const status = groupStatus(entity.status ?? []);
  const unmappedKm =
    routeLengthKm != null && drawnLengthKm != null ? Math.max(0, routeLengthKm - drawnLengthKm) : null;

  return (
    <div className="route-detail">
      <div className="section-head" style={{ position: "static" }}>
        <h2 style={{ fontSize: 12 }}>{entity.canonical_name}</h2>
        <button className="ghost" onClick={onClose} aria-label="Close route detail">✕</button>
      </div>

      <div className="eyebrow" style={{ marginBottom: 6 }}>
        {titleCase(entity.commodity)} · {titleCase(entity.entity_level)}
        {entity.subtype ? ` · ${titleCase(entity.subtype)}` : ""}
        {entity.curated ? "" : " · auto-derived from source"}
      </div>

      {/* --- identity ---------------------------------------------------------------- */}
      <div className="kv"><span className="k">Canonical id</span>
        <span className="v" style={{ fontFamily: "monospace", fontSize: 10 }}>{entity.canonical_pipeline_id}</span></div>
      {entity.operator && <div className="kv"><span className="k">Operator</span><span className="v">{entity.operator}</span></div>}
      {entity.countries?.length > 0 && (
        <div className="kv"><span className="k">Countries</span><span className="v">{entity.countries.join(" · ")}</span></div>
      )}
      {(entity.start_area || entity.end_area) && (
        <div className="kv"><span className="k">Route</span>
          <span className="v">{entity.start_area ?? "?"} → {entity.end_area ?? "?"}</span></div>
      )}
      {entity.aliases?.length > 0 && (
        <div style={{ fontSize: 10, color: "var(--text-dim)", marginTop: 4, lineHeight: 1.4 }}>
          Also known as: {entity.aliases.join(" · ")}
        </div>
      )}

      {/* --- hierarchy --------------------------------------------------------------- */}
      {(entity.parent_id || entity.child_ids?.length > 0) && (
        <>
          <div className="eyebrow" style={{ marginTop: 10 }}>Structure</div>
          {entity.parent_id && (
            <div className="kv"><span className="k">Part of</span><span className="v">{entity.parent_id}</span></div>
          )}
          {entity.child_ids?.length > 0 && (
            <div className="kv"><span className="k">Contains</span>
              <span className="v" style={{ fontSize: 10 }}>{entity.child_ids.join(", ")}</span></div>
          )}
          <div style={{ fontSize: 9.5, color: "var(--text-faint)", marginTop: 3, lineHeight: 1.35 }}>
            A corridor's length is not the sum of its strings, and its capacity is not their total.
          </div>
        </>
      )}

      {/* --- temporal status --------------------------------------------------------- */}
      {status.size > 0 && (
        <>
          <div className="eyebrow" style={{ marginTop: 10 }}>Status by kind</div>
          {[...status.entries()].map(([kind, records]) => {
            const meta = STATUS_KIND_LABEL[kind] ?? { label: titleCase(kind), hint: "" };
            return (
              <div key={kind} style={{ marginBottom: 6 }}>
                <div className="kv" title={meta.hint}>
                  <span className="k">{meta.label}</span>
                  <span className="v">{titleCase(records[0].status_value)}</span>
                </div>
                {records.map((r, i) => (
                  <div key={i} style={{ fontSize: 9.5, color: i === 0 ? "var(--text-dim)" : "var(--text-faint)", lineHeight: 1.4, paddingLeft: 2 }}>
                    {fmtInterval(r)} — {titleCase(r.status_value)}
                    {r.source_date ? ` · source ${r.source_date}` : ""}
                    {r.note ? ` · ${r.note}` : ""}
                  </div>
                ))}
              </div>
            );
          })}
          <div style={{ fontSize: 9.5, color: "var(--text-faint)", lineHeight: 1.35 }}>
            Physical, operational and commercial-flow status are tracked separately: a pipeline
            can be intact, available, and carrying nothing simultaneously.
          </div>
        </>
      )}

      {/* --- geometry completeness --------------------------------------------------- */}
      <div className="eyebrow" style={{ marginTop: 10 }}>Geometry completeness</div>
      {routeLengthKm != null && (
        <div className="kv"><span className="k">Route length (source)</span>
          <span className="v">{fmtNum(routeLengthKm, 0)} km</span></div>
      )}
      {drawnLengthKm != null && (
        <div className="kv"><span className="k">Drawn on this map</span>
          <span className="v">{fmtNum(drawnLengthKm, 0)} km</span></div>
      )}
      {g && g.generalized_geometry_km > 0 && (
        <div className="kv"><span className="k">Generalized</span>
          <span className="v">{fmtNum(g.generalized_geometry_km, 0)} km</span></div>
      )}
      {componentCount != null && componentCount > 1 && (
        <div className="kv"><span className="k">Drawn in</span>
          <span className="v">{componentCount} pieces</span></div>
      )}
      {unmappedKm != null && unmappedKm > 1 && (
        <div style={{ fontSize: 10, color: "var(--amber)", marginTop: 4, lineHeight: 1.4 }}>
          About {fmtNum(unmappedKm, 0)} km of this route is not mapped in the source. That is a
          gap in the mapping, <b>not</b> a break in the pipeline, and no line is drawn across it.
        </div>
      )}
      {g && g.unresolved_gap_count > 0 && (
        <div style={{ fontSize: 9.5, color: "var(--text-faint)", marginTop: 3, lineHeight: 1.35 }}>
          {g.unresolved_gap_count} unresolved gap{g.unresolved_gap_count === 1 ? "" : "s"}. The
          missing length is not estimated — the straight line between two mapped pieces is not the
          pipe that runs between them.
        </div>
      )}

      {/* --- sources ----------------------------------------------------------------- */}
      {entity.sources?.length > 0 && (
        <>
          <div className="eyebrow" style={{ marginTop: 10 }}>
            Source mappings ({entity.sources.length})
          </div>
          {entity.sources.map((s, i) => (
            <div key={i} style={{ marginBottom: 5, paddingLeft: 2 }}>
              <div style={{ fontSize: 10, lineHeight: 1.35 }}>
                <span style={{ fontFamily: "monospace" }}>{s.source_system}:{s.source_id}</span>
                {" · "}
                <span style={{ color: CONFIDENCE_COLOR[s.confidence] ?? "var(--text-dim)" }}>
                  {s.confidence}
                </span>
                {" · "}{s.relationship}
              </div>
              {s.source_native && (
                <div style={{ fontSize: 9.5, color: "var(--text-dim)", lineHeight: 1.35 }}>
                  Source name: “{s.source_native}”
                </div>
              )}
              {s.evidence && (
                <div style={{ fontSize: 9.5, color: "var(--text-faint)", lineHeight: 1.35 }}>
                  {s.evidence}
                </div>
              )}
            </div>
          ))}
          <div style={{ fontSize: 9.5, color: "var(--text-faint)", lineHeight: 1.35 }}>
            <b>represents</b> one-to-one · <b>aggregates</b> the source covers several of ours ·
            {" "}<b>part_of</b> the inverse. Matches are made on source identity, never on name
            similarity alone.
          </div>
        </>
      )}

      {entity.note && (
        <div style={{ fontSize: 10, color: "var(--text-dim)", marginTop: 8, lineHeight: 1.4 }}>
          {entity.note}
        </div>
      )}

      <div style={{ fontSize: 9.5, color: "var(--text-faint)", marginTop: 8, lineHeight: 1.35 }}>
        Permanent infrastructure and publicly documented routing. Never an operational status,
        a flow measurement, or a current condition.
      </div>
    </div>
  );
}
