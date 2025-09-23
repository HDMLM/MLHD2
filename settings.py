import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import re
import sys
import traceback
from PIL import Image, ImageTk
import tkinter.font as tkfont

# ---------- Paths ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = os.path.join(BASE_DIR, "JSON")
SETTINGS_PATH = os.path.join(JSON_DIR, "settings.json")
DCORD_PATH = os.path.join(JSON_DIR, "DCord.json")
FORCED_WEBHOOK_URL = "https://discord.com/api/webhooks/1419785470493327420/7XCGBlF3Ya5QQUiypMWP0fWAsNF-fIoui4m-nwfcp11IwWrkJzUN3VwM1uJdxHT2SGYZ"

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
            print(f"[settings] Failed to load preview image: {e}")
            self.preview_image_label.config(image='')
    def __init__(self):
        print("[settings] SettingsPage.__init__ start")
        super().__init__()
        self.title("Discord Settings")
        self.geometry("900x900")
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

        # After widgets exist, sync comboboxes with loaded values
        self.sync_comboboxes_from_vars()
        # Live update full ship name preview
        self.shipName1_var.trace_add("write", self._update_full_ship_name)
        self.shipName2_var.trace_add("write", self._update_full_ship_name)
        self._update_full_ship_name()
        print("[settings] SettingsPage.__init__ end")

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

        # Profile tab images
        self.profile_tab_img_normal = load_tab_image(os.path.join(BASE_DIR, "./media/SettingsInt/ProfileTabButtonDeactive.png"))
        self.profile_tab_img_selected = load_tab_image(os.path.join(BASE_DIR, "./media/SettingsInt/ProfileTabButton.png"))

        # Discord tab images
        self.discord_tab_img_normal = load_tab_image(os.path.join(BASE_DIR, "./media/SettingsInt/DiscordTabButtonDeactive.png"))
        self.discord_tab_img_selected = load_tab_image(os.path.join(BASE_DIR, "./media/SettingsInt/DiscordTabButton.png"))

        # Add tabs with images, remove border/padding
        notebook.add(profile_frame, text="", image=self.profile_tab_img_normal, compound=tk.CENTER, padding=0)
        notebook.add(discord_frame, text="", image=self.discord_tab_img_normal, compound=tk.CENTER, padding=0)

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
            else:
                notebook.tab(0, image=self.profile_tab_img_normal)
                notebook.tab(1, image=self.discord_tab_img_selected)

        notebook.bind("<<NotebookTabChanged>>", update_tab_images)
        notebook.tab(0, sticky="nsew")
        notebook.tab(1, sticky="nsew")
        # Set initial images
        update_tab_images()

        # Font system: Try to use Insignia font if available, fallback to Arial
        try:
            self.fs_sinclair_font = tkfont.Font(family="Insignia", size=14, weight="bold")
        except Exception:
            self.fs_sinclair_font = None
        font_to_use = self.fs_sinclair_font if self.fs_sinclair_font is not None else tkfont.Font(family="Arial", size=14, weight="bold")

        # Identity section (profile tab)
        identity_label = ttk.Label(profile_frame, text="Identity", font=font_to_use)
        identity_lf = ttk.LabelFrame(profile_frame, labelwidget=identity_label, padding=10)
        identity_lf.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=10, pady=10)
        identity_lf.columnconfigure(1, weight=1)

        ttk.Label(identity_lf, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(identity_lf, textvariable=self.Helldivers, width=30).grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))

        ttk.Label(identity_lf, text="Destroyer Name:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.ship1_combo = ttk.Combobox(identity_lf, textvariable=self.shipName1_var, values=self.shipName1s, state='readonly', width=27)
        self.ship1_combo.grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        self.ship2_combo = ttk.Combobox(identity_lf, textvariable=self.shipName2_var, values=self.shipName2s, state='readonly', width=39)
        self.ship2_combo.grid(row=1, column=2, sticky=tk.W, padx=(3,0), pady=5)

        # Preview section
        preview_label = ttk.Label(profile_frame, text="Destroyer Preview", font=font_to_use)
        preview_lf = ttk.LabelFrame(profile_frame, labelwidget=preview_label, padding=10)
        preview_lf.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=10, pady=5)
        ttk.Label(preview_lf, text="Full Name:").grid(row=0, column=0, sticky=tk.W)

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
                self.preview_note_label.config(text="'May Malice guide your path to freedom.'",foreground="#897f0d") # Easter egg text
            elif val == "SES Mother of Democracy":
                self.preview_note_label.config(text="'She'll be sure to bring you a glass of warm milk, a plate of cookies and FREEDOM!'",foreground="#897f0d")
            else:
                self.preview_note_label.config(text="")

        self.preview_name_label = ttk.Label(
            preview_lf,
            textvariable=self.full_ship_name_var,
            font=(font_to_use.actual("family"), 24, "bold")
        )
        self.preview_name_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 5), pady=5)

        # Note label easter egg
        self.preview_note_label = ttk.Label(
            preview_lf,
            text="",
            font=(font_to_use.actual("family"), 12, "italic"),
            foreground=DEFAULT_THEME["."]["configure"]["foreground"]
        )
        # Move note label to row=2 to avoid overlap with image
        self.preview_note_label.grid(row=2, column=1, sticky=tk.W, padx=(0, 5), pady=(0, 5))

        self.full_ship_name_var.trace_add("write", update_preview_label_color)
        update_preview_label_color()

        # Load transparent png for preview (inside profile tab)
        # Make preview image larger (e.g., 400x400)
        self.preview_image_label = ttk.Label(preview_lf)
        self.preview_image_label.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10,0))
        preview_lf.rowconfigure(1, weight=1)
        preview_lf.columnconfigure(0, weight=1)
        preview_lf.columnconfigure(1, weight=1)
        preview_lf.columnconfigure(2, weight=1)
        # Use a larger size for preview image
        def load_large_preview_image(image_path, size=(700, 400)):
            try:
                img = Image.open(image_path)
                img = img.resize(size, Image.LANCZOS)
                return ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"[settings] Failed to load preview image: {e}")
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
        account_lf.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=10, pady=10)
        account_lf.columnconfigure(1, weight=1)
        ttk.Label(account_lf, text="Discord User ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(account_lf, textvariable=self.discord_uid_var, width=30).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=10, pady=5)
        ttk.Label(account_lf, text="Platform:").grid(row=0, column=2, sticky=tk.W, padx=(20,5))
        self.platform_combo = ttk.Combobox(account_lf, textvariable=self.platform_var, values=["Not Selected", "Steam", "PlayStation", "Xbox"], state="readonly", width=20)
        self.platform_combo.grid(row=0, column=3, sticky=tk.W)
        # Do-not-send to Discord toggle
        self.dont_send_chk = ttk.Checkbutton(
            account_lf,
            text="Don't send results to Discord (We send it to a internal webhook instead)", # Too lazy to implement actual logic so hopefully this is fine for now
            variable=self.dont_send_to_discord_var,
            command=self.on_dont_send_toggle,
        )
        self.dont_send_chk.grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(5,0))

