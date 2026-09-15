"""ConfigparserCodec roundtrip + error coverage."""

from __future__ import annotations

import pytest

from e_loader.codecs.ini_stdlib import ConfigparserCodec
from e_loader.errors import DumpError, LoadError
from e_loader.formats import Format


async def test_codec_format_is_ini() -> None:
    assert ConfigparserCodec.format is Format.INI


async def test_roundtrip(ini_payload: dict[str, dict[str, str]]) -> None:
    codec = ConfigparserCodec()
    assert codec.loads(codec.dumps(ini_payload)) == ini_payload


async def test_dumps_rejects_non_dict() -> None:
    with pytest.raises(DumpError):
        ConfigparserCodec().dumps(["not", "a", "dict"])


async def test_loads_invalid_raises() -> None:
    with pytest.raises(LoadError):
        ConfigparserCodec().loads(b"this is not = ini\nsections")
