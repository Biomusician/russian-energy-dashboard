"""Review a country's candidate queue into its curated events (iteration 14, dual review 16).

    .venv\\Scripts\\python.exe scripts\\import_candidates.py us [cn sa ca in]

`data/candidates/<id>.json` is a research queue written by research lanes. Nothing in it is
published. This script is the gate between the two: it applies the review rules below,
writes only the records that pass to `data/curated/systems/<id>/events.json`, and reports
every record it held back and why. Run it when a queue changes, read the report, and commit
the curated file. The build never reads the queue (see pipeline/build_systems.py).

REVIEW RULES. A candidate is imported only if all hold:
  1. The research lane's suggested disposition is "accept".
  2. Every source has a URL, and not every source is marked as unopened. Lanes record
     `opened: true/false` per source; where a lane did not record it the event says
     "access not recorded" rather than being presented as checked (iteration 14 red team:
     a missing value used to count as opened).
  3. It is placed in a first-level unit of this system, or explicitly at country level.
  4. No text field trips the scope scan (coordinates, distances, vulnerability or dependency
     language, weapon, defence or attack-method detail, cyber technique). A hit holds the
     record for a person to read. Reviewer edits in data/curated/systems/review_edits.json
     are applied first, so a record is scanned as it will ship.
  5. Its id is a well-formed slug and unique in the system.
  6. (Iteration 16.) It was reviewed TWICE: `primary_review.completed` by the researcher who
     found it, and `independent_review.completed` by a second reviewer who opened at least one
     source and gave a disposition of `confirmed` or `corrected`. `held` and `removed` stop it.
     Records published before this rule are grandfathered by id in
     data/curated/systems/review_grandfathered.json, a frozen list that can only shrink.

PUBLICATION POLICY. A record covered by an ACTIVE campaign in
data/curated/systems/conflict_campaigns.json is imported with its recovery block replaced by the
withheld marker; the evidence stays here, in the local queue, and never reaches the repository.
When the campaign is recorded as ended and the release rule is met, a re-import publishes it.

WHAT REVIEW HERE DOES NOT MEAN. Even dual review is not omniscience: the reviewer checks the
record against its sources, not the world. Every imported event says how it was reviewed.
"""

import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import build_systems, calendars, ids, systems  # noqa: E402
from pipeline.fetch_wikipedia import safe_title  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REVIEW_DATE = "2026-10-30"

# Geography rulings that hold a record back because the system does not cover the place,
# never because of what happened there.
OUT_OF_GEOGRAPHY = {
    "us": {"US-PR", "US-VI", "US-GU", "US-AS", "US-MP"},
}

# Phrases that have no business in a disruption record under this project's scope boundary.
# Deliberately broad: a false positive costs a person one read; a false negative publishes.
# Widened in iteration 14 after a red team found it missed bare decimal coordinates, distance
# phrasing, hyphenated "air-defence", weapon designators, cyber technique and dependency
# language ("sole feed", "in-feed"), and false-positived on "price range of".
SCOPE_SCAN = re.compile(
    "|".join([
        # coordinates and map links
        r"\d+(\.\d+)?\s*°", r"\b\d{1,3}\.\d{3,}\s*[NSEW]\b", r"\b-?\d{1,3}\.\d{3,}\s*,\s*-?\d{1,3}\.\d{3,}",
        r"\blat(itude)?\b\.?\s*-?\d", r"\blon(gitude)?\b\.?\s*-?\d", r"\blatitude\b", r"\blongitude\b",
        r"maps\.google|google\.[a-z.]+/maps|\?q=-?\d",
        # distance and sub-region placement
        r"\b\d+(\.\d+)?\s*(km|kilomet(re|er)s?|mi|miles?)\s+(north|south|east|west|from|away)",
        r"within (about |roughly |some )?\d+\s*(km|kilomet|mi)", r"\bmilepost\b", r"\bkm from\b",
        r"\b(kilomet(re|er)s?|miles) (from|away)\b",
        # vulnerability, dependency, criticality
        r"vulnerab", r"weakest", r"weak point", r"single[- ]point[- ]of[- ]failure", r"choke ?point",
        r"bottleneck", r"\bredundan", r"\bN-1\b", r"critical node", r"\bin-?feed\b", r"sole (feed|source|supply|line)",
        r"only (line|feed|source|route) (supplying|into|to|feeding)", r"no alternative (supply|route|feed)",
        r"draws? [\d,.–-]+\s*(MW|GW)\s+(via|through|from)",
        # defences and weapons
        r"defen[cs]e gap", r"air[- ]defen[cs]e", r"defen[cs]es (were|was) (thin|weak)", r"intercept",
        r"shot down", r"warhead", r"ballistic", r"cruise missile", r"munition", r"\bShahed\b", r"\bQuds\b",
        r"\bPatriot batter", r"\bS-[34]00\b", r"within range\b",
        # cyber technique
        r"\bexploit", r"malware", r"ransomware", r"\bpayload\b", r"\bCVE-\d", r"\bSCADA\b", r"\bHMI\b",
        r"backdoor", r"phishing", r"Industroyer", r"IEC[- ]?104",
    ]),
    re.I)
