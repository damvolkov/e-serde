"""Backend-agnostic codec contract.

A `Codec` is the atomic unit of e-serde: one format, two operations (`loads`, `dumps`).
Every backend — msgspec (C) or the native Rust extension — satisfies this same interface,
which makes them interchangeable via the registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Protocol, runtime_checkable

if TYPE_CHECKING:
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
