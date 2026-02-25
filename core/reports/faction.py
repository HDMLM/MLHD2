import configparser
import json
import logging
import os
from datetime import datetime

import pandas as pd

from core.app_core import DEV_RELEASE, VERSION
from core.integrations.discord_integration import _sanitize_embed
from core.icon import (
    BIOME_BANNERS,
    CAMPAIGN_ICONS,
    DIFFICULTY_ICONS,
    ENEMY_ICONS,
    MISSION_ICONS,
    PLANET_ICONS,
    SUBFACTION_ICONS,
    TITLE_ICONS,
    get_badge_icons,
)
from core.infrastructure.logging_config import setup_logging
from core.infrastructure.runtime_paths import app_path
from core.integrations.webhook import post_webhook

# Set up application data paths
APP_DATA = os.path.join(os.getenv("LOCALAPPDATA"), "MLHD2")
if not os.path.exists(APP_DATA):
    os.makedirs(APP_DATA)

EXCEL_FILE_PROD = os.path.join(APP_DATA, "mission_log.xlsx")
EXCEL_FILE_TEST = os.path.join(APP_DATA, "mission_log_test.xlsx")
DATE_FORMAT = "%d-%m-%Y %H:%M:%S"

# Read config file
config = configparser.ConfigParser()
config.read(app_path("orphan", "config.config"))
iconconfig = configparser.ConfigParser()
iconconfig.read(app_path("orphan", "icon.config"))

date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

# Constants
DEBUG = config.getboolean("DEBUGGING", "DEBUG", fallback=False)
setup_logging(DEBUG)

# Read the Excel file
import random
import sys
import tkinter as tk
from tkinter import messagebox

excel_file = EXCEL_FILE_TEST if DEBUG else EXCEL_FILE_PROD
try:
    df = pd.read_excel(excel_file)
    if "Mega Structure" not in df.columns and "Mega City" in df.columns:
        df = df.rename(columns={"Mega City": "Mega Structure"})
    if df.empty:
        logging.error("Error: Excel file is empty. Please ensure the file contains data.")
        # Show a message box to the user
        root = tk.Tk()
        root.withdraw()
        randint = random.randint(1, 2)
        if randint == 1:
            messagebox.showerror("Export Error", "Have you even shot at anything? No missions found in the log.")
        else:
            messagebox.showerror(
                "Export Error", "No mission data recorded. Please log at least one mission before exporting."
            )
        raise ValueError("Excel file is empty.")
except (FileNotFoundError, ValueError) as e:
    logging.error(f"Error: Unable to read Excel file. {e}")
    sys.exit(0)  # Exit the subprocess gracefully and return to main

# Initialize a dictionary to store column totals
sectors = []
planets = []
enemy_types = []
MissionCategory = []
difficulties = []

# Get total number of rows
total_rows = len(df)
max_rating = total_rows * 5
# Initialize counter for rating
total_rating = 0
# Create rating mapping
rating_mapping = {
    "Gallantry Beyond Measure": 5,
    "Outstanding Patriotism": 5,
    "Truly Exceptional Heroism": 4,
    "Superior Valour": 4,
    "Costly Failure": 4,
    "Honourable Duty": 3,
    "Unremarkable Performance": 2,
    "Dissapointing Service": 1,
    "Disgraceful Conduct": 0,
}
# Calculate total rating
rating_series = df["Rating"] if "Rating" in df.columns else pd.Series([], dtype=object)
total_rating = rating_series.map(rating_mapping).fillna(0).sum() if not rating_series.empty else 0
Rating_Percentage = (total_rating / max_rating) * 100 if max_rating else 0

# Get the user's name and level from the last row of the DataFrame
helldiver_ses = df["Super Destroyer"].iloc[-1] if "Super Destroyer" in df.columns else "Unknown"
helldiver_name = df["Helldivers"].iloc[-1] if "Helldivers" in df.columns else "Unknown"
helldiver_level = df["Level"].iloc[-1] if "Level" in df.columns else 0
helldiver_title = df["Title"].iloc[-1] if "Title" in df.columns else "Unknown"

dcord_file = app_path("JSON", "DCord-dev.json") if DEBUG else app_path("JSON", "DCord.json")
try:
    with open(dcord_file, "r") as f:
        discord_data = json.load(f)
        webhook_urls = discord_data.get("discord_webhooks", [])
except (FileNotFoundError, json.JSONDecodeError):
    with open(app_path("JSON", "DCord.json"), "r") as f:
        discord_data = json.load(f)
        webhook_urls = discord_data.get("discord_webhooks", [])

webhook_urls = [
    (w.get("url") if isinstance(w, dict) else str(w)).strip()
    for w in webhook_urls
    if (isinstance(w, dict) and str(w.get("url", "")).strip()) or (isinstance(w, str) and w.strip())
]