TEXT_FIELDS = ("summary", "effect", "threshold_basis", "facility_name", "facility_name_local",
               "operator", "attribution_reported")
EDITS = ROOT / "data" / "curated" / "systems" / "review_edits.json"
# Publication dates a cited page states about itself (scripts/check_source_links.py), keyed by URL.
LINK_HEALTH = ROOT / "data" / "curated" / "systems" / "source_link_health.json"
DEFAULT_PROCESS = ("Single-pass open-source research lane; centrally reviewed against the "
                   "inclusion threshold, source rules and scope scan. Claims were not "
                   "independently re-verified beyond the cited sources.")
DUAL_PROCESS = ("Found by a research lane; then a second, independent reviewer opened the sources "
                "and checked identity, date, region, class, threshold, provenance, wording and "
                "episode before publication.")
GRANDFATHERED = ROOT / "data" / "curated" / "systems" / "review_grandfathered.json"
PASSING_DISPOSITIONS = ("confirmed", "corrected")
# Iteration 17: three blind roles (docs/REVIEW_GOVERNANCE.md §7). A record reviewed this way names
# the standard; every role must have accepted it, and the reconciled text is what they accepted.
BLIND = "blind_three_role"
BLIND_ROLES = ("evidence", "safety", "taxonomy")
BLIND_PASS = ("accept", "accept_with_correction")
BLIND_PROCESS = ("Found by a research lane; then reviewed blind by three independent reviewers, "
                 "none of whom saw the researcher's rationale or each other: one opened the sources "
                 "and checked identity, date, region, threshold and every figure; one checked the "
                 "text for placement finer than first-level region, inventories, dependency and "
                 "status wording; one checked class, cause, hazard name, episode and duplicates. "
                 "Published only because all three accepted it; their corrections were reconciled "
                 "into this text.")


PAGE_DATES = (json.loads(LINK_HEALTH.read_text(encoding="utf-8")).get("page_stated_dates", {})
              if LINK_HEALTH.exists() else {})
# Where a redirecting citation lands, from the last link check (iteration 20).
FINAL_ADDRESSES = (json.loads(LINK_HEALTH.read_text(encoding="utf-8")).get("final_addresses", {})
                   if LINK_HEALTH.exists() else {})


def canonical_url(url):
    """The address a citation is published under: where the link lands, without an amp suffix. A
    reader should reach the article, and the gate should judge the address the reader sees."""
    if not url:
        return url
    final = re.sub(r"/amp/?$", "/", FINAL_ADDRESSES.get(url, url))
    final = re.sub(r"[?&](amp(=1)?|outputType=amp)$", "", final)
    # The common spellings of an accelerated-mobile copy: an "amp." host, a leading "/amp/" path
    # segment, and "/ampArticle/" for "/article/". Each is the same article at its canonical address.
    final = re.sub(r"^(https?://)amp\.", r"\1", final)
    final = re.sub(r"^(https?://[^/]+)/amp/", r"\1/", final)
    return re.sub(r"/ampArticle/", "/article/", final)


# A page's own date, found under the address the citation is now published at.
PAGE_DATES = {**{canonical_url(u): d for u, d in PAGE_DATES.items()}, **PAGE_DATES}


def _texts(r):
    yield from (str(r.get(k) or "") for k in TEXT_FIELDS)
    yield json.dumps(r.get("recovery") or {}, ensure_ascii=False)
    yield json.dumps(r.get("capacity_affected") or {}, ensure_ascii=False)


