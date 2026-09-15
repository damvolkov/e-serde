"""TOML codec backed by stdlib `tomllib` (read) + `tomli-w` (write). Pure Python fallback."""

from __future__ import annotations

import tomllib
from typing import Any, ClassVar

import tomli_w

from e_loader.infra.errors import DumpError, LoadError
from e_loader.logic.formats import Format


class TomllibCodec:
    """Stdlib `tomllib` + `tomli-w`. Zero Rust dependency. Negligible perf cost for typical configs."""

    format: ClassVar[Format] = Format.TOML

    def loads(self, data: bytes) -> Any:
        try:
            return tomllib.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            raise LoadError(f"tomllib decode failed: {exc}") from exc

    def dumps(self, obj: Any) -> bytes:
        try:
            return tomli_w.dumps(obj).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise DumpError(f"tomli-w encode failed: {exc}") from exc