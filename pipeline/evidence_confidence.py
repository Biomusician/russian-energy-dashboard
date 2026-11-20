"""Evidence Confidence v2 (iteration 22): what do the sources a record cites support?

Three separate questions, never one number (docs/GLOBAL_IMPACT_METHODOLOGY.md §8):

  * `assess`                  did it happen, and is the reported effect supported?
  * `attribution_confidence`  how strong is the evidence about who did it?
  * `ai_problems`             does a source tie AI to this incident at the status claimed?

WHAT THIS IS NOT. Not a probability, not severity, not infrastructure importance, not research
completeness, and not a judgement of everything published about an event: it describes the sources
THIS RECORD CITES. It does not enter the ESDI: the theatre's scoring multiplier
(`confidence_weights` in scoring.json, set from cited-host count) is a different thing and is
unchanged. A test forbids `build_index` from importing this module.

WHY POINTS, AND WHY THESE. Nothing counts citations: ten copies of one wire story are one origin,
and three releases from one utility are one origin. Who is speaking and how many originating
statements there are are separate components, so an official statement is not marked down for
corroboration a closed media environment could not supply, and many copies of one statement do not
stand in for independence. Every component but the origin count is a maximum or an "any" over the
supporting sources, so adding a source cannot lower it. The origin count can fall: a new citation
can show that two sources thought separate are one (same organisation, same publisher, one a relay
of the other). That is the count being corrected, and it is the one way a score can drop.

WHAT THE METHOD CANNOT SEE (methodology red team, iteration 22). Whether a news report is the
outlet's own work or a relay of someone's statement is not in a citation. So the origin count is
called "independent originating statements" only where a reviewer has checked it (`basis:
"reviewed"`); otherwise it is a count of distinct publishers, said as such, and the record cannot be
High. A record cited only through an encyclopedia or an aggregator is not assessed at all: that is a
research state, not weak evidence.

Every parameter is in methodology/evidence_confidence.json. While its version ends in "-draft" the
thresholds are provisional: no blind calibration run has passed.
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
ORIGIN_BASES = ("reviewed", "publishers")

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


# --- one source: where it comes from, who is speaking ---------------------------------------------

def _words(text):
    return re.sub(r"[^\w]+", " ", str(text or "").lower()).strip()


_WRAPPERS = (
    # A copy of a page is that page: an archive snapshot, an AMP cache copy.
    (re.compile(r"^https?://(?:web\.)?archive\.org/web/[^/]+/(https?://.+)$", re.I), "{0}"),
    (re.compile(r"^https?://[^/]*\.cdn\.ampproject\.org/[a-z]+/(?:s/)?(.+)$", re.I), "https://{0}"),
    (re.compile(r"^https?://(?:www\.)?google\.[a-z.]+/amp/(?:s/)?(.+)$", re.I), "https://{0}"),
)


def _url(source):
    """The address a citation points at, with archive and AMP wrappers removed."""
    url = str(source.get("url") or "").strip()
    for pattern, shape in _WRAPPERS:
        m = pattern.match(url)
        if m:
            url = shape.format(m.group(1))
    return url


def _host(source):
    return _url(source).split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0].lower().rstrip(".")


def _on(host, domains):
    return any(host == d or host.endswith("." + d) for d in domains)


def _wire_named(text):
    """The wire a publisher string or an explicit origin names: the table the country systems use,
    then this module's additions (full names, and the agencies that table lacks)."""
    from pipeline import build_systems as B  # late: build_systems imports this module
    words = " " + re.sub(r"[^a-z]+", " ", str(text or "").lower()) + " "
    for key, name in B.WIRE_ORIGINS:
        if f" {key} " in words:
            return "wire:" + name
    for wire in METHOD["origins"]["wires"]:
        if any(f" {m} " in words for m in wire["match"]):
            return "wire:" + wire["name"]
    return None


