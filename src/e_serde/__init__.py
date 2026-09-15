"""e-serde — fast, type-safe structured data loading with pluggable codecs."""

from e_serde.backends import default_registry
from e_serde.backends.registry import CodecRegistry
from e_serde.infra.errors import (
    CodecError,
    DumpError,
    EncoderError,
    FormatError,
    LoaderError,
    LoadError,
)
from e_serde.infra.formats import Format
from e_serde.logic.api import adump, adumps, aload, aloads, dump, dumps, load, loads

__all__ = [
    "CodecError",
    "CodecRegistry",
    "DumpError",
    "EncoderError",
    "Format",
    "FormatError",
    "LoadError",
    "LoaderError",
    "adump",
    "adumps",
    "aload",
    "aloads",
    "default_registry",
    "dump",
    "dumps",
    "load",
    "loads",
]
