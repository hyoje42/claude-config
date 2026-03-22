# Tool Usage Rules

## 1. Prefer Relative Paths

When using file-related tools (Read, Edit, Write, Grep, Glob, Bash, etc.), always try relative paths from the workspace root first. Only fall back to absolute paths if the relative path fails or causes an error.

- Good: `Read("./src/utils/helper.py")`
- Fallback (only if above fails): `Read("/home/user/project/src/utils/helper.py")`
- Bad: Skipping relative path and going straight to absolute path

Note: This applies to **tool call arguments** only. User-facing code reference links in responses should use absolute paths in URLs (see response-format rules).