def _account(source):
    """(platform, handle) of a social post: from its `social` block, else from its address. One
    platform under two names is one platform, and a handle is compared without its @ or its case."""
    social = source.get("social") or {}
    host = _host(source)
    host = host[4:] if host.startswith("www.") else host
    platform = str(social.get("platform") or host).strip().lower()
    platform = METHOD["platform_aliases"].get(platform, platform)
    handle = str(social.get("handle") or "").strip().lower().lstrip("@")
    if not handle:
        skip = {"s", "i", "c", "p", "user", "channel", "watch", "share", "groups", "pages", "posts", "status"}
        parts = [p for p in _url(source).split("://", 1)[-1].split("?", 1)[0].split("/")[1:] if p]
        handle = next((p.lower().lstrip("@") for p in parts if p.lower() not in skip), "")
    return platform, handle


def origin_of(source):
    """The originating statement a citation carries. None for a discovery aid (Wikipedia, a content
    or news aggregator) and for a link shortener: neither is an origin, and no explicit `origin`
    can turn one into one. Otherwise an explicit `origin` (a lane that can see a republication
    groups it; one that names a wire is that wire), a social post's account, a named wire or a
    wire's own site, else the registered domain."""
    from pipeline import build_systems as B  # late: build_systems imports this module
    host = _host(source)
    if _on(host, METHOD["discovery_aid_domains"]) or _on(host, METHOD["shortener_hosts"]):
        return None
    bare = {k: v for k, v in source.items() if k != "origin"}
    bare["url"] = _url(source)
    natural = B.source_origin(bare)
    if natural is None:
        return None
    if source.get("origin"):
        return _wire_named(source["origin"]) or str(source["origin"]).strip().lower()
    if _medium(source) == "social":
        platform, handle = _account(source)
        if handle:
            return f"social:{platform}:{handle}"
        return natural
    if natural.startswith("wire:"):
        return natural
    wire = _wire_named(source.get("publisher")) or next(
        ("wire:" + w["name"] for w in METHOD["origins"]["wires"] if _on(host, w["domains"])), None)
    if wire:
        return wire
    # Two ministries under one national suffix, or two writers on one blogging host, are not one
    # publisher: the origin is the label in front of the shared suffix.
    for suffix in METHOD["origins"]["shared_suffixes"]:
        if host.endswith("." + suffix):
            return host[:-len(suffix) - 1].split(".")[-1] + "." + suffix
    return natural


def _medium(source):
    """The medium as typed, lower-cased; a post on a social platform is social whatever was typed:
    a channel filed as a website is still a channel."""
    if _on(_host(source), METHOD["social_hosts"]):
        return "social"
    return str(source.get("medium") or "").strip().lower()


def _identity_established(social):
    """An official account counts as its organisation only when the record says how its identity
    was established, and a platform badge is not a way (methodology §9): a basis made of nothing
    but badge words ("Verified account", "blue tick") establishes nothing."""
    basis = str((social or {}).get("identity_basis") or "").strip().lower()
    if not basis:
        return False
    empty = set(METHOD["badge_words"]) | set(METHOD["badge_filler"])
    return any(word not in empty for word in _words(basis.replace("_", " ")).split())


def tier_of(source):
    """Directness tier of one source: who is speaking, not how many repeat it."""
    if origin_of(source) is None:
        return "secondary"
    role = source.get("source_role")
    if _medium(source) == "social":
        social = source.get("social") or {}
        mapped = METHOD["social_tier"].get(str(social.get("account_tier") or "").strip().upper(), "unverified")
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


def is_discovery_aid(source):
    """An encyclopedia or an aggregator: a way to find sources, never one itself."""
    return origin_of(source) is None or source.get("source_role") in METHOD["discovery_aid_roles"]


def _claims_of(source, field):
    """`supports` / `disputes` as a list of known claims. A bare string is one claim, never a
    substring to search: "no_attribution" does not support attribution."""
    value = source.get(field)
    if value is None:
        return None
    value = [value] if isinstance(value, str) else list(value)
    return [c for c in value if c in CLAIMS]


def _supports(source, claim):
    # A source recorded as disputing a claim never backs it, whatever `supports` says. One that
    # denies the event happened does not back an effect of it either.
    disputed = _claims_of(source, "disputes") or []
    if claim in disputed or (claim == "effect" and "occurrence" in disputed):
        return False
    declared = _claims_of(source, "supports")
    # Country-system events predate claim-level provenance: every citation supports the event.
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


