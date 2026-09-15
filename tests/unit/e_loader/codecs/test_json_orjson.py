"""OrjsonCodec roundtrip + error coverage."""

from __future__ import annotations

import pytest

from e_loader.codecs.json_orjson import OrjsonCodec
from e_loader.errors import DumpError, LoadError
from e_loader.formats import Format


async def test_codec_format_is_json() -> None:
    assert OrjsonCodec.format is Format.JSON


async def test_roundtrip_small(small_payload: dict[str, object]) -> None:
    codec = OrjsonCodec()
    assert codec.loads(codec.dumps(small_payload)) == small_payload


async def test_roundtrip_nested(nested_payload: dict[str, object]) -> None:
    codec = OrjsonCodec()
    assert codec.loads(codec.dumps(nested_payload)) == nested_payload


async def test_loads_invalid_raises() -> None:
    with pytest.raises(LoadError):
        OrjsonCodec().loads(b"{not json}")


async def test_dumps_unsupported_type_raises() -> None:
    class _Unserializable:
        pass

    with pytest.raises(DumpError):
        OrjsonCodec().dumps({"x": _Unserializable()})
