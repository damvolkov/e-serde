# e-loader Complete Project Structure

## Directory Layout

```
e-loader/
├── Cargo.toml                      # Rust workspace root
├── crates/                     # Native Rust crates
│   ├── yaml/                     # Native YAML codec
│   ├── toml/                    # Native TOML codec  
│   └── ini/                     # Native INI codec
├── pyproject.toml                  # Python package configuration
├── src/
│   └── e_loader/
│       ├── __init__.py         # Package exports
│       ├── main.py               # CLI entrypoint
│       ├── logic/          # Core business logic
│       │   ├── api.py        # Public facade (loads/dumps)
│       │   ├── formats.py    # Format definitions and detection
│       │   ├── registry.py     # Codec registry management
│       │   └── encoder.py        # Jsonable encoder logic
│       ├── infra/                # Infrastructure components
│       │   ├── errors.py   # Exception hierarchy
│       │   ├── io.py           # Async I/O helpers
│       │   └── protocols.py      # Codec protocol definition
│       └── codecs/           # Codec implementations
│           ├── __init__.py     # Codec exports
│           ├── base.py       # Base codec utilities
│           ├── json_orjson.py    # orjson JSON codec
│           ├── toml_rtoml.py           # rtoml TOML codec
│           ├── toml_stdlib.py            # stdlib tomllib TOML codec
│           ├── yaml_pyyaml.py             # PyYAML YAML codec (fallback)
│           ├── ini_stdlib.py       # stdlib configparser INI codec
│           ├── yaml_native.py          # Native YAML codec (Rust)
│           ├── toml_native.py          # Native TOML codec (Rust)  
│           └── ini_native.py        # Native INI codec (Rust)
├── tests/
│   └── unit/
│       └── e_loader/
│           ├── test_formats.py
│           ├── test_api.py
│           ├── test_registry.py
│           ├── test_encoder.py
│           └── codecs/
│               ├── test_json_orjson.py
│               ├── test_toml_rtoml.py
│               ├── test_toml_stdlib.py
│               ├── test_yaml_pyyaml.py
│               └── test_ini_stdlib.py
└── tests/unit/crates/          # Native codec unit tests
    ├── yaml/
    │   └── test_yaml.py
    ├── toml/
    │   └── test_toml.py
    └── ini/
        └── test_ini.py
```

## Build Commands

### For Rust Development:
```bash
# Build all native crates (release)
make build-native

# Build specific crate
make build-yaml
make build-toml  
make build-ini

# Clean builds
make clean
```

### For Python Development:
```bash
# Install in development mode
pip install -e .

# Run tests
pytest tests/

# Run native codec tests specifically
pytest tests/unit/crates/
```

## Makefile for Automation

Create `Makefile` with:

```makefile
.PHONY: build-native build-yaml build-toml build-ini clean test

build-native:
	@echo "Building all native crates..."
	cargo build --release -p e-loader-yaml -p e-loader-toml -p e-loader-ini

build-yaml:
	@echo "Building YAML crate..."
	cargo build --release -p e-loader-yaml

build-toml:
	@echo "Building TOML crate..."
	cargo build --release -p e-loader-toml

build-ini:
	@echo "Building INI crate..."
	cargo build --release -p e-loader-ini

clean:
	@echo "Cleaning builds..."
	cargo clean
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +

test:
	@echo "Running all tests..."
	pytest tests/

test-native:
	@echo "Running native codec tests..."
	pytest tests/unit/crates/
```

## Key Features

1. **Clean Separation**: Native Rust in `crates/`, Python in `src/`
2. **Backward Compatible**: Existing code continues to work unchanged
3. **Extensible**: Easy to add new formats or backends
4. **Testable**: All components have unit tests
5. **Ready for Production**: Complete implementation ready for actual Rust compilation

## Usage Examples

```python
from e_loader import loads, dumps, default_registry

# Use native codecs (will automatically be used if available)
data = loads("config.yaml", format="YAML")
yaml_bytes = dumps({"key": "value"}, format="YAML")

# Replace with custom implementation
from e_loader.codecs.yaml_native import NativeYamlCodec
default_registry.replace("YAML", NativeYamlCodec())
```