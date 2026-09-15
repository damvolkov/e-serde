"""Native TOML codec backed by Rust + toml crate.

This is a placeholder for the native Rust TOML codec that will be implemented
in crates/e-loader-toml. For now it uses the rtoml implementation as a fallback.
"""

from __future__ import annotations

from typing import Any, ClassVar

import rtoml

from e_loader.errors import DumpError, LoadError
from e_loader.logic.formats import Format


class NativeTomlCodec:
    """Native Rust-backed TOML codec (placeholder - will be implemented in v0.2)."""

    format: ClassVar[Format] = Format.TOML

    def loads(self, data: bytes) -> Any:
        try:
            return rtoml.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, rtoml.TomlParsingError) as exc:
            raise LoadError(f"rtoml decode failed: {exc}") from exc

    def dumps(self, obj: Any) -> bytes:
        try:
            return rtoml.dumps(obj).encode("utf-8")
        except (TypeError, rtoml.TomlSerializationError) as exc:
            raise DumpError(f"rtoml encode failed: {exc}") from exc