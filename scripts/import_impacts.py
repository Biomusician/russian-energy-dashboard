"""Move reviewed impact candidates into the curated global impact corpus (iteration 22).

    .venv\\Scripts\\python.exe scripts\\import_impacts.py [--date 2026-11-20] [--dry-run]

`data/candidates/impacts22/<lane>/candidates.json` (and a lane's `context_entries.json`) is a
research queue. Nothing in it is published. This script is the one gate between the queue and
`data/curated/global_impacts/`: the build never reads the queue (pipeline/global_impacts.py).

WHAT IT DOES, in order (docs/GLOBAL_IMPACT_METHODOLOGY.md §12; REVIEW_FORMAT.md in the queue):
  1. Reads every lane's candidates and the reviewer files `reviews/<role>/<lane>.json`.
  2. A candidate no reviewer file mentions is left alone. One a role has not reviewed, or rejected
     (a "duplicate of ..." is an ordinary reject), is refused.
  3. Applies the reviewers' patches: evidence, then attribution and source, then safety, so safety
     wins. `opened` is whatever the EVIDENCE reviewer opened, never what the lane wrote. A reviewer
     may rename a candidate (`set: {"impact_id": ...}`); verdicts stay keyed by the original id.
     Then, only on a record every role accepted, the LEAD's normalisation (`reviews/lead/<lane>.json`,
     the same format; `accept_with_correction`, `set` and `remove_sources` only): mechanical
     rewrites of a spelling or a wording into the contract's. It changes no verdict, cannot weaken
     the publication policy, give a record a region, mark a source opened or change the cause of an
     attack, and the published review block says it was made and when.
  4. Every kinetic or sabotage record becomes country-abstracted: no region, no headline, no end
     date, and an id minted from a keyed hash (the country import's key; never printed).
  5. Dedupes across lanes: same country and sector, dates within a day. The one the reviewers
     accepted is kept; if they accepted more than one, all are refused for the lead to resolve.
  6. Reconciles with the country queues: a candidate in a monitored system that matches, by date
     and sector, a record of that system's own queue that is NOT published there is refused. The
     stricter policy wins: an event held from a country system does not appear here because this
     layer has a different schema, WHATEVER the hold was for, an inclusion threshold included.
     There is no override. `reconcile_distinct.json` is something else: the lead's statement, with
     a mandatory reason, that a date-and-class match is a DIFFERENT EVENT (a false match). It lifts
     no hold, and an attack record can never use it. `reconcile_allow.json` is no longer read.
  7. Runs the build's own gate on each record as it will be published, and refuses what it refuses.
  8. Stamps `first_published` on records new to the curated file. An existing record keeps its
     date; one whose content changed also gets `last_revised`. Running twice changes nothing.
  9. Rewrites the published research note from each lane's `lane_log.json`: process facts only.

ALSO:
  - A lane is any folder of the queue holding `candidates.json` or `context_entries.json`; nothing
    else is a lane. Everything is keyed `<lane>/<original id>` until final ids exist, so two lanes
    filing under one id are two candidates.
  - `lead_holds.json` (`{"holds": {"<lane>/<id>": reason}}`) refuses each held candidate with the
    lead's reason. The research note then carries NUMBERS only: how many are held and on which of
    three grounds, never a reason, a lane or an id.
  - The run FAILS and writes nothing if two imported records end with the same final id. Two
    imported records sharing country and sector within three days are a printed WARNING, not a
    refusal; `distinct_events.json` (`[["<lane>/<id>", "<lane>/<id>"], ...]`) records that a pair
    is two events.
  - `social/addenda.json` adds a reviewed social source to a record that is imported; its verdicts
    are keyed `<impact_id>#<ref>` in `reviews/<role>/social.json`. Where the lead holds a record as
    a "duplicate of <lane>/<id>", its accepted addenda go to that surviving record.
  - `--dry-run` reads everything, prints per-lane imported and refused counts with every refusal
    reason, and writes nothing: not the curated files, not the report.

The report is printed and written to `<queue>/import_report.json`, which is local and never
committed: it names candidates, old ids and the country queues' hold reasons.
"""

import argparse
import copy
import datetime as dt
import hashlib
import hmac
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline import build_systems as B  # noqa: E402
from pipeline import global_impacts as G  # noqa: E402
from pipeline import systems  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "data" / "candidates" / "impacts22"
COUNTRY_QUEUES = ROOT / "data" / "candidates"
ROLE_ORDER = ("evidence", "attribution_source", "safety")      # the order patches apply: safety last
CONTEXT_ROLES = G.CONTEXT_REVIEW_ROLES
# The lead's normalisation pass: read after the blind roles, never one of them.
LEAD = "lead"
# The roles that must each accept a social addendum (reviews/<role>/social.json) before it is added.
# Two, not three: an addendum is a source for a record whose occurrence and effect the evidence role
# already reviewed, so what remains to check is the social check (identity, tier, origin, what the
# post itself states; both reviewers open the post) and safety.
ADDENDA_ROLES = ("attribution_source", "safety")
LEAD_KEYS = ("verdict", "set", "remove_sources", "reason", "note")
PASS = B.BLIND_PASS
VERDICTS = PASS + ("reject",)
# Where a lane worked, for the published research note. A thematic lane names no region.
LANE_REGIONS = {"africa_latam": ["Africa", "Latin America and the Caribbean"], "asia": ["Asia"], "europe": ["Europe"],
                "na": ["North America"], "oceania": ["Oceania"], "mideast": ["Middle East"],
                "iran_cyber": ["Iran"], "iran_power": ["Iran"], "eurasia": ["Eurasia"],
                "gulf_states": ["Gulf states"], "gulf_civil": ["Gulf states"]}
# Words lanes use for a figure's qualifier, as the vocabulary writes them.
QUALIFIER_WORDS = {"over": "at_least", "more than": "at_least", "at least": "at_least", "minimum": "at_least",
                   "above": "at_least", "roughly": "about", "approximately": "about", "approx": "about",
                   "around": "about", "nearly": "about", "almost": "about", "some": "about", "estimated": "about",
                   "up to": "at_most", "as many as": "at_most", "at most": "at_most", "maximum": "at_most",
                   "less than": "at_most", "under": "at_most", "fewer than": "at_most", "near": "about",
                   "exactly": "exact", "between": "range"}
SCOPE_WORDS = {"subnational": "regional", "multi-region": "multi_region", "multiregion": "multi_region",
               "nationwide": "national", "countrywide": "national"}

# How a country system's own queue describes why a record is not published there. Read from the
# queue record's process fields, for the lead's local report ONLY: the kind of hold decides
# nothing, because a match with a held record is refused whatever it was held for.
#
# WHAT EACH PATTERN READS: the reason a researcher, reviewer or the lead wrote (disposition_reason,
# lead_hold, a review's reason or note). Never the names of the review roles, one of which is
# "safety". A word that only MENTIONS safety ("not an attack", "the campaign rule does not apply")
# reads as a safety hold: the report errs towards the graver kind.
SAFETY_HOLD = re.compile(
    r"safety|campaign|withh[eo]ld|abstract|coordinat|facility[- ]level|status|vulnerab|target|kinetic|attack|"
    r"strike|sabotage|drone|missile|nuclear|export[- ]route|shipping|strait|red team|\[D-\d+\]|out of scope|"
    r"dependen", re.I)
EVIDENCE_HOLD = re.compile(
    r"insufficient evidence|unverified|unsourced|uncorroborated|unconfirmed|not corroborat|single[- ]source|"
    r"could not (be )?(open|verif|confirm)\w*|inaccessible|no (public|primary|domestic) (source|page)|rumou?r|"
    r"not opened|unopened|dead link|paywall|rests only on|evidence (is |was )?(incomplete|thin|partial|partly)|"
    r"only source", re.I)
