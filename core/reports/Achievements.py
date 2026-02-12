import configparser
import json
import logging
import os
import time
from copy import deepcopy
from datetime import datetime

import pandas as pd
import requests

from core.app_core import DEV_RELEASE, VERSION
from core.integrations.discord_integration import _sanitize_embed
from core.icon import TITLE_ICONS, get_badge_icons
from core.infrastructure.logging_config import setup_logging
from core.infrastructure.runtime_paths import app_path
from core.integrations.webhook import post_webhook

# Read configuration from config.config
config = configparser.ConfigParser()
config.read(app_path("orphan", "config.config"))
iconconfig = configparser.ConfigParser()
iconconfig.read(app_path("orphan", "icon.config"))

date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

# Constants
DEBUG = config.getboolean("DEBUGGING", "DEBUG", fallback=False)
setup_logging(DEBUG)

# Set up application data paths
APP_DATA = os.path.join(os.getenv("LOCALAPPDATA"), "MLHD2")
if not os.path.exists(APP_DATA):
    os.makedirs(APP_DATA)

EXCEL_FILE_PROD = os.path.join(APP_DATA, "mission_log.xlsx")
EXCEL_FILE_TEST = os.path.join(APP_DATA, "mission_log_test.xlsx")
DATE_FORMAT = "%d-%m-%Y %H:%M:%S"

# Read the Excel file
import random
import sys
import tkinter as tk
from tkinter import messagebox

try:
    excel_file = EXCEL_FILE_TEST if DEBUG else EXCEL_FILE_PROD
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
            messagebox.showerror("Export Error", "You've achived nothing! No missions found in the log.")
        else:
            messagebox.showerror(
                "Export Error", "No mission data recorded. Please log at least one mission before exporting."
            )
        raise ValueError("Excel file is empty.")
except (FileNotFoundError, ValueError) as e:
    logging.error(f"Error: Unable to read Excel file. {e}")
    sys.exit(0)  # Exit the subprocess gracefully and return to main


highest_streak = 0
profile_picture = ""
with open(app_path("JSON", "streak_data.json"), "r") as f:
    streak_data = json.load(f)
    # Use "Helldiver" as the key
    highest_streak = streak_data.get("Helldiver", {}).get("highest_streak", 0)
    profile_picture = streak_data.get("Helldiver", {}).get("profile_picture_name", "")

# Aggregate data for each advancement query
# Cached series/masks to avoid repeated dataframe scans
major_order_mask = df["Major Order"].eq(1)
dss_active_mask = df["DSS Active"].eq(1)
mega_structure_mask = df["Mega Structure"].eq(1)

enemy_type_series = df["Enemy Type"]
terminids_mask = enemy_type_series.eq("Terminids")
automatons_mask = enemy_type_series.eq("Automatons")
illuminate_mask = enemy_type_series.eq("Illuminate")

planet_series = df["Planet"]
malevelon_creek_mask = planet_series.eq("Malevelon Creek")
super_earth_mask = planet_series.eq("Super Earth")
cyberstan_mask = planet_series.eq("Cyberstan")

rating_series = df["Rating"]
disgraceful_conduct_mask = rating_series.eq("Disgraceful Conduct")
costly_failure_mask = rating_series.eq("Costly Failure")

streak_10_mask = df["Streak"].ge(10)
streak_20_mask = df["Streak"].ge(20)
streak_30_mask = df["Streak"].ge(30)

kills_series = df["Kills"]
total_kills = kills_series.sum()

# get total missions
total_missions = len(df)

# get total mission with major order active
total_missions_major_order = int(major_order_mask.sum())

# get total mission with DSS active
total_missions_dss = int(dss_active_mask.sum())

total_missions_city = int(mega_structure_mask.sum())

# Get count of unique planets visited
total_missions_planets = len(df["Planet"].unique())

total_missions_sectors = len(df["Sector"].unique())

# get total terminid missions
total_terminid_missions = int(terminids_mask.sum())

# get total automaton missions
total_automaton_missions = int(automatons_mask.sum())

# get total illuminate missions
total_illuminate_missions = int(illuminate_mask.sum())

# get total terminid kills
total_terminid_kills = kills_series.loc[terminids_mask].sum()

# get total automaton kills
total_automaton_kills = kills_series.loc[automatons_mask].sum()

# get total illuminate kills
total_illuminate_kills = kills_series.loc[illuminate_mask].sum()

# get if at least one mission was played on Malevelon Creek
malevelon_creek = bool(malevelon_creek_mask.any())

# get if at least on mission was rated Disgracful Conduct
disgraceful_conduct = bool(disgraceful_conduct_mask.any())

costly_failure = bool(costly_failure_mask.any())

# get if at least one mission was played on Super Earth
super_earth = bool(super_earth_mask.any())

# get at least one mission was played on the Cyberstan
cyberstan = bool(cyberstan_mask.any())

# get if highest_streak is 30 or more
streak_10 = highest_streak >= 10
streak_20 = highest_streak >= 20
streak_30 = highest_streak >= 30

# Get count of difficulty types
difficulty_counts = df["Difficulty"].value_counts()
total_1 = difficulty_counts.get("1 - TRIVIAL", 0) > 0
total_2 = difficulty_counts.get("2 - EASY", 0) > 0
total_3 = difficulty_counts.get("3 - MEDIUM", 0) > 0
total_4 = difficulty_counts.get("4 - CHALLENGING", 0) > 0
total_5 = difficulty_counts.get("5 - HARD", 0) > 0
total_6 = difficulty_counts.get("6 - EXTREME", 0) > 0
total_7 = difficulty_counts.get("7 - SUICIDE MISSION", 0) > 0
total_8 = difficulty_counts.get("8 - IMPOSSIBLE", 0) > 0
total_9 = difficulty_counts.get("9 - HELLDIVE", 0) > 0
total_10 = difficulty_counts.get("10 - SUPER HELLDIVE", 0) > 0

# Check if at least one of each difficulty has been completed
all_difficulties = (
    total_1 and total_2 and total_3 and total_4 and total_5 and total_6 and total_7 and total_8 and total_9 and total_10
)

# Check for completion of each campaign type
mission_category_counts = df["Mission Category"].value_counts()
total_liberation = mission_category_counts.get("Liberation", 0) > 0
total_defense = mission_category_counts.get("Defense", 0) > 0
total_invasion = mission_category_counts.get("Invasion", 0) > 0
total_high_priority = mission_category_counts.get("High-Priority", 0) > 0
total_attrition = mission_category_counts.get("Attrition", 0) > 0
total_bfse = mission_category_counts.get("Battle for Super Earth", 0) > 0
total_recon = mission_category_counts.get("Recon", 0) > 0
total_bfc = mission_category_counts.get("Battle for Cyberstan", 0) > 0

# First-occurrence lookup tables used by date computations
first_time_by_difficulty = (
    df.drop_duplicates(subset=["Difficulty"], keep="first").set_index("Difficulty")["Time"].to_dict()
)
first_time_by_campaign = (
    df.drop_duplicates(subset=["Mission Category"], keep="first").set_index("Mission Category")["Time"].to_dict()
)
first_time_by_planet = df.drop_duplicates(subset=["Planet"], keep="first").set_index("Planet")["Time"].to_dict()
first_time_by_rating = df.drop_duplicates(subset=["Rating"], keep="first").set_index("Rating")["Time"].to_dict()

# Check if all campaign types have been completed
all_campaigns = (
    total_liberation
    and total_defense
    and total_invasion
    and total_high_priority
    and total_attrition
    and total_bfse
    and total_recon
    and total_bfc
)

# Load biome mapping from json file
with open(app_path("JSON", "BiomePlanets.json"), "r") as f:
    biome_mapping = json.load(f)

# Create a set of all unique biomes from the mapping
all_biome_types = set(biome_mapping.values())

# Create dictionary to track if each biome has been visited
biome_visited = {biome: False for biome in all_biome_types}

# For each planet visited in the dataframe, mark its biome as visited
for planet in df["Planet"].unique():
    if planet in biome_mapping:
        biome = biome_mapping[planet]
        biome_visited[biome] = True

# Check if all standard biomes have been visited
# Filter out special biomes like "Scorched", "Black Hole", "Super Earth", etc.
standard_biomes = {
    "Desert Dunes",
    "Desert Cliffs",
    "Acidic Badlands",
    "Rocky Canyons",
    "Moon",
    "Volcanic Jungle",
    "Deadlands",
    "Ethereal Jungle",
    "Ionic Jungle",
    "Icy Glaciers",
    "Boneyard",
    "Plains",
    "Tundra",
    "Scorched Moor",
    "Ionic Crimson",
    "Basic Swamp",
    "Haunted Swamp",
}

