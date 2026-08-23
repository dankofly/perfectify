#!/usr/bin/env python3
"""Deterministic state validation, context compilation, and trace analysis."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


STATE_REQUIRED = {
    "schema_version", "task_id", "goal", "acceptance_gates",
    "protected_behaviors", "authority", "budget", "stable_context_refs",
    "tool_index", "knowns", "unknowns", "evidence", "nodes", "champion",
    "checkpoint", "active_node",
}
BUDGET_FIELDS = ("input_tokens", "output_tokens", "tool_calls", "wall_time_ms", "cost")
TRACE_REQUIRED = {
    "schema_version", "timestamp", "task_id", "node_id", "attempt", "model",
    "model_class", "input_tokens", "cached_input_tokens", "output_tokens",
    "tool_calls", "tool_latency_ms", "model_latency_ms", "wall_time_ms",
    "retry_count", "activated", "verifier_result", "protected_failures",
    "rollback", "success", "terminal", "stop_reason",
}
TRACE_OPTIONAL = {"trace_id", "span_id", "cost"}
MODEL_CLASSES = {"none", "small", "medium", "strong"}
NODE_STATUSES = {"pending", "ready", "running", "completed", "failed", "blocked", "skipped"}
GATE_STATUSES = {"pending", "passed", "failed", "blocked"}
SIDE_EFFECTS = {"read", "reversible_write", "external", "irreversible"}
VERIFIER_KINDS = {"deterministic", "readback", "model", "human"}
VERIFIER_RESULTS = {"pass", "fail", "inconclusive", "not_run"}
HEX = set("0123456789abcdef")


class ContractError(ValueError):
    """Raised for invalid input contracts."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ContractError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid JSON in {path}: {exc}") from exc


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and set(value[7:]) <= HEX
    )


def _scope_allows(scope: str, target: str) -> bool:
    if scope == target:
        return True
    if scope.endswith("*"):
        return target.startswith(scope[:-1])
    return any(target.startswith(scope + separator) for separator in (":", "/", "#"))


def _check_exact_keys(
    obj: Any,
    required: set[str],
    optional: set[str],
    path: str,
    errors: list[str],
) -> bool:
    if not isinstance(obj, dict):
        errors.append(f"{path} must be an object")
        return False
    missing = sorted(required - set(obj))
    extra = sorted(set(obj) - required - optional)
    if missing:
        errors.append(f"{path} missing keys: {', '.join(missing)}")
    if extra:
        errors.append(f"{path} has unknown keys: {', '.join(extra)}")
    return not missing


