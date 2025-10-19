"""
data_manager.py

Centralizes data loading/saving logic for MLHD2.

Public functions:
- load_persistent_settings(path) -> dict
- save_persistent_settings(path, settings: dict) -> None
- append_mission_to_excel(excel_path, data: dict) -> bool
- read_streaks(path) -> dict
- write_streaks(path, streaks: dict) -> None

This module intentionally keeps no global state; callers pass file paths used
by the main application. Exceptions are raised to callers or logged.
"""
import json
import os
import logging
from typing import Dict
import pandas as pd


def load_persistent_settings(path: str) -> Dict:
    """Load persistent settings from `path` returning a dict. If file is missing,
    returns an empty dict.
    """
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load persistent settings from {path}: {e}")
    return {}


def save_persistent_settings(path: str, settings: Dict) -> None:
    """Write `settings` (dict) to `path` as JSON. Raises on error after logging.
    """
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to save persistent settings to {path}: {e}")
        raise


def append_mission_to_excel(excel_path: str, data: Dict) -> bool:
    """Append a single mission record (dict) to an Excel file.
    If the file doesn't exist, create it with the single row. Returns True on success.
    """
    try:
        new_data = pd.DataFrame([data])
        if os.path.exists(excel_path):
            existing_df = pd.read_excel(excel_path)
            updated_df = pd.concat([existing_df, new_data], ignore_index=True)
        else:
            updated_df = new_data

        with pd.ExcelWriter(excel_path) as writer:
            updated_df.to_excel(writer, index=False)

        logging.info(f"Successfully appended data to {excel_path}")
        return True
    except Exception as e:
        logging.error(f"Error saving to Excel ({excel_path}): {e}")
        return False


def read_streaks(path: str) -> Dict:
    """Read streak data (JSON) from path; returns dict or empty dict on error.
    """
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Failed to read streaks from {path}: {e}")
    return {}


def write_streaks(path: str, streaks: Dict) -> None:
    """Write streaks dict to path as JSON.
    """
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(streaks, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to write streaks to {path}: {e}")
        raise
