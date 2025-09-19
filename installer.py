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
import threading
import time
import zipfile
from typing import Any, Dict, List, Optional, Tuple, Callable

# Python 3.10.6 enforcement and bootstrap
REQUIRED_PYTHON_VERSION = (3, 10, 6)

def find_python3106_executable() -> Optional[str]:
    candidates = [
        sys.executable,
        "python3.10",
        "python3.10.6",
        "py -3.10",
        r"C:\\Python310\\python.exe",
        r"C:\\Python3.10.6\\python.exe",
    ]
    for exe in candidates:
        try:
            out = subprocess.check_output([
                exe, "-c", "import sys; print(sys.version_info[:3])"
            ], stderr=subprocess.DEVNULL)
            ver = eval(out.decode().strip())
            if tuple(ver) == REQUIRED_PYTHON_VERSION:
                return exe
        except Exception:
            continue
    return None

PYTHON3106_EXE = find_python3106_executable()


def ensure_python_version():
    # Thanks to Jesse's testing we know that the version needs to be exactly 3.10.6
    # Since some packages refuse to work, im looking at you Requests...
    if sys.version_info[:3] != REQUIRED_PYTHON_VERSION:
        msg = (
            f"ERROR: This program requires Python {REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]}.{REQUIRED_PYTHON_VERSION[2]}.\n"
            f"Current version: {sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}\n"
        )
        if not PYTHON3106_EXE:
            msg += "Python 3.10.6 not found. Please install it and re-run this installer."
            print(msg)
            sys.exit(1)
        else:
            msg += f"Attempting to use Python 3.10.6 at: {PYTHON3106_EXE}\n"
            print(msg)
ensure_python_version()

import requests
import tkinter as tk
from tkinter import messagebox, scrolledtext

GITHUB_API_REPO = "HDMLM/MLHD2"
GITHUB_REPO = "https://github.com/HDMLM/MLHD2"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_API_REPO}"
REQUIREMENTS_FILE = "requirements.txt"
MAIN_PROGRAM = "main.py"
BACKUP_DIR_ROOT = "backup"

REQUEST_TIMEOUT_RELEASES = 10
REQUEST_TIMEOUT_ZIP = 30

# Exclusion globs / prefixes relative to repo root
# We don't want to overwrite user data since even if it's outdated the program should update the JSON as required, though we could add the option
# to clear the JSON's if the user wants to reset their data or we make a change that requires it. for future consideration i guess
EXCLUDE_PATH_PREFIXES = (
    "JSON/persistent",  # user persistent data variants
    "JSON/settings",    # user settings variants
    BACKUP_DIR_ROOT,    # avoid recursing into previous backups
    ".git",             # git internals
    "venv",             # local virtual env
)

def _is_excluded(rel_path: str) -> bool:
    # Return True if a relative path should be skipped during update
    normalized = rel_path.replace("\\", "/").lstrip("./")
    return any(normalized.startswith(pref) for pref in EXCLUDE_PATH_PREFIXES)

_VERSION_REGEX = re.compile(r'^\s*VERSION\s*=\s*["\']([^"\']+)["\']')


def get_local_version() -> Optional[str]:
    # Extract version string from Main.py (VERSION = "...")
    try:
        with open(MAIN_PROGRAM, "r", encoding="utf-8") as f:
            for line in f:
                m = _VERSION_REGEX.match(line)
                if m:
                    return m.group(1).strip()
    except Exception as e:
        return f"Error reading local version: {e}"
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
                dest_path = os.path.join('.', rel_path.replace('/', os.sep))
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


def check_version(include_prerelease: bool = False) -> str:
    # Return formatted version + patch notes using semantic comparison
    local_version = get_local_version()
    latest = get_latest_github_version(full=True, include_prerelease=include_prerelease)
    if not local_version or not isinstance(latest, dict):
        return f"Could not determine version. Local: {local_version}, GitHub: {latest}"
    latest_version = latest.get("tag", "?")
    notes = latest.get("body", "No patch notes found.")
    is_pr = latest.get("prerelease", False)
    cmp_result = _compare_versions(local_version, latest_version)
    if cmp_result == 0:
        status_line = "You are up to date!"
    elif cmp_result > 0:
        status_line = "Local version is ahead of GitHub release (development build)."
    else:
        status_line = "Update available!"
    return (
        f"Current version: {local_version}\n"
        f"Latest GitHub version: {latest_version}{' (pre-release)' if is_pr else ''}\n"
        f"{status_line}\n\nPatch Notes:\n{notes}"
    )
