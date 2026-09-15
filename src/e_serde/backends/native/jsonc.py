"""JSONC codec — `jsonc-parser` (Deno) via the native extension.

Accepts comments, trailing commas, unquoted object keys and single-quoted strings.
`dumps` emits strict JSON: comments are not preserved on round-trip.
"""

from __future__ import annotations

from typing import ClassVar

from e_serde import _native
from e_serde.backends.base import NativeCodec
from e_serde.infra.formats import Format


class NativeJsoncCodec(NativeCodec):
    """JSONC loader backed by the Deno `jsonc-parser` Rust crate."""

    format: ClassVar[Format] = Format.JSONC
    backend: ClassVar = _native.jsonc
