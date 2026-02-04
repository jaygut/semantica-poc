#!/usr/bin/env python3
"""
Regenerate Semantica Export Bundle from Verified Source Schema

Transforms the corrected bridge_axiom_templates.json into the export format
required for Semantica ingestion, preserving audit trail.
"""

import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# Category to domain mapping
CATEGORY_TO_DOMAINS = {
    "ecological_to_service": ("ecological", "financial"),
    "ecological_to_ecological": ("ecological", "ecological"),
    "service_to_financial": ("service", "financial"),
}

# DOI to doc_id mapping (based on existing registry patterns)
DOI_TO_DOC_ID = {
    "10.1038/s41598-024-83664-1": "marcos_castillo_2024_dive_tourism_wtp",
    "10.1007/s00267-008-9198-z": "uyarra_2009_diver_preferences",
    "10.1002/eap.3027": "hopf_2024_notake_meta",
    "10.1038/nature13022": "edgar_2014_nature_mpa_neoli",
    "10.1890/110176": "wilmers_2012_otter_carbon",
    "10.1038/s41467-018-04568-z": "beck_2018_coral_flood_protection",
    "10.1038/s41598-020-61136-6": "menendez_2020_mangrove_flood_protection",
    "10.3390/su4030359": "salem_2012_mangrove_meta_valuation",
    "10.1073/pnas.0804601105": "aburto_2008_mangrove_fisheries",
    "10.1038/s43247-025-02229-w": "carrasquilla_2025_mangrove_juvenile_fish",
    "10.1038/ngeo1123": "donato_2011_mangrove_carbon",
    "10.1186/s13021-023-00233-1": "murdiyarso_2023_mangrove_emissions",
    "10.1038/s44183-025-00111-y": "duarte_2025_seagrass_carbon_credits",
    "10.1038/s41598-020-64094-1": "oreska_2020_seagrass_ghg_offset",
    "10.1038/s41467-025-56587-2": "zeng_2025_mangrove_restoration_bcr",
    "10.1038/s41467-023-37385-0": "eger_2023_kelp_global_value",
    "10.1111/gcb.17477": "ortiz_villa_2024_mpa_kelp_resilience",
    "10.1111/ele.12598": "mellin_2016_mpa_coral_resilience",
    "10.1111/1365-2664.13051": "rogers_2018_reef_fisheries_loss",
}


def transform_coefficients(axiom_id: str, coeffs: dict) -> dict:
    """Transform source coefficients to export format."""

    if axiom_id == "BA-001":
        # New WTP-based model
        return {
            "wtp_increase_max_percent": coeffs.get("wtp_increase_for_biomass_max_percent", 84),
            "biomass_contribution_percent": coeffs.get("biomass_contribution_to_revenue_percent", 47),
            "avg_biomass_increase_percent": coeffs.get("average_biomass_increase_full_protection_percent", 113),
            "global_additional_revenue_usd_millions": coeffs.get("global_additional_revenue_usd_millions", 616)
        }
    elif axiom_id == "BA-002":
        return {
            "biomass_ratio": coeffs.get("biomass_ratio_vs_unprotected", 6.7),
            "recovery_rate_per_year": coeffs.get("recovery_rate_per_year", 0.42)
        }
    elif axiom_id == "BA-003":
        return {
            "npp_multiplier": coeffs.get("npp_multiplier", 12),
            "carbon_value_usd_million_range": [
                coeffs.get("carbon_value_usd_million", {}).get("min", 205),
                coeffs.get("carbon_value_usd_million", {}).get("max", 408)
            ]
        }
    elif axiom_id == "BA-004":
        return {
            "global_protection_value_usd_billion": coeffs.get("global_flood_protection_value_usd_billion", 272),
            "wave_energy_reduction_percent": coeffs.get("wave_energy_reduction_percent", {}).get("healthy_reef", 97)
        }
    elif axiom_id == "BA-005":
        return {
            "global_protection_value_usd_billion": coeffs.get("global_protection_value_usd_billion_yr", 65),
            "value_per_ha_yr_usd": coeffs.get("value_per_ha_yr_mean_usd", 4185)
        }
    elif axiom_id == "BA-006":
        return {
            "value_per_ha_yr_usd": coeffs.get("value_per_ha_yr_median_usd", 37500),
            "species_mangrove_dependent_fraction": coeffs.get("species_proportion_mangrove_dependent", 0.32)
        }
    elif axiom_id == "BA-007":
        return {
            "undisturbed_mg_c_ha": coeffs.get("undisturbed_mg_c_ha", 1023),
            "global_stock_pg_c": coeffs.get("global_stock_pg_c", 6.17)
        }
    elif axiom_id == "BA-008":
        return {
            "conservation_max_revenue_usd_10yr": coeffs.get("conservation_100ha_max_revenue_usd_10yr", 1530000),
            "net_offset_t_co2e_ha_yr": coeffs.get("net_offset_t_co2e_ha_yr", 0.42)
        }
    elif axiom_id == "BA-009":
        bcr_range = coeffs.get("bcr_range", [6.35, 15.0])
        return {
            "bcr_range": bcr_range,
            "global_20yr_net_esv_gain_usd_billion_range": coeffs.get("global_20yr_net_esv_gain_usd_billion", [231, 725])
        }
    elif axiom_id == "BA-010":
        return {
            "global_value_usd_billion_yr": coeffs.get("global_value_usd_billion_yr", 500),
            "value_per_ha_yr_range_usd": coeffs.get("value_per_ha_yr_range_usd", [64400, 147100])
        }
    elif axiom_id == "BA-011":
        return {
            "kelp_recovery_premium_percent": coeffs.get("kelp_recovery_premium_percent", 8.5),
            "coral_disturbance_reduction_percent": coeffs.get("coral_disturbance_impact_reduction_percent", 30)
        }
    elif axiom_id == "BA-012":
        return {
            "productivity_loss_percent": coeffs.get("productivity_loss_at_degradation_percent", 35),
            "loss_range_percent": coeffs.get("productivity_loss_range_percent", [25, 50])
        }

    return coeffs


