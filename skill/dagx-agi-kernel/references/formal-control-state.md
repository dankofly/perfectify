# Optional Formal Control State

Load this reference only when the user requests a formal state machine, when implementing a harness adapter, or when an evaluator needs stable state-field names. Ordinary task execution should follow the plain-language workflow in `SKILL.md` without loading this notation.

The notation documents state. It is not executable code, authority, evidence, or a substitute for observed behavior.

## State

```text
PX = {
  goal: authorized objective,
  gates: authority, safety, acceptance, and protected-state constraints,
  acceptance: ordered observable checks,
  baseline: best verified champion,
  knowns: verified task facts,
  unknowns: decision-relevant missing facts,
  hypotheses: falsifiable candidate explanations,
  frontier: feasible next actions,
  evidence: observations and verifier results,
  failures: attempts, causes, and counterexamples,
  resources: attempts, tokens, tools, time, compute, money, and stop limits,
  transfer: withheld-case results,
  memory: scoped reusable lessons
}
```

The goal, hard gates, and acceptance priority cannot be changed by the optimization loop. Only a higher-authority instruction or resolved user clarification may change them.

## Transition

```text
observe source of truth
identify the highest-priority gap or invalidating unknown
generate feasible evidence-producing actions
select the smallest safe action
act once
observe and verify
promote the challenger or preserve the champion
record the trial
stop or continue with a materially different action
```

Each cycle must add external evidence, reduce a decision-critical unknown, test a materially different strategy, or stop. Internal rewriting and higher self-confidence are not state progress.

## Stop States

- `ACCEPT`: all acceptance-critical checks pass.
- `BLOCKED`: required authority, data, identity, tool, or human judgment is absent.
- `SATURATED`: available evidence no longer changes the decision.
- `DOMINATED`: every remaining candidate is worse than the champion.
- `MARGINAL`: likely evidence value is below cost or risk.
- `ENV_LIMIT`: the environment cannot execute or verify the needed action.

Return the champion, verification coverage, residual gaps, and the observed stop reason. Do not expose private reasoning traces.
