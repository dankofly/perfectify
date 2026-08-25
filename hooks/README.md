# The deterministic layer

The kernel is instructions. Instructions are read by a model, and a model can be
argued out of them. Several people said so on the launch thread, and they were
right: a skill is not a security boundary.

`perfectify_guard.py` is the part that does not negotiate. It runs as a
`PreToolUse` hook in a separate process, matches the command string, and routes
anything irreversible to a human. The model never sees its exit path and cannot
grant itself the approval.

Two layers, different jobs:

| Layer | Where it acts | What it catches | What defeats it |
| --- | --- | --- | --- |
| Kernel invariant 12 | Instruction level, before the model proposes an action | Bad plans, before a command exists | A convincing argument, a full context window, a conflicting skill |
| `perfectify_guard.py` | Tool call, after the model decided, before the shell runs | The command itself, whatever the model believes | Obfuscation (see limits) - and uninstalling the hook |

Use both. The kernel is why a good agent asks. The hook is why a bad one has to.

## Install (Claude Code)

Copy the file anywhere stable and register it in `~/.claude/settings.json` (or
the project's `.claude/settings.json`):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /absolute/path/to/hooks/perfectify_guard.py"
          }
        ]
      }
    ]
  }
}
```

Use an absolute path. Restart the session; hook config is read at startup. A
ready-to-merge file with the optional environment variables is in
[`settings.example.json`](settings.example.json).

A reader suggested pairing this with `permissions.ask` on Bash and turning off
auto-allow inside the sandbox, so the hook is not the only thing standing there.
That was worth checking rather than repeating, and it holds:

```json
{ "sandbox": { "enabled": true, "autoAllowBashIfSandboxed": false } }
```

`sandbox.autoAllowBashIfSandboxed` **defaults to true**, so with sandboxing on,
Bash commands are auto-approved and neither the ask rule nor your attention sees
them. Setting it to false is what makes the permission prompt fire again.
Verified against Claude Code 2.1.123 by reading the settings schema in the
shipped binary, not from documentation, so re-check it on a much newer version.

One related trap from the changelog, fixed in 2.1.34: commands excluded from
sandboxing (`sandbox.excludedCommands`, `dangerouslyDisableSandbox`) could
bypass the Bash ask rule while `autoAllowBashIfSandboxed` was enabled. If you
are pinned below that version, the exclusion list is a hole in this layer.

Verify before you trust it:

```bash
python3 hooks/perfectify_guard.py --self-test
echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /srv/data"}}' \
  | python3 hooks/perfectify_guard.py
