# This file is intentionally small: it validates basic user settings
# then imports and runs the application core from `app_core.py`.

import json
import logging
import os
import re
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox

from core.app_core import DEBUG, MissionLogGUI, app_path


# Validates Discord ID/platform and opens Settings if missing; affects startup
def _launch_settings(*, onboarding: bool = False) -> None:
    launch_args = [sys.executable, "-m", "core.settings"]
    if onboarding:
        launch_args.append("--onboarding")
    try:
        subprocess.Popen(launch_args, shell=False)
        return
    except Exception:
        pass
    try:
        settings_path = app_path("core", "settings.py")
    except Exception:
        settings_path = os.path.join(os.path.dirname(__file__), "core", "settings.py")
    fallback_args = [sys.executable, settings_path]
    if onboarding:
        fallback_args.append("--onboarding")
    subprocess.Popen(fallback_args, shell=False)


def _show_settings_error_and_exit(message: str) -> None:
    logging.error(message)
    messagebox.showerror("Settings Required", f"{message}\n\nOpening Settings now.")
    _launch_settings(onboarding=False)
    raise SystemExit(1)


def _validate_dcord() -> None:
    """Validate DCord.json has a reasonable Discord UID and a selected platform.

    On failure this will open the settings helper and exit the program.
    """
    try:
        with open(app_path("JSON", "DCord.json"), "r", encoding="utf-8") as f:
            settings_data = json.load(f)
        discord_uid = settings_data.get("discord_uid", "0")
        platform = settings_data.get("platform", "Not Selected")
        onboarding_completed = bool(settings_data.get("onboarding_completed", False))

        if not onboarding_completed:
            messagebox.showinfo(
                "Welcome to MLHD2",
                "First-run setup is required before using the app.\n\nSettings will open with onboarding guidance.",
            )
            _launch_settings(onboarding=True)
            raise SystemExit(1)

        if not (re.match(r"^\d{17,19}$", str(discord_uid)) or (DEBUG and str(discord_uid) == "0")):
            _show_settings_error_and_exit("Please set a valid Discord ID in Settings")

        if platform == "Not Selected":
            _show_settings_error_and_exit("Please set a valid Platform in Settings")

    except (FileNotFoundError, json.JSONDecodeError):
        messagebox.showinfo(
            "Welcome to MLHD2",
            "Initial setup files are missing or invalid.\n\nSettings will open with onboarding guidance.",
        )
        _launch_settings(onboarding=True)
        raise SystemExit(1)


if __name__ == "__main__":
    _validate_dcord()

    root = tk.Tk()
    app = MissionLogGUI(root)
    root.mainloop()
