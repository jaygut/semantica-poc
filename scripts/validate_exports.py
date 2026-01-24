#!/usr/bin/env python3
"""
Semantica export bundle validation.

Checks that export metadata matches file contents and that document_corpus.json
stays in sync with the registry. Uses only the standard library.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
REGISTRY_PATH = BASE_DIR / ".claude/registry/document_index.json"
EXPORT_DIR = BASE_DIR / "data/semantica_export"
CORPUS_PATH = EXPORT_DIR / "document_corpus.json"
ENTITIES_PATH = EXPORT_DIR / "entities.jsonld"
RELATIONSHIPS_PATH = EXPORT_DIR / "relationships.json"
AXIOMS_PATH = EXPORT_DIR / "bridge_axioms.json"


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise FileNotFoundError(f"Missing file: {path}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def approx_equal(a: float, b: float, tol: float = 1e-3) -> bool:
    return abs(a - b) <= tol


def validate_document_corpus(registry: dict, corpus: dict) -> list[str]:
    issues = []
    documents = registry.get("documents", {})
    stats = registry.get("statistics", {})
    by_tier = stats.get("by_tier", {})
    by_habitat = stats.get("by_habitat", {})
    by_domain = stats.get("by_domain", {})

    expected_total = len(documents)
    expected_abstracts = sum(1 for doc in documents.values() if doc.get("abstract"))
    expected_doi = sum(1 for doc in documents.values() if doc.get("doi"))

    summary = corpus.get("corpus_summary", {})

    if summary.get("total_documents") != expected_total:
        issues.append(
            f"document_corpus.total_documents {summary.get('total_documents')} "
            f"!= registry {expected_total}"
        )

    expected_tiers = {
        "T1_peer_reviewed": by_tier.get("T1", 0),
        "T2_institutional": by_tier.get("T2", 0),
        "T3_data_repository": by_tier.get("T3", 0),
    }
    if summary.get("by_tier") != expected_tiers:
        issues.append("document_corpus.by_tier does not match registry statistics")

    if summary.get("by_habitat") != by_habitat:
        issues.append("document_corpus.by_habitat does not match registry statistics")

    if summary.get("by_domain") != by_domain:
        issues.append("document_corpus.by_domain does not match registry statistics")

    expected_abstract_cov = round(expected_abstracts / expected_total, 3) if expected_total else 0.0
    expected_doi_cov = round(expected_doi / expected_total, 3) if expected_total else 0.0

    if not approx_equal(summary.get("abstract_coverage", 0.0), expected_abstract_cov):
        issues.append(
            f"document_corpus.abstract_coverage {summary.get('abstract_coverage')} "
            f"!= expected {expected_abstract_cov}"
        )

    if not approx_equal(summary.get("doi_coverage", 0.0), expected_doi_cov):
        issues.append(
            f"document_corpus.doi_coverage {summary.get('doi_coverage')} "
            f"!= expected {expected_doi_cov}"
        )

    return issues


def validate_entities(entities_doc: dict) -> list[str]:
    issues = []
    entities = entities_doc.get("entities")
    if not isinstance(entities, list):
        issues.append("entities.jsonld missing entities list")
        return issues

    for idx, entity in enumerate(entities):
        if "@type" not in entity:
            issues.append(f"entities[{idx}] missing @type")
        if "@id" not in entity:
            issues.append(f"entities[{idx}] missing @id")

    export_meta = entities_doc.get("export_metadata", {})
    entity_count = export_meta.get("entity_count")
    if entity_count is not None and entity_count != len(entities):
        issues.append(
            f"entities.jsonld export_metadata.entity_count {entity_count} "
            f"!= entities length {len(entities)}"
        )

    return issues


def validate_relationships(relationships_doc: dict) -> list[str]:
    issues = []
    relationships = relationships_doc.get("relationships")
    if not isinstance(relationships, list):
        issues.append("relationships.json missing relationships list")
        return issues

    for idx, rel in enumerate(relationships):
        for field in ("id", "type", "subject", "object"):
            if field not in rel:
                issues.append(f"relationships[{idx}] missing {field}")

    export_meta = relationships_doc.get("export_metadata", {})
    rel_count = export_meta.get("relationship_count")
    if rel_count is not None and rel_count != len(relationships):
        issues.append(
            f"relationships.json export_metadata.relationship_count {rel_count} "
            f"!= relationships length {len(relationships)}"
        )

    return issues


def validate_axioms(axioms_doc: dict) -> list[str]:
    issues = []
    axioms = axioms_doc.get("bridge_axioms")
    if not isinstance(axioms, list):
        issues.append("bridge_axioms.json missing bridge_axioms list")
        return issues

    export_meta = axioms_doc.get("export_metadata", {})
    axiom_count = export_meta.get("axiom_count")
    if axiom_count is not None and axiom_count != len(axioms):
        issues.append(
            f"bridge_axioms.json export_metadata.axiom_count {axiom_count} "
            f"!= bridge_axioms length {len(axioms)}"
        )

    average_sources = export_meta.get("average_sources_per_axiom")
    if average_sources is not None:
        sources = [len(ax.get("evidence_sources", [])) for ax in axioms]
        actual_avg = round(sum(sources) / len(sources), 1) if sources else 0.0
        expected_avg = round(float(average_sources), 1)
        if actual_avg != expected_avg:
            issues.append(
                f"bridge_axioms.json average_sources_per_axiom {average_sources} "
                f"!= computed {actual_avg}"
            )

    return issues


def main() -> int:
    issues: list[str] = []

    try:
        registry = load_json(REGISTRY_PATH)
        corpus = load_json(CORPUS_PATH)
        entities = load_json(ENTITIES_PATH)
        relationships = load_json(RELATIONSHIPS_PATH)
        axioms = load_json(AXIOMS_PATH)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    issues.extend(validate_document_corpus(registry, corpus))
    issues.extend(validate_entities(entities))
    issues.extend(validate_relationships(relationships))
    issues.extend(validate_axioms(axioms))

    if issues:
        print("EXPORT VALIDATION: FAILED")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("EXPORT VALIDATION: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
