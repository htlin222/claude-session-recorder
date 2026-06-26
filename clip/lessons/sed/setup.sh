#!/usr/bin/env bash
# sed lesson environment: write a tiny 7-line sample file `notes.txt` that every
# scene operates on. It deliberately packs: repeated words (red x3 -> s///g),
# mixed case (Green/green -> /I), the words cat & dog (-> & and (cat|dog)),
# two ISO dates (-> backref \3/\2/\1, /date/p, 4,5 s///), and a TODO line (-> d).
# Run via src/setup_dirs.sh right before every `vhs` render. Idempotent.
set -euo pipefail
# per-slug workspace: dispatcher exports CLIP_DEMO; fallback derives it from this
# lesson's folder name so the script still works run standalone.
DEMO="${CLIP_DEMO:-$(cd "$(dirname "$0")/../../intermediate" && pwd)/$(basename "$(dirname "$0")")}"
mkdir -p "$DEMO"
cd "$DEMO"

rm -f notes.txt

cat > notes.txt <<'X'
the red car and the red bike are red.
Green grass and green leaves look green.
the cat sat on the mat.
a dog barked at the dog.
today's date is 2026-06-27.
another date line: 2025-12-31.
TODO: clean up this file.
X

echo "reset done (sed): wrote $(wc -l < notes.txt | tr -d ' ')-line notes.txt"
