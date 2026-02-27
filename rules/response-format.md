# Response Format Rules

## 1. Explain Before and During Editing

When planning to edit code, explain:

1. **What you'll change** - Describe the specific modification
2. **Why you're changing it** - Explain the rationale or issue being fixed

Then, when using the Edit tool to modify code, explain again:

1. **What you're changing** - Describe the specific modification
2. **Why you're changing it** - Explain the rationale or issue being fixed

Provide the explanation before the Edit tool call and when requesting the Edit tool, so users understand the change before confirming yes/no.

### Example

**Good (same response as Edit tool):**
```
I'll remove the commented-out debug print statements at lines 323, 332, and 344. These are leftover debug code that should be cleaned up.
```

**Bad:**
```
Here's the refactored code:
```

## 2. Code References

When mentioning code in responses, use clickable markdown link format so users can navigate to the code.

### Format

Use **absolute paths in the link URL** but display **relative paths in the link text** for better readability:

- File: `[path/to/filename.py](/absolute/path/to/filename.py)`
- Specific line: `[path/to/filename.py:42](/absolute/path/to/filename.py#L42)`
- Line range: `[path/to/filename.py:42-51](/absolute/path/to/filename.py#L42-L51)`
- Directory: `[src/utils/](/absolute/path/to/src/utils/)`

The workspace root is the current working directory (use `pwd` to check). Always use the actual absolute path from your environment.

### Example

If your workspace root is `/home/user/project/`:

```markdown
See the [Helper class](src/utils/helper.py).
The run method is at [helper.py:120](/home/user/project/src/utils/helper.py#L120).
Check [log.20240115:30527](/home/user/project/log.20240115#L30527) for details.
```

### Anti-Patterns (Common Mistakes)

**❌ WRONG - Plain text without link (not clickable):**
```markdown
The code at helper.py:120 shows the issue.
Check log.20240115:30527 for details.
```

**❌ WRONG - Backticks without link (not clickable):**
```markdown
The code at `helper.py:120` shows the issue.
Check `log.20240115:30527` for details.
```

**❌ WRONG - Relative path in URL (won't work):**
```markdown
See [helper.py:120](src/utils/helper.py#L120).
```

**Why relative paths don't work:** Claude Code responses appear in a chat window, not as a file in the workspace. VSCode cannot determine the base directory for resolving relative paths from a chat message. Always use absolute paths.

**✅ CORRECT - Absolute path in URL, relative in text:**
```markdown
See [helper.py:120](/home/user/project/src/utils/helper.py#L120).
Check [log.20240115:30527](/home/user/project/log.20240115#L30527) for details.
```

**Do not use backticks or HTML tags for code references. Always use markdown links with absolute paths in the URL.**

## 3. Plan Mode Output Language

When in plan mode, all output (plans, explanations, code comments, documentation) must be written in the user's preference language unless explicitly instructed otherwise.

### Rule

1. Check the user's preference language setting
2. Write all plan outputs in that language
3. Technical terms, code identifiers, and file paths should remain in their original form
4. This applies to: plan files, implementation descriptions, summaries, and any documentation generated during planning

## 4. Batch Related Changes Together

When suggesting code modifications, avoid proposing overly granular changes within a single file. Group logically related changes together so users can better understand the overall change context.

For example:
- Combine import statements with their usage code in the same proposal
- Modify function definitions and their actual call sites together
- Group multiple modifications that belong to the same conceptual change

### Example

**Good (batched together):**
"I'll add a `case_sensitive` parameter to the `process_data` function and update the call site to pass `case_sensitive=True`."

**Bad (overly granular):**
"First, I'll add a `case_sensitive` parameter to the `process_data` function."
→ (Then) "Now I'll update the call site to pass `case_sensitive=True`."
