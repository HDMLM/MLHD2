import pandas as pd
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

#Constants
DEBUG = config.getboolean('DEBUGGING', 'DEBUG', fallback=False)
setup_logging(DEBUG)

# Set up application data paths 
APP_DATA = os.path.join(os.getenv('LOCALAPPDATA'), 'MLHD2')
if not os.path.exists(APP_DATA):
    os.makedirs(APP_DATA)

EXCEL_FILE_PROD = os.path.join(APP_DATA, 'mission_log.xlsx')
EXCEL_FILE_TEST = os.path.join(APP_DATA, 'mission_log_test.xlsx')

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
CmdFavourite1 = total_missions >= 100
CmdFavourite2 = total_missions >= 250
CmdFavourite3 = total_missions >= 500
ReliableDiver1 = total_missions_major_order >= 100
ReliableDiver2 = total_missions_major_order >= 250
ReliableDiver3 = total_missions_major_order >= 500
DSSDiver1 = total_missions_dss >= 100
DSSDiver2 = total_missions_dss >= 250
DSSDiver3 = total_missions_dss >= 500
CityDiver1 = total_missions_city >= 100
CityDiver2 = total_missions_city >= 250
CityDiver3 = total_missions_city >= 500
PlanetDiver1 = total_missions_planets >= 25
PlanetDiver2 = total_missions_planets >= 50
PlanetDiver3 = total_missions_planets >= 100
SectorDiver1 = total_missions_sectors >= 15
SectorDiver2 = total_missions_sectors >= 30
SectorDiver3 = total_missions_sectors >= 45
EveryAchievement = total_missions >= 500 and total_missions_major_order >= 500 and total_missions_dss >= 500 and total_missions_city >= 500 and total_missions_planets >= 100 and total_missions_sectors >= 45
OutbreakPerfected1 = total_terminid_missions >= 100
OutbreakPerfected2 = total_terminid_missions >= 250
OutbreakPerfected3 = total_terminid_missions >= 500
AutomatonPerfected1 = total_automaton_missions >= 100
AutomatonPerfected2 = total_automaton_missions >= 250
AutomatonPerfected3 = total_automaton_missions >= 500
IlluminatePerfected1 = total_illuminate_missions >= 100
IlluminatePerfected2 = total_illuminate_missions >= 250
IlluminatePerfected3 = total_illuminate_missions >= 500
TerminidHunter1 = total_terminid_kills >= 10000
TerminidHunter2 = total_terminid_kills >= 25000
TerminidHunter3 = total_terminid_kills >= 50000
AutomatonHunter1 = total_automaton_kills >= 10000
AutomatonHunter2 = total_automaton_kills >= 25000
AutomatonHunter3 = total_automaton_kills >= 50000
IlluminateHunter1 = total_illuminate_kills >= 10000
IlluminateHunter2 = total_illuminate_kills >= 25000
IlluminateHunter3 = total_illuminate_kills >= 50000
Streak10 = streak_10
Streak20 = streak_20
Streak30 = streak_30
EveryChallenge = total_terminid_missions >= 500 and total_automaton_missions >= 500 and total_illuminate_missions >= 500 and total_terminid_kills >= 50000 and total_automaton_kills >= 50000 and total_illuminate_kills >= 50000 and streak_30
MalevelonCreek = malevelon_creek
SuperEarth = super_earth
Cyberstan = cyberstan
AllDifficulties = all_difficulties
AllCampaigns = all_campaigns
AllBiomes = all_biomes
DisgracefulConduct = disgraceful_conduct
CostlyFailure = costly_failure
EveryTriumph = malevelon_creek and super_earth and cyberstan and all_difficulties and all_campaigns and all_biomes and disgraceful_conduct and costly_failure
OneMission = one_mission_100
OnePlanet = one_planet_100
OneSector = one_sector_100
CmdFavourite4 = total_missions >= 1000
ReliableDiver4 = total_missions_major_order >= 1000
DSSDiver4 = total_missions_dss >= 1000
CityDiver4 = total_missions_city >= 1000
OutbreakPerfected4 = total_terminid_missions >= 1000
AutomatonPerfected4 = total_automaton_missions >= 1000
IlluminatePerfected4 = total_illuminate_missions >= 1000
TerminidHunter4 = total_terminid_kills >= 100000
AutomatonHunter4 = total_automaton_kills >= 100000
IlluminateHunter4 = total_illuminate_kills >= 100000
SuperHunter = total_kills >= 1000000
EveryMilestone = total_missions >= 1000 and total_missions_major_order >= 1000 and total_missions_dss >= 1000 and total_missions_city >= 1000 and total_terminid_missions >= 1000 and total_automaton_missions >= 1000 and total_illuminate_missions >= 1000 and total_terminid_kills >= 100000 and total_automaton_kills >= 100000 and total_illuminate_kills >= 100000 and total_kills >= 1000000

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
    "CityDiver1": CityDiver1,
    "CityDiver2": CityDiver2,
    "CityDiver3": CityDiver3,
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
    "CityDiver4": CityDiver4,
    "OutbreakPerfected4": OutbreakPerfected4,
    "AutomatonPerfected4": AutomatonPerfected4,
    "IlluminatePerfected4": IlluminatePerfected4,
    "TerminidHunter4": TerminidHunter4,
    "AutomatonHunter4": AutomatonHunter4,
    "IlluminateHunter4": IlluminateHunter4,
    "SuperHunter": SuperHunter,
    "EveryMilestone": EveryMilestone
}

