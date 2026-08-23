# Behavioral Evaluation Protocol

Load this reference before claiming that the kernel improves activation, task success, efficiency, robustness, or transfer.

## What the Harness Proves

The included script validates case and result formats and aggregates recorded observations. It does not run a language model, judge semantic correctness, or independently prove that a result record is true. Those claims require actual matched runs and auditable graders.

Without completed baseline and candidate runs: `Insufficient data to verify`.

## Corpus

`evals/cases.jsonl` contains 25 cases:

- 10 positive activation cases;
- 10 negative controls that must remain direct;
- 5 boundary cases where keywords alone are insufficient.

Each case defines an expected activation decision, task-level success criteria, and protected behavior. Keep the case IDs and scoring rule fixed during one comparison. New cases receive a new corpus version. Do not alter a case after seeing candidate output.

## Matched Run Design

Run every case under two conditions:

1. `baseline`: identical model and harness settings without the skill;
2. `candidate`: identical settings with the tested skill version available under its real invocation policy.

Keep model version, system instructions, tools, permissions, temperature or sampling settings, attempt limit, context sources, time limit, and grader constant. Randomize or counterbalance run order when order effects are plausible. Record every attempt and selection rule. A best-of-n candidate cannot be compared with a single-shot baseline.

Prevent contamination:

- do not expose expected activation labels or success criteria to the tested agent unless they are part of the real user request;
- do not use held-out cases while editing the skill;
- blind qualitative graders to condition and intended outcome where possible;
- keep deterministic graders versioned and unchanged between conditions;
- archive raw outputs, tool traces, and grader evidence.

## Result Format

Create one JSON Lines file per condition. Each line uses:

```json
{
  "id": "activate-01",
  "activated": true,
  "success": true,
  "input_tokens": 1200,
  "output_tokens": 450,
  "tool_calls": 3,
  "wall_time_ms": 8400,
  "protected_failures": 0,
  "grader": "test-suite-v2",
  "artifact": "sha256:...",
  "notes": ""
}
```

`activated` and `success` may be `null` only when not observable or not adjudicated. Token, call, time, and cost values must be actual measurements, not estimates. Use `null` for missing measurements. The script reports missingness instead of imputing values.

## Commands

Validate the corpus:

```bash
python3 scripts/eval_kernel.py \
  --cases evals/cases.jsonl \
  --validate-cases
```

Score a candidate run:

```bash
python3 scripts/eval_kernel.py \
  --cases evals/cases.jsonl \
  --candidate results/v0.6.jsonl
```

Compare matched baseline and candidate runs:

```bash
python3 scripts/eval_kernel.py \
  --cases evals/cases.jsonl \
  --baseline results/baseline.jsonl \
  --candidate results/v0.6.jsonl \
  --strict-completeness
```

## Decision Rule

Report separately:

- activation true positives, false positives, true negatives, and false negatives;
- activation precision, recall, and specificity with denominators;
- paired task-success delta and count;
- paired input, output, and total-token deltas and count;
- baseline and candidate protected-failure counts;
- missing activation, success, resource, and grader data;
- results by positive, negative-control, and boundary group.

Do not collapse these dimensions into one score. A hard protected failure cannot be averaged away by higher success or lower token use. Promotion requires the task-specific acceptance rule recorded before the run.

## Required Claim Boundaries

- Corpus validation proves only that the files are structurally usable.
- One model and one corpus support a claim only for that evaluated system and distribution.
- Activation quality does not prove execution quality.
- Lower tokens do not prove greater efficiency if success or protected behavior declines.
- A public or development corpus is not held-out transfer evidence after it influences the skill.
- Broad capability claims require new task families, matched resource contracts, replication, and explicit attribution.
