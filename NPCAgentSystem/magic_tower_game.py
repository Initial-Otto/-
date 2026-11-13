"""
NPC Agent System - 魔塔风格像素游戏
使用 tkinter 实现，无需额外安装库
"""
import os
import sys
import time
import random
import tkinter as tk
from tkinter import font as tkfont
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Core.enums import NPCType
from Core.vector import Vector2
from Core.config import SETTINGS, GameSettings
from Utility import EventBus
from Business import NPCManager
from Business.Dialogue.dialogue_manager import DialogueManager, DialogueFactory


# ========== 游戏配置 ==========

@dataclass
class GameConfig:
    """游戏配置（兼容旧代码）"""
    tile_size: int = 28
    map_width: int = 40
    map_height: int = 30
    ui_height: int = 120
    ui_width: int = 280
    npc_move_interval: float = 0.2
    guard_move_interval: float = 0.8
    player_start_x: int = 2
    player_start_y: int = 2
    player_start_gold: int = 100
    interact_distance: float = 2.5
    guard_detect_radius: float = 8.0
    merchant_detect_radius: float = 4.0
    merchant_home_radius: int = 2
    merchant_dialogue_end_greet_range: float = 5.0


# 保持向后兼容
CONFIG = GameConfig()
WIN_W = CONFIG.map_width * CONFIG.tile_size + CONFIG.ui_width
WIN_H = CONFIG.map_height * CONFIG.tile_size + CONFIG.ui_height

# 魔塔配色（可配置化）
class ColorPalette:
    """颜色配置"""
    BG = '#000000'
    FLOOR = '#2a1a0f'
    FLOOR_LIGHT = '#3a2515'
    WALL = '#5a4030'
    WALL_DARK = '#3a2818'
    WALL_HIGHLIGHT = '#7a5a40'
    PLAYER = '#00e0ff'
    PLAYER_DARK = '#0080a0'
    PLAYER_SKIN = '#ffd0a0'
    GUARD = '#ff4040'
    GUARD_DARK = '#a02020'
    MERCHANT = '#ffd040'
    MERCHANT_DARK = '#a08020'
    UI_BG = '#1a1a2e'
    UI_BORDER = '#4a4a6e'
    UI_TEXT = '#e0e0e0'
    UI_TITLE = '#ffcc00'
    HEALTH = '#40ff40'
    STAMINA = '#4080ff'
    # 装饰物配色
    BARREL = '#8b5a2b'
    BARREL_DARK = '#5a3a1a'
    BARREL_BAND = '#6b4a2b'
    POT = '#a08060'
    POT_DARK = '#605040'
    TORCH = '#ffa040'
    TORCH_GLOW = '#ffcc60'
    PILLAR = '#9a9a9a'
    PILLAR_DARK = '#6a6a6a'
    PILLAR_LIGHT = '#bababa'


# ========== 瓦片类型 ==========

TILE_FLOOR = 0
TILE_WALL = 1
TILE_DOOR = 2
TILE_STAIRS = 3
TILE_BARREL = 4      # 木桶（装饰物，不可通过）
TILE_POT = 5          # 罐子（装饰物，不可通过）
TILE_TORCH = 6        # 火把（装饰物，不可通过）
TILE_PILLAR = 7       # 柱子（装饰物，不可通过）


# ========== 地图生成 ==========

def generate_magic_tower_map():
    """生成魔塔风格地图（40x30）"""
    random.seed(SETTINGS.map_seed)
    game_map = []
    map_w = CONFIG.map_width
    map_h = CONFIG.map_height

    for y in range(map_h):
        row = []
        for x in range(map_w):
            if x == 0 or x == map_w - 1 or y == 0 or y == map_h - 1:
                row.append(TILE_WALL)
            else:
                row.append(TILE_FLOOR)
        game_map.append(row)

    # 添加内部墙壁结构 - 魔塔风格房间
    # 水平走廊（按比例分布）
    for x in range(1, map_w - 1):
        game_map[7][x] = TILE_WALL
        game_map[15][x] = TILE_WALL
        game_map[23][x] = TILE_WALL

    # 垂直墙壁
    for y in range(1, map_h - 1):
        game_map[y][13] = TILE_WALL
        game_map[y][27] = TILE_WALL

    # 开门（走廊连接处）
    # 第一层
    game_map[7][5] = TILE_FLOOR
    game_map[7][10] = TILE_FLOOR
    game_map[7][20] = TILE_FLOOR
    game_map[7][32] = TILE_FLOOR
    # 第二层
    game_map[15][3] = TILE_FLOOR
    game_map[15][10] = TILE_FLOOR
    game_map[15][18] = TILE_FLOOR
    game_map[15][24] = TILE_FLOOR
    game_map[15][35] = TILE_FLOOR
    # 第三层
    game_map[23][6] = TILE_FLOOR
    game_map[23][13] = TILE_FLOOR
    game_map[23][22] = TILE_FLOOR
    game_map[23][33] = TILE_FLOOR

    # 垂直墙的门
    game_map[3][13] = TILE_FLOOR
    game_map[11][13] = TILE_FLOOR
    game_map[19][13] = TILE_FLOOR
    game_map[27][13] = TILE_FLOOR

    game_map[3][27] = TILE_FLOOR
    game_map[11][27] = TILE_FLOOR
    game_map[19][27] = TILE_FLOOR
    game_map[27][27] = TILE_FLOOR

    # 添加一些装饰性墙壁方块
    decorations = [
        (3, 3), (4, 3), (3, 4),
        (7, 9), (8, 9), (7, 10),
        (16, 3), (16, 4), (17, 3),
        (30, 7), (31, 7), (30, 8),
        (33, 14), (34, 14), (33, 15),
        (5, 25), (6, 25), (5, 26),
        (20, 27), (21, 27), (20, 28),
        (35, 25), (36, 25), (35, 26),
    ]
    for dx, dy in decorations:
        if 0 < dx < map_w - 1 and 0 < dy < map_h - 1:
            game_map[dy][dx] = TILE_WALL

    # 添加装饰物（木桶、罐子、火把、柱子）
    # 装饰物列表 (x, y, tile_type)
    decoration_tiles = [
        # 木桶（放在墙边和角落）
        (37, 2, TILE_BARREL),
        (5, 5, TILE_BARREL),
        (20, 2, TILE_BARREL),
        (35, 3, TILE_BARREL),
        (2, 20, TILE_BARREL),
        (30, 20, TILE_BARREL),
        (35, 20, TILE_BARREL),
        (8, 27, TILE_BARREL),
        (25, 27, TILE_BARREL),
        # 罐子（散落各处）
        (8, 3, TILE_POT),
        (24, 4, TILE_POT),
        (36, 10, TILE_POT),
        (3, 12, TILE_POT),
        (20, 20, TILE_POT),
        (32, 26, TILE_POT),
        (10, 27, TILE_POT),
        # 火把（沿墙壁放置）
        (1, 5, TILE_TORCH),
        (1, 12, TILE_TORCH),
        (1, 20, TILE_TORCH),
        (1, 27, TILE_TORCH),
        (38, 5, TILE_TORCH),
        (38, 12, TILE_TORCH),
        (38, 20, TILE_TORCH),
        (38, 27, TILE_TORCH),
        # 柱子（房间中央装饰）
        (6, 3, TILE_PILLAR),
        (20, 10, TILE_PILLAR),
        (33, 3, TILE_PILLAR),
        (6, 20, TILE_PILLAR),
        (24, 20, TILE_PILLAR),
        (33, 20, TILE_PILLAR),
    ]
    for dx, dy, dt in decoration_tiles:
        if 0 < dx < map_w - 1 and 0 < dy < map_h - 1:
            game_map[dy][dx] = dt

    return game_map


