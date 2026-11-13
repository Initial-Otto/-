from abc import ABC, abstractmethod
from typing import List
from Core.enums import EventType, BTResult
from Utility import EventData, IEventObserver


# ========== State Pattern ==========

class IState(ABC):
    @property
    @abstractmethod
    def state_name(self) -> str:
        pass

    @property
    def display_name(self) -> str:
        return self.state_name

    @abstractmethod
    def enter(self, context: 'INPCContext'):
        pass

    @abstractmethod
    def update(self, context: 'INPCContext', delta_time: float):
        pass

    @abstractmethod
    def exit(self, context: 'INPCContext'):
        pass

    @abstractmethod
    def try_transition(self, context: 'INPCContext') -> 'IState':
        pass


class INPCContext(ABC):
    @property
    @abstractmethod
    def npc_id(self) -> str:
        pass

    @property
    @abstractmethod
    def npc_type(self) -> str:
        pass

    @property
    @abstractmethod
    def current_state(self) -> IState:
        pass

    @property
    @abstractmethod
    def sense_results(self) -> List['SenseResult']:
        pass

    @sense_results.setter
    @abstractmethod
    def sense_results(self, value: List['SenseResult']):
        pass

    @abstractmethod
    def set_state(self, new_state: IState):
        pass

    @abstractmethod
    def set_strategy(self, strategy_name: str) -> bool:
        pass

    @abstractmethod
    def get_strategy_executor(self):
        pass

    @abstractmethod
    def get_action_service(self):
        pass

    @abstractmethod
    def set_action_service(self, action_service):
        pass

    @abstractmethod
    def notify_observers(self, event_type: EventType, data=None):
        pass


class NPCContext(INPCContext):
    def __init__(self, npc_id: str, event_bus, npc_type: str = "Guard",
                 strategy_executor=None, action_service=None):
        self._npc_id = npc_id
        self._npc_type = npc_type
        self._current_state = None
        self._sense_results = []
        self._observers: List[IEventObserver] = []
        self._event_bus = event_bus
        self._strategy_executor = strategy_executor
        self._action_service = action_service

    @property
    def npc_id(self) -> str:
        return self._npc_id

    @property
    def npc_type(self) -> str:
        return self._npc_type

    @property
    def current_state(self) -> IState:
        return self._current_state

    @property
    def sense_results(self):
        return self._sense_results

    @sense_results.setter
    def sense_results(self, value):
        self._sense_results = value

    def set_state(self, new_state: IState):
        old_state = self._current_state
        if old_state:
            old_state.exit(self)

        self._current_state = new_state
        new_state.enter(self)

        from Utility.Logger.logger import game_logger
        old_name = old_state.state_name if old_state else "None"
        game_logger.info(f"[{self._npc_id}] State changed: {old_name} -> {new_state.state_name}")

        self.notify_observers(EventType.STATE_CHANGED, new_state.state_name)

    def set_strategy(self, strategy_name: str) -> bool:
        if not self._strategy_executor:
            return False
        from .strategy import StrategyFactory
        strategy = StrategyFactory.get_strategy(strategy_name)
        if strategy is None:
            return False
        self._strategy_executor.set_strategy(strategy)
        return True

    def get_strategy_executor(self):
        return self._strategy_executor

    def get_action_service(self):
        return self._action_service

    def set_action_service(self, action_service):
        self._action_service = action_service

    def add_observer(self, observer: IEventObserver):
        self._observers.append(observer)

    def notify_observers(self, event_type: EventType, data=None):
        event_data = EventData(event_type, self, data)
        for observer in self._observers:
            try:
                observer.on_event(event_data)
            except Exception as ex:
                from Utility.Logger.logger import game_logger
                game_logger.error(f"Observer notification error: {ex}", ex)


# ========== Concrete States ==========

class AlertState(IState):
    """警戒状态：发现玩家，保持追逐直到玩家离开范围"""
    def __init__(self):
        self._lost_timer = 0.0
        self._lost_timeout = 2.0  # 失去目标2秒后返回巡逻

    @property
    def state_name(self) -> str:
        return "Alert"

    def enter(self, context: INPCContext):
        from Utility.Logger.logger import game_logger
        game_logger.debug(f"[{context.npc_id}] Entering Alert state")
        context.set_strategy("Defensive")
        self._lost_timer = 0.0

    def update(self, context: INPCContext, delta_time: float):
        action_service = context.get_action_service()
        if action_service:
            action_service.move_towards_player(context.npc_id)
        self._lost_timer += delta_time

    def exit(self, context: INPCContext):
        pass

    def try_transition(self, context: INPCContext) -> IState:
        detected = False
        for sense in context.sense_results:
            if sense.sense_type == EventType.SENSE_PLAYER_DETECTED:
                detected = True
                self._lost_timer = 0.0
        
        if not detected and self._lost_timer >= self._lost_timeout:
            return StateFactory.create_state("Patrol")
        
        return None


