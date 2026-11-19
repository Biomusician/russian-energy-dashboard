"""The global impact layer (iteration 22): load, gate, build.

    python -m pipeline.global_impacts --fixture     (frontend development only; see --help)

A second, separate, NON-SCORED corpus beside the country systems: reviewed, publicly reported
disruptions to energy and essential civilian services, at country or first-level-region precision
(docs/GLOBAL_IMPACT_METHODOLOGY.md, the contract this module implements).

WHAT IT WRITES (methodology §11), all under `global/`:
  * `impacts.json`              the records, newest event first, with their evidence confidence;
  * `regional_context.json`     dated, sourced, aggregate statements about the Gulf and Hormuz;
  * `evidence_confidence.json`  the confidence method as data, for the drawer and the glossary.

WHAT IT NEVER DOES. It computes no score and no count per country, orders nothing by a figure, and
is imported by no analytic module (a test holds that). It reads only `data/curated/global_impacts/`:
the candidate queue never reaches it; `scripts/import_impacts.py` is the one way in.

THE GATE (`record_problems`, `context_problems`, `log_problems`; methodology §13) refuses, naming
the record, anything the scope boundary forbids. What its wording rules can and cannot catch is
written beside each pattern. Nothing here detects personal data or an operator's name in free
text: those rest on the safety reviewer, and the gate does not pretend otherwise.
"""

import argparse
import copy
import datetime as dt
import math
import re
from pathlib import Path

from pipeline import build_systems as B
from pipeline import evidence_confidence as EC
from pipeline import outputs, systems
from pipeline.config import CURATED, METHODOLOGY_DIR, PROCESSED, ROOT, WEB_DATA
from pipeline.util import log, read_json, write_json

IMPACTS_CURATED = CURATED / "global_impacts"
EVENTS_FILE = IMPACTS_CURATED / "events.json"
CONTEXT_FILE = IMPACTS_CURATED / "regional_context.json"
LOG_FILE = IMPACTS_CURATED / "research_log.json"
# Optional: {"checked": date, "link_states": {url: state}} from an automated link check.
LINK_FILE = IMPACTS_CURATED / "link_health.json"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "impacts22"
TAXONOMY_PATH = METHODOLOGY_DIR / "impact_taxonomy.json"
TAXONOMY = read_json(TAXONOMY_PATH)

IMPACTS_OUT = "global/impacts.json"
CONTEXT_OUT = "global/regional_context.json"
METHOD_OUT = "global/evidence_confidence.json"
OUTPUTS = (IMPACTS_OUT, CONTEXT_OUT, METHOD_OUT)

SCHEMA_VERSION = 1
WINDOW_START = B.COVERAGE_START
CONTEXT_ID = "gulf_hormuz"
MULTI = "MULTI"
ATTEMPT = "attempt_no_service_impact"
ABSTRACTED = "country_abstracted"
# Causes that are attacks: published for the country only, everywhere (methodology §4).
ATTACK_FAMILIES = ("kinetic", "sabotage")
REVIEW_ROLES = tuple(r["id"] for r in TAXONOMY["review_roles"])
CONTEXT_REVIEW_ROLES = ("evidence", "safety")
CHECKS = ("passed", "not_applicable")


def ids(name):
    return tuple(x["id"] for x in TAXONOMY[name])


ABSENCE = ids("absence_words")
MALICIOUS = tuple(c["id"] for c in TAXONOMY["cause_families"] if c["malicious"] is True)
NOT_MALICIOUS = tuple(c["id"] for c in TAXONOMY["cause_families"] if c["malicious"] is False)
SECTOR_DOMAIN = {s["id"]: s["domain"] for s in TAXONOMY["sectors"]}
ROLE_RELATION = {r["id"]: r["relation"] for r in TAXONOMY["ai_roles"]}
SOLE_EVIDENCE_TIERS = tuple(t["id"] for t in TAXONOMY["social_tiers"] if t["may_be_sole_evidence"])

# The only fields a record, and each part of one, may carry. Anything else a lane wrote stays in
# the queue: an unknown key is refused, so a rationale, a rank or a position cannot ride along.
RECORD_FIELDS = (
    "impact_id", "record_kind", "date", "date_precision", "date_end", "country_a3", "countries_a3", "admin1",
    "geographic_precision", "domain", "sector", "technology", "cause_family", "contributing_factors",
    "cyber_mechanism", "summary", "effect", "effect_specificity", "inclusion_basis", "civilian_service_impact",
    "attribution", "ai_involvement", "dispute", "sources", "episode_id", "episode_basis", "publication_policy",
    "research_pass", "first_published", "last_revised", "review")
OPTIONAL_RECORD_FIELDS = ("countries_a3", "last_revised")
SOURCE_FIELDS = ("ref", "url", "publisher", "date", "language", "source_role", "medium", "social", "supports",
                 "opened", "title_original", "title_en", "derived_claim", "origin", "attribution_basis")
REQUIRED_SOURCE_FIELDS = ("ref", "url", "publisher", "date", "language", "source_role", "medium", "supports", "opened")
SOCIAL_FIELDS = ("platform", "handle", "display_name", "account_tier", "identity_basis", "posted_at")
IMPACT_FIELDS = ("service", "geographic_scope", "affected", "duration_text", "source_refs")
AFFECTED_FIELDS = ("value", "unit", "qualifier", "source_says")
ATTRIBUTION_FIELDS = ("status", "actor", "actor_type", "basis", "as_of", "statement", "competing", "source_refs")
COMPETING_FIELDS = ("actor", "actor_type", "basis", "statement", "source_refs")
AI_FIELDS = ("status", "relation", "role", "as_of", "statement", "source_refs")
DISPUTE_FIELDS = ("about", "statement", "source_refs")
REVIEW_FIELDS = ("reviewed_at", "review_status", "roles", "ai_check", "social_check", "disposition")
ENTRY_FIELDS = ("id", "date", "as_of", "context_type", "claim", "metric", "sources", "first_published",
                "last_revised", "review")
METRIC_FIELDS = ("value", "value_upper", "qualifier", "unit", "basis")
METRIC_QUALIFIERS = ("about", "at_least", "at_most", "range")
# The one mechanism a record that is not a cyberattack may carry (methodology §4).
IT_FAILURE_MECHANISM = "it_outage_affecting_operations"
LOG_FIELDS = ("window", "status", "source_families", "regions_worked", "limitations", "latest_research_date")
FAMILY_FIELDS = ("lane", "scope", "research_pass", "family", "method", "window", "status", "limitation")

# --- wording the gate refuses --------------------------------------------------------------------

# A key that names a position. Read by token ("is_latest_of_type" and "relation" are not "lat").
COORD_KEY_TOKENS = {"lat", "lon", "lng", "latitude", "longitude", "coord", "coords", "coordinate", "coordinates",
                    "geometry", "bbox", "centroid", "geojson", "point", "position", "xy", "geo", "location"}
# A position written into text or an address. Catches decimal pairs, degree notation (not a
# temperature), "lat"/"lon" labels and map links. It cannot catch a position spelled in words.
COORD_TEXT = re.compile("|".join([
    r"\d+(\.\d+)?\s*°(?!\s*[CF]\b)", r"\b\d{1,3}\.\d{3,}\s*°?\s*[NSEW]\b",
    r"-?\b\d{1,3}\.\d{3,}\s*[,;/ ]\s*-?\d{1,3}\.\d{3,}",
    r"\blat(itude)?\b\.?\s*[:=]?\s*-?\d", r"\b(lon|lng|longitude)\b\.?\s*[:=]?\s*-?\d", r"\blatitude\b", r"\blongitude\b",
    r"maps\.google|google\.[a-z.]+/maps|maps\.app\.goo\.gl|[?&]q=-?\d|/@-?\d+\.\d+,-?\d|openstreetmap\.org/[^ ]*#map|\bgeo:-?\d",
]), re.I)
_DECIMAL = re.compile(r"-?\d{1,3}\.\d{3,}")

IPV4 = re.compile(r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])")
IPV6 = re.compile(r"(?<![0-9a-f:])(?:[0-9a-f]{1,4}:){4,7}[0-9a-f]{1,4}(?![0-9a-f:])|"
                  r"(?<![0-9a-f:])(?:[0-9a-f]{1,4}:){1,6}:(?:[0-9a-f]{1,4}:){0,5}[0-9a-f]{1,4}(?![0-9a-f:])", re.I)
