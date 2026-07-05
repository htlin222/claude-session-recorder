#!/bin/bash
# render.sh <tape> — runs a VHS tape, then pads its Width x Height (a 4:5-ish
# content frame) into a 9:16 canvas of the same width, letterboxed with the
# Catppuccin Mocha background color (#1e1e2e) so the pad blends into the
# theme instead of showing as stark black bars.
set -euo pipefail
cd "$(dirname "$0")"

# Isolated nvim config for any tape that shells out to `nvim` (see
# nvim-xdg/config/nvim/init.lua) — redirecting the whole XDG trio, not just
# passing -u, so nvim's runtimepath never contains the real ~/.config/nvim.
export XDG_CONFIG_HOME="$(pwd)/nvim-xdg/config"
export XDG_DATA_HOME="$(pwd)/nvim-xdg/data"
export XDG_STATE_HOME="$(pwd)/nvim-xdg/state"

tape="$1"
out=$(grep -m1 '^Output ' "$tape" | awk '{print $2}')
width=$(grep -m1 '^Set Width ' "$tape" | awk '{print $3}')
[ -n "$out" ] || { echo "no Output line in $tape" >&2; exit 1; }
[ -n "$width" ] || { echo "no Set Width line in $tape" >&2; exit 1; }

vhs "$tape"

height916=$(( width * 16 / 9 ))
base="${out%.*}"
out916="${base}-916.${out##*.}"
pad="pad=${width}:${height916}:0:(${height916}-ih)/2:color=0x1e1e2e"
FF=/opt/homebrew/bin/ffmpeg

# Optional sidecar "<tape-basename>.sfx": one macOS system sound name (under
# /System/Library/Sounds/) per line, in typing order -- e.g. a distinct ding
# per markdown heading level. No timestamps to hand-derive: gen_onsets.py
# computes each line's onset from the tape's own Sleep constants + character
# weights + the ACTUAL measured duration of this render, so it self-corrects
# for VHS's run-to-run timing drift instead of assuming a fixed typing rate
# (see gen_onsets.py's docstring). Absent file = silent output, unchanged.
sfx="${base}.sfx"
if [ -f "$sfx" ]; then
  vtot=$(/opt/homebrew/bin/ffprobe -v error -show_entries format=duration -of csv=p=0 "$out")
  sounds=(); while IFS= read -r line; do sounds+=("$line"); done < "$sfx"
  onsets=(); while IFS= read -r line; do onsets+=("$line"); done \
    < <(python3 "$(dirname "$0")/gen_onsets.py" "$tape" "$out")
  if [ "${#sounds[@]}" -ne "${#onsets[@]}" ]; then
    echo "render.sh: $sfx has ${#sounds[@]} sounds but $tape has ${#onsets[@]} typed lines" >&2
    exit 1
  fi
  inputs=(); filt=""; labs=""
  for i in "${!sounds[@]}"; do
    inputs+=(-i "/System/Library/Sounds/${sounds[$i]}")
    ms=$(awk -v t="${onsets[$i]}" 'BEGIN{printf "%d", t*1000}')
    filt+="[$((i+1)):a]adelay=${ms}|${ms}[s${i}];"
    labs+="[s${i}]"
  done
  filt+="${labs}amix=inputs=${#sounds[@]}:normalize=0:dropout_transition=0,apad=whole_dur=${vtot},atrim=end=${vtot}[a]"
  "$FF" -y -i "$out" "${inputs[@]}" -filter_complex "[0:v]${pad}[v];${filt}" \
    -map "[v]" -map "[a]" -c:v libx264 -pix_fmt yuv420p -crf 20 \
    -c:a aac -b:a 160k "$out916"
else
  "$FF" -y -i "$out" -vf "$pad" "$out916"
fi

echo "wrote $out916"
