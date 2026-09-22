"""Verifies every claim in ``eserde.infra.standards`` against live behaviour.

Each (format, feature) cell is probed and asserted equal to the documented
claim — in both directions: an unclaimed feature that starts working is as
much a failure as a claimed one that stops. Crate versions named by the
contract must match the lockfile / installed metadata, so dependency bumps
force an explicit re-verification of the spec claims.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from importlib.metadata import version as dist_version
from pathlib import Path

import pytest

from eserde import dumps, loads
from eserde.infra.formats import Format
from eserde.infra.standards import STANDARDS, Feature

REPO = Path(__file__).resolve().parents[4]

DESC_LABEL = {
    Feature.NULL: "`null` values",
    Feature.NONFINITE: "`.inf` / `.nan` floats",
    Feature.BIGNUM: "integers beyond 64-bit",
    Feature.COMMENTS: "comments",
    Feature.TRAILING_COMMAS: "trailing array commas",
    Feature.ANCHORS: "anchors & aliases (`&x` / `*x`)",
    Feature.MERGE_KEYS: "merge keys (`<<`)",
    Feature.BOM_TOLERANT: "leading UTF-8 BOM",
    Feature.MERGE_DUP_SECTIONS: "repeated `[section]` blocks",
}

type Probe = Callable[[Format], bool]


def _safe(fn: Callable[[], bool]) -> bool:
    try:
        return fn()
    except Exception:  # noqa: BLE001 — a failing probe simply means "not supported"
        return False


def _null(fmt: Format) -> bool:
    raw = {
        Format.JSON: b'{"k": null}',
        Format.JSONC: b'{"k": null}',
        Format.YAML: b"k:\n",
        Format.TOML: b"k = null\n",
        Format.INI: b"[s]\nk = null\n",
    }[fmt]
    return _safe(lambda: loads(raw, format=fmt) == {"k": None})


def _nonfinite(fmt: Format) -> bool:
    return _safe(lambda: loads(dumps({"k": math.inf}, format=fmt), format=fmt)["k"] == math.inf)


def _bignum(fmt: Format) -> bool:
    digits = int("9" * 40)
    return _safe(lambda: loads(dumps({"k": digits}, format=fmt), format=fmt)["k"] == digits)


def _comments(fmt: Format) -> bool:
    raw = {
        Format.JSON: b'{"k": 1} // c',
        Format.JSONC: b'{"k": 1} // c',
        Format.YAML: b"k: 1 # c",
        Format.TOML: b"# c\nk = 1\n",
        Format.INI: b"; c\n[s]\nk = 1\n",
    }[fmt]
    return _safe(lambda: loads(raw, format=fmt) in ({"k": 1}, {"s": {"k": "1"}}))


def _trailing(fmt: Format) -> bool:
    raw = {
        Format.JSON: b"[1, 2,]",
        Format.JSONC: b"[1, 2,]",
        Format.YAML: b"[1, 2,]\n",
        Format.TOML: b"a = [1, 2,]\n",
        Format.INI: b"[s]\nk = [1, 2,]\n",
    }[fmt]
    return _safe(lambda: loads(raw, format=fmt) in ([1, 2], {"a": [1, 2]}))


def _anchors(fmt: Format) -> bool:
    return _safe(lambda: loads(b"a: &x 1\nb: *x\n", format=fmt) == {"a": 1, "b": 1})


def _merge_keys(fmt: Format) -> bool:
    return _safe(lambda: loads(b"a: &x {k: 1}\nb: {<<: *x}\n", format=fmt)["b"] == {"k": 1})


def _bom(fmt: Format) -> bool:
    payload = {
        Format.JSON: b'{"k": 1}',
        Format.JSONC: b'{"k": 1}',
        Format.YAML: b"k: 1\n",
        Format.TOML: b"k = 1\n",
        Format.INI: b"[s]\nk = 1\n",
    }[fmt]
    return _safe(lambda: loads(b"\xef\xbb\xbf" + payload, format=fmt) in ({"k": 1}, {"s": {"k": "1"}}))


def _merge_dup_sections(fmt: Format) -> bool:
    return _safe(lambda: loads(b"[a]\nk = 1\n[a]\nj = 2\n", format=fmt) == {"a": {"k": "1", "j": "2"}})


_PROBES: dict[Feature, Probe] = {
    Feature.NULL: _null,
    Feature.NONFINITE: _nonfinite,
    Feature.BIGNUM: _bignum,
    Feature.COMMENTS: _comments,
    Feature.TRAILING_COMMAS: _trailing,
    Feature.ANCHORS: _anchors,
    Feature.MERGE_KEYS: _merge_keys,
    Feature.BOM_TOLERANT: _bom,
    Feature.MERGE_DUP_SECTIONS: _merge_dup_sections,
}

_CELLS = [(fmt, feature) for fmt in Format for feature in _PROBES]


@pytest.mark.parametrize(("fmt", "feature"), _CELLS, ids=[f"{fmt.value}-{feature.value}" for fmt, feature in _CELLS])
def test_standard_claims_match_behaviour(fmt: Format, feature: Feature) -> None:
    claimed = feature in STANDARDS[fmt].features
    assert _PROBES[feature](fmt) is claimed, f"{fmt.value}: {feature.value} claimed={claimed}"


def test_every_format_has_a_standard() -> None:
    assert set(STANDARDS) == set(Format)


@pytest.mark.parametrize("fmt", list(Format), ids=lambda f: f.value)
def test_engine_version_matches_lockfile(fmt: Format) -> None:
    standard = STANDARDS[fmt]
    if standard.crate == "msgspec":
        installed = dist_version("msgspec")
    else:
        lock = (REPO / "Cargo.lock").read_text(encoding="utf-8")
        installed = next(re.finditer(rf'name = "{re.escape(standard.crate)}"\nversion = "([^"]+)"', lock)).group(1)
    assert installed.startswith(standard.version), (
        f"{fmt.value}: engine is {installed}, contract says {standard.version}"
    )


@pytest.mark.parametrize("fmt", list(Format), ids=[f.value for f in Format])
def test_format_page_not_stale(fmt: Format) -> None:
    page = (REPO / "docs" / "formats" / f"{fmt.value}.md").read_text(encoding="utf-8")
    standard = STANDARDS[fmt]
    assert f"**Spec:** {standard.spec}" in page, f"docs/formats/{fmt.value}.md stale on spec"
    assert f"**Engine:** `{standard.engine}` {standard.version}" in page, f"docs/formats/{fmt.value}.md stale on engine"
    for feature in Feature:
        cell = "yes" if feature in standard.features else "—"
        assert f"{DESC_LABEL[feature]} | {cell} " in page, (
            f"docs/formats/{fmt.value}.md: {feature.value} row out of sync"
        )
