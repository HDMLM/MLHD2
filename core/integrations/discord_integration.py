"""Discord integration helpers: webhook sending and Rich Presence (RPC).

These functions are written to avoid importing `main` to prevent circular
imports. They accept the application instance (`app`) and any module-level
constants they need as parameters.
"""

import configparser
import json
import logging
import os
import random
import threading
import time
from datetime import datetime
from typing import Dict

import pandas as pd

from core.transform.embed import sanitize_embed
from core.icon import (
    BIOME_BANNERS,
    CAMPAIGN_ICONS,
    DIFFICULTY_ICONS,
    DSS_ICONS,
    ENEMY_ICONS,
    HVT_ICONS,
    MISSION_ICONS,
    PROFILE_PICTURES,
    SUBFACTION_ICONS,
    SYSTEM_COLORS,
    TITLE_ICONS,
    get_badge_icons,
    get_helldiver_banner,
    get_planet_image,
    get_subfaction_banner,
)
from core.infrastructure.runtime_paths import app_path
from core.integrations.webhook import append_wait_query, post_webhook
from core.config.settings_shared import get_extra_webhook_urls

# Load config
iconconfig = configparser.ConfigParser()
# Try to load from the standard location first, then orphan as fallback
iconconfig.read(app_path("icon.config"))
try:
    orphan_icon_conf = app_path("orphan", "icon.config")
    if os.path.exists(orphan_icon_conf):
        iconconfig.read(orphan_icon_conf)
except OSError:
    pass

# Flair icon dynamic selection
from core.utils import get_effective_flair


# Returns left/right flair icons based on validated flair; affects embed visuals
def get_flair_icons():
    flair_colour = get_effective_flair()
    FlairLeftIco = iconconfig["MiscIcon"].get(f"Flair Left {flair_colour}", iconconfig["MiscIcon"]["Flair Left"])
    FlairRightIco = iconconfig["MiscIcon"].get(f"Flair Right {flair_colour}", iconconfig["MiscIcon"]["Flair Right"])
    return FlairLeftIco, FlairRightIco


_sanitize_embed = sanitize_embed


# Internal: returns enemy icon URL/key; affects embed visuals
def _get_enemy_icon(enemy_type: str) -> str:
    return ENEMY_ICONS.get(enemy_type, "NaN")


# Internal: returns difficulty icon URL/key; affects embed visuals
def _get_difficulty_icon(difficulty: str) -> str:
    return DIFFICULTY_ICONS.get(difficulty, "NaN")


# Internal: returns dynamic planet icon key; affects embed visuals
def _get_planet_icon(planet: str) -> str:
    # Get fresh dynamic planet icons to ensure favourite planet icons are current
    from core.dynamic_icons import apply_dynamic_planet_icons
    from core.icon import _BASE_PLANET_ICONS

    fresh_planet_icons = apply_dynamic_planet_icons(_BASE_PLANET_ICONS)
    return fresh_planet_icons.get(planet, "")


# Internal: returns system color for enemy; affects embed color theme
def _get_system_color(enemy_type: str) -> int:
    try:
        return int(SYSTEM_COLORS.get(enemy_type, "0"))
    except (TypeError, ValueError):
        return 0


# Internal: returns campaign icon key; affects embed visuals
def _get_campaign_icon(mission_category: str) -> str:
    return CAMPAIGN_ICONS.get(mission_category, "")


# Internal: returns mission icon key; affects embed visuals
def _get_mission_icon(mission_type: str) -> str:
    return MISSION_ICONS.get(mission_type, "")


# Internal: returns biome banner key; affects embed banner
def _get_biome_banner(planet: str) -> str:
    return BIOME_BANNERS.get(planet, "")


# Internal: returns DSS icon key; affects embed visuals
def _get_dss_icon(dss_modifier: str) -> str:
    return DSS_ICONS.get(dss_modifier, "")


# Internal: returns title icon key; affects embed visuals
def _get_title_icon(title: str) -> str:
    return TITLE_ICONS.get(title, "")


# Internal: returns profile picture key; affects embed thumbnail
def _get_profile_picture(profile_picture: str) -> str:
    return PROFILE_PICTURES.get(profile_picture, "")


