"""CLI entrypoint — emits version, formats and active backends. Real CLI lands later."""

from __future__ import annotations

import sys

from eserde import __version__
from eserde.backends.registry import default_registry
from eserde.infra.formats import Format


def main() -> None:
    """Emit the version line and one row per registered format naming its active backend."""
    rows = (f"  {fmt.value:<5} -> {type(default_registry.get(fmt)).__name__}\n" for fmt in Format)
    sys.stdout.write(f"e-serde {__version__}\n" + "".join(rows))


if __name__ == "__main__":
    main()