CVE = re.compile(r"\bCVE[-_ ]?\d{4}[-_ ]?\d{3,}\b", re.I)
# How access was gained, and the technical detail of a named victim (methodology §2). Conservative:
# a hit costs a reviewer one rewording. WHAT IT CATCHES: exploiting a vulnerability, zero-days,
# passwords and credentials, a numbered port, industrial and remote-access protocol names, firmware
# versions, a controller named with its maker, an "exposed ... model". WHAT IT CANNOT: a technique
# described in ordinary words ("staff were tricked into..."), an unlisted product or protocol, or a
# device identified by description. "Phishing" alone is not refused: the AI vocabulary has a role
# for generated deceptive messages, and the safety reviewer reads the sentence.
EXPLOIT_WORDING = re.compile("|".join([
    r"exploit\w*\s+(of\s+)?(a |an |the |known |unpatched |several |multiple )*(vulnerabilit|flaw|bug|weakness|zero)",
    r"zero[- ]day", r"\b(default|stolen|leaked|compromised|weak|hard-?coded|valid) (password|credential|login)s?\b",
    r"\bcredentials?\b", r"\bpasswords?\b", r"\bport \d+\b", r"\b(tcp|udp)[ /]\d+\b",
    r"\b(modbus|dnp3|iec[- ]?(60870|61850|104)|s7comm|bacnet|opc[- ]?ua|profinet|ethernet/ip|rdp|vnc|telnet|ssh|smb)\b",
    r"remote desktop", r"firmware (version|release|v?\d)", r"\bversion \d+\.\d+",
    r"\b(initial access|brute[- ]forc\w*|backdoor\w*|web ?shell|command[- ]and[- ]control|lateral movement|"
    r"privilege escalation|remote code execution)\b",
    r"(gain|gained|obtain|obtained|got) (initial |remote |unauthori[sz]ed )?access (via|through|by|using|with)",
    r"\b(unitronics|siemens|schneider|rockwell|allen[- ]bradley|omron|mitsubishi|honeywell|emerson|yokogawa|beckhoff|"
    r"wago)\b[^.]{0,40}\b(plc|hmi|rtu|controller)s?\b",
    r"\b(plc|hmi|rtu)s?\b[^.]{0,40}\b(unitronics|siemens|schneider|rockwell|allen[- ]bradley|omron|mitsubishi|honeywell|"
    r"emerson|yokogawa|beckhoff|wago)\b",
    r"exposed (controller|plc|hmi|rtu|device|system)s? model", r"\bmodel (number|no\.?) ",
    r"\bshodan\b", r"exposed[- ]device (list|inventor)", r"network (topology|diagram|map)",
]), re.I)

# Wording that says a service was NOT affected: an attempt filed as a disruption.
NO_IMPACT_WORDING = re.compile(
    r"\bno (reported |known |apparent )?(service |operational |customer )?(disruption|impact|interruption|outage|effect)\b|"
    r"\b(did|does|has|had|have) not (affect|disrupt|interrupt)\w*|\bwithout (any )?(disruption|interruption|impact|effect)\b|"
    r"\b(was|were) (thwarted|foiled|prevented|blocked|repelled)\b|\b(thwarted|foiled) (the |an )?(attack|attempt)\b|"
    r"\b(services?|operations?|supply|supplies) (was|were) (not|un)\s?(affected|disrupted|interrupted)\b", re.I)

# The regional context (methodology §10) may speak of shipping, the strait, transit, traffic,
# exports and cargoes IN AGGREGATE. It may never carry what follows. A vessel's NAME cannot be
# detected in general, so the gate refuses the signals around one: a ship prefix, an IMO or MMSI
# number, tracking, lists. Ports and terminals are an explicit list, kept deliberately broad for
# the Gulf; a port not on it, or a ship named without a prefix, rests on the safety reviewer.
CONTEXT_FORBIDDEN = re.compile("|".join([
    r"\bIMO\s*(number|no\.?|#)?\s*:?\s*\d{5,}", r"\bMMSI\b", r"\bAIS\b", r"(vessel|ship|tanker|marine|maritime)[- ]track\w*",
    r"\btrack(s|ed|ing|er|ers)?\b", r"\b(positions?|locations?) of (the |a |an )?(ship|vessel|tanker|carrier|fleet)s?\b",
    r"\b(whereabouts|anchored|anchorage|berth\w*)\b",
    r"\b(tanker|vessel|ship|carrier)s? (named|called|list)\b", r"\blist of (ships|vessels|tankers|carriers)\b",
    r"\b[a-z]+-flagged\b", r"\bflagged (vessel|ship|tanker|carrier)s?\b",
    r"\bbypass\w*", r"\balternat(e|ive) (export )?routes?\b", r"\bre-?rout\w*", r"\bdivert\w*", r"\bpipeline capacity\b",
    r"\bdepend(s|ed|ing|ent|ence|ency)? (up)?on\b", r"\bdependen(ce|cy|t)\b",
    r"\brel(y|ies|ied|iant|iance) (up)?on\b", r"choke ?points?", r"\bescort\w*", r"\bconvoys?\b", r"\bnaval\b", r"\bnavy\b",
    r"\bwarships?\b", r"\b(destroyer|frigate|corvette|submarine|patrol boat|fast boat|speedboat)s?\b",
    r"\b(sea |naval |limpet )?mines?\b", r"\bmine(d|laying|layer|sweep\w*)\b",
    r"\bvulnerab\w*", r"\bweak(est)? points?\b", r"\b(most|more) (exposed|important|critical)\b",
    r"\bgreatest (effect|impact)\b", r"\bsingle point of failure\b",
    r"\b(port|terminal|harbou?r) of\b",
    r"\b(ras tanura|ras al[- ]khair|ras markaz|kharg|khark|fujairah|jebel ali|bandar abbas|bandar imam|bandar[- ]e|"
    r"chabahar|mahshahr|mina al[- ]ahmadi|mina abdullah|mina al[- ]fahal|mina zayed|mina rashid|mina salman|ras laffan|"
    r"mesaieed|hamad port|khalifa port|khor al[- ]amaya|khor al[- ]zubair|basra(h)? (oil )?terminal|abot|umm qasr|"
    r"al[- ]faw|jubail|yanbu|ju'?aymah|dammam|sohar|duqm|salalah|sultan qaboos|das island|ruwais|zirku|jask|goreh|"
    r"assaluyeh|asaluyeh|lavan|sirri|khor fakkan|sitra|shuaiba|shuwaikh|al[- ]zour|hamriyah|halul|habshan|petroline|"
    r"east[- ]west pipeline|adcop)\b",
]), re.I)
# A ship's prefix before a capitalised name ("MT Example"). Case matters: "20 mt of" is a quantity.
CONTEXT_CASED = re.compile(r"\b(M/?[TV]|VLCC|ULCC|SS)\s+[A-Z][\w-]+")

# Held or rejected work never appears in a published research note (process facts only).
LOG_FORBIDDEN = re.compile(B.HELD_WORDING.pattern + r"|\breject\w*|\brefus\w*|\bnear[- ]miss\w*|\bduplicate\w*", re.I)

ID_STANDARD = re.compile(r"imp-(\d{4}(?:-\d{2}){0,2})-([a-z]{3,5})-([a-z-]+?)-([a-z0-9]+(?:-[a-z0-9]+)*)")
ADMIN1_CODE = re.compile(r"[A-Z]{2}-[A-Z0-9]{1,3}")
_ARTICLES = ("al", "ad", "an", "ar", "as", "ash", "at", "az", "el")


# --- small readers --------------------------------------------------------------------------------

def _date_ok(text, precisions=("day",)):
    """A real date of one of the given precisions."""
    if not isinstance(text, str):
        return False
    for p in precisions:
        if re.fullmatch(B.DATE_SHAPES[p], text):
            try:
                dt.date.fromisoformat((text + "-01-01")[:10])
                return True
            except ValueError:
                return False
    return False


def _start(text):
    return dt.date.fromisoformat((str(text) + "-01-01")[:10])


def _number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _walk(x, path=""):
    """(path, key-or-None, value) for every key and every leaf."""
    if isinstance(x, dict):
        for k, v in x.items():
            yield f"{path}.{k}" if path else k, k, v
            yield from _walk(v, f"{path}.{k}" if path else k)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield f"{path}[{i}]", None, v
            yield from _walk(v, f"{path}[{i}]")


def _strings(x):
    return [v for _, _, v in _walk(x) if isinstance(v, str)]


def _phrase_words(text):
    return re.findall(r"[^\W\d_]+", B.fold(str(text)))


def name_phrases(names, exclude=()):
    """Unit names as the folded phrases the text check looks for, with and without a leading
    article ("Al-Basrah" is also "Basrah"). `exclude` holds the country's own names: a governorate
    that shares its country's name must not refuse every sentence that names the country."""
    out = set()
    skip = {" ".join(_phrase_words(x)) for x in exclude}
    for n in names:
        w = _phrase_words(n)
        for seq in (w, w[1:] if w and w[0] in _ARTICLES else []):
            p = " ".join(seq)
            if len(p) >= 3 and p not in skip:
                out.add(p)
    return sorted(out)


