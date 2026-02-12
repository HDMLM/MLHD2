import configparser
import os
import sys
from pathlib import Path
from typing import Optional

_CONFIG_DIR_NAME = "MLHD2"
_CONFIG_FILENAME = "launcher_config.ini"


# Computes per-user launcher config file path; affects install dir persistence
def _get_user_config_file() -> str:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    cfg_dir = os.path.join(base, _CONFIG_DIR_NAME)
    try:
        os.makedirs(cfg_dir, exist_ok=True)
        return os.path.join(cfg_dir, _CONFIG_FILENAME)
    except Exception:
        # Fall back to a local config in the package folder
        try:
            local = os.path.join(str(Path(__file__).parent.resolve()), _CONFIG_FILENAME)
            os.makedirs(str(Path(__file__).parent.resolve()), exist_ok=True)
            return local
        except Exception:
            return os.path.join(str(Path(__file__).parent.resolve()), _CONFIG_FILENAME)


# Reads saved install directory from env/config; affects path resolution
def read_saved_install_dir() -> Optional[str]:
    # Try cache via env first
    env = os.environ.get("MLHD2_INSTALL_DIR")
    if env:
        return env
    cfg = configparser.ConfigParser()
    try:
        cfg.read(_get_user_config_file())
        v = cfg.get("Paths", "install_dir", fallback="").strip()
        if v:
            return v
    except Exception:
        pass
    return None


# Resolves effective install directory (handles frozen builds); affects resource lookup
def get_install_dir() -> str:
    d = read_saved_install_dir()
    if d:
        return d
    # Fallback to this package directory (useful for development)
    if getattr(sys, "frozen", False):
        return str(Path(os.path.dirname(sys.executable)).resolve())
    return str(Path(__file__).parent.resolve())


# Resolves resource path via install dir with sensible fallbacks; affects file access
def app_path(*parts: str) -> str:
    """Return an absolute path for a resource relative to the install directory.

    If the resource doesn't exist under the configured install directory, also
    check a few sensible fallback locations (repository root and current
    working directory). This keeps development workflows working when the
    package directory is used as the install dir but data files live in the
    repository root.
    """
    install_dir = Path(get_install_dir())
    candidates = [install_dir, Path(__file__).parent.parent.resolve(), Path.cwd()]
    for base in candidates:
        try:
            p = base.joinpath(*parts)
        except Exception:
            continue
        if p.exists():
            return str(p)
    # No existing file found - return the path under the install dir as a
    # best-effort fallback (matches previous behaviour).
    return str(install_dir.joinpath(*parts))


# Resolves bundled resource path (PyInstaller aware); affects packaged assets
def resource_path(*parts: str) -> str:
    # For bundled resources (PyInstaller _MEIPASS) or package-local resources
    meipass = getattr(sys, "_MEIPASS", None)
    base = Path(meipass) if meipass else Path(__file__).parent
    return str(base.joinpath(*parts))
