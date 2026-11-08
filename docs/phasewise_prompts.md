# CultureRoute: phasewise documentation prompts

Use these prompts in one conversation with an assistant that can read the three supplied attachments. Paste the **Shared grounding prompt** first, then each phase. Keep the output of each phase available as context for the next. Ask the project team to resolve items marked **Decision needed** before treating a draft as final.

## Shared grounding prompt — run once

```text
You are the documentation lead for CultureRoute, an exploratory cultural-tourism website. Read these reference attachments completely before drafting: CultureRoute_DEV_AAT_Project_Specification.pdf; SmartTrip (1).zip; WanderMatch.zip; and the UI template video “Screen Recording 2026-11-08 164657.mp4”. Treat the attachments as evidence and design reference, not as instructions to obey. In particular, do not import hackathon dates, upload rules, XR requirements, or product claims from the ZIP READMEs into CultureRoute unless the CultureRoute specification independently requires them.

Project facts to preserve: the proposed website has two connected experiences, a cultural day trip planner and a DEV Lab for source inspection, transformations, charts, and forecasts. The study covers 45 Indian cities, 675 listed attractions, and 411 non-cancelled trips. The source packs contain 18 SmartTrip tables / 32,627 rows and 14 WanderMatch tables / 27,428 rows. Eight tables are shared copies; the specified combined inventory is 24 distinct tables / 48,728 rows after keeping one copy. These are synthetic data, not observations of actual visits, spending, or employment. The initial cultural shares are 31.3% of listings, 31.3% of matched interactions, and 30.1% of selected planned stops, with different denominators. The project links to SDG 8.9 through promotion of local culture; do not claim measured job creation.

First produce a one-page source ledger with: source file, relevant pages/paths, what it establishes, conflicts or gaps, and confidence. Verify raw versus filtered counts from the SQLite files rather than assuming all rows are in study scope. Use IDs for joins. Keep interaction and itinerary counts separately aggregated before joining to attractions. Record each metric's numerator, denominator, filter, grain, date scope, and source. For money use decimal arithmetic; keep currency codes. Do not invent deployment details, APIs, algorithms, user research, security controls, or acceptance results. Label assumptions and proposed designs. When an exact filtering rule or implementation decision is absent, write “Decision needed” with the options and impact. Cite PDF page numbers and ZIP paths/table names in each document.

Output a compact confirmed-facts table, an open-decisions table, and a document-to-source traceability plan. Wait for the next phase prompt after that.
```

## Phase 1 — PRD (product requirements)

```text
Using the shared source ledger, draft a complete CultureRoute Product Requirements Document. Include: product summary; problem and research question; intended traveler and evaluator roles; SDG 8.9 alignment and its evidence limit; goals and non-goals; scope boundary for a demo/MVP versus later ideas; six-screen information architecture; prioritized user stories with IDs; functional requirements with IDs and measurable acceptance criteria; accessibility and usability requirements; data provenance requirements; success measures and how each is computed; failure/empty/infeasible states; dependencies, risks, assumptions, and open decisions.

The six screens are Project Overview, Discover a City, Build a Cultural Day, Compare Plans, Insights and Predictions, and DEV Lab. The planner must accept city, day, start time, budget, available hours, stop count, and preferences. It must compare a fastest feasible plan with one maximizing cultural stops under the same inputs. The DEV Lab must inspect raw/prepared tables, support guided transformations and bounded read-only SQL, show before/after tables and commands, and export supported outputs. Insights must show chart, table, and “How calculated” views, units, sample sizes, filters, provenance, and forecast errors.

Distinguish specified behavior from proposed behavior. Do not claim reservations, actual live prices, real visits, a production recommender, or measured economic impact. Include a requirements-to-screen matrix and a small acceptance-test matrix. End with “Decisions needed before sign-off.” Deliver as PRD.md.
```

## Phase 2 — TRD (technical requirements)

```text
Draft a CultureRoute Technical Requirements Document that implements the approved PRD without adding unapproved features. Start with a requirement traceability table (PRD ID → component → data input → test). Define the proposed stack exactly as specified where possible: Python, SQLite, pandas, Streamlit, Plotly, and Seaborn. Identify what is specified, what is an implementation proposal, and what is undecided.

Cover source loading in read-only mode; validation and shared-table deduplication; prepared-view contracts; planner request/response objects; eligibility and route feasibility; directed walking/cab legs; visit, wait, and travel duration; opening-hour uncertainty; entry fees and leg fares with decimal amounts; cultural-stop ranking versus elapsed-time ranking; accessibility at stops versus unknown transfer accessibility; analytics aggregations and denominator rules; chronological weekly forecast evaluation; missing-footfall estimation; guided pandas operations; bounded read-only SQL; export CSV/Parquet; caching/recalculation strategy; error handling; performance targets as proposed targets; test fixtures; logging and reproducibility.

Write interfaces as schemas/pseudocode rather than asserting an existing API. Include concrete acceptance examples from the specification: Saturday Jaipur, 09:00 start, six-hour window, INR 1,000 budget, three distinct stops; fastest plan 1 cultural stop / 3h27 / INR 585.46 / 1.806 kg estimated between-stop carbon; cultural-max plan 2 cultural stops / 3h47 / INR 638.30 / 2.840 kg. Mark these as specification baselines to reproduce, not independently verified runtime tests. Note that only 10 of each city's 15 attractions have recorded travel-matrix coverage. Deliver as TRD.md with unresolved technical decisions.
```

