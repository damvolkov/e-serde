"""Unit tests for native TOML codec."""

import pytest
from e_loader.codecs.toml_native import NativeTomlCodec


def test_toml_loads():
    """Test TOML loading functionality."""
    codec = NativeTomlCodec()
    
    # Test basic structure
    toml_data = """
name = "test"
value = 42
active = true

[config]
timeout = 30
"""
    
    result = codec.loads(toml_data.encode('utf-8'))
    expected = {
        'name': 'test',
        'value': 42,
        'active': True,
        'config': {
            'timeout': 30
        }
    }
    
    assert result == expected


def test_toml_dumps():
    """Test TOML dumping functionality."""
    codec = NativeTomlCodec()
    
    # Test basic structure
    obj = {
        'name': 'test',
        'value': 42,
        'active': True,
        'config': {
            'timeout': 30
        }
    }
    
    result = codec.dumps(obj)
    assert isinstance(result, bytes)
    assert b'test' in result


def test_toml_empty():
    """Test empty TOML."""
    codec = NativeTomlCodec()
    
    result = codec.loads(b"")
    assert result == {}


if __name__ == "__main__":
    pytest.main([__file__])