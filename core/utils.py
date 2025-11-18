import os
import json
import logging
from typing import Tuple, Dict, Optional


# Aggregates mission stats from Excel/streak files; affects flair validation
# Aggregates mission stats from local Excel/streak JSON; affects flair validation
def _read_mission_log_stats() -> Dict[str, int]:
    """Return mission log derived stats used for flair validation.

    Uses the same paths and logic as the export code in `core.app_core` so
    counts match what the export UI reports.
    """
    stats = {"total_deployments": 0, "has_super_earth": False, "highest_streak": 0}
    try:
        # Prefer app_core constants so we use the same production/test file paths
        from core import app_core

        # total_deployments: try app_core.total_missions() first (it already handles DEBUG/test),
        # but also attempt to read the actual DataFrame to compute has_super_earth and streak column.
        try:
            stats['total_deployments'] = int(app_core.total_missions())
        except Exception:
            stats['total_deployments'] = 0

        # Try to open the same Excel file used by app_core to compute other stats
        excel_file = app_core.EXCEL_FILE_TEST if getattr(app_core, 'DEBUG', False) else app_core.EXCEL_FILE_PROD
        if os.path.exists(excel_file):
            try:
                import pandas as pd
                df = pd.read_excel(excel_file)
                stats['total_deployments'] = len(df)
                stats['has_super_earth'] = 'Super Earth' in df['Planet'].values if 'Planet' in df.columns else False
                if 'Streak' in df.columns:
                    stats['highest_streak'] = int(df['Streak'].max())
            except Exception:
                # If pandas can't read, fall back to total_missions value
                pass

        # Also try the streak file provided by app_core for highest_streak fallback
        try:
            streak_path = getattr(app_core, 'streak_file', None)
            if streak_path and os.path.exists(streak_path):
                with open(streak_path, 'r', encoding='utf-8') as sf:
                    sdata = json.load(sf)
                json_highest = sdata.get('Helldiver', {}).get('highest_streak', 0)
                stats['highest_streak'] = max(stats['highest_streak'], int(json_highest or 0))
        except Exception:
            pass

    except Exception:
        # If app_core isn't importable, attempt a safe best-effort read from LOCALAPPDATA/MLHD2
        try:
            import pandas as pd
            APP_DATA = os.path.join(os.getenv('LOCALAPPDATA') or '', 'MLHD2')
            excel_file = os.path.join(APP_DATA, 'mission_log.xlsx')
            if os.path.exists(excel_file):
                df = pd.read_excel(excel_file)
                stats['total_deployments'] = len(df)
                stats['has_super_earth'] = 'Super Earth' in df['Planet'].values if 'Planet' in df.columns else False
                if 'Streak' in df.columns:
                    stats['highest_streak'] = int(df['Streak'].max())
        except Exception:
            pass

    return stats


# Validates whether a flair meets requirements; affects flair enforcement
# Validates flair eligibility using local stats; affects flair enforcement
def validate_flair(flair_name: str) -> Tuple[bool, Optional[str], Dict[str, int]]:
    """Return (allowed, message_if_not_allowed, stats).

    Uses the same thresholds as the app: Gold = 1000 deployments, Blue = at least one
    deployment on Super Earth, Red = highest streak >= 30.
    """
    stats = _read_mission_log_stats()
    name = (flair_name or '').strip()
    if not name:
        return True, None, stats
    key = name.capitalize()
    if key == 'Gold':
        if stats.get('total_deployments', 0) < 1000:
            return False, f"Gold Flair requires 1000 deployments (currently: {stats.get('total_deployments', 0)}).", stats
    elif key == 'Blue':
        if not stats.get('has_super_earth', False):
            return False, "Blue Flair requires a deployment on Super Earth.", stats
    elif key == 'Red':
        if stats.get('highest_streak', 0) < 30:
            return False, f"Red Flair requires a 30 streak (highest: {stats.get('highest_streak', 0)}).", stats
    return True, None, stats


