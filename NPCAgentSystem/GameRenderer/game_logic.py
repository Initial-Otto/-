"""
游戏逻辑核心 - 与渲染层完全解耦
100% 复用原 MagicTowerGame 的游戏逻辑，只替换渲染调用
保证 NPC 行为、状态转换、移动逻辑与原版本完全一致
"""
import os
import sys
import time
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Core.enums import NPCType
from Core.vector import Vector2
from Utility import EventBus
from Business import NPCManager
from Business.Dialogue.dialogue_manager import DialogueManager, DialogueFactory
from GameRenderer.renderer_interface import IGameRenderer
from Utility.Logger.logger import game_logger

from magic_tower_game import (
    generate_magic_tower_map,
    is_walkable,
    CONFIG,
    ColorPalette,
    TILE_FLOOR,
    TILE_WALL,
)


class GameLogic:
    """游戏逻辑核心 - 与原 MagicTowerGame 行为完全一致"""

    def __init__(self, renderer: IGameRenderer):
        self._renderer = renderer
        self._running = False

        # ===== 以下变量与原 MagicTowerGame 完全一致 =====
        self.game_map = []
        self.player = Vector2(CONFIG.player_start_x, CONFIG.player_start_y)
        self.player_hp = 100
        self.player_max_hp = 100
        self.player_gold = CONFIG.player_start_gold

        self.event_bus = EventBus()
        self.npc_manager = NPCManager(self.event_bus)
        self.dialogue_manager = DialogueManager()
        self.dialogue_tree = None

        self.in_dialogue = False
        self.dialogue_npc = None

        self.last_npc_move = time.time()
        self.last_guard_move = time.time()
        self.frame_count = 0

        self._entity_dirty = True
        self._prev_player_pos = None
        self._prev_npc_positions = {}
        self._prev_npc_states = {}

        self._rest_timers = {}
        self._ui_dirty = True
        self._dialogue_dirty = False
        self._prev_dialogue_state = False

        # 毒雾相关
        self._poison_state_map = {}  # npc_id -> 是否在毒雾中
        self._poison_zones = CONFIG.poison_zones if CONFIG.poison_enabled else []

    def init(self) -> bool:
        """初始化游戏逻辑（与原 MagicTowerGame.__init__ 逻辑一致）"""
        try:
            self.game_map = generate_magic_tower_map()
            self._create_npcs()
            self._init_rest_timers()

            self._renderer.set_key_handler(self._on_key_press)

            # 发送初始数据给渲染器
            self._renderer.set_map_data(self.game_map, CONFIG.tile_size)
            # 设置毒雾区域
            if CONFIG.poison_enabled:
                self._renderer.set_poison_zones(CONFIG.poison_zones)
            self._draw_entities()
            self._draw_ui()

            game_logger.info("GameLogic initialized")
            return True

        except Exception as e:
            game_logger.error(f"GameLogic init failed: {e}", e)
            return False

    def _create_npcs(self):
        """创建NPC（与原代码完全一致）"""
        guard1 = self.npc_manager.create_npc("Guard_001", NPCType.GUARD)
        guard1.position = Vector2(15, 3)

        guard2 = self.npc_manager.create_npc("Guard_002", NPCType.GUARD)
        guard2.position = Vector2(25, 9)

        merchant = self.npc_manager.create_npc("Merchant_001", NPCType.MERCHANT)
        merchant.position = Vector2(5, 15)
        merchant.home_pos = Vector2(5, 15)

        for npc in self.npc_manager.get_all_npcs():
            npc.initialize_brain(self.event_bus)

        merchant_dialogue = DialogueFactory.create_merchant_dialogue("Merchant_001")
        self.dialogue_manager.register_dialogue(merchant_dialogue)

        guard1_dialogue = DialogueFactory.create_guard_dialogue("Guard_001")
        self.dialogue_manager.register_dialogue(guard1_dialogue)

        guard2_dialogue = DialogueFactory.create_guard_dialogue("Guard_002")
        self.dialogue_manager.register_dialogue(guard2_dialogue)

    def _init_rest_timers(self):
        """初始化NPC休息计时器（与原代码完全一致）"""
        for npc in self.npc_manager.get_all_npcs():
            if npc.config.rest_enabled:
                self._rest_timers[npc.npc_id] = random.uniform(
                    npc.config.rest_interval * 0.5,
                    npc.config.rest_interval
                )
            else:
                self._rest_timers[npc.npc_id] = -1

    # ========== 输入处理（与原代码完全一致）==========

    def _on_key_press(self, key: str, pressed: bool):
        """键盘事件（与原 MagicTowerGame._on_key_press 逻辑完全一致）"""
        if not pressed:
            return

        key = key.lower()

        if key == 'q' or key == 'escape':
            if self.in_dialogue:
                self._end_dialogue()
                return
            self._running = False
            return

        if self.in_dialogue:
            self._handle_dialogue_input(key)
            return

        if key == 'e':
            self._try_interact()
            return

        dx = 0
        dy = 0

        if key in ('w', 'up', 'arrowup'):
            dy = -1
        elif key in ('s', 'down', 'arrowdown'):
            dy = 1
        elif key in ('a', 'left', 'arrowleft'):
            dx = -1
        elif key in ('d', 'right', 'arrowright'):
            dx = 1

        if dx != 0 or dy != 0:
            nx = int(self.player.x) + dx
            ny = int(self.player.y) + dy
            if is_walkable(self.game_map, nx, ny):
                self.player.x = nx
                self.player.y = ny
                self._entity_dirty = True
                self._ui_dirty = True

    def _try_interact(self):
        """尝试与附近的NPC交互（与原代码完全一致）"""
        for npc in self.npc_manager.get_all_npcs():
            dx = self.player.x - npc.position.x
            dy = self.player.y - npc.position.y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist <= CONFIG.interact_distance:
                self._start_dialogue(npc)
                return

    def _start_dialogue(self, npc):
        """开始对话（与原代码完全一致）"""
        dialogue_id = f"{'merchant' if npc.npc_type == NPCType.MERCHANT else 'guard'}_greeting"
        self.dialogue_tree = self.dialogue_manager.get_dialogue(dialogue_id)
        if self.dialogue_tree:
            self.in_dialogue = True
            self.dialogue_npc = npc
            npc.brain_state = "Dialog"
            self.dialogue_manager.start_dialogue(npc.npc_id, dialogue_id)
            self._dialogue_dirty = True
            self._entity_dirty = True

    def _end_dialogue(self):
        """结束对话（与原代码完全一致）"""
        if self.dialogue_npc:
            npc = self.dialogue_npc
            if npc.npc_type == NPCType.MERCHANT:
                dx = self.player.x - npc.position.x
                dy = self.player.y - npc.position.y
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < CONFIG.merchant_dialogue_end_greet_range:
                    npc.brain_state = "Greet"
                else:
                    npc.brain_state = "Organize"
            else:
                npc.brain_state = "Idle"
            self.dialogue_npc = None
        self.in_dialogue = False
        self.dialogue_tree = None
        self.dialogue_manager.end_dialogue()
        self._dialogue_dirty = True
        self._entity_dirty = True
        self._ui_dirty = True

    def _handle_dialogue_input(self, key):
        """处理对话中的输入（与原代码完全一致）"""
        if not self.dialogue_tree or not self.dialogue_tree.current_node:
            return

        options = self.dialogue_tree.current_node.options
        num_options = len(options)

        if key.isdigit():
            idx = int(key) - 1
            if 0 <= idx < num_options:
                self.dialogue_tree.select_option(idx)
                self._dialogue_dirty = True
                if not self.dialogue_tree.current_node.options:
                    self._end_dialogue()
                return

        if key in ('return', 'space'):
            if num_options > 0:
                self.dialogue_tree.select_option(0)
                self._dialogue_dirty = True
                if not self.dialogue_tree.current_node.options:
                    self._end_dialogue()

    # ========== NPC AI 更新（与原代码完全一致）==========

    def _update_npcs(self):
        """更新NPC AI（与原 MagicTowerGame._update_npcs 完全一致）"""
        now = time.time()

        self._update_rest_state(now)
        self._update_poison_state()

        for npc in self.npc_manager.get_all_npcs():
            npc.update()

        # 商人移动
        if now - self.last_npc_move >= CONFIG.npc_move_interval:
            self.last_npc_move = now
            for npc in self.npc_manager.get_all_npcs():
                if npc.brain_state in ("Dialog", "Rest"):
                    continue
                if npc.npc_type == NPCType.MERCHANT:
                    old_x, old_y = int(npc.position.x), int(npc.position.y)
                    self._update_merchant(npc)
                    new_x, new_y = int(npc.position.x), int(npc.position.y)
                    if old_x != new_x or old_y != new_y:
                        self._entity_dirty = True

        # 守卫移动
        if now - self.last_guard_move >= CONFIG.guard_move_interval:
            self.last_guard_move = now
            for npc in self.npc_manager.get_all_npcs():
                if npc.brain_state in ("Dialog", "Rest"):
                    continue
                if npc.npc_type == NPCType.GUARD:
                    old_x, old_y = int(npc.position.x), int(npc.position.y)
                    self._update_guard(npc)
                    new_x, new_y = int(npc.position.x), int(npc.position.y)
                    if old_x != new_x or old_y != new_y:
                        self._entity_dirty = True

        self.event_bus.update()

    def _update_rest_state(self, now: float):
        """更新NPC休息状态（与原代码完全一致）"""
        for npc in self.npc_manager.get_all_npcs():
            config = npc.config

            if not config.rest_enabled:
                continue

            rest_state_blocked = {"Alert", "Combat", "Greet", "Dialog", "Poisoned"}
            if npc.brain_state in rest_state_blocked:
                self._rest_timers[npc.npc_id] = config.rest_interval
                continue

            if npc.brain_state == "Rest":
                continue

            timer = self._rest_timers.get(npc.npc_id, -1)
            if timer < 0:
                continue

            timer -= 0.033
            self._rest_timers[npc.npc_id] = timer

            if timer <= 0:
                self._enter_rest_state(npc)

    def _is_in_poison_zone(self, x: float, y: float) -> bool:
        """检查坐标是否在毒雾区域中"""
        if not self._poison_zones:
            return False
        ix, iy = int(x), int(y)
        for x1, y1, x2, y2 in self._poison_zones:
            if x1 <= ix <= x2 and y1 <= iy <= y2:
                return True
        return False

    def _update_poison_state(self):
        """更新NPC中毒状态"""
        if not CONFIG.poison_enabled:
            return

        for npc in self.npc_manager.get_all_npcs():
            in_poison = self._is_in_poison_zone(npc.position.x, npc.position.y)
            self._poison_state_map[npc.npc_id] = in_poison

            # 进入毒雾区域，切换到中毒状态
            if in_poison and npc.brain_state not in ("Poisoned", "Combat", "Dialog"):
                self._enter_poisoned_state(npc)
            # 离开毒雾区域，更新PoisonedState的in_poison_zone状态
            elif not in_poison and npc.brain_state == "Poisoned":
                self._update_poisoned_state(npc, False)

    def _enter_poisoned_state(self, npc):
        """让NPC进入中毒状态"""
        from Agent.Decision.state import StateFactory

        current_state = npc.brain_state
        poisoned_state = StateFactory.create_state("Poisoned")
        poisoned_state.set_return_state(current_state)
        poisoned_state.set_in_poison_zone(True)

        npc._context.set_state(poisoned_state)
        self._entity_dirty = True
        self._ui_dirty = True
        game_logger.info(f"[{npc.npc_id}] 进入毒雾区域，切换到中毒状态")

    def _update_poisoned_state(self, npc, in_zone: bool):
        """更新中毒状态的是否在毒雾中"""
        if npc.brain_state == "Poisoned" and hasattr(npc, '_context') and npc._context:
            state = npc._context.current_state
            if hasattr(state, 'set_in_poison_zone'):
                state.set_in_poison_zone(in_zone)

    def _enter_rest_state(self, npc):
        """让NPC进入休息状态（与原代码完全一致）"""
        from Agent.Decision.state import StateFactory
        config = npc.config

        current_state = npc.brain_state

        rest_state = StateFactory.create_state("Rest")
        rest_state.set_return_state(current_state)
        rest_state.rest_duration = config.rest_duration
        rest_state.set_enabled(config.rest_enabled)

        npc._context.set_state(rest_state)

        self._rest_timers[npc.npc_id] = config.rest_interval + config.rest_duration

        self._entity_dirty = True
        self._ui_dirty = True

    def _update_guard(self, npc):
        """守卫AI：追击玩家（与原代码完全一致）"""
        dx = self.player.x - npc.position.x
        dy = self.player.y - npc.position.y
        dist = (dx * dx + dy * dy) ** 0.5

        if dist < CONFIG.guard_detect_radius:
            if npc.brain_state != "Alert":
                npc.brain_state = "Alert"
                self._ui_dirty = True
            self._move_towards_player(npc, dx, dy)
        else:
            if npc.brain_state != "Patrol":
                npc.brain_state = "Patrol"
                self._ui_dirty = True
            self._move_random(npc)

    def _update_merchant(self, npc):
        """商人AI：招揽顾客 / 整理货物（与原代码完全一致）"""
        if not hasattr(npc, 'home_pos'):
            npc.home_pos = Vector2(int(npc.position.x), int(npc.position.y))

        home = npc.home_pos
        home_radius = CONFIG.merchant_home_radius

        dx = self.player.x - npc.position.x
        dy = self.player.y - npc.position.y
        dist = (dx * dx + dy * dy) ** 0.5

        home_dx = home.x - npc.position.x
        home_dy = home.y - npc.position.y
        home_dist = (home_dx * home_dx + home_dy * home_dy) ** 0.5

        if dist < CONFIG.merchant_detect_radius:
            if npc.brain_state != "Greet":
                npc.brain_state = "Greet"
                self._ui_dirty = True
            if home_dist > home_radius:
                self._move_towards(npc, home.x, home.y)
        else:
            if npc.brain_state != "Organize":
                npc.brain_state = "Organize"
                self._ui_dirty = True
            if random.random() < 0.2:
                if home_dist > home_radius:
                    self._move_towards(npc, home.x, home.y)
                else:
                    self._move_random_in_range(npc, home, home_radius)

    def _move_towards_player(self, npc, dx, dy):
        """向玩家方向移动一格（与原代码完全一致）"""
        if abs(dx) > abs(dy):
            mx = 1 if dx > 0 else -1
            nx = int(npc.position.x) + mx
            ny = int(npc.position.y)
            if is_walkable(self.game_map, nx, ny):
                npc.position.x = nx
        else:
            my = 1 if dy > 0 else -1
            nx = int(npc.position.x)
            ny = int(npc.position.y) + my
            if is_walkable(self.game_map, nx, ny):
                npc.position.y = ny

    def _move_towards(self, npc, target_x, target_y):
        """向目标移动一格（与原代码完全一致）"""
        dx = target_x - npc.position.x
        dy = target_y - npc.position.y

        if abs(dx) > abs(dy):
            mx = 1 if dx > 0 else -1
            nx = int(npc.position.x) + mx
            ny = int(npc.position.y)
            if is_walkable(self.game_map, nx, ny):
                npc.position.x = nx
        elif abs(dy) > 0:
            my = 1 if dy > 0 else -1
            nx = int(npc.position.x)
            ny = int(npc.position.y) + my
            if is_walkable(self.game_map, nx, ny):
                npc.position.y = ny

    def _move_random(self, npc):
        """随机移动一格（与原代码完全一致）"""
        if random.random() < 0.3:
            dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
            mx, my = random.choice(dirs)
            nx = int(npc.position.x) + mx
            ny = int(npc.position.y) + my
            if is_walkable(self.game_map, nx, ny):
                npc.position.x = nx
                npc.position.y = ny

    def _move_random_in_range(self, npc, home, radius):
        """在指定范围内随机移动（与原代码完全一致）"""
        dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        mx, my = random.choice(dirs)
        nx = int(npc.position.x) + mx
        ny = int(npc.position.y) + my
        new_dx = home.x - nx
        new_dy = home.y - ny
        new_dist = (new_dx * new_dx + new_dy * new_dy) ** 0.5
        if new_dist <= radius and is_walkable(self.game_map, nx, ny):
            npc.position.x = nx
            npc.position.y = ny

    # ========== 渲染调用（替换原 canvas 操作）==========

    def _draw_entities(self):
        """绘制实体 - 通过渲染器接口"""
        entities = []

        # 玩家
        entities.append({
            "id": "player",
            "type": "player",
            "x": int(self.player.x),
            "y": int(self.player.y),
            "state": "",
            "name": "Player"
        })

        # NPC
        for npc in self.npc_manager.get_all_npcs():
            npc_type_str = 'guard' if npc.npc_type == NPCType.GUARD else 'merchant'
            entities.append({
                "id": npc.npc_id,
                "type": npc_type_str,
                "x": int(npc.position.x),
                "y": int(npc.position.y),
                "state": npc.brain_state,
                "state_display": npc.brain_display_state,
                "name": npc.npc_id
            })

        self._renderer.update_entities(entities)

    def _draw_ui(self):
        """绘制UI - 通过渲染器接口"""
        npc_list = []
        for npc in self.npc_manager.get_all_npcs():
            npc_type_str = 'guard' if npc.npc_type == NPCType.GUARD else 'merchant'
            npc_list.append({
                "id": npc.npc_id,
                "type": npc_type_str,
                "x": int(npc.position.x),
                "y": int(npc.position.y),
                "state": npc.brain_state,
                "state_display": npc.brain_display_state
            })

        self._renderer.update_ui(
            self.player_hp,
            self.player_max_hp,
            int(self.player.x),
            int(self.player.y),
            self.player_gold,
            npc_list
        )

    def _draw_dialogue_box(self):
        """绘制对话面板 - 通过渲染器接口"""
        if not self.in_dialogue or not self.dialogue_tree or not self.dialogue_tree.current_node:
            self._renderer.hide_dialogue()
            return

        node = self.dialogue_tree.current_node
        options = [opt.option_text for opt in node.options]

        npc_name = self.dialogue_npc.npc_id if self.dialogue_npc else "NPC"
        self._renderer.show_dialogue(npc_name, node.text, options)

    # ========== 主循环 ==========

    def run(self):
        """运行游戏逻辑（在单独线程中）"""
        self._running = True

        try:
            while self._running and self._renderer.is_running:
                try:
                    self._update_npcs()
                except Exception as e:
                    game_logger.error(f"Error in _update_npcs: {e}")
                self.frame_count += 1

                # 实体脏标记检查
                if self._entity_dirty:
                    self._draw_entities()
                    self._entity_dirty = False

                # UI脏标记检查
                if self._ui_dirty:
                    self._draw_ui()
                    self._ui_dirty = False

                # 对话脏标记检查
                if self._dialogue_dirty or self._prev_dialogue_state != self.in_dialogue:
                    self._draw_dialogue_box()
                    self._dialogue_dirty = False
                    self._prev_dialogue_state = self.in_dialogue

                # NPC状态变化检查
                for npc in self.npc_manager.get_all_npcs():
                    prev_state = self._prev_npc_states.get(npc.npc_id)
                    if prev_state != npc.brain_state:
                        self._prev_npc_states[npc.npc_id] = npc.brain_state
                        self._ui_dirty = True
                        self._entity_dirty = True

                time.sleep(0.033)

        except Exception as e:
            game_logger.error(f"GameLogic run error: {e}", e)

        self._running = False
        game_logger.info("GameLogic stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    def shutdown(self):
        self._running = False
