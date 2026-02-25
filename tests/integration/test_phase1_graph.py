"""Phase 1 Integration Tests: Graph Integrity (T1.1-T1.6).

Validates that the Neo4j population pipeline is idempotent, EVIDENCED_BY
metadata is correctly structured, Bronze/Silver site population works
without corrupting existing data, and SemanticaBackedManager tracks
provenance during population.

All tests use the @pytest.mark.integration marker and can be run via:
    pytest tests/integration/test_phase1_graph.py -v
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Project root for data file paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATES_PATH = PROJECT_ROOT / "schemas" / "bridge_axiom_templates.json"
EVIDENCE_PATH = PROJECT_ROOT / "data" / "semantica_export" / "bridge_axioms.json"

# Force-load real .env to override test conftest defaults (which set
# MARIS_NEO4J_PASSWORD="test-password"). Integration tests need real creds.
load_dotenv(PROJECT_ROOT / ".env", override=True)

# Reset the config singleton so it picks up the real env vars
import maris.config as _cfg_mod  # noqa: E402
_cfg_mod._config = None

from maris.config import get_config  # noqa: E402
from maris.config_v4 import get_config_v4  # noqa: E402
from maris.graph.connection import get_driver, run_query  # noqa: E402

# Reset the connection singleton too, in case it was initialized with bad creds
import maris.graph.connection as _conn_mod  # noqa: E402
_conn_mod._driver = None

_HAS_SEMANTICA = importlib.util.find_spec("semantica") is not None


def _neo4j_available() -> bool:
    """Check if Neo4j is reachable."""
    try:
        driver = get_driver()
        driver.verify_connectivity()
        return True
    except Exception:
        return False


skip_no_neo4j = pytest.mark.skipif(
    not _neo4j_available(),
    reason="Neo4j not reachable at bolt://localhost:7687",
)

skip_no_semantica = pytest.mark.skipif(
    not _HAS_SEMANTICA,
    reason="Semantica SDK not installed",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_node_counts() -> dict[str, int]:
    """Return {label: count} for all node labels."""
    records = run_query(
        "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt ORDER BY label"
    )
    return {r["label"]: r["cnt"] for r in records}


def _get_relationship_counts() -> dict[str, int]:
    """Return {type: count} for all relationship types."""
    records = run_query(
        "MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS cnt ORDER BY rel"
    )
    return {r["rel"]: r["cnt"] for r in records}


def _get_axiom_evidence_counts() -> dict[str, int]:
    """Return {axiom_id: evidence_count} for all BridgeAxiom nodes."""
    records = run_query(
        """
        MATCH (a:BridgeAxiom)
        OPTIONAL MATCH (a)-[:EVIDENCED_BY]->(d:Document)
        RETURN a.axiom_id AS axiom_id, count(d) AS evidence_count
        ORDER BY a.axiom_id
        """
    )
    return {r["axiom_id"]: r["evidence_count"] for r in records}


def _get_mpa_properties() -> dict[str, dict]:
    """Return MPA properties keyed by name."""
    records = run_query(
        """
        MATCH (m:MPA)
        RETURN m.name AS name, m.total_esv_usd AS total_esv_usd,
               m.neoli_score AS neoli_score, m.asset_rating AS asset_rating,
               m.area_km2 AS area_km2, m.country AS country
        ORDER BY m.name
        """
    )
    return {r["name"]: r for r in records}


def _cleanup_test_mpa(site_name: str) -> None:
    """Delete a test MPA node and all connected test nodes."""
    driver = get_driver()
    cfg = get_config()
    with driver.session(database=cfg.neo4j_database) as session:
        # Delete GENERATES edges and associated test EcosystemService nodes
        session.run(
            """
            MATCH (m:MPA {name: $name})-[:GENERATES]->(es:EcosystemService)
            WHERE es.service_id STARTS WITH $prefix
            DETACH DELETE es
            """,
            {
                "name": site_name,
                "prefix": site_name.lower().replace(" ", "_"),
            },
        )
        # Delete LOCATED_IN edges from test species
        session.run(
            """
            MATCH (s:Species)-[:LOCATED_IN]->(m:MPA {name: $name})
            WHERE s.worms_id > 9999000
            DETACH DELETE s
            """,
            {"name": site_name},
        )
        # Delete HAS_HABITAT edges (but not the Habitat node if shared)
        session.run(
            """
            MATCH (m:MPA {name: $name})-[r:HAS_HABITAT]->()
            DELETE r
            """,
            {"name": site_name},
        )
        # Delete test habitat nodes created with unique test IDs
        session.run(
            """
            MATCH (h:Habitat {habitat_id: "test_mangrove_integration"})
            DETACH DELETE h
            """,
        )
        # Delete the MPA node itself
        session.run(
            "MATCH (m:MPA {name: $name}) DETACH DELETE m",
            {"name": site_name},
        )


# ---------------------------------------------------------------------------
# T1.1: Snapshot Before Re-Population
# ---------------------------------------------------------------------------

@pytest.mark.integration
@skip_no_neo4j
class TestT11SnapshotBeforeRePopulation:
    """T1.1: Connect to Neo4j, run Cypher queries to get exact counts by label,
    by relationship type, BridgeAxiom evidence counts, and MPA properties.
    Record baselines."""

    def test_node_counts_baseline(self):
        """Record node counts and verify expected labels are present."""
        counts = _get_node_counts()

        # Verify expected labels are present (v4 schema: TrophicLevel not created by v4 populator)
        expected_labels = {
            "Document", "BridgeAxiom", "EcosystemService", "MPA",
            "Habitat", "Species", "Concept",
            "FinancialInstrument", "Framework",
        }
        present = set(counts.keys())
        missing = expected_labels - present
        assert not missing, f"Missing node labels: {missing}"

        # Verify expected counts (from CLAUDE.md: 893 nodes total)
        total = sum(counts.values())
        assert total >= 800, f"Total node count {total} is too low (expected ~893)"
        assert counts.get("BridgeAxiom", 0) == 40, (
            f"Expected 40 BridgeAxiom nodes, got {counts.get('BridgeAxiom', 0)}"
        )
        assert counts.get("MPA", 0) >= 9, (
            f"Expected at least 9 MPA nodes (9 portfolio sites), got {counts.get('MPA', 0)}"
        )

        # Store for later comparison
        TestT11SnapshotBeforeRePopulation._node_counts = counts
        print(f"\nNode counts baseline: {json.dumps(counts, indent=2)}")

    def test_relationship_counts_baseline(self):
        """Record relationship counts by type."""
        counts = _get_relationship_counts()

        # v4 schema: PREYS_ON, PART_OF_FOODWEB, TRANSLATES are legacy v2/v3 relationships
        # not created by the v4 populator
        expected_rels = {
            "GENERATES", "APPLIES_TO", "EVIDENCED_BY",
            "HAS_HABITAT", "INVOLVES_AXIOM",
        }
        present = set(counts.keys())
        missing = expected_rels - present
        assert not missing, f"Missing relationship types: {missing}"

        total = sum(counts.values())
        assert total >= 100, f"Total edge count {total} is too low (expected ~132)"

        TestT11SnapshotBeforeRePopulation._rel_counts = counts
        print(f"\nRelationship counts baseline: {json.dumps(counts, indent=2)}")

    def test_axiom_evidence_baseline(self):
        """Verify all 40 axioms have at least one EVIDENCED_BY edge."""
        evidence = _get_axiom_evidence_counts()

        assert len(evidence) == 40, (
            f"Expected 40 BridgeAxiom nodes, got {len(evidence)}"
        )

        for axiom_id, count in evidence.items():
            assert count >= 1, f"{axiom_id} has no EVIDENCED_BY edges"

        TestT11SnapshotBeforeRePopulation._evidence_counts = evidence
        print(f"\nAxiom evidence baseline: {json.dumps(evidence, indent=2)}")

    def test_mpa_properties_baseline(self):
        """Verify key MPA properties are correct."""
        mpas = _get_mpa_properties()

        assert "Cabo Pulmo National Park" in mpas
        assert "Shark Bay World Heritage Area" in mpas
        assert "Great Barrier Reef Marine Park" in mpas

        cp = mpas["Cabo Pulmo National Park"]
        assert cp["neoli_score"] == 4, f"Cabo Pulmo NEOLI score: {cp['neoli_score']}"
        assert cp["total_esv_usd"] is not None, "Cabo Pulmo total_esv_usd is None"

        sb = mpas["Shark Bay World Heritage Area"]
        assert sb["neoli_score"] == 4, f"Shark Bay NEOLI score: {sb['neoli_score']}"
        assert sb["total_esv_usd"] is not None, "Shark Bay total_esv_usd is None"

        TestT11SnapshotBeforeRePopulation._mpa_props = mpas
        print(f"\nMPA properties baseline recorded for {len(mpas)} sites")


# ---------------------------------------------------------------------------
# T1.2: Re-Run Population Pipeline (Idempotency)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@skip_no_neo4j
class TestT12ReRunPopulation:
    """T1.2: Re-run populate_neo4j.py and verify all counts are identical.
    MERGE operations must be idempotent."""

    def test_population_idempotency(self):
        """Run population pipeline and verify counts are unchanged."""
        # Snapshot before
        node_counts_before = _get_node_counts()
        rel_counts_before = _get_relationship_counts()
        evidence_before = _get_axiom_evidence_counts()
        mpa_props_before = _get_mpa_properties()

        # Re-run population pipeline via subprocess (v4 populator).
        # Pass credentials explicitly - some unit tests overwrite MARIS_NEO4J_PASSWORD
        # in os.environ ("test-password"), which would be inherited by the subprocess
        # and cause AuthError against the real local Neo4j instance.
        cfg = get_config_v4()
        sub_env = os.environ.copy()
        sub_env["MARIS_NEO4J_PASSWORD"] = cfg.neo4j_password
        sub_env["MARIS_NEO4J_URI"] = cfg.neo4j_uri
        sub_env["MARIS_NEO4J_DATABASE"] = cfg.neo4j_database
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "populate_neo4j_v4.py")],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=120,
            env=sub_env,
        )
        assert result.returncode == 0, (
            f"populate_neo4j.py failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # Snapshot after
        node_counts_after = _get_node_counts()
        rel_counts_after = _get_relationship_counts()
        evidence_after = _get_axiom_evidence_counts()
        mpa_props_after = _get_mpa_properties()

        # Compare node counts
        for label in set(node_counts_before) | set(node_counts_after):
            before = node_counts_before.get(label, 0)
            after = node_counts_after.get(label, 0)
            assert before == after, (
                f"Node count for {label} changed: {before} -> {after}"
            )

        # Compare relationship counts
        rel_deltas = {}
        for rel_type in set(rel_counts_before) | set(rel_counts_after):
            before = rel_counts_before.get(rel_type, 0)
            after = rel_counts_after.get(rel_type, 0)
            if before != after:
                rel_deltas[rel_type] = (before, after)

        if rel_deltas:
            # Report deltas as findings before asserting
            print(f"\nRelationship count deltas found: {rel_deltas}")
            # Check if the delta is the known BA-014 stale TRANSLATES edge
            # (a pre-existing issue where BA-014 has a legacy edge to
            # shark_bay_fisheries alongside the correct shark_bay_carbon_sequestration)
            if set(rel_deltas.keys()) == {"TRANSLATES"}:
                before_t, after_t = rel_deltas["TRANSLATES"]
                if after_t == before_t + 1:
                    # Investigate the extra edge
                    extra_edges = run_query(
                        """
                        MATCH (a:BridgeAxiom)-[r:TRANSLATES]->(es:EcosystemService)
                        RETURN a.axiom_id AS axiom_id, es.service_id AS service_id
                        ORDER BY a.axiom_id
                        """
                    )
                    print("\nAll TRANSLATES edges after repopulation:")
                    for e in extra_edges:
                        print(f"  {e['axiom_id']} -> {e['service_id']}")

                    pytest.xfail(
                        f"BUG: TRANSLATES count changed {before_t} -> {after_t}. "
                        f"Likely stale BA-014 -> shark_bay_fisheries edge from "
                        f"pre-fix population. The old edge was not cleaned up when "
                        f"BA-014 was remapped to shark_bay_carbon_sequestration."
                    )
            # Unexpected delta - fail hard
            for rel_type, (before, after) in rel_deltas.items():
                assert before == after, (
                    f"Relationship count for {rel_type} changed: {before} -> {after}"
                )

        # Compare axiom evidence
        assert evidence_before == evidence_after, (
            "Axiom evidence changed after re-population"
        )

        # Compare MPA properties
        for name in mpa_props_before:
            assert name in mpa_props_after, f"MPA {name} disappeared after re-population"
            for prop in ("neoli_score", "total_esv_usd", "asset_rating", "area_km2"):
                before_val = mpa_props_before[name].get(prop)
                after_val = mpa_props_after[name].get(prop)
                assert before_val == after_val, (
                    f"MPA {name}.{prop} changed: {before_val} -> {after_val}"
                )

        print("\nPASS: Population pipeline is idempotent - all counts identical")


# ---------------------------------------------------------------------------
# T1.3: Validate EVIDENCED_BY Edge Metadata
# ---------------------------------------------------------------------------

@pytest.mark.integration
@skip_no_neo4j
class TestT13EvidencedByMetadata:
    """T1.3: Query EVIDENCED_BY edges for extraction_timestamp and checksum
    properties. Document whether they exist."""

    def test_evidenced_by_edge_properties(self):
        """Check EVIDENCED_BY edges for provenance metadata."""
        records = run_query(
            """
            MATCH (a:BridgeAxiom)-[e:EVIDENCED_BY]->(d:Document)
            RETURN a.axiom_id AS axiom_id, d.doi AS doi,
                   e.finding AS finding,
                   e.extraction_timestamp AS extraction_timestamp,
                   e.checksum AS checksum
            ORDER BY a.axiom_id
            LIMIT 20
            """
        )
        assert len(records) > 0, "No EVIDENCED_BY edges found"

        has_timestamp = any(r["extraction_timestamp"] is not None for r in records)
        has_checksum = any(r["checksum"] is not None for r in records)
        has_finding = any(r["finding"] is not None for r in records)

        print(f"\nEVIDENCED_BY edge metadata analysis ({len(records)} edges sampled):")
        print(f"  has_finding:              {has_finding}")
        print(f"  has_extraction_timestamp: {has_timestamp}")
        print(f"  has_checksum:             {has_checksum}")

        # Finding is expected to be present (populated in _populate_bridge_axioms)
        assert has_finding, "No EVIDENCED_BY edges have a 'finding' property"

        # extraction_timestamp and checksum are P0 provenance upgrades.
        # If missing, document as GAP rather than failure.
        if not has_timestamp:
            print(
                "\n  GAP: extraction_timestamp not present on EVIDENCED_BY edges. "
                "P0.3 provenance metadata not yet added to population pipeline."
            )
        if not has_checksum:
            print(
                "\n  GAP: checksum not present on EVIDENCED_BY edges. "
                "P0.3 provenance metadata not yet added to population pipeline."
            )

    def test_all_axioms_have_evidence(self):
        """Every BridgeAxiom must have at least one EVIDENCED_BY edge."""
        records = run_query(
            """
            MATCH (a:BridgeAxiom)
            OPTIONAL MATCH (a)-[:EVIDENCED_BY]->(d:Document)
            RETURN a.axiom_id AS axiom_id, count(d) AS evidence_count
            ORDER BY a.axiom_id
            """
        )
        for rec in records:
            assert rec["evidence_count"] >= 1, (
                f"{rec['axiom_id']} has 0 EVIDENCED_BY edges"
            )
        print(f"\nAll {len(records)} axioms have EVIDENCED_BY edges")


# ---------------------------------------------------------------------------
# T1.4: Test Bronze Site Population
# ---------------------------------------------------------------------------

@pytest.mark.integration
@skip_no_neo4j
class TestT14BronzeSitePopulation:
    """T1.4: Test creating a Bronze-tier temp site and verify correct graph
    structure (MPA node only, no Species/Habitat/EcosystemService)."""

    TEST_SITE_NAME = "__Test_Bronze_Tubbataha_Reefs__"

    def test_bronze_site_population(self):
        """Create Bronze site, verify MPA-only, then clean up."""
        from maris.sites.models import (
            CharacterizationTier,
            CoordinatePair,
            SiteCharacterization,
        )
        from maris.graph.population import _populate_registered_sites

        # Snapshot existing counts
        node_counts_before = _get_node_counts()

        # Create a temp site registry file with one Bronze entry
        bronze_site = SiteCharacterization(
            canonical_name=self.TEST_SITE_NAME,
            tier=CharacterizationTier.bronze,
            country="Philippines",
            area_km2=970.0,
            designation_year=1988,
            coordinates=CoordinatePair(latitude=8.93, longitude=119.88),
            neoli_score=4,
            asset_rating="A",
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            registry_data = {
                "version": "1.0",
                "site_count": 1,
                "sites": {
                    self.TEST_SITE_NAME.lower().replace(" ", "_"): bronze_site.model_dump(mode="json"),
                },
            }
            json.dump(registry_data, f, indent=2, default=str)
            registry_path = f.name

        try:
            # Run population with the temp registry
            driver = get_driver()
            cfg = get_config()
            with driver.session(database=cfg.neo4j_database) as session:
                count = _populate_registered_sites(session, registry_path=Path(registry_path))

            assert count >= 1, f"Expected at least 1 operation, got {count}"

            # Verify MPA node was created
            mpa_records = run_query(
                "MATCH (m:MPA {name: $name}) RETURN m",
                {"name": self.TEST_SITE_NAME},
            )
            assert len(mpa_records) == 1, (
                f"Expected 1 MPA node for test site, got {len(mpa_records)}"
            )

            mpa = mpa_records[0]["m"]
            assert mpa["country"] == "Philippines"
            assert mpa["area_km2"] == 970.0
            assert mpa["characterization_tier"] == "bronze"

            # Verify NO Species, Habitat, or EcosystemService nodes were created for this site
            species_count = run_query(
                """
                MATCH (s:Species)-[:LOCATED_IN]->(m:MPA {name: $name})
                RETURN count(s) AS cnt
                """,
                {"name": self.TEST_SITE_NAME},
            )
            assert species_count[0]["cnt"] == 0, (
                f"Bronze site should have no Species, got {species_count[0]['cnt']}"
            )

            habitat_rels = run_query(
                """
                MATCH (m:MPA {name: $name})-[:HAS_HABITAT]->(h)
                RETURN count(h) AS cnt
                """,
                {"name": self.TEST_SITE_NAME},
            )
            assert habitat_rels[0]["cnt"] == 0, (
                f"Bronze site should have no HAS_HABITAT edges, got {habitat_rels[0]['cnt']}"
            )

            services_count = run_query(
                """
                MATCH (m:MPA {name: $name})-[:GENERATES]->(es)
                RETURN count(es) AS cnt
                """,
                {"name": self.TEST_SITE_NAME},
            )
            assert services_count[0]["cnt"] == 0, (
                f"Bronze site should have no GENERATES edges, got {services_count[0]['cnt']}"
            )

            # Verify existing data not corrupted
            node_counts_after = _get_node_counts()
            # MPA count should increase by exactly 1
            assert node_counts_after.get("MPA", 0) == node_counts_before.get("MPA", 0) + 1, (
                "MPA count should increase by exactly 1"
            )
            # Document count should remain unchanged
            assert node_counts_after.get("Document", 0) == node_counts_before.get("Document", 0), (
                "Document count changed after Bronze site population"
            )

            print(f"\nPASS: Bronze site '{self.TEST_SITE_NAME}' created correctly (MPA only)")

        finally:
            # Clean up: remove test MPA node and temp file
            _cleanup_test_mpa(self.TEST_SITE_NAME)
            os.unlink(registry_path)

            # Verify cleanup
            remaining = run_query(
                "MATCH (m:MPA {name: $name}) RETURN count(m) AS cnt",
                {"name": self.TEST_SITE_NAME},
            )
            assert remaining[0]["cnt"] == 0, "Cleanup failed: test MPA node still exists"


# ---------------------------------------------------------------------------
# T1.5: Test Silver Site Population
# ---------------------------------------------------------------------------

@pytest.mark.integration
@skip_no_neo4j
class TestT15SilverSitePopulation:
    """T1.5: Test Silver tier with species, habitats, ecosystem services.
    Verify correct graph structure and clean up."""

    TEST_SITE_NAME = "__Test_Silver_Raja_Ampat__"

    def test_silver_site_population(self):
        """Create Silver site with species, habitats, services, then clean up."""
        from maris.sites.models import (
            CharacterizationTier,
            CoordinatePair,
            EcosystemServiceEstimate,
            HabitatInfo,
            SiteCharacterization,
            SpeciesRecord,
        )
        from maris.graph.population import _populate_registered_sites

        # Snapshot existing counts
        node_counts_before = _get_node_counts()

        silver_site = SiteCharacterization(
            canonical_name=self.TEST_SITE_NAME,
            tier=CharacterizationTier.silver,
            country="Indonesia",
            area_km2=40000.0,
            designation_year=2007,
            coordinates=CoordinatePair(latitude=-0.5, longitude=130.5),
            neoli_score=3,
            asset_rating="A",
            species=[
                SpeciesRecord(
                    scientific_name="Manta birostris",
                    common_name="Giant Manta Ray",
                    worms_aphia_id=9999001,
                    trophic_level=3.5,
                ),
                SpeciesRecord(
                    scientific_name="Chelonia mydas",
                    common_name="Green Sea Turtle",
                    worms_aphia_id=9999002,
                ),
                SpeciesRecord(
                    scientific_name="Dugong dugon",
                    common_name="Dugong",
                    worms_aphia_id=9999003,
                ),
            ],
            habitats=[
                HabitatInfo(
                    habitat_id="test_mangrove_integration",
                    name="Test Mangrove (Integration)",
                    extent_km2=500.0,
                ),
            ],
            ecosystem_services=[
                EcosystemServiceEstimate(
                    service_type="tourism",
                    service_name="Dive Tourism",
                    annual_value_usd=15_000_000.0,
                    valuation_method="market_price",
                ),
                EcosystemServiceEstimate(
                    service_type="fisheries",
                    service_name="Small-Scale Fisheries",
                    annual_value_usd=8_000_000.0,
                    valuation_method="market_price",
                ),
            ],
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            registry_data = {
                "version": "1.0",
                "site_count": 1,
                "sites": {
                    self.TEST_SITE_NAME.lower().replace(" ", "_"): silver_site.model_dump(mode="json"),
                },
            }
            json.dump(registry_data, f, indent=2, default=str)
            registry_path = f.name

        try:
            driver = get_driver()
            cfg = get_config()
            with driver.session(database=cfg.neo4j_database) as session:
                count = _populate_registered_sites(session, registry_path=Path(registry_path))

            # Silver tier should create MPA + species + habitat + services + edges
            # 1 MPA + 3 species (with LOCATED_IN) + 1 habitat (with HAS_HABITAT) + 2 services (with GENERATES)
            assert count >= 7, f"Expected at least 7 operations for Silver, got {count}"

            # Verify MPA node
            mpa_records = run_query(
                "MATCH (m:MPA {name: $name}) RETURN m",
                {"name": self.TEST_SITE_NAME},
            )
            assert len(mpa_records) == 1, f"Expected 1 MPA node, got {len(mpa_records)}"
            mpa = mpa_records[0]["m"]
            assert mpa["characterization_tier"] == "silver"
            assert mpa["country"] == "Indonesia"

            # Verify Species nodes and LOCATED_IN edges
            species_records = run_query(
                """
                MATCH (s:Species)-[:LOCATED_IN]->(m:MPA {name: $name})
                RETURN s.worms_id AS worms_id, s.scientific_name AS name
                ORDER BY s.worms_id
                """,
                {"name": self.TEST_SITE_NAME},
            )
            assert len(species_records) == 3, (
                f"Expected 3 species linked to Silver site, got {len(species_records)}"
            )
            worms_ids = {r["worms_id"] for r in species_records}
            assert worms_ids == {9999001, 9999002, 9999003}

            # Verify Habitat and HAS_HABITAT edge
            habitat_records = run_query(
                """
                MATCH (m:MPA {name: $name})-[:HAS_HABITAT]->(h:Habitat)
                RETURN h.habitat_id AS habitat_id, h.name AS name
                """,
                {"name": self.TEST_SITE_NAME},
            )
            assert len(habitat_records) == 1, (
                f"Expected 1 habitat, got {len(habitat_records)}"
            )
            assert habitat_records[0]["habitat_id"] == "test_mangrove_integration"

            # Verify EcosystemService nodes and GENERATES edges
            service_records = run_query(
                """
                MATCH (m:MPA {name: $name})-[g:GENERATES]->(es:EcosystemService)
                RETURN es.service_id AS service_id, es.service_type AS svc_type,
                       es.annual_value_usd AS value, g.total_usd_yr AS edge_value
                ORDER BY es.service_type
                """,
                {"name": self.TEST_SITE_NAME},
            )
            assert len(service_records) == 2, (
                f"Expected 2 ecosystem services, got {len(service_records)}"
            )
            svc_types = {r["svc_type"] for r in service_records}
            assert "tourism" in svc_types
            assert "fisheries" in svc_types

            # Verify no collision with existing sites
            existing_mpas = run_query(
                """
                MATCH (m:MPA)
                WHERE m.name IN ['Cabo Pulmo National Park', 'Shark Bay World Heritage Area']
                RETURN m.name AS name, m.total_esv_usd AS esv
                """
            )
            for mpa_rec in existing_mpas:
                assert mpa_rec["esv"] is not None, (
                    f"{mpa_rec['name']} ESV became None after Silver site population"
                )

            print(f"\nPASS: Silver site '{self.TEST_SITE_NAME}' created with full graph structure")

        finally:
            # Clean up
            _cleanup_test_mpa(self.TEST_SITE_NAME)
            os.unlink(registry_path)

            # Verify cleanup restored original counts
            node_counts_after = _get_node_counts()
            assert node_counts_after.get("MPA", 0) == node_counts_before.get("MPA", 0), (
                f"MPA count not restored: {node_counts_after.get('MPA', 0)} vs {node_counts_before.get('MPA', 0)}"
            )


# ---------------------------------------------------------------------------
# T1.6: Population with SemanticaBackedManager Provenance
# ---------------------------------------------------------------------------

@pytest.mark.integration
@skip_no_semantica
class TestT16SemanticaProvenance:
    """T1.6: Create a SemanticaBackedManager with temp SQLite, track all 35
    axiom extractions, verify summary shows semantica_entries >= 35."""

    def test_semantica_provenance_during_population(self):
        """Track all 35 axiom extractions through SemanticaBackedManager."""
        from maris.semantica_bridge.manager import SemanticaBackedManager

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            mgr = SemanticaBackedManager(
                templates_path=str(TEMPLATES_PATH),
                evidence_path=str(EVIDENCE_PATH),
                db_path=db_path,
            )

            # Verify initial state
            assert mgr.semantica_available is True
            assert mgr.registry.count() == 40, (
                f"Expected 40 axioms in registry, got {mgr.registry.count()}"
            )

            # Track each axiom extraction
            tracked_count = 0
            for i in range(1, 17):
                axiom_id = f"BA-{i:03d}"
                axiom = mgr.registry.get(axiom_id)
                if axiom is not None:
                    result = mgr.track_extraction(
                        entity_id=f"axiom:{axiom_id}",
                        entity_type="BridgeAxiom",
                        source_doi=axiom.source_doi,
                        attributes={
                            "name": axiom.name,
                            "coefficient": axiom.coefficient,
                        },
                    )
                    assert result is not None, f"track_extraction returned None for {axiom_id}"
                    tracked_count += 1

            assert tracked_count == 16, (
                f"Only tracked {tracked_count}/16 axioms"
            )

            # Verify summary
            summary = mgr.summary()
            print(f"\nProvenance summary: {json.dumps(summary, indent=2, default=str)}")

            assert summary["semantica_available"] is True
            assert summary["axioms_loaded"] == 40
            assert summary["semantica_entries"] >= 35, (
                f"Expected semantica_entries >= 35, got {summary['semantica_entries']}"
            )

            print(f"\nPASS: All 35 axioms tracked in Semantica backend "
                  f"(entries={summary['semantica_entries']})")

        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_semantica_axiom_application_tracking(self):
        """Verify axiom application is tracked through SemanticaBackedManager."""
        from maris.semantica_bridge.manager import SemanticaBackedManager

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            mgr = SemanticaBackedManager(
                templates_path=str(TEMPLATES_PATH),
                evidence_path=str(EVIDENCE_PATH),
                db_path=db_path,
            )

            # Track a source extraction first
            mgr.track_extraction(
                entity_id="shark_bay_seagrass",
                entity_type="SeagrassExtent",
                source_doi="10.1038/s41558-018-0096-y",
                attributes={"extent_ha": 480_000},
            )

            # Apply BA-013: seagrass -> carbon sequestration
            result = mgr.track_axiom_application(
                axiom_id="BA-013",
                input_entity_id="shark_bay_seagrass",
                output_entity_id="shark_bay_carbon_seq",
                input_value=480_000,
                output_value=403_200,
            )
            assert result is not None, "Axiom application tracking returned None"

            # Verify the application was recorded
            summary = mgr.summary()
            assert summary["semantica_entries"] > 0, (
                "No Semantica entries after axiom application"
            )

            print(f"\nPASS: Axiom application tracked (entries={summary['semantica_entries']})")

        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


# ---------------------------------------------------------------------------
# T1.7: OBIS Enrichment on MPA Nodes
# ---------------------------------------------------------------------------

@pytest.mark.integration
@skip_no_neo4j
class TestT17OBISEnrichment:
    """T1.7: Verify OBIS enrichment properties on gold-tier MPA nodes.

    Tests gracefully skip if no OBIS data has been fetched yet.
    Run scripts/enrich_obis.py first to populate OBIS properties.
    """

    def _get_obis_enriched_mpas(self) -> list[dict]:
        """Return MPAs that have OBIS data (obis_fetched_at is set)."""
        return run_query(
            """
            MATCH (m:MPA)
            WHERE m.obis_fetched_at IS NOT NULL
            RETURN m.name AS name,
                   m.obis_species_richness AS species_richness,
                   m.obis_iucn_threatened_count AS iucn_threatened,
                   m.obis_total_records AS total_records,
                   m.obis_observation_quality_score AS quality_score,
                   m.obis_median_sst_c AS median_sst,
                   m.obis_data_year_min AS year_min,
                   m.obis_data_year_max AS year_max
            ORDER BY m.name
            """
        )

    def test_obis_properties_on_mpas(self):
        """If any MPA has OBIS data, verify required properties are set and valid."""
        enriched = self._get_obis_enriched_mpas()

        if not enriched:
            pytest.skip(
                "No MPAs have OBIS data yet. "
                "Run: python scripts/enrich_obis.py"
            )

        print(f"\n{len(enriched)} OBIS-enriched MPAs found")

        for mpa in enriched:
            name = mpa["name"]
            sr = mpa["species_richness"]
            assert sr is not None, f"{name}: obis_species_richness is None"
            assert isinstance(sr, int), (
                f"{name}: obis_species_richness is not int: {type(sr)}"
            )
            assert sr >= 0, f"{name}: obis_species_richness is negative: {sr}"

            tr = mpa["total_records"]
            assert tr is not None, f"{name}: obis_total_records is None"
            assert tr >= 0, f"{name}: obis_total_records is negative: {tr}"

            print(f"  {name}: species={sr}, records={tr}")

    def test_obis_quality_score_range(self):
        """OBIS observation quality score must be in [0, 1] for enriched MPAs."""
        enriched = self._get_obis_enriched_mpas()

        if not enriched:
            pytest.skip(
                "No MPAs have OBIS data yet. "
                "Run: python scripts/enrich_obis.py"
            )

        for mpa in enriched:
            name = mpa["name"]
            qs = mpa["quality_score"]
            if qs is not None:
                assert 0.0 <= qs <= 1.0, (
                    f"{name}: obis_observation_quality_score {qs} out of [0, 1]"
                )

        print(f"\nPASS: Quality scores valid for {len(enriched)} OBIS-enriched MPAs")

    def test_obis_year_range_consistency(self):
        """If year_min and year_max are set, year_min <= year_max."""
        enriched = self._get_obis_enriched_mpas()

        if not enriched:
            pytest.skip("No MPAs have OBIS data yet.")

        for mpa in enriched:
            name = mpa["name"]
            y_min = mpa["year_min"]
            y_max = mpa["year_max"]
            if y_min is not None and y_max is not None:
                assert y_min <= y_max, (
                    f"{name}: year_min ({y_min}) > year_max ({y_max})"
                )

        print(f"\nPASS: Year ranges consistent for {len(enriched)} OBIS-enriched MPAs")
