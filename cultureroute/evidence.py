"""Venue Field-Level Evidence Model and Resolver for CultureRoute (Phase 6).

Implements:
1. Append-only reviewable evidence store keyed to real place IDs and fields:
   - opening_hours
   - entry_fee
   - step_free_access
   - operating_status
   - typical_duration
2. Source hierarchy & conflict precedence:
   - OFFICIAL_GAZETTE > PRIMARY_VENUE_NOTICE > TICKETING_PORTAL > SURVEY_REPORT > CROWDSOURCED
3. Freshness policy (default 365 days max age; older evidence marked STALE).
4. Conflicting resolution: conflicting equal-precedence claims resolved to CONFLICTING status.
5. Injected clock support for deterministic temporal testing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple


class EvidenceSourceType(str, Enum):
    OFFICIAL_GAZETTE = "OFFICIAL_GAZETTE"
    PRIMARY_VENUE_NOTICE = "PRIMARY_VENUE_NOTICE"
    TICKETING_PORTAL = "TICKETING_PORTAL"
    SURVEY_REPORT = "SURVEY_REPORT"
    CROWDSOURCED = "CROWDSOURCED"


# Priority weight for conflict resolution (higher = more authoritative)
SOURCE_PRECEDENCE = {
    EvidenceSourceType.OFFICIAL_GAZETTE: 50,
    EvidenceSourceType.PRIMARY_VENUE_NOTICE: 40,
    EvidenceSourceType.TICKETING_PORTAL: 30,
    EvidenceSourceType.SURVEY_REPORT: 20,
    EvidenceSourceType.CROWDSOURCED: 10,
}


class FieldEvidenceStatus(str, Enum):
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"
    CONFLICTING = "CONFLICTING"


@dataclass(frozen=True)
class VenueEvidenceRecord:
    evidence_id: str
    source_id: str
    field_name: str
    source_type: EvidenceSourceType
    source_citation: str
    source_url: Optional[str]
    checked_date: date
    valid_from: Optional[date]
    valid_until: Optional[date]
    raw_value: str
    normalized_value: Dict[str, Any]
    visitor_scope: str = "ALL"  # "INDIAN_ADULT", "FOREIGN_ADULT", "CHILD", "ALL"


@dataclass(frozen=True)
class ResolvedFieldEvidence:
    field_name: str
    status: FieldEvidenceStatus
    value: Optional[Dict[str, Any]]
    display_text: str
    source_citation: Optional[str]
    source_url: Optional[str]
    checked_date: Optional[date]
    is_conflicting: bool = False
    is_stale: bool = False
    notes: Optional[str] = None


class VenueEvidenceStore:
    """SQLite-backed append-only evidence repository."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS venue_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_citation TEXT NOT NULL,
                    source_url TEXT,
                    checked_date TEXT NOT NULL,
                    valid_from TEXT,
                    valid_until TEXT,
                    raw_value TEXT NOT NULL,
                    normalized_value_json TEXT NOT NULL,
                    visitor_scope TEXT NOT NULL DEFAULT 'ALL',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_evidence_place_field ON venue_evidence(source_id, field_name);
            """)

    def insert_evidence(self, rec: VenueEvidenceRecord) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO venue_evidence (
                    evidence_id, source_id, field_name, source_type, source_citation,
                    source_url, checked_date, valid_from, valid_until, raw_value,
                    normalized_value_json, visitor_scope
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec.evidence_id,
                rec.source_id,
                rec.field_name,
                rec.source_type.value,
                rec.source_citation,
                rec.source_url,
                rec.checked_date.isoformat(),
                rec.valid_from.isoformat() if rec.valid_from else None,
                rec.valid_until.isoformat() if rec.valid_until else None,
                rec.raw_value,
                json.dumps(rec.normalized_value, ensure_ascii=False),
                rec.visitor_scope
            ))

    def get_evidence_records(self, source_id: str, field_name: Optional[str] = None) -> List[VenueEvidenceRecord]:
        with self._get_connection() as conn:
            if field_name:
                rows = conn.execute(
                    "SELECT * FROM venue_evidence WHERE source_id = ? AND field_name = ? ORDER BY checked_date DESC",
                    (source_id, field_name)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM venue_evidence WHERE source_id = ? ORDER BY field_name, checked_date DESC",
                    (source_id,)
                ).fetchall()

        records = []
        for r in rows:
            records.append(VenueEvidenceRecord(
                evidence_id=r["evidence_id"],
                source_id=r["source_id"],
                field_name=r["field_name"],
                source_type=EvidenceSourceType(r["source_type"]),
                source_citation=r["source_citation"],
                source_url=r["source_url"],
                checked_date=date.fromisoformat(r["checked_date"]),
                valid_from=date.fromisoformat(r["valid_from"]) if r["valid_from"] else None,
                valid_until=date.fromisoformat(r["valid_until"]) if r["valid_until"] else None,
                raw_value=r["raw_value"],
                normalized_value=json.loads(r["normalized_value_json"]),
                visitor_scope=r["visitor_scope"]
            ))
        return records

    def resolve_field(
        self,
        source_id: str,
        field_name: str,
        visit_date: date,
        visitor_profile: str = "INDIAN_ADULT",
        clock_date: Optional[date] = None,
        max_age_days: int = 365
    ) -> ResolvedFieldEvidence:
        """Resolve the effective evidence state for a venue field on a target date."""
        today = clock_date or date.today()
        records = self.get_evidence_records(source_id, field_name)

        if not records:
            return ResolvedFieldEvidence(
                field_name=field_name,
                status=FieldEvidenceStatus.UNKNOWN,
                value=None,
                display_text="Unknown (No verified field records)",
                source_citation=None,
                source_url=None,
                checked_date=None,
                notes="No primary evidence recorded for this field in the catalog."
            )

        # Filter by visitor scope: either exact match or "ALL"
        applicable = [
            r for r in records
            if r.visitor_scope in (visitor_profile, "ALL")
        ]

        if not applicable:
            applicable = records

        # Filter by temporal validity on visit_date
        temporally_valid = []
        for r in applicable:
            if r.valid_from and visit_date < r.valid_from:
                continue
            if r.valid_until and visit_date > r.valid_until:
                continue
            temporally_valid.append(r)

        if not temporally_valid:
            # All available records are outside the effective date window
            newest_rec = sorted(applicable, key=lambda x: x.checked_date, reverse=True)[0]
            return ResolvedFieldEvidence(
                field_name=field_name,
                status=FieldEvidenceStatus.UNKNOWN,
                value=None,
                display_text="Unknown (Visit date outside documented validity)",
                source_citation=newest_rec.source_citation,
                source_url=newest_rec.source_url,
                checked_date=newest_rec.checked_date,
                notes=f"Evidence valid window did not cover requested date {visit_date}."
            )

        # Sort by source precedence weight (highest first), then by checked_date (newest first)
        temporally_valid.sort(
            key=lambda r: (SOURCE_PRECEDENCE.get(r.source_type, 0), r.checked_date),
            reverse=True
        )

        top_priority = SOURCE_PRECEDENCE.get(temporally_valid[0].source_type, 0)
        top_candidates = [
            r for r in temporally_valid
            if SOURCE_PRECEDENCE.get(r.source_type, 0) == top_priority
        ]

        # Check for conflicts among equal-precedence top candidates
        # Distinct normalized values represent a real conflict
        values_repr = {json.dumps(r.normalized_value, sort_keys=True) for r in top_candidates}
        if len(values_repr) > 1:
            return ResolvedFieldEvidence(
                field_name=field_name,
                status=FieldEvidenceStatus.CONFLICTING,
                value=None,
                display_text="Conflicting Claims (Disagreement between authoritative sources)",
                source_citation="Multiple authoritative sources",
                source_url=None,
                checked_date=top_candidates[0].checked_date,
                is_conflicting=True,
                notes=f"Conflicting claims detected between {len(top_candidates)} sources of equal rank."
            )

        chosen = top_candidates[0]
        age_days = (today - chosen.checked_date).days
        is_stale = age_days > max_age_days

        status = FieldEvidenceStatus.STALE if is_stale else FieldEvidenceStatus.KNOWN
        display_str = self._format_display_value(field_name, chosen.normalized_value)

        return ResolvedFieldEvidence(
            field_name=field_name,
            status=status,
            value=chosen.normalized_value,
            display_text=display_str + (" [STALE]" if is_stale else ""),
            source_citation=chosen.source_citation,
            source_url=chosen.source_url,
            checked_date=chosen.checked_date,
            is_stale=is_stale,
            notes=f"Verified from {chosen.source_type.value} (checked {chosen.checked_date})."
        )

    def _format_display_value(self, field_name: str, val: Dict[str, Any]) -> str:
        if field_name == "entry_fee":
            if val.get("is_free"):
                return "Free Admission (INR 0.00)"
            amt = val.get("amount")
            curr = val.get("currency", "INR")
            tier = val.get("tier_name", "General")
            return f"{curr} {amt:.2f} ({tier})"
        elif field_name == "opening_hours":
            opens = val.get("opens_at", "Unknown")
            closes = val.get("closes_at", "Unknown")
            days = val.get("days", "Daily")
            return f"{opens} – {closes} ({days})"
        elif field_name == "step_free_access":
            acc = val.get("is_accessible")
            detail = val.get("detail", "")
            return f"Step-Free Access: {'Yes' if acc else 'No'}" + (f" ({detail})" if detail else "")
        elif field_name == "operating_status":
            stat = val.get("status", "OPEN")
            reason = val.get("reason", "")
            return f"Status: {stat}" + (f" - {reason}" if reason else "")
        elif field_name == "typical_duration":
            mins = val.get("duration_minutes", 60)
            return f"Typical Visit: {mins} minutes"
        return str(val)
