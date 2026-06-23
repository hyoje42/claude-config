# Tool Usage Rules

## 1. Prefer Relative Paths

For file-related tools (Read, Edit, Write, Grep, Glob, Bash, etc.), try workspace-root-relative paths first (e.g. `./src/utils/helper.py`); fall back to an absolute path only when the relative one fails.

Note: This applies to **tool call arguments** only. User-facing code reference links in responses use absolute paths in URLs (see response-format rules).
