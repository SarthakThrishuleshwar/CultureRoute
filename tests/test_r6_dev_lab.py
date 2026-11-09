"""Tests for CultureRoute Stage R6: DEV Lab Teaching Workbench.

Verifies:
1. Source Browser & Profiling across all 24 canonical study tables with safe projections.
2. Guided Transformations:
   - Filter and derive: price binning ([0,0] Free, (0,100] Budget, (100,500] Moderate, >500 Premium),
     cultural flag derivation, and reproducible pandas code snippet generation.
   - Split-apply-combine groupby aggregation.
   - Reversible long-to-wide pivot matrix (45 cities x 4 cultural categories).
   - Canonical 666-row outer join partition (363 saved, 655 planned, 352 both, 11 saved-only, 303 planned-only).
3. Bounded Read-Only SQL Sandbox under SQLite authorizer:
   - Permitted SELECT reads.
   - Denied writes: INSERT, UPDATE, DELETE.
   - Denied DDL and PRAGMA: DROP TABLE, PRAGMA.
   - Single-statement enforcement (no stacked queries with semicolon).
   - Character bound (> 1500 chars rejected).
   - Row truncation at 500 rows maximum.
   - Distinct rejection/denial error messages.
4. Typed Exports:
   - CSV formula injection protection.
   - Binary Parquet serialization and column round-trip.
5. Syllabus Reference completeness across Units 1–5.
6. Streamlit AppTest verification of DEV Lab load and tab navigation.
"""

from __future__ import annotations

import io
from pathlib import Path
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from cultureroute.dev_lab import (
    compute_methodology_comparison,
    compute_canonical_saved_planned_merge,
    ReadOnlySQLSandbox,
    get_table_profile,
    filter_and_derive_poi,
    groupby_aggregate_stops,
    pivot_city_category_matrix,
    export_dataframe_to_csv,
    export_dataframe_to_parquet,
    get_syllabus_reference_units,
)
from cultureroute.study_db import load_study_catalog, SENSITIVE_COLUMNS

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_dev_lab_all_24_tables_profiling_and_safe_projections():
    """Verify all 24 canonical tables are profilable and mask sensitive columns."""
    cat = load_study_catalog()
    assert len(cat.tables) == 24

    for tbl_name in cat.tables:
        profile = get_table_profile(tbl_name, sample_limit=10)
        assert profile is not None
        assert profile.table_name == tbl_name
        assert profile.row_count == cat.tables[tbl_name].row_count
        assert len(profile.columns) > 0

        # Verify sensitive columns are masked from safe projection
        for safe_col in profile.safe_columns:
            assert safe_col not in SENSITIVE_COLUMNS
        for col in profile.sample_df.columns:
            assert col not in SENSITIVE_COLUMNS


def test_guided_transform_filter_and_derive_price_bins():
    """Verify filter and derive generates correct price tiers, cultural tags, and code snippet."""
    df, snippet = filter_and_derive_poi(
        min_cost=0.0,
        max_cost=300.0,
        selected_categories=["heritage", "museum"],
        only_step_free=False
    )
    assert len(df) > 0
    assert "price_tier" in df.columns
    assert "is_cultural" in df.columns
    assert all(df["is_cultural"] == True)
    assert all(df["entry_cost"] <= 300.0)

    # Verify Free tier isolation
    free_items = df[df["entry_cost"] == 0.0]
    if len(free_items) > 0:
        assert all(free_items["price_tier"] == "Free (INR 0)")

    # Verify code snippet
    assert "pd.cut" in snippet or "price_tier" in snippet
    assert "activities_poi" in snippet


def test_guided_transform_groupby_and_pivot_matrix():
    """Verify split-apply-combine and 45-city pivot matrix."""
    # 1. Groupby
    agg_df, g_snippet = groupby_aggregate_stops("city_name")
    assert len(agg_df) == 45
    assert "cultural_share_pct" in agg_df.columns
    assert "total_stops" in agg_df.columns
    assert agg_df["total_stops"].sum() == 3191

    # 2. Pivot Matrix
    pivot_df, long_df, p_snippet = pivot_city_category_matrix()
    assert len(pivot_df) == 45  # 45 cities as rows
    assert "heritage" in pivot_df.columns
    assert "museum" in pivot_df.columns
    assert "religious" in pivot_df.columns
    assert "food" in pivot_df.columns
    assert "pivot" in p_snippet
    assert "melt" in p_snippet


