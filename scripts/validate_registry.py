#!/usr/bin/env python3
"""
Registry Validation Script for MARIS

Performs comprehensive validation of the document registry:
- Document count matches
- Statistics integrity
- Orphan file detection
- Required field checks
- DOI coverage analysis
- Duplicate detection

Usage:
    python scripts/validate_registry.py
    python scripts/validate_registry.py --fix  # Auto-fix issues where possible
    python scripts/validate_registry.py --verbose
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import re

# Paths
REGISTRY_DIR = Path(__file__).parent.parent / ".claude/registry"
DOCUMENTS_DIR = REGISTRY_DIR / "documents"
INDEX_FILE = REGISTRY_DIR / "document_index.json"


def load_index() -> dict:
    """Load the document index."""
    return json.loads(INDEX_FILE.read_text())


def save_index(index: dict):
    """Save the document index."""
    index['updated_at'] = datetime.now(timezone.utc).isoformat()
    INDEX_FILE.write_text(json.dumps(index, indent=2))


def recalculate_statistics(index: dict) -> dict:
    """Rebuild all statistics by iterating through documents."""
    stats = {
        'by_tier': {'T1': 0, 'T2': 0, 'T3': 0, 'T4': 0},
        'by_type': {},
        'by_domain': {},
        'by_habitat': {}
    }

    for doc_id, doc in index['documents'].items():
        # Count by tier
        tier = doc.get('source_tier', 'T4')
        if tier in stats['by_tier']:
            stats['by_tier'][tier] += 1
        else:
            stats['by_tier'][tier] = 1

        # Count by type
        doc_type = doc.get('document_type', 'unknown')
        stats['by_type'][doc_type] = stats['by_type'].get(doc_type, 0) + 1

        # Count by domain tags
        for tag in doc.get('domain_tags', []):
            stats['by_domain'][tag] = stats['by_domain'].get(tag, 0) + 1

        # Count by habitat
        habitat = doc.get('habitat')
        if habitat:
            stats['by_habitat'][habitat] = stats['by_habitat'].get(habitat, 0) + 1
        else:
            # Check domain_tags for habitat info
            found_habitat = False
            for tag in doc.get('domain_tags', []):
                if tag in ['coral_reef', 'kelp_forest', 'seagrass', 'mangrove']:
                    stats['by_habitat'][tag] = stats['by_habitat'].get(tag, 0) + 1
                    found_habitat = True
                    break
            if not found_habitat:
                stats['by_habitat']['general'] = stats['by_habitat'].get('general', 0) + 1

    index['statistics'] = stats
    index['document_count'] = len(index['documents'])

    return index


def infer_doi_from_url(url: str) -> Optional[str]:
    """Infer DOI from URL using publisher-specific patterns."""
    if not url:
        return None

    # Direct DOI patterns
    doi_patterns = [
        r'doi\.org/(10\.\d{4,}/[^\s?#]+)',
        r'/doi/(?:abs/|full/|pdf/)?(10\.\d{4,}/[^\s?#]+)',
        r'id=(10\.\d{4,}/[^\s&#]+)',
    ]

    for pattern in doi_patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1).rstrip('.')

    # Nature
    if 'nature.com' in url:
        match = re.search(r'/articles?/([a-z0-9\-]+)(?:\?|$)', url, re.IGNORECASE)
        if match:
            return f"10.1038/{match.group(1)}"

    # PLOS
    if 'plos.org' in url:
        match = re.search(r'id=(10\.1371/[^\s&#]+)', url)
        if match:
            return match.group(1)

    # Wiley
    if 'wiley.com' in url:
        match = re.search(r'/doi/(?:abs/|full/|pdf/)?(10\.\d{4,}/[^\s?#]+)', url)
        if match:
            return match.group(1)

    # Frontiers
    if 'frontiersin.org' in url:
        match = re.search(r'/articles/(10\.3389/[^\s?#]+)', url)
        if match:
            return match.group(1)

    return None


def validate_registry(fix: bool = False, verbose: bool = False) -> dict:
    """Comprehensive validation of registry integrity."""
    index = load_index()
    issues = []
    warnings = []
    fixes_applied = []

    print("=" * 60)
    print("MARIS Registry Validation Report")
    print("=" * 60)

    # Check 1: Document count
    actual_count = len(index['documents'])
    stated_count = index.get('document_count', 0)
    print(f"\n[1] Document Count: {actual_count}")

    if actual_count != stated_count:
        issues.append(f"Document count mismatch: stated {stated_count}, actual {actual_count}")
        if fix:
            index['document_count'] = actual_count
            fixes_applied.append("Fixed document_count")

    # Check 2: Statistics sums
    print(f"\n[2] Statistics Validation:")
    tier_sum = sum(index.get('statistics', {}).get('by_tier', {}).values())
    print(f"    Tier sum: {tier_sum}")

    if tier_sum != actual_count:
        issues.append(f"Tier statistics sum ({tier_sum}) doesn't match document count ({actual_count})")
        if fix:
            index = recalculate_statistics(index)
            fixes_applied.append("Recalculated all statistics")

    type_sum = sum(index.get('statistics', {}).get('by_type', {}).values())
    print(f"    Type sum: {type_sum}")
    if type_sum != actual_count:
        issues.append(f"Type statistics sum ({type_sum}) doesn't match document count ({actual_count})")

    # Check 3: Orphan files
    print(f"\n[3] Orphan File Check:")
    orphan_files = []
    if DOCUMENTS_DIR.exists():
        file_ids = {f.stem for f in DOCUMENTS_DIR.glob('*.json')}
        index_ids = set(index['documents'].keys())

        orphan_files = list(file_ids - index_ids)
        if orphan_files:
            issues.append(f"Orphan document files: {orphan_files}")
            print(f"    Found {len(orphan_files)} orphan files")
            if fix:
                for orphan_id in orphan_files:
                    orphan_path = DOCUMENTS_DIR / f"{orphan_id}.json"
                    orphan_path.unlink()
                    fixes_applied.append(f"Deleted orphan: {orphan_id}")
        else:
            print("    No orphan files found ✓")

    # Check 4: Required fields
    print(f"\n[4] Required Fields Check:")
    required_fields = ['title', 'url', 'source_tier']
    missing_fields_count = 0

    for doc_id, doc in index['documents'].items():
        for field in required_fields:
            if not doc.get(field):
                warnings.append(f"{doc_id}: missing {field}")
                missing_fields_count += 1

    print(f"    Documents with missing required fields: {missing_fields_count}")

    # Check 5: DOI coverage and inference
    print(f"\n[5] DOI Coverage:")
    docs_with_doi = 0
    docs_missing_doi = 0
    inferred_dois = 0

    for doc_id, doc in index['documents'].items():
        if doc.get('doi'):
            docs_with_doi += 1
        else:
            docs_missing_doi += 1
            # Try to infer DOI
            inferred = infer_doi_from_url(doc.get('url', ''))
            if inferred:
                inferred_dois += 1
                if fix:
                    doc['doi'] = inferred
                    fixes_applied.append(f"Inferred DOI for {doc_id}: {inferred}")

    coverage = (docs_with_doi / actual_count * 100) if actual_count > 0 else 0
    potential_coverage = ((docs_with_doi + inferred_dois) / actual_count * 100) if actual_count > 0 else 0

    print(f"    Current DOI coverage: {docs_with_doi}/{actual_count} ({coverage:.1f}%)")
    print(f"    Inferrable DOIs: {inferred_dois}")
    print(f"    Potential coverage: {potential_coverage:.1f}%")

    # Check 6: Duplicate DOIs
    print(f"\n[6] Duplicate Detection:")
    doi_to_ids = {}
    duplicates = []

    for doc_id, doc in index['documents'].items():
        doi = doc.get('doi')
        if doi:
            if doi in doi_to_ids:
                duplicates.append({'doi': doi, 'ids': [doi_to_ids[doi], doc_id]})
            else:
                doi_to_ids[doi] = doc_id

    if duplicates:
        issues.append(f"Duplicate DOIs found: {len(duplicates)}")
        print(f"    Duplicate DOI groups: {len(duplicates)}")
        for dup in duplicates[:5]:  # Show first 5
            print(f"      {dup['doi']}: {dup['ids']}")
    else:
        print("    No duplicate DOIs ✓")

    # Check 7: Abstract coverage
    print(f"\n[7] Abstract Coverage:")
    docs_with_abstract = sum(1 for doc in index['documents'].values() if doc.get('abstract'))
    abstract_coverage = (docs_with_abstract / actual_count * 100) if actual_count > 0 else 0
    print(f"    Documents with abstracts: {docs_with_abstract}/{actual_count} ({abstract_coverage:.1f}%)")

    # Apply fixes if requested
    if fix and fixes_applied:
        save_index(index)
        print(f"\n[FIXES APPLIED] {len(fixes_applied)} changes:")
        for f in fixes_applied[:10]:
            print(f"    - {f}")
        if len(fixes_applied) > 10:
            print(f"    ... and {len(fixes_applied) - 10} more")

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    is_valid = len(issues) == 0
    print(f"Status: {'✓ VALID' if is_valid else '✗ ISSUES FOUND'}")
    print(f"Issues: {len(issues)}")
    print(f"Warnings: {len(warnings)}")

    if issues:
        print("\nIssues:")
        for issue in issues:
            print(f"  ✗ {issue}")

    if verbose and warnings:
        print(f"\nWarnings (first 20 of {len(warnings)}):")
        for w in warnings[:20]:
            print(f"  ! {w}")

    result = {
        'valid': is_valid,
        'document_count': actual_count,
        'doi_coverage_percent': round(coverage, 1),
        'abstract_coverage_percent': round(abstract_coverage, 1),
        'issues': issues,
        'warnings_count': len(warnings),
        'fixes_applied': fixes_applied if fix else [],
        'checked_at': datetime.now(timezone.utc).isoformat()
    }

    return result


def main():
    fix = '--fix' in sys.argv
    verbose = '--verbose' in sys.argv or '-v' in sys.argv

    result = validate_registry(fix=fix, verbose=verbose)

    # Exit with error code if issues found
    sys.exit(0 if result['valid'] else 1)


if __name__ == "__main__":
    main()
