from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from Core.enums import DeviceType
from Core.vector import Vector2, Rect
from Utility import DeviceContext, ISceneStrategy
from Utility.Logger.logger import game_logger


class SceneContext:
    def __init__(self, device_context: DeviceContext):
        self.device_context = device_context
        self.bounds = Rect(0, 0, 1920, 1080)
        self.active_npcs: List[str] = []


class IScene(ABC):
    @property
    @abstractmethod
    def scene_id(self) -> str:
        pass

    @property
    @abstractmethod
    def context(self) -> SceneContext:
        pass

    @abstractmethod
    def load(self):
        pass

    @abstractmethod
    def unload(self):
        pass


class Scene(IScene):
    def __init__(self, scene_id: str, device_context: DeviceContext):
        self._scene_id = scene_id
        self._context = SceneContext(device_context)

    @property
    def scene_id(self) -> str:
        return self._scene_id

    @property
    def context(self) -> SceneContext:
        return self._context

    def load(self):
        game_logger.info(f"Scene [{self._scene_id}] loaded")

    def unload(self):
        game_logger.info(f"Scene [{self._scene_id}] unloaded")


class ISceneManager(ABC):
    @abstractmethod
    def create_scene_context(self, device_context: DeviceContext) -> SceneContext:
        pass

    @abstractmethod
    def add_npc_to_scene(self, npc, position: Vector2):
        pass

    @abstractmethod
    def get_npc_count(self) -> int:
        pass

    @abstractmethod
    def update(self):
        pass


class SceneManager(ISceneManager):
    def __init__(self):
        device_context = DeviceContext(DeviceType.PC)
        self._current_scene = Scene("MainScene", device_context)
        self._npcs_in_scene: Dict[str, object] = {}
        self._current_scene.load()

    def create_scene_context(self, device_context: DeviceContext) -> SceneContext:
        return SceneContext(device_context)

    def add_npc_to_scene(self, npc, position: Vector2):
        npc.position = position
        self._npcs_in_scene[npc.npc_id] = npc
        self._current_scene.context.active_npcs.append(npc.npc_id)
        game_logger.debug(
            f"NPC [{npc.npc_id}] added to scene at ({position.x}, {position.y})"
        )

    def get_npc_count(self) -> int:
        return len(self._npcs_in_scene)

    def update(self):
        pass


# ========== Scene Strategies ==========

class BattleSceneStrategy(ISceneStrategy):
    def get_strategy_name(self) -> str:
        return "BattleScene"

    def apply(self, context: DeviceContext):
        game_logger.info("Applying Battle scene strategy")


class TownSceneStrategy(ISceneStrategy):
    def get_strategy_name(self) -> str:
        return "TownScene"

    def apply(self, context: DeviceContext):
        game_logger.info("Applying Town scene strategy")


class DungeonSceneStrategy(ISceneStrategy):
    def get_strategy_name(self) -> str:
        return "DungeonScene"

    def apply(self, context: DeviceContext):
        game_logger.info("Applying Dungeon scene strategy")
