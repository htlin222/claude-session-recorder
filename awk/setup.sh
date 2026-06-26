#!/usr/bin/env bash
# awk lesson environment: write a small, STABLE employee dataset that every R()
# command in lesson.py reads. Two shapes of the SAME six rows:
#   data.txt  — whitespace-separated:  name dept salary   (for the default FS)
#   data.csv  — comma-separated:       name,dept,salary   (for the -F demo)
# Salaries straddle 5000 so `$3 > 5000` and `-v min=5000` actually filter; three
# rows are in dept "Eng" so the `/Eng/` pattern matches a real subset. Output is
# fixed and non-interactive. Run via src/setup_dirs.sh right before each render.
set -euo pipefail
DEMO="$(cd "$(dirname "$0")" && pwd)/intermediate"
mkdir -p "$DEMO"
cd "$DEMO"

rm -f data.txt data.csv

# name dept salary — space-separated. 3 rows are Eng; salaries straddle 5000.
cat > data.txt <<'X'
Alice Eng 6200
Bob Sales 4800
Carol Eng 5500
Dave HR 3900
Eve Sales 7100
Frank Eng 4500
X

# same six rows, comma-separated, for the -F, demo
cat > data.csv <<'X'
Alice,Eng,6200
Bob,Sales,4800
Carol,Eng,5500
Dave,HR,3900
Eve,Sales,7100
Frank,Eng,4500
X

echo "reset done (awk)."
