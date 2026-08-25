#!/usr/bin/env python3
"""Deterministic playbook merge with an admission gate (V1.5).

Applies a delta file (JSON list of operations) to playbook/playbook.md:
  {"op": "ADD",    "section": "gates", "content": "...", "evidence": "runs/..."}
  {"op": "UPDATE", "id": "gates-00001", "helpful": 1}   -> counter increment
  {"op": "REMOVE", "id": "gates-00001"}                 -> delete line

Usage:
  python3 merge_deltas.py playbook/playbook.md deltas.json [--strict]

Why the gate exists, and where it came from: the sibling research repo
(github.com/dankofly/dagx) makes the point that agent memory systems gate what
gets RETRIEVED by relevance and almost never gate what gets ADMITTED by
evidence, so anything the agent produced can become tomorrow's context,
including its own inventions. This script admitted every proposed bullet, which
is precisely that hole. Invariant 11 forbade it in prose; nothing enforced it.

Ported from DAGx's confidence classifier: a claim carrying a number, a
percentage, a currency, a date or a legal term can never be admitted as an
ordinary rule without evidence attached. The cap runs AFTER the proposal, in
code, so a confidently wrong model cannot promote an unsupported measurement.
Such a bullet is admitted with an explicit UNVERIFIED marker instead, which
playbook_health.py then counts, or rejected outright under --strict.

Environment-specific bullets are rejected, not tagged. The playbook's own
governance rule already says so; this makes it a mechanism rather than a wish.

Fail direction, deliberate and opposite to the PreToolUse hook: the execution
boundary fails OPEN, because a guard that crashes closed blocks every tool call
and gets uninstalled within a day. The memory boundary fails CLOSED, because a
bad admission is permanent and silent.

Exit codes: 0 ok; 2 usage; 3 malformed delta; 4 unknown id; 5 rejected by the gate.
Deterministic: same inputs -> same output bytes. No LLM involved.
"""
import json
import re
import sys

BULLET = re.compile(r"^\[([a-z][a-z0-9-]*-\d{5})\] helpful=(\d+) harmful=(\d+) :: (.*)$")
SECTION = re.compile(r"^## (.+)$")

UNVERIFIED = "UNVERIFIED: "

# Ported from DAGx audit/util.js isHardClaim. A rule that asserts a quantity is
# a measurement, and a measurement without a recorded run is a guess.
HARD_CLAIM = re.compile(
    r"\d|%|percent|[$€£]|(eur|usd)|"
    r"(19|20)\d{2}|p\s*[=~≈]|median|mean|average|"
    r"faster|slower|reduce[sd]?|improve[sd]?",
    re.IGNORECASE,
)

# The playbook's own govern-00001 rule, enforced instead of merely stated.
ENV_SPECIFIC = re.compile(
    r"(/[A-Za-z0-9_.-]+){2,}|[A-Za-z]:\|localhost|127\.0\.0\.1|"
    r"port\s*\d{2,5}|:\d{4,5}|https?://|@[A-Za-z0-9-]+\.[a-z]{2,}",
    re.IGNORECASE,
)


def gate_add(content, evidence, strict):
    """Return (verdict, content, reason). verdict is admit | tag | reject."""
    if ENV_SPECIFIC.search(content):
        return "reject", content, "environment-specific (path, host, port or URL)"
    if HARD_CLAIM.search(content) and not evidence:
        if strict:
            return "reject", content, "quantitative claim without evidence"
        return "tag", UNVERIFIED + content, "quantitative claim without evidence"
    return "admit", content, ""


def parse(text):
    lines = text.splitlines()
    out = []
    section = None
    for ln in lines:
        m = SECTION.match(ln.strip())
        if m and not BULLET.match(ln.strip()):
            section = m.group(1)
            out.append({"kind": "section", "name": section, "raw": ln})
            continue
        m = BULLET.match(ln.strip())
        if m:
            out.append({"kind": "bullet", "id": m.group(1), "helpful": int(m.group(2)),
                        "harmful": int(m.group(3)), "content": m.group(4), "section": section,
                        "raw": ln})
            continue
        out.append({"kind": "other", "raw": ln})
    return out


def render(items):
    lines = [it["raw"] for it in items]
    return "\n".join(lines).rstrip("\n") + "\n"


def next_id(items, section):
    import hashlib
    raw = (section or "gen").lower().replace(" ", "-")
    # stable 8-char prefix + short hash suffix -> no cross-section collisions
    prefix = re.sub(r"[^a-z0-9-]", "", raw)[:8] or "gen"
    h = hashlib.md5(raw.encode()).hexdigest()[:4]
    stem = f"{prefix}-{h}"
    # rsplit: the prefix itself may contain hyphens (e.g. section "failure-recovery")
    nums = [int(it["id"].rsplit("-", 1)[1]) for it in items
            if it["kind"] == "bullet" and it["id"].startswith(stem)]
    return f"{stem}-{(max(nums) + 1) if nums else 1:05d}"


def main():
    argv = [a for a in sys.argv[1:] if a != "--strict"]
    strict = "--strict" in sys.argv
    if len(argv) != 2:
        print(__doc__)
        sys.exit(2)
    path, delta_path = argv
    text = open(path, encoding="utf-8").read()
    deltas = json.load(open(delta_path, encoding="utf-8"))
    if not isinstance(deltas, list):
        print("delta file must be a JSON list")
        sys.exit(3)

    items = parse(text)
    by_id = {it["id"]: it for it in items if it["kind"] == "bullet"}

    for d in deltas:
        op = d.get("op")
        if op == "ADD":
            section = d.get("section") or "general"
            content = d.get("content", "").strip()
            content = re.sub(r"^\[[^\]]+\]\s*", "", content)  # strip inline id prefixes
            if not content:
                print("ADD without content:", d)
                sys.exit(3)
            verdict, content, why = gate_add(content, d.get("evidence"), strict)
            if verdict == "reject":
                print(f"REJECTED by admission gate ({why}): {content[:70]}")
                sys.exit(5)
            if verdict == "tag":
                print(f"admitted UNVERIFIED ({why}): {content[:60]}")
            nid = next_id(items, section)
            # find section anchor, append after last bullet of that section (or at EOF)
            idx = max((i for i, it in enumerate(items)
                       if it["kind"] == "bullet" and it.get("section") == section),
                      default=len(items) - 1)
            items.insert(idx + 1, {"kind": "bullet", "id": nid, "helpful": 0, "harmful": 0,
                                   "content": content, "section": section,
                                   "raw": f"[{nid}] helpful=0 harmful=0 :: {content}"})
        elif op in ("UPDATE", "REMOVE"):
            bid = d.get("id")
            if bid not in by_id:
                print("unknown bullet id:", bid)
                sys.exit(4)
            it = by_id[bid]
            if op == "UPDATE":
                it["helpful"] += int(d.get("helpful", 0))
                it["harmful"] += int(d.get("harmful", 0))
                it["raw"] = f"[{it['id']}] helpful={it['helpful']} harmful={it['harmful']} :: {it['content']}"
            else:
                items.remove(it)
        else:
            print("unknown op:", op)
            sys.exit(3)

    open(path, "w", encoding="utf-8").write(render(items))
    bullets = [it for it in items if it["kind"] == "bullet"]
    unverified = sum(1 for it in bullets if it["content"].startswith(UNVERIFIED))
    print(f"merged {len(deltas)} ops -> {len(bullets)} active bullets "
          f"({unverified} unverified)")


if __name__ == "__main__":
    main()
