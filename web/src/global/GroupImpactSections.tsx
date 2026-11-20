import { useEffect, useMemo, useState } from "react";
import { fmtDate } from "../data";
import { localISODate } from "../freshness";
import { CountryLink } from "./feedItems";
import { ResearchPreviewTag } from "./Disclosure";
import RecordFilterBar from "./RecordFilterBar";
import { applyFilters, decodeFilters, encodeFilters, hidingFilters, withFilterQuery, withoutFilters, type FilterState } from "./recordFilters";
import {
  AttributionLine, ContextTimeline, ImpactCard, loadImpacts, loadRegionalContext,
  type ImpactRecord, type ImpactResearch, type ImpactsPayload, type RegionalContext,
} from "./impacts";
import { impactDateText, isItFailure, isMaliciousCause, placeText } from "./impacts/model";
import { labelOf, lowerLabel } from "./impacts/vocab";
import { contextDescribes } from "./impacts/brief/briefInputs";
import {
  IT_FAILURE, confidenceWord, contextTypesPresent, digitalSplit, filterContext, groupAttempts, groupImpactFilters, groupRecords,
  impactAnchor, recordFromAnchor, serviceGroups,
} from "./groupImpacts";
import { SECTIONS, withSection, type SectionId, type TellLine } from "./groupSections";
import type { GroupSystem } from "./manifest";

/** The regional overview's evidence sections (iteration 22): reported impacts, cyber and civilian
 *  services, the regional context timeline and research coverage.
 *
 *  A REGIONAL PICTURE, NOT A TARGET SET, as the rest of the page. What these sections add is
 *  evidence about what was reported, never a place to look: records are one list in date order,
 *  no country has a count, an attack is the country's and nothing finer, and the context is dated
 *  statements with no status.
 *
 *  WORDING (methodology §10). Only `ContextSection` may carry aggregate wording about the strait
 *  and shipping. Its fixed block, "Why there is no tanker map", is the one place that names what
 *  is not collected.
 */

export type Loaded<T> = { state: "loading" } | { state: "failed" } | { state: "ready"; data: T };

/** The impact layer's two page files, each loaded on its own: a broken context file leaves the
 *  records working, and the other way round. */
export function useImpactLayer(): { impacts: Loaded<ImpactsPayload>; regional: Loaded<RegionalContext> } {
  const [impacts, setImpacts] = useState<Loaded<ImpactsPayload>>({ state: "loading" });
  const [regional, setRegional] = useState<Loaded<RegionalContext>>({ state: "loading" });
  useEffect(() => {
    let live = true;
    loadImpacts().then((data) => { if (live) setImpacts({ state: "ready", data }); })
      .catch(() => { if (live) setImpacts({ state: "failed" }); });
    loadRegionalContext().then((data) => { if (live) setRegional({ state: "ready", data }); })
      .catch(() => { if (live) setRegional({ state: "failed" }); });
    return () => { live = false; };
  }, []);
  return { impacts, regional };
}

const NARROW = "(max-width: 600px)";

