import json
import os
from typing import Dict, List

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Exclusions per your request (+ common VCS/IDE dirs)
IGNORE_FILES = {".gitignore", ".gitattributes", "installer.spec", "app.log"}
IGNORE_DIRS = {".git", ".vscode", "__pycache__", "venv", ".venv"}

def build_tree(dir_path: str) -> Dict:
    node = {"name": os.path.basename(dir_path) or dir_path, "type": "dir", "children": []}

    try:
        entries = os.listdir(dir_path)
    except OSError:
        return node

    dirs: List[str] = []
    files: List[str] = []

    for entry in entries:
        full = os.path.join(dir_path, entry)
        if os.path.isdir(full):
            if entry in IGNORE_DIRS:
                continue
            dirs.append(entry)
        else:
            if entry in IGNORE_FILES:
                continue
            files.append(entry)

    for d in sorted(dirs, key=str.casefold):
        node["children"].append(build_tree(os.path.join(dir_path, d)))

    for f in sorted(files, key=str.casefold):
        ext = os.path.splitext(f)[1].lower()
        if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp"}:
            ftype = "image"
        elif ext in {".py", ".js", ".ts", ".sh", ".bat", ".rb", ".pl"}:
            ftype = "script"
        elif ext in {".md", ".txt", ".rst"}:
            ftype = "text"
        elif ext in {".json", ".yaml", ".yml", ".xml", ".ini", ".toml"}:
            ftype = "config"
        elif ext in {".csv", ".tsv", ".xls", ".xlsx"}:
            ftype = "data"
        elif ext in {".zip", ".tar", ".gz", ".rar", ".7z"}:
            ftype = "archive"
        elif ext in {".exe", ".dll", ".so", ".bin"}:
            ftype = "binary"
        else:
            ftype = "file"
        node["children"].append({"name": f, "type": ftype})

    return node

def main():
    tree = build_tree(ROOT)
    out_dir = os.path.join(ROOT, "LaunchMedia")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "FStruct.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(tree, fh, indent=2)
    print(f"Wrote {os.path.relpath(out_path, ROOT)}")

if __name__ == "__main__":
    main()