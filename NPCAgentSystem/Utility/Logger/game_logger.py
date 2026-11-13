import os
import sys
from datetime import datetime
from .ilogger import ILogger
from Core.enums import LogLevel


class GameLogger(ILogger):
    _instance = None
    _lock = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_file_path = os.path.join(log_dir, f"game_{timestamp}.log")
        self._file = open(self._log_file_path, "a", encoding="utf-8")
        self._min_level = LogLevel.WARN  # 只显示警告和错误级别日志

    def debug(self, message: str):
        self._log(LogLevel.DEBUG, message)

    def info(self, message: str):
        self._log(LogLevel.INFO, message)

    def warn(self, message: str):
        self._log(LogLevel.WARN, message)

    def error(self, message: str, ex: Exception = None):
        if ex:
            self._log(LogLevel.ERROR, f"{message}\nException: {ex}")
        else:
            self._log(LogLevel.ERROR, message)

    def _log(self, level: LogLevel, message: str):
        if level.value < self._min_level.value:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.") + f"{datetime.now().microsecond // 1000:03d}"
        caller_info = self._get_caller_info()
        log_entry = f"[{timestamp}] [{level.name}] [{caller_info}] {message}"

        self._file.write(log_entry + "\n")
        self._file.flush()

        # Console output with color
        color = self._get_color(level)
        if color and sys.stdout.isatty():
            print(f"{color}{log_entry}\033[0m")
        else:
            print(log_entry)

    def _get_caller_info(self):
        import traceback
        stack = traceback.extract_stack()
        # Go back 4 levels to find the actual caller
        for frame in reversed(stack[:-3]):
            if "logger" not in frame.filename.lower():
                return f"{os.path.basename(frame.filename)}:{frame.lineno}"
        return "unknown"

    def _get_color(self, level: LogLevel):
        colors = {
            LogLevel.DEBUG: "\033[36m",
            LogLevel.INFO: "\033[32m",
            LogLevel.WARN: "\033[33m",
            LogLevel.ERROR: "\033[31m",
        }
        return colors.get(level, "")

    def close(self):
        if self._file:
            self._file.close()
