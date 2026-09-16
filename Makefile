.PHONY: build test lint format types arch check cargo-fmt clean release bench build-release

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

bench: build-release ## run the rival benchmark matrix and render charts + markdown report
	mkdir -p .benchmark
	uv run pytest tests/benchmark -m bench -p no:randomly \
		--benchmark-json=.benchmark/bench.json --benchmark-min-rounds=5 --benchmark-max-time=0.5 -q
	uv run python tests/benchmark/report.py .benchmark/bench.json .benchmark
