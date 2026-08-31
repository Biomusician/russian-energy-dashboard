"""Bounded ENTSOG cross-border topology snapshot (iteration 10 §14).

    python -m pipeline.import_entsog            # fetch, filter, reconcile, write
    python -m pipeline.import_entsog --report   # print only

WHY THIS SOURCE. OSM and GEM are both third-party *observations* of where pipe runs. ENTSOG's
Transparency Platform is the European TSOs' own register of where their systems actually connect:
the operators on each side of a point, the balancing zones, and the direction semantics. That
makes it a genuinely INDEPENDENT topology source rather than a third opinion about geometry —
which is exactly what the canonical-node model was built to hold.

WHAT IS DELIBERATELY NOT TAKEN:

  tpMapX / tpMapY   ENTSOG ships schematic diagram coordinates for its own network map. They are
                    positions on a SCHEMATIC, not geography, and are not read here at all. A
                    schematic coordinate that becomes a map pin is a fabricated location.
  capacities        Not topology. Out of scope for this iteration.
  flows             Operational data. Out of scope for this project, permanently.

BOUNDED BY CONSTRUCTION: only interconnections with at least one side in Russia, Belarus or
Ukraine — the boundary of the system this atlas models. That is ~68 of ENTSOG's 1,184 rows. This
is not the beginning of a European gas-market platform.

KNOWN LIMITATION: Turkey is not an ENTSOG member, so TurkStream's and Blue Stream's Turkish
landfalls do not appear here. Those nodes stay OSM/operator-sourced.
"""

import argparse
import collections
import csv
import datetime as dt
import json
import re
import urllib.request
from pathlib import Path

from pipeline.util import log, write_json

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "data" / "vendor" / "entsog"
REVIEW = ROOT / "data" / "review" / "entsog_node_review.csv"

API = "https://transparency.entsog.eu/api/v1"
CORE = {"RU", "BY", "UA"}

# Native fields kept verbatim. ENTSOG's own identifiers are the point of using ENTSOG: pointKey
# and the EIC codes are stable handles that survive a rename, which a label does not.
KEEP = ("pointKey", "pointLabel",
        "fromCountryKey", "fromCountryLabel", "fromOperatorKey", "fromOperatorLabel",
        "fromBzKey", "fromBzLabel", "fromDirectionKey", "fromTsoItemIdentifier",
        "toCountryKey", "toCountryLabel", "toOperatorKey", "toOperatorLabel",
        "toBzKey", "toBzLabel", "toDirectionKey", "toTsoItemIdentifier",
        "validFrom", "validto")

# Node-name matching. Only these forms are accepted, and only when they resolve to exactly one
# canonical node — everything else goes to review. ENTSOG labels carry bracketed qualifiers and
# operator suffixes that must be stripped before comparison, but nothing that DISTINGUISHES two
# points may be stripped.
_STRIP = re.compile(r"\s*\((?:[^)]*)\)\s*|\s*/\s*.*$|\s+(?:GMS|IP|ITP|VIP)\b", re.IGNORECASE)


def _norm(name):
    if not name:
        return ""
    s = _STRIP.sub(" ", str(name))
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip().casefold()


def fetch(endpoint, limit=20000):
    url = f"{API}/{endpoint}?limit={limit}"
    with urllib.request.urlopen(url, timeout=300) as fh:
        return json.loads(fh.read().decode("utf-8")), url


def relevant(rows):
    return [r for r in rows
            if (r.get("fromCountryKey") in CORE) or (r.get("toCountryKey") in CORE)]


def to_records(interconnections, eic_by_point, retrieved, source_urls):
    out = []
    for r in relevant(interconnections):
        rec = {k: (r.get(k) if r.get(k) not in ("", "?") else None) for k in KEEP}
        rec["point_eic"] = eic_by_point.get(r.get("pointKey"))
        # Direction is a PAIR: one side exits, the other enters. Kept as both native values
        # rather than collapsed to an arrow, because a bidirectional point reports both.
        rec["direction"] = f"{rec.get('fromDirectionKey') or '?'}->{rec.get('toDirectionKey') or '?'}"
        rec["source_system"] = "entsog_point"
        rec["retrieved_at"] = retrieved
        rec["source_url"] = source_urls["interconnections"]
        out.append(rec)
    return out


