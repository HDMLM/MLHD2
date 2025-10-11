import pandas as pd
from datetime import datetime, timezone, timedelta
import configparser
import requests
import json
import logging
import os
from logging_config import setup_logging
from icon import TITLE_ICONS
from main import VERSION, DEV_RELEASE

# Read configuration from config.config
config = configparser.ConfigParser()
config.read('config.config')
iconconfig = configparser.ConfigParser()
iconconfig.read('icon.config')

date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

#Constants
DEBUG = config.getboolean('DEBUGGING', 'DEBUG', fallback=False)
setup_logging(DEBUG)

# Set up application data paths 
APP_DATA = os.path.join(os.getenv('LOCALAPPDATA'), 'MLHD2')
if not os.path.exists(APP_DATA):
    os.makedirs(APP_DATA)

EXCEL_FILE_PROD = os.path.join(APP_DATA, 'mission_log.xlsx')
EXCEL_FILE_TEST = os.path.join(APP_DATA, 'mission_log_test.xlsx')
DATE_FORMAT = "%d-%m-%Y %H:%M:%S"

# Read the Excel file
import tkinter as tk
from tkinter import messagebox
import random
import sys
try:
    excel_file = EXCEL_FILE_TEST if DEBUG else EXCEL_FILE_PROD
    df = pd.read_excel(excel_file)
    if df.empty:
        logging.error("Error: Excel file is empty. Please ensure the file contains data.")
        # Show a message box to the user
        root = tk.Tk()
        root.withdraw()
        randint = random.randint(1, 2)
        if randint == 1:
            messagebox.showerror("Export Error", "You've achived nothing! No missions found in the log.")
        else:
            messagebox.showerror("Export Error", "No mission data recorded. Please log at least one mission before exporting.")
        raise ValueError("Excel file is empty.")
except (FileNotFoundError, ValueError) as e:
    logging.error(f"Error: Unable to read Excel file. {e}")
    sys.exit(0)  # Exit the subprocess gracefully and return to main


highest_streak = 0
profile_picture = ""
with open('./JSON/streak_data.json', 'r') as f:
    streak_data = json.load(f)
    # Use "Helldiver" as the key
    highest_streak = streak_data.get("Helldiver", {}).get("highest_streak", 0)
    profile_picture = streak_data.get("Helldiver", {}).get("profile_picture_name", "")

#get total kills
total_kills = df['Kills'].sum()


# Aggregate data for each advancement query

# get total missions
total_missions = len(df)

#get total mission with major order active
total_missions_major_order = df[df['Major Order'] == 1].shape[0]

#get total mission with DSS active
total_missions_dss = df[df['DSS Active'] == 1].shape[0]

total_missions_city = df[df['Mega City'] == 1].shape[0]

# Get count of unique planets visited
total_missions_planets = len(df['Planet'].unique())

total_missions_sectors = len(df['Sector'].unique())

#get total terminid missions
total_terminid_missions = df[df['Enemy Type'] == 'Terminids'].shape[0]

#get total automaton missions
total_automaton_missions = df[df['Enemy Type'] == 'Automatons'].shape[0]

#get total illuminate missions
total_illuminate_missions = df[df['Enemy Type'] == 'Illuminate'].shape[0]

# get total terminid kills
total_terminid_kills = df[df['Enemy Type'] == 'Terminids']['Kills'].sum()

# get total automaton kills
total_automaton_kills = df[df['Enemy Type'] == 'Automatons']['Kills'].sum()

# get total illuminate kills
total_illuminate_kills = df[df['Enemy Type'] == 'Illuminate']['Kills'].sum()

total_kills = df['Kills'].sum()

# get if at least one mission was played on Malevelon Creek
malevelon_creek = df[df['Planet'] == 'Malevelon Creek'].shape[0] > 0

# get if at least on mission was rated Disgracful Conduct
disgraceful_conduct = df[df['Rating'] == 'Disgraceful Conduct'].shape[0] > 0

costly_failure = df[df['Rating'] == 'Costly Failure'].shape[0] > 0

#get if at least one mission was played on Super Earth
super_earth = df[df['Planet'] == 'Super Earth'].shape[0] > 0

# get at least one mission was played on the Cyberstan
cyberstan = df[df['Planet'] == 'Cyberstan'].shape[0] > 0

# get if highest_streak is 30 or more
streak_10 = highest_streak >= 10
streak_20 = highest_streak >= 20
streak_30 = highest_streak >= 30

# Get count of difficulty types
total_1 = df[df['Difficulty'] == '1 - TRIVIAL'].shape[0] > 0
total_2 = df[df['Difficulty'] == '2 - EASY'].shape[0] > 0
total_3 = df[df['Difficulty'] == '3 - MEDIUM'].shape[0] > 0
total_4 = df[df['Difficulty'] == '4 - CHALLENGING'].shape[0] > 0
total_5 = df[df['Difficulty'] == '5 - HARD'].shape[0] > 0
total_6 = df[df['Difficulty'] == '6 - EXTREME'].shape[0] > 0
total_7 = df[df['Difficulty'] == '7 - SUICIDE MISSION'].shape[0] > 0
total_8 = df[df['Difficulty'] == '8 - IMPOSSIBLE'].shape[0] > 0
total_9 = df[df['Difficulty'] == '9 - HELLDIVE'].shape[0] > 0
total_10 = df[df['Difficulty'] == '10 - SUPER HELLDIVE'].shape[0] > 0

# Check if at least one of each difficulty has been completed
all_difficulties = (total_1 and total_2 and total_3 and 
                   total_4 and total_5 and total_6 and
                   total_7 and total_8 and total_9 and 
                   total_10)

# Check for completion of each campaign type
total_liberation = df[df['Mission Category'] == 'Liberation'].shape[0] > 0
total_defense = df[df['Mission Category'] == 'Defense'].shape[0] > 0
total_invasion = df[df['Mission Category'] == 'Invasion'].shape[0] > 0
total_high_priority = df[df['Mission Category'] == 'High-Priority'].shape[0] > 0
total_attrition = df[df['Mission Category'] == 'Attrition'].shape[0] > 0
total_bfse = df[df['Mission Category'] == 'Battle for Super Earth'].shape[0] 

# Check if all campaign types have been completed
all_campaigns = (total_liberation and total_defense and 
                total_invasion and total_high_priority and 
                total_attrition and total_bfse)

# Load biome mapping from json file
with open('./JSON/BiomePlanets.json', 'r') as f:
    biome_mapping = json.load(f)

# Create a set of all unique biomes from the mapping
all_biome_types = set(biome_mapping.values())

# Create dictionary to track if each biome has been visited
biome_visited = {biome: False for biome in all_biome_types}

# For each planet visited in the dataframe, mark its biome as visited
for planet in df['Planet'].unique():
    if planet in biome_mapping:
        biome = biome_mapping[planet]
        biome_visited[biome] = True

# Check if all standard biomes have been visited
# Filter out special biomes like "Scoured", "Black Hole", "Super Earth", etc.
standard_biomes = {
    'Desert Dunes', 'Desert Cliffs', 'Acidic Badlands', 'Rocky Canyons',
    'Moon', 'Volcanic Jungle', 'Deadlands', 'Ethereal Jungle', 
    'Ionic Jungle', 'Icy Glaciers', 'Boneyard', 'Plains', 'Tundra',
    'Scorched Moor', 'Ionic Crimson', 'Basic Swamp', 'Haunted Swamp'
}

all_biomes = all(biome_visited[biome] for biome in standard_biomes)

# Get counts for each mission
mission_counts = df['Mission Type'].value_counts()
# Check if any mission has 100 or more completions
one_mission_100 = any(count >= 100 for count in mission_counts)
# Assign bool values to tracking variables

# Get counts for each planet
planet_counts = df['Planet'].value_counts()
# Check if any planet has 100 or more missions
one_planet_100 = any(count >= 100 for count in planet_counts)
# Assign bool values to tracking variables

# Get counts for each sector
sector_counts = df['Sector'].value_counts()
# Check if any sector has 100 or more missions
one_sector_100 = any(count >= 100 for count in sector_counts)
# Assign bool values to tracking variables

#assign bool values to variables
# Function to get date of nth occurrence
def get_nth_date(df, condition, n):
    try:
        # Filter dataframe by condition and get the nth row's date
        filtered_df = df[condition]
        if len(filtered_df) >= n:
            return filtered_df.iloc[n-1]['Time']
    except:
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
ReliableDiver1_date = get_nth_date(df, df['Major Order'] == 1, 100) if ReliableDiver1 else "Not Obtained"

ReliableDiver2 = total_missions_major_order >= 250
ReliableDiver2_date = get_nth_date(df, df['Major Order'] == 1, 250) if ReliableDiver2 else "Not Obtained"

ReliableDiver3 = total_missions_major_order >= 500
ReliableDiver3_date = get_nth_date(df, df['Major Order'] == 1, 500) if ReliableDiver3 else "Not Obtained"

DSSDiver1 = total_missions_dss >= 100
DSSDiver1_date = get_nth_date(df, df['DSS Active'] == 1, 100) if DSSDiver1 else "Not Obtained"

DSSDiver2 = total_missions_dss >= 250
DSSDiver2_date = get_nth_date(df, df['DSS Active'] == 1, 250) if DSSDiver2 else "Not Obtained"

