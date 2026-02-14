#!/usr/bin/env python3
"""CLI for the multi-site characterization pipeline.

Usage:
    python scripts/characterize_site.py --name "Tubbataha Reefs" --tier silver --country Philippines
    python scripts/characterize_site.py --list
    python scripts/characterize_site.py --bulk sites.json
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from maris.sites.characterizer import SiteCharacterizer  # noqa: E402
from maris.sites.models import CharacterizationTier, CoordinatePair  # noqa: E402
from maris.sites.registry import SiteRegistry  # noqa: E402

DEFAULT_REGISTRY = project_root / "data" / "site_registry.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="MARIS Site Characterization CLI")
    parser.add_argument("--name", help="MPA name to characterize")
    parser.add_argument(
        "--tier",
        choices=["bronze", "silver", "gold"],
        default="bronze",
        help="Characterization depth tier",
    )
    parser.add_argument("--country", default="", help="Country (skips Marine Regions lookup)")
    parser.add_argument("--lat", type=float, help="Latitude")
    parser.add_argument("--lon", type=float, help="Longitude")
    parser.add_argument("--area", type=float, help="Area in km2")
    parser.add_argument("--year", type=int, help="Designation year")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY, help="Registry JSON path")
    parser.add_argument("--list", action="store_true", help="List all registered sites")
    parser.add_argument("--bulk", type=Path, help="Bulk characterize from JSON file")

    args = parser.parse_args()
    registry = SiteRegistry(args.registry)

    if args.list:
        sites = registry.list_sites()
        if not sites:
            print("No sites registered.")
            return
        print(f"{'Name':<45} {'Tier':<8} {'Country':<20} {'ESV (USD)':<15}")
        print("-" * 90)
        for s in sites:
            esv = f"${s.estimated_esv_usd:,.0f}" if s.estimated_esv_usd else "N/A"
            print(f"{s.canonical_name:<45} {s.tier.value:<8} {s.country:<20} {esv:<15}")
        return

    if args.bulk:
        if not args.bulk.exists():
            print(f"Bulk file not found: {args.bulk}")
            sys.exit(1)
        with open(args.bulk) as f:
            bulk_data = json.load(f)
        characterizer = SiteCharacterizer()
        for entry in bulk_data.get("sites", []):
            name = entry.get("name", "")
            tier = CharacterizationTier(entry.get("tier", "bronze"))
            coords = None
            if "lat" in entry and "lon" in entry:
                coords = CoordinatePair(latitude=entry["lat"], longitude=entry["lon"])
            site = characterizer.characterize(
                name=name,
                tier=tier,
                country=entry.get("country", ""),
                coordinates=coords,
                area_km2=entry.get("area_km2"),
                designation_year=entry.get("designation_year"),
            )
            if not registry.contains(name):
                registry.add_site(site)
                print(f"  Added: {name} ({tier.value})")
            else:
                registry.update_site(site)
                print(f"  Updated: {name} ({tier.value})")
        print(f"Registry now has {registry.count()} sites.")
        return

    if not args.name:
        parser.print_help()
        sys.exit(1)

    coordinates = None
    if args.lat is not None and args.lon is not None:
        coordinates = CoordinatePair(latitude=args.lat, longitude=args.lon)

    tier = CharacterizationTier(args.tier)
    characterizer = SiteCharacterizer()

    print(f"Characterizing {args.name} at {tier.value} tier...")
    site = characterizer.characterize(
        name=args.name,
        tier=tier,
        country=args.country,
        coordinates=coordinates,
        area_km2=args.area,
        designation_year=args.year,
    )

    if not registry.contains(args.name):
        registry.add_site(site)
        print(f"Site added to registry: {site.canonical_name}")
    else:
        registry.update_site(site)
        print(f"Site updated in registry: {site.canonical_name}")

    print(json.dumps(site.model_dump(mode="json"), indent=2, default=str))


if __name__ == "__main__":
    main()
