import { useId, useRef, useState } from "react";
import {
  CALENDAR_LABEL, LANGUAGE_LABEL, RECOVERY_KIND_LABEL, RECOVERY_LABEL, REVIEW_STATUS_LABEL, dirFor, labelFor,
  type CountryBundle, type CountryEvent,
} from "./manifest";
import {
  LINK_STATE_LABEL, countLine, eventAnchor, eventPlacement, headlinesAllowed, notEstablished, originLabel,
  originSummary, placementKind, plainBasis, roleVerdicts,
} from "./evidence";
import { PLACEMENT_LABEL } from "./placement";
import { fmtDate } from "../data";
import "../styles/country.css";

/** One reported record on a country page (iteration 21).
 *
 *  Read top to bottom: when, what kind of infrastructure, what caused it, what was reported to
 *  happen, how precisely it is placed, and what evidence it rests on. The Evidence Inspector
 *  below it answers why it is included and what it does not establish, in plain words.
 *
 *  Under active-campaign safeguards the card shows what the record publishes and nothing more:
 *  no headline, no capacity figure, no later status of the facility.
 */

/** A month-precision date is shown as a month: printing "1 Apr" would invent a day. */
export function fmtEventDate(e: CountryEvent): string {
  // Formatted from the string, never through the browser's Date parser (iteration 20).
  const d = e.date_precision === "month" ? fmtDate(e.date.slice(0, 7)) : fmtDate(e.date);
  return e.date_end ? `${d} – ${fmtDate(e.date_end)}` : d;
}

function recoveryText(e: CountryEvent): string {
  const r = e.recovery;
  if (r.research_status === "EVIDENCE_FOUND" && r.kind) return labelFor(RECOVERY_KIND_LABEL, r.kind);
  return labelFor(RECOVERY_LABEL, r.research_status);
}

/** A first-level unit's name for a code, from the system's own regions; the code if unknown. */
function unitName(bundle: CountryBundle, code: string): string {
  const f = bundle.regions.features.find((x) => (x.properties as { code?: string } | null)?.code === code);
  return ((f?.properties as { name?: string } | null)?.name) ?? code;
}

function hostOf(url: string): string {
  try { return new URL(url).hostname; } catch { return url; }
}

const ROLE_TEXT: Record<string, string> = {
  official: "official body", government: "government", regulator: "regulator", operator: "operator",
  dataset: "dataset", media: "news media", industry: "industry press",
};

