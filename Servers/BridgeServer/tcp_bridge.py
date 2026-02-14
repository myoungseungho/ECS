"""
TCP Bridge Server v1.0 - ECS FieldServer Python Implementation
==============================================================

C++ FieldServer의 패킷 핸들러를 Python으로 구현한 브릿지 서버.
Unity 클라이언트가 실제 TCP 소켓으로 접속하여 게임 기능을 테스트할 수 있음.

프로토콜: PacketComponents.h와 100% 동일
  [length:u32 LE][msg_type:u16 LE][payload:variable]

사용법:
  python tcp_bridge.py              # 기본 포트 7777
  python tcp_bridge.py --port 8888  # 커스텀 포트
  python tcp_bridge.py --verbose    # 상세 로그
"""

import asyncio
import struct
import json
import time
import math
import random
import argparse
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from enum import IntEnum

# ━━━ 프로토콜 정의 (PacketComponents.h 미러) ━━━

PACKET_HEADER_SIZE = 6
MAX_PACKET_SIZE = 8192

class MsgType(IntEnum):
    ECHO = 1
    PING = 2

    MOVE = 10
    MOVE_BROADCAST = 11
    POS_QUERY = 12
    APPEAR = 13
    DISAPPEAR = 14
    POSITION_CORRECTION = 15

    CHANNEL_JOIN = 20
    CHANNEL_INFO = 22

    ZONE_ENTER = 30
    ZONE_INFO = 31

    HANDOFF_REQUEST = 40
    HANDOFF_DATA = 41
    HANDOFF_RESTORE = 42
    HANDOFF_RESULT = 43

    GHOST_QUERY = 50
    GHOST_INFO = 51

    LOGIN = 60
    LOGIN_RESULT = 61
    CHAR_LIST_REQ = 62
    CHAR_LIST_RESP = 63
    CHAR_SELECT = 64
    ENTER_GAME = 65

    GATE_ROUTE_REQ = 70
    GATE_ROUTE_RESP = 71

    TIMER_ADD = 80
    TIMER_INFO = 81
    CONFIG_QUERY = 82
    CONFIG_RESP = 83
    EVENT_SUB_COUNT = 84

    STAT_QUERY = 90
    STAT_SYNC = 91
    STAT_ADD_EXP = 92
    STAT_TAKE_DMG = 93
    STAT_HEAL = 94

    STATS = 99

    ATTACK_REQ = 100
    ATTACK_RESULT = 101
    COMBAT_DIED = 102
    RESPAWN_REQ = 103
    RESPAWN_RESULT = 104

    MONSTER_SPAWN = 110
    MONSTER_MOVE = 111
    MONSTER_AGGRO = 112
    MONSTER_RESPAWN = 113

    ZONE_TRANSFER_REQ = 120
    ZONE_TRANSFER_RESULT = 121

    FIELD_REGISTER = 130
    FIELD_HEARTBEAT = 131
    FIELD_REGISTER_ACK = 132

    BUS_REGISTER = 140
    BUS_PUBLISH = 145
    BUS_MESSAGE = 146

    SKILL_LIST_REQ = 150
    SKILL_LIST_RESP = 151
    SKILL_USE = 152
    SKILL_RESULT = 153

    PARTY_CREATE = 160
    PARTY_INVITE = 161
    PARTY_ACCEPT = 162
    PARTY_LEAVE = 163
    PARTY_INFO = 164
    PARTY_KICK = 165

    INSTANCE_CREATE = 170
    INSTANCE_ENTER = 171
    INSTANCE_LEAVE = 172
    INSTANCE_LEAVE_RESULT = 173
    INSTANCE_INFO = 174

    MATCH_ENQUEUE = 180
    MATCH_DEQUEUE = 181
    MATCH_FOUND = 182
    MATCH_ACCEPT = 183
    MATCH_STATUS = 184

    INVENTORY_REQ = 190
    INVENTORY_RESP = 191
    ITEM_ADD = 192
    ITEM_ADD_RESULT = 193
    ITEM_USE = 194
    ITEM_USE_RESULT = 195
    ITEM_EQUIP = 196
    ITEM_UNEQUIP = 197
    ITEM_EQUIP_RESULT = 198

    BUFF_LIST_REQ = 200
    BUFF_LIST_RESP = 201
    BUFF_APPLY_REQ = 202
    BUFF_RESULT = 203
    BUFF_REMOVE_REQ = 204
    BUFF_REMOVE_RESP = 205

    CONDITION_EVAL = 210
    CONDITION_RESULT = 211

    SPATIAL_QUERY_REQ = 215
    SPATIAL_QUERY_RESP = 216

    LOOT_ROLL_REQ = 220
    LOOT_RESULT = 221

    QUEST_LIST_REQ = 230
    QUEST_LIST_RESP = 231
    QUEST_ACCEPT = 232
    QUEST_ACCEPT_RESULT = 233
    QUEST_PROGRESS = 234
    QUEST_COMPLETE = 235
    QUEST_COMPLETE_RESULT = 236

    CHAT_SEND = 240
    CHAT_MESSAGE = 241
    WHISPER_SEND = 242
    WHISPER_RESULT = 243
    SYSTEM_MESSAGE = 244

    SHOP_OPEN = 250
    SHOP_LIST = 251
    SHOP_BUY = 252
    SHOP_SELL = 253
    SHOP_RESULT = 254

    SKILL_LEVEL_UP = 260
    SKILL_LEVEL_UP_RESULT = 261
    SKILL_POINT_INFO = 262

    BOSS_SPAWN = 270
    BOSS_PHASE_CHANGE = 271
    BOSS_SPECIAL_ATTACK = 272
    BOSS_ENRAGE = 273
    BOSS_DEFEATED = 274

    ADMIN_RELOAD = 280
    ADMIN_RELOAD_RESULT = 281
    ADMIN_GET_CONFIG = 282
    ADMIN_CONFIG_RESP = 283

    # Guild (문파)
    GUILD_CREATE = 290
    GUILD_DISBAND = 291
    GUILD_INVITE = 292
    GUILD_ACCEPT = 293
    GUILD_LEAVE = 294
    GUILD_KICK = 295
    GUILD_INFO_REQ = 296
    GUILD_INFO = 297
    GUILD_LIST_REQ = 298
    GUILD_LIST = 299

    # Trade (거래)
    TRADE_REQUEST = 300
    TRADE_ACCEPT = 301
    TRADE_DECLINE = 302
    TRADE_ADD_ITEM = 303
    TRADE_ADD_GOLD = 304
    TRADE_CONFIRM = 305
    TRADE_CANCEL = 306
    TRADE_RESULT = 307

    # Mail (우편)
    MAIL_SEND = 310
    MAIL_LIST_REQ = 311
    MAIL_LIST = 312
    MAIL_READ = 313
    MAIL_READ_RESP = 314
    MAIL_CLAIM = 315
    MAIL_CLAIM_RESULT = 316
    MAIL_DELETE = 317
    MAIL_DELETE_RESULT = 318

    # Server Selection
    SERVER_LIST_REQ = 320
    SERVER_LIST = 321

    # Character CRUD
    CHARACTER_LIST_REQ = 322
    CHARACTER_LIST = 323
    CHARACTER_CREATE = 324
    CHARACTER_CREATE_RESULT = 325
    CHARACTER_DELETE = 326
    CHARACTER_DELETE_RESULT = 327

    # Tutorial
    TUTORIAL_STEP_COMPLETE = 330
    TUTORIAL_REWARD = 331

    # NPC Dialog
    NPC_INTERACT = 332
    NPC_DIALOG = 333

    # Enhancement
    ENHANCE_REQ = 340
    ENHANCE_RESULT = 341


# ━━━ 패킷 빌드/파싱 유틸 ━━━

def build_packet(msg_type: int, payload: bytes = b'') -> bytes:
    length = PACKET_HEADER_SIZE + len(payload)
    header = struct.pack('<IH', length, msg_type)
    return header + payload

def parse_header(data: bytes) -> Tuple[int, int]:
    """(total_length, msg_type)"""
    length, msg_type = struct.unpack('<IH', data[:6])
    return length, msg_type


# ━━━ ECS 엔티티/컴포넌트 (Python 축소판) ━━━

next_entity_id = 1000

def new_entity() -> int:
    global next_entity_id
    eid = next_entity_id
    next_entity_id += 1
    return eid

@dataclass
class Position:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

@dataclass
class Stats:
    level: int = 1
    hp: int = 100
    max_hp: int = 100
    mp: int = 50
    max_mp: int = 50
    atk: int = 10
    defense: int = 5
    exp: int = 0
    exp_next: int = 100
    equip_atk_bonus: int = 0
    equip_def_bonus: int = 0
    skill_points: int = 0

    def is_alive(self) -> bool:
        return self.hp > 0

    def add_exp(self, amount: int):
        self.exp += amount
        while self.exp >= self.exp_next and self.level < 99:
            self.exp -= self.exp_next
            self.level += 1
            self.max_hp += 20
            self.hp = self.max_hp
            self.max_mp += 10
            self.mp = self.max_mp
            self.atk += 3
            self.defense += 2
            self.exp_next = self.level * 100
            self.skill_points += 1

@dataclass
class InventorySlot:
    item_id: int = 0
    count: int = 0
    equipped: bool = False
    enhance_level: int = 0

@dataclass
class MonsterAI:
    monster_id: int = 0
    state: int = 0  # 0=IDLE,1=PATROL,2=CHASE,3=ATTACK,4=RETURN,5=DEAD
    spawn_x: float = 0.0
    spawn_y: float = 0.0
    spawn_z: float = 0.0
    target_entity: int = 0
    patrol_radius: float = 100.0
    leash_range: float = 500.0
    aggro_table: Dict[int, float] = field(default_factory=dict)

@dataclass
class PlayerSession:
    """TCP 클라이언트 한 명의 전체 상태"""
    writer: asyncio.StreamWriter = None
    entity_id: int = 0
    account_id: int = 0
    username: str = ""
    char_name: str = ""
    logged_in: bool = False
    in_game: bool = False
    zone_id: int = 1
    channel_id: int = 1
    pos: Position = field(default_factory=Position)
    stats: Stats = field(default_factory=Stats)
    inventory: List[InventorySlot] = field(default_factory=lambda: [InventorySlot() for _ in range(20)])
    gold: int = 1000
    skills: Dict[int, int] = field(default_factory=dict)  # skill_id -> level
    party_id: int = 0
    buffs: List[dict] = field(default_factory=list)
    quests: List[dict] = field(default_factory=list)
    violation_count: int = 0  # 이동 검증 위반 횟수
    last_move_time: float = 0.0
    guild_id: int = 0
    trade_partner: int = 0  # entity_id of trade partner, 0=not trading
    trade_items: List[dict] = field(default_factory=list)  # items offered
    trade_gold: int = 0
    trade_confirmed: bool = False
    tutorial_steps: Set[int] = field(default_factory=set)  # completed step IDs


# ━━━ 게임 데이터 정의 ━━━

# 캐릭터 템플릿
CHARACTER_TEMPLATES = [
    {"id": 1, "name": "Warrior_01", "level": 10, "job": 1},
    {"id": 2, "name": "Mage_01", "level": 5, "job": 2},
    {"id": 3, "name": "Archer_01", "level": 8, "job": 3},
]

# 스킬 데이터 (21개)
SKILLS = {
    1: {"name": "BasicAttack", "cd_ms": 0, "dmg": 10, "mp": 0, "range": 150, "type": 0, "effect": 0, "min_level": 1},
    2: {"name": "PowerStrike", "cd_ms": 3000, "dmg": 25, "mp": 10, "range": 150, "type": 0, "effect": 0, "min_level": 1},
    3: {"name": "Fireball", "cd_ms": 5000, "dmg": 40, "mp": 20, "range": 500, "type": 1, "effect": 1, "min_level": 3},
    4: {"name": "Heal", "cd_ms": 8000, "dmg": -30, "mp": 25, "range": 300, "type": 1, "effect": 2, "min_level": 5},
    5: {"name": "Shield", "cd_ms": 15000, "dmg": 0, "mp": 15, "range": 0, "type": 2, "effect": 3, "min_level": 3},
    6: {"name": "ArrowShot", "cd_ms": 2000, "dmg": 20, "mp": 5, "range": 600, "type": 0, "effect": 0, "min_level": 1},
    7: {"name": "DoubleSlash", "cd_ms": 4000, "dmg": 35, "mp": 12, "range": 150, "type": 0, "effect": 0, "min_level": 5},
    8: {"name": "IceBlast", "cd_ms": 6000, "dmg": 35, "mp": 18, "range": 400, "type": 1, "effect": 4, "min_level": 7},
    9: {"name": "Dash", "cd_ms": 10000, "dmg": 0, "mp": 8, "range": 0, "type": 2, "effect": 5, "min_level": 3},
    10: {"name": "Provoke", "cd_ms": 12000, "dmg": 0, "mp": 10, "range": 300, "type": 2, "effect": 6, "min_level": 5},
    11: {"name": "ShieldBash", "cd_ms": 6000, "dmg": 20, "mp": 12, "range": 150, "type": 0, "effect": 7, "min_level": 7},
    12: {"name": "Whirlwind", "cd_ms": 8000, "dmg": 30, "mp": 20, "range": 200, "type": 3, "effect": 0, "min_level": 10},
    13: {"name": "Warcry", "cd_ms": 20000, "dmg": 0, "mp": 15, "range": 0, "type": 2, "effect": 8, "min_level": 10},
    14: {"name": "PoisonArrow", "cd_ms": 7000, "dmg": 15, "mp": 12, "range": 600, "type": 0, "effect": 9, "min_level": 7},
    15: {"name": "RainOfArrows", "cd_ms": 15000, "dmg": 25, "mp": 25, "range": 500, "type": 3, "effect": 0, "min_level": 12},
    16: {"name": "Snipe", "cd_ms": 10000, "dmg": 60, "mp": 20, "range": 800, "type": 0, "effect": 10, "min_level": 15},
    17: {"name": "Thunder", "cd_ms": 8000, "dmg": 50, "mp": 25, "range": 500, "type": 1, "effect": 11, "min_level": 10},
    18: {"name": "Blizzard", "cd_ms": 12000, "dmg": 35, "mp": 30, "range": 400, "type": 3, "effect": 4, "min_level": 12},
    19: {"name": "ManaShield", "cd_ms": 20000, "dmg": 0, "mp": 30, "range": 0, "type": 2, "effect": 12, "min_level": 15},
    20: {"name": "Meteor", "cd_ms": 30000, "dmg": 100, "mp": 50, "range": 600, "type": 3, "effect": 1, "min_level": 20},
    21: {"name": "Resurrection", "cd_ms": 60000, "dmg": -100, "mp": 80, "range": 300, "type": 1, "effect": 13, "min_level": 25},
}

# 상점 데이터
SHOPS = {
    1: {"name": "GeneralStore", "items": [
        {"item_id": 101, "price": 50, "stock": 99},
        {"item_id": 102, "price": 100, "stock": 99},
        {"item_id": 103, "price": 30, "stock": 99},
    ]},
    2: {"name": "WeaponShop", "items": [
        {"item_id": 201, "price": 500, "stock": 10},
        {"item_id": 202, "price": 1000, "stock": 5},
        {"item_id": 203, "price": 2000, "stock": 3},
    ]},
    3: {"name": "ArmorShop", "items": [
        {"item_id": 301, "price": 400, "stock": 10},
        {"item_id": 302, "price": 800, "stock": 5},
        {"item_id": 303, "price": 1500, "stock": 3},
    ]},
}