if Rating_Percentage >= 90:
    Rating = "Outstanding Patriotism"
elif Rating_Percentage >= 70:
    Rating = "Superior Valour"
elif Rating_Percentage >= 50:
    Rating = "Honourable Duty"
elif Rating_Percentage >= 30:
    Rating = "Unremarkable Performance"
elif Rating_Percentage >= 10:
    Rating = "Dissapointing Service"
else:
    Rating = "Disgraceful Conduct"


# Returns last deployment timestamp for an enemy; affects faction embed stats
def get_last_deployment(df: pd.DataFrame, enemy_type: str) -> str:
    if "Time" not in df.columns or "Enemy Type" not in df.columns:
        return "No date available"

    # Filter rows for the enemy type
    subset = df[df["Enemy Type"] == enemy_type]
    if subset.empty:
        return "No deployments"

    # Clean and parse time strings
    times_raw = subset["Time"].astype(str).str.strip()

    # Normalize any '/' to '-' just in case
    times_normalized = times_raw.str.replace("/", "-", regex=False)

    # First try strict expected format
    times_parsed = pd.to_datetime(times_normalized, format="%d-%m-%Y %H:%M:%S", errors="coerce")

    # Fallback: attempt a more permissive parse (dayfirst=True)
    if times_parsed.isna().all():
        times_parsed = pd.to_datetime(times_normalized, errors="coerce", dayfirst=True)

    # Drop NaT values
    valid_mask = ~times_parsed.isna()
    if not valid_mask.any():
        return "No valid dates"

    valid_times = times_parsed[valid_mask]

    # Find the timestamp closest to "now"
    now = pd.Timestamp.now()
    deltas = (valid_times - now).abs()
    closest_idx = deltas.idxmin()
    closest_ts = valid_times.loc[closest_idx]

    return closest_ts.strftime("%d-%m-%Y %H:%M:%S")


# Returns first deployment timestamp for an enemy; affects faction embed stats
def get_first_deployment(df: pd.DataFrame, enemy_type: str) -> str:
    if "Time" not in df.columns or "Enemy Type" not in df.columns:
        return "No date available"

    # Filter rows for the enemy type
    subset = df[df["Enemy Type"] == enemy_type]
    if subset.empty:
        return "No deployments"

    # Clean and parse time strings
    times_raw = subset["Time"].astype(str).str.strip()

    # Normalize any '/' to '-' just in case
    times_normalized = times_raw.str.replace("/", "-", regex=False)

    # First try strict expected format
    times_parsed = pd.to_datetime(times_normalized, format="%d-%m-%Y %H:%M:%S", errors="coerce")

    # Fallback: attempt a more permissive parse (dayfirst=True)
    if times_parsed.isna().all():
        times_parsed = pd.to_datetime(times_normalized, errors="coerce", dayfirst=True)

    # Drop NaT values
    valid_mask = ~times_parsed.isna()
    if not valid_mask.any():
        return "No valid dates"

    valid_times = times_parsed[valid_mask]

    # Get the earliest timestamp
    first_ts = valid_times.min()
    return first_ts.strftime("%d-%m-%Y %H:%M:%S")


if "Sector" in df.columns:
    sectors = df["Sector"].dropna().unique().tolist()
if "Planet" in df.columns:
    planets = df["Planet"].dropna().unique().tolist()
if "Enemy Type" in df.columns:
    enemy_types = df["Enemy Type"].dropna().unique().tolist()
if "Mission Category" in df.columns:
    MissionCategory = df["Mission Category"].dropna().unique().tolist()
if "Difficulty" in df.columns:
    difficulties = df["Difficulty"].dropna().unique().tolist()

planet_stats_df = pd.DataFrame()
if "Planet" in df.columns:
    planet_stats_df = (
        df.groupby("Planet", dropna=False)
        .agg(
            **{
                "Total Kills": ("Kills", "sum"),
                "Total Deaths": ("Deaths", "sum"),
                "Major Orders": ("Major Order", lambda s: s.astype(int).sum()),
                "Last Date": ("Time", "max"),
            }
        )
        .reset_index()
    )

# Discord webhook configuration
dcord_file = app_path("JSON", "DCord-dev.json") if DEBUG else app_path("JSON", "DCord.json")
try:
    with open(dcord_file, "r") as f:
        dcord_data = json.load(f)
        ACTIVE_WEBHOOK = dcord_data.get("discord_webhooks", [])
except (FileNotFoundError, json.JSONDecodeError):
    with open(app_path("JSON", "DCord.json"), "r") as f:
        dcord_data = json.load(f)
        ACTIVE_WEBHOOK = dcord_data.get("discord_webhooks", [])

