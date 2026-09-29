# PR Fix Evaluation Harness

This directory preserves the verified-fix replay and independent grading scripts from STR-815.

## Scripts

- `run_verified_fixes.py` replays the frozen 100-case PR-review cohort through the OSS and Strix Pro fix-preparation runtime.
- `benchmark_dashboard_server.py` serves live four-stage progress, command output, and timestamped events from an active replay.
- `grade_workflow.py` runs the final five-group review for the timed 15-case gate and reconciles the results.
- `grade_15_case_gate_workflow.py` runs the earlier three-group 15-case grading workflow.
- `grade_verified_fixes_workflow.py` runs the 100-case grading workflow.

## Required local data

The scripts expect a frozen cohort directory with:

```text
cohort.json
cases/NN/source
archives/<repository>__<head_sha>.tar.gz
```

Set these environment variables when the checkouts do not use the original local paths:

```bash
export STRIX_BENCHMARK_SOURCE=/path/to/pr-fix-eval
export STRIX_BENCHMARK_OUTPUT=/path/to/independent-run
export STRIX_OSS_ROOT=/path/to/strix
export STRIX_PRO_ROOT=/path/to/strix-pro
```

Without `STRIX_BENCHMARK_OUTPUT`, `run_verified_fixes.py` writes replay
workspaces and results under:

```text
/home/ubuntu/verified-fix-benchmark/replay
```

The grading workflows use the same preserved local paths because they were executed as shared-VM dynamic workflows.

## Example replay

```bash
python PR_FIXES/run_verified_fixes.py --preflight
python PR_FIXES/run_verified_fixes.py --from 1 --to 15 --concurrency 1 --force
```

The replay supports:

```text
--from
--to
--concurrency
--force
--keep-workspaces
--smoke
--preflight
--no-network
```

The runner accepts any non-empty frozen cohort and validates `--from` and
`--to` against its actual size.

## Live dashboard

Start the dashboard against the replay output directory:

```bash
export STRIX_BENCHMARK_OUTPUT=/path/to/independent-run
export BENCHMARK_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
export BENCHMARK_START=1
export BENCHMARK_TOTAL=15
python PR_FIXES/benchmark_dashboard_server.py
```

The dashboard displays Build patch, Compile fix, Run unit tests, and Verify fix.
The runner writes live sandbox markers and command logs to
`/workspace/.strix-benchmark`, outside the protected repository at
`/workspace/source`.

## Fresh deterministic slice

Create a severity-stratified 15-case slice that excludes the original first 15
cases:

```bash
python PR_FIXES/select_fresh_slice.py \
  --source /home/ubuntu/pr-fix-eval \
  --output /home/ubuntu/pr-fix-eval-contract-v4-fresh-15 \
  --seed contract-v4-fresh-slice-2026-09-29
```

The selector uses explicit severity quotas, ranks eligible cases by a seed-bound
SHA-256 score, and prefers distinct repositories within each severity. It
writes the exact mapping and source identities to `selection-manifest.json`.

## Grading

The grading files are dynamic workflow scripts.
Run them with Devin's dynamic workflow runner so the injected `agent`, `register_workflow`, and `log` functions are available.

The final 15-case review used:

```text
grade_workflow.py
```

It grades patch correctness separately from controller eligibility.

## Historical baseline note

Some preserved scripts use `historical_baseline_correct`.
That value is an aggregate result from an earlier benchmark run.
It is not a later maintainer fix and is not repository ground truth.

The original benchmark did not retrieve a later fixed commit for candidate comparison.
