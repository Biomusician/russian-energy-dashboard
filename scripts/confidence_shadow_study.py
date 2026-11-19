"""Shadow study: what Evidence Confidence v2 would say about the theatre's incidents.

    .venv\\Scripts\\python.exe scripts\\confidence_shadow_study.py            # print the study
    .venv\\Scripts\\python.exe scripts\\confidence_shadow_study.py --write    # and refresh the doc section

THE QUESTION. The theatre's index multiplies each incident by a confidence weight set from how many
distinct hosts its citations sit on (confirmed / probable / possible; pipeline/fetch_wikipedia.py,
methodology/scoring.json). Evidence Confidence v2 asks a related question in a different way: who
is speaking, how many INDEPENDENT originating statements there are, whether the effect is
supported. This study computes the v2 category for every scored theatre incident from the citations
it already carries, sets it beside the v1 label, and asks what the index would be under a stated
candidate mapping from v2 categories to weights.

IT CHANGES NOTHING. The index is recomputed in memory by the real builder (`build_index.build`),
with the weights substituted for the length of one call and restored in a `finally`. No payload is
written: the build's incidental writes go to a temporary directory that is deleted. scoring.json,
build_index and every served theatre value are untouched, and a test pins that
(tests/test_iteration22_confidence.py).

WHAT THE REPLAY IS. One build yields the whole index series under today's corpus and code, so the
"earlier dates" are earlier EVALUATION dates of today's record, not reconstructions of what was
known then. That answers the question asked here (is the difference between the two weightings
stable over time?) without a second scoring model and without the network.

LIMITS, stated in the output too. Theatre citations carry no source role, so every one is treated
as independent media reporting unless its address is on a recognisably official domain; that
detection is deliberately narrow. No theatre citation records whether a reviewer opened it, so that
component is zero throughout. The Wikipedia strike table states that a strike was reported, not
what it did, so its incidents carry no supported effect.
"""
import argparse
import collections
import copy
import datetime as dt
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import build_assets, build_index, evidence_confidence, fetch_wikipedia, outputs  # noqa: E402
from pipeline import recovery as recovery_mod  # noqa: E402
from pipeline import run as R  # noqa: E402
from pipeline.build_systems import registered_domain  # noqa: E402
from pipeline.config import SECTORS, WINDOW_START  # noqa: E402

DOC = ROOT / "docs" / "EVIDENCE_CONFIDENCE_V2.md"
BEGIN, END = "<!-- shadow-study:begin -->", "<!-- shadow-study:end -->"

# The candidate mapping the study evaluates. It is a question put to the data, not a proposal that
# has been accepted: nothing reads it but this script.
CANDIDATE_WEIGHTS = {"HIGH": 1.0, "MODERATE": 0.75, "LIMITED": 0.45, "PRELIMINARY": 0.2}
# Off the scale: a Disputed incident, and one v2 does not assess (cited through a discovery aid
# only), have no category to map. Leaving them at their v1 weight made a disputed incident the
# heaviest in the shadow index (1.0, where no undisputed incident exceeded 0.75). The study states
# a decision instead: neither weighs more than the lowest mapped category.
OFF_SCALE = ("DISPUTED", "NOT_ASSESSED")
OFF_SCALE_WEIGHTS = {k: min(CANDIDATE_WEIGHTS.values()) for k in OFF_SCALE}
SHADOW_WEIGHTS = {**CANDIDATE_WEIGHTS, **OFF_SCALE_WEIGHTS}
V1_LABELS = ("confirmed", "probable", "possible", "unverified")
V2_LABELS = ("HIGH", "MODERATE", "LIMITED", "PRELIMINARY", "DISPUTED", "NOT_ASSESSED")
REPLAY_DAYS_BACK = (90, 180, 365)

# Deliberately narrow: a label that is exactly gov / gouv / mil, or one of two named hosts. A
# governor's channel quoted by a news site, and state media, are media here.
OFFICIAL_LABELS = {"gov", "gouv", "mil"}
OFFICIAL_HOSTS = {"kremlin.ru", "government.ru"}
MONTHS = {m: i + 1 for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july",
                                          "august", "september", "october", "november", "december"))}


