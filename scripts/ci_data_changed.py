"""Decide whether a freshly built dataset differs from HEAD in any SUBSTANTIVE way.

Exit 0 (a shell "true") if it does; exit 1 if the only difference is the per-run
wall-clock ``build_time``. The daily-refresh Action calls this before committing, so a
rerun that produced no real data change does not create an empty "daily refresh" commit.

``build_time`` is the only per-run wall-clock field in the emitted data. Everything else
that moves day to day — ``as_of`` and the recency-weighted index — moves only because the
data genuinely aged, which is a real change worth committing. This is deliberately narrow:
it suppresses same-day reruns, not legitimate daily drift.
"""

import json
import subprocess
import sys
from pathlib import Path

EMITTED_DIRS = ("data/processed", "web/public/data")
VOLATILE_TOP_KEYS = ("build_time",)  # per-run wall-clock; not a data change


def normalise(text: str) -> str:
    """Canonical JSON with per-run volatile top-level fields removed, so two runs over
    identical data compare equal. Non-JSON is compared verbatim."""
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return text
    if isinstance(obj, dict):
        for k in VOLATILE_TOP_KEYS:
            obj.pop(k, None)
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def _head_version(relpath: str):
    """The committed version of a file, or None if it is new (not in HEAD)."""
    r = subprocess.run(["git", "show", f"HEAD:{relpath}"],
                       capture_output=True, text=True, encoding="utf-8")
    return r.stdout if r.returncode == 0 else None


def substantive_change() -> bool:
    for d in EMITTED_DIRS:
        for fp in sorted(Path(d).glob("*")):
            if not fp.is_file():
                continue
            rel = fp.as_posix()
            head = _head_version(rel)
            if head is None:
                print(f"substantive: new file {rel}")
                return True
            if normalise(fp.read_text(encoding="utf-8")) != normalise(head):
                print(f"substantive: {rel} changed")
                return True
    print("no substantive change (only build_time differs, if anything)")
    return False


if __name__ == "__main__":
    sys.exit(0 if substantive_change() else 1)
