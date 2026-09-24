"""Backend-agnostic codec contract.

A `Codec` is the atomic unit of e-serde: one format, two operations (`loads`, `dumps`).
Every backend — msgspec (C) or the native Rust extension — satisfies this same interface,
which makes them interchangeable via the registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path

    from eserde.infra.formats import Format


@runtime_checkable
class Codec(Protocol):
    """Bidirectional codec for a single `Format`. Operates on raw bytes."""

    format: ClassVar[Format]

    def loads(self, data: bytes) -> Any:
        """Decode `data` into native Python objects."""
        ...

    def dumps(self, obj: Any) -> bytes:
        """Encode `obj` to bytes. `obj` is a JSON-compatible primitive tree."""
        ...


@runtime_checkable
class StreamingCodec(Protocol):
    """Codec that reads and writes one record at a time, never materializing the document.

    Capability, not obligation: `iloads`/`idumps` accept exactly the codecs that satisfy
    this protocol, and `STANDARDS` declares which formats claim it — a codec swap must
    keep the claim and the protocol in lockstep (checked by the contract test).
    """

    def iterloads(self, data: bytes) -> Iterator[Any]:
        """Yield decoded records from an in-memory document."""
        ...

    def iterload_path(self, path: Path) -> Iterator[Any]:
        """Yield decoded records straight from a file, without reading it whole."""
        ...

    def iterdumps(self, obj: Iterable[Any]) -> Iterator[bytes]:
        """Yield encoded chunks, one per record; concatenating them is the document."""
        ...
