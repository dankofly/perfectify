# Loop Engineering + Self-Improving Loops (V1.1)

Based on Anthropic's loop-engineering guidance (claude.com/blog/getting-started-with-loops) extended with Perfectify's self-learning layer. A loop is an agent repeating cycles of work until a stop condition is met. Perfectify adds: every loop iteration must leave learnable residue in the playbook, and the loop itself improves across runs.

## The four loop types and their learning hooks

| Loop | Trigger | Stop | Learning hook |
| --- | --- | --- | --- |
| Turn-based | user prompt | agent judges done or blocked | encode verification as skills; after each turn log what verification caught |
| Goal-based | prompt + goal condition | goal met OR max turns | per-iteration deltas; failed attempts become harmful-counter evidence on the strategy bullet |
| Time-based | interval (/loop, /schedule, cron) | cancelled or queue empty | each run compares against previous playbook state; recurring diffs become bullets |
| Proactive | event/schedule, no human | per-task goal met; routine runs until off | full pipeline: triage -> act -> review -> reflect -> merge deltas autonomously |

## Building a self-improving loop

A plain loop repeats work. A self-improving loop makes each cycle cheaper, faster, or more reliable than the last:

1. **Goal contract first**: define done with deterministic, quantitative criteria (tests passed, score threshold, zero new errors). Vague goals make loops terminate early and give the Reflector nothing to learn from.
2. **Verification skill**: never hand back partially verified work; if a check fails, fix and rerun from step 1.
3. **Learn each cycle** (Perfectify addition): after every completed cycle run Post-task Learning - distill <=3 lessons, mark playbook bullets helpful/harmful, apply via `scripts/merge_deltas.py`. The next cycle starts with the updated playbook.
4. **Second-agent review**: loops that write need loops that check; a fresh-context reviewer is less biased. Feed review verdicts into the playbook as counter evidence.
5. **Govern periodically**: run `scripts/govern_playbook.py --apply` every ~15 cycles to retire harmful rules and dedup; otherwise learned noise degrades future cycles (library drift).
6. **Escalation ladder**: start turn-based; promote to goal-based when exit criteria are stable; promote to time-based/proactive only when the work recurs unchanged. Each promotion must be justified by measured repetition.

## Token discipline inside loops

- Deterministic scripts beat reasoning: prefer shipped scripts (merge/govern/audit) over re-deriving steps each cycle.
- Clear stop criteria bound cost: explicit max-turn caps ("stop after 5 tries") prevent runaway cycles.
- Match model size to stage: cheap models for triage/mechanical fixes; capable models for judgment calls and reflection quality.
- Pilot small before scaling: gauge token usage on a slice of work before running hundreds of agents.
- Review usage per loop: track tokens/cost per cycle in traces so regressions are visible.

## Anti-patterns

- A loop without a learning hook: repeating work identically N times is waste, not engineering.
- Optimizing against your own verifier only (Goodhart): keep held-out checks outside the loop's influence.
- Unbounded accumulation of lessons: ungoverned playbooks degrade retrieval and inject stale guidance.
- Proactive autonomy over irreversible actions: proactive loops still obey Invariant 12 (hard stop for approval).
