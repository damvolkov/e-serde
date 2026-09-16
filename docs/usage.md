# Usage

Six functions with `json`-module semantics. `loads/dumps` take `bytes | str | Path`;
`load/dump` take a `Path` or an open binary handle. Every function has an async twin
prefixed with `a`.

```python
import eserde
```

!!! tip "Format"
    Sources given as `bytes`/`str` must name the format: `format=eserde.Format.JSON`.
    A `Path` autodetects from its extension (`.json .jsonc .yaml .yml .toml .ini .cfg .conf`).

## loads — decode to objects

```python
from eserde import Format

data = eserde.loads(b'{"host": "0.0.0.0", "port": 8080}', format=Format.JSON)
# {'host': '0.0.0.0', 'port': 8080}

# a str source is fine too — the bytes are decoded as UTF-8
eserde.loads('port: 8080', format=Format.YAML)
# {'port': 8080}
```

## load — decode a file

```python
from pathlib import Path

cfg = eserde.load(Path("config.toml"))          # format from the .toml suffix
raw = eserde.loads(Path("deploy.yaml"))          # loads() accepts a Path too

with open("app.json", "rb") as fh:               # or an open binary handle
    data = eserde.load(fh, format=Format.JSON)
```

## type= — validate into a model

Pass `type=` and the plain tree is run through `msgspec.convert` into any Struct,
dataclass or TypedDict. Decoding stays Rust/C; validation is msgspec's.

```python
import msgspec

class Server(msgspec.Struct, frozen=True):
    host: str
    port: int

eserde.loads(b'{"host": "x", "port": 8080}', format=Format.JSON, type=Server)
# Server(host='x', port=8080)

# the same works for formats without a native validator
eserde.loads(Path("server.yaml"), type=Server)
```

A schema violation raises `eserde.LoadError`, not a raw `msgspec.ValidationError`.

## strict=False — coercion

By default types are enforced. `strict=False` lets msgspec coerce — the escape hatch
for INI, where every value is a string:

```python
eserde.loads(b"[svc]\nport = 8080\n", format=Format.INI, type=dict[str, Server], strict=False)
# {'svc': Server(port=8080)}   # "8080" coerced to int
```

## dumps / dump — encode

`dumps` returns `bytes`; `dump` writes straight to a `Path` or handle. Every input is
normalized through the Jsonable encoder first (datetime → ISO, `Enum` → value, `bytes`
→ base64), so each format sees the same tree.

```python
eserde.dumps({"name": "demian", "n": 42}, format=Format.YAML)
# b'name: demian\n"n": 42\n'

eserde.dump({"a": 1}, Path("out.jsonc"))          # format from the .jsonc suffix
```

## Async twins

`aloads / aload / adumps / adump` move both I/O and GIL-free native parsing off the
event loop. The same arguments apply.

```python
import asyncio

async def main():
    cfg = await eserde.aloads(Path("config.yaml"), type=Server)
    await eserde.adump(cfg, Path("copy.json"))

asyncio.run(main())
```

!!! info "When async pays"
    The Rust codecs release the GIL, so concurrent `aloads` parallelize decode across
    cores — on 10 MB YAML/TOML the fan-out is ~2× faster than serial sync. JSON runs on
    msgspec's C decoder, which holds the GIL, so it stays flat. See [Benchmarks](benchmarks.md).

## Errors

Everything raises the `eserde.LoaderError` family:

| Exception          | Raised when                              |
| ------------------ | ---------------------------------------- |
| `FormatError`      | format can't be inferred or is unsupported |
| `LoadError`         | decode failed, or `type=` validation failed |
| `DumpError`         | encoding failed                          |
| `CodecError`        | a backend was unavailable at runtime     |

Full signatures live in the [API reference](reference.md).
