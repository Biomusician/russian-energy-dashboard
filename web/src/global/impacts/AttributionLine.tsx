import { fmtDate } from "../../data";
import { SELF_CLAIM_NOTE, attributionConfidenceLabel, basisText, selfClaimText, selfClaimsOf } from "./model";
import { confidenceMethod, definitionOf, labelOf, lowerLabel, useImpactVocab } from "./vocab";
import type { Attribution, CompetingAttribution, SelfClaim } from "./types";
import "../../styles/impacts.css";

/** Who is publicly said to be responsible, and by whom (iteration 22).
 *
 *  The site reports who attributes; it asserts nothing itself. So the line always reads
 *  "status · actor (type) · attributed by <who> · as of <date> · confidence", and the sentence
 *  below it is the served statement, which is written "X attributed this to Y".
 *
 *  Three absences, three renderings:
 *  - NOT_APPLICABLE (not a malicious act): nothing at all. There is nobody to attribute it to.
 *  - UNKNOWN: "Attribution: unknown (not established)". Not a low confidence, and no confidence
 *    word is shown beside it.
 *  - DISPUTED: every competing attribution is listed. The site does not choose.
 *
 *  An actor's own claim of responsibility (`self_claims`) is provenance, not an attribution: it is
 *  shown apart, as "Self-claim (unverified)", whatever the status, never under the competing
 *  attributions and never as the attribution itself.
 */

function actorText(actor: string | null, actorType: string | null): string {
  const type = actorType ? lowerLabel("actor_types", actorType) : "";
  if (!actor) return type ? `actor not named (${type})` : "actor not named";
  return type ? `${actor} (${type})` : actor;
}

/** "A government attributed this to Example Group E (state-linked)." */
function competingSentence(c: CompetingAttribution): string {
  const who = basisText(c.basis);
  const subject = who ? who.charAt(0).toUpperCase() + who.slice(1) : "A source";
  return `${subject} attributed this to ${actorText(c.actor, c.actor_type)}.`;
}

/** The self-claims, apart from the attribution and from any competing one. */
export function SelfClaims({ claims }: { claims: readonly SelfClaim[] }) {
  if (claims.length === 0) return null;
  return (
    <div className="attr-self-claims">
      <ul className="attr-self-claim-list">
        {claims.map((c, i) => (
          <li key={i} className="attr-self-claim">
            <span className="impact-line-label">Self-claim (unverified):</span> {selfClaimText(c)}
          </li>
        ))}
      </ul>
      <div className="dim">{SELF_CLAIM_NOTE}</div>
    </div>
  );
}

export function AttributionLine({ a }: { a: Attribution | null | undefined }) {
  useImpactVocab();
  if (!a) return null;
  const selfClaims = selfClaimsOf(a);
  if (a.status === "NOT_APPLICABLE") {
    // Nothing to attribute. A claim on record is still provenance, and still only a claim.
    return selfClaims.length > 0 ? <div className="attr-line attr-not_applicable small"><SelfClaims claims={selfClaims} /></div> : null;
  }
  if (a.status === "UNKNOWN") {
    return (
      <div className="attr-line attr-unknown small">
        <span className="impact-line-label">Attribution:</span> unknown (not established)
        <span className="dim"> — {definitionOf("attribution_statuses", "UNKNOWN") ?? "No credible public attribution."}</span>
        <SelfClaims claims={selfClaims} />
      </div>
    );
  }
  const method = confidenceMethod();
  const confidence = attributionConfidenceLabel(a, method?.attribution.labels);
  const disputed = a.status === "DISPUTED";
  const meanings = method?.attribution.meanings ?? {};
  const meaning = confidence && a.confidence && Object.prototype.hasOwnProperty.call(meanings, a.confidence) ? meanings[a.confidence] : null;
  // A claim of responsibility is the actor's own statement: nobody "attributed" it.
  const by = a.status === "CLAIMED" && a.basis.every((b) => b === "actor_self_claim")
    ? "claimed by the actor itself" : a.basis.length > 0 ? `attributed by ${basisText(a.basis)}` : null;
  const parts = [
    lowerLabel("attribution_statuses", a.status),
    disputed ? null : actorText(a.actor, a.actor_type),
    disputed ? null : by,
    a.as_of ? `as of ${fmtDate(a.as_of)}` : null,
    confidence ? `confidence: ${confidence}` : null,
  ].filter(Boolean);
  return (
    <div className={`attr-line attr-${a.status.toLowerCase()} small`}>
      <span className="impact-line-label">Attribution:</span> {parts.join(" · ")}
      {a.statement && <div className="attr-statement">{a.statement}</div>}
      {disputed && a.competing.length > 0 && (
        <>
          <div className="dim">Competing attributions, as reported. This site does not choose between them.</div>
          <ul className="attr-competing">
            {a.competing.map((c, i) => (
              <li key={i}>
                {competingSentence(c)}
                {c.statement && <span className="dim"> {c.statement}</span>}
              </li>
            ))}
          </ul>
        </>
      )}
      {meaning
        ? <div className="dim">Attribution confidence {confidence?.toLowerCase()}: {meaning}</div>
        // Without the method's wording, a claim still says what a claim is worth.
        : a.status === "CLAIMED" && <div className="dim">{definitionOf("attribution_statuses", "CLAIMED") ?? "A claim is not corroboration."}</div>}
      <SelfClaims claims={selfClaims} />
    </div>
  );
}

/** The status word alone, for a compact list ("Assessed", "Not established"). */
export function attributionStatusLabel(a: Attribution): string {
  return labelOf("attribution_statuses", a.status);
}

export default AttributionLine;
