import pandas as pd
import logging
import configparser  
import requests
import json
from datetime import datetime, timezone, timedelta
import os
import sys

# Ensure we can import from the project root when running directly
if __name__ == '__main__':
    # Add the project root to the Python path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from core.logging_config import setup_logging
from core.runtime_paths import app_path
from core.icon import ENEMY_ICONS, DIFFICULTY_ICONS, PLANET_ICONS, CAMPAIGN_ICONS, MISSION_ICONS, BIOME_BANNERS, SUBFACTION_ICONS, TITLE_ICONS, get_badge_icons, get_planet_image
from core.app_core import VERSION, DEV_RELEASE

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
rating_mapping = {"Gallantry Beyond Measure": 5, "Outstanding Patriotism": 5, "Truly Exceptional Heroism": 4, "Superior Valour": 4, "Costly Failure": 4, "Honourable Duty":3, "Unremarkable Performance":2, "Dissapointing Service":1, "Disgraceful Conduct":0}
# Calculate total rating
total_rating = sum(rating_mapping[row["Rating"]] for index, row in df.iterrows() if "Rating" in df.columns and row["Rating"] in rating_mapping)
Rating_Percentage = (total_rating / max_rating) * 100

# Get the user's name and level from the last row of the DataFrame
helldiver_ses = df['Super Destroyer'].iloc[-1] if 'Super Destroyer' in df.columns else "Unknown"
helldiver_name = df['Helldivers'].iloc[-1] if 'Helldivers' in df.columns else "Unknown"
helldiver_level = df['Level'].iloc[-1] if 'Level' in df.columns else 0
helldiver_title = df['Title'].iloc[-1] if 'Title' in df.columns else "Unknown"
# Get the current planet from command line argument or fallback to most recent from Excel
import sys
if len(sys.argv) > 1:
    current_planet = sys.argv[1]
else:
    current_planet = df['Planet'].iloc[-1] if 'Planet' in df.columns else "Unknown"
planet_thumbnail = get_planet_image(current_planet)

if DEBUG:
    webhook_urls = [config['Webhooks']['TEST']] # Use the webhook URL from the config for debugging
else:
    # Load webhook URLs from DCord.json
    with open(app_path('JSON', 'DCord.json'), 'r') as f:
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

# Returns last deployment timestamp for an enemy; affects observation embed stats
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

# Returns first deployment timestamp for an enemy; affects observation embed stats
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

# Fetches icon URL for a planet; affects observation planet thumbnail
def _get_planet_icon(planet: str) -> str:
    return PLANET_ICONS.get(planet, "")

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

# Get value counts for each category
mission_counts = df['Mission Type'].value_counts()
campaign_counts = df['Mission Category'].value_counts()
faction_counts = df['Enemy Type'].value_counts()
subfaction_counts = df['Enemy Subfaction'].value_counts()
difficulty_counts = df['Difficulty'].value_counts()
planet_counts = df['Planet'].value_counts()
sector_counts = df['Sector'].value_counts()

SEIco = iconconfig['MiscIcon'].get('Super Earth Icon', '') if 'MiscIcon' in iconconfig else ''
planet_icon = _get_planet_icon(current_planet)
if planet_icon == '':
            planet_icon = f"{SEIco}"

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
DeathIco = iconconfig['MiscIcon']['Deaths']
GoldStarIco = iconconfig['Stars']['GoldStar']
KillIco = iconconfig['MiscIcon']['Kills']
KDRIco = iconconfig['MiscIcon']['KDR']