DSSDiver3 = total_missions_dss >= 500
DSSDiver3_date = get_nth_date(df, df['DSS Active'] == 1, 500) if DSSDiver3 else "Not Obtained"

# For counts of unique planets/sectors, we need cumulative counts
def get_unique_nth_date(df, column, n):
    unique_counts = df[column].groupby(df.index).transform(lambda x: x.nunique())
    if (unique_counts >= n).any():
        return df.loc[unique_counts[unique_counts >= n].index[0], 'Time']
    return "Not Obtained"

# For unique planet visits, need to track cumulative unique counts
def get_unique_planet_milestone_date(df, n):
    # Create a running count of unique planets
    unique_planets = []
    dates = []
    for _, row in df.iterrows():
        planet = row['Planet']
        if planet not in unique_planets:
            unique_planets.append(planet)
            dates.append(row['Time'])
            if len(unique_planets) == n:
                return dates[n-1]
    return "Not Obtained"

def get_unique_sector_milestone_date(df, n):
    # Create a running count of unique sectors
    unique_sectors = []
    dates = []
    for _, row in df.iterrows():
        sector = row['Sector']
        if sector not in unique_sectors:
            unique_sectors.append(sector)
            dates.append(row['Time'])
            if len(unique_sectors) == n:
                return dates[n-1]
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
OutbreakPerfected1_date = get_nth_date(df, df['Enemy Type'] == 'Terminids', 100) if OutbreakPerfected1 else "Not Obtained"

OutbreakPerfected2 = total_terminid_missions >= 250
OutbreakPerfected2_date = get_nth_date(df, df['Enemy Type'] == 'Terminids', 250) if OutbreakPerfected2 else "Not Obtained"

OutbreakPerfected3 = total_terminid_missions >= 500
OutbreakPerfected3_date = get_nth_date(df, df['Enemy Type'] == 'Terminids', 500) if OutbreakPerfected3 else "Not Obtained"

AutomatonPerfected1 = total_automaton_missions >= 100
AutomatonPerfected1_date = get_nth_date(df, df['Enemy Type'] == 'Automatons', 100) if AutomatonPerfected1 else "Not Obtained"

AutomatonPerfected2 = total_automaton_missions >= 250
AutomatonPerfected2_date = get_nth_date(df, df['Enemy Type'] == 'Automatons', 250) if AutomatonPerfected2 else "Not Obtained"

AutomatonPerfected3 = total_automaton_missions >= 500
AutomatonPerfected3_date = get_nth_date(df, df['Enemy Type'] == 'Automatons', 500) if AutomatonPerfected3 else "Not Obtained"

IlluminatePerfected1 = total_illuminate_missions >= 100
IlluminatePerfected1_date = get_nth_date(df, df['Enemy Type'] == 'Illuminate', 100) if IlluminatePerfected1 else "Not Obtained"

IlluminatePerfected2 = total_illuminate_missions >= 250
IlluminatePerfected2_date = get_nth_date(df, df['Enemy Type'] == 'Illuminate', 250) if IlluminatePerfected2 else "Not Obtained"

IlluminatePerfected3 = total_illuminate_missions >= 500
IlluminatePerfected3_date = get_nth_date(df, df['Enemy Type'] == 'Illuminate', 500) if IlluminatePerfected3 else "Not Obtained"

# For kill counts, need to track cumulative sums
def get_kill_milestone_date(df, enemy_type, threshold):
    enemy_df = df[df['Enemy Type'] == enemy_type].copy()
    enemy_df['cumsum'] = enemy_df['Kills'].cumsum()
    if (enemy_df['cumsum'] >= threshold).any():
        return enemy_df.loc[enemy_df['cumsum'] >= threshold].iloc[0]['Time']
    return "Not Obtained"

TerminidHunter1 = total_terminid_kills >= 10000
TerminidHunter1_date = get_kill_milestone_date(df, 'Terminids', 10000) if TerminidHunter1 else "Not Obtained"

TerminidHunter2 = total_terminid_kills >= 25000
TerminidHunter2_date = get_kill_milestone_date(df, 'Terminids', 25000) if TerminidHunter2 else "Not Obtained"

TerminidHunter3 = total_terminid_kills >= 50000
TerminidHunter3_date = get_kill_milestone_date(df, 'Terminids', 50000) if TerminidHunter3 else "Not Obtained"

AutomatonHunter1 = total_automaton_kills >= 10000
AutomatonHunter1_date = get_kill_milestone_date(df, 'Automatons', 10000) if AutomatonHunter1 else "Not Obtained"

AutomatonHunter2 = total_automaton_kills >= 25000
AutomatonHunter2_date = get_kill_milestone_date(df, 'Automatons', 25000) if AutomatonHunter2 else "Not Obtained"

AutomatonHunter3 = total_automaton_kills >= 50000
AutomatonHunter3_date = get_kill_milestone_date(df, 'Automatons', 50000) if AutomatonHunter3 else "Not Obtained"

IlluminateHunter1 = total_illuminate_kills >= 10000
IlluminateHunter1_date = get_kill_milestone_date(df, 'Illuminate', 10000) if IlluminateHunter1 else "Not Obtained"

IlluminateHunter2 = total_illuminate_kills >= 25000
IlluminateHunter2_date = get_kill_milestone_date(df, 'Illuminate', 25000) if IlluminateHunter2 else "Not Obtained"

IlluminateHunter3 = total_illuminate_kills >= 50000
IlluminateHunter3_date = get_kill_milestone_date(df, 'Illuminate', 50000) if IlluminateHunter3 else "Not Obtained"

# Streak achievements already tracked externally
Streak10 = streak_10
Streak10_date = df[df['Streak'] >= 10].iloc[0]['Time'] if not df[df['Streak'] >= 10].empty else "Not Obtained"
Streak20 = streak_20
Streak20_date = df[df['Streak'] >= 20].iloc[0]['Time'] if not df[df['Streak'] >= 20].empty else "Not Obtained"
Streak30 = streak_30
Streak30_date = df[df['Streak'] >= 30].iloc[0]['Time'] if not df[df['Streak'] >= 30].empty else "Not Obtained"

# Special locations/achievements
MalevelonCreek = malevelon_creek
MalevelonCreek_date = df[df['Planet'] == 'Malevelon Creek'].iloc[0]['Time'] if malevelon_creek else "Not Obtained"

SuperEarth = super_earth
SuperEarth_date = df[df['Planet'] == 'Super Earth'].iloc[0]['Time'] if super_earth else "Not Obtained"

Cyberstan = cyberstan
Cyberstan_date = df[df['Planet'] == 'Cyberstan'].iloc[0]['Time'] if cyberstan else "Not Obtained"

# Milestone achievements
CmdFavourite4 = total_missions >= 1000
CmdFavourite4_date = get_nth_date(df, pd.Series([True] * len(df)), 1000) if CmdFavourite4 else "Not Obtained"

ReliableDiver4 = total_missions_major_order >= 1000
ReliableDiver4_date = get_nth_date(df, df['Major Order'] == 1, 1000) if ReliableDiver4 else "Not Obtained"

DSSDiver4 = total_missions_dss >= 1000
DSSDiver4_date = get_nth_date(df, df['DSS Active'] == 1, 1000) if DSSDiver4 else "Not Obtained"

CityDiver4 = total_missions_city >= 1000
CityDiver4_date = get_nth_date(df, df['Mega City'] == 1, 1000) if CityDiver4 else "Not Obtained"

OutbreakPerfected4 = total_terminid_missions >= 1000
OutbreakPerfected4_date = get_nth_date(df, df['Enemy Type'] == 'Terminids', 1000) if OutbreakPerfected4 else "Not Obtained"

AutomatonPerfected4 = total_automaton_missions >= 1000
AutomatonPerfected4_date = get_nth_date(df, df['Enemy Type'] == 'Automatons', 1000) if AutomatonPerfected4 else "Not Obtained"

IlluminatePerfected4 = total_illuminate_missions >= 1000
IlluminatePerfected4_date = get_nth_date(df, df['Enemy Type'] == 'Illuminate', 1000) if IlluminatePerfected4 else "Not Obtained"

TerminidHunter4 = total_terminid_kills >= 100000
TerminidHunter4_date = get_kill_milestone_date(df, 'Terminids', 100000) if TerminidHunter4 else "Not Obtained"

AutomatonHunter4 = total_automaton_kills >= 100000
AutomatonHunter4_date = get_kill_milestone_date(df, 'Automatons', 100000) if AutomatonHunter4 else "Not Obtained"

IlluminateHunter4 = total_illuminate_kills >= 100000
IlluminateHunter4_date = get_kill_milestone_date(df, 'Illuminate', 100000) if IlluminateHunter4 else "Not Obtained"

# For total kills milestone
def get_total_kills_date(df, threshold):
    df_copy = df.copy()
    df_copy['cumsum'] = df_copy['Kills'].cumsum()
    if (df_copy['cumsum'] >= threshold).any():
        return df_copy.loc[df_copy['cumsum'] >= threshold].iloc[0]['Time']
    return "Not Obtained"

SuperHunter = total_kills >= 1000000
SuperHunter_date = get_total_kills_date(df, 1000000) if SuperHunter else "Not Obtained"