class PatrolState(IState):
    @property
    def state_name(self) -> str:
        return "Patrol"

    def enter(self, context: INPCContext):
        from Utility.Logger.logger import game_logger
        game_logger.debug(f"[{context.npc_id}] Entering Patrol state")
        context.set_strategy("Patrol")

    def update(self, context: INPCContext, delta_time: float):
        action_service = context.get_action_service()
        if action_service:
            action_service.move_random(context.npc_id)

    def exit(self, context: INPCContext):
        pass

    def try_transition(self, context: INPCContext) -> IState:
        for sense in context.sense_results:
            if sense.sense_type == EventType.SENSE_PLAYER_DETECTED:
                return StateFactory.create_state("Alert")
        # 没有检测到玩家 -> 保持 Patrol（守卫一直巡逻）
        return None


class DialogState(IState):
    def __init__(self, previous_state: IState = None):
        self._previous_state = previous_state
        self._return_state = "Patrol"  # 对话结束后默认返回状态（守卫）

    @property
    def state_name(self) -> str:
        return "Dialog"

    @property
    def previous_state(self) -> IState:
        return self._previous_state

    def set_return_state(self, state_name: str):
        """设置对话结束后返回的状态"""
        self._return_state = state_name

    def enter(self, context: INPCContext):
        from Utility.Logger.logger import game_logger
        game_logger.debug(f"[{context.npc_id}] Entering Dialog state")
        context.notify_observers(EventType.DIALOGUE_STARTED)

    def update(self, context: INPCContext, delta_time: float):
        pass

    def exit(self, context: INPCContext):
        context.notify_observers(EventType.DIALOGUE_ENDED)

    def try_transition(self, context: INPCContext) -> IState:
        for sense in context.sense_results:
            if sense.sense_type == EventType.DIALOGUE_ENDED:
                if self._previous_state:
                    return self._previous_state
                return StateFactory.create_state(self._return_state)
        return None


class GreetState(IState):
    """揽客状态：商人发现玩家后停下招揽，玩家离开后返回整理货物"""
    def __init__(self):
        self._lost_timer = 0.0
        self._lost_timeout = 1.5  # 玩家离开1.5秒后返回整理货物

    @property
    def state_name(self) -> str:
        return "Greet"

    def enter(self, context: INPCContext):
        from Utility.Logger.logger import game_logger
        game_logger.debug(f"[{context.npc_id}] Entering Greet state - greeting customer")
        context.set_strategy("Merchant")
        self._lost_timer = 0.0

    def update(self, context: INPCContext, delta_time: float):
        # 揽客时停下不动
        self._lost_timer += delta_time

    def exit(self, context: INPCContext):
        pass

    def try_transition(self, context: INPCContext) -> IState:
        detected = False
        for sense in context.sense_results:
            if sense.sense_type == EventType.SENSE_PLAYER_DETECTED:
                detected = True
                self._lost_timer = 0.0
        
        if not detected and self._lost_timer >= self._lost_timeout:
            return StateFactory.create_state("Organize")
        
        return None


class OrganizeState(IState):
    """整理货物状态：商人在摊位附近走动（移动频率与守卫巡逻一致，由ActionService冷却控制）"""

    @property
    def state_name(self) -> str:
        return "Organize"

    def enter(self, context: INPCContext):
        from Utility.Logger.logger import game_logger
        game_logger.debug(f"[{context.npc_id}] Entering Organize state - arranging goods")
        context.set_strategy("Merchant")

    def update(self, context: INPCContext, delta_time: float):
        action_service = context.get_action_service()
        if action_service:
            action_service.move_random(context.npc_id)

    def exit(self, context: INPCContext):
        pass

    def try_transition(self, context: INPCContext) -> IState:
        for sense in context.sense_results:
            if sense.sense_type == EventType.SENSE_PLAYER_DETECTED:
                return StateFactory.create_state("Greet")
        return None


