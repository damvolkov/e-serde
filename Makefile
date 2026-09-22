.PHONY: build build-release test lint format types arch check cargo-fmt clean release bench docs docs-serve

build:            ## compile native extension into the venv (debug)
	uv run maturin develop

build-release:    ## compile native extension with optimizations
	uv run maturin develop --release

test:             ## run unit tests
	uv run pytest

lint:             ## ruff check (auto-fix)
	uv run ruff check --fix src tests tools

format:           ## ruff format
	uv run ruff format src tests tools

types:            ## static type checking
	uv run ty check

arch:             ## enforce import boundaries
	uv run tach check

check: lint format types arch test   ## everything CI runs

cargo-fmt:        ## format rust sources
	cargo fmt --all

clean:            ## remove build artifacts
	cargo clean
	rm -rf .pytest_cache .ruff_cache .coverage site src/eserde/__pycache__

release:          ## build distributable wheel
	uv run maturin build --release

bench: build-release ## rival benchmark matrix → charts in assets/benchmarks
	mkdir -p .benchmark
	uv run pytest tests/benchmark -m bench -p no:randomly \
		--benchmark-json=.benchmark/bench.json --benchmark-min-rounds=5 --benchmark-max-time=0.5 -q
	uv run python tests/benchmark/report.py .benchmark/bench.json .benchmark
	cp .benchmark/*.png assets/benchmarks/
	rm -rf .benchmark

docs-serve:       ## serve the documentation locally
	uv run --group docs mkdocs serve -a 127.0.0.1:8000

docs:             ## build the documentation (strict, fails on broken links)
	uv run --group docs mkdocs build --strict

docs-formats:     ## regenerate docs/formats/*.md from the STANDARDS contract
	uv run python tools/gen_formats.py
