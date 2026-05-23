import logging
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "fastapi_style": {
            # Note the "z" in ColourizedFormatter
            "()": "uvicorn.logging.ColourizedFormatter",
            # Uvicorn expects 'fmt' explicitly rather than 'format'
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": True,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "fastapi_style",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "fastapi_style",
            "filename": "/tmp/lens_app.log",
            "mode": "a",
        },
    },
    "loggers": {
        "watchfiles": {
            "level": "WARNING",
            "propagate": False,
        },
    },
    "root": {"level": "DEBUG", "handlers": ["console", "file"]},
}


def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)
