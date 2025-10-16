import pandas as pd
import logging
from datetime import datetime, timezone, timedelta
import json
import requests
import configparser
from icon import ENEMY_ICONS, DIFFICULTY_ICONS, PLANET_ICONS, CAMPAIGN_ICONS, MISSION_ICONS, BIOME_BANNERS, SUBFACTION_ICONS, TITLE_ICONS
from main import VERSION, DEV_RELEASE
import os

# --- Config and Logging Setup ---
from runtime_paths import app_path
config = configparser.ConfigParser()
config.read('config.config')
iconconfig = configparser.ConfigParser()
iconconfig.read('icon.config')
DEBUG = config.getboolean('DEBUGGING', 'DEBUG', fallback=False)

date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

# Set up application data paths 
APP_DATA = os.path.join(os.getenv('LOCALAPPDATA'), 'MLHD2')
if not os.path.exists(APP_DATA):
    os.makedirs(APP_DATA)

EXCEL_FILE_PROD = os.path.join(APP_DATA, 'mission_log.xlsx')
EXCEL_FILE_TEST = os.path.join(APP_DATA, 'mission_log_test.xlsx')
DATE_FORMAT = "%d-%m-%Y %H:%M:%S"

try:
    df = pd.read_excel(EXCEL_FILE_TEST if DEBUG else EXCEL_FILE_PROD)
except Exception as e:
    logging.error(f"Error reading Excel file: {e}")
    raise

# --- Filter Last 7 Days ---
if 'Time' not in df.columns:
    logging.error("No 'Time' column found in Excel file.")
    raise ValueError("No 'Time' column found.")

# Normalize and parse time column
df['Time'] = pd.to_datetime(df['Time'].astype(str).str.replace('/', '-', regex=False), errors='coerce', dayfirst=True)
now = pd.Timestamp.now()
seven_days_ago = now - timedelta(days=7)
recent_df = df[df['Time'] >= seven_days_ago]

if recent_df.empty:
    logging.warning("No entries found in the last 7 days.")
    # You may want to handle this case differently (e.g., send a message to Discord)
    exit(0)

# --- Prepare Discord Embed Data (Advanced, Faction-style) ---
# Get latest note
non_blank_notes = recent_df['Note'].dropna()
latest_note = non_blank_notes.iloc[-1] if not non_blank_notes.empty else "No Quote"

# Get most common values for favourites
search_mission = recent_df['Mission Type'].mode()[0] if 'Mission Type' in recent_df.columns and not recent_df['Mission Type'].mode().empty else "Unknown"
MissionCount = recent_df['Mission Type'].value_counts().iloc[0] if 'Mission Type' in recent_df.columns and not recent_df['Mission Type'].empty else 0
search_campaign = recent_df['Mission Category'].mode()[0] if 'Mission Category' in recent_df.columns and not recent_df['Mission Category'].mode().empty else "Unknown"
CampaignCount = recent_df['Mission Category'].value_counts().iloc[0] if 'Mission Category' in recent_df.columns and not recent_df['Mission Category'].empty else 0
search_faction = recent_df['Enemy Type'].mode()[0] if 'Enemy Type' in recent_df.columns and not recent_df['Enemy Type'].mode().empty else "Unknown"
FactionCount = recent_df['Enemy Type'].value_counts().iloc[0] if 'Enemy Type' in recent_df.columns and not recent_df['Enemy Type'].empty else 0
search_subfaction = recent_df['Enemy Subfaction'].mode()[0] if 'Enemy Subfaction' in recent_df.columns and not recent_df['Enemy Subfaction'].mode().empty else "Unknown"
SubfactionCount = recent_df['Enemy Subfaction'].value_counts().iloc[0] if 'Enemy Subfaction' in recent_df.columns and not recent_df['Enemy Subfaction'].empty else 0
search_difficulty = recent_df['Difficulty'].mode()[0] if 'Difficulty' in recent_df.columns and not recent_df['Difficulty'].mode().empty else "Unknown"
DifficultyCount = recent_df['Difficulty'].value_counts().iloc[0] if 'Difficulty' in recent_df.columns and not recent_df['Difficulty'].empty else 0
search_planet = recent_df['Planet'].mode()[0] if 'Planet' in recent_df.columns and not recent_df['Planet'].mode().empty else "Unknown"
PlanetCount = recent_df['Planet'].value_counts().iloc[0] if 'Planet' in recent_df.columns and not recent_df['Planet'].empty else 0
search_sector = recent_df['Sector'].mode()[0] if 'Sector' in recent_df.columns and not recent_df['Sector'].mode().empty else "Unknown"
SectorCount = recent_df['Sector'].value_counts().iloc[0] if 'Sector' in recent_df.columns and not recent_df['Sector'].empty else 0

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

# Get user info
helldiver_ses = recent_df['Super Destroyer'].iloc[-1] if 'Super Destroyer' in recent_df.columns else "Unknown"
helldiver_name = recent_df['Helldivers'].iloc[-1] if 'Helldivers' in recent_df.columns else "Unknown"
helldiver_level = recent_df['Level'].iloc[-1] if 'Level' in recent_df.columns else 0
helldiver_title = recent_df['Title'].iloc[-1] if 'Title' in recent_df.columns else "Unknown"

# Rating calculation (same as faction.py)
total_rows = len(recent_df)
max_rating = total_rows * 5
rating_mapping = {"Outstanding Patriotism": 5, "Superior Valour": 4, "Costly Failure": 4, "Honourable Duty":3, "Unremarkable Performance":2, "Dissapointing Service":1, "Disgraceful Conduct":0}
total_rating = sum(rating_mapping.get(row["Rating"], 0) for index, row in recent_df.iterrows() if "Rating" in recent_df.columns and row["Rating"] in rating_mapping)
Rating_Percentage = (total_rating / max_rating) * 100 if max_rating > 0 else 0

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

