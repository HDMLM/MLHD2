import pandas as pd
import logging
from core.logging_config import setup_logging
import configparser
from core.runtime_paths import app_path
import requests
import json
from datetime import datetime, timezone, timedelta
from core.icon import ENEMY_ICONS, DIFFICULTY_ICONS, PLANET_ICONS, CAMPAIGN_ICONS, MISSION_ICONS, BIOME_BANNERS, SUBFACTION_ICONS, TITLE_ICONS, get_badge_icons
from core.app_core import VERSION, DEV_RELEASE
import os

# Set up application data paths 
APP_DATA = os.path.join(os.getenv('LOCALAPPDATA'), 'MLHD2')
if not os.path.exists(APP_DATA):
    os.makedirs(APP_DATA)

EXCEL_FILE_PROD = os.path.join(APP_DATA, 'mission_log.xlsx')
EXCEL_FILE_TEST = os.path.join(APP_DATA, 'mission_log_test.xlsx')
DATE_FORMAT = "%d-%m-%Y %H:%M:%S"

# Read config file
config = configparser.ConfigParser()
config.read(app_path('orphan', 'config.config'))
iconconfig = configparser.ConfigParser()
iconconfig.read(app_path('orphan', 'icon.config'))

date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

#Constants
DEBUG = config.getboolean('DEBUGGING', 'DEBUG', fallback=False)
setup_logging(DEBUG)

