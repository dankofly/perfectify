# Fluid-Intelligence and Skill-Acquisition Protocol

Load this reference for genuinely novel tasks, few-shot rule induction, interactive unknown environments, world-model learning, cross-domain transfer, or any claim about fluid intelligence, AGI, ASI, benchmark progress, or general capability.

## 1. Construct Boundary

Operationalize fluid intelligence as:

> Efficient acquisition of task-relevant skill on problems not specifically trained or designed for, conditional on declared priors, task-specific experience, generalization difficulty, tools, resources, and assistance.

Do not define it as "solving without prior training." A model, human, or agent always brings priors. The scientific question is how much new verified skill it acquires from bounded task-specific evidence and whether that skill transfers beyond the optimized instances.

Keep four constructs separate:

- `skill`: final task performance under a stated protocol;
- `acquisition efficiency`: how the skill curve changes with task-specific experience and resources;
- `generality`: breadth of task families on which a performance threshold is met;
- `autonomy`: the interaction and oversight regime under which a capable system acts.

Capability does not imply maximum autonomy. Accumulated academic knowledge is not identical to fluid intelligence. A benchmark may measure several constructs, but every reported conclusion must name the measured construct and known confounds.

## 2. First Directive as an Executable Contract

For each potentially novel task initialize:

```text
FI/1 {
  G: authorized outcome and hard gates,
  P0: declared priors and prior task exposure,
  X: task-specific evidence seen so far,
  B: vector budget for examples, probes, actions, attempts, tokens, compute, time, money, tools, and human help,
  D: estimated generalization difficulty and novelty boundary,
  H: competing task/world hypotheses,
  W: smallest decision-sufficient model or direct policy,
  S: observed acquisition curve and acceptance evidence,
  T: held-out near- and far-transfer results,
  C: best validated champion,
  V: benchmark/protocol validity record
}
```

Lock `G`, hard gates, `P0`, held-out boundaries, and evaluation rules before comparing challengers. If they change, start a new comparison rather than splicing incompatible results.

### Novelty/prior/experience contract

Record, when material:

`task family | target population | prior/training exposure | public/tuned/private status | examples | interaction history | memory | tools | prompt/harness | human input | attempts | compute/cost | benchmark/version | held-out rule | contamination risk`

Classify novelty:

- `FAMILIAR`: known procedure and no meaningful rule acquisition; route to the cheapest verified execution.
- `COMPOSITIONAL`: known primitives must be recombined in an unseen way.
- `STRUCTURAL`: rules, ontology, action semantics, dynamics, or goal must be inferred.
- `DOMAIN_SHIFT`: the learned procedure must survive materially different inputs or task families.
- `UNKNOWN`: exposure or contamination cannot be established; restrict claims accordingly.

Novelty labels describe the evaluated system under this contract, not an intrinsic timeless property of an item.

## 3. Acquisition Measurement

Never reduce fluid intelligence to final accuracy. Record an acquisition curve:

`S(b) = verified acceptance vector after cumulative task-specific budget b`

`b` is normally a vector, not a fabricated scalar:

`b = <examples, environment_actions, attempts, tokens, compute, wall_time, money, tool_calls, human_help>`

Use predeclared checkpoints and matched budgets. Report:

- first-pass success and final success;
- area or ordered checkpoints of the learning curve when comparable;
- actions/probes to threshold;
- compute and financial cost to threshold;
- calibration and error detection;
- near transfer and far transfer;
- variance or confidence intervals across independent tasks/runs when repeated sampling exists;
- failures and censoring, not only successful trajectories.

Do not collapse incomparable costs into one number without an authoritative utility function. Use Pareto dominance. Challenger `c` fluid-dominates champion `k` only when all hard gates pass and at least one is true with none of the protected dimensions worse:

1. `S_c(b) >= S_k(b)` at matched predeclared budgets and strictly better at one relevant checkpoint;
2. `c` reaches the same acceptance threshold with a strictly smaller resource vector;
3. `c` transfers to a materially different held-out family at the same or smaller budget while preserving in-domain behavior;
4. `c` detects or corrects its own error earlier with equal final quality and no new protected failure.

Maintain a Pareto set when success, transfer, action efficiency, compute, cost, calibration, or risk trade off. Do not claim a universal winner from one task family.

## 4. Active-Abstraction Algorithm

Use this loop only while its expected information or decision value exceeds its cost:

