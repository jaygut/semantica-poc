"""Tests for the Semantica SDK bridge layer.

Verifies that maris.semantica_bridge adapters correctly delegate to the real
Semantica SDK while maintaining API compatibility with MARIS's native
provenance system.  Tests run whether or not the semantica package is installed
(graceful degradation is part of the contract).
"""

from __future__ import annotations

import importlib
import os
import tempfile
from pathlib import Path

import pytest

# Detect whether the real semantica package is available
_HAS_SEMANTICA = importlib.util.find_spec("semantica") is not None


# ---------------------------------------------------------------------------
# Module-level import checks
# ---------------------------------------------------------------------------

class TestBridgeImports:
    """Verify all bridge modules import cleanly."""

    def test_bridge_package_imports(self):
        import maris.semantica_bridge as bridge
        assert hasattr(bridge, "SEMANTICA_AVAILABLE")
        assert hasattr(bridge, "SemanticaStorage")
        assert hasattr(bridge, "SemanticaProvenanceAdapter")
        assert hasattr(bridge, "SemanticaIntegrityVerifier")
        assert hasattr(bridge, "SemanticaBackedManager")
        assert hasattr(bridge, "to_semantica_axiom")
        assert hasattr(bridge, "from_semantica_axiom")
        assert hasattr(bridge, "apply_via_semantica")
        assert hasattr(bridge, "create_semantica_chain")
        assert isinstance(bridge.SEMANTICA_AVAILABLE, bool)

    def test_semantica_available_flag_matches_reality(self):
        from maris.semantica_bridge import SEMANTICA_AVAILABLE
        assert SEMANTICA_AVAILABLE == _HAS_SEMANTICA


# ---------------------------------------------------------------------------
# SemanticaStorage tests
# ---------------------------------------------------------------------------

class TestSemanticaStorage:
    """Test SemanticaStorage adapter (drop-in for InMemoryStorage)."""

    def test_put_get_roundtrip(self):
        from maris.semantica_bridge.storage_adapter import SemanticaStorage

        store = SemanticaStorage()
        store.put("entity", "e1", {"entity_type": "MPA", "name": "Cabo Pulmo"})
        result = store.get("entity", "e1")
        assert result is not None
        assert result["name"] == "Cabo Pulmo"

    def test_get_returns_none_for_missing(self):
        from maris.semantica_bridge.storage_adapter import SemanticaStorage

        store = SemanticaStorage()
        assert store.get("entity", "nonexistent") is None

    def test_delete(self):
        from maris.semantica_bridge.storage_adapter import SemanticaStorage

        store = SemanticaStorage()
        store.put("entity", "e1", {"name": "test"})
        assert store.delete("entity", "e1") is True
        assert store.delete("entity", "e1") is False
        assert store.get("entity", "e1") is None

    def test_exists(self):
        from maris.semantica_bridge.storage_adapter import SemanticaStorage

        store = SemanticaStorage()
        assert store.exists("entity", "e1") is False
        store.put("entity", "e1", {"name": "test"})
        assert store.exists("entity", "e1") is True

    def test_list_by_type(self):
        from maris.semantica_bridge.storage_adapter import SemanticaStorage

        store = SemanticaStorage()
        store.put("entity", "e1", {"name": "a"})
        store.put("entity", "e2", {"name": "b"})
        store.put("activity", "a1", {"type": "extraction"})

        entities = store.list_by_type("entity")
        assert len(entities) == 2
        activities = store.list_by_type("activity")
        assert len(activities) == 1

    def test_find_by_attributes(self):
        from maris.semantica_bridge.storage_adapter import SemanticaStorage

        store = SemanticaStorage()
        store.put("entity", "e1", {"entity_type": "MPA", "name": "Cabo Pulmo"})
        store.put("entity", "e2", {"entity_type": "Species", "name": "Lutjanus"})
        store.put("entity", "e3", {"entity_type": "MPA", "name": "Shark Bay"})

        mpas = store.find("entity", entity_type="MPA")
        assert len(mpas) == 2

    def test_count(self):
        from maris.semantica_bridge.storage_adapter import SemanticaStorage

        store = SemanticaStorage()
        store.put("entity", "e1", {"name": "a"})
        store.put("entity", "e2", {"name": "b"})
        store.put("activity", "a1", {"type": "x"})

        assert store.count() == 3
        assert store.count("entity") == 2
        assert store.count("activity") == 1

    def test_clear(self):
        from maris.semantica_bridge.storage_adapter import SemanticaStorage

        store = SemanticaStorage()
        store.put("entity", "e1", {"name": "a"})
        store.put("entity", "e2", {"name": "b"})
        store.clear()
        assert store.count() == 0

    def test_deep_copy_isolation(self):
        from maris.semantica_bridge.storage_adapter import SemanticaStorage

        store = SemanticaStorage()
        data = {"name": "original", "nested": {"key": "val"}}
        store.put("entity", "e1", data)

        # Mutate original - should not affect stored copy
        data["name"] = "mutated"
        data["nested"]["key"] = "changed"

        retrieved = store.get("entity", "e1")
        assert retrieved["name"] == "original"
        assert retrieved["nested"]["key"] == "val"

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_sqlite_persistence(self):
        from maris.semantica_bridge.storage_adapter import SemanticaStorage

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = SemanticaStorage(db_path=db_path)
            store.put("entity", "e1", {"entity_type": "MPA", "name": "Cabo Pulmo"})

            # Verify Semantica backend has the entry
            entry = store.retrieve_semantica_entry("e1")
            assert entry is not None
            assert entry.entity_id == "e1"
        finally:
            os.unlink(db_path)

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_trace_lineage_via_semantica(self):
        from maris.semantica_bridge.storage_adapter import SemanticaStorage

        store = SemanticaStorage()
        store.put("entity", "doc1", {"entity_type": "Document", "derived_from": []})
        store.put("entity", "e1", {"entity_type": "MPA", "derived_from": ["doc1"]})

        lineage = store.trace_lineage("e1")
        assert len(lineage) >= 1

    def test_trace_lineage_fallback_without_semantica(self):
        from maris.semantica_bridge.storage_adapter import SemanticaStorage

        store = SemanticaStorage()
        store._semantica = None  # Force fallback
        store.put("entity", "doc1", {"entity_type": "Document", "derived_from": []})
        store.put("entity", "e1", {"entity_type": "MPA", "derived_from": ["doc1"]})

        lineage = store.trace_lineage("e1")
        assert len(lineage) == 2
        ids = [r.get("entity_type") for r in lineage]
        assert "MPA" in ids
        assert "Document" in ids


