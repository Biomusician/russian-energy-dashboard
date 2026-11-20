# Global impact layer: methodology and contract (iteration 22)

The dashboard's country systems answer "what reviewed energy disruption records have we found?".
The **global impact layer** adds a second, separate, **non-scored** corpus that answers different
questions: which civilian services were actually affected, whether a disruption was cyber, kinetic
or something else, who is publicly attributed and how firmly, whether AI was materially involved,
and how strong the evidence is for each of those claims.

This file is the contract. The pipeline (`pipeline/global_impacts.py`,
`pipeline/evidence_confidence.py`), the import gate (`scripts/import_impacts.py`), the frontend and
the tests all follow it. Vocabularies live in `methodology/impact_taxonomy.json`; confidence
parameters live in `methodology/evidence_confidence.json`. Nothing here is hardcoded in a component.

## 1. What the layer is, and is not

- **It is** a reviewed, expanding corpus of publicly reported disruptions to energy and essential
  civilian services, at country or first-level-region precision, 2022-01-01 to the present.
- **It is not** a census. Disclosure laws differ, operators may not disclose, conflicts distort
  reporting and media ecosystems differ. **Counts are published records in this corpus, never
  rates, and are never compared or ranked across countries.**
- **It is not scored.** No record here enters the ESDI, a country system's canonical event count, a
  country's research gate or any index. A test enforces that no analytic module imports it.
- **It does not create monitored systems.** A country that appears only here is an
  *impact-record country*: no index, no research-maturity claim, no onboarding dossier, no implied
  complete corpus. The thirteen systems stay thirteen.
- **It never widens publication.** The most conservative applicable rule wins: a record held from a
  country system cannot appear here, and a campaign-covered attack is as abstract here as there.

## 2. Scope boundary (never relaxed)

Never collected, stored or published, in any field, title, address, export or CSV:

- incident coordinates; anything finer than first-level region;
- current operating, repair or restart status, or remaining capacity, of an attacked facility;
- target, criticality, vulnerability or weak-point ranking of anything; defensive gaps;
- route dependence, bypass or alternate-route capacity, chokepoint exploitation;
- vessel names, positions, tracks, AIS, tanker lists, port vulnerability;
- IP addresses, exposed-device inventories, network topology, credentials, exploit chains,
  CVE-to-target linkage, protocols or interfaces of a named victim, current security controls;
  device makes or models, tooling or malware family names (outside a quoted attribution statement);
- weapon identification or selection, strike distances;
- personal data of any kind; faces; identification of people from media.

A cyber record may name a **broad mechanism** (ransomware, DDoS, destructive malware, OT
disruption) when publicly reported. It never says how access was gained.

## 3. Inclusion contract

A record is included when public sources establish **a real interruption or degradation of an
energy system or essential civilian service that is non-trivial in scale or duration**. At least
one of:

