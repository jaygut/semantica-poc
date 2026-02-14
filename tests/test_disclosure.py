"""Tests for TNFD LEAP disclosure module.

Covers: Pydantic models, LEAP generator, renderers, alignment scorer,
API endpoint, and content accuracy for both Cabo Pulmo and Shark Bay.
"""

import json
import os

import pytest
from unittest.mock import patch, MagicMock

# Ensure test environment variables
os.environ.setdefault("MARIS_NEO4J_PASSWORD", "test-password")
os.environ.setdefault("MARIS_LLM_API_KEY", "test-key")
os.environ.setdefault("MARIS_API_KEY", "test-api-key")
os.environ.setdefault("MARIS_DEMO_MODE", "true")

from maris.disclosure.models import (
    TNFDDisclosure,
    TNFDLocate,
    TNFDEvaluate,
    TNFDAssess,
    TNFDPrepare,
    ServiceDependency,
    RiskAssessment,
    DisclosureSection,
)
from maris.disclosure.leap_generator import LEAPGenerator
from maris.disclosure.renderers import render_markdown, render_json, render_summary
from maris.disclosure.alignment_scorer import AlignmentScorer, AlignmentResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cabo_pulmo_case_data():
    """Cabo Pulmo case study data matching the real JSON structure."""
    return {
        "site": {
            "name": "Cabo Pulmo National Park",
            "country": "Mexico",
            "coordinates": {"latitude": 23.42, "longitude": -109.42},
            "area_km2": 71.11,
            "designation_year": 1995,
            "governance": {
                "management_authority": "CONANP",
                "community_engagement": "high",
                "local_support": "strong",
            },
        },
        "neoli_assessment": {
            "neoli_score": 4,
            "source": {"doi": "10.1038/nature13022"},
        },
        "ecological_recovery": {
            "metrics": {
                "fish_biomass": {
                    "recovery_ratio": 4.63,
                    "confidence_interval_95": [3.8, 5.5],
                },
            },
        },
        "ecosystem_services": {
            "services": [
                {
                    "service_type": "tourism",
                    "annual_value_usd": 25000000,
                    "valuation_method": "market_price",
                },
                {
                    "service_type": "fisheries_spillover",
                    "annual_value_usd": 3200000,
                    "valuation_method": "market_price",
                },
                {
                    "service_type": "carbon_sequestration",
                    "annual_value_usd": 180000,
                    "valuation_method": "avoided_cost",
                },
                {
                    "service_type": "coastal_protection",
                    "annual_value_usd": 890000,
                    "valuation_method": "avoided_cost",
                },
            ],
            "total_annual_value_usd": 29270000,
        },
        "asset_quality_rating": {
            "rating": "AAA",
            "composite_score": 0.90,
        },
        "key_species": [
            {
                "scientific_name": "Lutjanus argentiventris",
                "common_name": "Yellow snapper",
                "role_in_ecosystem": "dominant_predator",
                "functional_group": "mesopredator",
            },
        ],
        "risk_assessment": {
            "risk_factors": [
                {
                    "risk_type": "bleaching",
                    "severity": "medium",
                    "likelihood": "increasing",
                    "evidence": "Coral bleaching risk from warming events",
                },
                {
                    "risk_type": "acidification",
                    "severity": "high",
                    "likelihood": "increasing",
                    "evidence": "Ocean acidification chronic risk",
                },
            ],
        },
    }