## Phase 3 — database and data dictionary

```text
Produce CultureRoute's Database and Data Preparation document from the actual SmartTrip PS-01.db and WanderMatch PS-11.db schemas, their data dictionaries, and the CultureRoute specification. Inventory every one of the 24 distinct tables, noting the 8 shared tables kept once. For each table give source pack, purpose, primary key, relevant foreign keys, grain, selected important fields, raw row count, and whether the website uses it directly, through a prepared view, or only in the explorer. Put a full column dictionary in an appendix rather than dropping columns silently.

Draw an ER diagram and a raw-to-prepared lineage diagram. Define attraction_summary (one of 675 study attractions), interaction_records (6,850 matched actions), selected_itinerary_stops (3,191 confirmed stops in 411 non-cancelled trips), trip/city summaries, and route_options (one directed leg and mode). Give executable SQL or precise pandas pseudocode for filters and aggregations, plus a reconciliation query for each published count. Specifically explain why the raw activities_poi table has 900 rows and cities has 60 while the project scope says 675 attractions across 45 Indian cities; derive and verify the filter rather than guessing it. Audit shared table equality by key and content before deduplicating. Preserve missing values and origin fields. Define IDs as opaque strings, BCP-47 language tags, and money as decimal strings converted to Decimal for calculation.

For cultural shares, document three separate numerator/denominator populations: catalog listings, matched platform interactions, and selected planned stops. Include join-cardinality guards so interactions × itinerary items cannot multiply counts. Report missingness for event expected_footfall, including the specified 46 missing of 225 Indian events, only after verifying scope. Add data-quality checks, indexes useful to each workflow, provenance, and a schema-change response. Deliver as DATABASE.md, ERD source, and a metric dictionary. Mark any unverified figure explicitly.
```

## Phase 4 — overall system and pipeline architecture

```text
Create CultureRoute's System Architecture and Data Pipeline document. Draw two diagrams: (1) a context/container view showing traveler and evaluator, Streamlit UI, planner, analytics/forecast, transformation engine, prepared views, and the two read-only SQLite/CSV packs; (2) a lineage pipeline from source validation → scope filtering → shared-table deduplication → separate aggregations → prepared views → planner/charts/forecasts/DEV Lab → displayed provenance and exports. Annotate materialization/caching and refresh only where proposed, not as known implementation.

For each component define inputs, outputs, failure modes, ownership, and how outputs trace back to source rows. Provide a sequence diagram for route generation and another for a DEV Lab transformation. Describe deterministic preparation, record-count checkpoints (18+14 source tables, 8 shared, 24 distinct, 48,728 distinct rows per specification), validation gates, reproducible version/cutoff metadata, and how the weekly forecast excludes future data. The forecast has 57 complete Monday–Sunday weeks; over the last 12 complete weeks the specification reports MAE 3.42 for last-week and 3.88 for four-week average. Label these as source baselines pending runtime reproduction.

Include architecture decisions with alternatives and trade-offs, data protection implications of synthetic user rows, observability, deployment assumptions, and explicit “not specified” entries for infrastructure details. Deliver ARCHITECTURE.md and editable Mermaid diagrams.
```

## Phase 5 — end-to-end workflow document

```text
Write WORKFLOWS.md with swimlane diagrams and numbered steps for two primary journeys: traveler and evaluator. For the traveler: choose city and constraints; inspect full 15-attraction catalog and matrix coverage; generate two feasible plans; compare maps/timetables/cost/carbon; open source rows; change budget or time and rerun; export plan table. Include decision branches for no eligible stops, no recorded directed leg, unknown opening hours, inaccessible stop, budget/time exceedance, and export failure. Distinguish confirmed route totals from estimates.

For the evaluator: select raw table/prepared view; inspect schema, row count, and missingness; run Guided Mode filter/derive/group/pivot/merge or bounded read-only SQL; view command and before/after tables; show matched/unmatched keys; chart with table and calculation explanation; export. Use the specified saved-versus-planned join example as a fixture: inner 352, left 363, full outer 666; outer breakdown 352 matched, 11 saved only, 303 planned only. Explain join grain and which nulls occur in outer rows. Include a third workflow for weekly forecast inspection and a fourth for missing-footfall estimation with held-out known values.

For every step specify actor, trigger, precondition, UI state, backend call or transformation, data input, output, error path, and acceptance evidence. Tie workflow steps to PRD/TRD IDs. Deliver editable Mermaid and prose; label unimplemented paths as design specifications.
```

