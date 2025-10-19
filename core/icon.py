import tkinter as tk
from tkinter import ttk, messagebox
import requests
from datetime import datetime, timezone, timedelta
import json
import pandas as pd
import logging
from core.logging_config import setup_logging
from typing import Dict, List, Optional
import time
import configparser
import threading
import os
import subprocess
import random
import re
import webbrowser

# Load config
iconconfig = configparser.ConfigParser()
from core.runtime_paths import app_path
iconconfig.read(app_path('orphan', 'icon.config'))

# Function to get player's first planet from mission log
def get_first_ingress():
    try:
        # Set up application data paths 
        APP_DATA = os.path.join(os.getenv('LOCALAPPDATA'), 'MLHD2')
        
        # Load config to check DEBUG mode
        config = configparser.ConfigParser()
        config.read(app_path('orphan', 'config.config'))
        DEBUG = config.getboolean('DEBUGGING', 'DEBUG', fallback=False)
        
        # Choose the appropriate Excel file
        EXCEL_FILE_PROD = os.path.join(APP_DATA, 'mission_log.xlsx')
        EXCEL_FILE_TEST = os.path.join(APP_DATA, 'mission_log_test.xlsx')
        excel_file = EXCEL_FILE_TEST if DEBUG else EXCEL_FILE_PROD
        
        # Read the mission log
        if os.path.exists(excel_file):
            df = pd.read_excel(excel_file)
            
            # Check if required columns exist
            if 'Time' in df.columns and 'Planet' in df.columns and not df.empty:
                # Convert Time column to datetime and sort by earliest first
                df['Time'] = pd.to_datetime(df['Time'].astype(str).str.replace('/', '-', regex=False), errors='coerce', dayfirst=True)
                df_sorted = df.dropna(subset=['Time', 'Planet']).sort_values('Time')
                
                # Get the first planet (chronologically)
                if not df_sorted.empty:
                    first_planet = df_sorted['Planet'].iloc[0]
                    return str(first_planet).strip()
        
        # Default fallback if no data found
        return "Super Earth"
        
    except Exception as e:
        logging.error(f"Error reading mission log for homeworld: {e}")
        return "Super Earth"

# Get player's homeworld planet
first_ingress = get_first_ingress()

ENEMY_ICONS = {
    "Automatons": iconconfig['EnemyIcons']['Automatons'],
    "Terminids": iconconfig['EnemyIcons']['Terminids'],
    "Illuminate": iconconfig['EnemyIcons']['Illuminate'],
    "Observing": iconconfig['EnemyIcons']['Observation'],
}

DIFFICULTY_ICONS = {
    "1 - TRIVIAL": iconconfig['DifficultyIcons']['1 - TRIVIAL'],
    "2 - EASY": iconconfig['DifficultyIcons']['2 - EASY'],
    "3 - MEDIUM": iconconfig['DifficultyIcons']['3 - MEDIUM'],
    "4 - CHALLENGING": iconconfig['DifficultyIcons']['4 - CHALLENGING'],
    "5 - HARD": iconconfig['DifficultyIcons']['5 - HARD'],
    "6 - EXTREME": iconconfig['DifficultyIcons']['6 - EXTREME'],
    "7 - SUICIDE MISSION": iconconfig['DifficultyIcons']['7 - SUICIDE MISSION'],
    "8 - IMPOSSIBLE": iconconfig['DifficultyIcons']['8 - IMPOSSIBLE'],
    "9 - HELLDIVE": iconconfig['DifficultyIcons']['9 - HELLDIVE'],
    "10 - SUPER HELLDIVE": iconconfig['DifficultyIcons']['10 - SUPER HELLDIVE']
}
SYSTEM_COLORS = {
    "Automatons": iconconfig['SystemColors']['Automatons'],
    "Terminids": iconconfig['SystemColors']['Terminids'],
    "Illuminate": iconconfig['SystemColors']['Illuminate']
}


# Base planet icons without First Ingress
_BASE_PLANET_ICONS = {
    "Super Earth": iconconfig['PlanetIcons']['Human Homeworld'],
    "Cyberstan": iconconfig['PlanetIcons']['Automaton Homeworld'],
    "Malevelon Creek": iconconfig['PlanetIcons']['Malevelon Creek'],
    "Calypso": iconconfig['PlanetIcons']['Calypso'],
    "Diaspora X": iconconfig['PlanetIcons']['Gloom'],
    "Enuliale": iconconfig['PlanetIcons']['Gloom'],
    "Epsilon Phoencis VI": iconconfig['PlanetIcons']['Gloom'],
    "Gemstone Bluffs": iconconfig['PlanetIcons']['Gloom'],
    "Nabatea Secundus": iconconfig['PlanetIcons']['Gloom'],
    "Navi VII": iconconfig['PlanetIcons']['Gloom'],
    "Azur Secundus": iconconfig['PlanetIcons']['Gloom'],
    "Erson Sands": iconconfig['PlanetIcons']['Gloom'],
    "Nivel 43": iconconfig['PlanetIcons']['Gloom'],
    "Zagon Prime": iconconfig['PlanetIcons']['Gloom'],
    "Hellmire": iconconfig['PlanetIcons']['Hellmire'],
    "Omicron": iconconfig['PlanetIcons']['Gloom'],
    "Oshaune": iconconfig['PlanetIcons']['Hive World'],
    "Fori Prime": iconconfig['PlanetIcons']['Gloom'],
    "Socorro III": iconconfig['PlanetIcons']['Gloom'],
    "Esker": iconconfig['PlanetIcons']['Gloom'],
    "Overgoe Prime": iconconfig['PlanetIcons']['Gloom'],
    "Partion": iconconfig['PlanetIcons']['Gloom'],
    "Estanu": iconconfig['PlanetIcons']['Gloom'],
    "Erata Prime": iconconfig['PlanetIcons']['Gloom'],
    "Crimsica": iconconfig['PlanetIcons']['Gloom'],
    "Aurora Bay": iconconfig['PlanetIcons']['Jet Brigade Factories'],
    "Chort Bay": iconconfig['PlanetIcons']['Jet Brigade Factories'],
    "Widow's Harbor": iconconfig['PlanetIcons']['Free Springs Retreat'],
    "Mog": iconconfig['PlanetIcons']['Illuminate Rally Locus'],
    "Bellatrix": iconconfig['PlanetIcons']['Illuminate Rally Locus'],
    "Hydrobius": iconconfig['PlanetIcons']['Illuminate Rally Locus'],
    "Haldus": iconconfig['PlanetIcons']['Illuminate Rally Locus'],
    "Mastia": iconconfig['PlanetIcons']['Governmental'],
    "Fenrir III": iconconfig['PlanetIcons']['Science'],
    "Tarsh": iconconfig['PlanetIcons']['Governmental'],
    "Claorell": iconconfig['PlanetIcons']['Hammer'],
    "Achernar Secundus": iconconfig['PlanetIcons']['Hammer'],
    "Mintoria": iconconfig['PlanetIcons']['Hammer'],
    "Turing": iconconfig['PlanetIcons']['Science'],
    "Emeria": iconconfig['PlanetIcons']['Governmental'],
    "Fort Union": iconconfig['PlanetIcons']['Governmental'],
    "Fort Sanctuary": iconconfig['PlanetIcons']['Governmental'],
    "Alamak VII": iconconfig['PlanetIcons']['Illuminate Stronghold'],
    "Alairt III": iconconfig['PlanetIcons']['Illuminate Stronghold'],
    "Wasat": iconconfig['PlanetIcons']['Database One'],
    "Pöpli IX": iconconfig['PlanetIcons']['Popli IX'],
    "Rogue 5": iconconfig['PlanetIcons']['Rogue 5'],
    "Seyshel Beach": iconconfig['PlanetIcons']['Seyshel Beach']
}

# Create combined PLANET_ICONS with homeworld support
PLANET_ICONS = _BASE_PLANET_ICONS.copy()

# Add or combine First Ingress icon
first_ingress_icon = iconconfig['PlanetIcons']['First Ingress']
if first_ingress in PLANET_ICONS:
    # Planet already has an icon, combine them
    existing_icon = PLANET_ICONS[first_ingress]
    PLANET_ICONS[first_ingress] = f"{existing_icon}{first_ingress_icon}"
else:
    # Planet doesn't have an icon, just add the homeworld icon
    PLANET_ICONS[first_ingress] = first_ingress_icon

    # Function to get player's most played planet from mission log
    def get_most_played_planet():
        try:
            # Set up application data paths 
            APP_DATA = os.path.join(os.getenv('LOCALAPPDATA'), 'MLHD2')
            
            # Load config to check DEBUG mode
            config = configparser.ConfigParser()
            config.read('config.config')
            DEBUG = config.getboolean('DEBUGGING', 'DEBUG', fallback=False)
            
            # Choose the appropriate Excel file
            EXCEL_FILE_PROD = os.path.join(APP_DATA, 'mission_log.xlsx')
            EXCEL_FILE_TEST = os.path.join(APP_DATA, 'mission_log_test.xlsx')
            excel_file = EXCEL_FILE_TEST if DEBUG else EXCEL_FILE_PROD
            
            # Read the mission log
            if os.path.exists(excel_file):
                df = pd.read_excel(excel_file)
                
                # Check if Planet column exists
                if 'Planet' in df.columns and not df.empty:
                    # Count occurrences of each planet and get the most frequent
                    planet_counts = df['Planet'].value_counts()
                    
                    if not planet_counts.empty:
                        most_played_planet = planet_counts.index[0]
                        return str(most_played_planet).strip()
            
            # Default fallback if no data found
            return "Super Earth"
            
        except Exception as e:
            logging.error(f"Error reading mission log for most played planet: {e}")
            return "Super Earth"

    # Get player's most played planet
    most_played_planet = get_most_played_planet()

    # Add or combine Favourite Planet icon
    favourite_planet_icon = iconconfig['PlanetIcons']['Favourite Planet']
    if most_played_planet in PLANET_ICONS:
        # Planet already has an icon, combine them
        existing_icon = PLANET_ICONS[most_played_planet]
        PLANET_ICONS[most_played_planet] = f"{existing_icon}{favourite_planet_icon}"
    else:
        # Planet doesn't have an icon, just add the favourite planet icon
        PLANET_ICONS[most_played_planet] = favourite_planet_icon

        # Load settings to get player's homeworld
        def load_player_homeworld():
            try:
                from core.runtime_paths import app_path
                with open(app_path('JSON', 'settings.json'), 'r') as f:
                    settings = json.load(f)
                    return settings.get('Player Homeworld', 'Super Earth')
            except Exception as e:
                logging.error(f"Error loading player homeworld from settings: {e}")
                return 'Super Earth'

        # Get player's homeworld from settings
        player_homeworld = load_player_homeworld()

        # Add or combine Player Homeworld icon
        player_homeworld_icon = iconconfig['PlanetIcons']['Player Homeworld']
        if player_homeworld in PLANET_ICONS:
            # Planet already has an icon, combine them
            existing_icon = PLANET_ICONS[player_homeworld]
            PLANET_ICONS[player_homeworld] = f"{existing_icon}{player_homeworld_icon}"
        else:
            # Planet doesn't have an icon, just add the homeworld icon
            PLANET_ICONS[player_homeworld] = player_homeworld_icon

