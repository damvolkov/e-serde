# Usage

Six functions with `json`-module semantics and keyword-only options. `loads`/`dumps` are
in-memory; `load`/`dump` take files; every function has an async twin prefixed with `a`.

| Function | Input | Output |
| --- | --- | --- |
| `loads` | `bytes \| str \| Path` | plain tree, or the model in `type=` |
| `dumps` | any object | `bytes` |
| `load` | `Path \| BinaryIO` | like `loads` |
| `dump` | object → file | `None` |
| `aloads` · `adumps` · `aload` · `adump` | same | awaitables of the same |

```python
import eserde
import msgspec
from eserde import Format
from pathlib import Path
```

!!! tip "Format"
    Sources given as `bytes`/`str` must name the format: `format=Format.JSON`.
    A `Path` autodetects from its extension (`.json .jsonc .yaml .yml .toml .ini .cfg .conf`).

## loads — decode

```python
cfg = eserde.loads(b'{"host": "0.0.0.0", "port": 8080}')  # pure JSON content sniffs itself
# {'host': '0.0.0.0', 'port': 8080}

eserde.loads('port: 8080', format="yaml")           # a str source is content; a plain format name works
# {'port': 8080}
```

```python
class Server(msgspec.Struct, frozen=True):
    host: str
    port: int

srv = eserde.loads(src, format=Format.JSON, type=Server)               # → Server
srv = eserde.loads(Path("server.yaml"), type=list[Server])             # Path + generics
ini = eserde.loads(b"[svc]\nport = 8080\n", format=Format.INI,
                   type=dict[str, Server], strict=False)               # "8080" → 8080
```

| kwarg | effect |
| --- | --- |
| `format=` | a `Format` member or its name; inferred from a path, sniffed from pure JSON, required otherwise |
| `type=` | validate into a Struct, dataclass, TypedDict, attrs or pydantic model |
| `strict=False` | msgspec coercion — the escape hatch INI needs |
| `object_hook=` | rewrite every decoded mapping, innermost first (json semantics) |
| `dec_hook=` | teach `type=` custom field types; requires `type=`, else `FormatError` |
| `registry=` | swap the default codec set |

A schema violation raises `eserde.LoadError`, never a raw `msgspec.ValidationError`.

## dumps — encode

```python
raw = eserde.dumps({"name": "demian", "n": 42}, format=Format.YAML)
# b'name: demian\n"n": 42\n'
```

```python
from fractions import Fraction
from datetime import date

eserde.dumps({"f": Fraction(1, 2)}, format=Format.JSON, default=float)
# b'{"f":0.5}'

eserde.dumps({"f": Fraction(1, 2)}, format=Format.JSON, encoders={Fraction: str})
# b'{"f":"1/2"}'

eserde.dumps({"d": date(2020, 1, 2)}, format=Format.JSON, encoders={date: lambda d: d.year})
# b'{"d":2020}'   # exact-type hook beats the ISO-string built-in
```

Every input is normalized through the Jsonable encoder first (datetime → ISO, `Enum` →
value, `bytes` → base64), so each format sees the same tree.

| kwarg | effect |
| --- | --- |
| `format=` | defaults to `Format.JSON` |
| `encoders=` | exact-type hooks, ahead of every built-in; the result is re-walked |
| `default=` | json/orjson-style last resort for unknown types; without it → `EncoderError` |
| `registry=` | swap the default codec set |

Both hooks are per call — no global patching, no monkey-patching.

## load / dump — files

```python
cfg = eserde.load(Path("config.toml"))              # format from the .toml suffix

with open("app.json", "rb") as fh:
    data = eserde.load(fh, format=Format.JSON)      # an open handle needs the format

eserde.dump(cfg, Path("out.jsonc"))                 # writes straight to disk → None
```

Same kwargs as `loads` / `dumps`; `load`/`dump` add nothing of their own.

## Async twins

`aloads` · `adumps` · `aload` · `adump` — same signatures; I/O and the GIL-free native
parse run off the event loop.

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

## CSV and TSV — tables, typed

```python
rows = eserde.loads(b'id,name,qty\n1,Turul,3\n2,Ainulindale,\n', format=Format.CSV)
# [{'id': 1, 'name': 'Turul', 'qty': 3}, {'id': 2, 'name': 'Ainulindale', 'qty': None}]
```

The header names the columns; **every column is type-inferred across its values**, polars-style:
integers widen only when the data demands it, empty fields become `None`, and integers past i64
stay exact. Quoted multi-line fields, `\r\n` and a leading BOM are all handled. Ragged rows and
duplicate header names are rejected, never repaired. `dumps` writes RFC 4180 from a non-empty
`list[dict]` (the first record's key order is the header); `Format.TSV` is the same codec, tab-delimited.
Under `type=list[MyStruct]` the inferred records convert directly.

## embed — content references

A document can index prose instead of holding it:

```yaml
# doc.yaml
title: Guía de instalación
content:
  format: markdown
  source: ./content/guia.md      # a real .md file, resolved at load
```

```python
import eserde
from pathlib import Path

doc = eserde.loads(Path("doc.yaml"), embed=True)
doc["content"]["source"]  # the full text of content/guia.md
```

`embed=True` resolves every `source` key; `embed=("path", "body")` names the keys. References
must point at plain `.md` files, are resolved against the document's own directory (or `root=`
for `bytes`/`str` sources) and confined inside it — `../` and absolute escapes raise `LoadError`.
A sibling `format:` must say `markdown`. The embedding is copy-on-write and all-or-nothing: a
broken reference never returns a half-built tree. Works in every format and in the async twins.

## object_hook and dec_hook

`object_hook` post-processes every decoded mapping (innermost first, json semantics).
`dec_hook` teaches the validator about custom field types inside a `type=` schema:

```python
from ipaddress import IPv4Address

class Net(msgspec.Struct):
    ip: IPv4Address

eserde.loads(b'{"ip": "10.0.0.1"}', format=Format.JSON, type=Net, dec_hook=lambda t, v: t(v))
# Net(ip=IPv4Address('10.0.0.1'))
```

## pydantic and attrs models

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

## compat — `json` drop-in

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

## Errors

Everything raises the `eserde.LoaderError` family:

| Exception | Raised when |
| --- | --- |
| `FormatError` | format can't be inferred or is unsupported |
| `LoadError` | decode failed, or `type=` validation failed |
| `DumpError` | encoding failed |
| `EncoderError` | a value had no rule and no `default=` |
| `CodecError` | a backend was unavailable at runtime |

Full signatures live in the [API reference](reference.md).
