"""compat façade: json-module semantics over e-serde codecs.

The promise is faithfulness: default calls must match stdlib `json` byte-for-byte,
and every json behaviour we do not share (cls, ascii, indent, sort, parse hooks)
must match too — slower but never surprising. The native fast path (`ensure_ascii=False`)
is checked for compact utf-8 output.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from eserde.compat import dumps, loads

_TREE_CASES: list[tuple[str, dict[str, Any], dict[str, Any]]] = [
    ("plain", {"b": [1, 2.5, True, None], "s": "text"}, {}),
    ("unicode", {"ñ": "Málaga", "emoji": "✓"}, {}),
    ("compact-separators", {"a": 1}, {"separators": (",", ":")}),
    ("indent", {"a": {"b": 1}}, {"indent": 2}),
    ("sort-keys", {"z": 1, "a": 2}, {"sort_keys": True}),
    ("ascii-escape", {"ñ": "Málaga"}, {}),
    ("allow-nan", {"x": float("nan")}, {"allow_nan": True}),
]


@pytest.mark.parametrize(
    ("tree", "kwargs"),
    [(tree, kwargs) for _, tree, kwargs in _TREE_CASES],
    ids=[case_id for case_id, _, _ in _TREE_CASES],
)
async def test_dumps_matches_stdlib(tree: dict[str, Any], kwargs: dict[str, Any]) -> None:
    assert dumps(tree, **kwargs) == json.dumps(tree, **kwargs)


async def test_dumps_native_fast_path_is_compact_utf8() -> None:
    assert dumps({"ñ": "Málaga"}, ensure_ascii=False, separators=(",", ":")) == '{"ñ":"Málaga"}'


async def test_dumps_default_hook_flows_through_encoder() -> None:
    tree = {"when": datetime(2020, 1, 1, tzinfo=UTC), "amount": Decimal("1.5")}
    stdlib_shape = {"when": "2020-01-01T00:00:00+00:00", "amount": str(Decimal("1.5"))}
    assert json.loads(dumps(tree, default=str)) == stdlib_shape


async def test_dumps_cls_delegates_to_stdlib() -> None:
    class _Subclass(json.JSONEncoder):
        def default(self, o: Any) -> Any:
            return "via-cls"

    assert dumps({"x": object()}, cls=_Subclass) == json.dumps({"x": object()}, cls=_Subclass)


async def test_dumps_skipkeys_and_circular_off_delegate() -> None:
    assert loads(dumps({(1,): "a"}, skipkeys=True)) == {}


async def test_loads_object_hook_matches_stdlib() -> None:
    hook = lambda d: {"wrapped": d}  # noqa: E731
    assert loads('{"a": {"b": 1}}', object_hook=hook) == json.loads('{"a": {"b": 1}}', object_hook=hook)


async def test_loads_parse_float_delegates_to_stdlib() -> None:
    assert loads('{"a": 1.5}', parse_float=Decimal) == json.loads('{"a": 1.5}', parse_float=Decimal)


async def test_loads_object_pairs_hook_delegates_to_stdlib() -> None:
    assert loads('{"a": 1}', object_pairs_hook=list) == json.loads('{"a": 1}', object_pairs_hook=list)


async def test_loads_accepts_bytes_source() -> None:
    assert loads(b'{"a": 1}') == {"a": 1}