@pytest.fixture
def shark_bay_case_data():
    """Shark Bay case study data matching the real JSON structure."""
    return {
        "site": {
            "name": "Shark Bay World Heritage Area",
            "country": "Australia",
            "coordinates": {"latitude": -25.97, "longitude": 113.86},
            "area_km2": 23000,
            "seagrass_extent_km2": 4800,
            "designation_year": 1991,
            "governance": {
                "management_authority": "DBCA",
                "community_engagement": "high",
                "local_support": "strong",
                "indigenous_partnership": "Malgana Aboriginal Corporation joint management (ILUA 2024)",
            },
        },
        "neoli_assessment": {
            "neoli_score": 4,
            "source": {"doi": "10.1038/nature13022"},
        },
        "ecological_status": {
            "primary_habitat": "seagrass_meadow",
            "dominant_species": "Posidonia australis",
            "metrics": {
                "sequestration": {
                    "rate_tCO2_per_ha_yr": 0.84,
                },
                "heatwave_impact": {
                    "recovery_status": "partial - uneven across bay",
                },
            },
        },
        "ecosystem_services": {
            "services": [
                {
                    "service_type": "carbon_sequestration",
                    "annual_value_usd": 12100000,
                    "valuation_method": "market_price",
                    "source": {"doi": "10.1038/s41558-018-0096-y"},
                },
                {
                    "service_type": "fisheries",
                    "annual_value_usd": 5200000,
                    "valuation_method": "market_price",
                },
                {
                    "service_type": "tourism",
                    "annual_value_usd": 3400000,
                    "valuation_method": "market_price",
                },
                {
                    "service_type": "coastal_protection",
                    "annual_value_usd": 800000,
                    "valuation_method": "avoided_cost",
                },
            ],
            "total_annual_value_usd": 21500000,
        },
        "asset_quality_rating": {
            "rating": "AA",
            "composite_score": 0.81,
        },
        "key_species": [
            {
                "scientific_name": "Posidonia australis",
                "common_name": "Fibre-ball weed",
                "role_in_ecosystem": "dominant_habitat_former",
                "carbon_relevance": "primary carbon stock species",
            },
            {
                "scientific_name": "Dugong dugon",
                "common_name": "Dugong",
                "role_in_ecosystem": "keystone_herbivore",
            },
        ],
        "risk_assessment": {
            "risk_factors": [
                {
                    "risk_type": "marine_heatwave",
                    "severity": "high",
                    "likelihood": "increasing",
                    "evidence": "2011 heatwave caused 36% seagrass loss",
                    "source_doi": "10.1038/s41558-018-0096-y",
                },
                {
                    "risk_type": "carbon_market_volatility",
                    "severity": "medium",
                    "likelihood": "moderate",
                    "evidence": "Carbon credit price volatility",
                },
            ],
        },
    }


@pytest.fixture
def sample_axiom_data():
    """Minimal axiom template data for testing."""
    return {
        "axioms": [
            {
                "axiom_id": "BA-001",
                "name": "mpa_biomass_dive_tourism_value",
                "category": "ecological_to_service",
                "description": "Fish biomass drives tourism WTP",
                "applicable_habitats": ["coral_reef"],
                "pattern": "IF full_protection THEN wtp_increase",
                "coefficients": {
                    "wtp_increase": {
                        "value": 84,
                        "source_doi": "10.1038/s41598-024-83664-1",
                    },
                },
            },
            {
                "axiom_id": "BA-013",
                "name": "seagrass_carbon_sequestration_rate",
                "category": "ecological_to_service",
                "description": "Seagrass area to carbon sequestration",
                "applicable_habitats": ["seagrass_meadow"],
                "pattern": "IF seagrass_extent THEN carbon_sequestration",
                "coefficients": {
                    "rate": {
                        "value": 0.84,
                        "source_doi": "10.1038/s41558-018-0096-y",
                    },
                },
            },
        ],
    }


@pytest.fixture
def generator():
    return LEAPGenerator()


