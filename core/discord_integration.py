"""Discord integration helpers: webhook sending and Rich Presence (RPC).

These functions are written to avoid importing `main` to prevent circular
imports. They accept the application instance (`app`) and any module-level
constants they need as parameters.
"""
import threading
import time
import logging
import json
import os
import random
from datetime import datetime
from typing import Dict

import requests
import pandas as pd
import configparser

from core.runtime_paths import app_path
from core.icon import (
    ENEMY_ICONS,
    DIFFICULTY_ICONS,
    SYSTEM_COLORS,
    PLANET_ICONS,
    CAMPAIGN_ICONS,
    MISSION_ICONS,
    BIOME_BANNERS,
    SUBFACTION_ICONS,
    HVT_ICONS,
    DSS_ICONS,
    TITLE_ICONS,
    PROFILE_PICTURES,
    get_subfaction_banner,
    get_helldiver_banner,
    get_badge_icons,
)

# Load config
iconconfig = configparser.ConfigParser()
from core.runtime_paths import app_path
# Try to load from the standard location first, then orphan as fallback
iconconfig.read(app_path('icon.config'))
try:
    orphan_icon_conf = app_path('orphan', 'icon.config')
    if os.path.exists(orphan_icon_conf):
        iconconfig.read(orphan_icon_conf)
except Exception:
    pass

def _get_enemy_icon(enemy_type: str) -> str:
    return ENEMY_ICONS.get(enemy_type, "NaN")


def _get_difficulty_icon(difficulty: str) -> str:
    return DIFFICULTY_ICONS.get(difficulty, "NaN")


def _get_planet_icon(planet: str) -> str:
    return PLANET_ICONS.get(planet, "")


def _get_system_color(enemy_type: str) -> int:
    try:
        return int(SYSTEM_COLORS.get(enemy_type, "0"))
    except Exception:
        return 0


def _get_campaign_icon(mission_category: str) -> str:
    return CAMPAIGN_ICONS.get(mission_category, "")


def _get_mission_icon(mission_type: str) -> str:
    return MISSION_ICONS.get(mission_type, "")


def _get_biome_banner(planet: str) -> str:
    return BIOME_BANNERS.get(planet, "")


def _get_dss_icon(dss_modifier: str) -> str:
    return DSS_ICONS.get(dss_modifier, "")


def _get_title_icon(title: str) -> str:
    return TITLE_ICONS.get(title, "")


def _get_profile_picture(profile_picture: str) -> str:
    return PROFILE_PICTURES.get(profile_picture, "")


def setup_discord_rpc(app, discord_client_id: str) -> None:
    """Initialize Discord Rich Presence in a background thread.

    Args:
        app: The MissionLogGUI instance.
        discord_client_id: The DISCORD_CLIENT_ID value (string or numeric string).
    """
    def init_rpc():
        try:
            app_id_int = int(discord_client_id)
            # import locally to avoid top-level dependency if not available
            import discordrpc

            app.RPC = discordrpc.RPC(app_id=app_id_int)
            threading.Thread(target=app.RPC.run, daemon=True).start()
            app.last_rpc_update = time.time()
            logging.info("Discord Rich Presence (discordrpc) initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize Discord Rich Presence: {e}")
            app.RPC = None
            app.last_rpc_update = 0

    threading.Thread(target=init_rpc, daemon=True).start()


