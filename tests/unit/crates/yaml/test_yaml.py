"""Unit tests for native YAML codec."""

import pytest
from e_loader.codecs.yaml_native import NativeYamlCodec


def test_yaml_loads():
    """Test YAML loading functionality."""
    codec = NativeYamlCodec()
    
    # Test basic structure
    yaml_data = """
name: test
value: 42
active: true
tags:
  - python
  - rust
"""
    
    result = codec.loads(yaml_data.encode('utf-8'))
    expected = {
        'name': 'test',
        'value': 42,
        'active': True,
        'tags': ['python', 'rust']
    }
    
    assert result == expected


def test_yaml_dumps():
    """Test YAML dumping functionality."""
    codec = NativeYamlCodec()
    
    # Test basic structure
    obj = {
        'name': 'test',
        'value': 42,
        'active': True,
        'tags': ['python', 'rust']
    }
    
    result = codec.dumps(obj)
    assert isinstance(result, bytes)
    assert b'test' in result


def test_yaml_empty():
    """Test empty YAML."""
    codec = NativeYamlCodec()
    
    result = codec.loads(b"{}")
    assert result == {}


if __name__ == "__main__":
    pytest.main([__file__])