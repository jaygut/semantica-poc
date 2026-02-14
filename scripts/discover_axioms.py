#!/usr/bin/env python3
"""CLI for axiom discovery pipeline.

Usage:
    # Discover candidate axioms from the paper library
    python scripts/discover_axioms.py --min-sources 3 --output candidates.json

    # List candidates by status
    python scripts/discover_axioms.py --list --status candidate

    # Review a specific candidate
    python scripts/discover_axioms.py --review --candidate CAND-017 --accept --reviewer "Jane Doe"
    python scripts/discover_axioms.py --review --candidate CAND-017 --reject --reason "Insufficient evidence"
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from maris.discovery.pipeline import DiscoveryPipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MARIS Axiom Discovery Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Discovery mode
    parser.add_argument(
        "--min-sources",
        type=int,
        default=3,
        help="Minimum independent sources for a candidate (default: 3)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for discovered candidates (JSON)",
    )
    parser.add_argument(
        "--registry",
        type=str,
        default=None,
        help="Path to document_index.json (default: .claude/registry/document_index.json)",
    )

    # List mode
    parser.add_argument(
        "--list",
        action="store_true",
        help="List candidates from a previous run",
    )
    parser.add_argument(
        "--status",
        type=str,
        choices=["candidate", "accepted", "rejected"],
        default=None,
        help="Filter candidates by status",
    )

    # Review mode
    parser.add_argument("--review", action="store_true", help="Review a candidate")
    parser.add_argument("--candidate", type=str, help="Candidate ID to review")
    parser.add_argument("--accept", action="store_true", help="Accept the candidate")
    parser.add_argument("--reject", action="store_true", help="Reject the candidate")
    parser.add_argument("--reviewer", type=str, default="anonymous", help="Reviewer name")
    parser.add_argument("--reason", type=str, default="", help="Rejection reason")

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    # List mode: read from output file
    if args.list:
        _list_candidates(args)
        return

    # Review mode: accept/reject a candidate
    if args.review:
        _review_candidate(args)
        return

    # Discovery mode (default)
    _run_discovery(args)


def _run_discovery(args: argparse.Namespace) -> None:
    """Run the full discovery pipeline."""
    pipeline = DiscoveryPipeline(
        min_sources=args.min_sources,
        registry_path=args.registry,
    )

    # Load corpus
    count = pipeline.load_corpus()
    if count == 0:
        print("No papers found in registry. Check --registry path.")
        sys.exit(1)

    print(f"Loaded {count} papers from registry")

    # Run pipeline
    candidates = pipeline.run()

    # Print summary
    summary = pipeline.summary()
    print("\nPipeline Summary:")
    print(f"  Papers processed: {summary['papers_loaded']}")
    print(f"  Raw patterns detected: {summary['raw_patterns']}")
    print(f"  Aggregated groups: {summary['aggregated_groups']}")
    print(f"  Candidate axioms: {summary['candidates']}")

    if candidates:
        print("\nCandidate Axioms:")
        for c in candidates:
            print(f"  {c.candidate_id}: {c.proposed_name}")
            print(f"    Mean coefficient: {c.mean_coefficient:.4f} [{c.ci_low:.4f}, {c.ci_high:.4f}]")
            print(f"    Studies: {c.n_studies}, DOIs: {len(c.supporting_dois)}")
            if c.conflicts:
                print(f"    CONFLICTS: {c.conflicts}")
    else:
        print("\nNo candidate axioms discovered at the current threshold.")

    # Export if output specified
    if args.output:
        pipeline.export_candidates(args.output)
        print(f"\nExported to {args.output}")


def _list_candidates(args: argparse.Namespace) -> None:
    """List candidates from a JSON file."""
    if not args.output:
        print("Use --output to specify the candidates file to list from.")
        sys.exit(1)

    path = Path(args.output)
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    with open(path) as f:
        data = json.load(f)

    candidates = data.get("candidates", [])
    if args.status:
        candidates = [c for c in candidates if c.get("status") == args.status]

    print(f"Candidates ({len(candidates)}):")
    for c in candidates:
        print(f"  {c['candidate_id']}: {c['proposed_name']} [{c['status']}]")
        print(f"    Coefficient: {c['mean_coefficient']:.4f} [{c['ci_low']:.4f}, {c['ci_high']:.4f}]")
        print(f"    Studies: {c['n_studies']}")


def _review_candidate(args: argparse.Namespace) -> None:
    """Review (accept/reject) a candidate."""
    if not args.candidate:
        print("Specify --candidate ID to review.")
        sys.exit(1)

    if not args.output:
        print("Specify --output file containing the candidates.")
        sys.exit(1)

    path = Path(args.output)
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    with open(path) as f:
        data = json.load(f)

    candidates = data.get("candidates", [])
    target = None
    for c in candidates:
        if c["candidate_id"] == args.candidate:
            target = c
            break

    if target is None:
        print(f"Candidate {args.candidate} not found.")
        sys.exit(1)

    if args.accept:
        target["status"] = "accepted"
        target["reviewed_by"] = args.reviewer
        target["review_notes"] = args.reason or "Accepted"
        print(f"Accepted {args.candidate}")
    elif args.reject:
        target["status"] = "rejected"
        target["reviewed_by"] = args.reviewer
        target["review_notes"] = args.reason
        print(f"Rejected {args.candidate}: {args.reason}")
    else:
        print("Specify --accept or --reject")
        sys.exit(1)

    with open(path, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    main()
