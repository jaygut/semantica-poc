"""Tests for Cypher template safety and correctness."""

import re

import pytest

from maris.query.cypher_templates import TEMPLATES, get_template, templates_for_category


class TestTemplateExistence:
    def test_all_categories_have_templates(self):
        expected = {"site_valuation", "provenance_drilldown", "axiom_explanation", "comparison", "risk_assessment"}
        template_cats = {t["category"] for t in TEMPLATES.values() if t["category"] != "utility"}
        assert expected.issubset(template_cats)

    def test_get_template_returns_dict(self):
        t = get_template("site_valuation")
        assert t is not None
        assert isinstance(t, dict)
        assert "cypher" in t

    def test_get_template_unknown_returns_none(self):
        assert get_template("nonexistent_template") is None

    def test_templates_for_category_returns_list(self):
        results = templates_for_category("site_valuation")
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_templates_for_unknown_category_empty(self):
        results = templates_for_category("unknown_category")
        assert results == []


class TestParameterizedQueries:
    """Verify all templates use parameterized queries (no string interpolation)."""

    @pytest.mark.parametrize("name,template", list(TEMPLATES.items()))
    def test_no_fstring_interpolation(self, name, template):
        """Templates must not contain Python f-string patterns like {variable}
        that are not Neo4j parameters ($variable)."""
        cypher = template["cypher"]
        # Neo4j parameters use $param_name. We check for curly-brace interpolation
        # but allow legitimate Cypher map syntax {key: $value} and labels {name: $name}
        # Also allow MAX_HOPS_PLACEHOLDER as a known safe substitution
        # Strip out Cypher map literals (inside curly braces with colons) first
        cleaned = re.sub(r"\{[^}]*:[^}]*\}", "", cypher)
        # The remaining text should not have Python-style {variable} patterns
        # that could indicate string interpolation vulnerability
        suspicious = re.findall(r"\{(\w+)\}", cleaned)
        assert not suspicious, f"Template '{name}' may have unsafe interpolation: {suspicious}"

    @pytest.mark.parametrize("name,template", list(TEMPLATES.items()))
    def test_uses_dollar_parameters(self, name, template):
        """Templates with parameters should use $ syntax."""
        params = template.get("parameters", [])
        cypher = template["cypher"]
        for param in params:
            if param == "max_hops":
                # max_hops uses placeholder substitution, not $ parameter
                assert "MAX_HOPS_PLACEHOLDER" in cypher
            elif param == "result_limit":
                assert f"${param}" in cypher
            else:
                assert f"${param}" in cypher, (
                    f"Template '{name}' declares parameter '{param}' but doesn't use ${param}"
                )


class TestMaxHopsPlaceholder:
    def test_graph_traverse_has_placeholder(self):
        t = get_template("graph_traverse")
        assert t is not None
        assert "MAX_HOPS_PLACEHOLDER" in t["cypher"]

    def test_placeholder_substitution_produces_valid_cypher(self):
        t = get_template("graph_traverse")
        cypher = t["cypher"].replace("MAX_HOPS_PLACEHOLDER", "3")
        assert "*1..3" in cypher
        assert "MAX_HOPS_PLACEHOLDER" not in cypher

    def test_max_hops_integer_only(self):
        """Ensure non-integer max_hops would be caught by int() conversion."""
        with pytest.raises(ValueError):
            int("3; DROP (n)")  # noqa: B018


class TestTemplateFields:
    @pytest.mark.parametrize("name,template", list(TEMPLATES.items()))
    def test_has_required_keys(self, name, template):
        assert "name" in template
        assert "category" in template
        assert "cypher" in template
        assert "parameters" in template

    def test_site_valuation_returns_expected_fields(self):
        t = get_template("site_valuation")
        cypher = t["cypher"]
        assert "AS site" in cypher
        assert "AS total_esv" in cypher
        assert "AS services" in cypher
        assert "AS evidence" in cypher

    def test_provenance_returns_doi(self):
        t = get_template("provenance_drilldown")
        assert "AS doi" in t["cypher"]

    def test_axiom_returns_coefficients(self):
        t = get_template("axiom_explanation")
        assert "AS coefficients" in t["cypher"]

    def test_comparison_returns_site_name(self):
        t = get_template("comparison")
        assert "AS site" in t["cypher"]

    def test_graph_traverse_has_limit(self):
        t = get_template("graph_traverse")
        assert "LIMIT" in t["cypher"]


