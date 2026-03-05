from __future__ import annotations

from pathlib import Path

import pandas as pd


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


def validate_columns(df: pd.DataFrame, required_columns: list[str], context: str) -> None:
    """Raise a clear error if required columns are missing."""
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns for {context}: {missing}")


def load_clean_log(logfile_path: str | Path, required_columns: list[str], context: str) -> pd.DataFrame:
    """Load a cleaned log CSV, parse timestamp, and validate required columns."""
    df = pd.read_csv(logfile_path)
    validate_columns(df, required_columns, context)
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

    before_drop = len(df)
    df = df.dropna(subset=['case_id', 'activity', 'timestamp']).copy()
    dropped = before_drop - len(df)
    if dropped:
        print(f"Warning: dropped {dropped} rows with missing case_id/activity/timestamp in {context}.")

    return df
