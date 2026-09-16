# Development

```bash
uv sync                 # install the dev group + build the extension in place
make check              # ruff + format + ty + tach + pytest  (what CI runs)
make test               # unit tests
make bench              # rival benchmark matrix → assets/benchmarks/*.png
make docs               # serve the documentation at http://127.0.0.1:8000
make build-release      # compile the Rust codec optimized
make release            # maturin build --release → wheel in target/wheels
```

## Layout

```
crates/native/          single Rust cdylib, one submodule per format
src/eserde/
  infra/                contracts with zero internal deps: errors, formats, io, protocols
  backends/             one folder per engine: native/ (Rust), msgspec/ (C) + registry
  logic/                the facade: loads/dumps/load/dump/async + Jsonable encoder
tests/
  unit/eserde/          exact mirror of the source tree
  benchmark/            rival matrix + report renderer
  resources/            canonical sample.* fixtures
docs/                   mkdocs-material site
assets/                 logo, banner, benchmark charts
```

Import boundaries are enforced by `tach`: `eserde` → `logic` → `backends` → `infra`/`_native`.
Only the package root has an `__init__.py` (the façade); every subpackage is a namespace folder.

## Releasing

Versioned from git by [release-plz](https://release-plz.dev): conventional commits on
`main` open a version-bump PR; merging it cuts `vX.Y.Z` and GitHub Release, and
`publish.yml` builds sdist + wheels and publishes to PyPI via trusted publishing. The
crate version in `Cargo.toml` is the single source of truth; maturin derives PEP 440.
