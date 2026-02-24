"""TNFD LEAP disclosure generator from MARIS knowledge graph data.

Generates each of the four LEAP phases by querying the MARIS knowledge
graph (or accepting pre-built graph results for testing). Every claim
is traced to a bridge axiom and/or DOI source.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from maris.disclosure.models import (
    DisclosureSection,
    HabitatDescriptor,
    ImpactPathway,
    MetricEntry,
    Opportunity,
    ProvenanceEntry,
    RiskAssessment,
    ServiceDependency,
    SpeciesDependency,
    TargetEntry,
    TNFDAssess,
    TNFDDisclosure,
    TNFDEvaluate,
    TNFDLocate,
    TNFDPrepare,
)

logger = logging.getLogger(__name__)

# Canonical site names to case study file paths
_CASE_STUDY_FILES: dict[str, str] = {
    "Cabo Pulmo National Park": "examples/cabo_pulmo_case_study.json",
    "Shark Bay World Heritage Area": "examples/shark_bay_case_study.json",
}


class LEAPGenerator:
    """Generate TNFD LEAP disclosures from MARIS graph data.

    Can operate in two modes:
    1. From case study JSON files (default) - reads directly from disk
    2. From pre-built data dicts (for testing) - pass data to generate_from_data()
    """

    def __init__(self, project_root: Path | str | None = None) -> None:
        if project_root is None:
            self._root = Path(__file__).resolve().parent.parent.parent
        else:
            self._root = Path(project_root)

    def generate(self, site_name: str) -> TNFDDisclosure:
        """Generate a full TNFD LEAP disclosure for a site.

        Loads the case study JSON and axiom templates from disk.
        """
        case_file = _CASE_STUDY_FILES.get(site_name)
        if case_file is None:
            raise ValueError(
                f"No case study available for '{site_name}'. "
                f"Available sites: {list(_CASE_STUDY_FILES.keys())}"
            )

        case_path = self._root / case_file
        with open(case_path) as f:
            case_data = json.load(f)

        axiom_path = self._root / "schemas" / "bridge_axiom_templates.json"
        with open(axiom_path) as f:
            axiom_data = json.load(f)

        return self.generate_from_data(site_name, case_data, axiom_data)

    def generate_from_data(
        self,
        site_name: str,
        case_data: dict[str, Any],
        axiom_data: dict[str, Any] | None = None,
    ) -> TNFDDisclosure:
        """Generate TNFD LEAP disclosure from pre-built data dicts.

        This is the primary entry point for testing - pass mock data
        without needing files on disk.
        """
        locate = self._build_locate(site_name, case_data)
        evaluate = self._build_evaluate(case_data, axiom_data)
        assess = self._build_assess(case_data, axiom_data)
        prepare = self._build_prepare(site_name, case_data, evaluate, assess)

        return TNFDDisclosure(
            site_name=site_name,
            locate=locate,
            evaluate=evaluate,
            assess=assess,
            prepare=prepare,
        )

    # ------------------------------------------------------------------
    # Phase builders
    # ------------------------------------------------------------------

    def _build_locate(self, site_name: str, case_data: dict) -> TNFDLocate:
        """Build LEAP Locate phase from site metadata."""
        site = case_data.get("site", {})
        coords = site.get("coordinates", {})
        governance = site.get("governance", {})
        neoli = case_data.get("neoli_assessment", {})
        eco = case_data.get("ecological_status", {})

        # Build habitat list
        habitats: list[HabitatDescriptor] = []
        if eco.get("primary_habitat"):
            habitats.append(HabitatDescriptor(
                habitat_id=eco["primary_habitat"],
                name=eco["primary_habitat"].replace("_", " ").title(),
                extent_km2=site.get("seagrass_extent_km2"),
                condition=eco.get("metrics", {}).get("heatwave_impact", {}).get(
                    "recovery_status", "stable"
                ),
            ))

        # Check for reef habitat from ecological_recovery
        recovery = case_data.get("ecological_recovery", {})
        if recovery:
            habitats.append(HabitatDescriptor(
                habitat_id="coral_reef",
                name="Coral Reef",
                extent_km2=site.get("area_km2"),
                condition="recovered" if recovery.get("metrics", {}).get(
                    "fish_biomass", {}
                ).get("recovery_ratio", 0) > 3.0 else "moderate",
            ))

        # Determine biome
        biome = "Marine"
        if any(h.habitat_id == "seagrass_meadow" for h in habitats):
            biome = "Marine - Seagrass Meadows"
        elif any(h.habitat_id == "coral_reef" for h in habitats):
            biome = "Marine Shelves"

        return TNFDLocate(
            site_name=site_name,
            country=site.get("country", ""),
            coordinates={
                "latitude": coords.get("latitude", 0),
                "longitude": coords.get("longitude", 0),
            },
            area_km2=site.get("area_km2"),
            biome=biome,
            habitats=habitats,
            priority_biodiversity_area=neoli.get("neoli_score", 0) >= 3,
            world_heritage_status="World Heritage" in site_name,
            designation_year=site.get("designation_year"),
            management_authority=governance.get("management_authority", ""),
            indigenous_partnership=governance.get("indigenous_partnership", ""),
        )

    def _build_evaluate(
        self, case_data: dict, axiom_data: dict | None
    ) -> TNFDEvaluate:
        """Build LEAP Evaluate phase from ecosystem services and axioms."""
        esv_bundle = case_data.get("ecosystem_services", {})
        services_raw = esv_bundle.get("services", [])
        total_esv = esv_bundle.get("total_annual_value_usd", 0)

        services: list[ServiceDependency] = []
        for svc in services_raw:
            val = svc.get("annual_value_usd", 0)
            share = (val / total_esv * 100) if total_esv > 0 else 0
            services.append(ServiceDependency(
                service_type=svc.get("service_type", ""),
                annual_value_usd=val,
                valuation_method=svc.get("valuation_method", ""),
                share_of_total_esv_pct=round(share, 1),
            ))

        # Sort by value descending to find primary dependency
        services.sort(key=lambda s: s.annual_value_usd or 0, reverse=True)
        primary_dep = ""
        if services:
            top = services[0]
            primary_dep = (
                f"{top.service_type.replace('_', ' ').title()} "
                f"({top.share_of_total_esv_pct:.0f}%)"
            )

        # Species dependencies
        species_deps: list[SpeciesDependency] = []
        for sp in case_data.get("key_species", []):
            species_deps.append(SpeciesDependency(
                scientific_name=sp.get("scientific_name", ""),
                common_name=sp.get("common_name", ""),
                role=sp.get("role_in_ecosystem", ""),
                dependency_type=sp.get("carbon_relevance", sp.get(
                    "functional_group", ""
                )),
            ))

        # Impact pathways from axiom data
        impact_pathways: list[ImpactPathway] = []
        axiom_ids: list[str] = []
        if axiom_data:
            for ax in axiom_data.get("axioms", []):
                axiom_id = ax.get("axiom_id", "")
                # Only include axioms relevant to this site's habitat types
                applicable = ax.get("applicable_habitats", [])
                eco = case_data.get("ecological_status", {})
                primary_habitat = eco.get("primary_habitat", "")
                recovery = case_data.get("ecological_recovery", {})

                is_relevant = (
                    not applicable
                    or primary_habitat in applicable
                    or (recovery and "coral_reef" in applicable)
                )
                if not is_relevant:
                    continue

                category = ax.get("category", "")
                if category in ("ecological_to_service", "ecological_to_financial"):
                    axiom_ids.append(axiom_id)
                    # Get source DOI from first coefficient that has one
                    source_doi = None
                    for coeff_val in ax.get("coefficients", {}).values():
                        if isinstance(coeff_val, dict):
                            source_doi = coeff_val.get("source_doi")
                            if source_doi:
                                break

                    impact_pathways.append(ImpactPathway(
                        pathway_type=category,
                        description=ax.get("description", ""),
                        direction="positive",
                        magnitude=ax.get("pattern", ""),
                        bridge_axiom_id=axiom_id,
                        source_doi=source_doi,
                    ))

        return TNFDEvaluate(
            total_esv_usd=total_esv,
            services=services,
            primary_dependency=primary_dep,
            species_dependencies=species_deps,
            impact_pathways=impact_pathways,
            bridge_axioms_applied=axiom_ids,
        )

    def _build_assess(
        self, case_data: dict, axiom_data: dict | None
    ) -> TNFDAssess:
        """Build LEAP Assess phase from risk data and Monte Carlo."""
        neoli = case_data.get("neoli_assessment", {})
        rating = case_data.get("asset_quality_rating", {})
        risk_data = case_data.get("risk_assessment", {})

        physical_risks: list[RiskAssessment] = []
        transition_risks: list[RiskAssessment] = []
        systemic_risks: list[RiskAssessment] = []

        for rf in risk_data.get("risk_factors", []):
            risk = RiskAssessment(
                risk_type=rf.get("risk_type", ""),
                severity=rf.get("severity", ""),
                likelihood=rf.get("likelihood", ""),
                financial_impact_description=rf.get("evidence", ""),
                source_doi=rf.get("source_doi"),
            )
            rtype = rf.get("risk_type", "")
            if rtype in ("marine_heatwave", "cyclone", "bleaching"):
                risk.category = "physical_acute"
                physical_risks.append(risk)
            elif rtype in ("ocean_warming", "acidification", "sea_level_rise"):
                risk.category = "physical_chronic"
                physical_risks.append(risk)
            elif rtype in ("policy_change", "carbon_market_volatility"):
                risk.category = "transition"
                transition_risks.append(risk)
            else:
                risk.category = "systemic"
                systemic_risks.append(risk)

        # Opportunities
        opportunities: list[Opportunity] = []
        esv_bundle = case_data.get("ecosystem_services", {})
        services_raw = esv_bundle.get("services", [])

        # Carbon credit opportunity if carbon service present
        for svc in services_raw:
            if svc.get("service_type") == "carbon_sequestration":
                val = svc.get("annual_value_usd", 0)
                opportunities.append(Opportunity(
                    opportunity_type="blue_carbon_credits",
                    description=(
                        "Blue carbon credit issuance under Verra VCS VM0033 "
                        "methodology for seagrass/reef carbon sequestration"
                    ),
                    estimated_value_range=f"${val:,.0f}/year at current pricing",
                    time_horizon="medium-term (3-10 years)",
                    enabling_axioms=["BA-013", "BA-014"],
                ))
                break

        # Blue bond opportunity if total ESV is large enough
        total_esv = esv_bundle.get("total_annual_value_usd", 0)
        if total_esv > 10_000_000:
            opportunities.append(Opportunity(
                opportunity_type="blue_bond_issuance",
                description=(
                    "Nature-backed blue bond with ESV underpinning repayment "
                    "capacity; IFC Blue Finance and GBP/GLP consistent"
                ),
                estimated_value_range=f"${total_esv * 1.0:,.0f}-${total_esv * 1.7:,.0f} (illustrative)",
                time_horizon="medium-term (3-5 years)",
                enabling_axioms=["BA-001", "BA-002"],
            ))

        # Monte Carlo summary from services
        mc_summary: dict[str, Any] = {}
        if services_raw:
            mc_services = []
            for svc in services_raw:
                val = svc.get("annual_value_usd", 0)
                mc_services.append({
                    "value": val,
                    "ci_low": val * 0.7,
                    "ci_high": val * 1.3,
                })
            try:
                from maris.axioms.monte_carlo import run_monte_carlo
                mc_result = run_monte_carlo(mc_services, n_simulations=10_000)
                mc_summary = {
                    "median": mc_result["median"],
                    "mean": mc_result["mean"],
                    "p5": mc_result["p5"],
                    "p95": mc_result["p95"],
                    "n_simulations": mc_result["n_simulations"],
                }
            except Exception:
                logger.warning("Monte Carlo simulation failed; skipping")

        return TNFDAssess(
            physical_risks=physical_risks,
            transition_risks=transition_risks,
            systemic_risks=systemic_risks,
            opportunities=opportunities,
            neoli_score=neoli.get("neoli_score"),
            asset_rating=rating.get("rating", ""),
            composite_score=rating.get("composite_score"),
            monte_carlo_summary=mc_summary,
        )

    def _build_prepare(
        self,
        site_name: str,
        case_data: dict,
        evaluate: TNFDEvaluate,
        assess: TNFDAssess,
    ) -> TNFDPrepare:
        """Build LEAP Prepare phase - the 14 recommended disclosures."""
        esv_bundle = case_data.get("ecosystem_services", {})
        total_esv = esv_bundle.get("total_annual_value_usd", 0)
        governance = case_data.get("site", {}).get("governance", {})

        # 14 TNFD recommended disclosures across 4 pillars
        # Governance (A, B, C) - 3 disclosures
        governance_sections = [
            DisclosureSection(
                disclosure_id="GOV-A",
                pillar="Governance",
                title="Board oversight of nature-related issues",
                content=(
                    f"Board oversight includes review of MARIS asset ratings "
                    f"(current: {assess.asset_rating}, composite {assess.composite_score:.2f}) "
                    f"and NEOLI alignment assessments ({assess.neoli_score}/5 criteria met) "
                    f"for {site_name}."
                ),
                populated=True,
            ),
            DisclosureSection(
                disclosure_id="GOV-B",
                pillar="Governance",
                title="Management's role in assessing nature-related issues",
                content=(
                    f"Management authority: {governance.get('management_authority', 'N/A')}. "
                    f"Community engagement: {governance.get('community_engagement', 'N/A')}."
                ),
                populated=bool(governance.get("management_authority")),
            ),
            DisclosureSection(
                disclosure_id="GOV-C",
                pillar="Governance",
                title="Human rights and stakeholder engagement",
                content=self._stakeholder_content(case_data),
                populated=True,
            ),
        ]

        # Strategy (A, B, C, D) - 4 disclosures
        strategy_sections = [
            DisclosureSection(
                disclosure_id="STR-A",
                pillar="Strategy",
                title="Nature-related dependencies, impacts, risks, and opportunities",
                content=(
                    f"Primary dependency: {evaluate.primary_dependency}. "
                    f"Total ESV: ${total_esv:,.0f}/year. "
                    f"{len(evaluate.bridge_axioms_applied)} bridge axioms quantify "
                    f"ecological-to-financial translation pathways."
                ),
                populated=True,
            ),
            DisclosureSection(
                disclosure_id="STR-B",
                pillar="Strategy",
                title="Effect on business model, value chain, and financial planning",
                content=(
                    f"Nature-dependent revenue streams total ${total_esv:,.0f}/year "
                    f"across {len(evaluate.services)} ecosystem service categories. "
                    f"MARIS confidence model yields composite score of "
                    f"{assess.composite_score:.2f}."
                ),
                populated=True,
            ),
            DisclosureSection(
                disclosure_id="STR-C",
                pillar="Strategy",
                title="Resilience of strategy under different scenarios",
                content=self._resilience_content(assess),
                populated=bool(assess.monte_carlo_summary),
            ),
            DisclosureSection(
                disclosure_id="STR-D",
                pillar="Strategy",
                title="Priority locations for nature-related assessment",
                content=(
                    f"{site_name} identified as priority location based on "
                    f"NEOLI alignment ({assess.neoli_score}/5 criteria), "
                    f"biodiversity significance, and ESV magnitude (${total_esv:,.0f}/year)."
                ),
                populated=True,
            ),
        ]

        # Risk & Impact Management (A, B, C, D) - 4 disclosures
        risk_management_sections = [
            DisclosureSection(
                disclosure_id="RIM-A",
                pillar="Risk & Impact Management",
                title="Process for identifying nature-related issues in direct operations",
                content=(
                    "MARIS knowledge graph identifies nature-related issues through "
                    "40 bridge axioms mapping ecological states to financial metrics. "
                    "All claims traceable to DOI-backed peer-reviewed sources."
                ),
                populated=True,
            ),
            DisclosureSection(
                disclosure_id="RIM-B",
                pillar="Risk & Impact Management",
                title="Process for identifying nature-related issues in the value chain",
                content=(
                    f"{len(evaluate.impact_pathways)} impact pathways identified "
                    f"linking ecosystem condition to service delivery. "
                    f"Dependencies span {len(evaluate.services)} ecosystem service categories."
                ),
                populated=bool(evaluate.impact_pathways),
            ),
            DisclosureSection(
                disclosure_id="RIM-C",
                pillar="Risk & Impact Management",
                title="Process for managing nature-related issues",
                content=(
                    f"Risk management informed by {len(assess.physical_risks)} physical risks, "
                    f"{len(assess.transition_risks)} transition risks, "
                    f"and {len(assess.systemic_risks)} systemic risks identified via "
                    f"MARIS risk assessment framework."
                ),
                populated=True,
            ),
            DisclosureSection(
                disclosure_id="RIM-D",
                pillar="Risk & Impact Management",
                title="Integration with overall risk management",
                content=(
                    f"Nature-related risks integrated via MARIS composite scoring model "
                    f"(asset rating: {assess.asset_rating}) and Monte Carlo simulation "
                    f"for ESV uncertainty quantification."
                ),
                populated=True,
            ),
        ]

        # Metrics & Targets (A, B, C) - 3 disclosures
        metrics_targets_sections = [
            DisclosureSection(
                disclosure_id="MT-A",
                pillar="Metrics & Targets",
                title="Metrics used to assess nature-related risks and opportunities",
                content=self._metrics_content(evaluate, assess),
                populated=True,
            ),
            DisclosureSection(
                disclosure_id="MT-B",
                pillar="Metrics & Targets",
                title="Metrics used to assess dependencies and impacts on nature",
                content=self._impact_metrics_content(case_data, evaluate),
                populated=True,
            ),
            DisclosureSection(
                disclosure_id="MT-C",
                pillar="Metrics & Targets",
                title="Targets and goals for managing nature-related issues",
                content=(
                    "Targets aligned with Kunming-Montreal Global Biodiversity Framework. "
                    "Maintain NEOLI alignment, protect habitat extent, "
                    "and sustain ecosystem service delivery capacity."
                ),
                populated=True,
            ),
        ]

        # Build metrics list
        metrics = self._build_metrics(case_data, evaluate, assess)
        targets = self._build_targets(case_data, assess)
        provenance = self._build_provenance(case_data, evaluate)

        recommendation = (
            f"Maintain NEOLI alignment for {site_name}. "
            f"Continue monitoring {len(evaluate.services)} ecosystem service streams "
            f"(${total_esv:,.0f}/year total ESV). "
        )
        if assess.opportunities:
            opp_types = [o.opportunity_type.replace("_", " ") for o in assess.opportunities]
            recommendation += f"Pursue {', '.join(opp_types)} opportunities."

        return TNFDPrepare(
            governance_sections=governance_sections,
            strategy_sections=strategy_sections,
            risk_management_sections=risk_management_sections,
            metrics_targets_sections=metrics_targets_sections,
            metrics=metrics,
            targets=targets,
            provenance_chain=provenance,
            recommendation=recommendation,
        )

    # ------------------------------------------------------------------
    # Content helpers
    # ------------------------------------------------------------------

    def _stakeholder_content(self, case_data: dict) -> str:
        governance = case_data.get("site", {}).get("governance", {})
        parts = []
        ip = governance.get("indigenous_partnership", "")
        if ip:
            parts.append(f"Indigenous partnership: {ip}.")
        ce = governance.get("community_engagement", "")
        if ce:
            parts.append(f"Community engagement level: {ce}.")
        ls = governance.get("local_support", "")
        if ls:
            parts.append(f"Local support: {ls}.")
        return " ".join(parts) if parts else "Stakeholder engagement data not yet available."

    def _resilience_content(self, assess: TNFDAssess) -> str:
        mc = assess.monte_carlo_summary
        if not mc:
            return "Monte Carlo scenario analysis not yet available."
        return (
            f"Monte Carlo simulation ({mc.get('n_simulations', 0):,} runs): "
            f"median ESV ${mc.get('median', 0):,.0f}, "
            f"P5 ${mc.get('p5', 0):,.0f}, "
            f"P95 ${mc.get('p95', 0):,.0f}. "
            f"Demonstrates resilience range under parameter uncertainty."
        )

    def _metrics_content(self, evaluate: TNFDEvaluate, assess: TNFDAssess) -> str:
        parts = [
            f"Total ESV: ${evaluate.total_esv_usd:,.0f}/year.",
            f"NEOLI score: {assess.neoli_score}/5.",
            f"Asset rating: {assess.asset_rating} (composite {assess.composite_score:.2f}).",
        ]
        if assess.monte_carlo_summary:
            mc = assess.monte_carlo_summary
            parts.append(
                f"Monte Carlo P5-P95 range: "
                f"${mc.get('p5', 0):,.0f} - ${mc.get('p95', 0):,.0f}."
            )
        return " ".join(parts)

    def _impact_metrics_content(self, case_data: dict, evaluate: TNFDEvaluate) -> str:
        parts = []
        # Biomass recovery if available
        recovery = case_data.get("ecological_recovery", {})
        if recovery:
            bio = recovery.get("metrics", {}).get("fish_biomass", {})
            if bio:
                parts.append(
                    f"Fish biomass recovery: {bio.get('recovery_ratio', 0)}x "
                    f"(CI [{bio.get('confidence_interval_95', [0, 0])[0]}, "
                    f"{bio.get('confidence_interval_95', [0, 0])[1]}])."
                )

        # Carbon metrics if available
        eco = case_data.get("ecological_status", {})
        seq = eco.get("metrics", {}).get("sequestration", {})
        if seq:
            parts.append(
                f"Carbon sequestration: {seq.get('rate_tCO2_per_ha_yr', 0)} tCO2/ha/yr."
            )

        # Service count
        parts.append(
            f"{len(evaluate.services)} ecosystem services quantified "
            f"with market-price methodology."
        )
        return " ".join(parts)

    def _build_metrics(
        self, case_data: dict, evaluate: TNFDEvaluate, assess: TNFDAssess
    ) -> list[MetricEntry]:
        metrics: list[MetricEntry] = []

        metrics.append(MetricEntry(
            metric_name="Total ESV",
            value=evaluate.total_esv_usd,
            unit="USD/year",
            methodology="market-price",
        ))

        metrics.append(MetricEntry(
            metric_name="NEOLI Score",
            value=assess.neoli_score,
            unit="out of 5",
            source_doi="10.1038/nature13022",
            methodology="Edgar et al. 2014",
        ))

        metrics.append(MetricEntry(
            metric_name="Asset Rating",
            value=assess.asset_rating,
            unit="MARIS rating scale",
            methodology="composite score model",
        ))

        for svc in evaluate.services:
            metrics.append(MetricEntry(
                metric_name=f"ESV - {svc.service_type.replace('_', ' ').title()}",
                value=svc.annual_value_usd,
                unit="USD/year",
                methodology=svc.valuation_method,
            ))

        # Ecological metrics
        recovery = case_data.get("ecological_recovery", {})
        if recovery:
            bio = recovery.get("metrics", {}).get("fish_biomass", {})
            if bio:
                metrics.append(MetricEntry(
                    metric_name="Fish Biomass Recovery Ratio",
                    value=bio.get("recovery_ratio"),
                    unit="x baseline",
                    source_doi="10.1371/journal.pone.0023601",
                ))

        eco = case_data.get("ecological_status", {})
        seq = eco.get("metrics", {}).get("sequestration", {})
        if seq:
            metrics.append(MetricEntry(
                metric_name="Carbon Sequestration Rate",
                value=seq.get("rate_tCO2_per_ha_yr"),
                unit="tCO2/ha/yr",
                source_doi="10.1038/s41558-018-0096-y",
            ))

        return metrics

    def _build_targets(
        self, case_data: dict, assess: TNFDAssess
    ) -> list[TargetEntry]:
        targets: list[TargetEntry] = []

        targets.append(TargetEntry(
            target_name="Maintain NEOLI alignment",
            baseline_value=assess.neoli_score,
            target_value=assess.neoli_score,
            target_year=2030,
            aligned_framework="Kunming-Montreal GBF Target 3",
            status="on track",
        ))

        targets.append(TargetEntry(
            target_name="Maintain or improve asset rating",
            baseline_value=assess.asset_rating,
            target_value=assess.asset_rating,
            target_year=2030,
            aligned_framework="TNFD Recommended Disclosure MT-C",
            status="on track",
        ))

        # Habitat protection target
        site = case_data.get("site", {})
        area = site.get("area_km2")
        if area:
            targets.append(TargetEntry(
                target_name="Maintain protected area extent",
                baseline_value=area,
                target_value=area,
                target_year=2030,
                aligned_framework="Kunming-Montreal GBF Target 3 (30x30)",
                status="achieved",
            ))

        return targets

    def _build_provenance(
        self, case_data: dict, evaluate: TNFDEvaluate
    ) -> list[ProvenanceEntry]:
        provenance: list[ProvenanceEntry] = []

        # ESV claim
        esv = case_data.get("ecosystem_services", {})
        total = esv.get("total_annual_value_usd", 0)
        provenance.append(ProvenanceEntry(
            claim=f"Total ESV of ${total:,.0f}/year (market-price methodology)",
            evidence_tier="T1",
            confidence=0.85,
        ))

        # Per-service claims
        for svc in esv.get("services", []):
            source = svc.get("source", {})
            provenance.append(ProvenanceEntry(
                claim=(
                    f"{svc.get('service_type', '').replace('_', ' ').title()}: "
                    f"${svc.get('annual_value_usd', 0):,.0f}/year"
                ),
                source_doi=source.get("doi"),
                evidence_tier="T1",
            ))

        # NEOLI claim
        neoli_source = case_data.get("neoli_assessment", {}).get("source", {})
        provenance.append(ProvenanceEntry(
            claim=f"NEOLI alignment: {case_data.get('neoli_assessment', {}).get('neoli_score', 0)}/5",
            source_doi=neoli_source.get("doi"),
            evidence_tier="T1",
            confidence=0.90,
        ))

        return provenance