all_biomes = all(biome_visited[biome] for biome in standard_biomes)

# Get counts for each mission
mission_counts = df["Mission Type"].value_counts()
# Check if any mission has 100 or more completions
one_mission_100 = any(count >= 100 for count in mission_counts)
# Assign bool values to tracking variables

# Get counts for each planet
planet_counts = df["Planet"].value_counts()
# Check if any planet has 100 or more missions
one_planet_100 = any(count >= 100 for count in planet_counts)
# Assign bool values to tracking variables

# Get counts for each sector
sector_counts = df["Sector"].value_counts()
# Check if any sector has 100 or more missions
one_sector_100 = any(count >= 100 for count in sector_counts)
# Assign bool values to tracking variables


# assign bool values to variables
# Function to get date of nth occurrence
def get_nth_date(df, condition, n):
    # Return date of the nth row matching condition; powers achievement dates
    try:
        # Filter dataframe by condition and get the nth row's date
        filtered_df = df.loc[condition]
        if len(filtered_df) >= n:
            return filtered_df.iloc[n - 1]["Time"]
    except (KeyError, TypeError, ValueError):
        return None
    return None


# Get dates for each achievement
CmdFavourite1 = total_missions >= 100
CmdFavourite1_date = get_nth_date(df, pd.Series([True] * len(df)), 100) if CmdFavourite1 else "Not Obtained"

CmdFavourite2 = total_missions >= 250
CmdFavourite2_date = get_nth_date(df, pd.Series([True] * len(df)), 250) if CmdFavourite2 else "Not Obtained"

CmdFavourite3 = total_missions >= 500
CmdFavourite3_date = get_nth_date(df, pd.Series([True] * len(df)), 500) if CmdFavourite3 else "Not Obtained"

ReliableDiver1 = total_missions_major_order >= 100
ReliableDiver1_date = get_nth_date(df, df["Major Order"] == 1, 100) if ReliableDiver1 else "Not Obtained"

ReliableDiver2 = total_missions_major_order >= 250
ReliableDiver2_date = get_nth_date(df, df["Major Order"] == 1, 250) if ReliableDiver2 else "Not Obtained"

ReliableDiver3 = total_missions_major_order >= 500
ReliableDiver3_date = get_nth_date(df, df["Major Order"] == 1, 500) if ReliableDiver3 else "Not Obtained"

DSSDiver1 = total_missions_dss >= 100
DSSDiver1_date = get_nth_date(df, df["DSS Active"] == 1, 100) if DSSDiver1 else "Not Obtained"

DSSDiver2 = total_missions_dss >= 250
DSSDiver2_date = get_nth_date(df, df["DSS Active"] == 1, 250) if DSSDiver2 else "Not Obtained"

DSSDiver3 = total_missions_dss >= 500
DSSDiver3_date = get_nth_date(df, df["DSS Active"] == 1, 500) if DSSDiver3 else "Not Obtained"


# For unique planet visits, need to track cumulative unique counts
def get_unique_planet_milestone_date(df, n):
    # Date when the nth unique planet is visited; used for PlanetDiver milestones
    # Create a running count of unique planets
    unique_planets = []
    dates = []
    for _, row in df.iterrows():
        planet = row["Planet"]
        if planet not in unique_planets:
            unique_planets.append(planet)
            dates.append(row["Time"])
            if len(unique_planets) == n:
                return dates[n - 1]
    return "Not Obtained"


def get_unique_sector_milestone_date(df, n):
    # Date when the nth unique sector is visited; used for SectorDiver milestones
    # Create a running count of unique sectors
    unique_sectors = []
    dates = []
    for _, row in df.iterrows():
        sector = row["Sector"]
        if sector not in unique_sectors:
            unique_sectors.append(sector)
            dates.append(row["Time"])
            if len(unique_sectors) == n:
                return dates[n - 1]
    return "Not Obtained"


PlanetDiver1 = total_missions_planets >= 25
PlanetDiver1_date = get_unique_planet_milestone_date(df, 25) if PlanetDiver1 else "Not Obtained"

PlanetDiver2 = total_missions_planets >= 50
PlanetDiver2_date = get_unique_planet_milestone_date(df, 50) if PlanetDiver2 else "Not Obtained"

PlanetDiver3 = total_missions_planets >= 100
PlanetDiver3_date = get_unique_planet_milestone_date(df, 100) if PlanetDiver3 else "Not Obtained"

SectorDiver1 = total_missions_sectors >= 15
SectorDiver1_date = get_unique_sector_milestone_date(df, 15) if SectorDiver1 else "Not Obtained"

SectorDiver2 = total_missions_sectors >= 30
SectorDiver2_date = get_unique_sector_milestone_date(df, 30) if SectorDiver2 else "Not Obtained"

SectorDiver3 = total_missions_sectors >= 45
SectorDiver3_date = get_unique_sector_milestone_date(df, 45) if SectorDiver3 else "Not Obtained"

# For enemy-specific missions
OutbreakPerfected1 = total_terminid_missions >= 100
OutbreakPerfected1_date = (
    get_nth_date(df, df["Enemy Type"] == "Terminids", 100) if OutbreakPerfected1 else "Not Obtained"
)

OutbreakPerfected2 = total_terminid_missions >= 250
OutbreakPerfected2_date = (
    get_nth_date(df, df["Enemy Type"] == "Terminids", 250) if OutbreakPerfected2 else "Not Obtained"
)

OutbreakPerfected3 = total_terminid_missions >= 500
OutbreakPerfected3_date = (
    get_nth_date(df, df["Enemy Type"] == "Terminids", 500) if OutbreakPerfected3 else "Not Obtained"
)

AutomatonPerfected1 = total_automaton_missions >= 100
AutomatonPerfected1_date = (
    get_nth_date(df, df["Enemy Type"] == "Automatons", 100) if AutomatonPerfected1 else "Not Obtained"
)

AutomatonPerfected2 = total_automaton_missions >= 250
AutomatonPerfected2_date = (
    get_nth_date(df, df["Enemy Type"] == "Automatons", 250) if AutomatonPerfected2 else "Not Obtained"
)

AutomatonPerfected3 = total_automaton_missions >= 500
AutomatonPerfected3_date = (
    get_nth_date(df, df["Enemy Type"] == "Automatons", 500) if AutomatonPerfected3 else "Not Obtained"
)

IlluminatePerfected1 = total_illuminate_missions >= 100
IlluminatePerfected1_date = (
    get_nth_date(df, df["Enemy Type"] == "Illuminate", 100) if IlluminatePerfected1 else "Not Obtained"
)

IlluminatePerfected2 = total_illuminate_missions >= 250
IlluminatePerfected2_date = (
    get_nth_date(df, df["Enemy Type"] == "Illuminate", 250) if IlluminatePerfected2 else "Not Obtained"
)

IlluminatePerfected3 = total_illuminate_missions >= 500
IlluminatePerfected3_date = (
    get_nth_date(df, df["Enemy Type"] == "Illuminate", 500) if IlluminatePerfected3 else "Not Obtained"
)


# For kill counts, need to track cumulative sums
def get_kill_milestone_date(df, enemy_type, threshold):
    # Date when cumulative kills vs given enemy reach threshold; challenge badges
    enemy_df = df[df["Enemy Type"] == enemy_type].copy()
    enemy_df["cumsum"] = enemy_df["Kills"].cumsum()
    if (enemy_df["cumsum"] >= threshold).any():
        return enemy_df.loc[enemy_df["cumsum"] >= threshold].iloc[0]["Time"]
    return "Not Obtained"


def get_first_time(mask):
    # First mission time matching a boolean mask; reused by date fields
    matching_times = df.loc[mask, "Time"]
    return matching_times.iloc[0] if not matching_times.empty else "Not Obtained"


TerminidHunter1 = total_terminid_kills >= 10000
TerminidHunter1_date = get_kill_milestone_date(df, "Terminids", 10000) if TerminidHunter1 else "Not Obtained"

TerminidHunter2 = total_terminid_kills >= 25000
TerminidHunter2_date = get_kill_milestone_date(df, "Terminids", 25000) if TerminidHunter2 else "Not Obtained"

TerminidHunter3 = total_terminid_kills >= 50000
TerminidHunter3_date = get_kill_milestone_date(df, "Terminids", 50000) if TerminidHunter3 else "Not Obtained"

