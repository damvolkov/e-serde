"""CSV/TSV codec contract: headered records, polars-style inference, RFC 4180 quoting."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import msgspec
import pytest

from eserde import DumpError, LoadError
from eserde.infra.formats import Format
from eserde.logic.api import aloads, dumps, loads

if TYPE_CHECKING:
    from pathlib import Path

_ROWS = [
    {"id": 1, "name": "Turul", "price": 9.5, "active": True, "note": None},
    {"id": 2, "name": 'a"b,c', "price": None, "active": False, "note": "multi\nline"},
]


@pytest.mark.parametrize("fmt", [Format.CSV, Format.TSV])
def test_roundtrip_preserves_inference(fmt: Format) -> None:
    assert loads(dumps(_ROWS, format=fmt), format=fmt) == _ROWS


@pytest.mark.parametrize("fmt", [Format.CSV, Format.TSV])
def test_empty_field_is_null(fmt: Format) -> None:
    raw = b"a,b\n1,\n" if fmt is Format.CSV else b"a\tb\n1\t\n"
    assert loads(raw, format=fmt) == [{"a": 1, "b": None}]


@pytest.mark.parametrize("fmt", [Format.CSV, Format.TSV])
def test_column_kinds(fmt: Format) -> None:
    sep = b"," if fmt is Format.CSV else b"\t"
    lines = [
        b"i,f,big,t,s,mixed,allnull",
        b"1,1.5,99000000000000000000000,true,x,1,",
        b"2,2,3,false,y,z,",
    ]
    raw = b"\n".join(line.replace(b",", sep) for line in lines) + b"\n"
    rows = loads(raw, format=fmt)
    assert [r["i"] for r in rows] == [1, 2]
    assert [r["f"] for r in rows] == [1.5, 2.0]
    assert rows[0]["big"] == 99_000_000_000_000_000_000_000
    assert rows[1]["big"] == 3
    assert rows[0]["t"] is True
    assert rows[1]["t"] is False
    assert [r["s"] for r in rows] == ["x", "y"]
    assert [r["mixed"] for r in rows] == ["1", "z"]
    assert [r["allnull"] for r in rows] == [None, None]


@pytest.mark.parametrize("fmt", [Format.CSV, Format.TSV])
def test_inf_token_infers_float_column(fmt: Format) -> None:
    raw = b"k\ninf\n"
    rows = loads(raw, format=fmt)
    assert math.isinf(rows[0]["k"])
    assert rows[0]["k"] > 0


@pytest.mark.parametrize("fmt", [Format.CSV, Format.TSV])
def test_bom_tolerated(fmt: Format) -> None:
    assert loads(b"\xef\xbb\xbf" + b"k\n1\n", format=fmt) == [{"k": 1}]


def test_rfc4180_quoting_multiline_and_crlf() -> None:
    raw = b'a,b\r\n"x\ny","he said ""hi"""\r\n'
    assert loads(raw, format=Format.CSV) == [{"a": "x\ny", "b": 'he said "hi"'}]


def test_duplicate_headers_rejected() -> None:
    with pytest.raises(LoadError, match="duplicate column"):
        loads(b"a,a\n1,2\n", format=Format.CSV)


def test_ragged_rows_rejected() -> None:
    with pytest.raises(LoadError, match="row 2 has 1 fields"):
        loads(b"a,b\n1\n", format=Format.CSV)
    with pytest.raises(LoadError, match="row 2 has 3 fields"):
        loads(b"a,b\n1,2,3\n", format=Format.CSV)


def test_headerless_document_rejected() -> None:
    with pytest.raises(LoadError, match="no header"):
        loads(b"\n", format=Format.CSV)
    with pytest.raises(LoadError, match="no header"):
        loads(b"", format=Format.CSV)


def test_dumps_requires_records() -> None:
    with pytest.raises(DumpError, match="lists of records"):
        dumps({"k": 1}, format=Format.CSV)
    with pytest.raises(DumpError, match="at least one record"):
        dumps([], format=Format.CSV)
    with pytest.raises(DumpError, match="not a csv scalar"):
        dumps([{"a": [1]}], format=Format.CSV)


def test_dumps_requires_uniform_records() -> None:
    with pytest.raises(DumpError, match="missing column"):
        dumps([{"a": 1, "b": 2}, {"a": 3, "c": 4}], format=Format.CSV)
    with pytest.raises(DumpError, match="record 2 has 1 keys"):
        dumps([{"a": 1, "b": 2}, {"a": 3}], format=Format.CSV)


def test_dumps_header_order_and_escapes() -> None:
    assert dumps([{"b": 1, "a": "x\ny"}], format=Format.CSV) == b'b,a\n1,"x\ny"\n'


class _Row(msgspec.Struct, frozen=True):
    id: int
    name: str


def test_typed_conversion() -> None:
    rows = loads(b"id,name\n1,Turul\n2,Ainulindale\n", format=Format.CSV, type=list[_Row])
    assert rows == [_Row(1, "Turul"), _Row(2, "Ainulindale")]


def test_detect_by_extension(tmp_path: Path) -> None:
    (tmp_path / "data.csv").write_bytes(b"k\n1\n")
    (tmp_path / "data.tsv").write_bytes(b"k\tv\n1\t2\n")
    assert loads(tmp_path / "data.csv") == [{"k": 1}]
    assert loads(tmp_path / "data.tsv") == [{"k": 1, "v": 2}]


async def test_async_csv() -> None:
    assert await aloads(b"a,b\n1,x\n", format=Format.CSV) == [{"a": 1, "b": "x"}]


def test_delimiters_are_not_interchangeable() -> None:
    assert loads(b"a\tb\n1\t2\n", format=Format.TSV) == [{"a": 1, "b": 2}]
    assert loads(b'a,b\n1,"x"\n', format=Format.CSV) == [{"a": 1, "b": "x"}]