# Composite achievements
# Get the completion date for EveryAchievement - find latest date among all requirements
EveryAchievement = total_missions >= 500 and total_missions_major_order >= 500 and total_missions_dss >= 500 and total_missions_planets >= 100 and total_missions_sectors >= 45

# Get dates for all requirements
achievement_dates = [
    get_nth_date(df, pd.Series([True] * len(df)), 500) if total_missions >= 500 else None,
    get_nth_date(df, df['Major Order'] == 1, 500) if total_missions_major_order >= 500 else None, 
    get_nth_date(df, df['DSS Active'] == 1, 500) if total_missions_dss >= 500 else None,
    get_unique_planet_milestone_date(df, 100) if total_missions_planets >= 100 else None,
    get_unique_sector_milestone_date(df, 45) if total_missions_sectors >= 45 else None
]

# Filter out None and "Not Obtained" values
valid_dates = [d for d in achievement_dates if d and d != "Not Obtained"]

# Set the date to the most recent completion date if all requirements are met
EveryAchievement_date = max(valid_dates) if EveryAchievement and valid_dates else "Not Obtained"
# Get the completion date for EveryChallenge - find latest date among all challenge requirements 
EveryChallenge = total_terminid_missions >= 500 and total_automaton_missions >= 500 and total_illuminate_missions >= 500 and total_terminid_kills >= 50000 and total_automaton_kills >= 50000 and total_illuminate_kills >= 50000 and streak_30

# Get dates for all challenge requirements
challenge_dates = [
    get_nth_date(df, df['Enemy Type'] == 'Terminids', 500) if total_terminid_missions >= 500 else None,
    get_nth_date(df, df['Enemy Type'] == 'Automatons', 500) if total_automaton_missions >= 500 else None, 
    get_nth_date(df, df['Enemy Type'] == 'Illuminate', 500) if total_illuminate_missions >= 500 else None,
    get_kill_milestone_date(df, 'Terminids', 50000) if total_terminid_kills >= 50000 else None,
    get_kill_milestone_date(df, 'Automatons', 50000) if total_automaton_kills >= 50000 else None,
    get_kill_milestone_date(df, 'Illuminate', 50000) if total_illuminate_kills >= 50000 else None,
    df[df['Streak'] >= 30].iloc[0]['Time'] if not df[df['Streak'] >= 30].empty else None
]

# Filter out None and "Not Obtained" values
valid_challenge_dates = [d for d in challenge_dates if d and d != "Not Obtained"]

# Set the date to the most recent completion date if all requirements are met
EveryChallenge_date = max(valid_challenge_dates) if EveryChallenge and valid_challenge_dates else "Not Obtained"
AllDifficulties = all_difficulties
# Get the latest date when all difficulty types were completed
difficulty_completion_dates = []
if AllDifficulties:
    for difficulty in ['1 - TRIVIAL', '2 - EASY', '3 - MEDIUM', '4 - CHALLENGING', '5 - HARD', 
                      '6 - EXTREME', '7 - SUICIDE MISSION', '8 - IMPOSSIBLE', '9 - HELLDIVE', '10 - SUPER HELLDIVE']:
        if not df[df['Difficulty'] == difficulty].empty:
            difficulty_completion_dates.append(df[df['Difficulty'] == difficulty].iloc[0]['Time'])
    AllDifficulties_date = max(difficulty_completion_dates) if difficulty_completion_dates else "Not Obtained"
else:
    AllDifficulties_date = "Not Obtained"

AllCampaigns = all_campaigns
# Get the latest date when all campaign types were completed
campaign_completion_dates = []
if AllCampaigns:
    for campaign in ['Liberation', 'Defense', 'Invasion', 'High-Priority', 'Attrition', 'Battle for Super Earth']:
        if not df[df['Mission Category'] == campaign].empty:
            campaign_completion_dates.append(df[df['Mission Category'] == campaign].iloc[0]['Time'])
    AllCampaigns_date = max(campaign_completion_dates) if campaign_completion_dates else "Not Obtained"
else:
    AllCampaigns_date = "Not Obtained"

AllBiomes = all_biomes
# Get the latest date when all standard biomes were completed
biome_completion_dates = []
if AllBiomes:
    for planet in df['Planet'].unique():
        if planet in biome_mapping:
            biome = biome_mapping[planet]
            if biome in standard_biomes:
                planet_first_visit = df[df['Planet'] == planet].iloc[0]['Time']
                biome_completion_dates.append(planet_first_visit)
    AllBiomes_date = max(biome_completion_dates) if biome_completion_dates else "Not Obtained"
else:
    AllBiomes_date = "Not Obtained"
DisgracefulConduct = disgraceful_conduct
DisgracefulConduct_date = df[df['Rating'] == 'Disgraceful Conduct'].iloc[0]['Time'] if disgraceful_conduct else "Not Obtained"
CostlyFailure = costly_failure
CostlyFailure_date = df[df['Rating'] == 'Costly Failure'].iloc[0]['Time'] if costly_failure else "Not Obtained"
EveryTriumph = malevelon_creek and super_earth and cyberstan and all_difficulties and all_campaigns and all_biomes and disgraceful_conduct and costly_failure

# Get dates for all triumph requirements
triumph_dates = [
    df[df['Planet'] == 'Malevelon Creek'].iloc[0]['Time'] if malevelon_creek else None,
    df[df['Planet'] == 'Super Earth'].iloc[0]['Time'] if super_earth else None,
    df[df['Planet'] == 'Cyberstan'].iloc[0]['Time'] if cyberstan else None,
    AllDifficulties_date if all_difficulties and AllDifficulties_date != "Not Obtained" else None,
    AllCampaigns_date if all_campaigns and AllCampaigns_date != "Not Obtained" else None,
    AllBiomes_date if all_biomes and AllBiomes_date != "Not Obtained" else None,
    df[df['Rating'] == 'Disgraceful Conduct'].iloc[0]['Time'] if disgraceful_conduct else None,
    df[df['Rating'] == 'Costly Failure'].iloc[0]['Time'] if costly_failure else None
]

# Filter out None and "Not Obtained" values
valid_triumph_dates = [d for d in triumph_dates if d and d != "Not Obtained"]

# Set the date to the most recent completion date if all requirements are met
EveryTriumph_date = max(valid_triumph_dates) if EveryTriumph and valid_triumph_dates else "Not Obtained"
# Get date when first mission type reached 100 completions
def get_first_mission_100_date(df):
    mission_counts = df.groupby(['Mission Type', 'Time']).size().reset_index(name='count')
    mission_counts['cumsum'] = mission_counts.groupby('Mission Type')['count'].cumsum()
    missions_100 = mission_counts[mission_counts['cumsum'] >= 100]
    if not missions_100.empty:
        return missions_100.iloc[0]['Time']
    return "Not Obtained"

OneMission = one_mission_100
OneMission_date = get_first_mission_100_date(df) if OneMission else "Not Obtained"
# Function to get date when first planet reached 100 missions
def get_first_planet_100_date(df):
    planet_counts = df.groupby(['Planet', 'Time']).size().reset_index(name='count')
    planet_counts['cumsum'] = planet_counts.groupby('Planet')['count'].cumsum()
    planets_100 = planet_counts[planet_counts['cumsum'] >= 100]
    if not planets_100.empty:
        return planets_100.iloc[0]['Time']
    return "Not Obtained"

OnePlanet = one_planet_100
OnePlanet_date = get_first_planet_100_date(df) if OnePlanet else "Not Obtained"
# Get date when first sector reached 100 missions
def get_first_sector_100_date(df):
    sector_counts = df.groupby(['Sector', 'Time']).size().reset_index(name='count')
    sector_counts['cumsum'] = sector_counts.groupby('Sector')['count'].cumsum()
    sectors_100 = sector_counts[sector_counts['cumsum'] >= 100]
    if not sectors_100.empty:
        return sectors_100.iloc[0]['Time']
    return "Not Obtained"

OneSector = one_sector_100
OneSector_date = get_first_sector_100_date(df) if OneSector else "Not Obtained"
EveryMilestone = total_missions >= 1000 and total_missions_major_order >= 1000 and total_missions_dss >= 1000 and total_missions_city >= 1000 and total_terminid_missions >= 1000 and total_automaton_missions >= 1000 and total_illuminate_missions >= 1000 and total_terminid_kills >= 100000 and total_automaton_kills >= 100000 and total_illuminate_kills >= 100000 and total_kills >= 1000000
# Get dates for all milestone requirements
milestone_dates = [
    get_nth_date(df, pd.Series([True] * len(df)), 1000) if total_missions >= 1000 else None,
    get_nth_date(df, df['Major Order'] == 1, 1000) if total_missions_major_order >= 1000 else None,
    get_nth_date(df, df['DSS Active'] == 1, 1000) if total_missions_dss >= 1000 else None,
    get_nth_date(df, df['Mega City'] == 1, 1000) if total_missions_city >= 1000 else None,
    get_nth_date(df, df['Enemy Type'] == 'Terminids', 1000) if total_terminid_missions >= 1000 else None,
    get_nth_date(df, df['Enemy Type'] == 'Automatons', 1000) if total_automaton_missions >= 1000 else None,
    get_nth_date(df, df['Enemy Type'] == 'Illuminate', 1000) if total_illuminate_missions >= 1000 else None,
    get_kill_milestone_date(df, 'Terminids', 100000) if total_terminid_kills >= 100000 else None,
    get_kill_milestone_date(df, 'Automatons', 100000) if total_automaton_kills >= 100000 else None,
    get_kill_milestone_date(df, 'Illuminate', 100000) if total_illuminate_kills >= 100000 else None,
    get_total_kills_date(df, 1000000) if total_kills >= 1000000 else None
]

