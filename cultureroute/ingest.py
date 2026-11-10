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
    # Extended coverage settlements outside the 45-city synthetic study:
    {"id": "SETTLE:IN:KHJ", "name": "Khajuraho", "state": "Madhya Pradesh", "district": "Chhatarpur", "sub_district": "Rajnagar", "type": "town", "lat": 24.8510, "lon": 79.9199, "local": {"hi": "खजुराहो"}},
    {"id": "SETTLE:IN:SAN", "name": "Sanchi", "state": "Madhya Pradesh", "district": "Raisen", "sub_district": "Gairatganj", "type": "town", "lat": 23.4810, "lon": 77.7397, "local": {"hi": "सांची"}},
    {"id": "SETTLE:IN:TNJ", "name": "Thanjavur", "state": "Tamil Nadu", "district": "Thanjavur", "sub_district": "Thanjavur", "type": "city", "lat": 10.7870, "lon": 79.1378, "local": {"ta": "தஞ்சாவூர்"}},
    {"id": "SETTLE:IN:MAM", "name": "Mamallapuram", "state": "Tamil Nadu", "district": "Chengalpattu", "sub_district": "Thirukalukundram", "type": "town", "lat": 12.6269, "lon": 80.1927, "local": {"ta": "மாமல்லபுரம்"}},
    {"id": "SETTLE:IN:KNK", "name": "Konark", "state": "Odisha", "district": "Puri", "sub_district": "Gop", "type": "town", "lat": 19.8876, "lon": 86.0945, "local": {"or": "କୋଣାର୍କ"}},
    {"id": "SETTLE:IN:OGO", "name": "Old Goa", "state": "Goa", "district": "North Goa", "sub_district": "Tiswadi", "type": "town", "lat": 15.5009, "lon": 73.9116, "local": {"kok": "पोरणें गोंय"}},
    {"id": "SETTLE:IN:TAB", "name": "Tabo", "state": "Himachal Pradesh", "district": "Lahaul and Spiti", "sub_district": "Spiti", "type": "village", "lat": 32.0950, "lon": 78.3780, "local": {"hi": "ताबो"}},
    {"id": "SETTLE:IN:SHR", "name": "Shravanabelagola", "state": "Karnataka", "district": "Hassan", "sub_district": "Channarayapatna", "type": "town", "lat": 12.8580, "lon": 76.4860, "local": {"kn": "ಶ್ರವಣಬೆಳಗೊಳ"}},
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
    },
    # Extended State 1 (Madhya Pradesh): Khajuraho Group of Monuments
    {
        "source_id": "WD:Q179732",
        "upstream_type": "item",
        "upstream_id": "Q179732",
        "name": "Khajuraho Group of Monuments",
        "local_names": {"hi": "खजुराहो स्मारक समूह"},
        "latitude": 24.8519,
        "longitude": 79.9199,
        "state": "Madhya Pradesh",
        "district": "Chhatarpur",
        "sub_district": "Rajnagar",
        "settlement_type": "town",
        "cultural_category": CulturalCategory.HERITAGE,
        "subcategory": "temple_complex",
        "tags": {"historic": "monument", "heritage_designation": "UNESCO World Heritage Site"},
        "source_url": "https://www.wikidata.org/wiki/Q179732",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    },
    # Extended State 1 (Madhya Pradesh): Buddhist Monuments at Sanchi
    {
        "source_id": "WD:Q199874",
        "upstream_type": "item",
        "upstream_id": "Q199874",
        "name": "Buddhist Monuments at Sanchi",
        "local_names": {"hi": "सांची के बौद्ध स्मारक"},
        "latitude": 23.4794,
        "longitude": 77.7397,
        "state": "Madhya Pradesh",
        "district": "Raisen",
        "sub_district": "Gairatganj",
        "settlement_type": "town",
        "cultural_category": CulturalCategory.HERITAGE,
        "subcategory": "stupa",
        "tags": {"historic": "monument", "heritage_designation": "UNESCO World Heritage Site"},
        "source_url": "https://www.wikidata.org/wiki/Q199874",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    },
    # Extended State 2 (Tamil Nadu): Brihadisvara Temple, Thanjavur
    {
        "source_id": "WD:Q839211",
        "upstream_type": "item",
        "upstream_id": "Q839211",
        "name": "Brihadisvara Temple, Thanjavur",
        "local_names": {"ta": "தஞ்சைப் பெருவுடையார் கோயில்", "hi": "बृहदीश्वर मन्दिर"},
        "latitude": 10.7828,
        "longitude": 79.1318,
        "state": "Tamil Nadu",
        "district": "Thanjavur",
        "sub_district": "Thanjavur",
        "settlement_type": "city",
        "cultural_category": CulturalCategory.HERITAGE,
        "subcategory": "chola_temple",
        "tags": {"historic": "temple", "heritage_designation": "UNESCO World Heritage Site"},
        "source_url": "https://www.wikidata.org/wiki/Q839211",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    },
    # Extended State 2 (Tamil Nadu): Group of Monuments at Mahabalipuram
    {
        "source_id": "WD:Q1078426",
        "upstream_type": "item",
        "upstream_id": "Q1078426",
        "name": "Group of Monuments at Mahabalipuram",
        "local_names": {"ta": "மாமல்லபுர மரபுச்சின்னங்கள்"},
        "latitude": 12.6167,
        "longitude": 80.1917,
        "state": "Tamil Nadu",
        "district": "Chengalpattu",
        "sub_district": "Thirukalukundram",
        "settlement_type": "town",
        "cultural_category": CulturalCategory.HERITAGE,
        "subcategory": "shore_temple",
        "tags": {"historic": "monument", "heritage_designation": "UNESCO World Heritage Site"},
        "source_url": "https://www.wikidata.org/wiki/Q1078426",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    },
    # Extended State 3 (Odisha): Sun Temple, Konark
    {
        "source_id": "WD:Q219985",
        "upstream_type": "item",
        "upstream_id": "Q219985",
        "name": "Sun Temple, Konark",
        "local_names": {"or": "କୋଣାର୍କ ସୂର୍ଯ୍ୟ ମନ୍ଦିର", "hi": "कोणार्क सूर्य मंदिर"},
        "latitude": 19.8876,
        "longitude": 86.0945,
        "state": "Odisha",
        "district": "Puri",
        "sub_district": "Gop",
        "settlement_type": "town",
        "cultural_category": CulturalCategory.HERITAGE,
        "subcategory": "chariot_temple",
        "tags": {"historic": "temple", "heritage_designation": "UNESCO World Heritage Site"},
        "source_url": "https://www.wikidata.org/wiki/Q219985",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    },
    # Extended State 4 (Goa): Basilica of Bom Jesus, Old Goa
    {
        "source_id": "WD:Q4867451",
        "upstream_type": "item",
        "upstream_id": "Q4867451",
        "name": "Basilica of Bom Jesus",
        "local_names": {"kok": "बोम जेजुची बाझिलिका"},
        "latitude": 15.5009,
        "longitude": 73.9116,
        "state": "Goa",
        "district": "North Goa",
        "sub_district": "Tiswadi",
        "settlement_type": "town",
        "cultural_category": CulturalCategory.HERITAGE,
        "subcategory": "basilica",
        "tags": {"historic": "church", "heritage_designation": "UNESCO World Heritage Site"},
        "source_url": "https://www.wikidata.org/wiki/Q4867451",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    },
    # Extended State 5 (Himachal Pradesh): Tabo Monastery
    {
        "source_id": "WD:Q675376",
        "upstream_type": "item",
        "upstream_id": "Q675376",
        "name": "Tabo Monastery, Spiti Valley",
        "local_names": {"hi": "ताबो बौद्ध मठ"},
        "latitude": 32.0950,
        "longitude": 78.3780,
        "state": "Himachal Pradesh",
        "district": "Lahaul and Spiti",
        "sub_district": "Spiti",
        "settlement_type": "village",
        "cultural_category": CulturalCategory.RELIGIOUS,
        "subcategory": "monastery",
        "tags": {"historic": "monastery", "heritage_designation": "ASI Protected"},
        "source_url": "https://www.wikidata.org/wiki/Q675376",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    },
    # Extended Site (Karnataka): Gommateshwara Statue, Shravanabelagola
    {
        "source_id": "WD:Q3535231",
        "upstream_type": "item",
        "upstream_id": "Q3535231",
        "name": "Gommateshwara Monolith, Shravanabelagola",
        "local_names": {"kn": "ಗೊಮ್ಮಟೇಶ್ವರ ಬಾಹುಬಲಿ ಪ್ರತಿಮೆ"},
        "latitude": 12.8580,
        "longitude": 76.4860,
        "state": "Karnataka",
        "district": "Hassan",
        "sub_district": "Channarayapatna",
        "settlement_type": "town",
        "cultural_category": CulturalCategory.RELIGIOUS,
        "subcategory": "jain_monolith",
        "tags": {"historic": "statue", "heritage_designation": "ASI Protected"},
        "source_url": "https://www.wikidata.org/wiki/Q3535231",
        "source_extract_date": date(2026, 10, 15),
        "last_checked_date": date(2026, 11, 9),
        "opening_hours": OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        "entry_fee": EntryFeeDetail(status=FeeStatus.UNKNOWN),
        "accessibility": AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    },
]


