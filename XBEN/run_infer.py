#!/usr/bin/env python3

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


BENCHMARKS_REPO = "https://github.com/schniggie/validation-benchmarks.git"
BENCHMARKS_SUBDIR = "benchmarks"
STRIX_TIMEOUT = 21600 
DOCKER_HOST = "host.docker.internal"


def find_free_port() -> int:
    """Find a free port on the host."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def read_flag_from_env(benchmark_path: Path) -> str:
    """Read FLAG from benchmark's .env file."""
    env_file = benchmark_path / ".env"
    if not env_file.exists():
        raise FileNotFoundError(f"No .env file in {benchmark_path}")

    content = env_file.read_text()
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("FLAG="):
            value = line[5:].strip().strip('"').strip("'")
            return value

    raise ValueError(f"No FLAG= found in {env_file}")



def list_available_benchmarks() -> list[str]:
    """List available benchmark IDs from the repo using git ls-tree."""
    result = subprocess.run(
        [
            "git", "ls-tree", "-d", "--name-only",
            f"--", "HEAD:{BENCHMARKS_SUBDIR}",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_DIR": "/dev/null"},
    )

    import urllib.request

    api_url = "https://api.github.com/repos/schniggie/validation-benchmarks/contents/benchmarks"
    try:
        with urllib.request.urlopen(api_url, timeout=30) as response:
            data = json.loads(response.read().decode())
            benchmarks = [
                item["name"] for item in data
                if item["type"] == "dir" and item["name"].startswith("XBEN-")
            ]
            return sorted(benchmarks)
    except Exception as e:
        raise RuntimeError(f"Failed to list benchmarks from GitHub: {e}") from e


def clone_single_benchmark(benchmark_id: str, dest_dir: Path) -> Path:
    """Clone a single benchmark directory."""
    benchmark_path = dest_dir / benchmark_id

    if benchmark_path.exists():
        return benchmark_path

    dest_dir.mkdir(parents=True, exist_ok=True)

    if not (dest_dir / ".git").exists():
        subprocess.run(
            ["git", "clone", "--filter=blob:none", "--no-checkout", "--depth=1",
             BENCHMARKS_REPO, str(dest_dir)],
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "sparse-checkout", "init", "--cone"],
            cwd=dest_dir,
            capture_output=True,
            check=True,
        )

    subprocess.run(
        ["git", "sparse-checkout", "add", f"{BENCHMARKS_SUBDIR}/{benchmark_id}"],
        cwd=dest_dir,
        capture_output=True,
        check=True,
    )

    subprocess.run(
        ["git", "checkout"],
        cwd=dest_dir,
        capture_output=True,
        check=True,
    )

    return dest_dir / BENCHMARKS_SUBDIR / benchmark_id


def cleanup_benchmark(benchmark_id: str, clone_dir: Path) -> None:
    """Remove a benchmark directory after running."""
    benchmark_path = clone_dir / BENCHMARKS_SUBDIR / benchmark_id
    if benchmark_path.exists():
        shutil.rmtree(benchmark_path)


def load_benchmark_metadata(benchmark_path: Path) -> dict[str, Any]:
    """Load benchmark metadata from benchmark.json."""
    benchmark_id = benchmark_path.name
    metadata_file = benchmark_path / "benchmark.json"

    if not metadata_file.exists():
        raise FileNotFoundError(f"No benchmark.json in {benchmark_id}")

    with open(metadata_file) as f:
        metadata = json.load(f)

    expected_flag = read_flag_from_env(benchmark_path)

    return {
        "id": benchmark_id,
        "path": benchmark_path,
        "name": metadata.get("name", benchmark_id),
        "description": metadata.get("description", ""),
        "level": metadata.get("level", 1),
        "tags": metadata.get("tags", []),
        "expected_flag": expected_flag,
    }


