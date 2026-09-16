# Installation

e-serde targets **CPython 3.14+** and ships prebuilt wheels for Linux, macOS and
Windows — no compiler, no Cargo required.

=== "uv"

    ```bash
    uv add e-serde
    ```

=== "pip"

    ```bash
    pip install e-serde
    ```

## Verify

```python
import eserde
print(eserde.__version__)     # e.g. 0.1.0
```

The `e-serde` console script lists the active codecs and the format each one uses:

```bash
e-serde
#   json  -> MsgspecJsonCodec
#   jsonc -> NativeJsoncCodec
#   yaml  -> NativeYamlCodec
#   toml  -> NativeTomlCodec
#   ini   -> NativeIniCodec
```

## From source

```bash
git clone https://github.com/damvolkov/e-serde && cd e-serde
uv sync            # builds the Rust extension in place (maturin)
```

Requires a Rust toolchain. See [Development](development.md).

## Runtime dependencies

Only `msgspec`. The native codecs are compiled into the wheel as `eserde._native`; if the
extension is unavailable the package raises `eserde.CodecError` at import of a backend.
