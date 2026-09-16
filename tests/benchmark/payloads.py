"""Payload corpora seeded from `tests/resources/sample.*` — one source of truth.

The `1kb` tier IS the canonical sample file (a real config, every rival parses it).
`100kb` and `10mb` replicate the sample's `entries` (or `[entry.*]` sections in INI)
until the rendered payload hits the target size, so the scaled corpora keep the exact
rich type-mix of the fixture. Rendering stays neutral (stdlib json, pyyaml, rtoml);
TOML drops the `null_value` key — the format has no null, see `test_resources.py`.
"""

from __future__ import annotations

import configparser
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
}


def _resource(fmt: Format) -> Path:
    return Path(__file__).resolve().parents[1] / "resources" / _RESOURCE_NAMES[fmt]


@cache
def _base_tree(fmt: Format) -> Any:
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
