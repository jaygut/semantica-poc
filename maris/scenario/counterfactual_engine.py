"""Counterfactual scenario engine.

Computes 'what would this site be worth without protection?' by reverting
key ecological parameters to pre-protection baselines and propagating
through bridge axiom chains.

Runs without Neo4j in under 5 seconds using case study JSON data.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import numpy as np

from maris.scenario.constants import (
    SCENARIO_CONFIDENCE_PENALTIES,
    SERVICE_REEF_SENSITIVITY,
)
from maris.scenario.models import (
    PropagationStep,
    ScenarioDelta,
    ScenarioRequest,
    ScenarioResponse,
    ScenarioUncertainty,
)

# ---------------------------------------------------------------------------
# Site data loading
# ---------------------------------------------------------------------------

_EXAMPLES_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "examples"

# Mapping from common site name tokens to case study JSON filenames
_SITE_FILE_MAP: dict[str, str] = {
    "cabo_pulmo": "cabo_pulmo_case_study.json",
    "cabo pulmo": "cabo_pulmo_case_study.json",
    "shark_bay": "shark_bay_case_study.json",
    "shark bay": "shark_bay_case_study.json",
    "sundarbans": "sundarbans_case_study.json",
    "ningaloo": "ningaloo_case_study.json",
    "belize": "belize_barrier_reef_case_study.json",
    "raja_ampat": "raja_ampat_case_study.json",
    "raja ampat": "raja_ampat_case_study.json",
    "galapagos": "galapagos_case_study.json",
    "aldabra": "aldabra_case_study.json",
    "cispata": "cispata_bay_case_study.json",
    "cispata_bay": "cispata_bay_case_study.json",
    "cispata bay": "cispata_bay_case_study.json",
}

# Pre-protection biomass baseline for overfished Mexican reefs (kg/ha)
# Aburto-Oropeza et al. 2011 (doi:10.1371/journal.pone.0023601)
_CABO_PULMO_PRE_PROTECTION_BIOMASS_KG_HA = 200.0


def _find_case_study(site_name: str) -> pathlib.Path | None:
    """Resolve a site name to its case study JSON file path."""
    key = site_name.lower().strip()
    # Direct lookup
    if key in _SITE_FILE_MAP:
        path = _EXAMPLES_DIR / _SITE_FILE_MAP[key]
        if path.exists():
            return path
    # Fuzzy: check if any key is contained in the site name
    for token, filename in _SITE_FILE_MAP.items():
        if token in key:
            path = _EXAMPLES_DIR / filename
            if path.exists():
                return path
    # Pattern scan: try <site>_case_study.json
    slug = key.replace(" ", "_")
    for candidate in _EXAMPLES_DIR.glob("*_case_study.json"):
        if slug in candidate.stem:
            return candidate
    return None


def _load_site_data(site_name: str) -> dict | None:
    """Load and return parsed case study JSON for a site."""
    path = _find_case_study(site_name)
    if path is None:
        return None
    with open(path) as f:
        return json.load(f)


def _extract_services(site_data: dict) -> list[dict]:
    """Extract service list from case study JSON.

    Returns list of dicts with keys: service_type, annual_value_usd,
    valuation_method, ci_low, ci_high.
    """
    es = site_data.get("ecosystem_services", {})
    services = es.get("services", [])
    result = []
    for svc in services:
        ci = svc.get("confidence_interval", {})
        result.append({
            "service_type": svc.get("service_type", "unknown"),
            "annual_value_usd": svc.get("annual_value_usd", 0),
            "valuation_method": svc.get("valuation_method", "unknown"),
            "ci_low": ci.get("ci_low", svc.get("annual_value_usd", 0) * 0.8),
            "ci_high": ci.get("ci_high", svc.get("annual_value_usd", 0) * 1.2),
        })
    return result


def _get_total_esv(site_data: dict) -> float:
    """Extract total ESV from case study JSON."""
    es = site_data.get("ecosystem_services", {})
    return float(es.get("total_annual_value_usd", 0))


# ---------------------------------------------------------------------------
# Site-specific counterfactual logic
# ---------------------------------------------------------------------------

def _normalize_service_type(stype: str) -> str:
    """Map service type variants to SERVICE_REEF_SENSITIVITY keys."""
    mapping = {
        "tourism": "tourism",
        "ecotourism": "tourism",
        "fisheries": "fisheries",
        "fisheries_spillover": "fisheries",
        "carbon_sequestration": "carbon_sequestration",
        "coastal_protection": "coastal_protection",
    }
    return mapping.get(stype, stype)


def _cabo_pulmo_counterfactual(
    site_data: dict,
    services: list[dict],
) -> tuple[dict, list[PropagationStep], list[ScenarioDelta], str]:
    """Cabo Pulmo: revert biomass_multiplier from 4.63x to 1.0x.

    At 1.0x biomass (~200 kg/ha), the reef is at the mmsy_lower threshold
    zone per McClanahan et al. 2011 (doi:10.1073/pnas.1106861108).
    Apply SERVICE_REEF_SENSITIVITY at mmsy_lower level.

    Validation anchor: scenario ESV in [$3M, $12M], delta in [-$26M, -$18M].
    """
    recovery = site_data.get("ecological_recovery", {})
    biomass_ratio = recovery.get("metrics", {}).get("fish_biomass", {}).get("recovery_ratio", 4.63)
    pre_protection_biomass = _CABO_PULMO_PRE_PROTECTION_BIOMASS_KG_HA
    current_biomass = pre_protection_biomass * biomass_ratio  # ~926 kg/ha
    counterfactual_biomass = pre_protection_biomass  # 200 kg/ha (1.0x)

    trace = []
    deltas = []
    scenario_services: dict[str, float] = {}

    trace.append(PropagationStep(
        axiom_id="BA-002",
        description=(
            f"Revert biomass from {biomass_ratio:.2f}x ({current_biomass:.0f} kg/ha) "
            f"to 1.0x ({counterfactual_biomass:.0f} kg/ha) - pre-protection baseline"
        ),
        input_value=biomass_ratio,
        input_parameter="biomass_multiplier",
        output_value=1.0,
        output_parameter="biomass_multiplier_counterfactual",
        coefficient=1.0 / biomass_ratio,
        source_doi="10.1371/journal.pone.0023601",
    ))

    for svc in services:
        stype = _normalize_service_type(svc["service_type"])
        baseline_val = svc["annual_value_usd"]
        sensitivity = SERVICE_REEF_SENSITIVITY.get(stype)

        if sensitivity is not None:
            # At 200 kg/ha (between collapse=150 and mmsy_lower=300),
            # use mmsy_lower retained fraction per PRD specification
            # McClanahan et al. 2011 (doi:10.1073/pnas.1106861108)
            retained = sensitivity["mmsy_lower"]
        else:
            # Non-reef services: generic 40% retention without protection
            retained = 0.40

        scenario_val = baseline_val * retained
        scenario_services[svc["service_type"]] = scenario_val

        delta_val = scenario_val - baseline_val
        pct_change = (delta_val / baseline_val * 100) if baseline_val else 0.0

        deltas.append(ScenarioDelta(
            metric=svc["service_type"],
            baseline_value=baseline_val,
            scenario_value=scenario_val,
            absolute_change=delta_val,
            percent_change=pct_change,
            unit="USD",
        ))

        trace.append(PropagationStep(
            axiom_id="BA-001",
            description=(
                f"{svc['service_type']}: {retained:.0%} retained at mmsy_lower "
                f"threshold ({counterfactual_biomass:.0f} kg/ha)"
            ),
            input_value=baseline_val,
            input_parameter=f"baseline_{svc['service_type']}_usd",
            output_value=scenario_val,
            output_parameter=f"scenario_{svc['service_type']}_usd",
            coefficient=retained,
            source_doi="10.1073/pnas.1106861108",
        ))

    scenario_total = sum(scenario_services.values())
    scenario_case = {
        "total_esv_usd": scenario_total,
        "services": scenario_services,
        "biomass_multiplier": 1.0,
        "biomass_kg_ha": counterfactual_biomass,
    }

    tipping_msg = (
        f"At {counterfactual_biomass:.0f} kg/ha, Cabo Pulmo would be between "
        f"collapse (150 kg/ha) and mmsy_lower (300 kg/ha) thresholds - "
        f"multiple ecosystem metrics degrading simultaneously"
    )

    return scenario_case, trace, deltas, tipping_msg


def _shark_bay_counterfactual(
    site_data: dict,
    services: list[dict],
) -> tuple[dict, list[PropagationStep], list[ScenarioDelta], str | None]:
    """Shark Bay: revert seagrass to 10% of current extent.

    Based on 2011 marine heatwave observed minimum.
    Arias-Ortiz et al. 2018 (doi:10.1038/s41558-018-0096-y).
    """
    retained_fraction = 0.10  # Post-2011-heatwave observed minimum

    trace = []
    deltas = []
    scenario_services: dict[str, float] = {}

    trace.append(PropagationStep(
        axiom_id="BA-015",
        description=(
            "Revert seagrass extent to 10% of current - "
            "2011 marine heatwave observed minimum"
        ),
        input_value=1.0,
        input_parameter="seagrass_extent_fraction",
        output_value=retained_fraction,
        output_parameter="seagrass_extent_fraction_counterfactual",
        coefficient=retained_fraction,
        source_doi="10.1038/s41558-018-0096-y",
    ))

    for svc in services:
        baseline_val = svc["annual_value_usd"]
        scenario_val = baseline_val * retained_fraction
        scenario_services[svc["service_type"]] = scenario_val

        delta_val = scenario_val - baseline_val
        pct_change = (delta_val / baseline_val * 100) if baseline_val else 0.0

        deltas.append(ScenarioDelta(
            metric=svc["service_type"],
            baseline_value=baseline_val,
            scenario_value=scenario_val,
            absolute_change=delta_val,
            percent_change=pct_change,
            unit="USD",
        ))

        trace.append(PropagationStep(
            axiom_id="BA-013",
            description=f"{svc['service_type']}: scaled to {retained_fraction:.0%} of current (seagrass loss)",
            input_value=baseline_val,
            input_parameter=f"baseline_{svc['service_type']}_usd",
            output_value=scenario_val,
            output_parameter=f"scenario_{svc['service_type']}_usd",
            coefficient=retained_fraction,
            source_doi="10.1038/s41558-018-0096-y",
        ))

    scenario_total = sum(scenario_services.values())
    scenario_case = {
        "total_esv_usd": scenario_total,
        "services": scenario_services,
        "seagrass_extent_fraction": retained_fraction,
    }

    return scenario_case, trace, deltas, None


def _sundarbans_counterfactual(
    site_data: dict,
    services: list[dict],
) -> tuple[dict, list[PropagationStep], list[ScenarioDelta], str | None]:
    """Sundarbans: full deforestation scenario.

    carbon_sequestration -> 0, coastal_protection -> 30% (remnant buffer).
    Other services scale by 0.15 (severe degradation).
    Sani et al. 2022 (doi:10.1038/s41598-022-11716-5).
    """
    trace = []
    deltas = []
    scenario_services: dict[str, float] = {}

    trace.append(PropagationStep(
        axiom_id="BA-007",
        description="Full deforestation scenario: mangrove carbon stock eliminated",
        input_value=1.0,
        input_parameter="mangrove_extent_fraction",
        output_value=0.0,
        output_parameter="mangrove_extent_fraction_counterfactual",
        coefficient=0.0,
        source_doi="10.1038/s41598-022-11716-5",
    ))

    for svc in services:
        baseline_val = svc["annual_value_usd"]
        stype = svc["service_type"]

        if stype == "carbon_sequestration":
            retained = 0.0  # No mangrove = no sequestration
        elif stype == "coastal_protection":
            retained = 0.30  # Remnant buffer (non-mangrove coastline features)
        elif stype == "fisheries":
            retained = 0.20  # Severe nursery habitat loss
        else:
            retained = 0.15  # Severe degradation

        scenario_val = baseline_val * retained
        scenario_services[stype] = scenario_val

        delta_val = scenario_val - baseline_val
        pct_change = (delta_val / baseline_val * 100) if baseline_val else 0.0

        deltas.append(ScenarioDelta(
            metric=stype,
            baseline_value=baseline_val,
            scenario_value=scenario_val,
            absolute_change=delta_val,
            percent_change=pct_change,
            unit="USD",
        ))

        axiom = "BA-005" if stype == "coastal_protection" else "BA-006" if stype == "fisheries" else "BA-007"
        trace.append(PropagationStep(
            axiom_id=axiom,
            description=f"{stype}: {retained:.0%} retained under full deforestation",
            input_value=baseline_val,
            input_parameter=f"baseline_{stype}_usd",
            output_value=scenario_val,
            output_parameter=f"scenario_{stype}_usd",
            coefficient=retained,
            source_doi="10.1038/s41598-022-11716-5",
        ))

    scenario_total = sum(scenario_services.values())
    scenario_case = {
        "total_esv_usd": scenario_total,
        "services": scenario_services,
        "mangrove_loss_scenario": "full_deforestation",
    }

    return scenario_case, trace, deltas, None


def _generic_counterfactual(
    site_data: dict,
    services: list[dict],
    site_name: str,
) -> tuple[dict, list[PropagationStep], list[ScenarioDelta], str | None]:
    """Generic protection removal: 40% of current ESV retained (conservative).

    Applied when no site-specific counterfactual model exists.
    """
    retained = 0.40

    trace = []
    deltas = []
    scenario_services: dict[str, float] = {}

    trace.append(PropagationStep(
        axiom_id="BA-002",
        description=f"Generic protection removal for {site_name}: 40% ESV retained (conservative estimate)",
        input_value=1.0,
        input_parameter="protection_status",
        output_value=retained,
        output_parameter="esv_retention_fraction",
        coefficient=retained,
        source_doi="10.1038/nature13022",
    ))

    for svc in services:
        baseline_val = svc["annual_value_usd"]
        scenario_val = baseline_val * retained
        scenario_services[svc["service_type"]] = scenario_val

        delta_val = scenario_val - baseline_val
        pct_change = (delta_val / baseline_val * 100) if baseline_val else 0.0

        deltas.append(ScenarioDelta(
            metric=svc["service_type"],
            baseline_value=baseline_val,
            scenario_value=scenario_val,
            absolute_change=delta_val,
            percent_change=pct_change,
            unit="USD",
        ))

    scenario_total = sum(scenario_services.values())
    scenario_case = {
        "total_esv_usd": scenario_total,
        "services": scenario_services,
        "protection_removal_fraction": retained,
    }

    return scenario_case, trace, deltas, None


# ---------------------------------------------------------------------------
# Monte Carlo uncertainty quantification
# ---------------------------------------------------------------------------

def _compute_uncertainty(
    total_delta: float,
    n_simulations: int = 10_000,
    seed: int = 42,
    dominant_driver: str = "unknown",
) -> ScenarioUncertainty:
    """Triangular distribution uncertainty over the delta.

    Min = 0.8 * delta, mode = delta, max = 1.2 * delta.
    """
    rng = np.random.default_rng(seed)

    # Delta is negative for counterfactuals (scenario < baseline)
    # Use absolute delta for triangular sampling, then restore sign
    abs_delta = abs(total_delta)
    if abs_delta < 1.0:
        return ScenarioUncertainty(
            p5=total_delta,
            p50=total_delta,
            p95=total_delta,
            dominant_driver=dominant_driver,
            n_simulations=n_simulations,
        )

    low = 0.8 * abs_delta
    mode = abs_delta
    high = 1.2 * abs_delta

    samples = rng.triangular(low, mode, high, size=n_simulations)

    # Restore sign (negative for counterfactual losses)
    sign = -1.0 if total_delta < 0 else 1.0
    samples = sign * samples

    return ScenarioUncertainty(
        p5=float(np.percentile(samples, 5)),
        p50=float(np.percentile(samples, 50)),
        p95=float(np.percentile(samples, 95)),
        dominant_driver=dominant_driver,
        n_simulations=n_simulations,
    )


# ---------------------------------------------------------------------------
# Confidence computation
# ---------------------------------------------------------------------------

def _compute_confidence(
    site_name: str,
    scenario_req: ScenarioRequest,
    has_site_specific_model: bool,
) -> tuple[float, list[dict[str, Any]]]:
    """Compute scenario confidence with penalty log.

    Base confidence 0.85 for counterfactual scenarios.
    """
    base = 0.85
    penalties: list[dict[str, Any]] = []

    if not has_site_specific_model:
        penalty = SCENARIO_CONFIDENCE_PENALTIES["missing_site_calibration"]["penalty"]
        base -= penalty
        penalties.append({
            "reason": "missing_site_calibration",
            "penalty": -penalty,
        })

    return max(0.10, base), penalties


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_counterfactual(scenario_req: ScenarioRequest) -> ScenarioResponse:
    """Run a counterfactual scenario: 'What would this site be worth without protection?'

    Loads site data from examples/<site>_case_study.json and applies
    site-specific counterfactual logic based on bridge axiom chains.

    Args:
        scenario_req: ScenarioRequest with scenario_type='counterfactual'
            and at least one site in site_scope.

    Returns:
        ScenarioResponse with baseline and counterfactual ESV, propagation
        trace, uncertainty, and confidence. Returns fail-closed response
        with insufficient_scenario_evidence if site data is not available.
    """
    if not scenario_req.site_scope:
        return _insufficient_evidence_response(scenario_req, "No site specified")

    site_name = scenario_req.site_scope[0]
    site_data = _load_site_data(site_name)

    if site_data is None:
        return _insufficient_evidence_response(
            scenario_req,
            f"No case study data available for '{site_name}'",
        )

    services = _extract_services(site_data)
    total_esv = _get_total_esv(site_data)
    site_canonical = site_data.get("site", {}).get("name", site_name)

    baseline_case: dict[str, Any] = {
        "total_esv_usd": total_esv,
        "services": {s["service_type"]: s["annual_value_usd"] for s in services},
        "site_name": site_canonical,
    }

    # Dispatch to site-specific counterfactual
    key = site_name.lower().strip()
    has_site_specific = False
    tipping_msg: str | None = None

    if "cabo" in key or "pulmo" in key:
        scenario_case, trace, deltas, tipping_msg = _cabo_pulmo_counterfactual(site_data, services)
        has_site_specific = True
        dominant_driver = "biomass_tourism_chain"
        axioms_used = ["BA-001", "BA-002"]
    elif "shark" in key or "bay" in key and "cispata" not in key:
        scenario_case, trace, deltas, tipping_msg = _shark_bay_counterfactual(site_data, services)
        has_site_specific = True
        dominant_driver = "seagrass_extent"
        axioms_used = ["BA-013", "BA-015"]
    elif "sundarban" in key:
        scenario_case, trace, deltas, tipping_msg = _sundarbans_counterfactual(site_data, services)
        has_site_specific = True
        dominant_driver = "mangrove_deforestation"
        axioms_used = ["BA-005", "BA-006", "BA-007"]
    else:
        scenario_case, trace, deltas, tipping_msg = _generic_counterfactual(site_data, services, site_canonical)
        dominant_driver = "generic_protection_removal"
        axioms_used = ["BA-002"]

    scenario_total = scenario_case["total_esv_usd"]
    total_delta = scenario_total - total_esv

    # Add total delta
    total_pct = (total_delta / total_esv * 100) if total_esv else 0.0
    deltas.append(ScenarioDelta(
        metric="total_esv",
        baseline_value=total_esv,
        scenario_value=scenario_total,
        absolute_change=total_delta,
        percent_change=total_pct,
        unit="USD",
    ))

    uncertainty = _compute_uncertainty(
        total_delta,
        dominant_driver=dominant_driver,
    )

    confidence, penalties = _compute_confidence(
        site_name, scenario_req, has_site_specific,
    )

    # Generate narrative answer
    delta_m = abs(total_delta) / 1e6
    baseline_m = total_esv / 1e6
    scenario_m = scenario_total / 1e6
    answer = (
        f"Without protection, {site_canonical} ESV would decline from "
        f"${baseline_m:.1f}M to an estimated ${scenario_m:.1f}M - "
        f"a loss of ${delta_m:.1f}M ({abs(total_pct):.0f}%). "
        f"This demonstrates that protection generates approximately "
        f"${delta_m:.1f}M in annual ecosystem service value."
    )

    caveats = [
        "Counterfactual assumes complete removal of protection measures",
        "Actual degradation trajectory would depend on local pressures and management alternatives",
        "Ecosystem service losses may not be linear with ecological degradation",
    ]
    if not has_site_specific:
        caveats.append(
            "Generic 40% retention model used - no site-specific counterfactual calibration available"
        )

    return ScenarioResponse(
        scenario_request=scenario_req,
        baseline_case=baseline_case,
        scenario_case=scenario_case,
        deltas=deltas,
        propagation_trace=trace,
        uncertainty=uncertainty,
        confidence=confidence,
        confidence_penalties=penalties,
        scenario_validity="in_domain" if has_site_specific else "partially_out_of_domain",
        tipping_point_proximity=tipping_msg,
        answer=answer,
        caveats=caveats,
        axioms_used=axioms_used,
    )


def _insufficient_evidence_response(
    scenario_req: ScenarioRequest,
    reason: str,
) -> ScenarioResponse:
    """Fail-closed response when data is insufficient."""
    return ScenarioResponse(
        scenario_request=scenario_req,
        baseline_case={},
        scenario_case={},
        deltas=[],
        propagation_trace=[],
        uncertainty=ScenarioUncertainty(
            p5=0.0, p50=0.0, p95=0.0,
            dominant_driver="insufficient_data",
            n_simulations=0,
        ),
        confidence=0.0,
        confidence_penalties=[{"reason": "insufficient_scenario_evidence", "penalty": -1.0}],
        scenario_validity="out_of_domain",
        tipping_point_proximity=None,
        answer=f"Insufficient scenario evidence: {reason}",
        caveats=[reason],
        axioms_used=[],
    )
