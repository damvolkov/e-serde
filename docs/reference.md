# Reference

The complete public surface: six functions plus async twins, one shared option set,
keyword arguments enforced.

```python
import eserde
```

## Signatures

```python
def loads(
    source: bytes | str | Path,
    *,
    format: Format | None = None,
    type: builtins.type[Any] | None = None,
    strict: bool = True,
    registry: CodecRegistry = default_registry,
    object_hook: Callable[[dict[str, Any]], Any] | None = None,
    dec_hook: Callable[[Any, Any], Any] | None = None,
) -> Any: ...

def dumps(
    obj: Any,
    *,
    format: Format = Format.JSON,
    registry: CodecRegistry = default_registry,
    default: Callable[[Any], Any] | None = None,
    encoders: Mapping[type, Callable[[Any], Any]] | None = None,
) -> bytes: ...

def load(target: Path | BinaryIO, *, ...) -> Any: ...        # like loads, file input
def dump(obj: Any, target: Path | BinaryIO, *, ...) -> None: ...   # like dumps, file output

# async twins — identical signatures, offloaded I/O and parsing
def aloads(...) -> Awaitable[Any]: ...
def adumps(...) -> Awaitable[bytes]: ...
def aload(...) -> Awaitable[Any]: ...
def adump(...) -> Awaitable[None]: ...
```

## Options

| Parameter | Applies to | Effect |
| --- | --- | --- |
| `format` | all | required for `bytes`/`str` sources and handles; inferred from a `Path` suffix |
| `type` | decode | routes the plain tree through `msgspec.convert` into a Struct, dataclass, TypedDict or attrs class; pydantic models and generics (`list[M]`, `dict[str, M]`) are detected and validated through a lazily imported, cached `TypeAdapter`. Decoding stays Rust/C; validation is msgspec's or pydantic's. Violations raise `LoadError` either way |
| `strict` | decode | `False` opts into msgspec coercion — the escape hatch INI needs |
| `object_hook` | decode | rewrites each decoded mapping bottom-up, json semantics |
| `dec_hook` | decode | `(type, value) -> Any` custom field types inside `type=`; without `type=` raises `FormatError` |
| `default` | encode | last resort for unknown types, json/orjson semantics |
| `encoders` | encode | `Mapping[type, Callable]` intercepted by exact type ahead of every built-in; results are re-walked |
| `registry` | all | a `CodecRegistry` mapping each `Format` to its codec; `default_registry` ships the five built-ins — pass a custom one to swap engines without touching call sites |

`encode.register` remains available for library-wide type rules.

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

| Exception | Raised when |
| --- | --- |
| `FormatError` | format can't be inferred, or a source type is invalid |
| `LoadError` | decode failed, or `type=` validation failed |
| `DumpError` | encoding failed |
| `EncoderError` | the Jsonable normalizer hit an unserializable value |
| `CodecError` | a backend was unavailable at runtime |
