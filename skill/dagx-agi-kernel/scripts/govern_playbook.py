#!/usr/bin/env python3
"""Ratchet governance for the Perfectify playbook (V0.8+).

Implements the verified anti-drift recipe (arXiv:2605.19576):
  - outcome-driven retirement: harmful >= helpful after >= min_trials -> REMOVE
  - bounded active cap: evict lowest-contribution bullets beyond cap
  - dedup: identical normalized content merges counters

Usage: python3 govern_playbook.py playbook/playbook.md [--cap 60] [--min-trials 5] [--apply]
Without --apply, prints a dry-run report only.
"""
import json
import re
import sys
from collections import Counter

BULLET = re.compile(r"^\[([a-z][a-z0-9-]*-\d{5})\] helpful=(\d+) harmful=(\d+) :: (.*)$")


def load(path):
    return [(m.group(1), int(m.group(2)), int(m.group(3)), m.group(4))
            for ln in open(path, encoding="utf-8")
            if (m := BULLET.match(ln.strip()))]


def norm(c):
    return re.sub(r"\W+", " ", c.lower()).strip()


def similar(a, b, threshold=0.82):
    """Prefix-window Jaccard on word sets to catch near-duplicates."""
    wa, wb = set(norm(a).split()), set(norm(b).split())
    if not wa or not wb:
        return False
    inter = len(wa & wb)
    return inter / max(1, min(len(wa), len(wb))) >= threshold


def main():
    args = sys.argv[1:]
    if not args or "-h" in args or "--help" in args:
        print(__doc__.strip())
        sys.exit(0 if args else 2)
    apply = "--apply" in args
    cap, min_trials = 60, 5
    if "--cap" in args:
        cap = int(args[args.index("--cap") + 1])
    if "--min-trials" in args:
        min_trials = int(args[args.index("--min-trials") + 1])
    path = args[0]

    bullets = load(path)
    report = {"total": len(bullets), "retire": [], "evict": [], "dedup": []}

    # dedupe by normalized content: keep highest (helpful - harmful), sum counters
    seen = []
    keep_map = {}
    for b in sorted(bullets, key=lambda x: -(x[1] - x[2])):
        twin = next((s for s in seen if similar(s[3], b[3])), None)
        if twin is not None:
            report["dedup"].append({"keep": twin[0], "merge": b[0]})
        else:
            seen.append(b)
            keep_map[b[0]] = b

    unique = list(seen)

    for bid, h, harm, c in unique:
        trials = h + harm
        if trials >= min_trials and harm >= h:
            report["retire"].append({"id": bid, "helpful": h, "harmful": harm})

    survivors = [b for b in unique if b[0] not in {r["id"] for r in report["retire"]}]
    if len(survivors) > cap:
        ranked = sorted(survivors, key=lambda x: (x[1] - x[2], -(x[1] + x[2])))
        for b in ranked[: len(survivors) - cap]:
            report["evict"].append({"id": b[0], "score": b[1] - b[2]})

    print(json.dumps(report, indent=2))

    if apply and (report["retire"] or report["evict"] or report["dedup"]):
        dead = {r["id"] for r in report["retire"]} | {e["id"] for e in report["evict"]}
        dupes = {d["merge"] for d in report["dedup"]}
        dead |= dupes
        keep = {b[0]: b for b in bullets if b[0] not in dead}
        # fold merged counters into keepers
        merge_map = {d["merge"]: d["keep"] for d in report["dedup"]}
        for src, dst in merge_map.items():
            s = next(b for b in bullets if b[0] == src)
            k = keep[dst]
            keep[dst] = (k[0], k[1] + s[1], k[2] + s[2], k[3])

        out = []
        for ln in open(path, encoding="utf-8"):
            m = BULLET.match(ln.strip())
            if not m:
                out.append(ln.rstrip("\n"))
                continue
            bid = m.group(1)
            if bid in dead:
                continue
            h, harm, c = keep[bid][1], keep[bid][2], keep[bid][3]
            out.append(f"[{bid}] helpful={h} harmful={harm} :: {c}")
        open(path, "w", encoding="utf-8").write("\n".join(out).rstrip("\n") + "\n")

        # append decision log entry (SkillHone pattern)
        with open(path.replace("playbook.md", "decision-log.jsonl"), "a") as f:
            f.write(json.dumps({"action": "govern", "report": report}) + "\n")
        print(f"applied: retired/evicted/deduped -> {len(load(path))} active bullets")


if __name__ == "__main__":
    main()
