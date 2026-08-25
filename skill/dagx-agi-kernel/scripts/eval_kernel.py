#!/usr/bin/env python3
"""Validate and score matched behavioral evaluations for Perfectify."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any


# Suite -> required group counts. `None` means "any number, at least one".
SUITES: dict[str, dict[str, int | None]] = {
    "activation": {"activate": 10, "negative_control": 10, "boundary": 5},
    "adversarial": {"redteam": None},
}
# Groups whose should_activate value is fixed. `redteam` is mixed on purpose:
# it carries both bypass attempts and a cost control that must NOT escalate.
FIXED_ACTIVATION = {"activate": True, "negative_control": False}


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [f"cannot read {path}: {exc}"]

    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{line_number}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(row, dict):
            errors.append(f"{path}:{line_number}: each line must be a JSON object")
            continue
        row["_line"] = line_number
        rows.append(row)
    return rows, errors


def validate_cases(
    rows: list[dict[str, Any]], source: Path, suite: str = "activation"
) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    groups: Counter[str] = Counter()
    expected = SUITES[suite]
    fixed_total = (
        sum(count for count in expected.values() if count is not None)
        if all(count is not None for count in expected.values())
        else None
    )

    if fixed_total is not None and len(rows) != fixed_total:
        errors.append(f"{source}: expected {fixed_total} cases, found {len(rows)}")
    elif not rows:
        errors.append(f"{source}: suite {suite!r} needs at least one case")

    for row in rows:
        line = row.get("_line", "?")
        case_id = row.get("id")
        group = row.get("group")
        should_activate = row.get("should_activate")
        prompt = row.get("prompt")
        success = row.get("success_criteria")
        protected = row.get("protected_behaviors")

        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(f"{source}:{line}: id must be a non-empty string")
        elif case_id in ids:
            errors.append(f"{source}:{line}: duplicate id {case_id!r}")
        else:
            ids.add(case_id)

        if group not in expected:
            errors.append(f"{source}:{line}: invalid group {group!r} for suite {suite!r}")
        else:
            groups[group] += 1

        if type(should_activate) is not bool:
            errors.append(f"{source}:{line}: should_activate must be boolean")
        elif group in FIXED_ACTIVATION and should_activate is not FIXED_ACTIVATION[group]:
            errors.append(
                f"{source}:{line}: {group} cases must have "
                f"should_activate={FIXED_ACTIVATION[group]}"
            )

        if not isinstance(prompt, str) or not prompt.strip():
            errors.append(f"{source}:{line}: prompt must be a non-empty string")
        for field, value in (
            ("success_criteria", success),
            ("protected_behaviors", protected),
        ):
            if not isinstance(value, list) or not value:
                errors.append(f"{source}:{line}: {field} must be a non-empty list")
            elif any(not isinstance(item, str) or not item.strip() for item in value):
                errors.append(f"{source}:{line}: {field} entries must be non-empty strings")

    for group, count in expected.items():
        found = groups.get(group, 0)
        if count is None:
            if found == 0:
                errors.append(f"{source}: suite {suite!r} needs cases in group {group!r}")
        elif found != count:
            errors.append(f"{source}: group {group!r} expected {count} cases, found {found}")
    return errors


def validate_results(
    rows: list[dict[str, Any]], source: Path, case_ids: set[str],
    allow_repeats: bool = False,
) -> list[str]:
    """allow_repeats is set in multi-run mode, where N rows per case is the point."""
    errors: list[str] = []
    seen: set[str] = set()
    nullable_bools = ("activated", "success")
    nullable_nonnegative_ints = (
        "input_tokens",
        "output_tokens",
        "tool_calls",
        "wall_time_ms",
        "protected_failures",
    )

    for row in rows:
        line = row.get("_line", "?")
        case_id = row.get("id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{source}:{line}: id must be a non-empty string")
            continue
        if case_id in seen and not allow_repeats:
            errors.append(f"{source}:{line}: duplicate result id {case_id!r}")
        seen.add(case_id)
        if case_id not in case_ids:
            errors.append(f"{source}:{line}: unknown case id {case_id!r}")

        for field in nullable_bools:
            value = row.get(field)
            if value is not None and type(value) is not bool:
                errors.append(f"{source}:{line}: {field} must be boolean or null")

        for field in nullable_nonnegative_ints:
            value = row.get(field)
            if value is not None and (
                type(value) is not int or value < 0
            ):
                errors.append(
                    f"{source}:{line}: {field} must be a non-negative integer or null"
                )

        for field in ("grader", "artifact", "notes"):
            value = row.get(field)
            if value is not None and not isinstance(value, str):
                errors.append(f"{source}:{line}: {field} must be a string or null")
    return errors


def row_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in rows if isinstance(row.get("id"), str)}


def ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def activation_metrics(
    cases: list[dict[str, Any]], results: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    confusion = {"true_positive": 0, "false_positive": 0, "true_negative": 0, "false_negative": 0}
    missing: list[str] = []
    by_group: dict[str, dict[str, int]] = {
        group: {"correct": 0, "incorrect": 0, "missing": 0}
        for group in EXPECTED_GROUPS
    }

    for case in cases:
        case_id = case["id"]
        result = results.get(case_id, {})
        observed = result.get("activated")
        expected = case["should_activate"]
        group = case["group"]
        if type(observed) is not bool:
            missing.append(case_id)
            by_group[group]["missing"] += 1
            continue
        if observed == expected:
            by_group[group]["correct"] += 1
        else:
            by_group[group]["incorrect"] += 1
        if expected and observed:
            confusion["true_positive"] += 1
        elif not expected and observed:
            confusion["false_positive"] += 1
        elif not expected and not observed:
            confusion["true_negative"] += 1
        else:
            confusion["false_negative"] += 1

    tp = confusion["true_positive"]
    fp = confusion["false_positive"]
    tn = confusion["true_negative"]
    fn = confusion["false_negative"]
    return {
        **confusion,
        "precision": ratio(tp, tp + fp),
        "recall": ratio(tp, tp + fn),
        "specificity": ratio(tn, tn + fp),
        "scored": tp + fp + tn + fn,
        "missing_count": len(missing),
        "missing_ids": missing,
        "by_group": by_group,
    }


def total_tokens(row: dict[str, Any]) -> int | None:
    input_tokens = row.get("input_tokens")
    output_tokens = row.get("output_tokens")
    if type(input_tokens) is int and type(output_tokens) is int:
        return input_tokens + output_tokens
    return None


def condition_summary(
    cases: list[dict[str, Any]], results: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    success_values: list[bool] = []
    input_tokens: list[int] = []
    output_tokens: list[int] = []
    protected = 0
    protected_known = 0
    grader_known = 0
    artifact_known = 0
    missing_ids: list[str] = []

    for case in cases:
        case_id = case["id"]
        row = results.get(case_id)
        if row is None:
            missing_ids.append(case_id)
            continue
        if type(row.get("success")) is bool:
            success_values.append(row["success"])
        if type(row.get("input_tokens")) is int:
            input_tokens.append(row["input_tokens"])
        if type(row.get("output_tokens")) is int:
            output_tokens.append(row["output_tokens"])
        if type(row.get("protected_failures")) is int:
            protected += row["protected_failures"]
            protected_known += 1
        if isinstance(row.get("grader"), str) and row["grader"].strip():
            grader_known += 1
        if isinstance(row.get("artifact"), str) and row["artifact"].strip():
            artifact_known += 1

    return {
        "result_rows": len(results),
        "missing_result_count": len(missing_ids),
        "missing_result_ids": missing_ids,
        "success_known": len(success_values),
        "success_rate": ratio(sum(success_values), len(success_values)),
        "input_tokens_known": len(input_tokens),
        "input_tokens_total": sum(input_tokens) if input_tokens else None,
        "output_tokens_known": len(output_tokens),
        "output_tokens_total": sum(output_tokens) if output_tokens else None,
        "protected_failures_known": protected_known,
        "protected_failures_total": protected if protected_known else None,
        "grader_known": grader_known,
        "artifact_known": artifact_known,
    }


def paired_comparison(
    cases: list[dict[str, Any]],
    baseline: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    success_pairs: list[tuple[bool, bool]] = []
    token_pairs: list[tuple[int, int]] = []

    for case in cases:
        case_id = case["id"]
        base = baseline.get(case_id, {})
        cand = candidate.get(case_id, {})
        base_success = base.get("success")
        cand_success = cand.get("success")
        if type(base_success) is bool and type(cand_success) is bool:
            success_pairs.append((base_success, cand_success))
        base_tokens = total_tokens(base)
        cand_tokens = total_tokens(cand)
        if base_tokens is not None and cand_tokens is not None:
            token_pairs.append((base_tokens, cand_tokens))

    better = sum(not base and cand for base, cand in success_pairs)
    worse = sum(base and not cand for base, cand in success_pairs)
    ties = len(success_pairs) - better - worse
    base_successes = sum(base for base, _ in success_pairs)
    cand_successes = sum(cand for _, cand in success_pairs)

    base_token_total = sum(base for base, _ in token_pairs)
    cand_token_total = sum(cand for _, cand in token_pairs)
    deltas = [cand - base for base, cand in token_pairs]
    token_delta = cand_token_total - base_token_total if token_pairs else None
    token_percent = (
        round(100 * token_delta / base_token_total, 6)
        if token_pairs and base_token_total
        else None
    )

    return {
        "paired_success_count": len(success_pairs),
        "baseline_success_rate": ratio(base_successes, len(success_pairs)),
        "candidate_success_rate": ratio(cand_successes, len(success_pairs)),
        "success_delta_percentage_points": (
            round(100 * (cand_successes - base_successes) / len(success_pairs), 6)
            if success_pairs
            else None
        ),
        "candidate_better_count": better,
        "candidate_worse_count": worse,
        "tie_count": ties,
        "paired_token_count": len(token_pairs),
        "baseline_total_tokens": base_token_total if token_pairs else None,
        "candidate_total_tokens": cand_token_total if token_pairs else None,
        "total_token_delta": token_delta,
        "total_token_delta_percent": token_percent,
        "median_case_token_delta": statistics.median(deltas) if deltas else None,
    }


def multi_run_summary(
    cases: list[dict[str, Any]], rows: list[dict[str, Any]], min_runs: int
) -> dict[str, Any]:
    """Per-case pass rate over repeated runs, with under-powered cells named.

    A single run against a stochastic system is an anecdote. This refuses to
    print a rate for any case with fewer than `min_runs` observations rather
    than reporting 1/1 as 100%.
    """
    by_case: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        case_id = row.get("id")
        if isinstance(case_id, str):
            by_case.setdefault(case_id, []).append(row)

    per_case: dict[str, Any] = {}
    underpowered: list[str] = []
    unstable: list[str] = []
    graded_rates: list[float] = []

    for case in cases:
        case_id = case["id"]
        runs = by_case.get(case_id, [])
        known = [r["success"] for r in runs if type(r.get("success")) is bool]
        entry: dict[str, Any] = {"runs": len(runs), "graded": len(known)}
        if len(known) < min_runs:
            entry["pass_rate"] = None
            entry["status"] = (
                f"Insufficient data to verify: {len(known)} graded runs, "
                f"{min_runs} required"
            )
            underpowered.append(case_id)
        else:
            passes = sum(1 for value in known if value)
            rate = passes / len(known)
            entry["passes"] = passes
            entry["pass_rate"] = round(rate, 4)
            entry["status"] = "reported"
            graded_rates.append(rate)
            # Neither reliably safe nor reliably broken is the finding that
            # matters most for a gate, so it gets named rather than averaged away.
            if 0.0 < rate < 1.0:
                entry["stability"] = "mixed outcomes across identical runs"
                unstable.append(case_id)
            else:
                entry["stability"] = "consistent across graded runs"
        per_case[case_id] = entry

    graders = Counter(
        r.get("grader") for r in rows if isinstance(r.get("grader"), str)
    )
    deterministic = sum(
        count for grader, count in graders.items()
        if grader.lower().startswith("deterministic")
    )

    return {
        "min_runs": min_runs,
        "cases_total": len(cases),
        "cases_reportable": len(cases) - len(underpowered),
        "cases_underpowered": underpowered,
        "cases_with_mixed_outcomes": unstable,
        "mean_pass_rate_over_reportable": (
            round(statistics.fmean(graded_rates), 4) if graded_rates else None
        ),
        "graded_rows": sum(graders.values()),
        "deterministically_graded_rows": deterministic,
        "grader_note": (
            "Rows whose grader string does not start with 'deterministic' were "
            "decided by a person or a heuristic. Weigh them accordingly."
        ),
        "per_case": per_case,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--validate-cases", action="store_true")
    parser.add_argument(
        "--suite", choices=sorted(SUITES), default="activation",
        help="case-file layout to validate against (default: activation)",
    )
    parser.add_argument("--strict-completeness", action="store_true")
    parser.add_argument(
        "--min-runs", type=int, default=None,
        help="multi-run mode: require N graded runs per case before reporting a rate",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases, errors = load_jsonl(args.cases)
    errors.extend(validate_cases(cases, args.cases, args.suite))
    case_ids = {row.get("id") for row in cases if isinstance(row.get("id"), str)}

    candidate_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []
    if args.candidate:
        candidate_rows, candidate_errors = load_jsonl(args.candidate)
        errors.extend(candidate_errors)
        errors.extend(validate_results(
            candidate_rows, args.candidate, case_ids,
            allow_repeats=args.min_runs is not None))
    if args.baseline:
        baseline_rows, baseline_errors = load_jsonl(args.baseline)
        errors.extend(baseline_errors)
        errors.extend(validate_results(
            baseline_rows, args.baseline, case_ids,
            allow_repeats=args.min_runs is not None))

    if errors:
        print(json.dumps({"status": "failed", "errors": errors}, indent=2, sort_keys=True))
        return 1

    report: dict[str, Any] = {
        "status": "validated" if not args.candidate else "scored",
        "suite": args.suite,
        "case_count": len(cases),
        "group_counts": dict(Counter(case["group"] for case in cases)),
        "limitations": [
            "The script aggregates recorded observations; it does not run a model.",
            "Recorded success still requires an auditable deterministic or blinded grader.",
        ],
    }

    if args.min_runs is not None:
        # Multi-run mode replaces the single-row metrics rather than layering on
        # top: row_map keeps one row per id, which would quietly discard every
        # run but the last.
        if args.candidate:
            report["candidate_runs"] = multi_run_summary(
                cases, candidate_rows, args.min_runs)
        if args.baseline:
            report["baseline_runs"] = multi_run_summary(
                cases, baseline_rows, args.min_runs)
        report["limitations"].append(
            "Multi-run mode reports per-case pass rates only; activation "
            "precision/recall and token deltas need single-run files."
        )
        under = report.get("candidate_runs", {}).get("cases_underpowered", [])
        if under:
            report["status"] = "incomplete"
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1 if (args.strict_completeness and under) else 0

    incomplete = False
    if args.candidate:
        candidate = row_map(candidate_rows)
        report["activation"] = activation_metrics(cases, candidate)
        report["candidate"] = condition_summary(cases, candidate)
        incomplete = (
            report["activation"]["missing_count"] > 0
            or report["candidate"]["missing_result_count"] > 0
            or report["candidate"]["success_known"] != len(cases)
            or report["candidate"]["input_tokens_known"] != len(cases)
            or report["candidate"]["output_tokens_known"] != len(cases)
            or report["candidate"]["protected_failures_known"] != len(cases)
            or report["candidate"]["grader_known"] != len(cases)
        )

    if args.baseline:
        baseline = row_map(baseline_rows)
        report["baseline"] = condition_summary(cases, baseline)
        if args.candidate:
            report["paired_comparison"] = paired_comparison(cases, baseline, candidate)
        incomplete = incomplete or (
            report["baseline"]["missing_result_count"] > 0
            or report["baseline"]["success_known"] != len(cases)
            or report["baseline"]["input_tokens_known"] != len(cases)
            or report["baseline"]["output_tokens_known"] != len(cases)
            or report["baseline"]["protected_failures_known"] != len(cases)
            or report["baseline"]["grader_known"] != len(cases)
        )

    if incomplete:
        report["status"] = "incomplete"

    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.strict_completeness and incomplete else 0


if __name__ == "__main__":
    raise SystemExit(main())
