"""Streaming contract: iloads/idumps and their async twins, per codec capability."""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

import pytest

from eserde import Format
from eserde.backends.registry import default_registry
from eserde.infra.errors import FormatError, LoadError
from eserde.infra.protocols import StreamingCodec
from eserde.logic.api import aidumps, ailoads, idumps, iloads

if TYPE_CHECKING:
    from pathlib import Path

_NDJSON = b'{"a": 1}\n\n{"a": 2}\n'
_CSV = b"id,v\n1,x\n2,y\n"
_TSV = b"id\tv\n1\tx\n2\ty\n"
_STREAMABLE = {Format.JSON, Format.JSONC, Format.CSV, Format.TSV}


def test_registry_streaming_matches_format_set() -> None:
    streamable = {fmt for fmt in default_registry.formats() if isinstance(default_registry.get(fmt), StreamingCodec)}
    assert streamable == _STREAMABLE


def test_iloads_json_skips_blank_lines() -> None:
    assert list(iloads(_NDJSON, format=Format.JSON)) == [{"a": 1}, {"a": 2}]


def test_iloads_jsonc_accepts_line_comments() -> None:
    assert list(iloads(b'{"a": 1} // one\n{"a": 2} // two\n', format=Format.JSONC)) == [{"a": 1}, {"a": 2}]


def test_iloads_partial_document_raises_on_iteration() -> None:
    iterator = iloads(b'{"a": ', format=Format.JSON)
    with pytest.raises(LoadError):
        next(iterator)


def test_iloads_non_streamable_raises_with_menu() -> None:
    with pytest.raises(FormatError, match=r"does not support streaming.*csv · json · jsonc · tsv"):
        iloads(b"k: 1", format=Format.YAML)
    with pytest.raises(FormatError, match="does not support streaming"):
        iloads(b"[s]\nk = 1\n", format=Format.TOML)
    with pytest.raises(FormatError, match="does not support streaming"):
        iloads(b"[s]\nk = 1\n", format=Format.INI)


def test_iloads_csv_types_per_cell() -> None:
    rows = list(iloads(b"a,b\n1,x\ny,2\n", format=Format.CSV))
    assert rows == [{"a": 1, "b": "x"}, {"a": "y", "b": 2}]


def test_iloads_csv_multiline_quoted_record() -> None:
    rows = list(iloads(b'a\n"l1\nl2"\n', format=Format.CSV))
    assert rows == [{"a": "l1\nl2"}]


def test_iloads_csv_ragged_row_raises_mid_stream() -> None:
    with pytest.raises(LoadError, match="row 4"):
        list(iloads(_CSV + b"3\n", format=Format.CSV))


def test_iloads_csv_rejects_ragged_row_at_path(tmp_path: Path) -> None:
    (tmp_path / "bad.csv").write_bytes(b"a,b\n1\n")
    with pytest.raises(LoadError, match="row 2"):
        list(iloads(tmp_path / "bad.csv"))


def test_iloads_detects_ndjson_by_extension(tmp_path: Path) -> None:
    (tmp_path / "x.ndjson").write_bytes(_NDJSON)
    (tmp_path / "y.jsonl").write_bytes(_NDJSON)
    assert len(list(iloads(tmp_path / "x.ndjson"))) == 2
    assert len(list(iloads(tmp_path / "y.jsonl"))) == 2


def test_iloads_path_streams_csv(tmp_path: Path) -> None:
    (tmp_path / "big.csv").write_bytes(b"id\n" + b"".join(b"%d\n" % i for i in range(3000)))
    assert [r["id"] for r in iloads(tmp_path / "big.csv")][-1] == 2999


def test_idumps_json_lines_end_to_end() -> None:
    chunks = list(idumps([{"a": 1}, {"b": 2}], format=Format.JSON))
    assert b"".join(chunks) == b'{"a":1}\n{"b":2}\n'
    assert list(iloads(b"".join(chunks), format=Format.JSON)) == [{"a": 1}, {"b": 2}]


def test_idumps_csv_emits_single_header_and_lazily_consumes() -> None:
    infinite = ({"n": i} for i in itertools.count())
    chunks = list(itertools.islice(idumps(infinite, format=Format.CSV), 4))
    assert b"".join(chunks) == b"n\n0\n1\n2\n"


def test_idumps_csv_rejects_missing_column() -> None:
    with pytest.raises(Exception, match="missing column"):
        list(idumps([{"a": 1, "b": 2}, {"a": 3, "c": 4}], format=Format.CSV))


def test_idumps_rejects_unstreamable() -> None:
    with pytest.raises(FormatError, match="does not support streaming"):
        idumps([{"a": 1}], format=Format.YAML)


async def test_ailoads_matches_iloads(tmp_path: Path) -> None:
    (tmp_path / "t.csv").write_bytes(_CSV)
    sync = list(iloads(tmp_path / "t.csv"))
    assert [r async for r in ailoads(tmp_path / "t.csv")] == sync
    assert [r async for r in ailoads(_NDJSON, format=Format.JSON)] == list(iloads(_NDJSON, format=Format.JSON))


async def test_ailoads_batches_across_boundary(tmp_path: Path) -> None:
    payload = b"k\n" + b"\n".join(b"%d" % i for i in range(2500)) + b"\n"
    (tmp_path / "n.csv").write_bytes(payload)
    assert len([r async for r in ailoads(tmp_path / "n.csv")]) == 2500


async def test_aidumps_sync_source_and_roundtrip() -> None:
    rows = [{"id": 1, "v": "x"}, {"id": 2, "v": "y"}]
    out = b"".join([c async for c in aidumps(iter(rows), format=Format.CSV)])
    assert out == b"id,v\n1,x\n2,y\n"
    assert [r async for r in ailoads(out, format=Format.CSV)] == rows


async def test_aidumps_async_source() -> None:
    async def source():
        for i in range(3):
            yield {"i": i}

    out = b"".join([c async for c in aidumps(source(), format=Format.JSON)])
    assert out == b'{"i":0}\n{"i":1}\n{"i":2}\n'


async def test_aidumps_rejects_unstreamable_eagerly() -> None:
    with pytest.raises(FormatError, match="does not support streaming"):
        aidumps([{"a": 1}], format=Format.TOML)


def test_sniffing_applies_to_iloads() -> None:
    assert list(iloads(b'{"a": 1}\n{"a": 2}\n')) == [{"a": 1}, {"a": 2}]
    with pytest.raises(FormatError, match="cannot infer"):
        iloads(b"k: 1\n")
