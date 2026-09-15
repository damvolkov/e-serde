"""PyyamlCodec roundtrip + error coverage."""

from __future__ import annotations

import pytest

from e_loader.codecs.yaml_pyyaml import PyyamlCodec
from e_loader.errors import LoadError
from e_loader.formats import Format


async def test_codec_format_is_yaml() -> None:
    assert PyyamlCodec.format is Format.YAML


async def test_roundtrip_small(small_payload: dict[str, object]) -> None:
    codec = PyyamlCodec()
    assert codec.loads(codec.dumps(small_payload)) == small_payload


async def test_roundtrip_nested(nested_payload: dict[str, object]) -> None:
    codec = PyyamlCodec()
    assert codec.loads(codec.dumps(nested_payload)) == nested_payload


async def test_loads_invalid_raises() -> None:
    with pytest.raises(LoadError):
        PyyamlCodec().loads(b"{ invalid: yaml: :: ")
