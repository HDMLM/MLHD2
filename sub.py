import pandas as pd
import logging
from logging_config import setup_logging
import configparser
import requests
import json
import os
import html as html_lib
from datetime import datetime, timezone, timedelta
from icon import ENEMY_ICONS, DIFFICULTY_ICONS, PLANET_ICONS, CAMPAIGN_ICONS, MISSION_ICONS, BIOME_BANNERS, SUBFACTION_ICONS, TITLE_ICONS
from main import VERSION, DEV_RELEASE


# Set up application data paths 
APP_DATA = os.path.join(os.getenv('LOCALAPPDATA'), 'MLHD2')
if not os.path.exists(APP_DATA):
    os.makedirs(APP_DATA)

EXCEL_FILE_PROD = os.path.join(APP_DATA, 'mission_log.xlsx')
EXCEL_FILE_TEST = os.path.join(APP_DATA, 'mission_log_test.xlsx')
DATE_FORMAT = "%d-%m-%Y %H:%M:%S"

# Read configuration from config.config
config = configparser.ConfigParser()
config.read('config.config')
iconconfig = configparser.ConfigParser()
iconconfig.read('icon.config')

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
            messagebox.showerror("Export Error", "Have you even left Super Earth? No missions found in the log.")
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
search_mega_city = df['Mega City'].mode()[0]
MegaCityCount = df.apply(lambda row: row.astype(str).str.contains(search_mega_city, case=False).sum(), axis=1).sum()
search_sector = df['Sector'].mode()[0]
SectorCount = df.apply(lambda row: row.astype(str).str.contains(search_sector, case=False).sum(), axis=1).sum()

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
    
def _build_primary_embed_description() -> str:
    """Compose the primary embed description (kept modular so we can reuse in HTML)."""
    # Calculate Mega City deployments excluding "Planet Surface" and empty values
    mega_city_count = df[df['Mega City'].fillna('').astype(str).apply(lambda x: x != '' and x.lower() != 'planet surface')].shape[0]

    return (
        f"**Level {helldiver_level} | {helldiver_title} {TITLE_ICONS.get(df['Title'].iloc[-1], '')}**\n\n"
        f"\"{latest_note}\"\n\n"
        f"<a:easyshine1:1349110651829747773>  <a:easyshine2:1349110649753698305> Combat Statistics <a:easyshine2:1349110649753698305> <a:easyshine3:1349110648528699422>\n"
        f"> Kills - {df['Kills'].sum()}\n"
        f"> Deaths - {df['Deaths'].sum()}\n"
        f"> KDR - {(df['Kills'].sum() / df['Deaths'].sum()):.2f}\n"
        f"> Highest Kills in Mission - {df['Kills'].max()}\n"
        f"\n<a:easyshine1:1349110651829747773>  <a:easysuperearth:1343266082881802443> Mission Statistics <a:easysuperearth:1343266082881802443> <a:easyshine3:1349110648528699422>\n"
        f"> Deployments - {len(df)}\n"
        f"> Major Order Deployments - {df['Major Order'].astype(int).sum()}\n"
        f"> DSS Deployments - {df['DSS Active'].astype(int).sum()}\n"
        f"> Mega City Deployments - {mega_city_count}\n"
    f"> First Deployment - {get_first_deployment(df, df['Enemy Type'].mode().iloc[0])}\n"
        f"\n<a:easyshine1:1349110651829747773>  <a:easyskullgold:1232018045791375360> Performance Statistics <a:easyskullgold:1232018045791375360> <a:easyshine3:1349110648528699422>\n"
        f"> Rating - {Rating} | {int(Rating_Percentage)}%\n"
        f"> Highest Streak - {highest_streak} Missions\n"
        f"\n<a:easyshine1:1349110651829747773>  <:goldstar:1337818552094163034> Favourites <:goldstar:1337818552094163034> <a:easyshine3:1349110648528699422>\n"
    f"> Mission - {df['Mission Type'].mode().iloc[0]} {MISSION_ICONS.get(df['Mission Type'].mode().iloc[0], '')} (x{MissionCount})\n"
    f"> Campaign - {df['Mission Category'].mode().iloc[0]} {CAMPAIGN_ICONS.get(df['Mission Category'].mode().iloc[0], '')} (x{CampaignCount})\n"
    f"> Faction - {df['Enemy Type'].mode().iloc[0]} {ENEMY_ICONS.get(df['Enemy Type'].mode().iloc[0], '')} (x{FactionCount})\n"
    f"> Subfaction - {df['Enemy Subfaction'].mode().iloc[0]} {SUBFACTION_ICONS.get(df['Enemy Subfaction'].mode().iloc[0], '')} (x{SubfactionCount})\n"
    f"> Difficulty - {df['Difficulty'].mode().iloc[0]} {DIFFICULTY_ICONS.get(df['Difficulty'].mode().iloc[0], '')} (x{DifficultyCount})\n"
    f"> Planet - {df['Planet'].mode().iloc[0]} {PLANET_ICONS.get(df['Planet'].mode().iloc[0], '')} (x{PlanetCount})\n"
    f"> Sector - {df['Sector'].mode().iloc[0]} (x{SectorCount})\n"
    )

