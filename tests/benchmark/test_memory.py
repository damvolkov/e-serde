"""Allocation peak per decoder (tracemalloc, 100 KB payloads, Python-visible memory).

`tracemalloc` only sees what the Python allocator owns: C/Rust buffers that never
touch it (orjson, msgspec) read low, which is the point — decode-and-discard on
small objects is where Python-visible pressure actually lives.
"""

from __future__ import annotations

import tracemalloc
from typing import TYPE_CHECKING

import pytest

from e_serde import Format
from tests.benchmark.payloads import payload
from tests.benchmark.rivals import LOAD_RIVALS

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture

pytestmark = [pytest.mark.bench, pytest.mark.timeout(600)]


def test_loads_peak(benchmark: BenchmarkFixture, fmt: str, size: str, rival: str) -> None:
    format_ = Format(fmt)
    data = payload(format_, size)
    decode = LOAD_RIVALS[format_][rival]

    def _peak_bytes() -> int:
        tracemalloc.start()
        try:
            decode(data)
        finally:
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
        return peak

    benchmark.extra_info["peak_kib"] = round(benchmark(_peak_bytes) / 1024, 1)
