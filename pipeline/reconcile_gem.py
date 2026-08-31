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


# GEM statuses that describe something not built, no longer built, or never operated. Binding one
# of these to an operating canonical entity is the RV-009 failure (a cancelled Yamal-Europe 2
# matched an operating trunk by name), so it is detected rather than left to a reader.
_NOT_OPERATING = {"cancelled", "proposed", "shelved", "retired", "mothballed", "construction",
                  "pre-construction", "idle"}


def _contradictions(row, entity):
    """Reasons this name match is probably NOT the same asset."""
    out = []
    status = (row.get("status_native") or "").strip().lower()
    if status in _NOT_OPERATING:
        out.append(f"GEM status is '{status}' — the registry entity is treated as built")
    reg_countries = {c.strip().upper() for c in (entity.get("countries") or [])}
    gem_countries = {c.strip().upper()[:2] for c in (row.get("countries") or [])}
    ISO = {"RUSSIA": "RU", "BELARUS": "BY", "UKRAINE": "UA", "GERMANY": "DE", "POLAND": "PL",
           "CHINA": "CN", "KAZAKHSTAN": "KZ", "TURKEY": "TR", "SLOVAKIA": "SK", "HUNGARY": "HU",
           "CZECHIA": "CZ", "UZBEKISTAN": "UZ", "TURKMENISTAN": "TM"}
    gem_iso = {ISO.get(c.strip().upper(), c.strip().upper()[:2])
               for c in (row.get("countries") or [])}
    if reg_countries and gem_iso and not (reg_countries & gem_iso):
        out.append(f"no country overlap: registry {sorted(reg_countries)} vs GEM {sorted(gem_iso)}")
    return out


def reconcile(gem_rows, entities):
    """-> (auto_map, review_rows). Nothing here is `exact`; see the confidence note below."""
    keys = registry_keys(entities)
    entity_by_id = {e["canonical_pipeline_id"]: e for e in entities}
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
            # RELATIONSHIP DIRECTION. GEM splits a pipeline into per-country / per-phase
            # SEGMENTS, so each GEM row is a PART OF the canonical entity. `aggregates` means the
            # opposite — one source record covering several of ours, as an OSM superroute does —
            # and writing it here inverted the hierarchy on 54 of 66 rows.
            rel = "represents" if len(ids) == 1 else "part_of"
            for pid in ids:
                row = next(r for r in group if r["gem_project_id"] == pid)
                # CONFIDENCE. This matcher compares NAMES. A name match is not an identity match,
                # and this iteration has two proofs: three OSM relations are called "Nord Stream",
                # and "Yamal Europe 2" is a cancelled project whose name matches an operating
                # trunk. `exact` is auto-mergeable, so claiming it here would let name similarity
                # become canonical silently — the exact failure this module's docstring forbids.
                # Name equality against a curated alias is `strong` evidence and no more.
                conf = "strong"
                flags = _contradictions(row, entity_by_id[hits[0]])
                if flags:
                    # A status or country contradiction is not a weak match, it is a probable
                    # WRONG match: a cancelled or foreign asset bound to an operating one.
                    conf = "possible"
                auto.append({
                    "canonical_pipeline_id": hits[0],
                    "source_system": "gem_ggit" if group[0]["commodity"] == "gas" else "gem_goit",
                    "source_id": pid,
                    "relationship": rel,
                    "confidence": conf,
                    "gem_status": row.get("status_native"),
                    "contradictions": "; ".join(flags),
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
                                           "relationship", "confidence", "gem_status",
                                           "contradictions", "evidence", "source_native"])
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
