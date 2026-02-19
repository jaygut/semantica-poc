"""Tests for DOI verification and placeholder blocking logic."""

from maris.provenance.doi_verifier import DoiVerifier


class TestDoiVerifier:
    def test_normalize_plain_doi(self):
        assert DoiVerifier.normalize("10.1038/s41467-025-59204-4") == "10.1038/s41467-025-59204-4"

    def test_normalize_doi_url(self):
        assert (
            DoiVerifier.normalize("https://doi.org/10.1038/s41467-025-59204-4")
            == "10.1038/s41467-025-59204-4"
        )

    def test_normalize_doi_prefix(self):
        assert DoiVerifier.normalize("doi:10.1016/j.ecolecon.2024.108163") == "10.1016/j.ecolecon.2024.108163"

    def test_placeholder_is_blocked(self):
        verifier = DoiVerifier(enable_live_checks=False)
        result = verifier.verify("10.1016/j.marpol.2025.106XXX")
        assert result.doi_valid is False
        assert result.verification_status == "placeholder_blocked"

    def test_invalid_format_is_blocked(self):
        verifier = DoiVerifier(enable_live_checks=False)
        result = verifier.verify("not-a-doi")
        assert result.doi_valid is False
        assert result.verification_status == "invalid_format"

    def test_missing_is_blocked(self):
        verifier = DoiVerifier(enable_live_checks=False)
        result = verifier.verify("")
        assert result.doi_valid is False
        assert result.verification_status == "missing"

    def test_valid_format_without_live_checks_is_unverified(self):
        verifier = DoiVerifier(enable_live_checks=False)
        result = verifier.verify("10.1016/j.ecolecon.2024.108163")
        assert result.doi_valid is True
        assert result.verification_status == "unverified"

    def test_cached_result_reused(self):
        verifier = DoiVerifier(enable_live_checks=False)
        first = verifier.verify("10.1016/j.ecolecon.2024.108163")
        second = verifier.verify("10.1016/j.ecolecon.2024.108163")
        assert first == second
