"""Unit tests for the enhanced SiteCharacterizer pipeline and API clients.

Covers:
  - WoRMS get_attributes() and get_classification() methods
  - OBIS get_checklist() with mpa_name parameter
  - Marine Regions get_geometry() returning boundary WKT
  - flatten_classification() helper
  - Habitat inference scoring with taxonomic hierarchy and functional groups
  - ESV estimation with known habitat + area
  - Full Silver tier pipeline with mocked APIs

All tests use unittest.mock - no real HTTP calls are made.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from maris.sites.api_clients import (
    MarineRegionsClient,
    OBISClient,
    WoRMSClient,
    flatten_classification,
)
from maris.sites.characterizer import SiteCharacterizer
from maris.sites.esv_estimator import estimate_esv
from maris.sites.models import (
    CharacterizationTier,
    HabitatInfo,
    SpeciesRecord,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_response(
    status_code: int = 200,
    content: bytes = b"",
    json_data: dict | list | None = None,
) -> MagicMock:
    """Build a mock httpx.Response."""
    import json

    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    resp.raise_for_status = MagicMock()
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
    return resp


# ---------------------------------------------------------------------------
# 1. flatten_classification helper
# ---------------------------------------------------------------------------

class TestFlattenClassification:
    """Tests for the flatten_classification utility."""

    def test_nested_hierarchy_is_flattened(self) -> None:
        """A nested WoRMS classification tree is flattened to {rank: name}."""
        tree = {
            "AphiaID": 1,
            "rank": "Kingdom",
            "scientificname": "Animalia",
            "child": {
                "AphiaID": 2,
                "rank": "Phylum",
                "scientificname": "Cnidaria",
                "child": {
                    "AphiaID": 3,
                    "rank": "Class",
                    "scientificname": "Anthozoa",
                    "child": {
                        "AphiaID": 4,
                        "rank": "Order",
                        "scientificname": "Scleractinia",
                        "child": {
                            "AphiaID": 5,
                            "rank": "Family",
                            "scientificname": "Acroporidae",
                            "child": {
                                "AphiaID": 6,
                                "rank": "Genus",
                                "scientificname": "Acropora",
                                "child": None,
                            },
                        },
                    },
                },
            },
        }
        flat = flatten_classification(tree)
        assert flat == {
            "Kingdom": "Animalia",
            "Phylum": "Cnidaria",
            "Class": "Anthozoa",
            "Order": "Scleractinia",
            "Family": "Acroporidae",
            "Genus": "Acropora",
        }

    def test_empty_dict_returns_empty(self) -> None:
        assert flatten_classification({}) == {}

    def test_single_node_no_child(self) -> None:
        flat = flatten_classification({"rank": "Species", "scientificname": "Foo bar"})
        assert flat == {"Species": "Foo bar"}


# ---------------------------------------------------------------------------
# 2. WoRMS client - get_attributes and get_classification
# ---------------------------------------------------------------------------

class TestWoRMSAttributes:
    """WoRMS get_attributes() returns a list of attribute dicts."""

    def test_get_attributes_returns_list(self) -> None:
        attrs = [
            {"measurementType": "Functional group", "measurementValue": "reef-associated"},
            {"measurementType": "Trophic level", "measurementValue": "3.5"},
        ]
        resp = _make_mock_response(
            status_code=200,
            content=b'[...]',
            json_data=attrs,
        )
        with patch("maris.sites.api_clients.httpx.get", return_value=resp):
            client = WoRMSClient(max_retries=1)
            result = client.get_attributes(206974)
        assert result == attrs

    def test_get_attributes_204_returns_empty_list(self) -> None:
        resp = _make_mock_response(status_code=204, content=b"")
        with patch("maris.sites.api_clients.httpx.get", return_value=resp):
            client = WoRMSClient(max_retries=1)
            result = client.get_attributes(999999999)
        assert result == []

    def test_get_classification_returns_nested_dict(self) -> None:
        tree = {
            "rank": "Kingdom",
            "scientificname": "Animalia",
            "child": {"rank": "Phylum", "scientificname": "Cnidaria", "child": None},
        }
        resp = _make_mock_response(
            status_code=200,
            content=b'{...}',
            json_data=tree,
        )
        with patch("maris.sites.api_clients.httpx.get", return_value=resp):
            client = WoRMSClient(max_retries=1)
            result = client.get_classification(206974)
        assert result["rank"] == "Kingdom"
        assert result["child"]["rank"] == "Phylum"


# ---------------------------------------------------------------------------
# 3. OBIS client - get_checklist with mpa_name
# ---------------------------------------------------------------------------

class TestOBISChecklist:
    """OBIS get_checklist() with mpa_name parameter."""

    def test_get_checklist_with_mpa_name(self) -> None:
        obis_data = {
            "results": [
                {"scientificName": "Acropora palmata", "aphiaID": 206974},
                {"scientificName": "Posidonia australis", "aphiaID": 145795},
            ]
        }
        resp = _make_mock_response(
            status_code=200,
            content=b'{...}',
            json_data=obis_data,
        )
        with patch("maris.sites.api_clients.httpx.get", return_value=resp) as mock_get:
            client = OBISClient(max_retries=1)
            results = client.get_checklist(mpa_name="Tubbataha Reefs Natural Park")
        assert len(results) == 2
        assert results[0]["scientificName"] == "Acropora palmata"
        # Verify areaid param was sent
        call_kwargs = mock_get.call_args
        assert "areaid" in call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))

    def test_get_checklist_with_geometry(self) -> None:
        obis_data = {"results": [{"scientificName": "Foo bar", "aphiaID": 1}]}
        resp = _make_mock_response(
            status_code=200,
            content=b'{...}',
            json_data=obis_data,
        )
        with patch("maris.sites.api_clients.httpx.get", return_value=resp) as mock_get:
            client = OBISClient(max_retries=1)
            results = client.get_checklist(geometry="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
        assert len(results) == 1
        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))
        assert "geometry" in params

    def test_get_checklist_204_returns_empty(self) -> None:
        resp = _make_mock_response(status_code=204, content=b"")
        with patch("maris.sites.api_clients.httpx.get", return_value=resp):
            client = OBISClient(max_retries=1)
            results = client.get_checklist(mpa_name="Nonexistent")
        assert results == []


# ---------------------------------------------------------------------------
# 4. Marine Regions - get_geometry returning boundary data
# ---------------------------------------------------------------------------

class TestMarineRegionsGeometry:
    """Marine Regions get_geometry() returns boundary polygon data."""

    def test_get_geometry_returns_first_entry(self) -> None:
        geom_data = [{"the_geom": "POLYGON((119 8, 120 8, 120 10, 119 10, 119 8))"}]
        resp = _make_mock_response(
            status_code=200,
            content=b'[...]',
            json_data=geom_data,
        )
        with patch("maris.sites.api_clients.httpx.get", return_value=resp):
            client = MarineRegionsClient(max_retries=1)
            result = client.get_geometry(8364)
        assert "the_geom" in result
        assert "POLYGON" in result["the_geom"]

    def test_get_geometry_204_returns_empty(self) -> None:
        resp = _make_mock_response(status_code=204, content=b"")
        with patch("maris.sites.api_clients.httpx.get", return_value=resp):
            client = MarineRegionsClient(max_retries=1)
            result = client.get_geometry(999999)
        assert result == {}


# ---------------------------------------------------------------------------
# 5. Habitat inference scoring with known species sets
# ---------------------------------------------------------------------------

class TestHabitatInference:
    """Test the enhanced habitat inference scoring system."""

    def _make_coral_species(self) -> list[SpeciesRecord]:
        """Create species records that indicate a coral reef."""
        sp1 = SpeciesRecord(
            scientific_name="Acropora palmata",
            worms_aphia_id=206974,
            functional_group="reef-associated",
        )
        sp1._classification = {  # type: ignore[attr-defined]
            "Kingdom": "Animalia",
            "Phylum": "Cnidaria",
            "Class": "Anthozoa",
            "Order": "Scleractinia",
            "Family": "Acroporidae",
            "Genus": "Acropora",
        }
        sp2 = SpeciesRecord(
            scientific_name="Porites lobata",
            worms_aphia_id=207000,
        )
        sp2._classification = {  # type: ignore[attr-defined]
            "Order": "Scleractinia",
            "Family": "Poritidae",
        }
        sp3 = SpeciesRecord(
            scientific_name="Lutjanus argentiventris",
            worms_aphia_id=281326,
        )
        return [sp1, sp2, sp3]

    def _make_seagrass_species(self) -> list[SpeciesRecord]:
        """Create species records that indicate a seagrass meadow."""
        sp1 = SpeciesRecord(
            scientific_name="Posidonia australis",
            worms_aphia_id=145795,
            functional_group="seagrass",
        )
        sp1._classification = {  # type: ignore[attr-defined]
            "Order": "Alismatales",
            "Family": "Posidoniaceae",
        }
        sp2 = SpeciesRecord(
            scientific_name="Zostera marina",
            worms_aphia_id=145790,
        )
        sp2._classification = {  # type: ignore[attr-defined]
            "Order": "Alismatales",
            "Family": "Zosteraceae",
        }
        return [sp1, sp2]

    def test_coral_species_infer_coral_reef(self) -> None:
        """Coral indicator species + taxonomy = coral_reef as primary habitat."""
        from maris.sites.characterizer import SiteCharacterizer
        from maris.sites.models import SiteCharacterization

        species = self._make_coral_species()
        site = SiteCharacterization(canonical_name="Test Reef", area_km2=100.0)
        char = SiteCharacterizer()
        habitats = char._step_characterize_habitat(site, species)

        assert len(habitats) >= 1
        assert habitats[0].habitat_id == "coral_reef"
        assert habitats[0].confidence > 0

    def test_seagrass_species_infer_seagrass_meadow(self) -> None:
        """Seagrass indicator species + taxonomy = seagrass_meadow."""
        from maris.sites.models import SiteCharacterization

        species = self._make_seagrass_species()
        site = SiteCharacterization(canonical_name="Test Seagrass", area_km2=500.0)
        char = SiteCharacterizer()
        habitats = char._step_characterize_habitat(site, species)

        assert len(habitats) >= 1
        assert habitats[0].habitat_id == "seagrass_meadow"
        assert habitats[0].confidence > 0

    def test_mixed_species_returns_multiple_habitats(self) -> None:
        """A mix of coral and seagrass species returns both habitats."""
        from maris.sites.models import SiteCharacterization

        species = self._make_coral_species() + self._make_seagrass_species()
        site = SiteCharacterization(canonical_name="Mixed", area_km2=200.0)
        char = SiteCharacterizer()
        habitats = char._step_characterize_habitat(site, species)

        hab_ids = [h.habitat_id for h in habitats]
        assert "coral_reef" in hab_ids
        assert "seagrass_meadow" in hab_ids

    def test_empty_species_returns_no_habitats(self) -> None:
        """No species = no habitats inferred."""
        from maris.sites.models import SiteCharacterization

        site = SiteCharacterization(canonical_name="Empty", area_km2=100.0)
        char = SiteCharacterizer()
        habitats = char._step_characterize_habitat(site, [])
        assert habitats == []

    def test_taxonomic_indicators_boost_score(self) -> None:
        """Species with Scleractinia order get +3 taxonomic boost."""
        from maris.sites.models import SiteCharacterization

        # One species with only taxonomic info (no keyword match)
        sp = SpeciesRecord(scientific_name="Unknown sp.", worms_aphia_id=1)
        sp._classification = {"Order": "Scleractinia", "Family": "Merulinidae"}  # type: ignore[attr-defined]
        site = SiteCharacterization(canonical_name="Tax Test", area_km2=50.0)
        char = SiteCharacterizer()
        habitats = char._step_characterize_habitat(site, [sp])

        assert len(habitats) >= 1
        assert habitats[0].habitat_id == "coral_reef"

    def test_functional_group_contributes_to_score(self) -> None:
        """A species with functional_group='reef-associated' boosts coral_reef."""
        from maris.sites.models import SiteCharacterization

        sp = SpeciesRecord(
            scientific_name="Generic fish sp.",
            worms_aphia_id=2,
            functional_group="reef-associated",
        )
        site = SiteCharacterization(canonical_name="FG Test", area_km2=50.0)
        char = SiteCharacterizer()
        habitats = char._step_characterize_habitat(site, [sp])

        assert len(habitats) >= 1
        assert habitats[0].habitat_id == "coral_reef"


# ---------------------------------------------------------------------------
# 6. ESV estimation with known habitat + area
# ---------------------------------------------------------------------------

class TestESVEstimation:
    """ESV estimation from habitat type and area."""

    def test_coral_reef_esv_is_positive(self) -> None:
        habitats = [HabitatInfo(habitat_id="coral_reef", extent_km2=100.0)]
        services, total, confidence = estimate_esv(habitats)
        assert total > 0
        assert len(services) > 0
        assert confidence["ci_low"] < total < confidence["ci_high"]

    def test_seagrass_meadow_esv(self) -> None:
        habitats = [HabitatInfo(habitat_id="seagrass_meadow", extent_km2=4800.0)]
        services, total, confidence = estimate_esv(habitats)
        assert total > 0
        svc_types = [s.service_type for s in services]
        assert "carbon_sequestration" in svc_types

    def test_unknown_habitat_returns_zero(self) -> None:
        habitats = [HabitatInfo(habitat_id="deep_ocean", extent_km2=1000.0)]
        services, total, _ = estimate_esv(habitats)
        assert total == 0.0
        assert services == []

    def test_multiple_habitats_sum_correctly(self) -> None:
        habitats = [
            HabitatInfo(habitat_id="coral_reef", extent_km2=50.0),
            HabitatInfo(habitat_id="seagrass_meadow", extent_km2=200.0),
        ]
        services, total, confidence = estimate_esv(habitats)
        assert total > 0
        assert len(services) >= 4  # 3 coral + 2 seagrass
        assert abs(total - sum(s.annual_value_usd for s in services)) < 0.01

    def test_esv_with_zero_area_returns_zero(self) -> None:
        habitats = [HabitatInfo(habitat_id="coral_reef", extent_km2=0.0)]
        _, total, _ = estimate_esv(habitats)
        assert total == 0.0


# ---------------------------------------------------------------------------
# 7. Full Silver tier pipeline with mocked APIs
# ---------------------------------------------------------------------------

class TestSilverTierPipeline:
    """Full Silver characterization with all external APIs mocked."""

    def _build_mocked_characterizer(self) -> SiteCharacterizer:
        """Build a SiteCharacterizer with fully mocked clients."""
        obis = OBISClient(max_retries=1)
        worms = WoRMSClient(max_retries=1)
        mr = MarineRegionsClient(max_retries=1)
        return SiteCharacterizer(
            obis_client=obis,
            worms_client=worms,
            marine_regions_client=mr,
        )

    def _mock_marine_regions_search(self) -> list[dict]:
        return [{
            "MRGID": 8364,
            "preferredGazetteerName": "Tubbataha Reefs Natural Park",
            "latitude": 9.47,
            "longitude": 119.87,
            "country": "Philippines",
            "area_km2": 970.0,
            "year": 1988,
        }]

    def _mock_marine_regions_geometry(self) -> dict:
        return {"the_geom": "POLYGON((119 8, 120 8, 120 10, 119 10, 119 8))"}

    def _mock_obis_checklist(self) -> dict:
        return {
            "results": [
                {"scientificName": "Acropora palmata", "aphiaID": 206974, "taxonID": 206974},
                {"scientificName": "Porites lobata", "aphiaID": 207000, "taxonID": 207000},
                {"scientificName": "Lutjanus argentiventris", "aphiaID": 281326, "taxonID": 281326},
            ]
        }

    def _mock_worms_record(self, aphia_id: int) -> dict:
        records = {
            206974: {"scientificname": "Acropora palmata", "iucn_status": "CR"},
            207000: {"scientificname": "Porites lobata", "iucn_status": "LC"},
            281326: {"scientificname": "Lutjanus argentiventris", "iucn_status": "LC"},
        }
        return records.get(aphia_id, {})

    def _mock_worms_classification(self, aphia_id: int) -> dict:
        classifications = {
            206974: {
                "rank": "Kingdom", "scientificname": "Animalia",
                "child": {
                    "rank": "Phylum", "scientificname": "Cnidaria",
                    "child": {
                        "rank": "Class", "scientificname": "Anthozoa",
                        "child": {
                            "rank": "Order", "scientificname": "Scleractinia",
                            "child": {
                                "rank": "Family", "scientificname": "Acroporidae",
                                "child": {"rank": "Genus", "scientificname": "Acropora", "child": None},
                            },
                        },
                    },
                },
            },
            207000: {
                "rank": "Order", "scientificname": "Scleractinia",
                "child": {
                    "rank": "Family", "scientificname": "Poritidae",
                    "child": None,
                },
            },
            281326: {
                "rank": "Order", "scientificname": "Perciformes",
                "child": {
                    "rank": "Family", "scientificname": "Lutjanidae",
                    "child": None,
                },
            },
        }
        return classifications.get(aphia_id, {})

    def _mock_worms_attributes(self, aphia_id: int) -> list:
        attrs = {
            206974: [
                {"measurementType": "Functional group", "measurementValue": "reef-associated"},
            ],
            207000: [
                {"measurementType": "Functional group", "measurementValue": "reef-associated"},
            ],
            281326: [
                {"measurementType": "Functional group", "measurementValue": "reef-associated"},
                {"measurementType": "Trophic level", "measurementValue": "3.5"},
            ],
        }
        return attrs.get(aphia_id, [])

    def test_silver_produces_species_habitats_esv(self) -> None:
        """Full Silver pipeline populates species, habitats, and ESV."""
        char = self._build_mocked_characterizer()

        with patch.object(char._mr, "search_by_name", return_value=self._mock_marine_regions_search()), \
             patch.object(char._mr, "get_geometry", return_value=self._mock_marine_regions_geometry()), \
             patch.object(char._obis, "get_checklist", return_value=self._mock_obis_checklist()["results"]), \
             patch.object(char._worms, "get_record", side_effect=self._mock_worms_record), \
             patch.object(char._worms, "get_classification", side_effect=self._mock_worms_classification), \
             patch.object(char._worms, "get_attributes", side_effect=self._mock_worms_attributes):

            site = char.characterize(
                name="Tubbataha Reefs Natural Park",
                tier=CharacterizationTier.silver,
            )

        # Species populated
        assert len(site.species) == 3
        assert site.species[0].scientific_name == "Acropora palmata"
        assert site.species[0].conservation_status == "CR"

        # Habitats inferred - coral_reef should be dominant
        assert len(site.habitats) >= 1
        assert site.habitats[0].habitat_id == "coral_reef"
        assert site.habitats[0].confidence > 0

        # ESV estimated
        assert site.estimated_esv_usd is not None
        assert site.estimated_esv_usd > 0
        assert len(site.ecosystem_services) > 0

        # NEOLI score and rating
        assert site.neoli_score is not None
        assert site.neoli_score >= 3  # old, large, designated
        assert site.asset_rating in ("A", "AA", "AAA")

        # Tier set correctly
        assert site.tier == CharacterizationTier.silver

    def test_silver_with_enriched_attributes(self) -> None:
        """Verify that WoRMS attributes (functional group, trophic level) are set."""
        char = self._build_mocked_characterizer()

        with patch.object(char._mr, "search_by_name", return_value=self._mock_marine_regions_search()), \
             patch.object(char._mr, "get_geometry", return_value=self._mock_marine_regions_geometry()), \
             patch.object(char._obis, "get_checklist", return_value=self._mock_obis_checklist()["results"]), \
             patch.object(char._worms, "get_record", side_effect=self._mock_worms_record), \
             patch.object(char._worms, "get_classification", side_effect=self._mock_worms_classification), \
             patch.object(char._worms, "get_attributes", side_effect=self._mock_worms_attributes):

            site = char.characterize(
                name="Tubbataha Reefs Natural Park",
                tier=CharacterizationTier.silver,
            )

        # Acropora should have functional group set
        acropora = next(s for s in site.species if s.worms_aphia_id == 206974)
        assert acropora.functional_group == "reef-associated"

        # Lutjanus should have trophic level set
        lutjanus = next(s for s in site.species if s.worms_aphia_id == 281326)
        assert lutjanus.trophic_level == 3.5
        assert lutjanus.functional_group == "reef-associated"

    def test_silver_fallback_to_occurrences_when_checklist_empty(self) -> None:
        """If checklist returns empty, pipeline falls back to occurrences."""
        char = self._build_mocked_characterizer()

        occurrence_data = [
            {"scientificName": "Acropora palmata", "aphiaID": 206974, "taxonID": 206974},
        ]

        with patch.object(char._mr, "search_by_name", return_value=self._mock_marine_regions_search()), \
             patch.object(char._mr, "get_geometry", return_value=self._mock_marine_regions_geometry()), \
             patch.object(char._obis, "get_checklist", return_value=[]), \
             patch.object(char._obis, "get_occurrences", return_value=occurrence_data) as mock_occ, \
             patch.object(char._worms, "get_record", return_value={"scientificname": "Acropora palmata", "iucn_status": "CR"}), \
             patch.object(char._worms, "get_classification", return_value={"rank": "Order", "scientificname": "Scleractinia", "child": None}), \
             patch.object(char._worms, "get_attributes", return_value=[]):

            site = char.characterize(
                name="Tubbataha Reefs Natural Park",
                tier=CharacterizationTier.silver,
            )

        mock_occ.assert_called_once()
        assert len(site.species) == 1

    def test_silver_handles_worms_failures_gracefully(self) -> None:
        """If WoRMS enrichment fails, species still populated from OBIS data."""
        char = self._build_mocked_characterizer()

        with patch.object(char._mr, "search_by_name", return_value=self._mock_marine_regions_search()), \
             patch.object(char._mr, "get_geometry", return_value=self._mock_marine_regions_geometry()), \
             patch.object(char._obis, "get_checklist", return_value=self._mock_obis_checklist()["results"]), \
             patch.object(char._worms, "get_record", side_effect=ConnectionError("WoRMS down")), \
             patch.object(char._worms, "get_classification", side_effect=ConnectionError("WoRMS down")), \
             patch.object(char._worms, "get_attributes", side_effect=ConnectionError("WoRMS down")):

            site = char.characterize(
                name="Tubbataha Reefs Natural Park",
                tier=CharacterizationTier.silver,
            )

        # Species still populated from OBIS data
        assert len(site.species) == 3
        assert site.species[0].scientific_name == "Acropora palmata"
        # But conservation_status not enriched
        assert site.species[0].conservation_status == ""


# ---------------------------------------------------------------------------
# 8. HabitatInfo confidence field
# ---------------------------------------------------------------------------

class TestHabitatInfoModel:
    """Test the confidence field on HabitatInfo."""

    def test_confidence_defaults_to_zero(self) -> None:
        h = HabitatInfo(habitat_id="coral_reef")
        assert h.confidence == 0.0

    def test_confidence_can_be_set(self) -> None:
        h = HabitatInfo(habitat_id="coral_reef", confidence=0.85)
        assert h.confidence == 0.85
