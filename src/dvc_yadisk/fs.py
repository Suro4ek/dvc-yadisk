"""Yandex Disk filesystem implementation for DVC."""

from __future__ import annotations

import io
import os
import threading
from collections.abc import Iterator
from typing import Any, ClassVar

from dvc_objects.fs.base import ObjectFileSystem
from funcy import cached_property, wrap_prop
from yadisk import Client


class YaDiskFileSystem(ObjectFileSystem):
    """
    Yandex Disk filesystem implementation for DVC.

    Uses the yadisk library to interact with Yandex Disk REST API.
    Supports OAuth token-based authentication.
    """

    protocol = "yadisk"
    PARAM_CHECKSUM = "md5"
    REQUIRES: ClassVar[dict[str, str]] = {"yadisk": "yadisk"}
    TRAVERSE_WEIGHT_MULTIPLIER = 1

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize YaDiskFileSystem.

        Args:
            **kwargs: Configuration options including:
                - token: OAuth token (or use YADISK_TOKEN env var)
        """
        super().__init__(**kwargs)
        self._yadisk_client: Client | None = None
        self._yadisk_lock = threading.Lock()

    @classmethod
    def _strip_protocol(cls, path: str) -> str:
        """Remove yadisk:// protocol prefix from path."""
        if path.startswith("yadisk://"):
            return path[9:].lstrip("/")
        return path.lstrip("/")

    def unstrip_protocol(self, path: str) -> str:
        """Add yadisk:// protocol prefix to path."""
        return f"yadisk://{path.lstrip('/')}"

    def _normalize_path(self, path: str) -> str:
        """Normalize path to Yandex Disk format."""
        path = path.lstrip("/")
        return f"/{path}" if path else "/"

    def _strip_disk_prefix(self, path: str) -> str:
        """Remove disk: prefix from path."""
        if path.startswith("disk:"):
            return path[5:]
        return path

    def _get_yadisk_client(self) -> Client:
        """Get or create yadisk client (thread-safe)."""
        if self._yadisk_client is None:
            with self._yadisk_lock:
                if self._yadisk_client is None:
                    token = self.fs_args.get("token") or os.environ.get("YADISK_TOKEN")
                    if not token:
                        raise ValueError(
                            "Yandex Disk token is required. "
                            "Set via 'token' config or YADISK_TOKEN env var."
                        )

                    client = Client(token=token)
                    if not client.check_token():
                        raise ValueError("Invalid Yandex Disk token")

                    self._yadisk_client = client
        return self._yadisk_client

    @wrap_prop(threading.Lock())  # type: ignore[untyped-decorator]
    @cached_property  # type: ignore[untyped-decorator]
    def fs(self) -> YaDiskFileSystem:
        """Return self as the filesystem (required by ObjectFileSystem)."""
        return self

    def info(self, path: str, **kwargs: Any) -> dict[str, Any]:  # type: ignore[override]
        """Get file/directory metadata."""
        client = self._get_yadisk_client()
        norm_path = self._normalize_path(self._strip_protocol(path))
        meta = client.get_meta(norm_path)
        return {
            "name": meta.name,
            "path": self._strip_disk_prefix(meta.path or ""),
            "size": meta.size or 0,
            "type": "directory" if meta.type == "dir" else "file",
            "md5": getattr(meta, "md5", None),
        }

    def ls(self, path: str, detail: bool = False, **kwargs: Any) -> list[Any]:  # type: ignore[override]
        """List directory contents."""
        client = self._get_yadisk_client()
        norm_path = self._normalize_path(self._strip_protocol(path))
        items = list(client.listdir(norm_path))

        if detail:
            return [
                {
                    "name": item.name,
                    "path": self._strip_disk_prefix(item.path or ""),
                    "size": item.size or 0,
                    "type": "directory" if item.type == "dir" else "file",
                    "md5": getattr(item, "md5", None),
                }
                for item in items
            ]
        return [self._strip_disk_prefix(item.path or "") for item in items]

    def find(  # type: ignore[override]
        self,
        path: str,
        prefix: str = "",
        maxdepth: int | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        """Recursively find all files under path."""
        client = self._get_yadisk_client()
        base_path = self._strip_protocol(path)
        norm_path = self._normalize_path(base_path)

        def _find_recursive(current_path: str, depth: int) -> Iterator[str]:
            if maxdepth is not None and depth > maxdepth:
                return

            try:
                for item in client.listdir(current_path):
                    item_path = self._strip_disk_prefix(item.path or "")
                    # Remove leading slash for consistency
                    item_path = item_path.lstrip("/")

                    if not item_path:
                        continue

                    if prefix and not (item.name or "").startswith(prefix):
                        continue

                    if item.type == "dir":
                        yield from _find_recursive(item.path or "", depth + 1)
                    else:
                        yield item_path
            except Exception:
                return

        yield from _find_recursive(norm_path, 0)

    def exists(  # type: ignore[override]
        self, path: str | list[str], batch_size: int | None = None, **kwargs: Any
    ) -> bool | list[bool]:
        """Check if path(s) exist."""
        # Handle batch exists for DVC compatibility
        if isinstance(path, (list, tuple)):
            return [self._single_exists(p) for p in path]
        return self._single_exists(path)

    def _single_exists(self, path: str) -> bool:
        """Check if a single path exists."""
        try:
            client = self._get_yadisk_client()
            norm_path = self._normalize_path(self._strip_protocol(path))
            result: bool = client.exists(norm_path)
            return result
        except Exception:
            return False

    def isdir(self, path: str, **kwargs: Any) -> bool:
        """Check if path is a directory."""
        try:
            client = self._get_yadisk_client()
            norm_path = self._normalize_path(self._strip_protocol(path))
            result: bool = client.is_dir(norm_path)
            return result
        except Exception:
            return False

    def isfile(self, path: str, **kwargs: Any) -> bool:
        """Check if path is a file."""
        try:
            client = self._get_yadisk_client()
            norm_path = self._normalize_path(self._strip_protocol(path))
            result: bool = client.is_file(norm_path)
            return result
        except Exception:
            return False

    def mkdir(self, path: str, create_parents: bool = True, **kwargs: Any) -> None:
        """Create directory."""
        client = self._get_yadisk_client()
        norm_path = self._normalize_path(self._strip_protocol(path))
        if create_parents:
            client.makedirs(norm_path)
        else:
            client.mkdir(norm_path)

    def makedirs(self, path: str, exist_ok: bool = True, **kwargs: Any) -> None:
        """Create directory and all parent directories."""
        client = self._get_yadisk_client()
        norm_path = self._normalize_path(self._strip_protocol(path))
        try:
            client.makedirs(norm_path)
        except Exception:
            if not exist_ok:
                raise

    def rm_file(self, path: str, **kwargs: Any) -> None:
        """Remove a single file."""
        client = self._get_yadisk_client()
        norm_path = self._normalize_path(self._strip_protocol(path))
        client.remove(norm_path, permanently=True)

    def rm(self, path: str, recursive: bool = False, **kwargs: Any) -> None:  # type: ignore[override]
        """Remove file or directory."""
        client = self._get_yadisk_client()
        norm_path = self._normalize_path(self._strip_protocol(path))
        client.remove(norm_path, permanently=True)

    def rmdir(self, path: str, **kwargs: Any) -> None:
        """Remove empty directory."""
        client = self._get_yadisk_client()
        norm_path = self._normalize_path(self._strip_protocol(path))
        client.remove(norm_path, permanently=True)

    def cat_file(self, path: str, **kwargs: Any) -> bytes:  # type: ignore[override]
        """Read file contents."""
        client = self._get_yadisk_client()
        norm_path = self._normalize_path(self._strip_protocol(path))
        buffer = io.BytesIO()
        client.download(norm_path, buffer)
        buffer.seek(0)
        return buffer.read()

    def pipe_file(self, path: str, data: bytes, **kwargs: Any) -> None:  # type: ignore[override]
        """Write data to file."""
        client = self._get_yadisk_client()
        norm_path = self._normalize_path(self._strip_protocol(path))

        # Ensure parent directory exists
        parent = "/".join(norm_path.split("/")[:-1])
        if parent and parent != "/":
            try:
                client.makedirs(parent)
            except Exception:
                pass

        buffer = io.BytesIO(data)
        client.upload(buffer, norm_path, overwrite=True)

    def get_file(self, rpath: str, lpath: str, **kwargs: Any) -> None:  # type: ignore[override]
        """Download file from Yandex Disk to local path."""
        client = self._get_yadisk_client()
        norm_path = self._normalize_path(self._strip_protocol(rpath))
        client.download(norm_path, lpath)

    def put_file(self, lpath: str, rpath: str, **kwargs: Any) -> None:  # type: ignore[override]
        """Upload file from local path to Yandex Disk."""
        client = self._get_yadisk_client()
        norm_path = self._normalize_path(self._strip_protocol(rpath))

        # Ensure parent directory exists
        parent = "/".join(norm_path.split("/")[:-1])
        if parent and parent != "/":
            try:
                client.makedirs(parent)
            except Exception:
                pass

        client.upload(lpath, norm_path, overwrite=True)

    def cp_file(self, path1: str, path2: str, **kwargs: Any) -> None:  # type: ignore[override]
        """Copy file within Yandex Disk."""
        client = self._get_yadisk_client()
        src = self._normalize_path(self._strip_protocol(path1))
        dst = self._normalize_path(self._strip_protocol(path2))
        client.copy(src, dst, overwrite=True)

    def mv(self, path1: str, path2: str, **kwargs: Any) -> None:  # type: ignore[override]
        """Move/rename file or directory."""
        client = self._get_yadisk_client()
        src = self._normalize_path(self._strip_protocol(path1))
        dst = self._normalize_path(self._strip_protocol(path2))
        client.move(src, dst, overwrite=True)

    def checksum(self, path: str, **kwargs: Any) -> str | None:  # type: ignore[override]
        """Get MD5 checksum for file."""
        info = self.info(path)
        return info.get("md5")

    def size(self, path: str, **kwargs: Any) -> int:
        """Get file size in bytes."""
        info = self.info(path)
        size: int = info.get("size", 0)
        return size
