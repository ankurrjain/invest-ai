"""
Data formatting utilities for presenting financial data to LLMs and the UI.
"""
import pandas as pd
from typing import Any


def format_number(value: Any, decimals: int = 2, prefix: str = "", suffix: str = "") -> str:
    """Format a number with K/M/B/T suffixes."""
    if value is None:
        return "N/A"
    try:
        v = float(value)
        if pd.isna(v):
            return "N/A"
        abs_v = abs(v)
        if abs_v >= 1e12:
            return f"{prefix}{v/1e12:.{decimals}f}T{suffix}"
        elif abs_v >= 1e9:
            return f"{prefix}{v/1e9:.{decimals}f}B{suffix}"
        elif abs_v >= 1e6:
            return f"{prefix}{v/1e6:.{decimals}f}M{suffix}"
        elif abs_v >= 1e3:
            return f"{prefix}{v/1e3:.{decimals}f}K{suffix}"
        else:
            return f"{prefix}{v:.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return "N/A"


def format_pct(value: Any, decimals: int = 2) -> str:
    """Format a value as a percentage."""
    if value is None:
        return "N/A"
    try:
        v = float(value)
        if pd.isna(v):
            return "N/A"
        return f"{v*100:.{decimals}f}%"
    except (TypeError, ValueError):
        return "N/A"


def df_to_markdown(df: pd.DataFrame, max_rows: int = 8) -> str:
    """Convert a DataFrame to a compact markdown table string."""
    if df is None or df.empty:
        return "No data available."
    try:
        return df.head(max_rows).to_markdown(index=True)
    except Exception:
        return df.head(max_rows).to_string()


def safe_get(d: dict, key: str, default="N/A") -> Any:
    """Safely get a value from a dict, returning default if missing/None."""
    val = d.get(key)
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    return val
