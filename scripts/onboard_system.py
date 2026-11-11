"""Turn a reviewed source-audit draft into a curated country system (iteration 19).

    .venv\\Scripts\\python.exe scripts\\onboard_system.py <cc> <draft_dir>

Reads `<draft_dir>/<cc>_system_draft.json` and `<cc>_profile_draft.json` (written by a source-audit
lane into the local queue) and the lead's decisions for that country in
`<draft_dir>/lead_decisions.json`, and writes `data/curated/systems/<cc>/` with an EMPTY record:
no events, no episodes, no research pass. Records arrive only through `import_candidates.py`.

WHY A SCRIPT. Seven countries were onboarded at once, and each needs the same things checked
before a file becomes curated truth: the id is registered, the unit count is the one Natural Earth
draws, every ruling names a drawn unit, the profile holds national rows only, and the precision
policy states its reason. Doing that by hand seven times is how one gets skipped.

It refuses to overwrite a system that already has events.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import build_systems, systems  # noqa: E402

# Words that turn a national statistic into a statement about worth as a target. A profile says
# what a country produces; it never says what matters most.
LOADED = ("critical", "chokepoint", "choke point", "vital", "artery", "lifeline", "strategic",
          "vulnerab", "linchpin", "backbone", "crown jewel", "most important", "indispensable")
EVENTS_NOTE = None
EPISODES_NOTE = ("Hand-curated. Records share an episode only for the same explicitly named hazard, the same "
                 "explicitly identified common event or coordinated wave, or an explicit continuation of the same "
                 "disruption, and every shared basis other than a named hazard cites the source that says so. "
                 "Records not listed here are each their own episode (singleton).")
LOG_NOTE = ("What was searched, when, and how far it got. Counts only: the candidate queue's per-record narratives "
            "are kept off the public record (data/candidates/README.md). A SYSTEMATIC pass declares its source "
            "lanes and window before searching. A window searched with the budget exhausted is PARTIAL, not "
            "researched-and-quiet.")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, doc):
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def loaded_words(doc):
    text = json.dumps(doc, ensure_ascii=False).lower()
    return sorted(w for w in LOADED if w in text)


def assemble(cc, draft, profile, decisions, unit_codes):
    """(system, profile) ready to write, or ValueError naming every problem."""
    problems = []
    if draft.get("system_id") != cc:
        problems.append(f"draft is for {draft.get('system_id')!r}")
    doc = {k: v for k, v in draft.items()}
    geo = doc["geography"]
    if geo.get("units_expected") != len(unit_codes):
        problems.append(f"units_expected {geo.get('units_expected')} but Natural Earth draws {len(unit_codes)}")
    drop = set(decisions.get("drop_rulings") or [])
    restatus = decisions.get("ruling_status") or {}
    rulings = [dict(r, status=restatus.get(r["code"], r["status"])) for r in geo.get("rulings", []) if r["code"] not in drop]
    rulings += decisions.get("add_rulings") or []
    for r in rulings:
        if r["code"] not in unit_codes:
            problems.append(f"ruling for {r['code']}, which is not a drawn unit")
        if r["status"] not in ("note", "contains_disputed_area", "disputed_unassigned"):
            problems.append(f"ruling {r['code']}: unknown status {r['status']!r}")
    geo["rulings"] = sorted(rulings, key=lambda r: r["code"])
    policy = decisions.get("precision_policy")
    if not policy or not policy.get("reason"):
        problems.append("the lead's decisions state no precision policy with a reason")
    else:
        geo["precision_policy"] = policy
        for code in policy.get("no_event_units") or []:
            if code not in unit_codes:
                problems.append(f"no_event_units names {code}, which is not a drawn unit")
    if decisions.get("geography_note"):
        geo["note"] = decisions["geography_note"]
    doc["maturity"] = decisions.get("maturity", "research_preview")
    if decisions.get("reporting_environment"):
        doc["reporting_environment"] = decisions["reporting_environment"]
    if doc.get("reporting_environment") not in systems.REPORTING_ENVIRONMENTS:
        problems.append(f"unknown reporting environment {doc.get('reporting_environment')!r}")
    doc["research_gaps"] = list(decisions.get("research_gaps") or draft.get("research_gaps") or [])
    if decisions.get("lane_registry"):
        # Which registry sources each declared lane searches (scripts/write_gulf_pass.py).
        in_use = {s["name"] for s in doc.get("sources", []) if not s["role"].startswith("rejected")}
        for lane, entry in decisions["lane_registry"].items():
            if set(entry["registry"]) - in_use:
                problems.append(f"lane {lane} names a source that is not in use: {sorted(set(entry['registry']) - in_use)}")
        doc["lane_registry"] = decisions["lane_registry"]
    doc["provenance"] = (f"Authored {decisions['date']} (iteration 19) from the source-audit lane's draft, with the "
                         "lead's precision policy and rulings. Edit by hand; this file is the curated source.")
    dropped = set(decisions.get("drop_metrics") or [])
    prof = dict(profile, metrics=[m for m in profile["metrics"] if m["metric"] not in dropped])
    for m in prof["metrics"]:
        if not (m.get("source") and m.get("url") and m.get("year")):
            problems.append(f"profile row {m['metric']}: needs source, url and year")
    bad = loaded_words(prof) + loaded_words({k: doc.get(k) for k in ("reporting_note", "sectors", "research_gaps")})
    if bad:
        problems.append(f"loaded wording {sorted(set(bad))}: a profile describes, it does not weigh")
    if problems:
        raise ValueError(f"onboard {cc}: " + "; ".join(problems))
    return doc, prof


def run(cc, draft_dir):
    draft_dir = Path(draft_dir)
    if cc not in systems.COUNTRY_SYSTEMS:
        raise SystemExit(f"{cc} is not registered in pipeline/systems.py")
    out = ROOT / "data" / "curated" / "systems" / cc
    if (out / "events.json").exists() and read(out / "events.json").get("events"):
        raise SystemExit(f"{out} already holds events; edit its files by hand")
    decisions = read(draft_dir / "lead_decisions.json")[cc]
    admin1, admin0 = build_systems.load_admin1(), build_systems.load_admin0()
    unit_codes = {u[0] for u in build_systems.units(cc, admin1, admin0)}
    doc, prof = assemble(cc, read(draft_dir / f"{cc}_system_draft.json"),
                         read(draft_dir / f"{cc}_profile_draft.json"), decisions, unit_codes)
    out.mkdir(parents=True, exist_ok=True)
    write(out / "system.json", doc)
    write(out / "profile.json", prof)
    write(out / "events.json", {"system_id": cc, "events": []})
    write(out / "episodes.json", {"note": EPISODES_NOTE, "episodes": []})
    write(out / "research_log.json", {"note": LOG_NOTE, "passes": []})
    print(f"{cc}: {len(unit_codes)} units, {len(doc['geography']['rulings'])} rulings, "
          f"{len(prof['metrics'])} profile rows, policy {doc['geography']['precision_policy'].get('kinetic')}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    run(sys.argv[1], sys.argv[2])
