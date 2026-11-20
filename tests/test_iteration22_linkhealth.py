"""Iteration 22, link health of the impact layer and the regional context.

`scripts/check_source_links.py --impacts` visits every citation of the impact records and the
regional context once and writes each published citation's state to
`data/curated/global_impacts/link_health.json`, which the impact build serves as `link_check`.
These tests pin the rules that make that file honest and the run polite, without the network:

  * blocked is never dead, and a failure of the checker is never dead;
  * a host is dead from DNS only when a second lookup agrees;
  * a removal is read from the page's own title and description, never from an article body;
  * one request per URL, a per-host pause, no second request to a host that refused, a cap;
  * the public file holds published citations and known states only, nothing else;
  * the redirect-safety scan reads the FINAL address of every sensitive citation and reports a
    leak by kind, never by the words that matched.
"""
import importlib.util
import json
import socket
import ssl
import urllib.error
from pathlib import Path

import pytest

from pipeline import build_systems as B
from pipeline import global_impacts as GI

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LC = _load("check_source_links")


class _Headers(dict):
    def get(self, k, default=None):
        return super().get(k.lower(), default)


def _http_error(monkeypatch, code, headers=None, body=b""):
    import io

    def raise_it(req, timeout=None, context=None):
        raise urllib.error.HTTPError(req.full_url, code, "x", _Headers(headers or {}), io.BytesIO(body))
    monkeypatch.setattr(LC.urllib.request, "urlopen", raise_it)
    return LC.fetch("https://site.example/a/b")


# --- classification ---------------------------------------------------------------------------------

def test_link_health_blocked_is_never_dead(monkeypatch):
    for code in (401, 402, 403, 406, 429, 451):
        assert _http_error(monkeypatch, code)["state"] == "blocked", code
    for code in (404, 410):
        assert _http_error(monkeypatch, code)["state"] == "dead", code
    assert _http_error(monkeypatch, 500)["state"] == "error"
    assert _http_error(monkeypatch, 503, {"cf-mitigated": "challenge"})["state"] == "blocked"
    assert _http_error(monkeypatch, 503, body=b"<title>Just a moment...</title>")["state"] == "blocked"
    assert _http_error(monkeypatch, 503)["state"] == "error"


def test_link_health_a_checker_failure_is_never_dead():
    for reason in (TimeoutError(), socket.timeout(), ssl.SSLError("bad handshake"), ValueError("x"), "odd reason",
                   socket.gaierror(11002, "temporary failure"), socket.gaierror(-3, "try again")):
        assert LC.transport_failure(reason)["state"] == "error", reason
    for reason in (ConnectionRefusedError(), ConnectionResetError()):
        assert LC.transport_failure(reason)["state"] == "blocked", reason
    # A host DNS says does not exist is not dead on one lookup: fetch_checked decides.
    assert LC.transport_failure(socket.gaierror(11001, "no such host"))["state"] == "error"


def test_link_health_dns_not_found_is_dead_only_after_a_second_lookup():
    not_found = {"state": "error", "http": None, "dns_not_found": True}
    waits = []
    answers = iter([dict(not_found), dict(not_found)])
    r = LC.fetch_checked("https://gone.example/x", fetch_one=lambda u: next(answers), sleep=waits.append)
    assert r["state"] == "dead" and "dns_not_found" not in r and waits == [LC.DNS_RETRY_WAIT]
    answers = iter([dict(not_found), {"state": "reachable", "http": 200}])
    r = LC.fetch_checked("https://flaky.example/x", fetch_one=lambda u: next(answers), sleep=lambda s: None)
    assert r["state"] == "reachable"
    asked = []
    r = LC.fetch_checked("https://ok.example/x", fetch_one=lambda u: asked.append(u) or {"state": "blocked", "http": 403},
                         sleep=lambda s: None)
    assert r["state"] == "blocked" and len(asked) == 1, "a refusal is never asked twice"


def test_link_health_removal_is_read_from_the_title_and_description_only():
    assert LC.removal_notice("<html><title>x</title></html>", "Page not found | Example News")
    assert LC.removal_notice("<html></html>", "404 - Example")
    assert LC.removal_notice('<meta property="og:description" content="This post was deleted by its author.">', "Example")
    assert LC.removal_notice('<meta name="description" content="This page is no longer available.">', "Example")
    body = "<html><title>Hackers deface utility site</title><p>The post was deleted within hours. Page not found.</p>"
    assert not LC.removal_notice(body, "Hackers deface utility site"), "an article body quoting a deletion is not one"
    assert not LC.removal_notice("<html></html>", "The dam no longer exists, officials say")


