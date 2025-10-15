import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import re
import logging
import sys
import traceback
from PIL import Image, ImageTk
import tkinter.font as tkfont
from ui_sound import (
    play_button_click,
    play_button_hover,
    init_ui_sounds,
    register_global_click_binding,
    set_ui_sounds_enabled,
)
from placard import generate_helldiver_banner
import io
import requests
import threading

# ---------- Paths ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = os.path.join(BASE_DIR, "JSON")
SETTINGS_PATH = os.path.join(JSON_DIR, "settings.json")
DCORD_PATH = os.path.join(JSON_DIR, "DCord.json")
PERSISTENT_PATH = os.path.join(JSON_DIR, "persistent.json")
FORCED_WEBHOOK_URL = "https://discord.com/api/webhooks/1419785470493327420/7XCGBlF3Ya5QQUiypMWP0fWAsNF-fIoui4m-nwfcp11IwWrkJzUN3VwM1uJdxHT2SGYZ"

# Paths for generated media assets
MEDIA_DIR = os.path.join(BASE_DIR, "media")
MISC_ITEMS_DIR = os.path.join(MEDIA_DIR, "MiscItems")
GENERATED_BANNER_FILENAME = "GeneratedBanner.png"
GENERATED_BANNER_PATH = os.path.join(MISC_ITEMS_DIR, GENERATED_BANNER_FILENAME)

# ---------- Helpers ----------
def norm(s: str) -> str:
    if s is None:
        return ""
    s = str(s).replace("\xa0", " ")
    return " ".join(s.strip().split()).casefold()



# ---------- Theme ----------
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
        "TNotebook.Tab": {"configure": {"background": button_bg or bg, "foreground": entry_fg or fg}},
    }

DEFAULT_THEME = make_theme(
    bg="#252526",
    fg="#FFFFFF",
    entry_bg="#252526",
    entry_fg="#000000",
    button_bg="#4C4C4C",
    button_fg="#000000",
    frame_bg="#252526",
)

# ---------- Data ----------
SHIP1_OPTIONS = [
    "SES Adjudicator", "SES Advocate", "SES Aegis", "SES Agent", "SES Arbiter", "SES Banner", "SES Beacon", "SES Blade", "SES Bringer", "SES Champion", "SES Citizen", "SES Claw", "SES Colossus", "SES Comptroller", "SES Courier", "SES Custodian", "SES Dawn", "SES Defender", "SES Diamond", "SES Distributor", "SES Dream", "SES Elected Representative", "SES Emperor", "SES Executor", "SES Eye", "SES Father", "SES Fist", "SES Flame", "SES Force", "SES Forerunner", "SES Founding Father", "SES Gauntlet", "SES Giant", "SES Guardian", "SES Halo", "SES Hammer", "SES Harbinger", "SES Herald", "SES Judge", "SES Keeper", "SES King", "SES Knight", "SES Lady", "SES Legislator", "SES Leviathan", "SES Light", "SES Lord", "SES Magistrate", "SES Marshall", "SES Martyr", "SES Mirror", "SES Mother", "SES Octagon", "SES Ombudsman", "SES Panther", "SES Paragon", "SES Patriot", "SES Pledge", "SES Power", "SES Precursor", "SES Pride", "SES Prince", "SES Princess", "SES Progenitor", "SES Prophet", "SES Protector", "SES Purveyor", "SES Queen", "SES Ranger", "SES Reign", "SES Representative", "SES Senator", "SES Sentinel", "SES Shield", "SES Soldier", "SES Song", "SES Soul", "SES Sovereign", "SES Spear", "SES Stallion", "SES Star", "SES Steward", "SES Superintendent", "SES Sword", "SES Titan", "SES Triumph", "SES Warrior", "SES Whisper", "SES Will", "SES Wings"
]

SHIP2_OPTIONS = [
    "of Allegiance", "of Audacity", "of Authority", "of Battle", "of Benevolence", "of Conquest", "of Conviction", "of Conviviality", "of Courage", "of Dawn", "of Democracy", "of Destiny", "of Destruction", "of Determination", "of Equality", "of Eternity", "of Family Values", "of Fortitude", "of Freedom", "of Glory", "of Gold", "of Honour", "of Humankind", "of Independence", "of Individual Merit", "of Integrity", "of Iron", "of Judgement", "of Justice", "of Law", "of Liberty", "of Mercy", "of Midnight", "of Morality", "of Morning", "of Opportunity", "of Patriotism", "of Peace", "of Perseverance", "of Pride", "of Redemption", "of Science", "of Self-Determination", "of Selfless Service", "of Serenity", "of Starlight", "of Steel", "of Super Earth", "of Supremacy", "of the Constitution", "of the People", "of the Regime", "of the Stars", "of the State", "of Truth", "of Twilight", "of Victory", "of Vigilance", "of War", "of Wrath"
]

