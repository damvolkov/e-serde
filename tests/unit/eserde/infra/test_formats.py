"""Format enum and extension detection — smoke coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

from eserde.infra.errors import FormatError
from eserde.infra.formats import Format, coerce_format, detect_format, sniff_format


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


_SNIFF_CASES: list[tuple[bytes, Format | None]] = [
    (b'{"k": 1}', Format.JSON),
    (b'  {"k": 1}', Format.JSON),
    (b"{}", Format.JSON),
    (b"{ }", Format.JSON),
    (b'\xef\xbb\xbf{"k": 1}', Format.JSON),
    (b'{// c\n"k": 1}', Format.JSONC),
    (b'{ /* c */ "k": 1}', Format.JSONC),
    (b'// doc header\n{"k": 1}', Format.JSONC),
    (b'/* doc header */ {"k": 1}', Format.JSONC),
    (b'{"url": "http://x"}', Format.JSON),
    (b"[1, 2]", None),
    (b"[table]\nk = 1", None),
    (b"k: 1", None),
    (b"# c", None),
    (b"", None),
    (b"   ", None),
    (b'"scalar"', None),
    (b"a,b\n1,2", None),
]


@pytest.mark.parametrize(("data", "expected"), _SNIFF_CASES, ids=range(len(_SNIFF_CASES)))
def test_sniff_format_strict(data: bytes, expected: Format | None) -> None:
    assert sniff_format(data) is expected


def test_coerce_format_accepts_members_and_names() -> None:
    assert coerce_format(Format.YAML) is Format.YAML
    assert coerce_format("yaml") is Format.YAML


def test_coerce_format_rejects_unknown_names() -> None:
    with pytest.raises(FormatError, match="unknown format 'jzon'"):
        coerce_format("jzon")