/** `inEpisode`: drawn inside its episode's group, which already names the episode. */
export function EventCard({ e, bundle, inEpisode = false, targeted = false }: {
  e: CountryEvent; bundle: CountryBundle; inEpisode?: boolean; targeted?: boolean;
}) {
  const sys = bundle.system;
  const tax = sys.taxonomy;
  const [open, setOpen] = useState(false);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();
  const recClass = e.recovery.kind ?? e.recovery.research_status;
  const ep = bundle.episodes.find((x) => x.episode_id === e.episode_id);
  const kind = placementKind(e, sys);
  const place = eventPlacement(e, sys);
  const origins = originSummary(e);
  const headlines = headlinesAllowed(e, sys);
  const covered = !!e.publication;
  const unit = sys.geography.unit_label;
  // Null for a campaign-covered record whose id could name a facility: no anchor, so no link.
  const anchor = eventAnchor(e, sys.system_id);
  const title = e.facility_name ?? e.region_name ?? sys.name;
  return (
    <li className={`event-item event-card placement-${kind}${targeted ? " targeted" : ""}`}
        id={anchor ?? undefined}>
      <div className="event-head">
        <span className="event-date mono">{fmtEventDate(e)}</span>
        <span className="event-tags">
          <span className="event-tag">{labelFor(tax.asset_classes, e.asset_class)}</span>
          <span className="event-tag">{labelFor(tax.causes, e.cause)}</span>
        </span>
      </div>
      <div className="event-title">{title}</div>
      <p className="small event-summary">{e.summary}</p>
      {e.source_date_text && e.date_calendar && e.date_calendar !== "gregorian" && (
        <p className="small dim">
          Date in the source: <bdi lang={e.date_calendar === "solar_hijri" ? "fa" : "ar"}>{e.source_date_text}</bdi>{" "}
          ({labelFor(CALENDAR_LABEL, e.date_calendar)}). {e.conversion_basis}
        </p>
      )}
      <dl className="event-facts small">
        {e.effect && (<div><dt>Reported effect</dt><dd>{e.effect}</dd></div>)}
        <div>
          <dt>Placement</dt>
          <dd>
            <span className="placement-level">{PLACEMENT_LABEL[place]}</span>
            {kind === "region" && <>: {e.region_name}</>}
            {kind === "country_attack" && <span className="dim"> — published for the country as a whole, with no region or facility</span>}
            {kind === "country_rule" && <span className="dim"> — every record of this country is kept for the country as a whole</span>}
            {kind === "national" && <span className="dim"> — not placed in one {unit}</span>}
            {kind !== "country_attack" && e.regions_affected.length > 0 && (
              <div className="dim">Regions affected: {e.regions_affected.map((c) => unitName(bundle, c)).join(", ")}</div>
            )}
          </dd>
        </div>
        <div>
          {/* "Later status" under the campaign rule: the record publishes no recovery at all. */}
          <dt>{covered ? "Later status" : "Recovery"}</dt>
          <dd>
            <span className={`rec rec-${recClass.toLowerCase()}`}>{recoveryText(e)}</span>
            {e.recovery.date && <span className="dim"> ({fmtDate(e.recovery.date)})</span>}
            {e.recovery.evidence && <span className="dim"> — {e.recovery.evidence}</span>}
          </dd>
        </div>
        <div>
          <dt>Review</dt>
          <dd className="review-note">
            <span className={`review-${e.review.review_status}`}>{labelFor(REVIEW_STATUS_LABEL, e.review.review_status)}</span>
            {e.review.review_status !== "legacy_single_review" && e.review.disposition === "corrected" && " · corrected on review"}
          </dd>
        </div>
      </dl>
      {ep && ep.records > 1 && !inEpisode && (
        <p className="small dim episode-note">Part of an episode: {ep.name} ({ep.records} records)</p>
      )}
      {(!ep || ep.records <= 1) && (
        <p className="small dim episode-note">Standalone: not linked to any other record (an episode of one).</p>
      )}
      {e.publication && <p className="small dim withheld-note">{e.publication.note}</p>}

      <div className="evidence-block">
        <div className="evidence-head">
          <span className="eyebrow">Evidence</span>
          <span className="small origin-count">{countLine(origins)}</span>
        </div>
        {origins.discoveryOnly && (
          <p className="small discovery-only">This record rests only on Wikipedia or a content aggregator. They restate
            other publishers' reporting, so no originating statement is cited.</p>
        )}
        <ul className="source-list sources">
          {e.sources.map((s, i) => (
            <li key={i} className="source-row small">
              <span className="source-meta">
                <a href={s.url} target="_blank" rel="noopener noreferrer">{s.publisher ?? hostOf(s.url)}</a>
                {s.date && <span className="dim">{fmtDate(s.date)}</span>}
                {s.language && <span className="dim">{LANGUAGE_LABEL[s.language] ?? s.language}</span>}
              </span>
              {/* A non-English source keeps its own headline, in its own script and direction; the
                  English gloss is ours and sits on its own line. */}
              {headlines && s.title_original && (
                <span className="source-title"><bdi lang={s.language} dir={dirFor(s.language)}>{s.title_original}</bdi></span>
              )}
              {headlines && s.title_original && s.title_en && (
                <span className="source-gloss dim">Gloss: {s.title_en}</span>
              )}
            </li>
          ))}
        </ul>
        {e.review.source_access === "not recorded by the research lane" && (
          <p className="small dim">{e.review.review_status === "legacy_single_review"
            ? "Whether these were read was not recorded."
            : "The researcher's reading was not recorded; the independent review opened them."}</p>
        )}
      </div>

      {/* The anchor already existed and "Copy view link" keeps it, but nothing on the page exposed
          it: an analyst citing one record had no way to get its address. A plain link, so it can be
          copied, opened or bookmarked without a clipboard permission. Placed BEFORE the toggle so the toggle's
          next Tab stop stays its own panel. */}
      {anchor && <a className="ev-permalink" href={`#${anchor}`}>Link to this record<span className="sr-only">: {title}, {fmtEventDate(e)}</span></a>}
      {/* The hidden words make each toggle's name unique: a screen reader's list of buttons
          otherwise reads "Evidence inspector" a hundred times. Only what the card already shows. */}
      <button ref={toggleRef} type="button" className="ghost ev-inspector-toggle" aria-expanded={open}
              aria-controls={panelId} onClick={() => setOpen((o) => !o)}
              onKeyDown={(ev) => { if (ev.key === "Escape" && open) { ev.preventDefault(); ev.stopPropagation(); setOpen(false); } }}>
        {open ? "Close evidence inspector" : "Evidence inspector"}
        <span className="sr-only">: {title}, {fmtEventDate(e)}</span>
      </button>
      {open && (
        <EvidenceInspector id={panelId} e={e} bundle={bundle}
          onClose={() => { setOpen(false); toggleRef.current?.focus(); }} />
      )}
    </li>
  );
}

