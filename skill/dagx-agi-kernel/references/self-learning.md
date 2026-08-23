# Self-Learning Protocol (V0.8+)

The playbook (`playbook/playbook.md`) is the kernel's procedural memory: itemized rules in ACE format (arXiv:2510.04618) with helpful/harmful counters.

## Loop

1. **Reflect** (after each F1+ task): read your own trace. What was decisive? What almost failed? Distill at most 3 lessons. Learn from BOTH successes and failures - failures yield preventative guardrails, often more valuable than success recipes (ReasoningBank evidence).
2. **Propose**: each lesson as a delta JSON entry:
   - `{"op": "ADD", "section": "gates|verification|failure-recovery|...", "content": "<rule with Trigger and Test>"}`
   - `{"op": "UPDATE", "id": "<bullet-id>", "helpful": 1}` or `"harmful": 1` when an existing bullet helped or misled.
3. **Gate before merge** (regression-awareness):
   - no bullet without explicit trigger + test condition;
   - no bullet contradicting an existing one (update that one instead);
   - max 3 new bullets per task.
4. **Merge deterministically**: `python3 scripts/merge_deltas.py playbook/playbook.md deltas.json`. Never rewrite the playbook as a whole - monolithic rewrites cause context collapse.
5. **Retrieve lazily**: when a later task matches a section, load only that section's bullets and mark used bullets helpful/harmful after the task.
6. **Govern**: `python3 scripts/govern_playbook.py --apply` every ~15 tasks or above ~60 bullets. It retires harmful bullets (harmful >= helpful after >=5 trials), evicts lowest contributors beyond the cap, dedupes, and logs decisions to `playbook/decision-log.jsonl`.

## Hard constraints

- Never edit the playbook directly by hand; always via delta merge so counters stay truthful.
- Never add benchmark-specific answers or task-identifying shortcuts; rules must generalize behind their trigger condition.
- Held-out honesty: a rule promoted to the playbook has NOT been validated on unseen tasks until a fresh eval run confirms it; treat playbook content as UNVERIFIED until then.
