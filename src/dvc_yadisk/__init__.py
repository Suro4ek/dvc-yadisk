"""DVC plugin for Yandex Disk remote storage."""

from dvc_yadisk.fs import YaDiskFileSystem

__all__ = ["YaDiskFileSystem"]
__version__ = "0.1.2"


def _register_with_dvc() -> None:
    """Register YaDiskFileSystem with DVC's filesystem registry and config schema."""
    try:
        # Register filesystem
        from dvc.fs import registry

        if "yadisk" not in registry._registry:
            registry._registry["yadisk"] = {
                "class": "dvc_yadisk.YaDiskFileSystem",
                "err": "yadisk is supported, but requires 'dvc-yadisk' to be installed",
            }

        # Register config schema - need to rebuild SCHEMA with yadisk
        from dvc import config_schema

        if "yadisk" not in config_schema.REMOTE_SCHEMAS:
            config_schema.REMOTE_SCHEMAS["yadisk"] = {
                "token": str,
                **config_schema.REMOTE_COMMON,
            }
            # Rebuild the SCHEMA remote validator with updated REMOTE_SCHEMAS
            config_schema.SCHEMA["remote"] = {
                str: config_schema.ByUrl(config_schema.REMOTE_SCHEMAS)
            }
    except ImportError:
        # DVC not installed, skip registration
        pass


# Register on import
_register_with_dvc()


def get_async_filesystem() -> type:
    """Get async filesystem class (lazy import to avoid import errors)."""
    from dvc_yadisk.afs import AsyncYaDiskFileSystem

    return AsyncYaDiskFileSystem
