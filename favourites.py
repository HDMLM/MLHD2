import pandas as pd
import logging
from logging_config import setup_logging
import configparser
import requests
import json
from datetime import datetime
from icon import ENEMY_ICONS, DIFFICULTY_ICONS, PLANET_ICONS, CAMPAIGN_ICONS, MISSION_ICONS, BIOME_BANNERS, SUBFACTION_ICONS, TITLE_ICONS
from main import VERSION, DEV_RELEASE
import os

# Set up application data paths 
APP_DATA = os.path.join(os.getenv('LOCALAPPDATA'), 'MLHD2')
if not os.path.exists(APP_DATA):
    os.makedirs(APP_DATA)

EXCEL_FILE_PROD = os.path.join(APP_DATA, 'mission_log.xlsx')
EXCEL_FILE_TEST = os.path.join(APP_DATA, 'mission_log_test.xlsx')

# Read config file
config = configparser.ConfigParser()
config.read('config.config')
iconconfig = configparser.ConfigParser()
iconconfig.read('icon.config')

#Constants
DEBUG = config.getboolean('DEBUGGING', 'DEBUG', fallback=False)
setup_logging(DEBUG)

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
            messagebox.showerror("Export Error", "You're favourite thing is clearly disobeying orders. No missions found in the log.")
        else:
            messagebox.showerror("Export Error", "No mission data recorded. Please log at least one mission before exporting.")
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
rating_mapping = {"Outstanding Patriotism": 5, "Superior Valour": 4, "Costly Failure": 4, "Honourable Duty":3, "Unremarkable Performance":2, "Dissapointing Service":1, "Disgraceful Conduct":0}
# Calculate total rating
total_rating = sum(rating_mapping[row["Rating"]] for index, row in df.iterrows() if "Rating" in df.columns and row["Rating"] in rating_mapping)
Rating_Percentage = (total_rating / max_rating) * 100

# Get the user's name and level from the last row of the DataFrame
helldiver_ses = df['Super Destroyer'].iloc[-1] if 'Super Destroyer' in df.columns else "Unknown"
helldiver_name = df['Helldivers'].iloc[-1] if 'Helldivers' in df.columns else "Unknown"
helldiver_level = df['Level'].iloc[-1] if 'Level' in df.columns else 0
helldiver_title = df['Title'].iloc[-1] if 'Title' in df.columns else "Unknown"

if DEBUG:
    webhook_urls = [config['Webhooks']['TEST']] # Use the webhook URL from the config for debugging