def update_discord_presence(app, rpc_update_interval: int) -> None:
    """Update Discord Rich Presence using the app.RPC object.

    This function mirrors the logic previously embedded in the GUI class but
    operates purely against the passed-in `app` instance.
    """
    if not hasattr(app, 'RPC') or app.RPC is None:
        return

    current_time = time.time()
    if app.last_rpc_update != 0 and current_time - app.last_rpc_update < rpc_update_interval:
        return

    try:
        helldiver = getattr(app, 'helldiver_default', None) or "Unknown Helldiver"
        sector = app.sector.get() or "No Sector"
        planet = app.planet.get() or "No Planet"
        enemytype = app.enemy_type.get() or "Unknown Enemy"
        level = app.level.get() or 0
        title = app.title.get() or "No Title"

        enemy_assets = {
            "Automatons": "bots",
            "Terminids": "bugs",
            "Illuminate": "squids",
            "Observing": "obs"
        }
        small_image = enemy_assets.get(enemytype, "unknown")

        logging.info(f"Updating Discord RPC: enemytype={enemytype}, small_image={small_image}")

        if enemytype == "Observing":
            small_text = "Observing"
            act_type = 3
            logging.info("set_activity params: Observing presence")
            if app.RPC is not None:
                app.RPC.set_activity(
                    state=f"On sector: {sector} | Planet: {planet}",
                    details=f"Helldiver: {helldiver} Level: {level} | {title}",
                    large_image="test",
                    large_text="Helldivers 2",
                    small_image=small_image,
                    small_text=small_text,
                    act_type=act_type,
                )
                app.last_rpc_update = current_time
            else:
                logging.warning("Discord RPC object is not initialized.")
        else:
            small_text = f"Fighting: {enemytype}"
            rpcplanet = planet.replace("ö", "o").replace("-", "_").replace("'", "")
            buttons = [
                {"label": "View Galactic War", "url": "https://helldiverscompanion.com/#map"},
                {"label": "More Info", "url": f"https://helldiverscompanion.com/#hellpad/planets/{rpcplanet.replace(' ', '_')}"}
            ]
            logging.info(f"set_activity params: state=On sector: {sector} | Planet: {planet}, details=Helldiver: {helldiver} Level: {level} | {title}, small_image={small_image}, small_text={small_text}, buttons={buttons}")
            if app.RPC is not None:
                app.RPC.set_activity(
                    state=f"On sector: {sector} | Planet: {planet}",
                    details=f"Helldiver: {helldiver} Level: {level} | {title}",
                    large_image="test",
                    large_text="Helldivers 2",
                    small_image=small_image,
                    small_text=small_text,
                    buttons=buttons,
                )
                app.last_rpc_update = current_time
            else:
                logging.warning("Discord RPC object is not initialized.")
    except Exception as e:
        logging.error(f"Failed to update Discord Rich Presence: {e}")