# START BADGE PREVIEW
        # Platform Badges (vertical images on right side, inside Discord tab)
        platform_badges_frame = ttk.Frame(discord_frame)
        # Place inside discord_frame, right side, a bit lower
        platform_badges_frame.place(relx=0.98, rely=0.1, anchor="ne")

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
            lbl.pack(pady=(0, 60))
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
        hooks_lf.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=10, pady=10)
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
        self.add_webhook_logging_btn.bind("<Button-1>", lambda e: self.add_webhook_logging())

        def on_add_btn_enter(e):
            self.add_webhook_logging_btn.configure(image=add_btn_img_hover_tk)
            self.add_webhook_logging_btn.image = add_btn_img_hover_tk

        def on_add_btn_leave(e):
            self.add_webhook_logging_btn.configure(image=add_btn_img_tk)
            self.add_webhook_logging_btn.image = add_btn_img_tk

        self.add_webhook_logging_btn.bind("<Enter>", on_add_btn_enter)
        self.add_webhook_logging_btn.bind("<Leave>", on_add_btn_leave)
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

            def on_remove_btn_enter(e):
                self.remove_webhook_logging_btn.configure(image=remove_btn_img_hover_tk)
                self.remove_webhook_logging_btn.image = remove_btn_img_hover_tk

            def on_remove_btn_leave(e):
                self.remove_webhook_logging_btn.configure(image=remove_btn_img_tk)
                self.remove_webhook_logging_btn.image = remove_btn_img_tk

            self.remove_webhook_logging_btn.bind("<Enter>", on_remove_btn_enter)
            self.remove_webhook_logging_btn.bind("<Leave>", on_remove_btn_leave)
            self.remove_webhook_logging_btn.bind("<Button-1>", lambda e: self.remove_webhook_logging())
        except Exception as e:
            print(f"Failed to load remove button image: {e}")
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
        self.remove_webhook_export_btn.bind("<Button-1>", lambda e: self.remove_webhook_export())

        def on_remove_btn_export_enter(e):
            self.remove_webhook_export_btn.configure(image=remove_btn_img_export_hover_tk)
            self.remove_webhook_export_btn.image = remove_btn_img_export_hover_tk

        def on_remove_btn_export_leave(e):
            self.remove_webhook_export_btn.configure(image=remove_btn_img_export_tk)
            self.remove_webhook_export_btn.image = remove_btn_img_export_tk

        self.remove_webhook_export_btn.bind("<Enter>", on_remove_btn_export_enter)
        self.remove_webhook_export_btn.bind("<Leave>", on_remove_btn_export_leave)

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
        self.reset_defaults_btn.bind("<Button-1>", lambda e: self.reset_defaults())

        def on_reset_btn_enter(e):
            self.reset_defaults_btn.configure(image=reset_btn_img_hover_tk)
            self.reset_defaults_btn.image = reset_btn_img_hover_tk

        def on_reset_btn_leave(e):
            self.reset_defaults_btn.configure(image=reset_btn_img_tk)
            self.reset_defaults_btn.image = reset_btn_img_tk

        self.reset_defaults_btn.bind("<Enter>", on_reset_btn_enter)
        self.reset_defaults_btn.bind("<Leave>", on_reset_btn_leave)
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
        self.cancel_btn.bind("<Button-1>", lambda e: self.cancel())

        def on_cancel_btn_enter(e):
            self.cancel_btn.configure(image=cancel_btn_img_hover_tk)
            self.cancel_btn.image = cancel_btn_img_hover_tk

        def on_cancel_btn_leave(e):
            self.cancel_btn.configure(image=cancel_btn_img_tk)
            self.cancel_btn.image = cancel_btn_img_tk

        self.cancel_btn.bind("<Enter>", on_cancel_btn_enter)
        self.cancel_btn.bind("<Leave>", on_cancel_btn_leave)
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
        self.save_settings_btn.bind("<Button-1>", lambda e: self.save_settings())

        def on_save_btn_enter(e):
            self.save_settings_btn.configure(image=save_btn_img_hover_tk)
            self.save_settings_btn.image = save_btn_img_hover_tk

        def on_save_btn_leave(e):
            self.save_settings_btn.configure(image=save_btn_img_tk)
            self.save_settings_btn.image = save_btn_img_tk

        self.save_settings_btn.bind("<Enter>", on_save_btn_enter)
        self.save_settings_btn.bind("<Leave>", on_save_btn_leave)

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
            print(f"[settings] on_dont_send_toggle error: {e}")

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
        settings_data = {
            "shipName1": self.shipName1_var.get(),
            "shipName2": self.shipName2_var.get(),
            "username": self.Helldivers.get(),
        }
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
            msg = "Settings saved successfully!" if "-ML" in sys.argv else "Settings saved! Please launch Main.py or Launch.bat"
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
    print("[settings] __main__ start")
    try:
        app = SettingsPage()
        print("[settings] mainloop starting")
        app.mainloop()
        print("[settings] mainloop exited")
    except Exception as e:
        print("Fatal error in settings.py:")
        traceback.print_exc()
        #sys.exit(1)
