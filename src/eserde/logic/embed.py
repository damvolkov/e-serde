"""Content embedding — the document indexes, the Markdown file carries the prose.

`embed` walks a decoded tree and inlines every string found under a declared key
(`source` by convention): the string names a plain `.md` file, resolved against a root
directory and confined inside it. The result is a copy; a failing reference raises
before any tree is returned, so partial embedding never leaks.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from eserde.infra.errors import LoadError

if TYPE_CHECKING:
    from collections.abc import Sequence

MAX_EMBED_BYTES = 16 * 1024 * 1024
DEFAULT_EMBED_KEYS: tuple[str, ...] = ("source",)


def embed(obj: Any, keys: Sequence[str], root: Path) -> Any:
    """Return a copy of `obj` with every reference under `keys` replaced by the file's text."""
    return _walk(obj, frozenset(keys), root.resolve())


def _walk(node: Any, keys: frozenset[str], root: Path) -> Any:
    match node:
        case dict():
            return {
                key: (
                    _inline(value, root, node) if key in keys and isinstance(value, str) else _walk(value, keys, root)
                )
                for key, value in node.items()
            }
        case list():
            return [_walk(value, keys, root) for value in node]
        case _:
            return node


def _inline(reference: str, root: Path, parent: dict[str, Any]) -> str:
    if (declared := parent.get("format")) is not None and declared != "markdown":
        msg = f"embedded references must be markdown, not {declared!r} ({reference!r})"
        raise LoadError(msg)
    path = _confine(Path(reference), root)
    if path.suffix.lower() != ".md":
        msg = f"only plain .md files can be embedded, got {reference!r}"
        raise LoadError(msg)
    if not path.is_file():
        msg = f"embedded file not found: {reference!r} (root {root})"
        raise LoadError(msg)
    if path.stat().st_size > MAX_EMBED_BYTES:
        msg = f"embedded file too large (> {MAX_EMBED_BYTES} bytes): {reference!r}"
        raise LoadError(msg)
    try:
        return path.read_text("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        msg = f"cannot embed {reference!r}: {exc}"
        raise LoadError(msg) from exc


def _confine(path: Path, root: Path) -> Path:
    resolved = (root / path if not path.is_absolute() else path).resolve()
    if root not in resolved.parents and resolved != root:
        msg = f"embedded path escapes the document root: {path} (root {root})"
        raise LoadError(msg)
    return resolved
