"""NativeTomlCodec coverage — toml crate (rust-toml org)."""

from __future__ import annotations

import pytest

from eserde.backends.native.toml import NativeTomlCodec
from eserde.infra.errors import DumpError, LoadError
from eserde.infra.formats import Format


@pytest.fixture
def codec() -> NativeTomlCodec:
    return NativeTomlCodec()


async def test_codec_format_is_toml() -> None:
    assert NativeTomlCodec.format is Format.TOML


async def test_roundtrip_nested(codec: NativeTomlCodec, nested_payload: dict[str, object]) -> None:
    assert codec.loads(codec.dumps(nested_payload)) == nested_payload


async def test_loads_preserves_document_order(codec: NativeTomlCodec) -> None:
    data = b"z = 1\n[bravo]\nx = 1\n[alpha]\ny = 2\n"
    assert list(codec.loads(data)) == ["z", "bravo", "alpha"]


async def test_loads_datetime_as_iso_string(codec: NativeTomlCodec) -> None:
    loaded = codec.loads(b"dob = 1979-05-27T07:32:00Z\n")
    assert loaded == {"dob": "1979-05-27T07:32:00Z"}


async def test_dumps_preserves_insertion_order(codec: NativeTomlCodec) -> None:
    out = codec.dumps({"name": "demian", "n": 42}).decode()
    assert out.index("name") < out.index("n =")


async def test_dumps_rejects_null(codec: NativeTomlCodec) -> None:
    with pytest.raises(DumpError, match="null"):
        codec.dumps({"a": None})


async def test_loads_invalid_raises(codec: NativeTomlCodec) -> None:
    with pytest.raises(LoadError):
        codec.loads(b"= invalid toml")
