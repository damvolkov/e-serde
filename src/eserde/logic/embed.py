"""Content embedding — the document indexes, companion files carry the content.

`embed` walks a decoded tree and inlines every string found under a declared key
(`source` by convention). The string names a file, resolved against the directory of
the document that references it and confined inside the root: a `.md` file is inlined
as text, a structured file (`.json`, `.yaml`, `.toml`, …) is decoded through the
registry's codec and embedded as a tree, recursively. Cycles are refused. The result is
a copy; a failing reference raises before any tree is returned, so partial embedding
never leaks.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

from eserde.infra.errors import LoadError
from eserde.infra.formats import Format, detect_format

if TYPE_CHECKING:
    from collections.abc import Sequence

    from eserde.backends.registry import CodecRegistry

MAX_EMBED_BYTES = 16 * 1024 * 1024
DEFAULT_EMBED_KEYS: tuple[str, ...] = ("source",)
_MARKDOWN = "markdown"


class _Scope(NamedTuple):
    keys: frozenset[str]
    root: Path
    base: Path
    registry: CodecRegistry
    chain: frozenset[Path]


def embed(obj: Any, keys: Sequence[str], root: Path, registry: CodecRegistry) -> Any:
    """Return a copy of `obj` with every reference under `keys` replaced by the file's content."""
    anchor = root.resolve()
    return _walk(obj, _Scope(frozenset(keys), anchor, anchor, registry, frozenset()))


def _walk(node: Any, scope: _Scope) -> Any:
    match node:
        case dict():
            return {
                key: (
                    _inline(value, node, scope) if key in scope.keys and isinstance(value, str) else _walk(value, scope)
                )
                for key, value in node.items()
            }
        case list():
            return [_walk(value, scope) for value in node]
        case _:
            return node


def _inline(reference: str, parent: dict[str, Any], scope: _Scope) -> Any:
    path = _confine(Path(reference), scope)
    kind = _kind(path, reference)
    if (declared := parent.get("format")) is not None and declared != kind:
        msg = f"reference {reference!r} is {kind}, but its sibling format declares {declared!r}"
        raise LoadError(msg)
    _check(path, reference, scope)
    match kind:
        case Format() as fmt:
            return _nested(fmt, path, reference, scope)
        case _:
            return _text(path, reference)


def _kind(path: Path, reference: str) -> Format | str:
    """`markdown` for `.md`, the detected `Format` for structured files; anything else is refused."""
    match path.suffix.lower(), detect_format(path):
        case ".md", _:
            return _MARKDOWN
        case _, Format() as fmt:
            return fmt
        case _:
            msg = f"cannot embed {reference!r}: expected .md or a structured format ({' · '.join(Format)})"
            raise LoadError(msg)


def _check(path: Path, reference: str, scope: _Scope) -> None:
    if not path.is_file():
        msg = f"embedded file not found: {reference!r} (base {scope.base})"
        raise LoadError(msg)
    if path.stat().st_size > MAX_EMBED_BYTES:
        msg = f"embedded file too large (> {MAX_EMBED_BYTES} bytes): {reference!r}"
        raise LoadError(msg)


def _text(path: Path, reference: str) -> str:
    """Markdown reads in text mode: universal newlines, so CRLF files inline as `\\n` everywhere."""
    try:
        return path.read_text("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        msg = f"cannot embed {reference!r}: {exc}"
        raise LoadError(msg) from exc


def _nested(fmt: Format, path: Path, reference: str, scope: _Scope) -> Any:
    """Decode through the registry's codec, then embed the sub-tree relative to its own directory."""
    if path in scope.chain:
        msg = f"embedding cycle: {reference!r} is already being embedded"
        raise LoadError(msg)
    try:
        tree = scope.registry.get(fmt).loads(path.read_bytes())
    except (OSError, LoadError) as exc:
        msg = f"cannot embed {reference!r}: {exc}"
        raise LoadError(msg) from exc
    return _walk(tree, scope._replace(base=path.parent, chain=scope.chain | {path}))


def _confine(path: Path, scope: _Scope) -> Path:
    resolved = (scope.base / path if not path.is_absolute() else path).resolve()
    if scope.root not in resolved.parents and resolved != scope.root:
        msg = f"embedded path escapes the document root: {path} (root {scope.root})"
        raise LoadError(msg)
    return resolved
