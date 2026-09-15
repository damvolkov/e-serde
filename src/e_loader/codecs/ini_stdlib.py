"""INI codec backed by stdlib `configparser`.

Placeholder until the native Rust INI codec lands. INI files are small enough that
Python's `configparser` is rarely a bottleneck; this exists purely to slot into the
Codec contract and provide a working default.
"""

from __future__ import annotations

import io
from configparser import ConfigParser
from configparser import Error as ConfigParserError
from typing import Any, ClassVar

from e_loader.infra.errors import DumpError, LoadError
from e_loader.logic.formats import Format


class ConfigparserCodec:
    """Stdlib `configparser` codec. Returns nested `dict[str, dict[str, str]]`."""

    format: ClassVar[Format] = Format.INI

    def loads(self, data: bytes) -> dict[str, dict[str, str]]:
        parser = ConfigParser()
        try:
            parser.read_string(data.decode("utf-8"))
        except (UnicodeDecodeError, ConfigParserError) as exc:
            raise LoadError(f"configparser decode failed: {exc}") from exc
        return {section: dict(parser[section]) for section in parser.sections()}

    def dumps(self, obj: Any) -> bytes:
        if not isinstance(obj, dict):
            raise DumpError(f"configparser dumps expects dict, got {type(obj).__name__}")
        parser = ConfigParser()
        try:
            for section, items in obj.items():
                parser[section] = {str(k): str(v) for k, v in items.items()}
        except (TypeError, AttributeError, ConfigParserError) as exc:
            raise DumpError(f"configparser encode failed: {exc}") from exc
        buffer = io.StringIO()
        parser.write(buffer)
        return buffer.getvalue().encode("utf-8")