@pytest.fixture
def scorer():
    return AlignmentScorer()


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestDisclosureModels:
    def test_tnfd_locate_serialization(self):
        loc = TNFDLocate(
            site_name="Test Site",
            country="TestCountry",
            biome="Marine",
            area_km2=100.0,
        )
        data = loc.model_dump()
        assert data["site_name"] == "Test Site"
        assert data["area_km2"] == 100.0

    def test_tnfd_evaluate_serialization(self):
        ev = TNFDEvaluate(
            total_esv_usd=29270000,
            primary_dependency="Tourism (85%)",
            services=[
                ServiceDependency(
                    service_type="tourism",
                    annual_value_usd=25000000,
                ),
            ],
        )
        data = ev.model_dump()
        assert data["total_esv_usd"] == 29270000
        assert len(data["services"]) == 1

    def test_tnfd_assess_serialization(self):
        asr = TNFDAssess(
            neoli_score=4,
            asset_rating="AAA",
            composite_score=0.90,
            physical_risks=[
                RiskAssessment(risk_type="bleaching", severity="medium"),
            ],
        )
        data = asr.model_dump()
        assert data["asset_rating"] == "AAA"
        assert len(data["physical_risks"]) == 1

    def test_tnfd_prepare_serialization(self):
        prep = TNFDPrepare(
            governance_sections=[
                DisclosureSection(
                    disclosure_id="GOV-A",
                    pillar="Governance",
                    title="Board oversight",
                    populated=True,
                ),
            ],
            recommendation="Maintain NEOLI alignment.",
        )
        data = prep.model_dump()
        assert len(data["governance_sections"]) == 1
        assert data["recommendation"] == "Maintain NEOLI alignment."

    def test_full_disclosure_roundtrip(self):
        disclosure = TNFDDisclosure(
            site_name="Test Site",
            locate=TNFDLocate(site_name="Test Site"),
            evaluate=TNFDEvaluate(),
            assess=TNFDAssess(),
            prepare=TNFDPrepare(),
        )
        data = disclosure.model_dump()
        restored = TNFDDisclosure(**data)
        assert restored.site_name == "Test Site"
        assert restored.framework_version == "TNFD v1.0"

    def test_disclosure_generated_at_auto_populated(self):
        disclosure = TNFDDisclosure(
            site_name="Test",
            locate=TNFDLocate(site_name="Test"),
            evaluate=TNFDEvaluate(),
            assess=TNFDAssess(),
            prepare=TNFDPrepare(),
        )
        assert disclosure.generated_at is not None
        assert len(disclosure.generated_at) > 10


# ---------------------------------------------------------------------------
# Generator tests
# ---------------------------------------------------------------------------