AutomatonHunter1 = total_automaton_kills >= 10000
AutomatonHunter1_date = get_kill_milestone_date(df, "Automatons", 10000) if AutomatonHunter1 else "Not Obtained"

AutomatonHunter2 = total_automaton_kills >= 25000
AutomatonHunter2_date = get_kill_milestone_date(df, "Automatons", 25000) if AutomatonHunter2 else "Not Obtained"

AutomatonHunter3 = total_automaton_kills >= 50000
AutomatonHunter3_date = get_kill_milestone_date(df, "Automatons", 50000) if AutomatonHunter3 else "Not Obtained"

IlluminateHunter1 = total_illuminate_kills >= 10000
IlluminateHunter1_date = get_kill_milestone_date(df, "Illuminate", 10000) if IlluminateHunter1 else "Not Obtained"

IlluminateHunter2 = total_illuminate_kills >= 25000
IlluminateHunter2_date = get_kill_milestone_date(df, "Illuminate", 25000) if IlluminateHunter2 else "Not Obtained"

IlluminateHunter3 = total_illuminate_kills >= 50000
IlluminateHunter3_date = get_kill_milestone_date(df, "Illuminate", 50000) if IlluminateHunter3 else "Not Obtained"

# Streak achievements already tracked externally
Streak10 = streak_10
Streak10_date = get_first_time(streak_10_mask)
Streak20 = streak_20
Streak20_date = get_first_time(streak_20_mask)
Streak30 = streak_30
Streak30_date = get_first_time(streak_30_mask)

# Special locations/achievements
MalevelonCreek = malevelon_creek
MalevelonCreek_date = first_time_by_planet.get("Malevelon Creek", "Not Obtained") if malevelon_creek else "Not Obtained"

SuperEarth = super_earth
SuperEarth_date = first_time_by_planet.get("Super Earth", "Not Obtained") if super_earth else "Not Obtained"

Cyberstan = cyberstan
Cyberstan_date = first_time_by_planet.get("Cyberstan", "Not Obtained") if cyberstan else "Not Obtained"

# Milestone achievements
CmdFavourite4 = total_missions >= 1000
CmdFavourite4_date = get_nth_date(df, pd.Series([True] * len(df)), 1000) if CmdFavourite4 else "Not Obtained"

ReliableDiver4 = total_missions_major_order >= 1000
ReliableDiver4_date = get_nth_date(df, df["Major Order"] == 1, 1000) if ReliableDiver4 else "Not Obtained"

DSSDiver4 = total_missions_dss >= 1000
DSSDiver4_date = get_nth_date(df, df["DSS Active"] == 1, 1000) if DSSDiver4 else "Not Obtained"

CityDiver4 = total_missions_city >= 1000
CityDiver4_date = get_nth_date(df, df["Mega Structure"] == 1, 1000) if CityDiver4 else "Not Obtained"

OutbreakPerfected4 = total_terminid_missions >= 1000
OutbreakPerfected4_date = (
    get_nth_date(df, df["Enemy Type"] == "Terminids", 1000) if OutbreakPerfected4 else "Not Obtained"
)

AutomatonPerfected4 = total_automaton_missions >= 1000
AutomatonPerfected4_date = (
    get_nth_date(df, df["Enemy Type"] == "Automatons", 1000) if AutomatonPerfected4 else "Not Obtained"
)

IlluminatePerfected4 = total_illuminate_missions >= 1000
IlluminatePerfected4_date = (
    get_nth_date(df, df["Enemy Type"] == "Illuminate", 1000) if IlluminatePerfected4 else "Not Obtained"
)

TerminidHunter4 = total_terminid_kills >= 100000
TerminidHunter4_date = get_kill_milestone_date(df, "Terminids", 100000) if TerminidHunter4 else "Not Obtained"

AutomatonHunter4 = total_automaton_kills >= 100000
AutomatonHunter4_date = get_kill_milestone_date(df, "Automatons", 100000) if AutomatonHunter4 else "Not Obtained"

IlluminateHunter4 = total_illuminate_kills >= 100000
IlluminateHunter4_date = get_kill_milestone_date(df, "Illuminate", 100000) if IlluminateHunter4 else "Not Obtained"


# For total kills milestone
def get_total_kills_date(df, threshold):
    # Date when total cumulative kills reach threshold; SuperHunter/Milestones
    df_copy = df.copy()
    df_copy["cumsum"] = df_copy["Kills"].cumsum()
    if (df_copy["cumsum"] >= threshold).any():
        return df_copy.loc[df_copy["cumsum"] >= threshold].iloc[0]["Time"]
    return "Not Obtained"


SuperHunter = total_kills >= 1000000
SuperHunter_date = get_total_kills_date(df, 1000000) if SuperHunter else "Not Obtained"

# Composite achievements
# Get the completion date for EveryAchievement - find latest date among all requirements
EveryAchievement = (
    total_missions >= 500
    and total_missions_major_order >= 500
    and total_missions_dss >= 500
    and total_missions_planets >= 100
    and total_missions_sectors >= 45
)

# Get dates for all requirements
achievement_dates = [
    get_nth_date(df, pd.Series([True] * len(df)), 500) if total_missions >= 500 else None,
    get_nth_date(df, df["Major Order"] == 1, 500) if total_missions_major_order >= 500 else None,
    get_nth_date(df, df["DSS Active"] == 1, 500) if total_missions_dss >= 500 else None,
    get_unique_planet_milestone_date(df, 100) if total_missions_planets >= 100 else None,
    get_unique_sector_milestone_date(df, 45) if total_missions_sectors >= 45 else None,
]

# Filter out None and "Not Obtained" values
valid_dates = [d for d in achievement_dates if d and d != "Not Obtained"]

# Set the date to the most recent completion date if all requirements are met
EveryAchievement_date = max(valid_dates) if EveryAchievement and valid_dates else "Not Obtained"
# Get the completion date for EveryChallenge - find latest date among all challenge requirements
EveryChallenge = (
    total_terminid_missions >= 500
    and total_automaton_missions >= 500
    and total_illuminate_missions >= 500
    and total_terminid_kills >= 50000
    and total_automaton_kills >= 50000
    and total_illuminate_kills >= 50000
    and streak_30
)

# Get dates for all challenge requirements
challenge_dates = [
    get_nth_date(df, df["Enemy Type"] == "Terminids", 500) if total_terminid_missions >= 500 else None,
    get_nth_date(df, df["Enemy Type"] == "Automatons", 500) if total_automaton_missions >= 500 else None,
    get_nth_date(df, df["Enemy Type"] == "Illuminate", 500) if total_illuminate_missions >= 500 else None,
    get_kill_milestone_date(df, "Terminids", 50000) if total_terminid_kills >= 50000 else None,
    get_kill_milestone_date(df, "Automatons", 50000) if total_automaton_kills >= 50000 else None,
    get_kill_milestone_date(df, "Illuminate", 50000) if total_illuminate_kills >= 50000 else None,
    get_first_time(streak_30_mask) if streak_30 else None,
]

# Filter out None and "Not Obtained" values
valid_challenge_dates = [d for d in challenge_dates if d and d != "Not Obtained"]

# Set the date to the most recent completion date if all requirements are met
EveryChallenge_date = max(valid_challenge_dates) if EveryChallenge and valid_challenge_dates else "Not Obtained"
AllDifficulties = all_difficulties
# Get the latest date when all difficulty types were completed
difficulty_completion_dates = []
if AllDifficulties:
    for difficulty in [
        "1 - TRIVIAL",
        "2 - EASY",
        "3 - MEDIUM",
        "4 - CHALLENGING",
        "5 - HARD",
        "6 - EXTREME",
        "7 - SUICIDE MISSION",
        "8 - IMPOSSIBLE",
        "9 - HELLDIVE",
        "10 - SUPER HELLDIVE",
    ]:
        first_time = first_time_by_difficulty.get(difficulty)
        if first_time is not None:
            difficulty_completion_dates.append(first_time)
    AllDifficulties_date = max(difficulty_completion_dates) if difficulty_completion_dates else "Not Obtained"
else:
    AllDifficulties_date = "Not Obtained"

AllCampaigns = all_campaigns
# Get the latest date when all campaign types were completed
campaign_completion_dates = []
if AllCampaigns:
    for campaign in [
        "Liberation",
        "Defense",
        "Invasion",
        "High-Priority",
        "Attrition",
        "Battle for Super Earth",
        "Recon",
        "Battle for Cyberstan",
    ]:
        first_time = first_time_by_campaign.get(campaign)
        if first_time is not None:
            campaign_completion_dates.append(first_time)
    AllCampaigns_date = max(campaign_completion_dates) if campaign_completion_dates else "Not Obtained"