def is_walkable(game_map, x, y):
    """检查指定坐标是否可通行"""
    map_w = CONFIG.map_width
    map_h = CONFIG.map_height
    if x < 0 or x >= map_w or y < 0 or y >= map_h:
        return False
    return game_map[y][x] == TILE_FLOOR


# ========== 像素绘制工具 ==========

def get_tile_rect(x, y):
    """计算瓦片像素坐标"""
    px = x * CONFIG.tile_size
    py = y * CONFIG.tile_size
    return px, py, CONFIG.tile_size


def draw_rect(canvas, px, py, s, fill, outline='', width=1, x_ratio=0, y_ratio=0, w_ratio=1, h_ratio=1, tag=''):
    """通用矩形绘制"""
    x1 = px + s * x_ratio
    y1 = py + s * y_ratio
    x2 = px + s * (x_ratio + w_ratio)
    y2 = py + s * (y_ratio + h_ratio)
    if tag:
        canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=width, tags=tag)
    else:
        canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=width)


def draw_polygon(canvas, px, py, s, points, fill, outline='', tag=''):
    """通用多边形绘制"""
    transformed = [(px + p[0] * s, py + p[1] * s) for p in points]
    if tag:
        canvas.create_polygon(transformed, fill=fill, outline=outline, tags=tag)
    else:
        canvas.create_polygon(transformed, fill=fill, outline=outline)


def draw_wall_tile(canvas, x, y, tag=''):
    """绘制魔塔风格墙壁"""
    px, py, s = get_tile_rect(x, y)

    # 墙壁主体
    if tag:
        canvas.create_rectangle(px, py, px + s, py + s,
                                fill=ColorPalette.WALL, outline='', tags=tag)
    else:
        canvas.create_rectangle(px, py, px + s, py + s,
                                fill=ColorPalette.WALL, outline='')

    # 砖块纹理 - 横向
    if tag:
        canvas.create_line(px, py + s // 3, px + s, py + s // 3,
                           fill=ColorPalette.WALL_DARK, width=1, tags=tag)
        canvas.create_line(px, py + s * 2 // 3, px + s, py + s * 2 // 3,
                           fill=ColorPalette.WALL_DARK, width=1, tags=tag)

        # 砖块纹理 - 竖向交错
        canvas.create_line(px + s // 2, py, px + s // 2, py + s // 3,
                           fill=ColorPalette.WALL_DARK, width=1, tags=tag)
        canvas.create_line(px + s // 4, py + s // 3, px + s // 4, py + s * 2 // 3,
                           fill=ColorPalette.WALL_DARK, width=1, tags=tag)
        canvas.create_line(px + s * 3 // 4, py + s // 3, px + s * 3 // 4, py + s * 2 // 3,
                           fill=ColorPalette.WALL_DARK, width=1, tags=tag)
        canvas.create_line(px + s // 2, py + s * 2 // 3, px + s // 2, py + s,
                           fill=ColorPalette.WALL_DARK, width=1, tags=tag)

        # 高光
        canvas.create_line(px + 1, py + 1, px + s - 2, py + 1,
                           fill=ColorPalette.WALL_HIGHLIGHT, width=1, tags=tag)
    else:
        canvas.create_line(px, py + s // 3, px + s, py + s // 3,
                           fill=ColorPalette.WALL_DARK, width=1)
        canvas.create_line(px, py + s * 2 // 3, px + s, py + s * 2 // 3,
                           fill=ColorPalette.WALL_DARK, width=1)

        # 砖块纹理 - 竖向交错
        canvas.create_line(px + s // 2, py, px + s // 2, py + s // 3,
                           fill=ColorPalette.WALL_DARK, width=1)
        canvas.create_line(px + s // 4, py + s // 3, px + s // 4, py + s * 2 // 3,
                           fill=ColorPalette.WALL_DARK, width=1)
        canvas.create_line(px + s * 3 // 4, py + s // 3, px + s * 3 // 4, py + s * 2 // 3,
                           fill=ColorPalette.WALL_DARK, width=1)
        canvas.create_line(px + s // 2, py + s * 2 // 3, px + s // 2, py + s,
                           fill=ColorPalette.WALL_DARK, width=1)

        # 高光
        canvas.create_line(px + 1, py + 1, px + s - 2, py + 1,
                           fill=ColorPalette.WALL_HIGHLIGHT, width=1)


def draw_floor_tile(canvas, x, y, tag=''):
    """绘制魔塔风格地板"""
    px, py, s = get_tile_rect(x, y)

    # 地板主体
    if tag:
        canvas.create_rectangle(px, py, px + s, py + s,
                                fill=ColorPalette.FLOOR, outline='', tags=tag)
    else:
        canvas.create_rectangle(px, py, px + s, py + s,
                                fill=ColorPalette.FLOOR, outline='')

    # 地板格子纹理
    offset = (x + y) % 2
    if offset == 0:
        if tag:
            canvas.create_rectangle(px + 1, py + 1, px + s - 1, py + s - 1,
                                    fill=ColorPalette.FLOOR_LIGHT, outline='', tags=tag)
        else:
            canvas.create_rectangle(px + 1, py + 1, px + s - 1, py + s - 1,
                                    fill=ColorPalette.FLOOR_LIGHT, outline='')

    # 地板线条
    if tag:
        canvas.create_rectangle(px, py, px + s, py + s,
                                fill='', outline=ColorPalette.WALL_DARK, width=1, tags=tag)
    else:
        canvas.create_rectangle(px, py, px + s, py + s,
                                fill='', outline=ColorPalette.WALL_DARK, width=1)


