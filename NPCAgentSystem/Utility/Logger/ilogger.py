from abc import ABC, abstractmethod
from Core.enums import LogLevel


class ILogger(ABC):
    @abstractmethod
    def debug(self, message: str):
        pass

    @abstractmethod
    def info(self, message: str):
        pass

    @abstractmethod
    def warn(self, message: str):
        pass

    @abstractmethod
    def error(self, message: str, ex: Exception = None):
        pass
