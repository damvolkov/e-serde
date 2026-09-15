"""YAML codec backed by PyYAML with LibYAML (C) loader/dumper.

Placeholder until the native Rust YAML codec lands. PyYAML is C (LibYAML), not Rust, but
it is the fastest mainstream option available today and slots into the same Codec contract.
"""

from __future__ import annotations

from typing import Any, ClassVar

import yaml

from e_loader.infra.errors import DumpError, LoadError
from e_loader.logic.formats import Format

try:
    from yaml import CSafeDumper as _SafeDumper
    from yaml import CSafeLoader as _SafeLoader
except ImportError:  # libyaml not built; degraded pure-Python path
    from yaml import SafeDumper as _SafeDumper  # type: ignore[assignment]
    from yaml import SafeLoader as _SafeLoader  # type: ignore[assignment]


class PyyamlCodec:
    """PyYAML codec using `CSafeLoader`/`CSafeDumper` when LibYAML is available."""

    format: ClassVar[Format] = Format.YAML

    def loads(self, data: bytes) -> Any:
        try:
            return yaml.load(data, Loader=_SafeLoader)
        except yaml.YAMLError as exc:
            raise LoadError(f"pyyaml decode failed: {exc}") from exc

    def dumps(self, obj: Any) -> bytes:
        try:
            return yaml.dump(obj, Dumper=_SafeDumper, allow_unicode=True, sort_keys=False).encode("utf-8")
        except yaml.YAMLError as exc:
            raise DumpError(f"pyyaml encode failed: {exc}") from exc