# Calculate total achievements completed
total_achievements = len(achievements)
completed_achievements = sum(1 for value in achievements.values() if value)
achievement_percentage = round((completed_achievements / total_achievements) * 100, 1)

# Add to achievements dictionary
achievements['completion_percentage'] = achievement_percentage

# Load Webhook URL from config
# Discord webhook configuration
WEBHOOK_URLS = {
    'PROD': config['Webhooks']['BAT'].split(','),
    'TEST': config['Webhooks']['TEST'].split(',')
}
ACTIVE_WEBHOOK = WEBHOOK_URLS['TEST'] if DEBUG else WEBHOOK_URLS['PROD']

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
    "CityDiver1": {
        "message": ("Log 100 Missions inside a Mega City", "HINT: You know these streets like the back of your hands"),
        "title": (
            "<a:bro:1414376629190262965> **BELONG TO THE STREETS I**",
            "<:locked1:1416039237106663455> **~~BELONG TO THE STREETS I~~**"
        )
    },
    "CityDiver2": {
        "message": ("Log 250 Missions inside a Mega City", "HINT: You know these streets like the back of your hands"),
        "title": (
            "<a:sil:1414376620378034196> **BELONG TO THE STREETS II**",
            "<:locked1:1416039237106663455> **~~BELONG TO THE STREETS II~~**"
        )
    },
    "CityDiver3": {
        "message": ("Log 500 Missions inside a Mega City", "HINT: You know these streets like the back of your hands"),
        "title": (
            "<a:gol:1414376388516909076> **BELONG TO THE STREETS III**",
            "<:locked1:1416039237106663455> **~~BELONG TO THE STREETS III~~**"
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
    "CityDiver4": {
        "message": ("Log 1000 Missions inside a Mega City", "HINT: You guard Super Earth's Citizens and guide SEAF to freedom"),
        "title": (
            "<a:EasyAwardEggHunt2025:1363541656447488200> **STREETS OF FIRE**",
            "<:locked4:1416039238654361600> **~~STREETS OF FIRE~~**"
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
        "message": ("Complete Every Milestone", "HINT: ..."),
        "title": (
            "<a:EasyAwardEggHunt2025:1363541656447488200> **SECOND GALACTIC WAR VETERAN**",
            "<:locked4:1416039238654361600> **~~SECOND GALACTIC WAR VETERAN~~**"
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
latest_note = df['Note'].iloc[-1] if not pd.isna(df['Note'].iloc[-1]) else "No notes available"

# Discord webhook configuration
WEBHOOK_URLS = {
    'PROD': config['Webhooks']['BAT'].split(','),
    'TEST': config['Webhooks']['TEST'].split(',')
}
ACTIVE_WEBHOOK = WEBHOOK_URLS['TEST'] if DEBUG else WEBHOOK_URLS['PROD']

# UID from local DCord.json (user settings)
try:
    with open('./JSON/DCord.json', 'r') as f:
        settings_data = json.load(f)
        UID = settings_data.get('discord_uid', '0')
except (FileNotFoundError, json.JSONDecodeError) as e:
    logging.error(f"Error loading settings.json: {e}")
    UID = '0'  # Fallback to default

# Create embed data
embed_data = {
    "content": None,
    "embeds": [
        {
            "title": f"{helldiver_ses}\nHelldiver: {helldiver_name}",
            "description": f"**Level {helldiver_level} | {helldiver_title} {TITLE_ICONS.get(df['Title'].iloc[-1], '')}**\n\n\"{latest_note}\"\n\nTotal Completion: {achievement_percentage}%\n\n<a:easyshine1:1349110651829747773> <a:gol:1414376388516909076> Achievements <a:gol:1414376388516909076> <a:easyshine3:1349110648528699422>\n" + 
                        f"> {globals()['CmdFavourite1_title']}\n" +
                        f"> *{globals()['CmdFavourite1_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['CmdFavourite2_title']}\n" +
                        f"> *{globals()['CmdFavourite2_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['CmdFavourite3_title']}\n" +
                        f"> *{globals()['CmdFavourite3_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['ReliableDiver1_title']}\n" +
                        f"> *{globals()['ReliableDiver1_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['ReliableDiver2_title']}\n" +
                        f"> *{globals()['ReliableDiver2_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['ReliableDiver3_title']}\n" +
                        f"> *{globals()['ReliableDiver3_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['DSSDiver1_title']}\n" +
                        f"> *{globals()['DSSDiver1_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['DSSDiver2_title']}\n" +
                        f"> *{globals()['DSSDiver2_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['DSSDiver3_title']}\n" +
                        f"> *{globals()['DSSDiver3_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['CityDiver1_title']}\n" +
                        f"> *{globals()['CityDiver1_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['CityDiver2_title']}\n" +
                        f"> *{globals()['CityDiver2_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['CityDiver3_title']}\n" +
                        f"> *{globals()['CityDiver3_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['PlanetDiver1_title']}\n" +
                        f"> *{globals()['PlanetDiver1_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['PlanetDiver2_title']}\n" +
                        f"> *{globals()['PlanetDiver2_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['PlanetDiver3_title']}\n" +
                        f"> *{globals()['PlanetDiver3_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['SectorDiver1_title']}\n" +
                        f"> *{globals()['SectorDiver1_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['SectorDiver2_title']}\n" +
                        f"> *{globals()['SectorDiver2_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['SectorDiver3_title']}\n" +
                        f"> *{globals()['SectorDiver3_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['EveryAchievement_title']}\n" +
                        f"> *{globals()['EveryAchievement_message']}*\n",                    
            "color": 7257043,
            "author": {"name": "SEAF Achievement Record"},
            "image": {"url": f"https://cdn.discordapp.com/attachments/1340508329977446484/1416046371911241847/achievementsBanner.png?ex=68c56b73&is=68c419f3&hm=291ffb6f464c34e8fc2e20204d387ffaa8324d1e71165bd4f925e0dbb7dc6efc&"},
            "thumbnail": {"url": f"{profile_picture}"}
        },
        {           "description": f"<a:easyshine1:1349110651829747773> <a:EasyAwardBaftaMP2025:1363545915352289371> Challenges <a:EasyAwardBaftaMP2025:1363545915352289371> <a:easyshine3:1349110648528699422>\n" + 
                        f"> {globals()['OutbreakPerfected1_title']}\n" +
                        f"> *{globals()['OutbreakPerfected1_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['OutbreakPerfected2_title']}\n" +
                        f"> *{globals()['OutbreakPerfected2_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['OutbreakPerfected3_title']}\n" +
                        f"> *{globals()['OutbreakPerfected3_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['AutomatonPerfected1_title']}\n" +
                        f"> *{globals()['AutomatonPerfected1_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['AutomatonPerfected2_title']}\n" +
                        f"> *{globals()['AutomatonPerfected2_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['AutomatonPerfected3_title']}\n" +
                        f"> *{globals()['AutomatonPerfected3_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['IlluminatePerfected1_title']}\n" +
                        f"> *{globals()['IlluminatePerfected1_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['IlluminatePerfected2_title']}\n" +
                        f"> *{globals()['IlluminatePerfected2_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['IlluminatePerfected3_title']}\n" +
                        f"> *{globals()['IlluminatePerfected3_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['TerminidHunter1_title']}\n" +
                        f"> *{globals()['TerminidHunter1_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['TerminidHunter2_title']}\n" +
                        f"> *{globals()['TerminidHunter2_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['TerminidHunter3_title']}\n" +
                        f"> *{globals()['TerminidHunter3_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['AutomatonHunter1_title']}\n" +
                        f"> *{globals()['AutomatonHunter1_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['AutomatonHunter2_title']}\n" +
                        f"> *{globals()['AutomatonHunter2_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['AutomatonHunter3_title']}\n" +
                        f"> *{globals()['AutomatonHunter3_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['IlluminateHunter1_title']}\n" +
                        f"> *{globals()['IlluminateHunter1_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['IlluminateHunter2_title']}\n" +
                        f"> *{globals()['IlluminateHunter2_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['IlluminateHunter3_title']}\n" +
                        f"> *{globals()['IlluminateHunter3_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['Streak10_title']}\n" +
                        f"> *{globals()['Streak10_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['Streak20_title']}\n" +
                        f"> *{globals()['Streak20_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['Streak30_title']}\n" +
                        f"> *{globals()['Streak30_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['EveryChallenge_title']}\n" +
                        f"> *{globals()['EveryChallenge_message']}*\n",                        
            "color": 7257043,
            "author": {"name": "SEAF Achievement Record"},
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
                        f"> *{globals()['MalevelonCreek_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['SuperEarth_title']}\n" +
                        f"> *{globals()['SuperEarth_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['Cyberstan_title']}\n" +
                        f"> *{globals()['Cyberstan_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['AllDifficulties_title']}\n" +
                        f"> *{globals()['AllDifficulties_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['AllCampaigns_title']}\n" +
                        f"> *{globals()['AllCampaigns_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['AllBiomes_title']}\n" +
                        f"> *{globals()['AllBiomes_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['DisgracefulConduct_title']}\n" +
                        f"> *{globals()['DisgracefulConduct_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['CostlyFailure_title']}\n" +
                        f"> *{globals()['CostlyFailure_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['EveryTriumph_title']}\n" +
                        f"> *{globals()['EveryTriumph_message']}*\n",
                        
            "color": 7257043,
            "author": {"name": "SEAF Achievement Record"},
            "image": {"url": f"https://cdn.discordapp.com/attachments/1340508329977446484/1416046382896250933/triumphsBanner.png?ex=68c56b76&is=68c419f6&hm=00f97614e113fab2ed23c56dbd5a2f94e9d7ddd963b0bcd9b3ce896dc04146aa&"},
        },
        {           "description": f"<a:gshiny1:1416046438764249240> <a:EasyAwardEggHunt2025:1363541656447488200> Milestones <a:EasyAwardEggHunt2025:1363541656447488200> <a:gshiny3:1416046435610136699>\n" + 
                        f"> {globals()['CmdFavourite4_title']}\n" +
                        f"> *{globals()['CmdFavourite4_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['ReliableDiver4_title']}\n" +
                        f"> *{globals()['ReliableDiver4_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['DSSDiver4_title']}\n" +
                        f"> *{globals()['DSSDiver4_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['CityDiver4_title']}\n" +
                        f"> *{globals()['CityDiver4_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['OutbreakPerfected4_title']}\n" +
                        f"> *{globals()['OutbreakPerfected4_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['AutomatonPerfected4_title']}\n" +
                        f"> *{globals()['AutomatonPerfected4_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['IlluminatePerfected4_title']}\n" +
                        f"> *{globals()['IlluminatePerfected4_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['TerminidHunter4_title']}\n" +
                        f"> *{globals()['TerminidHunter4_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['AutomatonHunter4_title']}\n" +
                        f"> *{globals()['AutomatonHunter4_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['IlluminateHunter4_title']}\n" +
                        f"> *{globals()['IlluminateHunter4_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['SuperHunter_title']}\n" +
                        f"> *{globals()['SuperHunter_message']}*\n" +
                        f"> \n" +
                        f"> {globals()['EveryMilestone_title']}\n" +
                        f"> *{globals()['EveryMilestone_message']}*\n",         
            "color": 16761088,
            "author": {"name": "SEAF Achievement Record"},
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