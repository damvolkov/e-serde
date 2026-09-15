# e-loader Native Codecs

This directory contains the native Rust implementations of e-loader codecs.

## Structure

- `yaml/` - Native YAML codec  
- `toml/` - Native TOML codec
- `ini/` - Native INI codec

Each crate implements:
1. `loads(data: bytes) -> Any` - Decode data to Python objects
2. `dumps(obj: Any) -> bytes` - Encode Python objects to bytes

## Building

To build all crates:

```bash
# Build all native crates  
cargo build --release
```

Each crate can be built individually:
```bash
cd yaml && cargo build --release
cd toml && cargo build --release
cd ini && cargo build --release
```

The resulting binaries will be in `target/release/` and are automatically linked by the Python wrappers.

## Testing

Unit tests for each native codec are available in `tests/unit/crates/`.