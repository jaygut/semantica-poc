"""LLM response validation and hallucination guardrails.

Provides schema validation, numerical claim verification against graph
context, DOI format checks, confidence bounds enforcement, and empty
result protection. Every LLM-generated answer is validated before being
returned to the user.
"""

import json
import logging
import re

from maris.provenance.doi_verifier import get_doi_verifier

logger = logging.getLogger(__name__)

# Regex for extracting numerical claims from answer text
_NUMERIC_PATTERN = re.compile(
    r"""
    \$[\d,.]+\s*[MBKmk]?       # Dollar amounts: $29.27M, $25,000
    | \d+\.?\d*\s*%             # Percentages: 84%, 4.5%
    | \d+\.?\d*\s*x             # Ratios: 4.63x
    """,
    re.VERBOSE,
)

# Required fields in a valid LLM response
_REQUIRED_FIELDS = {
    "answer": str,
    "confidence": (int, float),
    "evidence": list,
    "caveats": list,
}


def is_graph_context_empty(graph_context: dict | list | None) -> bool:
    """Check if graph context has no usable data.

    Returns True if context is None, empty, or contains only null values.
    """
    if graph_context is None:
        return True

    if isinstance(graph_context, list):
        if not graph_context:
            return True
        return all(
            v is None for item in graph_context
            for v in (item.values() if isinstance(item, dict) else [item])
        )

    if isinstance(graph_context, dict):
        if not graph_context:
            return True
        return all(_is_empty_value(v) for v in graph_context.values())

    return False


def _is_empty_value(v: object) -> bool:
    """Check if a single value is effectively empty."""
    if v is None:
        return True
    if isinstance(v, (list, dict)) and not v:
        return True
    return False


def empty_result_response() -> dict:
    """Return a safe response when graph context is empty."""
    return {
        "answer": (
            "Insufficient data in the knowledge graph to answer this question."
        ),
        "confidence": 0.0,
        "evidence": [],
        "axioms_used": [],
        "graph_path": [],
        "caveats": ["No matching data found in graph"],
        "verified_claims": [],
        "unverified_claims": [],
    }


def validate_response_schema(response: dict) -> tuple[dict, list[str]]:
    """Validate that the LLM response has required fields with correct types.

    Returns (cleaned_response, issues). If critical fields are missing, they
    are replaced with safe defaults.
    """
    issues: list[str] = []
    cleaned = dict(response)

    # Check required fields
    for field, expected_type in _REQUIRED_FIELDS.items():
        if field not in cleaned:
            issues.append(f"Missing required field: {field}")
            if expected_type is str:
                cleaned[field] = ""
            elif expected_type is list:
                cleaned[field] = []
            elif expected_type in ((int, float),):
                cleaned[field] = 0.0
        elif not isinstance(cleaned[field], expected_type):
            issues.append(
                f"Field '{field}' has wrong type: "
                f"expected {expected_type}, got {type(cleaned[field]).__name__}"
            )
            if field == "confidence":
                try:
                    cleaned[field] = float(cleaned[field])
                except (TypeError, ValueError):
                    cleaned[field] = 0.0
                    issues.append(
                        "Non-numeric confidence value, defaulted to 0.0"
                    )
            elif field == "evidence" and not isinstance(cleaned[field], list):
                cleaned[field] = []
            elif field == "caveats" and not isinstance(cleaned[field], list):
                cleaned[field] = []

    # Ensure confidence is bounded [0.0, 1.0]
    if "confidence" in cleaned:
        try:
            conf = float(cleaned["confidence"])
            cleaned["confidence"] = max(0.0, min(1.0, conf))
            if conf < 0.0 or conf > 1.0:
                issues.append(
                    f"Confidence {conf} clamped to [{max(0.0, conf):.2f}, "
                    f"{min(1.0, conf):.2f}]"
                )
        except (TypeError, ValueError):
            cleaned["confidence"] = 0.0
            issues.append("Non-numeric confidence value, defaulted to 0.0")

    return cleaned, issues


def validate_evidence_dois(evidence: list[dict]) -> tuple[list[dict], list[str]]:
    """Validate DOI format on each evidence item.

    Returns (evidence_with_flags, issues).
    """
    verifier = get_doi_verifier()
    issues: list[str] = []
    validated = []

    for idx, item in enumerate(evidence, start=1):
        entry = dict(item)
        doi = entry.get("doi", "") or ""
        result = verifier.verify(doi)
        entry["doi"] = result.normalized_doi
        entry["doi_valid"] = result.doi_valid
        entry["doi_verification_status"] = result.verification_status
        entry["doi_verification_reason"] = result.reason
        entry["doi_resolver"] = result.resolver

        if result.verification_status != "verified":
            issues.append(
                f"Evidence item {idx}: DOI '{result.normalized_doi or doi}' "
                f"status={result.verification_status} ({result.reason})"
            )

        if not result.normalized_doi:
            issues.append(f"Evidence item {idx}: missing DOI")

        validated.append(entry)

    return validated, issues


def extract_numerical_claims(text: str) -> list[str]:
    """Extract all numerical claims (dollar amounts, percentages, ratios) from text."""
    return _NUMERIC_PATTERN.findall(text)