ACTIVE_WEBHOOK = [
    (w.get("url") if isinstance(w, dict) else str(w)).strip()
    for w in ACTIVE_WEBHOOK
    if (isinstance(w, dict) and str(w.get("url", "")).strip()) or (isinstance(w, str) and w.strip())
]

# Get latest note
non_blank_notes = df["Note"].dropna()
latest_note = non_blank_notes.iloc[-1] if not non_blank_notes.empty else "No Quote"

enemy_type_series = df["Enemy Type"] if "Enemy Type" in df.columns else pd.Series([], dtype=object)
enemy_type_key = enemy_type_series.fillna("Unknown")
mission_category_series = df["Mission Category"] if "Mission Category" in df.columns else pd.Series([], dtype=object)
mission_category_key = mission_category_series.fillna("Unknown")
kills_series = df["Kills"] if "Kills" in df.columns else pd.Series([], dtype=float)
deaths_series = df["Deaths"] if "Deaths" in df.columns else pd.Series([], dtype=float)
major_order_series = df["Major Order"].astype(int) if "Major Order" in df.columns else pd.Series([], dtype=int)
dss_series = df["DSS Active"].astype(int) if "DSS Active" in df.columns else pd.Series([], dtype=int)

enemy_group = df.groupby(enemy_type_key, dropna=False) if not enemy_type_key.empty else None
enemy_kills = enemy_group["Kills"].sum() if enemy_group is not None else pd.Series(dtype=float)
enemy_deaths = enemy_group["Deaths"].sum() if enemy_group is not None else pd.Series(dtype=float)
enemy_max_kills = enemy_group["Kills"].max() if enemy_group is not None else pd.Series(dtype=float)
enemy_deployments = enemy_group.size() if enemy_group is not None else pd.Series(dtype=int)
enemy_major_orders = major_order_series.groupby(enemy_type_key).sum() if not enemy_type_key.empty else pd.Series(dtype=int)
enemy_dss = dss_series.groupby(enemy_type_key).sum() if not enemy_type_key.empty else pd.Series(dtype=int)
mission_counts_by_enemy = (
    df.groupby([enemy_type_key, mission_category_key]).size() if not enemy_type_key.empty else pd.Series(dtype=int)
)

# Get value counts for each category
mission_counts = df["Mission Type"].value_counts()
campaign_counts = df["Mission Category"].value_counts()
faction_counts = df["Enemy Type"].value_counts()
subfaction_counts = df["Enemy Subfaction"].value_counts()
difficulty_counts = df["Difficulty"].value_counts()
planet_counts = df["Planet"].value_counts()
sector_counts = df["Sector"].value_counts()

search_mission = mission_counts.index[0] if not mission_counts.empty else "Unknown"
MissionCount = int(mission_counts.iloc[0]) if not mission_counts.empty else 0
search_campaign = campaign_counts.index[0] if not campaign_counts.empty else "Unknown"
CampaignCount = int(campaign_counts.iloc[0]) if not campaign_counts.empty else 0
search_faction = faction_counts.index[0] if not faction_counts.empty else "Unknown"
FactionCount = int(faction_counts.iloc[0]) if not faction_counts.empty else 0
search_subfaction = subfaction_counts.index[0] if not subfaction_counts.empty else "Unknown"
SubfactionCount = int(subfaction_counts.iloc[0]) if not subfaction_counts.empty else 0
search_difficulty = difficulty_counts.index[0] if not difficulty_counts.empty else "Unknown"
DifficultyCount = int(difficulty_counts.iloc[0]) if not difficulty_counts.empty else 0
search_planet = planet_counts.index[0] if not planet_counts.empty else "Unknown"
PlanetCount = int(planet_counts.iloc[0]) if not planet_counts.empty else 0
search_sector = sector_counts.index[0] if not sector_counts.empty else "Unknown"
SectorCount = int(sector_counts.iloc[0]) if not sector_counts.empty else 0

# Get badge icons using centralized function
badge_data = get_badge_icons(DEBUG, APP_DATA, DATE_FORMAT)

# Build badge string: always-on first, then up to 4 user-selected badges
always_on_order = ["bicon", "ticon", "yearico", "PIco"]
selectable_order = ["bsuperearth", "bcyberstan", "bmaleveloncreek", "bcalypso", "bpopliix", "bseyshelbeach", "boshaune"]

# Load user's badge display preference from DCord.json if present
try:
    display_pref = dcord_data.get("display_badges", None) if "dcord_data" in locals() else None
except Exception:
    display_pref = None

badge_items = []
# Add always-on badges
for k in always_on_order:
    if badge_data.get(k):
        badge_items.append(badge_data.get(k))

# Add user-selected badges (up to 4)
selected_count = 0
if isinstance(display_pref, list) and display_pref:
    for k in display_pref:
        if k in badge_data and badge_data.get(k):
            badge_items.append(badge_data.get(k))
            selected_count += 1
        if selected_count >= 4:
            break