class TestLEAPGenerator:
    def test_generate_cabo_pulmo(self, generator, cabo_pulmo_case_data, sample_axiom_data):
        disclosure = generator.generate_from_data(
            "Cabo Pulmo National Park",
            cabo_pulmo_case_data,
            sample_axiom_data,
        )
        assert disclosure.site_name == "Cabo Pulmo National Park"
        assert disclosure.locate.country == "Mexico"
        assert disclosure.locate.biome == "Marine Shelves"
        assert disclosure.evaluate.total_esv_usd == 29270000
        assert disclosure.assess.asset_rating == "AAA"

    def test_generate_shark_bay(self, generator, shark_bay_case_data, sample_axiom_data):
        disclosure = generator.generate_from_data(
            "Shark Bay World Heritage Area",
            shark_bay_case_data,
            sample_axiom_data,
        )
        assert disclosure.site_name == "Shark Bay World Heritage Area"
        assert disclosure.locate.country == "Australia"
        assert disclosure.locate.biome == "Marine - Seagrass Meadows"
        assert disclosure.evaluate.total_esv_usd == 21500000
        assert disclosure.assess.asset_rating == "AA"

    def test_locate_priority_biodiversity(self, generator, cabo_pulmo_case_data):
        disclosure = generator.generate_from_data(
            "Cabo Pulmo National Park",
            cabo_pulmo_case_data,
        )
        # NEOLI score >= 3 means priority biodiversity area
        assert disclosure.locate.priority_biodiversity_area is True

    def test_locate_world_heritage(self, generator, shark_bay_case_data):
        disclosure = generator.generate_from_data(
            "Shark Bay World Heritage Area",
            shark_bay_case_data,
        )
        assert disclosure.locate.world_heritage_status is True

    def test_evaluate_primary_dependency_cabo_pulmo(self, generator, cabo_pulmo_case_data):
        disclosure = generator.generate_from_data(
            "Cabo Pulmo National Park",
            cabo_pulmo_case_data,
        )
        # Tourism is highest at $25M = ~85%
        assert "Tourism" in disclosure.evaluate.primary_dependency

    def test_evaluate_primary_dependency_shark_bay(self, generator, shark_bay_case_data):
        disclosure = generator.generate_from_data(
            "Shark Bay World Heritage Area",
            shark_bay_case_data,
        )
        # Carbon sequestration is highest at $12.1M = ~56%
        assert "Carbon" in disclosure.evaluate.primary_dependency

    def test_evaluate_services_count(self, generator, cabo_pulmo_case_data):
        disclosure = generator.generate_from_data(
            "Cabo Pulmo National Park",
            cabo_pulmo_case_data,
        )
        assert len(disclosure.evaluate.services) == 4

    def test_assess_risks_populated(self, generator, shark_bay_case_data):
        disclosure = generator.generate_from_data(
            "Shark Bay World Heritage Area",
            shark_bay_case_data,
        )
        assert len(disclosure.assess.physical_risks) >= 1
        heatwave_risks = [r for r in disclosure.assess.physical_risks if r.risk_type == "marine_heatwave"]
        assert len(heatwave_risks) == 1

    def test_assess_opportunities_generated(self, generator, cabo_pulmo_case_data):
        disclosure = generator.generate_from_data(
            "Cabo Pulmo National Park",
            cabo_pulmo_case_data,
        )
        # Should have blue bond opportunity (ESV > $10M)
        bond_opps = [o for o in disclosure.assess.opportunities if o.opportunity_type == "blue_bond_issuance"]
        assert len(bond_opps) >= 1

    def test_prepare_14_disclosures(self, generator, cabo_pulmo_case_data):
        disclosure = generator.generate_from_data(
            "Cabo Pulmo National Park",
            cabo_pulmo_case_data,
        )
        prep = disclosure.prepare
        total = (
            len(prep.governance_sections)
            + len(prep.strategy_sections)
            + len(prep.risk_management_sections)
            + len(prep.metrics_targets_sections)
        )
        assert total == 14

    def test_prepare_provenance_chain(self, generator, cabo_pulmo_case_data):
        disclosure = generator.generate_from_data(
            "Cabo Pulmo National Park",
            cabo_pulmo_case_data,
        )
        assert len(disclosure.prepare.provenance_chain) >= 1
        # Should include ESV claim
        esv_claims = [p for p in disclosure.prepare.provenance_chain if "$29,270,000" in p.claim]
        assert len(esv_claims) == 1

    def test_generate_unknown_site_raises(self, generator):
        with pytest.raises(ValueError, match="No case study available"):
            generator.generate("Nonexistent Marine Park")


# ---------------------------------------------------------------------------
# Renderer tests
# ---------------------------------------------------------------------------

class TestRenderers:
    def test_render_markdown_structure(self, generator, cabo_pulmo_case_data):
        disclosure = generator.generate_from_data(
            "Cabo Pulmo National Park", cabo_pulmo_case_data
        )
        md = render_markdown(disclosure)
        assert "# TNFD LEAP Disclosure" in md
        assert "## Phase 1: Locate" in md
        assert "## Phase 2: Evaluate" in md
        assert "## Phase 3: Assess" in md
        assert "## Phase 4: Prepare" in md

    def test_render_markdown_contains_esv(self, generator, cabo_pulmo_case_data):
        disclosure = generator.generate_from_data(
            "Cabo Pulmo National Park", cabo_pulmo_case_data
        )
        md = render_markdown(disclosure)
        assert "$29,270,000" in md

    def test_render_json_valid(self, generator, cabo_pulmo_case_data):
        disclosure = generator.generate_from_data(
            "Cabo Pulmo National Park", cabo_pulmo_case_data
        )
        json_str = render_json(disclosure)
        parsed = json.loads(json_str)
        assert parsed["site_name"] == "Cabo Pulmo National Park"
        assert "locate" in parsed
        assert "evaluate" in parsed

    def test_render_summary_concise(self, generator, cabo_pulmo_case_data):
        disclosure = generator.generate_from_data(
            "Cabo Pulmo National Park", cabo_pulmo_case_data
        )
        summary = render_summary(disclosure)
        assert "Executive Summary" in summary
        # Summary should be significantly shorter than full disclosure
        md = render_markdown(disclosure)
        assert len(summary) < len(md)

    def test_render_summary_contains_key_data(self, generator, shark_bay_case_data):
        disclosure = generator.generate_from_data(
            "Shark Bay World Heritage Area", shark_bay_case_data
        )
        summary = render_summary(disclosure)
        assert "Shark Bay" in summary
        assert "$21,500,000" in summary
        assert "AA" in summary