def names_in(text, phrases):
    padded = " " + " ".join(_phrase_words(text)) + " "
    return sorted(p for p in phrases if f" {p} " in padded)


_ADMIN = {}


def system_unit_phrases(system_id):
    """Every name a first-level unit of a country system goes by, plus the system's own region
    words (a federal region, a coast), as folded phrases. The same rows the country import reads."""
    if "admin" not in _ADMIN:
        _ADMIN["admin"] = (B.load_admin1(), B.load_admin0())
    admin1, admin0 = _ADMIN["admin"]
    doc = read_json(B.SYSTEMS_CURATED / system_id / "system.json")
    rows = B.unit_name_rows(doc, B.units(system_id, admin1, admin0))
    words = [name for _, name in rows]
    words += ((doc.get("geography") or {}).get("precision_policy") or {}).get("region_words") or []
    s = systems.system(system_id)
    return name_phrases(words, exclude=(s["name"],) + tuple(s.get("aliases") or ()))


# --- context: what the gate and the builder need to know about the world -----------------------------

def load_context(world_path=None, unit_names=None, link_states=None):
    """Country names, which countries are monitored systems, which of those are under the campaign
    policy, and known link states. `unit_names` ({system_id: phrases}) is for tests that must not
    need the Natural Earth cache; left out, unit names are read on first use."""
    world = read_json(world_path or PROCESSED / "global" / "world.geojson")
    names = {}
    for f in world["features"]:
        p = f["properties"]
        # Crimea is drawn as its own feature carrying a3 UKR; the country's name is Ukraine's.
        if p.get("status") != "occupied" and p.get("a3") and p.get("name"):
            names.setdefault(p["a3"], p["name"])
    states = B.load_campaigns().get("system_states") or {}
    if link_states is None:
        link_states = {}
        for path in (B.LINK_HEALTH, LINK_FILE):
            if path.exists():
                link_states.update(read_json(path).get("link_states") or {})
    return {
        "names": names,
        "system_of": {a3: s["id"] for s in systems.SYSTEMS if s["kind"] == "country" for a3 in s["admin0_a3"]},
        "theatre_a3": frozenset(systems.system(systems.THEATRE)["admin0_a3"]),
        # The same classification the country systems use (build_systems.RESTRICTING_STATES).
        "restricted": frozenset(sid for sid in systems.COUNTRY_SYSTEMS
                                if (states.get(sid) or {}).get("state") in B.RESTRICTING_STATES),
        "unit_names": dict(unit_names or {}),
        "link_states": link_states,
    }


def _unit_phrases(ctx, system_id):
    if system_id not in ctx["unit_names"]:
        ctx["unit_names"][system_id] = system_unit_phrases(system_id)
    return ctx["unit_names"][system_id]


def _countries(r):
    return list(r.get("countries_a3") or []) if r.get("country_a3") == MULTI else [r.get("country_a3")]


def restricted_systems(r, ctx):
    """The campaign-restricted country systems this record falls in."""
    return sorted({ctx["system_of"][a3] for a3 in _countries(r)
                   if ctx["system_of"].get(a3) in ctx["restricted"]})


def digital_category(r):
    """"cyber" for a cyberattack (the cause family, or a contributing factor, is cyber), "it_failure"
    for a disruption digitally triggered without malice, else None. Two filters, never one: an IT
    failure counted under Cyber would turn a faulty update into an attack."""
    if r.get("cause_family") == "cyber" or "cyber" in (r.get("contributing_factors") or []):
        return "cyber"
    return "it_failure" if r.get("cyber_mechanism") == IT_FAILURE_MECHANISM else None


def is_attack(r):
    return r.get("cause_family") in ATTACK_FAMILIES or bool(set(r.get("contributing_factors") or []) & set(ATTACK_FAMILIES))


# --- the gate ---------------------------------------------------------------------------------------

def coordinate_problems(x):
    """Coordinate-like keys, number pairs and position text, anywhere in `x`."""
    out = []
    if isinstance(x, dict):
        floats = [v for v in x.values() if isinstance(v, float) and not v.is_integer() and abs(v) <= 180
                  and _DECIMAL.fullmatch(repr(v))]
        if len(floats) >= 2:
            out.append("two decimal numbers side by side read as a position")
    for path, key, v in _walk(x):
        if key is not None and set(re.split(r"[^a-z]+", key.lower())) & COORD_KEY_TOKENS:
            out.append(f"coordinate-like key {path}")
        if isinstance(v, dict):
            floats = [n for n in v.values() if isinstance(n, float) and not n.is_integer() and abs(n) <= 180
                      and _DECIMAL.fullmatch(repr(n))]
            if len(floats) >= 2:
                out.append(f"{path}: two decimal numbers side by side read as a position")
        if isinstance(v, list) and 2 <= len(v) <= 3:
            if all(_number(n) for n in v) and any(isinstance(n, float) and not n.is_integer() for n in v) \
                    and abs(v[0]) <= 180 and abs(v[1]) <= 180:
                out.append(f"{path}: a pair of numbers that reads as a position")
            if all(isinstance(n, str) and _DECIMAL.fullmatch(n.strip()) for n in v):
                out.append(f"{path}: a pair of numbers that reads as a position")
        if isinstance(v, str) and COORD_TEXT.search(v):
            out.append(f"{path}: coordinate or map-link text")
    return out


def technical_problems(x):
    """IP addresses and CVE identifiers in any string (addresses included); exploit wording in
    prose and headlines. An address is read for the first two only: "/port-2024-outage" is a
    harbour, not a network port."""
    out = []
    for path, key, v in _walk(x):
        if not isinstance(v, str):
            continue
        if IPV4.search(v) or IPV6.search(v):
            out.append(f"{path}: an IP address")
        if CVE.search(v):
            out.append(f"{path}: a CVE identifier")
        if key != "url" and EXPLOIT_WORDING.search(v):
            out.append(f"{path}: exploit or access-method wording ({EXPLOIT_WORDING.search(v).group(0)!r})")
    return out


def _unknown_keys(obj, allowed, where):
    return [f"{where}: field {k!r} is not part of the contract" for k in sorted(set(obj) - set(allowed))]


def _absent_or(value, allowed):
    """None (not applicable), an absence word, or a member of `allowed`."""
    return value is None or value in ABSENCE or value in allowed


def source_problems(sources, claims=EC.CLAIMS):
    """Each citation: complete, in vocabulary, and honest about what it is."""
    out = []
    if not isinstance(sources, list) or not sources:
        return ["no source"]
    refs = [s.get("ref") for s in sources if isinstance(s, dict)]
    if len(set(refs)) != len(refs):
        out.append("two sources share a ref")
    for s in sources:
        if not isinstance(s, dict):
            out.append("a source is not an object")
            continue
        w = f"source {s.get('ref')!r}"
        out += _unknown_keys(s, SOURCE_FIELDS, w)
        for k in REQUIRED_SOURCE_FIELDS:
            if k not in s or s[k] in (None, "", []) and k != "opened":
                out.append(f"{w}: no {k}")
        if not re.match(r"https?://[^\s/]+\.[^\s/]+", str(s.get("url") or "")):
            out.append(f"{w}: the address is not a public web address")
        if not _date_ok(s.get("date"), ("day", "month", "year")):
            out.append(f"{w}: date {s.get('date')!r} is not a date")
        if s.get("source_role") not in ids("source_roles"):
            out.append(f"{w}: source_role {s.get('source_role')!r} is not in the vocabulary")
        if s.get("medium") not in ids("media"):
            out.append(f"{w}: medium {s.get('medium')!r} is not in the vocabulary")
        supports = s.get("supports")
        if not isinstance(supports, list) or not supports or set(supports) - set(claims):
            out.append(f"{w}: supports {supports!r} must name at least one of {tuple(claims)}")
        if not isinstance(s.get("opened"), bool):
            out.append(f"{w}: opened must be true or false, as the evidence reviewer found it")
        if s.get("attribution_basis") is not None and s["attribution_basis"] not in EC.ATTRIBUTION_BASES:
            out.append(f"{w}: attribution_basis {s['attribution_basis']!r} is not in the vocabulary")
        social = s.get("social")
        if s.get("medium") == "social":
            if not isinstance(social, dict):
                out.append(f"{w}: a social post needs its account (social)")
            else:
                out += _unknown_keys(social, SOCIAL_FIELDS, w + " social")
                if social.get("account_tier") not in ids("social_tiers"):
                    out.append(f"{w}: a social post needs an account tier, one of {ids('social_tiers')}")
                if not str(social.get("identity_basis") or "").strip():
                    out.append(f"{w}: a social post needs identity_basis; a platform badge is not identity")
                for k in ("platform", "handle"):
                    if not social.get(k):
                        out.append(f"{w}: a social post needs its {k}")
        elif social is not None:
            out.append(f"{w}: social is set on a source whose medium is not social")
    return out


