#!/usr/bin/env python3
from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "data/run_manifests"


def _iso(dt: datetime | None) -> str:
    stamp = dt or datetime.now(timezone.utc)
    return stamp.astimezone(timezone.utc).isoformat()


def _git_metadata(base_dir: Path) -> dict[str, Any]:
    commit = None
    dirty = None
    try:
        commit = (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=base_dir)
            .decode()
            .strip()
        )
        status = (
            subprocess.check_output(["git", "status", "--porcelain"], cwd=base_dir)
            .decode()
            .strip()
        )
        dirty = bool(status)
    except Exception:
        pass
    return {"commit": commit, "dirty": dirty}


def write_run_manifest(
    *,
    script_name: str,
    args: dict[str, Any],
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
    output_dir: Path | None = None,
) -> Path:
    started = started_at or datetime.now(timezone.utc)
    finished = ended_at or datetime.now(timezone.utc)
    run_id = started.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    manifest = {
        "run_id": run_id,
        "script": script_name,
        "started_at": _iso(started),
        "ended_at": _iso(finished),
        "args": args,
        "inputs": inputs or {},
        "outputs": outputs or {},
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "git": _git_metadata(BASE_DIR),
    }

    target_dir = output_dir or DEFAULT_OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    output_path = target_dir / f"{script_name}_{run_id}.json"
    output_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return output_path
