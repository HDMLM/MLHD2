import pandas as pd
import logging
from logging_config import setup_logging
import configparser
import requests
import json
from PIL import Image, ImageDraw, ImageFont
import textwrap
import io
from icon import ENEMY_ICONS, DIFFICULTY_ICONS, PLANET_ICONS, CAMPAIGN_ICONS, MISSION_ICONS, BIOME_BANNERS, SUBFACTION_ICONS
from main import VERSION, DEV_RELEASE

# Read configuration from config.config
config = configparser.ConfigParser()
config.read('config.config')
iconconfig = configparser.ConfigParser()
iconconfig.read('icon.config')

#Constants
DEBUG = config.getboolean('DEBUGGING', 'DEBUG', fallback=False)

# Set the default values for the variables
ExpType = "Planetary"

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

# Read the Excel file
setup_logging(DEBUG)
try:
    df = pd.read_excel('mission_log_test.xlsx') if DEBUG else pd.read_excel('mission_log.xlsx')
except FileNotFoundError:
    logging.error("Error: Excel file not found. Please ensure the file exists in the correct location.")
    exit(1)

# Initialize a dictionary to store column totals
sectors = []
planets = []
enemy_types = []
MissionCategory = []
difficulties = []

# Initialize lists to store stats for each planet
planet_kills_list = []
planet_deaths_list = []
planet_orders_list = []

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

def get_rating(df):
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

    return Rating, Rating_Percentage


def get_LastEntry(df):
    # Get the user's name and level from the last row of the DataFrame
    helldiver_ses = df['Super Destroyer'].iloc[-1] if 'Super Destroyer' in df.columns else "Unknown"
    helldiver_name = df['Helldivers'].iloc[-1] if 'Helldivers' in df.columns else "Unknown"
    helldiver_level = df['Level'].iloc[-1] if 'Level' in df.columns else 0
    helldiver_title = df['Title'].iloc[-1] if 'Title' in df.columns else "Unknown"
    non_blank_notes = df['Note'].dropna()
    latest_note = non_blank_notes.iloc[-1] if not non_blank_notes.empty else "No Quote"
    
    return helldiver_ses, helldiver_name, helldiver_level, helldiver_title, latest_note

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
WEBHOOK_URLS = {
    'PROD': config['Webhooks']['BAT'].split(','),
    'TEST': config['Webhooks']['TEST'].split(',')
}

# Discord webhook settings
ACTIVE_WEBHOOK = WEBHOOK_URLS['TEST'] if DEBUG else WEBHOOK_URLS['PROD']
UID = config['Discord']['UID']


# Get Instances from Data
search_mission = df['Mission Type'].mode()[0]
MissionCount = df.apply(lambda row: row.astype(str).str.contains(search_mission, case=False).sum(), axis=1).sum()
search_campaign = df['Mission Category'].mode()[0]
CampaignCount = df.apply(lambda row: row.astype(str).str.contains(search_campaign, case=False).sum(), axis=1).sum()
search_faction = df['Enemy Type'].mode()[0]
FactionCount = df.apply(lambda row: row.astype(str).str.contains(search_faction, case=False).sum(), axis=1).sum()
search_subfaction = df['Enemy Subfaction'].mode()[0]
SubfactionCount = df.apply(lambda row: row.astype(str).str.contains(search_subfaction, case=False).sum(), axis=1).sum()
search_difficulty = df['Difficulty'].mode()[0]
DifficultyCount = df.apply(lambda row: row.astype(str).str.contains(search_difficulty, case=False).sum(), axis=1).sum()
search_planet = df['Planet'].mode()[0]
PlanetCount = df['Planet'].apply(lambda x: str(x).lower() == search_planet.lower()).sum()
search_mega_city = df['Mega City'].mode()[0]
MegaCityCount = df['Mega City'].apply(lambda x: str(x).lower() == search_mega_city.lower()).sum()
search_sector = df['Sector'].mode()[0]
SectorCount = df.apply(lambda row: row.astype(str).str.contains(search_sector, case=False).sum(), axis=1).sum()



# Get the rating and percentage
Rating, Rating_Percentage = get_rating(df)
# Get the last entry details
helldiver_ses, helldiver_name, helldiver_level, helldiver_title, latest_note = get_LastEntry(df)
# get streak
highest_streak = 0
with open('streak_data.json', 'r') as f:
    streak_data = json.load(f)
    # Use "Helldiver" as the key or fall back to helldiver_ses if the first one doesn't exist
    highest_streak = streak_data.get("Helldiver", streak_data.get(helldiver_ses, {})).get("highest_streak", 0)

