# session-recorder (live) — dev Makefile.
# The unified driver is record.py (record-session console script).
PY ?= python
DEMO ?= /tmp/csr-demo
SCRIPT ?= script.example.json

.PHONY: test demo demo-robust install clean

## test — run the pure-logic unit tests (no vhs/ffmpeg/tmux needed)
test:
	$(PY) -m pytest tests/

## demo — record the default example (standard run_v6.sh path)
demo:
	$(PY) record.py $(DEMO) $(SCRIPT)

## demo-robust — record via the robust tmux+qmonitor path
demo-robust:
	$(PY) record.py $(DEMO) $(SCRIPT) --robust

## install — editable install with dev extras
install:
	pip install -e .[dev]

## clean — drop the demo dir and python caches
clean:
	rm -rf $(DEMO)
	rm -rf __pycache__ .pytest_cache tests/__pycache__
