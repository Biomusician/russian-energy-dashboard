"""Reconcile GEM tracker rows against the canonical pipeline registry.

    python -m pipeline.reconcile_gem            # writes the proposal + review rows
    python -m pipeline.reconcile_gem --report   # print only

THE RULE THIS FILE EXISTS TO ENFORCE: source identity beats name similarity.

Iteration 10 already has one scar from ignoring that — a substring match let `Ukhta–Torzhok 1`
swallow strings 2 and 3, because "Ухта — Торжок 1" is a prefix of nothing but "Ухта — Торжок" is a
substring of both. So this matcher does exactly one automatic thing: it compares NORMALISED FULL
NAMES for equality. No substring containment, no fuzzy ratio, no token overlap. Everything that is
not an exact normalised hit goes to a human in `data/review/pipeline_match_review.csv`.

GEM splits a pipeline into per-country / per-phase segments that share `PipelineName` and differ by
`ProjectID`. So one canonical entity legitimately maps to MANY GEM rows: that is `aggregates`, not
a duplicate, and it is why the source map is many-to-many.
"""

import argparse
import collections
import csv
import json
import re
import sys
from pathlib import Path

from pipeline.pipeline_registry import load_registry, MATCH_CONFIDENCE
from pipeline.util import log

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "data" / "vendor" / "gem"
REVIEW = ROOT / "data" / "review" / "gem_match_review.csv"
PROPOSAL = ROOT / "data" / "review" / "gem_source_map_proposal.csv"

# GEM appends a commodity suffix to nearly every name. Stripping it is normalisation, not matching:
# it removes a token GEM adds uniformly, rather than discarding a distinguishing word.
SUFFIX = re.compile(
    r"\s+(gas|oil|product|condensate|ngl|petroleum products?|natural gas)?\s*pipeline\s*$",
    re.IGNORECASE)


def normalise(name):
    """Fold to a comparable key WITHOUT discarding anything that distinguishes two pipelines.

    Digits are kept deliberately: `Ukhta-Torzhok 1` and `Ukhta-Torzhok 2` must not collide.
    Dash variants are unified because sources disagree on hyphen vs en-dash vs em-dash for the
    same pipeline, and that is orthography rather than identity.
    """
    if not name:
        return ""
    s = SUFFIX.sub("", str(name)).strip()
    s = s.replace("–", "-").replace("—", "-").replace("‒", "-")
    s = s.replace("‑", "-").replace(" ", " ")
    s = re.sub(r"\s*-\s*", "-", s)
    s = re.sub(r"[^\w\s\-]", "", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip().casefold()


def registry_keys(entities):
    """normalised name/alias -> [canonical_id]. A key hitting >1 entity is AMBIGUOUS, never auto."""
    keys = collections.defaultdict(set)
    for e in entities:
        for label in [e["canonical_name"]] + list(e.get("aliases") or []):
            k = normalise(label)
            if k:
                keys[k].add(e["canonical_pipeline_id"])
    return {k: sorted(v) for k, v in keys.items()}


def load_gem():
    rows = []
    for tracker in ("ggit", "goit"):
        p = VENDOR / f"gem_{tracker}_records.json"
        if p.exists():
            rows.extend(json.loads(p.read_text(encoding="utf-8")))
    return rows


def reconcile(gem_rows, entities):
    """-> (auto_map, review_rows). Only `exact` ever reaches auto_map."""
    keys = registry_keys(entities)
    by_name = collections.defaultdict(list)
    for r in gem_rows:
        by_name[normalise(r["name"])].append(r)

    auto, review = [], []
    for key, group in sorted(by_name.items()):
        if not key:
            continue
        hits = keys.get(key, [])
        ids = sorted({r["gem_project_id"] for r in group if r["gem_project_id"]})
        display = group[0]["name"]

        if len(hits) == 1:
            # One canonical entity, N GEM segments. N>1 is `aggregates` by construction.
            rel = "represents" if len(ids) == 1 else "aggregates"
            for pid in ids:
                auto.append({
                    "canonical_pipeline_id": hits[0],
                    "source_system": "gem_ggit" if group[0]["commodity"] == "gas" else "gem_goit",
                    "source_id": pid,
                    "relationship": rel,
                    "confidence": "exact",
                    "evidence": (f"Normalised name equality with a registry name/alias; "
                                 f"{len(ids)} GEM segment(s) share this name"),
                    "source_native": display,
                })
        elif len(hits) > 1:
            review.append(("AMBIGUOUS", display, ";".join(ids), "|".join(hits),
                           "Name matches more than one canonical entity — never auto-merged"))
        else:
            review.append(("UNMATCHED", display, ";".join(ids), "",
                           "No registry name or alias matches; candidate for a new entity"))
    return auto, review


def summarise(gem_rows, auto, review, entities):
    mapped_ids = {a["source_id"] for a in auto}
    covered = {a["canonical_pipeline_id"] for a in auto}
    quality = collections.Counter(r["route_quality"] for r in gem_rows)
    return {
        "gem_rows": len(gem_rows),
        "gem_rows_auto_mapped": len(mapped_ids),
        "gem_rows_to_review": sum(len(r[2].split(";")) for r in review if r[2]),
        "registry_entities": len(entities),
        "registry_entities_with_gem": len(covered),
        "registry_entities_without_gem": sorted(
            e["canonical_pipeline_id"] for e in entities
            if e["canonical_pipeline_id"] not in covered),
        "review_ambiguous": sum(1 for r in review if r[0] == "AMBIGUOUS"),
        "review_unmatched": sum(1 for r in review if r[0] == "UNMATCHED"),
        "route_quality": dict(quality),
        # The number that matters for honesty: GEM rows whose geometry is GEM's own straight line.
        "gem_rows_topology_only": quality.get("topology_only", 0),
    }


def write(auto, review):
    PROPOSAL.parent.mkdir(parents=True, exist_ok=True)
    with open(PROPOSAL, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["canonical_pipeline_id", "source_system", "source_id",
                                           "relationship", "confidence", "evidence",
                                           "source_native"])
        w.writeheader()
        w.writerows(sorted(auto, key=lambda r: (r["canonical_pipeline_id"], r["source_id"])))
    with open(REVIEW, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["disposition", "gem_name", "gem_project_ids", "candidate_canonical_ids",
                    "reason"])
        w.writerows(sorted(review))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true", help="print only, write nothing")
    args = ap.parse_args(argv)

    gem_rows = load_gem()
    if not gem_rows:
        print("no GEM records — run `python -m pipeline.import_gem` first", file=sys.stderr)
        return 1
    entities = list(load_registry().values())
    auto, review = reconcile(gem_rows, entities)
    s = summarise(gem_rows, auto, review, entities)

    log("gem-reconcile:")
    for k in ("gem_rows", "gem_rows_auto_mapped", "gem_rows_to_review",
              "registry_entities_with_gem", "review_ambiguous", "review_unmatched",
              "gem_rows_topology_only"):
        log(f"  {k:28s} {s[k]}")
    log(f"  registry entities with NO GEM match: {len(s['registry_entities_without_gem'])}")
    for e in s["registry_entities_without_gem"]:
        log(f"      {e}")
    if not args.report:
        write(auto, review)
        log(f"  wrote {PROPOSAL.name} and {REVIEW.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
