"""Unit tests for v4 GraphRAG chat normalization and DOI UI helpers."""

from investor_demo.components.v4.graphrag_chat import (
    _confidence_methodology_markdown,
    _confidence_breakdown_html,
    _doi_status_metrics,
    _evidence_table,
    _normalize_query,
    _resolve_doi_status,
)


def test_normalize_query_governance_prompt_to_risk_template():
    normalized, reason = _normalize_query(
        effective_question="How does UNESCO governance pressure affect this site?",
        site="Galapagos Marine Reserve",
        classification={"category": "open_domain", "confidence": 0.2, "sites": []},
    )

    assert normalized == "What are the key governance and climate risks for Galapagos Marine Reserve?"
    assert reason is not None
    assert "governance" in reason.lower()


def test_normalize_query_provenance_prompt_to_evidence_template():
    normalized, reason = _normalize_query(
        effective_question="Can you show DOI sources for this claim?",
        site="Aldabra Atoll",
        classification={"category": "open_domain", "confidence": 0.1, "sites": []},
    )

    assert normalized == "What evidence supports the valuation of Aldabra Atoll?"
    assert reason is not None
    assert "provenance" in reason.lower()


def test_normalize_query_comparison_with_one_site_falls_back_to_valuation():
    normalized, reason = _normalize_query(
        effective_question="Compare Raja Ampat against the portfolio average",
        site="Raja Ampat Marine Park",
        classification={
            "category": "comparison",
            "confidence": 0.9,
            "sites": ["Raja Ampat Marine Park"],
        },
    )

    assert normalized == "What is the total ecosystem service value of Raja Ampat Marine Park?"
    assert reason is not None
    assert "fewer than two" in reason.lower()


def test_normalize_query_keeps_high_confidence_deterministic_prompt():
    normalized, reason = _normalize_query(
        effective_question="What is the total ecosystem service value of Cabo Pulmo National Park?",
        site="Cabo Pulmo National Park",
        classification={"category": "site_valuation", "confidence": 0.92, "sites": []},
    )

    assert normalized == "What is the total ecosystem service value of Cabo Pulmo National Park?"
    assert reason is None


def test_resolve_doi_status_uses_explicit_status_and_fallbacks():
    assert _resolve_doi_status({"doi_verification_status": "invalid_format", "doi": "not-a-doi"}) == "invalid_format"
    assert _resolve_doi_status({"doi": "10.1000/example", "doi_valid": True}) == "verified"
    assert _resolve_doi_status({"doi": "10.1000/example", "doi_valid": False}) == "unverified"
    assert _resolve_doi_status({"doi": ""}) == "missing"


def test_doi_status_metrics_counts_verified_unverified_and_missing_invalid():
    evidence = [
        {"doi_verification_status": "verified", "doi": "10.1000/abc"},
        {"doi": "10.1000/def", "doi_valid": False},
        {"doi": "", "doi_verification_status": "missing"},
        {"doi_verification_status": "placeholder_blocked", "doi": "TBD"},
    ]

    metrics = _doi_status_metrics(evidence)
    assert metrics == {"verified": 1, "unverified": 1, "missing_invalid": 2}


def test_evidence_table_renders_doi_status_column_and_reason_tooltip():
    evidence = [
        {
            "tier": "T1",
            "title": "Blue carbon valuation baseline",
            "doi": "10.1000/xyz",
            "doi_url": "https://doi.org/10.1000/xyz",
            "year": 2024,
            "doi_verification_status": "verified",
            "doi_verification_reason": "Crossref title and year matched",
        }
    ]

    html = _evidence_table(evidence)

    assert "DOI Status" in html
    assert "verified" in html.lower()
    assert 'title="Crossref title and year matched"' in html
    assert "Blue carbon valuation baseline" in html


def test_evidence_table_renders_na_for_missing_tier_and_year():
    html = _evidence_table([
        {
            "title": "Untiered source",
            "doi": "",
            "doi_url": "",
            "year": None,
            "tier": None,
            "doi_verification_status": "missing",
        }
    ])

    assert "Untiered source" in html
    assert ">N/A<" in html


def test_confidence_breakdown_renders_new_provenance_factors():
    html = _confidence_breakdown_html(
        {
            "composite": 0.42,
            "tier_base": 0.8,
            "path_discount": 0.85,
            "staleness_discount": 0.9,
            "sample_factor": 0.7,
            "evidence_quality_factor": 0.6,
            "citation_coverage_factor": 0.4,
            "completeness_factor": 0.5,
            "explanation": "test",
        }
    )

    assert "Evidence Quality" in html
    assert "Citation Coverage" in html
    assert "Completeness" in html


def test_confidence_methodology_markdown_includes_formula_and_caps():
    content = _confidence_methodology_markdown()

    assert "composite = tier_base x path_discount" in content
    assert "capped at **25%**" in content
    assert "capped at **35%**" in content
    assert "Show confidence breakdown" in content
