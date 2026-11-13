"""Iteration 21: country pages — the event card's origin count, headlines, the empty page.

The card counts each record's originating statements in TypeScript (web/src/global/evidence.ts).
The country's published totals are counted in Python (pipeline/build_systems.py). Two copies of
one rule drift unless something runs both on the same records, so these tests load the
TypeScript module in Node and compare it, record by record, with the Python rule on every served
record and on constructed cases the served data does not happen to contain.

Node is not on the machine PATH (CLAUDE.md); the tests look for the portable copy beside the
repository, or EDM_NODE. Without a Node that can strip types they skip and say so; vitest runs
the same mirror against the served totals in CI.
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from pipeline import build_systems as B
from pipeline import systems

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web" / "public" / "data"
SRC = ROOT / "web" / "src" / "global"
needs_payload = pytest.mark.skipif(not (WEB / "global" / "manifest.json").exists(), reason="no built payload")


def _node():
    if os.environ.get("EDM_NODE"):
        return os.environ["EDM_NODE"]
    starts = [ROOT] + ([Path(os.environ["EDM_GIT_ROOT"])] if os.environ.get("EDM_GIT_ROOT") else [])
    for start in starts:
        for d in [start, *start.parents]:
            for name in ("node.exe", "node"):
                if (d / "tools" / "node" / name).is_file():
                    return str(d / "tools" / "node" / name)
    return shutil.which("node")


def _run_ts(tmp_path, script, data):
    """Run `script` (an ES module body that receives `input` and the two modules) in Node."""
    node = _node()
    if not node:
        pytest.skip("no Node found to load the TypeScript mirror (set EDM_NODE)")
    evidence = (SRC / "evidence.ts").resolve().as_uri()
    copy = (SRC / "countryCopy.ts").resolve().as_uri()
    (tmp_path / "input.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    harness = tmp_path / "harness.mjs"
    harness.write_text(
        "import { readFileSync } from 'node:fs';\n"
        f"import * as ev from '{evidence}';\n"
        f"import * as copy from '{copy}';\n"
        "const input = JSON.parse(readFileSync(process.argv[2], 'utf-8'));\n"
        f"const out = (() => {{ {script} }})();\n"
        "process.stdout.write(JSON.stringify(out));\n", encoding="utf-8")
    r = subprocess.run([node, "--experimental-strip-types", "--no-warnings", str(harness), str(tmp_path / "input.json")],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0 and "bad option" in r.stderr:
        pytest.skip(f"this Node cannot strip TypeScript types: {r.stderr.strip()[:120]}")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _served():
    out = {}
    for sid in systems.COUNTRY_SYSTEMS:
        out[sid] = {"events": json.loads((WEB / "systems" / sid / "events.json").read_text(encoding="utf-8"))["events"],
                    "system": json.loads((WEB / "systems" / sid / "system.json").read_text(encoding="utf-8"))}
    return out


ORIGINS_JS = ("return Object.fromEntries(Object.entries(input).map(([sid, d]) => [sid, {"
              "per: d.events.map((e) => [...ev.eventOrigins(e)].sort()),"
              "lines: d.events.map((e) => ev.countLine(ev.originSummary(e))),"
              "totals: ev.originTotals(d.events)}]));")


@needs_payload
def test_the_card_counts_origins_exactly_as_the_pipeline_does_on_every_served_record(tmp_path):
    served = _served()
    got = _run_ts(tmp_path, ORIGINS_JS, {sid: {"events": d["events"]} for sid, d in served.items()})
    checked = fewer_origins_than_pages = discovery_only = wire = 0
    for sid, d in served.items():
        for e, ts in zip(d["events"], got[sid]["per"]):
            py = sorted(B.event_origins(e))
            assert ts == py, (sid, e["event_id"], ts, py)
            checked += 1
            fewer_origins_than_pages += len(py) < len({s["url"] for s in e["sources"]})
            discovery_only += not py
            wire += any(o.startswith("wire:") for o in py)
        sh = d["system"].get("source_health") or {}
        if "single_origin_events" in sh:
            assert got[sid]["totals"] == {"single_origin_events": sh["single_origin_events"],
                                          "discovery_only_events": sh["discovery_only_events"]}, sid
    assert checked > 0
    # The served records exercise every branch the rule has; otherwise this test proves little.
    assert fewer_origins_than_pages > 0 and discovery_only > 0 and wire > 0, (fewer_origins_than_pages, discovery_only, wire)


CASES = [
    # one agency, three pages: one origin
    [{"url": "https://www.agency.gov/a", "publisher": "Agency"}, {"url": "https://agency.gov/b", "publisher": "Agency"},
     {"url": "https://news.agency.gov/c", "publisher": "Agency news"}],
    # one wire story republished by two outlets: one origin
    [{"url": "https://boereport.com/x", "publisher": "BOE Report (Reuters)"},
     {"url": "https://www.theglobeandmail.com/y", "publisher": "Globe and Mail / Reuters"}],
    [{"url": "https://a.example.com/x", "publisher": "Outlet (AFP)"}, {"url": "https://b.example.org/y", "publisher": "Other (AFP)"},
     {"url": "https://c.example.net/z", "publisher": "Third"}],
    # discovery aids count for nothing, whatever the publisher field or host says
    [{"url": "https://en.wikipedia.org/wiki/X", "publisher": "Wikipedia"}],
    [{"url": "https://www.indexbox.io/blog/x", "publisher": "IndexBox"}, {"url": "https://example.com/z", "publisher": "Wikipedia (English)"}],
    # second-level country domains, ports, no scheme, a word inside another word
    [{"url": "https://news.bbc.co.uk/x", "publisher": "BBC"}, {"url": "https://www.bbc.co.uk:443/y", "publisher": "BBC"},
     {"url": "pib.gov.in/z", "publisher": "PIB"}, {"url": "https://spacenews.com/q", "publisher": "SpaceNews"}],
    [{"url": "https://aleqt.com/x", "publisher": "Al-Eqtisadiah (republishing SPA)"}, {"url": "https://www.spa.gov.sa/y", "publisher": "SPA"}],
    [{"url": "https://x.com/a", "publisher": None}, {"url": "", "publisher": "Wire copy"}],
]


def test_the_card_counts_origins_as_the_pipeline_does_on_constructed_cases(tmp_path):
    got = _run_ts(tmp_path, "return input.map((sources) => ({origins: [...ev.eventOrigins({sources})].sort(),"
                            " summary: ev.originSummary({sources})}));", CASES)
    for sources, ts in zip(CASES, got):
        py = sorted(B.event_origins({"sources": sources}))
        assert ts["origins"] == py, (sources, ts["origins"], py)
        assert ts["summary"]["origins"] == py
        assert ts["summary"]["discoveryOnly"] == (not py)
    # The cases themselves: a republished wire is one origin, three pages of one agency are one.
    assert [len(x["origins"]) for x in got[:4]] == [1, 1, 2, 0]
    assert got[0]["summary"]["pages"] == 3


@needs_payload
def test_no_headline_is_allowed_on_a_campaign_or_country_level_attack_record(tmp_path):
    served = _served()
    covered = [e for e in served["sa"]["events"] if e.get("publication")]
    assert covered, "no campaign-covered record is served to check"
    titled = {"url": "https://example.com/x", "title_original": "عنوان", "title_en": "A headline", "language": "ar"}
    base = dict(served["kw"]["events"][0], sources=[titled], publication=None, cause="technical")
    cases = {
        "covered": [dict(e, sources=[titled]) for e in covered],
        "attack": [dict(base, cause="kinetic_strike", geography_precision="country")],
        "plain": [base],
    }
    got = _run_ts(tmp_path, "return Object.fromEntries(Object.entries(input.cases).map(([k, es]) =>"
                            " [k, es.map((e) => ev.headlinesAllowed(e, input.systems[e.event_id.slice(0, 2)]))]));",
                  {"cases": cases, "systems": {"sa": served["sa"]["system"], "kw": served["kw"]["system"]}})
    assert got["covered"] == [False] * len(covered)
    assert got["attack"] == [False]
    assert got["plain"] == [True], "the guard must not hide every headline"
    card = (SRC / "EventCard.tsx").read_text(encoding="utf-8")
    # Every condition that renders a headline or its gloss starts with the guard.
    conditions = re.findall(r"\{[^{}]*?\bs\.title_(?:original|en) &&", card)
    assert len(conditions) >= 2, conditions
    for c in conditions:
        assert c.startswith("{headlines && "), f"a headline rendered without the campaign guard: {c}"
    inspector = card[card.index("function EvidenceInspector"):]
    assert "title_original" not in inspector and "title_en" not in inspector, "the inspector never repeats a headline"


def test_an_empty_country_page_says_what_the_absence_means_and_never_prints_a_zero(tmp_path):
    copy = _run_ts(tmp_path, "return { lead: copy.EMPTY_CORPUS_LEAD, preview: copy.RESEARCH_PREVIEW_DEFINITION };", {})
    assert copy["lead"].startswith("No qualifying records in the current reviewed corpus")
    assert "not evidence that no disruption occurred" in copy["lead"]
    assert "the absence of a record is not evidence that no disruption occurred" in copy["preview"]
    # "no disruption occurred" is the sentence that denies it; "no disruptions" is the claim.
    zero = re.compile(r"\b0 (disruptions?|events?|records?|incidents?)\b|\bno disruptions\b|\bno disruption (was|has|in)\b"
                      r"|\bzero (disruptions?|events?|records?)\b", re.I)
    for name in ("countryCopy.ts", "EmptyCorpus.tsx", "EventCard.tsx", "CountryView.tsx"):
        # Comments may name what is forbidden; reader copy may not say it.
        text = re.sub(r"(?s)/\*.*?\*/|//[^\n]*", "", (SRC / name).read_text(encoding="utf-8"))
        assert not zero.search(text), (name, zero.search(text).group(0))
    empty = (SRC / "EmptyCorpus.tsx").read_text(encoding="utf-8")
    assert "{EMPTY_CORPUS_LEAD}" in empty and "held" not in empty.lower().replace("held back", "")


def test_the_research_preview_definition_lives_in_one_module():
    copy = (SRC / "countryCopy.ts").read_text(encoding="utf-8")
    assert "RESEARCH_PREVIEW_DEFINITION" in copy
    for path in SRC.glob("*.tsx"):
        text = path.read_text(encoding="utf-8")
        # No second wording of the definition, and no hover-only explanation of it.
        assert "the systematic search is still incomplete" not in text, path.name
        assert not re.search(r'title="Research preview', text), path.name
        if "research_preview" in text and path.name != "Disclosure.tsx":
            assert re.search(r"ResearchPreview(Badge|Tag)|RESEARCH_PREVIEW_DEFINITION", text), path.name


def test_country_page_copy_carries_no_internal_process_language():
    for name in ("CountryView.tsx", "EventCard.tsx", "EmptyCorpus.tsx", "countryCopy.ts", "evidence.ts"):
        text = (SRC / name).read_text(encoding="utf-8")
        # Reader-facing strings only: JSX text and string literals, not comments.
        strings = re.findall(r'"[^"\n]{12,}"|`[^`]{12,}`|>[^<>{}\n]{12,}<', re.sub(r"(?s)/\*.*?\*/|//[^\n]*|\{/\*.*?\*/\}", "", text))
        for s in strings:
            assert not re.search(r"\bopen decision\b|\bproject owner\b|\bonboarded\b|\bD-\d\d\b", s), (name, s)


@needs_payload
def test_every_served_citation_link_state_is_a_known_state_and_comes_from_the_curated_check():
    health = json.loads((ROOT / "data" / "curated" / "systems" / "source_link_health.json").read_text(encoding="utf-8"))
    states = health.get("link_states") or {}
    seen = 0
    for sid, d in _served().items():
        for e in d["events"]:
            for s in e["sources"]:
                if "link_check" in s:
                    assert s["link_check"] in B.LINK_STATES
                    assert states.get(s["url"]) == s["link_check"], (sid, s["url"])
                    seen += 1
                else:
                    assert s["url"] not in states, (sid, s["url"], "a recorded state was dropped")
    assert seen > 0
    # Nothing beyond the state leaves the local file.
    assert all(v in B.LINK_STATES for v in states.values())
