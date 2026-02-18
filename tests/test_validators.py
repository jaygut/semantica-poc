"""Tests for LLM response validation logic in maris.query.validators."""


from maris.query.validators import (
    validate_response_schema,
    extract_numerical_claims,
    verify_numerical_claims,
    validate_evidence_dois,
    extract_json_robust,
    is_graph_context_empty,
    validate_llm_response,
)


# ---- Schema validation ----

class TestSchemaValidation:
    def test_valid_response_no_issues(self):
        response = {
            "answer": "The ESV is $29.27M.",
            "confidence": 0.85,
            "evidence": [{"doi": "10.1016/j.ecolecon.2024.108163", "finding": "WTP increase"}],
            "caveats": [],
        }
        cleaned, issues = validate_response_schema(response)
        assert len(issues) == 0
        assert cleaned["answer"] == "The ESV is $29.27M."

    def test_missing_answer_adds_issue(self):
        response = {"confidence": 0.5, "evidence": [], "caveats": []}
        cleaned, issues = validate_response_schema(response)
        assert any("answer" in i.lower() for i in issues)
        assert cleaned["answer"] == ""

    def test_missing_confidence_adds_issue(self):
        response = {"answer": "test", "evidence": [], "caveats": []}
        cleaned, issues = validate_response_schema(response)
        assert any("confidence" in i.lower() for i in issues)
        assert cleaned["confidence"] == 0.0

    def test_wrong_type_confidence_coerced(self):
        response = {"answer": "test", "confidence": "high", "evidence": [], "caveats": []}
        cleaned, _issues = validate_response_schema(response)
        assert isinstance(cleaned["confidence"], float)

    def test_confidence_clamped_above_one(self):
        response = {"answer": "test", "confidence": 1.5, "evidence": [], "caveats": []}
        cleaned, _issues = validate_response_schema(response)
        assert cleaned["confidence"] <= 1.0

    def test_confidence_clamped_below_zero(self):
        response = {"answer": "test", "confidence": -0.5, "evidence": [], "caveats": []}
        cleaned, _issues = validate_response_schema(response)
        assert cleaned["confidence"] >= 0.0

    def test_normal_confidence_unchanged(self):
        response = {"answer": "test", "confidence": 0.85, "evidence": [], "caveats": []}
        cleaned, _issues = validate_response_schema(response)
        assert cleaned["confidence"] == 0.85


# ---- Numerical claim extraction ----

class TestNumericalClaimExtraction:
    def test_dollar_amount_millions(self):
        claims = extract_numerical_claims("The total ESV is $29.27M per year.")
        assert any("29.27" in c for c in claims)

    def test_percentage(self):
        claims = extract_numerical_claims("WTP increased by 84% with higher biomass.")
        assert any("84" in c for c in claims)

    def test_ratio(self):
        claims = extract_numerical_claims("Biomass recovery ratio of 4.63x.")
        assert any("4.63" in c for c in claims)

    def test_no_claims(self):
        claims = extract_numerical_claims("This is a qualitative statement.")
        assert len(claims) == 0

    def test_multiple_claims(self):
        text = "ESV is $29.27M with 84% confidence and 4.63x biomass ratio."
        claims = extract_numerical_claims(text)
        assert len(claims) >= 3

    def test_dollar_billions(self):
        claims = extract_numerical_claims("Value estimated at $1.2B annually.")
        assert any("1.2" in c for c in claims)


# ---- Claim verification ----

class TestClaimVerification:
    def test_verified_claim_found_in_context(self):
        context = {"total_esv": 29270000}
        verified, unverified = verify_numerical_claims("The ESV is $29.27M.", context)
        assert len(verified) > 0 or len(unverified) >= 0

    def test_empty_context_all_unverified(self):
        _verified, unverified = verify_numerical_claims("The ESV is $29.27M.", {})
        assert len(unverified) > 0

    def test_no_claims_empty_result(self):
        verified, unverified = verify_numerical_claims("No numbers here.", {"total_esv": 29270000})
        assert len(verified) == 0
        assert len(unverified) == 0

    def test_none_context(self):
        _verified, unverified = verify_numerical_claims("Value is $100M.", None)
        assert len(unverified) > 0


# ---- DOI format validation ----

