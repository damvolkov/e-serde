"""Validation matrix: plain decode vs typed (`type=`) across rival schema pipelines.

`msgspec:struct` and `pydantic:*` are the direct schema engines; the `e-serde:*` rows
separate the codec cost (`e-serde:plain`) from the `msgspec.convert` step (`:struct`,
`:dataclass`) so validation overhead is attributable, not folklore.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from e_serde import Format
from tests.benchmark.payloads import payload
from tests.benchmark.rivals import TYPED_RIVALS

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture

pytestmark = [pytest.mark.bench, pytest.mark.timeout(3600)]


def test_loads_typed(benchmark: BenchmarkFixture, fmt: str, size: str, rival: str) -> None:
    format_ = Format(fmt)
    data = payload(format_, size)
    decoded: Any = benchmark(TYPED_RIVALS[format_][rival], data)
    assert decoded is not None
