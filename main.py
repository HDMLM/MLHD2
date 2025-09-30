# Helldiver Mission Log Manager (GUI)
#
# Tracks Helldivers 2 mission data, persists user settings, exports to Excel, and
# pushes Discord webhook reports with rich embeds + presence (RPC).
#
# Credits:
# - Dean: Primary JSON data contributions, testing, debugging, cosmetic improvements
# - Adam: Original script + GUI foundations
# - Jesse(GameForDays2): Testing, feedback, and moral support
# - Honourble mention, Copilot for handling that mundane shit like changing lists to data structs


# Times i've wished we didn't use Excel - 22
# Times we should move away from discord - 2
# Time we really shouldn't have used Python - 3

import tkinter as tk
from tkinter import ttk, messagebox
import requests
from datetime import datetime, timezone, timedelta
import json
import pandas as pd
import logging
from logging_config import setup_logging
from typing import Dict, List, Optional
import time
import configparser
import threading
import os
import subprocess
import shutil
import random
import re
import webbrowser
import discordrpc
from ui_sound import (
    init_ui_sounds,
    play_button_click,
    play_button_hover,
    register_global_click_binding,
    set_ui_sounds_enabled,
)


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
from icon import ENEMY_ICONS, DIFFICULTY_ICONS, SYSTEM_COLORS, PLANET_ICONS, CAMPAIGN_ICONS, MISSION_ICONS, BIOME_BANNERS, SUBFACTION_ICONS,  HVT_ICONS, DSS_ICONS, TITLE_ICONS, PROFILE_PICTURES

# Manual Configuration
GWDay = "Day: 600"
GWDate = "Date: 30/09/2025"
VERSION = "1.7.007"
DEV_RELEASE = "-dev"
RPC_UPDATE_INTERVAL = 10  # seconds, this is in seconds
DATE_FORMAT = "%d-%m-%Y %H:%M:%S"

# Load config
config = configparser.ConfigParser()
config.read('config.config')
DISCORD_CLIENT_ID = config['Discord']['DISCORD_CLIENT_ID']
iconconfig = configparser.ConfigParser()
iconconfig.read('icon.config')

DEBUG = config.getboolean('DEBUGGING', 'DEBUG', fallback=False)
setup_logging(DEBUG)

# File paths
if DEBUG:
    SETTINGS_FILE = './JSON/settings-dev.json'
    PERSISTENCE_FILE = './JSON/persistent-dev.json'
    streak_file = './JSON/streak_data-dev.json'
else:
    SETTINGS_FILE = './JSON/settings.json'
    PERSISTENCE_FILE = './JSON/persistent.json'
    streak_file = './JSON/streak_data.json'

# Set up application data paths 
APP_DATA = os.path.join(os.getenv('LOCALAPPDATA'), 'MLHD2')
if not os.path.exists(APP_DATA):
    os.makedirs(APP_DATA)

EXCEL_FILE_PROD = os.path.join(APP_DATA, 'mission_log.xlsx')
EXCEL_FILE_TEST = os.path.join(APP_DATA, 'mission_log_test.xlsx')


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

# Apply default theme to the GUI
DEFAULT_THEME = make_theme(
    bg="#252526",      # background color
    fg="#FFFFFF",      # foreground/text color
    entry_bg="#252526",
    entry_fg="#000000",
    button_bg="#4C4C4C",
    button_fg="#000000",
    frame_bg="#252526"
)

