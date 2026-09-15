"""CLI entrypoint — emits version, formats and active backends. Real CLI lands later."""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version

from e_serde.backends.registry import default_registry
from e_serde.infra.formats import Format


def main() -> None:
    try:
        pkg_version = version("e-serde")
    except PackageNotFoundError:
        pkg_version = "0.0.0+dev"
    sys.stdout.write(f"e-serde {pkg_version}\n")
    for fmt in Format:
        codec = default_registry.get(fmt)
        sys.stdout.write(f"  {fmt.value:<5} -> {type(codec).__name__}\n")


if __name__ == "__main__":
    main()
