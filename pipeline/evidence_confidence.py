"""Evidence Confidence v2 (iteration 22): how strong is the public evidence for a record?

Three separate questions, never one number (docs/GLOBAL_IMPACT_METHODOLOGY.md §8):

  * `assess`                  did it happen, and is the reported effect supported?
  * `attribution_confidence`  how strong is the evidence about who did it?
  * `ai_problems`             does a source tie AI to this incident at the status claimed?

WHAT THIS IS NOT. Not a probability, not severity, not infrastructure importance, not research
completeness. It does not enter the ESDI: the theatre's scoring multiplier
(`confidence_weights` in scoring.json, set from cited-host count) is a different thing and is
unchanged. A test forbids `build_index` from importing this module.

WHY POINTS, AND WHY THESE. Every component is a maximum, an "any" or a count of distinct origins
over the supporting sources, so adding a source can never lower the score and removing one can never
raise it. Nothing counts citations: ten copies of one wire story are one origin, and three
releases from one utility are one origin. Directness and corroboration are separate components, so
an official statement is not marked down for corroboration a closed media environment could not
supply, and many copies of one statement do not stand in for independence.

Every parameter is in methodology/evidence_confidence.json.
"""

import datetime as dt
import json
import re

from pipeline.config import METHODOLOGY_DIR

METHOD_PATH = METHODOLOGY_DIR / "evidence_confidence.json"
METHOD = json.loads(METHOD_PATH.read_text(encoding="utf-8"))

CLAIMS = ("occurrence", "effect", "attribution", "ai_involvement")
EFFECT_SPECIFICITY = tuple(METHOD["effect_points"])
TIER_ORDER = ("unverified", "researcher_social", "secondary", "independent", "direct")
CATEGORIES = tuple(c["id"] for c in METHOD["categories"]) + (METHOD["disputed"]["id"],)

ATTRIBUTION_STATUSES = ("NOT_APPLICABLE", "UNKNOWN", "CLAIMED", "SUSPECTED", "ASSESSED", "ATTRIBUTED", "DISPUTED")
ATTRIBUTION_CONFIDENCE = ("HIGH", "MODERATE", "LOW", "CLAIM_ONLY", "DISPUTED", "NOT_ESTABLISHED")
ACTOR_TYPES = ("state", "state_linked", "hacktivist", "criminal", "insider", "unknown", "other")
ATTRIBUTION_BASES = ("government", "law_enforcement", "victim_operator", "cybersecurity_firm", "researcher",
                     "media_investigation", "actor_self_claim")
# Whose authority a source carries when it attributes, by its role. A lane may override per source
# with `attribution_basis` (a wire story reporting a government's attribution carries the
# government's authority, at one remove).
BASIS_OF_ROLE = {"government": "government", "official": "government", "regulator": "government",
                 "cert": "government", "law_enforcement": "law_enforcement", "court_record": "law_enforcement",
                 "operator": "victim_operator", "cyber_firm": "cybersecurity_firm", "researcher": "researcher",
                 "wire": "media_investigation", "media": "media_investigation",
                 "specialist_media": "media_investigation", "industry": "media_investigation",
                 "actor_self_claim": "actor_self_claim"}

AI_STATUSES = ("NONE_REPORTED", "CLAIMED", "SUSPECTED", "ASSESSED", "CONFIRMED")
AI_RELATIONS = ("ai_assisted", "ai_operational_cause")
AI_ROLES = ("attacker_assistance", "social_engineering_generation", "malware_or_script_generation",
            "automated_attack_orchestration", "ai_operational_system_failure",
            "ai_generated_configuration_or_code", "ai_service_dependency_failure", "other", "unknown")


def origin_of(source):
    """The originating statement a citation carries. An explicit `origin` wins (a lane that can see
    a republication groups it); a social post's origin is its account; otherwise the rule the
    country systems already use (a named wire, else the registered domain). None for a discovery
    aid (Wikipedia, a content aggregator), which is never an origin."""
    if source.get("origin"):
        return str(source["origin"]).lower()
    social = source.get("social") or {}
    if source.get("medium") == "social" and social.get("handle"):
        return f"social:{(social.get('platform') or '').lower()}:{social['handle'].lower().lstrip('@')}"
    from pipeline.build_systems import source_origin  # late: build_systems is large and imports nothing from here
    return source_origin(source)


