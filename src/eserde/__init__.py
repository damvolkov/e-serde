"""e-serde — fast, type-safe structured data loading with pluggable codecs.

The one façade in the tree: `import eserde; eserde.loads(...)`. Everything else is
reached through its path (`eserde.backends.native.yaml`), never re-exported.
"""

from importlib.metadata import PackageNotFoundError, version

from eserde.backends.registry import CodecRegistry, default_registry
from eserde.infra.errors import (
    CodecError,
    DumpError,
    EncoderError,
    FormatError,
    LoaderError,
    LoadError,
)
from eserde.infra.formats import Format
from eserde.logic.api import adump, adumps, aload, aloads, dump, dumps, load, loads

try:
    __version__: str = version("e-serde")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"

__all__ = [
    "CodecError",
    "CodecRegistry",
    "DumpError",
    "EncoderError",
    "Format",
    "FormatError",
    "LoadError",
    "LoaderError",
    "__version__",
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
