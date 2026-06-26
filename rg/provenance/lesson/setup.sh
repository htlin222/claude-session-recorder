#!/usr/bin/env bash
# rg (ripgrep) lesson environment: a small, fixed source tree under src/ plus a
# couple of top-level docs and ONE hidden dotfile, crafted so every R() command
# prints stable, reproducible output. Extensions are chosen to dodge the repo's
# .gitignore (no *.log etc.) so rg's default ignore-filtering never eats a demo
# file. rg always scans the explicit root `.`, skips hidden + .gitignored files
# by default, and --hidden / type / glob flags each get a file to act on.
# Idempotent: wipes and recreates its own dirs. Run right before every vhs render.
set -euo pipefail
DEMO="$(cd "$(dirname "$0")" && pwd)/intermediate"
mkdir -p "$DEMO"
cd "$DEMO"

rm -rf src docs README.md notes.txt .app_secrets

mkdir -p src/utils docs

# ---- src/log.txt : crafted for -i / -w / -n / -v / -C on the word "error" ----
# Mixes lowercase whole-word "error", the plural "errors", the run-on
# "errorlog", and an UPPERCASE "ERROR" so case-sensitivity (-i), word-boundary
# (-w), inversion (-v) and context (-C) each show a distinct result.
cat > src/log.txt <<'X'
connection error occurred at startup
many errors were logged today
the errorlog file was rotated
FATAL ERROR detected here
WARNING high memory usage
INFO service is healthy
my error happened right here
stack trace follows below
all systems nominal now
X

# ---- src/main.py : TODO markers at known line numbers (for -n) ----
cat > src/main.py <<'X'
def main():
    # TODO: parse the CLI arguments
    print("starting up")
    run()


def run():
    # TODO: handle the error case
    return 0
X

# ---- src/utils/calc.py : a literal "3.14" for -F (regex dot vs fixed string) ----
cat > src/utils/calc.py <<'X'
PI = 3.14159  # TODO: use math.pi instead
AREA = lambda r: PI * r * r
X

# ---- top-level docs (.md) so -g '*.md' and -t py each filter to real files ----
cat > README.md <<'X'
# Demo project
A tiny tree for the rg lesson.
TODO: write proper documentation.
X
cat > docs/guide.md <<'X'
# Guide
TODO: add an installation section.
X

# ---- a plain note (.txt) — has TODO but is neither .py nor .md ----
cat > notes.txt <<'X'
random scratch notes
TODO: tidy this file up later
X

# ---- ONE hidden dotfile holding the only "secret", for --hidden ----
# Name dodges the common global gitignore (.env is widely ignored, so default
# rg would skip it for TWO reasons); this one is hidden ONLY, making --hidden
# the single thing that lets it through — identical on Linux and macOS.
cat > .app_secrets <<'X'
secret_token = please-rotate-me
debug = false
X

echo "reset done (rg)."
