# PX Adaptive Optimizer Router

Load this reference for repeated comparable trials, noisy or sparse feedback, optimizer selection, textual-gradient requests, strategy momentum, prompt/process optimization, or requests to adapt Adam, AdamW, SGD with momentum, RMSprop, or Nadam.

## 1. Exact Boundary

Gradient optimizers require a parameter vector, a scalar differentiable objective, gradients, and repeated comparable updates. General agent tasks usually expose discrete actions, ordered acceptance criteria, textual criticism, delayed effects, and hard gates instead.

Use two distinct modes:

- `EXACT_GRAD`: a differentiable or externally computed gradient exists for authorized numeric parameters. Use a tested numerical library and its documented algorithm.
- `EVIDENCE_DIRECTION`: no true gradient exists. Use externally verified comparisons to generate directional evidence for discrete strategy features. The equations below are optimizer-inspired control state, not derivatives of the task.

Never call self-confidence, chain-of-thought, fluency, evaluator persuasion, or an unverified scalar a gradient. Never convert an ordered acceptance vector into one number unless its scale and aggregation rule are externally defined.

## 2. Strategy Coordinates and Feedback

Define only controllable, task-relevant coordinates:

`theta = {representation, decomposition, retrieval, tool_route, search_breadth, verification_depth, experiment_size, context_policy, reusable_procedure}`

Lock `G`, `H`, `A`, authority, permissions, protected state, and the champion outside `theta`.

For trial `t`, compare the verified result with the champion on the same acceptance suite:

`q_t = {hard_gates, ordered_acceptance, evidence_coverage, resource_vector}`

Attribute an ordinal direction only to coordinates causally tested by the trial:

`s_t[k] in {-1, 0, +1, UNKNOWN}`

- `+1`: changing coordinate `k` produced a verified improvement with protected behavior held.
- `0`: no material verified change within coverage.
- `-1`: verified regression or increased cost at equal acceptance.
- `UNKNOWN`: attribution is not supported.

When several coordinates changed together, use ablation, a controlled comparison, or keep their entries `UNKNOWN`. Unknown entries do not update moment state.

If calibrated numeric deltas exist, additionally define `d_t[k] in real_numbers or UNKNOWN`, retain their units and provenance, and require `sign(d_t[k]) = s_t[k]`. Do not mix scores from different rubrics, versions, populations, or task regimes.

## 3. Machine Protocol

```text
PX::OPTIMIZE[
  MODE := EXACT_GRAD|PARETO_ONLY|SGD_M|RMS|ADAM|ADAMW|NADAM|AMS_GUARD;
  theta := AUTHORIZED_STRATEGY_COORDINATES;
  d := VERIFIED_ATTRIBUTED_DIRECTION;
  m := DIRECTION_MOMENT;
  v := SQUARED_DIRECTION_MOMENT;
  vmax := LONG_TERM_RISK_MEMORY;
  decay := DECOUPLED_UNSUPPORTED_COMPLEXITY_DECAY;
  route := OBSERVE>ATTRIBUTE>UPDATE>BIAS_FRONTIER>LOOKAHEAD?>VERIFY>PROMOTE|PRESERVE;
  reset := GOAL_SHIFT|GATE_SHIFT|VERIFIER_SHIFT|REGIME_SHIFT|CORRUPT_STATE;
]
```

The optimizer biases which feasible challenger to test next. `PROMOTE_OR_PRESERVE` remains controlled by acceptance evidence and hard gates.

## 4. Optimizer Router

Start with `PARETO_ONLY`. Switch only when the trigger is observed.

| Mode | Use when | Agentic mechanism | Main guard |
| --- | --- | --- | --- |
| `SGD_M` | representative sampled evals produce a stable attributed direction; transfer matters more than rapid local fit | accumulate consistent direction across sampled cases | tune schedule; test held-out cases |
| `RMS` | directional feedback is sparse, nonstationary, or differs greatly in volatility across coordinates | normalize each current direction by its recent squared magnitude | reset on regime shift; retain severe failures separately |
| `ADAM` | both persistent direction and coordinate-specific volatility are measurable | combine first-moment direction with RMS normalization and early bias correction | monitor adaptive-method non-convergence and eval overfit |
| `ADAMW` | `ADAM` applies and prompt/process/memory complexity is growing | apply complexity/staleness decay independently of performance-direction updates | never decay evidence, goals, gates, or protected behavior |
| `NADAM` | an Adam-like route applies and a cheap faithful preview/simulation can test the momentum-ahead candidate | evaluate a lookahead state before committing the real trial | preview is evidence only if its environment is valid |
| `AMS_GUARD` | rare large failures or high-impact evidence must not vanish from an exponential window | retain a coordinate-wise maximum risk/volatility memory and archive the failure | do not let old evidence override a verified regime change |

