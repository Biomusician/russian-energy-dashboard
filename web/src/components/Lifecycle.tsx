/** Recovery Lifecycle Explorer (iteration 11 P7).
 *
 *  TWO LAYERS THAT MUST NEVER BE CONFUSED. Observed milestones are discrete, sourced events. The
 *  modelled disruption weight is a decay curve the index consumes. They are drawn separately and
 *  labelled separately, because a continuous line under a row of milestones reads as measured
 *  repair progress — and nothing here measures repair progress.
 *
 *  STAGES ARE NOT A TEMPLATE. An episode shows only the stages its evidence establishes. A
 *  pipeline whose sole evidence is flow rerouting shows disruption and rerouting; the remaining
 *  stages are listed as UNKNOWN, never as pending or done. Rerouting gas around a broken segment
 *  is not a repair, and a filled-in template would say it was.
 *
 *  SERVICE RESTORED IS NOT FACILITY REBUILT. The evidence families stay distinct in the data and
 *  in the type, and each milestone carries what its source actually establishes.
 *
 *  This component performs no scoring and no statistics. Durations, medians and sample-size
 *  refusals all arrive computed from pipeline/lifecycle.py.
 */

import { useEffect, useMemo, useState } from "react";
import type { Bundle, LifecyclePayload, LifecycleEpisode, Milestone } from "../types";
import { FAMILY_LABEL, fmtDate, fmtNum, loadLifecycle, titleCase } from "../data";
import { Sparkline, hostOf } from "./ui";
import type { InspectTarget } from "./Inspector";
import type { CompareState } from "./Comparison";

const STAGE_LABEL: Record<string, string> = {
  disruption: "Disruption",
  flow_rerouting: "Flow rerouted",
  partial_operations_resumed: "Partial operations resumed",
  service_restoration: "Service restored",
  unit_restart: "Unit restarted",
  physical_reconstitution: "Physically reconstituted",
  estimated_restoration: "Estimated restoration",
};

/** Where a milestone sits relative to an active two-date comparison (§14). Computed from dates
 *  against the same resolved series points the comparison uses — no second date engine. */
function abPosition(date: string | null, a: string | null, b: string | null) {
  if (!date || !a || !b) return null;
  if (date <= a) return "by_a";
  if (date <= b) return "between";
  return "after_b";
}

const AB_LABEL: Record<string, string> = {
  by_a: "by A",
  between: "A→B",
  after_b: "after B",
};

export default function Lifecycle({
  bundle, onClose, onExplain, compare, selectedEpisode, onSelectEpisode,
}: {
  bundle: Bundle;
  onClose: () => void;
  onExplain: (t: InspectTarget) => void;
  compare: CompareState | null;
  /** Held in App so reopening the panel restores the reader's place (§18). */
  selectedEpisode: string | null;
  onSelectEpisode: (id: string | null) => void;
}) {
  const [data, setData] = useState<LifecyclePayload | null | "loading">("loading");
  useEffect(() => {
    let live = true;
    loadLifecycle().then((d) => { if (live) setData(d); });
    return () => { live = false; };
  }, []);

  const episode = useMemo(() => {
    if (!data || data === "loading") return null;
    return data.episodes.find((e) => e.episode_id === selectedEpisode) ?? null;
  }, [data, selectedEpisode]);

  if (data === "loading") {
    return <div className="empty" style={{ padding: 24 }}>Loading recovery evidence…</div>;
  }
  if (!data) {
    return (
      <div className="empty" style={{ padding: 24 }}>
        <div className="eyebrow">Lifecycle unavailable</div>
        <p style={{ lineHeight: 1.6, color: "var(--text-dim)" }}>
          This payload carries no recovery lifecycle. That is not a finding about recovery — it
          means the build did not emit one.
        </p>
      </div>
    );
  }

  return (
    <div className="lifecycle">
      <div className="section-head">
        <div>
          <h2 style={{ fontSize: 13 }}>Recovery lifecycle</h2>
          <div className="eyebrow" style={{ marginTop: 3 }}>
            {data.episode_count} episodes with evidence
          </div>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          {episode && (
            <button className="ghost" onClick={() => onSelectEpisode(null)}>all episodes</button>
          )}
          <button className="ghost" onClick={onClose}>close</button>
        </div>
      </div>

      {/* §8: the current-estimate caveat, visible rather than buried. */}
      <div className="semantics-note">{data.reconstruction_caveat}</div>

      {episode
        ? <EpisodeDetail e={episode} data={data} bundle={bundle} onExplain={onExplain}
                         compare={compare} />
        : <EpisodeList data={data} onSelect={onSelectEpisode} compare={compare} />}
    </div>
  );
}