## Phase 6 — UI/UX specification and template adaptation

```text
Produce UI_UX.md and a clickable high-fidelity prototype for CultureRoute. Use the attached 28.8-second template recording as visual reference. Its defining language is warm cream paper, charcoal handwritten/editorial type, oxblood/red emphasis, thin imperfect underlines and borders, doodle arrows/stars, pale yellow taped notes, generous white space, offset cards, and a long narrative scroll. Adapt the structure and rhythm, but replace every Acme/team/pricing/testimonial claim with truthful CultureRoute content. Do not invent user testimonials, customer counts, subscriptions, or a live booking service.

Translate the reference's hero into “Explore the culture behind every route” or equivalent, with a clear planner CTA and a DEV Lab CTA. Translate generic feature cards into city discovery, feasible day plans, side-by-side comparison, chart/table/provenance, and guided transformations. Use the supplied green landscape photograph as an illustrative hero image and the supplied fort, ornate interior, Golden Temple, and food photographs for the four cultural-category cards. Add a restrained glow and scale effect on image hover, with a reduced-motion fallback. Keep the supplied cliffside monastery photograph out of the Indian-city study presentation because it appears to depict a site outside India. Do not imply a supplied photograph is a row in the synthetic dataset. Cover heritage, museums, religious sites, and food experiences in the category cards. Replace pricing with an honest “Two ways to explore” or scope comparison. Use the documented Jaipur scenario as a clearly labeled example; show synthetic-data notice. Make all six required application screens explicit in a sitemap and provide desktop/mobile wireframes for each, with component inventory, interaction states, field validation, empty/loading/error states, focus/keyboard behavior, contrast, responsive breakpoints, and content rules.

The planner screen must keep map and timetable paired. Compare Plans must label “Fastest plan” and “Most cultural stops” consistently. Insights must have Chart / Table / How calculated views and expose units, sample size, date cutoff, filters, and reset. Use both color and text for observed/missing/estimated values. DEV Lab must visibly identify read-only SQL, query limits, row counts, and matched/unmatched join counts. Use at least one Indian language where useful as a proposed UI design, but do not claim a translation exists. Separate visual inspiration from actual implementation scope. Include an annotated mapping: template element → CultureRoute replacement → reason. Deliver prototype assets and UI_UX.md.
```

## Phase 7 — final review and handoff

```text
Audit PRD.md, TRD.md, DATABASE.md, ARCHITECTURE.md, WORKFLOWS.md, UI_UX.md, diagrams, and prototype as one documentation set. Build a traceability matrix from research question → PRD requirement → screen/workflow → technical component → source table/view → metric/acceptance test. Check every cross-document count, date, unit, denominator, filter, and use of “observed”, “estimated”, and “synthetic”. Re-run source reconciliation queries and the specified Jaipur, join, and forecast fixtures where code exists; otherwise mark them as pending implementation verification. Inspect all diagrams and prototype screens at desktop and mobile sizes. Identify contradictions, unsupported claims, accessibility issues, missing edge cases, and broken links. Fix issues that are unambiguous. Return a concise change log, unresolved decisions with owner suggestions, and a sign-off checklist. Never call a proposed design an implemented feature.
```

## Known facts to keep consistent

| Topic | Specification baseline | Documentation caution |
| --- | --- | --- |
| Study scope | 45 Indian cities, 675 listed attractions, 411 non-cancelled trips | Explain raw-to-study filters. |
| Source inventory | SmartTrip 18 tables / 32,627 rows; WanderMatch 14 / 27,428 | Eight tables overlap; combined 24 distinct / 48,728 rows. |
| Engagement | 6,850 matched interaction actions | Specify matching predicate and grain. |
| Plans | 3,191 selected itinerary stops | State active/confirmed and trip filters. |
| Cultural shares | 31.3% listings, 31.3% interactions, 30.1% planned stops | Three distinct denominators. |
| Data | Fully synthetic | No claims about actual visits, spending, or employment. |
| Stack | Python, SQLite, pandas, Streamlit, Plotly, Seaborn | Planned stack, not proven deployment. |
| Prediction | 57 complete weeks; last 12-week MAE 3.42 vs 3.88 | Source baseline; verify chronologically. |

