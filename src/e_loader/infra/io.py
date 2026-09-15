"""Async I/O helpers — kept isolated so codecs stay sync and pure."""

from __future__ import annotations

from pathlib import Path

import aiofiles


async def aread_bytes(path: Path) -> bytes:
    """Async equivalent of `Path.read_bytes`."""
    async with aiofiles.open(path, mode="rb") as fh:
        return await fh.read()


async def awrite_bytes(path: Path, data: bytes) -> None:
    """Async equivalent of `Path.write_bytes`."""
    async with aiofiles.open(path, mode="wb") as fh:
        await fh.write(data)