# This file is intentionally small: it validates basic user settings
# then imports and runs the application core from `app_core.py`.

# The original, full application source has been preserved in
# `main_full_backup.py` in this repository root.

from app_core import MissionLogGUI, app_path, DEBUG
import json
import re
import logging
import subprocess
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
            subprocess.run(['python', 'settings.py'])
            raise SystemExit(1)

        if platform == 'Not Selected':
            logging.error("Please set a valid Platform in settings.py")
            messagebox.showerror("Error", "Please set a valid Platform in settings.py")
            subprocess.run(['python', 'settings.py'])
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