# ---------------------------------------------------------------------------
# Axiom adapter tests
# ---------------------------------------------------------------------------

class TestAxiomAdapter:
    """Test BridgeAxiom conversion between MARIS and Semantica formats."""

    def _make_maris_axiom(self):
        from maris.provenance.bridge_axiom import BridgeAxiom
        return BridgeAxiom(
            axiom_id="BA-001",
            name="mpa_biomass_dive_tourism_value",
            rule="IF biomass(Site, X) THEN tourism_value(Site, X * 0.346)",
            coefficient=0.346,
            input_domain="ecological",
            output_domain="financial",
            source_doi="10.1038/s41586-021-03371-z",
            source_page="Table S4",
            source_quote="84% higher WTP",
            confidence="high",
            ci_low=0.28,
            ci_high=0.41,
            applicable_habitats=["coral_reef"],
            evidence_sources=[{"doi": "10.1038/s41586-021-03371-z", "citation": "Smith 2021"}],
            caveats=["Tropical reefs only"],
        )

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_to_semantica_axiom(self):
        from maris.semantica_bridge.axiom_adapter import to_semantica_axiom
        from semantica.provenance.bridge_axiom import BridgeAxiom as SemAxiom

        maris_ax = self._make_maris_axiom()
        sem_ax = to_semantica_axiom(maris_ax)

        assert isinstance(sem_ax, SemAxiom)
        assert sem_ax.axiom_id == "BA-001"
        assert sem_ax.coefficient == 0.346
        assert sem_ax.confidence == 0.9  # "high" -> 0.9
        assert sem_ax.input_domain == "ecological"
        assert sem_ax.output_domain == "financial"

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_from_semantica_axiom(self):
        from maris.semantica_bridge.axiom_adapter import to_semantica_axiom, from_semantica_axiom
        from maris.provenance.bridge_axiom import BridgeAxiom as MARISAxiom

        original = self._make_maris_axiom()
        sem_ax = to_semantica_axiom(original)
        roundtrip = from_semantica_axiom(sem_ax)

        assert isinstance(roundtrip, MARISAxiom)
        assert roundtrip.axiom_id == "BA-001"
        assert roundtrip.coefficient == 0.346
        assert roundtrip.ci_low == 0.28
        assert roundtrip.ci_high == 0.41
        assert "coral_reef" in roundtrip.applicable_habitats

    def test_to_semantica_returns_none_without_package(self):
        from maris.semantica_bridge import axiom_adapter

        # Temporarily pretend semantica is not available
        original = axiom_adapter._HAS_SEMANTICA
        axiom_adapter._HAS_SEMANTICA = False
        try:
            result = axiom_adapter.to_semantica_axiom(self._make_maris_axiom())
            assert result is None
        finally:
            axiom_adapter._HAS_SEMANTICA = original

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_apply_via_semantica(self):
        from maris.semantica_bridge.axiom_adapter import apply_via_semantica

        axiom = self._make_maris_axiom()
        result = apply_via_semantica(axiom, "cabo_pulmo_biomass", 100.0)

        assert result["axiom_id"] == "BA-001"
        assert abs(result["output_value"] - 34.6) < 0.01
        assert result["input_entity"] == "cabo_pulmo_biomass"
        assert "ci_low" in result
        assert "ci_high" in result

    def test_apply_via_semantica_fallback(self):
        """Test that apply_via_semantica falls back to MARIS native."""
        from maris.semantica_bridge import axiom_adapter

        original = axiom_adapter._HAS_SEMANTICA
        axiom_adapter._HAS_SEMANTICA = False
        try:
            axiom = self._make_maris_axiom()
            result = axiom_adapter.apply_via_semantica(axiom, "entity1", 100.0)
            assert abs(result["output_value"] - 34.6) < 0.01
            assert result["input_entity"] == "entity1"
        finally:
            axiom_adapter._HAS_SEMANTICA = original

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_apply_via_semantica_with_provenance_tracking(self):
        from maris.semantica_bridge.axiom_adapter import apply_via_semantica
        from semantica.provenance.manager import ProvenanceManager

        pm = ProvenanceManager()
        axiom = self._make_maris_axiom()
        result = apply_via_semantica(axiom, "test_entity", 200.0, prov_manager=pm)

        assert abs(result["output_value"] - 69.2) < 0.01

        # Verify provenance was tracked
        stats = pm.get_statistics()
        assert stats["total_entries"] >= 1

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_create_semantica_chain(self):
        from maris.semantica_bridge.axiom_adapter import create_semantica_chain
        from maris.provenance.bridge_axiom import BridgeAxiom

        ax1 = BridgeAxiom(axiom_id="BA-001", name="a1", coefficient=2.0,
                          source_doi="10.1/a", source_page="p1")
        ax2 = BridgeAxiom(axiom_id="BA-002", name="a2", coefficient=3.0,
                          source_doi="10.1/b", source_page="p2")

        result = create_semantica_chain(
            maris_axioms=[ax1, ax2],
            input_data={"entity_id": "test", "value": 10.0, "source": "test_source"},
        )

        assert result["axiom_count"] == 2
        assert "10.1/a" in result["source_dois"]
        assert "10.1/b" in result["source_dois"]

    def test_create_semantica_chain_fallback(self):
        """Chain execution falls back to MARIS TranslationChain."""
        from maris.semantica_bridge import axiom_adapter
        from maris.provenance.bridge_axiom import BridgeAxiom

        original = axiom_adapter._HAS_SEMANTICA
        axiom_adapter._HAS_SEMANTICA = False
        try:
            ax1 = BridgeAxiom(axiom_id="BA-001", name="a1", coefficient=2.0)
            ax2 = BridgeAxiom(axiom_id="BA-002", name="a2", coefficient=3.0)

            result = axiom_adapter.create_semantica_chain(
                maris_axioms=[ax1, ax2],
                input_data={"value": 10.0},
            )
            assert result["final_value"] == 60.0  # 10 * 2 * 3
        finally:
            axiom_adapter._HAS_SEMANTICA = original