# --- traffic -----------------------------------------------------------------------------------------

def test_link_health_one_request_per_url_a_pause_per_host_no_retry_after_refusal_and_a_cap():
    asked, waits = [], []

    def fake(url):
        asked.append(url)
        return {"state": "blocked", "http": 403} if "refuses.example" in url else {"state": "reachable", "http": 200}
    urls = ["https://a.example/1", "https://a.example/2", "https://a.example/3",
            "https://refuses.example/1", "https://refuses.example/2", "https://b.example/1"]
    res = LC.check_all(urls, {}, fetch_one=fake, sleep=waits.append)
    assert sorted(asked) == sorted(set(asked)), "one request per URL"
    assert "https://refuses.example/2" not in asked and res["https://refuses.example/2"]["state"] == "blocked"
    assert len([w for w in waits if w > 0]) >= 2 and all(w <= LC.PER_HOST_DELAY for w in waits)
    assert LC.PER_HOST_DELAY >= 1 and LC.TIMEOUT > 0
    asked.clear()
    res = LC.check_all(urls, {}, cap=2, fetch_one=fake, sleep=lambda s: None)
    assert len(asked) == 2
    assert sum(r["state"] == "unchecked" for r in res.values()) >= 3


def test_link_health_user_agent_names_the_project_and_nothing_personal():
    assert "EnergyDisruptionMonitor" in LC.UA
    assert "@" not in LC.UA and "://" not in LC.UA


# --- redirects ---------------------------------------------------------------------------------------

def test_link_health_impact_redirect_to_a_home_page_is_not_dead():
    def results():
        return {"https://n.example/story-about-a-thing": {"state": "redirected", "redirect": True,
                                                         "final_url": "https://n.example/"},
                "https://n.example/x/1": {"state": "redirected", "redirect": True,
                                          "final_url": "https://n.example/cdn-cgi/challenge?x"}}
    impacts = results()
    LC.classify_redirects(impacts, gone_is_dead=False)
    assert impacts["https://n.example/story-about-a-thing"]["state"] == "redirected"
    assert impacts["https://n.example/story-about-a-thing"]["redirect_kind"] == "general_page"
    assert impacts["https://n.example/x/1"]["state"] == "blocked"
    countries = results()
    LC.classify_redirects(countries, gone_is_dead=True)
    assert countries["https://n.example/story-about-a-thing"]["state"] == "dead"


def test_link_health_country_file_carries_only_its_five_states():
    res = {"https://a.example/1": {"state": "deleted"}, "https://a.example/2": {"state": "unchecked"},
           "https://a.example/3": {"state": "blocked"}}
    assert LC.link_states(res, set(res)) == {"https://a.example/3": "blocked"}
    assert set(LC.SYSTEM_STATES) == set(B.LINK_STATES)


# --- the public file -------------------------------------------------------------------------------

def test_link_health_public_file_holds_published_citations_and_known_states_only(tmp_path):
    citations = LC.impact_citations(GI.FIXTURE_DIR)
    published = [c[3] for c in citations]
    results = {published[0]: {"state": "reachable", "title": "t", "final_url": published[0], "hash": "h"},
               published[1]: {"state": "unchecked"},
               published[2]: {"state": "archived_copy"},
               published[3]: {"state": "fine"},
               "https://not-cited.example/x": {"state": "dead"}}
    out = tmp_path / "link_health.json"
    LC.write_impacts_public(results, citations, path=out)
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert set(doc) == {"checked", "note", "link_states"}, "no title, hash, final address or finding leaves"
    assert doc["link_states"] == {published[0]: "reachable"}
    events, context, _ = GI.load_curated(GI.FIXTURE_DIR)
    assert GI.link_problems(doc["link_states"], events, context) == []


def test_link_health_committed_file_speaks_only_of_published_citations():
    path = GI.LINK_FILE
    if not path.exists():
        pytest.skip("no impact link check recorded")
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert set(doc) == {"checked", "note", "link_states"}
    assert set(doc["link_states"].values()) <= set(GI.ids("link_states")) - {"unchecked", "archived_copy"}
    events, context, _ = GI.load_curated()
    assert GI.link_problems(doc["link_states"], events, context) == []
    assert "not that the page is gone" in doc["note"]


