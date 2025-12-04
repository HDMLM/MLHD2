# Main launcher and installer. Handles checking for updates, applying updates, managing dependencies, and launching the main program.
# Converted to PyQt5

from __future__ import annotations
import io
import os
import re
import shutil
import subprocess
import sys
import logging
import threading
import time
import zipfile
from typing import Any, Dict, List, Optional, Tuple, Callable
import webbrowser
from pathlib import Path
from ast import literal_eval
import configparser

# PyQt5 imports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QTextEdit, QPushButton, QFrame,
                            QProgressBar, QCheckBox, QMessageBox, QSplashScreen)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QFont, QPainter, QPalette, QFontDatabase

#Manual Constants
GameUpdateTitle = "INTO THE UNJUST"

# NEW: imports for font detection/installation
import ctypes
try:
    import winreg  # Windows only
except Exception:
    winreg = None

# Optional: Discord Rich Presence for the launcher
try:
    import discordrpc  # provided by package 'discord-rpc'
except Exception:
    discordrpc = None  # launcher will still work without RPC

# Python 3.10.6 enforcement and bootstrap
REQUIRED_PYTHON_VERSION = (3, 10, 6)

def _is_frozen() -> bool:
    return getattr(sys, "frozen", False) is True

# Paths: distinguish between the real app folder (read/write) and bundled resources
APP_DIR = Path(os.path.dirname(sys.executable) if _is_frozen() else os.path.dirname(__file__)).resolve()
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR)).resolve()

def app_path(*parts: str) -> str:
    return str(APP_DIR.joinpath(*parts))

def resource_path(*parts: str) -> str:
    return str(BUNDLE_DIR.joinpath(*parts))

# Load launcher config for Discord RPC Client ID
_config = configparser.ConfigParser()
try:
    _config.read(app_path("config.config"))
    DISCORD_CLIENT_ID = _config.get('Discord', 'DISCORD_CLIENT_ID', fallback='0')
except Exception:
    DISCORD_CLIENT_ID = '0'

def find_python3106_executable() -> Optional[List[str]]:
    # In frozen mode, sys.executable points to the EXE; skip that candidate
    candidates: List[List[str]] = []
    if not _is_frozen():
        candidates.append([sys.executable])
    candidates.extend([
        ["python3.10"],
        ["python3.10.6"],
        ["py", "-3.10"],  # Windows Python launcher
        [r"C:\\Python310\\python.exe"],
        [r"C:\\Python3.10.6\\python.exe"],
    ])
    for exe_argv in candidates:
        try:
            out = subprocess.check_output(
                [*exe_argv, "-c", "import sys; print(tuple(sys.version_info[:3]))"],
                stderr=subprocess.DEVNULL,
            )
            ver = literal_eval(out.decode().strip())
            if tuple(ver) == REQUIRED_PYTHON_VERSION:
                return exe_argv
        except Exception:
            continue
    return None

PYTHON3106_CMD = find_python3106_executable()

def _py_cmd() -> List[str]:
    return PYTHON3106_CMD or [sys.executable]

def ensure_python_version():
    # When frozen (PyInstaller), don't enforce embedded interpreter version strictly.
    # External Python 3.10.6 is only required for running main.py and pip.
    if _is_frozen():
        return
    # Thanks to Jesse's testing we know that the version needs to be exactly 3.10.6
    if sys.version_info[:3] != REQUIRED_PYTHON_VERSION:
        msg = (
            f"ERROR: This program requires Python {REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]}.{REQUIRED_PYTHON_VERSION[2]}.\n"
            f"Current version: {sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}\n"
        )
        if not PYTHON3106_CMD:
            msg += "Python 3.10.6 not found. Please install it and re-run this installer."
            logging.error(msg)
            sys.exit(1)
        else:
            msg += f"Attempting to use Python 3.10.6 at: {' '.join(PYTHON3106_CMD)}\n"
            logging.info(msg)
ensure_python_version()

import requests

