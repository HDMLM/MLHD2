import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

_configured = False


class _StructuredContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "module_field"):
            record.module_field = record.name
        if not hasattr(record, "action"):
            record.action = "-"
        if not hasattr(record, "outcome"):
            record.outcome = "-"
        if not hasattr(record, "latency_ms"):
            record.latency_ms = "-"
        return True


# Configures root logging (console/file levels); affects app-wide logging output
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
    context_filter = _StructuredContextFilter()

    # Remove any pre-existing handlers added by libraries (to avoid duplicate/verbose output)
    for h in list(root.handlers):
        root.removeHandler(h)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(console_level)
    ch.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(module_field)s] action=%(action)s outcome=%(outcome)s latency_ms=%(latency_ms)s %(message)s",
            "%H:%M:%S",
        )
    )
    ch.addFilter(context_filter)
    root.addHandler(ch)

    # File handler (rotating not required yet; simple append)
    try:
        max_bytes = int(os.getenv("MLHD2_LOG_MAX_BYTES", str(2 * 1024 * 1024)))
        backup_count = int(os.getenv("MLHD2_LOG_BACKUP_COUNT", "3"))
        fh = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        fh.setLevel(log_level_file)
        fh.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(module_field)s] action=%(action)s outcome=%(outcome)s latency_ms=%(latency_ms)s %(message)s",
                "%Y-%m-%d %H:%M:%S",
            )
        )
        fh.addFilter(context_filter)
        root.addHandler(fh)
    except OSError:
        root.error("Failed to set up file logging; continuing without file handler")

    _configured = True

    # Quiet noisy third-party libraries by default
    # Pillow (PIL) PNG plugin can be very verbose at DEBUG level.
    for noisy in ("PIL", "PIL.PngImagePlugin", "urllib3", "requests", "discord", "discordrpc", "presence"):
        nlog = logging.getLogger(noisy)
        nlog.setLevel(logging.WARNING)
        # Avoid duplicate output if library attached its own handlers
        for h in list(nlog.handlers):
            nlog.removeHandler(h)


# Returns a named logger for modules; affects structured log routing
def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name)


def log_event(
    logger: logging.Logger,
    level: int,
    message: str,
    *,
    module: str,
    action: str,
    outcome: str,
    latency_ms: Optional[int] = None,
) -> None:
    logger.log(
        level,
        message,
        extra={
            "module_field": module,
            "action": action,
            "outcome": outcome,
            "latency_ms": latency_ms if latency_ms is not None else "-",
        },
    )
