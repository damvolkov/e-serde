"""Typed schemas mirroring `payloads.build_tree` — the subject of the validation benchmarks.

Three materializations of one shape (msgspec Struct, frozen dataclass, pydantic
BaseModel) so `type=` decoding is compared against the canonical pipelines at equal
expressiveness, never against a strawman.
"""

from __future__ import annotations

from dataclasses import dataclass

import msgspec
from pydantic import BaseModel, ConfigDict, TypeAdapter


class Limits(msgspec.Struct, frozen=True):
    cpu: int
    memory_mb: int
    timeout_ms: int


class Owner(msgspec.Struct, frozen=True):
    team: str
    email: str


class Entry(msgspec.Struct, frozen=True):
    id: str
    name: str
    endpoint: str
    weight: float
    retries: int
    enabled: bool
    tags: list[str]
    limits: Limits
    role: str
    owner: Owner
    headers: dict[str, str]


class Meta(msgspec.Struct, frozen=True):
    project: str
    stage: str
    revision: int
    sample_rate: float
    strict: bool


class Settings(msgspec.Struct, frozen=True):
    region: str
    log_level: str
    drain_sec: int
    flags: list[str]


class Config(msgspec.Struct, frozen=True):
    meta: Meta
    settings: Settings
    entries: list[Entry]


@dataclass(slots=True, frozen=True)
class DCLimits:
    cpu: int
    memory_mb: int
    timeout_ms: int


@dataclass(slots=True, frozen=True)
class DCOwner:
    team: str
    email: str


@dataclass(slots=True, frozen=True)
class DCEntry:
    id: str
    name: str
    endpoint: str
    weight: float
    retries: int
    enabled: bool
    tags: list[str]
    limits: DCLimits
    role: str
    owner: DCOwner
    headers: dict[str, str]


@dataclass(slots=True, frozen=True)
class DCMeta:
    project: str
    stage: str
    revision: int
    sample_rate: float
    strict: bool


@dataclass(slots=True, frozen=True)
class DCSettings:
    region: str
    log_level: str
    drain_sec: int
    flags: list[str]


@dataclass(slots=True, frozen=True)
class DCConfig:
    meta: DCMeta
    settings: DCSettings
    entries: list[DCEntry]


class PLimits(BaseModel):
    model_config = ConfigDict(frozen=True)
    cpu: int
    memory_mb: int
    timeout_ms: int


class POwner(BaseModel):
    model_config = ConfigDict(frozen=True)
    team: str
    email: str


class PEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str
    endpoint: str
    weight: float
    retries: int
    enabled: bool
    tags: list[str]
    limits: PLimits
    role: str
    owner: POwner
    headers: dict[str, str]


class PMeta(BaseModel):
    model_config = ConfigDict(frozen=True)
    project: str
    stage: str
    revision: int
    sample_rate: float
    strict: bool


class PSettings(BaseModel):
    model_config = ConfigDict(frozen=True)
    region: str
    log_level: str
    drain_sec: int
    flags: list[str]


class PConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    meta: PMeta
    settings: PSettings
    entries: list[PEntry]


type Adapter = TypeAdapter[PConfig]
PYDANTIC: Adapter = TypeAdapter(PConfig)
