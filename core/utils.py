import json
import logging
import os
from typing import Dict, Optional, Tuple

from core.icon import (
    BIOME_BANNERS,
    CAMPAIGN_ICONS,
    DIFFICULTY_ICONS,
    DSS_ICONS,
    ENEMY_ICONS,
    HVT_ICONS,
    MISSION_ICONS,
    PLANET_ICONS,
    PROFILE_PICTURES,
    SUBFACTION_ICONS,
    SYSTEM_COLORS,
    TITLE_ICONS,
    get_planet_image,
)


def _read_mission_log_stats() -> Dict[str, int]:
    """Return mission log derived stats used for flair validation."""
    stats = {"total_deployments": 0, "has_super_earth": False, "highest_streak": 0}
    try:
        from core import app_core

        try:
            stats["total_deployments"] = int(app_core.total_missions())
        except Exception:
            stats["total_deployments"] = 0

        excel_file = app_core.EXCEL_FILE_TEST if getattr(app_core, "DEBUG", False) else app_core.EXCEL_FILE_PROD
        if os.path.exists(excel_file):
            try:
                import pandas as pd

                df = pd.read_excel(excel_file)
                stats["total_deployments"] = len(df)
                stats["has_super_earth"] = "Super Earth" in df["Planet"].values if "Planet" in df.columns else False
                if "Streak" in df.columns:
                    stats["highest_streak"] = int(df["Streak"].max())
            except Exception:
                pass

        try:
            streak_path = getattr(app_core, "streak_file", None)
            if streak_path and os.path.exists(streak_path):
                with open(streak_path, "r", encoding="utf-8") as sf:
                    streak_data = json.load(sf)
                json_highest = streak_data.get("Helldiver", {}).get("highest_streak", 0)
                stats["highest_streak"] = max(stats["highest_streak"], int(json_highest or 0))
        except Exception:
            pass

    except Exception:
        try:
            import pandas as pd

            app_data = os.path.join(os.getenv("LOCALAPPDATA") or "", "MLHD2")
            excel_file = os.path.join(app_data, "mission_log.xlsx")
            if os.path.exists(excel_file):
                df = pd.read_excel(excel_file)
                stats["total_deployments"] = len(df)
                stats["has_super_earth"] = "Super Earth" in df["Planet"].values if "Planet" in df.columns else False
                if "Streak" in df.columns:
                    stats["highest_streak"] = int(df["Streak"].max())
        except Exception:
            pass

        try:
            from core.infrastructure.runtime_paths import app_path

            streak_path = app_path("JSON", "streak_data.json")
            if os.path.exists(streak_path):
                with open(streak_path, "r", encoding="utf-8") as sf:
                    streak_data = json.load(sf)
                json_highest = streak_data.get("Helldiver", {}).get("highest_streak", 0)
                stats["highest_streak"] = max(stats["highest_streak"], int(json_highest or 0))
        except Exception:
            pass

    return stats


def validate_flair(flair_name: str) -> Tuple[bool, Optional[str], Dict[str, int]]:
    """Validate flair against local mission requirements."""
    stats = _read_mission_log_stats()
    key = (flair_name or "").strip().capitalize()
    if not key:
        return True, None, stats

    if key == "Gold" and stats.get("total_deployments", 0) < 1000:
        return False, f"Gold Flair requires 1000 deployments (currently: {stats.get('total_deployments', 0)}).", stats
    if key == "Blue" and not stats.get("has_super_earth", False):
        return False, "Blue Flair requires a deployment on Super Earth.", stats
    if key == "Red" and stats.get("highest_streak", 0) < 30:
        return False, f"Red Flair requires a 30 streak (highest: {stats.get('highest_streak', 0)}).", stats

    return True, None, stats


def get_effective_flair(dcord_path: Optional[str] = None) -> str:
    """Return saved flair if valid, otherwise 'Default'."""
    try:
        from core.infrastructure.runtime_paths import app_path

        if not dcord_path:
            dcord_path = app_path("JSON", "DCord.json")
        if os.path.exists(dcord_path):
            with open(dcord_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            saved = (data.get("flair_colour") or "Default").capitalize()
            ok, _, _ = validate_flair(saved)
            return saved if ok else "Default"
    except Exception:
        pass
    return "Default"


def is_valid_numeric_value(value: str, min_value: int = 0, max_value: int = 999999) -> bool:
    if value is None or value == "":
        return True
    try:
        ival = int(value)
        return min_value <= ival <= max_value
    except (ValueError, TypeError):
        return False


def clean_numeric_string(s: Optional[str]) -> str:
    if not s:
        return ""
    cleaned = s.lstrip("0")
    return cleaned if cleaned != "" else "0"


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
        "Cyborgs": "Cyborgs",
        "Cyborgs & Jet Brigade": "CyborgsJetBrigade",
        "Cyborgs & Incineration Corps": "CyborgsIncinerationCorps",
        "Cyborgs, Jet Brigade & Incineration Corps": "CyborgsJetBrigadeIncinerationCorps",
    }
    return replacements.get(normalized, normalized)


def normalize_hvt_name(hvt: str) -> str:
    normalized = " ".join(hvt.split()).title()
    replacements = {"Hive Lords": "HiveLords"}
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


def get_planet_image_url(planet_name: str) -> str:
    return get_planet_image(planet_name)


def get_profile_pictures_list() -> list:
    """Return profile picture names merged from JSON and icon mapping."""
    try:
        from core.infrastructure.runtime_paths import app_path

        json_path = app_path("JSON", "ProfilePictures.json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            pics = data.get("Profile Pictures", []) or []
        else:
            pics = []

        mapped_keys = list(PROFILE_PICTURES.keys())

        combined = []
        for name in pics:
            if name not in combined:
                combined.append(name)
        for name in mapped_keys:
            if name not in combined:
                combined.append(name)
        pics = combined

        try:
            secret_path = app_path("secret")
            if os.path.exists(secret_path):
                if "ML-13 Red Eagle" not in pics:
                    pics.append("ML-13 Red Eagle")
                if "ML-3326 Supreme Guard" not in pics:
                    pics.append("ML-3326 Supreme Guard")
        except Exception:
            pass

        return sorted(pics, key=lambda s: s.lower())
    except Exception:
        return sorted(list(dict.fromkeys(PROFILE_PICTURES.keys())), key=lambda s: s.lower())
