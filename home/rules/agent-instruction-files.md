# Agent Instruction File Authoring

How to author a project's agent instruction files (AGENTS.md / CLAUDE.md)
when no project-specific instruction says otherwise.

## 1. Default Content and Scope

When you create or extend an AGENTS.md, default to development-relevant
content: build/test/run commands, code conventions, architecture entry
points, and the work rules an agent needs to act correctly in the repo.

Keep it concise. Do NOT duplicate detail that already lives elsewhere —
point to the canonical document (README, design docs, specific source
files) instead of inlining it. AGENTS.md is an index of rules and
pointers, not a copy of every document.

This is a default; an explicit user instruction overrides it.

## 2. Single Source of Truth: AGENTS.md + CLAUDE.md Import

To serve both Claude Code and Codex from one source, keep the real content
in AGENTS.md and make CLAUDE.md a thin import of it — a single line:

    @AGENTS.md

Codex reads AGENTS.md natively; Claude Code reads CLAUDE.md, which imports
AGENTS.md. This avoids maintaining two divergent copies.