def check_requirements() -> str:
    # Ensure packages in requirements.txt are installed
    output: List[str] = []

    def read_requirements_lines(path: str) -> List[str]:
        # Read requirements file with multiple encoding fallbacks because people don't name packages like normal humans
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
        python_exe = PYTHON3106_EXE or sys.executable
        try:
            data = subprocess.check_output(
                [python_exe, "-m", "pip", "list", "--format", "json"],
                stderr=subprocess.DEVNULL,
            )
            import json
            pkgs = json.loads(data.decode("utf-8", errors="replace"))
            return {p["name"].lower(): p.get("version", "") for p in pkgs if isinstance(p, dict) and "name" in p}
        except Exception:
            return {}

    MGMT_PACKAGES = {"pip", "setuptools", "wheel"}  # skip managing these as they are part of pip's own operation... i think

    try:
        requirements = read_requirements_lines(REQUIREMENTS_FILE)
        if not requirements:
            output.append("No requirements found (file empty or unreadable).")
        installed = get_installed_packages()
        for req in requirements:
            # Support package==version or just package
            if '==' in req:
                pkg, pinned_version = req.split('==', 1)
                pinned_version = pinned_version.strip()
            else:
                pkg, pinned_version = req, ''
            pkg = pkg.strip()
            if not pkg:
                continue
            low_pkg = pkg.lower()
            if low_pkg in MGMT_PACKAGES:
                output.append(f"Skipping management package {pkg} (handled externally).")
                continue
            output.append(f"Checking {pkg} ...")
            python_exe = PYTHON3106_EXE or sys.executable
            if low_pkg in installed:
                current_v = installed[low_pkg]
                if pinned_version and current_v != pinned_version:
                    output.append(f"{pkg}: Version {current_v} != required {pinned_version} - updating...")
                    try:
                        subprocess.check_call([python_exe, "-m", "pip", "install", f"{pkg}=={pinned_version}"])
                        output.append(f"{pkg}: UPDATED to {pinned_version}")
                    except subprocess.CalledProcessError as e:
                        output.append(f"{pkg}: UPDATE FAILED ({e})")
                else:
                    output.append(f"{pkg}: OK ({current_v})")
            else:
                output.append(f"{pkg}: MISSING - Installing...")
                install_target = f"{pkg}=={pinned_version}" if pinned_version else pkg
                try:
                    subprocess.check_call([python_exe, "-m", "pip", "install", install_target])
                    output.append(f"{pkg}: INSTALLED")
                except subprocess.CalledProcessError as e:
                    output.append(f"{pkg}: INSTALL FAILED ({e})")
    except Exception as e:
        output.append(f"Error reading requirements: {e}")

    # Derive summary
    missing = [line for line in output if 'MISSING' in line or 'INSTALL FAILED' in line]
    if not output:
        output.append("No requirements processed.")
    if missing:
        output.append("")
        output.append(f"Summary: {len(missing)} package(s) missing - issued install commands.")
    else:
        output.append("")
        output.append("Summary: All requirements satisfied.")
    return "\n".join(output)

def launch_program_detached() -> Optional[subprocess.Popen]:
    # Start the main program process and return the Popen or None on failure
    python_exe = PYTHON3106_EXE or sys.executable
    if not os.path.exists(MAIN_PROGRAM):
        messagebox.showerror("Launch Error", f"Main program '{MAIN_PROGRAM}' not found.")
        return None
    try:
        return subprocess.Popen([python_exe, MAIN_PROGRAM])
    except Exception as e:
        messagebox.showerror("Launch Error", str(e))
        return None

def threaded_action(action: Callable[[], str], text_widget: scrolledtext.ScrolledText) -> None:
    def run():
        try:
            text_widget.config(state="normal")
            text_widget.insert(tk.END, f"{action.__name__.replace('_', ' ').title()}...\n")
            text_widget.update()
            result = action()
            text_widget.insert(tk.END, result + "\n")
        finally:
            text_widget.config(state="disabled")
    t = threading.Thread(target=run, daemon=True)
    t.start()


class InstallerGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MLHD2 Launcher")
        self.geometry("1280x720")
        self.resizable(False, False)

    # Load placeholder background image with error handling
        try:
            from PIL import Image, ImageTk
        except ImportError:
            tk.messagebox.showerror("Missing Dependency", "Pillow (PIL) is not installed. Please run 'pip install pillow' and restart the launcher.")
            self.bg_photo = None
        else:
            bg_path = os.path.join("media", "UnusedAssets", "SpacePlaceholder.png")
            if not os.path.exists(bg_path):
                tk.messagebox.showerror("Missing Image", f"Background image not found: {bg_path}")
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
                    tk.messagebox.showerror("Image Error", f"Failed to load background image: {e}")
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
        sidebar_icons = ["🏠", "📰", "⚙️", "❓"]
        for i, icon in enumerate(sidebar_icons):
            lbl = tk.Label(self.sidebar, text=icon, bg="#252526", fg="white", font=("Arial", 28, "bold"))
            lbl.place(x=20, y=40 + i*90, width=40, height=40)

    # Banner area
        self.banner_frame = tk.Frame(self.canvas, bg="#252526", width=920, height=110)
        self.banner_frame.place(x=80, y=0)
        self.banner_label = tk.Label(self.banner_frame, text="HD2 Mission Logger", bg="#252526", fg="white", font=("Arial", 28, "bold"))
        self.banner_label.place(x=30, y=18)
        latest_version = get_latest_github_version(include_prerelease=True)
        self.version_label = tk.Label(
            self.banner_frame,
            text=f"Latest Version: {latest_version}" if isinstance(latest_version, str) else "Drop Into Hell...",
            bg="#252526",
            fg="#AEE2FF",
            font=("Arial", 18, "italic")
        )
        self.version_label.place(x=30, y=60)


    # Main content area
        self.content_frame = tk.Frame(self.canvas, bg="#4C4C4C", width=400, height=320)
        self.content_frame.place(x=120, y=140)
        self.content_frame.update()
        self.content_frame.config(highlightbackground="#B0BEC5", highlightthickness=2)
        self.shadow = tk.Frame(self.canvas, bg="#252526", width=410, height=330)
        self.shadow.place(x=115, y=135)
        self.content_frame.lift(self.shadow)

        self.text = scrolledtext.ScrolledText(self.content_frame, state="disabled", width=46, height=10, font=("Arial", 12), relief="flat", bd=0, bg="#4C4C4C", fg="white", wrap="word")
        self.text.place(x=10, y=10)

    # Patch notes box
        self.patch_notes_frame = tk.Frame(self.canvas, bg="#4C4C4C", width=400, height=100)
        self.patch_notes_frame.place(x=120, y=470)
        self.patch_notes_frame.config(highlightbackground="#252526", highlightthickness=2)
        self.patch_notes_box = scrolledtext.ScrolledText(self.patch_notes_frame, state="disabled", width=46, height=5, font=("Arial", 11, "italic"), relief="flat", bd=0, bg="#4C4C4C", fg="white", wrap="word")
        self.patch_notes_box.place(x=10, y=10)

    # Button row

        button_y = 670
        button_x_start = 40
        button_w = 160
        button_h = 38
        button_pad = 20
        self.check_btn = tk.Button(self.canvas, text="Check Requirements", bg="#E0E0E0", fg="black", font=("Arial", 12), command=lambda: threaded_action(check_requirements, self.text), borderwidth=0)
        self.check_btn.place(x=button_x_start, y=button_y, width=button_w, height=button_h)

        self.update_btn = tk.Button(self.canvas, text="Update to Latest", bg="#E0E0E0", fg="black", font=("Arial", 12), command=lambda: threaded_action(lambda: safe_zip_update(self.include_prerelease.get()), self.text), borderwidth=0)
        self.update_btn.place(x=button_x_start + button_w + button_pad, y=button_y, width=button_w, height=button_h)

        self.version_btn = tk.Button(self.canvas, text="Check Version", bg="#E0E0E0", fg="black", font=("Arial", 12), command=self.display_version_info, borderwidth=0)
        self.version_btn.place(x=button_x_start + 2*(button_w + button_pad), y=button_y, width=button_w, height=button_h)

    # Always include pre-releases by default, originally a checkbox but im too lazy to refactor the code to remove it so we just set it true
        self.include_prerelease = tk.BooleanVar(value=True)

    # Place Start Game button at the absolute bottom right
        self.launch_btn = tk.Button(self.canvas, text="▶ Start Game", bg="#FFD600", fg="black", font=("Arial", 18, "bold"), command=self.launch_and_monitor, borderwidth=0, relief="flat", activebackground="#FFEA70")
        self.launch_btn.place(x=1080, y=630, width=180, height=55)

    # Initial display
        self.display_version_info()

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

        def monitor():
            exit_code = proc.wait()
            # Return to main thread for UI restore
            def restore():
                self.deiconify()
                self.launch_btn.config(state='normal')
                self.text.config(state='normal')
                self.text.insert(tk.END, f"Main program exited with code {exit_code}\n")
                self.text.config(state='disabled')
            try:
                self.after(0, restore)
            except Exception:
                pass

        threading.Thread(target=monitor, daemon=True).start()

if __name__ == "__main__":
    app = InstallerGUI()
    app.mainloop()