def official_domain(url):
    host = (url or "").split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0].lower()
    return bool(OFFICIAL_LABELS & set(host.split("."))) or registered_domain(url) in OFFICIAL_HOSTS


def iso_date(text):
    """A citation's date as ISO, from the forms the strike table uses ("25 January 2024",
    "January 25, 2024", "January 2024", ISO). None when it cannot be read: never a guess."""
    if not text:
        return None
    t = str(text).strip()
    if re.fullmatch(r"\d{4}(-\d{2}){0,2}", t):
        return t
    words = re.findall(r"[A-Za-z]+|\d+", t)
    month = next((MONTHS[w.lower()] for w in words if w.lower() in MONTHS), None)
    year = next((w for w in words if re.fullmatch(r"\d{4}", w)), None)
    day = next((int(w) for w in words if re.fullmatch(r"\d{1,2}", w)), None)
    if not (month and year):
        return None
    return f"{year}-{month:02d}-{day:02d}" if day and 1 <= day <= 31 else f"{year}-{month:02d}"


def v2_source(citation):
    """A theatre citation in the shape the v2 model reads. Role is all the theatre does not record."""
    return {"url": citation.get("url"), "publisher": citation.get("publisher"),
            "date": iso_date(citation.get("date")),
            "source_role": "government" if official_domain(citation.get("url")) else "media",
            # No theatre citation records a reviewer opening it. None, not False: not recorded.
            "opened": None}


def effect_specificity(incident):
    """Quantified where the incident carries a capacity figure; described where the record states
    a damage status; otherwise the source reports a strike and no effect."""
    if any(incident.get(k) is not None for k in ("capacity_affected_mw", "capacity_affected_mtpa", "capacity_affected_pct")):
        return "quantified"
    return "described" if incident.get("status") not in (None, "", "unknown") else "vague"


def shadow(incident):
    dispute = {"about": "effect"} if incident.get("conflicting_reports") else None
    return evidence_confidence.assess([v2_source(c) for c in incident.get("sources") or []],
                                      incident["date"], incident.get("date_end"),
                                      effect_specificity(incident), dispute)


def index_inputs(as_of):
    """The arguments `pipeline.run` hands the index builder, assembled the same way. Kept honest by
    `study()`: the unsubstituted result must equal the served headline for the same date."""
    assets, lines, region_meta = build_assets.build()
    assets += R.load_asset_supplement(region_meta)
    wiki_facilities, wiki_incidents, _warnings, _rev = R.build_wikipedia(as_of)
    _refineries, refining_total, _recon, _rrev = R.build_refineries(as_of)
    for inc in wiki_incidents:
        inc["origin"] = "wikipedia_strike_table"
        inc.setdefault("status", "unknown")
    incidents = wiki_incidents + R.load_curated_incidents()
    incidents = [i for i in incidents if i["date"] >= WINDOW_START[:len(i["date"])]]
    incidents.sort(key=lambda i: i["date"])
    district_of = {m["code"]: m["district"] for m in region_meta.values()}
    for inc in incidents:
        if inc.get("region_code"):
            inc["_district"] = district_of.get(inc["region_code"])
    in_aoi = [i for i in incidents if i.get("region_code")]
    recovery_by_incident, _policy = recovery_mod.apply_campaign_embargo(
        R.load_recovery_records(), incidents, as_of, None)
    tx = collections.Counter(
        f["properties"]["region_code"] for f in lines
        if f["properties"].get("asset_class") in ("transmission_line", "interconnector")
        and f["properties"].get("region_code"))
    return dict(incidents=in_aoi, facilities=wiki_facilities, assets=assets,
                refinery_total_mtpa=refining_total, region_meta=region_meta, as_of=as_of,
                recovery_by_incident=recovery_by_incident, transmission_lines_by_region=dict(tx),
                region_context=R.load_region_context(),
                # First-seen dates feed the lifecycle display only, never a score.
                first_seen={})


