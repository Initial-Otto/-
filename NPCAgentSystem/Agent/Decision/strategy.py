from abc import ABC, abstractmethod
from typing import List, Optional
from .state import INPCContext
from Utility.exceptions import StrategyExecutionException
from Utility.Logger.logger import game_logger


# ========== Strategy Pattern ==========

class IAction(ABC):
    @property
    @abstractmethod
    def action_name(self) -> str:
        pass

    @abstractmethod
    def execute(self, context: INPCContext):
        pass


class IStrategy(ABC):
    @property
    @abstractmethod
    def strategy_name(self) -> str:
        pass

    @abstractmethod
    def evaluate(self, context: INPCContext) -> float:
        pass

    @abstractmethod
    def select_action(self, context: INPCContext) -> Optional[IAction]:
        pass


class IStrategyExecutor(ABC):
    @abstractmethod
    def set_strategy(self, strategy: IStrategy):
        pass

    @abstractmethod
    def get_current_strategy(self) -> Optional[IStrategy]:
        pass

    @abstractmethod
    def execute(self, context: INPCContext) -> Optional[IAction]:
        pass

    @abstractmethod
    def reset(self):
        pass


class StrategyExecutor(IStrategyExecutor):
    def __init__(self):
        self._current_strategy: Optional[IStrategy] = None
        self._available_strategies: List[IStrategy] = []

    def set_strategy(self, strategy: IStrategy):
        self._current_strategy = strategy
        game_logger.debug(f"Strategy changed to: {strategy.strategy_name}")

    def get_current_strategy(self) -> Optional[IStrategy]:
        return self._current_strategy

    def execute(self, context: INPCContext) -> Optional[IAction]:
        if not self._current_strategy:
            game_logger.warn("No strategy set, using default")
            return None
        try:
            return self._current_strategy.select_action(context)
        except Exception as ex:
            raise StrategyExecutionException(self._current_strategy.strategy_name, ex)

    def reset(self):
        self._current_strategy = None

    def register_strategy(self, strategy: IStrategy):
        self._available_strategies.append(strategy)


# ========== Concrete Strategies ==========

class AggressiveStrategy(IStrategy):
    @property
    def strategy_name(self) -> str:
        return "Aggressive"

    def evaluate(self, context: INPCContext) -> float:
        return 0.8

    def select_action(self, context: INPCContext) -> Optional[IAction]:
        return AttackAction()


class DefensiveStrategy(IStrategy):
    @property
    def strategy_name(self) -> str:
        return "Defensive"

    def evaluate(self, context: INPCContext) -> float:
        return 0.6

    def select_action(self, context: INPCContext) -> Optional[IAction]:
        return DefendAction()


class EscapeStrategy(IStrategy):
    @property
    def strategy_name(self) -> str:
        return "Escape"

    def evaluate(self, context: INPCContext) -> float:
        return 0.5

    def select_action(self, context: INPCContext) -> Optional[IAction]:
        return FleeAction()


class PatrolStrategy(IStrategy):
    @property
    def strategy_name(self) -> str:
        return "Patrol"

    def evaluate(self, context: INPCContext) -> float:
        return 0.9

    def select_action(self, context: INPCContext) -> Optional[IAction]:
        return MoveAction()


class MerchantStrategy(IStrategy):
    @property
    def strategy_name(self) -> str:
        return "Merchant"

    def evaluate(self, context: INPCContext) -> float:
        return 0.95

    def select_action(self, context: INPCContext) -> Optional[IAction]:
        from Core.enums import EventType
        for sense in context.sense_results:
            if sense.sense_type == EventType.SENSE_PLAYER_DETECTED:
                return GreetAction()
        return OrganizeGoodsAction()


# ========== Concrete Actions ==========

class AttackAction(IAction):
    @property
    def action_name(self) -> str:
        return "Attack"

    def execute(self, context: INPCContext):
        game_logger.info(f"[{context.npc_id}] Performing Attack action")


class DefendAction(IAction):
    @property
    def action_name(self) -> str:
        return "Defend"

    def execute(self, context: INPCContext):
        game_logger.info(f"[{context.npc_id}] Performing Defend action")


class FleeAction(IAction):
    @property
    def action_name(self) -> str:
        return "Flee"

    def execute(self, context: INPCContext):
        game_logger.info(f"[{context.npc_id}] Performing Flee action")


class MoveAction(IAction):
    @property
    def action_name(self) -> str:
        return "Move"

    def execute(self, context: INPCContext):
        game_logger.info(f"[{context.npc_id}] Performing Move action")


class GreetAction(IAction):
    @property
    def action_name(self) -> str:
        return "Greet"

    def execute(self, context: INPCContext):
        game_logger.info(f"[{context.npc_id}] Performing Greet action - welcoming customer")


class OrganizeGoodsAction(IAction):
    @property
    def action_name(self) -> str:
        return "OrganizeGoods"

    def execute(self, context: INPCContext):
        game_logger.info(f"[{context.npc_id}] Performing OrganizeGoods action - arranging merchandise")


class StrategyFactory:
    _strategy_classes = {}
    _strategy_singletons = {}

    @classmethod
    def register_strategy(cls, strategy_name: str, strategy_class):
        cls._strategy_classes[strategy_name] = strategy_class
        if strategy_name in cls._strategy_singletons:
            del cls._strategy_singletons[strategy_name]

    @classmethod
    def create_strategy(cls, strategy_name: str) -> IStrategy:
        strategy_class = cls._strategy_classes.get(strategy_name)
        if not strategy_class:
            game_logger.warn(f"Strategy [{strategy_name}] not found, using AggressiveStrategy")
            return AggressiveStrategy()
        return strategy_class()

    @classmethod
    def get_strategy(cls, strategy_name: str) -> Optional[IStrategy]:
        if strategy_name not in cls._strategy_singletons:
            strategy_class = cls._strategy_classes.get(strategy_name)
            if not strategy_class:
                game_logger.warn(f"Strategy [{strategy_name}] not found")
                return None
            cls._strategy_singletons[strategy_name] = strategy_class()
        return cls._strategy_singletons[strategy_name]

    @classmethod
    def get_available_strategies(cls) -> list:
        return list(cls._strategy_classes.keys())


StrategyFactory.register_strategy("Aggressive", AggressiveStrategy)
StrategyFactory.register_strategy("Defensive", DefensiveStrategy)
StrategyFactory.register_strategy("Escape", EscapeStrategy)
StrategyFactory.register_strategy("Patrol", PatrolStrategy)
StrategyFactory.register_strategy("Merchant", MerchantStrategy)
