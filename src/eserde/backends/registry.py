"""Codec registry — one active `Codec` per `Format`, plus the default wiring.

The registry is the swap point between engines: `loads("x", format=Format.YAML)` is
oblivious to whether YAML resolves to the native Rust codec or a msgspec one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from eserde.backends.msgspec.json import MsgspecJsonCodec
from eserde.backends.native.csv import NativeCsvCodec, NativeTsvCodec
from eserde.backends.native.ini import NativeIniCodec
from eserde.backends.native.jsonc import NativeJsoncCodec
from eserde.backends.native.toml import NativeTomlCodec
from eserde.backends.native.yaml import NativeYamlCodec
from eserde.infra.errors import CodecError

if TYPE_CHECKING:
    from eserde.infra.formats import Format
    from eserde.infra.protocols import Codec


class CodecRegistry:
    """Mapping of `Format` to active `Codec`. Mutable, supports runtime replacement."""

    __slots__ = ("_codecs",)

    def __init__(self) -> None:
        self._codecs: dict[Format, Codec] = {}

    def register(self, codec: Codec, *, format: Format | None = None, override: bool = False) -> None:
        """Bind `codec` to a format. Defaults to `codec.format`; raises if already bound unless `override`."""
        fmt = format or codec.format
        if not override and fmt in self._codecs:
            msg = f"codec for {fmt.value!r} already registered; pass override=True to replace"
            raise CodecError(msg)
        self._codecs[fmt] = codec

    def replace(self, format: Format, codec: Codec) -> Codec:
        """Swap the codec for `format` and return the previous one. Raises if none was registered."""
        if (previous := self._codecs.get(format)) is None:
            msg = f"no codec registered for {format.value!r}"
            raise CodecError(msg)
        self._codecs[format] = codec
        return previous

    def get(self, format: Format) -> Codec:
        """Retrieve the active codec for `format`. Raises if unregistered."""
        if (codec := self._codecs.get(format)) is None:
            msg = f"no codec registered for {format.value!r}"
            raise CodecError(msg)
        return codec

    def has(self, format: Format) -> bool:
        """Whether `format` has an active codec."""
        return format in self._codecs

    def formats(self) -> frozenset[Format]:
        """Snapshot of formats with active codecs."""
        return frozenset(self._codecs)


_DEFAULT_CODECS: tuple[Codec, ...] = (
    MsgspecJsonCodec(),
    NativeJsoncCodec(),
    NativeYamlCodec(),
    NativeTomlCodec(),
    NativeIniCodec(),
    NativeCsvCodec(),
    NativeTsvCodec(),
)


def build_default_registry() -> CodecRegistry:
    """Fresh registry wired to the default backends: msgspec (C) for JSON, native Rust for the rest."""
    registry = CodecRegistry()
    for codec in _DEFAULT_CODECS:
        registry.register(codec)
    return registry


default_registry = build_default_registry()
