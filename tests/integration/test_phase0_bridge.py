"""Phase 0 Integration Tests: Semantica SDK Bridge Validation (T0.1-T0.9).

These tests validate the Semantica SDK bridge against real data (35 axioms,
2 sites, SQLite persistence). This is the foundational layer - if the bridge
fails, nothing else works.

All tests use the @pytest.mark.integration marker and can be run via:
    pytest tests/integration/test_phase0_bridge.py -v
"""

from __future__ import annotations

import importlib.util
import os
import tempfile
from pathlib import Path

import pytest

# Project root for data file paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATES_PATH = PROJECT_ROOT / "schemas" / "bridge_axiom_templates.json"
EVIDENCE_PATH = PROJECT_ROOT / "data" / "semantica_export" / "bridge_axioms.json"

_HAS_SEMANTICA = importlib.util.find_spec("semantica") is not None


# ---------------------------------------------------------------------------
# T0.1: Bridge Availability Check
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT01BridgeAvailability:
    """T0.1: Verify SEMANTICA_AVAILABLE is True and all 7 SDK modules import."""

    def test_semantica_available_flag(self):
        from maris.semantica_bridge import SEMANTICA_AVAILABLE
        assert SEMANTICA_AVAILABLE is True, "Semantica SDK not installed or not importable"

    def test_semantica_package_imports(self):
        import semantica  # noqa: F401

    def test_semantica_provenance_imports(self):
        import semantica.provenance  # noqa: F401

    def test_semantica_provenance_manager_imports(self):
        import semantica.provenance.manager  # noqa: F401

    def test_semantica_provenance_storage_imports(self):
        import semantica.provenance.storage  # noqa: F401

    def test_semantica_provenance_schemas_imports(self):
        import semantica.provenance.schemas  # noqa: F401

    def test_semantica_provenance_bridge_axiom_imports(self):
        import semantica.provenance.bridge_axiom  # noqa: F401

    def test_semantica_provenance_integrity_imports(self):
        import semantica.provenance.integrity  # noqa: F401

    def test_all_bridge_exports_present(self):
        import maris.semantica_bridge as bridge
        expected = [
            "SEMANTICA_AVAILABLE",
            "SemanticaStorage",
            "SemanticaProvenanceAdapter",
            "SemanticaIntegrityVerifier",
            "SemanticaBackedManager",
            "to_semantica_axiom",
            "from_semantica_axiom",
            "apply_via_semantica",
            "create_semantica_chain",
        ]
        for name in expected:
            assert hasattr(bridge, name), f"Missing export: {name}"


# ---------------------------------------------------------------------------
# T0.2: SQLite Persistence Round-Trip
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT02SQLitePersistence:
    """T0.2: Prove that SemanticaBackedManager with SQLite persists across sessions."""

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_sqlite_persistence_round_trip(self):
        from maris.semantica_bridge.manager import SemanticaBackedManager

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            # Session 1: Write provenance data
            mgr1 = SemanticaBackedManager(
                templates_path=str(TEMPLATES_PATH),
                db_path=db_path,
            )
            mgr1.track_extraction(
                entity_id="cabo_pulmo_esv",
                entity_type="EcosystemServiceValuation",
                source_doi="10.1371/journal.pone.0062799",
                attributes={"total_esv_usd": 29_270_000, "method": "market-price"},
            )
            mgr1.track_extraction(
                entity_id="shark_bay_carbon",
                entity_type="CarbonSequestration",
                source_doi="10.1038/s41558-018-0096-y",
                attributes={"annual_carbon_usd": 12_100_000, "rate_tco2_ha_yr": 0.84},
            )
            stats1 = mgr1.provenance.get_semantica_statistics()
            assert stats1["total_entries"] >= 2, (
                f"Session 1 should have >= 2 Semantica entries, got {stats1['total_entries']}"
            )

            # Session 2: New manager instance against same SQLite DB
            mgr2 = SemanticaBackedManager(
                templates_path=str(TEMPLATES_PATH),
                db_path=db_path,
            )
            stats2 = mgr2.provenance.get_semantica_statistics()
            assert stats2["total_entries"] >= 2, (
                f"Session 2 should read back >= 2 entries from SQLite, got {stats2['total_entries']}. "
                "Persistence gap NOT solved."
            )

        finally:
            os.unlink(db_path)