# ---------------------------------------------------------------------------
# Provenance adapter tests
# ---------------------------------------------------------------------------

class TestProvenanceAdapter:
    """Test SemanticaProvenanceAdapter (dual-write provenance manager)."""

    def test_track_entity_stores_in_maris(self):
        from maris.semantica_bridge.provenance_adapter import SemanticaProvenanceAdapter

        adapter = SemanticaProvenanceAdapter()
        entity = adapter.track_entity("e1", entity_type="MPA", attributes={"name": "Cabo Pulmo"})

        assert entity.entity_id == "e1"
        assert entity.entity_type == "MPA"

        # Verify in MARIS storage
        stored = adapter.get_entity("e1")
        assert stored is not None
        assert stored["attributes"]["name"] == "Cabo Pulmo"

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_track_entity_mirrors_to_semantica(self):
        from maris.semantica_bridge.provenance_adapter import SemanticaProvenanceAdapter

        adapter = SemanticaProvenanceAdapter()
        adapter.track_entity("e1", entity_type="MPA", attributes={"doi": "10.1/test"})

        # Verify in Semantica backend
        sem_entry = adapter.semantica_manager.storage.retrieve("e1")
        assert sem_entry is not None
        assert sem_entry.entity_id == "e1"

    def test_record_activity_stores_in_maris(self):
        from maris.semantica_bridge.provenance_adapter import SemanticaProvenanceAdapter

        adapter = SemanticaProvenanceAdapter()
        activity = adapter.record_activity(
            activity_type="extraction",
            used=["doc1"],
            generated=["e1"],
        )
        assert activity.activity_type == "extraction"

        stored = adapter.get_activity(activity.activity_id)
        assert stored is not None

    def test_get_lineage_returns_maris_lineage(self):
        from maris.semantica_bridge.provenance_adapter import SemanticaProvenanceAdapter

        adapter = SemanticaProvenanceAdapter()
        adapter.track_entity("doc1", entity_type="Document")
        adapter.track_entity("e1", entity_type="MPA", derived_from=["doc1"])

        lineage = adapter.get_lineage("e1")
        assert len(lineage) == 2

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_get_semantica_lineage(self):
        from maris.semantica_bridge.provenance_adapter import SemanticaProvenanceAdapter

        adapter = SemanticaProvenanceAdapter()
        adapter.track_entity("e1", entity_type="MPA", attributes={"doi": "10.1/test"})

        sem_lineage = adapter.get_semantica_lineage("e1")
        assert isinstance(sem_lineage, dict)
        assert sem_lineage.get("entity_id") == "e1"

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_get_semantica_statistics(self):
        from maris.semantica_bridge.provenance_adapter import SemanticaProvenanceAdapter

        adapter = SemanticaProvenanceAdapter()
        adapter.track_entity("e1", entity_type="MPA")
        adapter.track_entity("e2", entity_type="Species")

        stats = adapter.get_semantica_statistics()
        assert stats["total_entries"] >= 2

    def test_summary(self):
        from maris.semantica_bridge.provenance_adapter import SemanticaProvenanceAdapter

        adapter = SemanticaProvenanceAdapter()
        adapter.track_entity("e1", entity_type="MPA")
        summary = adapter.summary()
        assert summary["entities"] == 1

    def test_register_agent(self):
        from maris.semantica_bridge.provenance_adapter import SemanticaProvenanceAdapter
        from maris.provenance.core import ProvenanceAgent

        adapter = SemanticaProvenanceAdapter()
        adapter.register_agent(ProvenanceAgent(
            agent_id="test:agent",
            agent_type="SoftwareAgent",
            name="Test Agent",
        ))
        agent = adapter.get_agent("test:agent")
        assert agent is not None
        assert agent["name"] == "Test Agent"

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_sqlite_persistence(self):
        from maris.semantica_bridge.provenance_adapter import SemanticaProvenanceAdapter

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            adapter = SemanticaProvenanceAdapter(db_path=db_path)
            adapter.track_entity("e1", entity_type="MPA", attributes={"doi": "10.1/a"})

            # Verify persisted in SQLite
            sem = adapter.semantica_manager
            entry = sem.storage.retrieve("e1")
            assert entry is not None
        finally:
            os.unlink(db_path)