```

The first prints `self-test: 41/41 cases correct`. The second prints a
`permissionDecision: "ask"` payload. A benign command prints nothing and exits 0.

Other harnesses: Codex, Hermes and OpenCode each have their own pre-execution
approval mechanism, and Hermes in particular puts dangerous-command approval,
an authorization layer and container isolation in the runtime rather than in a
prompt, which [u/Mean-Loquat-7982](https://www.reddit.com/r/hermesagent/comments/1vwbhpv/comment/p5jrg0f/)
pointed out with a link to their security docs, and it is the right design. Use theirs
first; this file is the portable fallback, not a replacement. It is small enough
to port, one `inspect()` function over a command string, but the shipped wiring
is Claude Code's hook format only and nothing here has been measured elsewhere.

## What it does

Matches 40 deterministic patterns and returns `ask`. Destructive work is
legitimate work most of the time, and a blanket deny only teaches people to
uninstall the hook; the goal is that a human sees the command, not that the
action becomes impossible. The identity gate below is the one exception, and it
is off unless you configure it.

Covered: recursive/forced deletes, `find -delete`, force push, `reset --hard`,
`git clean -fd`, SQL `DROP`/`TRUNCATE`/`DELETE`-without-`WHERE`, raw device
writes, `mkfs`, power state, `crontab -r`, `chmod 777`, `kubectl delete`,
`terraform destroy`, recursive S3 deletes, AWS `delete-*`, docker prune/volume
rm, `npm publish`, release creation, `gh pr merge`, `gh repo delete`, and
`curl … | sh`.

It also guards itself. A command that both mutates and mentions the guard, the
kernel, a skills or hooks directory, `settings.json`, `CLAUDE.md` or `AGENTS.md`
goes to the human. That case comes straight from the thread:
`rm -rf ~/.hermes/skills/perfectify`.

## Identity gate: who is allowed to make the agent run anything

Asked for on r/hermesagent, verbatim: *"I've been having a hard time making my
Hermes abide to: DO NOT EXECUTE ANY COMMANDS IF THE USER DOES NOT HAVE MY DISCORD
ID. That's a serious security risk."*

It is, and no wording of that sentence will hold, because it is a request to a
text generator to perform access control. An allowlist compared in a separate
process does hold.

```bash
export PERFECTIFY_ALLOWED_PRINCIPALS="discord:428…,telegram:77…"
```

Unset, the gate is off and nothing changes. Set, every tool call needs a
principal that is on the list, or it is denied before the shell sees it. The
principal comes from the hook payload (`principal`, `user_id`,
`session_principal`, `author_id`) or from `PERFECTIFY_PRINCIPAL`, which a gateway
sets per session. Claude Code does not supply one, so in Claude Code leave the
allowlist unset unless you set `PERFECTIFY_PRINCIPAL` yourself.

This is the one place the guard returns `deny` rather than `ask`. Denying an
unknown caller is the whole request; asking them politely would defeat it.

**Footgun, on purpose:** set the allowlist wrong and every command is denied.
The denial message names the variable and the principal it actually saw, so the
fix takes one look. `--self-test` covers seven identity cases.

## Admin channel: see the request without being at the keyboard

The same comment wanted execution requests forwarded to an admin channel.

```bash
export PERFECTIFY_AUDIT_LOG="/var/log/perfectify-decisions.jsonl"
export PERFECTIFY_NOTIFY_CMD="curl -sS -X POST -H 'Content-Type: application/json' --data-binary @- $DISCORD_WEBHOOK"
```

Every `ask` and `deny` is appended to the log as one JSON line (timestamp,
principal, tool, command, decision, reason) and piped to the notify command on
stdin. Both are opt-in and both fail silently on purpose: an unreachable webhook
must never become a blocked tool call. The notify command gets 5 seconds.

Allowed principals running harmless commands produce no output and no log line.
The log is a record of what was stopped, not a transcript of the session.

## Two tests, and why the second one exists

`--self-test` asks whether the matcher does what the pattern list says. As a
coverage claim that is circular: the cases were written from the patterns, so it
passes by construction. It passed 41 of 41 while missing almost everything.

`--threat-corpus` was written the other way round, from "what would an agent
actually run to clean up inactive users", without looking at the pattern list.

The first time it ran it scored **1 of 17**. It missed the launch scenario
itself, because `DELETE FROM` was only matched *without* a `WHERE` clause and
"delete all inactive users" always has one. It also missed bulk `UPDATE`, mongo
`deleteMany`, `prisma migrate reset`, `redis-cli FLUSHALL`, `truncate -s 0`,
`cp /dev/null`, `git checkout -- .`, `docker compose down -v`, and an inline
`python -c` that rewrites a JSON file in place, which is how an agent edits a
data store.

It is 25 of 25 now, over 17 destructive commands and 8 controls. The pattern
list went from 28 to 40. The kernel this ships with has an invariant that says
local success is not held-out transfer; the guard was breaking it, and nothing
would have surfaced that without a set written from the threat instead of from
the code.

```bash
python3 perfectify_guard.py --self-test        # the matcher behaves as specified
python3 perfectify_guard.py --threat-corpus    # it covers commands it did not inspire
```

**What it costs.** `DELETE FROM` and bulk `UPDATE` now ask on every occurrence,
including `DELETE FROM users WHERE id = 3`. That case used to sit in the allowed
list and was moved rather than exempted: a one-row delete against a real database
is still irreversible, and one prompt is the price of covering the case the repo
is named after. If you do heavy database work interactively you will notice.

**The gap that stays open.** `python cleanup.py --confirm` is in the corpus as a
control, and it is not a control, it is a known miss. A script name carries no
information about what the script does. String matching cannot reach it and no
pattern here pretends to. That is the boundary of this approach, and the answer
to it is a permission boundary or a container, not a longer regex.

If you find a command that slips through, add it to `threat_corpus.jsonl` first
and the pattern second. A pattern without the command that motivated it is how
the list drifts back into testing itself.

## Layer 2: a judge for what the patterns miss

Suggested on r/claudeskills: rather than hoping a regex list is complete,
classify the command with a small fast model. Off unless you configure it.

```bash
export PERFECTIFY_JUDGE_CMD="/path/to/judge.sh"   # command text arrives on stdin
export PERFECTIFY_JUDGE_VOTES=2                   # default
```

The judge prints `{"safe": true|false, "reason": "..."}`, or simply exits 0 for
safe and non-zero for unsafe. Both votes must come back safe.

Three properties worth knowing before switching it on:

**It only sees a narrow slice.** Layer 1 runs first and costs nothing. The judge
is invoked only for commands layer 1 cleared that still look like a write, so a
`git status` never reaches a model. A session heavy on file writes will still
hit it often, and every hit is a model call you pay for.

**It fails closed, and layer 1 does not.** A crashed judge, a timeout,
unparseable output or a single dissenting vote all resolve to "ask the human".
That is affordable here because the set reaching this point is already narrow.
The regex layer stays fail-open on purpose, so a broken judge can never block
every tool call.

**Two votes is borrowed, not tuned.** DAGx measured a single judge at ~0.77
precision and 2-of-2 consensus at ~1.0 on its own audit task. Nothing equivalent
has been measured for shell commands here. Treat the count as a structure taken
from a neighbouring result, not as a number that came out of this repo.

**Shell portability.** `PERFECTIFY_JUDGE_CMD` and `PERFECTIFY_NOTIFY_CMD` run
through the platform shell, which is cmd.exe on Windows and not bash. Single
quotes there are literal characters, so a POSIX one-liner will silently do
nothing. Point the variable at a script file rather than inlining quoting. The
self-test caught exactly this bug in its own stubs.

## Limits, stated because they matter more than the feature list

- **One unwrap layer.** `bash -c '…'` and `sudo bash -c '…'` are unwrapped and
  matched. Base64, a script written to a file and then executed, or a command
  assembled at runtime reaches the shell unmatched.
- **String matching, not semantics.** It reads the command, not the filesystem.
  `python cleanup.py` is invisible to it.
- **It fails open, on purpose, and that is not the general rule.** Malformed
  input exits 0 and lets normal permissions run, because a guard that crashes
  closed blocks every tool call and gets uninstalled within a day. The opposite
  choice is correct one layer up: the playbook admission gate in
  `merge_deltas.py` fails CLOSED, because a bad tool call is loud and recoverable
  while a bad lesson entering procedural memory is silent and permanent. Fail
  open at the execution boundary, fail closed at the memory boundary. That split
  came from reading [dankofly/dagx](https://github.com/dankofly/dagx), whose
  promotion gate is fail-closed throughout.
- **Uninstallable.** Anything with write access to `settings.json` can turn it
  off. The self-protect rule raises the cost; it does not remove the hole.
- **The notify path is not a gate.** It reports; it does not wait for an answer.
  Approval still happens in the harness. A queue that blocks until an admin
  replies is a different, bigger thing and is not in here.
- **Coverage is measured against a held-out set, not against real sessions.**
  The threat corpus is 17 destructive commands one person thought of. It is a
  much better number than the self-test alone, and it is still not a
  false-positive rate from anybody's real week of work.
- **Unmeasured elsewhere.** The 41 self-test cases are hand-written by the author. There is
  no held-out corpus and no false-positive rate from real sessions. If you run it
  and it fires on something ordinary, that is a bug worth an issue.

If you need a boundary rather than a speed bump: run the agent as a user that
cannot delete the thing you care about, in a container, against a database role
without `DROP`. Filesystem permissions do not read prompts.
