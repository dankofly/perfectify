# Verification, Evaluation, and Promotion

Load this reference for `F2`, `F3`, high-stakes work, domain-specific verification, or any improvement/promotion claim.

## 1. Claim-Level Evidence

For every acceptance-critical claim track:

`claim_id | exact claim/scope | criticality | evidence | provenance | freshness | verifier | status | residual uncertainty`

Statuses:

- `VERIFIED`: direct evidence is sufficient for the exact claim and scope.
- `SUPPORTED`: credible evidence exists but is indirect, partial, or coverage-limited.
- `UNVERIFIED`: evidence is absent or inadequate.
- `REFUTED`: stronger evidence contradicts the claim.
- `NOT_TESTABLE`: no trustworthy verifier is available within authority and scope.

Rules:

1. A source must support the adjacent claim, not merely the topic.
2. User-supplied data is an authorized input, not automatically independent truth.
3. Search snippets, memory, summaries, generated text, and consensus are not primary evidence.
4. Preserve version/date and distinguish observation from interpretation.
5. State `Insufficient data to verify` when a material claim cannot be supported.
6. Do not express calibrated probability unless calibration data exists for comparable outcomes.

## 2. Verifier Selection

Choose the verifier that observes the intended property most directly:

| Verifier | Best for | Main limitation |
| --- | --- | --- |
| formal/checker | syntax, types, schemas, invariants, proofs | proves only encoded properties |
| deterministic test | repeatable functional behavior | coverage can omit the real failure |
| runtime observation | end-to-end or user-visible behavior | may be environment-specific |
| render/read-back/diff | artifacts and state mutations | detects output, not hidden semantics |
| primary record/source | factual or documentary truth | may be stale, incomplete, or disputed |
| baseline/control | relative improvement and regression | depends on representative cases |
| independent rubric/judge | qualitative properties | judge bias and correlated model error |
| human approval/expert | rights, intent, high-stakes judgment | does not replace executable evidence |

Use complementary verifiers when a single signal can pass while the intended behavior fails. Self-review is a defect-finding pass, not independent proof.

## 3. Domain Profiles

### Code and systems

1. Read governing repository instructions and inspect current state.
2. Verify the smallest affected unit first.
3. Run applicable build, type, schema, or static checks.
4. Run targeted tests; add integration/end-to-end checks when boundaries change.
5. Observe runtime/UI behavior for user-visible work.
6. Review the final diff for scope, secrets, accidental rewrites, compatibility, and untested paths.
7. State coverage limits. Passing tests do not prove behavior outside them.

### Research and factual synthesis

1. Decompose the question into material claims.
2. Retrieve primary/current sources for volatile, niche, disputed, exact, or consequential claims.
3. Map conclusions to evidence and separate event date from publication date.
4. Search for credible counterexamples and alternative explanations.
5. Resolve contradictions or label them `DISPUTED`.
6. Distinguish fact, inference, forecast, and unknown.
7. Never fabricate citations or cite a page that does not support the claim.

### Documents, media, and visual artifacts

1. Verify required content, format, dimensions, and delivery target.
2. Render/preview the actual final artifact when layout matters.
3. Inspect clipping, overflow, pagination, resolution, contrast, labels, fonts, and consistency.
4. Re-open or read back the saved artifact, not merely its source.

### External actions and records

1. Resolve exact account, recipient, object, quantity, time, and destination.
2. Confirm action authority at the point of side effect.
3. Preview/dry-run when risk warrants it.
4. Verify resulting state, receipt, or per-item status.
5. Report partial success item by item; never promote top-level success over failed items.

### Strategy and decisions

1. State objective, constraints, decision criteria, and decisive assumptions.
2. Compare credible alternatives on the same criteria.
3. Separate observed evidence from forecast.
4. Test sensitivity where an assumption can reverse the decision.
5. Identify falsifiers, dependencies, leading indicators, and review points.
6. Do not label an unevaluated narrative as optimized.

## 4. Eval Design

An eval case is:

`input + environment + allowed actions -> trace/artifacts/result -> deterministic checks + scoped rubric -> score/status`

Define before changing the system:

- target behavior and exact failure being repaired;
- hard gates that cannot regress;
- baseline/champion;
- representative, boundary, adversarial, and negative-control cases;
- held-out or meaningfully different case when transfer is claimed;
- budget and stop condition;
- promotion/rollback rule.