# ---------------------------------------------------------------------------
# Integrity adapter tests
# ---------------------------------------------------------------------------

class TestIntegrityAdapter:
    """Test SemanticaIntegrityVerifier."""

    def test_compute_checksum_produces_hex_string(self):
        from maris.semantica_bridge.integrity_adapter import SemanticaIntegrityVerifier

        checksum = SemanticaIntegrityVerifier.compute_checksum({"key": "value"})
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA-256 hex

    def test_verify_correct_checksum(self):
        from maris.semantica_bridge.integrity_adapter import SemanticaIntegrityVerifier

        data = {"name": "Cabo Pulmo", "esv": 29.27}
        checksum = SemanticaIntegrityVerifier.compute_checksum(data)
        assert SemanticaIntegrityVerifier.verify(data, checksum) is True

    def test_verify_incorrect_checksum(self):
        from maris.semantica_bridge.integrity_adapter import SemanticaIntegrityVerifier

        data = {"name": "Cabo Pulmo", "esv": 29.27}
        assert SemanticaIntegrityVerifier.verify(data, "wrong_checksum") is False

    def test_compute_checksum_deterministic(self):
        from maris.semantica_bridge.integrity_adapter import SemanticaIntegrityVerifier

        data = {"b": 2, "a": 1}  # Different insertion order
        cs1 = SemanticaIntegrityVerifier.compute_checksum(data)
        cs2 = SemanticaIntegrityVerifier.compute_checksum({"a": 1, "b": 2})
        assert cs1 == cs2

    def test_compute_checksum_bytes(self):
        from maris.semantica_bridge.integrity_adapter import SemanticaIntegrityVerifier

        cs = SemanticaIntegrityVerifier.compute_checksum_bytes(b"hello world")
        assert isinstance(cs, str)
        assert len(cs) == 64

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_compute_entry_checksum(self):
        from maris.semantica_bridge.integrity_adapter import SemanticaIntegrityVerifier
        from semantica.provenance.schemas import ProvenanceEntry

        entry = ProvenanceEntry(
            entity_id="e1",
            entity_type="test",
            activity_id="test_activity",
        )
        cs = SemanticaIntegrityVerifier.compute_entry_checksum(entry)
        assert isinstance(cs, str)
        assert len(cs) == 64

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_verify_entry(self):
        from maris.semantica_bridge.integrity_adapter import SemanticaIntegrityVerifier
        from semantica.provenance.schemas import ProvenanceEntry
        from semantica.provenance.integrity import compute_checksum

        entry = ProvenanceEntry(
            entity_id="e1",
            entity_type="test",
            activity_id="test_activity",
        )
        entry.checksum = compute_checksum(entry)
        assert SemanticaIntegrityVerifier.verify_entry(entry) is True


