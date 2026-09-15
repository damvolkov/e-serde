"""JSON codec backed by `orjson` (Rust + serde_json + CPython-API hand-tuning)."""

from __future__ import annotations

from importlib.util import find_spec
from typing import Any, ClassVar

import orjson

from e_loader.infra.errors import DumpError, LoadError
from e_loader.logic.formats import Format


_HAS_NUMPY = find_spec("numpy") is not None
_DUMP_OPT = orjson.OPT_SERIALIZE_DATACLASS | orjson.OPT_NAIVE_UTC | orjson.OPT_NON_STR_KEYS
if _HAS_NUMPY:
    _DUMP_OPT |= orjson.OPT_SERIALIZE_NUMPY


class OrjsonCodec:
    """orjson-backed JSON codec. Returns `bytes` directly — no UTF-8 re-encoding."""

    format: ClassVar[Format] = Format.JSON

    def loads(self, data: bytes) -> Any:
        try:
            return orjson.loads(data)
        except orjson.JSONDecodeError as exc:
            raise LoadError(f"orjson decode failed: {exc}") from exc

    def dumps(self, obj: Any) -> bytes:
        try:
            return orjson.dumps(obj, option=_DUMP_OPT)
        except (TypeError, orjson.JSONEncodeError) as exc:
            raise DumpError(f"orjson encode failed: {exc}") from exc