def run_index(kwargs, weights=None, labels=None):
    """The real builder's national series. With `weights`, the confidence weights are substituted
    for this one call and each incident's label replaced by `labels[incident_id]`; restored in
    `finally`, because a study that leaves the model altered would be the worst version of this."""
    kwargs = {**kwargs, "incidents": copy.deepcopy(kwargs["incidents"])}
    declared = dict(build_index.SCORING["confidence_weights"])
    try:
        if weights is not None:
            for inc in kwargs["incidents"]:
                inc["confidence"] = labels[inc["incident_id"]]
            build_index.SCORING["confidence_weights"].update(weights)
        return build_index.build(**kwargs)[0]
    finally:
        build_index.SCORING["confidence_weights"].clear()
        build_index.SCORING["confidence_weights"].update(declared)


def _at(series, i):
    return {"date": series["dates"][i], "esdi": series["esdi"][i],
            "sectors": {s: series["sectors"][s][i] for s in SECTORS}}


def _ratio(shadow_value, current_value):
    # None where the index was zero: a ratio to nothing is not a number.
    return round(shadow_value / current_value, 2) if current_value else None


def _nearest(dates, target):
    return min(range(len(dates)), key=lambda i: abs((dt.date.fromisoformat(dates[i]) - target).days))


def study(as_of):
    kwargs = index_inputs(as_of)
    incidents = kwargs["incidents"]
    declared = {k: v for k, v in build_index.SCORING["confidence_weights"].items() if not k.startswith("_")}
    results = {i["incident_id"]: shadow(i) for i in incidents}

    cross = {a: {b: 0 for b in V2_LABELS} for a in V1_LABELS}
    change = {"higher": 0, "lower": 0, "same": 0, "off_scale": 0}
    labels, components = {}, collections.Counter()
    citations = official = dated = 0
    for inc in incidents:
        v1 = inc.get("confidence") or "possible"
        r = results[inc["incident_id"]]
        # No category is "not assessed", a state of its own: never folded into Preliminary.
        label = r["category"] or "NOT_ASSESSED"
        cross.setdefault(v1, {b: 0 for b in V2_LABELS})[label] += 1
        components[r["components"]["directness"]["tier"] or "none"] += 1
        for c in inc.get("sources") or []:
            citations += 1
            official += official_domain(c.get("url"))
            dated += iso_date(c.get("date")) is not None
        labels[inc["incident_id"]] = label
        change["off_scale"] += label in OFF_SCALE
        old, new = declared.get(v1, 0.45), SHADOW_WEIGHTS[label]
        change["higher" if new > old else "lower" if new < old else "same"] += 1

    # Where the two disagree, and why: each line is a property of the citations, countable by hand.
    why = collections.Counter()
    for inc in incidents:
        r = results[inc["incident_id"]]
        cites = inc.get("sources") or []
        n_hosts = len({fetch_wikipedia._host(c.get("url")) for c in cites} - {None})
        n_origins = r["components"]["origins"]["count"]
        aid = any(evidence_confidence.origin_of(v2_source(c)) is None for c in cites)
        why["cite_a_discovery_aid"] += aid
        if (inc.get("confidence") or "possible") == "confirmed":
            why["labelled_confirmed"] += 1
            why["labelled_confirmed_citing_two_or_more_hosts"] += n_hosts >= 2
            # A curated incident's label is typed by the curator, not derived from its citations.
            why["labelled_confirmed_by_the_curator"] += inc.get("origin") == "curated"
        if n_hosts >= 2:
            why["two_or_more_hosts"] += 1
            why["two_or_more_hosts_and_two_or_more_origins" if n_origins >= 2
                else "two_or_more_hosts_but_one_origin" if n_origins == 1
                else "two_or_more_hosts_but_no_origin"] += 1
            why["two_or_more_hosts_one_of_them_a_discovery_aid"] += aid
        why["not_assessed_by_v2"] += r["category"] is None
        why["effect_supported"] += (r["components"]["effect"]["points"] or 0) > 0
        why["a_citation_dated_at_the_time"] += (r["components"]["contemporaneous"]["points"] or 0) > 0
        why["no_citation_with_a_readable_date"] += not any(iso_date(c.get("date")) for c in cites)
    differences = {k: why[k] for k in (
        "labelled_confirmed", "labelled_confirmed_citing_two_or_more_hosts", "labelled_confirmed_by_the_curator",
        "two_or_more_hosts", "two_or_more_hosts_and_two_or_more_origins", "two_or_more_hosts_but_one_origin",
        "two_or_more_hosts_but_no_origin", "two_or_more_hosts_one_of_them_a_discovery_aid", "cite_a_discovery_aid",
        "not_assessed_by_v2", "effect_supported", "a_citation_dated_at_the_time", "no_citation_with_a_readable_date")}

    current = run_index(kwargs)
    candidate = run_index(kwargs, {**declared, **SHADOW_WEIGHTS}, labels)
    # The substitution left nothing behind.
    assert {k: v for k, v in build_index.SCORING["confidence_weights"].items() if not k.startswith("_")} == declared

    end = dt.date.fromisoformat(current["dates"][-1])
    replay = []
    for back in REPLAY_DAYS_BACK:
        i = _nearest(current["dates"], end - dt.timedelta(days=back))
        replay.append({"days_back": back, "date": current["dates"][i], "current": _at(current, i)["esdi"],
                       "shadow": _at(candidate, i)["esdi"],
                       "shadow_over_current": _ratio(_at(candidate, i)["esdi"], _at(current, i)["esdi"]),
                       "sectors": {s: {"current": current["sectors"][s][i], "shadow": candidate["sectors"][s][i]}
                                   for s in SECTORS}})
    now_c, now_s = _at(current, -1), _at(candidate, -1)

    served = None
    snap = ROOT / "data" / "processed" / "snapshot.json"
    if snap.is_file():
        with open(snap, encoding="utf-8") as fh:
            doc = json.load(fh)
        served = doc.get("esdi") if doc.get("as_of") == as_of else None

    return {
        "as_of": as_of,
        "method_version": evidence_confidence.METHOD["version"],
        "status": "shadow only: the theatre's scoring multiplier is unchanged",
        "incidents": len(incidents),
        "citations": {"total": citations, "on_an_official_domain": official, "with_a_readable_date": dated},
        "cross_tabulation": {"rows": "v1 label (scored today)", "columns": "v2 category (shadow)",
                             "counts": {k: v for k, v in cross.items() if sum(v.values())}},
        "candidate_mapping": CANDIDATE_WEIGHTS,
        "off_scale_weights": {"weights": OFF_SCALE_WEIGHTS,
                              "why": "Disputed and not-assessed incidents have no category to map. Each is given "
                                     "the lowest mapped weight, so neither outweighs an incident nobody disputes."},
        "v1_weights": declared,
        "weight_change_under_mapping": change,
        "why_they_differ": differences,
        "esdi": {"current": now_c["esdi"], "shadow": now_s["esdi"],
                 "shadow_over_current": _ratio(now_s["esdi"], now_c["esdi"]),
                 "reproduces_served_headline": None if served is None else served == now_c["esdi"],
                 "sectors": {s: {"current": now_c["sectors"][s], "shadow": now_s["sectors"][s]} for s in SECTORS}},
        "replay": {"kind": "earlier evaluation dates of today's corpus and code, from one build's series; "
                           "not a reconstruction of what was known then",
                   "dates": replay},
        "best_source_tier": dict(components),
        "limitations": [
            "Theatre citations carry no source role: each is treated as independent media reporting unless its "
            "address is on a recognisably official domain (a label that is exactly gov, gouv or mil, or "
            "kremlin.ru / government.ru). Official statements quoted by the press are counted as press.",
            "No theatre citation records whether it was opened, and theatre incidents carry no review block, so "
            "the 10-point 'opened during research or review' component is zero for every incident. That is "
            "'not recorded', not 'not opened'.",
            "The Wikipedia strike table reports that a strike happened, not what it did. Its incidents carry no "
            "supported effect, so the 15-point effect component is zero for them.",
            "Nobody has reviewed which theatre citations relay which, so every origin count here is a count of "
            "distinct publishers and no incident can be High: Moderate is the ceiling by rule, whatever the "
            "citations. '0 higher' in the table above therefore follows from construction, not from the evidence.",
            "Origins are counted by named wire, registered domain, publisher name and the organisation table. "
            "Republication the record does not name is invisible, which can only overstate independence in v1 "
            "and v2 alike.",
            "The candidate weights are ranks given numbers. v2 is declared not to be a probability, and nothing "
            "here shows that a Moderate incident deserves three quarters of a High one.",
        ],
    }