def _unique_id_map(items: Any, path: str, errors: list[str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(items, list):
        errors.append(f"{path} must be an array")
        return result
    for index, item in enumerate(items):
        item_path = f"{path}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_path} must be an object")
            continue
        item_id = item.get("id")
        if not _is_nonempty_string(item_id):
            errors.append(f"{item_path}.id must be a nonempty string")
            continue
        if item_id in result:
            errors.append(f"duplicate id {item_id!r} in {path}")
        else:
            result[item_id] = item
    return result


def _string_array(value: Any, path: str, errors: list[str], unique: bool = True) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{path} must be an array")
        return []
    output: list[str] = []
    for index, item in enumerate(value):
        if not _is_nonempty_string(item):
            errors.append(f"{path}[{index}] must be a nonempty string")
        else:
            output.append(item)
    if unique and len(output) != len(set(output)):
        errors.append(f"{path} must contain unique values")
    return output


def _validate_budget(value: Any, path: str, errors: list[str]) -> None:
    if not _check_exact_keys(value, set(BUDGET_FIELDS), set(), path, errors):
        return
    for field in BUDGET_FIELDS:
        item = value.get(field)
        if item is None:
            continue
        expected = (int, float) if field == "cost" else (int,)
        if isinstance(item, bool) or not isinstance(item, expected) or item < 0:
            errors.append(f"{path}.{field} must be null or a nonnegative number")


def _topological_waves(nodes: dict[str, dict[str, Any]]) -> tuple[list[list[str]], list[str]]:
    deps: dict[str, set[str]] = {
        node_id: {dep for dep in node.get("deps", []) if dep in nodes}
        for node_id, node in nodes.items()
    }
    remaining = set(nodes)
    done: set[str] = set()
    waves: list[list[str]] = []
    while remaining:
        wave = sorted(node_id for node_id in remaining if deps[node_id] <= done)
        if not wave:
            return waves, sorted(remaining)
        waves.append(wave)
        done.update(wave)
        remaining.difference_update(wave)
    return waves, []


def _ancestors(nodes: dict[str, dict[str, Any]], node_id: str) -> set[str]:
    found: set[str] = set()
    stack = list(nodes[node_id].get("deps", []))
    while stack:
        current = stack.pop()
        if current in found or current not in nodes:
            continue
        found.add(current)
        stack.extend(nodes[current].get("deps", []))
    return found


def validate_state(state: Any) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not _check_exact_keys(state, STATE_REQUIRED, set(), "$", errors):
        return {"valid": False, "errors": errors, "warnings": warnings, "waves": []}

    if state.get("schema_version") != "1":
        errors.append("$.schema_version must equal '1'")
    for field in ("task_id", "goal"):
        if not _is_nonempty_string(state.get(field)):
            errors.append(f"$.{field} must be a nonempty string")

    gates = _unique_id_map(state.get("acceptance_gates"), "$.acceptance_gates", errors)
    tools = _unique_id_map(state.get("tool_index"), "$.tool_index", errors)
    knowns = _unique_id_map(state.get("knowns"), "$.knowns", errors)
    unknowns = _unique_id_map(state.get("unknowns"), "$.unknowns", errors)
    evidence = _unique_id_map(state.get("evidence"), "$.evidence", errors)
    nodes = _unique_id_map(state.get("nodes"), "$.nodes", errors)
    stable_refs = _unique_id_map(state.get("stable_context_refs"), "$.stable_context_refs", errors)

    input_namespaces = [set(knowns), set(unknowns), set(evidence)]
    input_ids = set().union(*input_namespaces)
    for left_index, left in enumerate(input_namespaces):
        for right in input_namespaces[left_index + 1:]:
            for duplicate in sorted(left & right):
                errors.append(f"input reference id {duplicate!r} is ambiguous across namespaces")

    if not isinstance(state.get("protected_behaviors"), list):
        errors.append("$.protected_behaviors must be an array")
    else:
        _string_array(state["protected_behaviors"], "$.protected_behaviors", errors)

    authority = state.get("authority")
    authority_ok = _check_exact_keys(
        authority, {"read_scopes", "write_scopes", "external_actions"}, set(), "$.authority", errors
    )
    if authority_ok:
        _string_array(authority.get("read_scopes"), "$.authority.read_scopes", errors)
        _string_array(authority.get("write_scopes"), "$.authority.write_scopes", errors)
        if not isinstance(authority.get("external_actions"), bool):
            errors.append("$.authority.external_actions must be boolean")
    _validate_budget(state.get("budget"), "$.budget", errors)

    for gate_id, gate in gates.items():
        path = f"$.acceptance_gates[{gate_id}]"
        if _check_exact_keys(gate, {"id", "priority", "condition", "status"}, set(), path, errors):
            if isinstance(gate.get("priority"), bool) or not isinstance(gate.get("priority"), int) or gate["priority"] < 1:
                errors.append(f"{path}.priority must be an integer >= 1")
            if not _is_nonempty_string(gate.get("condition")):
                errors.append(f"{path}.condition must be a nonempty string")
            if gate.get("status") not in GATE_STATUSES:
                errors.append(f"{path}.status is invalid")

    for ref_id, ref in stable_refs.items():
        path = f"$.stable_context_refs[{ref_id}]"
        if _check_exact_keys(ref, {"id", "uri", "digest"}, set(), path, errors):
            if not _is_nonempty_string(ref.get("uri")):
                errors.append(f"{path}.uri must be a nonempty string")
            if not _is_digest(ref.get("digest")):
                errors.append(f"{path}.digest must be sha256:<64 lowercase hex>")

    for tool_id, tool in tools.items():
        path = f"$.tool_index[{tool_id}]"
        if _check_exact_keys(tool, {"id", "summary", "schema_ref"}, {"schema"}, path, errors):
            if not _is_nonempty_string(tool.get("summary")):
                errors.append(f"{path}.summary must be a nonempty string")
            if tool.get("schema_ref") is not None and not _is_nonempty_string(tool.get("schema_ref")):
                errors.append(f"{path}.schema_ref must be null or a nonempty string")
            if "schema" in tool and tool["schema"] is not None and not isinstance(tool["schema"], dict):
                errors.append(f"{path}.schema must be null or an object")

    for known_id, known in knowns.items():
        path = f"$.knowns[{known_id}]"
        if _check_exact_keys(known, {"id", "claim", "evidence_refs"}, set(), path, errors):
            if not _is_nonempty_string(known.get("claim")):
                errors.append(f"{path}.claim must be a nonempty string")
            refs = _string_array(known.get("evidence_refs"), f"{path}.evidence_refs", errors)
            for ref in refs:
                if ref not in evidence:
                    errors.append(f"{path}.evidence_refs references unknown evidence {ref!r}")

    for unknown_id, unknown in unknowns.items():
        path = f"$.unknowns[{unknown_id}]"
        if _check_exact_keys(unknown, {"id", "question", "blocks"}, set(), path, errors):
            if not _is_nonempty_string(unknown.get("question")):
                errors.append(f"{path}.question must be a nonempty string")
            for ref in _string_array(unknown.get("blocks"), f"{path}.blocks", errors):
                if ref not in nodes:
                    errors.append(f"{path}.blocks references unknown node {ref!r}")

    for evidence_id, item in evidence.items():
        path = f"$.evidence[{evidence_id}]"
        if _check_exact_keys(item, {"id", "kind", "artifact_ref", "digest", "freshness"}, set(), path, errors):
            for field in ("kind", "artifact_ref"):
                if not _is_nonempty_string(item.get(field)):
                    errors.append(f"{path}.{field} must be a nonempty string")
            if item.get("digest") is not None and not _is_digest(item.get("digest")):
                errors.append(f"{path}.digest must be null or sha256:<64 lowercase hex>")
            if item.get("freshness") is not None and not _is_nonempty_string(item.get("freshness")):
                errors.append(f"{path}.freshness must be null or a nonempty string")

    node_required = {
        "id", "objective", "deps", "status", "model_class", "escalation_conditions",
        "tool_refs", "input_refs", "expected_evidence", "write_set", "side_effect",
        "idempotency_key", "approval_gate", "readback_required", "recovery_ref",
        "verifier", "result_ref", "budget",
    }
    for node_id, node in nodes.items():
        path = f"$.nodes[{node_id}]"
        if not _check_exact_keys(node, node_required, set(), path, errors):
            continue
        if not _is_nonempty_string(node.get("objective")):
            errors.append(f"{path}.objective must be a nonempty string")
        deps = _string_array(node.get("deps"), f"{path}.deps", errors)
        for dep in deps:
            if dep not in nodes:
                errors.append(f"{path}.deps references unknown node {dep!r}")
            if dep == node_id:
                errors.append(f"{path}.deps cannot contain itself")
        if node.get("status") not in NODE_STATUSES:
            errors.append(f"{path}.status is invalid")
        if node.get("model_class") not in MODEL_CLASSES:
            errors.append(f"{path}.model_class is invalid")
        _string_array(node.get("escalation_conditions"), f"{path}.escalation_conditions", errors)
        for ref in _string_array(node.get("tool_refs"), f"{path}.tool_refs", errors):
            if ref not in tools:
                errors.append(f"{path}.tool_refs references unknown tool {ref!r}")
        for ref in _string_array(node.get("input_refs"), f"{path}.input_refs", errors):
            if ref not in input_ids:
                errors.append(f"{path}.input_refs references unknown input {ref!r}")
        _string_array(node.get("expected_evidence"), f"{path}.expected_evidence", errors, unique=False)
        write_set = _string_array(node.get("write_set"), f"{path}.write_set", errors)
        side_effect = node.get("side_effect")
        if side_effect not in SIDE_EFFECTS:
            errors.append(f"{path}.side_effect is invalid")
        verifier = node.get("verifier")
        if _check_exact_keys(verifier, {"kind", "ref"}, set(), f"{path}.verifier", errors):
            if verifier.get("kind") not in VERIFIER_KINDS:
                errors.append(f"{path}.verifier.kind is invalid")
            if not _is_nonempty_string(verifier.get("ref")):
                errors.append(f"{path}.verifier.ref must be a nonempty string")
        for field in ("idempotency_key", "approval_gate", "recovery_ref", "result_ref"):
            if node.get(field) is not None and not _is_nonempty_string(node.get(field)):
                errors.append(f"{path}.{field} must be null or a nonempty string")
        if not isinstance(node.get("readback_required"), bool):
            errors.append(f"{path}.readback_required must be boolean")
        _validate_budget(node.get("budget"), f"{path}.budget", errors)

        if side_effect != "read":
            if not write_set:
                errors.append(f"{path} non-read side effect requires a nonempty write_set")
            if not _is_nonempty_string(node.get("idempotency_key")):
                errors.append(f"{path} non-read side effect requires idempotency_key")
            if not _is_nonempty_string(node.get("recovery_ref")):
                errors.append(f"{path} non-read side effect requires recovery_ref")
            write_scopes = authority.get("write_scopes", []) if isinstance(authority, dict) else []
            for target in write_set:
                if not any(_scope_allows(scope, target) for scope in write_scopes if isinstance(scope, str)):
                    errors.append(f"{path}.write_set target {target!r} is outside authority.write_scopes")
        elif write_set:
            errors.append(f"{path} read side effect must have an empty write_set")
        if side_effect in {"external", "irreversible"}:
            gate = node.get("approval_gate")
            if not _is_nonempty_string(gate):
                errors.append(f"{path} {side_effect} side effect requires approval_gate")
            elif gate not in gates:
                errors.append(f"{path}.approval_gate references unknown gate {gate!r}")
            if node.get("readback_required") is not True:
                errors.append(f"{path} {side_effect} side effect requires readback_required=true")
            if isinstance(authority, dict) and authority.get("external_actions") is not True:
                errors.append(f"{path} requires authority.external_actions=true")

    waves, cycle_nodes = _topological_waves(nodes)
    if cycle_nodes:
        errors.append("dependency cycle detected among nodes: " + ", ".join(cycle_nodes))

    if not cycle_nodes:
        ancestors = {node_id: _ancestors(nodes, node_id) for node_id in nodes}
        active_nodes = [node_id for node_id, node in nodes.items() if node.get("status") != "skipped"]
        for index, left_id in enumerate(active_nodes):
            left_writes = set(nodes[left_id].get("write_set", []))
            if not left_writes:
                continue
            for right_id in active_nodes[index + 1:]:
                if left_id in ancestors[right_id] or right_id in ancestors[left_id]:
                    continue
                overlap = sorted(left_writes & set(nodes[right_id].get("write_set", [])))
                if overlap:
                    errors.append(
                        f"unordered write conflict between {left_id!r} and {right_id!r}: {', '.join(overlap)}"
                    )

    champion = state.get("champion")
    if _check_exact_keys(champion, {"artifact_ref", "verified_gate_ids"}, set(), "$.champion", errors):
        if champion.get("artifact_ref") is not None and not _is_nonempty_string(champion.get("artifact_ref")):
            errors.append("$.champion.artifact_ref must be null or a nonempty string")
        for gate_id in _string_array(champion.get("verified_gate_ids"), "$.champion.verified_gate_ids", errors):
            if gate_id not in gates:
                errors.append(f"$.champion.verified_gate_ids references unknown gate {gate_id!r}")

    checkpoint = state.get("checkpoint")
    checkpoint_required = {"completed_nodes", "state_digest", "next_safe_node", "attempted_idempotency_keys"}
    if _check_exact_keys(checkpoint, checkpoint_required, set(), "$.checkpoint", errors):
        for node_id in _string_array(checkpoint.get("completed_nodes"), "$.checkpoint.completed_nodes", errors):
            if node_id not in nodes:
                errors.append(f"$.checkpoint.completed_nodes references unknown node {node_id!r}")
        digest = checkpoint.get("state_digest")
        if digest is not None and not _is_digest(digest):
            errors.append("$.checkpoint.state_digest must be null or sha256:<64 lowercase hex>")
        next_node = checkpoint.get("next_safe_node")
        if next_node is not None and next_node not in nodes:
            errors.append(f"$.checkpoint.next_safe_node references unknown node {next_node!r}")
        _string_array(
            checkpoint.get("attempted_idempotency_keys"),
            "$.checkpoint.attempted_idempotency_keys",
            errors,
        )

    active_node = state.get("active_node")
    if active_node is not None and active_node not in nodes:
        errors.append(f"$.active_node references unknown node {active_node!r}")
    if not gates:
        warnings.append("no acceptance gates declared")
    budget = state.get("budget")
    if isinstance(budget, dict) and budget and all(value is None for value in budget.values()):
        warnings.append("all task budget fields are unmeasured")

    return {"valid": not errors, "errors": errors, "warnings": warnings, "waves": waves}


def compile_context(state: dict[str, Any], node_id: str | None, load_tool_schemas: bool) -> dict[str, Any]:
    report = validate_state(state)
    if not report["valid"]:
        raise ContractError("invalid state:\n- " + "\n- ".join(report["errors"]))
    selected_id = node_id if node_id is not None else state.get("active_node")
    if selected_id is None:
        raise ContractError("no node selected and active_node is null")
    node_map = {item["id"]: item for item in state["nodes"]}
    if selected_id not in node_map:
        raise ContractError(f"unknown node {selected_id!r}")
    node = copy.deepcopy(node_map[selected_id])
    incomplete_deps = [
        dep for dep in node["deps"] if node_map[dep]["status"] not in {"completed", "skipped"}
    ]
    if incomplete_deps:
        raise ContractError("selected node has incomplete dependencies: " + ", ".join(sorted(incomplete_deps)))
    if node["side_effect"] in {"external", "irreversible"}:
        gates = {gate["id"]: gate for gate in state["acceptance_gates"]}
        gate_id = node["approval_gate"]
        if gate_id is None or gates[gate_id]["status"] != "passed":
            raise ContractError(f"selected node requires passed approval gate {gate_id!r}")

    known_map = {item["id"]: item for item in state["knowns"]}
    unknown_map = {item["id"]: item for item in state["unknowns"]}
    evidence_map = {item["id"]: item for item in state["evidence"]}
    tool_map = {item["id"]: item for item in state["tool_index"]}
    selected_inputs = set(node["input_refs"])
    selected_knowns = [copy.deepcopy(known_map[item]) for item in sorted(selected_inputs & set(known_map))]
    evidence_ids = set(selected_inputs & set(evidence_map))
    for known in selected_knowns:
        evidence_ids.update(known["evidence_refs"])
    selected_evidence = [copy.deepcopy(evidence_map[item]) for item in sorted(evidence_ids)]
    selected_unknowns = [copy.deepcopy(unknown_map[item]) for item in sorted(selected_inputs & set(unknown_map))]

    selected_tools: list[dict[str, Any]] = []
    for tool_id in sorted(node["tool_refs"]):
        source = tool_map[tool_id]
        item = {"id": source["id"], "summary": source["summary"], "schema_ref": source["schema_ref"]}
        if load_tool_schemas and source.get("schema") is not None:
            item["schema"] = copy.deepcopy(source["schema"])
        selected_tools.append(item)

    stable_prefix = {
        "schema_version": state["schema_version"],
        "stable_context_refs": sorted(copy.deepcopy(state["stable_context_refs"]), key=lambda item: item["id"]),
        "tools": selected_tools,
    }
    dependency_results = [
        {"id": dep, "status": node_map[dep]["status"], "result_ref": node_map[dep]["result_ref"]}
        for dep in sorted(node["deps"])
    ]
    task_delta = {
        "task_id": state["task_id"],
        "goal": state["goal"],
        "unresolved_acceptance_gates": [
            copy.deepcopy(gate) for gate in state["acceptance_gates"] if gate["status"] != "passed"
        ],
        "protected_behaviors": copy.deepcopy(state["protected_behaviors"]),
        "authority": copy.deepcopy(state["authority"]),
        "remaining_budget": copy.deepcopy(state["budget"]),
        "active_node": node,
        "dependency_results": dependency_results,
        "knowns": selected_knowns,
        "unknowns": selected_unknowns,
        "evidence": selected_evidence,
        "champion": copy.deepcopy(state["champion"]),
        "checkpoint": copy.deepcopy(state["checkpoint"]),
    }
    return {
        "schema_version": "1",
        "stable_prefix_key": sha256_digest(stable_prefix),
        "task_delta_digest": sha256_digest(task_delta),
        "stable_prefix": stable_prefix,
        "task_delta": task_delta,
    }


def _trace_error(event: Any, line_number: int) -> list[str]:
    errors: list[str] = []
    path = f"line {line_number}"
    if not _check_exact_keys(event, TRACE_REQUIRED, TRACE_OPTIONAL, path, errors):
        return errors
    if event.get("schema_version") != "1":
        errors.append(f"{path}.schema_version must equal '1'")
    for field in ("timestamp", "task_id", "node_id"):
        if not _is_nonempty_string(event.get(field)):
            errors.append(f"{path}.{field} must be a nonempty string")
    timestamp = event.get("timestamp")
    if _is_nonempty_string(timestamp):
        try:
            parsed_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"{path}.timestamp must be an ISO 8601 date-time")
        else:
            if "T" not in timestamp or parsed_timestamp.tzinfo is None:
                errors.append(f"{path}.timestamp must include time and UTC offset")
    for field in ("trace_id", "span_id", "model", "stop_reason"):
        if event.get(field) is not None and not _is_nonempty_string(event.get(field)):
            errors.append(f"{path}.{field} must be null or a nonempty string")
    if event.get("model_class") not in MODEL_CLASSES:
        errors.append(f"{path}.model_class is invalid")
    if isinstance(event.get("attempt"), bool) or not isinstance(event.get("attempt"), int) or event["attempt"] < 1:
        errors.append(f"{path}.attempt must be an integer >= 1")
    if isinstance(event.get("retry_count"), bool) or not isinstance(event.get("retry_count"), int) or event["retry_count"] < 0:
        errors.append(f"{path}.retry_count must be a nonnegative integer")
    integer_metrics = ("input_tokens", "cached_input_tokens", "output_tokens", "tool_calls")
    number_metrics = ("tool_latency_ms", "model_latency_ms", "wall_time_ms", "cost")
    for field in integer_metrics:
        value = event.get(field)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            errors.append(f"{path}.{field} must be null or a nonnegative integer")
    for field in number_metrics:
        value = event.get(field)
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or not math.isfinite(value)
        ):
            errors.append(f"{path}.{field} must be null or a finite nonnegative number")
    cached = event.get("cached_input_tokens")
    total_input = event.get("input_tokens")
    if cached is not None and total_input is not None and cached > total_input:
        errors.append(f"{path}.cached_input_tokens cannot exceed input_tokens")
    for field in ("activated", "rollback", "success", "terminal"):
        if not isinstance(event.get(field), bool):
            errors.append(f"{path}.{field} must be boolean")
    if event.get("verifier_result") not in VERIFIER_RESULTS:
        errors.append(f"{path}.verifier_result is invalid")
    _string_array(event.get("protected_failures"), f"{path}.protected_failures", errors)
    return errors