def draw_barrel_tile(canvas, x, y, tag=''):
    """绘制木桶装饰物"""
    px, py, s = get_tile_rect(x, y)

    # 先画地板底色
    if tag:
        canvas.create_rectangle(px, py, px + s, py + s,
                                fill=ColorPalette.FLOOR, outline='', tags=tag)
    else:
        canvas.create_rectangle(px, py, px + s, py + s,
                                fill=ColorPalette.FLOOR, outline='')

    # 木桶主体（椭圆形）
    cx = px + s // 2
    bw = int(s * 0.6)
    bh = int(s * 0.7)
    bx1 = cx - bw // 2
    by1 = py + (s - bh) // 2
    bx2 = cx + bw // 2
    by2 = by1 + bh

    if tag:
        canvas.create_oval(bx1, by1, bx2, by2,
                           fill=ColorPalette.BARREL, outline=ColorPalette.BARREL_DARK,
                           width=1, tags=tag)
    else:
        canvas.create_oval(bx1, by1, bx2, by2,
                           fill=ColorPalette.BARREL, outline=ColorPalette.BARREL_DARK,
                           width=1)

    # 木桶铁箍（横线）
    mid_y1 = by1 + bh // 3
    mid_y2 = by1 + (bh * 2) // 3
    if tag:
        canvas.create_line(bx1, mid_y1, bx2, mid_y1,
                           fill=ColorPalette.BARREL_BAND, width=2, tags=tag)
        canvas.create_line(bx1, mid_y2, bx2, mid_y2,
                           fill=ColorPalette.BARREL_BAND, width=2, tags=tag)
    else:
        canvas.create_line(bx1, mid_y1, bx2, mid_y1,
                           fill=ColorPalette.BARREL_BAND, width=2)
        canvas.create_line(bx1, mid_y2, bx2, mid_y2,
                           fill=ColorPalette.BARREL_BAND, width=2)

    # 木桶顶部椭圆
    if tag:
        canvas.create_oval(bx1, by1 - 2, bx2, by1 + 4,
                           fill=ColorPalette.BARREL_DARK, outline=ColorPalette.BARREL_DARK,
                           tags=tag)
    else:
        canvas.create_oval(bx1, by1 - 2, bx2, by1 + 4,
                           fill=ColorPalette.BARREL_DARK, outline=ColorPalette.BARREL_DARK)


def draw_pot_tile(canvas, x, y, tag=''):
    """绘制罐子装饰物"""
    px, py, s = get_tile_rect(x, y)

    # 地板底色
    if tag:
        canvas.create_rectangle(px, py, px + s, py + s,
                                fill=ColorPalette.FLOOR, outline='', tags=tag)
    else:
        canvas.create_rectangle(px, py, px + s, py + s,
                                fill=ColorPalette.FLOOR, outline='')

    # 罐子主体
    cx = px + s // 2
    pw = int(s * 0.5)
    ph = int(s * 0.55)
    px1 = cx - pw // 2
    py1 = py + (s - ph) // 2
    px2 = cx + pw // 2
    py2 = py1 + ph

    if tag:
        canvas.create_oval(px1, py1, px2, py2,
                           fill=ColorPalette.POT, outline=ColorPalette.POT_DARK,
                           width=1, tags=tag)
    else:
        canvas.create_oval(px1, py1, px2, py2,
                           fill=ColorPalette.POT, outline=ColorPalette.POT_DARK,
                           width=1)

    # 罐口
    neck_w = int(pw * 0.5)
    nx1 = cx - neck_w // 2
    nx2 = cx + neck_w // 2
    if tag:
        canvas.create_rectangle(nx1, py1 - 3, nx2, py1 + 3,
                                 fill=ColorPalette.POT_DARK, outline=ColorPalette.POT_DARK,
                                 tags=tag)
    else:
        canvas.create_rectangle(nx1, py1 - 3, nx2, py1 + 3,
                                 fill=ColorPalette.POT_DARK, outline=ColorPalette.POT_DARK)


def draw_torch_tile(canvas, x, y, tag=''):
    """绘制火把装饰物"""
    px, py, s = get_tile_rect(x, y)

    # 地板底色
    if tag:
        canvas.create_rectangle(px, py, px + s, py + s,
                                fill=ColorPalette.FLOOR, outline='', tags=tag)
    else:
        canvas.create_rectangle(px, py, px + s, py + s,
                                fill=ColorPalette.FLOOR, outline='')

    cx = px + s // 2

    # 火把杆
    stick_w = 3
    sx1 = cx - stick_w // 2
    if tag:
        canvas.create_rectangle(sx1, py + int(s * 0.3), sx1 + stick_w, py + int(s * 0.85),
                                 fill=ColorPalette.BARREL_DARK, outline='', tags=tag)
    else:
        canvas.create_rectangle(sx1, py + int(s * 0.3), sx1 + stick_w, py + int(s * 0.85),
                                 fill=ColorPalette.BARREL_DARK, outline='')

    # 火焰
    fw = int(s * 0.3)
    fh = int(s * 0.35)
    fx1 = cx - fw // 2
    fy1 = py + int(s * 0.05)
    fx2 = cx + fw // 2
    fy2 = fy1 + fh
    if tag:
        canvas.create_oval(fx1, fy1, fx2, fy2,
                           fill=ColorPalette.TORCH, outline=ColorPalette.TORCH_GLOW,
                           width=1, tags=tag)
    else:
        canvas.create_oval(fx1, fy1, fx2, fy2,
                           fill=ColorPalette.TORCH, outline=ColorPalette.TORCH_GLOW,
                           width=1)

    # 火焰中心高亮
    if tag:
        canvas.create_oval(fx1 + 2, fy1 + 2, fx2 - 2, fy2 - 2,
                           fill=ColorPalette.TORCH_GLOW, outline='', tags=tag)
    else:
        canvas.create_oval(fx1 + 2, fy1 + 2, fx2 - 2, fy2 - 2,
                           fill=ColorPalette.TORCH_GLOW, outline='')


def draw_pillar_tile(canvas, x, y, tag=''):
    """绘制柱子装饰物"""
    px, py, s = get_tile_rect(x, y)

    # 地板底色
    if tag:
        canvas.create_rectangle(px, py, px + s, py + s,
                                fill=ColorPalette.FLOOR, outline='', tags=tag)
    else:
        canvas.create_rectangle(px, py, px + s, py + s,
                                fill=ColorPalette.FLOOR, outline='')

    # 柱子主体
    pw = int(s * 0.45)
    px1 = px + (s - pw) // 2
    px2 = px1 + pw
    if tag:
        canvas.create_rectangle(px1, py + 2, px2, py + s - 2,
                                fill=ColorPalette.PILLAR, outline=ColorPalette.PILLAR_DARK,
                                width=1, tags=tag)
    else:
        canvas.create_rectangle(px1, py + 2, px2, py + s - 2,
                                fill=ColorPalette.PILLAR, outline=ColorPalette.PILLAR_DARK,
                                width=1)

    # 柱头（顶部加宽）
    hw = int(s * 0.6)
    hx1 = px + (s - hw) // 2
    hx2 = hx1 + hw
    if tag:
        canvas.create_rectangle(hx1, py + 1, hx2, py + int(s * 0.2),
                                fill=ColorPalette.PILLAR_LIGHT, outline=ColorPalette.PILLAR_DARK,
                                width=1, tags=tag)
    else:
        canvas.create_rectangle(hx1, py + 1, hx2, py + int(s * 0.2),
                                fill=ColorPalette.PILLAR_LIGHT, outline=ColorPalette.PILLAR_DARK,
                                width=1)

    # 柱基（底部加宽）
    if tag:
        canvas.create_rectangle(hx1, py + int(s * 0.8), hx2, py + s - 1,
                                fill=ColorPalette.PILLAR_DARK, outline=ColorPalette.PILLAR_DARK,
                                tags=tag)
    else:
        canvas.create_rectangle(hx1, py + int(s * 0.8), hx2, py + s - 1,
                                fill=ColorPalette.PILLAR_DARK, outline=ColorPalette.PILLAR_DARK)


