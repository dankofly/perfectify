#!/usr/bin/env python3
"""Deterministic playbook merge for Perfectify V0.8+ (ACE-style, no LLM).

Applies a delta file (JSON list of operations) to playbook/playbook.md:
  {"op": "ADD",    "section": "gates", "content": "..."}            -> new bullet, counters 0/0
  {"op": "UPDATE", "id": "gates-00001", "helpful": 1}                -> counter increment (or "harmful": 1)
  {"op": "REMOVE", "id": "gates-00001"}                              -> delete line

Usage:
  python3 merge_deltas.py playbook/playbook.md deltas.json

Exit codes: 0 ok; 2 usage; 3 malformed delta; 4 unknown id for UPDATE/REMOVE.
Deterministic: same inputs -> same output bytes. No LLM involved.
"""
import json
import re
import sys

BULLET = re.compile(r"^\[([a-z][a-z0-9-]*-\d{5})\] helpful=(\d+) harmful=(\d+) :: (.*)$")
SECTION = re.compile(r"^## (.+)$")


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
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    path, delta_path = sys.argv[1], sys.argv[2]
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
    print(f"merged {len(deltas)} ops -> {len(bullets)} active bullets")


if __name__ == "__main__":
    main()
