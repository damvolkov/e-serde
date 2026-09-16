# Reference

The complete public surface. All eight functions share one shape: a data source, an
optional `format`, an optional `type` schema, a `strict` flag and a `registry`. Keyword
arguments are enforced.

```python
import eserde
```

| Function | Signature |
| -------- | --------- |
| `loads`  | `loads(source: bytes \| str \| Path, *, format: Format \| None = None, type: type \| None = None, strict: bool = True, registry = default_registry) → Any` |
| `load`   | `load(target: Path \| BinaryIO, *, format: Format \| None = None, type: type \| None = None, strict: bool = True, registry = default_registry) → Any` |
| `dumps`  | `dumps(obj: Any, *, format: Format = Format.JSON, registry = default_registry) → bytes` |
| `dump`   | `dump(obj: Any, target: Path \| BinaryIO, *, format: Format \| None = None, registry = default_registry) → None` |
| `aloads` | `async` twin of `loads` |
| `aload`  | `async` twin of `load` |
| `adumps` | `async` twin of `dumps` |
| `adump`  | `async` twin of `dump` |

## `loads(source, *, format=None, type=None, strict=True, registry)`

Decode `source` into native Python objects, or into `type` when a schema is given.
Auto-detects `format` from a `Path` extension; `bytes`/`str` sources require it.

```python
eserde.loads(b"[a]\nk = 1\n", format=eserde.Format.INI)      # {'a': {'k': '1'}}
```

## `load(target, *, format=None, type=None, strict=True, registry)`

Decode a file — a `Path` or an open binary handle. Same contract as `json.load`;
a `Path` infers the format from its suffix.

## `dumps(obj, *, format=Format.JSON, registry)`

Encode `obj` to `bytes` in `format`, normalizing through the Jsonable encoder first
(datetime → ISO, `Enum` → value, `bytes` → base64) so every codec sees the same tree.

## `dump(obj, target, *, format=None, registry)`

Encode `obj` straight into a file. Format is inferred from a `Path`; a binary handle
requires `format`.

## `type` and `strict`

`type=` routes the decoded tree through `msgspec.convert` into any Struct, dataclass or
TypedDict. Decoding is Rust/C; validation is msgspec's. `strict=False` opts into coercion
(the escape hatch INI needs). A schema violation raises `LoadError`.

## `registry`

A `CodecRegistry` maps each `Format` to its codec. `default_registry` ships the five
built-ins; pass a custom `registry=` to swap engines without touching call sites.

## `Format`

```python
class Format(StrEnum):
    JSON; JSONC; YAML; TOML; INI
```

`detect_format(path)` maps `.json .jsonc .yaml .yml .toml .ini .cfg .conf` → `Format`,
or returns `None`.

## Errors

All derive from `eserde.LoaderError`:

| Exception      | Raised when                                          |
| -------------- | ---------------------------------------------------- |
| `FormatError`  | format can't be inferred, or a source type is invalid |
| `LoadError`    | decode failed, or `type=` validation failed           |
| `DumpError`    | encoding failed                                       |
| `EncoderError` | the Jsonable normalizer hit an unserializable value   |
| `CodecError`   | a backend was unavailable at runtime                  |
