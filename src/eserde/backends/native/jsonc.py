"""JSONC codec — `jsonc-parser` (Deno) via the native extension.

Accepts comments, trailing commas, unquoted object keys and single-quoted strings.
`dumps` emits strict JSON: comments are not preserved on round-trip.
"""

from __future__ import annotations

from typing import ClassVar

from eserde import _native
from eserde.backends.base import NativeCodec
from eserde.infra.formats import Format


class NativeJsoncCodec(NativeCodec):
    """JSONC loader backed by the Deno `jsonc-parser` Rust crate."""

    format: ClassVar[Format] = Format.JSONC
    backend: ClassVar = _native.jsonc