WHY_TEXT = {
    "labelled_confirmed": "Labelled `confirmed` by v1",
    "labelled_confirmed_citing_two_or_more_hosts": "… and cite two or more distinct hosts",
    "labelled_confirmed_by_the_curator": "… where the label was typed by the curator (curated incidents), not derived from citations",
    "two_or_more_hosts": "Cite two or more distinct hosts (what v1 counts for a strike-table incident)",
    "two_or_more_hosts_and_two_or_more_origins": "… and two or more distinct publishers as v2 counts them",
    "two_or_more_hosts_but_one_origin": "… but only one publisher as v2 counts them",
    "two_or_more_hosts_but_no_origin": "… but no countable publisher under v2",
    "two_or_more_hosts_one_of_them_a_discovery_aid": "… where one of the hosts is a discovery aid (Wikipedia)",
    "cite_a_discovery_aid": "Cite a discovery aid at all",
    "not_assessed_by_v2": "Cite nothing but a discovery aid, so v2 does not assess them",
    "effect_supported": "Have an effect the v2 model counts as supported",
    "a_citation_dated_at_the_time": "Have a citation dated within 30 days of the event",
    "no_citation_with_a_readable_date": "Have no citation with a readable date",
}


def _fmt(x):
    return "n/a" if x is None else f"{x:.2f}" if isinstance(x, float) else str(x)


