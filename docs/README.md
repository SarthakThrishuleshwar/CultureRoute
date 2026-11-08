# CultureRoute documentation

This folder contains the **actual proposed documentation set** for CultureRoute, plus prompts for future revisions. The documents are grounded in the eight-page `CultureRoute_DEV_AAT_Project_Specification.pdf` and the SQLite/data-model files inside `SmartTrip (1).zip` and `WanderMatch.zip`. The template video and supplied photos guide visual design only. Hackathon dates, submission rules, XR instructions, and unrelated product ambitions in the ZIP READMEs are not CultureRoute requirements.

## Read in this order

| Document | What it covers | Current status |
| --- | --- | --- |
| [PRD](PRD.md) | Research problem, product scope, six screens, requirements and acceptance criteria. | Proposed product specification. |
| [TRD](TRD.md) | Component contracts, planner and analytics logic, SQL limits, verification. | Proposed technical design. |
| [Database](DATABASE.md) | 24-table inventory, ERD, India filters, prepared views, metrics, reconciliation SQL. | Source counts verified; views proposed. |
| [Full data dictionary](DATA_DICTIONARY.md) | Every supplied SQLite column, type, required flag, PK/FK. | Generated from actual source schemas. |
| [System architecture](ARCHITECTURE.md) | Context/container, request sequences, pipeline diagram, component responsibilities, decisions. | Target architecture. |
| [Pipeline](PIPELINE.md) | Stage-by-stage input/output gates, lineage, forecast, footfall, refresh procedure. | Target pipeline; source audit executable. |
| [Workflows](WORKFLOWS.md) | Traveler, evaluator, forecast, and footfall journeys with error branches. | Proposed workflows. |
| [UI/UX](UI_UX.md) | Template adaptation, design system, six-screen behavior, responsive and accessibility rules. | Design specification. |
| [Traceability](TRACEABILITY.md) | Requirement-to-screen/component/data/evidence matrix and sign-off gaps. | Current audit. |
| [Phasewise prompts](phasewise_prompts.md) | Reusable prompts to regenerate or expand documents phase by phase. | Supplementary authoring aid. |
| [Visual reference map](uiux_design_reference.md) | Short template-to-CultureRoute mapping and tokens. | Companion to UI/UX specification. |

The [static landing-page prototype](../site/dist/index.html) illustrates the visual language. It does **not** implement the planner, DEV Lab, database pipeline, or six connected application screens.

## Verified source baseline

Run `python docs/audit_sources.py` from the workspace root. It reads both ZIP databases without changing them and verifies: 18 SmartTrip tables/32,627 rows; 14 WanderMatch tables/27,428 rows; eight identical shared tables/11,327 duplicate rows; 24 distinct tables/48,728 rows; 45 Indian cities, 675 attractions, 411 non-cancelled trips, 6,850 matched POI actions, 3,191 selected stops; cultural shares 211/675, 2,144/6,850, and 961/3,191; the 352/11/303 saved/planned join; 225 Indian events with 46 missing footfall values; and 57 complete weeks with MAE 3.42/3.88. The Jaipur route figures come from the specification and remain an implementation fixture.

## How to use the set

Use the PRD to agree on product scope, the TRD/database/architecture/pipeline documents to build it, and the workflows/UI/UX documents to implement and review the six screens. The traceability page lists verified evidence and what remains unimplemented. If source data or scope changes, rerun the audit and update the metric definitions, fixtures, diagrams, and UI copy together.
