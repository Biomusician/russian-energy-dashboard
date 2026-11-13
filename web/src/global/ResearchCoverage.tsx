import { localISODate } from "../freshness";
import "../styles/research.css";
import { fmtDate } from "../data";
import {
  ENVIRONMENT_LABEL, LANE_WINDOW_LABEL, LANGUAGE_LABEL, labelFor, languageNames,
  type CountryBundle,
} from "./manifest";
import { readerText } from "./readerText";
import { inSentence } from "./countryCopy";
import {
  COVERAGE_STATES, COVERAGE_STATE_MEANING, COVERAGE_STATE_TEXT, UNIVERSE_TEXT, countStates, coverageSummary,
  isCampaignRestricted, latestLanes, missingLanguages, passOutcomeText, reviewLine, workDone,
  type CoverageState, type LaneRow,
} from "./laneCoverage";

/** The Research coverage tab of a country system: how well has this country actually been searched?
 *
 *  One row per lane (one family of sources searched as a unit), as it stands in the latest pass that
 *  logged it. Every state is text plus a shape, all in one neutral colour: a lane blocked by a
 *  publisher is not a moral failing, and a partial lane can be the honest end state.
 *
 *  Kept apart from SOURCE HEALTH, which describes the citations behind events already published.
 *  The one place this tab touches citations is a separately headed block at the end, saying so.
 *
 *  Under the attack-campaign rule nothing here gives a count of candidates, held records or pass
 *  outcomes; at most it says that review continues. */
