"""Native YAML codec backed by Rust + serde_yaml.

This is the actual native Rust-backed YAML codec for e-loader v0.2.
"""

from __future__ import annotations

from typing import Any, ClassVar

# Import the native Rust implementation
try:
    from e_loader._rust.yaml import yaml_loads, yaml_dumps
except ImportError:
    # Fallback to PyYAML if native implementation not available
    import yaml as pyyaml_lib
    
    def yaml_loads(data: str) -> Any:
        return pyyaml_lib.load(data, Loader=pyyaml_lib.SafeLoader)
    
    def yaml_dumps(obj: Any) -> str:
        return pyyaml_lib.dump(obj, Dumper=pyyaml_lib.SafeDumper, allow_unicode=True, sort_keys=False)


from e_loader.errors import DumpError, LoadError
from e_loader.logic.formats import Format


class NativeYamlCodec:
    """Native Rust-backed YAML codec."""

    format: ClassVar[Format] = Format.YAML

    def loads(self, data: bytes) -> Any:
        try:
            return yaml_loads(data.decode("utf-8"))
        except Exception as exc:
            raise LoadError(f"native YAML decode failed: {exc}") from exc

    def dumps(self, obj: Any) -> bytes:
        try:
            return yaml_dumps(obj).encode("utf-8")
        except Exception as exc:
            raise DumpError(f"native YAML encode failed: {exc}") from exc