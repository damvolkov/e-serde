"""CodecRegistry behavior: register, get, replace, has, formats."""

from __future__ import annotations

from typing import Any, ClassVar

import pytest

from e_loader.codecs.json_orjson import OrjsonCodec
from e_loader.codecs.toml_stdlib import TomllibCodec
from e_loader.errors import CodecError
from e_loader.formats import Format
from e_loader.protocols import Codec
from e_loader.registry import CodecRegistry, default_registry


class _StubJsonCodec:
    format: ClassVar[Format] = Format.JSON

    def loads(self, data: bytes) -> Any:
        return {"stub": True}

    def dumps(self, obj: Any) -> bytes:
        return b'{"stub":true}'


async def test_default_registry_covers_all_formats() -> None:
    assert default_registry.formats() == frozenset(Format)


async def test_register_then_get() -> None:
    registry = CodecRegistry()
    codec = OrjsonCodec()
    registry.register(codec)
    assert registry.get(Format.JSON) is codec


async def test_register_duplicate_raises() -> None:
    registry = CodecRegistry()
    registry.register(OrjsonCodec())
    with pytest.raises(CodecError, match="already registered"):
        registry.register(OrjsonCodec())


async def test_register_override_replaces() -> None:
    registry = CodecRegistry()
    registry.register(OrjsonCodec())
    new_codec = _StubJsonCodec()
    registry.register(new_codec, override=True)
    assert registry.get(Format.JSON) is new_codec


async def test_replace_returns_previous() -> None:
    registry = CodecRegistry()
    original = OrjsonCodec()
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
    registry.register(OrjsonCodec())
    assert registry.has(Format.JSON)


async def test_stub_codec_is_runtime_checkable() -> None:
    assert isinstance(_StubJsonCodec(), Codec)


async def test_register_explicit_format_overrides_codec_format() -> None:
    registry = CodecRegistry()
    registry.register(TomllibCodec(), format=Format.INI)
    assert registry.get(Format.INI).format == Format.TOML