Separate evaluation dimensions:

- `activation`: should the skill trigger?
- `outcome`: does the deliverable pass acceptance?
- `process`: were routing, tools, permissions, and retries appropriate?
- `epistemic`: are material claims supported and unknowns honest?
- `robustness`: do boundary, adversarial, and failure cases recover safely?
- `efficiency`: tokens, latency, calls, compute, cost, coordination.
- `transfer`: does improvement survive outside the optimized case?

Do not average away hard-gate failures. Report each critical failure separately.

## 5. Goodhart and Evaluation Integrity

An evaluation is invalid for promotion when the challenger can improve its score by changing what is measured rather than improving the intended outcome.

Reject or investigate when any occurs:

- tests/graders/acceptance criteria weaken after seeing challenger output;
- failed or difficult cases are removed without domain justification;
- denominators, thresholds, or scoring rules change only for the challenger;
- held-out cases enter prompts, memory, training, or optimization context;
- the evaluator is instructed toward the desired verdict;
- traces/artifacts are selectively omitted;
- an efficiency gain hides lower quality, coverage, or increased downstream cost;
- a qualitative judge shares the same failure-inducing context/scaffold as the candidate.

Prefer deterministic gates for exact invariants and independent evaluation for qualitative judgment. When independence is impossible, disclose correlated-error risk.

## 6. Promotion Decision

Use:

`champion -> gap -> challenger -> eval -> hard gates -> compare -> promote|reject|investigate`

Promote only if:

- the targeted gap improves on observed evidence;
- all authority/safety/mandatory acceptance gates pass;
- no protected regression appears within stated coverage;
- provenance and rollback exist;
- transfer is tested before a general capability claim;
- complexity and ongoing context cost are justified by value.

No baseline/eval means no verified improvement claim. No observed regression means only "none detected within coverage", never universal no-regression.

## 7. Kernel Behavioral Suite

Kernel changes require real model runs, not wording-match tests. The executable corpus is `evals/cases.jsonl`; its scorer is `scripts/eval_kernel.py`. Read [evaluation-protocol.md](evaluation-protocol.md) for matched-run controls, result fields, commands, metrics, and claim boundaries.

The corpus covers positive activations, negative controls, and keyword or complexity boundary cases. Score activation precision and recall separately from task success. Compare baseline and candidate success, tokens, protected failures, and missing measurements on paired cases. Preserve raw outputs and grader evidence.

The corpus is a development set after it influences the skill. It can test regression on those cases but cannot support a held-out transfer claim. Create and freeze a new unseen set before evaluating generalization.

## 8. Goal-Convergence Measurement

For goal-convergence trials, record only observable task-relevant dimensions:

`trial | novelty/exposure contract | acceptance vector | hard gates | evidence status | changed state | task-specific experience | resource vector | transfer rung | residual gaps`

A challenger dominates the champion only when all hard gates pass and one holds:

- a higher-priority acceptance dimension improves without worsening any higher dimension;
- more acceptance dimensions pass with no protected regression;
- acceptance and evidence are equal while a material resource cost decreases;
- uncertainty on a decision-critical claim decreases enough to change or secure the next action.

Do not compress incomparable dimensions into invented weights. Maintain a Pareto set when candidates trade quality, risk, information, and cost. The user or an authoritative acceptance rule resolves material tradeoffs.

Convergence claims require a trace showing decreasing unresolved acceptance gaps or increasing verified coverage. Repeated activity, longer reasoning, more tools, and self-reported confidence are not progress metrics.

For optimizer changes compare at a fixed acceptance suite and resource budget:

`mode | accepted_gap_closure/trial | verified_information/cost | repeated_failure_rate | rollback_rate | protected_pass_rate | held_out_pass_rate | context/tool overhead`

Report the vector. Do not average away a hard-gate failure or claim a better optimizer from one task family.

For fluid-intelligence changes compare at fixed novelty, prior/exposure, harness, held-out, and resource contracts:

`system | first-pass success | acquisition checkpoints | actions/attempts to threshold | compute/cost to threshold | calibration | near transfer | far transfer | protected pass rate | variance`

Endpoint accuracy without the acquisition trajectory supports a skill claim only. Public or task-tuned evaluation supports a system-engineering claim only. General capability requires materially different held-out task families and protocol-complete attribution.