def _later_formal_account(source, date, date_end):
    """A dated first-party source published after the window that is a formal account: a
    regulator's final report, a court record, a government inquiry, or a source that says so
    itself (`formal_account: true`, for an operator's regulatory filing). An investigation that
    reports eight months later is not weaker evidence than a same-day line."""
    stop, cited = _date(date_end or date, end=True), _date(source.get("date"))
    if not (stop and cited) or tier_of(source) != "direct":
        return False
    formal = source.get("formal_account") is True or source.get("source_role") in METHOD["formal_account_roles"]
    return formal and cited > stop + dt.timedelta(days=METHOD["contemporaneous_days"])


# --- originating statements ----------------------------------------------------------------------

def _publisher_key(source):
    return _words(source.get("publisher")) or None


def organisation_of(source):
    """The organisation a source belongs to, from the parameter file's table, followed up to its
    parent: two arms of one department, or a state news agency and its state, are one voice. None
    when the table does not know it, which is most sources."""
    from pipeline import build_systems as B
    table = {o["id"]: o for o in METHOD["origins"]["organisations"]}
    host, domain = _host(source), B.registered_domain(_url(source))
    publisher = f" {_publisher_key(source) or ''} "
    handle = str((source.get("social") or {}).get("handle") or "").strip().lower().lstrip("@")
    for org in table.values():
        hit = (domain in org.get("domains", ()) or host in org.get("domains", ())
               or any(host == s or host.endswith("." + s) for s in org.get("domain_suffixes", ()))
               or any(f" {p} " in publisher for p in org.get("publishers", ()))
               or (handle and handle in org.get("handles", ())))
        if hit:
            seen, oid = set(), org["id"]
            while table.get(oid, {}).get("parent") and oid not in seen:
                seen.add(oid)
                oid = table[oid]["parent"]
            return oid
    return None


def _filed_form(source):
    text = f"{source.get('url') or ''} {source.get('publisher') or ''}".lower()
    return next((f for f in METHOD["origins"]["filed_forms"] if any(m in text for m in f["match"])), None)


def origin_keys(source):
    """Every identity a source shares with others that carry the same statement: its origin, its
    publisher's name, its organisation, its own `ref`, and the `ref` it says it relays."""
    keys = {("origin", origin_of(source))}
    if _publisher_key(source):
        keys.add(("publisher", _publisher_key(source)))
    if organisation_of(source):
        keys.add(("organisation", organisation_of(source)))
    if source.get("ref"):
        keys.add(("statement", str(source["ref"])))
    if source.get("relays"):
        # A relay never adds an origin: it joins the statement it relays, cited or not.
        keys.add(("statement", str(source["relays"])))
    return keys