def _weak_for_occurrence(s):
    """A source that can never be the sole evidence that something happened."""
    if s.get("source_role") == "actor_self_claim":
        return True
    return s.get("medium") == "social" and (s.get("social") or {}).get("account_tier") not in SOLE_EVIDENCE_TIERS


def claim_problems(r):
    """Claim-level provenance: no claim without a supporting source (methodology §9)."""
    out = []
    sources = [s for s in r.get("sources") or [] if isinstance(s, dict)]
    by_ref = {s.get("ref"): s for s in sources}

    def backing(claim):
        return [s for s in sources if claim in (s.get("supports") or [])]

    occurrence = backing("occurrence")
    if not occurrence:
        out.append("no source supports occurrence")
    elif all(_weak_for_occurrence(s) for s in occurrence):
        out.append("the only evidence of occurrence is an unverified or unofficial social post or an actor's own claim")
    if r.get("effect_specificity") in ("quantified", "described") and not backing("effect"):
        out.append(f"the effect is {r.get('effect_specificity')} but no source supports effect")
    if r.get("record_kind") == ATTEMPT and not any(EC.tier_of(s) == "direct" for s in occurrence):
        out.append("an attempt needs an official or operator statement that supports occurrence")

    def refs(where, listed, claim):
        if not isinstance(listed, list):
            return [f"{where}: source_refs must be a list"]
        bad = [x for x in listed if x not in by_ref]
        got = [f"{where}: source_refs {bad} name no source"] if bad else []
        got += [f"{where}: source {x!r} is cited for {claim} but does not support it"
                for x in listed if x in by_ref and claim not in (by_ref[x].get("supports") or [])]
        return got

    for i, c in enumerate(r.get("civilian_service_impact") or []):
        if isinstance(c, dict):
            if not c.get("source_refs"):
                out.append(f"civilian_service_impact[{i}]: no source")
            out += refs(f"civilian_service_impact[{i}]", c.get("source_refs") or [], "effect")
    a = r.get("attribution") or {}
    out += refs("attribution", a.get("source_refs") or [], "attribution")
    for i, c in enumerate(a.get("competing") or []):
        if isinstance(c, dict):
            if not c.get("source_refs"):
                out.append(f"attribution.competing[{i}]: no source")
            out += refs(f"attribution.competing[{i}]", c.get("source_refs") or [], "attribution")
    ai = r.get("ai_involvement") or {}
    out += refs("ai_involvement", ai.get("source_refs") or [], "ai_involvement")
    d = r.get("dispute")
    if isinstance(d, dict):
        if not d.get("source_refs"):
            out.append("dispute: no source")
        out += [f"dispute: source_refs {[x for x in d.get('source_refs') or [] if x not in by_ref]} name no source"] \
            if any(x not in by_ref for x in d.get("source_refs") or []) else []
    out += EC.attribution_problems(r.get("attribution"), sources)
    out += EC.ai_problems(r.get("ai_involvement"), sources)
    return out


def vocabulary_problems(r):
    """Every enumerated field holds a member of its vocabulary; null and the absence words mean
    what methodology §4 says they mean; an absence is never a zero or an empty string."""
    out = []
    for path, _, v in _walk(r):
        if v == "":
            out.append(f"{path}: an empty string; an absence is null or one of {ABSENCE}")
    if r.get("record_kind") not in ids("record_kinds"):
        out.append(f"record_kind {r.get('record_kind')!r}")
    if r.get("date_precision") not in ids("date_precision"):
        out.append(f"date_precision {r.get('date_precision')!r}")
    elif not _date_ok(r.get("date"), (r["date_precision"],)):
        out.append(f"date {r.get('date')!r} is not a {r['date_precision']}-precision date")
    elif not WINDOW_START <= (r["date"] + "-01-01")[:10]:
        out.append(f"date {r['date']} is before the corpus window ({WINDOW_START})")
    end = r.get("date_end")
    if end is not None and end not in ABSENCE and not _date_ok(end, ("day", "month", "year")):
        out.append(f"date_end {end!r} is not a date, null or an absence word")
    elif _date_ok(end, ("day", "month", "year")) and _date_ok(r.get("date"), ("day", "month", "year")) and end < r["date"][:len(end)]:
        out.append("date_end is before date")
    if r.get("geographic_precision") not in ids("geographic_precision"):
        out.append(f"geographic_precision {r.get('geographic_precision')!r}")
    if r.get("domain") not in ids("domains"):
        out.append(f"domain {r.get('domain')!r}")
    if r.get("sector") not in SECTOR_DOMAIN:
        out.append(f"sector {r.get('sector')!r} is not in the vocabulary")
    elif SECTOR_DOMAIN[r["sector"]] != r.get("domain"):
        out.append(f"sector {r['sector']} belongs to the {SECTOR_DOMAIN[r['sector']]} domain")
    tech = r.get("technology")
    if r.get("domain") == "energy":
        if tech is None or not _absent_or(tech, ids("technologies")):
            out.append(f"technology {tech!r}: an energy record names a technology or says why not ({ABSENCE})")
    elif tech is not None:
        out.append("technology is null (not applicable) outside energy")
    if r.get("cause_family") not in ids("cause_families"):
        out.append(f"cause_family {r.get('cause_family')!r}")
    factors = r.get("contributing_factors")
    if not isinstance(factors, list) or set(factors) - set(ids("cause_families")) or r.get("cause_family") in (factors or []):
        out.append(f"contributing_factors {factors!r} must be a list of other cause families")
    cyber = r.get("cause_family") == "cyber" or "cyber" in (factors if isinstance(factors, list) else [])
    mech = r.get("cyber_mechanism")
    if cyber and (mech is None or not _absent_or(mech, ids("cyber_mechanisms"))):
        out.append(f"cyber_mechanism {mech!r}: a cyber record names a broad mechanism or says it is not reported")
    if not cyber and mech is not None:
        # One exception (methodology §4): a disruption digitally triggered WITHOUT malice, such as a
        # faulty software update. It is a technical failure, never a cyberattack, and nobody is
        # attributed.
        if mech != IT_FAILURE_MECHANISM or r.get("cause_family") != "industrial_technical":
            out.append(f"cyber_mechanism is null (not applicable) when no cause is cyber; the one exception is "
                       f"{IT_FAILURE_MECHANISM} on an industrial_technical record")
        elif (r.get("attribution") or {}).get("status") != "NOT_APPLICABLE":
            out.append("an IT failure is not a malicious act: its attribution is NOT_APPLICABLE")
    for k in ("summary",):
        if not isinstance(r.get(k), str) or not r[k].strip():
            out.append(f"no {k}")
    if r.get("publication_policy") not in ids("publication_policies"):
        out.append(f"publication_policy {r.get('publication_policy')!r}")
    if not isinstance(r.get("research_pass"), str) or not re.fullmatch(r"i\d+-[a-z0-9_]+", r.get("research_pass") or ""):
        out.append(f"research_pass {r.get('research_pass')!r}")

    attempt = r.get("record_kind") == ATTEMPT
    spec, basis = r.get("effect_specificity"), r.get("inclusion_basis")
    if attempt:
        # An attempt met no inclusion basis and had no effect: both are not applicable, not vague.
        if basis is not None or spec is not None or r.get("civilian_service_impact") or r.get("effect") is not None:
            out.append("an attempt has no effect, no service impact and no inclusion basis (all null)")
    else:
        if spec not in EC.EFFECT_SPECIFICITY:
            out.append(f"effect_specificity {spec!r} is not one of {EC.EFFECT_SPECIFICITY}")
        if isinstance(basis, bool) or basis not in ids("inclusion_bases"):
            out.append(f"inclusion_basis {basis!r} is not one of {ids('inclusion_bases')}")
        if not isinstance(r.get("effect"), str) or not r["effect"].strip():
            out.append("a disruption states its effect")
        if NO_IMPACT_WORDING.search(f"{r.get('summary') or ''} {r.get('effect') or ''}"):
            out.append("the text says no service was affected: an attempt is filed as a disruption")

    impacts = r.get("civilian_service_impact")
    if not isinstance(impacts, list):
        out.append("civilian_service_impact must be a list")
        impacts = []
    quantified = False
    for i, c in enumerate(impacts):
        w = f"civilian_service_impact[{i}]"
        if not isinstance(c, dict):
            out.append(f"{w} is not an object")
            continue
        out += _unknown_keys(c, IMPACT_FIELDS, w)
        if c.get("service") not in SECTOR_DOMAIN:
            out.append(f"{w}: service {c.get('service')!r} is not a sector")
        if not _absent_or(c.get("geographic_scope"), ids("geographic_scopes")) or c.get("geographic_scope") is None:
            out.append(f"{w}: geographic_scope {c.get('geographic_scope')!r}")
        if c.get("duration_text") is not None and not isinstance(c["duration_text"], str):
            out.append(f"{w}: duration_text is text, null or an absence word")
        aff = c.get("affected")
        if aff is None or aff in ABSENCE:
            continue
        if not isinstance(aff, dict):
            out.append(f"{w}: affected is an object, null or an absence word")
            continue
        out += _unknown_keys(aff, AFFECTED_FIELDS, w + ".affected")
        value = aff.get("value")
        if value is not None:
            if not _number(value) or not math.isfinite(value) or value <= 0:
                out.append(f"{w}: affected.value {value!r}: an absence is null, never zero; a figure is a positive number")
            if not isinstance(aff.get("unit"), str) or not aff["unit"].strip():
                out.append(f"{w}: a value without a unit")
            if not isinstance(aff.get("source_says"), str) or not aff["source_says"].strip():
                out.append(f"{w}: a value without the source's own words (source_says)")
            if aff.get("qualifier") not in ids("affected_qualifiers"):
                out.append(f"{w}: qualifier {aff.get('qualifier')!r} is not one of {ids('affected_qualifiers')}")
            quantified = True
        elif aff.get("unit") is not None or aff.get("qualifier") is not None:
            out.append(f"{w}: a unit or qualifier with no value")
    if quantified and spec != "quantified":
        out.append("a figure is given for the effect but effect_specificity is not quantified")

    a = r.get("attribution")
    if not isinstance(a, dict):
        out.append("no attribution block (UNKNOWN and NOT_APPLICABLE are normal, and are stated)")
    else:
        out += _unknown_keys(a, ATTRIBUTION_FIELDS, "attribution")
        status = a.get("status")
        if r.get("cause_family") in MALICIOUS and status == "NOT_APPLICABLE":
            out.append("attribution is NOT_APPLICABLE on a malicious act; nobody credibly attributing it is UNKNOWN")
        if (r.get("cause_family") in NOT_MALICIOUS and not set(factors or []) & set(MALICIOUS)
                and status not in (None, "NOT_APPLICABLE")):
            out.append(f"attribution is {status} on a record that is not a malicious act")
        if a.get("as_of") is not None and not _date_ok(a["as_of"], ("day", "month", "year")):
            out.append(f"attribution.as_of {a['as_of']!r} is not a date")
        if not isinstance(a.get("basis", []), list) or not isinstance(a.get("competing", []), list):
            out.append("attribution.basis and attribution.competing are lists")
        else:
            for i, c in enumerate(a.get("competing") or []):
                if not isinstance(c, dict) or not c.get("actor") or not c.get("statement"):
                    out.append(f"attribution.competing[{i}] needs an actor and a statement")
                else:
                    out += _unknown_keys(c, COMPETING_FIELDS, f"attribution.competing[{i}]")
        if status not in (None, "NOT_APPLICABLE", "UNKNOWN") and not str(a.get("statement") or "").strip():
            out.append("an attribution needs a statement of who attributes it to whom")
    ai = r.get("ai_involvement")
    if not isinstance(ai, dict):
        out.append("no ai_involvement block (NONE_REPORTED is normal, and is stated)")
    else:
        out += _unknown_keys(ai, AI_FIELDS, "ai_involvement")
        want = ROLE_RELATION.get(ai.get("role"))
        if ai.get("status") != "NONE_REPORTED" and want and ai.get("relation") != want:
            out.append(f"ai_involvement role {ai.get('role')} belongs to {want}: assistance and operational cause are never merged")
        if ai.get("as_of") is not None and not _date_ok(ai["as_of"], ("day", "month", "year")):
            out.append(f"ai_involvement.as_of {ai['as_of']!r} is not a date")
        if ai.get("status") not in (None, "NONE_REPORTED") and not str(ai.get("statement") or "").strip():
            out.append("an AI-involvement finding needs a statement of what the source says")
    d = r.get("dispute")
    if d is not None:
        if not isinstance(d, dict) or d.get("about") not in ids("dispute_about") or not str(d.get("statement") or "").strip():
            out.append(f"dispute needs about (one of {ids('dispute_about')}) and a statement, or is null")
        else:
            out += _unknown_keys(d, DISPUTE_FIELDS, "dispute")
    return out