function EpisodeList({
  data, onSelect, compare,
}: {
  data: LifecyclePayload;
  onSelect: (id: string) => void;
  compare: CompareState | null;
}) {
  return (
    <>
      <section className="cmp-block">
        <h3>Episodes</h3>
        <p className="small">
          One row per disrupted facility that has recovery evidence. Families are kept apart:
          service restored is not the same claim as facility rebuilt.
        </p>
        <div className="contrib-list">
          {data.episodes.map((e) => {
            const last = e.milestones[e.milestones.length - 1];
            const pos = compare ? abPosition(last?.date ?? null, compare.a, compare.b) : null;
            return (
              <button key={e.episode_id} className="contrib-row plain lifecycle-row"
                      onClick={() => onSelect(e.episode_id)}>
                <span className="contrib-name">
                  {e.asset_name ?? e.asset_id}
                  {pos && <span className={`flag ab ${pos}`}>{AB_LABEL[pos]}</span>}
                </span>
                <span className="contrib-math">
                  {fmtDate(e.incident_date)} · {titleCase(e.asset_class ?? "")}
                </span>
                <span className="lifecycle-fam">
                  {FAMILY_LABEL[e.evidence_family ?? "none"]}
                  {e.duration_days != null && ` · ${e.duration_days}d observed`}
                  {e.duration_days == null && e.evidence_family === "estimate"
                    && " · projected horizon, no observed restoration"}
                  {e.undated_restoration_claim && " · restoration claimed, date unrecorded"}
                </span>
              </button>
            );
          })}
        </div>
      </section>

      <Distributions data={data} />
      <TemporalModel data={data} />
    </>
  );
}

function EpisodeDetail({
  e, data, bundle, onExplain, compare,
}: {
  e: LifecycleEpisode;
  data: LifecyclePayload;
  bundle: Bundle;
  onExplain: (t: InspectTarget) => void;
  compare: CompareState | null;
}) {
  const weights = e.trajectory.map((p) => p.weight);
  return (
    <>
      <section className="cmp-block">
        <h3>{e.asset_name ?? e.asset_id}</h3>
        <p className="small">
          {fmtDate(e.incident_date)} · {titleCase(e.asset_class ?? "")}
          {e.region_code && ` · ${bundle.snapshot.regions[e.region_code]?.name ?? e.region_code}`}
          {e.cause && ` · ${titleCase(e.cause)}`}
        </p>

        <h4>Observed milestones</h4>
        <p className="small">{data.layer_labels.observed}</p>
        <ol className="stages">
          {e.milestones.map((m) => (
            <StageNode key={m.stage + m.date} m={m} compare={compare} />
          ))}
        </ol>
        {e.undated_restoration_claim && (
          <p className="small warn-text">{e.undated_restoration_note}</p>
        )}
        {e.stages_unknown.length > 0 && (
          <div className="stages-unknown">
            <span className="eyebrow">No evidence either way</span>
            <div>
              {e.stages_unknown.map((s) => (
                <span key={s} className="flag unknown-stage">{STAGE_LABEL[s] ?? s}</span>
              ))}
            </div>
            <p className="small">
              These stages are UNKNOWN for this episode — not pending, and not complete. Nothing
              in the record says whether they happened.
            </p>
          </div>
        )}
      </section>

      {weights.length > 1 && (
        <section className="cmp-block">
          <h3>Modelled disruption weight</h3>
          {/* Named for what it is. This is the value that entered the index, not a measurement
              of how much of the facility has been repaired. */}
          <p className="small">{data.layer_labels.model}</p>
          <Sparkline values={weights} width={300} height={54} color="var(--amber)"
                     ariaLabel={`Modelled disruption weight for ${e.asset_name ?? e.asset_id}`} />
          <div className="traj-scale">
            <span className="mono small">{fmtDate(e.trajectory[0].date)}</span>
            <span className="mono small">
              {fmtNum(weights[0], 3)} → {fmtNum(weights[weights.length - 1], 3)}
            </span>
            <span className="mono small">
              {fmtDate(e.trajectory[e.trajectory.length - 1].date)}
            </span>
          </div>
          <dl className="kv">
            <dt>Initial impairment</dt>
            <dd className="mono">{fmtNum(e.initial_impairment, 3)}</dd>
            <dt>Half-life</dt>
            <dd className="mono">
              {fmtNum(e.half_life_days, 1)} d
              <span className="flag">{e.half_life_kind}</span>
            </dd>
          </dl>
          <p className="small warn-text">
            A falling curve is impairment ageing out of the model. Where no restoration was
            observed, it is not evidence that anything was repaired.
          </p>
        </section>
      )}

      <section className="cmp-block">
        <h3>Duration</h3>
        {e.duration_days == null ? (
          <p className="small">
            No duration: this episode has no dated restoration milestone to measure to.
          </p>
        ) : (
          <p>
            <span className="mono big">{e.duration_days}</span> days from{" "}
            <span className="mono">{e.duration_start}</span> to{" "}
            <span className="mono">{e.duration_end}</span>.
            {" "}<span className="small">
              Comparable only with other {FAMILY_LABEL[e.evidence_family ?? "none"]} durations.
            </span>
          </p>
        )}
      </section>

      <section className="cmp-block">
        <h3>Evidence ({e.sources.length})</h3>
        {e.sources.length === 0 ? (
          <p className="small">No source is attached to this episode.</p>
        ) : (
          <ul className="tight">
            {e.sources.map((s, i) => (
              <li key={i}>
                <a href={s.url} target="_blank" rel="noreferrer noopener">{hostOf(s.url)}</a>
                <span className="small">
                  {" · "}
                  {s.published
                    ? `published ${fmtDate(s.published)}`
                    : "publication date unavailable"}
                </span>
              </li>
            ))}
          </ul>
        )}
        {/* §2: never call this "when we learned it". */}
        <p className="small">
          {e.first_seen
            ? `First present in dashboard: ${fmtDate(e.first_seen.build_date)}`
            : "First-present-in-dashboard is unavailable: it requires a build ledger with "
              + "provable lineage."}
        </p>
      </section>

      <section className="cmp-block">
        <div className="cmp-explain">
          <button className="ghost"
                  onClick={() => onExplain({ kind: "incident", incidentId: e.incident_id })}>
            Explain contribution
          </button>
          <button className="ghost"
                  onClick={() => onExplain({ kind: "facility", assetId: e.asset_id })}>
            Facility detail
          </button>
        </div>
      </section>
    </>
  );
}