CAMPAIGN_ICONS = {
    "Defense": iconconfig['CampaignIcons']['Defense'],
    "Liberation": iconconfig['CampaignIcons']['Liberation'],
    "Invasion": iconconfig['CampaignIcons']['Invasion'],
    "High-Priority": iconconfig['CampaignIcons']['High-Priority'],
    "Attrition": iconconfig['CampaignIcons']['Attrition'],
    "Battle for Super Earth": iconconfig['CampaignIcons']['Battle for Super Earth'],
}


MISSION_ICONS = {
    "Unlisted Mission": iconconfig['MissionIcons']['Unlisted Mission'],
    "Terminate Illegal Broadcast": iconconfig['MissionIcons']['Terminate Illegal Broadcast'],
    "Pump Fuel To ICBM": iconconfig['MissionIcons']['Pump Fuel To ICBM'],
    "Upload Escape Pod Data": iconconfig['MissionIcons']['Upload Escape Pod Data'],
    "Spread Democracy": iconconfig['MissionIcons']['Spread Democracy'],
    "Conduct Geological Survey": iconconfig['MissionIcons']['Conduct Geological Survey'],
    "Launch ICBM": iconconfig['MissionIcons']['Launch ICBM'],
    "Retrieve Valuable Data": iconconfig['MissionIcons']['Retrieve Valuable Data'],
    "Blitz: Search and Destroy": iconconfig['MissionIcons']['Blitz Search and Destroy'],
    "Emergency Evacuation": iconconfig['MissionIcons']['Emergency Evacuation'],
    "Retrieve Essential Personnel": iconconfig['MissionIcons']['Retrieve Essential Personnel'],
    "Evacuate High-Value Assets": iconconfig['MissionIcons']['Evacuate High-Value Assets'],
    "Eliminate Brood Commanders": iconconfig['MissionIcons']['Eliminate Brood Commanders'],
    "Eliminate Chargers": iconconfig['MissionIcons']['Eliminate Chargers'],
    "Eliminate Impaler": iconconfig['MissionIcons']['Eliminate Impaler'],
    "Eliminate Bile Titans": iconconfig['MissionIcons']['Eliminate Bile Titans'],
    "Activate E-710 Pumps": iconconfig['MissionIcons']['Activate E-710 Pumps'],
    "Purge Hatcheries": iconconfig['MissionIcons']['Purge Hatcheries'],
    "Enable E-710 Extraction": iconconfig['MissionIcons']['Enable E-710 Extraction'],
    "Nuke Nursery": iconconfig['MissionIcons']['Nuke Nursery'],
    "Activate Terminid Control System": iconconfig['MissionIcons']['Activate Terminid Control System'],
    "Deactivate Terminid Control System": iconconfig['MissionIcons']['Deactivate Terminid Control System'],
    "Deploy Dark Fluid": iconconfig['MissionIcons']['Deploy Dark Fluid'],
    "Eradicate Terminid Swarm": iconconfig['MissionIcons']['Eradicate Terminid Swarm'],
    "Destroy Transmission Network": iconconfig['MissionIcons']['Destroy Transmission Network'],
    "Eliminate Devastators": iconconfig['MissionIcons']['Eliminate Devastators'],
    "Eliminate Automaton Hulks": iconconfig['MissionIcons']['Eliminate Automaton Hulks'],
    "Eliminate Automaton Factory Strider": iconconfig['MissionIcons']['Eliminate Automaton Factory Strider'],
    "Sabotage Supply Bases": iconconfig['MissionIcons']['Sabotage Supply Bases'],
    "Sabotage Air Base": iconconfig['MissionIcons']['Sabotage Air Base'],
    "Eradicate Automaton Forces": iconconfig['MissionIcons']['Eradicate Automaton Forces'],
    "Destroy Command Bunkers": iconconfig['MissionIcons']['Destroy Command Bunkers'],
    "Neutralize Orbital Defenses": iconconfig['MissionIcons']['Neutralize Orbital Defenses'],
    "Evacuate Colonists": iconconfig['MissionIcons']['Evacuate Colonists'],
    "Retrieve Recon Craft Intel": iconconfig['MissionIcons']['Retrieve Recon Craft Intel'],
    "Free Colony": iconconfig['MissionIcons']['Free Colony'],
    "Blitz: Destroy Illuminate Warp Ships": iconconfig['MissionIcons']['Blitz Destroy Illuminate Warp Ships'],
    "Destroy Harvesters": iconconfig['MissionIcons']['Destroy Harvesters'],
    "Extract Research Probe Data": iconconfig['MissionIcons']['Extract Research Probe Data'],
    "Collect Meteorological Data": iconconfig['MissionIcons']['Collect Meteorological Data'],
    "Collect Gloom-Infused Oil": iconconfig['MissionIcons']['Collect Gloom-Infused Oil'],
    "Blitz: Secure Research Site": iconconfig['MissionIcons']['Blitz Secure Research Site'],
    "Collect Gloom Spore Readings": iconconfig['MissionIcons']['Collect Gloom Spore Readings'],
    "Chart Terminid Tunnels": iconconfig['MissionIcons']['Chart Terminid Tunnels'],
    "Take Down Overship": iconconfig['MissionIcons']['Take Down Overship'],
    "Repel Invasion Fleet": iconconfig['MissionIcons']['Repel Invasion Fleet'],
    "Evacuate Citizens": iconconfig['MissionIcons']['Evacuate Citizens'],
    "Free The City": iconconfig['MissionIcons']['Free The City'],
    "Restore Air Quality": iconconfig['MissionIcons']['Restore Air Quality'],
    "Cleanse Infested District": iconconfig['MissionIcons']['Cleanse Infested District'],
    "Destroy Spore Lung": iconconfig['MissionIcons']['Destroy Spore Lung'],
    "Conduct Mobile E-711 Extraction": iconconfig['MissionIcons']['Conduct Mobile E-711 Extraction'],
    "Extract Mysterious Substance": iconconfig['MissionIcons']['Extract Mysterious Substance'],
    "Restore Oil Pumps": iconconfig['MissionIcons']['Restore Oil Pumps'],
    "Secure E-711 Extraction": iconconfig['MissionIcons']['Secure E-711 Extraction'],
}

