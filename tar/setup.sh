#!/usr/bin/env bash
# tar lesson environment: build a small `project/` tree plus a loose notes.txt
# (the -r append target) and an empty restored/ dir (the -xzf -C destination).
# Idempotent: wipes and recreates everything each run, so repeated renders start
# clean. Run via src/setup_dirs.sh right before every `vhs` render.
set -euo pipefail
DEMO="$(cd "$(dirname "$0")" && pwd)/intermediate"
mkdir -p "$DEMO"
cd "$DEMO"

# wipe everything this lesson creates / its commands produce, so the run is
# deterministic from a clean slate.
rm -rf project restored
rm -f notes.txt project.tar docs.tar project.tar.gz project.tgz clean.tgz

mkdir -p project/src project/docs project/data project/logs

# source files
printf 'print("hello")\n'              > project/src/app.py
printf 'def helper(): return 42\n'     > project/src/utils.py

# docs (also packed alone via project/docs)
cat > project/docs/guide.md <<'X'
# Guide
how to use this project.
X
printf '# intro\nwelcome.\n'           > project/docs/intro.md

# several .log files — these are what --exclude='*.log' will filter out
printf '[INFO] boot ok\n'              > project/logs/build.log
printf '[WARN] retry\n'                > project/logs/error.log
printf '[INFO] GET /\n'                > project/logs/access.log

# top-level readme
cat > project/README.md <<'X'
# project
a tiny sample project for the tar lesson.
X

# a >1 MB data file, so -z / -czf compression has something meaningful to chew on
head -c 1500000 /dev/urandom          > project/data/big.bin

# the loose file appended into project.tar via `tar -r ... notes.txt`
printf 'remember to ship the release.\n' > notes.txt

# empty destination for `tar -xzf project.tgz -C restored` (bsdtar needs -C dir
# to already exist)
mkdir -p restored

echo "reset done (tar)."
