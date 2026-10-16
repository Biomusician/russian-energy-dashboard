"""Markdown for the GitHub Actions run summary, so a maintainer can see what a refresh did
without opening the log.

Between 2026-09-21 and 2026-10-01 this workflow failed eleven times. Every run built the
dataset correctly and every run discarded it, and the only way to know which step had failed
was to open the log. Between 2026-09-05 and 2026-10-15 it succeeded forty-one times while
committing a stale `docs/CURRENT_STATE.md`, and the run page said nothing at all. A run that
cannot report what it published is not observable.

Reads only what is on disk, so it is safe to call whether the build, the tests or the commit
step failed. Prints to stdout; the workflow redirects it into $GITHUB_STEP_SUMMARY.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROCESSED = ROOT / "data" / "processed"


def _json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _git(*args):
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                              encoding="utf-8", check=True).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return ""


def main():
    out = []
    snap = _json(PROCESSED / "snapshot.json")
    if snap is None:
        print("## Refresh\n\nNo snapshot on disk — the build did not reach its emit step.")
        return

    out.append("## Refresh\n")
    out.append(f"| | |\n|---|---|")
    out.append(f"| as_of | **{snap.get('as_of')}** |")
    out.append(f"| ESDI | **{snap.get('esdi')}** |")
    out.append(f"| events | **{snap.get('incident_total')}** |")
    out.append(f"| build_time | {snap.get('build_time')} |")
    out.append(f"| schema | {snap.get('schema_version')} |")

    # Did anything actually get committed, and did the full declared set go with it?
    head = _git("log", "-1", "--format=%h %an %s")
    out.append(f"| HEAD | `{head}` |")
    dirty = [ln for ln in _git("status", "--porcelain").splitlines() if ln.strip()]
    if dirty:
        out.append(f"| uncommitted | {len(dirty)} path(s) — see below |")

    # The change ledger already classifies the build-to-build delta; surface its headline
    # rather than recomputing one here.
    ledger = _json(PROCESSED / "build_changes.json") or {}
    delta = ledger.get("esdi_delta")
    if delta is not None:
        out.append(f"| ESDI delta vs previous build | **{delta:+.2f}** |")
    for key, label in (("incidents_added", "incidents added"),
                       ("incidents_revised", "incidents revised"),
                       ("recovery_added", "recovery evidence added")):
        rows = ledger.get(key)
        if rows:
            out.append(f"| {label} | {len(rows) if isinstance(rows, list) else rows} |")
    lineage = ledger.get("lineage") or ledger.get("lineage_status")
    if lineage:
        out.append(f"| ledger lineage | {lineage} |")

    out.append("")

    warnings = snap.get("parser_warnings") or []
    if warnings:
        out.append(f"### Parser warnings ({len(warnings)})\n")
        for w in warnings[:10]:
            text = w if isinstance(w, str) else json.dumps(w, ensure_ascii=False)
            out.append(f"- {text[:300]}")
        if len(warnings) > 10:
            out.append(f"- …and {len(warnings) - 10} more")
        out.append("")

    if dirty:
        out.append("### Uncommitted after staging\n")
        out.append("A generated artifact left out of the commit is the defect this workflow "
                   "shipped for forty-one days. These paths are dirty and were not staged:\n")
        for ln in dirty[:25]:
            out.append(f"- `{ln.strip()}`")
        out.append("")

    print("\n".join(out))


if __name__ == "__main__":
    main()