# ---------------------------------------------------------------------------
# T0.3: All 16 Real Axioms - Conversion Round-Trip
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT03AxiomConversionRoundTrip:
    """T0.3: Load all 35 axioms, convert MARIS -> Semantica -> MARIS, verify lossless."""

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_registry_loads_all_35_axioms(self):
        from maris.provenance.bridge_axiom_registry import BridgeAxiomRegistry

        registry = BridgeAxiomRegistry()
        registry.load(TEMPLATES_PATH, EVIDENCE_PATH)
        assert registry.count() == 35, f"Expected 35 axioms, got {registry.count()}"

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_all_35_axioms_round_trip_losslessly(self):
        from maris.provenance.bridge_axiom_registry import BridgeAxiomRegistry
        from maris.semantica_bridge.axiom_adapter import to_semantica_axiom, from_semantica_axiom

        registry = BridgeAxiomRegistry()
        registry.load(TEMPLATES_PATH, EVIDENCE_PATH)

        for i in range(1, 17):
            axiom_id = f"BA-{i:03d}"
            maris_axiom = registry.get(axiom_id)
            assert maris_axiom is not None, f"Axiom {axiom_id} not in registry"

            # MARIS -> Semantica
            sem_axiom = to_semantica_axiom(maris_axiom)
            assert sem_axiom is not None, f"to_semantica_axiom returned None for {axiom_id}"
            assert sem_axiom.axiom_id == axiom_id
            assert sem_axiom.name == maris_axiom.name
            assert sem_axiom.coefficient == maris_axiom.coefficient
            assert sem_axiom.source_doi == maris_axiom.source_doi

            # Semantica -> MARIS
            roundtrip = from_semantica_axiom(sem_axiom)
            assert roundtrip.axiom_id == axiom_id
            assert roundtrip.name == maris_axiom.name
            assert abs(roundtrip.coefficient - maris_axiom.coefficient) < 1e-9, (
                f"{axiom_id}: coefficient mismatch {roundtrip.coefficient} != {maris_axiom.coefficient}"
            )

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_confidence_mapping(self):
        """Verify confidence string -> float mapping: high->0.9, medium->0.7, low->0.4."""
        from maris.provenance.bridge_axiom_registry import BridgeAxiomRegistry
        from maris.semantica_bridge.axiom_adapter import to_semantica_axiom

        registry = BridgeAxiomRegistry()
        registry.load(TEMPLATES_PATH, EVIDENCE_PATH)

        confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.4}

        for axiom in registry.get_all():
            sem_axiom = to_semantica_axiom(axiom)
            if isinstance(axiom.confidence, str):
                expected = confidence_map.get(axiom.confidence, 0.7)
                assert sem_axiom.confidence == expected, (
                    f"{axiom.axiom_id}: confidence '{axiom.confidence}' should map to {expected}, "
                    f"got {sem_axiom.confidence}"
                )


