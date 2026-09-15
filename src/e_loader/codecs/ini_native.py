"""Native INI codec backed by Rust + configparser.

This is a placeholder for the native Rust INI codec that will be implemented
in crates/e-loader-ini. For now it uses the stdlib implementation as a fallback.
"""

from __future__ import annotations

import io
from configparser import ConfigParser
from configparser import Error as ConfigParserError
from typing import Any, ClassVar

from e_loader.errors import DumpError, LoadError
from e_loader.logic.formats import Format


class NativeIniCodec:
    """Native Rust-backed INI codec (placeholder - will be implemented in v0.2)."""

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