"""Mutation campaign for the iteration-16 governance rules.

    .venv\\Scripts\\python.exe scripts\\mutation_campaign.py

Each mutation deliberately breaks ONE rule in an isolated copy of the repository and runs the
tests that are supposed to guard it. A mutation that leaves those tests green has SURVIVED,
which means the rule is not actually protected; the script exits non-zero if any survive.

The copy holds the code, tests, curated and processed data and the Natural Earth cache; the real
repository is never modified. Tests that need git history read it from the real repository
(read-only) through EDM_GIT_ROOT.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

COPY_DIRS = ("pipeline", "scripts", "tests", "methodology", "data/curated", "data/processed",
             "web/public/data", "docs")
COPY_FILES = ("pyproject.toml", "data/raw/ne_10m_admin_1.geojson", "data/raw/ne_50m_admin_0.geojson",
              "CLAUDE.md", "README.md")


def _text(old, new):
    def mutate(s):
        assert s.count(old) == 1, f"mutation anchor not found exactly once: {old[:70]!r}"
        return s.replace(old, new)
    return mutate


def _episodes(fn):
    def mutate(s):
        d = json.loads(s)
        fn({e["episode_id"]: e for e in d["episodes"]})
        return json.dumps(d, ensure_ascii=False, indent=2)
    return mutate


def _drop_helene_member(eps):
    eps["us-2024-09-hurricane-helene"]["event_ids"].pop()


def _helene_member_into_francine(eps):
    eps["us-2024-09-hurricane-francine"]["event_ids"].append(
        eps["us-2024-09-hurricane-helene"]["event_ids"][0])


# (name, [(file, mutate)], pytest -k expression)
MUTATIONS = [
    ("one statement => one episode shortcut restored",
     [("pipeline/build_systems.py", _text("\nEPISODE_BASES = {\n",
       '\nEPISODE_BASES = {\n    "single_statement": "One source statement reported these records together.",\n')),
      ("pipeline/build_systems.py", _text("        if basis in RETIRED_EPISODE_BASES:", "        if False:"))],
     "one_source_statement_is_not_an_episode"),
    ("second reviewer omitted (import gate)",
     [("scripts/import_candidates.py", _text('        if not indep.get("completed"):\n', "        if False:\n"))],
     "import_gate_holds_what_it_should"),
    ("second reviewer omitted (build)",
     [("pipeline/build_systems.py", _text('        if not r.get("independent_review_complete"):\n',
                                          "        if False:\n"))],
     "refuses_a_record_without_two_reviews"),
    ("research completeness inferred from source freshness",
     [("pipeline/build_systems.py", _text('{"complete": "met", "partial": "partial"}.get(rf["completeness"], "unmet"),',
                                          '"met" if not unstated else "partial",'))],
     "not_inferred_from_source_freshness"),
    ("current reconstruction labelled as-published",
     [("pipeline/production_history.py", _text('            "mode": RECONSTRUCTION,', '            "mode": CONCEPT,'))],
     "reconstruction_never_as_published"),
    ("Oct-9 backfilled event appears in the as-published snapshot",
     [("pipeline/production_history.py", _text('ids = _event_ids(root, e["sha"])', 'ids = _event_ids(root, "HEAD")'))],
     "backfill_fixture_holds_when_history_is_rebuilt"),
    ("active-campaign recovery status exposed (import)",
     [("scripts/import_candidates.py", _text("    if campaigns and build_systems.campaign_of(ev, system_id, campaigns):",
                                             "    if False:"))],
     "writes_the_withheld_marker"),
    ("active-campaign recovery status exposed (build)",
     [("pipeline/build_systems.py", _text(
         '        if rec["research_status"] != WITHHELD or any(rec[k] for k in ("kind", "date", "evidence", "url")):',
         "        if False:"))],
     "active_campaign_withholds_facility_status"),
    ("source stale threshold alters analytics",
     [("pipeline/build_systems.py", _text('    events = [e for e in events if e["date"] <= as_of]\n',
       '    events = [e for e in events if e["date"] <= as_of]\n'
       '    events = [e for e in events if min(p["days"] for p in STALE_POLICIES.values()) > 30]\n'))],
     "stale_limits_never_change_what_a_system_publishes"),
    ("US research marked complete with a skipped source lane",
     [("pipeline/build_systems.py", _text(
         '            if p.get("status") == "complete" and any(lane.get("status") != "complete" for lane in lanes):',
         "            if False:"))],
     "complete_means_every_declared_lane_was_executed"),
    ("one episode loses a member",
     [("data/curated/systems/us/episodes.json", _episodes(_drop_helene_member))],
     "every_shipped_episode_obeys_the_iteration_16_invariants"),
    ("one record enters two episodes",
     [("data/curated/systems/us/episodes.json", _episodes(_helene_member_into_francine))],
     "every_shipped_episode_obeys_the_iteration_16_invariants"),
]


def _sandbox():
    box = Path(tempfile.mkdtemp(prefix="edm-mutation-"))
    for d in COPY_DIRS:
        shutil.copytree(ROOT / d, box / d, ignore=shutil.ignore_patterns("__pycache__"))
    for f in COPY_FILES:
        src = ROOT / f
        if src.exists():
            (box / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, box / f)
    return box


def _run(box, k):
    env = {**os.environ, "EDM_GIT_ROOT": str(ROOT), "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([PY, "-m", "pytest", "-q", "-o", "addopts=", "-p", "no:cacheprovider",
                        "tests/test_pipeline.py", "-k", k], cwd=box, capture_output=True, text=True,
                       encoding="utf-8", env=env)
    tail = (r.stdout.strip().splitlines() or [""])[-1]
    return r.returncode, tail


def main():
    box = _sandbox()
    try:
        failures = []
        for name, edits, k in MUTATIONS:
            code, tail = _run(box, k)
            if code != 0 or "skipped" in tail and "passed" not in tail:
                failures.append(f"BASELINE not green for {k!r}: {tail}")
                print(f"  baseline  {name}: {tail}")
                continue
            originals = {}
            for rel, mutate in edits:
                p = box / rel
                originals.setdefault(rel, p.read_text(encoding="utf-8"))
                p.write_text(mutate(p.read_text(encoding="utf-8")), encoding="utf-8")
            code, tail = _run(box, k)
            for rel, text in originals.items():
                (box / rel).write_text(text, encoding="utf-8")
            caught = code != 0
            print(f"  {'CAUGHT  ' if caught else 'SURVIVED'}  {name}  ({tail})")
            if not caught:
                failures.append(f"survived: {name}")
        print(f"{len(MUTATIONS)} mutations, {len(MUTATIONS) - sum(1 for f in failures if f.startswith('survived'))} caught")
        if failures:
            print("\n".join(failures))
            sys.exit(1)
    finally:
        shutil.rmtree(box, ignore_errors=True)


if __name__ == "__main__":
    main()
