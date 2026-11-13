from enum import Enum


class EventType(Enum):
    NONE = 0
    SENSE_PLAYER_DETECTED = 1
    SENSE_PLAYER_LOST = 2
    SENSE_DANGER = 3
    SENSE_ITEM_NEARBY = 4
    STATE_CHANGED = 5
    HEALTH_CHANGED = 6
    ENERGY_CHANGED = 7
    DIALOGUE_STARTED = 8
    DIALOGUE_ENDED = 9
    PLAYER_INTERACTED = 10
    COMBAT_STARTED = 11
    COMBAT_ENDED = 12
    DAMAGE_DEALT = 13
    DAMAGE_RECEIVED = 14
    SCENE_LOADED = 15
    SCENE_UNLOADED = 16
    TICK = 17
    NPC_CREATED = 18
    NPC_DESTROYED = 19
    # 毒雾相关事件
    ENTER_POISON_ZONE = 20      # 进入毒雾区域
    EXIT_POISON_ZONE = 21       # 离开毒雾区域
    POISONED = 22               # 中毒状态开始
    POISON_RECOVERY = 23        # 中毒状态解除


class NPCType(Enum):
    GUARD = 0
    MERCHANT = 1
    QUEST_GIVER = 2
    ENEMY = 3
    CIVILIAN = 4


class BTResult(Enum):
    RUNNING = 0
    SUCCESS = 1
    FAILURE = 2


class DeviceType(Enum):
    PC = 0
    MOBILE = 1
    CONSOLE = 2


class LogLevel(Enum):
    DEBUG = 0
    INFO = 1
    WARN = 2
    ERROR = 3
