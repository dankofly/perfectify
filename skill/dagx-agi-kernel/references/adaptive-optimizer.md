# Adaptive Trial Control and Optimizer Boundary

Load this reference only for true-gradient work, an explicit request to adapt neural optimizers, or a behavioral A/B test of optimizer-inspired routing. Do not load it for ordinary agent retries.

## Default Rule for Agent Work

General agent tasks usually have discrete strategies, ordered acceptance criteria, textual feedback, delayed effects, and hard gates. They do not expose a differentiable objective or verified gradients.

The default agentic control is therefore:

1. preserve the current verified champion;
2. change one attributable strategy coordinate when practical;
3. run the smallest comparable trial;
4. record observed improvement, regression, no change, or unknown attribution;
5. reuse a direction only after repeated support;
6. reduce change size or isolate a coordinate when outcomes oscillate;
7. change strategy class when progress plateaus;
8. retain severe failures as explicit guards;
9. promote only through the normal acceptance and regression gates.

This is evidence-directed search. It is not Adam, RMSprop, Nadam, SGD, or gradient descent.

## Mechanism Boundary

| Evidence available | Valid mechanism |
| --- | --- |
| Scalar differentiable objective and actual gradients for authorized numeric parameters | Use a tested numerical implementation of the selected optimizer |
| Repeated comparable trials with attributed numeric deltas | Use the deltas to order the next experiment; optional moment statistics may bias exploration |
| Repeated comparable trials with ordinal outcomes only | Track positive, negative, stable, volatile, and unknown directions without gradient equations |
| Incomparable trials or unattributed multi-change trials | Preserve a Pareto set and do not update per-coordinate direction |

Never call self-confidence, chain-of-thought, textual criticism, evaluator persuasion, or an unverified score a gradient. Never invent a scalar by averaging hard gates or incomparable resource dimensions.

## Trial Coordinates

Change only controllable strategy features, for example:

- representation;
- decomposition;
- retrieval source or query;
- tool choice;
- search breadth;
- verification depth;
- context selection;
- experiment size;
- reusable procedure complexity.

Keep the authorized goal, scope, permissions, acceptance order, protected behavior, evidence, and champion outside the modifiable coordinates.

For each comparable trial record:

`coordinate | prior value | tested value | prediction | observed acceptance delta | protected result | resource delta | attribution | regime | next falsifier`

Use `positive`, `negative`, `no material change`, or `unknown` when calibrated numeric deltas do not exist. If several coordinates changed, use ablation or retain unknown attribution.

## Useful Principles Without Optimizer Theater

Neural optimizers provide research analogies only when they change an observable trial decision:

| Principle | Agentic use | Required evidence |
| --- | --- | --- |
| Momentum | Prioritize a strategy direction that repeatedly improved comparable cases | More than one attributed result in the current regime |
| Volatility scaling | Make smaller or more isolated changes on coordinates with oscillating outcomes | Comparable observations showing instability |
| Decoupled complexity control | Remove stale, duplicated, or unsupported prompt, context, memory, or process state separately from outcome optimization | Acceptance and protected behavior remain constant while cost falls |
| Lookahead | Preview, simulate, dry-run, or test a candidate on a cheap representative subset before a real side effect | Preview is faithful enough to predict the relevant gate |
| Long-term failure memory | Prevent a rare severe failure from disappearing from a short recent window | Verified severe failure with a defined scope and retirement condition |

Do not label these routes `ADAM`, `RMS`, or `NADAM` during normal execution. The label adds no value unless the implementation actually maintains the corresponding state and an evaluation compares it with a simpler controller.

Contradictory current evidence overrides momentum. Reset derived direction or volatility state when the goal, acceptance order, verifier, data distribution, tool behavior, environment, or causal representation changes. Preserve raw observations and failure records.

## True Gradient Mode

Use optimizer equations only when a task exposes a parameter vector, scalar differentiable objective, and actual gradient. Use the framework's tested optimizer rather than reimplementing it in prose.

The standard mechanisms are:

- SGD with momentum accumulates a first-moment direction across gradients.
- RMSprop scales each coordinate using a moving average of squared gradients.
- Adam combines bias-corrected first and second gradient moments.
- AdamW applies weight decay separately from the adaptive gradient update.
- Nadam combines Adam-style moments with Nesterov-style lookahead; formulations vary by library.

Do not copy neural-network defaults for learning rate, moment decay, epsilon, or weight decay into an agent workflow. Such values require measurements from the actual differentiable training problem.

## Required A/B Evaluation

Any claim that optimizer-inspired routing improves an agent must compare at least:

1. the simpler controller from the default rule;
2. the proposed router;
3. identical model, harness, prompts, tools, permissions, case set, attempt policy, and resource limits;
4. representative, boundary, negative-control, and held-out cases;
5. all attempts, including failures and best-of-n selection;
6. the same fixed verifier and protected gates.

Report separately:

- accepted gap closure per trial;
- task success and protected failures;
- repeated-failure rate;
- rollback rate;
- held-out success;
- input and output tokens;
- tool calls, time, compute, and cost;
- context and controller overhead.

Do not average away protected failures. A router that saves trials but lowers success or adds unmeasured context cost is not verified as better.

Use `scripts/eval_kernel.py` and `evals/cases.jsonl` for the repository-level activation and outcome comparison. Add optimizer-specific cases only in a versioned held-out set before inspecting candidate output.

Without matched behavioral results: `Insufficient data to verify`.

## Research Basis

- [Adam](https://arxiv.org/abs/1412.6980): adaptive first and second gradient moments with initialization-bias correction.
- [Decoupled Weight Decay Regularization](https://arxiv.org/abs/1711.05101): AdamW separates weight decay from the adaptive loss-gradient update.
- [Momentum in Deep Learning](https://proceedings.mlr.press/v28/sutskever13.html): initialization and momentum scheduling materially affect gradient optimization.
- [RMSprop lecture source](https://www.cs.toronto.edu/~tijmen/csc321/slides/lecture_slides_lec6.pdf): moving squared-gradient averages for coordinate scaling.
- [On the Convergence of Adam and Beyond](https://research.google/pubs/on-the-convergence-of-adam-and-beyond/): finite exponential windows can cause non-convergence and motivate long-term memory variants.
- [Marginal Value of Adaptive Gradient Methods](https://proceedings.neurips.cc/paper/2017/hash/81b3833e2504647f9d794f7d7b9bf341-Abstract.html): adaptive methods can generalize worse than SGD in evaluated settings despite lower training loss.
- [ProTeGi](https://aclanthology.org/2023.emnlp-main.494/), [TextGrad](https://arxiv.org/abs/2406.07496), and [OPRO](https://arxiv.org/abs/2309.03409): evaluated textual feedback can guide discrete prompt or system search without becoming a true task gradient.
- [GEPA](https://arxiv.org/abs/2507.19457): reflective mutation and Pareto selection are an agent-native alternative to unsupported scalar-gradient claims.

These sources support the listed mechanisms in their evaluated settings. They do not establish a universal agent optimizer or prove that this kernel improves real-world success.