export default function ResearchCoverage({ bundle }: { bundle: CountryBundle }) {
  const s = bundle.system;
  const passes = s.research_log.passes;
  const newestSystematic = passes.filter((p) => p.kind === "systematic").at(-1);
  const rf = s.research_freshness;
  const rows = latestLanes(passes);
  const counts = countStates(rows);
  const restricted = isCampaignRestricted(s);
  const review = reviewLine(s);
  const today = localISODate(new Date());
  const owed = rf.completeness !== "complete" && rows.length > 0;
  const shownStates = COVERAGE_STATES.filter((x) => x !== "earlier_format" || counts.earlier_format > 0);
  const rc = s.recovery_coverage;
  const cq = s.citation_quality;

  return (
    <section className="rc" aria-labelledby="rc-heading">
      <h2 id="rc-heading">Research coverage</h2>
      <p className="small rc-lead">How well has {inSentence(s.name)} actually been searched for disruptions? The search is
        planned in <strong>lanes</strong>: a lane is one family of sources searched as a unit, such as one
        ministry's statements or the national press. Other pages of this site call a lane a source group.</p>
      <p className="small rc-distinct"><strong>Research coverage</strong> is how far the search for events got.{" "}
        <strong>Source health</strong>, under Sources &amp; data quality, describes the citations behind the events
        already published. Neither implies the other.</p>

      <div className="rc-overview">
        <p className="rc-summary-line">{coverageSummary(rows, passes.length)}</p>
        {review && <p className="small rc-review">{review}</p>}
        {rf.coverage_window && rf.last_systematic_pass && (
          <p className="small">Search period {fmtDate(rf.coverage_window[0])} – {fmtDate(rf.coverage_window[1])};
            last worked on {fmtDate(rf.last_systematic_pass)}.
            {rf.next_due && (owed
              ? " The unfinished lanes are owed now, not in a year's time."
              : ` Next full search due ${fmtDate(rf.next_due)}${rf.next_due < today ? " (now due)" : ""}.`)}
          </p>
        )}
        <p className="small dim">
          {rf.first_systematic_pass
            ? `Systematic research for this country began on ${fmtDate(rf.first_systematic_pass)}; records can date back to 2022, so older ones were found afterwards, not monitored as they happened.`
            : "No systematic search has been run for this country yet."}
          {" "}Reporting environment: {labelFor(ENVIRONMENT_LABEL, s.reporting_environment)}.</p>
      </div>

      {rows.length > 0 && (<>
        <table className="lane-table rc-matrix">
          <caption>Lane states at a glance</caption>
          <thead><tr><th scope="col">Lane</th><th scope="col">How it is searched</th><th scope="col">State</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.lane.lane}>
                <th scope="row">
                  <button type="button" className="linkish mono" aria-label={`${r.lane.lane}: go to lane details`}
                    onClick={() => document.getElementById(laneId(s.system_id, r.lane.lane))?.focus()}>
                    {r.lane.lane}
                  </button>
                </th>
                <td>{labelFor(UNIVERSE_TEXT, r.lane.universe_kind ?? "not recorded")}</td>
                <td><StateMark state={r.state} /></td>
              </tr>
            ))}
          </tbody>
        </table>

        <details className="rc-legend" open>
          <summary>What each state means</summary>
          <dl>
            {shownStates.map((st) => (
              <div key={st} className="rc-legend-row">
                <dt><StateMark state={st} /></dt>
                <dd>{COVERAGE_STATE_MEANING[st]}</dd>
              </div>
            ))}
          </dl>
          <p className="small dim">No percentage or score is given on purpose: a lane waiting on a publisher and a
            lane that ran a few of its searches are different shortfalls and do not add up to one number.</p>
        </details>

        <ol className="rc-lanes" aria-label="Lanes in detail">
          {rows.map((r) => <LaneCard key={r.lane.lane} row={r} systemId={s.system_id} newestPassDate={rf.last_systematic_pass} />)}
        </ol>
      </>)}

      {s.research_gaps.length > 0 && (<>
        <h3 className="eyebrow">Other known gaps</h3>
        <ul className="small">{s.research_gaps.map((g, i) => <li key={i}>{readerText(g)}</li>)}</ul>
      </>)}

      {/* With no published record there is no recovery research or citation to describe: a list of
          zeros would read as a finding. */}
      {bundle.events.length === 0 && (
        <p className="small dim rc-no-records">No record is published yet, so there is no recovery research and no citation to describe.</p>
      )}
      {rc && bundle.events.length > 0 && (<>
        <h3 className="eyebrow">Recovery research</h3>
        <p className="small dim">Whether a public report of a facility or service coming back was looked for, per
          published event. A separate question from the event search above.</p>
        <ul className="small recovery-coverage">
          <li>Observed report of recovery: {rc.observed}</li>
          <li>Sourced estimate only: {rc.estimate}</li>
          {rc.other_statement > 0 && <li>Statement that supply was unaffected or nothing was lost: {rc.other_statement}</li>}
          <li>Researched, no public evidence: {rc.researched_no_public_evidence}</li>
          <li>Not yet researched: {rc.not_researched}</li>
          {rc.withheld_active_campaign > 0 && <li>Status withheld while an attack campaign is active: {rc.withheld_active_campaign}</li>}
        </ul>
        {Object.keys(rc.unresearched_by_class).length > 0 && (
          <p className="small dim">Still to research: {Object.entries(rc.unresearched_by_class).map(([k, n]) => `${n} ${labelFor(s.taxonomy.asset_classes, k).toLowerCase()}`).join(", ")}.</p>
        )}
        <p className="small dim">{readerText(rc.policy)}</p>
      </>)}

      <details className="small rc-history">
        <summary>Every pass, as it was logged</summary>
        <table className="research-log rc-log">
          <thead><tr><th scope="col">Pass</th><th scope="col">Kind and status then</th><th scope="col">What it found</th></tr></thead>
          <tbody>
            {passes.map((p, i) => (
              <tr key={`${p.date}-${p.by}-${i}`}>
                <td>{fmtDate(p.date)}<div className="dim">{readerText(p.by)}</div></td>
                <td>{p.kind === "targeted" ? "targeted search" : `systematic, ${p.status}`}{p.status_reason && <div className="dim">{readerText(p.status_reason)}</div>}</td>
                <td>{passOutcomeText(p, restricted, p === newestSystematic)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>

      {cq && bundle.events.length > 0 && (
        <aside className="rc-source-health" aria-labelledby="rc-sh-heading">
          <h3 id="rc-sh-heading" className="eyebrow rc-sh-head">Source health: the citations behind the published events</h3>
          <p className="small dim">Not part of research coverage. This describes the sources already cited, not how
            far the search got; the full picture is under Sources &amp; data quality.</p>
          <ul className="small citation-quality">
            <li>{cq.citations} citations; {cq.with_publication_date} carry a publication date stated by the source.</li>
            <li>Languages: {Object.entries(cq.languages).map(([k, n]) => `${LANGUAGE_LABEL[k] ?? k} ${n}`).join(", ") || "none"}.</li>
            <li>Event dates: {Object.entries(cq.event_date_precision).map(([k, n]) => `${n} to the ${k}`).join(", ") || "none"}.</li>
            {cq.link_check && <li>Automated link check, {fmtDate(cq.link_check_date ?? "")}: {cq.link_check.reachable} reachable, {cq.link_check.redirected} redirected, {cq.link_check.blocked} refused the check, {cq.link_check.dead} gone, {cq.link_check.error} failed to load.</li>}
          </ul>
          {cq.link_check_note && <p className="small dim">{readerText(cq.link_check_note)}</p>}
        </aside>
      )}
    </section>
  );
}

function laneId(systemId: string, lane: string): string {
  return `rc-lane-${systemId}-${lane.replace(/[^A-Za-z0-9_-]/g, "_")}`;
}

function LaneCard({ row, systemId, newestPassDate }: { row: LaneRow; systemId: string; newestPassDate: string | null }) {
  const l = row.lane;
  const required = Array.isArray(l.languages_required) ? l.languages_required : [];
  const ran = Array.isArray(l.languages_executed) ? l.languages_executed : [];
  const missing = missingLanguages(l);
  const work = workDone(l);
  const span = Array.isArray(row.pass.window) ? row.pass.window : null;
  const latestRelease = row.state === "complete" && l.source_window === "publisher_not_yet_released";
  const headingId = `${laneId(systemId, l.lane)}-h`;
  return (
    <li className={`rc-lane rc-lane-${row.state}`} id={laneId(systemId, l.lane)} tabIndex={-1} aria-labelledby={headingId}>
      <h3 id={headingId} className="rc-lane-head">
        <span className="mono rc-lane-id">{l.lane}</span>{" "}
        <span className="rc-family">{l.source_family ? readerText(l.source_family) : "Source family not recorded"}</span>
      </h3>
      <div className="rc-lane-state">
        <StateMark state={row.state} />
        {latestRelease && <span className="small dim"> · through the publisher's latest release; later items are not yet published</span>}
      </div>
      <dl className="rc-facts">
        <div><dt>How it is searched</dt><dd>{labelFor(UNIVERSE_TEXT, l.universe_kind ?? "not recorded")}{work && <span className="dim"> · {work}</span>}</dd></div>
        <div>
          <dt>Languages</dt>
          <dd>
            {required.length ? <>Required: {languageNames(required)}. Run: {ran.length ? languageNames(ran) : "none"}.</> : "Not recorded."}
            {missing.length > 0 && (
              <strong className="rc-missing"><MissingIcon /> Not run in: {languageNames(missing)}</strong>
            )}
          </dd>
        </div>
        <div><dt>Search window</dt><dd>{span ? `${fmtDate(span[0])} – ${fmtDate(span[1])}` : "Not recorded"}</dd></div>
        <div><dt>Covered through</dt><dd>{l.covered_through ? fmtDate(l.covered_through) : "No date was reached in full"}</dd></div>
        <div><dt>What the source allows</dt><dd>{labelFor(LANE_WINDOW_LABEL, l.source_window ?? "unknown")}</dd></div>
        {(row.pass.date !== newestPassDate || l.carried_forward) && (
          <div><dt>Logged in</dt><dd>The pass of {fmtDate(row.pass.date)}{l.carried_forward ? ", carried forward with no new work" : ""}</dd></div>
        )}
      </dl>
      {l.limitation && <p className="small rc-note"><span className="rc-note-label">What limited it:</span> {readerText(l.limitation)}</p>}
      {l.finding && (
        <details className="small rc-finding">
          <summary>What the search learned about the source</summary>
          <p>{readerText(l.finding)}</p>
        </details>
      )}
    </li>
  );
}

/** Text plus a distinct shape. Every state is drawn in the same colour: the shape and the words carry it. */
export function StateMark({ state }: { state: CoverageState }) {
  return (
    <span className={`rc-state rc-state-${state}`}>
      <StateIcon state={state} />
      <span className="rc-state-text">{COVERAGE_STATE_TEXT[state]}</span>
    </span>
  );
}

function StateIcon({ state }: { state: CoverageState }) {
  const common = { width: 14, height: 14, viewBox: "0 0 14 14", "aria-hidden": true, focusable: false, className: "rc-icon" } as const;
  switch (state) {
    case "complete":      // filled circle
      return <svg {...common}><circle cx="7" cy="7" r="5.5" fill="currentColor" /></svg>;
    case "partial":       // half-filled circle
      return <svg {...common}><circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" strokeWidth="1.5" /><path d="M7 2 A5 5 0 0 0 7 12 Z" fill="currentColor" /></svg>;
    case "not_started":   // empty circle
      return <svg {...common}><circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" strokeWidth="1.5" /></svg>;
    case "unavailable":   // crossed box
      return <svg {...common}><rect x="2" y="2" width="10" height="10" fill="none" stroke="currentColor" strokeWidth="1.5" /><path d="M4 4 L10 10 M10 4 L4 10" stroke="currentColor" strokeWidth="1.5" /></svg>;
    case "stopped":       // filled square: stop
      return <svg {...common}><rect x="2.5" y="2.5" width="9" height="9" fill="currentColor" /></svg>;
    case "archive_limit": // hollow diamond
      return <svg {...common}><path d="M7 1.5 L12.5 7 L7 12.5 L1.5 7 Z" fill="none" stroke="currentColor" strokeWidth="1.5" /></svg>;
    default:              // dotted ring: earlier format
      return <svg {...common}><circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray="1.5 2" /></svg>;
  }
}

function MissingIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden focusable={false} className="rc-icon">
      <circle cx="6" cy="6" r="4.5" fill="none" stroke="currentColor" strokeWidth="1.3" />
      <path d="M2.8 9.2 L9.2 2.8" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  );
}
