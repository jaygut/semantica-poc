"""Climate scenario engine - SSP-linked degradation curves per habitat type.

Implements forward-looking ESV projections under IPCC SSP scenarios by
interpolating habitat degradation from 2025 (0% loss) through IPCC AR6 WG2 Ch.3
anchor points (2050, 2100) and applying service-specific sensitivity factors.

All degradation anchors sourced from:
- IPCC AR6 WG2 Ch.3 (doi:10.1007/978-3-031-59144-8)
- Nature 2025 (doi:10.1038/s41586-025-09439-4)
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import numpy as np

from maris.scenario.constants import (
    SCENARIO_CONFIDENCE_PENALTIES,
    SERVICE_REEF_SENSITIVITY,
    SSP_SCENARIOS,
)
from maris.scenario.models import (
    PropagationStep,
    ScenarioDelta,
    ScenarioRequest,
    ScenarioResponse,
    ScenarioUncertainty,
)

# ---------------------------------------------------------------------------
# Site data loading (reuse pattern from counterfactual_engine)
# ---------------------------------------------------------------------------

_EXAMPLES_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "examples"

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

# Habitat type aliases: map case study primary_habitat to anchor keys
_HABITAT_ALIAS: dict[str, str] = {
    "coral_reef": "coral_reef",
    "mangrove_forest": "mangrove_forest",
    "seagrass_meadow": "seagrass_meadow",
    "mixed": "mixed",
}

# IPCC AR6 WG2 Ch.3 degradation anchors (fraction of habitat lost)
# Each entry: {year: (low_fraction, high_fraction)}
# 2025 is implicitly (0.0, 0.0) - no additional loss from baseline
_DEGRADATION_ANCHORS: dict[str, dict[str, dict[int, tuple[float, float]]]] = {
    "coral_reef": {
        "SSP1-2.6": {2050: (0.30, 0.50), 2100: (0.70, 0.90)},
        "SSP2-4.5": {2050: (0.50, 0.70), 2100: (0.90, 0.99)},
        "SSP5-8.5": {2050: (0.70, 0.90), 2100: (0.99, 1.00)},
    },
    "mangrove_forest": {
        "SSP1-2.6": {2050: (0.02, 0.08), 2100: (0.08, 0.20)},
        "SSP2-4.5": {2050: (0.05, 0.15), 2100: (0.15, 0.30)},
        "SSP5-8.5": {2050: (0.10, 0.25), 2100: (0.30, 0.55)},
    },
    "seagrass_meadow": {
        "SSP1-2.6": {2050: (0.10, 0.20), 2100: (0.20, 0.40)},
        "SSP2-4.5": {2050: (0.20, 0.35), 2100: (0.35, 0.55)},
        "SSP5-8.5": {2050: (0.35, 0.55), 2100: (0.55, 0.80)},
    },
    "mixed": {
        "SSP1-2.6": {2050: (0.15, 0.30), 2100: (0.35, 0.60)},
        "SSP2-4.5": {2050: (0.25, 0.45), 2100: (0.55, 0.80)},
        "SSP5-8.5": {2050: (0.45, 0.65), 2100: (0.75, 0.95)},
    },
}

# Sites that use "mixed" habitat for climate scenarios
_MIXED_HABITAT_SITES = {"galapagos", "aldabra"}

_BASE_YEAR = 2025


def _find_case_study(site_name: str) -> pathlib.Path | None:
    """Resolve a site name to its case study JSON file path."""
    key = site_name.lower().strip()
    if key in _SITE_FILE_MAP:
        path = _EXAMPLES_DIR / _SITE_FILE_MAP[key]
        if path.exists():
            return path
    for token, filename in _SITE_FILE_MAP.items():
        if token in key:
            path = _EXAMPLES_DIR / filename
            if path.exists():
                return path
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
    """Extract service list from case study JSON."""
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


def _get_habitat_key(site_data: dict, site_name: str) -> str:
    """Determine the habitat key for degradation anchor lookup."""
    key = site_name.lower().strip()
    for mixed_site in _MIXED_HABITAT_SITES:
        if mixed_site in key:
            return "mixed"
    primary = site_data.get("ecological_status", {}).get("primary_habitat", "coral_reef")
    return _HABITAT_ALIAS.get(primary, "coral_reef")


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


# ---------------------------------------------------------------------------
# Interpolation
# ---------------------------------------------------------------------------

def interpolate_degradation(
    ssp: str,
    habitat: str,
    target_year: int,
) -> tuple[float, float]:
    """Linear interpolation between 2025 (0% loss) and IPCC AR6 anchor points.

    Args:
        ssp: SSP scenario label ("SSP1-2.6", "SSP2-4.5", "SSP5-8.5").
        habitat: Habitat key ("coral_reef", "mangrove_forest", "seagrass_meadow", "mixed").
        target_year: Target year for projection (2025-2100).

    Returns:
        (degradation_fraction_low, degradation_fraction_high) - fraction of habitat
        functional capacity lost by target_year. Values in [0.0, 1.0].

    Raises:
        ValueError: If SSP or habitat not recognized.
    """
    if habitat not in _DEGRADATION_ANCHORS:
        raise ValueError(f"Unknown habitat: {habitat}. Expected one of {list(_DEGRADATION_ANCHORS.keys())}")
    if ssp not in _DEGRADATION_ANCHORS[habitat]:
        raise ValueError(f"Unknown SSP: {ssp}. Expected one of {list(_DEGRADATION_ANCHORS[habitat].keys())}")

    anchors = _DEGRADATION_ANCHORS[habitat][ssp]

    if target_year <= _BASE_YEAR:
        return (0.0, 0.0)

    if target_year >= 2100:
        return anchors[2100]

    # Determine which interval we're in: [2025, 2050] or [2050, 2100]
    if target_year <= 2050:
        # Interpolate between 2025 (0, 0) and 2050 anchor
        t = (target_year - _BASE_YEAR) / (2050 - _BASE_YEAR)
        anchor_low, anchor_high = anchors[2050]
        return (t * anchor_low, t * anchor_high)
    else:
        # Interpolate between 2050 anchor and 2100 anchor
        t = (target_year - 2050) / (2100 - 2050)
        a50_low, a50_high = anchors[2050]
        a100_low, a100_high = anchors[2100]
        return (
            a50_low + t * (a100_low - a50_low),
            a50_high + t * (a100_high - a50_high),
        )


# ---------------------------------------------------------------------------
# Climate scenario engine
# ---------------------------------------------------------------------------

def run_climate_scenario(
    scenario_req: ScenarioRequest,
    n_simulations: int = 10_000,
    seed: int = 42,
) -> ScenarioResponse:
    """Compute ESV projection under a specified SSP scenario for target year.

    Loads site data from examples/<site>_case_study.json, interpolates
    habitat degradation for the given SSP and target year, applies
    service-specific sensitivity from SERVICE_REEF_SENSITIVITY, and
    produces uncertainty via triangular Monte Carlo sampling.

    Args:
        scenario_req: Must have ssp_scenario set ("SSP1-2.6" | "SSP2-4.5" | "SSP5-8.5")
                      and target_year (2030 | 2040 | 2050 | 2075 | 2100).
        n_simulations: Number of Monte Carlo samples for uncertainty.
        seed: Random seed for reproducibility.

    Returns:
        ScenarioResponse with baseline and projected ESV, propagation trace,
        and uncertainty. Returns fail-closed response if site data unavailable.
    """
    if not scenario_req.site_scope:
        return _insufficient_evidence_response(scenario_req, "No site specified")

    ssp = scenario_req.ssp_scenario
    target_year = scenario_req.target_year

    if not ssp or ssp not in ("SSP1-2.6", "SSP2-4.5", "SSP5-8.5"):
        return _insufficient_evidence_response(
            scenario_req,
            f"Invalid or missing SSP scenario: {ssp}",
        )

    if not target_year or target_year < _BASE_YEAR:
        return _insufficient_evidence_response(
            scenario_req,
            f"Invalid or missing target year: {target_year}",
        )

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
    habitat_key = _get_habitat_key(site_data, site_name)

    # Interpolate degradation for this SSP/habitat/year
    deg_low, deg_high = interpolate_degradation(ssp, habitat_key, target_year)

    baseline_case: dict[str, Any] = {
        "total_esv_usd": total_esv,
        "services": {s["service_type"]: s["annual_value_usd"] for s in services},
        "site_name": site_canonical,
    }

    trace: list[PropagationStep] = []
    deltas: list[ScenarioDelta] = []
    scenario_services: dict[str, float] = {}
    axioms_used: list[str] = []

    # Record degradation interpolation step
    trace.append(PropagationStep(
        axiom_id="IPCC-AR6-WG2-Ch3",
        description=(
            f"Habitat degradation for {habitat_key} under {ssp} by {target_year}: "
            f"{deg_low:.1%}-{deg_high:.1%} functional capacity loss"
        ),
        input_value=0.0,
        input_parameter="degradation_fraction_2025",
        output_value=(deg_low + deg_high) / 2,
        output_parameter=f"degradation_fraction_{target_year}",
        coefficient=None,
        source_doi="10.1007/978-3-031-59144-8",
    ))

    # Mid-point degradation for deterministic per-service calculation
    deg_mid = (deg_low + deg_high) / 2
    retained_habitat = 1.0 - deg_mid

    for svc in services:
        stype = _normalize_service_type(svc["service_type"])
        baseline_val = svc["annual_value_usd"]

        # Apply service-specific sensitivity: at degradation level,
        # interpolate between full capacity (1.0) and the sensitivity
        # at the corresponding threshold level
        sensitivity = SERVICE_REEF_SENSITIVITY.get(stype)

        if sensitivity is not None:
            # Map degradation fraction to retained ESV fraction using
            # service sensitivity curve. Higher degradation = lower retained.
            # Use linear interpolation across threshold levels.
            service_retained = _interpolate_service_sensitivity(
                retained_habitat, sensitivity,
            )
        else:
            # Non-sensitivity-mapped services: scale linearly with habitat
            service_retained = retained_habitat

        scenario_val = baseline_val * service_retained
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

        axiom_id = f"BA-001-{stype}" if sensitivity else "BA-002"
        if axiom_id not in axioms_used:
            axioms_used.append(axiom_id)

        trace.append(PropagationStep(
            axiom_id=axiom_id,
            description=(
                f"{svc['service_type']}: {service_retained:.1%} retained "
                f"({deg_mid:.1%} habitat degradation, {ssp})"
            ),
            input_value=baseline_val,
            input_parameter=f"baseline_{svc['service_type']}_usd",
            output_value=scenario_val,
            output_parameter=f"scenario_{svc['service_type']}_usd",
            coefficient=service_retained,
            source_doi="10.1007/978-3-031-59144-8",
        ))

    scenario_total = sum(scenario_services.values())
    total_delta = scenario_total - total_esv
    total_pct = (total_delta / total_esv * 100) if total_esv else 0.0

    deltas.append(ScenarioDelta(
        metric="total_esv",
        baseline_value=total_esv,
        scenario_value=scenario_total,
        absolute_change=total_delta,
        percent_change=total_pct,
        unit="USD",
    ))

    scenario_case: dict[str, Any] = {
        "total_esv_usd": scenario_total,
        "services": scenario_services,
        "ssp_scenario": ssp,
        "target_year": target_year,
        "habitat_degradation_mid": deg_mid,
    }

    # Monte Carlo uncertainty using triangular distribution
    uncertainty = _compute_climate_uncertainty(
        services, deg_low, deg_high, habitat_key,
        n_simulations=n_simulations, seed=seed,
    )

    # Confidence with scenario penalties
    confidence, penalties = _compute_scenario_confidence(
        scenario_req, target_year,
    )

    # Validity
    if target_year > 2100:
        validity = "out_of_domain"
    elif target_year > 2050:
        validity = "partially_out_of_domain"
    else:
        validity = "in_domain"

    answer = (
        f"Under {ssp} by {target_year}, {site_canonical} ESV is projected to decline "
        f"from ${total_esv/1e6:.1f}M to ${scenario_total/1e6:.1f}M "
        f"(a {abs(total_pct):.0f}% reduction). "
        f"The {habitat_key.replace('_', ' ')} habitat faces {deg_low:.0%}-{deg_high:.0%} "
        f"functional capacity loss under this pathway."
    )

    caveats = [
        f"Degradation estimates interpolated from IPCC AR6 WG2 Ch.3 anchor points for {habitat_key}",
        "Service-specific sensitivities based on axiom chain analysis - actual impacts may differ",
        f"Confidence penalized for temporal extrapolation ({target_year}) and SSP uncertainty ({ssp})",
    ]

    # Enrich with environmental baseline if available in site data
    env_baselines = site_data.get("environmental_baselines", {})
    sst_baseline = env_baselines.get("sst", {})
    if sst_baseline.get("median_sst_c") is not None:
        ssp_warming = float(SSP_SCENARIOS.get(ssp, {}).get("warming_2100_c", 0))
        # Scale warming by temporal position (linear from 0 at 2025 to full at 2100)
        temporal_fraction = min(1.0, max(0.0, (target_year - _BASE_YEAR) / (2100 - _BASE_YEAR)))
        projected_warming = round(ssp_warming * temporal_fraction, 2)

        from maris.scenario.environmental_baselines import compute_warming_impact
        warming_impact = compute_warming_impact(
            sst_baseline["median_sst_c"],
            projected_warming,
            habitat_key,
        )

        answer += (
            f" Observed SST baseline: {sst_baseline['median_sst_c']}C "
            f"(OBIS, {sst_baseline.get('n_records', 'N/A')} records). "
            f"{warming_impact['confidence_note']}"
        )

        caveats.append(
            "SST baseline derived from OBIS occurrence records, not continuous monitoring"
        )

        trace.append(PropagationStep(
            axiom_id="OBIS-ENV-BASELINE",
            description=(
                f"Observed SST baseline {sst_baseline['median_sst_c']}C, "
                f"projected {warming_impact['projected_sst_c']}C under {ssp} by {target_year}"
            ),
            input_value=sst_baseline["median_sst_c"],
            input_parameter="observed_sst_baseline_c",
            output_value=warming_impact["projected_sst_c"],
            output_parameter="projected_sst_c",
            coefficient=projected_warming,
            source_doi=None,
        ))

    return ScenarioResponse(
        scenario_request=scenario_req,
        baseline_case=baseline_case,
        scenario_case=scenario_case,
        deltas=deltas,
        propagation_trace=trace,
        uncertainty=uncertainty,
        confidence=confidence,
        confidence_penalties=penalties,
        scenario_validity=validity,
        tipping_point_proximity=None,
        answer=answer,
        caveats=caveats,
        axioms_used=axioms_used,
    )


def _interpolate_service_sensitivity(
    retained_habitat: float,
    sensitivity: dict[str, float],
) -> float:
    """Map habitat retained fraction to service ESV retained fraction.

    Uses the SERVICE_REEF_SENSITIVITY thresholds to create a piecewise
    linear mapping from habitat quality to service output.

    Threshold levels correspond to reef function fractions:
      1.00 (pristine) -> warning (0.90) -> mmsy_upper (0.65) ->
      mmsy_lower (0.30) -> collapse (0.05) -> 0.0

    retained_habitat is the fraction of habitat capacity remaining [0, 1].
    """
    # Define breakpoints: (habitat_quality, service_retained)
    breakpoints = [
        (1.00, 1.00),
        (0.90, sensitivity["warning"]),
        (0.65, sensitivity["mmsy_upper"]),
        (0.30, sensitivity["mmsy_lower"]),
        (0.05, sensitivity["collapse"]),
        (0.00, 0.00),
    ]

    if retained_habitat >= 1.0:
        return 1.0
    if retained_habitat <= 0.0:
        return 0.0

    # Find the interval
    for i in range(len(breakpoints) - 1):
        upper_hab, upper_svc = breakpoints[i]
        lower_hab, lower_svc = breakpoints[i + 1]
        if retained_habitat >= lower_hab:
            if upper_hab == lower_hab:
                return upper_svc
            t = (retained_habitat - lower_hab) / (upper_hab - lower_hab)
            return lower_svc + t * (upper_svc - lower_svc)

    return 0.0


def _compute_climate_uncertainty(
    services: list[dict],
    deg_low: float,
    deg_high: float,
    habitat_key: str,
    n_simulations: int = 10_000,
    seed: int = 42,
) -> ScenarioUncertainty:
    """Triangular distribution uncertainty over degradation range.

    Samples degradation fraction from triangular(deg_low, midpoint, deg_high)
    and computes total ESV for each sample.
    """
    rng = np.random.default_rng(seed)

    if deg_low >= deg_high or deg_high <= 0:
        total_baseline = sum(s["annual_value_usd"] for s in services)
        return ScenarioUncertainty(
            p5=total_baseline,
            p50=total_baseline,
            p95=total_baseline,
            dominant_driver=habitat_key,
            n_simulations=n_simulations,
        )

    deg_mode = (deg_low + deg_high) / 2
    deg_samples = rng.triangular(deg_low, deg_mode, deg_high, size=n_simulations)

    total_baseline = sum(s["annual_value_usd"] for s in services)
    esv_samples = np.zeros(n_simulations)

    for svc in services:
        stype = _normalize_service_type(svc["service_type"])
        baseline_val = svc["annual_value_usd"]
        sensitivity = SERVICE_REEF_SENSITIVITY.get(stype)

        for i in range(n_simulations):
            retained = 1.0 - deg_samples[i]
            if sensitivity is not None:
                svc_retained = _interpolate_service_sensitivity(retained, sensitivity)
            else:
                svc_retained = retained
            esv_samples[i] += baseline_val * svc_retained

    return ScenarioUncertainty(
        p5=float(np.percentile(esv_samples, 5)),
        p50=float(np.percentile(esv_samples, 50)),
        p95=float(np.percentile(esv_samples, 95)),
        dominant_driver=habitat_key,
        n_simulations=n_simulations,
    )


def _compute_scenario_confidence(
    scenario_req: ScenarioRequest,
    target_year: int,
) -> tuple[float, list[dict[str, Any]]]:
    """Compute scenario confidence with temporal and SSP penalties."""
    base = 0.85
    penalties: list[dict[str, Any]] = []

    # Temporal extrapolation penalty
    decades_out = max(0, (target_year - _BASE_YEAR) / 10)
    temporal_penalty = min(
        decades_out * SCENARIO_CONFIDENCE_PENALTIES["temporal_extrapolation"]["penalty_per_decade"],
        SCENARIO_CONFIDENCE_PENALTIES["temporal_extrapolation"]["max_penalty"],
    )
    base -= temporal_penalty
    penalties.append({
        "reason": f"temporal_extrapolation_{target_year}",
        "penalty": -temporal_penalty,
    })

    # SSP uncertainty penalty
    ssp = scenario_req.ssp_scenario
    if ssp:
        ssp_penalty = SCENARIO_CONFIDENCE_PENALTIES["ssp_uncertainty"].get(ssp, 0.10)
        base -= ssp_penalty
        penalties.append({
            "reason": f"ssp_scenario_uncertainty_{ssp}",
            "penalty": -ssp_penalty,
        })

    return max(0.10, base), penalties


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
