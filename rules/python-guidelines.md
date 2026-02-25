# Python Guidelines

## 1. Virtual Environment

When executing Python commands, always check if a `.venv` directory exists in the workspace root. If it exists, activate the virtual environment before running Python commands.

### Rule

1. Check for `.venv` directory in the workspace root
2. If `.venv` exists, run: `source .venv/bin/activate && <python_command>`
3. If `.venv` does not exist, run the Python command directly

### Example

**Good (with .venv):**
```bash
source .venv/bin/activate && python script.py
```

**Good (without .venv):**
```bash
python script.py
```

This ensures that the correct Python interpreter and dependencies from the virtual environment are used.
