import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext
import requests
from typing import Optional, Dict, Any, List

GITHUB_API_REPO = "HDMLM/MLHD2"  # Set to your repo
GITHUB_REPO = "https://github.com/HDMLM/MLHD2"  # Set to your repo
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_API_REPO}"
REQUIREMENTS_FILE = "requirements.txt"
MAIN_PROGRAM = "main.py"  # Change to your main program filename

def get_local_version():
    # Reads VERSION from main.py
    try:
        with open(MAIN_PROGRAM, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("VERSION"):
                    # VERSION = "1.6.000"
                    parts = line.split("=")
                    if len(parts) == 2:
                        return parts[1].strip().replace('"', '').replace("'", "")
    except Exception as e:
        return f"Error reading local version: {e}"
    return None

def _github_headers() -> Dict[str, str]:
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def fetch_releases() -> List[Dict[str, Any]]:
    """Return list of releases (includes prereleases & drafts) from GitHub.
    Drafts are filtered out because they are not publicly downloadable.
    """
    url = f"{GITHUB_API_BASE}/releases"
    try:
        r = requests.get(url, headers=_github_headers(), timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        if not isinstance(data, list):
            return []
        # Filter out drafts
        return [release for release in data if not release.get("draft")]
    except Exception:
        return []

def pick_latest_release(include_prerelease: bool) -> Optional[Dict[str, Any]]:
    """Pick the latest release from the list.

    If include_prerelease is False, choose the first non-prerelease.
    If True, just return the first (GitHub API returns releases in descending chronological order).
    """
    releases = fetch_releases()
    if not releases:
        return None
    if include_prerelease:
        return releases[0]
    for rel in releases:
        if not rel.get("prerelease"):
            return rel
    return None

def get_latest_github_version(full=False, include_prerelease=False):
    """Fetch latest release (optionally including prerelease).

    Replaces earlier implementation that always hit /releases/latest which skips prereleases.
    """
    rel = pick_latest_release(include_prerelease=include_prerelease)
    if not rel:
        return "Could not fetch releases (possible rate limit or network issue)."
    tag = rel.get("tag_name") or rel.get("name")
    if full:
        return {
            "tag": tag,
            "body": rel.get("body", "No patch notes found."),
            "prerelease": rel.get("prerelease", False)
        }
    return tag

def check_version(include_prerelease=False):
    local_version = get_local_version()
    latest = get_latest_github_version(full=True, include_prerelease=include_prerelease)
    if not local_version or not isinstance(latest, dict):
        return f"Could not determine version. Local: {local_version}, GitHub: {latest}"
    latest_version = latest.get("tag", "?")
    notes = latest.get("body", "No patch notes found.")
    is_pr = latest.get("prerelease", False)
    msg = f"Current version: {local_version}\nLatest GitHub version: {latest_version}{' (pre-release)' if is_pr else ''}\n"
    if local_version == latest_version:
        msg += "You are up to date!\n"
    else:
        msg += "Update available!\n"
    msg += f"\nPatch Notes:\n{notes}"
    return msg
def check_requirements():
    output = []
    try:
        with open(REQUIREMENTS_FILE, "r") as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        for req in requirements:
            pkg = req.split("==")[0]
            try:
                subprocess.check_output([sys.executable, "-m", "pip", "show", pkg])
                output.append(f"{pkg}: OK")
            except subprocess.CalledProcessError:
                output.append(f"{pkg}: MISSING - Installing...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", req])
                output.append(f"{pkg}: INSTALLED")
    except Exception as e:
        output.append(f"Error: {e}")
    return "\n".join(output)

def update_from_github():
    output = []
    try:
        if not os.path.exists(".git"):
            output.append("Cloning repository...")
            subprocess.check_call(["git", "clone", GITHUB_REPO, "."])
        else:
            output.append("Pulling latest changes...")
            subprocess.check_call(["git", "pull"])
        output.append("Update complete.")
    except Exception as e:
        output.append(f"Error: {e}")
    return "\n".join(output)

def launch_program():
    try:
        subprocess.Popen([sys.executable, MAIN_PROGRAM])
    except Exception as e:
        messagebox.showerror("Launch Error", str(e))

def threaded_action(action, text_widget):
    def run():
        text_widget.config(state="normal")
        text_widget.insert(tk.END, f"{action.__name__.replace('_', ' ').title()}...\n")
        text_widget.update()
        result = action()
        text_widget.insert(tk.END, result + "\n")
        text_widget.config(state="disabled")
    threading.Thread(target=run).start()

class InstallerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MLHD2 Installer & Launcher")
        self.geometry("700x500")
        self.resizable(False, False)

        self.text = scrolledtext.ScrolledText(self, state="disabled", width=85, height=15)
        self.text.pack(pady=10)

        # Patch notes box
        self.patch_notes_label = tk.Label(self, text="Latest Patch Notes:", font=("Arial", 10, "bold"))
        self.patch_notes_label.pack(pady=(0,2))
        self.patch_notes_box = scrolledtext.ScrolledText(self, state="disabled", width=85, height=8)
        self.patch_notes_box.pack(pady=(0,10))

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)

        self.check_btn = tk.Button(btn_frame, text="Check Requirements", width=20,
                                   command=lambda: threaded_action(check_requirements, self.text))
        self.check_btn.grid(row=0, column=0, padx=5)

        self.update_btn = tk.Button(btn_frame, text="Update from GitHub", width=20,
                                    command=lambda: threaded_action(update_from_github, self.text))
        self.update_btn.grid(row=0, column=1, padx=5)

        self.launch_btn = tk.Button(btn_frame, text="Launch Program", width=20, command=launch_program)
        self.launch_btn.grid(row=0, column=2, padx=5)

        self.version_btn = tk.Button(btn_frame, text="Check Version", width=20,
                         command=self.display_version_info)
        self.version_btn.grid(row=1, column=1, pady=5)

        # Pre-release toggle (must be after root init)
        self.include_prerelease = tk.BooleanVar(value=False)
        # Place checkbox inside the button frame so it stays visible within fixed window height
        self.prerelease_chk = tk.Checkbutton(btn_frame, text="Include pre-releases",
                         variable=self.include_prerelease,
                         command=self.display_version_info)
        # Put it to the left of the Check Version button
        self.prerelease_chk.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        # Run version check on startup
        self.display_version_info()

    def display_version_info(self):
        self.text.config(state="normal")
        self.text.delete(1.0, tk.END)
        info = check_version(include_prerelease=self.include_prerelease.get())
        # Split patch notes from info
        if "Patch Notes:" in info:
            main_info, notes = info.split("Patch Notes:", 1)
        else:
            main_info, notes = info, "No patch notes found."
        self.text.insert(tk.END, main_info.strip() + "\n")
        self.text.config(state="disabled")
        self.patch_notes_box.config(state="normal")
        self.patch_notes_box.delete(1.0, tk.END)
        self.patch_notes_box.insert(tk.END, notes.strip())
        self.patch_notes_box.config(state="disabled")

if __name__ == "__main__":
    app = InstallerGUI()
    app.mainloop()