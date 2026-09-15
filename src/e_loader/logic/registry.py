"""Codec registry — one active `Codec` per `Format`.

The registry is the swap point between external Rust-backed wheels (orjson, rtoml) and
our own native Rust bindings (planned for YAML and INI in v0.2). Replacing a codec at
runtime is a one-liner, which keeps the facade `loads`/`dumps` oblivious to the backend.
"""

from __future__ import annotations

from e_loader.codecs.ini_stdlib import ConfigparserCodec
from e_loader.codecs.ini_native import NativeIniCodec
from e_loader.codecs.json_orjson import OrjsonCodec
from e_loader.codecs.toml_rtoml import RtomlCodec
from e_loader.codecs.toml_native import NativeTomlCodec
from e_loader.codecs.yaml_pyyaml import PyyamlCodec
from e_loader.codecs.yaml_native import NativeYamlCodec
from e_loader.errors import CodecError
from e_loader.logic.formats import Format
from e_loader.infra.protocols import Codec


class CodecRegistry:
    """Mapping of `Format` to active `Codec`. Mutable, supports runtime replacement."""

    __slots__ = ("_codecs",)

    def __init__(self) -> None:
        self._codecs: dict[Format, Codec] = {}

    def register(self, codec: Codec, *, format: Format | None = None, override: bool = False) -> None:
        """Bind `codec` to a format. Defaults to `codec.format`; raises if already bound unless `override`."""
        fmt = format or codec.format
        if not override and fmt in self._codecs:
            raise CodecError(f"codec for {fmt.value!r} already registered; pass override=True to replace")
        self._codecs[fmt] = codec

    def replace(self, format: Format, codec: Codec) -> Codec:
        """Swap the codec for `format` and return the previous one. Raises if none was registered."""
        if (previous := self._codecs.get(format)) is None:
            raise CodecError(f"no codec registered for {format.value!r}")
        self._codecs[format] = codec
        return previous

    def get(self, format: Format) -> Codec:
        """Retrieve the active codec for `format`. Raises if unregistered."""
        if (codec := self._codecs.get(format)) is None:
            raise CodecError(f"no codec registered for {format.value!r}")
        return codec

    def has(self, format: Format) -> bool:
        """Whether `format` has an active codec."""
        return format in self._codecs

    def formats(self) -> frozenset[Format]:
        """Snapshot of formats with active codecs."""
        return frozenset(self._codecs)


def _build_default_registry() -> CodecRegistry:
    registry = CodecRegistry()
    registry.register(OrjsonCodec())
    registry.register(RtomlCodec())
    registry.register(PyyamlCodec())
    registry.register(ConfigparserCodec())
    # Native codecs are optional and can be swapped in later
    return registry


default_registry = _build_default_registry()