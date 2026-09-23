"""Rival matrix: the strong, direct libraries that do exactly what e-serde does.

One dispatch table per operation — format -> rival label -> callable over `bytes`.
Each adapter receives the payload the way real callers would hand it over (some want
`str`, some want `bytes`): the conversion is part of the rival's cost, not a strawman.
"""

from __future__ import annotations

import configparser
import csv as stdlib_csv
import io
import json
import tomllib
from collections.abc import Callable
from typing import Any

import json5
import msgspec
import orjson
import polars
import pyjson5
import rtoml
import simplejson
import tomli
import tomli_w
import tomlkit
import ujson
import yaml
from ruamel.yaml import YAML

import eserde
from eserde import Format
from tests.benchmark.models import PYDANTIC, Config, DCConfig

type Decode = Callable[[bytes], Any]
type Encode = Callable[[Any], bytes]

_RUAMEL = YAML(typ="safe")
_RUAMEL_RW = YAML()


def _serde_loads(fmt: Format) -> Decode:
    return lambda data: eserde.loads(data, format=fmt)


def _serde_dumps(fmt: Format) -> Encode:
    return lambda obj: eserde.dumps(obj, format=fmt)


def _serde_typed(fmt: Format, schema: Any) -> Decode:
    return lambda data: eserde.loads(data, format=fmt, type=schema)


def _str_loads(fn: Callable[[str], Any]) -> Decode:
    return lambda data: fn(data.decode())


def _str_encode(fn: Callable[[Any], str]) -> Encode:
    return lambda obj: fn(obj).encode()


def _polars_loads(separator: str) -> Decode:
    def decode(data: bytes) -> Any:
        return polars.read_csv(io.BytesIO(data), separator=separator).to_dicts()

    return decode


def _polars_dumps(rows: list[dict[str, Any]]) -> bytes:
    return polars.DataFrame(rows).write_csv().encode()


def _stdlib_csv_loads(data: bytes) -> Any:
    return list(stdlib_csv.DictReader(io.StringIO(data.decode())))


def _configparser_loads(data: bytes) -> dict[str, dict[str, str]]:
    parser = configparser.ConfigParser()
    parser.read_string(data.decode())
    return {section: dict(parser[section]) for section in parser.sections()}


def _configparser_dumps(obj: dict[str, dict[str, str]]) -> bytes:
    parser = configparser.ConfigParser()
    parser.optionxform = str  # type: ignore
    parser.read_dict(obj)
    buf = io.StringIO()
    parser.write(buf)
    return buf.getvalue().encode()


def _ruamel_dumps(obj: Any) -> bytes:
    buf = io.BytesIO()
    _RUAMEL_RW.dump(obj, buf)
    return buf.getvalue()


def _pyyaml_loads(data: bytes) -> Any:
    return yaml.load(data, Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))  # noqa: S506


def _pyyaml_dumps(obj: Any) -> bytes:
    return yaml.dump(obj, Dumper=getattr(yaml, "CSafeDumper", yaml.SafeDumper), sort_keys=False).encode()


def _tomlkit_loads(data: bytes) -> Any:
    return tomlkit.parse(data)


def _msgspec_struct(data: bytes) -> Any:
    return msgspec.json.decode(data, type=Config)


def _pydantic_orjson(data: bytes) -> Any:
    return PYDANTIC.validate_python(orjson.loads(data))


def _pydantic_pyyaml(data: bytes) -> Any:
    return PYDANTIC.validate_python(yaml.safe_load(data))


def _pydantic_rtoml(data: bytes) -> Any:
    return PYDANTIC.validate_python(rtoml.loads(data.decode()))


LOAD_RIVALS: dict[Format, dict[str, Decode]] = {
    Format.JSON: {
        "stdlib-json": json.loads,
        "simplejson": simplejson.loads,
        "ujson": ujson.loads,
        "orjson": orjson.loads,
        "msgspec": msgspec.json.decode,
        "e-serde": _serde_loads(Format.JSON),
    },
    Format.JSONC: {
        "json5": _str_loads(json5.loads),
        "pyjson5": _str_loads(pyjson5.loads),
        "e-serde": _serde_loads(Format.JSONC),
    },
    Format.YAML: {
        "pyyaml": _pyyaml_loads,
        "ruamel": _RUAMEL.load,
        "e-serde": _serde_loads(Format.YAML),
    },
    Format.TOML: {
        "stdlib-tomllib": _str_loads(tomllib.loads),
        "tomli": _str_loads(tomli.loads),
        "rtoml": _str_loads(rtoml.loads),
        "tomlkit": _tomlkit_loads,
        "e-serde": _serde_loads(Format.TOML),
    },
    Format.INI: {
        "configparser": _configparser_loads,
        "e-serde": _serde_loads(Format.INI),
    },
    Format.CSV: {
        "stdlib-csv": _stdlib_csv_loads,
        "polars": _polars_loads(","),
        "e-serde": _serde_loads(Format.CSV),
    },
    Format.TSV: {
        "polars": _polars_loads("\t"),
        "e-serde": _serde_loads(Format.TSV),
    },
}

DUMP_RIVALS: dict[Format, dict[str, Encode]] = {
    Format.JSON: {
        "stdlib-json": _str_encode(json.dumps),
        "simplejson": _str_encode(simplejson.dumps),
        "ujson": _str_encode(ujson.dumps),
        "orjson": orjson.dumps,
        "msgspec": msgspec.json.encode,
        "e-serde": _serde_dumps(Format.JSON),
    },
    Format.JSONC: {
        "json5": _str_encode(json5.dumps),
        "pyjson5": _str_encode(pyjson5.dumps),
        "e-serde": _serde_dumps(Format.JSONC),
    },
    Format.YAML: {
        "pyyaml": _pyyaml_dumps,
        "ruamel": _ruamel_dumps,
        "e-serde": _serde_dumps(Format.YAML),
    },
    Format.TOML: {
        "tomli-w": _str_encode(tomli_w.dumps),
        "rtoml": _str_encode(rtoml.dumps),
        "tomlkit": _str_encode(tomlkit.dumps),
        "e-serde": _serde_dumps(Format.TOML),
    },
    Format.INI: {
        "configparser": _configparser_dumps,
        "e-serde": _serde_dumps(Format.INI),
    },
    Format.CSV: {
        "polars": _polars_dumps,
        "e-serde": _serde_dumps(Format.CSV),
    },
    Format.TSV: {
        "polars": _polars_dumps,
        "e-serde": _serde_dumps(Format.TSV),
    },
}

TYPED_RIVALS: dict[Format, dict[str, Decode]] = {
    Format.JSON: {
        "e-serde:plain": _serde_loads(Format.JSON),
        "e-serde:struct": _serde_typed(Format.JSON, Config),
        "e-serde:dataclass": _serde_typed(Format.JSON, DCConfig),
        "msgspec:struct": _msgspec_struct,
        "pydantic:orjson": _pydantic_orjson,
    },
    Format.YAML: {
        "e-serde:plain": _serde_loads(Format.YAML),
        "e-serde:struct": _serde_typed(Format.YAML, Config),
        "e-serde:dataclass": _serde_typed(Format.YAML, DCConfig),
        "pydantic:pyyaml": _pydantic_pyyaml,
    },
    Format.TOML: {
        "e-serde:plain": _serde_loads(Format.TOML),
        "e-serde:struct": _serde_typed(Format.TOML, Config),
        "e-serde:dataclass": _serde_typed(Format.TOML, DCConfig),
        "pydantic:rtoml": _pydantic_rtoml,
    },
}
