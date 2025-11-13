# Helldiver Mission Log Manager (GUI) - Application core
#
# This module contains the core application class `MissionLogGUI` and
# supporting functions/constants previously placed in `main.py`.

import tkinter as tk
from tkinter import ttk, messagebox
import requests
from datetime import datetime, timezone, timedelta
import json
import pandas as pd
import logging
from core.logging_config import setup_logging
from typing import Dict, List, Optional
from PIL import Image, ImageTk, ImageDraw, ImageFont
import time
import configparser
from core.runtime_paths import app_path, get_install_dir
import threading
import os
import subprocess
import shutil
import random
import re
import webbrowser
import discordrpc
import sys
from core.ui_sound import (
    init_ui_sounds,
    play_button_click,
    play_button_hover,
    register_global_click_binding,
    set_ui_sounds_enabled,
)
from core.data_manager import (
    load_persistent_settings,
    save_persistent_settings,
    append_mission_to_excel,
    read_streaks,
)

# Load config
iconconfig = configparser.ConfigParser()
from core.runtime_paths import app_path
iconconfig.read(app_path('orphan', 'icon.config'))

def _verify_discordrpc():
    try:
        import logging
        path = getattr(discordrpc, "__file__", "N/A")
        logging.info(f"discordrpc loaded from: {path}")
        if not hasattr(discordrpc, "RPC"):
            try:
                import discord_rpc as alt
                logging.info(f"Also found discord_rpc at: {getattr(alt, '__file__', 'N/A')}")
            except Exception:
                pass
            raise AttributeError(f"discordrpc has no attribute RPC (module path: {path})")
    except Exception as e:
        # Surface early and clearly
        raise
_verify_discordrpc()

from tkinter import font as tkfont


# Ensure Pillow debug output is disabled before importing PIL
os.environ["PILLOW_DEBUG"] = "0"

from PIL import Image, ImageTk
from core.icon import ENEMY_ICONS, DIFFICULTY_ICONS, SYSTEM_COLORS, PLANET_ICONS, CAMPAIGN_ICONS, MISSION_ICONS, BIOME_BANNERS, SUBFACTION_ICONS,  HVT_ICONS, DSS_ICONS, TITLE_ICONS, PROFILE_PICTURES, SUBFACTION_BANNERS, HELLDIVER_BANNERS, get_subfaction_banner, get_helldiver_banner
from core.utils import (
    is_valid_numeric_value,
    clean_numeric_string,
    normalize_subfaction_name,
    normalize_hvt_name,
    get_enemy_icon as util_get_enemy_icon,
    get_planet_icon as util_get_planet_icon,
    get_system_color as util_get_system_color,
    get_difficulty_icon as util_get_difficulty_icon,
    get_campaign_icon as util_get_campaign_icon,
    get_mission_icon as util_get_mission_icon,
    get_biome_banner as util_get_biome_banner,
    get_dss_icon as util_get_dss_icon,
    get_title_icon as util_get_title_icon,
    get_profile_picture as util_get_profile_picture,
    get_subfaction_icon as util_get_subfaction_icon,
    get_hvt_icon as util_get_hvt_icon,
)
import random

# Manual Configuration
GWDay = "Day: 644"
GWDate = "Date: 13/11/2025"
VERSION = "1.7.011"
DEV_RELEASE = "-dev"
RPC_UPDATE_INTERVAL = 10  # seconds, this is in seconds
DATE_FORMAT = "%d-%m-%Y %H:%M:%S"

# Load config
config = configparser.ConfigParser()
# Prefer install-aware config paths
# Prefer install-aware config paths; also try orphan folder where the user moved configs
config.read(app_path('config.config'))
# If user moved the config into orphan/, prefer that value (app_path will check install dir then repo root)
try:
    # Try orphan explicitly first if present
    orphan_conf = app_path('orphan', 'config.config')
    if os.path.exists(orphan_conf):
        config.read(orphan_conf)
except Exception:
    pass
DISCORD_CLIENT_ID = config.get('Discord', 'DISCORD_CLIENT_ID', fallback='0')
iconconfig = configparser.ConfigParser()
iconconfig.read(app_path('icon.config'))

DEBUG = config.getboolean('DEBUGGING', 'DEBUG', fallback=False)
setup_logging(DEBUG)

# File paths
if DEBUG:
    SETTINGS_FILE = app_path('JSON', 'settings-dev.json')
    PERSISTENCE_FILE = app_path('JSON', 'persistent-dev.json')
    streak_file = app_path('JSON', 'streak_data-dev.json')
