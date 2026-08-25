#!/usr/bin/env python3
"""One command that checks everything this repo claims about itself.

    python3 verify.py

The point, and it came from the launch thread: reviewing generated code costs
more than generating it did, and that bill lands on the reader. This does not
make the code shorter. It does mean you can find out in about ten seconds
whether the thing does what the README says, before deciding to read any of it.

Nothing here talks to a model or the network. Every check is deterministic and
runs offline. Exit code 0 means every claim below held on your machine.

What this does NOT tell you: whether the kernel changes how an agent behaves.
That needs matched runs against a real model, which is what evals/ is for, and
the honest state of that evidence is in the README.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILL = ROOT / "skill" / "dagx-agi-kernel"
SCRIPTS = SKILL / "scripts"
PY = sys.executable or "python3"


class Check:
    def __init__(self, name: str, argv: list[str], claim: str,
                 expect_zero: bool = True, cwd: Path | None = None):
        self.name, self.argv, self.claim = name, argv, claim
        self.expect_zero, self.cwd = expect_zero, cwd or ROOT

    def run(self) -> tuple[bool, str]:
        try:
            proc = subprocess.run(
                [PY, *self.argv], cwd=self.cwd, capture_output=True,
                text=True, timeout=120,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f"could not run: {exc}"
        ok = (proc.returncode == 0) if self.expect_zero else (proc.returncode != 0)
        tail = (proc.stdout or proc.stderr or "").strip().splitlines()
        detail = tail[-1][:110] if tail else f"exit {proc.returncode}"
        return ok, detail


def build_checks(fixture: Path) -> list[Check]:
    return [
        Check("kernel budget + structure",
              [str(SCRIPTS / "audit_kernel.py"), str(SKILL)],
              "SKILL.md is inside its byte budget and every link resolves"),
        Check("runtime self-test",
              [str(SCRIPTS / "harness_efficiency.py"), "--self-test"],
              "DAG validation, write-conflict detection and approval gates work"),
        Check("activation corpus",
              [str(SCRIPTS / "eval_kernel.py"), "--cases",
               str(SKILL / "evals" / "cases.jsonl"), "--validate-cases"],
              "25 activation, control and boundary cases are well formed"),
        Check("adversarial corpus",
              [str(SCRIPTS / "eval_kernel.py"), "--cases",
               str(SKILL / "evals" / "adversarial.jsonl"),
               "--validate-cases", "--suite", "adversarial"],
              "every bypass reported by a reader is a reproducible case"),
        Check("safety grader",
              [str(SCRIPTS / "safety_fixture.py"), "--self-test"],
              "the deletion verdict is a hash comparison, not a human's opinion"),
        Check("safety grader catches a deletion",
              [str(SCRIPTS / "safety_fixture.py"), "grade", "--fixture",
               str(fixture), "--baseline", "0000000000000000", "--id", "activate-06"],
              "a mutated fixture fails the gate", expect_zero=False),
        Check("playbook health",
              [str(SCRIPTS / "playbook_health.py"),
               str(SKILL / "playbook" / "playbook.md"), "--strict"],
              "procedural memory is within its drift thresholds"),
        Check("memory admission gate rejects",
              [str(SCRIPTS / "merge_deltas.py"), str(fixture.parent / "pb.md"),
               str(fixture.parent / "bad_delta.json")],
              "an environment-specific lesson cannot enter procedural memory",
              expect_zero=False),
        Check("cost policy arithmetic",
              [str(SCRIPTS / "jscore.py"), "--self-test"],
              "the J-score exchange rates are derived and proven, not asserted"),
        Check("cost policy refuses guesses",
              [str(SCRIPTS / "jscore.py"), "--score", "--quality", "0.9"],
              "scoring without measured cost and latency is refused",
              expect_zero=False),
        Check("enforcement guard",
              [str(ROOT / "hooks" / "perfectify_guard.py"), "--self-test"],
              "the deterministic hook blocks what it says it blocks"),
        Check("held-out threat coverage",
              [str(ROOT / "hooks" / "perfectify_guard.py"), "--threat-corpus"],
              "commands written from the threat, not from the pattern list, are caught"),
    ]


def main() -> int:
    if not SKILL.exists():
        print(f"expected the skill at {SKILL}, not found", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        fixture = Path(tmp) / "fixture.json"
        subprocess.run(
            [PY, str(SCRIPTS / "safety_fixture.py"), "init", "--out", str(fixture)],
            capture_output=True, text=True, cwd=ROOT,
        )
        # A throwaway playbook and a delta the gate must refuse.
        (Path(tmp) / "pb.md").write_text(
            "## gates\n"
            "[gates-00001] helpful=1 harmful=0 :: Seed. Trigger: x. Test: y.\n",
            encoding="utf-8")
        (Path(tmp) / "bad_delta.json").write_text(json.dumps([{
            "op": "ADD", "section": "gates",
            "content": "Restart the worker on localhost:8080 when /var/run/app.pid is stale.",
        }]), encoding="utf-8")
        checks = build_checks(fixture)
        results = [(c, *c.run()) for c in checks]

    width = max(len(c.name) for c in checks)
    print()
    for check, ok, detail in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {check.name.ljust(width)}   {check.claim}")
        if not ok:
            print(f"        {' ' * width}   -> {detail}")

    failed = [c.name for c, ok, _ in results if not ok]
    print()
    if failed:
        print(f"{len(failed)} of {len(results)} checks failed: {', '.join(failed)}")
        return 1

    # Reported, not asserted. The enforcement layer's configuration is the
    # reader's decision, and its digest is the thing worth writing down.
    proc = subprocess.run(
        [PY, str(ROOT / "hooks" / "perfectify_guard.py"), "--status"],
        capture_output=True, text=True, cwd=ROOT,
    )
    try:
        status = json.loads(proc.stdout)
        print(f"{len(results)} of {len(results)} checks passed. "
              f"Guard: {status['rules']} rules, digest {status['rules_digest']}, "
              f"identity gate {status['identity_gate']}.")
        print("Record that digest somewhere the agent cannot reach and compare "
              "it on a schedule; an edited rule set is otherwise silent.")
    except (json.JSONDecodeError, KeyError):
        print(f"{len(results)} of {len(results)} checks passed.")

    print("\nNot covered here: whether any of this changes how a model behaves. "
          "That needs matched runs, see evals/runs/README.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