# Filter out None and "Not Obtained" values
valid_milestone_dates = [d for d in milestone_dates if d and d != "Not Obtained"]

# Set the date to the most recent completion date if all requirements are met
EveryMilestone_date = max(valid_milestone_dates) if EveryMilestone and valid_milestone_dates else "Not Obtained"

OneHundredPercent = EveryAchievement and EveryChallenge and EveryTriumph and EveryMilestone
# Get 100% completion date
if OneHundredPercent:
    dates_to_check = [
        EveryAchievement_date,
        EveryChallenge_date, 
        EveryTriumph_date,
        EveryMilestone_date
    ]
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
    "OneHundredPercent": OneHundredPercent
}

# Calculate total achievements completed
total_achievements = len(achievements)
completed_achievements = sum(1 for value in achievements.values() if value)
achievement_percentage = round((completed_achievements / total_achievements) * 100, 1)

# Add to achievements dictionary
achievements['completion_percentage'] = achievement_percentage

if DEBUG:
    webhook_urls = [config['Webhooks']['TEST']] # Use the webhook URL from the config for debugging
else:
    # Load webhook URLs from DCord.json
    with open('./JSON/DCord.json', 'r') as f:
        discord_data = json.load(f)
        webhook_urls = discord_data.get('discord_webhooks', [])
        webhook_urls = [
            (w.get('url') if isinstance(w, dict) else str(w)).strip()
            for w in webhook_urls
            if (isinstance(w, dict) and str(w.get('url','')).strip()) or (isinstance(w, str) and w.strip())
        ]