else:
    AllCampaigns_date = "Not Obtained"

AllBiomes = all_biomes
# Get the latest date when all standard biomes were completed
biome_completion_dates = []
if AllBiomes:
    for planet in df["Planet"].unique():
        if planet in biome_mapping:
            biome = biome_mapping[planet]
            if biome in standard_biomes:
                planet_first_visit = first_time_by_planet.get(planet)
                biome_completion_dates.append(planet_first_visit)
    AllBiomes_date = max(biome_completion_dates) if biome_completion_dates else "Not Obtained"
else:
    AllBiomes_date = "Not Obtained"
DisgracefulConduct = disgraceful_conduct
DisgracefulConduct_date = (
    first_time_by_rating.get("Disgraceful Conduct", "Not Obtained") if disgraceful_conduct else "Not Obtained"
)
CostlyFailure = costly_failure
CostlyFailure_date = first_time_by_rating.get("Costly Failure", "Not Obtained") if costly_failure else "Not Obtained"
EveryTriumph = (
    malevelon_creek
    and super_earth
    and cyberstan
    and all_difficulties
    and all_campaigns
    and all_biomes
    and disgraceful_conduct
    and costly_failure
)

# Get dates for all triumph requirements
triumph_dates = [
    first_time_by_planet.get("Malevelon Creek") if malevelon_creek else None,
    first_time_by_planet.get("Super Earth") if super_earth else None,
    first_time_by_planet.get("Cyberstan") if cyberstan else None,
    AllDifficulties_date if all_difficulties and AllDifficulties_date != "Not Obtained" else None,
    AllCampaigns_date if all_campaigns and AllCampaigns_date != "Not Obtained" else None,
    AllBiomes_date if all_biomes and AllBiomes_date != "Not Obtained" else None,
    first_time_by_rating.get("Disgraceful Conduct") if disgraceful_conduct else None,
    first_time_by_rating.get("Costly Failure") if costly_failure else None,
]

# Filter out None and "Not Obtained" values
valid_triumph_dates = [d for d in triumph_dates if d and d != "Not Obtained"]

# Set the date to the most recent completion date if all requirements are met
EveryTriumph_date = max(valid_triumph_dates) if EveryTriumph and valid_triumph_dates else "Not Obtained"


# Get date when first mission type reached 100 completions
def get_first_mission_100_date(df):
    # First date any mission type hits 100 completions; milestone tracking
    mission_counts = df.groupby(["Mission Type", "Time"]).size().reset_index(name="count")
    mission_counts["cumsum"] = mission_counts.groupby("Mission Type")["count"].cumsum()
    missions_100 = mission_counts[mission_counts["cumsum"] >= 100]
    if not missions_100.empty:
        return missions_100.iloc[0]["Time"]
    return "Not Obtained"


OneMission = one_mission_100
OneMission_date = get_first_mission_100_date(df) if OneMission else "Not Obtained"


# Function to get date when first planet reached 100 missions
def get_first_planet_100_date(df):
    # First date any planet reaches 100 missions; milestone tracking
    planet_counts = df.groupby(["Planet", "Time"]).size().reset_index(name="count")
    planet_counts["cumsum"] = planet_counts.groupby("Planet")["count"].cumsum()
    planets_100 = planet_counts[planet_counts["cumsum"] >= 100]
    if not planets_100.empty:
        return planets_100.iloc[0]["Time"]
    return "Not Obtained"


OnePlanet = one_planet_100
OnePlanet_date = get_first_planet_100_date(df) if OnePlanet else "Not Obtained"


# Get date when first sector reached 100 missions
def get_first_sector_100_date(df):
    # First date any sector reaches 100 missions; milestone tracking
    sector_counts = df.groupby(["Sector", "Time"]).size().reset_index(name="count")
    sector_counts["cumsum"] = sector_counts.groupby("Sector")["count"].cumsum()
    sectors_100 = sector_counts[sector_counts["cumsum"] >= 100]
    if not sectors_100.empty:
        return sectors_100.iloc[0]["Time"]
    return "Not Obtained"


OneSector = one_sector_100
OneSector_date = get_first_sector_100_date(df) if OneSector else "Not Obtained"
EveryMilestone = (
    total_missions >= 1000
    and total_missions_major_order >= 1000
    and total_missions_dss >= 1000
    and total_missions_city >= 1000
    and total_terminid_missions >= 1000
    and total_automaton_missions >= 1000
    and total_illuminate_missions >= 1000
    and total_terminid_kills >= 100000
    and total_automaton_kills >= 100000
    and total_illuminate_kills >= 100000
    and total_kills >= 1000000
)
# Get dates for all milestone requirements
milestone_dates = [
    get_nth_date(df, pd.Series([True] * len(df)), 1000) if total_missions >= 1000 else None,
    get_nth_date(df, df["Major Order"] == 1, 1000) if total_missions_major_order >= 1000 else None,
    get_nth_date(df, df["DSS Active"] == 1, 1000) if total_missions_dss >= 1000 else None,
    get_nth_date(df, df["Mega Structure"] == 1, 1000) if total_missions_city >= 1000 else None,
    get_nth_date(df, df["Enemy Type"] == "Terminids", 1000) if total_terminid_missions >= 1000 else None,
    get_nth_date(df, df["Enemy Type"] == "Automatons", 1000) if total_automaton_missions >= 1000 else None,
    get_nth_date(df, df["Enemy Type"] == "Illuminate", 1000) if total_illuminate_missions >= 1000 else None,
    get_kill_milestone_date(df, "Terminids", 100000) if total_terminid_kills >= 100000 else None,
    get_kill_milestone_date(df, "Automatons", 100000) if total_automaton_kills >= 100000 else None,
    get_kill_milestone_date(df, "Illuminate", 100000) if total_illuminate_kills >= 100000 else None,
    get_total_kills_date(df, 1000000) if total_kills >= 1000000 else None,
]

# Filter out None and "Not Obtained" values
valid_milestone_dates = [d for d in milestone_dates if d and d != "Not Obtained"]

# Set the date to the most recent completion date if all requirements are met
EveryMilestone_date = max(valid_milestone_dates) if EveryMilestone and valid_milestone_dates else "Not Obtained"

OneHundredPercent = EveryAchievement and EveryChallenge and EveryTriumph and EveryMilestone
# Get 100% completion date
if OneHundredPercent:
    dates_to_check = [EveryAchievement_date, EveryChallenge_date, EveryTriumph_date, EveryMilestone_date]
    # Filter out "Not Obtained"
    valid_dates = [d for d in dates_to_check if d != "Not Obtained"]
    OneHundredPercent_date = max(valid_dates) if valid_dates else "Not Obtained"
else:
    OneHundredPercent_date = "Not Obtained"

# Create a dictionary to store the achievements
achievements = {
    "CmdFavourite1": CmdFavourite1,
    "CmdFavourite2": CmdFavourite2,
    "CmdFavourite3": CmdFavourite3,
    "ReliableDiver1": ReliableDiver1,
    "ReliableDiver2": ReliableDiver2,
    "ReliableDiver3": ReliableDiver3,
    "DSSDiver1": DSSDiver1,
    "DSSDiver2": DSSDiver2,
    "DSSDiver3": DSSDiver3,
    "PlanetDiver1": PlanetDiver1,
    "PlanetDiver2": PlanetDiver2,
    "PlanetDiver3": PlanetDiver3,
    "SectorDiver1": SectorDiver1,
    "SectorDiver2": SectorDiver2,
    "SectorDiver3": SectorDiver3,
    "EveryAchievement": EveryAchievement,
    "OutbreakPerfected1": OutbreakPerfected1,
    "OutbreakPerfected2": OutbreakPerfected2,
    "OutbreakPerfected3": OutbreakPerfected3,
    "AutomatonPerfected1": AutomatonPerfected1,
    "AutomatonPerfected2": AutomatonPerfected2,
    "AutomatonPerfected3": AutomatonPerfected3,
    "IlluminatePerfected1": IlluminatePerfected1,
    "IlluminatePerfected2": IlluminatePerfected2,
    "IlluminatePerfected3": IlluminatePerfected3,
    "TerminidHunter1": TerminidHunter1,
    "TerminidHunter2": TerminidHunter2,
    "TerminidHunter3": TerminidHunter3,
    "AutomatonHunter1": AutomatonHunter1,
    "AutomatonHunter2": AutomatonHunter2,
    "AutomatonHunter3": AutomatonHunter3,
    "IlluminateHunter1": IlluminateHunter1,
    "IlluminateHunter2": IlluminateHunter2,
    "IlluminateHunter3": IlluminateHunter3,
    "Streak10": Streak10,
    "Streak20": Streak20,
    "Streak30": Streak30,
    "EveryChallenge": EveryChallenge,
    "MalevelonCreek": MalevelonCreek,
    "SuperEarth": SuperEarth,
    "Cyberstan": Cyberstan,
    "AllDifficulties": AllDifficulties,
    "AllCampaigns": AllCampaigns,
    "AllBiomes": AllBiomes,
    "CostlyFailure": CostlyFailure,
    "DisgracefulConduct": DisgracefulConduct,
    "EveryTriumph": EveryTriumph,
    "OneMission": OneMission,
    "OnePlanet": OnePlanet,
    "OneSector": OneSector,
    "CmdFavourite4": CmdFavourite4,
    "ReliableDiver4": ReliableDiver4,
    "DSSDiver4": DSSDiver4,
    "OutbreakPerfected4": OutbreakPerfected4,
    "AutomatonPerfected4": AutomatonPerfected4,
    "IlluminatePerfected4": IlluminatePerfected4,
    "TerminidHunter4": TerminidHunter4,
    "AutomatonHunter4": AutomatonHunter4,
    "IlluminateHunter4": IlluminateHunter4,
    "SuperHunter": SuperHunter,
    "EveryMilestone": EveryMilestone,
    "OneHundredPercent": OneHundredPercent,
}