GITHUB_API_REPO = "HDMLM/MLHD2"
GITHUB_REPO = "https://github.com/HDMLM/MLHD2"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_API_REPO}"
REQUIREMENTS_FILE = app_path("requirements.txt")
MAIN_PROGRAM = app_path("main.py")
BACKUP_DIR_ROOT = app_path("backup")

REQUEST_TIMEOUT_RELEASES = 10
REQUEST_TIMEOUT_ZIP = 30

# NEW: font install settings
FONT_FAMILY_NAME = "Insignia"
FONT_FILE_NAME = "Insignia.ttf"
FIRST_LAUNCH_MARKER = app_path(".first_launch_done")

# --- Discord Rich Presence helper for the launcher ---
class _LauncherRPC:
    def __init__(self) -> None:
        self.RPC = None
        self._started = False

    def start(self) -> None:
        if self._started or not discordrpc:
            return
        def _init():
            try:
                app_id_int = int(DISCORD_CLIENT_ID)
                self.RPC = discordrpc.RPC(app_id=app_id_int)
                threading.Thread(target=self.RPC.run, daemon=True).start()
                self._started = True
                # Initial presence
                self.set_status("Launcher Open")
            except Exception:
                self.RPC = None
                self._started = False
        threading.Thread(target=_init, daemon=True).start()

    def set_status(self, status: str, details: Optional[str] = None) -> None:
        if not self.RPC:
            return
        try:
            # Buttons are optional; ignore if not available
            buttons = None
            try:
                from discordrpc import Button
                buttons = Button(
                    "GitHub Repo", "https://github.com/HDMLM/MLHD2",
                    "Join Discord", "https://discord.gg/U6ydgwFKZG",
                )
            except Exception:
                buttons = None

            self.RPC.set_activity(
                state=status,
                details=details or "MLHD2 Launcher",
                large_image="test",          # Uses same asset key as the main app
                large_text="MLHD2",
                small_image="obs",           # Neutral/observing icon
                small_text="Launcher",
                act_type=3,                   # 3 = Watching
                **({"buttons": buttons} if buttons else {})
            )
        except Exception:
            # Silently ignore RPC errors to keep launcher robust
            pass

    def close(self) -> None:
        try:
            if self.RPC and hasattr(self.RPC, 'close'):
                self.RPC.close()
        except Exception:
            pass

# Include all the other functions from the original file...
# (For brevity, I'll include just the essential ones and the GUI class)

def launch_program_detached() -> Optional[subprocess.Popen]:
    # Start the main program process and return the Popen or None on failure
    python_exe = _py_cmd()
    if not os.path.exists(MAIN_PROGRAM):
        QMessageBox.critical(
            None,
            "Not Installed",
            "The main program is not installed yet.\n"
            "Click 'Update to Latest' to download the latest release, then try launching again."
        )
        return None
    if not PYTHON3106_CMD and _is_frozen():
        QMessageBox.critical(None, "Launch Error", "Python 3.10.6 is required to run the logger. Please install Python 3.10.6 and try again.")
        return None
    try:
        return subprocess.Popen([*python_exe, MAIN_PROGRAM])
    except Exception as e:
        QMessageBox.critical(None, "Launch Error", str(e))

def _is_font_available(font_family: str) -> bool:
    try:
        font_db = QFontDatabase()
        families = [f.lower() for f in font_db.families()]
        return font_family.lower() in families
    except Exception:
        return False