# Biome Banners per Planet (used as embed image backgrounds)
BIOME_BANNERS = {
    "Propus": iconconfig['BiomeBanners']['Desert Dunes'],
    "Klen Dahth II": iconconfig['BiomeBanners']['Desert Dunes'],
    "Outpost 32": iconconfig['BiomeBanners']['Desert Dunes'],
    "Lastofe": iconconfig['BiomeBanners']['Desert Dunes'],
    "Diaspora X": iconconfig['BiomeBanners']['Desert Dunes'],
    "Zagon Prime": iconconfig['BiomeBanners']['Desert Dunes'],
    "Osupsam": iconconfig['BiomeBanners']['Desert Dunes'],
    "Mastia": iconconfig['BiomeBanners']['Desert Dunes'],
    "Caramoor": iconconfig['BiomeBanners']['Desert Dunes'],
    "Heze Bay": iconconfig['BiomeBanners']['Desert Dunes'],
    "Viridia Prime": iconconfig['BiomeBanners']['Desert Dunes'],
    "Durgen": iconconfig['BiomeBanners']['Desert Dunes'],
    "Phact Bay": iconconfig['BiomeBanners']['Desert Dunes'],
    "Keid": iconconfig['BiomeBanners']['Desert Dunes'],
    "Zzaniah Prime": iconconfig['BiomeBanners']['Desert Dunes'],
    "Choohe": iconconfig['BiomeBanners']['Desert Dunes'],
    "Pilen V": iconconfig['BiomeBanners']['Desert Cliffs'],
    "Zea Rugosia": iconconfig['BiomeBanners']['Desert Cliffs'],
    "Myradesh": iconconfig['BiomeBanners']['Desert Cliffs'],
    "Azur Secundus": iconconfig['BiomeBanners']['Desert Cliffs'],
    "Erata Prime": iconconfig['BiomeBanners']['Desert Cliffs'],
    "Mortax Prime": iconconfig['BiomeBanners']['Desert Cliffs'],
    "Cerberus IIIc": iconconfig['BiomeBanners']['Desert Cliffs'],
    "Ustotu": iconconfig['BiomeBanners']['Desert Cliffs'],
    "Erson Sands": iconconfig['BiomeBanners']['Desert Cliffs'],
    "Canopus": iconconfig['BiomeBanners']['Desert Cliffs'],
    "Hydrobius": iconconfig['BiomeBanners']['Desert Cliffs'],
    "Polaris Prime": iconconfig['BiomeBanners']['Desert Cliffs'],
    "Darrowsport": iconconfig['BiomeBanners']['Acidic Badlands'],
    "Darius II": iconconfig['BiomeBanners']['Acidic Badlands'],
    "Chort Bay": iconconfig['BiomeBanners']['Acidic Badlands'],
    "Leng Secundus": iconconfig['BiomeBanners']['Acidic Badlands'],
    "Rirga Bay": iconconfig['BiomeBanners']['Acidic Badlands'],
    "Shete": iconconfig['BiomeBanners']['Acidic Badlands'],
    "Skaash": iconconfig['BiomeBanners']['Acidic Badlands'],
    "Wraith": iconconfig['BiomeBanners']['Acidic Badlands'],
    "Slif": iconconfig['BiomeBanners']['Acidic Badlands'],
    "Wilford Station": iconconfig['BiomeBanners']['Acidic Badlands'],
    "Botein": iconconfig['BiomeBanners']['Acidic Badlands'],
    "Wasat": iconconfig['BiomeBanners']['Acidic Badlands'],
    "Esker": iconconfig['BiomeBanners']['Acidic Badlands'],
    "Charbal-VII": iconconfig['BiomeBanners']['Acidic Badlands'],
    "Kraz": iconconfig['BiomeBanners']['Rocky Canyons'],
    "Hydrofall Prime": iconconfig['BiomeBanners']['Rocky Canyons'],
    "Myrium": iconconfig['BiomeBanners']['Rocky Canyons'],
    "Vernen Wells": iconconfig['BiomeBanners']['Rocky Canyons'],
    "Calypso": iconconfig['BiomeBanners']['Rocky Canyons'],
    "Achird III": iconconfig['BiomeBanners']['Rocky Canyons'],
    "Azterra": iconconfig['BiomeBanners']['Rocky Canyons'],
    "Senge 23": iconconfig['BiomeBanners']['Rocky Canyons'],
    "Emeria": iconconfig['BiomeBanners']['Rocky Canyons'],
    "Fori Prime": iconconfig['BiomeBanners']['Rocky Canyons'],
    "Mekbuda": iconconfig['BiomeBanners']['Rocky Canyons'],
    "Effluvia": iconconfig['BiomeBanners']['Rocky Canyons'],
    "Pioneer II": iconconfig['BiomeBanners']['Rocky Canyons'],
    "Castor": iconconfig['BiomeBanners']['Rocky Canyons'],
    "Prasa": iconconfig['BiomeBanners']['Rocky Canyons'],
    "Kuma": iconconfig['BiomeBanners']['Rocky Canyons'],
	"Widow's Harbor": iconconfig['BiomeBanners']['Moon'],
	"RD-4": iconconfig['BiomeBanners']['Moon'],
	"Claorell": iconconfig['BiomeBanners']['Moon'],
	"Maia": iconconfig['BiomeBanners']['Moon'],
	"Curia": iconconfig['BiomeBanners']['Moon'],
	"Sirius": iconconfig['BiomeBanners']['Moon'],
	"Rasp": iconconfig['BiomeBanners']['Moon'],
	"Terrek": iconconfig['BiomeBanners']['Moon'],
	"Dolph": iconconfig['BiomeBanners']['Moon'],
	"Fenrir III": iconconfig['BiomeBanners']['Moon'],
	"Zosma": iconconfig['BiomeBanners']['Moon'],
	"Euphoria III": iconconfig['BiomeBanners']['Moon'],
	"Primordia": iconconfig['BiomeBanners']['Volcanic Jungle'],
	"Rogue 5": iconconfig['BiomeBanners']['Volcanic Jungle'],
	"Alta V": iconconfig['BiomeBanners']['Volcanic Jungle'],
	"Mantes": iconconfig['BiomeBanners']['Volcanic Jungle'],
	"Gaellivare": iconconfig['BiomeBanners']['Volcanic Jungle'],
	"Meissa": iconconfig['BiomeBanners']['Volcanic Jungle'],
	"Spherion": iconconfig['BiomeBanners']['Volcanic Jungle'],
	"Kirrik": iconconfig['BiomeBanners']['Volcanic Jungle'],
	"Baldrick Prime": iconconfig['BiomeBanners']['Volcanic Jungle'],
	"Zegema Paradise": iconconfig['BiomeBanners']['Volcanic Jungle'],
	"Irulta": iconconfig['BiomeBanners']['Volcanic Jungle'],
	"Regnus": iconconfig['BiomeBanners']['Volcanic Jungle'],
	"Navi VII": iconconfig['BiomeBanners']['Volcanic Jungle'],
	"Oasis": iconconfig['BiomeBanners']['Volcanic Jungle'],
	"Pollux 31": iconconfig['BiomeBanners']['Volcanic Jungle'],
	"Aesir Pass": iconconfig['BiomeBanners']['Deadlands'],
	"Alderidge Cove": iconconfig['BiomeBanners']['Deadlands'],
	"Penta": iconconfig['BiomeBanners']['Deadlands'],
	"Ain-5": iconconfig['BiomeBanners']['Deadlands'],
	"Skat Bay": iconconfig['BiomeBanners']['Deadlands'],
	"Alaraph": iconconfig['BiomeBanners']['Deadlands'],
	"Veil": iconconfig['BiomeBanners']['Deadlands'],
	"Troost": iconconfig['BiomeBanners']['Deadlands'],
	"Haka": iconconfig['BiomeBanners']['Deadlands'],
	"Nivel 43": iconconfig['BiomeBanners']['Deadlands'],
	"Pandion-XXIV": iconconfig['BiomeBanners']['Deadlands'],
	"Cirrus": iconconfig['BiomeBanners']['Deadlands'],
	"Mort": iconconfig['BiomeBanners']['Deadlands'],
	"Iridica": iconconfig['BiomeBanners']['Ethereal Jungle'],
	"Seyshel Beach": iconconfig['BiomeBanners']['Ethereal Jungle'],
	"Ursica XI": iconconfig['BiomeBanners']['Ethereal Jungle'],
	"Acubens Prime": iconconfig['BiomeBanners']['Ethereal Jungle'],
	"Fort Justice": iconconfig['BiomeBanners']['Ethereal Jungle'],
	"Sulfura": iconconfig['BiomeBanners']['Ethereal Jungle'],
	"Alamak VII": iconconfig['BiomeBanners']['Ethereal Jungle'],
	"Tibit": iconconfig['BiomeBanners']['Ethereal Jungle'],
	"Mordia 9": iconconfig['BiomeBanners']['Ethereal Jungle'],
	"Emorath": iconconfig['BiomeBanners']['Ethereal Jungle'],
	"Shallus": iconconfig['BiomeBanners']['Ethereal Jungle'],
	"Vindemitarix Prime": iconconfig['BiomeBanners']['Ethereal Jungle'],
	"Zefia": iconconfig['BiomeBanners']['Ethereal Jungle'],
	"Bekvam III": iconconfig['BiomeBanners']['Ethereal Jungle'],
	"Turing": iconconfig['BiomeBanners']['Ethereal Jungle'],
	"New Haven": iconconfig['BiomeBanners']['Ionic Jungle'],
	"Prosperity Falls": iconconfig['BiomeBanners']['Ionic Jungle'],
	"Veld": iconconfig['BiomeBanners']['Ionic Jungle'],
	"Malevelon Creek": iconconfig['BiomeBanners']['Ionic Jungle'],
	"Siemnot": iconconfig['BiomeBanners']['Ionic Jungle'],
	"Alairt III": iconconfig['BiomeBanners']['Ionic Jungle'],
	"Merak": iconconfig['BiomeBanners']['Ionic Jungle'],
	"Gemma": iconconfig['BiomeBanners']['Ionic Jungle'],
	"Minchir": iconconfig['BiomeBanners']['Ionic Jungle'],
	"Kuper": iconconfig['BiomeBanners']['Ionic Jungle'],
	"Brink-2": iconconfig['BiomeBanners']['Ionic Jungle'],
	"Peacock": iconconfig['BiomeBanners']['Ionic Jungle'],
	"Genesis Prime": iconconfig['BiomeBanners']['Ionic Jungle'],
	"New Kiruna": iconconfig['BiomeBanners']['Icy Glaciers'],
	"Borea": iconconfig['BiomeBanners']['Icy Glaciers'],
	"Marfark": iconconfig['BiomeBanners']['Icy Glaciers'],
	"Epsilon Phoencis VI": iconconfig['BiomeBanners']['Icy Glaciers'],
	"Kelvinor": iconconfig['BiomeBanners']['Icy Glaciers'],
	"Vog-Sojoth": iconconfig['BiomeBanners']['Icy Glaciers'],
	"Alathfar XI": iconconfig['BiomeBanners']['Icy Glaciers'],
	"Okul VI": iconconfig['BiomeBanners']['Icy Glaciers'],
	"Julheim": iconconfig['BiomeBanners']['Icy Glaciers'],
	"Hadar": iconconfig['BiomeBanners']['Icy Glaciers'],
	"Mog": iconconfig['BiomeBanners']['Icy Glaciers'],
	"Vandalon IV": iconconfig['BiomeBanners']['Icy Glaciers'],
	"Arkturus": iconconfig['BiomeBanners']['Icy Glaciers'],
	"Hesoe Prime": iconconfig['BiomeBanners']['Icy Glaciers'],
	"Vega Bay": iconconfig['BiomeBanners']['Icy Glaciers'],
	"New Stockholm": iconconfig['BiomeBanners']['Icy Glaciers'],
	"Heeth": iconconfig['BiomeBanners']['Icy Glaciers'],
	"Choepessa IV": iconconfig['BiomeBanners']['Boneyard'],
	"Martyr's Bay": iconconfig['BiomeBanners']['Boneyard'],
	"Lesath": iconconfig['BiomeBanners']['Boneyard'],
	"Cyberstan": iconconfig['BiomeBanners']['Boneyard'],
	"Deneb Secundus": iconconfig['BiomeBanners']['Boneyard'],
	"Acrux IX": iconconfig['BiomeBanners']['Boneyard'],
	"Inari": iconconfig['BiomeBanners']['Boneyard'],
	"Estanu": iconconfig['BiomeBanners']['Boneyard'],
	"Stor Tha Prime": iconconfig['BiomeBanners']['Boneyard'],
	"Halies Port": iconconfig['BiomeBanners']['Boneyard'],
	"Oslo Station": iconconfig['BiomeBanners']['Boneyard'],
	"Igla": iconconfig['BiomeBanners']['Boneyard'],
	"Krakatwo": iconconfig['BiomeBanners']['Boneyard'],
	"Grafmere": iconconfig['BiomeBanners']['Boneyard'],
	"Eukoria": iconconfig['BiomeBanners']['Boneyard'],
	"Tien Kwan": iconconfig['BiomeBanners']['Boneyard'],
	"Pathfinder V": iconconfig['BiomeBanners']['Plains'],
	"Fort Union": iconconfig['BiomeBanners']['Plains'],
	"Volterra": iconconfig['BiomeBanners']['Plains'],
	"Gemstone Bluffs": iconconfig['BiomeBanners']['Plains'],
	"Acamar IV": iconconfig['BiomeBanners']['Plains'],
	"Achernar Secundus": iconconfig['BiomeBanners']['Plains'],
	"Electra Bay": iconconfig['BiomeBanners']['Plains'],
	"Afoyay Bay": iconconfig['BiomeBanners']['Plains'],
	"Matar Bay": iconconfig['BiomeBanners']['Plains'],
	"Reaf": iconconfig['BiomeBanners']['Plains'],
	"Termadon": iconconfig['BiomeBanners']['Plains'],
	"Fenmire": iconconfig['BiomeBanners']['Plains'],
	"The Weir": iconconfig['BiomeBanners']['Plains'],
	"Bellatrix": iconconfig['BiomeBanners']['Plains'],
	"Oshaune": iconconfig['BiomeBanners']['Hive World'],
	"Varylia 5": iconconfig['BiomeBanners']['Plains'],
	"Hort": iconconfig['BiomeBanners']['Plains'],
	"Draupnir": iconconfig['BiomeBanners']['Plains'],
	"Obari": iconconfig['BiomeBanners']['Plains'],
	"Mintoria": iconconfig['BiomeBanners']['Plains'],
	"Midasburg": iconconfig['BiomeBanners']['Tundra'],
	"Demiurg": iconconfig['BiomeBanners']['Tundra'],
	"Kerth Secundus": iconconfig['BiomeBanners']['Tundra'],
	"Aurora Bay": iconconfig['BiomeBanners']['Tundra'],
	"Martale": iconconfig['BiomeBanners']['Tundra'],
	"Crucible": iconconfig['BiomeBanners']['Tundra'],
	"Shelt": iconconfig['BiomeBanners']['Tundra'],
	"Trandor": iconconfig['BiomeBanners']['Tundra'],
	"Andar": iconconfig['BiomeBanners']['Tundra'],
	"Diluvia": iconconfig['BiomeBanners']['Tundra'],
	"Bunda Secundus": iconconfig['BiomeBanners']['Tundra'],
	"Ilduna Prime": iconconfig['BiomeBanners']['Tundra'],
	"Omicron": iconconfig['BiomeBanners']['Tundra'],
	"Ras Algethi": iconconfig['BiomeBanners']['Tundra'],
	"Duma Tyr": iconconfig['BiomeBanners']['Tundra'],
	"Adhara": iconconfig['BiomeBanners']['Scorched Moor'],
	"Hellmire": iconconfig['BiomeBanners']['Scorched Moor'],
	"Imber": iconconfig['BiomeBanners']['Scorched Moor'],
	"Menkent": iconconfig['BiomeBanners']['Scorched Moor'],
	"Blistica": iconconfig['BiomeBanners']['Scorched Moor'],
	"Herthon Secundus": iconconfig['BiomeBanners']['Scorched Moor'],
	"Pöpli IX": iconconfig['BiomeBanners']['Scorched Moor'],
	"Partion": iconconfig['BiomeBanners']['Scorched Moor'],
	"Wezen": iconconfig['BiomeBanners']['Scorched Moor'],
	"Marre IV": iconconfig['BiomeBanners']['Scorched Moor'],
	"Karlia": iconconfig['BiomeBanners']['Scorched Moor'],
	"Maw": iconconfig['BiomeBanners']['Scorched Moor'],
	"Kneth Port": iconconfig['BiomeBanners']['Scorched Moor'],
	"Grand Errant": iconconfig['BiomeBanners']['Scorched Moor'],
	"Fort Sanctuary": iconconfig['BiomeBanners']['Ionic Crimson'],
	"Elysian Meadows": iconconfig['BiomeBanners']['Ionic Crimson'],
	"Acrab XI": iconconfig['BiomeBanners']['Ionic Crimson'],
	"Enuliale": iconconfig['BiomeBanners']['Ionic Crimson'],
	"Liberty Ridge": iconconfig['BiomeBanners']['Ionic Crimson'],
	"Stout": iconconfig['BiomeBanners']['Ionic Crimson'],
	"Gatria": iconconfig['BiomeBanners']['Ionic Crimson'],
	"Freedom Peak": iconconfig['BiomeBanners']['Ionic Crimson'],
	"Ubanea": iconconfig['BiomeBanners']['Ionic Crimson'],
	"Valgaard": iconconfig['BiomeBanners']['Ionic Crimson'],
	"Valmox": iconconfig['BiomeBanners']['Ionic Crimson'],
	"Overgoe Prime": iconconfig['BiomeBanners']['Ionic Crimson'],
	"Providence": iconconfig['BiomeBanners']['Ionic Crimson'],
	"Kharst": iconconfig['BiomeBanners']['Ionic Crimson'],
	"Gunvald": iconconfig['BiomeBanners']['Ionic Crimson'],
	"Yed Prior": iconconfig['BiomeBanners']['Ionic Crimson'],
	"Ingmar": iconconfig['BiomeBanners']['Ionic Crimson'],
	"Crimsica": iconconfig['BiomeBanners']['Ionic Crimson'],
	"Charon Prime": iconconfig['BiomeBanners']['Ionic Crimson'],
	"Clasa": iconconfig['BiomeBanners']['Basic Swamp'],
	"Seasse": iconconfig['BiomeBanners']['Basic Swamp'],
	"Parsh": iconconfig['BiomeBanners']['Basic Swamp'],
	"East Iridium Trading Bay": iconconfig['BiomeBanners']['Basic Swamp'],
	"Gacrux": iconconfig['BiomeBanners']['Basic Swamp'],
	"Barabos": iconconfig['BiomeBanners']['Basic Swamp'],
	"Ivis": iconconfig['BiomeBanners']['Fractured Planet'],
	"Fornskogur II": iconconfig['BiomeBanners']['Basic Swamp'],
	"Nabatea Secundus": iconconfig['BiomeBanners']['Basic Swamp'],
	"Haldus": iconconfig['BiomeBanners']['Basic Swamp'],
	"Caph": iconconfig['BiomeBanners']['Basic Swamp'],
	"Bore Rock": iconconfig['BiomeBanners']['Basic Swamp'],
	"X-45": iconconfig['BiomeBanners']['Basic Swamp'],
	"Pherkad Secundus": iconconfig['BiomeBanners']['Basic Swamp'],
	"Krakabos": iconconfig['BiomeBanners']['Basic Swamp'],
	"Asperoth Prime": iconconfig['BiomeBanners']['Basic Swamp'],
	"Atrama": iconconfig['BiomeBanners']['Haunted Swamp'],
	"Setia": iconconfig['BiomeBanners']['Haunted Swamp'],
	"Tarsh": iconconfig['BiomeBanners']['Haunted Swamp'],
	"Gar Haren": iconconfig['BiomeBanners']['Haunted Swamp'],
	"Merga IV": iconconfig['BiomeBanners']['Haunted Swamp'],
	"Ratch": iconconfig['BiomeBanners']['Haunted Swamp'],
	"Bashyr": iconconfig['BiomeBanners']['Haunted Swamp'],
	"Nublaria I": iconconfig['BiomeBanners']['Haunted Swamp'],
	"Solghast": iconconfig['BiomeBanners']['Haunted Swamp'],
	"Iro": iconconfig['BiomeBanners']['Haunted Swamp'],
	"Socorro III": iconconfig['BiomeBanners']['Haunted Swamp'],
	"Khandark": iconconfig['BiomeBanners']['Haunted Swamp'],
	"Klaka 5": iconconfig['BiomeBanners']['Haunted Swamp'],
	"Skitter": iconconfig['BiomeBanners']['Haunted Swamp'],
    "Angel's Venture": iconconfig['BiomeBanners']['Fractured Planet'],
    "Moradesh": iconconfig['BiomeBanners']['Fractured Planet'],
    "Meridia": iconconfig['BiomeBanners']['Black Hole'],
    "Super Earth": iconconfig['BiomeBanners']['Super Earth'],
    "Mars": iconconfig['BiomeBanners']['Mars']
}