# Combined badge string used in embeds
badge_string = "".join(badge_items)

# Create named references for backwards-compatibility in other code
bicon = badge_data.get("bicon", "")
ticon = badge_data.get("ticon", "")
PIco = badge_data.get("PIco", "")
yearico = badge_data.get("yearico", "")
bsuperearth = badge_data.get("bsuperearth", "")
bcyberstan = badge_data.get("bcyberstan", "")
bmaleveloncreek = badge_data.get("bmaleveloncreek", "")
bcalypso = badge_data.get("bcalypso", "")
bpopliix = badge_data.get("bpopliix", "")
bseyshelbeach = badge_data.get("bseyshelbeach", "")
boshaune = badge_data.get("boshaune", "")

highest_streak = 0
profile_picture = ""
with open(app_path("JSON", "streak_data.json"), "r") as f:
    streak_data = json.load(f)
    # Use "Helldiver" as the key or fall back to helldiver_ses if the first one doesn't exist
    highest_streak = streak_data.get("Helldiver", streak_data.get(helldiver_ses, {})).get("highest_streak", 0)
    profile_picture = streak_data.get("Helldiver", streak_data.get(helldiver_ses, {})).get("profile_picture_name", "")

# Load DCord.json data
with open(app_path("JSON", "DCord.json"), "r") as f:
    dcord_data = json.load(f)

# Calculate Mega Structure deployments excluding "Planet Surface" and empty values
mega_city_count = df[
    df["Mega Structure"].fillna("").astype(str).apply(lambda x: x != "" and x.lower() != "planet surface")
].shape[0]

terminids_mega_city_count = df[
    (df["Enemy Type"] == "Terminids")
    & (df["Mega Structure"].fillna("").astype(str).apply(lambda x: x != "" and x.lower() != "planet surface"))
].shape[0]
automatons_mega_city_count = df[
    (df["Enemy Type"] == "Automatons")
    & (df["Mega Structure"].fillna("").astype(str).apply(lambda x: x != "" and x.lower() != "planet surface"))
].shape[0]
illuminate_mega_city_count = df[
    (df["Enemy Type"] == "Illuminate")
    & (df["Mega Structure"].fillna("").astype(str).apply(lambda x: x != "" and x.lower() != "planet surface"))
].shape[0]

from core.utils import get_effective_flair

flair_colour = get_effective_flair()
if flair_colour.lower() == "gold":
    FlairLeftIco = iconconfig["MiscIcon"].get("Gold Flair Left", iconconfig["MiscIcon"]["Flair Left"])
    FlairRightIco = iconconfig["MiscIcon"].get("Gold Flair Right", iconconfig["MiscIcon"]["Flair Right"])
elif flair_colour.lower() == "blue":
    FlairLeftIco = iconconfig["MiscIcon"].get("Blue Flair Left", iconconfig["MiscIcon"]["Flair Left"])
    FlairRightIco = iconconfig["MiscIcon"].get("Blue Flair Right", iconconfig["MiscIcon"]["Flair Right"])
elif flair_colour.lower() == "red":
    FlairLeftIco = iconconfig["MiscIcon"].get("Red Flair Left", iconconfig["MiscIcon"]["Flair Left"])
    FlairRightIco = iconconfig["MiscIcon"].get("Red Flair Right", iconconfig["MiscIcon"]["Flair Right"])
else:
    FlairLeftIco = iconconfig["MiscIcon"].get(f"Flair Left {flair_colour}", iconconfig["MiscIcon"]["Flair Left"])
    FlairRightIco = iconconfig["MiscIcon"].get(f"Flair Right {flair_colour}", iconconfig["MiscIcon"]["Flair Right"])
GoldStarIco = iconconfig["Stars"]["GoldStar"]
FlairSkullIco = iconconfig["MiscIcon"]["Flair Skull"]
FlairSEIco = iconconfig["MiscIcon"]["Flair Super Earth"]
FlairGSSkullIco = iconconfig["MiscIcon"]["Flair Gold Spinning Skull"]
BugIco = iconconfig["EnemyIcons"]["Terminids"]
BotIco = iconconfig["EnemyIcons"]["Automatons"]
SquidIco = iconconfig["EnemyIcons"]["Illuminate"]
KillIco = iconconfig["MiscIcon"]["Kills"]
DeathIco = iconconfig["MiscIcon"]["Deaths"]
KDRIco = iconconfig["MiscIcon"]["KDR"]
HighestKillIco = iconconfig["MiscIcon"]["Highest Kills"]
DeployIco = iconconfig["MiscIcon"]["Deployments"]
MODeployIco = iconconfig["MiscIcon"]["Major Order Deployments"]
DSSDeployIco = iconconfig["MiscIcon"]["DSS Deployments"]
BugMCDeployIco = iconconfig["MiscIcon"]["Bug Mega City Deployments"]
BotMCDeployIco = iconconfig["MiscIcon"]["Bot Mega City Deployments"]
SquidMCDeployIco = iconconfig["MiscIcon"]["Squid Mega City Deployments"]
LastDeployIco = iconconfig["MiscIcon"]["Last Deployment"]
LiberationIco = iconconfig["CampaignIcons"]["Liberation"]
DefenceIco = iconconfig["CampaignIcons"]["Defense"]
InvasionIco = iconconfig["CampaignIcons"]["Invasion"]
HighPriorityIco = iconconfig["CampaignIcons"]["High-Priority"]
AttritionIco = iconconfig["CampaignIcons"]["Attrition"]
ReconIco = iconconfig["CampaignIcons"]["Recon"]