def independent_origins(sources):
    """How many originating statements stand behind `sources`: the number of groups left when
    sources that share an origin, a publisher, an organisation or a declared relay are joined, and
    a filed form is joined to its filer. Discovery aids count for nothing.

    This is an upper bound on independence. Republication a record does not name stays invisible,
    so it can overstate; `assess` therefore calls it a count of independent statements only when a
    reviewer checked it. It can also fall when a source is added: a citation that links two groups
    shows they were one."""
    counted = [s for s in sources if origin_of(s) is not None]
    parent = list(range(len(counted)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    owner = {}
    for i, s in enumerate(counted):
        for key in origin_keys(s):
            if key in owner:
                parent[find(i)] = find(owner[key])
            else:
                owner[key] = i
    for i, s in enumerate(counted):
        form = _filed_form(s)
        if form:
            for j, other in enumerate(counted):
                if other.get("source_role") in form["filed_by_roles"]:
                    parent[find(i)] = find(j)
    return len({find(i) for i in range(len(counted))})


def origins_reviewed(review):
    """Whether a reviewer checked which of a record's sources relay which. True for a record whose
    review block shows the source-and-attribution role accepting it (impact records: that reviewer
    sets a shared `origin` or `relays` on every relay). A country record's reviewers did not."""
    cfg = METHOD["origins"]
    roles = (review or {}).get("roles") or {}
    return roles.get(cfg["reviewed_by_role"]) in cfg["accepting_verdicts"]


def _reviewer_opened(review):
    """The record's own review block says a reviewer opened at least one source."""
    try:
        return int((review or {}).get("sources_opened_by_reviewer") or 0) > 0
    except (TypeError, ValueError):
        return False


# --- evidence confidence -------------------------------------------------------------------------

def _disputed(sources, dispute):
    """Whether occurrence or effect is credibly contested: the record says so, or a direct or
    independent source is recorded as disputing one of them (`disputes`, the mirror of
    `supports`). An anonymous denial is not credible disagreement, and a dispute about who did it
    belongs to attribution."""
    if dispute:
        about = dispute.get("about") if isinstance(dispute, dict) else None
        about = [about] if isinstance(about, str) else list(about or [])
        about = [str(a).strip().lower() for a in about]
        # A dispute that does not say what it is about, or says something outside the vocabulary
        # ("figure"), is read as one about the record itself: the conservative reading, since
        # Disputed claims less than any category. A dispute about the cause or about who did it
        # is not one about whether it happened.
        about = [a if a in CLAIMS + ("cause",) else "occurrence" for a in about]
        if not about or any(a in ("occurrence", "effect") for a in about):
            return True
    return any(tier_of(s) in METHOD["corroborating_tiers"]
               and any(a in ("occurrence", "effect") for a in (_claims_of(s, "disputes") or []))
               for s in sources)


def _category(category_id):
    return next(c for c in METHOD["categories"] if c["id"] == category_id)


def _not_assessed(disputed, basis):
    """A record with nothing to assess. Null, not Preliminary and not zero: the three absences stay
    distinct, and "a primary source is not yet attached" is a research state."""
    cfg = METHOD["not_assessed"]
    return {
        "category": None, "label": cfg["label"], "score": None, "disputed": disputed,
        "reason": cfg["discovery_aid_only"], "cap": None,
        "components": {
            "directness": {"tier": None, "points": None},
            "origins": {"count": 0, "points": None, "basis": basis},
            "effect": {"specificity": None, "points": None},
            "opened": {"points": None},
            "contemporaneous": {"points": None, "dated": None},
        },
        "reasons": [cfg["discovery_aid_only"][0].upper() + cfg["discovery_aid_only"][1:]],
    }


def assess(sources, date, date_end=None, effect_specificity="described", dispute=None, review=None):
    """Evidence confidence for occurrence and effect: category, ordinal score and its components.

    `review` is the record's own review block. It answers two things the citations cannot: whether
    a reviewer opened a source, and whether a reviewer checked which sources relay which. Without
    it the origin count is a count of publishers and the record cannot be High.

    `category` is None, with `reason`, for a record cited only through a discovery aid."""
    backing = [s for s in sources if _supports(s, "occurrence") or _supports(s, "effect")]
    basis = "reviewed" if origins_reviewed(review) else "publishers"
    disputed = _disputed(sources, dispute)
    if backing and all(is_discovery_aid(s) for s in backing):
        return _not_assessed(disputed, basis)

    tiers = [tier_of(s) for s in backing]
    best = max(tiers, key=TIER_ORDER.index) if tiers else None
    strong = [s for s, t in zip(backing, tiers) if t in METHOD["corroborating_tiers"]]
    origin_count = independent_origins(strong)

    directness = METHOD["tiers"][best]["points"] if best else 0
    origin_points = METHOD["origin_points"][str(min(origin_count, 3))] if origin_count else 0
    effect_backed = any(_supports(s, "effect") for s in strong)
    effect_points = METHOD["effect_points"].get(effect_specificity, 0) if effect_backed else 0
    # Opened during research (the source's own flag) or during review (the record's review block).
    # "Not recorded" on a source is not "not opened": it earns nothing by itself and costs nothing
    # where the review block says a reviewer read the sources.
    was_opened = bool(strong) and (any(s.get("opened") is True for s in strong) or _reviewer_opened(review))
    opened = METHOD["opened_points"] if was_opened else 0
    # A report at the time, or a later formal account. A source with no date is "not recorded":
    # said in the reasons, because the absence of a date is not a finding about the event.
    dated = (None if not strong
             else "at_the_time" if any(_contemporaneous(s, date, date_end) for s in strong)
             else "later_formal_account" if any(_later_formal_account(s, date, date_end) for s in strong)
             else "outside_window" if any(_date(s.get("date")) for s in strong)
             else "not_recorded")
    timely = METHOD["contemporaneous_points"] if dated in ("at_the_time", "later_formal_account") else 0
    score = directness + origin_points + effect_points + opened + timely

    category = next(c for c in METHOD["categories"] if score >= c["min"])
    cap = None
    order = [c["id"] for c in METHOD["categories"]]            # strongest first
    ceiling = METHOD["origins"]["cap_when_not_reviewed"]
    if basis != "reviewed" and order.index(category["id"]) < order.index(ceiling):
        # Two publishers may be one statement relayed. Until someone has checked, the count is an
        # upper bound, and an upper bound does not earn the top category.
        category, cap = _category(ceiling), "origins_not_reviewed"
    if best in (None, "researcher_social", "unverified"):
        category = _category(METHOD["caps"]["unverified_only"])
        cap = "unverified_only" if best else None
    if disputed:
        category = METHOD["disputed"]

    reasons = []
    if best:
        reasons.append(METHOD["tiers"][best]["label"])
    first_party = [s for s, t in zip(backing, tiers) if t == "direct"]
    if first_party and all(s.get("source_role") in METHOD["party_roles"] for s in first_party):
        # "First-party" says who is speaking. Where that is the affected party, say so: its
        # account of its own facility has not been checked by anyone else the record cites.
        reasons.append("The first-party source is the affected party itself")
    if not origin_count:
        reasons.append("No first-party source and no press report")
    elif basis == "reviewed":
        reasons.append(f"{origin_count} independent originating statements" if origin_count >= 2
                       else "One originating statement")
    else:
        reasons.append(f"{origin_count} distinct publishers cited; whether they relay one statement was not reviewed"
                       if origin_count >= 2 else "One publisher cited")
    if effect_backed:
        reasons.append({"quantified": "Effect quantified by a source", "described": "Effect described, not quantified",
                        "vague": "Effect reported only in general terms"}.get(effect_specificity, "Effect not assessed"))
    else:
        reasons.append("No first-party source or press report for the effect")
    if opened:
        reasons.append("A cited source was opened during research or review")
    if dated == "at_the_time":
        reasons.append("Reported at the time")
    elif dated == "later_formal_account":
        reasons.append("A dated formal account, published later")
    elif dated == "not_recorded":
        reasons.append("No cited source carries a date: not recorded")
    if cap == "origins_not_reviewed" and not disputed:
        reasons.append(f"Held at {_category(ceiling)['label']}: independence of the cited sources has not been reviewed")
    if cap == "unverified_only":
        reasons.append("Rests on unverified claims only")
    if disputed:
        # Nothing positive is shown as settled on a contested record: no total, and the reader is
        # told what is contested before what was cited.
        reasons = ["Credible sources disagree",
                   "The lines below describe the sources cited; they are not a settled reading"] + reasons

    return {
        "category": category["id"], "label": category["label"], "score": None if disputed else score,
        "disputed": disputed, "reason": None, "cap": cap,
        "components": {
            "directness": {"tier": best, "points": directness},
            "origins": {"count": origin_count, "points": origin_points, "basis": basis},
            "effect": {"specificity": effect_specificity if effect_backed else None, "points": effect_points},
            "opened": {"points": opened},
            "contemporaneous": {"points": timely, "dated": dated},
        },
        "reasons": reasons,
    }


# --- attribution ---------------------------------------------------------------------------------

def _actor_names(attribution):
    a = attribution or {}
    return [n for n in (_words(x) for x in [a.get("actor"), *(a.get("actor_aliases") or [])]) if n]


def _published_by_actor(source, attribution):
    """The source is the named actor speaking: its publisher or origin is the actor (or a name the
    record lists for it, such as the government body that announced its own operation). A name of
    two or more words also matches inside a longer publisher name ("Group X News")."""
    voices = [f" {v} " for v in (_publisher_key(source), _words(source.get("origin")),
                                 _words((source.get("social") or {}).get("display_name"))) if v]
    for name in _actor_names(attribution):
        for voice in voices:
            if voice.strip() == name or (" " in name and f" {name} " in voice):
                return True
    return False


def _own_claim(source, attribution=None):
    """The actor's own claim of responsibility, whatever role the source was given: typed as one,
    declared as one (a wire report of the claim carries the claim), or published by the actor."""
    return (source.get("source_role") == "actor_self_claim"
            or source.get("attribution_basis") == "actor_self_claim"
            or _published_by_actor(source, attribution))


def _basis(source, attribution=None):
    """Whose authority a source carries when it names an actor, or None when it carries none.

    The actor's own claim is a claim whatever else the record says about it. A discovery aid and
    an anonymous or unestablished account are not credible attribution and carry nothing. The
    `attribution_basis` override (a wire story reporting a government's attribution) is honoured
    only on a direct or independently reporting source: a post or an aggregator cannot borrow a
    government's authority."""
    role = source.get("source_role")
    declared = source.get("attribution_basis")
    if _own_claim(source, attribution):
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


def _own_finding(source):
    """An attribution the source makes itself: it sits in the first-party or press tier and it is
    not a restating role, unless that role declares an investigation of its own
    (`attribution_basis: "media_investigation"`). A source that says it relays a cited statement
    needs no rule here: `independent_origins` joins it to that statement, so it is never a second."""
    if tier_of(source) not in METHOD["corroborating_tiers"]:
        return False
    if source.get("source_role") in METHOD["attribution"]["restating_roles"]:
        return source.get("attribution_basis") == "media_investigation"
    return True


def _attribution_evidence(sources, attribution=None):
    """(backing, named, claims): every source that supports attribution, those that carry a
    credible third-party attribution, and the actor's own claims with everything that relays them.

    A relay of a claim is a claim: a source that says it relays one (`relays`), and, where a claim
    is among the sources, press coverage that declares no basis of its own. "Group X claimed
    responsibility", reported by any number of outlets, is still one claim by Group X."""
    backing = [s for s in sources if _supports(s, "attribution")]
    claims = [s for s in backing if _own_claim(s, attribution)]
    rest = [s for s in backing if not _own_claim(s, attribution)]
    moved = bool(claims)
    while moved:
        # To a fixed point: a relay of a relay of the claim is the claim too, in whatever order
        # the sources are listed.
        refs = {str(s["ref"]) for s in claims if s.get("ref")}
        relays = [s for s in rest if (s.get("relays") and str(s["relays"]) in refs) or not _corroborates(s)]
        rest = [s for s in rest if not any(s is r for r in relays)]
        claims += relays
        moved = bool(relays)
    named = [s for s in rest if _basis(s, attribution) is not None]
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
    if (attribution or {}).get("competing"):
        # A competing attribution is on the record: whatever the status says, it is contested.
        return "DISPUTED"
    _backing, named, claims = _attribution_evidence(sources, attribution)
    cfg = METHOD["attribution"]
    if not named:
        return "CLAIM_ONLY" if claims else "NOT_ESTABLISHED"
    bases = {_basis(s, attribution) for s in named}
    # Who counts toward corroboration: a first-party or press-tier source with a finding of its
    # own. A post, a dataset, an aggregator or an unknown role can show that someone names the
    # actor (Low) and nothing more.
    own = [s for s in named if _own_finding(s)]
    # An attribution carried at one remove (a wire reporting a government's statement that the
    # record does not cite) is one attribution of the relayed basis. However many outlets carry
    # it, and whatever bases they declare, together they add at most one: they may all be one
    # press conference.
    relayed = [s for s in named if not any(s is o for o in own) and _corroborates(s)
               and tier_of(s) in METHOD["corroborating_tiers"]]
    separate = independent_origins(own)
    if any(independent_origins(own + [r]) > separate for r in relayed):
        separate += 1
    firm_bases = {_basis(s, attribution) for s in own + relayed}
    if firm_bases & set(cfg["official_bases"]) and len(firm_bases) >= 2 and separate >= 2:
        level = "HIGH"
    elif (bases & set(cfg["first_party_bases"])
          or independent_origins([s for s in own if _basis(s, attribution) in cfg["technical_bases"]]) >= 2):
        level = "MODERATE"
    else:
        level = "LOW"
    # The confidence cannot say more than the status does.
    order = ("LOW", "MODERATE", "HIGH")
    ceiling = cfg["status_ceiling"].get(status)
    return order[min(order.index(level), order.index(ceiling))] if ceiling else level


def attribution_problems(attribution, sources):
    """Where an attribution's status says more (or less) than its sources do."""
    out = []
    a = attribution or {}
    status = a.get("status")
    if status not in ATTRIBUTION_STATUSES:
        return [f"attribution status {status!r} is not one of {ATTRIBUTION_STATUSES}"]
    backing, named, claims = _attribution_evidence(sources, a)
    bases = {_basis(s, a) for s in named}
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
        # Only a source with a finding of its own makes CLAIMED an understatement. Outlets
        # reporting the claim are the claim again.
        if named:
            out.append("CLAIMED but another party also attributes: the status understates the sources")
    elif status == "DISPUTED":
        if len(a.get("competing") or []) < 1:
            out.append("DISPUTED needs the competing attribution listed")
    else:
        if not named:
            out.append(f"{status} has no credible source naming the actor: the actor's own claim, and any "
                       "report of it, is CLAIMED; an anonymous post or a discovery aid attributes nothing")
        # Methodology §8.2: ATTRIBUTED is a formal attribution. Any number of technical or press
        # attributions that agree is ASSESSED (iteration 22: three origins used to be enough here).
        if status == "ATTRIBUTED" and not bases & set(cfg["official_bases"]):
            out.append("ATTRIBUTED needs a formal government or law-enforcement attribution; "
                       "technical or press attributions that agree are ASSESSED")
    for b in a.get("basis") or []:
        if b not in ATTRIBUTION_BASES:
            out.append(f"attribution basis {b!r} is not one of {ATTRIBUTION_BASES}")
    return out


# --- AI involvement ------------------------------------------------------------------------------

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


# --- the method, as served data ---------------------------------------------------------------------

def source_problems(source):
    """What a gate should refuse before a source is scored: values outside the vocabulary. Scoring
    itself reads each of these conservatively (an unknown role is secondary, a post with no tier is
    unverified, a shortened link counts for nothing), so a record that slips past is understated,
    never overstated; the gate is what makes the typing mean something."""
    out = []
    medium = source.get("medium")
    if medium is not None and str(medium).strip().lower() not in METHOD["media"]:
        out.append(f"medium {medium!r} is not one of {tuple(METHOD['media'])}")
    if source.get("source_role") not in METHOD["role_tier"]:
        out.append(f"source_role {source.get('source_role')!r} is not one of {tuple(sorted(METHOD['role_tier']))}")
    if _on(_host(source), METHOD["shortener_hosts"]):
        out.append("a shortened link is not a citation: cite the page it points to")
    if _medium(source) == "social":
        social = source.get("social") or {}
        if str(social.get("account_tier") or "").strip().upper() not in METHOD["social_tier"]:
            out.append(f"a social post needs social.account_tier, one of {tuple(METHOD['social_tier'])}")
        if str(medium or "").strip().lower() != "social":
            out.append("the address is on a social platform: medium must be 'social'")
    for field in ("supports", "disputes"):
        value = source.get(field)
        if value is not None and (isinstance(value, str) or any(c not in CLAIMS for c in value)):
            out.append(f"{field} must be a list of {CLAIMS}, not {value!r}")
    if source.get("date") and _date(source["date"]) is None:
        out.append(f"date {source['date']!r} cannot be read: use YYYY, YYYY-MM or YYYY-MM-DD")
    return out


def dispute_problems(dispute):
    """A record's `dispute` must say what is disputed, in the vocabulary. "cause" is accepted and
    recorded; this module's category does not cover cause (docs/EVIDENCE_CONFIDENCE_V2.md §7)."""
    if dispute in (None, False):
        return []
    if not isinstance(dispute, dict):
        return ["dispute must be an object with `about`"]
    about = dispute.get("about")
    about = [about] if isinstance(about, str) else list(about or [])
    known = CLAIMS + ("cause",)
    if not about:
        return [f"dispute needs `about`, one or more of {known}"]
    return [f"dispute.about {a!r} is not one of {known}" for a in about if a not in known]


def calibration_status():
    """What may be said about the thresholds. Tied to the version: while it ends in "-draft" no
    calibration result has been recorded and nothing may claim a calibration."""
    return METHOD["status_while_draft"] if METHOD["version"].endswith("-draft") else METHOD["status_when_calibrated"]


def method():
    """The method as served data, for the confidence drawer and the glossary."""
    return {
        "version": METHOD["version"],
        "status": calibration_status(),
        "statement": METHOD["statement"],
        "questions": [
            {"id": "evidence", "label": "Evidence confidence",
             "asks": "Did it happen, and is the reported effect supported, on the sources this record cites?"},
            {"id": "attribution", "label": "Attribution confidence",
             "asks": "How strong is the evidence about who did it?"},
            {"id": "ai", "label": "AI involvement",
             "asks": "Does a source tie AI to this incident, and how firmly?"},
        ],
        "components": [
            {"id": "directness", "label": "Who is speaking", "max": METHOD["tiers"]["direct"]["points"],
             "tiers": [{"id": t, **METHOD["tiers"][t]} for t in reversed(TIER_ORDER)]},
            {"id": "origins", "label": "Originating statements", "max": METHOD["origin_points"]["3"],
             "meaning": "Counted in originating statements, not links: a wire story and its copies are one; "
                        "releases from one organisation are one, on its website or its official account; a "
                        "form and the operator that filed it are one; a relay is the statement it relays. "
                        "Where a reviewer checked which sources relay which, the count is of independent "
                        "statements. Where nobody did, it is a count of distinct publishers, an upper bound, "
                        "and the record cannot be High."},
            {"id": "effect", "label": "How specific the reported effect is", "max": METHOD["effect_points"]["quantified"],
             "meaning": "Quantified, described or only general, as a first-party source or the press reports it."},
            {"id": "opened", "label": "Opened during research or review", "max": METHOD["opened_points"],
             "meaning": "A first-party source or press report was opened by the researcher, or the record's "
                        "review says a reviewer opened its sources. Not recorded is not the same as not opened."},
            {"id": "contemporaneous", "label": "Dated account", "max": METHOD["contemporaneous_points"],
             "meaning": f"A first-party source or press report dated within {METHOD['contemporaneous_days']} days of the "
                        "event, or a later formal account (a regulator's report, a court record, a government "
                        "inquiry). A source with no date is not recorded, which is said and is not a finding."},
        ],
        "categories": METHOD["categories"] + [METHOD["disputed"]],
        "not_assessed": METHOD["not_assessed"],
        "origin_bases": {
            "reviewed": "A reviewer checked which sources relay which: the count is of independent originating statements.",
            "publishers": "Distinct publishers cited. Whether they relay one statement was not reviewed.",
        },
        "overrides": [
            "Disputed overrides the points: credible sources disagree, the product does not choose, and no "
            "total is shown. A source that disputes a claim is never counted as support for it.",
            "A record resting only on unverified posts or an actor's own claim is at most Preliminary.",
            "A record whose sources' independence has not been reviewed is at most Moderate.",
            "A record cited only through an encyclopedia or an aggregator is not assessed.",
        ],
        "properties": [
            "A duplicate citation, or a second citation from the same publisher at the same origin, changes nothing.",
            "The number of links never enters; only who is speaking and how many originating statements there are.",
            "Adding a source never lowers a component, with one exception: a citation that shows two sources "
            "share an origin lowers the count of originating statements.",
            "The points are ordinal: they order records by what their citations show. They are not a probability "
            "and not a percentage.",
        ],
        "attribution": METHOD["attribution"],
    }
