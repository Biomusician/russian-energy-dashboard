"""Calibrate Evidence Confidence v2 against blind reviewer labels.

    .venv\\Scripts\\python.exe scripts\\eci_calibration.py packets [--per-cell 2] [--seed 22]
    .venv\\Scripts\\python.exe scripts\\eci_calibration.py compare

WHY. The model's thresholds (High >= 78, and so on) are a claim about how a careful reader would
sort records by the quality of their evidence. That claim is checked by asking reviewers to sort a
sample WITHOUT seeing what the model said, and measuring agreement. A reviewer shown the model's
category tends to agree with it, so the two halves live in two files:

  packets.json  what a reviewer sees: an opaque packet id, the record's neutral summary and effect,
                its date, and for each source who published it, in what role and medium, when, in
                what language, which named wire it carries (its own story or a republication) and what it supports.
                Never the category, the score, a component, the record's id or a source address.
  key.json      packet id -> record and the model's result. A reviewer never opens it.

`packets` samples every country system's PUBLISHED events, a few from each category the model
gave in each country, plus any impact candidates in the local queue. `compare` reads the label
files reviewers wrote beside the packets (`labels_<name>.json`,
{packet_id: {"label": "HIGH|MODERATE|LIMITED|PRELIMINARY|DISPUTED", "reason": "..."}}) and reports
each reviewer against the model and against each other: confusion matrix, exact and within-one
agreement, Cohen's kappa, and the packets where two reviewers agree with each other and not with
the model, which is where a threshold or a rule is most likely wrong.

Everything is written to the local, gitignored queue (`data/candidates/eci_calibration/`): packets
may describe candidates that are never published. Nothing here is served, and nothing here reaches
the theatre's index.
"""
import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import build_systems, evidence_confidence, systems  # noqa: E402

OUT = ROOT / "data" / "candidates" / "eci_calibration"
PROCESSED = ROOT / "data" / "processed"
IMPACT_QUEUE = ROOT / "data" / "candidates" / "impacts22"

LABELS = ("HIGH", "MODERATE", "LIMITED", "PRELIMINARY", "DISPUTED")
# Disputed is off the scale: it is not "one below Preliminary", so it is never within one of anything.
ORDINAL = ("PRELIMINARY", "LIMITED", "MODERATE", "HIGH")
# What a packet may hold. A test holds `packet()` to these and to nothing that reveals the result.
PACKET_FIELDS = ("packet_id", "summary", "effect", "reported_figure", "date", "date_end", "sources")
PACKET_SOURCE_FIELDS = ("publisher", "role", "medium", "social_tier", "date", "language",
                        "carries_wire", "supports")


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def packet_id(seed, kind, record_id):
    """Opaque and stable for one seed: a reviewer cannot read the record or its stratum from it,
    and re-running `packets` does not orphan labels already written."""
    return "pkt-" + hashlib.sha256(f"{seed}|{kind}|{record_id}".encode("utf-8")).hexdigest()[:10]


def blind_source(s):
    origin = evidence_confidence.origin_of(s) or ""
    supports = s.get("supports")
    return {
        "publisher": s.get("publisher"),
        "role": s.get("source_role"),
        "medium": s.get("medium") or "web",
        "social_tier": (s.get("social") or {}).get("account_tier"),
        "date": s.get("date"),
        "language": s.get("language"),
        "carries_wire": origin[5:] if origin.startswith("wire:") else None,
        # A country record predates claim-level provenance: its citations support the event.
        "supports": ["occurrence", "effect"] if supports is None else list(supports),
    }


def _figure(record):
    cap = record.get("capacity_affected")
    if cap:
        return {k: cap.get(k) for k in ("value", "value_min", "value_max", "qualifier", "measure", "unit", "source_says")}
    impacts = record.get("civilian_service_impact") or []
    return [i.get("affected") for i in impacts if i.get("affected")] or None


def packet(pid, record):
    """The record as a labelling reviewer sees it."""
    return {"packet_id": pid, "summary": record.get("summary"), "effect": record.get("effect"),
            "reported_figure": _figure(record), "date": record.get("date"), "date_end": record.get("date_end"),
            "sources": [blind_source(s) for s in record.get("sources") or []]}


def country_records():
    """(kind, stratum, record id, record, model result) for every published country event."""
    for sid in systems.COUNTRY_SYSTEMS:
        path = PROCESSED / systems.root(sid) / "events.json"
        if not path.is_file():
            continue
        for e in _read(path)["events"]:
            model = evidence_confidence.assess(e["sources"], e["date"], e.get("date_end"),
                                               build_systems.effect_specificity(e))
            yield "country_event", sid, e["event_id"], e, model