# Define achievement metadata for messages and titles
ACHIEVEMENT_DEFS = {
    "CmdFavourite1": {
        "message": ("Log 100 Missions", "HINT: You have the strength and the courage... to be free"),
        "title": (
            "<a:bro:1414376629190262965> **HIGH COMMAND'S FAVOURITE I**",
            "<:locked1:1416039237106663455> **~~HIGH COMMAND'S FAVOURITE I~~**"
        )
    },
    "CmdFavourite2": {
        "message": ("Log 250 Missions", "HINT: You have the strength and the courage... to be free"),
        "title": (
            "<a:sil:1414376620378034196> **HIGH COMMAND'S FAVOURITE II**",
            "<:locked1:1416039237106663455> **~~HIGH COMMAND'S FAVOURITE II~~**"
        )
    },
    "CmdFavourite3": {
        "message": ("Log 500 Missions", "HINT: You have the strength and the courage... to be free"),
        "title": (
            "<a:gol:1414376388516909076> **HIGH COMMAND'S FAVOURITE III**",
            "<:locked1:1416039237106663455> **~~HIGH COMMAND'S FAVOURITE III~~**"
        )
    },
    "ReliableDiver1": {
        "message": ("Log 100 Major Order Missions", "HINT: You're one to obey orders"),
        "title": (
            "<a:bro:1414376629190262965> **RELIABLE DIVER I**",
            "<:locked1:1416039237106663455> **~~RELIABLE DIVER I~~**"
        )
    },
    "ReliableDiver2": {
        "message": ("Log 250 Major Order Missions", "HINT: You're one to obey orders"),
        "title": (
            "<a:sil:1414376620378034196> **RELIABLE DIVER II**",
            "<:locked1:1416039237106663455> **~~RELIABLE DIVER II~~**"
        )
    },
    "ReliableDiver3": {
        "message": ("Log 500 Major Order Missions", "HINT: You're one to obey orders"),
        "title": (
            "<a:gol:1414376388516909076> **RELIABLE DIVER III**",
            "<:locked1:1416039237106663455> **~~RELIABLE DIVER III~~**"
        )
    },
    "DSSDiver1": {
        "message": ("Log 100 Missions with the Democracy Space Station in Orbit", "HINT: You like a good bit of support"),
        "title": (
            "<a:bro:1414376629190262965> **I <3 DSS I**",
            "<:locked1:1416039237106663455> **~~I <3 DSS I~~**"
        )
    },
    "DSSDiver2": {
        "message": ("Log 250 Missions with the Democracy Space Station in Orbit", "HINT: You like a good bit of support"),
        "title": (
            "<a:sil:1414376620378034196> **I <3 DSS II**",
            "<:locked1:1416039237106663455> **~~I <3 DSS II~~**"
        )
    },
    "DSSDiver3": {
        "message": ("Log 500 Missions with the Democracy Space Station in Orbit", "HINT: You like a good bit of support"),
        "title": (
            "<a:gol:1414376388516909076> **I <3 DSS III**",
            "<:locked1:1416039237106663455> **~~I <3 DSS III~~**"
        )
    },
    "PlanetDiver1": {
        "message": ("Log Missions on 25 Different Planets", "HINT: You leave no stone unturned"),
        "title": (
            "<a:bro:1414376629190262965> **THE LONG MARCH OF LIBERTY I**",
            "<:locked1:1416039237106663455> **~~THE LONG MARCH OF LIBERTY I~~**"
        )
    },
    "PlanetDiver2": {
        "message": ("Log Missions on 50 Different Planets", "HINT: You leave no stone unturned"),
        "title": (
            "<a:sil:1414376620378034196> **THE LONG MARCH OF LIBERTY II**",
            "<:locked1:1416039237106663455> **~~THE LONG MARCH OF LIBERTY II~~**"
        )
    },
    "PlanetDiver3": {
        "message": ("Log Missions on 100 Different Planets", "HINT: You leave no stone unturned"),
        "title": (
            "<a:gol:1414376388516909076> **THE LONG MARCH OF LIBERTY III**",
            "<:locked1:1416039237106663455> **~~THE LONG MARCH OF LIBERTY III~~**"
        )
    },
    "SectorDiver1": {
        "message": ("Log Missions on 15 Different Sectors", "HINT: You like to cover all bases"),
        "title": (
            "<a:bro:1414376629190262965> **MASTER OF THE MAP I**",
            "<:locked1:1416039237106663455> **~~MASTER OF THE MAP I~~**"
        )
    },
    "SectorDiver2": {
        "message": ("Log Missions on 30 Different Sectors", "HINT: You like to cover all bases"),
        "title": (
            "<a:sil:1414376620378034196> **MASTER OF THE MAP II**",
            "<:locked1:1416039237106663455> **~~MASTER OF THE MAP II~~**"
        )
    },
    "SectorDiver3": {
        "message": ("Log Missions on 45 Different Sectors", "HINT: You like to cover all bases"),
        "title": (
            "<a:gol:1414376388516909076> **MASTER OF THE MAP III**",
            "<:locked1:1416039237106663455> **~~MASTER OF THE MAP III~~**"
        )
    },
    "EveryAchievement": {
        "message": ("Complete Every Achievement", "HINT: You love a good hunt"),
        "title": (
            "<a:gol:1414376388516909076> **ACHIEVEMENT HUNTER**",
            "<:locked1:1416039237106663455> **~~ACHIEVEMENT HUNTER~~**"
        )
    },
    "OutbreakPerfected1": {
        "message": ("Log 100 Terminid Missions", "HINT: You're rather familiar with E-710"),
        "title": (
            "<a:bro1:1415834803256688732> **OUTBREAK PERFECTED I**",
            "<:locked2:1416039336520187975> **~~OUTBREAK PERFECTED I~~**"
        )
    },
    "OutbreakPerfected2": {
        "message": ("Log 250 Terminid Missions", "HINT: You're rather familiar with E-710"),
        "title": (
            "<a:sil1:1415835160431300660> **OUTBREAK PERFECTED II**",
            "<:locked2:1416039336520187975> **~~OUTBREAK PERFECTED II~~**"
        )
    },
    "OutbreakPerfected3": {
        "message": ("Log 500 Terminid Missions", "HINT: You're rather familiar with E-710"),
        "title": (
            "<a:EasyAwardBaftaMP2025:1363545915352289371> **OUTBREAK PERFECTED III**",
            "<:locked2:1416039336520187975> **~~OUTBREAK PERFECTED III~~**"
        )
    },
    "AutomatonPerfected1": {
        "message": ("Log 100 Automaton Missions", "HINT: You're rather familiar with losing access to your Stratagems"),
        "title": (
            "<a:bro1:1415834803256688732> **INCURSION DEVASTATED I**",
            "<:locked2:1416039336520187975> **~~INCURSION DEVASTATED I~~**"
        )
    },
    "AutomatonPerfected2": {
        "message": ("Log 250 Automaton Missions", "HINT: You're rather familiar with losing access to your Stratagems"),
        "title": (
            "<a:sil1:1415835160431300660> **INCURSION DEVASTATED II**",
            "<:locked2:1416039336520187975> **~~INCURSION DEVASTATED II~~**"
        )
    },
    "AutomatonPerfected3": {
        "message": ("Log 500 Automaton Missions", "HINT: You're rather familiar with losing access to your Stratagems"),
        "title": (
            "<a:EasyAwardBaftaMP2025:1363545915352289371> **INCURSION DEVASTATED III**",
            "<:locked2:1416039336520187975> **~~INCURSION DEVASTATED III~~**"
        )
    },
    "IlluminatePerfected1": {
        "message": ("Log 100 Illuminate Missions", "HINT: You're rather familiar with their autocratic intentions"),
        "title": (
            "<a:bro1:1415834803256688732> **INVASION ABOLISHED I**",
            "<:locked2:1416039336520187975> **~~INVASION ABOLISHED I~~**"
        )
    },
    "IlluminatePerfected2": {
        "message": ("Log 250 Illuminate Missions", "HINT: You're rather familiar with their autocratic intentions"),
        "title": (
            "<a:sil1:1415835160431300660> **INVASION ABOLISHED II**",
            "<:locked2:1416039336520187975> **~~INVASION ABOLISHED II~~**"
        )
    },
    "IlluminatePerfected3": {
        "message": ("Log 500 Illuminate Missions", "HINT: You're rather familiar with their autocratic intentions"),
        "title": (
            "<a:EasyAwardBaftaMP2025:1363545915352289371> **INVASION ABOLISHED III**",
            "<:locked2:1416039336520187975> **~~INVASION ABOLISHED III~~**"
        )
    },
    "TerminidHunter1": {
        "message": ("Log 10,000 Kills against the Terminids", "HINT: You douse yourself in E-710"),
        "title": (
            "<a:bro1:1415834803256688732> **BUG STOMPER I**",
            "<:locked2:1416039336520187975> **~~BUG STOMPER I~~**"
        )
    },
    "TerminidHunter2": {
        "message": ("Log 25,000 Kills against the Terminids", "HINT: You douse yourself in E-710"),
        "title": (
            "<a:sil1:1415835160431300660> **BUG STOMPER II**",
            "<:locked2:1416039336520187975> **~~BUG STOMPER II~~**"
        )
    },
    "TerminidHunter3": {
        "message": ("Log 50,000 Kills against the Terminids", "HINT: You douse yourself in E-710"),
        "title": (
            "<a:EasyAwardBaftaMP2025:1363545915352289371> **BUG STOMPER III**",
            "<:locked2:1416039336520187975> **~~BUG STOMPER III~~**"
        )
    },
    "AutomatonHunter1": {
        "message": ("Log 10,000 Kills against the Automatons", "HINT: You make things out of scrap metal in your spare time"),
        "title": (
            "<a:bro1:1415834803256688732> **CLANKER SCRAPPER I**",
            "<:locked2:1416039336520187975> **~~CLANKER SCRAPPER I~~**"
        )
    },
    "AutomatonHunter2": {
        "message": ("Log 25,000 Kills against the Automatons", "HINT: You make things out of scrap metal in your spare time"),
        "title": (
            "<a:sil1:1415835160431300660> **CLANKER SCRAPPER II**",
            "<:locked2:1416039336520187975> **~~CLANKER SCRAPPER II~~**"
        )
    },
    "AutomatonHunter3": {
        "message": ("Log 50,000 Kills against the Automatons", "HINT: You make things out of scrap metal in your spare time"),
        "title": (
            "<a:EasyAwardBaftaMP2025:1363545915352289371> **CLANKER SCRAPPER III**",
            "<:locked2:1416039336520187975> **~~CLANKER SCRAPPER III~~**"
        )
    },
    "IlluminateHunter1": {
        "message": ("Log 10,000 Kills against the Illuminate", "HINT: You single handedly make an effort of wiping them out of the Second Galactic War"),
        "title": (
            "<a:bro1:1415834803256688732> **SQUID SEVERER I**",
            "<:locked2:1416039336520187975> **~~SQUID SEVERER I~~**"
        )
    },
    "IlluminateHunter2": {
        "message": ("Log 25,000 Kills against the Illuminate", "HINT: You single handedly make an effort of wiping them out of the Second Galactic War"),
        "title": (
            "<a:sil1:1415835160431300660> **SQUID SEVERER II**",
            "<:locked2:1416039336520187975> **~~SQUID SEVERER II~~**"
        )
    },
    "IlluminateHunter3": {
        "message": ("Log 50,000 Kills against the Illuminate", "HINT: You single handedly make an effort of wiping them out of the Second Galactic War"),
        "title": (
            "<a:EasyAwardBaftaMP2025:1363545915352289371> **SQUID SEVERER III**",
            "<:locked2:1416039336520187975> **~~SQUID SEVERER III~~**"
        )
    },
    "Streak10": {
        "message": ("Reach a Streak of 10", "HINT: You'll need to take some annual leave after this... seriously... Democracy Applauds You!"),
        "title": (
            "<a:bro1:1415834803256688732> **INFLAMMABLE I**",
            "<:locked2:1416039336520187975> **~~INFLAMMABLE I~~**"
        )
    },
    "Streak20": {
        "message": ("Reach a Streak of 20", "HINT: You'll need to take some annual leave after this... seriously... Democracy Applauds You!"),
        "title": (
            "<a:sil1:1415835160431300660> **INFLAMMABLE II**",
            "<:locked2:1416039336520187975> **~~INFLAMMABLE II~~**"
        )
    },
    "Streak30": {
        "message": ("Reach a Streak of 30", "HINT: You'll need to take some annual leave after this... seriously... Democracy Applauds You!"),
        "title": (
            "<a:EasyAwardBaftaMP2025:1363545915352289371> **INFLAMMABLE III**",
            "<:locked2:1416039336520187975> **~~INFLAMMABLE III~~**"
        )
    },
    "EveryChallenge": {
        "message": ("Complete Every Challenge", "HINT: You love a good challenge"),
        "title": (
            "<a:EasyAwardBaftaMP2025:1363545915352289371> **A NEW CHALLENGER APPROACHES**",
            "<:locked2:1416039336520187975> **~~A NEW CHALLENGER APPROACHES~~**"
        )
    },
    "MalevelonCreek": {
        "message": ("Serve on Malevelon Creek", "HINT: You remember..."),
        "title": (
            "<a:EasyAwardBaftaMusic2025:1359268029850058974> **NEVER FORGET**",
            "<:locked3:1416039337841262633> **~~NEVER FORGET~~**"
        )
    },
    "SuperEarth": {
        "message": ("Serve on Super Earth", "HINT: You feel very welcome"),
        "title": (
            "<a:EasyAwardBaftaMusic2025:1359268029850058974> **HOME SUPER HOME**",
            "<:locked3:1416039337841262633> **~~HOME SUPER HOME~~**"
        )
    },
    "Cyberstan": {
        "message": ("Serve on an Enemy Homeworld", "HINT: You don't feel very welcome... like they have a choice"),
        "title": (
            "<a:EasyAwardBaftaMusic2025:1359268029850058974> **ON THE ENEMY'S DOORSTEP**",
            "<:locked3:1416039337841262633> **~~ON THE ENEMY'S DOORSTEP~~**"
        )
    },
    "AllDifficulties": {
        "message": ("Complete 1 of Every Difficulty Type", "HINT: You don't care how difficult the task, as long as democracy is spread"),
        "title": (
            "<a:EasyAwardBaftaMusic2025:1359268029850058974> **JACK OF ALL TRADES**",
            "<:locked3:1416039337841262633> **~~JACK OF ALL TRADES~~**"
        )
    },
    "AllCampaigns": {
        "message": ("Complete 1 of Every Campaign Type", "HINT: You have a wide range of choice, and you picked every single one"),
        "title": (
            "<a:EasyAwardBaftaMusic2025:1359268029850058974> **QUEEN OF ALL TRADES**",
            "<:locked3:1416039337841262633> **~~QUEEN OF ALL TRADES~~**"
        )
    },
    "AllBiomes": {
        "message": ("Complete 1 of Every Biome Type", "HINT: You are well versed with every terrain, every parameter, every storm"),
        "title": (
            "<a:EasyAwardBaftaMusic2025:1359268029850058974> **KING OF ALL TRADES**",
            "<:locked3:1416039337841262633> **~~KING OF ALL TRADES~~**"
        )
    },
    "DisgracefulConduct": {
        "message": ("Get a Performance Rating of Disgraceful Conduct on a Mission", "HINT: You... why?"),
        "title": (
            "<a:EasyAwardBaftaMusic2025:1359268029850058974> **you got this on purpose...**",
            "<:locked3:1416039337841262633> **~~you got this on purpose...~~**"
        )
    },
    "CostlyFailure": {
        "message": ("Get a Performance Rating of Costly Failure on a Mission", "HINT: You... okay but seriously why?"),
        "title": (
            "<a:EasyAwardBaftaMusic2025:1359268029850058974> **okay I was serious before but... you really did get this on purpose...**",
            "<:locked3:1416039337841262633> **~~okay I was serious before but... you really did get this on purpose...~~**"
        )
    },
    "EveryTriumph": {
        "message": ("Complete Every Triumph", "HINT: You alone are the triumphant one"),
        "title": (
            "<a:EasyAwardBaftaMusic2025:1359268029850058974> **A TRIUMPHANT RETURN**",
            "<:locked3:1416039337841262633> **~~A TRIUMPHANT RETURN~~**"
        )
    },
    "OneMission": {
        "message": ("Log 100 Missions of 1 Mission Type", "HINT: You don't even need teammates for this mission"),
        "title": (
            "<a:EasyAwardEggHunt2025:1363541656447488200> **LET ME SOLO THIS**",
            "<:locked4:1416039238654361600> **~~LET ME SOLO THIS~~**"
        )
    },
    "OnePlanet": {
        "message": ("Log 100 Missions of 1 Planet Type", "HINT: You must really like this planet"),
        "title": (
            "<a:EasyAwardEggHunt2025:1363541656447488200> **NEW HOMEWORLD**",
            "<:locked4:1416039238654361600> **~~NEW HOMEWORLD~~**"
        )
    },
    "OneSector": {
        "message": ("Log 100 Missions of 1 Sector Type", "HINT: Your name echoes from the neighbouring planets"),
        "title": (
            "<a:EasyAwardEggHunt2025:1363541656447488200> **THEY FEAR YOUR NAME**",
            "<:locked4:1416039238654361600> **~~THEY FEAR YOUR NAME~~**"
        )
    },
    "CmdFavourite4": {
        "message": ("Log 1000 Missions", "HINT: You have earned your rightful place on Super Earth, and served with purpose"),
        "title": (
            "<a:EasyAwardEggHunt2025:1363541656447488200> **HELLDIVERS TO HELLPODS**",
            "<:locked4:1416039238654361600> **~~HELLDIVERS TO HELLPODS~~**"
        )
    },
    "ReliableDiver4": {
        "message": ("Log 1000 Major Order Missions", "HINT: You're always there, when they call your name"),
        "title": (
            "<a:EasyAwardEggHunt2025:1363541656447488200> **AT EASE SUPER PRIVATE**",
            "<:locked4:1416039238654361600> **~~AT EASE SUPER PRIVATE~~**"
        )
    },
    "DSSDiver4": {
        "message": ("Log 1000 Missions with the Democracy Space Station in Orbit", "HINT: You are one with democracy"),
        "title": (
            "<a:EasyAwardEggHunt2025:1363541656447488200> **I REALLY <3 DSS**",
            "<:locked4:1416039238654361600> **~~I REALLY <3 DSS~~**"
        )
    },
    "OutbreakPerfected4": {
        "message": ("Log 1000 Terminid Missions", "HINT: You're way too familiar with E-710"),
        "title": (
            "<a:EasyAwardEggHunt2025:1363541656447488200> **FOREVER INHALING GLOOM**",
            "<:locked4:1416039238654361600> **~~FOREVER INHALING GLOOM~~**"
        )
    },
    "AutomatonPerfected4": {
        "message": ("Log 1000 Automaton Missions", "HINT: You're way too familiar with losing access to your Stratagems"),
        "title": (
            "<a:EasyAwardEggHunt2025:1363541656447488200> **HEARING BINARY IN THE BUSHES**",
            "<:locked4:1416039238654361600> **~~HEARING BINARY IN THE BUSHES~~**"
        )
    },
    "IlluminatePerfected4": {
        "message": ("Log 1000 Illuminates Missions", "HINT: You're way too familiar with their autocratic intentions"),
        "title": (
            "<a:EasyAwardEggHunt2025:1363541656447488200> **RID OF THY SQU'ITH**",
            "<:locked4:1416039238654361600> **~~RID OF THY SQU'ITH~~**"
        )
    },
    "TerminidHunter4": {
        "message": ("Kill 100,000 Terminids", "HINT: You can never have enough E-710"),
        "title": (
            "<a:EasyAwardEggHunt2025:1363541656447488200> **DID SOMEONE SAY OIL?**",
            "<:locked4:1416039238654361600> **~~DID SOMEONE SAY OIL?~~**"
        )
    },
    "AutomatonHunter4": {
        "message": ("Kill 100,000 Automatons", "HINT: You can't pick the two apart, you just know these traitors must succumb at the hands of managed democracy"),
        "title": (
            "<a:EasyAwardEggHunt2025:1363541656447488200> **CYBORG OR AUTOMATON?**",
            "<:locked4:1416039238654361600> **~~CYBORG OR AUTOMATON?~~**"
        )
    },
    "IlluminateHunter4": {
        "message": ("Kill 100,000 Illuminate", "HINT: You can't tell how many more are left, but you will continue to make your mark on their population no matter the cost"),
        "title": (
            "<a:EasyAwardEggHunt2025:1363541656447488200> **PEACE WAS NEVER AN OPTION**",
            "<:locked4:1416039238654361600> **~~PEACE WAS NEVER AN OPTION~~**"
        )
    },
    "SuperHunter": {
        "message": ("Kill 1,000,000 Enemies", "HINT: Your enemies are a mere blur, nothing gets in the way of liberty"),
        "title": (
            "<a:EasyAwardEggHunt2025:1363541656447488200> **NO MATTER THE FRONT**",
            "<:locked4:1416039238654361600> **~~NO MATTER THE FRONT~~**"
        )
    },
    "EveryMilestone": {
        "message": ("Complete Every Milestone", "HINT: Beating Top Records is just another day at the office"),
        "title": (
            "<a:EasyAwardEggHunt2025:1363541656447488200> **SECOND GALACTIC WAR VETERAN**",
            "<:locked4:1416039238654361600> **~~SECOND GALACTIC WAR VETERAN~~**"
        )
    },
    "OneHundredPercent": {
        "message": ("Achieve 100% Completion", "HINT: ..."),
        "title": (
            "<a:EasyAwardEggHunt2025:1363541656447488200> **JOHN HELLDIVER**",
            "<:locked4:1416039238654361600> **~~???~~**"
        )
    }
}

