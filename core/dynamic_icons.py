"""
Dynamic icon management module for MLHD2
Handles all dynamic icon generation based on player data with JSON caching

CACHING SYSTEM:
- Dynamic planet data is cached in JSON/dynamic_icons.json for performance
- Cache is updated automatically when missions are submitted
- On startup, cache is initialized if it doesn't exist or is invalid
- Functions ending in "_from_excel" read directly from Excel (used for cache updates)
- Main functions (without "_from_excel") read from JSON cache for fast access

USAGE:
- apply_dynamic_planet_icons() - Apply cached dynamic icons to base planet icons
- get_dynamic_planet_data() - Get all cached dynamic planet information
- update_dynamic_icons_from_excel() - Refresh cache from Excel (called on mission submit)
- initialize_dynamic_icons_cache() - Initialize cache on app startup
- force_refresh_cache() - Manual cache refresh for troubleshooting
"""

import configparser
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from core.data.data_manager import get_mission_data_service, get_runtime_excel_path
from core.infrastructure.runtime_paths import app_path

# Load config
iconconfig = configparser.ConfigParser()
iconconfig.read(app_path("orphan", "icon.config"))

# JSON file path for caching dynamic icon data
DYNAMIC_ICONS_JSON = Path(__file__).parent.parent.joinpath("JSON", "dynamic_icons.json")


def load_dynamic_icons_cache() -> Dict[str, str]:
    # Load cached dynamic planet data; affects planet icon overlays in UI/exports
    """
    Load dynamic icon data from JSON cache file

    Returns:
        Dict: Dictionary containing cached dynamic planet data
    """
    try:
        if os.path.exists(DYNAMIC_ICONS_JSON):
            with open(DYNAMIC_ICONS_JSON, "r") as f:
                data = json.load(f)
                # Ensure all required keys exist with defaults
                return {
                    "first_ingress": data.get("first_ingress", "Super Earth"),
                    "ingress_100": data.get("ingress_100", "Super Earth"),
                    "ingress_1k": data.get("ingress_1k", "Super Earth"),
                    "favourite_planet": data.get("favourite_planet", "Super Earth"),
                    "player_homeworld": data.get("player_homeworld", "Super Earth"),
                    "highest_kills_planet": data.get("highest_kills_planet", "Super Earth"),
                    "highest_deaths_planet": data.get("highest_deaths_planet", "Super Earth"),
                    "last_updated": data.get("last_updated", ""),
                }
    except Exception as e:
        logging.error(f"Error loading dynamic icons cache: {e}")

    # Return defaults if file doesn't exist or error occurred
    return {
        "first_ingress": "Super Earth",
        "ingress_100": "Super Earth",
        "ingress_1k": "Super Earth",
        "favourite_planet": "Super Earth",
        "player_homeworld": "Super Earth",
        "highest_kills_planet": "Super Earth",
        "highest_deaths_planet": "Super Earth",
        "last_updated": "",
    }