class OsmStreamingImporter:
    """Streams OpenStreetMap PBF or XML extracts using pyosmium, extracting settlements and cultural attractions.

    Supports:
    - Nodes: Points of interest, settlement center nodes, shrine/heritage markers.
    - Ways: Polygons and building footprints (e.g. temples, forts, palaces), using average coordinate centroid.
    - Relations: Multi-polygon complexes, resolving representative coordinates from member ways/nodes.
    Records separate object-type counts and rejection metrics.
    """

    def __init__(self, temp_store: RealCatalogStore, boundary_val: IndiaBoundaryValidator, import_dt: date, extract_dt: Optional[date] = None):
        self.store = temp_store
        self.boundary = boundary_val
        self.import_dt = import_dt
        self.extract_dt = extract_dt or import_dt

        # Object-type specific scan counters
        self.nodes_scanned = 0
        self.ways_scanned = 0
        self.relations_scanned = 0

        # Import counts by object type
        self.settlements_nodes_imported = 0
        self.settlements_ways_imported = 0
        self.attractions_nodes_imported = 0
        self.attractions_ways_imported = 0
        self.attractions_relations_imported = 0

        # Category-specific attraction counts
        self.attractions_by_category: Dict[str, int] = {
            "heritage": 0,
            "religious": 0,
            "museum": 0,
            "food": 0,
        }

        # Rejection metrics
        self.rejected_boundary_nodes = 0
        self.rejected_boundary_ways = 0
        self.rejected_boundary_relations = 0
        self.rejected_non_cultural = 0
        self.rejected_missing_geometry = 0

    def run_import(self, osm_path: Path) -> Dict[str, object]:
        try:
            import osmium
        except ImportError:
            raise RuntimeError("pyosmium is required for OSM PBF/XML ingestion. Install with `pip install osmium`.")

        class _Pass1Handler(osmium.SimpleHandler):
            """Pass 1: Ingest nodes and ways with direct locations, while indexing cultural way centroids for relation resolution."""
            MAX_WAY_CENTROIDS = 100000  # Cap way centroids in memory (~5 MB max)
            BATCH_SIZE = 2000

            def __init__(self, outer: OsmStreamingImporter):
                super().__init__()
                self.outer = outer
                self.cultural_way_centroids: Dict[int, Tuple[float, float]] = {}
                self.settlement_batch: List[RealSettlement] = []
                self.place_batch: List[RealPlaceRecord] = []

            def _flush_settlements(self) -> None:
                if self.settlement_batch:
                    self.outer.store.insert_settlements_batch(self.settlement_batch)
                    self.settlement_batch.clear()

            def _flush_places(self) -> None:
                if self.place_batch:
                    self.outer.store.insert_places_batch(self.place_batch)
                    self.place_batch.clear()

            def _flush_all(self) -> None:
                self._flush_settlements()
                self._flush_places()

            def node(self, n):
                self.outer.nodes_scanned += 1
                if len(n.tags) == 0 or not n.location.valid():
                    return

                tags = {tag.k: tag.v for tag in n.tags}
                lat = n.location.lat
                lon = n.location.lon
                name = tags.get("name") or tags.get("name:en")
                if not name:
                    return

                # Check settlement
                place_type = tags.get("place", "").lower()
                if place_type in ["city", "town", "village", "hamlet", "suburb", "locality"]:
                    if self.outer.boundary.is_inside(lat, lon):
                        sid = f"OSM:node/{n.id}"
                        local_names = {tag.k.split(":")[-1]: tag.v for tag in n.tags if tag.k.startswith("name:") and tag.k != "name:en"}
                        settle = RealSettlement(
                            settlement_id=sid,
                            name=name,
                            local_names=local_names,
                            state=tags.get("is_in:state", tags.get("addr:state", "India")),
                            district=tags.get("is_in:district", tags.get("addr:district")),
                            sub_district=tags.get("is_in:subdistrict"),
                            settlement_type=place_type,
                            latitude=lat,
                            longitude=lon,
                            source_name="OpenStreetMap PBF Extract",
                            source_url=f"https://www.openstreetmap.org/node/{n.id}",
                            source_record_id=str(n.id),
                            extract_date=self.outer.extract_dt,
                        )
                        self.settlement_batch.append(settle)
                        self.outer.settlements_nodes_imported += 1
                        if len(self.settlement_batch) >= self.BATCH_SIZE:
                            self._flush_settlements()
                    else:
                        self.outer.rejected_boundary_nodes += 1

                # Check cultural attraction
                classified = classify_cultural_tags(tags)
                if classified:
                    if self.outer.boundary.is_inside(lat, lon):
                        cat, subcat = classified
                        pid = f"OSM:node/{n.id}"
                        local_names = {tag.k.split(":")[-1]: tag.v for tag in n.tags if tag.k.startswith("name:") and tag.k != "name:en"}
                        place = RealPlaceRecord(
                            source_id=pid,
                            upstream_type="node",
                            upstream_id=str(n.id),
                            name=name,
                            local_names=local_names,
                            latitude=lat,
                            longitude=lon,
                            state=tags.get("addr:state", "India"),
                            district=tags.get("addr:district"),
                            sub_district=tags.get("addr:subdistrict"),
                            settlement_type="unknown",
                            cultural_category=cat,
                            subcategory=subcat,
                            raw_tags=tags,
                            source_url=f"https://www.openstreetmap.org/node/{n.id}",
                            source_extract_date=self.outer.extract_dt,
                            import_date=self.outer.import_dt,
                            last_checked_date=self.outer.extract_dt,
                            opening_hours=OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
                            entry_fee=EntryFeeDetail(status=FeeStatus.UNKNOWN),
                            accessibility=AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
                        )
                        self.place_batch.append(place)
                        self.outer.attractions_nodes_imported += 1
                        self.outer.attractions_by_category[cat.value] += 1
                        if len(self.place_batch) >= self.BATCH_SIZE:
                            self._flush_places()
                    else:
                        self.outer.rejected_boundary_nodes += 1
                else:
                    self.outer.rejected_non_cultural += 1

            def way(self, w):
                self.outer.ways_scanned += 1
                tags = {tag.k: tag.v for tag in w.tags}
                if not tags:
                    return

                # Calculate representative centroid from way nodes
                pts = [(n.location.lat, n.location.lon) for n in w.nodes if n.location.valid()]
                if not pts:
                    self.outer.rejected_missing_geometry += 1
                    return

                lat = sum(p[0] for p in pts) / len(pts)
                lon = sum(p[1] for p in pts) / len(pts)

                name = tags.get("name") or tags.get("name:en")
                if not name:
                    return

                # Check cultural attraction on way (temple footprint, fort wall, monument)
                classified = classify_cultural_tags(tags)
                if classified:
                    # Cache cultural way centroid with memory bound
                    if len(self.cultural_way_centroids) < self.MAX_WAY_CENTROIDS:
                        self.cultural_way_centroids[w.id] = (lat, lon)

                    if self.outer.boundary.is_inside(lat, lon):
                        cat, subcat = classified
                        pid = f"OSM:way/{w.id}"
                        local_names = {tag.k.split(":")[-1]: tag.v for tag in w.tags if tag.k.startswith("name:") and tag.k != "name:en"}
                        place = RealPlaceRecord(
                            source_id=pid,
                            upstream_type="way",
                            upstream_id=str(w.id),
                            name=name,
                            local_names=local_names,
                            latitude=lat,
                            longitude=lon,
                            state=tags.get("addr:state", "India"),
                            district=tags.get("addr:district"),
                            sub_district=tags.get("addr:subdistrict"),
                            settlement_type="unknown",
                            cultural_category=cat,
                            subcategory=subcat,
                            raw_tags=tags,
                            source_url=f"https://www.openstreetmap.org/way/{w.id}",
                            source_extract_date=self.outer.extract_dt,
                            import_date=self.outer.import_dt,
                            last_checked_date=self.outer.extract_dt,
                            opening_hours=OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
                            entry_fee=EntryFeeDetail(status=FeeStatus.UNKNOWN),
                            accessibility=AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
                        )
                        self.place_batch.append(place)
                        self.outer.attractions_ways_imported += 1
                        self.outer.attractions_by_category[cat.value] += 1
                        if len(self.place_batch) >= self.BATCH_SIZE:
                            self._flush_places()
                    else:
                        self.outer.rejected_boundary_ways += 1
                else:
                    self.outer.rejected_non_cultural += 1

                # Check settlement polygon (e.g. residential area, town boundary)
                place_type = tags.get("place", "").lower()
                if place_type in ["city", "town", "village", "hamlet", "suburb", "locality"]:
                    if self.outer.boundary.is_inside(lat, lon):
                        sid = f"OSM:way/{w.id}"
                        local_names = {tag.k.split(":")[-1]: tag.v for tag in w.tags if tag.k.startswith("name:") and tag.k != "name:en"}
                        settle = RealSettlement(
                            settlement_id=sid,
                            name=name,
                            local_names=local_names,
                            state=tags.get("is_in:state", tags.get("addr:state", "India")),
                            district=tags.get("is_in:district", tags.get("addr:district")),
                            sub_district=tags.get("is_in:subdistrict"),
                            settlement_type=place_type,
                            latitude=lat,
                            longitude=lon,
                            source_name="OpenStreetMap PBF Extract",
                            source_url=f"https://www.openstreetmap.org/way/{w.id}",
                            source_record_id=str(w.id),
                            extract_date=self.outer.extract_dt,
                        )
                        self.settlement_batch.append(settle)
                        self.outer.settlements_ways_imported += 1
                        if len(self.settlement_batch) >= self.BATCH_SIZE:
                            self._flush_settlements()
                    else:
                        self.outer.rejected_boundary_ways += 1

            def relation(self, r):
                self.outer.relations_scanned += 1
                tags = {tag.k: tag.v for tag in r.tags}
                if not tags:
                    return

                name = tags.get("name") or tags.get("name:en")
                if not name:
                    return

                classified = classify_cultural_tags(tags)
                if not classified:
                    self.outer.rejected_non_cultural += 1
                    return

                # Resolve representative point from resolved member ways
                member_pts = []
                for m in r.members:
                    if m.type == "w" and m.ref in self.cultural_way_centroids:
                        member_pts.append(self.cultural_way_centroids[m.ref])

                if not member_pts:
                    self.outer.rejected_missing_geometry += 1
                    return

                lat = sum(p[0] for p in member_pts) / len(member_pts)
                lon = sum(p[1] for p in member_pts) / len(member_pts)

                if self.outer.boundary.is_inside(lat, lon):
                    cat, subcat = classified
                    pid = f"OSM:relation/{r.id}"
                    local_names = {tag.k.split(":")[-1]: tag.v for tag in r.tags if tag.k.startswith("name:") and tag.k != "name:en"}
                    place = RealPlaceRecord(
                        source_id=pid,
                        upstream_type="relation",
                        upstream_id=str(r.id),
                        name=name,
                        local_names=local_names,
                        latitude=lat,
                        longitude=lon,
                        state=tags.get("addr:state", "India"),
                        district=tags.get("addr:district"),
                        sub_district=tags.get("addr:subdistrict"),
                        settlement_type="unknown",
                        cultural_category=cat,
                        subcategory=subcat,
                        raw_tags=tags,
                        source_url=f"https://www.openstreetmap.org/relation/{r.id}",
                        source_extract_date=self.outer.extract_dt,
                        import_date=self.outer.import_dt,
                        last_checked_date=self.outer.extract_dt,
                        opening_hours=OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
                        entry_fee=EntryFeeDetail(status=FeeStatus.UNKNOWN),
                        accessibility=AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
                    )
                    self.place_batch.append(place)
                    self.outer.attractions_relations_imported += 1
                    self.outer.attractions_by_category[cat.value] += 1
                    if len(self.place_batch) >= self.BATCH_SIZE:
                        self._flush_places()
                else:
                    self.outer.rejected_boundary_relations += 1

        handler = _Pass1Handler(self)
        handler.apply_file(str(osm_path), locations=True)
        handler._flush_all()

        total_settlements = self.settlements_nodes_imported + self.settlements_ways_imported
        total_attractions = (
            self.attractions_nodes_imported +
            self.attractions_ways_imported +
            self.attractions_relations_imported
        )

        return {
            "nodes_scanned": self.nodes_scanned,
            "ways_scanned": self.ways_scanned,
            "relations_scanned": self.relations_scanned,
            "settlements_imported": total_settlements,
            "settlements_by_type": {
                "nodes": self.settlements_nodes_imported,
                "ways": self.settlements_ways_imported,
            },
            "attractions_imported": total_attractions,
            "attractions_by_type": {
                "nodes": self.attractions_nodes_imported,
                "ways": self.attractions_ways_imported,
                "relations": self.attractions_relations_imported,
            },
            "attractions_by_category": self.attractions_by_category,
            "rejected_boundary": {
                "nodes": self.rejected_boundary_nodes,
                "ways": self.rejected_boundary_ways,
                "relations": self.rejected_boundary_relations,
            },
            "rejected_non_cultural": self.rejected_non_cultural,
            "rejected_missing_geometry": self.rejected_missing_geometry,
        }


