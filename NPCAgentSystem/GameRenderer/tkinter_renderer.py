"""
Tkinter 渲染适配器
100% 复用原 magic_tower_game 的绘制函数，视觉效果与原版本完全一致
优化：地图只画一次，实体用 coords 移动，UI 用脏标记更新
"""
import os
import sys
import threading
import tkinter as tk
from tkinter import font as tkfont
from typing import List, Dict, Any, Callable, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from GameRenderer.renderer_interface import IGameRenderer
from magic_tower_game import (
    draw_wall_tile,
    draw_floor_tile,
    draw_player,
    draw_guard,
    draw_merchant,
    ColorPalette,
    CONFIG,
    WIN_W,
    WIN_H,
    TILE_FLOOR,
    TILE_WALL,
)


class TkinterRenderer(IGameRenderer):
    """Tkinter 渲染适配器 - 与原游戏视觉效果完全一致"""

    def __init__(self):
        self._root: Optional[tk.Tk] = None
        self._canvas: Optional[tk.Canvas] = None
        self._running = False
        self._key_handler: Optional[Callable[[str, bool], None]] = None

        self._width = WIN_W
        self._height = WIN_H
        self._title = "NPC Agent System - Magic Tower"
        self._tile_size = CONFIG.tile_size

        self._game_map = []
        self._map_width = CONFIG.map_width
        self._map_height = CONFIG.map_height

        # 实体item缓存
        self._entity_items = {}  # id -> list of canvas item ids
        self._entity_state_items = {}  # id -> state text item id

        # UI元素缓存（静态只画一次，动态更新）
        self._ui_static_drawn = False
        self._ui_dynamic_items = {}  # 动态UI元素
        self._ui_npc_item_pool = []  # NPC列表item池

        # 对话相关
        self._dialogue_visible = False
        self._dialogue_items = []

        # 毒雾区域
        self._poison_zones = []

        self._fonts = {}

        # 线程安全：缓存数据，主线程定时重绘
        self._entities_cache = []
        self._entities_dirty = False
        self._ui_dirty = False
        self._dialogue_data = None
        self._dialogue_hide = False

    def init(self, width: int, height: int, title: str) -> bool:
        self._width = width
        self._height = height
        self._title = title

        self._root = tk.Tk()
        self._root.title(title)
        self._root.configure(bg=ColorPalette.BG)
        self._root.resizable(False, False)

        self._canvas = tk.Canvas(
            self._root,
            width=width,
            height=height,
            bg=ColorPalette.BG,
            highlightthickness=0
        )
        self._canvas.pack()

        # 字体（与原代码一致）
        self._fonts['title'] = tkfont.Font(family='Microsoft YaHei', size=14, weight='bold')
        self._fonts['normal'] = tkfont.Font(family='Microsoft YaHei', size=12)
        self._fonts['small'] = tkfont.Font(family='Microsoft YaHei', size=10)
        self._fonts['tiny'] = tkfont.Font(family='Microsoft YaHei', size=9)

        self._root.bind('<KeyPress>', self._on_key_press)
        self._root.bind('<KeyRelease>', self._on_key_release)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._running = True
        return True

    def set_map_data(self, tiles: List[List[int]], tile_size: int):
        self._game_map = tiles
        self._map_height = len(tiles)
        self._map_width = len(tiles[0]) if tiles else 0
        self._tile_size = tile_size
        self._draw_map()
        self._draw_ui_static()

    def set_poison_zones(self, zones: List[Tuple[int, int, int, int]]):
        self._poison_zones = zones
        self._draw_poison_zones()

    def update_entities(self, entities: List[Dict[str, Any]]):
        # 线程安全：只缓存数据，由主线程定时重绘
        self._entities_cache = entities
        self._entities_dirty = True

        # 如果是在主线程（如初始化阶段），立即绘制
        if threading.current_thread() is threading.main_thread():
            self._do_draw_entities(entities)
            self._entities_dirty = False

    def show_dialogue(self, npc_name: str, text: str, options: List[str]):
        self._dialogue_data = (npc_name, text, options)
        self._dialogue_hide = False
        self._dialogue_dirty = True

        if threading.current_thread() is threading.main_thread():
            self._dialogue_visible = True
            self._dialogue_npc_name = npc_name
            self._dialogue_text = text
            self._dialogue_options = options
            self._redraw_dialogue()
            self._dialogue_dirty = False

    def hide_dialogue(self):
        self._dialogue_hide = True
        self._dialogue_dirty = True

        if threading.current_thread() is threading.main_thread():
            self._dialogue_visible = False
            self._clear_dialogue()
            self._dialogue_dirty = False

    def update_ui(self, player_hp: int, player_max_hp: int,
                  player_x: int, player_y: int, player_gold: int,
                  npc_list: List[Dict[str, Any]]):
        self._player_hp = player_hp
        self._player_max_hp = player_max_hp
        self._player_x = player_x
        self._player_y = player_y
        self._player_gold = player_gold
        self._npc_list = npc_list
        self._ui_dirty = True

        if threading.current_thread() is threading.main_thread():
            if self._ui_static_drawn:
                self._redraw_ui_dynamic()
                self._ui_dirty = False

    def set_key_handler(self, handler: Callable[[str, bool], None]):
        self._key_handler = handler

    def _on_key_press(self, event):
        if self._key_handler:
            self._key_handler(event.keysym, True)

    def _on_key_release(self, event):
        if self._key_handler:
            self._key_handler(event.keysym, False)

    def _on_close(self):
        self._running = False
        if self._root:
            self._root.destroy()

    def run(self):
        if self._root:
            # 启动渲染定时器（主线程中运行）
            self._render_tick()
            self._root.mainloop()

    def _render_tick(self):
        """主线程渲染 tick - 处理脏标记更新"""
        if not self._running or not self._canvas:
            return

        try:
            # 实体脏标记
            if self._entities_dirty:
                self._do_draw_entities(self._entities_cache)
                self._entities_dirty = False

            # UI脏标记
            if self._ui_dirty and self._ui_static_drawn:
                self._redraw_ui_dynamic()
                self._ui_dirty = False

            # 对话脏标记
            if self._dialogue_dirty:
                if self._dialogue_hide:
                    self._dialogue_visible = False
                    self._clear_dialogue()
                elif self._dialogue_data:
                    self._dialogue_visible = True
                    self._dialogue_npc_name = self._dialogue_data[0]
                    self._dialogue_text = self._dialogue_data[1]
                    self._dialogue_options = self._dialogue_data[2]
                    self._redraw_dialogue()
                self._dialogue_dirty = False

        except Exception as e:
            pass

        # 约30fps
        if self._running and self._root:
            self._root.after(33, self._render_tick)

    def shutdown(self):
        self._running = False
        if self._root:
            try:
                self._root.destroy()
            except:
                pass

    @property
    def is_running(self) -> bool:
        return self._running

    # ========== 地图绘制（只画一次）==========

    def _draw_map(self):
        if not self._canvas:
            return

        for y in range(self._map_height):
            for x in range(self._map_width):
                tile = self._game_map[y][x]
                if tile == TILE_WALL:
                    draw_wall_tile(self._canvas, x, y, tag="map")
                else:
                    draw_floor_tile(self._canvas, x, y, tag="map")

    def _draw_poison_zones(self):
        """绘制毒雾区域"""
        if not self._canvas or not self._poison_zones:
            return

        # 删除旧的毒雾
        self._canvas.delete("poison")

        for x1, y1, x2, y2 in self._poison_zones:
            # 绘制毒雾矩形
            px1 = x1 * self._tile_size
            py1 = y1 * self._tile_size
            px2 = (x2 + 1) * self._tile_size
            py2 = (y2 + 1) * self._tile_size

            self._canvas.create_rectangle(
                px1, py1, px2, py2,
                fill="#00aa00",
                outline="#006600",
                stipple="gray50",
                tags="poison"
            )

            # 添加毒雾标记（使用毒性符号）
            center_x = (px1 + px2) // 2
            center_y = (py1 + py2) // 2
            self._canvas.create_text(
                center_x, center_y,
                text="☠",
                fill="#88ff88",
                font=('Arial', 20, 'bold'),
                tags="poison"
            )

    # ========== 实体绘制（在主线程中调用）==========

    def _do_draw_entities(self, entities: List[Dict[str, Any]]):
        if not self._canvas:
            return

        # 与原代码一致：delete entity tag 后重绘
        self._canvas.delete("entity")

        for entity in entities:
            etype = entity.get('type', '')
            ex = entity.get('x', 0)
            ey = entity.get('y', 0)

            if etype == 'player':
                draw_player(self._canvas, ex, ey, tag="entity")
            elif etype == 'guard':
                draw_guard(self._canvas, ex, ey, tag="entity")
            elif etype == 'merchant':
                draw_merchant(self._canvas, ex, ey, tag="entity")

    # ========== UI 绘制 ==========

    def _draw_ui_static(self):
        """绘制静态UI（只画一次）"""
        if not self._canvas or self._ui_static_drawn:
            return

        ui_x = CONFIG.map_width * CONFIG.tile_size
        ui_w = CONFIG.ui_width

        # UI背景
        self._canvas.create_rectangle(ui_x, 0, ui_x + ui_w, WIN_H,
                                       fill=ColorPalette.UI_BG, outline='', tags="ui_static")
        # 边框
        self._canvas.create_rectangle(ui_x + 2, 2, ui_x + ui_w - 2, WIN_H - 2,
                                       fill='', outline=ColorPalette.UI_BORDER, width=2, tags="ui_static")

        # 标题
        self._canvas.create_text(ui_x + ui_w // 2, 25,
                                text="MAGIC TOWER",
                                fill=ColorPalette.UI_TITLE, font=self._fonts['title'], tags="ui_static")
        self._canvas.create_line(ui_x + 15, 42, ui_x + ui_w - 15, 42,
                                fill=ColorPalette.UI_BORDER, width=2, tags="ui_static")

        # 玩家状态标题
        y_offset = 60
        self._canvas.create_text(ui_x + 15, y_offset,
                                text="PLAYER STATUS",
                                fill=ColorPalette.UI_TITLE, font=self._fonts['normal'],
                                anchor='w', tags="ui_static")
        y_offset += 25

        # 位置标签（静态"Pos:"部分动态更新）
        self._ui_pos_item = self._canvas.create_text(ui_x + 20, y_offset,
                                text="Pos: (0, 0)",
                                fill=ColorPalette.UI_TEXT, font=self._fonts['small'],
                                anchor='w', tags="ui_dynamic")
        y_offset += 20

        # HP标签
        self._canvas.create_text(ui_x + 20, y_offset,
                                text="HP", fill=ColorPalette.HEALTH,
                                font=self._fonts['small'], anchor='w', tags="ui_static")
        # 血条背景
        self._canvas.create_rectangle(ui_x + 50, y_offset - 6, ui_x + ui_w - 20, y_offset + 6,
                                     fill='#202020', outline=ColorPalette.UI_BORDER, tags="ui_static")
        # 血条前景（动态）
        self._ui_hp_fill_item = self._canvas.create_rectangle(
            ui_x + 50, y_offset - 6, ui_x + 50 + 150, y_offset + 6,
            fill=ColorPalette.HEALTH, outline='', tags="ui_dynamic")
        y_offset += 25

        # 分隔线
        self._canvas.create_line(ui_x + 15, y_offset, ui_x + ui_w - 15, y_offset,
                                fill=ColorPalette.UI_BORDER, width=1, tags="ui_static")
        y_offset += 15

        # NPC列表标题
        self._canvas.create_text(ui_x + 15, y_offset,
                                text="NPC LIST",
                                fill=ColorPalette.UI_TITLE, font=self._fonts['normal'],
                                anchor='w', tags="ui_static")
        y_offset += 25

        # NPC列表起始y
        self._npc_list_start_y = y_offset

        # 预留NPC列表空间（预创建10个item）
        self._ui_npc_items = []
        for i in range(10):
            # 每个NPC占3行（图标+名称、位置、状态），共60px
            base_y = y_offset + i * 60
            # 图标背景
            icon_bg = self._canvas.create_rectangle(0, 0, 0, 0,
                                                    fill='', outline='', tags="ui_dynamic")
            # 图标文字
            icon_text = self._canvas.create_text(0, 0, text='',
                                                 fill='#000000', font=self._fonts['small'],
                                                 tags="ui_dynamic")
            # 名称
            name_item = self._canvas.create_text(0, 0, text='',
                                                 fill=ColorPalette.UI_TEXT, font=self._fonts['small'],
                                                 anchor='w', tags="ui_dynamic")
            # 位置
            pos_item = self._canvas.create_text(0, 0, text='',
                                                fill=ColorPalette.UI_TEXT, font=self._fonts['small'],
                                                anchor='w', tags="ui_dynamic")
            # 状态
            state_item = self._canvas.create_text(0, 0, text='',
                                                  fill='#808080', font=self._fonts['small'],
                                                  anchor='w', tags="ui_dynamic")
            self._ui_npc_items.append({
                'icon_bg': icon_bg,
                'icon_text': icon_text,
                'name': name_item,
                'pos': pos_item,
                'state': state_item,
                'base_y': base_y,
            })

        # 计算底部提示位置
        help_y = WIN_H - 50
        self._canvas.create_text(ui_x + ui_w // 2, help_y,
                                text="WASD / Arrows: Move",
                                fill=ColorPalette.UI_TEXT, font=self._fonts['small'], tags="ui_static")
        self._canvas.create_text(ui_x + ui_w // 2, help_y + 20,
                                text="E: Interact  |  Q: Quit",
                                fill='#ff6060', font=self._fonts['small'], tags="ui_static")

        self._ui_static_drawn = True

    def _redraw_ui_dynamic(self):
        """更新动态UI部分（位置、血条、NPC列表）"""
        if not self._canvas or not self._ui_static_drawn:
            return

        ui_x = CONFIG.map_width * CONFIG.tile_size
        ui_w = CONFIG.ui_width

        # 更新位置
        if hasattr(self, '_ui_pos_item') and hasattr(self, '_player_x'):
            self._canvas.itemconfig(self._ui_pos_item,
                                    text=f"Pos: ({self._player_x}, {self._player_y})")

        # 更新血条
        if hasattr(self, '_ui_hp_fill_item') and hasattr(self, '_player_hp'):
            hp_ratio = self._player_hp / self._player_max_hp if self._player_max_hp > 0 else 0
            hp_fill_w = int(150 * hp_ratio)
            # 血条y位置: 60 + 25 + 20 - 6 = 99
            hp_y = 60 + 25 + 20
            self._canvas.coords(self._ui_hp_fill_item,
                ui_x + 50, hp_y - 6,
                ui_x + 50 + hp_fill_w, hp_y + 6
            )

        # 更新NPC列表
        if hasattr(self, '_ui_npc_items') and hasattr(self, '_npc_list'):
            npc_count = len(self._npc_list)
            pool_size = len(self._ui_npc_items)

            for i in range(pool_size):
                items = self._ui_npc_items[i]
                base_y = self._npc_list_start_y

                if i < npc_count:
                    npc = self._npc_list[i]
                    npc_type = npc.get('type', '')
                    npc_id = npc.get('id', '')
                    nx = npc.get('x', 0)
                    ny = npc.get('y', 0)
                    state = npc.get('state', '')
                    state_display = npc.get('state_display', state)

                    is_guard = npc_type == 'guard'
                    npc_color = ColorPalette.GUARD if is_guard else ColorPalette.MERCHANT
                    npc_icon = 'G' if is_guard else 'M'
                    state_color = npc_color if state == 'Alert' else '#808080'

                    y = base_y + i * 60

                    # 图标背景
                    self._canvas.coords(items['icon_bg'],
                        ui_x + 20, y - 8, ui_x + 40, y + 8)
                    self._canvas.itemconfig(items['icon_bg'], fill=npc_color, state='normal')

                    # 图标文字
                    self._canvas.coords(items['icon_text'], ui_x + 30, y)
                    self._canvas.itemconfig(items['icon_text'], text=npc_icon, state='normal')

                    # 名称
                    self._canvas.coords(items['name'], ui_x + 50, y)
                    self._canvas.itemconfig(items['name'], text=npc_id, state='normal')

                    # 位置
                    self._canvas.coords(items['pos'], ui_x + 60, y + 20)
                    self._canvas.itemconfig(items['pos'],
                        text=f"Pos: ({nx}, {ny})", state='normal')

                    # 状态
                    self._canvas.coords(items['state'], ui_x + 60, y + 38)
                    self._canvas.itemconfig(items['state'],
                        text=f"State: {state_display}", fill=state_color, state='normal')
                else:
                    # 隐藏多余的
                    for key in items:
                        if key != 'base_y':
                            self._canvas.itemconfig(items[key], state='hidden')

    # ========== 对话 ==========

    def _clear_dialogue(self):
        if not self._canvas:
            return
        for item in self._dialogue_items:
            self._canvas.delete(item)
        self._dialogue_items = []

    def _redraw_dialogue(self):
        if not self._canvas:
            return

        self._clear_dialogue()

        if not self._dialogue_visible:
            return

        # 与原代码布局一致
        box_x = 50
        box_y = CONFIG.map_height * CONFIG.tile_size - 130
        box_w = CONFIG.map_width * CONFIG.tile_size - 100
        box_h = 120

        # 外框
        self._dialogue_items.append(self._canvas.create_rectangle(
            box_x, box_y, box_x + box_w, box_y + box_h,
            fill='#0a0a12', outline=ColorPalette.UI_BORDER, width=2, tags="dialogue"
        ))
        # 内框
        self._dialogue_items.append(self._canvas.create_rectangle(
            box_x + 6, box_y + 6, box_x + box_w - 6, box_y + box_h - 6,
            fill=ColorPalette.UI_BG, outline='', tags="dialogue"
        ))

        # NPC名字
        self._dialogue_items.append(self._canvas.create_text(
            box_x + 20, box_y + 18,
            text=self._dialogue_npc_name,
            fill=ColorPalette.UI_TITLE, font=self._fonts['normal'],
            anchor='w', tags="dialogue"
        ))

        # 分隔线
        self._dialogue_items.append(self._canvas.create_line(
            box_x + 15, box_y + 38, box_x + box_w - 15, box_y + 38,
            fill=ColorPalette.UI_BORDER, width=1, tags="dialogue"
        ))

        # 对话文本
        text_y = box_y + 55
        max_w = box_w - 50
        text = self._dialogue_text
        line_h = 22

        # 简单换行
        current_line = ''
        for char in text:
            test_line = current_line + char
            if self._fonts['small'].measure(test_line) > max_w and current_line:
                self._dialogue_items.append(self._canvas.create_text(
                    box_x + 25, text_y,
                    text=current_line,
                    fill=ColorPalette.UI_TEXT, font=self._fonts['small'],
                    anchor='w', tags="dialogue"
                ))
                text_y += line_h
                current_line = ''
            current_line += char

        if current_line:
            self._dialogue_items.append(self._canvas.create_text(
                box_x + 25, text_y,
                text=current_line,
                fill=ColorPalette.UI_TEXT, font=self._fonts['small'],
                anchor='w', tags="dialogue"
            ))
            text_y += line_h

        # 选项
        text_y += 5
        for i, opt in enumerate(self._dialogue_options):
            opt_y = text_y + i * 18
            self._dialogue_items.append(self._canvas.create_text(
                box_x + 30, opt_y,
                text=f"{i + 1}. {opt}",
                fill=ColorPalette.UI_TEXT, font=self._fonts['small'],
                anchor='w', tags="dialogue"
            ))