else:
    SETTINGS_FILE = app_path('JSON', 'settings.json')
    PERSISTENCE_FILE = app_path('JSON', 'persistent.json')
    streak_file = app_path('JSON', 'streak_data.json')

# Set up application data paths 
APP_DATA = os.path.join(os.getenv('LOCALAPPDATA'), 'MLHD2')
if not os.path.exists(APP_DATA):
    os.makedirs(APP_DATA)

EXCEL_FILE_PROD = os.path.join(APP_DATA, 'mission_log.xlsx')
EXCEL_FILE_TEST = os.path.join(APP_DATA, 'mission_log_test.xlsx')


# Theme System
def make_theme(bg, fg, entry_bg=None, entry_fg=None, button_bg=None, button_fg=None, frame_bg=None):
    combobox_bg = "#D3D3D3"  # light gray for dropdowns
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
            # Force combobox/dropdown boxes to a light gray regardless of entry_bg
            "background": combobox_bg,
            "foreground": entry_fg or fg,
            "fieldbackground": combobox_bg,
            "insertcolor": fg,
        }},
        "TFrame": {"configure": {"background": frame_bg or bg}},
        "TLabelframe": {"configure": {"background": frame_bg or bg, "foreground": fg}},
        "TLabelframe.Label": {"configure": {"background": frame_bg or bg, "foreground": fg}},
        "TNotebook": {"configure": {"background": bg}},
        "TNotebook.Tab": {"configure": {"background": button_bg or bg, "foreground": fg}},
    }

# Apply default theme to the GUI
DEFAULT_THEME = make_theme(
    bg="#252526",      # background color
    fg="#FFFFFF",      # foreground/text color
    entry_bg="#D3D3D3",
    entry_fg="#000000",
    button_bg="#4C4C4C",
    button_fg="#000000",
    frame_bg="#252526"
)

def apply_theme(style, theme_dict, root=None):
    # Use clam theme for full control
    try:
        style.theme_use('clam')
    except Exception:
        pass

    # Apply standard ttk styles
    for widget, opts in theme_dict.items():
        for method, cfg in opts.items():
            try:
                getattr(style, method)(widget, **cfg)
            except Exception:
                pass

    # Handle TCombobox colors (readonly state)
    combobox_cfg = theme_dict.get("TCombobox", {}).get("configure", {})
    combobox_bg = combobox_cfg.get("background", "#D3D3D3")
    style.map("TCombobox",
              fieldbackground=[("readonly", combobox_bg)],
              background=[("readonly", combobox_bg)])


    if root is not None:
        root.option_add('*TCombobox*Listbox.background', combobox_bg)
        root.option_add('*TCombobox*Listbox.foreground', combobox_cfg.get("foreground", "#000000"))


def get_enemy_icon(enemy_type: str) -> str:
    return util_get_enemy_icon(enemy_type)


def get_difficulty_icon(difficulty: str) -> str:
    return util_get_difficulty_icon(difficulty)


def get_planet_icon(planet: str) -> str:
    return util_get_planet_icon(planet)


def get_system_color(enemy_type: str) -> int:
    return util_get_system_color(enemy_type)


def get_campaign_icon(mission_category: str) -> str:
    return util_get_campaign_icon(mission_category)


def get_mission_icon(mission_type: str) -> str:
    return util_get_mission_icon(mission_type)


def get_biome_banner(planet: str) -> str:
    return util_get_biome_banner(planet)


def get_dss_icon(dss_modifier: str) -> str:
    return util_get_dss_icon(dss_modifier)


def get_title_icon(title: str) -> str:
    return util_get_title_icon(title)


def get_profile_picture(profile_picture: str) -> str:
    return util_get_profile_picture(profile_picture)

def normalize_subfaction_name(subfaction: str) -> str:
    # Normalize subfaction name. - A: is this even used rn?
    normalized = " ".join(subfaction.split()).title()
    replacements = {
        "Jet Brigade": "JetBrigade",
        "Predator Strain": "PredatorStrain",
        "Incineration Corps": "IncinerationCorps",
        "Jet Brigade & Incineration Corps": "JetBrigadeIncinerationCorps",
        "Spore Burst Strain": "SporeBurstStrain",
        "The Great Host": "TheGreatHost",
        "Rupture Strain": "RuptureStrain",
        "Dragonroach": "Dragonroach",
        "Predator Strain & Dragonroach": "PredatorStrainDragonroach",
        "Spore Burst Strain & Dragonroach": "SporeBurstStrainDragonroach",
        "Rupture Strain & Dragonroach": "RuptureStrainDragonroach"
    }
    return replacements.get(normalized, normalized)

