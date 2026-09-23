"""CSV/TSV codecs — `csv` crate (BurntSushi, RFC 4180) via the native extension.

Documents decode to `list[dict]`: the header names the columns and every column is
type-inferred across its values exactly like polars (empty fields are `null`,
integers past i64 stay exact, bools demote mixed columns to strings). Encoding
requires a non-empty list of uniform mappings; the first record's keys are the header.
"""

from __future__ import annotations

from typing import ClassVar

from eserde import _native
from eserde.backends.base import NativeCodec
from eserde.infra.formats import Format


class NativeCsvCodec(NativeCodec):
    """RFC 4180 loader/dumper backed by the `csv` Rust crate, comma-delimited."""

    format: ClassVar[Format] = Format.CSV
    backend: ClassVar = _native.csv


class NativeTsvCodec(NativeCodec):
    """RFC 4180 loader/dumper backed by the `csv` Rust crate, tab-delimited."""

    format: ClassVar[Format] = Format.TSV
    backend: ClassVar = _native.tsv
