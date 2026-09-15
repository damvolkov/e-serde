.PHONY: build test lint format types arch check cargo-fmt clean release

build:            ## compile native extension into the venv (debug)
	uv run maturin develop

build-release:    ## compile native extension with optimizations
	uv run maturin develop --release

test:             ## run unit tests
	uv run pytest

lint:             ## ruff check (auto-fix)
	uv run ruff check --fix src tests

format:           ## ruff format
	uv run ruff format src tests

types:            ## static type checking
	uv run ty check

arch:             ## enforce import boundaries
	uv run tach check

check: lint format types arch test   ## everything CI runs

cargo-fmt:        ## format rust sources
	cargo fmt --all

clean:            ## remove build artifacts
	cargo clean
	rm -rf .pytest_cache .ruff_cache .coverage src/e_serde/__pycache__

release:          ## build distributable wheel
	uv run maturin build --release
