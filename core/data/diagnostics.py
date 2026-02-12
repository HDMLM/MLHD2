from __future__ import annotations

import json
import os
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from core.infrastructure.runtime_paths import app_path


def _safe_json_load(path: str) -> tuple[bool, str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            json.load(f)
        return True, "ok"
    except FileNotFoundError:
        return False, "missing"
    except json.JSONDecodeError as exc:
        return False, f"invalid_json:{exc.msg}"
    except Exception as exc:
        return False, f"error:{type(exc).__name__}"


def generate_diagnostics_dump(output_dir: str | None = None) -> str:
    now = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    target_dir = Path(output_dir or app_path("orphan"))
    target_dir.mkdir(parents=True, exist_ok=True)
    output_path = target_dir / f"diagnostics-{now}.json"

    json_files = [
        app_path("JSON", "settings.json"),
        app_path("JSON", "persistent.json"),
        app_path("JSON", "streak_data.json"),
    ]
    json_status: dict[str, dict[str, Any]] = {}
    for p in json_files:
        ok, state = _safe_json_load(p)
        json_status[p] = {"valid": ok, "state": state}

    mission_log_path = os.path.join(os.getenv("LOCALAPPDATA") or "", "MLHD2", "mission_log.xlsx")
    mission_test_log_path = os.path.join(os.getenv("LOCALAPPDATA") or "", "MLHD2", "mission_log_test.xlsx")

    payload: dict[str, Any] = {
        "created_utc": datetime.utcnow().isoformat() + "Z",
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "python": sys.version,
        },
        "environment": {
            "localappdata": os.getenv("LOCALAPPDATA", ""),
            "cwd": str(Path.cwd()),
            "mlhd2_data_backend": os.getenv("MLHD2_DATA_BACKEND", "excel"),
        },
        "files": {
            "json": json_status,
            "mission_log_exists": Path(mission_log_path).exists(),
            "mission_log_test_exists": Path(mission_test_log_path).exists(),
            "app_log_exists": Path("app.log").exists(),
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return str(output_path)
