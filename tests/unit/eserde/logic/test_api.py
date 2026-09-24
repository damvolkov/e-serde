"""End-to-end facade tests: sync/async, sources, targets, typed decoding."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from fractions import Fraction
from ipaddress import IPv4Address
from typing import TYPE_CHECKING

import msgspec
import pydantic
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
    with pytest.raises(FormatError, match="cannot infer"):
        loads(b"k: 1")


async def test_loads_str_without_format_raises() -> None:
    with pytest.raises(FormatError, match="cannot infer"):
        loads("k: 1")


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


##### DECODE HOOKS #####


async def test_loads_object_hook_walks_bottom_up() -> None:
    decoded = loads(b'{"a": {"b": 1}}', format=Format.JSON, object_hook=lambda d: {"wrap": d})
    assert decoded == {"wrap": {"a": {"wrap": {"b": 1}}}}


async def test_loads_object_hook_on_typed_tree_before_convert() -> None:
    decoded = loads(
        b'[{"host": "h", "port": 1}]',
        format=Format.JSON,
        object_hook=dict,
        type=list[_Server],
    )
    assert decoded == [_Server(host="h", port=1)]


class _Net(msgspec.Struct):
    ip: IPv4Address


async def test_loads_dec_hook_materializes_custom_fields() -> None:
    assert loads(b'{"ip": "10.0.0.1"}', format=Format.JSON, type=_Net, dec_hook=lambda t, v: t(v)) == _Net(
        ip=IPv4Address("10.0.0.1")
    )


async def test_loads_dec_hook_without_type_raises() -> None:
    with pytest.raises(FormatError, match="requires a type"):
        loads(b"{}", format=Format.JSON, dec_hook=lambda t, v: None)


async def test_aloads_carries_decode_hooks() -> None:
    decoded = await aloads(b'{"a": 1}', format=Format.JSON, object_hook=lambda d: {**d, "seen": True})
    assert decoded == {"a": 1, "seen": True}


##### ENCODE HOOKS #####


async def test_dumps_default_and_encoders_per_call() -> None:
    data = {"a": Fraction(1, 2), "b": Fraction(1, 4)}
    with_default = loads(dumps(data, format=Format.JSON, default=float), format=Format.JSON)
    with_encoders = loads(dumps(data, format=Format.JSON, encoders={Fraction: str}), format=Format.JSON)
    assert (with_default, with_encoders) == ({"a": 0.5, "b": 0.25}, {"a": "1/2", "b": "1/4"})


async def test_adumps_carries_encode_hooks() -> None:
    encoded = await adumps({"f": Fraction(3, 4)}, format=Format.YAML, default=float)
    assert loads(encoded, format=Format.YAML) == {"f": 0.75}


##### PYDANTIC SCHEMAS #####


async def test_loads_pydantic_model_and_generics() -> None:
    class _M(pydantic.BaseModel):
        n: int

    assert loads(b'{"n": 5}', format=Format.JSON, type=_M) == _M(n=5)
    assert loads(b'[{"n": 5}]', format=Format.JSON, type=list[_M]) == [_M(n=5)]
    assert await aloads(b'{"n": 5}', format=Format.JSON, type=_M) == _M(n=5)


async def test_loads_pydantic_invalid_wraps_as_load_error() -> None:
    class _M(pydantic.BaseModel):
        n: int

    with pytest.raises(LoadError, match="schema validation failed"):
        loads(b'{"n": "x"}', format=Format.JSON, type=_M)


async def test_loads_unknown_class_keeps_msgspec_rejection() -> None:
    class _Opaque:
        __slots__ = ()

    with pytest.raises(LoadError):
        loads(b'{"x": 1}', format=Format.JSON, type=_Opaque)


async def test_load_accepts_str_path(tmp_path: Path) -> None:
    (tmp_path / "doc.json").write_text('{"a": 1}', "utf-8")
    assert load(str(tmp_path / "doc.json")) == {"a": 1}


async def test_format_accepts_plain_names(tmp_path: Path) -> None:
    (tmp_path / "doc.bin").write_bytes(b'{"a": 1}')
    assert load(tmp_path / "doc.bin", format="json") == {"a": 1}
    assert dumps({"a": 1}, format="json") == b'{"a":1}'


async def test_loads_json_object_sniffed() -> None:
    assert loads(b'{"k": [1, 2]}') == {"k": [1, 2]}
    assert loads('{"k": 1}') == {"k": 1}


async def test_sniffed_json_failure_carries_hint() -> None:
    with pytest.raises(LoadError, match="sniffed"):
        loads(b'{"broken": ')


async def test_aload_accepts_str_path(tmp_path: Path) -> None:
    (tmp_path / "doc.toml").write_text("k = 1\n", "utf-8")
    assert await aload(str(tmp_path / "doc.toml")) == {"k": 1}


async def test_adump_accepts_str_path(tmp_path: Path) -> None:
    await adump({"a": 1}, str(tmp_path / "out.jsonc"))
    assert (tmp_path / "out.jsonc").read_bytes() == b'{"a":1}'