# Calculate total achievements completed
total_achievements = len(achievements)
completed_achievements = sum(1 for value in achievements.values() if value)
achievement_percentage = round((completed_achievements / total_achievements) * 100, 1)

# Add to achievements dictionary
achievements["completion_percentage"] = achievement_percentage

from core.utils import get_effective_flair

flair_colour = get_effective_flair()
FlairLeftIco = iconconfig["MiscIcon"].get(f"Flair Left {flair_colour}", iconconfig["MiscIcon"]["Flair Left"])
FlairRightIco = iconconfig["MiscIcon"].get(f"Flair Right {flair_colour}", iconconfig["MiscIcon"]["Flair Right"])
Locked1Ico = iconconfig["MiscIcon"]["Locked 1"]
Locked2Ico = iconconfig["MiscIcon"]["Locked 2"]
Locked3Ico = iconconfig["MiscIcon"]["Locked 3"]
Locked4Ico = iconconfig["MiscIcon"]["Locked 4"]
Bronze1Ico = iconconfig["MiscIcon"]["Bronze 1"]
Bronze2Ico = iconconfig["MiscIcon"]["Bronze 2"]
Silver1Ico = iconconfig["MiscIcon"]["Silver 1"]
Silver2Ico = iconconfig["MiscIcon"]["Silver 2"]
Gold1Ico = iconconfig["MiscIcon"]["Gold 1"]
Gold2Ico = iconconfig["MiscIcon"]["Gold 2"]
Gold3Ico = iconconfig["MiscIcon"]["Gold 3"]
Gold4Ico = iconconfig["MiscIcon"]["Gold 4"]
GoldFlairLeftIco = iconconfig["MiscIcon"]["Gold Flair Left"]
GoldFlairRightIco = iconconfig["MiscIcon"]["Gold Flair Right"]