def draw_decoration_tile(canvas, x, y, tile_type, tag=''):
    """根据装饰物类型绘制对应装饰"""
    if tile_type == TILE_BARREL:
        draw_barrel_tile(canvas, x, y, tag)
    elif tile_type == TILE_POT:
        draw_pot_tile(canvas, x, y, tag)
    elif tile_type == TILE_TORCH:
        draw_torch_tile(canvas, x, y, tag)
    elif tile_type == TILE_PILLAR:
        draw_pillar_tile(canvas, x, y, tag)
    else:
        draw_floor_tile(canvas, x, y, tag)


def draw_player(canvas, x, y, tag=''):
    """绘制玩家角色（勇者）"""
    px, py, s = get_tile_rect(x, y)

    # 头盔
    draw_rect(canvas, px, py, s, ColorPalette.PLAYER, x_ratio=0.25, y_ratio=0.1, w_ratio=0.5, h_ratio=0.25, tag=tag)
    draw_rect(canvas, px, py, s, ColorPalette.PLAYER, x_ratio=0.4, y_ratio=0.02, w_ratio=0.2, h_ratio=0.13, tag=tag)

    # 脸
    draw_rect(canvas, px, py, s, ColorPalette.PLAYER_SKIN, x_ratio=0.3, y_ratio=0.25, w_ratio=0.4, h_ratio=0.2, tag=tag)
    draw_rect(canvas, px, py, s, '#000000', x_ratio=0.35, y_ratio=0.3, w_ratio=0.08, h_ratio=0.06, tag=tag)
    draw_rect(canvas, px, py, s, '#000000', x_ratio=0.57, y_ratio=0.3, w_ratio=0.08, h_ratio=0.06, tag=tag)

    # 身体（盔甲）
    draw_rect(canvas, px, py, s, ColorPalette.PLAYER, x_ratio=0.22, y_ratio=0.4, w_ratio=0.56, h_ratio=0.3, tag=tag)
    draw_rect(canvas, px, py, s, ColorPalette.PLAYER_DARK, x_ratio=0.42, y_ratio=0.42, w_ratio=0.16, h_ratio=0.26, tag=tag)

    # 剑（右手）
    draw_rect(canvas, px, py, s, '#c0c0c0', x_ratio=0.78, y_ratio=0.3, w_ratio=0.1, h_ratio=0.45, tag=tag)
    draw_rect(canvas, px, py, s, '#8b4513', x_ratio=0.73, y_ratio=0.7, w_ratio=0.2, h_ratio=0.08, tag=tag)

    # 盾牌（左手）
    draw_rect(canvas, px, py, s, ColorPalette.PLAYER_DARK, x_ratio=0.08, y_ratio=0.45, w_ratio=0.14, h_ratio=0.27, tag=tag)
    draw_rect(canvas, px, py, s, '#ffe066', x_ratio=0.11, y_ratio=0.48, w_ratio=0.08, h_ratio=0.21, tag=tag)

    # 腿
    draw_rect(canvas, px, py, s, ColorPalette.PLAYER_DARK, x_ratio=0.28, y_ratio=0.7, w_ratio=0.17, h_ratio=0.22, tag=tag)
    draw_rect(canvas, px, py, s, ColorPalette.PLAYER_DARK, x_ratio=0.55, y_ratio=0.7, w_ratio=0.17, h_ratio=0.22, tag=tag)


def draw_guard(canvas, x, y, tag=''):
    """绘制守卫NPC"""
    px, py, s = get_tile_rect(x, y)

    # 头盔
    draw_rect(canvas, px, py, s, ColorPalette.GUARD, x_ratio=0.25, y_ratio=0.1, w_ratio=0.5, h_ratio=0.25, tag=tag)
    draw_rect(canvas, px, py, s, ColorPalette.GUARD_DARK, x_ratio=0.18, y_ratio=0.05, w_ratio=0.1, h_ratio=0.15, tag=tag)
    draw_rect(canvas, px, py, s, ColorPalette.GUARD_DARK, x_ratio=0.72, y_ratio=0.05, w_ratio=0.1, h_ratio=0.15, tag=tag)

    # 脸
    draw_rect(canvas, px, py, s, ColorPalette.PLAYER_SKIN, x_ratio=0.3, y_ratio=0.25, w_ratio=0.4, h_ratio=0.2, tag=tag)
    draw_rect(canvas, px, py, s, '#ff0000', x_ratio=0.35, y_ratio=0.3, w_ratio=0.08, h_ratio=0.06, tag=tag)
    draw_rect(canvas, px, py, s, '#ff0000', x_ratio=0.57, y_ratio=0.3, w_ratio=0.08, h_ratio=0.06, tag=tag)

    # 身体（红色盔甲）
    draw_rect(canvas, px, py, s, ColorPalette.GUARD, x_ratio=0.2, y_ratio=0.4, w_ratio=0.6, h_ratio=0.3, tag=tag)
    draw_rect(canvas, px, py, s, ColorPalette.GUARD_DARK, x_ratio=0.38, y_ratio=0.42, w_ratio=0.24, h_ratio=0.26, tag=tag)

    # 长矛
    draw_rect(canvas, px, py, s, '#a0a0a0', x_ratio=0.82, y_ratio=0.05, w_ratio=0.08, h_ratio=0.75, tag=tag)
    draw_polygon(canvas, px, py, s, [(0.86, 0.02), (0.75, 0.18), (0.97, 0.18)], '#e0e0e0', tag=tag)

    # 腿
    draw_rect(canvas, px, py, s, ColorPalette.GUARD_DARK, x_ratio=0.28, y_ratio=0.7, w_ratio=0.17, h_ratio=0.22, tag=tag)
    draw_rect(canvas, px, py, s, ColorPalette.GUARD_DARK, x_ratio=0.55, y_ratio=0.7, w_ratio=0.17, h_ratio=0.22, tag=tag)