def save_dynamic_icons_cache(data: Dict[str, str]) -> bool:
    # Persist dynamic planet data cache; keeps UI overlays up-to-date
    """
    Save dynamic icon data to JSON cache file

    Args:
        data: Dictionary containing dynamic planet data to save

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Add timestamp
        data["last_updated"] = datetime.now().isoformat()

        # Prefer a repo-root JSON/ directory when present so developers' JSON
        # folder is used during development. Otherwise fall back to the
        # app_path-derived location. Ensure the parent directory exists.
        try:
            repo_root_json = Path(__file__).parent.parent.joinpath("JSON", "dynamic_icons.json")
        except Exception:
            repo_root_json = None

        candidate = None
        if repo_root_json and repo_root_json.exists():
            candidate = repo_root_json
        else:
            # Current working directory JSON folder is also a valid developer location
            cwd_json = Path.cwd().joinpath("JSON", "dynamic_icons.json")
            if cwd_json.exists():
                candidate = cwd_json
            else:
                candidate = Path(DYNAMIC_ICONS_JSON)

        parent_dir = candidate.parent
        try:
            os.makedirs(str(parent_dir), exist_ok=True)
        except Exception:
            # If directory creation fails, proceed and let open() raise
            pass

        with open(str(candidate), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logging.error(f"Error saving dynamic icons cache: {e}")
        return False


def _compute_dynamic_data_from_df(df: Optional[pd.DataFrame] = None) -> Dict[str, str]:
    data = {
        "first_ingress": "Super Earth",
        "ingress_100": "",
        "ingress_1k": "",
        "favourite_planet": "Super Earth",
        "player_homeworld": load_player_homeworld_from_settings(),
        "highest_kills_planet": "Super Earth",
        "highest_deaths_planet": "Super Earth",
    }
    try:
        if df is None:
            excel_path = get_runtime_excel_path()
            df = get_mission_data_service().read_mission_log(excel_path, use_cache=True)

        if df is None or df.empty:
            return data

        if "Planet" in df.columns:
            planets = df["Planet"].dropna().astype(str).str.strip()
            if not planets.empty:
                data["favourite_planet"] = str(planets.value_counts().index[0]).strip()

        if "Time" in df.columns and "Planet" in df.columns:
            ordered = df[["Time", "Planet"]].copy()
            ordered["Time"] = pd.to_datetime(
                ordered["Time"].astype(str).str.replace("/", "-", regex=False),
                errors="coerce",
                dayfirst=True,
            )
            ordered["Planet"] = ordered["Planet"].astype(str).str.strip()
            ordered = ordered.dropna(subset=["Time", "Planet"]).sort_values("Time")
            if not ordered.empty:
                data["first_ingress"] = str(ordered["Planet"].iloc[0]).strip()
                if len(ordered) >= 100:
                    data["ingress_100"] = str(ordered["Planet"].iloc[99]).strip()
                if len(ordered) >= 1000:
                    data["ingress_1k"] = str(ordered["Planet"].iloc[999]).strip()

        if "Planet" in df.columns and "Kills" in df.columns:
            kills_df = df[["Planet", "Kills"]].copy()
            kills_df["Kills"] = pd.to_numeric(kills_df["Kills"], errors="coerce").fillna(0)
            kills_df["Planet"] = kills_df["Planet"].astype(str).str.strip()
            kills_df = kills_df.dropna(subset=["Planet"])
            grouped = kills_df.groupby("Planet")["Kills"].sum()
            if not grouped.empty:
                data["highest_kills_planet"] = str(grouped.idxmax()).strip()

        if "Planet" in df.columns and "Deaths" in df.columns:
            deaths_df = df[["Planet", "Deaths"]].copy()
            deaths_df["Deaths"] = pd.to_numeric(deaths_df["Deaths"], errors="coerce").fillna(0)
            deaths_df["Planet"] = deaths_df["Planet"].astype(str).str.strip()
            deaths_df = deaths_df.dropna(subset=["Planet"])
            grouped = deaths_df.groupby("Planet")["Deaths"].sum()
            if not grouped.empty:
                data["highest_deaths_planet"] = str(grouped.idxmax()).strip()
    except Exception as e:
        logging.error(f"Error computing dynamic icon data from mission log: {e}")
    return data


def get_first_ingress_from_excel() -> str:
    # Read first mission planet from Excel; feeds dynamic planet overlay
    return _compute_dynamic_data_from_df().get("first_ingress", "Super Earth")


def get_ingress_100_from_excel() -> str:
    # Read 100th mission planet from Excel; updates dynamic overlay badges
    return _compute_dynamic_data_from_df().get("ingress_100", "")


def get_ingress_1k_from_excel() -> str:
    # Read 1000th mission planet from Excel; updates dynamic overlay badges
    return _compute_dynamic_data_from_df().get("ingress_1k", "")


def get_most_played_planet_from_excel() -> str:
    # Compute most played planet (favourite) from Excel; used in overlays
    return _compute_dynamic_data_from_df().get("favourite_planet", "Super Earth")


def load_player_homeworld_from_settings() -> str:
    # Load player homeworld from settings JSON; applies homeworld icon overlay
    """Load player's homeworld from settings (reads settings.json directly)"""
    try:
        with open(app_path("JSON", "settings.json"), "r") as f:
            settings = json.load(f)
            return settings.get("Player Homeworld", "Super Earth")
    except Exception as e:
        logging.error(f"Error loading player homeworld from settings: {e}")
        return "Super Earth"


