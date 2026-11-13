"""
渲染器接口
定义游戏渲染层的抽象接口，支持多种渲染后端（tkinter等）
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple


class IGameRenderer(ABC):
    """游戏渲染器接口"""

    @abstractmethod
    def init(self, width: int, height: int, title: str) -> bool:
        """初始化渲染器"""
        pass

    @abstractmethod
    def set_map_data(self, tiles: List[List[int]], tile_size: int):
        """设置地图数据"""
        pass

    @abstractmethod
    def set_poison_zones(self, zones: List[Tuple[int, int, int, int]]):
        """设置毒雾区域"""
        pass

    @abstractmethod
    def update_entities(self, entities: List[Dict[str, Any]]):
        """更新实体（玩家、NPC）"""
        pass

    @abstractmethod
    def show_dialogue(self, npc_name: str, text: str, options: List[str]):
        """显示对话框"""
        pass

    @abstractmethod
    def hide_dialogue(self):
        """隐藏对话框"""
        pass

    @abstractmethod
    def update_ui(self, player_hp: int, player_max_hp: int,
                  player_x: int, player_y: int, player_gold: int,
                  npc_list: List[Dict[str, Any]]):
        """更新UI面板

        Args:
            player_hp: 当前生命
            player_max_hp: 最大生命
            player_x: 玩家x坐标
            player_y: 玩家y坐标
            player_gold: 金币
            npc_list: NPC列表，每个包含id/type/x/y/state
        """
        pass

    @abstractmethod
    def set_key_handler(self, handler):
        """设置按键事件处理器"""
        pass

    @abstractmethod
    def run(self):
        """运行主循环（阻塞）"""
        pass

    @abstractmethod
    def shutdown(self):
        """关闭渲染器"""
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """是否在运行"""
        pass