SUBFACTION_BANNERS = {
    "Automaton Legion": iconconfig['SubfactionBanners'].get('AutomatonLegion', 'Automaton Legion'),
    "Terminid Horde": iconconfig['SubfactionBanners'].get('TerminidHorde', 'Terminid Horde'),
    "Illuminate Cult": iconconfig['SubfactionBanners'].get('IlluminateCult', 'Illuminate Cult'),
    "Jet Brigade": iconconfig['SubfactionBanners'].get('JetBrigade', 'Jet Brigade'),
    "Predator Strain": iconconfig['SubfactionBanners'].get('PredatorStrain', 'Predator Strain'),
    "Incineration Corps": iconconfig['SubfactionBanners'].get('IncinerationCorps', 'Incineration Corps'),
    "Jet Brigade & Incineration Corps": iconconfig['SubfactionBanners'].get('JetBrigadeIncinerationCorps', 'Jet Brigade & Incineration Corps'),
    "Spore Burst Strain": iconconfig['SubfactionBanners'].get('SporeBurstStrain', 'Spore Burst Strain'),
    "The Great Host": iconconfig['SubfactionBanners'].get('TheGreatHost', 'The Great Host'),
    "Rupture Strain": iconconfig['SubfactionBanners'].get('RuptureStrain', 'Rupture Strain'),
    "Dragonroach": iconconfig['SubfactionBanners'].get('Dragonroach', 'Dragonroach'),
    "Predator Strain & Dragonroach": iconconfig['SubfactionBanners'].get('PredatorStrainDragonroach', 'Predator Strain & Dragonroach'),
    "Spore Burst Strain & Dragonroach": iconconfig['SubfactionBanners'].get('SporeBurstStrainDragonroach', 'Spore Burst Strain & Dragonroach'),
    "Rupture Strain & Dragonroach": iconconfig['SubfactionBanners'].get('RuptureStrainDragonroach', 'Rupture Strain & Dragonroach')
}

