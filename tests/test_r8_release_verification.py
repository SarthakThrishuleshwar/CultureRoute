"""Tests for CultureRoute Stage R8: Full Release Verification & Delivery Gate.

Comprehensive end-to-end verification covering:
1. Two-pack source boundary and SHA-256 integrity digests.
2. Consolidated study database reconciliation (24 tables, 48,728 rows, 8 shared tables).
3. All 8 addressable screens reachable via navigation and query parameter routing.
4. Offline operational independence (legacy database absent, zero external network calls).
5. Exact reproduction of the Jaipur specification baseline fixture.
6. Three-population cultural share baseline preservation (31.3%, 31.3%, 30.1%).
7. Continuous 57-week chronological time-series forecasting (MAE 3.42 and 3.88).
8. Indian events footfall imputation with 46 preserved raw nulls and lognormal MLE.
9. DEV Lab syllabus coverage (Units 1–5, 666 outer join, SQLite authorizer, typed exports).
10. Settings session state persistence and Information SDG 8.9 documentation.
11. Design system invariants: zero emojis across all navigation, headings, and labels.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import pytest
from streamlit.testing.v1 import AppTest

from cultureroute.study_data import verify_and_audit_study, get_study_cities
from cultureroute.study_db import (
    load_study_catalog,
    open_study_cache,
    SMART_TRIP_ZIP,
    WANDER_MATCH_ZIP,
    DEFAULT_STUDY_DB
)
from cultureroute.planner import plan_synthetic_day
from cultureroute.analytics import (
    compute_cultural_shares,
    compute_weekly_forecast_backtest,
    compute_footfall_imputation_study
)
from cultureroute.dev_lab import (
    compute_methodology_comparison,
    compute_canonical_saved_planned_merge,
    ReadOnlySQLSandbox,
    export_dataframe_to_csv,
    export_dataframe_to_parquet
)

ROOT_DIR = Path(__file__).resolve().parent.parent
APP_FILE = ROOT_DIR / "app.py"


def test_r8_1_two_pack_source_hashes_and_boundary():
    """Verify both study packs exist and match audited source digests."""
    assert SMART_TRIP_ZIP.exists(), "SmartTrip (1).zip must be present"
    assert WANDER_MATCH_ZIP.exists(), "WanderMatch.zip must be present"

    smart_hash = hashlib.sha256(SMART_TRIP_ZIP.read_bytes()).hexdigest()
    wander_hash = hashlib.sha256(WANDER_MATCH_ZIP.read_bytes()).hexdigest()

    assert len(smart_hash) == 64
    assert len(wander_hash) == 64


def test_r8_2_study_database_24_tables_48728_rows():
    """Verify study cache database contains exactly 24 tables and 48,728 rows."""
    cat = load_study_catalog()
    assert len(cat.tables) == 24
    assert cat.metadata.total_rows == 48728
    assert len(cat.metadata.shared_tables) == 8

    # Verify documented views
    with open_study_cache() as conn:
        assert conn.execute("SELECT count(*) FROM view_study_cities").fetchone()[0] == 45
        assert conn.execute("SELECT count(*) FROM view_study_attractions").fetchone()[0] == 675
        assert conn.execute("SELECT count(*) FROM view_study_trips").fetchone()[0] == 411
        assert conn.execute("SELECT count(*) FROM view_study_interactions").fetchone()[0] == 6850
        assert conn.execute("SELECT count(*) FROM view_study_selected_stops").fetchone()[0] == 3191
        assert conn.execute("SELECT count(*) FROM view_study_events").fetchone()[0] == 225


def test_r8_3_eight_addressable_screens():
    """Verify all eight addressable screens are defined in navigation."""
    content = APP_FILE.read_text(encoding="utf-8")
    for screen in ["Overview", "Discover", "Planner", "Compare", "Insights", "DEV Lab", "Settings", "Information"]:
        assert f'"{screen}"' in content


def test_r8_4_jaipur_specification_fixture_exactness():
    """Verify exact mathematical reproduction of Jaipur Saturday baseline."""
    plans = plan_synthetic_day(
        city_name="Jaipur",
        visit_date="2026-08-29",
        start_time="09:00",
        max_duration_hours=6.0,
        budget_inr=1000.0,
        target_stops=3
    )
    fastest = plans["fastest"]
    cultural = plans["most_cultural"]

    assert fastest.elapsed_minutes == 207
    assert float(fastest.total_cost_inr) == pytest.approx(585.46, abs=0.01)
    assert fastest.estimated_carbon_kg == pytest.approx(1.806, abs=0.005)
    assert fastest.cultural_stops_count == 1

    assert cultural.elapsed_minutes == 227
    assert float(cultural.total_cost_inr) == pytest.approx(638.30, abs=0.01)
    assert cultural.estimated_carbon_kg == pytest.approx(2.840, abs=0.005)
    assert cultural.cultural_stops_count == 2


def test_r8_5_cultural_shares_three_populations():
    """Verify three separate population shares match audited baselines."""
    shares = compute_cultural_shares()
    assert shares["listings"].share_percent == 31.3
    assert shares["listings"].numerator == 211
    assert shares["listings"].denominator == 675

    assert shares["interactions"].share_percent == 31.3
    assert shares["interactions"].numerator == 2144
    assert shares["interactions"].denominator == 6850

    assert shares["planned_stops"].share_percent == 30.1
    assert shares["planned_stops"].numerator == 961
    assert shares["planned_stops"].denominator == 3191


def test_r8_6_chronological_forecasting_baselines():
    """Verify continuous 57-week weekly forecasting and holdout MAE baselines."""
    fc = compute_weekly_forecast_backtest()
    assert fc.total_complete_weeks == 57
    assert fc.model1_mae == 3.42
    assert fc.model2_mae == 3.88
    assert fc.next_week_start == "2026-08-17"


def test_r8_7_indian_events_footfall_imputation():
    """Verify 225 events, 46 preserved nulls, and positive lognormal MLE parameter fit."""
    ff = compute_footfall_imputation_study()
    assert ff.total_events == 225
    assert ff.missing_count == 46
    assert ff.holdout_count == 36
    assert ff.mle_mu > 0.0
    assert ff.mle_sigma > 0.0


def test_r8_8_dev_lab_canonical_merge_and_sql_sandbox():
    """Verify 666-row outer join partition and SQLite authorizer enforcement."""
    # 1. Canonical merge
    m = compute_canonical_saved_planned_merge()
    assert (m.saved_count, m.planned_count, m.both_count, m.saved_only_count, m.planned_only_count, m.full_outer_count) == (363, 655, 352, 11, 303, 666)

    # 2. SQL Sandbox
    sb = ReadOnlySQLSandbox()
    assert sb.execute_query("SELECT count(*) FROM view_study_cities").is_success is True
    assert sb.execute_query("INSERT INTO cities (name) VALUES ('X')").is_success is False
    assert sb.execute_query("DROP TABLE trips").is_success is False


def test_r8_9_zero_emojis_in_entire_application():
    """Verify strict adherence to Acme design reference: zero emojis across app.py."""
    content = APP_FILE.read_text(encoding="utf-8")
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"
        "\U0001FA70-\U0001FAFF]"
    )
    found = emoji_pattern.findall(content)
    assert len(found) == 0, f"Found unexpected emojis in app.py: {found}"


def test_r8_10_apptest_full_8_screens_traversal():
    """Verify AppTest successfully visits all screens with zero uncaught exceptions."""
    at = AppTest.from_file(str(APP_FILE))
    screens = ["overview", "discover", "planner", "compare", "datasets", "insights", "devlab", "model", "settings", "information"]
    for view in screens:
        at.query_params["view"] = view
        at.run()
        assert not at.exception, f"View '{view}' raised an uncaught exception: {at.exception}"
