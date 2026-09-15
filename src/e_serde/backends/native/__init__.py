"""Native Rust backend: single extension module `e_serde._native`, one submodule per format.

Crates: saphyr (YAML 1.2), toml (rust-toml), jsonc-parser (Deno), rust-ini.
Parsing runs with the GIL released; this package fails fast if the extension is missing.
"""

from e_serde.backends.native.ini import NativeIniCodec
from e_serde.backends.native.jsonc import NativeJsoncCodec
from e_serde.backends.native.toml import NativeTomlCodec
from e_serde.backends.native.yaml import NativeYamlCodec

__all__ = ["NativeIniCodec", "NativeJsoncCodec", "NativeTomlCodec", "NativeYamlCodec"]
