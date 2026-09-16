"""Correctness guard behind every timing: all rivals parse, and re-read, the same tree.

A matrix that times a parser choking on the payload is worthless: first check every
rival decodes the corpus to the exact source tree, then check every rival reads back
what e-serde wrote. Runs under the `bench` marker: it imports the rival set.
"""

from __future__ import annotations

import pytest

from e_serde import Format
from tests.benchmark.payloads import payload, source_tree
from tests.benchmark.rivals import DUMP_RIVALS, LOAD_RIVALS

pytestmark = pytest.mark.bench


@pytest.mark.parametrize("fmt", [f.value for f in Format])
@pytest.mark.parametrize("size", ["1kb", "100kb"])
def test_payload(fmt: str, size: str) -> None:
    format_ = Format(fmt)
    expected = source_tree(format_, size)
    data = payload(format_, size)
    for rival, decode in LOAD_RIVALS[format_].items():
        assert decode(data) == expected, rival


@pytest.mark.parametrize("fmt", [f.value for f in Format])
@pytest.mark.parametrize("size", ["1kb", "100kb"])
def test_payload_roundtrip(fmt: str, size: str) -> None:
    format_ = Format(fmt)
    expected = source_tree(format_, size)
    written = DUMP_RIVALS[format_]["e-serde"](expected)
    for rival, decode in LOAD_RIVALS[format_].items():
        assert decode(written) == expected, rival
