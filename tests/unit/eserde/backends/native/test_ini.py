"""NativeIniCodec coverage — rust-ini, strict subset (no interpolation, no DEFAULT merge)."""

from __future__ import annotations

import pytest

from eserde.backends.native.ini import NativeIniCodec
from eserde.infra.errors import DumpError, LoadError
from eserde.infra.formats import Format


@pytest.fixture
def codec() -> NativeIniCodec:
    return NativeIniCodec()


async def test_codec_format_is_ini() -> None:
    assert NativeIniCodec.format is Format.INI


async def test_roundtrip(codec: NativeIniCodec, ini_payload: dict[str, dict[str, str]]) -> None:
    assert codec.loads(codec.dumps(ini_payload)) == ini_payload


async def test_values_always_strings(codec: NativeIniCodec) -> None:
    loaded = codec.loads(b"[s]\nport = 8080\nenabled = true\n")
    assert loaded == {"s": {"port": "8080", "enabled": "true"}}


async def test_comments_ignored(codec: NativeIniCodec) -> None:
    assert codec.loads(b"# hash\n; semi\n[s]\nk = v\n") == {"s": {"k": "v"}}


async def test_multiline_roundtrip(codec: NativeIniCodec) -> None:
    payload = {"s": {"text": "line one\nline two"}}
    assert codec.loads(codec.dumps(payload)) == payload


async def test_dumps_rejects_non_dict(codec: NativeIniCodec) -> None:
    with pytest.raises(DumpError, match="mapping"):
        codec.dumps(["not", "a", "dict"])


async def test_dumps_rejects_nested_values(codec: NativeIniCodec) -> None:
    with pytest.raises(DumpError):
        codec.dumps({"s": {"nested": {"a": 1}}})


async def test_keys_outside_section_raise(codec: NativeIniCodec) -> None:
    with pytest.raises(LoadError, match="outside"):
        codec.loads(b"stray = value\n[s]\nk = v\n")


async def test_loads_invalid_raises(codec: NativeIniCodec) -> None:
    with pytest.raises(LoadError):
        codec.loads(b"[unclosed\nkey = value\n")
