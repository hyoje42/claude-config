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

- File: `[filename.py](path/to/filename.py)`
- Specific line: `[filename.py:42](path/to/filename.py#L42)`
- Line range: `[filename.py:42-51](path/to/filename.py#L42-L51)`
- Directory: `[src/utils/](src/utils/)`

### Example

```markdown
See the [DroidAgent class](droidrun/agent/droid/droid_agent.py).
The run method is at [droid_agent.py:120](droidrun/agent/droid/droid_agent.py#L120).
```

**Do not use backticks or HTML tags for code references. Always use markdown links.**

## 3. Batch Related Changes Together

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
