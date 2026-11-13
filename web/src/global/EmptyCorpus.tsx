import {
  CAMPAIGN_STATE_LABEL, ENVIRONMENT_LABEL, LANE_STATE_LABEL, labelFor, languageNames, type CountryBundle,
} from "./manifest";
import { rowForSystem, type EnergyContext } from "./context";
import { NationalFigures } from "./WorldContext";
import { EMPTY_CORPUS_LEAD } from "./countryCopy";
import { readerText } from "./readerText";
import { fmtDate } from "../data";
import "../styles/country.css";

/** The Reported events tab of a country with no published record (iteration 21).
 *
 *  An empty page is a statement about the dataset, so it leads with that, then says what was
 *  searched, how the country reports, its national context, the sources, the safeguards that
 *  apply and what is still incomplete. No count is shown here: not of records, not of anything
 *  held back, and never a zero standing in for "nothing happened".
 */
export function EmptyCorpus({ bundle, ctx, onTab }: {
  bundle: CountryBundle; ctx: EnergyContext | null; onTab: (t: "research" | "sources" | "context" | "method") => void;
}) {
  const s = bundle.system;
  const rf = s.research_freshness;
  const passes = s.research_log.passes.filter((p) => p.kind === "systematic");
  const lanes = (passes[passes.length - 1]?.lanes ?? []).filter((l) => l.execution);
  const required = [...new Set(lanes.flatMap((l) => l.languages_required ?? []))].sort();
  const families = [...new Set(lanes.map((l) => l.source_family).filter((x): x is string => !!x))];
  const used = s.sources.filter((x) => !x.role.startsWith("rejected"));
  const row = ctx ? rowForSystem(ctx, s.system_id) : null;
  const campaign = s.campaign_state && s.campaign_state.state !== "NO_ACTIVE_CAMPAIGN" ? s.campaign_state : null;
  const gaps = [...lanes.filter((l) => l.limitation).map((l) => readerText(l.limitation)), ...s.research_gaps];
  return (
    <div className="empty-corpus" aria-label="No qualifying records">
      <p className="empty-lead">{EMPTY_CORPUS_LEAD}</p>
      <p className="small">Nothing on this page has passed the inclusion rule and review yet. That describes this
        dataset, not {s.name}.</p>

      <h3 className="eyebrow">What was searched</h3>
      {passes.length === 0 ? (
        <p className="small">No systematic search has been run yet.</p>
      ) : (
        <>
          <p className="small">
            {rf.coverage_window && <>Research period {fmtDate(rf.coverage_window[0])} – {fmtDate(rf.coverage_window[1])}. </>}
            {rf.last_systematic_pass && <>Last worked on {fmtDate(rf.last_systematic_pass)}. </>}
            {families.length > 0 && <>Source groups: {families.join("; ")}. </>}
            {required.length > 0 && <>Languages the plan requires: {languageNames(required)}.</>}
          </p>
          {rf.lane_states && Object.keys(rf.lane_states).length > 0 && (
            <ul className="small">
              {Object.entries(rf.lane_states).map(([k, n]) => (
                <li key={k}>{n} {n === 1 ? "source group" : "source groups"}: {labelFor(LANE_STATE_LABEL, k).toLowerCase()}</li>
              ))}
            </ul>
          )}
        </>
      )}
      <button type="button" className="ghost" onClick={() => onTab("research")}>See what was searched</button>

      <h3 className="eyebrow">How {s.name} reports disruptions</h3>
      <p className="small"><strong>{labelFor(ENVIRONMENT_LABEL, s.reporting_environment)}.</strong> {s.reporting_environment_text}</p>

      <h3 className="eyebrow">National context</h3>
      {row && ctx ? (
        <div className="national-block">
          <NationalFigures row={row} ctx={ctx} />
          <p className="small dim">{ctx.comparison_year} national figures from {ctx.source.name}. They describe the size of
            the energy system: context, never disruption and never importance.</p>
        </div>
      ) : (
        <p className="small dim">National figures are on the Energy context tab.</p>
      )}
      <button type="button" className="ghost" onClick={() => onTab("context")}>Open the Energy context tab</button>

      <h3 className="eyebrow">Sources</h3>
      <p className="small">{used.length} registered sources were set up for this country, among them{" "}
        {used.slice(0, 4).map((x) => x.name).join("; ")}{used.length > 4 ? "; and others" : ""}.</p>
      <button type="button" className="ghost" onClick={() => onTab("sources")}>See the registered sources</button>

      <h3 className="eyebrow">Publication safeguards</h3>
      <ul className="small">
        {campaign && (
          <li>{labelFor(CAMPAIGN_STATE_LABEL, campaign.state)}. A reported attack that meets the rule is recorded as having
            happened, with its date, the kind of infrastructure and the effect reported at the time; whether a facility
            has been repaired, restarted or is operating is not published.</li>
        )}
        {s.geography.precision_policy && <li>{readerText(s.geography.precision_policy.reason)}</li>}
        <li>No record carries coordinates; nothing is placed more precisely than a first-level region.</li>
      </ul>

      <h3 className="eyebrow">What remains incomplete</h3>
      {gaps.length > 0 ? (
        <ul className="small">{gaps.map((g, i) => <li key={i}>{g}</li>)}</ul>
      ) : (
        <p className="small">The research log lists no open gap; events the sources never reported are still missing.</p>
      )}
      <button type="button" className="ghost" onClick={() => onTab("method")}>Why there is no score</button>
    </div>
  );
}