primary_description = _build_primary_embed_description()

# Create embed data (initial)
embed_data = {
    "content": None,
    "embeds": [
        {
            "title": "",  # Will set below
            "description": primary_description,
            "color": 7257043,
            "author": {
                        "name": f"SEAF Planetary Record\nDate: {date}",
                        "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356001307596427564/NwNzS9B.png?ex=67eafa21&is=67e9a8a1&hm=7e204265cbcdeaf96d7b244cd63992c4ef10dc18befbcf2ed39c3a269af14ec0&"
                    },
            "footer": {"text": dcord_data['discord_uid'],"icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356025859319926784/5cwgI15.png?ex=67eb10fe&is=67e9bf7e&hm=ab6326a9da1e76125238bf3668acac8ad1e43b24947fc6d878d7b94c8a60ab28&"},
            "image": {"url": f"{BIOME_BANNERS.get(df['Planet'].mode().iloc[0], '')}"},
            "thumbnail": {"url": f"{profile_picture}"}
        }
    ],
    "attachments": []
}

# Update the embed title with name and level
embed_data["embeds"][0]["title"] = f"{helldiver_ses}\nHelldiver: {helldiver_name}"

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

# Planet type specific embeds with icons
planet_icons = {
    "Super Earth": {
        "emoji": iconconfig['PlanetIcons']['Human Homeworld']
    },
    "Cyberstan": {
        "emoji": iconconfig['PlanetIcons']['Automaton Homeworld']
    },
    "Malevelon Creek": {
        "emoji": iconconfig['PlanetIcons']['Malevelon Creek']
    },
    "Calypso": {
        "emoji": iconconfig['PlanetIcons']['Calypso']
    },
    "Diaspora X": {
        "emoji": iconconfig['PlanetIcons']['Gloom']
    },
    "Enuliale": {
        "emoji": iconconfig['PlanetIcons']['Gloom']
    },
    "Epsilon Phoencis VI": {
        "emoji": iconconfig['PlanetIcons']['Gloom']
    },
    "Gemstone Bluffs": {
        "emoji": iconconfig['PlanetIcons']['Gloom']
    },
    "Nabatea Secundus": {
        "emoji": iconconfig['PlanetIcons']['Gloom']
    },
    "Navi VII": {
        "emoji": iconconfig['PlanetIcons']['Gloom']
    },
    "Azur Secundus": {
        "emoji": iconconfig['PlanetIcons']['Gloom']
    },
    "Erson Sands": {
        "emoji": iconconfig['PlanetIcons']['Gloom']
    },
    "Nivel 43": {
        "emoji": iconconfig['PlanetIcons']['Gloom']
    },
    "Zagon Prime": {
        "emoji": iconconfig['PlanetIcons']['Gloom']
    },
    "Hellmire": {
        "emoji": iconconfig['PlanetIcons']['Gloom']
    },
    "Omicron": {
        "emoji": iconconfig['PlanetIcons']['Gloom']
    },
    "Oshaune": {
        "emoji": iconconfig['PlanetIcons']['Gloom']
    },
    "Fori Prime": {
        "emoji": iconconfig['PlanetIcons']['Gloom']
    }
}