# Calculate success/failure rates for current planet
current_planet_data = df[df['Planet'] == current_planet] if current_planet in df['Planet'].values else pd.DataFrame()
if not current_planet_data.empty:
    planet_total_missions = len(current_planet_data)
    planet_failed_missions = len(current_planet_data[current_planet_data['Rating'] == 'Disgraceful Conduct'])
    planet_success_missions = planet_total_missions - planet_failed_missions
    
    # Calculate percentages
    planet_success_percentage = (planet_success_missions / planet_total_missions * 100) if planet_total_missions > 0 else 0
    planet_failure_percentage = (planet_failed_missions / planet_total_missions * 100) if planet_total_missions > 0 else 0
    
    # Calculate KDR for current planet
    planet_total_kills = current_planet_data['Kills'].sum() if 'Kills' in current_planet_data.columns else 0
    planet_total_deaths = current_planet_data['Deaths'].sum() if 'Deaths' in current_planet_data.columns else 0
    planet_kdr = planet_total_kills / planet_total_deaths if planet_total_deaths > 0 else planet_total_kills
    
    # Calculate faction-specific kills for current planet
    planet_faction_kills = {}
    for faction in ['Automatons', 'Terminids', 'Illuminate']:
        faction_data = current_planet_data[current_planet_data['Enemy Type'] == faction]
        if not faction_data.empty:
            planet_faction_kills[faction] = faction_data['Kills'].sum() if 'Kills' in faction_data.columns else 0
    
    # Calculate Helldiver deaths (total deaths on planet)
    planet_helldiver_deaths = planet_total_deaths
    
    # Get the sector for the current planet
    current_planet_sector = current_planet_data['Sector'].iloc[0] if 'Sector' in current_planet_data.columns and not current_planet_data.empty else "Unknown"
    
    # Calculate highest kills in a single mission on current planet
    planet_highest_kills = current_planet_data['Kills'].max() if 'Kills' in current_planet_data.columns and not current_planet_data.empty else 0
    
    # Calculate first deployment on current planet
    if 'Time' in current_planet_data.columns and not current_planet_data.empty:
        times_raw = current_planet_data['Time'].astype(str).str.strip()
        times_normalized = times_raw.str.replace('/', '-', regex=False)
        times_parsed = pd.to_datetime(times_normalized, format='%d-%m-%Y %H:%M:%S', errors='coerce')
        if times_parsed.isna().all():
            times_parsed = pd.to_datetime(times_normalized, errors='coerce', dayfirst=True)
        valid_times = times_parsed.dropna()
        planet_first_deployment = valid_times.min().strftime('%d-%m-%Y %H:%M:%S') if not valid_times.empty else 'No deployments'
        planet_last_deployment = valid_times.max().strftime('%d-%m-%Y %H:%M:%S') if not valid_times.empty else 'No deployments'
    else:
        planet_first_deployment = 'No deployments'
        planet_last_deployment = 'No deployments'
    
    # Calculate most common mission type on current planet
    planet_most_common_mission = current_planet_data['Mission Type'].mode().iloc[0] if 'Mission Type' in current_planet_data.columns and not current_planet_data.empty and not current_planet_data['Mission Type'].mode().empty else 'Unknown'
    
    # Calculate most common mission category on current planet
    planet_most_common_category = current_planet_data['Mission Category'].mode().iloc[0] if 'Mission Category' in current_planet_data.columns and not current_planet_data.empty and not current_planet_data['Mission Category'].mode().empty else 'Unknown'
    
    # Calculate most common faction on current planet
    planet_most_common_faction = current_planet_data['Enemy Type'].mode().iloc[0] if 'Enemy Type' in current_planet_data.columns and not current_planet_data.empty and not current_planet_data['Enemy Type'].mode().empty else 'Unknown'
    
    # Calculate most common subfaction on current planet
    planet_most_common_subfaction = current_planet_data['Enemy Subfaction'].mode().iloc[0] if 'Enemy Subfaction' in current_planet_data.columns and not current_planet_data.empty and not current_planet_data['Enemy Subfaction'].mode().empty else 'Unknown'
    
    # Calculate most common difficulty on current planet
    planet_most_common_difficulty = current_planet_data['Difficulty'].mode().iloc[0] if 'Difficulty' in current_planet_data.columns and not current_planet_data.empty and not current_planet_data['Difficulty'].mode().empty else 'Unknown'
    
    # Calculate instance counts for each field on current planet
    planet_mission_count = len(current_planet_data[current_planet_data['Mission Type'] == planet_most_common_mission]) if planet_most_common_mission != 'Unknown' else 0
    planet_category_count = len(current_planet_data[current_planet_data['Mission Category'] == planet_most_common_category]) if planet_most_common_category != 'Unknown' else 0
    planet_faction_count = len(current_planet_data[current_planet_data['Enemy Type'] == planet_most_common_faction]) if planet_most_common_faction != 'Unknown' else 0
    planet_subfaction_count = len(current_planet_data[current_planet_data['Enemy Subfaction'] == planet_most_common_subfaction]) if planet_most_common_subfaction != 'Unknown' else 0
    planet_difficulty_count = len(current_planet_data[current_planet_data['Difficulty'] == planet_most_common_difficulty]) if planet_most_common_difficulty != 'Unknown' else 0
    
    # Calculate planet index (order of first appearance in mission log)
    planet_index = planets.index(current_planet) + 1 if current_planet in planets else 0
