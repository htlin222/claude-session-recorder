#!/usr/bin/env bash
# jq lesson environment: write a FIXED data.json so every `cat data.json | jq …`
# prints a stable, reproducible result. It is an array of three objects, each
# with a string field (name), a number field (age, used by select/map), an array
# field (tags), and a nested object (loc.city, used by the nesting demo). The
# engine runs this (via src/setup_dirs.sh) right before every render. Idempotent.
set -euo pipefail
DEMO="$(cd "$(dirname "$0")" && pwd)/intermediate"
mkdir -p "$DEMO"
cd "$DEMO"

rm -f data.json

cat > data.json <<'JSON'
[
  {
    "name": "Ada",
    "age": 36,
    "tags": ["dev", "lead"],
    "loc": { "city": "Taipei", "zip": "100" }
  },
  {
    "name": "Linus",
    "age": 28,
    "tags": ["kernel"],
    "loc": { "city": "Helsinki", "zip": "001" }
  },
  {
    "name": "Grace",
    "age": 45,
    "tags": ["navy", "compiler"],
    "loc": { "city": "New York", "zip": "100" }
  }
]
JSON

echo "reset done (jq)."
