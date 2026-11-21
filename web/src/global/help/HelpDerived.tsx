/** The live values inside the Help prose (iteration 23): one renderer per `derived` key.
 *
 *  Every value is read from a served file or from the one code module that defines it; nothing is
 *  typed here except the words that frame it. While a file is loading the block says so, and if it
 *  failed it says that, never a guess in its place. Pure: given the same files it renders the same
 *  markup, so the Python tests render it with the served data.
 */
import { fmtDate, fmtNum } from "../../data";
import { COVERAGE_STATES, COVERAGE_STATE_MEANING, LANE_STATE_LABEL } from "../laneCoverage";
import { ENVIRONMENT_LABEL, labelFor, type Manifest, type WhatsNew } from "../manifest";
import { PLACEMENTS, PLACEMENT_LABEL, PLACEMENT_MEANING } from "../placement";
import { readerText } from "../readerText";
import { TAB_LABEL, TAB_ORDER } from "../countryTabs";
import type { ConfidenceMethod } from "../impacts/types";
import { navigateTo } from "../router";
import { START_HERE } from "./glossary";
import { HOW_IT_WORKS } from "./glossaryDetail";
import type { DerivedKey } from "./content";
import type { HelpFacts } from "./facts";

/** A file the page reads: its value once loaded, and whether loading it failed. */
export interface Loaded<T> { value: T | null; failed: boolean }

export interface HelpData {
  facts: Loaded<HelpFacts>;
  manifest: Loaded<Manifest>;
  method: Loaded<ConfidenceMethod>;
  whatsNew: Loaded<WhatsNew>;
}

/** Said while the Evidence Confidence method's version is a draft. Shown only when the served
 *  version says so: when the method is calibrated this paragraph goes, and the served status
 *  says what it is instead. */
export const ECI_DRAFT_NOTE = "Its first blind test did not meet the agreement bar set in advance, so the cut points between "
  + "categories remain under review. The reviewers in that test were AI sessions from the same project, not independent "
  + "people. A second test is prepared; it needs at least one person from outside the project and has not been run.";

export function isDraftMethod(m: Pick<ConfidenceMethod, "version"> | null | undefined): boolean {
  return !!m?.version && /-draft$/.test(m.version);
}

function Pending({ what, failed }: { what: string; failed: boolean }) {
  return failed
    ? <p className="small dim help-derived-missing">The {what} could not be loaded, so it is not shown here.</p>
    : <p className="small dim help-derived-missing" role="status">Loading the {what}…</p>;
}

function Defs({ items, label }: { items: { term: string; text: string | null | undefined }[]; label?: string }) {
  return (
    <dl className="help-defs" aria-label={label}>
      {items.map((it) => (
        <div key={it.term}><dt>{it.term}</dt><dd>{it.text || "No definition is published."}</dd></div>
      ))}
    </dl>
  );
}

/** A real link (new tab, copy address), moved in-page on a plain click. */
export function go(href: string) {
  return (e: React.MouseEvent) => {
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    navigateTo(href);
  };
}

const dec = (n: number | null | undefined, d = 2) => (n == null ? "not stated" : fmtNum(n, d));