# Group planets by enemy type
enemy_planets = {}
for planet in planets:
    planet_data = df[df["Planet"] == planet]
    if not planet_data.empty:
        enemy_type = planet_data["Enemy Type"].iloc[0]
        if enemy_type not in enemy_planets:
            enemy_planets[enemy_type] = []
        enemy_planets[enemy_type].append((planet, planet_data))

# Add enemy-specific embeds
for enemy_type, planet_list in enemy_planets.items():
    planets_description_parts = []
    for planet, planet_data in planet_list:
        planets_description_parts.append(
            f"{enemy_icons.get(enemy_type, {'emoji': ''})['emoji']} **{planet}** {planet_icons.get(planet, {'emoji': ''})['emoji']}\n"
            f"> Deployments - {len(planet_data)}\n"
            f"> Major Order Deployments - {planet_data['Major Order'].astype(int).sum()}\n"
            f"> Kills - {planet_data['Kills'].sum()}\n"
            f"> Deaths - {planet_data['Deaths'].sum()}\n"
            f"> KDR - {(planet_data['Kills'].sum() / planet_data['Deaths'].sum()):.2f}\n"
            f"> Last Deployment - {get_last_deployment(planet_data, enemy_type)}\n"
        )
    planets_description = "\n".join(planets_description_parts)

    embed_data["embeds"].append({
        "title": f"{enemy_type} Front",
        "description": planets_description,
        "color": enemy_icons.get(enemy_type, {"color": 7257043})["color"],
        "thumbnail": {"url": enemy_icons.get(enemy_type, {"url": ""})["url"]}
    })

if DEBUG:
    webhook_urls = [config['Webhooks']['TEST']] # Use the webhook URL from the config for debugging
else:
    # Load webhook URLs from DCord.json
    with open('./JSON/DCord.json', 'r') as f:
        discord_data = json.load(f)
        webhook_urls = discord_data.get('discord_webhooks_export', [])
        webhook_urls = [
            (w.get('url') if isinstance(w, dict) else str(w)).strip()
            for w in webhook_urls
            if (isinstance(w, dict) and str(w.get('url','')).strip()) or (isinstance(w, str) and w.strip())
        ]
def _embeds_exceed_limits(e_data: dict) -> bool:
    """Heuristically determine if embed payload is likely to hit Discord limits.
    Discord limits (simplified):
      - 10 embeds per message
      - 4096 chars per embed description
      - ~6000 chars combined embed data (safe lower heuristic)  
    """
    embeds = e_data.get("embeds", [])
    if len(embeds) > 10:
        return True
    total_desc = 0
    for e in embeds:
        desc = e.get("description", "") or ""
        if len(desc) > 3900:  # safety margin below 4096
            return True
        total_desc += len(desc)
    if total_desc > 15000:  # arbitrary global safety threshold
        return True
    # Additional heuristic: if total json size gets large
    try:
        if len(json.dumps(e_data)) > 18000:
            return True
    except Exception:
        pass
    return False