```text
FI::ACQUIRE
  1 CONTRACT    declare goal, priors, novelty boundary, budgets, held-out rule, hard gates
  2 OBSERVE     separate settled state, transient evidence, outcome, and uncertainty
  3 HYPOTHESIZE maintain a small diverse set of falsifiable rule/goal/world hypotheses
  4 PROBE       choose the cheapest safe action that best separates decision-relevant hypotheses
  5 MODEL       build the smallest model needed for the next decision; make it executable when replay or planning value justifies cost
  6 FALSIFY     replay observed transitions, predict the next observation/outcome, test counterexamples
  7 PLAN        search or simulate only through verified model regions; attach contingencies to uncertain transitions
  8 ACT         commit the minimal authorized action; observe actual state and score every real interaction cost
  9 REPAIR      localize mismatch among perception, ontology, dynamics, goal inference, planning, execution, or verifier
 10 TRANSFER    test the acquired abstraction on withheld instances and a materially different family
 11 PROMOTE     retain only a challenger that passes hard gates and dominates or expands the Pareto frontier
 12 STOP        accept, preserve champion, or report the exact blocker when evidence value is exhausted
```

### Probe selection

Prefer probes that distinguish plausible hypotheses and are safe, reversible, and cheap. If numerical likelihoods are uncalibrated, rank probes ordinally:

`goal relevance > expected hypothesis separation > risk reduction > reversibility > action/compute cost`

Do not invent entropy, posterior probabilities, gradients, or expected values. When a probe changes real state irreversibly, compare its information value with a goal-progressing action and preserve an exit path.

### Model allocation

Use direct reasoning or a cached procedure when one-pass execution is reliable. Construct an explicit model when it can support at least one of:

- prediction before an expensive or irreversible action;
- exact replay against recorded transitions;
- discrimination between competing hypotheses;
- planning over multiple steps or hidden state;
- reuse across levels, cases, or task families;
- causal localization after a mismatch.

An executable model is a hypothesis, not truth. Admit it for planning only within its verified coverage. Invalidate queued actions after a prediction mismatch. Repair locally when possible; rebuild when the ontology or regime changed. Bypass or delete the model when its maintenance cost exceeds its decision value.

### Failure localization

Classify the earliest supported failure:

`PERCEPTION | STATE_ALIASING | ONTOLOGY | ACTION_SEMANTICS | DYNAMICS | GOAL | PLANNING | EXECUTION | VERIFIER | CONTAMINATION | RESOURCE_LIMIT`

Change the responsible layer, then replay the original counterexample and run a protected regression case. A successful action under a false model is not model validation.

## 5. Transfer Ladder

Claims are limited by the strongest completed rung:

| Rung | Evaluation | Allowed claim |
| --- | --- | --- |
| `R0` | same item or replay | local fit only |
| `R1` | withheld instance, same rule family | within-family generalization |
| `R2` | new composition or environment, same primitives | compositional transfer |
| `R3` | materially different task family with matched resource contract | cross-family transfer |
| `R4` | broad, versioned portfolio with human/resource baselines and repeated replication | evidence of broader general capability |

No rung alone proves AGI. `R4` supports only the evaluated capability vector and protocol. Generality claims require breadth and depth; autonomy claims require a separate deployment evaluation.

## 6. Benchmark Portfolio and Construct Map

Use complementary benchmarks. Do not average them into an "AGI percentage" without a validated model connecting the scores to the construct.

| Benchmark family | Primary signal | Major confound or limit |
| --- | --- | --- |
| ARC-AGI-1/2 | few-example static rule induction and compositional abstraction | static public tasks can be targeted, augmented, or contaminated; final score omits total development cost |
| ARC-AGI-3 | interactive goal/dynamics inference, planning, and human-normalized action efficiency | public-set or domain-specific harness scores measure system engineering, not held-out general intelligence |
| GPQA, HLE, FrontierMath | difficult academic knowledge and reasoning depth | knowledge, item validity, contamination, and domain coverage confound fluid-intelligence claims |
| GAIA | browsing, multimodality, reasoning, and tool coordination | tool/API access and environment drift affect comparability |
| OSWorld | real GUI interaction and end-to-end computer use | software versions, visual grounding, and infrastructure reliability affect results |
| SWE-bench | patching real repositories against tests | repository familiarity, issue ambiguity, test adequacy, and scaffold/tooling matter |
| Terminal-Bench | terminal-based execution over diverse tasks | harness, container, dependency, and test coverage determine part of the score |
| METR task horizons | reliability as human task duration increases | task mixture and external validity limit extrapolation to all work or future systems |

