"""NativeYamlCodec coverage — saphyr (YAML 1.2 core schema) + native emitter."""

from __future__ import annotations

import pytest

from e_serde.backends.native.yaml import NativeYamlCodec
from e_serde.infra.errors import LoadError
from e_serde.infra.formats import Format


@pytest.fixture
def codec() -> NativeYamlCodec:
    return NativeYamlCodec()


async def test_codec_format_is_yaml() -> None:
    assert NativeYamlCodec.format is Format.YAML


async def test_roundtrip_nested(codec: NativeYamlCodec, nested_payload: dict[str, object]) -> None:
    assert codec.loads(codec.dumps(nested_payload)) == nested_payload


async def test_loads_core_schema_types(codec: NativeYamlCodec) -> None:
    data = b"a: 1\nb: 2.5\nc: true\nd: null\ne: yes\nf: 2026-01-01\n"
    assert codec.loads(data) == {"a": 1, "b": 2.5, "c": True, "d": None, "e": "yes", "f": "2026-01-01"}


async def test_loads_explicit_tag(codec: NativeYamlCodec) -> None:
    assert codec.loads(b"a: !!str 42\n") == {"a": "42"}


async def test_loads_tagged_collection_expands_inner(codec: NativeYamlCodec) -> None:
    assert codec.loads(b"a: !custom [1, 2]\n") == {"a": [1, 2]}


async def test_loads_unicode(codec: NativeYamlCodec) -> None:
    assert codec.loads("city: Málaga\n".encode()) == {"city": "Málaga"}


async def test_dumps_quotes_ambiguity(codec: NativeYamlCodec) -> None:
    assert codec.dumps({"a": "true", "b": "123", "c": "# hash"}) == b'a: "true"\nb: "123"\nc: "# hash"\n'


async def test_dumps_empty_collections(codec: NativeYamlCodec) -> None:
    assert codec.loads(codec.dumps({"a": {}, "b": []})) == {"a": {}, "b": []}


async def test_dumps_sequence_of_mappings(codec: NativeYamlCodec) -> None:
    payload = {"rows": [{"i": 1}, {"i": 2}]}
    assert codec.loads(codec.dumps(payload)) == payload


async def test_loads_multi_document_raises(codec: NativeYamlCodec) -> None:
    with pytest.raises(LoadError, match="exactly one"):
        codec.loads(b"a: 1\n---\nb: 2\n")


async def test_loads_invalid_raises(codec: NativeYamlCodec) -> None:
    with pytest.raises(LoadError):
        codec.loads(b"{ invalid: yaml: :: ")


async def test_loads_non_utf8_raises(codec: NativeYamlCodec) -> None:
    with pytest.raises(LoadError):
        codec.loads(b"\xff\xfe broken")