class RestState(IState):
    """休息状态：NPC周期性休息，休息时不移动"""
    def __init__(self):
        self._rest_duration = 3.0      # 休息持续时间（秒）
        self._rest_timer = 0.0
        self._return_state = "Patrol"  # 休息结束后返回的状态（守卫默认）
        self._interval_timer = 0.0     # 距离下次休息的计时
        self._enabled = True           # 是否启用

    @property
    def state_name(self) -> str:
        return "Rest"

    @property
    def rest_timer(self) -> float:
        return self._rest_timer

    @rest_timer.setter
    def rest_timer(self, value: float):
        self._rest_timer = value

    @property
    def rest_duration(self) -> float:
        return self._rest_duration

    @rest_duration.setter
    def rest_duration(self, value: float):
        self._rest_duration = value

    @property
    def interval_timer(self) -> float:
        return self._interval_timer

    @interval_timer.setter
    def interval_timer(self, value: float):
        self._interval_timer = value

    def set_return_state(self, state_name: str):
        """设置休息结束后返回的状态"""
        self._return_state = state_name

    def set_enabled(self, enabled: bool):
        """设置是否启用休息"""
        self._enabled = enabled

    def enter(self, context: INPCContext):
        from Utility.Logger.logger import game_logger
        game_logger.debug(f"[{context.npc_id}] Entering Rest state - resting for {self._rest_duration}s")
        self._rest_timer = 0.0

    def update(self, context: INPCContext, delta_time: float):
        self._rest_timer += delta_time

    def exit(self, context: INPCContext):
        from Utility.Logger.logger import game_logger
        game_logger.debug(f"[{context.npc_id}] Exiting Rest state after {self._rest_timer:.1f}s")

    def try_transition(self, context: INPCContext) -> IState:
        # 休息时间到，返回指定状态
        if self._rest_timer >= self._rest_duration:
            return StateFactory.create_state(self._return_state)
        return None

    def can_enter_rest(self, current_state: str) -> bool:
        """检查当前状态是否可以进入休息"""
        # 追击/警戒/战斗/招揽/中毒状态下不允许休息
        REST_BLOCKED_STATES = {"Alert", "Greet", "Dialog", "Poisoned"}
        return current_state not in REST_BLOCKED_STATES

    def should_rest(self) -> bool:
        """检查是否应该进入休息（间隔计时是否到）"""
        if not self._enabled:
            return False
        return self._interval_timer <= 0


class PoisonedState(IState):
    """中毒状态装饰器（装饰器模式）：包装其他状态，添加中毒效果
    - 移动速度减慢
    - 不能进入休息状态
    - 商人中毒时不与玩家交互（不揽客、不对话）
    - 内部状态正常转换（如 Patrol → Alert 仍然可以）
    """
    def __init__(self, inner_state: IState = None):
        # 如果没传内部状态，默认包一个PatrolState（用于工厂方法创建）
        if inner_state is None:
            inner_state = PatrolState()
        self._inner_state = inner_state      # 被装饰的内部状态
        self._recovery_duration = 3.0        # 中毒解除时间（秒）
        self._recovery_timer = 0.0
        self._in_poison_zone = True          # 是否仍在毒雾中
        self._slow_factor = 2.4              # 移动速度变为原来的 1/slow_factor
        self._original_action_service = None # 保存原始 action_service

    @property
    def state_name(self) -> str:
        return "Poisoned"

    @property
    def display_name(self) -> str:
        return f"{self._inner_state.display_name}（Poisoned）"

    @property
    def inner_state(self) -> IState:
        return self._inner_state

    def set_in_poison_zone(self, in_zone: bool):
        self._in_poison_zone = in_zone

    def enter(self, context: INPCContext):
        from Utility.Logger.logger import game_logger
        game_logger.debug(f"[{context.npc_id}] 进入 Poisoned 中毒状态（装饰 {self._inner_state.state_name}）")
        context.notify_observers(EventType.POISONED)
        self._recovery_timer = 0.0

        # 包装 action_service 实现减速
        original = context.get_action_service()
        if original and not isinstance(original, _SlowActionServiceDecorator):
            self._original_action_service = original
            context.set_action_service(_SlowActionServiceDecorator(original, self._slow_factor))

        # 进入内部状态
        self._inner_state.enter(context)

    def update(self, context: INPCContext, delta_time: float):
        if self._in_poison_zone:
            self._recovery_timer = 0.0
        else:
            self._recovery_timer += delta_time

        # 商人中毒时不与玩家交互：过滤掉玩家检测的感知
        if self._is_merchant(context):
            filtered = [s for s in context.sense_results
                        if s.sense_type not in (EventType.SENSE_PLAYER_DETECTED,)]
            context.sense_results = filtered

        # 内部状态正常更新
        self._inner_state.update(context, delta_time)

    def exit(self, context: INPCContext):
        from Utility.Logger.logger import game_logger
        game_logger.debug(f"[{context.npc_id}] 解除 Poisoned 中毒状态")
        context.notify_observers(EventType.POISON_RECOVERY)

        # 恢复原始 action_service
        if self._original_action_service:
            context.set_action_service(self._original_action_service)
            self._original_action_service = None

        # 内部状态 exit 不需要调用（因为返回后外部会再 enter 一次）
        # 但为了对称，这里调用一下
        self._inner_state.exit(context)

    def try_transition(self, context: INPCContext) -> IState:
        # 商人中毒时：拦截 SENSE_PLAYER_DETECTED，防止进入 Greet/Dialog
        if self._is_merchant(context):
            filtered = [s for s in context.sense_results
                        if s.sense_type not in (EventType.SENSE_PLAYER_DETECTED,)]
            original_sense = context.sense_results
            context.sense_results = filtered

            inner_new = self._inner_state.try_transition(context)

            context.sense_results = original_sense
        else:
            inner_new = self._inner_state.try_transition(context)

        # 如果内部状态想转换
        if inner_new:
            # 中毒时不能进入休息状态
            if inner_new.state_name == "Rest":
                pass
            else:
                # 切换内部状态，保持中毒装饰
                self._inner_state.exit(context)
                self._inner_state = inner_new
                self._inner_state.enter(context)

        # 检查中毒是否解除
        if not self._in_poison_zone and self._recovery_timer >= self._recovery_duration:
            # 解除中毒，返回内部状态
            # 先 exit（会恢复 action_service）
            self._original_action_service = None  # 防止 exit 里重复恢复
            return self._inner_state

        return None

    def _is_merchant(self, context: INPCContext) -> bool:
        return context.npc_type == "merchant"


