# Harness Adapters and Deployment Semantics

Load this reference before installing the skill, attempting always-on behavior, or using harness-specific tools, memory, subagents, approvals, or file conventions.

## 1. Root Authority Is a Harness Property

`SKILL.md` is a portable activation-scoped instruction package. The phrase "ROOT / GOD DIRECTIVE" describes the kernel's internal priority after activation; it does not outrank the host's system/developer/policy layer or make the skill permanently active.

Deployment modes:

- `on-demand skill`: best default; loaded explicitly or by description match for in-scope complex work.
- `project kernel`: project-level instructions require or invoke the skill for qualifying tasks.
- `always-on root`: a harness owner deliberately embeds a condensed kernel at the system/developer/root configuration layer and keeps detailed procedures in this skill.

Do not claim always-on behavior without inspecting the actual harness configuration.

## 2. Semantic Capability Binding

Detect only capabilities needed by the task:

`retrieve | execute | mutate | verify | delegate | persist | communicate | approve`

| Semantic operation | Preferred capability | Safe fallback |
| --- | --- | --- |
| retrieve truth | native read/search/browse/query | supplied context with explicit uncertainty |
| exact transform | deterministic script/tool | constrained manual transform plus checks |
| mutate state | scoped edit/API/action | produce patch/instructions; do not claim execution |
| verify | test/checker/render/read-back | explicit rubric and verification limitation |
| parallelize | batched tools or isolated workers | sequential DAG |
| persist learning | scoped native memory or versioned file | session-only state |
| gate risk | native approval/preview/transaction | stop before side effect |

Never assume names, paths, network, installed dependencies, permission mode, context limits, memory, or multi-agent availability. Inspect or use documented runtime capabilities.

## 3. Codex and ChatGPT

- Use the native Agent Skills mechanism for on-demand activation.
- Keep `name` and `description` selective because they drive discovery and implicit invocation.
- Use plan/state tools only for work that benefits from orchestration; simple work remains `F0`.
- Use available batched/parallel reads for independent evidence and serialize conflicting mutations.
- Prefer native edit primitives, tests, renders, and read-back over prose claims.
- Project or workspace instructions may require the skill for qualifying tasks; they still cannot override higher-level policy or permission gates.
- Do not assume Library, web, browser, collaboration, approval, or persistent-memory tools exist in every Codex/ChatGPT surface.

## 4. Claude Code

- Install as an Agent Skill and keep conditional detail in referenced files.
- Project instructions can route complex tasks to the skill, but the skill body loads only when invoked or selected.
- Use subagents for bounded context isolation or parallel work, not as a default quality multiplier.
- Treat hooks as configured executable controls with their own risk and lifecycle; never assume a hook exists.
- Keep durable memory concise, scoped, and freshness-aware; subagents may not share the same memory/context semantics.
- Respect Claude Code's actual tool permissions and approval prompts at the point of mutation.

## 5. Hermes

- Install through Hermes' native skill mechanism supported by the active version.
- Bind only enabled toolsets, MCP servers, terminal backends, delegates, and memory features.
- Missing optional tools cause graceful fallback, not fabricated execution.
- Delegates receive bounded contracts and isolated write ownership.
- Terminal or direct-command shortcuts remain subject to the harness' approval and security behavior.
- Messaging surfaces may deliver files differently; verify the actual artifact/receipt rather than assuming local-path visibility.

## 6. Portability Rules

1. Keep core semantics in `SKILL.md` and vendor-specific details here.
2. Use standard frontmatter; place nonstandard fields under `metadata` only when a harness supports them.
3. Do not pre-approve tools in portable metadata unless the user explicitly requests and understands the permission effect.
4. Keep relative references one level deep and verify every link.
5. Do not encode volatile model names, limits, tool inventories, or paths as universal invariants.
6. If host behavior matters and may have changed, inspect current official documentation or runtime state.
7. A fallback must reduce capability honestly; it must never simulate a missing tool/action.

## 7. Recommended Installation Shape

```text
dagx-agi-kernel/
|-- SKILL.md
|-- references/
|   |-- verification-evals.md
|   |-- memory-rsi.md
|   |-- orchestration-security.md
|   `-- harness-adapters.md
`-- scripts/
    `-- audit_kernel.py
```

Install the directory, not only the root file, when lazy references and deterministic audit are required. Verify the current native skill location for the target harness rather than assuming one universal filesystem path.
