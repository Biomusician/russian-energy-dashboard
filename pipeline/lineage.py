"""Where the change ledger's "previous build" comes from (addendum §2, §3, §19).

THE PROBLEM WITH THE OBVIOUS ANSWER. `web/public/data/` still holds the last build's payload
until the mirror overwrites it, so reading it there is easy — and wrong. That directory is a
mutable worktree artefact. It can hold a frozen `--as-of` comparison run, a local experiment, a
half-finished build that was interrupted, files left over from another branch, or something
copied in by hand. A ledger built on it would answer "what changed since whatever happened to be
in this folder", and would say so with the same confidence as a real answer.

The question the ledger must actually answer is:

    WHAT CHANGED SINCE THE PREVIOUS COMMITTED PRODUCTION BUILD?

So the baseline is read out of git — an immutable, named commit — and never off disk. If that
cannot be done, the ledger says its lineage is invalid rather than quietly substituting the
worktree.

WHICH COMMIT. In order: an explicit `PRODUCTION_REF`, then `origin/main`, then `main`. On the
daily refresh runner, `origin/main` is HEAD before the bot commits — precisely the previous
committed production state, which is what §3 asks us to use deliberately.

VALID vs DEVELOPMENT. A baseline that is a genuine ancestor of HEAD proves lineage. Building on
the production branch makes it the production story; building on a feature branch makes it a
development comparison — a real answer to "what would change if this branch shipped", but not
the daily one. The distinction is published so a branch/testing mistake is visible rather than
inferred, and the UI badges it.
"""

import json
import os
import subprocess

PRODUCTION_BRANCH = "main"
PAYLOAD_DIR = "web/public/data"

# Baseline payloads read from the commit, not from disk.
BASELINE_FILES = ("snapshot.json", "incidents.json", "assets.json")


def _git(root, *args, binary=False):
    """Run git, returning None on any failure. Absent git is a degraded mode, not a crash."""
    try:
        r = subprocess.run(["git", *args], cwd=str(root), capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout if binary else r.stdout.decode("utf-8", "replace").strip()


def _resolve_baseline_ref(root):
    """The commit whose committed payload is the production baseline."""
    explicit = os.environ.get("PRODUCTION_REF")
    candidates = [explicit] if explicit else []
    candidates += [f"origin/{PRODUCTION_BRANCH}", PRODUCTION_BRANCH]
    for ref in candidates:
        if not ref:
            continue
        sha = _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
        if sha:
            return ref, sha
    return None, None


def _show_json(root, sha, relpath):
    raw = _git(root, "show", f"{sha}:{relpath}", binary=True)
    if raw is None:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except ValueError:
        return None


def resolve(root, current_as_of):
    """Find the baseline build. Returns (payloads, lineage) — payloads is None when invalid.

    `lineage` is always returned, and always says why: a ledger that cannot prove what it is
    comparing against must be able to display that fact rather than a plausible delta.
    """
    lineage = {
        "source": "git",
        "production_branch": PRODUCTION_BRANCH,
        "baseline_ref": None,
        "previous_commit": None,
        "previous_commit_subject": None,
        "previous_commit_date": None,
        "current_branch": None,
        "current_commit": None,
        "worktree_dirty": None,
        "on_production_branch": False,
        "previous_is_ancestor": False,
        "valid": False,
        "mode": "invalid",
        "reason": None,
        "worktree_payload_differs_from_baseline": None,
    }

    if _git(root, "rev-parse", "--git-dir") is None:
        lineage.update(source="none", reason="not a git repository, or git is unavailable")
        return None, lineage

    lineage["current_branch"] = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    lineage["current_commit"] = _git(root, "rev-parse", "HEAD")
    status = _git(root, "status", "--porcelain")
    lineage["worktree_dirty"] = bool(status)

    ref, sha = _resolve_baseline_ref(root)
    if not sha:
        lineage["reason"] = (
            f"no production baseline: neither PRODUCTION_REF, origin/{PRODUCTION_BRANCH} "
            f"nor {PRODUCTION_BRANCH} resolves to a commit")
        return None, lineage

    lineage["baseline_ref"] = ref
    lineage["previous_commit"] = sha
    lineage["previous_commit_subject"] = _git(root, "log", "-1", "--format=%s", sha)
    lineage["previous_commit_date"] = _git(root, "log", "-1", "--format=%cI", sha)
    lineage["on_production_branch"] = lineage["current_branch"] == PRODUCTION_BRANCH

    # Ancestry is what proves the two builds are on one lineage. A baseline on a diverged branch
    # is not a predecessor of this build and must not be presented as one.
    is_ancestor = _git(root, "merge-base", "--is-ancestor", sha, "HEAD") is not None
    lineage["previous_is_ancestor"] = is_ancestor
    if not is_ancestor:
        lineage["reason"] = (
            f"baseline {sha[:8]} is not an ancestor of HEAD; these builds are on diverged "
            "histories and one is not the predecessor of the other")
        return None, lineage

    payloads = {}
    for name in BASELINE_FILES:
        doc = _show_json(root, sha, f"{PAYLOAD_DIR}/{name}")
        if doc is None:
            lineage["reason"] = f"commit {sha[:8]} carries no readable {PAYLOAD_DIR}/{name}"
            return None, lineage
        payloads[name] = doc

    prev_as_of = (payloads["snapshot.json"] or {}).get("as_of")
    if prev_as_of and current_as_of and prev_as_of > current_as_of:
        # A production "since last build" story never runs backwards. This happens when a
        # current build is deliberately evaluated at an earlier date, which belongs in testing.
        lineage["reason"] = (
            f"baseline is evaluated at {prev_as_of}, later than this build's {current_as_of}; "
            "a production comparison never runs backwards")
        lineage["mode"] = "backward"
        return payloads, lineage

    lineage["valid"] = True
    lineage["mode"] = "production" if lineage["on_production_branch"] else "development"
    if lineage["mode"] == "development":
        lineage["reason"] = (
            f"building on branch '{lineage['current_branch']}', not {PRODUCTION_BRANCH}: this "
            "compares against the last production build, which answers what would change if "
            "this branch shipped — not the daily production story")
    return payloads, lineage


def worktree_differs(root, baseline_snapshot):
    """Whether the on-disk payload disagrees with the committed baseline.

    Reported, never acted on. It is the signal that someone has a frozen or experimental build
    sitting in the worktree — exactly the artefact that must not become a baseline.
    """
    path = root / PAYLOAD_DIR / "snapshot.json"
    if not path.is_file() or not baseline_snapshot:
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            disk = json.load(fh)
    except (OSError, ValueError):
        return None
    return (disk.get("as_of"), disk.get("build_time")) != (
        baseline_snapshot.get("as_of"), baseline_snapshot.get("build_time"))
