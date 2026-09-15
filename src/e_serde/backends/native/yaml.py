"""YAML codec — saphyr (YAML 1.2 core schema) via the native extension.

Anchors/aliases are expanded by the parser; multi-document streams are rejected.
"""

from __future__ import annotations

from typing import ClassVar

from e_serde import _native
from e_serde.backends.base import NativeCodec
from e_serde.infra.formats import Format


class NativeYamlCodec(NativeCodec):
    """YAML 1.2 loader/dumper backed by the `saphyr` Rust crate."""

    format: ClassVar[Format] = Format.YAML
    backend: ClassVar = _native.yaml