Static induction, academic expertise, software execution, GUI/tool use, interactive learning, and long-horizon reliability are distinct axes. A system may be strong on one and weak on another.

## 7. Benchmark Integrity Gate

Before citing or comparing a score, record:

`exact benchmark + version | subset | public/semi-private/private | model version | prompt | harness/tools/memory | task-specific preparation | attempts/best-of-n | action/token/compute/cost budget | date | scoring rule | human baseline | uncertainty | source`

Reject or restrict a conclusion when:

- benchmark items, solutions, or close synthetic analogues may have entered training or optimization;
- public examples informed a task-specific harness later evaluated on those examples;
- model-only and full-system results are conflated;
- best-of-n, selective reruns, fallback models, or failed trials are omitted;
- benchmark versions, subsets, prompts, tools, costs, or denominators differ;
- exact-match graders reward an invalid shortcut or reject valid alternatives;
- human baselines use different tools, time, incentives, or exposure;
- the evaluator changed after seeing results;
- the score is self-reported without artifacts or independent verification.

Public-set mastery can validate an engineering hypothesis. It cannot establish novel-task generalization on the same set. Retrieve current official results at evaluation time; do not treat a stored leaderboard snapshot as durable truth.

## 8. AGI and ASI Claim Gate

Maintain a capability vector instead of a binary declaration:

`C_AGI = <breadth, depth, acquisition_efficiency, near_transfer, far_transfer, metacognition, calibration, robustness, long_horizon_reliability, ecological_validity, resource_efficiency>`

Track autonomy separately:

`A_SYS = <initiative, action_scope, persistence, oversight, reversibility, containment, human_control>`

An AGI-progress claim requires versioned, held-out, contamination-audited evidence across a broad task portfolio, matched protocols, resource accounting, and human/reference baselines. A single saturated benchmark is neither necessary nor sufficient. An ASI or technological-singularity claim additionally requires a declared definition and direct evidence across the relevant breadth; extrapolation, recursive-improvement rhetoric, or one superhuman narrow skill is insufficient.

If these requirements are unmet, report the narrower supported result. If a material claim has no adequate evidence, state exactly: `Insufficient data to verify`.

## 9. Research Basis

- [On the Measure of Intelligence](https://arxiv.org/abs/1911.01547): task skill is confounded by priors and experience; intelligence is framed as skill-acquisition efficiency over scope and generalization difficulty.
- [Universal Intelligence](https://arxiv.org/abs/0712.3329): formalizes broad performance across environments and clarifies why one task is insufficient.
- [Levels of AGI](https://arxiv.org/abs/2311.02462): separates performance depth, capability breadth, and autonomy; requires cognitive and metacognitive coverage.
- [ARC-AGI-3 technical report](https://arxiv.org/abs/2603.24621): operationalizes interactive skill acquisition through exploration, goal inference, world modeling, planning, and human-normalized action efficiency; separates official from harness-driven results.
- [Tycho](https://arxiv.org/abs/2607.28287): tests persistent evidence, optional executable world models, replay verification, planning, model repair, and metareasoning over modeling cost.
- [OPINE-World](https://arxiv.org/abs/2607.01531): uses object-centric programmatic world models, counterexample-guided repair, replay verification, and uncertainty-directed exploration.
- [BetterBench](https://arxiv.org/abs/2411.12990): supplies lifecycle practices for benchmark validity, reproducibility, reporting, and maintenance.
- [Data Contamination in LLMs](https://arxiv.org/abs/2406.04244): surveys contamination definitions, detection, and mitigation that constrain benchmark interpretation.
- [GPQA](https://arxiv.org/abs/2311.12022), [Humanity's Last Exam](https://arxiv.org/abs/2501.14249), and [FrontierMath](https://arxiv.org/abs/2411.04872): measure difficult academic knowledge/reasoning rather than fluid intelligence alone.
- [GAIA](https://arxiv.org/abs/2311.12983), [OSWorld](https://arxiv.org/abs/2404.07972), [SWE-bench](https://arxiv.org/abs/2310.06770), and [Terminal-Bench 2.0](https://arxiv.org/abs/2601.11868): cover tool use, computer interaction, repository repair, and terminal execution.
- [Measuring AI Ability to Complete Long Tasks](https://arxiv.org/abs/2503.14499): measures reliability as human task duration increases and explicitly limits extrapolation beyond the evaluated task distribution.

The sources support components of this protocol, not a proof that the combined kernel is optimal or that it creates AGI. Promotion still requires direct evaluation of this implementation.