# ---------------------------------------------------------------------------
# T0.4: Axiom Application via Semantica
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT04AxiomApplication:
    """T0.4: Apply BA-013 and BA-014 through the bridge, verify Shark Bay ~$12.1M."""

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_ba013_seagrass_carbon_sequestration(self):
        from maris.provenance.bridge_axiom_registry import BridgeAxiomRegistry
        from maris.semantica_bridge.axiom_adapter import apply_via_semantica
        from semantica.provenance.manager import ProvenanceManager as SemanticaPM
        from semantica.provenance.storage import InMemoryStorage

        registry = BridgeAxiomRegistry()
        registry.load(TEMPLATES_PATH, EVIDENCE_PATH)

        sem_pm = SemanticaPM(storage=InMemoryStorage())

        ba013 = registry.get("BA-013")
        assert ba013 is not None
        # BA-013 coefficient is 0.84 tCO2/ha/yr
        result = apply_via_semantica(
            maris_axiom=ba013,
            input_entity="shark_bay_seagrass",
            input_value=480_000,  # 4,800 km2 = 480,000 ha
            prov_manager=sem_pm,
        )
        # Expected: 480,000 * 0.84 = 403,200 tCO2/yr
        assert abs(result["output_value"] - 403_200) < 1.0, (
            f"BA-013: expected ~403,200, got {result['output_value']}"
        )
        assert result["axiom_id"] == "BA-013"

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_ba014_carbon_to_credit_value(self):
        from maris.provenance.bridge_axiom_registry import BridgeAxiomRegistry
        from maris.semantica_bridge.axiom_adapter import apply_via_semantica
        from semantica.provenance.manager import ProvenanceManager as SemanticaPM
        from semantica.provenance.storage import InMemoryStorage

        registry = BridgeAxiomRegistry()
        registry.load(TEMPLATES_PATH, EVIDENCE_PATH)

        sem_pm = SemanticaPM(storage=InMemoryStorage())

        ba014 = registry.get("BA-014")
        assert ba014 is not None
        # BA-014 coefficient is $30/tCO2
        result = apply_via_semantica(
            maris_axiom=ba014,
            input_entity="shark_bay_carbon_stock",
            input_value=403_200,  # from BA-013 output
            prov_manager=sem_pm,
        )
        # Expected: 403,200 * 30 = $12,096,000
        assert abs(result["output_value"] - 12_096_000) < 100, (
            f"BA-014: expected ~$12,096,000, got {result['output_value']}"
        )

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_chained_ba013_ba014_approximates_shark_bay(self):
        """Chain BA-013 -> BA-014: 480,000 ha -> ~$12.1M."""
        from maris.provenance.bridge_axiom_registry import BridgeAxiomRegistry
        from maris.semantica_bridge.axiom_adapter import apply_via_semantica
        from semantica.provenance.manager import ProvenanceManager as SemanticaPM
        from semantica.provenance.storage import InMemoryStorage

        registry = BridgeAxiomRegistry()
        registry.load(TEMPLATES_PATH, EVIDENCE_PATH)

        sem_pm = SemanticaPM(storage=InMemoryStorage())

        ba013 = registry.get("BA-013")
        ba014 = registry.get("BA-014")

        # Step 1: seagrass area -> carbon sequestration
        r1 = apply_via_semantica(ba013, "shark_bay_seagrass", 480_000, sem_pm)
        # Step 2: carbon sequestration -> credit value
        r2 = apply_via_semantica(ba014, "shark_bay_carbon", r1["output_value"], sem_pm)

        final_value = r2["output_value"]
        # Should be close to $12.1M
        assert 11_000_000 < final_value < 13_000_000, (
            f"Chained result should approximate $12.1M, got ${final_value:,.0f}"
        )

        # Verify provenance was tracked
        stats = sem_pm.get_statistics()
        assert stats["total_entries"] >= 2, (
            f"Expected >= 2 provenance entries, got {stats['total_entries']}"
        )


