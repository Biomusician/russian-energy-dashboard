"""Build input fingerprints (addendum §4).

WHY. The change ledger has to distinguish an asset-inventory change from a denominator change
from a source refresh from a methodology change. Those categories cannot be established from the
emitted snapshot, incidents and assets alone: two builds can differ in the scoring constants and
produce identical incidents, or refresh a vendor snapshot and produce an identical score. Without
a fingerprint of what went IN, the ledger can only report that nothing it looked at changed.

So each build stamps a hash of the logical inputs it was built from, grouped by the kind of
change each group would represent. The next build compares fingerprints and knows what class of
thing moved even when the outputs look similar.

WHAT IS DELIBERATELY NOT HASHED. Not the whole repository — a README edit is not a data change
and a ledger that said so would be noise. Only the analytical and data-contract inputs whose
change would alter what the dashboard asserts.

A missing file is recorded as missing rather than skipped. `data/raw/` is gitignored and
regenerable, so a fresh clone legitimately has none of it; recording the absence keeps a build
with no raw cache from silently looking identical to one with a full cache.
"""

import hashlib
import json

from pipeline.config import SCHEMA_VERSION

# Logical input groups. The group name IS the change category the ledger reports, so adding a
# file to the wrong group would mislabel real changes.
INPUT_GROUPS = {
    # What events we assert happened.
    "incident_corpus": [
        "data/curated/incidents.csv",
        "data/raw/wiki_deep_strike.json",
        "data/raw/wiki_refineries.json",
        "data/raw/wiki_fuel_crisis.json",
    ],
    # What we know about repair and restoration.
    "recovery_corpus": [
        "data/curated/recovery.csv",
        "data/curated/effects.csv",
    ],
    # What infrastructure exists.
    "asset_inventory": [
        "data/curated/assets_supplement.csv",
        "data/curated/refineries_supplement.csv",
    ],
    # What the index divides by.
    "denominator_inputs": [
        "data/curated/refineries_canonical.csv",
        "data/curated/region_context.csv",
    ],
    # How the index is computed. A change here moves every number at once.
    "methodology": [
        "methodology/scoring.json",
    ],
    # Canonical pipeline identity, aliases, temporal status and topology.
    "pipeline_registry": [
        "data/curated/pipeline_registry.csv",
        "data/curated/pipeline_aliases.csv",
        "data/curated/pipeline_status.csv",
        "data/curated/pipeline_topology.csv",
        "data/curated/pipeline_source_map.csv",
        "data/curated/network_nodes.csv",
    ],
    # Third-party snapshots and their vintages. Changing one is a SOURCE_REFRESH even when the
    # score does not move.
    "source_snapshots": [
        "data/curated/sources.csv",
        "data/curated/crea_snapshots.csv",
        "data/vendor/gem",
        "data/vendor/entsog",
    ],
}


def _hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _hash_dir(path):
    """Directory fingerprint over sorted (relative name, content) pairs.

    Sorted so filesystem ordering cannot change the hash, and names included so a rename is a
    change — for a vendor snapshot directory the filename usually carries the release date.
    """
    h = hashlib.sha256()
    files = sorted(p for p in path.rglob("*") if p.is_file())
    for p in files:
        h.update(p.relative_to(path).as_posix().encode("utf-8"))
        h.update(_hash_file(p).encode("ascii"))
    return h.hexdigest(), len(files)


def fingerprint(root):
    """Per-group input fingerprints for one build, plus what was missing when it ran."""
    groups = {}
    missing = []
    for group, members in INPUT_GROUPS.items():
        h = hashlib.sha256()
        present = 0
        for rel in members:
            path = root / rel
            if path.is_dir():
                digest, n = _hash_dir(path)
                h.update(rel.encode("utf-8"))
                h.update(digest.encode("ascii"))
                present += n
            elif path.is_file():
                h.update(rel.encode("utf-8"))
                h.update(_hash_file(path).encode("ascii"))
                present += 1
            else:
                missing.append(rel)
                # Recorded in the hash: a build with the file absent must not fingerprint the
                # same as one with it present but empty.
                h.update(rel.encode("utf-8"))
                h.update(b"__ABSENT__")
        groups[group] = h.hexdigest()[:16]
        groups[group + "_files"] = present

    groups["schema_version"] = SCHEMA_VERSION
    return {
        "groups": {k: v for k, v in groups.items() if not k.endswith("_files")},
        "file_counts": {k[:-6]: v for k, v in groups.items() if k.endswith("_files")},
        "missing_inputs": missing,
        "schema_version": SCHEMA_VERSION,
    }


def output_fingerprint(payloads):
    """Fingerprint of the analytic OUTPUT, so a build can be identified by what it produced.

    Deliberately excludes `snapshot.json` — it carries this value, so hashing it would be
    circular — and excludes build_time everywhere, since a rebuild of identical inputs must
    fingerprint identically or the ledger would report a change on every rerun.
    """
    h = hashlib.sha256()
    for name in sorted(payloads):
        h.update(name.encode("utf-8"))
        h.update(json.dumps(payloads[name], sort_keys=True, ensure_ascii=False,
                            default=str).encode("utf-8"))
    return h.hexdigest()[:16]


def compare(prev, curr):
    """Which input groups moved between two builds.

    Returns (changed_groups, comparable). `comparable` is False when either side carries no
    fingerprint — an older payload predates this file, and reporting "nothing changed" for it
    would be an assertion we cannot support.
    """
    if not prev or not curr:
        return [], False
    pg = (prev or {}).get("groups") or {}
    cg = (curr or {}).get("groups") or {}
    if not pg or not cg:
        return [], False
    return sorted(k for k in set(pg) | set(cg) if pg.get(k) != cg.get(k)), True
