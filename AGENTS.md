# Claude Code Config Repo — Work Guide

A submodule of `dev-ai-tools`. For the overview (structure, scripts, machine-specific mechanism, etc.), see [README.md](./README.md). This document holds only the rules an agent must follow when editing/managing this repo.

Path map: only `home/` syncs to `~/.claude/` · `home/settings.json` is the shared baseline · `local/` is the machine override (merge input, git-ignored).

## Work rules

- **Sync gate**: applying to `~/.claude/` (whether via `claude-sync-to-home` or a manual copy) happens **only when the user explicitly says so**. Normally just check the diff with `claude-diff-with-home` and share it.
- **Sync-area boundary**: do not move files outside `home/` into the sync target, or vice versa.
- **settings.json is merged**: deep-merge `home/settings.json` (baseline) + `local/settings.override.json` (machine values) and write the result to `~/.claude/settings.json`. Do not put machine-specific values in the baseline.
- **Machine-specific values**: commit only the `*.example` in `local/`. The real `settings.override.json` (broad permissions and other machine-specific values) is git-ignored — do not commit it. Keep it **strict JSON** (no comments — jq can't read JSONC, and `//` would clash with the `//` inside `http://` values).
- **`home/CLAUDE.md` is intentionally empty** — do not fill it (global instructions are managed in `home/rules/`).
- **Commit order**: commit in the submodule first → then commit the pointer bump in the parent.
- **Do not port mechanisms**: do not move this merge approach to codex (seed-if-absent), or vice versa.
- **Authoring skills**: build new skills using the official examples in `reference-skills/` (a reference-only submodule — do not edit it directly).
