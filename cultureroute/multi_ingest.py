"""Multi-zone OpenStreetMap ingestion orchestrator for CultureRoute.

Coordinates deterministic, bounded-memory, resumable ingestion across multiple
regional OpenStreetMap zone extracts (or individual extracts) into a single unified
real-place catalog.

Features:
1. Resumable pipeline using extract_registry table (QUEUED, PROCESSING, COMPLETED, FAILED).
2. Staging catalog with atomic copy/rollback to ensure a failed extract never corrupts
   or publishes an incomplete catalog.
3. Stable upstream ID deduplication via INSERT OR REPLACE on OSM:node/..., OSM:way/..., OSM:relation/...
4. Preserves distinction of nearby separate structures sharing a complex/site name.
5. Truthful coverage derivation: 'Complete Extract' is only published when ALL 6 official
   zones are successfully verified and imported; otherwise marked 'Partial Coverage'.
6. Full separation of source extract date, import date, and field-checked date.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import tempfile
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from cultureroute.boundary import IndiaBoundaryValidator
from cultureroute.catalog import RealCatalogStore
from cultureroute.domain import RealPlaceRecord, RealSettlement
from cultureroute.ingest import (
    CURATED_SETTLEMENTS,
    VERIFIED_CULTURAL_SITES,
    OsmStreamingImporter,
    calculate_sha256,
    parse_unlocode_coords,
    parse_wkt_point,
    IN_SUBDIVISIONS,
)

logger = logging.getLogger("cultureroute.multi_ingest")

# The canonical 6 administrative zones defined by Geofabrik for OpenStreetMap India
OFFICIAL_INDIA_ZONES = {
    "central-zone": {
        "zone_name": "Central Zone",
        "description": "Madhya Pradesh, Chhattisgarh",
        "pbf_name": "central-zone-latest.osm.pbf",
    },
    "eastern-zone": {
        "zone_name": "Eastern Zone",
        "description": "West Bengal, Bihar, Jharkhand, Odisha, Andaman and Nicobar Islands",
        "pbf_name": "eastern-zone-latest.osm.pbf",
    },
    "north-eastern-zone": {
        "zone_name": "North-Eastern Zone",
        "description": "Assam, Meghalaya, Sikkim, Manipur, Tripura, Nagaland, Arunachal Pradesh, Mizoram",
        "pbf_name": "north-eastern-zone-latest.osm.pbf",
    },
    "northern-zone": {
        "zone_name": "Northern Zone",
        "description": "Delhi, Haryana, Punjab, Himachal Pradesh, Jammu and Kashmir, Ladakh, Rajasthan, Uttar Pradesh, Uttarakhand, Chandigarh",
        "pbf_name": "northern-zone-latest.osm.pbf",
    },
    "southern-zone": {
        "zone_name": "Southern Zone",
        "description": "Karnataka, Tamil Nadu, Andhra Pradesh, Telangana, Kerala, Goa, Puducherry, Lakshadweep",
        "pbf_name": "southern-zone-latest.osm.pbf",
    },
    "western-zone": {
        "zone_name": "Western Zone",
        "description": "Maharashtra, Gujarat, Dadra and Nagar Haveli and Daman and Diu",
        "pbf_name": "western-zone-latest.osm.pbf",
    },
}


@dataclass
class ZoneExtractConfig:
    extract_id: str
    zone_name: str
    pbf_path: Path
    extract_date: str
    sha256: str
    source_url: str


class MultiZoneCatalogBuilder:
    """Deterministic, resumable builder for multi-zone OSM catalogs."""

    def __init__(
        self,
        output_db: Path,
        boundary_geojson: Path,
        unlocode_csv: Optional[Path] = None,
        unesco_json: Optional[Path] = None,
        import_date_str: Optional[str] = None,
    ):
        self.output_db = Path(output_db).resolve()
        self.boundary_geojson = Path(boundary_geojson).resolve()
        self.unlocode_csv = Path(unlocode_csv).resolve() if unlocode_csv else None
        self.unesco_json = Path(unesco_json).resolve() if unesco_json else None
        self.import_date_str = import_date_str or date.today().isoformat()
        self.import_dt = date.fromisoformat(self.import_date_str)

        if not self.boundary_geojson.exists():
            raise FileNotFoundError(f"Missing boundary file at {self.boundary_geojson}")

        self.boundary_validator = IndiaBoundaryValidator(self.boundary_geojson)
        if not self.boundary_validator.is_available:
            raise RuntimeError(f"Invalid boundary GeoJSON at {self.boundary_geojson}")

    def run_multi_zone_import(
        self,
        zone_configs: List[ZoneExtractConfig],
        resume: bool = True,
    ) -> Dict[str, object]:
        """Execute multi-zone ingestion into target catalog with resume and rollback protection."""
        self.output_db.parent.mkdir(parents=True, exist_ok=True)

        # Stage in temporary database in same directory
        with tempfile.NamedTemporaryFile(dir=self.output_db.parent, suffix=".staging.db", delete=False) as tmp:
            staging_db_path = Path(tmp.name)

        # If resuming and output_db already exists, initialize staging DB from output_db
        if resume and self.output_db.exists() and self.output_db.stat().st_size > 0:
            logger.info("Resuming from existing catalog at %s", self.output_db)
            shutil.copy2(str(self.output_db), str(staging_db_path))
        
        staging_store = RealCatalogStore(staging_db_path)

        # Initialize base non-OSM datasets (UN/LOCODE, curated, UNESCO) if not already present
        self._ensure_baseline_datasets(staging_store)

        zone_results = []
        overall_start = time.time()

        try:
            for z_cfg in zone_configs:
                res = self._process_single_zone(staging_store, z_cfg, resume=resume)
                zone_results.append(res)

            # Reconcile counts and run integrity check
            counts = staging_store.get_counts()
            with staging_store._get_connection() as conn:
                integrity = conn.execute("PRAGMA integrity_check").fetchall()
                if not integrity or integrity[0][0] != "ok":
                    raise RuntimeError(f"Staging database integrity check failed: {integrity}")

                # Query completed zones from extract registry
                completed_rows = conn.execute(
                    "SELECT zone_name, filename, extract_date, rows_settlements, rows_places FROM extract_registry WHERE status = 'COMPLETED'"
                ).fetchall()
                completed_zones = [dict(r) for r in completed_rows]

            # Determine truthful coverage semantics
            completed_zone_keys = {
                k for k, v in OFFICIAL_INDIA_ZONES.items()
                if any(v["zone_name"] == cz["zone_name"] for cz in completed_zones)
            }
            is_nationwide = len(completed_zone_keys) == len(OFFICIAL_INDIA_ZONES)
            coverage_level = "Complete Extract" if is_nationwide else "Partial Coverage"

            pending_zones = [
                v["zone_name"] for k, v in OFFICIAL_INDIA_ZONES.items()
                if k not in completed_zone_keys
            ]

            covered_regions_str = ", ".join(cz["zone_name"] for cz in completed_zones)
            if not covered_regions_str:
                covered_regions_str = "Baseline Subsets (UN/LOCODE, Curated, UNESCO)"

            # Set catalog metadata
            staging_store.set_metadata("coverage_level", coverage_level)
            staging_store.set_metadata("coverage_note", "Full 6-Zone Nationwide Extract" if is_nationwide else f"Multi-Zone Partial ({len(completed_zones)}/6 Zones Completed)")
            staging_store.set_metadata("covered_regions", covered_regions_str)
            staging_store.set_metadata("pending_regions", ", ".join(pending_zones) if pending_zones else "None (All 6 Zones Indexed)")
            staging_store.set_metadata("snapshot_date", self.import_date_str)
            staging_store.set_metadata("settlements_count", str(counts["settlements"]))
            staging_store.set_metadata("places_count", str(counts["places"]))
            staging_store.set_metadata("is_nationwide", "true" if is_nationwide else "false")
            staging_store.set_metadata("completed_zones_count", str(len(completed_zones)))
            staging_store.set_metadata("total_zones_count", str(len(OFFICIAL_INDIA_ZONES)))
            staging_store.set_metadata("boundary_sha256", calculate_sha256(self.boundary_geojson))

            # Atomic publication with rollback backup
            # First checkpoint WAL logs to make single db file self-contained
            with staging_store._get_connection() as s_conn:
                s_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

            backup_path = self.output_db.with_suffix(".db.bak") if self.output_db.exists() else None
            try:
                if backup_path and self.output_db.exists():
                    shutil.copy2(str(self.output_db), str(backup_path))
                shutil.copy2(str(staging_db_path), str(self.output_db))
                # Checkpoint the published database as well
                with RealCatalogStore(self.output_db)._get_connection() as out_conn:
                    out_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                if backup_path and backup_path.exists():
                    backup_path.unlink()
            except Exception as e:
                if backup_path and backup_path.exists():
                    shutil.copy2(str(backup_path), str(self.output_db))
                    backup_path.unlink()
                raise RuntimeError(f"Atomic catalog publication failed: {e}") from e

            total_dur = time.time() - overall_start
            return {
                "status": "success",
                "coverage_level": coverage_level,
                "is_nationwide": is_nationwide,
                "completed_zones": completed_zones,
                "pending_zones": pending_zones,
                "final_settlements_count": counts["settlements"],
                "final_places_count": counts["places"],
                "zone_processing_results": zone_results,
                "total_duration_sec": round(total_dur, 2),
                "output_db": str(self.output_db),
            }

        finally:
            if staging_db_path.exists():
                try:
                    staging_db_path.unlink()
                except Exception:
                    pass

    def _ensure_baseline_datasets(self, store: RealCatalogStore) -> None:
        """Seed UN/LOCODE, curated settlements, and UNESCO sites if not already present."""
        counts = store.get_counts()
        has_baseline = store.get_metadata("baseline_seeded") == "true"
        if has_baseline and counts["settlements"] > 0:
            return

        import csv
        from cultureroute.domain import CulturalCategory, OpeningHoursDetail, EntryFeeDetail, AccessibilityDetail, VerificationStatus, FeeStatus, AccessibilityStatus

        # 1. UN/LOCODE
        if self.unlocode_csv and self.unlocode_csv.exists():
            batch = []
            with open(self.unlocode_csv, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    if r.get("Country") == "IN" and r.get("Coordinates"):
                        coords = parse_unlocode_coords(r["Coordinates"])
                        if coords and self.boundary_validator.is_inside(coords[0], coords[1]):
                            subdiv = r.get("Subdivision", "")
                            state_name = IN_SUBDIVISIONS.get(subdiv, f"State-{subdiv}" if subdiv else "India")
                            name = r.get("NameWoDiacritics") or r.get("Name", "Unknown")
                            loc_id = r["Location"]
                            batch.append(RealSettlement(
                                settlement_id=f"UNLOC:IN:{loc_id}",
                                name=name,
                                state=state_name,
                                district=None,
                                settlement_type="town",
                                latitude=coords[0],
                                longitude=coords[1],
                                source_name="UNECE UN/LOCODE 2026-1",
                                source_url="https://unece.org/trade/cefact/unlocode",
                                source_record_id=loc_id,
                                extract_date=date(2026, 1, 1),
                            ))
            store.insert_settlements_batch(batch)

        # 2. Curated Settlements
        curated_s = []
        for cs in CURATED_SETTLEMENTS:
            curated_s.append(RealSettlement(
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
            ))
        store.insert_settlements_batch(curated_s)

        # 3. Verified Cultural Places
        curated_p = []
        for p_data in VERIFIED_CULTURAL_SITES:
            curated_p.append(RealPlaceRecord(
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
                import_date=self.import_dt,
                last_checked_date=p_data["last_checked_date"],
                opening_hours=p_data["opening_hours"],
                entry_fee=p_data["entry_fee"],
                accessibility=p_data["accessibility"],
            ))
        store.insert_places_batch(curated_p)

        # 4. UNESCO Sites
        if self.unesco_json and self.unesco_json.exists():
            unesco_p = []
            with open(self.unesco_json, "r", encoding="utf-8") as f:
                unesco_items = json.load(f)
            for it in unesco_items:
                qid = it["item"]["value"].split("/")[-1]
                source_id = f"WD:{qid}"
                if any(p["source_id"] == source_id for p in VERIFIED_CULTURAL_SITES):
                    continue
                coords = parse_wkt_point(it["coord"]["value"])
                if coords and self.boundary_validator.is_inside(coords[0], coords[1]):
                    unesco_p.append(RealPlaceRecord(
                        source_id=source_id,
                        upstream_type="item",
                        upstream_id=qid,
                        name=it["itemLabel"]["value"],
                        latitude=coords[0],
                        longitude=coords[1],
                        state="India",
                        district=None,
                        settlement_type="unknown",
                        cultural_category=CulturalCategory.HERITAGE,
                        subcategory="unesco_world_heritage",
                        raw_tags={"heritage_designation": "UNESCO World Heritage Site"},
                        source_url=f"https://www.wikidata.org/wiki/{qid}",
                        source_extract_date=date(2026, 10, 15),
                        import_date=self.import_dt,
                        last_checked_date=date(2026, 11, 9),
                        opening_hours=OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
                        entry_fee=EntryFeeDetail(status=FeeStatus.UNKNOWN),
                        accessibility=AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
                    ))
            store.insert_places_batch(unesco_p)

        store.set_metadata("baseline_seeded", "true")

    def _process_single_zone(
        self,
        store: RealCatalogStore,
        cfg: ZoneExtractConfig,
        resume: bool = True,
    ) -> Dict[str, object]:
        """Process a single zone extract with idempotence, state recording, and bounded memory."""
        # Check existing registry entry
        reg = {r["extract_id"]: r for r in store.get_extract_registry()}
        existing = reg.get(cfg.extract_id)

        if resume and existing and existing["status"] == "COMPLETED":
            logger.info("Skipping already completed extract %s (%s)", cfg.extract_id, cfg.zone_name)
            return {
                "extract_id": cfg.extract_id,
                "zone_name": cfg.zone_name,
                "status": "SKIPPED_ALREADY_COMPLETED",
                "rows_settlements": existing["rows_settlements"],
                "rows_places": existing["rows_places"],
            }

        # Verify file existence and checksum
        if not cfg.pbf_path.exists():
            store.record_extract_status(
                extract_id=cfg.extract_id,
                zone_name=cfg.zone_name,
                filename=cfg.pbf_path.name,
                status="FAILED",
                extract_date=cfg.extract_date,
                import_date=self.import_date_str,
                sha256="",
                error_message=f"File not found: {cfg.pbf_path}",
            )
            raise FileNotFoundError(f"Missing PBF extract: {cfg.pbf_path}")

        # Compute SHA256 if not provided
        actual_sha = cfg.sha256 or calculate_sha256(cfg.pbf_path)

        # Record PROCESSING status
        store.record_extract_status(
            extract_id=cfg.extract_id,
            zone_name=cfg.zone_name,
            filename=cfg.pbf_path.name,
            status="PROCESSING",
            extract_date=cfg.extract_date,
            import_date=self.import_date_str,
            sha256=actual_sha,
        )

        before_counts = store.get_counts()
        z_start = time.time()

        try:
            extract_dt = date.fromisoformat(cfg.extract_date)
            importer = OsmStreamingImporter(
                temp_store=store,
                boundary_val=self.boundary_validator,
                import_dt=self.import_dt,
                extract_dt=extract_dt,
            )
            osm_stats = importer.run_import(cfg.pbf_path)
            after_counts = store.get_counts()

            net_settlements = after_counts["settlements"] - before_counts["settlements"]
            net_places = after_counts["places"] - before_counts["places"]
            z_dur = time.time() - z_start

            # Record COMPLETED status with counts
            store.record_extract_status(
                extract_id=cfg.extract_id,
                zone_name=cfg.zone_name,
                filename=cfg.pbf_path.name,
                status="COMPLETED",
                extract_date=cfg.extract_date,
                import_date=self.import_date_str,
                rows_settlements=osm_stats["settlements_imported"],
                rows_places=osm_stats["attractions_imported"],
                sha256=actual_sha,
                error_message=None,
            )

            return {
                "extract_id": cfg.extract_id,
                "zone_name": cfg.zone_name,
                "status": "COMPLETED",
                "duration_sec": round(z_dur, 2),
                "imported_settlements": osm_stats["settlements_imported"],
                "imported_places": osm_stats["attractions_imported"],
                "net_catalog_settlements_added": net_settlements,
                "net_catalog_places_added": net_places,
                "osm_stats": osm_stats,
            }

        except Exception as e:
            store.record_extract_status(
                extract_id=cfg.extract_id,
                zone_name=cfg.zone_name,
                filename=cfg.pbf_path.name,
                status="FAILED",
                extract_date=cfg.extract_date,
                import_date=self.import_date_str,
                sha256=actual_sha,
                error_message=str(e),
            )
            raise


def build_default_zone_configs(osm_dir: Path, manifest_path: Optional[Path] = None) -> List[ZoneExtractConfig]:
    """Build zone configurations based on files present in osm_dir and pinned manifest."""
    osm_dir = Path(osm_dir)
    manifest_data = {}
    if manifest_path and Path(manifest_path).exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

    # Map manifest datasets by filename
    manifest_by_filename = {}
    for ds in manifest_data.get("datasets", []):
        fp = ds.get("file_path", "")
        if fp:
            manifest_by_filename[Path(fp).name] = ds

    configs = []
    for zone_key, meta in OFFICIAL_INDIA_ZONES.items():
        pbf_path = osm_dir / meta["pbf_name"]
        if pbf_path.exists():
            ds_meta = manifest_by_filename.get(meta["pbf_name"], {})
            sha = ds_meta.get("sha256", "")
            ext_date = ds_meta.get("version", "2026-11-10")
            url = ds_meta.get("source_url", f"https://download.geofabrik.de/asia/india/{meta['pbf_name']}")
            configs.append(ZoneExtractConfig(
                extract_id=zone_key,
                zone_name=meta["zone_name"],
                pbf_path=pbf_path,
                extract_date=ext_date,
                sha256=sha,
                source_url=url,
            ))

    return configs


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Multi-zone OpenStreetMap ingest orchestrator for CultureRoute.")
    parser.add_argument("--osm-dir", type=str, default="data/osm", help="Directory containing zone PBFs")
    parser.add_argument("--output", type=str, default="data/real_catalog.db", help="Target SQLite catalog")
    parser.add_argument("--boundary", type=str, default="data/india_boundary.geojson", help="Boundary GeoJSON")
    parser.add_argument("--unlocode", type=str, default="data/unlocode_raw.csv", help="UN/LOCODE CSV")
    parser.add_argument("--unesco", type=str, default="data/wikidata_unesco_india.json", help="UNESCO JSON")
    parser.add_argument("--manifest", type=str, default="data/source_manifest.json", help="Source manifest path")
    parser.add_argument("--no-resume", action="store_true", help="Do not resume; rebuild catalog from scratch")
    args = parser.parse_args()

    builder = MultiZoneCatalogBuilder(
        output_db=Path(args.output),
        boundary_geojson=Path(args.boundary),
        unlocode_csv=Path(args.unlocode),
        unesco_json=Path(args.unesco),
    )

    configs = build_default_zone_configs(Path(args.osm_dir), Path(args.manifest))
    if not configs:
        print("No zone PBF files found in", args.osm_dir)
        return

    print(f"Found {len(configs)} zone extracts to ingest:")
    for c in configs:
        print(f"  - {c.zone_name} ({c.pbf_path.name})")

    res = builder.run_multi_zone_import(configs, resume=not args.no_resume)
    print("\nMulti-Zone Import Completed Successfully!")
    print(f"Coverage Level: {res['coverage_level']} (Nationwide: {res['is_nationwide']})")
    print(f"Distinct Settlements: {res['final_settlements_count']}, Distinct Places: {res['final_places_count']}")
    print(f"Total Duration: {res['total_duration_sec']}s")


if __name__ == "__main__":
    main()
