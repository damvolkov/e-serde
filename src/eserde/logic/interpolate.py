"""Variable interpolation — compose-spec `${VAR:-default}` over a decoded tree.

String leaves are expanded natively (`$VAR`, `${VAR}`, `:-`/`-` defaults, `:?`/`?`
required, `:+`/`+` alternates, `$$` escape, nested operands); keys and non-string
scalars pass through. An unset variable without a default expands to `""`, as in
docker compose. The result is a copy; a failing expansion raises before any tree is
returned.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from eserde import _native
from eserde.infra.errors import LoadError

if TYPE_CHECKING:
    from collections.abc import Mapping


def interpolate(obj: Any, env: Mapping[str, str] | None = None) -> Any:
    """Return a copy of `obj` with every string leaf expanded against `env` (default: the process environment)."""
    try:
        return _native.interpolate(obj, dict(os.environ if env is None else env))
    except (TypeError, ValueError) as exc:
        msg = f"interpolation failed: {exc}"
        raise LoadError(msg) from exc
