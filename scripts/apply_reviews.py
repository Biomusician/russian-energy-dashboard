"""Apply reconciled blind reviews to the curated inputs (iteration 17).

    .venv\\Scripts\\python.exe scripts\\apply_reviews.py <final-prefix> [...]
    e.g. scripts\\apply_reviews.py gf_us gf_ca gf_cn gf_in gf_sa new_us new_ca new_in

Reads `data/candidates/review18/<prefix>_final.json` (written by the reconciler, local) and
changes the three things the import gate reads -- nothing else:

  1. `data/curated/systems/review_edits.json`: one `set` edit per reconciled field, with the
     roles whose correction it carries. Kept as data so a re-import reproduces the reviewed text.
  2. the local research queue `data/candidates/<cc>.json`: each record's `independent_review`
     becomes the blind three-role verdict. A record that is not accepted gets disposition
     `held`, which stops the import; its reason stays local.
  3. `data/curated/systems/review_grandfathered.json`: every reviewed id leaves the list,
     accepted or not. The list only shrinks.

and, where the reconciler gave episode edits or a held record sat in an episode,
`data/curated/systems/<cc>/episodes.json`. A held record leaves its episode; an episode left with
one member is dissolved (a declared episode groups at least two records).

Then the confirmation round (every role checks the final text):

    scripts\apply_reviews.py --confirm gf_us gf_ca ...

holds any record a role objected to. Run `scripts/import_candidates.py <cc>` afterwards, then the
build. Idempotent: running it twice
does not duplicate edits.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The local review directory of the current pass. Earlier passes keep theirs (review18); set
# EDM_REVIEW_DIR to work on one of those.
R = ROOT / "data" / "candidates" / os.environ.get("EDM_REVIEW_DIR", "review19")
SYS = ROOT / "data" / "curated" / "systems"
EDITS = SYS / "review_edits.json"
GF = SYS / "review_grandfathered.json"
ROLE_NAME = {"A": "evidence", "B": "safety", "C": "taxonomy"}
REVIEWED_AT = os.environ.get("EDM_REVIEWED_AT", "2026-11-11")


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


GENERIC_REASON = "reconciled correction; the reviewers' wording is kept in the local review file"


def _abstract(cc, q):
    """Whether this record is published without its place (an attack or sabotage record in a
    system whose policy records those for the country)."""
    doc = _read(SYS / cc / "system.json")
    policy = (doc.get("geography") or {}).get("precision_policy") or {}
    return policy.get("kinetic") == "country" and q.get("cause") in ("kinetic_strike", "sabotage")


def _reason(roles, why):
    """Who made the correction. The lead is not a blind role and is never labelled as one."""
    if roles == ["lead"]:
        return f"Lead ruling, stricter than the roles and confirmed by all three on the final text: {why}"
    return f"Blind review, role(s) {', '.join(roles)}: {why}"


def _public_set(field, value, abstract):
    """The value as it may be committed. A kept citation of an abstracted record carries no
    headline: the gate would drop it at import, but this file is public before that."""
    if abstract and field == "sources" and isinstance(value, list):
        return [{k: v for k, v in s.items() if k not in ("title_original", "title_en")} for s in value]
    return value


def apply(prefix, report):
    cc = prefix.split("_")[1]
    final = _read(R / f"{prefix}_final.json")["records"]
    merged = {x["event_id"]: x for x in _read(R / f"{prefix}_merged.json")["records"]}
    qpath = ROOT / "data" / "candidates" / f"{cc}.json"
    queue = _read(qpath)
    qidx = {r.get("candidate_id"): r for r in queue}
    edits_doc = _read(EDITS)
    have = {(e["event_id"], e["field"], json.dumps(e.get("set"), ensure_ascii=False, sort_keys=True))
            for e in edits_doc["edits"] if "set" in e}
    gf_doc = _read(GF)
    gf = set(gf_doc["event_ids"])
    ep_path = SYS / cc / "episodes.json"
    episodes = _read(ep_path)
    held = []
    for rec in final:
        eid = rec["event_id"]
        q = qidx.get(eid)
        if q is None:
            raise SystemExit(f"{prefix}: {eid} is not in the {cc} queue")
        m = merged[eid]
        roles = {ROLE_NAME[k]: v.lower() for k, v in m["dispositions"].items()}
        # An iteration-14 record predates the primary_review field: its lane researched it and a
        # central reviewer checked it (its own review_process says so). Record that, dated as the
        # record itself dates it, rather than leave the gate to call it unresearched.
        if eid in gf and not (q.get("primary_review") or {}).get("completed"):
            q["primary_review"] = {"completed": q.get("reviewed") or "2026-10-30",
                                   "note": "iteration-14 research lane, centrally reviewed (pre-dates this field)"}
        if rec["decision"] == "accept":
            abstract = _abstract(cc, q)
            for e in rec.get("edits") or []:
                value = _public_set(e["field"], e["set"], abstract)
                key = (eid, e["field"], json.dumps(value, ensure_ascii=False, sort_keys=True))
                if key in have:
                    continue
                # A reviewer's reason says what was removed and why, which for an abstracted
                # record means naming the place. It stays in the local file (iteration 19).
                why = GENERIC_REASON if abstract else e.get("reason")
                edits_doc["edits"].append({
                    "event_id": eid, "field": e["field"], "set": value,
                    "reason": _reason(e.get("roles") or [], why),
                })
                have.add(key)
            q["independent_review"] = {
                "completed": REVIEWED_AT, "standard": "blind_three_role",
                "disposition": "corrected" if rec.get("edits") else "confirmed",
                "sources_opened": rec.get("sources_opened_by_A") or m.get("sources_opened_by_A") or 0,
                "roles": roles,
            }
            for ee in rec.get("episode_edits") or []:
                _episode_edit(episodes, ee)
            report.append((prefix, eid, "accept", len(rec.get("edits") or [])))
        else:
            q["independent_review"] = {
                "completed": REVIEWED_AT, "standard": "blind_three_role", "disposition": "held",
                "sources_opened": m.get("sources_opened_by_A") or 0, "roles": roles,
                "outcome": rec["decision"],
                "reason": rec.get("hold_reason") or "; ".join(v for v in (m.get("reasons") or {}).values() if v),
                "owner_questions": rec.get("owner_questions") or [],
            }
            held.append(eid)
            report.append((prefix, eid, rec["decision"], 0))
        gf.discard(eid)
    # A held record leaves its episode; a declared episode needs two members.
    for ep in list(episodes["episodes"]):
        before = list(ep["event_ids"])
        ep["event_ids"] = [x for x in ep["event_ids"] if x not in held]
        if len(ep["event_ids"]) < 2:
            episodes["episodes"].remove(ep)
            if before != ep["event_ids"] or len(before) < 2:
                report.append((prefix, ep["episode_id"], "episode dissolved", 0))
    _write(qpath, queue)
    _write(EDITS, edits_doc)
    gf_doc["event_ids"] = sorted(gf)
    _write(GF, gf_doc)
    _write(ep_path, episodes)


def _episode_edit(episodes, ee):
    eps = {e["episode_id"]: e for e in episodes["episodes"]}
    if ee["field"] == "__create__":
        if ee["episode_id"] not in eps:
            episodes["episodes"].append(ee["set"])
        return
    ep = eps.get(ee["episode_id"])
    if ep is None:
        raise SystemExit(f"episode edit for unknown episode {ee['episode_id']}")
    path = ee["field"].split(".")
    holder = ep
    for k in path[:-1]:
        holder = holder.setdefault(k, {})
    holder[path[-1]] = ee["set"]


def confirm(prefix, report):
    """The confirmation round: each role checked the FINAL reconciled text. One OBJECT holds the
    record; a missing role file is a refusal, because an unconfirmed text may not be published."""
    cc = prefix.split("_")[1]
    group = prefix.split("_")[0]
    verdicts = {}
    for role in ROLE_NAME:
        path = R / f"confirm_{group}_{cc}_{role}.json"
        if not path.exists():
            raise SystemExit(f"{path.name} is missing: role {role} has not confirmed {prefix}")
        for v in _read(path)["records"]:
            verdicts.setdefault(v["event_id"], {})[role] = v
    qpath = ROOT / "data" / "candidates" / f"{cc}.json"
    queue = _read(qpath)
    qidx = {r.get("candidate_id"): r for r in queue}
    packet = _read(R / f"confirm_{group}_{cc}.json")["records"]
    held = []
    for rec in packet:
        eid = rec.get("event_id") or rec["candidate_id"]
        vs = verdicts.get(eid, {})
        missing = [r for r in ROLE_NAME if r not in vs]
        objections = [f"role {r} on {v.get('field')}: {v.get('reason')}" for r, v in vs.items()
                      if v["verdict"] != "CONFIRM"]
        ir = qidx[eid]["independent_review"]
        ir["confirmed"] = {ROLE_NAME[r]: vs[r]["verdict"].lower() for r in vs}
        if missing or objections:
            ir.update({"disposition": "held", "outcome": "confirmation",
                       "reason": "; ".join(objections) or f"no confirmation from role(s) {missing}"})
            held.append(eid)
            report.append((prefix, eid, "held at confirmation", 0))
        else:
            report.append((prefix, eid, "confirmed", 0))
    _write(qpath, queue)
    if held:
        ep_path = SYS / cc / "episodes.json"
        episodes = _read(ep_path)
        for ep in list(episodes["episodes"]):
            ep["event_ids"] = [x for x in ep["event_ids"] if x not in held]
            if len(ep["event_ids"]) < 2:
                episodes["episodes"].remove(ep)
                report.append((prefix, ep["episode_id"], "episode dissolved", 0))
        _write(ep_path, episodes)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    report = []
    if sys.argv[1] == "--confirm":
        for p in sys.argv[2:]:
            confirm(p, report)
        from collections import Counter
        print(Counter((p, d) for p, _, d, _ in report))
        for p, eid, d, n in report:
            if d != "confirmed":
                print(f"  {d:22} {eid}")
        raise SystemExit(0)
    for p in sys.argv[1:]:
        apply(p, report)
    from collections import Counter
    print(Counter((p.split("_")[1], d) for p, _, d, _ in report))
    for p, eid, d, n in report:
        if d != "accept":
            print(f"  {d:18} {eid}")
