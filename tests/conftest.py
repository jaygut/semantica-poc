"""Shared test fixtures for MARIS test suite."""

import os

import pytest
from unittest.mock import MagicMock, patch


# Ensure test environment variables are set before any config import
os.environ.setdefault("MARIS_NEO4J_PASSWORD", "test-password")
os.environ.setdefault("MARIS_LLM_API_KEY", "test-key")
os.environ.setdefault("MARIS_API_KEY", "test-api-key")
os.environ.setdefault("MARIS_DEMO_MODE", "true")


@pytest.fixture
def sample_graph_result():
    """A typical graph result from a site_valuation query."""
    return {
        "template": "site_valuation",
        "parameters": {"site_name": "Cabo Pulmo National Park"},
        "results": [
            {
                "site": "Cabo Pulmo National Park",
                "total_esv": 29270000,
                "biomass_ratio": 4.63,
                "neoli_score": 4,
                "asset_rating": "AAA",
                "services": [
                    {
                        "service": "Tourism",
                        "value_usd": 25000000,
                        "method": "market_price",
                        "ci_low": 20000000,
                        "ci_high": 30000000,
                    },
                    {
                        "service": "Fisheries Spillover",
                        "value_usd": 2500000,
                        "method": "production_function",
                        "ci_low": 1500000,
                        "ci_high": 3500000,
                    },
                ],
                "evidence": [
                    {
                        "axiom_id": "BA-001",
                        "axiom_name": "mpa_biomass_dive_tourism_value",
                        "doi": "10.1016/j.ecolecon.2024.108163",
                        "title": "Tourism WTP study",
                        "year": 2024,
                        "tier": "T1",
                    },
                ],
            }
        ],
        "record_count": 1,
    }


@pytest.fixture
def empty_graph_result():
    """A graph result with no matching data."""
    return {
        "template": "site_valuation",
        "parameters": {"site_name": "Unknown Site"},
        "results": [],
        "record_count": 0,
    }


@pytest.fixture
def sample_llm_response():
    """A well-formed LLM JSON response."""
    return {
        "answer": "Cabo Pulmo National Park has a total ESV of $29.27M per year.",
        "confidence": 0.85,
        "evidence": [
            {
                "doi": "10.1016/j.ecolecon.2024.108163",
                "finding": "Tourism WTP increase of up to 84%",
            },
        ],
        "axioms_used": ["BA-001", "BA-002"],
        "caveats": ["Biomass data from 2009"],
    }


@pytest.fixture
def sample_services():
    """Sample ecosystem services for Monte Carlo simulation."""
    return [
        {"value": 25000000, "ci_low": 20000000, "ci_high": 30000000},
        {"value": 2500000, "ci_low": 1500000, "ci_high": 3500000},
        {"value": 1270000, "ci_low": 800000, "ci_high": 1700000},
        {"value": 500000, "ci_low": 300000, "ci_high": 700000},
    ]


@pytest.fixture
def sample_questions():
    """Sample questions per classification category."""
    return {
        "site_valuation": [
            "What is Cabo Pulmo worth?",
            "What is the ESV of Cabo Pulmo?",
            "What is the total value of the Great Barrier Reef?",
        ],
        "provenance_drilldown": [
            "What evidence supports this valuation?",
            "Show me the DOI sources for Cabo Pulmo",
            "What research backs the biomass claim?",
        ],
        "axiom_explanation": [
            "Explain bridge axiom BA-001",
            "What is the coefficient for BA-002?",
        ],
        "comparison": [
            "Compare Cabo Pulmo to the Great Barrier Reef",
            "How does CP rank versus GBR?",
        ],
        "risk_assessment": [
            "What are the risks to Cabo Pulmo?",
            "What if climate change degrades the reef?",
        ],
    }


@pytest.fixture
def mock_neo4j():
    """Mock the Neo4j run_query function."""
    with patch("maris.graph.connection.run_query") as mock:
        mock.return_value = []
        yield mock


@pytest.fixture
def mock_config():
    """Mock config for testing without .env file."""
    with patch("maris.config.get_config") as mock:
        cfg = MagicMock()
        cfg.neo4j_uri = "bolt://localhost:7687"
        cfg.neo4j_user = "neo4j"
        cfg.neo4j_password = "test-password"
        cfg.neo4j_database = "neo4j"
        cfg.llm_provider = "deepseek"
        cfg.llm_api_key = "test-key"
        cfg.llm_base_url = "https://api.deepseek.com/v1"
        cfg.llm_model = "deepseek-chat"
        cfg.llm_timeout = 30
        cfg.llm_max_tokens = 4096
        cfg.api_key = "test-api-key"
        cfg.cors_origins = ["http://localhost:8501"]
        cfg.demo_mode = True
        cfg.enable_live_graph = True
        cfg.enable_chat = True
        mock.return_value = cfg
        yield cfg