else:
    planet_total_missions = 0
    planet_failed_missions = 0
    planet_success_missions = 0
    planet_success_percentage = 0
    planet_failure_percentage = 0
    planet_total_kills = 0
    planet_total_deaths = 0
    planet_kdr = 0
    planet_faction_kills = {}
    planet_helldiver_deaths = 0
    current_planet_sector = "Unknown"
    planet_highest_kills = 0
    planet_first_deployment = 'No deployments'
    planet_last_deployment = 'No deployments'
    planet_most_common_mission = 'Unknown'
    planet_most_common_category = 'Unknown'
    planet_most_common_faction = 'Unknown'
    planet_most_common_subfaction = 'Unknown'
    planet_most_common_difficulty = 'Unknown'
    planet_mission_count = 0
    planet_category_count = 0
    planet_faction_count = 0
    planet_subfaction_count = 0
    planet_difficulty_count = 0
    planet_index = 0

# Build dynamic faction kill lines (only show factions fought on this planet)
faction_kill_lines = ""
faction_icons = {'Automatons': ENEMY_ICONS.get('Automatons', ''), 'Terminids': ENEMY_ICONS.get('Terminids', ''), 'Illuminate': ENEMY_ICONS.get('Illuminate', '')}
for faction, kills in planet_faction_kills.items():
    if kills > 0:  # Only show if user has kills against this faction on this planet
        faction_kill_lines += f"> Dead {faction} - {kills} {faction_icons[faction]}\n"

# Add Helldiver deaths if there are any
if planet_helldiver_deaths > 0:
    faction_kill_lines += f"> Dead Helldivers - {planet_helldiver_deaths} {DeathIco}\n\n"

# No deployments on this planet - show reconnaissance message
# Load planet status data
with open(app_path('JSON', 'PlanetStatus.json'), 'r') as f:
    planet_status_data = json.load(f)
# Determine planet status
planet_status = "UNKNOWN STATUS"
status_category = None
for category, data in planet_status_data.items():
    if current_planet in data.get('planets', []):
        status_category = category
        if category == "Contested/Controlled Environment":
            planet_status = "**CONTROLLED/CONTESTED**"
        elif category == "Uncharted Territory":
            planet_status = "**UNCHARTED TERRITORY**"
        elif category == "Lost Connection":
            planet_status = "**LOST CONNECTION**"
        break

# Create embed data
# Check if user has deployed on this planet (excluding special planets)
if (current_planet_data.empty or planet_total_missions == 0) and current_planet not in ["Meridia", "Angel's Venture", "Moradesh", "Ivis"]:
    embed_description = f"**Level {helldiver_level} | {helldiver_title} {TITLE_ICONS.get(df['Title'].iloc[-1], '')}**\n\n{FlairLeftIco} {SEIco} **Reconnaissance Report** {SEIco} {FlairRightIco}\n" + \
                      f"> Planet - {current_planet} {PLANET_ICONS.get(current_planet, '')}\n" + \
                      f"> Status - **{planet_status}**\n\n" + \
                      f"**INCOMING MESSAGES FROM SUPER EARTH**\n" + \
                      f"> You have yet to make contact with this planet.\n" + \
                      f"> No tactical data available for analysis.\n" + \
                      f"> Deploy on **{current_planet}** to begin reconnaissance operations.\n" + \
                      f"> Super Earth High Command awaits your first report, Helldiver.\n\n"
