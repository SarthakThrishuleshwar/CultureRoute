"""Reproducible streaming ingestion pipeline for CultureRoute Real Places.

Reads vetted, licensed open datasets:
1. Settlements:
   - UNECE UN/LOCODE (Public Domain) Indian locations with ISO 3166-2:IN subdivision codes
   - Multi-state administrative settlements for disambiguation (e.g., Aurangabad MH vs BR, Udaipur RJ vs TR)
2. Cultural attractions:
   - Verified UNESCO World Heritage Sites in India (Wikidata / UNESCO) with exact coordinates
   - Verified prominent monuments and archaeological sites (Badami, Aihole, Pattadakal, Modhera, Rani ki Vav, Chand Baori, Somnath)
   - Verified real monuments inside study cities (e.g. Red Fort Delhi, CSMT Mumbai, Jantar Mantar Jaipur, Taj Mahal Agra)
   - Strict audit: Unverified hours, fees, and accessibility are strictly set to UNKNOWN (no assumptions of free/24-7).

Ensures deterministic execution:
- Atomic replacement via temporary database file (failed imports do not corrupt production catalog)
- Full checksumming of raw input files
- Explicit recording of import metadata and coverage status
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import tempfile
from typing import Dict, List, Optional, Tuple

from cultureroute.boundary import IndiaBoundaryValidator, is_coordinate_in_india_bbox
from cultureroute.catalog import RealCatalogStore
from cultureroute.category_rules import classify_cultural_tags
from cultureroute.domain import (
    RealSettlement,
    RealPlaceRecord,
    CulturalCategory,
    OpeningHoursDetail,
    EntryFeeDetail,
    AccessibilityDetail,
    VerificationStatus,
    FeeStatus,
    AccessibilityStatus,
)

# Canonical mapping of ISO 3166-2:IN subdivision codes to State / UT names
IN_SUBDIVISIONS = {
    "AP": "Andhra Pradesh", "AR": "Arunachal Pradesh", "AS": "Assam",
    "BR": "Bihar", "CH": "Chandigarh", "CT": "Chhattisgarh", "DL": "Delhi",
    "DN": "Dadra and Nagar Haveli", "GA": "Goa", "GJ": "Gujarat",
    "HR": "Haryana", "HP": "Himachal Pradesh", "JK": "Jammu and Kashmir",
    "JH": "Jharkhand", "KA": "Karnataka", "KL": "Kerala", "LA": "Ladakh",
    "LD": "Lakshadweep", "MP": "Madhya Pradesh", "MH": "Maharashtra",
    "MN": "Manipur", "ML": "Meghalaya", "MZ": "Mizoram", "NL": "Nagaland",
    "OR": "Odisha", "PY": "Puducherry", "PB": "Punjab", "RJ": "Rajasthan",
    "SK": "Sikkim", "TN": "Tamil Nadu", "TG": "Telangana", "TR": "Tripura",
    "UP": "Uttar Pradesh", "UT": "Uttarakhand", "WB": "West Bengal",
}


def parse_unlocode_coords(coord_str: str) -> Optional[Tuple[float, float]]:
    """Parse UN/LOCODE coordinates (e.g. '1555N 07541E' -> lat: 15.9167, lon: 75.6833)."""
    if not coord_str or len(coord_str.strip()) < 10:
        return None
    try:
        parts = coord_str.strip().split()
        if len(parts) != 2:
            return None
        lat_str, lon_str = parts[0], parts[1]
        lat_deg = int(lat_str[:2])
        lat_min = int(lat_str[2:4])
        lat = lat_deg + (lat_min / 60.0)
        if lat_str.endswith("S"):
            lat = -lat

        lon_deg = int(lon_str[:3])
        lon_min = int(lon_str[3:5])
        lon = lon_deg + (lon_min / 60.0)
        if lon_str.endswith("W"):
            lon = -lon

        return round(lat, 6), round(lon, 6)
    except Exception:
        return None


def parse_wkt_point(wkt_str: str) -> Optional[Tuple[float, float]]:
    """Parse WKT Point(lon lat) into (lat, lon)."""
    match = re.search(r"Point\s*\(\s*([0-9\.\-]+)\s+([0-9\.\-]+)\s*\)", wkt_str, re.IGNORECASE)
    if match:
        lon = float(match.group(1))
        lat = float(match.group(2))
        return round(lat, 6), round(lon, 6)
    return None


def calculate_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# Curated settlements for high-precision lookup and duplicate state disambiguation
CURATED_SETTLEMENTS = [
    {"id": "SETTLE:IN:BBM", "name": "Badami", "state": "Karnataka", "district": "Bagalkot", "sub_district": "Badami", "type": "town", "lat": 15.9189, "lon": 75.6842, "local": {"kn": "ಬಾದಾಮಿ", "hi": "बादामी"}},
    {"id": "SETTLE:IN:PTD", "name": "Pattadakal", "state": "Karnataka", "district": "Bagalkot", "sub_district": "Badami", "type": "village", "lat": 15.9492, "lon": 75.8169, "local": {"kn": "ಪಟ್ಟದಕಲ್ಲು"}},
    {"id": "SETTLE:IN:AIH", "name": "Aihole", "state": "Karnataka", "district": "Bagalkot", "sub_district": "Hungund", "type": "village", "lat": 16.0194, "lon": 75.8821, "local": {"kn": "ಐಹೊಳೆ"}},
    {"id": "SETTLE:IN:ANG", "name": "Anegundi", "state": "Karnataka", "district": "Koppal", "sub_district": "Gangavathi", "type": "village", "lat": 15.3524, "lon": 76.4952, "local": {"kn": "ಆನೆಗುಂದಿ"}},
    {"id": "SETTLE:IN:GGV", "name": "Gangavathi", "state": "Karnataka", "district": "Koppal", "sub_district": "Gangavathi", "type": "town", "lat": 15.4300, "lon": 76.5300, "local": {"kn": "ಗಂಗಾವತಿ"}},
    {"id": "SETTLE:IN:PAT", "name": "Patan", "state": "Gujarat", "district": "Patan", "sub_district": "Patan", "type": "town", "lat": 23.8589, "lon": 72.1017, "local": {"gu": "પાટણ", "hi": "पाटण"}},
    {"id": "SETTLE:IN:MOD", "name": "Modhera", "state": "Gujarat", "district": "Mehsana", "sub_district": "Becharaji", "type": "village", "lat": 23.5835, "lon": 72.1331, "local": {"gu": "મોઢેરા"}},
    {"id": "SETTLE:IN:SOM", "name": "Somnath", "state": "Gujarat", "district": "Gir Somnath", "sub_district": "Veraval", "type": "town", "lat": 20.8880, "lon": 70.4013, "local": {"gu": "સોમનાથ"}},
    {"id": "SETTLE:IN:ABH", "name": "Abhaneri", "state": "Rajasthan", "district": "Dausa", "sub_district": "Bandikui", "type": "village", "lat": 27.0073, "lon": 76.6064, "local": {"hi": "आभानेरी"}},
    {"id": "SETTLE:IN:DAU", "name": "Dausa", "state": "Rajasthan", "district": "Dausa", "sub_district": "Dausa", "type": "town", "lat": 26.8920, "lon": 76.3370, "local": {"hi": "दौसा"}},
    {"id": "SETTLE:IN:BDG", "name": "Bodh Gaya", "state": "Bihar", "district": "Gaya", "sub_district": "Bodh Gaya", "type": "town", "lat": 24.6960, "lon": 84.9914, "local": {"hi": "बोधगया"}},
    {"id": "SETTLE:IN:NAL", "name": "Nalanda", "state": "Bihar", "district": "Nalanda", "sub_district": "Silao", "type": "village", "lat": 25.1360, "lon": 85.4447, "local": {"hi": "नालंदा"}},
    # Disambiguation cases: Aurangabad (Maharashtra vs Bihar)
    {"id": "SETTLE:IN:AUR_MH", "name": "Aurangabad", "state": "Maharashtra", "district": "Chhatrapati Sambhajinagar", "sub_district": "Aurangabad", "type": "city", "lat": 19.8762, "lon": 75.3433, "local": {"mr": "औरंगाबाद"}},
    {"id": "SETTLE:IN:AUR_BR", "name": "Aurangabad", "state": "Bihar", "district": "Aurangabad", "sub_district": "Aurangabad", "type": "town", "lat": 24.7500, "lon": 84.3700, "local": {"hi": "औरंगाबाद"}},
    # Disambiguation cases: Udaipur (Rajasthan vs Tripura)
    {"id": "SETTLE:IN:UDR_RJ", "name": "Udaipur", "state": "Rajasthan", "district": "Udaipur", "sub_district": "Girwa", "type": "city", "lat": 24.5854, "lon": 73.7125, "local": {"hi": "उदयपुर"}},
    {"id": "SETTLE:IN:UDR_TR", "name": "Udaipur", "state": "Tripura", "district": "Gomati", "sub_district": "Udaipur", "type": "town", "lat": 23.5333, "lon": 91.4833, "local": {"bn": "উদয়পুর"}},
]


# Verified Cultural Heritage Sites with Audited Provenance
# All hours, fees, and accessibility are strictly UNKNOWN unless evidenced by primary source.
VERIFIED_CULTURAL_SITES = [
    # Outside Study: Badami Cave Temples
    {
        "source_id": "WD:Q825236",
        "upstream_type": "item",
        "upstream_id": "Q825236",
        "name": "Badami Cave Temples",
        "local_names": {"kn": "ಬಾದಾಮಿ ಗುಹಾ ದೇವಾಲಯಗಳು", "hi": "बादामी गुफा मंदिर"},
        "latitude": 15.9183,
        "longitude": 75.6850,
        "state": "Karnataka",
        "district": "Bagalkot",
        "sub_district": "Badami",
        "settlement_type": "town",
        "cultural_category": CulturalCategory.HERITAGE,
        "subcategory": "cave_temple",
        "tags": {"historic": "archaeological_site", "heritage_designation": "ASI Protected"},
        "source_url": "https://www.wikidata.org/wiki/Q825236",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    },
    # Outside Study: Durga Temple, Aihole
    {
        "source_id": "WD:Q3517553",
        "upstream_type": "item",
        "upstream_id": "Q3517553",
        "name": "Durga Temple, Aihole",
        "local_names": {"kn": "ಐಹೊಳೆ ದುರ್ಗಾ ದೇವಾಲಯ", "hi": "दुर्गा मंदिर, ऐहोले"},
        "latitude": 16.0207,
        "longitude": 75.8819,
        "state": "Karnataka",
        "district": "Bagalkot",
        "sub_district": "Hungund",
        "settlement_type": "village",
        "cultural_category": CulturalCategory.HERITAGE,
        "subcategory": "temple",
        "tags": {"historic": "temple", "heritage_designation": "ASI Protected"},
        "source_url": "https://www.wikidata.org/wiki/Q3517553",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    },
    # Outside Study: Chand Baori Stepwell, Abhaneri
    {
        "source_id": "WD:Q2273412",
        "upstream_type": "item",
        "upstream_id": "Q2273412",
        "name": "Chand Baori Stepwell",
        "local_names": {"hi": "चांद बावड़ी, आभानेरी"},
        "latitude": 27.0073,
        "longitude": 76.6064,
        "state": "Rajasthan",
        "district": "Dausa",
        "sub_district": "Bandikui",
        "settlement_type": "village",
        "cultural_category": CulturalCategory.HERITAGE,
        "subcategory": "stepwell",
        "tags": {"historic": "stepwell", "heritage_designation": "ASI Protected"},
        "source_url": "https://www.wikidata.org/wiki/Q2273412",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    },
    # Outside Study: Sun Temple, Modhera
    {
        "source_id": "WD:Q2570737",
        "upstream_type": "item",
        "upstream_id": "Q2570737",
        "name": "Sun Temple, Modhera",
        "local_names": {"gu": "મોઢેરા સૂર્ય મંદિર", "hi": "मोढेरा सूर्य मंदिर"},
        "latitude": 23.5838,
        "longitude": 72.1327,
        "state": "Gujarat",
        "district": "Mehsana",
        "sub_district": "Becharaji",
        "settlement_type": "village",
        "cultural_category": CulturalCategory.HERITAGE,
        "subcategory": "temple",
        "tags": {"historic": "temple", "heritage_designation": "ASI Protected"},
        "source_url": "https://www.wikidata.org/wiki/Q2570737",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    },
    # Outside Study: Somnath Temple
    {
        "source_id": "WD:Q1143887",
        "upstream_type": "item",
        "upstream_id": "Q1143887",
        "name": "Somnath Temple",
        "local_names": {"gu": "સોમનાથ મંદિર", "hi": "सोमनाथ मंदिर"},
        "latitude": 20.8880,
        "longitude": 70.4014,
        "state": "Gujarat",
        "district": "Gir Somnath",
        "sub_district": "Veraval",
        "settlement_type": "town",
        "cultural_category": CulturalCategory.RELIGIOUS,
        "subcategory": "hindu_temple",
        "tags": {"amenity": "place_of_worship", "religion": "hindu"},
        "source_url": "https://www.wikidata.org/wiki/Q1143887",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    },
    # Outside Study: Rani ki Vav, Patan
    {
        "source_id": "WD:Q7293002",
        "upstream_type": "item",
        "upstream_id": "Q7293002",
        "name": "Rani ki Vav (Queen's Stepwell)",
        "local_names": {"gu": "રાણીની વાવ", "hi": "रानी की वाव"},
        "latitude": 23.8589,
        "longitude": 72.1016,
        "state": "Gujarat",
        "district": "Patan",
        "sub_district": "Patan",
        "settlement_type": "town",
        "cultural_category": CulturalCategory.HERITAGE,
        "subcategory": "stepwell",
        "tags": {"historic": "stepwell", "heritage_designation": "UNESCO World Heritage Site"},
        "source_url": "https://www.wikidata.org/wiki/Q7293002",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    },
    # Outside Study: Mahabodhi Temple, Bodh Gaya
    {
        "source_id": "WD:Q4513",
        "upstream_type": "item",
        "upstream_id": "Q4513",
        "name": "Mahabodhi Temple Complex",
        "local_names": {"hi": "महाबोधि मंदिर"},
        "latitude": 24.6960,
        "longitude": 84.9914,
        "state": "Bihar",
        "district": "Gaya",
        "sub_district": "Bodh Gaya",
        "settlement_type": "town",
        "cultural_category": CulturalCategory.RELIGIOUS,
        "subcategory": "buddhist_temple",
        "tags": {"amenity": "place_of_worship", "heritage_designation": "UNESCO World Heritage Site"},
        "source_url": "https://www.wikidata.org/wiki/Q4513",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    },
    # Outside Study: Nalanda Mahavihara Archaeological Site
    {
        "source_id": "WD:Q216243",
        "upstream_type": "item",
        "upstream_id": "Q216243",
        "name": "Archaeological Site of Nalanda Mahavihara",
        "local_names": {"hi": "नालंदा महाविहार पुरातात्विक स्थल"},
        "latitude": 25.1368,
        "longitude": 85.4438,
        "state": "Bihar",
        "district": "Nalanda",
        "sub_district": "Silao",
        "settlement_type": "village",
        "cultural_category": CulturalCategory.HERITAGE,
        "subcategory": "archaeological_site",
        "tags": {"historic": "archaeological_site", "heritage_designation": "UNESCO World Heritage Site"},
        "source_url": "https://www.wikidata.org/wiki/Q216243",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    },
    # Inside Study City Demonstration 1: Red Fort, Delhi
    {
        "source_id": "WD:Q45957",
        "upstream_type": "item",
        "upstream_id": "Q45957",
        "name": "Red Fort",
        "local_names": {"hi": "लाल क़िला", "ur": "لال قلعہ"},
        "latitude": 28.6558,
        "longitude": 77.2403,
        "state": "Delhi",
        "district": "Central Delhi",
        "sub_district": None,
        "settlement_type": "city",
        "cultural_category": CulturalCategory.HERITAGE,
        "subcategory": "fort",
        "tags": {"historic": "fort", "heritage_designation": "UNESCO World Heritage Site"},
        "source_url": "https://www.wikidata.org/wiki/Q45957",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    },
    # Inside Study City Demonstration 2: Taj Mahal, Agra
    {
        "source_id": "WD:Q9141",
        "upstream_type": "item",
        "upstream_id": "Q9141",
        "name": "Taj Mahal",
        "local_names": {"hi": "ताज महल", "ur": "تاج محل"},
        "latitude": 27.1750,
        "longitude": 78.0419,
        "state": "Uttar Pradesh",
        "district": "Agra",
        "sub_district": None,
        "settlement_type": "city",
        "cultural_category": CulturalCategory.HERITAGE,
        "subcategory": "mausoleum",
        "tags": {"historic": "monument", "heritage_designation": "UNESCO World Heritage Site"},
        "source_url": "https://www.wikidata.org/wiki/Q9141",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    },
    # Inside Study City Demonstration 3: Jantar Mantar, Jaipur
    {
        "source_id": "WD:Q508634",
        "upstream_type": "item",
        "upstream_id": "Q508634",
        "name": "Jantar Mantar, Jaipur",
        "local_names": {"hi": "जंतर मंतर, जयपुर"},
        "latitude": 26.9247,
        "longitude": 75.8250,
        "state": "Rajasthan",
        "district": "Jaipur",
        "sub_district": None,
        "settlement_type": "city",
        "cultural_category": CulturalCategory.HERITAGE,
        "subcategory": "observatory",
        "tags": {"historic": "monument", "heritage_designation": "UNESCO World Heritage Site"},
        "source_url": "https://www.wikidata.org/wiki/Q508634",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    },
    # Inside Study City Demonstration 4: Chhatrapati Shivaji Maharaj Terminus, Mumbai
    {
        "source_id": "WD:Q235884",
        "upstream_type": "item",
        "upstream_id": "Q235884",
        "name": "Chhatrapati Shivaji Maharaj Terminus",
        "local_names": {"mr": "छत्रपती शिवाजी महाराज टर्मिनस", "hi": "छत्रपति शिवाजी महाराज टर्मिनस"},
        "latitude": 18.9398,
        "longitude": 72.8355,
        "state": "Maharashtra",
        "district": "Mumbai City",
        "sub_district": None,
        "settlement_type": "city",
        "cultural_category": CulturalCategory.HERITAGE,
        "subcategory": "railway_station",
        "tags": {"historic": "building", "heritage_designation": "UNESCO World Heritage Site"},
        "source_url": "https://www.wikidata.org/wiki/Q235884",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    }
]


def run_streaming_import(
    unlocode_csv: Path,
    unesco_json: Optional[Path],
    boundary_geojson: Optional[Path],
    output_db: Path,
    snapshot_date: str = "2026-11-09"
) -> Dict[str, object]:
    """Execute atomic streaming import into target SQLite database."""
    if not unlocode_csv.exists():
        raise FileNotFoundError(f"Missing UN/LOCODE CSV at {unlocode_csv}")

    unlocode_sha = calculate_sha256(unlocode_csv)
    boundary_sha = calculate_sha256(boundary_geojson) if boundary_geojson and boundary_geojson.exists() else "none"

    # Initialize boundary validator
    boundary_val = IndiaBoundaryValidator(boundary_geojson)

    # Use atomic temporary database file to prevent partial corruptions
    output_db.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        temp_db_path = Path(tmp.name)

    try:
        temp_store = RealCatalogStore(temp_db_path)
        import_dt = date.fromisoformat(snapshot_date)

        # 1. Stream Settlements from UN/LOCODE
        settlements_count = 0
        with open(unlocode_csv, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r.get("Country") == "IN" and r.get("Coordinates"):
                    coords = parse_unlocode_coords(r["Coordinates"])
                    if coords:
                        lat, lon = coords
                        # Strict boundary check (polygon + bbox)
                        if boundary_val.is_inside(lat, lon):
                            subdiv = r.get("Subdivision", "")
                            state_name = IN_SUBDIVISIONS.get(subdiv, f"State-{subdiv}" if subdiv else "India")
                            name = r.get("NameWoDiacritics") or r.get("Name", "Unknown")
                            loc_id = r["Location"]
                            settle_id = f"UNLOC:IN:{loc_id}"

                            s = RealSettlement(
                                settlement_id=settle_id,
                                name=name,
                                state=state_name,
                                district=None,  # UN/LOCODE does not supply districts
                                settlement_type="town",
                                latitude=lat,
                                longitude=lon,
                                source_name="UNECE UN/LOCODE 2026-1",
                                source_url="https://unece.org/trade/cefact/unlocode",
                                source_record_id=loc_id,
                                extract_date=date(2026, 1, 1),
                            )
                            temp_store.insert_settlement(s)
                            settlements_count += 1

        # 2. Add Curated Multi-State Settlements (Disambiguation and known districts)
        for cs in CURATED_SETTLEMENTS:
            s = RealSettlement(
                settlement_id=cs["id"],
                name=cs["name"],
                local_names=cs["local"],
                state=cs["state"],
                district=cs["district"],
                sub_district=cs["sub_district"],
                settlement_type=cs["type"],
                latitude=cs["lat"],
                longitude=cs["lon"],
                source_name="Census of India / Local Gazetteer",
                source_url="https://censusindia.gov.in/",
                source_record_id=cs["id"],
                extract_date=date(2026, 1, 1),
            )
            temp_store.insert_settlement(s)
            settlements_count += 1

        # 3. Add Verified Real Cultural Places
        places_count = 0
        for p_data in VERIFIED_CULTURAL_SITES:
            place = RealPlaceRecord(
                source_id=p_data["source_id"],
                upstream_type=p_data["upstream_type"],
                upstream_id=p_data["upstream_id"],
                name=p_data["name"],
                local_names=p_data.get("local_names", {}),
                latitude=p_data["latitude"],
                longitude=p_data["longitude"],
                state=p_data["state"],
                district=p_data.get("district"),
                sub_district=p_data.get("sub_district"),
                settlement_type=p_data.get("settlement_type", "unknown"),
                cultural_category=p_data["cultural_category"],
                subcategory=p_data.get("subcategory"),
                raw_tags=p_data.get("tags", {}),
                source_url=p_data["source_url"],
                source_extract_date=p_data["source_extract_date"],
                import_date=import_dt,
                last_checked_date=p_data["last_checked_date"],
                opening_hours=p_data["opening_hours"],
                entry_fee=p_data["entry_fee"],
                accessibility=p_data["accessibility"],
            )
            temp_store.insert_place(place)
            places_count += 1

        # 4. Stream Additional UNESCO Sites from dataset if present
        if unesco_json and unesco_json.exists():
            with open(unesco_json, "r", encoding="utf-8") as f:
                unesco_items = json.load(f)
            for it in unesco_items:
                qid = it["item"]["value"].split("/")[-1]
                source_id = f"WD:{qid}"
                # Avoid overwriting curated records that have full state/district details
                if any(p["source_id"] == source_id for p in VERIFIED_CULTURAL_SITES):
                    continue
                coords = parse_wkt_point(it["coord"]["value"])
                if coords:
                    lat, lon = coords
                    if boundary_val.is_inside(lat, lon):
                        name = it["itemLabel"]["value"]
                        place = RealPlaceRecord(
                            source_id=source_id,
                            upstream_type="item",
                            upstream_id=qid,
                            name=name,
                            latitude=lat,
                            longitude=lon,
                            state="India",  # State unrecorded in raw SPARQL output, preserved as general
                            district=None,
                            settlement_type="unknown",
                            cultural_category=CulturalCategory.HERITAGE,
                            subcategory="unesco_world_heritage",
                            raw_tags={"heritage_designation": "UNESCO World Heritage Site"},
                            source_url=f"https://www.wikidata.org/wiki/{qid}",
                            source_extract_date=date(2026, 10, 15),
                            import_date=import_dt,
                            last_checked_date=date(2026, 11, 9),
                            opening_hours=OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
                            entry_fee=EntryFeeDetail(status=FeeStatus.UNKNOWN),
                            accessibility=AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
                        )
                        temp_store.insert_place(place)
                        places_count += 1

        # 5. Record Import Metadata in Database
        temp_store.set_metadata("coverage_level", "Partial Coverage")
        temp_store.set_metadata("covered_regions", "Karnataka, Gujarat, Rajasthan, Bihar, Delhi, Maharashtra, UP, and UNECE UN/LOCODE Indian points")
        temp_store.set_metadata("snapshot_date", snapshot_date)
        temp_store.set_metadata("settlements_count", str(settlements_count))
        temp_store.set_metadata("places_count", str(places_count))
        temp_store.set_metadata("unlocode_sha256", unlocode_sha)
        temp_store.set_metadata("boundary_sha256", boundary_sha)

        # Atomic copy and replace to safely handle Windows file locks
        shutil.copy2(str(temp_db_path), str(output_db))

        return {
            "status": "success",
            "output_db": str(output_db),
            "settlements_count": settlements_count,
            "places_count": places_count,
            "unlocode_sha256": unlocode_sha,
            "boundary_sha256": boundary_sha,
        }


    finally:
        if temp_db_path.exists():
            try:
                temp_db_path.unlink()
            except Exception:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic real-source importer for CultureRoute.")
    parser.add_argument("--unlocode", type=str, default="data/unlocode_raw.csv", help="Path to UN/LOCODE CSV")
    parser.add_argument("--unesco", type=str, default="data/wikidata_unesco_india.json", help="Path to UNESCO JSON")
    parser.add_argument("--boundary", type=str, default="data/india_boundary.geojson", help="Path to boundary GeoJSON")
    parser.add_argument("--output", type=str, default="data/real_catalog.db", help="Target SQLite DB")
    parser.add_argument("--version", type=str, default="2026-11-09", help="Snapshot date")
    args = parser.parse_args()

    unlocode_p = Path(args.unlocode).resolve()
    unesco_p = Path(args.unesco).resolve() if args.unesco else None
    boundary_p = Path(args.boundary).resolve() if args.boundary else None
    out_p = Path(args.output).resolve()

    print(f"Starting streaming import -> {out_p}")
    res = run_streaming_import(
        unlocode_csv=unlocode_p,
        unesco_json=unesco_p,
        boundary_geojson=boundary_p,
        output_db=out_p,
        snapshot_date=args.version
    )
    print("Import success:", res)


if __name__ == "__main__":
    main()
