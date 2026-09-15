"""Jsonable encoder dispatch coverage."""

from __future__ import annotations

import base64
import dataclasses
import enum
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import PurePosixPath
from uuid import UUID

import pytest

from e_loader.encoder import encode
from e_loader.errors import EncoderError


class _Color(enum.StrEnum):
    RED = "red"
    BLUE = "blue"


@dataclasses.dataclass(slots=True, frozen=True)
class _Point:
    x: int
    y: int


_PRIMITIVE_CASES: list[tuple[object, object]] = [
    (None, None),
    (True, True),
    (False, False),
    (1, 1),
    (1.5, 1.5),
    ("text", "text"),
]


@pytest.mark.parametrize(
    ("obj", "expected"),
    _PRIMITIVE_CASES,
    ids=["none", "bool-true", "bool-false", "int", "float", "str"],
)
async def test_encode_primitives_passthrough(obj: object, expected: object) -> None:
    assert encode(obj) == expected


async def test_encode_bytes_returns_base64() -> None:
    assert encode(b"hello") == base64.b64encode(b"hello").decode("ascii")


async def test_encode_bytearray_returns_base64() -> None:
    assert encode(bytearray(b"hello")) == base64.b64encode(b"hello").decode("ascii")


async def test_encode_dict_recurses() -> None:
    assert encode({"a": 1, "b": [2, 3]}) == {"a": 1, "b": [2, 3]}


async def test_encode_dict_coerces_non_string_keys() -> None:
    assert encode({1: "a", 2.5: "b"}) == {"1": "a", "2.5": "b"}


async def test_encode_list_and_tuple_and_set() -> None:
    assert encode([1, 2, 3]) == [1, 2, 3]
    assert encode((1, 2, 3)) == [1, 2, 3]
    assert encode(frozenset([1])) == [1]


async def test_encode_range() -> None:
    assert encode(range(3)) == [0, 1, 2]


async def test_encode_datetime() -> None:
    dt = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
    assert encode(dt) == "2026-05-13T12:00:00+00:00"


async def test_encode_date() -> None:
    assert encode(date(2026, 5, 13)) == "2026-05-13"


async def test_encode_time() -> None:
    assert encode(time(12, 30)) == "12:30:00"


async def test_encode_timedelta() -> None:
    assert encode(timedelta(seconds=90)) == 90.0


async def test_encode_uuid() -> None:
    uid = UUID("12345678-1234-5678-1234-567812345678")
    assert encode(uid) == "12345678-1234-5678-1234-567812345678"


async def test_encode_decimal() -> None:
    assert encode(Decimal("3.14159")) == "3.14159"


async def test_encode_path() -> None:
    assert encode(PurePosixPath("/tmp/foo")) == "/tmp/foo"


async def test_encode_complex() -> None:
    assert encode(2 + 3j) == {"real": 2.0, "imag": 3.0}


async def test_encode_strenum() -> None:
    assert encode(_Color.RED) == "red"


async def test_encode_dataclass() -> None:
    assert encode(_Point(1, 2)) == {"x": 1, "y": 2}


async def test_encode_nested_combination() -> None:
    payload = {"point": _Point(1, 2), "color": _Color.BLUE, "tags": {"a", "b"}}
    encoded = encode(payload)
    assert encoded["point"] == {"x": 1, "y": 2}
    assert encoded["color"] == "blue"
    assert sorted(encoded["tags"]) == ["a", "b"]


async def test_encode_unsupported_raises() -> None:
    class _Opaque:
        __slots__ = ()

    with pytest.raises(EncoderError):
        encode(_Opaque())
