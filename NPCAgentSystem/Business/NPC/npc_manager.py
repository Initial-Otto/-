from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from Core.enums import NPCType, EventType
from Core.vector import Vector2
from Core.config import SETTINGS, NPCConfig
from Utility import IEventBus, EventData, IEventObserver
from Utility.Logger.logger import game_logger
from Agent import (
    NPCBrain, INPCBrain, NPCContext,
    PerceptionComponent, ActionExecutor,
    MoveCommand, AttackCommand, SpeakCommand,
    StateFactory, StrategyFactory,
)


class NPCAttribute:
    """NPC属性（生命值、能量等）"""
    def __init__(self, npc_type: NPCType):
        self.type = npc_type
        self.max_health = 100.0
        self.health = self.max_health
        self.max_energy = 100.0
        self.energy = self.max_energy
        self.level = 1


class INPC(ABC):
    """NPC接口定义"""
    @property
    @abstractmethod
    def npc_id(self) -> str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def npc_type(self) -> NPCType:
        pass

    @property
    @abstractmethod
    def attribute(self) -> NPCAttribute:
        pass

    @property
    @abstractmethod
    def position(self) -> Vector2:
        pass

    @position.setter
    @abstractmethod
    def position(self, value: Vector2):
        pass

    @abstractmethod
    def initialize_brain(self, event_bus: IEventBus):
        pass

    @abstractmethod
    def update(self):
        pass


class NPC(INPC):
    """NPC实体类（业务层实现）"""
    def __init__(self, npc_id: str, name: str, npc_type: NPCType,
                 config: Optional[NPCConfig] = None):
        self._npc_id = npc_id
        self._name = name
        self._type = npc_type
        self._attribute = NPCAttribute(npc_type)
        self._position = Vector2.zero()

        # 使用提供的配置或从全局配置获取
        self._config = config or SETTINGS.get_npc_config(npc_type)

        # AI Agent组件（解耦：只依赖接口）
        self._brain: Optional[INPCBrain] = None
        self._context: Optional[NPCContext] = None
        self._perception: Optional[PerceptionComponent] = None
        self._action_executor: Optional[ActionExecutor] = None
        self._event_bus: Optional[IEventBus] = None

    @property
    def npc_id(self) -> str:
        return self._npc_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def npc_type(self) -> NPCType:
        return self._type

    @property
    def attribute(self) -> NPCAttribute:
        return self._attribute

    @property
    def position(self) -> Vector2:
        return self._position

    @position.setter
    def position(self, value: Vector2):
        self._position = value

    @property
    def config(self) -> NPCConfig:
        """获取NPC配置"""
        return self._config

    @property
    def brain_state(self) -> str:
        """获取当前AI状态名称（用于逻辑判断）"""
        if self._context and self._context.current_state:
            return self._context.current_state.state_name
        return "Unknown"

    @property
    def brain_display_state(self) -> str:
        """获取当前AI状态显示名（用于UI显示）"""
        if self._context and self._context.current_state:
            return self._context.current_state.display_name
        return "Unknown"

    @brain_state.setter
    def brain_state(self, state_name: str):
        """设置AI状态（通过状态机）"""
        if not self._context:
            return
        if self.brain_state == state_name:
            return

        new_state = StateFactory.create_state(state_name)

        # Dialog状态需要特殊处理
        if state_name == "Dialog" and hasattr(new_state, 'set_return_state'):
            # 根据NPC类型设置默认返回状态
            return_state = "Organize" if self._type == NPCType.MERCHANT else "Patrol"
            new_state.set_return_state(return_state)
            new_state._previous_state = self._context.current_state

        self._context.set_state(new_state)

    def initialize_brain(self, event_bus: IEventBus, action_service=None):
        """初始化AI大脑"""
        self._event_bus = event_bus

        self._perception = PerceptionComponent(
            self._npc_id,
            attention_radius=self._config.attention_radius
        )
        self._perception.add_attention_filter(lambda s: s.confidence > 0.3)

        self._action_executor = ActionExecutor()

        from Agent.Decision.strategy import StrategyExecutor, StrategyFactory
        strategy_executor = StrategyExecutor()
        default_strategy = StrategyFactory.get_strategy(self._config.default_strategy)
        if default_strategy:
            strategy_executor.set_strategy(default_strategy)

        npc_type_str = self._type.name.lower()
        self._context = NPCContext(
            self._npc_id, event_bus,
            npc_type=npc_type_str,
            strategy_executor=strategy_executor,
            action_service=action_service
        )
        self._context.add_observer(self._perception)

        default_state = StateFactory.create_state(self._config.default_state)

        self._brain = NPCBrain(strategy_executor=strategy_executor)
        self._brain.set_default_state(default_state)
        self._brain.initialize(self._context, event_bus)

        event_bus.subscribe(EventType.SENSE_PLAYER_DETECTED, self._perception)
        event_bus.subscribe(EventType.SENSE_PLAYER_LOST, self._perception)
        event_bus.subscribe(EventType.SENSE_DANGER, self._perception)

        game_logger.info(
            f"[{self._npc_id}] NPC brain initialized as {self._type.name} "
            f"(state={self._config.default_state}, strategy set by state enter)"
        )

    def update(self):
        """更新NPC（业务层调用）"""
        if self._perception:
            self._perception.set_position(self._position)
            self._perception.update()
            if self._context:
                self._context.sense_results = self._perception.get_sense_results()

        self._brain.update(0.016)

        if self._action_executor:
            self._action_executor.update()

    def update_perception(self, player_pos, danger_radius: float = 2.0):
        """直接更新感知（传入玩家位置）"""
        if self._perception:
            self._perception.set_position(self._position)
            self._perception.update_player_position(player_pos, danger_radius)

    def move_to(self, target: Vector2):
        """移动命令"""
        if self._action_executor:
            cmd = MoveCommand(self._npc_id, target)
            self._action_executor.execute_command(cmd)

    def attack(self, target_id: str):
        """攻击命令"""
        if self._action_executor:
            cmd = AttackCommand(self._npc_id, target_id)
            self._action_executor.execute_command(cmd)

    def speak(self, dialogue_id: str):
        """对话命令"""
        if self._action_executor:
            cmd = SpeakCommand(self._npc_id, dialogue_id)
            self._action_executor.execute_command(cmd)


