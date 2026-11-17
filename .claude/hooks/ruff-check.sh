#!/bin/sh
# PostToolUse hook for Write|Edit: lint the Python file that was just edited with
# the project's ruff. Exit 2 sends the output back to Claude.
f=$(jq -r '.tool_response.filePath // .tool_input.file_path // empty')
[ -n "$f" ] && [ -f "$f" ] || exit 0
dir=${CLAUDE_PROJECT_DIR:-$(pwd)}
case $f in
"$dir"/*.py) ;;
*) exit 0 ;;
esac
[ -x "$dir/.venv/bin/ruff" ] || exit 0
out=$("$dir/.venv/bin/ruff" check "$f" 2>&1) || { echo "$out" >&2; exit 2; }
exit 0
