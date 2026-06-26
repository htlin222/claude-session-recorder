#!/usr/bin/env bash
# GNU sed lesson environment: write a tiny 7-line sample file `notes.txt` that
# every scene operates on with `gsed`. It deliberately packs:
#   line 1  repeated `red`            -> s///  and  s///g
#   line 2  green / Green / GREEN     -> s///gI (ignore case)
#   line 3  the word `cat` AND `category`  -> & , -E over-matches, then \bcat\b
#   line 4  `cat` and `dog`           -> -E 's/(cat|dog)/pet/g'
#   line 5  ISO date 2024-03-15       -> backref \3.\2.\1 , /date/p
#   line 6  ISO date 2023-11-02       -> backref , /date/p , 2,4p
#   line 7  a TODO line               -> /TODO/d
# Run via src/setup_dirs.sh right before every `vhs` render. Idempotent.
set -euo pipefail
DEMO="$(cd "$(dirname "$0")" && pwd)/intermediate"
mkdir -p "$DEMO"
cd "$DEMO"

rm -f notes.txt

cat > notes.txt <<'X'
red red apple stays red
green Green GREEN leaves
the cat naps in the category
a cat and a dog play
ship date 2024-03-15 ok
back date 2023-11-02 done
TODO clean this file
X

echo "reset done (sed): wrote $(wc -l < notes.txt | tr -d ' ')-line notes.txt"