def _normalize_number(claim: str) -> float | None:
    """Convert a claim string like '$29.27M' or '4.63x' to a float."""
    s = claim.strip().rstrip("%xX")
    s = s.lstrip("$")
    s = s.replace(",", "")

    multiplier = 1.0
    if claim.strip().upper().endswith("M"):
        multiplier = 1_000_000
        s = s.rstrip("Mm")
    elif claim.strip().upper().endswith("B"):
        multiplier = 1_000_000_000
        s = s.rstrip("Bb")
    elif claim.strip().upper().endswith("K"):
        multiplier = 1_000
        s = s.rstrip("Kk")

    try:
        return float(s) * multiplier
    except ValueError:
        return None


def _flatten_values(obj: object) -> list[float]:
    """Recursively extract all numeric values from a nested dict/list."""
    values: list[float] = []
    if isinstance(obj, (int, float)):
        values.append(float(obj))
    elif isinstance(obj, str):
        try:
            values.append(float(obj))
        except ValueError:
            pass
    elif isinstance(obj, dict):
        for v in obj.values():
            values.extend(_flatten_values(v))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            values.extend(_flatten_values(item))
    return values


def verify_numerical_claims(
    answer: str, graph_context: dict | list | None
) -> tuple[list[str], list[str]]:
    """Cross-check numerical claims in the answer against graph context.

    Returns (verified_claims, unverified_claims).
    """
    claims = extract_numerical_claims(answer)
    if not claims:
        return [], []

    # Flatten all numeric values from graph context
    context_values = set()
    if graph_context:
        raw_values = _flatten_values(graph_context)
        context_values = set(raw_values)
        # Also add common derived forms (millions, percentages)
        for v in raw_values:
            context_values.add(v * 1_000_000)
            context_values.add(v * 100)
            context_values.add(v / 1_000_000)

    verified: list[str] = []
    unverified: list[str] = []

    for claim in claims:
        claim_val = _normalize_number(claim)
        if claim_val is None:
            unverified.append(claim)
            continue

        # Check if the claim value (or close to it) exists in context
        found = False
        for cv in context_values:
            if cv == 0:
                if claim_val == 0:
                    found = True
                    break
            elif abs(claim_val - cv) / max(abs(cv), 1e-9) < 0.05:
                found = True
                break

        if found:
            verified.append(claim)
        else:
            unverified.append(claim)

    return verified, unverified


def validate_llm_response(
    response: dict, graph_context: dict | list | None
) -> dict:
    """Full validation pipeline for an LLM response.

    1. Schema validation
    2. Confidence bounds
    3. Evidence DOI validation
    4. Numerical claim verification
    5. Add verified/unverified claims and caveats

    Returns the cleaned, validated response dict.
    """
    all_caveats: list[str] = list(response.get("caveats", []))

    # 1. Schema validation
    cleaned, schema_issues = validate_response_schema(response)
    if schema_issues:
        logger.warning("Schema issues: %s", schema_issues)
        all_caveats.extend(schema_issues)

    # 2. Evidence DOI validation
    evidence = cleaned.get("evidence", [])
    validated_evidence, doi_issues = validate_evidence_dois(evidence)
    cleaned["evidence"] = validated_evidence
    if doi_issues:
        logger.warning("DOI issues: %s", doi_issues)
        all_caveats.extend(doi_issues)

    # 3. Numerical claim verification
    answer = cleaned.get("answer", "")
    verified, unverified = verify_numerical_claims(answer, graph_context)
    cleaned["verified_claims"] = verified
    cleaned["unverified_claims"] = unverified
    if unverified:
        all_caveats.append(
            f"Unverified numerical claims: {', '.join(unverified)}"
        )

    cleaned["caveats"] = all_caveats
    return cleaned


def extract_json_robust(text: str) -> dict:
    """Extract JSON from LLM response text, handling common failure modes.

    Tries in order:
    1. JSON code fence extraction
    2. Direct JSON parse
    3. First { to last } extraction
    4. Truncated JSON repair (close open braces/brackets)
    5. Structured error fallback
    """
    if not text or not text.strip():
        return {
            "error": "Empty LLM response",
            "raw": "",
            "answer": "",
            "confidence": 0.0,
            "evidence": [],
            "caveats": ["LLM returned empty response"],
        }

    # 1. Try code fence extraction (```json ... ``` or ``` ... ```)
    fence_match = re.search(
        r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL
    )
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # 2. Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 3. Extract from first { to last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass

    # 4. Attempt truncated JSON repair
    if first_brace != -1:
        fragment = text[first_brace:]
        repaired = _repair_truncated_json(fragment)
        if repaired is not None:
            return repaired

    # 5. Structured error fallback
    logger.warning("All JSON extraction methods failed")
    return {
        "error": "Failed to parse JSON from LLM response",
        "raw": text[:1000],
        "answer": "",
        "confidence": 0.0,
        "evidence": [],
        "caveats": ["LLM response could not be parsed as JSON"],
    }


def _repair_truncated_json(fragment: str) -> dict | None:
    """Attempt to repair truncated JSON by closing open brackets/braces."""
    # Count open vs close braces and brackets
    open_braces = fragment.count("{") - fragment.count("}")
    open_brackets = fragment.count("[") - fragment.count("]")

    if open_braces < 0 or open_brackets < 0:
        return None

    # Remove trailing comma if present
    repaired = fragment.rstrip().rstrip(",")

    # Close quotes if odd number
    if repaired.count('"') % 2 == 1:
        repaired += '"'

    # Close brackets then braces
    repaired += "]" * open_brackets
    repaired += "}" * open_braces

    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        return None