class TestWarningRegression:
    def test_site_valuation_uses_safe_ci_property_access(self):
        cypher = get_template("site_valuation")["cypher"]
        assert "es.ci_low" not in cypher
        assert "es.ci_high" not in cypher
        assert "properties(es)['ci_low']" in cypher
        assert "properties(es)['ci_high']" in cypher

    def test_risk_assessment_uses_safe_ci_property_access(self):
        cypher = get_template("risk_assessment")["cypher"]
        assert "es.ci_low" not in cypher
        assert "es.ci_high" not in cypher
        assert "properties(es)['ci_low']" in cypher
        assert "properties(es)['ci_high']" in cypher

    def test_provenance_uses_safe_citation_property_access(self):
        cypher = get_template("provenance_drilldown")["cypher"]
        assert "d.citation" not in cypher
        assert "properties(d)['citation']" in cypher


class TestAxiomByConceptTemplate:
    """Tests for the axiom_by_concept template (Phase I intelligence upgrade)."""

    def test_axiom_by_concept_exists(self):
        t = get_template("axiom_by_concept")
        assert t is not None

    def test_axiom_by_concept_has_required_keys(self):
        t = get_template("axiom_by_concept")
        assert t["category"] == "axiom_explanation"
        assert "concept_term" in t["parameters"]
        assert "axiom_ids" in t["parameters"]

    def test_axiom_by_concept_uses_parameters(self):
        t = get_template("axiom_by_concept")
        cypher = t["cypher"]
        assert "$concept_term" in cypher
        assert "$axiom_ids" in cypher
        assert "$result_limit" in cypher

    def test_axiom_by_concept_returns_expected_fields(self):
        t = get_template("axiom_by_concept")
        cypher = t["cypher"]
        assert "AS axiom_id" in cypher
        assert "AS axiom_name" in cypher
        assert "AS evidence" in cypher
        assert "AS applicable_sites" in cypher

    def test_axiom_by_concept_has_limit(self):
        t = get_template("axiom_by_concept")
        assert "LIMIT" in t["cypher"]


class TestMechanismChainTemplate:
    """Tests for mechanism_chain and concept_overview templates (Phase II)."""

    def test_mechanism_chain_exists(self):
        t = get_template("mechanism_chain")
        assert t is not None

    def test_mechanism_chain_category(self):
        t = get_template("mechanism_chain")
        assert t["category"] == "concept_explanation"

    def test_mechanism_chain_parameters(self):
        t = get_template("mechanism_chain")
        assert "concept_id" in t["parameters"]

    def test_mechanism_chain_uses_concept_id_param(self):
        t = get_template("mechanism_chain")
        assert "$concept_id" in t["cypher"]

    def test_mechanism_chain_has_limit(self):
        t = get_template("mechanism_chain")
        assert "LIMIT" in t["cypher"]

    def test_mechanism_chain_traverses_involves_axiom(self):
        t = get_template("mechanism_chain")
        assert "INVOLVES_AXIOM" in t["cypher"]

    def test_mechanism_chain_returns_expected_fields(self):
        t = get_template("mechanism_chain")
        cypher = t["cypher"]
        assert "AS axiom_id" in cypher
        assert "AS name" in cypher
        assert "AS description" in cypher
        assert "AS evidence" in cypher

    def test_concept_overview_exists(self):
        t = get_template("concept_overview")
        assert t is not None

    def test_concept_overview_category(self):
        t = get_template("concept_overview")
        assert t["category"] == "concept_explanation"

    def test_concept_overview_parameters(self):
        t = get_template("concept_overview")
        assert "search_term" in t["parameters"]
        assert "concept_id" in t["parameters"]

    def test_concept_overview_uses_parameters(self):
        t = get_template("concept_overview")
        cypher = t["cypher"]
        assert "$search_term" in cypher
        assert "$concept_id" in cypher

    def test_concept_overview_has_limit(self):
        t = get_template("concept_overview")
        assert "LIMIT" in t["cypher"]

    def test_concept_overview_returns_expected_fields(self):
        t = get_template("concept_overview")
        cypher = t["cypher"]
        assert "AS concept_id" in cypher
        assert "AS name" in cypher
        assert "AS description" in cypher
        assert "AS domain" in cypher

    def test_concept_explanation_category_has_templates(self):
        results = templates_for_category("concept_explanation")
        assert len(results) >= 2
        names = [t["name"] for t in results]
        assert "mechanism_chain" in names
        assert "concept_overview" in names
