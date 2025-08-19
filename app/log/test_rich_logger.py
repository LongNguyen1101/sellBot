# colored_logger_helpers.py - Helper functions cho màu cố định
import logging
from rich.logging import RichHandler
from rich.console import Console

# Setup cơ bản
console = Console(force_terminal=True, width=120)
rich_handler = RichHandler(console=console, show_time=True, show_path=False, markup=True)
logger = logging.getLogger("app.test")
logger.setLevel(logging.DEBUG)
logger.addHandler(rich_handler)

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

# Tạo colored logger
colored_log = ColoredLogger(logger)

# Test
if __name__ == "__main__":
    print("=== Test màu mặc định ===")
    colored_log.debug("Debug message với màu cyan mặc định")
    colored_log.info("Info message với màu magenta mặc định")
    colored_log.warning("Warning message với màu cam mặc định")
    colored_log.error("Error message với màu đỏ sáng mặc định")
    colored_log.critical("Critical message với màu tím đậm mặc định")
    
    print("\n=== Test màu tùy chỉnh ===")
    colored_log.debug("Debug với màu xanh lá", color="green")
    colored_log.info("Info với màu xanh dương", color="blue")
    colored_log.error("Error với màu vàng", color="yellow")
    
    print("\n=== Test method đặc biệt ===")
    colored_log.success("Operation completed successfully!")
    colored_log.fail("Operation failed!")
    colored_log.highlight("Important information!")
    colored_log.subtle("Less important info...")
    
    print("\n=== Tất cả màu Rich có thể dùng ===")
    colors = [
        "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
        "bright_black", "bright_red", "bright_green", "bright_yellow", 
        "bright_blue", "bright_magenta", "bright_cyan", "bright_white",
        "orange3", "purple", "pink1", "deep_pink1", "gold1"
    ]
    
    for color in colors:
        colored_log.info(f"Màu {color}", color=color)