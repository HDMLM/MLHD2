# installer_pyqt_full.py
# Full conversion of installer.py from Tkinter -> PyQt5 with hover-image swapping and QSS.
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

# Manual constants
GameUpdateTitle = "INTO THE UNJUST"

# Font / Windows registry helpers
import ctypes
try:
    import winreg
except Exception:
    winreg = None

# Keep logic-level dependencies
import requests

# PyQt5 imports
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QSize
from PyQt5.QtGui import QPixmap, QFont, QIcon, QFontDatabase, QColor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QProgressBar, QTextEdit, QMessageBox, QSplashScreen, QFrame, QSizePolicy, QGraphicsDropShadowEffect
)

# Pillow for some image handling (optional)
try:
    from PIL import Image
except Exception:
    Image = None

# ----------------- Paths & bootstrap -----------------
def _is_frozen() -> bool:
    return getattr(sys, "frozen", False) is True

APP_DIR = Path(os.path.dirname(sys.executable) if _is_frozen() else os.path.dirname(__file__)).resolve()
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR)).resolve()

def app_path(*parts: str) -> str:
    return str(APP_DIR.joinpath(*parts))

def resource_path(*parts: str) -> str:
    return str(BUNDLE_DIR.joinpath(*parts))

# Config (Discord client id fallback)
_config = configparser.ConfigParser()
try:
    _config.read(app_path("config.config"))
    DISCORD_CLIENT_ID = _config.get('Discord', 'DISCORD_CLIENT_ID', fallback='0')
except Exception:
    DISCORD_CLIENT_ID = '0'

# Python version enforcement (original logic)
REQUIRED_PYTHON_VERSION = (3, 10, 6)

def find_python3106_executable() -> Optional[List[str]]:
    candidates: List[List[str]] = []
    if not _is_frozen():
        candidates.append([sys.executable])
    candidates.extend([
        ["python3.10"],
        ["python3.10.6"],
        ["py", "-3.10"],
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
    if _is_frozen():
        return
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

# ----------------- GitHub/update helpers -----------------
GITHUB_API_REPO = "HDMLM/MLHD2"
GITHUB_REPO = "https://github.com/HDMLM/MLHD2"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_API_REPO}"
REQUIREMENTS_FILE = app_path("requirements.txt")
MAIN_PROGRAM = app_path("main.py")
BACKUP_DIR_ROOT = app_path("backup")

REQUEST_TIMEOUT_RELEASES = 10
REQUEST_TIMEOUT_ZIP = 30

FONT_FAMILY_NAME = "Insignia"
FONT_FILE_NAME = "Insignia.ttf"
FIRST_LAUNCH_MARKER = app_path(".first_launch_done")

# ----------------- Discord RPC helper (unchanged) -----------------
try:
    import discordrpc
except Exception:
    discordrpc = None

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
                self.set_status("Launcher Open")
            except Exception:
                self.RPC = None
                self._started = False
        threading.Thread(target=_init, daemon=True).start()

    def set_status(self, status: str, details: Optional[str] = None) -> None:
        if not self.RPC:
            return
        try:
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
                large_image="test",
                large_text="MLHD2",
                small_image="obs",
                small_text="Launcher",
                act_type=3,
                **({"buttons": buttons} if buttons else {})
            )
        except Exception:
            pass

    def close(self) -> None:
        try:
            if self.RPC and hasattr(self.RPC, 'close'):
                self.RPC.close()
        except Exception:
            pass

# ----------------- Exclusion & validation -----------------
EXCLUDE_PATH_PREFIXES = (
    "JSON/persistent",
    "JSON/settings",
    "JSON/streak_data",
    "backup",
    ".git",
    "venv",
    "mission_log.xlsx",
    "DCord.json",
)

def _is_excluded(rel_path: str) -> bool:
    normalized = rel_path.replace("\\", "/").lstrip("./")
    return any(normalized.startswith(pref) for pref in EXCLUDE_PATH_PREFIXES)