HELLDIVER_BANNERS = {
    "Helldiver1": iconconfig['HelldiverBanners']['Helldiver1'],
    "Helldiver2": iconconfig['HelldiverBanners']['Helldiver2'],
	"Helldiver3": iconconfig['HelldiverBanners']['Helldiver3'],
	"Helldiver4": iconconfig['HelldiverBanners']['Helldiver4'],
	"Helldiver5": iconconfig['HelldiverBanners']['Helldiver5'],
	"Helldiver6": iconconfig['HelldiverBanners']['Helldiver6']
}

SUBFACTION_ICONS = {
    "Automaton Legion": iconconfig['SubfactionIcons']['AutomatonLegion'],
    "Terminid Horde": iconconfig['SubfactionIcons']['TerminidHorde'],
    "Illuminate Cult": iconconfig['SubfactionIcons']['IlluminateCult'],
    "Jet Brigade": iconconfig['SubfactionIcons']['JetBrigade'],
    "Predator Strain": iconconfig['SubfactionIcons']['PredatorStrain'],
    "Incineration Corps": iconconfig['SubfactionIcons']['IncinerationCorps'],
    "Jet Brigade & Incineration Corps": iconconfig['SubfactionIcons']['JetBrigadeIncinerationCorps'],
    "Spore Burst Strain": iconconfig['SubfactionIcons']['SporeBurstStrain'],
    "The Great Host": iconconfig['SubfactionIcons']['TheGreatHost'],
    "Rupture Strain": iconconfig['SubfactionIcons']['RuptureStrain'],
    "Dragonroach": iconconfig['SubfactionIcons']['Dragonroach'],
    "Predator Strain & Dragonroach": iconconfig['SubfactionIcons']['PredatorStrainDragonroach'],
    "Spore Burst Strain & Dragonroach": iconconfig['SubfactionIcons']['SporeBurstStrainDragonroach'],
    "Rupture Strain & Dragonroach": iconconfig['SubfactionIcons']['RuptureStrainDragonroach']
}

HVT_ICONS = {
    "HiveLords": iconconfig['HVTIcons']['HiveLords'],
}

DSS_ICONS = {
    "Inactive": iconconfig['MiscIcon']['Inactive'],
    "Eagle Storm": iconconfig['MiscIcon']['Eagle Storm'],
    "Orbital Blockade": iconconfig['MiscIcon']['Orbital Blockade'],
    "Heavy Ordnance Distribution": iconconfig['MiscIcon']['Heavy Ordnance Distribution'],
    "Eagle Blockade": iconconfig['MiscIcon']['Eagle Blockade']
}

TITLE_ICONS = {
    "CADET": iconconfig['TitleIcons']['CADET'],
    "SPACE CADET": iconconfig['TitleIcons']['SPACE CADET'], 
    "SERGEANT": iconconfig['TitleIcons']['SERGEANT'],
    "MASTER SERGEANT": iconconfig['TitleIcons']['MASTER SERGEANT'],
    "CHIEF": iconconfig['TitleIcons']['CHIEF'],
    "SPACE CHIEF PRIME": iconconfig['TitleIcons']['SPACE CHIEF PRIME'],
    "DEATH CAPTAIN": iconconfig['TitleIcons']['DEATH CAPTAIN'],
    "MARSHAL": iconconfig['TitleIcons']['MARSHAL'],
    "STAR MARSHAL": iconconfig['TitleIcons']['STAR MARSHAL'],
    "ADMIRAL": iconconfig['TitleIcons']['ADMIRAL'], 
    "SKULL ADMIRAL": iconconfig['TitleIcons']['SKULL ADMIRAL'],
    "FLEET ADMIRAL": iconconfig['TitleIcons']['FLEET ADMIRAL'],
    "ADMIRABLE ADMIRAL": iconconfig['TitleIcons']['ADMIRABLE ADMIRAL'],
    "COMMANDER": iconconfig['TitleIcons']['COMMANDER'],
    "GALACTIC COMMANDER": iconconfig['TitleIcons']['GALACTIC COMMANDER'],
    "HELL COMMANDER": iconconfig['TitleIcons']['HELL COMMANDER'],
    "GENERAL": iconconfig['TitleIcons']['GENERAL'],
    "5-STAR GENERAL": iconconfig['TitleIcons']['5-STAR GENERAL'],
    "10-STAR GENERAL": iconconfig['TitleIcons']['10-STAR GENERAL'],
    "PRIVATE": iconconfig['TitleIcons']['PRIVATE'],
    "SUPER PRIVATE": iconconfig['TitleIcons']['SUPER PRIVATE'],
    "SUPER CITIZEN": iconconfig['TitleIcons']['SUPER CITIZEN'],
    "VIPER COMMANDO": iconconfig['TitleIcons']['VIPER COMMANDO'],
    "FIRE SAFETY OFFICER": iconconfig['TitleIcons']['FIRE SAFETY OFFICER'],
    "EXPERT EXTERMINATOR": iconconfig['TitleIcons']['EXPERT EXTERMINATOR'],
    "FREE OF THOUGHT": iconconfig['TitleIcons']['FREE OF THOUGHT'],
    "SUPER PEDESTRIAN": iconconfig['TitleIcons']['SUPER PEDESTRIAN'],
    "ASSAULT INFANTRY": iconconfig['TitleIcons']['ASSAULT INFANTRY'],
    "SERVANT OF FREEDOM": iconconfig['TitleIcons']['SERVANT OF FREEDOM'],
    "SUPER SHERIFF": iconconfig['TitleIcons']['SUPER SHERIFF'],
    "DECORATED HERO": iconconfig['TitleIcons']['DECORATED HERO'],
    "EXTRA JUDICIAL": iconconfig['TitleIcons']['EXTRA JUDICIAL'],
    "EXEMPLARY SUBJECT": iconconfig['TitleIcons']['EXEMPLARY SUBJECT'],
    "ROOKIE": iconconfig['TitleIcons']['ROOKIE'],
    "BURIER OF HEADS": iconconfig['TitleIcons']['BURIER OF HEADS']
}

