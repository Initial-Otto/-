"""
游戏配置管理模块
统一管理所有游戏配置，消除硬编码
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple
from Core.enums import NPCType


@dataclass
class NPCConfig:
    """NPC类型配置"""
    npc_type: NPCType
    default_state: str = "Idle"
    default_strategy: str = "Aggressive"
    attention_radius: float = 500.0
    move_speed: float = 1.0
    # 休息参数
    rest_enabled: bool = True          # 是否启用休息
    rest_interval: float = 10.0        # 休息间隔（秒）
    rest_duration: float = 3.0         # 休息持续时间（秒）


@dataclass
class GameSettings:
    """游戏全局配置"""
    # 地图配置
    tile_size: int = 28
    map_width: int = 40
    map_height: int = 30
    map_seed: int = 12345

    # UI配置
    ui_height: int = 120
    ui_width: int = 280

    # 玩家配置
    player_start_x: int = 2
    player_start_y: int = 2
    player_start_gold: int = 100
    player_max_health: int = 100

    # 交互配置
    interact_distance: float = 2.5

    # NPC行为配置
    guard_move_interval: float = 0.8
    merchant_move_interval: float = 0.2
    guard_detect_radius: float = 8.0
    merchant_detect_radius: float = 4.0
    merchant_home_radius: int = 2
    merchant_dialogue_end_greet_range: float = 5.0

    # 毒雾配置
    poison_enabled: bool = True              # 是否启用毒雾
    poison_recovery_time: float = 3.0      # 中毒解除时间（秒）
    poison_zones: List[Tuple[int, int, int, int]] = field(default_factory=list)  # 毒雾区域列表 (x1, y1, x2, y2)

    # NPC类型配置映射
    npc_configs: Dict[NPCType, NPCConfig] = field(default_factory=dict)

    def __post_init__(self):
        """初始化默认配置"""
        # 初始化毒雾区域
        if not self.poison_zones:
            self.poison_zones = [
                (2, 14, 5, 17),    # 左下毒雾区域
                (11, 7, 19, 11),   # 中部毒雾区域
            ]

        # 初始化NPC配置
        if not self.npc_configs:
            self.npc_configs = {
                NPCType.GUARD: NPCConfig(
                    npc_type=NPCType.GUARD,
                    default_state="Patrol",
                    default_strategy="Aggressive",
                    attention_radius=8.0,
                    rest_enabled=True,
                    rest_interval=10.0,   # 守卫10秒休息一次
                    rest_duration=3.0     # 一次休息3秒
                ),
                NPCType.MERCHANT: NPCConfig(
                    npc_type=NPCType.MERCHANT,
                    default_state="Organize",
                    default_strategy="Merchant",
                    attention_radius=6.0,
                    rest_enabled=True,
                    rest_interval=20.0,   # 商人20秒休息一次
                    rest_duration=5.0     # 一次休息5秒
                ),
                NPCType.QUEST_GIVER: NPCConfig(
                    npc_type=NPCType.QUEST_GIVER,
                    default_state="Idle",
                    default_strategy="Patrol",
                    attention_radius=5.0,
                    rest_enabled=False
                ),
                NPCType.ENEMY: NPCConfig(
                    npc_type=NPCType.ENEMY,
                    default_state="Patrol",
                    default_strategy="Aggressive",
                    attention_radius=10.0,
                    rest_enabled=False
                ),
                NPCType.CIVILIAN: NPCConfig(
                    npc_type=NPCType.CIVILIAN,
                    default_state="Idle",
                    default_strategy="Patrol",
                    attention_radius=4.0,
                    rest_enabled=True,
                    rest_interval=15.0,
                    rest_duration=4.0
                ),
            }

    def get_npc_config(self, npc_type: NPCType) -> NPCConfig:
        """获取指定NPC类型的配置"""
        return self.npc_configs.get(npc_type, NPCConfig(npc_type))

    def update_npc_config(self, npc_type: NPCType, **kwargs):
        """更新指定NPC类型的配置"""
        if npc_type in self.npc_configs:
            config = self.npc_configs[npc_type]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)


# 全局配置实例
SETTINGS = GameSettings()