def geography_problems(r, ctx):
    """Country, precision and the first-level-region rules (methodology §4)."""
    out = []
    a3, precision, admin1 = r.get("country_a3"), r.get("geographic_precision"), r.get("admin1")
    if a3 == MULTI:
        listed = r.get("countries_a3")
        if precision != "multi_country" or not isinstance(listed, list) or len(set(listed)) < 2 or len(set(listed)) != len(listed):
            out.append("MULTI needs geographic_precision multi_country and a countries_a3 list of two or more")
        else:
            out += [f"countries_a3: {x!r} is not a country on the world map" for x in listed if x not in ctx["names"]]
    else:
        if a3 not in ctx["names"]:
            out.append(f"country_a3 {a3!r} is not a country on the world map")
        if precision == "multi_country" or "countries_a3" in r:
            out.append("multi_country precision and countries_a3 belong to a MULTI record")
    if admin1 is None:
        if precision == "admin1":
            out.append("admin1 precision with no admin1")
    else:
        if (not isinstance(admin1, dict) or set(admin1) != {"code", "name"}
                or not ADMIN1_CODE.fullmatch(str(admin1.get("code"))) or not str(admin1.get("name") or "").strip()):
            out.append("admin1 is null or {code, name} for a first-level region")
        if precision != "admin1":
            out.append("admin1 is set but geographic_precision is not admin1")
        if is_attack(r):
            out.append("a kinetic or sabotage record never carries a region (admin1)")
    return out


def identity_problems(r):
    """The id's form, and the dates the record carries about itself."""
    out = []
    iid = str(r.get("impact_id") or "")
    a3 = str(r.get("country_a3") or "").lower()
    sector = str(r.get("sector") or "").replace("_", "-")
    prefix = f"imp-{r.get('date')}-{a3}-{sector}-"
    if not ID_STANDARD.fullmatch(iid) or not iid.startswith(prefix) or len(iid) > 110:
        out.append(f"impact_id must be imp-<date>-<a3>-<sector>-<slug> (expected to start {prefix!r})")
    if not _date_ok(r.get("first_published")):
        out.append(f"first_published {r.get('first_published')!r} is not a date; the import stamps it")
    if "last_revised" in r and (not _date_ok(r["last_revised"]) or (_date_ok(r.get("first_published"))
                                                                    and r["last_revised"] < r["first_published"])):
        out.append("last_revised is a date on or after first_published")
    if r.get("episode_id") is not None and (not re.fullmatch(r"ep-[a-z0-9]+(-[a-z0-9]+)*", str(r["episode_id"]))
                                            or not str(r.get("episode_basis") or "").strip()):
        out.append("episode_id is null or an ep-<slug> with an episode_basis")
    if r.get("episode_id") is None and r.get("episode_basis") is not None:
        out.append("episode_basis without an episode_id")
    return out


def review_problems(r, roles=REVIEW_ROLES, full=True):
    """No record imports itself: every blind role accepted the text that is published."""
    v = r.get("review")
    if not isinstance(v, dict):
        return ["no review block"]
    out = _unknown_keys(v, REVIEW_FIELDS if full else ("reviewed_at", "roles"), "review")
    if not _date_ok(v.get("reviewed_at")):
        out.append("review.reviewed_at is not a date")
    got = v.get("roles") if isinstance(v.get("roles"), dict) else {}
    for role in roles:
        if got.get(role) not in B.BLIND_PASS:
            out.append(f"review role {role} did not accept ({got.get(role)!r})")
    if set(got) - set(roles):
        out.append(f"review roles {sorted(set(got) - set(roles))} are not roles of this review")
    if full:
        if v.get("review_status") != "blind_reviewed":
            out.append("review_status must be blind_reviewed")
        if v.get("disposition") not in B.REVIEW_DISPOSITIONS:
            out.append(f"review disposition {v.get('disposition')!r}")
        ai_needed = (r.get("ai_involvement") or {}).get("status") not in (None, "NONE_REPORTED")
        social_needed = any(isinstance(s, dict) and s.get("medium") == "social" for s in r.get("sources") or [])
        for key, needed in (("ai_check", ai_needed), ("social_check", social_needed)):
            if v.get(key) not in CHECKS or (needed and v.get(key) != "passed"):
                out.append(f"review.{key} is {v.get(key)!r}; it must be passed where it applies, else not_applicable")
    return out