def apply_theme(style, theme_dict):
    for widget, opts in theme_dict.items():
        for method, cfg in opts.items():
            getattr(style, method)(widget, **cfg)


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
        if hasattr(self, 'submit_label'):
            self.submit_label.configure(image=self.submit_img_default)
            self.submit_label.image = self.submit_img_default
            self._submit_img_state = self.submit_img_default

        def leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                delattr(widget, 'tooltip')

        def motion(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.geometry(f"+{event.x_root+15}+{event.y_root+10}")

        widget.bind("<Leave>", leave)
        widget.bind("<Motion>", motion)
        widget.bind("<Enter>", enter)


    def __init__(self, *args, **kwargs):
        # Initialize the GUI application.
        try:
            init_ui_sounds(preload=True)
        except Exception:
            pass
        style = ttk.Style()
        apply_theme(style, DEFAULT_THEME)
        self.root = root
        # Install global click sound bindings early so newly created widgets are covered
        try:
            self._install_click_sound()
        except Exception as e:
            logging.debug(f"Failed to install global click sound binding: {e}")
        if not os.path.exists(EXCEL_FILE_PROD):
            columns = [
                'Super Destroyer', 'Helldivers', 'Level', 'Title', 'Sector', 'Planet', 'Mega City',
                'Enemy Type', 'Enemy Subfaction', 'Enemy HVT', 'Major Order', 'DSS Active', 'DSS Modifier',
                'Mission Category', 'Mission Type', 'Difficulty', 'Kills', 'Deaths', 'Rating', 'Time', 'Note'
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
                from PIL import Image, ImageTk
                pil_icon = Image.open('SuperEarth.png').convert('RGBA')
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
        self.root.after(2000, self._periodic_rpc_update)
        # Save settings on window close
        try:
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        except Exception as e:
            logging.error(f"Failed to bind WM_DELETE_WINDOW handler: {e}")

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

        self.frame = ttk.Frame(self.root, padding="10", style='Custom.TFrame')
        self.frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        style.configure('TLabel', font=('Arial', 10))
        style.configure('TButton', font=('Arial', 10, 'bold'))
        style.configure('TExportButton', font=('Arial', 7))


    def _setup_discord_rpc(self) -> None:
    # Initialize Discord Rich Presence using discordrpc.
        def init_rpc():
            try:
                # discordrpc expects an integer app_id
                app_id_int = int(DISCORD_CLIENT_ID)
                self.RPC = discordrpc.RPC(app_id=app_id_int)
                # Start the RPC event loop in a background thread
                threading.Thread(target=self.RPC.run, daemon=True).start()
                self.last_rpc_update = time.time()  # Initialize the timestamp
                logging.info("Discord Rich Presence (discordrpc) initialized successfully")
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
        SETime = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M:%S")#

        try:
            # Try to use Insignia font by family name (Tkinter does not support loading from file directly)
            self.fs_sinclair_font = None
            insignia_font_path = os.path.abspath("./MiscItems/Fonts/Insignia.ttf")
            try:
                self.fs_sinclair_font = tkfont.Font(root=self.root, family="Insignia", size=14)
            except tk.TclError:
                # Font not installed, try to load using tk.call to add font from file (Windows only)
                pass
            if os.path.exists(insignia_font_path):
                try:
                    self.root.tk.call("font", "create", "InsigniaTemp", "-family", "Insignia", "-size", 14)
                    self.fs_sinclair_font = tkfont.Font(root=self.root, name="InsigniaTemp", exists=True)
                    logging.info("Loaded Insignia font from file (font must be installed system-wide).")
                except Exception as load_e:
                    logging.error(f"Failed to load Insignia font from file: {load_e}")
            else:
                logging.error("Insignia.ttf not found in ./MiscItems/Fonts/")
        except Exception as e:
            self.fs_sinclair_font = None
            logging.error(f"Failed to load Insignia font: {e}")

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
        external_frame = ttk.Frame(header_frame)

        font_to_use = self.fs_sinclair_font if self.fs_sinclair_font is not None else tkfont.Font(family="Arial", size=14, weight="bold")
        ttk.Label(header_frame, text="Operation Details", font=font_to_use).pack(side=tk.LEFT)

        # Galactic War label and toggle
        gw_frame = ttk.Frame(external_frame)
        gw_frame.pack(side=tk.LEFT, padx=(0,0), pady=(0,0))

        # Place Galactic War label, icon, and date in the top right of the window
        top_right_frame = ttk.Frame(self.root)
        top_right_frame.place(relx=1.0, rely=0.0, anchor="ne", x=-40, y=20)  # 20px from top-right corner

        # Add GW label, date toggle, and icon in a single row (icon on the right)
        try:
            pil_gw_icon = Image.open("./media/SyInt/gw_icon.png").convert('RGBA')
            pil_gw_icon = pil_gw_icon.resize((pil_gw_icon.width // 55, pil_gw_icon.height // 55), Image.LANCZOS)
            bg_color = (37, 37, 38, 255)
            background = Image.new('RGBA', pil_gw_icon.size, bg_color)
            pil_gw_icon = Image.alpha_composite(background, pil_gw_icon)
            self.gw_icon_img = ImageTk.PhotoImage(pil_gw_icon)
            gw_icon_label = ttk.Label(top_right_frame, image=self.gw_icon_img, cursor="hand2")
            # Place icon on the right of the text
            gw_icon_label.pack(side=tk.RIGHT, padx=(1, 0))
            gw_icon_label.bind("<Button-1>", toggle_gw_date)
        except Exception as e:
            logging.error(f"Failed to load GW icon: {e}")

        ttk.Label(top_right_frame, text="Galactic War").pack(side=tk.LEFT)

        gw_label = ttk.Label(top_right_frame, textvariable=gw_date_var, cursor="hand2", width=14, anchor="w")
        gw_label.pack(side=tk.LEFT, padx=(2,0))
        gw_label.bind("<Button-1>", toggle_gw_date)

        # Pack external_frame so its children are visible
        external_frame.pack(side=tk.LEFT, padx=(10,0))

        mission_frame = ttk.LabelFrame(content, padding=10, labelwidget=header_frame)

        def update_time():
            mission_time_var.set((datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%H:%M:%S"))

        self.update_time = update_time
        mission_frame.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        # Fix: Explicitly configure grid columns to prevent overlap
        for col in range(8):
            mission_frame.columnconfigure(col, weight=1)

        # Load sectors from config (and store for later)
        with open('./JSON/PlanetSectors.json', 'r') as f:
            sectors_data = json.load(f)
            self.sectors_data = sectors_data
            sector_list = list(sectors_data.keys())

        # --- Mission Info Grid ---
        # Load ship name selections and Helldiver username from settings.json
        try:
            with open(self.settings_file, 'r') as f:
                settings_data = json.load(f)
                shipName1_default = settings_data.get('shipName1', "SES Adjudicator")
                shipName2_default = settings_data.get('shipName2', "of Allegiance")
                self.shipname1_default = shipName1_default
                self.shipname2_default = shipName2_default
                self.helldiver_default = settings_data.get('username', "")
                self.full_ship_name = f"{shipName1_default} {shipName2_default}".strip()
        except Exception:
            shipName1_default = "SES Adjudicator"
            shipName2_default = "of Allegiance"
            self.shipname1_default = shipName1_default
            self.shipname2_default = shipName2_default
            self.helldiver_default = ""

        # Seed the Helldiver field from settings.json if it's empty/unset
        if not self.Helldivers.get():
            self.Helldivers.set(self.helldiver_default or "")

        ttk.Label(mission_frame, text="Level:").grid(row=0, column=2, sticky=tk.W, padx=0, pady=5)
        ttk.Entry(mission_frame, textvariable=self.level, width=35).grid(row=0, column=2, sticky=tk.W, padx=(45,0), pady=5)


        ttk.Label(mission_frame, text="Title:").grid(row=1, column=2, sticky=tk.W, pady=5)
        # Load titles from json file
        with open('./JSON/Titles.json', 'r') as f:
            titles_data = json.load(f)
            self.titles = titles_data["Titles"]
        self.title_combo = ttk.Combobox(mission_frame, textvariable=self.title, state='readonly', width=32)
        self.title_combo['values'] = self.titles
        self.title_combo.grid(row=1, column=2, sticky=tk.W, padx=(45,0), pady=5)
        self.title_combo.set(self.titles[0])

        ttk.Label(mission_frame, text="Profile:").grid(row=2, column=2, sticky=tk.W, pady=5)
        # Load profile pictures from json
        with open('./JSON/ProfilePictures.json', 'r') as f:
            profile_data = json.load(f)
            self.profile_pictures = profile_data["Profile Pictures"]
        self.profile_picture_combo = ttk.Combobox(mission_frame, textvariable=self.profile_picture, state='readonly', width=32)
        self.profile_picture_combo['values'] = self.profile_pictures
        self.profile_picture_combo.grid(row=2, column=2, sticky=tk.W, padx=(45,0), pady=5)
        self.profile_picture_combo.set(self.profile_pictures[0])

    # --- Mission Details Section ---
        # Create details_frame with custom font for the label
        details_frame = ttk.LabelFrame(content, padding=10)
        details_label = ttk.Label(details_frame, text="Mission Details", font=font_to_use)
        details_frame['labelwidget'] = details_label
        details_frame.grid(row=1, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))

        profile_preview_frame = ttk.LabelFrame(mission_frame, labelwidget=ttk.Label(mission_frame, text="Profile Preview", font=("Arial", 10, "bold"), anchor="center", justify="center"), padding=5)
        profile_preview_frame.grid(row=0, column=3, rowspan=6, sticky=tk.N, padx=(20,0))  # Adjusted row span and sticky

        # Create label to hold the preview image with fixed square dimensions
        self.preview_label = tk.Label(profile_preview_frame, width=120, height=120, borderwidth=0)  # Fixed size for square preview
        self.preview_label.pack(padx=0, pady=0)  # Reduced vertical padding

        def update_profile_preview(*args):
            try:
                # Get selected profile name
                profile_name = self.profile_picture.get()
                if not profile_name:
                    return
                

                # Construct path to profile picture
                img_path = os.path.join('.\media', 'profile_pictures', f"{profile_name}.png")


                # Load and resize image for preview
                pil_img = Image.open(img_path).convert("RGBA")
                pil_img = pil_img.resize((120, 120), Image.LANCZOS)  # Adjust size as needed
                img = ImageTk.PhotoImage(pil_img)

                # Store reference to prevent garbage collection
                self.preview_img = img

                # Update preview label
                self.preview_label.configure(image=img)

            except Exception as e:
                logging.error(f"Failed to load profile preview: {e}")
                self.preview_label.configure(image='')

        # Bind preview update to profile selection
        self.profile_picture.trace_add("write", update_profile_preview)

        # Initial preview update
        update_profile_preview()

        ttk.Label(mission_frame, text="Sector:").grid(row=0, column=0, sticky=tk.W, pady=5)
        sector_combo = ttk.Combobox(mission_frame, textvariable=self.sector, values=sector_list, state='readonly', width=27)
        sector_combo.grid(row=0, column=1, padx=5, pady=5)
        sector_combo.set(sector_list[0])
            

        ttk.Label(mission_frame, text="Planet:").grid(row=1, column=0, sticky=tk.W, pady=5)
        planet_combo = ttk.Combobox(mission_frame, textvariable=self.planet, state='readonly', width=27)
        planet_combo.grid(row=1, column=1, padx=5, pady=5)
        self.sector_combo = sector_combo 
        self.planet_combo = planet_combo
        

        # Create frame for planet preview with increased size
        planet_preview_frame = ttk.LabelFrame(mission_frame, labelwidget=ttk.Label(mission_frame, text="Planet Preview", font=("Arial", 10, "bold"), anchor="center", justify="center"), padding=5)
        planet_preview_frame.grid(row=0, column=4, rowspan=6, sticky=tk.N, padx=(20,0))


        # Create label to hold the preview image with fixed square dimensions
        self.planet_preview_label = tk.Label(planet_preview_frame, width=120, height=120, borderwidth=0)
        self.planet_preview_label.pack(padx=0, pady=0)

        # sector frame and label
        sector_frame = ttk.LabelFrame(mission_frame, labelwidget=ttk.Label(mission_frame, text="Sector Preview", font=("Arial", 10, "bold"), anchor="center", justify="center"), padding=5)
        sector_frame.grid(row=0, column=5, rowspan=6, sticky=tk.N, padx=(20,0))

        self.sector_info_label = tk.Label(sector_frame, borderwidth=0)
        self.sector_info_label.pack(padx=0, pady=0)


        try:
            pil_phimg = Image.open("sector-placeholder.png").convert('RGBA')
            bg_color = (37, 37, 38, 255)
            background = Image.new('RGBA', pil_phimg.size, bg_color)
            pil_phimg = Image.alpha_composite(background, pil_phimg)
            self.sector_info_img = ImageTk.PhotoImage(pil_phimg)
            self.sector_info_label.configure(image=self.sector_info_img)
        except Exception as e:
            logging.error(f"Failed to load sector preview image: {e}")

        # Create label and frame to hold the biome of the planet
        biome_frame = ttk.LabelFrame(details_frame, text="Planet Biome", padding=5)
        biome_frame.grid(row=0, column=6, rowspan=6, sticky=tk.N, padx=(20,0))

        self.planet_biome_label = tk.Label(biome_frame, borderwidth=0)  # no width/height -> uses image natural size
        self.planet_biome_label.pack(padx=0, pady=0)

        def update_biome_banner(*args,f):
            try:
                planet_name = self.planet.get()
                biome_map = f
                biome_name = biome_map.get(planet_name, "Mars")
                logging.debug(f"Planet: {planet_name}, Biome: {biome_name}")
                self.current_biome = biome_name

                # Build absolute, cross-platform path to biome banner
                base_dir = os.path.dirname(os.path.abspath(__file__))
                banner_path = os.path.join(base_dir, 'media', 'biome_banners', f"{biome_name}.png")
                if not os.path.isfile(banner_path):
                    logging.warning(f"Biome banner not found at {banner_path}, falling back to Mars.png")
                    banner_path = os.path.join(base_dir, 'media', 'biome_banners', 'Mars.png')

                logging.debug(f"Loading biome banner from: {banner_path}")

                pil_banner = Image.open(banner_path).convert('RGBA')
                bg_color = (37, 37, 38, 255)
                background = Image.new('RGBA', pil_banner.size, bg_color)
                pil_banner = Image.alpha_composite(background, pil_banner)
                self.biome_banner_img = ImageTk.PhotoImage(pil_banner)
                self.planet_biome_label.configure(image=self.biome_banner_img)
            except Exception as e:
                logging.error(f"Failed to load biome banner: {e}")
                #fallback to default
                banner_path = os.path.join('.\media', 'biome_banners', "Mars.png")
                self.planet_biome_label.configure(image='')

        def update_planet_preview(*args):
            try:
                # Get selected planet name
                planet_name = self.planet.get()
                if not planet_name:
                    return

                with open('./JSON/BiomePlanets.json', 'r', encoding='utf-8') as f:
                    biome_map = json.load(f)
                biome_name = biome_map.get(planet_name, "Mars")
                # Compare selected planet (parent) to BiomePlanets.json keys and get its biome (child)
                child_biome = biome_map.get(planet_name)
                if not child_biome:
                    # Case-insensitive fallback search
                    for parent, child in biome_map.items():
                        if parent.lower() == planet_name.lower():
                            child_biome = child
                            break

                # Final fallback
                if not child_biome:
                    child_biome = "Super Earth"

                BiomePlanet = child_biome
                
                # Construct path to planet picture
                img_path = os.path.join('.\media', 'planets', f"{BiomePlanet}.png")
                # Load and resize image for preview
                pil_img = Image.open(img_path).convert('RGBA')
                bg_color = (37, 37, 38, 255)
                background = Image.new('RGBA', pil_img.size, bg_color)
                pil_img = Image.alpha_composite(background, pil_img)
                self.planet_preview_img = ImageTk.PhotoImage(pil_img)
                self.planet_preview_label.configure(image=self.planet_preview_img)
                update_biome_banner(f=biome_map) # passing biome data to avoid reloading file
            except Exception as e:
                logging.error(f"Failed to load planet preview: {e}")
                self.planet_preview_label.configure(image='')

        def update_sector_preview(*args):
            try:
            # Get selected sector name and enemy type
                sector_name = self.sector.get()
                enemy_type = self.enemy_type.get()
                if not sector_name:
                    return

                # Define chroma colors based on enemy type
                enemy_colors = {
                    "Automatons": "#ff6d6d",
                    "Terminids": "#ffc100",
                    "Illuminate": "#8960ca",
                    "Observing": "#41639C"
                }
            
                # Get color for current enemy, default to white
                chroma_color = enemy_colors.get(enemy_type, "#ffffff")

                # Construct path to sector image
                img_path = os.path.join('.\media', 'sectors', f"{sector_name}.png")

                # Load image using PIL first for color manipulation
                pil_img = Image.open(img_path)

                # Convert to RGBA if not already
                pil_img = pil_img.convert('RGBA')

                # Get image data
                data = pil_img.getdata()

                # Replace white pixels with enemy color
                new_data = []
                for item in data:
                    # If pixel is white (or nearly white), replace with chroma color
                    if item[0] > 240 and item[1] > 240 and item[2] > 240:
                        # Convert hex color to RGB
                        r = int(chroma_color[1:3], 16)
                        g = int(chroma_color[3:5], 16)
                        b = int(chroma_color[5:7], 16)
                        new_data.append((r, g, b, item[3]))  # Keep original alpha
                    else:
                        new_data.append(item)
            
                # Update image with new colors
                pil_img.putdata(new_data)

                # Composite with frame background (same as planet preview)
                bg_color = (37, 37, 38, 255)  # #252526
                background = Image.new('RGBA', pil_img.size, bg_color)
                pil_img = Image.alpha_composite(background, pil_img)

                # Convert PIL image to PhotoImage
                photo = ImageTk.PhotoImage(pil_img)

                # Store reference to prevent garbage collection
                self.sector_preview_img = photo

                # Update preview label
                self.sector_info_label.configure(image=photo)

            except Exception as e:
                logging.error(f"Failed to load sector preview: {e}")
                self.sector_info_label.configure(image='')

        # Bind preview update to both sector AND enemy type selection
        self.sector.trace_add("write", update_sector_preview)
        self.enemy_type.trace_add("write", update_sector_preview)

        # Initial preview update
        update_sector_preview()

        # Bind preview update to planet selection
        self.planet.trace_add("write", update_planet_preview)

        # Initial preview update
        update_planet_preview()

        ttk.Label(mission_frame, text="Mega City:").grid(row=2, column=0, sticky=tk.W, pady=5)
        mega_cities_combo = ttk.Combobox(mission_frame, textvariable=self.mega_cities, state='readonly', width=27)
        mega_cities_combo.grid(row=2, column=1, sticky=tk.W, padx=(8,0), pady=5)
        self.mega_cities_combo = mega_cities_combo



    # Dynamic planet / mega city lists
        def update_mega_cities(*args):
            # Populate mega cities based on currently selected planet.
            selected_planet = self.planet.get()
            try:
                with open("./JSON/MegaCityPlanets.json", "r") as f:
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

        # 7 images underneath mega city and profile, packed tightly together
        # Each image is based on a dropdown: enemy type, subfaction, campaign, difficulty, mission, major order, DSS
        self.row_image_labels = []
        images_row_frame = ttk.Frame(mission_frame)
        images_row_frame.grid(row=4, column=0, columnspan=7, sticky="w", padx=0, pady=0)  # Remove vertical padding
        for idx in range(7):
            lbl = tk.Label(images_row_frame, width=60, height=60, borderwidth=0, highlightthickness=0)  # Smaller size
            lbl.pack(side=tk.LEFT, padx=8, pady=0)  # Tighter packing
            self.row_image_labels.append(lbl)

        def update_row_images(*args):
            # Image 1: Enemy Type
            enemy_type = self.enemy_type.get()
            enemy_icon_path = os.path.join('./media/factions', f"{enemy_type}.png") if enemy_type else None
            if not enemy_icon_path or not os.path.exists(enemy_icon_path):
                enemy_icon_path = "sector-placeholder.png"

            # Image 2: Subfaction
            subfaction_type = self.subfaction_type.get()
            subfaction_type_clean = subfaction_type.replace(" ", "_") if subfaction_type else ""
            subfaction_icon_path = os.path.join('./media/subfactions', f"{subfaction_type_clean}.png") if subfaction_type_clean else None
            if not subfaction_icon_path or not os.path.exists(subfaction_icon_path):
                subfaction_icon_path = "sector-placeholder.png"

            # Image 3: Campaign
            campaign_type = self.mission_category.get()
            campaign_type_clean = campaign_type.replace(" ", "_") if campaign_type else ""
            campaign_icon_path = os.path.join('./media/campaigns', f"{campaign_type_clean}.png") if campaign_type_clean else None
            if not campaign_icon_path or not os.path.exists(campaign_icon_path):
                campaign_icon_path = "sector-placeholder.png"

            # Image 4: Difficulty
            try:
                difficulty_type = self.difficulty.get()
                if difficulty_type and '-' in difficulty_type:
                    difficulty_type_clean = difficulty_type.split('-', 1)[1].strip()
                else:
                    difficulty_type_clean = difficulty_type.replace(" ", "_") if difficulty_type else ""
                difficulty_icon_path = os.path.join('./media/difficulties', f"{difficulty_type_clean}.png")
                if not difficulty_icon_path or not os.path.exists(difficulty_icon_path):
                    difficulty_icon_path = "sector-placeholder.png"
            except Exception as e:
                logging.error(f"Error loading difficulty icon: {e}")
                difficulty_icon_path = "sector-placeholder.png"

            # Image 5: Mission
            mission_type = self.mission_type.get()
            enemy_type = self.enemy_type.get()
            # Special handling for Blitz: Search and Destroy missions
            if mission_type == "Blitz: Search and Destroy":
                if enemy_type == "Terminids":
                    mission_icon_filename = "Blitz Search and Destroy_Terminids.png"
                elif enemy_type == "Automatons":
                    mission_icon_filename = "Blitz Search and Destroy_Automatons.png"
                else:
                    mission_icon_filename = f"{mission_type}.png"
            elif mission_type == "Blitz: Secure Research Site":
                mission_icon_filename = "Blitz Secure Research Site.png"
            elif mission_type == "Blitz: Destroy Illuminate Warp Ships":
                mission_icon_filename = "Blitz Destroy Illuminate Warp Ships.png"
            else:
                mission_icon_filename = f"{mission_type}.png" if mission_type else None
            mission_icon_path = os.path.join('./media/missions', mission_icon_filename) if mission_icon_filename else None
            if not mission_icon_path or not os.path.exists(mission_icon_path):
                mission_icon_path = "sector-placeholder.png"

            # Image 6: Major Order checkbox
            major_order_active = self.MO.get()
            if major_order_active:
                major_order_icon_path = os.path.join('./media/major_order', "Major_Order_True.png")
            else:
                major_order_icon_path = os.path.join('./media/major_order', "Major_Order_False.png")
            if not os.path.exists(major_order_icon_path):
                major_order_icon_path = "sector-placeholder.png"

            # Image 7: DSS dropdown
            dss_mod = self.DSSMod.get()
            dss_mod_clean = dss_mod.replace(" ", "_") if dss_mod else ""
            dss_icon_path = os.path.join('./media/dssmod', f"{dss_mod_clean}.png") if dss_mod_clean else None
            if not dss_icon_path or not os.path.exists(dss_icon_path):
                dss_icon_path = "sector-placeholder.png"

            icon_paths = [
                enemy_icon_path,
                subfaction_icon_path,
                campaign_icon_path,
                difficulty_icon_path,
                mission_icon_path,
                major_order_icon_path,
                dss_icon_path,
            ]
            self.row_images = []
            for idx, (lbl, img_path) in enumerate(zip(self.row_image_labels, icon_paths)):
                try:
                    if img_path and os.path.exists(img_path):
                        pil_img = Image.open(img_path).convert('RGBA')
                        pil_img = pil_img.resize((60, 60), Image.LANCZOS)
                        bg_color = (37, 37, 38, 255)
                        background = Image.new('RGBA', pil_img.size, bg_color)
                        pil_img = Image.alpha_composite(background, pil_img)
                        tk_img = ImageTk.PhotoImage(pil_img)
                        lbl.configure(image=tk_img)
                        lbl.image = tk_img  # Prevent garbage collection
                        self.row_images.append(tk_img)
                    else:
                        lbl.configure(image='')
                        lbl.image = None
                except Exception as e:
                    logging.error(f"Failed to load row image {img_path}: {e}")
                    lbl.configure(image='')
                    lbl.image = None

        # Bind updates to dropdowns and checkboxes
        self.enemy_type.trace_add("write", update_row_images)
        self.subfaction_type.trace_add("write", update_row_images)
        self.mission_category.trace_add("write", update_row_images)
        self.difficulty.trace_add("write", update_row_images)
        self.mission_type.trace_add("write", update_row_images)
        self.MO.trace_add("write", update_row_images)
        self.DSSMod.trace_add("write", update_row_images)
        # Initial population
        update_row_images()


        # Create a dedicated frame for setting and invite buttons to avoid affecting grid row height
        button_icon_frame = ttk.Frame(mission_frame)
        button_icon_frame.grid(row=0, column=7, padx=(0,10), pady=(0,10), sticky=tk.NE,rowspan=7)
        # Top row to place Settings (kept inside) and a separate root-level info button
        top_buttons_row = ttk.Frame(button_icon_frame)
        top_buttons_row.pack(side=tk.TOP, pady=(10,8), padx=(10,0))
        # Settings button with hover effect
        try:
            def load_settings_btn_img(path):
                pil_img = Image.open(path).convert('RGBA')
                pil_img = pil_img.resize((pil_img.width // 4, pil_img.height // 4), Image.LANCZOS)
                bg_color = (37, 37, 38, 255)
                background = Image.new('RGBA', pil_img.size, bg_color)
                pil_img = Image.alpha_composite(background, pil_img)
                return ImageTk.PhotoImage(pil_img)

            self.settings_btn_img_default = load_settings_btn_img("./media/SyInt/SettingsButton.png")
            self.settings_btn_img_hover = load_settings_btn_img("./media/SyInt/SettingsButtonHover.png")

            self.settings_btn_label = tk.Label(
                top_buttons_row,
                image=self.settings_btn_img_default,
                borderwidth=0,
                highlightthickness=0,
                cursor="hand2"
            )
            self.settings_btn_label.pack(side=tk.LEFT, pady=0, padx=(0,6))

            def on_settings_btn_enter(e):
                    self.settings_btn_label.configure(image=self.settings_btn_img_hover)
                    try:
                        play_button_hover()
                    except Exception:
                        pass
            def on_settings_btn_leave(e):
                self.settings_btn_label.configure(image=self.settings_btn_img_default)

            self.settings_btn_label.bind("<Enter>", on_settings_btn_enter)
            self.settings_btn_label.bind("<Leave>", on_settings_btn_leave)
            self.settings_btn_label.bind("<Button-1>", lambda e: subprocess.run(['python', 'settings.py', '-ML']))
        except Exception as e:
            logging.error(f"Failed to load settings button image: {e}")
            fallback_label = tk.Label(top_buttons_row, text="Settings", cursor="hand2")
            fallback_label.pack(side=tk.LEFT, pady=0, padx=(0,6))
            fallback_label.bind("<Button-1>", lambda e: subprocess.run(['python', 'settings.py']))

        # Info (Help) button with hover effect, placed OUTSIDE frames at root top-right and smaller
        try:
            # Create a root-level overlay frame for the info button
            self.top_right_info_frame = ttk.Frame(self.root)
            # Anchor to top-right, adjust x/y padding as needed
            self.top_right_info_frame.place(relx=1.0, rely=0.0, anchor="ne", x=-8, y=8)

            def load_help_btn_img(path):
                pil_img = Image.open(path).convert('RGBA')
                # Smaller than other icons
                pil_img = pil_img.resize((max(12, pil_img.width // 6), max(12, pil_img.height // 6)), Image.LANCZOS)
                bg_color = (37, 37, 38, 255)
                background = Image.new('RGBA', pil_img.size, bg_color)
                pil_img = Image.alpha_composite(background, pil_img)
                return ImageTk.PhotoImage(pil_img)

            self.help_btn_img_default = load_help_btn_img("./media/SyInt/HelpButton.png")
            self.help_btn_img_hover = load_help_btn_img("./media/SyInt/HelpButtonHover.png")

            self.help_btn_label = tk.Label(
            self.top_right_info_frame,
            image=self.help_btn_img_default,
            borderwidth=0,
            highlightthickness=0,
            cursor="hand2"
            )
            self.help_btn_label.pack(side=tk.LEFT, pady=0, padx=0)

            def on_help_btn_enter(e):
                    self.help_btn_label.configure(image=self.help_btn_img_hover)
                    try:
                        play_button_hover()
                    except Exception:
                        pass
            def on_help_btn_leave(e):
                self.help_btn_label.configure(image=self.help_btn_img_default)

            self.help_btn_label.bind("<Enter>", on_help_btn_enter)
            self.help_btn_label.bind("<Leave>", on_help_btn_leave)

            def show_sector_placeholder_window():
                # Create a new top-level window
                win = tk.Toplevel(self.root)
                win.title("Sector Placeholder")
                win.resizable(False, False)
                # Load the image
                try:
                    pil_img = Image.open("sector-placeholder.png").convert('RGBA')
                    img = ImageTk.PhotoImage(pil_img)
                    lbl = tk.Label(win, image=img)
                    lbl.image = img  # Keep reference
                    lbl.pack(padx=10, pady=10)
                except Exception as e:
                    lbl = tk.Label(win, text="Failed to load image")
                    lbl.pack(padx=10, pady=10)

            self.help_btn_label.bind("<Button-1>", lambda e: show_sector_placeholder_window())
        except Exception as e:
            logging.error(f"Failed to load help/info button image: {e}")
            help_fallback = tk.Label(self.root, text="Info", cursor="hand2")
            help_fallback.place(relx=1.0, rely=0.0, anchor="ne", x=-8, y=8)
            help_fallback.bind("<Button-1>", lambda e: show_sector_placeholder_window())

        # Invite button with hover effect
        try:
            def load_invite_btn_img(path):
                pil_img = Image.open(path).convert('RGBA')
                pil_img = pil_img.resize((pil_img.width // 4, pil_img.height // 4), Image.LANCZOS)
                bg_color = (37, 37, 38, 255)
                background = Image.new('RGBA', pil_img.size, bg_color)
                pil_img = Image.alpha_composite(background, pil_img)
                return ImageTk.PhotoImage(pil_img)

            self.invite_btn_img_default = load_invite_btn_img("./media/SyInt/InviteButton.png")
            self.invite_btn_img_hover = load_invite_btn_img("./media/SyInt/InviteButtonHover.png")

            self.invite_btn_label = tk.Label(
            button_icon_frame,
            image=self.invite_btn_img_default,
            borderwidth=0,
            highlightthickness=0,
            cursor="hand2"
            )
            self.invite_btn_label.pack(side=tk.TOP, pady=(0,8), padx=(10,0))

            def on_invite_btn_enter(e):
                    self.invite_btn_label.configure(image=self.invite_btn_img_hover)
                    try:
                        play_button_hover()
                    except Exception:
                        pass
            def on_invite_btn_leave(e):
                self.invite_btn_label.configure(image=self.invite_btn_img_default)

            self.invite_btn_label.bind("<Enter>", on_invite_btn_enter)
            self.invite_btn_label.bind("<Leave>", on_invite_btn_leave)
            self.invite_btn_label.bind("<Button-1>", lambda e: webbrowser.open("https://discord.gg/U6ydgwFKZG"))
        except Exception as e:
            logging.error(f"Failed to load invite button image: {e}")
            invite_fallback = tk.Label(button_icon_frame, text="Invite Button", cursor="hand2")
            invite_fallback.pack(side=tk.TOP, pady=(0,8), padx=(10,0))
            invite_fallback.bind("<Button-1>", lambda e: webbrowser.open("https://discord.gg/U6ydgwFKZG"))

    # Enemy selection
        ttk.Label(details_frame, text="Enemy Type:").grid(row=0, column=0, sticky=tk.W, pady=5)

        with open('./JSON/Missions.json', 'r') as f:
            missions_data = json.load(f)
            enemy_types = list(missions_data.keys())

        with open('./JSON/Enemies.json', 'r') as f:
            enemies_data = json.load(f)
            enemy_types = list(enemies_data.keys())

        enemy_combo = ttk.Combobox(details_frame, textvariable=self.enemy_type, values=enemy_types, state='readonly', width=27)
        enemy_combo.grid(row=0, column=1, padx=5, pady=5)

    # Major Order + DSS toggles
        ttk.Label(details_frame, text="Major Order:").grid(row=2, column=2, sticky=tk.W, pady=5)
        ttk.Checkbutton(details_frame, variable=self.MO).grid(row=2, column=2, sticky=tk.W, padx=(100,0), pady=5)

    # DSS modifier dropdown (shown only if active)
        ttk.Label(details_frame, text="DSS Active:").grid(row=2, column=2, sticky=tk.W, pady=5, padx=(150,0))
        ttk.Checkbutton(details_frame, variable=self.DSS).grid(row=2, column=2, sticky=tk.W, padx=(250,0), pady=5)

        self.dss_frame = ttk.Frame(details_frame)
        self.dss_frame.grid(row=3, column=2, sticky=tk.W, pady=5)
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

    # HVT Type
        ttk.Label(details_frame, text="High-Value Target:").grid(row=1, column=2, sticky=tk.W, pady=5)
        hvt_combo = ttk.Combobox(details_frame, textvariable=self.hvt_type, state='readonly', width=27)
        hvt_combo.grid(row=1, column=2, padx=(125,0), pady=5)


    # Campaign
        ttk.Label(details_frame, text="Mission Campaign:").grid(row=1, column=0, sticky=tk.W, pady=5)
        mission_cat_combo = ttk.Combobox(details_frame, textvariable=self.mission_category, state='readonly', width=27)
        mission_cat_combo.grid(row=1, column=1, padx=5, pady=5)

    # Difficulty
        ttk.Label(details_frame, text="Mission Difficulty:").grid(row=2, column=0, sticky=tk.W, pady=5)
        difficulty_combo = ttk.Combobox(details_frame, textvariable=self.difficulty, state='readonly', width=27)
        difficulty_combo.grid(row=2, column=1, padx=5, pady=5)


    # Mission type
        ttk.Label(details_frame, text="Mission Name:").grid(row=3, column=0, sticky=tk.W, pady=5)
        mission_type_combo = ttk.Combobox(details_frame, textvariable=self.mission_type, state='readonly', width=27)
        mission_type_combo.grid(row=3, column=1, padx=5, pady=5)


        def update_subfactions(*args):
            enemy = self.enemy_type.get()
            subfactions = []
            if enemy in missions_data:
                subfactions = list(missions_data[enemy].keys())
                logging.info(f"Available subfactions for {enemy}: {subfactions}")
                subfaction_combo['values'] = subfactions
            else:
                subfaction_combo['values'] = []
            if subfactions:
                subfaction_combo.set(subfactions[0])
                update_mission_categories()

        def update_hvts(*args):
            enemy = self.enemy_type.get()
            subfaction = self.subfaction_type.get()
            
            try:
                with open('./JSON/Enemies.json', 'r') as f:
                    enemies_data = json.load(f)
                
                # Get HVTs for selected enemy/subfaction
                if enemy in enemies_data:
                    hvt_list = enemies_data[enemy].get(subfaction, [])
                    
                    # Convert string to list if needed
                    if isinstance(hvt_list, str):
                        if hvt_list == "No HVTs":
                            hvt_list = ["No HVTs"]
                        else:
                            hvt_list = [hvt_list]
                    elif not isinstance(hvt_list, list):
                        hvt_list = ["No HVTs"]
                    
                    # Ensure list is not empty before setting values
                    if not hvt_list:
                        hvt_list = ["No HVTs"]
                        
                    hvt_combo['values'] = hvt_list
                    hvt_combo.set(hvt_list[0] if hvt_list else "No HVTs")
                    logging.info(f"Updated HVTs for {enemy}/{subfaction}: {hvt_list}")
                else:
                    hvt_combo['values'] = ["No HVTs"]
                    hvt_combo.set("No HVTs")
                    logging.info(f"No enemy type found: {enemy}")
                    
            except Exception as e:
                logging.error(f"Error updating HVTs: {e}")
                hvt_combo['values'] = ["Error loading HVTs"]
                hvt_combo.set("Error loading HVTs")

        enemy_combo.bind('<<ComboboxSelected>>', lambda e: [update_subfactions(e), update_hvts(e)])
        subfaction_combo.bind('<<ComboboxSelected>>', lambda e: [update_mission_categories(e), update_hvts(e)])
        update_hvts() # Initial population

        # Clear HVT when enemy type changes
        def reset_hvt(*args):
            self.hvt_type.set("No HVTs")
        self.enemy_type.trace_add("write", reset_hvt)

        def update_mission_categories(*args):
            enemy = self.enemy_type.get()
            subfaction = self.subfaction_type.get()
            categories = []
            if enemy in missions_data and subfaction in missions_data[enemy]:
                categories = list(missions_data[enemy][subfaction].keys())
                mission_cat_combo['values'] = categories
            else:
                mission_cat_combo['values'] = []
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

        enemy_combo.bind('<<ComboboxSelected>>', lambda e: [update_subfactions()])
        subfaction_combo.bind('<<ComboboxSelected>>', lambda e: [update_mission_categories()])
        self.enemy_type.trace_add("write", lambda *args: update_hvts())
        self.subfaction_type.trace_add("write", lambda *args: update_hvts())
        mission_cat_combo.bind('<<ComboboxSelected>>', update_mission_types)
        difficulty_combo.bind('<<ComboboxSelected>>', update_available_missions)

        # Set enemy type first, then update subfactions and mission categories
        enemy_combo.set("Observing")
        # Prime dependent dropdowns on initial load so they are not blank
        try:
            update_subfactions()
            update_mission_categories()
            update_mission_types()
        except Exception as e:
            logging.error(f"Failed to initialize dependent dropdowns: {e}")

    # --- Stats + Note ---
        stats_note_container = ttk.Frame(content)
        stats_note_container.grid(row=2, column=0, padx=5, pady=5, sticky=(tk.W, tk.E))

    # Stats
        stats_frame = ttk.LabelFrame(stats_note_container, text="Mission Results", padding=10)
        stats_label = ttk.Label(stats_frame, text="Mission Results", font=font_to_use)
        stats_frame['labelwidget'] = stats_label
        stats_frame.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)

    # Note
        note_frame = ttk.LabelFrame(stats_note_container, text="Notes", padding=10)
        note_label = ttk.Label(note_frame, text="Notes", font=font_to_use)
        note_frame['labelwidget'] = note_label
        note_frame.pack(side=tk.RIGHT, padx=5, fill=tk.BOTH, expand=True)

        MAX_NOTE_CHARS = 512

        note_font = tkfont.Font(family=font_to_use, size=14)
        note_entry = tk.Text(note_frame, height=3, width=30, wrap="word", font=note_font)
        note_entry.grid(row=0, column=0, padx=5, pady=(5,0), sticky=(tk.W, tk.E, tk.N, tk.S))
        self.note_entry = note_entry

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

    # Submit (Image Button with Hover)
        try:
            def load_btn_img(path):
                pil_img = Image.open(path).convert('RGBA')
                pil_img = pil_img.resize((pil_img.width, pil_img.height), Image.LANCZOS)
                bg_color = (37, 37, 38, 255)
                background = Image.new('RGBA', pil_img.size, bg_color)
                pil_img = Image.alpha_composite(background, pil_img)
                return ImageTk.PhotoImage(pil_img)

            self.submit_img_default = load_btn_img("./media/SyInt/SubmitButtonNH.png")
            self.submit_img_hover = load_btn_img("./media/SyInt/SubmitButtonHover.png")
            self.submit_img_yes = load_btn_img("./media/SyInt/SubmitButtonYes.png")
            self.submit_img_no = load_btn_img("./media/SyInt/SubmitButtonNo.png")

            self._submit_img_state = self.submit_img_default
            self.submit_label = tk.Label(content, image=self.submit_img_default, borderwidth=0, highlightthickness=0, cursor="hand2")
            self.submit_label.grid(row=3, column=0, pady=15)

            def on_enter(e):
                    self.submit_label.configure(image=self.submit_img_hover)
                    try:
                        play_button_hover()
                    except Exception:
                        pass
            def on_leave(e):
                self.submit_label.configure(image=self._submit_img_state)

            def on_click(e):
                play_button_click()
                self.submit_data()

            self.submit_label.bind("<Enter>", on_enter)
            self.submit_label.bind("<Leave>", on_leave)
            self.submit_label.bind("<Button-1>", on_click)
        except Exception as e:
            logging.error(f"Failed to load submit button image: {e}")
            submit_button = ttk.Button(content, text="Submit Mission Report", command=self.submit_data, width=130, padding=(0, 30))
            submit_button.grid(row=3, column=0, pady=15)

        # Submission overlay image placed behind the submit button
        try:
            overlay_img_path = "./media/SyInt/SubmissionOverlay.png"
            pil_overlay = Image.open(overlay_img_path).convert('RGBA')
            new_width = int(pil_overlay.width * 1.05)
            new_height = pil_overlay.height
            pil_overlay = pil_overlay.resize((new_width, new_height), Image.LANCZOS)
            bg_color = (37, 37, 38, 255)
            background = Image.new('RGBA', pil_overlay.size, bg_color)
            pil_overlay = Image.alpha_composite(background, pil_overlay)
            self.submit_overlay_img = ImageTk.PhotoImage(pil_overlay)
            self.submit_overlay_label = tk.Label(
            content, image=self.submit_overlay_img, borderwidth=0, highlightthickness=0, bg="#252526"
            )
            self.submit_overlay_label.grid(row=3, column=0, pady=(10, 0), padx=(0, 5), sticky="n")
            self.submit_overlay_label.lower(self.submit_label)
        except Exception as e:
            logging.error(f"Failed to load submission overlay image: {e}")


        # Export + Style sections
        bottom_frame = ttk.LabelFrame(content, text="Report Style and Export", padding=10)
        bottom_frame.grid(row=4, column=0, pady=5, sticky=(tk.W, tk.E))

        # Export buttons / integrations
        export_frame = ttk.LabelFrame(content, text="Exporting", padding=10)
        export_frame.grid(row=4, column=0, pady=5, sticky=(tk.W, tk.E))

        # Export GUI launcher with image and hover effect, with sound effect on click
        try:
            def load_export_gui_img(path):
                pil_img = Image.open(path).convert('RGBA')
                pil_img = pil_img.resize((pil_img.width // 2, pil_img.height // 2), Image.LANCZOS)
                bg_color = (37, 37, 38, 255)
                background = Image.new('RGBA', pil_img.size, bg_color)
                pil_img = Image.alpha_composite(background, pil_img)
                return ImageTk.PhotoImage(pil_img)

            self.export_gui_img_default = load_export_gui_img("./media/SyInt/ExportGUIButton.png")
            self.export_gui_img_hover = load_export_gui_img("./media/SyInt/ExportGUIButtonHover.png")

            # Pad left side by increasing padx
            self.export_gui_label = tk.Label(export_frame, image=self.export_gui_img_default, borderwidth=0, highlightthickness=0, cursor="hand2")
            self.export_gui_label.grid(row=4, column=0, pady=15, padx=(20,0))  # <-- Increased left padding here

            def on_export_gui_enter(e):
                    self.export_gui_label.configure(image=self.export_gui_img_hover)
                    try:
                        play_button_hover()
                    except Exception:
                        pass
            def on_export_gui_leave(e):
                self.export_gui_label.configure(image=self.export_gui_img_default)

            def on_export_gui_click(e):
                play_button_click()
                subprocess.run(['python', 'exportGUI.py'], shell=False)

            self.export_gui_label.bind("<Enter>", on_export_gui_enter)
            self.export_gui_label.bind("<Leave>", on_export_gui_leave)
            self.export_gui_label.bind("<Button-1>", on_export_gui_click)
        except Exception as e:
            logging.error(f"Failed to load Export GUI button image: {e}")
            GUIbutton = ttk.Button(export_frame, text=" Open\nExport\n  GUI", command=lambda: subprocess.run(['python', 'exportGUI.py'], shell=False), padding=(6,5), width=14)
            GUIbutton.grid(row=4, column=0, pady=15, padx=(20,0))  # <-- Increased left padding here

    # Planet aggregation export (with image and hover effect)
        try:
            def load_export_planet_img(path):
                pil_img = Image.open(path).convert('RGBA')
                pil_img = pil_img.resize((pil_img.width // 2, pil_img.height // 2), Image.LANCZOS)
                bg_color = (37, 37, 38, 255)
                background = Image.new('RGBA', pil_img.size, bg_color)
                pil_img = Image.alpha_composite(background, pil_img)
                return ImageTk.PhotoImage(pil_img)

            self.export_planet_img_default = load_export_planet_img("./media/SyInt/ExportPlanetButton.png")
            self.export_planet_img_hover = load_export_planet_img("./media/SyInt/ExportPlanetButtonHover.png")

            self.export_planet_label = tk.Label(export_frame, image=self.export_planet_img_default, borderwidth=0, highlightthickness=0, cursor="hand2")
            self.export_planet_label.grid(row=4, column=1, padx=(20,0), pady=15)

            def on_export_planet_enter(e):
                    self.export_planet_label.configure(image=self.export_planet_img_hover)
                    try:
                        play_button_hover()
                    except Exception:
                        pass
            def on_export_planet_leave(e):
                self.export_planet_label.configure(image=self.export_planet_img_default)

            def on_export_planet_click(e):
                play_button_click()
                subprocess.run(['python', 'sub.py'], shell=False)

            self.export_planet_label.bind("<Enter>", on_export_planet_enter)
            self.export_planet_label.bind("<Leave>", on_export_planet_leave)
            self.export_planet_label.bind("<Button-1>", on_export_planet_click)
        except Exception as e:
            logging.error(f"Failed to load Export Planet button image: {e}")
            export_button = ttk.Button(export_frame, text="Export Planet\n     Data to\n   Webhook", command=lambda: subprocess.run(['python', 'sub.py']), padding=(6,5), width=14)
            export_button.grid(row=4, column=1, padx=(20,0), pady=15)

    # Faction aggregation export (with image and hover effect)
        # Faction aggregation export (with image and hover effect)
        try:
            def load_export_faction_img(path):
                pil_img = Image.open(path).convert('RGBA')
                pil_img = pil_img.resize((pil_img.width // 2, pil_img.height // 2), Image.LANCZOS)
                bg_color = (37, 37, 38, 255)
                background = Image.new('RGBA', pil_img.size, bg_color)
                pil_img = Image.alpha_composite(background, pil_img)
                return ImageTk.PhotoImage(pil_img)

            self.export_faction_img_default = load_export_faction_img("./media/SyInt/ExportFactionButton.png")
            self.export_faction_img_hover = load_export_faction_img("./media/SyInt/ExportFactionButtonHover.png")

            self.export_faction_label = tk.Label(export_frame, image=self.export_faction_img_default, borderwidth=0, highlightthickness=0, cursor="hand2")
            self.export_faction_label.grid(row=4, column=2, padx=(20,0), pady=15)

            def on_export_faction_enter(e):
                    self.export_faction_label.configure(image=self.export_faction_img_hover)
                    try:
                        play_button_hover()
                    except Exception:
                        pass
            def on_export_faction_leave(e):
                self.export_faction_label.configure(image=self.export_faction_img_default)

            def on_export_faction_click(e):
                play_button_click()
                subprocess.run(['python', 'faction.py'], shell=False)

            self.export_faction_label.bind("<Enter>", on_export_faction_enter)
            self.export_faction_label.bind("<Leave>", on_export_faction_leave)
            self.export_faction_label.bind("<Button-1>", on_export_faction_click)
        except Exception as e:
            logging.error(f"Failed to load Export Faction button image: {e}")
            export_button = ttk.Button(export_frame, text="Export Faction\n      Data to\n    Webhook", command=lambda: subprocess.run(['python', 'faction.py']), padding=(6,5), width=14)
            export_button.grid(row=4, column=2, padx=(20,0), pady=15)

        # Prior 7 days aggregation export (with image and hover effect)
        try:
            def load_export_7days_img(path):
                pil_img = Image.open(path).convert('RGBA')
                pil_img = pil_img.resize((pil_img.width // 2, pil_img.height // 2), Image.LANCZOS)
                bg_color = (37, 37, 38, 255)
                background = Image.new('RGBA', pil_img.size, bg_color)
                pil_img = Image.alpha_composite(background, pil_img)
                return ImageTk.PhotoImage(pil_img)

            self.export_7days_img_default = load_export_7days_img("./media/SyInt/Export7DaysButton.png")
            self.export_7days_img_hover = load_export_7days_img("./media/SyInt/Export7DaysButtonHover.png")

            self.export_7days_label = tk.Label(export_frame, image=self.export_7days_img_default, borderwidth=0, highlightthickness=0, cursor="hand2")
            self.export_7days_label.grid(row=4, column=3, padx=(20,0), pady=15)

            def on_export_7days_enter(e):
                    self.export_7days_label.configure(image=self.export_7days_img_hover)
                    try:
                        play_button_hover()
                    except Exception:
                        pass
            def on_export_7days_leave(e):
                self.export_7days_label.configure(image=self.export_7days_img_default)

            def on_export_7days_click(e):
                play_button_click()
                subprocess.run(['python', '7days.py'], shell=False)

            self.export_7days_label.bind("<Enter>", on_export_7days_enter)
            self.export_7days_label.bind("<Leave>", on_export_7days_leave)
            self.export_7days_label.bind("<Button-1>", on_export_7days_click)

        except Exception as e:
            logging.error(f"Failed to load Export 7 Days button image: {e}")
            export_button = ttk.Button(export_frame, text="Export Last 7 Days\n       Data to\n     Webhook", command=lambda: subprocess.run(['python', '7days.py']), padding=(6,5), width=16)
            export_button.grid(row=4, column=3, padx=(20,0), pady=15)

        # Favourite aggregation export (with image and hover effect)
        try:
            def load_export_favourites_img(path):
                pil_img = Image.open(path).convert('RGBA')
                pil_img = pil_img.resize((pil_img.width // 2, pil_img.height // 2), Image.LANCZOS)
                bg_color = (37, 37, 38, 255)
                background = Image.new('RGBA', pil_img.size, bg_color)
                pil_img = Image.alpha_composite(background, pil_img)
                return ImageTk.PhotoImage(pil_img)

            self.export_favourites_img_default = load_export_favourites_img("./media/SyInt/ExportFavouritesButton.png")
            self.export_favourites_img_hover = load_export_favourites_img("./media/SyInt/ExportFavouritesButtonHover.png")

            self.export_favourites_label = tk.Label(export_frame, image=self.export_favourites_img_default, borderwidth=0, highlightthickness=0, cursor="hand2")
            self.export_favourites_label.grid(row=4, column=4, padx=(20,0), pady=15)

            def on_export_favourites_enter(e):
                    self.export_favourites_label.configure(image=self.export_favourites_img_hover)
                    try:
                        play_button_hover()
                    except Exception:
                        pass
            def on_export_favourites_leave(e):
                self.export_favourites_label.configure(image=self.export_favourites_img_default)

            def on_export_favourites_click(e):
                play_button_click()
                subprocess.run(['python', 'favourites.py'], shell=False)

            self.export_favourites_label.bind("<Enter>", on_export_favourites_enter)
            self.export_favourites_label.bind("<Leave>", on_export_favourites_leave)
            self.export_favourites_label.bind("<Button-1>", on_export_favourites_click)
        except Exception as e:
            logging.error(f"Failed to load Export Favourites button image: {e}")
            export_button = ttk.Button(export_frame, text="Export Favourites\n        Data to\n     Webhook", command=lambda: subprocess.run(['python', 'favourites.py']), padding=(6,5), width=16)
            export_button.grid(row=4, column=4, padx=(20,0), pady=15)

        image_button_frame = ttk.Frame(mission_frame)
        image_button_frame.grid(row=5, column=4, padx=5, pady=5)

        # Achievements export button (with image and hover effect)
        try:
            def load_export_achievements_img(path):
                pil_img = Image.open(path).convert('RGBA')
                pil_img = pil_img.resize((pil_img.width // 2, pil_img.height // 2), Image.LANCZOS)
                bg_color = (37, 37, 38, 255)
                background = Image.new('RGBA', pil_img.size, bg_color)
                pil_img = Image.alpha_composite(background, pil_img)
                return ImageTk.PhotoImage(pil_img)

            self.export_achievements_img_default = load_export_achievements_img("./media/SyInt/ExportAchievementsButton.png")
            self.export_achievements_img_hover = load_export_achievements_img("./media/SyInt/ExportAchievementsButtonHover.png")

            self.export_achievements_label = tk.Label(export_frame, image=self.export_achievements_img_default, borderwidth=0, highlightthickness=0, cursor="hand2")
            self.export_achievements_label.grid(row=4, column=5, padx=(20,0), pady=15)

            self.export_achievements_label.grid(row=4, column=5, padx=(20,0), pady=15)

            def on_export_achievements_enter(e):
                    self.export_achievements_label.configure(image=self.export_achievements_img_hover)
                    try:
                        play_button_hover()
                    except Exception:
                        pass
            def on_export_achievements_leave(e):
                self.export_achievements_label.configure(image=self.export_achievements_img_default)

            def on_export_achievements_click(e):
                play_button_click()
                subprocess.run(['python', 'achievements.py'], shell=False)

            self.export_achievements_label.bind("<Enter>", on_export_achievements_enter)
            self.export_achievements_label.bind("<Leave>", on_export_achievements_leave)
            self.export_achievements_label.bind("<Button-1>", on_export_achievements_click)
        except Exception as e:
            logging.error(f"Failed to load Export Achievements button image: {e}")
            export_button = ttk.Button(export_frame, text="Export Achievements\n        Data to\n     Webhook", command=lambda: subprocess.run(['python', 'achievements.py']), padding=(6,5), width=16)
            export_button.grid(row=4, column=5, padx=(20,0), pady=15)

        ###############################################################
        # END OF GUI SETUP
        ###############################################################

    def _update_discord_presence(self) -> None:
        # Update Discord Rich Presence with current mission information.
        if not hasattr(self, 'RPC') or self.RPC is None:
            return

        current_time = time.time()
        # Only update if enough time has passed, but always update if last_rpc_update is 0
        if self.last_rpc_update != 0 and current_time - self.last_rpc_update < RPC_UPDATE_INTERVAL:
            return

        try:
            helldiver = self.helldiver_default or "Unknown Helldiver"
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

            # Debug logging
            logging.info(f"Updating Discord RPC: enemytype={enemytype}, small_image={small_image}")

            # Set activity type based on enemy type
            if enemytype == "Observing":
                small_text = "Observing"
                act_type = 3  # Watching
                logging.info(f"set_activity params: state=On sector: {sector} | Planet: {planet}, details=Helldiver: {helldiver} Level: {level} | {title}, large_image=test, large_text=Helldivers 2, small_image={small_image}, small_text={small_text}, act_type={act_type}")
                if self.RPC is not None:
                    self.RPC.set_activity(
                        state=f"On sector: {sector} | Planet: {planet}",
                        details=f"Helldiver: {helldiver} Level: {level} | {title}",
                        large_image="test",
                        large_text="Helldivers 2",
                        small_image=small_image,
                        small_text=small_text,
                        act_type=act_type,
                    )
                    self.last_rpc_update = current_time
                else:
                    logging.warning("Discord RPC object is not initialized.")
            else:
                small_text = f"Fighting: {enemytype}"

                #handle special shit from planet names
                rpcplanet = planet.replace("ö", "o")
                rpcplanet = rpcplanet.replace("-", "_")
                rpcplanet = rpcplanet.replace("'", "")
                buttons = Button(
                    "View Galactic War", "https://helldiverscompanion.com/#map",
                    "More Info", "https://helldiverscompanion.com/#hellpad/planets/{}".format(rpcplanet.replace(" ", "_"))
                )
                logging.info(f"set_activity params: state=On sector: {sector} | Planet: {planet}, details=Helldiver: {helldiver} Level: {level} | {title}, large_image=test, large_text=Helldivers 2, small_image={small_image}, small_text={small_text}, act_type=Playing (default), buttons={buttons}")
                if self.RPC is not None:
                    self.RPC.set_activity(
                        state=f"On sector: {sector} | Planet: {planet}",
                        details=f"Helldiver: {helldiver} Level: {level} | {title}",
                        large_image="test",
                        large_text="Helldivers 2",
                        small_image=small_image,
                        small_text=small_text,
                        buttons=buttons,
                    )
                    self.last_rpc_update = current_time
                else:
                    logging.warning("Discord RPC object is not initialized.")
        except Exception as e:
            logging.error(f"Failed to update Discord Rich Presence: {e}")


    def load_settings(self) -> None:
    # Load user settings from file.
        def load():
            try:
                persistent_settings = {}
                if os.path.exists(PERSISTENCE_FILE):
                    with open(PERSISTENCE_FILE, 'r') as f:
                        persistent_settings = json.load(f)
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
            with open(PERSISTENCE_FILE, 'w') as f:
                json.dump(settings, f, indent=4)
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
        with open('./JSON/DCord.json', 'r') as f:
            discord_data = json.load(f)
            global Platform
            Platform = discord_data.get('platform', 'Not Selected')

    # Handle mission report submission.
        if not self._validate_submission():
            return
            
        self.save_settings()
        self.update_time()

        if self.enemy_type.get() == "Observing":
            self._show_error("ADVISORY: You cannot submit an observation mission")
            self.update_submit_button_image("Fail")
            return

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
            'Note': note_value,
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
            GoldStar = iconconfig['Stars']['GoldStar']
            GreyStar = iconconfig['Stars']['GreyStar']
            
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
            hvt_icon = get_hvt_icon(data['Enemy HVT'])
            campaign_icon = get_campaign_icon(data['Mission Category'])
            if data['Mission Type'] == "Blitz: Search and Destroy" and data['Enemy Type'] == "Automatons":
                mission_icon = get_mission_icon("PLACEHOLDER")
            else:
                mission_icon = get_mission_icon(data['Mission Type'])
            biome_banner = get_biome_banner(data['Planet'])
            dss_icon = get_dss_icon(data['DSS Modifier'])
            title_icon = get_title_icon(data['Title'])
            profile_picture = get_profile_picture(self.profile_picture.get())

            # Get discord_uid from DCord.json
            with open('./JSON/DCord.json', 'r') as f:
                dcord_data = json.load(f)
                user_discord_uid = dcord_data.get('discord_uid', '')

            bicon = iconconfig['BadgeIcons']['Icon'] if user_discord_uid in ['695767541393653791', '850139032720900116'] else ''
            
            if dcord_data.get('platform') == 'Steam':
                    PIco = iconconfig['BadgeIcons-Platform']['Steam']
            elif dcord_data.get('platform') == 'PlayStation':
                    PIco = iconconfig['BadgeIcons-Platform']['PlayStation']
            elif dcord_data.get('platform') == 'Xbox':
                    PIco = iconconfig['BadgeIcons-Platform']['Xbox']
            else:
                    PIco = ''

            # Check mission log for planet visits - USE APPDATA PATH
            excel_file = EXCEL_FILE_TEST if DEBUG else EXCEL_FILE_PROD  # <-- FIXED
            try:
                df = pd.read_excel(excel_file)
                bsuperearth = iconconfig['BadgeIcons']['Super Earth'] if 'Super Earth' in df['Planet'].values else ''
                bcyberstan = iconconfig['BadgeIcons']['Cyberstan'] if 'Cyberstan' in df['Planet'].values else ''
                bmaleveloncreek = iconconfig['BadgeIcons']['Malevelon Creek'] if 'Malevelon Creek' in df['Planet'].values else ''
                bcalypso = iconconfig['BadgeIcons']['Calypso'] if 'Calypso' in df['Planet'].values or user_discord_uid in ['695767541393653791', '850139032720900116'] else ''
                bpopliix = iconconfig['BadgeIcons']['Popli IX'] if 'Pöpli IX' in df['Planet'].values else ''
            except Exception as e:
                logging.error(f"Error checking mission log for planet visits: {e}")
                # Set default values if file doesn't exist
                bsuperearth = bcyberstan = bmaleveloncreek = bcalypso = bpopliix = ''

            # Dynamic performance tracking icons
            try:
                excel_file = EXCEL_FILE_TEST if DEBUG else EXCEL_FILE_PROD
                if os.path.exists(excel_file):
                    df = pd.read_excel(excel_file)
                    last_mission = df.iloc[-2] if not df.empty else None
                    
                    # Compare current kills/deaths to previous mission independently
                    if last_mission is not None:
                        prev_kills = last_mission['Kills']
                        prev_deaths = last_mission['Deaths']
                        current_kills = int(data['Kills'])
                        current_deaths = int(data['Deaths'])
                        
                        # Calculate separate indicators for kills and deaths
                        if current_kills > prev_kills:
                            killico = iconconfig['MiscIcon']['Positive']
                        elif current_kills < prev_kills:
                            killico = iconconfig['MiscIcon']['Negative']
                        else:
                            killico = iconconfig['MiscIcon']['Neutral']
                            
                        if current_deaths < prev_deaths:
                            deathico = iconconfig['MiscIcon']['PositiveDeaths']
                        elif current_deaths > prev_deaths:
                            deathico = iconconfig['MiscIcon']['NegativeDeaths']
                        else:
                            deathico = iconconfig['MiscIcon']['Neutral']
            except Exception as e:
                logging.error(f"Error calculating previous kills/deaths: {e}")
                killico = ''
                deathico = ''

            # Streak tracking (missions within 1h chain)
            helldiver_name = "Helldiver"
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
                with open('./JSON/DCord.json', 'r') as f:
                    settings_data = json.load(f)
                    UID = settings_data.get('discord_uid', '0')
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logging.error(f"Error loading settings.json: {e}")
                UID = '0'  # Fallback to default
            # Platform from local DCord.json (user settings)
            try:
                with open('./JSON/DCord.json', 'r') as f:
                    settings_data = json.load(f)
                    Platform = settings_data.get('platform', "Not Selected")
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logging.error(f"Error loading DCord.json: {e}")
                Platform = "Not Selected"  # Fallback to default
            MICo = str(data["Major Order"]) + " " + iconconfig['MiscIcon']['MO'] if data["Major Order"] else str(data["Major Order"])
            DSSIco = str(data["DSS Active"]) + " " + iconconfig['MiscIcon']['DSS'] if data["DSS Active"] else str(data["DSS Active"])

            message_content = {
                "content": None,
                "embeds": [{
                    "title": f"{data['Super Destroyer']}\nDeployed {data['Helldivers']}\n{bicon}{PIco}{bsuperearth}{bcyberstan}{bmaleveloncreek}{bcalypso}{bpopliix}",
                    "description": f"**Level {data['Level']} | {data['Title']} {title_icon}\nMission: {total_missions_main}**\n\n<a:easyshine1:1349110651829747773> <:hd1superearth:1103949794285723658> **Galactic Intel** {planet_icon} <a:easyshine3:1349110648528699422>\n> Sector: {data['Sector']}\n> Planet: {data['Planet']}\n> Mega City: {data['Mega City']}\n> Major Order: {MICo}\n> DSS Active: {DSSIco}\n> DSS Modifier: {data['DSS Modifier']} {dss_icon}\n\n",
                    "color": system_color,
                    "fields": [{
                        "name": f"<a:easyshine1:1349110651829747773> {enemy_icon} **Enemy Intel** {subfaction_icon} <a:easyshine3:1349110648528699422>",
                        "value": f"> Faction: {data['Enemy Type']}\n> Subfaction: {data['Enemy Subfaction']}\n" +
                        (f"> High-Value Target: {data['Enemy HVT']} {hvt_icon}\n" if data['Enemy HVT'] != "No HVTs" else "") +
                        f"> Campaign: {data['Mission Category']}\n\n<a:easyshine1:1349110651829747773> {campaign_icon} **Mission Intel** {mission_icon} <a:easyshine3:1349110648528699422>\n> Mission: {data['Mission Type']}\n> Difficulty: {data['Difficulty']} {diff_icon}\n> Kills: {data['Kills']} {killico}\n> Deaths: {data['Deaths']} {deathico}\n> KDR: {(int(data['Kills']) / max(1, int(data['Deaths']))):.2f}\n> Rating: {data['Rating']}\n\n {Stars}\n"
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
                with open('./JSON/DCord.json', 'r') as f:
                    dcord_data = json.load(f)
                    ACTIVE_WEBHOOK = dcord_data.get('discord_webhooks_logging', [])
                    # Backward/forward compatibility: allow list of dicts with {'label','url'}
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
                # discordrpc does not expose close like pypresence; set no-op or future cleanup
                if hasattr(self.RPC, 'close'):
                    self.RPC.close()
            except Exception:
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

if __name__ == "__main__":
    # Efficiently validate Discord ID and Platform before launching GUI
    try:
        with open('./JSON/DCord.json', 'r') as f:
            settings_data = json.load(f)
        discord_uid = settings_data.get('discord_uid', '0')
        platform = settings_data.get('platform', "Not Selected")
        if not (re.match(r'^\d{17,19}$', discord_uid) or (DEBUG and discord_uid == '0')):
            logging.error("Please set a valid Discord ID in the settings.py file")
            messagebox.showerror("Error", "Please set a valid Discord ID in the settings.py file")
            subprocess.run(['python', 'settings.py'])
            os._exit(1)
        if platform == "Not Selected":
            logging.error("Please set a valid Platform in settings.py")
            messagebox.showerror("Error", "Please set a valid Platform in settings.py")
            subprocess.run(['python', 'settings.py'])
            os._exit(1)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error loading DCord.json: {e}")
        messagebox.showerror("Error", f"Error loading DCord.json: {e}")
        os._exit(1)

    root = tk.Tk()
    app = MissionLogGUI(root)
    root.mainloop()