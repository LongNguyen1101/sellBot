# logging_config.py
import logging
import logging.config
from rich.logging import RichHandler
from rich.console import Console

console = Console(force_terminal=True, width=150)

# Tạo RichHandler
rich_handler = RichHandler(
    console=console,
    show_time=True,
    show_path=False,
    markup=True,
    rich_tracebacks=True
)

class ColoredLogger:
    """Wrapper class cung cấp các method với màu cố định"""
    
    def __init__(self, logger):
        self.logger = logger
    
    # Các màu tùy chỉnh cho từng level
    def debug(self, message, color="cyan"):
        self.logger.debug(f"🔍 [{color}]{message}[/{color}]")
    
    def info(self, message, color="bright_magenta"):
        self.logger.info(f"ℹ️  [{color}]{message}[/{color}]")
    
    def warning(self, message, color="orange3"):
        self.logger.warning(f"⚠️  [{color}]{message}[/{color}]")
    
    def error(self, message, color="bright_red"):
        self.logger.error(f"❌ [{color}]{message}[/{color}]")
    
    def critical(self, message, color="bold purple"):
        self.logger.critical(f"🚨 [{color}]{message}[/{color}]")
    
    # Các method với màu đặc biệt
    def success(self, message):
        self.logger.info(f"✅ [bold green]{message}[/bold green]")
    
    def fail(self, message):
        self.logger.error(f"💥 [bold red on yellow]{message}[/bold red on yellow]")
    
    def highlight(self, message):
        self.logger.info(f"⭐ [bold yellow on blue]{message}[/bold yellow on blue]")
    
    def subtle(self, message):
        self.logger.info(f"[dim]{message}[/dim]")

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
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False 
    logger.addHandler(rich_handler)
    
    return ColoredLogger(logger)