def _safe_div(numer, denom):
    return (numer / denom) if denom else 0


def _fmt_number(value):
    # Format numeric stats without trailing .0 while keeping real decimals.
    try:
        if pd.isna(value):
            return "0"
    except Exception:
        pass
    try:
        as_float = float(value)
    except Exception:
        return str(value)
    if as_float.is_integer():
        return str(int(as_float))
    return f"{as_float:.2f}".rstrip("0").rstrip(".")


def _enemy_stat(series, enemy, default=0):
    return series.get(enemy, default) if series is not None else default


terminid_kills = float(_enemy_stat(enemy_kills, "Terminids", 0))
terminid_deaths = float(_enemy_stat(enemy_deaths, "Terminids", 0))
terminid_kdr = _safe_div(terminid_kills, terminid_deaths)
terminid_max_kills = float(_enemy_stat(enemy_max_kills, "Terminids", 0))
terminid_deployments = int(_enemy_stat(enemy_deployments, "Terminids", 0))
terminid_major_orders = int(_enemy_stat(enemy_major_orders, "Terminids", 0))
terminid_dss = int(_enemy_stat(enemy_dss, "Terminids", 0))

automaton_kills = float(_enemy_stat(enemy_kills, "Automatons", 0))
automaton_deaths = float(_enemy_stat(enemy_deaths, "Automatons", 0))
automaton_kdr = _safe_div(automaton_kills, automaton_deaths)
automaton_max_kills = float(_enemy_stat(enemy_max_kills, "Automatons", 0))
automaton_deployments = int(_enemy_stat(enemy_deployments, "Automatons", 0))
automaton_major_orders = int(_enemy_stat(enemy_major_orders, "Automatons", 0))
automaton_dss = int(_enemy_stat(enemy_dss, "Automatons", 0))

illuminate_kills = float(_enemy_stat(enemy_kills, "Illuminate", 0))
illuminate_deaths = float(_enemy_stat(enemy_deaths, "Illuminate", 0))
illuminate_kdr = _safe_div(illuminate_kills, illuminate_deaths)
illuminate_max_kills = float(_enemy_stat(enemy_max_kills, "Illuminate", 0))
illuminate_deployments = int(_enemy_stat(enemy_deployments, "Illuminate", 0))
illuminate_major_orders = int(_enemy_stat(enemy_major_orders, "Illuminate", 0))
illuminate_dss = int(_enemy_stat(enemy_dss, "Illuminate", 0))


def _enemy_campaign(enemy, category):
    return int(mission_counts_by_enemy.get((enemy, category), 0))


def _campaign_line(enemy, category, label, icon, hide_zero=False):
    count = _enemy_campaign(enemy, category)
    if hide_zero and count < 1:
        return ""
    return f"> {icon} {label} - {count}\n"


terminid_campaign_lines = (
    _campaign_line("Terminids", "Liberation", "Liberations", LiberationIco)
    + _campaign_line("Terminids", "Defense", "Defenses", DefenceIco)
    + _campaign_line("Terminids", "Invasion", "Invasion", InvasionIco, hide_zero=True)
    + _campaign_line("Terminids", "High-Priority", "High-Priority", HighPriorityIco)
    + _campaign_line("Terminids", "Attrition", "Attrition", AttritionIco, hide_zero=True)
    + _campaign_line("Terminids", "Battle for Super Earth", "Battle for Super Earth", InvasionIco, hide_zero=True)
    + _campaign_line("Terminids", "Recon", "Recon", ReconIco)
    + _campaign_line("Terminids", "Battle for Cyberstan", "Battle for Cyberstan", LiberationIco, hide_zero=True)
)