# ---------------------------------------------------------------------------
# T0.5: Dual-Write Provenance Verification
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT05DualWriteProvenance:
    """T0.5: Verify entities exist in BOTH MARIS and Semantica backends."""

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_entity_in_both_backends(self):
        from maris.semantica_bridge.provenance_adapter import SemanticaProvenanceAdapter

        adapter = SemanticaProvenanceAdapter()

        adapter.track_entity(
            entity_id="cabo_pulmo_tourism",
            entity_type="EcosystemService",
            attributes={
                "annual_value_usd": 25_000_000,
                "method": "market-price",
                "doi": "10.1016/j.marpol.2024",
            },
            derived_from=["doc:10.1016/j.marpol.2024"],
            attributed_to="maris:system",
        )

        # Check MARIS backend
        maris_entity = adapter.get_entity("cabo_pulmo_tourism")
        assert maris_entity is not None, "Entity missing from MARIS backend"
        assert maris_entity["entity_type"] == "EcosystemService"

        # Check Semantica backend
        sem_stats = adapter.get_semantica_statistics()
        assert sem_stats["total_entries"] >= 1, (
            f"Entity not mirrored to Semantica backend. Stats: {sem_stats}"
        )

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_lineage_available_from_both_backends(self):
        from maris.semantica_bridge.provenance_adapter import SemanticaProvenanceAdapter

        adapter = SemanticaProvenanceAdapter()

        # Create parent -> child derivation
        adapter.track_entity(
            entity_id="doc:10.1371/test",
            entity_type="Document",
            attributes={"doi": "10.1371/test"},
        )
        adapter.track_entity(
            entity_id="cabo_esv_test",
            entity_type="EcosystemService",
            derived_from=["doc:10.1371/test"],
        )

        # MARIS lineage
        maris_lineage = adapter.get_lineage("cabo_esv_test")
        assert len(maris_lineage) == 2, (
            f"Expected 2 lineage entries, got {len(maris_lineage)}"
        )

        # Semantica lineage
        sem_lineage = adapter.get_semantica_lineage("cabo_esv_test")
        assert isinstance(sem_lineage, dict)


# ---------------------------------------------------------------------------
# T0.6: Integrity Verification via Semantica
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT06IntegrityVerification:
    """T0.6: Checksums are deterministic, tamper detection works."""

    def test_checksum_deterministic(self):
        from maris.semantica_bridge.integrity_adapter import SemanticaIntegrityVerifier

        data = {
            "entity_id": "cabo_pulmo_esv",
            "entity_type": "EcosystemServiceValuation",
            "total_esv_usd": 29_270_000,
            "tourism_usd": 25_000_000,
            "biomass_ratio": 4.63,
            "ci_low": 3.8,
            "ci_high": 5.5,
        }

        cs1 = SemanticaIntegrityVerifier.compute_checksum(data)
        cs2 = SemanticaIntegrityVerifier.compute_checksum(data)
        assert cs1 == cs2, "Checksums not deterministic"
        assert len(cs1) == 64, f"Expected SHA-256 hex (64 chars), got {len(cs1)}"

    def test_tamper_detection(self):
        from maris.semantica_bridge.integrity_adapter import SemanticaIntegrityVerifier

        data = {
            "entity_id": "cabo_pulmo_esv",
            "entity_type": "EcosystemServiceValuation",
            "total_esv_usd": 29_270_000,
        }

        checksum = SemanticaIntegrityVerifier.compute_checksum(data)

        tampered = {**data, "total_esv_usd": 30_000_000}
        tampered_checksum = SemanticaIntegrityVerifier.compute_checksum(tampered)

        assert checksum != tampered_checksum, "Tampered data has same checksum"

    def test_verify_accepts_original(self):
        from maris.semantica_bridge.integrity_adapter import SemanticaIntegrityVerifier

        data = {"name": "Cabo Pulmo", "esv": 29.27}
        checksum = SemanticaIntegrityVerifier.compute_checksum(data)
        assert SemanticaIntegrityVerifier.verify(data, checksum) is True

    def test_verify_rejects_tampered(self):
        from maris.semantica_bridge.integrity_adapter import SemanticaIntegrityVerifier

        data = {"name": "Cabo Pulmo", "esv": 29.27}
        checksum = SemanticaIntegrityVerifier.compute_checksum(data)

        tampered = {"name": "Cabo Pulmo", "esv": 30.0}
        assert SemanticaIntegrityVerifier.verify(tampered, checksum) is False

    def test_key_order_invariance(self):
        from maris.semantica_bridge.integrity_adapter import SemanticaIntegrityVerifier

        data_a = {"b": 2, "a": 1}
        data_b = {"a": 1, "b": 2}
        assert (
            SemanticaIntegrityVerifier.compute_checksum(data_a)
            == SemanticaIntegrityVerifier.compute_checksum(data_b)
        ), "Checksum should be key-order invariant"


