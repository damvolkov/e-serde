"""Canonical sample fixtures: the four structured formats must decode to one tree.

`sample.{json,jsonc,yaml,toml}` are the same rich config (every scalar type, big int,
floats, bools, empty/null collections, unicode, and strings that look like dates or
numbers). Cross-format equality is the strongest correctness signal the codecs agree;
TOML has no null type, so its tree legitimately omits `null_value` (per-format note).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from e_serde import Format, dumps, load, loads

RESOURCES = Path(__file__).resolve().parents[2] / "resources"

STRUCTURED = (Format.JSON, Format.JSONC, Format.YAML, Format.TOML)
NULL_PATH = ("types", "null_value")
TYPED_KEYS = ("meta", "settings", "entries")


def _sample(fmt: Format) -> Any:
    return load(RESOURCES / f"sample.{fmt.value}", format=fmt)


def _without_null(tree: dict[str, Any]) -> dict[str, Any]:
    rest = {k: v for k, v in tree["types"].items() if k != "null_value"}
    return {**tree, "types": rest}


@pytest.mark.parametrize("fmt", STRUCTURED)
def test_sample_decodes_to_expected_types(fmt: Format) -> None:
    tree = _sample(fmt)
    assert tuple(sorted(tree)) == tuple(sorted(_sample(Format.JSON)))


def test_sample_cross_format_equivalence() -> None:
    reference = _sample(Format.JSON)
    assert reference["types"]["null_value"] is None
    bigint = reference["types"]["bigint"]
    assert isinstance(bigint, int)
    assert bigint == 9_007_199_254_740_991
    assert isinstance(reference["types"]["float_pi"], float)
    assert reference["types"]["numeric_string"] == "123"
    assert reference["types"]["date_like"] == "2024-01-15"
    for fmt in STRUCTURED:
        expected = _without_null(reference) if fmt is Format.TOML else reference
        assert _sample(fmt) == expected, fmt


def test_sample_jsonc_carries_comments() -> None:
    text = (RESOURCES / "sample.jsonc").read_text()
    assert "//" in text
    assert "/*" in text
    assert loads(text, format=Format.JSONC) == _sample(Format.JSON)


@pytest.mark.parametrize("fmt", STRUCTURED)
def test_sample_roundtrip_stable(fmt: Format) -> None:
    tree = _sample(fmt)
    revived = loads(dumps(tree, format=fmt), format=fmt)
    expected = _without_null(tree) if fmt is Format.TOML else tree
    assert revived == expected


def test_sample_ini_is_flat_strings() -> None:
    tree = _sample(Format.INI)
    assert all(
        isinstance(section, dict) and all(isinstance(v, str) for v in section.values()) for section in tree.values()
    )
