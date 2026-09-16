"""CodecRegistry behavior: register, get, replace, has, formats + default wiring."""

from __future__ import annotations

from typing import Any, ClassVar

import pytest

from eserde.backends.msgspec.json import MsgspecJsonCodec
from eserde.backends.native.toml import NativeTomlCodec
from eserde.backends.registry import CodecRegistry, build_default_registry, default_registry
from eserde.infra.errors import CodecError
from eserde.infra.formats import Format
from eserde.infra.protocols import Codec


class _StubJsonCodec:
    format: ClassVar[Format] = Format.JSON

    def loads(self, data: bytes) -> Any:
        return {"stub": True}

    def dumps(self, obj: Any) -> bytes:
        return b'{"stub":true}'


async def test_default_registry_covers_all_formats() -> None:
    assert default_registry.formats() == frozenset(Format)


async def test_default_backends_are_msgspec_json_and_native_rest() -> None:
    registry = build_default_registry()
    assert isinstance(registry.get(Format.JSON), MsgspecJsonCodec)
    assert isinstance(registry.get(Format.TOML), NativeTomlCodec)


async def test_register_then_get() -> None:
    registry = CodecRegistry()
    codec = MsgspecJsonCodec()
    registry.register(codec)
    assert registry.get(Format.JSON) is codec


async def test_register_duplicate_raises() -> None:
    registry = CodecRegistry()
    registry.register(MsgspecJsonCodec())
    with pytest.raises(CodecError, match="already registered"):
        registry.register(MsgspecJsonCodec())


async def test_register_override_replaces() -> None:
    registry = CodecRegistry()
    registry.register(MsgspecJsonCodec())
    new_codec = _StubJsonCodec()
    registry.register(new_codec, override=True)
    assert registry.get(Format.JSON) is new_codec


async def test_replace_returns_previous() -> None:
    registry = CodecRegistry()
    original = MsgspecJsonCodec()
    registry.register(original)
    new_codec = _StubJsonCodec()
    previous = registry.replace(Format.JSON, new_codec)
    assert previous is original
    assert registry.get(Format.JSON) is new_codec


async def test_replace_missing_raises() -> None:
    registry = CodecRegistry()
    with pytest.raises(CodecError, match="no codec registered"):
        registry.replace(Format.JSON, _StubJsonCodec())


async def test_get_missing_raises() -> None:
    registry = CodecRegistry()
    with pytest.raises(CodecError, match="no codec registered"):
        registry.get(Format.YAML)


async def test_has_reflects_registration() -> None:
    registry = CodecRegistry()
    assert not registry.has(Format.JSON)
    registry.register(MsgspecJsonCodec())
    assert registry.has(Format.JSON)


async def test_stub_codec_is_runtime_checkable() -> None:
    assert isinstance(_StubJsonCodec(), Codec)


async def test_register_explicit_format_overrides_codec_format() -> None:
    registry = CodecRegistry()
    registry.register(NativeTomlCodec(), format=Format.INI)
    assert registry.get(Format.INI).format is Format.TOML