def reconcile_nodes(records, nodes):
    """Match ENTSOG points to canonical nodes on NAME, and only when unambiguous.

    Returns (accepted, review). A match is accepted only if the normalised ENTSOG point label
    resolves to exactly one canonical node AND that node's country is one of the two countries
    the interconnection joins. The country check is what stops a common toponym from binding to
    the wrong border.
    """
    by_name = collections.defaultdict(list)
    for nid, n in nodes.items():
        # Aliases participate exactly as names do. A curated alias is a human saying "this source
        # spells it that way"; widening the matcher would be a machine guessing it everywhere.
        for label in [n["node_name"]] + list(n.get("aliases") or []):
            k = _norm(label)
            if k:
                by_name[k].append(nid)

    accepted, review = [], []
    for rec in records:
        label = _norm(rec.get("pointLabel"))
        hits = by_name.get(label, [])
        countries = {rec.get("fromCountryKey"), rec.get("toCountryKey")}
        plausible = sorted({h for h in hits if (nodes[h].get("country") or "") in countries})
        if len(plausible) == 1:
            accepted.append({
                "canonical_node_id": plausible[0],
                "source_system": "entsog_point",
                "source_id": rec["pointKey"],
                "point_eic": rec.get("point_eic"),
                "confidence": "strong",
                "evidence": (f"ENTSOG point label '{rec['pointLabel']}' matches the canonical node "
                             f"name, and the node's country is one of the two the point joins "
                             f"({rec.get('fromCountryKey')}/{rec.get('toCountryKey')})"),
                "source_native": rec["pointLabel"],
            })
        elif hits:
            review.append(("AMBIGUOUS", rec["pointKey"], rec["pointLabel"], "|".join(hits),
                           "Name matches a canonical node but the country check did not confirm it"))
        else:
            review.append(("UNMATCHED", rec["pointKey"], rec["pointLabel"], "",
                           "No canonical node carries this name; ENTSOG record kept unmatched"))
    return accepted, review


def run(write=True):
    from pipeline import pipeline_registry

    retrieved = dt.date.today().isoformat()
    inter, u1 = fetch("interconnections")
    points, u2 = fetch("connectionpoints")
    urls = {"interconnections": u1, "connectionpoints": u2}

    eic = {p["pointKey"]: (p.get("pointEicCode") if p.get("pointEicCode") not in ("", "?") else None)
           for p in points["connectionpoints"]}
    records = to_records(inter["interconnections"], eic, retrieved, urls)
    nodes = pipeline_registry.load_nodes()
    accepted, review = reconcile_nodes(records, nodes)

    pairs = collections.Counter(
        f"{r.get('fromCountryKey')}->{r.get('toCountryKey')}" for r in records)
    log("entsog-import:")
    log(f"  interconnections in feed : {len(inter['interconnections'])}")
    log(f"  kept (RU/BY/UA boundary) : {len(records)}")
    log(f"  distinct points          : {len({r['pointKey'] for r in records})}")
    log(f"  with an EIC code         : {sum(1 for r in records if r.get('point_eic'))}")
    log(f"  matched to canonical node: {len(accepted)}")
    log(f"  left unmatched / review  : {len(review)}")
    log(f"  border pairs             : {dict(sorted(pairs.items()))}")

    manifest = {
        "source": "ENTSOG Transparency Platform",
        "endpoints": urls,
        "retrieved_at": retrieved,
        "release_identifier": None,
        "vintage_note": (f"Live API with no release identifier; this is a snapshot retrieved "
                         f"{retrieved}. Cite it as such, never as a dated publication."),
        "licence": "ENTSOG Transparency Platform terms; attribution required",
        "records_in_feed": len(inter["interconnections"]),
        "records_kept": len(records),
        "filter": "at least one side in RU/BY/UA",
        "excluded_fields": ["tpMapX", "tpMapY"],
        "excluded_reason": ("tpMapX/tpMapY are positions on ENTSOG's schematic network diagram, "
                            "not geography. They are never read."),
        "known_limitation": ("Turkey is not an ENTSOG member, so the TurkStream and Blue Stream "
                             "Turkish landfalls do not appear in this source."),
    }

    if write:
        VENDOR.mkdir(parents=True, exist_ok=True)
        write_json(VENDOR / "entsog_interconnections.json", records)
        write_json(VENDOR / "MANIFEST.json", manifest)
        REVIEW.parent.mkdir(parents=True, exist_ok=True)
        with open(REVIEW, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["disposition", "entsog_point_key", "entsog_point_label",
                        "candidate_node_ids", "reason"])
            w.writerows(sorted(review))
        with open(VENDOR / "node_matches.csv", "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(accepted[0]) if accepted else
                               ["canonical_node_id", "source_system", "source_id"])
            w.writeheader()
            w.writerows(accepted)
        log(f"  wrote {VENDOR}")
    return records, accepted, review, manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true", help="print only, write nothing")
    args = ap.parse_args(argv)
    run(write=not args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
