"""DOI verification utilities for provenance hardening.

This module implements three levels of DOI checks:
1) normalization + syntax validation,
2) placeholder blocking,
3) optional live resolvability checks (Crossref/doi.org).
"""

from __future__ import annotations

import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from maris.provenance.models import DoiVerificationResult

# Relaxed DOI pattern accepted by Crossref and common publishers.
_DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)

# Placeholder fragments that should never be treated as valid provenance.
_PLACEHOLDER_PATTERN = re.compile(
    r"(?:x{3,}|unknown|tbd|placeholder|not[\s._-]?available)",
    re.IGNORECASE,
)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class _ResolverConfig:
    enable_live_checks: bool
    timeout_seconds: float


class DoiVerifier:
    """Validate and optionally resolve DOIs.

    Live checks are disabled by default to keep request latency predictable.
    Enable with ``MARIS_ENABLE_LIVE_DOI_CHECKS=true``.
    """

    def __init__(
        self,
        *,
        enable_live_checks: bool | None = None,
        timeout_seconds: float = 2.0,
    ) -> None:
        if enable_live_checks is None:
            enable_live_checks = _env_bool("MARIS_ENABLE_LIVE_DOI_CHECKS", default=False)
        self._cfg = _ResolverConfig(
            enable_live_checks=enable_live_checks,
            timeout_seconds=max(float(timeout_seconds), 0.5),
        )
        self._cache: dict[str, DoiVerificationResult] = {}

    @staticmethod
    def normalize(doi: str | None) -> str:
        """Normalize DOI strings to canonical format without resolver prefix."""
        if not doi:
            return ""
        value = doi.strip()
        if not value:
            return ""

        value = value.removeprefix("doi:").removeprefix("DOI:").strip()

        for prefix in (
            "https://doi.org/",
            "http://doi.org/",
            "https://dx.doi.org/",
            "http://dx.doi.org/",
        ):
            if value.lower().startswith(prefix):
                value = value[len(prefix):]
                break

        return value.strip()

    @staticmethod
    def has_placeholder(doi: str) -> bool:
        if not doi:
            return False
        return bool(_PLACEHOLDER_PATTERN.search(doi))

    @staticmethod
    def is_valid_format(doi: str) -> bool:
        if not doi:
            return False
        return bool(_DOI_PATTERN.match(doi))

    def verify(self, raw_doi: str | None) -> DoiVerificationResult:
        """Validate and optionally resolve a DOI."""
        normalized = self.normalize(raw_doi)

        if not normalized:
            return DoiVerificationResult(
                raw_doi=raw_doi or "",
                normalized_doi="",
                doi_valid=False,
                verification_status="missing",
                reason="DOI is missing",
            )

        if self.has_placeholder(normalized):
            return DoiVerificationResult(
                raw_doi=raw_doi or "",
                normalized_doi=normalized,
                doi_valid=False,
                verification_status="placeholder_blocked",
                reason="DOI contains placeholder tokens",
            )

        if not self.is_valid_format(normalized):
            return DoiVerificationResult(
                raw_doi=raw_doi or "",
                normalized_doi=normalized,
                doi_valid=False,
                verification_status="invalid_format",
                reason="DOI format is invalid",
            )

        if normalized in self._cache:
            return self._cache[normalized]

        if not self._cfg.enable_live_checks:
            result = DoiVerificationResult(
                raw_doi=raw_doi or "",
                normalized_doi=normalized,
                doi_valid=True,
                verification_status="unverified",
                reason="Live DOI verification is disabled",
            )
            self._cache[normalized] = result
            return result

        # Live checks: Crossref first, then DOI resolver.
        resolved = self._resolve_crossref(normalized)
        if resolved is None:
            resolved = self._resolve_doi_org(normalized)

        if resolved is None:
            result = DoiVerificationResult(
                raw_doi=raw_doi or "",
                normalized_doi=normalized,
                doi_valid=True,
                verification_status="unresolvable",
                reason="DOI did not resolve via Crossref or doi.org",
            )
        else:
            result = DoiVerificationResult(
                raw_doi=raw_doi or "",
                normalized_doi=normalized,
                doi_valid=True,
                verification_status="verified",
                reason="DOI resolved",
                resolver=resolved["resolver"],
                resolved_url=resolved["url"],
            )

        self._cache[normalized] = result
        return result

    def _resolve_crossref(self, doi: str) -> dict[str, str] | None:
        quoted = urllib.parse.quote(doi, safe="")
        url = f"https://api.crossref.org/works/{quoted}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "MARIS-DOI-Validator/1.0"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._cfg.timeout_seconds) as resp:  # noqa: S310
                if 200 <= resp.status < 300:
                    return {"resolver": "crossref", "url": url}
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            return None
        return None

    def _resolve_doi_org(self, doi: str) -> dict[str, str] | None:
        url = f"https://doi.org/{urllib.parse.quote(doi, safe='/')}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "MARIS-DOI-Validator/1.0"},
            method="HEAD",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._cfg.timeout_seconds) as resp:  # noqa: S310
                if 200 <= resp.status < 400:
                    return {"resolver": "doi.org", "url": url}
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            return None
        return None


_default_verifier: DoiVerifier | None = None


def get_doi_verifier() -> DoiVerifier:
    """Return module-level DOI verifier singleton."""
    global _default_verifier
    if _default_verifier is None:
        _default_verifier = DoiVerifier()
    return _default_verifier
