# Main launcher and installer. Handles checking for updates, applying updates, managing dependencies, and launching the main program.
# id rather this be a minimal import file but sadly python says no
# I wonder if it's possible to package them alongside the launcher in a zip or something, preferably without needing to unzip them so the user doesn't have to deal with it.
# I think this is something we'll need to look into for distribution, i think pyinstaller can do it but im not sure how well it works with the dynamic imports we need for the version checking in the Main.py
# im curious actually if this requires requests to be installed to run the launcher, if so that kinda sucks, i think we'll have to find out via Jesse's testing

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


#Manual Constants
GameUpdateTitle = "INTO THE UNJUST"

# NEW: imports for font detection/installation
import ctypes
try:
    import winreg  # Windows only
except Exception:
    winreg = None
import tkinter.font as tkfont

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
import tkinter as tk
from tkinter import messagebox, scrolledtext
from tkinter import ttk

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

# Exclusion globs / prefixes relative to repo root (from inside the ZIP)
# We don't want to overwrite user data since even if it's outdated the program should update the JSON as required, though we could add the option
# to clear the JSON's if the user wants to reset their data or we make a change that requires it. for future consideration i guess
EXCLUDE_PATH_PREFIXES = (
    "JSON/persistent",  # user persistent data variants
    "JSON/settings",    # user settings variants
    "JSON/streak_data", # user streak data
    "backup",           # avoid recursing into previous backups
    ".git",             # git internals
    "venv",             # local virtual env - This should never be in the repo but just in case
    "mission_log.xlsx", # user excel log file
    "DCord.json",       # user discord config
)

def _is_excluded(rel_path: str) -> bool:
    # Return True if a relative path should be skipped during update
    normalized = rel_path.replace("\\", "/").lstrip("./")
    return any(normalized.startswith(pref) for pref in EXCLUDE_PATH_PREFIXES)

# NEW: validate files/dirs against LaunchMedia/FStruct.json
def _validate_files_against_fstruct() -> Tuple[int, int, int, List[str], List[str]]:
    """
    Returns:
      total_expected (int): total expected entries (files+dirs, required only)
      missing_required (int)
      missing_optional (int)
      missing_required_list (List[str])  relative paths
      missing_optional_list (List[str])  relative paths
    """
    try:
        import json
        # Locate FStruct.json (prefer bundled, fallback to app dir)
        candidates = [
            resource_path("LaunchMedia", "FStruct.json"),
            app_path("LaunchMedia", "FStruct.json"),
            app_path("FStruct.json"),
        ]
        fstruct_path = next((p for p in candidates if os.path.exists(p)), "")
        if not fstruct_path:
            return -1, 0, 0, [], []  # not found; signal skipped

        with open(fstruct_path, "r", encoding="utf-8") as f:
            spec = json.load(f)

        # Flatten tree (ignore the root name and start from its children)
        required: List[Tuple[str, str]] = []  # (type, relpath)
        optional: List[Tuple[str, str]] = []  # (type, relpath)

        def is_optional(node_type: str, name: str, rel_path: str) -> bool:
            # Treat data files and dotfiles as optional; adjust if needed
            if node_type == "data":
                return True
            if os.path.basename(name).startswith("."):
                return True
            return False

        def walk(children: List[Dict[str, Any]], base: str = "") -> None:
            for ch in children or []:
                t = ch.get("type", "")
                n = ch.get("name", "")
                if not n:
                    # Skip anonymous container nodes; recurse into their children at same base
                    sub = ch.get("children", [])
                    if sub:
                        walk(sub, base)
                    continue
                rel = os.path.normpath(os.path.join(base, n))
                if t == "dir":
                    (optional if is_optional(t, n, rel) else required).append(("dir", rel))
                    walk(ch.get("children", []), rel)
                else:
                    (optional if is_optional(t, n, rel) else required).append(("file", rel))

        walk(spec.get("children", []), "")

        def exists(entry_type: str, rel: str) -> bool:
            full = os.path.join(str(APP_DIR), rel)
            if entry_type == "dir":
                return os.path.isdir(full)
            return os.path.isfile(full)

        missing_req = [rel for (t, rel) in required if not exists(t, rel)]
        missing_opt = [rel for (t, rel) in optional if not exists(t, rel)]

        return len(required), len(missing_req), len(missing_opt), missing_req, missing_opt
    except Exception:
        # On any error, don't block normal flow
        return -1, 0, 0, [], []


_VERSION_REGEX = re.compile(r'^\s*VERSION\s*=\s*["\']([^"\']+)["\']')


def get_local_version() -> Optional[str]:
    # Extract version string from Main.py (VERSION = "...")
    try:
        with open(MAIN_PROGRAM, "r", encoding="utf-8") as f:
            for line in f:
                m = _VERSION_REGEX.match(line)
                if m:
                    return m.group(1).strip()
    except FileNotFoundError:
        # Fresh install scenario: main program not present yet
        return None
    except Exception as e:
        # Return a sentinel string describing unexpected error so caller can surface it
        return f"__ERROR__:{e}"
    return None