/** Plain answers about one record. Rendered only while open, so a closed card carries none of it. */
export function EvidenceInspector({ id, e, bundle, onClose }: {
  id: string; e: CountryEvent; bundle: CountryBundle; onClose: () => void;
}) {
  const sys = bundle.system;
  const origins = originSummary(e);
  const covered = !!e.publication;
  const verdicts = roleVerdicts(e);
  const threshold = sys.inclusion_threshold;
  const clause = e.criterion_met != null ? threshold.clauses[String(e.criterion_met)] : null;
  return (
    <section id={id} className="ev-inspector small" aria-label="Evidence inspector"
             onKeyDown={(ev) => { if (ev.key === "Escape") { ev.stopPropagation(); onClose(); } }}>
      <h4>Why this record is included</h4>
      <p className="ev-inspector-basis">{plainBasis(e, threshold)}</p>
      <details className="ev-inspector-technical">
        <summary>Technical detail</summary>
        <p>Inclusion rule, version {threshold.version}{e.criterion_met != null ? `, clause ${e.criterion_met}` : ""}
          {clause ? `: ${clause}` : "."}</p>
        {e.threshold_basis && <p>As recorded: {e.threshold_basis}</p>}
        <p className="dim">The rule: {threshold.rule}</p>
      </details>

      <h4>Where the report came from</h4>
      <ul className="ev-inspector-sources">
        {e.sources.map((s, i) => (
          <li key={i}>
            <strong>{s.publisher ?? hostOf(s.url)}</strong>
            {" — "}{s.source_role ? labelFor(ROLE_TEXT, s.source_role) : "role not recorded"}
            {s.language ? `, ${LANGUAGE_LABEL[s.language] ?? s.language}` : ""}
            {s.date ? `, published ${fmtDate(s.date)}` : ", publication date not stated"}.
            <div className="dim">
              {s.opened === true ? "Opened by the researcher. " : s.opened === false ? "Recorded as not opened by the researcher. " : ""}
              Link: <span className={`link-state link-${s.link_check ?? "unchecked"}`}>
                {s.link_check ? LINK_STATE_LABEL[s.link_check] ?? s.link_check : "not link-checked"}</span>
              {s.link_check && sys.citation_quality?.link_check_date ? ` (${fmtDate(sys.citation_quality.link_check_date)})` : ""}.
            </div>
          </li>
        ))}
      </ul>

      <h4>How many independent originating statements support it</h4>
      <p className="ev-inspector-origins">
        {countLine(origins)}.{" "}
        {origins.origins.length > 0 && <>Originating: {origins.origins.map(originLabel).join("; ")}.</>}
      </p>
      {origins.discoveryOnly ? (
        <p>Every citation is Wikipedia or a content aggregator. They restate what others reported, so they count
          for no originating statement: this record is supported by no cited original report.</p>
      ) : origins.discoveryCitations > 0 ? (
        <p className="dim">{origins.discoveryCitations} of the citations {origins.discoveryCitations === 1 ? "is" : "are"} Wikipedia
          or a content aggregator and count for none.</p>
      ) : null}
      <p className="dim">An originating statement is a wire service the citation names, otherwise the website it sits on:
        two reports from one agency count once, and a wire story republished by several outlets counts once. Republication
        a citation does not name cannot be seen, so this can undercount independence but never overstate it.</p>

      <h4>What this report does not establish</h4>
      <ul className="ev-inspector-limits">
        {notEstablished(e).map((line, i) => <li key={i}>{line}</li>)}
      </ul>

      <h4>Review</h4>
      <p className="ev-inspector-review">
        {labelFor(REVIEW_STATUS_LABEL, e.review.review_status)}
        {e.review.review_status !== "legacy_single_review" && e.review.disposition === "corrected" ? "; the text was corrected on review" : ""}.
        {verdicts.length > 0 && <> Verdicts: {verdicts.join("; ")}.</>}
        {e.review.reviewed_at && <> Reviewed {fmtDate(e.review.reviewed_at)}.</>}
      </p>
      {covered && (
        <p className="dim">Published under active-campaign safeguards: see the note on this record for what is not shown.</p>
      )}
      <button type="button" className="ghost ev-inspector-close" onClick={onClose}>Close</button>
    </section>
  );
}
