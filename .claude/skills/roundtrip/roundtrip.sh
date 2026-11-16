#!/bin/sh
# Synthetic round trip: optar -> PNG "scan" -> unoptar -> compare.
# usage: roundtrip.sh [-s SCALE] [-k] [INPUT_FILE]
#   -s SCALE  pixel repetition for the fake scan (default 3)
#   -k        keep the work directory and print its path
# Without INPUT_FILE, 300000 random bytes are used (two A4 pages).
# Expects ./optar and ./unoptar to be built in the current directory (lega-c).
set -eu
scale=3
keep=0
while getopts s:k opt; do
	case $opt in
	s) scale=$OPTARG ;;
	k) keep=1 ;;
	*) exit 2 ;;
	esac
done
shift $((OPTIND - 1))

here=$(cd "$(dirname "$0")" && pwd)
repo=$(pwd)
[ -x "$repo/optar" ] && [ -x "$repo/unoptar" ] || {
	echo "roundtrip: build optar and unoptar first (cd lega-c && make)" >&2
	exit 2
}

work=$(mktemp -d)
[ "$keep" -eq 1 ] || trap 'rm -rf "$work"' EXIT

if [ $# -gt 0 ]; then
	cp "$1" "$work/in.bin"
else
	head -c 300000 /dev/urandom > "$work/in.bin"
fi
size=$(wc -c < "$work/in.bin")

cd "$work"
"$repo/optar" in.bin page > optar.log 2>&1
pages=$(ls page_[0-9][0-9][0-9][0-9].pgm | wc -l)
python3 "$here/pgm2png.py" --scale "$scale" page_[0-9][0-9][0-9][0-9].pgm

# The format string is the label optar prints at the bottom of each page.
format=$(sed -n 's/.*#define TEXT_HEIGHT[^0-9]*\([0-9]*\).*/\1/p' "$repo/optar.c")
"$repo/unoptar" "0-0-0-0-0-0-0-${format:-24}" page > out.bin 2> unoptar.log || {
	echo "FAIL: unoptar exited non-zero" >&2
	tail -5 unoptar.log >&2
	exit 1
}

if cmp -n "$size" in.bin out.bin; then
	echo "PASS: $size bytes, $pages page(s), scale $scale"
else
	echo "FAIL: decoded data differs from input" >&2
	tail -5 unoptar.log >&2
	exit 1
fi
[ "$keep" -eq 0 ] || echo "work directory: $work"
