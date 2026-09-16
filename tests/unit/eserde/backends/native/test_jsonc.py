"""NativeJsoncCodec coverage — jsonc-parser (Deno)."""

from __future__ import annotations

import pytest

from eserde.backends.native.jsonc import NativeJsoncCodec
from eserde.infra.errors import LoadError
from eserde.infra.formats import Format


@pytest.fixture
def codec() -> NativeJsoncCodec:
    return NativeJsoncCodec()


async def test_codec_format_is_jsonc() -> None:
    assert NativeJsoncCodec.format is Format.JSONC


async def test_loads_line_and_block_comments(codec: NativeJsoncCodec) -> None:
    data = b'{\n  // line\n  "a": 1 /* block */, "b": 2\n}\n'
    assert codec.loads(data) == {"a": 1, "b": 2}


async def test_loads_trailing_comma_and_loose_keys(codec: NativeJsoncCodec) -> None:
    assert codec.loads(b"{a: 1, b: [2, 3,],}") == {"a": 1, "b": [2, 3]}


async def test_loads_single_quoted_strings(codec: NativeJsoncCodec) -> None:
    assert codec.loads(b"{'k': 'v'}") == {"k": "v"}


async def test_dumps_emits_strict_json(codec: NativeJsoncCodec, small_payload: dict[str, object]) -> None:
    assert codec.loads(codec.dumps(small_payload)) == small_payload


async def test_loads_invalid_raises(codec: NativeJsoncCodec) -> None:
    with pytest.raises(LoadError):
        codec.loads(b'{"a": ')
