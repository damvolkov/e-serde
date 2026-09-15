# e-serde

Universal loader for configuration files — native Rust codecs that decode any popular
config format into native Python objects and, when you ask, into frozen `msgspec`
models. Two verbs, sync and async, one wheel.

## Formats and backends

| Format | Extension          | Engine                        | Notes                          |
| ------ | ------------------ | ----------------------------- | ------------------------------ |
| JSON   | `.json`            | `msgspec.json` (C)            | fastest-in-class decode        |
| JSONC  | `.jsonc`           | `jsonc-parser` (Rust, Deno)   | comments, trailing commas      |
| YAML   | `.yaml` `.yml`     | `saphyr` (Rust)               | YAML 1.2 core schema           |
| TOML   | `.toml`            | `toml` (Rust, rust-toml org)  | datetimes → ISO strings        |
| INI    | `.ini` `.cfg` `.conf` | `rust-ini` (Rust)         | strict: no interpolation       |

Everything Rust lives in one extension module (`e_serde._native`), compiled by
`maturin` from `crates/native`. No Python runtime dependencies beyond `msgspec`.

## Usage

```python
from pathlib import Path
import msgspec
from e_serde import Format, loads, dumps, dump, aloads

class Server(msgspec.Struct, frozen=True):
    host: str
    port: int

# bytes/str sources require the format; Paths autodetect by extension.
cfg = loads(Path("config.toml"), type=Server)             # frozen model, validated
cfg = loads(b'{"host": "x", "port": 8080}', format=Format.JSON, type=Server)
data = loads(Path("app.conf"), strict=False)              # INI str coercion ("8080" → 8080)
raw = dumps({"name": "demian", "n": 42}, format=Format.YAML)

# file helpers, json-module semantics
dump(cfg, Path("out.jsonc"))                              # format from extension

# async: I/O and GIL-free native parsing off the event loop
cfg = await aloads(Path("config.yaml"), type=Server)
```

## Layout

```
crates/native/          single Rust cdylib, one submodule per format
src/e_serde/
  infra/                contracts with zero internal deps: errors, formats, io, protocols
  backends/             one folder per engine: native/ (Rust), msgspec/ (C) + registry
  logic/                the facade: loads/dumps/load/dump/async + Jsonable encoder
```

Import boundaries are enforced by `tach`: `e_serde` → `logic` → `backends` → `infra`/`_native`.

## Development

```bash
uv sync --group dev    # builds the extension in place (maturin backend)
make test              # pytest
make check             # ruff + ty + tach + pytest
make release           # maturin build --release → wheel in target/wheels
```

## Versioning

`Cargo.toml` is the single source of truth: pyproject declares `dynamic =
["version"]` and maturin derives the wheel version from the crate (SemVer →
PEP 440). A release bump therefore moves version, git tag and wheel in one
commit — the canonical setup is `release-plz` on main: it opens the bump PR,
and the merge produces `vX.Y.Z` + a CI job that publishes the wheel from the
same tree. No hatch, no version files to keep in sync by hand.

## Design notes

- `loads`/`dumps` operate on `bytes | str | Path`; `load`/`dump` on `Path` or binary handles.
- `type=` routes the decoded tree through `msgspec.convert` — validation is msgspec's,
  decoding is Rust's. `strict=False` enables type coercion (the escape hatch INI needs).
- `dumps` normalizes through the Jsonable encoder first (datetime → ISO, Enum → value,
  bytes → base64), so every format sees the same tree.
- Native parsing releases the GIL: `aloads` parallelizes decode across cores.
- Round-trip losses are explicit: JSONC comments are dropped on dumps; TOML has no null;
  YAML non-scalar keys and multi-document streams are rejected.
