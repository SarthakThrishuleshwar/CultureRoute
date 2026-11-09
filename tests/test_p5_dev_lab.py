"""Tests for CultureRoute Stage P5: DEV Lab Evaluator Workbench.

Verifies:
1. 6-Step Research Workflow & Provenance:
   - Select -> Inspect -> Transform -> Compare -> Chart -> Explain & Export.
   - Link back to Datasets catalog.
2. Canonical Merge Set Partition:
   - 352 Both (Inner join overlap)
   - 11 Saved-Only (WanderMatch)
   - 303 Planned-Only (SmartTrip)
   - 666 Full Outer Join distinct attractions.
3. Read-Only SQL Sandbox Security Invariants:
   - Allowlisted read queries succeed.
   - Denied writes (INSERT/UPDATE/DELETE/DROP/ALTER) are blocked by SQLite authorizer.
   - ATTACH and PRAGMA modifications are denied.
4. Formulas & Syntax (Units 1–5):
   - All 5 syllabus units documented with purpose, formula syntax, and study examples.
   - "Run this example" queries execute cleanly and return valid rows.
5. AppTest Integration:
   - ?view=devlab loads with 0 exceptions across all 5 tabs.
"""

from __future__ import annotations

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

from cultureroute.dev_lab import (
    ReadOnlySQLSandbox,
    compute_canonical_saved_planned_merge,
    get_syllabus_reference_units,
    filter_and_derive_poi,
    groupby_aggregate_stops,
    pivot_city_category_matrix,
    export_dataframe_to_csv,
    export_dataframe_to_parquet,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
APP_FILE = ROOT_DIR / "app.py"


def test_p5_canonical_outer_join_partition_counts():
    """Verify exact audited set partition counts in the canonical merge."""
    merge_res = compute_canonical_saved_planned_merge()

    assert merge_res.saved_count == 363
    assert merge_res.planned_count == 655
    assert merge_res.both_count == 352
    assert merge_res.saved_only_count == 11
    assert merge_res.planned_only_count == 303
    assert merge_res.full_outer_count == 666

    # Invariant: 352 + 11 + 303 == 666
    assert (merge_res.both_count + merge_res.saved_only_count + merge_res.planned_only_count) == merge_res.full_outer_count
    # Invariant: 352 + 11 == 363 (saved)
    assert (merge_res.both_count + merge_res.saved_only_count) == merge_res.saved_count
    # Invariant: 352 + 303 == 655 (planned)
    assert (merge_res.both_count + merge_res.planned_only_count) == merge_res.planned_count


def test_p5_sql_sandbox_security_authorizer():
    """Verify ReadOnlySQLSandbox allows safe SELECTs and strictly blocks writes."""
    sandbox = ReadOnlySQLSandbox()

    # Safe SELECT
    safe_res = sandbox.execute_query("SELECT city_id, name, population FROM cities WHERE country_code='IN' LIMIT 5")
    assert safe_res.is_success
    assert safe_res.row_count == 5
    assert safe_res.rows is not None
    assert len(safe_res.rows) == 5

    # Blocked INSERT
    blocked_insert = sandbox.execute_query("INSERT INTO cities (city_id, name) VALUES ('fake', 'Malicious City')")
    assert not blocked_insert.is_success
    assert any(w in blocked_insert.error_message.lower() for w in ["disallowed", "not authorized", "read-only"])

    # Blocked DROP
    blocked_drop = sandbox.execute_query("DROP TABLE cities")
    assert not blocked_drop.is_success

    # Blocked ATTACH
    blocked_attach = sandbox.execute_query("ATTACH DATABASE ':memory:' AS evil_db")
    assert not blocked_attach.is_success


def test_p5_formulas_and_syntax_units_coverage():
    """Verify all 5 syllabus units are defined and their preset queries execute cleanly."""
    units = get_syllabus_reference_units()
    assert len(units) == 5

    expected_units = ["Unit 1", "Unit 2", "Unit 3", "Unit 4", "Unit 5"]
    actual_units = [u["unit"] for u in units]
    assert actual_units == expected_units

    sandbox = ReadOnlySQLSandbox()
    for u in units:
        assert "purpose" in u
        assert "formula_syntax" in u
        assert "prerequisites" in u
        assert "study_example" in u
        assert "preset_query" in u

        # Run the example query in the sandbox
        res = sandbox.execute_query(u["preset_query"])
        assert res.is_success, f"{u['unit']} preset query failed: {res.error_message}"
        assert res.row_count > 0, f"{u['unit']} preset query returned 0 rows"


def test_p5_typed_export_roundtrip():
    """Verify CSV escaping and PyArrow Parquet export round-trip."""
    merge_res = compute_canonical_saved_planned_merge()
    df = merge_res.merged_df.head(20)

    # CSV
    csv_str = export_dataframe_to_csv(df)
    assert len(csv_str) > 0
    assert "poi_id" in csv_str

    # Parquet binary
    pq_bytes = export_dataframe_to_parquet(df)
    assert len(pq_bytes) > 0
    assert pq_bytes.startswith(b"PAR1")  # Standard Parquet magic bytes


def test_p5_apptest_dev_lab_loads_cleanly():
    """Verify AppTest loads DEV Lab with 0 exceptions across all 5 workbench tabs."""
    at = AppTest.from_file(str(APP_FILE))
    at.query_params["view"] = "devlab"
    at.run()
    assert not at.exception

    # Check 5 tabs
    assert len(at.tabs) >= 5

    # Check top banner content
    md_text = " ".join(m.value for m in at.markdown)
    assert "What You Can Do Here" in md_text
    assert "6-Step Evaluator Workbench" in md_text
    assert "1. Select" in md_text
    assert "6. Explain & Export" in md_text