def _validate_files_against_fstruct() -> Tuple[int, int, int, List[str], List[str]]:
    try:
        import json
        candidates = [
            resource_path("LaunchMedia", "FStruct.json"),
            app_path("LaunchMedia", "FStruct.json"),
            app_path("FStruct.json"),
        ]
        fstruct_path = next((p for p in candidates if os.path.exists(p)), "")
        if not fstruct_path:
            return -1, 0, 0, [], []

        with open(fstruct_path, "r", encoding="utf-8") as f:
            spec = json.load(f)

        required: List[Tuple[str, str]] = []
        optional: List[Tuple[str, str]] = []

        def is_optional(node_type: str, name: str, rel_path: str) -> bool:
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
        return -1, 0, 0, [], []

# ----------------- Version parsing & GitHub -----------------
_VERSION_REGEX = re.compile(r'^\s*VERSION\s*=\s*["\']([^"\']+)["\']')

def get_local_version() -> Optional[str]:
    try:
        with open(MAIN_PROGRAM, "r", encoding="utf-8") as f:
            for line in f:
                m = _VERSION_REGEX.match(line)
                if m:
                    return m.group(1).strip()
    except FileNotFoundError:
        return None
    except Exception as e:
        return f"__ERROR__:{e}"
    return None

def _github_headers() -> Dict[str, str]:
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def _github_get(path: str, timeout: int = REQUEST_TIMEOUT_RELEASES) -> Optional[Any]:
    url = f"{GITHUB_API_BASE}/{path.lstrip('/')}"
    try:
        r = requests.get(url, headers=_github_headers(), timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def fetch_releases() -> List[Dict[str, Any]]:
    data = _github_get("releases")
    if not isinstance(data, list):
        return []
    return [r for r in data if not r.get("draft")]

def pick_latest_release(include_prerelease: bool) -> Optional[Dict[str, Any]]:
    releases = fetch_releases()
    if not releases:
        return None
    if include_prerelease:
        return releases[0]
    return next((r for r in releases if not r.get("prerelease")), None)

def download_release_zip(include_prerelease: bool) -> Tuple[Optional[str], Optional[bytes], str]:
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
    local_version = get_local_version()
    latest = get_latest_github_version(include_prerelease=include_prerelease)
    if not isinstance(latest, str):
        return f"Could not determine GitHub version: {latest}"
    if local_version and not local_version.startswith("__ERROR__:"):
        cmp_result = _compare_versions(local_version, latest)
        if cmp_result > 0:
            return "Local version is ahead of GitHub release (development build). No update applied."

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
            members = z.namelist()
            if not members:
                return "Safe update failed: archive empty"
            top = members[0].split('/')[0]
            for member in members:
                if member.endswith('/'):
                    continue
                parts = member.split('/')
                if parts[0] != top:
                    rel_path = member
                else:
                    rel_path = '/'.join(parts[1:])
                if not rel_path:
                    continue
                if _is_excluded(rel_path):
                    excluded += 1
                    continue
                dest_path = os.path.join(str(APP_DIR), rel_path.replace('/', os.sep))
                dest_dir = os.path.dirname(dest_path)
                try:
                    os.makedirs(dest_dir, exist_ok=True)
                    data = z.read(member)
                    if os.path.exists(dest_path):
                        try:
                            with open(dest_path, 'rb') as existing:
                                if existing.read() == data:
                                    skipped += 1
                                    continue
                        except Exception:
                            pass
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
    while parts and parts[-1] == 0:
        parts.pop()
    return parts

def _compare_versions(a: str, b: str) -> int:
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
    return re.sub(r'[-_.]+', '-', name).lower()

# ----------------- requirements & check_version (unchanged) -----------------
def check_version(include_prerelease: bool = False) -> str:
    raw_local = get_local_version()
    latest = get_latest_github_version(full=True, include_prerelease=include_prerelease)
    if not isinstance(latest, dict):
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
    output: List[str] = []
    progress_initialized = False

    def log(line: str) -> None:
        import textwrap
        wrapped = textwrap.fill(line, width=80)
        output.append(wrapped)
        if log_callback:
            log_callback(wrapped + "\n")

    def read_requirements_lines(path: str) -> List[str]:
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
        python_exe = _py_cmd()
        try:
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
        python_exe = _py_cmd()
        spec = f"{pkg}=={target}" if target else pkg
        DEBUG_MODE = bool(sys.gettrace()) or os.environ.get("MLHD2_DEBUG_PIP")
        try:
            cmd = [*python_exe, "-m", "pip", "install", spec, "--disable-pip-version-check", "--no-input"]
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

    MGMT_PACKAGES = {"pip", "setuptools", "wheel"}
    failures: List[str] = []
    updated_count = 0
    installed_count = 0

    try:
        if _is_frozen() and not PYTHON3106_CMD:
            log("Python 3.10.6 not found. Cannot verify or install requirements from the bundled launcher.")
            log("Please install Python 3.10.6 and run 'Check Requirements' again, or run 'pip install -r requirements.txt' manually.")
            return "Summary: Skipped (Python 3.10.6 missing)"
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

        parsed_reqs: List[Tuple[str, Optional[str]]] = []
        for req in requirements:
            if '==' in req:
                pkg, pinned_version = req.split('==', 1)
                parsed_reqs.append((pkg.strip(), pinned_version.strip()))
            else:
                parsed_reqs.append((req.strip(), None))

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
            installed = get_installed_packages()
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

    try:
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
                for p in miss_opt_list[:10]:
                    log(f"  - missing optional: {p}")
            else:
                log(f"Files: {miss_req} missing required file(s). Optional missing: {miss_opt}")
                for p in miss_req_list[:15]:
                    log(f"  - MISSING: {p}")
                for p in miss_opt_list[:5]:
                    log(f"  - missing optional: {p}")
    except Exception as e:
        log(f"Files: Validation error: {e}")
    finally:
        if progress_tick:
            try:
                progress_tick(1)
            except Exception:
                pass
        if progress_done:
            try:
                progress_done()
            except Exception:
                pass

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

    summary_lines = []
    for line in output:
        if (
            line.startswith("Summary:")
            or line.startswith("Actions:")
            or line.startswith("Error reading requirements:")
            or line.startswith("Files:")
        ):
            summary_lines.append(line)
        elif line.strip().startswith("- MISSING:") or line.strip().startswith("- missing optional:"):
            summary_lines.append(line)
    return "\n".join(summary_lines) if summary_lines else "\n".join(output[-10:])

# ----------------- GUI helper wrappers -----------------
def gui_error(title: str, message: str) -> None:
    try:
        QMessageBox.critical(None, title, message)
    except Exception:
        print(f"ERROR - {title}: {message}", file=sys.stderr)

def gui_info(title: str, message: str) -> None:
    try:
        QMessageBox.information(None, title, message)
    except Exception:
        print(f"INFO - {title}: {message}")

def launch_program_detached() -> Optional[subprocess.Popen]:
    python_exe = _py_cmd()
    if not os.path.exists(MAIN_PROGRAM):
        gui_error(
            "Not Installed",
            "The main program is not installed yet.\n"
            "Click 'Update to Latest' to download the latest release, then try launching again."
        )
        return None
    if not PYTHON3106_CMD and _is_frozen():
        gui_error("Launch Error", "Python 3.10.6 is required to run the logger. Please install Python 3.10.6 and try again.")
        return None
    try:
        return subprocess.Popen([*python_exe, MAIN_PROGRAM])
    except Exception as e:
        gui_error("Launch Error", str(e))
        return None

# ----------------- Stylesheet & image loader & HoverButton -----------------
def load_stylesheet() -> str:
    candidates = [
        resource_path("LaunchMedia", "styles.qss"),
        app_path("LaunchMedia", "styles.qss"),
        resource_path("styles.qss"),
        app_path("styles.qss"),
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                with open(c, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                logging.warning(f"Failed to read QSS: {e}")
    # fallback QSS
    return """
QMainWindow { background-color: #252526; color: white; }
QLabel { color: white; }
QTextEdit { background-color: #4C4C4C; color: white; border: 2px solid #B0BEC5; }
QPushButton { background-color: #4C4C4C; color: white; border: none; padding: 6px; border-radius: 6px; }
QPushButton:hover { background-color: #5C5C5C; }
QProgressBar { border: 1px solid #252526; background: #252526; height: 16px; }
QProgressBar::chunk { background-color: #FFD600; }
"""

def load_pixmap(*path_parts: str) -> Optional[QPixmap]:
    candidates = [
        resource_path(*path_parts),
        app_path(*path_parts),
        os.path.join(*path_parts)
    ]
    for p in candidates:
        if p and os.path.exists(p):
            pix = QPixmap(p)
            if not pix.isNull():
                return pix
    logging.warning(f"Missing image: {'/'.join(path_parts)}")
    return None

class HoverButton(QPushButton):
    """
    QPushButton with optional normal and hover QPixmaps. Automatically swaps icons on enter/leave.
    """
    def __init__(self, normal_pix: Optional[QPixmap], hover_pix: Optional[QPixmap], fallback_text: str = "", parent=None, icon_size: Tuple[int,int]=(40,40)):
        super().__init__(parent)
        self.normal_icon = QIcon(normal_pix) if normal_pix else None
        self.hover_icon = QIcon(hover_pix) if hover_pix else None
        self.icon_size = QSize(*icon_size)
        if self.normal_icon:
            self.setIcon(self.normal_icon)
            self.setIconSize(self.icon_size)
        if fallback_text and not self.normal_icon:
            self.setText(fallback_text)
        self.setCursor(Qt.PointingHandCursor)
        # No default border background: style applied by stylesheet

    def enterEvent(self, e):
        if self.hover_icon:
            self.setIcon(self.hover_icon)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if self.normal_icon:
            self.setIcon(self.normal_icon)
        super().leaveEvent(e)

# ----------------- Font helpers (Qt-based) -----------------
def _is_font_available(font_family: str) -> bool:
    try:
        families = set(f.lower() for f in QFontDatabase().families())
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

        if not winreg:
            return False, "winreg unavailable."
        key_path = r"Software\Microsoft\Windows NT\CurrentVersion\Fonts"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            value_name = f"{font_family} (TrueType)"
            winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, os.path.basename(dest_path))

        try:
            AddFontResourceExW = ctypes.windll.gdi32.AddFontResourceExW
            SendMessageTimeoutW = ctypes.windll.user32.SendMessageTimeoutW
            res = AddFontResourceExW(dest_path, 0, 0)
            HWND_BROADCAST = 0xFFFF
            WM_FONTCHANGE = 0x001D
            SMTO_ABORTIFHUNG = 0x0002
            SendMessageTimeoutW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0, SMTO_ABORTIFHUNG, 1000, None)
        except Exception:
            pass

        return True, "Installed."
    except Exception as e:
        return False, str(e)

# ----------------- Signals for UI updates -----------------
class UISignals(QObject):
    append_text = pyqtSignal(str)
    progress_init = pyqtSignal(int)
    progress_tick = pyqtSignal(int)
    progress_done = pyqtSignal()
    set_version_text = pyqtSignal(str)
    set_patch_notes = pyqtSignal(str)
    set_progress_visible = pyqtSignal(bool)

# ----------------- InstallerWindow (PyQt5) -----------------
class InstallerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MLHD2 Launcher")
        self.setFixedSize(1280, 720)
        self._content_width = 1100  # approximate visual width of content area in screenshot
        self._rpc = _LauncherRPC()
        self._rpc.start()
        self.signals = UISignals()
        self.include_prerelease = True  # default like original

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Background image (like Tk canvas background in installer.py)
        # Tries LaunchMedia/SpacePlaceholder.png and scales it with the window.
        self._bg_pixmap: Optional[QPixmap] = load_pixmap("LaunchMedia", "SpacePlaceholder.png")
        self.bg_label = QLabel(central)
        self.bg_label.setObjectName("bg_label")
        self.bg_label.setScaledContents(False)  # we'll scale manually for better quality
        self.bg_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.bg_label.lower()  # ensure it's behind other widgets
        self._update_background()

        # Sidebar (using HoverButton with icons)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(72)
        self.sidebar.setStyleSheet(
            "QFrame#sidebar { background-color: #252526; border-right: 1px solid #3a3a3a; }"
        )
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 16, 0, 16)
        sidebar_layout.setSpacing(24)

        sidebar_btn_info = [
            ("GitHubButton.png", "GitHubButtonHover.png", "🏠", "https://github.com/HDMLM/MLHD2"),
            ("DiscordButton.png", "DiscordButtonHover.png", "📰", "https://discord.gg/U6ydgwFKZG"),
            ("SettingsButton.png", "SettingsButtonHover.png", "⚙️", "settings"),
            ("HelpButton.png", "HelpButtonHover.png", "❓", "https://github.com/HDMLM/MLHD2/blob/main/README.md"),
        ]

        self.sidebar_buttons = []
        for normal, hover, fallback, action in sidebar_btn_info:
            pix_n = load_pixmap("LaunchMedia", normal)
            pix_h = load_pixmap("LaunchMedia", hover)
            btn = HoverButton(pix_n, pix_h, fallback, parent=self, icon_size=(44,44))
            btn.setFixedSize(56, 56)
            btn.setStyleSheet("background: transparent; border: none;")
            btn.setFocusPolicy(Qt.NoFocus)
            if action == "settings":
                btn.clicked.connect(self.open_settings)
            else:
                url = action
                btn.clicked.connect(lambda _, u=url: webbrowser.open(u))
            sidebar_layout.addWidget(btn, alignment=Qt.AlignHCenter | Qt.AlignTop)
            self.sidebar_buttons.append(btn)

        # Right/main area
        banner_frame = QFrame()
        # Translucent banner bar across the top, like the Tk version overlay
        banner_frame.setStyleSheet("background-color: rgba(33,33,33,200); color: white;")
        banner_frame.setFixedHeight(90)
        banner_frame.setMaximumWidth(self._content_width)
        banner_layout = QVBoxLayout(banner_frame)
        banner_layout.setContentsMargins(20, 10, 10, 10)

        self.banner_label = QLabel("HD2 MISSION LOGGER")
        # Title typography (uppercase, slightly increased letter spacing)
        title_font = QFont(FONT_FAMILY_NAME if _is_font_available(FONT_FAMILY_NAME) else "Arial", 30)
        try:
            title_font.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
            title_font.setBold(True)
        except Exception:
            pass
        self.banner_label.setFont(title_font)
        self.banner_label.setStyleSheet("color: white;")
        banner_layout.addWidget(self.banner_label, alignment=Qt.AlignLeft)

        latest_version = get_latest_github_version(include_prerelease=True)
        version_text = f"Latest Version: {latest_version} - {GameUpdateTitle}" if isinstance(latest_version, str) else "Drop Into Hell..."
        self.version_label = QLabel(version_text)
        self.version_label.setStyleSheet("color: #AEE2FF; font-style: italic;")
        banner_layout.addWidget(self.version_label, alignment=Qt.AlignLeft)

    # Subtle drop shadow under banner
        banner_shadow = QGraphicsDropShadowEffect(banner_frame)
        banner_shadow.setBlurRadius(24)
        banner_shadow.setOffset(0, 6)
        banner_shadow.setColor(QColor(0, 0, 0, 160))
        banner_frame.setGraphicsEffect(banner_shadow)

        # Log and patch notes (framed panels with drop shadows)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setStyleSheet("background-color: transparent; color: white; border: none;")
        self.text.setFixedHeight(180)

        self.patch_notes_box = QTextEdit()
        self.patch_notes_box.setReadOnly(True)
        self.patch_notes_box.setStyleSheet("background-color: transparent; color: white; border: none;")
        self.patch_notes_box.setFixedHeight(250)

        def make_panel(child_widget: QWidget, border_color: str = "#B0BEC5") -> QFrame:
            frame = QFrame()
            # Double-border look: outer darker border using shadow + inner light border
            frame.setStyleSheet(
                f"QFrame {{ background-color: #4C4C4C; border: 2px solid {border_color}; }}"
            )
            lay = QVBoxLayout(frame)
            lay.setContentsMargins(12, 12, 12, 12)
            lay.addWidget(child_widget)
            # Add drop shadow effect
            shadow = QGraphicsDropShadowEffect(frame)
            shadow.setBlurRadius(24)
            shadow.setOffset(6, 6)
            shadow.setColor(QColor(0, 0, 0, 160))
            frame.setGraphicsEffect(shadow)
            frame.setMaximumWidth(self._content_width)
            return frame

        self.version_frame = make_panel(self.text, border_color="#B0BEC5")
        self.notes_frame = make_panel(self.patch_notes_box, border_color="#252526")

        # Progress controls
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: white; background-color: #4C4C4C;")
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        self.progress_label.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #252526;
                background: #252526;
                height: 16px;
            }
            QProgressBar::chunk {
                background-color: #FFD600;
            }
        """)

        # Bottom image buttons with hover
        def make_image_button(base_name, hover_name, fallback_text, callback, size=(190,60)):
            pix_n = load_pixmap("LaunchMedia", base_name)
            pix_h = load_pixmap("LaunchMedia", hover_name)
            btn = HoverButton(pix_n, pix_h, fallback_text, parent=self, icon_size=(size[0], size[1]))
            btn.setFixedSize(*size)
            btn.setStyleSheet("background-color: transparent; border: none;")
            btn.clicked.connect(callback)
            return btn

        # button sizes chosen to match original visuals (wide/tall buttons)
        button_img_wide = 190
        button_img_tall = 60

        self.check_btn = make_image_button("VerifyIntegrityButton.png", "VerifyIntegrityButtonHover.png",
                                           "Check Requirements", self._action_check_requirements,
                                           size=(button_img_wide, button_img_tall))
        self.update_btn = make_image_button("UpdateToLatestButton.png", "UpdateToLatestButtonHover.png",
                                           "Update to Latest", self._action_update_latest,
                                           size=(button_img_wide, button_img_tall))
        # Start/Launch button uses wider image (200x65) like original
        self.launch_btn = make_image_button("StartLoggerButton.png", "StartLoggerButtonHover.png",
                                           "▶ Launch Logger", self._action_launch,
                                           size=(200, 65))

        # Compose layouts
        left_v = QVBoxLayout()
        left_v.setContentsMargins(12, 8, 12, 12)
        left_v.addWidget(banner_frame, alignment=Qt.AlignLeft)
        left_v.addSpacing(4)
        left_v.addWidget(self.version_frame, alignment=Qt.AlignLeft)
        left_v.addWidget(self.notes_frame, alignment=Qt.AlignLeft)
        left_v.addWidget(self.progress_label)
        left_v.addWidget(self.progress)

        bottom_h = QHBoxLayout()
        bottom_h.addWidget(self.check_btn)
        bottom_h.addWidget(self.update_btn)
        bottom_h.addStretch()
        bottom_h.addWidget(self.launch_btn)

        left_v.addLayout(bottom_h)

        root_h = QHBoxLayout(central)
        root_h.setContentsMargins(0, 0, 0, 0)
        root_h.addWidget(self.sidebar)
        root_h.addLayout(left_v)

        # Connect signals
        self.signals.append_text.connect(self._slot_append_text)
        self.signals.progress_init.connect(self._slot_progress_init)
        self.signals.progress_tick.connect(self._slot_progress_tick)
        self.signals.progress_done.connect(self._slot_progress_done)
        self.signals.set_version_text.connect(self._slot_set_version_text)
        self.signals.set_patch_notes.connect(self._slot_set_patch_notes)
        self.signals.set_progress_visible.connect(self._slot_set_progress_visible)

        # Display initial version info
        self.display_version_info()

        # Font prompt on first run (delayed)
        QTimer.singleShot(200, self.maybe_prompt_font_install)

        # Show splash if exists
        splash_path = resource_path("LaunchMedia", "splash.png")
        if not os.path.exists(splash_path):
            splash_path = app_path("LaunchMedia", "splash.png")
        if os.path.exists(splash_path):
            try:
                splash_pix = QPixmap(splash_path)
                splash = QSplashScreen(splash_pix)
                splash.setWindowFlag(Qt.WindowStaysOnTopHint)
                splash.show()
                QTimer.singleShot(1200, splash.close)
            except Exception:
                pass

        # Internal process handle
        self._proc: Optional[subprocess.Popen] = None
        self._progress_total = 1
        # Ensure background renders after layout is applied
        QTimer.singleShot(0, self._update_background)

    def _update_background(self) -> None:
        try:
            if not self._bg_pixmap or self._bg_pixmap.isNull():
                self.bg_label.clear()
                return
            # Scale to cover the central area while keeping aspect ratio
            cw = self.centralWidget().width()
            ch = self.centralWidget().height()
            if cw <= 0 or ch <= 0:
                return
            scaled = self._bg_pixmap.scaled(cw, ch, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.bg_label.setPixmap(scaled)
            self.bg_label.setGeometry(0, 0, cw, ch)
        except Exception:
            # Non-fatal; just skip background if anything goes wrong
            pass

    # ---------- Slots ----------
    def _slot_append_text(self, s: str):
        # append to log safely on main thread
        self.text.moveCursor(self.text.textCursor().End)
        self.text.insertPlainText(s)
        self.text.moveCursor(self.text.textCursor().End)

    def _slot_progress_init(self, total: int):
        self._progress_total = max(1, total)
        self.progress.setMaximum(self._progress_total)
        self.progress.setValue(0)
        self.progress_label.setText(f"Verifying 0/{self._progress_total} Python packages…")
        self.progress_label.setVisible(True)
        self.progress.setVisible(True)

    def _slot_progress_tick(self, step: int):
        try:
            current = self.progress.value() + (step or 1)
            self.progress.setValue(current)
            self.progress_label.setText(f"Verifying {int(current)}/{int(self._progress_total)} Python packages…")
        except Exception:
            pass

    def _slot_progress_done(self):
        QTimer.singleShot(500, lambda: (self.progress.setVisible(False), self.progress_label.setVisible(False)))

    def _slot_set_version_text(self, s: str):
        self.version_label.setText(s)

    def _slot_set_patch_notes(self, s: str):
        self.patch_notes_box.setPlainText(s)

    def _slot_set_progress_visible(self, visible: bool):
        self.progress.setVisible(visible)
        self.progress_label.setVisible(visible)

    # ---------- Actions ----------
    def open_settings(self):
        python_exe = _py_cmd()
        settings_path = app_path("settings.py")
        if not os.path.exists(settings_path):
            gui_error("Settings Not Found", 'Please "Update to Latest" before opening Settings.')
            return
        try:
            subprocess.Popen([*python_exe, settings_path])
        except Exception as e:
            gui_error("Error", f"Could not open settings: {e}")

    def _action_check_requirements(self) -> None:
        try:
            self._rpc.set_status("Checking Requirements", "pip dependencies")
        except Exception:
            pass

        def run():
            def log_cb(line: str):
                self.signals.append_text.emit(line)

            def p_init(total: int):
                self.signals.progress_init.emit(total)

            def p_tick(step: int = 1):
                self.signals.progress_tick.emit(step)

            def p_done():
                self.signals.progress_done.emit()

            result = check_requirements(log_callback=log_cb, progress_init=p_init, progress_tick=p_tick, progress_done=p_done)
            if result:
                self.signals.append_text.emit(result + "\n")
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

        def run():
            # Use safe_zip_update and post summary
            result = safe_zip_update(self.include_prerelease)
            self.signals.append_text.emit(result + "\n")
            try:
                # refresh displayed version info after update attempt
                self.signals.set_version_text.emit(f"Latest Version: {get_latest_github_version(include_prerelease=self.include_prerelease)} - {GameUpdateTitle}")
                self._rpc.set_status("Idle", "Ready")
            except Exception:
                pass

        threading.Thread(target=run, daemon=True).start()

    def _action_launch(self) -> None:
        try:
            self._rpc.set_status("Launching Logger", "Starting main app")
        except Exception:
            pass
        self.launch_and_monitor()

    # ---------- Font prompt ----------
    def maybe_prompt_font_install(self) -> None:
        try:
            if os.path.exists(FIRST_LAUNCH_MARKER):
                return

            if os.name != "nt":
                with open(FIRST_LAUNCH_MARKER, "w", encoding="utf-8") as _:
                    _.write("ok")
                return

            if _is_font_available(FONT_FAMILY_NAME):
                with open(FIRST_LAUNCH_MARKER, "w", encoding="utf-8") as _:
                    _.write("ok")
                return

            candidates = [
                resource_path("LaunchMedia", FONT_FILE_NAME),
                app_path("LaunchMedia", FONT_FILE_NAME),
                resource_path(FONT_FILE_NAME),
                app_path(FONT_FILE_NAME),
            ]
            font_path = next((p for p in candidates if os.path.exists(p)), "")

            if not font_path:
                reply = QMessageBox.question(self, "Optional Font",
                    f"The '{FONT_FAMILY_NAME}' font improves visuals.\n"
                    f"The font file '{FONT_FILE_NAME}' was not found.\nOpen the app folder to install it manually?",
                    QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    try:
                        os.startfile(str(APP_DIR))
                    except Exception:
                        pass
                with open(FIRST_LAUNCH_MARKER, "w", encoding="utf-8") as _:
                    _.write("asked")
                return

            reply = QMessageBox.question(self, "Install Font",
                f"The '{FONT_FAMILY_NAME}' font is recommended.\nInstall it now for this Windows user?",
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                ok, err = _install_font_per_user_windows(font_path, FONT_FAMILY_NAME)
                if ok:
                    QMessageBox.information(self, "Font Installed", f"'{FONT_FAMILY_NAME}' installed.\nYou may need to restart the launcher to see it.")
                else:
                    QMessageBox.critical(self, "Font Install Failed", f"Automatic install failed:\n{err}\nOpening the font file; click 'Install' in the viewer.")
                    try:
                        os.startfile(font_path)
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

    # ---------- Version display ----------
    def display_version_info(self) -> None:
        info = check_version(include_prerelease=self.include_prerelease)
        if "Patch Notes:" in info:
            main_info, notes = info.split("Patch Notes:", 1)
        else:
            main_info, notes = info, "No patch notes found."
        self.text.setPlainText(main_info.strip() + "\n")
        self.patch_notes_box.setPlainText(notes.strip())

    # ---------- Launch & monitor ----------
    def launch_and_monitor(self) -> None:
        if self._proc and self._proc.poll() is None:
            QMessageBox.information(self, "Already Running", "Main program is already running.")
            return
        self.launch_btn.setDisabled(True)
        proc = launch_program_detached()
        if not proc:
            self.launch_btn.setDisabled(False)
            return
        self._proc = proc
        self.hide()
        try:
            self._rpc.close()
        except Exception:
            pass

        def monitor_proc():
            exit_code = proc.wait()
            def restore():
                try:
                    self.show()
                except Exception:
                    pass
                self.launch_btn.setDisabled(False)
                try:
                    self._rpc.start()
                    self._rpc.set_status("Idle", "Ready")
                except Exception:
                    pass
            QTimer.singleShot(0, restore)

        threading.Thread(target=monitor_proc, daemon=True).start()

    # Ensure background scales when the window changes size
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._update_background()

# ----------------- Main -----------------
if __name__ == "__main__":
    # Ensure logging goes somewhere helpful
    logging.basicConfig(level=logging.WARNING)
    app = QApplication(sys.argv)
    # Apply stylesheet (from LaunchMedia/styles.qss if present)
    app.setStyleSheet(load_stylesheet())
    window = InstallerWindow()
    window.show()
    sys.exit(app.exec_())