# Generate messages and titles dynamically
for key, defs in ACHIEVEMENT_DEFS.items():
    achieved = achievements[key]
    globals()[f"{key}_message"] = defs["message"][0] if achieved else defs["message"][1]
    globals()[f"{key}_title"] = defs["title"][0] if achieved else defs["title"][1]

# generate embed message

helldiver_level = df['Level'].iloc[-1]
helldiver_title = df['Title'].iloc[-1]
helldiver_ses = df['Super Destroyer'].iloc[-1]
helldiver_name = df['Helldivers'].iloc[-1]
non_blank_notes = df['Note'].dropna()
latest_note = non_blank_notes.iloc[-1] if not non_blank_notes.empty else "No Quote"


# UID from local DCord.json (user settings)
try:
    with open('./JSON/DCord.json', 'r') as f:
        settings_data = json.load(f)
        UID = settings_data.get('discord_uid', '0')
except (FileNotFoundError, json.JSONDecodeError) as e:
    logging.error(f"Error loading settings.json: {e}")
    UID = '0'  # Fallback to default

# Get discord_uid from DCord.json
with open('./JSON/DCord.json', 'r') as f:
    dcord_data = json.load(f)
    user_discord_uid = dcord_data.get('discord_uid', '')

bicon = iconconfig['BadgeIcons']['Icon'] if user_discord_uid in ['695767541393653791', '850139032720900116'] else ''
ticon = iconconfig['BadgeIcons']['Test'] if user_discord_uid in ['332209233577771008'] else ''
            
if dcord_data.get('platform') == 'Steam':
        PIco = iconconfig['BadgeIcons-Platform']['Steam']
elif dcord_data.get('platform') == 'PlayStation':
        PIco = iconconfig['BadgeIcons-Platform']['PlayStation']
elif dcord_data.get('platform') == 'Xbox':
        PIco = iconconfig['BadgeIcons-Platform']['Xbox']
else:
        PIco = ''
# Check mission log for planet visits
excel_file = 'mission_log_test.xlsx' if DEBUG else 'mission_log.xlsx'
try:
    df = pd.read_excel(os.path.join(APP_DATA, excel_file))
    # Parse and use the known time format when checking for last year's missions
    times = pd.to_datetime(df['Time'], format=DATE_FORMAT, errors='coerce')
    if (times.dt.year == datetime.now().year - 1).any():
        yearico = iconconfig["BadgeIcons"]["1 Year"]
    else:
        yearico = ''
    bsuperearth = iconconfig['BadgeIcons']['Super Earth'] if 'Super Earth' in df['Planet'].values else ''
    bcyberstan = iconconfig['BadgeIcons']['Cyberstan'] if 'Cyberstan' in df['Planet'].values else ''
    bmaleveloncreek = iconconfig['BadgeIcons']['Malevelon Creek'] if 'Malevelon Creek' in df['Planet'].values else ''
    bcalypso = iconconfig['BadgeIcons']['Calypso'] if 'Calypso' in df['Planet'].values or user_discord_uid in ['695767541393653791', '850139032720900116'] else ''
    bpopliix = iconconfig['BadgeIcons']['Popli IX'] if 'Pöpli IX' in df['Planet'].values else ''
except Exception as e:
    logging.error(f"Error checking mission log for planet visits: {e}")