No mode is universal. Use `PARETO_ONLY` when trials are incomparable, attribution is absent, feedback is purely qualitative without a reliable order, or the sample is insufficient for moment estimates.

## 5. Exact Mathematical Kernels

For true gradients `g_t`, the core updates are:

### SGD with momentum

`m_t = beta*m_(t-1) + g_t`

`theta_t = theta_(t-1) - alpha*m_t`

Momentum accelerates directions whose gradients remain consistent and dampens oscillatory directions. Initialization and schedule materially affect results.

### RMSprop

`v_t = rho*v_(t-1) + (1-rho)*(g_t elementwise_squared)`

`theta_t = theta_(t-1) - alpha*g_t/(sqrt(v_t)+epsilon)`

RMSprop adapts the step per coordinate using an exponential average of squared gradients. It does not supply a first-moment direction.

### Adam

`m_t = beta1*m_(t-1) + (1-beta1)*g_t`

`v_t = beta2*v_(t-1) + (1-beta2)*(g_t elementwise_squared)`

`mhat_t = m_t/(1-beta1^t)`

`vhat_t = v_t/(1-beta2^t)`

`theta_t = theta_(t-1) - alpha*mhat_t/(sqrt(vhat_t)+epsilon)`

Bias correction compensates for zero-initialized moment estimates. It is not evidence calibration.

### AdamW

`theta_t = theta_(t-1) - alpha*mhat_t/(sqrt(vhat_t)+epsilon) - alpha*lambda*theta_(t-1)`

The decay term is separate from the loss gradient. In agentic mode this maps only to independent removal of unsupported complexity and stale strategy commitments.

### Nadam

Nadam combines Adam's adaptive moments with a Nesterov-style current-gradient plus momentum lookahead. Use the target library's documented implementation because momentum schedules and formulations vary. In agentic mode, create and cheaply evaluate the momentum-ahead challenger before performing its real side effect.

Do not copy neural-network defaults for `alpha`, `beta`, `rho`, `epsilon`, or `lambda` into agentic control. Calibrate them on comparable eval traces or use the ordinal fallback below.

## 6. Evidence-Direction Update

When calibrated `d_t` is numeric, comparable, and attributed, optimizer-inspired state may be updated per coordinate:

```text
for k where d_t[k] != UNKNOWN:
  m_t[k] <- beta1*m_(t-1)[k] + (1-beta1)*d_t[k]
  v_t[k] <- beta2*v_(t-1)[k] + (1-beta2)*d_t[k]^2
  mhat_t[k] <- BIAS_CORRECT(m_t[k], beta1, observed_updates[k])
  vhat_t[k] <- BIAS_CORRECT(v_t[k], beta2, observed_updates[k])
  direction_score[k] <- mhat_t[k]/(sqrt(vhat_t[k])+epsilon)
```

Use `direction_score` only to bias candidate generation and ordering. A high score means that a similar coordinate change has produced consistent verified progress relative to its observed volatility. It does not prove the next change will work.

For ordinal-only `s_t`, do not run arithmetic moments. Track:

`coordinate | supported_positive | supported_negative | stable | unknown | recency | regime | falsifier`

Rank lexicographically by hard-gate compatibility, repeated positive support, absence of regression, current-regime relevance, reversibility, evidence gain, and cost.

## 7. Decoupled Complexity Decay

`ADAMW` contributes the strongest general control principle: separate optimization pressure from complexity control.

At review points, remove or retire strategy state that is unsupported, duplicated, expired, contradicted, or fails transfer. Apply this independently of the current directional update.

Eligible decay targets:

`unused prompt clauses | redundant context | stale hypotheses | superseded memory | dominated candidates | unneeded tools/steps | brittle special cases`

Never decay:

`authorized goal | hard gates | evidence/provenance | user constraints | security boundaries | rollback data | unresolved material risks | validated champion`