# Read the Excel file
import tkinter as tk
from tkinter import messagebox
import random
import sys
excel_file = EXCEL_FILE_TEST if DEBUG else EXCEL_FILE_PROD
try:
    df = pd.read_excel(excel_file)
    if df.empty:
        logging.error("Error: Excel file is empty. Please ensure the file contains data.")
        # Show a message box to the user
        root = tk.Tk()
        root.withdraw()
        randint = random.randint(1, 2)
        if randint == 1:
            messagebox.showerror("Export Error", "Have you even shot at anything? No missions found in the log.")
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
rating_mapping = {"Gallantry Beyond Measure": 5, "Outstanding Patriotism": 5, "Truly Exceptional Heroism": 4, "Superior Valour": 4, "Costly Failure": 4, "Honourable Duty":3, "Unremarkable Performance":2, "Dissapointing Service":1, "Disgraceful Conduct":0}
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
    with open(app_path('JSON', 'DCord.json'), 'r') as f:
        discord_data = json.load(f)
        webhook_urls = discord_data.get('discord_webhooks', [])
        webhook_urls = [
            (w.get('url') if isinstance(w, dict) else str(w)).strip()
            for w in webhook_urls
            if (isinstance(w, dict) and str(w.get('url','')).strip()) or (isinstance(w, str) and w.strip())
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

# Returns first deployment timestamp for an enemy; affects faction embed stats
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
    with open(app_path('JSON', 'DCord.json'), 'r') as f:
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

# Get Instances from Data
search_mission = df['Mission Type'].mode()[0]
MissionCount = df.apply(lambda row: row.astype(str).str.contains(search_mission, case=False).sum(), axis=1).sum()
search_campaign = df['Mission Category'].mode()[0]
CampaignCount = df.apply(lambda row: row.astype(str).str.contains(search_campaign, case=False).sum(), axis=1).sum()
search_faction = df['Enemy Type'].mode()[0]
FactionCount = df['Enemy Type'].apply(lambda x: str(x).lower() == search_faction.lower()).sum()
search_subfaction = df['Enemy Subfaction'].mode()[0]
SubfactionCount = df.apply(lambda row: row.astype(str).str.contains(search_subfaction, case=False).sum(), axis=1).sum()
search_difficulty = df['Difficulty'].mode()[0]
DifficultyCount = df.apply(lambda row: row.astype(str).str.contains(search_difficulty, case=False).sum(), axis=1).sum()
search_planet = df['Planet'].mode()[0]
PlanetCount = df['Planet'].apply(lambda x: str(x).lower() == search_planet.lower()).sum()
search_sector = df['Sector'].mode()[0]
SectorCount = df.apply(lambda row: row.astype(str).str.contains(search_sector, case=False).sum(), axis=1).sum()

# Get badge icons using centralized function
badge_data = get_badge_icons(DEBUG, APP_DATA, DATE_FORMAT)
bicon = badge_data['bicon']
ticon = badge_data['ticon']
PIco = badge_data['PIco']
yearico = badge_data['yearico']
bsuperearth = badge_data['bsuperearth']
bcyberstan = badge_data['bcyberstan']
bmaleveloncreek = badge_data['bmaleveloncreek']
bcalypso = badge_data['bcalypso']
bpopliix = badge_data['bpopliix']
bseyshelbeach = badge_data['bseyshelbeach']
boshaune = badge_data['boshaune']

highest_streak = 0
profile_picture = ""
with open(app_path('JSON', 'streak_data.json'), 'r') as f:
    streak_data = json.load(f)
    # Use "Helldiver" as the key or fall back to helldiver_ses if the first one doesn't exist
    highest_streak = streak_data.get("Helldiver", streak_data.get(helldiver_ses, {})).get("highest_streak", 0)
    profile_picture = streak_data.get("Helldiver", streak_data.get(helldiver_ses, {})).get("profile_picture_name", "")

# Load DCord.json data
with open(app_path('JSON', 'DCord.json'), 'r') as f:
    dcord_data = json.load(f)

# Calculate Mega City deployments excluding "Planet Surface" and empty values
mega_city_count = df[df['Mega City'].fillna('').astype(str).apply(lambda x: x != '' and x.lower() != 'planet surface')].shape[0]

terminids_mega_city_count = df[(df['Enemy Type'] == 'Terminids') & (df['Mega City'].fillna('').astype(str).apply(lambda x: x != '' and x.lower() != 'planet surface'))].shape[0]
automatons_mega_city_count = df[(df['Enemy Type'] == 'Automatons') & (df['Mega City'].fillna('').astype(str).apply(lambda x: x != '' and x.lower() != 'planet surface'))].shape[0]
illuminate_mega_city_count = df[(df['Enemy Type'] == 'Illuminate') & (df['Mega City'].fillna('').astype(str).apply(lambda x: x != '' and x.lower() != 'planet surface'))].shape[0]

from core.utils import get_effective_flair
flair_colour = get_effective_flair()
if flair_colour.lower() == 'gold':
    FlairLeftIco = iconconfig['MiscIcon'].get('Gold Flair Left', iconconfig['MiscIcon']['Flair Left'])
    FlairRightIco = iconconfig['MiscIcon'].get('Gold Flair Right', iconconfig['MiscIcon']['Flair Right'])
elif flair_colour.lower() == 'blue':
    FlairLeftIco = iconconfig['MiscIcon'].get('Blue Flair Left', iconconfig['MiscIcon']['Flair Left'])
    FlairRightIco = iconconfig['MiscIcon'].get('Blue Flair Right', iconconfig['MiscIcon']['Flair Right'])
elif flair_colour.lower() == 'red':
    FlairLeftIco = iconconfig['MiscIcon'].get('Red Flair Left', iconconfig['MiscIcon']['Flair Left'])
    FlairRightIco = iconconfig['MiscIcon'].get('Red Flair Right', iconconfig['MiscIcon']['Flair Right'])
else:
    FlairLeftIco = iconconfig['MiscIcon'].get(f'Flair Left {flair_colour}', iconconfig['MiscIcon']['Flair Left'])
    FlairRightIco = iconconfig['MiscIcon'].get(f'Flair Right {flair_colour}', iconconfig['MiscIcon']['Flair Right'])
GoldStarIco = iconconfig['Stars']['GoldStar']
FlairSkullIco = iconconfig['MiscIcon']['Flair Skull']
FlairSEIco = iconconfig['MiscIcon']['Flair Super Earth']
FlairGSSkullIco = iconconfig['MiscIcon']['Flair Gold Spinning Skull']
BugIco = iconconfig['EnemyIcons']['Terminids']
BotIco = iconconfig['EnemyIcons']['Automatons']
SquidIco = iconconfig['EnemyIcons']['Illuminate']
KillIco = iconconfig['MiscIcon']['Kills']
DeathIco = iconconfig['MiscIcon']['Deaths']
KDRIco = iconconfig['MiscIcon']['KDR']
HighestKillIco = iconconfig['MiscIcon']['Highest Kills']
DeployIco = iconconfig['MiscIcon']['Deployments']
MODeployIco = iconconfig['MiscIcon']['Major Order Deployments']
DSSDeployIco = iconconfig['MiscIcon']['DSS Deployments']
BugMCDeployIco = iconconfig['MiscIcon']['Bug Mega City Deployments']
BotMCDeployIco = iconconfig['MiscIcon']['Bot Mega City Deployments']
SquidMCDeployIco = iconconfig['MiscIcon']['Squid Mega City Deployments']
LastDeployIco = iconconfig['MiscIcon']['Last Deployment']
LiberationIco = iconconfig['CampaignIcons']['Liberation']
DefenceIco = iconconfig['CampaignIcons']['Defense']
InvasionIco = iconconfig['CampaignIcons']['Invasion']
HighPriorityIco = iconconfig['CampaignIcons']['High-Priority']
AttritionIco = iconconfig['CampaignIcons']['Attrition']

# Create embed data
embed_data = {
    "content": None,
    "embeds": [
        {
            "title": "",  # Empty title, will be set below
            "description": f"**Level {helldiver_level} | {helldiver_title} {TITLE_ICONS.get(df['Title'].iloc[-1], '')}**\n\n\"{latest_note}\"\n\n{FlairLeftIco}  {FlairSkullIco} Combat Statistics {FlairSkullIco} {FlairRightIco}\n" + 
                        f"> Kills - {df['Kills'].sum()}\n" +
                        f"> Deaths - {df['Deaths'].sum()}\n" +
                        f"> KDR - {(df['Kills'].sum() / df['Deaths'].sum()):.2f}\n" +
                        f"> Highest Kills in Mission - {df['Kills'].max()}\n" +

                        f"\n{FlairLeftIco}  {FlairSEIco} Mission Statistics {FlairSEIco} {FlairRightIco}\n" + 
                        f"> Deployments - {len(df)}\n" +
                        f"> Major Order Deployments - {df['Major Order'].astype(int).sum()}\n" +
                        f"> DSS Deployments - {df['DSS Active'].astype(int).sum()}\n" +
                        f"> Mega City Deployments - {mega_city_count}\n" +
                        f"> First Deployment - {get_first_deployment(df, df['Enemy Type'].mode().iloc[0])}\n" +

                        f"\n{FlairLeftIco}  {FlairGSSkullIco} Performance Statistics {FlairGSSkullIco} {FlairRightIco}\n" +                      
                        f"> Rating - {Rating} | {int(Rating_Percentage)}%\n" +
                        f"> Highest Streak - {highest_streak} Missions\n" +

                        f"\n{FlairLeftIco}  {GoldStarIco} Favourites {GoldStarIco} {FlairRightIco}\n" +     
                        f"> Mission - {df['Mission Type'].mode().iloc[0]} {MISSION_ICONS.get(df['Mission Type'].mode().iloc[0], '')} (x{MissionCount})\n" +
                        f"> Campaign - {df['Mission Category'].mode().iloc[0]} {CAMPAIGN_ICONS.get(df['Mission Category'].mode().iloc[0], '')} (x{CampaignCount})\n" +
                        f"> Faction - {df['Enemy Type'].mode().iloc[0]} {ENEMY_ICONS.get(df['Enemy Type'].mode().iloc[0], '')} (x{FactionCount})\n" +
                        f"> Subfaction - {df['Enemy Subfaction'].mode().iloc[0]} {SUBFACTION_ICONS.get(df['Enemy Subfaction'].mode().iloc[0], '')} (x{SubfactionCount})\n"
                        f"> Difficulty - {df['Difficulty'].mode().iloc[0]} {DIFFICULTY_ICONS.get(df['Difficulty'].mode().iloc[0], '')} (x{DifficultyCount})\n" +
                        f"> Planet - {df['Planet'].mode().iloc[0]} {PLANET_ICONS.get(df['Planet'].mode().iloc[0], '')} (x{PlanetCount})\n" +
                        f"> Sector - {df['Sector'].mode().iloc[0]} (x{SectorCount})\n",
            "color": 7257043,
            "author": {
                        "name": f"SEAF Faction Record\nDate: {date}",
                        "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356001307596427564/NwNzS9B.png?ex=67eafa21&is=67e9a8a1&hm=7e204265cbcdeaf96d7b244cd63992c4ef10dc18befbcf2ed39c3a269af14ec0&"
                    },
            "footer": {"text": f"{discord_data['discord_uid']}   v{VERSION}{DEV_RELEASE}","icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356025859319926784/5cwgI15.png?ex=67eb10fe&is=67e9bf7e&hm=ab6326a9da1e76125238bf3668acac8ad1e43b24947fc6d878d7b94c8a60ab28&"},
            "image": {"url": f"{BIOME_BANNERS.get(df['Planet'].mode().iloc[0], '')}"},
            "thumbnail": {"url": f"{profile_picture}"}
        },
        {
      "title": "Terminids Campaign Record",
      "description": f"{FlairLeftIco} {BugIco} Terminid Front Statistics {BugIco} {FlairRightIco}\n" +
                         f"> {KillIco} Kills - {df[df['Enemy Type'] == 'Terminids']['Kills'].sum()}\n" +
                         f"> {DeathIco} Deaths - {df[df['Enemy Type'] == 'Terminids']['Deaths'].sum()}\n" +
                         f"> {KDRIco} KDR - {(df[df['Enemy Type'] == 'Terminids']['Kills'].sum() / df[df['Enemy Type'] == 'Terminids']['Deaths'].sum()):.2f}\n" +
                         f"> {HighestKillIco} Highest Kills in Mission - {df[df['Enemy Type'] == 'Terminids']['Kills'].max()}\n\n" +

                         f"> {DeployIco} Deployments - {df[df['Enemy Type'] == 'Terminids']['Enemy Type'].count().sum()}\n" +
                         f"> {MODeployIco} Major Order Deployments - {df[df['Enemy Type'] == 'Terminids']['Major Order'].astype(int).sum()}\n" +
                         f"> {DSSDeployIco} DSS Deployments - {df[df['Enemy Type'] == 'Terminids']['DSS Active'].astype(int).sum()}\n" +
                         f"> {BugMCDeployIco} Mega City Deployments - {terminids_mega_city_count}\n" +
                         f"> {LastDeployIco} Last Deployment - {get_last_deployment(df, 'Terminids')}\n\n" +

                         f"> {LiberationIco} Liberations - {df[df['Enemy Type'] == 'Terminids'][df['Mission Category'] == 'Liberation']['Mission Category'].count().sum()}\n" +
                         f"> {DefenceIco} Defenses - {df[df['Enemy Type'] == 'Terminids'][df['Mission Category'] == 'Defense']['Mission Category'].count().sum()}\n" +
                         f"> {InvasionIco} Invasion - {df[df['Enemy Type'] == 'Terminids'][df['Mission Category'] == 'Invasion']['Mission Category'].count().sum()}\n" +
                         f"> {HighPriorityIco} High-Priority - {df[df['Enemy Type'] == 'Terminids'][df['Mission Category'] == 'High-Priority']['Mission Category'].count().sum()}\n" +
                         f"> {AttritionIco} Attrition - {df[df['Enemy Type'] == 'Terminids'][df['Mission Category'] == 'Attrition']['Mission Category'].count().sum()}\n" +
                         f"> {InvasionIco} Battle for Super Earth - {df[df['Enemy Type'] == 'Terminids'][df['Mission Category'] == 'Battle for Super Earth']['Mission Category'].count().sum()}\n\n",
      
      "color": 16761088,
      "image": {
        "url": "https://cdn.discordapp.com/attachments/1340508329977446484/1370786767128760420/terminidBanner.png?ex=6820c429&is=681f72a9&hm=3ca1e122e8063426a3dd1963791aca33ba6343a7a946b06287d344ce6c0f93a0&"
      },
      "thumbnail": {
        "url": "https://i.ibb.co/PspGgJkH/Terminids-Icon.png"
      }
    },
    {
      "title": "Automaton Campaign Record",
      "description": f"{FlairLeftIco} {BotIco} Automaton Front Statistics {BotIco} {FlairRightIco}\n" +
                         f"> {KillIco} Kills - {df[df['Enemy Type'] == 'Automatons']['Kills'].sum()}\n" +
                         f"> {DeathIco} Deaths - {df[df['Enemy Type'] == 'Automatons']['Deaths'].sum()}\n" +
                         f"> {KDRIco} KDR - {(df[df['Enemy Type'] == 'Automatons']['Kills'].sum() / df[df['Enemy Type'] == 'Automatons']['Deaths'].sum()):.2f}\n" +
                         f"> {HighestKillIco} Highest Kills in Mission - {df[df['Enemy Type'] == 'Automatons']['Kills'].max()}\n\n" +

                         f"> {DeployIco} Deployments - {df[df['Enemy Type'] == 'Automatons']['Enemy Type'].count().sum()}\n" +
                         f"> {MODeployIco} Major Order Deployments - {df[df['Enemy Type'] == 'Automatons']['Major Order'].astype(int).sum()}\n" +
                         f"> {DSSDeployIco} DSS Deployments - {df[df['Enemy Type'] == 'Automatons']['DSS Active'].astype(int).sum()}\n" +
                         f"> {BotMCDeployIco} Mega City Deployments - {automatons_mega_city_count}\n" +
                         f"> {LastDeployIco} Last Deployment - {get_last_deployment(df, 'Automatons')}\n\n" +

                         f"> {LiberationIco} Liberations - {df[df['Enemy Type'] == 'Automatons'][df['Mission Category'] == 'Liberation']['Mission Category'].count().sum()}\n" +
                         f"> {DefenceIco} Defenses - {df[df['Enemy Type'] == 'Automatons'][df['Mission Category'] == 'Defense']['Mission Category'].count().sum()}\n" +
                         f"> {InvasionIco} Invasion - {df[df['Enemy Type'] == 'Automatons'][df['Mission Category'] == 'Invasion']['Mission Category'].count().sum()}\n" +
                         f"> {HighPriorityIco} High-Priority - {df[df['Enemy Type'] == 'Automatons'][df['Mission Category'] == 'High-Priority']['Mission Category'].count().sum()}\n" +
                         f"> {AttritionIco} Attrition - {df[df['Enemy Type'] == 'Automatons'][df['Mission Category'] == 'Attrition']['Mission Category'].count().sum()}\n" +
                         f"> {InvasionIco} Battle for Super Earth - {df[df['Enemy Type'] == 'Automatons'][df['Mission Category'] == 'Battle for Super Earth']['Mission Category'].count().sum()}\n\n",

      "color": 16739693,
      "image": {
        "url": "https://cdn.discordapp.com/attachments/1340508329977446484/1370786778465964193/automatonBanner.png?ex=6820c42b&is=681f72ab&hm=63213a37d29cfc25661737c7d20867ebea272fffc9e830116c32ef7df3cf1a24&"
      },
      "thumbnail": {
        "url": "https://i.ibb.co/bgNp2q73/Automatons-Icon.png"
      }
    },
    {
      "title": "Illuminate Campaign Record",
      "description": f"{FlairLeftIco} {SquidIco} Illuminate Cult Statistics {SquidIco} {FlairRightIco}\n" +
                         f"> {KillIco} Kills - {df[df['Enemy Type'] == 'Illuminate']['Kills'].sum()}\n" +
                         f"> {DeathIco} Deaths - {df[df['Enemy Type'] == 'Illuminate']['Deaths'].sum()}\n" +
                         f"> {KDRIco} KDR - {(df[df['Enemy Type'] == 'Illuminate']['Kills'].sum() / df[df['Enemy Type'] == 'Illuminate']['Deaths'].sum()):.2f}\n" +
                         f"> {HighestKillIco} Highest Kills in Mission - {df[df['Enemy Type'] == 'Illuminate']['Kills'].max()}\n\n" +

                         f"> {DeployIco} Deployments - {df[df['Enemy Type'] == 'Illuminate']['Enemy Type'].count().sum()}\n" +
                         f"> {MODeployIco} Major Order Deployments - {df[df['Enemy Type'] == 'Illuminate']['Major Order'].astype(int).sum()}\n" +
                         f"> {DSSDeployIco} DSS Deployments - {df[df['Enemy Type'] == 'Illuminate']['DSS Active'].astype(int).sum()}\n" +
                         f"> {SquidMCDeployIco} Mega City Deployments - {illuminate_mega_city_count}\n" +
                         f"> {LastDeployIco} Last Deployment - {get_last_deployment(df, 'Illuminate')}\n\n" +

                         f"> {LiberationIco} Liberations - {df[df['Enemy Type'] == 'Illuminate'][df['Mission Category'] == 'Liberation']['Mission Category'].count().sum()}\n" +
                         f"> {DefenceIco} Defenses - {df[df['Enemy Type'] == 'Illuminate'][df['Mission Category'] == 'Defense']['Mission Category'].count().sum()}\n" +
                         f"> {InvasionIco} Invasion - {df[df['Enemy Type'] == 'Illuminate'][df['Mission Category'] == 'Invasion']['Mission Category'].count().sum()}\n" +
                         f"> {HighPriorityIco} High-Priority - {df[df['Enemy Type'] == 'Illuminate'][df['Mission Category'] == 'High-Priority']['Mission Category'].count().sum()}\n" +
                         f"> {AttritionIco} Attrition - {df[df['Enemy Type'] == 'Illuminate'][df['Mission Category'] == 'Attrition']['Mission Category'].count().sum()}\n" +
                         f"> {InvasionIco} Battle for Super Earth - {df[df['Enemy Type'] == 'Illuminate'][df['Mission Category'] == 'Battle for Super Earth']['Mission Category'].count().sum()}\n\n",

      "color": 9003210,
      "image": {
        "url": "https://cdn.discordapp.com/attachments/1340508329977446484/1370786787441774632/illuminateBanner.png?ex=6820c42e&is=681f72ae&hm=bc4d9e9f89bcae58521b9af1558816ecb0c336bee108862725663b87e5bb6079&"
      },
      "thumbnail": {
        "url": "https://i.ibb.co/wr4Nm5HT/Illuminate-Icon.png"
      }
    }
    ],
    "attachments": []
}

# Update the embed title with name and level
embed_data["embeds"][0]["title"] = f"{helldiver_ses}\nHelldiver: {helldiver_name}\n{bicon}{ticon}{yearico}{PIco}{bsuperearth}{bcyberstan}{bmaleveloncreek}{bcalypso}{bpopliix}{bseyshelbeach}{boshaune}"

# Enemy type specific embeds with icons
enemy_icons = {
    "Automatons": {
        "emoji": iconconfig['EnemyIcons']['Automatons'],
        "color": int(iconconfig['SystemColors']['Automatons']),
        "url": "https://i.ibb.co/bgNp2q73/Automatons-Icon.png"
    },
    "Terminids": {
        "emoji": iconconfig['EnemyIcons']['Terminids'],
        "color": int(iconconfig['SystemColors']['Terminids']),
        "url": "https://i.ibb.co/PspGgJkH/Terminids-Icon.png"
    },
    "Illuminate": {
        "emoji": iconconfig['EnemyIcons']['Illuminate'],
        "color": int(iconconfig['SystemColors']['Illuminate']),
        "url": "https://i.ibb.co/wr4Nm5HT/Illuminate-Icon.png"
    }
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
    }
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
            "planets": faction_data["Planet"].unique().tolist()
        }

if DEBUG:
    webhook_urls = [config['Webhooks']['TEST']] # Use the webhook URL from the config for debugging
else:
    # Load webhook URLs from DCord.json
    with open(app_path('JSON', 'DCord.json'), 'r') as f:
        discord_data = json.load(f)
        webhook_urls = discord_data.get('discord_webhooks_export', [])
        webhook_urls = [
            (w.get('url') if isinstance(w, dict) else str(w)).strip()
            for w in webhook_urls
            if (isinstance(w, dict) and str(w.get('url','')).strip()) or (isinstance(w, str) and w.strip())
        ]

# Send data to each webhook
for webhook_url in webhook_urls:
    response = requests.post(webhook_url, json=embed_data)
    if response.status_code == 204:
        logging.info("Data sent successfully.")
    else:
        logging.error(f"Failed to send data. Status: {response.status_code}")
