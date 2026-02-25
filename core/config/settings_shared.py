from __future__ import annotations

import configparser
import json
import os
from typing import Any

from core.infrastructure.runtime_paths import app_path

# Check DEBUG mode from config.config
config = configparser.ConfigParser()
config.read(app_path("orphan", "config.config"))
# Try both uppercase and lowercase for compatibility
DEBUG = config.getboolean("DEBUGGING", "DEBUG", fallback=None)
if DEBUG is None:
    DEBUG = config.getboolean("DEBUGGING", "debug", fallback=False)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = app_path("JSON")
SETTINGS_PATH = app_path("JSON", "settings-dev.json" if DEBUG else "settings.json")
DCORD_PATH = app_path("JSON", "DCord-dev.json" if DEBUG else "DCord.json")
PERSISTENT_PATH = app_path("JSON", "persistent-dev.json" if DEBUG else "persistent.json")
FORCED_WEBHOOK_ENV_VAR = "MLHD2_FORCED_WEBHOOK_URL"
FORCED_WEBHOOKS_ENV_VAR = "MLHD2_FORCED_WEBHOOK_URLS"
LOGGING_WEBHOOKS_ENV_VAR = "MLHD2_WEBHOOKS_LOGGING"
EXPORT_WEBHOOKS_ENV_VAR = "MLHD2_WEBHOOKS_EXPORT"
BOOSTER_WEBHOOKS_FILENAME = "booster_webhooks.json"
DOTENV_PATH = app_path(".env")
BOOSTER_WEBHOOKS_PATH = app_path(BOOSTER_WEBHOOKS_FILENAME)

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


def _load_dotenv(path: str) -> None:
    if not path or not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'").strip('"')
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        return


def _is_valid_webhook_url(url: str) -> bool:
    return bool(url) and url.lower().startswith(("http://", "https://"))


def _parse_webhook_list(raw: str) -> list[str]:
    if not raw:
        return []
    urls = [u.strip() for u in raw.split(",") if u.strip()]
    return [u for u in urls if _is_valid_webhook_url(u)]


_load_dotenv(DOTENV_PATH)


def get_forced_webhook_url() -> str:
    url = os.getenv(FORCED_WEBHOOK_ENV_VAR, "").strip()
    if _is_valid_webhook_url(url):
        return url
    return ""


def _get_env_webhook_urls(kind: str) -> list[str]:
    urls: list[str] = []
    forced_single = get_forced_webhook_url()
    if forced_single:
        urls.append(forced_single)
    urls.extend(_parse_webhook_list(os.getenv(FORCED_WEBHOOKS_ENV_VAR, "")))

    if kind == "logging":
        urls.extend(_parse_webhook_list(os.getenv(LOGGING_WEBHOOKS_ENV_VAR, "")))
    elif kind == "export":
        urls.extend(_parse_webhook_list(os.getenv(EXPORT_WEBHOOKS_ENV_VAR, "")))

    return urls


def _get_booster_webhook_urls(kind: str) -> list[str]:
    if not BOOSTER_WEBHOOKS_PATH or not os.path.isfile(BOOSTER_WEBHOOKS_PATH):
        return []
    try:
        with open(BOOSTER_WEBHOOKS_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return []

    urls: list[str] = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str) and _is_valid_webhook_url(item):
                urls.append(item)
        return urls

    if not isinstance(data, dict):
        return []

    def _extend_from_key(key: str) -> None:
        entries = data.get(key, [])
        if isinstance(entries, list):
            for item in entries:
                if isinstance(item, str) and _is_valid_webhook_url(item):
                    urls.append(item)
                elif isinstance(item, dict):
                    url = str(item.get("url", "")).strip()
                    if _is_valid_webhook_url(url):
                        urls.append(url)

    if kind == "logging":
        _extend_from_key("logging")
        _extend_from_key("logs")
        _extend_from_key("discord_webhooks_logging")
    elif kind == "export":
        _extend_from_key("export")
        _extend_from_key("exports")
        _extend_from_key("discord_webhooks_export")

    webhook_items = data.get("webhooks", [])
    if isinstance(webhook_items, list):
        for item in webhook_items:
            if isinstance(item, dict):
                item_kind = str(item.get("type", item.get("kind", ""))).strip().lower()
                url = str(item.get("url", "")).strip()
                if item_kind and item_kind != kind:
                    continue
                if _is_valid_webhook_url(url):
                    urls.append(url)
            elif isinstance(item, str) and _is_valid_webhook_url(item):
                urls.append(item)

    return urls


def get_extra_webhook_urls(kind: str) -> list[str]:
    urls: list[str] = []
    urls.extend(_get_env_webhook_urls(kind))
    urls.extend(_get_booster_webhook_urls(kind))
    # De-dupe while preserving order
    seen = set()
    deduped = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        deduped.append(url)
    return deduped


def get_forced_webhooks_labeled() -> list[dict[str, str]]:
    forced_url = get_forced_webhook_url()
    labeled: list[dict[str, str]] = []
    if forced_url:
        labeled.append({"label": "Forced", "url": forced_url})
    for idx, url in enumerate(_parse_webhook_list(os.getenv(FORCED_WEBHOOKS_ENV_VAR, "")), start=1):
        labeled.append({"label": f"Forced {idx}", "url": url})
    return labeled


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