def load_traces(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ContractError(f"cannot read {path}: {exc}") from exc
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    attempt_keys: set[tuple[str, str, int]] = set()
    for line_number, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_number}: invalid JSON: {exc}")
            continue
        event_errors = _trace_error(event, line_number)
        errors.extend(event_errors)
        if not event_errors:
            key = (event["task_id"], event["node_id"], event["attempt"])
            if key in attempt_keys:
                errors.append(f"line {line_number}: duplicate task/node/attempt {key!r}")
                continue
            attempt_keys.add(key)
            events.append(event)
    if errors:
        raise ContractError("invalid traces:\n- " + "\n- ".join(errors))
    if not events:
        raise ContractError("trace file contains no events")
    return events


def _sum_known(events: Iterable[dict[str, Any]], field: str) -> tuple[float | int | None, int, int]:
    values = [event.get(field) for event in events]
    known = [value for value in values if value is not None]
    return (sum(known) if known else None, len(known), len(values) - len(known))


def analyze_traces(events: list[dict[str, Any]]) -> dict[str, Any]:
    metric_fields = (
        "input_tokens", "cached_input_tokens", "output_tokens", "tool_calls",
        "tool_latency_ms", "model_latency_ms", "wall_time_ms", "cost",
    )
    totals: dict[str, Any] = {}
    missingness: dict[str, dict[str, int]] = {}
    for field in metric_fields:
        total, known, missing = _sum_known(events, field)
        totals[field] = total
        missingness[field] = {"known_events": known, "missing_events": missing}

    paired_cache_events = [
        event for event in events
        if event.get("input_tokens") is not None and event.get("cached_input_tokens") is not None
    ]
    input_total = sum(event["input_tokens"] for event in paired_cache_events)
    cached_total = sum(event["cached_input_tokens"] for event in paired_cache_events)
    cache_ratio = None
    if input_total > 0:
        cache_ratio = cached_total / input_total

    terminal_by_task: dict[str, dict[str, Any]] = {}
    per_task_events: dict[str, list[dict[str, Any]]] = defaultdict(list)
    per_class_events: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        per_task_events[event["task_id"]].append(event)
        per_class_events[event["model_class"]].append(event)
        if event["terminal"]:
            terminal_by_task[event["task_id"]] = event

    per_task: dict[str, Any] = {}
    for task_id in sorted(per_task_events):
        task_events = per_task_events[task_id]
        terminal = terminal_by_task.get(task_id)
        per_task[task_id] = {
            "events": len(task_events),
            "attempts": sum(1 for _ in task_events),
            "retries": sum(event["retry_count"] for event in task_events),
            "protected_failures": sum(len(event["protected_failures"]) for event in task_events),
            "terminal_observed": terminal is not None,
            "success": terminal["success"] if terminal is not None else None,
            "stop_reason": terminal["stop_reason"] if terminal is not None else None,
        }

    per_model_class: dict[str, Any] = {}
    for model_class in sorted(per_class_events):
        class_events = per_class_events[model_class]
        class_totals = {field: _sum_known(class_events, field)[0] for field in metric_fields}
        per_model_class[model_class] = {
            "events": len(class_events),
            "successful_events": sum(1 for event in class_events if event["success"]),
            "totals": class_totals,
        }

    terminal_events = list(terminal_by_task.values())
    return {
        "schema_version": "1",
        "event_count": len(events),
        "task_count": len(per_task_events),
        "terminal_task_count": len(terminal_events),
        "terminal_success_count": sum(1 for event in terminal_events if event["success"]),
        "terminal_success_rate": (
            sum(1 for event in terminal_events if event["success"]) / len(terminal_events)
            if terminal_events else None
        ),
        "protected_failure_count": sum(len(event["protected_failures"]) for event in events),
        "rollback_count": sum(1 for event in events if event["rollback"]),
        "retry_count": sum(event["retry_count"] for event in events),
        "cache_read_ratio": cache_ratio,
        "cache_ratio_event_count": len(paired_cache_events),
        "cache_ratio_definition": "sum(cached_input_tokens) / sum(input_tokens) over events where both are known",
        "totals": totals,
        "missingness": missingness,
        "per_model_class": per_model_class,
        "per_task": per_task,
    }


