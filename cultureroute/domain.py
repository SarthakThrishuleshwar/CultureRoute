"""Domain models and data contracts for CultureRoute.

Defines:
1. Synthetic study record types (read-only research baseline).
2. Nationwide real-place contracts (strictly separated from synthetic entities by source namespace).
3. Field-level verification evidence, directed travel legs, and honest result level rules.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
import re
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


# =====================================================================
# Cultural Categories (Shared Specification)
# =====================================================================

class CulturalCategory(str, Enum):
    HERITAGE = "heritage"
    MUSEUM = "museum"
    RELIGIOUS = "religious"
    FOOD = "food"


# =====================================================================
# Coverage & Result Levels
# =====================================================================

class ResultLevel(str, Enum):
    """Honest result levels based on verifiable ground truth."""
    DISCOVERY_ONLY = "discovery"  # Real cultural places discovered and browsable; no itinerary created.
    PROVISIONAL = "provisional"   # Reserved for future planning when candidate stops contain unverified hours/fees.
    VERIFIED = "verified"         # Reserved for future planning when all stops, dwell times, and legs are strictly verified.


class VerificationStatus(str, Enum):
    KNOWN = "known"
    UNKNOWN = "unknown"
    ALWAYS_OPEN = "always_open"
    SEASONAL = "seasonal"


class FeeStatus(str, Enum):
    KNOWN_FREE = "known_free"
    KNOWN_TICKETED = "known_ticketed"
    UNKNOWN = "unknown"  # Critical: unknown is explicitly UNKNOWN, NOT ₹0


class AccessibilityStatus(str, Enum):
    VERIFIED_STEP_FREE = "verified_step_free"
    PARTIAL_STEP_FREE = "partial_step_free"
    NOT_ACCESSIBLE = "not_accessible"
    UNKNOWN = "unknown"


# Known synthetic prefixes and ID patterns across SmartTrip and WanderMatch
SYNTHETIC_PREFIXES = (
    "poi_", "cty_", "usr_", "trp_", "iti_", "iit_", "ptm_", "evt_",
    "cat_", "lan_", "cnt_", "cur_", "flt_", "htl_", "air_", "gui_",
    "ses_", "mem_", "pro_", "vot_", "uix_", "kb_"
)


# =====================================================================
# Evidence & Audit Trail for Verifiable Fields
# =====================================================================

class FieldEvidence(BaseModel):
    """Audit provenance for an externally verified or inspected field."""
    source_url: str = Field(description="URL to the primary document, official registry, or OSM object")
    checked_date: date = Field(description="Date when this evidence was inspected")
    verifier_notes: Optional[str] = Field(default=None, description="Observations, citations, or caveat notes")


class OpeningHoursDetail(BaseModel):
    status: VerificationStatus = VerificationStatus.UNKNOWN
    opens_local_time: Optional[str] = Field(default=None, description="Local HH:MM opening time if uniform")
    closes_local_time: Optional[str] = Field(default=None, description="Local HH:MM closing time if uniform")
    closed_days: List[str] = Field(default_factory=list, description="Days of week closed (e.g. ['Monday'])")
    raw_schedule_text: Optional[str] = Field(default=None, description="Raw tag or text from source")
    evidence: Optional[FieldEvidence] = None


class EntryFeeDetail(BaseModel):
    status: FeeStatus = FeeStatus.UNKNOWN
    amount_domestic: Optional[Decimal] = Field(default=None, description="Decimal fee in domestic currency")
    amount_international: Optional[Decimal] = Field(default=None, description="Decimal fee for foreign visitors")
    currency: str = Field(default="INR", description="Three-letter currency code")
    evidence: Optional[FieldEvidence] = None

    @field_validator("amount_domestic", "amount_international", mode="before")
    @classmethod
    def parse_decimal(cls, v):
        if v is None:
            return None
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v


class AccessibilityDetail(BaseModel):
    status: AccessibilityStatus = AccessibilityStatus.UNKNOWN
    details: Optional[str] = None
    evidence: Optional[FieldEvidence] = None


# =====================================================================
# Real Settlement Contract (Cities, Towns, Villages, Localities)
# =====================================================================

class RealSettlement(BaseModel):
    """A verified real Indian settlement from open authoritative/crowdsourced gazetteers."""
    settlement_id: str = Field(description="Namespace-prefixed stable ID, e.g. 'SETTLE:IN:123', 'UNLOC:IN:BBM'")
    name: str = Field(description="Official or common name in English")
    local_names: Dict[str, str] = Field(default_factory=dict, description="BCP-47 localized names, e.g. {'hi': '...'}")
    state: str = Field(description="Indian State or Union Territory")
    district: Optional[str] = Field(default=None, description="Administrative district; None if unrecorded by source")
    sub_district: Optional[str] = Field(default=None, description="Tehsil / Taluk / Block; None if unrecorded")
    settlement_type: Literal["city", "town", "village", "hamlet", "suburb", "locality", "rural_locality", "unknown"] = "unknown"
    latitude: float = Field(ge=5.0, le=38.0, description="WGS-84 latitude bounded to India")
    longitude: float = Field(ge=67.0, le=98.0, description="WGS-84 longitude bounded to India")
    source_name: str = Field(description="Source registry or extract name")
    source_url: str = Field(description="Canonical source URL")
    source_record_id: str = Field(description="Original ID in the upstream dataset")
    extract_date: date = Field(description="Date when source extract was published/captured")

    @field_validator("settlement_id")
    @classmethod
    def validate_settlement_id(cls, v: str) -> str:
        for prefix in SYNTHETIC_PREFIXES:
            if v.startswith(prefix):
                raise ValueError(f"Synthetic prefix '{prefix}' prohibited in real settlement ID: '{v}'")
        if not re.match(r"^[A-Z0-9_\-]+:[A-Za-z0-9_\-\.:/]+$", v):
            raise ValueError(f"Settlement ID must be namespace-prefixed (e.g. 'SETTLE:IN:123', 'OSM:node/123'), got: '{v}'")
        return v


# =====================================================================
# Real Cultural Place Contract
# =====================================================================

class RealPlaceRecord(BaseModel):
    """Contract for nationwide real-world cultural attractions.
    
    Can exist anywhere in India (including within the geographic boundaries of the 45 study cities).
    Strictly decoupled from synthetic records via source namespace and explicit source provenance.
    """
    source_id: str = Field(description="Opaque namespace-prefixed ID, e.g. 'OSM:node/12345', 'WD:Q42907'")
    upstream_type: str = Field(description="Upstream entity type, e.g. 'node', 'way', 'relation', 'item'")
    upstream_id: str = Field(description="Upstream numeric or string ID, e.g. '12345', 'Q42907'")
    name: str = Field(description="Primary catalog name in English")
    local_names: Dict[str, str] = Field(default_factory=dict, description="BCP-47 keyed name translations")
    latitude: float = Field(ge=5.0, le=38.0, description="WGS-84 latitude within India")
    longitude: float = Field(ge=67.0, le=98.0, description="WGS-84 longitude within India")
    state: str = Field(description="Indian State or Union Territory")
    district: Optional[str] = Field(default=None, description="Administrative district; None if unverified by source")
    sub_district: Optional[str] = Field(default=None, description="Tehsil / Taluk / Block; None if unverified")
    settlement_type: Literal["city", "town", "village", "hamlet", "suburb", "locality", "rural_locality", "unknown"] = "unknown"
    cultural_category: CulturalCategory
    subcategory: Optional[str] = Field(default=None, description="Specific tag, e.g. 'fort', 'stepwell', 'museum'")
    raw_tags: Dict[str, str] = Field(default_factory=dict, description="Preserved upstream source tags")
    source_url: str = Field(description="Canonical upstream source URL")
    source_extract_date: date = Field(description="Date when source dataset was published/exported")
    import_date: date = Field(description="Date when record was imported into local catalog")
    last_checked_date: date = Field(description="Date when record was last audited/verified")
    opening_hours: OpeningHoursDetail = Field(default_factory=OpeningHoursDetail)
    entry_fee: EntryFeeDetail = Field(default_factory=EntryFeeDetail)
    accessibility: AccessibilityDetail = Field(default_factory=AccessibilityDetail)

    @field_validator("source_id")
    @classmethod
    def validate_source_id_prefix(cls, v: str) -> str:
        # Enforce separation: synthetic IDs in SmartTrip/WanderMatch use specific prefixes
        for prefix in SYNTHETIC_PREFIXES:
            if v.startswith(prefix):
                raise ValueError(
                    f"Synthetic prefix '{prefix}' prohibited in RealPlaceRecord ID '{v}'. "
                    f"Real places must use external namespace prefix (e.g. 'OSM:', 'WD:', 'ASI:')."
                )
        if not re.match(r"^[A-Z0-9_\-]+:[A-Za-z0-9_\-\.:/]+$", v):
            raise ValueError(f"Real place ID must be namespace-prefixed (e.g. 'OSM:node/123'), got: '{v}'")
        return v


# =====================================================================
# Directed Travel Leg Contract (Reserved for future routing phase)
# =====================================================================

class DirectedLegOption(BaseModel):
    """Contract for a directed travel leg between two distinct points."""
    origin_source_id: str
    dest_source_id: str
    mode: Literal["walk", "cab", "auto", "public_transit"]
    duration_minutes: int = Field(gt=0, description="Directed travel duration in integer minutes")
    distance_km: Decimal = Field(gt=Decimal("0.0"), description="Traveled road/path distance")
    fare_cost: Optional[Decimal] = Field(default=None, description="Fare cost; None if unknown, 0 if walking")
    currency: str = Field(default="INR")
    carbon_kg: Optional[Decimal] = Field(default=None, description="Estimated between-stop carbon")
    is_routed_network: bool = Field(description="True if calculated along a valid road/pedestrian graph; False for straight-line estimate")

    @field_validator("fare_cost", "carbon_kg", "distance_km", mode="before")
    @classmethod
    def parse_leg_decimal(cls, v):
        if v is None:
            return None
        return Decimal(str(v))


# =====================================================================
# Coverage & Result Level Rules
# =====================================================================

def evaluate_discovery_level(places_found: int) -> ResultLevel:
    """In Phase 2, real places are in DISCOVERY ONLY mode.
    
    Itinerary planning (provisional or verified) is explicitly reserved for future phases.
    """
    return ResultLevel.DISCOVERY_ONLY