elif current_planet == "Meridia":
    embed_description = f"**Level {helldiver_level} | {helldiver_title} {TITLE_ICONS.get(df['Title'].iloc[-1], '')}**\n\n{FlairLeftIco} {SEIco} **Reconnaissance Report** {SEIco} {FlairRightIco}\n" + \
                      f"> Planet - {current_planet} {PLANET_ICONS.get(current_planet, '')}\n" + \
                      f"> Status - **{planet_status}**\n\n" + \
                      f"**INCOMING MESSAGES FROM SUPER EARTH**\n" + \
                      f"> Contact with the **Meridian Singularity** {PLANET_ICONS.get(current_planet, '')} is not available.\n" + \
                      f"> Detail from **Operation Enduring Peace** was\n" + \
                      f"> not saved from the planetary implosion.\n" + \
                      f"> Please await further orders from Super Earth High Command, Helldiver.\n\n"
elif current_planet == "Angel's Venture":
    embed_description = f"**Level {helldiver_level} | {helldiver_title} {TITLE_ICONS.get(df['Title'].iloc[-1], '')}**\n\n{FlairLeftIco} {SEIco} **Reconnaissance Report** {SEIco} {FlairRightIco}\n" + \
                      f"> Planet - {current_planet} {PLANET_ICONS.get(current_planet, '')}\n" + \
                      f"> Status - **{planet_status}**\n\n" + \
                      f"**INCOMING MESSAGES FROM SUPER EARTH**\n" + \
                      f"> We have lost contact with **{current_planet}** {PLANET_ICONS.get(current_planet, '')}.\n" + \
                      f"> Detail from **Operation Ink & Thunder** was\n" + \
                      f"> not saved during the fracture from the Meridian Singularity {PLANET_ICONS.get('Meridia', '')}.\n" + \
                      f"> Please await further orders from Super Earth High Command, Helldiver.\n\n"
elif current_planet == "Moradesh":
    embed_description = f"**Level {helldiver_level} | {helldiver_title} {TITLE_ICONS.get(df['Title'].iloc[-1], '')}**\n\n{FlairLeftIco} {SEIco} **Reconnaissance Report** {SEIco} {FlairRightIco}\n" + \
                      f"> Planet - {current_planet} {PLANET_ICONS.get(current_planet, '')}\n" + \
                      f"> Status - **{planet_status}**\n\n" + \
                      f"**INCOMING MESSAGES FROM SUPER EARTH**\n" + \
                      f"> We have lost contact with **{current_planet}** {PLANET_ICONS.get(current_planet, '')}.\n" + \
                      f"> Detail from **Operation Black Hole Sun** was\n" + \
                      f"> not saved during the fracture from the Meridian Singularity {PLANET_ICONS.get('Meridia', '')}.\n" + \
                      f"> Please await further orders from Super Earth High Command, Helldiver.\n\n"
elif current_planet == "Ivis":
    embed_description = f"**Level {helldiver_level} | {helldiver_title} {TITLE_ICONS.get(df['Title'].iloc[-1], '')}**\n\n{FlairLeftIco} {SEIco} **Reconnaissance Report** {SEIco} {FlairRightIco}\n" + \
                      f"> Planet - {current_planet} {PLANET_ICONS.get(current_planet, '')}\n" + \
                      f"> Status - **{planet_status}**\n\n" + \
                      f"**INCOMING MESSAGES FROM SUPER EARTH**\n" + \
                      f"> We have lost contact with **{current_planet}** {PLANET_ICONS.get(current_planet, '')}.\n" + \
                      f"> Detail from **Operation Martyr's Calling** was\n" + \
                      f"> not saved during the fracture from the Meridian Singularity {PLANET_ICONS.get('Meridia', '')}.\n" + \
                      f"> Please await further orders from Super Earth High Command, Helldiver.\n\n"
