"""Public synchronous and asynchronous loader/encoder API.

The facade resolves a `(Format, bytes)` pair from any supported `Source`, then delegates
to the active codec in the registry. Backend choice — external Rust wheel or native Rust
binding — is opaque at this layer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from e_loader.infra.errors import FormatError
from e_loader.logic.formats import Format, detect_format
from e_loader.infra.io import aread_bytes
from e_loader.logic.registry import CodecRegistry, default_registry

type Source = bytes | str | Path


def loads(source: Source, *, format: Format | None = None, registry: CodecRegistry = default_registry) -> Any:
    """Decode `source` into native Python objects. Auto-detects `format` from `Path` extension."""
    fmt, data = _resolve_sync(source, format)
    return registry.get(fmt).loads(data)


def dumps(obj: Any, *, format: Format = Format.JSON, registry: CodecRegistry = default_registry) -> bytes:
    """Encode `obj` to bytes in the requested `format`."""
    return registry.get(format).dumps(obj)


async def aloads(source: Source, *, format: Format | None = None, registry: CodecRegistry = default_registry) -> Any:
    """Async variant of `loads`. Reads `Path` sources via aiofiles."""
    fmt, data = await _resolve_async(source, format)
    return registry.get(fmt).loads(data)


async def adumps(obj: Any, *, format: Format = Format.JSON, registry: CodecRegistry = default_registry) -> bytes:
    """Async variant of `dumps`. Returns bytes; provided for API symmetry with `aloads`."""
    return registry.get(format).dumps(obj)


def _resolve_sync(source: Source, format: Format | None) -> tuple[Format, bytes]:
    match source:
        case Path():
            return _format_from_path(source, format), source.read_bytes()
        case bytes():
            return _require_format(format, "bytes"), source
        case str():
            return _require_format(format, "str"), source.encode("utf-8")


async def _resolve_async(source: Source, format: Format | None) -> tuple[Format, bytes]:
    match source:
        case Path():
            return _format_from_path(source, format), await aread_bytes(source)
        case bytes():
            return _require_format(format, "bytes"), source
        case str():
            return _require_format(format, "str"), source.encode("utf-8")


def _format_from_path(path: Path, format: Format | None) -> Format:
    if format is not None:
        return format
    if (detected := detect_format(path)) is None:
        raise FormatError(f"cannot detect format from path {path.name!r}")
    return detected


def _require_format(format: Format | None, source_kind: str) -> Format:
    if format is None:
        raise FormatError(f"format must be specified for {source_kind} source")
    return format