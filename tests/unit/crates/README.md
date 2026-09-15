# Native Codec Testing

Unit tests for native Rust codecs.

## Structure

- `yaml/` - YAML codec tests
- `toml/` - TOML codec tests  
- `ini/` - INI codec tests

Each test file validates:
1. Loading functionality (bytes → Python objects)
2. Dumping functionality (Python objects → bytes) 
3. Edge cases and empty inputs

## Running Tests

```bash
# Run all native codec tests
pytest tests/unit/crates/

# Run specific codec tests
pytest tests/unit/crates/yaml/
pytest tests/unit/crates/toml/  
pytest tests/unit/crates/ini/
```