# Define achievement metadata for messages and titles
ACHIEVEMENT_DEFS = {
    "CmdFavourite1": {
        "message": ("Log 100 Missions", "HINT: You have the strength and the courage... to be free"),
        "title": (f"{Bronze1Ico} **HIGH COMMAND'S FAVOURITE I**", f"{Locked1Ico} **~~HIGH COMMAND'S FAVOURITE I~~**"),
    },
    "CmdFavourite2": {
        "message": ("Log 250 Missions", "HINT: You have the strength and the courage... to be free"),
        "title": (f"{Silver1Ico} **HIGH COMMAND'S FAVOURITE II**", f"{Locked1Ico} **~~HIGH COMMAND'S FAVOURITE II~~**"),
    },
    "CmdFavourite3": {
        "message": ("Log 500 Missions", "HINT: You have the strength and the courage... to be free"),
        "title": (f"{Gold1Ico} **HIGH COMMAND'S FAVOURITE III**", f"{Locked1Ico} **~~HIGH COMMAND'S FAVOURITE III~~**"),
    },
    "ReliableDiver1": {
        "message": ("Log 100 Major Order Missions", "HINT: You're one to obey orders"),
        "title": (f"{Bronze1Ico} **RELIABLE DIVER I**", f"{Locked1Ico} **~~RELIABLE DIVER I~~**"),
    },
    "ReliableDiver2": {
        "message": ("Log 250 Major Order Missions", "HINT: You're one to obey orders"),
        "title": (f"{Silver1Ico} **RELIABLE DIVER II**", f"{Locked1Ico} **~~RELIABLE DIVER II~~**"),
    },
    "ReliableDiver3": {
        "message": ("Log 500 Major Order Missions", "HINT: You're one to obey orders"),
        "title": (f"{Gold1Ico} **RELIABLE DIVER III**", f"{Locked1Ico} **~~RELIABLE DIVER III~~**"),
    },
    "DSSDiver1": {
        "message": (
            "Log 100 Missions with the Democracy Space Station in Orbit",
            "HINT: You like a good bit of support",
        ),
        "title": (f"{Bronze1Ico} **I <3 DSS I**", f"{Locked1Ico} **~~I <3 DSS I~~**"),
    },
    "DSSDiver2": {
        "message": (
            "Log 250 Missions with the Democracy Space Station in Orbit",
            "HINT: You like a good bit of support",
        ),
        "title": (f"{Silver1Ico} **I <3 DSS II**", f"{Locked1Ico} **~~I <3 DSS II~~**"),
    },
    "DSSDiver3": {
        "message": (
            "Log 500 Missions with the Democracy Space Station in Orbit",
            "HINT: You like a good bit of support",
        ),
        "title": (f"{Gold1Ico} **I <3 DSS III**", f"{Locked1Ico} **~~I <3 DSS III~~**"),
    },
    "PlanetDiver1": {
        "message": ("Log Missions on 25 Different Planets", "HINT: You leave no stone unturned"),
        "title": (f"{Bronze1Ico} **THE LONG MARCH OF LIBERTY I**", f"{Locked1Ico} **~~THE LONG MARCH OF LIBERTY I~~**"),
    },
    "PlanetDiver2": {
        "message": ("Log Missions on 50 Different Planets", "HINT: You leave no stone unturned"),
        "title": (
            f"{Silver1Ico} **THE LONG MARCH OF LIBERTY II**",
            f"{Locked1Ico} **~~THE LONG MARCH OF LIBERTY II~~**",
        ),
    },
    "PlanetDiver3": {
        "message": ("Log Missions on 100 Different Planets", "HINT: You leave no stone unturned"),
        "title": (
            f"{Gold1Ico} **THE LONG MARCH OF LIBERTY III**",
            f"{Locked1Ico} **~~THE LONG MARCH OF LIBERTY III~~**",
        ),
    },
    "SectorDiver1": {
        "message": ("Log Missions on 15 Different Sectors", "HINT: You like to cover all bases"),
        "title": (f"{Bronze1Ico} **MASTER OF THE MAP I**", f"{Locked1Ico} **~~MASTER OF THE MAP I~~**"),
    },
    "SectorDiver2": {
        "message": ("Log Missions on 30 Different Sectors", "HINT: You like to cover all bases"),
        "title": (f"{Silver1Ico} **MASTER OF THE MAP II**", f"{Locked1Ico} **~~MASTER OF THE MAP II~~**"),
    },
    "SectorDiver3": {
        "message": ("Log Missions on 45 Different Sectors", "HINT: You like to cover all bases"),
        "title": (f"{Gold1Ico} **MASTER OF THE MAP III**", f"{Locked1Ico} **~~MASTER OF THE MAP III~~**"),
    },
    "EveryAchievement": {
        "message": ("Complete Every Achievement", "HINT: You love a good hunt"),
        "title": (f"{Gold1Ico} **ACHIEVEMENT HUNTER**", f"{Locked1Ico} **~~ACHIEVEMENT HUNTER~~**"),
    },
    "OutbreakPerfected1": {
        "message": ("Log 100 Terminid Missions", "HINT: You're rather familiar with E-710"),
        "title": (f"{Bronze2Ico} **OUTBREAK PERFECTED I**", f"{Locked2Ico} **~~OUTBREAK PERFECTED I~~**"),
    },
    "OutbreakPerfected2": {
        "message": ("Log 250 Terminid Missions", "HINT: You're rather familiar with E-710"),
        "title": (f"{Silver2Ico} **OUTBREAK PERFECTED II**", f"{Locked2Ico} **~~OUTBREAK PERFECTED II~~**"),
    },
    "OutbreakPerfected3": {
        "message": ("Log 500 Terminid Missions", "HINT: You're rather familiar with E-710"),
        "title": (f"{Gold2Ico} **OUTBREAK PERFECTED III**", f"{Locked2Ico} **~~OUTBREAK PERFECTED III~~**"),
    },
    "AutomatonPerfected1": {
        "message": ("Log 100 Automaton Missions", "HINT: You're rather familiar with losing access to your Stratagems"),
        "title": (f"{Bronze2Ico} **INCURSION DEVASTATED I**", f"{Locked2Ico} **~~INCURSION DEVASTATED I~~**"),
    },
    "AutomatonPerfected2": {
        "message": ("Log 250 Automaton Missions", "HINT: You're rather familiar with losing access to your Stratagems"),
        "title": (f"{Silver2Ico} **INCURSION DEVASTATED II**", f"{Locked2Ico} **~~INCURSION DEVASTATED II~~**"),
    },
    "AutomatonPerfected3": {
        "message": ("Log 500 Automaton Missions", "HINT: You're rather familiar with losing access to your Stratagems"),
        "title": (f"{Gold2Ico} **INCURSION DEVASTATED III**", f"{Locked2Ico} **~~INCURSION DEVASTATED III~~**"),
    },
    "IlluminatePerfected1": {
        "message": ("Log 100 Illuminate Missions", "HINT: You're rather familiar with their autocratic intentions"),
        "title": (f"{Bronze2Ico} **INVASION ABOLISHED I**", f"{Locked2Ico} **~~INVASION ABOLISHED I~~**"),
    },
    "IlluminatePerfected2": {
        "message": ("Log 250 Illuminate Missions", "HINT: You're rather familiar with their autocratic intentions"),
        "title": (f"{Silver2Ico} **INVASION ABOLISHED II**", f"{Locked2Ico} **~~INVASION ABOLISHED II~~**"),
    },
    "IlluminatePerfected3": {
        "message": ("Log 500 Illuminate Missions", "HINT: You're rather familiar with their autocratic intentions"),
        "title": (f"{Gold2Ico} **INVASION ABOLISHED III**", f"{Locked2Ico} **~~INVASION ABOLISHED III~~**"),
    },
    "TerminidHunter1": {
        "message": ("Log 10,000 Kills against the Terminids", "HINT: You douse yourself in E-710"),
        "title": (f"{Bronze2Ico} **BUG STOMPER I**", f"{Locked2Ico} **~~BUG STOMPER I~~**"),
    },
    "TerminidHunter2": {
        "message": ("Log 25,000 Kills against the Terminids", "HINT: You douse yourself in E-710"),
        "title": (f"{Silver2Ico} **BUG STOMPER II**", f"{Locked2Ico} **~~BUG STOMPER II~~**"),
    },
    "TerminidHunter3": {
        "message": ("Log 50,000 Kills against the Terminids", "HINT: You douse yourself in E-710"),
        "title": (f"{Gold2Ico} **BUG STOMPER III**", f"{Locked2Ico} **~~BUG STOMPER III~~**"),
    },
    "AutomatonHunter1": {
        "message": (
            "Log 10,000 Kills against the Automatons",
            "HINT: You make things out of scrap metal in your spare time",
        ),
        "title": (f"{Bronze2Ico} **CLANKER SCRAPPER I**", f"{Locked2Ico} **~~CLANKER SCRAPPER I~~**"),
    },
    "AutomatonHunter2": {
        "message": (
            "Log 25,000 Kills against the Automatons",
            "HINT: You make things out of scrap metal in your spare time",
        ),
        "title": (f"{Silver2Ico} **CLANKER SCRAPPER II**", f"{Locked2Ico} **~~CLANKER SCRAPPER II~~**"),
    },
    "AutomatonHunter3": {
        "message": (
            "Log 50,000 Kills against the Automatons",
            "HINT: You make things out of scrap metal in your spare time",
        ),
        "title": (f"{Gold2Ico} **CLANKER SCRAPPER III**", f"{Locked2Ico} **~~CLANKER SCRAPPER III~~**"),
    },
    "IlluminateHunter1": {
        "message": (
            "Log 10,000 Kills against the Illuminate",
            "HINT: You single handedly make an effort of wiping them out of the Second Galactic War",
        ),
        "title": (f"{Bronze2Ico} **SQUID SEVERER I**", f"{Locked2Ico} **~~SQUID SEVERER I~~**"),
    },
    "IlluminateHunter2": {
        "message": (
            "Log 25,000 Kills against the Illuminate",
            "HINT: You single handedly make an effort of wiping them out of the Second Galactic War",
        ),
        "title": (f"{Silver2Ico} **SQUID SEVERER II**", f"{Locked2Ico} **~~SQUID SEVERER II~~**"),
    },
    "IlluminateHunter3": {
        "message": (
            "Log 50,000 Kills against the Illuminate",
            "HINT: You single handedly make an effort of wiping them out of the Second Galactic War",
        ),
        "title": (f"{Gold2Ico} **SQUID SEVERER III**", f"{Locked2Ico} **~~SQUID SEVERER III~~**"),
    },
    "Streak10": {
        "message": (
            "Reach a Streak of 10",
            "HINT: You'll need to take some annual leave after this... seriously... Democracy Applauds You!",
        ),
        "title": (f"{Bronze2Ico} **INFLAMMABLE I**", f"{Locked2Ico} **~~INFLAMMABLE I~~**"),
    },
    "Streak20": {
        "message": (
            "Reach a Streak of 20",
            "HINT: You'll need to take some annual leave after this... seriously... Democracy Applauds You!",
        ),
        "title": (f"{Silver2Ico} **INFLAMMABLE II**", f"{Locked2Ico} **~~INFLAMMABLE II~~**"),
    },
    "Streak30": {
        "message": (
            "Reach a Streak of 30",
            "HINT: You'll need to take some annual leave after this... seriously... Democracy Applauds You!",
        ),
        "title": (f"{Gold2Ico} **INFLAMMABLE III**", f"{Locked2Ico} **~~INFLAMMABLE III~~**"),
    },
    "EveryChallenge": {
        "message": ("Complete Every Challenge", "HINT: You love a good challenge"),
        "title": (f"{Gold2Ico} **A NEW CHALLENGER APPROACHES**", f"{Locked2Ico} **~~A NEW CHALLENGER APPROACHES~~**"),
    },
    "MalevelonCreek": {
        "message": ("Serve on Malevelon Creek", "HINT: You remember..."),
        "title": (f"{Gold3Ico} **NEVER FORGET**", f"{Locked3Ico} **~~NEVER FORGET~~**"),
    },
    "SuperEarth": {
        "message": ("Serve on Super Earth", "HINT: You feel very welcome"),
        "title": (f"{Gold3Ico} **HOME SUPER HOME**", f"{Locked3Ico} **~~HOME SUPER HOME~~**"),
    },
    "Cyberstan": {
        "message": ("Serve on an Enemy Homeworld", "HINT: You don't feel very welcome... like they have a choice"),
        "title": (f"{Gold3Ico} **ON THE ENEMY'S DOORSTEP**", f"{Locked3Ico} **~~ON THE ENEMY'S DOORSTEP~~**"),
    },
    "AllDifficulties": {
        "message": (
            "Complete 1 of Every Difficulty Type",
            "HINT: You don't care how difficult the task, as long as democracy is spread",
        ),
        "title": (f"{Gold3Ico} **JACK OF ALL TRADES**", f"{Locked3Ico} **~~JACK OF ALL TRADES~~**"),
    },
    "AllCampaigns": {
        "message": (
            "Complete 1 of Every Campaign Type",
            "HINT: You have a wide range of choice, and you picked every single one",
        ),
        "title": (f"{Gold3Ico} **QUEEN OF ALL TRADES**", f"{Locked3Ico} **~~QUEEN OF ALL TRADES~~**"),
    },
    "AllBiomes": {
        "message": (
            "Complete 1 of Every Biome Type",
            "HINT: You are well versed with every terrain, every parameter, every storm",
        ),
        "title": (f"{Gold3Ico} **KING OF ALL TRADES**", f"{Locked3Ico} **~~KING OF ALL TRADES~~**"),
    },
    "DisgracefulConduct": {
        "message": ("Get a Performance Rating of Disgraceful Conduct on a Mission", "HINT: You... why?"),
        "title": (f"{Gold3Ico} **you got this on purpose...**", f"{Locked3Ico} **~~you got this on purpose...~~**"),
    },
    "CostlyFailure": {
        "message": ("Get a Performance Rating of Costly Failure on a Mission", "HINT: You... okay but seriously why?"),
        "title": (
            f"{Gold3Ico} **okay I was serious before but... you really did get this on purpose...**",
            f"{Locked3Ico} **~~okay I was serious before but... you really did get this on purpose...~~**",
        ),
    },
    "EveryTriumph": {
        "message": ("Complete Every Triumph", "HINT: You alone are the triumphant one"),
        "title": (f"{Gold3Ico} **A TRIUMPHANT RETURN**", f"{Locked3Ico} **~~A TRIUMPHANT RETURN~~**"),
    },
    "OneMission": {
        "message": ("Log 100 Missions of 1 Mission Type", "HINT: You don't even need teammates for this mission"),
        "title": (f"{Gold4Ico} **LET ME SOLO THIS**", f"{Locked4Ico} **~~LET ME SOLO THIS~~**"),
    },
    "OnePlanet": {
        "message": ("Log 100 Missions of 1 Planet Type", "HINT: You must really like this planet"),
        "title": (f"{Gold4Ico} **NEW HOMEWORLD**", f"{Locked4Ico} **~~NEW HOMEWORLD~~**"),
    },
    "OneSector": {
        "message": ("Log 100 Missions of 1 Sector Type", "HINT: Your name echoes from the neighbouring planets"),
        "title": (f"{Gold4Ico} **THEY FEAR YOUR NAME**", f"{Locked4Ico} **~~THEY FEAR YOUR NAME~~**"),
    },
    "CmdFavourite4": {
        "message": (
            "Log 1000 Missions",
            "HINT: You have earned your rightful place on Super Earth, and served with purpose",
        ),
        "title": (f"{Gold4Ico} **HELLDIVERS TO HELLPODS**", f"{Locked4Ico} **~~HELLDIVERS TO HELLPODS~~**"),
    },
    "ReliableDiver4": {
        "message": ("Log 1000 Major Order Missions", "HINT: You're always there, when they call your name"),
        "title": (f"{Gold4Ico} **AT EASE SUPER PRIVATE**", f"{Locked4Ico} **~~AT EASE SUPER PRIVATE~~**"),
    },
    "DSSDiver4": {
        "message": ("Log 1000 Missions with the Democracy Space Station in Orbit", "HINT: You are one with democracy"),
        "title": (f"{Gold4Ico} **I REALLY <3 DSS**", f"{Locked4Ico} **~~I REALLY <3 DSS~~**"),
    },
    "OutbreakPerfected4": {
        "message": ("Log 1000 Terminid Missions", "HINT: You're way too familiar with E-710"),
        "title": (f"{Gold4Ico} **FOREVER INHALING GLOOM**", f"{Locked4Ico} **~~FOREVER INHALING GLOOM~~**"),
    },
    "AutomatonPerfected4": {
        "message": (
            "Log 1000 Automaton Missions",
            "HINT: You're way too familiar with losing access to your Stratagems",
        ),
        "title": (f"{Gold4Ico} **HEARING BINARY IN THE BUSHES**", f"{Locked4Ico} **~~HEARING BINARY IN THE BUSHES~~**"),
    },
    "IlluminatePerfected4": {
        "message": ("Log 1000 Illuminates Missions", "HINT: You're way too familiar with their autocratic intentions"),
        "title": (f"{Gold4Ico} **RID OF THY SQU'ITH**", f"{Locked4Ico} **~~RID OF THY SQU'ITH~~**"),
    },
    "TerminidHunter4": {
        "message": ("Kill 100,000 Terminids", "HINT: You can never have enough E-710"),
        "title": (f"{Gold4Ico} **DID SOMEONE SAY OIL?**", f"{Locked4Ico} **~~DID SOMEONE SAY OIL?~~**"),
    },
    "AutomatonHunter4": {
        "message": (
            "Kill 100,000 Automatons",
            "HINT: You can't pick the two apart, you just know these traitors must succumb at the hands of managed democracy",
        ),
        "title": (f"{Gold4Ico} **CYBORG OR AUTOMATON?**", f"{Locked4Ico} **~~CYBORG OR AUTOMATON?~~**"),
    },
    "IlluminateHunter4": {
        "message": (
            "Kill 100,000 Illuminate",
            "HINT: You can't tell how many more are left, but you will continue to make your mark on their population no matter the cost",
        ),
        "title": (f"{Gold4Ico} **PEACE WAS NEVER AN OPTION**", f"{Locked4Ico} **~~PEACE WAS NEVER AN OPTION~~**"),
    },
    "SuperHunter": {
        "message": ("Kill 1,000,000 Enemies", "HINT: Your enemies are a mere blur, nothing gets in the way of liberty"),
        "title": (f"{Gold4Ico} **NO MATTER THE FRONT**", f"{Locked4Ico} **~~NO MATTER THE FRONT~~**"),
    },
    "EveryMilestone": {
        "message": ("Complete Every Milestone", "HINT: Beating Top Records is just another day at the office"),
        "title": (f"{Gold4Ico} **SECOND GALACTIC WAR VETERAN**", f"{Locked4Ico} **~~SECOND GALACTIC WAR VETERAN~~**"),
    },
    "OneHundredPercent": {
        "message": ("Achieve 100% Completion", "HINT: ..."),
        "title": (f"{Gold4Ico} **JOHN HELLDIVER**", f"{Locked4Ico} **~~???~~**"),
    },
}