def _github_headers() -> Dict[str, str]:
    # Build headers for GitHub API calls
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _github_get(path: str, timeout: int = REQUEST_TIMEOUT_RELEASES) -> Optional[Any]:
    # Perform a GET to the GitHub API returning JSON or None on failure
    url = f"{GITHUB_API_BASE}/{path.lstrip('/')}"
    try:
        r = requests.get(url, headers=_github_headers(), timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def fetch_releases() -> List[Dict[str, Any]]:
    # Return non-draft releases newest first
    data = _github_get("releases")
    if not isinstance(data, list):
        return []
    return [r for r in data if not r.get("draft")]

def pick_latest_release(include_prerelease: bool) -> Optional[Dict[str, Any]]:
    # Return the most recent release
    releases = fetch_releases()
    if not releases:
        return None
    if include_prerelease:
        return releases[0]
    return next((r for r in releases if not r.get("prerelease")), None)

def download_release_zip(include_prerelease: bool) -> Tuple[Optional[str], Optional[bytes], str]:
    # Download selected release zipball. Returns (tag, bytes, error_message)
    rel = pick_latest_release(include_prerelease=include_prerelease)
    if not rel:
        return None, None, "No release metadata available"
    tag = rel.get("tag_name") or rel.get("name")
    zip_url = rel.get("zipball_url")
    if not zip_url:
        return None, None, "Zip URL missing in release data"
    try:
        r = requests.get(zip_url, headers=_github_headers(), timeout=REQUEST_TIMEOUT_ZIP)
        if r.status_code != 200:
            return None, None, f"Download failed HTTP {r.status_code}"
        return tag, r.content, ""
    except Exception as e:
        return None, None, f"Download error: {e}"

def safe_zip_update(include_prerelease: bool = False) -> str:
    # Perform safe update via zip archive with backup of changed files

    #check if current version is higher than latest version if so skip update
    local_version = get_local_version()
    latest = get_latest_github_version(include_prerelease=include_prerelease)
    if not isinstance(latest, str):
        return f"Could not determine GitHub version: {latest}"
    if local_version and not local_version.startswith("__ERROR__:"):
        cmp_result = _compare_versions(local_version, latest)
        if cmp_result > 0:
            return "Local version is ahead of GitHub release (development build). No update applied."
    # If local_version is None (fresh install) or an error string, proceed with installation/update


    tag, content, err = download_release_zip(include_prerelease=include_prerelease)
    if err:
        return ("Safe update failed: " + err +
                "\nTroubleshooting:\n - Check internet connectivity\n - Set GITHUB_TOKEN env var if rate-limited\n - Retry with prerelease toggle adjusted\n - As last resort clone repo manually.")
    if not content:
        return ("Safe update failed: empty archive\nThis may indicate a transient GitHub issue. Retry in a minute.")
    updated = created = skipped = excluded = backed_up = 0
    errors: List[str] = []
    ts = time.strftime('%Y%m%d-%H%M%S')
    backup_root = os.path.join(BACKUP_DIR_ROOT, ts)
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            # Determine common top-level directory in GitHub zipball
            members = z.namelist()
            if not members:
                return "Safe update failed: archive empty"
            top = members[0].split('/')[0]
            for member in members:
                if member.endswith('/'):
                    continue
                # Strip top-level folder
                parts = member.split('/')
                if parts[0] != top:
                    # Unexpected structure, still attempt relative mapping
                    rel_path = member
                else:
                    rel_path = '/'.join(parts[1:])
                if not rel_path:
                    continue
                if _is_excluded(rel_path):
                    excluded += 1
                    continue
                # Always write updates into the application directory
                dest_path = os.path.join(str(APP_DIR), rel_path.replace('/', os.sep))
                dest_dir = os.path.dirname(dest_path)
                try:
                    os.makedirs(dest_dir, exist_ok=True)
                    data = z.read(member)
                    # Decide if needs copy
                    if os.path.exists(dest_path):
                        # Compare size & content quickly
                        try:
                            with open(dest_path, 'rb') as existing:
                                if existing.read() == data:
                                    skipped += 1
                                    continue
                        except Exception:
                            pass
                        # Backup then overwrite
                        backup_path = os.path.join(backup_root, rel_path.replace('/', os.sep))
                        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                        shutil.copy2(dest_path, backup_path)
                        backed_up += 1
                        with open(dest_path, 'wb') as f:
                            f.write(data)
                        updated += 1
                    else:
                        with open(dest_path, 'wb') as f:
                            f.write(data)
                        created += 1
                except Exception as e:
                    errors.append(f"{rel_path}: {e}")
        summary = [
            f"Safe ZIP Update to {tag}",
            f"Created: {created}",
            f"Updated: {updated}",
            f"Backed up: {backed_up}",
            f"Unchanged (skipped): {skipped}",
            f"Excluded: {excluded}",
        ]
        if errors:
            summary.append(f"Errors: {len(errors)}")
            summary.extend(errors[:10])
        if backed_up > 0:
            summary.append(f"Backup stored in {backup_root}")
        return "\n".join(summary)
    except Exception as e:
        return (f"Safe update failed during extraction: {e}\n"
                "Ensure disk space and that existing files are not locked by another process.")

def get_latest_github_version(full: bool = False, include_prerelease: bool = False) -> Any:
    # Return latest release metadata or just tag (error string on failure)
    rel = pick_latest_release(include_prerelease=include_prerelease)
    if not rel:
        return "Could not fetch releases (possible rate limit or network issue)."
    tag = rel.get("tag_name") or rel.get("name")
    if full:
        return {
            "tag": tag,
            "body": rel.get("body", "No patch notes found."),
            "prerelease": rel.get("prerelease", False),
        }
    return tag

def _parse_version(v: str) -> List[int]:
    # Parse dotted version string into list of ints; strip leading v and non-digit tails
    if not v:
        return []
    v = v.strip()
    if v.startswith(('v', 'V')):
        v = v[1:]
    parts = []
    for seg in v.split('.'):
        seg = seg.strip()
        if not seg:
            parts.append(0)
            continue
        num = ''
        for ch in seg:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    # Trim trailing zeros
    while parts and parts[-1] == 0:
        parts.pop()
    return parts


def _compare_versions(a: str, b: str) -> int:
    # Compare two version strings a vs b; return 1, -1, or 0
    pa = _parse_version(a)
    pb = _parse_version(b)
    max_len = max(len(pa), len(pb))
    for i in range(max_len):
        ai = pa[i] if i < len(pa) else 0
        bi = pb[i] if i < len(pb) else 0
        if ai > bi:
            return 1
        if ai < bi:
            return -1
    return 0

def _canon_name(name: str) -> str:
    # PEP 503 canonicalization: collapse -, _, . to - and lowercase
    return re.sub(r'[-_.]+', '-', name).lower()

def check_version(include_prerelease: bool = False) -> str:
    # Return formatted version + patch notes using semantic comparison
    raw_local = get_local_version()
    latest = get_latest_github_version(full=True, include_prerelease=include_prerelease)
    if not isinstance(latest, dict):
        # Even if we can't get latest metadata, show local state
        if raw_local is None:
            return f"Current version: Not installed\nLatest GitHub version: (error fetching releases)\nCannot fetch patch notes right now. Try again later."
        elif isinstance(raw_local, str) and raw_local.startswith("__ERROR__:"):
            return f"Current version: Error determining local version ({raw_local[10:]})\nLatest GitHub version: (error fetching releases)\nCannot fetch patch notes right now. Try again later."
        else:
            return f"Current version: {raw_local}\nLatest GitHub version: (error fetching releases)\nCannot fetch patch notes right now. Try again later."

    latest_version = latest.get("tag", "?")
    notes = latest.get("body", "No patch notes found.")
    is_pr = latest.get("prerelease", False)

    if raw_local is None:
        status_line = "Not installed yet. Click 'Update to Latest' to install."
        local_display = "Not installed"
    elif raw_local.startswith("__ERROR__:"):
        status_line = "Local version unreadable (see log). You can still attempt an update."
        local_display = f"Error: {raw_local[10:]}"
    else:
        local_display = raw_local
        cmp_result = _compare_versions(raw_local, latest_version)
        if cmp_result == 0:
            status_line = "You are up to date!"
        elif cmp_result > 0:
            status_line = "Local version is ahead of GitHub release (development build)."
        else:
            status_line = "Update available!"

    return (
        f"Current version: {local_display}\n"
        f"Latest GitHub version: {latest_version}{' (pre-release)' if is_pr else ''}\n"
        f"{status_line}\n\nPatch Notes:\n{notes}"
    )
def check_requirements(
    log_callback: Optional[Callable[[str], None]] = None,
    progress_init: Optional[Callable[[int], None]] = None,
    progress_tick: Optional[Callable[[int], None]] = None,
    progress_done: Optional[Callable[[], None]] = None,
) -> str:
    # Ensure packages in requirements.txt are installed and report per-package status
    output: List[str] = []
    progress_initialized = False

    def log(line: str) -> None:
        # Word wrap at 80 chars for better display
        import textwrap
        wrapped = textwrap.fill(line, width=80)
        output.append(wrapped)
        if log_callback:
            log_callback(wrapped + "\n")

    def read_requirements_lines(path: str) -> List[str]:
        # Read requirements file with multiple encoding fallbacks
        encodings = ["utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "latin-1"]
        last_err: Optional[Exception] = None
        for enc in encodings:
            try:
                with open(path, "r", encoding=enc) as f:
                    lines = []
                    for raw in f:
                        line = raw.strip()
                        if not line or line.startswith('#'):
                            continue
                        lines.append(line)
                    return lines
            except Exception as e:
                last_err = e
                continue
        if last_err:
            raise last_err
        return []

    def get_installed_packages() -> Dict[str, str]:
        # Return mapping of installed package -> version using single pip list call
        python_exe = _py_cmd()
        try:
            # Hide console windows on Windows while invoking pip
            startupinfo = None
            creationflags = 0
            if os.name == "nt":
                try:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    creationflags = subprocess.CREATE_NO_WINDOW
                except Exception:
                    startupinfo = None
                    creationflags = 0
            data = subprocess.check_output(
                [*python_exe, "-m", "pip", "list", "--format", "json", "--disable-pip-version-check"],
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo,
                creationflags=creationflags,
            )
            import json
            pkgs = json.loads(data.decode("utf-8", errors="replace"))
            return {_canon_name(p["name"]): p.get("version", "") for p in pkgs if isinstance(p, dict) and "name" in p}
        except Exception:
            return {}

    def install_or_update(pkg: str, target: Optional[str]) -> Tuple[bool, str]:
        # Install or update a package; target is exact version string or None
        python_exe = _py_cmd()
        spec = f"{pkg}=={target}" if target else pkg
        # Show real pip output when debugging to aid troubleshooting
        DEBUG_MODE = bool(sys.gettrace()) or os.environ.get("MLHD2_DEBUG_PIP")
        try:
            cmd = [*python_exe, "-m", "pip", "install", spec, "--disable-pip-version-check", "--no-input"]
            # Hide console windows on Windows when not in debug mode
            startupinfo = None
            creationflags = 0
            if os.name == "nt" and not DEBUG_MODE:
                try:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    creationflags = subprocess.CREATE_NO_WINDOW
                except Exception:
                    startupinfo = None
                    creationflags = 0
            if DEBUG_MODE:
                # Don't redirect so errors are visible in the console
                subprocess.check_call(cmd)
            else:
                subprocess.check_call(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.STDOUT,
                    startupinfo=startupinfo,
                    creationflags=creationflags,
                )
            return True, ""
        except subprocess.CalledProcessError as e:
            return False, f"pip exit code {e.returncode}"
        except Exception as e:
            return False, str(e)

    MGMT_PACKAGES = {"pip", "setuptools", "wheel"}  # skip these

    failures: List[str] = []
    updated_count = 0
    installed_count = 0

    try:
        if _is_frozen() and not PYTHON3106_CMD:
            log("Python 3.10.6 not found. Cannot verify or install requirements from the bundled launcher.")
            log("Please install Python 3.10.6 and run 'Check Requirements' again, or run 'pip install -r requirements.txt' manually.")
            return "Summary: Skipped (Python 3.10.6 missing)"
        # In frozen mode, REQUIREMENTS_FILE might not exist next to the EXE; look in app dir specifically
        if not os.path.exists(REQUIREMENTS_FILE):
            alt_req = app_path("requirements.txt")
            if os.path.exists(alt_req):
                req_path = alt_req
            else:
                req_path = REQUIREMENTS_FILE
        else:
            req_path = REQUIREMENTS_FILE
        requirements = read_requirements_lines(req_path)
        if not requirements:
            log("No requirements found (file empty or unreadable).")
        installed = get_installed_packages()

        # Normalize requirements into (name, pinned_version|None)
        parsed_reqs: List[Tuple[str, Optional[str]]] = []
        for req in requirements:
            if '==' in req:
                pkg, pinned_version = req.split('==', 1)
                parsed_reqs.append((pkg.strip(), pinned_version.strip()))
            else:
                parsed_reqs.append((req.strip(), None))

        # Add one extra step for file validation
        total = len(parsed_reqs) + 1
        if progress_init:
            try:
                progress_init(total)
                progress_initialized = True
            except Exception:
                progress_initialized = False
        for idx, (pkg, pinned) in enumerate(parsed_reqs, start=1):
            if not pkg:
                continue
            key = _canon_name(pkg)
            if key in MGMT_PACKAGES:
                log(f"[{idx}/{total}] {pkg}: Skipping (management package).")
                if progress_tick:
                    try:
                        progress_tick(1)
                    except Exception:
                        pass
                continue

            log(f"[{idx}/{total}] Checking {pkg} ...")
            installed = get_installed_packages()  # refresh snapshot
            if key in installed:
                current_v = installed[key]
                if pinned and _compare_versions(current_v, pinned) != 0:
                    log(f"  - Found {pkg} {current_v}; requires {pinned}. Updating...")
                    ok, err = install_or_update(pkg, pinned)
                    if ok:
                        installed = get_installed_packages()
                        final_v = installed.get(key, "")
                        if final_v and _compare_versions(final_v, pinned) == 0:
                            updated_count += 1
                            log(f"  - UPDATED to {pinned}")
                        else:
                            msg = f"{pkg}: UPDATE FAILED (wanted {pinned}, now {final_v or 'not installed'})"
                            log(f"  - {msg}")
                            failures.append(msg)
                    else:
                        msg = f"{pkg}: UPDATE FAILED ({err})"
                        log(f"  - {msg}")
                        failures.append(msg)
                else:
                    log(f"  - OK ({current_v})")
            else:
                target_desc = pinned if pinned else "latest"
                log(f"  - Not installed. Installing ({target_desc})...")
                ok, err = install_or_update(pkg, pinned)
                if ok:
                    installed = get_installed_packages()
                    final_v = installed.get(key, "")
                    if final_v and (not pinned or _compare_versions(final_v, pinned) == 0):
                        installed_count += 1
                        log(f"  - INSTALLED ({final_v})")
                    else:
                        msg = f"{pkg}: INSTALL VERIFIED FAILED (wanted {pinned or 'any'}, now {final_v or 'missing'})"
                        log(f"  - {msg}")
                        failures.append(msg)
                else:
                    msg = f"{pkg}: INSTALL FAILED ({err})"
                    log(f"  - {msg}")
                    failures.append(msg)
            if progress_tick:
                try:
                    progress_tick(1)
                except Exception:
                    pass
    except Exception as e:
        log(f"Error reading requirements: {e}")

    # NEW: Validate files/dirs using FStruct.json
    try:
        # If we never initialized the progress bar due to an early error, initialize with a single step for file check
        if not progress_initialized and progress_init:
            try:
                progress_init(1)
                progress_initialized = True
            except Exception:
                pass
        log("")
        log("Validating files against LaunchMedia/FStruct.json ...")
        total_expected, miss_req, miss_opt, miss_req_list, miss_opt_list = _validate_files_against_fstruct()
        if total_expected == -1:
            log("Files: FStruct.json not found. Skipped file validation.")
        else:
            if miss_req == 0 and miss_opt == 0:
                log("Files: All files present.")
            elif miss_req == 0:
                log(f"Files: OK (0 missing required). Optional missing: {miss_opt}")
                # List a few optional misses for visibility
                for p in miss_opt_list[:10]:
                    log(f"  - missing optional: {p}")
            else:
                log(f"Files: {miss_req} missing required file(s). Optional missing: {miss_opt}")
                for p in miss_req_list[:15]:
                    log(f"  - MISSING: {p}")
                # Show a few optional too
                for p in miss_opt_list[:5]:
                    log(f"  - missing optional: {p}")
    except Exception as e:
        log(f"Files: Validation error: {e}")
    finally:
        if progress_tick:
            try:
                # Count the file validation as one progress step
                progress_tick(1)
            except Exception:
                pass
        if progress_done:
            try:
                progress_done()
            except Exception:
                pass

    # Summary
    if output and output[-1] != "":
        log("")
    if failures:
        log(f"Summary: {len(failures)} issue(s) detected.")
        for f in failures:
            log(f" - {f}")
    else:
        log("Summary: All requirements satisfied.")
    if updated_count or installed_count:
        log(f"Actions: {installed_count} installed, {updated_count} updated.")

    # Only return the summary for the version box, not the full log
    summary_lines = []
    for line in output:
        if (
            line.startswith("Summary:")
            or line.startswith("Actions:")
            or line.startswith("Error reading requirements:")
            or line.startswith("Files:")            # NEW: include file validation in silent summary
        ):
            summary_lines.append(line)
        elif line.strip().startswith("- MISSING:") or line.strip().startswith("- missing optional:"):
            # Include detailed missing entries in silent summary
            summary_lines.append(line)
    return "\n".join(summary_lines) if summary_lines else "\n".join(output[-10:])

def launch_program_detached() -> Optional[subprocess.Popen]:
    # Start the main program process and return the Popen or None on failure
    python_exe = _py_cmd()
    if not os.path.exists(MAIN_PROGRAM):
        messagebox.showerror(
            "Not Installed",
            "The main program is not installed yet.\n"
            "Click 'Update to Latest' to download the latest release, then try launching again."
        )
        return None
    if not PYTHON3106_CMD and _is_frozen():
        messagebox.showerror("Launch Error", "Python 3.10.6 is required to run the logger. Please install Python 3.10.6 and try again.")
        return None
    try:
        return subprocess.Popen([*python_exe, MAIN_PROGRAM])
    except Exception as e:
        messagebox.showerror("Launch Error", str(e))

        
def threaded_action(
    action: Callable[..., str],
    text_widget: scrolledtext.ScrolledText,
    *,
    silent: bool = False,
    progress_init: Optional[Callable[[int], None]] = None,
    progress_tick: Optional[Callable[[int], None]] = None,
    progress_done: Optional[Callable[[], None]] = None,
) -> None:
    def log_callback(line: str) -> None:
        if silent:
            return
        text_widget.config(state="normal")
        text_widget.insert(tk.END, line)
        text_widget.see(tk.END)
        text_widget.update()
        text_widget.config(state="disabled")

    def run():
        try:
            text_widget.config(state="normal")
            if not silent:
                text_widget.insert(tk.END, f"{action.__name__.replace('_', ' ').title()}...\n")
            text_widget.see(tk.END)
            text_widget.update()
            text_widget.config(state="disabled")
            if action.__name__ == "check_requirements":
                result = action(log_callback if not silent else None, progress_init, progress_tick, progress_done)
                # Show only the summary when silent
                if silent and result:
                    text_widget.config(state="normal")
                    text_widget.insert(tk.END, result + "\n")
                    text_widget.see(tk.END)
                    text_widget.config(state="disabled")
            else:
                result = action()
                text_widget.config(state="normal")
                text_widget.insert(tk.END, result + "\n")
                text_widget.see(tk.END)
                text_widget.config(state="disabled")
        finally:
            text_widget.config(state="disabled")

    t = threading.Thread(target=run, daemon=True)
    t.start()

# NEW: font helpers
def _is_font_available(font_family: str) -> bool:
    try:
        families = set(f.lower() for f in tkfont.families())
        return font_family.lower() in families
    except Exception:
        return False

def _install_font_per_user_windows(font_path: str, font_family: str) -> Tuple[bool, str]:
    if os.name != "nt":
        return False, "Not Windows."
    try:
        local_app = os.environ.get("LOCALAPPDATA")
        if not local_app:
            return False, "LOCALAPPDATA not set."
        user_fonts = os.path.join(local_app, "Microsoft", "Windows", "Fonts")
        os.makedirs(user_fonts, exist_ok=True)
        dest_path = os.path.join(user_fonts, os.path.basename(font_path))
        if os.path.abspath(font_path) != os.path.abspath(dest_path):
            shutil.copy2(font_path, dest_path)

        # Registry entry so Windows enumerates the font for this user
        if not winreg:
            return False, "winreg unavailable."
        key_path = r"Software\Microsoft\Windows NT\CurrentVersion\Fonts"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            value_name = f"{font_family} (TrueType)"
            winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, os.path.basename(dest_path))

        # Load into current session and notify apps
        try:
            AddFontResourceExW = ctypes.windll.gdi32.AddFontResourceExW
            SendMessageTimeoutW = ctypes.windll.user32.SendMessageTimeoutW
            res = AddFontResourceExW(dest_path, 0, 0)
            HWND_BROADCAST = 0xFFFF
            WM_FONTCHANGE = 0x001D
            SMTO_ABORTIFHUNG = 0x0002
            SendMessageTimeoutW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0, SMTO_ABORTIFHUNG, 1000, None)
        except Exception:
            # Non-fatal; font will appear after restart
            pass

        return True, "Installed."
    except Exception as e:
        return False, str(e)

class InstallerGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MLHD2 Launcher")
        self.geometry("1280x720")
        self.resizable(False, False)
        # Discord RPC for launcher
        self._rpc = _LauncherRPC()
        self._rpc.start()

        # Optional: set window icon from LaunchMedia/app.ico if present
        try:
            ico_path = resource_path("LaunchMedia", "app.ico")
            if not os.path.exists(ico_path):
                ico_path = app_path("LaunchMedia", "app.ico")
            if os.path.exists(ico_path):
                # On Windows, Tk expects .ico
                self.iconbitmap(default=ico_path)
        except Exception:
            pass

        # Optional: show a splash screen image if LaunchMedia/splash.png exists
        # Splash will appear centered and close automatically shortly after startup
        self.withdraw()  # hide main window until splash completes
        try:
            splash_path = resource_path("LaunchMedia", "splash.png")
            if not os.path.exists(splash_path):
                splash_path = app_path("LaunchMedia", "splash.png")
            if os.path.exists(splash_path):
                splash = tk.Toplevel()
                splash.overrideredirect(True)
                splash.attributes("-topmost", True)
                try:
                    # Use Tk's PhotoImage (supports PNG with Tk 8.6+)
                    self._splash_img = tk.PhotoImage(file=splash_path)
                except Exception:
                    self._splash_img = None
                w = self._splash_img.width() if self._splash_img else 600
                h = self._splash_img.height() if self._splash_img else 300
                sw = splash.winfo_screenwidth()
                sh = splash.winfo_screenheight()
                x = (sw // 2) - (w // 2)
                y = (sh // 2) - (h // 2)
                splash.geometry(f"{w}x{h}+{x}+{y}")
                if self._splash_img:
                    lbl = tk.Label(splash, image=self._splash_img, borderwidth=0, highlightthickness=0)
                else:
                    lbl = tk.Label(splash, text="MLHD2", font=("Arial", 24, "bold"), bg="#252526", fg="white")
                lbl.pack(fill="both", expand=True)

                # Close splash after delay and show main window
                def _close_splash():
                    try:
                        splash.destroy()
                    except Exception:
                        pass
                    self.deiconify()

                # 1.2s splash; adjust as needed
                self.after(1200, _close_splash)
            else:
                # No splash image; show window immediately
                self.deiconify()
        except Exception:
            # On any error, just show window
            self.deiconify()

        # Try to use Insignia font if available, fallback to Arial
        try:
            insignia_font = tkfont.Font(family="Insignia", size=18, weight="bold", slant="italic")
        except Exception:
            insignia_font = tkfont.Font(family="Arial", size=18, weight="bold", slant="italic")

        # Load placeholder background image with error handling
        try:
            from PIL import Image, ImageTk
        except ImportError:
            messagebox.showerror("Missing Dependency", "Pillow (PIL) is not installed. Please run 'pip install pillow' and restart the launcher.")
            self.bg_photo = None
        else:
            bg_path = resource_path("LaunchMedia", "SpacePlaceholder.png")
            if not os.path.exists(bg_path):
                # try app dir fallback in dev
                bg_path = app_path("LaunchMedia", "SpacePlaceholder.png")
            if not os.path.exists(bg_path):
                messagebox.showerror("Missing Image", f"Background image not found: {bg_path}")
                self.bg_photo = None
            else:
                try:
                    bg_img = Image.open(bg_path)
                    try:
                        resample = Image.Resampling.LANCZOS
                    except AttributeError:
                        resample = Image.ANTIALIAS
                    bg_img = bg_img.resize((1280, 720), resample)
                    self.bg_photo = ImageTk.PhotoImage(bg_img)
                except Exception as e:
                    messagebox.showerror("Image Error", f"Failed to load background image: {e}")
                    self.bg_photo = None

        # Canvas for background
        self.canvas = tk.Canvas(self, width=1280, height=720, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        if self.bg_photo:
            self.canvas.create_image(0, 0, anchor="nw", image=self.bg_photo)
        else:
            self.canvas.create_rectangle(0, 0, 1280, 720, fill="#252526", outline="")

        # Sidebar
        self.sidebar = tk.Frame(self.canvas, bg="#252526", width=80, height=600)
        self.sidebar.place(x=0, y=0)

        # Sidebar button image paths and icons
        sidebar_btn_info = [
            (resource_path("LaunchMedia", "GitHubButton.png"), resource_path("LaunchMedia", "GitHubButtonHover.png"), "🏠"),
            (resource_path("LaunchMedia", "DiscordButton.png"), resource_path("LaunchMedia", "DiscordButtonHover.png"), "📰"),
            (resource_path("LaunchMedia", "SettingsButton.png"), resource_path("LaunchMedia", "SettingsButtonHover.png"), "⚙️"),
            (resource_path("LaunchMedia", "HelpButton.png"), resource_path("LaunchMedia", "HelpButtonHover.png"), "❓"),
        ]
        self.sidebar_buttons = []
        self.sidebar_btn_photos = []
        self.sidebar_btn_hover_photos = []

        # Sidebar button actions
        def open_url(url):
            webbrowser.open(url)

        def open_settings():
            python_exe = _py_cmd()
            settings_path = app_path("settings.py")
            if not os.path.exists(settings_path):
                messagebox.showerror(
                    "Settings Not Found",
                    "Please \"Update to Latest\" before opening Settings."
                )
                return
            try:
                subprocess.Popen([*python_exe, settings_path])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open settings: {e}")

        sidebar_btn_actions = [
            lambda: open_url("https://github.com/HDMLM/MLHD2"),  # GitHub
            lambda: open_url("https://discord.gg/U6ydgwFKZG"),  # Discord (same link as requested)
            open_settings,                                        # Settings
            lambda: open_url("https://github.com/HDMLM/MLHD2/blob/main/README.md"),  # Help
        ]

        for i, (img, hover_img, fallback_icon) in enumerate(sidebar_btn_info):
            try:
                if not os.path.exists(img):
                    img = app_path("LaunchMedia", os.path.basename(img))
                if not os.path.exists(hover_img):
                    hover_img = app_path("LaunchMedia", os.path.basename(hover_img))
                # Pillow compatibility for older versions
                try:
                    resample_algo = Image.Resampling.LANCZOS
                except Exception:
                    resample_algo = Image.ANTIALIAS
                btn_img = Image.open(img).convert("RGBA").resize((40, 40), resample_algo)
                btn_hover_img = Image.open(hover_img).convert("RGBA").resize((40, 40), resample_algo)
                btn_photo = ImageTk.PhotoImage(btn_img)
                btn_hover_photo = ImageTk.PhotoImage(btn_hover_img)
            except Exception:
                btn_photo = None
                btn_hover_photo = None

            btn = tk.Button(
            self.sidebar,
            image=btn_photo if btn_photo else None,
            text=fallback_icon if not btn_photo else "",
            bg="#252526",
            fg="white",
            font=("Arial", 28, "bold"),
            borderwidth=0,
            relief="flat",
            activebackground="#353535",
            highlightthickness=0,
            compound="center",
            command=sidebar_btn_actions[i]
            )
            btn.place(x=20, y=40 + i * 90, width=40, height=40)
            if btn_photo and btn_hover_photo:
                btn.bind("<Enter>", lambda e, b=btn, h=btn_hover_photo: b.config(image=h))
                btn.bind("<Leave>", lambda e, b=btn, n=btn_photo: b.config(image=n))
            self.sidebar_buttons.append(btn)
            self.sidebar_btn_photos.append(btn_photo)
            self.sidebar_btn_hover_photos.append(btn_hover_photo)

        # Banner area
        self.banner_frame = tk.Frame(self.canvas, bg="#252526", width=920, height=110)
        self.banner_frame.place(x=80, y=0)
        self.banner_label = tk.Label(self.banner_frame, text="HD2 MISSION LOGGER", bg="#252526", fg="white", font=(insignia_font.actual("family"), 30))
        self.banner_label.place(x=30, y=18)
        latest_version = get_latest_github_version(include_prerelease=True)

        self.version_label = tk.Label(
            self.banner_frame,
            text=f"Latest Version: {latest_version} - {GameUpdateTitle}" if isinstance(latest_version, str) else "Drop Into Hell...",
            bg="#252526",
            fg="#AEE2FF",
            font=insignia_font
        )
        self.version_label.place(x=30, y=60)


        # Main content area (match height with patch notes)
        self.content_frame = tk.Frame(self.canvas, bg="#4C4C4C", width=400, height=180)
        self.content_frame.place(x=120, y=140)
        self.content_frame.update()
        self.content_frame.config(highlightbackground="#B0BEC5", highlightthickness=2)
        self.shadow = tk.Frame(self.canvas, bg="#252526", width=410, height=170)
        self.shadow.place(x=115, y=135)
        self.content_frame.lift(self.shadow)

        self.text = scrolledtext.ScrolledText(self.content_frame, state="disabled", width=46, height=8, font=("Arial", 12), relief="flat", bd=0, bg="#4C4C4C", fg="white", wrap="word")
        self.text.place(x=10, y=10)

        # Progress bar for silent operations (e.g., Check Requirements)
        self.progress_label = tk.Label(self.content_frame, text="", bg="#4C4C4C", fg="white", font=("Arial", 10))
        # ttk.Progressbar only supports color styling, not images so screw that plan i had of using a hazzard tape progress bar :(
        style = ttk.Style(self)
        style.theme_use('default')
        style.configure(
            "YellowBlack.Horizontal.TProgressbar",
            troughcolor="#252526",  # black/dark trough
            background="#FFD600",   # yellow bar
            bordercolor="#252526",
            lightcolor="#FFD600",
            darkcolor="#FFD600"
        )
        # Use maximum=1000 for finer granularity (smoother animation)
        self.progress = ttk.Progressbar(
            self.content_frame,
            orient="horizontal",
            mode="determinate",
            length=360,
            style="YellowBlack.Horizontal.TProgressbar",
            maximum=1000
        )
        # Initially hidden; will be placed during operations

        # Patch notes box
        # Match size with the main log text box
        self.patch_notes_frame = tk.Frame(self.canvas, bg="#4C4C4C", width=400, height=250)
        # Place directly below the log box, keeping ~10px gap
        self.patch_notes_frame.place(x=120, y=340)
        self.patch_notes_frame.config(highlightbackground="#252526", highlightthickness=2)
        self.patch_notes_box = scrolledtext.ScrolledText(self.patch_notes_frame, state="disabled", width=46, height=15, font=("Arial", 11, "italic"), relief="flat", bd=0, bg="#4C4C4C", fg="white", wrap="word")
        self.patch_notes_box.place(x=10, y=10)

        # Button row

        button_y = 670
        button_x_start = 40
        button_w = 160
        button_h = 38
        button_pad = 20
        # Button image loading helper
        def load_button_images(base_path, normal_name, hover_name, size):
            try:
                npath = resource_path(base_path, normal_name)
                hpath = resource_path(base_path, hover_name)
                if not os.path.exists(npath):
                    npath = app_path(base_path, normal_name)
                if not os.path.exists(hpath):
                    hpath = app_path(base_path, hover_name)
                try:
                    resample_algo = Image.Resampling.LANCZOS
                except Exception:
                    resample_algo = Image.ANTIALIAS
                normal_img = Image.open(npath).convert("RGBA")
                hover_img = Image.open(hpath).convert("RGBA")
                normal_img = normal_img.resize(size, resample_algo)
                hover_img = hover_img.resize(size, resample_algo)
                return ImageTk.PhotoImage(normal_img), ImageTk.PhotoImage(hover_img)
            except Exception:
                return None, None

        button_h_tall = 60
        button_w_wide = button_w + 30
        button_img_size = (button_w_wide, button_h_tall)
        button_img_pad = 30  # Padding between buttons
        button_bottom_pad = 30  # Padding from bottom (increased spacing below patch notes)

        # Calculate new y position with bottom padding
        button_y_padded = button_y - button_bottom_pad

        # Verify button images
        self.verify_photo, self.verify_photo_hover = load_button_images(
            "LaunchMedia", "VerifyIntegrityButton.png", "VerifyIntegrityButtonHover.png", button_img_size
        )
        self.check_btn = tk.Button(
            self.canvas,
            image=self.verify_photo if self.verify_photo else None,
            text="" if self.verify_photo else "Check Requirements",
            bg="#4C4C4C",
            fg="white",
            font=("Arial", 12),
            command=self._action_check_requirements,
            borderwidth=0,
            compound="center",
            highlightthickness=0,
            activebackground="#4C4C4C"
        )
        self.check_btn.place(x=button_x_start, y=button_y_padded, width=button_w_wide, height=button_h_tall)

        if self.verify_photo and self.verify_photo_hover:
            self.check_btn.bind("<Enter>", lambda e: self.check_btn.config(image=self.verify_photo_hover))
            self.check_btn.bind("<Leave>", lambda e: self.check_btn.config(image=self.verify_photo))

        # Update button images
        self.update_photo, self.update_photo_hover = load_button_images(
            "LaunchMedia", "UpdateToLatestButton.png", "UpdateToLatestButtonHover.png", button_img_size
        )
        update_x = button_x_start + button_w_wide + button_img_pad
        self.update_btn = tk.Button(
            self.canvas,
            image=self.update_photo if self.update_photo else None,
            text="" if self.update_photo else "Update to Latest",
            bg="#4C4C4C",
            fg="white",
            font=("Arial", 12),
            command=self._action_update_latest,
            borderwidth=0,
            compound="center",
            highlightthickness=0,
            activebackground="#4C4C4C"
        )
        self.update_btn.place(x=update_x, y=button_y_padded, width=button_w_wide, height=button_h_tall)

        if self.update_photo and self.update_photo_hover:
            self.update_btn.bind("<Enter>", lambda e: self.update_btn.config(image=self.update_photo_hover))
            self.update_btn.bind("<Leave>", lambda e: self.update_btn.config(image=self.update_photo))

    # Always include pre-releases by default, originally a checkbox but im too lazy to refactor the code to remove it so we just set it true
        self.include_prerelease = tk.BooleanVar(value=True)

    # Place Start Game button at the absolute bottom right using image button
        start_btn_img_path = resource_path("LaunchMedia", "StartLoggerButton.png")
        start_btn_hover_img_path = resource_path("LaunchMedia", "StartLoggerButtonHover.png")
        start_btn_clicked_img_path = resource_path("LaunchMedia", "StartLoggerButtonActive.png")
        if not os.path.exists(start_btn_img_path):
            start_btn_img_path = app_path("LaunchMedia", "StartLoggerButton.png")
        if not os.path.exists(start_btn_hover_img_path):
            start_btn_hover_img_path = app_path("LaunchMedia", "StartLoggerButtonHover.png")
        if not os.path.exists(start_btn_clicked_img_path):
            start_btn_clicked_img_path = app_path("LaunchMedia", "StartLoggerButtonActive.png")
        btn_width = 200
        btn_height = 65  # Increased height from 55 to 65
        try:
            try:
                resample_algo = Image.Resampling.LANCZOS
            except Exception:
                resample_algo = Image.ANTIALIAS
            start_btn_img = Image.open(start_btn_img_path).convert("RGBA").resize((btn_width, btn_height), resample_algo)
            start_btn_hover_img = Image.open(start_btn_hover_img_path).convert("RGBA").resize((btn_width, btn_height), resample_algo)
            start_btn_clicked_img = Image.open(start_btn_clicked_img_path).convert("RGBA").resize((btn_width, btn_height), resample_algo)
            self.start_btn_photo = ImageTk.PhotoImage(start_btn_img)
            self.start_btn_hover_photo = ImageTk.PhotoImage(start_btn_hover_img)
            self.start_btn_clicked_photo = ImageTk.PhotoImage(start_btn_clicked_img)
        except Exception:
            self.start_btn_photo = None
            self.start_btn_hover_photo = None
            self.start_btn_clicked_photo = None

        self.launch_btn = tk.Button(
            self.canvas,
            image=self.start_btn_photo if self.start_btn_photo else None,
            text="" if self.start_btn_photo else "▶ Launch Logger",
            bg="#FFD600",
            fg="black",
            font=("Arial", 18, "bold"),
            command=self._action_launch,
            borderwidth=0,
            relief="flat",
            activebackground="#FFEA70",
            width=25
        )
        self.launch_btn.place(x=1060, y=630, width=btn_width, height=btn_height)

        # State management for normal, hover, and clicked
        def set_normal(e=None):
            if self.start_btn_photo:
                self.launch_btn.config(image=self.start_btn_photo)

        def set_hover(e=None):
            if self.start_btn_hover_photo:
                self.launch_btn.config(image=self.start_btn_hover_photo)

        def set_clicked(e=None):
            if self.start_btn_clicked_photo:
                self.launch_btn.config(image=self.start_btn_clicked_photo)

        if self.start_btn_photo and self.start_btn_hover_photo and self.start_btn_clicked_photo:
            self.launch_btn.bind("<Enter>", set_hover)
            self.launch_btn.bind("<Leave>", set_normal)
            self.launch_btn.bind("<ButtonPress-1>", set_clicked)
            self.launch_btn.bind("<ButtonRelease-1>", set_hover)
        elif self.start_btn_photo and self.start_btn_hover_photo:
            self.launch_btn.bind("<Enter>", set_hover)
            self.launch_btn.bind("<Leave>", set_normal)

    # Initial display
        self.display_version_info()

        # NEW: prompt once on first launch to install Insignia.ttf
        self.after(200, self.maybe_prompt_font_install)

    # Button actions with RPC status updates
    def _action_check_requirements(self) -> None:
        try:
            self._rpc.set_status("Checking Requirements", "pip dependencies")
        except Exception:
            pass
        def run():
            threaded_action(
                check_requirements,
                self.text,
                silent=True,
                progress_init=self._progress_init,
                progress_tick=self._progress_tick,
                progress_done=self._progress_done,
            )
            try:
                self._rpc.set_status("Idle", "Ready")
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    def _action_update_latest(self) -> None:
        try:
            self._rpc.set_status("Updating", "Fetching latest release")
        except Exception:
            pass
        def _update():
            threaded_action(lambda: safe_zip_update(self.include_prerelease.get()), self.text)
            try:
                self._rpc.set_status("Idle", "Ready")
            except Exception:
                pass
        threading.Thread(target=_update, daemon=True).start()

    def _action_launch(self) -> None:
        try:
            self._rpc.set_status("Launching Logger", "Starting main app")
        except Exception:
            pass
        self.launch_and_monitor()

    # NEW: first-launch font prompt
    def maybe_prompt_font_install(self) -> None:
        try:
            if os.path.exists(FIRST_LAUNCH_MARKER):
                return

            # Only relevant on Windows
            if os.name != "nt":
                with open(FIRST_LAUNCH_MARKER, "w", encoding="utf-8") as _:
                    _.write("ok")
                return

            if _is_font_available(FONT_FAMILY_NAME):
                with open(FIRST_LAUNCH_MARKER, "w", encoding="utf-8") as _:
                    _.write("ok")
                return

            # Prefer font from LaunchMedia; fall back to app or root if present
            candidates = [
                resource_path("LaunchMedia", FONT_FILE_NAME),
                app_path("LaunchMedia", FONT_FILE_NAME),
                resource_path(FONT_FILE_NAME),
                app_path(FONT_FILE_NAME),
            ]
            font_path = next((p for p in candidates if os.path.exists(p)), "")

            if not font_path:
                if messagebox.askyesno(
                    "Optional Font",
                    f"The '{FONT_FAMILY_NAME}' font improves visuals.\n"
                    f"The font file '{FONT_FILE_NAME}' was not found.\nOpen the app folder to install it manually?"
                ):
                    try:
                        os.startfile(str(APP_DIR))
                    except Exception:
                        pass
                with open(FIRST_LAUNCH_MARKER, "w", encoding="utf-8") as _:
                    _.write("asked")
                return

            if messagebox.askyesno(
                "Install Font",
                f"The '{FONT_FAMILY_NAME}' font is recommended.\nInstall it now for this Windows user?"
            ):
                ok, err = _install_font_per_user_windows(font_path, FONT_FAMILY_NAME)
                if ok:
                    messagebox.showinfo(
                        "Font Installed",
                        f"'{FONT_FAMILY_NAME}' installed.\nYou may need to restart the launcher to see it."
                    )
                else:
                    messagebox.showerror(
                        "Font Install Failed",
                        f"Automatic install failed:\n{err}\nOpening the font file; click 'Install' in the viewer."
                    )
                    try:
                        os.startfile(font_path)  # Opens font viewer for manual install
                    except Exception:
                        pass

            with open(FIRST_LAUNCH_MARKER, "w", encoding="utf-8") as _:
                _.write("asked")
        except Exception:
            try:
                with open(FIRST_LAUNCH_MARKER, "w", encoding="utf-8") as _:
                    _.write("asked")
            except Exception:
                pass

    def display_version_info(self) -> None:
        info = check_version(include_prerelease=self.include_prerelease.get())
        if "Patch Notes:" in info:
            main_info, notes = info.split("Patch Notes:", 1)
        else:
            main_info, notes = info, "No patch notes found."
        self.text.config(state="normal")
        self.text.delete(1.0, tk.END)
        self.text.insert(tk.END, main_info.strip() + "\n")
        self.text.config(state="disabled")
        self.patch_notes_box.config(state="normal")
        self.patch_notes_box.delete(1.0, tk.END)
        self.patch_notes_box.insert(tk.END, notes.strip())
        self.patch_notes_box.config(state="disabled")

    # Launch / monitor logic
    def launch_and_monitor(self) -> None:
        # Hide launcher while main program runs; restore on exit
        if getattr(self, '_proc', None) and self._proc.poll() is None:
            messagebox.showinfo("Already Running", "Main program is already running.")
            return
        self.launch_btn.config(state='disabled')
        proc = launch_program_detached()
        if not proc:
            self.launch_btn.config(state='normal')
            return
        self._proc = proc
        self.withdraw()
        try:
            self._rpc.close()  # Stop RPC when hidden
        except Exception:
            pass

        def monitor():
            exit_code = proc.wait()
            # Return to main thread for UI restore
            def restore():
                self.deiconify()
                self.launch_btn.config(state='normal')
                self.text.config(state='normal')
                self.text.config(state='disabled')
                try:
                    self._rpc.start()  # Restart RPC when re-shown
                    self._rpc.set_status("Idle", "Ready")
                except Exception:
                    pass
            try:
                self.after(0, restore)
            except Exception:
                pass

        threading.Thread(target=monitor, daemon=True).start()

        def monitor():
            exit_code = proc.wait()
            # Return to main thread for UI restore
            def restore():
                self.deiconify()
                self.launch_btn.config(state='normal')
                self.text.config(state='normal')
                self.text.config(state='disabled')
                try:
                    self._rpc.set_status("Idle", "Ready")
                except Exception:
                    pass
            try:
                self.after(0, restore)
            except Exception:
                pass

        threading.Thread(target=monitor, daemon=True).start()

    # Progress helpers for Check Requirements
    def _progress_init(self, total: int) -> None:
        try:
            # Show label and progress bar
            self.progress_label.config(text=f"Verified 0/{total} Python packages…")
            self.progress_label.place(x=20, y=125)
            self.progress.config(maximum=max(1, total), value=0)
            self.progress.place(x=20, y=145)
            self.progress.update()
            self._progress_total = total  # Store total for updates
        except Exception:
            pass

    def _progress_tick(self, step: int = 1) -> None:
        try:
            current = self.progress["value"] + (step or 1)
            total = getattr(self, "_progress_total", self.progress["maximum"])
            self.progress.config(value=current)
            self.progress_label.config(text=f"Verifying {int(current)}/{int(total)} Python packages…")
            self.progress.update()
        except Exception:
            pass

    def _progress_done(self) -> None:
        try:
            # Hide after a brief moment
            self.after(500, lambda: (self.progress.place_forget(), self.progress_label.place_forget()))
        except Exception:
            pass

if __name__ == "__main__":
    app = InstallerGUI()
    app.mainloop()