def _prose(r):
    """Our own words and the words we keep from sources: everything but addresses, ids and headlines."""
    parts = [r.get("summary"), r.get("effect"), r.get("episode_basis")]
    for c in r.get("civilian_service_impact") or []:
        if isinstance(c, dict):
            parts.append(c.get("duration_text"))
            if isinstance(c.get("affected"), dict):
                parts += [c["affected"].get("source_says"), c["affected"].get("unit")]
    a = r.get("attribution") if isinstance(r.get("attribution"), dict) else {}
    parts += [a.get("statement"), a.get("actor")]
    for c in a.get("competing") or []:
        if isinstance(c, dict):
            parts += [c.get("statement"), c.get("actor")]
    ai = r.get("ai_involvement") if isinstance(r.get("ai_involvement"), dict) else {}
    parts.append(ai.get("statement"))
    if isinstance(r.get("dispute"), dict):
        parts.append(r["dispute"].get("statement"))
    for s in r.get("sources") or []:
        if isinstance(s, dict):
            parts.append(s.get("derived_claim"))
    return " \n ".join(str(p) for p in parts if isinstance(p, str))


def _sources(r):
    return [s for s in r.get("sources") or [] if isinstance(s, dict)]


def _titles(r):
    return " \n ".join(str(s.get(k)) for s in _sources(r) for k in ("title_original", "title_en") if s.get(k))


def _addresses(r):
    return [str(s.get("url") or "") for s in _sources(r)]


def _id_words(r):
    return " ".join(str(r.get(k) or "").replace("-", " ") for k in ("impact_id", "episode_id"))


def wording_problems(r):
    """Route, method and loaded wording (methodology §2, §4)."""
    out = []
    prose, titles = _prose(r), _titles(r)
    words = " ".join(B.address_words(u) for u in _addresses(r))
    hit = B.ROUTE_WORDING.search(" \n ".join([prose, titles, _id_words(r), words]))
    if hit:
        out.append(f"shipping, strait or route wording ({hit.group(0)!r}); it belongs to the regional context only")
    hit = B.METHOD_WORDING.search(prose)
    if hit:
        out.append(f"the text states how an attack was carried out ({hit.group(0)!r})")
    hit = B.LOADED_WORDING.search(f"{r.get('summary') or ''} \n {r.get('effect') or ''}")
    if hit:
        out.append(f"size or importance wording in the summary or effect ({hit.group(0)!r})")
    return out


def abstraction_problems(r, ctx):
    """An attack is the country's: no region, headline, method, later status, or place in an address."""
    out = []
    attack, policy = is_attack(r), r.get("publication_policy")
    if attack and policy != ABSTRACTED:
        out.append("a kinetic or sabotage record must be country_abstracted")
    if policy != ABSTRACTED:
        return out
    if not attack:
        out.append("country_abstracted is the attack rule; this record's cause is not kinetic or sabotage")
    if r.get("geographic_precision") != "country" or r.get("admin1") is not None:
        out.append("an abstracted record is published for the country only")
    iid = str(r.get("impact_id") or "")
    stem = f"imp-{r.get('date')}-{str(r.get('country_a3') or '').lower()}-{str(r.get('sector') or '').replace('_', '-')}-attack-"
    if not iid.startswith(stem) or not re.fullmatch(B.OPAQUE_TOKEN, iid[len(stem):]):
        out.append("an abstracted record's id is imp-<date>-<a3>-<sector>-attack-<six hex digits of the import's keyed hash>")
    if r.get("episode_id") is not None:
        out.append("an abstracted record is its own episode: a declared episode's name is not gated")
    if r.get("date_end") is not None:
        out.append("an abstracted record carries no end date: when service came back is later status")
    for s in _sources(r):
        if s.get("title_original") or s.get("title_en"):
            out.append(f"source {s.get('ref')!r}: a headline on a record published without its place")
        url = str(s.get("url") or "")
        if B.method_in_address(url):
            out.append(f"source {s.get('ref')!r}: the citation address states how the attack was carried out")
        path = re.sub(r"^https?://[^/]+", "", url)
        if B.status_wording(B.address_words(path)):
            out.append(f"source {s.get('ref')!r}: the citation address carries status wording")
    hit = B.status_wording(_prose(r))
    if hit:
        out.append(f"status wording on an abstracted record ({hit.group(0)!r})")
    return out


def campaign_problems(r, ctx):
    """ANY record in a system under the campaign policy: no region, no headline, and no name of
    one of that system's regions in its text, its id or (for an attack) a citation address."""
    out = []
    for sid in restricted_systems(r, ctx):
        if r.get("admin1") is not None or r.get("geographic_precision") == "admin1":
            out.append(f"a record in a campaign-restricted system ({sid}) carries a region")
        if _titles(r):
            out.append(f"a record in a campaign-restricted system ({sid}) carries a headline")
        phrases = _unit_phrases(ctx, sid)
        found = names_in(" \n ".join([_prose(r), _id_words(r)] + [str(s.get("publisher") or "") for s in _sources(r)]), phrases)
        if found:
            out.append(f"the text or id names a region of a campaign-restricted system ({sid}): {found}")
        if is_attack(r):
            for s in _sources(r):
                path = re.sub(r"^https?://", "", str(s.get("url") or ""))
                if names_in(B.address_words(path), phrases):
                    out.append(f"source {s.get('ref')!r}: the citation address names a region of {sid}")
    return out


def one_record_problems(r, ctx):
    if not isinstance(r, dict):
        return ["not an object"]
    out = _unknown_keys(r, RECORD_FIELDS, "record")
    out += [f"no {k}" for k in RECORD_FIELDS if k not in r and k not in OPTIONAL_RECORD_FIELDS]
    out += coordinate_problems(r)
    out += technical_problems(r)
    out += vocabulary_problems(r)
    out += geography_problems(r, ctx)
    out += identity_problems(r)
    out += source_problems(r.get("sources"))
    out += claim_problems(r)
    out += wording_problems(r)
    out += abstraction_problems(r, ctx)
    out += campaign_problems(r, ctx)
    out += review_problems(r)
    return out


def record_problems(records, ctx):
    """Why these records cannot be published: [] or one line per problem, naming the record."""
    out = []
    seen = set()
    for i, r in enumerate(records):
        rid = r.get("impact_id") if isinstance(r, dict) else None
        name = rid or f"record #{i}"
        if rid in seen:
            out.append(f"{name}: duplicate impact_id")
        seen.add(rid)
        out += [f"{name}: {p}" for p in one_record_problems(r, ctx)]
    return out


def context_problems(entries):
    """The regional context: dated, as-of, sourced, reviewed, aggregate. No vessel, route, port,
    dependence or status flag (methodology §10)."""
    out = []
    seen = set()
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            out.append(f"context entry #{i}: not an object")
            continue
        name = e.get("id") or f"context entry #{i}"
        p = _unknown_keys(e, ENTRY_FIELDS, "entry")
        p += [f"no {k}" for k in ENTRY_FIELDS if k not in e and k != "last_revised"]
        if e.get("id") in seen:
            p.append("duplicate id")
        seen.add(e.get("id"))
        if not re.fullmatch(r"ctx-\d{4}-\d{2}-\d{2}-[a-z0-9]+(-[a-z0-9]+)*", str(e.get("id") or "")) \
                or not str(e.get("id")).startswith(f"ctx-{e.get('date')}-"):
            p.append("id must be ctx-<date>-<slug>")
        for k in ("date", "as_of", "first_published"):
            if not _date_ok(e.get(k)):
                p.append(f"{k} {e.get(k)!r} is not a date: every statement is dated and says as of when")
        if _date_ok(e.get("date")) and _date_ok(e.get("as_of")) and e["as_of"] < e["date"]:
            p.append("as_of is before date")
        if _date_ok(e.get("date")) and e["date"] < WINDOW_START:
            p.append(f"date is before the corpus window ({WINDOW_START})")
        if e.get("context_type") not in ids("context_types"):
            p.append(f"context_type {e.get('context_type')!r} is not in the vocabulary")
        if not isinstance(e.get("claim"), str) or not e["claim"].strip():
            p.append("no claim")
        m = e.get("metric")
        if m is not None:
            if not isinstance(m, dict):
                p.append("metric is an object or null")
            else:
                p += _unknown_keys(m, METRIC_FIELDS, "metric")
                if not _number(m.get("value")) or not math.isfinite(m["value"]):
                    p.append("metric.value is a number; a statement with no figure has metric null")
                if not isinstance(m.get("unit"), str) or not m["unit"].strip():
                    p.append("a metric value without a unit")
                if not isinstance(m.get("basis"), str) or not m["basis"].strip():
                    p.append("a metric without its basis (what the figure measures, in the source's words)")
                if m.get("qualifier") is not None and m["qualifier"] not in METRIC_QUALIFIERS:
                    p.append(f"metric.qualifier {m['qualifier']!r} is not one of {METRIC_QUALIFIERS}")
                upper = m.get("value_upper")
                if (m.get("qualifier") == "range") != (upper is not None):
                    p.append("metric.value_upper is given for a range, and only for a range")
                elif upper is not None and (not _number(upper) or not math.isfinite(upper)
                                            or not _number(m.get("value")) or upper <= m["value"]):
                    p.append("metric.value_upper is a number above metric.value")
        p += source_problems(e.get("sources"), claims=("occurrence",))
        p += review_problems(e, roles=CONTEXT_REVIEW_ROLES, full=False)
        p += coordinate_problems(e)
        p += technical_problems(e)
        text = " \n ".join(s for s in _strings({k: v for k, v in e.items() if k != "sources"}))
        for s in e.get("sources") or []:
            if isinstance(s, dict):
                text += " \n " + " \n ".join(str(s.get(k) or "") for k in ("derived_claim", "title_original", "title_en", "publisher"))
                text += " \n " + B.address_words(re.sub(r"^https?://[^/]+", "", str(s.get("url") or "")))
        hit = CONTEXT_CASED.search(text) or CONTEXT_FORBIDDEN.search(text)
        if hit:
            p.append(f"vessel, route, port, dependence or naval wording ({hit.group(0)!r}); the context is aggregate only")
        hit = B.METHOD_WORDING.search(text)
        if hit:
            p.append(f"weapon or method wording ({hit.group(0)!r})")
        out += [f"{name}: {x}" for x in p]
    return out