# --- redirect safety -------------------------------------------------------------------------------

def _lists():
    """Synthetic stand-ins for the pipeline's lists: one Gulf system with one region and one
    facility name. The real lists come from safety_lists(); here the rules are what is tested."""
    return {"gulf": ("ir",), "gulf_a3": frozenset({"IRN"}), "sid_of": {"IRN": "ir", "USA": "us"},
            "phrases": {"ir": ["synthabad"]}, "unit_words": {"ir": ["synthabad"]},
            "facility": {"ir": {"synthoil"}, "us": set()},
            "facility_types": frozenset(B.fold(w) for w in LC.FACILITY_TYPE_WORDS)}


def _record(iid, a3, policy="standard", ref="s1", url="https://news.example/?p=123"):
    return {"impact_id": iid, "country_a3": a3, "publication_policy": policy, "sources": [{"ref": ref, "url": url}]}


def _hits(items, results):
    cites = [("context" if "entries" in x else "impact", x.get("impact_id") or x.get("id"), s["ref"], s["url"], x)
             for x in items for s in x["sources"]]
    return LC.safety_hits(cites, results, _lists())


def test_link_health_safety_scan_reads_the_final_address():
    gulf = _record("imp-synthetic-irn", "IRN")
    final = "https://news.example/region/synthabad-synthoil-restarted-after-drone-strike"
    hits = _hits([gulf], {gulf["sources"][0]["url"]: {"state": "redirected", "final_url": final}})
    kinds = {h["kind"] for h in hits}
    assert {"place", "facility", "status", "method"} <= kinds, kinds
    assert all(h["where"] == "final address" and h["field"] == "sources[s1].url" for h in hits)
    text = json.dumps(hits)
    assert "synthabad" not in text and "synthoil" not in text, "a hit never quotes the leaked words"
    assert "drone" not in text and "restarted" not in text and "news.example" not in text


def test_link_health_safety_scan_covers_abstracted_gulf_and_context_but_not_others():
    final = "https://news.example/x/power-plant-drone-attack-restored"
    abstracted = _record("imp-2025-01-01-usa-electricity-attack-abcdef", "USA", policy="country_abstracted")
    ordinary = _record("imp-2025-01-01-usa-electricity-storm", "USA")
    ctx = {"id": "ctx-2026-01-01-synthetic", "entries": True,
           "sources": [{"ref": "s1", "url": "https://agency.example/n/9"}]}
    results = {abstracted["sources"][0]["url"]: {"final_url": final},
               "https://agency.example/n/9": {"final_url": "https://agency.example/notice/tanker-tracking-resumed"}}
    hits = _hits([abstracted, ordinary, ctx], results)
    by = {(h["id"], h["kind"]) for h in hits}
    assert {(abstracted["impact_id"], k) for k in ("method", "status", "facility_type")} <= by
    assert not any(i == ordinary["impact_id"] for i, _ in by), "a standard record outside the Gulf is not scanned"
    assert {("ctx-2026-01-01-synthetic", "route"), ("ctx-2026-01-01-synthetic", "status")} <= by


def test_link_health_an_unread_short_link_on_a_sensitive_record_is_a_hit():
    gulf = _record("imp-synthetic-irn", "IRN")
    assert {h["kind"] for h in _hits([gulf], {gulf["sources"][0]["url"]: {"state": "blocked"}})} == {"unresolved"}
    read = {gulf["sources"][0]["url"]: {"state": "redirected", "final_url": "https://news.example/a/power-cuts-reported-nationwide"}}
    assert _hits([gulf], read) == []


@pytest.mark.skipif(not (RAW / "ne_10m_admin_1.geojson").exists(), reason="Natural Earth cache not present")
def test_link_health_safety_lists_are_the_pipelines_own():
    from pipeline import systems
    import import_candidates as IC
    L = LC.safety_lists()
    assert L["gulf"] == tuple(systems.GROUPS["gulf_littoral"]["members"]) and len(L["gulf"]) == 8
    assert L["gulf_a3"] == {"IRN", "IRQ", "KWT", "SAU", "BHR", "QAT", "ARE", "OMN"}
    assert all(L["phrases"][sid] == GI.system_unit_phrases(sid) for sid in L["gulf"])
    assert set(LC.FACILITY_TYPE_WORDS) <= IC.GENERIC_NAME_WORDS
