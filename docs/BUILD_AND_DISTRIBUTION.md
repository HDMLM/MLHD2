# Build and Distribution Flow

## Prerequisites
- Python 3.10.x
- Windows host (for current `.spec` + batch flow)
- Virtual environment recommended

## Setup
1. Create/activate venv.
2. Install runtime deps:
   - `pip install -r requirements.txt`
3. Install developer deps (optional but recommended):
   - `pip install -r requirements-dev.txt`

## Run Locally
- `python main.py`

## Build Launcher EXE
1. From repository root:
   - `cd tools`
   - `build.bat`
2. Output artifact:
   - `tools/Built/MLHD2-Launcher.exe`

## Packaging Notes
- PyInstaller uses `installer.spec`.
- Build script cleans `dist/` and `build/` after moving artifact.
- Keep media/JSON resources in expected relative paths for runtime.

## Distribution Steps
1. Build using clean virtual environment.
2. Smoke test launcher on a non-dev machine/profile.
3. Verify app can:
   - open settings,
   - append mission,
   - send webhook,
   - read/write JSON cache files.
4. Publish executable with matching release notes and checksum.
