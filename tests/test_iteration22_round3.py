"""Iteration 22, release closure round 3: what the verifier's NB-1, NS-1, NS-2 and NS-3 added.

  NS-2  research broadly, publish narrowly: the names of places inside a unit of a Gulf system that are
        not the unit or its capital (export terminals, refinery, LNG and gas-processing sites, ports,
        towns) are read by the import gate and never served, so the site search cannot turn a site name
        into its first-level region.
  NB-1  a served figure rests on a source that contains it: the welfare-check figure that came from a
        removed citation is gone from the record.
  NS-1  a derived claim does not carry what section 3.1 removed from the effect.

NS-3 (the precision sentence says only what served records do) is tested beside the sentence's other
tests in tests/test_iteration22_impacts.py.
"""
import json
from pathlib import Path

import pytest

from pipeline import build_systems as B

ROOT = Path(__file__).resolve().parent.parent
CURATED = ROOT / "data" / "curated" / "systems"
PROCESSED = ROOT / "data" / "processed"
CAMPAIGN = ("ae", "bh", "iq", "ir", "kw", "om", "qa")

# The reviewed list, pinned by name: site names the round-2 review found in the served aliases. Each
# stays gate-only; moving one back into `unit_aliases` serves it again and fails here.
SITE_NAMES = {
    "ir": ["Asaluyeh", "Assaluyeh", "عسلویه", "Kangan", "Qeshm", "Abadan", "Mahshahr"],
    "kw": ["Mina al-Ahmadi", "Mina Abdullah", "Zour", "Al-Zour", "Shuaiba", "الشعيبة"],
    "bh": ["Sitra", "Awali"],
    "qa": ["Ras Laffan", "Laffan", "راس لفان", "Mesaieed", "Umm Said", "Dukhan"],
    "ae": ["Jebel Ali", "Ruwais", "Das Island", "Habshan", "Hamriyah"],
    "om": ["Mina al Fahal", "Duqm"],
}


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _geo(sid):
    return _json(CURATED / sid / "system.json")["geography"]


def _folded_aliases(geo, key):
    return {B.fold(a) for names in (geo.get(key) or {}).values() for a in names}


def test_site_names_are_gate_only_and_never_in_the_served_aliases():
    for sid, names in SITE_NAMES.items():
        geo = _geo(sid)
        served = _folded_aliases(B.served_geography(geo, sid), "unit_aliases")
        gate = _folded_aliases(geo, "gate_aliases")
        for name in names:
            assert B.fold(name) in gate, (sid, name, "the gate must still read it")
            assert B.fold(name) not in served, (sid, name, "a site name is served")


def test_the_served_geography_carries_no_gate_only_key_and_the_gate_still_reads_every_name():
    for sid in CAMPAIGN:
        geo = _geo(sid)
        out = B.served_geography(geo, sid)
        assert not set(out) & set(B.GATE_ONLY_GEOGRAPHY), sid
        assert not _folded_aliases(out, "unit_aliases") & _folded_aliases(geo, "gate_aliases"), sid
        # The gate's rows (unit_name_rows) still hold every gate-only name.
        rows = {B.fold(n) for _, n in B.unit_name_rows({"geography": geo}, [])}
        assert _folded_aliases(geo, "gate_aliases") <= rows, sid


def test_a_name_listed_both_served_and_gate_only_is_refused():
    geo = {"unit_aliases": {"QA-KH": ["Al Khor", "Ras Laffan"]}, "gate_aliases": {"QA-KH": ["ras laffan"]}}
    with pytest.raises(ValueError, match="also listed as gate-only"):
        B.served_geography(geo, "qa")


def test_the_built_system_files_serve_no_gate_only_name():
    for sid in CAMPAIGN:
        for base in (PROCESSED / "systems" / sid, ROOT / "web" / "public" / "data" / "systems" / sid):
            path = base / "system.json"
            if not path.exists():
                pytest.skip("no build yet")
            geo = _json(path)["geography"]
            assert not set(geo) & set(B.GATE_ONLY_GEOGRAPHY), (path, "gate-only key served")
            leaked = _folded_aliases(geo, "unit_aliases") & _folded_aliases(_geo(sid), "gate_aliases")
            assert not leaked, (path, sorted(leaked))


def test_every_served_alias_list_still_names_each_unit_in_two_scripts():
    """Moving the site names out must not leave a unit the search can find in only one script: the
    unit's own name and its capital stay served."""
    for sid in CAMPAIGN:
        al = B.served_geography(_geo(sid), sid).get("unit_aliases") or {}
        feats = _json(ROOT / "web" / "public" / "data" / "systems" / sid / "regions.geojson")["features"]
        for f in feats:
            code = f["properties"]["code"]
            if code.endswith("~"):
                continue
            names = [f["properties"]["name"], *al.get(code, [])]
            assert any(n.isascii() for n in names) and any(not n.isascii() for n in names), (sid, code)


# --- served impact records: NB-1 and NS-1 ---------------------------------------------------------

def _served(impact_id):
    path = PROCESSED / "global" / "impacts.json"
    if not path.exists():
        pytest.skip("no build yet")
    doc = _json(path)
    return next(r for r in doc["records"] + doc["attempts"] if r["impact_id"] == impact_id)


def test_the_welfare_check_figure_rests_on_a_source_that_contains_it():
    r = _served("imp-2026-07-08-aus-telecom-mobile-network-outage")
    assert "639" not in json.dumps(r, ensure_ascii=False)
    for entry in r["civilian_service_impact"]:
        if isinstance(entry["affected"].get("value"), (int, float)):
            refs = set(entry["source_refs"])
            claims = " ".join(s.get("derived_claim") or "" for s in r["sources"] if s["ref"] in refs)
            assert f"{entry['affected']['value']:,}".replace(",", "") in claims.replace(",", ""), entry


def test_a_section_3_1_record_keeps_the_fallback_out_of_its_derived_claims():
    r = _served("imp-2022-03-31-deu-electricity-wind-manufacturer-it-incident-remote-access")
    text = " ".join([r["effect"]] + [s.get("derived_claim") or "" for s in r["sources"]]).lower()
    for phrase in ("alternative remote", "most of the fleet", "unaffected", "grid-operator communication"):
        assert phrase not in text, phrase