def _empty_budget() -> dict[str, None]:
    return {field: None for field in BUDGET_FIELDS}


def _valid_fixture() -> dict[str, Any]:
    digest = "sha256:" + "0" * 64
    return {
        "schema_version": "1",
        "task_id": "fixture",
        "goal": "Produce verified output",
        "acceptance_gates": [{"id": "g1", "priority": 1, "condition": "tests pass", "status": "pending"}],
        "protected_behaviors": ["preserve baseline"],
        "authority": {"read_scopes": ["repo"], "write_scopes": ["repo"], "external_actions": False},
        "budget": _empty_budget(),
        "stable_context_refs": [{"id": "kernel", "uri": "skill://kernel", "digest": digest}],
        "tool_index": [
            {"id": "read", "summary": "Read an artifact", "schema_ref": "schema://read", "schema": {"type": "object"}},
            {"id": "test", "summary": "Run deterministic tests", "schema_ref": "schema://test"},
            {"id": "unused", "summary": "Must not leak", "schema_ref": "schema://unused"},
        ],
        "knowns": [
            {"id": "k1", "claim": "baseline exists", "evidence_refs": ["e1"]},
            {"id": "k_unused", "claim": "irrelevant", "evidence_refs": ["e_unused"]},
        ],
        "unknowns": [{"id": "u1", "question": "Does the test pass?", "blocks": ["n2"]}],
        "evidence": [
            {"id": "e1", "kind": "artifact", "artifact_ref": "baseline", "digest": digest, "freshness": None},
            {"id": "e_unused", "kind": "artifact", "artifact_ref": "unused", "digest": digest, "freshness": None},
        ],
        "nodes": [
            {
                "id": "n1", "objective": "Inspect", "deps": [], "status": "completed", "model_class": "none",
                "escalation_conditions": [], "tool_refs": ["read"], "input_refs": ["k1"],
                "expected_evidence": ["inspection"], "write_set": [], "side_effect": "read",
                "idempotency_key": None, "approval_gate": None, "readback_required": False,
                "recovery_ref": None, "verifier": {"kind": "deterministic", "ref": "parse"},
                "result_ref": "result://n1", "budget": _empty_budget(),
            },
            {
                "id": "n2", "objective": "Test", "deps": ["n1"], "status": "ready", "model_class": "none",
                "escalation_conditions": [], "tool_refs": ["test"], "input_refs": ["u1"],
                "expected_evidence": ["test report"], "write_set": [], "side_effect": "read",
                "idempotency_key": None, "approval_gate": None, "readback_required": False,
                "recovery_ref": None, "verifier": {"kind": "deterministic", "ref": "tests"},
                "result_ref": None, "budget": _empty_budget(),
            },
        ],
        "champion": {"artifact_ref": "baseline", "verified_gate_ids": []},
        "checkpoint": {
            "completed_nodes": ["n1"], "state_digest": digest, "next_safe_node": "n2",
            "attempted_idempotency_keys": [],
        },
        "active_node": "n2",
    }


