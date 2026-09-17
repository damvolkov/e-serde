# Reference

The complete public surface. All eight functions share one shape: a data source, an
optional `format`, an optional `type` schema, a `strict` flag, a `registry` and
per-call encode/decode hooks. Keyword arguments are enforced.

```python
import eserde
```

| Function | Signature |
| -------- | --------- |
| `loads`  | `loads(source: bytes \| str \| Path, *, format: Format \| None = None, type: type \| None = None, strict: bool = True, registry = default_registry, object_hook: Callable[[dict], Any] \| None = None, dec_hook: Callable[[type, Any], Any] \| None = None) → Any` |
| `load`   | `load(target: Path \| BinaryIO, *, format: Format \| None = None, type: type \| None = None, strict: bool = True, registry = default_registry) → Any` |
| `dumps`  | `dumps(obj: Any, *, format: Format = Format.JSON, registry = default_registry, default: Callable[[Any], Any] \| None = None, encoders: Mapping[type, Callable] \| None = None) → bytes` |
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

## `dumps(obj, *, format=Format.JSON, registry, default=None, encoders=None)`

Encode `obj` to `bytes` in `format`, normalizing through the Jsonable encoder first
(datetime → ISO, `Enum` → value, `bytes` → base64) so every codec sees the same tree.
`encoders` intercepts by exact type ahead of every built-in; `default` is the last
resort for unknown types; hook results are re-walked.

## `dump(obj, target, *, format=None, registry)`

Encode `obj` straight into a file. Format is inferred from a `Path`; a binary handle
requires `format`.

## `type`, `strict` and the hooks

`type=` routes the decoded tree through `msgspec.convert` into any Struct, dataclass,
TypedDict or attrs class; pydantic models and generics (`list[M]`, `dict[str, M]`) are
detected and validated through a lazily imported, cached `TypeAdapter`. Decoding is
Rust/C; validation is msgspec's or pydantic's. `strict=False` opts into coercion (the
escape hatch INI needs). A schema violation raises `LoadError` either way.

`dec_hook=(type, value) -> Any` teaches msgspec custom field types (requires `type=`);
`object_hook=(dict) -> Any` rewrites each decoded mapping bottom-up, json semantics.
`encode.register` remains available for library-wide type rules.

## `registry`

A `CodecRegistry` maps each `Format` to its codec. `default_registry` ships the five
built-ins; pass a custom `registry=` to swap engines without touching call sites.

## `eserde.compat`

`json`-module drop-in surface: `compat.dumps(obj, /, **json_kwargs) -> str` and
`compat.loads(s, /, **json_kwargs)`. Default invocations are byte-faithful to the
stdlib; `ensure_ascii=False` opts into the native compact utf-8 path; json behaviours
e-serde does not share (`cls=`, `parse_*`, `object_pairs_hook`, `skipkeys`, `indent`,
`sort_keys`, `allow_nan=False`) delegate to the stdlib module.

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
