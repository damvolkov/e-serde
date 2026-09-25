"""Drop-in `json`-module surface over the e-serde codecs.

For frameworks that duck-type `json.dumps`/`json.loads` (aiohttp-style `json_serialize=`,
structlog renderers, logging formatters): same call shape, `str` output. Default
invocations are byte-faithful to the stdlib; callers that opt into `ensure_ascii=False`
get the native compact utf-8 fast path (orjson semantics). Behaviours e-serde does not
share with the stdlib (`cls=`, ascii escaping, `indent`, `sort_keys`, parse hooks,
`object_pairs_hook`, `skipkeys`) delegate to it — slower but faithful, never a surprise.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from eserde.infra.formats import Format
from eserde.logic.api import dumps as serde_dumps
from eserde.logic.api import loads as serde_loads
from eserde.logic.encoder import encode


def dumps(
    obj: Any,
    /,
    *,
    skipkeys: bool = False,
    ensure_ascii: bool = True,
    check_circular: bool = True,
    allow_nan: bool = True,
    cls: type[json.JSONEncoder] | None = None,
    indent: int | str | None = None,
    separators: tuple[str, str] | None = None,
    default: Callable[[Any], Any] | None = None,
    sort_keys: bool = False,
    **kw: Any,
) -> str:
    """Serialize `obj` to a JSON string with json-module semantics, Rust codecs underneath."""
    stdlib_only = cls is not None or skipkeys or not check_circular or not allow_nan
    if stdlib_only:
        return json.dumps(
            obj,
            skipkeys=skipkeys,
            ensure_ascii=ensure_ascii,
            check_circular=check_circular,
            allow_nan=allow_nan,
            cls=cls,
            indent=indent,
            separators=separators,
            default=default,
            sort_keys=sort_keys,
            **kw,
        )
    tree = encode(obj, default=default)
    native = not ensure_ascii and indent is None and not sort_keys and separators in (None, (",", ":"))
    return (
        serde_dumps(tree, format=Format.JSON).decode("utf-8")
        if native
        else json.dumps(tree, ensure_ascii=ensure_ascii, indent=indent, separators=separators, sort_keys=sort_keys)
    )


def loads(
    s: str | bytes,
    /,
    *,
    cls: type[json.JSONDecoder] | None = None,
    object_hook: Callable[[dict[str, Any]], Any] | None = None,
    parse_float: Callable[[str], Any] | None = None,
    parse_int: Callable[[str], Any] | None = None,
    parse_constant: Callable[[str], Any] | None = None,
    object_pairs_hook: Callable[[list[tuple[str, Any]]], Any] | None = None,
    **kw: Any,
) -> Any:
    """Deserialize a JSON document, json-module semantics; native where faithful."""
    stdlib_only = (
        cls is not None
        or parse_float is not None
        or parse_int is not None
        or parse_constant is not None
        or object_pairs_hook is not None
    )
    if stdlib_only:
        return json.loads(
            s,
            cls=cls,
            object_hook=object_hook,
            parse_float=parse_float,
            parse_int=parse_int,
            parse_constant=parse_constant,
            object_pairs_hook=object_pairs_hook,
            **kw,
        )
    return serde_loads(s, format=Format.JSON, object_hook=object_hook)
