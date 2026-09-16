"""Decode matrix: every rival parses byte-identical payloads under equal conditions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from eserde import Format
from tests.benchmark.payloads import payload
from tests.benchmark.rivals import LOAD_RIVALS

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture

pytestmark = [pytest.mark.bench, pytest.mark.timeout(3600)]


def test_loads(benchmark: BenchmarkFixture, fmt: str, size: str, rival: str) -> None:
    format_ = Format(fmt)
    data = payload(format_, size)
    decoded: Any = benchmark(LOAD_RIVALS[format_][rival], data)
    assert isinstance(decoded, dict)
