"""MsgspecJsonCodec coverage — msgspec.json C decoder."""

from __future__ import annotations

import pytest

from eserde.backends.msgspec.json import MsgspecJsonCodec
from eserde.infra.errors import DumpError, LoadError
from eserde.infra.formats import Format


@pytest.fixture
def codec() -> MsgspecJsonCodec:
    return MsgspecJsonCodec()


async def test_codec_format_is_json() -> None:
    assert MsgspecJsonCodec.format is Format.JSON


async def test_roundtrip_small(codec: MsgspecJsonCodec, small_payload: dict[str, object]) -> None:
    assert codec.loads(codec.dumps(small_payload)) == small_payload


async def test_roundtrip_nested(codec: MsgspecJsonCodec, nested_payload: dict[str, object]) -> None:
    assert codec.loads(codec.dumps(nested_payload)) == nested_payload


async def test_loads_preserves_key_order(codec: MsgspecJsonCodec) -> None:
    assert list(codec.loads(b'{"z": 1, "a": 2, "m": 3}')) == ["z", "a", "m"]


async def test_loads_invalid_raises(codec: MsgspecJsonCodec) -> None:
    with pytest.raises(LoadError):
        codec.loads(b"{not json}")


async def test_loads_non_utf8_raises(codec: MsgspecJsonCodec) -> None:
    with pytest.raises(LoadError):
        codec.loads(b"\xff\xfe")


async def test_dumps_unsupported_type_raises(codec: MsgspecJsonCodec) -> None:
    class _Unserializable:
        pass

    with pytest.raises(DumpError):
        codec.dumps({"x": _Unserializable()})
