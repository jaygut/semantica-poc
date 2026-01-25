#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from registry_filters import looks_like_asset
from run_manifest import write_run_manifest

BASE_DIR = Path(__file__).resolve().parent.parent
REGISTRY_PATH = BASE_DIR / ".claude/registry/document_index.json"
REPORT_PATH = BASE_DIR / "data/registry_purge_report.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Purge asset-like entries from registry.")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> int:
    started_at = datetime.now(timezone.utc)
    args = parse_args()

    if not REGISTRY_PATH.exists():
        print(f"Missing registry: {REGISTRY_PATH}")
        return 1

    registry = json.loads(REGISTRY_PATH.read_text())
    documents = registry.get("documents", {})
    removed = []

    for doc_id, doc in list(documents.items()):
        if looks_like_asset(doc):
            removed.append(doc_id)
            if args.apply:
                documents.pop(doc_id, None)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "apply": bool(args.apply),
        "removed_count": len(removed),
        "removed_ids": removed,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")

    if args.apply:
        registry["documents"] = documents
        try:
            from validate_registry import recalculate_statistics

            registry = recalculate_statistics(registry)
        except Exception:
            registry["document_count"] = len(documents)
        registry["updated_at"] = datetime.now(timezone.utc).isoformat()
        REGISTRY_PATH.write_text(json.dumps(registry, indent=2) + "\n")

    manifest_path = write_run_manifest(
        script_name=Path(__file__).stem,
        args=vars(args),
        inputs={"registry_path": str(REGISTRY_PATH)},
        outputs={"purge_report": str(REPORT_PATH), "removed_count": len(removed)},
        started_at=started_at,
        ended_at=datetime.now(timezone.utc),
    )

    print("REGISTRY ASSET PURGE COMPLETE")
    print(f"  Removed:      {len(removed)}")
    print(f"  Applied:      {args.apply}")
    print(f"  Report:       {REPORT_PATH}")
    print(f"  Run manifest: {manifest_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
