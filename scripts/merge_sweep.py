"""Merge one research pass's candidate files into the local queues.

    .venv\\Scripts\\python.exe scripts\\merge_sweep.py                      # iteration 18's pass
    .venv\\Scripts\\python.exe scripts\\merge_sweep.py gulf19 19 ir iq ...  # <dir> <iteration> <cc ...>

Reads `data/candidates/<dir>/<cc>_*_candidates.json` and adds each record to
`data/candidates/<cc>.json`. Both are local and gitignored. Publishes nothing: a record still has
to pass blind review and the import gate.

A candidate whose id already exists replaces the queue record only if that record was never
accepted by review (a lead the researcher has now resolved). A published record is never touched
from here. LEAD_HOLDS records the lead's decision to be stricter than a researcher, which the
governance allows; the reverse is not allowed.
"""
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = ROOT / "data" / "candidates"
PASSING = ("confirmed", "corrected")

LEAD_HOLDS = {
    "cn-2024-06-15-guangdong-flood-outage":
        "388,000 is households that experienced outages over about three days, not a stated simultaneous peak: clause 5 needs a peak",
    "in-2024-09-12-tamil-nadu-chennai-grid-outage":
        "a MW figure with no customer count; the same question held Mumbai 2022 for the owner",
}


def main(sweep="sweep18", iteration="18", countries=("us", "ca", "cn", "in", "sa")):
    for cc in countries:
        qpath = CANDIDATES / f"{cc}.json"
        # A country onboarded in this pass has no queue yet.
        queue = json.loads(qpath.read_text(encoding="utf-8")) if qpath.exists() else []
        index = {r.get("candidate_id"): i for i, r in enumerate(queue)}
        added = replaced = kept = 0
        for path in sorted(glob.glob(str(CANDIDATES / sweep / f"{cc}_*_candidates.json"))):
            for r in json.loads(Path(path).read_text(encoding="utf-8")):
                cid = r.get("candidate_id")
                # Always this pass's tag: a researcher's own spelling of it would drop the record
                # from the pass's packets and counts.
                r["research_pass"] = f"iteration-{iteration}-{cc}"
                r["found_by"] = Path(path).name.replace("_candidates.json", "")
                if cid in LEAD_HOLDS and r.get("suggested_disposition") == "accept":
                    r["suggested_disposition"] = "held"
                    r["disposition_reason"] = "lead hold: " + LEAD_HOLDS[cid]
                if cid in index:
                    old = queue[index[cid]]
                    published = (old.get("independent_review") or {}).get("disposition") in PASSING
                    if published:
                        kept += 1
                        continue
                    queue[index[cid]] = {**r, "supersedes_earlier_candidate": True}
                    replaced += 1
                else:
                    index[cid] = len(queue)
                    queue.append(r)
                    added += 1
        qpath.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(cc, f"added {added}, replaced unpublished {replaced}, left published alone {kept}, queue {len(queue)}")


if __name__ == "__main__":
    if len(sys.argv) > 3:
        main(sys.argv[1], sys.argv[2], tuple(sys.argv[3:]))
    else:
        main()
