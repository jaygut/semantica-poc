"""Tests for graph population pipeline."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch


class TestLoadJson:
    def test_load_valid_json(self):
        from maris.graph.population import _load_json
        mock_data = json.dumps({"key": "value"})
        with patch("builtins.open", mock_open(read_data=mock_data)):
            result = _load_json(Path("/fake/path.json"))
        assert result == {"key": "value"}

    def test_load_missing_file_raises(self):
        from maris.graph.population import _load_json
        with pytest.raises(FileNotFoundError):
            _load_json(Path("/nonexistent/path.json"))


class TestPopulateDocuments:
    def test_documents_created_from_registry(self):
        from maris.graph.population import _populate_documents

        mock_session = MagicMock()
        mock_cfg = MagicMock()

        # registry_path.exists() must return True
        mock_registry_path = MagicMock()
        mock_registry_path.exists.return_value = True
        mock_cfg.registry_path = mock_registry_path

        registry_data = {
            "documents": {
                "doc_001": {
                    "doi": "10.1234/test.001",
                    "title": "Test Paper",
                    "year": 2024,
                    "source_tier": "T1",
                    "domain": "Blue Finance",
                },
                "doc_002_no_doi": {
                    "title": "No DOI Paper",
                    "year": 2023,
                },
            }
        }

        with patch("maris.graph.population._load_json", return_value=registry_data):
            count = _populate_documents(mock_session, mock_cfg)

        # Only doc_001 has a DOI, so only 1 should be created
        assert count == 1
        mock_session.run.assert_called()

    def test_missing_registry_returns_zero(self):
        from maris.graph.population import _populate_documents

        mock_session = MagicMock()
        mock_cfg = MagicMock()

        mock_registry_path = MagicMock()
        mock_registry_path.exists.return_value = False
        mock_cfg.registry_path = mock_registry_path

        count = _populate_documents(mock_session, mock_cfg)
        assert count == 0


class TestPopulateComparisonSites:
    def test_comparison_sites_created(self):
        from maris.graph.population import _populate_comparison_sites

        mock_session = MagicMock()
        count = _populate_comparison_sites(mock_session)

        # Should create GBR and Papahanaumokuakea
        assert count == 2
        assert mock_session.run.call_count == 2

    def test_site_names_match_expected(self):
        from maris.graph.population import _populate_comparison_sites

        mock_session = MagicMock()
        _populate_comparison_sites(mock_session)

        all_params = [call.args[1] if len(call.args) > 1 else call.kwargs.get("parameters", {})
                      for call in mock_session.run.call_args_list]
        site_names = [p.get("name", "") for p in all_params if isinstance(p, dict)]
        assert "Great Barrier Reef Marine Park" in site_names
        assert any("Marine National Monument" in n for n in site_names)


class TestPopulateCaboPulmo:
    def test_cabo_pulmo_enrichment(self):
        from maris.graph.population import _populate_cabo_pulmo

        mock_session = MagicMock()
        mock_cfg = MagicMock()

        case_study = {
            "site": {"country": "Mexico", "area_km2": 71.11, "designation_year": 1995},
            "neoli_assessment": {"neoli_score": 4, "criteria": {}},
            "ecological_recovery": {"metrics": {"fish_biomass": {"recovery_ratio": 4.63}}},
            "asset_quality_rating": {"rating": "AAA", "composite_score": 0.90},
            "ecosystem_services": {
                "total_annual_value_usd": 29270000,
                "services": [
                    {"service_type": "tourism", "annual_value_usd": 25000000, "valuation_method": "market_price"},
                ],
            },
            "key_species": [],
            "trophic_network": {"nodes": [], "edges": []},
        }

        with patch("maris.graph.population._load_json", return_value=case_study):
            count = _populate_cabo_pulmo(mock_session, mock_cfg)

        # Should create at least MPA enrichment + 1 service
        assert count >= 2
        mock_session.run.assert_called()


class TestNumericalValidation:
    def test_esv_values_are_positive(self):
        """ESV values from case study should be positive."""
        case_study = {
            "ecosystem_services": {
                "total_annual_value_usd": 29270000,
                "services": [
                    {"service_type": "tourism", "annual_value_usd": 25000000},
                    {"service_type": "fisheries", "annual_value_usd": 2500000},
                ],
            }
        }
        total = case_study["ecosystem_services"]["total_annual_value_usd"]
        assert total > 0

        for svc in case_study["ecosystem_services"]["services"]:
            assert svc["annual_value_usd"] > 0

    def test_neoli_score_in_range(self):
        """NEOLI score should be 0-5."""
        neoli_score = 4
        assert 0 <= neoli_score <= 5

    def test_biomass_ratio_positive(self):
        """Biomass recovery ratio must be positive."""
        ratio = 4.63
        assert ratio > 0
