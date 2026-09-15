"""INI codec — `rust-ini` via the native extension.

Deliberately stricter than `configparser`: no interpolation, no DEFAULT inheritance,
keys outside a section are rejected. Multi-line values round-trip through
`\n`/`\\` escapes (rust-ini dialect). Values always decode to `str`;
type them with `msgspec` + `type=`.
"""

from __future__ import annotations

from typing import Any, ClassVar

from e_serde import _native
from e_serde.backends.base import NativeCodec
from e_serde.infra.errors import DumpError
from e_serde.infra.formats import Format


class NativeIniCodec(NativeCodec):
    """INI loader/dumper backed by the `rust-ini` crate."""

    format: ClassVar[Format] = Format.INI
    backend: ClassVar = _native.ini

    def dumps(self, obj: Any) -> bytes:
        if not isinstance(obj, dict):
            msg = f"INI dumps expects a mapping of sections, got {type(obj).__name__}"
            raise DumpError(msg)
        return super().dumps(obj)
