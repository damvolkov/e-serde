"""CLI entrypoint — emits version, formats and active backends. Real CLI lands later."""

from __future__ import annotations

import sys

from eserde import __version__
from eserde.backends.registry import default_registry
from eserde.infra.formats import Format


def main() -> None:
    sys.stdout.write(f"e-serde {__version__}\n")
    for fmt in Format:
        codec = default_registry.get(fmt)
        sys.stdout.write(f"  {fmt.value:<5} -> {type(codec).__name__}\n")


if __name__ == "__main__":
    main()
