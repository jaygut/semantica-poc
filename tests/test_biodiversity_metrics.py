"""Tests for maris/sites/biodiversity_metrics.py.

Covers compute_biodiversity_metrics() with full, partial, and empty data,
build_wkt_from_bounds(), and MT-A / MT-B summary generation.
"""

from __future__ import annotations

from maris.sites.biodiversity_metrics import (
    build_wkt_from_bounds,
    compute_biodiversity_metrics,
)


# ---------------------------------------------------------------------------
# build_wkt_from_bounds
# ---------------------------------------------------------------------------

class TestBuildWktFromBounds:
    def test_basic_bounding_box(self) -> None:
        wkt = build_wkt_from_bounds(-25.0, 113.0, -24.0, 114.0)
        assert wkt == (
            "POLYGON((113.0 -25.0, 114.0 -25.0, "
            "114.0 -24.0, 113.0 -24.0, 113.0 -25.0))"
        )

    def test_negative_coordinates(self) -> None:
        wkt = build_wkt_from_bounds(-10.0, -110.0, -9.0, -109.0)
        assert "POLYGON((" in wkt
        # First and last coordinate pairs must match (closed ring)
        coords = wkt.replace("POLYGON((", "").replace("))", "")
        pairs = coords.split(", ")
        assert pairs[0] == pairs[-1]


# ---------------------------------------------------------------------------
# compute_biodiversity_metrics - full data
# ---------------------------------------------------------------------------

class TestComputeBiodiversityMetricsFull:
    def setup_method(self) -> None:
        self.statistics = {
            "species": 1234,
            "records": 56789,
            "datasets": 42,
            "yearmin": 1985,
            "yearmax": 2023,
        }
        self.redlist_species = [
            {"scientificName": "Carcharodon carcharias", "category": "VU"},
            {"scientificName": "Rhincodon typus", "category": "EN"},
            {"scientificName": "Pristis pristis", "category": "CR"},
            {"scientificName": "Dugong dugon", "category": "VU"},
            {"scientificName": "Chelonia mydas", "category": "EN"},
            {"scientificName": "Manta birostris", "category": "VU"},
            {"scientificName": "Sousa sahulensis", "category": "VU"},
            {"scientificName": "Squalus sp.", "category": "NT"},
        ]
        self.composition = {
            "Actinopterygii": 800,
            "Chondrichthyes": 45,
            "Mammalia": 12,
            "Reptilia": 5,
        }

    def test_species_richness(self) -> None:
        result = compute_biodiversity_metrics(
            self.statistics, self.redlist_species, self.composition
        )
        assert result["species_richness"] == 1234

    def test_total_records(self) -> None:
        result = compute_biodiversity_metrics(
            self.statistics, self.redlist_species, self.composition
        )
        assert result["total_records"] == 56789

    def test_dataset_count(self) -> None:
        result = compute_biodiversity_metrics(
            self.statistics, self.redlist_species, self.composition
        )
        assert result["dataset_count"] == 42

    def test_year_range(self) -> None:
        result = compute_biodiversity_metrics(
            self.statistics, self.redlist_species, self.composition
        )
        assert result["year_range"] == (1985, 2023)

    def test_iucn_threatened_count(self) -> None:
        result = compute_biodiversity_metrics(
            self.statistics, self.redlist_species, self.composition
        )
        # CR=1, EN=2, VU=4 => 7
        assert result["iucn_threatened_count"] == 7

    def test_iucn_by_category(self) -> None:
        result = compute_biodiversity_metrics(
            self.statistics, self.redlist_species, self.composition
        )
        assert result["iucn_by_category"]["CR"] == 1
        assert result["iucn_by_category"]["EN"] == 2
        assert result["iucn_by_category"]["VU"] == 4
        assert result["iucn_by_category"]["NT"] == 1

    def test_taxonomic_composition_passthrough(self) -> None:
        result = compute_biodiversity_metrics(
            self.statistics, self.redlist_species, self.composition
        )
        assert result["taxonomic_composition"] == self.composition

    def test_mt_a_summary(self) -> None:
        result = compute_biodiversity_metrics(
            self.statistics, self.redlist_species, self.composition
        )
        mt_a = result["mt_a_summary"]
        assert "1,234 species documented" in mt_a
        assert "7 IUCN Red List species" in mt_a
        assert "1 CR" in mt_a
        assert "2 EN" in mt_a
        assert "4 VU" in mt_a

    def test_mt_b_summary(self) -> None:
        result = compute_biodiversity_metrics(
            self.statistics, self.redlist_species, self.composition
        )
        mt_b = result["mt_b_summary"]
        assert "1985-2023" in mt_b
        assert "42 datasets" in mt_b
        assert "56,789 occurrence records" in mt_b


# ---------------------------------------------------------------------------
# compute_biodiversity_metrics - empty data
# ---------------------------------------------------------------------------

class TestComputeBiodiversityMetricsEmpty:
    def test_all_empty(self) -> None:
        result = compute_biodiversity_metrics({}, [], {})
        assert result["species_richness"] == 0
        assert result["total_records"] == 0
        assert result["dataset_count"] == 0
        assert result["year_range"] is None
        assert result["iucn_threatened_count"] == 0
        assert result["iucn_by_category"] == {}
        assert result["mt_a_summary"] == ""
        assert result["mt_b_summary"] == ""

    def test_statistics_only(self) -> None:
        result = compute_biodiversity_metrics(
            {"species": 100, "records": 500}, [], {}
        )
        assert result["species_richness"] == 100
        assert result["iucn_threatened_count"] == 0
        assert "100 species documented" in result["mt_a_summary"]
        # No year range or datasets, so mt_b only has records
        assert "500 occurrence records" in result["mt_b_summary"]


# ---------------------------------------------------------------------------
# compute_biodiversity_metrics - partial data
# ---------------------------------------------------------------------------

class TestComputeBiodiversityMetricsPartial:
    def test_redlist_only_cr(self) -> None:
        result = compute_biodiversity_metrics(
            {},
            [{"category": "CR"}, {"category": "CR"}],
            {},
        )
        assert result["iucn_threatened_count"] == 2
        assert result["iucn_by_category"] == {"CR": 2}
        assert "2 CR" in result["mt_a_summary"]

    def test_no_threatened_only_nt_lc(self) -> None:
        result = compute_biodiversity_metrics(
            {},
            [{"category": "NT"}, {"category": "LC"}],
            {},
        )
        assert result["iucn_threatened_count"] == 0
        # NT and LC should still appear in iucn_by_category
        assert result["iucn_by_category"]["NT"] == 1
        assert result["iucn_by_category"]["LC"] == 1

    def test_year_range_missing_yearmax(self) -> None:
        result = compute_biodiversity_metrics(
            {"yearmin": 1990}, [], {}
        )
        assert result["year_range"] is None

    def test_redlist_species_with_empty_category(self) -> None:
        result = compute_biodiversity_metrics(
            {},
            [{"scientificName": "Unknown", "category": ""}],
            {},
        )
        # Empty category should be ignored
        assert result["iucn_threatened_count"] == 0
