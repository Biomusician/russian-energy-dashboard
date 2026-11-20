import { fmtDate } from "../../data";
import { LANGUAGE_LABEL, dirFor } from "../manifest";
import { ConfidenceBreakdown, useConfidenceMethod } from "./ConfidenceChip";
import {
  LEAD_ADDED_NOT_COUNTED, NO_CONFIDENCE_REASON, SELF_CLAIM_NOTE, claimSupport, confidenceLabel, isAbstracted, notEstablished, originsText, selfClaimText,
  selfClaimsOf, sourceKind,
} from "./model";
import { definitionOf, labelOf, lowerLabel, useImpactVocab, vocabulary } from "./vocab";
import type { ImpactRecord, ImpactSource } from "./types";
import "../../styles/impacts.css";

/** The Evidence Inspector for an impact record (iteration 22).
 *
 *  Answers, in this order: which claim rests on which source; who each source is, through what
 *  medium, and whether its link still opens; what produced the evidence confidence; and what the
 *  evidence does not establish.
 *
 *  A social post is shown as a medium, not a quality level: its platform, the account, the account
 *  tier and HOW the account's identity was established. Posts are not reproduced.
 *
 *  An abstracted (attack or sabotage) record shows no source headline: a headline can name what the
 *  record withholds.
 */

function hostOf(url: string): string {
  try { return new URL(url).hostname; } catch { return url; }
}

function publisherOf(s: ImpactSource): string {
  return s.publisher ?? hostOf(s.url);
}

function SourceRow({ s, headlines }: { s: ImpactSource; headlines: boolean }) {
  const link = s.link_check ?? "unchecked";
  return (
    <li className="imp-source">
      <div>
        <a href={s.url} target="_blank" rel="noopener noreferrer"><strong>{publisherOf(s)}</strong></a>
        {" — "}{sourceKind(s)}
        {s.date ? `, ${fmtDate(s.date)}` : ", date not stated"}
        {s.language ? `, ${LANGUAGE_LABEL[s.language] ?? s.language}` : ""}.
      </div>
      {s.social && (
        <div className="imp-social">
          Posted on {s.social.platform} by {s.social.display_name ?? "an account"}{s.social.handle ? ` (${s.social.handle})` : ""}.{" "}
          Account tier {s.social.account_tier}: {lowerLabel("social_tiers", s.social.account_tier)}.{" "}
          <span className="dim">How identity was established: {s.social.identity_basis}</span>
          {definitionOf("social_tiers", s.social.account_tier) && <div className="dim">{definitionOf("social_tiers", s.social.account_tier)}</div>}
        </div>
      )}
      <div className="imp-supports">
        Supports: {s.supports.length > 0 ? s.supports.map((c) => lowerLabel("claims", c)).join("; ") : "no claim recorded"}.
      </div>
      {s.derived_claim && <div className="dim">What it says, in our words: {s.derived_claim}</div>}
      {headlines && s.title_original && (
        <div className="source-title"><bdi lang={s.language ?? undefined} dir={dirFor(s.language ?? undefined)}>{s.title_original}</bdi></div>
      )}
      {headlines && s.title_original && s.title_en && s.title_en !== s.title_original && <div className="source-gloss dim">Gloss: {s.title_en}</div>}
      <div className="dim">
        {s.added_by === "lead" && (
          <span className="lead-added">
            Added on lead review, after the blind reviews: not opened by a reviewer, and whether it repeats another cited source was
            not checked, so it is not counted as an independent statement.{" "}
          </span>
        )}
        {s.opened === true ? "Opened and read by a reviewer. " : s.opened === false ? "Recorded as not opened. " : ""}
        Link: <span className={`link-state link-${link}`}>{lowerLabel("link_states", link)}</span>
        {definitionOf("link_states", link) ? ` (${definitionOf("link_states", link)})` : ""}
      </div>
    </li>
  );
}

/** `headingLevel`: 5 where the card sits under an h4 (the atlas timeline's month headings), so the
 *  outline nests; 4 elsewhere. */
