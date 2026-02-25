"""Enrich case study JSONs with OBIS biodiversity, quality, and SST baseline data.

Usage:
    python scripts/enrich_obis.py              # enrich all 9 sites
    python scripts/enrich_obis.py --dry-run    # preview only
    python scripts/enrich_obis.py --site cabo  # single site
    python scripts/enrich_obis.py --force      # re-fetch even if already enriched
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from math import cos, radians, sqrt
from pathlib import Path

from maris.scenario.environmental_baselines import extract_sst_baseline
from maris.services.ingestion.discovery import discover_case_study_paths
from maris.sites.api_clients import OBISClient
from maris.sites.biodiversity_metrics import (
    build_wkt_from_bounds,
    compute_biodiversity_metrics,
)
from maris.sites.observation_quality import compute_observation_quality


def _derive_wkt_bbox(
    lat: float, lon: float, area_km2: float, cap_degrees: float = 8.0
) -> str:
    """Derive a WKT bounding box from site coordinates and area.

    Computes a square bounding box centered on (lat, lon) with side length
    proportional to sqrt(area). Caps each half-side at cap_degrees/2 to
    avoid absurdly large queries for big MPAs.
    """
    radius_km = sqrt(area_km2) / 2.0
    delta_lat = min(cap_degrees / 2, radius_km / 111.0)
    delta_lon = min(
        cap_degrees / 2,
        radius_km / (111.0 * max(cos(radians(abs(lat))), 0.1)),
    )
    return build_wkt_from_bounds(
        lat - delta_lat, lon - delta_lon, lat + delta_lat, lon + delta_lon
    )


def _enrich_site(
    cs_path: Path,
    obis_client: OBISClient,
    stats: dict,
    portfolio_max_records: int,
    dry_run: bool = False,
    force: bool = False,
) -> dict | None:
    """Enrich a single case study JSON with OBIS data.

    Returns a summary dict on success, or None if skipped.
    """
    with open(cs_path) as f:
        cs = json.load(f)

    site_name = cs.get("site", {}).get("name", cs_path.stem)

    # Skip if already enriched (unless --force)
    if cs.get("biodiversity_metrics", {}).get("obis_fetched_at") and not force:
        print(f"  SKIP {site_name} (already enriched, use --force to re-fetch)")
        return None

    coords = cs.get("site", {}).get("coordinates", {})
    lat = coords.get("latitude", 0.0)
    lon = coords.get("longitude", 0.0)
    area_km2 = cs.get("site", {}).get("area_km2", 100.0)

    if dry_run:
        print(f"  DRY-RUN {site_name}: would fetch OBIS data for "
              f"lat={lat}, lon={lon}, area={area_km2} km2")
        return None

    wkt = _derive_wkt_bbox(lat, lon, area_km2)

    # Fetch OBIS data (each call in try/except for graceful degradation)
    redlist: list = []
    try:
        redlist = obis_client.get_checklist_redlist(geometry=wkt)
    except ConnectionError as exc:
        print(f"  WARNING: Red List fetch failed for {site_name}: {exc}",
              file=sys.stderr)
    except Exception as exc:
        print(f"  WARNING: Red List fetch error for {site_name}: {exc}",
              file=sys.stderr)

    composition: dict = {}
    try:
        composition = obis_client.get_statistics_composition(geometry=wkt)
    except ConnectionError as exc:
        print(f"  WARNING: Composition fetch failed for {site_name}: {exc}",
              file=sys.stderr)
    except Exception as exc:
        print(f"  WARNING: Composition fetch error for {site_name}: {exc}",
              file=sys.stderr)

    qc_stats: dict = {}
    try:
        qc_stats = obis_client.get_statistics_qc(geometry=wkt)
    except ConnectionError as exc:
        print(f"  WARNING: QC stats fetch failed for {site_name}: {exc}",
              file=sys.stderr)
    except Exception as exc:
        print(f"  WARNING: QC stats fetch error for {site_name}: {exc}",
              file=sys.stderr)

    env_stats: dict = {}
    try:
        env_stats = obis_client.get_statistics_env(geometry=wkt)
    except ConnectionError as exc:
        print(f"  WARNING: Env stats fetch failed for {site_name}: {exc}",
              file=sys.stderr)
    except Exception as exc:
        print(f"  WARNING: Env stats fetch error for {site_name}: {exc}",
              file=sys.stderr)

    # Compute metrics
    bio = compute_biodiversity_metrics(stats, redlist, composition)
    bio["obis_fetched_at"] = datetime.now(timezone.utc).isoformat()

    qual = compute_observation_quality(stats, qc_stats, portfolio_max_records)
    sst = extract_sst_baseline(env_stats)

    # Inject into case study
    cs["biodiversity_metrics"] = bio
    cs["observation_quality"] = qual
    cs["environmental_baselines"] = {"sst": sst}

    # Atomic write: tmp file then os.replace
    fd, tmp_path = tempfile.mkstemp(
        dir=cs_path.parent, suffix=".tmp", prefix=cs_path.stem
    )
    try:
        with os.fdopen(fd, "w") as tmp_f:
            json.dump(cs, tmp_f, indent=2, ensure_ascii=False)
            tmp_f.write("\n")
        os.replace(tmp_path, cs_path)
    except Exception:
        # Clean up temp file on failure
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    print(f"  OK {site_name}: {stats.get('records', 0)} records, "
          f"{bio['species_richness']} species, "
          f"{bio['iucn_threatened_count']} IUCN threatened, "
          f"quality={qual['composite_quality_score']:.3f}, "
          f"median SST={sst.get('median_sst_c')}")

    return {
        "name": site_name,
        "records": stats.get("records", 0),
        "species": bio["species_richness"],
        "iucn_threatened": bio["iucn_threatened_count"],
        "quality_score": qual["composite_quality_score"],
        "median_sst": sst.get("median_sst_c"),
    }


def main() -> None:
    """CLI entry point for OBIS enrichment."""
    parser = argparse.ArgumentParser(
        description="Enrich case study JSONs with OBIS biodiversity data."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview what would be fetched without writing files.",
    )
    parser.add_argument(
        "--site", type=str, default=None,
        help="Enrich a single site (substring match on filename).",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-fetch even if obis_fetched_at already present.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    paths = discover_case_study_paths(project_root)

    if args.site:
        site_filter = args.site.lower()
        paths = [p for p in paths if site_filter in p.stem.lower()]
        if not paths:
            print(f"No case study found matching '{args.site}'", file=sys.stderr)
            sys.exit(1)

    print(f"OBIS Enrichment: {len(paths)} site(s)")
    print("=" * 60)

    obis = OBISClient()

    # Pass 1: fetch statistics for all sites to determine portfolio_max_records
    print("\nPass 1: Fetching site statistics...")
    all_stats: dict[str, dict] = {}
    for cs_path in paths:
        with open(cs_path) as f:
            cs = json.load(f)
        site_name = cs.get("site", {}).get("name", cs_path.stem)
        coords = cs.get("site", {}).get("coordinates", {})
        lat = coords.get("latitude", 0.0)
        lon = coords.get("longitude", 0.0)
        area_km2 = cs.get("site", {}).get("area_km2", 100.0)
        wkt = _derive_wkt_bbox(lat, lon, area_km2)

        stats: dict = {}
        try:
            stats = obis.get_statistics(geometry=wkt)
            print(f"  {site_name}: {stats.get('records', 0)} records, "
                  f"{stats.get('species', 0)} species")
        except ConnectionError as exc:
            print(f"  WARNING: Statistics fetch failed for {site_name}: {exc}",
                  file=sys.stderr)
        except Exception as exc:
            print(f"  WARNING: Statistics fetch error for {site_name}: {exc}",
                  file=sys.stderr)
        all_stats[str(cs_path)] = stats

    all_records = [s.get("records", 0) for s in all_stats.values()]
    portfolio_max_records = max(all_records + [10_000])
    print(f"\n  Portfolio max records: {portfolio_max_records:,}")

    # Pass 2: enrich each site
    print("\nPass 2: Enriching sites...")
    summaries: list[dict] = []
    for cs_path in paths:
        stats = all_stats.get(str(cs_path), {})
        result = _enrich_site(
            cs_path, obis, stats, portfolio_max_records,
            dry_run=args.dry_run, force=args.force,
        )
        if result:
            summaries.append(result)

    # Summary
    if summaries:
        print(f"\nEnriched {len(summaries)} site(s):")
        print(f"  {'Site':<35} {'Records':>10} {'Species':>8} "
              f"{'IUCN':>6} {'Quality':>8} {'SST':>6}")
        print("  " + "-" * 75)
        for s in summaries:
            sst_str = f"{s['median_sst']:.1f}" if s["median_sst"] is not None else "N/A"
            print(f"  {s['name']:<35} {s['records']:>10,} {s['species']:>8} "
                  f"{s['iucn_threatened']:>6} {s['quality_score']:>8.3f} "
                  f"{sst_str:>6}")
    elif not args.dry_run:
        print("\nNo sites were enriched (all skipped or failed).")

    print("\nDone.")


if __name__ == "__main__":
    main()
