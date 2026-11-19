"""Calibrate Evidence Confidence v2 against blind reviewer labels.

    .venv\\Scripts\\python.exe scripts\\eci_calibration.py packets [--target 60] [--seed 22]
    .venv\\Scripts\\python.exe scripts\\eci_calibration.py compare

WHY. The model's thresholds (High >= 78, and so on) are a claim about how a careful reader would
sort records by what their cited sources support. That claim is checked by asking reviewers to
sort a sample WITHOUT seeing what the model said, and measuring agreement. A reviewer shown the
model's category tends to agree with it, so the two halves live in two files:

  packets.json  what a reviewer sees: an opaque packet id, the record's neutral summary and effect,
                its date, and for each source who published it, in what role and medium, when, in
                what language, which named wire it carries (its own story or a republication) and what it supports.
                Never the category, the score, a component, the record's id or a source address.
  key.json      packet id -> record and the model's result. A reviewer never opens it.

The reviewer is given the QUESTION and five neutral labels, not the model's rubric: instructions
that restate the model's category meanings measure whether a reader can apply the rubric, not
whether the rubric sorts records the way a careful reader would.

`packets` samples every country system's PUBLISHED events, the imported impact records
(`data/curated/global_impacts/events.json`) when the corpus has been imported, and any impact
candidates still in the local queue. The sample is drawn across country and a neutral description
of the sources (a dispute, a social post, an actor's claim, a first-party statement, press only),
NEVER across the model's own categories: a sample stratified on one rater's output cannot estimate
agreement with that rater. `compare` reads the label files reviewers wrote beside the packets
(`labels_<name>.json`, {packet_id: {"label": "HIGH|MODERATE|LIMITED|PRELIMINARY|DISPUTED",
"reason": "..."}}) and reports each reviewer against the model and against each other: confusion
matrix, exact and within-one agreement, Cohen's kappa, and the packets where two reviewers agree
with each other and not with the model, which is where a threshold or a rule is most likely wrong.
It also writes `calibration_result.json`, the compact block that is pasted into
docs/EVIDENCE_CONFIDENCE_V2.md when a calibration is recorded.

WHAT THIS CANNOT SEE. A reviewer works from the same typed role, medium and `supports` the model
reads, and has no source address. A mistyped role, or a relay nobody marked, is invisible to both
sides. Typing is a separate error rate that this tool does not measure.

Everything is written to the local, gitignored queue (`data/candidates/eci_calibration/`): packets
may describe candidates that are never published. Nothing here is served, and nothing here reaches
the theatre's index.
"""
import argparse
import datetime as dt
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
IMPACT_CURATED = ROOT / "data" / "curated" / "global_impacts" / "events.json"
# Fewer packets than this and an agreement figure is too noisy to carry a threshold.
TARGET = 60

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
                                               build_systems.effect_specificity(e), review=e.get("review"))
            yield "country_event", sid, e["event_id"], e, model


def _impact_rows(doc):
    rows = doc if isinstance(doc, list) else next(
        (doc[k] for k in ("events", "records", "candidates") if isinstance(doc.get(k), list)), [])
    return [r for r in rows if isinstance(r, dict) and r.get("sources") and r.get("date")]


def _impact_model(r):
    return evidence_confidence.assess(r["sources"], r["date"], r.get("date_end"), r.get("effect_specificity") or "described",
                                      r.get("dispute"), review=r.get("review"))


def impact_records(path=None):
    """Imported, reviewed impact records, when the corpus has been imported. These are where the
    social posts, the actors' claims and the disputes are: the country systems have none."""
    path = Path(path or IMPACT_CURATED)
    if not path.is_file():
        return
    for r in _impact_rows(_read(path)):
        yield "impact_record", r.get("country_a3") or "impact", r.get("impact_id"), r, _impact_model(r)


def impact_candidates(directory=None, imported=()):
    """The same for impact candidates still in the local queue, leaving out any already imported."""
    directory = Path(directory or IMPACT_QUEUE)
    if not directory.is_dir():
        return
    for path in sorted(directory.glob("*/candidates.json")):
        for r in _impact_rows(_read(path)):
            rid = r.get("impact_id") or r.get("candidate_id")
            if rid not in imported:
                yield "impact_candidate", path.parent.name, rid, r, _impact_model(r)


def source_profile(record):
    """What kind of citations a record has, from its typed fields and never from the model's
    result. The sample is spread across these so the rules for posts, claims and disputes are in
    front of the reviewers even though such records are few."""
    sources = record.get("sources") or []
    if record.get("dispute") or any(s.get("disputes") for s in sources):
        return "disputed"
    if any(str(s.get("medium") or "").lower() == "social" for s in sources):
        return "social"
    if any(s.get("source_role") == "actor_self_claim" for s in sources):
        return "actor_claim"
    direct = {r for r, t in evidence_confidence.METHOD["role_tier"].items() if t == "direct"}
    return "first_party" if any(s.get("source_role") in direct for s in sources) else "press_or_secondary"


def sample(rows, target, seed):
    """About `target` records, one at a time from each (kind, country or lane, source profile) in
    turn, random within each: every country and every kind of citation is in front of the
    reviewers, and nothing about the draw depends on what the model said. Records the model does
    not assess (a discovery aid only) are left out: there is no label to compare. Seeded."""
    rng = random.Random(seed)
    strata = {}
    for row in rows:
        if row[4]["category"] is not None:
            strata.setdefault((row[0], row[1], source_profile(row[3])), []).append(row)
    for key in sorted(strata):
        strata[key] = sorted(strata[key], key=lambda r: str(r[2]))
        rng.shuffle(strata[key])
    picked = []
    while len(picked) < target and any(strata.values()):
        for key in sorted(strata):
            if strata[key] and len(picked) < target:
                picked.append(strata[key].pop())
    # Shuffled, so a packet's position says nothing about its country or its sources.
    rng.shuffle(picked)
    return picked


