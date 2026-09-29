#!/usr/bin/env python3
"""Replay frozen security findings through the Strix verified-fix runtime."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import io
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import zipfile
from collections import Counter
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median
from typing import Any


EVAL_ROOT = Path(os.environ.get("STRIX_BENCHMARK_SOURCE", "/home/ubuntu/pr-fix-eval"))
OSS_ROOT = Path(
    os.environ.get("STRIX_OSS_ROOT", "/home/ubuntu/worktrees/benchmark-rerun-v4-oss")
).resolve()
PRO_ROOT = Path(
    os.environ.get("STRIX_PRO_ROOT", "/home/ubuntu/worktrees/benchmark-rerun-v4-pro")
).resolve()
APP_ROOT = Path(
    os.environ.get("STRIX_APP_ROOT", "/home/ubuntu/worktrees/benchmark-rerun-v4-app")
).resolve()
REPLAY_ROOT = Path(
    os.environ.get(
        "STRIX_BENCHMARK_OUTPUT", "/home/ubuntu/verified-fix-benchmark/replay"
    )
)
CASE_ROOT = REPLAY_ROOT / "cases"
RESULT_ROOT = REPLAY_ROOT / "results"
HISTORICAL_BASELINE_CORRECT = 66

for runtime_root, marker in (
    (OSS_ROOT, "strix/fix/prepare.py"),
    (PRO_ROOT, "strix_pro/fix_runtime.py"),
    (APP_ROOT, "src/lib/fix-preparation/contracts.ts"),
):
    if not (runtime_root / marker).is_file():
        raise RuntimeError(f"Selected runtime root is invalid: {runtime_root}")

sys.path.insert(0, str(OSS_ROOT))
sys.path.insert(0, str(PRO_ROOT))

from strix.config import load_settings  # noqa: E402
from strix.config.models import configure_sdk_model_defaults  # noqa: E402
from strix.fix import (  # noqa: E402
    FindingContext,
    FixCandidateV1,
    FixPreparationRequestV1,
    PreparationState,
    ReproductionSpec,
    SourceIdentity,
    SourceIdentityKind,
    candidate_from_legacy_report,
)
from strix.fix.locations import anchor_candidate  # noqa: E402

from strix_pro import fix_runtime as fix_runtime_module  # noqa: E402
from strix_pro.fix_runtime import run_isolated_fix_preparation  # noqa: E402


_PROGRESS_PATH: ContextVar[Path | None] = ContextVar(
    "benchmark_progress_path", default=None
)


def _append_agent_trace(
    *,
    actor: str,
    kind: str,
    title: str,
    status: str = "completed",
    arguments: str = "",
    result: str = "",
    detail: str = "",
) -> None:
    progress_path = _PROGRESS_PATH.get()
    if progress_path is None:
        return
    trace_path = progress_path.parent / "agent-trace.jsonl"
    timestamp = datetime.now(UTC)
    event = {
        "id": f"{time.time_ns()}-{kind}",
        "timestamp": timestamp.isoformat(),
        "actor": actor,
        "kind": kind,
        "title": title,
        "status": status,
        "arguments": arguments[-6000:],
        "result": result[-12000:],
        "detail": detail[-2000:],
    }
    with trace_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True) + "\n")


def _telemetry_root(sandbox_workspace: str) -> Path:
    source_root = Path(sandbox_workspace).resolve()
    telemetry_root = source_root.parent / ".strix-benchmark"
    if telemetry_root.is_relative_to(source_root):
        raise RuntimeError("Benchmark telemetry must stay outside repository source.")
    return telemetry_root


def _initial_progress() -> dict[str, Any]:
    return {
        "attempt": 1,
        "current_stage": "patch",
        "latest_event": "The repair agent is inspecting the frozen workspace.",
        "stages": {
            "patch": {
                "status": "pending",
                "meta": "Waiting for the repair agent.",
                "detail": "",
            },
            "compile": {
                "status": "pending",
                "meta": "Waiting for patch.",
                "detail": "",
            },
            "unit": {
                "status": "pending",
                "meta": "Waiting for compilation.",
                "detail": "",
            },
            "verify": {
                "status": "pending",
                "meta": "Waiting for tests.",
                "detail": "",
            },
        },
        "updated_at": datetime.now(UTC).isoformat(),
    }


def _update_progress(
    stage: str,
    status: str,
    meta: str,
    *,
    detail: str = "",
    attempt: int | None = None,
    reset_stages: bool = False,
) -> None:
    path = _PROGRESS_PATH.get()
    if path is None:
        return
    progress = _initial_progress()
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                progress = loaded
        except (OSError, json.JSONDecodeError):
            pass
    if attempt is not None:
        progress["attempt"] = attempt
    if reset_stages:
        progress["stages"] = _initial_progress()["stages"]
    progress["current_stage"] = stage
    progress["latest_event"] = meta
    stages = progress.setdefault("stages", {})
    stages[stage] = {"status": status, "meta": meta, "detail": detail}
    progress["updated_at"] = datetime.now(UTC).isoformat()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(progress, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


_repair_call = fix_runtime_module.ManagedRepairAgent.__call__
_command_call = fix_runtime_module._RuntimeEnvironment.run_isolated_command
_review_call = fix_runtime_module.ManagedIndependentVerifier.__call__
_tool_trace_llm_start = fix_runtime_module._ToolTrace.on_llm_start
_tool_trace_llm_end = fix_runtime_module._ToolTrace.on_llm_end
_tool_trace_tool_start = fix_runtime_module._ToolTrace.on_tool_start
_tool_trace_tool_end = fix_runtime_module._ToolTrace.on_tool_end


async def _instrumented_llm_start(
    self: Any,
    context: Any,
    agent: Any,
    system_prompt: str | None,
    input_items: Any,
) -> None:
    await _tool_trace_llm_start(
        self,
        context,
        agent,
        system_prompt,
        input_items,
    )
    _append_agent_trace(
        actor=str(agent.name),
        kind="model",
        title=f"Model turn {self.turns}",
        status="running",
        detail="The agent is choosing its next action.",
    )


async def _instrumented_llm_end(
    self: Any,
    context: Any,
    agent: Any,
    response: Any,
) -> None:
    await _tool_trace_llm_end(self, context, agent, response)
    _append_agent_trace(
        actor=str(agent.name),
        kind="model",
        title=f"Model turn {self.turns}",
        detail="The model response was received.",
    )


async def _instrumented_tool_start(
    self: Any,
    context: Any,
    agent: Any,
    tool: Any,
) -> None:
    await _tool_trace_tool_start(self, context, agent, tool)
    _append_agent_trace(
        actor=str(agent.name),
        kind="tool",
        title=str(getattr(tool, "name", type(tool).__name__)),
        status="running",
        arguments=str(getattr(context, "tool_arguments", "") or ""),
        detail="Tool call started.",
    )


async def _instrumented_tool_end(
    self: Any,
    context: Any,
    agent: Any,
    tool: Any,
    result: Any,
) -> None:
    await _tool_trace_tool_end(self, context, agent, tool, result)
    _append_agent_trace(
        actor=str(agent.name),
        kind="tool",
        title=str(getattr(tool, "name", type(tool).__name__)),
        arguments=str(getattr(context, "tool_arguments", "") or ""),
        result=str(result),
        detail="Tool call completed.",
    )


async def _instrumented_repair(
    self: Any, context: Any, previous_checks: Any
) -> Any:
    _append_agent_trace(
        actor="Repair agent",
        kind="handoff",
        title=f"Repair attempt {context.attempt}",
        status="running",
        detail="The controller handed the case to the repair agent.",
    )
    _update_progress(
        "patch",
        "running",
        f"Repair attempt {context.attempt} is building the patch.",
        attempt=context.attempt,
        reset_stages=True,
    )
    outcome = await _repair_call(self, context, previous_checks)
    changed = bool(
        subprocess.run(
            ["/usr/bin/git", "status", "--porcelain=v1"],
            cwd=self.environment.workspace,
            check=True,
            capture_output=True,
            timeout=30,
        ).stdout.strip()
    )
    status = "passed" if changed else "failed"
    _update_progress(
        "patch",
        status,
        "Patch submitted." if changed else "No changed files were submitted.",
        detail=str(outcome.summary or ""),
        attempt=context.attempt,
    )
    _append_agent_trace(
        actor="Repair agent",
        kind="handoff",
        title=f"Repair attempt {context.attempt} returned",
        status="completed" if changed else "failed",
        result=str(outcome.summary or ""),
        detail="The repair agent returned control to the controller.",
    )
    return outcome


async def _instrumented_command(
    self: Any, command: Any, *, protect_source: bool = False
) -> Any:
    purpose = str(command.purpose)
    stage = {
        "quality": "compile",
        "unit": "unit",
        "regression": "verify",
        "security": "verify",
    }.get(purpose)
    if command.name == "Repository setup" or (
        purpose == "quality" and not command.required
    ):
        stage = None
    if stage is not None:
        label = {
            "compile": "Compile or quality check",
            "unit": "Customer unit tests",
            "verify": "Regression validation",
        }[stage]
        progress_path = _PROGRESS_PATH.get()
        case_label = progress_path.parent.name if progress_path is not None else "unknown"
        await self.initialize()
        telemetry_root = _telemetry_root(self.sandbox_workspace)
        await self.session.exec(
            "mkdir",
            "-p",
            str(telemetry_root),
            shell=False,
            timeout=30,
        )
        await self.session.write(
            telemetry_root / "case",
            io.BytesIO(case_label.encode()),
        )
        await self.session.write(
            telemetry_root / "stage",
            io.BytesIO(stage.encode()),
        )
        log_path = str(telemetry_root / f"{stage}.log")
        status_result = await self.session.exec(
            "git",
            "-C",
            self.sandbox_workspace,
            "status",
            "--porcelain=v1",
            shell=False,
            timeout=30,
        )
        if not int(status_result.exit_code) and (status_result.stdout or b"").strip():
            _update_progress(
                "patch",
                "passed",
                "The patch is ready for validation.",
            )
        _update_progress(
            stage,
            "running",
            f"{label} is running.",
            detail=f"{command.name}: {' '.join(command.argv)}",
        )
        wrapped_command = command.model_copy(
            update={
                "argv": [
                    "bash",
                    "-o",
                    "pipefail",
                    "-c",
                    'log=$1; shift; : > "$log"; "$@" 2>&1 | tee -a "$log"',
                    "strix-live-log",
                    log_path,
                    *command.argv,
                ]
            }
        )
    else:
        wrapped_command = command
    result = await _command_call(
        self, wrapped_command, protect_source=protect_source
    )
    if stage is not None:
        result = result.model_copy(update={"argv": command.argv})
    if stage is not None:
        result_status = getattr(result.status, "value", str(result.status))
        passed = result_status == "passed" and result.exit_code == 0
        if stage == "verify" and passed:
            status = "pending"
            meta = "Regression validation passed; waiting for independent review."
        else:
            status = "passed" if passed else "failed"
            meta = f"{command.name} {'passed' if passed else 'failed'}."
        _update_progress(
            stage,
            status,
            meta,
            detail=f"Exit code: {result.exit_code}",
        )
    return result


async def _instrumented_review(
    self: Any, context: Any, checks: Any
) -> Any:
    _append_agent_trace(
        actor="Reviewer agent",
        kind="handoff",
        title="Independent review",
        status="running",
        detail="The controller handed the patch to the independent reviewer.",
    )
    _update_progress(
        "verify",
        "running",
        "The independent reviewer is verifying the fix.",
    )
    result = await _review_call(self, context, checks)
    concerns = list(result.concerns or [])
    blocking = any(
        getattr(concern, "kind", "") in {"repair_needed", "customer_prerequisite"}
        for concern in concerns
    )
    passed = (
        getattr(result.decision, "value", str(result.decision)) == "verified"
        and result.security_invariant_closed
        and result.regression_test_valid
        and result.unit_test_coverage_valid
        and not blocking
    )
    _update_progress(
        "verify",
        "passed" if passed else "failed",
        "Independent review passed." if passed else "Independent review found a required concern.",
        detail=str(result.summary or ""),
    )
    _append_agent_trace(
        actor="Reviewer agent",
        kind="handoff",
        title="Independent review returned",
        status="completed" if passed else "failed",
        result=str(result.summary or ""),
        detail="The reviewer returned its delivery decision.",
    )
    return result


fix_runtime_module.ManagedRepairAgent.__call__ = _instrumented_repair
fix_runtime_module._RuntimeEnvironment.run_isolated_command = _instrumented_command
fix_runtime_module.ManagedIndependentVerifier.__call__ = _instrumented_review
fix_runtime_module._ToolTrace.on_llm_start = _instrumented_llm_start
fix_runtime_module._ToolTrace.on_llm_end = _instrumented_llm_end
fix_runtime_module._ToolTrace.on_tool_start = _instrumented_tool_start
fix_runtime_module._ToolTrace.on_tool_end = _instrumented_tool_end


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay frozen security findings through Strix + Strix Pro."
    )
    parser.add_argument("--from", dest="start", type=int, default=1)
    parser.add_argument("--to", dest="end", type=int)
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
    if not isinstance(payload, list) or not payload:
        raise RuntimeError("Expected a non-empty frozen cohort.")
    return payload


def _validate_cohort(cohort: list[dict[str, Any]]) -> dict[str, Any]:
    manifest_path = EVAL_ROOT / "selection-manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.is_file()
        else {}
    )
    expected_count = int(manifest.get("case_count", len(cohort)))
    if len(cohort) != expected_count:
        raise RuntimeError(
            f"Cohort contains {len(cohort)} cases; manifest expects {expected_count}."
        )
    expected_cohort_digest = manifest.get("cohort_sha256")
    cohort_digest = _sha256_file(EVAL_ROOT / "cohort.json")
    if expected_cohort_digest and cohort_digest != expected_cohort_digest:
        raise RuntimeError(
            "Frozen cohort checksum does not match selection-manifest.json."
        )
    expected_source_digest = manifest.get("source", {}).get("source_tree_sha256")
    manifest_cases = {
        str(item["finding_id"]): item
        for item in manifest.get("cases", [])
        if isinstance(item, dict) and item.get("finding_id")
    }
    scan_ids = [str(case["scan_id"]) for case in cohort if case.get("scan_id")]
    expected_distinct_scan_count = manifest.get("distinct_scan_count")
    if (
        expected_distinct_scan_count is not None
        and len(set(scan_ids)) != int(expected_distinct_scan_count)
    ):
        raise RuntimeError(
            "Frozen cohort distinct scan count does not match "
            "selection-manifest.json."
        )
    if manifest.get("source_kind") == "strix_scans":
        if len(scan_ids) != len(cohort):
            raise RuntimeError("Every scan cohort case must include scan_id.")
        if any(case.get("pr_review_id") for case in cohort):
            raise RuntimeError("Scan cohort cases must not include pr_review_id.")
    category_counts = Counter(
        str(case["cohort_category"])
        for case in cohort
        if case.get("cohort_category")
    )
    expected_category_counts = manifest.get("scan_mix")
    if expected_category_counts is not None and dict(category_counts) != {
        str(category): int(count)
        for category, count in expected_category_counts.items()
    }:
        raise RuntimeError(
            "Frozen cohort scan mix does not match selection-manifest.json."
        )

    cases: list[dict[str, Any]] = []
    for case_number, case in enumerate(cohort, start=1):
        label = _case_label(case_number)
        manifest_case = manifest_cases.get(str(case["id"]), {})
        for field in (
            "scan_id",
            "cohort_category",
            "engagement_type",
            "repository_full_name",
            "head_sha",
        ):
            expected = manifest_case.get(field)
            if expected is not None and str(case.get(field)) != str(expected):
                raise RuntimeError(
                    f"Frozen case {label} {field} does not match "
                    "selection-manifest.json."
                )
        if (
            case.get("cohort_category") == "live_test_with_repositories"
            and (
                case.get("engagement_type") != "live_test"
                or not case.get("repository_full_name")
                or not case.get("repository_url")
                or manifest_case.get("repositories_attached") is not True
            )
        ):
            raise RuntimeError(
                f"Frozen live-test case {label} must have an attached "
                "repository."
            )
        source = EVAL_ROOT / "cases" / label / "source"
        if not source.is_dir():
            raise FileNotFoundError(f"Frozen source is missing: {source}")
        source_digest = _sha256_tree(source)
        case_source_digest = (
            manifest_case.get("source_tree_sha256") or expected_source_digest
        )
        if case_source_digest and source_digest != case_source_digest:
            raise RuntimeError(
                f"Frozen source checksum does not match for case {label}."
            )
        archive = _archive_path(case)
        archive_digest = _sha256_file(archive)
        expected_archive_digest = (
            manifest_case.get("archive_sha256")
            or case.get("source_archive_sha256")
        )
        if (
            expected_archive_digest
            and archive_digest != expected_archive_digest
        ):
            raise RuntimeError(
                f"Frozen archive checksum does not match for case {label}."
            )
        request = _build_request(case, archive_digest, network_allowed=False)
        cases.append(
            {
                "case": case_number,
                "finding_id": case["id"],
                "scan_id": case.get("scan_id") or case.get("pr_review_id"),
                "repository_full_name": case["repository_full_name"],
                "head_sha": case["head_sha"],
                "source_tree_sha256": source_digest,
                "archive": archive.name,
                "archive_sha256": archive_digest,
                "candidate_digest": request.candidate.digest(),
                "finding_location_count": len(request.candidate.finding_locations),
            }
        )
    return {
        "case_count": len(cases),
        "distinct_scan_count": len(set(scan_ids)),
        "scan_mix": dict(sorted(category_counts.items())),
        "cohort_sha256": cohort_digest,
        "selection_manifest_sha256": (
            _sha256_file(manifest_path) if manifest_path.is_file() else None
        ),
        "cases": cases,
    }


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


def _sha256_tree(path: Path) -> str:
    archive = subprocess.run(  # noqa: S603
        [
            "tar",
            "--sort=name",
            "--mtime=@0",
            "--owner=0",
            "--group=0",
            "--numeric-owner",
            "-cf",
            "-",
            ".",
        ],
        cwd=path,
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout
    return hashlib.sha256(archive).hexdigest()


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
        "app": _git_identity(APP_ROOT),
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
            "title": case.get("title"),
            "description": case.get("description"),
            "technical_analysis": case.get("technical_analysis")
            or case.get("description"),
            "remediation_steps": case.get("remediation_steps"),
            "code_locations": case.get("code_locations"),
            "evidence": case.get("evidence"),
        },
        source_identity=source_identity,
    )
    if candidate is None and case.get("scan_id"):
        technical_analysis = str(
            case.get("technical_analysis") or case.get("description") or ""
        ).strip()
        remediation = str(case.get("remediation_steps") or "").strip()
        evidence = str(case.get("evidence") or "").strip()
        candidate = FixCandidateV1(
            source_identity=source_identity,
            security_invariant=remediation
            or technical_analysis
            or "Resolve the reported security finding without changing legitimate behavior.",
            reproduction=(
                ReproductionSpec(instructions=evidence) if evidence else None
            ),
            finding=FindingContext(
                title=str(case.get("title") or ""),
                description=str(case.get("description") or technical_analysis),
                evidence=evidence,
                remediation=remediation,
            ),
            known_gaps=["The scan finding has no structured source location."],
        )
    if candidate is None:
        raise RuntimeError("The frozen finding did not produce a fix candidate.")
    return FixPreparationRequestV1(
        organization_id=case.get("organization_id"),
        scan_id=str(case.get("scan_id") or case["pr_review_id"]),
        finding_id=str(case["id"]),
        repository_id=str(case["repository_full_name"]),
        candidate=candidate,
        max_agent_turns=500,
        timeout_seconds=7200,
        network_allowed=network_allowed,
        credentials_allowed=[],
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


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
            if "execution.json" not in names:
                return {"valid": False, "reason": "execution_history_missing"}
            execution = json.loads(archive.read("execution.json"))
            if not isinstance(execution, list):
                return {"valid": False, "reason": "execution_history_invalid"}
    except (
        OSError,
        KeyError,
        ValueError,
        zipfile.BadZipFile,
        json.JSONDecodeError,
    ) as error:
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
        "scan_id": case.get("scan_id"),
        "pr_review_id": case.get("pr_review_id"),
        "repository_full_name": case["repository_full_name"],
        "pr_number": case.get("pr_number"),
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

    progress_path = case_output / "progress.json"
    _write_json(progress_path, _initial_progress())
    progress_token = _PROGRESS_PATH.set(progress_path)
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
        record["artifact_validation"] = _artifact_validation(
            artifact_path, result_payload
        )
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
    finally:
        _PROGRESS_PATH.reset(progress_token)

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
    cohort = _load_cohort()
    args.end = args.end or len(cohort)
    if not 1 <= args.start <= args.end <= len(cohort):
        raise SystemExit(f"--from and --to must select cases within 1..{len(cohort)}")
    if args.concurrency < 1:
        raise SystemExit("--concurrency must be positive")
    runtime_identity = _runtime_identity()
    cohort_validation = _validate_cohort(cohort)
    runtime_identity["cohort_validation"] = cohort_validation
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
        "runtime_exceptions": sum(
            bool(result.get("runtime_exception")) for result in results
        ),
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
