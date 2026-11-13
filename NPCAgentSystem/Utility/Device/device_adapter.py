from .idevice_adapter import IDeviceAdapter, DeviceContext, ISceneStrategy
from Core.enums import DeviceType
from Core.vector import Vector2
from Utility.Logger.logger import game_logger


class PCAdapter(IDeviceAdapter):
    def __init__(self):
        self._context = DeviceContext(DeviceType.PC)
        self._context.screen_size = Vector2(1920, 1080)
        self._context.dpi_scale = 1.0
        self._context.supports_touch = False
        self._context.supports_gamepad = True

    def get_device_type(self) -> DeviceType:
        return DeviceType.PC

    def get_device_context(self) -> DeviceContext:
        return self._context

    def apply_scene_strategy(self, strategy: ISceneStrategy):
        game_logger.debug(f"Applying strategy [{strategy.get_strategy_name()}] for PC device")
        strategy.apply(self._context)


class MobileAdapter(IDeviceAdapter):
    def __init__(self):
        self._context = DeviceContext(DeviceType.MOBILE)
        self._context.screen_size = Vector2(1080, 1920)
        self._context.dpi_scale = 2.0
        self._context.supports_touch = True
        self._context.supports_gamepad = False

    def get_device_type(self) -> DeviceType:
        return DeviceType.MOBILE

    def get_device_context(self) -> DeviceContext:
        return self._context

    def apply_scene_strategy(self, strategy: ISceneStrategy):
        game_logger.debug(f"Applying strategy [{strategy.get_strategy_name()}] for Mobile device")
        strategy.apply(self._context)


class ConsoleAdapter(IDeviceAdapter):
    def __init__(self):
        self._context = DeviceContext(DeviceType.CONSOLE)
        self._context.screen_size = Vector2(1920, 1080)
        self._context.dpi_scale = 1.0
        self._context.supports_touch = False
        self._context.supports_gamepad = True

    def get_device_type(self) -> DeviceType:
        return DeviceType.CONSOLE

    def get_device_context(self) -> DeviceContext:
        return self._context

    def apply_scene_strategy(self, strategy: ISceneStrategy):
        game_logger.debug(f"Applying strategy [{strategy.get_strategy_name()}] for Console device")
        strategy.apply(self._context)
