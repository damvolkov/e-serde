"""Format enum and extension detection — smoke coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

from e_loader.formats import Format, detect_format


async def test_format_members_exhaustive() -> None:
    assert {f.value for f in Format} == {"json", "yaml", "toml", "ini"}


_DETECTION_CASES: list[tuple[str, Format | None]] = [
    ("config.json", Format.JSON),
    ("config.yaml", Format.YAML),
    ("config.yml", Format.YAML),
    ("pyproject.toml", Format.TOML),
    ("setup.cfg", Format.INI),
    ("noext", None),
    ("config.UNKNOWN", None),
]


@pytest.mark.parametrize(
    ("filename", "expected"),
    _DETECTION_CASES,
    ids=["json", "yaml", "yml", "toml", "cfg-as-ini", "no-extension", "unknown-extension"],
)
async def test_detect_format_resolves_by_extension(filename: str, expected: Format | None) -> None:
    assert detect_format(Path(filename)) == expected
