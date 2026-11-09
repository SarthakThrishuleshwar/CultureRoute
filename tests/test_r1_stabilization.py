"""Tests for CultureRoute Stage R1: Stabilization and Two-Pack Boundary Enforcement.

Verifies:
1. DEV Lab load and study databases accessibility (open_study_databases available).
2. Robust time parsing and validation in planner (invalid times handled gracefully).
3. Browser/AppTest regression for invalid planner time ("noon" gives inline warning, no crash).
4. Browser/AppTest regression for DEV Lab loading with 0 exceptions.
5. Legacy database absence tolerance (app runs even without real_catalog.db).
6. Integrity of the two study pack hashes (SmartTrip and WanderMatch).
7. Completeness of documented requirements (plotly, scipy, pyarrow present).
8. Offline execution of core workflows without external network dependencies.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

from cultureroute.planner import parse_time_to_minutes, plan_synthetic_day
from cultureroute.study_data import open_study_databases, verify_and_audit_study

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_dev_lab_open_study_databases_accessible():
    """Verify open_study_databases context manager is importable and executes query."""
    with open_study_databases() as (smart, wander):
        assert smart is not None
        assert wander is not None
        # All POIs total 900, exactly 675 in India
        total_row = smart.execute("SELECT count(*) as c FROM activities_poi").fetchone()
        assert total_row["c"] == 900
        in_row = smart.execute(
            "SELECT count(*) as c FROM activities_poi a JOIN cities c USING(city_id) WHERE c.country_code='IN'"
        ).fetchone()
        assert in_row["c"] == 675


def test_planner_time_parsing_valid_and_invalid():
    """Verify parse_time_to_minutes handles both valid times and invalid inputs like 'noon'."""
    # Valid times
    assert parse_time_to_minutes("09:00") == 540
    assert parse_time_to_minutes("00:00") == 0
    assert parse_time_to_minutes("23:59") == 1439
    assert parse_time_to_minutes("12:30") == 750

    # Invalid times (must return None, never raise unhandled exception)
    assert parse_time_to_minutes("noon") is None
    assert parse_time_to_minutes("25:00") is None
    assert parse_time_to_minutes("09:60") is None
    assert parse_time_to_minutes("-01:00") is None
    assert parse_time_to_minutes("abc") is None
    assert parse_time_to_minutes("") is None
    assert parse_time_to_minutes(None) is None  # type: ignore

    # Direct plan_synthetic_day invocation with invalid time raises clear ValueError
    with pytest.raises(ValueError, match="Invalid time format"):
        plan_synthetic_day(start_time="noon")


def test_planner_apptest_invalid_time_inline_warning():
    """Verify in AppTest that entering 'noon' shows an inline warning and does not crash."""
    at = AppTest.from_file(str(ROOT_DIR / "app.py"))
    at.query_params["view"] = "planner"
    at.run()
    assert not at.exception

    # Enter invalid start time 'noon'
    time_input = at.get("text_input")[0]
    time_input.set_value("noon").run()
    assert not at.exception
    warnings = [w.value for w in at.warning]
    assert any("Invalid start time 'noon'" in w for w in warnings)


def test_dev_lab_apptest_loads_cleanly():
    """Verify in AppTest that navigating to DEV Lab loads with 0 exceptions."""
    at = AppTest.from_file(str(ROOT_DIR / "app.py"))
    at.query_params["view"] = "devlab"
    at.run()
    assert not at.exception


def test_apptest_runs_without_legacy_catalog_db():
    """Verify in AppTest that if real_catalog.db is absent, the app operates cleanly."""
    db_path = ROOT_DIR / "data" / "real_catalog.db"
    bak_path = ROOT_DIR / "data" / "real_catalog.db.tmp_r1_test"
    renamed = False

    if db_path.exists():
        try:
            os.rename(db_path, bak_path)
            renamed = True
        except PermissionError:
            renamed = False

    try:
        at = AppTest.from_file(str(ROOT_DIR / "app.py"))
        at.query_params["view"] = "planner"
        at.run()
        assert not at.exception

        at.query_params["view"] = "devlab"
        at.run()
        assert not at.exception
    finally:
        if renamed and bak_path.exists():
            if db_path.exists():
                db_path.unlink()
            os.rename(bak_path, db_path)


def test_study_pack_hashes_integrity():
    """Verify the SHA-256 hashes of the two original study packs match the audited baselines."""
    smart_path = ROOT_DIR / "SmartTrip (1).zip"
    wander_path = ROOT_DIR / "WanderMatch.zip"

    assert smart_path.exists(), "SmartTrip (1).zip must be present"
    assert wander_path.exists(), "WanderMatch.zip must be present"

    smart_hash = hashlib.sha256(smart_path.read_bytes()).hexdigest()
    wander_hash = hashlib.sha256(wander_path.read_bytes()).hexdigest()

    expected_smart = "17c0a7d4bb399c4fd2b335cef5af4e02cbd21207103fea69fa9632ee6de06cc6"
    expected_wander = "dc8435c53e3c24ff611cfbc34c80accdc3b283c47aece49ecc52041e6eca18f8"

    assert smart_hash == expected_smart, f"SmartTrip (1).zip hash mismatch: {smart_hash}"
    assert wander_hash == expected_wander, f"WanderMatch.zip hash mismatch: {wander_hash}"


def test_requirements_documented_packages():
    """Verify that requirements.txt documents all essential dependencies."""
    req_file = ROOT_DIR / "requirements.txt"
    assert req_file.exists()
    content = req_file.read_text(encoding="utf-8").lower()

    for pkg in ["streamlit", "pandas", "pydantic", "pytest", "plotly", "scipy", "pyarrow"]:
        assert pkg in content, f"Package '{pkg}' must be documented in requirements.txt"


def test_offline_core_study_audit():
    """Verify that study audit runs completely offline and matches audited baselines."""
    report = verify_and_audit_study()
    assert report.distinct_tables_count == 24
    assert report.distinct_rows_count == 48728
    assert report.india_cities_count == 45
    assert report.india_attractions_count == 675
    assert report.study_trips_count == 411