def get_highest_kills_planet_from_excel() -> str:
    # Compute planet with highest total kills; adds kills badge overlay
    return _compute_dynamic_data_from_df().get("highest_kills_planet", "Super Earth")


def get_highest_deaths_planet_from_excel() -> str:
    # Compute planet with highest total deaths; adds deaths badge overlay
    return _compute_dynamic_data_from_df().get("highest_deaths_planet", "Super Earth")


def apply_dynamic_planet_icons(base_planet_icons: Dict[str, str]) -> Dict[str, str]:
    # Merge dynamic badges into base planet icons; updates UI iconography
    """
    Apply all dynamic planet icons to the base planet icons dictionary
    Uses cached JSON data for performance

    Args:
        base_planet_icons: Dictionary of base planet icons

    Returns:
        Dict: Updated planet icons with dynamic icons applied
    """
    # Create a copy to avoid modifying the original
    planet_icons = base_planet_icons.copy()

    # Get dynamic planet data from cache
    dynamic_data = load_dynamic_icons_cache()
    first_ingress = dynamic_data["first_ingress"]
    ingress_100 = dynamic_data["ingress_100"]
    ingress_1k = dynamic_data["ingress_1k"]
    most_played_planet = dynamic_data["favourite_planet"]
    player_homeworld = dynamic_data["player_homeworld"]
    highest_kills_planet = dynamic_data["highest_kills_planet"]
    highest_deaths_planet = dynamic_data["highest_deaths_planet"]

    # Apply First Ingress icon
    first_ingress_icon = iconconfig["PlanetIcons"]["First Ingress"]
    if first_ingress in planet_icons:
        existing_icon = planet_icons[first_ingress]
        planet_icons[first_ingress] = f"{existing_icon}{first_ingress_icon}"
    else:
        planet_icons[first_ingress] = first_ingress_icon

    # Apply 100th Ingress icon
    ingress_100_icon = iconconfig["PlanetIcons"]["Ingress 100"]
    if ingress_100 in planet_icons and ingress_100 != "Super Earth":
        existing_icon = planet_icons[ingress_100]
        planet_icons[ingress_100] = f"{existing_icon}{ingress_100_icon}"
    elif ingress_100 != "Super Earth":
        planet_icons[ingress_100] = ingress_100_icon

    # Apply 1000th Ingress icon
    ingress_1k_icon = iconconfig["PlanetIcons"]["Ingress 1k"]
    if ingress_1k in planet_icons and ingress_1k != "Super Earth":
        existing_icon = planet_icons[ingress_1k]
        planet_icons[ingress_1k] = f"{existing_icon}{ingress_1k_icon}"
    elif ingress_1k != "Super Earth":
        planet_icons[ingress_1k] = ingress_1k_icon

    # Apply Favourite Planet icon
    favourite_planet_icon = iconconfig["PlanetIcons"]["Favourite Planet"]
    if most_played_planet in planet_icons:
        existing_icon = planet_icons[most_played_planet]
        planet_icons[most_played_planet] = f"{existing_icon}{favourite_planet_icon}"
    else:
        planet_icons[most_played_planet] = favourite_planet_icon

    # Apply Player Homeworld icon
    player_homeworld_icon = iconconfig["PlanetIcons"]["Player Homeworld"]
    if player_homeworld in planet_icons:
        existing_icon = planet_icons[player_homeworld]
        planet_icons[player_homeworld] = f"{existing_icon}{player_homeworld_icon}"
    else:
        planet_icons[player_homeworld] = player_homeworld_icon

    # Apply Highest Planet Kills icon
    try:
        highest_kills_icon = iconconfig["PlanetIcons"]["Highest Planet Kills"]
        if highest_kills_planet in planet_icons:
            existing_icon = planet_icons[highest_kills_planet]
            planet_icons[highest_kills_planet] = f"{existing_icon}{highest_kills_icon}"
        else:
            planet_icons[highest_kills_planet] = highest_kills_icon
    except KeyError:
        logging.warning("Highest Planet Kills icon not found in config")

    # Apply Highest Planet Deaths icon
    try:
        highest_deaths_icon = iconconfig["PlanetIcons"]["Highest Planet Deaths"]
        if highest_deaths_planet in planet_icons:
            existing_icon = planet_icons[highest_deaths_planet]
            planet_icons[highest_deaths_planet] = f"{existing_icon}{highest_deaths_icon}"
        else:
            planet_icons[highest_deaths_planet] = highest_deaths_icon
    except KeyError:
        logging.warning("Highest Planet Deaths icon not found in config")

    return planet_icons