def draw_merchant(canvas, x, y, tag=''):
    """绘制商人NPC"""
    px, py, s = get_tile_rect(x, y)

    # 帽子
    draw_polygon(canvas, px, py, s, [(0.5, 0.02), (0.2, 0.3), (0.8, 0.3)], ColorPalette.MERCHANT, tag=tag)
    draw_rect(canvas, px, py, s, ColorPalette.MERCHANT_DARK, x_ratio=0.15, y_ratio=0.25, w_ratio=0.7, h_ratio=0.1, tag=tag)

    # 脸
    draw_rect(canvas, px, py, s, ColorPalette.PLAYER_SKIN, x_ratio=0.3, y_ratio=0.3, w_ratio=0.4, h_ratio=0.2, tag=tag)
    draw_rect(canvas, px, py, s, '#000000', x_ratio=0.36, y_ratio=0.37, w_ratio=0.07, h_ratio=0.05, tag=tag)
    draw_rect(canvas, px, py, s, '#000000', x_ratio=0.57, y_ratio=0.37, w_ratio=0.07, h_ratio=0.05, tag=tag)
    draw_rect(canvas, px, py, s, '#f0f0f0', x_ratio=0.32, y_ratio=0.45, w_ratio=0.36, h_ratio=0.07, tag=tag)

    # 身体（黄色袍子）
    draw_rect(canvas, px, py, s, ColorPalette.MERCHANT, x_ratio=0.18, y_ratio=0.48, w_ratio=0.64, h_ratio=0.37, tag=tag)
    draw_rect(canvas, px, py, s, ColorPalette.MERCHANT_DARK, x_ratio=0.4, y_ratio=0.5, w_ratio=0.2, h_ratio=0.32, tag=tag)
    draw_rect(canvas, px, py, s, '#8b4513', x_ratio=0.18, y_ratio=0.68, w_ratio=0.64, h_ratio=0.05, tag=tag)

    # 钱袋
    draw_rect(canvas, px, py, s, '#8b4513', x_ratio=0.65, y_ratio=0.7, w_ratio=0.15, h_ratio=0.12, tag=tag)
    draw_rect(canvas, px, py, s, '#ffd700', x_ratio=0.68, y_ratio=0.73, w_ratio=0.09, h_ratio=0.06, tag=tag)

    # 脚
    draw_rect(canvas, px, py, s, '#5a3010', x_ratio=0.25, y_ratio=0.85, w_ratio=0.2, h_ratio=0.1, tag=tag)
    draw_rect(canvas, px, py, s, '#5a3010', x_ratio=0.55, y_ratio=0.85, w_ratio=0.2, h_ratio=0.1, tag=tag)


# ========== 游戏主类 ==========

