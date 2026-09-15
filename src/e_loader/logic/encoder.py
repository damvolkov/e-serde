"""Jsonable encoder — canonicalizes arbitrary Python objects to a JSON-compatible primitive tree.

Equivalent in spirit to FastAPI's `jsonable_encoder`. Uses `plum-dispatch` for type-based
dispatch. The output of `encode` is always safe to feed into any `Codec.dumps`.
"""

from __future__ import annotations

import base64
import dataclasses
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import PurePath
from typing import Any
from uuid import UUID

from plum import dispatch

from e_loader.infra.errors import EncoderError

type Jsonable = None | bool | int | float | str | list[Any] | dict[str, Any]


@dispatch
def encode(obj: None) -> None:
    return obj


@dispatch
def encode(obj: bool | int | float | str) -> bool | int | float | str:  # noqa: F811
    return obj


@dispatch
def encode(obj: bytes | bytearray) -> str:  # noqa: F811
    return base64.b64encode(obj).decode("ascii")


@dispatch
def encode(obj: dict) -> dict[str, Any]:  # noqa: F811
    return {_jsonable_key(k): encode(v) for k, v in obj.items()}


@dispatch
def encode(obj: list | tuple | set | frozenset) -> list[Any]:  # noqa: F811
    return [encode(item) for item in obj]


@dispatch
def encode(obj: range) -> list[int]:  # noqa: F811
    return list(obj)


@dispatch
def encode(obj: datetime | date | time) -> str:  # noqa: F811
    return obj.isoformat()


@dispatch
def encode(obj: timedelta) -> float:  # noqa: F811
    return obj.total_seconds()


@dispatch
def encode(obj: UUID | Decimal | PurePath) -> str:  # noqa: F811
    return str(obj)


@dispatch
def encode(obj: complex) -> dict[str, float]:  # noqa: F811
    return {"real": obj.real, "imag": obj.imag}


@dispatch(precedence=1)
def encode(obj: Enum) -> Any:  # noqa: F811
    return encode(obj.value)


@dispatch
def encode(obj: object) -> Any:  # noqa: F811
    """Fallback for pydantic models, dataclasses, and objects with `__dict__`."""
    if (model_dump := getattr(obj, "model_dump", None)) is not None and callable(model_dump):
        return encode(model_dump(mode="json"))
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return encode(dataclasses.asdict(obj))
    raise EncoderError(f"cannot encode object of type {type(obj).__name__!r}")


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