# Words in a facility's name that do not identify it. What is left ("laffan", "ahmadi", "pars")
# does, and a citation whose address carries one names the place the record is not allowed to.
GENERIC_NAME_WORDS = {
    "refinery", "refineries", "plant", "plants", "field", "fields", "terminal", "terminals", "complex", "station",
    "stations", "power", "company", "corporation", "industrial", "city", "port", "ports", "facility", "facilities",
    "storage", "depot", "pipeline", "processing", "petrochemical", "petroleum", "energy", "national", "north",
    "south", "east", "west", "central", "island", "zone", "area", "unit", "units", "project", "export", "water",
    "desalination", "liquefied", "natural", "offshore", "onshore", "governorate", "province", "municipality", "emirate",
    "kuwait", "kuwaiti", "qatar", "qatari", "bahrain", "bahraini", "oman", "omani", "iran", "iranian", "iraq", "iraqi",
    "emirates", "emirati", "saudi", "arabia", "gulf", "arab", "united", "state", "sultanate", "kingdom", "islamic", "republic",
    "northern", "southern", "eastern", "western", "capital", "neutral", "region", "district", "news", "english", "article",
    "مصفاة", "محطة", "حقل", "ميناء", "شركة", "مدينة", "الصناعية", "منشأة", "مجمع", "مستودع", "الكويت", "قطر", "البحرين",
    "عمان", "الإمارات", "ایران", "العراق", "پالایشگاه", "نیروگاه", "میدان", "پتروشیمی", "شرکت", "بندر", "استان", "محافظة",
}


_GENERIC = None


def _generic():
    global _GENERIC
    if _GENERIC is None:
        _GENERIC = {build_systems.fold(w) for w in GENERIC_NAME_WORDS}
    return _GENERIC


# An Arabic word can carry the article and a one-letter preposition or conjunction in front:
# "بالبصرة" is "in Basra". A word is also read without them.
ARABIC_PREFIXES = ("وال", "بال", "فال", "كال", "لل", "ال", "و", "ب", "ل", "ف")


def word_forms(w):
    out = {w}
    if not w.isascii():
        for pre in ARABIC_PREFIXES:
            if w.startswith(pre) and len(w) - len(pre) >= 3:
                out.add(w[len(pre):])
    return out


def _words(text):
    """Single words, folded, three letters or more in Arabic script and four in Latin."""
    return [w for w in re.findall(r"[^\W\d_]+", build_systems.fold(text))
            if (len(w) >= 3 and not w.isascii()) or len(w) >= 4]


def name_tokens(r):
    """The distinctive words of a record's facility, operator and place names, in any script.

    `withheld_place_words` is a list a reviewer or the lead adds for what the name fields do not
    hold: a region, a town, an operator's short name. The first Iraq packet showed why: the only
    token from the facility's name was one word, and an address under a regional section of a
    news site, or one naming the operator, went straight through (blind safety review)."""
    out = set()
    for k in ("facility_name", "facility_name_local", "admin1_name", "operator"):
        for w in _words(str(r.get(k) or "")):
            if w not in _generic():
                out.add(w)
    out |= {build_systems.fold(str(w)).strip() for w in (r.get("withheld_place_words") or []) if len(str(w)) >= 3}
    return out


def unit_words(units):
    """The distinctive words of every first-level unit's name. An address that names any unit of
    the country narrows a record published for the country as a whole."""
    out = set()
    for u in units:
        out |= name_tokens({"admin1_name": u[1]})
        # The whole name as a phrase: "dhi qar" and "abu dhabi" are read even where each word is
        # short or common (iteration 20, geography red team).
        phrase = " ".join(re.findall(r"[^\W\d_]+", build_systems.fold(str(u[1]))))
        if " " in phrase or len(phrase) >= 2:
            out.add(phrase)
    return sorted(out)


def place_tokens(r, policy):
    return name_tokens(r) | set((policy or {}).get("unit_words") or [])


def short_link(url):
    """A publisher's redirecting short link ("/?p=500001"): no path, only a query. The address a
    reader lands on is a different string, with the headline in it, and the gate never read it
    (release safety red team, iteration 19)."""
    rest = (url or "").split("://", 1)[-1].partition("/")[2]
    path, _, query = rest.partition("?")
    return bool(query) and not re.search(r"[^\W\d_]{3,}", unquote(path))


def opaque_unresolved(url):
    """An address with no words in its path ("/node/2636397", "/article/74438") whose destination
    no link check has recorded: what a reader lands on was never read (iteration 20)."""
    if url in FINAL_ADDRESSES:
        return False
    path = unquote(url or "").split("://", 1)[-1].partition("/")[2].partition("?")[0]
    words = set(re.findall(r"[^\W\d_]{3,}", path.lower())) - GENERIC_PATH_WORDS
    return bool(path) and not words and bool(re.search(r"\d{4,}", path))


