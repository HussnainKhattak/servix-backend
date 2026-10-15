import logging
import logging.config
import sys
from app.core.config import settings


def setup_logging():
    """Configure structured logging for FastAPI and SQLAlchemy."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
                "datefmt": "%Y-%m-%dT%H:%M:%SZ",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "default",
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
        "loggers": {
            "uvicorn": {"level": logging.INFO},
            "uvicorn.error": {"level": logging.INFO},
            "uvicorn.access": {"level": logging.INFO},
            "sqlalchemy.engine": {
                "level": logging.INFO if settings.DB_ECHO else logging.WARNING
            },
            "alembic": {"level": logging.INFO},
            "app": {"level": log_level},
        },
    }

    logging.config.dictConfig(logging_config)
    logger = logging.getLogger("app")
    logger.info(f"Initialized {settings.APP_NAME} in [{settings.APP_ENV}] mode.")
    return logger


logger = logging.getLogger("app")
