"""Async I/O helpers — stdlib only (asyncio.to_thread); codecs stay sync and pure.

Native Rust parsing releases the GIL for the parse step, so offloading decode to a
worker thread gives real parallelism for large documents.
"""

from __future__ import annotations

from asyncio import to_thread
from typing import TYPE_CHECKING, BinaryIO

if TYPE_CHECKING:
    from pathlib import Path


async def aread_bytes(path: Path) -> bytes:
    """Async equivalent of `Path.read_bytes`."""
    return await to_thread(path.read_bytes)


async def awrite_bytes(path: Path, data: bytes) -> None:
    """Async equivalent of `Path.write_bytes`."""
    await to_thread(path.write_bytes, data)


async def aread_handle(handle: BinaryIO) -> bytes:
    """Async read of an already-open binary file object."""
    return await to_thread(handle.read)
