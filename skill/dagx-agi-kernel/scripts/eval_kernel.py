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


EXPECTED_GROUPS = {"activate": 10, "negative_control": 10, "boundary": 5}


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


def validate_cases(rows: list[dict[str, Any]], source: Path) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    groups: Counter[str] = Counter()

    if len(rows) != sum(EXPECTED_GROUPS.values()):
        errors.append(
            f"{source}: expected {sum(EXPECTED_GROUPS.values())} cases, found {len(rows)}"
        )

    for row in rows:
        line = row.get("_line", "?")
        case_id = row.get("id")
        group = row.get("group")
        expected = row.get("should_activate")
        prompt = row.get("prompt")
        success = row.get("success_criteria")
        protected = row.get("protected_behaviors")

        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(f"{source}:{line}: id must be a non-empty string")
        elif case_id in ids:
            errors.append(f"{source}:{line}: duplicate id {case_id!r}")
        else:
            ids.add(case_id)

        if group not in EXPECTED_GROUPS:
            errors.append(f"{source}:{line}: invalid group {group!r}")
        else:
            groups[group] += 1

        if type(expected) is not bool:
            errors.append(f"{source}:{line}: should_activate must be boolean")
        elif group == "activate" and expected is not True:
            errors.append(f"{source}:{line}: activate cases must expect activation")
        elif group == "negative_control" and expected is not False:
            errors.append(f"{source}:{line}: negative controls must not expect activation")

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

    if dict(groups) != EXPECTED_GROUPS:
        errors.append(
            f"{source}: expected group counts {EXPECTED_GROUPS}, found {dict(groups)}"
        )
    return errors


def validate_results(
    rows: list[dict[str, Any]], source: Path, case_ids: set[str]
) -> list[str]:
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
        if case_id in seen:
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--validate-cases", action="store_true")
    parser.add_argument("--strict-completeness", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases, errors = load_jsonl(args.cases)
    errors.extend(validate_cases(cases, args.cases))
    case_ids = {row.get("id") for row in cases if isinstance(row.get("id"), str)}

    candidate_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []
    if args.candidate:
        candidate_rows, candidate_errors = load_jsonl(args.candidate)
        errors.extend(candidate_errors)
        errors.extend(validate_results(candidate_rows, args.candidate, case_ids))
    if args.baseline:
        baseline_rows, baseline_errors = load_jsonl(args.baseline)
        errors.extend(baseline_errors)
        errors.extend(validate_results(baseline_rows, args.baseline, case_ids))

    if errors:
        print(json.dumps({"status": "failed", "errors": errors}, indent=2, sort_keys=True))
        return 1

    report: dict[str, Any] = {
        "status": "validated" if not args.candidate else "scored",
        "case_count": len(cases),
        "group_counts": dict(Counter(case["group"] for case in cases)),
        "limitations": [
            "The script aggregates recorded observations; it does not run a model.",
            "Recorded success still requires an auditable deterministic or blinded grader.",
        ],
    }

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
