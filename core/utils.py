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


def clean_numeric_string(s: Optional[str]) -> str:
    """Normalize numeric entry strings by removing leading zeros.

    Returns empty string if input is falsy.
    """
    if not s:
        return ""
    # Remove leading zeros but keep exactly "0" if that was the intent
    cleaned = s.lstrip('0')
    return cleaned if cleaned != '' else '0'


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


def normalize_hvt_name(hvt: str) -> str:
    normalized = " ".join(hvt.split()).title()
    replacements = {
        "Hive Lords": "HiveLords"
    }
    return replacements.get(normalized, normalized)


def get_enemy_icon(enemy_type: str) -> str:
    return ENEMY_ICONS.get(enemy_type, "NaN")


def get_difficulty_icon(difficulty: str) -> str:
    return DIFFICULTY_ICONS.get(difficulty, "NaN")


def get_planet_icon(planet: str) -> str:
    return PLANET_ICONS.get(planet, "")


def get_system_color(enemy_type: str) -> int:
    try:
        return int(SYSTEM_COLORS.get(enemy_type, "0"))
    except Exception:
        return 0


def get_campaign_icon(mission_category: str) -> str:
    return CAMPAIGN_ICONS.get(mission_category, "")


def get_mission_icon(mission_type: str) -> str:
    return MISSION_ICONS.get(mission_type, "")


def get_biome_banner(planet: str) -> str:
    return BIOME_BANNERS.get(planet, "")


def get_dss_icon(dss_modifier: str) -> str:
    return DSS_ICONS.get(dss_modifier, "")


def get_title_icon(title: str) -> str:
    return TITLE_ICONS.get(title, "")


def get_profile_picture(profile_picture: str) -> str:
    return PROFILE_PICTURES.get(profile_picture, "")


def get_subfaction_icon(subfaction_type: str) -> str:
    icon = SUBFACTION_ICONS.get(subfaction_type, "NaN")
    logging.info(f"Getting subfaction icon for '{subfaction_type}', found: {icon}")
    return "" if icon == "NaN" else icon


def get_hvt_icon(hvt_type: str) -> str:
    icon = HVT_ICONS.get(normalize_hvt_name(hvt_type), "NaN")
    logging.info(f"Getting HVT icon for '{hvt_type}', found: {icon}")
    return "" if icon == "NaN" else icon
