"""Format query responses with citations, evidence tables, and claim verification."""

from maris.query.validators import validate_evidence_dois


def format_response(raw_response: dict) -> dict:
    """Clean up a raw response: normalise evidence items, add DOI links,
    and pass through verified/unverified claims."""
    evidence = [_normalise_evidence_item(e) for e in raw_response.get("evidence", [])]

    # Validate evidence DOIs
    evidence, _doi_issues = validate_evidence_dois(evidence)

    return {
        "answer": raw_response.get("answer", ""),
        "confidence": raw_response.get("confidence", 0.0),
        "evidence": evidence,
        "axioms_used": raw_response.get("axioms_used", []),
        "graph_path": format_graph_path(raw_response.get("graph_path", [])),
        "caveats": raw_response.get("caveats", []),
        "verified_claims": raw_response.get("verified_claims", []),
        "unverified_claims": raw_response.get("unverified_claims", []),
        "confidence_breakdown": raw_response.get("confidence_breakdown"),
    }


def format_evidence_table(evidence: list[dict]) -> str:
    """Render evidence items as a markdown table."""
    if not evidence:
        return "_No evidence items._"

    header = "| DOI | Title | Year | Tier | Finding |"
    sep = "|-----|-------|------|------|---------|"
    rows = []
    for e in evidence:
        doi_link = f"[{e.get('doi', 'n/a')}](https://doi.org/{e['doi']})" if e.get("doi") else "n/a"
        rows.append(
            f"| {doi_link} | {e.get('title', '')} | {e.get('year', '')} | {e.get('tier', '')} | {e.get('finding', e.get('quote', ''))} |"
        )
    return "\n".join([header, sep, *rows])


def format_graph_path(path: list) -> list[dict]:
    """Normalise graph path entries into structured dicts."""
    structured = []
    for item in path:
        if isinstance(item, dict):
            structured.append(item)
        elif isinstance(item, str):
            structured.append({"step": item})
        else:
            structured.append({"step": str(item)})
    return structured


def _normalise_evidence_item(item: dict) -> dict:
    """Ensure evidence item has all expected fields."""
    doi = item.get("doi", "")
    return {
        "doi": doi,
        "doi_url": f"https://doi.org/{doi}" if doi else None,
        "title": item.get("title", ""),
        "year": item.get("year"),
        "tier": item.get("tier", ""),
        "page_ref": item.get("page_ref"),
        "quote": item.get("quote", item.get("finding", "")),
    }
