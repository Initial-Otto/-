from abc import ABC, abstractmethod
from Core.vector import Vector2


class INPCActionService(ABC):
    @abstractmethod
    def move_towards_player(self, npc_id: str):
        pass

    @abstractmethod
    def move_towards(self, npc_id: str, target: Vector2):
        pass

    @abstractmethod
    def move_random(self, npc_id: str):
        pass

    @abstractmethod
    def move_random_in_range(self, npc_id: str, center: Vector2, radius: float):
        pass

    @abstractmethod
    def attack_player(self, npc_id: str):
        pass

    @abstractmethod
    def stay(self, npc_id: str):
        pass