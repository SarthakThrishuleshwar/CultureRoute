"""Tests for CultureRoute Phase 6: Trustworthy Venue Evidence.

Verifies:
1. Explicit free entry vs unknown fee.
2. Distinct visitor profile fee tiers (Indian vs Foreign).
3. Temporal resolution and special temporary closure windows.
4. Stale evidence handling (>365 days max age).
5. Conflicting evidence detection and isolation.
6. Step-free accessibility evidence.
7. Future visit date outside verified validity window.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import pytest

from cultureroute.evidence import (
    EvidenceSourceType,
    FieldEvidenceStatus,
    VenueEvidenceRecord,
    VenueEvidenceStore,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
CATALOG_DB = ROOT_DIR / "data" / "real_catalog.db"


@pytest.fixture
def evidence_store():
    assert CATALOG_DB.exists(), "real_catalog.db must exist"
    return VenueEvidenceStore(CATALOG_DB)


def test_explicit_free_entry_vs_unknown_fee(evidence_store):
    """Verify free entry (Chand Baori) is KNOWN Free, while unevidenced place is UNKNOWN."""
    # Chand Baori (WD:Q2273412) has verified free entry
    res_free = evidence_store.resolve_field(
        source_id="WD:Q2273412",
        field_name="entry_fee",
        visit_date=date(2026, 11, 10),
        clock_date=date(2026, 11, 10)
    )
    assert res_free.status == FieldEvidenceStatus.KNOWN
    assert res_free.value["is_free"] is True
    assert res_free.value["amount"] == 0.0
    assert "Free" in res_free.display_text

    # Unevidenced place (e.g. Somnath Temple has no fee evidence in DB)
    res_unknown = evidence_store.resolve_field(
        source_id="WD:NON_EXISTENT_VENUE",
        field_name="entry_fee",
        visit_date=date(2026, 11, 10),
        clock_date=date(2026, 11, 10)
    )
    assert res_unknown.status == FieldEvidenceStatus.UNKNOWN
    assert res_unknown.value is None


def test_distinct_fee_tiers(evidence_store):
    """Verify separate fee tiers for Indian Adult vs Foreign Adult (Badami Cave Temples)."""
    # Indian Adult
    res_in = evidence_store.resolve_field(
        source_id="WD:Q825236",
        field_name="entry_fee",
        visit_date=date(2026, 11, 10),
        visitor_profile="INDIAN_ADULT",
        clock_date=date(2026, 11, 10)
    )
    assert res_in.status == FieldEvidenceStatus.KNOWN
    assert res_in.value["amount"] == 25.0
    assert res_in.value["currency"] == "INR"

    # Foreign Adult
    res_fn = evidence_store.resolve_field(
        source_id="WD:Q825236",
        field_name="entry_fee",
        visit_date=date(2026, 11, 10),
        visitor_profile="FOREIGN_ADULT",
        clock_date=date(2026, 11, 10)
    )
    assert res_fn.status == FieldEvidenceStatus.KNOWN
    assert res_fn.value["amount"] == 300.0
    assert res_fn.value["currency"] == "INR"


def test_special_temporal_closure(evidence_store):
    """Verify special closure during July monsoon window for WD:Q3517553."""
    # Inside July monsoon window -> Status is CLOSED
    res_july = evidence_store.resolve_field(
        source_id="WD:Q3517553",
        field_name="operating_status",
        visit_date=date(2026, 7, 15),
        clock_date=date(2026, 7, 1)
    )
    assert res_july.status == FieldEvidenceStatus.KNOWN
    assert res_july.value["status"] == "CLOSED"
    assert "conservation" in res_july.value["reason"].lower()

    # Outside July window -> No active closure record -> UNKNOWN / Normal
    res_nov = evidence_store.resolve_field(
        source_id="WD:Q3517553",
        field_name="operating_status",
        visit_date=date(2026, 11, 10),
        clock_date=date(2026, 11, 1)
    )
    assert res_nov.status == FieldEvidenceStatus.UNKNOWN


def test_stale_evidence_detection(evidence_store):
    """Verify evidence checked >365 days ago is flagged STALE."""
    res_stale = evidence_store.resolve_field(
        source_id="WD:Q1143887",
        field_name="entry_fee",
        visit_date=date(2026, 11, 10),
        clock_date=date(2026, 11, 10),
        max_age_days=365
    )
    assert res_stale.status == FieldEvidenceStatus.STALE
    assert res_stale.is_stale is True
    assert "[STALE]" in res_stale.display_text


def test_conflicting_claims_detection(evidence_store):
    """Verify conflicting claims between equal-priority sources result in CONFLICTING status."""
    res_conflict = evidence_store.resolve_field(
        source_id="WD:Q2570737",
        field_name="opening_hours",
        visit_date=date(2026, 11, 10),
        clock_date=date(2026, 11, 10)
    )
    assert res_conflict.status == FieldEvidenceStatus.CONFLICTING
    assert res_conflict.is_conflicting is True
    assert "Conflicting Claims" in res_conflict.display_text


def test_step_free_accessibility_evidence(evidence_store):
    """Verify step-free accessibility evidence distinctions."""
    # Sanchi Stupa has step-free access
    res_sanchi = evidence_store.resolve_field(
        source_id="WD:Q199874",
        field_name="step_free_access",
        visit_date=date(2026, 11, 10),
        clock_date=date(2026, 11, 10)
    )
    assert res_sanchi.status == FieldEvidenceStatus.KNOWN
    assert res_sanchi.value["is_accessible"] is True

    # Badami Caves has steep rock stairs -> Not step-free
    res_badami = evidence_store.resolve_field(
        source_id="WD:Q825236",
        field_name="step_free_access",
        visit_date=date(2026, 11, 10),
        clock_date=date(2026, 11, 10)
    )
    assert res_badami.status == FieldEvidenceStatus.KNOWN
    assert res_badami.value["is_accessible"] is False


def test_future_visit_outside_valid_window(evidence_store):
    """Verify future date past valid_until is marked UNKNOWN with date notice."""
    res_future = evidence_store.resolve_field(
        source_id="WD:Q825236",
        field_name="entry_fee",
        visit_date=date(2029, 1, 1),
        clock_date=date(2026, 11, 10)
    )
    assert res_future.status == FieldEvidenceStatus.UNKNOWN
    assert "outside documented validity" in res_future.display_text