def markdown(s):
    cross = s["cross_tabulation"]["counts"]
    ch = s["weight_change_under_mapping"]
    lines = [
        BEGIN,
        f"*Generated by `scripts/confidence_shadow_study.py --write` for the build dated {s['as_of']} "
        f"(method {s['method_version']}). A dated study, not a live figure: re-run the script to refresh it.*",
        "",
        f"**Scope.** {s['incidents']} scored theatre incidents carrying {s['citations']['total']} citations, of which "
        f"{s['citations']['on_an_official_domain']} sit on a recognisably official domain and "
        f"{s['citations']['with_a_readable_date']} carry a readable date.",
        "",
        "**Cross-tabulation** (rows: the v1 label the index uses today; columns: the v2 shadow category).",
        "",
        "| v1 \\ v2 | " + " | ".join(V2_LABELS) + " |",
        "|---|" + "---|" * len(V2_LABELS),
    ]
    lines += [f"| {v1} | " + " | ".join(str(row[c]) for c in V2_LABELS) + " |" for v1, row in cross.items()]
    lines += [
        "",
        "**Candidate mapping evaluated:** " + ", ".join(f"{k} → {v}" for k, v in s["candidate_mapping"].items())
        + ". (v1: " + ", ".join(f"{k} {v}" for k, v in s["v1_weights"].items()) + ".)",
        "",
        "**Off the scale:** " + ", ".join(f"{k} → {v}" for k, v in s["off_scale_weights"]["weights"].items())
        + ". " + s["off_scale_weights"]["why"],
        "",
        f"**Incidents whose weight would change:** {ch['lower']} lower, {ch['higher']} higher, {ch['same']} unchanged"
        + f" ({ch['off_scale']} of them off the scale).",
        "",
        "**Why they differ** (incidents; each line is a property of the citations).",
        "",
        "| | Incidents |",
        "|---|---|",
    ]
    lines += [f"| {WHY_TEXT[k]} | {v} |" for k, v in s["why_they_differ"].items()]
    lines += [
        "",
        "**Index under each weighting** (the real builder, weights substituted in memory).",
        "",
        "| Evaluation date | Headline, v1 (served) | Headline, shadow | Shadow ÷ v1 | "
        + " | ".join(f"{x}, v1 / shadow" for x in SECTORS) + " |",
        "|---|---|---|---|" + "---|" * len(SECTORS),
    ]

    def row(label, cur, sh, ratio, sectors):
        return (f"| {label} | {_fmt(cur)} | {_fmt(sh)} | {_fmt(ratio)} | "
                + " | ".join(f"{_fmt(sectors[x]['current'])} / {_fmt(sectors[x]['shadow'])}" for x in SECTORS) + " |")
    lines.append(row(f"{s['as_of']} (this build)", s["esdi"]["current"], s["esdi"]["shadow"],
                     s["esdi"]["shadow_over_current"], s["esdi"]["sectors"]))
    lines += [row(f"{r['date']} ({r['days_back']} days back)", r["current"], r["shadow"], r["shadow_over_current"], r["sectors"])
              for r in s["replay"]["dates"]]
    lines += [
        "",
        f"The replay rows are {s['replay']['kind']}.",
        "",
        "The v1 column " + {True: "reproduces the served headline exactly, so the study ran the model the build runs.",
                            False: "DOES NOT reproduce the served headline: the study's inputs have drifted from the build's and its numbers should not be used.",
                            None: "could not be checked against a served build of the same date."}[s["esdi"]["reproduces_served_headline"]],
        "",
        "**Limits of this study.**",
        "",
    ]
    lines += [f"- {x}" for x in s["limitations"]]
    lines += ["", "**`theatre_shadow` block** (for the lead to place in a payload; this script adds it to none).", "",
              "```json", json.dumps({"theatre_shadow": served_block(s)}, ensure_ascii=False, indent=2), "```", END]
    return "\n".join(lines)