# Calculate Mega City deployments excluding "Planet Surface" and empty values
mega_city_count = df[df['Mega City'].fillna('').astype(str).apply(lambda x: x != '' and x.lower() != 'planet surface')].shape[0]

# Create embed data
# Create the main embed first
embed_data = {
    "content": None,
    "embeds": [
        {
            "title": "",  # Empty title, will be set below
            "description": f"\"{latest_note}\"\n\n<a:easyshine1:1349110651829747773>  <a:easyshine2:1349110649753698305> Combat Statistics <a:easyshine2:1349110649753698305> <a:easyshine3:1349110648528699422>\n" + 
                        f"> Kills - {df['Kills'].sum()}\n" +
                        f"> Deaths - {df['Deaths'].sum()}\n" +
                        f"> KDR - {(df['Kills'].sum() / df['Deaths'].sum()):.2f}\n" +
                        f"> Highest Kills in Mission - {df['Kills'].max()}\n" +

                        f"\n<a:easyshine1:1349110651829747773>  <a:easysuperearth:1343266082881802443> Mission Statistics <a:easysuperearth:1343266082881802443> <a:easyshine3:1349110648528699422>\n" + 
                        f"> Deployments - {len(df)}\n" +
                        f"> Major Order Deployments - {df['Major Order'].astype(int).sum()}\n" +
                        f"> DSS Deployments - {df['DSS Active'].astype(int).sum()}\n" +
                        f"> Mega City Deployments - {mega_city_count}\n" +
                        f"> First Deployment - {get_first_deployment(df, df['Enemy Type'].mode()[0])}\n" +

                        f"\n<a:easyshine1:1349110651829747773>  <a:easyskullgold:1232018045791375360> Performance Statistics <a:easyskullgold:1232018045791375360> <a:easyshine3:1349110648528699422>\n" +                      
                        f"> Rating - {Rating} | {int(Rating_Percentage)}%\n" +
                        f"> Highest Streak - {highest_streak} Missions\n" +

                        f"\n<a:easyshine1:1349110651829747773>  <:goldstar:1337818552094163034> Favourites <:goldstar:1337818552094163034> <a:easyshine3:1349110648528699422>\n" +     
                        f"> Mission - {df['Mission Type'].mode()[0]} {MISSION_ICONS.get(df['Mission Type'].mode()[0], '')} (x{MissionCount})\n" +
                        f"> Campaign - {df['Mission Category'].mode()[0]} {CAMPAIGN_ICONS.get(df['Mission Category'].mode()[0], '')} (x{CampaignCount})\n" +
                        f"> Faction - {df['Enemy Type'].mode()[0]} {ENEMY_ICONS.get(df['Enemy Type'].mode()[0], '')} (x{FactionCount})\n" +
                        f"> Subfaction - {df['Enemy Subfaction'].mode()[0]} {SUBFACTION_ICONS.get(df['Enemy Subfaction'].mode()[0], '')} (x{SubfactionCount})\n"
                        f"> Difficulty - {df['Difficulty'].mode()[0]} {DIFFICULTY_ICONS.get(df['Difficulty'].mode()[0], '')} (x{DifficultyCount})\n" +
                        f"> Planet - {df['Planet'].mode()[0]} {PLANET_ICONS.get(df['Planet'].mode()[0], '')} (x{PlanetCount})\n" +
                        f"> Sector - {df['Sector'].mode()[0]} (x{SectorCount})\n" +
                        f"> Mega City - {df['Mega City'].mode()[0]} (x{MegaCityCount})\n",
            "color": 7257043,
            "author": {"name": "SEAF Battle Record"},
            "footer": {"text": config['Discord']['UID'],"icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356025859319926784/5cwgI15.png?ex=67eb10fe&is=67e9bf7e&hm=ab6326a9da1e76125238bf3668acac8ad1e43b24947fc6d878d7b94c8a60ab28&"},
            "image": {"url": f"{BIOME_BANNERS.get(df['Planet'].mode()[0], '')}"},
            "thumbnail": {"url": "https://i.ibb.co/5g2b9NXb/Super-Earth-Icon.png"}
        }
    ],
    "attachments": []
}

# Update the embed title with name and level
embed_data["embeds"][0]["title"] = f"{helldiver_ses}\nHelldiver: {helldiver_name}\nLevel {helldiver_level} | {helldiver_title}"
webhook_urls = WEBHOOK_URLS['TEST'] if DEBUG else WEBHOOK_URLS['PROD']