else:
    # Normal planet statistics for deployed planets
    embed_description = f"**Level {helldiver_level} | {helldiver_title} {TITLE_ICONS.get(df['Title'].iloc[-1], '')}**\n\n{FlairLeftIco} {SEIco} **Galactic Intel** {SEIco} {FlairRightIco}\n" + \
                        f"> Planet - {current_planet} {PLANET_ICONS.get(current_planet, '')}\n" + \
                        f"> Sector - {current_planet_sector}\n" + \
                        f"> Index - {planet_index}\n" + \
                        f"> Missions Completed - {planet_success_missions} ({planet_success_percentage:.1f}%)\n" + \
                        f"> Missions Failed - {planet_failed_missions} ({planet_failure_percentage:.1f}%)\n" + \
                        f"> First Contact - {planet_first_deployment}\n" + \
                        f"> Last Deployment - {planet_last_deployment}\n\n" + \
                        f"{FlairLeftIco} {KillIco} **Combat Intel** {KDRIco} {FlairRightIco}\n" + \
                        f"> Kill to Death Ratio - {planet_total_kills} : {planet_total_deaths}\n" + \
                        f"> Highest Kills in Mission - {planet_highest_kills}\n" + \
                        faction_kill_lines + \
                        f"{FlairLeftIco} {GoldStarIco} **Priority Intel** {GoldStarIco} {FlairRightIco}\n" + \
                        f"> Mission - {planet_most_common_mission} {MISSION_ICONS.get(planet_most_common_mission, '')} (x{planet_mission_count})\n" + \
                        f"> Campaign - {planet_most_common_category} {CAMPAIGN_ICONS.get(planet_most_common_category, '')} (x{planet_category_count})\n" + \
                        f"> Faction - {planet_most_common_faction} {ENEMY_ICONS.get(planet_most_common_faction, '')} (x{planet_faction_count})\n" + \
                        f"> Subfaction - {planet_most_common_subfaction} {SUBFACTION_ICONS.get(planet_most_common_subfaction, '')} (x{planet_subfaction_count})\n" + \
                        f"> Difficulty - {planet_most_common_difficulty} {DIFFICULTY_ICONS.get(planet_most_common_difficulty, '')} (x{planet_difficulty_count})\n\n"

embed_data = {
    "content": None,
    "embeds": [
        {
            "title": "",  # Empty title, will be set below
            "description": embed_description,                        
            "color": 7257043,
            "author": {
                        "name": f"SEAF Planetary Observation Record\nDate: {date}",
                        "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356001307596427564/NwNzS9B.png?ex=67eafa21&is=67e9a8a1&hm=7e204265cbcdeaf96d7b244cd63992c4ef10dc18befbcf2ed39c3a269af14ec0&"
                    },
            "footer": {"text": f"{discord_data['discord_uid']}   v{VERSION}{DEV_RELEASE}","icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356025859319926784/5cwgI15.png?ex=67eb10fe&is=67e9bf7e&hm=ab6326a9da1e76125238bf3668acac8ad1e43b24947fc6d878d7b94c8a60ab28&"},
            "image": {"url": f"{BIOME_BANNERS.get(current_planet, iconconfig['BiomeBanners'].get('Super Earth', ''))}"},
            "thumbnail": {"url": f"{planet_thumbnail}"}
        }
    ],
    "attachments": []
}

# Update the embed title with name and level
embed_data["embeds"][0]["title"] = f"{helldiver_ses}\nHelldiver: {helldiver_name}\n{bicon}{ticon}{yearico}{PIco}{bsuperearth}{bcyberstan}{bmaleveloncreek}{bcalypso}{bpopliix}{bseyshelbeach}{boshaune}"

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