# ---------------------------------------------------------------------------
# Alignment scorer tests
# ---------------------------------------------------------------------------

class TestAlignmentScorer:
    def test_score_all_populated(self, scorer, generator, cabo_pulmo_case_data):
        disclosure = generator.generate_from_data(
            "Cabo Pulmo National Park", cabo_pulmo_case_data
        )
        result = scorer.score(disclosure)
        assert result.total_disclosures == 14
        assert result.populated_count >= 12
        assert result.score_pct >= 80.0

    def test_score_with_known_gaps(self, scorer):
        """Create a disclosure with intentional gaps."""
        disclosure = TNFDDisclosure(
            site_name="Test",
            locate=TNFDLocate(site_name="Test"),
            evaluate=TNFDEvaluate(),
            assess=TNFDAssess(),
            prepare=TNFDPrepare(
                governance_sections=[
                    DisclosureSection(
                        disclosure_id="GOV-A",
                        pillar="Governance",
                        title="Board oversight",
                        content="Has content",
                        populated=True,
                    ),
                    DisclosureSection(
                        disclosure_id="GOV-B",
                        pillar="Governance",
                        title="Management role",
                        populated=False,
                        gap_reason="No governance data",
                    ),
                ],
            ),
        )
        result = scorer.score(disclosure)
        assert "GOV-A" in result.populated_ids
        assert "GOV-B" in result.gap_ids
        assert "GOV-C" in result.gap_ids
        assert result.gap_details["GOV-B"] == "No governance data"

    def test_score_to_dict(self, scorer, generator, cabo_pulmo_case_data):
        disclosure = generator.generate_from_data(
            "Cabo Pulmo National Park", cabo_pulmo_case_data
        )
        result = scorer.score(disclosure)
        d = result.to_dict()
        assert "total_disclosures" in d
        assert "populated_count" in d
        assert "gap_ids" in d

    def test_expected_ids_count(self, scorer):
        assert len(scorer.EXPECTED_IDS) == 14


# ---------------------------------------------------------------------------
# Content accuracy tests
# ---------------------------------------------------------------------------

class TestContentAccuracy:
    def test_cabo_pulmo_esv_correct(self, generator, cabo_pulmo_case_data):
        disclosure = generator.generate_from_data(
            "Cabo Pulmo National Park", cabo_pulmo_case_data
        )
        assert disclosure.evaluate.total_esv_usd == 29270000

    def test_shark_bay_esv_correct(self, generator, shark_bay_case_data):
        disclosure = generator.generate_from_data(
            "Shark Bay World Heritage Area", shark_bay_case_data
        )
        assert disclosure.evaluate.total_esv_usd == 21500000

    def test_cabo_pulmo_rating(self, generator, cabo_pulmo_case_data):
        disclosure = generator.generate_from_data(
            "Cabo Pulmo National Park", cabo_pulmo_case_data
        )
        assert disclosure.assess.asset_rating == "AAA"
        assert disclosure.assess.composite_score == 0.90

    def test_shark_bay_rating(self, generator, shark_bay_case_data):
        disclosure = generator.generate_from_data(
            "Shark Bay World Heritage Area", shark_bay_case_data
        )
        assert disclosure.assess.asset_rating == "AA"
        assert disclosure.assess.composite_score == 0.81

    def test_neoli_score_both_sites(self, generator, cabo_pulmo_case_data, shark_bay_case_data):
        cp = generator.generate_from_data("Cabo Pulmo National Park", cabo_pulmo_case_data)
        sb = generator.generate_from_data("Shark Bay World Heritage Area", shark_bay_case_data)
        assert cp.assess.neoli_score == 4
        assert sb.assess.neoli_score == 4

    def test_terminology_neoli_alignment(self, generator, cabo_pulmo_case_data):
        """Uses 'NEOLI alignment' not 'NEOLI compliance'."""
        disclosure = generator.generate_from_data(
            "Cabo Pulmo National Park", cabo_pulmo_case_data
        )
        md = render_markdown(disclosure)
        assert "NEOLI compliance" not in md
        assert "NEOLI alignment" in md


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