def _identity_established(social):
    """An official account counts as its organisation only when the record says how its identity
    was established, and a platform badge is not a way (methodology §9)."""
    basis = str((social or {}).get("identity_basis") or "").strip().lower()
    return bool(basis) and basis not in METHOD["badge_only_identity"]


def tier_of(source):
    """Directness tier of one source: who is speaking, not how many repeat it."""
    if origin_of(source) is None:
        return "secondary"
    role = source.get("source_role")
    if source.get("medium") == "social":
        social = source.get("social") or {}
        mapped = METHOD["social_tier"].get(social.get("account_tier"), "unverified")
        if mapped != "by_role":
            return mapped
        if not _identity_established(social):
            return "unverified"
        # An established official account speaks as its organisation does.
    # No role is promoted in code. A dataset restating others is secondary; a regulator's own
    # filing is cited with the regulator's role and `medium: "dataset"`. (Iteration 22: a
    # hard-coded "dataset is direct" here gave an event database the standing of an operator,
    # against the parameter file and methodology §8.1.)
    return METHOD["role_tier"].get(role, "secondary")


def _supports(source, claim):
    # Country-system events predate claim-level provenance: every citation supports the event.
    declared = source.get("supports")
    return claim in ("occurrence", "effect") if declared is None else claim in declared


def _date(text, end=False):
    """A date string of day, month or year precision as a date: the period's start, or its end."""
    if not text:
        return None
    try:
        parts = [int(x) for x in str(text)[:10].split("-")]
        if len(parts) == 3:
            return dt.date(*parts)
        if len(parts) == 2:
            first = dt.date(parts[0], parts[1], 1)
            return (first.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1) if end else first
        return dt.date(parts[0], 12, 31) if end else dt.date(parts[0], 1, 1)
    except (ValueError, TypeError):
        return None


def _contemporaneous(source, date, date_end):
    start, stop, cited = _date(date), _date(date_end or date, end=True), _date(source.get("date"))
    if not (start and stop and cited):
        return False
    return start - dt.timedelta(days=1) <= cited <= stop + dt.timedelta(days=METHOD["contemporaneous_days"])


def _publisher_key(source):
    name = re.sub(r"[^\w]+", " ", str(source.get("publisher") or "").lower()).strip()
    return name or origin_of(source)


def independent_origins(sources):
    """How many independent originating statements stand behind `sources`.

    The smaller of two counts: distinct origins (a named wire, a website, an account) and distinct
    publishers. One organisation speaking on its website and on its official account, or on two
    sites, is one statement; a wire and its republications are one. Each count can only grow as a
    source is added, so the smaller can only grow too, and a second citation from the same
    publisher at the same origin changes neither. It can undercount independence (two outlets a
    record gives the same publisher name), never overstate it. Discovery aids count for nothing."""
    counted = [s for s in sources if origin_of(s) is not None]
    return min(len({origin_of(s) for s in counted}), len({_publisher_key(s) for s in counted}))


def _disputed(sources, dispute):
    """Whether occurrence or effect is credibly contested: the record says so, or a direct or
    independent source is recorded as disputing one of them (`disputes`, the mirror of
    `supports`). An anonymous denial is not credible disagreement, and a dispute about who did it
    belongs to attribution."""
    if dispute:
        about = dispute.get("about") if isinstance(dispute, dict) else None
        about = [about] if isinstance(about, str) else list(about or [])
        # A dispute that does not say what it is about is read as one about the record itself:
        # the conservative reading, since Disputed claims less than any category.
        if not about or any(a in ("occurrence", "effect") for a in about):
            return True
    return any(tier_of(s) in METHOD["corroborating_tiers"]
               and any(a in ("occurrence", "effect") for a in (s.get("disputes") or []))
               for s in sources)


