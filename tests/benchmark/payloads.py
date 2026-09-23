"""Payload corpora seeded from `tests/resources/sample.*` — one source of truth.

The `1kb` tier IS the canonical sample file (a real config, every rival parses it).
`100kb` and `10mb` replicate the sample's `entries` (or `[entry.*]` sections in INI)
until the rendered payload hits the target size, so the scaled corpora keep the exact
rich type-mix of the fixture. Rendering stays neutral (stdlib json, pyyaml, rtoml);
TOML drops the `null_value` key — the format has no null, see `test_resources.py`.
"""

from __future__ import annotations

import configparser
import csv
import io
import json
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import rtoml
import yaml

from eserde import Format

if TYPE_CHECKING:
    from collections.abc import Callable

type Size = str

_SIZES: dict[Size, int] = {"1kb": 1_024, "100kb": 102_400, "10mb": 10_485_760}
_RESOURCE_NAMES: dict[Format, str] = {
    Format.JSON: "sample.json",
    Format.JSONC: "sample.jsonc",
    Format.YAML: "sample.yaml",
    Format.TOML: "sample.toml",
    Format.INI: "sample.ini",
    Format.CSV: "sample.csv",
    Format.TSV: "sample.tsv",
}

_TABLE: list[dict[str, Any]] = [
    {
        "sku": "VLN-001",
        "name": "Silmaril shard",
        "qty": 3,
        "price": 9.9,
        "active": True,
        "notes": None,
        "checksum": 9_007_199_254_740_993,
    },
    {
        "sku": "VLN-002",
        "name": 'Gauntlet, "of" Fëanor',
        "qty": -1,
        "price": None,
        "active": False,
        "notes": "handle\nwith\ncare",
        "checksum": 12345678901234567890123,
    },
    {
        "sku": "LOT-014",
        "name": "Mithril ring",
        "qty": 12,
        "price": 42.0,
        "active": True,
        "notes": 'says "hello", world',
        "checksum": 42,
    },
    {
        "sku": "LOT-015",
        "name": "Phial of Eärendil",
        "qty": 0,
        "price": 7.25,
        "active": False,
        "notes": None,
        "checksum": -99999999999999999999999,
    },
    {
        "sku": "NRD-001",
        "name": "colon: inside",
        "qty": 7,
        "price": None,
        "active": True,
        "notes": "ux, ördög, 日本語",
        "checksum": 1,
    },
]


def _csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _csv_render(rows: list[dict[str, Any]], delimiter: str) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=delimiter, lineterminator="\n")
    writer.writerow(rows[0])
    writer.writerows([_csv_cell(value) for value in row.values()] for row in rows)
    return buf.getvalue().encode()


def _resource(fmt: Format) -> Path:
    return Path(__file__).resolve().parents[1] / "resources" / _RESOURCE_NAMES[fmt]


@cache
def _base_tree(fmt: Format) -> Any:
    if fmt in (Format.CSV, Format.TSV):
        return [dict(row) for row in _TABLE]
    if fmt is Format.INI:
        return _read_ini(_resource(fmt).read_bytes())
    tree = json.loads(_resource(Format.JSON).read_bytes())
    return _drop_nulls(tree) if fmt is Format.TOML else tree


def _read_ini(data: bytes) -> dict[str, dict[str, str]]:
    parser = configparser.ConfigParser()
    parser.optionxform = str  # type: ignore
    parser.read_string(data.decode())
    return {section: dict(parser[section]) for section in parser.sections()}


def _clone(value: Any, generation: int) -> Any:
    """Copy of a sample node, shifting identity-bearing strings by replication round."""
    if isinstance(value, dict):
        return {key: _clone(item, generation) for key, item in value.items()}
    if isinstance(value, list):
        return [_clone(item, generation) for item in value]
    if isinstance(value, str) and "-" in value:
        return f"{value}-{generation}"
    return value