PROFILE_PICTURES = {
    "B-01 Tactical": iconconfig['ProfilePictures']['B-01 Tactical'],
    "TR-7 Ambassador of the Brand": iconconfig['ProfilePictures']['TR-7 Ambassador of the Brand'],
    "TR-9 Cavalier of Democracy": iconconfig['ProfilePictures']['TR-9 Cavalier of Democracy'],
    "TR-62 Knight": iconconfig['ProfilePictures']['TR-62 Knight'],
    "DP-53 Savior of the Free": iconconfig['ProfilePictures']['DP-53 Savior of the Free'],
    "TR-117 Alpha Commander": iconconfig['ProfilePictures']['TR-117 Alpha Commander'],
    "SC-37 Legionnaire": iconconfig['ProfilePictures']['SC-37 Legionnaire'],
    "SC-15 Drone Master": iconconfig['ProfilePictures']['SC-15 Drone Master'],
    "SC-34 Infiltrator": iconconfig['ProfilePictures']['SC-34 Infiltrator'],
    "FS-05 Marksman": iconconfig['ProfilePictures']['FS-05 Marksman'],
    "CE-35 Trench Engineer": iconconfig['ProfilePictures']['CE-35 Trench Engineer'],
    "CM-09 Bonesnapper": iconconfig['ProfilePictures']['CM-09 Bonesnapper'],
    "DP-40 Hero of the Federation": iconconfig['ProfilePictures']['DP-40 Hero of the Federation'],
    "FS-23 Battle Master": iconconfig['ProfilePictures']['FS-23 Battle Master'],
    "SC-30 Trailblazer Scout": iconconfig['ProfilePictures']['SC-30 Trailblazer Scout'],
    "SA-04 Combat Technician": iconconfig['ProfilePictures']['SA-04 Combat Technician'],
    "CM-14 Physician": iconconfig['ProfilePictures']['CM-14 Physician'],
    "DP-11 Champion of the People": iconconfig['ProfilePictures']['DP-11 Champion of the People'],
    "SA-25 Steel Trooper": iconconfig['ProfilePictures']['SA-25 Steel Trooper'],
    "SA-12 Servo Assisted": iconconfig['ProfilePictures']['SA-12 Servo Assisted'],
    "SA-32 Dynamo": iconconfig['ProfilePictures']['SA-32 Dynamo'],
    "B-24 Enforcer": iconconfig['ProfilePictures']['B-24 Enforcer'],
    "CE-74 Breaker": iconconfig['ProfilePictures']['CE-74 Breaker'],
    "B-27 Fortified Commando": iconconfig['ProfilePictures']['B-27 Fortified Commando'],
    "FS-38 Eradicator": iconconfig['ProfilePictures']['FS-38 Eradicator'],
    "B-08 Light Gunner": iconconfig['ProfilePictures']['B-08 Light Gunner'],
    "FS-61 Dreadnought": iconconfig['ProfilePictures']['FS-61 Dreadnought'],
    "FS-11 Executioner": iconconfig['ProfilePictures']['FS-11 Executioner'],
    "CM-21 Trench Paramedic": iconconfig['ProfilePictures']['CM-21 Trench Paramedic'],
    "CE-81 Juggernaut": iconconfig['ProfilePictures']['CE-81 Juggernaut'],
    "FS-34 Exterminator": iconconfig['ProfilePictures']['FS-34 Exterminator'],
    "CE-67 Titan": iconconfig['ProfilePictures']['CE-67 Titan'],
    "CM-17 Butcher": iconconfig['ProfilePictures']['CM-17 Butcher'],
    "EX-03 Prototype 3": iconconfig['ProfilePictures']['EX-03 Prototype 3'],
    "EX-16 Prototype 16": iconconfig['ProfilePictures']['EX-16 Prototype 16'],
    "EX-00 Prototype X": iconconfig['ProfilePictures']['EX-00 Prototype X'],
    "CE-27 Ground Breaker": iconconfig['ProfilePictures']['CE-27 Ground Breaker'],
    "CE-07 Demolition Specialist": iconconfig['ProfilePictures']['CE-07 Demolition Specialist'],
    "FS-55 Devastator": iconconfig['ProfilePictures']['FS-55 Devastator'],
    "CM-10 Clinician": iconconfig['ProfilePictures']['CM-10 Clinician'],
    "FS-37 Ravager": iconconfig['ProfilePictures']['FS-37 Ravager'],
    "CW-9 White Wolf": iconconfig['ProfilePictures']['CW-9 White Wolf'],
    "CE-64 Grenadier": iconconfig['ProfilePictures']['CE-64 Grenadier'],
    "CW-36 Winter Warrior": iconconfig['ProfilePictures']['CW-36 Winter Warrior'],
    "CW-22 Kodiak": iconconfig['ProfilePictures']['CW-22 Kodiak'],
    "CW-4 Arctic Ranger": iconconfig['ProfilePictures']['CW-4 Arctic Ranger'],
    "PH-56 Jaguar": iconconfig['ProfilePictures']['PH-56 Jaguar'],
    "CE-101 Guerilla Gorilla": iconconfig['ProfilePictures']['CE-101 Guerilla Gorilla'],
    "PH-9 Predator": iconconfig['ProfilePictures']['PH-9 Predator'],
    "PH-202 Twigsnapper": iconconfig['ProfilePictures']['PH-202 Twigsnapper'],
    "TR-40 Gold Eagle": iconconfig['ProfilePictures']['TR-40 Gold Eagle'],
    "I-44 Salamander": iconconfig['ProfilePictures']['I-44 Salamander'],
    "I-92 Fire Fighter": iconconfig['ProfilePictures']['I-92 Fire Fighter'],
    "I-09 Heatseeker": iconconfig['ProfilePictures']['I-09 Heatseeker'],
    "I-102 Draconaught": iconconfig['ProfilePictures']['I-102 Draconaught'],
    "AF-52 Lockdown": iconconfig['ProfilePictures']['AF-52 Lockdown'],
    "AF-91 Field Chemist": iconconfig['ProfilePictures']['AF-91 Field Chemist'],
    "AF-50 Noxious Ranger": iconconfig['ProfilePictures']['AF-50 Noxious Ranger'],
    "AF-02 Haz-Master": iconconfig['ProfilePictures']['AF-02 Haz-Master'],
    "DP-00 Tactical": iconconfig['ProfilePictures']['DP-00 Tactical'],
    "UF-84 Doubt Killer": iconconfig['ProfilePictures']['UF-84 Doubt Killer'],
    "UF-50 Bloodhound": iconconfig['ProfilePictures']['UF-50 Bloodhound'],
    "UF-16 Inspector": iconconfig['ProfilePictures']['UF-16 Inspector'],
    "SR-64 Cinderblock": iconconfig['ProfilePictures']['SR-64 Cinderblock'],
    "SR-24 Street Scout": iconconfig['ProfilePictures']['SR-24 Street Scout'],
    "SR-18 Roadblock": iconconfig['ProfilePictures']['SR-18 Roadblock'],
    "AC-1 Dutiful": iconconfig['ProfilePictures']['AC-1 Dutiful'],
    "AC-2 Obedient": iconconfig['ProfilePictures']['AC-2 Obedient'],
    "IE-57 Hell-Bent": iconconfig['ProfilePictures']['IE-57 Hell-Bent'],
    "IE-3 Martyr": iconconfig['ProfilePictures']['IE-3 Martyr'], 
    "IE-12 Righteous": iconconfig['ProfilePictures']['IE-12 Righteous'],
    "B-22 Model Citizen": iconconfig['ProfilePictures']['B-22 Model Citizen'],
    "GS-11 Democracy's Deputy": iconconfig['ProfilePictures']['GS-11 Democracy\'s Deputy'],
    "GS-17 Frontier Marshal": iconconfig['ProfilePictures']['GS-17 Frontier Marshal'],
    "GS-66 Lawmaker": iconconfig['ProfilePictures']['GS-66 Lawmaker'],
    "RE-824 Bearer of the Standard": iconconfig['ProfilePictures']['RE-824 Bearer of the Standard'],
    "RE-2310 Honorary Guard": iconconfig['ProfilePictures']['RE-2310 Honorary Guard'],
    "RE-1861 Parade Commander": iconconfig['ProfilePictures']['RE-1861 Parade Commander'],
    "BP-20 Corrections Officer": iconconfig['ProfilePictures']['BP-20 Corrections Officer'],
    "BP-32 Jackboot": iconconfig['ProfilePictures']['BP-32 Jackboot'],
    "BP-77 Grand Juror": iconconfig['ProfilePictures']['BP-77 Grand Juror'],
    "AD-11 Livewire": iconconfig['ProfilePictures']['AD-11 Livewire'],
    "AD-26 Bleeding Edge": iconconfig['ProfilePictures']['AD-26 Bleeding Edge'],
    "AD-49 Apollonian": iconconfig['ProfilePictures']['AD-49 Apollonian'],
    "A-9 Helljumper": iconconfig['ProfilePictures']['A-9 Helljumper'],
    "A-35 Recon": iconconfig['ProfilePictures']['A-35 Recon'],
    "DS-191 Scorpion": iconconfig['ProfilePictures']['DS-191 Scorpion'],
    "DS-42 Federation's Blade": iconconfig['ProfilePictures']['DS-42 Federation\'s Blade'],
    "DS-10 Big Game Hunter": iconconfig['ProfilePictures']['DS-10 Big Game Hunter']
}

