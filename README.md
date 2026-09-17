<p align="center">
  <img src="assets/eserde-banner.svg" width="520" alt="e-serde">
</p>

<p align="center">
  <a href="https://github.com/damvolkov/e-serde/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/damvolkov/e-serde/ci.yml?label=test" alt="CI"></a>
  <a href="https://pypi.org/project/e-serde/"><img src="https://img.shields.io/pypi/v/e-serde?color=166b7e" alt="PyPI"></a>
  <a href="https://pypi.org/project/e-serde/"><img src="https://img.shields.io/pypi/pyversions/e-serde" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/pypi/l/e-serde?color=166b7e" alt="License"></a>
</p>

Universal structured-data loader: native **Rust** codecs that decode any popular config
format into native Python objects — and, when you ask, into frozen `msgspec` models.
Two verbs, `loads`/`dumps`, sync and async twins, one wheel. `json`-module semantics,
strict typing, no surprises.

Part of the **Eager** (`e-`) stack by [damvolkov](https://github.com/damvolkov), built on
open-source engines — the speed and robustness of C and Rust, for serialization in Python.

## Install

```bash
uv add e-serde          # or: pip install e-serde
```

## Usage

```python
import eserde
from pathlib import Path
import msgspec

eserde.__version__          # '0.1.0'

# bytes/str sources name the format; Paths autodetect by extension.
cfg = eserde.loads(b'{"host": "0.0.0.0", "port": 8080}', format=eserde.Format.JSON)
# {'host': '0.0.0.0', 'port': 8080}

raw = eserde.dumps({"name": "demian", "n": 42}, format=eserde.Format.YAML)
# b'name: demian\n"n": 42\n'

cfg = eserde.load(Path("config.toml"))        # format inferred from the .toml suffix

# validate straight into a frozen model — Rust decodes, msgspec validates
class Server(msgspec.Struct, frozen=True):
    host: str
    port: int

srv = eserde.loads(b'{"host": "x", "port": 8080}', format=eserde.Format.JSON, type=Server)
# Server(host='x', port=8080)

# file helpers, json-module semantics
eserde.dump(cfg, Path("out.jsonc"))

# custom types, per call (json/orjson semantics) — no global patching
from fractions import Fraction
eserde.dumps({"f": Fraction(1, 2)}, format=eserde.Format.JSON, default=float)
# b'{"f":0.5}'
eserde.loads(b'{"n": 5}', format=eserde.Format.JSON, type=SomePydanticModel)
# validated through TypeAdapter; violations still surface as eserde.LoadError

# json-module drop-in for frameworks that duck-type it (aiohttp, structlog, logging)
from eserde import compat
compat.dumps({"a": 1}, ensure_ascii=False)         # '{"a":1}' native compact utf-8
```

Async — I/O and GIL-free native parsing off the event loop:

```python
async def main():
    srv = await eserde.aloads(Path("config.yaml"), type=Server)
```

`strict=False` enables type coercion — the escape hatch INI needs. The full guide lives
at [damvolkov.github.io/e-serde](https://damvolkov.github.io/e-serde/).

## Formats and backends

| Format | Extension             | Engine                       | Notes                     |
| ------ | --------------------- | ---------------------------- | ------------------------- |
| JSON   | `.json`               | `msgspec.json` (C)           | fastest-in-class decode   |
| JSONC  | `.jsonc`              | `jsonc-parser` (Rust, Deno)  | comments, trailing commas |
| YAML   | `.yaml` `.yml`        | `saphyr` (Rust)              | YAML 1.2 core schema      |
| TOML   | `.toml`               | `toml` (Rust)                | datetimes → ISO strings   |
| INI    | `.ini` `.cfg` `.conf` | `rust-ini` (Rust)            | no interpolation          |

Everything Rust lives in one extension module (`eserde._native`), compiled by `maturin`
from `crates/native`. The only runtime dependency is `msgspec`.

## Benchmarks

Median decode of a 100 KB config on CPython 3.14 (release build). Regenerate with `make bench`.

![loads](assets/benchmarks/loads.png)

| Format | e-serde | fastest rival          | margin                 |
| ------ | ------- | ---------------------- | ---------------------- |
| JSON   | 0.17 ms | orjson 0.16 ms         | ≈tie (uses msgspec)    |
| YAML   | 2.24 ms | pyyaml (C) 5.3× slower | ruamel 66× slower      |
| TOML   | 1.64 ms | rtoml 1.4× slower      | tomlkit 42× slower     |
| JSONC  | 0.66 ms | pyjson5 *faster* ×0.6  | the one format behind   |
| INI    | 1.87 ms | configparser 10× slower | —                     |

Because the Rust codecs release the GIL, `aloads` parallelizes decode: on 10 MB YAML/TOML the
async fan-out is ~2× faster than serial sync (JSON stays flat — msgspec's C decoder holds the
GIL). More charts in [`assets/benchmarks/`](assets/benchmarks/):
[dumps](assets/benchmarks/dumps.png) ·
[typed](assets/benchmarks/typed.png) ·
[async](assets/benchmarks/async.png) ·
[memory](assets/benchmarks/memory.png).

## Architecture

```
crates/native/          single Rust cdylib, one submodule per format
src/eserde/
  __init__.py           the one façade: import eserde; eserde.loads(...)
  infra/                contracts with zero internal deps: errors, formats, io, protocols
  backends/             one folder per engine: native/ (Rust), msgspec/ (C) + registry
  logic/                the facade functions: loads/dumps/load/dump/async + Jsonable encoder
tests/
  unit/eserde/          exact mirror of src
  benchmark/            rival matrix + report renderer
  resources/            canonical sample.* fixtures
docs/                   mkdocs-material site
```

Only the package root has an `__init__.py`; every subpackage is a namespace folder. Import
boundaries are enforced by `tach`: `eserde` → `logic` → `backends` → `infra`/`_native`.

Design rules:

- `loads`/`dumps` operate on `bytes | str | Path`; `load`/`dump` on `Path` or binary handles.
- `type=` routes the decoded tree through `msgspec.convert`: validation is msgspec's,
  decoding is Rust's. `strict=False` enables coercion.
- `dumps` normalizes through the Jsonable encoder first (datetime → ISO, Enum → value,
  bytes → base64), so every format sees the same tree.
- Round-trip losses are explicit: JSONC comments are dropped on dumps; TOML has no null;
  YAML non-scalar keys and multi-document streams are rejected.

## Development

```bash
uv sync                  # installs the dev group, builds the extension in place
make test                # pytest
make check               # ruff + format + ty + tach + pytest (what CI runs)
make bench               # rival benchmark matrix → assets/benchmarks/*.png
```

## Roadmap

The next iteration probes interop: using e-serde as the front-end decoder for
`msgspec`, `pydantic` and `fastapi` request/config pipelines.

## License

MIT — see [LICENSE](LICENSE).