def get_dynamic_planet_data() -> Dict[str, str]:
    # Expose cached dynamic planet metadata; used by UI and exports
    """
    Get all dynamic planet data from JSON cache

    Returns:
        Dict: Dictionary containing all cached dynamic planet information
    """
    return load_dynamic_icons_cache()


def update_dynamic_icons_from_excel() -> bool:
    # Refresh dynamic icon data from Excel/settings; called on mission submit
    """
    Update dynamic icon data by reading from Excel and settings, then save to JSON cache
    This should be called when missions are submitted to refresh the data

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        excel_path = get_runtime_excel_path()
        df = get_mission_data_service().read_mission_log(excel_path, use_cache=True)
        data = _compute_dynamic_data_from_df(df)

        # Save to JSON cache
        success = save_dynamic_icons_cache(data)
        if success:
            logging.info("Dynamic icons cache updated successfully from Excel")
        return success

    except Exception as e:
        logging.error(f"Error updating dynamic icons from Excel: {e}")
        return False


def initialize_dynamic_icons_cache() -> bool:
    # Ensure dynamic icons cache exists and is valid; runs at app startup
    """
    Initialize the dynamic icons cache if it doesn't exist or is invalid
    This should be called on application startup

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if cache file exists and is valid
        if not os.path.exists(DYNAMIC_ICONS_JSON):
            logging.info("Dynamic icons cache doesn't exist, creating from Excel data")
            return update_dynamic_icons_from_excel()

        # Check if cache has all required keys
        cache_data = load_dynamic_icons_cache()
        required_keys = [
            "first_ingress",
            "ingress_100",
            "ingress_1k",
            "favourite_planet",
            "player_homeworld",
            "highest_kills_planet",
            "highest_deaths_planet",
        ]

        if not all(key in cache_data for key in required_keys):
            logging.info("Dynamic icons cache is incomplete, refreshing from Excel data")
            return update_dynamic_icons_from_excel()

        logging.info("Dynamic icons cache loaded successfully")
        return True

    except Exception as e:
        logging.error(f"Error initializing dynamic icons cache: {e}")
        return update_dynamic_icons_from_excel()  # Try to recover by updating from Excel


def get_cache_last_updated() -> str:
    # Return cache last-updated timestamp; useful for diagnostics/UI tooltips
    """
    Get the timestamp when the cache was last updated

    Returns:
        str: ISO format timestamp or empty string if not available
    """
    try:
        cache_data = load_dynamic_icons_cache()
        return cache_data.get("last_updated", "")
    except Exception:
        return ""


def force_refresh_cache() -> bool:
    # Force rebuild of dynamic icons cache from Excel; troubleshooting UI badges
    """
    Force refresh the dynamic icons cache from Excel data
    Useful for manual refresh or troubleshooting

    Returns:
        bool: True if successful, False otherwise
    """
    logging.info("Force refreshing dynamic icons cache...")
    return update_dynamic_icons_from_excel()