# Create embed data
embed_data = {
    "content": None,
    "embeds": [
        {
            "title": f"{helldiver_ses}\nHelldiver: {helldiver_name}\n{bicon}{ticon}{yearico}{PIco}{bsuperearth}{bcyberstan}{bmaleveloncreek}{bcalypso}{bpopliix}",
            "description": f"**Level {helldiver_level} | {helldiver_title} {TITLE_ICONS.get(df['Title'].iloc[-1], '')}**\n\n\"{latest_note}\"\n\nTotal Completion: {achievement_percentage}%\n\n<a:easyshine1:1349110651829747773> <a:gol:1414376388516909076> Achievements <a:gol:1414376388516909076> <a:easyshine3:1349110648528699422>\n" + 
                        f"> {globals()['CmdFavourite1_title']}\n" +
                        f"> *{globals()['CmdFavourite1_message']}*\n> *{CmdFavourite1_date}*\n" +
                        f"> \n" +
                        f"> {globals()['CmdFavourite2_title']}\n" +
                        f"> *{globals()['CmdFavourite2_message']}*\n> *{CmdFavourite2_date}*\n" +
                        f"> \n" +
                        f"> {globals()['CmdFavourite3_title']}\n" +
                        f"> *{globals()['CmdFavourite3_message']}*\n> *{CmdFavourite3_date}*\n" +
                        f"> \n" +
                        f"> {globals()['ReliableDiver1_title']}\n" +
                        f"> *{globals()['ReliableDiver1_message']}*\n> *{ReliableDiver1_date}*\n" +
                        f"> \n" +
                        f"> {globals()['ReliableDiver2_title']}\n" +
                        f"> *{globals()['ReliableDiver2_message']}*\n> *{ReliableDiver2_date}*\n" +
                        f"> \n" +
                        f"> {globals()['ReliableDiver3_title']}\n" +
                        f"> *{globals()['ReliableDiver3_message']}*\n> *{ReliableDiver3_date}*\n" +
                        f"> \n" +
                        f"> {globals()['DSSDiver1_title']}\n" +
                        f"> *{globals()['DSSDiver1_message']}*\n> *{DSSDiver1_date}*\n" +
                        f"> \n" +
                        f"> {globals()['DSSDiver2_title']}\n" +
                        f"> *{globals()['DSSDiver2_message']}*\n> *{DSSDiver2_date}*\n" +
                        f"> \n" +
                        f"> {globals()['DSSDiver3_title']}\n" +
                        f"> *{globals()['DSSDiver3_message']}*\n> *{DSSDiver3_date}*\n" +
                        f"> \n" +
                        f"> {globals()['PlanetDiver1_title']}\n" +
                        f"> *{globals()['PlanetDiver1_message']}*\n> *{PlanetDiver1_date}* \n" +
                        f"> \n" +
                        f"> {globals()['PlanetDiver2_title']}\n" +
                        f"> *{globals()['PlanetDiver2_message']}*\n> *{PlanetDiver2_date}*\n" +
                        f"> \n" +
                        f"> {globals()['PlanetDiver3_title']}\n" +
                        f"> *{globals()['PlanetDiver3_message']}*\n> *{PlanetDiver3_date}*\n" +
                        f"> \n" +
                        f"> {globals()['SectorDiver1_title']}\n" +
                        f"> *{globals()['SectorDiver1_message']}*\n> *{SectorDiver1_date}*\n" +
                        f"> \n" +
                        f"> {globals()['SectorDiver2_title']}\n" +
                        f"> *{globals()['SectorDiver2_message']}*\n> *{SectorDiver2_date}*\n" +
                        f"> \n" +
                        f"> {globals()['SectorDiver3_title']}\n" +
                        f"> *{globals()['SectorDiver3_message']}*\n> *{SectorDiver3_date}*\n" +
                        f"> \n" +
                        f"> {globals()['EveryAchievement_title']}\n" +
                        f"> *{globals()['EveryAchievement_message']}*\n> *{EveryAchievement_date}*",                    
            "color": 7257043,
            "author": {
                        "name": f"SEAF Achievement Record\nDate: {date}",
                        "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356001307596427564/NwNzS9B.png?ex=67eafa21&is=67e9a8a1&hm=7e204265cbcdeaf96d7b244cd63992c4ef10dc18befbcf2ed39c3a269af14ec0&"
                    },
            "image": {"url": f"https://cdn.discordapp.com/attachments/1340508329977446484/1416046371911241847/achievementsBanner.png?ex=68c56b73&is=68c419f3&hm=291ffb6f464c34e8fc2e20204d387ffaa8324d1e71165bd4f925e0dbb7dc6efc&"},
            "thumbnail": {"url": f"{profile_picture}"}
        },
        {           "description": f"<a:easyshine1:1349110651829747773> <a:EasyAwardBaftaMP2025:1363545915352289371> Challenges <a:EasyAwardBaftaMP2025:1363545915352289371> <a:easyshine3:1349110648528699422>\n" + 
                        f"> {globals()['OutbreakPerfected1_title']}\n" +
                        f"> *{globals()['OutbreakPerfected1_message']}*\n> *{OutbreakPerfected1_date}*\n" +
                        f"> \n" +
                        f"> {globals()['OutbreakPerfected2_title']}\n" +
                        f"> *{globals()['OutbreakPerfected2_message']}*\n> *{OutbreakPerfected2_date}*\n" +
                        f"> \n" +
                        f"> {globals()['OutbreakPerfected3_title']}\n" +
                        f"> *{globals()['OutbreakPerfected3_message']}*\n> *{OutbreakPerfected3_date}*\n" +
                        f"> \n" +
                        f"> {globals()['AutomatonPerfected1_title']}\n" +
                        f"> *{globals()['AutomatonPerfected1_message']}*\n> *{AutomatonPerfected1_date}*\n" +
                        f"> \n" +
                        f"> {globals()['AutomatonPerfected2_title']}\n" +
                        f"> *{globals()['AutomatonPerfected2_message']}*\n> *{AutomatonPerfected2_date}*\n" +
                        f"> \n" +
                        f"> {globals()['AutomatonPerfected3_title']}\n" +
                        f"> *{globals()['AutomatonPerfected3_message']}*\n> *{AutomatonPerfected3_date}*\n" +
                        f"> \n" +
                        f"> {globals()['IlluminatePerfected1_title']}\n" +
                        f"> *{globals()['IlluminatePerfected1_message']}*\n> *{IlluminatePerfected1_date}*\n" +
                        f"> \n" +
                        f"> {globals()['IlluminatePerfected2_title']}\n" +
                        f"> *{globals()['IlluminatePerfected2_message']}*\n> *{IlluminatePerfected2_date}*\n" +
                        f"> \n" +
                        f"> {globals()['IlluminatePerfected3_title']}\n" +
                        f"> *{globals()['IlluminatePerfected3_message']}*\n> *{IlluminatePerfected3_date}*\n" +
                        f"> \n" +
                        f"> {globals()['TerminidHunter1_title']}\n" +
                        f"> *{globals()['TerminidHunter1_message']}*\n> *{TerminidHunter1_date}*\n" +
                        f"> \n" +
                        f"> {globals()['TerminidHunter2_title']}\n" +
                        f"> *{globals()['TerminidHunter2_message']}*\n> *{TerminidHunter2_date}*\n" +
                        f"> \n" +
                        f"> {globals()['TerminidHunter3_title']}\n" +
                        f"> *{globals()['TerminidHunter3_message']}*\n> *{TerminidHunter3_date}*\n" +
                        f"> \n" +
                        f"> {globals()['AutomatonHunter1_title']}\n" +
                        f"> *{globals()['AutomatonHunter1_message']}*\n> *{AutomatonHunter1_date}*\n" +
                        f"> \n" +
                        f"> {globals()['AutomatonHunter2_title']}\n" +
                        f"> *{globals()['AutomatonHunter2_message']}*\n> *{AutomatonHunter2_date}*\n" +
                        f"> \n" +
                        f"> {globals()['AutomatonHunter3_title']}\n" +
                        f"> *{globals()['AutomatonHunter3_message']}*\n> *{AutomatonHunter3_date}*\n" +
                        f"> \n" +
                        f"> {globals()['IlluminateHunter1_title']}\n" +
                        f"> *{globals()['IlluminateHunter1_message']}*\n> *{IlluminateHunter1_date}*\n" +
                        f"> \n" +
                        f"> {globals()['IlluminateHunter2_title']}\n" +
                        f"> *{globals()['IlluminateHunter2_message']}*\n> *{IlluminateHunter2_date}*\n" +
                        f"> \n" +
                        f"> {globals()['IlluminateHunter3_title']}\n" +
                        f"> *{globals()['IlluminateHunter3_message']}*\n> *{IlluminateHunter3_date}*\n" +
                        f"> \n" +
                        f"> {globals()['Streak10_title']}\n" +
                        f"> *{globals()['Streak10_message']}*\n> *{Streak10_date}*\n" +
                        f"> \n" +
                        f"> {globals()['Streak20_title']}\n" +
                        f"> *{globals()['Streak20_message']}*\n> *{Streak20_date}*\n" +
                        f"> \n" +
                        f"> {globals()['Streak30_title']}\n" +
                        f"> *{globals()['Streak30_message']}*\n> *{Streak30_date}*\n" +
                        f"> \n" +
                        f"> {globals()['EveryChallenge_title']}\n" +
                        f"> *{globals()['EveryChallenge_message']}*\n> *{EveryChallenge_date}*",
            "color": 7257043,
            "author": {
                        "name": f"SEAF Challenge Record\nDate: {date}",
                        "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356001307596427564/NwNzS9B.png?ex=67eafa21&is=67e9a8a1&hm=7e204265cbcdeaf96d7b244cd63992c4ef10dc18befbcf2ed39c3a269af14ec0&"
                    },
            "image": {"url": f"https://cdn.discordapp.com/attachments/1340508329977446484/1416046378492235826/challengesBanner.png?ex=68c56b75&is=68c419f5&hm=acf7a19e5c86a0057171fd7f9c997a7f9989b0cda63232eba6dd15edeb082921&"},
        }
    ],
    "attachments": []
}

