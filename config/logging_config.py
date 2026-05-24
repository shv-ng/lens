import logging
import logging.config
from pathlib import Path

LOG_DIR = Path("/tmp")
LOG_DIR.mkdir(parents=True, exist_ok=True)


class SafeExtraFormatter(logging.Formatter):
    def format(self, record):
        record.fn = getattr(record, "fn", "-")
        record.duration_ms = getattr(record, "duration_ms", "-")
        record.error = getattr(record, "error", "-")
        return super().format(record)


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": ("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "standard",
            "filename": str(LOG_DIR / "lens_app.log"),
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": [
            "console",
            "file",
        ],
    },
}


def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)
