"""TOML codec backed by `rtoml` (Rust + Cargo team's `toml` crate, PyO3 binding)."""

from __future__ import annotations

from typing import Any, ClassVar

import rtoml

from e_loader.infra.errors import DumpError, LoadError
from e_loader.logic.formats import Format


class RtomlCodec:
    """rtoml-backed TOML codec. Wraps UTF-8 to keep the bytes interface uniform."""

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