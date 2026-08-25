#!/usr/bin/env python3
"""Is the playbook learning, or just getting bigger?

A reader on the launch thread put it precisely: a self-distilling loop with
helpful/harmful counters is brittle over time, and claiming it will not
"over-constrain itself into paralysis" is not the same as showing it. Correct.
`govern_playbook.py` enforces the ratchet. Nothing measured whether the ratchet
is working.

This does. It reports what the playbook currently is, refuses to call a trend
from too few governance runs, and exits non-zero when a threshold is crossed so
it can sit in CI.

    python3 playbook_health.py playbook/playbook.md
    python3 playbook_health.py playbook/playbook.md --cap 60 --strict
    python3 playbook_health.py --self-test

The distinction that matters: a bullet with zero trials is a claim, not
knowledge. A playbook that is mostly claims is accumulating, not learning, and
that is the failure mode worth catching early.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

BULLET = re.compile(r"^\[([a-z][a-z0-9-]*-\d{5})\] helpful=(\d+) harmful=(\d+) :: (.*)$")
SECTION = re.compile(r"^##\s+(.+?)\s*$")

# Trend claims need history. Below this many recorded governance runs the
# honest output is the kernel's own phrase, not a smoothed line through noise.
MIN_RUNS_FOR_TREND = 5

# Admitted by merge_deltas with a quantitative claim and no evidence behind it.
# Distinct from "never tried": this one was a measurement nobody measured.
UNVERIFIED_TAG = "UNVERIFIED: "

THRESHOLDS = {
    # share of active bullets that have never been tried in a real task
    "unverified_share": 0.60,
    # share of active bullets that governance would retire on the next pass
    "at_risk_share": 0.15,
    # fraction of the cap consumed
    "cap_use": 0.90,
    # share admitted as an unbacked quantitative claim
    "unverified_tagged_share": 0.10,
}


def parse(path: Path) -> tuple[list[dict], list[str]]:
    bullets, errors = [], []
    section = "(none)"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [f"cannot read {path}: {exc}"]

    seen: set[str] = set()
    for number, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("# "):
            continue
        if (m := SECTION.match(line)):
            section = m.group(1)
            continue
        if not line.startswith("["):
            continue
        m = BULLET.match(line)
        if not m:
            errors.append(f"{path}:{number}: malformed bullet")
            continue
        bullet_id, helpful, harmful, rule = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
        if bullet_id in seen:
            errors.append(f"{path}:{number}: duplicate id {bullet_id}")
        seen.add(bullet_id)
        bullets.append({
            "id": bullet_id, "section": section, "helpful": helpful,
            "harmful": harmful, "trials": helpful + harmful, "rule": rule,
            # A rule with no trigger and no test cannot be falsified, which
            # makes it decoration rather than procedure.
            "testable": "Test:" in rule and "Trigger:" in rule,
            "tagged_unverified": rule.startswith(UNVERIFIED_TAG),
        })
    return bullets, errors


def read_log(path: Path) -> tuple[list[dict], list[str]]:
    if not path.exists():
        return [], [f"no decision log at {path}"]
    entries, notes = [], []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            notes.append(f"{path}:{number}: invalid JSON, skipped")
    return entries, notes


def share(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None


def report(bullets: list[dict], log: list[dict], cap: int) -> dict:
    total = len(bullets)
    unverified = [b for b in bullets if b["trials"] == 0]
    load_bearing = [b for b in bullets if b["helpful"] >= 2 and b["harmful"] == 0]
    at_risk = [b for b in bullets if b["harmful"] > 0 and b["harmful"] >= b["helpful"]]
    untestable = [b for b in bullets if not b["testable"]]
    tagged = [b for b in bullets if b["tagged_unverified"]]
    helpful_total = sum(b["helpful"] for b in bullets)
    harmful_total = sum(b["harmful"] for b in bullets)
    trials = helpful_total + harmful_total

    govern_runs = [e for e in log if e.get("action") == "govern"]
    retired = sum(len(e.get("report", {}).get("retire", [])) for e in govern_runs)
    evicted = sum(len(e.get("report", {}).get("evict", [])) for e in govern_runs)
    deduped = sum(len(e.get("report", {}).get("dedup", [])) for e in govern_runs)

    out = {
        "active_bullets": total,
        "cap": cap,
        "cap_use": share(total, cap),
        "sections": dict(Counter(b["section"] for b in bullets)),
        "verified": total - len(unverified),
        "unverified": len(unverified),
        "unverified_share": share(len(unverified), total),
        "load_bearing": len(load_bearing),
        "at_risk": len(at_risk),
        "at_risk_share": share(len(at_risk), total),
        "untestable": len(untestable),
        "unverified_tagged": len(tagged),
        "unverified_tagged_share": share(len(tagged), total),
        "total_trials": trials,
        "helpful_rate": share(helpful_total, trials),
        "governance_runs": len(govern_runs),
        "lifetime_retired": retired,
        "lifetime_evicted": evicted,
        "lifetime_deduped": deduped,
    }

    # The trend is the part the criticism was actually about, and it is the part
    # there is not enough history for. Say so instead of drawing a line.
    if len(govern_runs) < MIN_RUNS_FOR_TREND:
        out["trend"] = (
            f"Insufficient data to verify: {len(govern_runs)} governance runs "
            f"recorded, {MIN_RUNS_FOR_TREND} needed before a direction means anything."
        )
    else:
        churn = retired + evicted + deduped
        out["trend"] = {
            "removals_per_run": round(churn / len(govern_runs), 3),
            "note": ("Removals per run trending toward zero while active_bullets "
                     "climbs is the accretion signal. One number is not a trend; "
                     "compare across runs."),
        }

    breaches = []
    for key, limit in THRESHOLDS.items():
        value = out.get(key)
        if value is not None and value > limit:
            breaches.append(f"{key}={value} exceeds {limit}")
    out["breaches"] = breaches
    out["verdict"] = "attention" if breaches else "within thresholds"
    return out


def self_test() -> int:
    import tempfile

    failures = []
    sample = """# header
