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
    "competing": [], "source_refs": ["s3"]
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
- `effect_specificity`: `quantified` (a source gives a figure for the effect), `described` (a
  concrete effect without a figure) or `vague` ("disruption reported").
- `civilian_service_impact[].affected.unit` is the **source's own unit**. People are not customers
  are not households are not subscribers. Nothing is converted.
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
- `first_published`: the build date on which the record was first served. Stamped by the import
  script. Event date, source date and first-published date are three different dates.

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
  `supply_shortfall`, `civil_disruption`, `unknown`. The country systems' causes map onto these
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
| `ASSESSED` | A competent government body, the victim or operator, or a technical investigator assesses an actor. |
| `ATTRIBUTED` | A formal government or law-enforcement attribution, or several independent credible attributions that agree. |
| `DISPUTED` | Credible sources materially disagree. Competing attributions are listed; the product does not choose. |

- `actor_type`: `state`, `state_linked`, `hacktivist`, `criminal`, `insider`, `unknown`, `other`.
  "State-linked" is not "state-controlled"; the type is the source's, not ours.
- `basis` lists who attributes: `government`, `law_enforcement`, `victim_operator`,
  `cybersecurity_firm`, `researcher`, `media_investigation`, `actor_self_claim`.
- `as_of` is the date of the attribution, which may be much later than the event. Later knowledge is
  never shown as contemporaneous.
- Copy rule: "*X* attributed the incident to *Y*", never "*Y* attacked". The product reports who
  attributes; it asserts nothing itself. No actor leaderboard, no capability profile.

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
- `CONFIRMED` needs a direct authoritative source (the operator, a government investigation or the
  vendor's own incident report). `ASSESSED` needs an official or technical investigator.
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

| Component | Points | Rule |
|---|---|---|
| Directness | 40 / 28 / 15 / 10 / 4 | The best supporting source: direct authoritative (operator, government, regulator, CERT, law enforcement, court record, or an official account on social media whose identity is established) 40; independent reporting (wire, media, specialist media, a cyber firm's own investigation) 28; secondary (aggregator, dataset restating others, a journalist's social post) 15; a researcher's social post 10; an anonymous account or an actor's self-claim 4. |
| Independent origins | 0 / 16 / 25 | Distinct **originating statements** among direct and independent-reporting sources: one 0, two 16, three or more 25. A wire story and its republications are one origin; three releases from one utility are one origin; ten reposts are one origin at best. |
| Effect specificity | 15 / 8 / 0 | Quantified / described / vague, counted only when a direct or independent source supports `effect`. |
| Opened by a reviewer | 10 | At least one direct or independent supporting source was opened and read by a reviewer. |
| Contemporaneous | 10 | At least one direct or independent supporting source is dated within 30 days of the event. |

Categories: **High** ≥ 78, **Moderate** 55–77, **Limited** 35–54, **Preliminary** < 35.
Overrides: a record whose occurrence or effect is credibly contested is **Disputed**, whatever its
score. A record supported only by unverified social posts or only by an actor's self-claim is at
most **Preliminary**.

Properties, each tested and mutation-tested:

- adding a source never lowers the score; removing one never raises it;
- a duplicate citation or a second citation from the same origin changes nothing;
- source **count** never enters, only roles and origins;
- an official source alone is not penalised for lack of corroboration it could not have
  (directness and corroboration are separate components), and many copies of one state or wire
  statement are one origin.

Thresholds were calibrated against blind reviewer labels (`docs/EVIDENCE_CONFIDENCE_V2.md`).

### 8.2 Attribution confidence

From the sources that support `attribution`, by their role and origin:

- `HIGH`: a formal government or law-enforcement attribution **and** a second independent
  attribution origin of a different basis (a technical report, the victim, a second government).
- `MODERATE`: one formal government, law-enforcement or victim/operator attribution; or two
  independent technical or investigative origins that agree.
- `LOW`: a single cyber firm, researcher or media investigation.
- `CLAIM_ONLY`: only the actor's own claim. A self-claim can never produce more than this.
- `DISPUTED`: status `DISPUTED`. `NOT_ESTABLISHED`: status `UNKNOWN`.

Status and confidence must agree: `ATTRIBUTED` needs at least `MODERATE` with an official basis;
`CLAIMED` needs an `actor_self_claim` source; the build refuses the mismatch.

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

## 11. Served artifacts

Registered in `pipeline/artifacts.py` (`GLOBAL_PAYLOADS`); lazy-loaded; the home page loads none of
them.

- `global/impacts.json`: scope statement, caveats, vocabularies with labels and plain-language
  definitions, the research summary (window, source families, regions worked, known limitations,
  latest research date), and `records[]` in date order, newest first. Each served record adds
  `country_name`, `system_id` (when the country is a monitored system, else `null`),
  `evidence_confidence` (category, score, components, reasons), `attribution.confidence`,
  `origin_count`, and each source's `link_check`. Nothing is ordered by a figure.
- `global/regional_context.json`: the Gulf and Hormuz timeline of §10.
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
their corrections, mints abstracted ids, stamps `first_published`, and reconciles against the
country queues: a candidate matching a record held from a country system is refused.

## 13. What the build refuses

The builder fails, naming the record, when: a coordinate-like key or value appears; a kinetic or
sabotage record is not country-abstracted; a campaign-restricted system's record carries a region,
facility, operator or headline; route wording appears outside the regional context, or forbidden
maritime wording appears inside it; an IP address, CVE identifier or exploit wording appears; status
wording (restart, repair, back online, remaining capacity) appears on an abstracted record; a claim
has no supporting source; attribution status and sources disagree; an AI status has no
incident-specific source or no relation; a social source has no tier or identity basis, or an S3/S4
post is the sole evidence; an attempt is filed as a disruption; a unit is missing where a value is
given; an absence is written as zero.
