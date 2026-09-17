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

## Custom types on encode

`encoders=` intercepts by exact type, ahead of every built-in rule; `default=` is the
json/orjson-style last resort for anything the walk cannot recognize. Both are per call —
no global patching, no monkey-patching. The hook result is re-walked, so hooks may return
structures of their own. Unknown types without a hook raise `EncoderError`, exactly as before.

```python
from datetime import date
from fractions import Fraction

eserde.dumps({"f": Fraction(1, 2)}, format=Format.JSON, default=float)
# b'{"f":0.5}'

eserde.dumps({"f": Fraction(1, 2)}, format=Format.JSON, encoders={Fraction: str})
# b'{"f":"1/2"}'

eserde.dumps({"d": date(2020, 1, 2)}, format=Format.JSON, encoders={date: lambda d: d.year})
# b'{"d":2020}'     # exact-type hook beats the ISO-string built-in
```

## Custom types on decode

`object_hook` post-processes every decoded mapping, json semantics (innermost first).
`dec_hook` teaches the validator about custom fields inside a `type=` schema:

```python
from ipaddress import IPv4Address
import msgspec

class Net(msgspec.Struct):
    ip: IPv4Address

eserde.loads(b'{"ip": "10.0.0.1"}', format=Format.JSON, type=Net, dec_hook=lambda t, v: t(v))
# Net(ip=IPv4Address('10.0.0.1'))
```

`dec_hook` without `type=` raises `FormatError` — there is nothing to type it against.

## pydantic and attrs as `type=`

`type=` accepts any pydantic model or generic (`list[User]`, `dict[str, User]`) and routes
it through a cached `TypeAdapter`, imported lazily; attrs stays on the msgspec path.
Schema violations surface as `eserde.LoadError` regardless of which engine caught them:

```python
import pydantic

class User(pydantic.BaseModel):
    name: str
    age: int

eserde.loads(b'[{"name": "x", "age": 9}]', format=Format.JSON, type=list[User])
# [User(name='x', age=9)]     # decode: native codecs; validate: pydantic
```

## json drop-in (`eserde.compat`)

Frameworks duck-type the stdlib module (`json_serialize=`, renderers, formatters).
`eserde.compat` speaks `json.dumps`/`json.loads` exactly — same signature, `str` output:

```python
from eserde import compat

compat.dumps({"a": 1}, ensure_ascii=False)      # '{"a":1}'  — native compact utf-8
compat.dumps({"a": 1})                          # byte-faithful to stdlib json
compat.loads('{"a": 1.5}', parse_float=Decimal) # delegated to stdlib, never guessed
```

Behaviours e-serde does not share with the stdlib (`cls=`, ascii escaping, `indent`,
`sort_keys`, `parse_*`, `object_pairs_hook`) delegate to it: slower, but exact — no
silent surprises behind a json-shaped signature.

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
