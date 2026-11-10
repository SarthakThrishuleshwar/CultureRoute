"""Venue Field-Level Evidence Model and Resolver for CultureRoute (Phase 7).

Implements:
1. Append-only reviewable evidence store keyed to real place IDs and fields:
   - opening_hours
   - entry_fee
   - step_free_access
   - operating_status
   - typical_duration
2. Genuine append-only semantics:
   - Duplicate evidence_id raises ValueError/sqlite3.IntegrityError.
   - Evidence is persisted separately from real_catalog.db in data/venue_evidence.db.
   - Validation against RealCatalogStore to identify orphaned records.
3. Strict separation of source extract date, import date, and field checked date.
4. Five field-level states:
   - VERIFIED: Directly supported by authoritative primary venue/government evidence within freshness window.
   - PROVISIONAL: Preliminary / survey / crowdsourced evidence pending primary confirmation.
   - STALE: Evidence older than policy freshness window (default 365 days).
   - CONFLICTING: Disagreement between equal-rank authoritative sources.
   - UNKNOWN: Default state when no applicable evidence exists for requested visitor profile/date.
5. Multi-tier visitor profile awareness:
   - INDIAN_ADULT, FOREIGN_ADULT, CHILD, etc.
   - Free admission resolved to INR 0.00 ONLY when explicitly established by source.
   - Day-of-week closures (e.g. Taj Mahal closed Friday) recognized dynamically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from cultureroute.catalog import RealCatalogStore

DEFAULT_EVIDENCE_DB = Path(__file__).resolve().parent.parent / "data" / "venue_evidence.db"


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
    VERIFIED = "VERIFIED"
    KNOWN = "KNOWN"  # Backward compatibility alias for VERIFIED
    PROVISIONAL = "PROVISIONAL"
    STALE = "STALE"
    CONFLICTING = "CONFLICTING"
    UNKNOWN = "UNKNOWN"


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
    visitor_scope: str = "ALL"
    is_conflicting: bool = False
    is_stale: bool = False
    notes: Optional[str] = None


class VenueEvidenceStore:
    """SQLite-backed append-only evidence repository stored independently from real_catalog.db."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            self.db_path = DEFAULT_EVIDENCE_DB
        else:
            self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
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
                CREATE INDEX IF NOT EXISTS idx_evidence_source_id ON venue_evidence(source_id);
                CREATE TABLE IF NOT EXISTS evidence_retractions (
                    evidence_id TEXT PRIMARY KEY,
                    reason TEXT NOT NULL,
                    reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(evidence_id) REFERENCES venue_evidence(evidence_id)
                );
            """)

    def retract_evidence(self, evidence_id: str, reason: str) -> None:
        """Keep the original claim while excluding it from active resolution."""
        if not reason.strip():
            raise ValueError("A retraction needs an audit reason")
        with self._get_connection() as conn:
            if not conn.execute("SELECT 1 FROM venue_evidence WHERE evidence_id=?", (evidence_id,)).fetchone():
                raise ValueError(f"Unknown evidence ID: {evidence_id}")
            conn.execute("INSERT OR IGNORE INTO evidence_retractions(evidence_id, reason) VALUES (?,?)",
                         (evidence_id, reason))

    def insert_evidence(self, rec: VenueEvidenceRecord) -> None:
        """Genuinely append-only insert. Rejects duplicate evidence_id with ValueError."""
        with self._get_connection() as conn:
            try:
                conn.execute("""
                    INSERT INTO venue_evidence (
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
            except sqlite3.IntegrityError as e:
                raise ValueError(
                    f"Append-only violation: Evidence record with ID '{rec.evidence_id}' already exists and cannot be modified."
                ) from e

    def insert_evidence_batch(self, records: List[VenueEvidenceRecord]) -> None:
        """Batch append-only insert. Rejects duplicates atomically."""
        if not records:
            return
        params = [
            (
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
            )
            for rec in records
        ]
        with self._get_connection() as conn:
            try:
                conn.executemany("""
                    INSERT INTO venue_evidence (
                        evidence_id, source_id, field_name, source_type, source_citation,
                        source_url, checked_date, valid_from, valid_until, raw_value,
                        normalized_value_json, visitor_scope
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, params)
            except sqlite3.IntegrityError as e:
                raise ValueError(
                    f"Append-only violation during batch insert: duplicate evidence ID detected ({e})."
                ) from e

    def get_evidence_records(self, source_id: str, field_name: Optional[str] = None,
                             include_retracted: bool = False) -> List[VenueEvidenceRecord]:
        with self._get_connection() as conn:
            active = "" if include_retracted else " AND NOT EXISTS (SELECT 1 FROM evidence_retractions x WHERE x.evidence_id=e.evidence_id)"
            if field_name:
                rows = conn.execute(
                    "SELECT e.* FROM venue_evidence e WHERE e.source_id = ? AND e.field_name = ?" + active + " ORDER BY e.checked_date DESC, e.rowid DESC",
                    (source_id, field_name)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT e.* FROM venue_evidence e WHERE e.source_id = ?" + active + " ORDER BY e.field_name, e.checked_date DESC, e.rowid DESC",
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

    def get_all_source_ids(self) -> List[str]:
        """Return distinct source IDs represented in the evidence store."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT DISTINCT source_id FROM venue_evidence ORDER BY source_id").fetchall()
            return [r[0] for r in rows]

    def find_orphaned_records(self, catalog_store: RealCatalogStore) -> List[str]:
        """Validate all evidence against current catalog. Return source_ids that no longer exist in catalog."""
        evidence_sids = self.get_all_source_ids()
        if not evidence_sids:
            return []

        orphaned = []
        with catalog_store._get_connection() as conn:
            for sid in evidence_sids:
                exists = conn.execute("SELECT 1 FROM places WHERE source_id = ? LIMIT 1", (sid,)).fetchone()
                if not exists:
                    orphaned.append(sid)
        return orphaned

    def get_pilot_summary_counts(self) -> Dict[str, int]:
        """Count total evidence records by field status and source authority."""
        with self._get_connection() as conn:
            total_records = conn.execute("SELECT count(*) FROM venue_evidence").fetchone()[0]
            distinct_places = conn.execute("SELECT count(DISTINCT source_id) FROM venue_evidence").fetchone()[0]
            distinct_fields = conn.execute("SELECT count(DISTINCT field_name) FROM venue_evidence").fetchone()[0]
            return {
                "total_records": total_records,
                "distinct_places": distinct_places,
                "distinct_fields": distinct_fields,
            }

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
                display_text="UNKNOWN (No verified field evidence)",
                source_citation=None,
                source_url=None,
                checked_date=None,
                visitor_scope=visitor_profile,
                notes="No primary evidence recorded for this field in the catalog."
            )

        # Filter by visitor scope: either exact match or "ALL"
        applicable = [
            r for r in records
            if r.visitor_scope in (visitor_profile, "ALL")
        ]

        if not applicable:
            # Crucial requirement: Never substitute another visitor group's fee or rules
            return ResolvedFieldEvidence(
                field_name=field_name,
                status=FieldEvidenceStatus.UNKNOWN,
                value=None,
                display_text=f"UNKNOWN (No evidence for visitor group: {visitor_profile})",
                source_citation=None,
                source_url=None,
                checked_date=None,
                visitor_scope=visitor_profile,
                notes=f"Evidence exists for other visitor scopes, but none for '{visitor_profile}'."
            )

        # Filter by temporal validity on visit_date
        temporally_valid = []
        for r in applicable:
            if r.valid_from and visit_date < r.valid_from:
                continue
            if r.valid_until and visit_date > r.valid_until:
                continue
            temporally_valid.append(r)

        if not temporally_valid:
            newest_rec = sorted(applicable, key=lambda x: x.checked_date, reverse=True)[0]
            return ResolvedFieldEvidence(
                field_name=field_name,
                status=FieldEvidenceStatus.UNKNOWN,
                value=None,
                display_text=f"UNKNOWN (Visit date {visit_date} outside documented validity)",
                source_citation=newest_rec.source_citation,
                source_url=newest_rec.source_url,
                checked_date=newest_rec.checked_date,
                visitor_scope=visitor_profile,
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
        values_repr = {json.dumps(r.normalized_value, sort_keys=True) for r in top_candidates}
        if len(values_repr) > 1:
            return ResolvedFieldEvidence(
                field_name=field_name,
                status=FieldEvidenceStatus.CONFLICTING,
                value=None,
                display_text="CONFLICTING (Disagreement between authoritative sources)",
                source_citation=f"Conflicting: {', '.join(r.source_citation for r in top_candidates)}",
                source_url=top_candidates[0].source_url,
                checked_date=top_candidates[0].checked_date,
                visitor_scope=visitor_profile,
                is_conflicting=True,
                notes=f"Conflicting claims detected between {len(top_candidates)} sources of equal precedence ({top_candidates[0].source_type.value})."
            )

        chosen = top_candidates[0]
        age_days = (today - chosen.checked_date).days
        is_stale = age_days > max_age_days

        # Determine status: STALE, PROVISIONAL, or VERIFIED
        if is_stale:
            status = FieldEvidenceStatus.STALE
        elif chosen.source_type in (EvidenceSourceType.SURVEY_REPORT, EvidenceSourceType.CROWDSOURCED):
            status = FieldEvidenceStatus.PROVISIONAL
        elif field_name == "opening_hours" and (chosen.normalized_value.get("opens_at") is None or
                                                 chosen.normalized_value.get("closes_at") is None):
            # A documented weekly closure does not verify the rest of the opening window.
            status = FieldEvidenceStatus.PROVISIONAL
        else:
            status = FieldEvidenceStatus.VERIFIED

        display_str = self._format_display_value(field_name, chosen.normalized_value, visit_date=visit_date)

        return ResolvedFieldEvidence(
            field_name=field_name,
            status=status,
            value=chosen.normalized_value,
            display_text=display_str + (" [STALE]" if is_stale else ""),
            source_citation=chosen.source_citation,
            source_url=chosen.source_url,
            checked_date=chosen.checked_date,
            visitor_scope=chosen.visitor_scope,
            is_stale=is_stale,
            notes=f"Status: {status.value} from {chosen.source_type.value} (checked {chosen.checked_date.isoformat()})."
        )

    def _format_display_value(self, field_name: str, val: Dict[str, Any], visit_date: Optional[date] = None) -> str:
        if field_name == "entry_fee":
            if val.get("is_free"):
                return "Free Admission (INR 0.00)"
            amt = val.get("amount")
            curr = val.get("currency", "INR")
            tier = val.get("tier_name", "General")
            if amt is not None:
                return f"{curr} {amt:.2f} ({tier})"
            return "Fee Unknown"
        elif field_name == "opening_hours":
            # Check day-of-week closure if visit_date is provided
            if visit_date:
                day_name = visit_date.strftime("%A")
                closed_days = val.get("closed_days", [])
                if day_name in closed_days:
                    return f"CLOSED ({day_name} Weekly Closure)"
            if val.get("opens_at") is None or val.get("closes_at") is None:
                return "Exact opening times unknown" + (f"; closed {', '.join(val.get('closed_days', []))}" if val.get("closed_days") else "")

            opens = val.get("opens_at", "Unknown")
            closes = val.get("closes_at", "Unknown")
            days = val.get("days", "Daily")
            closed_str = f" [Closed: {', '.join(val.get('closed_days', []))}]" if val.get("closed_days") else ""
            return f"{opens} – {closes} ({days}){closed_str}"
        elif field_name == "step_free_access":
            acc = val.get("is_accessible")
            detail = val.get("detail", "")
            return f"Step-Free Access: {'Yes' if acc else 'No'}" + (f" ({detail})" if detail else "")
        elif field_name == "operating_status":
            stat = val.get("status", "OPEN")
            reason = val.get("reason", "")
            return f"Status: {stat}" + (f" - {reason}" if reason else "")
        elif field_name == "typical_duration":
            mins = val.get("duration_minutes")
            if mins is not None:
                return f"Typical Visit: {mins} minutes"
            return "Typical Visit: Unknown"
        return str(val)