# Generate messages and titles dynamically
achievement_view = {}
for key, defs in ACHIEVEMENT_DEFS.items():
    achieved = achievements[key]
    achievement_view[key] = {
        "message": defs["message"][0] if achieved else defs["message"][1],
        "title": defs["title"][0] if achieved else defs["title"][1],
        "date": locals().get(f"{key}_date", "Not Obtained"),
    }


def render_achievement_lines(keys):
    lines = []
    for idx, key in enumerate(keys):
        entry = achievement_view[key]
        lines.append(f"> {entry['title']}")
        lines.append(f"> *{entry['message']}*")
        lines.append(f"> *{entry['date']}*")
        if idx != len(keys) - 1:
            lines.append("> ")
    return "\n".join(lines)


# generate embed message

helldiver_level = df["Level"].iloc[-1]
helldiver_title = df["Title"].iloc[-1]
helldiver_ses = df["Super Destroyer"].iloc[-1]
helldiver_name = df["Helldivers"].iloc[-1]
non_blank_notes = df["Note"].dropna()
latest_note = non_blank_notes.iloc[-1] if not non_blank_notes.empty else "No Quote"
helldiver_title_icon = TITLE_ICONS.get(helldiver_title, "")


# UID from local DCord.json (user settings)
try:
    with open(app_path("JSON", "DCord.json"), "r") as f:
        settings_data = json.load(f)
        UID = settings_data.get("discord_uid", "0")
except (FileNotFoundError, json.JSONDecodeError) as e:
    logging.error(f"Error loading settings.json: {e}")
    UID = "0"  # Fallback to default

# Get badge icons using centralized function
badge_data = get_badge_icons(DEBUG, APP_DATA, DATE_FORMAT)

# Build badge string: always-on first, then up to 4 user-selected badges
always_on_order = ["bicon", "ticon", "yearico", "PIco"]

# Load user's badge display preference from DCord.json if present
try:
    display_pref = settings_data.get("display_badges", None) if "settings_data" in locals() else None
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

# Create embed data
achievement_keys = [
    "CmdFavourite1",
    "CmdFavourite2",
    "CmdFavourite3",
    "ReliableDiver1",
    "ReliableDiver2",
    "ReliableDiver3",
    "DSSDiver1",
    "DSSDiver2",
    "DSSDiver3",
    "PlanetDiver1",
    "PlanetDiver2",
    "PlanetDiver3",
    "SectorDiver1",
    "SectorDiver2",
    "SectorDiver3",
    "EveryAchievement",
]
challenge_keys = [
    "OutbreakPerfected1",
    "OutbreakPerfected2",
    "OutbreakPerfected3",
    "AutomatonPerfected1",
    "AutomatonPerfected2",
    "AutomatonPerfected3",
    "IlluminatePerfected1",
    "IlluminatePerfected2",
    "IlluminatePerfected3",
    "TerminidHunter1",
    "TerminidHunter2",
    "TerminidHunter3",
    "AutomatonHunter1",
    "AutomatonHunter2",
    "AutomatonHunter3",
    "IlluminateHunter1",
    "IlluminateHunter2",
    "IlluminateHunter3",
    "Streak10",
    "Streak20",
    "Streak30",
    "EveryChallenge",
]
triumph_keys = [
    "MalevelonCreek",
    "SuperEarth",
    "Cyberstan",
    "AllDifficulties",
    "AllCampaigns",
    "AllBiomes",
    "DisgracefulConduct",
    "CostlyFailure",
    "EveryTriumph",
]
milestone_keys = [
    "OneMission",
    "OnePlanet",
    "OneSector",
    "CmdFavourite4",
    "ReliableDiver4",
    "DSSDiver4",
    "OutbreakPerfected4",
    "AutomatonPerfected4",
    "IlluminatePerfected4",
    "TerminidHunter4",
    "AutomatonHunter4",
    "IlluminateHunter4",
    "SuperHunter",
    "EveryMilestone",
    "OneHundredPercent",
]