class _SlowActionServiceDecorator:
    """ActionService 减速装饰器（装饰器模式）
    把所有移动操作的间隔拉长，实现减速效果
    """
    def __init__(self, inner_service, slow_factor: float = 2.0):
        self._inner = inner_service
        self._slow_factor = slow_factor
        self._move_cooldown = {}  # npc_id -> remaining cooldown

    def move_towards_player(self, npc_id: str):
        if self._try_move(npc_id):
            self._inner.move_towards_player(npc_id)

    def move_towards(self, npc_id: str, target):
        if self._try_move(npc_id):
            self._inner.move_towards(npc_id, target)

    def move_random(self, npc_id: str):
        if self._try_move(npc_id):
            self._inner.move_random(npc_id)

    def move_random_in_range(self, npc_id: str, center, radius: float):
        if self._try_move(npc_id):
            self._inner.move_random_in_range(npc_id, center, radius)

    def attack_player(self, npc_id: str):
        self._inner.attack_player(npc_id)

    def stay(self, npc_id: str):
        self._inner.stay(npc_id)

    def _try_move(self, npc_id: str) -> bool:
        """每 slow_factor 次调用才允许一次真正的移动"""
        current = self._move_cooldown.get(npc_id, 0.0)
        current += 1.0  # 每次调用计 1 单位
        if current >= self._slow_factor:
            self._move_cooldown[npc_id] = 0.0
            return True
        self._move_cooldown[npc_id] = current
        return False


class StateFactory:
    _state_classes = {}

    @classmethod
    def register_state(cls, state_name: str, state_class):
        cls._state_classes[state_name] = state_class

    @classmethod
    def create_state(cls, state_name: str) -> IState:
        state_class = cls._state_classes.get(state_name)
        if not state_class:
            from Utility.Logger.logger import game_logger
            game_logger.warn(f"State [{state_name}] not found, using PatrolState")
            return PatrolState()
        return state_class()

    @classmethod
    def get_available_states(cls) -> list:
        return list(cls._state_classes.keys())


StateFactory.register_state("Alert", AlertState)
StateFactory.register_state("Patrol", PatrolState)
StateFactory.register_state("Dialog", DialogState)
StateFactory.register_state("Greet", GreetState)
StateFactory.register_state("Organize", OrganizeState)
StateFactory.register_state("Rest", RestState)
StateFactory.register_state("Poisoned", PoisonedState)
