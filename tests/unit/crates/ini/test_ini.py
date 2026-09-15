"""Unit tests for native INI codec."""

import pytest
from e_loader.codecs.ini_native import NativeIniCodec


def test_ini_loads():
    """Test INI loading functionality."""
    codec = NativeIniCodec()
    
    # Test basic structure
    ini_data = """
[database]
host = localhost
port = 5432
username = user

[api]
timeout = 30
"""
    
    result = codec.loads(ini_data.encode('utf-8'))
    expected = {
        'database': {
            'host': 'localhost',
            'port': '5432',
            'username': 'user'
        },
        'api': {
            'timeout': '30'
        }
    }
    
    assert result == expected


def test_ini_dumps():
    """Test INI dumping functionality."""
    codec = NativeIniCodec()
    
    # Test basic structure
    obj = {
        'database': {
            'host': 'localhost',
            'port': '5432'
        },
        'api': {
            'timeout': '30'
        }
    }
    
    result = codec.dumps(obj)
    assert isinstance(result, bytes)
    assert b'localhost' in result


def test_ini_empty():
    """Test empty INI."""
    codec = NativeIniCodec()
    
    result = codec.loads(b"")
    assert result == {}


if __name__ == "__main__":
    pytest.main([__file__])