# Initializes Discord Rich Presence in background; affects RPC status display
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


# Updates Discord Rich Presence if throttle allows; affects live presence
def update_discord_presence(app, rpc_update_interval: int) -> None:
    """Update Discord Rich Presence using the app.RPC object.

    This function mirrors the logic previously embedded in the GUI class but
    operates purely against the passed-in `app` instance.
    """
    if not hasattr(app, "RPC") or app.RPC is None:
        return

    current_time = time.time()
    if app.last_rpc_update != 0 and current_time - app.last_rpc_update < rpc_update_interval:
        return

    try:
        helldiver = getattr(app, "helldiver_default", None) or "Unknown Helldiver"
        sector = app.sector.get() or "No Sector"
        planet = app.planet.get() or "No Planet"
        enemytype = app.enemy_type.get() or "Unknown Enemy"
        level = app.level.get() or 0
        title = app.title.get() or "No Title"

        enemy_assets = {"Automatons": "bots", "Terminids": "bugs", "Illuminate": "squids", "Observing": "obs"}
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
                {
                    "label": "More Info",
                    "url": f"https://helldiverscompanion.com/#hellpad/planets/{rpcplanet.replace(' ', '_')}",
                },
            ]
            logging.info(
                f"set_activity params: state=On sector: {sector} | Planet: {planet}, details=Helldiver: {helldiver} Level: {level} | {title}, small_image={small_image}, small_text={small_text}, buttons={buttons}"
            )
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


