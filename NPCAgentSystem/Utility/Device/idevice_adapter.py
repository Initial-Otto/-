from abc import ABC, abstractmethod
from Core.enums import DeviceType
from Core.vector import Vector2


class DeviceContext:
    def __init__(self, device_type: DeviceType):
        self.device_type = device_type
        self.screen_size = Vector2(1920, 1080)
        self.dpi_scale = 1.0
        self.supports_touch = False
        self.supports_gamepad = False


class IDeviceAdapter(ABC):
    @abstractmethod
    def get_device_type(self) -> DeviceType:
        pass

    @abstractmethod
    def get_device_context(self) -> DeviceContext:
        pass

    @abstractmethod
    def apply_scene_strategy(self, strategy: 'ISceneStrategy'):
        pass


class ISceneStrategy(ABC):
    @abstractmethod
    def apply(self, context: DeviceContext):
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        pass