def _scale(fmt: Format, reps: int) -> Any:
    base = _base_tree(fmt)
    if fmt in (Format.CSV, Format.TSV):
        return [
            {**row, "sku": f"{row['sku']}-{gen:03d}", "qty": int(row["qty"]) + gen}
            for gen in range(reps + 1)
            for row in base
        ]
    if fmt is Format.INI:
        scaled = {key: value for key, value in base.items() if not key.startswith("entry.")}
        sections = {key: value for key, value in base.items() if key.startswith("entry.")}
        for generation in range(reps):
            for name, fields in sections.items():
                clone = {key: (f"{value}-{generation}" if key == "name" else value) for key, value in fields.items()}
                scaled[f"{name}-{generation:03d}" if generation else name] = clone
        return scaled
    entries = base["entries"]
    grown = [dict(entry) for entry in entries] + [_clone(entry, gen) for gen in range(1, reps) for entry in entries]
    return {**base, "entries": grown}


def _drop_nulls(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {key: _drop_nulls(value) for key, value in obj.items() if value is not None}
    if isinstance(obj, list):
        return [_drop_nulls(value) for value in obj]
    return obj


def _json_render(tree: Any) -> bytes:
    return json.dumps(tree, ensure_ascii=False, separators=(",", ":")).encode()


def _jsonc_render(tree: Any) -> bytes:
    lines = json.dumps(tree, indent=1, ensure_ascii=False).splitlines()
    out: list[str] = ["// e-serde jsonc benchmark payload"]
    for offset, line in enumerate(lines):
        if offset and offset % 12 == 0:
            out.append(f"  // section {offset // 12}")
        out.append(line)
    return "\n".join(out).encode()


def _yaml_render(tree: Any) -> bytes:
    return yaml.safe_dump(tree, allow_unicode=True, default_flow_style=False, sort_keys=False).encode()


def _toml_render(tree: Any) -> bytes:
    return rtoml.dumps(tree).encode()


def _ini_render(tree: dict[str, dict[str, str]]) -> bytes:
    parser = configparser.ConfigParser()
    parser.optionxform = str  # type: ignore
    parser.read_dict(tree)
    buf = io.StringIO()
    parser.write(buf)
    return buf.getvalue().encode()


_RENDERERS: dict[Format, Callable[[Any], bytes]] = {
    Format.JSON: _json_render,
    Format.JSONC: _jsonc_render,
    Format.YAML: _yaml_render,
    Format.TOML: _toml_render,
    Format.INI: _ini_render,
    Format.CSV: lambda tree: _csv_render(tree, ","),
    Format.TSV: lambda tree: _csv_render(tree, "\t"),
}


def _render(fmt: Format, reps: int) -> bytes:
    return _RENDERERS[fmt](_scale(fmt, reps))


@cache
def _reps_for(fmt: Format, size: Size) -> int:
    target = _SIZES[size]
    reps = max(1, target // max(len(_resource(Format.JSON).read_bytes()), 1))
    length = len(_render(fmt, reps))
    for _ in range(8):
        if target <= length <= target * 1.25:
            break
        if length < target:
            reps += max(1, int(reps * target / length * 0.9))
        else:
            reps = max(1, int(reps * target / length * 1.1))
        length = len(_render(fmt, reps))
    return reps


@cache
def payload(fmt: Format, size: Size) -> bytes:
    """Cached bytes every loader rival must parse; `1kb` is the real sample file."""
    if size == "1kb":
        return _resource(fmt).read_bytes()
    return _render(fmt, _reps_for(fmt, size))


@cache
def source_tree(fmt: Format, size: Size) -> Any:
    """Cached dict every dump rival must serialize (same shape as `payload`)."""
    if size == "1kb":
        return _base_tree(fmt)
    return _scale(fmt, _reps_for(fmt, size))


def sizes() -> tuple[Size, ...]:
    """Benchmark size buckets, small to large."""
    return tuple(_SIZES)