THRESHOLD_HOLD = re.compile(
    r"threshold|inclusion clause|strict reading|\bclause \d|\[C\d-[A-Z]+\]|customer (count|figure)|consumer count|"
    r"no stated size|does not meet|not met|too small|below", re.I)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, obj):
    # Bytes, so Windows does not turn every newline into CRLF.
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes((json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


# --- reading the queue ------------------------------------------------------------------------------

def lane_dirs(queue):
    """Every lane directory, found by looking, first and second pass alike ("na", "na2"). A lane is
    a directory that has filed candidates or context entries: `reviews` is not one, and neither is
    a folder that holds only notes, addenda or a scratchpad."""
    return sorted(p for p in Path(queue).iterdir() if p.is_dir() and p.name != "reviews"
                  and ((p / "candidates.json").exists() or (p / "context_entries.json").exists()))


def load_holds(queue):
    """The lead's holds: {"<lane>/<original id>": reason}. A bare id (the first form of the file)
    holds that id in every lane."""
    path = Path(queue) / "lead_holds.json"
    if not path.exists():
        return {}
    doc = read_json(path)
    holds = doc.get("holds") if isinstance(doc.get("holds"), dict) else doc
    return {k: str(v) for k, v in holds.items() if not k.startswith("_")}


def hold_ground(reason):
    """Which of the three counted grounds a lead hold falls under. Counted, never published as text."""
    if re.search(r"duplicate|same (id|incident|event|record)|filed (twice|by two)", reason, re.I):
        return "duplicates_across_lanes"
    if re.search(r"safety|campaign|abstract|precision|status|address|link|names? |ties |rule|scope|place|facility|"
                 r"operator|attack|strike|method|route|cable|sea ", reason, re.I):
        return "safety_grounds"
    return "other_grounds"


def _rows(path, keys):
    """A lane file as a list of records. A lane that has not written the file yet has none; side
    files this script does not know (near_misses.json, date_fixes.json, ...) are never opened."""
    if not path.exists():
        return []
    doc = read_json(path)
    if isinstance(doc, dict):
        doc = next((doc[k] for k in keys if isinstance(doc.get(k), list)), [])
    return [r for r in doc if isinstance(r, dict)] if isinstance(doc, list) else []


def load_reviews(queue):
    """{role: {lane: file}} for every reviewer file present."""
    out = {}
    base = Path(queue) / "reviews"
    for role in ROLE_ORDER + (LEAD,):
        out[role] = {}
        if (base / role).is_dir():
            for path in sorted((base / role).glob("*.json")):
                doc = read_json(path)
                if isinstance(doc, dict) and isinstance(doc.get("verdicts"), dict):
                    out[role][path.stem] = doc
    return out


def verdicts_for(reviews, lane, cid, roles):
    """({role: verdict}, reviewed_at) for the roles that reviewed this candidate in its lane."""
    got, dates = {}, []
    for role in roles:
        doc = reviews.get(role, {}).get(lane)
        if doc and isinstance(doc["verdicts"].get(cid), dict):
            got[role] = doc["verdicts"][cid]
            dates.append(str(doc.get("reviewed_at") or ""))
    return got, max(dates) if dates else None


# --- applying a review -----------------------------------------------------------------------------

_TOKEN = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(?:\[([^\]]+)\])?")


def set_path(obj, path, value):
    """Set `path` in `obj`. Dotted keys; `sources[<ref>]` addresses a source by its ref; any other
    `name[n]` is a list index. Raises ValueError where the path does not exist to be corrected."""
    parts = path.split(".")
    cur = obj
    for i, part in enumerate(parts):
        m = _TOKEN.fullmatch(part)
        if not m:
            raise ValueError(f"path {path!r} is not understood")
        name, index = m.group(1), m.group(2)
        last = i == len(parts) - 1
        if index is None:
            if last:
                cur[name] = value
                return
            if not isinstance(cur.get(name), dict):
                cur[name] = {}
            cur = cur[name]
            continue
        seq = cur.get(name)
        if not isinstance(seq, list):
            raise ValueError(f"path {path!r}: {name} is not a list")
        pos = None
        if name == "sources":
            pos = next((n for n, s in enumerate(seq) if isinstance(s, dict) and s.get("ref") == index), None)
        if pos is None and index.isdigit() and int(index) < len(seq):
            pos = int(index)
        if pos is None:
            raise ValueError(f"path {path!r}: no {name}[{index}]")
        if last:
            seq[pos] = value
            return
        cur = seq[pos]


def apply_reviews(record, verdicts, roles=ROLE_ORDER):
    """The record with every role's corrections applied in role order. Returns (record, problems)."""
    r = copy.deepcopy(record)
    problems = []
    removed = set()
    for role in roles:
        v = verdicts.get(role) or {}
        for path, value in (v.get("set") or {}).items():
            # A correction to a source an earlier role already removed has nothing left to correct.
            gone = re.match(r"sources\[([^\]]+)\]", path)
            if gone and gone.group(1) in removed:
                continue
            try:
                set_path(r, path, copy.deepcopy(value))
            except (ValueError, AttributeError, TypeError) as exc:
                problems.append(f"{role} correction could not be applied: {exc}")
        # Corrections first, then removals: a `set` may address a source the same verdict removes.
        drop = set(v.get("remove_sources") or [])
        if drop:
            removed |= drop
            r["sources"] = [s for s in r.get("sources") or [] if not (isinstance(s, dict) and s.get("ref") in drop)]
    sources = [s for s in r.get("sources") or [] if isinstance(s, dict)]
    # What was opened. Where the evidence reviewer lists what they opened, that list is the answer,
    # whatever the lane wrote. Where they list nothing (the field is optional), a source is opened
    # only if the lane itself recorded opening it: anything else reads as not opened.
    evidence = verdicts.get("evidence") or {}
    listed = evidence.get("sources_opened")
    for s in sources:
        s["opened"] = (s.get("ref") in listed) if isinstance(listed, list) else s.get("opened") is True
    return r, problems


def lead_patch(reviews, lane, cid):
    """(the lead's normalisation of this candidate, its date), or (None, None)."""
    doc = reviews.get(LEAD, {}).get(lane)
    v = doc["verdicts"].get(cid) if doc else None
    return (v, str(doc.get("reviewed_at") or "")) if isinstance(v, dict) else (None, None)


def apply_lead(reviewed, patch, patched_at):
    """A record every role accepted, with the lead's normalisation applied. Returns (record,
    problems); any problem refuses the record, so a patch that oversteps is never half-applied.

    WHAT THE LEAD MAY NOT DO HERE, because each is a reviewer's decision or a safety rule: accept
    or reject (the verdicts are already in), publish an abstracted record at a weaker policy, give
    a record with no region a region, turn an attack into anything else, or mark a source opened."""
    problems = []
    if patch.get("verdict") != "accept_with_correction":
        problems.append(f"its verdict is {patch.get('verdict')!r}; a normalisation is accept_with_correction and "
                        "decides nothing")
    extra = sorted(set(patch) - set(LEAD_KEYS))
    if extra:
        problems.append(f"it carries {extra}; a normalisation has `set` and `remove_sources` only")
    if not G._date_ok(patched_at):
        problems.append("the lead's file gives no reviewed_at date")
    if problems:
        return reviewed, [f"lead normalisation refused: {p}" for p in problems]
    opened = {s.get("ref"): s.get("opened") is True for s in reviewed.get("sources") or [] if isinstance(s, dict)}
    r, problems = apply_reviews(reviewed, {LEAD: patch}, roles=(LEAD,))
    for src in r.get("sources") or []:
        if isinstance(src, dict):
            # Opened is what the evidence reviewer or the lane found, never what a later patch says.
            src["opened"] = opened.get(src.get("ref"), False)
    if G.is_attack(reviewed) and (not G.is_attack(r) or r.get("cause_family") != reviewed.get("cause_family")):
        problems.append("it would change the cause of a kinetic or sabotage record")
    if reviewed.get("publication_policy") == G.ABSTRACTED and r.get("publication_policy") != G.ABSTRACTED:
        problems.append("it would publish a country-abstracted record at a weaker policy")
    if reviewed.get("admin1") is None and r.get("admin1") is not None:
        problems.append("it would give a region to a record the reviewers accepted without one")
    return r, [f"lead normalisation refused: {p}" for p in problems]


def prune_refs(r, refs, supports=None):
    """Drop `source_refs` that point at a source a reviewer removed, or (given `supports`, {ref:
    claims}) at a source the reviewers no longer let support that claim. A claim left with no
    source by that is then refused by the gate, which is the point."""
    def keep(obj, claim):
        if isinstance(obj, dict) and isinstance(obj.get("source_refs"), list):
            obj["source_refs"] = [x for x in obj["source_refs"]
                                  if x in refs and (supports is None or claim is None or claim in supports.get(x, ()))]
    for c in r.get("civilian_service_impact") or []:
        keep(c, "effect")
    keep(r.get("attribution"), "attribution")
    keep(r.get("ai_involvement"), "ai_involvement")
    keep(r.get("dispute"), None)
    for c in ((r.get("attribution") or {}).get("competing") or []) if isinstance(r.get("attribution"), dict) else []:
        keep(c, "attribution")


def reviewed_addenda(sources, review_id, taken, reviews, moved=False):
    """[(source, why not)] for the sources added later to one filed record. `why not` is None when
    every role accepted the addendum; its corrections are applied to the source itself.

    `review_id` is the id the addendum was reviewed under: the record's own original id, or, for
    `moved` addenda, the id of the copy the lead holds as its duplicate. A moved source whose ref
    the surviving record already uses takes the next free one."""
    out = []
    for src in sources:
        if not isinstance(src, dict) or not src.get("ref"):
            continue
        verdicts, _ = verdicts_for(reviews, "social", f"{review_id}#{src['ref']}", ADDENDA_ROLES)
        why = "not reviewed" if not verdicts else review_state(verdicts, ADDENDA_ROLES)
        if why is None and src["ref"] in taken and not moved:
            why = f"the record already has a source {src['ref']}"
        if why is None:
            fixed, problems = apply_reviews({"sources": [src]}, {role: {**v, "set": {}} for role, v in verdicts.items()})
            src = fixed["sources"][0]
            for role in ADDENDA_ROLES:
                for path, value in (verdicts[role].get("set") or {}).items():
                    try:
                        set_path(src, path, copy.deepcopy(value))
                    except (ValueError, AttributeError, TypeError) as exc:
                        problems.append(f"{role} correction could not be applied: {exc}")
            why = " | ".join(problems) or None
            if src["ref"] in taken:
                n = 1
                while f"s{n}" in taken:
                    n += 1
                src["ref"] = f"s{n}"
            taken.add(src["ref"])
        out.append((src, why))
    return out


def hold_survivor(reason):
    """The `<lane>/<id>` a lead hold names as the record this one duplicates, or None."""
    m = re.search(r"duplicate of\s+([A-Za-z0-9_]+/imp-[A-Za-z0-9_-]+)", str(reason), re.I)
    return m.group(1) if m else None


def review_state(verdicts, roles):
    """None if every role accepted, else why not."""
    missing = [role for role in roles if role not in verdicts]
    if missing:
        return f"not reviewed by {', '.join(missing)}"
    for role in roles:
        v = verdicts[role].get("verdict")
        if v not in VERDICTS:
            return f"{role} verdict {v!r} is not one of {VERDICTS}"
        if v == "reject":
            return f"rejected by {role}: {verdicts[role].get('reason') or 'no reason given'}"
    return None


# --- shaping a record -------------------------------------------------------------------------------

def abstract_id(record, original_id, key):
    """`imp-<date>-<a3>-<sector>-attack-<6 hex>` ("event" where a reviewer abstracted a record that
    is not an attack): six digits of a keyed hash of the queue id, so the id names no place, counts
    no sibling and cannot be matched by hashing guesses."""
    tag = hmac.new(key, f"impact|{original_id}".encode("utf-8"), hashlib.sha256).hexdigest()[:6]
    return f"{G.abstracted_stem(record)}{tag}"


def _prefix(record):
    """The stem every id of this record starts with: date, country and the sector id as written."""
    return f"imp-{record.get('date')}-{str(record.get('country_a3') or '').lower()}-{record.get('sector')}-"


def canonical_id(rid, record):
    """`imp-<date>-<a3>-<sector>-<slug>` with the stem rebuilt from the record's own fields and the
    slug kept. Lanes spelled the stem several ways (a hyphenated sector, a full date on a
    month-precision record, the date before a reviewer corrected it); the contract has one."""
    m = re.fullmatch(r"imp-\d{4}(?:-\d{2}){0,2}-[A-Za-z]{3,5}-(.+)", rid)
    if not m:
        return rid
    rest = m.group(1)
    for sector in sorted(G.SECTOR_DOMAIN, key=len, reverse=True):
        spelled = next((s for s in (sector, sector.replace("_", "-")) if rest.startswith(s + "-")), None)
        if spelled:
            rest = rest[len(spelled) + 1:]
            break
    slug = re.sub(r"[^a-z0-9]+", "-", rest.lower()).strip("-")
    return _prefix(record) + slug if slug else rid


def _qualifier(word, source_says):
    """A lane's qualifier in the vocabulary's spelling, or None if it is not one. A lane that gave
    no word gets the one the source's own words carry; a word this does not know is left for a
    reviewer, never guessed."""
    word = str(word or "").strip().lower().replace("_", " ")
    if not word:
        return B.capacity_qualifier(source_says)
    return word.replace(" ", "_") if word.replace(" ", "_") in G.ids("affected_qualifiers") else QUALIFIER_WORDS.get(word)


def normalise(r, notes):
    """Mechanical rewrites of a lane's spelling into the contract's, each noted in the report.
    Nothing here decides what a reviewer decides: an unknown word is left for the gate to refuse."""
    if isinstance(r.get("date"), str) and r.get("date_precision") in ("month", "year"):
        canon = B.canonical_date(r["date"], r["date_precision"])
        if canon != r["date"]:
            notes.append(f"date written at its {r['date_precision']} precision")
            r["date"] = canon
    if r.get("record_kind") == G.ATTEMPT and (r.get("inclusion_basis") is not None or r.get("civilian_service_impact")):
        # An attempt met no inclusion basis and affected no service: neither is carried.
        notes.append("an attempt carries no inclusion basis and no service impact: removed")
        r["inclusion_basis"], r["civilian_service_impact"] = None, []
    for s in r.get("sources") or []:
        # A reviewer who wrote the attributing source's ROLE where its basis belongs.
        basis = s.get("attribution_basis")
        if basis is not None and basis not in G.EC.ATTRIBUTION_BASES and basis in G.EC.BASIS_OF_ROLE:
            notes.append(f"attribution_basis {basis!r} written as {G.EC.BASIS_OF_ROLE[basis]}")
            s["attribution_basis"] = G.EC.BASIS_OF_ROLE[basis]
    # A citation the reviewers no longer let support a claim is not cited for it.
    sources = [s for s in r.get("sources") or [] if isinstance(s, dict)]
    before = json.dumps([r.get("civilian_service_impact"), r.get("attribution"), r.get("ai_involvement")], sort_keys=True)
    prune_refs(r, {s.get("ref") for s in sources}, {s.get("ref"): tuple(s.get("supports") or ()) for s in sources})
    if before != json.dumps([r.get("civilian_service_impact"), r.get("attribution"), r.get("ai_involvement")], sort_keys=True):
        notes.append("a source no longer cited for a claim it does not support")
    if r.get("date_end") in G.ABSENCE or r.get("date_end") == "":
        # A date field holds a date or null. An end date nobody states is simply not given.
        notes.append(f"end date {r['date_end']!r} written as null")
        r["date_end"] = None
    if r.get("geographic_precision") in ("multi_admin1", "multi_region"):
        # Several regions of one country: recorded for the country, as the country systems do.
        notes.append("an event across several regions is recorded for the country")
        r["geographic_precision"], r["admin1"] = "country", None
    for c in r.get("civilian_service_impact") or []:
        if not isinstance(c, dict):
            continue
        if c.get("geographic_scope") in SCOPE_WORDS:
            notes.append(f"geographic scope {c['geographic_scope']!r} written as {SCOPE_WORDS[c['geographic_scope']]}")
            c["geographic_scope"] = SCOPE_WORDS[c["geographic_scope"]]
        aff = c.get("affected")
        if not isinstance(aff, dict):
            continue
        if "absence" in aff:
            # Some lanes wrote why there is no figure beside a null value; the contract writes it as the value.
            word = aff.pop("absence")
            if aff.get("value") is None and word in G.ABSENCE:
                aff["value"] = word
        has_figure = aff.get("value") is not None and aff.get("value") not in G.ABSENCE
        if has_figure and aff.get("qualifier") not in G.ids("affected_qualifiers"):
            fixed = _qualifier(aff.get("qualifier"), aff.get("source_says"))
            if fixed in G.ids("affected_qualifiers"):
                notes.append(f"qualifier {aff.get('qualifier')!r} written as {fixed}")
                aff["qualifier"] = fixed
        if not has_figure and aff.get("qualifier") is not None:
            notes.append(f"qualifier {aff.get('qualifier')!r} removed: there is no figure for it to qualify")
            aff["qualifier"] = None
    a = r.get("attribution")
    for c in (a.get("competing") or []) if isinstance(a, dict) else []:
        if isinstance(c, dict):
            if c.get("note") and not c.get("statement"):
                c["statement"] = c["note"]
            for k in ("note", "status"):
                c.pop(k, None)
    if isinstance(a, dict) and isinstance(a.get("competing"), list):
        # A competing attribution stands on a source like any other claim. One whose sources the
        # reviewers removed, or no longer let support attribution, is not carried.
        kept = [c for c in a["competing"] if not isinstance(c, dict) or c.get("source_refs")]
        if len(kept) != len(a["competing"]):
            notes.append(f"{len(a['competing']) - len(kept)} competing attribution(s) dropped: no surviving source "
                         "supports them")
            a["competing"] = kept
    factors = r.get("contributing_factors") if isinstance(r.get("contributing_factors"), list) else []
    if (isinstance(a, dict) and a.get("status") == "UNKNOWN" and r.get("cause_family") in G.NOT_MALICIOUS
            and not set(factors) & set(G.MALICIOUS)):
        # Nobody is asked who did a storm. UNKNOWN is for a malicious act nobody credibly
        # attributes; the reverse (NOT_APPLICABLE on a malicious act) is refused, never rewritten.
        notes.append("attribution UNKNOWN on a record that is not a malicious act written as NOT_APPLICABLE")
        a["status"], a["actor"], a["actor_type"] = "NOT_APPLICABLE", None, None
    d = r.get("dispute")
    if isinstance(d, dict) and "claim" in d:
        # Some lanes named what is disputed under `claim`.
        claim = d.pop("claim")
        if d.get("about") is None and claim in G.ids("dispute_about"):
            d["about"] = claim


def clean_sources(sources):
    """Citations with the contract's fields only, in ref order; an optional field left null is dropped."""
    out = []
    for s in sources or []:
        if isinstance(s, dict):
            s = {k: s[k] for k in G.SOURCE_FIELDS if k in s}
            s.setdefault("social", None)
            for k in ("title_original", "title_en", "origin", "attribution_basis", "date_basis"):
                if s.get(k) is None:
                    s.pop(k, None)
            out.append(s)
    return sorted(out, key=lambda s: str(s.get("ref")))


def drop_unknown(r):
    """Remove fields the contract does not have from each part of a record; return their names."""
    dropped = []

    def keep(obj, allowed, where):
        if isinstance(obj, dict):
            for k in sorted(set(obj) - set(allowed)):
                del obj[k]
                dropped.append(f"{where}.{k}")

    a = r.get("attribution")
    keep(a, G.ATTRIBUTION_FIELDS, "attribution")
    for c in (a.get("competing") or []) if isinstance(a, dict) and isinstance(a.get("competing"), list) else []:
        keep(c, G.COMPETING_FIELDS, "attribution.competing")
    keep(r.get("ai_involvement"), G.AI_FIELDS, "ai_involvement")
    keep(r.get("dispute"), G.DISPUTE_FIELDS, "dispute")
    keep(r.get("admin1"), ("code", "name"), "admin1")
    for c in r.get("civilian_service_impact") or []:
        keep(c, G.IMPACT_FIELDS, "civilian_service_impact")
        if isinstance(c, dict):
            keep(c.get("affected"), G.AFFECTED_FIELDS, "civilian_service_impact.affected")
    for s in r.get("sources") or []:
        keep(s.get("social"), G.SOCIAL_FIELDS, "sources.social")
    return sorted(set(dropped))


def shape(reviewed, original_id, key, restricted, notes):
    """The reviewed candidate as a curated record (without its stamps): contract fields only,
    abstracted if it is an attack, headlines removed where they may not be shown."""
    r = {k: reviewed[k] for k in G.RECORD_FIELDS if k in reviewed and k not in ("review", "first_published", "last_revised")}
    # A field that is not part of the contract is dropped, never served. A reviewer who set one
    # to null meant exactly that.
    dropped = sorted(set(reviewed) - set(G.RECORD_FIELDS))
    dropped += sorted({f"sources.{k}" for s in reviewed.get("sources") or [] if isinstance(s, dict)
                       for k in set(s) - set(G.SOURCE_FIELDS)})
    for k, default in (("date_end", None), ("admin1", None), ("contributing_factors", []), ("cyber_mechanism", None),
                       ("civilian_service_impact", []), ("dispute", None), ("episode_id", None),
                       ("episode_basis", None), ("publication_policy", "standard")):
        r.setdefault(k, default)
    r["sources"] = clean_sources(r.get("sources"))
    normalise(r, notes)
    dropped += drop_unknown(r)
    if dropped:
        notes.append(f"fields outside the contract dropped: {', '.join(dropped)}")
    # The id's stem follows the record: a reviewer who corrected the date, country or sector need
    # not retype it, and a lane's own spelling of the stem is written as the contract writes it.
    r["impact_id"] = canonical_id(str(r.get("impact_id") or ""), r)

    abstracted = G.is_attack(r) or r.get("publication_policy") == G.ABSTRACTED
    if abstracted:
        # The campaign policy of the Gulf systems, applied to every attack everywhere (§4), and to
        # any other record a lane or a reviewer chose to abstract: the stricter policy is allowed.
        r["publication_policy"] = G.ABSTRACTED
        r["geographic_precision"] = "country"
        r["admin1"] = None
        r["episode_id"] = r["episode_basis"] = None
        if r.get("date_end") is not None:
            notes.append("end date removed: when service came back is later status")
            r["date_end"] = None
        if r.get("domain") == "energy" and r.get("technology") is None:
            # An energy record names its technology or says why not. For a record published
            # without its place the honest word is that it is withheld.
            notes.append("technology written as withheld on an abstracted record that named none")
            r["technology"] = "withheld"
        # Whatever a reviewer renamed it to: an abstracted record's id is always the keyed one.
        r["impact_id"] = abstract_id(r, original_id, key)
    if abstracted or restricted:
        # A headline names the place, the operator or the method; it is not shown beside a record
        # published without them, nor in a system under the campaign policy.
        for s in r["sources"]:
            if "title_original" in s or "title_en" in s:
                s.pop("title_original", None)
                s.pop("title_en", None)
                notes.append(f"headline removed from source {s.get('ref')}")
    return {k: r[k] for k in G.RECORD_FIELDS if k in r}


def review_block(record, verdicts, reviewed_at, roles, full=True, lead_at=None):
    """The published review block. `lead_at` is the date of the lead's normalisation, if there was
    one: it is stated beside the roles' verdicts and is never one of them."""
    lead = {"lead_normalisation": True, "lead_normalisation_at": lead_at} if lead_at else {}
    out = {"reviewed_at": reviewed_at, "roles": {role: verdicts[role]["verdict"] for role in roles}}
    if not full:
        return {**out, **lead}
    corrected = any(verdicts[role]["verdict"] == "accept_with_correction" for role in roles) or bool(lead)
    ai = (record.get("ai_involvement") or {}).get("status") not in (None, "NONE_REPORTED")
    social = any(s.get("medium") == "social" for s in record.get("sources") or [])
    return {"reviewed_at": reviewed_at, "review_status": "blind_reviewed", "roles": out["roles"],
            # The attribution-and-source role applies both checks; it accepted, so where they apply they passed.
            "ai_check": "passed" if ai else "not_applicable",
            "social_check": "passed" if social else "not_applicable",
            "disposition": "corrected" if corrected else "confirmed", **lead}


def stamp(new, old, date):
    """`first_published` once, for the life of the record; `last_revised` when its content changes."""
    def body(r):
        return {k: v for k, v in r.items() if k not in ("first_published", "last_revised")}
    out = dict(new)
    if old is None:
        out["first_published"] = date
    else:
        out["first_published"] = old.get("first_published") or date
        if body(new) != body(old):
            out["last_revised"] = date
        elif "last_revised" in old:
            out["last_revised"] = old["last_revised"]
    return out


# --- dates ------------------------------------------------------------------------------------------

def span(text):
    """(first day, last day) of a day-, month- or year-precision date, or None."""
    try:
        parts = [int(x) for x in str(text)[:10].split("-")]
        if len(parts) == 3:
            d = dt.date(*parts)
            return d, d
        if len(parts) == 2:
            first = dt.date(parts[0], parts[1], 1)
            return first, (first.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
        return dt.date(parts[0], 1, 1), dt.date(parts[0], 12, 31)
    except (ValueError, TypeError):
        return None


def within_a_day(a, b, days=1):
    sa, sb = span(a), span(b)
    if not sa or not sb:
        return False
    day = dt.timedelta(days=days)
    return sa[0] - day <= sb[1] and sb[0] - day <= sa[1]


# --- dedupe -----------------------------------------------------------------------------------------

def _same_event(a, b):
    return (set(G._countries(a)) & set(G._countries(b)) and a.get("sector") == b.get("sector")
            and within_a_day(a.get("date"), b.get("date")))


def duplicate_groups(items, distinct=()):
    """Groups of accepted candidates that look like one event: same country and sector, dates within
    a day. `distinct` lists pairs of original ids the lead has ruled are different events."""
    ruled = {frozenset(pair) for pair in distinct}
    root = list(range(len(items)))

    def find(i):
        while root[i] != i:
            i = root[i]
        return i

    for i, a in enumerate(items):
        for j in range(i + 1, len(items)):
            b = items[j]
            if _same_event(a["record"], b["record"]) and not ruled & {frozenset((a["original_id"], b["original_id"])),
                                                                      frozenset((a["key"], b["key"]))}:
                root[find(j)] = find(i)
    groups = {}
    for i, item in enumerate(items):
        groups.setdefault(find(i), []).append(item)
    return [g for g in groups.values() if len(g) > 1]


# --- reconciling with the country queues -------------------------------------------------------------

def _class_matches(asset_class, record):
    """Whether a country record's class and an impact record's sector can describe one event. A
    class the mapping gives no sector (a system-wide event, an upstream field) matches any energy
    sector: the conservative reading."""
    mapped = G.TAXONOMY["asset_class_to_technology"]["map"].get(asset_class)
    if mapped is None or mapped["sector"] is None:
        return record.get("domain") == "energy"
    # Sector or technology: a fuel terminal is oil and gas there and fuel supply here.
    return mapped["sector"] == record.get("sector") or (
        mapped["technology"] is not None and mapped["technology"] == record.get("technology"))


def country_opaque_id(system_id, r, key):
    """The id the country import publishes an attack record under (scripts/import_candidates.py,
    `opaque_id`): the same keyed hash, so a published attack record is recognised as published."""
    tag = hmac.new(key, f"{system_id}|{r['candidate_id']}".encode("utf-8"), hashlib.sha256).hexdigest()[:6]
    return f"{system_id}-{r.get('date')}-{str(r.get('asset_class') or '').replace('_', '-')}-attack-{tag}"


def load_country_queue(system_id, country_queues, systems_curated, key):
    """(unpublished queue records, all queue records by id) of a monitored system. A queue record is
    published when the curated file holds it under its own id, an earlier name of it, or its opaque
    id; a duplicate of a published record is published too."""
    path = Path(country_queues) / f"{system_id}.json"
    curated = Path(systems_curated) / system_id / "events.json"
    if not path.exists():
        return [], {}
    queue = [r for r in read_json(path) if isinstance(r, dict) and r.get("candidate_id")]
    published_ids = {e["event_id"] for e in read_json(curated)["events"]} if curated.exists() else set()
    by_id = {r["candidate_id"]: r for r in queue}

    def published(r, depth=0):
        if {r["candidate_id"], r.get("renamed_from"), country_opaque_id(system_id, r, key)} & published_ids:
            return True
        original = by_id.get(r.get("duplicate_of"))
        return bool(original) and depth < 5 and published(original, depth + 1)

    return [r for r in queue if not published(r)], by_id


def hold_fields(r):
    """The process fields a country queue record carries about why it is not published."""
    out = {k: r.get(k) for k in ("suggested_disposition", "disposition_reason", "lead_hold", "duplicate_of",
                                 "researcher_disposition") if r.get(k) is not None}
    for k in ("independent_review", "primary_review"):
        if isinstance(r.get(k), dict):
            out[k] = {x: r[k].get(x) for x in ("disposition", "outcome", "reason", "roles", "note") if r[k].get(x) is not None}
    return out


def _hold_text(r):
    """The reasons written on a country queue record, as one text. Reasons only: the keys of a
    review's `roles` ("safety", "evidence") are role names, not findings."""
    parts = [r.get("disposition_reason")]
    if isinstance(r.get("lead_hold"), dict):
        parts += [r["lead_hold"].get("basis"), r["lead_hold"].get("tag")]
    for k in ("independent_review", "primary_review"):
        if isinstance(r.get(k), dict):
            parts += [r[k].get("reason"), r[k].get("note"), r[k].get("outcome")]
    return " \n ".join(str(p) for p in parts if p)


def hold_kind(r, system_id, by_id, restricted, depth=0):
    """Why a country queue record is not published: "campaign", "safety", "evidence", "threshold" or
    "unclear". Read from the record's own fields; anything but a clear threshold hold fails closed."""
    if r.get("suggested_disposition") == "duplicate":
        original = by_id.get(r.get("duplicate_of"))
        return hold_kind(original, system_id, by_id, restricted, depth + 1) if original and depth < 5 else "unclear"
    if r.get("cause") in B.KINETIC_CAUSES:
        return "campaign"
    text = _hold_text(r)
    if SAFETY_HOLD.search(text) or r.get("suggested_disposition") == "out_of_scope":
        return "campaign" if system_id in restricted and re.search(r"campaign|withh[eo]ld", text, re.I) else "safety"
    if r.get("suggested_disposition") == "insufficient_evidence" or EVIDENCE_HOLD.search(text):
        return "evidence"
    # A threshold hold is one the queue SAYS is a threshold hold: held or rejected, with the clause.
    if r.get("suggested_disposition") in ("held", "reject") and THRESHOLD_HOLD.search(text):
        return "threshold"
    return "unclear"


def country_matches(record, ctx, queues):
    """[(system_id, queue record)] for unpublished country candidates this record matches."""
    out = []
    for a3 in G._countries(record):
        sid = ctx["system_of"].get(a3)
        if not sid:
            continue
        unpublished, _ = queues(sid)
        for q in unpublished:
            if within_a_day(record.get("date"), q.get("date")) and _class_matches(q.get("asset_class"), record):
                out.append((sid, q))
    return out


# --- the research note -------------------------------------------------------------------------------

def _lane_stem(lane):
    return re.sub(r"\d+$", "", lane)


def research_log(existing, lane_logs, date, held=None):
    """The published research note, with this run's lanes replacing their earlier entries. Process
    facts only: source families, method, window, status, limitation; and, where the lead holds
    records, how many and on which of three grounds, as numbers. Never a reason, a lane or an id:
    nothing in it identifies a record that is not published. Returns (log, dropped)."""
    out = {k: copy.deepcopy(existing.get(k)) for k in G.LOG_FIELDS if k != "lead_holds"}
    out["window"] = out["window"] or {"start": G.WINDOW_START, "end": "present"}
    out["status"] = out["status"] or "expanding corpus"
    families = [f for f in out["source_families"] or [] if f.get("lane") not in lane_logs]
    regions = set(out["regions_worked"] or [])
    latest = out["latest_research_date"]
    dropped = []
    standing = G.log_problems({**out, "source_families": []})
    for lane in sorted(lane_logs):
        doc, scope = lane_logs[lane]
        for f in doc.get("source_families") or []:
            if not isinstance(f, dict) or not f.get("family"):
                continue
            entry = {"lane": lane, "scope": scope, "research_pass": f"i22-{lane}"}
            entry.update({k: (str(f[k]) if f.get(k) is not None else None) for k in ("family", "method", "window", "status", "limitation")})
            problems = [p for p in G.log_problems({**out, "source_families": [entry]}) if p not in standing]
            if problems:
                dropped.append({"lane": lane, "family": entry["family"], "why": problems})
            else:
                families.append(entry)
        if scope == "impacts":
            listed = doc.get("regions") if isinstance(doc.get("regions"), list) else LANE_REGIONS.get(_lane_stem(lane), [])
            regions |= {str(x) for x in listed}
        # When the lane worked: its own field, else the last date its scope names. Never after today.
        stated = doc.get("research_date") or max(re.findall(r"\d{4}-\d{2}-\d{2}", str(doc.get("scope") or "")), default=None)
        if stated and G._date_ok(stated) and stated <= date and (latest is None or stated > latest):
            latest = stated
    out["source_families"] = sorted(families, key=lambda f: (f["lane"], str(f["family"]), str(f.get("method"))))
    out["regions_worked"] = sorted(regions)
    out["limitations"] = out["limitations"] or []
    out["latest_research_date"] = latest
    if held and sum(held.values()):
        out["lead_holds"] = {"held": sum(held.values()), **{k: held.get(k, 0) for k in G.HOLD_GROUNDS}}
    return out, dropped


# --- the run ----------------------------------------------------------------------------------------

def run(queue=QUEUE, curated=G.IMPACTS_CURATED, date=None, country_queues=COUNTRY_QUEUES,
        systems_curated=B.SYSTEMS_CURATED, ctx=None, key=None, write=True):
    """Import the queue into the curated directory and return the report."""
    queue, curated = Path(queue), Path(curated)
    date = date or dt.date.today().isoformat()
    if not G._date_ok(date):
        raise SystemExit(f"--date {date!r} is not a date")
    ctx = ctx or G.load_context()
    if key is None:
        import import_candidates
        key = import_candidates.opaque_key()
    reviews = load_reviews(queue)
    events_doc = read_json(curated / "events.json")
    context_doc = read_json(curated / "regional_context.json")
    existing = {r["impact_id"]: r for r in events_doc["records"]}
    existing_ctx = {e["id"]: e for e in context_doc["entries"]}
    # The lead's rulings that a date-and-class match with a held country record is a different
    # event. Not an override: see step 6.
    ruled_distinct = read_json(queue / "reconcile_distinct.json") if (queue / "reconcile_distinct.json").exists() else {}
    distinct = read_json(queue / "distinct_events.json") if (queue / "distinct_events.json").exists() else []
    # The lead's own holds, by the id the lane filed: refused whatever the reviewers said.
    holds = load_holds(queue)
    held = dict.fromkeys(G.HOLD_GROUNDS, 0)
    # Sources found later for a filed record: {original id: [source, ...]}, reviewed in
    # reviews/<role>/social.json under "<original id>#<ref>".
    addenda = read_json(queue / "social" / "addenda.json") if (queue / "social" / "addenda.json").exists() else {}

    _queues = {}

    def queues(sid):
        if sid not in _queues:
            _queues[sid] = load_country_queue(sid, country_queues, systems_curated, key)
        return _queues[sid]

    report = {"date": date, "imported": [], "refused": [], "not_reviewed": [], "withdrawn": [], "renamed": {},
              "notes": {}, "reconcile": [], "by_lane": {}, "context": {"imported": [], "refused": [], "not_reviewed": [],
                                                                      "withdrawn": []},
              "research_log": {}, "addenda": [], "collisions": [], "possible_duplicates": [],
              "lead_holds": {"count": 0}, "lead_normalised": [],
              "ignored_files": ["reconcile_allow.json"] if (queue / "reconcile_allow.json").exists() else []}
    lane_logs, accepted, known_ids = {}, [], set()
    # {surviving "<lane>/<id>": [held "<lane>/<id>", ...]}, from holds that name what they duplicate.
    duplicates_of = {}

    def lane_tally(lane):
        return report["by_lane"].setdefault(lane, {"imported": 0, "refused": 0, "not_reviewed": 0})

    def refuse(item, reasons):
        report["refused"].append({"lane": item["lane"], "candidate_id": item["original_id"],
                                  "reasons": reasons if isinstance(reasons, list) else [reasons]})
        lane_tally(item["lane"])["refused"] += 1

    # 1-4. Read, review, patch and shape every candidate.
    for lane_dir in lane_dirs(queue):
        lane = lane_dir.name
        lane_tally(lane)
        has_context = (lane_dir / "context_entries.json").exists()
        if (lane_dir / "lane_log.json").exists():
            doc = read_json(lane_dir / "lane_log.json")
            if isinstance(doc, dict):
                lane_logs[lane] = (doc, "regional_context" if has_context else "impacts")
        for cand in _rows(lane_dir / "candidates.json", ("records", "candidates")):
            original_id = str(cand.get("impact_id") or "")
            # Two lanes may file one incident under the same id: a candidate is its lane AND its id
            # until the final ids are assigned.
            item = {"lane": lane, "original_id": original_id, "key": f"{lane}/{original_id}"}
            lane_tally(lane)
            # Every id this candidate could be published under, so a record that stops being
            # accepted is taken out of the curated file instead of lingering there.
            known_ids.update({original_id, canonical_id(original_id, cand), abstract_id(cand, original_id, key),
                              abstract_id({**cand, "cause_family": "kinetic"}, original_id, key)})
            hold = holds.get(item["key"], holds.get(original_id))
            if hold is not None:
                report["lead_holds"]["count"] += 1
                held[hold_ground(hold)] += 1
                if hold_survivor(hold):
                    duplicates_of.setdefault(hold_survivor(hold), []).append(item["key"])
                refuse(item, "lead hold: " + re.sub(r"^lead hold:\s*", "", hold, flags=re.I))
                continue
            verdicts, reviewed_at = verdicts_for(reviews, lane, original_id, ROLE_ORDER)
            if not verdicts:
                report["not_reviewed"].append({"lane": lane, "candidate_id": original_id})
                lane_tally(lane)["not_reviewed"] += 1
                continue
            for v in verdicts.values():
                renamed = (v.get("set") or {}).get("impact_id")
                if renamed:
                    known_ids.add(str(renamed))
            why = review_state(verdicts, ROLE_ORDER)
            if why:
                refuse(item, why)
                continue
            reviewed, problems = apply_reviews(cand, verdicts)
            # The lead's normalisation: only now, on a record every role accepted, and after safety.
            patch, lead_at = lead_patch(reviews, lane, original_id)
            if patch is not None and not problems:
                if (patch.get("set") or {}).get("impact_id"):
                    known_ids.add(str(patch["set"]["impact_id"]))
                reviewed, problems = apply_lead(reviewed, patch, lead_at)
            if problems:
                refuse(item, problems)
                continue
            if patch is None:
                lead_at = None
            else:
                report["lead_normalised"].append(item["key"])
            notes = []
            restricted = bool(G.restricted_systems(reviewed, ctx)) if isinstance(reviewed.get("country_a3"), str) else False
            record = shape(reviewed, original_id, key, restricted, notes)
            known_ids.add(str(record.get("impact_id")))
            record["review"] = review_block(record, verdicts, reviewed_at, ROLE_ORDER, lead_at=lead_at)
            item.update({"record": record, "notes": notes, "verdicts": verdicts, "reviewed_at": reviewed_at,
                         "restricted": restricted, "lead_at": lead_at})
            accepted.append(item)

    # A renamed id that lands on another candidate's id, or on a different published record.
    by_final = {}
    for item in accepted:
        by_final.setdefault(item["record"].get("impact_id"), []).append(item)
    for rid, items in by_final.items():
        old = existing.get(rid)
        clash = len(items) > 1 or (old is not None and (old.get("country_a3"), old.get("sector")) !=
                                   (items[0]["record"].get("country_a3"), items[0]["record"].get("sector")))
        if clash:
            # Never overwritten, never one silently chosen: the run fails and the lead rules.
            report["collisions"].append({"impact_id": rid, "candidates": sorted(i["key"] for i in items)})
            for item in items:
                item["refused"] = [f"id collision: {rid} would name more than one record"]
    # 5. Dedupe across lanes.
    for group in duplicate_groups([i for i in accepted if "refused" not in i], distinct):
        for item in group:
            others = sorted(x["original_id"] for x in group if x is not item)
            item["refused"] = [f"accepted by reviewers alongside {others}, which looks like the same event (same country "
                               "and sector, dates within a day): a reviewer rejects one as a duplicate, or the lead "
                               "lists the pair in distinct_events.json"]
    # 6. Reconcile with the country queues.
    for item in accepted:
        if "refused" in item:
            continue
        record = item["record"]
        for sid, q in country_matches(record, ctx, queues):
            kind = hold_kind(q, sid, queues(sid)[1], ctx["restricted"])
            entry = {"lane": item["lane"], "candidate_id": item["original_id"], "system_id": sid,
                     "country_candidate_id": q["candidate_id"], "hold_kind": kind, "hold_fields": hold_fields(q)}
            # No override, whatever the hold was for: a restriction on publishing an event carries
            # over to this layer. The one thing the lead may say is that the match is FALSE: the
            # country record is a different event. That lifts no hold.
            listed = ruled_distinct.get(item["key"]) or []
            ruling = next((o for o in (listed if isinstance(listed, list) else [listed])
                           if isinstance(o, dict) and o.get("country_candidate_id") == q["candidate_id"]), None)
            reason = str((ruling or {}).get("reason") or "").strip()
            if ruling is None:
                entry["outcome"] = "refused: matches a record held or rejected in the country system's queue"
            elif not reason:
                entry["outcome"] = "refused: the ruling that this is a different event gives no reason"
            elif G.is_attack(record):
                entry["outcome"] = "refused: an attack record is never ruled distinct from a held country record"
            else:
                entry["outcome"] = f"a different event, by the lead's ruling: {reason}"
            report["reconcile"].append(entry)
            if entry["outcome"].startswith("refused"):
                item.setdefault("refused", []).append(
                    f"reconcile with {sid}: {entry['outcome'][9:]} (country candidate {q['candidate_id']})")
    # 7-8. The build's own gate, then the stamps.
    imported = {}

    def gated(base):
        stamped = stamp(base, existing.get(base["impact_id"]), date)
        stamped = {k: stamped[k] for k in G.RECORD_FIELDS if k in stamped}
        return stamped, G.one_record_problems(stamped, ctx)

    for item in accepted:
        if "refused" not in item:
            record, problems = gated(item["record"])
            if not problems:
                # Social addenda: a source found later for a record that was itself accepted. Each
                # is added only if every role accepted it and the record still passes the gate.
                base = item["record"]
                taken = {s.get("ref") for s in base["sources"]}
                own = addenda.get(item["key"]) or addenda.get(item["original_id"]) or []
                found = [(src, why, None) for src, why in reviewed_addenda(own, item["original_id"], taken, reviews)]
                # Addenda of a copy the lead holds as this record's duplicate follow the survivor.
                for held_key in duplicates_of.get(item["key"], []):
                    held_id = held_key.split("/", 1)[1]
                    theirs = addenda.get(held_key) or addenda.get(held_id) or []
                    if theirs is not own:   # two lanes that filed under one id share one list of addenda
                        found += [(src, why, held_key) for src, why in reviewed_addenda(theirs, held_id, taken, reviews, moved=True)]
                for src, why, moved_from in found:
                    outcome = {"candidate_id": item["original_id"], "ref": src.get("ref")}
                    if moved_from:
                        outcome["moved_from"] = moved_from
                    if why is None and any(s.get("url") == src.get("url") for s in base["sources"]):
                        why = "the record already cites this address"
                    if why is None:
                        trial = {**base, "sources": sorted(base["sources"] + clean_sources([src]), key=lambda s: str(s.get("ref")))}
                        if item["restricted"] or trial.get("publication_policy") == G.ABSTRACTED:
                            for s in trial["sources"]:
                                s.pop("title_original", None)
                                s.pop("title_en", None)
                        trial["review"] = review_block(trial, item["verdicts"], item["reviewed_at"], ROLE_ORDER,
                                                       lead_at=item["lead_at"])
                        added, trouble = gated(trial)
                        why = None if not trouble else "gate: " + " | ".join(trouble)
                        if why is None:
                            base, record = trial, added
                    outcome["outcome"] = "added" if why is None else f"not added: {why}"
                    report["addenda"].append(outcome)
            if problems:
                item["refused"] = [f"gate: {p}" for p in problems]
            else:
                imported[record["impact_id"]] = record
                report["imported"].append(record["impact_id"])
                lane_tally(item["lane"])["imported"] += 1
                if record["impact_id"] != item["original_id"]:
                    report["renamed"][item["key"]] = record["impact_id"]
                if item["notes"]:
                    report["notes"][record["impact_id"]] = item["notes"]
        if "refused" in item:
            refuse(item, item["refused"])
    # A record of the curated file that came from this queue and is no longer accepted is withdrawn;
    # one that came from elsewhere (an earlier pass whose lane is gone) stays as it is.
    kept = {rid: r for rid, r in existing.items() if rid not in known_ids}
    report["withdrawn"] = sorted(rid for rid in existing if rid in known_ids and rid not in imported)
    records = sorted({**kept, **imported}.values(), key=lambda r: r["impact_id"])
    # Published side by side and possibly one incident: same country and sector, dates within three
    # days. A warning for the lead to rule on, not a refusal (within one day was refused above).
    ruled = {frozenset(pair) for pair in distinct}
    filed_as = {v: k for k, v in report["renamed"].items()}
    for i, a in enumerate(records):
        for b in records[i + 1:]:
            if (set(G._countries(a)) & set(G._countries(b)) and a.get("sector") == b.get("sector")
                    and within_a_day(a.get("date"), b.get("date"), days=3)):
                pair = [a["impact_id"], b["impact_id"]]
                keys = frozenset(filed_as.get(x, x) for x in pair)
                if not ruled & {frozenset(pair), keys, frozenset(k.split("/", 1)[-1] for k in keys)}:
                    report["possible_duplicates"].append(pair)

    # The regional context: two roles, the same patches, the build's context gate.
    known_ctx, imported_ctx = set(), {}
    for lane_dir in lane_dirs(queue):
        lane = lane_dir.name
        for cand in _rows(lane_dir / "context_entries.json", ("entries",)):
            cid = str(cand.get("id") or "")
            known_ctx.add(cid)
            verdicts, reviewed_at = verdicts_for(reviews, lane, cid, CONTEXT_ROLES)
            if not verdicts:
                report["context"]["not_reviewed"].append({"lane": lane, "candidate_id": cid})
                continue
            for v in verdicts.values():
                if (v.get("set") or {}).get("id"):
                    known_ctx.add(str(v["set"]["id"]))
            why = review_state(verdicts, CONTEXT_ROLES)
            reviewed, problems = apply_reviews(cand, verdicts, CONTEXT_ROLES) if not why else (cand, [])
            patch, lead_at = lead_patch(reviews, lane, cid) if not why else (None, None)
            if patch is not None and not problems:
                if (patch.get("set") or {}).get("id"):
                    known_ctx.add(str(patch["set"]["id"]))
                reviewed, problems = apply_lead(reviewed, patch, lead_at)
                report["lead_normalised"].append(f"{lane}/{cid}")
            if patch is None:
                lead_at = None
            if why or problems:
                report["context"]["refused"].append({"lane": lane, "candidate_id": cid, "reasons": [why] if why else problems})
                continue
            entry = {k: reviewed[k] for k in G.ENTRY_FIELDS if k in reviewed and k not in ("review", "first_published", "last_revised")}
            entry.setdefault("metric", None)
            m = entry["metric"]
            if isinstance(m, dict) and m.get("qualifier") is not None and m["qualifier"] not in G.METRIC_QUALIFIERS:
                # A lane's word in the vocabulary's spelling; "exact" is no qualifier at all.
                fixed = _qualifier(m["qualifier"], None)
                if fixed in G.METRIC_QUALIFIERS or fixed == "exact":
                    m["qualifier"] = None if fixed == "exact" else fixed
            entry["sources"] = clean_sources(entry.get("sources"))
            entry["review"] = review_block(entry, verdicts, reviewed_at, CONTEXT_ROLES, full=False, lead_at=lead_at)
            entry = stamp(entry, existing_ctx.get(entry.get("id")), date)
            entry = {k: entry[k] for k in G.ENTRY_FIELDS if k in entry}
            problems = G.context_problems([entry])
            if entry.get("id") in imported_ctx:
                problems.append("id collision with another entry")
            if problems:
                report["context"]["refused"].append({"lane": lane, "candidate_id": cid, "reasons": [f"gate: {p}" for p in problems]})
                continue
            imported_ctx[entry["id"]] = entry
            report["context"]["imported"].append(entry["id"])
            if entry["id"] != cid:
                report["renamed"][f"{lane}/{cid}"] = entry["id"]
    kept_ctx = {cid: e for cid, e in existing_ctx.items() if cid not in known_ctx}
    report["context"]["withdrawn"] = sorted(cid for cid in existing_ctx if cid in known_ctx and cid not in imported_ctx)
    entries = sorted({**kept_ctx, **imported_ctx}.values(), key=lambda e: e["id"])

    # 9. The research note.
    log, dropped = research_log(read_json(curated / "research_log.json"), lane_logs, date, held)
    report["research_log"] = {"lanes": sorted(lane_logs), "families_dropped": dropped}
    report["lead_holds"].update(held)

    for k in ("imported",):
        report[k] = sorted(report[k])
        report["context"][k] = sorted(report["context"][k])
    if write and report["collisions"]:
        # Two candidates would be published under one id. Nothing is written until the lead rules
        # (a hold in lead_holds.json, or a reviewer's reject): choosing one here would be a guess.
        print_report(report)
        raise SystemExit("import_impacts: id collision; nothing was written. " + "; ".join(
            f"{c['impact_id']} <- {', '.join(c['candidates'])}" for c in report["collisions"]))
    if write:
        write_json(curated / "events.json", {**events_doc, "records": records})
        write_json(curated / "regional_context.json", {**context_doc, "entries": entries})
        write_json(curated / "research_log.json", log)
        write_json(queue / "import_report.json", report)
    return report


def print_report(report):
    print(f"impact import, {report['date']}: {len(report['imported'])} records imported, "
          f"{len(report['refused'])} refused, {len(report['not_reviewed'])} not yet reviewed, "
          f"{len(report['withdrawn'])} withdrawn")
    for lane, t in sorted(report["by_lane"].items()):
        print(f"   {lane}: {t['imported']} imported, {t['refused']} refused, {t['not_reviewed']} not reviewed")
    for r in report["refused"]:
        print(f"   refused {r['lane']}/{r['candidate_id']}: " + " | ".join(r["reasons"]))
    for rid in report["withdrawn"]:
        print(f"   withdrawn {rid}: no longer accepted")
    c = report["context"]
    print(f"regional context: {len(c['imported'])} entries imported, {len(c['refused'])} refused, "
          f"{len(c['not_reviewed'])} not yet reviewed, {len(c['withdrawn'])} withdrawn")
    for r in c["refused"]:
        print(f"   refused {r['lane']}/{r['candidate_id']}: " + " | ".join(str(x) for x in r["reasons"]))
    for d in report["research_log"]["families_dropped"]:
        print(f"   research note: dropped a family of lane {d['lane']}: " + " | ".join(d["why"]))
    for a in report["addenda"]:
        print(f"   addendum {a['candidate_id']}#{a['ref']}: {a['outcome']}")
    for c in report["collisions"]:
        print(f"   COLLISION {c['impact_id']}: filed as {', '.join(c['candidates'])}. The import fails until one is "
              "held or rejected.")
    for a, b in report["possible_duplicates"]:
        print(f"   WARNING possible duplicate (same country and sector, dates within three days): {a} and {b}")
    if report["lead_holds"]["count"]:
        h = report["lead_holds"]
        print(f"lead holds applied: {h['count']} ({h.get('duplicates_across_lanes', 0)} duplicates across lanes, "
              f"{h.get('safety_grounds', 0)} on safety grounds, {h.get('other_grounds', 0)} on other grounds)")
    if report["renamed"]:
        print(f"ids rewritten: {len(report['renamed'])} (old and new are in the local report only)")
    if report["lead_normalised"]:
        print(f"lead normalisation read for {len(report['lead_normalised'])} records and entries")
    distinct = [x for x in report["reconcile"] if not x["outcome"].startswith("refused")]
    if report["reconcile"]:
        print(f"country-queue matches: {len(report['reconcile']) - len(distinct)} refused, {len(distinct)} ruled a "
              "different event by the lead")
    for name in report["ignored_files"]:
        print(f"   NOT READ {name}: there is no override for a record held from a country system "
              "(reconcile_distinct.json states that a match is a different event)")


def main():
    ap = argparse.ArgumentParser(description="Import reviewed impact candidates into data/curated/global_impacts.")
    ap.add_argument("--date", default=dt.date.today().isoformat(),
                    help="first_published for records new to the curated file (default: today)")
    ap.add_argument("--dry-run", action="store_true",
                    help="write nothing: print what would be imported per lane and every refusal with its reason")
    args = ap.parse_args()
    report = run(date=args.date, write=not args.dry_run)
    print_report(report)
    if args.dry_run:
        print("DRY RUN: nothing was written.")


if __name__ == "__main__":
    main()
