import pandas as pd
import logging
from logging_config import setup_logging
import configparser
import requests
import json
import os
import html as html_lib
from datetime import datetime


# Read configuration from config.config
config = configparser.ConfigParser()
config.read('config.config')


#Constants
DEBUG = config.getboolean('DEBUGGING', 'DEBUG', fallback=False)
setup_logging(DEBUG)

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

# Enemy icons and colors from config
ENEMY_ICONS = {
    "Automatons": config['EnemyIcons']['Automatons'],
    "Terminids": config['EnemyIcons']['Terminids'],
    "Illuminate": config['EnemyIcons']['Illuminate'],
    "Observing": config['EnemyIcons']['Observation'],
}

# Planet Icons
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

# Campaign Icons
CAMPAIGN_ICONS = {
    "Defense": config['CampaignIcons']['Defense'],
    "Liberation": config['CampaignIcons']['Liberation'],
    "Invasion": config['CampaignIcons']['Invasion'],
    "High-Priority": config['CampaignIcons']['High-Priority'],
    "Attrition": config['CampaignIcons']['Attrition'],
    "Battle for Super Earth": config['CampaignIcons']['Battle for Super Earth'],
}

# Mission Icons
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

# Biome banners for Planets
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

# Title icons for Titles
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

# Read the Excel file
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
    with open('DCord.json', 'r') as f:
        dcord_data = json.load(f)
        ACTIVE_WEBHOOK = dcord_data.get('discord_webhooks', [])

# Get latest note
non_blank_notes = df['Note'].dropna()
latest_note = non_blank_notes.iloc[-1] if not non_blank_notes.empty else "No Quote"

# Get Instances from Data
search_mission = df['Mission Type'].mode()[0]
MissionCount = df.apply(lambda row: row.astype(str).str.contains(search_mission, case=False).sum(), axis=1).sum()
search_campaign = df['Mission Category'].mode()[0]
CampaignCount = df.apply(lambda row: row.astype(str).str.contains(search_campaign, case=False).sum(), axis=1).sum()
search_faction = df['Enemy Type'].mode()[0]
FactionCount = df.apply(lambda row: row.astype(str).str.contains(search_faction, case=False).sum(), axis=1).sum()
search_difficulty = df['Difficulty'].mode()[0]
DifficultyCount = df.apply(lambda row: row.astype(str).str.contains(search_difficulty, case=False).sum(), axis=1).sum()
search_planet = df['Planet'].mode()[0]
PlanetCount = df.apply(lambda row: row.astype(str).str.contains(search_planet, case=False).sum(), axis=1).sum()
search_sector = df['Sector'].mode()[0]
SectorCount = df.apply(lambda row: row.astype(str).str.contains(search_sector, case=False).sum(), axis=1).sum()

highest_streak = 0
profile_picture = ""
with open('streak_data.json', 'r') as f:
    streak_data = json.load(f)
    # Use "Helldiver" as the key or fall back to helldiver_ses if the first one doesn't exist
    highest_streak = streak_data.get("Helldiver", streak_data.get(helldiver_ses, {})).get("highest_streak", 0)
    profile_picture = streak_data.get("Helldiver", streak_data.get(helldiver_ses, {})).get("profile_picture_name", "")

# Load DCord.json data
with open('DCord.json', 'r') as f:
    dcord_data = json.load(f)
    
def _build_primary_embed_description() -> str:
    """Compose the primary embed description (kept modular so we can reuse in HTML)."""
    return (
        f"**Level {helldiver_level} | {helldiver_title} {TITLE_ICONS.get(df['Title'].mode()[0], '')}**\n\n"
        f"\"{latest_note}\"\n\n"
        f"<a:easyshine1:1349110651829747773>  <a:easyshine2:1349110649753698305> Combat Statistics <a:easyshine2:1349110649753698305> <a:easyshine3:1349110648528699422>\n"
        f"> Kills - {df['Kills'].sum()}\n"
        f"> Deaths - {df['Deaths'].sum()}\n"
        f"> Highest Kills in Mission - {df['Kills'].max()}\n"
        f"\n<a:easyshine1:1349110651829747773>  <a:easysuperearth:1343266082881802443> Mission Statistics <a:easysuperearth:1343266082881802443> <a:easyshine3:1349110648528699422>\n"
        f"> Deployments - {len(df)}\n"
        f"> Major Order Deployments - {df['Major Order'].astype(int).sum()}\n"
        f"> DSS Deployments - {df['DSS Active'].astype(int).sum()}\n"
        f"\n<a:easyshine1:1349110651829747773>  <a:easyskullgold:1232018045791375360> Performance Statistics <a:easyskullgold:1232018045791375360> <a:easyshine3:1349110648528699422>\n"
        f"> Rating - {Rating} | {int(Rating_Percentage)}%\n"
        f"> Highest Streak - {highest_streak} Missions\n"
        f"\n<a:easyshine1:1349110651829747773>  <:goldstar:1337818552094163034> Favourites <:goldstar:1337818552094163034> <a:easyshine3:1349110648528699422>\n"
        f"> Mission - {df['Mission Type'].mode()[0]} {MISSION_ICONS.get(df['Mission Type'].mode()[0], '')} (x{MissionCount})\n"
        f"> Campaign - {df['Mission Category'].mode()[0]} {CAMPAIGN_ICONS.get(df['Mission Category'].mode()[0], '')} (x{CampaignCount})\n"
        f"> Faction - {df['Enemy Type'].mode()[0]} {ENEMY_ICONS.get(df['Enemy Type'].mode()[0], '')} (x{FactionCount})\n"
        f"> Difficulty - {df['Difficulty'].mode()[0]} {DIFFICULTY_ICONS.get(df['Difficulty'].mode()[0], '')} (x{DifficultyCount})\n"
        f"> Planet - {df['Planet'].mode()[0]} {PLANET_ICONS.get(df['Planet'].mode()[0], '')} (x{PlanetCount})\n"
        f"> Sector - {df['Sector'].mode()[0]} (x{SectorCount})\n"
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
            "author": {"name": "SEAF Battle Record"},
            "footer": {"text": dcord_data['discord_uid'],"icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356025859319926784/5cwgI15.png?ex=67eb10fe&is=67e9bf7e&hm=ab6326a9da1e76125238bf3668acac8ad1e43b24947fc6d878d7b94c8a60ab28&"},
            "image": {"url": f"{BIOME_BANNERS.get(df['Planet'].mode()[0], '')}"},
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
        "emoji": config['EnemyIcons']['Automatons'],
        "color": int(config['SystemColors']['Automatons']),
        "url": "https://i.ibb.co/bgNp2q73/Automatons-Icon.png"
    },
    "Terminids": {
        "emoji": config['EnemyIcons']['Terminids'],
        "color": int(config['SystemColors']['Terminids']),
        "url": "https://i.ibb.co/PspGgJkH/Terminids-Icon.png"
    },
    "Illuminate": {
        "emoji": config['EnemyIcons']['Illuminate'],
        "color": int(config['SystemColors']['Illuminate']),
        "url": "https://i.ibb.co/wr4Nm5HT/Illuminate-Icon.png"
    }
}

