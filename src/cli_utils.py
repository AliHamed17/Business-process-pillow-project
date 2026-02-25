from __future__ import annotations

from pathlib import Path


def ensure_exists(path: str | Path, description: str) -> Path:
    """Validate that a required path exists and return it as Path."""
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"{description} not found: {target}")
    return target


def ensure_output_dir(path: str | Path) -> Path:
    """Create output directory when missing and return it as Path."""
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target