class TestDisclosureEndpoint:
    @pytest.fixture
    def app(self):
        import maris.config
        maris.config._config = None
        from maris.api.main import create_app
        return create_app()

    @pytest.fixture
    def client(self, app):
        from fastapi.testclient import TestClient
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": "Bearer test-api-key"}

    def test_disclosure_endpoint_json(self, client, auth_headers):
        """POST /api/disclosure/tnfd-leap should return JSON disclosure."""
        with patch("maris.api.routes.disclosure._get_generator") as mock_gen, \
             patch("maris.api.routes.disclosure._get_scorer") as mock_scorer:
            mock_disclosure = TNFDDisclosure(
                site_name="Cabo Pulmo National Park",
                locate=TNFDLocate(site_name="Cabo Pulmo National Park"),
                evaluate=TNFDEvaluate(total_esv_usd=29270000),
                assess=TNFDAssess(neoli_score=4, asset_rating="AAA", composite_score=0.90),
                prepare=TNFDPrepare(),
            )
            gen_instance = MagicMock()
            gen_instance.generate.return_value = mock_disclosure
            mock_gen.return_value = gen_instance

            scorer_instance = MagicMock()
            scorer_instance.score.return_value = AlignmentResult(
                total_disclosures=14,
                populated_count=12,
                gap_count=2,
                score_pct=85.7,
            )
            mock_scorer.return_value = scorer_instance

            response = client.post(
                "/api/disclosure/tnfd-leap",
                json={"site_name": "Cabo Pulmo National Park", "format": "json"},
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["site_name"] == "Cabo Pulmo National Park"
            assert "disclosure" in data
            assert "alignment" in data

    def test_disclosure_endpoint_markdown(self, client, auth_headers):
        """POST /api/disclosure/tnfd-leap with format=markdown."""
        with patch("maris.api.routes.disclosure._get_generator") as mock_gen, \
             patch("maris.api.routes.disclosure._get_scorer") as mock_scorer:
            mock_disclosure = TNFDDisclosure(
                site_name="Cabo Pulmo National Park",
                locate=TNFDLocate(site_name="Cabo Pulmo National Park"),
                evaluate=TNFDEvaluate(total_esv_usd=29270000),
                assess=TNFDAssess(neoli_score=4, asset_rating="AAA", composite_score=0.90),
                prepare=TNFDPrepare(),
            )
            gen_instance = MagicMock()
            gen_instance.generate.return_value = mock_disclosure
            mock_gen.return_value = gen_instance

            scorer_instance = MagicMock()
            scorer_instance.score.return_value = AlignmentResult(
                total_disclosures=14, populated_count=14, gap_count=0, score_pct=100.0,
            )
            mock_scorer.return_value = scorer_instance

            response = client.post(
                "/api/disclosure/tnfd-leap",
                json={"site_name": "Cabo Pulmo National Park", "format": "markdown"},
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["format"] == "markdown"
            assert "content" in data

    def test_disclosure_endpoint_unknown_site(self, client, auth_headers):
        """Unknown site should return 404."""
        with patch("maris.api.routes.disclosure._get_generator") as mock_gen, \
             patch("maris.api.routes.disclosure._get_scorer"):
            gen_instance = MagicMock()
            gen_instance.generate.side_effect = ValueError("No case study available")
            mock_gen.return_value = gen_instance

            response = client.post(
                "/api/disclosure/tnfd-leap",
                json={"site_name": "Unknown Park", "format": "json"},
                headers=auth_headers,
            )
            assert response.status_code == 404
