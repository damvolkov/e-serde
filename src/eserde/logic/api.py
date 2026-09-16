"""Public facade — the whole library is six functions with json-module semantics.

`loads`/`dumps` operate on `bytes | str | Path`; `load`/`dump` operate on files
(`Path` or open binary handles); `*`-prefixed async twins offload both I/O and GIL-free
native decoding to worker threads. Passing `type=` decodes the plain tree through
`msgspec.convert` into any Struct/dataclass/TypedDict — frozen models are the point.
"""

from __future__ import annotations

from asyncio import to_thread
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO

import msgspec

from eserde.backends.registry import CodecRegistry, default_registry
from eserde.infra.errors import FormatError, LoadError
from eserde.infra.formats import Format, detect_format
from eserde.infra.io import aread_bytes, aread_handle, awrite_bytes
from eserde.logic.encoder import encode

if TYPE_CHECKING:
    import builtins

type Source = bytes | str | Path
type Target = Path | BinaryIO


def loads(
    source: Source,
    *,
    format: Format | None = None,
    type: builtins.type[Any] | None = None,
    strict: bool = True,
    registry: CodecRegistry = default_registry,
) -> Any:
    """Decode `source` into native Python objects, or into `type` when a schema is given.

    Auto-detects `format` from `Path` extensions; `bytes`/`str` sources require it.
    """
    fmt, data = _resolve(source, format, "loads")
    return _finalize(registry.get(fmt).loads(data), type=type, strict=strict)


def dumps(
    obj: Any,
    *,
    format: Format = Format.JSON,
    registry: CodecRegistry = default_registry,
) -> bytes:
    """Encode `obj` to bytes in `format`, normalizing through the Jsonable encoder first."""
    return registry.get(format).dumps(encode(obj))


def load(
    target: Target,
    *,
    format: Format | None = None,
    type: builtins.type[Any] | None = None,
    strict: bool = True,
    registry: CodecRegistry = default_registry,
) -> Any:
    """Decode a file (`Path` or open binary handle). Same contract as `json.load`."""
    fmt, data = _resolve_file(target, format)
    return _finalize(registry.get(fmt).loads(data), type=type, strict=strict)


def dump(
    obj: Any,
    target: Target,
    *,
    format: Format | None = None,
    registry: CodecRegistry = default_registry,
) -> None:
    """Encode `obj` straight into a file. Format inferred from `Path`; handles require it."""
    data = dumps(obj, format=_target_format(target, format), registry=registry)
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
) -> Any:
    """Async variant of `loads`. Path reads and native parsing off the event loop."""
    if isinstance(source, Path):
        data, fmt = await aread_bytes(source), _path_format(source, format)
    else:
        fmt, data = _resolve(source, format, "loads")
    return await to_thread(_finalize, await to_thread(registry.get(fmt).loads, data), type=type, strict=strict)


async def adumps(
    obj: Any,
    *,
    format: Format = Format.JSON,
    registry: CodecRegistry = default_registry,
) -> bytes:
    """Async variant of `dumps`."""
    plain = await to_thread(encode, obj)
    return await to_thread(registry.get(format).dumps, plain)


async def aload(
    target: Target,
    *,
    format: Format | None = None,
    type: builtins.type[Any] | None = None,
    strict: bool = True,
    registry: CodecRegistry = default_registry,
) -> Any:
    """Async variant of `load`."""
    fmt, data = (
        (_path_format(target, format), await aread_bytes(target))
        if isinstance(target, Path)
        else (_require_format(format, "file handle"), await aread_handle(target))
    )
    decoded = await to_thread(registry.get(fmt).loads, data)
    return await to_thread(_finalize, decoded, type=type, strict=strict)


async def adump(
    obj: Any,
    target: Target,
    *,
    format: Format | None = None,
    registry: CodecRegistry = default_registry,
) -> None:
    """Async variant of `dump`."""
    data = await adumps(obj, format=_target_format(target, format), registry=registry)
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


def _finalize(obj: Any, *, type: builtins.type[Any] | None, strict: bool) -> Any:
    if type is None:
        return obj
    try:
        return msgspec.convert(obj, type, strict=strict)
    except msgspec.ValidationError as exc:
        msg = f"schema validation failed: {exc}"
        raise LoadError(msg) from exc


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
