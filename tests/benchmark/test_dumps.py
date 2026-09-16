"""Encode matrix: every rival writes the same source tree, bytes out."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from e_serde import Format
from tests.benchmark.payloads import source_tree
from tests.benchmark.rivals import DUMP_RIVALS

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture

pytestmark = [pytest.mark.bench, pytest.mark.timeout(3600)]


def test_dumps(benchmark: BenchmarkFixture, fmt: str, size: str, rival: str) -> None:
    format_ = Format(fmt)
    obj = source_tree(format_, size)
    encoded = benchmark(DUMP_RIVALS[format_][rival], obj)
    assert isinstance(encoded, bytes)
    assert encoded