# ---------------------------------------------------------------------------
# T0.7: SemanticaBackedManager Full Lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT07ManagerFullLifecycle:
    """T0.7: Init with real axiom templates, track, certificate, lineage, summary."""

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_full_lifecycle(self):
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
            assert mgr.registry.count() == 35

            initial_summary = mgr.summary()
            assert initial_summary["semantica_available"] is True
            assert initial_summary["axioms_loaded"] == 35

            # Track extraction
            entity_data = mgr.track_extraction(
                entity_id="cabo_pulmo_esv",
                entity_type="EcosystemServiceValuation",
                source_doi="10.1371/journal.pone.0062799",
                attributes={"total_esv_usd": 29_270_000},
            )
            assert entity_data["entity_id"] == "cabo_pulmo_esv"
            assert entity_data["entity_type"] == "EcosystemServiceValuation"

            # Track axiom application (BA-002: no-take MPA biomass multiplier)
            mgr.provenance.track_entity("cabo_pulmo_baseline_biomass", entity_type="Observation")
            result = mgr.track_axiom_application(
                axiom_id="BA-002",
                input_entity_id="cabo_pulmo_baseline_biomass",
                output_entity_id="cabo_pulmo_recovered_biomass",
                input_value=1.0,
                output_value=4.63,
            )
            assert result is not None
            assert result["attributes"]["axiom_id"] == "BA-002"

            # Get certificate
            cert = mgr.get_certificate("cabo_pulmo_esv")
            assert cert["entity_id"] == "cabo_pulmo_esv"
            assert "checksum" in cert

            # Get lineage
            lineage = mgr.get_lineage("cabo_pulmo_esv")
            assert len(lineage) >= 2, f"Expected >= 2 lineage entries, got {len(lineage)}"

            # Final summary should show Semantica entries
            final_summary = mgr.summary()
            assert final_summary["semantica_entries"] > 0, (
                f"Expected semantica_entries > 0, got {final_summary['semantica_entries']}"
            )

        finally:
            os.unlink(db_path)


# ---------------------------------------------------------------------------
# T0.8: Translation Chain via Semantica
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT08TranslationChain:
    """T0.8: Execute BA-013 -> BA-014 chain, verify ~$12.1M."""

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_chain_ba013_ba014_via_manager(self):
        from maris.semantica_bridge.manager import SemanticaBackedManager

        mgr = SemanticaBackedManager(
            templates_path=str(TEMPLATES_PATH),
            evidence_path=str(EVIDENCE_PATH),
        )

        result = mgr.execute_chain(
            axiom_ids=["BA-013", "BA-014"],
            input_data={
                "entity_id": "shark_bay_seagrass_extent",
                "value": 480_000,
                "unit": "hectares",
                "source": "direct_survey",
            },
        )

        # Verify chain executed
        assert result["axiom_count"] == 2

        # Verify final value approximates $12.1M
        final_value = result.get("final_value")
        assert final_value is not None, "Chain did not produce a final_value"
        assert 11_000_000 < final_value < 13_000_000, (
            f"Chain result should approximate $12.1M, got ${final_value:,.0f}"
        )

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_chain_has_source_dois(self):
        from maris.semantica_bridge.manager import SemanticaBackedManager

        mgr = SemanticaBackedManager(
            templates_path=str(TEMPLATES_PATH),
            evidence_path=str(EVIDENCE_PATH),
        )

        result = mgr.execute_chain(
            axiom_ids=["BA-013", "BA-014"],
            input_data={"entity_id": "test", "value": 480_000, "source": "test"},
        )

        # Both axioms have DOIs
        assert len(result.get("source_dois", [])) == 2

    def test_chain_fallback_without_semantica(self):
        """Even without Semantica, the chain should produce a result via MARIS fallback."""
        from maris.semantica_bridge import axiom_adapter
        from maris.provenance.bridge_axiom import BridgeAxiom

        original = axiom_adapter._HAS_SEMANTICA
        axiom_adapter._HAS_SEMANTICA = False
        try:
            ax1 = BridgeAxiom(axiom_id="BA-013", name="seagrass_carbon", coefficient=0.84,
                              source_doi="10.1038/s41467-025-64667-6")
            ax2 = BridgeAxiom(axiom_id="BA-014", name="carbon_credit", coefficient=30.0,
                              source_doi="10.1038/s44183-025-00111-y")

            result = axiom_adapter.create_semantica_chain(
                maris_axioms=[ax1, ax2],
                input_data={"value": 480_000},
            )
            # 480,000 * 0.84 * 30 = 12,096,000
            assert abs(result["final_value"] - 12_096_000) < 1.0
        finally:
            axiom_adapter._HAS_SEMANTICA = original


