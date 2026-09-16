"""YAML codec — saphyr (YAML 1.2 core schema) via the native extension.

Anchors/aliases are expanded by the parser; multi-document streams are rejected.
"""

from __future__ import annotations

from typing import ClassVar

from eserde import _native
from eserde.backends.base import NativeCodec
from eserde.infra.formats import Format


class NativeYamlCodec(NativeCodec):
    """YAML 1.2 loader/dumper backed by the `saphyr` Rust crate."""

    format: ClassVar[Format] = Format.YAML
    backend: ClassVar = _native.yaml