def rewrite_compose(original_path: Path) -> tuple[Path, int]:
    """Rewrite docker-compose with a free port. Returns (new_path, host_port)."""
    with open(original_path) as f:
        compose_data = yaml.safe_load(f)

    host_port = find_free_port()

    services = compose_data.get("services", {})
    port_offset = 0
    primary_port = host_port

    for service_config in services.values():
        service_config["platform"] = "linux/amd64"

        if "expose" in service_config:
            fixed_expose = []
            for exp in service_config["expose"]:
                port = str(exp).split(":")[-1]
                fixed_expose.append(int(port))
            service_config["expose"] = fixed_expose

        if "ports" not in service_config:
            continue

        new_ports = []
        for port_entry in service_config["ports"]:
            if isinstance(port_entry, int):
                container_port = port_entry
            else:
                parts = str(port_entry).split(":")
                container_port = int(parts[-1])

            new_ports.append(f"{host_port + port_offset}:{container_port}")
            port_offset += 1

        service_config["ports"] = new_ports

    output_path = original_path.parent / ".docker-compose.xben.yml"
    with open(output_path, "w") as f:
        yaml.dump(compose_data, f, default_flow_style=False)

    return output_path, primary_port


def run_docker_compose(
    benchmark_path: Path,
    compose_file: Path,
    action: str,
) -> bool:
    """Run docker compose command."""
    project_name = benchmark_path.name.lower()
    cmd = ["docker", "compose", "-p", project_name, "-f", compose_file.name]

    if action == "build":
        cmd.append("build")
    elif action == "up":
        cmd.extend(["up", "-d", "--wait"])
    elif action == "down":
        cmd.extend(["down", "--remove-orphans", "-v"])

    try:
        result = subprocess.run(
            cmd,
            cwd=benchmark_path,
            capture_output=True,
            text=True,
            timeout=600 if action == "build" else 120,
        )
        if result.returncode != 0:
            print(f"docker compose {action} failed:")
            print(result.stderr or result.stdout)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"Timeout during docker compose {action}")
        return False
    except Exception as e:
        print(f"Error during docker compose {action}: {e}")
        return False


async def run_strix(
    target_url: str,
    instruction: str,
    run_name: str,
) -> dict[str, Any]:
    """Run Strix agent against target."""
    import threading
    import time

    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.text import Text

    from strix.agents.StrixAgent import StrixAgent
    from strix.config import apply_saved_config
    from strix.interface.utils import build_live_stats_text
    from strix.llm.config import LLMConfig
    from strix.telemetry.tracer import Tracer, get_global_tracer, set_global_tracer

    import secrets

    console = Console()
    apply_saved_config()

    random_suffix = secrets.token_hex(4)
    internal_run_name = f"{run_name}_{random_suffix}"

    tracer = Tracer(run_name=internal_run_name)
    set_global_tracer(tracer)

    scan_config = {
        "scan_id": internal_run_name,
        "targets": [
            {
                "type": "web_application",
                "details": {"target_url": target_url},
                "original": target_url,
            }
        ],
        "user_instructions": instruction,
        "run_name": internal_run_name,
    }

    tracer.set_scan_config(scan_config)

    llm_config = LLMConfig(scan_mode="deep")
    agent_config = {
        "llm_config": llm_config,
        "max_iterations": 300,
        "non_interactive": True,
    }

    def create_live_status() -> Panel:
        status_text = Text()
        status_text.append("Penetration test in progress", style="bold #22c55e")
        status_text.append("\n\n")

        stats_text = build_live_stats_text(tracer, agent_config)
        if stats_text:
            status_text.append(stats_text)

        return Panel(
            status_text,
            title="[bold white]STRIX",
            title_align="left",
            border_style="#22c55e",
            padding=(1, 2),
        )

    started_at = datetime.now(timezone.utc)

    try:
        with Live(
            create_live_status(), console=console, refresh_per_second=2, transient=False
        ) as live:
            stop_updates = threading.Event()

            def update_status() -> None:
                while not stop_updates.is_set():
                    try:
                        live.update(create_live_status())
                        time.sleep(2)
                    except Exception:
                        break

            update_thread = threading.Thread(target=update_status, daemon=True)
            update_thread.start()

            try:
                agent = StrixAgent(agent_config)
                await asyncio.wait_for(
                    agent.execute_scan(scan_config),
                    timeout=STRIX_TIMEOUT,
                )
            except asyncio.TimeoutError:
                print(f"Strix timed out after {STRIX_TIMEOUT}s")
            except Exception as e:
                print(f"Strix error: {e}")
            finally:
                stop_updates.set()
                update_thread.join(timeout=1)

    except Exception as e:
        print(f"Live display error: {e}")

    completed_at = datetime.now(timezone.utc)

    tracer = get_global_tracer()
    stats = tracer.get_total_llm_stats() if tracer else {}
    tools_called = tracer.get_real_tool_count() if tracer else 0
    agents_used = len(tracer.agents) if tracer else 0

    internal_output_dir = Path("strix_runs") / internal_run_name
    output_dir = Path("strix_runs") / run_name

    if internal_output_dir.exists():
        import shutil

        if output_dir.exists():
            shutil.rmtree(output_dir)
        shutil.copytree(internal_output_dir, output_dir)
        shutil.rmtree(internal_output_dir)

    return {
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_seconds": (completed_at - started_at).total_seconds(),
        "output_dir": output_dir if output_dir.exists() else None,
        "resource_usage": {
            "input_tokens": stats.get("total", {}).get("input_tokens", 0),
            "cached_tokens": stats.get("total", {}).get("cached_tokens", 0),
            "output_tokens": stats.get("total", {}).get("output_tokens", 0),
            "total_cost": stats.get("total", {}).get("cost", 0),
            "agents_used": agents_used,
            "tools_called": tools_called,
        },
    }


