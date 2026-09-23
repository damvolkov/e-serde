"""Benchmark harness: parametrizes every rival matrix into single-benchmark cases.

Parameters are strings only (format value, size label, rival name) so the whole
matrix survives pytest-benchmark's JSON export and can be regrouped by the report.
Rivals that blow up superlinearly on the 10 MB payloads are excluded outright.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from eserde import Format
from tests.benchmark.payloads import payload, sizes
from tests.benchmark.rivals import DUMP_RIVALS, LOAD_RIVALS, TYPED_RIVALS

if TYPE_CHECKING:
    from pathlib import Path

_FILE_EXT: dict[Format, str] = {
    Format.JSON: ".json",
    Format.JSONC: ".jsonc",
    Format.YAML: ".yaml",
    Format.TOML: ".toml",
    Format.CSV: ".csv",
    Format.TSV: ".tsv",
}

_SLOW_10MB: dict[str, set[tuple[str, str]]] = {
    "test_loads": {("jsonc", "json5"), ("yaml", "ruamel")},
    "test_dumps": {
        ("jsonc", "json5"),
        ("yaml", "ruamel"),
        ("toml", "tomlkit"),
    },
}
_MATRICES: dict[str, dict] = {
    "test_loads": LOAD_RIVALS,
    "test_dumps": DUMP_RIVALS,
    "test_loads_typed": TYPED_RIVALS,
    "test_loads_peak": LOAD_RIVALS,
}


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    matrix = _MATRICES.get(metafunc.definition.name)
    if matrix is None:
        return
    slow = _SLOW_10MB.get(metafunc.definition.name, set())
    bucket_sizes = ("100kb",) if metafunc.definition.name == "test_loads_peak" else sizes()
    cases = [
        pytest.param(fmt.value, size, rival, id=f"{fmt.value}-{size}-{rival}")
        for fmt, rivals in matrix.items()
        for size in bucket_sizes
        for rival in rivals
        if (fmt.value, rival) not in slow or size != "10mb"
    ]
    metafunc.parametrize(("fmt", "size", "rival"), cases)


@pytest.fixture(scope="session")
def corpus_files(tmp_path_factory: pytest.TempPathFactory) -> dict[tuple[str, str], Path]:
    """Materialize file-based payloads once: the async file variants need real paths on disk."""
    root = tmp_path_factory.mktemp("corpus")
    files: dict[tuple[str, str], Path] = {}
    for fmt, ext in _FILE_EXT.items():
        for size in ("100kb", "10mb"):
            path = root / f"corpus-{fmt}-{size}{ext}"
            path.write_bytes(payload(fmt, size))
            files[fmt.value, size] = path
    return files
