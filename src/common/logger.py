import logging
from datetime import datetime
from pathlib import Path

try:
    from . import config
except ImportError:
    import config


class Logger:
    LOG_LEVELS = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    class _LogTypeFilter(logging.Filter):
        def __init__(self, log_type: str):
            super().__init__()
            self.log_type = log_type

        def filter(self, record: logging.LogRecord) -> bool:
            # Inject log_type so the formatter placeholder is always present.
            if not hasattr(record, "log_type"):
                record.log_type = self.log_type
            return True

    def __init__(self, log_type: str):
        if log_type not in ("backend", "frontend"):
            raise ValueError(
                f"Invalid log_type '{log_type}'. Expected 'backend' or 'frontend'.")

        self.logger = logging.getLogger(f"wnm_{log_type}")
        self.logger.setLevel(self.LOG_LEVELS.get(
            config.LOG_LEVEL.strip().lower(), logging.INFO))
        self.logger.handlers.clear()

        self._log_type_filter = self._LogTypeFilter(log_type)
        self.logger.addFilter(self._log_type_filter)

        self.log_dir = Path(__file__).parent.parent.parent / "logs" / log_type
        self.formatter = logging.Formatter(
            "%(asctime)s - [%(log_type)s] - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.last_log_path = None

        self._ensure_log_dir_exists()
        self._setup_handlers()

    def _ensure_log_dir_exists(self):
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(
                f"Failed to create log directory {self.log_dir.absolute()}: {e}")
            raise

    def _get_today_log_path(self) -> Path:
        today = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"{today}.log"

    def _setup_handlers(self):
        current_log_path = self._get_today_log_path()

        if self.last_log_path == current_log_path:
            return

        for handler in list(self.logger.handlers):
            if isinstance(handler, logging.FileHandler):
                self.logger.removeHandler(handler)
                handler.close()

        try:
            new_file_handler = logging.FileHandler(
                str(current_log_path),
                encoding="utf-8"
            )
            new_file_handler.setFormatter(self.formatter)
            self.logger.addHandler(new_file_handler)
            self.last_log_path = current_log_path
        except Exception as e:
            print(
                f"Failed to create file handler for {current_log_path.absolute()}: {e}")
            raise

        has_console_handler = any(isinstance(
            h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
            for h in self.logger.handlers)
        if not has_console_handler:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(self.formatter)
            self.logger.addHandler(console_handler)

    def _log(self, level, msg, exc_info=False):
        self._setup_handlers()
        if level == logging.DEBUG:
            self.logger.debug(msg)
        elif level == logging.INFO:
            self.logger.info(msg)
        elif level == logging.WARNING:
            self.logger.warning(msg)
        elif level == logging.ERROR:
            self.logger.error(msg, exc_info=exc_info)
        elif level == logging.CRITICAL:
            self.logger.critical(msg)

    def debug(self, msg):
        self._log(logging.DEBUG, msg)

    def info(self, msg):
        self._log(logging.INFO, msg)

    def warning(self, msg):
        self._log(logging.WARNING, msg)

    def error(self, msg, exc_info=False):
        self._log(logging.ERROR, msg, exc_info=exc_info)

    def critical(self, msg):
        self._log(logging.CRITICAL, msg)


frontend_logger = Logger(log_type="frontend")
backend_logger = Logger(log_type="backend")
