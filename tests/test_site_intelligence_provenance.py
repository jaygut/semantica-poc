"""Tests for Site Intelligence provenance summary normalization."""

from investor_demo.components.v4.site_intelligence import _resolve_provenance_summary


def _sample_sources() -> list[dict]:
    return [
        {"doi": "10.1038/s41558-018-0096-y", "source_tier": "T1"},
        {"doi": "10.1038/s41467-025-59204-4", "source_tier": "T1"},
        {"url": "https://example.org/report", "source_tier": "T2"},
    ]


class TestResolveProvenanceSummary:
    def test_uses_matching_summary(self):
        data = {
            "site": {"name": "Test Site"},
            "provenance": {"data_sources": _sample_sources()},
            "provenance_summary": {
                "total_sources": 3,
                "doi_backed": 2,
                "url_only": 1,
                "doi_coverage_pct": 66.7,
                "evidence_tier_distribution": {"T1": 2, "T2": 1, "T3": 0, "T4": 0},
            },
        }

        summary = _resolve_provenance_summary(data)
        assert summary["total_sources"] == 3
        assert summary["doi_backed"] == 2
        assert summary["url_only"] == 1
        assert summary["doi_coverage_pct"] == 66.7
        assert summary["evidence_tier_distribution"] == {"T1": 2, "T2": 1, "T3": 0, "T4": 0}

    def test_accepts_curated_summary_when_internally_consistent(self):
        data = {
            "site": {"name": "Mismatch Site"},
            "provenance": {"data_sources": _sample_sources()},
            "provenance_summary": {
                "total_sources": 99,
                "doi_backed": 99,
                "url_only": 0,
                "doi_coverage_pct": 100.0,
                "evidence_tier_distribution": {"T1": 99, "T2": 0, "T3": 0, "T4": 0},
            },
        }

        summary = _resolve_provenance_summary(data)

        assert summary["total_sources"] == 99
        assert summary["doi_backed"] == 99
        assert summary["url_only"] == 0
        assert summary["doi_coverage_pct"] == 100.0
        assert summary["evidence_tier_distribution"] == {
            "T1": 99,
            "T2": 0,
            "T3": 0,
            "T4": 0,
        }

    def test_falls_back_to_derived_when_summary_invalid(self, caplog):
        data = {
            "site": {"name": "Invalid Summary Site"},
            "provenance": {"data_sources": _sample_sources()},
            "provenance_summary": {
                "total_sources": 3,
                "doi_backed": 2,
                "url_only": 1,
                "doi_coverage_pct": 66.7,
                # invalid: tier counts sum to 2 instead of 3
                "evidence_tier_distribution": {"T1": 2, "T2": 0, "T3": 0, "T4": 0},
            },
        }

        summary = _resolve_provenance_summary(data)

        assert summary["total_sources"] == 3
        assert summary["doi_backed"] == 2
        assert summary["url_only"] == 1
        assert summary["doi_coverage_pct"] == 66.7
        assert summary["evidence_tier_distribution"] == {
            "T1": 2,
            "T2": 1,
            "T3": 0,
            "T4": 0,
        }
        assert "provenance_summary invalid" in caplog.text

    def test_derives_summary_when_missing(self):
        data = {
            "provenance": {
                "data_sources": [
                    {"doi": "10.1038/s41558-018-0096-y", "source_tier": "T1"},
                    {"url": "https://example.org/t2", "source_tier": "T2"},
                    {"url": "https://example.org/t4", "source_tier": "T4"},
                ]
            }
        }

        summary = _resolve_provenance_summary(data)
        assert summary == {
            "total_sources": 3,
            "doi_backed": 1,
            "url_only": 2,
            "doi_coverage_pct": 33.3,
            "evidence_tier_distribution": {"T1": 1, "T2": 1, "T3": 0, "T4": 1},
        }