else:
    # Load webhook URLs from DCord.json
    with open('./JSON/DCord.json', 'r') as f:
        discord_data = json.load(f)
        webhook_urls = discord_data.get('discord_webhooks', [])
        # Normalize possible dict entries and filter invalid/empty
        webhook_urls = [
            (w.get('url') if isinstance(w, dict) else str(w)).strip()
            for w in webhook_urls
            if (isinstance(w, dict) and str(w.get('url', '')).strip()) or (isinstance(w, str) and w.strip())
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

def get_last_deployment(df: pd.DataFrame, enemy_type: str) -> str:
    if 'Time' not in df.columns or 'Enemy Type' not in df.columns:
        return 'No date available'

    # Filter rows for the enemy type
    subset = df[df['Enemy Type'] == enemy_type]
    if subset.empty:
        return 'No deployments'

    # Clean and parse time strings
    times_raw = subset['Time'].astype(str).str.strip()

    # Normalize any '/' to '-' just in case
    times_normalized = times_raw.str.replace('/', '-', regex=False)

    # First try strict expected format
    times_parsed = pd.to_datetime(times_normalized,
                                  format='%d-%m-%Y %H:%M:%S',
                                  errors='coerce')

    # Fallback: attempt a more permissive parse (dayfirst=True)
    if times_parsed.isna().all():
        times_parsed = pd.to_datetime(times_normalized,
                                      errors='coerce',
                                      dayfirst=True)

    # Drop NaT values
    valid_mask = ~times_parsed.isna()
    if not valid_mask.any():
        return 'No valid dates'

    valid_times = times_parsed[valid_mask]

    # Find the timestamp closest to "now"
    now = pd.Timestamp.now()
    deltas = (valid_times - now).abs()
    closest_idx = deltas.idxmin()
    closest_ts = valid_times.loc[closest_idx]

    return closest_ts.strftime('%d-%m-%Y %H:%M:%S')

def get_first_deployment(df: pd.DataFrame, enemy_type: str) -> str:
    if 'Time' not in df.columns or 'Enemy Type' not in df.columns:
        return 'No date available'

    # Filter rows for the enemy type
    subset = df[df['Enemy Type'] == enemy_type]
    if subset.empty:
        return 'No deployments'

    # Clean and parse time strings 
    times_raw = subset['Time'].astype(str).str.strip()

    # Normalize any '/' to '-' just in case
    times_normalized = times_raw.str.replace('/', '-', regex=False)

    # First try strict expected format
    times_parsed = pd.to_datetime(times_normalized,
                                  format='%d-%m-%Y %H:%M:%S', 
                                  errors='coerce')

    # Fallback: attempt a more permissive parse (dayfirst=True)
    if times_parsed.isna().all():
        times_parsed = pd.to_datetime(times_normalized,
                                      errors='coerce',
                                      dayfirst=True)

    # Drop NaT values
    valid_mask = ~times_parsed.isna()
    if not valid_mask.any():
        return 'No valid dates'

    valid_times = times_parsed[valid_mask]

    # Get the earliest timestamp
    first_ts = valid_times.min()
    return first_ts.strftime('%d-%m-%Y %H:%M:%S')

# Iterate through each row
for index, row in df.iterrows():
    # Append Sector values to the list
    if "Sector" in df.columns and row["Sector"] not in sectors:
        sectors.append(row["Sector"])

    # Append Planet values to the list
    if "Planet" in df.columns and row["Planet"] not in planets:
        planets.append(row["Planet"])

    # Append Enemy Type values to the list
    if "Enemy Type" in df.columns and row["Enemy Type"] not in enemy_types:
        enemy_types.append(row["Enemy Type"])
    
    # Append Category values to the list
    if "Mission Category" in df.columns and row["Mission Category"] not in MissionCategory:
        MissionCategory.append(row["Mission Category"])
    
    # Append Difficulty values to the list
    if "Difficulty" in df.columns and row["Difficulty"] not in difficulties:
        difficulties.append(row["Difficulty"])

# Initialize lists to store stats for each planet
planet_kills_list = []
planet_deaths_list = []
planet_orders_list = []

for Planets in planets:
    # Filter data for this planet and sum stats
    planet_data = df[df["Planet"] == Planets]
    planet_kills = planet_data["Kills"].sum()
    planet_deaths = planet_data["Deaths"].sum()
    planet_major_orders = planet_data["Major Order"].astype(int).sum()
    planet_last_date = planet_data["Time"].max() if "Time" in df.columns else "No date available"
    planet_deployments = len(planet_data)
    
    # Create dictionaries to store data for each planet if they don't exist
    if 'planet_data_dict' not in locals():
        planet_data_dict = {}
        planet_kills_dict = {}
        planet_deaths_dict = {}
        planet_orders_dict = {}
        planet_last_date_dict = {}
        planet_deployments_dict = {}
    
    # Store data in dictionaries with planet name as key
    planet_data_dict[Planets] = planet_data
    planet_kills_dict[Planets] = planet_kills
    planet_deaths_dict[Planets] = planet_deaths
    planet_orders_dict[Planets] = planet_major_orders
    planet_last_date_dict[Planets] = planet_last_date
    planet_deployments_dict[Planets] = planet_deployments

# Create a DataFrame from the planet stats
planet_stats_df = pd.DataFrame({
    "Planet": planets,
    "Total Kills": [planet_kills_dict[planet] for planet in planets],
    "Total Deaths": [planet_deaths_dict[planet] for planet in planets],
    "Major Orders": [planet_orders_dict[planet] for planet in planets],
    "Last Date": [planet_last_date_dict[planet] for planet in planets]
})

# Discord webhook configuration
if DEBUG:
    # Use TEST webhook from config if in debug mode
    ACTIVE_WEBHOOK = [config['Webhooks']['TEST']]
else:
    # Use PROD webhook in production mode
    with open('./JSON/DCord.json', 'r') as f:
        dcord_data = json.load(f)
        ACTIVE_WEBHOOK = dcord_data.get('discord_webhooks', [])
        ACTIVE_WEBHOOK = [
            (w.get('url') if isinstance(w, dict) else str(w)).strip()
            for w in ACTIVE_WEBHOOK
            if (isinstance(w, dict) and str(w.get('url','')).strip()) or (isinstance(w, str) and w.strip())
        ]

# Get latest note
non_blank_notes = df['Note'].dropna()
latest_note = non_blank_notes.iloc[-1] if not non_blank_notes.empty else "No Quote"

# Get value counts for each category
mission_counts = df['Mission Type'].value_counts()
campaign_counts = df['Mission Category'].value_counts()
faction_counts = df['Enemy Type'].value_counts()
subfaction_counts = df['Enemy Subfaction'].value_counts()
difficulty_counts = df['Difficulty'].value_counts()
planet_counts = df['Planet'].value_counts()
sector_counts = df['Sector'].value_counts()

# First Place
search_mission = mission_counts.index[0]
MissionCount = mission_counts.iloc[0]
search_campaign = campaign_counts.index[0]
CampaignCount = campaign_counts.iloc[0]
search_faction = faction_counts.index[0]
FactionCount = faction_counts.iloc[0]
search_subfaction = subfaction_counts.index[0]
SubfactionCount = subfaction_counts.iloc[0]
search_difficulty = difficulty_counts.index[0]
DifficultyCount = difficulty_counts.iloc[0]
search_planet = planet_counts.index[0]
PlanetCount = planet_counts.iloc[0]
search_sector = sector_counts.index[0]
SectorCount = sector_counts.iloc[0]

# Second Place - Remove first place from counts
mission_counts_2 = mission_counts.drop(search_mission)
campaign_counts_2 = campaign_counts.drop(search_campaign)
faction_counts_2 = faction_counts.drop(search_faction)
subfaction_counts_2 = subfaction_counts.drop(search_subfaction)
difficulty_counts_2 = difficulty_counts.drop(search_difficulty)
planet_counts_2 = planet_counts.drop(search_planet)
sector_counts_2 = sector_counts.drop(search_sector)

search_mission2 = mission_counts_2.index[0] if len(mission_counts_2) > 0 else "None"
MissionCount2 = mission_counts_2.iloc[0] if len(mission_counts_2) > 0 else 0
search_campaign2 = campaign_counts_2.index[0] if len(campaign_counts_2) > 0 else "None"
CampaignCount2 = campaign_counts_2.iloc[0] if len(campaign_counts_2) > 0 else 0
search_faction2 = faction_counts_2.index[0] if len(faction_counts_2) > 0 else "None"
FactionCount2 = faction_counts_2.iloc[0] if len(faction_counts_2) > 0 else 0
search_subfaction2 = subfaction_counts_2.index[0] if len(subfaction_counts_2) > 0 else "None"
SubfactionCount2 = subfaction_counts_2.iloc[0] if len(subfaction_counts_2) > 0 else 0
search_difficulty2 = difficulty_counts_2.index[0] if len(difficulty_counts_2) > 0 else "None"
DifficultyCount2 = difficulty_counts_2.iloc[0] if len(difficulty_counts_2) > 0 else 0
search_planet2 = planet_counts_2.index[0] if len(planet_counts_2) > 0 else "None"
PlanetCount2 = planet_counts_2.iloc[0] if len(planet_counts_2) > 0 else 0
search_sector2 = sector_counts_2.index[0] if len(sector_counts_2) > 0 else "None"
SectorCount2 = sector_counts_2.iloc[0] if len(sector_counts_2) > 0 else 0

# Third Place - Remove second place from remaining counts
mission_counts_3 = mission_counts_2.drop(search_mission2) if search_mission2 != "None" else mission_counts_2
campaign_counts_3 = campaign_counts_2.drop(search_campaign2) if search_campaign2 != "None" else campaign_counts_2
faction_counts_3 = faction_counts_2.drop(search_faction2) if search_faction2 != "None" else faction_counts_2
subfaction_counts_3 = subfaction_counts_2.drop(search_subfaction2) if search_subfaction2 != "None" else subfaction_counts_2
difficulty_counts_3 = difficulty_counts_2.drop(search_difficulty2) if search_difficulty2 != "None" else difficulty_counts_2
planet_counts_3 = planet_counts_2.drop(search_planet2) if search_planet2 != "None" else planet_counts_2
sector_counts_3 = sector_counts_2.drop(search_sector2) if search_sector2 != "None" else sector_counts_2

search_mission3 = mission_counts_3.index[0] if len(mission_counts_3) > 0 else "None"
MissionCount3 = mission_counts_3.iloc[0] if len(mission_counts_3) > 0 else 0
search_campaign3 = campaign_counts_3.index[0] if len(campaign_counts_3) > 0 else "None"
CampaignCount3 = campaign_counts_3.iloc[0] if len(campaign_counts_3) > 0 else 0
search_faction3 = faction_counts_3.index[0] if len(faction_counts_3) > 0 else "None"
FactionCount3 = faction_counts_3.iloc[0] if len(faction_counts_3) > 0 else 0
search_subfaction3 = subfaction_counts_3.index[0] if len(subfaction_counts_3) > 0 else "None"
SubfactionCount3 = subfaction_counts_3.iloc[0] if len(subfaction_counts_3) > 0 else 0
search_difficulty3 = difficulty_counts_3.index[0] if len(difficulty_counts_3) > 0 else "None"
DifficultyCount3 = difficulty_counts_3.iloc[0] if len(difficulty_counts_3) > 0 else 0
search_planet3 = planet_counts_3.index[0] if len(planet_counts_3) > 0 else "None"
PlanetCount3 = planet_counts_3.iloc[0] if len(planet_counts_3) > 0 else 0
search_sector3 = sector_counts_3.index[0] if len(sector_counts_3) > 0 else "None"
SectorCount3 = sector_counts_3.iloc[0] if len(sector_counts_3) > 0 else 0

# Get discord_uid from DCord.json
with open('./JSON/DCord.json', 'r') as f:
    dcord_data = json.load(f)
    user_discord_uid = dcord_data.get('discord_uid', '')

bicon = iconconfig['BadgeIcons']['Icon'] if user_discord_uid in ['695767541393653791', '850139032720900116'] else ''
            
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
    bsuperearth = iconconfig['BadgeIcons']['Super Earth'] if 'Super Earth' in df['Planet'].values else ''
    bcyberstan = iconconfig['BadgeIcons']['Cyberstan'] if 'Cyberstan' in df['Planet'].values else ''
    bmaleveloncreek = iconconfig['BadgeIcons']['Malevelon Creek'] if 'Malevelon Creek' in df['Planet'].values else ''
    bcalypso = iconconfig['BadgeIcons']['Calypso'] if 'Calypso' in df['Planet'].values or user_discord_uid in ['695767541393653791', '850139032720900116'] else ''
    bpopliix = iconconfig['BadgeIcons']['Popli IX'] if 'Pöpli IX' in df['Planet'].values else ''
except Exception as e:
    logging.error(f"Error checking mission log for planet visits: {e}")

highest_streak = 0
profile_picture = ""
with open('./JSON/streak_data.json', 'r') as f:
    streak_data = json.load(f)
    # Use "Helldiver" as the key or fall back to helldiver_ses if the first one doesn't exist
    highest_streak = streak_data.get("Helldiver", streak_data.get(helldiver_ses, {})).get("highest_streak", 0)
    profile_picture = streak_data.get("Helldiver", streak_data.get(helldiver_ses, {})).get("profile_picture_name", "")

# Load DCord.json data
with open('./JSON/DCord.json', 'r') as f:
    dcord_data = json.load(f)

# Calculate Mega City deployments excluding "Planet Surface" and empty values
mega_city_count = df[df['Mega City'].fillna('').astype(str).apply(lambda x: x != '' and x.lower() != 'planet surface')].shape[0]

terminids_mega_city_count = df[(df['Enemy Type'] == 'Terminids') & (df['Mega City'].fillna('').astype(str).apply(lambda x: x != '' and x.lower() != 'planet surface'))].shape[0]
automatons_mega_city_count = df[(df['Enemy Type'] == 'Automatons') & (df['Mega City'].fillna('').astype(str).apply(lambda x: x != '' and x.lower() != 'planet surface'))].shape[0]
illuminate_mega_city_count = df[(df['Enemy Type'] == 'Illuminate') & (df['Mega City'].fillna('').astype(str).apply(lambda x: x != '' and x.lower() != 'planet surface'))].shape[0]

# Create embed data
embed_data = {
    "content": None,
    "embeds": [
        {
            "title": "",  # Empty title, will be set below
            "description": f"**Level {helldiver_level} | {helldiver_title} {TITLE_ICONS.get(df['Title'].mode().iloc[0], '')}**\n\n\"{latest_note}\"\n\n<a:easyshine1:1349110651829747773> <a:gol:1414376388516909076> Your Top Favourites <a:gol:1414376388516909076> <a:easyshine3:1349110648528699422>\n" +   
                        f"> Mission - {df['Mission Type'].mode().iloc[0]} {MISSION_ICONS.get(df['Mission Type'].mode().iloc[0], '')} (x{MissionCount})\n" +
                        f"> Campaign - {df['Mission Category'].mode().iloc[0]} {CAMPAIGN_ICONS.get(df['Mission Category'].mode().iloc[0], '')} (x{CampaignCount})\n" +
                        f"> Faction - {df['Enemy Type'].mode().iloc[0]} {ENEMY_ICONS.get(df['Enemy Type'].mode().iloc[0], '')} (x{FactionCount})\n" +
                        f"> Subfaction - {df['Enemy Subfaction'].mode().iloc[0]} {SUBFACTION_ICONS.get(df['Enemy Subfaction'].mode().iloc[0], '')} (x{SubfactionCount})\n"
                        f"> Difficulty - {df['Difficulty'].mode().iloc[0]} {DIFFICULTY_ICONS.get(df['Difficulty'].mode().iloc[0], '')} (x{DifficultyCount})\n" +
                        f"> Planet - {df['Planet'].mode().iloc[0]} {PLANET_ICONS.get(df['Planet'].mode().iloc[0], '')} (x{PlanetCount})\n" +
                        f"> Sector - {df['Sector'].mode().iloc[0]} (x{SectorCount})\n\n" +
                        f"<a:easyshine1:1349110651829747773> <a:sil:1414376620378034196> Strong Contenders <a:sil:1414376620378034196> <a:easyshine3:1349110648528699422>\n" +
                        f"> Mission - {search_mission2} {MISSION_ICONS.get(search_mission2, '')} (x{MissionCount2})\n" +
                        f"> Campaign - {search_campaign2} {CAMPAIGN_ICONS.get(search_campaign2, '')} (x{CampaignCount2})\n" +
                        f"> Faction - {search_faction2} {ENEMY_ICONS.get(search_faction2, '')} (x{FactionCount2})\n" +
                        f"> Subfaction - {search_subfaction2} {SUBFACTION_ICONS.get(search_subfaction2, '')} (x{SubfactionCount2})\n"
                        f"> Difficulty - {search_difficulty2} {DIFFICULTY_ICONS.get(search_difficulty2, '')} (x{DifficultyCount2})\n" +
                        f"> Planet - {search_planet2} {PLANET_ICONS.get(search_planet2, '')} (x{PlanetCount2})\n" +
                        f"> Sector - {search_sector2} (x{SectorCount2})\n\n" +
                        f"<a:easyshine1:1349110651829747773> <a:bro:1414376629190262965> Honourable Mentions <a:bro:1414376629190262965> <a:easyshine3:1349110648528699422>\n" +
                        f"> Mission - {search_mission3} {MISSION_ICONS.get(search_mission3, '')} (x{MissionCount3})\n" +
                        f"> Campaign - {search_campaign3} {CAMPAIGN_ICONS.get(search_campaign3, '')} (x{CampaignCount3})\n" +
                        f"> Faction - {search_faction3} {ENEMY_ICONS.get(search_faction3, '')} (x{FactionCount3})\n" +
                        f"> Subfaction - {search_subfaction3} {SUBFACTION_ICONS.get(search_subfaction3, '')} (x{SubfactionCount3})\n"
                        f"> Difficulty - {search_difficulty3} {DIFFICULTY_ICONS.get(search_difficulty3, '')} (x{DifficultyCount3})\n" +
                        f"> Planet - {search_planet3} {PLANET_ICONS.get(search_planet3, '')} (x{PlanetCount3})\n" +
                        f"> Sector - {search_sector3} (x{SectorCount3})\n",
            "color": 7257043,
            "author": {"name": "SEAF Battle Record"},
            "footer": {"text": f"{discord_data['discord_uid']}   v{VERSION}{DEV_RELEASE}","icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356025859319926784/5cwgI15.png?ex=67eb10fe&is=67e9bf7e&hm=ab6326a9da1e76125238bf3668acac8ad1e43b24947fc6d878d7b94c8a60ab28&"},
            "image": {"url": f"https://cdn.discordapp.com/attachments/1340508329977446484/1414378556825538601/favouritesbanner.png?ex=68bf5a2d&is=68be08ad&hm=b27d54aca26e82249e873ab14cdd87a698dcc5242b38d563dc7218522197174c&"},
            "thumbnail": {"url": f"{profile_picture}"}
        }
    ],
    "attachments": []
}

# Update the embed title with name and level
embed_data["embeds"][0]["title"] = f"{helldiver_ses}\nHelldiver: {helldiver_name}\n{bicon}{PIco}{bsuperearth}{bcyberstan}{bmaleveloncreek}{bcalypso}{bpopliix}"

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
            "planets": faction_data["Planet"].unique().tolist()
        }

if DEBUG:
    webhook_urls = [config['Webhooks']['TEST']] # Use the webhook URL from the config for debugging
else:
    # Load webhook URLs from DCord.json
    with open('./JSON/DCord.json', 'r') as f:
        discord_data = json.load(f)
        webhook_urls = discord_data.get('discord_webhooks', [])
        # Normalize possible dict entries and filter invalid/empty
        webhook_urls = [
            (w.get('url') if isinstance(w, dict) else str(w)).strip()
            for w in webhook_urls
            if (isinstance(w, dict) and str(w.get('url', '')).strip()) or (isinstance(w, str) and w.strip())
        ]

# Send data to each webhook
for webhook_url in webhook_urls:
    response = requests.post(webhook_url, json=embed_data)
    if response.status_code == 204:
        logging.info("Data sent successfully.")
    else:
        logging.error(f"Failed to send data. Status: {response.status_code}")
