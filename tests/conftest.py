"""Pytest configuration and fixtures."""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import Mock

import pytest


def pytest_configure(config: Any) -> None:
    """Configure pytest markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")


@pytest.fixture
def yadisk_token() -> str | None:
    """Get Yandex Disk token from environment."""
    return os.environ.get("YADISK_TOKEN")


@pytest.fixture
def mock_resource() -> Mock:
    """Create a mock Yandex Disk resource."""
    resource = Mock()
    resource.name = "test.txt"
    resource.path = "disk:/test.txt"
    resource.size = 100
    resource.type = "file"
    resource.md5 = "abc123def456"
    resource.created = "2024-01-01T00:00:00+00:00"
    resource.modified = "2024-01-02T00:00:00+00:00"
    return resource


@pytest.fixture
def mock_dir_resource() -> Mock:
    """Create a mock Yandex Disk directory resource."""
    resource = Mock()
    resource.name = "testdir"
    resource.path = "disk:/testdir"
    resource.size = None
    resource.type = "dir"
    resource.created = "2024-01-01T00:00:00+00:00"
    resource.modified = "2024-01-02T00:00:00+00:00"
    return resource


@pytest.fixture
def mock_yadisk_client(mock_resource: Mock, mock_dir_resource: Mock) -> Mock:
    """Create a mock yadisk client for unit tests."""
    client = Mock()
    client.check_token.return_value = True
    client.exists.return_value = True
    client.is_dir.return_value = False
    client.is_file.return_value = True
    client.get_meta.return_value = mock_resource
    client.listdir.return_value = [mock_resource, mock_dir_resource]
    return client