class INPCManager(ABC):
    @abstractmethod
    def create_npc(self, npc_id: str, npc_type: NPCType) -> INPC:
        pass

    @abstractmethod
    def get_npc(self, npc_id: str) -> Optional[INPC]:
        pass

    @abstractmethod
    def get_all_npcs(self) -> List[INPC]:
        pass

    @abstractmethod
    def get_npc_count(self) -> int:
        pass

    @abstractmethod
    def update(self):
        pass


class NPCManager(INPCManager):
    def __init__(self, event_bus: IEventBus):
        self._npcs: Dict[str, INPC] = {}
        self._event_bus = event_bus

    def create_npc(self, npc_id: str, npc_type: NPCType) -> INPC:
        if npc_id in self._npcs:
            game_logger.warn(f"NPC with id [{npc_id}] already exists")
            return self._npcs[npc_id]

        npc = NPC(npc_id, f"NPC_{npc_type.name}_{npc_id}", npc_type)
        self._npcs[npc_id] = npc

        self._event_bus.notify(EventData(EventType.NPC_CREATED, self))
        game_logger.info(f"Created NPC: [{npc_id}] of type {npc_type.name}")
        return npc

    def get_npc(self, npc_id: str) -> Optional[INPC]:
        return self._npcs.get(npc_id)

    def get_all_npcs(self) -> List[INPC]:
        return list(self._npcs.values())

    def get_npc_count(self) -> int:
        return len(self._npcs)

    def update(self):
        for npc in self._npcs.values():
            npc.update()


class INPCFactory(ABC):
    @abstractmethod
    def create(self, npc_id: str, npc_type: NPCType) -> INPC:
        pass


class NPCFactory(INPCFactory):
    def create(self, npc_id: str, npc_type: NPCType) -> INPC:
        return NPC(npc_id, f"NPC_{npc_type.name}_{npc_id}", npc_type)
