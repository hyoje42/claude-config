#!/usr/bin/env bash
# Working-tree snapshot for run-loop integrity checks.
# Read-only: never writes to the working tree, the index, or the object database.
#
#   tree_snapshot.sh take                print a snapshot of the current tree
#   tree_snapshot.sh changed <snapshot>  print every path whose state differs from a saved
#                                        snapshot, plus "!HEAD" / "!INDEX" if either moved
#
# A snapshot lists HEAD, an index fingerprint, and one content hash per file that differs
# from HEAD or is untracked. Git-ignored files are left out. Under .loop/ only the grading
# inputs (context and its draft, intent, spec, slices, gate results, change-set diff) are included.
# Paths containing newlines are not supported.
set -euo pipefail

take() {
  local top head
  top=$(git rev-parse --show-toplevel 2>/dev/null) || { echo "not a git repository: $PWD" >&2; exit 3; }
  cd "$top"
  if head=$(git rev-parse -q --verify HEAD); then
    printf 'HEAD %s\n' "$head"
    printf 'INDEX %s\n' "$(git diff --cached --raw --no-renames HEAD | git hash-object --stdin)"
    list() { git diff --name-only --no-renames -z HEAD; git ls-files -z --others --exclude-standard; }
  else
    printf 'HEAD none\n'
    printf 'INDEX %s\n' "$(git ls-files --stage | git hash-object --stdin)"
    list() { git ls-files -z --cached --others --exclude-standard; }
  fi
  list | sort -zu | while IFS= read -r -d '' f; do
    local state
    case "$f" in .loop/*) continue ;; esac
    if [ -L "$f" ]; then
      state="link:$(readlink -- "$f" | git hash-object --stdin)"
    elif [ -d "$f" ]; then
      # Submodule or nested repository: fingerprint its HEAD and its own dirty state.
      state="dir:$(git -C "$f" rev-parse -q --verify HEAD 2>/dev/null || echo none)"
      state="$state:$(git -C "$f" status --porcelain -uall 2>/dev/null | git hash-object --stdin)"
    elif [ -e "$f" ]; then
      state=$(git hash-object -- "$f")
    else
      state=deleted
    fi
    printf 'FILE %s %s\n' "$state" "$f"
  done
  # Grading inputs under .loop/: the orchestrator writes them between worker runs,
  # and no worker may rewrite them. Hashed directly, so a git-ignored .loop/ still counts.
  local g
  for g in .loop/context.md .loop/*/context-draft.md .loop/*/1-intent.md .loop/*/2-spec.md .loop/*/3-slices.md \
           .loop/*/5a-result.md .loop/*/5b-changes.diff; do
    if [ -f "$g" ]; then printf 'FILE %s %s\n' "$(git hash-object -- "$g")" "$g"; fi
  done
}

changed() {
  local base=$1
  [ -r "$base" ] || { echo "snapshot not readable: $base" >&2; exit 2; }
  base=$(realpath -- "$base")
  take | awk -v base="$base" '
    function path(line, a) { split(line, a, " "); return substr(line, length(a[1]) + length(a[2]) + 3) }
    BEGIN {
      while ((getline line < base) > 0) {
        split(line, a, " ")
        if (a[1] == "FILE") old[path(line)] = a[2]; else meta[a[1]] = a[2]
      }
    }
    $1 == "FILE" { p = path($0); seen[p] = 1; if (!(p in old) || old[p] != $2) print p; next }
    { if (meta[$1] != $2) print "!" $1 }
    END { for (p in old) if (!(p in seen)) print p }
  '
}

case "${1:-}" in
  take) take ;;
  changed) [ $# -eq 2 ] || { echo "usage: tree_snapshot.sh changed <snapshot>" >&2; exit 2; }; changed "$2" ;;
  *) echo "usage: tree_snapshot.sh take | changed <snapshot>" >&2; exit 2 ;;
esac