# Path words that say nothing about the article ("/node/123", "/ar/article/456").
GENERIC_PATH_WORDS = {"node", "article", "articles", "news", "newsdetails", "story", "stories", "post",
                      "posts", "item", "details", "detail", "amp", "html", "php", "aspx", "index",
                      # Section names say nothing about the article (iteration 20, geography red team).
                      "english", "arabic", "persian", "world", "business", "politics", "economy", "energy",
                      "middleeast", "region", "local", "latest", "home", "kurdistan", "iraq", "gulf"}


def unpublishable_address(url, tokens):
    """A citation that cannot stand beside a record published without its place: its address, or
    the address it redirects to, names the place or the operator, says how the attack was carried
    out, or is a short or opaque link whose destination was never read."""
    final = FINAL_ADDRESSES.get(url, url)
    return any(names_the_place(u, tokens) or build_systems.method_in_address(u) for u in {url, final}) \
        or (short_link(url) and url not in FINAL_ADDRESSES) or opaque_unresolved(url)


def names_the_place(url, tokens):
    """Whether a citation's address spells out the facility or region. Read as folded words, so an
    Arabic or Persian slug is read like a Latin one, whatever its letter forms, diacritics, attached
    prefixes or escapes; a multi-word name is read as a phrase; and a subdomain counts
    ("basra.example.com"), the publisher's own registered domain does not."""
    rest = (url or "").split("://", 1)[-1]
    host, _, path = rest.partition("/")
    labels = [x for x in host.lower().split(".") if x and x != "www"][:-2]
    text = " ".join(labels) + " " + path
    seq = [w for w in re.findall(r"[^\W\d_]+", build_systems.fold(text))]
    words = {f for w in seq for f in word_forms(w)}
    padded = " " + " ".join(seq) + " "
    for t in tokens:
        t = build_systems.fold(t).strip()
        if not t:
            continue
        if " " in t:
            if f" {t} " in padded or f" {t.replace('al ', 'al')} " in padded:
                return True
        elif word_forms(t) & words:
            return True
    return False


def kinetic_country_policy(policy, r):
    return (policy or {}).get("kinetic") == "country" and r.get("cause") in build_systems.KINETIC_CAUSES


def date_problem(r):
    """A date converted from another calendar must be reproducible from what the source wrote."""
    cal = r.get("date_calendar") or "gregorian"
    if cal == "gregorian":
        year = int(str(r.get("date") or "0")[:4] or 0)
        if not calendars.GREGORIAN_PLAUSIBLE[0] <= year <= calendars.GREGORIAN_PLAUSIBLE[1]:
            return f"date {r.get('date')!r} is not a Gregorian date; state the calendar"
        return None
    if not r.get("source_date_text"):
        return f"a {cal} date with no source text to check it against"
    try:
        n = calendars.normalize_date(r["source_date_text"], cal)
    except ValueError as err:
        return f"date conversion failed: {err}"
    if n["normalized_date"] is None:
        return (f"{r['source_date_text']!r} is a {cal} month, which spans two Gregorian months "
                f"({n['gregorian_range'][0]} to {n['gregorian_range'][1]}); give a day or hold")
    if n["normalized_date"][:len(r["date"])] != r["date"] and not (
            cal == "hijri" and r.get("date_precision") == "day" and len(r["date"]) == 10
            and abs((calendars.dt.date.fromisoformat(n["normalized_date"])
                     - calendars.dt.date.fromisoformat(r["date"])).days) <= 1):
        return f"date {r['date']} does not match {r['source_date_text']!r} ({cal}), which is {n['normalized_date']}"
    return None


