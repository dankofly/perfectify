#!/usr/bin/env python3
"""Deterministic structural audit for the DAGx Agent Skill package."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
PLACEHOLDER_RE = re.compile(r"\b(?:TODO|TBD|PLACEHOLDER)\b")
ALLOWED_TOP_LEVEL = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
MAX_ROOT_BYTES = 10_000
EXPECTED_EVAL_GROUPS = {"activate": 10, "negative_control": 10, "boundary": 5}


def parse_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    if not text.startswith("---\n"):
        return {}, ["SKILL.md does not start with YAML frontmatter"]
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, ["SKILL.md frontmatter is not closed"]

    raw = text[4:end]
    values: dict[str, str] = {}
    top_keys: list[str] = []
    for line in raw.splitlines():
        if not line.strip() or line.startswith((" ", "\t")):
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not match:
            errors.append(f"invalid top-level frontmatter line: {line!r}")
            continue
        key, value = match.groups()
        top_keys.append(key)
        values[key] = value.strip().strip('"').strip("'")

    unknown = sorted(set(top_keys) - ALLOWED_TOP_LEVEL)
    if unknown:
        errors.append(f"nonstandard top-level frontmatter keys: {unknown}")
    return values, errors


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    skill = root / "SKILL.md"
    errors: list[str] = []
    warnings: list[str] = []

    if not skill.is_file():
        print(json.dumps({"status": "failed", "errors": ["SKILL.md not found"]}))
        return 1

    text = skill.read_text(encoding="utf-8")
    frontmatter, fm_errors = parse_frontmatter(text)
    errors.extend(fm_errors)

    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")
    if not NAME_RE.fullmatch(name):
        errors.append("name must use lowercase alphanumerics and single hyphens")
    if name != root.name:
        errors.append(f"skill name {name!r} does not match folder {root.name!r}")
    if not (1 <= len(name) <= 64):
        errors.append("name length must be 1..64 characters")
    if not (1 <= len(description) <= 1024):
        errors.append("description length must be 1..1024 characters")

    root_lines = len(text.splitlines())
    root_bytes = len(text.encode("utf-8"))
    if root_lines > 500:
        warnings.append("SKILL.md exceeds the recommended 500 lines")
    if root_bytes > MAX_ROOT_BYTES:
        errors.append(
            f"SKILL.md exceeds the {MAX_ROOT_BYTES}-byte context budget: {root_bytes}"
        )
    if PLACEHOLDER_RE.search(text):
        errors.append("unfinished scaffold placeholder found in SKILL.md")
    if "—" in text:
        warnings.append("long em dash found")
    if "PX::ACTIVATE" in text or "arglexmax" in text:
        errors.append("formal control notation must remain outside SKILL.md")

    markdown_files = sorted(root.rglob("*.md"))
    package_files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    checked_links = 0
    root_relative_targets: set[Path] = set()
    for source in markdown_files:
        source_text = source.read_text(encoding="utf-8")
        if not source_text.strip():
            errors.append(f"empty markdown file: {source.relative_to(root)}")
        if PLACEHOLDER_RE.search(source_text):
            errors.append(f"placeholder found: {source.relative_to(root)}")
        for target in LINK_RE.findall(source_text):
            target = target.split("#", 1)[0]
            if not target or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
                continue
            checked_links += 1
            resolved = (source.parent / target).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                errors.append(f"link escapes skill root: {source.relative_to(root)} -> {target}")
                continue
            if not resolved.exists():
                errors.append(f"missing link target: {source.relative_to(root)} -> {target}")
            elif source == skill:
                root_relative_targets.add(resolved)

    references = sorted((root / "references").glob("*.md"))
    orphan_references = [path for path in references if path.resolve() not in root_relative_targets]
    for reference in orphan_references:
        errors.append(f"reference is not discoverable from SKILL.md: {reference.relative_to(root)}")

    audit_script = root / "scripts" / "audit_kernel.py"
    if not audit_script.is_file():
        errors.append("required maintenance audit is missing: scripts/audit_kernel.py")

    required_runtime_files = [
        root / "scripts" / "eval_kernel.py",
        root / "scripts" / "harness_efficiency.py",
        root / "evals" / "cases.jsonl",
        root / "templates" / "trial-ledger.md",
        root / "references" / "evaluation-protocol.md",
        root / "references" / "formal-control-state.md",
        root / "references" / "harness-efficiency.md",
        root / "schemas" / "harness-state.schema.json",
        root / "schemas" / "trace-event.schema.json",
        root / "examples" / "harness-state.example.json",
        root / "examples" / "traces.example.jsonl",
    ]
    for required in required_runtime_files:
        if not required.is_file():
            errors.append(f"required runtime file is missing: {required.relative_to(root)}")

    efficiency_script = root / "scripts" / "harness_efficiency.py"
    # NTFS has no POSIX exec bits; scripts run via `python script.py` there.
    if os.name != "nt":
        for executable in (audit_script, root / "scripts" / "eval_kernel.py", efficiency_script):
            if executable.is_file() and executable.stat().st_mode & 0o111 == 0:
                errors.append(f"required script is not executable: {executable.relative_to(root)}")

    schemas = sorted((root / "schemas").glob("*.schema.json"))
    for schema in schemas:
        try:
            payload = json.loads(schema.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid schema JSON in {schema.relative_to(root)}: {exc.msg}")
            continue
        if payload.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append(f"schema does not declare draft 2020-12: {schema.relative_to(root)}")
        if payload.get("type") != "object" or not payload.get("title"):
            errors.append(f"schema lacks object type or title: {schema.relative_to(root)}")

    runtime_self_test = "missing"
    if efficiency_script.is_file():
        try:
            completed = subprocess.run(
                [sys.executable, str(efficiency_script), "--self-test"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            runtime_self_test = "error"
            errors.append(f"harness runtime self-test could not run: {exc}")
        else:
            runtime_self_test = "passed" if completed.returncode == 0 else "failed"
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout).strip()
                errors.append(f"harness runtime self-test failed: {detail}")

    eval_cases = 0
    eval_groups: Counter[str] = Counter()
    eval_ids: set[str] = set()
    eval_file = root / "evals" / "cases.jsonl"
    if eval_file.is_file():
        for line_number, line in enumerate(
            eval_file.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(
                    f"invalid eval JSON at evals/cases.jsonl:{line_number}: {exc.msg}"
                )
                continue
            eval_cases += 1
            case_id = case.get("id")
            if not isinstance(case_id, str) or not case_id:
                errors.append(f"missing eval id at evals/cases.jsonl:{line_number}")
            elif case_id in eval_ids:
                errors.append(f"duplicate eval id at evals/cases.jsonl:{line_number}: {case_id}")
            else:
                eval_ids.add(case_id)
            group = case.get("group")
            if isinstance(group, str):
                eval_groups[group] += 1
        if eval_cases != sum(EXPECTED_EVAL_GROUPS.values()):
            errors.append(
                f"expected {sum(EXPECTED_EVAL_GROUPS.values())} eval cases, found {eval_cases}"
            )
        if dict(eval_groups) != EXPECTED_EVAL_GROUPS:
            errors.append(
                f"expected eval groups {EXPECTED_EVAL_GROUPS}, found {dict(eval_groups)}"
            )

    if (root / "README.md").exists():
        warnings.append("README.md is not needed for an Agent Skill package")

    metrics = {
        "root_lines": root_lines,
        "root_words": len(text.split()),
        "root_bytes": root_bytes,
        "root_byte_limit": MAX_ROOT_BYTES,
        "markdown_files": len(markdown_files),
        "package_files": len(package_files),
        "package_bytes": sum(path.stat().st_size for path in package_files),
        "checked_relative_links": checked_links,
        "references": len(references),
        "orphan_references": len(orphan_references),
        "schemas": len(schemas),
        "runtime_self_test": runtime_self_test,
        "eval_cases": eval_cases,
        "eval_groups": dict(eval_groups),
    }
    result = {
        "status": "failed" if errors else "passed_with_warnings" if warnings else "passed",
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
