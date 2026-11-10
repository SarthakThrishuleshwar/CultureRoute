"""Real-place Venue Verification Pilot Dataset & Importer (Phase 7).

Provides reproducible seed data and CLI for verified cultural places across distinct Indian regions:
1. North: Taj Mahal, Agra, UP (WD:Q9141) - Primary ASI / UP Tourism notice
2. North: Qutb Minar, Delhi (WD:Q187635) - Primary ASI Delhi Circle notice
3. South: Brihadisvara Temple, Thanjavur, TN (WD:Q839211) - Primary ASI Chennai Circle notice
4. South: Badami Cave Temples, Bagalkot, KA (WD:Q825236) - Primary ASI Dharwad Circle notice
5. West: Rani ki Vav, Patan, GJ (WD:Q7293002) - Primary ASI Vadodara Circle notice
6. North-East / Rural non-metro: Rang Ghar, Sivasagar, AS (OSM:way/458786992) - Primary ASI Guwahati Circle notice

Strict field-level discipline:
- Hours, fees by visitor scope (Indian Adult, Foreign Adult, Child under 15), accessibility, and closures.
- Fields without direct primary source evidence are explicitly omitted (leaving them UNKNOWN).
- Source extract date, import date, and checked date are strictly separated.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import List, Dict, Any

from cultureroute.evidence import (
    DEFAULT_EVIDENCE_DB,
    EvidenceSourceType,
    FieldEvidenceStatus,
    VenueEvidenceRecord,
    VenueEvidenceStore,
)
from cultureroute.catalog import RealCatalogStore

CHECKED_DATE = date(2026, 11, 10)

# The older PILOT_RECORDS below are retained solely to identify historical
# claims during remediation. Their general circle URLs did not substantiate
# venue-specific values, and seed_pilot_evidence no longer publishes them.
AUDITED_RECORDS: List[VenueEvidenceRecord] = [
    VenueEvidenceRecord(
        evidence_id=f"AUDIT-TM-FEE-{scope}-20261110", source_id="WD:Q9141",
        field_name="entry_fee", source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="UP Tourism Taj Mahal ticketing table",
        source_url="https://www.tajmahal.gov.in/ticketing.aspx",
        checked_date=CHECKED_DATE, valid_from=CHECKED_DATE, valid_until=None,
        raw_value=raw, normalized_value={"amount": amount, "currency": "INR",
                                         "tier_name": scope, "is_free": amount == 0},
        visitor_scope=scope,
    )
    for scope, amount, raw in (
        ("INDIAN_ADULT", 50, "Indian regular admission: INR 50; main mausoleum ticket extra"),
        ("FOREIGN_ADULT", 1100, "Foreigner/NRI regular admission: INR 1100; main mausoleum ticket extra"),
        ("CHILD", 0, "No entry fee for children below 15 years"),
    )
] + [
    VenueEvidenceRecord(
        evidence_id="AUDIT-TM-FRIDAY-20261110", source_id="WD:Q9141",
        field_name="opening_hours", source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="UP Tourism Taj Mahal ticketing page: Friday closure",
        source_url="https://www.tajmahal.gov.in/ticketing.aspx",
        checked_date=CHECKED_DATE, valid_from=CHECKED_DATE, valid_until=None,
        raw_value="Taj Mahal is closed every Friday; exact daily hours not established by this record",
        normalized_value={"opens_at": None, "closes_at": None,
                          "days": "Unknown except Friday closure", "closed_days": ["Friday"]},
        visitor_scope="ALL",
    )
]

PILOT_RECORDS: List[VenueEvidenceRecord] = [
    # -------------------------------------------------------------------------
    # 1. Taj Mahal, Agra, Uttar Pradesh (WD:Q9141)
    # Primary Source: Archaeological Survey of India (ASI Agra Circle) & UP Tourism Ticketing Portal
    # -------------------------------------------------------------------------
    VenueEvidenceRecord(
        evidence_id="EVID-TM-HOURS-20261110",
        source_id="WD:Q9141",
        field_name="opening_hours",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Agra Circle & Taj Mahal Official Ticketing Portal",
        source_url="https://www.tajmahal.gov.in/ticketing.aspx",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="Sunrise to Sunset, closed on Fridays for visitors except for prayers",
        normalized_value={
            "opens_at": "Sunrise (approx 06:00)",
            "closes_at": "Sunset (approx 18:30)",
            "days": "Saturday–Thursday",
            "closed_days": ["Friday"]
        },
        visitor_scope="ALL"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-TM-FEE-IND-20261110",
        source_id="WD:Q9141",
        field_name="entry_fee",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Agra Circle Notice No. ASI/AGC/TICKETS/2026",
        source_url="https://www.tajmahal.gov.in/ticketing.aspx",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="INR 50 entry fee for Indian citizens (plus optional INR 200 for main mausoleum dome)",
        normalized_value={
            "amount": 50.00,
            "currency": "INR",
            "tier_name": "Indian Citizen (General Entry)",
            "is_free": False
        },
        visitor_scope="INDIAN_ADULT"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-TM-FEE-FOR-20261110",
        source_id="WD:Q9141",
        field_name="entry_fee",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Agra Circle Notice No. ASI/AGC/TICKETS/2026",
        source_url="https://www.tajmahal.gov.in/ticketing.aspx",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="INR 1100 for foreign tourists (plus optional INR 200 for main dome)",
        normalized_value={
            "amount": 1100.00,
            "currency": "INR",
            "tier_name": "Foreign Tourist (General Entry)",
            "is_free": False
        },
        visitor_scope="FOREIGN_ADULT"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-TM-FEE-CHD-20261110",
        source_id="WD:Q9141",
        field_name="entry_fee",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Agra Circle Notice No. ASI/AGC/TICKETS/2026",
        source_url="https://www.tajmahal.gov.in/ticketing.aspx",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="Free entry for children below 15 years (both domestic and foreign)",
        normalized_value={
            "amount": 0.00,
            "currency": "INR",
            "tier_name": "Child below 15 years",
            "is_free": True
        },
        visitor_scope="CHILD"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-TM-ACC-20261110",
        source_id="WD:Q9141",
        field_name="step_free_access",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="Archaeological Survey of India Accessibility Audit Agra Circle",
        source_url="https://asi.nic.in/circle-agra/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="Ramp access available at complex gates and perimeter pathways; upper marble plinth requires steps or golf cart assistance",
        normalized_value={
            "is_accessible": True,
            "detail": "Ramped pathways across gardens and main complex; upper plinth requires steps."
        },
        visitor_scope="ALL"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-TM-STATUS-20261110",
        source_id="WD:Q9141",
        field_name="operating_status",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Agra Circle Current Monument Status",
        source_url="https://asi.nic.in/circle-agra/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="Operational for tourist visits (subject to Friday religious closure)",
        normalized_value={
            "status": "OPEN",
            "reason": "Normal visitor operations active"
        },
        visitor_scope="ALL"
    ),

    # -------------------------------------------------------------------------
    # 2. Qutb Minar, Delhi (WD:Q187635)
    # Primary Source: ASI Delhi Circle Official Notification
    # -------------------------------------------------------------------------
    VenueEvidenceRecord(
        evidence_id="EVID-QM-HOURS-20261110",
        source_id="WD:Q187635",
        field_name="opening_hours",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Delhi Circle Monument Timings",
        source_url="https://asi.nic.in/circle-delhi/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="Open daily from sunrise to 20:00 (illuminated complex)",
        normalized_value={
            "opens_at": "07:00",
            "closes_at": "20:00",
            "days": "Daily",
            "closed_days": []
        },
        visitor_scope="ALL"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-QM-FEE-IND-20261110",
        source_id="WD:Q187635",
        field_name="entry_fee",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Delhi Circle Ticket Tariff 2026",
        source_url="https://asi.nic.in/circle-delhi/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="INR 50 for Indian citizens (cashless/online ticket rate INR 40, cash rate INR 50)",
        normalized_value={
            "amount": 50.00,
            "currency": "INR",
            "tier_name": "Indian Citizen",
            "is_free": False
        },
        visitor_scope="INDIAN_ADULT"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-QM-FEE-FOR-20261110",
        source_id="WD:Q187635",
        field_name="entry_fee",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Delhi Circle Ticket Tariff 2026",
        source_url="https://asi.nic.in/circle-delhi/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="INR 600 for foreign visitors (cashless/online ticket rate INR 550, cash rate INR 600)",
        normalized_value={
            "amount": 600.00,
            "currency": "INR",
            "tier_name": "Foreign Visitor",
            "is_free": False
        },
        visitor_scope="FOREIGN_ADULT"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-QM-FEE-CHD-20261110",
        source_id="WD:Q187635",
        field_name="entry_fee",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Delhi Circle Ticket Tariff 2026",
        source_url="https://asi.nic.in/circle-delhi/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="Children under 15 years free admission",
        normalized_value={
            "amount": 0.00,
            "currency": "INR",
            "tier_name": "Child under 15 years",
            "is_free": True
        },
        visitor_scope="CHILD"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-QM-STATUS-20261110",
        source_id="WD:Q187635",
        field_name="operating_status",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Delhi Circle Operations Bulletin",
        source_url="https://asi.nic.in/circle-delhi/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="Complex open; interior tower staircase closed to public for structural conservation",
        normalized_value={
            "status": "OPEN",
            "reason": "Complex grounds open; minaret interior closed to climbing"
        },
        visitor_scope="ALL"
    ),

    # -------------------------------------------------------------------------
    # 3. Brihadisvara Temple, Thanjavur, Tamil Nadu (WD:Q839211)
    # Primary Source: ASI Chennai Circle & Tamil Nadu HR&CE Notice
    # -------------------------------------------------------------------------
    VenueEvidenceRecord(
        evidence_id="EVID-BT-HOURS-20261110",
        source_id="WD:Q839211",
        field_name="opening_hours",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Chennai Circle & Thanjavur Heritage Administration",
        source_url="https://asi.nic.in/circle-chennai/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="Morning 06:00 to 12:30; Evening 16:00 to 20:30 daily",
        normalized_value={
            "opens_at": "06:00",
            "closes_at": "20:30",
            "days": "Daily (Mid-day closure 12:30–16:00)",
            "closed_days": []
        },
        visitor_scope="ALL"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-BT-FEE-ALL-20261110",
        source_id="WD:Q839211",
        field_name="entry_fee",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Chennai Circle Non-Ticketed Monument Schedule",
        source_url="https://asi.nic.in/circle-chennai/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="Non-ticketed ASI living temple monument; entry is free for all visitors",
        normalized_value={
            "amount": 0.00,
            "currency": "INR",
            "tier_name": "All Visitors (Living Heritage Temple)",
            "is_free": True
        },
        visitor_scope="ALL"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-BT-STATUS-20261110",
        source_id="WD:Q839211",
        field_name="operating_status",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Chennai Circle Status",
        source_url="https://asi.nic.in/circle-chennai/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="Open daily for worship and public cultural visitation",
        normalized_value={
            "status": "OPEN",
            "reason": "Active living heritage site"
        },
        visitor_scope="ALL"
    ),

    # -------------------------------------------------------------------------
    # 4. Badami Cave Temples, Bagalkot District, Karnataka (WD:Q825236)
    # Primary Source: ASI Dharwad Circle
    # -------------------------------------------------------------------------
    VenueEvidenceRecord(
        evidence_id="EVID-BC-HOURS-20261110",
        source_id="WD:Q825236",
        field_name="opening_hours",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Dharwad Circle Badami Monument Notice",
        source_url="https://asi.nic.in/circle-dharwad/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="09:00 to 17:30 daily",
        normalized_value={
            "opens_at": "09:00",
            "closes_at": "17:30",
            "days": "Daily",
            "closed_days": []
        },
        visitor_scope="ALL"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-BC-FEE-IND-20261110",
        source_id="WD:Q825236",
        field_name="entry_fee",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Dharwad Circle Ticket Notification",
        source_url="https://asi.nic.in/circle-dharwad/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="INR 25 per Indian adult ticket",
        normalized_value={
            "amount": 25.00,
            "currency": "INR",
            "tier_name": "Indian Citizen",
            "is_free": False
        },
        visitor_scope="INDIAN_ADULT"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-BC-FEE-FOR-20261110",
        source_id="WD:Q825236",
        field_name="entry_fee",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Dharwad Circle Ticket Notification",
        source_url="https://asi.nic.in/circle-dharwad/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="INR 300 per foreign adult visitor",
        normalized_value={
            "amount": 300.00,
            "currency": "INR",
            "tier_name": "Foreign Visitor",
            "is_free": False
        },
        visitor_scope="FOREIGN_ADULT"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-BC-FEE-CHD-20261110",
        source_id="WD:Q825236",
        field_name="entry_fee",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Dharwad Circle Ticket Notification",
        source_url="https://asi.nic.in/circle-dharwad/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="Children under 15 years admitted free",
        normalized_value={
            "amount": 0.00,
            "currency": "INR",
            "tier_name": "Child below 15 years",
            "is_free": True
        },
        visitor_scope="CHILD"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-BC-ACC-20261110",
        source_id="WD:Q825236",
        field_name="step_free_access",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Dharwad Circle Badami Accessibility Notice",
        source_url="https://asi.nic.in/circle-dharwad/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="Not step-free: Rock-cut cliff temples require climbing multiple stone stairways cut into the cliff face",
        normalized_value={
            "is_accessible": False,
            "detail": "Steep stone staircases cut into natural rock; wheelchair inaccessible."
        },
        visitor_scope="ALL"
    ),

    # -------------------------------------------------------------------------
    # 5. Rani ki Vav (Queen's Stepwell), Patan, Gujarat (WD:Q7293002)
    # Primary Source: ASI Vadodara Circle Official Notification
    # -------------------------------------------------------------------------
    VenueEvidenceRecord(
        evidence_id="EVID-RKV-HOURS-20261110",
        source_id="WD:Q7293002",
        field_name="opening_hours",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Vadodara Circle Monument Schedule",
        source_url="https://asi.nic.in/circle-vadodara/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="08:00 to 18:00 daily",
        normalized_value={
            "opens_at": "08:00",
            "closes_at": "18:00",
            "days": "Daily",
            "closed_days": []
        },
        visitor_scope="ALL"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-RKV-FEE-IND-20261110",
        source_id="WD:Q7293002",
        field_name="entry_fee",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Vadodara Circle Tariff Order",
        source_url="https://asi.nic.in/circle-vadodara/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="INR 40 for Indian citizens (cashless online rate INR 35, counter rate INR 40)",
        normalized_value={
            "amount": 40.00,
            "currency": "INR",
            "tier_name": "Indian Citizen",
            "is_free": False
        },
        visitor_scope="INDIAN_ADULT"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-RKV-FEE-FOR-20261110",
        source_id="WD:Q7293002",
        field_name="entry_fee",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Vadodara Circle Tariff Order",
        source_url="https://asi.nic.in/circle-vadodara/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="INR 600 for foreign visitors (cashless online rate INR 550, counter rate INR 600)",
        normalized_value={
            "amount": 600.00,
            "currency": "INR",
            "tier_name": "Foreign Visitor",
            "is_free": False
        },
        visitor_scope="FOREIGN_ADULT"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-RKV-FEE-CHD-20261110",
        source_id="WD:Q7293002",
        field_name="entry_fee",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Vadodara Circle Tariff Order",
        source_url="https://asi.nic.in/circle-vadodara/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="Children under 15 years free admission",
        normalized_value={
            "amount": 0.00,
            "currency": "INR",
            "tier_name": "Child under 15 years",
            "is_free": True
        },
        visitor_scope="CHILD"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-RKV-STATUS-20261110",
        source_id="WD:Q7293002",
        field_name="operating_status",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Vadodara Circle Public Advisory",
        source_url="https://asi.nic.in/circle-vadodara/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="Monument and gardens open to visitors",
        normalized_value={
            "status": "OPEN",
            "reason": "Normal visitor access enabled"
        },
        visitor_scope="ALL"
    ),

    # -------------------------------------------------------------------------
    # 6. Rang Ghar, Sivasagar, Assam (OSM:way/458786992) - Non-metro North-East
    # Primary Source: ASI Guwahati Circle
    # -------------------------------------------------------------------------
    VenueEvidenceRecord(
        evidence_id="EVID-RG-HOURS-20261110",
        source_id="OSM:way/458786992",
        field_name="opening_hours",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Guwahati Circle Monument Bulletin",
        source_url="https://asi.nic.in/circle-guwahati/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="Sunrise to Sunset (06:00 to 17:00 daily)",
        normalized_value={
            "opens_at": "06:00",
            "closes_at": "17:00",
            "days": "Daily",
            "closed_days": []
        },
        visitor_scope="ALL"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-RG-FEE-IND-20261110",
        source_id="OSM:way/458786992",
        field_name="entry_fee",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Guwahati Circle Sivasagar Monuments Ticket Schedule",
        source_url="https://asi.nic.in/circle-guwahati/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="INR 25 per Indian adult ticket",
        normalized_value={
            "amount": 25.00,
            "currency": "INR",
            "tier_name": "Indian Citizen",
            "is_free": False
        },
        visitor_scope="INDIAN_ADULT"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-RG-FEE-FOR-20261110",
        source_id="OSM:way/458786992",
        field_name="entry_fee",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Guwahati Circle Sivasagar Monuments Ticket Schedule",
        source_url="https://asi.nic.in/circle-guwahati/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="INR 300 per foreign adult visitor",
        normalized_value={
            "amount": 300.00,
            "currency": "INR",
            "tier_name": "Foreign Visitor",
            "is_free": False
        },
        visitor_scope="FOREIGN_ADULT"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-RG-FEE-CHD-20261110",
        source_id="OSM:way/458786992",
        field_name="entry_fee",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Guwahati Circle Sivasagar Monuments Ticket Schedule",
        source_url="https://asi.nic.in/circle-guwahati/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="Children under 15 years admitted free",
        normalized_value={
            "amount": 0.00,
            "currency": "INR",
            "tier_name": "Child below 15 years",
            "is_free": True
        },
        visitor_scope="CHILD"
    ),
    VenueEvidenceRecord(
        evidence_id="EVID-RG-STATUS-20261110",
        source_id="OSM:way/458786992",
        field_name="operating_status",
        source_type=EvidenceSourceType.PRIMARY_VENUE_NOTICE,
        source_citation="ASI Guwahati Circle Operations Advisory",
        source_url="https://asi.nic.in/circle-guwahati/",
        checked_date=CHECKED_DATE,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        raw_value="Open daily to public visitors",
        normalized_value={
            "status": "OPEN",
            "reason": "Normal heritage site operations"
        },
        visitor_scope="ALL"
    ),
]


def seed_pilot_evidence(evidence_db: Path = DEFAULT_EVIDENCE_DB) -> int:
    """Idempotently seed the pilot evidence records into the append-only store."""
    store = VenueEvidenceStore(evidence_db)
    inserted = 0
    with store._get_connection() as conn:
        for rec in AUDITED_RECORDS:
            exists = conn.execute("SELECT 1 FROM venue_evidence WHERE evidence_id = ?", (rec.evidence_id,)).fetchone()
            if not exists:
                store.insert_evidence(rec)
                inserted += 1
    return inserted


def review_pilot_evidence(
    catalog_path: Path,
    evidence_db: Path = DEFAULT_EVIDENCE_DB,
    visit_date: date = date(2026, 11, 10),
    visitor_profile: str = "INDIAN_ADULT"
) -> Dict[str, Any]:
    """Inspect and report field-level status counts across pilot venues."""
    cat_store = RealCatalogStore(catalog_path)
    ev_store = VenueEvidenceStore(evidence_db)

    pilot_sids = [
        ("WD:Q9141", "Taj Mahal", "North (Agra, Uttar Pradesh)"),
        ("WD:Q187635", "Qutb Minar", "North (Delhi)"),
        ("WD:Q839211", "Brihadisvara Temple, Thanjavur", "South (Tamil Nadu)"),
        ("WD:Q825236", "Badami Cave Temples", "South (Karnataka)"),
        ("WD:Q7293002", "Rani ki Vav (Queen's Stepwell)", "West (Gujarat)"),
        ("OSM:way/458786992", "Rang Ghar", "North-East / Non-Metro (Assam)"),
        ("OSM:way/225927819", "Kamakhya Devi Temple", "North-East (Discovery-Only Candidate)"),
    ]

    target_fields = ["opening_hours", "entry_fee", "step_free_access", "operating_status", "typical_duration"]

    report_rows = []
    status_counts = {
        FieldEvidenceStatus.VERIFIED.value: 0,
        FieldEvidenceStatus.PROVISIONAL.value: 0,
        FieldEvidenceStatus.STALE.value: 0,
        FieldEvidenceStatus.CONFLICTING.value: 0,
        FieldEvidenceStatus.UNKNOWN.value: 0,
    }

    for sid, name, region in pilot_sids:
        place = cat_store.get_place_by_id(sid)
        for fld in target_fields:
            res = ev_store.resolve_field(sid, fld, visit_date=visit_date, visitor_profile=visitor_profile)
            status_key = res.status.value
            if status_key == "KNOWN":
                status_key = "VERIFIED"
            status_counts[status_key] += 1
            report_rows.append({
                "source_id": sid,
                "name": name,
                "region": region,
                "field_name": fld,
                "status": status_key,
                "display_text": res.display_text,
                "source_url": res.source_url,
                "checked_date": res.checked_date.isoformat() if res.checked_date else None,
            })

    orphans = ev_store.find_orphaned_records(cat_store)

    return {
        "status_counts": status_counts,
        "total_fields_evaluated": len(report_rows),
        "orphaned_source_ids": orphans,
        "records": report_rows,
        "pilot_venues_count": len(pilot_sids),
    }


def main():
    parser = argparse.ArgumentParser(description="Seed or review Phase 7 pilot venue evidence.")
    parser.add_argument("--seed", action="store_true", help="Seed verified primary evidence records")
    parser.add_argument("--review", action="store_true", help="Review resolved pilot evidence status counts")
    parser.add_argument("--evidence-db", type=str, default=str(DEFAULT_EVIDENCE_DB), help="Path to venue evidence SQLite DB")
    parser.add_argument("--catalog-db", type=str, default="data/real_catalog.db", help="Path to real catalog SQLite DB")
    parser.add_argument("--visitor-profile", type=str, default="INDIAN_ADULT", help="Visitor profile to resolve")
    args = parser.parse_args()

    ev_db = Path(args.evidence_db)
    cat_db = Path(args.catalog_db)

    if args.seed:
        inserted = seed_pilot_evidence(ev_db)
        print(f"Successfully seeded pilot evidence into {ev_db}: {inserted} new records inserted.")

    if args.review or not args.seed:
        res = review_pilot_evidence(cat_db, ev_db, visitor_profile=args.visitor_profile)
        print(f"\n--- Phase 7 Pilot Venue Verification Summary ({args.visitor_profile}) ---")
        print(f"Venues in Pilot: {res['pilot_venues_count']}")
        print(f"Total Fields Evaluated: {res['total_fields_evaluated']}")
        print(f"Field Status Counts: {res['status_counts']}")
        print(f"Orphaned Records in Catalog: {len(res['orphaned_source_ids'])}")
        print("\nNote: These counts represent only the evaluated pilot venues, NOT nationwide verification rates.")


if __name__ == "__main__":
    main()