Promote a simplification only when acceptance and risk remain constant within stated coverage and resource cost materially decreases.

## 8. Momentum, Lookahead, and Regime Change

Momentum is a prior over promising strategy directions, not authority to continue. Contradictory current evidence overrides it.

For `NADAM` agentic lookahead:

1. construct the candidate implied by current evidence plus accumulated direction;
2. preview, simulate, dry-run, statically check, or evaluate it on a cheap representative subset;
3. use the new observation to revise the candidate;
4. execute the smallest real trial only after feasibility gates pass.

Reset incompatible moment state when the goal, acceptance order, verifier, data distribution, environment, tool behavior, or causal representation materially changes. Preserve raw evidence and failure records; reset only derived optimizer state.

## 9. Long-Term Guard

Exponential windows can forget rare but decisive evidence. Maintain:

`vmax_t[k] = max(vmax_(t-1)[k], v_t[k])`

and a non-decaying archive of severe verified failures with scope and retirement conditions. Use this as a risk brake or AMSGrad-style denominator guard when recent smooth feedback would otherwise repeat a known failure.

Retire a guard only when stronger evidence shows that its causal regime no longer applies. Never preserve stale risk state merely because it is old.

## 10. Hybrid Schedule

Use observed phases, not a fixed universal schedule:

1. `PARETO_ONLY` until acceptance, attribution, and comparability exist.
2. `ADAM/ADAMW` for rapid adaptation under sparse or noisy measured feedback.
3. `NADAM` only when lookahead is cheap and faithful.
4. `SGD_M` or unadapted representative sampling for transfer-focused refinement when local adaptive search begins to overfit.
5. `AMS_GUARD` whenever rare severe evidence must survive short-memory adaptation.
6. reset or return to `PARETO_ONLY` on regime change.

Switching requires observed evidence such as plateau, oscillation, generalization gap, complexity growth, or nonstationarity. Optimizer names alone are not triggers.

## 11. Evaluation and Promotion

Before claiming benefit, compare the router with the current champion at the same acceptance suite and resource budget. Measure:

`accepted_gap_closure/trial | verified_information/cost | protected_pass_rate | repeated_failure_rate | rollback_rate | held_out_pass_rate | context/tool overhead`

Required cases include sparse feedback, oscillating evidence, one rare severe failure, a regime shift, an unattributed multi-change trial, a deceptive proxy, a cheap lookahead failure, complexity growth, and a held-out task family.

Static equations and valid package structure do not prove a higher real-world hit rate. Without behavioral comparison: `Insufficient data to verify`.

## 12. Research Basis

- [Adam](https://arxiv.org/abs/1412.6980): adaptive estimates of first and second gradient moments with initialization-bias correction.
- [Decoupled Weight Decay Regularization](https://arxiv.org/abs/1711.05101): AdamW separates decay from the adaptive loss-gradient update.
- [Momentum in Deep Learning](https://proceedings.mlr.press/v28/sutskever13.html): initialization and momentum scheduling materially affect optimization; Nesterov momentum can improve stability.
- [RMSprop source](https://www.cs.toronto.edu/~tijmen/csc321/slides/lecture_slides_lec6.pdf): exponential averaging of squared gradients for coordinate-wise normalization.
- [Nadam](https://cs229.stanford.edu/proj2015/054_report.pdf): Nesterov-style momentum incorporated into Adam; its reported benchmark results are mixed rather than universally dominant.
- [On the Convergence of Adam and Beyond](https://research.google/pubs/on-the-convergence-of-adam-and-beyond/): finite exponential windows can cause non-convergence; long-term memory motivates AMSGrad-style guards.
- [Marginal Value of Adaptive Gradient Methods](https://proceedings.neurips.cc/paper/2017/hash/81b3833e2504647f9d794f7d7b9bf341-Abstract.html): adaptive methods can generalize worse than SGD on evaluated settings despite lower training loss.
- [ProTeGi](https://aclanthology.org/2023.emnlp-main.494/), [TextGrad](https://arxiv.org/abs/2406.07496), and [OPRO](https://arxiv.org/abs/2309.03409): textual feedback and evaluated histories can guide discrete LLM-system optimization without true gradients.
- [GEPA](https://arxiv.org/abs/2507.19457): reflective mutation and Pareto selection provide an agent-native alternative to scalar policy-gradient optimization.
