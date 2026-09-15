"""Backend-agnostic codec contract.

A `Codec` is the atomic unit of e-loader: one format, two operations (`loads`, `dumps`).
Both external-wheel codecs (orjson, rtoml, PyYAML) and native-Rust codecs satisfy this
same interface, which makes them interchangeable via the registry.
"""

from __future__ import annotations

from typing import Any, ClassVar, Protocol, runtime_checkable

from e_loader.logic.formats import Format


@runtime_checkable
class Codec(Protocol):
    """Bidirectional codec for a single `Format`. Operates on raw bytes."""

    format: ClassVar[Format]

    def loads(self, data: bytes) -> Any:
        """Decode `data` into native Python objects."""
        ...

    def dumps(self, obj: Any) -> bytes:
        """Encode `obj` to bytes."""
        ...