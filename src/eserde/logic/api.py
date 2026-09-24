"""Public facade — the whole library is twelve functions with json-module semantics.

`loads`/`dumps` operate on `bytes | str | Path`; `load`/`dump` operate on files
(`Path` or open binary handles); `*`-prefixed async twins offload both I/O and GIL-free
native decoding to worker threads. Passing `type=` decodes the plain tree through
`msgspec.convert` into any Struct/dataclass/TypedDict — frozen models are the point.
"""

from __future__ import annotations

from asyncio import to_thread
from collections.abc import AsyncIterable, Callable, Sequence
from functools import cache
from itertools import islice
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, NamedTuple, get_args

import msgspec

from eserde.backends.registry import CodecRegistry, default_registry
from eserde.infra.errors import FormatError, LoadError
from eserde.infra.formats import Format, coerce_format, detect_format, sniff_format
from eserde.infra.io import aread_bytes, aread_handle, awrite_bytes
from eserde.infra.protocols import StreamingCodec
from eserde.logic.embed import DEFAULT_EMBED_KEYS
from eserde.logic.embed import embed as embed_tree
from eserde.logic.encoder import Default, Encoders, encode

if TYPE_CHECKING:
    import builtins
    from collections.abc import AsyncIterator, Iterable, Iterator

type Source = bytes | str | Path
type Target = str | Path | BinaryIO
type FormatLike = Format | str
type ObjectHook = Callable[[dict[str, Any]], Any]
type DecHook = Callable[[Any, Any], Any]
type Embed = Sequence[str] | bool


_STREAM_BATCH = 1024


def iloads(
    source: Source,
    *,
    format: FormatLike | None = None,
    registry: CodecRegistry = default_registry,
) -> Iterator[Any]:
    """Iterate records from a streamed document: CSV/TSV rows, NDJSON lines.

    One record materialized at a time; `Path` sources are opened by the reader,
    never read whole. Type claims follow the streaming contract of each format
    (CSV types cells per-value, not per-column; see `docs/formats`).
    """
    return _plan_stream(source, format, registry).records()


def idumps(
    obj: Iterable[Any],
    *,
    format: FormatLike = Format.JSON,
    registry: CodecRegistry = default_registry,
) -> Iterator[bytes]:
    """Iterate encoded chunks, one record at a time; concatenating them is the document."""
    return _stream_codec(coerce_format(format), registry).iterdumps(obj)


def ailoads(
    source: Source,
    *,
    format: FormatLike | None = None,
    registry: CodecRegistry = default_registry,
) -> AsyncIterator[Any]:
    """Async variant of `iloads`: batches drained off the event loop, eager validation."""
    return _drain_reads(_plan_stream(source, format, registry))


def aidumps(
    obj: Iterable[Any] | AsyncIterable[Any],
    *,
    format: FormatLike = Format.JSON,
    registry: CodecRegistry = default_registry,
) -> AsyncIterator[bytes]:
    """Async variant of `idumps`; `obj` may be a sync or async iterable."""
    return _drain_writes(_stream_codec(coerce_format(format), registry), obj)


class _StreamPlan(NamedTuple):
    codec: StreamingCodec
    data: bytes | None
    path: Path | None

    def records(self) -> Iterator[Any]:
        match self.path, self.data:
            case Path() as path, _:
                return self.codec.iterload_path(path)
            case _, bytes() as data:
                return self.codec.iterloads(data)
            case _:
                msg = "stream plan carries neither data nor path"
                raise FormatError(msg)


def _plan_stream(source: Source, format: FormatLike | None, registry: CodecRegistry) -> _StreamPlan:
    match source:
        case Path():
            return _StreamPlan(_stream_codec(_path_format(source, format), registry), None, source)
        case bytes():
            return _StreamPlan(_stream_codec(_require_or_sniff(format, source), registry), source, None)
        case str():
            data = source.encode("utf-8")
            return _StreamPlan(_stream_codec(_require_or_sniff(format, data), registry), data, None)
        case _:
            msg = f"unsupported source type {type(source).__name__!r}"
            raise FormatError(msg)


