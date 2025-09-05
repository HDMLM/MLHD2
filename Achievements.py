import pandas as pd
import configparser
import requests
import json
import logging
from logging_config import setup_logging
from icon import TITLE_ICONS
from main import VERSION, DEV_RELEASE

# Read configuration from config.config
config = configparser.ConfigParser()
config.read('config.config')

#Constants
DEBUG = config.getboolean('DEBUGGING', 'DEBUG', fallback=False)
setup_logging(DEBUG)

# Read the Excel file
try:
    df = pd.read_excel('mission_log_test.xlsx') if DEBUG else pd.read_excel('mission_log.xlsx')
except FileNotFoundError:
    logging.error("Excel file not found. Please ensure the file exists in the correct location.")
    exit(1)


highest_streak = 0
profile_picture = ""
with open('streak_data.json', 'r') as f:
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

#get total terminid missions
total_terminid_missions = df[df['Enemy Type'] == 'Terminids'].shape[0]

#get total automaton missions
total_automaton_missions = df[df['Enemy Type'] == 'Automatons'].shape[0]

#get total illuminate missions
total_illuminate_missions = df[df['Enemy Type'] == 'Illuminates'].shape[0]

# get total terminid kills
total_terminid_kills = df[df['Enemy Type'] == 'Terminids']['Kills'].sum()

# get total automaton kills
total_automaton_kills = df[df['Enemy Type'] == 'Automatons']['Kills'].sum()

# get total illuminate kills
total_illuminate_kills = df[df['Enemy Type'] == 'Illuminates']['Kills'].sum()

# get if at least one mission was played on Malevelon Creek
malevelon_creek = df[df['Planet'] == 'Malevelon Creek'].shape[0] > 0

# get if at least on mission was rated Disgracful Conduct
disgraceful_conduct = df[df['Rating'] == 'Disgraceful Conduct'].shape[0] > 0

#get if at least one mission was played on Super Earth
super_earth = df[df['Planet'] == 'Super Earth'].shape[0] > 0

# get at least one mission was played on the Cyberstan
cyberstan = df[df['Planet'] == 'Cyberstan'].shape[0] > 0

# get if highest_streak is 30 or more
streak_30 = highest_streak >= 30


#assign bool values to variables
CmdFavourite = total_missions >= 1000
ReliableDiver = total_missions_major_order >= total_missions / 2
DSSDiver = total_missions_dss >= total_missions / 2
OutbreakPerfected = total_terminid_missions >= 250
AutomatonPerfected = total_automaton_missions >= 250
IlluminatePerfected = total_illuminate_missions >= 250
TerminidHunter = total_terminid_kills >= 100000
AutomatonHunter = total_automaton_kills >= 100000
IlluminateHunter = total_illuminate_kills >= 100000
MalevelonCreek = malevelon_creek
DisgracefulConduct = disgraceful_conduct
SuperEarth = super_earth
Cyberstan = cyberstan
Streak30 = streak_30

# Create a dictionary to store the achievements
achievements = {
    "CmdFavourite": CmdFavourite,
    "ReliableDiver": ReliableDiver,
    "DSSDiver": DSSDiver,
    "OutbreakPerfected": OutbreakPerfected,
    "AutomatonPerfected": AutomatonPerfected,
    "IlluminatePerfected": IlluminatePerfected,
    "TerminidHunter": TerminidHunter,
    "AutomatonHunter": AutomatonHunter,
    "IlluminateHunter": IlluminateHunter,
    "MalevelonCreek": MalevelonCreek,
    "DisgracefulConduct": DisgracefulConduct,
    "SuperEarth": SuperEarth,
    "Cyberstan": Cyberstan,
    "Streak30": Streak30
}

# Load Webhook URL from config
# Discord webhook configuration
WEBHOOK_URLS = {
    'PROD': config['Webhooks']['BAT'].split(','),
    'TEST': config['Webhooks']['TEST'].split(',')
}
ACTIVE_WEBHOOK = WEBHOOK_URLS['TEST'] if DEBUG else WEBHOOK_URLS['PROD']

