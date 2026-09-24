"""Stubs for the compiled Rust extension `eserde._native`.

One submodule per format; `loads` accepts `str` (UTF-8 decoding happens in the Python codec layer); `dumps` consumes a
JSON-compatible tree and returns `str`. Failures surface as `ValueError`/`TypeError`.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

class _FormatModule:
    def loads(self, data: str) -> Any: ...
    def dumps(self, obj: Any) -> str: ...

class _CsvStream:
    header: list[str]
    def __iter__(self) -> Iterator[Any]: ...
    def __next__(self) -> Any: ...

class _CsvModule:
    def loads(self, data: str) -> Any: ...
    def dumps(self, obj: Any) -> str: ...
    def stream(self, data: bytes) -> _CsvStream: ...
    def stream_at(self, path: str) -> _CsvStream: ...
    def dumps_header(self, header: list[str]) -> str: ...
    def dumps_row(self, header: list[str], number: int, row: Any) -> str: ...

yaml: _FormatModule
csv: _CsvModule
tsv: _CsvModule
toml: _FormatModule
jsonc: _FormatModule
ini: _FormatModule