def impact_candidates():
    """The same for impact candidates in the local queue, when a lane has written any."""
    if not IMPACT_QUEUE.is_dir():
        return
    for path in sorted(IMPACT_QUEUE.glob("*/candidates.json")):
        doc = _read(path)
        rows = doc if isinstance(doc, list) else doc.get("candidates") or doc.get("records") or []
        for r in rows:
            if not isinstance(r, dict) or not r.get("sources") or not r.get("date"):
                continue
            model = evidence_confidence.assess(r["sources"], r["date"], r.get("date_end"),
                                               r.get("effect_specificity") or "described", r.get("dispute"))
            yield "impact_candidate", path.parent.name, r.get("impact_id") or r.get("candidate_id"), r, model


def sample(rows, per_cell, seed):
    """Up to `per_cell` records from each (stratum, model category) cell: every country, and every
    category the model used there, is in front of the reviewers. Seeded, so it can be re-run."""
    rng = random.Random(seed)
    cells = {}
    for row in rows:
        cells.setdefault((row[0], row[1], row[4]["category"]), []).append(row)
    picked = []
    for key in sorted(cells):
        members = sorted(cells[key], key=lambda r: str(r[2]))
        picked += rng.sample(members, min(per_cell, len(members)))
    # Shuffled, so a packet's position says nothing about its country or its category.
    rng.shuffle(picked)
    return picked


def build_packets(per_cell=2, seed=22):
    rows = sample(list(country_records()) + list(impact_candidates()), per_cell, seed)
    packets, key = [], {}
    for kind, stratum, rid, record, model in rows:
        pid = packet_id(seed, kind, rid)
        packets.append(packet(pid, record))
        key[pid] = {"kind": kind, "stratum": stratum, "record_id": rid, "model": model}
    return packets, key


INSTRUCTIONS = (
    "For each packet, judge the QUALITY OF THE PUBLIC EVIDENCE that the event happened and that the "
    "reported effect is supported. Not how severe it was, not how likely, not how important the "
    "facility. HIGH: a direct or independently reported account, corroborated by a second independent "
    "originating statement, with a specific reported effect. MODERATE: a credible account from one "
    "originating statement, or corroborated reporting with a less specific effect. LIMITED: reported "
    "by a credible source but single-origin and thin on the effect, or resting on secondary sources. "
    "PRELIMINARY: rests on unverified or secondary claims. DISPUTED: credible sources materially "
    "disagree about whether it happened or what the effect was. Copies of one wire story are one "
    "statement. Write labels_<your name>.json beside this file: "
    '{"<packet_id>": {"label": "HIGH|MODERATE|LIMITED|PRELIMINARY|DISPUTED", "reason": "one sentence"}}. '
    "Do not open key.json or another reviewer's labels.")


def cmd_packets(args):
    packets, key = build_packets(args.per_cell, args.seed)
    _write(OUT / "packets.json", {"instructions": INSTRUCTIONS, "labels": list(LABELS), "packets": packets})
    _write(OUT / "key.json", {"seed": args.seed, "per_cell": args.per_cell,
                              "method_version": evidence_confidence.METHOD["version"], "packets": key})
    print(f"{len(packets)} blind packets -> {OUT / 'packets.json'}")
    print(f"key (reviewers do not open it) -> {OUT / 'key.json'}")


# --- agreement ---------------------------------------------------------------------------------------

def confusion(a, b):
    """{row label: {column label: count}} over the packets both labelled."""
    table = {r: {c: 0 for c in LABELS} for r in LABELS}
    for pid in sorted(set(a) & set(b)):
        table[a[pid]][b[pid]] += 1
    return table


def within_one(x, y):
    if x == y:
        return True
    return x in ORDINAL and y in ORDINAL and abs(ORDINAL.index(x) - ORDINAL.index(y)) == 1


def kappa(a, b):
    """Cohen's kappa: agreement beyond what two raters with these label frequencies would reach by
    chance. None when it is undefined (no shared packets, or both used one label throughout)."""
    shared = sorted(set(a) & set(b))
    n = len(shared)
    if not n:
        return None
    observed = sum(1 for p in shared if a[p] == b[p]) / n
    expected = sum((sum(1 for p in shared if a[p] == c) / n) * (sum(1 for p in shared if b[p] == c) / n) for c in LABELS)
    if expected >= 1:
        return None
    return round((observed - expected) / (1 - expected), 3)


def agreement(a, b):
    shared = sorted(set(a) & set(b))
    n = len(shared)
    return {
        "packets": n,
        "exact": round(sum(1 for p in shared if a[p] == b[p]) / n, 3) if n else None,
        "within_one": round(sum(1 for p in shared if within_one(a[p], b[p])) / n, 3) if n else None,
        "kappa": kappa(a, b),
        "confusion": confusion(a, b),
    }