# Returns saved flair if valid, else 'Default'; affects UI theming/overlays
# Reads saved flair and returns it only if valid; affects UI theming/overlays
def get_effective_flair(dcord_path: Optional[str] = None) -> str:
    """Read `DCord.json` and return saved flair if it meets requirements; otherwise 'Default'."""
    try:
        from core.runtime_paths import app_path
        if not dcord_path:
            dcord_path = app_path('JSON', 'DCord.json')
        if os.path.exists(dcord_path):
            with open(dcord_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            saved = (data.get('flair_colour') or 'Default').capitalize()
            ok, _, _ = validate_flair(saved)
            return saved if ok else 'Default'
    except Exception:
        pass
    return 'Default'


# ------------------ Other small helpers used across the app ------------------
from typing import Optional as _Optional


# Validates numeric string against bounds; affects field validation
# Validates numeric string within provided bounds; affects live entry validation
def is_valid_numeric_value(value: str, min_value: int = 0, max_value: int = 999999) -> bool:
    if value is None or value == "":
        return True
    try:
        ival = int(value)
        return min_value <= ival <= max_value
    except (ValueError, TypeError):
        return False


# Strips leading zeros from numeric strings; affects display normalization
def clean_numeric_string(s: _Optional[str]) -> str:
    if not s:
        return ""
    cleaned = s.lstrip('0')
    return cleaned if cleaned != '' else '0'


# Normalizes subfaction names to canonical keys; affects icon lookup
def normalize_subfaction_name(subfaction: str) -> str:
    normalized = " ".join(subfaction.split()).title()
    replacements = {
        "Jet Brigade": "JetBrigade",
        "Predator Strain": "PredatorStrain",
        "Incineration Corps": "IncinerationCorps",
        "Jet Brigade & Incineration Corps": "JetBrigadeIncinerationCorps",
        "Spore Burst Strain": "SporeBurstStrain",
        "The Great Host": "TheGreatHost",
        "Rupture Strain": "RuptureStrain",
        "Dragonroach": "Dragonroach",
        "Predator Strain & Dragonroach": "PredatorStrainDragonroach",
        "Spore Burst Strain & Dragonroach": "SporeBurstStrainDragonroach",
        "Rupture Strain & Dragonroach": "RuptureStrainDragonroach",
    }
    return replacements.get(normalized, normalized)


# Normalizes HVT names to canonical keys; affects icon lookup
def normalize_hvt_name(hvt: str) -> str:
    normalized = " ".join(hvt.split()).title()
    replacements = {"Hive Lords": "HiveLords"}
    return replacements.get(normalized, normalized)


# Returns a planet image URL via icon module; affects external references
def get_planet_image_url(planet_name: str) -> str:
    try:
        from core.icon import get_planet_image
        return get_planet_image(planet_name)
    except Exception:
        return ""
import os
import json
from typing import Tuple, Dict, Optional


def _read_mission_log_stats() -> Dict[str, int]:
    stats = {"total_deployments": 0, "has_super_earth": False, "highest_streak": 0}
    try:
        import pandas as pd
        APP_DATA = os.path.join(os.getenv('LOCALAPPDATA') or '', 'MLHD2')
        excel_file = os.path.join(APP_DATA, 'mission_log.xlsx')
        if os.path.exists(excel_file):
            try:
                df = pd.read_excel(excel_file)
                stats['total_deployments'] = len(df)
                stats['has_super_earth'] = 'Super Earth' in df['Planet'].values if 'Planet' in df.columns else False
                if 'Streak' in df.columns:
                    stats['highest_streak'] = int(df['Streak'].max())
            except Exception:
                pass
    except Exception:
        # If pandas isn't available or read fails, leave defaults
        pass

    # Try streak_data.json for additional streak info
    try:
        from core.runtime_paths import app_path
        streak_path = app_path('JSON', 'streak_data.json')
        if os.path.exists(streak_path):
            with open(streak_path, 'r', encoding='utf-8') as sf:
                streak_data = json.load(sf)
            json_highest = streak_data.get('Helldiver', {}).get('highest_streak', 0)
            stats['highest_streak'] = max(stats['highest_streak'], int(json_highest or 0))
    except Exception:
        pass

    return stats


def validate_flair(flair_name: str) -> Tuple[bool, Optional[str], Dict[str, int]]:
    """
    Validate whether the given flair is allowed based on local mission log and streak data.

    Returns: (allowed, message_if_not_allowed_or_None, stats)
    """
    stats = _read_mission_log_stats()
    name = (flair_name or '').strip()
    if not name:
        return True, None, stats
    # Normalize common variants
    key = name.capitalize()
    if key == 'Gold':
        if stats.get('total_deployments', 0) < 1000:
            return False, f"Gold Flair requires 1000 deployments (currently: {stats.get('total_deployments', 0)}).", stats
    elif key == 'Blue':
        if not stats.get('has_super_earth', False):
            return False, "Blue Flair requires a deployment on Super Earth.", stats
    elif key == 'Red':
        if stats.get('highest_streak', 0) < 30:
            return False, f"Red Flair requires a 30 streak (highest: {stats.get('highest_streak', 0)}).", stats
    return True, None, stats


def get_effective_flair(dcord_path: Optional[str] = None) -> str:
    """Read `DCord.json` (or given path) and return a flair that meets requirements.

    If the saved flair does not meet requirements, returns 'Default'.
    """
    try:
        from core.runtime_paths import app_path
        if not dcord_path:
            dcord_path = app_path('JSON', 'DCord.json')
        if os.path.exists(dcord_path):
            with open(dcord_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            saved = (data.get('flair_colour') or 'Default').capitalize()
            ok, _, _ = validate_flair(saved)
            return saved if ok else 'Default'
    except Exception:
        pass
    return 'Default'
"""Utility helpers: validation, normalization, and small wrappers.

This module centralizes small pure helpers used across the app so they can
be tested and maintained in one place.
"""
from typing import Optional
import logging

from core.icon import (
    ENEMY_ICONS,  
    DIFFICULTY_ICONS,
    SYSTEM_COLORS,
    PLANET_ICONS,
    CAMPAIGN_ICONS,
    MISSION_ICONS,
    BIOME_BANNERS,
    DSS_ICONS,
    TITLE_ICONS,
    PROFILE_PICTURES,
    SUBFACTION_ICONS,
    HVT_ICONS,
    get_planet_image,
)


def is_valid_numeric_value(value: str, min_value: int = 0, max_value: int = 999999) -> bool:
    """Return True if the provided string represents an int in the allowed range.

    Empty string is considered valid (useful for live-entry validation hooks).
    """
    if value is None or value == "":
        return True
    try:
        ival = int(value)
        return min_value <= ival <= max_value
    except (ValueError, TypeError):
        return False


# Normalizes numeric strings by removing leading zeros; affects display values
def clean_numeric_string(s: Optional[str]) -> str:
    """Normalize numeric entry strings by removing leading zeros.

    Returns empty string if input is falsy.
    """
    if not s:
        return ""
    # Remove leading zeros but keep exactly "0" if that was the intent
    cleaned = s.lstrip('0')
    return cleaned if cleaned != '' else '0'


# Normalizes subfaction to a canonical key; affects mapping lookups
def normalize_subfaction_name(subfaction: str) -> str:
    normalized = " ".join(subfaction.split()).title()
    replacements = {
        "Jet Brigade": "JetBrigade",
        "Predator Strain": "PredatorStrain",
        "Incineration Corps": "IncinerationCorps",
        "Jet Brigade & Incineration Corps": "JetBrigadeIncinerationCorps",
        "Spore Burst Strain": "SporeBurstStrain",
        "The Great Host": "TheGreatHost",
        "Rupture Strain": "RuptureStrain",
        "Dragonroach": "Dragonroach",
        "Predator Strain & Dragonroach": "PredatorStrainDragonroach",
        "Spore Burst Strain & Dragonroach": "SporeBurstStrainDragonroach",
        "Rupture Strain & Dragonroach": "RuptureStrainDragonroach"
    }
    return replacements.get(normalized, normalized)


# Normalizes HVT to a canonical key; affects mapping lookups
def normalize_hvt_name(hvt: str) -> str:
    normalized = " ".join(hvt.split()).title()
    replacements = {
        "Hive Lords": "HiveLords"
    }
    return replacements.get(normalized, normalized)


# Returns enemy icon key from constants; affects visual asset selection
def get_enemy_icon(enemy_type: str) -> str:
    return ENEMY_ICONS.get(enemy_type, "NaN")


# Returns difficulty icon key from constants; affects visual asset selection
def get_difficulty_icon(difficulty: str) -> str:
    return DIFFICULTY_ICONS.get(difficulty, "NaN")


# Returns planet icon key from constants; affects visual asset selection
def get_planet_icon(planet: str) -> str:
    return PLANET_ICONS.get(planet, "")


# Returns system color code for enemy; affects theming/icon tinting
def get_system_color(enemy_type: str) -> int:
    try:
        return int(SYSTEM_COLORS.get(enemy_type, "0"))
    except Exception:
        return 0


# Returns campaign icon key from constants; affects visual asset selection
def get_campaign_icon(mission_category: str) -> str:
    return CAMPAIGN_ICONS.get(mission_category, "")


# Returns mission icon key from constants; affects visual asset selection
def get_mission_icon(mission_type: str) -> str:
    return MISSION_ICONS.get(mission_type, "")


# Returns biome banner key from constants; affects banner selection
def get_biome_banner(planet: str) -> str:
    return BIOME_BANNERS.get(planet, "")


# Returns DSS icon key from constants; affects visual asset selection
def get_dss_icon(dss_modifier: str) -> str:
    return DSS_ICONS.get(dss_modifier, "")


# Returns title icon key from constants; affects visual asset selection
def get_title_icon(title: str) -> str:
    return TITLE_ICONS.get(title, "")


# Returns profile picture key from constants; affects profile visuals
def get_profile_picture(profile_picture: str) -> str:
    return PROFILE_PICTURES.get(profile_picture, "")


# Returns subfaction icon (empty if 'NaN'); affects visual asset selection
def get_subfaction_icon(subfaction_type: str) -> str:
    icon = SUBFACTION_ICONS.get(subfaction_type, "NaN")
    logging.info(f"Getting subfaction icon for '{subfaction_type}', found: {icon}")
    return "" if icon == "NaN" else icon


# Returns HVT icon (empty if 'NaN'); affects visual asset selection
def get_hvt_icon(hvt_type: str) -> str:
    icon = HVT_ICONS.get(normalize_hvt_name(hvt_type), "NaN")
    logging.info(f"Getting HVT icon for '{hvt_type}', found: {icon}")
    return "" if icon == "NaN" else icon


# Gets a planet image URL from constants module; affects external image links
def get_planet_image_url(planet_name: str) -> str:
    """Get the planet image URL based on the planet name."""
    return get_planet_image(planet_name)
