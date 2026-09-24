"""CSV/TSV codecs — `csv` crate (BurntSushi, RFC 4180) via the native extension.

Documents decode to `list[dict]`: the header names the columns and every column is
type-inferred across its values exactly like polars (empty fields are `null`,
integers past i64 stay exact, bools demote mixed columns to strings). Encoding
requires a non-empty list of uniform mappings; the first record's keys are the header.

Streaming (`iloads`/`idumps`) iterates one record at a time; without the whole file
the inference is per cell, so mixed-kind columns may vary row to row.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from eserde import _native
from eserde.backends.base import NativeCodec
from eserde.infra.errors import LoadError
from eserde.infra.formats import Format

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path


class _NativeCsvStreaming(NativeCodec):
    """Shared streaming surface: record-at-a-time iteration over the `csv` crate."""

    def iterloads(self, data: bytes) -> Iterator[Any]:
        return self._guarded(self._create(lambda: self.backend.stream(data)))

    def iterload_path(self, path: Path) -> Iterator[Any]:
        return self._guarded(self._create(lambda: self.backend.stream_at(str(path))))

    def _create(self, open_stream: Any) -> Iterator[Any]:
        try:
            return open_stream()
        except ValueError as exc:
            msg = f"{self.format.value} decode failed: {exc}"
            raise LoadError(msg) from exc

    def _guarded(self, rows: Iterator[Any]) -> Iterator[Any]:
        while True:
            try:
                row = next(rows)
            except StopIteration:
                return
            except ValueError as exc:
                msg = f"{self.format.value} decode failed: {exc}"
                raise LoadError(msg) from exc
            yield row

    def iterdumps(self, obj: Iterable[Any]) -> Iterator[bytes]:
        rows = iter(obj)
        first = next(rows)
        header = list(first.keys())
        yield self.backend.dumps_header(header).encode()
        yield self.backend.dumps_row(header, 0, first).encode()
        for number, row in enumerate(rows, 1):
            yield self.backend.dumps_row(header, number, row).encode()


class NativeCsvCodec(_NativeCsvStreaming):
    """RFC 4180 loader/dumper backed by the `csv` Rust crate, comma-delimited."""

    format: ClassVar[Format] = Format.CSV
    backend: ClassVar = _native.csv


class NativeTsvCodec(_NativeCsvStreaming):
    """RFC 4180 loader/dumper backed by the `csv` Rust crate, tab-delimited."""

    format: ClassVar[Format] = Format.TSV
    backend: ClassVar = _native.tsv