embed_data_2 = {
    "content": None,
    "embeds": [
        {           "description": f"<a:easyshine1:1349110651829747773> <a:EasyAwardBaftaMusic2025:1359268029850058974> Triumphs <a:EasyAwardBaftaMusic2025:1359268029850058974> <a:easyshine3:1349110648528699422>\n" + 
                        f"> {globals()['MalevelonCreek_title']}\n" +
                        f"> *{globals()['MalevelonCreek_message']}*\n> *{MalevelonCreek_date}*\n" +
                        f"> \n" +
                        f"> {globals()['SuperEarth_title']}\n" +
                        f"> *{globals()['SuperEarth_message']}*\n> *{SuperEarth_date}*\n" +
                        f"> \n" +
                        f"> {globals()['Cyberstan_title']}\n" +
                        f"> *{globals()['Cyberstan_message']}*\n> *{Cyberstan_date}*\n" +
                        f"> \n" +
                        f"> {globals()['AllDifficulties_title']}\n" +
                        f"> *{globals()['AllDifficulties_message']}*\n> *{AllDifficulties_date}*\n" +
                        f"> \n" +
                        f"> {globals()['AllCampaigns_title']}\n" +
                        f"> *{globals()['AllCampaigns_message']}*\n> *{AllCampaigns_date}*\n" +
                        f"> \n" +
                        f"> {globals()['AllBiomes_title']}\n" +
                        f"> *{globals()['AllBiomes_message']}*\n> *{AllBiomes_date}*\n" +
                        f"> \n" +
                        f"> {globals()['DisgracefulConduct_title']}\n" +
                        f"> *{globals()['DisgracefulConduct_message']}*\n> *{DisgracefulConduct_date}*\n" +
                        f"> \n" +
                        f"> {globals()['CostlyFailure_title']}\n" +
                        f"> *{globals()['CostlyFailure_message']}*\n> *{CostlyFailure_date}*\n" +
                        f"> \n" +
                        f"> {globals()['EveryTriumph_title']}\n" +
                        f"> *{globals()['EveryTriumph_message']}*\n> *{EveryTriumph_date}*\n",

            "color": 7257043,
            "author": {
                        "name": f"SEAF Triumph Record\nDate: {date}",
                        "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356001307596427564/NwNzS9B.png?ex=67eafa21&is=67e9a8a1&hm=7e204265cbcdeaf96d7b244cd63992c4ef10dc18befbcf2ed39c3a269af14ec0&"
                    },
            "image": {"url": f"https://cdn.discordapp.com/attachments/1340508329977446484/1416046382896250933/triumphsBanner.png?ex=68c56b76&is=68c419f6&hm=00f97614e113fab2ed23c56dbd5a2f94e9d7ddd963b0bcd9b3ce896dc04146aa&"},
        },
        {           "description": f"<a:gshiny1:1416046438764249240> <a:EasyAwardEggHunt2025:1363541656447488200> Milestones <a:EasyAwardEggHunt2025:1363541656447488200> <a:gshiny3:1416046435610136699>\n" + 
                        f"> {globals()['OneMission_title']}\n" +
                        f"> *{globals()['OneMission_message']}*\n> *{OneMission_date}*\n" +
                        f"> \n" +
                        f"> {globals()['OnePlanet_title']}\n" +
                        f"> *{globals()['OnePlanet_message']}*\n> *{OnePlanet_date}*\n" +
                        f"> \n" +
                        f"> {globals()['OneSector_title']}\n" +
                        f"> *{globals()['OneSector_message']}*\n> *{OneSector_date}*\n" +
                        f"> \n" +
                        f"> {globals()['CmdFavourite4_title']}\n" +
                        f"> *{globals()['CmdFavourite4_message']}*\n> *{CmdFavourite4_date}*\n" +
                        f"> \n" +
                        f"> {globals()['ReliableDiver4_title']}\n" +
                        f"> *{globals()['ReliableDiver4_message']}*\n> *{ReliableDiver4_date}*\n" +
                        f"> \n" +
                        f"> {globals()['DSSDiver4_title']}\n" +
                        f"> *{globals()['DSSDiver4_message']}*\n> *{DSSDiver4_date}*\n" +
                        f"> \n" +
                        f"> {globals()['OutbreakPerfected4_title']}\n" +
                        f"> *{globals()['OutbreakPerfected4_message']}*\n> *{OutbreakPerfected4_date}*\n" +
                        f"> \n" +
                        f"> {globals()['AutomatonPerfected4_title']}\n" +
                        f"> *{globals()['AutomatonPerfected4_message']}*\n> *{AutomatonPerfected4_date}*\n" +
                        f"> \n" +
                        f"> {globals()['IlluminatePerfected4_title']}\n" +
                        f"> *{globals()['IlluminatePerfected4_message']}*\n> *{IlluminatePerfected4_date}*\n" +
                        f"> \n" +
                        f"> {globals()['TerminidHunter4_title']}\n" +
                        f"> *{globals()['TerminidHunter4_message']}*\n> *{TerminidHunter4_date}*\n" +
                        f"> \n" +
                        f"> {globals()['AutomatonHunter4_title']}\n" +
                        f"> *{globals()['AutomatonHunter4_message']}*\n> *{AutomatonHunter4_date}*\n" +
                        f"> \n" +
                        f"> {globals()['IlluminateHunter4_title']}\n" +
                        f"> *{globals()['IlluminateHunter4_message']}*\n> *{IlluminateHunter4_date}*\n" +
                        f"> \n" +
                        f"> {globals()['SuperHunter_title']}\n" +
                        f"> *{globals()['SuperHunter_message']}*\n> *{SuperHunter_date}*\n" +
                        f"> \n" +
                        f"> {globals()['EveryMilestone_title']}\n" +
                        f"> *{globals()['EveryMilestone_message']}*\n> *{EveryMilestone_date}*\n" +
                        f"> \n" +
                        f"> {globals()['OneHundredPercent_title']}\n" +
                        f"> *{globals()['OneHundredPercent_message']}*\n> *{OneHundredPercent_date}*\n",
            "color": 16761088,
            "author": {
                        "name": f"SEAF Milestone Record\nDate: {date}",
                        "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356001307596427564/NwNzS9B.png?ex=67eafa21&is=67e9a8a1&hm=7e204265cbcdeaf96d7b244cd63992c4ef10dc18befbcf2ed39c3a269af14ec0&"
                    },
            "footer": {"text": f"\n{UID}   v{VERSION}{DEV_RELEASE}","icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356025859319926784/5cwgI15.png?ex=67eb10fe&is=67e9bf7e&hm=ab6326a9da1e76125238bf3668acac8ad1e43b24947fc6d878d7b94c8a60ab28&"},
            "image": {"url": f"https://cdn.discordapp.com/attachments/1340508329977446484/1416046388663287808/milestonesBanner.png?ex=68c56b77&is=68c419f7&hm=89b8497b58d232ae0f194df8ab210bf123765ba550321bb8ab1b08a38c0de8c8&"},
        }
    ],
    "attachments": []
}

# Logging already configured via setup_logging in import section.

# Determine ACTIVE_WEBHOOK list based on DEBUG flag
if DEBUG:
    # Use TEST webhooks from config (support comma-separated list)
    ACTIVE_WEBHOOK = [w.strip() for w in config['Webhooks']['TEST'].split(',') if w.strip()]
    logging.info("DEBUG mode: using TEST webhook(s)")
else:
    # Load production webhooks from external JSON
    try:
        with open('./JSON/DCord.json', 'r') as f:
            dcord_data = json.load(f)
            ACTIVE_WEBHOOK = dcord_data.get('discord_webhooks_export', [])
            ACTIVE_WEBHOOK = [
                (w.get('url') if isinstance(w, dict) else str(w)).strip()
                for w in ACTIVE_WEBHOOK
                if (isinstance(w, dict) and str(w.get('url','')).strip()) or (isinstance(w, str) and w.strip())
            ]
        if not ACTIVE_WEBHOOK:
            logging.error("No production webhooks found in DCord.json (key: discord_webhooks_export).")
    except FileNotFoundError:
        logging.error("DCord.json not found. Cannot load production webhooks.")
        ACTIVE_WEBHOOK = []
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse DCord.json: {e}")
        ACTIVE_WEBHOOK = []

# Send the embed payload to each webhook
successes = []
for url in ACTIVE_WEBHOOK:
    try:
        response = requests.post(url, json=embed_data, timeout=10)
        response = requests.post(url, json=embed_data_2, timeout=10)
        if response.status_code == 204:
            logging.info(f"Successfully sent to Discord webhook: {url}")
            successes.append(True)
        else:
            logging.error(f"Failed to send to Discord webhook {url}. Status code: {response.status_code}")
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