# Builds and posts the mission embed to configured webhooks; affects Discord export
def send_to_discord(
    app, data: Dict, excel_file: str, debug: bool, date_format: str, version: str, dev_release: str
) -> bool:
    """Send the nicely formatted embed to configured Discord webhooks.

    This function re-implements the webhook payload creation and posting logic
    that previously lived in the GUI class.
    """
    try:
        # Use the module-level iconconfig that was already loaded
        # (no need to reload it here, just use the global one)
        GoldStar = iconconfig["Stars"].get("GoldStar", "") if "Stars" in iconconfig else ""
        GreyStar = iconconfig["Stars"].get("GreyStar", "") if "Stars" in iconconfig else ""

        rating_stars = {
            "Gallantry Beyond Measure": 5,
            "Outstanding Patriotism": 5,
            "Truly Exceptional Heroism": 4,
            "Superior Valour": 4,
            "Costly Failure": 4,
            "Honourable Duty": 3,
            "Unremarkable Performance": 2,
            "Disappointing Service": 1,
            "Disgraceful Conduct": 0,
        }

        SEIco = iconconfig["MiscIcon"].get("Super Earth Icon", "") if "MiscIcon" in iconconfig else ""

        gold_count = rating_stars.get(app.rating.get(), 0)
        Stars = GoldStar * gold_count + GreyStar * (5 - gold_count)
        date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        enemy_icon = _get_enemy_icon(data["Enemy Type"])
        planet_icon = _get_planet_icon(data["Planet"])
        if planet_icon == "":
            planet_icon = f"{SEIco}"
        system_color = _get_system_color(data["Enemy Type"])
        diff_icon = _get_difficulty_icon(data["Difficulty"])
        subfaction_icon = SUBFACTION_ICONS.get(data["Enemy Subfaction"], "")
        hvt_icon = HVT_ICONS.get(data["Enemy HVT"], "")
        campaign_icon = _get_campaign_icon(data["Mission Category"])
        if data["Mission Type"] == "Blitz: Search and Destroy" and data["Enemy Type"] == "Automatons":
            mission_icon = _get_mission_icon("PLACEHOLDER")
        else:
            mission_icon = _get_mission_icon(data["Mission Type"])

        # Load banner preference from settings and set appropriate banner
        try:
            with open(app.settings_file, "r", encoding="utf-8") as f:
                settings_data = json.load(f)
            banner_preference = settings_data.get("banner", "Biome Banner")
        except Exception:
            banner_preference = "Biome Banner"

        if banner_preference == "Biome Banner":
            banner = _get_biome_banner(data["Planet"])
        elif banner_preference == "Subfaction Banner":
            subfaction = data["Enemy Subfaction"] or "Unknown"
            banner = get_subfaction_banner(subfaction) or _get_biome_banner(data["Planet"])
        elif banner_preference == "Helldiver Banner":
            helldiver_num = random.randint(1, 6)
            helldiver_key = f"Helldiver{helldiver_num}"
            banner = get_helldiver_banner(helldiver_key) or _get_biome_banner(data["Planet"])
        else:
            banner = _get_biome_banner(data["Planet"])

        dss_icon = _get_dss_icon(data["DSS Modifier"])
        title_icon = _get_title_icon(data["Title"])
        profile_picture = _get_profile_picture(app.profile_picture.get())
        get_planet_image(data["Planet"])

        # Get badge icons using centralized function
        app_data_path = os.path.dirname(excel_file) if excel_file else os.path.join(os.getenv("LOCALAPPDATA"), "MLHD2")
        badge_data = get_badge_icons(debug, app_data_path, date_format)

        # Build badge string: always-on first, then up to 4 user-selected badges
        always_on_order = ["bicon", "ticon", "yearico", "PIco"]

        # Load user's badge display preference from DCord.json if available
        try:
            if os.path.exists(app_path("JSON", "DCord.json")):
                with open(app_path("JSON", "DCord.json"), "r", encoding="utf-8") as f:
                    dcord_data = json.load(f)
            else:
                dcord_data = {}
        except Exception:
            dcord_data = {}

        display_pref = dcord_data.get("display_badges", None)

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
        badge_string = "".join(badge_items)

        # Create named references for backwards-compatibility
        badge_data.get("bicon", "")
        badge_data.get("ticon", "")
        badge_data.get("PIco", "")
        badge_data.get("yearico", "")
        badge_data.get("bsuperearth", "")
        badge_data.get("bcyberstan", "")
        badge_data.get("bmaleveloncreek", "")
        badge_data.get("bcalypso", "")
        badge_data.get("bpopliix", "")
        badge_data.get("bseyshelbeach", "")
        badge_data.get("boshaune", "")

        # Dynamic performance tracking icons (previous mission comparison)
        try:
            if os.path.exists(excel_file):
                df = pd.read_excel(excel_file)
                if len(df) < 2:
                    killico = ""
                    deathico = ""
                else:
                    last_mission = df.iloc[-2]
                    prev_kills = int(last_mission["Kills"])
                    prev_deaths = int(last_mission["Deaths"])
                    current_kills = int(data["Kills"])
                    current_deaths = int(data["Deaths"])
                    if current_kills > prev_kills:
                        killico = iconconfig["MiscIcon"].get("Positive", "") if "MiscIcon" in iconconfig else ""
                    elif current_kills < prev_kills:
                        killico = iconconfig["MiscIcon"].get("Negative", "") if "MiscIcon" in iconconfig else ""
                    else:
                        killico = iconconfig["MiscIcon"].get("Neutral", "") if "MiscIcon" in iconconfig else ""
                    if current_deaths < prev_deaths:
                        deathico = iconconfig["MiscIcon"].get("PositiveDeaths", "") if "MiscIcon" in iconconfig else ""
                    elif current_deaths > prev_deaths:
                        deathico = iconconfig["MiscIcon"].get("NegativeDeaths", "") if "MiscIcon" in iconconfig else ""
                    else:
                        deathico = iconconfig["MiscIcon"].get("Neutral", "") if "MiscIcon" in iconconfig else ""
            else:
                killico = ""
                deathico = ""
        except Exception as e:
            logging.error(f"Error calculating previous kills/deaths: {e}")
            killico = ""
            deathico = ""

        # Streak tracking - use the streak calculated by the app_core
        try:
            helldiver_name = "Helldiver"
            streak_data = {}
            if os.path.exists(app_path("JSON", "streak_data.json")):
                with open(app_path("JSON", "streak_data.json"), "r") as f:
                    streak_data = json.load(f)
            user_data = streak_data.get(helldiver_name, {"streak": 0, "highest_streak": 0})

            # Use the streak from the mission data (already calculated correctly)
            streak = data.get("Streak", 1)
            streak_emoji = ""

            # Generate streak emoji based on streak value (only for streaks of 2 or higher)
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
            elif streak >= 2:
                streak_emoji = "🔥 x" + str(streak)
            # If streak is 1, streak_emoji remains empty (no display)

            highest_streak = user_data.get("highest_streak", 0)
            if streak > highest_streak:
                highest_streak = streak

            # Update the JSON file with the current streak and timestamp
            streak_data[helldiver_name] = {
                "streak": streak,
                "highest_streak": highest_streak,
                "last_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "profile_picture_name": profile_picture,
            }
            with open(app_path("JSON", "streak_data.json"), "w") as f:
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
            with open(app_path("JSON", "DCord.json"), "r") as f:
                settings_data = json.load(f)
                UID = settings_data.get("discord_uid", "0")
        except Exception:
            UID = "0"

        try:
            with open(app_path("JSON", "DCord.json"), "r") as f:
                settings_data = json.load(f)
                settings_data.get("platform", "Not Selected")
        except Exception:
            pass

        MICo = (
            str(data.get("Major Order"))
            + " "
            + (iconconfig["MiscIcon"].get("MO", "") if "MiscIcon" in iconconfig else "")
            if data.get("Major Order")
            else str(data.get("Major Order"))
        )
        DSSIco = (
            str(data.get("DSS Active"))
            + " "
            + (iconconfig["MiscIcon"].get("DSS", "") if "MiscIcon" in iconconfig else "")
            if data.get("DSS Active")
            else str(data.get("DSS Active"))
        )
        # Flair icons based on flair_colour
        flair_colour = data.get("flair_colour", "Default")
        if flair_colour == "Gold":
            FlairLeftIco = iconconfig["MiscIcon"].get("Gold Flair Left", "") if "MiscIcon" in iconconfig else ""
            FlairRightIco = iconconfig["MiscIcon"].get("Gold Flair Right", "") if "MiscIcon" in iconconfig else ""
        elif flair_colour == "Blue":
            FlairLeftIco = iconconfig["MiscIcon"].get("Blue Flair Left", "") if "MiscIcon" in iconconfig else ""
            FlairRightIco = iconconfig["MiscIcon"].get("Blue Flair Right", "") if "MiscIcon" in iconconfig else ""
        elif flair_colour == "Red":
            FlairLeftIco = iconconfig["MiscIcon"].get("Red Flair Left", "") if "MiscIcon" in iconconfig else ""
            FlairRightIco = iconconfig["MiscIcon"].get("Red Flair Right", "") if "MiscIcon" in iconconfig else ""
        else:
            FlairLeftIco = iconconfig["MiscIcon"].get("Flair Left", "") if "MiscIcon" in iconconfig else ""
            FlairRightIco = iconconfig["MiscIcon"].get("Flair Right", "") if "MiscIcon" in iconconfig else ""

        mega_label = "Mega Factory" if str(data.get("Planet", "")).strip().lower() == "cyberstan" else "Mega City"

        message_content = {
            "content": None,
            "embeds": [
                {
                    "title": f"{data.get('Super Destroyer')}\nDeployed {data.get('Helldivers')}\n{badge_string}",
                    "description": f"**Level {data.get('Level')} | {data.get('Title')} {title_icon}\nMission: {total_missions_main}**\n\n{FlairLeftIco} {SEIco} **Galactic Intel** {planet_icon} {FlairRightIco}\n> Sector: {data.get('Sector')}\n> Planet: {data.get('Planet')}\n> {mega_label}: {data.get('Mega Structure', data.get('Mega City'))}\n> Major Order: {MICo}\n> DSS Active: {DSSIco}\n> DSS Modifier: {data.get('DSS Modifier')} {dss_icon}\n\n",
                    "color": system_color,
                    "fields": [
                        {
                            "name": f"{FlairLeftIco} {enemy_icon} **Enemy Intel** {subfaction_icon} {FlairRightIco}",
                            "value": f"> Faction: {data.get('Enemy Type')}\n> Subfaction: {data.get('Enemy Subfaction')}\n"
                            + (
                                f"> High-Value Target: {data.get('Enemy HVT')} {hvt_icon}\n"
                                if data.get("Enemy HVT") != "No HVTs"
                                else ""
                            )
                            + f"> Campaign: {data.get('Mission Category')}\n\n{FlairLeftIco} {campaign_icon} **Mission Intel** {mission_icon} {FlairRightIco}\n> Mission: {data.get('Mission Type')}\n> Difficulty: {data.get('Difficulty')} {diff_icon}\n> Kills: {data.get('Kills')} {killico}\n> Deaths: {data.get('Deaths')} {deathico}\n> KDR: {(int(data.get('Kills')) / max(1, int(data.get('Deaths')))):.2f}\n> Rating: {data.get('Rating')}\n\n {Stars}\n",
                        }
                    ],
                    "author": {
                        "name": f"Super Earth Mission Report\nDate: {date}",
                        "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356001307596427564/NwNzS9B.png?ex=67eafa21&is=67e9a8a1&hm=7e204265cbcdeaf96d7b244cd63992c4ef10dc18befbcf2ed39c3a269af14ec0&",
                    },
                    "footer": {
                        "text": f"{streak_emoji + chr(10) if streak_emoji else ''}{UID}     v{version}{dev_release}",
                        "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356025859319926784/5cwgI15.png?ex=67eb10fe&is=67e9bf7e&hm=ab6326a9da1e76125238bf3668acac8ad1e43b24947fc6d878d7b94c8a60ab28&",
                    },
                    "image": {"url": f"{banner}"},
                    "thumbnail": {"url": f"{profile_picture}"},
                }
            ],
            "attachments": [],
        }

        # Load webhooks from the appropriate file based on debug mode
        dcord_file = app_path("JSON", "DCord-dev.json") if debug else app_path("JSON", "DCord.json")
        try:
            with open(dcord_file, "r") as f:
                dcord_data = json.load(f)
                ACTIVE_WEBHOOK = dcord_data.get("discord_webhooks_logging", [])
        except (FileNotFoundError, json.JSONDecodeError):
            # Fallback to production file if dev file doesn't exist
            try:
                with open(app_path("JSON", "DCord.json"), "r") as f:
                    dcord_data = json.load(f)
                    ACTIVE_WEBHOOK = dcord_data.get("discord_webhooks_logging", [])
            except (FileNotFoundError, json.JSONDecodeError):
                ACTIVE_WEBHOOK = []

        # Normalize webhook URLs (handle both string and dict formats)
        ACTIVE_WEBHOOK = [
            (w.get("url") if isinstance(w, dict) else str(w)).strip()
            for w in ACTIVE_WEBHOOK
            if (isinstance(w, dict) and str(w.get("url", "")).strip()) or (isinstance(w, str) and w.strip())
        ]

        extra_logging = get_extra_webhook_urls("logging")
        if extra_logging:
            ACTIVE_WEBHOOK = list(dict.fromkeys(ACTIVE_WEBHOOK + extra_logging))

        successes = []
        for url in ACTIVE_WEBHOOK:
            # Prepare a sanitized copy of the payload to avoid mutation side-effects
            payload = json.loads(json.dumps(message_content))
            if payload.get("content") is None:
                payload.pop("content", None)

            # Sanitize embeds
            if "embeds" in payload and isinstance(payload["embeds"], list) and payload["embeds"]:
                sanitized, changes = _sanitize_embed(payload["embeds"][0])
                payload["embeds"][0] = sanitized
                if changes:
                    logging.info(f"Sanitized embed before sending: {changes}")

            # If embed is now empty (no title/description/fields/etc), skip sending
            if not payload.get("embeds") or not payload["embeds"][0]:
                logging.error(f"Skipping webhook send to {url}: embed is empty after sanitization.")
                successes.append(False)
                continue

            send_url = append_wait_query(url) if debug else url

            success, response, err = post_webhook(
                send_url,
                json_payload=payload,
                timeout=20,
                retries=2,
            )

            if success:
                logging.info(
                    f"Data sent successfully to {url} (status {response.status_code if response else 'unknown'})."
                )
                successes.append(True)
            else:
                logging.error(f"Failed to send data to {url}. {err}")
                try:
                    status = response.status_code if response is not None else "network"
                    app._show_error(f"Failed to send to Discord (Status: {status})")
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
