import os
import json
import random
import logging
import subprocess
import sys
import webbrowser
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageTk, ImageDraw
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

from core.runtime_paths import app_path
from core.image_utils import (
    load_gw_icon,
    load_profile_preview,
    load_sector_placeholder,
    load_planet_preview,
    load_sector_preview,
    load_row_image,
    load_settings_button_images,
    load_biome_banner,
)
from core.ui_effects import bind_image_hover, load_small_icon
from core.ui_sound import play_button_click, play_button_hover


# Build and wire the main GUI; affects overall UI layout and interactions
def build_ui(app):
    """Construct the UI using the existing variables and methods on `app`.
    `app` is expected to be an instance of MissionLogGUI from main.py.
    This function intentionally mirrors the original _setup_ui implementation
    but references `app` instead of `self`.
    """

    root = app.root

    # --- Flair Colour Logic ---
    flair_colour = 'default'
    flair_colours = {
        'gold': {'fg': '#FFD700', 'outline': '#FFD700'},
        'blue': {'fg': '#00BFFF', 'outline': '#00BFFF'},
        'red': {'fg': '#FF4040', 'outline': '#FF4040'},
        'default': {'fg': '#FFFFFF', 'outline': '#666666'}
    }
    try:
        from core.utils import get_effective_flair
        flair_colour = get_effective_flair().lower()
        if flair_colour not in flair_colours:
            flair_colour = 'default'
    except Exception:
        flair_colour = 'default'
    flair_fg = flair_colours[flair_colour]['fg']
    flair_outline = flair_colours[flair_colour]['outline']

    # Create main content frame
    content = ttk.Frame(app.frame, padding=(20, 10))
    content.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    SETime = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M:%S")

    try:
        # Try to use Insignia font by family name (Tkinter does not support loading from file directly)
        app.fs_sinclair_font = None
        insignia_font_path = app_path('MiscItems', 'Fonts', 'Insignia.ttf')
        try:
            app.fs_sinclair_font = tkfont.Font(root=app.root, family="Insignia", size=14)
        except tk.TclError:
            # Font not installed, try to load using tk.call to add font from file (Windows only)
            pass
        if os.path.exists(insignia_font_path):
            try:
                app.root.tk.call("font", "create", "InsigniaTemp", "-family", "Insignia", "-size", 14)
                app.fs_sinclair_font = tkfont.Font(root=app.root, name="InsigniaTemp", exists=True)
                logging.info("Loaded Insignia font from file (font must be installed system-wide).")
            except Exception as load_e:
                logging.error(f"Failed to load Insignia font from file: {load_e}")
        else:
            logging.error("Insignia.ttf not found in ./MiscItems/Fonts/")
    except Exception as e:
        app.fs_sinclair_font = None
        logging.error(f"Failed to load Insignia font: {e}")

    # Mission Time + GW Date Toggle
    mission_time_var = tk.StringVar(value=SETime)
    gw_date_var = tk.StringVar(value=app.GWDate if hasattr(app, 'GWDate') else "")

    # Toggles display between GW date and GW day; affects top-right GW header
    def toggle_gw_date(event=None):
        # Toggle between GWDate and GWDay
        if gw_date_var.get() == getattr(app, 'GWDate', ''):
            gw_date_var.set(getattr(app, 'GWDay', ''))
        else:
            gw_date_var.set(getattr(app, 'GWDate', ''))

    header_frame = ttk.Frame(content)
    external_frame = ttk.Frame(header_frame)

    font_to_use = app.fs_sinclair_font if app.fs_sinclair_font is not None else tkfont.Font(family="Arial", size=14, weight="bold")
    ttk.Label(header_frame, text="Operation Details", font=font_to_use, foreground=flair_fg).pack(side=tk.LEFT)

    # Galactic War label and toggle
    gw_frame = ttk.Frame(external_frame)
    gw_frame.pack(side=tk.LEFT, padx=(0,0), pady=(0,0))

    # Place Galactic War label, icon, and date in the top right of the window
    top_right_frame = ttk.Frame(app.root)
    top_right_frame.place(relx=1.0, rely=0.0, anchor="ne", x=-40, y=20)  # 20px from top-right corner

    # Add GW label, date toggle, and icon in a single row (icon on the right)
    try:
        app.gw_icon_img = load_gw_icon()
        if app.gw_icon_img:
            gw_icon_label = ttk.Label(top_right_frame, image=app.gw_icon_img, cursor="hand2")
            gw_icon_label.pack(side=tk.RIGHT, padx=(1, 0))
            gw_icon_label.bind("<Button-1>", toggle_gw_date)
    except Exception as e:
        logging.error(f"Failed to load GW icon: {e}")

    ttk.Label(top_right_frame, text="Galactic War", foreground=flair_fg).pack(side=tk.LEFT)

    gw_label = ttk.Label(top_right_frame, textvariable=gw_date_var, cursor="hand2", width=14, anchor="w", foreground=flair_fg)
    gw_label.pack(side=tk.LEFT, padx=(2,0))
    gw_label.bind("<Button-1>", toggle_gw_date)

    # Pack external_frame so its children are visible
    external_frame.pack(side=tk.LEFT, padx=(10,0))

    mission_frame = ttk.LabelFrame(content, padding=10, labelwidget=header_frame, style="Flair.TLabelframe")

    # Updates the mission time string every tick; affects mission header
    def update_time():
        mission_time_var.set((datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%H:%M:%S"))

    app.update_time = update_time
    mission_frame.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
    # Fix: Explicitly configure grid columns to prevent overlap
    for col in range(8):
        mission_frame.columnconfigure(col, weight=1)

    # Load sectors from config (and store for later)
    with open(app_path('JSON', 'PlanetSectors.json'), 'r') as f:
        sectors_data = json.load(f)
        app.sectors_data = sectors_data
        sector_list = list(sectors_data.keys())

    # --- Mission Info Grid ---
    # Load ship name selections and Helldiver username from settings.json
    try:
        with open(app.settings_file, 'r') as f:
            settings_data = json.load(f)
            shipName1_default = settings_data.get('shipName1', "SES Adjudicator")
            shipName2_default = settings_data.get('shipName2', "of Allegiance")
            banner_type = settings_data.get('banner', "Biome Banner")
            app.shipname1_default = shipName1_default
            app.shipname2_default = shipName2_default
            app.helldiver_default = settings_data.get('username', "")
            app.full_ship_name = f"{shipName1_default} {shipName2_default}".strip()
    except Exception:
        shipName1_default = "SES Adjudicator"
        shipName2_default = "of Allegiance"
        app.shipname1_default = shipName1_default
        app.shipname2_default = shipName2_default
        app.helldiver_default = ""

    # Seed the Helldiver field from settings.json if it's empty/unset
    if not app.Helldivers.get():
        app.Helldivers.set(app.helldiver_default or "")

    ttk.Label(mission_frame, text="Level:", foreground=flair_fg).grid(row=0, column=2, sticky=tk.W, padx=0, pady=5)
    ttk.Entry(mission_frame, textvariable=app.level, width=35).grid(row=0, column=2, sticky=tk.W, padx=(45,0), pady=5)

    ttk.Label(mission_frame, text="Title:", foreground=flair_fg).grid(row=1, column=2, sticky=tk.W, pady=5)
    # Load titles from json file
    with open(app_path('JSON', 'Titles.json'), 'r') as f:
        titles_data = json.load(f)
        app.titles = titles_data["Titles"]
    app.title_combo = ttk.Combobox(mission_frame, textvariable=app.title, state='readonly', width=32)
    app.title_combo['values'] = app.titles
    app.title_combo.grid(row=1, column=2, sticky=tk.W, padx=(45,0), pady=5)
    app.title_combo.set(app.titles[0])

    ttk.Label(mission_frame, text="Profile:", foreground=flair_fg).grid(row=2, column=2, sticky=tk.W, pady=5)
    # Load profile pictures centrally (includes optional hidden profile)
    try:
        from core.utils import get_profile_pictures_list
        app.profile_pictures = get_profile_pictures_list()
    except Exception:
        # Fallback: read directly from JSON
        try:
            with open(app_path('JSON', 'ProfilePictures.json'), 'r') as f:
                profile_data = json.load(f)
                app.profile_pictures = profile_data.get("Profile Pictures", [])
        except Exception:
            app.profile_pictures = []
    app.profile_picture_combo = ttk.Combobox(mission_frame, textvariable=app.profile_picture, state='readonly', width=32)
    app.profile_picture_combo['values'] = app.profile_pictures
    app.profile_picture_combo.grid(row=2, column=2, sticky=tk.W, padx=(45,0), pady=5)
    app.profile_picture_combo.set(app.profile_pictures[0])

    # --- Mission Details Section ---
    # Create details_frame with custom font for the label
    details_frame = ttk.LabelFrame(content, padding=10, style="Flair.TLabelframe")
    details_label = ttk.Label(details_frame, text="Mission Details", font=font_to_use, foreground=flair_fg)
    details_frame['labelwidget'] = details_label
    details_frame.grid(row=1, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))

    profile_preview_frame = ttk.LabelFrame(mission_frame, labelwidget=ttk.Label(mission_frame, text="Profile Preview", font=("Arial", 10, "bold"), anchor="center", justify="center", foreground=flair_fg), padding=5, style="Flair.TLabelframe")
    profile_preview_frame.grid(row=0, column=3, rowspan=6, sticky=tk.N, padx=(20,0))  # Adjusted row span and sticky

    # Create label to hold the preview image with fixed square dimensions
    app.preview_label = tk.Label(profile_preview_frame, width=120, height=120, borderwidth=0)  # Fixed size for square preview
    app.preview_label.pack(padx=0, pady=0)  # Reduced vertical padding

    # Loads and shows selected profile picture preview; affects profile preview frame
    def update_profile_preview(*args):
        try:
            # Get selected profile name
            profile_name = app.profile_picture.get()
            if not profile_name:
                return

            img = load_profile_preview(profile_name, size=(120, 120))
            if img:
                app.preview_img = img
                app.preview_label.configure(image=img)
            else:
                app.preview_label.configure(image='')

        except Exception as e:
            logging.error(f"Failed to load profile preview: {e}")
            app.preview_label.configure(image='')

    # Bind preview update to profile selection
    try:
        app.profile_picture.trace_add("write", update_profile_preview)
    except Exception:
        # If trace_add not available, fallback to trace
        try:
            app.profile_picture.trace("w", lambda *a: update_profile_preview())
        except Exception:
            pass

    # Initial preview update
    update_profile_preview()

    ttk.Label(mission_frame, text="Sector:", foreground=flair_fg).grid(row=0, column=0, sticky=tk.W, pady=5)
    sector_combo = ttk.Combobox(mission_frame, textvariable=app.sector, values=sector_list, state='readonly', width=27)
    sector_combo.grid(row=0, column=1, padx=5, pady=5)
    sector_combo.set(sector_list[0])

    ttk.Label(mission_frame, text="Planet:", foreground=flair_fg).grid(row=1, column=0, sticky=tk.W, pady=5)
    planet_combo = ttk.Combobox(mission_frame, textvariable=app.planet, state='readonly', width=27)
    planet_combo.grid(row=1, column=1, padx=5, pady=5)
    app.sector_combo = sector_combo
    app.planet_combo = planet_combo

    # Create frame for planet preview with increased size
    planet_preview_frame = ttk.LabelFrame(mission_frame, labelwidget=ttk.Label(mission_frame, text="Planet Preview", font=("Arial", 10, "bold"), anchor="center", justify="center", foreground=flair_fg), padding=5, style="Flair.TLabelframe")
    planet_preview_frame.grid(row=0, column=4, rowspan=6, sticky=tk.N, padx=(20,0))

    # Create label to hold the preview image with fixed square dimensions
    app.planet_preview_label = tk.Label(planet_preview_frame, width=120, height=120, borderwidth=0)
    app.planet_preview_label.pack(padx=0, pady=0)

    # sector frame and label
    sector_frame = ttk.LabelFrame(mission_frame, labelwidget=ttk.Label(mission_frame, text="Sector Preview", font=("Arial", 10, "bold"), anchor="center", justify="center", foreground=flair_fg), padding=5, style="Flair.TLabelframe")
    sector_frame.grid(row=0, column=5, rowspan=6, sticky=tk.N, padx=(20,0))

    app.sector_info_label = tk.Label(sector_frame, borderwidth=0)
    app.sector_info_label.pack(padx=0, pady=0)

    try:
        ph = load_sector_placeholder()
        if ph:
            app.sector_info_img = ph
            app.sector_info_label.configure(image=app.sector_info_img)
    except Exception as e:
        logging.error(f"Failed to load sector preview image: {e}")

    # Banner type selection combobox
    banner_options = ["Biome Banner", "Subfaction Banner", "Helldiver Banner"]
    app.banner_type_var = tk.StringVar(value=banner_type)

    # Header containing the label and the combobox, used as the LabelFrame's labelwidget
    banner_header = ttk.Frame(details_frame)
    ttk.Label(banner_header, text="Banner Selection", foreground=flair_fg).pack(side=tk.LEFT)
    app.biome_banner_combo = ttk.Combobox(
        banner_header,
        textvariable=app.banner_type_var,
        values=banner_options,
        state="readonly",
        width=17
    )
    app.biome_banner_combo.pack(side=tk.LEFT, padx=(6, 0))

    # Frame reserved only for the image; header sits in the label area
    biome_frame = ttk.LabelFrame(details_frame, padding=5, style="Flair.TLabelframe")
    biome_frame['labelwidget'] = banner_header
    biome_frame.grid(row=0, column=6, rowspan=6, sticky=tk.N, padx=(20,0))

    # Bind combobox selection event
    app.biome_banner_combo.bind('<<ComboboxSelected>>', lambda e: [update_biome_banner(), save_banner_setting()])

    app.planet_biome_label = tk.Label(biome_frame, borderwidth=0)  # no width/height -> uses image natural size
    app.planet_biome_label.pack(padx=0, pady=0)

    # Updates banner image based on selected type/planet; affects banner display
    def update_biome_banner(*args, f=None):
        try:
            # Get banner type from the combobox
            banner_type_selected = app.banner_type_var.get()
            # Resolve current biome for the selected planet
            planet_name = app.planet.get()
            biome_map = f or {}
            if not biome_map:
                try:
                    with open(app_path('JSON', 'BiomePlanets.json'), 'r', encoding='utf-8') as bf:
                        biome_map = json.load(bf)
                except Exception:
                    biome_map = {}
            biome_name = biome_map.get(planet_name, "Mars")
            logging.debug(f"Planet: {planet_name}, Biome: {biome_name}, Banner style: {banner_type_selected}")
            app.current_biome = biome_name

            # Delegate actual loading/selection to image_utils.load_biome_banner which prefers repo-root media
            banner_img = load_biome_banner(app, banner_type_selected, planet_name)
            if banner_img:
                app.biome_banner_img = banner_img
                app.planet_biome_label.configure(image=app.biome_banner_img)
        except Exception as e:
            logging.error(f"Failed to load biome banner: {e}")
            # Fallback to default
            try:
                banner_path = app_path('media', 'biome_banners', 'Mars.png')
                pil_banner = Image.open(banner_path).convert('RGBA')
                bg_color = (37, 37, 38, 255)
                background = Image.new('RGBA', pil_banner.size, bg_color)
                pil_banner = Image.alpha_composite(background, pil_banner)
                app.biome_banner_img = ImageTk.PhotoImage(pil_banner)
                app.planet_biome_label.configure(image=app.biome_banner_img)
            except Exception:
                app.planet_biome_label.configure(image='')

    # Function to save banner selection to settings file
    # Persists current banner selection to settings.json; affects saved UI preferences
    def save_banner_setting(*args):
        try:
            # Ensure directory exists
            settings_dir = os.path.dirname(app.settings_file)
            os.makedirs(settings_dir, exist_ok=True)
            
            # Read current settings
            settings_data = {}
            if os.path.exists(app.settings_file):
                with open(app.settings_file, 'r', encoding='utf-8') as f:
                    settings_data = json.load(f)

            # Update banner setting
            settings_data['banner'] = app.banner_type_var.get()

            # Write back to settings file
            with open(app.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving banner setting: {e}")

    # Keep banner reactive to inputs that affect each style
            try:
                app.subfaction_type.trace_add("write", lambda *a: update_biome_banner())
                app.profile_picture.trace_add("write", lambda *a: update_biome_banner())
                app.banner_type_var.trace_add("write", lambda *a: [update_biome_banner(), save_banner_setting()])
            except Exception:
                pass

    # Loads planet preview image and syncs banner biome; affects planet and banner previews
    def update_planet_preview(*args):
        try:
            # Get selected planet name
            planet_name = app.planet.get()
            if not planet_name:
                return

            with open(app_path('JSON', 'BiomePlanets.json'), 'r', encoding='utf-8') as f:
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

            img = load_planet_preview(BiomePlanet)
            if img:
                app.planet_preview_img = img
                app.planet_preview_label.configure(image=app.planet_preview_img)
            update_biome_banner(f=biome_map) # passing biome data to avoid reloading file
        except Exception as e:
            logging.error(f"Failed to load planet preview: {e}")
            app.planet_preview_label.configure(image='')

    # Loads sector preview image based on sector/enemy; affects sector preview frame
    def update_sector_preview(*args):
        try:
            # Get selected sector name and enemy type
            sector_name = app.sector.get()
            enemy_type = app.enemy_type.get()
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

            photo = load_sector_preview(sector_name, enemy_type)
            if photo:
                app.sector_preview_img = photo
                app.sector_info_label.configure(image=photo)

        except Exception as e:
            logging.error(f"Failed to load sector preview: {e}")
            app.sector_info_label.configure(image='')

    # Bind preview update to both sector AND enemy type selection
    try:
        app.sector.trace_add("write", update_sector_preview)
    except Exception:
        try:
            app.sector.trace("w", lambda *a: update_sector_preview())
        except Exception:
            pass
    try:
        app.enemy_type.trace_add("write", update_sector_preview)
    except Exception:
        try:
            app.enemy_type.trace("w", lambda *a: update_sector_preview())
        except Exception:
            pass

    # Initial preview update
    update_sector_preview()

    # Bind preview update to planet selection
    try:
        app.planet.trace_add("write", update_planet_preview)
    except Exception:
        try:
            app.planet.trace("w", lambda *a: update_planet_preview())
        except Exception:
            pass

    # Initial preview update
    update_planet_preview()

    ttk.Label(mission_frame, text="Mega City:", foreground=flair_fg).grid(row=2, column=0, sticky=tk.W, pady=5)
    mega_cities_combo = ttk.Combobox(mission_frame, textvariable=app.mega_cities, state='readonly', width=27)
    mega_cities_combo.grid(row=2, column=1, sticky=tk.W, padx=(8,0), pady=5)
    app.mega_cities_combo = mega_cities_combo

    # Dynamic planet / mega city lists
    # Populates mega city options for the selected planet; affects mega city combobox
    def update_mega_cities(*args):
        # Populate mega cities based on currently selected planet.
        selected_planet = app.planet.get()
        try:
            with open(app_path('JSON', 'MegaCityPlanets.json'), 'r') as f:
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

    # Populates planets for the selected sector and refreshes mega cities; affects planet combobox
    def update_planets(*args):
        # Populate planets based on selected sector and immediately refresh mega cities.
        selected_sector = app.sector.get()
        if not selected_sector or selected_sector not in sectors_data:
            return
        planet_list = sectors_data[selected_sector]["planets"]
        planet_combo['values'] = planet_list
        # Preserve existing planet if still valid, else select first
        current_planet = app.planet.get()
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
    app.row_image_labels = []
    images_row_frame = ttk.Frame(mission_frame)
    images_row_frame.grid(row=4, column=0, columnspan=7, sticky="w", padx=0, pady=0)  # Remove vertical padding
    for idx in range(7):
        lbl = tk.Label(images_row_frame, width=60, height=60, borderwidth=0, highlightthickness=0)  # Smaller size
        lbl.pack(side=tk.LEFT, padx=8, pady=0)  # Tighter packing
        app.row_image_labels.append(lbl)

    # Refreshes the row of seven summary icons from current selections; affects icons row
    def update_row_images(*args):
        # Image 1: Enemy Type
        enemy_type = app.enemy_type.get()
        enemy_icon_path = app_path('media', 'factions', f"{enemy_type}.png") if enemy_type else None
        if not enemy_icon_path or not os.path.exists(enemy_icon_path):
            enemy_icon_path = app_path('orphan', 'sector-placeholder.png')

        # Image 2: Subfaction
        subfaction_type = app.subfaction_type.get()
        subfaction_type_clean = subfaction_type.replace(" ", "_") if subfaction_type else ""
        subfaction_icon_path = app_path('media', 'subfactions', f"{subfaction_type_clean}.png") if subfaction_type_clean else None
        if not subfaction_icon_path or not os.path.exists(subfaction_icon_path):
            subfaction_icon_path = app_path('orphan', 'sector-placeholder.png')

        # Image 3: Campaign
        campaign_type = app.mission_category.get()
        campaign_type_clean = campaign_type.replace(" ", "_") if campaign_type else ""
        campaign_icon_path = app_path('media', 'campaigns', f"{campaign_type_clean}.png") if campaign_type_clean else None
        if not campaign_icon_path or not os.path.exists(campaign_icon_path):
            campaign_icon_path = app_path('orphan', 'sector-placeholder.png')

        # Image 4: Difficulty
        try:
            difficulty_type = app.difficulty.get()
            if difficulty_type and '-' in difficulty_type:
                difficulty_type_clean = difficulty_type.split('-', 1)[1].strip()
            else:
                difficulty_type_clean = difficulty_type.replace(" ", "_") if difficulty_type else ""
            difficulty_icon_path = app_path('media', 'difficulties', f"{difficulty_type_clean}.png")
            if not difficulty_icon_path or not os.path.exists(difficulty_icon_path):
                difficulty_icon_path = app_path('orphan', 'sector-placeholder.png')
        except Exception as e:
            logging.error(f"Error loading difficulty icon: {e}")
            difficulty_icon_path = app_path('orphan', 'sector-placeholder.png')

        # Image 5: Mission
        mission_type = app.mission_type.get()
        enemy_type = app.enemy_type.get()
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
        elif mission_type == "Blitz: Destroy Bio-Processors":
            mission_icon_filename = "Blitz Destroy Bio-Processors.png"
        elif mission_type == "Commando: Acquire Evidence":
            mission_icon_filename = "Commando Acquire Evidence.png"
        elif mission_type == "Commando: Extract Intel":
            mission_icon_filename = "Commando Extract Intel.png"
        elif mission_type == "Commando: Secure Black Box":
            mission_icon_filename = "Commando Secure Black Box.png"
        else:
            mission_icon_filename = f"{mission_type}.png" if mission_type else None
        mission_icon_path = app_path('media', 'missions', mission_icon_filename) if mission_icon_filename else None
        if not mission_icon_path or not os.path.exists(mission_icon_path):
            mission_icon_path = app_path('orphan', 'sector-placeholder.png')

        # Image 6: Major Order checkbox
        major_order_active = app.MO.get()
        if major_order_active:
            major_order_icon_path = app_path('media', 'major_order', "Major_Order_True.png")
        else:
            major_order_icon_path = app_path('media', 'major_order', "Major_Order_False.png")
        if not major_order_icon_path or not os.path.exists(major_order_icon_path):
            major_order_icon_path = app_path('orphan', 'sector-placeholder.png')

        # Image 7: DSS dropdown
        dss_mod = app.DSSMod.get()
        dss_mod_clean = dss_mod.replace(" ", "_") if dss_mod else ""
        dss_icon_path = app_path('media', 'dssmod', f"{dss_mod_clean}.png") if dss_mod_clean else None
        if not dss_icon_path or not os.path.exists(dss_icon_path):
            dss_icon_path = app_path('orphan', 'sector-placeholder.png')

        icon_paths = [
            enemy_icon_path,
            subfaction_icon_path,
            campaign_icon_path,
            difficulty_icon_path,
            mission_icon_path,
            major_order_icon_path,
            dss_icon_path,
        ]
        app.row_images = []
        for idx, (lbl, img_path) in enumerate(zip(app.row_image_labels, icon_paths)):
            try:
                tk_img = load_row_image(img_path, size=(60, 60)) if img_path else None
                if tk_img:
                    lbl.configure(image=tk_img)
                    lbl.image = tk_img
                    app.row_images.append(tk_img)
                else:
                    lbl.configure(image='')
                    lbl.image = None
            except Exception as e:
                logging.error(f"Failed to load row image {img_path}: {e}")
                lbl.configure(image='')
                lbl.image = None

    # Bind updates to dropdowns and checkboxes
    try:
        app.enemy_type.trace_add("write", update_row_images)
        app.subfaction_type.trace_add("write", update_row_images)
        app.mission_category.trace_add("write", update_row_images)
        app.difficulty.trace_add("write", update_row_images)
        app.mission_type.trace_add("write", update_row_images)
        app.MO.trace_add("write", update_row_images)
        app.DSSMod.trace_add("write", update_row_images)
    except Exception:
        pass
    # Initial population
    update_row_images()

    # Create a dedicated frame for setting and invite buttons to avoid affecting grid row height
    button_icon_frame = ttk.Frame(mission_frame)
    button_icon_frame.grid(row=0, column=7, padx=(0,10), pady=(0,10), sticky=tk.NE,rowspan=7)
    # Top row to place Settings (kept inside) and a separate root-level info button
    top_buttons_row = ttk.Frame(button_icon_frame)
    top_buttons_row.pack(side=tk.TOP, pady=(10,8), padx=0)
    # Settings button with hover effect
    try:
        try:
            default_img, hover_img = load_settings_button_images()
            app.settings_btn_img_default = default_img
            app.settings_btn_img_hover = hover_img
        except Exception:
            app.settings_btn_img_default = app.settings_btn_img_hover = None

        app.settings_btn_label = tk.Label(
            top_buttons_row,
            image=app.settings_btn_img_default,
            borderwidth=0,
            highlightthickness=0,
            cursor="hand2"
        )
        app.settings_btn_label.pack(side=tk.LEFT, pady=0, padx=0)

        # Bind hover enter/leave using the ui_effects helper
        bind_image_hover(app.settings_btn_label, app.settings_btn_img_default, app.settings_btn_img_hover,
                        on_enter=lambda e: (play_button_hover(), None),
                        on_leave=lambda e: None)

        # Launches the settings UI in a separate process; affects settings window
        def _open_settings(event=None):
            """Open settings.py in a detached child process using the current Python
            interpreter and a cleaned environment so debugpy/pydevd plugins from the
            parent do not trigger in the child process.
            """
            try:
                # Prefer running settings as a module so package-relative imports work
                settings_module = ['-m', 'core.settings']

                env = os.environ.copy()
                # Remove environment variables that may cause debugger/pydevd to inject plugins
                for k in list(env.keys()):
                    uk = k.upper()
                    if uk.startswith('PYDEVD') or uk.startswith('DEBUGPY') or 'PYDEVD' in uk or 'DEBUGPY' in uk:
                        env.pop(k, None)

                creationflags = 0
                if os.name == 'nt':
                    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

                try:
                    subprocess.Popen([sys.executable] + settings_module + ['-ML'], env=env,
                                     creationflags=creationflags, close_fds=True)
                except Exception:
                    # Fallback to running the file directly if module invocation fails
                    settings_path = app_path("settings.py")
                    if not os.path.exists(settings_path):
                        settings_path = os.path.join(os.path.dirname(__file__), 'settings.py')
                    subprocess.Popen([sys.executable, settings_path, '-ML'], env=env,
                                     creationflags=creationflags, close_fds=True)
            except Exception as e:
                logging.error(f"Failed to open settings: {e}")

        app.settings_btn_label.bind("<Button-1>", _open_settings)
    except Exception as e:
        logging.error(f"Failed to load settings button image: {e}")
        fallback_label = tk.Label(top_buttons_row, text="Settings", cursor="hand2")
        fallback_label.pack(side=tk.LEFT, pady=0, padx=0)
        fallback_label.bind("<Button-1>", _open_settings)

    # Info (Help) button with hover effect, placed OUTSIDE frames at root top-right and smaller
    try:
        # Create a root-level overlay frame for the info button
        app.top_right_info_frame = ttk.Frame(app.root)
        # Anchor to top-right, adjust x/y padding as needed
        app.top_right_info_frame.place(relx=1.0, rely=0.0, anchor="ne", x=-8, y=8)

        app.help_btn_img_default = load_small_icon(app_path('media', 'SyInt', 'HelpButton.png'))
        app.help_btn_img_hover = load_small_icon(app_path('media', 'SyInt', 'HelpButtonHover.png'))

        app.help_btn_label = tk.Label(
        app.top_right_info_frame,
        image=app.help_btn_img_default,
        borderwidth=0,
        highlightthickness=0,
        cursor="hand2"
        )
        app.help_btn_label.pack(side=tk.LEFT, pady=0, padx=0)

        bind_image_hover(app.help_btn_label, app.help_btn_img_default, app.help_btn_img_hover,
                        on_enter=lambda e: (play_button_hover(), None),
                        on_leave=lambda e: None)

        # Easter egg tracking
        import time
        app.help_btn_clicks = []
        
        # Shows Tips window or easter egg image after rapid clicks; affects help popup
        def show_sector_placeholder_window():
            # Track clicks for easter egg
            current_time = time.time()
            app.help_btn_clicks.append(current_time)
            # Remove clicks older than 60 seconds
            app.help_btn_clicks = [t for t in app.help_btn_clicks if current_time - t <= 60]
            
            # Check if easter egg should trigger (10 clicks within a minute)
            show_easter_egg = len(app.help_btn_clicks) >= 10
            
            # Create a new top-level window
            win = tk.Toplevel(app.root)
            win.title("Tips" if not show_easter_egg else "???")
            win.resizable(False, False)
            # Load the image
            try:
                if show_easter_egg:
                    # Easter egg: show egg.png at larger size
                    pil_img = Image.open(app_path('media', 'SyInt', 'egg.png')).convert('RGBA')
                    # Scale up the image (2x size)
                    pil_img = pil_img.resize((pil_img.width * 2, pil_img.height * 2), Image.LANCZOS)
                    img = ImageTk.PhotoImage(pil_img)
                    lbl = tk.Label(win, image=img)
                    lbl.image = img  # Keep reference
                    lbl.pack(padx=0, pady=0)
                else:
                    # Normal: show Tips.png
                    pil_img = Image.open(app_path('media', 'SyInt', 'Tips.png')).convert('RGBA')
                    # Subsample the image (resize to half size)
                    pil_img = pil_img.resize((pil_img.width // 2, pil_img.height // 2), Image.LANCZOS)
                    img = ImageTk.PhotoImage(pil_img)
                    lbl = tk.Label(win, image=img)
                    lbl.image = img  # Keep reference
                    lbl.pack(padx=10, pady=10)
            except Exception as e:
                lbl = tk.Label(win, text="Failed to load image")
                lbl.pack(padx=10, pady=10)

        app.help_btn_label.bind("<Button-1>", lambda e: show_sector_placeholder_window())
    except Exception as e:
        logging.error(f"Failed to load help/info button image: {e}")
        help_fallback = tk.Label(app.root, text="Info", cursor="hand2")
        help_fallback.place(relx=1.0, rely=0.0, anchor="ne", x=-8, y=8)
        help_fallback.bind("<Button-1>", lambda e: show_sector_placeholder_window())

    # Invite button with hover effect
    try:
        # Helper to load invite button images with background; used by invite control
        def load_invite_btn_img(path):
            pil_img = Image.open(path).convert('RGBA')
            pil_img = pil_img.resize((pil_img.width // 4, pil_img.height // 4), Image.LANCZOS)
            bg_color = (37, 37, 38, 255)
            background = Image.new('RGBA', pil_img.size, bg_color)
            pil_img = Image.alpha_composite(background, pil_img)
            return ImageTk.PhotoImage(pil_img)

        app.invite_btn_img_default = load_invite_btn_img(app_path('media', 'SyInt', 'InviteButton.png'))
        app.invite_btn_img_hover = load_invite_btn_img(app_path('media', 'SyInt', 'InviteButtonHover.png'))

        app.invite_btn_label = tk.Label(
        button_icon_frame,
        image=app.invite_btn_img_default,
        borderwidth=0,
        highlightthickness=0,
        cursor="hand2"
        )
        app.invite_btn_label.pack(side=tk.TOP, pady=(0,8), padx=0)

        # Hover handler to swap invite button image; affects invite button UI
        def on_invite_btn_enter(e):
                app.invite_btn_label.configure(image=app.invite_btn_img_hover)
                try:
                    play_button_hover()
                except Exception:
                    pass
        # Leave handler to restore invite button image; affects invite button UI
        def on_invite_btn_leave(e):
            app.invite_btn_label.configure(image=app.invite_btn_img_default)

        app.invite_btn_label.bind("<Enter>", on_invite_btn_enter)
        app.invite_btn_label.bind("<Leave>", on_invite_btn_leave)
        app.invite_btn_label.bind("<Button-1>", lambda e: webbrowser.open("https://discord.gg/U6ydgwFKZG"))
    except Exception as e:
        logging.error(f"Failed to load invite button image: {e}")
        invite_fallback = tk.Label(button_icon_frame, text="Invite Button", cursor="hand2")
        invite_fallback.pack(side=tk.TOP, pady=(0,8), padx=0)
        invite_fallback.bind("<Button-1>", lambda e: webbrowser.open("https://discord.gg/U6ydgwFKZG"))

    # Enemy selection
    ttk.Label(details_frame, text="Enemy Type:", foreground=flair_fg).grid(row=0, column=0, sticky=tk.W, pady=5)

    enemy_types = []
    try:
        with open(app_path('JSON', 'Missions.json'), 'r') as f:
            missions_data = json.load(f)
            # Missions.json may map enemy types to missions; collect keys
            enemy_types = list(missions_data.keys())
    except Exception:
        # fallback to Enemies.json
        try:
            with open(app_path('JSON', 'Enemies.json'), 'r') as f:
                enemies_data = json.load(f)
                enemy_types = list(enemies_data.keys())
        except Exception:
            enemy_types = []

    enemy_combo = ttk.Combobox(details_frame, textvariable=app.enemy_type, values=enemy_types, state='readonly', width=27)
    enemy_combo.grid(row=0, column=1, padx=5, pady=5)

    # Major Order + DSS toggles
    ttk.Label(details_frame, text="Major Order:", foreground=flair_fg).grid(row=2, column=2, sticky=tk.W, pady=5)
    ttk.Checkbutton(details_frame, variable=app.MO).grid(row=2, column=2, sticky=tk.W, padx=(100,0), pady=5)

    # DSS modifier dropdown (shown only if active)
    ttk.Label(details_frame, text="DSS Active:", foreground=flair_fg).grid(row=2, column=2, sticky=tk.W, pady=5, padx=(150,0))
    ttk.Checkbutton(details_frame, variable=app.DSS).grid(row=2, column=2, sticky=tk.W, padx=(250,0), pady=5)

    app.dss_frame = ttk.Frame(details_frame)
    app.dss_frame.grid(row=3, column=2, sticky=tk.W, pady=5)
    ttk.Label(app.dss_frame, text="DSS Modifier:", foreground=flair_fg).pack(side=tk.LEFT)
    dss_mods = ["Inactive", "Orbital Blockade", "Heavy Ordnance Distribution", "Eagle Storm", "Eagle Blockade"]
    app.DSSMod.set("Inactive")  # Set default value
    app.dss_combo = ttk.Combobox(app.dss_frame, textvariable=app.DSSMod, values=dss_mods, state='readonly', width=27)
    app.dss_combo.pack(side=tk.LEFT, padx=(40,0))

    app.dss_frame.grid_remove()

    # Shows or hides DSS modifier controls based on DSS state; affects DSS frame
    def toggle_dss_mod(*args):
        if app.DSS.get():
            app.dss_frame.grid()
        else:
            app.DSSMod.set("Inactive")
            app.dss_frame.grid_remove()

    try:
        app.DSS.trace_add("write", toggle_dss_mod)
    except Exception:
        try:
            app.DSS.trace("w", lambda *a: toggle_dss_mod())
        except Exception:
            pass

    # Subfaction
    ttk.Label(details_frame, text="Enemy Subfaction:", foreground=flair_fg).grid(row=0, column=2, sticky=tk.W, pady=5)
    subfaction_combo = ttk.Combobox(details_frame, textvariable=app.subfaction_type, state='readonly', width=27)
    subfaction_combo.grid(row=0, column=2, sticky=tk.E, padx=(125,0), pady=5)
    # Ensure banner updates when subfaction changes
    try:
        subfaction_combo.bind('<<ComboboxSelected>>', lambda e: update_biome_banner())
        app.subfaction_type.trace_add("write", lambda *a: update_biome_banner())
    except Exception:
        try:
            subfaction_combo.bind('<<ComboboxSelected>>', lambda e: update_biome_banner())
            app.subfaction_type.trace("w", lambda *a: update_biome_banner())
        except Exception:
            pass

    # HVT Type
    ttk.Label(details_frame, text="High-Value Target:", foreground=flair_fg).grid(row=1, column=2, sticky=tk.W, pady=5)
    hvt_combo = ttk.Combobox(details_frame, textvariable=app.hvt_type, state='readonly', width=27)
    hvt_combo.grid(row=1, column=2, padx=(125,0), pady=5)
    # Ensure banner updates when HVT changes
    try:
        hvt_combo.bind('<<ComboboxSelected>>', lambda e: update_biome_banner())
        app.hvt_type.trace_add("write", lambda *a: update_biome_banner())
    except Exception:
        try:
            hvt_combo.bind('<<ComboboxSelected>>', lambda e: update_biome_banner())
            app.hvt_type.trace("w", lambda *a: update_biome_banner())
        except Exception:
            pass

    # Campaign
    ttk.Label(details_frame, text="Mission Campaign:", foreground=flair_fg).grid(row=1, column=0, sticky=tk.W, pady=5)
    mission_cat_combo = ttk.Combobox(details_frame, textvariable=app.mission_category, state='readonly', width=27)
    mission_cat_combo.grid(row=1, column=1, padx=5, pady=5)

    # Difficulty
    ttk.Label(details_frame, text="Mission Difficulty:", foreground=flair_fg).grid(row=2, column=0, sticky=tk.W, pady=5)
    difficulty_combo = ttk.Combobox(details_frame, textvariable=app.difficulty, state='readonly', width=27)
    difficulty_combo.grid(row=2, column=1, padx=5, pady=5)

    # Mission type
    ttk.Label(details_frame, text="Mission Name:", foreground=flair_fg).grid(row=3, column=0, sticky=tk.W, pady=5)
    mission_type_combo = ttk.Combobox(details_frame, textvariable=app.mission_type, state='readonly', width=27)
    mission_type_combo.grid(row=3, column=1, padx=5, pady=5)

    # Populates subfactions for the selected enemy; affects subfaction combobox
    def update_subfactions(*args):
        enemy = app.enemy_type.get()
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

    # Populates HVT options for selected enemy/subfaction; affects HVT combobox
    def update_hvts(*args):
        enemy = app.enemy_type.get()
        subfaction = app.subfaction_type.get()
        
        try:
            with open(app_path('JSON', 'Enemies.json'), 'r') as f:
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
    # Resets HVT selection when enemy type changes; affects HVT state
    def reset_hvt(*args):
        app.hvt_type.set("No HVTs")
    try:
        app.enemy_type.trace_add("write", reset_hvt)
    except Exception:
        try:
            app.enemy_type.trace("w", lambda *a: reset_hvt())
        except Exception:
            pass

    # Populates mission categories for enemy/subfaction; affects campaign combobox
    def update_mission_categories(*args):
        enemy = app.enemy_type.get()
        subfaction = app.subfaction_type.get()
        categories = []
        if enemy in missions_data and subfaction in missions_data[enemy]:
            categories = list(missions_data[enemy][subfaction].keys())
            mission_cat_combo['values'] = categories
        else:
            mission_cat_combo['values'] = []
        if categories:
            mission_cat_combo.set(categories[0])
            update_mission_types()

    # Populates difficulties and mission names for selected category; affects difficulty/mission comboboxes
    def update_mission_types(*args):
        enemy = app.enemy_type.get()
        subfaction = app.subfaction_type.get()
        category = app.mission_category.get()
        
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

    # Updates mission names when difficulty changes; affects mission combobox
    def update_available_missions(*args):
        enemy = app.enemy_type.get()
        subfaction = app.subfaction_type.get()
        category = app.mission_category.get()
        difficulty = app.difficulty.get()
        
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
    app.enemy_type.trace_add("write", lambda *args: update_hvts())
    app.subfaction_type.trace_add("write", lambda *args: update_hvts())
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
    stats_frame = ttk.LabelFrame(stats_note_container, text="Mission Results", padding=10, style="Flair.TLabelframe")
    stats_label = ttk.Label(stats_frame, text="Mission Results", font=font_to_use, foreground=flair_fg)
    stats_frame['labelwidget'] = stats_label
    stats_frame.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)

    # Note
    note_frame = ttk.LabelFrame(stats_note_container, text="Notes", padding=10, style="Flair.TLabelframe")
    note_label = ttk.Label(note_frame, text="Notes", font=font_to_use, foreground=flair_fg)
    note_frame['labelwidget'] = note_label
    note_frame.pack(side=tk.RIGHT, padx=5, fill=tk.BOTH, expand=True)

    MAX_NOTE_CHARS = 512

    note_font = tkfont.Font(family=font_to_use, size=14)
    note_entry = tk.Text(note_frame, height=3, width=30, wrap="word", font=note_font)
    try:
        note_entry.configure(selectforeground='black')
    except Exception:
        pass
    note_entry.grid(row=0, column=0, padx=5, pady=(5,0), sticky=(tk.W, tk.E, tk.N, tk.S))
    app.note_entry = note_entry

    # Character counter
    counter_label = ttk.Label(note_frame, text=f"0/{MAX_NOTE_CHARS}")
    counter_label.grid(row=1, column=0, padx=5, pady=(2,5), sticky=tk.E)

    # Enforces note length limit and updates counter; affects Notes panel
    def update_note_limit(event=None):
        text = note_entry.get("1.0", "end-1c")
        if len(text) > MAX_NOTE_CHARS:
            # Delete only the excess instead of resetting whole text
            note_entry.delete(f"1.0+{MAX_NOTE_CHARS}c", tk.END)
            text = note_entry.get("1.0", "end-1c")
        counter_label.config(text=f"{len(text)}/{MAX_NOTE_CHARS}")
        app.note.set(text)

    # Blocks extra typing when note is at max length; affects note input behavior
    def block_excess(event):
        # Prevent further typing when at limit (allow navigation & deletion)
        text = note_entry.get("1.0", "end-1c")
        if (len(text) >= MAX_NOTE_CHARS and 
            event.keysym not in ("BackSpace", "Delete", "Left", "Right", "Up", "Down", "Home", "End")):
            return "break"

    # Bind note editor constraints
    note_entry.bind("<KeyPress>", block_excess)
    note_entry.bind("<KeyRelease>", update_note_limit)
    note_entry.bind("<<Paste>>", lambda e: app.root.after(1, update_note_limit))
    note_entry.bind("<FocusOut>", update_note_limit)

    # Initialize note state
    update_note_limit()

    note_frame.columnconfigure(0, weight=1)
    note_frame.rowconfigure(0, weight=1)

    ttk.Label(stats_frame, text="Kills:", foreground=flair_fg).grid(row=1, column=0, sticky=tk.W, pady=5)
    ttk.Entry(stats_frame, textvariable=app.kills, width=30).grid(row=1, column=1, padx=5, pady=5)

    ttk.Label(stats_frame, text="Deaths:", foreground=flair_fg).grid(row=2, column=0, sticky=tk.W, pady=5)
    ttk.Entry(stats_frame, textvariable=app.deaths, width=30).grid(row=2, column=1, padx=5, pady=5)

    ttk.Label(stats_frame, text="Performance:", foreground=flair_fg).grid(row=3, column=0, sticky=tk.W, pady=5)
    ratings = ["Gallantry Beyond Measure", "Outstanding Patriotism", "Truly Exceptional Heroism", "Superior Valour", "Costly Failure", "Honourable Duty", "Unremarkable Performance", "Disappointing Service", "Disgraceful Conduct"]
    rating_combo = ttk.Combobox(stats_frame, textvariable=app.rating, values=ratings, state='readonly', width=27)
    rating_combo.grid(row=3, column=1, padx=5, pady=5)

    # Submit (Image Button with Hover)
    try:
        # Helper to load submit/observe button images with app background; used by submit area
        def load_btn_img(path):
            pil_img = Image.open(path).convert('RGBA')
            pil_img = pil_img.resize((pil_img.width, pil_img.height), Image.LANCZOS)
            bg_color = (37, 37, 38, 255)
            background = Image.new('RGBA', pil_img.size, bg_color)
            pil_img = Image.alpha_composite(background, pil_img)
            return ImageTk.PhotoImage(pil_img)

        app.submit_img_default = load_btn_img(app_path('media', 'SyInt', 'SubmitButtonNH.png'))
        app.submit_img_hover = load_btn_img(app_path('media', 'SyInt', 'SubmitButtonHover.png'))
        app.submit_img_yes = load_btn_img(app_path('media', 'SyInt', 'SubmitButtonYes.png'))
        app.submit_img_no = load_btn_img(app_path('media', 'SyInt', 'SubmitButtonNo.png'))
        
        # Observe button images
        app.observe_img_default = load_btn_img(app_path('media', 'SyInt', 'ObserveButton.png'))
        app.observe_img_hover = load_btn_img(app_path('media', 'SyInt', 'ObserveButtonHover.png'))
        
        # Observe button images
        app.observe_img_default = load_btn_img(app_path('media', 'SyInt', 'ObserveButton.png'))
        app.observe_img_hover = load_btn_img(app_path('media', 'SyInt', 'ObserveButtonHover.png'))

        app._submit_img_state = app.submit_img_default
        app.submit_label = tk.Label(content, image=app.submit_img_default, borderwidth=0, highlightthickness=0, cursor="hand2")
        app.submit_label.grid(row=3, column=0, pady=15)

        # Hover handler to swap submit/observe image; affects submit button UI
        def on_enter(e):
            if app.enemy_type.get() == "Observing":
                app.submit_label.configure(image=app.observe_img_hover)
                app.submit_label.image = app.observe_img_hover
            else:
                app.submit_label.configure(image=app.submit_img_hover)
                app.submit_label.image = app.submit_img_hover
            try:
                play_button_hover()
            except Exception:
                pass
        # Leave handler restoring submit/observe image; affects submit button UI
        def on_leave(e):
            app.submit_label.configure(image=app._submit_img_state)
            app.submit_label.image = app._submit_img_state  # Prevent garbage collection

        # Click handler to submit report or observe data; triggers submit/observe flow
        def on_click(e):
            play_button_click()
            if app.enemy_type.get() == "Observing":
                app.observe_data()
            else:
                app.submit_data()

        app.submit_label.bind("<Enter>", on_enter)
        app.submit_label.bind("<Leave>", on_leave)
        app.submit_label.bind("<Button-1>", on_click)
    except Exception as e:
        logging.error(f"Failed to load submit button image: {e}")
        submit_button = ttk.Button(content, text="Submit Mission Report", command=app.submit_data, width=130, padding=(0, 30))
        submit_button.grid(row=3, column=0, pady=15)

    # Submission overlay image placed behind the submit button, with flair colour support
    try:
        # Default to SubmissionOverlay.png
        overlay_img_name = 'SubmissionOverlay.png'
        # Try to read flair_colour from DCord.json
        try:
            from core.utils import get_effective_flair
            flair_colour = get_effective_flair().lower()
            if flair_colour == 'gold':
                overlay_img_name = 'GoldSubmissionOverlay.png'
            elif flair_colour == 'blue':
                overlay_img_name = 'BlueSubmissionOverlay.png'
            elif flair_colour == 'red':
                overlay_img_name = 'RedSubmissionOverlay.png'
        except Exception as e:
            logging.warning(f"Could not determine effective flair colour: {e}")
        overlay_img_path = app_path('media', 'SyInt', overlay_img_name)
        pil_overlay = Image.open(overlay_img_path).convert('RGBA')
        new_width = int(pil_overlay.width * 1.05)
        new_height = pil_overlay.height
        pil_overlay = pil_overlay.resize((new_width, new_height), Image.LANCZOS)
        bg_color = (37, 37, 38, 255)
        background = Image.new('RGBA', pil_overlay.size, bg_color)
        pil_overlay = Image.alpha_composite(background, pil_overlay)
        app.submit_overlay_img = ImageTk.PhotoImage(pil_overlay)
        app.submit_overlay_label = tk.Label(
            content, image=app.submit_overlay_img, borderwidth=0, highlightthickness=0, bg="#252526"
        )
        app.submit_overlay_label.grid(row=3, column=0, pady=(10, 0), padx=(0, 5), sticky="n")
        app.submit_overlay_label.lower(app.submit_label)
    except Exception as e:
        logging.error(f"Failed to load submission overlay image: {e}")

    # Export + Style sections
    bottom_frame = ttk.LabelFrame(content, text="Report Style and Export", padding=10, style="Flair.TLabelframe")
    bottom_frame.grid(row=4, column=0, pady=5, sticky=(tk.W, tk.E))

    # Export buttons / integrations
    export_label = ttk.Label(content, text="Exporting", font=font_to_use, foreground=flair_fg)
    export_frame = ttk.LabelFrame(content, padding=10, style="Flair.TLabelframe", labelwidget=export_label)
    export_frame.grid(row=4, column=0, pady=5, sticky=(tk.W, tk.E))
    # --- Apply custom style for flair outlines ---
    style = ttk.Style()
    style.configure("Flair.TLabelframe", bordercolor=flair_outline, borderwidth=3)
    style.configure("Flair.TLabelframe.Label", foreground=flair_fg)

    # Export GUI launcher with image and hover effect, with sound effect on click
    try:
        # Helper to load Export GUI button images with background; used by export GUI
        def load_export_gui_img(path):
            pil_img = Image.open(path).convert('RGBA')
            pil_img = pil_img.resize((pil_img.width // 2, pil_img.height // 2), Image.LANCZOS)
            bg_color = (37, 37, 38, 255)
            background = Image.new('RGBA', pil_img.size, bg_color)
            pil_img = Image.alpha_composite(background, pil_img)
            return ImageTk.PhotoImage(pil_img)

        app.export_gui_img_default = load_export_gui_img(app_path('media', 'SyInt', 'ExportGUIButton.png'))
        app.export_gui_img_hover = load_export_gui_img(app_path('media', 'SyInt', 'ExportGUIButtonHover.png'))

        # Pad left side by increasing padx
        app.export_gui_label = tk.Label(export_frame, image=app.export_gui_img_default, borderwidth=0, highlightthickness=0, cursor="hand2")
        app.export_gui_label.grid(row=4, column=0, pady=15, padx=(20,0))  # <-- Increased left padding here

        # Hover handler for Export GUI button; affects export GUI button UI
        def on_export_gui_enter(e):
            app.export_gui_label.configure(image=app.export_gui_img_hover)
            try:
                play_button_hover()
            except Exception:
                pass

        # Leave handler for Export GUI button; affects export GUI button UI
        def on_export_gui_leave(e):
            app.export_gui_label.configure(image=app.export_gui_img_default)

        # Launches the Export GUI module; affects export workflow
        def on_export_gui_click(e):
            play_button_click()
            try:
                # prefer running as a module so package imports resolve
                subprocess.run([sys.executable, '-m', 'core.exportGUI'], shell=False)
            except Exception:
                try:
                    exportgui_path = app_path('core', 'exportGUI.py')
                except Exception:
                    exportgui_path = os.path.join(os.path.dirname(__file__), 'exportGUI.py')
                subprocess.run([sys.executable, exportgui_path], shell=False)

        app.export_gui_label.bind("<Enter>", on_export_gui_enter)
        app.export_gui_label.bind("<Leave>", on_export_gui_leave)
        app.export_gui_label.bind("<Button-1>", on_export_gui_click)
    except Exception as e:
        logging.error(f"Failed to load Export GUI button image: {e}")
        # Fallback launcher for Export GUI when module run fails; affects export workflow
        def _launch_export_gui():
            try:
                exportgui_path = app_path('core', 'exportGUI.py')
            except Exception:
                exportgui_path = os.path.join(os.path.dirname(__file__), 'exportGUI.py')
            subprocess.run([sys.executable, exportgui_path], shell=False)

        GUIbutton = ttk.Button(export_frame, text=" Open\nExport\n  GUI", command=_launch_export_gui, padding=(6,5), width=14)
        GUIbutton.grid(row=4, column=0, pady=15, padx=(20,0))  # <-- Increased left padding here

    # Planet aggregation export (with image and hover effect)
    try:
        # Helper to load Export Planet button images; used by planet export
        def load_export_planet_img(path):
            pil_img = Image.open(path).convert('RGBA')
            pil_img = pil_img.resize((pil_img.width // 2, pil_img.height // 2), Image.LANCZOS)
            bg_color = (37, 37, 38, 255)
            background = Image.new('RGBA', pil_img.size, bg_color)
            pil_img = Image.alpha_composite(background, pil_img)
            return ImageTk.PhotoImage(pil_img)

        app.export_planet_img_default = load_export_planet_img(app_path('media', 'SyInt', 'ExportPlanetButton.png'))
        app.export_planet_img_hover = load_export_planet_img(app_path('media', 'SyInt', 'ExportPlanetButtonHover.png'))

        app.export_planet_label = tk.Label(export_frame, image=app.export_planet_img_default, borderwidth=0, highlightthickness=0, cursor="hand2")
        app.export_planet_label.grid(row=4, column=1, padx=(20,0), pady=15)

        # Hover handler for Export Planet button; affects planet export button UI
        def on_export_planet_enter(e):
            app.export_planet_label.configure(image=app.export_planet_img_hover)
            try:
                play_button_hover()
            except Exception:
                pass

        # Leave handler for Export Planet button; affects planet export button UI
        def on_export_planet_leave(e):
            app.export_planet_label.configure(image=app.export_planet_img_default)

        # Launches planet aggregation export; affects webhook export
        def on_export_planet_click(e):
            play_button_click()
            try:
                subprocess.run([sys.executable, '-m', 'core.sub'], shell=False)
            except Exception:
                try:
                    sub_path = app_path('core', 'sub.py')
                except Exception:
                    sub_path = os.path.join(os.path.dirname(__file__), 'sub.py')
                subprocess.run([sys.executable, sub_path], shell=False)

        app.export_planet_label.bind("<Enter>", on_export_planet_enter)
        app.export_planet_label.bind("<Leave>", on_export_planet_leave)
        app.export_planet_label.bind("<Button-1>", on_export_planet_click)
    except Exception as e:
        logging.error(f"Failed to load Export Planet button image: {e}")
        # Fallback launcher for planet export; affects webhook export
        def _launch_sub():
            try:
                sub_path = app_path('core', 'sub.py')
            except Exception:
                sub_path = os.path.join(os.path.dirname(__file__), 'sub.py')
            subprocess.run([sys.executable, sub_path], shell=False)

        export_button = ttk.Button(export_frame, text="Export Planet\n     Data to\n   Webhook", command=_launch_sub, padding=(6,5), width=14)
        export_button.grid(row=4, column=1, padx=(20,0), pady=15)

    # Faction aggregation export (with image and hover effect)
    try:
        # Helper to load Export Faction button images; used by faction export
        def load_export_faction_img(path):
            pil_img = Image.open(path).convert('RGBA')
            pil_img = pil_img.resize((pil_img.width // 2, pil_img.height // 2), Image.LANCZOS)
            bg_color = (37, 37, 38, 255)
            background = Image.new('RGBA', pil_img.size, bg_color)
            pil_img = Image.alpha_composite(background, pil_img)
            return ImageTk.PhotoImage(pil_img)

        app.export_faction_img_default = load_export_faction_img(app_path('media', 'SyInt', 'ExportFactionButton.png'))
        app.export_faction_img_hover = load_export_faction_img(app_path('media', 'SyInt', 'ExportFactionButtonHover.png'))

        app.export_faction_label = tk.Label(export_frame, image=app.export_faction_img_default, borderwidth=0, highlightthickness=0, cursor="hand2")
        app.export_faction_label.grid(row=4, column=2, padx=(20,0), pady=15)

        # Hover handler for Export Faction button; affects faction export button UI
        def on_export_faction_enter(e):
            app.export_faction_label.configure(image=app.export_faction_img_hover)
            try:
                play_button_hover()
            except Exception:
                pass

        # Leave handler for Export Faction button; affects faction export button UI
        def on_export_faction_leave(e):
            app.export_faction_label.configure(image=app.export_faction_img_default)

        # Launches faction aggregation export; affects webhook export
        def on_export_faction_click(e):
            play_button_click()
            try:
                subprocess.run([sys.executable, '-m', 'core.faction'], shell=False)
            except Exception:
                try:
                    faction_path = app_path('core', 'faction.py')
                except Exception:
                    faction_path = os.path.join(os.path.dirname(__file__), 'faction.py')
                subprocess.run([sys.executable, faction_path], shell=False)

        app.export_faction_label.bind("<Enter>", on_export_faction_enter)
        app.export_faction_label.bind("<Leave>", on_export_faction_leave)
        app.export_faction_label.bind("<Button-1>", on_export_faction_click)
    except Exception as e:
        logging.error(f"Failed to load Export Faction button image: {e}")
        # Fallback launcher for faction export; affects webhook export
        def _launch_faction():
            try:
                faction_path = app_path('core', 'faction.py')
            except Exception:
                faction_path = os.path.join(os.path.dirname(__file__), 'faction.py')
            subprocess.run([sys.executable, faction_path], shell=False)

        export_button = ttk.Button(export_frame, text="Export Faction\n      Data to\n    Webhook", command=_launch_faction, padding=(6,5), width=14)
        export_button.grid(row=4, column=2, padx=(20,0), pady=15)

    # Prior 7 days aggregation export (with image and hover effect)
    try:
        # Helper to load Export 7 Days button images; used by 7-day export
        def load_export_7days_img(path):
            pil_img = Image.open(path).convert('RGBA')
            pil_img = pil_img.resize((pil_img.width // 2, pil_img.height // 2), Image.LANCZOS)
            bg_color = (37, 37, 38, 255)
            background = Image.new('RGBA', pil_img.size, bg_color)
            pil_img = Image.alpha_composite(background, pil_img)
            return ImageTk.PhotoImage(pil_img)

        app.export_7days_img_default = load_export_7days_img(app_path('media', 'SyInt', 'Export7DaysButton.png'))
        app.export_7days_img_hover = load_export_7days_img(app_path('media', 'SyInt', 'Export7DaysButtonHover.png'))

        app.export_7days_label = tk.Label(export_frame, image=app.export_7days_img_default, borderwidth=0, highlightthickness=0, cursor="hand2")
        app.export_7days_label.grid(row=4, column=3, padx=(20,0), pady=15)

        # Hover handler for Export 7 Days button; affects 7-days export button UI
        def on_export_7days_enter(e):
            app.export_7days_label.configure(image=app.export_7days_img_hover)
            try:
                play_button_hover()
            except Exception:
                pass

        # Leave handler for Export 7 Days button; affects 7-days export button UI
        def on_export_7days_leave(e):
            app.export_7days_label.configure(image=app.export_7days_img_default)

        # Launches last 7 days aggregation export; affects webhook export
        def on_export_7days_click(e):
            play_button_click()
            try:
                subprocess.run([sys.executable, '-m', 'core.expWeek'], shell=False)
            except Exception:
                try:
                    expweek_path = app_path('core', 'expWeek.py')
                except Exception:
                    expweek_path = os.path.join(os.path.dirname(__file__), 'expWeek.py')
                subprocess.run([sys.executable, expweek_path], shell=False)

        app.export_7days_label.bind("<Enter>", on_export_7days_enter)
        app.export_7days_label.bind("<Leave>", on_export_7days_leave)
        app.export_7days_label.bind("<Button-1>", on_export_7days_click)

    except Exception as e:
        logging.error(f"Failed to load Export 7 Days button image: {e}")
        # Fallback launcher for 7-days export; affects webhook export
        def _launch_expweek():
            try:
                expweek_path = app_path('core', 'expWeek.py')
            except Exception:
                expweek_path = os.path.join(os.path.dirname(__file__), 'expWeek.py')
            subprocess.run([sys.executable, expweek_path], shell=False)

        export_button = ttk.Button(export_frame, text="Export Last 7 Days\n       Data to\n     Webhook", command=_launch_expweek, padding=(6,5), width=16)
        export_button.grid(row=4, column=3, padx=(20,0), pady=15)

    # Favourite aggregation export (with image and hover effect)
    try:
        # Helper to load Export Favourites button images; used by favourites export
        def load_export_favourites_img(path):
            pil_img = Image.open(path).convert('RGBA')
            pil_img = pil_img.resize((pil_img.width // 2, pil_img.height // 2), Image.LANCZOS)
            bg_color = (37, 37, 38, 255)
            background = Image.new('RGBA', pil_img.size, bg_color)
            pil_img = Image.alpha_composite(background, pil_img)
            return ImageTk.PhotoImage(pil_img)

        app.export_favourites_img_default = load_export_favourites_img(app_path('media', 'SyInt', 'ExportFavouritesButton.png'))
        app.export_favourites_img_hover = load_export_favourites_img(app_path('media', 'SyInt', 'ExportFavouritesButtonHover.png'))

        app.export_favourites_label = tk.Label(export_frame, image=app.export_favourites_img_default, borderwidth=0, highlightthickness=0, cursor="hand2")
        app.export_favourites_label.grid(row=4, column=4, padx=(20,0), pady=15)

        # Hover handler for Export Favourites button; affects favourites export button UI
        def on_export_favourites_enter(e):
            app.export_favourites_label.configure(image=app.export_favourites_img_hover)
            try:
                play_button_hover()
            except Exception:
                pass

        # Leave handler for Export Favourites button; affects favourites export button UI
        def on_export_favourites_leave(e):
            app.export_favourites_label.configure(image=app.export_favourites_img_default)

        # Launches favourites aggregation export; affects webhook export
        def on_export_favourites_click(e):
            play_button_click()
            try:
                subprocess.run([sys.executable, '-m', 'core.favourites'], shell=False)
            except Exception:
                try:
                    fav_path = app_path('core', 'favourites.py')
                except Exception:
                    fav_path = os.path.join(os.path.dirname(__file__), 'favourites.py')
                subprocess.run([sys.executable, fav_path], shell=False)

        app.export_favourites_label.bind("<Enter>", on_export_favourites_enter)
        app.export_favourites_label.bind("<Leave>", on_export_favourites_leave)
        app.export_favourites_label.bind("<Button-1>", on_export_favourites_click)
    except Exception as e:
        logging.error(f"Failed to load Export Favourites button image: {e}")
        # Fallback launcher for favourites export; affects webhook export
        def _launch_favourites():
            try:
                fav_path = app_path('core', 'favourites.py')
            except Exception:
                fav_path = os.path.join(os.path.dirname(__file__), 'favourites.py')
            subprocess.run([sys.executable, fav_path], shell=False)

        export_button = ttk.Button(export_frame, text="Export Favourites\n        Data to\n     Webhook", command=_launch_favourites, padding=(6,5), width=16)
        export_button.grid(row=4, column=4, padx=(20,0), pady=15)

    image_button_frame = ttk.Frame(mission_frame)
    image_button_frame.grid(row=5, column=4, padx=5, pady=5)

    # Achievements export button (with image and hover effect)
    try:
        # Helper to load Export Achievements button images; used by achievements export
        def load_export_achievements_img(path):
            pil_img = Image.open(path).convert('RGBA')
            pil_img = pil_img.resize((pil_img.width // 2, pil_img.height // 2), Image.LANCZOS)
            bg_color = (37, 37, 38, 255)
            background = Image.new('RGBA', pil_img.size, bg_color)
            pil_img = Image.alpha_composite(background, pil_img)
            return ImageTk.PhotoImage(pil_img)

        app.export_achievements_img_default = load_export_achievements_img(app_path('media', 'SyInt', 'ExportAchievementsButton.png'))
        app.export_achievements_img_hover = load_export_achievements_img(app_path('media', 'SyInt', 'ExportAchievementsButtonHover.png'))

        app.export_achievements_label = tk.Label(export_frame, image=app.export_achievements_img_default, borderwidth=0, highlightthickness=0, cursor="hand2")
        app.export_achievements_label.grid(row=4, column=5, padx=(20,0), pady=15)

        app.export_achievements_label.grid(row=4, column=5, padx=(20,0), pady=15)

        # Hover handler for Export Achievements button; affects achievements export button UI
        def on_export_achievements_enter(e):
            app.export_achievements_label.configure(image=app.export_achievements_img_hover)
            try:
                play_button_hover()
            except Exception:
                pass

        # Leave handler for Export Achievements button; affects achievements export button UI
        def on_export_achievements_leave(e):
            app.export_achievements_label.configure(image=app.export_achievements_img_default)

        # Launches achievements aggregation export; affects webhook export
        def on_export_achievements_click(e):
            play_button_click()
            try:
                subprocess.run([sys.executable, '-m', 'core.Achievements'], shell=False)
            except Exception:
                try:
                    achievements_path = app_path('core', 'Achievements.py')
                except Exception:
                    achievements_path = os.path.join(os.path.dirname(__file__), 'Achievements.py')
                subprocess.run([sys.executable, achievements_path], shell=False)

        app.export_achievements_label.bind("<Enter>", on_export_achievements_enter)
        app.export_achievements_label.bind("<Leave>", on_export_achievements_leave)
        app.export_achievements_label.bind("<Button-1>", on_export_achievements_click)
    except Exception as e:
        logging.error(f"Failed to load Export Achievements button image: {e}")
        # Fallback launcher for achievements export; affects webhook export
        def _launch_achievements():
            try:
                achievements_path = app_path('core', 'Achievements.py')
            except Exception:
                achievements_path = os.path.join(os.path.dirname(__file__), 'Achievements.py')
            subprocess.run([sys.executable, achievements_path], shell=False)

        export_button = ttk.Button(export_frame, text="Export Achievements\n        Data to\n     Webhook", command=_launch_achievements, padding=(6,5), width=16)
        export_button.grid(row=4, column=5, padx=(20,0), pady=15)

    # Enforces 'No Faction' when enemy is Observing; affects subfaction state and submit button appearance
    def _force_no_faction_for_observing(*_):
        # Run after other handlers (populate -> then enforce)
        # Applies enforcement after idle to avoid race conditions; affects subfaction combobox and submit button state
        def _apply():
            if app.enemy_type.get() == "Observing":
                vals = list(subfaction_combo['values']) or []
                # Ensure "No Faction" is a valid option
                if vals != ["No Faction"]:
                    subfaction_combo['values'] = ("No Faction",)
                # Only override if not already set by persistence
                if app.subfaction_type.get() != "No Faction":
                    try:
                        subfaction_combo.set("No Faction")
                        app.subfaction_type.set("No Faction")
                    except tk.TclError:
                        pass
            # Update button based on faction
            app._update_button_for_faction()
        app.root.after_idle(_apply)

    # Re-apply whenever enemy changes and once after initial setup/persistence load
    try:
        app.enemy_type.trace_add("write", _force_no_faction_for_observing)
    except Exception:
        try:
            app.enemy_type.trace("w", lambda *a: _force_no_faction_for_observing())
        except Exception:
            pass
    app.root.after(400, _force_no_faction_for_observing)

    ###############################################################
    # END OF GUI SETUP
    ###############################################################
