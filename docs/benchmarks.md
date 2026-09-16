# Benchmarks

Median decode/encode of a **100 KB** config on CPython 3.14, release build. Lower is
faster; the ratio is against e-serde. Regenerate everything with `make bench`.

The corpus is the canonical `tests/resources/sample.*` file, grown to each size — the
same bytes every rival parses. The rivals are each library's *own* recommended API.

## Decode

![loads](assets/benchmarks/loads.png)

| Format | e-serde | orjson     | msgspec    | pyyaml(C)  | rtoml      | configparser |
| ------ | ------- | ---------- | ---------- | ---------- | ---------- | ------------ |
| JSON   | 0.17 ms | 0.16 ms    | 0.17 ms    | —          | —          | —            |
| YAML   | 2.24 ms | —          | —          | 11.9 ms    | —          | —            |
| TOML   | 1.64 ms | —          | —          | —          | 2.27 ms    | —            |
| INI    | 1.87 ms | —          | —          | —          | —          | 19.3 ms      |

- **JSON** — a tie by construction: e-serde *is* msgspec here. The C decoder holds the GIL.
- **YAML** — 5.3× faster than PyYAML's C loader, 66× faster than ruamel.
- **TOML** — ahead of rtoml, its nearest Rust rival, and 40×+ over the pure-Python parsers.
- **JSONC** — the one format e-serde does not lead: `pyjson5` (Rust, dedicated) beats it ~×0.6.

## Validate (`type=`)

![typed](assets/benchmarks/typed.png)

Decoding is only part of the job. Routing the tree through `msgspec.convert` adds ~×1.4
for a Struct, and stays ~3× ahead of an `orjson → pydantic` pipeline on the same payload.

## Async (GIL-detachment probe)

![async](assets/benchmarks/async.png)

Eight concurrent decodes of a **10 MB** payload, fan-out vs serial-sync ratio:

| Format | async vs serial | Why |
| ------ | --------------- | --- |
| YAML   | **×0.49** (2.0× faster) | saphyr releases the GIL → parallel |
| TOML   | **×0.45** (2.2× faster) | toml-rs releases the GIL → parallel |
| JSON   | ×1.03 (no gain)   | msgspec's C decoder holds the GIL |

The native Rust codecs scale across cores; the C one does not. That is the whole argument
for `aloads` on large payloads.

## Memory

![memory](assets/benchmarks/memory.png)

Python-visible allocations (`tracemalloc`) per 100 KB decode. C/Rust buffers that never
touch the Python allocator read low by design — that is a feature, not a measurement gap.

## Reproduce

```bash
make bench        # builds release, runs the matrix, writes assets/benchmarks/*.png
```
