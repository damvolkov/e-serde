"""Public facade — the whole library is six functions with json-module semantics.

`loads`/`dumps` operate on `bytes | str | Path`; `load`/`dump` operate on files
(`Path` or open binary handles); `*`-prefixed async twins offload both I/O and GIL-free
native decoding to worker threads. Passing `type=` decodes the plain tree through
`msgspec.convert` into any Struct/dataclass/TypedDict — frozen models are the point.
"""

from __future__ import annotations

from asyncio import to_thread
from collections.abc import Callable, Sequence
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, get_args

import msgspec

from eserde.backends.registry import CodecRegistry, default_registry
from eserde.infra.errors import FormatError, LoadError
from eserde.infra.formats import Format, coerce_format, detect_format, sniff_format
from eserde.infra.io import aread_bytes, aread_handle, awrite_bytes
from eserde.logic.embed import DEFAULT_EMBED_KEYS
from eserde.logic.embed import embed as embed_tree
from eserde.logic.encoder import Default, Encoders, encode

if TYPE_CHECKING:
    import builtins

type Source = bytes | str | Path
type Target = str | Path | BinaryIO
type FormatLike = Format | str
type ObjectHook = Callable[[dict[str, Any]], Any]
type DecHook = Callable[[Any, Any], Any]
type Embed = Sequence[str] | bool


def _embed_keys(embed: Embed) -> tuple[str, ...]:
    if isinstance(embed, bool):
        return DEFAULT_EMBED_KEYS if embed else ()
    return tuple(embed)


def _embed_root(root: str | Path | None, base: Path | None) -> Path:
    if root is not None:
        return Path(root)
    if base is None:
        msg = "embed requires root= when the source carries no path to anchor relative references"
        raise FormatError(msg)
    return base


def loads(
    source: Source,
    *,
    format: FormatLike | None = None,
    type: builtins.type[Any] | None = None,
    strict: bool = True,
    registry: CodecRegistry = default_registry,
    object_hook: ObjectHook | None = None,
    dec_hook: DecHook | None = None,
    embed: Embed = False,
    root: str | Path | None = None,
) -> Any:
    """Decode `source` into native Python objects, or into `type` when a schema is given.

    `format` accepts a `Format` member or its plain name; `Path` sources infer it from
    the extension, and JSON-object-shaped `bytes`/`str` may sniff it — anything else
    must declare it. `object_hook` post-processes every decoded mapping (json
    semantics); `dec_hook` teaches `type=` about custom fields (msgspec semantics).
    `embed` inlines references: `True` resolves `source:` keys against the document's
    directory (or `root=`), a sequence names the keys to treat as `.md` references.
    """
    fmt, data, base = _resolve(source, format, "loads")
    keys = _embed_keys(embed)
    tree = _decode_sniffed(registry, fmt, data, sniffed=format is None and not isinstance(source, Path))
    if keys:
        tree = embed_tree(tree, keys, _embed_root(root, base))
    return _finalize(tree, type=type, strict=strict, object_hook=object_hook, dec_hook=dec_hook)


def dumps(
    obj: Any,
    *,
    format: FormatLike = Format.JSON,
    registry: CodecRegistry = default_registry,
    default: Default | None = None,
    encoders: Encoders | None = None,
) -> bytes:
    """Encode `obj` to bytes in `format`, normalizing through the Jsonable encoder first.

    `encoders`/`default` customize the normalization per call, json/orjson semantics.
    """
    return registry.get(coerce_format(format)).dumps(encode(obj, default=default, encoders=encoders))


