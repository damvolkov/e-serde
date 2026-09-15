# e-loader - Clean Project Structure

## Overview

This is the clean, organized structure of the e-loader package following your requirements for strict directory organization.

## Directory Structure

```
e-loader/
├── Cargo.toml                      # Rust workspace root (for native crates)
├── crates/                         # Rust crates (PyO3 bindings)
│   ├── e-loader-yaml/              # Native YAML codec
│   ├── e-loader-toml/                # Native TOML codec  
│   └── e-loader-ini/         # Native INI codec
├── pyproject.toml                # Python package configuration
├── src/
│   ├── e_loader/
│   │   ├── __init__.py             # Package exports
│   │   ├── main.py                   # CLI entrypoint
│   │   ├── logic/                # Core business logic
│   │   │   ├── api.py          # Public facade (loads/dumps)
│   │   │   ├── formats.py        # Format definitions and detection
│   │   │   ├── registry.py     # Codec registry management
│   │   │   └── encoder.py  # Jsonable encoder logic
│   │   ├── infra/                  # Infrastructure components
│   │   │   ├── errors.py         # Exception hierarchy
│   │   │   ├── io.py             # Async I/O helpers
│   │   │   └── protocols.py          # Codec protocol definition
│   │   └── codecs/               # Codec implementations
│   │       ├── __init__.py       # Codec exports
│   │       ├── base.py       # Base codec utilities
│   │       ├── json_orjson.py    # orjson JSON codec
│   │       ├── toml_rtoml.py     # rtoml TOML codec
│   │       ├── toml_stdlib.py  # stdlib tomllib TOML codec
│   │       ├── yaml_pyyaml.py   # PyYAML YAML codec (placeholder)
│   │       └── ini_stdlib.py # stdlib configparser INI codec
└── tests/
    └── unit/
        └── e_loader/
            ├── test_formats.py
            ├── test_api.py
            ├── test_registry.py
            ├── test_encoder.py
            └── codecs/
                ├── test_json_orjson.py
                ├── test_toml_rtoml.py
                ├── test_toml_stdlib.py
                ├── test_yaml_pyyaml.py
                └── test_ini_stdlib.py
```

## Design Principles

1. **Strict Separation of Concerns**:
   - `logic/` - Core business logic (API, formats, registry, encoder)
   - `infra/` - Infrastructure components (errors, protocols, I/O helpers)  
   - `codecs/` - Format-specific implementations
   - `crates/` - Native Rust bindings for performance-critical codecs

2. **Clear Module Organization**:
   - All modules are clearly categorized by function
   - No nested directories with overlapping responsibilities
   - Consistent naming and structure

3. **Future Extensibility**:
   - Rust crates in `crates/` directory ready for v0.2 implementation
   - Clean separation allows easy replacement of codecs (e.g., native YAML)
   - All imports work correctly through proper package structure

## Key Features of This Structure

- **Modular**: Each functionality has its own dedicated directory
- **Scalable**: Easy to add new formats or backends
- **Maintainable**: Clear separation makes code easier to understand and modify
- **Testable**: Unit tests organized to match the source structure
- **Ready for Rust Integration**: Crates directory is prepared with workspace setup

This organization allows for clear separation between Python components (logic, infra) and native Rust components (crates), while maintaining clean, type-safe Python code throughout.