automaton_campaign_lines = (
    _campaign_line("Automatons", "Liberation", "Liberations", LiberationIco)
    + _campaign_line("Automatons", "Defense", "Defenses", DefenceIco)
    + _campaign_line("Automatons", "Invasion", "Invasion", InvasionIco, hide_zero=True)
    + _campaign_line("Automatons", "High-Priority", "High-Priority", HighPriorityIco)
    + _campaign_line("Automatons", "Attrition", "Attrition", AttritionIco, hide_zero=True)
    + _campaign_line("Automatons", "Battle for Super Earth", "Battle for Super Earth", InvasionIco, hide_zero=True)
    + _campaign_line("Automatons", "Recon", "Recon", ReconIco)
    + _campaign_line("Automatons", "Battle for Cyberstan", "Battle for Cyberstan", LiberationIco)
)

illuminate_campaign_lines = (
    _campaign_line("Illuminate", "Liberation", "Liberations", LiberationIco)
    + _campaign_line("Illuminate", "Defense", "Defenses", DefenceIco)
    + _campaign_line("Illuminate", "Invasion", "Invasion", InvasionIco)
    + _campaign_line("Illuminate", "High-Priority", "High-Priority", HighPriorityIco)
    + _campaign_line("Illuminate", "Attrition", "Attrition", AttritionIco)
    + _campaign_line("Illuminate", "Battle for Super Earth", "Battle for Super Earth", InvasionIco)
    + _campaign_line("Illuminate", "Recon", "Recon", ReconIco)
    + _campaign_line("Illuminate", "Battle for Cyberstan", "Battle for Cyberstan", LiberationIco, hide_zero=True)
)