# ---------------------------------------------------------------------------
# T0.9: Graceful Degradation (Semantica Unavailable)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT09GracefulDegradation:
    """T0.9: SemanticaStorage works with _semantica=None (local-only mode)."""

    def test_crud_without_semantica_backend(self):
        from maris.semantica_bridge.storage_adapter import SemanticaStorage

        storage = SemanticaStorage.__new__(SemanticaStorage)
        storage._local = {}
        storage._lock = __import__("threading").Lock()
        storage._semantica = None  # Simulate no Semantica

        # Put and get
        storage.put("entity", "test1", {"value": 42, "name": "test"})
        result = storage.get("entity", "test1")
        assert result is not None
        assert result["value"] == 42

        # Exists
        assert storage.exists("entity", "test1") is True
        assert storage.exists("entity", "nonexistent") is False

        # Delete
        assert storage.delete("entity", "test1") is True
        assert storage.get("entity", "test1") is None

    def test_list_and_find_without_semantica_backend(self):
        from maris.semantica_bridge.storage_adapter import SemanticaStorage

        storage = SemanticaStorage.__new__(SemanticaStorage)
        storage._local = {}
        storage._lock = __import__("threading").Lock()
        storage._semantica = None

        storage.put("entity", "e1", {"entity_type": "MPA", "name": "Cabo Pulmo"})
        storage.put("entity", "e2", {"entity_type": "Species", "name": "Lutjanus"})
        storage.put("activity", "a1", {"type": "extraction"})

        # list_by_type
        entities = storage.list_by_type("entity")
        assert len(entities) == 2

        # find
        mpas = storage.find("entity", entity_type="MPA")
        assert len(mpas) == 1

        # count
        assert storage.count() == 3
        assert storage.count("entity") == 2

    def test_lineage_fallback_without_semantica_backend(self):
        from maris.semantica_bridge.storage_adapter import SemanticaStorage

        storage = SemanticaStorage.__new__(SemanticaStorage)
        storage._local = {}
        storage._lock = __import__("threading").Lock()
        storage._semantica = None

        storage.put("entity", "parent", {"entity_type": "Document", "derived_from": []})
        storage.put("entity", "child", {"entity_type": "MPA", "derived_from": ["parent"]})

        chain = storage.trace_lineage("child")
        assert len(chain) == 2, f"Expected 2 lineage entries, got {len(chain)}"

        types = [r.get("entity_type") for r in chain]
        assert "MPA" in types
        assert "Document" in types

    def test_clear_without_semantica_backend(self):
        from maris.semantica_bridge.storage_adapter import SemanticaStorage

        storage = SemanticaStorage.__new__(SemanticaStorage)
        storage._local = {}
        storage._lock = __import__("threading").Lock()
        storage._semantica = None

        storage.put("entity", "e1", {"value": 1})
        storage.put("entity", "e2", {"value": 2})
        assert storage.count() == 2

        storage.clear()
        assert storage.count() == 0
