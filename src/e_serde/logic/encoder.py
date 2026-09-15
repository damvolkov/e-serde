"""Jsonable encoder — canonicalizes arbitrary Python objects to a JSON-compatible tree.

Stdlib `functools.singledispatch`; output is safe to feed into any backend `dumps`.
The facade applies it before encoding, so every format shares one normalization contract
(bytes -> base64 str, datetime -> ISO str, Enum -> value, dataclass/pydantic -> dict).
"""

from __future__ import annotations

import base64
import dataclasses
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from functools import singledispatch
from pathlib import PurePath
from typing import Any
from uuid import UUID

import msgspec

from e_serde.infra.errors import EncoderError

type Jsonable = bool | int | float | str | list[Any] | dict[str, Any] | None


@singledispatch
def encode(obj: Any) -> Any:
    """Fallback for msgspec Structs, pydantic models, dataclasses and exotic objects."""
    if (model_dump := getattr(obj, "model_dump", None)) is not None and callable(model_dump):
        return encode(model_dump(mode="json"))
    if isinstance(obj, msgspec.Struct):
        return encode(msgspec.to_builtins(obj))
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return encode(dataclasses.asdict(obj))
    msg = f"cannot encode object of type {type(obj).__name__!r}"
    raise EncoderError(msg)


@encode.register(type(None))
def _encode_none(obj: None) -> None:
    return obj


@encode.register(bool)
@encode.register(int)
@encode.register(float)
@encode.register(str)
def _encode_passthrough(obj: Any) -> Any:
    return obj


@encode.register(bytes)
@encode.register(bytearray)
def _encode_bytes(obj: bytes | bytearray) -> str:
    return base64.b64encode(obj).decode("ascii")


@encode.register(dict)
def _encode_dict(obj: dict[Any, Any]) -> dict[str, Any]:
    return {_jsonable_key(k): encode(v) for k, v in obj.items()}


@encode.register(list)
@encode.register(tuple)
@encode.register(set)
@encode.register(frozenset)
@encode.register(range)
def _encode_sequence(obj: Any) -> list[Any]:
    return [encode(item) for item in obj]


@encode.register(datetime)
@encode.register(date)
@encode.register(time)
def _encode_temporal(obj: datetime | date | time) -> str:
    return obj.isoformat()


@encode.register(timedelta)
def _encode_timedelta(obj: timedelta) -> float:
    return obj.total_seconds()


@encode.register(UUID)
@encode.register(PurePath)
@encode.register(Decimal)
def _encode_textual(obj: Any) -> str:
    return str(obj)


@encode.register(complex)
def _encode_complex(obj: complex) -> dict[str, float]:
    return {"real": obj.real, "imag": obj.imag}


@encode.register(Enum)
def _encode_enum(obj: Enum) -> Any:
    return encode(obj.value)


def _jsonable_key(key: Any) -> str:
    """Coerce a dict key to its JSON-compatible string representation."""
    match key:
        case str():
            return key
        case bool() | int() | float():
            return str(key)
        case None:
            return "null"
        case _:
            encoded = encode(key)
            return encoded if isinstance(encoded, str) else str(encoded)
