"""JSONC codec — `jsonc-parser` (Deno) via the native extension.

Accepts comments, trailing commas, unquoted object keys and single-quoted strings.
`dumps` emits strict JSON: comments are not preserved on round-trip.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from eserde import _native
from eserde.backends.base import NativeCodec
from eserde.infra.formats import Format

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

if TYPE_CHECKING:
    from pathlib import Path


class NativeJsoncCodec(NativeCodec):
    """JSONC loader backed by the Deno `jsonc-parser` Rust crate."""

    format: ClassVar[Format] = Format.JSONC
    backend: ClassVar = _native.jsonc

    def iterloads(self, data: bytes) -> Iterator[Any]:
        return (self.loads(line) for line in data.splitlines() if line.strip())

    def iterload_path(self, path: Path) -> Iterator[Any]:
        with path.open("rb") as handle:
            yield from (self.loads(line) for line in handle if line.strip())

    def iterdumps(self, obj: Iterable[Any]) -> Iterator[bytes]:
        for record in obj:
            yield self.dumps(record) + b"\n"