def review(system_id, r, unit_codes, grandfathered=frozenset(), policy=None, unplaceable=frozenset()):
    """None if the record passes, else the reason it is held."""
    if r.get("suggested_disposition") != "accept":
        return f"disposition {r.get('suggested_disposition')!r}"
    why = date_problem(r)
    if why:
        return why
    if policy:
        # Systems onboarded under the iteration-19 rules: a production decision, sanction, planned
        # maintenance or unexplained decline is not an event, and nothing nuclear below a national
        # total is recorded.
        why = build_systems.not_a_physical_event(r)
        if why:
            return why
        text = " ".join(str(r.get(k) or "") for k in ("summary", "effect", "threshold_basis", "facility_name"))
        if build_systems.NUCLEAR_DETAIL.search(text):
            return "a record at or about a nuclear site is not published"
        if any("in the record" in p for p in build_systems.route_problems([{**r, "event_id": "x", "sources": []}])):
            return "shipping, strait or route material is outside this product"
    never = set((policy or {}).get("no_event_units") or []) | set(unplaceable)
    for c in [r.get("admin1_code"), *(r.get("admin1_codes_affected") or [])]:
        if c in never:
            return f"{c} is drawn but never used for events"
    if r.get("cause") in build_systems.KINETIC_CAUSES and r.get("asset_class") in ((policy or {}).get("single_site_classes") or {}):
        # Country plus class names the site; no truthful parent class exists (iteration 20, §44).
        return "[SINGLE-SITE] the country has one site of this class, so the class names it"
    if kinetic_country_policy(policy, r):
        # The record will be published with no facility. Its text must not name one either.
        names = [n for n in (r.get("facility_name"), r.get("facility_name_local")) if n and len(n) >= 4]
        text = " ".join(str(r.get(k) or "") for k in ("summary", "effect", "threshold_basis", "hazard_name"))
        text = (text + " " + str((r.get("capacity_affected") or {}).get("source_says") or "")).lower()
        named = [n for n in names if n.lower() in text]
        if named:
            return "names the facility in its text under a country-level policy for kinetic events"
        # A record published without its facility must not be one click from it by reading its
        # own citation list: an address that spells the place out is not published, and a record
        # with no other citation waits for one.
        tokens = place_tokens(r, policy)
        if r.get("sources") and all(unpublishable_address(s.get("url"), tokens) for s in r["sources"]):
            return "its only citations name the facility or region, or the method, in their address"
        if build_systems.METHOD_WORDING.search(text):
            return "states how the attack was carried out"
    rec = r.get("recovery") or {}
    status = rec.get("research_status") or "NOT_YET_RESEARCHED"
    if status not in build_systems.RECOVERY_STATUSES:
        # Caught here, not by the build: a record that fails the build stops every system
        # (iteration 19: a lane wrote "RESEARCHED" and three reviews read past it).
        return f"recovery research status {status!r} is not in the vocabulary"
    if (status == "EVIDENCE_FOUND") != (rec.get("kind") is not None):
        return "a recovery kind and a status of EVIDENCE_FOUND go together"
    srcs = r.get("sources") or []
    if not srcs or not all(s.get("url") for s in srcs):
        return "a source has no URL"
    if srcs and all(s.get("opened") is False for s in srcs):
        return "no source was opened by the researcher"
    code = r.get("admin1_code")
    if code in OUT_OF_GEOGRAPHY.get(system_id, set()):
        return f"{code} is outside this system's geography this iteration"
    if kinetic_country_policy(policy, r) or (policy or {}).get("other") == "country":
        pass    # published at country level whatever the lane wrote; see to_event
    elif r.get("geography_precision") == "admin1" and code not in unit_codes:
        return f"region {code!r} is not a unit of this system"
    if r.get("geography_precision") not in ("admin1", "country"):
        return f"geography precision {r.get('geography_precision')!r}"
    for t in _texts(r):
        m = SCOPE_SCAN.search(t)
        if m:
            return f"scope scan hit {m.group(0)!r}: held for a person to read"
    cid = r.get("candidate_id") or ""
    if ids.full_slug(cid) != cid:
        return f"id {cid!r} is not a slug"
    # Checked last, so a record that fails on substance says so rather than "unreviewed".
    if r.get("candidate_id") not in grandfathered:
        primary, indep = r.get("primary_review") or {}, r.get("independent_review") or {}
        if not primary.get("completed"):
            return "no primary review"
        if not indep.get("completed"):
            return "no independent review: one researcher may discover, but publication needs a second look"
        if indep.get("disposition") not in PASSING_DISPOSITIONS:
            return f"independent review disposition {indep.get('disposition')!r}"
        if (indep.get("sources_opened") or 0) < 1:
            return "the independent reviewer opened no source"
        if indep.get("standard") == BLIND:
            roles = indep.get("roles") or {}
            failed = [k for k in BLIND_ROLES if roles.get(k) not in BLIND_PASS]
            if failed:
                return f"blind review: role(s) {failed} did not accept"
            # The confirmation round was procedure only: the gate never looked for it, so a text
            # changed after acceptance could be imported unconfirmed (iteration 19). Records of
            # earlier passes predate the field.
            m = re.match(r"iteration-(\d+)", r.get("research_pass") or "")
            if m and int(m.group(1)) >= 19:
                confirmed = indep.get("confirmed") or {}
                missing = [k for k in BLIND_ROLES if confirmed.get(k) != "confirm"]
                if missing:
                    return f"the final text was not confirmed by role(s) {missing}"
    return None


