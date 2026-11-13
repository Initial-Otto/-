from abc import ABC, abstractmethod
from typing import Optional
from .state import IState, INPCContext
from .behavior_tree import IBehaviorTree, BehaviorTreeFactory
from .strategy import IStrategyExecutor, StrategyExecutor
from Utility import IEventBus
from Utility.Logger.logger import game_logger


class INPCBrain(ABC):
    @abstractmethod
    def initialize(self, context: INPCContext, event_bus: IEventBus):
        pass

    @abstractmethod
    def update(self, delta_time: float):
        pass

    @abstractmethod
    def set_default_state(self, state: IState):
        pass

    @abstractmethod
    def get_current_state(self) -> Optional[IState]:
        pass


class NPCBrain(INPCBrain):
    def __init__(self, behavior_tree: Optional[IBehaviorTree] = None,
                 strategy_executor: Optional[IStrategyExecutor] = None):
        self._context: Optional[INPCContext] = None
        self._event_bus: Optional[IEventBus] = None
        self._default_state: Optional[IState] = None
        self._behavior_tree = behavior_tree
        self._strategy_executor = strategy_executor

    def initialize(self, context: INPCContext, event_bus: IEventBus):
        self._context = context
        self._event_bus = event_bus

        if not self._behavior_tree:
            self._behavior_tree = BehaviorTreeFactory.create_standard_npc_tree()

        if not self._strategy_executor:
            self._strategy_executor = StrategyExecutor()

        if not self._default_state:
            from .state import PatrolState
            self._default_state = PatrolState()

        self._context.set_state(self._default_state)

        game_logger.info(
            f"[{context.npc_id}] NPCBrain initialized with state: {self._default_state.state_name}"
        )

    def update(self, delta_time: float):
        if not self._context or not self._context.current_state:
            game_logger.warn("NPCBrain Update called without proper initialization")
            return

        try:
            self._context.current_state.update(self._context, delta_time)

            new_state = self._context.current_state.try_transition(self._context)
            if new_state:
                self._context.set_state(new_state)

            if self._strategy_executor:
                try:
                    action = self._strategy_executor.execute(self._context)
                    if action:
                        action.execute(self._context)
                except Exception as ex:
                    game_logger.debug(f"Strategy execution skipped: {ex}")

        except Exception as ex:
            game_logger.error(f"NPCBrain Update error: {ex}", ex)

    def set_default_state(self, state: IState):
        self._default_state = state

    def get_current_state(self) -> Optional[IState]:
        return self._context.current_state if self._context else None
