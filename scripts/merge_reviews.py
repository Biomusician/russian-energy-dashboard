"""Combine the three blind reviews of a record into one outcome (iteration 17).

    .venv\\Scripts\\python.exe scripts\\merge_reviews.py <packet-prefix> [<packet-prefix> ...]
    e.g. scripts\\merge_reviews.py gf_us gf_ca gf_cn gf_in gf_sa

Reads `data/candidates/review18/<prefix>_{A,B,C}.json` (local, gitignored) and writes
`<prefix>_merged.json` beside them. Writes nothing that is published.

THE RULE (docs/REVIEW_GOVERNANCE.md §7). Three roles review blind: A evidence, B safety and
abstraction, C taxonomy and episodes. There is no majority vote. A record goes forward only if
every role accepts it, with or without corrections:

    any REJECT                     -> reject
    any HOLD or DUPLICATE          -> hold
    any NEEDS_HUMAN_DECISION       -> owner      (held until the owner rules)
    all ACCEPT / ACCEPT_WITH_CORR. -> accept, with every correction applied

Corrections from different roles to DIFFERENT fields are applied as they stand. Two roles that
both rewrote the SAME field have not disagreed about the record, but neither has seen the other's
text, so the field is RECONCILED: one text that makes every correction and adds nothing, which
the roles then confirm. A reconciliation that cannot honour both is a material disagreement and
the record is held. An id rename is never applied here: ids are permanent references (episodes,
the build ledger, as-published history), so a proposed rename goes to the owner.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The local review directory of the current pass. Earlier passes keep theirs (review18); set
# EDM_REVIEW_DIR to work on one of those.
R = ROOT / "data" / "candidates" / os.environ.get("EDM_REVIEW_DIR", "review19")
ROLES = ("A", "B", "C")
PASS = ("ACCEPT", "ACCEPT_WITH_CORRECTION")
NOT_APPLIED_HERE = ("event_id",)   # ids are permanent; renames go to the owner


def outcome(dispositions):
    ds = set(dispositions.values())
    if "REJECT" in ds:
        return "reject"
    if ds & {"HOLD", "DUPLICATE"}:
        return "hold"
    if "NEEDS_HUMAN_DECISION" in ds:
        return "owner"
    # An unknown disposition (a misspelling such as "ACCEPT_WITH_CORRECTIONS") is never read as
    # acceptance. A real check, not an assert: `python -O` strips asserts (lane-G red team).
    unknown = ds - set(PASS)
    if unknown:
        raise ValueError(f"unknown disposition(s) {sorted(unknown)}; expected {PASS} or a hold/reject")
    if set(dispositions) != set(ROLES):
        raise ValueError(f"a verdict from every role is required: got {sorted(dispositions)}")
    return "accept"


def merge(prefix):
    packet = json.loads((R / f"{prefix}.json").read_text(encoding="utf-8"))["records"]
    by_role = {}
    for role in ROLES:
        doc = json.loads((R / f"{prefix}_{role}.json").read_text(encoding="utf-8"))
        by_role[role] = {x["event_id"]: x for x in doc["records"]}
    out = []
    for rec in packet:
        eid = rec.get("event_id") or rec["candidate_id"]   # a new record has no event id yet
        missing = [r for r in ROLES if eid not in by_role[r]]
        if missing:
            raise SystemExit(f"{prefix}: {eid} has no review from role(s) {missing}")
        reviews = {r: by_role[r][eid] for r in ROLES}
        disp = {r: reviews[r]["disposition"] for r in ROLES}
        o = outcome(disp)
        fields = {}
        for r in ROLES:
            for c in reviews[r].get("corrections") or []:
                fields.setdefault(c["field"], []).append({"role": r, "new_value": c.get("new_value"),
                                                          "why": c.get("why")})
        applied, reconcile, deferred = {}, {}, {}
        for f, cs in fields.items():
            if f in NOT_APPLIED_HERE:
                deferred[f] = cs
            elif len({c["role"] for c in cs}) == 1 and len(cs) == 1:
                applied[f] = cs[0]
            else:
                reconcile[f] = cs
        out.append({
            "event_id": eid,
            "outcome": o,
            "dispositions": disp,
            "reasons": {r: reviews[r].get("rationale") for r in ROLES
                        if disp[r] not in PASS},
            "sources_opened_by_A": sum(1 for s in reviews["A"].get("sources_opened") or [] if s.get("opened")),
            "applied": applied,
            "reconcile": reconcile,
            "deferred_to_owner": deferred,
            "record": rec,
        })
    path = R / f"{prefix}_merged.json"
    path.write_text(json.dumps({"packet": prefix, "records": out}, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")
    counts = {}
    for x in out:
        counts[x["outcome"]] = counts.get(x["outcome"], 0) + 1
    print(f"{path.relative_to(ROOT)}: {counts}; reconcile {sum(1 for x in out if x['reconcile'] and x['outcome'] == 'accept')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for p in sys.argv[1:]:
        merge(p)
