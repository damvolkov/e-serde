"""Async twins: serial decodes vs event-loop fan-out — the GIL-detachment probe.

The bytes variants isolate the decoder pool; the file variants add I/O offload
(`aload` reads outside the loop). Eight workers stress the default `to_thread` pool.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

import e_serde
from e_serde import Format
from tests.benchmark.payloads import payload

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture

pytestmark = [pytest.mark.bench, pytest.mark.timeout(3600)]

_WORKERS = 8
type Files = dict[tuple[str, str], Path]
type Drive = Callable[[Format, str, Files], list[Any]]


def _loads_bytes(fmt: Format, size: str, _files: Files) -> list[Any]:
    data = payload(fmt, size)
    return [e_serde.loads(data, format=fmt) for _ in range(_WORKERS)]


def _aloads_bytes(fmt: Format, size: str, _files: Files) -> list[Any]:
    data = payload(fmt, size)

    async def _gather() -> list[Any]:
        return list(await asyncio.gather(*(e_serde.aloads(data, format=fmt) for _ in range(_WORKERS))))

    return asyncio.run(_gather())


def _loads_file(fmt: Format, size: str, files: Files) -> list[Any]:
    path = files[fmt.value, size]
    return [e_serde.load(path) for _ in range(_WORKERS)]


def _aloads_file(fmt: Format, size: str, files: Files) -> list[Any]:
    path = files[fmt.value, size]

    async def _gather() -> list[Any]:
        return list(await asyncio.gather(*(e_serde.aload(path) for _ in range(_WORKERS))))

    return asyncio.run(_gather())


_DRIVES: dict[str, Drive] = {
    "loads-bytes": _loads_bytes,
    "aloads-bytes": _aloads_bytes,
    "loads-file": _loads_file,
    "aloads-file": _aloads_file,
}


@pytest.mark.parametrize("drive", list(_DRIVES))
@pytest.mark.parametrize("fmt", ["json", "jsonc", "yaml", "toml"])
@pytest.mark.parametrize("size", ["100kb", "10mb"])
def test_aloads(benchmark: BenchmarkFixture, fmt: str, size: str, drive: str, corpus_files: Files) -> None:
    outputs = benchmark(_DRIVES[drive], Format(fmt), size, corpus_files)
    assert len(outputs) == _WORKERS
