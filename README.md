# dvc-yadisk

Yandex Disk remote storage plugin for [DVC](https://dvc.org) (Data Version Control).

## Installation

```bash
# Using uv
uv add dvc-yadisk

# Using pip
pip install dvc-yadisk
```

After installation, enable the plugin:

```bash
# Run the enable script to register the plugin with DVC
dvc-yadisk-enable
```

This creates a `sitecustomize.py` file in your Python environment that loads the plugin automatically when DVC starts.

## Configuration

### 1. Get Yandex Disk OAuth Token

1. Go to [Yandex Poginon](https://yandex.ru/dev/disk/poligon)
2. Create a token
3. Copy the token

### 2. Configure DVC Remote

```bash
# Add a Yandex Disk remote
dvc remote add -d myremote yadisk://my-dvc-data

# Set the OAuth token (use --local to avoid committing token to git)
dvc remote modify --local myremote token YOUR_OAUTH_TOKEN
```

Or use environment variable:

```bash
export YADISK_TOKEN=YOUR_OAUTH_TOKEN
```

### 3. Use DVC as Normal

```bash
# Track data
dvc add data/

# Push to Yandex Disk
dvc push

# Pull from Yandex Disk
dvc pull
```

## Configuration Options

| Option | Environment Variable | Description |
|--------|---------------------|-------------|
| `token` | `YADISK_TOKEN` | OAuth access token (required) |

## Example Usage

```python
from dvc_yadisk import YaDiskFileSystem

# Create filesystem instance
fs = YaDiskFileSystem(token="your_oauth_token")

# List files
files = fs.ls("my-folder")

# Check if file exists
exists = fs.exists("my-folder/data.csv")

# Read file
data = fs.cat_file("my-folder/data.csv")

# Write file
fs.pipe_file("my-folder/output.txt", b"Hello, World!")
```

### Async Usage

```python
import asyncio
from dvc_yadisk import get_async_filesystem

async def main():
    AsyncFS = get_async_filesystem()
    fs = AsyncFS(token="your_oauth_token")

    # List files
    files = await fs.ls("my-folder")

    # Read file
    data = await fs.cat_file("my-folder/data.csv")

asyncio.run(main())
```

## Limitations

- Maximum file size: 1GB (50GB for Yandex 360 subscribers)
- Upload URLs are valid for 30 minutes
- API rate limits apply

## Development

```bash
# Clone repository
git clone https://github.com/Suro4ek/dvc-yadisk.git
cd dvc-yadisk

# Install with dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=dvc_yadisk

# Type checking
uv run mypy src/dvc_yadisk

# Linting
uv run ruff check src/dvc_yadisk
```


## License

Apache License 2.0
