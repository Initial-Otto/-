from abc import ABC, abstractmethod
from typing import List, Callable
from Core.enums import EventType
from Core.vector import Vector2
from Utility import IEventObserver, EventData
from Utility.Logger.logger import game_logger


class SenseResult:
    def __init__(self, sense_type: EventType, data, confidence: float, position: Vector2):
        self.sense_type = sense_type
        self.data = data
        self.confidence = confidence
        self.position = position


class IPerception(ABC):
    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def get_sense_results(self) -> List[SenseResult]:
        pass

    @abstractmethod
    def set_attention_radius(self, radius: float):
        pass

    @abstractmethod
    def add_attention_filter(self, filter_func: Callable[[SenseResult], bool]):
        pass


class PerceptionComponent(IPerception, IEventObserver):
    def __init__(self, owner_id: str, attention_radius: float = 500.0):
        self._owner_id = owner_id
        self._attention_radius = attention_radius
        self._sense_buffer = []
        self._filters = []
        self._position = Vector2.zero()

    def set_position(self, position: Vector2):
        self._position = position

    def update(self):
        self._sense_buffer = [s for s in self._sense_buffer if s.confidence >= 0.1]
        for sense in self._sense_buffer:
            sense.confidence *= 0.95

    def get_sense_results(self) -> List[SenseResult]:
        results = []
        for sense in self._sense_buffer:
            if self._apply_filters(sense):
                results.append(sense)
        self._sense_buffer = []
        return results

    def set_attention_radius(self, radius: float):
        self._attention_radius = radius

    def add_attention_filter(self, filter_func: Callable[[SenseResult], bool]):
        self._filters.append(filter_func)

    def update_player_position(self, player_pos: Vector2, danger_radius: float = 2.0):
        distance = self._position.distance_to(player_pos)
        if distance <= self._attention_radius:
            confidence = max(0, 1.0 - distance / self._attention_radius)
            self._add_sense(SenseResult(
                EventType.SENSE_PLAYER_DETECTED,
                None,
                confidence,
                player_pos
            ))
            if distance <= danger_radius:
                self._add_sense(SenseResult(
                    EventType.SENSE_DANGER,
                    None,
                    confidence,
                    player_pos
                ))

    def _apply_filters(self, sense: SenseResult) -> bool:
        for f in self._filters:
            if not f(sense):
                return False
        return True

    def on_event(self, event_data: EventData):
        if event_data.event_type in (EventType.SENSE_PLAYER_DETECTED,
                                     EventType.SENSE_PLAYER_LOST,
                                     EventType.SENSE_DANGER,
                                     EventType.SENSE_ITEM_NEARBY):
            player_pos = event_data.sender
            if isinstance(player_pos, Vector2):
                distance = self._position.distance_to(player_pos)
                if distance > self._attention_radius:
                    return
                confidence = max(0, 1.0 - distance / self._attention_radius)
            else:
                confidence = 1.0
                player_pos = None
            
            self._add_sense(SenseResult(
                event_data.event_type,
                event_data,
                confidence,
                player_pos if player_pos else self._position
            ))

    def _add_sense(self, sense: SenseResult):
        distance = self._position.distance_to(sense.position)
        if distance > self._attention_radius:
            sense.confidence *= (1 - (distance - self._attention_radius) / self._attention_radius)

        self._sense_buffer.append(sense)
        game_logger.debug(
            f"[{self._owner_id}] Sense detected: {sense.sense_type.name} "
            f"(confidence: {sense.confidence:.2f})"
        )