def self_test() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append({"name": name, "passed": bool(condition), "detail": detail})

    fixture = _valid_fixture()
    valid_report = validate_state(fixture)
    check("valid state passes", valid_report["valid"], "; ".join(valid_report["errors"]))
    check("topological waves", valid_report["waves"] == [["n1"], ["n2"]], str(valid_report["waves"]))

    cycle = copy.deepcopy(fixture)
    cycle["nodes"][0]["deps"] = ["n2"]
    check("cycle rejected", any("cycle" in item for item in validate_state(cycle)["errors"]))

    bad_dep = copy.deepcopy(fixture)
    bad_dep["nodes"][1]["deps"] = ["missing"]
    check("unknown dependency rejected", any("unknown node" in item for item in validate_state(bad_dep)["errors"]))

    bad_tool = copy.deepcopy(fixture)
    bad_tool["nodes"][1]["tool_refs"] = ["missing"]
    check("unknown tool rejected", any("unknown tool" in item for item in validate_state(bad_tool)["errors"]))

    conflict = copy.deepcopy(fixture)
    for node in conflict["nodes"]:
        node.update({
            "deps": [], "write_set": ["repo:file"], "side_effect": "reversible_write",
            "idempotency_key": f"key-{node['id']}", "recovery_ref": "backup://repo",
        })
    check("unordered write conflict rejected", any("write conflict" in item for item in validate_state(conflict)["errors"]))

    external = copy.deepcopy(fixture)
    external["authority"]["external_actions"] = True
    external["nodes"][1].update({
        "side_effect": "external", "write_set": ["remote:issue"], "idempotency_key": None,
        "approval_gate": None, "readback_required": False, "recovery_ref": None,
    })
    external_errors = validate_state(external)["errors"]
    check(
        "unguarded external action rejected",
        all(any(term in item for item in external_errors) for term in ("idempotency_key", "approval_gate", "readback_required", "recovery_ref")),
        "; ".join(external_errors),
    )

    compiled = compile_context(fixture, None, False)
    delta_text = canonical_json(compiled["task_delta"])
    prefix_text = canonical_json(compiled["stable_prefix"])
    check("unreferenced known excluded", "k_unused" not in delta_text)
    check("unreferenced evidence excluded", "e_unused" not in delta_text)
    check("unselected tool excluded", "unused" not in prefix_text)
    reordered = copy.deepcopy(fixture)
    reordered["stable_context_refs"][0] = dict(reversed(list(reordered["stable_context_refs"][0].items())))
    second = compile_context(reordered, None, False)
    check("stable key deterministic", compiled["stable_prefix_key"] == second["stable_prefix_key"])

    blocked = copy.deepcopy(fixture)
    blocked["authority"]["external_actions"] = True
    blocked["authority"]["write_scopes"] = ["remote"]
    blocked["nodes"][1].update({
        "side_effect": "external", "write_set": ["remote:issue"], "idempotency_key": "issue-1",
        "approval_gate": "g1", "readback_required": True, "recovery_ref": "readback://issue",
    })
    try:
        compile_context(blocked, "n2", False)
    except ContractError as exc:
        check("pending approval blocks compilation", "passed approval gate" in str(exc), str(exc))
    else:
        check("pending approval blocks compilation", False, "external node compiled without approval")

    events = [
        {
            "schema_version": "1", "timestamp": "2026-01-01T00:00:00Z", "task_id": "t1", "node_id": "n1",
            "attempt": 1, "model": "m", "model_class": "small", "input_tokens": 100,
            "cached_input_tokens": 40, "output_tokens": 10, "tool_calls": 1, "tool_latency_ms": 5,
            "model_latency_ms": 10, "wall_time_ms": 15, "cost": 0.1, "retry_count": 0,
            "activated": True, "verifier_result": "pass", "protected_failures": [], "rollback": False,
            "success": True, "terminal": True, "stop_reason": "verified",
        },
        {
            "schema_version": "1", "timestamp": "2026-01-01T00:00:01Z", "task_id": "t2", "node_id": "n1",
            "attempt": 1, "model": None, "model_class": "none", "input_tokens": None,
            "cached_input_tokens": None, "output_tokens": None, "tool_calls": 1, "tool_latency_ms": 2,
            "model_latency_ms": None, "wall_time_ms": 2, "retry_count": 1, "activated": False,
            "verifier_result": "fail", "protected_failures": ["baseline"], "rollback": True,
            "success": False, "terminal": True, "stop_reason": "protected failure",
        },
    ]
    trace_errors = [error for index, event in enumerate(events, 1) for error in _trace_error(event, index)]
    check("trace fixtures valid", not trace_errors, "; ".join(trace_errors))
    analysis = analyze_traces(events)
    check("trace token totals", analysis["totals"]["input_tokens"] == 100)
    check("trace cache ratio", analysis["cache_read_ratio"] == 0.4)
    check("trace protected failures", analysis["protected_failure_count"] == 1)
    check("no composite score", "score" not in analysis and "composite_score" not in analysis)

    failures = [item for item in checks if not item["passed"]]
    return {"passed": not failures, "checks": checks, "failure_count": len(failures)}


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run deterministic runtime tests")
    subparsers = parser.add_subparsers(dest="command")

    validate = subparsers.add_parser("validate-state", help="validate a harness state")
    validate.add_argument("--state", required=True, type=Path)

    compile_parser = subparsers.add_parser("compile-context", help="compile minimal context for one node")
    compile_parser.add_argument("--state", required=True, type=Path)
    compile_parser.add_argument("--node")
    compile_parser.add_argument("--load-tool-schemas", action="store_true")

    analyze = subparsers.add_parser("analyze-traces", help="validate and summarize JSONL traces")
    analyze.add_argument("--traces", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.self_test:
            result = self_test()
            print_json(result)
            return 0 if result["passed"] else 1
        if args.command == "validate-state":
            report = validate_state(load_json(args.state))
            print_json(report)
            return 0 if report["valid"] else 1
        if args.command == "compile-context":
            print_json(compile_context(load_json(args.state), args.node, args.load_tool_schemas))
            return 0
        if args.command == "analyze-traces":
            print_json(analyze_traces(load_traces(args.traces)))
            return 0
        build_parser().print_help(sys.stderr)
        return 2
    except ContractError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