def assess(sources, date, date_end=None, effect_specificity="described", dispute=None):
    """Evidence confidence for occurrence and effect: category, ordinal score and its components."""
    backing = [s for s in sources if _supports(s, "occurrence") or _supports(s, "effect")]
    tiers = [tier_of(s) for s in backing]
    best = max(tiers, key=TIER_ORDER.index) if tiers else None
    strong = [s for s, t in zip(backing, tiers) if t in METHOD["corroborating_tiers"]]
    origin_count = independent_origins(strong)

    directness = METHOD["tiers"][best]["points"] if best else 0
    origin_points = METHOD["origin_points"][str(min(origin_count, 3))] if origin_count else 0
    effect_backed = any(_supports(s, "effect") for s in strong)
    effect_points = METHOD["effect_points"].get(effect_specificity, 0) if effect_backed else 0
    opened = METHOD["opened_points"] if any(s.get("opened") is True for s in strong) else 0
    timely = METHOD["contemporaneous_points"] if any(_contemporaneous(s, date, date_end) for s in strong) else 0
    score = directness + origin_points + effect_points + opened + timely

    category = next(c for c in METHOD["categories"] if score >= c["min"])
    capped = best in (None, "researcher_social", "unverified")
    if capped:
        category = next(c for c in METHOD["categories"] if c["id"] == METHOD["caps"]["unverified_only"])
    disputed = _disputed(sources, dispute)
    if disputed:
        category = METHOD["disputed"]

    reasons = []
    if best:
        reasons.append(METHOD["tiers"][best]["label"])
    if origin_count >= 2:
        reasons.append(f"{origin_count} independent originating statements")
    elif origin_count == 1:
        reasons.append("One originating statement")
    else:
        reasons.append("No direct or independently reported source")
    if effect_backed:
        reasons.append({"quantified": "Effect quantified by a source", "described": "Effect described, not quantified",
                        "vague": "Effect reported only in general terms"}.get(effect_specificity, "Effect not assessed"))
    else:
        reasons.append("No direct or independent source for the effect")
    if opened:
        reasons.append("Source read by a reviewer")
    if timely:
        reasons.append("Reported at the time")
    if capped and best:
        reasons.append("Rests on unverified claims only")
    if disputed:
        reasons.append("Credible sources disagree")

    return {
        "category": category["id"], "label": category["label"], "score": score, "disputed": disputed,
        "components": {
            "directness": {"tier": best, "points": directness},
            "origins": {"count": origin_count, "points": origin_points},
            "effect": {"specificity": effect_specificity if effect_backed else None, "points": effect_points},
            "opened": {"points": opened},
            "contemporaneous": {"points": timely},
        },
        "reasons": reasons,
    }


def _basis(source):
    """Whose authority a source carries when it names an actor, or None when it carries none.

    The actor's own claim is a claim whatever else the record says about it. A discovery aid and
    an anonymous or unestablished account are not credible attribution and carry nothing. The
    `attribution_basis` override (a wire story reporting a government's attribution) is honoured
    only on a direct or independently reporting source: a post or an aggregator cannot borrow a
    government's authority."""
    role = source.get("source_role")
    declared = source.get("attribution_basis")
    if role == "actor_self_claim" or declared == "actor_self_claim":
        return "actor_self_claim"
    tier = tier_of(source)
    if origin_of(source) is None or tier == "unverified":
        return None
    if tier in METHOD["corroborating_tiers"]:
        return declared or BASIS_OF_ROLE.get(role, "media_investigation")
    return "researcher" if role == "researcher" or tier == "researcher_social" else "media_investigation"


def _corroborates(source):
    """Whether a source is an attribution of its own, as against a report of someone else's.

    News coverage of an attribution usually restates it. A wire, outlet or trade title therefore
    counts toward corroboration only when the record declares what it carries (`attribution_basis`):
    an investigation of its own, or a named authority's attribution at one remove. Undeclared, it
    still shows that someone credible names the actor (LOW), but two outlets repeating one
    statement are not two attributions."""
    return (source.get("source_role") not in METHOD["attribution"]["restating_roles"]
            or bool(source.get("attribution_basis")))


