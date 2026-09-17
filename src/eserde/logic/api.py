"""Public facade — the whole library is six functions with json-module semantics.

`loads`/`dumps` operate on `bytes | str | Path`; `load`/`dump` operate on files
(`Path` or open binary handles); `*`-prefixed async twins offload both I/O and GIL-free
native decoding to worker threads. Passing `type=` decodes the plain tree through
`msgspec.convert` into any Struct/dataclass/TypedDict — frozen models are the point.
"""

from __future__ import annotations

from asyncio import to_thread
from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, get_args

import msgspec

from eserde.backends.registry import CodecRegistry, default_registry
from eserde.infra.errors import FormatError, LoadError
from eserde.infra.formats import Format, detect_format
from eserde.infra.io import aread_bytes, aread_handle, awrite_bytes
from eserde.logic.encoder import Default, Encoders, encode

if TYPE_CHECKING:
    import builtins

type Source = bytes | str | Path
type Target = Path | BinaryIO
type ObjectHook = Callable[[dict[str, Any]], Any]
type DecHook = Callable[[Any, Any], Any]


def loads(
    source: Source,
    *,
    format: Format | None = None,
    type: builtins.type[Any] | None = None,
    strict: bool = True,
    registry: CodecRegistry = default_registry,
    object_hook: ObjectHook | None = None,
    dec_hook: DecHook | None = None,
) -> Any:
    """Decode `source` into native Python objects, or into `type` when a schema is given.

    Auto-detects `format` from `Path` extensions; `bytes`/`str` sources require it.
    `object_hook` post-processes every decoded mapping (json semantics); `dec_hook`
    teaches `type=` about custom fields (msgspec semantics).
    """
    fmt, data = _resolve(source, format, "loads")
    return _finalize(
        registry.get(fmt).loads(data), type=type, strict=strict, object_hook=object_hook, dec_hook=dec_hook
    )


def dumps(
    obj: Any,
    *,
    format: Format = Format.JSON,
    registry: CodecRegistry = default_registry,
    default: Default | None = None,
    encoders: Encoders | None = None,
) -> bytes:
    """Encode `obj` to bytes in `format`, normalizing through the Jsonable encoder first.

    `encoders`/`default` customize the normalization per call, json/orjson semantics.
    """
    return registry.get(format).dumps(encode(obj, default=default, encoders=encoders))


def load(
    target: Target,
    *,
    format: Format | None = None,
    type: builtins.type[Any] | None = None,
    strict: bool = True,
    registry: CodecRegistry = default_registry,
    object_hook: ObjectHook | None = None,
    dec_hook: DecHook | None = None,
) -> Any:
    """Decode a file (`Path` or open binary handle). Same contract as `json.load`."""
    fmt, data = _resolve_file(target, format)
    return _finalize(
        registry.get(fmt).loads(data), type=type, strict=strict, object_hook=object_hook, dec_hook=dec_hook
    )


def dump(
    obj: Any,
    target: Target,
    *,
    format: Format | None = None,
    registry: CodecRegistry = default_registry,
    default: Default | None = None,
    encoders: Encoders | None = None,
) -> None:
    """Encode `obj` straight into a file. Format inferred from `Path`; handles require it."""
    data = dumps(obj, format=_target_format(target, format), registry=registry, default=default, encoders=encoders)
    if isinstance(target, Path):
        target.write_bytes(data)
    else:
        target.write(data)


async def aloads(
    source: Source,
    *,
    format: Format | None = None,
    type: builtins.type[Any] | None = None,
    strict: bool = True,
    registry: CodecRegistry = default_registry,
    object_hook: ObjectHook | None = None,
    dec_hook: DecHook | None = None,
) -> Any:
    """Async variant of `loads`. Path reads and native parsing off the event loop."""
    if isinstance(source, Path):
        data, fmt = await aread_bytes(source), _path_format(source, format)
    else:
        fmt, data = _resolve(source, format, "loads")
    return await to_thread(
        _finalize,
        await to_thread(registry.get(fmt).loads, data),
        type=type,
        strict=strict,
        object_hook=object_hook,
        dec_hook=dec_hook,
    )


async def adumps(
    obj: Any,
    *,
    format: Format = Format.JSON,
    registry: CodecRegistry = default_registry,
    default: Default | None = None,
    encoders: Encoders | None = None,
) -> bytes:
    """Async variant of `dumps`."""
    plain = await to_thread(encode, obj, default=default, encoders=encoders)
    return await to_thread(registry.get(format).dumps, plain)


async def aload(
    target: Target,
    *,
    format: Format | None = None,
    type: builtins.type[Any] | None = None,
    strict: bool = True,
    registry: CodecRegistry = default_registry,
    object_hook: ObjectHook | None = None,
    dec_hook: DecHook | None = None,
) -> Any:
    """Async variant of `load`."""
    fmt, data = (
        (_path_format(target, format), await aread_bytes(target))
        if isinstance(target, Path)
        else (_require_format(format, "file handle"), await aread_handle(target))
    )
    decoded = await to_thread(registry.get(fmt).loads, data)
    return await to_thread(
        _finalize,
        decoded,
        type=type,
        strict=strict,
        object_hook=object_hook,
        dec_hook=dec_hook,
    )


async def adump(
    obj: Any,
    target: Target,
    *,
    format: Format | None = None,
    registry: CodecRegistry = default_registry,
    default: Default | None = None,
    encoders: Encoders | None = None,
) -> None:
    """Async variant of `dump`."""
    data = await adumps(
        obj, format=_target_format(target, format), registry=registry, default=default, encoders=encoders
    )
    if isinstance(target, Path):
        await awrite_bytes(target, data)
    else:
        await to_thread(target.write, data)


def _resolve(source: Source, format: Format | None, _op: str) -> tuple[Format, bytes]:
    match source:
        case Path():
            return _path_format(source, format), source.read_bytes()
        case bytes():
            return _require_format(format, "bytes"), source
        case str():
            return _require_format(format, "str"), source.encode("utf-8")
        case _:
            msg = f"unsupported source type {type(source).__name__!r}"
            raise FormatError(msg)


def _resolve_file(target: Target, format: Format | None) -> tuple[Format, bytes]:
    if isinstance(target, Path):
        return _path_format(target, format), target.read_bytes()
    return _require_format(format, "file handle"), target.read()


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


def _path_format(path: Path, format: Format | None) -> Format:
    if format is not None:
        return format
    if (detected := detect_format(path)) is None:
        msg = f"cannot detect format from path {path.name!r}"
        raise FormatError(msg)
    return detected


def _target_format(target: Target, format: Format | None) -> Format:
    if isinstance(target, Path):
        return _path_format(target, format)
    return _require_format(format, "file handle")


def _require_format(format: Format | None, source_kind: str) -> Format:
    if format is None:
        msg = f"format must be specified for {source_kind} source"
        raise FormatError(msg)
    return format
