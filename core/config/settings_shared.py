from __future__ import annotations

import os
from typing import Any

from core.infrastructure.runtime_paths import app_path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = app_path("JSON")
SETTINGS_PATH = app_path("JSON", "settings.json")
DCORD_PATH = app_path("JSON", "DCord.json")
PERSISTENT_PATH = app_path("JSON", "persistent.json")
FORCED_WEBHOOK_ENV_VAR = "MLHD2_FORCED_WEBHOOK_URL"

MEDIA_DIR = app_path("media")
MISC_ITEMS_DIR = app_path("media", "MiscItems")
GENERATED_BANNER_FILENAME = "GeneratedBanner.png"
GENERATED_BANNER_PATH = os.path.join(MISC_ITEMS_DIR, GENERATED_BANNER_FILENAME)
REPO_ROOT = os.path.dirname(JSON_DIR) if JSON_DIR else None


def norm(value: str) -> str:
    if value is None:
        return ""
    normalized = str(value).replace("\xa0", " ")
    return " ".join(normalized.strip().split()).casefold()


def get_forced_webhook_url() -> str:
    url = os.getenv(FORCED_WEBHOOK_ENV_VAR, "").strip()
    if url.lower().startswith(("http://", "https://")):
        return url
    return ""


def get_forced_webhooks_labeled() -> list[dict[str, str]]:
    forced_url = get_forced_webhook_url()
    if forced_url:
        return [{"label": "Forced", "url": forced_url}]
    return []


def make_theme(
    bg: str,
    fg: str,
    entry_bg: str | None = None,
    entry_fg: str | None = None,
    button_bg: str | None = None,
    button_fg: str | None = None,
    frame_bg: str | None = None,
) -> dict[str, dict[str, dict[str, Any]]]:
    return {
        ".": {"configure": {"background": bg, "foreground": fg}},
        "TLabel": {"configure": {"background": bg, "foreground": fg}},
        "TButton": {"configure": {"background": button_bg or bg, "foreground": button_fg or fg}},
        "TEntry": {
            "configure": {
                "background": entry_bg or bg,
                "foreground": entry_fg or fg,
                "fieldbackground": entry_bg or bg,
                "insertcolor": fg,
            }
        },
        "TCheckbutton": {"configure": {"background": bg, "foreground": fg}},
        "TCombobox": {
            "configure": {
                "background": entry_bg or bg,
                "foreground": entry_fg or fg,
                "fieldbackground": entry_bg or bg,
                "insertcolor": fg,
            }
        },
        "TFrame": {"configure": {"background": frame_bg or bg}},
        "TLabelframe": {"configure": {"background": frame_bg or bg, "foreground": fg}},
        "TLabelframe.Label": {"configure": {"background": frame_bg or bg, "foreground": fg}},
        "TNotebook": {"configure": {"background": bg}},
        "TNotebook.Tab": {"configure": {"background": button_bg or bg, "foreground": entry_fg or fg}},
    }


DEFAULT_THEME = make_theme(
    bg="#252526",
    fg="#FFFFFF",
    entry_bg="#252526",
    entry_fg="#000000",
    button_bg="#4C4C4C",
    button_fg="#000000",
    frame_bg="#252526",
)

SHIP1_OPTIONS = [
    "SES Adjudicator",
    "SES Advocate",
    "SES Aegis",
    "SES Agent",
    "SES Arbiter",
    "SES Banner",
    "SES Beacon",
    "SES Blade",
    "SES Bringer",
    "SES Champion",
    "SES Citizen",
    "SES Claw",
    "SES Colossus",
    "SES Comptroller",
    "SES Courier",
    "SES Custodian",
    "SES Dawn",
    "SES Defender",
    "SES Diamond",
    "SES Distributor",
    "SES Dream",
    "SES Elected Representative",
    "SES Emperor",
    "SES Executor",
    "SES Eye",
    "SES Father",
    "SES Fist",
    "SES Flame",
    "SES Force",
    "SES Forerunner",
    "SES Founding Father",
    "SES Gauntlet",
    "SES Giant",
    "SES Guardian",
    "SES Halo",
    "SES Hammer",
    "SES Harbinger",
    "SES Herald",
    "SES Judge",
    "SES Keeper",
    "SES King",
    "SES Knight",
    "SES Lady",
    "SES Legislator",
    "SES Leviathan",
    "SES Light",
    "SES Lord",
    "SES Magistrate",
    "SES Marshall",
    "SES Martyr",
    "SES Mirror",
    "SES Mother",
    "SES Octagon",
    "SES Ombudsman",
    "SES Panther",
    "SES Paragon",
    "SES Patriot",
    "SES Pledge",
    "SES Power",
    "SES Precursor",
    "SES Pride",
    "SES Prince",
    "SES Princess",
    "SES Progenitor",
    "SES Prophet",
    "SES Protector",
    "SES Purveyor",
    "SES Queen",
    "SES Ranger",
    "SES Reign",
    "SES Representative",
    "SES Senator",
    "SES Sentinel",
    "SES Shield",
    "SES Soldier",
    "SES Song",
    "SES Soul",
    "SES Sovereign",
    "SES Spear",
    "SES Stallion",
    "SES Star",
    "SES Steward",
    "SES Superintendent",
    "SES Sword",
    "SES Titan",
    "SES Triumph",
    "SES Warrior",
    "SES Whisper",
    "SES Will",
    "SES Wings",
]

SHIP2_OPTIONS = [
    "of Allegiance",
    "of Audacity",
    "of Authority",
    "of Battle",
    "of Benevolence",
    "of Conquest",
    "of Conviction",
    "of Conviviality",
    "of Courage",
    "of Dawn",
    "of Democracy",
    "of Destiny",
    "of Destruction",
    "of Determination",
    "of Equality",
    "of Eternity",
    "of Family Values",
    "of Fortitude",
    "of Freedom",
    "of Glory",
    "of Gold",
    "of Honour",
    "of Humankind",
    "of Independence",
    "of Individual Merit",
    "of Integrity",
    "of Iron",
    "of Judgement",
    "of Justice",
    "of Law",
    "of Liberty",
    "of Mercy",
    "of Midnight",
    "of Morality",
    "of Morning",
    "of Opportunity",
    "of Patriotism",
    "of Peace",
    "of Perseverance",
    "of Pride",
    "of Redemption",
    "of Science",
    "of Self-Determination",
    "of Selfless Service",
    "of Serenity",
    "of Starlight",
    "of Steel",
    "of Super Earth",
    "of Supremacy",
    "of the Constitution",
    "of the People",
    "of the Regime",
    "of the Stars",
    "of the State",
    "of Truth",
    "of Twilight",
    "of Victory",
    "of Vigilance",
    "of War",
    "of Wrath",
]
