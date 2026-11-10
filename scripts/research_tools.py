"""Tools for running a research pass (iteration 18).

    .venv\\Scripts\\python.exe scripts\\research_tools.py packet <cc> <lane>   # what a researcher needs for a lane
    .venv\\Scripts\\python.exe scripts\\research_tools.py validate             # check the worker lane logs
    .venv\\Scripts\\python.exe scripts\\research_tools.py next [cc]            # what is left to run, per lane
    .venv\\Scripts\\python.exe scripts\\research_tools.py recovery [cc]        # records with no recovery research
    .venv\\Scripts\\python.exe scripts\\research_tools.py report               # outcome of the pass, per country

Reads the local worker logs in `data/candidates/sweep18/` and the committed research logs. Prints
only; it changes nothing. Research is deliberately NOT part of the daily refresh: searches are
run by a person or an agent, on purpose, against a plan committed first.

A "next query" is one the plan declared and the log says was not run. It is never a suggestion to
try a blocked site by another route: a refused endpoint stays refused and is listed as such.
"""
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import build_systems as B  # noqa: E402

SWEEP = ROOT / "data" / "candidates" / "sweep18"
SYS = ROOT / "data" / "curated" / "systems"
COUNTRIES = ("ca", "cn", "in", "sa", "us")
PLANS = {"us": "US", "ca": "CA", "cn": "CN", "in": "IN", "sa": "SA"}
DONE = ("enumerated_complete", "declared_search_complete")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def worker_lanes(cc):
    """Every lane entry a worker logged for this country."""
    out = []
    for path in sorted(glob.glob(str(SWEEP / f"{cc}_*_lanes.json"))):
        for lane in read(path).get("lanes", []):
            out.append((Path(path).name, lane))
    return out


def newest_pass(cc):
    return [p for p in read(SYS / cc / "research_log.json")["passes"] if p["kind"] == "systematic"][-1]


def log_problems(lane):
    """Why a worker's log entry cannot be taken at face value. Empty means it is consistent."""
    out = []
    if lane.get("execution") not in B.EXECUTION_STATES:
        out.append(f"execution {lane.get('execution')!r}")
    if lane.get("source_window") not in B.SOURCE_WINDOW_STATES:
        out.append(f"source window {lane.get('source_window')!r}")
    declared, run = lane.get("queries_declared"), lane.get("queries_run")
    if declared is not None and run is not None and run > declared:
        out.append(f"{run} queries run of {declared} declared")
    if lane.get("execution") == "declared_search_complete" and declared is not None and run != declared:
        out.append(f"called complete with {run} of {declared} run")
    if lane.get("execution") == "enumerated_complete" and lane.get("source_window") in ("inaccessible", "unknown"):
        out.append("enumerated, yet the source was not reachable")
    if lane.get("execution") != "not_started" and not lane.get("limitation"):
        out.append("no limitation stated")
    return out


def cmd_packet(cc, lane_id):
    plan = (ROOT / "docs" / "countries" / f"{PLANS[cc]}_LANE_PASS_18.md").read_text(encoding="utf-8")
    rows = [line for line in plan.splitlines() if line.startswith(f"| {lane_id} |")]
    print("\n".join(rows) or f"{lane_id}: not in the plan")
    old = next((x for x in newest_pass(cc)["lanes"] if x["lane"] == lane_id), None)
    print(json.dumps(old, ensure_ascii=False, indent=1))
    print("Inclusion rule:", read(SYS / "inclusion_threshold.json")["version"])
    print("Brief:", SWEEP / "RESEARCHER_BRIEF.md")


def cmd_validate():
    bad = 0
    for cc in COUNTRIES:
        for name, lane in worker_lanes(cc):
            for p in log_problems(lane):
                bad += 1
                print(f"{cc} {lane.get('lane')} ({name}): {p}")
    print("worker logs: " + ("consistent" if not bad else f"{bad} problem(s)"))
    return bad


def cmd_next(only=None):
    for cc in only or COUNTRIES:
        logged = {}
        for _, lane in worker_lanes(cc):
            logged.setdefault(lane["lane"], []).append(lane)
        print(f"== {cc}")
        for lane in newest_pass(cc)["lanes"]:
            if lane["execution"] in DONE:
                continue
            print(f"{lane['lane']}: {lane['execution']} / {lane['source_window']}, "
                  f"{lane.get('queries_run')} of {lane.get('queries_declared')} queries. {lane.get('limitation') or ''}")
            for entry in logged.get(lane["lane"], []):
                for q in entry.get("queries_not_run") or []:
                    print(f"   next: {q}")
                for b in entry.get("blocked_endpoints") or []:
                    url = b.get("url") if isinstance(b, dict) else b
                    print(f"   refused (do not route around): {url}")


def cmd_recovery(only=None):
    for cc in only or COUNTRIES:
        events = read(SYS / cc / "events.json")["events"]
        queue = [e for e in events if e["recovery"]["research_status"] == "NOT_YET_RESEARCHED"]
        print(f"== {cc}: {len(queue)} of {len(events)} not yet researched")
        for e in sorted(queue, key=lambda x: x["date"]):
            print(f"   {e['date']}  {e['event_id']}")


def cmd_report():
    for cc in COUNTRIES:
        p = newest_pass(cc)
        states = {}
        for lane in p["lanes"]:
            s = B.lane_summary_state(lane)
            states[s] = states.get(s, 0) + 1
        print(f"{cc}: {p['date']} outcome {p['outcome']}; lanes {states}")


def main(argv):
    cmd = argv[0] if argv else None
    if cmd == "packet" and len(argv) == 3:
        cmd_packet(argv[1], argv[2])
    elif cmd == "validate":
        return 1 if cmd_validate() else 0
    elif cmd == "next":
        cmd_next(argv[1:])
    elif cmd == "recovery":
        cmd_recovery(argv[1:])
    elif cmd == "report":
        cmd_report()
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main(sys.argv[1:]))
