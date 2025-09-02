# Helldiver Mission Log Manager (GUI)
#
# Tracks Helldivers 2 mission data, persists user settings, exports to Excel, and
# pushes Discord webhook reports with rich embeds + presence (RPC).
#
# Credits:
# - Dean: Primary JSON data contributions, testing, debugging, cosmetic improvements
# - Adam: Original script + GUI foundations
# - Honourble mention, Copilot for handling that mundane shit like changing lists to data structs

# Times i've wished we didn't use Excel - 22
# Times we should move away from discord - 1

import tkinter as tk
from tkinter import ttk, messagebox
import requests
from datetime import datetime, timezone, timedelta
import json
import pandas as pd
import logging
from logging_config import setup_logging
from typing import Dict, List, Optional
from pypresence import Presence
import time
import configparser
import threading
import os
import subprocess
import random
import re
import webbrowser

# Manual Configuration
GWDay = "Day: 572"
GWDate = "Date: 02/09/2025"
VERSION = "1.5.003"
DEV_RELEASE = "-dev"
RPC_UPDATE_INTERVAL = 15  # seconds, this is in seconds
DATE_FORMAT = "%d-%m-%Y %H:%M:%S"

# File paths
SETTINGS_FILE = 'settings.json'
PERSISTENCE_FILE = 'persistent.json'
EXCEL_FILE_PROD = 'mission_log.xlsx'
EXCEL_FILE_TEST = 'mission_log_test.xlsx'

# Load config
config = configparser.ConfigParser()
config.read('config.config')
DISCORD_CLIENT_ID = config['Discord']['DISCORD_CLIENT_ID']

DEBUG = config.getboolean('DEBUGGING', 'DEBUG', fallback=False)
setup_logging(DEBUG)

# Theme System
def make_theme(bg, fg, entry_bg=None, entry_fg=None, button_bg=None, button_fg=None, frame_bg=None):
    return {
        ".": {"configure": {"background": bg, "foreground": fg}},
        "TLabel": {"configure": {"background": bg, "foreground": fg}},
        "TButton": {"configure": {"background": button_bg or bg, "foreground": button_fg or fg}},
        "TEntry": {"configure": {
            "background": entry_bg or bg,
            "foreground": entry_fg or fg,
            "fieldbackground": entry_bg or bg,
            "insertcolor": fg,
        }},
        "TCheckbutton": {"configure": {"background": bg, "foreground": fg}},
        "TCombobox": {"configure": {
            "background": entry_bg or bg,
            "foreground": entry_fg or fg,
            "fieldbackground": entry_bg or bg,
            "insertcolor": fg,
        }},
        "TFrame": {"configure": {"background": frame_bg or bg}},
        "TLabelframe": {"configure": {"background": frame_bg or bg, "foreground": fg}},
        "TLabelframe.Label": {"configure": {"background": frame_bg or bg, "foreground": fg}},
        "TNotebook": {"configure": {"background": bg}},
        "TNotebook.Tab": {"configure": {"background": button_bg or bg, "foreground": fg}},
    }

light_theme = make_theme(
    bg="#ffffff", fg="#000000",
    entry_bg="#ffffff", entry_fg="#000000",
    button_bg="#e0e0e0", button_fg="#000000",
    frame_bg="#ffffff"
)

dark_theme = make_theme(
    bg="#252526", fg="white",
    entry_bg="#3c3c3c", entry_fg="white",
    button_bg="#444444", button_fg="white",
    frame_bg="#252526"
)

THEMES = {
    "light": light_theme,
    "dark": dark_theme
}

def get_current_theme():
    # Return the last saved theme name (light/dark) or fallback to light.
    if os.path.exists(PERSISTENCE_FILE):
        try:
            with open(PERSISTENCE_FILE, 'r') as f:
                settings = json.load(f)
                return settings.get('theme', 'light')
        except Exception:
            pass
    return 'light'

