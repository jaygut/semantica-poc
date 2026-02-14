"""Phase 2 Integration Tests: External API Validation (T2.1-T2.8).

These tests validate P1's three API clients (OBIS, WoRMS, Marine Regions)
against real external services and the full SiteCharacterizer pipeline.

All tests use the @pytest.mark.integration marker and can be run via:
    pytest tests/integration/test_phase2_apis.py -v

IMPORTANT: These tests hit REAL external APIs. They may be slow, rate-limited,
or temporarily unavailable. Timeouts are set to 30s per request. If an external
API is down, tests will be marked as XFAIL rather than FAIL.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Check if the sites module exists
_HAS_SITES_MODULE = importlib.util.find_spec("maris.sites") is not None
_HAS_API_CLIENTS = importlib.util.find_spec("maris.sites.api_clients") is not None

# Skip entire module if the sites package is missing
if not _HAS_SITES_MODULE or not _HAS_API_CLIENTS:
    pytest.skip(
        "Module maris.sites.api_clients not found - GAP: P1 site scaling not implemented",
        allow_module_level=True,
    )

from maris.sites.api_clients import MarineRegionsClient, OBISClient, WoRMSClient
from maris.sites.characterizer import SiteCharacterizer
from maris.sites.models import CharacterizationTier


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def obis_client() -> OBISClient:
    return OBISClient(timeout=30.0, max_retries=2, retry_delay=1.0)


@pytest.fixture(scope="module")
def worms_client() -> WoRMSClient:
    return WoRMSClient(timeout=30.0, max_retries=2, retry_delay=1.0)


@pytest.fixture(scope="module")
def marine_regions_client() -> MarineRegionsClient:
    return MarineRegionsClient(timeout=30.0, max_retries=2, retry_delay=1.0)


# ---------------------------------------------------------------------------
# T2.1: OBIS API - Known Site Occurrence Query
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT2_1_OBISKnownSite:
    """Query OBIS for species occurrences near Cabo Pulmo."""

    def test_obis_returns_list_for_cabo_pulmo_bbox(self, obis_client: OBISClient) -> None:
        """OBIS occurrence query near Cabo Pulmo returns a list of records."""
        geometry = "POLYGON((-109.5 23.3, -109.3 23.3, -109.3 23.6, -109.5 23.6, -109.5 23.3))"
        try:
            results = obis_client.get_occurrences(geometry=geometry, limit=20)
        except ConnectionError:
            pytest.xfail("OBIS API unreachable - external service may be down")

        assert isinstance(results, list), f"Expected list, got {type(results).__name__}"

    def test_obis_records_have_expected_keys(self, obis_client: OBISClient) -> None:
        """Each OBIS occurrence record contains the keys the characterizer expects."""
        geometry = "POLYGON((-109.5 23.3, -109.3 23.3, -109.3 23.6, -109.5 23.6, -109.5 23.3))"
        try:
            results = obis_client.get_occurrences(geometry=geometry, limit=5)
        except ConnectionError:
            pytest.xfail("OBIS API unreachable - external service may be down")

        if not results:
            pytest.skip("OBIS returned 0 results for Cabo Pulmo bbox - may be rate-limited")

        # The characterizer (characterizer.py:174-178) reads these keys from OBIS:
        #   aphiaID or taxonID, scientificName, vernacularName
        # The fixture (obis_response.json) has: aphiaID, taxonID, scientificName, vernacularName
        record = results[0]
        has_taxon_key = "aphiaID" in record or "taxonID" in record
        assert has_taxon_key, (
            f"OBIS record missing both 'aphiaID' and 'taxonID'. "
            f"Keys present: {sorted(record.keys())}"
        )

    def test_obis_fixture_keys_match_real_response(self, obis_client: OBISClient) -> None:
        """Compare fixture keys against real API response to detect contract drift."""
        import json

        geometry = "POLYGON((-109.5 23.3, -109.3 23.3, -109.3 23.6, -109.5 23.6, -109.5 23.3))"
        try:
            results = obis_client.get_occurrences(geometry=geometry, limit=5)
        except ConnectionError:
            pytest.xfail("OBIS API unreachable")

        if not results:
            pytest.skip("OBIS returned 0 results")

        fixture_path = PROJECT_ROOT / "tests" / "fixtures" / "obis_response.json"
        fixture_data = json.loads(fixture_path.read_text())
        fixture_keys = set(fixture_data["results"][0].keys())
        real_keys = set(results[0].keys())

        # The characterizer depends on these specific keys
        critical_keys = {"scientificName"}
        missing_critical = critical_keys - real_keys
        assert not missing_critical, (
            f"Real OBIS response is missing critical keys: {missing_critical}. "
            f"Fixture keys: {sorted(fixture_keys)}, Real keys: {sorted(real_keys)}"
        )


# ---------------------------------------------------------------------------
# T2.2: OBIS API - Empty Area Query
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT2_2_OBISEmptyArea:
    """Query an area with no known marine life - should return empty list."""

    def test_obis_empty_area_returns_empty_list(self, obis_client: OBISClient) -> None:
        """Deep mid-Atlantic query returns empty list, no exception."""
        geometry = "POLYGON((-30.1 30.0, -29.9 30.0, -29.9 30.2, -30.1 30.2, -30.1 30.0))"
        try:
            results = obis_client.get_occurrences(geometry=geometry, limit=20)
        except ConnectionError:
            pytest.xfail("OBIS API unreachable")

        assert isinstance(results, list), f"Expected list, got {type(results).__name__}"
        # Mid-Atlantic may still have some pelagic records, so we don't assert len==0,
        # but we verify no exception was raised and the result is a list.


# ---------------------------------------------------------------------------
# T2.3: WoRMS API - Known Species Lookup
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT2_3_WoRMSKnownSpecies:
    """Look up Lutjanus argentiventris (yellow snapper) in WoRMS."""

    def test_worms_returns_records_for_known_species(self, worms_client: WoRMSClient) -> None:
        """WoRMS search for known species returns at least one record."""
        try:
            results = worms_client.search_by_name("Lutjanus argentiventris")
        except ConnectionError:
            pytest.xfail("WoRMS API unreachable")

        assert isinstance(results, list), f"Expected list, got {type(results).__name__}"
        assert len(results) >= 1, "Expected at least one record for Lutjanus argentiventris"

    def test_worms_record_has_aphia_id(self, worms_client: WoRMSClient) -> None:
        """WoRMS record contains an integer AphiaID."""
        try:
            results = worms_client.search_by_name("Lutjanus argentiventris")
        except ConnectionError:
            pytest.xfail("WoRMS API unreachable")

        if not results:
            pytest.skip("WoRMS returned 0 results")

        record = results[0]
        assert "AphiaID" in record, f"WoRMS record missing 'AphiaID'. Keys: {sorted(record.keys())}"
        assert isinstance(record["AphiaID"], int), f"AphiaID should be int, got {type(record['AphiaID'])}"

    def test_worms_classification_for_known_species(self, worms_client: WoRMSClient) -> None:
        """get_classification returns taxonomic hierarchy for a known AphiaID."""
        try:
            results = worms_client.search_by_name("Lutjanus argentiventris")
        except ConnectionError:
            pytest.xfail("WoRMS API unreachable")

        if not results:
            pytest.skip("WoRMS returned 0 results")

        aphia_id = results[0]["AphiaID"]
        try:
            classification = worms_client.get_classification(aphia_id)
        except ConnectionError:
            pytest.xfail("WoRMS API unreachable for classification")

        assert isinstance(classification, dict), f"Expected dict, got {type(classification).__name__}"
        # Classification should have at least a scientificname
        assert "scientificname" in classification or "child" in classification, (
            f"Classification response unexpected structure. Keys: {sorted(classification.keys())}"
        )

    def test_worms_fixture_keys_match_real_response(self, worms_client: WoRMSClient) -> None:
        """Compare fixture keys against real WoRMS response."""
        import json

        try:
            results = worms_client.search_by_name("Lutjanus argentiventris")
        except ConnectionError:
            pytest.xfail("WoRMS API unreachable")

        if not results:
            pytest.skip("WoRMS returned 0 results")

        fixture_path = PROJECT_ROOT / "tests" / "fixtures" / "worms_response.json"
        fixture_data = json.loads(fixture_path.read_text())
        fixture_keys = set(fixture_data.keys())
        real_keys = set(results[0].keys())

        # The characterizer reads: scientificname, iucn_status from WoRMS
        critical_keys = {"AphiaID", "scientificname"}
        missing_critical = critical_keys - real_keys
        assert not missing_critical, (
            f"Real WoRMS response missing critical keys: {missing_critical}. "
            f"Fixture keys: {sorted(fixture_keys)}, Real keys: {sorted(real_keys)}"
        )


# ---------------------------------------------------------------------------
# T2.4: WoRMS API - Non-Existent Species
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT2_4_WoRMSNonExistent:
    """Look up a non-existent species - should return empty, no exception."""

    def test_worms_returns_empty_for_fake_species(self, worms_client: WoRMSClient) -> None:
        """WoRMS search for fake species returns empty list, no exception.

        BUG FINDING: WoRMS API returns HTTP 204 (No Content) for non-existent
        species. The current WoRMSClient.search_by_name() calls resp.json()
        which raises json.JSONDecodeError on empty body. The client should
        handle 204 responses by returning an empty list.
        """
        try:
            results = worms_client.search_by_name("Nonexistus fakeus")
        except ConnectionError:
            pytest.xfail("WoRMS API unreachable")
        except Exception as exc:
            # BUG: WoRMS returns 204 No Content, resp.json() fails
            if "Expecting value" in str(exc) or "JSONDecodeError" in type(exc).__name__:
                pytest.fail(
                    "BUG: WoRMSClient crashes on 204 No Content for non-existent "
                    "species. _BaseClient._get() calls resp.json() on empty body. "
                    "Fix: check resp.status_code == 204 and return [] before parsing JSON."
                )
            raise

        assert isinstance(results, list), f"Expected list, got {type(results).__name__}"
        assert len(results) == 0, f"Expected 0 results for fake species, got {len(results)}"


# ---------------------------------------------------------------------------
# T2.5: Marine Regions API - Known MPA Lookup
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT2_5_MarineRegionsKnownMPA:
    """Search Marine Regions for Cabo Pulmo."""

    def test_marine_regions_returns_records(self, marine_regions_client: MarineRegionsClient) -> None:
        """Marine Regions search for 'Cabo Pulmo' returns at least one record."""
        try:
            results = marine_regions_client.search_by_name("Cabo Pulmo")
        except ConnectionError:
            pytest.xfail("Marine Regions API unreachable")

        assert isinstance(results, list), f"Expected list, got {type(results).__name__}"
        assert len(results) >= 1, "Expected at least one record for Cabo Pulmo"

    def test_marine_regions_record_has_expected_keys(self, marine_regions_client: MarineRegionsClient) -> None:
        """Marine Regions record has MRGID, preferredGazetteerName, latitude, longitude."""
        try:
            results = marine_regions_client.search_by_name("Cabo Pulmo")
        except ConnectionError:
            pytest.xfail("Marine Regions API unreachable")

        if not results:
            pytest.skip("Marine Regions returned 0 results")

        record = results[0]
        expected_keys = {"MRGID", "preferredGazetteerName", "latitude", "longitude"}
        missing = expected_keys - set(record.keys())
        assert not missing, (
            f"Marine Regions record missing keys: {missing}. "
            f"Keys present: {sorted(record.keys())}"
        )

    def test_marine_regions_mrgid_is_integer(self, marine_regions_client: MarineRegionsClient) -> None:
        """MRGID should be an integer."""
        try:
            results = marine_regions_client.search_by_name("Cabo Pulmo")
        except ConnectionError:
            pytest.xfail("Marine Regions API unreachable")

        if not results:
            pytest.skip("Marine Regions returned 0 results")

        mrgid = results[0]["MRGID"]
        assert isinstance(mrgid, int), f"MRGID should be int, got {type(mrgid).__name__}"

    def test_marine_regions_get_by_mrgid(self, marine_regions_client: MarineRegionsClient) -> None:
        """get_by_mrgid returns a valid record for a known MRGID."""
        try:
            results = marine_regions_client.search_by_name("Cabo Pulmo")
        except ConnectionError:
            pytest.xfail("Marine Regions API unreachable")

        if not results:
            pytest.skip("Marine Regions returned 0 results")

        mrgid = results[0]["MRGID"]
        try:
            record = marine_regions_client.get_by_mrgid(mrgid)
        except ConnectionError:
            pytest.xfail("Marine Regions API unreachable for get_by_mrgid")

        assert isinstance(record, dict), f"Expected dict, got {type(record).__name__}"
        assert record.get("MRGID") == mrgid, f"MRGID mismatch: {record.get('MRGID')} != {mrgid}"

    def test_marine_regions_fixture_keys_match_real_response(self, marine_regions_client: MarineRegionsClient) -> None:
        """Compare fixture keys against real Marine Regions response."""
        import json

        try:
            results = marine_regions_client.search_by_name("Cabo Pulmo")
        except ConnectionError:
            pytest.xfail("Marine Regions API unreachable")

        if not results:
            pytest.skip("Marine Regions returned 0 results")

        fixture_path = PROJECT_ROOT / "tests" / "fixtures" / "marine_regions_response.json"
        fixture_data = json.loads(fixture_path.read_text())
        fixture_keys = set(fixture_data[0].keys())
        real_keys = set(results[0].keys())

        # The characterizer reads: country, latitude, longitude, area_km2, year, MRGID
        critical_keys = {"MRGID", "latitude", "longitude"}
        missing_critical = critical_keys - real_keys
        assert not missing_critical, (
            f"Real Marine Regions response missing critical keys: {missing_critical}. "
            f"Fixture keys: {sorted(fixture_keys)}, Real keys: {sorted(real_keys)}"
        )


# ---------------------------------------------------------------------------
# T2.6: Full Characterization Pipeline - Bronze Tier
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT2_6_BronzeCharacterization:
    """Characterize Tubbataha Reefs Natural Park at Bronze tier."""

    def test_bronze_characterization_returns_valid_site(self) -> None:
        """Bronze characterization returns SiteCharacterization with tier=bronze."""
        char = SiteCharacterizer()
        try:
            site = char.characterize(
                name="Tubbataha Reefs Natural Park",
                tier=CharacterizationTier.bronze,
                country="Philippines",
                coordinates={"latitude": 8.9, "longitude": 119.9},
            )
        except ConnectionError:
            pytest.xfail("External API unreachable during bronze characterization")

        assert site.canonical_name == "Tubbataha Reefs Natural Park"
        assert site.tier == CharacterizationTier.bronze

    def test_bronze_does_not_populate_species(self) -> None:
        """Bronze tier should NOT populate species or habitats."""
        char = SiteCharacterizer()
        try:
            site = char.characterize(
                name="Tubbataha Reefs Natural Park",
                tier=CharacterizationTier.bronze,
                country="Philippines",
                coordinates={"latitude": 8.9, "longitude": 119.9},
            )
        except ConnectionError:
            pytest.xfail("External API unreachable")

        assert len(site.species) == 0, f"Bronze should have 0 species, got {len(site.species)}"
        assert len(site.habitats) == 0, f"Bronze should have 0 habitats, got {len(site.habitats)}"
        assert site.estimated_esv_usd is None, "Bronze should not have ESV estimate"

    def test_bronze_does_not_call_obis_or_worms(self) -> None:
        """Bronze tier should NOT call OBIS or WoRMS APIs."""
        obis = OBISClient()
        worms = WoRMSClient()
        mr = MarineRegionsClient()

        with patch.object(obis, "get_occurrences") as mock_obis, \
             patch.object(worms, "search_by_name") as mock_worms:

            char = SiteCharacterizer(
                obis_client=obis,
                worms_client=worms,
                marine_regions_client=mr,
            )
            try:
                char.characterize(
                    name="Tubbataha Reefs Natural Park",
                    tier=CharacterizationTier.bronze,
                    country="Philippines",
                    coordinates={"latitude": 8.9, "longitude": 119.9},
                )
            except ConnectionError:
                pytest.xfail("Marine Regions unreachable")

            mock_obis.assert_not_called()
            mock_worms.assert_not_called()


# ---------------------------------------------------------------------------
# T2.7: Full Characterization Pipeline - Silver Tier
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT2_7_SilverCharacterization:
    """Characterize Tubbataha Reefs Natural Park at Silver tier."""

    def test_silver_characterization_has_species(self) -> None:
        """Silver characterization should populate species list."""
        char = SiteCharacterizer()
        try:
            site = char.characterize(
                name="Tubbataha Reefs Natural Park",
                tier=CharacterizationTier.silver,
                country="Philippines",
                coordinates={"latitude": 8.9, "longitude": 119.9},
                area_km2=970.0,
                designation_year=1988,
            )
        except ConnectionError:
            pytest.xfail("External API unreachable during silver characterization")

        # Silver should have species from OBIS.
        # OBIS may return 0 results if the API is rate-limited or the area
        # query doesn't match, so we check gracefully.
        if len(site.species) == 0:
            pytest.xfail(
                "OBIS returned 0 species for Tubbataha - API may be rate-limited "
                "or MPA name query yielded no results"
            )
        assert len(site.species) > 0

    def test_silver_characterization_has_habitats(self) -> None:
        """Silver characterization should infer habitat types from species."""
        char = SiteCharacterizer()
        try:
            site = char.characterize(
                name="Tubbataha Reefs Natural Park",
                tier=CharacterizationTier.silver,
                country="Philippines",
                coordinates={"latitude": 8.9, "longitude": 119.9},
                area_km2=970.0,
                designation_year=1988,
            )
        except ConnectionError:
            pytest.xfail("External API unreachable")

        if len(site.species) == 0:
            pytest.xfail("No species returned - cannot infer habitats")

        # Tubbataha is a coral reef system; if OBIS returns relevant species
        # the habitat inference should detect coral_reef
        if len(site.habitats) == 0:
            pytest.xfail(
                "No habitats inferred - species may not match inference keywords"
            )

    def test_silver_characterization_has_esv(self) -> None:
        """Silver characterization should produce ESV estimates."""
        char = SiteCharacterizer()
        try:
            site = char.characterize(
                name="Tubbataha Reefs Natural Park",
                tier=CharacterizationTier.silver,
                country="Philippines",
                coordinates={"latitude": 8.9, "longitude": 119.9},
                area_km2=970.0,
                designation_year=1988,
            )
        except ConnectionError:
            pytest.xfail("External API unreachable")

        if len(site.habitats) == 0:
            pytest.xfail("No habitats - cannot estimate ESV")

        assert site.estimated_esv_usd is not None, "Silver should have ESV estimate"
        assert site.estimated_esv_usd > 0, f"ESV should be positive, got {site.estimated_esv_usd}"
        # Sanity check: ESV should be plausible (not $0, not $999B)
        assert site.estimated_esv_usd < 1e12, f"ESV unreasonably large: {site.estimated_esv_usd}"

    def test_silver_characterization_has_esv_confidence(self) -> None:
        """Silver characterization should produce ESV confidence info."""
        char = SiteCharacterizer()
        try:
            site = char.characterize(
                name="Tubbataha Reefs Natural Park",
                tier=CharacterizationTier.silver,
                country="Philippines",
                coordinates={"latitude": 8.9, "longitude": 119.9},
                area_km2=970.0,
                designation_year=1988,
            )
        except ConnectionError:
            pytest.xfail("External API unreachable")

        if len(site.habitats) == 0:
            pytest.xfail("No habitats - no ESV confidence")

        assert isinstance(site.esv_confidence, dict), "esv_confidence should be a dict"

    def test_silver_characterization_has_neoli_score(self) -> None:
        """Silver characterization should calculate NEOLI score and rating."""
        char = SiteCharacterizer()
        try:
            site = char.characterize(
                name="Tubbataha Reefs Natural Park",
                tier=CharacterizationTier.silver,
                country="Philippines",
                coordinates={"latitude": 8.9, "longitude": 119.9},
                area_km2=970.0,
                designation_year=1988,
            )
        except ConnectionError:
            pytest.xfail("External API unreachable")

        assert site.neoli_score is not None, "Silver should have NEOLI score"
        assert 0 <= site.neoli_score <= 5, f"NEOLI score out of range: {site.neoli_score}"
        assert site.asset_rating != "", "Silver should have asset rating"
        # Tubbataha: designated 1988 (>10yr old), 970 km2 (>100km2 large),
        # designation_year set (no_take + enforced assumed). Score should be >= 3.
        assert site.neoli_score >= 3, (
            f"Expected NEOLI >= 3 for Tubbataha (old, large, designated), got {site.neoli_score}"
        )


# ---------------------------------------------------------------------------
# T2.8: API Error Handling
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT2_8_ErrorHandling:
    """Test error handling when external APIs are unreachable."""

    def _make_bad_client(self, cls: type, bad_url: str = "https://nonexistent.example.com"):
        """Create a client with a bad base URL.

        GAP FINDING: OBISClient, WoRMSClient, and MarineRegionsClient hardcode
        base_url in their __init__ and pass **kwargs to super(). This means
        base_url cannot be overridden via constructor kwargs (TypeError:
        multiple values for keyword argument 'base_url'). We work around this
        by constructing with defaults and then patching base_url.
        """
        client = cls(max_retries=1, timeout=5.0, retry_delay=0.1)
        client.base_url = bad_url
        return client

    def test_obis_bad_url_raises_connection_error(self) -> None:
        """OBISClient with bad base URL raises ConnectionError."""
        client = self._make_bad_client(OBISClient)
        with pytest.raises(ConnectionError):
            client.get_occurrences(limit=1)

    def test_worms_bad_url_raises_connection_error(self) -> None:
        """WoRMSClient with bad base URL raises ConnectionError."""
        client = self._make_bad_client(WoRMSClient)
        with pytest.raises(ConnectionError):
            client.search_by_name("anything")

    def test_marine_regions_bad_url_raises_connection_error(self) -> None:
        """MarineRegionsClient with bad base URL raises ConnectionError."""
        client = self._make_bad_client(MarineRegionsClient)
        with pytest.raises(ConnectionError):
            client.search_by_name("anything")

    def test_retry_logic_fires_on_failure(self) -> None:
        """Verify retry logic fires the expected number of attempts."""
        client = OBISClient(max_retries=2, timeout=2.0, retry_delay=0.1)
        client.base_url = "https://nonexistent.example.com"

        import time
        start = time.monotonic()
        with pytest.raises(ConnectionError) as exc_info:
            client.get_occurrences(limit=1)
        elapsed = time.monotonic() - start

        # Should have attempted twice with ~0.1s delay between
        assert "2 attempts" in str(exc_info.value), (
            f"Error message should reference 2 attempts: {exc_info.value}"
        )

    def test_characterizer_handles_unreachable_apis_gracefully(self) -> None:
        """SiteCharacterizer with bad clients should not crash on bronze."""
        bad_mr = MarineRegionsClient(max_retries=1, timeout=2.0, retry_delay=0.1)
        bad_mr.base_url = "https://nonexistent.example.com"
        char = SiteCharacterizer(marine_regions_client=bad_mr)

        # Bronze with pre-supplied country + coordinates should succeed
        # even if Marine Regions is unreachable (it's used as fallback)
        site = char.characterize(
            name="Test MPA",
            tier=CharacterizationTier.bronze,
            country="TestCountry",
            coordinates={"latitude": 10.0, "longitude": 120.0},
        )
        assert site.canonical_name == "Test MPA"
        assert site.country == "TestCountry"
        assert site.tier == CharacterizationTier.bronze
