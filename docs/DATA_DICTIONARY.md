# CultureRoute source data dictionary

This is the full SQLite column inventory from `SmartTrip/data/PS-01.db` and `WanderMatch/data/PS-11.db`. Shared tables were compared row-for-row by primary key with `audit_sources.py` and are listed once. The ZIP files’ `01_YOUR_DATA_MODEL.md` files explain each field’s intended meaning and enum values; this page records the exact supplied SQLite schema. Source rows are raw counts, not India-filtered study counts.

| Source | Tables | Raw rows |
| --- | ---: | ---: |
| SmartTrip | 18 | 32,627 |
| WanderMatch | 14 | 27,428 |
| Shared, kept once | 8 | 11,327 |
| Distinct combined | 24 | 48,728 |

## `activities_poi`

**Source:** SmartTrip · **Raw rows:** 900

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `poi_id` | `TEXT` | Yes | PK |
| `city_id` | `TEXT` | Yes | FK → `cities.city_id` |
| `name` | `TEXT` | Yes | — |
| `category_id` | `TEXT` | Yes | FK → `categories.category_id` |
| `poi_category` | `TEXT` | Yes | — |
| `lat` | `NUMERIC(9,6)` | Yes | — |
| `lng` | `NUMERIC(9,6)` | Yes | — |
| `typical_duration_minutes` | `INTEGER` | Yes | — |
| `entry_cost` | `TEXT` | Yes | — |
| `currency` | `TEXT` | Yes | FK → `currencies.iso4217` |
| `carbon_kg` | `NUMERIC(8,3)` | Yes | — |
| `popularity_score` | `INTEGER` | Yes | — |
| `value_score` | `INTEGER` | Yes | — |
| `opens_at` | `TEXT` | No | — |
| `closes_at` | `TEXT` | No | — |
| `closed_days` | `TEXT` | No | — |
| `best_season` | `TEXT` | No | — |
| `accessibility` | `TEXT` | Yes | — |
| `tags` | `TEXT` | Yes | — |
| `description` | `TEXT` | Yes | — |
| `has_xr_scene` | `INTEGER` | Yes | — |
| `status` | `TEXT` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `airlines`

**Source:** SmartTrip · **Raw rows:** 30

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `airline_id` | `TEXT` | Yes | PK |
| `iata` | `TEXT` | Yes | — |
| `name` | `TEXT` | Yes | — |
| `alliance` | `TEXT` | No | — |
| `country_id` | `TEXT` | Yes | FK → `countries.country_id` |
| `low_cost` | `INTEGER` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `airports`

**Source:** SmartTrip · **Raw rows:** 80

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `airport_id` | `TEXT` | Yes | PK |
| `iata` | `TEXT` | Yes | — |
| `icao` | `TEXT` | No | — |
| `name` | `TEXT` | Yes | — |
| `city_id` | `TEXT` | Yes | FK → `cities.city_id` |
| `lat` | `NUMERIC(9,6)` | Yes | — |
| `lng` | `NUMERIC(9,6)` | Yes | — |
| `timezone` | `TEXT` | Yes | — |
| `is_international` | `INTEGER` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `categories`

**Source:** SmartTrip · **Raw rows:** 70

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `category_id` | `TEXT` | Yes | PK |
| `code` | `TEXT` | Yes | — |
| `label` | `TEXT` | Yes | — |
| `parent_category_id` | `TEXT` | No | FK → `categories.category_id` |
| `applies_to` | `TEXT` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `cities`

**Source:** Shared: SmartTrip + WanderMatch · **Raw rows:** 60

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `city_id` | `TEXT` | Yes | PK |
| `name` | `TEXT` | Yes | — |
| `state` | `TEXT` | No | — |
| `country_id` | `TEXT` | Yes | FK → `countries.country_id` |
| `country_code` | `TEXT` | Yes | — |
| `lat` | `NUMERIC(9,6)` | Yes | — |
| `lng` | `NUMERIC(9,6)` | Yes | — |
| `timezone` | `TEXT` | Yes | — |
| `region` | `TEXT` | Yes | — |
| `population` | `INTEGER` | No | — |
| `season_profile` | `TEXT` | Yes | — |
| `peak_months` | `TEXT` | Yes | — |
| `primary_language` | `TEXT` | Yes | FK → `languages.bcp47` |
| `description` | `TEXT` | No | — |
| `status` | `TEXT` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `countries`

