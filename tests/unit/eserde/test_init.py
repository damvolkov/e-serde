"""Package surface: public exports and the derived version."""

from __future__ import annotations

from importlib.metadata import version

import eserde


def test___version__matches_distribution() -> None:
    assert eserde.__version__ == version("e-serde")


def test___all__exports_resolve() -> None:
    missing = [name for name in eserde.__all__ if not hasattr(eserde, name)]
    assert missing == []
