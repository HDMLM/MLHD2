import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import re
import sys

def make_theme(bg, fg, entry_bg=None, entry_fg=None, button_bg=None, button_fg=None, frame_bg=None):
    """Return a theme dictionary for ttk widgets."""
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
        "TNotebook.Tab": {"configure": {"background": button_bg or bg, "foreground": entry_fg}},
    }

DEFAULT_THEME = make_theme(
    bg="#252526",
    fg="#FFFFFF",
    entry_bg="#252526",
    entry_fg="#000000",
    button_bg="#4C4C4C",
    button_fg="#000000",
    frame_bg="#252526"
)

def apply_theme(style: ttk.Style, theme_dict):
    """Apply theme dictionary to ttk.Style."""
    for widget, opts in theme_dict.items():
        for method, cfg in opts.items():
            getattr(style, method)(widget, **cfg)

class SettingsPage(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Discord Settings")
        self.geometry("900x600")
        self.resizable(False, False)
        style = ttk.Style()
        apply_theme(style, DEFAULT_THEME)
        self.configure(bg=DEFAULT_THEME["."]["configure"]["background"])

        # Settings state
        self.settings = {
            "discord_uid": "",
            "discord_webhooks_logging": [],
            "discord_webhooks_export": [],
            "theme": "dark",
            "shipName1": "SES Adjudicator",
            "shipName2": "of Allegiance"
        }

        # Username field
        self.Helldivers = tk.StringVar(value="Helldiver")
        self.shipName1s = [
            "SES Adjudicator", "SES Advocate", "SES Aegis", "SES Agent", "SES Arbiter", "SES Banner", "SES Beacon", "SES Blade", "SES Bringer", "SES Champion", "SES Citizen", "SES Claw", "SES Colossus", "SES Comptroller", "SES Courier", "SES Custodian", "SES Dawn", "SES Defender", "SES Diamond", "SES Distributor", "SES Dream", "SES Elected Representative", "SES Emperor", "SES Executor", "SES Eye", "SES Father", "SES Fist", "SES Flame", "SES Force", "SES Forerunner", "SES Founding Father", "SES Gauntlet", "SES Giant", "SES Guardian", "SES Halo", "SES Hammer", "SES Harbinger", "SES Herald", "SES Judge", "SES Keeper", "SES King", "SES Knight", "SES Lady", "SES Legislator", "SES Leviathan", "SES Light", "SES Lord", "SES Magistrate", "SES Marshall", "SES Martyr", "SES Mirror", "SES Mother", "SES Octagon", "SES Ombudsman", "SES Panther", "SES Paragon", "SES Patriot", "SES Pledge", "SES Power", "SES Precursor", "SES Pride", "SES Prince", "SES Princess", "SES Progenitor", "SES Prophet", "SES Protector", "SES Purveyor", "SES Queen", "SES Ranger", "SES Reign", "SES Representative", "SES Senator", "SES Sentinel", "SES Shield", "SES Soldier", "SES Song", "SES Soul", "SES Sovereign", "SES Spear", "SES Stallion", "SES Star", "SES Steward", "SES Superintendent", "SES Sword", "SES Titan", "SES Triumph", "SES Warrior", "SES Whisper", "SES Will", "SES Wings"
        ]
        self.shipName2s = [
            "of Allegiance", "of Audacity", "of Authority", "of Battle", "of Benevolence", "of Conquest", "of Conviction", "of Conviviality", "of Courage", "of Dawn", "of Democracy", "of Destiny", "of Destruction", "of Determination", "of Equality", "of Eternity", "of Family Values", "of Fortitude", "of Freedom", "of Glory", "of Gold", "of Honour", "of Humankind", "of Independence", "of Individual Merit", "of Integrity", "of Iron", "of Judgement", "of Justice", "of Law", "of Liberty", "of Mercy", "of Midnight", "of Morality", "of Morning", "of Opportunity", "of Patriotism", "of Peace", "of Perseverance", "of Pride", "of Redemption", "of Science", "of Self-Determination", "of Selfless Service", "of Serenity", "of Starlight", "of Steel", "of Super Earth", "of Supremacy", "of the Constitution", "of the People", "of the Regime", "of the Stars", "of the State", "of Truth", "of Twilight", "of Victory", "of Vigilance", "of War", "of Wrath"
        ]
        self.shipName1_var = tk.StringVar(value=self.settings["shipName1"])
        self.shipName2_var = tk.StringVar(value=self.settings["shipName2"])
        self.discord_uid_var = tk.StringVar(value="")
        self.webhooks_logging = []
        self.webhooks_export = []

        self.create_widgets()
        self.load_settings()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Ship Name Tab ---
        ship_frame = ttk.Frame(notebook, padding="10")
        notebook.add(ship_frame, text="Ship Name")
        ttk.Label(ship_frame, text="Destroyer Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ship1_combo = ttk.Combobox(ship_frame, textvariable=self.shipName1_var, values=self.shipName1s, state='readonly', width=27)
        ship1_combo.grid(row=0, column=1, padx=5, pady=5)
        ship1_combo.set(self.shipName1s[0])
        ship2_combo = ttk.Combobox(ship_frame, textvariable=self.shipName2_var, values=self.shipName2s, state='readonly', width=39)
        ship2_combo.grid(row=0, column=2, sticky=tk.W, padx=(3,0), pady=5)
        ship2_combo.set(self.shipName2s[0])
        def update_full_ship_name(*_):
            self.settings["shipName1"] = self.shipName1_var.get()
            self.settings["shipName2"] = self.shipName2_var.get()
        self.shipName1_var.trace_add("write", update_full_ship_name)
        self.shipName2_var.trace_add("write", update_full_ship_name)
        update_full_ship_name()

        # --- Username Tab ---
        mission_frame = ttk.Frame(notebook, padding="10")
        notebook.add(mission_frame, text="Username")
        ttk.Label(mission_frame, text="Username:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(mission_frame, textvariable=self.Helldivers, width=30).grid(row=2, column=1, padx=5, pady=5)

        # --- Discord Tab ---
        discord_frame = ttk.Frame(notebook, padding="10")
        notebook.add(discord_frame, text="Discord")
        ttk.Label(discord_frame, text="Discord User ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.discord_uid_var = tk.StringVar(value=self.settings.get("discord_uid", ""))
        discord_uid_entry = ttk.Entry(discord_frame, textvariable=self.discord_uid_var, width=30)
        discord_uid_entry.grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)

        # Logging Webhooks
        ttk.Label(discord_frame, text="Logging Webhooks (These are for the standard logging embeds that output per mission):").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        logging_webhooks_frame = ttk.Frame(discord_frame)
        logging_webhooks_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W+tk.E, pady=5)
        self.webhooks_listbox_logging = tk.Listbox(logging_webhooks_frame, width=60, height=5)
        self.webhooks_listbox_logging.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        logging_buttons_frame = ttk.Frame(discord_frame)
        logging_buttons_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        self.new_webhook_label_var_logging = tk.StringVar()
        ttk.Label(logging_buttons_frame, text="Label:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(logging_buttons_frame, textvariable=self.new_webhook_label_var_logging, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Label(logging_buttons_frame, text="New Logging Webhook:").pack(side=tk.LEFT, padx=5)
        self.new_webhook_var_logging = tk.StringVar()
        ttk.Entry(logging_buttons_frame, textvariable=self.new_webhook_var_logging, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(logging_buttons_frame, text="Add", command=self.add_webhook_logging).pack(side=tk.LEFT, padx=5)
        ttk.Button(logging_buttons_frame, text="Remove Selected", command=self.remove_webhook_logging).pack(side=tk.LEFT, padx=5)

        # Export Webhooks
        ttk.Label(discord_frame, text="Export Webhooks (This is where outputs such as faction data will go):").grid(row=4, column=0, sticky=tk.W, pady=5, padx=5)
        export_webhooks_frame = ttk.Frame(discord_frame)
        export_webhooks_frame.grid(row=5, column=0, columnspan=2, sticky=tk.W+tk.E, pady=5)
        self.webhooks_listbox_export = tk.Listbox(export_webhooks_frame, width=60, height=5)
        self.webhooks_listbox_export.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        export_buttons_frame = ttk.Frame(discord_frame)
        export_buttons_frame.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=5)
        self.new_webhook_label_var_export = tk.StringVar()
        ttk.Label(export_buttons_frame, text="Label:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(export_buttons_frame, textvariable=self.new_webhook_label_var_export, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Label(export_buttons_frame, text="New Export Webhook:").pack(side=tk.LEFT, padx=5)
        self.new_webhook_var_export = tk.StringVar()
        ttk.Entry(export_buttons_frame, textvariable=self.new_webhook_var_export, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_buttons_frame, text="Add", command=self.add_webhook_export).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_buttons_frame, text="Remove Selected", command=self.remove_webhook_export).pack(side=tk.LEFT, padx=5)

        # Show URLs toggle
        show_urls_frame = ttk.Frame(discord_frame)
        show_urls_frame.grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=5)
        self.show_urls_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(show_urls_frame, text="Show URLs (otherwise show labels)", variable=self.show_urls_var, command=self.refresh_webhook_listboxes).pack(side=tk.LEFT, padx=5)

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, expand=True, pady=10)
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=0)
        button_frame.columnconfigure(2, weight=0)
        ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_defaults).grid(row=9, column=0, sticky="w", padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).grid(row=9, column=1, sticky="e", padx=5)
        ttk.Button(button_frame, text="Save Settings", command=self.save_settings).grid(row=9, column=2, sticky="e", padx=5)

        # Platform Selection
        platform_frame = ttk.Frame(discord_frame)
        platform_frame.grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=10)
        ttk.Label(platform_frame, text="Platform:").pack(side=tk.LEFT, padx=5)
        default_platform = "Not Selected"
        try:
            if os.path.exists("./JSON/DCord.json"):
                with open("./JSON/DCord.json", "r") as f:
                    loaded_settings = json.load(f)
                    default_platform = loaded_settings.get("platform", "Not Selected")
        except Exception:
            pass
        self.platform_var = tk.StringVar(value=default_platform)
        ttk.Combobox(platform_frame, textvariable=self.platform_var, values=["Not Selected", "Steam", "PlayStation", "Xbox"], state="readonly").pack(side=tk.LEFT, padx=5)

    def save_settings(self):
        """Save settings to JSON files."""
        url_pattern = re.compile(r"^(http://|https://).+")

        def _validate_urls(items):
            seen_urls = set()
            for w in items:
                url = (w.get("url", "") if isinstance(w, dict) else str(w)).strip()
                if url:
                    if not url_pattern.match(url):
                        label = w.get("label", "") if isinstance(w, dict) else ""
                        messagebox.showerror("Error", f"Invalid webhook URL: {url}\nLabel: {label}")
                        return False
                    if url in seen_urls:
                        label = w.get("label", "") if isinstance(w, dict) else ""
                        messagebox.showerror("Error", f"Duplicate webhook URL detected: {url}\nLabel: {label}")
                        return False
                    seen_urls.add(url)
            return True

        if not _validate_urls(self.webhooks_logging) or not _validate_urls(self.webhooks_export):
            return

        def _extract_urls(items):
            return [
                (w.get("url", "") if isinstance(w, dict) else str(w)).strip()
                for w in items
                if (w.get("url", "") if isinstance(w, dict) else str(w)).strip().lower().startswith(("http://", "https://"))
            ]

        def _extract_labeled(items):
            result = []
            for w in items:
                if isinstance(w, dict):
                    url = str(w.get("url", "")).strip()
                    label = str(w.get("label", "")).strip()
                else:
                    url = str(w).strip()
                    label = ""
                if url.lower().startswith(("http://", "https://")):
                    result.append({"label": label, "url": url})
            return result

        settings_data = {
            "shipName1": self.shipName1_var.get(),
            "shipName2": self.shipName2_var.get(),
            "username": self.Helldivers.get()
        }
        discord_settings = {
            "discord_uid": self.discord_uid_var.get(),
            "discord_webhooks_logging": _extract_urls(self.webhooks_logging),
            "discord_webhooks_export": _extract_urls(self.webhooks_export),
            "discord_webhooks": _extract_urls(self.webhooks_export),
            "discord_webhooks_logging_labeled": _extract_labeled(self.webhooks_logging),
            "discord_webhooks_export_labeled": _extract_labeled(self.webhooks_export),
            "platform": self.platform_var.get()
        }
        try:
            with open("./JSON/settings.json", "w") as f:
                json.dump(settings_data, f, indent=4)
            with open("./JSON/DCord.json", "w") as f:
                json.dump(discord_settings, f, indent=4)
            msg = "Settings saved successfully!" if "-ML" in sys.argv else "Settings saved! Please launch Main.py or Launch.bat"
            messagebox.showinfo("Success", msg)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Could not save settings: {str(e)}")
    def load_settings(self):
        """Load settings from JSON files."""
        try:
            if os.path.exists("./JSON/settings.json"):
                with open("./JSON/settings.json", "r") as f:
                    loaded_settings = json.load(f)
                    self.settings["shipName1"] = loaded_settings.get("shipName1", self.settings["shipName1"])
                    self.settings["shipName2"] = loaded_settings.get("shipName2", self.settings["shipName2"])
                    self.Helldivers.set(loaded_settings.get("username", self.Helldivers.get()))
            if os.path.exists("./JSON/DCord.json"):
                with open("./JSON/DCord.json", "r") as f:
                    loaded_settings = json.load(f)
                    self.settings["discord_uid"] = loaded_settings.get("discord_uid", "")
                    self.settings["discord_webhooks_logging"] = loaded_settings.get("discord_webhooks_logging", [])
                    export_list = loaded_settings.get("discord_webhooks_export")
                    if export_list is None:
                        export_list = loaded_settings.get("discord_webhooks", [])
                    self.settings["discord_webhooks_export"] = export_list
                    self.settings["platform"] = loaded_settings.get("platform", "")
                    labeled_logging = loaded_settings.get("discord_webhooks_logging_labeled")
                    labeled_export = loaded_settings.get("discord_webhooks_export_labeled")
        except Exception as e:
            messagebox.showerror("Error", f"Could not load settings: {str(e)}")

        self.discord_uid_var.set(self.settings["discord_uid"])
        self.shipName1_var.set(self.settings["shipName1"])
        self.shipName2_var.set(self.settings["shipName2"])

        def _make_webhook_list(labeled, fallback):
            if labeled and isinstance(labeled, list):
                return [
                    {"label": str(w.get("label", "")).strip(), "url": str(w.get("url", "")).strip()}
                    for w in labeled if isinstance(w, dict)
                ]
            return [w if isinstance(w, dict) else {"label": "", "url": w} for w in fallback]

        self.webhooks_logging = _make_webhook_list(locals().get('labeled_logging'), self.settings["discord_webhooks_logging"])
        self.webhooks_export = _make_webhook_list(locals().get('labeled_export'), self.settings["discord_webhooks_export"])
        self.refresh_webhook_listboxes()

    def reset_defaults(self):
        if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset Discord settings to default values?"):
            self.settings["discord_uid"] = ""
            self.settings["discord_webhooks_logging"] = []
            self.settings["discord_webhooks_export"] = []
            self.discord_uid_var.set("")
            self.webhooks_logging.clear()
            self.webhooks_export.clear()
            self.webhooks_listbox_logging.delete(0, tk.END)
            self.webhooks_listbox_export.delete(0, tk.END)

    def cancel(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to exit? Any unsaved changes will be lost."):
            self.destroy()

    def add_webhook_logging(self):
        url = self.new_webhook_var_logging.get().strip()
        label = self.new_webhook_label_var_logging.get().strip()
        if not url:
            messagebox.showwarning("Empty Input", "Please enter a webhook URL.")
            return
        if any((w.get("url") if isinstance(w, dict) else w) == url for w in self.webhooks_logging):
            messagebox.showwarning("Duplicate", "This webhook already exists in the list.")
            return
        self.webhooks_logging.append({"label": label, "url": url})
        self.refresh_webhook_listboxes()
        self.new_webhook_var_logging.set("")
        self.new_webhook_label_var_logging.set("")

    def remove_webhook_logging(self):
        selected = self.webhooks_listbox_logging.curselection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a webhook to remove.")
            return
        del self.webhooks_logging[selected[0]]
        self.refresh_webhook_listboxes()

    def add_webhook_export(self):
        url = self.new_webhook_var_export.get().strip()
        label = self.new_webhook_label_var_export.get().strip()
        if not url:
            messagebox.showwarning("Empty Input", "Please enter a webhook URL.")
            return
        if any((w.get("url") if isinstance(w, dict) else w) == url for w in self.webhooks_export):
            messagebox.showwarning("Duplicate", "This webhook already exists in the list.")
            return
        self.webhooks_export.append({"label": label, "url": url})
        self.refresh_webhook_listboxes()
        self.new_webhook_var_export.set("")
        self.new_webhook_label_var_export.set("")

    def remove_webhook_export(self):
        selected = self.webhooks_listbox_export.curselection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a webhook to remove.")
            return
        del self.webhooks_export[selected[0]]
        self.refresh_webhook_listboxes()

    def _format_webhook_display(self, webhook: dict) -> str:
        """Return label or URL for webhook display."""
        label = webhook.get("label", "")
        url = webhook.get("url", "")
        return url if self.show_urls_var.get() or not label else label

    def refresh_webhook_listboxes(self):
        """Refresh webhook listboxes."""
        self.webhooks_listbox_logging.delete(0, tk.END)
        for webhook in self.webhooks_logging:
            self.webhooks_listbox_logging.insert(tk.END, self._format_webhook_display(webhook))
        self.webhooks_listbox_export.delete(0, tk.END)
        for webhook in self.webhooks_export:
            self.webhooks_listbox_export.insert(tk.END, self._format_webhook_display(webhook))

if __name__ == "__main__":
    app = SettingsPage()
    app.mainloop()
