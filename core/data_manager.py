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


# Loads persisted UI selections/settings from JSON file; affects app defaults
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


# Saves current selections/settings to JSON file; affects persistence across sessions
def save_persistent_settings(path: str, settings: Dict) -> None:
    """Write `settings` (dict) to `path` as JSON. Raises on error after logging.
    """
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to save persistent settings to {path}: {e}")
        raise


# Appends a mission record to the Excel log (creating file if missing); affects local log
def append_mission_to_excel(excel_path: str, data: Dict) -> bool:
    """Append a single mission record (dict) to an Excel file.
    If the file doesn't exist, create it with the single row. Returns True on success.
    """
    try:
        # Do not persist flair_colour into the Excel mission log. Flair is a UI/Discord
        # concern and should not be stored alongside mission rows.
        data_to_save = dict(data)
        if 'flair_colour' in data_to_save:
            del data_to_save['flair_colour']
        if 'Mega City' in data_to_save and 'Mega Structure' not in data_to_save:
            data_to_save['Mega Structure'] = data_to_save.pop('Mega City')
        new_data = pd.DataFrame([data_to_save])
        if os.path.exists(excel_path):
            existing_df = pd.read_excel(excel_path)
            if 'Mega City' in existing_df.columns:
                if 'Mega Structure' in existing_df.columns:
                    existing_df['Mega Structure'] = existing_df['Mega Structure'].where(
                        existing_df['Mega Structure'].notna(),
                        existing_df['Mega City']
                    )
                    existing_df = existing_df.drop(columns=['Mega City'])
                else:
                    existing_df = existing_df.rename(columns={'Mega City': 'Mega Structure'})
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


# Reads streak data from JSON; affects streak calculation
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


# Writes streak data to JSON; affects persisted streak history
def write_streaks(path: str, streaks: Dict) -> None:
    """Write streaks dict to path as JSON.
    """
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(streaks, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to write streaks to {path}: {e}")
        raise
