import asyncio
import json


ROOT = "/home/ubuntu/verified-fix-benchmark/replay"
COHORT = "/home/ubuntu/pr-fix-eval/cohort.json"
GROUPS = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9],
    [10, 11, 12],
    [13, 14, 15],
]

GRADE_SCHEMA = {
    "type": "object",
    "properties": {
        "cases": {"type": "string"},
        "grades_json": {"type": "string"},
        "cross_case_findings": {"type": "string"},
    },
    "required": ["cases", "grades_json", "cross_case_findings"],
}

REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "metrics_path": {"type": "string"},
        "report_path": {"type": "string"},
        "recommendation": {"type": "string"},
    },
    "required": ["metrics_path", "report_path", "recommendation"],
}


def grader_prompt(cases: list[int]) -> str:
    labels = ", ".join(f"{case:02d}" for case in cases)
    return f"""
Independently grade benchmark cases {labels}. This is a read-only security-fix
evaluation. Do not modify files, switch branches, commit, delete artifacts, or
rerun the repair agents.

All evidence exists only on this shared machine:
- Frozen cohort: {COHORT}
- Per-case request, generated patch, and preserved workspace:
  {ROOT}/cases/NN/request.json
  {ROOT}/cases/NN/prepared-fix.patch
  {ROOT}/cases/NN/workspace
- Controller result and verifier/check evidence:
  {ROOT}/results/NN.json

For each assigned case:
1. Locate the exact frozen cohort record by finding_id or recency_rank.
2. Read the original finding, remediation, code locations, and expected
   security invariant.
3. Inspect the complete generated patch, not only the controller state.
4. Inspect relevant surrounding and sibling paths in the preserved workspace.
5. Read repository-check and security-verifier evidence in the result JSON.
6. Decide whether the patch substantively and safely closes the whole finding,
   preserves legitimate behavior, and has adequate regression coverage.
7. Judge whether the controller outcome was appropriate. A runtime label is
   not a correctness score. In particular, identify unsafe ready results and
   correct patches that were over-blocked.
8. Classify non-ready causes as repair defect, verifier defect, quality-gate
   defect, legitimate source/environment/external blocker, repository-baseline
   blocker, or mixed.
9. Include wall_clock_seconds and explain whether the time was useful work,
   a fast preflight block, turn-limit wheel-spinning, or quality/verifier work.

Return grades_json as a valid JSON array encoded as a string. Each item must
have these keys:
case, finding_title, repository, runtime_state, duration_seconds,
patch_verdict (correct|incomplete|incorrect|no_patch|ungradable),
patch_correct (boolean), controller_outcome_appropriate (boolean),
automatic_approval_safe (boolean|null), cause_classification,
security_analysis, test_and_quality_analysis, timing_analysis,
evidence_paths (array of absolute paths), confidence (high|medium|low).

Be skeptical and specific. Do not accept a patch merely because tests passed.
Do not reject a patch merely because the runtime state is failed or blocked.
""".strip()


async def grade_group(cases: list[int]) -> dict:
    return await agent(
        grader_prompt(cases),
        phase="grade",
        schema=GRADE_SCHEMA,
        label=f"cases-{cases[0]:02d}-{cases[-1]:02d}",
        mode="normal",
        # The benchmark workspaces and result evidence exist only on this VM.
        vm_mode="shared",
        soft_time_limit_minutes=25,
    )


async def main() -> None:
    await register_workflow(
        {
            "name": "verified-fix-15-case-grading",
            "description": (
                "Independently inspect and grade all generated security patches, "
                "then reconcile correctness, controller precision, blockers, and timing."
            ),
            "product": "Strix verified fix preparation",
            "soft_time_limit_minutes": 25,
            "phases": [
                {
                    "title": "grade",
                    "detail": "Inspect each patch and its security evidence",
                    "count": 5,
                    "labels": [
                        f"cases-{group[0]:02d}-{group[-1]:02d}" for group in GROUPS
                    ],
                },
                {
                    "title": "reconcile",
                    "detail": "Reconcile independent grades into the final case-by-case review",
                    "count": 1,
                    "labels": ["final-review"],
                    "soft_time_limit_minutes": 25,
                },
            ],
        }
    )
    log("Starting five independent grading groups")
    graders = await asyncio.gather(*(grade_group(group) for group in GROUPS))
    log("All case grades complete; starting reconciliation")
    reconciliation_prompt = f"""
Reconcile the five independent grading outputs below into one rigorous report.
You may read the original files under {ROOT} and {COHORT} to resolve any
ambiguity. Do not modify any repository or benchmark input artifact.

Grader outputs:
{json.dumps(graders, sort_keys=True)}

The report must:
- cover all 15 cases individually
- include runtime state and exact duration for every case
- distinguish patch correctness from controller eligibility
- count correct, incomplete, incorrect, no-patch, and ungradable patches
- compute automatic-ready precision and identify any unsafe ready result
- count correct patches withheld and explain why
- classify blocker and failure causes
- summarize minimum, maximum, mean, median, p95, and total case time from the
  benchmark summary
- identify time outliers and wheel-spinning patterns
- assess whether the simplified architecture improved the earlier failure modes
- recommend specific next changes and whether the 100-case replay should start
- explicitly keep the 100-case replay paused unless the evidence justifies it

Use concise but thorough Markdown. Give evidence-based conclusions and call out
contradictory verifier fields. Write the full Markdown report to
{ROOT}/verified-fix-15-case-review.md and its valid JSON metrics object to
{ROOT}/verified-fix-15-case-metrics.json. These two new report files are the
only files you may create or update. Return their absolute paths and a concise
recommendation.
""".strip()
    report = await agent(
        reconciliation_prompt,
        phase="reconcile",
        schema=REPORT_SCHEMA,
        label="final-review",
        mode="normal",
        # Reconciliation must cross-check the same machine-local artifacts.
        vm_mode="shared",
        soft_time_limit_minutes=25,
    )
    log("Reconciliation complete")
    print(json.dumps({"graders": graders, "report": report}, indent=2))


asyncio.run(main())
