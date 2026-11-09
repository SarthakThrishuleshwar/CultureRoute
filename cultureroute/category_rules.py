"""Category tag classification rules and exclusions for CultureRoute Real Places.

Defines:
1. Exact OSM and Wikidata tag mappings to the 4 Cultural Categories:
   - Heritage: historic monuments, forts, ruins, heritage sites, memorials, castles.
   - Museum: museums, archives, art centres, public galleries.
   - Religious: places of worship (temples, mosques, churches, gurdwaras, viharas, ashrams).
   - Food: traditional regional markets, century-old street bazaars, culinary heritage institutions.
2. Strict exclusions: generic modern restaurants, fast food, cafes, non-cultural eateries.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple
from cultureroute.domain import CulturalCategory


# Subcategories and tags qualifying as HERITAGE
HERITAGE_TAGS = {
    "historic": {
        "monument", "memorial", "castle", "fort", "ruins", "archaeological_site",
        "city_gate", "tomb", "stepwell", "heritage", "palace", "pillar"
    },
    "heritage": {"1", "2", "yes"},
    "tourism": {"monument"}
}

# Subcategories and tags qualifying as MUSEUM
MUSEUM_TAGS = {
    "tourism": {"museum", "gallery"},
    "amenity": {"arts_centre"}
}

# Subcategories and tags qualifying as RELIGIOUS
RELIGIOUS_TAGS = {
    "amenity": {"place_of_worship"},
    "historic": {"temple", "church", "mosque", "gurdwara"}
}

# Subcategories qualifying as CULTURAL FOOD EXPERIENCE
# Note: Generic restaurant, fast_food, cafe are explicitly EXCLUDED.
FOOD_HERITAGE_TAGS = {
    "amenity": {"marketplace"},
    "cuisine": {"regional", "traditional", "indian", "mughlai", "rajasthani", "south_indian"}
}

EXCLUDED_AMENITIES = {
    "fast_food", "bar", "pub", "nightclub", "atm", "bank", "fuel",
    "parking", "pharmacy", "hospital", "police", "post_office", "school"
}


def classify_cultural_tags(tags: Dict[str, str]) -> Optional[Tuple[CulturalCategory, str]]:
    """Classify a raw tag dictionary into a cultural category and subcategory tag.

    Returns (category, subcategory_name) or None if the entity does not qualify
    as a defensible cultural attraction.
    """
    # 1. Check exclusions first
    amenity = tags.get("amenity", "").lower()
    if amenity in EXCLUDED_AMENITIES:
        return None

    # Check generic modern restaurant without specific cultural/historic distinction
    if amenity == "restaurant":
        # Only accept if historic=yes or historic building or heritage marker is attached
        if "historic" not in tags and "heritage" not in tags:
            return None

    # 2. Check Heritage
    historic = tags.get("historic", "").lower()
    if historic in HERITAGE_TAGS["historic"]:
        return CulturalCategory.HERITAGE, historic

    if tags.get("heritage") in HERITAGE_TAGS["heritage"]:
        return CulturalCategory.HERITAGE, "heritage_site"

    # 3. Check Museum
    tourism = tags.get("tourism", "").lower()
    if tourism in MUSEUM_TAGS["tourism"]:
        return CulturalCategory.MUSEUM, tourism
    if amenity in MUSEUM_TAGS["amenity"]:
        return CulturalCategory.MUSEUM, amenity

    # 4. Check Religious
    if amenity in RELIGIOUS_TAGS["amenity"] or historic in RELIGIOUS_TAGS["historic"]:
        religion = tags.get("religion", tags.get("denomination", "religious_site")).lower()
        return CulturalCategory.RELIGIOUS, religion

    # 5. Check Cultural Food / Traditional Market
    if amenity == "marketplace":
        return CulturalCategory.FOOD, "traditional_market"

    # Wikidata P1435 (heritage designation) or P31 (instance of)
    if "heritage_designation" in tags or "unesco" in tags:
        return CulturalCategory.HERITAGE, "world_heritage"

    return None
