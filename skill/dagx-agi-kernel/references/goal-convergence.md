# PX Goal-Convergence Engine

Load this reference for `F2/F3`, repeated failure, open-ended tasks, autonomous multi-step execution, measurable optimization, or any request to keep searching until a goal is reached.

## 1. Operating Claim

`PX` is an anytime, feedback-driven, problem-adaptive meta-optimizer. It continuously preserves the best verified result and searches for a better feasible result while evidence-producing actions remain valuable.

It is intentionally not described as universally unbeatable. No fixed optimizer dominates across every possible problem class, and many goals are uncomputable, undecidable, underspecified, inaccessible, or resource-limited. `PX` maximizes measured goal convergence under the actual task distribution, evidence, tools, authority, and budget.

## 2. Working State

Maintain only information that changes the next decision:

- authorized goal, hard gates, ordered acceptance, and protected behavior;
- novelty, prior exposure, task-specific experience, and resource contract when relevant;
- verified knowns, decision-relevant unknowns, and falsifiable hypotheses;
- the current champion and feasible challengers;
- observations, verifier results, failures, and scoped lessons;
- used resources and stop conditions.

The goal, hard gates, and acceptance priority are locked against self-modification. Change them only through a higher-authority instruction or resolved user clarification. Formal field names are available in [formal-control-state.md](formal-control-state.md) only when an implementation needs them.

## 3. Activation and Baseline

On activation, form the task contract, observe source-of-truth state, record the resource limit, and preserve the current valid result as champion. If no explicit baseline exists, use the smallest valid current solution or the pre-change result. If acceptance cannot be observed, first create a task-fit verifier or state the verification gap; never substitute self-confidence.

## 4. Convergence Loop

For each cycle:

1. identify the highest-priority unresolved gap or premise-killing unknown;
2. generate only feasible actions that can close the gap or falsify a hypothesis;
3. select the smallest safe action with the best evidence value;
4. execute once, observe actual output, and apply the fixed verifier;
5. record acceptance, protected behavior, resource use, and attribution;
6. promote the challenger or preserve the champion;
7. stop unless the next cycle adds external evidence or tests a materially different strategy.

Directional history may bias which challenger is tested next, but it cannot bypass feasibility, verification, or promotion gates. Read [adaptive-optimizer.md](adaptive-optimizer.md) only for explicit optimizer adaptation or its A/B evaluation.

## 5. Acceptance and Baseline

Represent acceptance as ordered tests, not one vague reward:

`A = [a1, a2, ...]`, where each `ai = {claim, verifier, priority, pass condition, coverage}`.

Rules:

1. Hard gates are pass/fail and never averaged away.
2. Higher-priority acceptance cannot be traded for lower-priority convenience.
3. Use direct outcome measures when possible.
4. A proxy must have a stated relationship to the real objective and a falsifier.
5. If a proxy can be gamed, add an independent signal or deterministic gate.
6. Preserve the baseline/champion unchanged until a challenger is promoted.

Improvement is verified only when a challenger passes all hard gates and dominates the champion on the ordered acceptance/evidence/resource vector. Equal quality with lower material cost is an efficiency improvement. More activity is not improvement.

For a novel-task or fluid-intelligence claim, compare acquisition curves at matched task-specific experience budgets and require a held-out rung from `fluid-intelligence.md`. A higher final score bought with more examples, attempts, hidden task preparation, or compute is not automatically more intelligent. For a familiar task, set `N=FAMILIAR` and do not manufacture an acquisition loop.

## 6. Candidate Generation

Generate only strategies capable of closing an unresolved gap. Use a diverse operator set:

- `EXPLOIT`: refine the strongest validated strategy.
- `VERIFY`: obtain evidence that can confirm, reject, or reorder decisions.
- `REPAIR`: correct the earliest causal failure.
- `REDECOMPOSE`: change task/DAG granularity or dependency order.
- `REFRAME`: change representation while preserving `G/H/A`.
- `RETRIEVE`: acquire missing authoritative/local information.
- `TOOL_SHIFT`: use a more deterministic or better-suited capability.
- `BACKTRACK`: return to the last branch point before a false premise.
- `DIVERSIFY`: explore a different strategy family, assumption, or solution architecture.
- `SIMPLIFY`: remove steps or state that add cost without evidence value.

Do not generate alternatives merely to increase count. Diversity must change the causal path, evidence source, representation, or verifier.

## 7. Feasibility and Pareto Selection

Filter any candidate that violates authority, scope, safety, legality, permissions, mandatory acceptance, protected state, or available prerequisites.

For each feasible action rank ordinally unless calibrated data exists:

`rank(a) = lex<critical_gap_closure, invalidating_information, risk_reduction, reversibility, expected_evidence_gain, -resource_cost>`

