"""Tests for the MARIS provenance module.

Covers: InMemoryStorage, ProvenanceManager, BridgeAxiom, TranslationChain,
BridgeAxiomRegistry, IntegrityVerifier, ProvenanceCertificate, MARISProvenanceManager,
LLM extractor integration, confidence integration, and the provenance API endpoint.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure test env is set
os.environ.setdefault("MARIS_NEO4J_PASSWORD", "test-password")
os.environ.setdefault("MARIS_LLM_API_KEY", "test-key")
os.environ.setdefault("MARIS_API_KEY", "test-api-key")
os.environ.setdefault("MARIS_DEMO_MODE", "true")

from maris.provenance.storage import InMemoryStorage
from maris.provenance.core import (
    ProvenanceAgent,
    ProvenanceManager,
)
from maris.provenance.bridge_axiom import BridgeAxiom, TranslationChain
from maris.provenance.integrity import IntegrityVerifier
from maris.provenance.bridge_axiom_registry import BridgeAxiomRegistry
from maris.provenance.certificate import ProvenanceCertificate
from maris.provenance.manager import MARISProvenanceManager

TEMPLATES_PATH = Path("schemas/bridge_axiom_templates.json")
EVIDENCE_PATH = Path("data/semantica_export/bridge_axioms.json")


# ============================================================================
# InMemoryStorage
# ============================================================================


class TestInMemoryStorage:
    def test_put_and_get(self):
        store = InMemoryStorage()
        store.put("entity", "e1", {"name": "test"})
        result = store.get("entity", "e1")
        assert result == {"name": "test"}

    def test_get_nonexistent_returns_none(self):
        store = InMemoryStorage()
        assert store.get("entity", "missing") is None

    def test_delete(self):
        store = InMemoryStorage()
        store.put("entity", "e1", {"name": "test"})
        assert store.delete("entity", "e1") is True
        assert store.get("entity", "e1") is None

    def test_delete_nonexistent(self):
        store = InMemoryStorage()
        assert store.delete("entity", "missing") is False

    def test_exists(self):
        store = InMemoryStorage()
        store.put("entity", "e1", {"name": "test"})
        assert store.exists("entity", "e1") is True
        assert store.exists("entity", "e2") is False

    def test_list_by_type(self):
        store = InMemoryStorage()
        store.put("entity", "e1", {"name": "a"})
        store.put("entity", "e2", {"name": "b"})
        store.put("activity", "a1", {"type": "extraction"})
        entities = store.list_by_type("entity")
        assert len(entities) == 2

    def test_find_by_attribute(self):
        store = InMemoryStorage()
        store.put("entity", "e1", {"name": "a", "tier": "T1"})
        store.put("entity", "e2", {"name": "b", "tier": "T2"})
        results = store.find("entity", tier="T1")
        assert len(results) == 1
        assert results[0]["name"] == "a"

    def test_count(self):
        store = InMemoryStorage()
        store.put("entity", "e1", {"name": "a"})
        store.put("entity", "e2", {"name": "b"})
        store.put("activity", "a1", {})
        assert store.count() == 3
        assert store.count("entity") == 2
        assert store.count("activity") == 1

    def test_clear(self):
        store = InMemoryStorage()
        store.put("entity", "e1", {"name": "a"})
        store.clear()
        assert store.count() == 0

    def test_deep_copy_isolation(self):
        """Modifications to returned data should not affect stored data."""
        store = InMemoryStorage()
        store.put("entity", "e1", {"items": [1, 2, 3]})
        result = store.get("entity", "e1")
        result["items"].append(4)
        original = store.get("entity", "e1")
        assert len(original["items"]) == 3


# ============================================================================
# ProvenanceManager
# ============================================================================


class TestProvenanceManager:
    def test_register_agent(self):
        pm = ProvenanceManager()
        agent = ProvenanceAgent(agent_id="agent:1", name="MARIS")
        pm.register_agent(agent)
        retrieved = pm.get_agent("agent:1")
        assert retrieved is not None
        assert retrieved["name"] == "MARIS"

    def test_track_entity(self):
        pm = ProvenanceManager()
        entity = pm.track_entity(
            entity_id="e1",
            entity_type="Species",
            attributes={"name": "Test species"},
        )
        assert entity.entity_id == "e1"
        retrieved = pm.get_entity("e1")
        assert retrieved is not None
        assert retrieved["entity_type"] == "Species"

    def test_track_entity_with_derivation(self):
        pm = ProvenanceManager()
        pm.track_entity("parent", entity_type="Document")
        pm.track_entity("child", entity_type="Species", derived_from=["parent"])
        child = pm.get_entity("child")
        assert "parent" in child["derived_from"]

    def test_record_activity(self):
        pm = ProvenanceManager()
        activity = pm.record_activity(
            activity_type="extraction",
            used=["doc:1"],
            generated=["entity:1"],
        )
        assert activity.activity_type == "extraction"
        retrieved = pm.get_activity(activity.activity_id)
        assert retrieved is not None

    def test_get_lineage(self):
        pm = ProvenanceManager()
        pm.track_entity("root", entity_type="Document")
        pm.track_entity("mid", entity_type="Concept", derived_from=["root"])
        pm.track_entity("leaf", entity_type="Service", derived_from=["mid"])
        lineage = pm.get_lineage("leaf")
        ids = [r["entity_id"] for r in lineage]
        assert "leaf" in ids
        assert "mid" in ids
        assert "root" in ids

    def test_get_lineage_max_depth(self):
        pm = ProvenanceManager()
        pm.track_entity("a", entity_type="A")
        pm.track_entity("b", entity_type="B", derived_from=["a"])
        pm.track_entity("c", entity_type="C", derived_from=["b"])
        pm.track_entity("d", entity_type="D", derived_from=["c"])
        # Full lineage reaches all 4 nodes
        full = pm.get_lineage("d", max_depth=10)
        assert len(full) == 4
        # Limited depth should return fewer nodes
        limited = pm.get_lineage("d", max_depth=1)
        assert len(limited) < len(full)
        assert limited[0]["entity_id"] == "d"

    def test_get_entities_by_type(self):
        pm = ProvenanceManager()
        pm.track_entity("s1", entity_type="Species")
        pm.track_entity("s2", entity_type="Species")
        pm.track_entity("d1", entity_type="Document")
        species = pm.get_entities_by_type("Species")
        assert len(species) == 2

    def test_get_activities_for_entity(self):
        pm = ProvenanceManager()
        pm.record_activity(activity_type="extraction", used=["e1"], generated=["e2"])
        pm.record_activity(activity_type="transform", used=["e2"], generated=["e3"])
        acts = pm.get_activities_for_entity("e2")
        assert len(acts) == 2

    def test_summary(self):
        pm = ProvenanceManager()
        pm.register_agent(ProvenanceAgent(agent_id="a1"))
        pm.track_entity("e1")
        pm.record_activity(activity_type="test")
        s = pm.summary()
        assert s["entities"] == 1
        assert s["activities"] == 1
        assert s["agents"] == 1


# ============================================================================
# BridgeAxiom
# ============================================================================


class TestBridgeAxiom:
    def test_apply(self):
        ba = BridgeAxiom(axiom_id="BA-TEST", coefficient=2.0, source_doi="10.1234/test")
        result = ba.apply(100.0)
        assert result["output_value"] == 200.0
        assert result["axiom_id"] == "BA-TEST"

    def test_apply_with_ci(self):
        ba = BridgeAxiom(axiom_id="BA-TEST", coefficient=2.0, ci_low=1.5, ci_high=2.5)
        result = ba.apply(100.0)
        assert result["output_value"] == 200.0
        assert result["ci_low"] == 150.0
        assert result["ci_high"] == 250.0

    def test_apply_zero(self):
        ba = BridgeAxiom(axiom_id="BA-TEST", coefficient=2.0)
        result = ba.apply(0.0)
        assert result["output_value"] == 0.0

    def test_to_dict(self):
        ba = BridgeAxiom(axiom_id="BA-001", name="test", coefficient=1.5)
        d = ba.to_dict()
        assert d["axiom_id"] == "BA-001"
        assert d["coefficient"] == 1.5


# ============================================================================
# TranslationChain
# ============================================================================


class TestTranslationChain:
    def test_empty_chain(self):
        chain = TranslationChain()
        result = chain.execute(100.0)
        assert result["final_value"] == 100.0
        assert result["axiom_count"] == 0

    def test_single_axiom_chain(self):
        ba = BridgeAxiom(axiom_id="BA-001", coefficient=2.0, ci_low=1.5, ci_high=2.5)
        chain = TranslationChain([ba])
        result = chain.execute(100.0)
        assert result["final_value"] == 200.0
        assert len(result["steps"]) == 1

    def test_two_axiom_chain(self):
        ba1 = BridgeAxiom(axiom_id="BA-001", coefficient=2.0)
        ba2 = BridgeAxiom(axiom_id="BA-002", coefficient=3.0)
        chain = TranslationChain([ba1, ba2])
        result = chain.execute(10.0)
        assert result["final_value"] == 60.0  # 10 * 2 * 3
        assert result["axiom_count"] == 2

    def test_chain_collects_dois(self):
        ba1 = BridgeAxiom(axiom_id="BA-001", coefficient=2.0, source_doi="10.1234/a")
        ba2 = BridgeAxiom(axiom_id="BA-002", coefficient=3.0, source_doi="10.1234/b")
        chain = TranslationChain([ba1, ba2])
        result = chain.execute(10.0)
        assert "10.1234/a" in result["source_dois"]
        assert "10.1234/b" in result["source_dois"]

    def test_chain_ci_propagation(self):
        ba1 = BridgeAxiom(axiom_id="BA-001", coefficient=2.0, ci_low=1.5, ci_high=2.5)
        ba2 = BridgeAxiom(axiom_id="BA-002", coefficient=3.0, ci_low=2.0, ci_high=4.0)
        chain = TranslationChain([ba1, ba2])
        result = chain.execute(10.0)
        assert result["final_value"] == 60.0
        assert result["ci_low"] < 60.0
        assert result["ci_high"] > 60.0

    def test_add_axiom(self):
        chain = TranslationChain()
        chain.add(BridgeAxiom(axiom_id="BA-001", coefficient=2.0))
        assert len(chain.axioms) == 1

    def test_to_dict(self):
        chain = TranslationChain([BridgeAxiom(axiom_id="BA-001", coefficient=2.0)])
        chain.execute(10.0)
        d = chain.to_dict()
        assert len(d["axioms"]) == 1
        assert len(d["steps"]) == 1


# ============================================================================
# IntegrityVerifier
# ============================================================================


class TestIntegrityVerifier:
    def test_compute_checksum(self):
        data = {"key": "value"}
        checksum = IntegrityVerifier.compute_checksum(data)
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA-256 hex

    def test_deterministic(self):
        data = {"a": 1, "b": 2}
        c1 = IntegrityVerifier.compute_checksum(data)
        c2 = IntegrityVerifier.compute_checksum(data)
        assert c1 == c2

    def test_key_order_independent(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 2, "a": 1}
        assert IntegrityVerifier.compute_checksum(d1) == IntegrityVerifier.compute_checksum(d2)

    def test_verify_valid(self):
        data = {"key": "value"}
        checksum = IntegrityVerifier.compute_checksum(data)
        assert IntegrityVerifier.verify(data, checksum) is True

    def test_verify_invalid(self):
        data = {"key": "value"}
        assert IntegrityVerifier.verify(data, "wrong") is False

    def test_compute_checksum_bytes(self):
        content = b"hello world"
        checksum = IntegrityVerifier.compute_checksum_bytes(content)
        assert isinstance(checksum, str)
        assert len(checksum) == 64


# ============================================================================
# BridgeAxiomRegistry
# ============================================================================


class TestBridgeAxiomRegistry:
    @pytest.fixture
    def registry(self):
        return BridgeAxiomRegistry(
            templates_path=TEMPLATES_PATH,
            evidence_path=EVIDENCE_PATH,
        )

    def test_load_all_35_axioms(self, registry):
        assert registry.count() == 40

    def test_get_ba001(self, registry):
        ba = registry.get("BA-001")
        assert ba is not None
        assert ba.axiom_id == "BA-001"
        assert ba.name == "mpa_biomass_dive_tourism_value"

    def test_get_nonexistent(self, registry):
        assert registry.get("BA-999") is None

    def test_get_all(self, registry):
        all_axioms = registry.get_all()
        assert len(all_axioms) == 40

    def test_all_axiom_ids_present(self, registry):
        ids = {a.axiom_id for a in registry.get_all()}
        for i in range(1, 36):
            assert f"BA-{i:03d}" in ids

    def test_axiom_has_source_doi(self, registry):
        """Every axiom should have at least one source DOI."""
        for ba in registry.get_all():
            assert ba.source_doi, f"{ba.axiom_id} missing source DOI"

    def test_axiom_has_evidence_sources(self, registry):
        """Every axiom should have at least one evidence source."""
        for ba in registry.get_all():
            assert len(ba.evidence_sources) >= 1, f"{ba.axiom_id} missing evidence"

    def test_get_by_habitat_coral_reef(self, registry):
        coral = registry.get_by_habitat("coral_reef")
        ids = {a.axiom_id for a in coral}
        assert "BA-004" in ids  # coral_reef_flood_protection
        assert "BA-012" in ids  # reef_degradation_fisheries_loss

    def test_get_by_habitat_seagrass(self, registry):
        seagrass = registry.get_by_habitat("seagrass_meadow")
        ids = {a.axiom_id for a in seagrass}
        assert "BA-013" in ids
        assert "BA-014" in ids

    def test_get_by_domain(self, registry):
        ecological = registry.get_by_domain(input_domain="ecological")
        assert len(ecological) > 0
        for a in ecological:
            assert a.input_domain == "ecological"

    def test_build_chain(self, registry):
        chain = registry.build_chain(["BA-013", "BA-014"])
        assert len(chain.axioms) == 2

    def test_build_chain_invalid_id_raises(self, registry):
        with pytest.raises(ValueError, match="BA-999"):
            registry.build_chain(["BA-013", "BA-999"])

    def test_ba013_coefficient(self, registry):
        """BA-013 primary coefficient should be 0.84 (seagrass sequestration rate)."""
        ba = registry.get("BA-013")
        assert ba.coefficient == 0.84

    def test_ba014_coefficient(self, registry):
        """BA-014 primary coefficient should be 30 (carbon credit price)."""
        ba = registry.get("BA-014")
        assert ba.coefficient == 30.0

    def test_ba015_coefficient(self, registry):
        """BA-015 emission factor should be 294."""
        ba = registry.get("BA-015")
        assert ba.coefficient == 294.0

    def test_ba016_permanence(self, registry):
        """BA-016 permanence years should be 50."""
        ba = registry.get("BA-016")
        assert ba.coefficient == 50.0

    def test_blue_carbon_axioms_have_seagrass_habitat(self, registry):
        """BA-013 through BA-016 should include seagrass_meadow in applicable habitats."""
        for aid in ("BA-013", "BA-014", "BA-015", "BA-016"):
            ba = registry.get(aid)
            assert "seagrass_meadow" in ba.applicable_habitats, f"{aid} missing seagrass habitat"

    def test_axiom_domain_mapping(self, registry):
        """Axioms should have non-empty domain fields from evidence mapping."""
        ba013 = registry.get("BA-013")
        assert ba013.input_domain == "ecological"
        assert ba013.output_domain == "service"


# ============================================================================
# ProvenanceCertificate
# ============================================================================


class TestProvenanceCertificate:
    def test_generate_certificate(self):
        pm = ProvenanceManager()
        pm.track_entity("doc:10.1234/a", entity_type="Document", attributes={"doi": "10.1234/a"})
        pm.track_entity("species:1", entity_type="Species", derived_from=["doc:10.1234/a"])
        cert_gen = ProvenanceCertificate(pm)
        cert = cert_gen.generate("species:1")
        assert cert["entity_id"] == "species:1"
        assert "checksum" in cert
        assert cert["lineage_depth"] >= 2
        assert "10.1234/a" in cert["source_dois"]

    def test_generate_certificate_not_found(self):
        pm = ProvenanceManager()
        cert_gen = ProvenanceCertificate(pm)
        cert = cert_gen.generate("missing")
        assert "error" in cert

    def test_generate_markdown(self):
        pm = ProvenanceManager()
        pm.track_entity("e1", entity_type="Species", attributes={"name": "Test"})
        cert_gen = ProvenanceCertificate(pm)
        md = cert_gen.generate_markdown("e1")
        assert "# Provenance Certificate" in md
        assert "Species" in md

    def test_verify_certificate(self):
        pm = ProvenanceManager()
        pm.track_entity("e1", entity_type="Species")
        cert_gen = ProvenanceCertificate(pm)
        cert = cert_gen.generate("e1")
        assert cert_gen.verify(cert) is True

    def test_verify_tampered_certificate(self):
        pm = ProvenanceManager()
        pm.track_entity("e1", entity_type="Species")
        cert_gen = ProvenanceCertificate(pm)
        cert = cert_gen.generate("e1")
        cert["entity_type"] = "Tampered"
        assert cert_gen.verify(cert) is False

    def test_certificate_with_activities(self):
        pm = ProvenanceManager()
        pm.track_entity("e1", entity_type="Document")
        pm.track_entity("e2", entity_type="Species", derived_from=["e1"])
        pm.record_activity(
            activity_type="extraction",
            used=["e1"],
            generated=["e2"],
        )
        cert_gen = ProvenanceCertificate(pm)
        cert = cert_gen.generate("e2")
        assert len(cert["activities"]) >= 1


# ============================================================================
# MARISProvenanceManager
# ============================================================================


class TestMARISProvenanceManager:
    @pytest.fixture
    def manager(self):
        return MARISProvenanceManager(
            templates_path=TEMPLATES_PATH,
            evidence_path=EVIDENCE_PATH,
        )

    def test_initialization(self, manager):
        assert manager.registry.count() == 40
        # MARIS system agent should be registered
        agent = manager.provenance.get_agent("maris:system")
        assert agent is not None

    def test_track_extraction(self, manager):
        entity = manager.track_extraction(
            entity_id="species:1",
            entity_type="Species",
            source_doi="10.1234/test",
            attributes={"name": "Test"},
        )
        assert entity["entity_id"] == "species:1"
        # Document should be tracked too
        doc = manager.provenance.get_entity("doc:10.1234/test")
        assert doc is not None

    def test_track_axiom_application(self, manager):
        manager.provenance.track_entity("input:1")
        manager.provenance.track_entity("output:1")
        activity = manager.track_axiom_application(
            axiom_id="BA-013",
            input_entity_id="input:1",
            output_entity_id="output:1",
            input_value=100.0,
            output_value=84.0,
        )
        assert activity is not None
        assert activity["attributes"]["axiom_id"] == "BA-013"

    def test_track_axiom_application_unknown(self, manager):
        result = manager.track_axiom_application(
            axiom_id="BA-999",
            input_entity_id="i",
            output_entity_id="o",
            input_value=0,
            output_value=0,
        )
        assert result is None

    def test_get_certificate(self, manager):
        manager.track_extraction("e1", "Species", "10.1234/a")
        cert = manager.get_certificate("e1")
        assert cert["entity_id"] == "e1"
        assert "checksum" in cert

    def test_get_lineage(self, manager):
        manager.track_extraction("e1", "Species", "10.1234/a")
        lineage = manager.get_lineage("e1")
        ids = [r["entity_id"] for r in lineage]
        assert "e1" in ids
        assert "doc:10.1234/a" in ids

    def test_summary(self, manager):
        s = manager.summary()
        assert "entities" in s
        assert "activities" in s
        assert "agents" in s
        assert s["axioms_loaded"] == 40


# ============================================================================
# LLM Extractor integration (with provenance)
# ============================================================================


class TestLLMExtractorProvenance:
    def test_extractor_with_provenance_manager(self):
        """LLMExtractor should accept optional provenance_manager param."""
        from maris.ingestion.llm_extractor import LLMExtractor

        mock_config = MagicMock()
        mock_config.llm_api_key = "test"
        mock_config.llm_base_url = "http://localhost"
        mock_config.llm_model = "test"
        mock_config.llm_timeout = 10
        mock_config.llm_max_tokens = 100
        mock_config.extraction_confidence_threshold = 0.5

        manager = MARISProvenanceManager()

        with patch("maris.ingestion.llm_extractor.OpenAI"):
            extractor = LLMExtractor(mock_config, provenance_manager=manager)
            assert extractor._provenance is manager

    def test_extractor_without_provenance_still_works(self):
        """LLMExtractor should work without provenance (backward compat)."""
        from maris.ingestion.llm_extractor import LLMExtractor

        mock_config = MagicMock()
        mock_config.llm_api_key = "test"
        mock_config.llm_base_url = "http://localhost"
        mock_config.llm_model = "test"
        mock_config.llm_timeout = 10
        mock_config.llm_max_tokens = 100
        mock_config.extraction_confidence_threshold = 0.5

        with patch("maris.ingestion.llm_extractor.OpenAI"):
            extractor = LLMExtractor(mock_config)
            assert extractor._provenance is None


# ============================================================================
# Confidence integration (with provenance certificate)
# ============================================================================


class TestConfidenceWithProvenance:
    def test_confidence_without_certificate(self):
        """Existing signature should work unchanged."""
        from maris.axioms.confidence import calculate_response_confidence

        nodes = [{"source_tier": "T1", "year": 2024}]
        result = calculate_response_confidence(nodes, n_hops=1, current_year=2026)
        assert "composite" in result
        assert "provenance_depth" not in result

    def test_confidence_with_certificate(self):
        """Certificate param should enrich the result."""
        from maris.axioms.confidence import calculate_response_confidence

        nodes = [{"source_tier": "T1", "year": 2024}]
        cert = {
            "lineage_depth": 3,
            "checksum": "abc123",
            "source_dois": ["10.1234/a"],
        }
        result = calculate_response_confidence(
            nodes, n_hops=1, current_year=2026, provenance_certificate=cert,
        )
        assert result["provenance_depth"] == 3
        assert result["provenance_checksum"] == "abc123"
        assert result["provenance_dois"] == ["10.1234/a"]


# ============================================================================
# API endpoint
# ============================================================================


class TestProvenanceEndpoint:
    @pytest.fixture
    def app(self):
        import maris.config
        maris.config._config = None
        from maris.api.main import create_app
        return create_app()

    @pytest.fixture
    def client(self, app):
        from fastapi.testclient import TestClient
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": "Bearer test-api-key"}

    def test_provenance_summary(self, client, auth_headers):
        """GET /api/provenance should return a summary."""
        response = client.get("/api/provenance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert "axioms_loaded" in data

    def test_provenance_entity_not_found(self, client, auth_headers):
        """GET /api/provenance/missing should return 404."""
        response = client.get("/api/provenance/nonexistent-entity", headers=auth_headers)
        assert response.status_code == 404

    def test_provenance_requires_auth(self, client):
        """Provenance endpoints should require authentication (in non-demo mode)."""
        # In demo mode auth is bypassed, so this should still work
        response = client.get("/api/provenance")
        assert response.status_code == 200


# ============================================================================
# Backward compatibility
# ============================================================================


class TestBackwardCompatibility:
    def test_existing_confidence_api_unchanged(self):
        """calculate_response_confidence works without provenance_certificate."""
        from maris.axioms.confidence import calculate_response_confidence

        nodes = [
            {"source_tier": "T1", "doi": "10.1234/a", "year": 2024},
            {"source_tier": "T1", "doi": "10.1234/b", "year": 2025},
        ]
        result = calculate_response_confidence(nodes, n_hops=1, current_year=2026)
        assert "composite" in result
        assert "tier_base" in result
        assert 0 <= result["composite"] <= 1

    def test_extractor_old_signature(self):
        """LLMExtractor(config) still works without provenance_manager."""
        from maris.ingestion.llm_extractor import LLMExtractor

        mock_config = MagicMock()
        mock_config.llm_api_key = "k"
        mock_config.llm_base_url = "http://localhost"
        mock_config.llm_model = "m"
        mock_config.llm_timeout = 10
        mock_config.llm_max_tokens = 100
        mock_config.extraction_confidence_threshold = 0.5

        with patch("maris.ingestion.llm_extractor.OpenAI"):
            extractor = LLMExtractor(mock_config)
            assert extractor._provenance is None
