"""
Configuração de logging para a aplicação.
"""

import os
import logging.config
from datetime import datetime

# Diretório para logs
LOG_DIR = os.getenv("LOG_DIR", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Nome do arquivo de log baseado na data
LOG_FILE = os.path.join(LOG_DIR, f"api_{datetime.now().strftime('%Y%m%d')}.log")

# Configuração do logging
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        "detailed": {
            "format": (
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s "
                "[%(pathname)s:%(lineno)d]"
            )
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "detailed",
            "filename": LOG_FILE,
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "detailed",
            "filename": os.path.join(LOG_DIR, "error.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "level": "ERROR"
        }
    },
    "loggers": {
        "api": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False
        },
        "celery": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False
        },
        "storage": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False
        }
    },
    "root": {
        "handlers": ["console", "file", "error_file"],
        "level": "WARNING"
    }
} 