Do not invent numeric probabilities or weights. Eliminate candidates dominated on every relevant dimension. When surviving candidates trade incomparable user values, ask only if the tradeoff materially changes the outcome; otherwise choose the most reversible evidence-producing candidate.

Balance exploitation and exploration by evidence:

- exploit while the champion's neighborhood yields verified improvement;
- explore when progress stalls, the model is uncertain, or repeated failures share one strategy class;
- retain diverse high-quality stepping stones instead of keeping only the latest path.

## 8. Safe Trial and Error

Every trial record:

`trial_id | state_digest | gap | hypothesis | action | prediction | observation | verifier | delta | cost | failure_class | lesson | rollback`

Trial rules:

1. Use the smallest experiment that can falsify the hypothesis.
2. Prefer sandboxed, simulated, read-only, local, or reversible trials.
3. `R0/R1` may proceed autonomously within user scope.
4. `R2/R3` stays read-only/sandboxed until the required side-effect gate passes.
5. Observe actual environment/tool output; do not self-generate the reward and evidence from the same unsupported judgment.
6. After failure, change a premise, representation, decomposition, tool, evidence source, or strategy family.
7. Never repeat an identical failed action under the same state.
8. Roll back failed mutations and preserve the last champion.

## 9. Plateau Escape

Declare a plateau when recent cycles produce no verified acceptance gain, no decision-changing information, and repeat the same causal failure region.

Apply in order only until new evidence appears:

1. audit the verifier and objective proxy;
2. challenge stale/false premises;
3. resolve the highest-impact unknown;
4. change representation or decomposition;
5. switch tool or evidence source;
6. backtrack to the last viable branch;
7. sample a distinct strategy family from the archive;
8. reduce the problem to a falsifiable subgoal;
9. request missing authority/data/judgment if no autonomous path remains;
10. stop with the best champion and exact blocker when further search has no positive value.

Never conceal a plateau with longer prose, cosmetic variants, repeated searches, or lower acceptance thresholds.

## 10. Continuous Learning

Learning occurs at three scopes:

- `episode`: update `B/F/E` from the current trial.
- `task`: reuse validated lessons and stepping stones within the active goal.
- `cross-task`: promote only scoped procedures that pass recurrence, independent confirmation, or transfer evaluation.

Compile reusable learning into the cheapest reliable form:

`verified fact < detector/check < procedure < script/tool < specialized skill`

Use the lowest layer that preserves correctness. Deterministic enforcement is preferred when the same rule recurs.

Durable learning requires an authorized persistent memory/file/tool. Without it, learning is session-local. Read `memory-rsi.md` before persistence or self-modification.

## 11. Stop and Resume

Stop only on a recorded reason:

- `ACCEPT`: all acceptance-critical tests pass.
- `BLOCKED`: required authority, data, identity, tool, or human judgment is absent.
- `SATURATED`: available evidence/strategies no longer change the decision.
- `DOMINATED`: remaining candidates are worse than the champion.
- `MARGINAL`: expected evidence/progress is below cost or risk.
- `ENV_LIMIT`: the environment cannot execute or verify the needed action.

Return the champion, verification coverage, residual gaps, and exact stop reason. Preserve resumable state when the harness supports it.

## 12. Research Basis

The engine combines mechanisms supported in primary research:

- [ReAct](https://arxiv.org/abs/2210.03629): interleaved reasoning, acting, observation, and plan updating.
- [Reflexion](https://arxiv.org/abs/2303.11366): trial feedback converted into episodic linguistic learning.
- [Language Agent Tree Search](https://arxiv.org/abs/2310.04406): alternative trajectory search with environment feedback and reflection.
- [Voyager](https://arxiv.org/abs/2305.16291): automatic curriculum, iterative environment feedback, and reusable skill libraries.
- [Darwin Godel Machine](https://arxiv.org/abs/2505.22954): diverse candidate archives and empirical validation of self-modifications.
- [AlphaEvolve](https://arxiv.org/abs/2506.13131): evolutionary candidate generation paired with automated evaluators.
- [STOP](https://arxiv.org/abs/2310.02304): recursively improving scaffolding against an explicit utility function.
- [No Free Lunch Theorems](https://doi.org/10.1109/4235.585893): no fixed optimizer is uniformly superior across all possible problem classes.
- [ProTeGi](https://aclanthology.org/2023.emnlp-main.494/): textual critique can direct candidate edits combined with beam and bandit search.
- [TextGrad](https://arxiv.org/abs/2406.07496): textual feedback can propagate through compound AI systems as a gradient analogy.
- [Optimization by PROmpting](https://arxiv.org/abs/2309.03409): LLMs can optimize derivative-free objectives using evaluated solution histories.
- [GEPA](https://arxiv.org/abs/2507.19457): reflective mutation, trajectory feedback, and Pareto archives support sample-efficient prompt and agent optimization.
