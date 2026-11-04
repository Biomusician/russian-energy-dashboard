"""Extract what the dashboard actually SERVED on a past day (iteration 17, archive extraction).

    .venv\\Scripts\\python.exe scripts\\extract_published.py 2026-10-09 --out data/reconstruction/published-2026-10-09

The fourth way to look at the past, and deliberately not a pipeline mode: it runs no scoring code
over any corpus. It finds the build that was being served at the end of the UTC day (the
as-published history, pipeline/production_history.py), and writes that commit's payload
(`data/processed/`) out of git, byte for byte, with a provenance file saying which commit, from
when, and on what lineage evidence. Compare with:

    pipeline.run --mode reconstruction --as-of D   today's code and corpus evaluated at D
    production_history.json                         the index of served builds, not their payloads

It refuses: a day before the first reliable as-published build (the history says when); and an
output directory that is, or contains, the production payload or the web bundle.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import outputs, production_history  # noqa: E402
from pipeline.lineage import PAYLOAD_DIR  # noqa: E402


class ExtractRefused(ValueError):
    pass


def _git(*args, binary=False):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode("utf-8")


def served_on(day, history=None):
    """The as-published entry served at the end of `day`, or refuse."""
    history = history or production_history.build(ROOT)
    entry = production_history.as_published_on(history, day)
    if entry is None:
        raise ExtractRefused(f"nothing reliable was served by {day}; the as-published history starts "
                             f"{history.get('earliest_reliable_as_published_date')}")
    return entry


def extract(day, out, history=None):
    if outputs._protected(out):
        raise ExtractRefused(f"{out} is, or contains, the production payload or the web bundle")
    entry = served_on(day, history)
    sha = entry["sha"]
    files = [f for f in _git("ls-tree", "-r", "--name-only", sha, PAYLOAD_DIR).splitlines() if f]
    out = Path(out)
    for rel in files:
        dest = out / Path(rel).relative_to(PAYLOAD_DIR)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(_git("show", f"{sha}:{rel}", binary=True))
    # Integrity: the snapshot we wrote is the blob the history recorded, and says what it said.
    blob = _git("hash-object", str(out / "snapshot.json")).strip()
    if entry.get("snapshot_blob") and blob != entry["snapshot_blob"]:
        raise ExtractRefused(f"snapshot blob {blob} != recorded {entry['snapshot_blob']}")
    snap = json.loads((out / "snapshot.json").read_text(encoding="utf-8"))
    if snap.get("esdi") != entry.get("esdi") or snap.get("as_of") != entry.get("as_of"):
        raise ExtractRefused("extracted snapshot disagrees with the as-published history")
    provenance = {
        "concept": "as_published",
        "label": f"As published at the end of {day} (UTC)",
        "method": "git blobs of the served commit's payload; no code was run over any corpus",
        "day": day,
        "sha": sha,
        "served_from": entry["served_from"],
        "lineage": entry["lineage"],
        "as_of": entry["as_of"],
        "esdi": entry["esdi"],
        "files": len(files),
        "snapshot_blob": blob,
    }
    (out / "PROVENANCE.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
    return provenance


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("day", help="YYYY-MM-DD (UTC day)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    print(json.dumps(extract(a.day, a.out), ensure_ascii=False, indent=2))
