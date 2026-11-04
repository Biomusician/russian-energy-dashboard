"""Where a build writes, and what kind of build it is (iteration 17).

THE DEFECT THIS REMOVES. Until iteration 16 every build wrote to `data/processed/`, and whether a
build was a reconstruction was inferred from `--as-of` being in the past. A reconstruction of
2026-08-28 therefore overwrote the production payload in the working tree, and three guards (a
label, a skipped CURRENT_STATE rewrite, a test that refused a committed reconstruction) stood
between that and a release. Guards around a shared directory are a memory test. This module
removes the shared directory instead.

A build now declares its MODE, and the mode decides everything that differs:

    mode             as_of          output root                     mirror   CURRENT_STATE  ledger
    current          today          data/processed (only)            yes      yes            vs production
    reconstruction   before today   anywhere else (required)         never    never          unavailable
    fixture          any            anywhere else (required)         never    never          unavailable

`plan()` validates a requested build once, before any work, and refuses the dangerous
combinations: a reconstruction or fixture into a protected root, a current build at a past date,
a current build anywhere but `data/processed`. A reconstruction may be written into a protected
root only with an explicit override, and even then it never mirrors, never rewrites
CURRENT_STATE and never computes a production ledger. Every writer asks `processed()` for its
directory; nothing else in the pipeline may name `PROCESSED` for writing (a test enforces it).

Archive extraction — reading what a past deployed build served — is not a pipeline mode at all:
it runs no code over the corpus. See `scripts/extract_published.py`.
"""
import os
from pathlib import Path

from pipeline.config import PROCESSED, ROOT, WEB_DATA

MODES = ("current", "reconstruction", "fixture")
# Directories a non-current build must never write into: the committed production payload, the
# web bundle Vercel serves, and the working-tree root above them.
PROTECTED = (PROCESSED, WEB_DATA)
# The one place inside the repository a reconstruction or fixture may write (gitignored).
RECONSTRUCTION_DIR = ROOT / "data" / "reconstruction"


class OutputRefused(ValueError):
    """A build was asked to write where its mode must not."""


def _inside(path, parent):
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False


def _same(a, b):
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def _existing_chain(path):
    """`path` and its ancestors, those that exist."""
    p = Path(path).resolve()
    return [x for x in (p, *p.parents) if x.exists()]


def _alias_prefix(path):
    # Extended-length, device and UNC spellings (a leading double backslash) can name a local
    # directory under a prefix
    # that resolve() does not normalise; an output root never needs one (lane-D red team).
    s = str(path).replace("/", "\\")
    return s.startswith("\\\\")


def _protected(path):
    """Inside a protected root, or an ancestor of one (writing `data/` or `web/` would write
    beside, and under some layouts over, the production payload).

    Compared by path AND by filesystem identity: a string comparison alone let
    a UNC spelling of the local data/processed through (iteration 17, lane-D red team)."""
    if _alias_prefix(path):
        return True
    p = Path(path).resolve()
    if any(_inside(p, root) or _inside(root, p) for root in PROTECTED):
        return True
    for root in PROTECTED:
        root_chain = [Path(root).resolve(), *Path(root).resolve().parents]
        for anc in _existing_chain(p):
            if _same(anc, root):
                return True          # path is inside root
        if p.exists() and any(_same(p, r) for r in root_chain if r.exists()):
            return True              # path is root or one of its ancestors
    return False


def plan(mode, as_of, today, output_root=None, allow_protected_root=False):
    """Validate a requested build and return what it may do. Raises OutputRefused."""
    if mode not in MODES:
        raise OutputRefused(f"unknown build mode {mode!r}; one of {MODES}")
    if mode == "current":
        if as_of != today:
            raise OutputRefused(
                f"a current build is for today ({today}); --as-of {as_of} is a past date. A past "
                "date is a reconstruction: pass --mode reconstruction --output-root <scratch dir>.")
        if output_root is not None and Path(output_root).resolve() != PROCESSED.resolve():
            raise OutputRefused("a current build writes only to data/processed")
        return {"mode": mode, "root": PROCESSED, "mirror_web": True, "write_current_state": True,
                "production_ledger": True}
    if output_root is None:
        raise OutputRefused(f"a {mode} build needs an explicit --output-root outside data/processed")
    if mode == "reconstruction" and as_of >= today:
        raise OutputRefused(f"a reconstruction is for a past date; {as_of} is not before {today}")
    # Inside the repository a non-current build may write only under data/reconstruction/
    # (gitignored). Anywhere else in the tree is someone's source of truth: a root of data/curated
    # would have written each country's events.json over its curated file (iteration 17,
    # test-architecture red team). Outside the repository (a scratch dir, a test's tmp_path) is fine.
    resolved = Path(output_root).resolve()
    in_repo = _inside(resolved, ROOT) or any(_same(a, ROOT) for a in _existing_chain(resolved))
    if in_repo and not _protected(output_root) and not _inside(resolved, RECONSTRUCTION_DIR):
        raise OutputRefused(f"a {mode} build may write inside the repository only under "
                            f"data/reconstruction/; {output_root} is not")
    if _protected(output_root):
        # The override names exactly the working-tree payload, never the served bundle, the repo
        # root or an alias of either (lane-D red team).
        if (mode == "reconstruction" and allow_protected_root and not _alias_prefix(output_root)
                and _same(Path(output_root).resolve(), PROCESSED)):
            pass  # explicit, deliberate, and still never mirrored or recorded as current
        else:
            raise OutputRefused(
                f"a {mode} build may not write into {output_root}: that is the production payload, "
                "the web bundle or a directory containing them"
                + (". Pass --allow-protected-root only if you mean to overwrite the working-tree "
                   "payload, and rebuild the current build before committing." if mode == "reconstruction" else "."))
    return {"mode": mode, "root": Path(output_root), "mirror_web": False, "write_current_state": False,
            "production_ledger": False}


_target = {"mode": "current", "root": PROCESSED, "mirror_web": True, "write_current_state": True,
           "production_ledger": True}


def set_target(p):
    """Install a plan for the rest of this process. Called once, by pipeline.run."""
    _target.clear()
    _target.update(p)
    Path(p["root"]).mkdir(parents=True, exist_ok=True)


def processed():
    """The directory every writer in this build writes to."""
    return Path(_target["root"])


def mode():
    return _target["mode"]


def grants(capability):
    """Whether the installed plan allows `capability`."""
    return bool(_target.get(capability))


def require(capability):
    """Raise unless the installed plan grants `capability` (mirror_web, write_current_state,
    production_ledger). The second line of defence: even a caller that forgot to check the plan
    cannot mirror a reconstruction or rewrite CURRENT_STATE from one."""
    if not grants(capability):
        raise OutputRefused(f"a {_target['mode']} build may not {capability.replace('_', ' ')}")
