"""CLI entrypoint — emits version and supported formats. Real CLI lands later."""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version

from e_loader.logic.formats import Format


def main() -> None:
    try:
        pkg_version = version("e-loader")
    except PackageNotFoundError:
        pkg_version = "0.0.0+dev"
    sys.stdout.write(f"e-loader {pkg_version}\n")
    sys.stdout.write(f"formats: {', '.join(f.value for f in Format)}\n")


if __name__ == "__main__":
    main()