1. an official emergency declaration or formal incident declaration tied to the disruption;
2. a service interruption affecting a large population, customer base or region (the source's own
   figure, in the source's own unit);
3. material power, load, generation or fuel-output loss stated by an operator, regulator or
   government;
4. loss or severe degradation of a national or regional service (payments at fuel stations
   nationwide, a national telecom operator down, hospital diversion across a region);
5. sustained operational disruption (days, or repeated over weeks) of an essential service;
6. material interruption of industrial or energy output.

Not included: a vulnerability advisory with no disruption; a generic risk article; a forecast,
exercise or warning; a data breach with no operational effect; a claim with no credible report that
a service was affected.

There is no universal numeric threshold. Sector differs from sector, and inventing "100,000" where
the evidence is a hospital network diverting ambulances would be a false precision. The reviewer
records which basis applied (`inclusion_basis`).

**Attempts** are a separate record kind: `record_kind: "attempt_no_service_impact"`, labelled
"ATTEMPT — NO REPORTED SERVICE DISRUPTION", never counted with disruptions and shown only in a
separate section. Only clearly documented attempts on essential services qualify (an official or
operator statement).

### 3.1 Degraded operational capability with supply continuing (B12)

**PROPOSED, applied in iteration 22 closure.** Pending the owner's confirmation; until then it is
the reading reviewers and the lead apply.

<!-- B12: applied to N records -->

The question: a cyber incident degrades an operator's operational or remote-control capability
(dispatch, remote switching, monitoring of the network) while end-user supply continues, because
staff switch to manual operation or redundancy holds. Is that a disruption or an attempt?

- **DISRUPTION** (`record_kind: "disruption"`): a control or operational function that is actually
  used to deliver the energy or civilian service was degraded or unavailable **for a meaningful
  duration** (below), even if redundancy or manual operation prevented a customer outage. This is
  "a real interruption or degradation of an energy system" in the sense of the inclusion contract
  above; the record does not need a customer figure.
- **ATTEMPT** (`record_kind: "attempt_no_service_impact"`): malicious activity with no
  demonstrably degraded service, and no operational function degraded for a meaningful duration.
  (The candidate wording, "no demonstrably degraded service or operational function", left a gap:
  a degradation too brief to be meaningful was neither. It falls here.) The attempt bar above is
  unchanged: an official or operator statement.

**Meaningful duration.** The methodology has no numeric threshold for this and the sources do not
support one: operators rarely state minutes, and a figure invented here would be false precision.
It is judged on the two duration tests the inclusion contract already has:

1. **sustained** (inclusion basis 5): the function was degraded for days, or repeatedly over weeks,
   as a source states; or
2. **formally recognised** (inclusion basis 1): a competent authority declared it, or classed it as a
   reportable incident with a stated effect on operations. This is the precedent already applied to
   grid disturbances in which generation tripped but no customer lost supply: rejected unless the
   regulator classed them as reportable events with a stated system effect.

A degradation shorter than that and not formally recognised is an attempt (if the attempt bar is
met) or not included.

**What does not count as an operational function:** corporate IT, e-mail, websites, billing or
customer-account portals, and data theft, unless a source states that operations stopped because
of them. An operator that halts operations as a precaution has actually interrupted service or
output: that is a disruption on inclusion basis 5 or 6, not this rule.

**Evidence.** The degradation must be stated by a first-party or official source (the operator, a
regulator, a government body, a national CERT) or by a formal report of one. An actor's claim to
have taken over or disrupted control systems is a claim (§6) and never establishes the
degradation, however widely it is repeated.

**What the record says, and does not.** `effect` says, in past tense and the source's words, that an
operational function was degraded and that end-user supply continued, as the source states; the
duration as the source gives it; `effect_specificity: "described"` unless a source gives a figure
for the effect. The effect leads with the degradation: the build refuses a disruption whose every
effect sentence says nothing was affected, because that is an attempt. `civilian_service_impact`
carries no affected figure (an entry, if any, has `affected: null`): no customers were affected,
and the operator's customer base is not a figure for this record (§4). `inclusion_basis` is 5 or 1,
whichever test was met. The record never names the
control system, its make or vendor, an interface, a protocol or how access was gained (§2); never
describes the redundancy, backup or manual capability that held, or evaluates it; and never says
whether the function is restored now (§2: no current status of anything attacked).

## 4. Record contract (curated: `data/curated/global_impacts/events.json`)

```json
{
  "impact_id": "imp-2023-12-12-ukr-telecom-kyivstar-cyberattack",
  "record_kind": "disruption",
  "date": "2023-12-12", "date_precision": "day", "date_end": "2023-12-20",
  "country_a3": "UKR",
  "admin1": null,
  "geographic_precision": "country",
  "domain": "civilian_service",
  "sector": "telecom",
  "technology": null,
  "cause_family": "cyber",
  "contributing_factors": [],
  "cyber_mechanism": "destructive_malware",
  "summary": "One or two plain sentences: what happened, to what service, where (country or region).",
  "effect": "What the sources say the effect was, in neutral words.",
  "effect_specificity": "quantified",
  "inclusion_basis": 4,
  "civilian_service_impact": [
    {"service": "telecom", "geographic_scope": "national",
     "affected": {"value": 24000000, "unit": "subscribers", "qualifier": "about",
                  "source_says": "about 24 million mobile subscribers"},
     "duration_text": "service restored in stages over about a week", "source_refs": ["s1", "s2"]}
  ],
  "attribution": {
    "status": "ATTRIBUTED", "actor": "Sandworm", "actor_type": "state_linked",
    "basis": ["government", "victim_operator"], "as_of": "2024-01-04",
    "statement": "Ukraine's security service attributed the attack to the Sandworm group.",
    "competing": [], "self_claims": [], "source_refs": ["s3"]
  },
  "ai_involvement": {"status": "NONE_REPORTED", "relation": null, "role": null, "as_of": null,
                     "statement": null, "source_refs": []},
  "dispute": null,
  "sources": [
    {"ref": "s1", "url": "https://…", "publisher": "Kyivstar", "date": "2023-12-12",
     "language": "uk", "source_role": "operator", "medium": "web", "social": null,
     "supports": ["occurrence", "effect"], "opened": true,
     "title_original": "…", "title_en": "…", "derived_claim": "Operator confirms a cyberattack caused a network outage."}
  ],
  "episode_id": null, "episode_basis": null,
  "publication_policy": "standard",
  "research_pass": "i22-eurasia",
  "first_published": "2026-11-20",
  "review": {"reviewed_at": "2026-11-19", "review_status": "blind_reviewed",
             "roles": {"evidence": "accept", "attribution_source": "accept", "safety": "accept"},
             "ai_check": "not_applicable", "social_check": "not_applicable", "disposition": "confirmed"}
}
```

Field rules:

- `impact_id`: `imp-<date>-<a3 lower>-<sector>-<short slug>`. For an abstracted attack record
  (`publication_policy: "country_abstracted"`): `imp-<date>-<a3>-<sector>-attack-<6 hex>`, the token
  a keyed hash minted by the import script, never a lane's own numbering and never a place name.
- `country_a3`: ISO alpha-3 present in `global/world.geojson`. `"MULTI"` is allowed only with
  `geographic_precision: "multi_country"` and a `countries_a3` list.
- `admin1`: `null`, or `{"code", "name"}` at first-level region. **Never** for a kinetic or sabotage
  record, **never** for any record in a system under the campaign policy, never finer.
- `domain`: `energy` or `civilian_service`. `sector` and `technology` come from the taxonomy (§5).
  `technology` is `null` (not applicable) outside energy.
- `cause_family`: one primary cause; `contributing_factors` only where a source says so.
- `cyber_mechanism`: `null` (not applicable) unless `cause_family` or a contributing factor is cyber.
  One exception: a disruption that was **digitally triggered without malice** (a faulty software
  update, an IT system failure that stopped operations) is `cause_family: "industrial_technical"`
  with `cyber_mechanism: "it_outage_affecting_operations"`, the only mechanism allowed there. It is
  not a cyberattack, its attribution is `NOT_APPLICABLE`, and the "Cyber" filters do not include it;
  it has its own "IT failure" filter.
- A municipal or public body that announced its own non-kinetic incident (a city government's
  ransomware incident) may be named as the affected organisation outside campaign-restricted
  systems; the record's geography still stops at the first-level region.
- A regional-context `metric` may also carry `qualifier` (about, at least, at most, range) and
  `value_upper` for a range.
- `effect_specificity`: `quantified` (a source gives a figure for the effect), `described` (a
  concrete effect without a figure) or `vague` ("disruption reported").
- `civilian_service_impact[].affected.unit` is the **source's own unit**. People are not customers
  are not households are not subscribers. Nothing is converted.
- `civilian_service_impact[].affected` is the **scale affected**: how many people, customers,
  subscribers or facilities lost or had degraded service. It is never a restoration percentage, a
  duration, a recovery time, or the operator's total customer base, unless the source says the whole
  base was affected. "Power restored to 80% of customers" is not an affected figure; nor is "the
  utility serves 1.2 million customers". Duration and restoration wording go in `duration_text`.
- `date_end` is an **observed** endpoint only: a source reports that the disruption ended on that
  date. An announced, expected or scheduled end ("cuts will continue until Friday", "restoration
  expected within a week") goes in `duration_text` or `effect`, in the source's words, and
  `date_end` stays `null`. The build refuses a `date_end` later than the newest date among the
  record's sources, when the sources are dated: no source can have observed an end after it was
  published. (`date_end` also widens the window in which a source counts as a dated account, §8.1,
  which is one more reason a planned end must not stand in for an observed one.)
- Absences are distinct and explicit. A field that may be absent uses `null` for *not applicable*
  and one of these strings where the difference matters: `"unknown"`, `"not_researched"`,
  `"withheld"`, `"no_public_evidence"`, `"source_inaccessible"`. `null` is never zero.
- `publication_policy`: `standard` or `country_abstracted`. **Every kinetic or sabotage record,
  everywhere, is `country_abstracted`**: country level, no facility, operator, place or region, no
  headline (`title_original`/`title_en`), no citation whose address names the place, operator or
  method, no later status. This is the campaign policy of the Gulf systems applied to the whole
  layer, because the layer aggregates across conflicts and cannot rule each one.
- Operators and facilities: a **non-kinetic** record outside a campaign-restricted system may name
  the operator when the incident is already public under that name (a utility that announced its
  own ransomware incident). A safety reviewer decides; the default is to name the service and the
  country, not the plant.
- `first_published`: the build date on which the record was **first served**. `null` means not yet
  served: the record is pending its first release. The import never stamps its own run date (an
  import is not a release, and a record imported today may first be served days later). The release
  lead runs `scripts/stamp_first_published.py --date <release build date>` in the release commit; it
  fills only `null` values. **An existing date never changes**, on re-import, correction or rebuild.
  Event date, source date and first-published date are three different dates.

## 5. Vocabularies (`methodology/impact_taxonomy.json`)

- **Sectors, energy:** `electricity`, `oil_gas`, `fuel_supply`, `district_energy`.
- **Sectors, civilian service:** `water`, `wastewater`, `desalination`, `telecom`, `healthcare`,
  `transport`, `municipal_services`.
- **Technology (energy only):** `oil_upstream`, `gas_upstream`, `refinery`, `lng`, `gas_processing`,
  `fuel_storage_or_distribution`, `thermal_generation`, `hydro_generation`, `wind_generation`,
  `solar_generation`, `battery_or_grid_storage`, `transmission`, `distribution`, `grid_control`,
  `other_energy`. A separate field from the country systems' `asset_class`; a mapping table relates
  them and nothing is migrated.
- **Cause family:** `kinetic`, `cyber`, `sabotage`, `industrial_technical`, `natural_hazard`,
  `supply_shortfall`, `civil_disruption`, `authority_order`, `unknown`. `authority_order` is a
  service restricted or shut down by order of an authority (an exam-period or protest-period
  internet shutdown): not a malicious incident, attribution `NOT_APPLICABLE`, and the record says
  who ordered it only as a source states. The country systems' causes map onto these
  (`kinetic_strike` → `kinetic`, and so on); the country vocabulary is unchanged.
- **Cyber mechanism:** `ransomware`, `data_wiper`, `ddos`, `unauthorized_access`,
  `it_outage_affecting_operations`, `ot_ics_disruption`, `supply_chain_compromise`,
  `malicious_configuration_change`, `destructive_malware`, `service_provider_compromise`,
  `cyber_physical_disruption`, `unknown_cyber_mechanism`.
- **Source role:** `operator`, `government`, `regulator`, `cert` (national CERT or cyber agency),
  `law_enforcement`, `court_record`, `wire`, `media`, `specialist_media`, `cyber_firm`,
  `researcher`, `dataset`, `aggregator`, `actor_self_claim`.
- **Medium:** `web`, `report`, `dataset`, `social`.

## 6. Attribution

Attribution is separate from cause and separate from whether the event happened.

| Status | Meaning |
|---|---|
| `NOT_APPLICABLE` | Not a malicious act (natural hazard, technical failure, shortfall). |
| `UNKNOWN` | Malicious or possibly malicious; no credible public attribution. Not a low confidence: attribution is not established. |
| `CLAIMED` | An actor claimed responsibility. A claim is not corroboration. |
| `SUSPECTED` | A credible source names a likely actor without a firm attribution. |
| `ASSESSED` | A competent government body, the victim or operator, or a technical investigator assesses an actor; or several technical or press attributions agree. |
| `ATTRIBUTED` | A formal government or law-enforcement attribution. Agreement among technical or press attributions, however many, is `ASSESSED`. |
| `DISPUTED` | Credible sources materially disagree about the actor. Competing attributions are listed; the product does not choose. |

**What `ATTRIBUTED` requires, exactly** (`pipeline/evidence_confidence.py::attribution_problems`;
the build and the import refuse the record otherwise). At least one source that supports
`attribution` must carry a government or law-enforcement basis
(`methodology/evidence_confidence.json` → `attribution.official_bases`). A source's basis is:

- the actor's own claim, if it is one (typed `actor_self_claim`, declared
  `attribution_basis: "actor_self_claim"`, or published by the named actor). A claim, and any
  outlet that relays it without a finding of its own, never counts, whatever else it says;
- nothing, for a discovery aid or an unverified account (an anonymous post, an S4 post, an S1
  account whose identity is not established);
- for a first-party or press source: its declared `attribution_basis` if it has one (a wire story
  reporting a government's attribution declares `government`), else the basis of its role:
  `government`, `official`, `regulator` and `cert` give `government`; `law_enforcement` and
  `court_record` give `law_enforcement`; `operator` gives `victim_operator`; `cyber_firm` gives
  `cybersecurity_firm`; press roles give `media_investigation`;
- for a secondary source or a researcher's post: `researcher` or `media_investigation`. A declared
  basis is not honoured here: a post or a dataset cannot borrow a government's authority.

The record-level `attribution.basis` list is descriptive and checked only against the vocabulary;
the gate reads the sources. One official's interview is not a formal attribution, and a
campaign-level advisory that does not name the victim attributes nothing to it (reviewer rulings,
iteration 22). An `ATTRIBUTED` record with a non-empty `competing` list has attribution confidence
`DISPUTED`.

- `actor_type`: `state`, `state_linked`, `hacktivist`, `criminal`, `insider`, `unknown`, `other`.
  "State-linked" is not "state-controlled"; the type is the source's, not ours.
- `basis` lists who attributes: `government`, `law_enforcement`, `victim_operator`,
  `cybersecurity_firm`, `researcher`, `media_investigation`, `actor_self_claim`.
- `as_of` is the date of the attribution, which may be much later than the event. Later knowledge is
  never shown as contemporaneous.
- Copy rule: "*X* attributed the incident to *Y*", never "*Y* attacked". The product reports who
  attributes; it asserts nothing itself. No actor leaderboard, no capability profile.
- `competing` lists a **credible alternative attribution advanced by a source other than the
  actor**: a government, investigator, victim or press investigation naming a different actor.
  A non-empty list makes attribution confidence `DISPUTED`, whatever the status.
- `self_claims` is provenance for an **actor's own unverified claim** (that it did it, or that
  someone else did not). A self-claim goes there, never in `competing`, and never yields `DISPUTED`:
  a group claiming an incident another body attributes elsewhere is a claim beside an attribution,
  not credible sources disagreeing.
- `CLAIMED` is not `ATTRIBUTED`. However many outlets report a claim, it stays a claim (§8.2).
- A malware or ransomware family name is not an actor identity. "Attacked with ransomware family Z"
  says what tool was reported, not who used it; `actor` names a group or body only where a source
  attributes the incident to one. (Outside an attribution statement a tool or malware name is not
  published at all, §2.)

**Attribution confidence** is computed from the attribution sources (§8), never typed by hand:
`HIGH`, `MODERATE`, `LOW`, `CLAIM_ONLY`, `DISPUTED`, `NOT_ESTABLISHED` (for `UNKNOWN`), and absent for
`NOT_APPLICABLE`.

## 7. AI involvement

A source must tie AI to **this incident**. Modern, sophisticated, automated or scripted is not AI.

- `status`: `NONE_REPORTED`, `CLAIMED`, `SUSPECTED`, `ASSESSED`, `CONFIRMED`.
- `relation`: `ai_assisted` (an attacker used AI tooling) or `ai_operational_cause` (an AI system in
  operations made the erroneous decision, or an AI service the operation depended on failed). These
  are different and never merged: AI-generated phishing does not mean AI caused the outage.
- `role`: `attacker_assistance`, `social_engineering_generation`, `malware_or_script_generation`,
  `automated_attack_orchestration`, `ai_operational_system_failure`,
  `ai_generated_configuration_or_code`, `ai_service_dependency_failure`, `other`, `unknown`.
- "AI may have helped" is `SUSPECTED` or `CLAIMED` with its source, never upgraded. A defender's use
  of AI to detect the attack does not set the field.
- `CONFIRMED` needs a first-party or official source that supports `ai_involvement` (the operator, a
  government investigation or the vendor's own incident report). `ASSESSED` needs a first-party or
  official source, or press or third-party reporting (an official or technical investigator, or a
  report of one). These are checks on who is speaking, not on what the source says: whether it
  states, assesses or only suspects AI involvement is the reviewer's check
  (`docs/EVIDENCE_CONFIDENCE_V2.md` §7).
- Few records are expected. The feature shows the reviewed corpus as it is; an empty filter result
  is a correct answer.

## 8. Evidence Confidence v2

Three separate questions, three separate answers. None is a probability, none is severity, none is
infrastructure importance, and none measures how completely a country was researched.

1. **Evidence confidence** (occurrence and effect): did it happen, and is the reported effect
   supported?
2. **Attribution confidence**: how strong is the evidence about who did it?
3. **AI-involvement status**: how firmly does a source tie AI to this incident?

### 8.1 Evidence confidence

Computed by `pipeline/evidence_confidence.py` from the sources that support `occurrence` or
`effect`. Output: a category, an ordinal score 0–100 (**not a probability**) and the components
that produced it, so every card can answer "why?".

The labels below are the served ones (`methodology/evidence_confidence.json`, `tiers.*.label`);
`docs/EVIDENCE_CONFIDENCE_V2.md` §2 is the full statement of each rule.

| Component | Points | Rule |
|---|---|---|
| Who is speaking | 40 / 28 / 15 / 10 / 4 | The best supporting source: a **first-party or official statement** (operator, government, regulator, national CERT or cyber agency, law enforcement, court record, or an official social account whose identity is established) 40; **press or third-party reporting** (wire, news outlet, specialist press, trade body, a cyber firm's own investigation) 28; a **secondary source** (a dataset restating others, a recognised journalist's post, a researcher's web publication) 15; a **researcher's social post** 10; an **unverified claim** (an anonymous account, an actor's own claim) 4. "First-party" says who is speaking, not that the statement was verified; "press or third-party" says who carried it, not that the reporting was its own work. |
| Originating statements | 0 / 16 / 25 | Groups of first-party and press sources that share an origin, a publisher, an organisation, a filed form or a declared relay: one 0, two 16, three or more 25. A wire story and its republications are one; three releases from one utility are one; ten reposts are one at best. The count is called "independent originating statements" only when the attribution-and-source reviewer checked which sources relay which (`basis: "reviewed"`); otherwise it is "distinct publishers cited" and the record is at most Moderate. |
| Effect specificity | 15 / 8 / 0 | Quantified / described / vague, counted only when a first-party or press source supports `effect`. |
| Opened during research or review | 10 | A first-party or press supporting source carries `opened: true`, or the record's review block says a reviewer opened its sources. `opened: null` is "not recorded", never "not opened". |
| Dated account | 10 | A first-party or press supporting source dated from the day before the event to 30 days after its end, or a later formal account (a dated first-party source in a formal role, or one marked `formal_account: true`). |

Categories: **High** ≥ 78, **Moderate** 55–77, **Limited** 35–54, **Preliminary** < 35. The points are
ordinal, never a percentage.
Overrides: a record whose occurrence or effect is credibly contested is **Disputed**, whatever its
score, and shows no total. A record supported only by unverified social posts, a researcher's post
or an actor's own claim is at most **Preliminary**. A record whose originating statements were not
reviewed is at most **Moderate**. A record cited only through a discovery aid (an encyclopedia, an
aggregator) is **Not assessed** (`category: null`), never Preliminary.

Properties, each tested and mutation-tested:
- adding a source never lowers the score, and removing one never raises it, except where the source shows that two cited sources are one account (a shared publisher, organisation or declared relay);
- a duplicate citation or a second citation from the same origin changes nothing;
- source **count** never enters, only roles and origins;
- an official source alone is not penalised for lack of corroboration it could not have
  (directness and corroboration are separate components), and many copies of one state or wire
  statement are one origin.

Thresholds are provisional: one blind calibration has been run and they did not pass it, and the method is served with `status: "provisional: thresholds not calibrated"` until a run passes (`docs/EVIDENCE_CONFIDENCE_V2.md` §6).

### 8.2 Attribution confidence

From the sources that support `attribution`, by their role and origin:

- `HIGH`: a formal government or law-enforcement attribution **and** a second attribution from a
  separate origin with a different basis (a technical report, the victim, or law enforcement beside
  a government). Two bodies of the same basis are one basis; organisations that are parent and
  child in the organisation table are one origin; outlets relaying one attribution add at most one.
- `MODERATE`: one government, law-enforcement or victim/operator attribution; or two technical or
  investigative findings of their own, from separate origins, that agree.
- `LOW`: a single cyber firm, researcher or media investigation.
- `CLAIM_ONLY`: only the actor's own claim. A self-claim can never produce more than this.
- `DISPUTED`: status `DISPUTED`. `NOT_ESTABLISHED`: status `UNKNOWN`.

Status and sources must agree, and the build refuses the mismatch: `ATTRIBUTED` needs an official
basis as defined in §6 (so its confidence is at least `MODERATE`, or `DISPUTED` when `competing` is
non-empty); `CLAIMED` needs the actor's own claim as a source and no other party's finding. The
confidence never says more than the status: `SUSPECTED` is capped at `LOW` and `ASSESSED` at
`MODERATE`.

### 8.3 Scope of use

Evidence confidence is shown on impact records and on the country systems' published events. It is
**not** the theatre's scoring confidence. The theatre's multiplier (confirmed/probable/possible by
cited-host count) is unchanged; a shadow comparison is published in the review and the methodology
panel, and replacing the multiplier is a separate decision with its own bar
(`docs/EVIDENCE_CONFIDENCE_V2.md`).

## 9. Sources, origins and social media

- **Claim-level provenance.** Each source lists what it supports: `occurrence`, `effect`,
  `attribution`, `ai_involvement`. A cyber firm can support attribution without supporting the
  service impact. The build refuses a claim with no supporting source.
- **Origins.** An origin is an originating statement: the wire a citation names, else the website
  it sits on, else (for social) the account. A lane may set `origin` explicitly to group
  republications it can see. Wikipedia and aggregators are discovery aids and are never an origin.
- **Social media is a medium, not a quality level.** Public posts only; no private groups, no
  logins, no circumvention.

| Tier | Account | May support |
|---|---|---|
| S1 | Official account of a government, regulator, grid operator, utility or company, identity established from the organisation's own site or long-standing institutional references | occurrence and effect, like any primary announcement |
| S2 | Recognised journalist or institution | discovery and contemporaneous observation; material claims are corroborated |
| S3 | Reputable OSINT or researcher account | discovery and corroborative lead; never sole evidence |
| S4 | Unknown or anonymous account | discovery only; never cited as sole evidence |

- A platform badge is not identity. `social.identity_basis` says how identity was established.
- A cited post stores platform, display name, handle, account tier, URL, timestamp, language and a
  short derived claim. Posts are not reproduced. Media is not stored.
- Link states: `reachable`, `redirected`, `blocked`, `dead`, `error`, `deleted`, `archived_copy`,
  `unchecked`. A platform refusing the checker is `blocked` or `unchecked`, not dead. A deleted post
  does not erase a corroborated claim; provenance says what happened.
- No geolocation from imagery, no weapon or damage inference beyond what reliable reporting says.

## 10. Regional context: the Gulf and the Strait of Hormuz

Owner direction for iteration 22 (brief §6) narrows the earlier rule that the product carried
"nothing about straits or shipping". The rule is now:

- **One artifact only**, `global/regional_context.json`, may carry aggregate, dated, sourced
  statements about the Gulf and the Strait of Hormuz: that shipping is restricted or disrupted, in
  aggregate; aggregate trade, supply and market effects; strategic-reserve and policy responses;
  broad civilian and environmental consequences. Every other payload keeps the old ban, and the
  country systems' records still carry no route wording.
- **Never, anywhere:** a vessel name, number, position or track; AIS; a list of ships; a route or
  an alternate route; bypass capacity; which facility or port depends on the strait; port
  vulnerability; which asset would have the greatest effect. The builder refuses the wording.
- **No single status flag.** Not "open" or "closed": dated statements with their source and their
  "as of" date. An entry older than its stated shelf life is shown as historical, never as current.
- Context is context. It never enters an index, a count or a country's record; a market movement is
  never presented as infrastructure loss; causality is stated only where the source states it.

Entry contract (`data/curated/global_impacts/regional_context.json` → `entries[]`):

```json
{"id": "ctx-2026-03-05-iea-supply-statement", "date": "2026-03-05", "as_of": "2026-03-05",
 "context_type": "aggregate_supply",
 "claim": "One or two neutral sentences attributed to the source.",
 "metric": {"value": 0, "unit": "mb/d", "basis": "what the figure measures, in the source's words"},
 "sources": [{"ref": "s1", "url": "…", "publisher": "IEA", "date": "2026-03-05", "language": "en",
              "source_role": "government", "medium": "report", "supports": ["occurrence"], "opened": true}],
 "review": {"reviewed_at": "2026-11-19", "roles": {"evidence": "accept", "safety": "accept"}}}
```

`context_type`: `shipping_status`, `aggregate_trade`, `aggregate_supply`, `market_response`,
`reserve_action`, `policy_response`, `civilian_environmental`. `metric` is `null` when the statement
has no figure.

Figures in context entries:

- **A numeric comparison needs a defined comparator.** "Down 40%" is published only with what it is
  down from, as the source defines it (a stated period, a stated baseline, a named series); a change
  with no comparator is stated in words, without the number.
- **A number whose series cannot be identified is not published.** If the source does not say what
  the figure measures (which flow, which aggregate, over what period) well enough to fill
  `metric.basis`, the entry keeps its claim in words and `metric` is `null`.
- **"Latest" is a set, not a pick.** Within one `context_type`, every entry carrying the newest
  `as_of` date is latest; ties are all latest and none is chosen over another. The served file lists
  them per type in `latest_by_type`. An entry older than its shelf life is historical, whatever this
  says.

## 11. Served artifacts

Registered in `pipeline/artifacts.py` (`GLOBAL_PAYLOADS`); lazy-loaded; the home page loads none of
them.

- `global/impacts.json`: scope statement, caveats, vocabularies with labels and plain-language
  definitions, the research summary (window, source families, regions worked, known limitations,
  latest research date), and `records[]` in date order, newest first. Each served record adds
  `country_name`, `system_id` (when the country is a monitored system, else `null`),
  `evidence_confidence` (category, score, components, reasons), `attribution.confidence`,
  `origin_count`, and each source's `link_check`. Nothing is ordered by a figure.
- `global/regional_context.json`: the Gulf and Hormuz timeline of §10, with `latest_by_type` (every
  entry tied at the newest `as_of` of its type).
- `global/evidence_confidence.json`: the method of §8 as data (components, thresholds, the
  definitions and the sentence that confidence is evidence quality, not severity, not probability,
  not importance), read by the confidence drawer and the glossary.
- Country systems' `events.json`: each published event gains `evidence_confidence`.

## 12. Review

No record imports itself. A candidate is written by a research lane into the local queue
(`data/candidates/impacts22/<lane>/`, never committed, never served). It is published only after
three independent reviews that do not see the researcher's rationale or each other:

- **Evidence**: opens the sources; checks identity, date, country, the effect and every figure;
  checks the inclusion basis; sets effect specificity.
- **Attribution and source**: checks each source's role, medium, origin and what it really
  supports; checks attribution status against the sources; applies the AI check ("does the source
  tie AI materially to this incident?") and the social check (identity established? direct evidence
  or discovery? independently corroborated? a repeat of another origin?).
- **Safety and abstraction**: checks §2 and §4 (precision, abstraction, exploit detail, status
  wording, loaded wording, personal data, addresses and titles that leak).

`scripts/import_impacts.py` moves a record into the curated file only when all three accept, applies
their corrections, mints abstracted ids, leaves `first_published` `null` for a new record (the
release lead stamps it, §4) and keeps an existing one unchanged, and reconciles against the country
queues: a candidate matching a record held from a country system is refused.

**The source and dispute validators gate the import and the build.**
`pipeline/evidence_confidence.py::source_problems` (medium, role and social tier in the vocabulary;
no shortened link; an address on a social platform is a post; `supports` and `disputes` are lists of
claims; a readable date) and `dispute_problems` (`dispute.about` present and in the vocabulary) run
on every candidate before it is written to the curated file and on every record when the build
runs; a finding refuses the record, naming it. They are deterministic checks of the record's own
fields. They do not open a source, judge whether a role was typed correctly, or detect an unmarked
relay: those stay the reviewers' work (`docs/EVIDENCE_CONFIDENCE_V2.md` §7).

## 13. What the build refuses

The builder fails, naming the record, when: a coordinate-like key or value appears; a kinetic or
sabotage record is not country-abstracted; a campaign-restricted system's record carries a region,
facility, operator or headline; route wording appears outside the regional context, or forbidden
maritime wording appears inside it; an IP address, CVE identifier or exploit wording appears; status
wording (restart, repair, back online, remaining capacity) appears on an abstracted record; a claim
has no supporting source; attribution status and sources disagree; an AI status has no
incident-specific source or no relation; a social source has no tier or identity basis, or an S3/S4
post is the sole evidence; an attempt is filed as a disruption; a unit is missing where a value is
given; an absence is written as zero; a `date_end` is later than the newest dated source; a source
or a dispute fails the validators of §12.
