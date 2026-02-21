import configparser
import json
import logging
import os
import threading
import tkinter as tk
from datetime import datetime
from tkinter import font as tkfont
from tkinter import messagebox, ttk

import pandas as pd

from core.data.data_manager import get_mission_data_service
from core.icon import BIOME_BANNERS, CAMPAIGN_ICONS, DIFFICULTY_ICONS, ENEMY_ICONS, MISSION_ICONS, PLANET_ICONS, SUBFACTION_ICONS, TITLE_ICONS, get_badge_icons, get_planet_image
from core.infrastructure.logging_config import setup_logging
from core.infrastructure.runtime_paths import app_path, resource_path
from core.ui.ui_sound import init_ui_sounds, play_button_click, play_button_hover, register_global_click_binding
from core.integrations.webhook import classify_webhook_error, format_webhook_failure_line, post_webhook
from core.config.settings_shared import get_extra_webhook_urls

try:
    # After refactor these constants live in app_core
    from core.app_core import EXCEL_FILE_PROD, EXCEL_FILE_TEST
except Exception:
    # Backwards compatibility: fall back to main if app_core is not importable
    from core.main import EXCEL_FILE_PROD, EXCEL_FILE_TEST

# Read configuration
config = configparser.ConfigParser()
config.read(app_path("config.config"))

DEBUG = config.getboolean("DEBUGGING", "DEBUG", fallback=False)
setup_logging(DEBUG)
SETTINGS_FILE = app_path("JSON", "persistence.json")