def load(
    target: Target,
    *,
    format: FormatLike | None = None,
    type: builtins.type[Any] | None = None,
    strict: bool = True,
    registry: CodecRegistry = default_registry,
    object_hook: ObjectHook | None = None,
    dec_hook: DecHook | None = None,
    embed: Embed = False,
    root: str | Path | None = None,
) -> Any:
    """Decode a file (path as `str` or `Path`, or an open binary handle)."""
    fmt, data, base = _resolve_file(target, format)
    keys = _embed_keys(embed)
    tree = registry.get(fmt).loads(data)
    if keys:
        tree = embed_tree(tree, keys, _embed_root(root, base))
    return _finalize(tree, type=type, strict=strict, object_hook=object_hook, dec_hook=dec_hook)


def dump(
    obj: Any,
    target: Target,
    *,
    format: FormatLike | None = None,
    registry: CodecRegistry = default_registry,
    default: Default | None = None,
    encoders: Encoders | None = None,
) -> None:
    """Encode `obj` straight into a file. Format inferred from the path; handles require it."""
    target = Path(target) if isinstance(target, str) else target
    data = dumps(obj, format=_target_format(target, format), registry=registry, default=default, encoders=encoders)
    if isinstance(target, Path):
        target.write_bytes(data)
    else:
        target.write(data)


async def aloads(
    source: Source,
    *,
    format: FormatLike | None = None,
    type: builtins.type[Any] | None = None,
    strict: bool = True,
    registry: CodecRegistry = default_registry,
    object_hook: ObjectHook | None = None,
    dec_hook: DecHook | None = None,
    embed: Embed = False,
    root: str | Path | None = None,
) -> Any:
    """Async variant of `loads`. Path reads, embedding and native parsing off the event loop."""
    if isinstance(source, Path):
        data, fmt, base = await aread_bytes(source), _path_format(source, format), source.parent
    else:
        fmt, data, base = _resolve(source, format, "loads")
    keys = _embed_keys(embed)
    tree = await to_thread(_decode_sniffed, registry, fmt, data, sniffed=format is None)
    if keys:
        tree = await to_thread(embed_tree, tree, keys, _embed_root(root, base))
    return await to_thread(_finalize, tree, type=type, strict=strict, object_hook=object_hook, dec_hook=dec_hook)


async def adumps(
    obj: Any,
    *,
    format: FormatLike = Format.JSON,
    registry: CodecRegistry = default_registry,
    default: Default | None = None,
    encoders: Encoders | None = None,
) -> bytes:
    """Async variant of `dumps`."""
    plain = await to_thread(encode, obj, default=default, encoders=encoders)
    return await to_thread(registry.get(coerce_format(format)).dumps, plain)


async def aload(
    target: Target,
    *,
    format: FormatLike | None = None,
    type: builtins.type[Any] | None = None,
    strict: bool = True,
    registry: CodecRegistry = default_registry,
    object_hook: ObjectHook | None = None,
    dec_hook: DecHook | None = None,
    embed: Embed = False,
    root: str | Path | None = None,
) -> Any:
    """Async variant of `load`."""
    target = Path(target) if isinstance(target, str) else target
    fmt, data, base = (
        (_path_format(target, format), await aread_bytes(target), target.parent)
        if isinstance(target, Path)
        else (_require_format(format, "file handle"), await aread_handle(target), None)
    )
    keys = _embed_keys(embed)
    tree = await to_thread(registry.get(fmt).loads, data)
    if keys:
        tree = await to_thread(embed_tree, tree, keys, _embed_root(root, base))
    return await to_thread(_finalize, tree, type=type, strict=strict, object_hook=object_hook, dec_hook=dec_hook)


async def adump(
    obj: Any,
    target: Target,
    *,
    format: FormatLike | None = None,
    registry: CodecRegistry = default_registry,
    default: Default | None = None,
    encoders: Encoders | None = None,
) -> None:
    """Async variant of `dump`."""
    target = Path(target) if isinstance(target, str) else target
    data = await adumps(
        obj, format=_target_format(target, format), registry=registry, default=default, encoders=encoders
    )
    if isinstance(target, Path):
        await awrite_bytes(target, data)
    else:
        await to_thread(target.write, data)