# Create embed data
embed_data = {
    "content": None,
    "embeds": [
        {
            "title": "",  # Empty title, will be set below
            "description": f'**Level {helldiver_level} | {helldiver_title} {TITLE_ICONS.get(df["Title"].iloc[-1], "")}**\n\n"{latest_note}"\n\n{FlairLeftIco}  {FlairSkullIco} Combat Statistics {FlairSkullIco} {FlairRightIco}\n'
            + f"> Kills - {_fmt_number(kills_series.sum())}\n"
            + f"> Deaths - {_fmt_number(deaths_series.sum())}\n"
            + f"> KDR - {_safe_div(kills_series.sum(), deaths_series.sum()):.2f}\n"
            + f"> Highest Kills in Mission - {_fmt_number(kills_series.max())}\n"
            + f"\n{FlairLeftIco}  {FlairSEIco} Mission Statistics {FlairSEIco} {FlairRightIco}\n"
            + f"> Deployments - {len(df)}\n"
            + f"> Major Order Deployments - {major_order_series.sum()}\n"
            + f"> DSS Deployments - {dss_series.sum()}\n"
            + f"> Mega Structure Deployments - {mega_city_count}\n"
            + f"> First Deployment - {get_first_deployment(df, enemy_type_key.mode().iloc[0] if not enemy_type_key.empty else 'Unknown')}\n"
            + f"\n{FlairLeftIco}  {FlairGSSkullIco} Performance Statistics {FlairGSSkullIco} {FlairRightIco}\n"
            + f"> Rating - {Rating} | {int(Rating_Percentage)}%\n"
            + f"> Highest Streak - {highest_streak} Missions\n"
            + f"\n{FlairLeftIco}  {GoldStarIco} Favourites {GoldStarIco} {FlairRightIco}\n"
            + f"> Mission - {search_mission} {MISSION_ICONS.get(search_mission, '')} (x{MissionCount})\n"
            + f"> Campaign - {search_campaign} {CAMPAIGN_ICONS.get(search_campaign, '')} (x{CampaignCount})\n"
            + f"> Faction - {search_faction} {ENEMY_ICONS.get(search_faction, '')} (x{FactionCount})\n"
            + f"> Subfaction - {search_subfaction} {SUBFACTION_ICONS.get(search_subfaction, '')} (x{SubfactionCount})\n"
            f"> Difficulty - {search_difficulty} {DIFFICULTY_ICONS.get(search_difficulty, '')} (x{DifficultyCount})\n"
            + f"> Planet - {search_planet} {PLANET_ICONS.get(search_planet, '')} (x{PlanetCount})\n"
            + f"> Sector - {search_sector} (x{SectorCount})\n",
            "color": 7257043,
            "author": {
                "name": f"SEAF Faction Record\nDate: {date}",
                "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356001307596427564/NwNzS9B.png?ex=67eafa21&is=67e9a8a1&hm=7e204265cbcdeaf96d7b244cd63992c4ef10dc18befbcf2ed39c3a269af14ec0&",
            },
            "footer": {
                "text": f"{discord_data['discord_uid']}   v{VERSION}{DEV_RELEASE}",
                "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356025859319926784/5cwgI15.png?ex=67eb10fe&is=67e9bf7e&hm=ab6326a9da1e76125238bf3668acac8ad1e43b24947fc6d878d7b94c8a60ab28&",
            },
            "image": {"url": f"{BIOME_BANNERS.get(search_planet, '')}"},
            "thumbnail": {"url": f"{profile_picture}"},
        },
        {
            "title": "Terminids Campaign Record",
            "description": f"{FlairLeftIco} {BugIco} Terminid Front Statistics {BugIco} {FlairRightIco}\n"
            + f"> {KillIco} Kills - {_fmt_number(terminid_kills)}\n"
            + f"> {DeathIco} Deaths - {_fmt_number(terminid_deaths)}\n"
            + f"> {KDRIco} KDR - {terminid_kdr:.2f}\n"
            + f"> {HighestKillIco} Highest Kills in Mission - {_fmt_number(terminid_max_kills)}\n\n"
            + f"> {DeployIco} Deployments - {terminid_deployments}\n"
            + f"> {MODeployIco} Major Order Deployments - {terminid_major_orders}\n"
            + f"> {DSSDeployIco} DSS Deployments - {terminid_dss}\n"
            + f"> {BugMCDeployIco} Mega Structure Deployments - {terminids_mega_city_count}\n"
            + f"> {LastDeployIco} Last Deployment - {get_last_deployment(df, 'Terminids')}\n\n"
            + f"{terminid_campaign_lines}\n",
            "color": 16761088,
            "image": {
                "url": "https://cdn.discordapp.com/attachments/1340508329977446484/1370786767128760420/terminidBanner.png?ex=6820c429&is=681f72a9&hm=3ca1e122e8063426a3dd1963791aca33ba6343a7a946b06287d344ce6c0f93a0&"
            },
            "thumbnail": {"url": "https://i.ibb.co/PspGgJkH/Terminids-Icon.png"},
        },
        {
            "title": "Automaton Campaign Record",
            "description": f"{FlairLeftIco} {BotIco} Automaton Front Statistics {BotIco} {FlairRightIco}\n"
            + f"> {KillIco} Kills - {_fmt_number(automaton_kills)}\n"
            + f"> {DeathIco} Deaths - {_fmt_number(automaton_deaths)}\n"
            + f"> {KDRIco} KDR - {automaton_kdr:.2f}\n"
            + f"> {HighestKillIco} Highest Kills in Mission - {_fmt_number(automaton_max_kills)}\n\n"
            + f"> {DeployIco} Deployments - {automaton_deployments}\n"
            + f"> {MODeployIco} Major Order Deployments - {automaton_major_orders}\n"
            + f"> {DSSDeployIco} DSS Deployments - {automaton_dss}\n"
            + f"> {BotMCDeployIco} Mega Structure Deployments - {automatons_mega_city_count}\n"
            + f"> {LastDeployIco} Last Deployment - {get_last_deployment(df, 'Automatons')}\n\n"
            + f"{automaton_campaign_lines}\n",
            "color": 16739693,
            "image": {
                "url": "https://cdn.discordapp.com/attachments/1340508329977446484/1370786778465964193/automatonBanner.png?ex=6820c42b&is=681f72ab&hm=63213a37d29cfc25661737c7d20867ebea272fffc9e830116c32ef7df3cf1a24&"
            },
            "thumbnail": {"url": "https://i.ibb.co/bgNp2q73/Automatons-Icon.png"},
        },
        {
            "title": "Illuminate Campaign Record",
            "description": f"{FlairLeftIco} {SquidIco} Illuminate Cult Statistics {SquidIco} {FlairRightIco}\n"
            + f"> {KillIco} Kills - {_fmt_number(illuminate_kills)}\n"
            + f"> {DeathIco} Deaths - {_fmt_number(illuminate_deaths)}\n"
            + f"> {KDRIco} KDR - {illuminate_kdr:.2f}\n"
            + f"> {HighestKillIco} Highest Kills in Mission - {_fmt_number(illuminate_max_kills)}\n\n"
            + f"> {DeployIco} Deployments - {illuminate_deployments}\n"
            + f"> {MODeployIco} Major Order Deployments - {illuminate_major_orders}\n"
            + f"> {DSSDeployIco} DSS Deployments - {illuminate_dss}\n"
            + f"> {SquidMCDeployIco} Mega Structure Deployments - {illuminate_mega_city_count}\n"
            + f"> {LastDeployIco} Last Deployment - {get_last_deployment(df, 'Illuminate')}\n\n"
            + f"{illuminate_campaign_lines}\n",
            "color": 9003210,
            "image": {
                "url": "https://cdn.discordapp.com/attachments/1340508329977446484/1370786787441774632/illuminateBanner.png?ex=6820c42e&is=681f72ae&hm=bc4d9e9f89bcae58521b9af1558816ecb0c336bee108862725663b87e5bb6079&"
            },
            "thumbnail": {"url": "https://i.ibb.co/wr4Nm5HT/Illuminate-Icon.png"},
        },
    ],
    "attachments": [],
}

