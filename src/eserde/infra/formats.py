"""Supported structured data formats.

Lives in `infra` (not `logic`) because both backends and the facade import it;
keeping it here enforces the layering: `infra` <- `backends` <- `logic`.
"""

from __future__ import annotations

from enum import StrEnum, auto
from typing import TYPE_CHECKING

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


def detect_format(path: Path) -> Format | None:
    """Infer Format from file extension. Returns None when no extension matches."""
    return _EXTENSION_TO_FORMAT.get(path.suffix.lower())