def _attribution_evidence(sources):
    """(backing, named, claims): every source that supports attribution, those that carry a
    credible third-party attribution, and the actor's own claims."""
    backing = [s for s in sources if _supports(s, "attribution")]
    named = [s for s in backing if _basis(s) not in (None, "actor_self_claim")]
    claims = [s for s in backing if _basis(s) == "actor_self_claim"]
    return backing, named, claims


def attribution_confidence(attribution, sources):
    """Attribution confidence from the sources that support `attribution`. None when attribution
    does not apply; NOT_ESTABLISHED (not "low") when nobody credible attributes."""
    status = (attribution or {}).get("status")
    if status in (None, "NOT_APPLICABLE"):
        return None
    if status == "UNKNOWN":
        return "NOT_ESTABLISHED"
    if status == "DISPUTED":
        return "DISPUTED"
    _backing, named, claims = _attribution_evidence(sources)
    cfg = METHOD["attribution"]
    if not named:
        return "CLAIM_ONLY" if claims else "NOT_ESTABLISHED"
    bases = {_basis(s) for s in named}
    firm = [s for s in named if _corroborates(s)]
    firm_bases = {_basis(s) for s in firm}
    if firm_bases & set(cfg["official_bases"]) and len(firm_bases) >= 2 and independent_origins(firm) >= 2:
        return "HIGH"
    technical = [s for s in firm if _basis(s) in cfg["technical_bases"]]
    if bases & set(cfg["first_party_bases"]) or independent_origins(technical) >= 2:
        return "MODERATE"
    return "LOW"


def attribution_problems(attribution, sources):
    """Where an attribution's status says more (or less) than its sources do."""
    out = []
    a = attribution or {}
    status = a.get("status")
    if status not in ATTRIBUTION_STATUSES:
        return [f"attribution status {status!r} is not one of {ATTRIBUTION_STATUSES}"]
    backing, named, claims = _attribution_evidence(sources)
    bases = {_basis(s) for s in named}
    cfg = METHOD["attribution"]
    if status in ("NOT_APPLICABLE", "UNKNOWN"):
        if a.get("actor") or backing:
            out.append(f"attribution is {status} but an actor or an attribution source is recorded")
        return out
    if not a.get("actor") and status != "DISPUTED":
        out.append(f"attribution is {status} with no actor named")
    if a.get("actor_type") not in ACTOR_TYPES:
        out.append(f"actor_type {a.get('actor_type')!r} is not one of {ACTOR_TYPES}")
    if not a.get("as_of"):
        out.append("an attribution needs the date it was made (as_of)")
    if not backing:
        out.append(f"attribution is {status} with no source that supports attribution")
    if status == "CLAIMED":
        if not claims:
            out.append("CLAIMED needs the actor's own claim as a source")
        if named:
            out.append("CLAIMED but another party also attributes: the status understates the sources")
    elif status == "DISPUTED":
        if len(a.get("competing") or []) < 1:
            out.append("DISPUTED needs the competing attribution listed")
    else:
        if not named:
            out.append(f"{status} has no credible source naming the actor: the actor's own claim is "
                       "CLAIMED, and an anonymous post or a discovery aid attributes nothing")
        # Methodology §8.2: ATTRIBUTED is a formal attribution. Any number of technical or press
        # attributions that agree is ASSESSED (iteration 22: three origins used to be enough here).
        if status == "ATTRIBUTED" and not bases & set(cfg["official_bases"]):
            out.append("ATTRIBUTED needs a formal government or law-enforcement attribution; "
                       "technical or press attributions that agree are ASSESSED")
    for b in a.get("basis") or []:
        if b not in ATTRIBUTION_BASES:
            out.append(f"attribution basis {b!r} is not one of {ATTRIBUTION_BASES}")
    return out