achievements_description = (
    f"**Level {helldiver_level} | {helldiver_title} {helldiver_title_icon}**\n\n"
    f'"{latest_note}"\n\n'
    f"Total Completion: {achievement_percentage}%\n\n"
    f"{FlairLeftIco} {Gold1Ico} Achievements {Gold1Ico} {FlairRightIco}\n"
    f"{render_achievement_lines(achievement_keys)}"
)
challenges_description = (
    f"{FlairLeftIco} {Gold2Ico} Challenges {Gold2Ico} {FlairRightIco}\n{render_achievement_lines(challenge_keys)}"
)
triumphs_description = (
    f"{FlairLeftIco} {Gold3Ico} Triumphs {Gold3Ico} {FlairRightIco}\n{render_achievement_lines(triumph_keys)}"
)
milestones_description = (
    f"{GoldFlairLeftIco} {Gold4Ico} Milestones {Gold4Ico} {GoldFlairRightIco}\n"
    f"{render_achievement_lines(milestone_keys)}"
)

embed_data = {
    "content": None,
    "embeds": [
        {
            "title": f"{helldiver_ses}\nHelldiver: {helldiver_name}\n{badge_string}",
            "description": achievements_description,
            "color": 7257043,
            "author": {
                "name": f"SEAF Achievement Record\nDate: {date}",
                "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356001307596427564/NwNzS9B.png?ex=67eafa21&is=67e9a8a1&hm=7e204265cbcdeaf96d7b244cd63992c4ef10dc18befbcf2ed39c3a269af14ec0&",
            },
            "image": {
                "url": "https://cdn.discordapp.com/attachments/1340508329977446484/1416046371911241847/achievementsBanner.png?ex=68c56b73&is=68c419f3&hm=291ffb6f464c34e8fc2e20204d387ffaa8324d1e71165bd4f925e0dbb7dc6efc&"
            },
            "thumbnail": {"url": f"{profile_picture}"},
        },
        {
            "description": challenges_description,
            "color": 7257043,
            "author": {
                "name": f"SEAF Challenge Record\nDate: {date}",
                "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356001307596427564/NwNzS9B.png?ex=67eafa21&is=67e9a8a1&hm=7e204265cbcdeaf96d7b244cd63992c4ef10dc18befbcf2ed39c3a269af14ec0&",
            },
            "image": {
                "url": "https://cdn.discordapp.com/attachments/1340508329977446484/1416046378492235826/challengesBanner.png?ex=68c56b75&is=68c419f5&hm=acf7a19e5c86a0057171fd7f9c997a7f9989b0cda63232eba6dd15edeb082921&"
            },
        },
    ],
    "attachments": [],
}

embed_data_2 = {
    "content": None,
    "embeds": [
        {
            "description": triumphs_description,
            "color": 7257043,
            "author": {
                "name": f"SEAF Triumph Record\nDate: {date}",
                "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356001307596427564/NwNzS9B.png?ex=67eafa21&is=67e9a8a1&hm=7e204265cbcdeaf96d7b244cd63992c4ef10dc18befbcf2ed39c3a269af14ec0&",
            },
            "image": {
                "url": "https://cdn.discordapp.com/attachments/1340508329977446484/1416046382896250933/triumphsBanner.png?ex=68c56b76&is=68c419f6&hm=00f97614e113fab2ed23c56dbd5a2f94e9d7ddd963b0bcd9b3ce896dc04146aa&"
            },
        },
        {
            "description": milestones_description,
            "color": 16761088,
            "author": {
                "name": f"SEAF Milestone Record\nDate: {date}",
                "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356001307596427564/NwNzS9B.png?ex=67eafa21&is=67e9a8a1&hm=7e204265cbcdeaf96d7b244cd63992c4ef10dc18befbcf2ed39c3a269af14ec0&",
            },
            "footer": {
                "text": f"\n{UID}   v{VERSION}{DEV_RELEASE}",
                "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356025859319926784/5cwgI15.png?ex=67eb10fe&is=67e9bf7e&hm=ab6326a9da1e76125238bf3668acac8ad1e43b24947fc6d878d7b94c8a60ab28&",
            },
            "image": {
                "url": "https://cdn.discordapp.com/attachments/1340508329977446484/1416046388663287808/milestonesBanner.png?ex=68c56b77&is=68c419f7&hm=89b8497b58d232ae0f194df8ab210bf123765ba550321bb8ab1b08a38c0de8c8&"
            },
        },
    ],
    "attachments": [],
}

# Logging already configured via setup_logging in import section.

# Determine ACTIVE_WEBHOOK list based on DEBUG flag
if DEBUG:
    # Use TEST webhooks from config (support comma-separated list)
    ACTIVE_WEBHOOK = [w.strip() for w in config["Webhooks"]["TEST"].split(",") if w.strip()]
    logging.info("DEBUG mode: using TEST webhook(s)")
else:
    # Load production webhooks from external JSON
    try:
        with open(app_path("JSON", "DCord.json"), "r") as f:
            dcord_data = json.load(f)
        ACTIVE_WEBHOOK = dcord_data.get("discord_webhooks_export", [])
        ACTIVE_WEBHOOK = [
            (w.get("url") if isinstance(w, dict) else str(w)).strip()
            for w in ACTIVE_WEBHOOK
            if (isinstance(w, dict) and str(w.get("url", "")).strip()) or (isinstance(w, str) and w.strip())
        ]
        if not ACTIVE_WEBHOOK:
            logging.error("No production webhooks found in DCord.json (key: discord_webhooks_export).")
    except FileNotFoundError:
        logging.error("DCord.json not found. Cannot load production webhooks.")
        ACTIVE_WEBHOOK = []
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse DCord.json: {e}")
        ACTIVE_WEBHOOK = []


def sanitize_and_send_payload(url, source_payload, payload_label):
    payload = deepcopy(source_payload)
    if payload.get("content") is None:
        payload.pop("content", None)

    if "embeds" in payload and isinstance(payload["embeds"], list):
        for i, embed in enumerate(payload["embeds"]):
            if embed:
                sanitized, changes = _sanitize_embed(embed)
                payload["embeds"][i] = sanitized
                if changes:
                    logging.info(f"Sanitized embed {i} in {payload_label} payload: {changes}")

    if not any(payload.get("embeds", [])):
        return False, f"{payload_label} embed empty after sanitization."

    success, response, err = post_webhook(url, json_payload=payload, timeout=10, retries=2)
    return success, err


# Send the embed payload to each webhook
successes = []
for url in ACTIVE_WEBHOOK:
    try:
        # Send first embed (main achievement card)
        success_1, err_1 = sanitize_and_send_payload(url, embed_data, "first")
        if not success_1:
            logging.error(f"Failed to send first embed to {url}. {err_1}")
            successes.append(False)
            continue

        # Add delay to ensure second embed appears after first
        time.sleep(0.5)  # 500ms delay

        # Send second embed (stats/info card)
        success_2, err_2 = sanitize_and_send_payload(url, embed_data_2, "second")
        if success_2:
            logging.info(f"Successfully sent both embeds to Discord webhook: {url}")
            successes.append(True)
        else:
            logging.error(f"Failed to send second embed to {url}. {err_2}")
            successes.append(False)
    except requests.RequestException as e:
        logging.error(f"Network error sending to Discord webhook {url}: {e}")
        successes.append(False)
    except Exception as e:
        logging.error(f"Unexpected error sending to Discord webhook {url}: {e}")
        successes.append(False)

# Optional summary output
if successes:
    logging.info(f"Sent {sum(successes)}/{len(successes)} webhook messages successfully.")
else:
    logging.warning("No webhooks were processed.")