# Theme system (copied from main.py/settings.py)
def make_theme(bg, fg, entry_bg=None, entry_fg=None, button_bg=None, button_fg=None, frame_bg=None):
    # Build ttk theme palette; affects export viewer styling
    return {
        ".": {"configure": {"background": bg, "foreground": fg}},
        "TLabel": {"configure": {"background": bg, "foreground": fg}},
        "TButton": {"configure": {"background": button_bg or bg, "foreground": button_fg or fg}},
        "TEntry": {
            "configure": {
                "background": entry_bg or bg,
                "foreground": entry_fg or fg,
                "fieldbackground": entry_bg or bg,
                "insertcolor": fg,
            }
        },
        "TCheckbutton": {"configure": {"background": bg, "foreground": fg}},
        "TCombobox": {
            "configure": {
                "background": entry_bg or bg,
                "foreground": entry_fg or fg,
                "fieldbackground": entry_bg or bg,
                "insertcolor": fg,
            }
        },
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


def apply_theme(style, theme_dict):
    # Apply theme settings to ttk styles; skins export viewer UI
    for widget, opts in theme_dict.items():
        for method, cfg in opts.items():
            getattr(style, method)(widget, **cfg)


def main():
    # Launch Export Viewer window; manages table, filters, and Discord export
    root = tk.Tk()
    root.title("Mission Log Export Viewer")
    # Autosize window based on current screen resolution, center it, allow resize with min size
    try:
        screen_w = max(800, root.winfo_screenwidth())
        screen_h = max(600, root.winfo_screenheight())
        min_w, min_h = 1000, 700
        margin = 100
        init_w = min(max(int(screen_w * 0.85), min_w), screen_w - margin)
        init_h = min(max(int(screen_h * 0.80), min_h), screen_h - margin)
        pos_x = max(0, (screen_w - init_w) // 2)
        pos_y = max(0, (screen_h - init_h) // 2)
        root.geometry(f"{init_w}x{init_h}+{pos_x}+{pos_y}")
        root.minsize(min_w, min_h)
        root.resizable(True, True)
    except Exception:
        root.geometry("1400x900")
        root.minsize(1000, 700)
        root.resizable(True, True)

    # Set window icon (SuperEarth.png)
    try:
        icon_path = resource_path("LaunchMedia", "SuperEarth.png")
        from PIL import Image, ImageTk

        pil_icon = Image.open(icon_path)
        root._icon_image = ImageTk.PhotoImage(pil_icon)
        root.iconphoto(True, root._icon_image)
    except Exception as e:
        logging.warning(f"Unable to load window icon: {e}")

    # Apply theme
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # Configure tag colors for alternating rows (Stack Overflow pattern)
    def configure_row_tags():
        # Define alternating row tag colors; improves table readability
        table.tag_configure("oddrow", background="#2d2d2d", foreground="#FFFFFF")
        table.tag_configure("evenrow", background="#232323", foreground="#FFFFFF")

    apply_theme(style, DEFAULT_THEME)
    root.configure(bg=DEFAULT_THEME["."]["configure"]["background"])

    # Font system: Try to use Insignia font if available, fallback to Arial
    try:
        fs_sinclair_font = tkfont.Font(family="Insignia", size=14, weight="bold")
    except Exception:
        fs_sinclair_font = tkfont.Font(family="Arial", size=14, weight="bold")

    # Main frame
    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Notebook for tabs (future extensibility)
    notebook = ttk.Notebook(main_frame)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Export tab (with image, styled like settings.py)
    export_frame = ttk.Frame(notebook, padding="10")

    def load_tab_image(path):
        # Load and scale tab image; styles the notebook tab
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

    # Tab image (only one state)
    try:
        export_tab_img = load_tab_image(app_path("media", "Exportsys", "ExportViewerTabButton.png"))
        notebook.add(export_frame, text="", image=export_tab_img, compound=tk.CENTER, padding=0)
        notebook._export_tab_img = export_tab_img
    except Exception:
        notebook.add(export_frame, text="Export Viewer")

    # Remove tab border/highlight (like settings.py)
    style.layout(
        "TNotebook.Tab",
        [
            (
                "Notebook.tab",
                {
                    "sticky": "nswe",
                    "children": [
                        (
                            "Notebook.padding",
                            {
                                "side": "top",
                                "sticky": "nswe",
                                "children": [
                                    (
                                        "Notebook.focus",
                                        {
                                            "side": "top",
                                            "sticky": "nswe",
                                            "children": [
                                                ("Notebook.image", {"side": "left", "sticky": ""}),
                                            ],
                                        },
                                    ),
                                ],
                            },
                        ),
                    ],
                },
            ),
        ],
    )
    style.configure("TNotebook.Tab", borderwidth=0, highlightthickness=0, padding=0)
    style.map(
        "TNotebook.Tab",
        background=[
            ("selected", DEFAULT_THEME["."]["configure"]["background"]),
            ("!selected", DEFAULT_THEME["."]["configure"]["background"]),
        ],
    )

    def update_tab_image(event=None):
        # Keep tab image consistent on selection; cosmetic behavior
        # Only one tab, always selected
        notebook.tab(0, image=notebook._export_tab_img)

    notebook.bind("<<NotebookTabChanged>>", update_tab_image)
    notebook.tab(0, sticky="nsew")
    update_tab_image()

    # Table section
    table_lf = ttk.LabelFrame(
        export_frame, labelwidget=ttk.Label(export_frame, text="Mission Log Data", font=fs_sinclair_font), padding=10
    )
    table_lf.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Table (Treeview) with column headers and filtering
    # NOTE: Windows ttk themes may ignore tag-based row coloring for Treeview rows.
    # For true alternation, consider using ttkbootstrap or a custom widget.
    style.configure(
        "Treeview",
        background="#232323",
        foreground="#FFFFFF",
        fieldbackground="#232323",
        rowheight=24,
        bordercolor="#232323",
        lightcolor="#232323",
        darkcolor="#232323",
    )
    style.configure(
        "Treeview.Heading",
        background="#252526",
        foreground="#FFFFFF",
        font=(fs_sinclair_font.actual("family"), 10, "bold"),
    )
    style.map("Treeview", background=[("selected", "#4C4C4C")], foreground=[("selected", "#FFFFFF")])
    
    # Create scrollbars for the table
    vsb = ttk.Scrollbar(table_lf, orient="vertical")
    hsb = ttk.Scrollbar(table_lf, orient="horizontal")
    
    table = ttk.Treeview(
        table_lf, 
        show="headings", 
        selectmode="extended", 
        style="Treeview",
        yscrollcommand=vsb.set,
        xscrollcommand=hsb.set
    )
    
    vsb.config(command=table.yview)
    hsb.config(command=table.xview)
    
    # Grid layout for table and scrollbars
    table.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    
    # Configure grid weights so table expands
    table_lf.grid_rowconfigure(0, weight=1)
    table_lf.grid_columnconfigure(0, weight=1)

    # Button section (bottom of window)
    button_frame = ttk.Frame(root)
    button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

    # Reset filters button
    def reset_filters():
        # Reset all dropdown filters to 'All'; refreshes table view
        enemy_var.set("All")
        subfaction_var.set("All")
        sector_var.set("All")
        planet_var.set("All")

    # Load button images

    def load_button_image(path, box=(160, 48), preserve_aspect=True, pad_to_box=True):
        # Load button image with padding; used for hover/static states
        # Keeps image aspect ratio; pads to a consistent box so hover/static sizes match
        from PIL import Image, ImageTk

        img = Image.open(path)
        if preserve_aspect:
            # Downscale to fit within box while preserving aspect
            img.thumbnail(box, Image.LANCZOS)
            if pad_to_box:
                # Create transparent canvas and center the image
                canvas = Image.new("RGBA", box, (0, 0, 0, 0))
                x = (box[0] - img.width) // 2
                y = (box[1] - img.height) // 2
                # If source has alpha, use it as mask to preserve edges
                canvas.paste(img, (x, y), img if img.mode in ("RGBA", "LA") else None)
                img = canvas
        else:
            img = img.resize(box, Image.LANCZOS)
        return ImageTk.PhotoImage(img)

    clear_btn_img = load_button_image(app_path("media", "Exportsys", "ClearFiltersButton.png"))
    clear_btn_img_hover = load_button_image(app_path("media", "Exportsys", "ClearFiltersButtonHover.png"))

    reset_btn = tk.Label(
        button_frame,
        image=clear_btn_img,
        cursor="hand2",
        bd=0,
        highlightthickness=0,
        borderwidth=0,
        relief="flat",
        background=DEFAULT_THEME["."]["configure"]["background"],
    )
    reset_btn.image = clear_btn_img  # Prevent garbage collection
    reset_btn.pack(side=tk.LEFT, padx=5)

    def on_enter(event):
        # Hover handler for Clear Filters button; updates image and plays sound
        reset_btn.configure(image=clear_btn_img_hover)
        reset_btn.image = clear_btn_img_hover
        try:
            play_button_hover()
        except Exception:
            pass

    def on_leave(event):
        # Mouse leave handler for Clear Filters button; restores default image
        reset_btn.configure(image=clear_btn_img)
        reset_btn.image = clear_btn_img

    reset_btn.bind("<Enter>", on_enter)
    reset_btn.bind("<Leave>", on_leave)
    reset_btn.bind("<Button-1>", lambda e: clear_all_filters())

    # Initialize & bind UI sounds
    try:
        init_ui_sounds(preload=True)
        register_global_click_binding(root)
    except Exception:
        pass

    # Refresh button
    def refresh_table():
        # Reload Excel into table and reapply current filters
        nonlocal full_df
        full_df = load_table()
        filter_table()

    # Load refresh button images
    refresh_btn_img = load_button_image(app_path("media", "Exportsys", "RefreshButton.png"))
    refresh_btn_img_hover = load_button_image(app_path("media", "Exportsys", "RefreshButtonHover.png"))

    refresh_btn = tk.Label(
        button_frame,
        image=refresh_btn_img,
        cursor="hand2",
        bd=0,
        highlightthickness=0,
        borderwidth=0,
        relief="flat",
        background=DEFAULT_THEME["."]["configure"]["background"],
    )
    refresh_btn.image = refresh_btn_img  # Prevent garbage collection
    refresh_btn.pack(side=tk.LEFT, padx=5)

    def on_refresh_enter(event):
        # Hover handler for Refresh button; updates image and plays sound
        refresh_btn.configure(image=refresh_btn_img_hover)
        refresh_btn.image = refresh_btn_img_hover
        try:
            play_button_hover()
        except Exception:
            pass

    def on_refresh_leave(event):
        # Mouse leave handler for Refresh button; restores default image
        refresh_btn.configure(image=refresh_btn_img)
        refresh_btn.image = refresh_btn_img

    def on_refresh_click(event):
        # Click handler for Refresh button; reloads table data
        play_button_click()
        refresh_table()

    refresh_btn.bind("<Enter>", on_refresh_enter)
    refresh_btn.bind("<Leave>", on_refresh_leave)
    refresh_btn.bind("<Button-1>", on_refresh_click)

    # Removed Preview Embed feature as requested

    # Post to Discord helper
    def post_discord(webhook_url: str, payload: dict, timeout: int = 10):
        success, _, err = post_webhook(
            webhook_url,
            json_payload=payload,
            timeout=timeout,
            retries=2,
        )
        return success, err

    # Submit a single mission as a revision/resubmission
    def submit_mission_revision():
        # Format selected mission(s) and send to Discord
        # Single selection: detailed revision report
        # Multiple selections: aggregated summary report
        selected_ids = list(table.selection())
        
        # Validate at least one row is selected
        if len(selected_ids) == 0:
            messagebox.showwarning(
                "Export Submission",
                "Please select at least one mission to export."
            )
            return
        
        # Branch based on selection count
        if len(selected_ids) == 1:
            # Single mission: Use detailed revision format
            submit_single_mission_revision(selected_ids[0])
        else:
            # Multiple missions: Use aggregated summary format
            submit_multiple_missions_export(selected_ids)
    
    def submit_single_mission_revision(row_id):
        # Original single-mission revision logic
        columns = list(table["columns"]) if table["columns"] else []
        row_values = tuple(table.item(row_id, "values"))
        
        if not columns or not row_values:
            messagebox.showerror("Revision Submission", "Unable to read selected mission data.")
            return
        
        # Build data dict from row
        data_dict = {c: v for c, v in zip(columns, row_values)}
        
        # Get the row index from the treeview directly (more reliable than matching back to Excel)
        all_items = table.get_children()
        matched_row_index = all_items.index(row_id) if row_id in all_items else -1
        logging.info(f"DEBUG: Selected row_id={row_id}, matched_row_index={matched_row_index}, total items={len(all_items)}")
        
        # Load webhooks for revision submission (use export webhooks, not mission webhooks)
        webhooks = []
        dcord_data = {}
        try:
            dcord_path = app_path("JSON", "DCord.json")
            with open(dcord_path, "r", encoding="utf-8") as f:
                dcord_data = json.load(f)
            
            # Use export webhooks for revision submissions
            if isinstance(dcord_data.get("discord_webhooks_export"), list):
                webhooks = [u for u in dcord_data["discord_webhooks_export"] if isinstance(u, str) and u.strip()]
            
            if not webhooks and isinstance(dcord_data.get("discord_webhooks_export_labeled"), list):
                for item in dcord_data["discord_webhooks_export_labeled"]:
                    if isinstance(item, dict) and item.get("url"):
                        webhooks.append(item["url"])
            
            # Fallback to regular webhooks if no export-specific ones configured
            if not webhooks and isinstance(dcord_data.get("discord_webhooks"), list):
                webhooks = [u for u in dcord_data["discord_webhooks"] if isinstance(u, str) and u.strip()]
            
            # Add extra export webhooks if configured
            extra_export = get_extra_webhook_urls("export")
            if extra_export:
                webhooks = list(dict.fromkeys(webhooks + extra_export))
        except Exception as e:
            logging.warning(f"Failed to load export webhooks for revision: {e}")
        
        if not webhooks:
            messagebox.showerror("Revision Submission", "No Discord webhooks configured for revisions.")
            return
        
        # Get Discord UID
        uid = dcord_data.get("discord_uid", "0")
        
        # Get mission number from the treeview row index
        mission_number = matched_row_index + 1  # Convert to 1-based mission number
        logging.info(f"DEBUG: mission_number={mission_number}, will compare with index {matched_row_index - 1}")
        
        # Extract mission data fields
        kills = str(data_dict.get("Kills", "0")) or "0"
        deaths = str(data_dict.get("Deaths", "1")) or "1"
        try:
            kdr = f"{(int(kills) / max(1, int(deaths))):.2f}"
        except (ValueError, ZeroDivisionError):
            kdr = "-"
        
        # Load badge icons (similar to send_to_discord logic)
        badge_string = ""
        try:
            app_data_path = os.path.dirname(excel_file) if excel_file else os.path.join(os.getenv("LOCALAPPDATA"), "MLHD2")
            from core.icon import get_badge_icons
            badge_data = get_badge_icons(DEBUG, app_data_path, "%d-%m-%Y %H:%M:%S")
            
            # Build badge string: always-on badges first
            always_on_order = ["bicon", "ticon", "yearico", "PIco"]
            badge_items = []
            for k in always_on_order:
                if badge_data.get(k):
                    badge_items.append(badge_data[k])
            
            # Load user's badge display preference from DCord.json if available
            try:
                if os.path.exists(app_path("JSON", "DCord.json")):
                    with open(app_path("JSON", "DCord.json"), "r", encoding="utf-8") as f:
                        dcord_badge_data = json.load(f)
                else:
                    dcord_badge_data = {}
            except Exception:
                dcord_badge_data = {}
            
            display_pref = dcord_badge_data.get("display_badges", None)
            
            # Add user-selected badges (up to 4)
            selected_count = 0
            if isinstance(display_pref, list) and display_pref:
                for k in display_pref:
                    if selected_count >= 4:
                        break
                    if badge_data.get(k):
                        badge_items.append(badge_data[k])
                        selected_count += 1
            
            badge_string = "".join(badge_items)
        except Exception as e:
            logging.warning(f"Error loading badges: {e}")
        
        # Load icon config for flair and other icons (match discord_integration.py)
        import configparser as cp
        iconconfig = cp.ConfigParser()
        iconconfig.read(app_path("icon.config"))
        try:
            orphan_icon_conf = app_path("orphan", "icon.config")
            if os.path.exists(orphan_icon_conf):
                iconconfig.read(orphan_icon_conf)
        except OSError:
            pass
        
        # Get flair icons and Super Earth icon
        FlairLeftIco = iconconfig["MiscIcon"].get("Flair Left", "") if "MiscIcon" in iconconfig else ""
        FlairRightIco = iconconfig["MiscIcon"].get("Flair Right", "") if "MiscIcon" in iconconfig else ""
        SEIco = iconconfig["MiscIcon"].get("Super Earth Icon", "") if "MiscIcon" in iconconfig else ""
        
        # Get icon references
        title_icon = TITLE_ICONS.get(data_dict.get('Title', ''), '')
        planet_icon = PLANET_ICONS.get(data_dict.get('Planet', ''), '')
        if not planet_icon:
            planet_icon = SEIco
        enemy_icon = ENEMY_ICONS.get(data_dict.get('Enemy Type', ''), '')
        subfaction_icon = SUBFACTION_ICONS.get(data_dict.get('Enemy Subfaction', ''), '')
        campaign_icon = CAMPAIGN_ICONS.get(data_dict.get('Mission Category', ''), '')
        mission_icon = MISSION_ICONS.get(data_dict.get('Mission Type', ''), '')
        diff_icon = DIFFICULTY_ICONS.get(data_dict.get('Difficulty', ''), '')
        
        # Get system color based on enemy type
        try:
            from core.icon import SYSTEM_COLORS
            system_color = int(SYSTEM_COLORS.get(data_dict.get('Enemy Type', ''), "7257043"))
        except (TypeError, ValueError):
            system_color = 7257043
        
        # Get rating stars
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
        gold_count = rating_stars.get(data_dict.get('Rating', ''), 0)
        Stars = GoldStar * gold_count + GreyStar * (5 - gold_count)
        
        # Get performance icons (killico, deathico) - compare against the previous mission chronologically
        killico = ""
        deathico = ""
        logging.info(f"DEBUG: matched_row_index={matched_row_index}, excel_file exists={os.path.exists(excel_file)}")
        try:
            if os.path.exists(excel_file) and matched_row_index > 0:
                # Load the file again to get previous mission
                df = pd.read_excel(excel_file)
                logging.info(f"DEBUG: loaded {len(df)} rows from Excel")
                if len(df) > matched_row_index:
                    # Get the mission immediately before the selected one
                    prev_mission = df.iloc[matched_row_index - 1]
                    prev_kills = int(prev_mission["Kills"])
                    prev_deaths = int(prev_mission["Deaths"])
                    current_kills = int(kills)
                    current_deaths = int(deaths)
                    logging.info(f"DEBUG: Comparing kills {current_kills} vs {prev_kills}, deaths {current_deaths} vs {prev_deaths}")
                    
                    # Compare kills: positive if more, negative if less, neutral if same
                    if current_kills > prev_kills:
                        killico = iconconfig["MiscIcon"].get("Positive", "") if "MiscIcon" in iconconfig else ""
                    elif current_kills < prev_kills:
                        killico = iconconfig["MiscIcon"].get("Negative", "") if "MiscIcon" in iconconfig else ""
                    else:
                        killico = iconconfig["MiscIcon"].get("Neutral", "") if "MiscIcon" in iconconfig else ""
                    
                    # Compare deaths: positive if fewer (lower is better), negative if more, neutral if same
                    if current_deaths < prev_deaths:
                        deathico = iconconfig["MiscIcon"].get("PositiveDeaths", "") if "MiscIcon" in iconconfig else ""
                    elif current_deaths > prev_deaths:
                        deathico = iconconfig["MiscIcon"].get("NegativeDeaths", "") if "MiscIcon" in iconconfig else ""
                    else:
                        deathico = iconconfig["MiscIcon"].get("Neutral", "") if "MiscIcon" in iconconfig else ""
                    
                    logging.info(f"DEBUG: killico='{killico}', deathico='{deathico}'")
            else:
                logging.info(f"DEBUG: Skipped performance icons - matched_row_index={matched_row_index}, file exists={os.path.exists(excel_file)}")
        except Exception as e:
            logging.warning(f"Error calculating performance icons: {e}", exc_info=True)
        
        # Get MO and DSS labels
        # Check if Major Order is active (handle both boolean False and string "False")
        mo_value = data_dict.get("Major Order", "False")
        mo_is_active = mo_value not in [False, "False", "No", "", None]
        mo_label = str(mo_value)
        if mo_is_active and "MiscIcon" in iconconfig:
            mo_ico = iconconfig["MiscIcon"].get("MO", "")
            mo_label = f"{mo_label} {mo_ico}"
        
        # Check if DSS is active (handle both boolean False and string "False")
        dss_value = data_dict.get("DSS Active", "False")
        dss_is_active = dss_value not in [False, "False", "No", "", None]
        dss_label = str(dss_value)
        if dss_is_active and "MiscIcon" in iconconfig:
            dss_ico = iconconfig["MiscIcon"].get("DSS", "")
            dss_label = f"{dss_label} {dss_ico}"
        
        dss_mod_label = str(data_dict.get("DSS Modifier", "Inactive"))
        dss_mod_ico = ""  # Can add DSS modifier icon lookup here if needed
        
        # Get mega label (Mega Factory for Cyberstan, Mega City for others)
        mega_label = "Mega Factory" if str(data_dict.get("Planet", "")).strip().lower() == "cyberstan" else "Mega City"
        
        # Build the revision embed (matching discord_integration.py structure exactly)
        date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        embed = {
            "title": f"{data_dict.get('Super Destroyer', 'Unknown')}\nDeployed {data_dict.get('Helldivers', 'Helldiver')}\n{badge_string}",
            "description": (
                f"**Level {data_dict.get('Level', 'N/A')} | {data_dict.get('Title', 'N/A')} {title_icon}\n"
                f"Mission: {mission_number} [REVISION]**\n\n"
                f"{FlairLeftIco} {SEIco} **Galactic Intel** {planet_icon} {FlairRightIco}\n"
                f"> Sector: {data_dict.get('Sector', 'N/A')}\n"
                f"> Planet: {data_dict.get('Planet', 'N/A')}\n"
                f"> {mega_label}: {data_dict.get('Mega Structure', data_dict.get('Mega City', 'N/A'))}\n"
                f"> Major Order: {mo_label}\n"
                f"> DSS Active: {dss_label}\n"
                f"> DSS Modifier: {dss_mod_label} {dss_mod_ico}\n\n"
            ),
            "color": system_color,
            "fields": [
                {
                    "name": f"{FlairLeftIco} {enemy_icon} **Enemy Intel** {subfaction_icon} {FlairRightIco}",
                    "value": (
                        f"> Faction: {data_dict.get('Enemy Type', 'N/A')}\n"
                        f"> Subfaction: {data_dict.get('Enemy Subfaction', 'N/A')}\n"
                        f"> Campaign: {data_dict.get('Mission Category', 'N/A')}\n\n"
                        f"{FlairLeftIco} {campaign_icon} **Mission Intel** {mission_icon} {FlairRightIco}\n"
                        f"> Mission: {data_dict.get('Mission Type', 'N/A')}\n"
                        f"> Difficulty: {data_dict.get('Difficulty', 'N/A')} {diff_icon}\n"
                        f"> Kills: {kills} {killico}\n"
                        f"> Deaths: {deaths} {deathico}\n"
                        f"> KDR: {kdr}\n"
                        f"> Rating: {data_dict.get('Rating', 'N/A')}\n\n"
                        f"{Stars}\n"
                    ),
                }
            ],
            "author": {
                "name": f"Super Earth Mission Report - Revision\nDate: {date}",
                "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356001307596427564/NwNzS9B.png?ex=67eafa21&is=67e9a8a1&hm=7e204265cbcdeaf96d7b244cd63992c4ef10dc18befbcf2ed39c3a269af14ec0&",
            },
            "footer": {
                "text": f"{uid}",
                "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356025859319926784/5cwgI15.png?ex=67eb10fe&is=67e9bf7e&hm=ab6326a9da1e76125238bf3668acac8ad1e43b24947fc6d878d7b94c8a60ab28&",
            },
            "image": {"url": BIOME_BANNERS.get(data_dict.get("Planet", ""), "")},
            "thumbnail": {"url": get_planet_image(data_dict.get("Planet", ""))},
        }
        
        # Show progress window
        progress_win = tk.Toplevel(root)
        progress_win.title("Revision Progress")
        progress_win.transient(root)
        progress_win.grab_set()
        progress_win.resizable(False, False)
        progress_win.configure(bg=DEFAULT_THEME["."]["configure"]["background"])
        ttk.Label(progress_win, text="Submitting mission revision...").pack(anchor=tk.W, padx=12, pady=(12, 6))
        progress_var = tk.StringVar(value=f"0/{len(webhooks)} submitted")
        ttk.Label(progress_win, textvariable=progress_var).pack(anchor=tk.W, padx=12)
        progress_bar = ttk.Progressbar(
            progress_win, orient=tk.HORIZONTAL, mode="determinate", maximum=len(webhooks), value=0, length=380
        )
        progress_bar.pack(fill=tk.X, padx=12, pady=(6, 8))
        status_box = tk.Text(progress_win, width=60, height=6, state=tk.DISABLED, wrap=tk.WORD)
        status_box.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        
        def _append_status(line: str):
            status_box.configure(state=tk.NORMAL)
            status_box.insert(tk.END, f"{line}\n")
            status_box.see(tk.END)
            status_box.configure(state=tk.DISABLED)
        
        def worker():
            ok = 0
            fail = 0
            failures = []
            
            for i, webhook_url in enumerate(webhooks):
                success, err = post_discord(webhook_url, {"embeds": [embed]})
                if success:
                    ok += 1
                    line = f"✓ Webhook {i+1}: revision submitted"
                else:
                    fail += 1
                    failures.append((webhook_url, err))
                    short_reason, _ = classify_webhook_error(err)
                    line = f"✗ Webhook {i+1}: failed ({short_reason})"
                
                try:
                    root.after(
                        0,
                        lambda s=i+1, o=ok, f=fail: (
                            progress_bar.configure(value=s),
                            progress_var.set(f"{s}/{len(webhooks)} completed"),
                        ),
                    )
                    root.after(0, lambda l=line: _append_status(l))
                except Exception:
                    pass
            
            def finish_ui():
                try:
                    progress_win.destroy()
                except Exception:
                    pass
                
                if fail:
                    detail_lines = [format_webhook_failure_line(url, err) for url, err in failures[:3]]
                    suffix = "\n- ..." if len(failures) > 3 else ""
                    messagebox.showinfo(
                        "Revision Submission",
                        f"Revision submitted to {ok}/{ok + fail} webhook(s).\n\n"
                        f"Details:\n{chr(10).join(detail_lines)}{suffix}",
                    )
                else:
                    messagebox.showinfo(
                        "Revision Submission",
                        f"Mission revision successfully submitted to {ok} webhook(s)!",
                    )
            
            root.after(0, finish_ui)
        
        threading.Thread(target=worker, daemon=True).start()
    
    def submit_multiple_missions_export(selected_ids):
        # Aggregate multiple selected missions into a summary export (observation-style)
        columns = list(table["columns"]) if table["columns"] else []
        
        # Collect all selected rows into a list of dicts
        selected_missions = []
        for row_id in selected_ids:
            row_values = tuple(table.item(row_id, "values"))
            if columns and row_values:
                selected_missions.append({c: v for c, v in zip(columns, row_values)})
        
        if not selected_missions:
            messagebox.showerror("Export Submission", "Unable to read selected mission data.")
            return
        
        # Convert to DataFrame for easier analysis
        selected_df = pd.DataFrame(selected_missions)
        
        # Convert numeric columns from strings to integers
        numeric_columns = ["Kills", "Deaths", "Level"]
        for col in numeric_columns:
            if col in selected_df.columns:
                selected_df[col] = pd.to_numeric(selected_df[col], errors='coerce').fillna(0).astype(int)
        
        # Load webhooks for export
        webhooks = []
        dcord_data = {}
        try:
            dcord_path = app_path("JSON", "DCord.json")
            with open(dcord_path, "r", encoding="utf-8") as f:
                dcord_data = json.load(f)
            
            # Use export webhooks
            if isinstance(dcord_data.get("discord_webhooks_export"), list):
                webhooks = [u for u in dcord_data["discord_webhooks_export"] if isinstance(u, str) and u.strip()]
            
            if not webhooks and isinstance(dcord_data.get("discord_webhooks_export_labeled"), list):
                for item in dcord_data["discord_webhooks_export_labeled"]:
                    if isinstance(item, dict) and item.get("url"):
                        webhooks.append(item["url"])
            
            if not webhooks and isinstance(dcord_data.get("discord_webhooks"), list):
                webhooks = [u for u in dcord_data["discord_webhooks"] if isinstance(u, str) and u.strip()]
            
            # Add extra export webhooks
            extra_export = get_extra_webhook_urls("export")
            if extra_export:
                webhooks = list(dict.fromkeys(webhooks + extra_export))
        except Exception as e:
            logging.error(f"Failed to load export webhooks: {e}")
        
        if not webhooks:
            messagebox.showerror("Export Submission", "No export webhooks configured.")
            return
        
        uid = dcord_data.get("discord_uid", "0")
        
        # Calculate aggregate statistics
        total_missions = len(selected_df)
        total_kills = int(selected_df["Kills"].sum()) if "Kills" in selected_df.columns else 0
        total_deaths = int(selected_df["Deaths"].sum()) if "Deaths" in selected_df.columns else 0
        kdr = f"{(total_kills / max(1, total_deaths)):.2f}"
        
        # Calculate success/failure rates
        failed_missions = len(selected_df[selected_df["Rating"] == "Disgraceful Conduct"]) if "Rating" in selected_df.columns else 0
        success_missions = total_missions - failed_missions
        success_percentage = (success_missions / total_missions * 100) if total_missions > 0 else 0
        failure_percentage = (failed_missions / total_missions * 100) if total_missions > 0 else 0
        
        # Get most common values
        most_common_planet = selected_df["Planet"].mode().iloc[0] if "Planet" in selected_df.columns and not selected_df["Planet"].mode().empty else "Various"
        most_common_sector = selected_df["Sector"].mode().iloc[0] if "Sector" in selected_df.columns and not selected_df["Sector"].mode().empty else "Various"
        most_common_enemy = selected_df["Enemy Type"].mode().iloc[0] if "Enemy Type" in selected_df.columns and not selected_df["Enemy Type"].mode().empty else "Various"
        most_common_subfaction = selected_df["Enemy Subfaction"].mode().iloc[0] if "Enemy Subfaction" in selected_df.columns and not selected_df["Enemy Subfaction"].mode().empty else "Various"
        most_common_category = selected_df["Mission Category"].mode().iloc[0] if "Mission Category" in selected_df.columns and not selected_df["Mission Category"].mode().empty else "Various"
        most_common_mission = selected_df["Mission Type"].mode().iloc[0] if "Mission Type" in selected_df.columns and not selected_df["Mission Type"].mode().empty else "Various"
        most_common_difficulty = selected_df["Difficulty"].mode().iloc[0] if "Difficulty" in selected_df.columns and not selected_df["Difficulty"].mode().empty else "Various"
        
        # Count occurrences
        planet_count = len(selected_df[selected_df["Planet"] == most_common_planet]) if most_common_planet != "Various" else 0
        enemy_count = len(selected_df[selected_df["Enemy Type"] == most_common_enemy]) if most_common_enemy != "Various" else 0
        subfaction_count = len(selected_df[selected_df["Enemy Subfaction"] == most_common_subfaction]) if most_common_subfaction != "Various" else 0
        category_count = len(selected_df[selected_df["Mission Category"] == most_common_category]) if most_common_category != "Various" else 0
        mission_count = len(selected_df[selected_df["Mission Type"] == most_common_mission]) if most_common_mission != "Various" else 0
        difficulty_count = len(selected_df[selected_df["Difficulty"] == most_common_difficulty]) if most_common_difficulty != "Various" else 0
        
        # Get user info from most recent selected mission
        helldiver_ses = selected_df["Super Destroyer"].iloc[-1] if "Super Destroyer" in selected_df.columns else "Unknown"
        helldiver_name = selected_df["Helldivers"].iloc[-1] if "Helldivers" in selected_df.columns else "Unknown"
        helldiver_level = selected_df["Level"].iloc[-1] if "Level" in selected_df.columns else 0
        helldiver_title = selected_df["Title"].iloc[-1] if "Title" in selected_df.columns else "Unknown"
        
        # Load badge icons
        badge_string = ""
        try:
            app_data_path = os.path.dirname(excel_file) if excel_file else os.path.join(os.getenv("LOCALAPPDATA"), "MLHD2")
            badge_data = get_badge_icons(DEBUG, app_data_path, "%d-%m-%Y %H:%M:%S")
            
            always_on_order = ["bicon", "ticon", "yearico", "PIco"]
            badge_items = []
            for k in always_on_order:
                if badge_data.get(k):
                    badge_items.append(badge_data[k])
            
            try:
                if os.path.exists(app_path("JSON", "DCord.json")):
                    with open(app_path("JSON", "DCord.json"), "r", encoding="utf-8") as f:
                        dcord_badge_data = json.load(f)
                else:
                    dcord_badge_data = {}
            except Exception:
                dcord_badge_data = {}
            
            display_pref = dcord_badge_data.get("display_badges", None)
            selected_count = 0
            if isinstance(display_pref, list) and display_pref:
                for k in display_pref:
                    if selected_count >= 4:
                        break
                    if badge_data.get(k):
                        badge_items.append(badge_data[k])
                        selected_count += 1
            
            badge_string = "".join(badge_items)
        except Exception as e:
            logging.warning(f"Error loading badges: {e}")
        
        # Load icon config
        import configparser as cp
        iconconfig = cp.ConfigParser()
        iconconfig.read(app_path("icon.config"))
        try:
            orphan_icon_conf = app_path("orphan", "icon.config")
            if os.path.exists(orphan_icon_conf):
                iconconfig.read(orphan_icon_conf)
        except OSError:
            pass
        
        # Get flair icons
        from core.utils import get_effective_flair
        flair_colour = get_effective_flair()
        if flair_colour.lower() == "gold":
            FlairLeftIco = iconconfig["MiscIcon"].get("Gold Flair Left", iconconfig["MiscIcon"]["Flair Left"])
            FlairRightIco = iconconfig["MiscIcon"].get("Gold Flair Right", iconconfig["MiscIcon"]["Flair Right"])
        elif flair_colour.lower() == "blue":
            FlairLeftIco = iconconfig["MiscIcon"].get("Blue Flair Left", iconconfig["MiscIcon"]["Flair Left"])
            FlairRightIco = iconconfig["MiscIcon"].get("Blue Flair Right", iconconfig["MiscIcon"]["Flair Right"])
        elif flair_colour.lower() == "red":
            FlairLeftIco = iconconfig["MiscIcon"].get("Red Flair Left", iconconfig["MiscIcon"]["Flair Left"])
            FlairRightIco = iconconfig["MiscIcon"].get("Red Flair Right", iconconfig["MiscIcon"]["Flair Right"])
        else:
            FlairLeftIco = iconconfig["MiscIcon"].get("Flair Left", "")
            FlairRightIco = iconconfig["MiscIcon"].get("Flair Right", "")
        
        SEIco = iconconfig["MiscIcon"].get("Super Earth Icon", "") if "MiscIcon" in iconconfig else ""
        KillIco = iconconfig["MiscIcon"].get("Kills", "") if "MiscIcon" in iconconfig else ""
        DeathIco = iconconfig["MiscIcon"].get("Deaths", "") if "MiscIcon" in iconconfig else ""
        KDRIco = iconconfig["MiscIcon"].get("KDR", "") if "MiscIcon" in iconconfig else ""
        GoldStarIco = iconconfig["Stars"].get("GoldStar", "") if "Stars" in iconconfig else ""
        
        # Get icons
        title_icon = TITLE_ICONS.get(helldiver_title, '')
        planet_icon = PLANET_ICONS.get(most_common_planet, '') if most_common_planet != "Various" else SEIco
        enemy_icon = ENEMY_ICONS.get(most_common_enemy, '') if most_common_enemy != "Various" else ""
        subfaction_icon = SUBFACTION_ICONS.get(most_common_subfaction, '') if most_common_subfaction != "Various" else ""
        category_icon = CAMPAIGN_ICONS.get(most_common_category, '') if most_common_category != "Various" else ""
        mission_icon = MISSION_ICONS.get(most_common_mission, '') if most_common_mission != "Various" else ""
        diff_icon = DIFFICULTY_ICONS.get(most_common_difficulty, '') if most_common_difficulty != "Various" else ""
        
        # Calculate faction-specific kills
        faction_kill_lines = ""
        for faction in ["Automatons", "Terminids", "Illuminate"]:
            faction_data = selected_df[selected_df["Enemy Type"] == faction] if "Enemy Type" in selected_df.columns else pd.DataFrame()
            if not faction_data.empty:
                faction_kills = int(faction_data["Kills"].sum()) if "Kills" in faction_data.columns else 0
                if faction_kills > 0:
                    faction_icon = ENEMY_ICONS.get(faction, "")
                    faction_kill_lines += f"> Dead {faction} - {faction_kills} {faction_icon}\n"
        
        if total_deaths > 0:
            faction_kill_lines += f"> Dead Helldivers - {total_deaths} {DeathIco}\n\n"
        
        # Get system color based on most common enemy
        try:
            from core.icon import SYSTEM_COLORS
            system_color = int(SYSTEM_COLORS.get(most_common_enemy, "7257043")) if most_common_enemy != "Various" else 7257043
        except (TypeError, ValueError):
            system_color = 7257043
        
        # Build the aggregated embed
        date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        embed = {
            "title": f"{helldiver_ses}\nHelldiver: {helldiver_name}\n{badge_string}",
            "description": (
                f"**Level {helldiver_level} | {helldiver_title} {title_icon}**\n\n"
                f"{FlairLeftIco} {SEIco} **Mission Export Summary** {SEIco} {FlairRightIco}\n"
                f"> Total Missions - {total_missions}\n"
                f"> Missions Completed - {success_missions} ({success_percentage:.1f}%)\n"
                f"> Missions Failed - {failed_missions} ({failure_percentage:.1f}%)\n"
                f"> Most Common Sector - {most_common_sector}\n"
                f"> Most Common Planet - {most_common_planet} {planet_icon}" + (f" (x{planet_count})" if planet_count > 0 else "") + "\n\n"
                f"{FlairLeftIco} {KillIco} **Combat Intel** {KDRIco} {FlairRightIco}\n"
                f"> Kill to Death Ratio - {total_kills} : {total_deaths}\n"
                f"> KDR - {kdr}\n"
                + faction_kill_lines +
                f"{FlairLeftIco} {GoldStarIco} **Priority Intel** {GoldStarIco} {FlairRightIco}\n"
                f"> Mission - {most_common_mission} {mission_icon}" + (f" (x{mission_count})" if mission_count > 0 else "") + "\n"
                f"> Campaign - {most_common_category} {category_icon}" + (f" (x{category_count})" if category_count > 0 else "") + "\n"
                f"> Faction - {most_common_enemy} {enemy_icon}" + (f" (x{enemy_count})" if enemy_count > 0 else "") + "\n"
                f"> Subfaction - {most_common_subfaction} {subfaction_icon}" + (f" (x{subfaction_count})" if subfaction_count > 0 else "") + "\n"
                f"> Difficulty - {most_common_difficulty} {diff_icon}" + (f" (x{difficulty_count})" if difficulty_count > 0 else "") + "\n\n"
            ),
            "color": system_color,
            "author": {
                "name": f"SEAF Mission Export Summary\nDate: {date}",
                "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356001307596427564/NwNzS9B.png?ex=67eafa21&is=67e9a8a1&hm=7e204265cbcdeaf96d7b244cd63992c4ef10dc18befbcf2ed39c3a269af14ec0&",
            },
            "footer": {
                "text": f"{uid}",
                "icon_url": "https://cdn.discordapp.com/attachments/1340508329977446484/1356025859319926784/5cwgI15.png?ex=67eb10fe&is=67e9bf7e&hm=ab6326a9da1e76125238bf3668acac8ad1e43b24947fc6d878d7b94c8a60ab28&",
            },
            "image": {"url": BIOME_BANNERS.get(most_common_planet, "") if most_common_planet != "Various" else ""},
            "thumbnail": {"url": get_planet_image(most_common_planet) if most_common_planet != "Various" else ""},
        }
        
        # Show progress window
        progress_win = tk.Toplevel(root)
        progress_win.title("Export Progress")
        progress_win.transient(root)
        progress_win.grab_set()
        progress_win.resizable(False, False)
        progress_win.configure(bg=DEFAULT_THEME["."]["configure"]["background"])
        ttk.Label(progress_win, text=f"Exporting {total_missions} missions...").pack(anchor=tk.W, padx=12, pady=(12, 6))
        progress_var = tk.StringVar(value=f"0/{len(webhooks)} submitted")
        ttk.Label(progress_win, textvariable=progress_var).pack(anchor=tk.W, padx=12)
        progress_bar = ttk.Progressbar(
            progress_win, orient=tk.HORIZONTAL, mode="determinate", maximum=len(webhooks), value=0, length=380
        )
        progress_bar.pack(fill=tk.X, padx=12, pady=(6, 8))
        status_box = tk.Text(progress_win, width=60, height=6, state=tk.DISABLED, wrap=tk.WORD)
        status_box.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        
        def _append_status(line: str):
            status_box.configure(state=tk.NORMAL)
            status_box.insert(tk.END, f"{line}\n")
            status_box.see(tk.END)
            status_box.configure(state=tk.DISABLED)
        
        def worker():
            ok = 0
            fail = 0
            failures = []
            
            for i, webhook_url in enumerate(webhooks):
                success, err = post_discord(webhook_url, {"embeds": [embed]})
                if success:
                    ok += 1
                    line = f"✓ Webhook {i+1}: export submitted"
                else:
                    fail += 1
                    failures.append((webhook_url, err))
                    short_reason, _ = classify_webhook_error(err)
                    line = f"✗ Webhook {i+1}: failed ({short_reason})"
                
                try:
                    root.after(
                        0,
                        lambda s=i+1, o=ok, f=fail: (
                            progress_bar.configure(value=s),
                            progress_var.set(f"{s}/{len(webhooks)} completed"),
                        ),
                    )
                    root.after(0, lambda l=line: _append_status(l))
                except Exception:
                    pass
            
            def finish_ui():
                try:
                    progress_win.destroy()
                except Exception:
                    pass
                
                if fail:
                    detail_lines = [format_webhook_failure_line(url, err) for url, err in failures[:3]]
                    suffix = "\n- ..." if len(failures) > 3 else ""
                    messagebox.showinfo(
                        "Export Submission",
                        f"Export submitted to {ok}/{ok + fail} webhook(s).\n\n"
                        f"Details:\n{chr(10).join(detail_lines)}{suffix}",
                    )
                else:
                    messagebox.showinfo(
                        "Export Submission",
                        f"Mission export successfully submitted to {ok} webhook(s)!",
                    )
            
            root.after(0, finish_ui)
        
        threading.Thread(target=worker, daemon=True).start()

    def load_export_webhooks():
        # Read export webhook URLs from JSON/DCord.json; used for Discord export
        try:
            dcord_path = app_path("JSON", "DCord.json")
            with open(dcord_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            urls = []
            if isinstance(data.get("discord_webhooks_export"), list):
                urls.extend(u for u in data["discord_webhooks_export"] if isinstance(u, str) and u.strip())
            if not urls and isinstance(data.get("discord_webhooks_export_labeled"), list):
                for item in data["discord_webhooks_export_labeled"]:
                    if isinstance(item, dict) and item.get("url"):
                        urls.append(item["url"])
            # Fallback: generic webhooks key if export-specific is missing
            if not urls and isinstance(data.get("discord_webhooks"), list):
                urls.extend(u for u in data["discord_webhooks"] if isinstance(u, str) and u.strip())

            extra_export = get_extra_webhook_urls("export")
            if extra_export:
                urls = list(dict.fromkeys(urls + extra_export))
            return urls
        except Exception as e:
            logging.error(f"Failed to read export webhooks: {e}")
            return []

    def load_discord_json():
        # Load DCord.json config; provides UID and webhook settings
        try:
            dcord_path = app_path("JSON", "DCord.json")
            with open(dcord_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def load_discord_uid():
        # Get Discord UID from DCord.json; used in embed footer
        data = load_discord_json()
        return str(data.get("discord_uid", ""))

    def post_discord(webhook_url: str, payload: dict, timeout: int = 10):
        success, _, err = post_webhook(
            webhook_url,
            json_payload=payload,
            timeout=timeout,
            retries=2,
        )
        return success, err

    def _guess_first_value(rows, columns, key):
        # Helper: find first non-empty value for a column in rows
        try:
            if key in columns and rows:
                idx = columns.index(key)
                for r in rows:
                    val = r[idx]
                    if val not in (None, ""):
                        return str(val)
        except Exception:
            pass
        return ""

    def _compose_header_embed(rows: list[tuple], columns: list[str]) -> dict:
        # Build leading summary embed (banner/stats) for Discord export
        # Build a header/summary embed similar in spirit to sub.py
        djson = load_discord_json()
        uid = str(djson.get("discord_uid", ""))
        # Try to pick representative values for banner and title
        planet = _guess_first_value(rows, columns, "Planet")
        enemy = _guess_first_value(rows, columns, "Enemy Type") or _guess_first_value(rows, columns, "Enemy")
        title_name = _guess_first_value(rows, columns, "Title")
        helldiver_name = _guess_first_value(rows, columns, "Helldivers") or _guess_first_value(
            rows, columns, "Helldiver"
        )
        ship_name = _guess_first_value(rows, columns, "Super Destroyer")

        banner_url = BIOME_BANNERS.get(planet, "") if planet else ""
        enemy_emoji = ENEMY_ICONS.get(enemy, "") if enemy else ""

        # Short description with a few quick stats if available
        total_rows = len(rows)
        kills_sum = 0
        deaths_sum = 0
        try:
            if "Kills" in columns:
                kidx = columns.index("Kills")
                kills_sum = sum(int(float(r[kidx])) for r in rows if str(r[kidx]).strip() != "")
            if "Deaths" in columns:
                didx = columns.index("Deaths")
                deaths_sum = sum(int(float(r[didx])) for r in rows if str(r[didx]).strip() != "")
        except Exception:
            pass
        kdr = f"{(kills_sum / deaths_sum):.2f}" if deaths_sum else "-"

        desc_lines = []
        if title_name or helldiver_name:
            desc_lines.append(f"**{title_name} {helldiver_name}**")
        if enemy:
            desc_lines.append(f"Front: {enemy_emoji} {enemy}")
        desc_lines.append(f"Deployments in export: {total_rows}")
        if kills_sum or deaths_sum:
            desc_lines.append(f"Kills: {kills_sum} | Deaths: {deaths_sum} | KDR: {kdr}")

        header = {
            "title": f"{ship_name}\nHelldiver: {helldiver_name}" if ship_name or helldiver_name else "Mission Export",
            "description": "\n".join(desc_lines) if desc_lines else None,
            "color": 7257043,
            "author": {"name": "SEAF Battle Record"},
            "footer": {"text": uid} if uid else None,
        }
        if banner_url:
            header["image"] = {"url": banner_url}
        # Clean out None fields
        if not header.get("description"):
            header.pop("description", None)
        if not header.get("footer"):
            header.pop("footer", None)
        return header

    def _format_entry_block(i: int, columns: list[str], vals: tuple) -> str:
        # Format a row's details into a readable block for embed descriptions
        # Decorate with icons when known columns are present
        parts = [f"Deployment {i}"]
        lookup = {c: v for c, v in zip(columns, vals)}
        # Topline: Planet with icon, Mission with icon, Difficulty icon
        planet = str(lookup.get("Planet", "") or "")
        mission = str(lookup.get("Mission Type", "") or lookup.get("Mission", "") or "")
        campaign = str(lookup.get("Mission Category", "") or "")
        diff = str(lookup.get("Difficulty", "") or "")
        enemy = str(lookup.get("Enemy Type", "") or lookup.get("Enemy", "") or "")
        time_str = str(lookup.get("Time", "") or "")

        planet_icon = PLANET_ICONS.get(planet, "") if planet else ""
        mission_icon = MISSION_ICONS.get(mission, "") if mission else ""
        campaign_icon = CAMPAIGN_ICONS.get(campaign, "") if campaign else ""
        diff_icon = DIFFICULTY_ICONS.get(diff, "") if diff else ""
        enemy_icon = ENEMY_ICONS.get(enemy, "") if enemy else ""

        topline = []
        if planet:
            topline.append(f"{planet} {planet_icon}")
        if mission:
            topline.append(f"{mission} {mission_icon}")
        if campaign:
            topline.append(f"{campaign} {campaign_icon}")
        if diff:
            topline.append(f"{diff} {diff_icon}")
        if enemy:
            topline.append(f"{enemy} {enemy_icon}")
        if time_str:
            topline.append(f"{time_str}")
        if topline:
            parts.append(" • ".join([p for p in topline if p]))

        # Common stats if present
        stat_keys = ["Kills", "Deaths", "Major Order", "DSS Active", "Mega Structure", "Sector"]
        stats = []
        for k in stat_keys:
            col_key = k
            if k == "Mega Structure" and k not in columns and "Mega City" in columns:
                col_key = "Mega City"
            if col_key in columns:
                v = lookup.get(col_key, "")
                if str(v) != "":
                    label = "Mega Structure" if k == "Mega Structure" else k
                    stats.append(f"{label}: {v}")
        if stats:
            parts.append("> " + " | ".join(stats))

        # Fallback: include a couple of extra interesting columns if available
        for extra in ["Helldivers", "Title", "Level", "Super Destroyer"]:
            if extra in columns and str(lookup.get(extra, "")):
                parts.append(f"> {extra}: {lookup.get(extra)}")

        return "\n".join(parts) + "\n\n"

    def format_embeds_for_rows(rows: list[tuple], columns: list[str]) -> list[dict]:
        # Convert rows into Discord embeds (header + chunked detail embeds)
        # Construct a leading header embed and then chunked detail embeds
        all_embeds = []
        header = _compose_header_embed(rows, columns)
        if header:
            all_embeds.append(header)

        desc_builder = ""
        for i, vals in enumerate(rows, start=1):
            block = _format_entry_block(i, columns, vals)
            if len(desc_builder) + len(block) > 3600 and desc_builder:
                all_embeds.append({"title": "Mission Log Details", "description": desc_builder, "color": 7257043})
                desc_builder = block
            else:
                desc_builder += block
        if desc_builder:
            all_embeds.append({"title": "Mission Log Details", "description": desc_builder, "color": 7257043})
        # Ensure we don't exceed 10 embeds per message; caller sends one embed per message
        return all_embeds

    # Load Revision button images
    revision_btn_img = load_button_image(app_path("media", "Exportsys", "ExtractToDiscordButton.png"))
    revision_btn_img_hover = load_button_image(app_path("media", "Exportsys", "ExtractToDiscordButtonHover.png"))

    revision_btn = tk.Label(
        button_frame,
        image=revision_btn_img,
        cursor="hand2",
        bd=0,
        highlightthickness=0,
        borderwidth=0,
        relief="flat",
        background=DEFAULT_THEME["."]["configure"]["background"],
    )
    revision_btn.image = revision_btn_img  # Prevent garbage collection
    revision_btn.pack(side=tk.LEFT, padx=5)

    def on_revision_enter(event):
        # Hover handler for Revision button; updates image and plays sound
        revision_btn.configure(image=revision_btn_img_hover)
        revision_btn.image = revision_btn_img_hover
        try:
            play_button_hover()
        except Exception:
            pass

    def on_revision_leave(event):
        # Mouse leave handler for Revision button; restores default image
        revision_btn.configure(image=revision_btn_img)
        revision_btn.image = revision_btn_img

    def on_revision_click(event):
        # Click handler for Revision button; formats and sends a single selected mission
        play_button_click()
        submit_mission_revision()

    revision_btn.bind("<Enter>", on_revision_enter)
    revision_btn.bind("<Leave>", on_revision_leave)
    revision_btn.bind("<Button-1>", on_revision_click)

    # Exit button as image button (styled like other image buttons)
    exit_btn_img = load_button_image(app_path("media", "Exportsys", "ExitButton.png"))
    exit_btn_img_hover = load_button_image(app_path("media", "Exportsys", "ExitButtonHover.png"))

    exit_btn = tk.Label(
        button_frame,
        image=exit_btn_img,
        cursor="hand2",
        bd=0,
        highlightthickness=0,
        borderwidth=0,
        relief="flat",
        background=DEFAULT_THEME["."]["configure"]["background"],
    )
    exit_btn.image = exit_btn_img  # Prevent garbage collection
    exit_btn.pack(side=tk.RIGHT, padx=5)

    def on_exit_enter(event):
        # Hover handler for Exit button; updates image and plays sound
        exit_btn.configure(image=exit_btn_img_hover)
        exit_btn.image = exit_btn_img_hover
        try:
            play_button_hover()
        except Exception:
            pass

    def on_exit_leave(event):
        # Mouse leave handler for Exit button; restores default image
        exit_btn.configure(image=exit_btn_img)
        exit_btn.image = exit_btn_img

    def on_exit_click(event):
        # Click handler for Exit button; closes the Export Viewer
        play_button_click()
        root.quit()

    exit_btn.bind("<Enter>", on_exit_enter)
    exit_btn.bind("<Leave>", on_exit_leave)
    exit_btn.bind("<Button-1>", on_exit_click)

    # Alternating row colors for Treeview
    def set_alternating_row_colors():
        # Apply alternating row tags to current Treeview items
        for i, item in enumerate(table.get_children()):
            if i % 2 == 0:
                table.item(item, tags=("even",))
            else:
                table.item(item, tags=("odd",))
        table.tag_configure("even", background="#232323", foreground="#FFFFFF")
        table.tag_configure("odd", background="#2d2d2d", foreground="#FFFFFF")

    # Filter section
    filter_lf = ttk.LabelFrame(
        export_frame, labelwidget=ttk.Label(export_frame, text="Filters", font=fs_sinclair_font), padding=10
    )
    filter_lf.pack(fill=tk.X, padx=10, pady=(0, 10))

    # Filter variables
    enemy_var = tk.StringVar(value="All")
    subfaction_var = tk.StringVar(value="All")
    sector_var = tk.StringVar(value="All")
    planet_var = tk.StringVar(value="All")

    # Dropdown values (copied from previous)

    # Load Excel data
    excel_file = EXCEL_FILE_TEST if DEBUG else EXCEL_FILE_PROD
    data_service = get_mission_data_service()

    # Sorting state and helpers for header click sorting
    # Additional dynamic filtering (exclusions) and sorting state will be defined near filter_table
    sort_column = None
    sort_reverse = False

    def update_heading_labels():
        # Update column header labels with sort arrows based on state
        # Show ▲ for ascending, ▼ for descending on the active sort column
        current_cols = list(table["columns"]) if table["columns"] else []
        for col in current_cols:
            label = col
            if sort_column == col:
                label = f"{col} {'▼' if sort_reverse else '▲'}"
            try:
                table.heading(col, text=label)
            except Exception:
                pass

    def on_heading_click(col_name):
        # Toggle sort order for a column and refresh table
        # Toggle sort: if clicking same column, reverse; else ascending by default
        nonlocal sort_column, sort_reverse
        if sort_column == col_name:
            sort_reverse = not sort_reverse
        else:
            sort_column = col_name
            sort_reverse = False
        # Defer to filter refresh (which applies sorting) and update headers
        filter_table()
        update_heading_labels()

    def load_table():
        # Read Excel into DataFrame and configure Treeview columns/headings
        try:
            df = data_service.read_mission_log(excel_file, use_cache=True)
            if "Mega Structure" not in df.columns and "Mega City" in df.columns:
                df = df.rename(columns={"Mega City": "Mega Structure"})
            columns = list(df.columns)
            table["columns"] = columns
            for col in columns:
                # Make headings clickable for sorting
                table.heading(col, text=col, command=lambda c=col: on_heading_click(c))
                table.column(col, width=120, anchor=tk.CENTER)
            update_heading_labels()
            return df
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load Excel file: {e}")
            return pd.DataFrame()

    full_df = load_table()
    last_filtered_df = full_df.copy() if isinstance(full_df, pd.DataFrame) else None

    # Filtering logic
    # Additional dynamic filtering (exclusions) and sorting state
    exclude_filters = {"Enemy": set(), "Subfaction": set(), "Sector": set(), "Planet": set()}

    def filter_table(*args):
        # Filter/sort DataFrame based on controls, then reload Treeview items
        nonlocal last_filtered_df
        df = full_df.copy()
        if enemy_var.get() != "All":
            df = df[df["Enemy"] == enemy_var.get()]
        if subfaction_var.get() != "All":
            df = df[df["Subfaction"] == subfaction_var.get()]
        if sector_var.get() != "All":
            df = df[df["Sector"] == sector_var.get()]
        if planet_var.get() != "All":
            df = df[df["Planet"] == planet_var.get()]
        # Apply exclude filters (values to be excluded per filterable column)
        for col, values in exclude_filters.items():
            if values and col in df.columns:
                try:
                    df = df[~df[col].isin(list(values))]
                except Exception:
                    # Fallback to string comparison if types mismatch
                    df = df[~df[col].astype(str).isin([str(v) for v in values])]

        # Apply sorting if set
        if sort_column in df.columns:
            try:
                df = df.sort_values(by=sort_column, ascending=not sort_reverse, kind="mergesort")
            except Exception:
                # Fallback to string sort
                df = (
                    df.assign(_sort=df[sort_column].astype(str))
                    .sort_values("_sort", ascending=not sort_reverse, kind="mergesort")
                    .drop(columns=["_sort"])
                )
        # Clear table

        for item in table.get_children():
            table.delete(item)
        for idx, (_, row) in enumerate(df.iterrows()):
            values = [str(val) if pd.notna(val) else "" for val in row]
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            table.insert("", tk.END, values=values, tags=(tag,))
        configure_row_tags()
        last_filtered_df = df

    # Utilities
    # Full-scan autosize with dynamic max width (per screen size)
    def compute_column_width(col_name):
        # Measure content to compute ideal pixel width for a column
        # Ensure UI is laid out for accurate font metrics
        root.update_idletasks()

        try:
            cell_font_spec = style.lookup("Treeview", "font") or tkfont.nametofont("TkDefaultFont")
            cell_font = (
                cell_font_spec
                if isinstance(cell_font_spec, tkfont.Font)
                else tkfont.Font(font=cell_font_spec)
                if cell_font_spec
                else tkfont.nametofont("TkDefaultFont")
            )
        except Exception:
            cell_font = tkfont.nametofont("TkDefaultFont")

        try:
            heading_font_spec = style.lookup("Treeview.Heading", "font") or cell_font
            heading_font = (
                heading_font_spec
                if isinstance(heading_font_spec, tkfont.Font)
                else tkfont.Font(font=heading_font_spec)
                if heading_font_spec
                else cell_font
            )
        except Exception:
            heading_font = cell_font

        padding = 24
        min_w = 60
        # Dynamic max width as a fraction of screen width
        screen_w = max(800, root.winfo_screenwidth())
        max_w = int(screen_w * 0.45)  # allow up to 45% of screen per column

        # Start with header width
        width_px = heading_font.measure(str(col_name)) + padding

        # Full scan of all row texts for this column
        for item in table.get_children():
            try:
                val = table.set(item, col_name)
                width_px = max(width_px, cell_font.measure(str(val)) + padding)
            except Exception:
                continue

        width_px = max(min_w, min(max_w, int(width_px)))
        return width_px

    def autosize_columns_full():
        # Autosize all columns based on full content scan
        for col in table["columns"]:
            table.column(col, width=compute_column_width(col))

    def autosize_column_full(col_name):
        # Autosize a single column to fit its content
        if col_name:
            table.column(col_name, width=compute_column_width(col_name))

    def reset_column_widths():
        # Reset all column widths to default fixed size
        for col in table["columns"]:
            table.column(col, width=120)

    # Bind filter changes
    enemy_var.trace_add("write", filter_table)
    subfaction_var.trace_add("write", filter_table)
    sector_var.trace_add("write", filter_table)
    planet_var.trace_add("write", filter_table)

    # Context menu for right-click actions on table (decorated)
    context_menu = tk.Menu(
        root, tearoff=0, bg="#2b2b2b", fg="#ffffff", activebackground="#4C4C4C", activeforeground="#ffffff", bd=1
    )

    # Map column names to their corresponding filter variables
    filter_var_by_column = {
        "Enemy": enemy_var,
        "Subfaction": subfaction_var,
        "Sector": sector_var,
        "Planet": planet_var,
    }

    def copy_to_clipboard(text: str):
        # Copy provided text to OS clipboard; safe-guarded against errors
        if text is None:
            return
        try:
            root.clipboard_clear()
            root.clipboard_append(str(text))
            root.update()  # now it stays on the clipboard after the window is closed
        except Exception as e:
            logging.warning(f"Clipboard copy failed: {e}")

    def copy_selection_as_markdown(row_ids, with_headers=True):
        # Copy first selected row as structured Markdown (sections/fields)
        cols = list(table["columns"])
        # Only use the first selected row for this format
        if not row_ids:
            return
        rid = row_ids[0]
        vals = list(table.item(rid, "values"))
        data = {c: v if v != "" else "N/A" for c, v in zip(cols, vals)}
        # Section 1: Helldiver Details
        helldiver_section = [
            "# Helldiver Details",
            "### Helldivers: ",
            data.get("Helldivers", "N/A"),
            "### Level: ",
            data.get("Level", "N/A"),
            "### Title: ",
            data.get("Title", "N/A"),
            "### Super Destroyer: ",
            data.get("Super Destroyer", "N/A"),
            "",
        ]
        # Section 2: Deployments Details
        deployment_section = [
            "# Deployments Details",
            "### Sector: ",
            data.get("Sector", "N/A"),
            "### Planet: ",
            data.get("Planet", "N/A"),
            "### Enemy Type: ",
            data.get("Enemy Type", data.get("Enemy", "N/A")),
            "### Enemy Subfaction: ",
            data.get("Subfaction", "N/A"),
            "### Mission Category: ",
            data.get("Mission Category", "N/A"),
            "### Mission Type: ",
            data.get("Mission Type", data.get("Mission", "N/A")),
            "### Mega Structure: ",
            data.get("Mega Structure", data.get("Mega City", "N/A")),
            "### Difficulty: ",
            data.get("Difficulty", "N/A"),
            "### Major Order: ",
            data.get("Major Order", "N/A"),
            "### DSS Active: ",
            data.get("DSS Active", "N/A"),
            "### DSS Modifier: ",
            data.get("DSS Modifier", "N/A"),
            "",
        ]
        # Section 3: Mission Report
        report_section = [
            "# Mission Report",
            "### Kills: ",
            data.get("Kills", "N/A"),
            "### Deaths: ",
            data.get("Deaths", "N/A"),
            "### Rating: ",
            data.get("Rating", "N/A"),
            "### Note: ",
            data.get("Note", "N/A"),
            "## Mission Timestamp ",
            data.get("Time", "N/A"),
            "",
        ]
        markdown = "\n".join(helldiver_section + deployment_section + report_section)
        copy_to_clipboard(markdown)

    def copy_row_as_json(row_id):
        # Copy a row's data as formatted JSON to clipboard
        cols = list(table["columns"])
        vals = list(table.item(row_id, "values"))
        obj = {c: v for c, v in zip(cols, vals)}
        try:
            s = json.dumps(obj, ensure_ascii=False, indent=2)
        except Exception:
            s = str(obj)
        copy_to_clipboard(s)

    def get_selected_or_row(default_row):
        # Return current selection or fallback to provided default row id
        sel = list(table.selection())
        if sel:
            return sel
        return [default_row] if default_row else []

    def show_row_details(row_id):
        # Popup dialog showing all column values for the row
        cols = list(table["columns"])
        vals = list(table.item(row_id, "values"))
        details = "\n".join(f"{c}: {v}" for c, v in zip(cols, vals))
        messagebox.showinfo("Row details", details)

    def set_sort(c, reverse):
        # Set sort parameters and refresh table contents
        nonlocal sort_column, sort_reverse
        sort_column, sort_reverse = c, reverse
        filter_table()
        update_heading_labels()

    def add_exclude_value(col, val):
        # Add a value to exclude filters for a column and refresh
        if col in exclude_filters and val not in (None, ""):
            exclude_filters[col].add(val)
            filter_table()

    def clear_exclude(col):
        # Clear all excluded values for a given column
        if col in exclude_filters:
            exclude_filters[col].clear()
            filter_table()

    def clear_all_excludes():
        # Clear all exclude filters across all columns
        for k in exclude_filters:
            exclude_filters[k].clear()
        filter_table()

    # Combine includes (comboboxes) and excludes into one clear action
    def clear_all_filters():
        # Clear include (combobox) and exclude filters, then refresh
        reset_filters()
        clear_all_excludes()
        filter_table()

    def double_click(event):
        # Open details dialog for double-clicked row
        row_id = table.identify_row(event.y)
        if row_id:
            show_row_details(row_id)

    def on_right_click(event):
        # Show context menu for copy/select/sort/filter/column sizing actions
        # Identify the row and column under the cursor
        row_id = table.identify_row(event.y)
        col_id = table.identify_column(event.x)  # like '#1', '#2', ...

        # Clear and rebuild the menu for this event
        context_menu.delete(0, tk.END)

        # If not on a valid row, don't show menu
        if not row_id:
            return

        # Select the row that was right-clicked
        try:
            table.selection_set(row_id)
        except Exception:
            pass

        # Resolve column name and cell value
        try:
            col_index = int(col_id.replace("#", "")) - 1
        except Exception:
            col_index = None

        col_name = None
        cell_value = None
        if col_index is not None and 0 <= col_index < len(table["columns"]):
            col_name = table["columns"][col_index]
            try:
                cell_value = table.set(row_id, col_name)
            except Exception:
                cell_value = None

        # Submenus for organization
        copy_menu = tk.Menu(
            context_menu,
            tearoff=0,
            bg="#2b2b2b",
            fg="#ffffff",
            activebackground="#4C4C4C",
            activeforeground="#ffffff",
            bd=1,
        )
        select_menu = tk.Menu(
            context_menu,
            tearoff=0,
            bg="#2b2b2b",
            fg="#ffffff",
            activebackground="#4C4C4C",
            activeforeground="#ffffff",
            bd=1,
        )
        sort_menu = tk.Menu(
            context_menu,
            tearoff=0,
            bg="#2b2b2b",
            fg="#ffffff",
            activebackground="#4C4C4C",
            activeforeground="#ffffff",
            bd=1,
        )
        filter_menu = tk.Menu(
            context_menu,
            tearoff=0,
            bg="#2b2b2b",
            fg="#ffffff",
            activebackground="#4C4C4C",
            activeforeground="#ffffff",
            bd=1,
        )
        size_menu = tk.Menu(
            context_menu,
            tearoff=0,
            bg="#2b2b2b",
            fg="#ffffff",
            activebackground="#4C4C4C",
            activeforeground="#ffffff",
            bd=1,
        )

        # Copy submenu
        if cell_value not in (None, ""):
            copy_menu.add_command(label="Copy value", command=lambda v=cell_value: copy_to_clipboard(v))
        # Selection rows for copy operations
        target_ids = get_selected_or_row(row_id)
        copy_menu.add_command(
            label="Copy selection (Markdown)",
            command=lambda ids=target_ids: copy_selection_as_markdown(ids, with_headers=True),
        )
        copy_menu.add_separator()
        copy_menu.add_command(label="Copy row as JSON", command=lambda rid=row_id: copy_row_as_json(rid))
        copy_menu.add_command(
            label="Copy column name",
            command=lambda n=col_name: copy_to_clipboard(n) if n else None,
            state=(tk.NORMAL if col_name else tk.DISABLED),
        )

        # Select submenu
        select_menu.add_command(label="Select all", command=lambda: table.selection_set(table.get_children()))
        select_menu.add_command(label="Clear selection", command=lambda: table.selection_remove(table.get_children()))

        # Sort submenu
        if col_name:
            # Indicate current sort with checkmarks
            asc_label = f"Sort by {col_name} ▲"
            desc_label = f"Sort by {col_name} ▼"
            sort_menu.add_command(label=asc_label, command=lambda c=col_name: set_sort(c, False))
            sort_menu.add_command(label=desc_label, command=lambda c=col_name: set_sort(c, True))
            # Visual hint: disabled item showing current state
            try:
                current = (
                    f"Current: {sort_column} " + ("▼" if sort_reverse else "▲") if sort_column else "Current: None"
                )
            except Exception:
                current = "Current: None"
            sort_menu.add_separator()
            sort_menu.add_command(label=current, state=tk.DISABLED)

        # Filter submenu
        if col_name in filter_var_by_column and cell_value not in (None, ""):
            filter_menu.add_command(
                label=f"Include: {col_name} = {cell_value}",
                command=lambda c=col_name, v=cell_value: filter_var_by_column[c].set(v),
            )
            filter_menu.add_command(
                label=f"Exclude: {col_name} = {cell_value}",
                command=lambda c=col_name, v=cell_value: add_exclude_value(c, v),
            )
            filter_menu.add_separator()
            filter_menu.add_command(
                label=f"Clear {col_name} include", command=lambda c=col_name: filter_var_by_column[c].set("All")
            )
            filter_menu.add_command(label=f"Clear {col_name} excludes", command=lambda c=col_name: clear_exclude(c))
            filter_menu.add_separator()
        filter_menu.add_command(label="Clear all includes", command=reset_filters)
        filter_menu.add_command(label="Clear all excludes", command=clear_all_excludes)
        filter_menu.add_command(label="Clear all filters", command=clear_all_filters)

        # Size submenu
        size_menu.add_command(
            label="Auto-size this column",
            command=lambda n=col_name: autosize_column_full(n),
            state=(tk.NORMAL if col_name else tk.DISABLED),
        )
        size_menu.add_command(label="Auto-size all columns", command=autosize_columns_full)
        size_menu.add_command(label="Reset column widths", command=reset_column_widths)

        # Row details
        context_menu.add_cascade(label="Copy", menu=copy_menu)
        context_menu.add_cascade(label="Select", menu=select_menu)
        context_menu.add_cascade(label="Sort", menu=sort_menu, state=(tk.NORMAL if col_name else tk.DISABLED))
        context_menu.add_cascade(label="Filter", menu=filter_menu)
        context_menu.add_cascade(label="Columns", menu=size_menu)
        context_menu.add_separator()
        context_menu.add_command(label="Show row details", command=lambda rid=row_id: show_row_details(rid))

        # Show the menu
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    # Bind right-click on the table
    table.bind("<Button-3>", on_right_click)
    table.bind("<Double-1>", double_click)

    # Populate initially using tagged rows for alternating colors
    filter_table()

    # Now that clear_all_filters exists, attach it to the top bar button
    try:
        reset_btn.configure(command=clear_all_filters)
    except Exception:
        pass

    root.mainloop()


if __name__ == "__main__":
    main()
