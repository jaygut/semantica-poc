"""Bridge axiom registry - loads 16 axioms from JSON and builds TranslationChains."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from maris.provenance.bridge_axiom import BridgeAxiom, TranslationChain

logger = logging.getLogger(__name__)


def _extract_primary_coefficient(coefficients: dict[str, Any]) -> float:
    """Extract the most representative numeric coefficient from an axiom's coefficients dict.

    Looks for common patterns: value dicts, scalar floats, or named primary keys.
    """
    # Priority keys that represent the main coefficient
    priority_keys = [
        "sequestration_rate_tCO2_ha_yr",
        "price_per_tCO2_usd",
        "emission_factor_tCO2_per_ha",
        "permanence_years",
        "biomass_ratio_vs_unprotected",
        "npp_multiplier",
        "global_flood_protection_value_usd_billion",
        "global_protection_value_usd_billion_yr",
        "value_per_ha_yr_median_usd",
        "undisturbed_mg_c_ha",
        "carbon_credit_range_usd_per_ha",
        "global_value_usd_billion_yr",
        "kelp_recovery_premium_percent",
        "productivity_loss_at_degradation_percent",
        "wtp_increase_for_biomass_max_percent",
    ]

    for key in priority_keys:
        val = coefficients.get(key)
        if val is not None:
            if isinstance(val, dict) and "value" in val:
                return float(val["value"])
            if isinstance(val, (int, float)):
                return float(val)

    # Fallback: first numeric-valued coefficient
    for val in coefficients.values():
        if isinstance(val, dict) and "value" in val:
            return float(val["value"])
        if isinstance(val, (int, float)):
            return float(val)

    return 0.0


def _extract_primary_bounds(coefficients: dict[str, Any]) -> tuple[float | None, float | None]:
    """Extract ci_low and ci_high from the primary coefficient."""
    priority_keys = [
        "sequestration_rate_tCO2_ha_yr",
        "price_per_tCO2_usd",
        "emission_factor_tCO2_per_ha",
        "permanence_years",
        "biomass_ratio_vs_unprotected",
        "npp_multiplier",
        "wtp_increase_for_biomass_max_percent",
    ]

    for key in priority_keys:
        val = coefficients.get(key)
        if isinstance(val, dict) and "ci_low" in val and "ci_high" in val:
            return (float(val["ci_low"]), float(val["ci_high"]))

    # Fallback
    for val in coefficients.values():
        if isinstance(val, dict) and "ci_low" in val and "ci_high" in val:
            return (float(val["ci_low"]), float(val["ci_high"]))

    return (None, None)


class BridgeAxiomRegistry:
    """Load bridge axioms from JSON templates and evidence files.

    Converts the raw JSON data into BridgeAxiom objects and provides
    lookup, filtering, and chain-building operations.
    """

    def __init__(
        self,
        templates_path: Path | str | None = None,
        evidence_path: Path | str | None = None,
    ) -> None:
        self._axioms: dict[str, BridgeAxiom] = {}

        if templates_path is not None:
            self.load(Path(templates_path), Path(evidence_path) if evidence_path else None)

    def load(self, templates_path: Path, evidence_path: Path | None = None) -> int:
        """Load axioms from JSON files.

        Returns the number of axioms loaded.
        """
        with open(templates_path) as f:
            templates_data = json.load(f)

        evidence_lookup: dict[str, dict[str, Any]] = {}
        if evidence_path and evidence_path.exists():
            with open(evidence_path) as f:
                evidence_data = json.load(f)
            for ax in evidence_data.get("bridge_axioms", []):
                evidence_lookup[ax["axiom_id"]] = ax

        for axiom_raw in templates_data.get("axioms", []):
            aid = axiom_raw["axiom_id"]
            evidence = evidence_lookup.get(aid, {})
            coefficients = axiom_raw.get("coefficients", {})

            primary_coeff = _extract_primary_coefficient(coefficients)
            ci_low, ci_high = _extract_primary_bounds(coefficients)

            # Build evidence sources list
            evidence_sources = []
            for src in axiom_raw.get("sources", []):
                evidence_sources.append({
                    "doi": src.get("doi", ""),
                    "citation": src.get("citation", ""),
                    "finding": src.get("finding", ""),
                })

            primary_doi = ""
            if evidence_sources:
                primary_doi = evidence_sources[0].get("doi", "")

            ba = BridgeAxiom(
                axiom_id=aid,
                name=axiom_raw.get("name", ""),
                rule=axiom_raw.get("pattern", ""),
                coefficient=primary_coeff,
                input_domain=evidence.get("domain_from", axiom_raw.get("category", "").split("_to_")[0] if "_to_" in axiom_raw.get("category", "") else ""),
                output_domain=evidence.get("domain_to", axiom_raw.get("category", "").split("_to_")[-1] if "_to_" in axiom_raw.get("category", "") else ""),
                source_doi=primary_doi,
                source_page="",
                source_quote=evidence_sources[0].get("finding", "") if evidence_sources else "",
                confidence=evidence.get("confidence", "high"),
                ci_low=ci_low,
                ci_high=ci_high,
                applicable_habitats=axiom_raw.get("applicable_habitats", []),
                evidence_sources=evidence_sources,
                caveats=axiom_raw.get("caveats", []),
            )
            self._axioms[aid] = ba

        count = len(self._axioms)
        logger.info("Loaded %d bridge axioms from %s", count, templates_path)
        return count

    # -- Lookup ---------------------------------------------------------------

    def get(self, axiom_id: str) -> BridgeAxiom | None:
        """Return a BridgeAxiom by ID, or None."""
        return self._axioms.get(axiom_id)

    def get_all(self) -> list[BridgeAxiom]:
        """Return all loaded axioms."""
        return list(self._axioms.values())

    def get_by_habitat(self, habitat: str) -> list[BridgeAxiom]:
        """Return axioms applicable to a specific habitat."""
        return [
            a for a in self._axioms.values()
            if "all" in a.applicable_habitats or habitat in a.applicable_habitats
        ]

    def get_by_domain(self, input_domain: str | None = None, output_domain: str | None = None) -> list[BridgeAxiom]:
        """Return axioms filtered by input and/or output domain."""
        results = list(self._axioms.values())
        if input_domain:
            results = [a for a in results if a.input_domain == input_domain]
        if output_domain:
            results = [a for a in results if a.output_domain == output_domain]
        return results

    def count(self) -> int:
        """Return the number of loaded axioms."""
        return len(self._axioms)

    # -- Chain building -------------------------------------------------------

    def build_chain(self, axiom_ids: list[str]) -> TranslationChain:
        """Build a TranslationChain from a sequence of axiom IDs.

        Raises ValueError if any axiom ID is not found.
        """
        axioms: list[BridgeAxiom] = []
        for aid in axiom_ids:
            ba = self._axioms.get(aid)
            if ba is None:
                raise ValueError(f"Axiom {aid} not found in registry")
            axioms.append(ba)
        return TranslationChain(axioms)
