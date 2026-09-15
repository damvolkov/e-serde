"""Shared utilities for codec implementations.

Codecs operate strictly on `bytes`. Backends that consume/produce `str` are wrapped here
to keep the interface uniform.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from e_loader.infra.errors import DumpError, LoadError


def wrap_load_str(backend: Callable[[str], Any], encoding: str = "utf-8") -> Callable[[bytes], Any]:
    """Adapt a `str`-consuming backend loader to operate on `bytes`."""

    def _loads(data: bytes) -> Any:
        try:
            return backend(data.decode(encoding))
        except (UnicodeDecodeError, ValueError) as exc:
            raise LoadError(f"{backend.__module__}.{backend.__name__} loads failed: {exc}") from exc

    return _loads


def wrap_dump_str(backend: Callable[[Any], str], encoding: str = "utf-8") -> Callable[[Any], bytes]:
    """Adapt a `str`-producing backend dumper to return `bytes`."""

    def _dumps(obj: Any) -> bytes:
        try:
            return backend(obj).encode(encoding)
        except (TypeError, ValueError) as exc:
            raise DumpError(f"{backend.__module__}.{backend.__name__} dumps failed: {exc}") from exc

    return _dumps