# Get discord_uid from DCord.json
with open(app_path('JSON', 'DCord.json'), 'r') as f:
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
with open(app_path('JSON', 'streak_data.json'), 'r') as f:
    streak_data = json.load(f)
    # Use "Helldiver" as the key or fall back to helldiver_ses if the first one doesn't exist
    highest_streak = streak_data.get("Helldiver", streak_data.get(helldiver_ses, {})).get("highest_streak", 0)
    profile_picture = streak_data.get("Helldiver", streak_data.get(helldiver_ses, {})).get("profile_picture_name", "")

embed_data = {
    "content": None,
    "embeds": [
        {
            "title": f"{helldiver_ses}\nHelldiver: {helldiver_name}\n{bicon}{ticon}{yearico}{PIco}{bsuperearth}{bcyberstan}{bmaleveloncreek}{bcalypso}{bpopliix}",
            "description": f"**Level {helldiver_level} | {helldiver_title} {TITLE_ICONS.get(df['Title'].iloc[-1], '')}**\n\n"
                           f"\"{latest_note}\"\n\n"
                           f"<a:easyshine1:1349110651829747773> <a:easyshine2:1349110649753698305> Combat Statistics <a:easyshine2:1349110649753698305> <a:easyshine3:1349110648528699422>\n"
                           f"> Kills - {recent_df['Kills'].sum()}\n"
                           f"> Deaths - {recent_df['Deaths'].sum()}\n"
                           f"> KDR - {(recent_df['Kills'].sum() / recent_df['Deaths'].sum()):.2f}\n"
                           f"> Highest Kills in Mission - {recent_df['Kills'].max()}\n"
                           f"\n<a:easyshine1:1349110651829747773> <a:easysuperearth:1343266082881802443> Mission Statistics <a:easysuperearth:1343266082881802443> <a:easyshine3:1349110648528699422>\n"
                           f"> Deployments - {len(recent_df)}\n"
                           f"> First Deployment - {recent_df['Time'].min().strftime('%d-%m-%Y %H:%M:%S')}\n"
                           f"> Last Deployment - {recent_df['Time'].max().strftime('%d-%m-%Y %H:%M:%S')}\n"
                           f"\n<a:easyshine1:1349110651829747773> <a:easyskullgold:1232018045791375360> Performance Statistics <a:easyskullgold:1232018045791375360> <a:easyshine3:1349110648528699422>\n"
                           f"> Rating - {Rating} | {int(Rating_Percentage)}%\n"
                           f"\n<a:easyshine1:1349110651829747773>  <:goldstar:1423054692228792430> Favourites <:goldstar:1423054692228792430> <a:easyshine3:1349110648528699422>\n"    
                           f"> Mission - {search_mission} {MISSION_ICONS.get(search_mission, '')} (x{MissionCount})\n"
                           f"> Campaign - {search_campaign} {CAMPAIGN_ICONS.get(search_campaign, '')} (x{CampaignCount})\n"
                           f"> Faction - {search_faction} {ENEMY_ICONS.get(search_faction, '')} (x{FactionCount})\n"
                           f"> Subfaction - {search_subfaction} {SUBFACTION_ICONS.get(search_subfaction, '')} (x{SubfactionCount})\n"
                           f"> Difficulty - {search_difficulty} {DIFFICULTY_ICONS.get(search_difficulty, '')} (x{DifficultyCount})\n"
                           f"> Planet - {search_planet} {PLANET_ICONS.get(search_planet, '')} (x{PlanetCount})\n"
                           f"> Sector - {search_sector} (x{SectorCount})\n",
            "color": 7257043,
            "author": {
                        "name": f"SEAF Weekly Battle Record\nDate: {date}",
                        "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356001307596427564/NwNzS9B.png?ex=67eafa21&is=67e9a8a1&hm=7e204265cbcdeaf96d7b244cd63992c4ef10dc18befbcf2ed39c3a269af14ec0&"
                    },
            "footer": {"text": f"{discord_data['discord_uid']}   v{VERSION}{DEV_RELEASE}","icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356025859319926784/5cwgI15.png?ex=67eb10fe&is=67e9bf7e&hm=ab6326a9da1e76125238bf3668acac8ad1e43b24947fc6d878d7b94c8a60ab28&"},
            "image": {"url": "https://cdn.discordapp.com/attachments/1340508329977446484/1426631105397788834/expWeekly.png?ex=68ebed41&is=68ea9bc1&hm=2cf2c9bed4b40597c509dc756eab867be37f20058b5570fd9fb5c18949ae882d&"},
            "thumbnail": {"url": f"{profile_picture}"}
        }
    ],
    "attachments": []
}

# --- Send to Discord Webhook ---
with open(app_path('JSON', 'DCord.json'), 'r') as f:
    discord_data = json.load(f)
webhook_urls = discord_data.get('discord_webhooks_export', [])
webhook_urls = [
    (w.get('url') if isinstance(w, dict) else str(w)).strip()
    for w in webhook_urls
    if (isinstance(w, dict) and str(w.get('url','')).strip()) or (isinstance(w, str) and w.strip())
]

for webhook_url in webhook_urls:
    response = requests.post(webhook_url, json=embed_data)
    if response.status_code == 204:
        logging.info("Data sent successfully.")
    else:
        logging.error(f"Failed to send data. Status: {response.status_code}")