# Define achievement metadata for messages and titles
ACHIEVEMENT_DEFS = {
    "CmdFavourite": {
        "message": ("Log 1000 Missions", "HINT: You have the strength and the courage... to be free"),
        "title": (
            "<a:EasyAwardBaftaMP2025:1363545915352289371> **HIGH COMMAND'S FAVOURITE**",
            "<:achievement_style_3:1374174049726632067> **~~HIGH COMMAND'S FAVOURITE~~**"
        )
    },
    "ReliableDiver": {
        "message": ("More than 50% of your logged missions are involved in a Major Order", "HINT: You're one to obey orders"),
        "title": (
            "<a:EasyAwardBaftaMusic2025:1359268029850058974> **RELIABLE DIVER**",
            "<:achievement_style_1:1374174053254041640> **~~RELIABLE DIVER~~**"
        )
    },
    "DSSDiver": {
        "message": ("More than 50% of your logged Missions are involved with the Democracy Space Station", "HINT: You like a good bit of support"),
        "title": (
            "<a:EasyAwardBaftaMusic2025:1359268029850058974> **I <3 DSS**",
            "<:achievement_style_1:1374174053254041640> **~~I <3 DSS~~**"
        )
    },
    "OutbreakPerfected": {
        "message": ("Log 250 Terminid Missions", "HINT: You're rather familiar with E-710"),
        "title": (
            "<a:EasyMedal:1233854253077102653> **OUTBREAK PERFECTED**",
            "<:achievement_style_2:1374174051551154267> **~~OUTBREAK PERFECTED~~**"
        )
    },
    "AutomatonPerfected": {
        "message": ("Log 250 Automaton Missions", "HINT: You're rather familiar with losing access to your Stratagems"),
        "title": (
            "<a:EasyMedal:1233854253077102653> **INCURSION DEVASTATED**",
            "<:achievement_style_2:1374174051551154267> **~~INCURSION DEVASTATED~~**"
        )
    },
    "IlluminatePerfected": {
        "message": ("Log 250 Illuminates Missions", "HINT: You're rather familiar with their autocratic intentions"),
        "title": (
            "<a:EasyMedal:1233854253077102653> **INVASION ABOLISHED**",
            "<:achievement_style_2:1374174051551154267> **~~INVASION ABOLISHED~~**"
        )
    },
    "TerminidHunter": {
        "message": ("Log 100,000 Kills against the Terminids", "HINT: You douse yourself in E-710"),
        "title": (
            "<a:EasyAwardBaftaMP2025:1363545915352289371> **BUG STOMPER**",
            "<:achievement_style_3:1374174049726632067> **~~BUG STOMPER~~**"
        )
    },
    "AutomatonHunter": {
        "message": ("Log 100,000 Kills against the Automatons", "HINT: You make things out of scrap metal in your spare time"),
        "title": (
            "<a:EasyAwardBaftaMP2025:1363545915352289371> **CLANKER SCRAPPER**",
            "<:achievement_style_3:1374174049726632067> **~~CLANKER SCRAPPER~~**"
        )
    },
    "IlluminateHunter": {
        "message": ("Log 100,000 Kills against the Illuminates", "HINT: You single handedly make an effort of wiping them out of the Second Galactic War"),
        "title": (
            "<a:EasyAwardBaftaMP2025:1363545915352289371> **SQUID SEVERER**",
            "<:achievement_style_3:1374174049726632067> **~~SQUID SEVERER~~**"
        )
    },
    "MalevelonCreek": {
        "message": ("Serve on Malevelon Creek", "HINT: You remember..."),
        "title": (
            "<a:EasyAwardBaftaMusic2025:1359268029850058974> **NEVER FORGET**",
            "<:achievement_style_1:1374174053254041640> **~~NEVER FORGET~~**"
        )
    },
    "DisgracefulConduct": {
        "message": ("Get a Performance Rating of Disgraceful Conduct on a Mission", "HINT: You... why?"),
        "title": (
            "<a:EasyMedal:1233854253077102653> **you got this on purpose...**",
            "<:achievement_style_2:1374174051551154267> **~~you got this on purpose...~~"
        )
    },
    "SuperEarth": {
        "message": ("Serve on Super Earth", "HINT: You feel very welcome"),
        "title": (
            "<a:EasyAwardBaftaMusic2025:1359268029850058974> **HOME SUPER HOME**",
            "<:achievement_style_1:1374174053254041640> **~~HOME SUPER HOME~~**"
        )
    },
    "Cyberstan": {
        "message": ("Serve on an Enemy Homeworld", "HINT: You don't feel very welcome... like they have a choice"),
        "title": (
            "<a:EasyAwardBaftaMusic2025:1359268029850058974> **ON THE ENEMY'S DOORSTEP**",
            "<:achievement_style_1:1374174053254041640> **~~ON THE ENEMY'S DOORSTEP~~**"
        )
    },
    "Streak30": {
        "message": ("Reach a Streak of 30", "HINT: You'll need to take some annual leave after this... seriously... Democracy Applauds You!"),
        "title": (
            "<a:EasyMedal:1233854253077102653> **INFLAMMABLE**",
            "<:achievement_style_2:1374174051551154267> **~~INFLAMMABLE~~**"
        )
    },
}

