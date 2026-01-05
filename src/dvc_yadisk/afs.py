"""Async Yandex Disk filesystem implementation for DVC."""

from __future__ import annotations

import io
import os
from collections.abc import AsyncIterator
from typing import Any

from yadisk import AsyncClient


class AsyncYaDiskFS:
    """
    Async fsspec-compatible filesystem wrapper around yadisk.AsyncClient.

    Implements async versions of filesystem operations for better performance
    with large files and concurrent operations.
    """

    def __init__(self, client: Any) -> None:
        """
        Initialize with an authenticated yadisk AsyncClient.

        Args:
            client: Authenticated yadisk.AsyncClient instance
        """
        self._client = client

    def _normalize_path(self, path: str) -> str:
        """Normalize path to Yandex Disk format."""
        path = path.lstrip("/")
        if not path.startswith("disk:/"):
            return f"/{path}"
        return path.replace("disk:", "")

    def _strip_disk_prefix(self, path: str) -> str:
        """Remove disk: prefix from path."""
        if path.startswith("disk:"):
            return path[5:]
        return path

    async def info(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """Get metadata for a file or directory."""
        norm_path = self._normalize_path(path)
        meta = await self._client.get_meta(norm_path)
        return {
            "name": meta.name,
            "path": self._strip_disk_prefix(meta.path),
            "size": meta.size or 0,
            "type": "directory" if meta.type == "dir" else "file",
            "md5": getattr(meta, "md5", None),
            "created": meta.created,
            "modified": meta.modified,
        }

    async def ls(self, path: str, detail: bool = False, **kwargs: Any) -> list[Any]:
        """List directory contents."""
        norm_path = self._normalize_path(path)
        items = [item async for item in self._client.listdir(norm_path)]

        if detail:
            return [
                {
                    "name": item.name,
                    "path": self._strip_disk_prefix(item.path),
                    "size": item.size or 0,
                    "type": "directory" if item.type == "dir" else "file",
                    "md5": getattr(item, "md5", None),
                }
                for item in items
            ]
        return [self._strip_disk_prefix(item.path) for item in items]

    async def find(
        self, path: str, prefix: str = "", maxdepth: int | None = None, **kwargs: Any
    ) -> AsyncIterator[str]:
        """Recursively find all files under path."""
        norm_path = self._normalize_path(path)

        async def _find_recursive(current_path: str, depth: int) -> AsyncIterator[str]:
            if maxdepth is not None and depth > maxdepth:
                return

            async for item in self._client.listdir(current_path):
                item_path = self._strip_disk_prefix(item.path)

                if prefix and not item.name.startswith(prefix):
                    continue

                if item.type == "dir":
                    async for p in _find_recursive(item.path, depth + 1):
                        yield p
                else:
                    yield item_path

        async for p in _find_recursive(norm_path, 0):
            yield p

    async def exists(self, path: str, **kwargs: Any) -> bool:
        """Check if path exists."""
        try:
            norm_path = self._normalize_path(path)
            result: bool = await self._client.exists(norm_path)
            return result
        except Exception:
            return False

    async def isdir(self, path: str, **kwargs: Any) -> bool:
        """Check if path is a directory."""
        try:
            norm_path = self._normalize_path(path)
            result: bool = await self._client.is_dir(norm_path)
            return result
        except Exception:
            return False

    async def isfile(self, path: str, **kwargs: Any) -> bool:
        """Check if path is a file."""
        try:
            norm_path = self._normalize_path(path)
            result: bool = await self._client.is_file(norm_path)
            return result
        except Exception:
            return False

    async def mkdir(self, path: str, create_parents: bool = True, **kwargs: Any) -> None:
        """Create directory."""
        norm_path = self._normalize_path(path)
        if create_parents:
            await self._client.makedirs(norm_path)
        else:
            await self._client.mkdir(norm_path)

    async def makedirs(self, path: str, exist_ok: bool = True, **kwargs: Any) -> None:
        """Create directory and all parent directories."""
        norm_path = self._normalize_path(path)
        try:
            await self._client.makedirs(norm_path)
        except Exception:
            if not exist_ok:
                raise

    async def rm_file(self, path: str, **kwargs: Any) -> None:
        """Remove a single file."""
        norm_path = self._normalize_path(path)
        await self._client.remove(norm_path, permanently=True)

    async def rm(self, path: str, recursive: bool = False, **kwargs: Any) -> None:
        """Remove file or directory."""
        norm_path = self._normalize_path(path)
        await self._client.remove(norm_path, permanently=True)

    async def rmdir(self, path: str, **kwargs: Any) -> None:
        """Remove empty directory."""
        norm_path = self._normalize_path(path)
        await self._client.remove(norm_path, permanently=True)

    async def cat_file(self, path: str, **kwargs: Any) -> bytes:
        """Read file contents."""
        norm_path = self._normalize_path(path)
        buffer = io.BytesIO()
        await self._client.download(norm_path, buffer)
        buffer.seek(0)
        return buffer.read()

    async def pipe_file(self, path: str, data: bytes, **kwargs: Any) -> None:
        """Write data to file."""
        norm_path = self._normalize_path(path)

        # Ensure parent directory exists
        parent = "/".join(norm_path.split("/")[:-1])
        if parent and parent != "/":
            try:
                await self._client.makedirs(parent)
            except Exception:
                pass

        buffer = io.BytesIO(data)
        await self._client.upload(buffer, norm_path, overwrite=True)

    async def get_file(self, rpath: str, lpath: str, **kwargs: Any) -> None:
        """Download file from Yandex Disk to local path."""
        norm_path = self._normalize_path(rpath)
        await self._client.download(norm_path, lpath)

    async def put_file(self, lpath: str, rpath: str, **kwargs: Any) -> None:
        """Upload file from local path to Yandex Disk."""
        norm_path = self._normalize_path(rpath)

        # Ensure parent directory exists
        parent = "/".join(norm_path.split("/")[:-1])
        if parent and parent != "/":
            try:
                await self._client.makedirs(parent)
            except Exception:
                pass

        await self._client.upload(lpath, norm_path, overwrite=True)

    async def cp_file(self, path1: str, path2: str, **kwargs: Any) -> None:
        """Copy file within Yandex Disk."""
        src = self._normalize_path(path1)
        dst = self._normalize_path(path2)
        await self._client.copy(src, dst, overwrite=True)

    async def mv(self, path1: str, path2: str, **kwargs: Any) -> None:
        """Move/rename file or directory."""
        src = self._normalize_path(path1)
        dst = self._normalize_path(path2)
        await self._client.move(src, dst, overwrite=True)

    async def checksum(self, path: str, **kwargs: Any) -> str | None:
        """Get MD5 checksum for file."""
        info = await self.info(path)
        return info.get("md5")

    async def size(self, path: str, **kwargs: Any) -> int:
        """Get file size in bytes."""
        info = await self.info(path)
        size: int = info.get("size", 0)
        return size


class AsyncYaDiskFileSystem:
    """
    Async Yandex Disk filesystem for DVC.

    Use this when you need async operations for better performance.
    """

    protocol = "yadisk"
    PARAM_CHECKSUM = "md5"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize AsyncYaDiskFileSystem."""
        self._kwargs = kwargs
        self._fs: AsyncYaDiskFS | None = None

    @classmethod
    def _strip_protocol(cls, path: str) -> str:
        """Remove yadisk:// protocol prefix from path."""
        if path.startswith("yadisk://"):
            return path[9:].lstrip("/")
        return path.lstrip("/")

    def _prepare_credentials(self) -> dict[str, Any]:
        """Prepare credentials for yadisk AsyncClient."""
        token = self._kwargs.get("token") or os.environ.get("YADISK_TOKEN")
        if not token:
            raise ValueError(
                "Yandex Disk token is required. "
                "Set it via 'token' config option or YADISK_TOKEN environment variable."
            )
        return {"token": token}

    async def _get_fs(self) -> AsyncYaDiskFS:
        """Get or create the async filesystem instance."""
        if self._fs is None:
            credentials = self._prepare_credentials()
            client = AsyncClient(**credentials)

            if not await client.check_token():
                raise ValueError("Invalid Yandex Disk token")

            self._fs = AsyncYaDiskFS(client)
        return self._fs

    async def info(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """Get file/directory metadata."""
        fs = await self._get_fs()
        return await fs.info(self._strip_protocol(path), **kwargs)

    async def ls(self, path: str, detail: bool = False, **kwargs: Any) -> list[Any]:
        """List directory contents."""
        fs = await self._get_fs()
        return await fs.ls(self._strip_protocol(path), detail=detail, **kwargs)

    async def exists(self, path: str, **kwargs: Any) -> bool:
        """Check if path exists."""
        fs = await self._get_fs()
        return await fs.exists(self._strip_protocol(path), **kwargs)

    async def mkdir(self, path: str, **kwargs: Any) -> None:
        """Create directory."""
        fs = await self._get_fs()
        await fs.mkdir(self._strip_protocol(path), **kwargs)

    async def rm_file(self, path: str, **kwargs: Any) -> None:
        """Remove file."""
        fs = await self._get_fs()
        await fs.rm_file(self._strip_protocol(path), **kwargs)

    async def cat_file(self, path: str, **kwargs: Any) -> bytes:
        """Read file contents."""
        fs = await self._get_fs()
        return await fs.cat_file(self._strip_protocol(path), **kwargs)

    async def pipe_file(self, path: str, data: bytes, **kwargs: Any) -> None:
        """Write data to file."""
        fs = await self._get_fs()
        await fs.pipe_file(self._strip_protocol(path), data, **kwargs)

    async def get_file(self, rpath: str, lpath: str, **kwargs: Any) -> None:
        """Download file."""
        fs = await self._get_fs()
        await fs.get_file(self._strip_protocol(rpath), lpath, **kwargs)

    async def put_file(self, lpath: str, rpath: str, **kwargs: Any) -> None:
        """Upload file."""
        fs = await self._get_fs()
        await fs.put_file(lpath, self._strip_protocol(rpath), **kwargs)
