#!/usr/bin/env python3
"""Deterministic structural audit for the DAGx Agent Skill package."""

from __future__ import annotations

import json
import re
import sys
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
    if root_lines > 500:
        warnings.append("SKILL.md exceeds the recommended 500 lines")
    if PLACEHOLDER_RE.search(text):
        errors.append("unfinished scaffold placeholder found in SKILL.md")
    if "—" in text:
        warnings.append("long em dash found")

    markdown_files = sorted(root.rglob("*.md"))
    package_files = sorted(path for path in root.rglob("*") if path.is_file())
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

    if (root / "README.md").exists():
        warnings.append("README.md is not needed for an Agent Skill package")

    metrics = {
        "root_lines": root_lines,
        "root_words": len(text.split()),
        "root_bytes": len(text.encode("utf-8")),
        "markdown_files": len(markdown_files),
        "package_files": len(package_files),
        "package_bytes": sum(path.stat().st_size for path in package_files),
        "checked_relative_links": checked_links,
        "references": len(references),
        "orphan_references": len(orphan_references),
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
