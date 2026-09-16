"""JSON codec — `msgspec.json` (C). Fastest-in-class decode, no external deps.

The facade routes `type=` validation through `msgspec.convert` regardless of format;
for JSON that means the plain tree here is the input to the same validated pipeline.
"""

from __future__ import annotations

from typing import Any, ClassVar

import msgspec

from eserde.infra.errors import DumpError, LoadError
from eserde.infra.formats import Format


class MsgspecJsonCodec:
    """JSON loader/dumper backed by msgspec's C decoder."""

    format: ClassVar[Format] = Format.JSON

    def loads(self, data: bytes) -> Any:
        try:
            return msgspec.json.decode(data)
        except (UnicodeDecodeError, ValueError) as exc:
            msg = f"json decode failed: {exc}"
            raise LoadError(msg) from exc

    def dumps(self, obj: Any) -> bytes:
        try:
            return msgspec.json.encode(obj)
        except (TypeError, msgspec.EncodeError) as exc:
            msg = f"json encode failed: {exc}"
            raise DumpError(msg) from exc