export function ImpactInspector({ record, id, onClose, headingLevel = 4 }: { record: ImpactRecord; id?: string; onClose?: () => void; headingLevel?: 4 | 5 }) {
  const H = headingLevel === 5 ? "h5" : "h4";
  useImpactVocab();
  const { method, failed } = useConfidenceMethod(true);
  const r = record;
  const headlines = !isAbstracted(r);
  const chain = claimSupport(r, vocabulary("claims").map((c) => String(c.id)));
  const originsBasis = r.evidence_confidence?.components?.origins?.basis ?? null;
  const selfClaims = selfClaimsOf(r.attribution);
  return (
    <section id={id} className="ev-inspector imp-inspector small" aria-label="Evidence inspector"
             onKeyDown={(e) => { if (e.key === "Escape" && onClose) { e.stopPropagation(); onClose(); } }}>
      <H>What each claim rests on</H>
      <ul className="imp-chain">
        {chain.map((c) => (
          <li key={c.claim}>
            <strong>{c.label}:</strong>{" "}
            {c.sources.map((s) => `${publisherOf(s)} (${lowerLabel("source_roles", s.source_role)}${s.medium === "social" ? `, ${lowerLabel("media", s.medium)}` : ""})`).join(" + ")}
          </li>
        ))}
      </ul>
      {/* What was counted is the served basis's to say: publishers are not called originating
          statements unless a reviewer established that they are. */}
      {r.origin_count != null && originsBasis && (
        <p className="dim imp-origins">
          Across {r.sources.length} {r.sources.length === 1 ? "citation" : "citations"}: {originsText(r.origin_count, originsBasis)}.
          {/* The served count leaves out lead-added citations, actors' own claims and discovery aids
              (round-2 ruling R4); where a lead-added citation is present, say so beside the count. */}
          {r.sources.some((s) => s.added_by === "lead") && ` ${LEAD_ADDED_NOT_COUNTED}`}
        </p>
      )}

      {selfClaims.length > 0 && (
        <>
          <H>Self-claims of responsibility (unverified)</H>
          <ul className="imp-self-claims">
            {selfClaims.map((c, i) => {
              const cited = r.sources.filter((s) => (Array.isArray(c.source_refs) ? c.source_refs : []).includes(s.ref)).map(publisherOf);
              return (
                <li key={i} className="attr-self-claim">
                  <span className="impact-line-label">Self-claim (unverified):</span> {selfClaimText(c)}
                  <span className="dim"> {cited.length > 0 ? `Cited: ${[...new Set(cited)].join("; ")}.` : "No cited source is listed for it."}</span>
                </li>
              );
            })}
          </ul>
          <p className="dim">{SELF_CLAIM_NOTE}</p>
        </>
      )}

      <H>Sources ({r.sources.length})</H>
      <ul className="imp-sources">
        {r.sources.map((s) => <SourceRow key={s.ref} s={s} headlines={headlines} />)}
      </ul>
      {!headlines && <p className="dim">Source headlines are not shown for an attack or sabotage record.</p>}

      <H>Evidence confidence: {confidenceLabel(r.evidence_confidence)}</H>
      {r.evidence_confidence && r.evidence_confidence.category != null
        ? <ConfidenceBreakdown value={r.evidence_confidence} method={method} failed={failed} />
        : <p className="imp-not-assessed">{r.evidence_confidence?.reason ?? NO_CONFIDENCE_REASON}</p>}

      {r.inclusion_basis != null && (
        <>
          <H>Why this record is included</H>
          <p>{labelOf("inclusion_bases", r.inclusion_basis)}: {definitionOf("inclusion_bases", r.inclusion_basis) ?? ""}</p>
        </>
      )}

      <H>What the evidence does not establish</H>
      <ul className="ev-inspector-limits">
        {notEstablished(r).map((line, i) => <li key={i}>{line}</li>)}
      </ul>

      {r.review?.reviewed_at && (
        <p className="dim">Reviewed {fmtDate(r.review.reviewed_at)} by three independent roles
          ({vocabulary("review_roles").map((x) => x.label.toLowerCase()).join("; ") || "evidence; attribution and source; safety"}).</p>
      )}
      {onClose && <button type="button" className="ghost ev-inspector-close" onClick={onClose}>Close</button>}
    </section>
  );
}

export default ImpactInspector;