/** A phone-width window. The same breakpoint the filter bar and the stylesheet use. */
export function useNarrow(): boolean {
  const [narrow, setNarrow] = useState(() => typeof window !== "undefined" && !!window.matchMedia && window.matchMedia(NARROW).matches);
  useEffect(() => {
    if (!window.matchMedia) return;
    const mq = window.matchMedia(NARROW);
    const on = () => setNarrow(mq.matches);
    on();
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return narrow;
}

const plainClick = (e: { button: number; metaKey: boolean; ctrlKey: boolean; shiftKey: boolean }) =>
  e.button === 0 && !e.metaKey && !e.ctrlKey && !e.shiftKey;

const search = () => (typeof window === "undefined" ? "" : window.location.search);

/** The address of a section of this page: the page's own address with `section=` set. */
function sectionHref(id: SectionId): string {
  return withSection(search(), id) || "?";
}

/** In-page navigation. Links, so they can be copied, opened in a new tab and reached by Tab; a
 *  plain click moves within the page instead of reloading it. */
export function SectionNav({ current, onGo }: { current: SectionId | null; onGo: (id: SectionId) => void }) {
  return (
    <nav className="group-sections" aria-label="Sections of this page">
      <ul>
        {SECTIONS.map((s) => (
          <li key={s.id}>
            <a href={sectionHref(s.id)} aria-current={current === s.id ? "location" : undefined}
               onClick={(e) => { if (plainClick(e)) { e.preventDefault(); onGo(s.id); } }}>{s.label}</a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

const LABEL = new Map(SECTIONS.map((s) => [s.id, s.label]));

export const TELL_HEADING = "What this page can tell you";
export const TELL_LIST_ID = "group-tell-list";

/** The phone's way into the block: one phrase inside the caveat line that opens it. A phone's
 *  first screen has to hold the map (iteration 21), so the eight lines wait behind this; on a
 *  wider screen the block is simply there and this is not rendered. */
export function TellToggle({ open, onToggle }: { open: boolean; onToggle: (open: boolean) => void }) {
  return (
    <button type="button" className="disclosure-button linklike group-tell-toggle" aria-expanded={open} aria-controls={TELL_LIST_ID}
            onClick={() => onToggle(!open)}
            onKeyDown={(e) => { if (e.key === "Escape" && open) { e.preventDefault(); e.stopPropagation(); onToggle(false); } }}>
      {TELL_HEADING}<span aria-hidden="true">{open ? " −" : " +"}</span>
    </button>
  );
}

/** "What this page can tell you": eight questions, each answered in a sentence and linked to the
 *  section that holds the evidence. */
export function TellBlock({ lines, onGo }: { lines: TellLine[]; onGo: (id: SectionId) => void }) {
  return (
    <div className="group-tell">
      <h2 className="group-tell-head">{TELL_HEADING}</h2>
      <dl id={TELL_LIST_ID} className="group-tell-list small">
        {lines.map((l) => (
          <div key={l.id}>
            <dt>{l.question}</dt>
            <dd>{l.answer}{" "}
              <a href={sectionHref(l.section)} onClick={(e) => { if (plainClick(e)) { e.preventDefault(); onGo(l.section); } }}>
                {LABEL.get(l.section)}<span className="sr-only">: {l.question}</span>
              </a>
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function Loading({ what }: { what: string }) {
  return <p className="small dim" role="status">Loading {what}…</p>;
}

/** One failed file is ONE alert (iteration 22 closure): the impact records say it as an alert; the
 *  other sections that read the same file say it too, as a polite status, so a screen reader is not
 *  interrupted three times with the same news. */
function Failed({ what, still, alert = true }: { what: string; still: string; alert?: boolean }) {
  return <p className="warn-text small" role={alert ? "alert" : "status"}>{what} could not be loaded. {still}</p>;
}

// ---- reported impacts ---------------------------------------------------------------------------

function ImpactRecords({ payload, members, memberCount }: { payload: ImpactsPayload; members: readonly string[]; memberCount: number }) {
  const records = useMemo(() => groupRecords(payload, members), [payload, members]);
  const attempts = useMemo(() => groupAttempts(payload, members), [payload, members]);
  const { defs, fixed } = useMemo(() => groupImpactFilters(records, payload.vocabularies), [records, payload]);
  // The address is read once, when the records that define the filters are known.
  const fromLink = useMemo(() => decodeFilters(search(), defs), [defs]);
  const [edited, setEdited] = useState<FilterState | null>(null);
  const state = edited ?? fromLink.state;
  const today = localISODate(new Date());
  const shown = useMemo(() => applyFilters(records, defs, state, today), [records, defs, state, today]);

  const change = (next: FilterState) => {
    setEdited(next);
    // The filters live in the address, beside the group and the section, so a filtered list can be linked.
    const q = withFilterQuery(window.location.search, encodeFilters(defs, next));
    window.history.replaceState(null, "", `${window.location.pathname}${q ? `?${q}` : ""}${window.location.hash}`);
  };

  // A link to one record (`#impact-<id>`, as the compact lists further down write). The browser
  // scrolls to a record that is on the page; one the filters hide is shown first, by clearing the
  // filters that hide it and saying so. A filter never hides a linked record silently.
  const [linked, setLinked] = useState<string | null>(null);
  const [cleared, setCleared] = useState(false);
  useEffect(() => {
    const read = () => setLinked(recordFromAnchor(window.location.hash));
    read();
    window.addEventListener("hashchange", read);
    return () => window.removeEventListener("hashchange", read);
  }, []);
  useEffect(() => {
    if (!linked) return;
    const record = records.find((r) => r.impact_id === linked);
    if (!record) { setLinked(null); return; }
    const hiding = hidingFilters(record, defs, state, today);
    if (hiding.length > 0) { setCleared(true); change(withoutFilters(state, hiding)); return; }
    const el = document.getElementById(impactAnchor(linked));
    el?.scrollIntoView({ block: "start" });
    el?.focus({ preventScroll: true });
    setLinked(null);
  }, [linked, records, defs, state]);  // eslint-disable-line react-hooks/exhaustive-deps
  const notes = cleared ? [...fromLink.notes, "A filter was cleared to show the record you opened."] : fromLink.notes;

  return (
    <>
      <p className="small">{payload.scope_statement}</p>
      <p className="small impact-corpus-note" role="note">
        <strong>Reviewed records from a separate corpus that is not scored.</strong> They enter no index, no country's
        event count and no research assessment. The list is in date order only: nothing here is counted, grouped or
        ordered by country, and a longer list is a larger set of published records, not a more affected region.
      </p>
      {records.length === 0 ? (
        <p className="small" role="status">
          {payload.records.length === 0 && payload.empty_reason
            ? payload.empty_reason
            : `No impact record for these ${memberCount} countries in the current reviewed corpus. That describes this corpus, not the region.`}
        </p>
      ) : (
        <>
          <RecordFilterBar defs={defs} state={state} onChange={change} records={records} shown={shown.length} today={today}
                           noun="published impact records" notes={notes} fixed={fixed} />
          <ol className="impact-list" aria-label="Impact records, newest first">
            {shown.map((r) => <li key={r.impact_id} id={impactAnchor(r.impact_id)} tabIndex={-1}><ImpactCard record={r} /></li>)}
          </ol>
          {shown.length === 0 && <p className="small dim">No record matches the filters that are on.</p>}
        </>
      )}
      {attempts.length > 0 && (
        <div className="impact-attempts">
          <h3>{payload.attempts_label ?? "Attempts with no reported service disruption"}</h3>
          <p className="small dim">Documented attempts that sources say did not interrupt a service. Listed apart, and never counted with the records above.</p>
          <ol className="impact-list" aria-label="Attempts with no reported service disruption">
            {attempts.map((r) => <li key={r.impact_id}><ImpactCard record={r} /></li>)}
          </ol>
        </div>
      )}
      {payload.caveats.length > 0 && (
        <details className="small impact-caveats">
          <summary>Notes on this corpus</summary>
          <ul>{payload.caveats.map((c) => <li key={c}>{c}</li>)}</ul>
        </details>
      )}
    </>
  );
}

export function ReportedImpacts({ impacts, members, memberCount }: { impacts: Loaded<ImpactsPayload>; members: readonly string[]; memberCount: number }) {
  if (impacts.state === "loading") return <Loading what="the impact records" />;
  if (impacts.state === "failed") {
    return <Failed what="The impact records" still="That is a failed download, not a finding. The rest of this page is unaffected, and the country systems' reviewed energy events are listed below." />;
  }
  return <ImpactRecords payload={impacts.data} members={members} memberCount={memberCount} />;
}

// ---- cyber and civilian services ----------------------------------------------------------------

function definition(payload: ImpactsPayload, vocabulary: string, id: string): string | null {
  return (payload.vocabularies[vocabulary] ?? []).find((e) => e.id === id)?.definition ?? null;
}

/** One cyber record or IT failure, in brief: when, where, what, who is said to be responsible and
 *  how strong the evidence is, with a link to the full record. Not a second copy of the card: the
 *  card and its evidence inspector are under Reported impacts, once. */
function DigitalRow({ r }: { r: ImpactRecord }) {
  const when = impactDateText(r);
  const place = placeText(r);
  return (
    <li className="digital-row">
      <div className="event-head"><span className="mono service-when">{when}</span> <span className="service-place">{place}</span></div>
      <div className="event-tags">
        <span className="event-tag">{labelOf("sectors", r.sector)}</span>
        {r.cyber_mechanism && <span className="event-tag">{isItFailure(r) ? "IT failure" : "Mechanism"}: {lowerLabel("cyber_mechanisms", r.cyber_mechanism)}</span>}
      </div>
      <p className="small digital-summary">{r.summary}</p>
      <AttributionLine a={r.attribution} maliciousCause={isMaliciousCause(r)} />
      <p className="small dim digital-foot">Evidence confidence: {confidenceWord(r)}.{" "}
        <a href={`#${impactAnchor(r.impact_id)}`}>Full record and sources<span className="sr-only">: {when}, {place}</span></a></p>
    </li>
  );
}

/** A cause's served definition. A malicious cause whose definition does not say so (the served
 *  "cyber" reads "caused through computer systems") says it here, so cyber is never read as an
 *  ordinary IT failure. */
export function causeDefinition(f: { definition?: string; malicious?: boolean | null }): string {
  const d = f.definition ?? "No definition is served for this cause.";
  return f.malicious === true && !/malic|attack/i.test(d) ? `${d} Malicious: an attack, not an accident or a failure.` : d;
}

/** The IT-failure definition, saying once that it is not an attack: the served definition already
 *  says so ("never counted as one"), and repeating it read as a stutter. */
export function itFailureDefinition(served: string | null): string {
  const d = served ?? "Digitally triggered without malice, such as a faulty software update or a system failure.";
  return /\bnever\b/i.test(d) ? d : `${d} Not an attack, and never listed as cyber.`;
}

function Services({ payload, members }: { payload: ImpactsPayload; members: readonly string[] }) {
  const records = useMemo(() => groupRecords(payload, members), [payload, members]);
  const groups = useMemo(() => serviceGroups(records, payload.vocabularies), [records, payload]);
  const { cyber, itFailures } = useMemo(() => digitalSplit(records), [records]);
  const families = payload.vocabularies.cause_families ?? [];
  const itLabel = (payload.vocabularies.digital_categories ?? []).find((d) => d.id === IT_FAILURE)?.label ?? "IT failure";
  return (
    <>
      <h3>What each reported cause means</h3>
      <p className="small dim">Every record names one reported cause, from the list below. The words are the taxonomy's own.</p>
      <dl className="small cause-kinds">
        {families.map((f) => <div key={String(f.id)}><dt>{f.label}</dt><dd>{causeDefinition(f)}</dd></div>)}
        <div><dt>{itLabel}</dt><dd>{itFailureDefinition(definition(payload, "digital_categories", IT_FAILURE))}</dd></div>
      </dl>

      <h3>Documented effects on civilian services, by service</h3>
      {groups.length === 0 ? (
        <p className="small" role="status">No record for these countries documents an effect on a named civilian service in the current reviewed corpus. That is not a finding that no service was affected.</p>
      ) : (
        <>
          <p className="small dim">Each figure is the source's own, in the source's own unit: people are not customers are not households, and nothing
            is converted or added up. Services follow the vocabulary's order and, inside a service, the lines are in date order. A record that
            names two services is listed under both.</p>
          {groups.map((g) => (
            <section key={g.service} className="service-group" aria-label={`${g.label}: documented effects`}>
              <h4>{g.label}</h4>
              <ul className="service-rows small">
                {g.rows.map((row) => (
                  <li key={row.key}>
                    <span className="mono service-when">{row.when}</span> <span className="service-place">{row.place}</span>
                    <span className="dim"> · {row.line.scope.toLowerCase()}</span>
                    {row.line.affected && <> · affected: {row.line.affected}</>}
                    {row.line.unitNote && <span className="dim"> ({row.line.unitNote}; not converted)</span>}
                    {row.line.duration && <> · duration: {row.line.duration}</>}
                    {" "}<span className="event-tag">Cause: {row.cause}</span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </>
      )}

      <h3>Cyber records</h3>
      {cyber.length === 0
        ? <p className="small" role="status">No cyber record for these countries in the current reviewed corpus. That describes this corpus: it is not a finding that none occurred.</p>
        : (
          <>
            <p className="small dim">The records under Reported impacts whose reported cause is cyber, in date order. Attribution is shown as who attributes and how firmly. There is no summary by actor.</p>
            <ol className="digital-list" aria-label="Cyber records, newest first">
              {cyber.map((r) => <DigitalRow key={r.impact_id} r={r} />)}
            </ol>
          </>
        )}
      {itFailures.length > 0 && (
        <>
          <h3>{itLabel === "IT failure" ? "IT failures" : itLabel} (not attacks)</h3>
          <ol className="digital-list" aria-label="IT failures, newest first">
            {itFailures.map((r) => <DigitalRow key={r.impact_id} r={r} />)}
          </ol>
        </>
      )}
    </>
  );
}

export function ServicesSection({ impacts, members }: { impacts: Loaded<ImpactsPayload>; members: readonly string[] }) {
  if (impacts.state === "loading") return <Loading what="the impact records" />;
  if (impacts.state === "failed") return <Failed what="The impact records" still="That is a failed download, not a finding." alert={false} />;
  return <Services payload={impacts.data} members={members} />;
}

// ---- regional context ---------------------------------------------------------------------------

/** The fixed block above the timeline. The one place on this site that names what is not collected
 *  about shipping, as a refusal. Rendered whether or not the context file loads. */
export const NO_TANKER_MAP = {
  heading: "Why there is no tanker map",
  lines: [
    "This product publishes aggregate, dated, sourced statements only. It does not collect vessel positions, routes, bypass capacity or which facility depends on the strait, because those serve operations, not understanding.",
    "Regional context enters no index and no country's record. A price movement is not an infrastructure loss.",
  ],
} as const;

function Context({ ctx }: { ctx: RegionalContext }) {
  const types = useMemo(() => contextTypesPresent(ctx), [ctx]);
  const [chosen, setChosen] = useState<string[]>([]);
  const shown = useMemo(() => filterContext(ctx, chosen), [ctx, chosen]);
  const toggle = (id: string) => setChosen((c) => (c.includes(id) ? c.filter((x) => x !== id) : [...c, id]));
  return (
    <>
      {types.length > 1 && (
        <fieldset className="ctx-filter small">
          <legend>Show statements about</legend>
          {types.map((t) => {
            const id = String(t.id);
            return <label key={id}><input type="checkbox" checked={chosen.includes(id)} onChange={() => toggle(id)} /> {t.label}</label>;
          })}
          <button type="button" className="ghost" onClick={() => setChosen([])} disabled={chosen.length === 0}>Show every kind</button>
        </fieldset>
      )}
      <p className="small ctx-count" role="status">
        Showing <strong>{shown.entries.length}</strong> of <strong>{ctx.entries.length}</strong> dated statements, newest first.
        Each is as of its own date. No single status is given.
      </p>
      <ContextTimeline ctx={shown} />
      {/* Here and not under Research coverage: a source family's name may speak of shipping, and
          this is the one section that may. */}
      {ctx.research && (
        <>
          <h3>How these statements were researched</h3>
          <Families research={ctx.research} caption="Source families read for regional context statements" />
        </>
      )}
    </>
  );
}

export function ContextSection({ regional, groupId }: { regional: Loaded<RegionalContext>; groupId: string | null }) {
  return (
    <>
      <div className="no-tanker-map" role="note" aria-label={NO_TANKER_MAP.heading}>
        <h3>{NO_TANKER_MAP.heading}</h3>
        {NO_TANKER_MAP.lines.map((l) => <p key={l} className="small">{l}</p>)}
      </div>
      {/* The group's id arrives with the manifest: until then nothing is said about whose context this is. */}
      {(regional.state === "loading" || (regional.state === "ready" && groupId == null)) && <Loading what="the regional context" />}
      {regional.state === "failed" && <Failed what="The regional context statements" still="The rest of this page is unaffected." />}
      {regional.state === "ready" && groupId != null && (contextDescribes(regional.data, groupId)
        ? <Context ctx={regional.data} />
        : <p className="small" role="status">No regional context is published for this group.</p>)}
    </>
  );
}

// ---- research coverage --------------------------------------------------------------------------

function Families({ research, caption }: { research: ImpactResearch; caption: string }) {
  if (research.source_families.length === 0) return <p className="small dim">{caption}: no source family is recorded yet.</p>;
  return (
    <ul className="family-list small" aria-label={caption}>
      {research.source_families.map((f, i) => (
        <li key={`${f.family}:${i}`}>
          <strong>{f.family}</strong>{f.status ? <span className="dim"> · {f.status}</span> : null}{f.window ? <span className="dim"> · {f.window}</span> : null}
          {f.method && <div>{f.method}</div>}
          {f.limitation && <div className="dim">Limit: {f.limitation}</div>}
        </li>
      ))}
    </ul>
  );
}

export const WITHHELD = [
  "For an attack or sabotage record: the place, the facility, the operator, the method, the source's headline and any later status. The record is the country's and nothing finer.",
  "For every record: coordinates and anything finer than a first-level region.",
  "For every country here: the restart, repair, operating rate or remaining capacity of an attacked facility is neither researched nor published.",
  "For the regional context: only aggregate, dated statements are kept, with no status and nothing about any single asset.",
  "Nothing on this page orders countries by a figure, and no figure here is a count of incidents per country.",
] as const;

export function CoverageSection({ impacts, systems }: { impacts: Loaded<ImpactsPayload>; systems: GroupSystem[] }) {
  return (
    <>
      <h3>How the impact layer was researched</h3>
      {impacts.state === "loading" && <Loading what="the research summary" />}
      {impacts.state === "failed" && <Failed what="The impact layer's research summary" still="Each country's own coverage, below, is unaffected." alert={false} />}
      {impacts.state === "ready" && (
        <>
          <p className="small">
            {impacts.data.research.window && <>Search period {fmtDate(impacts.data.research.window.start)} to {impacts.data.research.window.end === "present" ? "the present" : fmtDate(impacts.data.research.window.end)}. </>}
            {impacts.data.research.status && <>State: {impacts.data.research.status}. </>}
            {impacts.data.research.latest_research_date ? <>Latest research {fmtDate(impacts.data.research.latest_research_date)}. </> : <>No research date is recorded. </>}
            The impact layer is researched as one corpus, so these notes describe all of it and not only these countries.
            It is not a census: an absent record is not an absent disruption.
          </p>
          <Families research={impacts.data.research} caption="Source families searched for impact records" />
          {(impacts.data.research.limitations ?? []).length > 0 && (
            <ul className="small research-limits" aria-label="Known limits of the impact research">
              {(impacts.data.research.limitations ?? []).map((l) => <li key={l}>{l}</li>)}
            </ul>
          )}
        </>
      )}

      <h3 id="what-is-withheld">What is withheld</h3>
      <ul className="small withheld-list">{WITHHELD.map((w) => <li key={w}>{w}</li>)}</ul>

      <h3>Each country's own research coverage</h3>
      <p className="small dim">Alphabetical. Each country's page has a Research coverage tab that lists its search source group by source group.</p>
      <ul className="coverage-links small">
        {systems.map((s) => (
          <li key={s.system_id}>
            <CountryLink id={s.system_id} name={s.name} />
            <span className="dim"> · {s.last_systematic_pass ? `latest systematic pass ${fmtDate(s.last_systematic_pass)}` : "no systematic research pass yet"}</span>
            {s.maturity === "research_preview" && <> <ResearchPreviewTag /></>}
          </li>
        ))}
      </ul>
    </>
  );
}