def _resolve(source: Source, format: FormatLike | None, _op: str) -> tuple[Format, bytes, Path | None]:
    match source:
        case Path():
            return _path_format(source, format), source.read_bytes(), source.parent
        case bytes():
            return _require_or_sniff(format, source), source, None
        case str():
            data = source.encode("utf-8")
            return _require_or_sniff(format, data), data, None
        case _:
            msg = f"unsupported source type {type(source).__name__!r}"
            raise FormatError(msg)


def _require_or_sniff(format: FormatLike | None, data: bytes) -> Format:
    if format is not None:
        return coerce_format(format)
    sniffed = sniff_format(data)
    if sniffed is None:
        msg = f"cannot infer format from content — pass format= ({' · '.join(Format)})"
        raise FormatError(msg)
    return sniffed


def _decode_sniffed(registry: CodecRegistry, fmt: Format, data: bytes, *, sniffed: bool) -> Any:
    try:
        return registry.get(fmt).loads(data)
    except LoadError as exc:
        if sniffed:
            msg = f"{exc} — the format was sniffed from content; pass format= explicitly if this is not JSON"
            raise LoadError(msg) from exc
        raise


def _resolve_file(target: Target, format: FormatLike | None) -> tuple[Format, bytes, Path | None]:
    if isinstance(target, str):
        target = Path(target)
    if isinstance(target, Path):
        return _path_format(target, format), target.read_bytes(), target.parent
    return _require_format(format, "file handle"), target.read(), None


def _finalize(
    obj: Any,
    *,
    type: builtins.type[Any] | None,
    strict: bool,
    object_hook: ObjectHook | None,
    dec_hook: DecHook | None,
) -> Any:
    if object_hook is not None:
        obj = _apply_object_hook(obj, object_hook)
    match type, dec_hook:
        case None, None:
            return obj
        case None, _:
            msg = "dec_hook requires a type= schema to validate against"
            raise FormatError(msg)
        case _ if _uses_pydantic(type):
            return _pydantic_validate(obj, type, strict=strict)
        case _:
            try:
                return msgspec.convert(obj, type, strict=strict, dec_hook=dec_hook)
            except msgspec.ValidationError as exc:
                msg = f"schema validation failed: {exc}"
                raise LoadError(msg) from exc


def _apply_object_hook(node: Any, hook: ObjectHook) -> Any:
    match node:
        case dict():
            return hook({key: _apply_object_hook(value, hook) for key, value in node.items()})
        case list():
            return [_apply_object_hook(value, hook) for value in node]
        case _:
            return node


def _uses_pydantic(type_: Any) -> bool:
    if hasattr(type_, "__pydantic_validator__"):
        return True
    return any(_uses_pydantic(arg) for arg in get_args(type_))


def _pydantic_validate(obj: Any, type_: Any, *, strict: bool) -> Any:
    from pydantic import ValidationError  # noqa: PLC0415 — optional peer dependency, lazy by design

    try:
        return _adapter(type_).validate_python(obj, strict=strict)
    except ValidationError as exc:
        msg = f"schema validation failed: {exc}"
        raise LoadError(msg) from exc


@cache
def _adapter(type_: Any) -> Any:
    from pydantic import TypeAdapter  # noqa: PLC0415 — optional peer dependency, lazy by design

    return TypeAdapter(type_)


def _path_format(path: Path, format: FormatLike | None) -> Format:
    if format is not None:
        return coerce_format(format)
    if (detected := detect_format(path)) is None:
        msg = f"cannot detect format from path {path.name!r}"
        raise FormatError(msg)
    return detected


def _target_format(target: Target, format: FormatLike | None) -> Format:
    if isinstance(target, (Path, str)):
        return _path_format(Path(target), format)
    return _require_format(format, "file handle")


def _require_format(format: FormatLike | None, source_kind: str) -> Format:
    if format is None:
        msg = f"format must be specified for {source_kind} source"
        raise FormatError(msg)
    return coerce_format(format)
