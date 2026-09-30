import asyncio
import json
from pathlib import Path


ROOT = Path("/home/ubuntu/verified-fix-benchmark")
COHORT = Path("/home/ubuntu/pr-fix-eval/cohort.json")
RESULTS = ROOT / "replay" / "results"
RANGES = [(1, 5), (6, 10), (11, 15)]

GRADE_SCHEMA = {
    "type": "object",
    "properties": {
        "grades": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "case": {"type": "integer"},
                    "verdict": {
                        "type": "string",
                        "enum": ["correct", "incorrect", "ungradeable", "no_patch"],
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                    "security_invariant_closed": {"type": "boolean"},
                    "behavior_preserved": {"type": "boolean"},
                    "automatic_pr_eligible": {"type": "boolean"},
                    "automatic_eligibility_appropriate": {"type": "boolean"},
                    "rationale": {"type": "string"},
                },
                "required": [
                    "case",
                    "verdict",
                    "confidence",
                    "security_invariant_closed",
                    "behavior_preserved",
                    "automatic_pr_eligible",
                    "automatic_eligibility_appropriate",
                    "rationale",
                ],
            },
        }
    },
    "required": ["grades"],
}


def prompt_for(start: int, end: int) -> str:
    return f"""
You are an independent security-fix benchmark grader. Grade cases {start:02d}-{end:02d}
without trusting the runtime's verifier verdict.

Read-only inputs on this VM:
- frozen cohort: {COHORT}
- per-case result: {RESULTS}/NN.json
- generated patch: {ROOT}/replay/cases/NN/prepared-fix.patch
- prepared artifact when needed: {ROOT}/replay/cases/NN/prepared-fix.zip
- final checkout when retained: {ROOT}/replay/cases/NN/workspace

Do not modify files, git state, processes, containers, or the running benchmark.

For each case:
1. Read cohort array item case-1 for the finding title, description, evidence,
   locations, and remediation intent.
2. Read the result JSON, patch, and relevant final source. If the patch is absent
   or empty, inspect the result manifest and prepared artifact before deciding
   `no_patch`.
3. Grade the patch itself:
   - `correct` only when the reported security invariant is fully closed,
     relevant sibling paths are addressed, intended behavior is preserved,
     tests/security controls are not weakened, and there is no obvious regression.
   - `incorrect` when a substantive patch is incomplete, unsafe, or behavior-breaking.
   - `no_patch` when no substantive remediation was produced.
   - `ungradeable` only when the available repository evidence cannot support a decision.
4. Copy `automatic_pr_eligible` from the result JSON. Mark eligibility appropriate
   only when an eligible patch is correct with valid evidence, or an ineligible patch
   is not safe to auto-apply. A correct but ineligible patch is over-blocked, so mark
   `automatic_eligibility_appropriate=false`.
5. Give a concise, concrete rationale naming the decisive file/symbol/evidence.

Return exactly {end - start + 1} grades, one for every case {start}-{end}, ordered
by case number.
""".strip()


async def grade_range(start: int, end: int) -> dict[str, object]:
    # Shared VM is required because the frozen cohort, generated patches, and
    # benchmark workspaces exist only on this machine and are too large to upload.
    return await agent(  # noqa: F821
        prompt_for(start, end),
        phase="grade",
        schema=GRADE_SCHEMA,
        label=f"cases-{start:02d}-{end:02d}",
        vm_mode="shared",
        soft_time_limit_minutes=45,
    )


async def main() -> None:
    await register_workflow(  # noqa: F821
        {
            "name": "verified-fix-15-case-gate-grading",
            "description": "Independently grade the corrected 15-case benchmark gate",
            "product": "Strix verified fix preparation",
            "soft_time_limit_minutes": 45,
            "phases": [
                {
                    "title": "grade",
                    "detail": "Review generated patches against frozen findings",
                    "count": len(RANGES),
                    "labels": [
                        f"cases-{start:02d}-{end:02d}" for start, end in RANGES
                    ],
                }
            ],
        }
    )
    log("Starting three independent grading ranges")  # noqa: F821
    batches = await asyncio.gather(
        *(grade_range(start, end) for start, end in RANGES)
    )
    grades = [grade for batch in batches for grade in batch["grades"]]
    grades.sort(key=lambda grade: grade["case"])
    observed = [grade["case"] for grade in grades]
    if observed != list(range(1, 16)):
        raise RuntimeError(f"Expected cases 1-15 exactly once, got {observed}")

    verdict_counts = {
        verdict: sum(grade["verdict"] == verdict for grade in grades)
        for verdict in ("correct", "incorrect", "ungradeable", "no_patch")
    }
    eligible = [grade for grade in grades if grade["automatic_pr_eligible"]]
    correct_internal = [
        grade
        for grade in grades
        if grade["verdict"] == "correct" and not grade["automatic_pr_eligible"]
    ]
    runtime_identities = [
        json.loads((RESULTS / f"{case:02d}.json").read_text(encoding="utf-8"))[
            "runtime_identity"
        ]
        for case in range(1, 16)
    ]
    implementation_counts: dict[str, int] = {}
    for identity in runtime_identities:
        label = (
            f"oss:{identity['oss']['head']} "
            f"pro:{identity['pro']['head']} "
            f"model:{identity['model']}"
        )
        implementation_counts[label] = implementation_counts.get(label, 0) + 1

    eligible_correct = sum(grade["verdict"] == "correct" for grade in eligible)
    eligible_incorrect = sum(grade["verdict"] == "incorrect" for grade in eligible)
    appropriate_decisions = sum(
        grade["automatic_eligibility_appropriate"] for grade in grades
    )
    summary = {
        "cases": 15,
        "cohort_sha256": runtime_identities[0]["cohort_sha256"],
        "harness_sha256": runtime_identities[0]["harness_sha256"],
        "implementation_counts": implementation_counts,
        "verdict_counts": verdict_counts,
        "total_correct": verdict_counts["correct"],
        "automatic_pr_eligible": len(eligible),
        "automatic_pr_eligible_correct": eligible_correct,
        "automatic_pr_eligible_incorrect": eligible_incorrect,
        "automatic_pr_precision": (
            eligible_correct / len(eligible) if eligible else None
        ),
        "correct_but_not_eligible": len(correct_internal),
        "correct_internal_overblocked": sum(
            not grade["automatic_eligibility_appropriate"]
            for grade in correct_internal
        ),
        "eligibility_decisions_appropriate": appropriate_decisions,
        "eligibility_decisions_appropriate_rate": appropriate_decisions / len(grades),
    }
    grades_path = RESULTS / "gate-15-independent-grades.json"
    summary_path = RESULTS / "gate-15-independent-grade-summary.json"
    grades_path.write_text(json.dumps(grades, indent=2) + "\n", encoding="utf-8")
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    log(f"Wrote {grades_path}")  # noqa: F821
    log(f"Wrote {summary_path}: {json.dumps(summary, sort_keys=True)}")  # noqa: F821


asyncio.run(main())
