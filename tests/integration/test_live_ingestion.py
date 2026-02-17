"""Integration tests for ingestion pipeline against real Neo4j."""

import json
import pytest
from maris.services.ingestion.case_study_loader import CaseStudyLoader

# Mark as integration test
pytestmark = pytest.mark.integration


def test_live_ingestion(integration_neo4j_driver, tmp_path):
    """Verify CaseStudyLoader correctly populates graph in a real DB."""
    driver = integration_neo4j_driver
    
    # Sentinel check to ensure we aren't wiping a prod DB (paranoid check)
    # The fixture uses localhost:7687/7688, but good to be safe.
    # We assume the user/CI environment is safe for testing.
    
    with driver.session() as session:
        # 1. Clean slate
        session.run("MATCH (n) DETACH DELETE n")
        
        # 2. Prepare dummy case study
        case_data = {
            "site": {
                "name": "Integration Test Site",
                "country": "Testland",
                "coordinates": {"latitude": 0, "longitude": 0},
                "area_km2": 100,
                "designation_year": 2020
            },
            "ecological_status": {
                "primary_habitat": "coral_reef",
                "assessment_year": 2022
            },
            "ecosystem_services": {
                "total_annual_value_usd": 1000000,
                "services": [
                    {
                        "service_type": "tourism",
                        "annual_value_usd": 500000,
                        "valuation_method": "market_price"
                    }
                ]
            },
            "key_species": [
                {
                    "worms_aphia_id": 123456,
                    "scientific_name": "Testus species",
                    "common_name": "Test Fish",
                    "role_in_ecosystem": "Herbivore"
                }
            ]
        }
        
        case_file = tmp_path / "integration_test_case.json"
        case_file.write_text(json.dumps(case_data))
        
        # 3. Run loader
        loader = CaseStudyLoader(session)
        count = loader.load_site(case_file)
        
        assert count > 0, "Loader should have performed operations"

        # 4. Verify Nodes
        # MPA
        result = session.run("MATCH (m:MPA {name: 'Integration Test Site'}) RETURN m")
        mpa = result.single()
        assert mpa, "MPA node not created"
        assert mpa["m"]["country"] == "Testland"
        assert mpa["m"]["total_esv_usd"] == 1000000
        
        # Habitat (Logic links 'coral_reef' automatically if primary)
        result = session.run(
            """
            MATCH (m:MPA {name: 'Integration Test Site'})-[:HAS_HABITAT]->(h:Habitat)
            RETURN h.habitat_id
            """
        )
        habitats = [rec["h.habitat_id"] for rec in result]
        assert "coral_reef" in habitats
        
        # Service
        result = session.run(
            """
            MATCH (m:MPA {name: 'Integration Test Site'})-[:GENERATES]->(es:EcosystemService)
            RETURN es.service_type, es.annual_value_usd
            """
        )
        svc = result.single()
        assert svc["es.service_type"] == "tourism"
        assert svc["es.annual_value_usd"] == 500000
        
        # Species
        result = session.run(
            """
            MATCH (s:Species {worms_id: 123456})-[:LOCATED_IN]->(m:MPA)
            RETURN s.scientific_name
            """
        )
        sp = result.single()
        assert sp["s.scientific_name"] == "Testus species"