# Biome Banners per Planet (used as embed image backgrounds)
PLANET_PROFILES = {
    "Propus": iconconfig['PlanetProfile']['Desert Dunes'],
    "Klen Dahth II": iconconfig['PlanetProfile']['Desert Dunes'],
    "Outpost 32": iconconfig['PlanetProfile']['Desert Dunes'],
    "Lastofe": iconconfig['PlanetProfile']['Desert Dunes'],
    "Diaspora X": iconconfig['PlanetProfile']['Desert Dunes'], 
    "Zagon Prime": iconconfig['PlanetProfile']['Desert Dunes'],
    "Osupsam": iconconfig['PlanetProfile']['Desert Dunes'],
    "Mastia": iconconfig['PlanetProfile']['Desert Dunes'],
    "Caramoor": iconconfig['PlanetProfile']['Desert Dunes'],
    "Heze Bay": iconconfig['PlanetProfile']['Desert Dunes'],
    "Viridia Prime": iconconfig['PlanetProfile']['Desert Dunes'],
    "Durgen": iconconfig['PlanetProfile']['Desert Dunes'],
    "Phact Bay": iconconfig['PlanetProfile']['Desert Dunes'],
    "Keid": iconconfig['PlanetProfile']['Desert Dunes'],
    "Zzaniah Prime": iconconfig['PlanetProfile']['Desert Dunes'],
    "Choohe": iconconfig['PlanetProfile']['Desert Dunes'],
    "Pilen V": iconconfig['PlanetProfile']['Scoured - Pilen V'],
    "Zea Rugosia": iconconfig['PlanetProfile']['Desert Cliffs'],
    "Myradesh": iconconfig['PlanetProfile']['Desert Cliffs'],
    "Azur Secundus": iconconfig['PlanetProfile']['Desert Cliffs'],
    "Erata Prime": iconconfig['PlanetProfile']['Desert Cliffs'],
    "Mortax Prime": iconconfig['PlanetProfile']['Desert Cliffs'],
    "Cerberus IIIc": iconconfig['PlanetProfile']['Desert Cliffs'],
    "Ustotu": iconconfig['PlanetProfile']['Desert Cliffs'],
    "Erson Sands": iconconfig['PlanetProfile']['Desert Cliffs'],
    "Canopus": iconconfig['PlanetProfile']['Desert Cliffs'],
    "Hydrobius": iconconfig['PlanetProfile']['Desert Cliffs'],
    "Polaris Prime": iconconfig['PlanetProfile']['Desert Cliffs'],
    "Darrowsport": iconconfig['PlanetProfile']['Acidic Badlands'],
    "Darius II": iconconfig['PlanetProfile']['Acidic Badlands'],
    "Chort Bay": iconconfig['PlanetProfile']['Acidic Badlands'],
    "Leng Secundus": iconconfig['PlanetProfile']['Acidic Badlands'],
    "Rirga Bay": iconconfig['PlanetProfile']['Acidic Badlands'],
    "Shete": iconconfig['PlanetProfile']['Acidic Badlands'],
    "Skaash": iconconfig['PlanetProfile']['Acidic Badlands'],
    "Wraith": iconconfig['PlanetProfile']['Acidic Badlands'],
    "Slif": iconconfig['PlanetProfile']['Acidic Badlands'],
    "Wilford Station": iconconfig['PlanetProfile']['Acidic Badlands'],
    "Botein": iconconfig['PlanetProfile']['Acidic Badlands'],
    "Wasat": iconconfig['PlanetProfile']['Acidic Badlands'],
    "Esker": iconconfig['PlanetProfile']['Acidic Badlands'],
    "Charbal-VII": iconconfig['PlanetProfile']['Acidic Badlands'],
    "Kraz": iconconfig['PlanetProfile']['Rocky Canyons'],
    "Hydrofall Prime": iconconfig['PlanetProfile']['Rocky Canyons'],
    "Myrium": iconconfig['PlanetProfile']['Rocky Canyons'],
    "Vernen Wells": iconconfig['PlanetProfile']['Rocky Canyons'],
    "Calypso": iconconfig['PlanetProfile']['Rocky Canyons'],
    "Achird III": iconconfig['PlanetProfile']['Rocky Canyons'],
    "Azterra": iconconfig['PlanetProfile']['Rocky Canyons'],
    "Senge 23": iconconfig['PlanetProfile']['Rocky Canyons'],
    "Emeria": iconconfig['PlanetProfile']['Rocky Canyons'],
    "Fori Prime": iconconfig['PlanetProfile']['Rocky Canyons'],
    "Mekbuda": iconconfig['PlanetProfile']['Rocky Canyons'],
    "Effluvia": iconconfig['PlanetProfile']['Rocky Canyons'],
    "Pioneer II": iconconfig['PlanetProfile']['Rocky Canyons'],
    "Castor": iconconfig['PlanetProfile']['Rocky Canyons'],
    "Prasa": iconconfig['PlanetProfile']['Rocky Canyons'],
    "Kuma": iconconfig['PlanetProfile']['Rocky Canyons'],
	"Widow's Harbor": iconconfig['PlanetProfile']['Scoured - Widow\'s Harbor'],
	"RD-4": iconconfig['PlanetProfile']['Moon'],
	"Claorell": iconconfig['PlanetProfile']['Moon'],
	"Maia": iconconfig['PlanetProfile']['Moon'],
	"Curia": iconconfig['PlanetProfile']['Moon'],
	"Sirius": iconconfig['PlanetProfile']['Moon'],
	"Rasp": iconconfig['PlanetProfile']['Moon'],
	"Terrek": iconconfig['PlanetProfile']['Moon'],
	"Dolph": iconconfig['PlanetProfile']['Moon'],
	"Fenrir III": iconconfig['PlanetProfile']['Moon'],
	"Zosma": iconconfig['PlanetProfile']['Moon'],
	"Euphoria III": iconconfig['PlanetProfile']['Moon'],
	"Primordia": iconconfig['PlanetProfile']['Volcanic Jungle'],
	"Rogue 5": iconconfig['PlanetProfile']['Volcanic Jungle'],
	"Alta V": iconconfig['PlanetProfile']['Volcanic Jungle'],
	"Mantes": iconconfig['PlanetProfile']['Volcanic Jungle'],
	"Gaellivare": iconconfig['PlanetProfile']['Volcanic Jungle'],
	"Meissa": iconconfig['PlanetProfile']['Volcanic Jungle'],
	"Spherion": iconconfig['PlanetProfile']['Volcanic Jungle'],
	"Kirrik": iconconfig['PlanetProfile']['Volcanic Jungle'],
	"Baldrick Prime": iconconfig['PlanetProfile']['Volcanic Jungle'],
	"Zegema Paradise": iconconfig['PlanetProfile']['Volcanic Jungle'],
	"Irulta": iconconfig['PlanetProfile']['Volcanic Jungle'],
	"Regnus": iconconfig['PlanetProfile']['Volcanic Jungle'],
	"Navi VII": iconconfig['PlanetProfile']['Volcanic Jungle'],
	"Oasis": iconconfig['PlanetProfile']['Volcanic Jungle'],
	"Pollux 31": iconconfig['PlanetProfile']['Volcanic Jungle'],
	"Aesir Pass": iconconfig['PlanetProfile']['Deadlands'],
	"Alderidge Cove": iconconfig['PlanetProfile']['Deadlands'],
	"Penta": iconconfig['PlanetProfile']['Deadlands'],
	"Ain-5": iconconfig['PlanetProfile']['Deadlands'],
	"Skat Bay": iconconfig['PlanetProfile']['Deadlands'],
	"Alaraph": iconconfig['PlanetProfile']['Deadlands'],
	"Veil": iconconfig['PlanetProfile']['Deadlands'],
	"Troost": iconconfig['PlanetProfile']['Deadlands'],
	"Haka": iconconfig['PlanetProfile']['Deadlands'],
	"Nivel 43": iconconfig['PlanetProfile']['Deadlands'],
	"Pandion-XXIV": iconconfig['PlanetProfile']['Deadlands'],
	"Cirrus": iconconfig['PlanetProfile']['Deadlands'],
	"Mort": iconconfig['PlanetProfile']['Deadlands'],
	"Iridica": iconconfig['PlanetProfile']['Ethereal Jungle'],
	"Seyshel Beach": iconconfig['PlanetProfile']['Ethereal Jungle'],
	"Ursica XI": iconconfig['PlanetProfile']['Ethereal Jungle'],
	"Acubens Prime": iconconfig['PlanetProfile']['Ethereal Jungle'],
	"Fort Justice": iconconfig['PlanetProfile']['Ethereal Jungle'],
	"Sulfura": iconconfig['PlanetProfile']['Ethereal Jungle'],
	"Alamak VII": iconconfig['PlanetProfile']['Ethereal Jungle'],
	"Tibit": iconconfig['PlanetProfile']['Ethereal Jungle'],
	"Mordia 9": iconconfig['PlanetProfile']['Ethereal Jungle'],
	"Emorath": iconconfig['PlanetProfile']['Ethereal Jungle'],
	"Shallus": iconconfig['PlanetProfile']['Ethereal Jungle'],
	"Vindemitarix Prime": iconconfig['PlanetProfile']['Ethereal Jungle'],
	"Zefia": iconconfig['PlanetProfile']['Ethereal Jungle'],
	"Bekvam III": iconconfig['PlanetProfile']['Ethereal Jungle'],
	"Turing": iconconfig['PlanetProfile']['Ethereal Jungle'],
	"New Haven": iconconfig['PlanetProfile']['Scoured - New Haven'],
	"Prosperity Falls": iconconfig['PlanetProfile']['Ionic Jungle'],
	"Veld": iconconfig['PlanetProfile']['Ionic Jungle'],
	"Malevelon Creek": iconconfig['PlanetProfile']['Ionic Jungle'],
	"Siemnot": iconconfig['PlanetProfile']['Ionic Jungle'],
	"Alairt III": iconconfig['PlanetProfile']['Ionic Jungle'],
	"Merak": iconconfig['PlanetProfile']['Ionic Jungle'],
	"Gemma": iconconfig['PlanetProfile']['Ionic Jungle'],
	"Minchir": iconconfig['PlanetProfile']['Ionic Jungle'],
	"Kuper": iconconfig['PlanetProfile']['Ionic Jungle'],
	"Brink-2": iconconfig['PlanetProfile']['Ionic Jungle'],
	"Peacock": iconconfig['PlanetProfile']['Ionic Jungle'],
	"Genesis Prime": iconconfig['PlanetProfile']['Ionic Jungle'],
	"New Kiruna": iconconfig['PlanetProfile']['Icy Glaciers'],
	"Borea": iconconfig['PlanetProfile']['Icy Glaciers'],
	"Marfark": iconconfig['PlanetProfile']['Icy Glaciers'],
	"Epsilon Phoencis VI": iconconfig['PlanetProfile']['Icy Glaciers'],
	"Kelvinor": iconconfig['PlanetProfile']['Icy Glaciers'],
	"Vog-Sojoth": iconconfig['PlanetProfile']['Icy Glaciers'],
	"Alathfar XI": iconconfig['PlanetProfile']['Icy Glaciers'],
	"Okul VI": iconconfig['PlanetProfile']['Icy Glaciers'],
	"Julheim": iconconfig['PlanetProfile']['Icy Glaciers'],
	"Hadar": iconconfig['PlanetProfile']['Icy Glaciers'],
	"Mog": iconconfig['PlanetProfile']['Icy Glaciers'],
	"Vandalon IV": iconconfig['PlanetProfile']['Icy Glaciers'],
	"Arkturus": iconconfig['PlanetProfile']['Icy Glaciers'],
	"Hesoe Prime": iconconfig['PlanetProfile']['Icy Glaciers'],
	"Vega Bay": iconconfig['PlanetProfile']['Icy Glaciers'],
	"New Stockholm": iconconfig['PlanetProfile']['Icy Glaciers'],
	"Heeth": iconconfig['PlanetProfile']['Icy Glaciers'],
	"Choepessa IV": iconconfig['PlanetProfile']['Boneyard'],
	"Martyr's Bay": iconconfig['PlanetProfile']['Boneyard'],
	"Lesath": iconconfig['PlanetProfile']['Boneyard'],
	"Cyberstan": iconconfig['PlanetProfile']['Boneyard'],
	"Deneb Secundus": iconconfig['PlanetProfile']['Boneyard'],
	"Acrux IX": iconconfig['PlanetProfile']['Boneyard'],
	"Inari": iconconfig['PlanetProfile']['Boneyard'],
	"Estanu": iconconfig['PlanetProfile']['Boneyard'],
	"Stor Tha Prime": iconconfig['PlanetProfile']['Boneyard'],
	"Halies Port": iconconfig['PlanetProfile']['Boneyard'],
	"Oslo Station": iconconfig['PlanetProfile']['Boneyard'],
	"Igla": iconconfig['PlanetProfile']['Boneyard'],
	"Krakatwo": iconconfig['PlanetProfile']['Boneyard'],
	"Grafmere": iconconfig['PlanetProfile']['Boneyard'],
	"Eukoria": iconconfig['PlanetProfile']['Boneyard'],
	"Tien Kwan": iconconfig['PlanetProfile']['Boneyard'],
	"Pathfinder V": iconconfig['PlanetProfile']['Plains'],
	"Fort Union": iconconfig['PlanetProfile']['Plains'],
	"Volterra": iconconfig['PlanetProfile']['Plains'],
	"Gemstone Bluffs": iconconfig['PlanetProfile']['Plains'],
	"Acamar IV": iconconfig['PlanetProfile']['Plains'],
	"Achernar Secundus": iconconfig['PlanetProfile']['Plains'],
	"Electra Bay": iconconfig['PlanetProfile']['Plains'],
	"Afoyay Bay": iconconfig['PlanetProfile']['Plains'],
	"Matar Bay": iconconfig['PlanetProfile']['Plains'],
	"Reaf": iconconfig['PlanetProfile']['Plains'],
	"Termadon": iconconfig['PlanetProfile']['Plains'],
	"Fenmire": iconconfig['PlanetProfile']['Plains'],
	"The Weir": iconconfig['PlanetProfile']['Plains'],
	"Bellatrix": iconconfig['PlanetProfile']['Plains'],
	"Oshaune": iconconfig['PlanetProfile']['Hive World'],
	"Varylia 5": iconconfig['PlanetProfile']['Plains'],
	"Hort": iconconfig['PlanetProfile']['Plains'],
	"Draupnir": iconconfig['PlanetProfile']['Plains'],
	"Obari": iconconfig['PlanetProfile']['Plains'],
	"Mintoria": iconconfig['PlanetProfile']['Plains'],
	"Midasburg": iconconfig['PlanetProfile']['Tundra'],
	"Demiurg": iconconfig['PlanetProfile']['Tundra'],
	"Kerth Secundus": iconconfig['PlanetProfile']['Tundra'],
	"Aurora Bay": iconconfig['PlanetProfile']['Tundra'],
	"Martale": iconconfig['PlanetProfile']['Tundra'],
	"Crucible": iconconfig['PlanetProfile']['Tundra'],
	"Shelt": iconconfig['PlanetProfile']['Tundra'],
	"Trandor": iconconfig['PlanetProfile']['Tundra'],
	"Andar": iconconfig['PlanetProfile']['Tundra'],
	"Diluvia": iconconfig['PlanetProfile']['Tundra'],
	"Bunda Secundus": iconconfig['PlanetProfile']['Tundra'],
	"Ilduna Prime": iconconfig['PlanetProfile']['Tundra'],
	"Omicron": iconconfig['PlanetProfile']['Tundra'],
	"Ras Algethi": iconconfig['PlanetProfile']['Tundra'],
	"Duma Tyr": iconconfig['PlanetProfile']['Tundra'],
	"Adhara": iconconfig['PlanetProfile']['Scorched Moor'],
	"Hellmire": iconconfig['PlanetProfile']['Scorched Moor'],
	"Imber": iconconfig['PlanetProfile']['Scorched Moor'],
	"Menkent": iconconfig['PlanetProfile']['Scorched Moor'],
	"Blistica": iconconfig['PlanetProfile']['Scorched Moor'],
	"Herthon Secundus": iconconfig['PlanetProfile']['Scorched Moor'],
	"Pöpli IX": iconconfig['PlanetProfile']['Scorched Moor'],
	"Partion": iconconfig['PlanetProfile']['Scorched Moor'],
	"Wezen": iconconfig['PlanetProfile']['Scorched Moor'],
	"Marre IV": iconconfig['PlanetProfile']['Scorched Moor'],
	"Karlia": iconconfig['PlanetProfile']['Scorched Moor'],
	"Maw": iconconfig['PlanetProfile']['Scorched Moor'],
	"Kneth Port": iconconfig['PlanetProfile']['Scorched Moor'],
	"Grand Errant": iconconfig['PlanetProfile']['Scorched Moor'],
	"Fort Sanctuary": iconconfig['PlanetProfile']['Ionic Crimson'],
	"Elysian Meadows": iconconfig['PlanetProfile']['Ionic Crimson'],
	"Acrab XI": iconconfig['PlanetProfile']['Ionic Crimson'],
	"Enuliale": iconconfig['PlanetProfile']['Ionic Crimson'],
	"Liberty Ridge": iconconfig['PlanetProfile']['Ionic Crimson'],
	"Stout": iconconfig['PlanetProfile']['Ionic Crimson'],
	"Gatria": iconconfig['PlanetProfile']['Ionic Crimson'],
	"Freedom Peak": iconconfig['PlanetProfile']['Ionic Crimson'],
	"Ubanea": iconconfig['PlanetProfile']['Ionic Crimson'],
	"Valgaard": iconconfig['PlanetProfile']['Ionic Crimson'],
	"Valmox": iconconfig['PlanetProfile']['Ionic Crimson'],
	"Overgoe Prime": iconconfig['PlanetProfile']['Ionic Crimson'],
	"Providence": iconconfig['PlanetProfile']['Ionic Crimson'],
	"Kharst": iconconfig['PlanetProfile']['Ionic Crimson'],
	"Gunvald": iconconfig['PlanetProfile']['Ionic Crimson'],
	"Yed Prior": iconconfig['PlanetProfile']['Ionic Crimson'],
	"Ingmar": iconconfig['PlanetProfile']['Ionic Crimson'],
	"Crimsica": iconconfig['PlanetProfile']['Ionic Crimson'],
	"Charon Prime": iconconfig['PlanetProfile']['Ionic Crimson'],
	"Clasa": iconconfig['PlanetProfile']['Basic Swamp'],
	"Seasse": iconconfig['PlanetProfile']['Basic Swamp'],
	"Parsh": iconconfig['PlanetProfile']['Basic Swamp'],
	"East Iridium Trading Bay": iconconfig['PlanetProfile']['Basic Swamp'],
	"Gacrux": iconconfig['PlanetProfile']['Basic Swamp'],
	"Barabos": iconconfig['PlanetProfile']['Basic Swamp'],
	"Ivis": iconconfig['PlanetProfile']['Fractured Planet'],
	"Fornskogur II": iconconfig['PlanetProfile']['Basic Swamp'],
	"Nabatea Secundus": iconconfig['PlanetProfile']['Basic Swamp'],
	"Haldus": iconconfig['PlanetProfile']['Basic Swamp'],
	"Caph": iconconfig['PlanetProfile']['Basic Swamp'],
	"Bore Rock": iconconfig['PlanetProfile']['Basic Swamp'],
	"X-45": iconconfig['PlanetProfile']['Basic Swamp'],
	"Pherkad Secundus": iconconfig['PlanetProfile']['Basic Swamp'],
	"Krakabos": iconconfig['PlanetProfile']['Basic Swamp'],
	"Asperoth Prime": iconconfig['PlanetProfile']['Basic Swamp'],
	"Atrama": iconconfig['PlanetProfile']['Haunted Swamp'],
	"Setia": iconconfig['PlanetProfile']['Haunted Swamp'],
	"Tarsh": iconconfig['PlanetProfile']['Haunted Swamp'],
	"Gar Haren": iconconfig['PlanetProfile']['Haunted Swamp'],
	"Merga IV": iconconfig['PlanetProfile']['Haunted Swamp'],
	"Ratch": iconconfig['PlanetProfile']['Haunted Swamp'],
	"Bashyr": iconconfig['PlanetProfile']['Haunted Swamp'],
	"Nublaria I": iconconfig['PlanetProfile']['Haunted Swamp'],
	"Solghast": iconconfig['PlanetProfile']['Haunted Swamp'],
	"Iro": iconconfig['PlanetProfile']['Haunted Swamp'],
	"Socorro III": iconconfig['PlanetProfile']['Haunted Swamp'],
	"Khandark": iconconfig['PlanetProfile']['Haunted Swamp'],
	"Klaka 5": iconconfig['PlanetProfile']['Haunted Swamp'],
	"Skitter": iconconfig['PlanetProfile']['Haunted Swamp'],
    "Angel's Venture": iconconfig['PlanetProfile']['Fractured Planet'],
    "Moradesh": iconconfig['PlanetProfile']['Fractured Planet'],
    "Meridia": iconconfig['PlanetProfile']['Black Hole'],
    "Super Earth": iconconfig['PlanetProfile']['Super Earth'],
    "Mars": iconconfig['PlanetProfile']['Scoured - Mars']
}

# Helper functions to retrieve banner URLs
def get_subfaction_banner(subfaction: str) -> str:
    """Return subfaction banner URL from config."""
    return SUBFACTION_BANNERS.get(subfaction, "")

def get_helldiver_banner(helldiver_key: str) -> str:
    """Return helldiver banner URL from config."""
    return HELLDIVER_BANNERS.get(helldiver_key, "")