# Perfectify

![Version](https://img.shields.io/badge/version-V1.1-f59e0b)
![Agent Skill](https://img.shields.io/badge/type-Agent%20Skill-0f766e)
![Evidence](https://img.shields.io/badge/behaviorally--evaluated-3%2F3%20gates%20held-16a34a)

> **The agent skill that stops disasters, learns from every task, and improves the loop that improves it.**

Perfectify is a portable control kernel for AI coding agents (Claude Code, Codex, Hermes, OpenCode, and any harness that loads Agent Skills). It turns your agent from a brilliant amnesiac into a disciplined engineer: it refuses irreversible mistakes, verifies its own work, remembers every lesson across sessions, and gets measurably better at the work you give it most.

---

## Why 10,000+ developers need this

Every agent has shipped one of these:

| The incident | What it cost | Perfectify's answer |
| --- | --- | --- |
| Agent bulk-deleted "inactive" production accounts without asking | Data loss, trust gone | **HARD STOP invariant**: dry-run list + exactly one approval question, turn ends. Proven under an "execute now" stress prompt: 3/3 stops. |
| Agent claimed "fixed, tests pass" on a flaky suite | Silent regressions for weeks | **Acceptance evidence gates**: 60+ consecutive green runs, measured residual failure probability (p < 1/1000), matched timing baselines |
| Agent's "improvement" broke what already worked | Net-negative velocity | **Champion preservation**: changes promote only after baseline + protected-case comparison; rollback always exists |
| Same mistake re-explained every session | You are the agent's memory | **Self-learning playbook**: lessons distilled each task, merged deterministically, governed against drift |

## The three systems

### 1. Evidence-gated execution
Eleven core invariants ("executed != completed", "confidence != evidence", "new != better") plus a four-mode effort router keep the agent cheap on easy tasks and rigorous on risky ones. External or irreversible actions run through a state compiler whose approval gate is enforced by code, not politeness: `compile-context` refuses to release a deletion node until a human gate passes.

### 2. Self-learning playbook (procedural memory)
After every nontrivial task the agent reflects on its own trace and distills up to three lessons in ACE format: `[id] helpful=N harmful=M :: rule with Trigger + Test`. Merges are deterministic scripts, no LLM in the write path — so knowledge accumulates instead of collapsing. It learns from failures as much as successes; failures become preventative guardrails.

### 3. Loop engineering built in
Turn-based, goal-based, time-based, proactive: Perfectify implements Anthropic-style loop taxonomy with one rule no other skill has — **every loop cycle must carry a learning hook**. A loop that repeats work without improving is waste. Escalation between loop types requires measured repetition, not vibes.

### Governance: why this library stays clean
Self-evolving skills have a documented failure mode: LLM-authored rules average +0.0pp while human-curated ones deliver +16pp. Perfectify ships the verified fix as code — `govern_playbook.py` retires harmful rules (harmful ≥ helpful after ≥5 trials), evicts beyond the active cap, fuzzy-deduplicates near-identical lessons, and appends every decision to an audit log. A meta-rule learned during development even rejects benchmark-specific bullets at merge time.

---

## Proof, not promises

| Claim | Evidence |
| --- | --- |
| Stops unauthorized irreversible actions | Text-only prose gates stopped **0/6** runs across versions; Invariant 12 placement stopped **3/3** under stress prompts, independently verified (data byte-identical) |
| Learns across tasks | First live loop: agent stopped a deletion AND wrote 2 new playbook rules with correct counters in the same run |
| Improves its own tooling | First goal-based loop exposed two real bugs in the merge script → fixed, regression-tested, committed |
| Solves hard tasks | Flaky-suite recovery: root cause quantified (p≈0.31/call), fix proven over 160 runs, suite faster than before |
| Doesn't overtrigger | Routine questions answered directly at baseline cost across all versions; zero orchestration theater on controls |
| Fits the budget | Root SKILL.md ≤ 10 KB (hard limit, audited); references load lazily only when triggered |

Structural audits pass, runtime self-tests pass, 25 activation/control/boundary cases validate. Behavioral claims above come from recorded matched runs; per-cell sample sizes are small and stated honestly — we publish our eval harness (`evals/`) so you can reproduce every number.

## Install

```bash
git clone https://github.com/dankofly/perfectify.git
cd perfectify
```

Copy `skill/dagx-agi-kernel/` into your harness's native skills directory. Verify installation by asking your agent something risky ("delete all inactive users in prod") — if it comes back with a dry-run list and one question instead of doing it, you're protected.

Validate the package:

```bash
python3 skill/dagx-agi-kernel/scripts/audit_kernel.py skill/dagx-agi-kernel
python3 skill/dagx-agi-kernel/scripts/harness_efficiency.py --self-test
```

## Use it

Explicit activation for high-stakes work:

```text
Use Perfectify for this task.
Task: migrate our payments schema behind a feature flag
Definition of done: migrations reversible, flag defaults off,
integration tests green twice consecutively
```

Or just install it — the trigger description activates selectively (repeated failures, dependency-heavy changes, improvement claims needing evidence) and stays out of the way otherwise.

## What's inside

| Path | Purpose |
| --- | --- |
| `SKILL.md` | Control kernel: invariants, router, contracts, gates, learning protocol (≤10 KB) |
| `playbook/playbook.md` | The agent's growing procedural memory (ACE-format bullets with counters) |
| `scripts/harness_efficiency.py` | Decision-state compiler, DAG validation, approval gates, trace analytics |
| `scripts/merge_deltas.py` | Deterministic playbook merge (ADD/UPDATE/REMOVE) |
| `scripts/govern_playbook.py` | Ratchet governance: retirement, cap eviction, dedup, decision log |
| `scripts/audit_kernel.py` | Structural audit (frontmatter, links, budget, placeholders) |
| `scripts/eval_kernel.py` | Matched-run scoring: activation precision/recall, success/token deltas |
| `evals/cases.jsonl` | 25 activation, control, and boundary cases |
| `references/` | 12 lazy-loaded deep-dives: self-learning, loop engineering, verification, orchestration security, and more |

## Design principles

1. **Placement beats content.** A safety rule in the core-invariant list outperforms the identical sentence buried in prose — measured, not theorized.
2. **Mechanisms over manners.** Code-level gates stop agents; paragraphs rarely do. Where a mechanism exists, behavior routes through it.
3. **Learn from both directions.** Failures produce tighter guardrails than successes produce shortcuts.
4. **Governance is not optional.** Accumulation without lifecycle management is how self-improving systems rot.
5. **Honesty about evidence.** Until matched held-out runs exist, the claim is: *Insufficient data to verify.*

## Contributing

Changes follow the kernel's own promotion protocol: name the observable gap, ship the smallest causal change, include target + protected + adversarial cases, show held-out evidence for transfer claims, and state resource impact with a rollback path. Changes that only lengthen prompts or weaken evaluation get rejected — by reviewers and by CI.

## License & provenance

MIT. Research foundations: ACE (ICLR 2026), GEPA, ReasoningBank (Google), Ratchet/Library-Drift governance, GRASP gating, Anthropic loop-engineering guidance — translated from papers into runnable, audited mechanisms.
