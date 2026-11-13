from collections import defaultdict, deque
from .ievent_bus import IEventBus, IEventObserver, EventData
from Core.enums import EventType
from Utility.Logger.logger import game_logger


class EventBus(IEventBus):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self._observers = defaultdict(list)
        self._delayed_events = deque()

    def subscribe(self, event_type: EventType, observer: IEventObserver):
        if event_type == EventType.NONE:
            return
        if observer not in self._observers[event_type]:
            self._observers[event_type].append(observer)
            game_logger.debug(f"Observer [{observer.__class__.__name__}] subscribed to [{event_type.name}]")

    def unsubscribe(self, event_type: EventType, observer: IEventObserver):
        if event_type == EventType.NONE:
            return
        if observer in self._observers[event_type]:
            self._observers[event_type].remove(observer)
            game_logger.debug(f"Observer [{observer.__class__.__name__}] unsubscribed from [{event_type.name}]")

    def notify(self, event_data: EventData):
        if event_data.event_type == EventType.NONE:
            return
        observers = list(self._observers[event_data.event_type])
        for observer in observers:
            try:
                observer.on_event(event_data)
            except Exception as ex:
                game_logger.error(f"Error notifying observer {observer.__class__.__name__}: {ex}", ex)

    def notify_delayed(self, event_data: EventData):
        self._delayed_events.append(event_data)

    def update(self):
        count = len(self._delayed_events)
        for _ in range(count):
            if self._delayed_events:
                evt = self._delayed_events.popleft()
                self.notify(evt)