def apply_edits(r, edits):
    """Apply the reviewer edits for this record. Fails loudly if an edit no longer matches:
    a silently skipped edit would publish the text it was written to remove."""
    import copy
    r = copy.deepcopy(r)
    for e in edits:
        if e["event_id"] != r.get("candidate_id"):
            continue
        path = e["field"].split(".")
        holder = r
        for key in path[:-1]:
            holder = holder.setdefault(key, {})
        leaf = path[-1]
        if "set" in e:
            holder[leaf] = e["set"]
        else:
            old, new = e["replace"]
            text = holder.get(leaf) or ""
            if old not in text:
                raise SystemExit(f"review edit for {e['event_id']}.{e['field']} no longer matches: {old!r}")
            holder[leaf] = text.replace(old, new)
    return r


def _review_block(r, grandfathered):
    indep = r.get("independent_review") or {}
    legacy = r["candidate_id"] in grandfathered and not indep.get("completed")
    blind = not legacy and indep.get("standard") == BLIND
    block = {
        # A record from a later research pass carries its own date and process (iteration 15);
        # the iteration-14 lanes' records predate the fields and keep the defaults.
        "reviewed_at": (r.get("reviewed") or REVIEW_DATE) if legacy else indep["completed"],
        "threshold_version": "2026-10-30.1",
        "review_status": "legacy_single_review" if legacy else ("blind_reviewed" if blind else "dual_reviewed"),
        "primary_review_complete": True,
        "independent_review_complete": not legacy,
        "reviewer_count": 1 if legacy else (1 + len(BLIND_ROLES) if blind else 2),
        "disposition": None if legacy else indep["disposition"],
        "source_count": len(r["sources"]),
        "sources_opened_by_reviewer": None if legacy else indep.get("sources_opened"),
        "process": ((r.get("review_process") or DEFAULT_PROCESS) if legacy
                    else BLIND_PROCESS if blind else DUAL_PROCESS),
        "source_access": ("at least one source read" if any(s.get("opened") is True for s in r["sources"])
                          else "not recorded by the research lane"),
    }
    if blind:
        # Each role's verdict, never its rationale: the reasons stay in the local review files.
        block["roles"] = {k: indep["roles"][k] for k in BLIND_ROLES}
    return block


def _withheld_recovery():
    return {"research_status": build_systems.WITHHELD, "kind": None, "date": None,
            "evidence": None, "url": None}


def opaque_id(system_id, r):
    """An id that names no facility, stable for the life of the record: date, class and four hex
    digits of the queue id's hash."""
    # A lane that already wrote an opaque id keeps it, so reviews and edits refer to one name.
    if re.fullmatch(build_systems.OPAQUE_ID.format(cc=system_id), r["candidate_id"]):
        return r["candidate_id"]
    tag = hashlib.sha1(r["candidate_id"].encode("utf-8")).hexdigest()[:4]
    return f"{system_id}-{r['date']}-{r['asset_class'].replace('_', '-')}-attack-{tag}"


def _canonical(s):
    return {**s, "url": canonical_url(s["url"])}


# The script a headline in each language is written in. A placeholder such as "(headline not
# recorded)" stored as an Arabic title would render as English inside a right-to-left span.
TITLE_SCRIPT = {"ar": "؀-ۿ", "fa": "؀-ۿ", "ku": "؀-ۿ", "ckb": "؀-ۿ",
                "ur": "؀-ۿ", "zh": "一-鿿", "ru": "Ѐ-ӿ", "uk": "Ѐ-ӿ",
                "hi": "ऀ-ॿ"}


def title_matches_language(title, lang):
    """Whether most letters of an original-language headline are in that language's script."""
    rng = TITLE_SCRIPT.get((lang or "").lower())
    if not rng:
        return True
    letters = [c for c in title if c.isalpha()]
    if not letters:
        return False
    native = sum(1 for c in letters if re.match(f"[{rng}]", c))
    return native * 2 > len(letters)