def log_problems(research_log):
    """A research note publishes process facts only: families, method, window, status, limitation."""
    out = _unknown_keys(research_log, LOG_FIELDS, "research log")
    out += [f"research log: no {k}" for k in LOG_FIELDS if k not in research_log]
    for i, f in enumerate(research_log.get("source_families") or []):
        w = f"research log family #{i}"
        if not isinstance(f, dict):
            out.append(f"{w}: not an object")
            continue
        out += _unknown_keys(f, FAMILY_FIELDS, w)
        if f.get("scope") not in ("impacts", "regional_context"):
            out.append(f"{w}: scope must be impacts or regional_context")
        if not f.get("family"):
            out.append(f"{w}: no family")
        # The Hormuz lane's notes are served with the regional context, under its wording rule.
        text = " \n ".join(_strings(f))
        if f.get("scope") != "regional_context" and B.ROUTE_WORDING.search(text):
            out.append(f"{w}: shipping or route wording in an impact research note")
        if f.get("scope") == "regional_context" and (CONTEXT_CASED.search(text) or CONTEXT_FORBIDDEN.search(text)):
            out.append(f"{w}: vessel, route, port or dependence wording")
    for path, _, v in _walk(research_log):
        if isinstance(v, str) and LOG_FORBIDDEN.search(v):
            out.append(f"research log {path}: speaks of held, rejected or candidate work ({LOG_FORBIDDEN.search(v).group(0)!r})")
    latest = research_log.get("latest_research_date")
    if latest is not None and not _date_ok(latest):
        out.append("research log: latest_research_date is a date or null")
    out += [f"research log: {p}" for p in coordinate_problems(research_log) + technical_problems(research_log)]
    return out


def gate(events_doc, context_doc, research_log, ctx):
    """Every reason this corpus cannot be built. [] means it can."""
    out = []
    if events_doc.get("schema_version") != SCHEMA_VERSION or not isinstance(events_doc.get("records"), list):
        return [f"events.json must be {{schema_version: {SCHEMA_VERSION}, records: [...]}}"]
    if context_doc.get("context_id") != CONTEXT_ID or not isinstance(context_doc.get("entries"), list):
        return [f"regional_context.json must be {{context_id: {CONTEXT_ID!r}, entries: [...]}}"]
    out += record_problems(events_doc["records"], ctx)
    out += context_problems(context_doc["entries"])
    out += log_problems(research_log)
    return out


def link_problems(link_states, events_doc, context_doc):
    """A link state may speak only of a citation that is published (the country systems' rule): a
    record withdrawn after the check would otherwise leave its address in a committed file."""
    published = {s.get("url") for r in events_doc["records"] for s in _sources(r)}
    published |= {s.get("url") for e in context_doc["entries"] for s in (e.get("sources") or []) if isinstance(s, dict)}
    out = [f"link_health: {url} is not a citation of any published record"
           for url in sorted(set(link_states) - published)]
    out += [f"link_health: {url} has state {state!r}" for url, state in sorted(link_states.items())
            if state not in ids("link_states")]
    return out


# --- build ------------------------------------------------------------------------------------------

SCOPE_STATEMENT = (
    "Reviewed, publicly reported disruptions to energy systems and essential civilian services, at country or "
    "first-level-region precision, from 2022 to the present. Each record says what service was affected, what kind "
    "of cause is reported, who is publicly said to be responsible and how firmly, and how strong the public evidence is.")
CAVEATS = (
    "This is not a census. Disclosure laws differ, operators may not disclose, conflicts distort reporting and media "
    "ecosystems differ from country to country.",
    "A count here is a number of published records in this corpus. It is never a rate, and counts are never compared "
    "or ranked across countries.",
    "Nothing here is scored. No record enters any index, any country system's event count or any research assessment.",
    "A country that appears only here is not a monitored system: no index, no research-maturity claim, and no implied "
    "complete record for that country.",
    "An attack or sabotage record is published for the country only, with no place, operator, method, headline or "
    "later status.",
    "Evidence confidence describes the quality of the public evidence. It is not a probability, not severity and not "
    "a statement about how important any infrastructure is.",
)
EMPTY_REASON = ("No reviewed record has been published yet. That is the state of the review, not a finding that "
                "nothing happened.")
ORDER = ("Records: by event date, newest first, then by id. Countries: alphabetical by name. Nothing is ordered "
         "or ranked by a figure.")
FIELD_NOTES = {
    "system_id": "The monitored country system this country belongs to, else null. Appearing here does not make a "
                 "country a monitored system.",
    "theatre": "Present and true where the country is part of the Russia, Belarus and Crimea theatre. The record is "
               "not a theatre record and enters no index.",
    "digital_category": "cyber for a cyberattack (the cause family or a contributing factor is cyber); it_failure for "
                        "a disruption digitally triggered without malice, such as a faulty software update; else "
                        "null. Two separate filters: an IT failure is never counted as cyber.",
    "origin_count": "Distinct originating statements among the record's citations. A wire story and its copies are "
                    "one; discovery aids are none. Not a count of links.",
    "first_published": "The build date on which this record was first served. Not the event date and not a source date.",
    "link_check": "The citation's state at the last automated link check, or unchecked. A failed link says nothing "
                  "about the record.",
    "attempts": "Documented attempts with no reported service disruption. Listed apart and never counted with disruptions.",
    "null": TAXONOMY["null_means"],
}
VOCABULARIES = ("domains", "sectors", "technologies", "cause_families", "cyber_mechanisms", "digital_categories",
                "source_roles", "media",
                "social_tiers", "claims", "attribution_statuses", "actor_types", "attribution_bases", "ai_statuses",
                "ai_relations", "ai_roles", "record_kinds", "absence_words", "inclusion_bases", "effect_specificity",
                "geographic_precision", "geographic_scopes", "date_precision", "affected_qualifiers",
                "publication_policies", "link_states", "review_roles", "dispute_about")
CONTEXT_STATEMENT = (
    "Dated, sourced statements about the Gulf and the Strait of Hormuz, in aggregate: shipping, trade, supply, "
    "markets, reserves, policy and broad civilian and environmental effects. Each statement is as of its own date.")
CONTEXT_NOT_BUILT = (
    "There is no open or closed flag and no current status: only what a named source said, and when. Nothing here "
    "identifies a ship, a port, a facility or a path, and nothing here enters an index, a count or a country's "
    "record. A market movement is never presented as infrastructure loss.")
CONTEXT_ORDER = "By statement date, newest first, then by id."
LATEST_NOTE = ("is_latest_of_type marks the newest statement of its type by its as-of date. It is the most recent "
               "statement on record, shown as of that date, and older ones are historical. It is not a current status.")


def _place(a3, ctx):
    out = {"a3": a3, "name": ctx["names"][a3], "system_id": ctx["system_of"].get(a3)}
    if a3 in ctx["theatre_a3"]:
        out["theatre"] = True
    return out


