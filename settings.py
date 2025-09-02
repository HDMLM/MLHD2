import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

class SettingsPage(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Discord Settings")
        self.geometry("700x500")
        self.resizable(False, False)
        # Theme definitions (copied from main.py, unified for button/tab appearance)
        self.light_theme = {
            ".": { "configure": { "background": "#FFFFFF", "foreground": "#000000" } },
            "TFrame": { "configure": { "background": "#FFFFFF" } },
            "TLabelframe": { "configure": { "background": "#FFFFFF", "foreground": "#000000" } },
            "TLabelframe.Label": { "configure": { "background": "#FFFFFF", "foreground": "#000000" } },
            "TNotebook": { "configure": { "background": "#FFFFFF" } },
            "TNotebook.Tab": { "configure": { "background": "#FFFFFF", "foreground": "#000000" } },
            "TButton": { "configure": { "background": "#e0e0e0", "foreground": "#000000" } },
            "TLabel": { "configure": { "background": "#ffffff", "foreground": "#000000" } },
            "TEntry": { "configure": { "background": "#ffffff", "foreground": "#000000", "fieldbackground": "#ffffff", "insertcolor": "#000000", "bordercolor": "#c0c0c0", "lightcolor": "#ffffff", "darkcolor": "#c0c0c0" } },
            "TCheckbutton": { "configure": { "background": "#ffffff", "foreground": "#000000", "indicatorbackground": "#ffffff", "indicatorforeground": "#000000" } },
            "TCombobox": { "configure": { "background": "#ffffff", "foreground": "#000000", "fieldbackground": "#ffffff", "insertcolor": "#000000", "bordercolor": "#c0c0c0", "lightcolor": "#ffffff", "darkcolor": "#c0c0c0", "arrowcolor": "#000000" } }
        }
        self.dark_theme = {
            ".": { "configure": { "background": "#252526", "foreground": "white" } },
            "TFrame": { "configure": { "background": "#252526" } },
            "TLabelframe": { "configure": { "background": "#252526", "foreground": "white" } },
            "TLabelframe.Label": { "configure": { "background": "#252526", "foreground": "white" } },
            "TNotebook": { "configure": { "background": "#444444" } },
            "TNotebook.Tab": { "configure": { "background": "#444444", "foreground": "black" } },
            "TButton": { "configure": { "background": "#444444", "foreground": "white" } },
            "TLabel": { "configure": { "background": "#252526", "foreground": "white" } },
            "TEntry": { "configure": { "background": "#252526", "foreground": "white", "fieldbackground": "#3c3c3c", "insertcolor": "#a3a3a3", "bordercolor": "black", "lightcolor": "#4d4d4d", "darkcolor": "black" } },
            "TCheckbutton": { "configure": { "background": "#252526", "foreground": "white", "indicatorbackground": "white", "indicatorforeground": "black" } },
            "TCombobox": { "configure": { "background": "#444444", "foreground": "black", "fieldbackground": "#444444", "insertcolor": "white", "bordercolor": "black", "lightcolor": "#4d4d4d", "darkcolor": "black", "arrowcolor": "gray" } }
        }
        self.THEMES = {"light": self.light_theme, "dark": self.dark_theme}
        # Only keep Discord-related settings
        self.settings = {
            "discord_uid": "",
            "discord_webhooks": [],
            "theme": "light"
        }
        # Initialize variables before they're accessed in load_settings
        self.discord_uid_var = tk.StringVar(value="")
        self.webhooks = []
        self.apply_theme(self.settings.get("theme", "light"))
        self.create_widgets()
        self.load_settings()

    def get_current_theme(self):
        if os.path.exists('settings.json'):
            try:
                with open('settings.json', 'r') as f:
                    settings = json.load(f)
                    return settings.get('theme', 'light')
            except Exception:
                return 'light'
        return 'light'

    def apply_theme(self, theme_name=None):
        if theme_name is None:
            theme_name = self.get_current_theme()
        style = ttk.Style()
        style.theme_use('clam')  # Force clam theme for consistent styling
        theme = self.THEMES.get(theme_name, self.light_theme)
        for widget, opts in theme.items():
            if "configure" in opts:
                style.configure(widget, **opts["configure"])
            if "map" in opts:
                style.map(widget, **opts["map"])
        # Explicitly set TButton style to ensure it takes effect
        style.configure('TButton', background=theme['TButton']['configure']['background'], foreground=theme['TButton']['configure']['foreground'])
        self.configure(bg=theme["."]["configure"]["background"])

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
        # Discord Webhooks
        ttk.Label(discord_frame, text="Discord Webhooks:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        webhooks_frame = ttk.Frame(discord_frame)
        webhooks_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W+tk.E, pady=5)
        self.webhooks_listbox = tk.Listbox(webhooks_frame, width=60, height=8)
        self.webhooks_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # We'll populate the webhook listbox from load_settings() later
        webhook_buttons_frame = ttk.Frame(discord_frame)
        webhook_buttons_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        ttk.Label(webhook_buttons_frame, text="New Webhook:").pack(side=tk.LEFT, padx=5)
        self.new_webhook_var = tk.StringVar()
        webhook_entry = ttk.Entry(webhook_buttons_frame, textvariable=self.new_webhook_var, width=40)
        webhook_entry.pack(side=tk.LEFT, padx=5)
        add_webhook_btn = ttk.Button(webhook_buttons_frame, text="Add", command=self.add_webhook)
        add_webhook_btn.pack(side=tk.LEFT, padx=5)
        remove_webhook_btn = ttk.Button(webhook_buttons_frame, text="Remove Selected", command=self.remove_webhook)
        remove_webhook_btn.pack(side=tk.LEFT, padx=5)
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        save_btn = ttk.Button(button_frame, text="Save Settings", command=self.save_settings)
        save_btn.pack(side=tk.RIGHT, padx=5)
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=self.cancel)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        reset_btn = ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_defaults)
        reset_btn.pack(side=tk.LEFT, padx=5)

        # Platform Selection
        platform_frame = ttk.Frame(discord_frame)
        platform_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=10)
        ttk.Label(platform_frame, text="Platform:").pack(side=tk.LEFT, padx=5)
        
        # Load platform from DCord.json if it exists, otherwise default to Steam
        default_platform = "Not Selected"
        try:
            if os.path.exists("DCord.json"):
                with open("DCord.json", "r") as f:
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
            "discord_webhooks": self.webhooks,
            "platform": self.platform_var.get()
        }
        try:
            with open("DCord.json", "w") as f:
                json.dump(settings_data, f, indent=4)
            messagebox.showinfo("Success", "Settings saved successfully!")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Could not save settings: {str(e)}")

    def load_settings(self):
        # Load theme, UID, and webhooks from DCord.json only
        try:
            if os.path.exists("DCord.json"):
                with open("DCord.json", "r") as f:
                    loaded_settings = json.load(f)
                    self.settings["discord_uid"] = loaded_settings.get("discord_uid", "")
                    self.settings["discord_webhooks"] = loaded_settings.get("discord_webhooks", [])
                    self.settings["platform"] = loaded_settings.get("platform", "")
        except Exception as e:
            messagebox.showerror("Error", f"Could not load settings: {str(e)}")
        self.discord_uid_var.set(self.settings["discord_uid"])
        self.webhooks = self.settings["discord_webhooks"]
        self.webhooks_listbox.delete(0, tk.END)
        for webhook in self.webhooks:
            self.webhooks_listbox.insert(tk.END, webhook)

    def reset_defaults(self):
        if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset Discord settings to default values?"):
            self.settings = {
                "discord_uid": "",
                "discord_webhooks": []
            }
            self.discord_uid_var.set("")
            self.webhooks = []
            self.webhooks_listbox.delete(0, tk.END)

    def cancel(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to exit? Any unsaved changes will be lost."):
            self.destroy()

    def add_webhook(self):
        webhook = self.new_webhook_var.get().strip()
        if webhook:
            if webhook not in self.webhooks:
                self.webhooks.append(webhook)
                self.webhooks_listbox.insert(tk.END, webhook)
                self.new_webhook_var.set("")
            else:
                messagebox.showwarning("Duplicate", "This webhook already exists in the list.")
        else:
            messagebox.showwarning("Empty Input", "Please enter a webhook URL.")

    def remove_webhook(self):
        selected = self.webhooks_listbox.curselection()
        if selected:
            index = selected[0]
            self.webhooks_listbox.delete(index)
            del self.webhooks[index]
        else:
            messagebox.showwarning("No Selection", "Please select a webhook to remove.")

if __name__ == "__main__":
    app = SettingsPage()
    app.mainloop()
