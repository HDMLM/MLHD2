from __future__ import annotations

import pandas as pd

MISSION_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "Mega Structure": ("Mega Structure", "Mega City"),
}


def normalize_mission_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize known mission field aliases to canonical column names."""
    if "Mega Structure" not in df.columns and "Mega City" in df.columns:
        df = df.rename(columns={"Mega City": "Mega Structure"})
    if "Mega Structure" not in df.columns:
        df["Mega Structure"] = ""
    return df


def get_mega_structure_series(df: pd.DataFrame) -> pd.Series:
    if "Mega Structure" in df.columns:
        return df["Mega Structure"]
    if "Mega City" in df.columns:
        return df["Mega City"]
    return pd.Series([""] * len(df), index=df.index)