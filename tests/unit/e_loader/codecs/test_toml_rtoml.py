"""RtomlCodec roundtrip + error coverage."""

from __future__ import annotations

import pytest

from e_loader.codecs.toml_rtoml import RtomlCodec
from e_loader.errors import LoadError
from e_loader.formats import Format


async def test_codec_format_is_toml() -> None:
    assert RtomlCodec.format is Format.TOML


async def test_roundtrip_small(small_payload: dict[str, object]) -> None:
    codec = RtomlCodec()
    assert codec.loads(codec.dumps(small_payload)) == small_payload


async def test_roundtrip_nested(nested_payload: dict[str, object]) -> None:
    codec = RtomlCodec()
    assert codec.loads(codec.dumps(nested_payload)) == nested_payload


async def test_loads_invalid_raises() -> None:
    with pytest.raises(LoadError):
        RtomlCodec().loads(b"= invalid toml")
