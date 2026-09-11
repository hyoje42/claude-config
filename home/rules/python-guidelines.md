---
paths:
  - "**/*.py"
  - "**/pyproject.toml"
  - "**/requirements*.txt"
---

# Python Guidelines

When running Python commands (such as `python`, `pytest`, or `pip`), check for a `.venv` directory at the workspace root. If it exists, activate it in the same Bash call (`source <workspace-root>/.venv/bin/activate && <command>`); otherwise run the command directly.
