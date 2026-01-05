"""CLI tools for dvc-yadisk plugin."""

from __future__ import annotations

import os
import sys


def enable() -> None:
    """Enable dvc-yadisk plugin by creating sitecustomize.py."""
    # Find site-packages directory
    site_packages = None
    for path in sys.path:
        if "site-packages" in path and os.path.isdir(path):
            site_packages = path
            break

    if not site_packages:
        print("Error: Could not find site-packages directory")
        sys.exit(1)

    sitecustomize_path = os.path.join(site_packages, "sitecustomize.py")

    # Check if sitecustomize.py exists and contains our import
    import_line = "import dvc_yadisk"
    if os.path.exists(sitecustomize_path):
        with open(sitecustomize_path) as f:
            content = f.read()
        if import_line in content:
            print(f"dvc-yadisk is already enabled in {sitecustomize_path}")
            return
        # Append our import
        with open(sitecustomize_path, "a") as f:
            f.write(f"\n# dvc-yadisk plugin\ntry:\n    {import_line}\n")
            f.write("except ImportError:\n    pass\n")
    else:
        # Create new sitecustomize.py
        with open(sitecustomize_path, "w") as f:
            f.write(f"# dvc-yadisk plugin\ntry:\n    {import_line}\n")
            f.write("except ImportError:\n    pass\n")

    print("dvc-yadisk enabled successfully!")
    print(f"Created/updated: {sitecustomize_path}")
    print("\nYou can now use: dvc remote add myremote yadisk://path")


def disable() -> None:
    """Disable dvc-yadisk plugin by removing from sitecustomize.py."""
    site_packages = None
    for path in sys.path:
        if "site-packages" in path and os.path.isdir(path):
            site_packages = path
            break

    if not site_packages:
        print("Error: Could not find site-packages directory")
        sys.exit(1)

    sitecustomize_path = os.path.join(site_packages, "sitecustomize.py")

    if not os.path.exists(sitecustomize_path):
        print("sitecustomize.py not found, nothing to disable")
        return

    with open(sitecustomize_path) as f:
        lines = f.readlines()

    # Remove dvc-yadisk related lines
    new_lines = []
    skip_block = False
    for line in lines:
        if "# dvc-yadisk plugin" in line:
            skip_block = True
            continue
        if skip_block and line.strip() == "":
            skip_block = False
            continue
        is_dvc_yadisk_line = (
            "import dvc_yadisk" in line
            or line.startswith("try:")
            or line.startswith("except")
            or line.strip() == "pass"
        )
        if skip_block and is_dvc_yadisk_line:
            continue
        skip_block = False
        new_lines.append(line)

    if new_lines and all(line.strip() == "" for line in new_lines):
        # File is now empty, remove it
        os.remove(sitecustomize_path)
        print(f"Removed empty {sitecustomize_path}")
    else:
        with open(sitecustomize_path, "w") as f:
            f.writelines(new_lines)
        print(f"dvc-yadisk disabled in {sitecustomize_path}")


if __name__ == "__main__":
    enable()
