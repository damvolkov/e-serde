"""Jsonable encoder — canonicalizes arbitrary Python objects to a JSON-compatible tree.

Leaf transforms live in a `functools.singledispatch` registry; the container walk lives
here, so per-call hooks thread through the traversal without global state: `encoders`
wins on exact type before any built-in rule, `default` is the last-resort fallback for
unknown types (json/orjson semantics). Output is safe to feed into any backend `dumps`.
"""

from __future__ import annotations

import base64
import dataclasses
from collections.abc import Callable, Mapping
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from functools import singledispatch
from pathlib import PurePath
from typing import Any
from uuid import UUID

import msgspec

from eserde.infra.errors import EncoderError

type Jsonable = bool | int | float | str | list[Any] | dict[str, Any] | None
type Default = Callable[[Any], Any]
type Encoders = Mapping[type, Callable[[Any], Any]]

_PASSTHROUGH: frozenset[type] = frozenset({bool, int, float, str})


##### PRIVATE #####


@dataclasses.dataclass(frozen=True, slots=True)
class _Hooks:
    default: Default | None = None
    encoders: Encoders = dataclasses.field(default_factory=dict)


@singledispatch
def _leaf(obj: Any) -> Any:
    """Duck-typed models for objects the walk cannot consume: pydantic, Struct, dataclass."""
    if (model_dump := getattr(obj, "model_dump", None)) is not None and callable(model_dump):
        return model_dump(mode="json")
    if isinstance(obj, msgspec.Struct):
        return msgspec.to_builtins(obj)
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    msg = f"cannot encode object of type {type(obj).__name__!r}"
    raise EncoderError(msg)


@_leaf.register(bytes)
@_leaf.register(bytearray)
def _leaf_bytes(obj: bytes | bytearray) -> str:
    return base64.b64encode(obj).decode("ascii")


@_leaf.register(datetime)
@_leaf.register(date)
@_leaf.register(time)
def _leaf_temporal(obj: datetime | date | time) -> str:
    return obj.isoformat()


@_leaf.register(timedelta)
def _leaf_timedelta(obj: timedelta) -> float:
    return obj.total_seconds()


@_leaf.register(UUID)
@_leaf.register(PurePath)
@_leaf.register(Decimal)
def _leaf_textual(obj: Any) -> str:
    return str(obj)


@_leaf.register(complex)
def _leaf_complex(obj: complex) -> dict[str, float]:
    return {"real": obj.real, "imag": obj.imag}


@_leaf.register(Enum)
def _leaf_enum(obj: Enum) -> Any:
    return obj.value


def _walk(obj: Any, hooks: _Hooks) -> Any:
    if obj is None or type(obj) in _PASSTHROUGH:
        return obj
    if (custom := hooks.encoders.get(type(obj))) is not None:
        return _walk(custom(obj), hooks)
    match obj:
        case Mapping():
            return {_key(key, hooks): _walk(value, hooks) for key, value in obj.items()}
        case bytes() | bytearray():
            return _walk(_leaf(obj), hooks)
        case list() | tuple() | set() | frozenset() | range():
            return [_walk(item, hooks) for item in obj]
        case _:
            return _walk(_resolve_leaf(obj, hooks), hooks)


def _resolve_leaf(obj: Any, hooks: _Hooks) -> Any:
    try:
        return _leaf(obj)
    except EncoderError:
        if hooks.default is None:
            raise
        return hooks.default(obj)


def _key(key: Any, hooks: _Hooks) -> str:
    match key:
        case str():
            return str(key)
        case bool() | int() | float():
            return str(key)
        case None:
            return "null"
        case _:
            return str(_walk(key, hooks))


##### PUBLIC #####


class Encoder:
    """Callable entry point: normalize `obj` into a Jsonable tree.

    `encoders` intercepts by exact type ahead of every built-in; `default` is consulted
    only when nothing matched, and its result is re-walked. `register` keeps the global
    `functools.singledispatch` extension point.
    """

    __slots__ = ("_leaf",)

    def __init__(self, leaf: Any) -> None:
        self._leaf = leaf

    def __call__(self, obj: Any, *, default: Default | None = None, encoders: Encoders | None = None) -> Any:
        return _walk(obj, _Hooks(default=default, encoders=encoders or {}))

    def register(self, cls: type | None = None, **kwargs: Any) -> Callable[[Any], Any]:
        """Bind a leaf transform for `cls`; usable bare as a decorator, like `singledispatch.register`."""
        return self._leaf.register(cls, **kwargs)


encode = Encoder(_leaf)
