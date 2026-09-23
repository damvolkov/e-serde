"""Stubs for the compiled Rust extension `eserde._native`.

One submodule per format; `loads` accepts `str` (UTF-8 decoding happens in the Python codec layer); `dumps` consumes a
JSON-compatible tree and returns `str`. Failures surface as `ValueError`/`TypeError`.
"""

from __future__ import annotations

from typing import Any

class _FormatModule:
    def loads(self, data: str) -> Any: ...
    def dumps(self, obj: Any) -> str: ...

yaml: _FormatModule
csv: _FormatModule
tsv: _FormatModule
toml: _FormatModule
jsonc: _FormatModule
ini: _FormatModule