def send_to_discord(app, data: Dict, excel_file: str, debug: bool, date_format: str, version: str, dev_release: str) -> bool:
    """Send the nicely formatted embed to configured Discord webhooks.

    This function re-implements the webhook payload creation and posting logic
    that previously lived in the GUI class.
    """
    try:
        # Use the module-level iconconfig that was already loaded
        # (no need to reload it here, just use the global one)
        GoldStar = iconconfig['Stars'].get('GoldStar', '') if 'Stars' in iconconfig else ''
        GreyStar = iconconfig['Stars'].get('GreyStar', '') if 'Stars' in iconconfig else ''

        rating_stars = {
            "Outstanding Patriotism": 5,
            "Gallantry Beyond Measure": 5,
            "Superior Valour": 4,
            "Costly Failure": 4,
            "Honourable Duty": 3,
            "Unremarkable Performance": 2,
            "Disappointing Service": 1,
            "Disgraceful Conduct": 0
        }

        SEIco = iconconfig['MiscIcon'].get('Super Earth Icon', '') if 'MiscIcon' in iconconfig else ''

        gold_count = rating_stars.get(app.rating.get(), 0)
        Stars = GoldStar * gold_count + GreyStar * (5 - gold_count)
        date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        enemy_icon = _get_enemy_icon(data['Enemy Type'])
        planet_icon = _get_planet_icon(data['Planet'])
        if planet_icon == '':
            planet_icon = f"{SEIco}"
        system_color = _get_system_color(data['Enemy Type'])
        diff_icon = _get_difficulty_icon(data['Difficulty'])
        subfaction_icon = SUBFACTION_ICONS.get(data['Enemy Subfaction'], '')
        hvt_icon = HVT_ICONS.get(data['Enemy HVT'], '')
        campaign_icon = _get_campaign_icon(data['Mission Category'])
        if data['Mission Type'] == "Blitz: Search and Destroy" and data['Enemy Type'] == "Automatons":
            mission_icon = _get_mission_icon("PLACEHOLDER")
        else:
            mission_icon = _get_mission_icon(data['Mission Type'])

        # Load banner preference from settings and set appropriate banner
        try:
            with open(app.settings_file, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
            banner_preference = settings_data.get('banner', 'Biome Banner')
        except Exception:
            banner_preference = 'Biome Banner'

        if banner_preference == 'Biome Banner':
            banner = _get_biome_banner(data['Planet'])
        elif banner_preference == 'Subfaction Banner':
            subfaction = data['Enemy Subfaction'] or "Unknown"
            banner = get_subfaction_banner(subfaction) or _get_biome_banner(data['Planet'])
        elif banner_preference == 'Helldiver Banner':
            helldiver_num = random.randint(1, 6)
            helldiver_key = f"Helldiver{helldiver_num}"
            banner = get_helldiver_banner(helldiver_key) or _get_biome_banner(data['Planet'])
        else:
            banner = _get_biome_banner(data['Planet'])

        dss_icon = _get_dss_icon(data['DSS Modifier'])
        title_icon = _get_title_icon(data['Title'])
        profile_picture = _get_profile_picture(app.profile_picture.get())

        # Get badge icons using centralized function
        app_data_path = os.path.dirname(excel_file) if excel_file else os.path.join(os.getenv('LOCALAPPDATA'), 'MLHD2')
        badge_data = get_badge_icons(debug, app_data_path, date_format)
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

        # Dynamic performance tracking icons (previous mission comparison)
        try:
            if os.path.exists(excel_file):
                df = pd.read_excel(excel_file)
                if len(df) < 2:
                    killico = ''
                    deathico = ''
                else:
                    last_mission = df.iloc[-2]
                    prev_kills = int(last_mission['Kills'])
                    prev_deaths = int(last_mission['Deaths'])
                    current_kills = int(data['Kills'])
                    current_deaths = int(data['Deaths'])
                    if current_kills > prev_kills:
                        killico = iconconfig['MiscIcon'].get('Positive', '') if 'MiscIcon' in iconconfig else ''
                    elif current_kills < prev_kills:
                        killico = iconconfig['MiscIcon'].get('Negative', '') if 'MiscIcon' in iconconfig else ''
                    else:
                        killico = iconconfig['MiscIcon'].get('Neutral', '') if 'MiscIcon' in iconconfig else ''
                    if current_deaths < prev_deaths:
                        deathico = iconconfig['MiscIcon'].get('PositiveDeaths', '') if 'MiscIcon' in iconconfig else ''
                    elif current_deaths > prev_deaths:
                        deathico = iconconfig['MiscIcon'].get('NegativeDeaths', '') if 'MiscIcon' in iconconfig else ''
                    else:
                        deathico = iconconfig['MiscIcon'].get('Neutral', '') if 'MiscIcon' in iconconfig else ''
            else:
                killico = ''
                deathico = ''
        except Exception as e:
            logging.error(f"Error calculating previous kills/deaths: {e}")
            killico = ''
            deathico = ''

        # Streak tracking
        try:
            helldiver_name = "Helldiver"
            streak_data = {}
            if os.path.exists(app_path('JSON', 'streak_data.json')):
                with open(app_path('JSON', 'streak_data.json'), 'r') as f:
                    streak_data = json.load(f)
            user_data = streak_data.get(helldiver_name, {'streak': 0, 'last_time': None})
            streak = 1
            streak_emoji = ''
            if user_data.get('last_time'):
                last_time = datetime.strptime(user_data['last_time'], "%Y-%m-%d %H:%M:%S")
                time_diff = datetime.now() - last_time
                if time_diff.total_seconds() <= 3600:
                    streak = user_data['streak'] + 1
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
            highest_streak = user_data.get('highest_streak', 0)
            if streak > highest_streak:
                highest_streak = streak
            streak_data[helldiver_name] = {
                'streak': streak,
                'highest_streak': highest_streak,
                'last_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'profile_picture_name': profile_picture
            }
            with open(app_path('JSON', 'streak_data.json'), 'w') as f:
                json.dump(streak_data, f, indent=4)
        except Exception as e:
            logging.error(f"Error managing streak data: {e}")

        total_missions_main = 0
        try:
            if os.path.exists(excel_file):
                df = pd.read_excel(excel_file)
                total_missions_main = len(df)
        except Exception:
            total_missions_main = 0

        try:
            with open(app_path('JSON', 'DCord.json'), 'r') as f:
                settings_data = json.load(f)
                UID = settings_data.get('discord_uid', '0')
        except Exception:
            UID = '0'

        try:
            with open(app_path('JSON', 'DCord.json'), 'r') as f:
                settings_data = json.load(f)
                Platform = settings_data.get('platform', "Not Selected")
        except Exception:
            Platform = "Not Selected"

        MICo = str(data.get("Major Order")) + " " + (iconconfig['MiscIcon'].get('MO', '') if 'MiscIcon' in iconconfig else '') if data.get("Major Order") else str(data.get("Major Order"))
        DSSIco = str(data.get("DSS Active")) + " " + (iconconfig['MiscIcon'].get('DSS', '') if 'MiscIcon' in iconconfig else '') if data.get("DSS Active") else str(data.get("DSS Active"))
        FlairLeftIco = iconconfig['MiscIcon'].get('Flair Left', '') if 'MiscIcon' in iconconfig else ''
        FlairRightIco = iconconfig['MiscIcon'].get('Flair Right', '') if 'MiscIcon' in iconconfig else ''

        message_content = {
            "content": None,
            "embeds": [{
                "title": f"{data.get('Super Destroyer')}\nDeployed {data.get('Helldivers')}\n{bicon}{ticon}{yearico}{PIco}{bsuperearth}{bcyberstan}{bmaleveloncreek}{bcalypso}{bpopliix}{bseyshelbeach}{boshaune}",
                "description": f"**Level {data.get('Level')} | {data.get('Title')} {title_icon}\nMission: {total_missions_main}**\n\n{FlairLeftIco} {SEIco} **Galactic Intel** {planet_icon} {FlairRightIco}\n> Sector: {data.get('Sector')}\n> Planet: {data.get('Planet')}\n> Mega City: {data.get('Mega City')}\n> Major Order: {MICo}\n> DSS Active: {DSSIco}\n> DSS Modifier: {data.get('DSS Modifier')} {dss_icon}\n\n",
                "color": system_color,
                "fields": [{
                    "name": f"{FlairLeftIco} {enemy_icon} **Enemy Intel** {subfaction_icon} {FlairRightIco}",
                    "value": f"> Faction: {data.get('Enemy Type')}\n> Subfaction: {data.get('Enemy Subfaction')}\n" +
                    (f"> High-Value Target: {data.get('Enemy HVT')} {hvt_icon}\n" if data.get('Enemy HVT') != "No HVTs" else "") +
                    f"> Campaign: {data.get('Mission Category')}\n\n{FlairLeftIco} {campaign_icon} **Mission Intel** {mission_icon} {FlairRightIco}\n> Mission: {data.get('Mission Type')}\n> Difficulty: {data.get('Difficulty')} {diff_icon}\n> Kills: {data.get('Kills')} {killico}\n> Deaths: {data.get('Deaths')} {deathico}\n> KDR: {(int(data.get('Kills')) / max(1, int(data.get('Deaths')))):.2f}\n> Rating: {data.get('Rating')}\n\n {Stars}\n"
                }],
                "author": {
                    "name": f"Super Earth Mission Report\nDate: {date}",
                    "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356001307596427564/NwNzS9B.png?ex=67eafa21&is=67e9a8a1&hm=7e204265cbcdeaf96d7b244cd63992c4ef10dc18befbcf2ed39c3a269af14ec0&"
                },
                "footer": {
                    "text": f"{streak_emoji}\n{UID}     v{version}{dev_release}",
                    "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356025859319926784/5cwgI15.png?ex=67eb10fe&is=67e9bf7e&hm=ab6326a9da1e76125238bf3668acac8ad1e43b24947fc6d878d7b94c8a60ab28&"
                },
                "image": {"url": f"{banner}"},
                "thumbnail": {"url": f"{profile_picture}"},
            }],
            "attachments": []
        }

        if debug:
            ACTIVE_WEBHOOK = [configparser.ConfigParser().read_dict({}).get('Webhooks', {}).get('TEST', '')] if False else []
            # Keep behavior simple in debug: allow main to pass a suitable webhook list if needed
            ACTIVE_WEBHOOK = []
        else:
            with open(app_path('JSON', 'DCord.json'), 'r') as f:
                dcord_data = json.load(f)
                ACTIVE_WEBHOOK = dcord_data.get('discord_webhooks_logging', [])
                ACTIVE_WEBHOOK = [
                    (w.get('url') if isinstance(w, dict) else str(w)).strip()
                    for w in ACTIVE_WEBHOOK
                    if (isinstance(w, dict) and str(w.get('url','')).strip()) or (isinstance(w, str) and w.strip())
                ]

        successes = []
        for url in ACTIVE_WEBHOOK:
            try:
                response = requests.post(url, json=message_content)
                if response.status_code == 204:
                    logging.info(f"Successfully sent to Discord webhook: {url}")
                    successes.append(True)
                else:
                    logging.error(f"Failed to send to Discord webhook {url}. Status code: {response.status_code}")
                    try:
                        app._show_error(f"Failed to send to Discord (Status: {response.status_code})")
                    except Exception:
                        pass
                    successes.append(False)
            except requests.RequestException as e:
                logging.error(f"Network error sending to Discord webhook {url}: {e}")
                try:
                    app._show_error(f"Failed to connect to Discord webhook")
                except Exception:
                    pass
                successes.append(False)
            except Exception as e:
                logging.error(f"Unexpected error sending to Discord webhook {url}: {e}")
                try:
                    app._show_error("An unexpected error occurred while sending to Discord")
                except Exception:
                    pass
                successes.append(False)

        return any(successes) if successes else False
    except Exception as e:
        logging.error(f"Error preparing Discord message: {e}")
        try:
            app._show_error("Error preparing Discord message")
        except Exception:
            pass
        return False
