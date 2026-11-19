# Iteration 22 review: from event database to impact evidence

<!-- status: in-progress -->

Iteration 21 made the existing data easier to use. Iteration 22 adds new kinds of evidence: a
second, non-scored corpus of reviewed cyber and civilian-service impact records from any country,
attribution and AI involvement as first-class and separately-evidenced claims, a new evidence
confidence measure that counts originating statements instead of links, and an aggregate, dated
context timeline for the Gulf and the Strait of Hormuz. No country system was added and no score
changed. Live figures are in [CURRENT_STATE.md](CURRENT_STATE.md).

**The short version.**

<!-- LEAD: fill at release -->

---

## 0. Baseline

| | |
|---|---|
| Start | local `main` fast-forwarded to `origin/main` `1b61ec7` (daily refresh of 19 November; ESDI 5.97, 184 events); iteration 21 released (`91c3136` and its review note) |
| Work branch | `iteration-22`, foundation commit `5417e92` |
| Systems | 13, unchanged: the Russia theatre (index) and 12 country systems (no score) |
| Country corpus at start | 175 published records in 12 country systems; 65 research lanes |
| Tests at start | pytest 1,235 passed, 2 skipped; vitest 454; TypeScript clean; Playwright 400 passed, 1 skipped; mutation campaign 376 of 376 caught (0 survived, 0 invalid, 0 errors) |
| Served data at start | 10.6 MB under `web/public/data`; built JavaScript 1.75 MB |
| Link health at start | last full check 12 November: 299 cited addresses |
| Iran at start | research preview, campaign-restricted, no published record; no regional context anywhere in the product |

## 1. Product objective

The dashboard answered "what reviewed energy disruption records have we found?". It now also
begins to answer: which civilian services were affected; whether a disruption was cyber, kinetic,
technical or natural; who is publicly attributed and how firmly; whether AI was materially
involved; whether wind, solar, hydro or storage was affected; what credible reporting says about
the wider Gulf; and how strong the evidence is for each claim. It still does not answer, and is
built not to answer: which facility matters most, where a weak point is, which route is
vulnerable, what is still offline at a struck site, or where any vessel is.

## 2. Global impact architecture

The contract is [GLOBAL_IMPACT_METHODOLOGY.md](GLOBAL_IMPACT_METHODOLOGY.md).

<!-- LEAD: sections 2-35 at integration -->