class MagicTowerGame:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("NPC Agent System - Magic Tower")
        self.root.resizable(False, False)
        self.root.configure(bg=ColorPalette.BG)

        # 游戏画布
        self.canvas = tk.Canvas(self.root, width=WIN_W, height=WIN_H,
                                bg=ColorPalette.BG, highlightthickness=0)
        self.canvas.pack()

        # 字体
        self.title_font = tkfont.Font(family='Courier', size=12, weight='bold')
        self.normal_font = tkfont.Font(family='Courier', size=10)
        self.small_font = tkfont.Font(family='Courier', size=9)

        # 游戏数据
        self.game_map = generate_magic_tower_map()
        self.event_bus = EventBus()
        self.npc_manager = NPCManager(self.event_bus)
        self.dialogue_manager = DialogueManager()

        # 玩家
        self.player = Vector2(CONFIG.player_start_x, CONFIG.player_start_y)
        self.gold = CONFIG.player_start_gold

        # NPC
        self._create_npcs()

        # 对话状态
        self.in_dialogue = False
        self.dialogue_npc = None
        self.dialogue_tree = None
        self._prev_dialogue_state = False
        self._dialogue_dirty = False

        # 输入
        self.root.bind('<KeyPress>', self._on_key_press)
        self.running = True

        # 计时
        self.last_npc_move = time.time()
        self.last_guard_move = time.time()
        self.frame_count = 0

        # 脏标记 - 只有变化时才重绘
        self._entity_dirty = True
        self._prev_player_pos = None
        self._prev_npc_positions = {}

        # 休息计时 - 记录每个NPC距离下次休息的时间
        self._rest_timers = {}
        self._init_rest_timers()

        # 毒雾相关
        self._poison_state_map = {}
        self._poison_zones = SETTINGS.poison_zones if SETTINGS.poison_enabled else []

    def _create_npcs(self):
        """创建NPC"""
        from Agent.Action.action_service import INPCActionService
        import random

        class NPCActionService(INPCActionService):
            def __init__(self, game):
                self._game = game
                self._last_move_time = {}  # npc_id -> last_move_time
                self._move_interval = 0.5   # 每 500ms 移动一次

            def _can_move(self, npc_id):
                import time
                now = time.time()
                last = self._last_move_time.get(npc_id, 0)
                if now - last >= self._move_interval:
                    self._last_move_time[npc_id] = now
                    return True
                return False

            def move_towards_player(self, npc_id):
                if not self._can_move(npc_id):
                    return
                npc = self._game.npc_manager.get_npc(npc_id)
                if npc:
                    dx = self._game.player.x - npc.position.x
                    dy = self._game.player.y - npc.position.y
                    self._game._move_towards_player(npc, dx, dy)

            def move_towards(self, npc_id, target):
                if not self._can_move(npc_id):
                    return
                npc = self._game.npc_manager.get_npc(npc_id)
                if npc:
                    self._game._move_towards(npc, target.x, target.y)

            def move_random(self, npc_id):
                if not self._can_move(npc_id):
                    return
                npc = self._game.npc_manager.get_npc(npc_id)
                if npc:
                    self._game._move_random(npc)

            def move_random_in_range(self, npc_id, center, radius):
                if not self._can_move(npc_id):
                    return
                npc = self._game.npc_manager.get_npc(npc_id)
                if npc:
                    self._game._move_random_in_range(npc, center, radius)

            def attack_player(self, npc_id):
                pass

            def stay(self, npc_id):
                pass

        action_service = NPCActionService(self)

        guard1 = self.npc_manager.create_npc("Guard_001", NPCType.GUARD)
        guard1.position = Vector2(15, 3)
        guard1.initialize_brain(self.event_bus, action_service)

        guard2 = self.npc_manager.create_npc("Guard_002", NPCType.GUARD)
        guard2.position = Vector2(25, 9)
        guard2.initialize_brain(self.event_bus, action_service)

        merchant = self.npc_manager.create_npc("Merchant_001", NPCType.MERCHANT)
        merchant.position = Vector2(5, 12)
        merchant.home_pos = Vector2(5, 12)
        merchant.initialize_brain(self.event_bus, action_service)

        # 注册对话数据
        merchant_dialogue = DialogueFactory.create_merchant_dialogue("Merchant_001")
        self.dialogue_manager.register_dialogue(merchant_dialogue)

        guard1_dialogue = DialogueFactory.create_guard_dialogue("Guard_001")
        self.dialogue_manager.register_dialogue(guard1_dialogue)

        guard2_dialogue = DialogueFactory.create_guard_dialogue("Guard_002")
        self.dialogue_manager.register_dialogue(guard2_dialogue)

    def _init_rest_timers(self):
        """初始化NPC休息计时器"""
        for npc in self.npc_manager.get_all_npcs():
            if npc.config.rest_enabled:
                # 初始时随机化起始时间，避免所有NPC同时休息
                import random
                self._rest_timers[npc.npc_id] = random.uniform(
                    npc.config.rest_interval * 0.5,
                    npc.config.rest_interval
                )
            else:
                self._rest_timers[npc.npc_id] = -1  # 不休息

    def _on_key_press(self, event):
        """键盘事件"""
        key = event.keysym.lower()

        if key == 'q' or key == 'escape':
            if self.in_dialogue:
                self._end_dialogue()
                return
            self.running = False
            self.root.destroy()
            return

        # 对话模式下的按键处理
        if self.in_dialogue:
            self._handle_dialogue_input(key)
            return

        # 正常游戏模式
        if key == 'e':
            self._try_interact()
            return

        dx = 0
        dy = 0

        if key in ('w', 'up'):
            dy = -1
        elif key in ('s', 'down'):
            dy = 1
        elif key in ('a', 'left'):
            dx = -1
        elif key in ('d', 'right'):
            dx = 1

        if dx != 0 or dy != 0:
            nx = int(self.player.x) + dx
            ny = int(self.player.y) + dy
            if is_walkable(self.game_map, nx, ny):
                self.player.x = nx
                self.player.y = ny
                self._entity_dirty = True

    def _try_interact(self):
        """尝试与附近的NPC交互"""
        for npc in self.npc_manager.get_all_npcs():
            dx = self.player.x - npc.position.x
            dy = self.player.y - npc.position.y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist <= CONFIG.interact_distance:
                self._start_dialogue(npc)
                return

    def _start_dialogue(self, npc):
        """开始对话"""
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
        """结束对话"""
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
                npc.brain_state = "Patrol"
            self.dialogue_npc = None
        self.in_dialogue = False
        self.dialogue_tree = None
        self.dialogue_manager.end_dialogue()
        self._dialogue_dirty = True
        self._entity_dirty = True

    def _handle_dialogue_input(self, key):
        """处理对话中的输入"""
        if not self.dialogue_tree or not self.dialogue_tree.current_node:
            return

        options = self.dialogue_tree.current_node.options
        num_options = len(options)

        # 数字键选择
        if key.isdigit():
            idx = int(key) - 1
            if 0 <= idx < num_options:
                self.dialogue_tree.select_option(idx)
                self._dialogue_dirty = True
                # 检查是否到达结束节点
                if not self.dialogue_tree.current_node.options:
                    self._end_dialogue()
                return

        # 方向键选择（上/下）
        # 简化版：直接用数字键
        if key in ('return', 'space'):
            if num_options > 0:
                self.dialogue_tree.select_option(0)
                self._dialogue_dirty = True
                if not self.dialogue_tree.current_node.options:
                    self._end_dialogue()

    def _update_npcs(self):
        """更新NPC AI"""
        now = time.time()

        # 更新休息计时器，处理休息状态
        self._update_rest_state(now)
        # 更新毒雾状态
        self._update_poison_state()

        # 每帧更新所有NPC的感知（传入玩家位置，由感知组件判断距离）
        player_pos = Vector2(self.player.x, self.player.y)
        for npc in self.npc_manager.get_all_npcs():
            if npc.brain_state in ("Dialog", "Rest"):
                continue
            if npc.npc_type == NPCType.GUARD:
                npc.update_perception(player_pos, danger_radius=2.0)
            elif npc.npc_type == NPCType.MERCHANT:
                npc.update_perception(player_pos, danger_radius=1.0)

        # 调用每个NPC的AI大脑更新（状态机、策略）
        for npc in self.npc_manager.get_all_npcs():
            npc.update()

        # 在间隔时间内更新脏标记（移动后触发渲染更新）
        if now - self.last_npc_move >= CONFIG.npc_move_interval:
            self.last_npc_move = now
            for npc in self.npc_manager.get_all_npcs():
                if npc.brain_state not in ("Dialog", "Rest"):
                    x, y = int(npc.position.x), int(npc.position.y)
                    if x != getattr(npc, '_last_render_x', -1) or y != getattr(npc, '_last_render_y', -1):
                        npc._last_render_x, npc._last_render_y = x, y
                        self._entity_dirty = True

        self.event_bus.update()

    def _update_rest_state(self, now: float):
        """更新NPC休息状态 - 由游戏层统一管理休息触发"""
        for npc in self.npc_manager.get_all_npcs():
            config = npc.config

            # 不启用休息的NPC跳过
            if not config.rest_enabled:
                continue

            # 检查是否可以进入休息
            rest_state_blocked = {"Alert", "Greet", "Dialog", "Poisoned"}
            if npc.brain_state in rest_state_blocked:
                # 重置计时器，重新开始倒计时
                self._rest_timers[npc.npc_id] = config.rest_interval
                continue

            # 已经是休息状态，由状态机自己管理
            if npc.brain_state == "Rest":
                continue

            # 更新计时器
            timer = self._rest_timers.get(npc.npc_id, -1)
            if timer < 0:
                continue

            # 计时递减
            timer -= 0.033  # 约30fps帧间隔
            self._rest_timers[npc.npc_id] = timer

            # 时间到，进入休息
            if timer <= 0:
                self._enter_rest_state(npc)

    def _enter_rest_state(self, npc):
        """让NPC进入休息状态"""
        from Agent.Decision.state import StateFactory
        config = npc.config

        # 保存当前状态作为返回状态
        current_state = npc.brain_state

        # 创建Rest状态并配置
        rest_state = StateFactory.create_state("Rest")
        rest_state.set_return_state(current_state)
        rest_state.rest_duration = config.rest_duration
        rest_state.set_enabled(config.rest_enabled)

        # 设置到状态机
        npc._context.set_state(rest_state)

        # 重置休息计时器：间隔 + 休息时长
        self._rest_timers[npc.npc_id] = config.rest_interval + config.rest_duration

        self._entity_dirty = True

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
        if not SETTINGS.poison_enabled:
            return

        for npc in self.npc_manager.get_all_npcs():
            in_poison = self._is_in_poison_zone(npc.position.x, npc.position.y)
            self._poison_state_map[npc.npc_id] = in_poison

            # 进入毒雾区域，切换到中毒状态
            if in_poison and npc.brain_state not in ("Poisoned", "Dialog"):
                self._enter_poisoned_state(npc)
            # 离开毒雾区域，更新PoisonedState的in_poison_zone状态
            elif not in_poison and npc.brain_state == "Poisoned":
                self._update_poisoned_state(npc, False)

    def _enter_poisoned_state(self, npc):
        """让NPC进入中毒状态（装饰器模式：用PoisonedState包装当前状态）"""
        from Agent.Decision.state import PoisonedState

        current_state = npc._context.current_state
        # 如果已经在中毒状态，只更新毒雾标志
        if isinstance(current_state, PoisonedState):
            current_state.set_in_poison_zone(True)
            return

        # 用PoisonedState装饰当前状态
        poisoned_state = PoisonedState(current_state)
        poisoned_state.set_in_poison_zone(True)
        npc._context.set_state(poisoned_state)
        self._entity_dirty = True

    def _update_poisoned_state(self, npc, in_zone: bool):
        """更新中毒状态的是否在毒雾中"""
        if npc.brain_state == "Poisoned" and hasattr(npc, '_context') and npc._context:
            state = npc._context.current_state
            if hasattr(state, 'set_in_poison_zone'):
                state.set_in_poison_zone(in_zone)

    def _draw_poison_zones(self):
        """绘制毒雾区域"""
        if not self._poison_zones:
            return

        self.canvas.delete("poison")

        for x1, y1, x2, y2 in self._poison_zones:
            px1 = x1 * CONFIG.tile_size
            py1 = y1 * CONFIG.tile_size
            px2 = (x2 + 1) * CONFIG.tile_size
            py2 = (y2 + 1) * CONFIG.tile_size

            self.canvas.create_rectangle(
                px1, py1, px2, py2,
                fill="#00aa00",
                outline="#006600",
                stipple="gray50",
                tags="poison"
            )

            center_x = (px1 + px2) // 2
            center_y = (py1 + py2) // 2
            self.canvas.create_text(
                center_x, center_y,
                text="☠",
                fill="#88ff88",
                font=('Arial', 20, 'bold'),
                tags="poison"
            )

    def _update_guard(self, npc):
        """守卫AI：由AI层状态机驱动"""
        from Core.enums import EventType
        from Utility import EventData
        from Core.vector import Vector2

        dx = self.player.x - npc.position.x
        dy = self.player.y - npc.position.y
        dist = (dx * dx + dy * dy) ** 0.5

        player_pos = Vector2(self.player.x, self.player.y)
        if dist < CONFIG.guard_detect_radius:
            self.event_bus.notify(EventData(EventType.SENSE_PLAYER_DETECTED, player_pos))
            if dist < 2.0:
                self.event_bus.notify(EventData(EventType.SENSE_DANGER, player_pos))
        else:
            self.event_bus.notify(EventData(EventType.SENSE_PLAYER_LOST, player_pos))

    def _update_merchant(self, npc):
        """商人AI：由AI层状态机驱动"""
        from Core.enums import EventType
        from Utility import EventData
        from Core.vector import Vector2

        dx = self.player.x - npc.position.x
        dy = self.player.y - npc.position.y
        dist = (dx * dx + dy * dy) ** 0.5

        player_pos = Vector2(self.player.x, self.player.y)
        if dist < CONFIG.merchant_detect_radius:
            self.event_bus.notify(EventData(EventType.SENSE_PLAYER_DETECTED, player_pos))
        else:
            self.event_bus.notify(EventData(EventType.SENSE_PLAYER_LOST, player_pos))

    def _move_towards_player(self, npc, dx, dy):
        """向玩家方向移动一格"""
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
        """向目标移动一格"""
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
        """随机移动一格"""
        if random.random() < 0.3:
            dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
            mx, my = random.choice(dirs)
            nx = int(npc.position.x) + mx
            ny = int(npc.position.y) + my
            if is_walkable(self.game_map, nx, ny):
                npc.position.x = nx
                npc.position.y = ny

    def _move_random_in_range(self, npc, home, radius):
        """在指定范围内随机移动"""
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

    def _draw_map(self):
        """绘制地图（只绘制一次，永久保留）"""
        for y in range(CONFIG.map_height):
            for x in range(CONFIG.map_width):
                tile = self.game_map[y][x]
                if tile == TILE_WALL:
                    draw_wall_tile(self.canvas, x, y, tag="map")
                elif tile in (TILE_BARREL, TILE_POT, TILE_TORCH, TILE_PILLAR):
                    draw_decoration_tile(self.canvas, x, y, tile, tag="map")
                else:
                    draw_floor_tile(self.canvas, x, y, tag="map")

    def _draw_entities(self):
        """绘制实体（每帧重绘，带entity tag）"""
        self.canvas.delete("entity")
        for npc in self.npc_manager.get_all_npcs():
            if npc.npc_type == NPCType.GUARD:
                draw_guard(self.canvas, int(npc.position.x), int(npc.position.y), tag="entity")
            elif npc.npc_type == NPCType.MERCHANT:
                draw_merchant(self.canvas, int(npc.position.x), int(npc.position.y), tag="entity")
        draw_player(self.canvas, int(self.player.x), int(self.player.y), tag="entity")

    def _draw_ui(self):
        """绘制UI面板（每5帧重绘一次，带ui tag）"""
        self.canvas.delete("ui")
        ui_x = CONFIG.map_width * CONFIG.tile_size
        ui_w = CONFIG.ui_width

        # UI背景
        self.canvas.create_rectangle(ui_x, 0, ui_x + ui_w, WIN_H,
                                     fill=ColorPalette.UI_BG, outline='', tags="ui")
        # 边框
        self.canvas.create_rectangle(ui_x + 2, 2, ui_x + ui_w - 2, WIN_H - 2,
                                     fill='', outline=ColorPalette.UI_BORDER, width=2, tags="ui")

        # 标题
        self.canvas.create_text(ui_x + ui_w // 2, 25,
                                text="MAGIC TOWER",
                                fill=ColorPalette.UI_TITLE, font=self.title_font, tags="ui")
        self.canvas.create_line(ui_x + 15, 42, ui_x + ui_w - 15, 42,
                                fill=ColorPalette.UI_BORDER, width=2, tags="ui")

        # 玩家状态
        y_offset = 60
        self.canvas.create_text(ui_x + 15, y_offset,
                                text="PLAYER STATUS",
                                fill=ColorPalette.UI_TITLE, font=self.normal_font,
                                anchor='w', tags="ui")
        y_offset += 25

        self.canvas.create_text(ui_x + 20, y_offset,
                                text=f"Pos: ({int(self.player.x)}, {int(self.player.y)})",
                                fill=ColorPalette.UI_TEXT, font=self.small_font,
                                anchor='w', tags="ui")
        y_offset += 20

        # 生命条背景
        self.canvas.create_text(ui_x + 20, y_offset,
                                text="HP", fill=ColorPalette.HEALTH,
                                font=self.small_font, anchor='w', tags="ui")
        self.canvas.create_rectangle(ui_x + 50, y_offset - 6, ui_x + ui_w - 20, y_offset + 6,
                                     fill='#202020', outline=ColorPalette.UI_BORDER, tags="ui")
        self.canvas.create_rectangle(ui_x + 50, y_offset - 6, ui_x + 50 + 150, y_offset + 6,
                                     fill=ColorPalette.HEALTH, outline='', tags="ui")
        y_offset += 25

        # 分隔线
        self.canvas.create_line(ui_x + 15, y_offset, ui_x + ui_w - 15, y_offset,
                                fill=ColorPalette.UI_BORDER, width=1, tags="ui")
        y_offset += 15

        # NPC列表
        self.canvas.create_text(ui_x + 15, y_offset,
                                text="NPC LIST",
                                fill=ColorPalette.UI_TITLE, font=self.normal_font,
                                anchor='w', tags="ui")
        y_offset += 25

        for npc in self.npc_manager.get_all_npcs():
            npc_color = ColorPalette.GUARD if npc.npc_type == NPCType.GUARD else ColorPalette.MERCHANT
            npc_icon = 'G' if npc.npc_type == NPCType.GUARD else 'M'

            # NPC图标
            self.canvas.create_rectangle(ui_x + 20, y_offset - 8, ui_x + 40, y_offset + 8,
                                         fill=npc_color, outline='', tags="ui")
            self.canvas.create_text(ui_x + 30, y_offset,
                                    text=npc_icon, fill='#000000',
                                    font=self.small_font, anchor='center', tags="ui")

            # NPC名称
            self.canvas.create_text(ui_x + 50, y_offset,
                                    text=npc.npc_id,
                                    fill=ColorPalette.UI_TEXT, font=self.small_font,
                                    anchor='w', tags="ui")
            y_offset += 20

            # 位置和状态
            self.canvas.create_text(ui_x + 60, y_offset,
                                    text=f"Pos: ({int(npc.position.x)}, {int(npc.position.y)})",
                                    fill=ColorPalette.UI_TEXT, font=self.small_font,
                                    anchor='w', tags="ui")
            y_offset += 18

            # 状态
            state_color = npc_color if npc.brain_state == 'Alert' else '#808080'
            self.canvas.create_text(ui_x + 60, y_offset,
                                    text=f"State: {npc.brain_display_state}",
                                    fill=state_color, font=self.small_font,
                                    anchor='w', tags="ui")
            y_offset += 22

        # 底部提示
        self.canvas.create_text(ui_x + ui_w // 2, WIN_H - 50,
                                text="WASD / Arrows: Move",
                                fill=ColorPalette.UI_TEXT, font=self.small_font, tags="ui")
        self.canvas.create_text(ui_x + ui_w // 2, WIN_H - 30,
                                text="E: Interact  |  Q: Quit",
                                fill='#ff6060', font=self.small_font, tags="ui")

    def _draw_dialogue_box(self):
        """绘制对话面板（带dialogue tag）"""
        self.canvas.delete("dialogue")
        if not self.in_dialogue or not self.dialogue_tree or not self.dialogue_tree.current_node:
            return

        box_x = 50
        box_y = CONFIG.map_height * CONFIG.tile_size - 130
        box_w = CONFIG.map_width * CONFIG.tile_size - 100
        box_h = 120

        # 对话框背景
        self.canvas.create_rectangle(box_x, box_y, box_x + box_w, box_y + box_h,
                                     fill='#0a0a1a', outline='#ffcc00', width=3, tags="dialogue")
        # 内边框
        self.canvas.create_rectangle(box_x + 6, box_y + 6, box_x + box_w - 6, box_y + box_h - 6,
                                     fill='', outline='#8b6914', width=1, tags="dialogue")

        # NPC名称
        npc_name = self.dialogue_npc.npc_id if self.dialogue_npc else "???"
        npc_color = ColorPalette.MERCHANT if self.dialogue_npc and self.dialogue_npc.npc_type == NPCType.MERCHANT else ColorPalette.GUARD
        self.canvas.create_text(box_x + 20, box_y + 18,
                                text=f"[{npc_name}]",
                                fill=npc_color, font=self.normal_font,
                                anchor='w', tags="dialogue")

        # 对话内容
        text = self.dialogue_tree.current_node.text
        max_chars_per_line = 50
        lines = []
        current_line = ""
        for char in text:
            if len(current_line) >= max_chars_per_line and char == ' ':
                lines.append(current_line)
                current_line = ""
            else:
                current_line += char
        if current_line:
            lines.append(current_line)

        text_y = box_y + 45
        for line in lines:
            self.canvas.create_text(box_x + 25, text_y,
                                    text=line,
                                    fill=ColorPalette.UI_TEXT, font=self.normal_font,
                                    anchor='w', tags="dialogue")
            text_y += 22

        # 对话选项
        options = self.dialogue_tree.current_node.options
        opt_y = box_y + 90
        for i, option in enumerate(options):
            opt_text = f"{i + 1}. {option.option_text}"
            self.canvas.create_text(box_x + 30, opt_y,
                                    text=opt_text,
                                    fill='#a0d0ff', font=self.small_font,
                                    anchor='w', tags="dialogue")
            opt_y += 18

    def _game_loop(self):
        """游戏主循环"""
        if not self.running:
            return

        # 更新NPC
        self._update_npcs()

        # 检查对话状态变化
        dialogue_changed = (self.in_dialogue != self._prev_dialogue_state)
        self._prev_dialogue_state = self.in_dialogue

        # 只有实体位置变化时才重绘实体层
        if self._entity_dirty:
            self._draw_entities()
            self._entity_dirty = False

        # 对话框需要更新时才重绘
        if dialogue_changed or self._dialogue_dirty:
            self._draw_dialogue_box()
            self._dialogue_dirty = False

        # UI层更新频率降低（每10帧更新一次）
        if self.frame_count % 10 == 0:
            self._draw_ui()

        self.frame_count += 1

        # 延迟调用 - 约30fps，保持流畅
        self.root.after(33, self._game_loop)

    def run(self):
        """启动游戏"""
        # 初始化时绘制一次地图和UI
        self._draw_map()
        self._draw_poison_zones()
        self._draw_ui()
        self._game_loop()
        self.root.mainloop()


# ========== 主入口 ==========

def main():
    game = MagicTowerGame()
    game.run()


if __name__ == "__main__":
    main()