def set_current_theme(theme_name):
    # Persist the chosen theme to the persistence file.
    settings = {}
    if os.path.exists(PERSISTENCE_FILE):
        try:
            with open(PERSISTENCE_FILE, 'r') as f:
                settings = json.load(f)
        except Exception:
            settings = {}
    settings['theme'] = theme_name
    with open(PERSISTENCE_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

ENEMY_ICONS = {
    "Automatons": config['EnemyIcons']['Automatons'],
    "Terminids": config['EnemyIcons']['Terminids'],
    "Illuminate": config['EnemyIcons']['Illuminate'],
    "Observing": config['EnemyIcons']['Observation'],
}

DIFFICULTY_ICONS = {
    "1 - TRIVIAL": config['DifficultyIcons']['1 - TRIVIAL'],
    "2 - EASY": config['DifficultyIcons']['2 - EASY'],
    "3 - MEDIUM": config['DifficultyIcons']['3 - MEDIUM'],
    "4 - CHALLENGING": config['DifficultyIcons']['4 - CHALLENGING'],
    "5 - HARD": config['DifficultyIcons']['5 - HARD'],
    "6 - EXTREME": config['DifficultyIcons']['6 - EXTREME'],
    "7 - SUICIDE MISSION": config['DifficultyIcons']['7 - SUICIDE MISSION'],
    "8 - IMPOSSIBLE": config['DifficultyIcons']['8 - IMPOSSIBLE'],
    "9 - HELLDIVE": config['DifficultyIcons']['9 - HELLDIVE'],
    "10 - SUPER HELLDIVE": config['DifficultyIcons']['10 - SUPER HELLDIVE']
}
SYSTEM_COLORS = {
    "Automatons": config['SystemColors']['Automatons'],
    "Terminids": config['SystemColors']['Terminids'],
    "Illuminate": config['SystemColors']['Illuminate']
}


PLANET_ICONS = {
    "Super Earth": config['PlanetIcons']['Human Homeworld'],
    "Cyberstan": config['PlanetIcons']['Automaton Homeworld'],
    "Malevelon Creek": config['PlanetIcons']['Malevelon Creek'],
    "Calypso": config['PlanetIcons']['Calypso'],
    "Diaspora X": config['PlanetIcons']['Gloom'],
    "Enuliale": config['PlanetIcons']['Gloom'],
    "Epsilon Phoencis VI": config['PlanetIcons']['Gloom'],
    "Gemstone Bluffs": config['PlanetIcons']['Gloom'],
    "Nabatea Secundus": config['PlanetIcons']['Gloom'],
    "Navi VII": config['PlanetIcons']['Gloom'],
    "Azur Secundus": config['PlanetIcons']['Gloom'],
    "Erson Sands": config['PlanetIcons']['Gloom'],
    "Nivel 43": config['PlanetIcons']['Gloom'],
    "Zagon Prime": config['PlanetIcons']['Gloom'],
    "Hellmire": config['PlanetIcons']['Gloom'],
    "Omicron": config['PlanetIcons']['Gloom'],
    "Oshaune": config['PlanetIcons']['Gloom'],
    "Fori Prime": config['PlanetIcons']['Gloom'],
    "Aurora Bay": config['PlanetIcons']['Jet Brigade Factories'],
    "Chort Bay": config['PlanetIcons']['Jet Brigade Factories'],
    "Widow's Harbor": config['PlanetIcons']['Free Springs Retreat'],
    "Mog": config['PlanetIcons']['Illuminate Rally Locus'],
    "Bellatrix": config['PlanetIcons']['Illuminate Rally Locus'],
    "Hydrobius": config['PlanetIcons']['Illuminate Rally Locus'],
    "Haldus": config['PlanetIcons']['Illuminate Rally Locus'],
    "Mastia": config['PlanetIcons']['Governmental'],
    "Fenrir III": config['PlanetIcons']['Science'],
    "Tarsh": config['PlanetIcons']['Governmental'],
    "Claorell": config['PlanetIcons']['Hammer'],
    "Achernar Secundus": config['PlanetIcons']['Hammer'],
    "Turing": config['PlanetIcons']['Science'],
    "Emeria": config['PlanetIcons']['Governmental'],
    "Fort Union": config['PlanetIcons']['Governmental'],
    "Fort Sanctuary": config['PlanetIcons']['Governmental'],
}


CAMPAIGN_ICONS = {
    "Defense": config['CampaignIcons']['Defense'],
    "Liberation": config['CampaignIcons']['Liberation'],
    "Invasion": config['CampaignIcons']['Invasion'],
    "High-Priority": config['CampaignIcons']['High-Priority'],
    "Attrition": config['CampaignIcons']['Attrition'],
    "Battle for Super Earth": config['CampaignIcons']['Battle for Super Earth'],
}


MISSION_ICONS = {
    "Terminate Illegal Broadcast": config['MissionIcons']['Terminate Illegal Broadcast'],
    "Pump Fuel To ICBM": config['MissionIcons']['Pump Fuel To ICBM'],
    "Upload Escape Pod Data": config['MissionIcons']['Upload Escape Pod Data'],
    "Spread Democracy": config['MissionIcons']['Spread Democracy'],
    "Conduct Geological Survey": config['MissionIcons']['Conduct Geological Survey'],
    "Launch ICBM": config['MissionIcons']['Launch ICBM'],
    "Retrieve Valuable Data": config['MissionIcons']['Retrieve Valuable Data'],
    "Blitz: Search and Destroy": config['MissionIcons']['Blitz Search and Destroy'],
    "Emergency Evacuation": config['MissionIcons']['Emergency Evacuation'],
    "Retrieve Essential Personnel": config['MissionIcons']['Retrieve Essential Personnel'],
    "Evacuate High-Value Assets": config['MissionIcons']['Evacuate High-Value Assets'],
    "Eliminate Brood Commanders": config['MissionIcons']['Eliminate Brood Commanders'],
    "Eliminate Chargers": config['MissionIcons']['Eliminate Chargers'],
    "Eliminate Impaler": config['MissionIcons']['Eliminate Impaler'],
    "Eliminate Bile Titans": config['MissionIcons']['Eliminate Bile Titans'],
    "Activate E-710 Pumps": config['MissionIcons']['Activate E-710 Pumps'],
    "Purge Hatcheries": config['MissionIcons']['Purge Hatcheries'],
    "Enable E-710 Extraction": config['MissionIcons']['Enable E-710 Extraction'],
    "Nuke Nursery": config['MissionIcons']['Nuke Nursery'],
    "Activate Terminid Control System": config['MissionIcons']['Activate Terminid Control System'],
    "Deactivate Terminid Control System": config['MissionIcons']['Deactivate Terminid Control System'],
    "Deploy Dark Fluid": config['MissionIcons']['Deploy Dark Fluid'],
    "Eradicate Terminid Swarm": config['MissionIcons']['Eradicate Terminid Swarm'],
    "Destroy Transmission Network": config['MissionIcons']['Destroy Transmission Network'],
    "Eliminate Devastators": config['MissionIcons']['Eliminate Devastators'],
    "Eliminate Automaton Hulks": config['MissionIcons']['Eliminate Automaton Hulks'],
    "Eliminate Automaton Factory Strider": config['MissionIcons']['Eliminate Automaton Factory Strider'],
    "Sabotage Supply Bases": config['MissionIcons']['Sabotage Supply Bases'],
    "Sabotage Air Base": config['MissionIcons']['Sabotage Air Base'],
    "Eradicate Automaton Forces": config['MissionIcons']['Eradicate Automaton Forces'],
    "Destroy Command Bunkers": config['MissionIcons']['Destroy Command Bunkers'],
    "Neutralize Orbital Defenses": config['MissionIcons']['Neutralize Orbital Defenses'],
    "Evacuate Colonists": config['MissionIcons']['Evacuate Colonists'],
    "Retrieve Recon Craft Intel": config['MissionIcons']['Retrieve Recon Craft Intel'],
    "Free Colony": config['MissionIcons']['Free Colony'],
    "Blitz: Destroy Illuminate Warp Ships": config['MissionIcons']['Blitz Destroy Illuminate Warp Ships'],
    "Destroy Harvesters": config['MissionIcons']['Destroy Harvesters'],
    "Extract Research Probe Data": config['MissionIcons']['Extract Research Probe Data'],
    "Collect Meteorological Data": config['MissionIcons']['Collect Meteorological Data'],
    "Collect Gloom-Infused Oil": config['MissionIcons']['Collect Gloom-Infused Oil'],
    "Blitz: Secure Research Site": config['MissionIcons']['Blitz Secure Research Site'],
    "Collect Gloom Spore Readings": config['MissionIcons']['Collect Gloom Spore Readings'],
    "Chart Terminid Tunnels": config['MissionIcons']['Chart Terminid Tunnels'],
    "Take Down Overship": config['MissionIcons']['Take Down Overship'],
    "Repel Invasion Fleet": config['MissionIcons']['Repel Invasion Fleet'],
    "Evacuate Citizens": config['MissionIcons']['Evacuate Citizens'],
    "Free The City": config['MissionIcons']['Free The City'],
    "Restore Air Quality": config['MissionIcons']['Restore Air Quality'],
    "Cleanse Infested District": config['MissionIcons']['Cleanse Infested District']
}

# Biome Banners per Planet (used as embed image backgrounds)
BIOME_BANNERS = {
    "Propus": config['BiomeBanners']['Desert Dunes'],
    "Klen Dahth II": config['BiomeBanners']['Desert Dunes'],
    "Outpost 32": config['BiomeBanners']['Desert Dunes'],
    "Lastofe": config['BiomeBanners']['Desert Dunes'],
    "Diaspora X": config['BiomeBanners']['Desert Dunes'],
    "Zagon Prime": config['BiomeBanners']['Desert Dunes'],
    "Osupsam": config['BiomeBanners']['Desert Dunes'],
    "Mastia": config['BiomeBanners']['Desert Dunes'],
    "Caramoor": config['BiomeBanners']['Desert Dunes'],
    "Heze Bay": config['BiomeBanners']['Desert Dunes'],
    "Viridia Prime": config['BiomeBanners']['Desert Dunes'],
    "Durgen": config['BiomeBanners']['Desert Dunes'],
    "Phact Bay": config['BiomeBanners']['Desert Dunes'],
    "Keid": config['BiomeBanners']['Desert Dunes'],
    "Zzaniah Prime": config['BiomeBanners']['Desert Dunes'],
    "Choohe": config['BiomeBanners']['Desert Dunes'],
    "Pilen V": config['BiomeBanners']['Desert Cliffs'],
    "Zea Rugosia": config['BiomeBanners']['Desert Cliffs'],
    "Myradesh": config['BiomeBanners']['Desert Cliffs'],
    "Azur Secundus": config['BiomeBanners']['Desert Cliffs'],
    "Erata Prime": config['BiomeBanners']['Desert Cliffs'],
    "Mortax Prime": config['BiomeBanners']['Desert Cliffs'],
    "Cerberus IIIc": config['BiomeBanners']['Desert Cliffs'],
    "Ustotu": config['BiomeBanners']['Desert Cliffs'],
    "Erson Sands": config['BiomeBanners']['Desert Cliffs'],
    "Canopus": config['BiomeBanners']['Desert Cliffs'],
    "Hydrobius": config['BiomeBanners']['Desert Cliffs'],
    "Polaris Prime": config['BiomeBanners']['Desert Cliffs'],
    "Darrowsport": config['BiomeBanners']['Acidic Badlands'],
    "Darius II": config['BiomeBanners']['Acidic Badlands'],
    "Chort Bay": config['BiomeBanners']['Acidic Badlands'],
    "Leng Secundus": config['BiomeBanners']['Acidic Badlands'],
    "Rirga Bay": config['BiomeBanners']['Acidic Badlands'],
    "Shete": config['BiomeBanners']['Acidic Badlands'],
    "Skaash": config['BiomeBanners']['Acidic Badlands'],
    "Wraith": config['BiomeBanners']['Acidic Badlands'],
    "Slif": config['BiomeBanners']['Acidic Badlands'],
    "Wilford Station": config['BiomeBanners']['Acidic Badlands'],
    "Botein": config['BiomeBanners']['Acidic Badlands'],
    "Wasat": config['BiomeBanners']['Acidic Badlands'],
    "Esker": config['BiomeBanners']['Acidic Badlands'],
    "Charbal-VII": config['BiomeBanners']['Acidic Badlands'],
    "Kraz": config['BiomeBanners']['Rocky Canyons'],
    "Hydrofall Prime": config['BiomeBanners']['Rocky Canyons'],
    "Myrium": config['BiomeBanners']['Rocky Canyons'],
    "Vernen Wells": config['BiomeBanners']['Rocky Canyons'],
    "Calypso": config['BiomeBanners']['Rocky Canyons'],
    "Achird III": config['BiomeBanners']['Rocky Canyons'],
    "Azterra": config['BiomeBanners']['Rocky Canyons'],
    "Senge 23": config['BiomeBanners']['Rocky Canyons'],
    "Emeria": config['BiomeBanners']['Rocky Canyons'],
    "Fori Prime": config['BiomeBanners']['Rocky Canyons'],
    "Mekbuda": config['BiomeBanners']['Rocky Canyons'],
    "Effluvia": config['BiomeBanners']['Rocky Canyons'],
    "Pioneer II": config['BiomeBanners']['Rocky Canyons'],
    "Castor": config['BiomeBanners']['Rocky Canyons'],
    "Prasa": config['BiomeBanners']['Rocky Canyons'],
    "Kuma": config['BiomeBanners']['Rocky Canyons'],
	"Widow's Harbor": config['BiomeBanners']['Moon'],
	"RD-4": config['BiomeBanners']['Moon'],
	"Claorell": config['BiomeBanners']['Moon'],
	"Maia": config['BiomeBanners']['Moon'],
	"Curia": config['BiomeBanners']['Moon'],
	"Sirius": config['BiomeBanners']['Moon'],
	"Rasp": config['BiomeBanners']['Moon'],
	"Terrek": config['BiomeBanners']['Moon'],
	"Dolph": config['BiomeBanners']['Moon'],
	"Fenrir III": config['BiomeBanners']['Moon'],
	"Zosma": config['BiomeBanners']['Moon'],
	"Euphoria III": config['BiomeBanners']['Moon'],
	"Primordia": config['BiomeBanners']['Volcanic Jungle'],
	"Rogue 5": config['BiomeBanners']['Volcanic Jungle'],
	"Alta V": config['BiomeBanners']['Volcanic Jungle'],
	"Mantes": config['BiomeBanners']['Volcanic Jungle'],
	"Gaellivare": config['BiomeBanners']['Volcanic Jungle'],
	"Meissa": config['BiomeBanners']['Volcanic Jungle'],
	"Spherion": config['BiomeBanners']['Volcanic Jungle'],
	"Kirrik": config['BiomeBanners']['Volcanic Jungle'],
	"Baldrick Prime": config['BiomeBanners']['Volcanic Jungle'],
	"Zegema Paradise": config['BiomeBanners']['Volcanic Jungle'],
	"Irulta": config['BiomeBanners']['Volcanic Jungle'],
	"Regnus": config['BiomeBanners']['Volcanic Jungle'],
	"Navi VII": config['BiomeBanners']['Volcanic Jungle'],
	"Oasis": config['BiomeBanners']['Volcanic Jungle'],
	"Pollux 31": config['BiomeBanners']['Volcanic Jungle'],
	"Aesir Pass": config['BiomeBanners']['Deadlands'],
	"Alderidge Cove": config['BiomeBanners']['Deadlands'],
	"Penta": config['BiomeBanners']['Deadlands'],
	"Ain-5": config['BiomeBanners']['Deadlands'],
	"Skat Bay": config['BiomeBanners']['Deadlands'],
	"Alaraph": config['BiomeBanners']['Deadlands'],
	"Veil": config['BiomeBanners']['Deadlands'],
	"Troost": config['BiomeBanners']['Deadlands'],
	"Haka": config['BiomeBanners']['Deadlands'],
	"Nivel 43": config['BiomeBanners']['Deadlands'],
	"Pandion-XXIV": config['BiomeBanners']['Deadlands'],
	"Cirrus": config['BiomeBanners']['Deadlands'],
	"Mort": config['BiomeBanners']['Deadlands'],
	"Iridica": config['BiomeBanners']['Ethereal Jungle'],
	"Seyshel Beach": config['BiomeBanners']['Ethereal Jungle'],
	"Ursica XI": config['BiomeBanners']['Ethereal Jungle'],
	"Acubens Prime": config['BiomeBanners']['Ethereal Jungle'],
	"Fort Justice": config['BiomeBanners']['Ethereal Jungle'],
	"Sulfura": config['BiomeBanners']['Ethereal Jungle'],
	"Alamak VII": config['BiomeBanners']['Ethereal Jungle'],
	"Tibit": config['BiomeBanners']['Ethereal Jungle'],
	"Mordia 9": config['BiomeBanners']['Ethereal Jungle'],
	"Emorath": config['BiomeBanners']['Ethereal Jungle'],
	"Shallus": config['BiomeBanners']['Ethereal Jungle'],
	"Vindemitarix Prime": config['BiomeBanners']['Ethereal Jungle'],
	"Zefia": config['BiomeBanners']['Ethereal Jungle'],
	"Bekvam III": config['BiomeBanners']['Ethereal Jungle'],
	"Turing": config['BiomeBanners']['Ethereal Jungle'],
	"New Haven": config['BiomeBanners']['Ionic Jungle'],
	"Prosperity Falls": config['BiomeBanners']['Ionic Jungle'],
	"Veld": config['BiomeBanners']['Ionic Jungle'],
	"Malevelon Creek": config['BiomeBanners']['Ionic Jungle'],
	"Siemnot": config['BiomeBanners']['Ionic Jungle'],
	"Alairt III": config['BiomeBanners']['Ionic Jungle'],
	"Merak": config['BiomeBanners']['Ionic Jungle'],
	"Gemma": config['BiomeBanners']['Ionic Jungle'],
	"Minchir": config['BiomeBanners']['Ionic Jungle'],
	"Kuper": config['BiomeBanners']['Ionic Jungle'],
	"Brink-2": config['BiomeBanners']['Ionic Jungle'],
	"Peacock": config['BiomeBanners']['Ionic Jungle'],
	"Genesis Prime": config['BiomeBanners']['Ionic Jungle'],
	"New Kiruna": config['BiomeBanners']['Icy Glaciers'],
	"Borea": config['BiomeBanners']['Icy Glaciers'],
	"Marfark": config['BiomeBanners']['Icy Glaciers'],
	"Epsilon Phoencis VI": config['BiomeBanners']['Icy Glaciers'],
	"Kelvinor": config['BiomeBanners']['Icy Glaciers'],
	"Vog-Sojoth": config['BiomeBanners']['Icy Glaciers'],
	"Alathfar XI": config['BiomeBanners']['Icy Glaciers'],
	"Okul VI": config['BiomeBanners']['Icy Glaciers'],
	"Julheim": config['BiomeBanners']['Icy Glaciers'],
	"Hadar": config['BiomeBanners']['Icy Glaciers'],
	"Mog": config['BiomeBanners']['Icy Glaciers'],
	"Vandalon IV": config['BiomeBanners']['Icy Glaciers'],
	"Arkturus": config['BiomeBanners']['Icy Glaciers'],
	"Hesoe Prime": config['BiomeBanners']['Icy Glaciers'],
	"Vega Bay": config['BiomeBanners']['Icy Glaciers'],
	"New Stockholm": config['BiomeBanners']['Icy Glaciers'],
	"Heeth": config['BiomeBanners']['Icy Glaciers'],
	"Choepessa IV": config['BiomeBanners']['Boneyard'],
	"Martyr's Bay": config['BiomeBanners']['Boneyard'],
	"Lesath": config['BiomeBanners']['Boneyard'],
	"Cyberstan": config['BiomeBanners']['Boneyard'],
	"Deneb Secundus": config['BiomeBanners']['Boneyard'],
	"Acrux IX": config['BiomeBanners']['Boneyard'],
	"Inari": config['BiomeBanners']['Boneyard'],
	"Estanu": config['BiomeBanners']['Boneyard'],
	"Stor Tha Prime": config['BiomeBanners']['Boneyard'],
	"Halies Port": config['BiomeBanners']['Boneyard'],
	"Oslo Station": config['BiomeBanners']['Boneyard'],
	"Igla": config['BiomeBanners']['Boneyard'],
	"Krakatwo": config['BiomeBanners']['Boneyard'],
	"Grafmere": config['BiomeBanners']['Boneyard'],
	"Eukoria": config['BiomeBanners']['Boneyard'],
	"Tien Kwan": config['BiomeBanners']['Boneyard'],
	"Pathfinder V": config['BiomeBanners']['Plains'],
	"Fort Union": config['BiomeBanners']['Plains'],
	"Volterra": config['BiomeBanners']['Plains'],
	"Gemstone Bluffs": config['BiomeBanners']['Plains'],
	"Acamar IV": config['BiomeBanners']['Plains'],
	"Achernar Secundus": config['BiomeBanners']['Plains'],
	"Electra Bay": config['BiomeBanners']['Plains'],
	"Afoyay Bay": config['BiomeBanners']['Plains'],
	"Matar Bay": config['BiomeBanners']['Plains'],
	"Reaf": config['BiomeBanners']['Plains'],
	"Termadon": config['BiomeBanners']['Plains'],
	"Fenmire": config['BiomeBanners']['Plains'],
	"The Weir": config['BiomeBanners']['Plains'],
	"Bellatrix": config['BiomeBanners']['Plains'],
	"Oshaune": config['BiomeBanners']['Plains'],
	"Varylia 5": config['BiomeBanners']['Plains'],
	"Hort": config['BiomeBanners']['Plains'],
	"Draupnir": config['BiomeBanners']['Plains'],
	"Obari": config['BiomeBanners']['Plains'],
	"Mintoria": config['BiomeBanners']['Plains'],
	"Midasburg": config['BiomeBanners']['Tundra'],
	"Demiurg": config['BiomeBanners']['Tundra'],
	"Kerth Secundus": config['BiomeBanners']['Tundra'],
	"Aurora Bay": config['BiomeBanners']['Tundra'],
	"Martale": config['BiomeBanners']['Tundra'],
	"Crucible": config['BiomeBanners']['Tundra'],
	"Shelt": config['BiomeBanners']['Tundra'],
	"Trandor": config['BiomeBanners']['Tundra'],
	"Andar": config['BiomeBanners']['Tundra'],
	"Diluvia": config['BiomeBanners']['Tundra'],
	"Bunda Secundus": config['BiomeBanners']['Tundra'],
	"Ilduna Prime": config['BiomeBanners']['Tundra'],
	"Omicron": config['BiomeBanners']['Tundra'],
	"Ras Algethi": config['BiomeBanners']['Tundra'],
	"Duma Tyr": config['BiomeBanners']['Tundra'],
	"Adhara": config['BiomeBanners']['Scorched Moor'],
	"Hellmire": config['BiomeBanners']['Scorched Moor'],
	"Imber": config['BiomeBanners']['Scorched Moor'],
	"Menkent": config['BiomeBanners']['Scorched Moor'],
	"Blistica": config['BiomeBanners']['Scorched Moor'],
	"Herthon Secundus": config['BiomeBanners']['Scorched Moor'],
	"Pöpli IX": config['BiomeBanners']['Scorched Moor'],
	"Partion": config['BiomeBanners']['Scorched Moor'],
	"Wezen": config['BiomeBanners']['Scorched Moor'],
	"Marre IV": config['BiomeBanners']['Scorched Moor'],
	"Karlia": config['BiomeBanners']['Scorched Moor'],
	"Maw": config['BiomeBanners']['Scorched Moor'],
	"Kneth Port": config['BiomeBanners']['Scorched Moor'],
	"Grand Errant": config['BiomeBanners']['Scorched Moor'],
	"Fort Sanctuary": config['BiomeBanners']['Ionic Crimson'],
	"Elysian Meadows": config['BiomeBanners']['Ionic Crimson'],
	"Acrab XI": config['BiomeBanners']['Ionic Crimson'],
	"Enuliale": config['BiomeBanners']['Ionic Crimson'],
	"Liberty Ridge": config['BiomeBanners']['Ionic Crimson'],
	"Stout": config['BiomeBanners']['Ionic Crimson'],
	"Gatria": config['BiomeBanners']['Ionic Crimson'],
	"Freedom Peak": config['BiomeBanners']['Ionic Crimson'],
	"Ubanea": config['BiomeBanners']['Ionic Crimson'],
	"Valgaard": config['BiomeBanners']['Ionic Crimson'],
	"Valmox": config['BiomeBanners']['Ionic Crimson'],
	"Overgoe Prime": config['BiomeBanners']['Ionic Crimson'],
	"Providence": config['BiomeBanners']['Ionic Crimson'],
	"Kharst": config['BiomeBanners']['Ionic Crimson'],
	"Gunvald": config['BiomeBanners']['Ionic Crimson'],
	"Yed Prior": config['BiomeBanners']['Ionic Crimson'],
	"Ingmar": config['BiomeBanners']['Ionic Crimson'],
	"Crimsica": config['BiomeBanners']['Ionic Crimson'],
	"Charon Prime": config['BiomeBanners']['Ionic Crimson'],
	"Clasa": config['BiomeBanners']['Basic Swamp'],
	"Seasse": config['BiomeBanners']['Basic Swamp'],
	"Parsh": config['BiomeBanners']['Basic Swamp'],
	"East Iridium Trading Bay": config['BiomeBanners']['Basic Swamp'],
	"Gacrux": config['BiomeBanners']['Basic Swamp'],
	"Barabos": config['BiomeBanners']['Basic Swamp'],
	"Ivis": config['BiomeBanners']['Basic Swamp'],
	"Fornskogur II": config['BiomeBanners']['Basic Swamp'],
	"Nabatea Secundus": config['BiomeBanners']['Basic Swamp'],
	"Haldus": config['BiomeBanners']['Basic Swamp'],
	"Caph": config['BiomeBanners']['Basic Swamp'],
	"Bore Rock": config['BiomeBanners']['Basic Swamp'],
	"X-45": config['BiomeBanners']['Basic Swamp'],
	"Pherkad Secundus": config['BiomeBanners']['Basic Swamp'],
	"Krakabos": config['BiomeBanners']['Basic Swamp'],
	"Asperoth Prime": config['BiomeBanners']['Basic Swamp'],
	"Atrama": config['BiomeBanners']['Haunted Swamp'],
	"Setia": config['BiomeBanners']['Haunted Swamp'],
	"Tarsh": config['BiomeBanners']['Haunted Swamp'],
	"Gar Haren": config['BiomeBanners']['Haunted Swamp'],
	"Merga IV": config['BiomeBanners']['Haunted Swamp'],
	"Ratch": config['BiomeBanners']['Haunted Swamp'],
	"Bashyr": config['BiomeBanners']['Haunted Swamp'],
	"Nublaria I": config['BiomeBanners']['Haunted Swamp'],
	"Solghast": config['BiomeBanners']['Haunted Swamp'],
	"Iro": config['BiomeBanners']['Haunted Swamp'],
	"Socorro III": config['BiomeBanners']['Haunted Swamp'],
	"Khandark": config['BiomeBanners']['Haunted Swamp'],
	"Klaka 5": config['BiomeBanners']['Haunted Swamp'],
	"Skitter": config['BiomeBanners']['Haunted Swamp'],
    "Angel's Venture": config['BiomeBanners']['Fractured Planet'],
    "Moradesh": config['BiomeBanners']['Fractured Planet'],
    "Meridia": config['BiomeBanners']['Black Hole'],
    "Super Earth": config['BiomeBanners']['Super Earth']
}


SUBFACTION_ICONS = {
    "Automaton Legion": config['SubfactionIcons']['AutomatonLegion'],
    "Terminid Horde": config['SubfactionIcons']['TerminidHorde'],
    "Illuminate Cult": config['SubfactionIcons']['IlluminateCult'],
    "Jet Brigade": config['SubfactionIcons']['JetBrigade'],
    "Predator Strain": config['SubfactionIcons']['PredatorStrain'],
    "Incineration Corps": config['SubfactionIcons']['IncinerationCorps'],
    "Jet Brigade & Incineration Corps": config['SubfactionIcons']['JetBrigadeIncinerationCorps'],
    "Spore Burst Strain": config['SubfactionIcons']['SporeBurstStrain'],
    "The Great Host": config['SubfactionIcons']['TheGreatHost']
}


DSS_ICONS = {
    "Eagle Storm": config['MiscIcon']['Eagle Storm'],
    "Orbital Blockade": config['MiscIcon']['Orbital Blockade'],
    "Heavy Ordnance Distribution": config['MiscIcon']['Heavy Ordnance Distribution'],
    "Eagle Blockade": config['MiscIcon']['Eagle Blockade']
}


TITLE_ICONS = {
    "CADET": config['TitleIcons']['CADET'],
    "SPACE CADET": config['TitleIcons']['SPACE CADET'], 
    "SERGEANT": config['TitleIcons']['SERGEANT'],
    "MASTER SERGEANT": config['TitleIcons']['MASTER SERGEANT'],
    "CHIEF": config['TitleIcons']['CHIEF'],
    "SPACE CHIEF PRIME": config['TitleIcons']['SPACE CHIEF PRIME'],
    "DEATH CAPTAIN": config['TitleIcons']['DEATH CAPTAIN'],
    "MARSHAL": config['TitleIcons']['MARSHAL'],
    "STAR MARSHAL": config['TitleIcons']['STAR MARSHAL'],
    "ADMIRAL": config['TitleIcons']['ADMIRAL'], 
    "SKULL ADMIRAL": config['TitleIcons']['SKULL ADMIRAL'],
    "FLEET ADMIRAL": config['TitleIcons']['FLEET ADMIRAL'],
    "ADMIRABLE ADMIRAL": config['TitleIcons']['ADMIRABLE ADMIRAL'],
    "COMMANDER": config['TitleIcons']['COMMANDER'],
    "GALACTIC COMMANDER": config['TitleIcons']['GALACTIC COMMANDER'],
    "HELL COMMANDER": config['TitleIcons']['HELL COMMANDER'],
    "GENERAL": config['TitleIcons']['GENERAL'],
    "5-STAR GENERAL": config['TitleIcons']['5-STAR GENERAL'],
    "10-STAR GENERAL": config['TitleIcons']['10-STAR GENERAL'],
    "PRIVATE": config['TitleIcons']['PRIVATE'],
    "SUPER PRIVATE": config['TitleIcons']['SUPER PRIVATE'],
    "SUPER CITIZEN": config['TitleIcons']['SUPER CITIZEN'],
    "VIPER COMMANDO": config['TitleIcons']['VIPER COMMANDO'],
    "FIRE SAFETY OFFICER": config['TitleIcons']['FIRE SAFETY OFFICER'],
    "EXPERT EXTERMINATOR": config['TitleIcons']['EXPERT EXTERMINATOR'],
    "FREE OF THOUGHT": config['TitleIcons']['FREE OF THOUGHT'],
    "SUPER PEDESTRIAN": config['TitleIcons']['SUPER PEDESTRIAN'],
    "ASSAULT INFANTRY": config['TitleIcons']['ASSAULT INFANTRY'],
    "SERVANT OF FREEDOM": config['TitleIcons']['SERVANT OF FREEDOM'],
    "SUPER SHERIFF": config['TitleIcons']['SUPER SHERIFF'],
    "DECORATED HERO": config['TitleIcons']['DECORATED HERO'],
    "EXTRA JUDICIAL": config['TitleIcons']['EXTRA JUDICIAL'],
    "EXEMPLARY SUBJECT": config['TitleIcons']['EXEMPLARY SUBJECT'],
    "ROOKIE": config['TitleIcons']['ROOKIE'],
    "BURIER OF HEADS": config['TitleIcons']['BURIER OF HEADS']
}


PROFILE_PICTURES = {
    "B-01 Tactical": config['ProfilePictures']['B-01 Tactical'],
    "TR-7 Ambassador of the Brand": config['ProfilePictures']['TR-7 Ambassador of the Brand'],
    "TR-9 Cavalier of Democracy": config['ProfilePictures']['TR-9 Cavalier of Democracy'],
    "TR-62 Knight": config['ProfilePictures']['TR-62 Knight'],
    "DP-53 Savior of the Free": config['ProfilePictures']['DP-53 Savior of the Free'],
    "TR-117 Alpha Commander": config['ProfilePictures']['TR-117 Alpha Commander'],
    "SC-37 Legionnaire": config['ProfilePictures']['SC-37 Legionnaire'],
    "SC-15 Drone Master": config['ProfilePictures']['SC-15 Drone Master'],
    "SC-34 Infiltrator": config['ProfilePictures']['SC-34 Infiltrator'],
    "FS-05 Marksman": config['ProfilePictures']['FS-05 Marksman'],
    "CD-35 Trench Engineer": config['ProfilePictures']['CD-35 Trench Engineer'],
    "CM-09 Bonesnapper": config['ProfilePictures']['CM-09 Bonesnapper'],
    "DP-40 Hero of the Federation": config['ProfilePictures']['DP-40 Hero of the Federation'],
    "FS-23 Battle Master": config['ProfilePictures']['FS-23 Battle Master'],
    "SC-30 Trailblazer Scout": config['ProfilePictures']['SC-30 Trailblazer Scout'],
    "SA-04 Combat Technician": config['ProfilePictures']['SA-04 Combat Technician'],
    "CM-14 Physician": config['ProfilePictures']['CM-14 Physician'],
    "DP-11 Champion of the People": config['ProfilePictures']['DP-11 Champion of the People'],
    "SA-25 Steel Trooper": config['ProfilePictures']['SA-25 Steel Trooper'],
    "SA-12 Servo Assisted": config['ProfilePictures']['SA-12 Servo Assisted'],
    "SA-32 Dynamo": config['ProfilePictures']['SA-32 Dynamo'],
    "B-24 Enforcer": config['ProfilePictures']['B-24 Enforcer'],
    "CE-74 Breaker": config['ProfilePictures']['CE-74 Breaker'],
    "B-27 Fortified Commando": config['ProfilePictures']['B-27 Fortified Commando'],
    "FS-38 Eradicator": config['ProfilePictures']['FS-38 Eradicator'],
    "B-08 Light Gunner": config['ProfilePictures']['B-08 Light Gunner'],
    "FS-61 Dreadnought": config['ProfilePictures']['FS-61 Dreadnought'],
    "FS-11 Executioner": config['ProfilePictures']['FS-11 Executioner'],
    "CM-21 Trench Paramedic": config['ProfilePictures']['CM-21 Trench Paramedic'],
    "CE-81 Juggernaut": config['ProfilePictures']['CE-81 Juggernaut'],
    "FS-34 Exterminator": config['ProfilePictures']['FS-34 Exterminator'],
    "CE-67 Titan": config['ProfilePictures']['CE-67 Titan'],
    "CM-17 Butcher": config['ProfilePictures']['CM-17 Butcher'],
    "EX-03 Prototype 3": config['ProfilePictures']['EX-03 Prototype 3'],
    "EX-16 Prototype 16": config['ProfilePictures']['EX-16 Prototype 16'],
    "EX-00 Prototype X": config['ProfilePictures']['EX-00 Prototype X'],
    "CE-27 Ground Breaker": config['ProfilePictures']['CE-27 Ground Breaker'],
    "CE-07 Demolition Specialist": config['ProfilePictures']['CE-07 Demolition Specialist'],
    "FS-55 Devastator": config['ProfilePictures']['FS-55 Devastator'],
    "CM-10 Clinician": config['ProfilePictures']['CM-10 Clinician'],
    "FS-37 Ravager": config['ProfilePictures']['FS-37 Ravager'],
    "CW-9 White Wolf": config['ProfilePictures']['CW-9 White Wolf'],
    "CE-64 Grenadier": config['ProfilePictures']['CE-64 Grenadier'],
    "CW-36 Winter Warrior": config['ProfilePictures']['CW-36 Winter Warrior'],
    "CW-22 Kodiak": config['ProfilePictures']['CW-22 Kodiak'],
    "CW-4 Arctic Ranger": config['ProfilePictures']['CW-4 Arctic Ranger'],
    "PH-56 Jaguar": config['ProfilePictures']['PH-56 Jaguar'],
    "CE-101 Guerilla Gorilla": config['ProfilePictures']['CE-101 Guerilla Gorilla'],
    "PH-9 Predator": config['ProfilePictures']['PH-9 Predator'],
    "PH-202 Twigsnapper": config['ProfilePictures']['PH-202 Twigsnapper'],
    "TR-40 Gold Eagle": config['ProfilePictures']['TR-40 Gold Eagle'],
    "I-44 Salamander": config['ProfilePictures']['I-44 Salamander'],
    "I-92 Fire Fighter": config['ProfilePictures']['I-92 Fire Fighter'],
    "I-09 Heatseeker": config['ProfilePictures']['I-09 Heatseeker'],
    "I-102 Draconaught": config['ProfilePictures']['I-102 Draconaught'],
    "AF-52 Lockdown": config['ProfilePictures']['AF-52 Lockdown'],
    "AF-91 Field Chemist": config['ProfilePictures']['AF-91 Field Chemist'],
    "AF-50 Noxious Ranger": config['ProfilePictures']['AF-50 Noxious Ranger'],
    "AF-02 Haz-Master": config['ProfilePictures']['AF-02 Haz-Master'],
    "DP-00 Tactical": config['ProfilePictures']['DP-00 Tactical'],
    "UF-84 Doubt Killer": config['ProfilePictures']['UF-84 Doubt Killer'],
    "UF-50 Bloodhound": config['ProfilePictures']['UF-50 Bloodhound'],
    "UF-16 Inspector": config['ProfilePictures']['UF-16 Inspector'],
    "SR-64 Cinderblock": config['ProfilePictures']['SR-64 Cinderblock'],
    "SR-24 Street Scout": config['ProfilePictures']['SR-24 Street Scout'],
    "SR-18 Roadblock": config['ProfilePictures']['SR-18 Roadblock'],
    "AC-1 Dutiful": config['ProfilePictures']['AC-1 Dutiful'],
    "AC-2 Obedient": config['ProfilePictures']['AC-2 Obedient'],
    "IE-57 Hell-Bent": config['ProfilePictures']['IE-57 Hell-Bent'],
    "IE-3 Martyr": config['ProfilePictures']['IE-3 Martyr'], 
    "IE-12 Righteous": config['ProfilePictures']['IE-12 Righteous'],
    "B-22 Model Citizen": config['ProfilePictures']['B-22 Model Citizen'],
    "GS-11 Democracy's Deputy": config['ProfilePictures']['GS-11 Democracy\'s Deputy'],
    "GS-17 Frontier Marshal": config['ProfilePictures']['GS-17 Frontier Marshal'],
    "GS-66 Lawmaker": config['ProfilePictures']['GS-66 Lawmaker'],
    "RE-824 Bearer of the Standard": config['ProfilePictures']['RE-824 Bearer of the Standard'],
    "RE-2310 Honorary Guard": config['ProfilePictures']['RE-2310 Honorary Guard'],
    "RE-1861 Parade Commander": config['ProfilePictures']['RE-1861 Parade Commander'],
    "BP-20 Corrections Officer": config['ProfilePictures']['BP-20 Corrections Officer'],
    "BP-32 Jackboot": config['ProfilePictures']['BP-32 Jackboot'],
    "BP-77 Grand Juror": config['ProfilePictures']['BP-77 Grand Juror'],
    "AD-11 Livewire": config['ProfilePictures']['AD-11 Livewire'],
    "AD-26 Bleeding Edge": config['ProfilePictures']['AD-26 Bleeding Edge'],
    "AD-49 Apollonian": config['ProfilePictures']['AD-49 Apollonian'],
    "A-9 Helljumper": config['ProfilePictures']['A-9 Helljumper'],
    "A-35 Recon": config['ProfilePictures']['A-35 Recon'],
    "DS-191 Scorpion": config['ProfilePictures']['DS-191 Scorpion'],
    "DS-42 Federation's Blade": config['ProfilePictures']['DS-42 Federation\'s Blade']
}

def get_enemy_icon(enemy_type: str) -> str:
    # Return enemy icon emoji (empty string fallback).
    return ENEMY_ICONS.get(enemy_type, "NaN")

def get_difficulty_icon(difficulty: str) -> str:
    # Return difficulty icon.
    return DIFFICULTY_ICONS.get(difficulty, "NaN")

def get_planet_icon(planet: str) -> str:
    # Return planet icon or empty string.
    return PLANET_ICONS.get(planet, "")

def get_system_color(enemy_type: str) -> int:
    # Return embed color integer for enemy type.
    return int(SYSTEM_COLORS.get(enemy_type, "0"))

def get_campaign_icon(mission_category: str) -> str:
    # Return campaign icon.
    return CAMPAIGN_ICONS.get(mission_category, "")

def get_mission_icon(mission_type: str) -> str:
    # Return mission type icon.
    return MISSION_ICONS.get(mission_type, "")

def get_biome_banner(planet: str) -> str:
    # Return biome banner URL for planet.
    return BIOME_BANNERS.get(planet, "")

def get_dss_icon(dss_modifier: str) -> str:
    # Return DSS modifier icon.
    return DSS_ICONS.get(dss_modifier, "")

def get_title_icon(title: str) -> str:
    # Return title decoration icon.
    return TITLE_ICONS.get(title, "")

def get_profile_picture(profile_picture: str) -> str:
    # Return profile picture URL.
    return PROFILE_PICTURES.get(profile_picture, "")

def normalize_subfaction_name(subfaction: str) -> str:
    # Normalize subfaction name. - A: is this even used rn?
    normalized = " ".join(subfaction.split()).title()
    replacements = {
        "Jet Brigade": "JetBrigade",
        "Predator Strain": "PredatorStrain",
        "Incineration Corps": "IncinerationCorps",
        "Jet Brigade & Incineration Corps": "JetBrigadeIncinerationCorps",
        "Spore Burst Strain": "SporeBurstStrain",
        "The Great Host": "TheGreatHost"
    }
    return replacements.get(normalized, normalized)

def get_subfaction_icon(subfaction_type: str) -> str:
    # Return subfaction icon (empty if missing).
    icon = SUBFACTION_ICONS.get(subfaction_type, "NaN")
    logging.info(f"Getting subfaction icon for '{subfaction_type}', found: {icon}")
    if icon == "NaN":
        icon = ""
    return icon

def total_missions():
    df = pd.read_excel('mission_log_test.xlsx') if DEBUG else pd.read_excel('mission_log.xlsx')
    total_rows = len(df)
    return total_rows

class MissionLogGUI:
    def __init__(self, root: tk.Tk) -> None:
        # Initialize the GUI application.
        self.root = root
        if DEBUG:
            self.root.title("Helldiver Mission Log Manager v-{} DEBUG:{}".format(VERSION, DEBUG))
        else:
            self.root.title("Helldiver Mission Log Manager v-{}".format(VERSION))
        self.root.resizable(False, False)
        self.current_theme = "light"  # Default theme
        self.RPC = None
        self.last_rpc_update = 0
        def load_icon():
            try:
                icon = tk.PhotoImage(file='SuperEarth.png')
                self.root.after(0, lambda: self.root.iconphoto(False, icon))
            except Exception as e:
                logging.error(f"Failed to load icon: {e}")

        threading.Thread(target=load_icon, daemon=True).start()

    # Core state 
        self.settings_file = SETTINGS_FILE
        self.persistence_file = PERSISTENCE_FILE
        self._setup_variables()
        self._setup_discord_rpc()
        self._create_main_frame()
        self._setup_ui()
        self.root.after(100, self.load_settings)
        self.root.after(2000, self._periodic_rpc_update)

    def toggle_theme(self):
        new_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme(new_theme)

    def apply_theme(self, theme_name):
        if theme_name not in THEMES:
            logging.error(f"Unknown theme: {theme_name}")
            return
            
        theme = THEMES[theme_name]
        style = ttk.Style()
        style.theme_use('clam')
        
    # Apply theme styles
        for widget_type, settings in theme.items():
            if 'configure' in settings:
                try:
                    style.configure(widget_type, **settings['configure'])
                except Exception as e:
                    logging.error(f"Error applying theme to {widget_type}: {e}")
            if 'map' in settings:
                        try:
                            style.map(widget_type, **settings['map'])
                        except Exception as e:
                            logging.error(f"Error applying map for {widget_type}: {e}")
                
        
    # theme related tweaks
        if theme_name == 'dark':
            self.root.option_add("*TCombobox*Listbox*Background", '#2d2d2d')
            self.root.option_add("*TCombobox*Listbox*Foreground", 'white')
            style.configure('TCombobox', foreground='black', fieldbackground='#2d2d2d')
        else:
            self.root.option_add("*TCombobox*Listbox*Background", '#ffffff')
            self.root.option_add("*TCombobox*Listbox*Foreground", 'black')
            style.configure('TCombobox', foreground='black', fieldbackground='#ffffff')
        
        if '.' in theme and 'configure' in theme['.']:
            root_bg = theme['.']['configure'].get('background')
            if root_bg:
                self.root.configure(background=root_bg)
        
        if 'TFrame' in theme and 'configure' in theme['TFrame']:
            frame_bg = theme['TFrame']['configure'].get('background')
            if frame_bg:
                style.configure('Custom.TFrame', background=frame_bg)
                self.frame.configure(style='Custom.TFrame')
        
        self.current_theme = theme_name
        
        settings = {}
        try:
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        
        settings['theme'] = theme_name
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=4)

        self._update_widget_styles(self.root, theme_name)

    def _update_widget_styles(self, widget, theme_name):
        theme = THEMES[theme_name]
        tframe = theme.get('TFrame', {}).get('configure', {})
        tlabel = theme.get('TLabel', {}).get('configure', {})
        tbutton = theme.get('TButton', {}).get('configure', {})
        if isinstance(widget, (tk.Frame, ttk.Frame, ttk.LabelFrame)):
            bg = tframe.get('background', None)
            if bg:
                try:
                    widget.configure(background=bg)
                except Exception:
                    pass
        elif isinstance(widget, (tk.Label, ttk.Label)):
            fg = tlabel.get('foreground', None)
            bg = tlabel.get('background', None)
            if fg or bg:
                try:
                    widget.configure(foreground=fg, background=bg)
                except Exception:
                    pass
        elif isinstance(widget, (tk.Button, ttk.Button)):
            fg = tbutton.get('foreground', None)
            bg = tbutton.get('background', None)
            if fg or bg:
                try:
                    widget.configure(foreground=fg, background=bg)
                except Exception:
                    pass
        for child in widget.winfo_children():
            self._update_widget_styles(child, theme_name)

    def _periodic_rpc_update(self) -> None:
        try:
            self._update_discord_presence()
        except Exception as e:
            logging.error(f"Error in periodic RPC update: {e}")
        finally:
            self.root.after(RPC_UPDATE_INTERVAL * 1000, self._periodic_rpc_update)

    def _setup_variables(self) -> None:
    # Initialize tkinter variables with validation.
        self.sector = tk.StringVar()
        self.planet = tk.StringVar()
        self.mega_cities = tk.StringVar()
        self.mission_type = tk.StringVar()
        self.kills = tk.StringVar()
        self.deaths = tk.StringVar()
        self.enemy_type = tk.StringVar()
        self.subfaction_type = tk.StringVar()
        self.Helldivers = tk.StringVar()
        self.mission_category = tk.StringVar()
        self.rating = tk.StringVar(value="Outstanding Patriotism")
        self.level = tk.IntVar()
        self.title = tk.StringVar()
        self.difficulty = tk.StringVar()
        self.MO = tk.BooleanVar()
        self.DSS = tk.BooleanVar()
        self.DSSMod = tk.StringVar()
        self.report_style = tk.StringVar(value='Modern')
        self.note = tk.StringVar()
        self.shipName1 = tk.StringVar()
        self.shipName2 = tk.StringVar()
        self.FullShipName = tk.StringVar()
        self.profile_picture = tk.StringVar()

        validate_cmd = self.root.register(self._validate_numeric_input)
        self.kills.trace_add("write", lambda *args: self._validate_field(self.kills))
        self.deaths.trace_add("write", lambda *args: self._validate_field(self.deaths))

    def _validate_numeric_input(self, value: str) -> bool:
        if not value:
            return True
        try:
            return 0 <= int(value) <= 999999
        except ValueError:
            return False

    def _validate_field(self, var: tk.StringVar) -> None:
        if not self._validate_numeric_input(var.get()):
            var.set("")

    def _create_main_frame(self) -> None:
        style = ttk.Style()
        theme_name = getattr(self, 'current_theme', 'light')
        style.configure('Custom.TFrame', background=THEMES[theme_name]['TFrame']['configure']['background'])

        self.frame = ttk.Frame(self.root, padding="10", style='Custom.TFrame')
        self.frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        style.configure('TLabel', font=('Arial', 10))
        style.configure('TButton', font=('Arial', 10, 'bold'))
        style.configure('TExportButton', font=('Arial', 7))


    def _setup_discord_rpc(self) -> None:
    # Initialize Discord Rich Presence.
        def init_rpc():
            try:
                self.RPC = Presence(DISCORD_CLIENT_ID)
                self.RPC.connect()
                self.last_rpc_update = time.time()  # Initialize the timestamp
                logging.info("Discord Rich Presence initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize Discord Rich Presence: {e}")
                self.RPC = None
                self.last_rpc_update = 0  # Set default value even if connection fails

        # Run Discord RPC initialization in a separate thread so it doesn't block main
        threading.Thread(target=init_rpc, daemon=True).start()

    def _setup_ui(self) -> None:
        # Create main content frame
        content = ttk.Frame(self.frame, padding=(20, 10))
        content.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        SETime = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M:%S")

    # Mission Time + GW Date Toggle
        mission_time_var = tk.StringVar(value=SETime)
        gw_date_var = tk.StringVar(value=GWDate)

        def toggle_gw_date(event=None):
            # Toggle between GWDate and GWDay
            if gw_date_var.get() == GWDate:
                gw_date_var.set(GWDay)
            else:
                gw_date_var.set(GWDate)

        header_frame = ttk.Frame(content)
        ttk.Label(header_frame, text="Mission Information:").pack(side=tk.LEFT)

        time_label = ttk.Label(header_frame, textvariable=mission_time_var)
        time_label.pack(side=tk.LEFT, padx=(3,0))

        ttk.Label(header_frame, text="Galactic War").pack(side=tk.LEFT, padx=(4,0))

        gw_label = ttk.Label(header_frame, textvariable=gw_date_var, cursor="hand2")
        gw_label.pack(side=tk.LEFT, padx=(2,0))
        gw_label.bind("<Button-1>", toggle_gw_date)

        try:
            self.gw_icon_img = tk.PhotoImage(file="gw_icon.png")  #this shit is the TF2 coconut img ngl XD
            self.gw_icon_img = self.gw_icon_img.subsample(55, 55) #     nvm im better than valve lmaoooo
            self.gw_icon_label = ttk.Label(header_frame, image=self.gw_icon_img, cursor="hand2")
            self.gw_icon_label.pack(side=tk.LEFT, padx=(6,0))
            self.gw_icon_label.bind("<Button-1>", toggle_gw_date)
        except Exception as e:
            logging.error(f"Failed to load GW icon: {e}")

        mission_frame = ttk.LabelFrame(content, padding=10, labelwidget=header_frame)

        def update_time():
            mission_time_var.set((datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M:%S"))

        self.update_time = update_time
        mission_frame.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Load sectors from config (and store for later)
        with open('PlanetSectors.json', 'r') as f:
            sectors_data = json.load(f)
            self.sectors_data = sectors_data
            sector_list = list(sectors_data.keys())

    # --- Mission Info Grid ---
        ttk.Label(mission_frame, text="Destroyer Name:").grid(row=0, column=0, sticky=tk.W, pady=5)

        self.shipName1s = ["SES Adjudicator", "SES Advocate", "SES Aegis", "SES Agent", "SES Arbiter", "SES Banner", "SES Beacon", "SES Blade", "SES Bringer", "SES Champion", "SES Citizen", "SES Claw", "SES Colossus", "SES Comptroller", "SES Courier", "SES Custodian", "SES Dawn", "SES Defender", "SES Diamond", "SES Distributor", "SES Dream", "SES Elected Representative", "SES Emperor", "SES Executor", "SES Eye", "SES Father", "SES Fist", "SES Flame", "SES Force", "SES Forerunner", "SES Founding Father", "SES Gauntlet", "SES Giant", "SES Guardian", "SES Halo", "SES Hammer", "SES Harbinger", "SES Herald", "SES Judge", "SES Keeper", "SES King", "SES Knight", "SES Lady", "SES Legislator", "SES Leviathan", "SES Light", "SES Lord", "SES Magistrate", "SES Marshall", "SES Martyr", "SES Mirror", "SES Mother", "SES Octagon", "SES Ombudsman", "SES Panther", "SES Paragon", "SES Patriot", "SES Pledge", "SES Power", "SES Precursor", "SES Pride", "SES Prince", "SES Princess", "SES Progenitor", "SES Prophet", "SES Protector", "SES Purveyor", "SES Queen", "SES Ranger", "SES Reign", "SES Representative", "SES Senator", "SES Sentinel", "SES Shield", "SES Soldier", "SES Song", "SES Soul", "SES Sovereign", "SES Spear", "SES Stallion", "SES Star", "SES Steward", "SES Superintendent", "SES Sword", "SES Titan", "SES Triumph", "SES Warrior", "SES Whisper", "SES Will", "SES Wings"]
        self.shipName2s = ["of Allegiance", "of Audacity", "of Authority", "of Battle", "of Benevolence", "of Conquest", "of Conviction", "of Conviviality", "of Courage", "of Dawn", "of Democracy", "of Destiny", "of Destruction", "of Determination", "of Equality", "of Eternity", "of Family Values", "of Fortitude", "of Freedom", "of Glory", "of Gold", "of Honour", "of Humankind", "of Independence", "of Individual Merit", "of Integrity", "of Iron", "of Judgement", "of Justice", "of Law", "of Liberty", "of Mercy", "of Midnight", "of Morality", "of Morning", "of Opportunity", "of Patriotism", "of Peace", "of Perseverance", "of Pride", "of Redemption", "of Science", "of Self-Determination", "of Selfless Service", "of Serenity", "of Starlight", "of Steel", "of Super Earth", "of Supremacy", "of the Constitution", "of the People", "of the Regime", "of the Stars", "of the State", "of Truth", "of Twilight", "of Victory", "of Vigilance", "of War", "of Wrath"]

        self.ship1_combo = ttk.Combobox(mission_frame, textvariable=self.shipName1, values=self.shipName1s, state='readonly', width=27)
        self.ship1_combo.grid(row=0, column=1, padx=5, pady=5)
        self.ship1_combo.set(self.shipName1s[0])

        self.ship2_combo = ttk.Combobox(mission_frame, textvariable=self.shipName2, values=self.shipName2s, state='readonly', width=39)
        self.ship2_combo.grid(row=0, column=2, sticky=tk.W, padx=(3,0), pady=5)
        self.ship2_combo.set(self.shipName2s[0])

        def update_full_ship_name(*args):
            self.FullShipName.set(f"{self.shipName1.get()} {self.shipName2.get()}")

        self.shipName1.trace_add("write", update_full_ship_name)
        self.shipName2.trace_add("write", update_full_ship_name)
        update_full_ship_name()

        ttk.Label(mission_frame, text="Helldiver:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(mission_frame, textvariable=self.Helldivers, width=30).grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(mission_frame, text="Level:").grid(row=2, column=2, sticky=tk.W, padx=0, pady=5)
        ttk.Entry(mission_frame, textvariable=self.level, width=35).grid(row=2, column=2, sticky=tk.W, padx=(45,0), pady=5)

        ttk.Label(mission_frame, text="Title:").grid(row=3, column=2, sticky=tk.W, pady=5)
        self.titles = ['CADET', 'SPACE CADET', 'SERGEANT', 'MASTER SERGEANT', 'CHIEF', 'SPACE CHIEF PRIME', 
             'DEATH CAPTAIN', 'MARSHAL', 'STAR MARSHAL', 'ADMIRAL', 'SKULL ADMIRAL', 'FLEET ADMIRAL',
             'ADMIRABLE ADMIRAL', 'COMMANDER', 'GALACTIC COMMANDER', 'HELL COMMANDER', 'GENERAL',
             '5-STAR GENERAL', '10-STAR GENERAL', 'PRIVATE', 'SUPER PRIVATE', 'SUPER CITIZEN',
             'VIPER COMMANDO', 'FIRE SAFETY OFFICER', 'EXPERT EXTERMINATOR', 'FREE OF THOUGHT',
             'ASSAULT INFANTRY', 'SUPER PEDESTRIAN', 'SERVANT OF FREEDOM', 'SUPER SHERIFF', 'DECORATED HERO', 'EXTRA JUDICIAL']
        self.title_combo = ttk.Combobox(mission_frame, textvariable=self.title, state='readonly', width=32)
        self.title_combo['values'] = self.titles
        self.title_combo.grid(row=3, column=2, sticky=tk.W, padx=(45,0), pady=5)
        self.title_combo.set(self.titles[0])

        ttk.Label(mission_frame, text="Profile:").grid(row=4, column=2, sticky=tk.W, pady=5)
        self.profile_pictures = ['A-9 Helljumper', 'A-35 Recon', 'AC-1 Dutiful', 'AC-2 Obedient', 
               'AD-11 Livewire', 'AD-26 Bleeding Edge', 'AD-49 Apollonian', 'AF-02 Haz-Master', 
               'AF-50 Noxious Ranger', 'AF-52 Lockdown', 'AF-91 Field Chemist', 'B-01 Tactical', 
               'B-08 Light Gunner', 'B-22 Model Citizen', 'B-24 Enforcer', 'B-27 Fortified Commando',
               'BP-20 Corrections Officer', 'BP-32 Jackboot', 'BP-77 Grand Juror', 'CD-35 Trench Engineer',
               'CE-07 Demolition Specialist', 'CE-27 Ground Breaker', 'CE-64 Grenadier', 'CE-67 Titan',
               'CE-74 Breaker', 'CE-81 Juggernaut', 'CE-101 Guerilla Gorilla', 'CM-09 Bonesnapper',
               'CM-10 Clinician', 'CM-14 Physician', 'CM-17 Butcher', 'CM-21 Trench Paramedic',
               'CW-4 Arctic Ranger', 'CW-9 White Wolf', 'CW-22 Kodiak', 'CW-36 Winter Warrior',
               'DP-00 Tactical', 'DP-11 Champion of the People', 'DP-40 Hero of the Federation',
               'DP-53 Savior of the Free', 'DS-42 Federation\'s Blade', 'DS-191 Scorpion',
               'EX-00 Prototype X', 'EX-03 Prototype 3', 'EX-16 Prototype 16', 'FS-05 Marksman',
               'FS-11 Executioner', 'FS-23 Battle Master', 'FS-34 Exterminator', 'FS-37 Ravager',
               'FS-38 Eradicator', 'FS-55 Devastator', 'FS-61 Dreadnought', 'GS-11 Democracy\'s Deputy',
               'GS-17 Frontier Marshal', 'GS-66 Lawmaker', 'I-09 Heatseeker', 'I-44 Salamander',
               'I-92 Fire Fighter', 'I-102 Draconaught', 'IE-3 Martyr', 'IE-12 Righteous',
               'IE-57 Hell-Bent', 'PH-9 Predator', 'PH-56 Jaguar', 'PH-202 Twigsnapper',
               'RE-824 Bearer of the Standard', 'RE-1861 Parade Commander', 'RE-2310 Honorary Guard',
               'SA-04 Combat Technician', 'SA-12 Servo Assisted', 'SA-25 Steel Trooper',
               'SA-32 Dynamo', 'SC-15 Drone Master', 'SC-30 Trailblazer Scout', 'SC-34 Infiltrator',
               'SC-37 Legionnaire', 'SR-18 Roadblock', 'SR-24 Street Scout', 'SR-64 Cinderblock',
               'TR-7 Ambassador of the Brand', 'TR-9 Cavalier of Democracy', 'TR-40 Gold Eagle',
               'TR-62 Knight', 'TR-117 Alpha Commander', 'UF-16 Inspector', 'UF-50 Bloodhound',
               'UF-84 Doubt Killer']
        self.profile_picture_combo = ttk.Combobox(mission_frame, textvariable=self.profile_picture, state='readonly', width=32)
        self.profile_picture_combo['values'] = self.profile_pictures
        self.profile_picture_combo.grid(row=4, column=2, sticky=tk.W, padx=(45,0), pady=5)
        self.profile_picture_combo.set(self.profile_pictures[0])

        ttk.Label(mission_frame, text="Sector:").grid(row=3, column=0, sticky=tk.W, pady=5)
        sector_combo = ttk.Combobox(mission_frame, textvariable=self.sector, values=sector_list, state='readonly', width=27)
        sector_combo.grid(row=3, column=1, padx=5, pady=5)
        sector_combo.set(sector_list[0])

        ttk.Label(mission_frame, text="Planet:").grid(row=4, column=0, sticky=tk.W, pady=5)
        planet_combo = ttk.Combobox(mission_frame, textvariable=self.planet, state='readonly', width=27)
        planet_combo.grid(row=4, column=1, padx=5, pady=5)
        self.sector_combo = sector_combo
        self.planet_combo = planet_combo

        ttk.Label(mission_frame, text="Mega City:").grid(row=5, column=0, sticky=tk.W, pady=5)
        mega_cities_combo = ttk.Combobox(mission_frame, textvariable=self.mega_cities, state='readonly', width=27)
        mega_cities_combo.grid(row=5, column=1, sticky=tk.E, padx=5, pady=5)
        self.mega_cities_combo = mega_cities_combo

    # Dynamic planet / mega city lists
        def update_mega_cities(*args):
            # Populate mega cities based on currently selected planet.
            selected_planet = self.planet.get()
            try:
                with open("MegaCityPlanets.json", "r") as f:
                    planetary_data = json.load(f)
            except Exception:
                planetary_data = {}
            if not selected_planet or selected_planet not in planetary_data:
                mega_cities_combo['values'] = ["Planet Surface"]
                mega_cities_combo.set("Planet Surface")
            else:
                mega_cities_list = planetary_data[selected_planet].get("mega_cities", [])
                mega_cities_combo['values'] = mega_cities_list if mega_cities_list else ["Planet Surface"]
                mega_cities_combo.set(mega_cities_list[0] if mega_cities_list else "Planet Surface")

        def update_planets(*args):
            # Populate planets based on selected sector and immediately refresh mega cities.
            selected_sector = self.sector.get()
            if not selected_sector or selected_sector not in sectors_data:
                return
            planet_list = sectors_data[selected_sector]["planets"]
            planet_combo['values'] = planet_list
            # Preserve existing planet if still valid, else select first
            current_planet = self.planet.get()
            if current_planet in planet_list:
                planet_combo.set(current_planet)
            else:
                planet_combo.set(planet_list[0])
            # Immediately update mega cities for the (possibly new) planet
            update_mega_cities()

        sector_combo.bind('<<ComboboxSelected>>', update_planets)
        planet_combo.bind('<<ComboboxSelected>>', update_mega_cities)
        # Initial population
        update_planets()
        update_mega_cities()

    # --- Mission Details Section ---
        details_frame = ttk.LabelFrame(content, text="Mission Details", padding=10)
        details_frame.grid(row=1, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))

    # Enemy selection
        ttk.Label(details_frame, text="Enemy Type:").grid(row=0, column=0, sticky=tk.W, pady=5)

        with open('Missions.json', 'r') as f:
            missions_data = json.load(f)
            enemy_types = list(missions_data.keys())

        enemy_combo = ttk.Combobox(details_frame, textvariable=self.enemy_type, values=enemy_types, state='readonly', width=27)
        enemy_combo.grid(row=0, column=1, padx=5, pady=5)
        enemy_combo.set(enemy_types[0])

    # Major Order + DSS toggles
        ttk.Label(details_frame, text="Major Order:").grid(row=3, column=2, sticky=tk.W, pady=5)
        ttk.Checkbutton(details_frame, variable=self.MO).grid(row=3, column=2, sticky=tk.W, padx=(100,0), pady=5)

    # DSS modifier dropdown (shown only if active)
        ttk.Label(details_frame, text="DSS Active:").grid(row=1, column=2, sticky=tk.W, pady=5)
        ttk.Checkbutton(details_frame, variable=self.DSS).grid(row=1, column=2, sticky=tk.W, padx=(100,0), pady=5)

        self.dss_frame = ttk.Frame(details_frame)
        self.dss_frame.grid(row=2, column=2, sticky=tk.W, pady=5)
        ttk.Label(self.dss_frame, text="DSS Modifier:").pack(side=tk.LEFT)
        dss_mods = ["Inactive", "Orbital Blockade", "Heavy Ordnance Distribution", "Eagle Storm", "Eagle Blockade"]
        self.DSSMod.set("Inactive")  # Set default value
        self.dss_combo = ttk.Combobox(self.dss_frame, textvariable=self.DSSMod, values=dss_mods, state='readonly', width=27)
        self.dss_combo.pack(side=tk.LEFT, padx=(40,0))
        
        self.dss_frame.grid_remove()
        
        def toggle_dss_mod(*args):
            if self.DSS.get():
                self.dss_frame.grid()
            else:
                self.DSSMod.set("Inactive")
                self.dss_frame.grid_remove()
            
        self.DSS.trace_add("write", toggle_dss_mod)

    # Subfaction
        ttk.Label(details_frame, text="Enemy Subfaction:").grid(row=0, column=2, sticky=tk.W, pady=5)
        subfaction_combo = ttk.Combobox(details_frame, textvariable=self.subfaction_type, state='readonly', width=27)
        subfaction_combo.grid(row=0, column=2, sticky=tk.E, padx=(125,0), pady=5)

    # Campaign
        ttk.Label(details_frame, text="Mission Campaign:").grid(row=1, column=0, sticky=tk.W, pady=5)
        mission_cat_combo = ttk.Combobox(details_frame, textvariable=self.mission_category, state='readonly', width=27)
        mission_cat_combo.grid(row=1, column=1, padx=5, pady=5)

    # Difficulty
        ttk.Label(details_frame, text="Mission Difficulty:").grid(row=2, column=0, sticky=tk.W, pady=5)
        difficulty_combo = ttk.Combobox(details_frame, textvariable=self.difficulty, state='readonly', width=27)
        difficulty_combo.grid(row=2, column=1, padx=5, pady=5)

    # Mission type
        ttk.Label(details_frame, text="Mission Type:").grid(row=3, column=0, sticky=tk.W, pady=5)
        mission_type_combo = ttk.Combobox(details_frame, textvariable=self.mission_type, state='readonly', width=27)
        mission_type_combo.grid(row=3, column=1, padx=5, pady=5)

        def update_subfactions(*args):
            enemy = self.enemy_type.get()
            if enemy in missions_data:
                subfactions = list(missions_data[enemy].keys())
                logging.info(f"Available subfactions for {enemy}: {subfactions}")  # Add logging
                subfaction_combo['values'] = subfactions
            if subfactions:
                subfaction_combo.set(subfactions[0])
                update_mission_categories()

        def update_mission_categories(*args):
            enemy = self.enemy_type.get()
            subfaction = self.subfaction_type.get()
            if enemy in missions_data and subfaction in missions_data[enemy]:
                categories = list(missions_data[enemy][subfaction].keys())
                mission_cat_combo['values'] = categories
            if categories:
                mission_cat_combo.set(categories[0])
                update_mission_types()

        def update_mission_types(*args):
            enemy = self.enemy_type.get()
            subfaction = self.subfaction_type.get()
            category = self.mission_category.get()
            
            if (enemy in missions_data and 
                subfaction in missions_data[enemy] and 
                category in missions_data[enemy][subfaction]):
                
                if missions_data[enemy][subfaction][category] != "Unknown":
                    difficulties = list(missions_data[enemy][subfaction][category].keys())
                    difficulty_combo['values'] = difficulties
                    difficulty_combo.set(difficulties[0])
                    
                    # Set initial mission types from first difficulty
                    first_difficulty = difficulties[0]
                    available_missions = missions_data[enemy][subfaction][category][first_difficulty]
                    mission_type_combo['values'] = available_missions
                    if available_missions:
                        mission_type_combo.set(available_missions[0])
                else:
                    mission_type_combo['values'] = ["No missions available"]
                    mission_type_combo.set("No missions available")
                    difficulty_combo['values'] = ["No difficulties available"]
                    difficulty_combo.set("No difficulties available")

        def update_available_missions(*args):
            enemy = self.enemy_type.get()
            subfaction = self.subfaction_type.get()
            category = self.mission_category.get()
            difficulty = self.difficulty.get()
            
            if (enemy in missions_data and 
                subfaction in missions_data[enemy] and 
                category in missions_data[enemy][subfaction] and 
                difficulty in missions_data[enemy][subfaction][category]):
                
                available_missions = missions_data[enemy][subfaction][category][difficulty]
                mission_type_combo['values'] = available_missions
                if available_missions:
                    mission_type_combo.set(available_missions[0])

        enemy_combo.bind('<<ComboboxSelected>>', update_subfactions)
        subfaction_combo.bind('<<ComboboxSelected>>', update_mission_categories)
        mission_cat_combo.bind('<<ComboboxSelected>>', update_mission_types)
        difficulty_combo.bind('<<ComboboxSelected>>', update_available_missions)

    # Populate chained dropdowns
        update_subfactions()

    # --- Stats + Note ---
        stats_note_container = ttk.Frame(content)
        stats_note_container.grid(row=2, column=0, padx=5, pady=5, sticky=(tk.W, tk.E))

    # Stats
        stats_frame = ttk.LabelFrame(stats_note_container, text="Mission Statistics", padding=10)
        stats_frame.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)

    # Note
        note_frame = ttk.LabelFrame(stats_note_container, text="Note", padding=10)
        note_frame.pack(side=tk.RIGHT, padx=5, fill=tk.BOTH, expand=True)

        MAX_NOTE_CHARS = 512

        note_entry = tk.Text(note_frame, height=3, width=30, wrap="word")
        note_entry.grid(row=0, column=0, padx=5, pady=(5,0), sticky=(tk.W, tk.E, tk.N, tk.S))

    # Character counter
        counter_label = ttk.Label(note_frame, text=f"0/{MAX_NOTE_CHARS}")
        counter_label.grid(row=1, column=0, padx=5, pady=(2,5), sticky=tk.E)

        def update_note_limit(event=None):
            text = note_entry.get("1.0", "end-1c")
            if len(text) > MAX_NOTE_CHARS:
                # Delete only the excess instead of resetting whole text - Don't even ask me how i learned this is even a thing
                note_entry.delete(f"1.0+{MAX_NOTE_CHARS}c", tk.END)
                text = note_entry.get("1.0", "end-1c")
            counter_label.config(text=f"{len(text)}/{MAX_NOTE_CHARS}")
            self.note.set(text)

        def block_excess(event):
            # Prevent further typing when at limit (allow navigation & deletion)
            text = note_entry.get("1.0", "end-1c")
            if (len(text) >= MAX_NOTE_CHARS and 
                event.keysym not in ("BackSpace", "Delete", "Left", "Right", "Up", "Down", "Home", "End")):
                return "break"

    # Bind note editor constraints
        note_entry.bind("<KeyPress>", block_excess)
        note_entry.bind("<KeyRelease>", update_note_limit)
        note_entry.bind("<<Paste>>", lambda e: self.root.after(1, update_note_limit))
        note_entry.bind("<FocusOut>", update_note_limit)

    # Initialize note state
        update_note_limit()

        note_frame.columnconfigure(0, weight=1)
        note_frame.rowconfigure(0, weight=1)

        ttk.Label(stats_frame, text="Kills:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(stats_frame, textvariable=self.kills, width=30).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(stats_frame, text="Deaths:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(stats_frame, textvariable=self.deaths, width=30).grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(stats_frame, text="Performance:").grid(row=3, column=0, sticky=tk.W, pady=5)
        ratings = ["Outstanding Patriotism", "Superior Valour", "Costly Failure", "Honourable Duty", "Unremarkable Performance", "Disappointing Service", "Disgraceful Conduct"]
        rating_combo = ttk.Combobox(stats_frame, textvariable=self.rating, values=ratings, state='readonly', width=27)
        rating_combo.grid(row=3, column=1, padx=5, pady=5)

    # Submit
        submit_button = ttk.Button(content, text="Submit Mission Report", command=self.submit_data)
        submit_button.grid(row=3, column=0, pady=15)

    # Export + Style sections
        bottom_frame = ttk.LabelFrame(content, text="Report Style and Export", padding=10)
        bottom_frame.grid(row=4, column=0, pady=5, sticky=(tk.W, tk.E))

    # Export buttons / integrations
        export_frame = ttk.LabelFrame(content, text="Exporting", padding=10)
        export_frame.grid(row=4, column=0, pady=5, sticky=(tk.W, tk.E))

    # Export GUI launcher
        GUIbutton = ttk.Button(export_frame, text=" Open\nExport\n  GUI", command=lambda: subprocess.run(['python', 'exportGUI.py'], shell=False), padding=(6,5), width=14)
        GUIbutton.grid(row=4, column=0, pady=15, padx=(20,0))

    # Planet aggregation export
        export_button = ttk.Button(export_frame, text="Export Excel\n    Data to\n  Webhook", command=lambda: subprocess.run(['python', 'sub.py']), padding=(6,5), width=14)
        export_button.grid(row=4, column=1, padx=(40,0), pady=15)

    # Faction aggregation export
        export_button = ttk.Button(export_frame, text="Export Faction\n      Data to\n    Webhook", command=lambda: subprocess.run(['python', 'faction.py']), padding=(6,5), width=14)
        export_button.grid(row=4, column=2, padx=(40,0), pady=15)

    # Achievements + Invite + Theme + Settings buttons
        image_button_frame = ttk.Frame(mission_frame)
        image_button_frame.grid(row=5, column=4, padx=5, pady=5)

    # Achievement button image
        try:
            # Store the image as an instance attribute to prevent garbage collection
            self.button_image = tk.PhotoImage(file="achievement.png")
            self.button_image = self.button_image.subsample(2, 2)
            
            # Create the button with the image in the export frame
            image_button = ttk.Button(export_frame, image=self.button_image, command=lambda: subprocess.run(['python', 'Achievements.py']), width=7)
            image_button.configure(compound=tk.CENTER)
            image_button.grid(row=4, column=3, padx=(125,0), pady=15) 
            
        except Exception as e:
            logging.error(f"Failed to load button image: {e}")
            # Fallback to text button if image loading fails
            fallback_button = ttk.Button(export_frame, text="Image Button", command=lambda: subprocess.run(['python', 'Achievements.py']))
            fallback_button.grid(row=4, column=3, padx=(125,0), pady=15)

    # Discord invite button image
        try:
            # Store the image as an instance attribute to prevent garbage collection
            self.invite_image = tk.PhotoImage(file="invite.png")
            self.invite_image = self.invite_image.subsample(60, 60)
            
            # Create the button with the image in the export frame
            invite_button = ttk.Button(export_frame, image=self.invite_image, command=lambda: webbrowser.open("https://discord.gg/U6ydgwFKZG"), width=7)
            invite_button.configure(compound=tk.CENTER)
            invite_button.grid(row=4, column=3, padx=(0,20), pady=15)
            
        except Exception as e:
            logging.error(f"Failed to load invite button image: {e}")
            # Fallback to text button if image loading fails
            invite_fallback = ttk.Button(export_frame, text="Invite Button", command=lambda: webbrowser.open("https://discord.gg/U6ydgwFKZG"))
            invite_fallback.grid(row=4, column=3, padx=(0,20), pady=15)

    # Theme toggle
        theme_button = ttk.Button(export_frame, text="Toggle\nTheme", command=self.toggle_theme, padding=(6,5), width=14)
        theme_button.grid(row=4, column=4, padx=(40,0), pady=15)

    # Settings editor
        settings_button = ttk.Button(export_frame, text="Settings", command=lambda: subprocess.run(['python', 'settings.py']), padding=(6,5), width=14)
        settings_button.grid(row=4, column=5, padx=(40,0), pady=15)


    def _update_discord_presence(self) -> None:
    # Update Discord Rich Presence with current mission information.
        if not hasattr(self, 'RPC') or self.RPC is None:
            return

        current_time = time.time()
        if current_time - self.last_rpc_update < RPC_UPDATE_INTERVAL:
            return

        try:
            helldiver = self.Helldivers.get() or "Unknown Helldiver"
            sector = self.sector.get() or "No Sector"
            planet = self.planet.get() or "No Planet"
            enemytype = self.enemy_type.get() or "Unknown Enemy"
            level = self.level.get() or 0
            title = self.title.get() or "No Title"

            # Small image asset mapping
            enemy_assets = {
                "Automatons": "bots",
                "Terminids": "bugs",
                "Illuminate": "squids",
                "Observing": "obs"
            }
            
            small_image = enemy_assets.get(enemytype, "unknown")

            if self.enemy_type.get() == "Observing":
                SText = "Observing"
            else:
                SText = "Fighting: " + enemytype


            self.RPC.update(
                state=f"Sector: {sector}\nPlanet: {planet}",
                details=f"Helldiver: {helldiver} Level: {level} | {title}",
                large_image="superearth",
                large_text="Helldivers 2",
                small_image=small_image,
                small_text=f"{SText}",
            )
            self.last_rpc_update = current_time
        except Exception as e:
            logging.error(f"Failed to update Discord Rich Presence: {e}")

    def load_settings(self) -> None:
    # Load user settings from file.
        def load():
            try:
                theme = 'light'
                if os.path.exists(SETTINGS_FILE):
                    with open(SETTINGS_FILE, 'r') as f:
                        settings = json.load(f)
                        theme = settings.get('theme', 'light')
                # Load all values from persistent.json
                persistent_settings = {}
                if os.path.exists(PERSISTENCE_FILE):
                    with open(PERSISTENCE_FILE, 'r') as f:
                        persistent_settings = json.load(f)
                persistent_settings['theme'] = theme
                self.root.after(0, lambda: self._apply_settings(persistent_settings))
            except Exception as e:
                self.root.after(0, lambda: self._show_error(f"Error loading settings: {e}"))

        threading.Thread(target=load, daemon=True).start()

    def save_settings(self) -> None:
    # Save current settings to file.
        # Save theme to settings.json
        theme_data = {'theme': self.current_theme}
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(theme_data, f, indent=4)
        except Exception as e:
            self._show_error(f"Error saving theme: {e}")
        # Save all values to persistent.json
        settings = {
            'helldiver': self.Helldivers.get(),
            'level': self.level.get(),
            'title': self.title.get(),
            'sector': self.sector.get(),
            'planet': self.planet.get(),
            'difficulty': self.difficulty.get(),
            'mission': self.mission_type.get(),
            'DSS': self.DSS.get(),
            'DSSMod': self.DSSMod.get(),
            'campaign': self.mission_category.get(),
            'subfaction': self.subfaction_type.get(),
            'shipName1': self.shipName1.get(),
            'shipName2': self.shipName2.get(),
            'profile_picture': self.profile_picture.get(),
        }
        try:
            with open(PERSISTENCE_FILE, 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            self._show_error(f"Error saving persistent settings: {e}")

    def submit_data(self) -> None:
    # Handle mission report submission.
        if not self._validate_submission():
            return
            
        self.save_settings()
        self.update_time()

        if self.enemy_type.get() == "Observing":
            self._show_error("ADVISORY: You cannot submit an observation mission")
            return

        if self.mission_type.get() == "No missions available":
            self._show_error("ADVISORY: You cannot submit without selecting a mission")
            return

        if self.planet.get() == "Meridia":
            self._show_error("ADVISORY: Volatile spacetime fluctuations currently prohibit FTL travel to the Meridian Black Hole.")
            return

        if self.planet.get() == "Angel's Venture" or self.planet.get() == "Moradesh" or self.planet.get() == "Ivis":
            self._show_error("ADVISORY: You cannot deploy on a fractured planet")
            return
        
        if self.planet.get() == "Widow's Harbor" or self.planet.get() == "New Haven" or self.planet.get() == "Pilen V" or self.planet.get() == "Mars":
            self._show_error("ADVISORY: You cannot deploy on a scoured planet")
            return

        data = self._collect_mission_data()

        if self._save_to_excel(data):
            if self._send_to_discord(data):
                logging.info("Sent To Discord")
            
    def _validate_submission(self) -> bool:
    # Validate all required fields before submission.
        try:
            # Validate numeric fields
            level = int(self.level.get())
            kills = int(self.kills.get())
            deaths = int(self.deaths.get())
            #create a randint between 1 and 0 - to randomise for lil easter egg
            rndint = random.randint(0, 1)

            if level < 1 or level > 150:  # Add reasonable level range
                if rndint == 1:
                    self._show_error("ADVISORY: You are not a Helldiver")
                else:
                    self._show_error("Level must be between 1 and 150")
                return False

            if kills < 0 or kills > 10000:
                if rndint == 1:
                    self._show_error("These kills will be reported to your Democracy Officer... I dear hope you're not lying...")
                else:
                    self._show_error("Invalid number of kills")
                return False

            if deaths < 0 or deaths > 1000:
                if rndint == 1:
                    self._show_error("Surely you didn't die this many times... right?")
                else:
                    self._show_error("Invalid number of deaths")
                return False

            # Validate required text fields
            if not self.Helldivers.get().strip():
                if rndint == 1:
                    self._show_error("I know we're cannon fodder but you could at least give yourself a name... have some dignity!")
                else:
                    self._show_error("Helldiver name is required")
                return False

            if not self.mission_type.get().strip():
                if rndint == 1:
                    self._show_error("Did you sit in your hellpod the entire time?")
                else:
                    self._show_error("Mission type is required")
                return False

            return True
        except ValueError:
            self._show_error("Invalid numeric input")
            return False

    def _show_error(self, message: str) -> None:
        messagebox.showerror("Error", message)

    def _collect_mission_data(self) -> Dict:
    # Collect all mission data into a dictionary.
        return {
            'Super Destroyer': self.FullShipName.get(),
            'Helldivers': self.Helldivers.get(),
            'Level': self.level.get(),
            'Title': self.title.get(),
            'Sector': self.sector.get(),
            'Planet': self.planet.get(),
            'Mega City': self.mega_cities.get(),
            'Enemy Type': self.enemy_type.get(),
            'Enemy Subfaction': self.subfaction_type.get(),
            'Major Order': self.MO.get(),
            'DSS Active': self.DSS.get(),
            'DSS Modifier': self.DSSMod.get(),
            'Mission Category': self.mission_category.get(),
            'Mission Type': self.mission_type.get(),
            'Difficulty': self.difficulty.get(),
            'Kills': self.kills.get(),
            'Deaths': self.deaths.get(),
            'Rating': self.rating.get(),
            'Time': datetime.now().strftime(DATE_FORMAT),
            'Note': self.note.get(),
        }

    def _save_to_excel(self, data: Dict) -> bool:
    # Save mission data to Excel file by appending new rows.
        excel_file = EXCEL_FILE_TEST if DEBUG else EXCEL_FILE_PROD
        
        try:
            # Create new DataFrame with single row of data - because excel is weeeird... why are we even using excel again?
            new_data = pd.DataFrame([data])
            
            if os.path.exists(excel_file):
                existing_df = pd.read_excel(excel_file)
                updated_df = pd.concat([existing_df, new_data], ignore_index=True)
            else:
                updated_df = new_data
                
            with pd.ExcelWriter(excel_file) as writer:
                updated_df.to_excel(writer, index=False)
                
            logging.info(f"Successfully appended data to {excel_file}")
            return True
            
        except Exception as e:
            logging.error(f"Error saving to Excel: {e}")
            self._show_error(f"Error saving to Excel: {e}")
            return False

    def _send_to_discord(self, data: Dict) -> bool:
    # Send mission report to Discord.
        try:
            Stars = ""
            GoldStar = config['Stars']['GoldStar']
            GreyStar = config['Stars']['GreyStar']
            
            rating_stars = {
                "Outstanding Patriotism": 5,
                "Superior Valour": 4,
                "Costly Failure": 4,
                "Honourable Duty": 3,
                "Unremarkable Performance": 2,
                "Disappointing Service": 1,
                "Disgraceful Conduct": 0
            }
            
            gold_count = rating_stars.get(self.rating.get(), 0)
            Stars = GoldStar * gold_count + GreyStar * (5 - gold_count)
            date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            enemy_icon = get_enemy_icon(data['Enemy Type'])
            planet_icon = get_planet_icon(data['Planet'])
            if planet_icon == '':
                planet_icon = '<:hd1superearth:1103949794285723658>'
            system_color = get_system_color(data['Enemy Type'])
            diff_icon = get_difficulty_icon(data['Difficulty'])
            subfaction_icon = get_subfaction_icon(data['Enemy Subfaction'])
            campaign_icon = get_campaign_icon(data['Mission Category'])
            if data['Mission Type'] == "Blitz: Search and Destroy" and data['Enemy Type'] == "Automatons":
                mission_icon = get_mission_icon("PLACEHOLDER")
            else:
                mission_icon = get_mission_icon(data['Mission Type'])
            biome_banner = get_biome_banner(data['Planet'])
            dss_icon = get_dss_icon(data['DSS Modifier'])
            title_icon = get_title_icon(data['Title'])
            profile_picture = get_profile_picture(self.profile_picture.get())


            # Streak tracking (missions within 1h chain)
            helldiver_name = "Helldiver"
            streak_file = 'streak_data.json'
            streak = 1  # Default streak value
            highest_streak = 0  # Default highest streak value
            streak_emoji = ""  # No streak emoji by default
            profile_picture_name = profile_picture

            try:
                streak_data = {}
                if os.path.exists(streak_file):
                    with open(streak_file, 'r') as f:
                        streak_data = json.load(f)
                
                user_data = streak_data.get(helldiver_name, {'streak': 0, 'last_time': None})
                
                # Check if this user has previous streak data with valid timestamp
                if user_data['last_time']:
                    last_time = datetime.strptime(user_data['last_time'], "%Y-%m-%d %H:%M:%S")
                    time_diff = datetime.now() - last_time
                    
                    if time_diff.total_seconds() <= 3600:  # Within an hour
                        streak = user_data['streak'] + 1
                        # Add streak emoji based on length
                        if streak >= 30:
                            streak_emoji = "🔥 x" + str(streak) + " WTF!"
                        elif streak >= 24:
                            streak_emoji = "🔥 x" + str(streak) + " TRULY HELLDIVING!"
                        elif streak >= 21:
                            streak_emoji = "🔥 x" + str(streak) + " IMPOSSIBLE!"
                        elif streak >= 18:
                            streak_emoji = "🔥 x" + str(streak) + " SUICIDAL!"
                        elif streak >= 15:
                            streak_emoji = "🔥 x" + str(streak) + " PATRIOTIC!"
                        elif streak >= 12:
                            streak_emoji = "🔥 x" + str(streak) + " DEMOCRATIC!"
                        elif streak >= 9:
                            streak_emoji = "🔥 x" + str(streak) + " LIBERATING!"
                        elif streak >= 6:
                            streak_emoji = "🔥 x" + str(streak) + " SUPER!"
                        elif streak >= 3:
                            streak_emoji = "🔥 x" + str(streak) + " COMMENDABLE!"
                        else:
                            streak_emoji = "🔥 x" + str(streak)
                # Update streak data for this user
                highest_streak = user_data.get('highest_streak', 0)  # Get existing highest streak or default to 0
                if streak > highest_streak:
                    highest_streak = streak
                    
                streak_data[helldiver_name] = {
                    'streak': streak,
                    'highest_streak': highest_streak,
                    'last_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'profile_picture_name': profile_picture_name
                }
                
                # Save updated streak data
                with open(streak_file, 'w') as f:
                    json.dump(streak_data, f, indent=4)
                    
            except Exception as e:
                logging.error(f"Error managing streak data: {e}")

            total_missions_main = total_missions()

            # UID from local DCord.json (user settings)
            try:
                with open('DCord.json', 'r') as f:
                    settings_data = json.load(f)
                    UID = settings_data.get('discord_uid', '0')
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logging.error(f"Error loading settings.json: {e}")
                UID = '0'  # Fallback to default
            MICo = str(data["Major Order"]) + " " + config['MiscIcon']['MO'] if data["Major Order"] else str(data["Major Order"])
            DSSIco = str(data["DSS Active"]) + " " + config['MiscIcon']['DSS'] if data["DSS Active"] else str(data["DSS Active"])

            message_content = {
                "content": None,
                "embeds": [{
                    "title": f"{data['Super Destroyer']}\nDeployed {data['Helldivers']}",
                    "description": f"**Level {data['Level']} | {data['Title']} {title_icon}\nMission: {total_missions_main}**\n\n<a:easyshine1:1349110651829747773> <:hd1superearth:1103949794285723658> **Galactic Intel** {planet_icon} <a:easyshine3:1349110648528699422>\n> Sector: {data['Sector']}\n> Planet: {data['Planet']}\n> Mega City: {data['Mega City']}\n> Major Order: {MICo}\n> DSS Active: {DSSIco}\n> DSS Modifier: {data['DSS Modifier']} {dss_icon}\n\n",
                    "color": system_color,
                    "fields": [{
                        "name": f"<a:easyshine1:1349110651829747773> {enemy_icon} **Enemy Intel** {subfaction_icon} <a:easyshine3:1349110648528699422>",
                        "value": f"> Faction: {data['Enemy Type']}\n> Subfaction: {data['Enemy Subfaction']}\n> Campaign: {data['Mission Category']}\n\n<a:easyshine1:1349110651829747773> {campaign_icon} **Mission Intel** {mission_icon} <a:easyshine3:1349110648528699422>\n> Mission: {data['Mission Type']}\n> Difficulty: {data['Difficulty']} {diff_icon}\n> Kills: {data['Kills']}\n> Deaths: {data['Deaths']}\n> Rating: {data['Rating']}\n\n {Stars}\n"
                    }],
                    "author": {
                        "name": f"Super Earth Mission Report\nDate: {date}",
                        "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356001307596427564/NwNzS9B.png?ex=67eafa21&is=67e9a8a1&hm=7e204265cbcdeaf96d7b244cd63992c4ef10dc18befbcf2ed39c3a269af14ec0&"
                    },
                    "footer": {
                    "text": f"{streak_emoji}\n{UID}     v{VERSION}{DEV_RELEASE}",
                    "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356025859319926784/5cwgI15.png?ex=67eb10fe&is=67e9bf7e&hm=ab6326a9da1e76125238bf3668acac8ad1e43b24947fc6d878d7b94c8a60ab28&"
                    },
                    "image": {"url": f"{biome_banner}"},
                    "thumbnail": {"url": f"{profile_picture}"},                   
                }],
                "attachments": []
                
            }

            # Send embeds to active webhooks
            if DEBUG:
                # Use TEST webhook from config if in debug mode
                ACTIVE_WEBHOOK = [config['Webhooks']['TEST']]
            else:
                # Use PROD webhook in production mode
                with open('DCord.json', 'r') as f:
                    dcord_data = json.load(f)
                    ACTIVE_WEBHOOK = dcord_data.get('discord_webhooks', [])

            successes = []
            for url in ACTIVE_WEBHOOK:
                try:
                    response = requests.post(url, json=message_content)
                    if response.status_code == 204:
                        logging.info(f"Successfully sent to Discord webhook: {url}")
                        successes.append(True)
                    else:
                        logging.error(f"Failed to send to Discord webhook {url}. Status code: {response.status_code}")
                        self._show_error(f"Failed to send to Discord (Status: {response.status_code})")
                        successes.append(False)
                except requests.RequestException as e:
                    logging.error(f"Network error sending to Discord webhook {url}: {e}")
                    self._show_error(f"Failed to connect to Discord webhook")
                    successes.append(False)
                except Exception as e:
                    logging.error(f"Unexpected error sending to Discord webhook {url}: {e}")
                    self._show_error("An unexpected error occurred while sending to Discord")
                    successes.append(False)

            # Return True only if all webhooks succeeded
            return any(successes) if successes else False
        except Exception as e:
            logging.error(f"Error preparing Discord message: {e}")
            self._show_error("Error preparing Discord message")
            return False

    def export_data(self) -> None:
    # Export Excel data to webhook.
        excel_file = "mission_log_test.xlsx" if DEBUG else "mission_log.xlsx"
        try:
            if not os.path.exists(excel_file):
                self._show_error("No Excel file found to export")
                return

            df = pd.read_excel(excel_file)
            for _, row in df.iterrows():
                data = row.to_dict()
                self._send_to_discord(data)

            self._show_success("Excel data exported successfully!")
        except Exception as e:
            self._show_error(f"Error exporting data: {e}")
            logging.error(f"Error during Excel export: {e}")

    def __del__(self) -> None:
    # Clean up resources on deletion.
        if hasattr(self, 'RPC') and self.RPC is not None:
            try:
                self.RPC.close()
            except:
                pass

    def export_excel(self):
        try:
            subprocess.run(['python', 'sub.py'], 
                          shell=False,
                          check=True,
                          capture_output=True)
        except subprocess.CalledProcessError as e:
            self._show_error(f"Export failed: {e}")

    def _apply_settings(self, settings: dict) -> None:
    # Apply loaded settings to the GUI variables.
        # Only set if key exists to avoid KeyError
        self.Helldivers.set(settings.get('helldiver', ''))
        self.level.set(settings.get('level', 1))
        self.title.set(settings.get('title', ''))
        self.sector.set(settings.get('sector', ''))
        self.planet.set(settings.get('planet', ''))
        self.difficulty.set(settings.get('difficulty', ''))
        self.mission_type.set(settings.get('mission', ''))
        self.DSS.set(settings.get('DSS', False))
        self.DSSMod.set(settings.get('DSSMod', 'Inactive'))
        self.mission_category.set(settings.get('campaign', ''))
        self.subfaction_type.set(settings.get('subfaction', ''))
        self.shipName1.set(settings.get('shipName1', ''))
        self.shipName2.set(settings.get('shipName2', ''))
        self.profile_picture.set(settings.get('profile_picture', ''))
        # Apply theme if present
        theme = settings.get('theme', 'light')
        self.apply_theme(theme)
        # After loading saved sector/planet ensure dependent dropdowns refresh
        try:
            # Re-run planet population with current sector.
            if hasattr(self, 'sectors_data') and self.sector.get() in self.sectors_data:
                planets = self.sectors_data[self.sector.get()]['planets']
                self.planet_combo['values'] = planets
                if self.planet.get() not in planets and planets:
                    self.planet.set(planets[0])
            # Trigger mega city refresh by generating a virtual event - is this hacky? this feels hacky...
            if hasattr(self, 'planet_combo'):
                self.planet_combo.event_generate('<<ComboboxSelected>>')
        except Exception as e:
            logging.error(f"Failed to refresh planet / mega city lists after settings load: {e}")

if __name__ == "__main__":
    try:
        with open('DCord.json', 'r') as f:
            settings_data = json.load(f)
            discord_uid = settings_data.get('discord_uid', '0')
            if not (re.match(r'^\d{17,19}$', discord_uid) or (DEBUG and discord_uid == '0')):
                logging.error("Please set a valid Discord ID in the settings.py file")
                messagebox.showerror("Error", "Please set a valid Discord ID in the settings.py file")
                os._exit(1)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error loading settings.json: {e}")
        messagebox.showerror("Error", f"Error loading settings.json: {e}")
        os._exit(1)

    root = tk.Tk()
    app = MissionLogGUI(root)
    root.mainloop()