def test_canonical_outer_join_audited_set_partition():
    """Verify exact audited set partition: 363 saved, 655 planned, 352 both, 11 saved-only, 303 planned-only, 666 outer."""
    res = compute_canonical_saved_planned_merge()
    assert res.saved_count == 363
    assert res.planned_count == 655
    assert res.both_count == 352
    assert res.saved_only_count == 11
    assert res.planned_only_count == 303
    assert res.full_outer_count == 666
    assert res.both_count + res.saved_only_count + res.planned_only_count == 666


def test_sql_sandbox_authorizer_security_and_resource_bounds():
    """Verify SQLite authorizer blocks writes, DDL, PRAGMA, stacked queries, and bounds rows/length."""
    sandbox = ReadOnlySQLSandbox()

    # 1. Permitted SELECT
    ok = sandbox.execute_query("SELECT city_id, name, state FROM cities WHERE country_code='IN' LIMIT 5")
    assert ok.is_success is True
    assert ok.row_count == 5

    # 2. Denied INSERT
    res_ins = sandbox.execute_query("INSERT INTO cities (city_id, name) VALUES ('hack', 'Hacked')")
    assert res_ins.is_success is False
    assert "Disallowed" in res_ins.error_message or "Denied" in res_ins.error_message

    # 3. Denied UPDATE
    res_upd = sandbox.execute_query("UPDATE cities SET name='Hacked' WHERE city_id='cty_c07454f1'")
    assert res_upd.is_success is False

    # 4. Denied DELETE
    res_del = sandbox.execute_query("DELETE FROM cities")
    assert res_del.is_success is False

    # 5. Denied DROP TABLE
    res_drop = sandbox.execute_query("DROP TABLE cities")
    assert res_drop.is_success is False

    # 6. Denied PRAGMA
    res_prg = sandbox.execute_query("PRAGMA table_info(cities)")
    assert res_prg.is_success is False

    # 7. Stacked Queries rejected
    res_stk = sandbox.execute_query("SELECT 1; SELECT 2")
    assert res_stk.is_success is False
    assert "Multiple statements" in res_stk.error_message

    # 8. Length bound > 1500 chars rejected
    long_q = "SELECT " + ("1+" * 800) + "1"
    res_len = sandbox.execute_query(long_q)
    assert res_len.is_success is False
    assert "exceeds maximum permitted length" in res_len.error_message

    # 9. 500 rows maximum truncation
    res_500 = sandbox.execute_query("SELECT * FROM activities_poi")
    assert res_500.is_success is True
    assert res_500.row_count == 500
    assert res_500.is_truncated is True


def test_typed_exports_formula_defense_and_parquet_roundtrip():
    """Verify spreadsheet formula escaping and PyArrow Parquet binary round-trip."""
    test_df = pd.DataFrame([
        {"id": 1, "text": "=2+5", "value": 10.5},
        {"id": 2, "text": "+Malicious", "value": 20.0},
        {"id": 3, "text": "-Dangerous", "value": 30.0},
        {"id": 4, "text": "@AtSign", "value": 40.0},
        {"id": 5, "text": "Normal String", "value": 50.0},
    ])

    # Formula injection protection
    csv_str = export_dataframe_to_csv(test_df)
    assert "'=2+5" in csv_str
    assert "'+Malicious" in csv_str
    assert "'-Dangerous" in csv_str
    assert "'@AtSign" in csv_str
    assert "Normal String" in csv_str

    # Parquet binary round-trip
    pq_bytes = export_dataframe_to_parquet(test_df)
    assert len(pq_bytes) > 0
    read_df = pd.read_parquet(io.BytesIO(pq_bytes), engine="pyarrow")
    assert len(read_df) == 5
    assert list(read_df.columns) == list(test_df.columns)
    assert read_df["value"].sum() == 150.5


def test_syllabus_reference_covers_units_1_to_5():
    """Verify comprehensive syllabus reference coverage across Units 1–5."""
    units = get_syllabus_reference_units()
    unit_names = [u["unit"] for u in units]
    for exp_unit in ["Unit 1", "Unit 2", "Unit 3", "Unit 4", "Unit 5"]:
        assert exp_unit in unit_names

    for u in units:
        assert len(u["title"]) > 0
        assert len(u["formula_syntax"]) > 0
        assert len(u["prerequisites"]) > 0
        assert len(u["study_example"]) > 0
        assert len(u["interpretation"]) > 0


def test_dev_lab_apptest_loads_and_navigates_cleanly():
    """Verify AppTest loads DEV Lab workbench with 0 exceptions across all components."""
    at = AppTest.from_file(str(ROOT_DIR / "app.py"))
    at.query_params["view"] = "devlab"
    at.run()
    assert not at.exception
    assert len(at.tabs) >= 5
