"""Unit tests for YaDiskFileSystem."""

from __future__ import annotations

import io
import os
from unittest.mock import Mock, patch

import pytest

from dvc_yadisk.fs import YaDiskFileSystem


class TestYaDiskFileSystem:
    """Tests for the YaDiskFileSystem class."""

    def test_protocol(self) -> None:
        """Verify protocol is correctly set."""
        assert YaDiskFileSystem.protocol == "yadisk"

    def test_param_checksum(self) -> None:
        """Verify checksum parameter is md5."""
        assert YaDiskFileSystem.PARAM_CHECKSUM == "md5"

    def test_strip_protocol(self) -> None:
        """Test protocol stripping from URLs."""
        assert YaDiskFileSystem._strip_protocol("yadisk://path/to/file") == "path/to/file"
        assert YaDiskFileSystem._strip_protocol("yadisk:///root/file") == "root/file"
        assert YaDiskFileSystem._strip_protocol("path/to/file") == "path/to/file"

    def test_unstrip_protocol(self) -> None:
        """Test adding protocol to paths."""
        fs = YaDiskFileSystem(token="test")
        assert fs.unstrip_protocol("path/to/file") == "yadisk://path/to/file"
        assert fs.unstrip_protocol("/path/to/file") == "yadisk://path/to/file"

    def test_normalize_path(self) -> None:
        """Test path normalization."""
        fs = YaDiskFileSystem(token="test")
        assert fs._normalize_path("test.txt") == "/test.txt"
        assert fs._normalize_path("/test.txt") == "/test.txt"
        assert fs._normalize_path("path/to/file") == "/path/to/file"
        assert fs._normalize_path("") == "/"

    def test_strip_disk_prefix(self) -> None:
        """Test disk: prefix stripping."""
        fs = YaDiskFileSystem(token="test")
        assert fs._strip_disk_prefix("disk:/test.txt") == "/test.txt"
        assert fs._strip_disk_prefix("/test.txt") == "/test.txt"


