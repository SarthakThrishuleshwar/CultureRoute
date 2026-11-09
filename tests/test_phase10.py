"""Tests for CultureRoute Phase 10: DEV Lab & Syllabus Demonstrator.

Verifies:
1. Unit 1 EDA: Three-way comparison (Empirical p, Wilson Score CI, Beta-Binomial Credible Interval).
2. Unit 2 Transformations: Canonical Outer Merge (363 saved, 655 planned, 352 both, 11 saved-only, 303 planned-only, 666 full outer).
3. Unit 3 SQL: Secured read-only sandbox with SQLite authorizer (blocks writes, DDL, PRAGMA, stacked queries).
4. Unit 5 Exports: CSV formula injection defense and Parquet binary round-tripping.
"""

from __future__ import annotations

import io
import pandas as pd
import pytest

from cultureroute.dev_lab import (
    compute_methodology_comparison,
    compute_canonical_saved_planned_merge,
    ReadOnlySQLSandbox,
    export_dataframe_to_csv,
    export_dataframe_to_parquet
)


def test_unit1_methodology_comparison():
    """Verify EDA vs Classical vs Bayesian intervals on deterministic trip cohort."""
    res = compute_methodology_comparison()
    assert res.sample_size == 341
    assert res.success_count == 301
    assert res.empirical_proportion == pytest.approx(0.8827, abs=0.0001)

    # 95% Wilson Score Interval
    assert res.wilson_lower == pytest.approx(0.8442, abs=0.001)
    assert res.wilson_upper == pytest.approx(0.9127, abs=0.001)
    assert res.wilson_lower < res.empirical_proportion < res.wilson_upper

    # Bayesian Beta-Binomial Posterior Credible Interval with Beta(1,1) prior
    assert res.bayes_posterior_alpha == 302
    assert res.bayes_posterior_beta == 41
    assert res.bayes_lower == pytest.approx(0.8442, abs=0.001)
    assert res.bayes_upper == pytest.approx(0.9126, abs=0.001)


def test_unit2_canonical_saved_planned_merge():
    """Verify exact audited set operations: 363 saved, 655 planned, 352 both, 11 saved-only, 303 planned-only, 666 outer."""
    res = compute_canonical_saved_planned_merge()
    assert res.saved_count == 363
    assert res.planned_count == 655
    assert res.inner_count == 352
    assert res.left_count == 363
    assert res.full_outer_count == 666
    assert res.both_count == 352
    assert res.saved_only_count == 11
    assert res.planned_only_count == 303
    assert res.both_count + res.saved_only_count + res.planned_only_count == 666


def test_unit3_sql_sandbox_security_and_bounds():
    """Verify SQL sandbox authorizer denies writes, DDL, PRAGMA, and stacked queries."""
    sandbox = ReadOnlySQLSandbox()

    # 1. Allowed read query
    ok_res = sandbox.execute_query("SELECT city_id, name, state FROM cities WHERE country_code='IN' LIMIT 5")
    assert ok_res.is_success is True
    assert ok_res.row_count == 5
    assert len(ok_res.columns) == 3

    # 2. Blocked write: INSERT
    ins_res = sandbox.execute_query("INSERT INTO cities (city_id, name) VALUES ('fake', 'Fake City')")
    assert ins_res.is_success is False
    assert "Disallowed SQL command" in ins_res.error_message or "Denied" in ins_res.error_message

    # 3. Blocked write: UPDATE
    upd_res = sandbox.execute_query("UPDATE cities SET name='Hacked' WHERE city_id='cty_c07454f1'")
    assert upd_res.is_success is False

    # 4. Blocked DDL: DROP TABLE
    drop_res = sandbox.execute_query("DROP TABLE cities")
    assert drop_res.is_success is False

    # 5. Blocked PRAGMA
    pragma_res = sandbox.execute_query("PRAGMA table_info(cities)")
    assert pragma_res.is_success is False

    # 6. Blocked stacked queries (semicolon injection)
    stacked_res = sandbox.execute_query("SELECT 1; SELECT 2")
    assert stacked_res.is_success is False
    assert "Multiple statements" in stacked_res.error_message


def test_unit5_export_csv_and_parquet_roundtrip():
    """Verify CSV formula escaping and binary Parquet round-trip parity."""
    sample_df = pd.DataFrame([
        {"poi_id": "poi_1", "name": "Normal Venue", "cost": 100.0},
        {"poi_id": "poi_2", "name": "=cmd|' /C calc'!A0", "cost": 0.0},  # Formula injection attempt
        {"poi_id": "poi_3", "name": "+Malicious", "cost": 50.0}
    ])

    # 1. CSV Formula Escaping
    csv_str = export_dataframe_to_csv(sample_df)
    assert "'=cmd" in csv_str
    assert "'+Malicious" in csv_str

    # 2. Parquet Round-Trip Parity
    parquet_bytes = export_dataframe_to_parquet(sample_df)
    assert len(parquet_bytes) > 0

    read_back = pd.read_parquet(io.BytesIO(parquet_bytes), engine="pyarrow")
    assert len(read_back) == len(sample_df)
    assert list(read_back.columns) == list(sample_df.columns)
    assert read_back["cost"].tolist() == sample_df["cost"].tolist()
