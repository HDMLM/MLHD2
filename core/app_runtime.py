from __future__ import annotations

import configparser
import os

from core.infrastructure.runtime_paths import app_path


def ensure_app_data_dir() -> str:
    app_data = os.path.join(os.getenv("LOCALAPPDATA", ""), "MLHD2")
    if app_data and not os.path.exists(app_data):
        os.makedirs(app_data)
    return app_data


def get_excel_paths() -> tuple[str, str]:
    app_data = ensure_app_data_dir()
    return (
        os.path.join(app_data, "mission_log.xlsx"),
        os.path.join(app_data, "mission_log_test.xlsx"),
    )


def load_core_configs() -> tuple[configparser.ConfigParser, configparser.ConfigParser]:
    config = configparser.ConfigParser()
    config.read(app_path("orphan", "config.config"))

    icon_config = configparser.ConfigParser()
    icon_config.read(app_path("orphan", "icon.config"))
    return config, icon_config