# 몬스터 스폰 데이터
MONSTER_SPAWNS = [
    # Tutorial zone (zone=0) — P1_S02_S01
    {"id": 9001, "name": "Dummy", "level": 1, "hp": 100, "atk": 0, "def": 999, "zone": 0, "x": 50, "y": 0, "z": 80},
    {"id": 9002, "name": "TutSlime", "level": 1, "hp": 50, "atk": 5, "zone": 0, "x": 100, "y": 0, "z": 120},
    {"id": 9002, "name": "TutSlime", "level": 1, "hp": 50, "atk": 5, "zone": 0, "x": 120, "y": 0, "z": 100},
    {"id": 9002, "name": "TutSlime", "level": 1, "hp": 50, "atk": 5, "zone": 0, "x": 80, "y": 0, "z": 140},
    # ──── Field zone 1: 초원 평야 (Lv.3~8) ────  P2_S01_S01
    {"id": 1001, "name": "Slime", "level": 3, "hp": 50, "atk": 5, "zone": 1, "x": 100, "y": 0, "z": 100},
    {"id": 1001, "name": "Slime", "level": 3, "hp": 50, "atk": 5, "zone": 1, "x": 150, "y": 0, "z": 180},
    {"id": 1001, "name": "Slime", "level": 3, "hp": 50, "atk": 5, "zone": 1, "x": 200, "y": 0, "z": 120},
    {"id": 1002, "name": "Goblin", "level": 5, "hp": 120, "atk": 12, "zone": 1, "x": 300, "y": 0, "z": 200},
    {"id": 1002, "name": "Goblin", "level": 5, "hp": 120, "atk": 12, "zone": 1, "x": 350, "y": 0, "z": 250},
    {"id": 1002, "name": "Goblin", "level": 5, "hp": 120, "atk": 12, "zone": 1, "x": 400, "y": 0, "z": 180},
    {"id": 1003, "name": "Wolf", "level": 5, "hp": 180, "atk": 20, "zone": 1, "x": 500, "y": 0, "z": 400},
    {"id": 1003, "name": "Wolf", "level": 5, "hp": 180, "atk": 20, "zone": 1, "x": 550, "y": 0, "z": 350},
    {"id": 1004, "name": "Bear", "level": 7, "hp": 350, "atk": 30, "zone": 1, "x": 700, "y": 0, "z": 500},
    {"id": 1007, "name": "Bandit", "level": 8, "hp": 300, "atk": 25, "zone": 1, "x": 800, "y": 0, "z": 700},
    {"id": 1007, "name": "Bandit", "level": 8, "hp": 300, "atk": 25, "zone": 1, "x": 850, "y": 0, "z": 650},
    # ──── Field zone 2: 어둠의 숲 (Lv.8~15) ────
    {"id": 1005, "name": "Skeleton", "level": 8, "hp": 200, "atk": 25, "zone": 2, "x": 100, "y": 0, "z": 100},
    {"id": 1005, "name": "Skeleton", "level": 8, "hp": 200, "atk": 25, "zone": 2, "x": 200, "y": 0, "z": 150},
    {"id": 1005, "name": "Skeleton", "level": 10, "hp": 250, "atk": 30, "zone": 2, "x": 400, "y": 0, "z": 300},
    {"id": 1006, "name": "Orc", "level": 10, "hp": 400, "atk": 35, "zone": 2, "x": 300, "y": 0, "z": 200},
    {"id": 1006, "name": "Orc", "level": 12, "hp": 450, "atk": 40, "zone": 2, "x": 500, "y": 0, "z": 400},
    {"id": 1004, "name": "Bear", "level": 12, "hp": 500, "atk": 40, "zone": 2, "x": 800, "y": 0, "z": 600},
    {"id": 1007, "name": "Bandit", "level": 12, "hp": 350, "atk": 38, "zone": 2, "x": 600, "y": 0, "z": 500},
    {"id": 2001, "name": "EliteGolem", "level": 15, "hp": 3000, "atk": 120, "zone": 2, "x": 1000, "y": 0, "z": 1000},
    # ──── Field zone 3: 얼어붙은 봉우리 (Lv.15~20) ────
    {"id": 1008, "name": "IceGolem", "level": 15, "hp": 600, "atk": 45, "zone": 3, "x": 200, "y": 0, "z": 200},
    {"id": 1008, "name": "IceGolem", "level": 15, "hp": 600, "atk": 45, "zone": 3, "x": 400, "y": 0, "z": 300},
    {"id": 1009, "name": "FrostWolf", "level": 15, "hp": 350, "atk": 35, "zone": 3, "x": 500, "y": 0, "z": 500},
    {"id": 1009, "name": "FrostWolf", "level": 15, "hp": 350, "atk": 35, "zone": 3, "x": 600, "y": 0, "z": 400},
    {"id": 1010, "name": "Yeti", "level": 18, "hp": 800, "atk": 55, "zone": 3, "x": 800, "y": 0, "z": 800},
    {"id": 1005, "name": "Skeleton", "level": 18, "hp": 300, "atk": 50, "zone": 3, "x": 1000, "y": 0, "z": 600},
    {"id": 2002, "name": "IceQueenElite", "level": 18, "hp": 2500, "atk": 100, "zone": 3, "x": 1500, "y": 0, "z": 1500},
]

# 보스 데이터
BOSSES = {
    100: {"name": "AncientGolem", "level": 25, "hp": 3000, "zone": 2, "phases": 2, "enrage_sec": 180},
    101: {"name": "Dragon", "level": 30, "hp": 5000, "zone": 3, "phases": 3, "enrage_sec": 240},
    102: {"name": "DemonKing", "level": 40, "hp": 8000, "zone": 3, "phases": 3, "enrage_sec": 300},
}

# 루트 테이블
LOOT_TABLES = {
    1: [  # BasicMonster
        {"item_id": 101, "count": 1, "chance": 0.5},
        {"item_id": 102, "count": 1, "chance": 0.3},
        {"item_id": 103, "count": 2, "chance": 0.2},
    ],
    2: [  # EliteMonster
        {"item_id": 201, "count": 1, "chance": 0.3},
        {"item_id": 202, "count": 1, "chance": 0.15},
        {"item_id": 301, "count": 1, "chance": 0.2},
    ],
}

# 퀘스트 데이터
QUESTS = {
    1: {"name": "SlayGoblins", "type": "kill", "target_monster": 1, "target_count": 3, "reward_exp": 200, "reward_item": 101, "reward_count": 5},
    2: {"name": "WolfHunt", "type": "kill", "target_monster": 2, "target_count": 2, "reward_exp": 350, "reward_item": 102, "reward_count": 3},
    3: {"name": "OrcSlayer", "type": "kill", "target_monster": 3, "target_count": 5, "reward_exp": 500, "reward_item": 201, "reward_count": 1},
}

# 존 경계
ZONE_BOUNDS = {
    0: {"min_x": 0, "max_x": 500, "min_z": 0, "max_z": 500},      # tutorial
    1: {"min_x": 0, "max_x": 1000, "min_z": 0, "max_z": 1000},
    2: {"min_x": 0, "max_x": 2000, "min_z": 0, "max_z": 2000},
    3: {"min_x": 0, "max_x": 3000, "min_z": 0, "max_z": 3000},
    10: {"min_x": 0, "max_x": 300, "min_z": 0, "max_z": 300},     # village
    # 던전 존 (인스턴스)
    100: {"min_x": 0, "max_x": 500, "min_z": 0, "max_z": 500},    # goblin_cave
    101: {"min_x": 0, "max_x": 800, "min_z": 0, "max_z": 800},    # frozen_temple
    102: {"min_x": 0, "max_x": 600, "min_z": 0, "max_z": 600},    # demon_fortress
    103: {"min_x": 0, "max_x": 1000, "min_z": 0, "max_z": 1000},  # ancient_dragon_raid
}

# 서버 리스트 (서버 선택 화면용)
SERVER_LIST_DATA = [
    {"name": "크로노스", "status": 1, "population": 120},   # status: 0=OFF, 1=NORMAL, 2=BUSY, 3=FULL
    {"name": "아르카나", "status": 1, "population": 85},
    {"name": "엘리시움", "status": 2, "population": 350},
]

# 튜토리얼 스텝 보상
TUTORIAL_REWARDS = {
    1: {"reward_type": 0, "amount": 100},     # step 1: 골드 100
    2: {"reward_type": 1, "amount": 101},     # step 2: item_id 101 x1
    3: {"reward_type": 0, "amount": 200},     # step 3: 골드 200
    4: {"reward_type": 2, "amount": 50},      # step 4: 경험치 50
    5: {"reward_type": 0, "amount": 500},     # step 5: 골드 500
}

# NPC 스폰 데이터 (P1_S04_S01, P1_S05_S01)
NPC_SPAWNS = [
    # Tutorial zone (zone=0)
    {"npc_id": 1, "name": "튜토리얼 안내원", "type": "quest", "zone": 0, "x": 10.0, "y": 0.0, "z": 10.0, "quest_ids": [1]},
    # Village zone (zone=10)
    {"npc_id": 2, "name": "마을 장로", "type": "quest", "zone": 10, "x": 0.0, "y": 0.0, "z": 0.0, "quest_ids": [2, 3]},
    {"npc_id": 3, "name": "상점 주인", "type": "shop", "zone": 10, "x": 15.0, "y": 0.0, "z": 5.0, "shop_id": 1},
    {"npc_id": 4, "name": "무기 상인", "type": "shop", "zone": 10, "x": 20.0, "y": 0.0, "z": 5.0, "shop_id": 2},
    {"npc_id": 5, "name": "방어구 상인", "type": "shop", "zone": 10, "x": 20.0, "y": 0.0, "z": -5.0, "shop_id": 3},
    {"npc_id": 6, "name": "대장장이", "type": "blacksmith", "zone": 10, "x": -10.0, "y": 0.0, "z": 5.0},
    {"npc_id": 7, "name": "퀘스트 게시판", "type": "quest", "zone": 10, "x": 5.0, "y": 0.0, "z": -10.0, "quest_ids": [1, 2, 3]},
    {"npc_id": 8, "name": "스킬 트레이너", "type": "skill", "zone": 10, "x": -5.0, "y": 0.0, "z": -10.0},
]

# NPC 대화 데이터
NPC_DIALOGS = {
    1: [
        {"speaker": "튜토리얼 안내원", "text": "모험가여, 환영하네! 자네의 여정을 도와주지."},
        {"speaker": "튜토리얼 안내원", "text": "먼저 WASD로 이동해보게. 그리고 저 허수아비를 공격해보게나."},
        {"speaker": "튜토리얼 안내원", "text": "슬라임도 처치해보게. 실전 전투 연습이 될 거야."},
    ],
    2: [
        {"speaker": "마을 장로", "text": "오, 젊은 모험가. 마을에 일이 생겼다네..."},
        {"speaker": "마을 장로", "text": "마을 근처에 고블린이 출몰하고 있소. 퇴치해 주겠는가?"},
    ],
    3: [
        {"speaker": "상점 주인", "text": "어서오세요! 필요한 물건이 있으신가요?"},
    ],
    4: [
        {"speaker": "무기 상인", "text": "최고급 무기를 갖추고 있습니다!"},
    ],
    5: [
        {"speaker": "방어구 상인", "text": "튼튼한 방어구, 여기 다 있습니다."},
    ],
    6: [
        {"speaker": "대장장이", "text": "뭘 강화할 건가? 내 솜씨를 보여주지."},
    ],
    7: [
        {"speaker": "퀘스트 게시판", "text": "[의뢰 목록을 확인한다]"},
    ],
    8: [
        {"speaker": "스킬 트레이너", "text": "새로운 기술을 배우고 싶은가? 잘 찾아왔어."},
    ],
}

# 강화 확률 테이블 (P2_S02_S01)
ENHANCE_TABLE = {
    1: 0.90,   # +1: 90%
    2: 0.80,   # +2: 80%
    3: 0.70,   # +3: 70%
    4: 0.60,   # +4: 60%
    5: 0.50,   # +5: 50%
    6: 0.40,   # +6: 40%
    7: 0.30,   # +7: 30%
    8: 0.20,   # +8: 20%
    9: 0.10,   # +9: 10%
    10: 0.05,  # +10: 5%
}
ENHANCE_COST_BASE = 500  # 강화 비용 = base * level

# ──── 던전 목록 데이터 (P2_S03_S01) ────
DUNGEON_LIST_DATA = [
    {"id": 1, "name": "고블린 동굴",    "type": "party", "min_level": 15, "stages": 3, "zone_id": 100, "party_size": 4, "boss_id": 3004, "boss_hp": 30000},
    {"id": 2, "name": "얼어붙은 신전",  "type": "party", "min_level": 25, "stages": 4, "zone_id": 101, "party_size": 4, "boss_id": 3005, "boss_hp": 80000},
    {"id": 3, "name": "마왕의 요새",    "type": "abyss", "min_level": 40, "stages": 3, "zone_id": 102, "party_size": 4, "boss_id": 3003, "boss_hp": 200000},
    {"id": 4, "name": "고대 용의 둥지", "type": "raid",  "min_level": 50, "stages": 1, "zone_id": 103, "party_size": 8, "boss_id": 3002, "boss_hp": 2000000},
]

MATCH_TIMEOUT = 300  # 매칭 최대 대기 5분
MATCH_FLEX_AFTER = 120  # 2분 후 조건 완화

# 던전 난이도 보정
DIFFICULTY_MULT = {
    "normal": {"hp": 1.0, "atk": 1.0, "reward": 1.0},
    "hard":   {"hp": 2.0, "atk": 1.5, "reward": 2.0},
    "hell":   {"hp": 4.0, "atk": 2.5, "reward": 4.0},
}

# 이동 상수
MOVEMENT = {
    "base_speed": 200.0,
    "sprint_mult": 1.5,
    "mount_mult": 2.0,
    "tolerance": 1.5,
    "max_violations": 5,
}


# ━━━ 브릿지 서버 ━━━