def ai_problems(ai, sources):
    """An AI label needs a source that ties AI to this incident, at the strength the status claims."""
    out = []
    a = ai or {}
    status = a.get("status")
    if status not in AI_STATUSES:
        return [f"ai_involvement status {status!r} is not one of {AI_STATUSES}"]
    backing = [s for s in sources if _supports(s, "ai_involvement")]
    if status == "NONE_REPORTED":
        if backing or a.get("relation") or a.get("role"):
            out.append("ai_involvement is NONE_REPORTED but a relation, role or AI source is recorded")
        return out
    if not backing:
        out.append(f"ai_involvement is {status} with no source that ties AI to this incident")
    if a.get("relation") not in AI_RELATIONS:
        out.append(f"ai_involvement needs a relation, one of {AI_RELATIONS}: assistance is not causation")
    if a.get("role") not in AI_ROLES:
        out.append(f"ai_involvement role {a.get('role')!r} is not one of {AI_ROLES}")
    if not a.get("as_of"):
        out.append("an AI-involvement finding needs the date it was made (as_of)")
    tiers = {tier_of(s) for s in backing}
    # An anonymous account is discovery only and never sole evidence (methodology §9); an actor's
    # own boast is a claim and may stand as CLAIMED, nothing firmer.
    if backing and tiers <= {"unverified"} and not (
            status == "CLAIMED" and any(s.get("source_role") == "actor_self_claim" for s in backing)):
        out.append(f"ai_involvement is {status} on unverified posts alone; an anonymous account is never sole evidence")
    if status == "CONFIRMED" and "direct" not in tiers:
        out.append("CONFIRMED needs a direct authoritative source (operator, government or the vendor's own report)")
    if status == "ASSESSED" and not tiers & {"direct", "independent"}:
        out.append("ASSESSED needs an official or technical investigator as its source")
    return out


def method():
    """The method as served data, for the confidence drawer and the glossary."""
    return {
        "version": METHOD["version"],
        "statement": METHOD["statement"],
        "questions": [
            {"id": "evidence", "label": "Evidence confidence",
             "asks": "Did it happen, and is the reported effect supported?"},
            {"id": "attribution", "label": "Attribution confidence",
             "asks": "How strong is the evidence about who did it?"},
            {"id": "ai", "label": "AI involvement",
             "asks": "Does a source tie AI to this incident, and how firmly?"},
        ],
        "components": [
            {"id": "directness", "label": "Who is speaking", "max": METHOD["tiers"]["direct"]["points"],
             "tiers": [{"id": t, **METHOD["tiers"][t]} for t in reversed(TIER_ORDER)]},
            {"id": "origins", "label": "Independent originating statements", "max": METHOD["origin_points"]["3"],
             "meaning": "Counted in originating statements, not links: a wire story and its copies are one; "
                        "releases from one organisation are one, on its website or its official account; "
                        "reposts are one at best."},
            {"id": "effect", "label": "How specific the reported effect is", "max": METHOD["effect_points"]["quantified"],
             "meaning": "Quantified, described or only general, as a direct or independent source reports it."},
            {"id": "opened", "label": "Read by a reviewer", "max": METHOD["opened_points"],
             "meaning": "A reviewer opened and read a direct or independent source."},
            {"id": "contemporaneous", "label": "Reported at the time", "max": METHOD["contemporaneous_points"],
             "meaning": f"A direct or independent source dated within {METHOD['contemporaneous_days']} days of the event."},
        ],
        "categories": METHOD["categories"] + [METHOD["disputed"]],
        "overrides": [
            "Disputed overrides the score: credible sources disagree, and the product does not choose.",
            "A record resting only on unverified posts or an actor's own claim is at most Preliminary.",
        ],
        "properties": [
            "Adding a source never lowers the score; a duplicate or a second citation from the same origin changes nothing.",
            "The number of links never enters; only who is speaking and how many independent origins there are.",
            "The score is ordinal. It is not a probability.",
        ],
        "attribution": METHOD["attribution"],
    }
