#!/usr/bin/env python3
"""Create a deterministic severity-stratified slice of a frozen PR-fix cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_QUOTAS = {
    "critical": 1,
    "high": 2,
    "medium": 5,
    "low": 7,
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--exclude-through", type=int, default=15)
    return parser.parse_args()


def _score(seed: str, case: dict[str, Any]) -> str:
    identity = f"{seed}:{case['id']}:{case['head_sha']}"
    return hashlib.sha256(identity.encode()).hexdigest()


def _load_candidates(source: Path, exclude_through: int) -> list[dict[str, Any]]:
    cohort = json.loads((source / "cohort.json").read_text(encoding="utf-8"))
    candidates = [
        {**case, "_source_index": index}
        for index, case in enumerate(cohort, start=1)
        if index > exclude_through
    ]
    if len(candidates) < sum(DEFAULT_QUOTAS.values()):
        raise RuntimeError("Not enough cases remain after exclusions.")
    return candidates


def _select(candidates: list[dict[str, Any]], seed: str) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for severity, quota in DEFAULT_QUOTAS.items():
        ranked = sorted(
            (case for case in candidates if case["severity"] == severity),
            key=lambda case: _score(seed, case),
        )
        chosen: list[dict[str, Any]] = []
        repositories: set[str] = set()
        for case in ranked:
            repository = case["repository_full_name"]
            if repository in repositories:
                continue
            chosen.append(case)
            repositories.add(repository)
            if len(chosen) == quota:
                break
        for case in ranked:
            if len(chosen) == quota:
                break
            if case not in chosen:
                chosen.append(case)
        if len(chosen) != quota:
            raise RuntimeError(f"Could not fill the {severity} quota.")
        selected.extend(chosen)
    return sorted(selected, key=lambda case: int(case["recency_rank"]))


def _write_slice(
    source: Path,
    output: Path,
    selected: list[dict[str, Any]],
    seed: str,
    exclude_through: int,
) -> None:
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    (output / "cases").mkdir(parents=True)
    (output / "cohort.json").write_text(
        json.dumps(
            [
                {key: value for key, value in case.items() if key != "_source_index"}
                for case in selected
            ],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (output / "archives").symlink_to(source / "archives", target_is_directory=True)

    entries = []
    for slice_index, case in enumerate(selected, start=1):
        source_index = int(case["_source_index"])
        destination = output / "cases" / f"{slice_index:02d}"
        destination.mkdir()
        shutil.copy2(
            source / "cases" / f"{source_index:02d}" / "case.json", destination
        )
        (destination / "source").symlink_to(
            source / "cases" / f"{source_index:02d}" / "source",
            target_is_directory=True,
        )
        entries.append(
            {
                "slice_index": slice_index,
                "source_index": source_index,
                "finding_id": case["id"],
                "repository_full_name": case["repository_full_name"],
                "head_sha": case["head_sha"],
                "severity": case["severity"],
                "cwe": case.get("cwe") or [],
                "title": case["title"],
                "selection_score": _score(seed, case),
            }
        )

    manifest = {
        "method": "severity quotas, SHA-256 ranking, unique repositories preferred",
        "seed": seed,
        "excluded_source_indices": list(range(1, exclude_through + 1)),
        "quotas": DEFAULT_QUOTAS,
        "selected_severity_counts": dict(
            Counter(case["severity"] for case in selected)
        ),
        "cases": entries,
    }
    (output / "selection-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = _parse_args()
    candidates = _load_candidates(args.source, args.exclude_through)
    selected = _select(candidates, args.seed)
    _write_slice(
        args.source.resolve(),
        args.output.resolve(),
        selected,
        args.seed,
        args.exclude_through,
    )
    print((args.output / "selection-manifest.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
