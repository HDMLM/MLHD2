import logging
import os
from typing import Optional

_configured = False

def setup_logging(debug: bool, log_file: str = "app.log") -> None:
    """Configure root logger.

    In debug mode: verbose INFO to console.
    In normal mode: only ERROR+ to console; still capture INFO+ to file.
    Safe to call multiple times (will no-op after first successful config).
    """
    global _configured
    if _configured:
        # Still adjust console handler level if caller toggled debug at runtime
        for h in logging.getLogger().handlers:
            if isinstance(h, logging.StreamHandler):
                h.setLevel(logging.INFO if debug else logging.ERROR)
        return

    log_level_file = logging.DEBUG if debug else logging.INFO
    console_level = logging.INFO if debug else logging.ERROR

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # Capture all; handlers filter

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(console_level)
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%H:%M:%S"))
    root.addHandler(ch)

    # File handler (rotating not required yet; simple append)
    try:
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(log_level_file)
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
        root.addHandler(fh)
    except OSError:
        root.error("Failed to set up file logging; continuing without file handler")

    _configured = True

def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name)
