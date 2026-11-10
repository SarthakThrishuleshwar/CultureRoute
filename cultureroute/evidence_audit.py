"""Idempotent review of historical pilot claims; preserves the original rows."""

from __future__ import annotations

from cultureroute.evidence import DEFAULT_EVIDENCE_DB, VenueEvidenceStore
from cultureroute.pilot_evidence import PILOT_RECORDS, seed_pilot_evidence


def audit_legacy_pilot(db_path=DEFAULT_EVIDENCE_DB) -> dict:
    store = VenueEvidenceStore(db_path)
    legacy_ids = {r.evidence_id for r in PILOT_RECORDS}
    retracted = []
    with store._get_connection() as conn:
        rows = conn.execute("SELECT evidence_id,source_url FROM venue_evidence").fetchall()
    for row in rows:
        if row["evidence_id"] in legacy_ids or (row["source_url"] or "").startswith("https://asi.nic.in/circle-"):
            store.retract_evidence(row["evidence_id"],
                "Pilot citation does not directly substantiate this specific value; recheck against a venue notice.")
            retracted.append(row["evidence_id"])
    inserted = seed_pilot_evidence(db_path)
    return {"historical_claims_retracted": len(retracted), "audited_records_inserted": inserted}


if __name__ == "__main__":
    print(audit_legacy_pilot())