def _source(s, with_titles):
    out = {k: s.get(k) for k in ("url", "publisher", "date", "language", "source_role", "opened")}
    # A non-English source keeps its own title and a gloss, where the headline is safe to show.
    if with_titles and (s.get("language") or "en") != "en":
        for k in ("title_original", "title_en"):
            t = s.get(k)
            if t and safe_title(t) and not build_systems.status_wording(t) and not build_systems.LOADED_WORDING.search(t):
                if k == "title_original" and not title_matches_language(t, s.get("language")):
                    continue
                out[k] = t
        # Both or neither: a headline whose gloss was refused (status or loaded wording) says the
        # same thing in its own language, where the wording rule reads less well.
        if not ("title_en" in out and "title_original" in out):
            out.pop("title_en", None)
            out.pop("title_original", None)
    return out


def to_event(system_id, r, grandfathered=frozenset(), campaigns=None, policy=None):
    abstract = kinetic_country_policy(policy, r)
    if abstract:
        tokens = place_tokens(r, policy)
        # Downgraded here, at the gate, so no later step has to remember to (iteration 19).
        r = {**r, "sources": [s for s in r["sources"] if not unpublishable_address(s.get("url"), tokens)],
             "geography_precision": "country", "admin1_code": None, "admin1_codes_affected": [],
             "facility_name": None, "facility_name_local": None, "operator": None,
             "published_id": opaque_id(system_id, r)}
    elif (policy or {}).get("other") == "country":
        # A system whose every record is the country's. The facility stays: this is not the attack rule.
        r = {**r, "geography_precision": "country", "admin1_code": None, "admin1_codes_affected": []}
    precise = r["geography_precision"] == "admin1"
    ev = {
        "event_id": r.get("published_id") or r["candidate_id"],
        "date": build_systems.canonical_date(r["date"], r.get("date_precision") or "day"),
        "date_precision": r.get("date_precision") or "day",
        "date_end": r.get("date_end"),
        "region_code": r["admin1_code"] if precise else None,
        "geography_precision": r["geography_precision"],
        # Multi-unit events stay at country precision. The affected units are listed for the
        # reader, never counted per unit: assigning a three-state blackout to one state would
        # be a guess, and to all three would triple-count it.
        "regions_affected": r.get("admin1_codes_affected") or [],
        "facility_name": r.get("facility_name"),
        "facility_name_local": r.get("facility_name_local"),
        "operator": r.get("operator"),
        "asset_class": r["asset_class"],
        "cause": r["cause"],
        "summary": r["summary"],
        "effect": r.get("effect"),
        "inclusion_basis": "reported_effect" if r.get("effect") else "occurrence",
        "criterion_met": r.get("threshold_clause"),
        "threshold_basis": r.get("threshold_basis"),
        "capacity_affected": build_systems.normalize_capacity(r.get("capacity_affected")),
        # Titles are the publishers' headlines, not our words, and the page shows the publisher
        # only; `opened` is null where the lane did not record whether it read the source.
        "sources": [_source(_canonical(s), with_titles=not abstract) for s in r["sources"]],
        "recovery": ({**r["recovery"], "url": canonical_url(r["recovery"].get("url"))} if r.get("recovery")
                     else {"research_status": "NOT_YET_RESEARCHED"}),
        "review": _review_block(r, grandfathered),
        "hazard_name": r.get("hazard_name"),
    }
    if (r.get("date_calendar") or "gregorian") != "gregorian":
        ev.update({"source_date_text": r["source_date_text"], "date_calendar": r["date_calendar"],
                   "conversion_basis": calendars.normalize_date(r["source_date_text"], r["date_calendar"])["conversion_basis"]})
    if policy:
        # A citation whose address carries shipping or route wording is not published (iteration
        # 19). If it was the only one the build refuses the record, which is the right outcome.
        ev["sources"] = [s for s in ev["sources"] if not build_systems.route_problems([{"event_id": "x", "sources": [s]}])]
        ev["review"]["source_count"] = len(ev["sources"])
        if ev["review"].get("sources_opened_by_reviewer") is not None:
            ev["review"]["sources_opened_by_reviewer"] = min(ev["review"]["sources_opened_by_reviewer"], len(ev["sources"]))
    # A date only where the page states one; a researcher's date is never overwritten. Applied
    # before the campaign filter so a citation found to be late is withheld like any other.
    for s in ev["sources"]:
        s["date"] = s.get("date") or PAGE_DATES.get(s["url"])
    # An active campaign's records ship with the withheld marker; the evidence stays in the queue.
    if campaigns and build_systems.campaign_of(ev, system_id, campaigns):
        ev["recovery"] = _withheld_recovery()
        # An end date on a struck facility's record says when its outage ended: status by another
        # name (iteration 17, test-architecture red team). It stays in the queue too.
        ev["date_end"] = None
        # A headline is where a publisher puts the status. Covered records show the publisher only.
        for s in ev["sources"]:
            s.pop("title_original", None)
            s.pop("title_en", None)
        # A citation whose address announces a restart ("…-delays-restart-to-august-30") publishes
        # that status in the source list, and a capacity note quoting a post-restart operating rate
        # publishes it in our words. Both stay in the queue with the rest of the status evidence,
        # so the release rule restores them without re-research (iteration 16, safety red team).
        ev["sources"] = [s for s in ev["sources"] if not build_systems.status_wording(s["url"])
                         and not build_systems.late_citation(ev, s)]
        ev["review"]["source_count"] = len(ev["sources"])
        # A reviewer-opened count above the published count would say a further source exists and
        # is not shown (iteration 18, Saudi safety audit).
        if ev["review"].get("sources_opened_by_reviewer") is not None:
            ev["review"]["sources_opened_by_reviewer"] = min(ev["review"]["sources_opened_by_reviewer"], len(ev["sources"]))
        cap = ev["capacity_affected"] or {}
        if build_systems.status_wording(cap.get("source_says")):
            ev["capacity_affected"] = None
    return ev


