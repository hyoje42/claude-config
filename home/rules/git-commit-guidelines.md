# Git Commit Guidelines

## 1. Commit Only with Explicit Approval

Never run `git commit` on your own initiative. When asked to commit or to generate a commit message, propose the message first and run `git commit` only after the user approves. Ambiguous phrasing like "sync to git" does not mean commit.

## 2. Commit Message Format

- Follow conventional commit format (feat, fix, refactor, docs, test, chore, etc.)
- Keep the title concise (under 50 characters) and in imperative mood ("add", not "added")
- Add a body only when the change needs explanation; mark breaking changes explicitly
- Do NOT add AI co-author trailers (e.g., `Co-Authored-By: Claude`, `Co-Authored-By: Codex`) or generator footers (e.g., `🤖 Generated with ...`)