def _generate_html_export(df: pd.DataFrame) -> str:
    """Generate an HTML export using optional user template or fallback."""
    template_path = "mission_export_template.html"
    if os.path.exists(template_path):
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template = f.read()
        except Exception:
            template = ""
    else:
        template = ""

    if not template:
        template = """<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>
<title>Helldiver Mission Export</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>body{font-family:Segoe UI,Arial,sans-serif;background:#0f1215;color:#e5e7eb;margin:0;padding:1.25rem;}h1{margin:.2rem 0 .5rem;font-size:1.4rem;}table{border-collapse:collapse;width:100%;font-size:.72rem;margin-top:1rem;}th,td{border:1px solid #222;padding:4px 6px;text-align:left;}th{background:#1e2630;position:sticky;top:0;}tbody tr:nth-child(odd){background:#141b1f;}tbody tr:nth-child(even){background:#10161c;}code{background:#1e2630;padding:2px 4px;border-radius:4px;}footer{margin-top:2rem;font-size:.6rem;color:#6b7280;text-align:center;}section{margin-top:1.2rem;}h2{font-size:1rem;margin:.2rem 0 .4rem;border-bottom:1px solid #1e2630;padding-bottom:2px;}ul{margin:.3rem 0 .6rem;padding-left:1.1rem;font-size:.65rem;}li{margin:0 0 .25rem;} .pill{display:inline-block;background:#243b55;border-radius:12px;padding:2px 10px;font-size:.6rem;margin-left:8px;}</style>
</head><body>
<h1>Helldiver Mission Export <span class='pill'>v{{VERSION}}</span></h1>
<div style='font-size:.7rem;'>Generated {{GENERATED_AT}} | Rows: {{ROW_COUNT}}</div>
<section><h2>Summary</h2><pre style='white-space:pre-wrap;font-size:.65rem;background:#12171d;padding:.5rem;border:1px solid #1e2630;border-radius:4px;'>{{PRIMARY_DESCRIPTION}}</pre></section>
<section><h2>Planet Statistics</h2>{{PLANET_TABLE}}</section>
<section><h2>Enemy Fronts</h2>{{ENEMY_SECTIONS}}</section>
<section><h2>Raw Data</h2>{{DATA_TABLE}}</section>
<footer>Generated by Helldiver Mission Log Manager HTML fallback. Customize: mission_export_template.html</footer>
</body></html>"""

    # Planet stats table
    planet_rows = []
    for planet in planets:
        planet_rows.append(
            f"<tr><td>{html_lib.escape(str(planet))}</td>"
            f"<td>{planet_deployments_dict.get(planet, 0)}</td>"
            f"<td>{planet_kills_dict.get(planet, 0)}</td>"
            f"<td>{planet_deaths_dict.get(planet, 0)}</td>"
            f"<td>{planet_orders_dict.get(planet, 0)}</td>"
            f"<td>{html_lib.escape(str(planet_last_date_dict.get(planet, '')))}</td></tr>"
        )
    planet_table = (
        "<table><thead><tr><th>Planet</th><th>Deployments</th><th>Kills</th><th>Deaths</th><th>Major Orders</th><th>Last Date</th></tr></thead><tbody>"
        + "".join(planet_rows) + "</tbody></table>"
    )

    # Enemy sections
    enemy_sections_parts = []
    for enemy_type, plist in enemy_planets.items():
        lines = []
        for planet, p_df in plist:
            last_date = p_df["Time"].max() if "Time" in p_df.columns else "No date available"
            lines.append(
                f"<li><strong>{html_lib.escape(str(planet))}</strong> - Deployments: {len(p_df)} | Kills: {p_df['Kills'].sum()} | Deaths: {p_df['Deaths'].sum()} | Major Orders: {p_df['Major Order'].astype(int).sum()} | Last: {html_lib.escape(str(last_date))}</li>"
            )
        enemy_sections_parts.append(
            f"<div style='margin-bottom:0.8rem;'><h3 style='margin:0 0 .3rem;font-size:.85rem;'>{html_lib.escape(str(enemy_type))}</h3><ul>{''.join(lines)}</ul></div>"
        )
    enemy_sections_html = "".join(enemy_sections_parts)

    # Raw data table (limit 2000 rows for size safety)
    max_rows = 2000
    trimmed_df = df.head(max_rows)
    header_html = "".join(f"<th>{html_lib.escape(str(c))}</th>" for c in trimmed_df.columns)
    data_rows = []
    for _, r in trimmed_df.iterrows():
        data_rows.append(
            "<tr>" + "".join(
                f"<td>{html_lib.escape('' if pd.isna(r[c]) else str(r[c]))}</td>" for c in trimmed_df.columns
            ) + "</tr>"
        )
    data_table_html = f"<table><thead><tr>{header_html}</tr></thead><tbody>{''.join(data_rows)}</tbody></table>"

    rendered = (template
        .replace("{{VERSION}}", "1.0")
        .replace("{{GENERATED_AT}}", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        .replace("{{ROW_COUNT}}", str(len(df)))
        .replace("{{PRIMARY_DESCRIPTION}}", html_lib.escape(primary_description))
        .replace("{{PLANET_TABLE}}", planet_table)
        .replace("{{ENEMY_SECTIONS}}", enemy_sections_html)
        .replace("{{DATA_TABLE}}", data_table_html)
    )
    return rendered

embed_data_contingency = {
    "embeds": [
        {
            "title": f"{helldiver_ses}\nHelldiver: {helldiver_name}\n{bicon}{ticon}{yearico}{PIco}{bsuperearth}{bcyberstan}{bmaleveloncreek}{bcalypso}{bpopliix}",
            "color": 7257043,
            "fields": [
                {
                    "name": f"Level {helldiver_level} | {helldiver_title} {TITLE_ICONS.get(df['Title'].iloc[-1], '')}",
                    "value": "\n\nINITIAL TRANSMISSION FAILURE - CONTINGENCY PROTOCOL ACTIVATED\n\nAttention Helldiver,\n\nYour SEAF Battle Record failed to reach your terminal via our Super Earth Command database through the standard uplink procedure, whether due to xeno interference, bureaucratic lag, the amount of data attempting to upload or simple operator inadequacy is irrelevant.\n\nAs per Protocol MLHD2-E2 \"Compliance is Victory\", a SHTML fallback file has been auto-generated to ensure your mission data is preserved and viewable.\n\nReview the document locally and stand by for reclassification procedures.\n\nFor Super Earth. For Democracy. Upload Again.\n\n- Ministry of Intelligence | Automated Systems Division\nSuper Earth Uplink Command"
                }
            ],
            "author": {
                        "name": f"SEAF Contingency Report\nDate: {date}",
                        "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356001307596427564/NwNzS9B.png?ex=67eafa21&is=67e9a8a1&hm=7e204265cbcdeaf96d7b244cd63992c4ef10dc18befbcf2ed39c3a269af14ec0&"
                    },
            "footer": {"text": f"{discord_data['discord_uid']}   v{VERSION}{DEV_RELEASE}","icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356025859319926784/5cwgI15.png?ex=67eb10fe&is=67e9bf7e&hm=ab6326a9da1e76125238bf3668acac8ad1e43b24947fc6d878d7b94c8a60ab28&"},
            "image": {"url": "https://cdn.discordapp.com/attachments/1340508329977446484/1374329173081985054/Super_Earth_landscape.png?ex=682da748&is=682c55c8&hm=15bd1b8a0ae0ecf08d7159a0602368dc7f27e040000e5c7d6afc391dfab5eb00&"},
            "thumbnail": {"url": f"{profile_picture}"}
        }
    ]
}

def _send_html_fallback(webhook_urls, df: pd.DataFrame):
    html_text = _generate_html_export(df)
    data_bytes = html_text.encode('utf-8')

    size_mb = len(data_bytes) / (1024 * 1024)
    if len(data_bytes) > 24 * 1024 * 1024:
        logging.error(f"HTML export ({size_mb:.2f} MB) exceeds ~25MB Discord limit.")
        return

    # for some stupid reason (discord), the payload can't be in the actual embed, so it has to be split, embed first, html file after.
    try:
        payload = json.loads(json.dumps(embed_data_contingency))
    except Exception:
        payload = {"embeds": embed_data_contingency.get("embeds", [])}

    if not payload.get("embeds"):
        payload["embeds"] = [{
            "title": "Mission Export",
            "description": "Contingency export attached.",
            "color": 5832548
        }]

    try:
        first_embed = payload["embeds"][0]
        note_text = f"SHTML fallback file attached: {helldiver_name}_Cont_Report.html"
        added_note = False

        if "fields" in first_embed:
            for f in first_embed["fields"]:
                if "mission_export.html" in f.get("value", ""):
                    added_note = True
                    break
            if not added_note:
                first_embed["fields"].append({
                    "name": "Attachment",
                    "value": note_text,
                    "inline": False
                })
        else:
            first_embed["fields"] = [{
                "name": "Attachment",
                "value": note_text,
                "inline": False
            }]
    except Exception as e:
        logging.warning(f"Could not annotate embed with attachment note: {e}")

    for webhook_url in webhook_urls:
        try:
            embed_only_payload = json.loads(json.dumps(payload))
            embed_only_payload.pop("attachments", None)
            try:
                fe = embed_only_payload["embeds"][0]
                if "fields" in fe:
                    found = False
                    for f in fe["fields"]:
                        if "mission_export.html" in f.get("value", ""):
                            f["value"] = f["value"].replace("attached:", ":")
                            found = True
                            break
                    if not found:
                        fe["fields"].append({
                            "name": "Attachment",
                            "value": "SHTML fallback file will follow in next message",
                            "inline": False
                        })
                else:
                    fe["fields"] = [{
                        "name": "Attachment",
                        "value": "SHTML fallback file will follow in next message",
                        "inline": False
                    }]
            except Exception as e:
                logging.warning(f"Could not adjust attachment notice in embed-only payload: {e}")

            resp1 = requests.post(webhook_url, json=embed_only_payload, timeout=30)
            if resp1.status_code in (200, 204):
                logging.info(f"Fallback embed sent (step 1/2) to {webhook_url}.")
            else:
                logging.error(f"Failed to send fallback embed (step 1/2) status {resp1.status_code} body: {resp1.text[:180]}")
                # If embed fails, still attempt file so user gets data, though if the embed fails to send it's likley so will the data... worth a shot tho
        except Exception as e:
            logging.error(f"Exception sending fallback embed (step 1/2): {e}")

        try:
            export_filename = f"{helldiver_name}_Cont_Report.html" if helldiver_name else "mission_export.html"

            file_payload = {
                "content": "",
                "attachments": [{"id": 0, "filename": export_filename}]
            }
            files = {"files[0]": (export_filename, data_bytes, "text/html")}
            resp2 = requests.post(
                webhook_url,
                data={"payload_json": json.dumps(file_payload)},
                files=files,
                timeout=30
            )
            if resp2.status_code in (200, 204):
                logging.info(f"Fallback HTML file sent (step 2/2) to {webhook_url}. Size: {size_mb:.2f} MB")
            else:
                logging.error(f"Failed sending fallback file (step 2/2) status {resp2.status_code} body: {resp2.text[:180]}")
        except Exception as e:
            logging.error(f"Exception sending fallback file (step 2/2): {e}")

# Decide whether to fallback to HTML, based on embed expectations, row count is also a factor though i'd rather not use that in case
needs_html = _embeds_exceed_limits(embed_data) or len(df) > 120

if needs_html:
    logging.info("Embed size/row count too large -> using HTML export fallback.")
    _send_html_fallback(webhook_urls, df)
else:
    for webhook_url in webhook_urls:
        response = requests.post(webhook_url, json=embed_data)
        if response.status_code == 204:
            logging.info("Data sent successfully.")
        else:
            logging.error(f"Failed to send data. Status: {response.status_code} Body: {response.text[:180]}")