def create_stats_image(enemy_type, planet_list):
    # Create image with gray background
    width = 800
    height = len(planet_list) * 200 + 100  # Adjust height based on number of planets
    image = Image.new('RGB', (width, height), 'gray')
    draw = ImageDraw.Draw(image)
    
    # Load fonts (you'll need to provide proper font paths)
    try:
        title_font = ImageFont.truetype("arial.ttf", 36)
        regular_font = ImageFont.truetype("arial.ttf", 24)
    except:
        title_font = ImageFont.load_default()
        regular_font = ImageFont.load_default()

    # Draw title
    draw.text((20, 20), f"{enemy_type} Front Statistics", fill='white', font=title_font)
    
    current_y = 80
    for planet, planet_data in planet_list:
        
        # Draw planet stats
        planet_text = f"""
        {planet}
        Deployments: {len(planet_data)}
        Major Orders: {planet_data['Major Order'].astype(int).sum()}
        Kills: {planet_data['Kills'].sum()}
        Deaths: {planet_data['Deaths'].sum()}
        Last Deployment: {get_last_deployment(planet_data, enemy_type)}
        """
        
        # Draw each line of text
        for line in planet_text.strip().split('\n'):
            draw.text((20, current_y), line.strip(), fill='white', font=regular_font)
            current_y += 30
        
        current_y += 20  # Add spacing between planets

    # Convert image to bytes
    img_byte_array = io.BytesIO()
    image.save(img_byte_array, format='PNG')
    img_byte_array.seek(0)
    return img_byte_array

def generate_embed_data():
    # For storing file attachments separately
    files = []
    
    if ExpType == "Planetary":
        # Group planets by enemy type
        enemy_planets = {}
        for planet in planets:
            planet_data = df[df["Planet"] == planet]
            if not planet_data.empty:
                enemy_type = planet_data["Enemy Type"].iloc[0]
                if enemy_type not in enemy_planets:
                    enemy_planets[enemy_type] = []
                enemy_planets[enemy_type].append((planet, planet_data))

        # Create images for each enemy type and prepare them as attachments
        for i, (enemy_type, planet_list) in enumerate(enemy_planets.items()):
            stats_image = create_stats_image(enemy_type, planet_list)
            filename = f"{enemy_type.lower().replace(' ', '_')}_stats.png"
            
            # Add a new embed that references this attachment
            embed_data["embeds"].append({
                "title": f"{enemy_type} Front",
                "color": enemy_icons.get(enemy_type, {"color": 7257043})["color"],
                "image": {"url": f"attachment://{filename}"}
            })
            
            # Store file data for later use with the requests library
            files.append((filename, stats_image, 'image/png'))

        return embed_data, files

    elif ExpType == "Faction":
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

        # Add enemy-specific embeds
        for enemy_type, stats in faction_stats.items():
            faction_description = f"{enemy_icons.get(enemy_type, {'emoji': ''})['emoji']} **{enemy_type} Front Statistics**\n" + \
                f"> Deployments - {stats['total_deployments']}\n" + \
                f"> Major Order Deployments - {stats['major_orders']}\n" + \
                f"> Kills - {stats['total_kills']}\n" + \
                f"> Deaths - {stats['total_deaths']}\n" + \
                f"> Last Deployment - {stats['last_deployment']}\n\n"

            embed_data["embeds"].append({
                "title": f"{enemy_type} Campaign Record",
                "description": faction_description,
                "color": enemy_icons.get(enemy_type, {"color": 7257043})["color"],
                "thumbnail": {"url": enemy_icons.get(enemy_type, {"url": ""})["url"]}
            })
        return embed_data, []
    
    # Default return if no type matches
    return embed_data, []

# Generate embed data
result = generate_embed_data()
if isinstance(result, tuple) and len(result) == 2:
    embed_data, file_attachments = result
else:
    embed_data = result
    file_attachments = []

# Send data to Discord
for webhook_url in webhook_urls:
    if file_attachments:
        # Prepare files properly for requests
        files_dict = {}
        for i, (filename, file_obj, mime_type) in enumerate(file_attachments):
            # We need to create a tuple of (filename, file object or data, mime_type)
            files_dict[filename] = (filename, file_obj.getvalue(), mime_type)
        
        # Send the request with files properly attached
        response = requests.post(
            webhook_url,
            data={"payload_json": json.dumps(embed_data)},
            files=files_dict
        )
    else:
        # If no files, just send the JSON payload
        response = requests.post(webhook_url, json=embed_data)
    
    if response.status_code in [200, 204]:
        logging.info("Data sent successfully.")
    else:
        logging.error(f"Failed to send data. Status: {response.status_code}")
 