def load_labels(directory, known):
    """{reviewer: {packet_id: label}}, {reviewer: {packet_id: reason}}, and what was refused."""
    labels, reasons, problems = {}, {}, []
    for path in sorted(Path(directory).glob("labels_*.json")):
        name = path.stem[len("labels_"):]
        labels[name], reasons[name] = {}, {}
        for pid, row in _read(path).items():
            label = (row or {}).get("label") if isinstance(row, dict) else row
            if pid not in known:
                problems.append(f"{name}: {pid} is not a packet")
            elif label not in LABELS:
                problems.append(f"{name}: {pid} has label {label!r}, not one of {LABELS}")
            else:
                labels[name][pid] = label
                reasons[name][pid] = (row or {}).get("reason") if isinstance(row, dict) else None
    return labels, reasons, problems


def compare(key, labels, reasons=None):
    """Every reviewer against the model and against each other, and the packets where at least two
    reviewers give the same label and the model gives another."""
    model = {pid: row["model"]["category"] for pid, row in key.items()}
    names = sorted(labels)
    out = {"method_version": None, "packets_in_key": len(key), "reviewers": names,
           "reviewer_vs_model": {n: agreement(labels[n], model) for n in names},
           "reviewer_vs_reviewer": {f"{a} vs {b}": agreement(labels[a], labels[b])
                                    for i, a in enumerate(names) for b in names[i + 1:]},
           "reviewers_agree_model_differs": []}
    for pid in sorted(key):
        given = {n: labels[n][pid] for n in names if pid in labels[n]}
        for label in LABELS:
            who = sorted(n for n, v in given.items() if v == label)
            if len(who) >= 2 and label != model[pid]:
                out["reviewers_agree_model_differs"].append({
                    "packet_id": pid, "record_id": key[pid]["record_id"], "stratum": key[pid]["stratum"],
                    "reviewers": who, "reviewer_label": label, "model_label": model[pid],
                    "model_score": key[pid]["model"]["score"], "model_components": key[pid]["model"]["components"],
                    "reasons": {n: (reasons or {}).get(n, {}).get(pid) for n in who}})
    return out


def _table(title, table):
    lines = [f"**{title}** (rows: first rater; columns: second)", "", "| | " + " | ".join(LABELS) + " |",
             "|---|" + "---|" * len(LABELS)]
    lines += [f"| {r} | " + " | ".join(str(table[r][c]) for c in LABELS) + " |" for r in LABELS]
    return lines + [""]


def markdown(result):
    lines = ["# Evidence Confidence v2: calibration against blind labels", "",
             f"Reviewers: {', '.join(result['reviewers']) or 'none yet'}. Packets in the key: {result['packets_in_key']}.", ""]
    for heading, block in (("Each reviewer against the model", "reviewer_vs_model"),
                           ("Reviewers against each other", "reviewer_vs_reviewer")):
        lines += [f"## {heading}", "", "| Pair | Packets | Exact | Within one category | Cohen's kappa |", "|---|---|---|---|---|"]
        for name, a in result[block].items():
            label = f"{name} vs model" if block == "reviewer_vs_model" else name
            lines.append(f"| {label} | {a['packets']} | {a['exact']} | {a['within_one']} | {a['kappa']} |")
        lines.append("")
        for name, a in result[block].items():
            lines += _table(f"{name} vs model" if block == "reviewer_vs_model" else name, a["confusion"])
    lines += ["## Two reviewers agree with each other and not with the model", ""]
    if not result["reviewers_agree_model_differs"]:
        lines.append("None.")
    for row in result["reviewers_agree_model_differs"]:
        lines.append(f"- `{row['packet_id']}` ({row['stratum']}): {', '.join(row['reviewers'])} say "
                     f"{row['reviewer_label']}; the model says {row['model_label']} (score {row['model_score']}).")
    return "\n".join(lines) + "\n"


def cmd_compare(args):
    key = _read(OUT / "key.json")
    labels, reasons, problems = load_labels(OUT, key["packets"])
    for p in problems:
        print("REFUSED", p)
    if not labels:
        print(f"no labels_<name>.json in {OUT}; nothing to compare")
        return 1
    result = compare(key["packets"], labels, reasons)
    result["method_version"] = key.get("method_version")
    result["refused_labels"] = problems
    _write(OUT / "comparison.json", result)
    text = markdown(result)
    with open(OUT / "comparison.md", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(text)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("packets", help="write blind packets and their key to the local queue")
    p.add_argument("--per-cell", type=int, default=2, help="records per (country, model category)")
    p.add_argument("--seed", type=int, default=22)
    p.set_defaults(run=cmd_packets)
    c = sub.add_parser("compare", help="agreement of reviewer labels with the model and each other")
    c.set_defaults(run=cmd_compare)
    args = ap.parse_args(argv)
    return args.run(args) or 0


if __name__ == "__main__":
    sys.exit(main())
