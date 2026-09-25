"""JSON codec — `msgspec.json` (C). Fastest-in-class decode, no external deps.

The facade routes `type=` validation through `msgspec.convert` regardless of format;
for JSON that means the plain tree here is the input to the same validated pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

import msgspec

from eserde.infra.errors import DumpError, LoadError
from eserde.infra.formats import Format

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path


class MsgspecJsonCodec:
    """JSON loader/dumper backed by msgspec's C decoder."""

    format: ClassVar[Format] = Format.JSON

    def _common_lines(self, lines: Iterable[bytes]) -> Iterator[Any]:
        return (self.loads(line) for line in lines if line.strip())

    ############################################################

    def loads(self, data: bytes) -> Any:
        try:
            return msgspec.json.decode(data)
        except (UnicodeDecodeError, ValueError) as exc:
            msg = f"json decode failed: {exc}"
            raise LoadError(msg) from exc

    def dumps(self, obj: Any) -> bytes:
        try:
            return msgspec.json.encode(obj)
        except (TypeError, msgspec.EncodeError, UnicodeEncodeError) as exc:
            msg = f"json encode failed: {exc}"
            raise DumpError(msg) from exc

    def iterloads(self, data: bytes) -> Iterator[Any]:
        return self._common_lines(data.splitlines())

    def iterload_path(self, path: Path) -> Iterator[Any]:
        with path.open("rb") as handle:
            yield from self._common_lines(handle)

    def iterdumps(self, obj: Iterable[Any]) -> Iterator[bytes]:
        for record in obj:
            yield self.dumps(record) + b"\n"
