"""Machine-readable spec contract: what each format claims to support.

`test_standards.py` verifies every claim against live behaviour, so a
documentation promise can never drift from what the codecs actually do.
`version` is cross-checked against `Cargo.lock` / installed metadata: bumping
an engine fails CI until the claims for that format are re-verified.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto
from types import MappingProxyType
from typing import TYPE_CHECKING

from eserde.infra.formats import Format

if TYPE_CHECKING:
    from collections.abc import Mapping


class Feature(StrEnum):
    NULL = auto()
    NONFINITE = auto()
    BIGNUM = auto()
    COMMENTS = auto()
    TRAILING_COMMAS = auto()
    ANCHORS = auto()
    MERGE_KEYS = auto()
    BOM_TOLERANT = auto()
    MERGE_DUP_SECTIONS = auto()


@dataclass(frozen=True, slots=True)
class Standard:
    spec: str
    engine: str
    crate: str
    version: str
    features: frozenset[Feature]


_F = frozenset

STANDARDS: Mapping[Format, Standard] = MappingProxyType(
    {
        Format.JSON: Standard(
            spec="RFC 8259",
            engine="msgspec.json",
            crate="msgspec",
            version="0.21",
            features=_F({Feature.NULL, Feature.BIGNUM}),
        ),
        Format.JSONC: Standard(
            spec="Deno jsonc: JSON + comments + trailing commas",
            engine="jsonc-parser",
            crate="jsonc-parser",
            version="0.33",
            features=_F({Feature.NULL, Feature.BIGNUM, Feature.COMMENTS, Feature.TRAILING_COMMAS}),
        ),
        Format.YAML: Standard(
            spec="YAML 1.2 core schema, plus the 1.1 merge key",
            engine="saphyr",
            crate="saphyr",
            version="0.0.12",
            features=_F(
                {
                    Feature.NULL,
                    Feature.NONFINITE,
                    Feature.COMMENTS,
                    Feature.TRAILING_COMMAS,
                    Feature.ANCHORS,
                    Feature.MERGE_KEYS,
                    Feature.BOM_TOLERANT,
                }
            ),
        ),
        Format.TOML: Standard(
            spec="TOML v1.1",
            engine="toml (toml-rs)",
            crate="toml",
            version="1.1",
            features=_F({Feature.NONFINITE, Feature.COMMENTS, Feature.TRAILING_COMMAS, Feature.BOM_TOLERANT}),
        ),
        Format.INI: Standard(
            spec="de-facto INI: sections of string key/value, no interpolation",
            engine="rust-ini",
            crate="rust-ini",
            version="0.21",
            features=_F({Feature.COMMENTS, Feature.BOM_TOLERANT, Feature.MERGE_DUP_SECTIONS}),
        ),
        Format.CSV: Standard(
            spec="RFC 4180: headered records as `list[dict]`, polars-style per-column type inference",
            engine="csv",
            crate="csv",
            version="1.4",
            features=_F({Feature.NULL, Feature.NONFINITE, Feature.BIGNUM, Feature.BOM_TOLERANT}),
        ),
        Format.TSV: Standard(
            spec="RFC 4180 dialect: tab-delimited",
            engine="csv",
            crate="csv",
            version="1.4",
            features=_F({Feature.NULL, Feature.NONFINITE, Feature.BIGNUM, Feature.BOM_TOLERANT}),
        ),
    }
)
