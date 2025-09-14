import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

# Shared theme system (mirrors main.py)
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
    for widget, opts in theme_dict.items():
        for method, cfg in opts.items():
            getattr(style, method)(widget, **cfg)

class SettingsPage(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Discord Settings")
        self.geometry("700x600")
        self.resizable(False, False)
        # Apply shared theme (same as main.py)
        style = ttk.Style()
        apply_theme(style, DEFAULT_THEME)
        self.configure(bg=DEFAULT_THEME["."]["configure"]["background"])
        # Only keep Discord-related settings
        self.settings = {
            "discord_uid": "",
            "discord_webhooks_logging": [],
            "discord_webhooks_export": [],
            "theme": "dark"
        }
        # Initialize variables before they're accessed in load_settings
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
        # Discord Settings Tab
        discord_frame = ttk.Frame(notebook, padding="10")
        notebook.add(discord_frame, text="Discord")
        # Discord UID
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
        ttk.Label(logging_buttons_frame, text="New Logging Webhook:").pack(side=tk.LEFT, padx=5)
        self.new_webhook_var_logging = tk.StringVar()
        logging_webhook_entry = ttk.Entry(logging_buttons_frame, textvariable=self.new_webhook_var_logging, width=40)
        logging_webhook_entry.pack(side=tk.LEFT, padx=5)
        add_logging_webhook_btn = ttk.Button(logging_buttons_frame, text="Add", command=self.add_webhook_logging)
        add_logging_webhook_btn.pack(side=tk.LEFT, padx=5)
        remove_logging_webhook_btn = ttk.Button(logging_buttons_frame, text="Remove Selected", command=self.remove_webhook_logging)
        remove_logging_webhook_btn.pack(side=tk.LEFT, padx=5)

        # Export Webhooks
        ttk.Label(discord_frame, text="Export Webhooks (This is where outputs such as faction data will go):").grid(row=4, column=0, sticky=tk.W, pady=5, padx=5)
        export_webhooks_frame = ttk.Frame(discord_frame)
        export_webhooks_frame.grid(row=5, column=0, columnspan=2, sticky=tk.W+tk.E, pady=5)
        self.webhooks_listbox_export = tk.Listbox(export_webhooks_frame, width=60, height=5)
        self.webhooks_listbox_export.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        export_buttons_frame = ttk.Frame(discord_frame)
        export_buttons_frame.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=5)
        ttk.Label(export_buttons_frame, text="New Export Webhook:").pack(side=tk.LEFT, padx=5)
        self.new_webhook_var_export = tk.StringVar()
        export_webhook_entry = ttk.Entry(export_buttons_frame, textvariable=self.new_webhook_var_export, width=40)
        export_webhook_entry.pack(side=tk.LEFT, padx=5)
        add_export_webhook_btn = ttk.Button(export_buttons_frame, text="Add", command=self.add_webhook_export)
        add_export_webhook_btn.pack(side=tk.LEFT, padx=5)
        remove_export_webhook_btn = ttk.Button(export_buttons_frame, text="Remove Selected", command=self.remove_webhook_export)
        remove_export_webhook_btn.pack(side=tk.LEFT, padx=5)
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, expand=True, pady=10)
        # Use grid for better control
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=0)
        button_frame.columnconfigure(2, weight=0)
        reset_btn = ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_defaults)
        reset_btn.grid(row=9, column=0, sticky="w", padx=5)
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=self.cancel)
        cancel_btn.grid(row=9, column=1, sticky="e", padx=5)
        save_btn = ttk.Button(button_frame, text="Save Settings", command=self.save_settings)
        save_btn.grid(row=9, column=2, sticky="e", padx=5)

        # Platform Selection
        platform_frame = ttk.Frame(discord_frame)
        platform_frame.grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=10)
        ttk.Label(platform_frame, text="Platform:").pack(side=tk.LEFT, padx=5)
        # Load platform from DCord.json if it exists, otherwise default to Steam
        default_platform = "Not Selected"
        try:
            if os.path.exists("./JSON/DCord.json"):
                with open("./JSON/DCord.json", "r") as f:
                    loaded_settings = json.load(f)
                    default_platform = loaded_settings.get("platform", "Not Selected")
        except Exception:
            pass
        self.platform_var = tk.StringVar(value=default_platform)
        platform_dropdown = ttk.Combobox(platform_frame, textvariable=self.platform_var, values=["Not Selected", "Steam", "PlayStation", "Xbox"], state="readonly")
        platform_dropdown.pack(side=tk.LEFT, padx=5)

    def save_settings(self):
        # Save theme, UID, and webhooks to DCord.json only
        settings_data = {
            "discord_uid": self.discord_uid_var.get(),
            "discord_webhooks_logging": self.webhooks_logging,
            "discord_webhooks_export": self.webhooks_export,
            "platform": self.platform_var.get()
        }
        try:
            with open("./JSON/DCord.json", "w") as f:
                json.dump(settings_data, f, indent=4)
            messagebox.showinfo("Success", "Settings saved successfully!")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Could not save settings: {str(e)}")

    def load_settings(self):
        # Load theme, UID, and webhooks from DCord.json only
        try:
            if os.path.exists("./JSON/DCord.json"):
                with open("./JSON/DCord.json", "r") as f:
                    loaded_settings = json.load(f)
                    self.settings["discord_uid"] = loaded_settings.get("discord_uid", "")
                    self.settings["discord_webhooks_logging"] = loaded_settings.get("discord_webhooks_logging", [])
                    self.settings["discord_webhooks_export"] = loaded_settings.get("discord_webhooks_export", [])
                    self.settings["platform"] = loaded_settings.get("platform", "")
        except Exception as e:
            messagebox.showerror("Error", f"Could not load settings: {str(e)}")
        self.discord_uid_var.set(self.settings["discord_uid"])
        self.webhooks_logging = self.settings["discord_webhooks_logging"]
        self.webhooks_export = self.settings["discord_webhooks_export"]
        self.webhooks_listbox_logging.delete(0, tk.END)
        for webhook in self.webhooks_logging:
            self.webhooks_listbox_logging.insert(tk.END, webhook)
        self.webhooks_listbox_export.delete(0, tk.END)
        for webhook in self.webhooks_export:
            self.webhooks_listbox_export.insert(tk.END, webhook)

    def reset_defaults(self):
        if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset Discord settings to default values?"):
            self.settings = {
                "discord_uid": "",
                "discord_webhooks_logging": [],
                "discord_webhooks_export": []
            }
            self.discord_uid_var.set("")
            self.webhooks_logging = []
            self.webhooks_export = []
            self.webhooks_listbox_logging.delete(0, tk.END)
            self.webhooks_listbox_export.delete(0, tk.END)

    def cancel(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to exit? Any unsaved changes will be lost."):
            self.destroy()

    def add_webhook_logging(self):
        webhook = self.new_webhook_var_logging.get().strip()
        if webhook:
            if webhook not in self.webhooks_logging:
                self.webhooks_logging.append(webhook)
                self.webhooks_listbox_logging.insert(tk.END, webhook)
                self.new_webhook_var_logging.set("")
            else:
                messagebox.showwarning("Duplicate", "This webhook already exists in the list.")
        else:
            messagebox.showwarning("Empty Input", "Please enter a webhook URL.")

    def remove_webhook_logging(self):
        selected = self.webhooks_listbox_logging.curselection()
        if selected:
            index = selected[0]
            self.webhooks_listbox_logging.delete(index)
            del self.webhooks_logging[index]
        else:
            messagebox.showwarning("No Selection", "Please select a webhook to remove.")

    def add_webhook_export(self):
        webhook = self.new_webhook_var_export.get().strip()
        if webhook:
            if webhook not in self.webhooks_export:
                self.webhooks_export.append(webhook)
                self.webhooks_listbox_export.insert(tk.END, webhook)
                self.new_webhook_var_export.set("")
            else:
                messagebox.showwarning("Duplicate", "This webhook already exists in the list.")
        else:
            messagebox.showwarning("Empty Input", "Please enter a webhook URL.")

    def remove_webhook_export(self):
        selected = self.webhooks_listbox_export.curselection()
        if selected:
            index = selected[0]
            self.webhooks_listbox_export.delete(index)
            del self.webhooks_export[index]
        else:
            messagebox.showwarning("No Selection", "Please select a webhook to remove.")

if __name__ == "__main__":
    app = SettingsPage()
    app.mainloop()
