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

One reader suggested pairing this with `permissions.ask` on Bash and disabling
auto-allow inside the sandbox, so the hook is not the only thing standing there.
Those keys move between Claude Code versions, so check `/config` and the current
settings documentation for the exact names rather than copying them from here.

Verify before you trust it:

```bash
python3 hooks/perfectify_guard.py --self-test
echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /srv/data"}}' \
  | python3 hooks/perfectify_guard.py
```

The first prints `self-test: 34/34 cases correct`. The second prints a
`permissionDecision: "ask"` payload. A benign command prints nothing and exits 0.

Other harnesses: Codex, Hermes and OpenCode each have their own pre-execution
approval mechanism, and Hermes in particular puts dangerous-command approval,
an authorization layer and container isolation in the runtime rather than in a
prompt (pointed out on r/hermesagent, and it is the right design). Use theirs
first; this file is the portable fallback, not a replacement. It is small enough
to port, one `inspect()` function over a command string, but the shipped wiring
is Claude Code's hook format only and nothing here has been measured elsewhere.

## What it does

Matches 28 deterministic patterns and returns `ask`. Destructive work is
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

## Limits, stated because they matter more than the feature list

- **One unwrap layer.** `bash -c '…'` and `sudo bash -c '…'` are unwrapped and
  matched. Base64, a script written to a file and then executed, or a command
  assembled at runtime reaches the shell unmatched.
- **String matching, not semantics.** It reads the command, not the filesystem.
  `python cleanup.py` is invisible to it.
- **It fails open.** Malformed input exits 0 and lets normal permissions run. A
  guard that crashes closed blocks every tool call and gets removed within a day.
- **Uninstallable.** Anything with write access to `settings.json` can turn it
  off. The self-protect rule raises the cost; it does not remove the hole.
- **The notify path is not a gate.** It reports; it does not wait for an answer.
  Approval still happens in the harness. A queue that blocks until an admin
  replies is a different, bigger thing and is not in here.
- **Unmeasured.** The 34 self-test cases are hand-written by the author. There is
  no held-out corpus and no false-positive rate from real sessions. If you run it
  and it fires on something ordinary, that is a bug worth an issue.

If you need a boundary rather than a speed bump: run the agent as a user that
cannot delete the thing you care about, in a container, against a database role
without `DROP`. Filesystem permissions do not read prompts.
