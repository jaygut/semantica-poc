"""Tests for the multi-site scaling pipeline (P1).

Covers:
  - API client unit tests (OBIS, WoRMS, Marine Regions) with mocked HTTP
  - SiteCharacterization model validation
  - ESV estimator (habitat -> axiom -> estimate)
  - SiteCharacterizer pipeline (full pipeline with mocked clients)
  - SiteRegistry CRUD and persistence
  - Classifier extension (dynamic site loading, fuzzy matching)
  - Population extension (registered site -> graph)
  - Integration test (name -> characterization -> registry -> population)
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from maris.sites.models import (
    CharacterizationTier,
    CoordinatePair,
    EcosystemServiceEstimate,
    HabitatInfo,
    SiteCharacterization,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def obis_fixture():
    with open(FIXTURES_DIR / "obis_response.json") as f:
        return json.load(f)


@pytest.fixture
def worms_fixture():
    with open(FIXTURES_DIR / "worms_response.json") as f:
        return json.load(f)


@pytest.fixture
def marine_regions_fixture():
    with open(FIXTURES_DIR / "marine_regions_response.json") as f:
        return json.load(f)


@pytest.fixture
def sample_site():
    return SiteCharacterization(
        canonical_name="Test Marine Park",
        tier=CharacterizationTier.silver,
        country="Test Country",
        area_km2=500.0,
        designation_year=2005,
        coordinates=CoordinatePair(latitude=10.0, longitude=120.0),
        neoli_score=3,
        asset_rating="A",
        habitats=[HabitatInfo(habitat_id="coral_reef", name="Coral Reef", extent_km2=200.0)],
        ecosystem_services=[
            EcosystemServiceEstimate(
                service_type="tourism",
                annual_value_usd=5000000.0,
                valuation_method="bridge_axiom_estimate",
            )
        ],
        estimated_esv_usd=5000000.0,
    )


@pytest.fixture
def bronze_site():
    return SiteCharacterization(
        canonical_name="Bronze Atoll MPA",
        tier=CharacterizationTier.bronze,
        country="Maldives",
        area_km2=120.0,
        designation_year=2010,
    )


@pytest.fixture
def tmp_registry(tmp_path):
    return tmp_path / "test_registry.json"


# ---------------------------------------------------------------------------
# 1. Model validation tests
# ---------------------------------------------------------------------------
class TestSiteCharacterizationModel:
    def test_create_bronze_site(self):
        site = SiteCharacterization(
            canonical_name="Minimal MPA",
            tier=CharacterizationTier.bronze,
        )
        assert site.canonical_name == "Minimal MPA"
        assert site.tier == CharacterizationTier.bronze
        assert site.species == []
        assert site.habitats == []

    def test_create_silver_site(self, sample_site):
        assert sample_site.tier == CharacterizationTier.silver
        assert len(sample_site.habitats) == 1
        assert len(sample_site.ecosystem_services) == 1

    def test_neoli_score_validation(self):
        with pytest.raises(ValueError, match="NEOLI score must be between 0 and 5"):
            SiteCharacterization(canonical_name="Bad", neoli_score=6)

    def test_neoli_score_zero_valid(self):
        site = SiteCharacterization(canonical_name="Zero", neoli_score=0)
        assert site.neoli_score == 0

    def test_area_must_be_positive(self):
        with pytest.raises(ValueError, match="Area must be positive"):
            SiteCharacterization(canonical_name="Bad", area_km2=-10.0)

    def test_coordinate_validation(self):
        with pytest.raises(ValueError):
            CoordinatePair(latitude=100.0, longitude=0.0)

    def test_to_population_dict(self, sample_site):
        d = sample_site.to_population_dict()
        assert d["name"] == "Test Marine Park"
        assert d["country"] == "Test Country"
        assert d["area_km2"] == 500.0
        assert d["lat"] == 10.0
        assert d["lon"] == 120.0
        assert d["neoli_score"] == 3
        assert d["asset_rating"] == "A"

    def test_population_dict_without_coordinates(self):
        site = SiteCharacterization(canonical_name="No Coords")
        d = site.to_population_dict()
        assert "lat" not in d
        assert "lon" not in d


# ---------------------------------------------------------------------------
# 2. API client tests (all mocked, no real HTTP)
# ---------------------------------------------------------------------------
class TestOBISClient:
    def test_get_occurrences_parses_results(self, obis_fixture):
        from maris.sites.api_clients import OBISClient

        with patch("maris.sites.api_clients._BaseClient._get", return_value=obis_fixture):
            client = OBISClient()
            results = client.get_occurrences(mpa_name="Cabo Pulmo")

        assert len(results) == 3
        assert results[0]["scientificName"] == "Acropora palmata"
        assert results[0]["aphiaID"] == 206974

    def test_get_occurrences_with_geometry(self, obis_fixture):
        from maris.sites.api_clients import OBISClient

        with patch("maris.sites.api_clients._BaseClient._get", return_value=obis_fixture) as mock_get:
            client = OBISClient()
            client.get_occurrences(geometry="POLYGON((0 0,0 1,1 1,1 0,0 0))")

        call_args = mock_get.call_args
        assert "geometry" in call_args[1]["params"]

    def test_get_occurrences_empty_result(self):
        from maris.sites.api_clients import OBISClient

        with patch("maris.sites.api_clients._BaseClient._get", return_value={"results": []}):
            client = OBISClient()
            results = client.get_occurrences(mpa_name="Nonexistent")

        assert results == []

    def test_get_checklist(self, obis_fixture):
        from maris.sites.api_clients import OBISClient

        with patch("maris.sites.api_clients._BaseClient._get", return_value=obis_fixture):
            client = OBISClient()
            results = client.get_checklist(geometry="POLYGON((0 0,0 1,1 1,1 0,0 0))")

        assert len(results) == 3

    def test_connection_error_raised(self):
        from maris.sites.api_clients import OBISClient

        with patch("maris.sites.api_clients._BaseClient._get", side_effect=ConnectionError("fail")):
            client = OBISClient()
            with pytest.raises(ConnectionError):
                client.get_occurrences(mpa_name="test")


class TestWoRMSClient:
    def test_get_record(self, worms_fixture):
        from maris.sites.api_clients import WoRMSClient

        with patch("maris.sites.api_clients._BaseClient._get", return_value=worms_fixture):
            client = WoRMSClient()
            record = client.get_record(206974)

        assert record["scientificname"] == "Acropora palmata"
        assert record["AphiaID"] == 206974
        assert record["iucn_status"] == "CR"

    def test_search_by_name(self, worms_fixture):
        from maris.sites.api_clients import WoRMSClient

        with patch("maris.sites.api_clients._BaseClient._get", return_value=[worms_fixture]):
            client = WoRMSClient()
            results = client.search_by_name("Acropora palmata")

        assert len(results) == 1
        assert results[0]["scientificname"] == "Acropora palmata"

    def test_get_classification(self):
        from maris.sites.api_clients import WoRMSClient

        classification = {"AphiaID": 206974, "rank": "Species", "scientificname": "Acropora palmata"}
        with patch("maris.sites.api_clients._BaseClient._get", return_value=classification):
            client = WoRMSClient()
            result = client.get_classification(206974)

        assert result["rank"] == "Species"


class TestMarineRegionsClient:
    def test_search_by_name(self, marine_regions_fixture):
        from maris.sites.api_clients import MarineRegionsClient

        with patch("maris.sites.api_clients._BaseClient._get", return_value=marine_regions_fixture):
            client = MarineRegionsClient()
            results = client.search_by_name("Tubbataha")

        assert len(results) == 1
        assert results[0]["MRGID"] == 8364
        assert results[0]["country"] == "Philippines"

    def test_get_by_mrgid(self, marine_regions_fixture):
        from maris.sites.api_clients import MarineRegionsClient

        with patch("maris.sites.api_clients._BaseClient._get", return_value=marine_regions_fixture[0]):
            client = MarineRegionsClient()
            result = client.get_by_mrgid(8364)

        assert result["preferredGazetteerName"] == "Tubbataha Reefs Natural Park"

    def test_get_geometry(self):
        from maris.sites.api_clients import MarineRegionsClient

        geom = {"type": "MultiPolygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}
        with patch("maris.sites.api_clients._BaseClient._get", return_value=[geom]):
            client = MarineRegionsClient()
            result = client.get_geometry(8364)

        assert result["type"] == "MultiPolygon"

    def test_empty_search_result(self):
        from maris.sites.api_clients import MarineRegionsClient

        with patch("maris.sites.api_clients._BaseClient._get", return_value=[]):
            client = MarineRegionsClient()
            results = client.search_by_name("Nonexistent")

        assert results == []


# ---------------------------------------------------------------------------
# 3. ESV estimator tests
# ---------------------------------------------------------------------------
class TestESVEstimator:
    def test_coral_reef_esv(self):
        from maris.sites.esv_estimator import estimate_esv

        habitats = [HabitatInfo(habitat_id="coral_reef", extent_km2=10.0)]
        services, total, conf = estimate_esv(habitats)

        assert len(services) == 3  # tourism, coastal_protection, fisheries
        assert total > 0
        assert conf["ci_low"] < total
        assert conf["ci_high"] > total

    def test_seagrass_esv(self):
        from maris.sites.esv_estimator import estimate_esv

        habitats = [HabitatInfo(habitat_id="seagrass_meadow", extent_km2=100.0)]
        services, total, conf = estimate_esv(habitats)

        assert len(services) == 2  # carbon_sequestration, carbon_credits
        assert total > 0
        # Verify the carbon sequestration estimate uses known per-ha values
        carbon_svc = [s for s in services if s.service_type == "carbon_sequestration"][0]
        # 100 km2 = 10,000 ha, 25.2 USD/ha -> 252,000
        assert carbon_svc.annual_value_usd == pytest.approx(252000.0, rel=0.01)

    def test_mangrove_esv(self):
        from maris.sites.esv_estimator import estimate_esv

        habitats = [HabitatInfo(habitat_id="mangrove_forest", extent_km2=5.0)]
        services, total, conf = estimate_esv(habitats)

        assert len(services) == 3  # coastal_protection, fisheries, carbon_stock
        assert total > 0

    def test_kelp_forest_esv(self):
        from maris.sites.esv_estimator import estimate_esv

        habitats = [HabitatInfo(habitat_id="kelp_forest", extent_km2=20.0)]
        services, total, conf = estimate_esv(habitats)

        assert len(services) == 2  # ecosystem_value, carbon_sequestration
        assert total > 0

    def test_multi_habitat_esv(self):
        from maris.sites.esv_estimator import estimate_esv

        habitats = [
            HabitatInfo(habitat_id="coral_reef", extent_km2=10.0),
            HabitatInfo(habitat_id="seagrass_meadow", extent_km2=50.0),
        ]
        services, total, conf = estimate_esv(habitats)

        assert len(services) == 5  # 3 coral + 2 seagrass
        assert total > 0
        assert len(conf["axiom_chain"]) == 5

    def test_unknown_habitat_returns_empty(self):
        from maris.sites.esv_estimator import estimate_esv

        habitats = [HabitatInfo(habitat_id="unknown_biome")]
        services, total, conf = estimate_esv(habitats)

        assert services == []
        assert total == 0.0

    def test_zero_extent_returns_empty(self):
        from maris.sites.esv_estimator import estimate_esv

        habitats = [HabitatInfo(habitat_id="coral_reef", extent_km2=0.0)]
        services, total, conf = estimate_esv(habitats)

        assert services == []
        assert total == 0.0

    def test_fallback_to_site_area(self):
        from maris.sites.esv_estimator import estimate_esv

        habitats = [HabitatInfo(habitat_id="coral_reef")]  # no extent_km2
        services, total, conf = estimate_esv(habitats, area_km2=10.0)

        assert len(services) == 3
        assert total > 0

    def test_get_applicable_axioms(self):
        from maris.sites.esv_estimator import get_applicable_axioms

        coral_axioms = get_applicable_axioms("coral_reef")
        assert len(coral_axioms) == 3
        assert coral_axioms[0]["axiom_id"] == "BA-001"

        assert get_applicable_axioms("unknown") == []

    def test_axiom_ids_populated(self):
        from maris.sites.esv_estimator import estimate_esv

        habitats = [HabitatInfo(habitat_id="coral_reef", extent_km2=10.0)]
        services, _, _ = estimate_esv(habitats)

        for svc in services:
            assert len(svc.axiom_ids_used) == 1
            assert svc.axiom_ids_used[0].startswith("BA-")


# ---------------------------------------------------------------------------
# 4. Characterizer pipeline tests (all external calls mocked)
# ---------------------------------------------------------------------------
class TestSiteCharacterizer:
    def test_bronze_characterization(self, marine_regions_fixture):
        from maris.sites.characterizer import SiteCharacterizer

        mock_mr = MagicMock()
        mock_mr.search_by_name.return_value = marine_regions_fixture

        characterizer = SiteCharacterizer(
            marine_regions_client=mock_mr,
            obis_client=MagicMock(),
            worms_client=MagicMock(),
        )
        site = characterizer.characterize(
            name="Tubbataha Reefs",
            tier=CharacterizationTier.bronze,
        )

        assert site.canonical_name == "Tubbataha Reefs"
        assert site.tier == CharacterizationTier.bronze
        assert site.country == "Philippines"
        assert site.species == []

    def test_silver_characterization(self, marine_regions_fixture, obis_fixture, worms_fixture):
        from maris.sites.characterizer import SiteCharacterizer

        mock_mr = MagicMock()
        mock_mr.search_by_name.return_value = marine_regions_fixture

        mock_obis = MagicMock()
        mock_obis.get_occurrences.return_value = obis_fixture["results"]

        mock_worms = MagicMock()
        mock_worms.get_record.return_value = worms_fixture

        characterizer = SiteCharacterizer(
            marine_regions_client=mock_mr,
            obis_client=mock_obis,
            worms_client=mock_worms,
        )
        site = characterizer.characterize(
            name="Tubbataha Reefs",
            tier=CharacterizationTier.silver,
            area_km2=970.0,
        )

        assert site.tier == CharacterizationTier.silver
        assert len(site.species) > 0
        assert len(site.habitats) > 0
        assert site.estimated_esv_usd is not None
        assert site.estimated_esv_usd > 0
        assert site.neoli_score is not None
        assert site.asset_rating != ""

    def test_characterization_with_provenance(self, marine_regions_fixture):
        from maris.sites.characterizer import SiteCharacterizer

        mock_prov = MagicMock()
        mock_prov.provenance.record_activity.return_value = None

        characterizer = SiteCharacterizer(
            marine_regions_client=MagicMock(search_by_name=MagicMock(return_value=marine_regions_fixture)),
            obis_client=MagicMock(get_occurrences=MagicMock(return_value=[])),
            worms_client=MagicMock(),
            provenance_manager=mock_prov,
        )
        characterizer.characterize(
            name="Test MPA",
            tier=CharacterizationTier.silver,
        )

        # Provenance should be called for each step
        assert mock_prov.provenance.record_activity.call_count >= 4

    def test_marine_regions_failure_graceful(self):
        from maris.sites.characterizer import SiteCharacterizer

        mock_mr = MagicMock()
        mock_mr.search_by_name.side_effect = ConnectionError("timeout")

        characterizer = SiteCharacterizer(
            marine_regions_client=mock_mr,
            obis_client=MagicMock(get_occurrences=MagicMock(return_value=[])),
            worms_client=MagicMock(),
        )
        site = characterizer.characterize(
            name="Test MPA",
            tier=CharacterizationTier.bronze,
            country="Test",
            coordinates=CoordinatePair(latitude=0.0, longitude=0.0),
        )

        assert site.canonical_name == "Test MPA"
        assert site.country == "Test"

    def test_obis_failure_graceful(self, marine_regions_fixture):
        from maris.sites.characterizer import SiteCharacterizer

        mock_obis = MagicMock()
        mock_obis.get_occurrences.side_effect = ConnectionError("timeout")

        characterizer = SiteCharacterizer(
            marine_regions_client=MagicMock(search_by_name=MagicMock(return_value=marine_regions_fixture)),
            obis_client=mock_obis,
            worms_client=MagicMock(),
        )
        site = characterizer.characterize(
            name="Test MPA",
            tier=CharacterizationTier.silver,
            area_km2=100.0,
        )

        assert site.species == []

    def test_worms_failure_graceful(self, marine_regions_fixture, obis_fixture):
        from maris.sites.characterizer import SiteCharacterizer

        mock_worms = MagicMock()
        mock_worms.get_record.side_effect = ConnectionError("timeout")

        characterizer = SiteCharacterizer(
            marine_regions_client=MagicMock(search_by_name=MagicMock(return_value=marine_regions_fixture)),
            obis_client=MagicMock(get_occurrences=MagicMock(return_value=obis_fixture["results"])),
            worms_client=mock_worms,
        )
        site = characterizer.characterize(
            name="Test MPA",
            tier=CharacterizationTier.silver,
            area_km2=100.0,
        )

        # Species should still be populated from OBIS data even if WoRMS fails
        assert len(site.species) > 0

    def test_neoli_scoring(self, marine_regions_fixture):
        from maris.sites.characterizer import SiteCharacterizer

        characterizer = SiteCharacterizer(
            marine_regions_client=MagicMock(search_by_name=MagicMock(return_value=marine_regions_fixture)),
            obis_client=MagicMock(get_occurrences=MagicMock(return_value=[])),
            worms_client=MagicMock(),
        )
        site = characterizer.characterize(
            name="Old Large MPA",
            tier=CharacterizationTier.silver,
            area_km2=500.0,
            designation_year=2000,
        )

        # Should score: no_take=True, enforced=True, old=True (>10yr), large=True (>100km2), isolated=False
        assert site.neoli_score == 4
        assert site.neoli_criteria["large"] is True
        assert site.neoli_criteria["old"] is True
        assert site.neoli_criteria["isolated"] is False

    def test_habitat_inference_coral(self, marine_regions_fixture):
        from maris.sites.characterizer import SiteCharacterizer

        # OBIS returns coral species
        coral_occurrences = [
            {"scientificName": "Acropora palmata", "aphiaID": 206974},
            {"scientificName": "Porites lobata", "aphiaID": 207003},
        ]

        characterizer = SiteCharacterizer(
            marine_regions_client=MagicMock(search_by_name=MagicMock(return_value=marine_regions_fixture)),
            obis_client=MagicMock(get_occurrences=MagicMock(return_value=coral_occurrences)),
            worms_client=MagicMock(get_record=MagicMock(return_value={})),
        )
        site = characterizer.characterize(
            name="Coral Site",
            tier=CharacterizationTier.silver,
            area_km2=50.0,
        )

        habitat_ids = [h.habitat_id for h in site.habitats]
        assert "coral_reef" in habitat_ids

    def test_habitat_inference_seagrass(self, marine_regions_fixture):
        from maris.sites.characterizer import SiteCharacterizer

        seagrass_occurrences = [
            {"scientificName": "Posidonia australis", "aphiaID": 145795},
            {"scientificName": "Zostera marina", "aphiaID": 145793},
        ]

        characterizer = SiteCharacterizer(
            marine_regions_client=MagicMock(search_by_name=MagicMock(return_value=marine_regions_fixture)),
            obis_client=MagicMock(get_occurrences=MagicMock(return_value=seagrass_occurrences)),
            worms_client=MagicMock(get_record=MagicMock(return_value={})),
        )
        site = characterizer.characterize(
            name="Seagrass Site",
            tier=CharacterizationTier.silver,
            area_km2=100.0,
        )

        habitat_ids = [h.habitat_id for h in site.habitats]
        assert "seagrass_meadow" in habitat_ids


# ---------------------------------------------------------------------------
# 5. Site registry tests
# ---------------------------------------------------------------------------
class TestSiteRegistry:
    def test_add_and_get_site(self, tmp_registry, sample_site):
        from maris.sites.registry import SiteRegistry

        registry = SiteRegistry(tmp_registry)
        registry.add_site(sample_site)

        retrieved = registry.get_site("Test Marine Park")
        assert retrieved is not None
        assert retrieved.canonical_name == "Test Marine Park"
        assert retrieved.country == "Test Country"

    def test_duplicate_add_raises(self, tmp_registry, sample_site):
        from maris.sites.registry import SiteRegistry

        registry = SiteRegistry(tmp_registry)
        registry.add_site(sample_site)

        with pytest.raises(ValueError, match="already exists"):
            registry.add_site(sample_site)

    def test_update_site(self, tmp_registry, sample_site):
        from maris.sites.registry import SiteRegistry

        registry = SiteRegistry(tmp_registry)
        registry.add_site(sample_site)

        sample_site.estimated_esv_usd = 10000000.0
        registry.update_site(sample_site)

        retrieved = registry.get_site("Test Marine Park")
        assert retrieved.estimated_esv_usd == 10000000.0

    def test_update_nonexistent_raises(self, tmp_registry, sample_site):
        from maris.sites.registry import SiteRegistry

        registry = SiteRegistry(tmp_registry)
        with pytest.raises(KeyError, match="not found"):
            registry.update_site(sample_site)

    def test_remove_site(self, tmp_registry, sample_site):
        from maris.sites.registry import SiteRegistry

        registry = SiteRegistry(tmp_registry)
        registry.add_site(sample_site)
        assert registry.remove_site("Test Marine Park") is True
        assert registry.get_site("Test Marine Park") is None

    def test_remove_nonexistent(self, tmp_registry):
        from maris.sites.registry import SiteRegistry

        registry = SiteRegistry(tmp_registry)
        assert registry.remove_site("Nonexistent") is False

    def test_list_sites(self, tmp_registry, sample_site, bronze_site):
        from maris.sites.registry import SiteRegistry

        registry = SiteRegistry(tmp_registry)
        registry.add_site(sample_site)
        registry.add_site(bronze_site)

        sites = registry.list_sites()
        assert len(sites) == 2
        # Sorted by name: "Bronze Atoll MPA" < "Test Marine Park"
        assert sites[0].canonical_name == "Bronze Atoll MPA"

    def test_filter_by_tier(self, tmp_registry, sample_site, bronze_site):
        from maris.sites.registry import SiteRegistry

        registry = SiteRegistry(tmp_registry)
        registry.add_site(sample_site)
        registry.add_site(bronze_site)

        bronze_sites = registry.filter_by_tier(CharacterizationTier.bronze)
        assert len(bronze_sites) == 1
        assert bronze_sites[0].canonical_name == "Bronze Atoll MPA"

    def test_persistence(self, tmp_registry, sample_site):
        from maris.sites.registry import SiteRegistry

        registry = SiteRegistry(tmp_registry)
        registry.add_site(sample_site)

        # Reload from disk
        registry2 = SiteRegistry(tmp_registry)
        assert registry2.count() == 1
        assert registry2.get_site("Test Marine Park") is not None

    def test_contains(self, tmp_registry, sample_site):
        from maris.sites.registry import SiteRegistry

        registry = SiteRegistry(tmp_registry)
        registry.add_site(sample_site)

        assert registry.contains("Test Marine Park") is True
        assert registry.contains("Nonexistent") is False

    def test_get_site_names(self, tmp_registry, sample_site, bronze_site):
        from maris.sites.registry import SiteRegistry

        registry = SiteRegistry(tmp_registry)
        registry.add_site(sample_site)
        registry.add_site(bronze_site)

        names = registry.get_site_names()
        assert "Test Marine Park" in names
        assert "Bronze Atoll MPA" in names

    def test_validate_bronze_ok(self, tmp_registry, bronze_site):
        from maris.sites.registry import SiteRegistry

        registry = SiteRegistry(tmp_registry)
        issues = registry.validate_site(bronze_site)
        assert issues == []

    def test_validate_silver_missing_habitats(self, tmp_registry):
        from maris.sites.registry import SiteRegistry

        site = SiteCharacterization(
            canonical_name="Bad Silver",
            tier=CharacterizationTier.silver,
        )
        registry = SiteRegistry(tmp_registry)
        issues = registry.validate_site(site)
        assert any("habitat" in i.lower() for i in issues)

    def test_validate_gold_missing_esv(self, tmp_registry):
        from maris.sites.registry import SiteRegistry

        site = SiteCharacterization(
            canonical_name="Bad Gold",
            tier=CharacterizationTier.gold,
            habitats=[HabitatInfo(habitat_id="coral_reef")],
            ecosystem_services=[EcosystemServiceEstimate(service_type="tourism")],
        )
        registry = SiteRegistry(tmp_registry)
        issues = registry.validate_site(site)
        assert any("ESV" in i for i in issues)
        assert any("species" in i.lower() for i in issues)

    def test_export_site_json(self, tmp_registry, sample_site):
        from maris.sites.registry import SiteRegistry

        registry = SiteRegistry(tmp_registry)
        registry.add_site(sample_site)

        exported = registry.export_site_json("Test Marine Park")
        assert exported["canonical_name"] == "Test Marine Park"
        assert exported["tier"] == "silver"

    def test_in_memory_registry(self, sample_site):
        from maris.sites.registry import SiteRegistry

        registry = SiteRegistry()  # No path = in-memory only
        registry.add_site(sample_site)
        assert registry.count() == 1


# ---------------------------------------------------------------------------
# 6. Classifier extension tests
# ---------------------------------------------------------------------------
class TestClassifierDynamicSites:
    def test_register_dynamic_sites(self):
        from maris.query.classifier import register_dynamic_sites, get_all_canonical_sites

        count = register_dynamic_sites(["Raja Ampat Marine Park", "Cenderawasih Bay MPA"])
        assert count == 2

        all_sites = get_all_canonical_sites()
        assert "Raja Ampat Marine Park" in all_sites
        assert "Cenderawasih Bay MPA" in all_sites

        # Clean up
        register_dynamic_sites([])

    def test_dynamic_site_detected_in_query(self):
        from maris.query.classifier import QueryClassifier, register_dynamic_sites

        register_dynamic_sites(["Raja Ampat Marine Park"])
        classifier = QueryClassifier()
        result = classifier.classify("What is the ESV of Raja Ampat Marine Park?")

        assert result["site"] == "Raja Ampat Marine Park"

        # Clean up
        register_dynamic_sites([])

    def test_fuzzy_match_dynamic_site(self):
        from maris.query.classifier import QueryClassifier, register_dynamic_sites

        register_dynamic_sites(["Tubbataha Reefs Natural Park"])
        classifier = QueryClassifier()

        # Fuzzy match: "Tubbataha Reefs" should resolve to the registered name
        result = classifier.classify("What is Tubbataha Reefs worth?")
        assert result["site"] == "Tubbataha Reefs Natural Park"

        # Clean up
        register_dynamic_sites([])

    def test_static_sites_still_work(self):
        from maris.query.classifier import QueryClassifier

        classifier = QueryClassifier()
        result = classifier.classify("What is the ESV of Cabo Pulmo?")
        assert result["site"] == "Cabo Pulmo National Park"

    def test_get_all_canonical_sites_no_duplicates(self):
        from maris.query.classifier import register_dynamic_sites, get_all_canonical_sites

        # Register a site that's already static
        register_dynamic_sites(["Cabo Pulmo National Park", "New Site MPA"])
        all_sites = get_all_canonical_sites()

        # Should not have duplicates
        assert all_sites.count("Cabo Pulmo National Park") == 1
        assert "New Site MPA" in all_sites

        # Clean up
        register_dynamic_sites([])


# ---------------------------------------------------------------------------
# 7. Population extension tests
# ---------------------------------------------------------------------------
class TestPopulateRegisteredSites:
    def test_bronze_site_creates_mpa_only(self, tmp_registry, bronze_site):
        from maris.sites.registry import SiteRegistry
        from maris.graph.population import _populate_registered_sites

        registry = SiteRegistry(tmp_registry)
        registry.add_site(bronze_site)

        mock_session = MagicMock()
        count = _populate_registered_sites(mock_session, tmp_registry)

        assert count == 1
        # Only the MPA MERGE, no species/habitat/service calls
        assert mock_session.run.call_count == 1

    def test_silver_site_creates_full_subgraph(self, tmp_registry, sample_site):
        from maris.sites.registry import SiteRegistry
        from maris.graph.population import _populate_registered_sites

        registry = SiteRegistry(tmp_registry)
        registry.add_site(sample_site)

        mock_session = MagicMock()
        count = _populate_registered_sites(mock_session, tmp_registry)

        # MPA + 1 habitat (MERGE + HAS_HABITAT) + 1 service (MERGE + GENERATES)
        assert count >= 3
        assert mock_session.run.call_count >= 5  # MPA, habitat MERGE, HAS_HABITAT, service MERGE, GENERATES

    def test_no_registry_returns_zero(self):
        from maris.graph.population import _populate_registered_sites

        mock_session = MagicMock()
        count = _populate_registered_sites(mock_session, None)
        assert count == 0

    def test_empty_registry_returns_zero(self, tmp_registry):
        from maris.sites.registry import SiteRegistry
        from maris.graph.population import _populate_registered_sites

        SiteRegistry(tmp_registry)  # Create empty registry file

        mock_session = MagicMock()
        count = _populate_registered_sites(mock_session, tmp_registry)
        assert count == 0

    def test_gold_site_with_case_study_skipped(self, tmp_registry):
        from maris.sites.registry import SiteRegistry
        from maris.graph.population import _populate_registered_sites

        gold_site = SiteCharacterization(
            canonical_name="Gold MPA",
            tier=CharacterizationTier.gold,
            case_study_path="/examples/gold_case_study.json",
        )
        registry = SiteRegistry(tmp_registry)
        registry.add_site(gold_site)

        mock_session = MagicMock()
        count = _populate_registered_sites(mock_session, tmp_registry)

        # Gold with case_study_path should be skipped (handled by full population)
        assert count == 0


# ---------------------------------------------------------------------------
# 8. Integration test
# ---------------------------------------------------------------------------
class TestIntegration:
    def test_full_pipeline(self, tmp_registry, marine_regions_fixture, obis_fixture, worms_fixture):
        """End-to-end: name -> characterize -> registry -> population data."""
        from maris.sites.characterizer import SiteCharacterizer
        from maris.sites.registry import SiteRegistry
        from maris.graph.population import _populate_registered_sites

        # Step 1: Characterize
        characterizer = SiteCharacterizer(
            marine_regions_client=MagicMock(search_by_name=MagicMock(return_value=marine_regions_fixture)),
            obis_client=MagicMock(get_occurrences=MagicMock(return_value=obis_fixture["results"])),
            worms_client=MagicMock(get_record=MagicMock(return_value=worms_fixture)),
        )
        site = characterizer.characterize(
            name="Tubbataha Reefs Natural Park",
            tier=CharacterizationTier.silver,
            area_km2=970.0,
        )

        assert site.canonical_name == "Tubbataha Reefs Natural Park"
        assert site.tier == CharacterizationTier.silver
        assert len(site.species) > 0
        assert len(site.habitats) > 0
        assert site.estimated_esv_usd > 0

        # Step 2: Register
        registry = SiteRegistry(tmp_registry)
        registry.add_site(site)
        assert registry.count() == 1

        # Step 3: Populate graph (mocked session)
        mock_session = MagicMock()
        count = _populate_registered_sites(mock_session, tmp_registry)
        assert count > 0
        mock_session.run.assert_called()

    def test_classifier_recognizes_registered_site(self, tmp_registry, sample_site):
        """After registration, the classifier should find the site."""
        from maris.sites.registry import SiteRegistry
        from maris.query.classifier import QueryClassifier, register_dynamic_sites

        registry = SiteRegistry(tmp_registry)
        registry.add_site(sample_site)

        register_dynamic_sites(registry.get_site_names())
        classifier = QueryClassifier()
        result = classifier.classify("What is Test Marine Park worth?")

        assert result["site"] == "Test Marine Park"

        # Clean up
        register_dynamic_sites([])