def build_packets(target=TARGET, seed=22):
    imported = list(impact_records())
    population = list(country_records()) + imported + list(impact_candidates(imported={r[2] for r in imported}))
    rows = sample(population, target, seed)
    packets, key = [], {}
    for kind, stratum, rid, record, model in rows:
        pid = packet_id(seed, kind, rid)
        packets.append(packet(pid, record))
        key[pid] = {"kind": kind, "stratum": stratum, "source_profile": source_profile(record),
                    "record_id": rid, "model": model}
    drawn = {
        "population": len(population),
        "not_assessed_left_out": sum(1 for r in population if r[4]["category"] is None),
        "by_kind": {k: sum(1 for r in rows if r[0] == k) for k in sorted({r[0] for r in rows})},
        "by_source_profile": {p: sum(1 for r in rows if source_profile(r[3]) == p)
                              for p in sorted({source_profile(r[3]) for r in rows})},
        "stratified_by": "record kind, country or lane, and source profile; never by the model's category",
    }
    return packets, key, drawn


# The question and five labels in plain words. Deliberately NOT the model's rubric: no points, no
# thresholds, no rule about wires, origins or what earns which label. A reviewer who is handed the
# rubric reproduces it, and the comparison then says nothing about whether the rubric is right.
INSTRUCTIONS = (
    "For each packet, answer one question: on the sources listed, how well supported is it that the "
    "event happened and that the reported effect is as described? Not how severe it was, not how "
    "likely, not how important the facility, and not who or what caused it. Use one of five labels. "
    "HIGH: well supported. MODERATE: supported, with a gap you can name. LIMITED: reported, but thinly "
    "supported. PRELIMINARY: a lead more than a finding. DISPUTED: the sources materially disagree "
    "about whether it happened or what the effect was. How to weigh who is speaking, how many "
    "separate accounts there are and how specific the effect is, is your judgement: say in one "
    "sentence what decided it. Write labels_<your name>.json beside this file: "
    '{"<packet_id>": {"label": "HIGH|MODERATE|LIMITED|PRELIMINARY|DISPUTED", "reason": "one sentence"}}. '
    "Do not open key.json, another reviewer's labels, the method file or the served records.")


def cmd_packets(args):
    packets, key, drawn = build_packets(args.target, args.seed)
    _write(OUT / "packets.json", {"instructions": INSTRUCTIONS, "labels": list(LABELS), "packets": packets})
    _write(OUT / "key.json", {"seed": args.seed, "target": args.target, "sample": drawn,
                              "method_version": evidence_confidence.METHOD["version"], "packets": key})
    print(f"{len(packets)} blind packets -> {OUT / 'packets.json'}")
    print(f"key (reviewers do not open it) -> {OUT / 'key.json'}")
    print(json.dumps(drawn, indent=2))
    if len(packets) < args.target:
        print(f"NOTE: only {len(packets)} assessed records exist; {args.target} were asked for. "
              "Import the impact corpus (data/curated/global_impacts/events.json) and run again.")


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


def result_block(result, key_doc, run_on):
    """The compact record of one calibration run: what is pasted into the results block of
    docs/EVIDENCE_CONFIDENCE_V2.md. Agreement figures and counts only: no record id, no packet id,
    nothing that names a record. The decision (accept the thresholds, or change which rule) is
    the owner's and is written beside it by hand."""
    def brief(a):
        return {k: a[k] for k in ("packets", "exact", "within_one", "kappa")}
    model = [row["model"]["category"] for row in key_doc["packets"].values()]
    return {
        "method_version": key_doc.get("method_version"),
        "run_on": run_on,
        "packets": len(key_doc["packets"]),
        "target": key_doc.get("target"),
        "sample": key_doc.get("sample"),
        "reviewers": len(result["reviewers"]),
        "model_labels": {c: model.count(c) for c in LABELS},
        "reviewer_vs_model": {n: brief(a) for n, a in result["reviewer_vs_model"].items()},
        "reviewer_vs_reviewer": {n: brief(a) for n, a in result["reviewer_vs_reviewer"].items()},
        "reviewers_agree_model_differs": len(result["reviewers_agree_model_differs"]),
        "limits": [
            "Reviewers saw the same typed role, medium and supports the model reads, and no source "
            "address: a mistyped role or an unmarked relay is invisible to both.",
            "Cohen's kappa over this many packets has a wide interval; read it as a direction, not a measurement.",
        ],
        "decision": None,
    }


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
    _write(OUT / "calibration_result.json", result_block(result, key, dt.date.today().isoformat()))
    text = markdown(result)
    with open(OUT / "comparison.md", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(text)
    print(f"compact result to paste into docs/EVIDENCE_CONFIDENCE_V2.md -> {OUT / 'calibration_result.json'}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("packets", help="write blind packets and their key to the local queue")
    p.add_argument("--target", type=int, default=TARGET, help="how many packets to draw")
    p.add_argument("--seed", type=int, default=22)
    p.set_defaults(run=cmd_packets)
    c = sub.add_parser("compare", help="agreement of reviewer labels with the model and each other")
    c.set_defaults(run=cmd_compare)
    args = ap.parse_args(argv)
    return args.run(args) or 0


if __name__ == "__main__":
    sys.exit(main())