export function Derived({ k, data }: { k: DerivedKey; data: HelpData }) {
  const f = data.facts.value, m = data.manifest.value, meth = data.method.value, wn = data.whatsNew.value;
  const needFacts = (what: string) => <Pending what={what} failed={data.facts.failed} />;
  const needManifest = (what: string) => <Pending what={what} failed={data.manifest.failed} />;
  const needMethod = (what: string) => <Pending what={what} failed={data.method.failed} />;

  switch (k) {
    case "start.points":
      return (
        <ol className="help-points">
          {START_HERE.map((p) => <li key={p.title}><strong>{p.title}</strong> {p.text}</li>)}
        </ol>
      );
    case "how.steps":
      return (
        <ol className="help-points">
          {HOW_IT_WORKS.map((s) => <li key={s.step}><strong>{s.step}.</strong> {s.text}</li>)}
        </ol>
      );
    case "systems.list": {
      if (!m) return needManifest("list of monitored systems");
      return (
        <ul className="help-systems" aria-label="The monitored systems, in the order the site lists them">
          {m.systems.map((s) => (
            <li key={s.id}>
              <a href={`?sys=${encodeURIComponent(s.id)}`} onClick={go(`?sys=${encodeURIComponent(s.id)}`)}>{s.name}</a>
              <span className="dim"> · {s.kind === "theatre" ? "the indexed area, the only system with an index"
                : `country system, no index${s.maturity === "research_preview" ? " · research preview" : ""}${s.campaign_restricted ? " · publication safeguards apply" : ""}`}</span>
            </li>
          ))}
        </ul>
      );
    }
    case "country.tabs":
      return (
        <ol className="help-tabs" aria-label="Country page tabs, in order">
          {TAB_ORDER.map((t) => (
            <li key={t}>{TAB_LABEL[t]}{t === "regional" && <span className="dim"> (only on the pages of Gulf littoral states)</span>}</li>
          ))}
        </ol>
      );
    case "selection":
      if (!m) return needManifest("selection rule");
      return (
        <div className="help-served">
          <p>{m.selection.rule}</p>
          {m.selection.regional_rule && <p>{m.selection.regional_rule}</p>}
          <p className="small dim">{m.selection.caveat}</p>
          <p className="small dim">Source: <a href={m.selection.source_url} rel="noopener noreferrer">{m.selection.source}</a></p>
        </div>
      );
    case "esdi.headline": {
      if (!m) return needManifest("current index value");
      const t = m.systems.find((s) => s.kind === "theatre");
      const h = t?.headline;
      if (!h) return <p className="small dim">No index value is published in this build.</p>;
      return (
        <p className="help-served help-headline">
          In this build: <strong>{fmtNum(h.value, 1)}</strong> on {fmtDate(h.as_of)} ({h.label}). {h.meaning}
          {f?.theatre.method_version && <span className="dim"> Index method version {f.theatre.method_version}.</span>}
        </p>
      );
    }
    case "esdi.contributions":
      if (!f) return needFacts("breakdown of the index");
      return (
        <div className="table-scroll">
          <table className="help-table">
            <caption className="small dim">Each sector's part of the headline in this build, in the order the method lists them. A left-out sector is not a zero.</caption>
            <thead><tr><th scope="col">Sector</th><th scope="col">Value (0 to 100)</th><th scope="col">Weight used</th><th scope="col">Points added</th></tr></thead>
            <tbody>
              {f.theatre.contributions.map((c) => (
                <tr key={c.sector}>
                  <th scope="row">{c.sector}</th>
                  {c.included
                    ? <><td>{dec(c.sector_value)}</td><td>{dec(c.effective_weight)}</td><td>{dec(c.index_points)}</td></>
                    : <td colSpan={3}>Left out: {c.excluded_reason ?? "no capacity base"}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    case "esdi.weights":
      if (!f) return needFacts("sector weights");
      return (
        <p className="help-served">Fixed weights as set: {f.theatre.contributions.map((c) => `${c.sector} ${dec(c.nominal_weight)}`).join("; ")}.
          {" "}Weights used after left-out sectors are removed: {f.theatre.contributions.filter((c) => c.included).map((c) => `${c.sector} ${dec(c.effective_weight)}`).join("; ")}.</p>
      );
    case "esdi.uncovered":
      if (!f) return needFacts("list of left-out sectors");
      return f.theatre.sectors_uncovered.length === 0
        ? <p className="help-served">In this build no sector is left out for lack of a capacity base.</p>
        : <p className="help-served">Left out of the headline for lack of a capacity base: {f.theatre.sectors_uncovered.join(", ")}. They carry real records that are not scored.</p>;
    case "esdi.saturation":
      if (!f) return needFacts("transmission saturation point");
      return f.theatre.transmission_saturation_events == null ? <p className="small dim">The saturation point is not published in this build.</p>
        : <p className="help-served">The saturation point is {fmtNum(f.theatre.transmission_saturation_events, 0)} weighted concurrent disruptions: a documented judgement, not a measurement.</p>;
    case "esdi.sensitivity":
      if (!f) return needFacts("recovery-assumption sensitivity");
      return f.theatre.recovery_horizon_sensitivity.note ? <p className="help-served">{f.theatre.recovery_horizon_sensitivity.note}</p>
        : <p className="small dim">No sensitivity is published in this build.</p>;
    case "impacts.scope":
      if (!f) return needFacts("scope of the impact records");
      return <p className="help-served">{f.impacts.scope_statement}</p>;
    case "impacts.caveats":
      if (!f) return needFacts("caveats of the impact records");
      return <ul className="help-served" aria-label="What the impact records are and are not">{f.impacts.caveats.map((c) => <li key={c}>{c}</li>)}</ul>;
    case "impacts.research": {
      if (!f) return needFacts("research notes of the impact records");
      const r = f.impacts.research;
      return (
        <div className="help-served">
          <p>Research window: {r.window ? `${fmtDate(r.window.start)} to ${r.window.end === "present" ? "the present" : fmtDate(r.window.end)}` : "not stated"}
            {r.status ? `; ${r.status}` : ""}; latest research {r.latest_research_date ? fmtDate(r.latest_research_date) : "not recorded"}.</p>
          {r.limitations.length > 0 && <ul aria-label="Known limits of the impact research">{r.limitations.map((l) => <li key={l}>{l}</li>)}</ul>}
        </div>
      );
    }
    case "eci.status": {
      if (!meth) return needMethod("status of the evidence-confidence method");
      const draft = isDraftMethod(meth);
      return (
        <div className={`help-status${draft ? " help-status-draft" : ""}`} role="note">
          <p><strong>Method version {meth.version}.</strong>{meth.status ? <> Status: {readerText(meth.status)}.</> : null}</p>
          {draft && <p>{ECI_DRAFT_NOTE}</p>}
        </div>
      );
    }
    case "eci.statement":
      if (!meth) return needMethod("evidence-confidence statement");
      return <p className="help-served">{meth.statement}</p>;
    case "eci.categories": {
      if (!meth) return needMethod("evidence-confidence categories");
      const na = (meth as ConfidenceMethod & { not_assessed?: { label: string; meaning: string } }).not_assessed;
      return <Defs label="Evidence-confidence categories" items={[...meth.categories.map((c) => ({ term: c.label, text: c.meaning })),
        ...(na ? [{ term: na.label, text: na.meaning }] : [])]} />;
    }
    case "eci.overrides":
      if (!meth) return needMethod("rules that override the points");
      return <ul className="help-served">{meth.overrides.map((o) => <li key={o}>{o}</li>)}</ul>;
    case "attribution.statuses":
      if (!meth) return needMethod("attribution statuses");
      return <Defs label="Attribution statuses" items={(meth.labels.attribution_statuses ?? []).map((s) => ({ term: s.label, text: s.definition }))} />;
    case "attribution.meanings": {
      if (!meth) return needMethod("attribution-confidence levels");
      const { labels, meanings } = meth.attribution;
      const keys = ["HIGH", "MODERATE", "LOW", "CLAIM_ONLY", "DISPUTED", "NOT_ESTABLISHED"].filter((x) => x in labels && x in meanings);
      return <Defs label="Attribution-confidence levels" items={keys.map((x) => ({ term: labels[x], text: meanings[x] }))} />;
    }
    case "ai.relations":
      if (!meth) return needMethod("AI relations");
      return <Defs label="Kinds of AI involvement" items={(meth.labels.ai_relations ?? []).map((s) => ({ term: s.label, text: s.definition }))} />;
    case "ai.statuses":
      if (!meth) return needMethod("AI-involvement statuses");
      return <Defs label="AI-involvement statuses" items={(meth.labels.ai_statuses ?? []).map((s) => ({ term: s.label, text: s.definition }))} />;
    case "coverage.states":
      return <Defs label="Research states" items={COVERAGE_STATES.filter((s) => s !== "legacy").map((s) => ({ term: LANE_STATE_LABEL[s], text: COVERAGE_STATE_MEANING[s] }))} />;
    case "theatre.coverage": {
      if (!f) return needFacts("coverage of the indexed area");
      const c = f.theatre.coverage;
      return (
        <p className="help-served">In this build: {c.enumerated_oil_strikes ?? "an unstated number of"} oil-sector strikes enumerated against a reported
          benchmark of {c.reported_oil_strikes ?? "an unstated number"}{c.coverage_ratio != null ? ` (${Math.round(c.coverage_ratio * 100)}%)` : ""};
          {" "}{c.incidents_with_quantified_capacity ?? "an unstated number"} of {c.incident_total ?? "an unstated number of"} disruptions state capacity removed in MW or Mt/yr
          {c.incidents_with_reported_effect != null ? `, and ${c.incidents_with_reported_effect} report a halt, outage or throughput effect that is shown but never scored` : ""}.</p>
      );
    }
    case "build.date":
      if (!f) return needFacts("build date");
      return <p className="help-served">This build is dated {fmtDate(f.as_of)} and was generated on {fmtDate(f.build_time.slice(0, 10))} (UTC). That is the build date, not the date of any record or source.</p>;
    case "build.note":
      if (!f) return needFacts("note on build dates");
      return f.theatre.build_date_note ? <p className="help-served">{f.theatre.build_date_note}</p> : null;
    case "reporting.environments":
      if (!m) return needManifest("reporting environments");
      return <Defs label="Reporting environments" items={Object.keys(m.reporting_environments).map((x) => ({ term: labelFor(ENVIRONMENT_LABEL, x), text: m.reporting_environments[x] }))} />;
    case "context.vintage": {
      if (!f) return needFacts("national context vintage");
      const v = f.context_vintage;
      return (
        <p className="help-served">{v.source ?? "Source not stated"}: released {fmtDate(v.release)}, retrieved {fmtDate(v.retrieved)},
          comparison year {v.comparison_year ?? "not stated"}; {v.update_cadence ?? "update cadence not stated"}.{v.note ? ` ${v.note}` : ""}</p>
      );
    }
    case "whatsnew.comparison": {
      if (!wn) return <Pending what="comparison behind What's new" failed={data.whatsNew.failed} />;
      if (!wn.available) return <p className="help-served">What's new is not available for this build: {readerText(wn.unavailable_reason)}.</p>;
      const c = wn.comparison;
      return (
        <p className="help-served">This build ({fmtDate(c.current_as_of)}) is compared with {c.basis ?? "the previous published build"} ({fmtDate(c.previous_as_of)}).
          {c.note ? ` ${c.note}` : ""}</p>
      );
    }
    case "whatsnew.categories":
      if (!wn) return <Pending what="kinds of change" failed={data.whatsNew.failed} />;
      return <Defs label="Kinds of change" items={wn.categories.map((c) => ({ term: c.label, text: c.meaning }))} />;
    case "whatsnew.note":
      if (!wn) return null;
      return <p className="help-served">{readerText(wn.note)}</p>;
    case "history.first":
      if (!f) return needFacts("start date of published history");
      return f.theatre.earliest_published_date
        ? <p className="help-served">Published history starts on {fmtDate(f.theatre.earliest_published_date)}.</p>
        : <p className="small dim">No published history is recorded in this build.</p>;
    case "groups": {
      if (!m) return needManifest("groupings");
      const name = (id: string) => m.systems.find((s) => s.id === id)?.name ?? id.toUpperCase();
      return <Defs label="Groupings" items={Object.values(m.groups ?? {}).map((g) => ({
        term: `${g.label}: ${g.members.map(name).join(", ")}`, text: readerText(g.note) }))} />;
    }
    case "context.statement":
      if (!f) return needFacts("description of the regional context");
      return <p className="help-served">{f.regional_context.statement}</p>;
    case "context.not_built":
      if (!f) return needFacts("limits of the regional context");
      return <p className="help-served">{f.regional_context.not_built}</p>;
    case "cyber.mechanisms":
      if (!f) return needFacts("list of cyber mechanisms");
      return <Defs label="Broad cyber mechanisms" items={f.impacts.cyber_mechanisms.map((c) => ({ term: c.label, text: c.definition }))} />;
    case "absence.words":
      if (!f) return needFacts("words for what is not known");
      return <Defs label="Words for what is not known" items={f.impacts.absence_words.map((c) => ({ term: c.label, text: c.definition }))} />;
    case "placement.meanings":
      return <Defs label="Placements" items={PLACEMENTS.map((x) => ({ term: PLACEMENT_LABEL[x], text: PLACEMENT_MEANING[x] }))} />;
    case "theatre.delay":
      if (!f) return needFacts("recovery-evidence delay");
      return f.theatre.status_delay_days == null ? null
        : <p className="help-served">In this build that age is {f.theatre.status_delay_days} days.</p>;
    case "comparability":
      if (!m) return needManifest("statement on comparing countries");
      return <p className="help-served comparability">{m.comparability_statement}</p>;
    case "theatre.cannot":
      if (!f) return needFacts("list of what the indexed area cannot tell you");
      return <Defs label="What the Russia, Belarus & Crimea page cannot tell you" items={f.theatre.cannot_tell_you.map((c) => ({ term: c.question, text: c.answer }))} />;
  }
}
