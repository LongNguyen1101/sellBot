# logging_config.py
import logging
import logging.config
import sys

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "filters": {
        "app_only": {
            "()": "logging.Filter",
            "name": "app"  # chỉ cho phép logger bắt đầu với 'app'
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
            "level": "DEBUG",
            "filters": ["app_only"]
        },
        "file": {
            "class": "logging.FileHandler",
            "formatter": "default",
            "filename": "app.log",
            "level": "INFO",
            "filters": ["app_only"]
        }
    },
    "loggers": {
        # Tối ưu hóa logger cho các module "ồn ào"
        "urllib3": {"level": "WARNING", "handlers": [], "propagate": False},
        "openai": {"level": "WARNING", "handlers": [], "propagate": False},
        "langsmith": {"level": "WARNING", "handlers": [], "propagate": False},
        "httpcore": {"level": "WARNING", "handlers": [], "propagate": False},
    },
    "root": {
        "level": "DEBUG",
        "handlers": ["console", "file"]
    },
}

def setup_logging(name):
    """Cấu hình logging theo dictConfig với filter chỉ giữ log từ app.*"""
    logging.config.dictConfig(LOGGING_CONFIG)
    return logging.getLogger(name)