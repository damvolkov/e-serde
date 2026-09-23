"""Format enum and extension detection — smoke coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

from eserde.infra.formats import Format, detect_format


async def test_format_members_exhaustive() -> None:
    assert {f.value for f in Format} == {"json", "jsonc", "yaml", "toml", "ini", "csv", "tsv"}


_DETECTION_CASES: list[tuple[str, Format | None]] = [
    ("config.json", Format.JSON),
    ("config.jsonc", Format.JSONC),
    ("config.yaml", Format.YAML),
    ("config.yml", Format.YAML),
    ("pyproject.toml", Format.TOML),
    ("setup.cfg", Format.INI),
    ("sys.conf", Format.INI),
    ("data.csv", Format.CSV),
    ("data.tsv", Format.TSV),
    ("noext", None),
    ("config.UNKNOWN", None),
]


@pytest.mark.parametrize(
    ("filename", "expected"),
    _DETECTION_CASES,
    ids=[name for name, _ in _DETECTION_CASES],
)
async def test_detect_format_resolves_by_extension(filename: str, expected: Format | None) -> None:
    assert detect_format(Path(filename)) == expected
