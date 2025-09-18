import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import re
import sys
import traceback

# ---------- Paths ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = os.path.join(BASE_DIR, "JSON")
SETTINGS_PATH = os.path.join(JSON_DIR, "settings.json")
DCORD_PATH = os.path.join(JSON_DIR, "DCord.json")

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
    def __init__(self):
        print("[settings] SettingsPage.__init__ start")
        super().__init__()
        self.title("Discord Settings")
        self.geometry("900x800")
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

        # Labeled webhook items: list of {label, url}
        self.webhooks_logging = []
        self.webhooks_export = []
        self.show_urls_var = tk.BooleanVar(value=False)

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
            for method, cfg in opts.items():
                getattr(style, method)(widget, **cfg)

    # ----- UI Build -----
    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Profile tab (Username + Ship Name)
        profile_frame = ttk.Frame(notebook, padding="10")
        notebook.add(profile_frame, text="Profile")
        # Identity section
        identity_label = ttk.Label(profile_frame, text="Identity", font=("Arial", 12, "bold"))
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
        preview_label = ttk.Label(profile_frame, text="Destroyer Preview", font=("Arial", 12, "bold"))
        preview_lf = ttk.LabelFrame(profile_frame, labelwidget=preview_label, padding=10)
        preview_lf.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=10, pady=5)
        ttk.Label(preview_lf, text="Full Name:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(preview_lf, textvariable=self.full_ship_name_var).grid(row=0, column=1, sticky=tk.W, padx=5)

        # Discord tab
        discord_frame = ttk.Frame(notebook, padding="10")
        notebook.add(discord_frame, text="Discord")
        # Account section
        account_label = ttk.Label(discord_frame, text="Account", font=("Arial", 12, "bold"))
        account_lf = ttk.LabelFrame(discord_frame, labelwidget=account_label, padding=10)
        account_lf.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=10, pady=10)
        account_lf.columnconfigure(1, weight=1)
        ttk.Label(account_lf, text="Discord User ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(account_lf, textvariable=self.discord_uid_var, width=30).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=10, pady=5)
        ttk.Label(account_lf, text="Platform:").grid(row=0, column=2, sticky=tk.W, padx=(20,5))
        self.platform_combo = ttk.Combobox(account_lf, textvariable=self.platform_var, values=["Not Selected", "Steam", "PlayStation", "Xbox"], state="readonly", width=20)
        self.platform_combo.grid(row=0, column=3, sticky=tk.W)

        # Webhooks section
        hooks_label = ttk.Label(discord_frame, text="Webhooks", font=("Arial", 12, "bold"))
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
        ttk.Entry(log_controls, textvariable=self.new_webhook_label_var_logging, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Label(log_controls, text="URL:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(log_controls, textvariable=self.new_webhook_var_logging, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_controls, text="Add", command=self.add_webhook_logging).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_controls, text="Remove Selected", command=self.remove_webhook_logging).pack(side=tk.LEFT, padx=5)

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
        ttk.Entry(exp_controls, textvariable=self.new_webhook_label_var_export, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Label(exp_controls, text="URL:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(exp_controls, textvariable=self.new_webhook_var_export, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(exp_controls, text="Add", command=self.add_webhook_export).pack(side=tk.LEFT, padx=5)
        ttk.Button(exp_controls, text="Remove Selected", command=self.remove_webhook_export).pack(side=tk.LEFT, padx=5)

        ttk.Checkbutton(hooks_lf, text="Show URLs (otherwise show labels)", variable=self.show_urls_var, command=self.refresh_webhook_listboxes).grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=5)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, expand=True, pady=10)
        ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_defaults).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Save Settings", command=self.save_settings).pack(side=tk.RIGHT, padx=5)

        # Populate webhook listboxes
        self.refresh_webhook_listboxes()

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
        dcord = {
            "discord_uid": self.discord_uid_var.get(),
            "discord_webhooks_logging": _extract(self.webhooks_logging),
            "discord_webhooks_export": _extract(self.webhooks_export),
            "discord_webhooks": _extract(self.webhooks_export),
            "discord_webhooks_logging_labeled": self.webhooks_logging,
            "discord_webhooks_export_labeled": self.webhooks_export,
            "platform": self.platform_var.get() or "Not Selected",
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
        for w in self.webhooks_logging:
            self.webhooks_listbox_logging.insert(tk.END, _display(w))
        self.webhooks_listbox_export.delete(0, tk.END)
        for w in self.webhooks_export:
            self.webhooks_listbox_export.insert(tk.END, _display(w))

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
        sys.exit(1)
