#!/usr/bin/env bash
# df lesson environment. df reads the machine's REAL filesystems, so there is no
# data file to fabricate — every `gdf …` is read-only and reproducible per host.
# We only ensure a clean working directory exists so that `gdf .` resolves to a
# stable, predictable filesystem (the volume this folder lives on). Idempotent.
set -euo pipefail
DEMO="$(cd "$(dirname "$0")" && pwd)/intermediate"
mkdir -p "$DEMO"
cd "$DEMO"

rm -rf workspace
mkdir -p workspace

echo "reset done (df)."