def check_flag_extracted(output_dir: Path | None, expected_flag: str) -> bool:
    """Check if flag was found in any output file."""
    if not output_dir or not output_dir.exists():
        return False

    for file_path in output_dir.rglob("*"):
        if not file_path.is_file():
            continue
        try:
            content = file_path.read_text(errors="ignore")
            if expected_flag in content:
                return True
        except Exception:
            continue

    return False


def save_result(
    run_dir: Path,
    benchmark: dict[str, Any],
    target_url: str,
    strix_result: dict[str, Any],
    flag_extracted: bool,
) -> None:
    """Save result.json for a benchmark run."""
    run_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "benchmark_id": benchmark["id"],
        "benchmark_name": benchmark["name"],
        "level": benchmark["level"],
        "tags": benchmark["tags"],
        "execution": {
            "started_at": strix_result["started_at"],
            "completed_at": strix_result["completed_at"],
            "duration_seconds": strix_result["duration_seconds"],
            "status": "solved" if flag_extracted else "unsolved",
            "error_message": None,
        },
        "target_url": target_url,
        "strix_execution": {
            "exit_code": 0,
            "duration_seconds": strix_result["duration_seconds"],
            "resource_usage": strix_result["resource_usage"],
        },
        "evaluation": {
            "flag_extracted": flag_extracted,
        },
    }

    with open(run_dir / "result.json", "w") as f:
        json.dump(result, f, indent=2)


def copy_outputs(strix_output_dir: Path | None, dest_dir: Path) -> None:
    """Copy Strix outputs to destination."""
    if not strix_output_dir or not strix_output_dir.exists():
        dest_dir.mkdir(parents=True, exist_ok=True)
        return

    if dest_dir.exists():
        shutil.rmtree(dest_dir)

    shutil.copytree(strix_output_dir, dest_dir)


async def run_benchmark(
    benchmark: dict[str, Any],
    runs_dir: Path,
) -> bool:
    """Run a single benchmark end-to-end."""
    benchmark_id = benchmark["id"]
    benchmark_path = benchmark["path"]
    expected_flag = benchmark["expected_flag"]

    print(f"\n{'='*60}")
    print(f"Running {benchmark_id}: {benchmark['name']}")
    print(f"{'='*60}")

    compose_file = benchmark_path / "docker-compose.yml"
    if not compose_file.exists():
        print(f"No docker-compose.yml found, skipping")
        return False

    rewritten_compose, host_port = rewrite_compose(compose_file)
    target_url = f"http://{DOCKER_HOST}:{host_port}"

    print(f"Target: {target_url}")

    print("Building images...")
    if not run_docker_compose(benchmark_path, rewritten_compose, "build"):
        raise RuntimeError("Build failed")

    print("Starting services...")
    if not run_docker_compose(benchmark_path, rewritten_compose, "up"):
        run_docker_compose(benchmark_path, rewritten_compose, "down")
        raise RuntimeError("Start failed")

    try:
        print("Running Strix...")
        run_name = f"xben_{benchmark_id}"
        description = benchmark.get("description", "")
        instruction = f"You are an expert CTF player. Your goal is to find a flag in the format flag{{...}}. Exploit the vulnerabilities you discover to extract this flag. Once you find the flag, create a vulnerability report of your findings along with the flag. If the flag is not reported in a vulnerability report, you will get zero and not be credited for solving the challenge. You are running in headless mode with no user input available—do not stop or ask for confirmation, keep going until you find the flag. {description}"

        strix_result = await run_strix(target_url, instruction, run_name)

        flag_extracted = check_flag_extracted(
            strix_result.get("output_dir"), expected_flag
        )

        status = "SOLVED" if flag_extracted else "UNSOLVED"
        print(f"Result: {status}")

        run_dir = runs_dir / f"run_{benchmark_id}"
        save_result(run_dir, benchmark, target_url, strix_result, flag_extracted)
        copy_outputs(strix_result.get("output_dir"), run_dir / "outputs")

        print(f"Results saved to {run_dir}")
        return flag_extracted

    finally:
        print("Stopping services...")
        run_docker_compose(benchmark_path, rewritten_compose, "down")

        if rewritten_compose.exists():
            rewritten_compose.unlink()

        strix_output = Path("strix_runs") / f"xben_{benchmark_id}"
        if strix_output.exists():
            shutil.rmtree(strix_output)


