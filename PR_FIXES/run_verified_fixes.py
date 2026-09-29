#!/usr/bin/env python3
"""Replay frozen PR-review findings through the Strix verified-fix runtime."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median
from typing import Any


EVAL_ROOT = Path(os.environ.get("STRIX_BENCHMARK_SOURCE", "/home/ubuntu/pr-fix-eval"))
OSS_ROOT = Path(
    os.environ.get("STRIX_OSS_ROOT", "/home/ubuntu/worktrees/strix-fix-controller")
).resolve()
PRO_ROOT = Path(
    os.environ.get("STRIX_PRO_ROOT", "/home/ubuntu/worktrees/strix-pro-repair-loop")
).resolve()
REPLAY_ROOT = Path("/home/ubuntu/verified-fix-benchmark/replay")
CASE_ROOT = REPLAY_ROOT / "cases"
RESULT_ROOT = REPLAY_ROOT / "results"
HISTORICAL_BASELINE_CORRECT = 66

for runtime_root, marker in (
    (OSS_ROOT, "strix/fix/prepare.py"),
    (PRO_ROOT, "strix_pro/fix_runtime.py"),
):
    if not (runtime_root / marker).is_file():
        raise RuntimeError(f"Selected runtime root is invalid: {runtime_root}")

sys.path.insert(0, str(OSS_ROOT))
sys.path.insert(0, str(PRO_ROOT))

from strix.config import load_settings  # noqa: E402
from strix.config.models import configure_sdk_model_defaults  # noqa: E402
from strix.fix import (  # noqa: E402
    FixPreparationRequestV1,
    PreparationState,
    SourceIdentity,
    SourceIdentityKind,
    candidate_from_legacy_report,
)
from strix.fix.locations import anchor_candidate  # noqa: E402

from strix_pro.fix_runtime import run_isolated_fix_preparation  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay frozen PR-review findings through Strix + Strix Pro."
    )
    parser.add_argument("--from", dest="start", type=int, default=1)
    parser.add_argument("--to", dest="end", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--keep-workspaces",
        action="store_true",
        help="Retain mutated repository workspaces after recording patches.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run the fixed two-case smoke gate instead of the requested range.",
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Validate the frozen cohort and selected runtimes without running cases.",
    )
    parser.add_argument(
        "--no-network",
        action="store_true",
        help="Disable dependency installation; production requests enable it.",
    )
    return parser.parse_args()


def _load_cohort() -> list[dict[str, Any]]:
    payload = json.loads((EVAL_ROOT / "cohort.json").read_text(encoding="utf-8"))
    if not isinstance(payload, list) or len(payload) != 100:
        raise RuntimeError("Expected the frozen 100-case cohort.")
    return payload


def _case_label(case_number: int) -> str:
    return f"{case_number:02d}"


def _archive_path(case: dict[str, Any]) -> Path:
    repository = str(case["repository_full_name"]).replace("/", "__")
    path = EVAL_ROOT / "archives" / f"{repository}__{case['head_sha']}.tar.gz"
    if not path.is_file():
        raise FileNotFoundError(f"Frozen archive is missing: {path}")
    return path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _git_identity(repository: Path) -> dict[str, Any]:
    def run(*arguments: str) -> str:
        completed = subprocess.run(  # noqa: S603
            ["/usr/bin/git", *arguments],
            cwd=repository,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return completed.stdout.strip()

    return {
        "path": str(repository),
        "head": run("rev-parse", "HEAD"),
        "branch": run("branch", "--show-current"),
        "dirty": bool(run("status", "--porcelain")),
    }


def _runtime_identity() -> dict[str, Any]:
    try:
        strix_version = importlib.metadata.version("strix-agent")
    except importlib.metadata.PackageNotFoundError:
        strix_version = None
    try:
        pro_version = importlib.metadata.version("strix-pro")
    except importlib.metadata.PackageNotFoundError:
        pro_version = None
    return {
        "harness_sha256": _sha256_file(Path(__file__)),
        "cohort_sha256": _sha256_file(EVAL_ROOT / "cohort.json"),
        "python": sys.executable,
        "model": os.environ.get("STRIX_LLM"),
        "oss": {
            **_git_identity(OSS_ROOT),
            "version": strix_version,
            "module": str(Path(sys.modules["strix"].__file__).resolve()),
        },
        "pro": {
            **_git_identity(PRO_ROOT),
            "version": pro_version,
            "module": str(Path(sys.modules["strix_pro"].__file__).resolve()),
        },
    }


def _run_git(workspace: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Strix Benchmark",
        "GIT_AUTHOR_EMAIL": "benchmark@strix.invalid",
        "GIT_COMMITTER_NAME": "Strix Benchmark",
        "GIT_COMMITTER_EMAIL": "benchmark@strix.invalid",
    }
    return subprocess.run(  # noqa: S603
        ["/usr/bin/git", *arguments],
        cwd=workspace,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )


def _prepare_workspace(case_number: int, *, force: bool) -> Path:
    label = _case_label(case_number)
    workspace = CASE_ROOT / label / "workspace"
    if workspace.exists():
        if not force:
            return workspace
        shutil.rmtree(workspace)
    workspace.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        EVAL_ROOT / "cases" / label / "source",
        workspace,
        symlinks=True,
    )
    _run_git(workspace, "init", "-q")
    _run_git(workspace, "add", "-A")
    _run_git(workspace, "commit", "-q", "-m", "Frozen benchmark source")
    return workspace


def _build_request(
    case: dict[str, Any],
    archive_digest: str,
    *,
    network_allowed: bool,
) -> FixPreparationRequestV1:
    source_identity = SourceIdentity(
        kind=SourceIdentityKind.ARCHIVE,
        value=archive_digest,
        repository=str(case["repository_full_name"]),
    )
    candidate = candidate_from_legacy_report(
        {
            "technical_analysis": case.get("description"),
            "remediation_steps": case.get("remediation_steps"),
            "code_locations": case.get("code_locations"),
            "evidence": case.get("evidence"),
        },
        source_identity=source_identity,
    )
    if candidate is None:
        raise RuntimeError("The frozen finding did not produce a fix candidate.")
    return FixPreparationRequestV1(
        organization_id=case.get("organization_id"),
        scan_id=str(case["pr_review_id"]),
        finding_id=str(case["id"]),
        repository_id=str(case["repository_full_name"]),
        candidate=candidate,
        max_repair_attempts=2,
        timeout_seconds=1800,
        network_allowed=network_allowed,
        credentials_allowed=[],
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _artifact_validation(  # noqa: PLR0911
    artifact_path: Path,
    result: dict[str, Any],
) -> dict[str, Any]:
    if not artifact_path.is_file():
        return {"valid": False, "reason": "artifact_missing"}
    try:
        with zipfile.ZipFile(artifact_path) as archive:
            names = set(archive.namelist())
            manifest = json.loads(archive.read("manifest.json"))
            if manifest != result.get("final_file_manifest"):
                return {"valid": False, "reason": "manifest_mismatch"}
            for entry in manifest:
                if entry["operation"] == "delete":
                    continue
                member = f"files/{entry['path']}"
                if member not in names:
                    return {
                        "valid": False,
                        "reason": "file_missing",
                        "path": entry["path"],
                    }
                digest = hashlib.sha256(archive.read(member)).hexdigest()
                if digest != entry.get("resulting_sha256"):
                    return {
                        "valid": False,
                        "reason": "resulting_hash_mismatch",
                        "path": entry["path"],
                    }
            if "changes.patch" not in names:
                return {"valid": False, "reason": "patch_missing"}
    except (OSError, KeyError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        return {"valid": False, "reason": f"{type(error).__name__}: {error}"}
    return {"valid": True, "reason": None}


def _write_diff(workspace: Path, destination: Path) -> None:
    completed = _run_git(workspace, "diff", "--binary", "HEAD", "--")
    destination.write_text(completed.stdout, encoding="utf-8")


async def _run_case(
    case_number: int,
    case: dict[str, Any],
    *,
    force: bool,
    network_allowed: bool,
    runtime_identity: dict[str, Any],
    keep_workspace: bool,
) -> dict[str, Any]:
    label = _case_label(case_number)
    result_path = RESULT_ROOT / f"{label}.json"
    if result_path.is_file() and not force:
        existing = json.loads(result_path.read_text(encoding="utf-8"))
        if existing.get("runtime_identity") == runtime_identity:
            return existing
        force = True

    started_at = datetime.now(UTC)
    started = time.monotonic()
    case_output = CASE_ROOT / label
    case_output.mkdir(parents=True, exist_ok=True)
    artifact_path = case_output / "prepared-fix.zip"
    workspace = _prepare_workspace(case_number, force=force)
    archive_path = _archive_path(case)
    archive_digest = _sha256_file(archive_path)
    request = _build_request(
        case,
        archive_digest,
        network_allowed=network_allowed,
    )
    anchored_candidate, anchor_results = anchor_candidate(workspace, request.candidate)
    request_path = case_output / "request.json"
    request_path.write_text(request.model_dump_json(indent=2), encoding="utf-8")

    record: dict[str, Any] = {
        "case": case_number,
        "finding_id": case["id"],
        "pr_review_id": case["pr_review_id"],
        "repository_full_name": case["repository_full_name"],
        "pr_number": case["pr_number"],
        "original_head_sha": case["head_sha"],
        "source_archive": archive_path.name,
        "source_archive_sha256": archive_digest,
        "source_identity_validated": None,
        "candidate_digest": request.candidate.digest(),
        "candidate": request.candidate.model_dump(mode="json"),
        "anchor_results": [
            {
                "file": item.location.file,
                "status": str(item.status),
                "matches": list(item.matches),
                "anchored_start_line": item.location.start_line,
                "anchored_end_line": item.location.end_line,
            }
            for item in anchor_results
        ],
        "anchored_candidate_digest": anchored_candidate.digest(),
        "preparation_state_transitions": ["preparing"],
        "draft_application": "pending",
        "automatic_pr_eligible": False,
        "artifact_validation": {"valid": False, "reason": "not_built"},
        "runtime_exception": None,
        "runtime_identity": runtime_identity,
    }

    try:
        result = await run_isolated_fix_preparation(
            request,
            workspace,
            restored_source_identity=archive_digest,
            artifact_path=artifact_path,
            attempt_id=f"benchmark-{case_number:03d}",
        )
        result_payload = result.model_dump(mode="json")
        record["result"] = result_payload
        record["attempt_history"] = result_payload.get("attempt_history", [])
        record["repair_turns_used"] = sum(
            int(attempt.get("repair", {}).get("turns_used", 0))
            for attempt in record["attempt_history"]
        )
        record["preparation_state_transitions"].append(result.state.value)
        record["source_identity_validated"] = result.state is not PreparationState.STALE
        if result.state is PreparationState.STALE or result.stop_reason.startswith(
            "One or more candidate locations"
        ):
            record["draft_application"] = "not_applied"
        else:
            record["draft_application"] = "applied"
        record["artifact_validation"] = _artifact_validation(artifact_path, result_payload)
        record["automatic_pr_eligible"] = (
            result.state is PreparationState.READY
            and bool(result.final_file_manifest)
            and record["artifact_validation"]["valid"]
        )
    except Exception as error:  # noqa: BLE001
        record["preparation_state_transitions"].append("failed")
        record["draft_application"] = "unknown"
        record["runtime_exception"] = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
        }

    try:
        _write_diff(workspace, case_output / "prepared-fix.patch")
    except subprocess.CalledProcessError as error:
        record["diff_error"] = error.stderr[-4000:]
    finished_at = datetime.now(UTC)
    record["started_at"] = started_at.isoformat()
    record["finished_at"] = finished_at.isoformat()
    record["wall_clock_seconds"] = time.monotonic() - started
    _write_json(result_path, record)
    if not keep_workspace:
        shutil.rmtree(workspace)
    print(  # noqa: T201
        f"{label}: "
        f"{record.get('result', {}).get('state', 'runtime_error')} "
        f"({record['wall_clock_seconds']:.1f}s)",
        flush=True,
    )
    return record


async def _main() -> None:
    args = _parse_args()
    if not 1 <= args.start <= args.end <= 100:
        raise SystemExit("--from and --to must select cases within 1..100")
    if args.concurrency < 1:
        raise SystemExit("--concurrency must be positive")
    cohort = _load_cohort()
    runtime_identity = _runtime_identity()
    _write_json(RESULT_ROOT / "runtime-identity.json", runtime_identity)
    if args.preflight:
        print(json.dumps(runtime_identity, indent=2, sort_keys=True))  # noqa: T201
        return
    configure_sdk_model_defaults(load_settings())
    semaphore = asyncio.Semaphore(args.concurrency)

    async def bounded(case_number: int) -> dict[str, Any]:
        async with semaphore:
            return await _run_case(
                case_number,
                cohort[case_number - 1],
                force=args.force,
                network_allowed=not args.no_network,
                runtime_identity=runtime_identity,
                keep_workspace=args.keep_workspaces,
            )

    selected = [1, 2] if args.smoke else list(range(args.start, args.end + 1))
    results = await asyncio.gather(*(bounded(case_number) for case_number in selected))
    summary = {
        "cases": selected,
        "count": len(results),
        "states": {},
        "automatic_pr_eligible": sum(
            bool(result.get("automatic_pr_eligible")) for result in results
        ),
        "artifact_validation_failures": sum(
            not result.get("artifact_validation", {}).get("valid", False)
            for result in results
            if result.get("result", {}).get("final_file_manifest")
        ),
        "runtime_exceptions": sum(bool(result.get("runtime_exception")) for result in results),
        "runtime_identity": runtime_identity,
        "historical_baseline_correct": HISTORICAL_BASELINE_CORRECT,
    }
    for result in results:
        state = result.get("result", {}).get("state", "runtime_error")
        summary["states"][state] = summary["states"].get(state, 0) + 1
    durations = sorted(float(result["wall_clock_seconds"]) for result in results)
    summary["timing_seconds"] = {
        "minimum": durations[0],
        "maximum": durations[-1],
        "mean": mean(durations),
        "median": median(durations),
        "p95": durations[min(len(durations) - 1, int(len(durations) * 0.95))],
        "sum": sum(durations),
    }
    summary["ready_delta_vs_historical_correct"] = (
        summary["automatic_pr_eligible"] - HISTORICAL_BASELINE_CORRECT
        if len(selected) == 100
        else None
    )
    _write_json(
        RESULT_ROOT / f"summary-{selected[0]:03d}-{selected[-1]:03d}.json",
        summary,
    )


if __name__ == "__main__":
    asyncio.run(_main())