class BridgeServer:
    def __init__(self, port: int = 7777, verbose: bool = False):
        self.port = port
        self.verbose = verbose
        self.sessions: Dict[int, PlayerSession] = {}  # entity_id -> session
        self.writers: Dict[asyncio.StreamWriter, PlayerSession] = {}
        self.monsters: Dict[int, dict] = {}  # entity_id -> monster data
        self.parties: Dict[int, dict] = {}   # party_id -> party data
        self.next_party_id = 1
        self.next_account_id = 1000
        self.tick_count = 0
        self.start_time = time.time()
        self._running = False
        self.guilds: Dict[int, dict] = {}  # guild_id -> guild data
        self.next_guild_id = 1
        self.trades: Dict[int, dict] = {}  # entity_id -> trade session
        self.mails: Dict[int, List[dict]] = {}  # account_id -> mail list
        self.next_mail_id = 1
        self.characters: Dict[int, List[dict]] = {}  # account_id -> character list
        self.next_char_id = 1
        self.npcs: Dict[int, dict] = {}  # entity_id -> npc data
        self.instances: Dict[int, dict] = {}  # instance_id -> instance data
        self.next_instance_id = 1
        self.match_queue: Dict[int, dict] = {}  # dungeon_id -> {players: [], created_at: float}

    def log(self, msg: str, level: str = "INFO"):
        ts = time.strftime("%H:%M:%S")
        prefix = {"INFO": "  ", "RECV": "<<", "SEND": ">>", "GAME": "**", "ERR": "!!"}.get(level, "  ")
        print(f"[{ts}] {prefix} {msg}")

    # ━━━ 네트워크 ━━━

    async def start(self):
        server = await asyncio.start_server(
            self._on_client_connected, '0.0.0.0', self.port
        )
        self._running = True
        self.log(f"TCP Bridge Server started on port {self.port}", "INFO")
        self.log(f"Waiting for Unity client connections...", "INFO")

        # 몬스터 스폰
        self._spawn_monsters()
        self._spawn_npcs()

        # 게임 틱 루프 시작
        asyncio.create_task(self._game_tick_loop())

        async with server:
            await server.serve_forever()

    async def _on_client_connected(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info('peername')
        self.log(f"Client connected: {addr}", "INFO")

        session = PlayerSession(writer=writer)
        self.writers[writer] = session

        try:
            await self._read_loop(reader, writer, session)
        except (asyncio.IncompleteReadError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as e:
            self.log(f"Client error: {e}", "ERR")
        finally:
            self._on_client_disconnected(writer, session)

    def _on_client_disconnected(self, writer: asyncio.StreamWriter, session: PlayerSession):
        addr = writer.get_extra_info('peername')
        self.log(f"Client disconnected: {addr} (entity={session.entity_id})", "INFO")

        # 파티에서 제거
        if session.party_id and session.party_id in self.parties:
            party = self.parties[session.party_id]
            if session.entity_id in party["members"]:
                party["members"].remove(session.entity_id)
            if not party["members"]:
                del self.parties[session.party_id]

        # 거래 취소
        if session.trade_partner:
            partner_id = session.trade_partner
            if partner_id in self.sessions:
                partner = self.sessions[partner_id]
                partner.trade_partner = 0
                partner.trade_items = []
                partner.trade_gold = 0
                partner.trade_confirmed = False
                self._send(partner, MsgType.TRADE_RESULT, struct.pack('<B', 4))  # cancelled

        # 세션 정리
        if session.entity_id in self.sessions:
            del self.sessions[session.entity_id]
        if writer in self.writers:
            del self.writers[writer]

        # DISAPPEAR 브로드캐스트
        if session.in_game:
            disappear = struct.pack('<Q', session.entity_id)
            self._broadcast_to_zone(session.zone_id, session.entity_id,
                                     MsgType.DISAPPEAR, disappear)

        try:
            writer.close()
        except:
            pass

    async def _read_loop(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, session: PlayerSession):
        recv_buf = bytearray()

        while True:
            data = await reader.read(4096)
            if not data:
                break

            recv_buf.extend(data)

            # 패킷 어셈블링
            while len(recv_buf) >= PACKET_HEADER_SIZE:
                pkt_len = struct.unpack_from('<I', recv_buf, 0)[0]

                if pkt_len < PACKET_HEADER_SIZE or pkt_len > MAX_PACKET_SIZE:
                    self.log(f"Invalid packet length: {pkt_len}", "ERR")
                    return  # 연결 끊기

                if len(recv_buf) < pkt_len:
                    break  # 아직 다 안 옴

                # 완전한 패킷
                packet = bytes(recv_buf[:pkt_len])
                recv_buf = recv_buf[pkt_len:]

                _, msg_type = parse_header(packet)
                payload = packet[PACKET_HEADER_SIZE:]

                if self.verbose:
                    try:
                        name = MsgType(msg_type).name
                    except ValueError:
                        name = f"UNKNOWN({msg_type})"
                    self.log(f"Recv {name} ({len(payload)} bytes)", "RECV")

                await self._dispatch(writer, session, msg_type, payload)

    async def _dispatch(self, writer: asyncio.StreamWriter, session: PlayerSession,
                         msg_type: int, payload: bytes):
        handlers = {
            MsgType.ECHO: self._on_echo,
            MsgType.PING: self._on_ping,
            MsgType.STATS: self._on_stats,
            MsgType.LOGIN: self._on_login,
            MsgType.CHAR_LIST_REQ: self._on_char_list_req,
            MsgType.CHAR_SELECT: self._on_char_select,
            MsgType.MOVE: self._on_move,
            MsgType.POS_QUERY: self._on_pos_query,
            MsgType.CHANNEL_JOIN: self._on_channel_join,
            MsgType.ZONE_ENTER: self._on_zone_enter,
            MsgType.ZONE_TRANSFER_REQ: self._on_zone_transfer,
            MsgType.STAT_QUERY: self._on_stat_query,
            MsgType.STAT_ADD_EXP: self._on_stat_add_exp,
            MsgType.STAT_TAKE_DMG: self._on_stat_take_dmg,
            MsgType.STAT_HEAL: self._on_stat_heal,
            MsgType.ATTACK_REQ: self._on_attack_req,
            MsgType.RESPAWN_REQ: self._on_respawn_req,
            MsgType.SKILL_LIST_REQ: self._on_skill_list_req,
            MsgType.SKILL_USE: self._on_skill_use,
            MsgType.SKILL_LEVEL_UP: self._on_skill_level_up,
            MsgType.PARTY_CREATE: self._on_party_create,
            MsgType.PARTY_INVITE: self._on_party_invite,
            MsgType.PARTY_ACCEPT: self._on_party_accept,
            MsgType.PARTY_LEAVE: self._on_party_leave,
            MsgType.PARTY_KICK: self._on_party_kick,
            MsgType.INVENTORY_REQ: self._on_inventory_req,
            MsgType.ITEM_ADD: self._on_item_add,
            MsgType.ITEM_USE: self._on_item_use,
            MsgType.ITEM_EQUIP: self._on_item_equip,
            MsgType.ITEM_UNEQUIP: self._on_item_unequip,
            MsgType.BUFF_LIST_REQ: self._on_buff_list_req,
            MsgType.BUFF_APPLY_REQ: self._on_buff_apply,
            MsgType.BUFF_REMOVE_REQ: self._on_buff_remove,
            MsgType.LOOT_ROLL_REQ: self._on_loot_roll,
            MsgType.QUEST_LIST_REQ: self._on_quest_list_req,
            MsgType.QUEST_ACCEPT: self._on_quest_accept,
            MsgType.QUEST_PROGRESS: self._on_quest_progress,
            MsgType.QUEST_COMPLETE: self._on_quest_complete,
            MsgType.CHAT_SEND: self._on_chat_send,
            MsgType.WHISPER_SEND: self._on_whisper_send,
            MsgType.SHOP_OPEN: self._on_shop_open,
            MsgType.SHOP_BUY: self._on_shop_buy,
            MsgType.SHOP_SELL: self._on_shop_sell,
            MsgType.CONFIG_QUERY: self._on_config_query,
            MsgType.ADMIN_RELOAD: self._on_admin_reload,
            MsgType.ADMIN_GET_CONFIG: self._on_admin_get_config,
            MsgType.SPATIAL_QUERY_REQ: self._on_spatial_query,
            MsgType.GHOST_QUERY: self._on_ghost_query,
            MsgType.GUILD_CREATE: self._on_guild_create,
            MsgType.GUILD_DISBAND: self._on_guild_disband,
            MsgType.GUILD_INVITE: self._on_guild_invite,
            MsgType.GUILD_ACCEPT: self._on_guild_accept,
            MsgType.GUILD_LEAVE: self._on_guild_leave,
            MsgType.GUILD_KICK: self._on_guild_kick,
            MsgType.GUILD_INFO_REQ: self._on_guild_info_req,
            MsgType.GUILD_LIST_REQ: self._on_guild_list_req,
            MsgType.TRADE_REQUEST: self._on_trade_request,
            MsgType.TRADE_ACCEPT: self._on_trade_accept,
            MsgType.TRADE_DECLINE: self._on_trade_decline,
            MsgType.TRADE_ADD_ITEM: self._on_trade_add_item,
            MsgType.TRADE_ADD_GOLD: self._on_trade_add_gold,
            MsgType.TRADE_CONFIRM: self._on_trade_confirm,
            MsgType.TRADE_CANCEL: self._on_trade_cancel,
            MsgType.MAIL_SEND: self._on_mail_send,
            MsgType.MAIL_LIST_REQ: self._on_mail_list_req,
            MsgType.MAIL_READ: self._on_mail_read,
            MsgType.MAIL_CLAIM: self._on_mail_claim,
            MsgType.MAIL_DELETE: self._on_mail_delete,
            MsgType.SERVER_LIST_REQ: self._on_server_list_req,
            MsgType.CHARACTER_LIST_REQ: self._on_character_list_req,
            MsgType.CHARACTER_CREATE: self._on_character_create,
            MsgType.CHARACTER_DELETE: self._on_character_delete,
            MsgType.TUTORIAL_STEP_COMPLETE: self._on_tutorial_step_complete,
            MsgType.NPC_INTERACT: self._on_npc_interact,
            MsgType.ENHANCE_REQ: self._on_enhance_req,
            MsgType.MATCH_ENQUEUE: self._on_match_enqueue,
            MsgType.MATCH_DEQUEUE: self._on_match_dequeue,
            MsgType.MATCH_ACCEPT: self._on_match_accept,
            MsgType.INSTANCE_ENTER: self._on_instance_enter,
            MsgType.INSTANCE_LEAVE: self._on_instance_leave,
        }

        handler = handlers.get(msg_type)
        if handler:
            await handler(session, payload)
        else:
            try:
                name = MsgType(msg_type).name
            except ValueError:
                name = f"UNKNOWN({msg_type})"
            self.log(f"Unhandled: {name}", "ERR")

    def _send(self, session: PlayerSession, msg_type: int, payload: bytes = b''):
        if session.writer and not session.writer.is_closing():
            pkt = build_packet(msg_type, payload)
            session.writer.write(pkt)
            if self.verbose:
                try:
                    name = MsgType(msg_type).name
                except ValueError:
                    name = f"UNKNOWN({msg_type})"
                self.log(f"Send {name} ({len(payload)} bytes)", "SEND")

    def _broadcast_to_zone(self, zone_id: int, exclude_entity: int,
                            msg_type: int, payload: bytes):
        for eid, s in self.sessions.items():
            if s.zone_id == zone_id and eid != exclude_entity and s.in_game:
                self._send(s, msg_type, payload)

    def _broadcast_to_all(self, msg_type: int, payload: bytes, exclude: int = 0):
        for eid, s in self.sessions.items():
            if eid != exclude and s.in_game:
                self._send(s, msg_type, payload)

    # ━━━ 핸들러: 기본 ━━━

    async def _on_echo(self, session: PlayerSession, payload: bytes):
        self._send(session, MsgType.ECHO, payload)

    async def _on_ping(self, session: PlayerSession, payload: bytes):
        self._send(session, MsgType.PING, b'PONG')

    async def _on_stats(self, session: PlayerSession, payload: bytes):
        entity_count = len(self.sessions) + len(self.monsters)
        stats_str = f"entity_count={entity_count}|sessions={len(self.sessions)}|monsters={len(self.monsters)}|uptime={int(time.time()-self.start_time)}s"
        self._send(session, MsgType.STATS, stats_str.encode('utf-8'))

    # ━━━ 핸들러: 로그인 ━━━

    async def _on_login(self, session: PlayerSession, payload: bytes):
        if len(payload) < 2:
            self._send(session, MsgType.LOGIN_RESULT, struct.pack('<BI', 1, 0))  # FAIL=1
            return

        name_len = payload[0]
        if len(payload) < 1 + name_len + 1:
            self._send(session, MsgType.LOGIN_RESULT, struct.pack('<BI', 1, 0))  # FAIL=1
            return

        username = payload[1:1+name_len].decode('utf-8', errors='replace')
        pw_len = payload[1+name_len]
        password = payload[2+name_len:2+name_len+pw_len].decode('utf-8', errors='replace')

        # 간단한 로그인 (항상 성공)
        session.account_id = self.next_account_id
        self.next_account_id += 1
        session.username = username
        session.logged_in = True

        self.log(f"Login: {username} (account={session.account_id})", "GAME")
        self._send(session, MsgType.LOGIN_RESULT, struct.pack('<BI', 0, session.account_id))  # SUCCESS=0

    async def _on_char_list_req(self, session: PlayerSession, payload: bytes):
        if not session.logged_in:
            self._send(session, MsgType.CHAR_LIST_RESP, struct.pack('<B', 0))
            return

        count = len(CHARACTER_TEMPLATES)
        buf = struct.pack('<B', count)
        for ch in CHARACTER_TEMPLATES:
            name_bytes = ch["name"].encode('utf-8')[:32].ljust(32, b'\x00')
            buf += struct.pack('<I', ch["id"])
            buf += name_bytes
            buf += struct.pack('<II', ch["level"], ch["job"])
        self._send(session, MsgType.CHAR_LIST_RESP, buf)

    async def _on_char_select(self, session: PlayerSession, payload: bytes):
        if len(payload) < 4 or not session.logged_in:
            self._send(session, MsgType.ENTER_GAME, struct.pack('<B', 1) + b'\x00' * 24)  # FAIL=1
            return

        char_id = struct.unpack('<I', payload[:4])[0]
        tmpl = next((c for c in CHARACTER_TEMPLATES if c["id"] == char_id), None)
        if not tmpl:
            self._send(session, MsgType.ENTER_GAME, struct.pack('<B', 1) + b'\x00' * 24)  # FAIL=1
            return

        session.entity_id = new_entity()
        session.char_name = tmpl["name"]
        session.in_game = True
        session.zone_id = 1
        session.pos = Position(100.0, 0.0, 100.0)
        session.stats.level = tmpl["level"]
        session.stats.max_hp = 100 + (tmpl["level"] - 1) * 20
        session.stats.hp = session.stats.max_hp
        session.stats.atk = 10 + (tmpl["level"] - 1) * 3
        session.stats.defense = 5 + (tmpl["level"] - 1) * 2

        # 기본 스킬 부여
        session.skills = {1: 1, 2: 1, 6: 1}

        self.sessions[session.entity_id] = session

        self.log(f"EnterGame: {session.char_name} (entity={session.entity_id}, zone={session.zone_id})", "GAME")

        resp = struct.pack('<BQIfff',
            0, session.entity_id, session.zone_id,  # SUCCESS=0
            session.pos.x, session.pos.y, session.pos.z)
        self._send(session, MsgType.ENTER_GAME, resp)

        # 기존 플레이어에게 APPEAR
        appear_data = struct.pack('<Qfff', session.entity_id,
                                   session.pos.x, session.pos.y, session.pos.z)
        self._broadcast_to_zone(session.zone_id, session.entity_id,
                                 MsgType.APPEAR, appear_data)

        # 이 플레이어에게 기존 플레이어+몬스터 APPEAR
        for eid, other in self.sessions.items():
            if eid != session.entity_id and other.zone_id == session.zone_id and other.in_game:
                a = struct.pack('<Qfff', eid, other.pos.x, other.pos.y, other.pos.z)
                self._send(session, MsgType.APPEAR, a)

        # 존 내 몬스터 전송
        for mid, m in self.monsters.items():
            if m["zone"] == session.zone_id and m["ai"].state != 5:
                spawn_pkt = struct.pack('<QIIIIfff',
                    mid, m["monster_id"], m["level"], m["hp"], m["max_hp"],
                    m["pos"].x, m["pos"].y, m["pos"].z)
                self._send(session, MsgType.MONSTER_SPAWN, spawn_pkt)

        # STAT_SYNC
        self._send_stat_sync(session)

        # 시스템 메시지
        msg = f"Welcome, {session.char_name}! (Zone {session.zone_id})"
        msg_bytes = msg.encode('utf-8')
        self._send(session, MsgType.SYSTEM_MESSAGE,
                    struct.pack('<B', len(msg_bytes)) + msg_bytes)

    # ━━━ 핸들러: 이동 ━━━

    async def _on_move(self, session: PlayerSession, payload: bytes):
        if not session.in_game:
            return

        if len(payload) >= 12:
            x, y, z = struct.unpack_from('<fff', payload, 0)
        else:
            return

        timestamp = 0
        if len(payload) >= 16:
            timestamp = struct.unpack_from('<I', payload, 12)[0]

        # 이동 검증 (Session 35)
        bounds = ZONE_BOUNDS.get(session.zone_id)
        if bounds:
            if not (bounds["min_x"] <= x <= bounds["max_x"] and
                    bounds["min_z"] <= z <= bounds["max_z"]):
                session.violation_count += 1
                if session.violation_count >= MOVEMENT["max_violations"]:
                    self.log(f"KICK: {session.char_name} too many violations", "ERR")
                    return
                # 위치 보정
                cx = max(bounds["min_x"], min(x, bounds["max_x"]))
                cz = max(bounds["min_z"], min(z, bounds["max_z"]))
                correction = struct.pack('<fff', cx, y, cz)
                self._send(session, MsgType.POSITION_CORRECTION, correction)
                return

        # 속도 체크
        now = time.time()
        if session.last_move_time > 0:
            dt = now - session.last_move_time
            if dt > 0:
                dx = x - session.pos.x
                dz = z - session.pos.z
                dist = math.sqrt(dx*dx + dz*dz)
                max_speed = MOVEMENT["base_speed"] * MOVEMENT["mount_mult"] * MOVEMENT["tolerance"]
                if dist > max_speed * dt * 2:  # 여유 있게
                    session.violation_count += 1
                    if session.violation_count >= MOVEMENT["max_violations"]:
                        self.log(f"KICK: {session.char_name} speed hack detected", "ERR")
                        return
                    correction = struct.pack('<fff', session.pos.x, session.pos.y, session.pos.z)
                    self._send(session, MsgType.POSITION_CORRECTION, correction)
                    return

        session.pos.x = x
        session.pos.y = y
        session.pos.z = z
        session.last_move_time = now
        session.violation_count = max(0, session.violation_count - 1)  # 정상이면 감소

        # 브로드캐스트
        bcast = struct.pack('<Qfff', session.entity_id, x, y, z)
        self._broadcast_to_zone(session.zone_id, session.entity_id,
                                 MsgType.MOVE_BROADCAST, bcast)

    async def _on_pos_query(self, session: PlayerSession, payload: bytes):
        if not session.in_game:
            return
        resp = struct.pack('<Qfff', session.entity_id,
                            session.pos.x, session.pos.y, session.pos.z)
        self._send(session, MsgType.MOVE_BROADCAST, resp)

    # ━━━ 핸들러: 채널/존 ━━━

    async def _on_channel_join(self, session: PlayerSession, payload: bytes):
        if len(payload) < 4:
            return
        ch_id = struct.unpack('<I', payload[:4])[0]
        session.channel_id = ch_id
        self._send(session, MsgType.CHANNEL_INFO, struct.pack('<I', ch_id))

    async def _on_zone_enter(self, session: PlayerSession, payload: bytes):
        if len(payload) < 4:
            return
        zone_id = struct.unpack('<I', payload[:4])[0]
        session.zone_id = zone_id
        self._send(session, MsgType.ZONE_INFO, struct.pack('<I', zone_id))

    async def _on_zone_transfer(self, session: PlayerSession, payload: bytes):
        if len(payload) < 4 or not session.in_game:
            self._send(session, MsgType.ZONE_TRANSFER_RESULT,
                        struct.pack('<BIfff', 1, 0, 0.0, 0.0, 0.0))
            return

        target_zone = struct.unpack('<I', payload[:4])[0]
        if target_zone not in ZONE_BOUNDS:
            self._send(session, MsgType.ZONE_TRANSFER_RESULT,
                        struct.pack('<BIfff', 1, target_zone, 0.0, 0.0, 0.0))
            return

        if target_zone == session.zone_id:
            self._send(session, MsgType.ZONE_TRANSFER_RESULT,
                        struct.pack('<BIfff', 2, target_zone, 0.0, 0.0, 0.0))
            return

        # DISAPPEAR
        disappear = struct.pack('<Q', session.entity_id)
        self._broadcast_to_zone(session.zone_id, session.entity_id,
                                 MsgType.DISAPPEAR, disappear)

        old_zone = session.zone_id
        session.zone_id = target_zone
        spawn = ZONE_BOUNDS[target_zone]
        session.pos.x = float(spawn["min_x"] + 100)
        session.pos.z = float(spawn["min_z"] + 100)

        self.log(f"ZoneTransfer: {session.char_name} Zone{old_zone}→Zone{target_zone}", "GAME")

        self._send(session, MsgType.ZONE_TRANSFER_RESULT,
                    struct.pack('<BIfff', 0, target_zone,
                                session.pos.x, session.pos.y, session.pos.z))

        # APPEAR
        appear = struct.pack('<Qfff', session.entity_id,
                              session.pos.x, session.pos.y, session.pos.z)
        self._broadcast_to_zone(target_zone, session.entity_id,
                                 MsgType.APPEAR, appear)

    # ━━━ 핸들러: 스탯 ━━━

    def _send_stat_sync(self, session: PlayerSession):
        s = session.stats
        total_atk = s.atk + s.equip_atk_bonus
        total_def = s.defense + s.equip_def_bonus
        payload = struct.pack('<IiiiiIIII',
            s.level, s.hp, s.max_hp, s.mp, s.max_mp,
            total_atk, total_def, s.exp, s.exp_next)
        self._send(session, MsgType.STAT_SYNC, payload)

    async def _on_stat_query(self, session: PlayerSession, payload: bytes):
        if session.in_game:
            self._send_stat_sync(session)

    async def _on_stat_add_exp(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 4:
            return
        amount = struct.unpack('<I', payload[:4])[0]
        old_level = session.stats.level
        session.stats.add_exp(amount)
        if session.stats.level > old_level:
            self.log(f"LevelUp: {session.char_name} Lv{old_level}→Lv{session.stats.level}", "GAME")
        self._send_stat_sync(session)

    async def _on_stat_take_dmg(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 4:
            return
        raw = struct.unpack('<I', payload[:4])[0]
        actual = max(1, raw - session.stats.defense)
        session.stats.hp = max(0, session.stats.hp - actual)
        self._send_stat_sync(session)

    async def _on_stat_heal(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 4:
            return
        amount = struct.unpack('<I', payload[:4])[0]
        session.stats.hp = min(session.stats.max_hp, session.stats.hp + amount)
        self._send_stat_sync(session)

    # ━━━ 핸들러: 전투 ━━━

    async def _on_attack_req(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 8:
            return

        target = struct.unpack('<Q', payload[:8])[0]

        # 타겟이 몬스터인지 확인
        if target in self.monsters:
            m = self.monsters[target]
            if m["hp"] <= 0:
                self._send(session, MsgType.ATTACK_RESULT,
                            struct.pack('<BQQiII', 0, session.entity_id, target, 0, 0, 0))
                return

            damage = max(1, session.stats.atk + session.stats.equip_atk_bonus - m.get("def", 0))
            m["hp"] = max(0, m["hp"] - damage)

            # 어그로 추가
            m["ai"].aggro_table[session.entity_id] = \
                m["ai"].aggro_table.get(session.entity_id, 0) + damage

            result = struct.pack('<BQQiII', 1, session.entity_id, target,
                                  damage, m["hp"], m["max_hp"])
            self._send(session, MsgType.ATTACK_RESULT, result)
            self._broadcast_to_zone(session.zone_id, session.entity_id,
                                     MsgType.ATTACK_RESULT, result)

            # 어그로 변경 알림
            aggro_pkt = struct.pack('<QQ', target, session.entity_id)
            self._broadcast_to_zone(session.zone_id, 0, MsgType.MONSTER_AGGRO, aggro_pkt)

            if m["hp"] <= 0:
                m["ai"].state = 5  # DEAD
                died = struct.pack('<QQ', target, session.entity_id)
                self._broadcast_to_zone(session.zone_id, 0, MsgType.COMBAT_DIED, died)
                self._send(session, MsgType.COMBAT_DIED, died)

                # 루트 드롭
                loot_table_id = 1 if m["monster_id"] <= 2 else 2
                self._drop_loot(session, loot_table_id)

                # 경험치
                exp = m["level"] * 20
                old_lv = session.stats.level
                session.stats.add_exp(exp)
                if session.stats.level > old_lv:
                    self.log(f"LevelUp: {session.char_name} Lv{old_lv}→Lv{session.stats.level}", "GAME")
                self._send_stat_sync(session)

                # 퀘스트 진행
                self._on_monster_killed(session, m["monster_id"])

                # 리스폰 예약 (10초 후)
                asyncio.get_event_loop().call_later(10.0, self._respawn_monster, target)

                self.log(f"MonsterDied: {m['name']} (killer={session.char_name})", "GAME")

    async def _on_respawn_req(self, session: PlayerSession, payload: bytes):
        if not session.in_game:
            return
        session.stats.hp = session.stats.max_hp
        session.stats.mp = session.stats.max_mp
        bounds = ZONE_BOUNDS.get(session.zone_id, {"min_x": 0, "min_z": 0})
        session.pos.x = float(bounds["min_x"] + 100)
        session.pos.z = float(bounds["min_z"] + 100)
        session.pos.y = 0.0

        resp = struct.pack('<Biifff', 1, session.stats.hp, session.stats.mp,
                            session.pos.x, session.pos.y, session.pos.z)
        self._send(session, MsgType.RESPAWN_RESULT, resp)

    # ━━━ 핸들러: 스킬 ━━━

    async def _on_skill_list_req(self, session: PlayerSession, payload: bytes):
        if not session.in_game:
            return

        skills_to_send = []
        for sid, slevel in session.skills.items():
            if sid in SKILLS:
                skills_to_send.append((sid, slevel, SKILLS[sid]))

        buf = struct.pack('<B', len(skills_to_send))
        for sid, slevel, sdata in skills_to_send:
            name_bytes = sdata["name"].encode('utf-8')[:16].ljust(16, b'\x00')
            # 확장 포맷: +level +effect +min_level
            buf += struct.pack('<I', sid)
            buf += name_bytes
            buf += struct.pack('<IIIIB', sdata["cd_ms"], sdata["dmg"], sdata["mp"],
                               sdata["range"], sdata["type"])
            buf += struct.pack('<BBI', slevel, sdata["effect"], sdata["min_level"])
        self._send(session, MsgType.SKILL_LIST_RESP, buf)

    async def _on_skill_use(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 12:
            return

        skill_id, target_entity = struct.unpack('<IQ', payload[:12])

        if skill_id not in SKILLS or skill_id not in session.skills:
            self._send(session, MsgType.SKILL_RESULT,
                        struct.pack('<BIQQI', 0, skill_id, session.entity_id, target_entity, 0, 0))
            return

        sdata = SKILLS[skill_id]
        slevel = session.skills[skill_id]

        # MP 체크
        if session.stats.mp < sdata["mp"]:
            self._send(session, MsgType.SKILL_RESULT,
                        struct.pack('<BIQQI', 0, skill_id, session.entity_id, target_entity, 0, 0))
            return

        session.stats.mp -= sdata["mp"]
        damage = sdata["dmg"] * slevel

        target_hp = 0
        if target_entity in self.monsters:
            m = self.monsters[target_entity]
            if m["hp"] > 0:
                actual_dmg = max(0, damage)
                m["hp"] = max(0, m["hp"] - actual_dmg)
                target_hp = m["hp"]
                m["ai"].aggro_table[session.entity_id] = \
                    m["ai"].aggro_table.get(session.entity_id, 0) + actual_dmg

                if m["hp"] <= 0:
                    m["ai"].state = 5
                    died = struct.pack('<QQ', target_entity, session.entity_id)
                    self._broadcast_to_zone(session.zone_id, 0, MsgType.COMBAT_DIED, died)
                    self._send(session, MsgType.COMBAT_DIED, died)
                    loot_table_id = 1 if m["monster_id"] <= 2 else 2
                    self._drop_loot(session, loot_table_id)
                    exp = m["level"] * 20
                    session.stats.add_exp(exp)
                    self._on_monster_killed(session, m["monster_id"])
                    asyncio.get_event_loop().call_later(10.0, self._respawn_monster, target_entity)

        result = struct.pack('<BIQQI', 1, skill_id, session.entity_id,
                              target_entity, abs(damage), target_hp)
        self._send(session, MsgType.SKILL_RESULT, result)
        self._broadcast_to_zone(session.zone_id, session.entity_id,
                                 MsgType.SKILL_RESULT, result)
        self._send_stat_sync(session)

    async def _on_skill_level_up(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 4:
            return

        skill_id = struct.unpack('<I', payload[:4])[0]
        if skill_id not in SKILLS:
            self._send(session, MsgType.SKILL_LEVEL_UP_RESULT,
                        struct.pack('<BIbI', 0, skill_id, 0, session.stats.skill_points))
            return

        if session.stats.skill_points <= 0:
            self._send(session, MsgType.SKILL_LEVEL_UP_RESULT,
                        struct.pack('<BIbI', 0, skill_id, 0, session.stats.skill_points))
            return

        current_level = session.skills.get(skill_id, 0)
        if current_level >= 5:
            self._send(session, MsgType.SKILL_LEVEL_UP_RESULT,
                        struct.pack('<BIbI', 0, skill_id, current_level, session.stats.skill_points))
            return

        session.stats.skill_points -= 1
        session.skills[skill_id] = current_level + 1

        self._send(session, MsgType.SKILL_LEVEL_UP_RESULT,
                    struct.pack('<BIBI', 1, skill_id, current_level + 1, session.stats.skill_points))

    # ━━━ 핸들러: 파티 ━━━

    async def _on_party_create(self, session: PlayerSession, payload: bytes):
        if not session.in_game or session.party_id:
            self._send(session, MsgType.PARTY_INFO,
                        struct.pack('<BIQB', 0, 0, 0, 0))
            return

        pid = self.next_party_id
        self.next_party_id += 1
        self.parties[pid] = {"leader": session.entity_id, "members": [session.entity_id]}
        session.party_id = pid

        self.log(f"PartyCreate: {session.char_name} (party={pid})", "GAME")
        self._send_party_info(session)

    async def _on_party_invite(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 8 or not session.party_id:
            return

        target = struct.unpack('<Q', payload[:8])[0]
        if target in self.sessions:
            target_session = self.sessions[target]
            if not target_session.party_id:
                # 자동 수락 (간소화)
                target_session.party_id = session.party_id
                self.parties[session.party_id]["members"].append(target)
                self.log(f"PartyJoin: {target_session.char_name} → party={session.party_id}", "GAME")
                self._send_party_info(session)
                self._send_party_info(target_session)

    async def _on_party_accept(self, session: PlayerSession, payload: bytes):
        pass  # 자동 수락으로 간소화

    async def _on_party_leave(self, session: PlayerSession, payload: bytes):
        if not session.in_game or not session.party_id:
            return

        pid = session.party_id
        if pid in self.parties:
            party = self.parties[pid]
            if session.entity_id in party["members"]:
                party["members"].remove(session.entity_id)
            if party["leader"] == session.entity_id and party["members"]:
                party["leader"] = party["members"][0]
            if not party["members"]:
                del self.parties[pid]

        session.party_id = 0
        self._send(session, MsgType.PARTY_INFO, struct.pack('<BIQB', 1, 0, 0, 0))

    async def _on_party_kick(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 8 or not session.party_id:
            return
        target = struct.unpack('<Q', payload[:8])[0]
        pid = session.party_id
        if pid in self.parties and self.parties[pid]["leader"] == session.entity_id:
            if target in self.parties[pid]["members"]:
                self.parties[pid]["members"].remove(target)
                if target in self.sessions:
                    self.sessions[target].party_id = 0

    def _send_party_info(self, session: PlayerSession):
        if not session.party_id or session.party_id not in self.parties:
            self._send(session, MsgType.PARTY_INFO, struct.pack('<BIQB', 0, 0, 0, 0))
            return

        party = self.parties[session.party_id]
        count = len(party["members"])
        buf = struct.pack('<BIQB', 1, session.party_id, party["leader"], count)
        for eid in party["members"]:
            s = self.sessions.get(eid)
            level = s.stats.level if s else 1
            buf += struct.pack('<QI', eid, level)
        self._send(session, MsgType.PARTY_INFO, buf)

    # ━━━ 핸들러: 인벤토리 ━━━

    async def _on_inventory_req(self, session: PlayerSession, payload: bytes):
        if not session.in_game:
            return
        slots = [(i, s) for i, s in enumerate(session.inventory) if s.item_id > 0]
        buf = struct.pack('<B', len(slots))
        for i, s in slots:
            buf += struct.pack('<BIHB', i, s.item_id, s.count, 1 if s.equipped else 0)
        self._send(session, MsgType.INVENTORY_RESP, buf)

    async def _on_item_add(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 6:
            return
        item_id, count = struct.unpack('<IH', payload[:6])
        slot_idx = self._find_empty_slot(session)
        if slot_idx >= 0:
            session.inventory[slot_idx].item_id = item_id
            session.inventory[slot_idx].count = count
            self._send(session, MsgType.ITEM_ADD_RESULT,
                        struct.pack('<BBIH', 1, slot_idx, item_id, count))
        else:
            self._send(session, MsgType.ITEM_ADD_RESULT,
                        struct.pack('<BBIH', 0, 0, item_id, count))

    async def _on_item_use(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 1:
            return
        slot = payload[0]
        if 0 <= slot < len(session.inventory) and session.inventory[slot].item_id > 0:
            item_id = session.inventory[slot].item_id
            session.inventory[slot].count -= 1
            if session.inventory[slot].count <= 0:
                session.inventory[slot] = InventorySlot()
            self._send(session, MsgType.ITEM_USE_RESULT,
                        struct.pack('<BBI', 1, slot, item_id))
        else:
            self._send(session, MsgType.ITEM_USE_RESULT,
                        struct.pack('<BBI', 0, slot, 0))

    async def _on_item_equip(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 1:
            return
        slot = payload[0]
        if 0 <= slot < len(session.inventory) and session.inventory[slot].item_id > 0:
            session.inventory[slot].equipped = True
            item_id = session.inventory[slot].item_id
            # 장비 스탯 반영 (간이)
            if 200 <= item_id < 300:  # 무기
                session.stats.equip_atk_bonus += 10
            elif 300 <= item_id < 400:  # 방어구
                session.stats.equip_def_bonus += 8
            self._send(session, MsgType.ITEM_EQUIP_RESULT,
                        struct.pack('<BBIB', 1, slot, item_id, 1))
            self._send_stat_sync(session)
        else:
            self._send(session, MsgType.ITEM_EQUIP_RESULT,
                        struct.pack('<BBIB', 0, slot, 0, 0))

    async def _on_item_unequip(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 1:
            return
        slot = payload[0]
        if 0 <= slot < len(session.inventory) and session.inventory[slot].equipped:
            session.inventory[slot].equipped = False
            item_id = session.inventory[slot].item_id
            if 200 <= item_id < 300:
                session.stats.equip_atk_bonus = max(0, session.stats.equip_atk_bonus - 10)
            elif 300 <= item_id < 400:
                session.stats.equip_def_bonus = max(0, session.stats.equip_def_bonus - 8)
            self._send(session, MsgType.ITEM_EQUIP_RESULT,
                        struct.pack('<BBIB', 1, slot, item_id, 0))
            self._send_stat_sync(session)
        else:
            self._send(session, MsgType.ITEM_EQUIP_RESULT,
                        struct.pack('<BBIB', 0, slot, 0, 0))

    def _find_empty_slot(self, session: PlayerSession) -> int:
        for i, s in enumerate(session.inventory):
            if s.item_id == 0:
                return i
        return -1

    # ━━━ 핸들러: 버프 ━━━

    async def _on_buff_list_req(self, session: PlayerSession, payload: bytes):
        if not session.in_game:
            return
        buf = struct.pack('<B', len(session.buffs))
        for b in session.buffs:
            remaining = max(0, int(b["expires"] - time.time()) * 1000)
            buf += struct.pack('<IIB', b["buff_id"], remaining, b.get("stacks", 1))
        self._send(session, MsgType.BUFF_LIST_RESP, buf)

    async def _on_buff_apply(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 4:
            return
        buff_id = struct.unpack('<I', payload[:4])[0]
        duration_ms = 30000  # 30초
        session.buffs.append({
            "buff_id": buff_id,
            "expires": time.time() + duration_ms / 1000,
            "stacks": 1,
        })
        self._send(session, MsgType.BUFF_RESULT,
                    struct.pack('<BIBI', 1, buff_id, 1, duration_ms))

    async def _on_buff_remove(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 4:
            return
        buff_id = struct.unpack('<I', payload[:4])[0]
        session.buffs = [b for b in session.buffs if b["buff_id"] != buff_id]
        self._send(session, MsgType.BUFF_REMOVE_RESP, struct.pack('<BI', 1, buff_id))

    # ━━━ 핸들러: 루트 ━━━

    async def _on_loot_roll(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 4:
            return
        table_id = struct.unpack('<I', payload[:4])[0]
        self._drop_loot(session, table_id)

    def _drop_loot(self, session: PlayerSession, table_id: int):
        table = LOOT_TABLES.get(table_id, [])
        drops = []
        for entry in table:
            if random.random() < entry["chance"]:
                drops.append((entry["item_id"], entry["count"]))

        buf = struct.pack('<B', len(drops))
        for item_id, count in drops:
            buf += struct.pack('<IH', item_id, count)
            # 인벤에 추가
            slot = self._find_empty_slot(session)
            if slot >= 0:
                session.inventory[slot].item_id = item_id
                session.inventory[slot].count = count

        self._send(session, MsgType.LOOT_RESULT, buf)

    # ━━━ 핸들러: 퀘스트 ━━━

    async def _on_quest_list_req(self, session: PlayerSession, payload: bytes):
        if not session.in_game:
            return
        buf = struct.pack('<B', len(session.quests))
        for q in session.quests:
            buf += struct.pack('<IBII', q["quest_id"], q["state"], q["progress"], q["target"])
        self._send(session, MsgType.QUEST_LIST_RESP, buf)

    async def _on_quest_accept(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 4:
            return
        qid = struct.unpack('<I', payload[:4])[0]
        if qid not in QUESTS:
            self._send(session, MsgType.QUEST_ACCEPT_RESULT, struct.pack('<BI', 0, qid))
            return
        qdata = QUESTS[qid]
        session.quests.append({
            "quest_id": qid,
            "state": 1,  # active
            "progress": 0,
            "target": qdata["target_count"],
        })
        self._send(session, MsgType.QUEST_ACCEPT_RESULT, struct.pack('<BI', 1, qid))

    async def _on_quest_progress(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 4:
            return
        qid = struct.unpack('<I', payload[:4])[0]
        for q in session.quests:
            if q["quest_id"] == qid:
                buf = struct.pack('<IBII', qid, q["state"], q["progress"], q["target"])
                self._send(session, MsgType.QUEST_LIST_RESP, struct.pack('<B', 1) + buf)
                return

    async def _on_quest_complete(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 4:
            return
        qid = struct.unpack('<I', payload[:4])[0]
        for q in session.quests:
            if q["quest_id"] == qid and q["progress"] >= q["target"] and q["state"] == 1:
                q["state"] = 2  # complete
                qdata = QUESTS.get(qid, {})
                reward_exp = qdata.get("reward_exp", 0)
                reward_item = qdata.get("reward_item", 0)
                reward_count = qdata.get("reward_count", 0)
                session.stats.add_exp(reward_exp)
                if reward_item > 0:
                    slot = self._find_empty_slot(session)
                    if slot >= 0:
                        session.inventory[slot].item_id = reward_item
                        session.inventory[slot].count = reward_count
                self._send(session, MsgType.QUEST_COMPLETE_RESULT,
                            struct.pack('<BIIIH', 1, qid, reward_exp, reward_item, reward_count))
                self._send_stat_sync(session)
                return

        self._send(session, MsgType.QUEST_COMPLETE_RESULT,
                    struct.pack('<BIIIH', 0, qid, 0, 0, 0))

    def _on_monster_killed(self, session: PlayerSession, monster_id: int):
        for q in session.quests:
            if q["state"] == 1:
                qdata = QUESTS.get(q["quest_id"])
                if qdata and qdata["type"] == "kill" and qdata["target_monster"] == monster_id:
                    q["progress"] = min(q["progress"] + 1, q["target"])

    # ━━━ 핸들러: 채팅 ━━━

    async def _on_chat_send(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 2:
            return
        channel = payload[0]
        msg_len = payload[1]
        message = payload[2:2+msg_len].decode('utf-8', errors='replace')

        name_bytes = session.char_name.encode('utf-8')[:32].ljust(32, b'\x00')
        chat_pkt = struct.pack('<B', channel) + \
                   struct.pack('<Q', session.entity_id) + \
                   name_bytes + \
                   struct.pack('<B', msg_len) + \
                   message.encode('utf-8')[:msg_len]

        if channel == 0:  # Zone
            self._broadcast_to_zone(session.zone_id, 0, MsgType.CHAT_MESSAGE, chat_pkt)
        elif channel == 1:  # Party
            if session.party_id and session.party_id in self.parties:
                for eid in self.parties[session.party_id]["members"]:
                    if eid in self.sessions:
                        self._send(self.sessions[eid], MsgType.CHAT_MESSAGE, chat_pkt)
        elif channel == 3:  # System (admin only, broadcast to all)
            self._broadcast_to_all(MsgType.CHAT_MESSAGE, chat_pkt)

        if self.verbose:
            self.log(f"Chat[ch{channel}] {session.char_name}: {message}", "GAME")

    async def _on_whisper_send(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 2:
            return
        target_name_len = payload[0]
        target_name = payload[1:1+target_name_len].decode('utf-8', errors='replace')
        msg_len = payload[1+target_name_len]
        message = payload[2+target_name_len:2+target_name_len+msg_len].decode('utf-8', errors='replace')

        # 대상 찾기
        target_session = None
        for s in self.sessions.values():
            if s.char_name == target_name:
                target_session = s
                break

        if not target_session:
            # 실패 응답: WhisperResult::TARGET_NOT_FOUND=1
            other_name = target_name.encode('utf-8')[:32].ljust(32, b'\x00')
            self._send(session, MsgType.WHISPER_RESULT,
                        struct.pack('<BB', 1, 1) + other_name +
                        struct.pack('<B', 0))
            return

        # 발신자에게: WhisperResult::SUCCESS=0, WhisperDirection::SENT=1
        other_name = target_name.encode('utf-8')[:32].ljust(32, b'\x00')
        self._send(session, MsgType.WHISPER_RESULT,
                    struct.pack('<BB', 0, 1) + other_name +
                    struct.pack('<B', msg_len) + message.encode('utf-8')[:msg_len])

        # 수신자에게: WhisperResult::SUCCESS=0, WhisperDirection::RECEIVED=0
        sender_name = session.char_name.encode('utf-8')[:32].ljust(32, b'\x00')
        self._send(target_session, MsgType.WHISPER_RESULT,
                    struct.pack('<BB', 0, 0) + sender_name +
                    struct.pack('<B', msg_len) + message.encode('utf-8')[:msg_len])

    # ━━━ 핸들러: 상점 ━━━

    async def _on_shop_open(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 4:
            return
        npc_id = struct.unpack('<I', payload[:4])[0]
        shop = SHOPS.get(npc_id)
        if not shop:
            return

        items = shop["items"]
        buf = struct.pack('<IB', npc_id, len(items))
        for item in items:
            buf += struct.pack('<IIH', item["item_id"], item["price"], item["stock"])
        self._send(session, MsgType.SHOP_LIST, buf)

    async def _on_shop_buy(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 10:
            return
        npc_id, item_id, count = struct.unpack('<IIH', payload[:10])
        shop = SHOPS.get(npc_id)
        if not shop:
            # ShopResult::SHOP_NOT_FOUND=1, ShopAction::BUY=0
            self._send(session, MsgType.SHOP_RESULT,
                        struct.pack('<BBIH', 1, 0, item_id, count) + struct.pack('<I', session.gold))
            return

        item_data = next((i for i in shop["items"] if i["item_id"] == item_id), None)
        if not item_data:
            # ShopResult::ITEM_NOT_FOUND=2, ShopAction::BUY=0
            self._send(session, MsgType.SHOP_RESULT,
                        struct.pack('<BBIH', 2, 0, item_id, count) + struct.pack('<I', session.gold))
            return

        total_price = item_data["price"] * count
        if session.gold < total_price:
            # ShopResult::NOT_ENOUGH_GOLD=3, ShopAction::BUY=0
            self._send(session, MsgType.SHOP_RESULT,
                        struct.pack('<BBIH', 3, 0, item_id, count) + struct.pack('<I', session.gold))
            return

        slot = self._find_empty_slot(session)
        if slot < 0:
            # ShopResult::INVENTORY_FULL=4, ShopAction::BUY=0
            self._send(session, MsgType.SHOP_RESULT,
                        struct.pack('<BBIH', 4, 0, item_id, count) + struct.pack('<I', session.gold))
            return

        session.gold -= total_price
        session.inventory[slot].item_id = item_id
        session.inventory[slot].count = count
        # ShopResult::SUCCESS=0, ShopAction::BUY=0
        self._send(session, MsgType.SHOP_RESULT,
                    struct.pack('<BBIH', 0, 0, item_id, count) + struct.pack('<I', session.gold))
        self.log(f"ShopBuy: {session.char_name} bought {item_id}x{count} (-{total_price}g)", "GAME")

    async def _on_shop_sell(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 3:
            return
        slot = payload[0]
        count = struct.unpack('<H', payload[1:3])[0]

        if slot >= len(session.inventory) or session.inventory[slot].item_id == 0:
            # ShopResult::EMPTY_SLOT=6, ShopAction::SELL=1
            self._send(session, MsgType.SHOP_RESULT,
                        struct.pack('<BBIH', 6, 1, 0, 0) + struct.pack('<I', session.gold))
            return

        item_id = session.inventory[slot].item_id
        sell_count = min(count, session.inventory[slot].count)
        sell_price = 20 * sell_count  # 기본 판매가

        session.gold += sell_price
        session.inventory[slot].count -= sell_count
        if session.inventory[slot].count <= 0:
            session.inventory[slot] = InventorySlot()

        # ShopResult::SUCCESS=0, ShopAction::SELL=1
        self._send(session, MsgType.SHOP_RESULT,
                    struct.pack('<BBIH', 0, 1, item_id, sell_count) + struct.pack('<I', session.gold))

    # ━━━ 핸들러: 기타 ━━━

    async def _on_config_query(self, session: PlayerSession, payload: bytes):
        # 간단한 구현
        self._send(session, MsgType.CONFIG_RESP,
                    struct.pack('<B', 0) + struct.pack('<H', 0))

    async def _on_admin_reload(self, session: PlayerSession, payload: bytes):
        name = ""
        if len(payload) >= 1:
            name_len = payload[0]
            if name_len > 0 and len(payload) >= 1 + name_len:
                name = payload[1:1+name_len].decode('utf-8', errors='replace')

        self.log(f"AdminReload: '{name}' (requested by {session.char_name})", "GAME")
        name_bytes = name.encode('utf-8')
        self._send(session, MsgType.ADMIN_RELOAD_RESULT,
                    struct.pack('<BIIB', 1, 1, 1, len(name_bytes)) + name_bytes)

    async def _on_admin_get_config(self, session: PlayerSession, payload: bytes):
        if len(payload) < 2:
            self._send(session, MsgType.ADMIN_CONFIG_RESP,
                        struct.pack('<BH', 0, 0))
            return
        name_len = payload[0]
        name = payload[1:1+name_len].decode('utf-8', errors='replace')
        key_len = payload[1+name_len]
        key = payload[2+name_len:2+name_len+key_len].decode('utf-8', errors='replace')

        # 간단한 config 조회
        configs = {
            "monster_ai": {
                "move_speed": "80.0", "patrol_radius": "100.0",
                "leash_range": "500.0", "chase_speed_mult": "1.3",
                "attack_range": "200.0"
            },
            "movement_rules": {
                "base_speed": "200.0", "sprint_multiplier": "1.5",
                "tolerance": "1.5"
            },
        }
        section = configs.get(name, {})
        value = section.get(key, "")
        if value:
            v_bytes = value.encode('utf-8')
            self._send(session, MsgType.ADMIN_CONFIG_RESP,
                        struct.pack('<BH', 1, len(v_bytes)) + v_bytes)
        else:
            self._send(session, MsgType.ADMIN_CONFIG_RESP,
                        struct.pack('<BH', 0, 0))

    async def _on_spatial_query(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 17:
            return
        x, y, z, radius = struct.unpack_from('<ffff', payload, 0)
        filter_type = payload[16]

        results = []
        # 플레이어 검색
        if filter_type in (0, 1):
            for eid, s in self.sessions.items():
                if s.zone_id == session.zone_id and s.in_game:
                    dx = s.pos.x - x
                    dz = s.pos.z - z
                    dist = math.sqrt(dx*dx + dz*dz)
                    if dist <= radius:
                        results.append((eid, dist))

        # 몬스터 검색
        if filter_type in (0, 2):
            for mid, m in self.monsters.items():
                if m["zone"] == session.zone_id and m["ai"].state != 5:
                    dx = m["pos"].x - x
                    dz = m["pos"].z - z
                    dist = math.sqrt(dx*dx + dz*dz)
                    if dist <= radius:
                        results.append((mid, dist))

        results.sort(key=lambda r: r[1])
        buf = struct.pack('<B', min(len(results), 255))
        for eid, dist in results[:255]:
            buf += struct.pack('<Qf', eid, dist)
        self._send(session, MsgType.SPATIAL_QUERY_RESP, buf)

    async def _on_ghost_query(self, session: PlayerSession, payload: bytes):
        self._send(session, MsgType.GHOST_INFO, struct.pack('<I', 0))

    # ━━━ 핸들러: 길드 (문파) ━━━

    async def _on_guild_create(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 1:
            self._send(session, MsgType.GUILD_INFO, struct.pack('<BI', 1, 0) + b'\x00' * 42)
            return

        name_len = payload[0]
        if len(payload) < 1 + name_len or name_len == 0 or name_len > 32:
            self._send(session, MsgType.GUILD_INFO, struct.pack('<BI', 2, 0) + b'\x00' * 42)  # invalid name
            return

        guild_name = payload[1:1+name_len].decode('utf-8', errors='replace')

        if session.guild_id:
            self._send(session, MsgType.GUILD_INFO, struct.pack('<BI', 1, 0) + b'\x00' * 42)  # already in guild
            return

        # Create guild
        gid = self.next_guild_id
        self.next_guild_id += 1
        self.guilds[gid] = {
            "id": gid,
            "name": guild_name,
            "master_id": session.entity_id,
            "members": [session.entity_id],
            "level": 1,
            "exp": 0,
            "created": time.time()
        }
        session.guild_id = gid

        self.log(f"GuildCreate: {guild_name} (id={gid}, master={session.char_name})", "GAME")
        self._send_guild_info(session)

    async def _on_guild_disband(self, session: PlayerSession, payload: bytes):
        if not session.in_game or not session.guild_id:
            return

        gid = session.guild_id
        if gid not in self.guilds:
            return

        guild = self.guilds[gid]
        if guild["master_id"] != session.entity_id:
            return  # not master

        # Notify all members
        for member_id in guild["members"]:
            if member_id in self.sessions:
                member_session = self.sessions[member_id]
                member_session.guild_id = 0
                empty_info = struct.pack('<BI', 0, 0) + b'\x00' * 42
                self._send(member_session, MsgType.GUILD_INFO, empty_info)

        del self.guilds[gid]
        self.log(f"GuildDisband: {guild['name']} (id={gid})", "GAME")

    async def _on_guild_invite(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 8 or not session.guild_id:
            return

        target_entity = struct.unpack('<Q', payload[:8])[0]
        if target_entity not in self.sessions:
            self._send(session, MsgType.GUILD_INFO, struct.pack('<BI', 3, 0) + b'\x00' * 42)  # target not found
            return

        target_session = self.sessions[target_entity]
        if not target_session.in_game:
            return

        gid = session.guild_id
        if gid not in self.guilds:
            return

        guild = self.guilds[gid]
        if guild["master_id"] != session.entity_id:
            return  # not master

        if target_session.guild_id:
            self._send(session, MsgType.GUILD_INFO, struct.pack('<BI', 4, 0) + b'\x00' * 42)  # target already in guild
            return

        # Send invite to target
        name_bytes = guild["name"].encode('utf-8')[:32].ljust(32, b'\x00')
        invite_pkt = struct.pack('<I', gid) + name_bytes + struct.pack('<Q', session.entity_id)
        self._send(target_session, MsgType.GUILD_INVITE, invite_pkt)

        self.log(f"GuildInvite: {session.char_name} invited {target_session.char_name} to {guild['name']}", "GAME")

    async def _on_guild_accept(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 4:
            return

        gid = struct.unpack('<I', payload[:4])[0]
        if gid not in self.guilds:
            self._send(session, MsgType.GUILD_INFO, struct.pack('<BI', 5, 0) + b'\x00' * 42)  # guild not found
            return

        if session.guild_id:
            self._send(session, MsgType.GUILD_INFO, struct.pack('<BI', 1, 0) + b'\x00' * 42)  # already in guild
            return

        guild = self.guilds[gid]
        if len(guild["members"]) >= 20:
            self._send(session, MsgType.GUILD_INFO, struct.pack('<BI', 6, 0) + b'\x00' * 42)  # guild full
            return

        # Add to guild
        guild["members"].append(session.entity_id)
        session.guild_id = gid

        self.log(f"GuildAccept: {session.char_name} joined {guild['name']}", "GAME")

        # Send updated guild info to all members
        for member_id in guild["members"]:
            if member_id in self.sessions:
                self._send_guild_info(self.sessions[member_id])

    async def _on_guild_leave(self, session: PlayerSession, payload: bytes):
        if not session.in_game or not session.guild_id:
            return

        gid = session.guild_id
        if gid not in self.guilds:
            return

        guild = self.guilds[gid]
        if guild["master_id"] == session.entity_id:
            # Master must disband, not leave
            self._send(session, MsgType.GUILD_INFO, struct.pack('<BI', 7, gid) + b'\x00' * 42)  # master cannot leave
            return

        # Remove from guild
        if session.entity_id in guild["members"]:
            guild["members"].remove(session.entity_id)

        session.guild_id = 0
        empty_info = struct.pack('<BI', 0, 0) + b'\x00' * 42
        self._send(session, MsgType.GUILD_INFO, empty_info)

        # Notify remaining members
        for member_id in guild["members"]:
            if member_id in self.sessions:
                self._send_guild_info(self.sessions[member_id])

        self.log(f"GuildLeave: {session.char_name} left {guild['name']}", "GAME")

    async def _on_guild_kick(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 8 or not session.guild_id:
            return

        target_entity = struct.unpack('<Q', payload[:8])[0]
        gid = session.guild_id
        if gid not in self.guilds:
            return

        guild = self.guilds[gid]
        if guild["master_id"] != session.entity_id:
            return  # not master

        if target_entity == session.entity_id:
            return  # cannot kick self

        if target_entity not in guild["members"]:
            return

        # Remove target
        guild["members"].remove(target_entity)
        if target_entity in self.sessions:
            target_session = self.sessions[target_entity]
            target_session.guild_id = 0
            empty_info = struct.pack('<BI', 0, 0) + b'\x00' * 42
            self._send(target_session, MsgType.GUILD_INFO, empty_info)

        # Notify remaining members
        for member_id in guild["members"]:
            if member_id in self.sessions:
                self._send_guild_info(self.sessions[member_id])

        self.log(f"GuildKick: {session.char_name} kicked entity {target_entity} from {guild['name']}", "GAME")

    async def _on_guild_info_req(self, session: PlayerSession, payload: bytes):
        if not session.in_game:
            return
        self._send_guild_info(session)

    async def _on_guild_list_req(self, session: PlayerSession, payload: bytes):
        if not session.in_game:
            return

        count = min(len(self.guilds), 255)
        buf = struct.pack('<B', count)
        for guild in list(self.guilds.values())[:255]:
            name_bytes = guild["name"].encode('utf-8')[:32].ljust(32, b'\x00')
            buf += struct.pack('<I', guild["id"])
            buf += name_bytes
            buf += struct.pack('<BB', len(guild["members"]), guild["level"])
        self._send(session, MsgType.GUILD_LIST, buf)

    def _send_guild_info(self, session: PlayerSession):
        if not session.guild_id or session.guild_id not in self.guilds:
            empty_info = struct.pack('<BI', 0, 0) + b'\x00' * 42
            self._send(session, MsgType.GUILD_INFO, empty_info)
            return

        guild = self.guilds[session.guild_id]
        name_bytes = guild["name"].encode('utf-8')[:32].ljust(32, b'\x00')
        buf = struct.pack('<BI', 0, guild["id"])  # result=0 (success)
        buf += name_bytes
        buf += struct.pack('<QBB', guild["master_id"], len(guild["members"]), guild["level"])
        self._send(session, MsgType.GUILD_INFO, buf)

    # ━━━ 핸들러: 거래 ━━━

    async def _on_trade_request(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 8:
            return

        target_entity = struct.unpack('<Q', payload[:8])[0]
        if target_entity not in self.sessions:
            self._send(session, MsgType.TRADE_RESULT, struct.pack('<B', 1))  # target not found
            return

        target_session = self.sessions[target_entity]
        if not target_session.in_game or target_session.zone_id != session.zone_id:
            self._send(session, MsgType.TRADE_RESULT, struct.pack('<B', 2))  # not in same zone
            return

        if session.trade_partner or target_session.trade_partner:
            self._send(session, MsgType.TRADE_RESULT, struct.pack('<B', 3))  # already trading
            return

        # Create trade session for both
        session.trade_partner = target_entity
        session.trade_items = []
        session.trade_gold = 0
        session.trade_confirmed = False

        target_session.trade_partner = session.entity_id
        target_session.trade_items = []
        target_session.trade_gold = 0
        target_session.trade_confirmed = False

        # Send request to target
        name_bytes = session.char_name.encode('utf-8')[:32].ljust(32, b'\x00')
        req_pkt = struct.pack('<Q', session.entity_id) + name_bytes
        self._send(target_session, MsgType.TRADE_REQUEST, req_pkt)

        # Send success to requester
        self._send(session, MsgType.TRADE_RESULT, struct.pack('<B', 0))  # request sent

        self.log(f"TradeRequest: {session.char_name} → {target_session.char_name}", "GAME")

    async def _on_trade_accept(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 8:
            return

        requester_entity = struct.unpack('<Q', payload[:8])[0]
        if session.trade_partner != requester_entity:
            return

        if requester_entity not in self.sessions:
            return

        requester = self.sessions[requester_entity]

        # Send trade started to both
        self._send(session, MsgType.TRADE_RESULT, struct.pack('<BQ', 0, requester_entity))
        self._send(requester, MsgType.TRADE_RESULT, struct.pack('<BQ', 0, session.entity_id))

        self.log(f"TradeAccept: {requester.char_name} ↔ {session.char_name}", "GAME")

    async def _on_trade_decline(self, session: PlayerSession, payload: bytes):
        if not session.in_game or not session.trade_partner:
            return

        partner_id = session.trade_partner
        if partner_id in self.sessions:
            partner = self.sessions[partner_id]
            partner.trade_partner = 0
            partner.trade_items = []
            partner.trade_gold = 0
            partner.trade_confirmed = False
            self._send(partner, MsgType.TRADE_RESULT, struct.pack('<B', 3))  # declined

        session.trade_partner = 0
        session.trade_items = []
        session.trade_gold = 0
        session.trade_confirmed = False
        self._send(session, MsgType.TRADE_RESULT, struct.pack('<B', 3))  # declined

    async def _on_trade_add_item(self, session: PlayerSession, payload: bytes):
        if not session.in_game or not session.trade_partner or len(payload) < 3:
            return

        slot_index, count = struct.unpack('<BH', payload[:3])
        if slot_index >= len(session.inventory):
            return

        slot = session.inventory[slot_index]
        if slot.item_id == 0 or slot.count < count:
            return

        # Add to trade items
        session.trade_items.append({"slot": slot_index, "item_id": slot.item_id, "count": count})
        session.trade_confirmed = False

        partner_id = session.trade_partner
        if partner_id in self.sessions:
            partner = self.sessions[partner_id]
            partner.trade_confirmed = False
            # Send to partner
            add_pkt = struct.pack('<BIH', slot_index, slot.item_id, count)
            self._send(partner, MsgType.TRADE_ADD_ITEM, add_pkt)

    async def _on_trade_add_gold(self, session: PlayerSession, payload: bytes):
        if not session.in_game or not session.trade_partner or len(payload) < 4:
            return

        amount = struct.unpack('<I', payload[:4])[0]
        if amount > session.gold:
            return

        session.trade_gold = amount
        session.trade_confirmed = False

        partner_id = session.trade_partner
        if partner_id in self.sessions:
            partner = self.sessions[partner_id]
            partner.trade_confirmed = False
            # Send to partner
            self._send(partner, MsgType.TRADE_ADD_GOLD, struct.pack('<I', amount))

    async def _on_trade_confirm(self, session: PlayerSession, payload: bytes):
        if not session.in_game or not session.trade_partner:
            return

        session.trade_confirmed = True

        partner_id = session.trade_partner
        if partner_id not in self.sessions:
            return

        partner = self.sessions[partner_id]

        # Check if both confirmed
        if not partner.trade_confirmed:
            # Send status to partner
            return

        # Execute trade
        # Validate items still available
        valid = True
        for item in session.trade_items:
            slot_idx = item["slot"]
            if slot_idx >= len(session.inventory):
                valid = False
                break
            slot = session.inventory[slot_idx]
            if slot.item_id != item["item_id"] or slot.count < item["count"]:
                valid = False
                break

        for item in partner.trade_items:
            slot_idx = item["slot"]
            if slot_idx >= len(partner.inventory):
                valid = False
                break
            slot = partner.inventory[slot_idx]
            if slot.item_id != item["item_id"] or slot.count < item["count"]:
                valid = False
                break

        if not valid or session.gold < session.trade_gold or partner.gold < partner.trade_gold:
            # Cancel trade
            self._send(session, MsgType.TRADE_RESULT, struct.pack('<B', 5))  # validation failed
            self._send(partner, MsgType.TRADE_RESULT, struct.pack('<B', 5))
            session.trade_partner = 0
            session.trade_items = []
            session.trade_gold = 0
            session.trade_confirmed = False
            partner.trade_partner = 0
            partner.trade_items = []
            partner.trade_gold = 0
            partner.trade_confirmed = False
            return

        # Remove items from session, give to partner
        for item in session.trade_items:
            slot_idx = item["slot"]
            session.inventory[slot_idx].count -= item["count"]
            if session.inventory[slot_idx].count <= 0:
                session.inventory[slot_idx] = InventorySlot()
            # Add to partner
            empty_slot = self._find_empty_slot(partner)
            if empty_slot >= 0:
                partner.inventory[empty_slot].item_id = item["item_id"]
                partner.inventory[empty_slot].count = item["count"]

        # Remove items from partner, give to session
        for item in partner.trade_items:
            slot_idx = item["slot"]
            partner.inventory[slot_idx].count -= item["count"]
            if partner.inventory[slot_idx].count <= 0:
                partner.inventory[slot_idx] = InventorySlot()
            # Add to session
            empty_slot = self._find_empty_slot(session)
            if empty_slot >= 0:
                session.inventory[empty_slot].item_id = item["item_id"]
                session.inventory[empty_slot].count = item["count"]

        # Transfer gold
        session.gold -= session.trade_gold
        partner.gold += session.trade_gold
        partner.gold -= partner.trade_gold
        session.gold += partner.trade_gold

        # Send success
        self._send(session, MsgType.TRADE_RESULT, struct.pack('<B', 0))  # complete
        self._send(partner, MsgType.TRADE_RESULT, struct.pack('<B', 0))  # complete

        self.log(f"TradeComplete: {session.char_name} ↔ {partner.char_name}", "GAME")

        # Clear trade state
        session.trade_partner = 0
        session.trade_items = []
        session.trade_gold = 0
        session.trade_confirmed = False
        partner.trade_partner = 0
        partner.trade_items = []
        partner.trade_gold = 0
        partner.trade_confirmed = False

    async def _on_trade_cancel(self, session: PlayerSession, payload: bytes):
        if not session.in_game or not session.trade_partner:
            return

        partner_id = session.trade_partner
        if partner_id in self.sessions:
            partner = self.sessions[partner_id]
            partner.trade_partner = 0
            partner.trade_items = []
            partner.trade_gold = 0
            partner.trade_confirmed = False
            self._send(partner, MsgType.TRADE_RESULT, struct.pack('<B', 4))  # cancelled

        session.trade_partner = 0
        session.trade_items = []
        session.trade_gold = 0
        session.trade_confirmed = False
        self._send(session, MsgType.TRADE_RESULT, struct.pack('<B', 4))  # cancelled

    # ━━━ 핸들러: 우편 ━━━

    async def _on_mail_send(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 3:
            return

        offset = 0
        recipient_name_len = payload[offset]
        offset += 1
        if len(payload) < offset + recipient_name_len:
            return
        recipient_name = payload[offset:offset+recipient_name_len].decode('utf-8', errors='replace')
        offset += recipient_name_len

        if len(payload) < offset + 1:
            return
        subject_len = payload[offset]
        offset += 1
        if len(payload) < offset + subject_len:
            return
        subject = payload[offset:offset+subject_len].decode('utf-8', errors='replace')
        offset += subject_len

        if len(payload) < offset + 2:
            return
        body_len = struct.unpack_from('<H', payload, offset)[0]
        offset += 2
        if len(payload) < offset + body_len:
            return
        body = payload[offset:offset+body_len].decode('utf-8', errors='replace')
        offset += body_len

        if len(payload) < offset + 10:
            return
        gold, item_id, item_count = struct.unpack_from('<IIH', payload, offset)

        # Find recipient
        recipient_session = None
        recipient_account_id = 0
        for s in self.sessions.values():
            if s.char_name == recipient_name:
                recipient_session = s
                recipient_account_id = s.account_id
                break

        if not recipient_session:
            self._send(session, MsgType.MAIL_DELETE_RESULT, struct.pack('<BI', 1, 0))  # recipient not found
            return

        # Check resources
        if gold > session.gold:
            self._send(session, MsgType.MAIL_DELETE_RESULT, struct.pack('<BI', 2, 0))  # not enough gold
            return

        if item_id > 0:
            # Check if player has item
            has_item = False
            for slot in session.inventory:
                if slot.item_id == item_id and slot.count >= item_count:
                    has_item = True
                    slot.count -= item_count
                    if slot.count <= 0:
                        slot.item_id = 0
                        slot.count = 0
                    break
            if not has_item:
                self._send(session, MsgType.MAIL_DELETE_RESULT, struct.pack('<BI', 3, 0))  # item not found
                return

        # Deduct gold
        session.gold -= gold

        # Create mail
        mail_id = self.next_mail_id
        self.next_mail_id += 1
        mail = {
            "id": mail_id,
            "sender_name": session.char_name,
            "sender_account": session.account_id,
            "subject": subject,
            "body": body,
            "gold": gold,
            "item_id": item_id,
            "item_count": item_count,
            "read": False,
            "claimed": False,
            "sent_time": time.time(),
            "expires": time.time() + 7 * 86400
        }

        if recipient_account_id not in self.mails:
            self.mails[recipient_account_id] = []

        if len(self.mails[recipient_account_id]) >= 50:
            self._send(session, MsgType.MAIL_DELETE_RESULT, struct.pack('<BI', 4, 0))  # mailbox full
            # Refund
            session.gold += gold
            if item_id > 0:
                slot = self._find_empty_slot(session)
                if slot >= 0:
                    session.inventory[slot].item_id = item_id
                    session.inventory[slot].count = item_count
            return

        self.mails[recipient_account_id].append(mail)

        self._send(session, MsgType.MAIL_DELETE_RESULT, struct.pack('<BI', 0, mail_id))  # success
        self.log(f"MailSend: {session.char_name} → {recipient_name} (id={mail_id})", "GAME")

    async def _on_mail_list_req(self, session: PlayerSession, payload: bytes):
        if not session.in_game:
            return

        account_id = session.account_id
        if account_id not in self.mails:
            self._send(session, MsgType.MAIL_LIST, struct.pack('<B', 0))
            return

        # Clean expired mails
        now = time.time()
        self.mails[account_id] = [m for m in self.mails[account_id] if m["expires"] > now]

        mails = self.mails[account_id]
        count = min(len(mails), 255)
        buf = struct.pack('<B', count)
        for mail in mails[:255]:
            sender_name_bytes = mail["sender_name"].encode('utf-8')[:32].ljust(32, b'\x00')
            subject_bytes = mail["subject"].encode('utf-8')[:64].ljust(64, b'\x00')
            has_attachment = 1 if (mail["gold"] > 0 or mail["item_id"] > 0) else 0
            buf += struct.pack('<I', mail["id"])
            buf += sender_name_bytes
            buf += subject_bytes
            buf += struct.pack('<BBI', 1 if mail["read"] else 0, has_attachment, int(mail["sent_time"]))
        self._send(session, MsgType.MAIL_LIST, buf)

    async def _on_mail_read(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 4:
            return

        mail_id = struct.unpack('<I', payload[:4])[0]
        account_id = session.account_id
        if account_id not in self.mails:
            self._send(session, MsgType.MAIL_READ_RESP, struct.pack('<BI', 1, mail_id) + b'\x00' * 200)
            return

        mail = next((m for m in self.mails[account_id] if m["id"] == mail_id), None)
        if not mail:
            self._send(session, MsgType.MAIL_READ_RESP, struct.pack('<BI', 1, mail_id) + b'\x00' * 200)
            return

        # Mark as read
        mail["read"] = True

        sender_name_bytes = mail["sender_name"].encode('utf-8')[:32].ljust(32, b'\x00')
        subject_bytes = mail["subject"].encode('utf-8')[:64].ljust(64, b'\x00')
        body_bytes = mail["body"].encode('utf-8')[:256]
        buf = struct.pack('<BI', 0, mail_id)
        buf += sender_name_bytes
        buf += subject_bytes
        buf += struct.pack('<H', len(body_bytes)) + body_bytes
        buf += struct.pack('<IIH', mail["gold"], mail["item_id"], mail["item_count"])
        self._send(session, MsgType.MAIL_READ_RESP, buf)

    async def _on_mail_claim(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 4:
            return

        mail_id = struct.unpack('<I', payload[:4])[0]
        account_id = session.account_id
        if account_id not in self.mails:
            self._send(session, MsgType.MAIL_CLAIM_RESULT, struct.pack('<BIIIH', 1, mail_id, 0, 0, 0))
            return

        mail = next((m for m in self.mails[account_id] if m["id"] == mail_id), None)
        if not mail:
            self._send(session, MsgType.MAIL_CLAIM_RESULT, struct.pack('<BIIIH', 1, mail_id, 0, 0, 0))
            return

        if mail["claimed"]:
            self._send(session, MsgType.MAIL_CLAIM_RESULT, struct.pack('<BIIIH', 2, mail_id, 0, 0, 0))  # already claimed
            return

        if mail["gold"] == 0 and mail["item_id"] == 0:
            self._send(session, MsgType.MAIL_CLAIM_RESULT, struct.pack('<BIIIH', 3, mail_id, 0, 0, 0))  # no attachment
            return

        # Give gold
        session.gold += mail["gold"]

        # Give item
        if mail["item_id"] > 0:
            slot = self._find_empty_slot(session)
            if slot >= 0:
                session.inventory[slot].item_id = mail["item_id"]
                session.inventory[slot].count = mail["item_count"]
            else:
                # Inventory full, can't claim
                session.gold -= mail["gold"]
                self._send(session, MsgType.MAIL_CLAIM_RESULT, struct.pack('<BIIIH', 4, mail_id, 0, 0, 0))  # inventory full
                return

        mail["claimed"] = True
        self._send(session, MsgType.MAIL_CLAIM_RESULT,
                    struct.pack('<BIIIH', 0, mail_id, mail["gold"], mail["item_id"], mail["item_count"]))

    async def _on_mail_delete(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 4:
            return

        mail_id = struct.unpack('<I', payload[:4])[0]
        account_id = session.account_id
        if account_id not in self.mails:
            self._send(session, MsgType.MAIL_DELETE_RESULT, struct.pack('<BI', 1, mail_id))
            return

        mail = next((m for m in self.mails[account_id] if m["id"] == mail_id), None)
        if not mail:
            self._send(session, MsgType.MAIL_DELETE_RESULT, struct.pack('<BI', 1, mail_id))
            return

        # Check if attachment claimed
        if (mail["gold"] > 0 or mail["item_id"] > 0) and not mail["claimed"]:
            self._send(session, MsgType.MAIL_DELETE_RESULT, struct.pack('<BI', 2, mail_id))  # unclaimed attachment
            return

        # Delete mail
        self.mails[account_id].remove(mail)
        self._send(session, MsgType.MAIL_DELETE_RESULT, struct.pack('<BI', 0, mail_id))

    # ━━━ 핸들러: 서버 선택 ━━━

    async def _on_server_list_req(self, session: PlayerSession, payload: bytes):
        count = len(SERVER_LIST_DATA)
        buf = struct.pack('<B', count)
        for srv in SERVER_LIST_DATA:
            name_bytes = srv["name"].encode('utf-8')[:32].ljust(32, b'\x00')
            buf += name_bytes
            buf += struct.pack('<BH', srv["status"], srv["population"])
        self._send(session, MsgType.SERVER_LIST, buf)
        self.log(f"ServerList: sent {count} servers", "GAME")

    # ━━━ 핸들러: 캐릭터 CRUD ━━━

    async def _on_character_list_req(self, session: PlayerSession, payload: bytes):
        if not session.logged_in:
            self._send(session, MsgType.CHARACTER_LIST, struct.pack('<B', 0))
            return
        chars = self.characters.get(session.account_id, [])
        buf = struct.pack('<B', len(chars))
        for ch in chars:
            name_bytes = ch["name"].encode('utf-8')[:16].ljust(16, b'\x00')
            buf += name_bytes
            buf += struct.pack('<BHI', ch["class"], ch["level"], ch["zone_id"])
        self._send(session, MsgType.CHARACTER_LIST, buf)
        self.log(f"CharacterList: {len(chars)} chars for account {session.account_id}", "GAME")

    async def _on_character_create(self, session: PlayerSession, payload: bytes):
        if not session.logged_in:
            self._send(session, MsgType.CHARACTER_CREATE_RESULT, struct.pack('<BI', 1, 0))
            return
        if len(payload) < 2:
            self._send(session, MsgType.CHARACTER_CREATE_RESULT, struct.pack('<BI', 3, 0))
            return
        name_len = payload[0]
        if len(payload) < 1 + name_len + 1:
            self._send(session, MsgType.CHARACTER_CREATE_RESULT, struct.pack('<BI', 3, 0))
            return
        char_name = payload[1:1+name_len].decode('utf-8', errors='replace')
        char_class = payload[1+name_len]
        if len(char_name) < 2 or len(char_name) > 8:
            self._send(session, MsgType.CHARACTER_CREATE_RESULT, struct.pack('<BI', 3, 0))
            return
        if char_class not in (1, 2, 3):
            self._send(session, MsgType.CHARACTER_CREATE_RESULT, struct.pack('<BI', 1, 0))
            return
        for acct_chars in self.characters.values():
            for ch in acct_chars:
                if ch["name"] == char_name:
                    self._send(session, MsgType.CHARACTER_CREATE_RESULT, struct.pack('<BI', 2, 0))
                    return
        char_id = self.next_char_id
        self.next_char_id += 1
        new_char = {"id": char_id, "name": char_name, "class": char_class, "level": 1, "zone_id": 1}
        if session.account_id not in self.characters:
            self.characters[session.account_id] = []
        self.characters[session.account_id].append(new_char)
        self.log(f"CharCreate: {char_name} class={char_class} (account={session.account_id})", "GAME")
        self._send(session, MsgType.CHARACTER_CREATE_RESULT, struct.pack('<BI', 0, char_id))

    async def _on_character_delete(self, session: PlayerSession, payload: bytes):
        if not session.logged_in:
            self._send(session, MsgType.CHARACTER_DELETE_RESULT, struct.pack('<BI', 2, 0))
            return
        if len(payload) < 4:
            self._send(session, MsgType.CHARACTER_DELETE_RESULT, struct.pack('<BI', 1, 0))
            return
        char_id = struct.unpack('<I', payload[:4])[0]
        chars = self.characters.get(session.account_id, [])
        target = next((ch for ch in chars if ch["id"] == char_id), None)
        if not target:
            self._send(session, MsgType.CHARACTER_DELETE_RESULT, struct.pack('<BI', 1, char_id))
            return
        chars.remove(target)
        self.log(f"CharDelete: {target['name']} id={char_id} (account={session.account_id})", "GAME")
        self._send(session, MsgType.CHARACTER_DELETE_RESULT, struct.pack('<BI', 0, char_id))

    # ━━━ 핸들러: 튜토리얼 ━━━

    async def _on_tutorial_step_complete(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 1:
            return
        step_id = payload[0]
        if step_id in session.tutorial_steps:
            return
        reward = TUTORIAL_REWARDS.get(step_id)
        if not reward:
            return
        session.tutorial_steps.add(step_id)
        reward_type = reward["reward_type"]
        amount = reward["amount"]
        if reward_type == 0:
            session.gold += amount
        elif reward_type == 1:
            for slot in session.inventory:
                if slot.item_id == 0:
                    slot.item_id = amount
                    slot.count = 1
                    break
        elif reward_type == 2:
            session.stats.add_exp(amount)
        self.log(f"Tutorial: step {step_id} complete, reward_type={reward_type} amount={amount} ({session.char_name})", "GAME")
        self._send(session, MsgType.TUTORIAL_REWARD, struct.pack('<BBI', step_id, reward_type, amount))

    # ━━━ 몬스터 시스템 ━━━

    def _spawn_npcs(self):
        """NPC 엔티티 스폰 (P1_S04_S01, P1_S05_S01)"""
        for npc in NPC_SPAWNS:
            eid = new_entity()
            self.npcs[eid] = {
                "entity_id": eid,
                "npc_id": npc["npc_id"],
                "name": npc["name"],
                "type": npc["type"],
                "zone": npc["zone"],
                "pos": Position(npc["x"], npc["y"], npc["z"]),
                "shop_id": npc.get("shop_id"),
                "quest_ids": npc.get("quest_ids", []),
            }
        self.log(f"Spawned {len(self.npcs)} NPCs", "GAME")

    # ━━━ 핸들러: NPC 대화 (P1_S04_S01) ━━━

    async def _on_npc_interact(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 4:
            return
        npc_entity_id = struct.unpack("<I", payload[:4])[0]
        npc = self.npcs.get(npc_entity_id)
        if not npc:
            # npc_id 직접 조회 fallback
            npc_id = npc_entity_id
            for n in self.npcs.values():
                if n["npc_id"] == npc_id:
                    npc = n
                    break
        if not npc:
            return
        dialogs = NPC_DIALOGS.get(npc["npc_id"], [])
        if not dialogs:
            return
        npc_id = npc["npc_id"]
        npc_type_val = {"quest": 0, "shop": 1, "blacksmith": 2, "skill": 3}.get(npc["type"], 0)
        line_count = len(dialogs)
        # 대화 패킷: npc_id(u16) + npc_type(u8) + line_count(u8) + [speaker_len(u8) + speaker + text_len(u16) + text] * N
        buf = struct.pack("<HBB", npc_id, npc_type_val, line_count)
        for d in dialogs:
            speaker_bytes = d["speaker"].encode("utf-8")[:32]
            text_bytes = d["text"].encode("utf-8")[:256]
            buf += struct.pack("<B", len(speaker_bytes)) + speaker_bytes
            buf += struct.pack("<H", len(text_bytes)) + text_bytes
        # quest_ids 추가: quest_count(u8) + [quest_id(u32)] * N
        quest_ids = npc.get("quest_ids", [])
        buf += struct.pack("<B", len(quest_ids))
        for qid in quest_ids:
            buf += struct.pack("<I", qid)
        self._send(session, MsgType.NPC_DIALOG, buf)
        self.log(f"NPC Dialog: npc_id={npc_id} lines={line_count} ({session.char_name})", "GAME")

    # ━━━ 핸들러: 강화 (P2_S02_S01) ━━━

    async def _on_enhance_req(self, session: PlayerSession, payload: bytes):
        """ENHANCE_REQ: slot_index(u8). 해당 슬롯 장비를 강화."""
        if not session.in_game or len(payload) < 1:
            return
        slot_idx = payload[0]
        if slot_idx >= len(session.inventory):
            self._send(session, MsgType.ENHANCE_RESULT, struct.pack("<BBB", slot_idx, 1, 0))  # 1=INVALID_SLOT
            return
        item = session.inventory[slot_idx]
        if item.item_id == 0:
            self._send(session, MsgType.ENHANCE_RESULT, struct.pack("<BBB", slot_idx, 2, 0))  # 2=NO_ITEM
            return
        current_level = getattr(item, "enhance_level", 0)
        if current_level >= 10:
            self._send(session, MsgType.ENHANCE_RESULT, struct.pack("<BBB", slot_idx, 3, current_level))  # 3=MAX_LEVEL
            return
        cost = ENHANCE_COST_BASE * (current_level + 1)
        if session.gold < cost:
            self._send(session, MsgType.ENHANCE_RESULT, struct.pack("<BBB", slot_idx, 4, current_level))  # 4=NO_GOLD
            return
        session.gold -= cost
        import random as _rng
        success_rate = ENHANCE_TABLE.get(current_level + 1, 0.05)
        success = _rng.random() < success_rate
        if success:
            item.enhance_level = current_level + 1
            self.log(f"Enhance: +{item.enhance_level} SUCCESS slot={slot_idx} ({session.char_name})", "GAME")
            self._send(session, MsgType.ENHANCE_RESULT, struct.pack("<BBB", slot_idx, 0, item.enhance_level))  # 0=SUCCESS
        else:
            self.log(f"Enhance: +{current_level + 1} FAIL slot={slot_idx} ({session.char_name})", "GAME")
            self._send(session, MsgType.ENHANCE_RESULT, struct.pack("<BBB", slot_idx, 5, current_level))  # 5=FAIL (level preserved)

    # ━━━ 던전 매칭 시스템 (P2_S03_S01) ━━━

    async def _on_match_enqueue(self, session: PlayerSession, payload: bytes):
        """MATCH_ENQUEUE: dungeon_id(u8) + difficulty(u8). 매칭 큐에 등록."""
        if not session.in_game or len(payload) < 2:
            return
        dungeon_id = payload[0]
        difficulty = payload[1]  # 0=normal, 1=hard, 2=hell
        dungeon = next((d for d in DUNGEON_LIST_DATA if d["id"] == dungeon_id), None)
        if not dungeon:
            # result: 1=INVALID_DUNGEON
            self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 1, 0))
            return
        if session.stats.level < dungeon["min_level"]:
            # result: 2=LEVEL_TOO_LOW
            self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 2, 0))
            return
        import time as _time
        queue_key = dungeon_id
        if queue_key not in self.match_queue:
            self.match_queue[queue_key] = {"players": [], "created_at": _time.time(), "difficulty": difficulty}
        queue = self.match_queue[queue_key]
        # 중복 등록 방지
        if any(p["session"] is session for p in queue["players"]):
            self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 3, len(queue["players"])))
            return
        queue["players"].append({"session": session, "joined_at": _time.time()})
        self.log(f"MatchQueue: {session.char_name} joined dungeon={dungeon_id} ({len(queue['players'])}/{dungeon['party_size']})", "GAME")
        # result: 0=QUEUED, count=현재 인원
        self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 0, len(queue["players"])))
        # 파티 모집 완료 확인
        if len(queue["players"]) >= dungeon["party_size"]:
            await self._match_found(queue_key, dungeon)

    async def _match_found(self, queue_key: int, dungeon: dict):
        """매칭 완료 → 인스턴스 생성 → MATCH_FOUND 전송"""
        queue = self.match_queue.pop(queue_key, None)
        if not queue:
            return
        inst_id = self.next_instance_id
        self.next_instance_id += 1
        diff_name = ["normal", "hard", "hell"][queue.get("difficulty", 0)]
        mult = DIFFICULTY_MULT.get(diff_name, DIFFICULTY_MULT["normal"])
        instance = {
            "id": inst_id,
            "dungeon_id": dungeon["id"],
            "dungeon_name": dungeon["name"],
            "zone_id": dungeon["zone_id"],
            "difficulty": queue.get("difficulty", 0),
            "boss_hp": int(dungeon["boss_hp"] * mult["hp"]),
            "boss_current_hp": int(dungeon["boss_hp"] * mult["hp"]),
            "stage": 1,
            "max_stages": dungeon["stages"],
            "players": [p["session"] for p in queue["players"]],
            "active": True,
        }
        self.instances[inst_id] = instance
        self.log(f"Instance #{inst_id} created: {dungeon['name']} ({diff_name}) with {len(instance['players'])} players", "GAME")
        # MATCH_FOUND: instance_id(u32) + dungeon_id(u8) + difficulty(u8)
        for s in instance["players"]:
            self._send(s, MsgType.MATCH_FOUND, struct.pack("<IBB", inst_id, dungeon["id"], instance["difficulty"]))

    async def _on_match_dequeue(self, session: PlayerSession, payload: bytes):
        """MATCH_DEQUEUE: dungeon_id(u8). 매칭 큐에서 이탈."""
        if not session.in_game or len(payload) < 1:
            return
        dungeon_id = payload[0]
        queue = self.match_queue.get(dungeon_id)
        if queue:
            queue["players"] = [p for p in queue["players"] if p["session"] is not session]
            if not queue["players"]:
                del self.match_queue[dungeon_id]
        self.log(f"MatchQueue: {session.char_name} left dungeon={dungeon_id}", "GAME")
        self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 4, 0))  # 4=DEQUEUED

    async def _on_match_accept(self, session: PlayerSession, payload: bytes):
        """MATCH_ACCEPT: instance_id(u32). 매칭 수락 (현재는 자동 수락)."""
        if not session.in_game or len(payload) < 4:
            return
        inst_id = struct.unpack("<I", payload[:4])[0]
        instance = self.instances.get(inst_id)
        if not instance or not instance["active"]:
            return
        # INSTANCE_INFO 전송
        await self._send_instance_info(session, instance)

    async def _send_instance_info(self, session: PlayerSession, instance: dict):
        """인스턴스 정보 전송"""
        name_bytes = instance["dungeon_name"].encode("utf-8")[:32].ljust(32, b"\x00")
        buf = struct.pack("<IBB", instance["id"], instance["dungeon_id"], instance["difficulty"])
        buf += name_bytes
        buf += struct.pack("<BBII", instance["stage"], instance["max_stages"],
                           instance["boss_hp"], instance["boss_current_hp"])
        buf += struct.pack("<B", len(instance["players"]))
        self._send(session, MsgType.INSTANCE_INFO, buf)

    async def _on_instance_enter(self, session: PlayerSession, payload: bytes):
        """INSTANCE_ENTER: instance_id(u32). 던전 인스턴스 입장."""
        if not session.in_game or len(payload) < 4:
            return
        inst_id = struct.unpack("<I", payload[:4])[0]
        instance = self.instances.get(inst_id)
        if not instance or not instance["active"]:
            self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<IB", inst_id, 1))  # 1=NOT_FOUND
            return
        if session not in instance["players"]:
            self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<IB", inst_id, 2))  # 2=NOT_MEMBER
            return
        # 존 전환
        old_zone = session.zone_id
        session.zone_id = instance["zone_id"]
        session.pos.x = 50.0
        session.pos.y = 0.0
        session.pos.z = 50.0
        self.log(f"InstanceEnter: {session.char_name} → Instance#{inst_id} zone={instance['zone_id']}", "GAME")
        await self._send_instance_info(session, instance)

    async def _on_instance_leave(self, session: PlayerSession, payload: bytes):
        """INSTANCE_LEAVE: instance_id(u32). 던전 퇴장."""
        if not session.in_game or len(payload) < 4:
            return
        inst_id = struct.unpack("<I", payload[:4])[0]
        instance = self.instances.get(inst_id)
        if not instance:
            self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<IB", inst_id, 1))
            return
        if session in instance["players"]:
            instance["players"].remove(session)
        if not instance["players"]:
            instance["active"] = False
            self.log(f"Instance #{inst_id} closed (no players left)", "GAME")
        # 마을로 복귀
        session.zone_id = 10
        session.pos.x = 150.0
        session.pos.y = 0.0
        session.pos.z = 150.0
        self.log(f"InstanceLeave: {session.char_name} ← Instance#{inst_id}", "GAME")
        self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<IB", inst_id, 0))  # 0=OK

    # ━━━ 몬스터 시스템 ━━━

    def _spawn_monsters(self):
        for spawn in MONSTER_SPAWNS:
            eid = new_entity()
            self.monsters[eid] = {
                "entity_id": eid,
                "monster_id": spawn["id"],
                "name": spawn["name"],
                "level": spawn["level"],
                "hp": spawn["hp"],
                "max_hp": spawn["hp"],
                "atk": spawn["atk"],
                "def": spawn.get("def", 0),
                "zone": spawn["zone"],
                "pos": Position(float(spawn["x"]), float(spawn["y"]), float(spawn["z"])),
                "ai": MonsterAI(
                    monster_id=spawn["id"],
                    spawn_x=float(spawn["x"]),
                    spawn_y=float(spawn["y"]),
                    spawn_z=float(spawn["z"]),
                ),
            }
        self.log(f"Spawned {len(self.monsters)} monsters", "GAME")

    def _respawn_monster(self, entity_id: int):
        if entity_id not in self.monsters:
            return
        m = self.monsters[entity_id]
        m["hp"] = m["max_hp"]
        m["ai"].state = 0  # IDLE
        m["ai"].aggro_table.clear()
        m["ai"].target_entity = 0
        m["pos"].x = m["ai"].spawn_x
        m["pos"].y = m["ai"].spawn_y
        m["pos"].z = m["ai"].spawn_z

        # MONSTER_RESPAWN 브로드캐스트
        pkt = struct.pack('<QIIfff', entity_id, m["hp"], m["max_hp"],
                           m["pos"].x, m["pos"].y, m["pos"].z)
        self._broadcast_to_zone(m["zone"], 0, MsgType.MONSTER_RESPAWN, pkt)
        self.log(f"MonsterRespawn: {m['name']} (entity={entity_id})", "GAME")

    async def _game_tick_loop(self):
        """3초마다 몬스터 AI 업데이트"""
        while self._running:
            await asyncio.sleep(3.0)
            self.tick_count += 1
            self._update_monster_ai()
            self._cleanup_expired_buffs()

    def _update_monster_ai(self):
        for mid, m in self.monsters.items():
            if m["ai"].state == 5:  # DEAD
                continue

            ai = m["ai"]

            # 가장 높은 어그로 타겟 찾기
            best_target = 0
            best_aggro = 0.0
            for eid, aggro in list(ai.aggro_table.items()):
                if eid in self.sessions and self.sessions[eid].in_game and \
                   self.sessions[eid].zone_id == m["zone"] and \
                   self.sessions[eid].stats.is_alive():
                    if aggro > best_aggro:
                        best_aggro = aggro
                        best_target = eid
                else:
                    del ai.aggro_table[eid]  # 타겟 제거

            if best_target and ai.state in (0, 1):  # IDLE/PATROL → CHASE
                ai.state = 2  # CHASE
                ai.target_entity = best_target

            if ai.state == 2:  # CHASE
                if not best_target:
                    ai.state = 4  # RETURN
                    ai.target_entity = 0
                else:
                    target = self.sessions.get(best_target)
                    if target:
                        dx = target.pos.x - m["pos"].x
                        dz = target.pos.z - m["pos"].z
                        dist = math.sqrt(dx*dx + dz*dz)

                        # 리쉬 체크
                        sdx = m["pos"].x - ai.spawn_x
                        sdz = m["pos"].z - ai.spawn_z
                        spawn_dist = math.sqrt(sdx*sdx + sdz*sdz)
                        if spawn_dist > ai.leash_range:
                            ai.state = 4  # RETURN
                            ai.target_entity = 0
                            ai.aggro_table.clear()
                        elif dist <= 200.0:  # 공격 범위
                            ai.state = 3  # ATTACK
                        else:
                            # 이동
                            speed = 80.0 * 1.3  # chase speed
                            move_dist = min(speed * 3.0, dist)  # 3초 틱
                            if dist > 0:
                                nx = m["pos"].x + (dx / dist) * move_dist
                                nz = m["pos"].z + (dz / dist) * move_dist
                                m["pos"].x = nx
                                m["pos"].z = nz
                                # MONSTER_MOVE 브로드캐스트
                                move_pkt = struct.pack('<Qfff', mid, nx, m["pos"].y, nz)
                                self._broadcast_to_zone(m["zone"], 0, MsgType.MONSTER_MOVE, move_pkt)

            elif ai.state == 3:  # ATTACK
                if not best_target or best_target not in self.sessions:
                    ai.state = 4  # RETURN
                    ai.target_entity = 0
                else:
                    target = self.sessions[best_target]
                    damage = max(1, m["atk"] - target.stats.defense)
                    target.stats.hp = max(0, target.stats.hp - damage)

                    result = struct.pack('<BQQiII', 1, mid, best_target,
                                          damage, target.stats.hp, target.stats.max_hp)
                    self._broadcast_to_zone(m["zone"], 0, MsgType.ATTACK_RESULT, result)

                    if target.stats.hp <= 0:
                        died = struct.pack('<QQ', best_target, mid)
                        self._broadcast_to_zone(m["zone"], 0, MsgType.COMBAT_DIED, died)
                        ai.aggro_table.pop(best_target, None)
                        ai.state = 0 if not ai.aggro_table else 2

                    self._send_stat_sync(target)

            elif ai.state == 4:  # RETURN
                dx = ai.spawn_x - m["pos"].x
                dz = ai.spawn_z - m["pos"].z
                dist = math.sqrt(dx*dx + dz*dz)
                if dist < 10.0:
                    ai.state = 0  # IDLE
                    m["hp"] = m["max_hp"]  # 귀환 시 회복
                else:
                    speed = 80.0
                    move_dist = min(speed * 3.0, dist)
                    if dist > 0:
                        m["pos"].x += (dx / dist) * move_dist
                        m["pos"].z += (dz / dist) * move_dist
                        move_pkt = struct.pack('<Qfff', mid, m["pos"].x, m["pos"].y, m["pos"].z)
                        self._broadcast_to_zone(m["zone"], 0, MsgType.MONSTER_MOVE, move_pkt)

            elif ai.state == 0:  # IDLE → 랜덤 패트롤
                if random.random() < 0.3:  # 30% 확률로 이동
                    ai.state = 1
                    angle = random.uniform(0, 2 * math.pi)
                    dist = random.uniform(20, ai.patrol_radius)
                    target_x = ai.spawn_x + math.cos(angle) * dist
                    target_z = ai.spawn_z + math.sin(angle) * dist
                    m["pos"].x = target_x
                    m["pos"].z = target_z
                    move_pkt = struct.pack('<Qfff', mid, m["pos"].x, m["pos"].y, m["pos"].z)
                    self._broadcast_to_zone(m["zone"], 0, MsgType.MONSTER_MOVE, move_pkt)
                    ai.state = 0  # 이동 후 다시 IDLE

    def _cleanup_expired_buffs(self):
        now = time.time()
        for session in self.sessions.values():
            session.buffs = [b for b in session.buffs if b["expires"] > now]


# ━━━ 엔트리포인트 ━━━

def main():
    parser = argparse.ArgumentParser(description="TCP Bridge Server - ECS FieldServer Python")
    parser.add_argument('--port', type=int, default=7777, help='Listen port (default: 7777)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    args = parser.parse_args()

    print("=" * 50)
    print("  ECS TCP Bridge Server v1.0")
    print(f"  Port: {args.port}")
    print(f"  Protocol: PacketComponents.h compatible")
    print(f"  Handlers: Login, Move, Chat, Shop, Skill,")
    print(f"            Party, Inventory, Quest, Boss, AI,")
    print(f"            Guild, Trade, Mail")
    print("=" * 50)
    print()

    server = BridgeServer(port=args.port, verbose=args.verbose)

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
