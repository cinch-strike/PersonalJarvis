# Jarvis — common dev commands.
# Run from the repo root. Targets use the phase1 virtualenv by default;
# override the interpreter with e.g. `make test PY=python3` (used by CI).

PHASE1 := jarvis/phase1
# Absolute so it survives the `cd $(PHASE1)` in each recipe. Override for CI with
# a bare name that's on PATH, e.g. `make test PY=python3`.
PY     ?= $(CURDIR)/$(PHASE1)/.venv/bin/python

.DEFAULT_GOAL := help
.PHONY: help install test check doctor run clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install:  ## Create the phase1 venv and install Mac deps
	cd $(PHASE1) && python3.11 -m venv .venv \
		&& .venv/bin/python -m pip install --upgrade pip wheel \
		&& .venv/bin/python -m pip install -r requirements-common.txt -r requirements-mac.txt

test:  ## Run the full unit-test suite (no hardware needed)
	cd $(PHASE1) && $(PY) -m unittest discover -p 'test_*.py'

check:  ## Print which backends are selected for this OS
	cd $(PHASE1) && $(PY) jarvis.py --check

doctor:  ## Full environment readiness probe (no mic/model/LLM call)
	cd $(PHASE1) && $(PY) jarvis.py --doctor

run:  ## Start Jarvis
	cd $(PHASE1) && $(PY) jarvis.py

clean:  ## Remove Python caches
	find $(PHASE1) -type d -name __pycache__ -prune -exec rm -rf {} +
	find $(PHASE1) -type f -name '*.pyc' -delete