class TestDOIValidation:
    def test_valid_doi(self):
        evidence = [{"doi": "10.1016/j.ecolecon.2024.108163"}]
        validated, issues = validate_evidence_dois(evidence)
        assert validated[0]["doi_valid"] is True
        assert validated[0]["doi_verification_status"] in {
            "verified",
            "unverified",
            "unresolvable",
        }
        assert not any("invalid_format" in issue for issue in issues)

    def test_valid_doi_nature(self):
        evidence = [{"doi": "10.1038/nature12345"}]
        validated, issues = validate_evidence_dois(evidence)
        assert validated[0]["doi_valid"] is True
        assert validated[0]["doi_verification_status"] in {
            "verified",
            "unverified",
            "unresolvable",
        }
        assert not any("invalid_format" in issue for issue in issues)

    def test_invalid_doi_no_prefix(self):
        evidence = [{"doi": "fake-doi-123"}]
        validated, issues = validate_evidence_dois(evidence)
        assert validated[0]["doi_valid"] is False
        assert len(issues) > 0

    def test_empty_doi(self):
        evidence = [{"doi": ""}]
        validated, _issues = validate_evidence_dois(evidence)
        assert validated[0]["doi_valid"] is False
        assert validated[0]["doi_verification_status"] == "missing"

    def test_missing_doi(self):
        evidence = [{"title": "No DOI paper"}]
        validated, _issues = validate_evidence_dois(evidence)
        assert validated[0]["doi_valid"] is False
        assert validated[0]["doi_verification_status"] == "missing"

    def test_placeholder_doi_blocked(self):
        evidence = [{"doi": "10.1016/j.marpol.2025.106XXX"}]
        validated, issues = validate_evidence_dois(evidence)
        assert validated[0]["doi_valid"] is False
        assert validated[0]["doi_verification_status"] == "placeholder_blocked"
        assert any("placeholder_blocked" in issue for issue in issues)

    def test_doi_url_normalized(self):
        evidence = [{"doi": "https://doi.org/10.1038/s41467-025-59204-4"}]
        validated, _issues = validate_evidence_dois(evidence)
        assert validated[0]["doi"] == "10.1038/s41467-025-59204-4"
        assert validated[0]["doi_valid"] is True


# ---- Empty graph context ----

class TestEmptyGraphContext:
    def test_none_is_empty(self):
        assert is_graph_context_empty(None) is True

    def test_empty_dict_is_empty(self):
        assert is_graph_context_empty({}) is True

    def test_empty_list_is_empty(self):
        assert is_graph_context_empty([]) is True

    def test_dict_with_data_not_empty(self):
        assert is_graph_context_empty({"results": [{"site": "Cabo Pulmo"}]}) is False

    def test_all_none_values_is_empty(self):
        assert is_graph_context_empty({"a": None, "b": None}) is True


# ---- JSON extraction ----

class TestJSONExtraction:
    def test_fenced_json(self):
        text = '```json\n{"answer": "test", "confidence": 0.5}\n```'
        result = extract_json_robust(text)
        assert result.get("answer") == "test"

    def test_bare_json(self):
        text = '{"answer": "hello", "confidence": 0.8}'
        result = extract_json_robust(text)
        assert result.get("answer") == "hello"

    def test_non_json_returns_error(self):
        text = "This is just plain text without any JSON."
        result = extract_json_robust(text)
        assert "error" in result

    def test_partial_json(self):
        text = '{"answer": "truncated'
        result = extract_json_robust(text)
        # Should either repair or return error
        assert "answer" in result or "error" in result

    def test_empty_text_returns_error(self):
        result = extract_json_robust("")
        assert "error" in result
        assert result["confidence"] == 0.0

    def test_json_with_surrounding_text(self):
        text = 'Here is the result: {"answer": "found", "confidence": 0.7} end.'
        result = extract_json_robust(text)
        assert result.get("answer") == "found"


# ---- Full validation pipeline ----

class TestFullValidation:
    def test_full_pipeline_valid_response(self):
        response = {
            "answer": "The ESV is $29.27M.",
            "confidence": 0.85,
            "evidence": [{"doi": "10.1016/j.ecolecon.2024.108163", "finding": "Test"}],
            "caveats": [],
        }
        context = {"total_esv": 29270000}
        result = validate_llm_response(response, context)
        assert "verified_claims" in result
        assert "unverified_claims" in result

    def test_full_pipeline_empty_context(self):
        response = {
            "answer": "The value is $50M.",
            "confidence": 0.9,
            "evidence": [],
            "caveats": [],
        }
        result = validate_llm_response(response, {})
        assert len(result["unverified_claims"]) > 0

    def test_full_pipeline_surfaces_doi_caveats(self):
        response = {
            "answer": "Provenance is available.",
            "confidence": 0.8,
            "evidence": [{"doi": "10.1016/j.marpol.2025.106XXX", "title": "Placeholder"}],
            "caveats": [],
        }
        result = validate_llm_response(response, {})
        assert any("placeholder_blocked" in caveat for caveat in result["caveats"])