class TestYaDiskFileSystemWithMock:
    """Tests using mocked yadisk client."""

    @pytest.fixture
    def mock_client(self, mock_resource: Mock) -> Mock:
        """Create a mock yadisk client."""
        client = Mock()
        client.check_token.return_value = True
        client.exists.return_value = True
        client.is_dir.return_value = False
        client.is_file.return_value = True
        client.get_meta.return_value = mock_resource
        client.listdir.return_value = [mock_resource]
        return client

    @pytest.fixture
    def fs_with_mock(self, mock_client: Mock) -> YaDiskFileSystem:
        """Create a YaDiskFileSystem with mocked client."""
        fs = YaDiskFileSystem(token="test_token")
        fs._yadisk_client = mock_client
        return fs

    def test_info(self, fs_with_mock: YaDiskFileSystem, mock_client: Mock) -> None:
        """Test info method."""
        result = fs_with_mock.info("test.txt")

        mock_client.get_meta.assert_called_once_with("/test.txt")
        assert result["name"] == "test.txt"
        assert result["size"] == 100
        assert result["type"] == "file"
        assert result["md5"] == "abc123def456"

    def test_ls(self, fs_with_mock: YaDiskFileSystem, mock_client: Mock) -> None:
        """Test ls method."""
        result = fs_with_mock.ls("/")

        mock_client.listdir.assert_called_once()
        assert len(result) == 1
        assert "/test.txt" in result

    def test_ls_with_detail(self, fs_with_mock: YaDiskFileSystem) -> None:
        """Test ls with detail flag."""
        result = fs_with_mock.ls("/", detail=True)

        assert len(result) == 1
        assert result[0]["name"] == "test.txt"
        assert result[0]["type"] == "file"

    def test_exists_true(self, fs_with_mock: YaDiskFileSystem, mock_client: Mock) -> None:
        """Test exists when file exists."""
        mock_client.exists.return_value = True
        assert fs_with_mock.exists("/test.txt") is True

    def test_exists_false(self, fs_with_mock: YaDiskFileSystem, mock_client: Mock) -> None:
        """Test exists when file does not exist."""
        mock_client.exists.return_value = False
        assert fs_with_mock.exists("/nonexistent.txt") is False

    def test_isdir(self, fs_with_mock: YaDiskFileSystem, mock_client: Mock) -> None:
        """Test isdir method."""
        mock_client.is_dir.return_value = True
        assert fs_with_mock.isdir("/testdir") is True

        mock_client.is_dir.return_value = False
        assert fs_with_mock.isdir("/test.txt") is False

    def test_isfile(self, fs_with_mock: YaDiskFileSystem, mock_client: Mock) -> None:
        """Test isfile method."""
        mock_client.is_file.return_value = True
        assert fs_with_mock.isfile("/test.txt") is True

        mock_client.is_file.return_value = False
        assert fs_with_mock.isfile("/testdir") is False

    def test_cat_file(self, fs_with_mock: YaDiskFileSystem, mock_client: Mock) -> None:
        """Test reading file contents."""
        test_data = b"hello world"

        def mock_download(path: str, buffer: io.BytesIO) -> None:
            buffer.write(test_data)

        mock_client.download.side_effect = mock_download

        result = fs_with_mock.cat_file("/test.txt")
        assert result == test_data

    def test_pipe_file(self, fs_with_mock: YaDiskFileSystem, mock_client: Mock) -> None:
        """Test writing file contents."""
        test_data = b"hello world"

        fs_with_mock.pipe_file("/test.txt", test_data)

        mock_client.upload.assert_called_once()
        call_args = mock_client.upload.call_args
        assert call_args[0][1] == "/test.txt"
        assert call_args[1]["overwrite"] is True

    def test_mkdir(self, fs_with_mock: YaDiskFileSystem, mock_client: Mock) -> None:
        """Test directory creation."""
        fs_with_mock.mkdir("/new_dir")
        mock_client.makedirs.assert_called_once_with("/new_dir")

    def test_mkdir_no_parents(self, fs_with_mock: YaDiskFileSystem, mock_client: Mock) -> None:
        """Test directory creation without parents."""
        fs_with_mock.mkdir("/new_dir", create_parents=False)
        mock_client.mkdir.assert_called_once_with("/new_dir")

    def test_rm_file(self, fs_with_mock: YaDiskFileSystem, mock_client: Mock) -> None:
        """Test file removal."""
        fs_with_mock.rm_file("/test.txt")
        mock_client.remove.assert_called_once_with("/test.txt", permanently=True)

    def test_get_file(self, fs_with_mock: YaDiskFileSystem, mock_client: Mock) -> None:
        """Test downloading file."""
        fs_with_mock.get_file("/remote.txt", "/local.txt")
        mock_client.download.assert_called_once_with("/remote.txt", "/local.txt")

    def test_put_file(self, fs_with_mock: YaDiskFileSystem, mock_client: Mock) -> None:
        """Test uploading file."""
        fs_with_mock.put_file("/local.txt", "/remote.txt")
        mock_client.upload.assert_called_once_with(
            "/local.txt", "/remote.txt", overwrite=True
        )

    def test_cp_file(self, fs_with_mock: YaDiskFileSystem, mock_client: Mock) -> None:
        """Test copying file."""
        fs_with_mock.cp_file("/src.txt", "/dst.txt")
        mock_client.copy.assert_called_once_with("/src.txt", "/dst.txt", overwrite=True)

    def test_mv(self, fs_with_mock: YaDiskFileSystem, mock_client: Mock) -> None:
        """Test moving file."""
        fs_with_mock.mv("/src.txt", "/dst.txt")
        mock_client.move.assert_called_once_with("/src.txt", "/dst.txt", overwrite=True)

    def test_checksum(self, fs_with_mock: YaDiskFileSystem) -> None:
        """Test getting checksum."""
        result = fs_with_mock.checksum("/test.txt")
        assert result == "abc123def456"

    def test_size(self, fs_with_mock: YaDiskFileSystem) -> None:
        """Test getting file size."""
        result = fs_with_mock.size("/test.txt")
        assert result == 100


class TestCredentials:
    """Tests for credential handling."""

    def test_token_from_env(self) -> None:
        """Test credential preparation from environment."""
        with patch.dict(os.environ, {"YADISK_TOKEN": "env_token"}):
            with patch("dvc_yadisk.fs.Client") as mock_client_class:
                mock_client = Mock()
                mock_client.check_token.return_value = True
                mock_client_class.return_value = mock_client

                fs = YaDiskFileSystem()
                fs._get_yadisk_client()

                mock_client_class.assert_called_once_with(token="env_token")

    def test_token_missing(self) -> None:
        """Test error when token is missing."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("YADISK_TOKEN", None)
            fs = YaDiskFileSystem()

            with pytest.raises(ValueError, match="token is required"):
                fs._get_yadisk_client()
