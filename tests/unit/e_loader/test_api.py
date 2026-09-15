"""End-to-end facade tests: `loads`/`dumps` through the default registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from e_loader.api import adumps, aloads, dumps, loads
from e_loader.errors import FormatError
from e_loader.formats import Format

_PAYLOAD: dict[str, int | str | list[int]] = {"name": "demian", "n": 42, "items": [1, 2, 3]}


_FORMAT_ROUNDTRIP_CASES: list[Format] = [Format.JSON, Format.YAML, Format.TOML]


@pytest.mark.parametrize("fmt", _FORMAT_ROUNDTRIP_CASES, ids=[f.value for f in _FORMAT_ROUNDTRIP_CASES])
async def test_dumps_then_loads_roundtrip(fmt: Format) -> None:
    data = dumps(_PAYLOAD, format=fmt)
    assert loads(data, format=fmt) == _PAYLOAD


@pytest.mark.parametrize("fmt", _FORMAT_ROUNDTRIP_CASES, ids=[f.value for f in _FORMAT_ROUNDTRIP_CASES])
async def test_adumps_then_aloads_roundtrip(fmt: Format) -> None:
    data = await adumps(_PAYLOAD, format=fmt)
    assert await aloads(data, format=fmt) == _PAYLOAD


async def test_loads_bytes_without_format_raises() -> None:
    with pytest.raises(FormatError):
        loads(b"{}")


async def test_loads_str_without_format_raises() -> None:
    with pytest.raises(FormatError):
        loads("{}")


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
