# Claude Code Config Repo — Work Guide

A standalone repo; it may also be embedded as a submodule of a meta-repo. For the overview (structure, scripts, machine-specific mechanism, etc.), see [README.md](./README.md). This document holds only the rules an agent must follow when editing/managing this repo.

Path map: only `home/` syncs to `~/.claude/` · `home/settings.json` is the shared baseline · `local/` is the machine override (merge input, git-ignored).

## Work rules

- **Sync gate**: applying to `~/.claude/` (whether via `claude-sync-to-home` or a manual copy) happens **only when the user explicitly says so**. Normally just check the diff with `claude-diff-with-home` and share it.
- **Sync-area boundary**: do not move files outside `home/` into the sync target, or vice versa.
- **Sync-script validation**: `claude-diff-with-home` is a thin wrapper for `claude-sync-to-home --dry-run`; all plan/compare logic lives in `claude-sync-to-home`, and settings deep-merge lives in `claude-merge-settings`. After changing sync or merge behavior (managed dirs, excludes, merge semantics, local overrides), run `for script in claude-sync-to-home claude-merge-settings tests/*.sh; do bash -n "$script"; done`, `./tests/settings-merge.sh`, and `./tests/sync-home.sh` (the sync test uses a temporary HOME; never touches `~/.claude`).
- **settings.json is merged**: deep-merge `home/settings.json` (baseline) + `local/settings.override.json` (machine values) and write the result to `~/.claude/settings.json`. Do not put machine-specific values in the baseline.
- **Machine-specific values**: commit only the `*.example` in `local/`. The real `settings.override.json` (broad permissions and other machine-specific values) is git-ignored — do not commit it. Keep it **strict JSON** (no comments — jq can't read JSONC, and `//` would clash with the `//` inside `http://` values).
- **`home/CLAUDE.md` is intentionally empty** — do not fill it (global instructions are managed in `home/rules/`).
- **Scope context-specific rules with `paths:`**: a rule in `home/rules/` that only applies in a narrow context (Python work, AGENTS.md/CLAUDE.md authoring, etc.) should carry `paths:` frontmatter so it loads only when a matching file is touched; keep truly global rules unscoped. `paths:` is the only supported field for rules, and `@import` loads eagerly (not lazily) — neither defers global rules. See [README.md](./README.md).
- **Push to every remote**: this repo is mirrored to multiple remotes (conventionally `origin`/`upstream`); when pushing, push to all of them so the mirrors don't diverge, unless the user says to push only some.
- **Do not port mechanisms blindly**: Claude uses JSON settings merge; Codex uses TOML config merge plus separate runtime wrapper handling. Convert semantics intentionally when moving rules between tools.
- **Authoring skills**: build new skills using the official examples in `reference-skills/` (a reference-only submodule — do not edit it directly).
- **Explicit-invocation-only skills**: set `disable-model-invocation: true` in `SKILL.md` frontmatter. Do not rely on wording in `description` to prevent automatic invocation.
