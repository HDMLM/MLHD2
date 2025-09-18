import pandas as pd
import logging
from datetime import datetime, timedelta
import json
import requests
import configparser

# --- Config and Logging Setup ---
config = configparser.ConfigParser()
config.read('config.config')
DEBUG = config.getboolean('DEBUGGING', 'DEBUG', fallback=False)

# Read Excel file
excel_file = 'mission_log_test.xlsx' if DEBUG else 'mission_log.xlsx'
try:
    df = pd.read_excel(excel_file)
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
search_mission = recent_df['Mission Type'].mode()[0] if 'Mission Type' in recent_df.columns else "Unknown"
MissionCount = recent_df.apply(lambda row: row.astype(str).str.contains(search_mission, case=False).sum(), axis=1).sum() if 'Mission Type' in recent_df.columns else 0
search_campaign = recent_df['Mission Category'].mode()[0] if 'Mission Category' in recent_df.columns else "Unknown"
CampaignCount = recent_df.apply(lambda row: row.astype(str).str.contains(search_campaign, case=False).sum(), axis=1).sum() if 'Mission Category' in recent_df.columns else 0
search_faction = recent_df['Enemy Type'].mode()[0] if 'Enemy Type' in recent_df.columns else "Unknown"
FactionCount = recent_df['Enemy Type'].apply(lambda x: str(x).lower() == str(search_faction).lower()).sum() if 'Enemy Type' in recent_df.columns else 0
search_subfaction = recent_df['Enemy Subfaction'].mode()[0] if 'Enemy Subfaction' in recent_df.columns else "Unknown"
SubfactionCount = recent_df.apply(lambda row: row.astype(str).str.contains(search_subfaction, case=False).sum(), axis=1).sum() if 'Enemy Subfaction' in recent_df.columns else 0
search_difficulty = recent_df['Difficulty'].mode()[0] if 'Difficulty' in recent_df.columns else "Unknown"
DifficultyCount = recent_df.apply(lambda row: row.astype(str).str.contains(search_difficulty, case=False).sum(), axis=1).sum() if 'Difficulty' in recent_df.columns else 0
search_planet = recent_df['Planet'].mode()[0] if 'Planet' in recent_df.columns else "Unknown"
PlanetCount = recent_df['Planet'].apply(lambda x: str(x).lower() == str(search_planet).lower()).sum() if 'Planet' in recent_df.columns else 0
search_sector = recent_df['Sector'].mode()[0] if 'Sector' in recent_df.columns else "Unknown"
SectorCount = recent_df.apply(lambda row: row.astype(str).str.contains(search_sector, case=False).sum(), axis=1).sum() if 'Sector' in recent_df.columns else 0

# Basic icons (optional, can be expanded if you import icon configs)
MISSION_ICONS = {}
CAMPAIGN_ICONS = {}
ENEMY_ICONS = {}
SUBFACTION_ICONS = {}
DIFFICULTY_ICONS = {}
PLANET_ICONS = {}
BIOME_BANNERS = {}
TITLE_ICONS = {}

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

embed_data = {
    "content": None,
    "embeds": [
        {
            "title": f"{helldiver_ses}\nHelldiver: {helldiver_name}",
            "description": f"**Level {helldiver_level} | {helldiver_title} {TITLE_ICONS.get(helldiver_title, '')}**\n\n"
                           f"\"{latest_note}\"\n\n"
                           f"<a:easyshine1:1349110651829747773>  <a:easyshine2:1349110649753698305> Combat Statistics <a:easyshine2:1349110649753698305> <a:easyshine3:1349110648528699422>\n"
                           f"> Kills - {recent_df['Kills'].sum()}\n"
                           f"> Deaths - {recent_df['Deaths'].sum()}\n"
                           f"> KDR - {(recent_df['Kills'].sum() / recent_df['Deaths'].sum()):.2f}\n"
                           f"> Highest Kills in Mission - {recent_df['Kills'].max()}\n"
                           f"\n<a:easyshine1:1349110651829747773>  <a:easysuperearth:1343266082881802443> Mission Statistics <a:easysuperearth:1343266082881802443> <a:easyshine3:1349110648528699422>\n"
                           f"> Deployments - {len(recent_df)}\n"
                           f"> First Deployment - {recent_df['Time'].min().strftime('%d-%m-%Y %H:%M:%S')}\n"
                           f"> Last Deployment - {recent_df['Time'].max().strftime('%d-%m-%Y %H:%M:%S')}\n"
                           f"\n<a:easyshine1:1349110651829747773>  <a:easyskullgold:1232018045791375360> Performance Statistics <a:easyskullgold:1232018045791375360> <a:easyshine3:1349110648528699422>\n"
                           f"> Rating - {Rating} | {int(Rating_Percentage)}%\n"
                           f"\n<a:easyshine1:1349110651829747773>  <:goldstar:1337818552094163034> Favourites <:goldstar:1337818552094163034> <a:easyshine3:1349110648528699422>\n"
                           f"> Mission - {search_mission} {MISSION_ICONS.get(search_mission, '')} (x{MissionCount})\n"
                           f"> Campaign - {search_campaign} {CAMPAIGN_ICONS.get(search_campaign, '')} (x{CampaignCount})\n"
                           f"> Faction - {search_faction} {ENEMY_ICONS.get(search_faction, '')} (x{FactionCount})\n"
                           f"> Subfaction - {search_subfaction} {SUBFACTION_ICONS.get(search_subfaction, '')} (x{SubfactionCount})\n"
                           f"> Difficulty - {search_difficulty} {DIFFICULTY_ICONS.get(search_difficulty, '')} (x{DifficultyCount})\n"
                           f"> Planet - {search_planet} {PLANET_ICONS.get(search_planet, '')} (x{PlanetCount})\n"
                           f"> Sector - {search_sector} (x{SectorCount})\n",
            "color": 7257043,
            "author": {"name": "SEAF Weekly Battle Record"},
            "footer": {"text": "Weekly Export"},
            "image": {"url": f"{BIOME_BANNERS.get(search_planet, '')}"},
            "thumbnail": {"url": ""}
        }
    ],
    "attachments": []
}

# --- Send to Discord Webhook ---
with open('./JSON/DCord.json', 'r') as f:
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