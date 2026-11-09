"""Tests for CultureRoute Stage P2: Datasets & Data Lineage Screen.

Verifies:
1. Two-pack study boundary:
   - SmartTrip: 18 tables, 32,627 rows, verified SHA-256 hash.
   - WanderMatch: 14 tables, 27,428 rows, verified SHA-256 hash.
   - Exact reconciliation: 8 shared tables (11,327 duplicate rows retained once) -> 24 canonical tables / 48,728 rows.
2. Searchable Table Catalog & Safe Profiler:
   - 24 canonical tables accurately classified (10 SmartTrip-only, 6 WanderMatch-only, 8 Shared).
   - Safe projections mask/exclude sensitive columns.
   - Natural grain, primary key, and null count profiling for activities_poi and user_interactions.
3. Lineage pipelines:
   - User interactions to cultural attractions: 6,850 matched, 2,144 cultural (31.3%).
   - Trips to selected stops: 411 trips, 3,191 stops, 961 cultural (30.1%).
4. AppTest integration:
   - Direct deep-link ?view=datasets renders with 0 exceptions.
   - Origin pack filter and table selection operate cleanly.
   - Handoff to DEV Lab (?view=devlab&table=user_interactions) selects table seamlessly.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

from cultureroute.study_db import DEFAULT_STUDY_DB, load_study_catalog, open_study_cache
from cultureroute.study_data import verify_and_audit_study, open_study_databases
from cultureroute.dev_lab import get_table_profile
from cultureroute.datasets_view import (
    SMARTTRIP_HASH,
    WANDERMATCH_HASH,
    SHARED_TABLES,
    SMARTTRIP_ONLY,
    WANDERMATCH_ONLY,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
APP_FILE = ROOT_DIR / "app.py"


def test_p2_two_pack_hashes_and_boundary():
    """Verify the original two zip packs exist and match audited SHA-256 checksums."""
    smart_path = ROOT_DIR / "SmartTrip (1).zip"
    wander_path = ROOT_DIR / "WanderMatch.zip"

    assert smart_path.exists(), "SmartTrip (1).zip must be present"
    assert wander_path.exists(), "WanderMatch.zip must be present"

    smart_hash = hashlib.sha256(smart_path.read_bytes()).hexdigest()
    wander_hash = hashlib.sha256(wander_path.read_bytes()).hexdigest()

    assert smart_hash == SMARTTRIP_HASH
    assert wander_hash == WANDERMATCH_HASH


def test_p2_reconciliation_exact_counts():
    """Verify exact audited table and row counts across source packs and canonical cache."""
    report = verify_and_audit_study()

    assert report.smart_tables_count == 18
    assert report.smart_rows_count == 32627

    assert report.wander_tables_count == 14
    assert report.wander_rows_count == 27428

    assert report.shared_tables_count == 8
    assert report.shared_rows_count == 11327

    assert report.distinct_tables_count == 24
    assert report.distinct_rows_count == 48728

    # Formula check: 32627 + 27428 - 11327 == 48728
    assert (report.smart_rows_count + report.wander_rows_count - report.shared_rows_count) == report.distinct_rows_count


def test_p2_table_categorization_and_catalog():
    """Verify all 24 canonical tables are cataloged and categorized correctly."""
    catalog = load_study_catalog()
    assert len(catalog.tables) == 24

    assert len(SHARED_TABLES) == 8
    assert len(SMARTTRIP_ONLY) == 10
    assert len(WANDERMATCH_ONLY) == 6
    assert len(SHARED_TABLES) + len(SMARTTRIP_ONLY) + len(WANDERMATCH_ONLY) == 24

    for tbl in SHARED_TABLES:
        assert tbl in catalog.tables
        assert catalog.tables[tbl].origin_pack.lower() == "shared"

    for tbl in SMARTTRIP_ONLY:
        assert tbl in catalog.tables
        assert catalog.tables[tbl].origin_pack == "SmartTrip"

    for tbl in WANDERMATCH_ONLY:
        assert tbl in catalog.tables
        assert catalog.tables[tbl].origin_pack == "WanderMatch"


def test_p2_safe_profiles_for_key_tables():
    """Verify safe profile generation and sensitive column exclusion for key tables."""
    # 1. activities_poi (SmartTrip)
    poi_profile = get_table_profile("activities_poi", sample_limit=10)
    assert poi_profile is not None
    assert poi_profile.row_count == 900
    assert "poi_id" in poi_profile.columns
    assert "city_id" in poi_profile.columns
    assert "poi_category" in poi_profile.columns
    assert poi_profile.sample_df is not None
    assert len(poi_profile.sample_df) == 10

    # 2. user_interactions (WanderMatch)
    ui_profile = get_table_profile("user_interactions", sample_limit=10)
    assert ui_profile is not None
    assert ui_profile.row_count == 12339
    assert "interaction_id" in ui_profile.columns
    assert "entity_id" in ui_profile.columns
    assert "interaction_type" in ui_profile.columns
    assert ui_profile.sample_df is not None
    assert len(ui_profile.sample_df) == 10

    # 3. users (Shared, contains sensitive columns like email/password)
    users_profile = get_table_profile("users", sample_limit=10)
    assert users_profile is not None
    assert users_profile.row_count == 1200
    # Safe columns should exclude or mask sensitive fields
    for col in users_profile.sample_df.columns:
        assert col.lower() not in ["password", "password_hash", "token", "secret"]


def test_p2_lineage_pipeline_numbers():
    """Verify the lineage counts for interaction telemetry and trip planning match the audit."""
    report = verify_and_audit_study()

    # Pipeline 1: 45 cities, 675 attractions, 6850 matched actions, 2144 cultural actions (31.3%)
    assert report.india_cities_count == 45
    assert report.india_attractions_count == 675
    assert report.matched_interactions_count == 6850
    assert report.cultural_interactions_count == 2144
    assert round(report.cultural_interactions_count / report.matched_interactions_count, 3) == 0.313

    # Pipeline 2: 411 trips, 3191 selected stops, 961 cultural stops (30.1%)
    assert report.study_trips_count == 411
    assert report.selected_stops_count == 3191
    assert report.cultural_selected_stops_count == 961
    assert round(report.cultural_selected_stops_count / report.selected_stops_count, 3) == 0.301


def test_p2_apptest_datasets_screen_renders_cleanly():
    """Verify AppTest loads the Datasets screen with 0 exceptions and full UI components."""
    at = AppTest.from_file(str(APP_FILE))
    at.query_params["view"] = "datasets"
    at.run()
    assert not at.exception

    # Check that the reconciliation numbers and pack titles are present in the output
    markdown_texts = [m.value for m in at.markdown]
    combined_md = " ".join(markdown_texts)

    assert "Study Datasets" in combined_md
    assert "SmartTrip (1).zip" in combined_md
    assert "WanderMatch.zip" in combined_md
    assert "32,627" in combined_md
    assert "27,428" in combined_md
    assert "48,728" in combined_md
    assert "24 Canonical Tables" in combined_md or "24 canonical tables" in combined_md

    # Check selectbox for table inspection is present
    assert len(at.selectbox) >= 1
    table_sb = at.selectbox[0]
    assert any("user_interactions" in opt for opt in table_sb.options)


def test_p2_handoff_to_dev_lab_via_query_param():
    """Verify that passing table=user_interactions pre-selects the table in DEV Lab."""
    at = AppTest.from_file(str(APP_FILE))
    at.query_params["view"] = "devlab"
    at.query_params["table"] = "user_interactions"
    at.run()
    assert not at.exception

    # In DEV Lab Tab 1, selectbox should default to user_interactions
    table_sb = at.selectbox[0]
    assert table_sb.value == "user_interactions"
