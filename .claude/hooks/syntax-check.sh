#!/bin/sh
# PostToolUse hook for Write|Edit: report compiler warnings on the C file
# that was just edited (or on every C file when a header changed), and lint
# pgm2ps with shellcheck. Exit 2 sends the output back to Claude.
f=$(jq -r '.tool_response.filePath // .tool_input.file_path // empty')
[ -n "$f" ] && [ -f "$f" ] || exit 0
dir=${CLAUDE_PROJECT_DIR:-$(pwd)}
case $f in
"$dir"/*) ;;
*) exit 0 ;;
esac

case $f in
*/pgm2ps | *.sh)
	command -v shellcheck >/dev/null 2>&1 || exit 0
	out=$(shellcheck -S warning "$f" 2>&1) || { echo "$out" >&2; exit 2; }
	exit 0
	;;
*/golay_codes.c) exit 0 ;;
*.h) set -- "$dir"/*.c ;;
*.c) set -- "$f" ;;
*) exit 0 ;;
esac

cc=${CC:-cc}
command -v "$cc" >/dev/null 2>&1 || exit 0
inc=$(libpng-config --I_opts 2>/dev/null || pkg-config --cflags libpng 2>/dev/null)
have_png=0
# shellcheck disable=SC2086
echo '#include <png.h>' | "$cc" -E $inc - >/dev/null 2>&1 && have_png=1

status=0
for src in "$@"; do
	case $src in */golay_codes.c) continue ;; esac
	[ -f "$src" ] || continue
	# Without libpng headers the decoder cannot be checked at all.
	if [ "$have_png" -eq 0 ] && grep -q '<png\.h>' "$src"; then
		continue
	fi
	# shellcheck disable=SC2086
	out=$("$cc" -fsyntax-only -Wall -Wuninitialized $inc "$src" 2>&1)
	if [ -n "$out" ]; then
		echo "$out" >&2
		status=2
	fi
done
exit $status