**Source:** Shared: SmartTrip + WanderMatch · **Raw rows:** 30

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `country_id` | `TEXT` | Yes | PK |
| `iso2` | `TEXT` | Yes | — |
| `iso3` | `TEXT` | Yes | — |
| `name` | `TEXT` | Yes | — |
| `default_currency` | `TEXT` | Yes | FK → `currencies.iso4217` |
| `calling_code` | `TEXT` | Yes | — |
| `region` | `TEXT` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `currencies`

**Source:** Shared: SmartTrip + WanderMatch · **Raw rows:** 25

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `currency_id` | `TEXT` | Yes | PK |
| `iso4217` | `TEXT` | Yes | — |
| `name` | `TEXT` | Yes | — |
| `symbol` | `TEXT` | Yes | — |
| `minor_unit_exponent` | `INTEGER` | Yes | — |
| `display_locale` | `TEXT` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `events_festivals`

**Source:** SmartTrip · **Raw rows:** 300

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `event_id` | `TEXT` | Yes | PK |
| `city_id` | `TEXT` | Yes | FK → `cities.city_id` |
| `name` | `TEXT` | Yes | — |
| `category_id` | `TEXT` | Yes | FK → `categories.category_id` |
| `start_date` | `TEXT` | Yes | — |
| `end_date` | `TEXT` | Yes | — |
| `season` | `TEXT` | Yes | — |
| `recurrence` | `TEXT` | Yes | — |
| `expected_footfall` | `INTEGER` | No | — |
| `is_ticketed` | `INTEGER` | Yes | — |
| `ticket_price` | `TEXT` | No | — |
| `currency` | `TEXT` | No | FK → `currencies.iso4217` |
| `venue_lat` | `NUMERIC(9,6)` | No | — |
| `venue_lng` | `NUMERIC(9,6)` | No | — |
| `description` | `TEXT` | Yes | — |
| `status` | `TEXT` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `flight_fares`

**Source:** SmartTrip · **Raw rows:** 8,002

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `fare_id` | `TEXT` | Yes | PK |
| `flight_id` | `TEXT` | Yes | FK → `flights.flight_id` |
| `cabin_class` | `TEXT` | Yes | — |
| `fare_class` | `TEXT` | Yes | — |
| `base_fare` | `TEXT` | Yes | — |
| `taxes` | `TEXT` | Yes | — |
| `currency` | `TEXT` | Yes | FK → `currencies.iso4217` |
| `baggage_kg` | `INTEGER` | Yes | — |
| `cabin_baggage_kg` | `INTEGER` | Yes | — |
| `changeable` | `INTEGER` | Yes | — |
| `change_fee` | `TEXT` | No | — |
| `refundable` | `INTEGER` | Yes | — |
| `seats_total` | `INTEGER` | Yes | — |
| `status` | `TEXT` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `flights`

**Source:** SmartTrip · **Raw rows:** 4,000

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `flight_id` | `TEXT` | Yes | PK |
| `airline_id` | `TEXT` | Yes | FK → `airlines.airline_id` |
| `flight_number` | `TEXT` | Yes | — |
| `origin_airport_id` | `TEXT` | Yes | FK → `airports.airport_id` |
| `dest_airport_id` | `TEXT` | Yes | FK → `airports.airport_id` |
| `departs_at` | `TEXT` | Yes | — |
| `arrives_at` | `TEXT` | Yes | — |
| `duration_minutes` | `INTEGER` | Yes | — |
| `stops` | `INTEGER` | Yes | — |
| `aircraft_type` | `TEXT` | No | — |
| `cabin_classes` | `TEXT` | Yes | — |
| `carbon_kg` | `NUMERIC(8,3)` | Yes | — |
| `status` | `TEXT` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `hotels`