def transform_sources(sources: list) -> list:
    """Transform source citations to export evidence_sources format."""
    evidence = []
    for i, source in enumerate(sources):
        doi = source.get("doi", "")
        doc_id = DOI_TO_DOC_ID.get(doi, f"unknown_{doi.replace('/', '_').replace('.', '_')}")
        support_type = "primary" if i == 0 else "supporting"
        evidence.append({
            "doc_id": doc_id,
            "doi": doi,
            "support_type": support_type
        })
    return evidence


def generate_formula(axiom_id: str, pattern: str) -> str:
    """Generate simplified formula from pattern."""
    formulas = {
        "BA-001": "tourism_revenue = f(biomass_increase, wtp_curve, infrastructure)",
        "BA-002": "biomass_ratio = f(protection_type, enforcement, age)",
        "BA-003": "carbon_storage = otter_presence * npp_multiplier * kelp_area",
        "BA-004": "flood_protection_value = reef_condition * wave_attenuation * exposure",
        "BA-005": "flood_protection_value = mangrove_area * storm_attenuation",
        "BA-006": "fisheries_value = mangrove_fringe_ha * value_per_ha",
        "BA-007": "carbon_stock = mangrove_condition * carbon_density",
        "BA-008": "carbon_revenue = project_type * area * credit_price",
        "BA-009": "net_benefit = esv_gain - restoration_cost",
        "BA-010": "esv_total = kelp_area * per_ha_value",
        "BA-011": "resilience_multiplier = f(mpa_type, habitat)",
        "BA-012": "fisheries_loss = structural_degradation * productivity_coeff",
    }
    return formulas.get(axiom_id, pattern)


def regenerate_export():
    """Main regeneration function."""

    # Load source schema
    source_path = PROJECT_ROOT / "schemas" / "bridge_axiom_templates.json"
    with open(source_path) as f:
        source = json.load(f)

    print(f"Loaded source schema v{source['version']} ({len(source['axioms'])} axioms)")

    # Transform each axiom
    export_axioms = []
    for axiom in source["axioms"]:
        axiom_id = axiom["axiom_id"]
        category = axiom.get("category", "ecological_to_service")
        domain_from, domain_to = CATEGORY_TO_DOMAINS.get(category, ("ecological", "financial"))

        export_axiom = {
            "axiom_id": axiom_id,
            "name": axiom["name"],
            "domain_from": domain_from,
            "domain_to": domain_to,
            "description": axiom["description"],
            "formula": generate_formula(axiom_id, axiom.get("pattern", "")),
            "coefficients": transform_coefficients(axiom_id, axiom.get("coefficients", {})),
            "evidence_sources": transform_sources(axiom.get("sources", [])),
            "confidence": "high" if axiom.get("evidence_tier") == "T1" else "medium",
            "validation": axiom.get("example_calculation", {}).get("interpretation", "")
        }
        export_axioms.append(export_axiom)
        print(f"  Transformed {axiom_id}: {axiom['name']}")

    # Build export bundle
    export_bundle = {
        "bridge_axioms": export_axioms,
        "export_metadata": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source_version": source["version"],
            "source_updated": source.get("last_updated", "unknown"),
            "axiom_count": len(export_axioms),
            "regeneration_reason": "BA-001 DOI correction and coefficient update"
        }
    }

    # Write export
    export_path = PROJECT_ROOT / "data" / "semantica_export" / "bridge_axioms.json"
    with open(export_path, "w") as f:
        json.dump(export_bundle, f, indent=2)

    print(f"\nExport bundle written to: {export_path}")
    print(f"  Axioms: {len(export_axioms)}")
    print(f"  Generated: {export_bundle['export_metadata']['generated_at']}")

    return export_bundle


if __name__ == "__main__":
    regenerate_export()
