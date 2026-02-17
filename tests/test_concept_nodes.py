"""Tests for Phase II concept nodes, expanded axioms, and population pipeline."""

import json
from pathlib import Path

import pytest


_PROJECT_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# concepts.json structure tests
# ---------------------------------------------------------------------------

class TestConceptsJson:
    """Validate concepts.json structure and content."""

    @pytest.fixture(autouse=True)
    def _load_concepts(self):
        path = _PROJECT_ROOT / "data" / "semantica_export" / "concepts.json"
        assert path.exists(), f"concepts.json not found at {path}"
        with open(path) as f:
            self.data = json.load(f)
        self.concepts = self.data.get("concepts", [])

    def test_has_15_concepts(self):
        assert len(self.concepts) == 15

    def test_has_version(self):
        assert "version" in self.data

    def test_each_concept_has_concept_id(self):
        for c in self.concepts:
            assert "concept_id" in c, f"Missing concept_id in concept: {c.get('name')}"
            assert c["concept_id"].startswith("BC-")

    def test_each_concept_has_name(self):
        for c in self.concepts:
            assert "name" in c and c["name"], f"Missing name for {c.get('concept_id')}"

    def test_each_concept_has_description(self):
        for c in self.concepts:
            assert "description" in c and c["description"], (
                f"Missing description for {c.get('concept_id')}"
            )

    def test_each_concept_has_domain(self):
        for c in self.concepts:
            assert "domain" in c and c["domain"], (
                f"Missing domain for {c.get('concept_id')}"
            )

    def test_each_concept_has_involved_axiom_ids(self):
        for c in self.concepts:
            assert "involved_axiom_ids" in c, (
                f"Missing involved_axiom_ids for {c.get('concept_id')}"
            )
            assert isinstance(c["involved_axiom_ids"], list)

    def test_concept_ids_are_unique(self):
        ids = [c["concept_id"] for c in self.concepts]
        assert len(ids) == len(set(ids)), "Duplicate concept IDs found"

    def test_expected_concepts_present(self):
        names = {c["name"] for c in self.concepts}
        expected = {
            "Blue Carbon Sequestration",
            "Coastal Protection Services",
            "Marine Tourism Economics",
            "Carbon Credit Markets",
            "Reef Insurance Mechanisms",
            "TNFD Disclosure Framework",
        }
        for name in expected:
            assert name in names, f"Expected concept '{name}' not found"


# ---------------------------------------------------------------------------
# bridge_axiom_templates.json expansion tests
# ---------------------------------------------------------------------------

class TestExpandedAxioms:
    """Validate bridge axiom expansion from 16 to ~35."""

    @pytest.fixture(autouse=True)
    def _load_axioms(self):
        path = _PROJECT_ROOT / "schemas" / "bridge_axiom_templates.json"
        assert path.exists(), f"bridge_axiom_templates.json not found at {path}"
        with open(path) as f:
            self.data = json.load(f)
        self.axioms = self.data.get("axioms", [])

    def test_has_35_axioms(self):
        assert len(self.axioms) == 35

    def test_axiom_ids_sequential(self):
        ids = [a["axiom_id"] for a in self.axioms]
        for i, aid in enumerate(ids, start=1):
            assert aid == f"BA-{i:03d}", f"Expected BA-{i:03d}, got {aid}"

    def test_each_axiom_has_required_fields(self):
        for a in self.axioms:
            assert "axiom_id" in a, "Missing axiom_id"
            assert "name" in a, f"Missing name for {a.get('axiom_id')}"
            assert "category" in a, f"Missing category for {a.get('axiom_id')}"
            assert "description" in a, f"Missing description for {a.get('axiom_id')}"
            assert "sources" in a, f"Missing sources for {a.get('axiom_id')}"

    def test_original_16_axioms_preserved(self):
        ids = {a["axiom_id"] for a in self.axioms}
        for i in range(1, 17):
            assert f"BA-{i:03d}" in ids, f"Original axiom BA-{i:03d} missing"

    def test_new_axioms_ba017_through_ba035(self):
        ids = {a["axiom_id"] for a in self.axioms}
        for i in range(17, 36):
            assert f"BA-{i:03d}" in ids, f"New axiom BA-{i:03d} missing"

    def test_version_is_2_0(self):
        assert self.data.get("version") == "2.0"


# ---------------------------------------------------------------------------
# Cross-reference: concept axiom IDs vs axiom templates
# ---------------------------------------------------------------------------

class TestConceptAxiomCrossReference:
    """Validate that all axiom IDs referenced in concepts exist in templates."""

    @pytest.fixture(autouse=True)
    def _load_both(self):
        concepts_path = _PROJECT_ROOT / "data" / "semantica_export" / "concepts.json"
        axioms_path = _PROJECT_ROOT / "schemas" / "bridge_axiom_templates.json"
        with open(concepts_path) as f:
            self.concepts = json.load(f).get("concepts", [])
        with open(axioms_path) as f:
            self.axiom_ids = {
                a["axiom_id"] for a in json.load(f).get("axioms", [])
            }

    def test_all_concept_axiom_ids_valid(self):
        for concept in self.concepts:
            for aid in concept.get("involved_axiom_ids", []):
                assert aid in self.axiom_ids, (
                    f"Concept {concept['concept_id']} references {aid} "
                    f"which is not in bridge_axiom_templates.json"
                )

    def test_most_concepts_have_axioms(self):
        """Most concepts should reference at least one axiom (TNFD is an exception)."""
        with_axioms = sum(
            1 for c in self.concepts if c.get("involved_axiom_ids")
        )
        assert with_axioms >= 13, (
            f"Only {with_axioms}/15 concepts have axiom references"
        )


# ---------------------------------------------------------------------------
# Population script has concept stages
# ---------------------------------------------------------------------------

class TestPopulationScriptConcepts:
    """Validate that populate_neo4j_v4.py includes concept population."""

    @pytest.fixture(autouse=True)
    def _load_script(self):
        path = _PROJECT_ROOT / "scripts" / "populate_neo4j_v4.py"
        assert path.exists()
        self.source = path.read_text()

    def test_has_populate_concepts_function(self):
        assert "_populate_concepts" in self.source

    def test_mentions_concept_node_label(self):
        assert "Concept" in self.source

    def test_mentions_involves_axiom_relationship(self):
        assert "INVOLVES_AXIOM" in self.source

    def test_mentions_concepts_json(self):
        assert "concepts.json" in self.source

    def test_concept_step_in_pipeline(self):
        assert "concept" in self.source.lower()


# ---------------------------------------------------------------------------
# Schema includes Concept constraint and indexes
# ---------------------------------------------------------------------------

class TestSchemaConceptSupport:
    """Validate Neo4j schema supports Concept nodes."""

    @pytest.fixture(autouse=True)
    def _load_schema(self):
        path = _PROJECT_ROOT / "maris" / "graph" / "schema.py"
        self.source = path.read_text()

    def test_concept_id_constraint(self):
        assert "concept_id" in self.source
        assert "Concept" in self.source

    def test_concept_name_index(self):
        assert "concept_name" in self.source

    def test_concept_domain_index(self):
        assert "concept_domain" in self.source
