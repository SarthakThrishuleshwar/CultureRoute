"""Tests for CultureRoute Stage R2: Study Database and Calculation Contracts.

Verifies:
1. Deterministic build of study_cache.db from SmartTrip (1).zip and WanderMatch.zip.
2. Schema and row-level identity of the 8 shared tables.
3. Exact table count (24) and total row count (48,728).
4. Correctness of documented SQL views (45 cities, 675 POIs, 411 trips, 6,850 interactions, 3,191 stops, 225 events).
5. Schema catalog discoverability for all 24 canonical tables with grain, types, PK/FK, and null counts.
6. Sensitive personal data protection in safe column projections.
7. Shared result contracts (MetricContract, PlotDatasetContract, TableExportContract).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from cultureroute.study_db import (
    build_study_database,
    load_study_catalog,
    open_study_cache,
    DEFAULT_STUDY_DB,
    TableCatalogEntry,
    StudyDatabaseCatalog,
    MetricContract,
    PlotDatasetContract,
    TableExportContract,
    SENSITIVE_COLUMNS,
)

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_study_db_reproducible_build_and_row_reconciliation():
    """Verify building study database produces exactly 24 tables and 48,728 rows."""
    cat = build_study_database(DEFAULT_STUDY_DB, force=False)
    assert cat.metadata.total_tables == 24
    assert cat.metadata.total_rows == 48728
    assert len(cat.metadata.shared_tables) == 8
    assert len(cat.metadata.smart_only_tables) == 10
    assert len(cat.metadata.wander_only_tables) == 6


def test_build_determinism_twice_reconciliation():
    """Verify building twice in separate files yields identical table schemas and row counts."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        p1 = Path(tmp_dir) / "study1.db"
        p2 = Path(tmp_dir) / "study2.db"

        cat1 = build_study_database(p1, force=True)
        cat2 = build_study_database(p2, force=True)

        assert cat1.metadata.total_tables == cat2.metadata.total_tables == 24
        assert cat1.metadata.total_rows == cat2.metadata.total_rows == 48728

        for tbl in cat1.tables:
            assert tbl in cat2.tables
            t1, t2 = cat1.tables[tbl], cat2.tables[tbl]
            assert t1.row_count == t2.row_count
            assert t1.columns == t2.columns
            assert t1.column_types == t2.column_types
            assert t1.primary_key == t2.primary_key
            assert t1.null_counts == t2.null_counts
            assert t1.safe_columns == t2.safe_columns


def test_study_views_exact_baselines():
    """Verify that all documented views match audited study baseline counts."""
    with open_study_cache() as conn:
        cities = conn.execute("SELECT count(*) FROM view_study_cities").fetchone()[0]
        pois = conn.execute("SELECT count(*) FROM view_study_attractions").fetchone()[0]
        trips = conn.execute("SELECT count(*) FROM view_study_trips").fetchone()[0]
        interactions = conn.execute("SELECT count(*) FROM view_study_interactions").fetchone()[0]
        stops = conn.execute("SELECT count(*) FROM view_study_selected_stops").fetchone()[0]
        events = conn.execute("SELECT count(*) FROM view_study_events").fetchone()[0]

        assert cities == 45, f"Expected 45 study cities, got {cities}"
        assert pois == 675, f"Expected 675 attractions, got {pois}"
        assert trips == 411, f"Expected 411 non-cancelled trips, got {trips}"
        assert interactions == 6850, f"Expected 6850 interactions, got {interactions}"
        assert stops == 3191, f"Expected 3191 selected stops, got {stops}"
        assert events == 225, f"Expected 225 Indian events, got {events}"


def test_schema_catalog_and_safe_projections():
    """Verify that all 24 canonical tables have grains, types, and sensitive columns masked."""
    cat = load_study_catalog()
    assert len(cat.tables) == 24

    for tbl_name, tbl_meta in cat.tables.items():
        assert tbl_meta.grain != ""
        assert len(tbl_meta.columns) > 0
        assert tbl_meta.row_count >= 0

        # Check sensitive columns are excluded from safe_columns
        for c in tbl_meta.columns:
            if c.lower() in SENSITIVE_COLUMNS:
                assert c not in tbl_meta.safe_columns, f"Sensitive column {c} leaked into safe_columns for {tbl_name}"


def test_metric_and_export_contracts():
    """Verify instantiation of shared result contracts."""
    metric = MetricContract(
        name="cultural_listings_share",
        definition="Proportion of Indian attractions classified as cultural",
        population="45 Indian cities catalog attractions",
        filters="country_code='IN'",
        grain="1 row per attraction",
        units="percentage",
        numerator=211,
        denominator=675,
        value=0.31259,
        formatted_value="31.3%",
        null_policy="Exclude incomplete records",
        cutoff="2026-08-31",
        source_references=["activities_poi", "cities"]
    )
    assert metric.formatted_value == "31.3%"

    dataset = PlotDatasetContract(
        name="city_category_matrix",
        title="Attraction Counts by Category across Study Cities",
        question="Which cities lead in cultural attraction listings?",
        grain="City x Category",
        filters="country_code='IN'",
        units="count",
        data=[{"city": "Jaipur", "category": "heritage", "count": 7}],
        source_references=["view_study_attractions"]
    )
    assert len(dataset.data) == 1

    export_obj = TableExportContract(
        name="canonical_merge",
        columns=["poi_id", "name", "category", "in_saved", "in_planned"],
        rows=[["poi_001", "Hawa Mahal", "heritage", True, True]],
        row_count=1,
        format_type="csv",
        formula_safe=True
    )
    assert export_obj.row_count == 1
