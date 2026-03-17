# Tool Usage Guidelines

## 1. Edit Tool Parameter Types

When using the Edit tool, always ensure parameters have the correct JSON data types. The most common error is passing boolean values as strings.

### Critical Rule

**In JSON, boolean values must NOT be quoted:**
- ✅ Correct: `true` or `false` (boolean)
- ❌ Wrong: `"true"` or `"false"` (string)

### Parameter Types for Edit Tool

- `file_path`: string (required)
- `old_string`: string (required)
- `new_string`: string (required)
- `replace_all`: **boolean** (optional, default: false)

### Example

**✅ Correct (boolean type):**
```json
{
  "file_path": "/path/to/file.py",
  "old_string": "old code",
  "new_string": "new code",
  "replace_all": false
}
```

**❌ Wrong (string type):**
```json
{
  "file_path": "/path/to/file.py",
  "old_string": "old code",
  "new_string": "new code",
  "replace_all": "false"
}
```

### Why This Matters

The tool schema validation expects specific types. Passing `"false"` (string) instead of `false` (boolean) causes errors like:
```
The parameter `replace_all` type is expected as `boolean` but provided as `string`
```

**Always use proper JSON boolean values, not quoted strings.**