def run(system_id):
    queue = json.loads((ROOT / "data" / "candidates" / f"{system_id}.json").read_text(encoding="utf-8"))
    admin1, admin0 = build_systems.load_admin1(), build_systems.load_admin0()
    units = build_systems.units(system_id, admin1, admin0)
    unit_codes = {u[0] for u in units}
    edits = json.loads(EDITS.read_text(encoding="utf-8"))["edits"]
    known = {r.get("candidate_id") for r in queue}
    stray = sorted({e["event_id"] for e in edits if e["event_id"].startswith(system_id + "-")} - known)
    if stray:
        raise SystemExit(f"review edits name records not in the {system_id} queue: {stray}")
    queue = [apply_edits(r, edits) for r in queue]
    grandfathered = frozenset(json.loads(GRANDFATHERED.read_text(encoding="utf-8"))["event_ids"])
    campaigns = build_systems.load_campaigns()
    doc = json.loads((ROOT / "data" / "curated" / "systems" / system_id / "system.json").read_text(encoding="utf-8"))
    policy = doc["geography"].get("precision_policy")
    # A unit drawn for reference only (disputed, unassigned) never takes a record, whatever the
    # policy; the build refused it, the review did not (geography red team, iteration 20).
    # Passed apart from the policy: a policy switches on the iteration-19 rules, which China does not have.
    unplaceable = frozenset(x["code"] for x in doc["geography"].get("rulings", []) if x.get("status") == "disputed_unassigned")
    if policy:
        policy = {**policy, "unit_words": sorted(set(unit_words(build_systems.unit_name_rows(doc, units)))
                                                 | {build_systems.fold(w) for w in policy.get("region_words") or []})}
    accepted, held = [], []
    for r in queue:
        why = review(system_id, r, unit_codes, grandfathered, policy, unplaceable)
        if why is None:
            ev = to_event(system_id, r, grandfathered, campaigns, policy)
            if ev["sources"]:
                accepted.append(ev)
            else:
                held.append((r["candidate_id"], "active campaign: every citation reports facility "
                                                 "status, so none can be published"))
        elif r.get("suggested_disposition") == "accept":
            held.append((r["candidate_id"], why))
    out = ROOT / "data" / "curated" / "systems" / system_id / "events.json"
    # Bytes, so Windows does not turn every newline into CRLF (iteration 20).
    out.write_bytes((json.dumps({"system_id": system_id, "events": accepted},
                                ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(f"{system_id}: {len(accepted)} imported, {len(held)} lane-accepted records held")
    for cid, why in held:
        print(f"   held {cid}: {why}")


if __name__ == "__main__":
    for sid in sys.argv[1:]:
        if sid not in systems.COUNTRY_SYSTEMS:
            raise SystemExit(f"unknown country system {sid!r}")
        run(sid)
