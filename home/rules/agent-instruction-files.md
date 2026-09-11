# Agent Instruction File Authoring

Defaults for creating or extending AGENTS.md / CLAUDE.md; explicit user or project instructions override them.

## 1. Content and Scope

Keep AGENTS.md to development-relevant content (build/test/run commands, code conventions, architecture entry points, and the work rules an agent needs) and make it an index of rules and pointers, not a copy: point to the canonical document instead of inlining it, move a topic that outgrows a few lines into a separate doc with a one-line pointer, and skip trivial or throwaway repos.

## 2. Single Source of Truth

Use the single-source pattern (real content in AGENTS.md; CLAUDE.md is the single line `@AGENTS.md`) only when the user asks for both files or the repo already uses it. Otherwise write only the file you were asked for, and do not add or restructure instruction files the user did not ask you to change.

## 3. Language

Write these files in English by default, even when the conversation is in
another language — they are agent-facing and English is the most reliable
across tools and models. When extending an existing instruction file, match
its current language instead. An explicit user instruction overrides this.