**Source:** SmartTrip · **Raw rows:** 300

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `hotel_id` | `TEXT` | Yes | PK |
| `city_id` | `TEXT` | Yes | FK → `cities.city_id` |
| `name` | `TEXT` | Yes | — |
| `property_type` | `TEXT` | Yes | — |
| `star_rating` | `INTEGER` | Yes | — |
| `guest_score` | `NUMERIC(2,1)` | No | — |
| `review_count` | `INTEGER` | Yes | — |
| `address_line` | `TEXT` | Yes | — |
| `lat` | `NUMERIC(9,6)` | Yes | — |
| `lng` | `NUMERIC(9,6)` | Yes | — |
| `distance_to_centre_km` | `NUMERIC(6,2)` | Yes | — |
| `description` | `TEXT` | Yes | — |
| `base_currency` | `TEXT` | Yes | FK → `currencies.iso4217` |
| `checkin_time` | `TEXT` | Yes | — |
| `checkout_time` | `TEXT` | Yes | — |
| `chain_code` | `TEXT` | No | — |
| `has_xr_scene` | `INTEGER` | Yes | — |
| `status` | `TEXT` | Yes | — |
| `created_at` | `TEXT` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `itineraries`

**Source:** Shared: SmartTrip + WanderMatch · **Raw rows:** 803

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `itinerary_id` | `TEXT` | Yes | PK |
| `trip_id` | `TEXT` | Yes | FK → `trips.trip_id` |
| `name` | `TEXT` | Yes | — |
| `version` | `INTEGER` | Yes | — |
| `is_active` | `INTEGER` | Yes | — |
| `generated_by` | `TEXT` | Yes | — |
| `total_cost` | `TEXT` | Yes | — |
| `currency` | `TEXT` | Yes | FK → `currencies.iso4217` |
| `total_duration_minutes` | `INTEGER` | Yes | — |
| `total_carbon_kg` | `NUMERIC(10,3)` | Yes | — |
| `optimizer_weights` | `TEXT` | No | — |
| `status` | `TEXT` | Yes | — |
| `created_at` | `TEXT` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `itinerary_items`

**Source:** Shared: SmartTrip + WanderMatch · **Raw rows:** 8,583

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `item_id` | `TEXT` | Yes | PK |
| `itinerary_id` | `TEXT` | Yes | FK → `itineraries.itinerary_id` |
| `day_index` | `INTEGER` | Yes | — |
| `sort_order` | `INTEGER` | Yes | — |
| `starts_at` | `TEXT` | No | — |
| `ends_at` | `TEXT` | No | — |
| `item_type` | `TEXT` | Yes | — |
| `entity_type` | `TEXT` | No | — |
| `entity_id` | `TEXT` | No | — |
| `title` | `TEXT` | Yes | — |
| `cost` | `TEXT` | Yes | — |
| `currency` | `TEXT` | Yes | FK → `currencies.iso4217` |
| `carbon_kg` | `NUMERIC(8,3)` | Yes | — |
| `duration_minutes` | `INTEGER` | Yes | — |
| `source` | `TEXT` | Yes | — |
| `explanation` | `TEXT` | No | — |
| `locked` | `INTEGER` | Yes | — |
| `status` | `TEXT` | Yes | — |
| `created_at` | `TEXT` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `languages`

**Source:** Shared: SmartTrip + WanderMatch · **Raw rows:** 26

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `language_id` | `TEXT` | Yes | PK |
| `bcp47` | `TEXT` | Yes | — |
| `english_name` | `TEXT` | Yes | — |
| `native_name` | `TEXT` | Yes | — |
| `script` | `TEXT` | Yes | — |
| `rtl` | `INTEGER` | Yes | — |
| `tts_supported` | `INTEGER` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `place_kb`