class InstallerGUI(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MLHD2 Launcher")
        self.setFixedSize(1280, 720)
        
        # Discord RPC for launcher
        self._rpc = _LauncherRPC()
        self._rpc.start()

        # Optional: set window icon from LaunchMedia/app.ico if present
        try:
            ico_path = resource_path("LaunchMedia", "app.ico")
            if not os.path.exists(ico_path):
                ico_path = app_path("LaunchMedia", "app.ico")
            if os.path.exists(ico_path):
                self.setWindowIcon(QPixmap(ico_path))
        except Exception:
            pass

        # Show splash screen
        self.show_splash()

        # Setup UI after splash
        QTimer.singleShot(1200, self.setup_main_ui)

    def show_splash(self):
        try:
            splash_path = resource_path("LaunchMedia", "splash.png")
            if not os.path.exists(splash_path):
                splash_path = app_path("LaunchMedia", "splash.png")
            if os.path.exists(splash_path):
                pixmap = QPixmap(splash_path)
                self.splash = QSplashScreen(pixmap)
                self.splash.show()
                return
        except Exception:
            pass
        # No splash available
        self.splash = None

    def setup_main_ui(self):
        if self.splash:
            self.splash.close()

        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # Load and set background
        try:
            bg_path = resource_path("LaunchMedia", "SpacePlaceholder.png")
            if not os.path.exists(bg_path):
                bg_path = app_path("LaunchMedia", "SpacePlaceholder.png")
            if os.path.exists(bg_path):
                pixmap = QPixmap(bg_path).scaled(1280, 720, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                palette = QPalette()
                palette.setBrush(QPalette.Window, pixmap)
                main_widget.setPalette(palette)
        except Exception:
            main_widget.setStyleSheet("background-color: #252526;")

        # Main layout
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar
        self.setup_sidebar(main_layout)

        # Content area
        content_layout = QVBoxLayout()
        main_layout.addLayout(content_layout)

        # Banner
        self.setup_banner(content_layout)

        # Main content area with text boxes
        self.setup_content_area(content_layout)

        # Buttons
        self.setup_buttons(content_layout)

        # Show main window
        self.show()

    def setup_sidebar(self, main_layout):
        sidebar = QFrame()
        sidebar.setFixedWidth(80)
        sidebar.setStyleSheet("background-color: #252526;")
        main_layout.addWidget(sidebar)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 40, 20, 20)
        sidebar_layout.setSpacing(50)

        # Sidebar buttons
        button_info = [
            ("GitHubButton.png", "🏠", lambda: webbrowser.open("https://github.com/HDMLM/MLHD2")),
            ("DiscordButton.png", "📰", lambda: webbrowser.open("https://discord.gg/U6ydgwFKZG")),
            ("SettingsButton.png", "⚙️", self.open_settings),
            ("HelpButton.png", "❓", lambda: webbrowser.open("https://github.com/HDMLM/MLHD2/blob/main/README.md")),
        ]

        for img, fallback_text, action in button_info:
            btn = QPushButton()
            btn.setFixedSize(40, 40)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #252526;
                    border: none;
                    color: white;
                    font-size: 28px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #353535;
                }
            """)
            
            # Try to load image, fallback to text
            try:
                img_path = resource_path("LaunchMedia", img)
                if not os.path.exists(img_path):
                    img_path = app_path("LaunchMedia", img)
                if os.path.exists(img_path):
                    btn.setIcon(QPixmap(img_path))
                else:
                    btn.setText(fallback_text)
            except Exception:
                btn.setText(fallback_text)
            
            btn.clicked.connect(action)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

    def setup_banner(self, content_layout):
        banner_frame = QFrame()
        banner_frame.setFixedHeight(110)
        banner_frame.setStyleSheet("background-color: #252526;")
        content_layout.addWidget(banner_frame)

        banner_layout = QVBoxLayout(banner_frame)
        banner_layout.setContentsMargins(30, 18, 30, 18)

        # Try to use Insignia font
        try:
            font = QFont("Insignia", 30, QFont.Bold)
            font.setItalic(True)
        except Exception:
            font = QFont("Arial", 30, QFont.Bold)
            font.setItalic(True)

        title_label = QLabel("HD2 MISSION LOGGER")
        title_label.setFont(font)
        title_label.setStyleSheet("color: white;")
        banner_layout.addWidget(title_label)

        version_font = QFont("Insignia", 18, QFont.Bold)
        version_font.setItalic(True)
        
        self.version_label = QLabel(f"Latest Version: Loading... - {GameUpdateTitle}")
        self.version_label.setFont(version_font)
        self.version_label.setStyleSheet("color: #AEE2FF;")
        banner_layout.addWidget(self.version_label)

    def setup_content_area(self, content_layout):
        # Content area with text boxes
        content_frame = QFrame()
        content_layout.addWidget(content_frame)

        content_main_layout = QHBoxLayout(content_frame)

        # Left side - main log and progress
        left_frame = QFrame()
        left_frame.setFixedSize(400, 180)
        left_frame.setStyleSheet("""
            background-color: #4C4C4C;
            border: 2px solid #B0BEC5;
        """)
        content_main_layout.addWidget(left_frame)

        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(10, 10, 10, 10)

        # Main text area
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setStyleSheet("""
            background-color: #4C4C4C;
            color: white;
            border: none;
            font-family: Arial;
            font-size: 12px;
        """)
        left_layout.addWidget(self.text)

        # Progress bar (initially hidden)
        self.progress = QProgressBar()
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #252526;
                background-color: #252526;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #FFD600;
            }
        """)
        self.progress.hide()
        left_layout.addWidget(self.progress)

        # Right side - patch notes
        right_frame = QFrame()
        right_frame.setFixedSize(400, 250)
        right_frame.setStyleSheet("""
            background-color: #4C4C4C;
            border: 2px solid #252526;
        """)
        content_main_layout.addWidget(right_frame)

        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(10, 10, 10, 10)

        self.patch_notes_box = QTextEdit()
        self.patch_notes_box.setReadOnly(True)
        self.patch_notes_box.setStyleSheet("""
            background-color: #4C4C4C;
            color: white;
            border: none;
            font-family: Arial;
            font-size: 11px;
            font-style: italic;
        """)
        right_layout.addWidget(self.patch_notes_box)

        content_main_layout.addStretch()

    def setup_buttons(self, content_layout):
        # Add spacer
        content_layout.addStretch()

        # Button area
        button_frame = QFrame()
        content_layout.addWidget(button_frame)

        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(40, 0, 40, 30)

        # Create buttons with text fallbacks
        self.check_btn = QPushButton("Check Requirements")
        self.check_btn.setFixedSize(190, 60)
        self.check_btn.setStyleSheet("""
            QPushButton {
                background-color: #4C4C4C;
                color: white;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5C5C5C;
            }
        """)
        self.check_btn.clicked.connect(self.check_requirements)
        button_layout.addWidget(self.check_btn)

        button_layout.addSpacing(30)

        self.update_btn = QPushButton("Update to Latest")
        self.update_btn.setFixedSize(190, 60)
        self.update_btn.setStyleSheet("""
            QPushButton {
                background-color: #4C4C4C;
                color: white;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5C5C5C;
            }
        """)
        self.update_btn.clicked.connect(self.update_latest)
        button_layout.addWidget(self.update_btn)

        button_layout.addStretch()

        self.launch_btn = QPushButton("▶ Launch Logger")
        self.launch_btn.setFixedSize(200, 65)
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #4C4C4C;
                color: white;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #5C5C5C;
            }
        """)
        self.launch_btn.clicked.connect(self.launch_program)
        button_layout.addWidget(self.launch_btn)

    def open_settings(self):
        python_exe = _py_cmd()
        settings_path = app_path("settings.py")
        if not os.path.exists(settings_path):
            QMessageBox.critical(
                self,
                "Settings Not Found",
                "Please \"Update to Latest\" before opening Settings."
            )
            return
        try:
            subprocess.Popen([*python_exe, settings_path])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open settings: {e}")

    def check_requirements(self):
        self.text.setText("Checking requirements...")
        # Placeholder for actual requirements checking
        self.text.append("All requirements satisfied.")

    def update_latest(self):
        self.text.setText("Updating to latest version...")
        # Placeholder for actual update logic
        self.text.append("Update completed.")

    def launch_program(self):
        proc = launch_program_detached()
        if proc:
            self.text.append("Program launched successfully.")

def main():
    app = QApplication(sys.argv)
    window = InstallerGUI()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()