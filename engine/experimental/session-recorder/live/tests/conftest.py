import os
import sys

# make the live/ modules importable as top-level (ledger, author, splice, …)
LIVE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if LIVE not in sys.path:
    sys.path.insert(0, LIVE)