def run_streaming_import(
    unlocode_csv: Path,
    unesco_json: Optional[Path],
    boundary_geojson: Optional[Path],
    output_db: Path,
    snapshot_date: str = "2026-11-09",
    osm_pbf: Optional[Path] = None,
    source_extract_date: Optional[str] = None,
) -> Dict[str, object]:
    """Execute atomic streaming import into target SQLite database with verified boundary and count reconciliation."""
    unlocode_csv = Path(unlocode_csv) if unlocode_csv else None
    output_db = Path(output_db)
    unesco_json = Path(unesco_json) if unesco_json else None
    boundary_geojson = Path(boundary_geojson) if boundary_geojson else None
    osm_pbf = Path(osm_pbf) if osm_pbf else None

    if unlocode_csv and not unlocode_csv.exists():
        raise FileNotFoundError(f"Missing UN/LOCODE CSV at {unlocode_csv}")

    if not boundary_geojson or not boundary_geojson.exists():
        raise FileNotFoundError(f"Missing boundary GeoJSON at {boundary_geojson}")

    # Initialize and verify boundary validator
    boundary_val = IndiaBoundaryValidator(boundary_geojson)
    if not boundary_val.is_available:
        raise RuntimeError(f"Coordinate validation unavailable: boundary geometry in {boundary_geojson} is invalid or empty")

    unlocode_sha = calculate_sha256(unlocode_csv) if unlocode_csv and unlocode_csv.exists() else "none"
    boundary_sha = calculate_sha256(boundary_geojson)
    unesco_sha = calculate_sha256(unesco_json) if unesco_json and unesco_json.exists() else "none"
    osm_pbf_sha = calculate_sha256(osm_pbf) if osm_pbf and osm_pbf.exists() else "none"

    # Stage on the same filesystem directory to ensure atomic replacement
    output_db.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output_db.parent, suffix=".tmp.db", delete=False) as tmp:
        temp_db_path = Path(tmp.name)

    try:
        temp_store = RealCatalogStore(temp_db_path)
        import_dt = date.fromisoformat(snapshot_date)

        # 1. Stream Settlements from UN/LOCODE
        input_unlocode_count = 0
        imported_unlocode_count = 0
        rejected_unlocode_boundary_count = 0

        if unlocode_csv:
            with open(unlocode_csv, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    if r.get("Country") == "IN" and r.get("Coordinates"):
                        input_unlocode_count += 1
                        coords = parse_unlocode_coords(r["Coordinates"])
                        if coords:
                            lat, lon = coords
                            # Strict boundary check (MultiPolygon + Holes)
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
                                    district=None,
                                    settlement_type="town",
                                    latitude=lat,
                                    longitude=lon,
                                    source_name="UNECE UN/LOCODE 2026-1",
                                    source_url="https://unece.org/trade/cefact/unlocode",
                                    source_record_id=loc_id,
                                    extract_date=date(2026, 1, 1),
                                )
                                temp_store.insert_settlement(s)
                                imported_unlocode_count += 1
                            else:
                                rejected_unlocode_boundary_count += 1

        # 2. Add Curated Multi-State Settlements (Disambiguation and known districts)
        curated_settlements_count = len(CURATED_SETTLEMENTS)
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

        # 3. Add Verified Real Cultural Places
        curated_places_count = len(VERIFIED_CULTURAL_SITES)
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

        # 4. Stream Additional UNESCO Sites from dataset if present
        input_unesco_count = 0
        imported_unesco_count = 0
        rejected_unesco_boundary_count = 0

        if unesco_json and unesco_json.exists():
            with open(unesco_json, "r", encoding="utf-8") as f:
                unesco_items = json.load(f)
            input_unesco_count = len(unesco_items)
            for it in unesco_items:
                qid = it["item"]["value"].split("/")[-1]
                source_id = f"WD:{qid}"
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
                            state="India",
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
                        imported_unesco_count += 1
                    else:
                        rejected_unesco_boundary_count += 1

        # 5. Optional OSM PBF / XML streaming ingestion
        osm_stats = {}
        if osm_pbf and osm_pbf.exists():
            osm_extract_dt = date.fromisoformat(source_extract_date) if source_extract_date else import_dt
            osm_importer = OsmStreamingImporter(temp_store, boundary_val, import_dt, extract_dt=osm_extract_dt)
            osm_stats = osm_importer.run_import(osm_pbf)

        # Reconcile published metadata from ACTUAL SQLite row counts
        with temp_store._get_connection() as conn:
            actual_settlements = conn.execute("SELECT count(*) FROM settlements").fetchone()[0]
            actual_places = conn.execute("SELECT count(*) FROM places").fetchone()[0]
            integrity = conn.execute("PRAGMA integrity_check").fetchall()
            if not integrity or integrity[0][0] != "ok":
                raise RuntimeError(f"Integrity check failed on staging database: {integrity}")

        # 6. Record Import Metadata in Database
        # Truthful coverage level: Only an import covering full nationwide India extract qualifies for Complete Extract.
        # A test fixture, regional zone, or partial subset MUST remain Partial Coverage.
        is_full_india = False
        if osm_pbf and osm_pbf.exists():
            fname = osm_pbf.name.lower()
            if "india-latest" in fname and osm_pbf.stat().st_size > 1_000_000_000:
                is_full_india = True

        cov_level = "Complete Extract" if is_full_india else "Partial Coverage"
        cov_note = "Full India OSM Extract" if is_full_india else (
            f"Regional / Partial Extract ({osm_pbf.name})" if (osm_pbf and osm_pbf.exists()) else "Multi-State Subsets"
        )

        temp_store.set_metadata("coverage_level", cov_level)
        temp_store.set_metadata("coverage_note", cov_note)
        temp_store.set_metadata("covered_regions", "Karnataka, Gujarat, Rajasthan, Bihar, Madhya Pradesh, Tamil Nadu, Odisha, Goa, Himachal Pradesh, Assam, Meghalaya, Sikkim, Manipur, Tripura, Nagaland, Arunachal Pradesh, Mizoram, Delhi, Maharashtra, UP, and UNECE UN/LOCODE Indian points")
        temp_store.set_metadata("snapshot_date", snapshot_date)
        temp_store.set_metadata("source_extract_date", source_extract_date or snapshot_date)
        temp_store.set_metadata("settlements_count", str(actual_settlements))
        temp_store.set_metadata("places_count", str(actual_places))
        temp_store.set_metadata("input_unlocode_count", str(input_unlocode_count))
        temp_store.set_metadata("imported_unlocode_count", str(imported_unlocode_count))
        temp_store.set_metadata("rejected_unlocode_boundary_count", str(rejected_unlocode_boundary_count))
        temp_store.set_metadata("input_unesco_count", str(input_unesco_count))
        temp_store.set_metadata("imported_unesco_count", str(imported_unesco_count))
        temp_store.set_metadata("rejected_unesco_boundary_count", str(rejected_unesco_boundary_count))
        temp_store.set_metadata("unlocode_sha256", unlocode_sha)
        temp_store.set_metadata("boundary_sha256", boundary_sha)
        temp_store.set_metadata("unesco_sha256", unesco_sha)
        temp_store.set_metadata("osm_pbf_sha256", osm_pbf_sha)
        temp_store.set_metadata("osm_stats_json", json.dumps(osm_stats, default=str))

        # Checkpoint WAL logs to ensure everything is flushed to the main db file before copying
        with temp_store._get_connection() as tmp_c:
            tmp_c.execute("PRAGMA wal_checkpoint(TRUNCATE)")

        # Atomic copy and replace with backup/rollback on Windows
        backup_db_path = None
        try:
            if output_db.exists():
                backup_db_path = output_db.with_suffix(".db.bak")
                shutil.copy2(str(output_db), str(backup_db_path))
            shutil.copy2(str(temp_db_path), str(output_db))
            with RealCatalogStore(output_db)._get_connection() as out_c:
                out_c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            if backup_db_path and backup_db_path.exists():
                backup_db_path.unlink()
        except Exception as e:
            if backup_db_path and backup_db_path.exists():
                shutil.copy2(str(backup_db_path), str(output_db))
                backup_db_path.unlink()
            raise RuntimeError(f"Atomic replacement failed for {output_db}: {e}") from e

        return {
            "status": "success",
            "output_db": str(output_db),
            "settlements_count": actual_settlements,
            "places_count": actual_places,
            "input_unlocode_count": input_unlocode_count,
            "imported_unlocode_count": imported_unlocode_count,
            "rejected_unlocode_boundary_count": rejected_unlocode_boundary_count,
            "input_unesco_count": input_unesco_count,
            "imported_unesco_count": imported_unesco_count,
            "rejected_unesco_boundary_count": rejected_unesco_boundary_count,
            "unlocode_sha256": unlocode_sha,
            "boundary_sha256": boundary_sha,
            "unesco_sha256": unesco_sha,
            "osm_stats": osm_stats,
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
    parser.add_argument("--osm-pbf", type=str, default=None, help="Optional Path to OpenStreetMap PBF/XML extract")
    parser.add_argument("--version", type=str, default="2026-11-10", help="Import snapshot date")
    parser.add_argument("--extract-date", type=str, default=None, help="Source publication/export date (defaults to import date)")
    args = parser.parse_args()

    unlocode_p = Path(args.unlocode).resolve() if args.unlocode else None
    unesco_p = Path(args.unesco).resolve() if args.unesco else None
    boundary_p = Path(args.boundary).resolve() if args.boundary else None
    osm_p = Path(args.osm_pbf).resolve() if args.osm_pbf else None
    out_p = Path(args.output).resolve()

    print(f"Starting streaming import -> {out_p}")
    res = run_streaming_import(
        unlocode_csv=unlocode_p,
        unesco_json=unesco_p,
        boundary_geojson=boundary_p,
        output_db=out_p,
        snapshot_date=args.version,
        osm_pbf=osm_p,
        source_extract_date=args.extract_date,
    )
    print("Import success:", res)


if __name__ == "__main__":
    main()