def normalize_hvt_name(hvt: str) -> str:
    normalized = " ".join(hvt.split()).title()
    replacements = {
        "Hive Lords": "HiveLords"
    }
    return replacements.get(normalized, normalized)

def get_subfaction_icon(subfaction_type: str) -> str:
    # Return subfaction icon (empty if missing).
    icon = SUBFACTION_ICONS.get(subfaction_type, "NaN")
    logging.info(f"Getting subfaction icon for '{subfaction_type}', found: {icon}")
    if icon == "NaN":
        icon = ""
    return icon

def get_hvt_icon(hvt_type: str) -> str:
    # Return HVT icon (empty if missing).
    icon = HVT_ICONS.get(normalize_hvt_name(hvt_type), "NaN")
    logging.info(f"Getting HVT icon for '{hvt_type}', found: {icon}")
    if icon == "NaN":
        icon = ""
    return icon

def total_missions():
    excel_file = EXCEL_FILE_TEST if DEBUG else EXCEL_FILE_PROD  # <-- FIXED
    try:
        df = pd.read_excel(excel_file)
        total_rows = len(df)
        return total_rows
    except Exception as e:
        logging.error(f"Error reading Excel file for total missions: {e}")
        return 0  # Return 0 if file doesn't exist yet

class MissionLogGUI:
    def _install_click_sound(self) -> None:
        """Bind a global handler to play a click sound for primary button releases.

        We attach to <ButtonRelease-1> at the root level so that all current and future
        widgets automatically trigger the sound. We skip very high‑frequency widgets
        (like the Text note box while selecting) by basic widget class filtering.
        """
        try:
            # Guard so we don't bind multiple times (Tkinter can duplicate events otherwise)
            if getattr(self, '_click_sound_installed', False):
                return

            def _maybe_play(event):
                try:
                    w = event.widget
                    # Avoid spamming from Text dragging/selecting or frames
                    skip_classes = {tk.Text, ttk.Frame}
                    if any(isinstance(w, c) for c in skip_classes):
                        return
                    play_button_click()
                except Exception:
                    pass

            self.root.bind_all('<ButtonRelease-1>', _maybe_play, add=True)
            self._click_sound_installed = True
        except Exception as e:
            logging.debug(f"Failed installing click sound binding: {e}")
    def update_submit_button_image(self, status: str) -> None:
        """
        Updates the submission button image depending on status.
        Args:
            status (str): 'Passed' or 'Fail'.
        """
        try:
            if status == "Passed":
                img = self.submit_img_yes
            elif status == "Fail":
                img = self.submit_img_no
            else:
                img = self.submit_img_default
            if hasattr(self, 'submit_label'):
                self.submit_label.configure(image=img)
                self.submit_label.image = img  # Prevent garbage collection
                self._submit_img_state = img
                # After 4 seconds, reset to default
                if status in ("Passed", "Fail"):
                    self.root.after(4000, lambda: self._reset_submit_button_image())
        except Exception as e:
            logging.error(f"Failed to update submit button image: {e}")

    def _reset_submit_button_image(self):
        """Reset button image to appropriate default based on current faction."""
        if hasattr(self, 'submit_label'):
            # Check current faction to determine correct default button
            if hasattr(self, 'enemy_type') and self.enemy_type.get() == "Observing":
                # Reset to observe button if faction is still Observing
                self.submit_label.configure(image=self.observe_img_default)
                self.submit_label.image = self.observe_img_default
                self._submit_img_state = self.observe_img_default
            else:
                # Reset to submit button for other factions
                self.submit_label.configure(image=self.submit_img_default)
                self.submit_label.image = self.submit_img_default
                self._submit_img_state = self.submit_img_default
            self._submit_img_state = self.submit_img_default

        # Safely bind tooltip handlers to the submit label if it exists.
        widget = getattr(self, 'submit_label', None)
        if widget is not None:
            def leave(event):
                if hasattr(widget, 'tooltip'):
                    try:
                        widget.tooltip.destroy()
                    except Exception:
                        pass
                    try:
                        delattr(widget, 'tooltip')
                    except Exception:
                        pass

            def motion(event):
                if hasattr(widget, 'tooltip'):
                    try:
                        widget.tooltip.geometry(f"+{event.x_root+15}+{event.y_root+10}")
                    except Exception:
                        pass

            def enter(event):
                # No-op enter handler kept for parity with original behavior
                return

            try:
                widget.bind("<Leave>", leave)
                widget.bind("<Motion>", motion)
                widget.bind("<Enter>", enter)
            except Exception:
                pass


    def __init__(self, *args, **kwargs):
        # Initialize the GUI application.
        try:
            init_ui_sounds(preload=True)
        except Exception:
            pass
        
        # root is passed as first positional argument by the caller
        self.root = args[0] if args else kwargs.get('root')

        # Ensure selected text is readable: default selection foreground to black
        try:
            # Generic selection foreground
            self.root.option_add('*SelectionForeground', 'black')
            # Per-widget class defaults
            self.root.option_add('*Entry.selectForeground', 'black')
            self.root.option_add('*Text.selectForeground', 'black')
            self.root.option_add('*Listbox.selectForeground', 'black')
            # Combobox listbox entries used by ttk are handled by apply_theme already,
            # but set a fallback for the listbox widget used in dropdowns.
            self.root.option_add('*TCombobox*Listbox.selectForeground', 'black')
        except Exception:
            pass

        style = ttk.Style()
        apply_theme(style, DEFAULT_THEME, self.root)
        # expose some module-level globals to the instance so the extracted UI
        # builder can reference them without importing main (avoids circular imports)
        self.GWDate = GWDate
        self.GWDay = GWDay
        # Install global click sound bindings early so newly created widgets are covered
        try:
            self._install_click_sound()
        except Exception as e:
            logging.debug(f"Failed to install global click sound binding: {e}")
        if not os.path.exists(EXCEL_FILE_PROD):
            columns = [
                'Super Destroyer', 'Helldivers', 'Level', 'Title', 'Sector', 'Planet', 'Mega City',
                'Enemy Type', 'Enemy Subfaction', 'Enemy HVT', 'Major Order', 'DSS Active', 'DSS Modifier',
                'Mission Category', 'Mission Type', 'Difficulty', 'Kills', 'Deaths', 'Rating', 'Time', 'Streak', 'Note'
            ]
            df = pd.DataFrame(columns=columns)
            df.to_excel(EXCEL_FILE_PROD, index=False)
        if DEBUG:
            self.root.title("Helldiver Mission Log Manager v-{} DEBUG:{}".format(VERSION, DEBUG))
        else:
            self.root.title("Helldiver Mission Log Manager v-{}".format(VERSION))
        self.root.resizable(False, False)
        self.RPC = None
        self.last_rpc_update = 0
        def load_icon():
            try:
                pil_icon = Image.open(app_path('orphan', 'SuperEarth.png')).convert('RGBA')
                bg_color = (37, 37, 38, 255)  # #252526
                background = Image.new('RGBA', pil_icon.size, bg_color)
                pil_icon = Image.alpha_composite(background, pil_icon)
                icon = ImageTk.PhotoImage(pil_icon)
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
        self.root.after(200, self._initialize_dynamic_icons)
        self.root.after(2000, self._periodic_rpc_update)
        # Save settings on window close
        try:
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        except Exception as e:
            logging.error(f"Failed to bind WM_DELETE_WINDOW handler: {e}")

    def _initialize_dynamic_icons(self) -> None:
        """Initialize the dynamic icons cache on application startup"""
        try:
            from core.dynamic_icons import initialize_dynamic_icons_cache
            initialize_dynamic_icons_cache()
            logging.info("Dynamic icons cache initialized on startup")
        except Exception as e:
            logging.warning(f"Failed to initialize dynamic icons cache: {e}")

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
        self.hvt_type = tk.StringVar()
        self.Helldivers = tk.StringVar()
        self.mission_category = tk.StringVar()
        self.rating = tk.StringVar(value="Outstanding Patriotism")
        self.level = tk.IntVar()
        self.title = tk.StringVar()
        self.difficulty = tk.StringVar()
        self.MO = tk.BooleanVar()
        self.DSS = tk.BooleanVar()
        self.DSSMod = tk.StringVar()
        self.note = tk.StringVar()
        self.shipName1 = tk.StringVar()
        self.shipName2 = tk.StringVar()
        self.FullShipName = tk.StringVar()
        self.profile_picture = tk.StringVar()
        self.streak = tk.IntVar()

        validate_cmd = self.root.register(self._validate_numeric_input)
        self.kills.trace_add("write", lambda *args: self._validate_field(self.kills))
        self.deaths.trace_add("write", lambda *args: self._validate_field(self.deaths))

    def _validate_numeric_input(self, value: str) -> bool:
        # Delegate numeric validation to utils
        return is_valid_numeric_value(value, 0, 999999)

    def _validate_field(self, var: tk.StringVar) -> None:
        # Clean value using utils; if invalid, reset
        val = var.get()
        if not is_valid_numeric_value(val, 0, 999999):
            var.set("")
        else:
            # Remove leading zeros for nicer display
            cleaned = clean_numeric_string(val)
            # Avoid unnecessary writes if already normalized
            if cleaned != val:
                var.set(cleaned)

    def _create_main_frame(self) -> None:
        style = ttk.Style()

        self.frame = ttk.Frame(self.root, padding="10", style='Custom.TFrame')
        self.frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        style.configure('TLabel', font=('Arial', 10))
        style.configure('TButton', font=('Arial', 10, 'bold'))
        style.configure('TExportButton', font=('Arial', 7))


    def _setup_discord_rpc(self) -> None:
        # Delegate to discord_integration.setup_discord_rpc to keep main focused
        try:
            from core.discord_integration import setup_discord_rpc
            setup_discord_rpc(self, DISCORD_CLIENT_ID)
        except Exception as e:
            logging.error(f"Failed to initialize Discord RPC via discord_integration: {e}")

    def _setup_ui(self) -> None:
        # Delegate UI construction to gui_components to keep main file focused
        try:
            from core.gui_components import build_ui
            build_ui(self)
        except Exception as e:
            logging.error(f"Failed to build UI from gui_components: {e}")
            raise

    def _update_discord_presence(self) -> None:
        try:
            from core.discord_integration import update_discord_presence
            update_discord_presence(self, RPC_UPDATE_INTERVAL)
        except Exception as e:
            logging.error(f"Failed to update Discord presence via discord_integration: {e}")


    def load_settings(self) -> None:
    # Load user settings from file.
        def load():
            try:
                persistent_settings = load_persistent_settings(PERSISTENCE_FILE)
                self.root.after(0, lambda: self._apply_settings(persistent_settings))
            except Exception as e:
                self.root.after(0, lambda: self._show_error(f"Error loading settings: {e}"))

        threading.Thread(target=load, daemon=True).start()

    def save_settings(self) -> None:
        # Persist commonly edited selections between sessions
        settings = {
            'profile_picture': self.profile_picture.get(),
            'sector': self.sector.get(),
            'planet': self.planet.get(),
            'mega_cities': self.mega_cities.get(),
            'level': int(self.level.get() or 0),
            'title': self.title.get(),
            'difficulty': self.difficulty.get(),
            'mission': self.mission_type.get(),
            'campaign': self.mission_category.get(),
            'subfaction': self.subfaction_type.get(),
            'DSS': bool(self.DSS.get()),
            'DSSMod': self.DSSMod.get() or 'Inactive',
        }
        try:
            save_persistent_settings(PERSISTENCE_FILE, settings)
        except Exception as e:
            self._show_error(f"Error saving persistent settings: {e}")
    
    def _on_close(self) -> None:
        # Save current selections before closing the app
        try:
            self.save_settings()
        except Exception as e:
            logging.error(f"Error during save on close: {e}")
        finally:
            try:
                self.root.destroy()
            except Exception:
                os._exit(0)

    def submit_data(self) -> None:
        with open(app_path('JSON', 'DCord.json'), 'r') as f:
            discord_data = json.load(f)
            global Platform
            Platform = discord_data.get('platform', 'Not Selected')

    # Handle mission report submission.
        if not self._validate_submission():
            return
            
        self.save_settings()
        self.update_time()

        # Observing faction is handled by observe_data() method

        if Platform == "Not Selected":
            self._show_error("ADVISORY: You must select a platform in settings before submitting")
            self.update_submit_button_image("Fail")
            return

        if self.mission_type.get() == "No missions available":
            self._show_error("ADVISORY: You cannot submit without selecting a mission")
            self.update_submit_button_image("Fail")
            return

        if self.planet.get() == "Meridia":
            self._show_error("ADVISORY: Volatile spacetime fluctuations currently prohibit FTL travel to the Meridian Black Hole.")
            self.update_submit_button_image("Fail")
            return

        if self.planet.get() in ["Angel's Venture", "Moradesh", "Ivis"]:
            self._show_error("ADVISORY: You cannot deploy on a fractured planet")
            self.update_submit_button_image("Fail")
            return

        if self.planet.get() in ["Widow's Harbor", "New Haven", "Pilen V", "Mars"]:
            self._show_error("ADVISORY: You cannot deploy on a scoured planet")
            self.update_submit_button_image("Fail")
            return

        data = self._collect_mission_data()

        sent_success = False
        if self._save_to_excel(data):
            if self._send_to_discord(data):
                logging.info("Sent To Discord")
                self.update_submit_button_image("Passed")
                sent_success = True
            else:
                self.update_submit_button_image("Fail")
            # Clear fields after submission
            def clear_text_widgets(widget):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Text):
                        child.delete("1.0", tk.END)
                    clear_text_widgets(child)
            clear_text_widgets(self.root)
            self.kills.set("")
            self.deaths.set("")
            self.rating.set("Outstanding Patriotism")
            # Ensure underlying note state is also cleared so empty notes don't reuse previous content
            try:
                if hasattr(self, 'note_entry'):
                    # If programmatic clear didn't trigger bindings, force the var to empty
                    self.note.set("")
            except Exception as e:
                logging.error(f"Failed to reset note state: {e}")
            
    def observe_data(self) -> None:
        """Handle observation data by running the observation.py script."""
        try:
            logging.info("Running observation script...")
            observation_path = app_path('core', 'observation.py')
            # Pass current planet from GUI to observation script
            current_planet = self.planet.get() if hasattr(self, 'planet') else "Unknown"
            subprocess.run([sys.executable, observation_path, current_planet], shell=False)
            self.update_submit_button_image("Passed")
        except Exception as e:
            logging.error(f"Failed to run observation script: {e}")
            self._show_error(f"Failed to run observation: {e}")
            self.update_submit_button_image("Fail")
    
    def _update_button_for_faction(self) -> None:
        """Update button appearance based on selected faction."""
        try:
            if not hasattr(self, 'submit_label'):
                return
                
            if self.enemy_type.get() == "Observing":
                # Switch to observe button
                self.submit_label.configure(image=self.observe_img_default)
                self.submit_label.image = self.observe_img_default
                self._submit_img_state = self.observe_img_default
            else:
                # Switch to submit button
                self.submit_label.configure(image=self.submit_img_default)
                self.submit_label.image = self.submit_img_default
                self._submit_img_state = self.submit_img_default
        except Exception as e:
            logging.error(f"Failed to update button for faction: {e}")
            
    def _validate_submission(self) -> bool:
    # Validate all required fields before submission.
        excel_file = EXCEL_FILE_TEST if DEBUG else EXCEL_FILE_PROD
        if os.path.exists(excel_file):
            df = pd.read_excel(excel_file)
            last_mission = df.iloc[-1] if not df.empty else None
        try:
            last_mission_kills = last_mission['Kills']
            last_mission_deaths = last_mission['Deaths']
            last_mission_note = last_mission['Note']
            last_mission_campaign = last_mission['Mission Category']
            last_mission_mission = last_mission['Mission Type']

            if (str(self.kills.get()) == str(last_mission_kills) and
                str(self.deaths.get()) == str(last_mission_deaths) and
                (self.note.get() or "").strip() == (last_mission_note or "").strip()):
                result = messagebox.askyesno("ADVISORY", "You appear to be submitting a duplicate mission report. Submit anyway?")
                if not result:
                    return False

            if ((self.mission_category.get() or "").strip() == (last_mission_campaign or "").strip() and
                (self.mission_type.get() or "").strip() == (last_mission_mission or "").strip()):
                result = messagebox.askyesno("ADVISORY", "This report contains the same mission as your last log, is this correct?")
                if not result:
                    return False
        except Exception as e:
            logging.error(f"Error checking for duplicate missions: {e}")

        try:
            # Validate numeric fields
            level = int(self.level.get())

            # Remove leading zeros using regex for kills
            kills_str = re.sub(r'^0+', '', self.kills.get())
            kills = int(kills_str) if kills_str else 0

            # Remove leading zeros using regex for deaths
            deaths_str = re.sub(r'^0+', '', self.deaths.get())
            deaths = int(deaths_str) if deaths_str else 0

            #set the cleaned values back to the variables
            self.kills.set(kills)
            self.deaths.set(deaths)

            #create a randint between 1 and 0 - to randomise for lil easter egg
            rndint = random.randint(0, 1)

            #check for stupid values
            if len(str(kills)) > 5 or len(str(deaths)) > 4:
                self._show_error("ADVISORY: What are you even trying?")
                self.update_submit_button_image("Fail")
                return False

            if level < 1 or level > 150:  # Add reasonable level range
                if rndint == 1:
                    self._show_error("ADVISORY: You are not a Helldiver")
                else:
                    self._show_error("Level must be between 1 and 150")
                self.update_submit_button_image("Fail")
                return False

            if kills < 0 or kills > 10000:
                if rndint == 1:
                    self._show_error("These kills will be reported to your Democracy Officer... I dear hope you're not lying...")
                else:
                    self._show_error("Invalid number of kills")
                self.update_submit_button_image("Fail")
                return False

            if deaths < 0 or deaths > 1000:
                if rndint == 1:
                    self._show_error("Surely you didn't die this many times... right?")
                else:
                    self._show_error("Invalid number of deaths")
                self.update_submit_button_image("Fail")
                return False

            # Validate required text fields
            if not self.Helldivers.get().strip():
                if rndint == 1:
                    self._show_error("I know we're cannon fodder but you could at least give yourself a name... have some dignity!")
                else:
                    self._show_error("Helldiver name is required")
                self.update_submit_button_image("Fail")
                return False

            if not self.mission_type.get().strip():
                if rndint == 1:
                    self._show_error("Did you sit in your hellpod the entire time?")
                else:
                    self._show_error("Mission type is required")
                self.update_submit_button_image("Fail")
                return False

            return True
        except ValueError:
            self._show_error("Invalid numeric input")
            return False

    def _show_error(self, message: str) -> None:
        messagebox.showerror("Error", message)

    def _open_info(self) -> None:
        try:
            readme_path = os.path.abspath("README.md")
            if os.path.exists(readme_path):
                webbrowser.open_new_tab(f"file:///{readme_path}")
                return
        except Exception as e:
            logging.error(f"Failed to open README: {e}")

        # Fallback: About dialog
        try:
            info_text = (
                f"Helldiver Mission Log Manager\n"
                f"Version: {VERSION}{DEV_RELEASE}\n\n"
                "- Logs missions to Excel and Discord webhooks\n"
                "- Use Settings (gear icon) to configure platform, webhooks, and names\n\n"
                "Helpful links:\n"
                "• Galactic War Map: https://helldiverscompanion.com/#map\n"
                "• Project README (in repo root)\n"
            )
            messagebox.showinfo("About / Help", info_text)
        except Exception as e:
            logging.error(f"Failed to show info dialog: {e}")

    def _calculate_current_streak(self) -> int:
        """Calculate the current streak based on the streak data and time difference."""
        try:
            streak_data = read_streaks(streak_file)
            helldiver_name = "Helldiver"
            user_data = streak_data.get(helldiver_name, {'streak': 0, 'last_time': None})
            
            # Default to streak 1 (reset)
            streak = 1
            
            # Check if we should continue the streak based on time difference
            if user_data.get('last_time'):
                last_time = datetime.strptime(user_data['last_time'], "%Y-%m-%d %H:%M:%S")
                time_diff = datetime.now() - last_time
                # If last mission was within 1 hour (3600 seconds), continue the streak
                if time_diff.total_seconds() <= 3600:
                    streak = user_data['streak'] + 1
            
            return streak
        except Exception as e:
            logging.error(f"Error calculating current streak: {e}")
            return 1  # Default to 1 on error

    def _collect_mission_data(self) -> Dict:
    # Collect all mission data into a dictionary.
        # Read the current note text directly from the Text widget if available to avoid stale cached values
        try:
            if hasattr(self, 'note_entry') and isinstance(self.note_entry, tk.Text):
                note_value = self.note_entry.get("1.0", "end-1c").strip()
            else:
                note_value = (self.note.get() or "").strip()
        except Exception as e:
            logging.error(f"Failed to read note text: {e}")
            note_value = (self.note.get() or "").strip()

        # Calculate the correct streak based on time difference
        current_streak = self._calculate_current_streak()

        return {
            'Super Destroyer': self.shipname1_default +" "+ self.shipname2_default,
            'Helldivers': self.helldiver_default,
            'Level': self.level.get(),
            'Title': self.title.get(),
            'Sector': self.sector.get(),
            'Planet': self.planet.get(),
            'Mega City': self.mega_cities.get(),
            'Enemy Type': self.enemy_type.get(),
            'Enemy Subfaction': self.subfaction_type.get(),
            'Enemy HVT': self.hvt_type.get(),
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
            'Streak': current_streak,
            'Note': note_value,
        }

    def _save_to_excel(self, data: Dict) -> bool:
    # Save mission data to Excel file by appending new rows.
        excel_file = EXCEL_FILE_TEST if DEBUG else EXCEL_FILE_PROD
        success = append_mission_to_excel(excel_file, data)
        
        # Update dynamic icons cache after successful mission submission
        if success:
            try:
                from core.dynamic_icons import update_dynamic_icons_from_excel
                update_dynamic_icons_from_excel()
                logging.info("Dynamic icons cache updated after mission submission")
            except Exception as e:
                logging.warning(f"Failed to update dynamic icons cache: {e}")
                # Don't fail the mission submission if cache update fails
        
        return success

    def _send_to_discord(self, data: Dict) -> bool:
        try:
            from core.discord_integration import send_to_discord
            excel_file = EXCEL_FILE_TEST if DEBUG else EXCEL_FILE_PROD
            return send_to_discord(self, data, excel_file, DEBUG, DATE_FORMAT, VERSION, DEV_RELEASE)
        except Exception as e:
            logging.error(f"Failed to send to Discord via discord_integration: {e}")
            return False
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
                # discordrpc does not expose close like pypresence; set no-op or future cleanup
                if hasattr(self.RPC, 'close'):
                    self.RPC.close()
            except Exception:
                pass

    def export_excel(self):
        try:
            try:
                sub_path = app_path('core', 'sub.py')
            except Exception:
                sub_path = os.path.join(os.path.dirname(__file__), 'core', 'sub.py')
            subprocess.run([sys.executable, sub_path], 
                          shell=False,
                          check=True,
                          capture_output=True)
        except subprocess.CalledProcessError as e:
            self._show_error(f"Export failed: {e}")

    def _apply_settings(self, settings: dict) -> None:
        lvl = settings.get('level')
        if isinstance(lvl, int) and lvl > 0:
            self.level.set(lvl)

        val = settings.get('title')
        if val:
            self.title.set(val)

        val = settings.get('sector')
        if val:
            self.sector.set(val)

        val = settings.get('planet')
        if val:
            self.planet.set(val)

        val = settings.get('difficulty')
        if val:
            self.difficulty.set(val)

        val = settings.get('mission')
        if val:
            self.mission_type.set(val)

        if 'DSS' in settings:
            # Respect explicit False; only skip if key missing
            self.DSS.set(bool(settings.get('DSS')))

        val = settings.get('DSSMod')
        if val:
            self.DSSMod.set(val)

        val = settings.get('campaign')
        if val:
            self.mission_category.set(val)

        val = settings.get('subfaction')
        if val:
            self.subfaction_type.set(val)
        # Mega city
        val = settings.get('mega_cities')
        if val:
            self.mega_cities.set(val)
        self.shipName1.set(getattr(self, 'shipname1_default', 'SES Adjudicator'))
        self.shipName2.set(getattr(self, 'shipname2_default', 'of Allegiance'))
        val = settings.get('profile_picture')
        if val:
            try:
                # Only apply if the value exists in the available options to avoid blanking a readonly combobox
                options = getattr(self, 'profile_pictures', [])
                if val in options:
                    self.profile_picture.set(val)
                    if hasattr(self, 'profile_picture_combo'):
                        self.profile_picture_combo.set(val)
                else:
                    logging.warning(f"Persisted profile_picture '{val}' not found in available options; keeping current selection.")
            except Exception as e:
                logging.error(f"Failed applying persisted profile_picture '{val}': {e}")

        # After loading saved sector/planet ensure dependent dropdowns refresh
        try:
            if hasattr(self, 'sectors_data') and self.sector.get() in self.sectors_data:
                planets = self.sectors_data[self.sector.get()]['planets']
                self.planet_combo['values'] = planets
                if self.planet.get() not in planets and planets:
                    self.planet.set(planets[0])
            # Trigger dependent refreshes
            if hasattr(self, 'planet_combo'):
                self.planet_combo.event_generate('<<ComboboxSelected>>')
            try:
                if callable(locals().get('update_subfactions', None)):
                    locals()['update_subfactions']()
                if callable(locals().get('update_mission_categories', None)):
                    locals()['update_mission_categories']()
                if callable(locals().get('update_mission_types', None)):
                    locals()['update_mission_types']()
            except Exception:
                pass
        except Exception as e:
            logging.error(f"Failed to refresh planet / mega city lists after settings load: {e}")
        
        # Load banner setting from settings.json file
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings_data = json.load(f)
                banner_setting = settings_data.get('banner', 'Biome Banner')
                if hasattr(self, 'banner_type_var'):
                    self.banner_type_var.set(banner_setting)
        except Exception as e:
            logging.error(f"Failed to load banner setting: {e}")
            if hasattr(self, 'banner_type_var'):
                self.banner_type_var.set('Biome Banner')