# Update the embed title with name and level
embed_data["embeds"][0]["title"] = f"{helldiver_ses}\nHelldiver: {helldiver_name}\n{badge_string}"

# Enemy type specific embeds with icons
enemy_icons = {
    "Automatons": {
        "emoji": iconconfig["EnemyIcons"]["Automatons"],
        "color": int(iconconfig["SystemColors"]["Automatons"]),
        "url": "https://i.ibb.co/bgNp2q73/Automatons-Icon.png",
    },
    "Terminids": {
        "emoji": iconconfig["EnemyIcons"]["Terminids"],
        "color": int(iconconfig["SystemColors"]["Terminids"]),
        "url": "https://i.ibb.co/PspGgJkH/Terminids-Icon.png",
    },
    "Illuminate": {
        "emoji": iconconfig["EnemyIcons"]["Illuminate"],
        "color": int(iconconfig["SystemColors"]["Illuminate"]),
        "url": "https://i.ibb.co/wr4Nm5HT/Illuminate-Icon.png",
    },
}

enemy_banners = {
    "Automatons": {
        "url": "https://cdn.discordapp.com/attachments/1340508329977446484/1370786778465964193/automatonBanner.png?ex=6820c42b&is=681f72ab&hm=63213a37d29cfc25661737c7d20867ebea272fffc9e830116c32ef7df3cf1a24&"
    },
    "Terminids": {
        "url": "https://cdn.discordapp.com/attachments/1340508329977446484/1370786767128760420/terminidBanner.png?ex=6820c429&is=681f72a9&hm=3ca1e122e8063426a3dd1963791aca33ba6343a7a946b06287d344ce6c0f93a0&"
    },
    "Illuminate": {
        "url": "https://cdn.discordapp.com/attachments/1340508329977446484/1370786787441774632/illuminateBanner.png?ex=6820c42e&is=681f72ae&hm=bc4d9e9f89bcae58521b9af1558816ecb0c336bee108862725663b87e5bb6079&"
    },
}

# Group data by enemy type (faction)
faction_stats = {}
for enemy_type in enemy_types:
    faction_data = df[df["Enemy Type"] == enemy_type]
    if not faction_data.empty:
        faction_stats[enemy_type] = {
            "total_kills": faction_data["Kills"].sum(),
            "total_deaths": faction_data["Deaths"].sum(),
            "total_deployments": len(faction_data),
            "major_orders": faction_data["Major Order"].astype(int).sum(),
            "last_deployment": faction_data["Time"].max() if "Time" in df.columns else "No date available",
            "planets": faction_data["Planet"].unique().tolist(),
        }

dcord_file = app_path("JSON", "DCord-dev.json") if DEBUG else app_path("JSON", "DCord.json")
try:
    with open(dcord_file, "r") as f:
        discord_data = json.load(f)
        webhook_urls = discord_data.get("discord_webhooks_export", [])
except (FileNotFoundError, json.JSONDecodeError):
    with open(app_path("JSON", "DCord.json"), "r") as f:
        discord_data = json.load(f)
        webhook_urls = discord_data.get("discord_webhooks_export", [])

webhook_urls = [
    (w.get("url") if isinstance(w, dict) else str(w)).strip()
    for w in webhook_urls
    if (isinstance(w, dict) and str(w.get("url", "")).strip()) or (isinstance(w, str) and w.strip())
]

# Send data to each webhook
for webhook_url in webhook_urls:
    try:
        payload = json.loads(json.dumps(embed_data))
        if payload.get("content") is None:
            payload.pop("content", None)

        # Sanitize embeds to avoid Discord validation errors
        if "embeds" in payload and isinstance(payload["embeds"], list):
            for i, embed in enumerate(payload["embeds"]):
                if embed:  # Only sanitize if embed exists
                    sanitized, changes = _sanitize_embed(embed)
                    payload["embeds"][i] = sanitized
                    if changes:
                        logging.info(f"Sanitized embed {i} before sending: {changes}")

        # If all embeds are now empty after sanitization, skip sending
        if not any(payload.get("embeds", [])):
            logging.error(f"Skipping webhook send to {webhook_url}: all embeds empty after sanitization.")
            continue

        success, response, err = post_webhook(webhook_url, json_payload=payload, timeout=20, retries=2)
        if success:
            logging.info(
                f"Data sent successfully to {webhook_url} (status {response.status_code if response else 'unknown'})."
            )
        else:
            logging.error(f"Failed to send data to {webhook_url}. {err}")
    except Exception as e:
        logging.error(f"Exception sending webhook to {webhook_url}: {e}")
