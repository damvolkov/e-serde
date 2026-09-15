"""Shared codec fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def small_payload() -> dict[str, object]:
    return {"name": "demian", "n": 42, "active": True, "items": [1, 2, 3]}


@pytest.fixture
def nested_payload() -> dict[str, object]:
    return {
        "user": {"name": "demian", "age": 33},
        "tags": ["python", "rust"],
        "config": {"debug": True, "retries": 3, "thresholds": [0.1, 0.5, 0.9]},
    }


@pytest.fixture
def ini_payload() -> dict[str, dict[str, str]]:
    return {
        "service": {"name": "loader", "port": "8080"},
        "logging": {"level": "info", "format": "json"},
    }