def served_block(s):
    """The small summary a methodology panel could show. No incident, no facility, no ranking."""
    return {
        "as_of": s["as_of"], "method_version": s["method_version"], "status": s["status"],
        "incidents": s["incidents"],
        "cross_tabulation": s["cross_tabulation"],
        "candidate_mapping": s["candidate_mapping"],
        "off_scale_weights": s["off_scale_weights"],
        "weight_change_under_mapping": s["weight_change_under_mapping"],
        "why_they_differ": s["why_they_differ"],
        "esdi": {"current": s["esdi"]["current"], "shadow": s["esdi"]["shadow"],
                 "shadow_over_current": s["esdi"]["shadow_over_current"], "sectors": s["esdi"]["sectors"]},
        "replay": [{"date": r["date"], "current": r["current"], "shadow": r["shadow"],
                    "shadow_over_current": r["shadow_over_current"]} for r in s["replay"]["dates"]],
        "replay_kind": s["replay"]["kind"],
        "limitations": s["limitations"],
        "note": ("A comparison only. The index is computed with the v1 weights; the shadow column shows what it "
                 "would be under a candidate mapping that has not been adopted."),
    }


def write_section(text, doc=DOC):
    body = doc.read_text(encoding="utf-8")
    if BEGIN not in body or END not in body:
        raise SystemExit(f"{doc} has no {BEGIN} ... {END} markers to write between")
    head, rest = body.split(BEGIN, 1)
    tail = rest.split(END, 1)[1]
    with open(doc, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(head + text + tail)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--as-of", default=dt.date.today().isoformat())
    ap.add_argument("--write", action="store_true", help=f"refresh the study section of {DOC.name}")
    ap.add_argument("--json", action="store_true", help="print the full result as JSON")
    args = ap.parse_args(argv)
    # The asset build writes one geometry file wherever the build is pointed. Point it at a
    # temporary directory outside the repository: a fixture build may never touch data/processed.
    scratch = tempfile.mkdtemp(prefix="edm-shadow-")
    try:
        outputs.set_target(outputs.plan("fixture", args.as_of, dt.date.today().isoformat(), scratch))
        result = study(args.as_of)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    text = markdown(result)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else text)
    if args.write:
        write_section(text)
        print(f"wrote the shadow-study section of {DOC}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
