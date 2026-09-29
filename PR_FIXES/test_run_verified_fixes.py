from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


RUNNER_PATH = Path(__file__).with_name("run_verified_fixes.py")
SPEC = importlib.util.spec_from_file_location("run_verified_fixes", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)

from strix.fix import CheckStatus, CommandSpec  # noqa: E402
from strix_pro.fix_workspace import fingerprint_script  # noqa: E402


def _fingerprint(source: Path) -> str:
    return subprocess.check_output(
        [
            sys.executable,
            "-c",
            fingerprint_script,
            str(source),
            "HEAD",
        ],
        text=True,
    ).strip()


def test_dashboard_telemetry_does_not_change_source_fingerprint(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text('print("unchanged")\n', encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    subprocess.run(["git", "add", "app.py"], cwd=source, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@local",
            "commit",
            "-qm",
            "initial",
        ],
        cwd=source,
        check=True,
    )

    before = _fingerprint(source)
    telemetry_root = runner._telemetry_root(str(source))
    telemetry_root.mkdir()
    (telemetry_root / "case").write_text("03", encoding="utf-8")
    (telemetry_root / "stage").write_text("unit", encoding="utf-8")
    (telemetry_root / "unit.log").write_text("test output\n", encoding="utf-8")

    assert telemetry_root == source.parent / ".strix-benchmark"
    assert _fingerprint(source) == before


def test_build_request_uses_agent_review_limits() -> None:
    case = json.loads(
        (runner.EVAL_ROOT / "cohort.json").read_text(encoding="utf-8")
    )[0]

    request = runner._build_request(case, "0" * 64, network_allowed=True)

    assert request.max_agent_turns == 500
    assert request.timeout_seconds == 7200


def test_agent_trace_is_written_beside_case_progress(tmp_path: Path) -> None:
    progress_path = tmp_path / "03" / "progress.json"
    progress_path.parent.mkdir()
    progress_token = runner._PROGRESS_PATH.set(progress_path)
    try:
        runner._append_agent_trace(
            actor="Repair agent",
            kind="tool",
            title="read_file",
            arguments='{"path":"src/app.ts"}',
            result="file contents",
        )
    finally:
        runner._PROGRESS_PATH.reset(progress_token)

    events = [
        json.loads(line)
        for line in (progress_path.parent / "agent-trace.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert events[0]["actor"] == "Repair agent"
    assert events[0]["title"] == "read_file"
    assert events[0]["arguments"] == '{"path":"src/app.ts"}'


@pytest.mark.asyncio
async def test_instrumented_command_writes_only_outside_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    progress_path = tmp_path / "03" / "progress.json"
    progress_path.parent.mkdir()
    runner._write_json(progress_path, runner._initial_progress())
    progress_token = runner._PROGRESS_PATH.set(progress_path)

    class Session:
        def __init__(self) -> None:
            self.writes: list[Path] = []

        async def exec(self, *args: str, **_kwargs: Any) -> Any:
            if args and args[0] == "git":
                return SimpleNamespace(
                    exit_code=0,
                    stdout=b" M change.py\n",
                    stderr=b"",
                )
            return SimpleNamespace(exit_code=0, stdout=b"", stderr=b"")

        async def write(self, path: Path, content: io.BytesIO) -> None:
            self.writes.append(path)
            assert content.read()

    class Runtime:
        sandbox_workspace = "/workspace/source"

        def __init__(self) -> None:
            self.session = Session()
            self.workspace = tmp_path / "source"
            self.workspace.mkdir()

        async def initialize(self) -> None:
            return

    wrapped: list[CommandSpec] = []

    async def command_call(
        _runtime: Runtime,
        command: CommandSpec,
        *,
        protect_source: bool = False,
    ) -> Any:
        assert protect_source
        wrapped.append(command)
        return SimpleNamespace(
            status=CheckStatus.PASSED,
            exit_code=0,
            model_copy=lambda update: SimpleNamespace(
                status=CheckStatus.PASSED,
                exit_code=0,
                argv=update["argv"],
            ),
        )

    monkeypatch.setattr(runner, "_command_call", command_call)
    runtime = Runtime()
    command = CommandSpec(
        name="Customer unit tests",
        argv=["python", "-m", "pytest"],
        purpose="unit",
    )
    try:
        await runner._instrumented_command(
            runtime,
            command,
            protect_source=True,
        )
    finally:
        runner._PROGRESS_PATH.reset(progress_token)

    assert runtime.session.writes == [
        Path("/workspace/.strix-benchmark/case"),
        Path("/workspace/.strix-benchmark/stage"),
    ]
    assert wrapped[0].argv[6] == "/workspace/.strix-benchmark/unit.log"
    progress = json.loads(progress_path.read_text())
    assert progress["stages"]["patch"]["status"] == "passed"


@pytest.mark.asyncio
async def test_instrumented_command_ignores_exploratory_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    progress_path = tmp_path / "03" / "progress.json"
    progress_path.parent.mkdir()
    runner._write_json(progress_path, runner._initial_progress())
    progress_token = runner._PROGRESS_PATH.set(progress_path)

    class Runtime:
        sandbox_workspace = "/workspace/source"

    received: list[CommandSpec] = []

    async def command_call(
        _runtime: Runtime,
        command: CommandSpec,
        *,
        protect_source: bool = False,
    ) -> Any:
        assert not protect_source
        received.append(command)
        return SimpleNamespace(status=CheckStatus.PASSED, exit_code=0)

    monkeypatch.setattr(runner, "_command_call", command_call)
    command = CommandSpec(
        name="Inspect package metadata",
        argv=["cat", "package.json"],
        purpose="quality",
        required=False,
    )
    try:
        await runner._instrumented_command(Runtime(), command)
    finally:
        runner._PROGRESS_PATH.reset(progress_token)

    assert received == [command]
    progress = json.loads(progress_path.read_text(encoding="utf-8"))
    assert progress["current_stage"] == "patch"