**Source:** SmartTrip · **Raw rows:** 1,200

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `chunk_id` | `TEXT` | Yes | PK |
| `city_id` | `TEXT` | No | FK → `cities.city_id` |
| `poi_id` | `TEXT` | No | FK → `activities_poi.poi_id` |
| `section` | `TEXT` | Yes | — |
| `title` | `TEXT` | Yes | — |
| `body` | `TEXT` | Yes | — |
| `language` | `TEXT` | Yes | FK → `languages.bcp47` |
| `token_estimate` | `INTEGER` | Yes | — |
| `source_label` | `TEXT` | Yes | — |
| `embedding_ref` | `TEXT` | No | — |
| `seasonal_relevance` | `TEXT` | No | — |
| `updated_at` | `TEXT` | Yes | — |

## `poi_travel_matrix`

**Source:** SmartTrip · **Raw rows:** 6,418

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `matrix_id` | `TEXT` | Yes | PK |
| `origin_poi_id` | `TEXT` | Yes | FK → `activities_poi.poi_id` |
| `dest_poi_id` | `TEXT` | Yes | FK → `activities_poi.poi_id` |
| `mode` | `TEXT` | Yes | — |
| `minutes` | `INTEGER` | Yes | — |
| `distance_km` | `NUMERIC(7,3)` | Yes | — |
| `carbon_kg` | `NUMERIC(8,3)` | Yes | — |
| `cost` | `TEXT` | Yes | — |
| `currency` | `TEXT` | Yes | FK → `currencies.iso4217` |
| `bearing_deg` | `INTEGER` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `proposals`

**Source:** WanderMatch · **Raw rows:** 274

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `proposal_id` | `TEXT` | Yes | PK |
| `itinerary_id` | `TEXT` | Yes | FK → `itineraries.itinerary_id` |
| `proposed_by_user_id` | `TEXT` | Yes | FK → `users.user_id` |
| `action` | `TEXT` | Yes | — |
| `target_item_id` | `TEXT` | No | FK → `itinerary_items.item_id` |
| `entity_type` | `TEXT` | No | — |
| `entity_id` | `TEXT` | No | — |
| `title` | `TEXT` | Yes | — |
| `rationale` | `TEXT` | No | — |
| `cost_delta` | `TEXT` | Yes | — |
| `currency` | `TEXT` | Yes | FK → `currencies.iso4217` |
| `closes_at` | `TEXT` | Yes | — |
| `status` | `TEXT` | Yes | — |
| `created_at` | `TEXT` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `tour_guides`

**Source:** WanderMatch · **Raw rows:** 120

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `guide_id` | `TEXT` | Yes | PK |
| `city_id` | `TEXT` | Yes | FK → `cities.city_id` |
| `display_name` | `TEXT` | Yes | — |
| `languages` | `TEXT` | Yes | — |
| `specialisation` | `TEXT` | Yes | — |
| `secondary_specialisation` | `TEXT` | No | — |
| `years_experience` | `INTEGER` | Yes | — |
| `rating` | `NUMERIC(2,1)` | No | — |
| `review_count` | `INTEGER` | Yes | — |
| `day_rate` | `TEXT` | Yes | — |
| `half_day_rate` | `TEXT` | Yes | — |
| `currency` | `TEXT` | Yes | FK → `currencies.iso4217` |
| `certified` | `INTEGER` | Yes | — |
| `bio` | `TEXT` | Yes | — |
| `status` | `TEXT` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `trip_members`

**Source:** WanderMatch · **Raw rows:** 1,407

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `member_id` | `TEXT` | Yes | PK |
| `trip_id` | `TEXT` | Yes | FK → `trips.trip_id` |
| `user_id` | `TEXT` | Yes | FK → `users.user_id` |
| `role` | `TEXT` | Yes | — |
| `joined_at` | `TEXT` | Yes | — |
| `share_weight` | `NUMERIC(6,3)` | Yes | — |
| `invited_by_user_id` | `TEXT` | No | FK → `users.user_id` |
| `status` | `TEXT` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `trips`

