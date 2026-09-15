"""msgspec backend: C-implemented, zero-dependency engine used for JSON.

msgspec ships prebuilt wheels for every CPython and is the reference implementation
for both JSON speed and schema validation (`type=` on the facade API).
"""

from e_serde.backends.msgspec.json import MsgspecJsonCodec

__all__ = ["MsgspecJsonCodec"]