function StageNode({ m, compare }: { m: Milestone; compare: CompareState | null }) {
  const pos = compare ? abPosition(m.date, compare.a, compare.b) : null;
  return (
    <li className={`stage ${m.status}`}>
      <div className="stage-head">
        <span className="stage-dot" aria-hidden />
        <strong>{STAGE_LABEL[m.stage] ?? m.stage}</strong>
        <span className="mono small">{fmtDate(m.date)}</span>
        <span className={`flag ev-${m.status}`}>{m.status}</span>
        {m.drives_scoring_as && m.drives_scoring_as !== m.status && (
          <span className="flag" title="How this evidence drives the decay, which is a separate
question from whether the milestone itself was reported">
            decay {m.drives_scoring_as}
          </span>
        )}
        {pos && <span className={`flag ab ${pos}`}>{AB_LABEL[pos]}</span>}
      </div>
      {m.estimate_days && (
        <p className="small mono">
          projected {m.estimate_days.lower}–{m.estimate_days.upper} d
          (central {m.estimate_days.central})
          {m.estimate_method ? ` · ${m.estimate_method.replace(/_/g, " ")}` : ""}
        </p>
      )}
      <p className="small">{m.meaning}</p>
      {m.what_source_establishes && (
        <p className="small establishes">{m.what_source_establishes}</p>
      )}
    </li>
  );
}

function Distributions({ data }: { data: LifecyclePayload }) {
  const rows = Object.entries(data.distributions.by_class_family);
  const sufficient = rows.filter(([, v]) => v.sufficient);
  const insufficient = rows.filter(([, v]) => !v.sufficient);
  return (
    <section className="cmp-block">
      <h3>Observed durations by class and evidence type</h3>
      <p className="small">{data.distributions.note}</p>
      {sufficient.length === 0 ? (
        <p className="small">
          No class-and-family group reaches {data.distributions.min_sample} observations.
        </p>
      ) : (
        <table className="mini">
          <thead>
            <tr><th>Class · evidence</th><th>n</th><th>median</th><th>range</th></tr>
          </thead>
          <tbody>
            {sufficient.map(([k, v]) => (
              <tr key={k}>
                <td>
                  {titleCase(v.asset_class)}
                  <span className="flag">{FAMILY_LABEL[v.evidence_family] ?? v.evidence_family}</span>
                </td>
                {/* §17: never a statistic without its sample size. */}
                <td className="mono">{v.n}</td>
                <td className="mono">{v.median}d</td>
                <td className="mono">{v.min}–{v.max}d</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {sufficient.length > 0 && (
        <p className="small">
          Values shown individually because the samples are small:{" "}
          {sufficient.map(([, v]) => `${titleCase(v.asset_class)} ${v.values.join("/")}d`)
            .join(" · ")}.
        </p>
      )}

      {insufficient.length > 0 && (
        <>
          <h4>Insufficient observations</h4>
          <p className="small">
            Below {data.distributions.min_sample} observations a median is an anecdote. These
            groups show their raw values and no summary.
          </p>
          <table className="mini">
            <tbody>
              {insufficient.map(([k, v]) => (
                <tr key={k} className="dim">
                  <td>
                    {titleCase(v.asset_class)}
                    <span className="flag">
                      {FAMILY_LABEL[v.evidence_family] ?? v.evidence_family}
                    </span>
                  </td>
                  <td className="mono">n={v.n}</td>
                  <td className="mono">{v.values.join(", ")}d</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}

function TemporalModel({ data }: { data: LifecyclePayload }) {
  return (
    <section className="cmp-block">
      <h3>Four dates, and which of them exist</h3>
      <p className="small">{data.temporal_model.warning}</p>
      <dl className="kv">
        {data.temporal_model.concepts.map((c) => (
          <span key={c.field}>
            <dt>{c.label}</dt>
            <dd>
              <span className={`flag ${c.available ? "" : "unknown-stage"}`}>
                {c.available ? "available" : "not available"}
              </span>
              <p className="small">{c.note}</p>
            </dd>
          </span>
        ))}
      </dl>
      <p className="small">
        Episodes with a source publication date: {data.episodes_with_publication_date} of{" "}
        {data.episode_count}.
      </p>
    </section>
  );
}
