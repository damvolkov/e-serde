"""TOML codec — `toml` crate (rust-toml org, spec 1.1) via the native extension.

Datetime literals decode to ISO-8601 strings; `msgspec.convert` re-types them to
`datetime` when a schema asks for it. Null has no TOML representation and fails dumps.
"""

from __future__ import annotations

from typing import ClassVar

from e_serde import _native
from e_serde.backends.base import NativeCodec
from e_serde.infra.formats import Format


class NativeTomlCodec(NativeCodec):
    """TOML loader/dumper backed by the official `toml` Rust crate."""

    format: ClassVar[Format] = Format.TOML
    backend: ClassVar = _native.toml