# Generate messages and titles dynamically
for key, defs in ACHIEVEMENT_DEFS.items():
    achieved = achievements[key]
    globals()[f"{key}_message"] = defs["message"][0] if achieved else defs["message"][1]
    globals()[f"{key}_title"] = defs["title"][0] if achieved else defs["title"][1]

# generate embed message

helldiver_level = df['Level'].mode()[0]
helldiver_title = df['Title'].mode()[0]
helldiver_ses = df['Super Destroyer'].mode()[0]
helldiver_name = df['Helldivers'].mode()[0]
latest_note = df['Note'].iloc[-1] if not pd.isna(df['Note'].iloc[-1]) else "No notes available"

# Discord webhook configuration
WEBHOOK_URLS = {
    'PROD': config['Webhooks']['BAT'].split(','),
    'TEST': config['Webhooks']['TEST'].split(',')
}
ACTIVE_WEBHOOK = WEBHOOK_URLS['TEST'] if DEBUG else WEBHOOK_URLS['PROD']

# UID from local DCord.json (user settings)
try:
    with open('DCord.json', 'r') as f:
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
            "title": f"{helldiver_ses}\nHelldiver: {helldiver_name}",  # Empty title, will be set below
            "description": f"**Level {helldiver_level} | {helldiver_title} {TITLE_ICONS.get(df['Title'].mode()[0], '')}**\n\n\"{latest_note}\"\n\n<a:easyshine1:1349110651829747773> <a:easymedal:1233854253077102653> Achievements <a:easymedal:1233854253077102653> <a:easyshine3:1349110648528699422>\n" + 
                        f"> {CmdFavourite_title}\n" +
                        f"> *{CmdFavourite_message}*\n" +
                        f"> \n" +
                        f"> {ReliableDiver_title}\n" +
                        f"> *{ReliableDiver_message}*\n" +
                        f"> \n" +
                        f"> {DSSDiver_title}\n" +
                        f"> *{DSSDiver_message}*\n" +
                        f"> \n" +
                        f"> {OutbreakPerfected_title}\n" +
                        f"> *{OutbreakPerfected_message}*\n" +
                        f"> \n" +
                        f"> {AutomatonPerfected_title}\n" +
                        f"> *{AutomatonPerfected_message}*\n" +
                        f"> \n" +
                        f"> {IlluminatePerfected_title}\n" +
                        f"> *{IlluminatePerfected_message}*\n" +
                        f"> \n" +
                        f"> {TerminidHunter_title}\n" +
                        f"> *{TerminidHunter_message}*\n" +
                        f"> \n" +
                        f"> {AutomatonHunter_title}\n" +
                        f"> *{AutomatonHunter_message}*\n" +
                        f"> \n" +
                        f"> {IlluminateHunter_title}\n" +
                        f"> *{IlluminateHunter_message}*\n" +
                        f"> \n" +
                        f"> {MalevelonCreek_title}\n" +
                        f"> *{MalevelonCreek_message}*\n" +
                        f"> \n" +
                        f"> {DisgracefulConduct_title}\n" +
                        f"> *{DisgracefulConduct_message}*\n" +
                        f"> \n" +
                        f"> {SuperEarth_title}\n" +
                        f"> *{SuperEarth_message}*\n" +
                        f"> \n" +
                        f"> {Cyberstan_title}\n" +
                        f"> *{Cyberstan_message}*\n" +
                        f"> \n" +
                        f"> {Streak30_title}\n" +
                        f"> *{Streak30_message}*\n\n",
                        
            "color": 7257043,
            "author": {"name": "SEAF Battle Record"},
            "footer": {"text": f"\n{UID}   v{VERSION}{DEV_RELEASE}","icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356025859319926784/5cwgI15.png?ex=67eb10fe&is=67e9bf7e&hm=ab6326a9da1e76125238bf3668acac8ad1e43b24947fc6d878d7b94c8a60ab28&"},
            "image": {"url": f"https://cdn.discordapp.com/attachments/1340508329977446484/1374164186850000957/helldiversBanner.png?ex=682d0da0&is=682bbc20&hm=c80377ccc47f3e1b08661f1f48fadc8f8c171dbb9158087a9a96613a0ad366fb&"},
            "thumbnail": {"url": f"{profile_picture}"}
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
        with open('DCord.json', 'r') as f:
            dcord_data = json.load(f)
            ACTIVE_WEBHOOK = dcord_data.get('discord_webhooks', [])
        if not ACTIVE_WEBHOOK:
            logging.error("No production webhooks found in DCord.json (key: discord_webhooks).")
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