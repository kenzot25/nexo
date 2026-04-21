VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: help setup test t integration-test it test-install test-binary rename-brand rename-brand-apply run r

help:
	@echo "Available commands:"
	@echo "  make setup              Create venv and install project + pytest"
	@echo "  make test               Run test suite (short output)"
	@echo "  make integration-test   Run end-to-end template script test"
	@echo "  make it                 Short alias for integration-test"
	@echo "  make test-install       Run sandboxed installation flow test"
	@echo "  make test-binary        Run standalone binary build test"
	@echo "  make rename-brand       Preview scripted brand rename to nexo"
	@echo "  make rename-brand-apply Apply scripted brand rename to nexo"
	@echo "  make run CMD='...'      Run any command inside .venv"
	@echo "  make r CMD='...'        Short alias for run"

setup:
	python3 -m venv $(VENV)
	$(PY) -m pip install -U pip
	$(PY) -m pip install -e . pytest

test:
	$(PY) -m pytest tests/ -q --tb=short

t: test

integration-test:
	@bash tests/integration_test.sh

it: integration-test

test-install:
	@bash tests/test_install_flow.sh

test-binary:
	@bash tests/test_binary_build.sh

integration-test-binary:
	@USE_BINARY=1 bash tests/integration_test.sh

rename-brand:
	python tools/rename_brand.py --root .

rename-brand-apply:
	python tools/rename_brand.py --root . --apply

run:
	@if [ -z "$(CMD)" ]; then \
		echo "Usage: make run CMD='python -m pytest tests/ -q --tb=short'"; \
		exit 1; \
	fi
	@bash -lc 'source $(VENV)/bin/activate && $(CMD)'

r: run
