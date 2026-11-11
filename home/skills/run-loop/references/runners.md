# Runners

## agent (default)

Launch with the Agent tool.

- Pass `subagent_type`, `model`, and `effort` only when the roster sets them. A user-written roster is the explicit instruction that permits passing `effort`.
- `model` takes only the aliases the Agent tool lists. If the roster names something else, report it instead of substituting.
- Never use `subagent_type: "fork"` for `plan-reviewer` or `reviewer-5b`.
- Launch independent slices in one message. Completion arrives as a notification; do not poll.
- An Agent-tool worker keeps its full toolset whatever the prompt says, and the tool does not report which model ran. The integrity checks in SKILL.md are the only control on this runner.
- `view=tmux` has no effect: Agent runs expose no output stream.

## claude-cli

A separate headless Claude Code process. Use it when the roster sets `runner=claude-cli`, for example to give a reviewer a clean process whose tools are actually restricted. It needs `jq`; without it, say so and use `runner=agent`.

1. Write the prompt to `.loop/<task>/prompts/<role>-<id>.md`.
2. Run the command with the Bash tool and `run_in_background: true`. The process exit re-invokes you, which is the completion signal.
3. Read the result from the log as shown under [Reading a run](#reading-a-run).

Shell variables do not survive between Bash calls, and this file is not expanded when it is read. Write real paths into each command: the task folder where `$TASK` appears below, and this skill's directory where `$SKILL_DIR` appears (the path SKILL.md resolved for `tree_snapshot.sh`, normally `~/.claude/skills/run-loop`).

Reviewer and gate checker (read-only):

```bash
claude -p --no-session-persistence --permission-prompts none --permission-mode dontAsk \
  [--model <model>] [--effort <level>] \
  --tools "Read,Grep,Glob,Bash" \
  --allowedTools "Read Grep Glob Bash(git diff *) Bash(git log *) Bash(git show *)" \
  --output-format stream-json --verbose \
  < "$TASK/prompts/reviewer-5b.md" > "$TASK/logs/reviewer-5b.jsonl" 2> "$TASK/logs/reviewer-5b.err"
```

Implementer:

```bash
claude -p --no-session-persistence --permission-prompts none --permission-mode dontAsk \
  [--model <model>] [--effort <level>] \
  --allowedTools "Read Grep Glob Edit Write <Bash(gate command) ...>" \
  --output-format stream-json --verbose \
  < "$TASK/prompts/implementer-<id>.md" > "$TASK/logs/implementer-<id>.jsonl" 2> "$TASK/logs/implementer-<id>.err"
```

- `--permission-mode dontAsk` is what makes the allowlist a limit: only `--allowedTools` entries and the allow rules in the user's settings run, and everything else is denied. Without it the process inherits the user's default mode, and under `auto` a "read-only" reviewer can write files and run any command.
- Do not use `--permission-mode acceptEdits`: it also approves shell commands that change files, such as `rm` and `mv`. Never use `bypassPermissions`.
- `--tools` removes every other tool from the reviewer, including Edit and Write, even if a settings rule would allow them.
- Add one `Bash(...)` pattern per gate command to the implementer. A pattern matches only the command as written: a worker that runs `<gate>; echo $?` or `cd <root> && <gate>` is denied, which is why the slice prompt has a `claude-cli` variant of the gate line ([prompts.md](prompts.md#slice)). The implementer cannot delete or rename files unless a pattern allows it; add a narrow one such as `Bash(rm <path>)` only when the slice's file list calls for it.
- Run from the repo root so the process loads the project's settings and instructions.
- Keep stderr separate: Claude Code may print sign-in warnings there. For unattended runs the warning suggests `claude setup-token`; tell the user rather than running it.

### Reading a run

The exit code is 0 even when actions were denied, so read the log's `result` event:

```bash
jq -r 'select(.type=="result") | .result' "$TASK/logs/<role>-<id>.jsonl"            # the worker's report
jq -c 'select(.type=="result") | {is_error, subtype, denied: [.permission_denials[] | {tool_name, tool_input}]}' "$TASK/logs/<role>-<id>.jsonl"
jq -r 'select(.type=="system" and .subtype=="init") | .model' "$TASK/logs/<role>-<id>.jsonl"   # the model that actually ran
```

- No `result` event, or `is_error: true`, is a failed run, not a 5-a attempt (SKILL.md, [4] step 4).
- A denial means the allowlist is missing something the work needs, or the worker tried something out of scope. Decide which before retrying; do not widen the allowlist to make a denial go away.
- A reviewer that was denied when it tried to re-run a gate is working as intended: gates can write files, so it judges from `5a-result.md` instead.
- Record the model in `state.md`. If it shows that `reviewer-5b` and `implementer` ran on the same model, apply the same-model rule in SKILL.md.

## view=tmux

Only when `$TMUX` is set and a `claude-cli` role sets `view=tmux`. The pane is a read-only view, never a control channel; do not drive sessions with `send-keys` or `capture-pane`.

Open the pane right after launching the run, so the log file exists:

```bash
tmux split-window -d -h -c "$PWD" -P -F '#{pane_id}' \
  "tail -n +1 -f '$TASK/logs/<role>-<id>.jsonl' | jq -r --unbuffered -f '$SKILL_DIR/scripts/pane-filter.jq'"
```

The pane shows the worker's text and tool calls as they happen. Record the printed pane ID in `state.md` and close it with `tmux kill-pane -t <pane_id>` when the run finishes.
