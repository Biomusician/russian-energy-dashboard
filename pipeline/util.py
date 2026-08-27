"""HTTP fetching with an on-disk cache, and UTF-8-safe file IO.

Every read and write in this pipeline passes encoding="utf-8" explicitly. This
machine's Python defaults to cp1252, and the dataset is full of Cyrillic and
transliterated names -- an implicit encoding corrupts them silently, with no
exception raised. tests/test_encoding.py enforces this.
"""

import csv
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from pipeline.config import RAW

USER_AGENT = (
    "russian-energy-dashboard/0.1 (open-source research dashboard; "
    "contact via repository issues)"
)


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def read_text(path):
    return Path(path).read_text(encoding="utf-8")


def write_text(path, text):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, obj, indent=None):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        # ensure_ascii=False keeps Cyrillic readable in the emitted files rather
        # than exploding every character into a \uXXXX escape.
        json.dump(obj, fh, ensure_ascii=False, indent=indent, separators=(",", ":") if indent is None else None)


def read_csv(path):
    """Read a CSV into a list of dicts. Blank strings become None."""
    with open(path, encoding="utf-8", newline="") as fh:
        rows = []
        for row in csv.DictReader(fh):
            rows.append({k: (v if v not in ("", None) else None) for k, v in row.items()})
        return rows


def write_csv(path, rows, fieldnames):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k) for k in fieldnames})


def fetch(url, cache_name, max_age_hours=24, data=None, content_type=None):
    """GET (or POST, if `data` is given) with an on-disk cache under data/raw/.

    The cache is what makes this pipeline re-runnable without hammering Overpass or
    Wikipedia. Set max_age_hours=0 to force a refresh.
    """
    RAW.mkdir(parents=True, exist_ok=True)
    cache_path = RAW / cache_name
    if cache_path.exists() and max_age_hours > 0:
        age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
        if age_hours < max_age_hours:
            log(f"  cache hit  {cache_name} ({age_hours:.1f}h old)")
            return cache_path.read_bytes()

    log(f"  fetching   {url}")
    payload = data.encode("utf-8") if isinstance(data, str) else data
    req = urllib.request.Request(url, data=payload)
    req.add_header("User-Agent", USER_AGENT)
    if content_type:
        req.add_header("Content-Type", content_type)

    last_err = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                body = resp.read()
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(body)
            return body
        except (urllib.error.URLError, TimeoutError) as exc:
            last_err = exc
            wait = 5 * (attempt + 1)
            log(f"  retry {attempt + 1}/3 after {wait}s: {exc}")
            time.sleep(wait)

    # A stale cache beats no data at all -- the daily refresh should degrade to
    # yesterday's numbers rather than emit an empty dashboard.
    if cache_path.exists():
        log(f"  WARNING: fetch failed, using stale cache for {cache_name}")
        return cache_path.read_bytes()
    raise RuntimeError(f"fetch failed for {url}: {last_err}")


def fetch_text(url, cache_name, **kw):
    return fetch(url, cache_name, **kw).decode("utf-8")


def fetch_json(url, cache_name, **kw):
    return json.loads(fetch(url, cache_name, **kw).decode("utf-8"))
