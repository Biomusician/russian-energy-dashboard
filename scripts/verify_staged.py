"""Refuse a refresh commit whose staged tree is not a complete, self-consistent build.

WHAT THIS CHECKS, AND WHY IT IS NOT THE KIND OF GATE THAT CAUSED THE LAST OUTAGE.

On 2026-09-21 a test whose assertion was mathematically false began failing, `refresh.yml`
skipped its commit, and the dashboard served eleven-day-old figures while building correctly
every morning. The lesson recorded in `ci.yml` is that the set of things able to freeze
publication must be as small as the job that publishes.

This check belongs inside that small set, because it is not an assertion about the DATA. It
asks one structural question: does the commit about to be made contain every artifact this
build declared, all from this same build? A commit that fails it would publish a new snapshot
beside a stale document — which is the defect this whole mechanism exists to prevent, and which
shipped in twenty-nine consecutive commits. Publishing an internally inconsistent artifact is
worse than publishing nothing, so blocking is right here in a way it was not for `E <= esdi`.

It also cannot rot the way that assertion did. It compares a declared set against `git`'s own
index; there is no arithmetic in it, and no value in it becomes false as time passes.

Run after `git add`, before `git commit`. Exits non-zero with the missing paths named.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline.artifacts import GENERATED_DOCS, required_paths  # noqa: E402

PROCESSED_REL = "data/processed"
WEB_DATA_REL = "web/public/data"


def _git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout


def _lines(text):
    return {ln.strip() for ln in text.splitlines() if ln.strip()}


def check(root=REPO_ROOT):
    """Return a list of human-readable problems; empty means the commit is safe to make.

    `root` is a parameter so the staging boundary can be exercised in a throwaway repository
    rather than only in the one it protects. Testing the real commit boundary was the whole
    point: the old guard validated the worktree the build had just written, which is the layer
    before the one that ships.
    """
    root = Path(root)
    problems = []
    staged = _lines(_git(root, "diff", "--cached", "--name-only"))
    tracked = _lines(_git(root, "ls-files"))

    # 1. Every required artifact must be either staged now or already committed. A required
    #    artifact that is neither is about to be published absent.
    for path in required_paths():
        if path not in staged and path not in tracked:
            problems.append(f"required artifact is neither staged nor tracked: {path}")

    # 2. A generated document must never be left behind by a build that moved the payload.
    #    This is exactly the 2026-09-05 defect: snapshot.json staged, CURRENT_STATE.md not.
    payload_moved = any(p.startswith(PROCESSED_REL + "/") for p in staged)
    if payload_moved:
        for doc in GENERATED_DOCS:
            if not doc["refresh_managed"]:
                continue
            if not (root / doc["path"]).exists():
                problems.append(f"generated doc missing from the worktree: {doc['path']}")
                continue
            # Unmodified is fine: the doc renders from analytic content with no wall clock, so a
            # rebuild that changed nothing analytic legitimately leaves it byte-identical.
            # Modified-but-unstaged is the defect.
            dirty = _lines(_git(root, "diff", "--name-only", "--", doc["path"]))
            if dirty and doc["path"] not in staged:
                problems.append(
                    f"{doc['path']} was regenerated but is NOT staged — the commit would "
                    f"publish a new payload beside a stale document (written by "
                    f"{doc['producer']}, guarded by {doc['validated_by']})")

    # 3. One build, not two. The mirror and the manifest must agree with the snapshot, so a
    #    partial rebuild or an interrupted mirror cannot ship as a coherent set.
    try:
        snap = json.loads((root / PROCESSED_REL / "snapshot.json").read_text(encoding="utf-8"))
        manifest = json.loads(
            (root / PROCESSED_REL / "data_manifest.json").read_text(encoding="utf-8"))
        mirror = json.loads((root / WEB_DATA_REL / "snapshot.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        problems.append(f"could not read the build-identity triple: {exc}")
        return problems

    if manifest.get("build_time") != snap.get("build_time"):
        problems.append(f"data_manifest.json is from a different build than snapshot.json "
                        f"({manifest.get('build_time')} vs {snap.get('build_time')})")
    if mirror.get("build_time") != snap.get("build_time"):
        problems.append(f"the web/public/data mirror is from a different build than "
                        f"data/processed ({mirror.get('build_time')} vs {snap.get('build_time')})")
    if mirror.get("as_of") != snap.get("as_of"):
        problems.append(f"mirror as_of {mirror.get('as_of')} != "
                        f"processed as_of {snap.get('as_of')}")

    return problems


if __name__ == "__main__":
    found = check()
    if found:
        print("REFUSING THE COMMIT — the staged tree is not a complete build:", file=sys.stderr)
        for p in found:
            print(f"  * {p}", file=sys.stderr)
        sys.exit(1)
    print("staged tree carries every declared artifact, all from one build")
