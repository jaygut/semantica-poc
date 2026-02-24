"""Biodiversity metrics derived from OBIS observation data.

Transforms raw OBIS statistics into TNFD-compliant biodiversity metrics
for MT-A (risk/opportunity metrics) and MT-B (dependency/impact metrics).
"""

from __future__ import annotations

from typing import Any


def compute_biodiversity_metrics(
    statistics: dict[str, Any],
    redlist_species: list[dict[str, Any]],
    composition: dict[str, Any],
) -> dict[str, Any]:
    """Compute TNFD-ready biodiversity metrics from OBIS data.

    Returns a dict with:
    - species_richness: total species documented
    - total_records: total observation records
    - dataset_count: number of contributing datasets
    - year_range: (earliest_year, latest_year) of monitoring
    - iucn_threatened_count: number of Red List species (CR+EN+VU)
    - iucn_by_category: dict of category -> count
    - taxonomic_composition: simplified breakdown by major groups
    - mt_a_summary: formatted string for TNFD MT-A disclosure
    - mt_b_summary: formatted string for TNFD MT-B disclosure
    """
    # Extract from statistics
    species_richness = int(statistics.get("species", 0))
    total_records = int(statistics.get("records", 0))
    dataset_count = int(statistics.get("datasets", 0))

    year_min = statistics.get("yearmin")
    year_max = statistics.get("yearmax")
    year_range = (int(year_min), int(year_max)) if year_min and year_max else None

    # Process Red List species
    iucn_by_category: dict[str, int] = {}
    for sp in redlist_species:
        cat = sp.get("category", "")
        if cat:
            iucn_by_category[cat] = iucn_by_category.get(cat, 0) + 1
    iucn_threatened_count = sum(
        iucn_by_category.get(c, 0) for c in ("CR", "EN", "VU")
    )

    # Build MT-A summary
    mt_a_parts: list[str] = []
    if species_richness:
        mt_a_parts.append(f"{species_richness:,} species documented")
    if iucn_threatened_count:
        cat_parts = []
        for cat in ("CR", "EN", "VU"):
            n = iucn_by_category.get(cat, 0)
            if n:
                cat_parts.append(f"{n} {cat}")
        mt_a_parts.append(
            f"{iucn_threatened_count} IUCN Red List species ({', '.join(cat_parts)})"
        )
    mt_a_summary = "; ".join(mt_a_parts) if mt_a_parts else ""

    # Build MT-B summary
    mt_b_parts: list[str] = []
    if year_range:
        mt_b_parts.append(f"Biodiversity monitoring spans {year_range[0]}-{year_range[1]}")
    if dataset_count:
        mt_b_parts.append(f"across {dataset_count} datasets")
    if total_records:
        mt_b_parts.append(f"({total_records:,} occurrence records)")
    mt_b_summary = " ".join(mt_b_parts) if mt_b_parts else ""

    return {
        "species_richness": species_richness,
        "total_records": total_records,
        "dataset_count": dataset_count,
        "year_range": year_range,
        "iucn_threatened_count": iucn_threatened_count,
        "iucn_by_category": iucn_by_category,
        "taxonomic_composition": composition,
        "mt_a_summary": mt_a_summary,
        "mt_b_summary": mt_b_summary,
    }


def build_wkt_from_bounds(
    min_lat: float, min_lon: float, max_lat: float, max_lon: float
) -> str:
    """Build a WKT POLYGON from bounding box coordinates."""
    return (
        f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, "
        f"{max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
    )
