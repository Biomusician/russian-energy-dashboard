"""Build the confirmation packets of a blind review (iteration 19).

    .venv\\Scripts\\python.exe scripts\\confirm_packets.py new_iq new_kw ...

Run after `scripts/apply_reviews.py`. For every record the reconciler accepted, writes the text
that WILL be published -- the queue record with every reviewed edit applied and then passed
through the import gate, so an attack record appears as the gate will publish it, with no
facility and with the citations the gate keeps -- to
`data/candidates/review19/confirm_<group>_<cc>.json` (local, gitignored). The three roles confirm
or object to that text and nothing else (`docs/REVIEW_GOVERNANCE.md` §7).

A record the gate itself would hold is listed under `held_by_gate` with the reason and is not
sent for confirmation: nobody should confirm a text that cannot be published.

Before iteration 19 these packets were assembled by hand, which is how a confirmation could have
been given on a text the gate later changed.
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import build_systems  # noqa: E402

R = ROOT / "data" / "candidates" / os.environ.get("EDM_REVIEW_DIR", "review19")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def packet(prefix, imp=None):
    imp = imp or _load("import_candidates")
    group, cc = prefix.split("_")[0], prefix.split("_")[1]
    final = json.loads((R / f"{prefix}_final.json").read_text(encoding="utf-8"))["records"]
    queue = json.loads((ROOT / "data" / "candidates" / f"{cc}.json").read_text(encoding="utf-8"))
    edits = json.loads(imp.EDITS.read_text(encoding="utf-8"))["edits"]
    units = build_systems.units(cc, build_systems.load_admin1(), build_systems.load_admin0())
    doc = json.loads((ROOT / "data" / "curated" / "systems" / cc / "system.json").read_text(encoding="utf-8"))
    policy = doc["geography"].get("precision_policy")
    if policy:
        policy = {**policy, "unit_words": imp.unit_words(build_systems.unit_name_rows(doc, units))}
    campaigns = build_systems.load_campaigns()
    by_id = {r.get("candidate_id"): r for r in queue}
    records, held = [], []
    for rec in final:
        if rec["decision"] != "accept":
            continue
        r = imp.apply_edits(by_id[rec["event_id"]], edits)
        why = imp.review(cc, r, {u[0] for u in units}, policy=policy)
        ev = None if why else imp.to_event(cc, r, campaigns=campaigns, policy=policy)
        if ev is not None and not ev["sources"]:
            why = "no citation is left after the gate"
        if why:
            held.append({"event_id": rec["event_id"], "reason": why})
            continue
        ev.pop("review", None)
        records.append({"event_id": rec["event_id"], "published_event_id": ev.pop("event_id"), **ev,
                        "changed_fields": sorted({e["field"] for e in rec.get("edits") or []})})
    out = {"packet": f"confirm_{group}_{cc}",
           "note": "The final text as the import gate will publish it. Confirm or object; propose no wording.",
           "records": records, "held_by_gate": held}
    path = R / f"confirm_{group}_{cc}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{path.relative_to(ROOT)}: {len(records)} to confirm, {len(held)} held by the gate")
    for h in held:
        print(f"   held {h['event_id']}: {h['reason']}")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for p in sys.argv[1:]:
        packet(p)