def _link_check(source, ctx):
    state = ctx["link_states"].get(source.get("url"))
    return state if state in ids("link_states") else "unchecked"


def serve_record(r, ctx):
    """A curated record as it is served: the contract's fields plus what the build derives."""
    out = {k: copy.deepcopy(r[k]) for k in RECORD_FIELDS if k in r}
    if r["country_a3"] == MULTI:
        places = sorted((_place(a3, ctx) for a3 in r["countries_a3"]), key=lambda p: (p["name"], p["a3"]))
        out["country_name"] = "Several countries"
        out["system_id"] = None
        out["countries"] = places
    else:
        place = _place(r["country_a3"], ctx)
        out["country_name"] = place["name"]
        out["system_id"] = place["system_id"]
        if place.get("theatre"):
            out["theatre"] = True
    end = r.get("date_end") if _date_ok(r.get("date_end"), ("day", "month", "year")) else None
    out["evidence_confidence"] = EC.assess(r["sources"], r["date"], end, r.get("effect_specificity") or "vague",
                                           r.get("dispute"))
    out["attribution"]["confidence"] = EC.attribution_confidence(r["attribution"], r["sources"])
    out["origin_count"] = len({EC.origin_of(s) for s in r["sources"]} - {None})
    out["digital_category"] = digital_category(r)
    for s in out["sources"]:
        s["link_check"] = _link_check(s, ctx)
    return out


def _newest_first(rows, key="date", id_key="impact_id"):
    # Two stable sorts: by id, then by date descending, so equal dates stay in id order.
    return sorted(sorted(rows, key=lambda r: r[id_key]), key=lambda r: _start(r[key]), reverse=True)


def _labels(names):
    return {n: TAXONOMY[n] for n in names}


def _research(research_log, scope):
    families = [{k: f.get(k) for k in FAMILY_FIELDS if k != "scope"}
                for f in research_log.get("source_families") or [] if f.get("scope") == scope]
    families.sort(key=lambda f: (str(f.get("lane")), str(f.get("family")), str(f.get("method"))))
    out = {"window": research_log.get("window"), "status": research_log.get("status"), "source_families": families,
           "latest_research_date": research_log.get("latest_research_date")}
    if scope == "impacts":
        out["regions_worked"] = sorted(research_log.get("regions_worked") or [])
        out["limitations"] = list(research_log.get("limitations") or [])
    return out


def build_impacts(events_doc, research_log, ctx, as_of):
    known = [r for r in events_doc["records"] if (r["date"] + "-01-01")[:10] <= as_of]
    served = _newest_first([serve_record(r, ctx) for r in known])
    records = [r for r in served if r["record_kind"] != ATTEMPT]
    attempts = [r for r in served if r["record_kind"] == ATTEMPT]
    a3s = {a3 for r in known for a3 in _countries(r)}
    return {
        "schema_version": SCHEMA_VERSION,
        "as_of": as_of,
        "scope_statement": SCOPE_STATEMENT,
        "caveats": list(CAVEATS),
        "order": ORDER,
        "field_notes": FIELD_NOTES,
        "empty_reason": None if served else EMPTY_REASON,
        "attempts_label": next(k["label"] for k in TAXONOMY["record_kinds"] if k["id"] == ATTEMPT),
        "vocabularies": _labels(VOCABULARIES),
        "research": _research(research_log, "impacts"),
        # Which countries have a record, by name. No figure per country: a list ordered or sized by
        # a count reads as a league table, which the methodology forbids.
        "countries": sorted((_place(a3, ctx) for a3 in a3s), key=lambda p: (p["name"], p["a3"])),
        "records": records,
        "attempts": attempts,
    }


def build_context(context_doc, research_log, ctx, as_of):
    today = dt.date.fromisoformat(as_of)
    known = [e for e in context_doc["entries"] if e["date"] <= as_of]
    newest = {}
    for e in known:
        newest[e["context_type"]] = max(newest.get(e["context_type"], ""), e["as_of"])
    entries = []
    for e in _newest_first(known, id_key="id"):
        out = {k: copy.deepcopy(e[k]) for k in ENTRY_FIELDS if k in e}
        # How old the statement is, for the reader to judge. Never a shelf life and never "current".
        out["age_days"] = (today - dt.date.fromisoformat(e["as_of"])).days
        out["is_latest_of_type"] = e["as_of"] == newest[e["context_type"]]
        for s in out["sources"]:
            s["link_check"] = _link_check(s, ctx)
        entries.append(out)
    return {
        "schema_version": SCHEMA_VERSION,
        "as_of": as_of,
        "context_id": CONTEXT_ID,
        "label": context_doc.get("label") or "The Gulf and the Strait of Hormuz",
        "statement": CONTEXT_STATEMENT,
        "not_built": CONTEXT_NOT_BUILT,
        "order": CONTEXT_ORDER,
        "latest_note": LATEST_NOTE,
        "empty_reason": None if entries else "No reviewed statement has been published yet.",
        "context_types": TAXONOMY["context_types"],
        "vocabularies": _labels(("source_roles", "media", "link_states", "affected_qualifiers")),
        "research": _research(research_log, "regional_context"),
        "entries": entries,
    }


def build_method():
    """The confidence method as served data, plus the labels the drawer needs beside it."""
    out = EC.method()
    out["scope_of_use"] = ("Shown on impact records and on the country systems' published events. It is not the "
                           "Russia theatre's scoring confidence, which is unchanged, and it enters no index.")
    out["labels"] = _labels(("claims", "source_roles", "media", "social_tiers", "effect_specificity",
                             "attribution_statuses", "actor_types", "attribution_bases", "ai_statuses", "ai_relations",
                             "ai_roles", "link_states", "absence_words", "dispute_about"))
    out["null_means"] = TAXONOMY["null_means"]
    return out


def build_payloads(events_doc, context_doc, research_log, ctx, as_of):
    """{output name: payload}, or ValueError naming every record the gate refuses."""
    problems = gate(events_doc, context_doc, research_log, ctx)
    if problems:
        raise ValueError("global impacts: " + "; ".join(problems))
    return {
        IMPACTS_OUT: build_impacts(events_doc, research_log, ctx, as_of),
        CONTEXT_OUT: build_context(context_doc, research_log, ctx, as_of),
        METHOD_OUT: build_method(),
    }


def load_curated(directory=IMPACTS_CURATED):
    return (read_json(directory / "events.json"), read_json(directory / "regional_context.json"),
            read_json(directory / "research_log.json"))


def write_payloads(payloads, root):
    for name, payload in payloads.items():
        write_json(root / name, payload)


def build(as_of):
    """Build the three artifacts into the current build's output root. Called by pipeline.run after
    the country systems, whose world map supplies the country names."""
    ctx = load_context(outputs.processed() / "global" / "world.geojson")
    docs = load_curated()
    if LINK_FILE.exists():
        problems = link_problems(read_json(LINK_FILE).get("link_states") or {}, docs[0], docs[1])
        if problems:
            raise ValueError("global impacts: " + "; ".join(problems))
    payloads = build_payloads(*docs, ctx, as_of)
    write_payloads(payloads, outputs.processed())
    log(f"global impacts: {len(payloads[IMPACTS_OUT]['records'])} records, "
        f"{len(payloads[IMPACTS_OUT]['attempts'])} attempts, {len(payloads[CONTEXT_OUT]['entries'])} context entries")
    return payloads


def main():
    ap = argparse.ArgumentParser(
        description="Build the global impact artifacts from the SYNTHETIC fixture in tests/fixtures/impacts22, "
                    "for frontend development only. The real build is `python -m pipeline.run`.")
    ap.add_argument("--fixture", action="store_true", required=True,
                    help="write the three artifacts, built from synthetic records, into web/public/data/global/. "
                         "DEVELOPMENT ONLY: the output is invented data. Never commit it; restore with "
                         "`git checkout -- web/public/data` (or rebuild) before committing.")
    ap.add_argument("--as-of", default=dt.date.today().isoformat(), help="build date (default: today)")
    ap.add_argument("--out", default=str(WEB_DATA), help="directory that holds global/ (default: web/public/data)")
    args = ap.parse_args()
    ctx = load_context(link_states=read_json(FIXTURE_DIR / "link_health.json")["link_states"])
    payloads = build_payloads(*load_curated(FIXTURE_DIR), ctx, args.as_of)
    write_payloads(payloads, Path(args.out))
    for name in payloads:
        log(f"fixture: wrote {Path(args.out) / name}")
    log("fixture: SYNTHETIC records for frontend development. Do not commit web/public/data/global/"
        "{impacts,regional_context,evidence_confidence}.json built this way.")


if __name__ == "__main__":
    main()
