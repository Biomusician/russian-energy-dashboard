"""Date the impact records and context entries that a release is about to serve for the first time.

    .venv\\Scripts\\python.exe scripts\\stamp_first_published.py --date 2026-11-20 [--dry-run]

`first_published` is the date of the build that first served a record (docs/GLOBAL_IMPACT_METHODOLOGY.md
§4). The import cannot know it: it writes `null` ("pending its first release") on everything new
(scripts/import_impacts.py, step 8). The release lead runs this once, in the release commit, with
the date of the release build, and then rebuilds.

WHAT IT DOES. In `data/curated/global_impacts/events.json` and `regional_context.json`, every null
`first_published` becomes `--date`. Nothing else changes: a date already there is never touched, so
running it twice, or after a later import, changes only what is still pending.

WHAT IT REFUSES, writing nothing: a `--date` that is not a real YYYY-MM-DD date, and a `--date`
earlier than the newest `first_published` already in the files. A release cannot first serve
something before an earlier release did.

Stdlib only; every file is read and written as UTF-8.
"""

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CURATED = ROOT / "data" / "curated" / "global_impacts"
# (file, the key of its list)
FILES = (("events.json", "records"), ("regional_context.json", "entries"))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, obj):
    # The import's own format: two-space indent, UTF-8, LF newlines, a final newline.
    Path(path).write_bytes((json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def valid_date(text):
    if not isinstance(text, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return False
    try:
        dt.date.fromisoformat(text)
    except ValueError:
        return False
    return True


def stamp(date, curated=CURATED, write=True):
    """Fill every null first_published with `date`. Returns {file: {"stamped": n, "kept": n}}.
    Raises ValueError, having written nothing, for a malformed date or one that goes backwards."""
    if not valid_date(date):
        raise ValueError(f"--date {date!r} is not a YYYY-MM-DD date")
    curated = Path(curated)
    docs = {name: read_json(curated / name) for name, _ in FILES}
    dated = [row["first_published"] for name, key in FILES for row in docs[name][key]
             if row.get("first_published") is not None]
    newest = max(dated, default=None)
    if newest is not None and date < newest:
        raise ValueError(f"--date {date} is before {newest}, the newest first_published already in the files: "
                         "a release cannot first serve a record before an earlier release did")
    counts = {}
    for name, key in FILES:
        stamped = kept = 0
        for row in docs[name][key]:
            if row.get("first_published") is None:
                row["first_published"] = date
                stamped += 1
            else:
                kept += 1
        counts[name] = {"stamped": stamped, "kept": kept}
    if write:
        for name, _ in FILES:
            if counts[name]["stamped"]:
                write_json(curated / name, docs[name])
    return counts


def main():
    ap = argparse.ArgumentParser(description="Set every null first_published in the curated impact layer to the "
                                             "release build's date. Run once, by the release lead, in the release commit.")
    ap.add_argument("--date", required=True, help="the date of the release build (YYYY-MM-DD)")
    ap.add_argument("--dry-run", action="store_true", help="print what would be stamped and write nothing")
    args = ap.parse_args()
    try:
        counts = stamp(args.date, write=not args.dry_run)
    except ValueError as err:
        sys.exit(f"stamp_first_published: {err}")
    for name, c in counts.items():
        print(f"{name}: {c['stamped']} pending stamped {args.date}, {c['kept']} already dated and kept")
    if args.dry_run:
        print("DRY RUN: nothing was written.")


if __name__ == "__main__":
    main()