def _stream_codec(fmt: Format, registry: CodecRegistry) -> StreamingCodec:
    match registry.get(fmt):
        case StreamingCodec() as codec:
            return codec
        case _:
            streamable = " · ".join(
                sorted(f.value for f in registry.formats() if isinstance(registry.get(f), StreamingCodec))
            )
            msg = f"{fmt.value} does not support streaming — iloads/idumps speak {streamable}; materialize whole documents with loads/dumps"
            raise FormatError(msg)


def _read_batch(iterator: Iterator[Any]) -> list[Any]:
    return list(islice(iterator, _STREAM_BATCH))


def _encode_batch(codec: StreamingCodec, records: list[Any]) -> list[bytes]:
    return list(codec.iterdumps(records))


async def _drain_reads(plan: _StreamPlan) -> AsyncIterator[Any]:
    iterator = plan.records()
    while batch := await to_thread(_read_batch, iterator):
        for record in batch:
            yield record


async def _drain_writes(codec: StreamingCodec, obj: Iterable[Any] | AsyncIterable[Any]) -> AsyncIterator[bytes]:
    match obj:
        case AsyncIterable():
            async for record in obj:
                for chunk in await to_thread(_encode_batch, codec, [record]):
                    yield chunk
        case _:
            iterator = codec.iterdumps(obj)
            while batch := await to_thread(_read_batch, iterator):
                for chunk in batch:
                    yield chunk


def _embed_keys(embed: Embed) -> tuple[str, ...]:
    """`True` → default keys, `False` → none, a sequence → the declared keys."""
    match embed:
        case True:
            return DEFAULT_EMBED_KEYS
        case False:
            return ()
        case _:
            return tuple(embed)


def _embed_root(root: str | Path | None, base: Path | None) -> Path:
    """`root=` wins; otherwise anchor on the source's directory; otherwise refuse loudly."""
    match root, base:
        case str() | Path() as anchor, _:
            return Path(anchor)
        case None, Path():
            return base
        case _:
            msg = "embed requires root= when the source carries no path to anchor relative references"
            raise FormatError(msg)


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
    fmt, data, base = _resolve(source, format)
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
    data = dumps(obj, format=_target_format(target, format), registry=registry, default=default, encoders=encoders)
    match target:
        case str() | Path() as name:
            Path(name).write_bytes(data)
        case _:
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
    match source:
        case Path():
            fmt, data, base = _path_format(source, format), await aread_bytes(source), source.parent
        case _:
            fmt, data, base = _resolve(source, format)
    keys = _embed_keys(embed)
    tree = await to_thread(
        _decode_sniffed, registry, fmt, data, sniffed=format is None and not isinstance(source, Path)
    )
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
    match target:
        case str() | Path() as name:
            path = Path(name)
            fmt, data, base = _path_format(path, format), await aread_bytes(path), path.parent
        case _:
            fmt, data, base = _require_format(format, "file handle"), await aread_handle(target), None
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
    data = await adumps(
        obj, format=_target_format(target, format), registry=registry, default=default, encoders=encoders
    )
    match target:
        case str() | Path() as name:
            await awrite_bytes(Path(name), data)
        case _:
            await to_thread(target.write, data)


def _resolve(source: Source, format: FormatLike | None) -> tuple[Format, bytes, Path | None]:
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
    match target:
        case str() | Path() as name:
            path = Path(name)
            return _path_format(path, format), path.read_bytes(), path.parent
        case _:
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
    """Whether `type_` or any generic arg is a pydantic model; otherwise msgspec converts."""
    return hasattr(type_, "__pydantic_validator__") or any(_uses_pydantic(arg) for arg in get_args(type_))


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
    match target:
        case str() | Path() as name:
            return _path_format(Path(name), format)
        case _:
            return _require_format(format, "file handle")


def _require_format(format: FormatLike | None, source_kind: str) -> Format:
    if format is None:
        msg = f"format must be specified for {source_kind} source"
        raise FormatError(msg)
    return coerce_format(format)
