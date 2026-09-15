"""Supported structured data formats."""

from __future__ import annotations

from enum import StrEnum, auto
from pathlib import Path


class Format(StrEnum):
    """Canonical format identifier. Maps 1:1 to a backend loader/dumper pair."""

    JSON = auto()
    YAML = auto()
    TOML = auto()
    INI = auto()


_EXTENTION_TO_FORMAT: dict[str, Format] = {
    ".json": Format.JSON,
    ".yaml": Format.YAML,
    ".yml": Format.YAML,
    ".toml": Format.TOML,
    ".ini": Format.INI,
    ".cfg": Format.INI,
}


def detect_format(path: Path) -> Format | None:
    """Infer Format from file extension. Returns None when no extension matches."""
    return _EXTENTION_TO_FORMAT.get(path.suffix.lower())