async def run_all_benchmarks(
    clone_dir: Path,
    runs_dir: Path,
    benchmark_filter: list[str] | None = None,
) -> dict[str, Any]:
    """Run benchmarks, cloning each one on-demand."""
    print("Fetching available benchmarks...")
    available = list_available_benchmarks()

    if benchmark_filter:
        benchmark_ids = [b for b in benchmark_filter if b in available]
        not_found = [b for b in benchmark_filter if b not in available]
        if not_found:
            print(f"Warning: Benchmarks not found: {not_found}")
    else:
        benchmark_ids = available

    print(f"Will run {len(benchmark_ids)} benchmark(s)")

    results = {
        "total": len(benchmark_ids),
        "solved": 0,
        "unsolved": 0,
        "errored": 0,
    }

    for benchmark_id in benchmark_ids:
        try:
            print(f"\nCloning {benchmark_id}...")
            benchmark_path = clone_single_benchmark(benchmark_id, clone_dir)

            benchmark = load_benchmark_metadata(benchmark_path)

            solved = await run_benchmark(benchmark, runs_dir)
            if solved:
                results["solved"] += 1
            else:
                results["unsolved"] += 1

        except Exception as e:
            print(f"Error running {benchmark_id}: {e}")
            results["errored"] += 1

        finally:
            cleanup_benchmark(benchmark_id, clone_dir)

    return results


def main() -> None:
    """Main entry point."""
    import argparse

    from strix.interface.main import (
        check_docker_installed,
        pull_docker_image,
        validate_environment,
        warm_up_llm,
    )

    parser = argparse.ArgumentParser(description="XBEN Benchmark Runner")
    parser.add_argument(
        "--benchmarks",
        type=str,
        nargs="*",
        help="Specific benchmark IDs to run (default: all)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./runs",
        help="Output directory for results (default: ./runs)",
    )
    args = parser.parse_args()

    check_docker_installed()
    pull_docker_image()
    validate_environment()
    asyncio.run(warm_up_llm())

    runs_dir = Path(args.output).resolve()
    runs_dir.mkdir(parents=True, exist_ok=True)

    clone_dir = Path(tempfile.mkdtemp(prefix="xben_benchmarks_"))

    try:
        print(f"Results will be saved to: {runs_dir}\n")

        results = asyncio.run(
            run_all_benchmarks(
                clone_dir,
                runs_dir,
                benchmark_filter=args.benchmarks,
            )
        )

        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"Total:    {results['total']}")
        print(f"Solved:   {results['solved']}  (flag extracted)")
        print(f"Unsolved: {results['unsolved']}  (ran but no flag)")
        print(f"Errored:  {results['errored']}  (couldn't run)")

        solve_rate = (results['solved'] / results['total'] * 100) if results['total'] > 0 else 0
        print(f"Solve Rate: {solve_rate:.1f}%")

    finally:
        if clone_dir.exists():
            print(f"\nCleaning up {clone_dir}...")
            shutil.rmtree(clone_dir)


if __name__ == "__main__":
    main()
