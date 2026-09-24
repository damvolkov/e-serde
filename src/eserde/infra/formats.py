"""Supported structured data formats.

Lives in `infra` (not `logic`) because both backends and the facade import it;
keeping it here enforces the layering: `infra` <- `backends` <- `logic`.
"""

from __future__ import annotations

import re
from enum import StrEnum, auto
from typing import TYPE_CHECKING

from eserde.infra.errors import FormatError

if TYPE_CHECKING:
    from pathlib import Path


class Format(StrEnum):
    """Canonical format identifier. Maps 1:1 to a codec in the default registry."""

    JSON = auto()
    JSONC = auto()
    YAML = auto()
    TOML = auto()
    INI = auto()
    CSV = auto()
    TSV = auto()


_EXTENSION_TO_FORMAT: dict[str, Format] = {
    ".json": Format.JSON,
    ".ndjson": Format.JSON,
    ".jsonl": Format.JSON,
    ".jsonc": Format.JSONC,
    ".yaml": Format.YAML,
    ".yml": Format.YAML,
    ".toml": Format.TOML,
    ".ini": Format.INI,
    ".cfg": Format.INI,
    ".conf": Format.INI,
    ".csv": Format.CSV,
    ".tsv": Format.TSV,
}

_UTF8_BOM = b"\xef\xbb\xbf"
_WHITESPACE = b" \t\r\n\v\f"
_SNIFF_HEAD = 4096  # comment probes look at the head only: jsonc documents announce themselves early
_JSON_TOKEN = re.compile(rb'"(?:[^"\\]|\\.)*"|//[^\n]*|/\*.*?\*/', re.DOTALL)  # string | line comment | block comment


def detect_format(path: Path) -> Format | None:
    """Infer Format from file extension. Returns None when no extension matches."""
    return _EXTENSION_TO_FORMAT.get(path.suffix.lower())


def coerce_format(value: Format | str) -> Format:
    """Accept a `Format` member or its plain-string name; reject anything else loudly."""
    try:
        return Format(value)
    except ValueError:
        msg = f"unknown format {value!r} — expected one of: {' · '.join(Format)}"
        raise FormatError(msg) from None


def sniff_format(data: bytes) -> Format | None:
    """Strict content sniffing: answers only where no doubt is possible.

    Only JSON objects are sniffable: `{` (whitespace tolerated) immediately followed by
    `"` cannot be YAML flow (bare keys), TOML, INI or CSV. Comments in the head resolve
    the JSON-vs-JSONC tie — JSONC parses pure JSON too, so a false JSONC is harmless
    while a false JSON would break. Everything else — bare arrays included: `[` is both
    a JSON array and a TOML/INI section — is refused by design and must declare its
    format. New formats join by widening this table, never the facade.
    """
    body = data.removeprefix(_UTF8_BOM).lstrip(_WHITESPACE)
    match body[:1]:
        case b"/" if body[:2] in (b"//", b"/*"):
            return Format.JSONC
        case b"{":
            match body[1:].lstrip(_WHITESPACE)[:1]:
                case b"/":
                    return Format.JSONC
                case b'"' | b"}":
                    return Format.JSONC if _has_comment(body[:_SNIFF_HEAD]) else Format.JSON
                case _:
                    return None
        case _:
            return None


def _has_comment(head: bytes) -> bool:
    """Line scan honoring strings and escapes: a `//` inside a value is not a comment."""
    return any(token.group(0)[:1] == b"/" for token in _JSON_TOKEN.finditer(head))
