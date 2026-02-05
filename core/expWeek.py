import pandas as pd
import logging
from datetime import datetime, timezone, timedelta
import json
import requests
import configparser
from core.icon import ENEMY_ICONS, DIFFICULTY_ICONS, PLANET_ICONS, CAMPAIGN_ICONS, MISSION_ICONS, BIOME_BANNERS, SUBFACTION_ICONS, TITLE_ICONS, get_badge_icons
from core.app_core import VERSION, DEV_RELEASE
from core.discord_integration import _sanitize_embed
import os

# --- Config and Logging Setup ---
from core.runtime_paths import app_path
config = configparser.ConfigParser()
config.read(app_path('orphan', 'config.config'))
iconconfig = configparser.ConfigParser()
iconconfig.read(app_path('orphan', 'icon.config'))
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
rating_mapping = {"Gallantry Beyond Measure": 5, "Outstanding Patriotism": 5, "Truly Exceptional Heroism": 4, "Superior Valour": 4, "Costly Failure": 4, "Honourable Duty":3, "Unremarkable Performance":2, "Dissapointing Service":1, "Disgraceful Conduct":0}
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

# Get badge icons using centralized function
badge_data = get_badge_icons(DEBUG, APP_DATA, DATE_FORMAT)

# Build badge string: always-on first, then up to 4 user-selected badges
always_on_order = ['bicon', 'ticon', 'yearico', 'PIco']
selectable_order = ['bsuperearth', 'bcyberstan', 'bmaleveloncreek', 'bcalypso', 'bpopliix', 'bseyshelbeach', 'boshaune']

# Load user's badge display preference from DCord.json if present
try:
    display_pref = discord_data.get('display_badges', None) if 'discord_data' in locals() else None
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
badge_string = ''.join(badge_items)

# Create named references for backwards-compatibility in other code
bicon = badge_data.get('bicon', '')
ticon = badge_data.get('ticon', '')
PIco = badge_data.get('PIco', '')
yearico = badge_data.get('yearico', '')
bsuperearth = badge_data.get('bsuperearth', '')
bcyberstan = badge_data.get('bcyberstan', '')
bmaleveloncreek = badge_data.get('bmaleveloncreek', '')
bcalypso = badge_data.get('bcalypso', '')
bpopliix = badge_data.get('bpopliix', '')
bseyshelbeach = badge_data.get('bseyshelbeach', '')
boshaune = badge_data.get('boshaune', '')

highest_streak = 0
profile_picture = ""
with open(app_path('JSON', 'streak_data.json'), 'r') as f:
    streak_data = json.load(f)
    # Use "Helldiver" as the key or fall back to helldiver_ses if the first one doesn't exist
    highest_streak = streak_data.get("Helldiver", streak_data.get(helldiver_ses, {})).get("highest_streak", 0)
    profile_picture = streak_data.get("Helldiver", streak_data.get(helldiver_ses, {})).get("profile_picture_name", "")

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

embed_data = {
    "content": None,
    "embeds": [
        {
            "title": f"{helldiver_ses}\nHelldiver: {helldiver_name}\n{badge_string}",
            "description": f"**Level {helldiver_level} | {helldiver_title} {TITLE_ICONS.get(df['Title'].iloc[-1], '')}**\n\n"
                           f"\"{latest_note}\"\n\n"
                           f"{FlairLeftIco} {FlairSkullIco} Combat Statistics {FlairSkullIco} {FlairRightIco}\n"
                           f"> Kills - {recent_df['Kills'].sum()}\n"
                           f"> Deaths - {recent_df['Deaths'].sum()}\n"
                           f"> KDR - {(recent_df['Kills'].sum() / recent_df['Deaths'].sum()):.2f}\n"
                           f"> Highest Kills in Mission - {recent_df['Kills'].max()}\n"
                           f"\n{FlairLeftIco} {FlairSEIco} Mission Statistics {FlairSEIco} {FlairRightIco}\n"
                           f"> Deployments - {len(recent_df)}\n"
                           f"> First Deployment - {recent_df['Time'].min().strftime('%d-%m-%Y %H:%M:%S')}\n"
                           f"> Last Deployment - {recent_df['Time'].max().strftime('%d-%m-%Y %H:%M:%S')}\n"
                           f"\n{FlairLeftIco} {FlairGSSkullIco} Performance Statistics {FlairGSSkullIco} {FlairRightIco}\n"
                           f"> Rating - {Rating} | {int(Rating_Percentage)}%\n"
                           f"\n{FlairLeftIco}  {GoldStarIco} Favourites {GoldStarIco} {FlairRightIco}\n"    
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
    try:
        payload = json.loads(json.dumps(embed_data))
        if payload.get('content') is None:
            payload.pop('content', None)

        # Sanitize embeds to avoid Discord validation errors
        if 'embeds' in payload and isinstance(payload['embeds'], list):
            for i, embed in enumerate(payload['embeds']):
                if embed:  # Only sanitize if embed exists
                    sanitized, changes = _sanitize_embed(embed)
                    payload['embeds'][i] = sanitized
                    if changes:
                        logging.info(f"Sanitized embed {i} before sending: {changes}")

        # If all embeds are now empty after sanitization, skip sending
        if not any(payload.get('embeds', [])):
            logging.error(f"Skipping webhook send to {webhook_url}: all embeds empty after sanitization.")
            continue

        response = requests.post(webhook_url, json=payload)
        if response.status_code in (200, 204):
            logging.info(f"Data sent successfully to {webhook_url} (status {response.status_code}).")
        else:
            try:
                resp_data = response.json()
            except ValueError:
                resp_data = response.text
            logging.error(f"Failed to send data to {webhook_url}. Status: {response.status_code} Response: {resp_data}")
    except Exception as e:
        logging.error(f"Exception sending webhook to {webhook_url}: {e}")