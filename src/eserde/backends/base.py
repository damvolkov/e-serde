"""Shared base for codecs over the native Rust extension.

`eserde._native` functions take `str` and dump to `str`; this base adapts them to the
bytes-in/bytes-out `Codec` contract and maps backend exceptions onto the e-serde hierarchy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from eserde.infra.errors import DumpError, LoadError

if TYPE_CHECKING:
    from types import ModuleType

    from eserde.infra.formats import Format


class NativeCodec:
    """Codec bound to one submodule of the native extension (`_native.yaml`, `_native.toml`, ...)."""

    format: ClassVar[Format]
    backend: ClassVar[ModuleType]

    def loads(self, data: bytes) -> Any:
        try:
            return self.backend.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            msg = f"{self.format.value} decode failed: {exc}"
            raise LoadError(msg) from exc

    def dumps(self, obj: Any) -> bytes:
        try:
            return self.backend.dumps(obj).encode("utf-8")
        except (TypeError, ValueError) as exc:
            msg = f"{self.format.value} encode failed: {exc}"
            raise DumpError(msg) from exc
