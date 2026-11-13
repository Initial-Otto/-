from abc import ABC, abstractmethod
from datetime import datetime
from Core.enums import EventType


class EventData:
    def __init__(self, event_type: EventType, sender=None, extra_data=None):
        self.event_type = event_type
        self.sender = sender
        self.extra_data = extra_data
        self.timestamp = datetime.now()


class IEventObserver(ABC):
    @abstractmethod
    def on_event(self, event_data: EventData):
        pass


class IEventBus(ABC):
    @abstractmethod
    def subscribe(self, event_type: EventType, observer: IEventObserver):
        pass

    @abstractmethod
    def unsubscribe(self, event_type: EventType, observer: IEventObserver):
        pass

    @abstractmethod
    def notify(self, event_data: EventData):
        pass

    @abstractmethod
    def notify_delayed(self, event_data: EventData):
        pass

    @abstractmethod
    def update(self):
        pass
