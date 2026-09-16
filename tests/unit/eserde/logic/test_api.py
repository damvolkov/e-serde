"""End-to-end facade tests: sync/async, sources, targets, typed decoding."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import msgspec
import pytest

from eserde import FormatError, LoaderError, LoadError
from eserde.infra.errors import EncoderError
from eserde.infra.formats import Format
from eserde.logic.api import adump, adumps, aload, aloads, dump, dumps, load, loads

if TYPE_CHECKING:
    from pathlib import Path

_PAYLOAD: dict[str, object] = {"name": "demian", "n": 42, "items": [1, 2, 3]}


class _Server(msgspec.Struct, frozen=True):
    host: str
    port: int


_ROUNDTRIP_FORMATS: list[Format] = [Format.JSON, Format.JSONC, Format.YAML, Format.TOML]


@pytest.mark.parametrize("fmt", _ROUNDTRIP_FORMATS, ids=[f.value for f in _ROUNDTRIP_FORMATS])
async def test_dumps_then_loads_roundtrip(fmt: Format) -> None:
    data = dumps(_PAYLOAD, format=fmt)
    assert loads(data, format=fmt) == _PAYLOAD


@pytest.mark.parametrize("fmt", _ROUNDTRIP_FORMATS, ids=[f.value for f in _ROUNDTRIP_FORMATS])
async def test_adumps_then_aloads_roundtrip(fmt: Format) -> None:
    data = await adumps(_PAYLOAD, format=fmt)
    assert await aloads(data, format=fmt) == _PAYLOAD


async def test_loads_typed_frozen_model() -> None:
    model = loads(b'{"host": "127.0.0.1", "port": 8080}', format=Format.JSON, type=_Server)
    assert model == _Server("127.0.0.1", 8080)
    with pytest.raises(AttributeError):
        model.port = 9000


async def test_loads_typed_validation_failure_wrapped() -> None:
    with pytest.raises(LoadError, match="schema validation failed"):
        loads(b'{"host": "x", "port": "nan"}', format=Format.JSON, type=_Server)


async def test_loads_typed_strict_off_coerces_strings() -> None:
    model = loads(b'{"host": "h", "port": "8080"}', format=Format.JSON, type=_Server, strict=False)
    assert model.port == 8080


async def test_loads_typed_ini_into_nested_model() -> None:
    class _Cfg(msgspec.Struct, frozen=True):
        service: _Server

    model = loads(b"[service]\nhost = h\nport = 8080\n", format=Format.INI, type=_Cfg, strict=False)
    assert model.service == _Server("h", 8080)


async def test_loads_bytes_without_format_raises() -> None:
    with pytest.raises(FormatError):
        loads(b"{}")


async def test_loads_str_without_format_raises() -> None:
    with pytest.raises(FormatError):
        loads("{}")


async def test_loads_unsupported_source_type_raises() -> None:
    with pytest.raises(FormatError, match="unsupported source"):
        loads(42)  # ty: ignore[invalid-argument-type]


async def test_loads_path_with_unknown_extension_raises(tmp_path: Path) -> None:
    target = tmp_path / "config.unknown"
    target.write_bytes(b"{}")
    with pytest.raises(FormatError):
        loads(target)


async def test_loads_path_autodetects_format(tmp_path: Path) -> None:
    target = tmp_path / "config.json"
    target.write_bytes(dumps(_PAYLOAD, format=Format.JSON))
    assert loads(target) == _PAYLOAD


async def test_aloads_path_autodetects_format(tmp_path: Path) -> None:
    target = tmp_path / "config.yaml"
    target.write_bytes(dumps(_PAYLOAD, format=Format.YAML))
    assert await aloads(target) == _PAYLOAD


async def test_loads_explicit_format_overrides_extension(tmp_path: Path) -> None:
    target = tmp_path / "config.json"
    target.write_bytes(dumps(_PAYLOAD, format=Format.YAML))
    assert loads(target, format=Format.YAML) == _PAYLOAD


async def test_load_and_dump_path_pair(tmp_path: Path) -> None:
    target = tmp_path / "db.toml"
    dump(_PAYLOAD, target)
    assert load(target) == _PAYLOAD


async def test_load_and_dump_binary_handles(tmp_path: Path) -> None:
    target = tmp_path / "db.jsonc"
    with target.open("wb") as fh:
        dump(_PAYLOAD, fh, format=Format.JSONC)
    with target.open("rb") as fh:
        assert load(fh, format=Format.JSONC) == _PAYLOAD


async def test_dump_path_infers_format(tmp_path: Path) -> None:
    target = tmp_path / "x.yaml"
    dump({"a": 1}, target)
    assert loads(target) == {"a": 1}


async def test_dump_handle_without_format_raises(tmp_path: Path) -> None:
    with (tmp_path / "x.bin").open("wb") as fh, pytest.raises(FormatError):
        dump({"a": 1}, fh)


async def test_aload_adump_roundtrip(tmp_path: Path) -> None:
    target = tmp_path / "async.yaml"
    await adump(_PAYLOAD, target)
    assert await aload(target) == _PAYLOAD


@dataclasses.dataclass(slots=True, frozen=True)
class _Point:
    x: int
    y: int


async def test_dumps_normalizes_through_encoder() -> None:
    @dataclasses.dataclass(slots=True, frozen=True)
    class _Point:
        x: int
        y: int

    moment = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
    encoded = dumps({"p": _Point(1, 2), "t": moment}, format=Format.YAML)
    assert loads(encoded, format=Format.YAML) == {
        "p": {"x": 1, "y": 2},
        "t": "2026-05-13T12:00:00+00:00",
    }


async def test_dumps_unencodable_object_raises() -> None:
    class _Opaque:
        __slots__ = ()

    with pytest.raises(EncoderError):
        dumps({"x": _Opaque()}, format=Format.YAML)


async def test_aload_adump_binary_handles(tmp_path: Path) -> None:
    target = tmp_path / "async.jsonc"
    with target.open("wb") as fh:
        await adump(_PAYLOAD, fh, format=Format.JSONC)
    with target.open("rb") as fh:
        assert await aload(fh, format=Format.JSONC) == _PAYLOAD


async def test_errors_share_hierarchy() -> None:
    assert issubclass(FormatError, LoaderError)
    assert issubclass(LoadError, LoaderError)
