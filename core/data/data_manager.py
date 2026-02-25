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

import configparser
import json
import logging
import os
import sqlite3
import threading
import time
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from core.infrastructure.logging_config import log_event
from core.infrastructure.runtime_paths import app_path


# Loads persisted UI selections/settings from JSON file; affects app defaults
def load_persistent_settings(path: str) -> Dict:
    """Load persistent settings from `path` returning a dict. If file is missing,
    returns an empty dict.
    """
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load persistent settings from {path}: {e}")
    return {}


# Saves current selections/settings to JSON file; affects persistence across sessions
def save_persistent_settings(path: str, settings: Dict) -> None:
    """Write `settings` (dict) to `path` as JSON. Raises on error after logging."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to save persistent settings to {path}: {e}")
        raise


@lru_cache(maxsize=1)
def _get_debug_mode() -> bool:
    try:
        config = configparser.ConfigParser()
        config.read(app_path("orphan", "config.config"))
        return config.getboolean("DEBUGGING", "DEBUG", fallback=False)
    except Exception:
        return False


def get_runtime_excel_path(debug: Optional[bool] = None) -> str:
    app_data = os.path.join(os.getenv("LOCALAPPDATA") or "", "MLHD2")
    os.makedirs(app_data, exist_ok=True)
    is_debug = _get_debug_mode() if debug is None else bool(debug)
    return os.path.join(app_data, "mission_log_test.xlsx" if is_debug else "mission_log.xlsx")


def _normalize_mission_schema(df: pd.DataFrame) -> pd.DataFrame:
    if "Mega City" in df.columns:
        if "Mega Structure" in df.columns:
            df["Mega Structure"] = df["Mega Structure"].where(df["Mega Structure"].notna(), df["Mega City"])
            df = df.drop(columns=["Mega City"])
        else:
            df = df.rename(columns={"Mega City": "Mega Structure"})
    return df


class MissionDataService:
    """Centralized mission data access with lightweight in-memory caching.

    Optional SQLite support is available via env vars:
    - MLHD2_DATA_BACKEND=sqlite
    - MLHD2_SQLITE_PATH=<path to sqlite db>

    Excel remains the source-of-truth and is always written for compatibility.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._excel_cache: Dict[str, Dict[str, Any]] = {}
        self._last_row_cache: Dict[str, Dict] = {}
        self.backend = str(os.getenv("MLHD2_DATA_BACKEND", "excel")).strip().lower()
        self.sqlite_path = str(os.getenv("MLHD2_SQLITE_PATH", "")).strip()

    def _file_state(self, excel_path: str) -> Tuple[bool, Optional[float], Optional[int]]:
        if not os.path.exists(excel_path):
            return False, None, None
        stat = os.stat(excel_path)
        return True, stat.st_mtime, stat.st_size

    def invalidate_cache(self, excel_path: Optional[str] = None) -> None:
        with self._lock:
            if excel_path:
                self._excel_cache.pop(excel_path, None)
                self._last_row_cache.pop(excel_path, None)
            else:
                self._excel_cache.clear()
                self._last_row_cache.clear()

    def read_mission_log(self, excel_path: str, use_cache: bool = True) -> pd.DataFrame:
        started = time.perf_counter()
        with self._lock:
            exists, mtime, size = self._file_state(excel_path)
            if not exists:
                empty = pd.DataFrame()
                self._excel_cache[excel_path] = {"mtime": None, "size": None, "df": empty}
                self._last_row_cache[excel_path] = {}
                log_event(
                    logging.getLogger(__name__),
                    logging.INFO,
                    f"Mission log not found at {excel_path}; returning empty dataframe",
                    module="data_manager",
                    action="read_mission_log",
                    outcome="empty",
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
                return empty.copy()

            cached = self._excel_cache.get(excel_path)
            if use_cache and cached and cached.get("mtime") == mtime and cached.get("size") == size:
                log_event(
                    logging.getLogger(__name__),
                    logging.DEBUG,
                    f"Mission log cache hit for {excel_path}",
                    module="data_manager",
                    action="read_mission_log",
                    outcome="cache_hit",
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
                return cached["df"].copy()

            df = pd.read_excel(excel_path)
            df = _normalize_mission_schema(df)
            self._excel_cache[excel_path] = {"mtime": mtime, "size": size, "df": df}
            self._last_row_cache[excel_path] = df.iloc[-1].to_dict() if not df.empty else {}
            log_event(
                logging.getLogger(__name__),
                logging.INFO,
                f"Mission log loaded from {excel_path}",
                module="data_manager",
                action="read_mission_log",
                outcome="success",
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            return df.copy()

    def read_runtime_mission_log(self, debug: Optional[bool] = None, use_cache: bool = True) -> pd.DataFrame:
        return self.read_mission_log(get_runtime_excel_path(debug), use_cache=use_cache)

    def get_last_mission_row(self, excel_path: str, use_cache: bool = True) -> Optional[Dict]:
        with self._lock:
            if use_cache and excel_path in self._last_row_cache:
                row = self._last_row_cache.get(excel_path) or {}
                return dict(row) if row else None

            df = self.read_mission_log(excel_path, use_cache=use_cache)
            if df.empty:
                self._last_row_cache[excel_path] = {}
                return None
            row = df.iloc[-1].to_dict()
            self._last_row_cache[excel_path] = row
            return dict(row)

    def get_runtime_summary(self, debug: Optional[bool] = None) -> Dict[str, object]:
        excel_path = get_runtime_excel_path(debug)
        df = self.read_mission_log(excel_path, use_cache=True)
        has_super_earth = False
        if not df.empty and "Planet" in df.columns:
            try:
                has_super_earth = bool((df["Planet"].astype(str).str.strip() == "Super Earth").any())
            except Exception:
                has_super_earth = False
        return {
            "total_deployments": int(len(df)),
            "has_super_earth": has_super_earth,
            "excel_path": excel_path,
        }

    def _sanitize_mission_payload(self, data: Dict) -> Dict:
        payload = dict(data)
        if "flair_colour" in payload:
            del payload["flair_colour"]
        if "Mega City" in payload and "Mega Structure" not in payload:
            payload["Mega Structure"] = payload.pop("Mega City")
        return payload

    def append_mission(self, excel_path: str, data: Dict) -> bool:
        started = time.perf_counter()
        try:
            payload = self._sanitize_mission_payload(data)
            new_row = pd.DataFrame([payload])

            existing_df = self.read_mission_log(excel_path, use_cache=True)
            updated_df = pd.concat([existing_df, new_row], ignore_index=True) if not existing_df.empty else new_row
            updated_df = _normalize_mission_schema(updated_df)

            with pd.ExcelWriter(excel_path) as writer:
                updated_df.to_excel(writer, index=False)

            self.invalidate_cache(excel_path)
            with self._lock:
                self._last_row_cache[excel_path] = payload

            if self.backend == "sqlite" and self.sqlite_path:
                self._mirror_row_to_sqlite(payload)

            log_event(
                logging.getLogger(__name__),
                logging.INFO,
                f"Successfully appended mission data to {excel_path}",
                module="data_manager",
                action="append_mission",
                outcome="success",
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            return True
        except Exception as e:
            log_event(
                logging.getLogger(__name__),
                logging.ERROR,
                f"Error saving to Excel ({excel_path}): {e}",
                module="data_manager",
                action="append_mission",
                outcome="failure",
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            return False

    def _mirror_row_to_sqlite(self, data: Dict) -> None:
        try:
            os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)
            conn = sqlite3.connect(self.sqlite_path)
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS mission_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    time TEXT,
                    planet TEXT,
                    enemy_type TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                INSERT INTO mission_log (time, planet, enemy_type, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(data.get("Time", "")),
                    str(data.get("Planet", "")),
                    str(data.get("Enemy Type", "")),
                    json.dumps(data, ensure_ascii=False),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logging.warning(f"SQLite mirror write failed ({self.sqlite_path}): {e}")


_MISSION_DATA_SERVICE = MissionDataService()


def get_mission_data_service() -> MissionDataService:
    return _MISSION_DATA_SERVICE


# Appends a mission record to the Excel log (creating file if missing); affects local log
def append_mission_to_excel(excel_path: str, data: Dict) -> bool:
    """Append a single mission record (dict) to an Excel file.
    If the file doesn't exist, create it with the single row. Returns True on success.
    """
    return get_mission_data_service().append_mission(excel_path, data)


# Reads streak data from JSON; affects streak calculation
def read_streaks(path: str) -> Dict:
    """Read streak data (JSON) from path; returns dict or empty dict on error."""
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Failed to read streaks from {path}: {e}")
    return {}


# Writes streak data to JSON; affects persisted streak history
def write_streaks(path: str, streaks: Dict) -> None:
    """Write streaks dict to path as JSON."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(streaks, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to write streaks to {path}: {e}")
        raise