# Planet type specific embeds with icons
planet_icons = {
    "Super Earth": {
        "emoji": config['PlanetIcons']['Human Homeworld']
    },
    "Cyberstan": {
        "emoji": config['PlanetIcons']['Automaton Homeworld']
    },
    "Malevelon Creek": {
        "emoji": config['PlanetIcons']['Malevelon Creek']
    },
    "Calypso": {
        "emoji": config['PlanetIcons']['Calypso']
    },
    "Diaspora X": {
        "emoji": config['PlanetIcons']['Gloom']
    },
    "Enuliale": {
        "emoji": config['PlanetIcons']['Gloom']
    },
    "Epsilon Phoencis VI": {
        "emoji": config['PlanetIcons']['Gloom']
    },
    "Gemstone Bluffs": {
        "emoji": config['PlanetIcons']['Gloom']
    },
    "Nabatea Secundus": {
        "emoji": config['PlanetIcons']['Gloom']
    },
    "Navi VII": {
        "emoji": config['PlanetIcons']['Gloom']
    },
    "Azur Secundus": {
        "emoji": config['PlanetIcons']['Gloom']
    },
    "Erson Sands": {
        "emoji": config['PlanetIcons']['Gloom']
    },
    "Nivel 43": {
        "emoji": config['PlanetIcons']['Gloom']
    },
    "Zagon Prime": {
        "emoji": config['PlanetIcons']['Gloom']
    },
    "Hellmire": {
        "emoji": config['PlanetIcons']['Gloom']
    },
    "Omicron": {
        "emoji": config['PlanetIcons']['Gloom']
    },
    "Oshaune": {
        "emoji": config['PlanetIcons']['Gloom']
    },
    "Fori Prime": {
        "emoji": config['PlanetIcons']['Gloom']
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
        last_date = planet_data["Time"].max() if "Time" in df.columns else "No date available"
        planets_description_parts.append(
            f"{enemy_icons.get(enemy_type, {'emoji': ''})['emoji']} **{planet}** {planet_icons.get(planet, {'emoji': ''})['emoji']}\n"
            f"> Deployments - {len(planet_data)}\n"
            f"> Major Order Deployments - {planet_data['Major Order'].astype(int).sum()}\n"
            f"> Kills - {planet_data['Kills'].sum()}\n"
            f"> Deaths - {planet_data['Deaths'].sum()}\n"
            f"> Last Deployment - {last_date}\n"
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
    with open('DCord.json', 'r') as f:
        discord_data = json.load(f)
        webhook_urls = discord_data.get('discord_webhooks', [])
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
            "title": f"{helldiver_ses}\nHelldiver: {helldiver_name}",
            "color": 7257043,
            "fields": [
                {
                    "name": f"Level {helldiver_level} | {helldiver_title} {TITLE_ICONS.get(df['Title'].mode()[0], '')}",
                    "value": "\n\nINITIAL TRANSMISSION FAILURE - CONTINGENCY PROTOCOL ACTIVATED\n\nAttention Helldiver,\n\nYour SEAF Battle Record failed to reach your terminal via our Super Earth Command database through the standard uplink procedure, whether due to xeno interference, bureaucratic lag, the amount of data attempting to upload or simple operator inadequacy is irrelevant.\n\nAs per Protocol MLHD2-E2 \"Compliance is Victory\", a SHTML fallback file has been auto-generated to ensure your mission data is preserved and viewable.\n\nReview the document locally and stand by for reclassification procedures.\n\nFor Super Earth. For Democracy. Upload Again.\n\n- Ministry of Intelligence | Automated Systems Division\nSuper Earth Uplink Command"
                }
            ],
            "author": {"name": "SEAF Contingency Report"},
            "footer": {"text": dcord_data['discord_uid'],"icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356025859319926784/5cwgI15.png?ex=67eb10fe&is=67e9bf7e&hm=ab6326a9da1e76125238bf3668acac8ad1e43b24947fc6d878d7b94c8a60ab28&"},
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
