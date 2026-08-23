# Harness Efficiency Runtime

Use this reference for multi-call, tool-heavy, long-horizon, or resumable work. It converts the kernel's behavioral rules into provider-neutral runtime contracts. It does not claim that a particular model, router, cache, or harness supports these mechanisms until an adapter and trace demonstrate that support.

## 1. Objective

Optimize the verified outcome under explicit resource and authority constraints:

1. Preserve acceptance gates and already verified behavior.
2. Minimize irrelevant context, redundant model calls, repeated tool discovery, and speculative writes.
3. Spend stronger-model inference and expensive verification only where cheaper evidence is insufficient.
4. Make every material transition resumable, auditable, and safe to retry.

Do not collapse these dimensions into one decorative score. Report success, protected failures, cost, tokens, latency, retries, and cache use separately.

## 2. Compile decisions, not transcripts

Store execution state in `schemas/harness-state.schema.json`. Before each node, compile only the information needed for that decision:

- goal and unresolved acceptance gates;
- protected behaviors and authority limits;
- the active node, its dependencies, budget, tools, and verifier;
- referenced knowns, unknowns, and evidence;
- dependency result references and current champion;
- stable context references and remaining budget.

Do not replay the full conversation by default. A transcript is evidence only when a node explicitly references it. Long contexts can reduce retrieval accuracy even when the relevant fact is present, so selection quality matters as much as context capacity [Lost in the Middle](https://arxiv.org/abs/2307.03172). When compression is necessary, preserve constraints, identifiers, negation, evidence links, and unresolved uncertainty; never compress them into unsupported conclusions. LLMLingua-2 is evidence that task-aware prompt compression can reduce input length, but it is not permission to discard gates or authority boundaries [LLMLingua-2](https://arxiv.org/abs/2403.12968).

## 3. Discover tools progressively

Keep a compact tool index in state. Load a full schema only for tools selected by the active node. Prefer this order:

1. reuse a known tool reference;
2. search compact names and summaries;
3. load the schema of the smallest candidate set;
4. invoke only after validating arguments and authority.

This follows MCP guidance to discover tools progressively instead of injecting every schema into every prompt [MCP client best practices](https://modelcontextprotocol.io/docs/2026-07-28/develop/clients/client-best-practices). A host-native discovery mechanism wins. Do not build a second registry beside it.

## 4. Preserve a cacheable prefix

Separate each request into:

- **stable prefix:** kernel version, policy references, tool schema references, and immutable project references;
- **task delta:** active node, unresolved gates, selected evidence, tool results, and remaining budget.

Canonicalize the stable prefix and hash it. Keep stable content byte-identical and in the same order across calls. Append volatile data after it. The runtime script emits `stable_prefix_key` and `task_delta_digest`; they identify equivalent inputs but do not prove a provider cache hit. SGLang's RadixAttention demonstrates why reusable prefixes can improve serving efficiency, while actual gains remain provider- and workload-dependent [SGLang](https://arxiv.org/abs/2312.07104).

## 5. Validate the execution graph

Represent work as dependency nodes, not a prose checklist. Before execution:

- reject missing dependencies, cycles, invalid references, and duplicate identifiers;
- compute topological waves;
- allow parallel execution only for dependency-independent nodes with disjoint write sets;
- serialize overlapping writes unless a dependency already orders them;
- keep each node's objective, expected evidence, tools, budget, and verifier explicit.

Parallel planning and execution can reduce latency when dependencies are modeled correctly [LLMCompiler](https://arxiv.org/abs/2312.04511). Separating reasoning plans from observations can also reduce repeated inference [ReWOO](https://arxiv.org/abs/2305.18323). Neither result justifies parallel writes to the same target.

## 6. Route per node, not per task

Each node declares a model class and escalation conditions. Use the least expensive class that has demonstrated adequate performance for that node type. Escalate when a recorded condition occurs, such as failed decisive verification, unresolved ambiguity, or a plateau after a strategy change.

Do not invent routing thresholds. Learn thresholds only from paired traces on the harness's own workload. RouteLLM shows that preference-trained routing can trade cost against response quality, but its results do not transfer automatically to a new provider or task distribution [RouteLLM](https://arxiv.org/abs/2406.18665).

For deterministic parsing, hashing, graph checks, schema validation, and artifact comparison, set `model_class` to `none` and use code.

## 7. Gate side effects

Treat read, reversible write, external action, and irreversible action differently:

| Side effect | Required contract |
|---|---|
| `read` | declared tools and expected evidence |
| `reversible_write` | nonempty write set, idempotency key, recovery reference, decisive verifier |
| `external` | all write requirements plus approval gate and readback |
| `irreversible` | all external requirements plus explicit recovery or compensation reference |

An execution receipt is not completion. After every material write, verify the resulting state. Preserve an idempotency key across retries. On ambiguous failure, read back before retrying. Never infer failure from a timeout alone and repeat an external action blindly.

Every write-set target must equal an authorized write scope, descend from it by `:`, `/`, or `#`, or match an explicit scope ending in `*`. The context compiler will not release an external or irreversible node until its approval gate is `passed`, and it will not release a node whose dependencies are incomplete.

## 8. Verify on the cheapest decisive rung

Use the first rung that can decide the gate:

1. schema, parser, type, or static check;
2. deterministic unit or invariant test;
3. artifact diff or state readback;
4. integration or end-to-end test;
5. independent model review;
6. human approval for authority, preference, or irreversibility.

Interface design can materially affect agent performance; therefore validate the harness interface itself, not only model answers [SWE-agent](https://arxiv.org/abs/2405.15793).

## 9. Checkpoint and resume

Checkpoint after a node changes durable state, consumes a scarce resource, or produces evidence needed by later nodes. Store:

- completed node IDs and their result references;
- state digest and champion reference;
- next safe node;
- idempotency keys for attempted side effects;
- unresolved gates and remaining budget.

On resume, validate the digest, read back material external state, and continue from `next_safe_node`. Do not rerun completed side effects merely because the transcript is absent.

## 10. Trace what can change a decision

Emit one JSON object per attempt conforming to `schemas/trace-event.schema.json`. At minimum record task, node, attempt, model class, input and cached-input tokens when known, output tokens, tool calls, tool/model/wall latency, retries, verifier result, protected failures, rollback, success, terminal state, and stop reason. `retry_count` records retries caused since the preceding event, not a cumulative attempt number. Cache ratio uses only events where both input fields are known.

Use OpenTelemetry-compatible trace and metric identifiers when the host supports them; the GenAI semantic conventions are evolving, so pin the convention version in the adapter [OpenTelemetry GenAI observability](https://opentelemetry.io/blog/2026/genai-observability/).

Report missing telemetry explicitly. `null` means unmeasured, not zero. Compare variants on identical tasks with paired seeds or repeated runs where stochasticity matters. Promotion requires a primary-metric gain, no protected regression, and an acceptable resource delta.

## 11. Runtime commands

```bash
python3 scripts/harness_efficiency.py --self-test
python3 scripts/harness_efficiency.py validate-state --state state.json
python3 scripts/harness_efficiency.py compile-context --state state.json --node node-id
python3 scripts/harness_efficiency.py analyze-traces --traces traces.jsonl
```

The compiler and analyzer are deterministic reference implementations. Harness adapters may replace them only if they preserve the same observable invariants.
