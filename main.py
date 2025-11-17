# This file is intentionally small: it validates basic user settings
# then imports and runs the application core from `app_core.py`.

from core.app_core import MissionLogGUI, app_path, DEBUG
import json
import re
import logging
import subprocess
import sys
import os
from tkinter import messagebox
import tkinter as tk


def _validate_dcord() -> None:
    """Validate DCord.json has a reasonable Discord UID and a selected platform.

    On failure this will open the settings helper and exit the program.
    """
    try:
        with open(app_path('JSON', 'DCord.json'), 'r', encoding='utf-8') as f:
            settings_data = json.load(f)
        discord_uid = settings_data.get('discord_uid', '0')
        platform = settings_data.get('platform', 'Not Selected')

        if not (re.match(r'^\d{17,19}$', str(discord_uid)) or (DEBUG and str(discord_uid) == '0')):
            logging.error("Please set a valid Discord ID in the settings.py file")
            messagebox.showerror("Error", "Please set a valid Discord ID in the settings.py file")
            # Run settings UI as a module so package imports resolve correctly
            try:
                # Close any open Tkinter root window before launching settings
                try:
                    import tkinter as tk
                    for widget in tk._default_root.children.values():
                        widget.destroy()
                    if tk._default_root:
                        tk._default_root.destroy()
                except Exception:
                    pass
                subprocess.run([sys.executable, '-m', 'core.settings'])
            except Exception:
                # Fallback: execute file directly (older behavior)
                try:
                    settings_path = app_path('core', 'settings.py')
                except Exception:
                    settings_path = os.path.join(os.path.dirname(__file__), 'core', 'settings.py')
                subprocess.run([sys.executable, settings_path])
            raise SystemExit(1)

        if platform == 'Not Selected':
            logging.error("Please set a valid Platform in settings.py")
            messagebox.showerror("Error", "Please set a valid Platform in settings.py")
            # Run settings UI as a module so package imports resolve correctly
            try:
                # Close any open Tkinter root window before launching settings
                try:
                    import tkinter as tk
                    for widget in tk._default_root.children.values():
                        widget.destroy()
                    if tk._default_root:
                        tk._default_root.destroy()
                except Exception:
                    pass
                subprocess.run([sys.executable, '-m', 'core.settings'])
            except Exception:
                try:
                    settings_path = app_path('core', 'settings.py')
                except Exception:
                    settings_path = os.path.join(os.path.dirname(__file__), 'core', 'settings.py')
                subprocess.run([sys.executable, settings_path])
            raise SystemExit(1)

    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error loading DCord.json: {e}")
        messagebox.showerror("Error", f"Error loading DCord.json: {e}")
        raise SystemExit(1)


if __name__ == '__main__':
    _validate_dcord()

    root = tk.Tk()
    app = MissionLogGUI(root)
    root.mainloop()
