#!/bin/bash
# render.sh <tape> — runs a VHS tape, then pads its Width x Height (a 4:5-ish
# content frame) into a 9:16 canvas of the same width, letterboxed with the
# Catppuccin Mocha background color (#1e1e2e) so the pad blends into the
# theme instead of showing as stark black bars.
set -euo pipefail
cd "$(dirname "$0")"

tape="$1"
out=$(grep -m1 '^Output ' "$tape" | awk '{print $2}')
width=$(grep -m1 '^Set Width ' "$tape" | awk '{print $3}')
[ -n "$out" ] || { echo "no Output line in $tape" >&2; exit 1; }
[ -n "$width" ] || { echo "no Set Width line in $tape" >&2; exit 1; }

vhs "$tape"

height916=$(( width * 16 / 9 ))
base="${out%.*}"
out916="${base}-916.${out##*.}"

/opt/homebrew/bin/ffmpeg -y -i "$out" \
  -vf "pad=${width}:${height916}:0:(${height916}-ih)/2:color=0x1e1e2e" \
  "$out916"

echo "wrote $out916"