# ---------------------------------------------------------------------------
# SemanticaBackedManager (unified) tests
# ---------------------------------------------------------------------------

class TestSemanticaBackedManager:
    """Test the full SemanticaBackedManager."""

    def test_init_without_axioms(self):
        from maris.semantica_bridge.manager import SemanticaBackedManager

        mgr = SemanticaBackedManager()
        summary = mgr.summary()
        assert summary["entities"] == 0
        assert summary["axioms_loaded"] == 0
        assert isinstance(summary["semantica_available"], bool)

    def test_init_with_axiom_templates(self):
        from maris.semantica_bridge.manager import SemanticaBackedManager

        templates = Path(__file__).parent.parent / "schemas" / "bridge_axiom_templates.json"
        evidence = Path(__file__).parent.parent / "data" / "semantica_export" / "bridge_axioms.json"

        if templates.exists():
            mgr = SemanticaBackedManager(
                templates_path=str(templates),
                evidence_path=str(evidence) if evidence.exists() else None,
            )
            assert mgr.registry.count() == 35
        else:
            pytest.skip("Axiom templates not found")

    def test_track_extraction(self):
        from maris.semantica_bridge.manager import SemanticaBackedManager

        mgr = SemanticaBackedManager()
        entity = mgr.track_extraction(
            entity_id="cabo_pulmo_esv",
            entity_type="EcosystemService",
            source_doi="10.1371/journal.pone.0023601",
            attributes={"value_usd": 29270000},
        )

        assert entity["entity_id"] == "cabo_pulmo_esv"
        assert entity["entity_type"] == "EcosystemService"

        # Verify lineage includes the document
        lineage = mgr.get_lineage("cabo_pulmo_esv")
        assert len(lineage) == 2  # entity + source document
        types = [r["entity_type"] for r in lineage]
        assert "EcosystemService" in types
        assert "Document" in types

    def test_track_axiom_application(self):
        from maris.semantica_bridge.manager import SemanticaBackedManager

        templates = Path(__file__).parent.parent / "schemas" / "bridge_axiom_templates.json"
        evidence = Path(__file__).parent.parent / "data" / "semantica_export" / "bridge_axioms.json"

        if not templates.exists():
            pytest.skip("Axiom templates not found")

        mgr = SemanticaBackedManager(
            templates_path=str(templates),
            evidence_path=str(evidence) if evidence.exists() else None,
        )

        # Track input entity first
        mgr.provenance.track_entity("biomass_input", entity_type="Observation")

        result = mgr.track_axiom_application(
            axiom_id="BA-002",
            input_entity_id="biomass_input",
            output_entity_id="biomass_output",
            input_value=1.0,
            output_value=4.63,
        )
        assert result is not None
        assert result["attributes"]["axiom_id"] == "BA-002"

    def test_track_axiom_application_unknown_id(self):
        from maris.semantica_bridge.manager import SemanticaBackedManager

        mgr = SemanticaBackedManager()
        result = mgr.track_axiom_application("BA-999", "in", "out", 1.0, 1.0)
        assert result is None

    def test_get_certificate(self):
        from maris.semantica_bridge.manager import SemanticaBackedManager

        mgr = SemanticaBackedManager()
        mgr.track_extraction("e1", "MPA", "10.1/test", {"name": "Test"})

        cert = mgr.get_certificate("e1")
        assert cert["entity_id"] == "e1"
        assert "checksum" in cert

    def test_get_certificate_markdown(self):
        from maris.semantica_bridge.manager import SemanticaBackedManager

        mgr = SemanticaBackedManager()
        mgr.track_extraction("e1", "MPA", "10.1/test", {"doi": "10.1/test"})

        md = mgr.get_certificate_markdown("e1")
        assert "# Provenance Certificate" in md
        assert "e1" in md

    def test_get_certificate_missing_entity(self):
        from maris.semantica_bridge.manager import SemanticaBackedManager

        mgr = SemanticaBackedManager()
        cert = mgr.get_certificate("nonexistent")
        assert "error" in cert

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_get_semantica_lineage(self):
        from maris.semantica_bridge.manager import SemanticaBackedManager

        mgr = SemanticaBackedManager()
        mgr.track_extraction("e1", "MPA", "10.1/test")

        sem_lineage = mgr.get_semantica_lineage("e1")
        assert isinstance(sem_lineage, dict)

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_sqlite_backed_manager(self):
        from maris.semantica_bridge.manager import SemanticaBackedManager

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            mgr = SemanticaBackedManager(db_path=db_path)
            mgr.track_extraction("e1", "MPA", "10.1/a")
            mgr.track_extraction("e2", "Species", "10.1/b")

            summary = mgr.summary()
            assert summary["semantica_entries"] >= 2
        finally:
            os.unlink(db_path)

    @pytest.mark.skipif(not _HAS_SEMANTICA, reason="semantica not installed")
    def test_execute_chain(self):
        from maris.semantica_bridge.manager import SemanticaBackedManager

        templates = Path(__file__).parent.parent / "schemas" / "bridge_axiom_templates.json"
        evidence = Path(__file__).parent.parent / "data" / "semantica_export" / "bridge_axioms.json"

        if not templates.exists():
            pytest.skip("Axiom templates not found")

        mgr = SemanticaBackedManager(
            templates_path=str(templates),
            evidence_path=str(evidence) if evidence.exists() else None,
        )

        # Use two real axioms from the registry
        all_axioms = mgr.registry.get_all()
        if len(all_axioms) < 2:
            pytest.skip("Need at least 2 axioms")

        ids = [all_axioms[0].axiom_id, all_axioms[1].axiom_id]
        result = mgr.execute_chain(
            axiom_ids=ids,
            input_data={"entity_id": "test_input", "value": 100.0, "source": "test"},
        )
        assert result["axiom_count"] == 2
        assert len(result["source_dois"]) >= 0

    def test_execute_chain_unknown_axiom_raises(self):
        from maris.semantica_bridge.manager import SemanticaBackedManager

        mgr = SemanticaBackedManager()
        with pytest.raises(ValueError, match="not found"):
            mgr.execute_chain(["BA-999"], {"value": 10.0})

    def test_semantica_available_property(self):
        from maris.semantica_bridge.manager import SemanticaBackedManager

        mgr = SemanticaBackedManager()
        assert mgr.semantica_available == _HAS_SEMANTICA
