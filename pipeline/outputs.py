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
from pathlib import Path

from pipeline.config import PROCESSED, ROOT, WEB_DATA

MODES = ("current", "reconstruction", "fixture")
# Directories a non-current build must never write into: the committed production payload, the
# web bundle Vercel serves, and the working-tree root above them.
PROTECTED = (PROCESSED, WEB_DATA)


class OutputRefused(ValueError):
    """A build was asked to write where its mode must not."""


def _inside(path, parent):
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False


def _protected(path):
    """Inside a protected root, or an ancestor of one (writing `data/` or `web/` would write
    beside, and under some layouts over, the production payload)."""
    p = Path(path).resolve()
    return any(_inside(p, root) or _inside(root, p) for root in PROTECTED)


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
    if _protected(output_root):
        if mode == "reconstruction" and allow_protected_root:
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