**Source:** Shared: SmartTrip + WanderMatch · **Raw rows:** 600

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `trip_id` | `TEXT` | Yes | PK |
| `owner_user_id` | `TEXT` | Yes | FK → `users.user_id` |
| `title` | `TEXT` | Yes | — |
| `origin_city_id` | `TEXT` | No | FK → `cities.city_id` |
| `destination_city_id` | `TEXT` | Yes | FK → `cities.city_id` |
| `start_date` | `TEXT` | Yes | — |
| `end_date` | `TEXT` | Yes | — |
| `party_size` | `INTEGER` | Yes | — |
| `adults` | `INTEGER` | Yes | — |
| `children` | `INTEGER` | Yes | — |
| `trip_type` | `TEXT` | Yes | — |
| `is_group_trip` | `INTEGER` | Yes | — |
| `status` | `TEXT` | Yes | — |
| `home_currency` | `TEXT` | Yes | FK → `currencies.iso4217` |
| `notes` | `TEXT` | No | — |
| `created_at` | `TEXT` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `user_interactions`

**Source:** WanderMatch · **Raw rows:** 12,339

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `interaction_id` | `TEXT` | Yes | PK |
| `user_id` | `TEXT` | Yes | FK → `users.user_id` |
| `entity_type` | `TEXT` | Yes | — |
| `entity_id` | `TEXT` | Yes | — |
| `interaction_type` | `TEXT` | Yes | — |
| `occurred_at` | `TEXT` | Yes | — |
| `dwell_seconds` | `INTEGER` | No | — |
| `position_in_list` | `INTEGER` | No | — |
| `query_text` | `TEXT` | No | — |
| `query_language` | `TEXT` | No | FK → `languages.bcp47` |
| `channel` | `TEXT` | Yes | — |
| `session_id` | `TEXT` | Yes | — |
| `implicit_rating` | `NUMERIC(3,2)` | No | — |

## `user_preferences`

**Source:** WanderMatch · **Raw rows:** 1,200

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `preference_id` | `TEXT` | Yes | PK |
| `user_id` | `TEXT` | Yes | FK → `users.user_id` |
| `preferred_languages` | `TEXT` | Yes | — |
| `guide_language` | `TEXT` | No | FK → `languages.bcp47` |
| `interests` | `TEXT` | Yes | — |
| `dietary_flags` | `TEXT` | No | — |
| `accessibility_needs` | `TEXT` | No | — |
| `preferred_currency` | `TEXT` | Yes | FK → `currencies.iso4217` |
| `max_daily_budget` | `TEXT` | No | — |
| `max_daily_budget_currency` | `TEXT` | No | FK → `currencies.iso4217` |
| `pace` | `TEXT` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `users`

**Source:** Shared: SmartTrip + WanderMatch · **Raw rows:** 1,200

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `user_id` | `TEXT` | Yes | PK |
| `display_name` | `TEXT` | Yes | — |
| `email` | `TEXT` | Yes | — |
| `home_city_id` | `TEXT` | Yes | FK → `cities.city_id` |
| `home_currency` | `TEXT` | Yes | FK → `currencies.iso4217` |
| `locale` | `TEXT` | Yes | FK → `languages.bcp47` |
| `budget_band` | `TEXT` | Yes | — |
| `travel_style` | `TEXT` | Yes | — |
| `traveller_type` | `TEXT` | Yes | — |
| `segment` | `TEXT` | Yes | — |
| `date_of_signup` | `TEXT` | Yes | — |
| `loyalty_tier` | `TEXT` | No | — |
| `status` | `TEXT` | Yes | — |
| `created_at` | `TEXT` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

## `votes`

**Source:** WanderMatch · **Raw rows:** 761

| Column | SQLite type | Required | Key / reference |
| --- | --- | --- | --- |
| `vote_id` | `TEXT` | Yes | PK |
| `proposal_id` | `TEXT` | Yes | FK → `proposals.proposal_id` |
| `user_id` | `TEXT` | Yes | FK → `users.user_id` |
| `value` | `TEXT` | Yes | — |
| `weight` | `NUMERIC(4,2)` | Yes | — |
| `comment` | `TEXT` | No | — |
| `cast_at` | `TEXT` | Yes | — |
| `updated_at` | `TEXT` | Yes | — |