## gates
[gates-00001] helpful=3 harmful=0 :: Solid rule. Trigger: x. Test: y.
[gates-00002] helpful=0 harmful=0 :: Untried claim. Trigger: x. Test: y.
[gates-00003] helpful=1 harmful=4 :: Bad rule that governance should retire.
[gates-00004] helpful=0 harmful=0 :: UNVERIFIED: Cuts tokens by 40 percent. Trigger: x. Test: y.
"""
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "pb.md"
        p.write_text(sample, encoding="utf-8")
        bullets, errors = parse(p)
        if errors:
            failures.append(f"clean sample produced errors: {errors}")
        if len(bullets) != 4:
            failures.append(f"expected 4 bullets, parsed {len(bullets)}")

        r = report(bullets, [], cap=60)
        checks = {
            "active_bullets": 4, "unverified": 2, "load_bearing": 1,
            "at_risk": 1, "untestable": 1, "total_trials": 8,
            "unverified_tagged": 1,
        }
        for key, want in checks.items():
            if r[key] != want:
                failures.append(f"{key}: expected {want}, got {r[key]}")
        if not str(r["trend"]).startswith("Insufficient data"):
            failures.append("empty log should refuse a trend")
        if r["verdict"] != "attention":
            failures.append("33% unverified + 33% at_risk should breach a threshold")

        # A healthy playbook must come back clean.
        healthy = "## gates\n" + "".join(
            f"[gates-{i:05d}] helpful=3 harmful=0 :: Rule {i}. Trigger: x. Test: y.\n"
            for i in range(1, 11))
        p.write_text(healthy, encoding="utf-8")
        bullets, _ = parse(p)
        r = report(bullets, [], cap=60)
        if r["breaches"]:
            failures.append(f"healthy playbook flagged: {r['breaches']}")

        # Malformed lines must be reported, not silently dropped.
        p.write_text("## gates\n[gates-1] helpful=x harmful=0 :: broken\n", encoding="utf-8")
        _, errors = parse(p)
        if not errors:
            failures.append("malformed bullet was not reported")

    for line in failures:
        print(line, file=sys.stderr)
    total = 13
    print(f"self-test: {total - len(failures)}/{total} checks passed")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("playbook", nargs="?", help="path to playbook.md")
    parser.add_argument("--cap", type=int, default=60)
    parser.add_argument("--log", help="decision-log.jsonl (default: next to the playbook)")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 when a threshold is breached")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if not args.playbook:
        parser.print_help()
        return 2

    path = Path(args.playbook)
    bullets, errors = parse(path)
    log_path = Path(args.log) if args.log else path.parent / "decision-log.jsonl"
    log, notes = read_log(log_path)

    out = report(bullets, log, args.cap)
    out["parse_errors"] = errors
    out["log_notes"] = notes
    print(json.dumps(out, indent=2, sort_keys=True))

    if errors:
        return 1
    return 1 if (args.strict and out["breaches"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