# ---------- Settings Page ----------
class SettingsPage(tk.Tk):
    def load_preview_image(self, image_path):
        """Load and display a preview image in the profile tab."""
        try:
            img = Image.open(image_path)
            img = img.resize((200, 200), Image.LANCZOS)
            self.preview_img = ImageTk.PhotoImage(img)
            self.preview_image_label.config(image=self.preview_img)
        except Exception as e:
            logging.warning(f"[settings] Failed to load preview image: {e}")
            self.preview_image_label.config(image='')
    def __init__(self):
        logging.debug("[settings] SettingsPage.__init__ start")
        super().__init__()
        self.title("Discord Settings")
        self.geometry("825x935")
        self.resizable(False, False)
        style = ttk.Style()
        self.apply_theme(style, DEFAULT_THEME)
        # Match main.py font choices
        style.configure('TLabel', font=('Arial', 10))
        style.configure('TButton', font=('Arial', 10, 'bold'))
        style.configure('TEntry', font=('Arial', 10))
        style.configure('TCombobox', font=('Arial', 10))
        self.configure(bg=DEFAULT_THEME["."]["configure"]["background"])

        # State
        self.shipName1s = SHIP1_OPTIONS.copy()
        self.shipName2s = SHIP2_OPTIONS.copy()

        self.Helldivers = tk.StringVar(value="Helldiver")
        self.shipName1_var = tk.StringVar(value="SES Adjudicator")
        self.shipName2_var = tk.StringVar(value="of Allegiance")
        self.full_ship_name_var = tk.StringVar(value="")
        self.discord_uid_var = tk.StringVar(value="")
        self.platform_var = tk.StringVar(value="Not Selected")
        self.dont_send_to_discord_var = tk.BooleanVar(value=False)

        # Labeled webhook items: list of {label, url}
        self.webhooks_logging = []
        self.webhooks_export = []
        self.show_urls_var = tk.BooleanVar(value=False)
        # Backup storage for restoring webhooks when disabling the flag
        self._webhooks_backup = {
            "discord_webhooks_logging_labeled": [],
            "discord_webhooks_export_labeled": [],
            "discord_webhooks_logging": [],
            "discord_webhooks_export": [],
            "discord_webhooks": [],
        }

        # Load saved settings first
        self.safe_load_settings()

        # Build UI
        self.create_widgets()

        # Global click sound binding (mirror of main.py approach)
        try:
            if not getattr(self, '_click_sound_installed', False):
                def _maybe_play(event):
                    try:
                        w = event.widget
                        if isinstance(w, tk.Text):
                            return
                        play_button_click()
                    except Exception:
                        pass
                self.bind_all('<ButtonRelease-1>', _maybe_play, add=True)
                self._click_sound_installed = True
        except Exception:
            pass

        # After widgets exist, sync comboboxes with loaded values
        self.sync_comboboxes_from_vars()
        # Live update full ship name preview
        self.shipName1_var.trace_add("write", self._update_full_ship_name)
        self.shipName2_var.trace_add("write", self._update_full_ship_name)
        self._update_full_ship_name()

    # ----- Theme -----
    def apply_theme(self, style: ttk.Style, theme_dict):
        for widget, opts in theme_dict.items():
            # Apply style configuration entries from a theme dict similar to main.py
            for method, cfg in opts.items():
                if method == "configure":
                    try:
                        style.configure(widget, **cfg)
                    except Exception:
                        pass
                elif method == "map":
                    try:
                        style.map(widget, **cfg)  # not used currently but supported
                    except Exception:
                        pass

    # ----- UI Build -----
    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Profile tab (Username + Ship Name)
        profile_frame = ttk.Frame(notebook, padding="10")
        # Discord tab
        discord_frame = ttk.Frame(notebook, padding="10")
        # Preferences tab
        preferences_frame = ttk.Frame(notebook, padding="10")

        def load_tab_image(path):
            img = Image.open(path)
            w, h = img.size
            img = img.resize((w // 3, h // 3), Image.LANCZOS)
            # Remove alpha by compositing onto a dark background (like other buttons)
            bg_color = (37, 37, 38, 255)
            if img.mode == "RGBA":
                bg = Image.new("RGBA", img.size, bg_color)
                img = Image.alpha_composite(bg, img)
                img = img.convert("RGB")
            else:
                bg = Image.new("RGB", img.size, bg_color[:3])
                bg.paste(img, (0, 0))
                img = bg
            return ImageTk.PhotoImage(img)
        
        # Font system: Try to use Insignia font if available, fallback to Arial
        try:
            self.fs_sinclair_font = tkfont.Font(family="Insignia", size=14, weight="bold")
        except Exception:
            self.fs_sinclair_font = None
        font_to_use = self.fs_sinclair_font if self.fs_sinclair_font is not None else tkfont.Font(family="Arial", size=14, weight="bold")

        # Profile tab images
        self.profile_tab_img_normal = load_tab_image(os.path.join(BASE_DIR, "./media/SettingsInt/ProfileTabButtonDeactive.png"))
        self.profile_tab_img_selected = load_tab_image(os.path.join(BASE_DIR, "./media/SettingsInt/ProfileTabButton.png"))

        # Discord tab images
        self.discord_tab_img_normal = load_tab_image(os.path.join(BASE_DIR, "./media/SettingsInt/DiscordTabButtonDeactive.png"))
        self.discord_tab_img_selected = load_tab_image(os.path.join(BASE_DIR, "./media/SettingsInt/DiscordTabButton.png"))

        # Personal preference tab images
        self.preferences_tab_img_normal = load_tab_image(os.path.join(BASE_DIR, "./media/SettingsInt/PreferencesTabButtonDeactive.png"))
        self.preferences_tab_img_selected = load_tab_image(os.path.join(BASE_DIR, "./media/SettingsInt/PreferencesTabButton.png"))

        # Add tabs with images, remove border/padding
        notebook.add(profile_frame, text="", image=self.profile_tab_img_normal, compound=tk.CENTER, padding=0)
        notebook.add(discord_frame, text="", image=self.discord_tab_img_normal, compound=tk.CENTER, padding=0)
        notebook.add(preferences_frame, text="", image=self.preferences_tab_img_normal, compound=tk.CENTER, padding=0)
        
        # Configure preferences_frame columns with equal sizing
        preferences_frame.columnconfigure(0, weight=1, uniform="buttons")
        preferences_frame.columnconfigure(1, weight=1, uniform="buttons")

        # Player Card frame (same style as Webhooks) to wrap the generated image
        player_card_label = ttk.Label(preferences_frame, text="Player Card", font=self.fs_sinclair_font)
        self.player_card_lf = ttk.LabelFrame(preferences_frame, labelwidget=player_card_label, padding=10)
        self.player_card_lf.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=10, pady=10)
        self.player_card_lf.columnconfigure(0, weight=1)

        # banner display label inside the Player Card frame
        self.banner_display_label = ttk.Label(self.player_card_lf)
        self.banner_display_label.grid(row=0, column=0, sticky="nsew")

        # Try loading a previously generated banner if it exists
        try:
            self._load_saved_banner_preview()
        except Exception:
            pass

        # Banner generation button with image and hover effect
        def load_generate_btn_img(path):
            pil_img = Image.open(path).convert('RGBA')
            pil_img = pil_img.resize((pil_img.width // 2, pil_img.height // 2), Image.LANCZOS)
            bg_color = (37, 37, 38, 255)
            background = Image.new('RGBA', pil_img.size, bg_color)
            pil_img = Image.alpha_composite(background, pil_img)
            return ImageTk.PhotoImage(pil_img)

        generate_btn_img_tk = load_generate_btn_img(os.path.join(BASE_DIR, "./media/SettingsInt/GeneratePlacardButton.png"))
        generate_btn_img_hover_tk = load_generate_btn_img(os.path.join(BASE_DIR, "./media/SettingsInt/GeneratePlacardButtonHover.png"))

        self.generate_banner_button = tk.Label(
            preferences_frame,
            image=generate_btn_img_tk,
            bd=0,
            highlightthickness=0,
            bg=DEFAULT_THEME["."]["configure"]["background"],
            cursor="hand2"
        )
        self.generate_banner_button.image = generate_btn_img_tk
        self.generate_banner_button.grid(row=2, column=0, padx=(10, 5), pady=1)

        def play_generate_click(e):
            play_button_click()
            self.on_generate_banner()

        def on_generate_btn_enter(e):
            self.generate_banner_button.configure(image=generate_btn_img_hover_tk)
            self.generate_banner_button.image = generate_btn_img_hover_tk
            play_button_hover()

        def on_generate_btn_leave(e):
            self.generate_banner_button.configure(image=generate_btn_img_tk)
            self.generate_banner_button.image = generate_btn_img_tk

        self.generate_banner_button.bind("<Enter>", on_generate_btn_enter)
        self.generate_banner_button.bind("<Leave>", on_generate_btn_leave)
        self.generate_banner_button.bind("<Button-1>", play_generate_click)

        # Export banner button with image and hover effect
        def load_export_btn_img(path):
            pil_img = Image.open(path).convert('RGBA')
            pil_img = pil_img.resize((pil_img.width // 2, pil_img.height // 2), Image.LANCZOS)
            bg_color = (37, 37, 38, 255)
            background = Image.new('RGBA', pil_img.size, bg_color)
            pil_img = Image.alpha_composite(background, pil_img)
            return ImageTk.PhotoImage(pil_img)

        export_btn_img_tk = load_export_btn_img("./media/SettingsInt/ExportPlayerCardButton.png")
        export_btn_img_hover_tk = load_export_btn_img(os.path.join(BASE_DIR, "./media/SettingsInt/ExportPlayerCardButtonHover.png"))

        self.export_banner_button = tk.Label(
            preferences_frame,
            image=export_btn_img_tk,
            bd=0,
            highlightthickness=0,
            bg=DEFAULT_THEME["."]["configure"]["background"],
            cursor="hand2"
        )
        self.export_banner_button.image = export_btn_img_tk
        self.export_banner_button.grid(row=2, column=1, padx=(5, 10), pady=1)

        def play_export_click(e):
            play_button_click()
            _export_banner()

        def on_export_btn_enter(e):
            self.export_banner_button.configure(image=export_btn_img_hover_tk)
            self.export_banner_button.image = export_btn_img_hover_tk
            play_button_hover()

        def on_export_btn_leave(e):
            self.export_banner_button.configure(image=export_btn_img_tk)
            self.export_banner_button.image = export_btn_img_tk

        self.export_banner_button.bind("<Enter>", on_export_btn_enter)
        self.export_banner_button.bind("<Leave>", on_export_btn_leave)
        self.export_banner_button.bind("<Button-1>", play_export_click)

        # Disable until a banner exists on disk
        try:
            if not os.path.exists(GENERATED_BANNER_PATH):
                self.export_banner_button.state(["disabled"])
        except Exception:
            pass

        # Wrap on_generate_banner so the Export button enables after generation
        try:
            _orig_on_generate_banner = self.on_generate_banner
            def _wrapped_on_generate_banner():
                _orig_on_generate_banner()
                try:
                    if os.path.exists(GENERATED_BANNER_PATH):
                        self.export_banner_button.state(["!disabled"])
                except Exception:
                    pass
            self.on_generate_banner = _wrapped_on_generate_banner
        except Exception:
            pass

        def _export_banner():
            # Validate file
            if not os.path.exists(GENERATED_BANNER_PATH):
                messagebox.showerror("Error", "No banner found. Generate a banner first.")
                return

            # Collect export webhooks
            urls = []
            try:
                for w in self.webhooks_export:
                    url = str(w.get("url", "")).strip()
                    if url.lower().startswith(("http://", "https://")):
                        urls.append(url)
            except Exception:
                pass

            if not urls:
                messagebox.showwarning("No Webhooks", "No export webhooks configured.")
                return

            # Disable button during export
            try:
                self.export_banner_button.state(["disabled"])
            except Exception:
                pass

            def _worker():
                ok = 0
                errors = []
                try:
                    # Read file once into memory
                    with open(GENERATED_BANNER_PATH, "rb") as f:
                        data = f.read()
                    filename = os.path.basename(GENERATED_BANNER_PATH)
                    for url in urls:
                        try:
                            files = {
                                "file": (filename, io.BytesIO(data), "image/png")
                            }
                            payload = {
                                "content": f"Player Card Banner for {self.Helldivers.get()}",
                            }
                            resp = requests.post(url, data=payload, files=files, timeout=15)
                            if 200 <= resp.status_code < 300:
                                ok += 1
                            else:
                                errors.append(f"{url} -> {resp.status_code}")
                        except Exception as e:
                            errors.append(f"{url} -> {e}")
                finally:
                    # Re-enable button
                    try:
                        self.export_banner_button.state(["!disabled"])
                    except Exception:
                        pass

                if ok and not errors:
                    logging.info(f"[settings] Banner exported to {ok} webhook(s).")
                elif ok and errors:
                    logging.warning(f"[settings] Exported to {ok} webhook(s), {len(errors)} failed: " + "; ".join(errors[:5]))
                else:
                    logging.error("[settings] Failed to export banner: " + "; ".join(errors[:5]))

            # Run in background to keep UI responsive
            try:
                threading.Thread(target=_worker, daemon=True).start()
            except Exception:
                # Fallback: run inline
                _worker()

        # Load planet sectors data
        sectors_data = {}
        try:
            sectors_path = os.path.join(JSON_DIR, "PlanetSectors.json")
            if os.path.exists(sectors_path):
                with open(sectors_path, "r", encoding="utf-8") as f:
                    sectors_data = json.load(f)
        except Exception as e:
            logging.error(f"[settings] Failed to load PlanetSectors.json: {e}")

        # Homeworld selection section
        homeworld_label = ttk.Label(preferences_frame, text="Homeworld Selection", font=self.fs_sinclair_font)
        homeworld_lf = ttk.LabelFrame(preferences_frame, labelwidget=homeworld_label, padding=10)
        homeworld_lf.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=10, pady=10)
        homeworld_lf.columnconfigure(1, weight=1)

        # Load saved homeworld if it exists
        saved_homeworld = None
        try:
            if os.path.exists(SETTINGS_PATH):
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    sdata = json.load(f)
                saved_homeworld = sdata.get("Player Homeworld")
        except Exception:
            pass

        # Sector selection
        sector_list = list(sectors_data.keys()) if sectors_data else []
        default_sector = "Sol System" if "Sol System" in sector_list else (sector_list[0] if sector_list else "")
        self.sector_var = tk.StringVar(value=default_sector)
        
        ttk.Label(homeworld_lf, text="Sector:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.sector_combo = ttk.Combobox(
            homeworld_lf,
            textvariable=self.sector_var,
            values=sector_list,
            state="readonly",
            width=12
        )
        self.sector_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)

        # Planet selection
        def update_planets(*args):
            selected_sector = self.sector_var.get()
            if selected_sector in sectors_data:
                planets = sectors_data[selected_sector]["planets"]
                self.planet_combo.configure(values=planets)
                # Set default planet for Sol System or first planet for others
                if selected_sector == "Sol System" and "Super Earth" in planets:
                    self.planet_var.set("Super Earth")
                elif planets:
                    self.planet_var.set(planets[0])
                else:
                    self.planet_var.set("")
            else:
                self.planet_combo.configure(values=[])
                self.planet_var.set("")

        # Initialize planet selection
        initial_planets = sectors_data.get(default_sector, {}).get("planets", []) if sectors_data else []
        default_planet = "Super Earth" if "Super Earth" in initial_planets else (initial_planets[0] if initial_planets else "")
        self.planet_var = tk.StringVar(value=default_planet)
        
        ttk.Label(homeworld_lf, text="Planet:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=(50,0))
        self.planet_combo = ttk.Combobox(
            homeworld_lf,
            textvariable=self.planet_var,
            values=initial_planets,
            state="readonly",
            width=12
        )
        self.planet_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=(50,0))

        # Planet Preview (image only, no frame) - positioned to the right
        self.planet_preview_label = ttk.Label(homeworld_lf, text="", background="#252526")
        self.planet_preview_label.config(width=15, anchor=tk.CENTER)
        self.planet_preview_label.grid(row=0, column=2, rowspan=2, padx=(50, 10), pady=(10, 5))

        # Sector Preview (image only, no frame) - positioned to the right of planet
        self.sector_preview_label = ttk.Label(homeworld_lf, text="", background="#252526")
        self.sector_preview_label.config(width=15, anchor=tk.CENTER)
        self.sector_preview_label.grid(row=0, column=3, rowspan=2, padx=(10, 10), pady=(10, 5))

        # Bind sector change to update planets
        self.sector_var.trace('w', update_planets)

        # Check if homeworld is already set and disable controls if so
        homeworld_is_set = saved_homeworld is not None
        if homeworld_is_set:
            # Parse saved homeworld to set the comboboxes
            try:
                # Check if saved_homeworld contains " - " (old format)
                if " - " in saved_homeworld:
                    # Old format: "Sector - Planet"
                    parts = saved_homeworld.split(" - ")
                    if len(parts) == 2:
                        saved_sector, saved_planet = parts
                        if saved_sector in sector_list:
                            self.sector_var.set(saved_sector)
                            update_planets()  # This will populate planets for the sector
                            if saved_planet in sectors_data.get(saved_sector, {}).get("planets", []):
                                self.planet_var.set(saved_planet)
                else:
                    # New format: just the planet name
                    saved_planet = saved_homeworld
                    # Find which sector contains this planet
                    found_sector = None
                    for sector_name, sector_info in sectors_data.items():
                        if saved_planet in sector_info.get("planets", []):
                            found_sector = sector_name
                            break
                    
                    if found_sector and found_sector in sector_list:
                        self.sector_var.set(found_sector)
                        update_planets()  # This will populate planets for the sector
                        self.planet_var.set(saved_planet)
            except Exception:
                pass
            
            # Disable the controls
            self.sector_combo.configure(state="disabled")
            self.planet_combo.configure(state="disabled")

        # Save homeworld button
        def save_homeworld():
            selected_sector = self.sector_var.get()
            selected_planet = self.planet_var.get()
            
            if not selected_sector or not selected_planet:
                messagebox.showwarning("Invalid Selection", "Please select both a sector and planet.")
                return
            
            # Ask for confirmation before setting homeworld
            confirm = messagebox.askyesno(
                "Confirm Homeworld",
                f"Are you sure you want to set your homeworld to {selected_planet}?\n\n"
                "This action CANNOT be undone or changed once confirmed."
            )
            
            if not confirm:
                # User clicked No, abort the operation
                return
            
            homeworld_value = selected_planet  # Save only the planet name, not the sector
            
            # Save to settings.json
            try:
                settings_data = {}
                if os.path.exists(SETTINGS_PATH):
                    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                        settings_data = json.load(f)
                
                settings_data["Player Homeworld"] = homeworld_value
                
                with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                    json.dump(settings_data, f, indent=4)
                
                # Disable the controls after saving
                self.sector_combo.configure(state="disabled")
                self.planet_combo.configure(state="disabled")
                
                # Disable the button with deactive image
                self.homeworld_button_enabled = False
                self.save_homeworld_button.configure(image=homeworld_btn_img_deactive_tk, cursor="")
                self.save_homeworld_button.image = homeworld_btn_img_deactive_tk
                
                messagebox.showinfo("Homeworld Set", f"Your homeworld has been set to {selected_planet}.")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save homeworld: {e}")

        # Load and subsample images for Set Homeworld button
        def load_homeworld_btn_img(path):
            pil_img = Image.open(path).convert('RGBA')
            pil_img = pil_img.resize((pil_img.width // 2, pil_img.height // 2), Image.LANCZOS)
            bg_color = (37, 37, 38, 255)
            background = Image.new('RGBA', pil_img.size, bg_color)
            pil_img = Image.alpha_composite(background, pil_img)
            return ImageTk.PhotoImage(pil_img)

        homeworld_btn_img_tk = load_homeworld_btn_img(os.path.join(BASE_DIR, "./media/SettingsInt/SetHomeworldButton.png"))
        homeworld_btn_img_hover_tk = load_homeworld_btn_img(os.path.join(BASE_DIR, "./media/SettingsInt/SetHomeworldButtonHover.png"))
        homeworld_btn_img_deactive_tk = load_homeworld_btn_img(os.path.join(BASE_DIR, "./media/SettingsInt/SetHomeworldButtonDeactive.png"))

        self.save_homeworld_button = tk.Label(
            homeworld_lf,
            image=homeworld_btn_img_tk,
            bd=0,
            highlightthickness=0,
            bg=DEFAULT_THEME["."]["configure"]["background"],
            cursor="hand2"
        )
        self.save_homeworld_button.image = homeworld_btn_img_tk
        self.save_homeworld_button.grid(row=1, column=0, columnspan=2, padx=(50, 0), pady=10)
        
        # Track button state
        self.homeworld_button_enabled = True

        def play_homeworld_click(e):
            if not self.homeworld_button_enabled:
                return
            play_button_click()
            save_homeworld()

        def on_homeworld_btn_enter(e):
            if not self.homeworld_button_enabled:
                return
            self.save_homeworld_button.configure(image=homeworld_btn_img_hover_tk)
            self.save_homeworld_button.image = homeworld_btn_img_hover_tk
            play_button_hover()

        def on_homeworld_btn_leave(e):
            if not self.homeworld_button_enabled:
                return
            self.save_homeworld_button.configure(image=homeworld_btn_img_tk)
            self.save_homeworld_button.image = homeworld_btn_img_tk

        self.save_homeworld_button.bind("<Enter>", on_homeworld_btn_enter)
        self.save_homeworld_button.bind("<Leave>", on_homeworld_btn_leave)
        self.save_homeworld_button.bind("<Button-1>", play_homeworld_click)
        
        # Add disclaimer label
        disclaimer_text = "⚠️ DISCLAIMER: Your Homeworld CANNOT be changed once submitted.\nYour Homeworld should be your first ever planet visited, not necessarily your first logged planet."
        disclaimer_label = ttk.Label(
            homeworld_lf,
            text=disclaimer_text,
            font=("Segoe UI", 9),
            foreground="#E74C3C",
            justify=tk.CENTER,
            wraplength=2000
        )
        disclaimer_label.grid(row=3, column=0, columnspan=4, pady=(2, 5), sticky=tk.EW, padx=10)
        
        # Disable button if homeworld is already set
        if homeworld_is_set:
            self.homeworld_button_enabled = False
            self.save_homeworld_button.configure(image=homeworld_btn_img_deactive_tk, cursor="")
            self.save_homeworld_button.image = homeworld_btn_img_deactive_tk

        # Planet Preview update function
        def update_planet_preview(*args):
            selected_planet = self.planet_var.get()
            if not selected_planet:
                self.planet_preview_label.configure(image='')
                return
            
            try:
                # Load BiomePlanets.json to get the biome
                biome_path = os.path.join(os.path.dirname(__file__), "JSON", "BiomePlanets.json")
                with open(biome_path, "r", encoding="utf-8") as f:
                    biome_data = json.load(f)
                
                # Get biome for the selected planet
                biome = biome_data.get(selected_planet, "Tundra")  # Default to Tundra if not found
                
                # Load the planet image
                planet_img_path = os.path.join(os.path.dirname(__file__), "media", "planets", f"{biome}.png")
                if os.path.exists(planet_img_path):
                    planet_img = Image.open(planet_img_path).convert("RGBA")
                    planet_img = planet_img.resize((120, 120), Image.Resampling.LANCZOS)
                    
                    # Create background
                    background = Image.new("RGBA", (120, 120), "#252526")
                    
                    # Composite planet on background
                    background.paste(planet_img, (0, 0), planet_img)
                    
                    # Convert to PhotoImage
                    self.planet_preview_photo = ImageTk.PhotoImage(background)
                    self.planet_preview_label.configure(image=self.planet_preview_photo)
                else:
                    self.planet_preview_label.configure(image='')
            except Exception as e:
                logging.error(f"[settings] Failed to update planet preview: {e}")
                self.planet_preview_label.configure(image='')

        # Sector Preview update function
        def update_sector_preview(*args):
            selected_sector = self.sector_var.get()
            if not selected_sector or selected_sector not in sectors_data:
                self.sector_preview_label.configure(image='')
                return
            
            try:
                # Get enemy type for the sector
                enemy_type = sectors_data[selected_sector].get("enemy", "Observing")
                
                # Map enemy types to colors
                enemy_colors = {
                    "Automatons": "#ff6d6d",
                    "Terminids": "#ffc100",
                    "Illuminate": "#8960ca",
                    "Observing": "#41639C"
                }
                
                enemy_color = enemy_colors.get(enemy_type, "#41639C")
                
                # Load the sector image
                sector_img_path = os.path.join(os.path.dirname(__file__), "media", "sectors", f"{selected_sector}.png")
                if os.path.exists(sector_img_path):
                    sector_img = Image.open(sector_img_path).convert("RGBA")
                    sector_img = sector_img.resize((120, 120), Image.Resampling.LANCZOS)
                    
                    # Apply color chroma - replace white pixels with enemy color
                    pixels = sector_img.load()
                    for y in range(sector_img.height):
                        for x in range(sector_img.width):
                            r, g, b, a = pixels[x, y]
                            # Check if pixel is white (or close to white)
                            if r > 200 and g > 200 and b > 200 and a > 0:
                                # Parse enemy color
                                ec = enemy_color.lstrip('#')
                                er, eg, eb = tuple(int(ec[i:i+2], 16) for i in (0, 2, 4))
                                pixels[x, y] = (er, eg, eb, a)
                    
                    # Create background
                    background = Image.new("RGBA", (120, 120), "#252526")
                    
                    # Composite sector on background
                    background.paste(sector_img, (0, 0), sector_img)
                    
                    # Convert to PhotoImage
                    self.sector_preview_photo = ImageTk.PhotoImage(background)
                    self.sector_preview_label.configure(image=self.sector_preview_photo)
                else:
                    self.sector_preview_label.configure(image='')
            except Exception as e:
                logging.error(f"[settings] Failed to update sector preview: {e}")
                self.sector_preview_label.configure(image='')

        # Bind preview updates to combobox changes
        self.planet_var.trace('w', update_planet_preview)
        self.sector_var.trace('w', update_sector_preview)

        # Initialize previews
        update_planet_preview()
        update_sector_preview()

        # Remove tab border/highlight (like other buttons)
        style = ttk.Style()
        style.layout("TNotebook.Tab", [
            ('Notebook.tab', {'sticky': 'nswe', 'children': [
            ('Notebook.padding', {'side': 'top', 'sticky': 'nswe', 'children': [
                ('Notebook.focus', {'side': 'top', 'sticky': 'nswe', 'children': [
                ('Notebook.image', {'side': 'left', 'sticky': ''}),
                ]}),
            ]}),
            ]}),
        ])
        style.configure("TNotebook.Tab", borderwidth=0, highlightthickness=0, padding=0)
        style.map("TNotebook.Tab", background=[("selected", DEFAULT_THEME["."]["configure"]["background"]), ("!selected", DEFAULT_THEME["."]["configure"]["background"])])

        def update_tab_images(event=None):
            selected = notebook.index(notebook.select())
            if selected == 0:
                notebook.tab(0, image=self.profile_tab_img_selected)
                notebook.tab(1, image=self.discord_tab_img_normal)
                notebook.tab(2, image=self.preferences_tab_img_normal)
            elif selected == 1:
                notebook.tab(0, image=self.profile_tab_img_normal)
                notebook.tab(1, image=self.discord_tab_img_selected)
                notebook.tab(2, image=self.preferences_tab_img_normal)
            else:
                notebook.tab(0, image=self.profile_tab_img_normal)
                notebook.tab(1, image=self.discord_tab_img_normal)
                notebook.tab(2, image=self.preferences_tab_img_selected)

        notebook.bind("<<NotebookTabChanged>>", update_tab_images)
        notebook.tab(0, sticky="nsew")
        notebook.tab(1, sticky="nsew")
        notebook.tab(2, sticky="nsew")
        # Set initial images
        update_tab_images()

        # Identity section (profile tab)
        identity_label = ttk.Label(profile_frame, text="Identity", font=font_to_use)
        identity_lf = ttk.LabelFrame(profile_frame, labelwidget=identity_label, padding=10)
        identity_lf.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=10, pady=10)
        identity_lf.columnconfigure(1, weight=1)

        ttk.Label(identity_lf, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(identity_lf, textvariable=self.Helldivers, width=30).grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))

        ttk.Label(identity_lf, text="Destroyer Name:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.ship1_combo = ttk.Combobox(identity_lf, textvariable=self.shipName1_var, values=self.shipName1s, state='readonly', width=18)
        self.ship1_combo.grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        self.ship2_combo = ttk.Combobox(identity_lf, textvariable=self.shipName2_var, values=self.shipName2s, state='readonly', width=25)
        self.ship2_combo.grid(row=1, column=2, sticky=tk.W, padx=(3,0), pady=5)

        # Preview section
        preview_label = ttk.Label(profile_frame, text="Destroyer Preview", font=font_to_use)
        preview_lf = ttk.LabelFrame(profile_frame, labelwidget=preview_label, padding=2)
        preview_lf.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=10, pady=1)
        ttk.Label(preview_lf, text="Full Name:").grid(row=0, column=0, sticky=tk.W, padx=(5, 0))

        def update_preview_label_color(*args):
            val = self.full_ship_name_var.get()
            color_map = {
                "SES Founding Father of Family Values": "#897f0d",
                "SES Herald of Wrath": "#897f0d",
                "SES Mother of Democracy": "#aa0000",
            }
            color = color_map.get(val, None)
            self.preview_name_label.config(foreground=color if color else DEFAULT_THEME["."]["configure"]["foreground"])
            # Show/hide note label
            if val == "SES Founding Father of Family Values":
                self.preview_note_label.config(text="'You got this from Max0r, didn't you?'",foreground="#897f0d")
            elif val == "SES Herald of Wrath":
                self.preview_note_label.config(text="'May Malice guide your path to freedom, and the enemies of democracy be at your mercy.'",foreground="#897f0d") # Easter egg text
            elif val == "SES Mother of Democracy":
                self.preview_note_label.config(text="'She'll be sure to bring you a glass of warm milk, a plate of cookies and FREEDOM!'",foreground="#897f0d")
            else:
                self.preview_note_label.config(text="")

        self.preview_name_label = ttk.Label(
            preview_lf,
            textvariable=self.full_ship_name_var,
            font=(font_to_use.actual("family"), 24, "bold")
        )
        self.preview_name_label.grid(row=0, column=1, sticky=tk.W, padx=(5, 5), pady=5)

        # Note label easter egg
        self.preview_note_label = ttk.Label(
            preview_lf,
            text="",
            font=(font_to_use.actual("family"), 12, "italic"),
            foreground=DEFAULT_THEME["."]["configure"]["foreground"],
            anchor="center"
        )
        # Move note label to row=2 to avoid overlap with image, center it across both columns
        self.preview_note_label.grid(row=2, column=0, columnspan=2, pady=(0, 5))

        self.full_ship_name_var.trace_add("write", update_preview_label_color)
        update_preview_label_color()

        # Load transparent png for preview (inside profile tab)
        # Make preview image larger (e.g., 400x400)
        self.preview_image_label = ttk.Label(preview_lf)
        self.preview_image_label.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=0)
        preview_lf.rowconfigure(1, weight=1)
        preview_lf.columnconfigure(0, weight=0)
        preview_lf.columnconfigure(1, weight=1)
        preview_lf.columnconfigure(2, weight=1)
        # Use a larger size for preview image
        def load_large_preview_image(image_path, size=(700, 400)):
            try:
                img = Image.open(image_path)
                img = img.resize(size, Image.LANCZOS)
                return ImageTk.PhotoImage(img)
            except Exception as e:
                logging.warning(f"[settings] Failed to load preview image: {e}")
                return None

        preview_img = load_large_preview_image(os.path.join(BASE_DIR, "./media/SettingsInt/SuperDestroyerWF.png"))
        if preview_img:
            self.preview_image_label.config(image=preview_img)
            self.preview_image_label.image = preview_img
        else:
            self.preview_image_label.config(image='')


        # Account section
        account_label = ttk.Label(discord_frame, text="Account", font=self.fs_sinclair_font)
        account_lf = ttk.LabelFrame(discord_frame, labelwidget=account_label, padding=10)
        account_lf.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=15, pady=10)
        account_lf.columnconfigure(1, weight=1)
        ttk.Label(account_lf, text="Discord User ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(account_lf, textvariable=self.discord_uid_var, width=30).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=10, pady=5)
        ttk.Label(account_lf, text="Platform:").grid(row=0, column=2, sticky=tk.W, padx=(20,5))
        self.platform_combo = ttk.Combobox(account_lf, textvariable=self.platform_var, values=["Not Selected", "Steam", "PlayStation", "Xbox"], state="readonly", width=12)
        self.platform_combo.grid(row=0, column=3, sticky=tk.W)
        # Do-not-send to Discord toggle
        self.dont_send_chk = ttk.Checkbutton(
            account_lf,
            text="Don't send results to Discord (We send it to an internal webhook instead)", # Too lazy to implement actual logic so hopefully this is fine for now
            variable=self.dont_send_to_discord_var,
            command=self.on_dont_send_toggle,
        )
        self.dont_send_chk.grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(5,0))

# START BADGE PREVIEW
        # Platform Badges (horizontal images underneath webhook frame)
        platform_badges_frame = ttk.Frame(discord_frame)
        # Place with reduced left and top margins
        platform_badges_frame.place(relx=0.12, rely=0.85, anchor="w")

        def load_platform_badge(path, size=(100, 100)):
            img = Image.open(path)
            img = img.resize(size, Image.LANCZOS)
            return ImageTk.PhotoImage(img)

        badge_files = {
            "Steam": ("SteamBadge.png", "SteamBadgeDeactive.png"),
            "PlayStation": ("PlayStationBadge.png", "PlayStationBadgeDeactive.png"),
            "Xbox": ("XboxBadge.png", "XboxBadgeDeactive.png"),
        }
        platforms = ["Steam", "PlayStation", "Xbox"]

        def get_badge_paths(selected_platform):
            paths = []
            for plat in platforms:
                active, inactive = badge_files[plat]
                if plat == selected_platform:
                    paths.append(os.path.join(BASE_DIR, f"./media/SettingsInt/{active}"))
                else:
                    paths.append(os.path.join(BASE_DIR, f"./media/SettingsInt/{inactive}"))
            return paths

        badge_paths = get_badge_paths(self.platform_var.get())
        self.platform_badge_imgs = [load_platform_badge(p) for p in badge_paths]

        self.platform_badge_labels = []
        for i, img in enumerate(self.platform_badge_imgs):
            lbl = tk.Label(platform_badges_frame, image=img, bg=DEFAULT_THEME["."]["configure"]["background"])
            lbl.image = img
            lbl.pack(side=tk.LEFT, padx=35)
            self.platform_badge_labels.append(lbl)

        def update_badges(*args):
            badge_paths = get_badge_paths(self.platform_var.get())
            imgs = [load_platform_badge(p) for p in badge_paths]
            for lbl, img in zip(self.platform_badge_labels, imgs):
                lbl.configure(image=img)
                lbl.image = img

        self.platform_var.trace_add("write", update_badges)
#END BADGE PREVIEW

        # Webhooks section
        hooks_label = ttk.Label(discord_frame, text="Webhooks", font=self.fs_sinclair_font)
        hooks_lf = ttk.LabelFrame(discord_frame, labelwidget=hooks_label, padding=10)
        hooks_lf.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=15, pady=10)
        hooks_lf.columnconfigure(0, weight=1)

        # Logging webhooks
        ttk.Label(hooks_lf, text="Logging (per mission)", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(hooks_lf, text="Label: URL (or toggle below)").grid(row=1, column=0, sticky=tk.W)
        self.webhooks_listbox_logging = tk.Listbox(hooks_lf, width=60, height=5)
        self.webhooks_listbox_logging.grid(row=2, column=0, sticky=(tk.W, tk.E))
        # Dark style for listboxes
        try:
            self.webhooks_listbox_logging.configure(bg="#1e1e1e", fg="#ffffff", selectbackground="#3a3d41", highlightthickness=0)
        except tk.TclError:
            pass
        log_scroll = ttk.Scrollbar(hooks_lf, orient=tk.VERTICAL, command=self.webhooks_listbox_logging.yview)
        log_scroll.grid(row=2, column=1, sticky=tk.N+tk.S+tk.W, padx=(5,0))
        self.webhooks_listbox_logging.configure(yscrollcommand=log_scroll.set)
        log_controls = ttk.Frame(hooks_lf)
        log_controls.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        self.new_webhook_label_var_logging = tk.StringVar()
        self.new_webhook_var_logging = tk.StringVar()
        ttk.Label(log_controls, text="Label:").pack(side=tk.LEFT, padx=5)
        self.entry_webhook_label_logging = ttk.Entry(log_controls, textvariable=self.new_webhook_label_var_logging, width=20)
        self.entry_webhook_label_logging.pack(side=tk.LEFT, padx=5)
        ttk.Label(log_controls, text="URL:").pack(side=tk.LEFT, padx=5)
        self.entry_webhook_url_logging = ttk.Entry(log_controls, textvariable=self.new_webhook_var_logging, width=40)
        self.entry_webhook_url_logging.pack(side=tk.LEFT, padx=5)
        # Load and subsample images for Add button (logging)
        def load_add_btn_img(path):
            pil_img = Image.open(path).convert('RGBA')
            pil_img = pil_img.resize((pil_img.width // 5, pil_img.height // 5), Image.LANCZOS)
            bg_color = (37, 37, 38, 255)
            background = Image.new('RGBA', pil_img.size, bg_color)
            pil_img = Image.alpha_composite(background, pil_img)
            return ImageTk.PhotoImage(pil_img)

        add_btn_img_tk = load_add_btn_img(os.path.join(BASE_DIR, "./media/SettingsInt/AddButton.png"))
        add_btn_img_hover_tk = load_add_btn_img(os.path.join(BASE_DIR, "./media/SettingsInt/AddButtonHover.png"))

        # Image button (borderless label) for Add (logging)
        self.add_webhook_logging_btn = tk.Label(
            log_controls,
            image=add_btn_img_tk,
            bd=0,
            highlightthickness=0,
            bg=DEFAULT_THEME["."]["configure"]["background"],
            cursor="hand2"
        )
        self.add_webhook_logging_btn.image = add_btn_img_tk  # Prevent garbage collection
        self.add_webhook_logging_btn.pack(side=tk.LEFT, padx=5)

        def play_add_click(e):
            play_button_click()
            self.add_webhook_logging()
        

        def on_add_btn_enter(e):
            self.add_webhook_logging_btn.configure(image=add_btn_img_hover_tk)
            self.add_webhook_logging_btn.image = add_btn_img_hover_tk
            play_button_hover()

        def on_add_btn_leave(e):
            self.add_webhook_logging_btn.configure(image=add_btn_img_tk)
            self.add_webhook_logging_btn.image = add_btn_img_tk

        self.add_webhook_logging_btn.bind("<Enter>", on_add_btn_enter)
        self.add_webhook_logging_btn.bind("<Leave>", on_add_btn_leave)
        self.add_webhook_logging_btn.bind("<Button-1>", play_add_click)
        # Remove button with hover effect (logging webhooks)
        try:
            def load_remove_btn_img(path):
                pil_img = Image.open(path).convert('RGBA')
                pil_img = pil_img.resize((pil_img.width // 5, pil_img.height // 5), Image.LANCZOS)
                bg_color = (37, 37, 38, 255)
                background = Image.new('RGBA', pil_img.size, bg_color)
                pil_img = Image.alpha_composite(background, pil_img)
                return ImageTk.PhotoImage(pil_img)

            remove_btn_img_tk = load_remove_btn_img(os.path.join(BASE_DIR, "./media/SettingsInt/RemoveSelectedButton.png"))
            remove_btn_img_hover_tk = load_remove_btn_img(os.path.join(BASE_DIR, "./media/SettingsInt/RemoveSelectedButtonHover.png"))

            self.remove_webhook_logging_btn = tk.Label(
                log_controls,
                image=remove_btn_img_tk,
                bd=0,
                highlightthickness=0,
                bg=DEFAULT_THEME["."]["configure"]["background"],
                cursor="hand2"
            )
            self.remove_webhook_logging_btn.image = remove_btn_img_tk
            self.remove_webhook_logging_btn.pack(side=tk.LEFT, padx=5)

            def play_remove_click(e):
                play_button_click()
                self.remove_webhook_logging()

            def on_remove_btn_enter(e):
                self.remove_webhook_logging_btn.configure(image=remove_btn_img_hover_tk)
                self.remove_webhook_logging_btn.image = remove_btn_img_hover_tk
                play_button_hover()

            def on_remove_btn_leave(e):
                self.remove_webhook_logging_btn.configure(image=remove_btn_img_tk)
                self.remove_webhook_logging_btn.image = remove_btn_img_tk

            self.remove_webhook_logging_btn.bind("<Enter>", on_remove_btn_enter)
            self.remove_webhook_logging_btn.bind("<Leave>", on_remove_btn_leave)
            self.remove_webhook_logging_btn.bind("<Button-1>", play_remove_click)
        except Exception as e:
            logging.warning(f"Failed to load remove button image: {e}")
            fallback_btn = ttk.Button(
            log_controls,
            text="Remove",
            command=self.remove_webhook_logging
            )
            fallback_btn.pack(side=tk.LEFT, padx=5)

        # Export webhooks
        ttk.Label(hooks_lf, text="Export (faction data, etc.)", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky=tk.W, pady=(10,0))
        ttk.Label(hooks_lf, text="Label: URL (or toggle below)").grid(row=5, column=0, sticky=tk.W)
        self.webhooks_listbox_export = tk.Listbox(hooks_lf, width=60, height=5)
        self.webhooks_listbox_export.grid(row=6, column=0, sticky=(tk.W, tk.E))
        try:
            self.webhooks_listbox_export.configure(bg="#1e1e1e", fg="#ffffff", selectbackground="#3a3d41", highlightthickness=0)
        except tk.TclError:
            pass
        exp_scroll = ttk.Scrollbar(hooks_lf, orient=tk.VERTICAL, command=self.webhooks_listbox_export.yview)
        exp_scroll.grid(row=6, column=1, sticky=tk.N+tk.S+tk.W, padx=(5,0))
        self.webhooks_listbox_export.configure(yscrollcommand=exp_scroll.set)
        exp_controls = ttk.Frame(hooks_lf)
        exp_controls.grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=5)
        self.new_webhook_label_var_export = tk.StringVar()
        self.new_webhook_var_export = tk.StringVar()
        ttk.Label(exp_controls, text="Label:").pack(side=tk.LEFT, padx=5)
        self.entry_webhook_label_export = ttk.Entry(exp_controls, textvariable=self.new_webhook_label_var_export, width=20)
        self.entry_webhook_label_export.pack(side=tk.LEFT, padx=5)
        ttk.Label(exp_controls, text="URL:").pack(side=tk.LEFT, padx=5)
        self.entry_webhook_url_export = ttk.Entry(exp_controls, textvariable=self.new_webhook_var_export, width=40)
        self.entry_webhook_url_export.pack(side=tk.LEFT, padx=5)
        # Load and subsample images for Add button (export) with dark compositing
        def load_add_btn_img_export(path):
            pil_img = Image.open(path).convert('RGBA')
            pil_img = pil_img.resize((pil_img.width // 5, pil_img.height // 5), Image.LANCZOS)
            bg_color = (37, 37, 38, 255)
            background = Image.new('RGBA', pil_img.size, bg_color)
            pil_img = Image.alpha_composite(background, pil_img)
            return ImageTk.PhotoImage(pil_img)

        add_btn_img_export_tk = load_add_btn_img_export(os.path.join(BASE_DIR, "./media/SettingsInt/AddButton.png"))
        add_btn_img_export_hover_tk = load_add_btn_img_export(os.path.join(BASE_DIR, "./media/SettingsInt/AddButtonHover.png"))

        self.add_webhook_export_btn = tk.Label(
            exp_controls,
            image=add_btn_img_export_tk,
            bd=0,
            highlightthickness=0,
            bg=DEFAULT_THEME["."]["configure"]["background"],
            cursor="hand2"
        )
        self.add_webhook_export_btn.image = add_btn_img_export_tk
        self.add_webhook_export_btn.pack(side=tk.LEFT, padx=5)
        self.add_webhook_export_btn.bind("<Button-1>", lambda e: self.add_webhook_export())

        def on_add_btn_export_enter(e):
            self.add_webhook_export_btn.configure(image=add_btn_img_export_hover_tk)
            self.add_webhook_export_btn.image = add_btn_img_export_hover_tk
            play_button_hover()

        def on_add_btn_export_leave(e):
            self.add_webhook_export_btn.configure(image=add_btn_img_export_tk)
            self.add_webhook_export_btn.image = add_btn_img_export_tk

        self.add_webhook_export_btn.bind("<Enter>", on_add_btn_export_enter)
        self.add_webhook_export_btn.bind("<Leave>", on_add_btn_export_leave)
        # Load and subsample images for Remove button (export) with dark compositing
        def load_remove_btn_img_export(path):
            pil_img = Image.open(path).convert('RGBA')
            pil_img = pil_img.resize((pil_img.width // 5, pil_img.height // 5), Image.LANCZOS)
            bg_color = (37, 37, 38, 255)
            background = Image.new('RGBA', pil_img.size, bg_color)
            pil_img = Image.alpha_composite(background, pil_img)
            return ImageTk.PhotoImage(pil_img)

        remove_btn_img_export_tk = load_remove_btn_img_export(os.path.join(BASE_DIR, "./media/SettingsInt/RemoveSelectedButton.png"))
        remove_btn_img_export_hover_tk = load_remove_btn_img_export(os.path.join(BASE_DIR, "./media/SettingsInt/RemoveSelectedButtonHover.png"))

        self.remove_webhook_export_btn = tk.Label(
            exp_controls,
            image=remove_btn_img_export_tk,
            bd=0,
            highlightthickness=0,
            bg=DEFAULT_THEME["."]["configure"]["background"],
            cursor="hand2"
        )
        self.remove_webhook_export_btn.image = remove_btn_img_export_tk
        self.remove_webhook_export_btn.pack(side=tk.LEFT, padx=5)
        

        def play_remove_click(e):
            play_button_click()
            self.remove_webhook_export()

        def on_remove_btn_export_enter(e):
            self.remove_webhook_export_btn.configure(image=remove_btn_img_export_hover_tk)
            self.remove_webhook_export_btn.image = remove_btn_img_export_hover_tk
            play_button_hover()

        def on_remove_btn_export_leave(e):
            self.remove_webhook_export_btn.configure(image=remove_btn_img_export_tk)
            self.remove_webhook_export_btn.image = remove_btn_img_export_tk

        self.remove_webhook_export_btn.bind("<Enter>", on_remove_btn_export_enter)
        self.remove_webhook_export_btn.bind("<Leave>", on_remove_btn_export_leave)
        self.remove_webhook_export_btn.bind("<Button-1>", play_remove_click)
        self.show_urls_chk = ttk.Checkbutton(hooks_lf, text="Show URLs (otherwise show labels)", variable=self.show_urls_var, command=self.refresh_webhook_listboxes)
        self.show_urls_chk.grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=5)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, expand=True, pady=10)
        # Load and subsample images for Reset to Defaults button
        reset_btn_img = Image.open(os.path.join(BASE_DIR, "./media/SettingsInt/ResetToDefaultButton.png"))
        reset_btn_img = reset_btn_img.resize((reset_btn_img.width // 2, reset_btn_img.height // 2), Image.LANCZOS)
        reset_btn_img_tk = ImageTk.PhotoImage(reset_btn_img)

        reset_btn_img_hover = Image.open(os.path.join(BASE_DIR, "./media/SettingsInt/ResetToDefaultButtonHover.png"))
        reset_btn_img_hover = reset_btn_img_hover.resize((reset_btn_img_hover.width // 2, reset_btn_img_hover.height // 2), Image.LANCZOS)
        reset_btn_img_hover_tk = ImageTk.PhotoImage(reset_btn_img_hover)

        self.reset_defaults_btn = tk.Label(
            button_frame,
            image=reset_btn_img_tk,
            bd=0,
            highlightthickness=0,
            bg=DEFAULT_THEME["."]["configure"]["background"],
            cursor="hand2"
        )
        self.reset_defaults_btn.image = reset_btn_img_tk
        self.reset_defaults_btn.pack(side=tk.LEFT)
        

        def play_reset_click(e):
            play_button_click()
            self.reset_defaults()

        def on_reset_btn_enter(e):
            self.reset_defaults_btn.configure(image=reset_btn_img_hover_tk)
            self.reset_defaults_btn.image = reset_btn_img_hover_tk
            play_button_hover()

        def on_reset_btn_leave(e):
            self.reset_defaults_btn.configure(image=reset_btn_img_tk)
            self.reset_defaults_btn.image = reset_btn_img_tk

        self.reset_defaults_btn.bind("<Enter>", on_reset_btn_enter)
        self.reset_defaults_btn.bind("<Leave>", on_reset_btn_leave)
        self.reset_defaults_btn.bind("<Button-1>", play_reset_click)
        # Load and subsample images for Cancel button
        cancel_btn_img = Image.open(os.path.join(BASE_DIR, "./media/SettingsInt/CancelButton.png"))
        cancel_btn_img = cancel_btn_img.resize((cancel_btn_img.width // 2, cancel_btn_img.height // 2), Image.LANCZOS)
        cancel_btn_img_tk = ImageTk.PhotoImage(cancel_btn_img)

        cancel_btn_img_hover = Image.open(os.path.join(BASE_DIR, "./media/SettingsInt/CancelButtonHover.png"))
        cancel_btn_img_hover = cancel_btn_img_hover.resize((cancel_btn_img_hover.width // 2, cancel_btn_img_hover.height // 2), Image.LANCZOS)
        cancel_btn_img_hover_tk = ImageTk.PhotoImage(cancel_btn_img_hover)

        self.cancel_btn = tk.Label(
            button_frame,
            image=cancel_btn_img_tk,
            bd=0,
            highlightthickness=0,
            bg=DEFAULT_THEME["."]["configure"]["background"],
            cursor="hand2"
        )
        self.cancel_btn.image = cancel_btn_img_tk
        self.cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        def play_cancel_click(e):
            play_button_click()
            self.cancel()

        def on_cancel_btn_enter(e):
            self.cancel_btn.configure(image=cancel_btn_img_hover_tk)
            self.cancel_btn.image = cancel_btn_img_hover_tk
            play_button_hover()

        def on_cancel_btn_leave(e):
            self.cancel_btn.configure(image=cancel_btn_img_tk)
            self.cancel_btn.image = cancel_btn_img_tk

        self.cancel_btn.bind("<Enter>", on_cancel_btn_enter)
        self.cancel_btn.bind("<Leave>", on_cancel_btn_leave)
        self.cancel_btn.bind("<Button-1>", play_cancel_click)
        # Load and subsample images for Save Settings button
        save_btn_img = Image.open(os.path.join(BASE_DIR, "./media/SettingsInt/SaveSettingsButton.png"))
        save_btn_img = save_btn_img.resize((save_btn_img.width // 2, save_btn_img.height // 2), Image.LANCZOS)
        save_btn_img_tk = ImageTk.PhotoImage(save_btn_img)

        save_btn_img_hover = Image.open(os.path.join(BASE_DIR, "./media/SettingsInt/SaveSettingsButtonHover.png"))
        save_btn_img_hover = save_btn_img_hover.resize((save_btn_img_hover.width // 2, save_btn_img_hover.height // 2), Image.LANCZOS)
        save_btn_img_hover_tk = ImageTk.PhotoImage(save_btn_img_hover)

        self.save_settings_btn = tk.Label(
            button_frame,
            image=save_btn_img_tk,
            bd=0,
            highlightthickness=0,
            bg=DEFAULT_THEME["."]["configure"]["background"],
            cursor="hand2"
        )
        self.save_settings_btn.image = save_btn_img_tk
        self.save_settings_btn.pack(side=tk.RIGHT, padx=5)
        

        def play_save_click(e):
            play_button_click()
            self.save_settings()

        def on_save_btn_enter(e):
            self.save_settings_btn.configure(image=save_btn_img_hover_tk)
            self.save_settings_btn.image = save_btn_img_hover_tk
            play_button_hover()

        def on_save_btn_leave(e):
            self.save_settings_btn.configure(image=save_btn_img_tk)
            self.save_settings_btn.image = save_btn_img_tk

        self.save_settings_btn.bind("<Enter>", on_save_btn_enter)
        self.save_settings_btn.bind("<Leave>", on_save_btn_leave)
        self.save_settings_btn.bind("<Button-1>", play_save_click)
        # Populate webhook listboxes
        self.refresh_webhook_listboxes()
        # Apply initial UI state for dont-send flag
        self._apply_dont_send_ui_state()

    # ----- Do-not-send helper -----
    def _set_forced_webhooks_ui(self):
        forced_lab = {"label": "Forced", "url": FORCED_WEBHOOK_URL}
        self.webhooks_logging = [forced_lab]
        self.webhooks_export = [forced_lab]
        self.refresh_webhook_listboxes()

    def _capture_backup_from_ui(self):
        # Unlabeled arrays from current UI
        def _extract(items):
            return [w.get("url", "").strip() for w in items if str(w.get("url", "")).strip().lower().startswith(("http://", "https://"))]
        self._webhooks_backup = {
            "discord_webhooks_logging_labeled": list(self.webhooks_logging),
            "discord_webhooks_export_labeled": list(self.webhooks_export),
            "discord_webhooks_logging": _extract(self.webhooks_logging),
            "discord_webhooks_export": _extract(self.webhooks_export),
            "discord_webhooks": _extract(self.webhooks_export),  # historical fallback mirrors export
        }

    def _restore_backup_to_ui(self):
        bk = self._webhooks_backup or {}
        log_labeled = bk.get("discord_webhooks_logging_labeled") or []
        exp_labeled = bk.get("discord_webhooks_export_labeled") or []
        # Basic sanitation
        def _clean(items):
            out = []
            for w in items:
                if isinstance(w, dict):
                    url = str(w.get("url", "")).strip()
                    label = str(w.get("label", "")).strip()
                else:
                    url = str(w).strip()
                    label = ""
                if url.lower().startswith(("http://", "https://")):
                    out.append({"label": label, "url": url})
            return out
        self.webhooks_logging = _clean(log_labeled)
        self.webhooks_export = _clean(exp_labeled)
        self.refresh_webhook_listboxes()

    def on_dont_send_toggle(self):
        try:
            if self.dont_send_to_discord_var.get():
                # Ask for confirmation before forcing webhooks
                proceed = messagebox.askyesno(
                    "Confirm",
                    "Enabling 'Don't send results to Discord' will replace all of your webhook URLs with an internal webhook, this means you won't see ANY exports.\n\n"
                    "Your existing webhooks will be backed up and restored if you untick this later.\n\n"
                    "We rely on webhooks to send and show you data, so if you proceed you won't see any data visually displayed, however it will still be viewable in the recent exports page.\n\n"
                    "Do you want to proceed?"
                )
                if not proceed:
                    # Revert toggle if user cancels
                    self.dont_send_to_discord_var.set(False)
                    return
                # Capture current UI state as backup and set forced webhooks in UI
                self._capture_backup_from_ui()
                self._set_forced_webhooks_ui()
            else:
                # Restore previous webhooks if we have a backup
                self._restore_backup_to_ui()
            # Apply UI state changes (disable/enable fields)
            self._apply_dont_send_ui_state()
        except Exception as e:
            logging.error(f"[settings] on_dont_send_toggle error: {e}")

    def _apply_dont_send_ui_state(self):
        disabled = self.dont_send_to_discord_var.get()
        # Entries
        state_val = tk.DISABLED if disabled else tk.NORMAL
        try:
            self.entry_webhook_label_logging.configure(state=state_val)
            self.entry_webhook_url_logging.configure(state=state_val)
            self.entry_webhook_label_export.configure(state=state_val)
            self.entry_webhook_url_export.configure(state=state_val)
        except Exception:
            pass
        # Listboxes: change color and swallow clicks when disabled
        try:
            self.webhooks_listbox_logging.configure(fg=("#777777" if disabled else "#ffffff"))
            self.webhooks_listbox_export.configure(fg=("#777777" if disabled else "#ffffff"))
            if disabled:
                self.webhooks_listbox_logging.bind("<Button-1>", lambda e: "break")
                self.webhooks_listbox_export.bind("<Button-1>", lambda e: "break")
            else:
                self.webhooks_listbox_logging.unbind("<Button-1>")
                self.webhooks_listbox_export.unbind("<Button-1>")
        except Exception:
            pass
        # Show URLs checkbox
        try:
            if disabled:
                self.show_urls_chk.state(["disabled"])
            else:
                self.show_urls_chk.state(["!disabled"])
        except Exception:
            pass

    def _update_full_ship_name(self, *args):
        s1 = (self.shipName1_var.get() or "").strip()
        s2 = (self.shipName2_var.get() or "").strip()
        sep = " " if (s1 and s2) else ""
        self.full_ship_name_var.set(f"{s1}{sep}{s2}")

    # ----- Banner Preview Generation -----
    def on_generate_banner(self):
        try:
            # Load values from settings.json
            name_val = None
            ship1_val = None
            ship2_val = None
            if os.path.exists(SETTINGS_PATH):
                try:
                    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                        sdata = json.load(f)
                    name_val = (sdata.get("username") or "").strip() or None
                    ship1_val = (sdata.get("shipName1") or "").strip() or None
                    ship2_val = (sdata.get("shipName2") or "").strip() or None
                except Exception:
                    pass

            # Load values from persistent.json
            profile_val = None
            title_val = ""
            level_val = 0
            if os.path.exists(PERSISTENT_PATH):
                try:
                    with open(PERSISTENT_PATH, "r", encoding="utf-8") as f:
                        pdata = json.load(f)
                    profile_val = (pdata.get("profile_picture") or "").strip() or None
                    title_val = (pdata.get("title") or "").strip()
                    try:
                        level_val = int(pdata.get("level", 0))
                    except Exception:
                        level_val = 0
                except Exception:
                    pass

            # Fallback to current UI state if files missing/empty
            name_val = name_val or (self.Helldivers.get() or "Helldiver")
            ship1_val = ship1_val or (self.shipName1_var.get() or "SES Adjudicator")
            ship2_val = ship2_val or (self.shipName2_var.get() or "of Allegiance")

            # Generate the banner image using file-driven inputs
            pil_img = generate_helldiver_banner(
                name=name_val,
                title=title_val,
                level=level_val,
                shipname1=ship1_val,
                shipname2=ship2_val,
                profile=profile_val,
                base_dir=BASE_DIR,
                size=(640, 180),
            )
            # Ensure destination folder exists and save PNG (overwrite old one)
            os.makedirs(MISC_ITEMS_DIR, exist_ok=True)
            try:
                pil_img.save(GENERATED_BANNER_PATH, format="PNG")
            except Exception as se:
                logging.warning(f"[settings] Failed to save generated banner to disk: {se}")
            # Convert to ImageTk and show on label; keep a reference
            self._banner_preview_imgtk = ImageTk.PhotoImage(pil_img)
            self.banner_display_label.configure(image=self._banner_preview_imgtk)
        except Exception as e:
            logging.error(f"[settings] Failed generating banner: {e}")
            messagebox.showerror("Error", f"Failed to generate banner preview: {e}")

    def _load_saved_banner_preview(self):
        """Load banner preview image from disk if previously generated."""
        if os.path.exists(GENERATED_BANNER_PATH):
            try:
                img = Image.open(GENERATED_BANNER_PATH)
                self._banner_preview_imgtk = ImageTk.PhotoImage(img)
                self.banner_display_label.configure(image=self._banner_preview_imgtk)
            except Exception as e:
                logging.warning(f"[settings] Could not load saved banner preview: {e}")

    # ----- Combobox Selection -----
    def select_combobox_value(self, combo: ttk.Combobox, options: list[str], value: str, var: tk.StringVar):
        value = (value or "").strip()
        if not options:
            options.append(value or "")
        # Try to find normalized match
        try:
            idx = [norm(s) for s in options].index(norm(value))
        except ValueError:
            # Inject the loaded value at the front if not present
            if value:
                options[:] = [value] + [s for s in options if norm(s) != norm(value)]
                idx = 0
            else:
                idx = 0
        # Apply to combobox and var
        combo['values'] = options
        var.set(options[idx])
        combo.current(idx)

    def sync_comboboxes_from_vars(self):
        self.select_combobox_value(self.ship1_combo, self.shipName1s, self.shipName1_var.get(), self.shipName1_var)
        self.select_combobox_value(self.ship2_combo, self.shipName2s, self.shipName2_var.get(), self.shipName2_var)

    # ----- Save/Load -----
    def safe_load_settings(self):
        try:
            if os.path.exists(SETTINGS_PATH):
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ship1 = str(data.get("shipName1", self.shipName1_var.get())).strip()
                ship2 = str(data.get("shipName2", self.shipName2_var.get())).strip()
                user = str(data.get("username", self.Helldivers.get())).strip()
                self.shipName1_var.set(ship1)
                self.shipName2_var.set(ship2)
                self.Helldivers.set(user)
            if os.path.exists(DCORD_PATH):
                with open(DCORD_PATH, "r", encoding="utf-8") as f:
                    d = json.load(f)
                self.discord_uid_var.set(str(d.get("discord_uid", "")))
                self.platform_var.set(d.get("platform", "Not Selected") or "Not Selected")
                self.dont_send_to_discord_var.set(bool(d.get("dont_send_to_discord", False)))
                # Backward-compatible export keys
                logging_urls = d.get("discord_webhooks_logging_labeled") or [
                    {"label": "", "url": u} for u in d.get("discord_webhooks_logging", [])
                ]
                export_urls = d.get("discord_webhooks_export_labeled") or [
                    {"label": "", "url": u} for u in (d.get("discord_webhooks_export") or d.get("discord_webhooks", []))
                ]
                # Normalize labeled
                def _clean(items):
                    out = []
                    for w in items or []:
                        if isinstance(w, dict):
                            url = str(w.get("url", "")).strip()
                            label = str(w.get("label", "")).strip()
                        else:
                            url = str(w).strip()
                            label = ""
                        if url.lower().startswith(("http://", "https://")):
                            out.append({"label": label, "url": url})
                    return out
                self.webhooks_logging = _clean(logging_urls)
                self.webhooks_export = _clean(export_urls)
                # Load backup section if present
                bk = d.get("webhooks_backup") or {}
                if isinstance(bk, dict):
                    self._webhooks_backup = {
                        "discord_webhooks_logging_labeled": bk.get("discord_webhooks_logging_labeled", []),
                        "discord_webhooks_export_labeled": bk.get("discord_webhooks_export_labeled", []),
                        "discord_webhooks_logging": bk.get("discord_webhooks_logging", []),
                        "discord_webhooks_export": bk.get("discord_webhooks_export", []),
                        "discord_webhooks": bk.get("discord_webhooks", []),
                    }
                # If flag is set, reflect the forced state in UI but keep backup loaded in memory
                if self.dont_send_to_discord_var.get():
                    self._set_forced_webhooks_ui()
        except Exception as e:
            messagebox.showerror("Error", f"Could not load settings: {e}")

    def save_settings(self):
        # Validate URLs
        url_pattern = re.compile(r"^(http://|https://).+")
        def _validate(items):
            seen = set()
            for w in items:
                url = str(w.get("url", "")).strip()
                if url and not url_pattern.match(url):
                    messagebox.showerror("Error", f"Invalid webhook URL: {url}\nLabel: {w.get('label','')}")
                    return False
                if url in seen:
                    messagebox.showerror("Error", f"Duplicate webhook URL detected: {url}")
                    return False
                seen.add(url)
            return True
        if not _validate(self.webhooks_logging) or not _validate(self.webhooks_export):
            return

        # Ensure directory
        os.makedirs(JSON_DIR, exist_ok=True)

        # Write settings.json
        # Load existing settings to preserve Player Homeworld if it exists
        existing_homeworld = None
        try:
            if os.path.exists(SETTINGS_PATH):
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    existing_homeworld = existing_data.get("Player Homeworld")
        except Exception:
            pass
        
        settings_data = {
            "shipName1": self.shipName1_var.get(),
            "shipName2": self.shipName2_var.get(),
            "username": self.Helldivers.get(),
        }
        
        # Preserve Player Homeworld if it exists
        if existing_homeworld:
            settings_data["Player Homeworld"] = existing_homeworld
        
        # Write DCord.json
        def _extract(items):
            return [w.get("url", "").strip() for w in items if str(w.get("url", "")).strip().lower().startswith(("http://", "https://"))]
        if self.dont_send_to_discord_var.get():
            # When forcing, store backups and overwrite webhooks with forced URL
            # Ensure backup is captured from UI if not already
            if not self._webhooks_backup or not (self._webhooks_backup.get("discord_webhooks_logging_labeled") or self._webhooks_backup.get("discord_webhooks_export_labeled")):
                self._capture_backup_from_ui()
            forced_labeled = [{"label": "Forced", "url": FORCED_WEBHOOK_URL}]
            dcord = {
                "discord_uid": self.discord_uid_var.get(),
                "discord_webhooks_logging": [FORCED_WEBHOOK_URL],
                "discord_webhooks_export": [FORCED_WEBHOOK_URL],
                "discord_webhooks": [FORCED_WEBHOOK_URL],
                "discord_webhooks_logging_labeled": forced_labeled,
                "discord_webhooks_export_labeled": forced_labeled,
                "platform": self.platform_var.get() or "Not Selected",
                "dont_send_to_discord": True,
                "webhooks_backup": self._webhooks_backup,
            }
        else:
            # Normal save; if there is a backup but flag is off, write without forcing
            dcord = {
                "discord_uid": self.discord_uid_var.get(),
                "discord_webhooks_logging": _extract(self.webhooks_logging),
                "discord_webhooks_export": _extract(self.webhooks_export),
                "discord_webhooks": _extract(self.webhooks_export),
                "discord_webhooks_logging_labeled": self.webhooks_logging,
                "discord_webhooks_export_labeled": self.webhooks_export,
                "platform": self.platform_var.get() or "Not Selected",
                "dont_send_to_discord": False,
            }
        try:
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(settings_data, f, indent=4)
            with open(DCORD_PATH, "w", encoding="utf-8") as f:
                json.dump(dcord, f, indent=4)
            msg = "Settings saved successfully!" if "-ML" in sys.argv else "Settings saved! Please run MLHD2-Launcher.exe"
            messagebox.showinfo("Success", msg)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Could not save settings: {e}")

    # ----- Webhooks -----
    def refresh_webhook_listboxes(self):
        def _display(w):
            return w.get("url") if self.show_urls_var.get() or not w.get("label") else w.get("label")
        self.webhooks_listbox_logging.delete(0, tk.END)
        for idx, w in enumerate(self.webhooks_logging):
            self.webhooks_listbox_logging.insert(tk.END, _display(w))
            # Alternate row color
            bg = "#232323" if idx % 2 == 0 else "#1e1e1e"
            try:
                self.webhooks_listbox_logging.itemconfig(idx, bg=bg)
            except Exception:
                pass
        self.webhooks_listbox_export.delete(0, tk.END)
        for idx, w in enumerate(self.webhooks_export):
            self.webhooks_listbox_export.insert(tk.END, _display(w))
            bg = "#232323" if idx % 2 == 0 else "#1e1e1e"
            try:
                self.webhooks_listbox_export.itemconfig(idx, bg=bg)
            except Exception:
                pass

    def add_webhook_logging(self):
        url = self.new_webhook_var_logging.get().strip()
        label = self.new_webhook_label_var_logging.get().strip()
        if not url:
            messagebox.showwarning("Empty Input", "Please enter a webhook URL.")
            return
        if any(w.get("url") == url for w in self.webhooks_logging):
            messagebox.showwarning("Duplicate", "This webhook already exists in the list.")
            return
        self.webhooks_logging.append({"label": label, "url": url})
        self.new_webhook_var_logging.set("")
        self.new_webhook_label_var_logging.set("")
        self.refresh_webhook_listboxes()

    def remove_webhook_logging(self):
        sel = self.webhooks_listbox_logging.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a webhook to remove.")
            return
        del self.webhooks_logging[sel[0]]
        self.refresh_webhook_listboxes()

    def add_webhook_export(self):
        url = self.new_webhook_var_export.get().strip()
        label = self.new_webhook_label_var_export.get().strip()
        if not url:
            messagebox.showwarning("Empty Input", "Please enter a webhook URL.")
            return
        if any(w.get("url") == url for w in self.webhooks_export):
            messagebox.showwarning("Duplicate", "This webhook already exists in the list.")
            return
        self.webhooks_export.append({"label": label, "url": url})
        self.new_webhook_var_export.set("")
        self.new_webhook_label_var_export.set("")
        self.refresh_webhook_listboxes()

    def remove_webhook_export(self):
        sel = self.webhooks_listbox_export.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a webhook to remove.")
            return
        del self.webhooks_export[sel[0]]
        self.refresh_webhook_listboxes()

    # ----- Misc -----
    def reset_defaults(self):
        if not messagebox.askyesno("Confirm Reset", "Reset settings to defaults?"):
            return
        self.shipName1_var.set("SES Adjudicator")
        self.shipName2_var.set("of Allegiance")
        self.Helldivers.set("Helldiver")
        self.discord_uid_var.set("")
        self.platform_var.set("Not Selected")
        self.webhooks_logging.clear()
        self.webhooks_export.clear()
        self.sync_comboboxes_from_vars()
        self.refresh_webhook_listboxes()

    def cancel(self):
        if messagebox.askyesno("Confirm", "Exit without saving? Any unsaved changes will be lost."):
            self.destroy()

if __name__ == "__main__":
    logging.debug("[settings] __main__ start")
    try:
        app = SettingsPage()
        logging.debug("[settings] mainloop starting")
        app.mainloop()
        logging.debug("[settings] mainloop exited")
    except Exception as e:
        logging.critical("Fatal error in settings.py:")
        traceback.print_exc()
