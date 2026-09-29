from __future__ import annotations

import importlib.util
import io
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

        async def exec(self, *_args: str, **_kwargs: Any) -> Any:
            return SimpleNamespace(exit_code=0, stdout=b"", stderr=b"")

        async def write(self, path: Path, content: io.BytesIO) -> None:
            self.writes.append(path)
            assert content.read()

    class Runtime:
        sandbox_workspace = "/workspace/source"

        def __init__(self) -> None:
            self.session = Session()

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
