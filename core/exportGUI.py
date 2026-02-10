import os
import json
import threading
import logging
import configparser
import urllib.request
import urllib.error

import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont

import pandas as pd

from core.runtime_paths import app_path, resource_path
from core.logging_config import setup_logging
from core.icon import (
    ENEMY_ICONS, DIFFICULTY_ICONS, PLANET_ICONS,
    CAMPAIGN_ICONS, MISSION_ICONS, BIOME_BANNERS
)
from core.ui_sound import (
    init_ui_sounds, play_button_click, play_button_hover,
    register_global_click_binding
)

try:
    # After refactor these constants live in app_core
    from core.app_core import EXCEL_FILE_PROD, EXCEL_FILE_TEST
except Exception:
    # Backwards compatibility: fall back to main if app_core is not importable
    from core.main import EXCEL_FILE_PROD, EXCEL_FILE_TEST

# Read configuration
config = configparser.ConfigParser()
config.read(app_path('config.config'))

DEBUG = config.getboolean('DEBUGGING', 'DEBUG', fallback=False)
setup_logging(DEBUG)
SETTINGS_FILE = app_path('JSON', 'persistence.json')

# Theme system (copied from main.py/settings.py)
def make_theme(bg, fg, entry_bg=None, entry_fg=None, button_bg=None, button_fg=None, frame_bg=None):
    # Build ttk theme palette; affects export viewer styling
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
        icon_path = resource_path('LaunchMedia', 'SuperEarth.png')
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
        table.tag_configure('oddrow', background='#2d2d2d', foreground='#FFFFFF')
        table.tag_configure('evenrow', background='#232323', foreground='#FFFFFF')
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
        export_tab_img = load_tab_image(app_path('media', 'Exportsys', 'ExportViewerTabButton.png'))
        notebook.add(export_frame, text="", image=export_tab_img, compound=tk.CENTER, padding=0)
        notebook._export_tab_img = export_tab_img
    except Exception as e:
        notebook.add(export_frame, text="Export Viewer")

    # Remove tab border/highlight (like settings.py)
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

    def update_tab_image(event=None):
        # Keep tab image consistent on selection; cosmetic behavior
        # Only one tab, always selected
        notebook.tab(0, image=notebook._export_tab_img)

    notebook.bind("<<NotebookTabChanged>>", update_tab_image)
    notebook.tab(0, sticky="nsew")
    update_tab_image()

    # Table section
    table_lf = ttk.LabelFrame(export_frame, labelwidget=ttk.Label(export_frame, text="Mission Log Data", font=fs_sinclair_font), padding=10)
    table_lf.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)



    # Table (Treeview) with column headers and filtering
    # NOTE: Windows ttk themes may ignore tag-based row coloring for Treeview rows.
    # For true alternation, consider using ttkbootstrap or a custom widget.
    style.configure("Treeview", background="#232323", foreground="#FFFFFF", fieldbackground="#232323", rowheight=24, bordercolor="#232323", lightcolor="#232323", darkcolor="#232323")
    style.configure("Treeview.Heading", background="#252526", foreground="#FFFFFF", font=(fs_sinclair_font.actual("family"), 10, "bold"))
    style.map("Treeview", background=[("selected", "#4C4C4C")], foreground=[("selected", "#FFFFFF")])
    table = ttk.Treeview(table_lf, show="headings", selectmode="extended", style="Treeview")
    table.pack(fill=tk.BOTH, expand=True)



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

    clear_btn_img = load_button_image(app_path('media', 'Exportsys', 'ClearFiltersButton.png'))
    clear_btn_img_hover = load_button_image(app_path('media', 'Exportsys', 'ClearFiltersButtonHover.png'))

    reset_btn = tk.Label(
        button_frame,
        image=clear_btn_img,
        cursor="hand2",
        bd=0,
        highlightthickness=0,
        borderwidth=0,
        relief="flat",
        background=DEFAULT_THEME["."]["configure"]["background"]
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
    refresh_btn_img = load_button_image(app_path('media', 'Exportsys', 'RefreshButton.png'))
    refresh_btn_img_hover = load_button_image(app_path('media', 'Exportsys', 'RefreshButtonHover.png'))

    refresh_btn = tk.Label(
        button_frame,
        image=refresh_btn_img,
        cursor="hand2",
        bd=0,
        highlightthickness=0,
        borderwidth=0,
        relief="flat",
        background=DEFAULT_THEME["."]["configure"]["background"]
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

    # Export to Discord (selected or visible rows)
    def load_export_webhooks():
        # Read export webhook URLs from JSON/DCord.json; used for Discord export
        try:
            dcord_path = app_path('JSON', 'DCord.json')
            with open(dcord_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            urls = []
            if isinstance(data.get('discord_webhooks_export'), list):
                urls.extend(u for u in data['discord_webhooks_export'] if isinstance(u, str) and u.strip())
            if not urls and isinstance(data.get('discord_webhooks_export_labeled'), list):
                for item in data['discord_webhooks_export_labeled']:
                    if isinstance(item, dict) and item.get('url'):
                        urls.append(item['url'])
            # Fallback: generic webhooks key if export-specific is missing
            if not urls and isinstance(data.get('discord_webhooks'), list):
                urls.extend(u for u in data['discord_webhooks'] if isinstance(u, str) and u.strip())
            return urls
        except Exception as e:
            logging.error(f"Failed to read export webhooks: {e}")
            return []

    def load_discord_json():
        # Load DCord.json config; provides UID and webhook settings
        try:
            dcord_path = app_path('JSON', 'DCord.json')
            with open(dcord_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def load_discord_uid():
        # Get Discord UID from DCord.json; used in embed footer
        data = load_discord_json()
        return str(data.get('discord_uid', ''))

    def post_discord(webhook_url: str, payload: dict, timeout: int = 10):
        # POST JSON payload to Discord webhook; handles HTTP/Discord errors
        try:
            data = json.dumps(payload).encode('utf-8')
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'MLHD2-Exporter/1.0 (+https://example.com) Python-urllib'
            }
            req = urllib.request.Request(webhook_url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                # Discord often returns 204 No Content on success
                return resp.status if hasattr(resp, 'status') else 204
        except urllib.error.HTTPError as he:
            # Try to extract error body for diagnostics
            body = None
            try:
                body_bytes = he.read()
                if body_bytes:
                    body = body_bytes.decode('utf-8', errors='replace')
            except Exception:
                body = None
            # Try to parse Discord error JSON
            code = None
            message = None
            if body:
                try:
                    j = json.loads(body)
                    code = j.get('code')
                    message = j.get('message')
                except Exception:
                    pass
            if he.code == 404:
                logging.error("Discord webhook HTTP 404: Unknown Webhook (URL deleted or invalid).")
            elif he.code == 403:
                logging.error("Discord webhook HTTP 403: Forbidden (missing permissions or channel/thread restrictions).")
            else:
                logging.error(f"Discord webhook HTTP error: {he.code} {he.reason}")
            if message or code or body:
                logging.error(f"Discord response details: code={code} message={message} body={body[:300] if body else ''}")
            return None
        except Exception as e:
            logging.error(f"Discord webhook error: {e}")
            return None

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
        uid = str(djson.get('discord_uid', ''))
        # Try to pick representative values for banner and title
        planet = _guess_first_value(rows, columns, 'Planet')
        enemy = _guess_first_value(rows, columns, 'Enemy Type') or _guess_first_value(rows, columns, 'Enemy')
        title_name = _guess_first_value(rows, columns, 'Title')
        helldiver_name = _guess_first_value(rows, columns, 'Helldivers') or _guess_first_value(rows, columns, 'Helldiver')
        ship_name = _guess_first_value(rows, columns, 'Super Destroyer')

        banner_url = BIOME_BANNERS.get(planet, '') if planet else ''
        enemy_emoji = ENEMY_ICONS.get(enemy, '') if enemy else ''

        # Short description with a few quick stats if available
        total_rows = len(rows)
        kills_sum = 0
        deaths_sum = 0
        try:
            if 'Kills' in columns:
                kidx = columns.index('Kills')
                kills_sum = sum(int(float(r[kidx])) for r in rows if str(r[kidx]).strip() != '')
            if 'Deaths' in columns:
                didx = columns.index('Deaths')
                deaths_sum = sum(int(float(r[didx])) for r in rows if str(r[didx]).strip() != '')
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
        planet = str(lookup.get('Planet', '') or '')
        mission = str(lookup.get('Mission Type', '') or lookup.get('Mission', '') or '')
        campaign = str(lookup.get('Mission Category', '') or '')
        diff = str(lookup.get('Difficulty', '') or '')
        enemy = str(lookup.get('Enemy Type', '') or lookup.get('Enemy', '') or '')
        time_str = str(lookup.get('Time', '') or '')

        planet_icon = PLANET_ICONS.get(planet, '') if planet else ''
        mission_icon = MISSION_ICONS.get(mission, '') if mission else ''
        campaign_icon = CAMPAIGN_ICONS.get(campaign, '') if campaign else ''
        diff_icon = DIFFICULTY_ICONS.get(diff, '') if diff else ''
        enemy_icon = ENEMY_ICONS.get(enemy, '') if enemy else ''

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
        stat_keys = ['Kills', 'Deaths', 'Major Order', 'DSS Active', 'Mega Structure', 'Sector']
        stats = []
        for k in stat_keys:
            col_key = k
            if k == 'Mega Structure' and k not in columns and 'Mega City' in columns:
                col_key = 'Mega City'
            if col_key in columns:
                v = lookup.get(col_key, '')
                if str(v) != '':
                    label = 'Mega Structure' if k == 'Mega Structure' else k
                    stats.append(f"{label}: {v}")
        if stats:
            parts.append("> " + " | ".join(stats))

        # Fallback: include a couple of extra interesting columns if available
        for extra in ['Helldivers', 'Title', 'Level', 'Super Destroyer']:
            if extra in columns and str(lookup.get(extra, '')):
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
                all_embeds.append({
                    "title": "Mission Log Details",
                    "description": desc_builder,
                    "color": 7257043
                })
                desc_builder = block
            else:
                desc_builder += block
        if desc_builder:
            all_embeds.append({
                "title": "Mission Log Details",
                "description": desc_builder,
                "color": 7257043
            })
        # Ensure we don't exceed 10 embeds per message; caller sends one embed per message
        return all_embeds

    def export_to_discord():
        # Prepare selected/visible rows and send as embeds to Discord webhooks
        selected_ids = list(table.selection())
        use_rows = []
        columns = list(table["columns"]) if table["columns"] else []
        if selected_ids:
            for iid in selected_ids:
                use_rows.append(tuple(table.item(iid, 'values')))
        else:
            # If no selection, ask to export all visible rows
            if not messagebox.askyesno("Export to Discord", "No rows selected. Export all visible rows?"):
                return
            # Use last filtered dataframe values in table column order
            if columns and last_filtered_df is not None:
                try:
                    for _, r in last_filtered_df.iterrows():
                        use_rows.append(tuple(str(r.get(c, "")) if pd.notna(r.get(c, "")) else "" for c in columns))
                except Exception:
                    # Fallback to reading from Treeview if DF path fails
                    for iid in table.get_children():
                        use_rows.append(tuple(table.item(iid, 'values')))
            else:
                for iid in table.get_children():
                    use_rows.append(tuple(table.item(iid, 'values')))

        if not use_rows:
            messagebox.showinfo("Export to Discord", "Nothing to export.")
            return

        webhooks = load_export_webhooks()
        if not webhooks:
            messagebox.showerror("Export to Discord", "No export webhooks found in JSON/DCord.json")
            return

        embeds_list = format_embeds_for_rows(use_rows, columns)

        def worker():
            # Background worker: posts embeds to each webhook URL
            ok = 0
            fail = 0
            for w in webhooks:
                # Discord supports up to 10 embeds per message; we send one embed per message here for simplicity
                for emb in embeds_list:
                    status = post_discord(w, {"embeds": [emb]})
                    if status in (200, 201, 202, 204):
                        ok += 1
                    else:
                        fail += 1


        threading.Thread(target=worker, daemon=True).start()

    # Load Export to Discord button images
    extract_btn_img = load_button_image(app_path('media', 'Exportsys', 'ExtractToDiscordButton.png'))
    extract_btn_img_hover = load_button_image(app_path('media', 'Exportsys', 'ExtractToDiscordButtonHover.png'))

    export_btn = tk.Label(
        button_frame,
        image=extract_btn_img,
        cursor="hand2",
        bd=0,
        highlightthickness=0,
        borderwidth=0,
        relief="flat",
        background=DEFAULT_THEME["."]["configure"]["background"]
    )
    export_btn.image = extract_btn_img  # Prevent garbage collection
    export_btn.pack(side=tk.LEFT, padx=5)

    def on_export_enter(event):
        # Hover handler for Export button; updates image and plays sound
        export_btn.configure(image=extract_btn_img_hover)
        export_btn.image = extract_btn_img_hover
        try:
            play_button_hover()
        except Exception:
            pass

    def on_export_leave(event):
        # Mouse leave handler for Export button; restores default image
        export_btn.configure(image=extract_btn_img)
        export_btn.image = extract_btn_img

    def on_export_click(event):
        # Click handler for Export button; sends selected/visible rows to Discord
        play_button_click()
        export_to_discord()

    export_btn.bind("<Enter>", on_export_enter)
    export_btn.bind("<Leave>", on_export_leave)
    export_btn.bind("<Button-1>", on_export_click)

    # Exit button as image button (styled like other image buttons)
    exit_btn_img = load_button_image(app_path('media', 'Exportsys', 'ExitButton.png'))
    exit_btn_img_hover = load_button_image(app_path('media', 'Exportsys', 'ExitButtonHover.png'))

    exit_btn = tk.Label(
        button_frame,
        image=exit_btn_img,
        cursor="hand2",
        bd=0,
        highlightthickness=0,
        borderwidth=0,
        relief="flat",
        background=DEFAULT_THEME["."]["configure"]["background"]
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
    filter_lf = ttk.LabelFrame(export_frame, labelwidget=ttk.Label(export_frame, text="Filters", font=fs_sinclair_font), padding=10)
    filter_lf.pack(fill=tk.X, padx=10, pady=(0,10))

    # Filter variables
    enemy_var = tk.StringVar(value="All")
    subfaction_var = tk.StringVar(value="All")
    sector_var = tk.StringVar(value="All")
    planet_var = tk.StringVar(value="All")

    # Dropdown values (copied from previous)
    ENEMY_TYPES = ['All', 'Automatons', 'Illuminate', 'Terminids']
    SUBFACTIONS = [
        'All', 'Terminid Horde', 'Predator Strain', 'Spore Burst Strain', 
        'Automaton Legion', 'Jet Brigade', 'Incineration Corps', 
        'Jet Brigade & Incineration Corps', 'Illuminate Cult', 'The Great Host'
    ]
    SECTORS = [
        'All', 'Akira Sector', 'Alstrad Sector', 'Altus Sector', 'Andromeda Sector', 'Arturion Sector', 'Barnard Sector', 'Borgus Sector', 'Cancri Sector', 'Cantolus Sector', 'Celeste Sector', 'Draco Sector', 'Falstaff Sector', 'Farsight Sector', 'Ferris Sector', 'Gallux Sector',
        'Gellert Sector', 'Gothmar Sector', 'Guang Sector', 'Hanzo Sector', 'Hawking Sector', 'Hydra Sector', 'Idun Sector', 'Iptus Sector', 'Jin Xi Sector', 'Kelvin Sector', 'Korpus Sector', "L'estrade Sector", 'Lacaille Sector', 'Leo Sector', 'Marspira Sector', 'Meridian Sector',
        'Mirin Sector', 'Morgon Sector', 'Nanos Sector', 'Omega Sector', 'Orion Sector', 'Quintus Sector', 'Rictus Sector', 'Rigel Sector', 'Sagan Sector', 'Saleria Sector', 'Severin Sector', 'Sol System', 'Sten Sector', 'Talus Sector', 'Tanis Sector', 'Tarragon Sector', 'Theseus Sector',
        'Trigon Sector', 'Umlaut Sector', 'Ursa Sector', 'Valdis Sector', 'Xi Tauri Sector', 'Xzar Sector', 'Ymir Sector'
    ]
    PLANETS = [
        'All','Alaraph', 'Alathfar XI', 'Andar', 'Asperoth Prime', 'Keid', 'Kneth Port', 'Klaka 5', 'Kraz', 'Pathfinder V', 'Klen Dahth II', "Widow's Harbor", 'New Haven', 'Pilen V', 'Charbal-VII', 'Charon Prime', 'Martale', 'Marfark', 'Matar Bay', 'Mortax Prime', 'Kirrik', 'Wilford Station', 'Arkturus',
        'Pioneer II', 'Electra Bay', 'Deneb Secundus', 'Fornskogur II', 'Veil', 'Marre IV', 'Midasburg', 'Darrowsport', 'Hydrofall Prime', 'Ursica XI', 'Achird III', 'Achernar Secundus', 'Darius II', 'Prosperity Falls', 'Cerberus IIIc', 'Effluvia', 'Seyshel Beach', 'Fort Sanctuary', 'Kelvinor', "Martyr's Bay",
        'Freedom Peak', 'Viridia Prime', 'Obari', 'Sulfura', 'Nublaria I', 'Krakatwo', 'Ivis', 'Slif', 'Moradesh', 'Meridia', 'Crimsica', 'Estanu', 'Fori Prime', 'Bore Rock', 'Esker', 'Socorro III', 'Erson Sands', 'Prasa', 'Pollux 31', 'Polaris Prime', 'Pherkad Secundus', 'Grand Errant', 'Hadar', 'Haldus', 'Zea Rugosia',
        'Herthon Secundus', 'Kharst', 'Bashyr', 'Rasp', 'Acubens Prime', 'Adhara', 'Afoyay Bay', 'Minchir', 'Mintoria', 'Blistica', 'Zzaniah Prime', 'Zosma', 'Okul VI', 'Solghast', 'Diluvia', 'Elysian Meadows', 'Alderidge Cove', 'Bellatrix', 'Botein', 'Khandark', 'Heze Bay', 'Alairt III', 'Alamak VII', 'New Stockholm', 'Ain-5',
        'Mordia 9', 'Euphoria III', 'Skitter', 'Kuma', 'Aesir Pass', 'Vernen Wells', 'Menkent', 'Wraith', 'Atrama', 'Myradesh', 'Maw', 'Providence', 'Primordia', 'Krakabos', 'Iridica', 'Valgaard', 'Ratch', 'Acamar IV', 'Pandion-XXIV', 'Gacrux', 'Phact Bay', 'Gar Haren', 'Gatria', 'Zegema Paradise', 'Fort Justice', 'New Kiruna',
        'Igla', 'Emeria', 'Crucible', 'Volterra', 'Caramoor', 'Alta V', 'Inari', 'Navi VII', 'Omicron', 'Nabatea Secundus', 'Gemstone Bluffs', 'Epsilon Phoencis VI', 'Enuliale', 'Disapora X', 'Lesath', 'Penta', 'Chort Bay', 'Choohe', 'Ras Algethi', 'Propus', 'Halies Port', 'Haka', 'Curia', 'Barabos', 'Fenmire', 'Tarsh', 'Mastia',
        'Emorath', 'Ilduna Prime', 'Baldrick Prime', 'Liberty Ridge', 'Hellmire', 'Nivel 43', 'Zagon Prime', 'Oshaune', 'Myrium', 'Eukoria', 'Regnus', 'Mog', 'Dolph', 'Julheim', 'Bekvam III', 'Duma Tyr', 'Setia', 'Senge 23', 'Seasse', 'Hydrobius', 'Karlia', 'Terrek', 'Azterra', 'Fort Union', 'Cirrus', 'Heeth', "Angel's Venture",
        'Veld', 'Termadon', 'Stor Tha Prime', 'Spherion', 'Stout', 'Leng Secundus', 'Valmox', 'Iro', 'Grafmere', 'Kerth Secundus', 'Parsh', 'Oasis', 'Genesis Prime', 'Rogue 5', 'RD-4', 'Hesoe Prime', 'Hort', 'Rirga Bay', 'Oslo Station', 'Gunvald', 'Borea', 'Calypso', 'Outpost 32', 'Reaf', 'Irulta', 'Maia', 'Malevelon Creek', 'Durgen',
        'Ubanea', 'Tibit', 'Super Earth', 'Mars', 'Trandor', 'Peacock', 'Partion', 'Overgoe Prime', 'Azur Secundus', 'Shallus', 'Shelt', 'Gaellivare', 'Imber', 'Claorell', 'Vog-Sojoth', 'Clasa', 'Yed Prior', 'Zefia', 'Demiurg', 'East Iridium Trading Bay', 'Brink-2', 'Osupsam', 'Canopus', 'Bunda Secundus', 'The Weir', 'Kuper', 'Caph', 'Castor',
        'Tien Kwan', 'Lastofe', 'Varylia 5', 'Choepessa IV', 'Ustotu', 'Troost', 'Vandalon IV', 'Erata Prime', 'Fenrir III', 'Turing', 'Skaash', 'Acrab XI', 'Acrux IX', 'Gemma', 'Merga IV', 'Merak', 'Cyberstan', 'Aurora Bay', 'Mekbuda', 'Videmitarix Prime', 'Skat Bay', 'Sirius', 'Siemnot', 'Shete', 'Mort', 'P\u00F6pli IX', 'Ingmar', 'Mantes',
        'Draupnir', 'Meissa', 'Wasat', 'X-45', 'Vega Bay', 'Wezen', 'Fury', 'K', 'Mox', 'Cursa', 'Oroth', 'Karon Bay'
    ]

    # Load Excel data
    excel_file = EXCEL_FILE_TEST if DEBUG else EXCEL_FILE_PROD

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
            df = pd.read_excel(excel_file)
            if 'Mega Structure' not in df.columns and 'Mega City' in df.columns:
                df = df.rename(columns={'Mega City': 'Mega Structure'})
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
    exclude_filters = {'Enemy': set(), 'Subfaction': set(), 'Sector': set(), 'Planet': set()}

    def filter_table(*args):
        # Filter/sort DataFrame based on controls, then reload Treeview items
        nonlocal last_filtered_df
        df = full_df.copy()
        if enemy_var.get() != "All":
            df = df[df['Enemy'] == enemy_var.get()]
        if subfaction_var.get() != "All":
            df = df[df['Subfaction'] == subfaction_var.get()]
        if sector_var.get() != "All":
            df = df[df['Sector'] == sector_var.get()]
        if planet_var.get() != "All":
            df = df[df['Planet'] == planet_var.get()]
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
                df = df.sort_values(by=sort_column, ascending=not sort_reverse, kind='mergesort')
            except Exception:
                # Fallback to string sort
                df = df.assign(_sort=df[sort_column].astype(str)).sort_values('_sort', ascending=not sort_reverse, kind='mergesort').drop(columns=['_sort'])
        # Clear table

        for item in table.get_children():
            table.delete(item)
        for idx, (_, row) in enumerate(df.iterrows()):
            values = [str(val) if pd.notna(val) else "" for val in row]
            tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            table.insert('', tk.END, values=values, tags=(tag,))
        configure_row_tags()
        last_filtered_df = df

    # Utilities
    # Full-scan autosize with dynamic max width (per screen size)
    def compute_column_width(col_name):
        # Measure content to compute ideal pixel width for a column
        # Ensure UI is laid out for accurate font metrics
        root.update_idletasks()

        try:
            cell_font_spec = style.lookup('Treeview', 'font') or tkfont.nametofont('TkDefaultFont')
            cell_font = cell_font_spec if isinstance(cell_font_spec, tkfont.Font) else tkfont.Font(font=cell_font_spec) if cell_font_spec else tkfont.nametofont('TkDefaultFont')
        except Exception:
            cell_font = tkfont.nametofont('TkDefaultFont')

        try:
            heading_font_spec = style.lookup('Treeview.Heading', 'font') or cell_font
            heading_font = heading_font_spec if isinstance(heading_font_spec, tkfont.Font) else tkfont.Font(font=heading_font_spec) if heading_font_spec else cell_font
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
    context_menu = tk.Menu(root, tearoff=0, bg="#2b2b2b", fg="#ffffff", activebackground="#4C4C4C", activeforeground="#ffffff", bd=1)

    # Map column names to their corresponding filter variables
    filter_var_by_column = {
        'Enemy': enemy_var,
        'Subfaction': subfaction_var,
        'Sector': sector_var,
        'Planet': planet_var,
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
        vals = list(table.item(rid, 'values'))
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
            ""
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
            ""
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
            ""
        ]
        markdown = "\n".join(helldiver_section + deployment_section + report_section)
        copy_to_clipboard(markdown)

    def copy_row_as_json(row_id):
        # Copy a row's data as formatted JSON to clipboard
        cols = list(table["columns"])
        vals = list(table.item(row_id, 'values'))
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
        vals = list(table.item(row_id, 'values'))
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
            col_index = int(col_id.replace('#', '')) - 1
        except Exception:
            col_index = None

        col_name = None
        cell_value = None
        if col_index is not None and 0 <= col_index < len(table['columns']):
            col_name = table['columns'][col_index]
            try:
                cell_value = table.set(row_id, col_name)
            except Exception:
                cell_value = None

        # Submenus for organization
        copy_menu = tk.Menu(context_menu, tearoff=0, bg="#2b2b2b", fg="#ffffff", activebackground="#4C4C4C", activeforeground="#ffffff", bd=1)
        select_menu = tk.Menu(context_menu, tearoff=0, bg="#2b2b2b", fg="#ffffff", activebackground="#4C4C4C", activeforeground="#ffffff", bd=1)
        sort_menu = tk.Menu(context_menu, tearoff=0, bg="#2b2b2b", fg="#ffffff", activebackground="#4C4C4C", activeforeground="#ffffff", bd=1)
        filter_menu = tk.Menu(context_menu, tearoff=0, bg="#2b2b2b", fg="#ffffff", activebackground="#4C4C4C", activeforeground="#ffffff", bd=1)
        size_menu = tk.Menu(context_menu, tearoff=0, bg="#2b2b2b", fg="#ffffff", activebackground="#4C4C4C", activeforeground="#ffffff", bd=1)

        # Copy submenu
        if cell_value not in (None, ""):
            copy_menu.add_command(
                label=f"Copy value",
                command=lambda v=cell_value: copy_to_clipboard(v)
            )
        # Selection rows for copy operations
        target_ids = get_selected_or_row(row_id)
        copy_menu.add_command(label="Copy selection (Markdown)", command=lambda ids=target_ids: copy_selection_as_markdown(ids, with_headers=True))
        copy_menu.add_separator()
        copy_menu.add_command(label="Copy row as JSON", command=lambda rid=row_id: copy_row_as_json(rid))
        copy_menu.add_command(label="Copy column name", command=lambda n=col_name: copy_to_clipboard(n) if n else None, state=(tk.NORMAL if col_name else tk.DISABLED))

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
                current = f"Current: {sort_column} " + ("▼" if sort_reverse else "▲") if sort_column else "Current: None"
            except Exception:
                current = "Current: None"
            sort_menu.add_separator()
            sort_menu.add_command(label=current, state=tk.DISABLED)

        # Filter submenu
        if col_name in filter_var_by_column and cell_value not in (None, ""):
            filter_menu.add_command(
                label=f"Include: {col_name} = {cell_value}",
                command=lambda c=col_name, v=cell_value: filter_var_by_column[c].set(v)
            )
            filter_menu.add_command(
                label=f"Exclude: {col_name} = {cell_value}",
                command=lambda c=col_name, v=cell_value: add_exclude_value(c, v)
            )
            filter_menu.add_separator()
            filter_menu.add_command(label=f"Clear {col_name} include", command=lambda c=col_name: filter_var_by_column[c].set("All"))
            filter_menu.add_command(label=f"Clear {col_name} excludes", command=lambda c=col_name: clear_exclude(c))
            filter_menu.add_separator()
        filter_menu.add_command(label="Clear all includes", command=reset_filters)
        filter_menu.add_command(label="Clear all excludes", command=clear_all_excludes)
        filter_menu.add_command(label="Clear all filters", command=clear_all_filters)

        # Size submenu
        size_menu.add_command(label="Auto-size this column", command=lambda n=col_name: autosize_column_full(n), state=(tk.NORMAL if col_name else tk.DISABLED))
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