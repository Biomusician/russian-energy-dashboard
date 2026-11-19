import { fmtDate } from "../../data";
import { LANGUAGE_LABEL, dirFor } from "../manifest";
import { ConfidenceBreakdown, useConfidenceMethod } from "./ConfidenceChip";
import { claimSupport, isAbstracted, notEstablished, sourceKind } from "./model";
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
        {s.opened === true ? "Opened and read by a reviewer. " : s.opened === false ? "Recorded as not opened. " : ""}
        Link: <span className={`link-state link-${link}`}>{lowerLabel("link_states", link)}</span>
        {definitionOf("link_states", link) ? ` (${definitionOf("link_states", link)})` : ""}
      </div>
    </li>
  );
}

export function ImpactInspector({ record, id, onClose }: { record: ImpactRecord; id?: string; onClose?: () => void }) {
  useImpactVocab();
  const { method, failed } = useConfidenceMethod(true);
  const r = record;
  const headlines = !isAbstracted(r);
  const chain = claimSupport(r, vocabulary("claims").map((c) => String(c.id)));
  return (
    <section id={id} className="ev-inspector imp-inspector small" aria-label="Evidence inspector"
             onKeyDown={(e) => { if (e.key === "Escape" && onClose) { e.stopPropagation(); onClose(); } }}>
      <h4>What each claim rests on</h4>
      <ul className="imp-chain">
        {chain.map((c) => (
          <li key={c.claim}>
            <strong>{c.label}:</strong>{" "}
            {c.sources.map((s) => `${publisherOf(s)} (${lowerLabel("source_roles", s.source_role)}${s.medium === "social" ? `, ${lowerLabel("media", s.medium)}` : ""})`).join(" + ")}
          </li>
        ))}
      </ul>
      {r.origin_count != null && (
        <p className="dim">
          {r.origin_count} originating {r.origin_count === 1 ? "statement" : "statements"} across {r.sources.length}{" "}
          {r.sources.length === 1 ? "citation" : "citations"}. Republications of one statement count once.
        </p>
      )}

      <h4>Sources ({r.sources.length})</h4>
      <ul className="imp-sources">
        {r.sources.map((s) => <SourceRow key={s.ref} s={s} headlines={headlines} />)}
      </ul>
      {!headlines && <p className="dim">Source headlines are not shown for an attack or sabotage record.</p>}

      <h4>Evidence confidence: {r.evidence_confidence?.label ?? "not computed"}</h4>
      {r.evidence_confidence
        ? <ConfidenceBreakdown value={r.evidence_confidence} method={method} failed={failed} />
        : <p className="dim">No evidence confidence is published for this record.</p>}

      {r.inclusion_basis != null && (
        <>
          <h4>Why this record is included</h4>
          <p>{labelOf("inclusion_bases", r.inclusion_basis)}: {definitionOf("inclusion_bases", r.inclusion_basis) ?? ""}</p>
        </>
      )}

      <h4>What the evidence does not establish</h4>
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
