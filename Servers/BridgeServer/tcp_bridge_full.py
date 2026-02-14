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

    # PvP Arena (P3_S01_S01)
    PVP_QUEUE_REQ = 350       # 아레나 매칭 큐 등록
    PVP_QUEUE_CANCEL = 351    # 아레나 매칭 큐 취소
    PVP_QUEUE_STATUS = 352    # 아레나 매칭 상태
    PVP_MATCH_FOUND = 353     # 아레나 매칭 완료
    PVP_MATCH_ACCEPT = 354    # 아레나 매칭 수락
    PVP_MATCH_START = 355     # 아레나 경기 시작
    PVP_MATCH_END = 356       # 아레나 경기 종료 (결과)
    PVP_ATTACK = 357          # PvP 공격
    PVP_ATTACK_RESULT = 358   # PvP 공격 결과
    PVP_RATING_INFO = 359     # 레이팅 정보

    # Raid Boss Gimmick (P3_S02_S01)
    RAID_BOSS_SPAWN = 370     # 레이드 보스 스폰
    RAID_PHASE_CHANGE = 371   # 보스 페이즈 전환
    RAID_MECHANIC = 372       # 기믹 발동
    RAID_MECHANIC_RESULT = 373  # 기믹 결과 (성공/실패)
    RAID_STAGGER = 374        # 스태거 게이지 업데이트
    RAID_ENRAGE = 375         # 격노
    RAID_WIPE = 376           # 전멸
    RAID_CLEAR = 377          # 클리어
    RAID_ATTACK = 378         # 레이드 공격
    RAID_ATTACK_RESULT = 379
    # --- S041: Crafting/Gathering/Cooking/Enchant ---
    CRAFT_LIST_REQ = 380
    CRAFT_LIST = 381
    CRAFT_EXECUTE = 382
    CRAFT_RESULT = 383
    GATHER_START = 384
    GATHER_RESULT = 385
    COOK_EXECUTE = 386
    COOK_RESULT = 387
    ENCHANT_REQ = 388
    ENCHANT_RESULT = 389  # 레이드 공격 결과

    # Auction House / Economy (TASK 3)
    AUCTION_LIST_REQ = 390
    AUCTION_LIST = 391
    AUCTION_REGISTER = 392
    AUCTION_REGISTER_RESULT = 393
    AUCTION_BUY = 394
    AUCTION_BUY_RESULT = 395
    AUCTION_BID = 396
    AUCTION_BID_RESULT = 397

    # Tripod & Scroll System (TASK 15)
    TRIPOD_LIST_REQ = 520
    TRIPOD_LIST = 521
    TRIPOD_EQUIP = 522
    TRIPOD_EQUIP_RESULT = 523
    SCROLL_DISCOVER = 524

    # Bounty System (TASK 16)
    BOUNTY_LIST_REQ = 530
    BOUNTY_LIST = 531
    BOUNTY_ACCEPT = 532
    BOUNTY_ACCEPT_RESULT = 533
    BOUNTY_COMPLETE = 534
    BOUNTY_RANKING_REQ = 535
    BOUNTY_RANKING = 536
    PVP_BOUNTY_NOTIFY = 537

    # Quest Enhancement (TASK 4)
    DAILY_QUEST_LIST_REQ = 400
    DAILY_QUEST_LIST = 401
    WEEKLY_QUEST_REQ = 402
    WEEKLY_QUEST = 403
    REPUTATION_QUERY = 404
    REPUTATION_INFO = 405

    # Progression Deepening (TASK 7)
    TITLE_LIST_REQ = 440
    TITLE_LIST = 441
    TITLE_EQUIP = 442
    TITLE_EQUIP_RESULT = 443
    COLLECTION_QUERY = 444
    COLLECTION_INFO = 445
    JOB_CHANGE_REQ = 446
    JOB_CHANGE_RESULT = 447


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
    crafting_level: int = 1           # crafting proficiency
    crafting_exp: int = 0             # crafting exp
    gathering_level: int = 1          # gathering proficiency
    gathering_exp: int = 0            # gathering exp
    cooking_level: int = 1            # cooking proficiency
    energy: int = 200                 # gathering energy (max:200)
    energy_last_regen: float = 0.0    # last energy regen time
    food_buff: dict = field(default_factory=dict)  # current food buff
    weapon_enchant: dict = field(default_factory=dict)  # {slot: {element, level}}
    # Auction House & Economy (TASK 3)
    auction_listings: int = 0             # current listing count
    daily_gold_earned: dict = field(default_factory=lambda: {"monster": 0, "dungeon": 0, "quest": 0, "total": 0})  # daily gold tracking
    daily_gold_reset_date: str = ""       # last reset date (YYYY-MM-DD)
    # Tripod & Scroll System (TASK 15)
    tripod_unlocked: dict = field(default_factory=dict)  # {skill_id: {tier: [unlocked_option_ids]}}
    tripod_equipped: dict = field(default_factory=dict)  # {skill_id: {tier: option_id}}
    scroll_collection: set = field(default_factory=set)  # set of discovered scroll_ids
    # ---- Bounty System (TASK 16) ----
    bounty_accepted: list = field(default_factory=list)    # [{bounty_id, monster_id, type:"daily"/"weekly"}]
    bounty_completed_today: list = field(default_factory=list)  # completed bounty_ids today
    bounty_completed_weekly: list = field(default_factory=list)  # completed weekly bounty_ids
    bounty_tokens: int = 0
    bounty_reset_date: str = ""          # YYYY-MM-DD for daily reset
    bounty_weekly_reset_date: str = ""   # YYYY-MM-DD for weekly reset
    bounty_score_weekly: int = 0         # weekly ranking score
    pvp_kill_streak: int = 0             # current PvP kill streak
    pvp_bounty_tier: int = 0             # current PvP bounty tier (0=none)
    # ---- Quest Enhancement (TASK 4) ----
    daily_quests: list = field(default_factory=list)        # [{dq_id, type, target_id, count, progress, completed}]
    daily_quest_reset_date: str = ""                        # YYYY-MM-DD
    weekly_quest: dict = field(default_factory=dict)        # {wq_id, type, target_id, count, progress, completed}
    weekly_quest_reset_date: str = ""                       # YYYY-MM-DD (last wednesday)
    reputation: dict = field(default_factory=lambda: {"village_guard": 0, "merchant_guild": 0})  # faction -> points
    reputation_daily_gained: dict = field(default_factory=lambda: {"village_guard": 0, "merchant_guild": 0})
    reputation_daily_reset_date: str = ""                   # YYYY-MM-DD
    # ---- Progression Deepening (TASK 7) ----
    titles_unlocked: list = field(default_factory=list)   # [title_id, ...]
    title_equipped: int = 0                                # currently equipped title_id (0=none)
    collection_monsters: list = field(default_factory=list)  # [monster_name, ...] killed at least once
    collection_equip_tiers: list = field(default_factory=list)  # [tier, ...] obtained at least once
    second_job: str = ""                                   # "" = not yet, "berserker"/"guardian"/etc
    second_job_class: str = ""                             # original class when job changed
    milestones_claimed: list = field(default_factory=list)  # [level, ...] already claimed
    dungeon_clears: int = 0                                # total dungeon clears (for title condition)
    boss_kills: int = 0                                    # total boss kills (for title condition)


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
    # PvP 아레나
    200: {"min_x": 0, "max_x": 300, "min_z": 0, "max_z": 300},    # pvp_arena_1v1
    201: {"min_x": 0, "max_x": 500, "min_z": 0, "max_z": 500},    # pvp_arena_3v3
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

# ---- Crafting System Data (GDD crafting.yaml) ----
CRAFTING_RECIPES = {
    "iron_sword": {
        "id": "iron_sword", "name": "Iron Sword", "category": "weapon",
        "proficiency_required": 1,
        "materials": [{"item": "iron_ore", "count": 5}, {"item": "wood", "count": 2}],
        "gold_cost": 200, "craft_time": 5, "success_rate": 1.0,
        "result": {"item_id": 301, "count": 1},
        "bonus_option_chance": 0.0,
    },
    "steel_sword": {
        "id": "steel_sword", "name": "Steel Sword", "category": "weapon",
        "proficiency_required": 10,
        "materials": [{"item": "steel_ingot", "count": 3}, {"item": "leather", "count": 2}, {"item": "iron_sword", "count": 1}],
        "gold_cost": 1000, "craft_time": 10, "success_rate": 0.9,
        "result": {"item_id": 302, "count": 1},
        "bonus_option_chance": 0.2,
    },
    "hp_potion_s": {
        "id": "hp_potion_s", "name": "HP Potion (S)", "category": "potion",
        "proficiency_required": 1,
        "materials": [{"item": "herb", "count": 3}],
        "gold_cost": 20, "craft_time": 2, "success_rate": 1.0,
        "result": {"item_id": 201, "count": 3},
        "bonus_option_chance": 0.0,
    },
    "hp_potion_l": {
        "id": "hp_potion_l", "name": "HP Potion (L)", "category": "potion",
        "proficiency_required": 15,
        "materials": [{"item": "rare_herb", "count": 5}, {"item": "crystal_water", "count": 1}],
        "gold_cost": 200, "craft_time": 5, "success_rate": 0.8,
        "result": {"item_id": 202, "count": 3},
        "bonus_option_chance": 0.0,
    },
    "polished_ruby": {
        "id": "polished_ruby", "name": "Polished Ruby", "category": "gem",
        "proficiency_required": 10,
        "materials": [{"item": "rough_ruby", "count": 3}],
        "gold_cost": 100, "craft_time": 5, "success_rate": 1.0,
        "result": {"item_id": 501, "count": 1},
        "bonus_option_chance": 0.0,
    },
    "steel_ingot": {
        "id": "steel_ingot", "name": "Steel Ingot", "category": "material",
        "proficiency_required": 5,
        "materials": [{"item": "iron_ore", "count": 3}, {"item": "coal", "count": 1}],
        "gold_cost": 50, "craft_time": 3, "success_rate": 1.0,
        "result": {"item_id": 601, "count": 1},
        "bonus_option_chance": 0.0,
    },
}

GATHER_TYPES = {
    1: {"name": "herbalism", "gather_time": 3.0, "exp": 5, "loot": [
        {"item_id": 701, "name": "herb", "chance": 0.80},
        {"item_id": 702, "name": "rare_herb", "chance": 0.15},
        {"item_id": 703, "name": "legendary_herb", "chance": 0.05},
    ]},
    2: {"name": "mining", "gather_time": 5.0, "exp": 8, "loot": [
        {"item_id": 711, "name": "iron_ore", "chance": 0.70},
        {"item_id": 712, "name": "gold_ore", "chance": 0.20},
        {"item_id": 713, "name": "crystal", "chance": 0.08},
        {"item_id": 714, "name": "diamond_ore", "chance": 0.02},
    ]},
    3: {"name": "logging", "gather_time": 4.0, "exp": 6, "loot": [
        {"item_id": 721, "name": "wood", "chance": 0.80},
        {"item_id": 722, "name": "hardwood", "chance": 0.15},
        {"item_id": 723, "name": "world_tree_branch", "chance": 0.05},
    ]},
}
GATHER_ENERGY_MAX = 200
GATHER_ENERGY_COST = 5
GATHER_ENERGY_REGEN = 1  # per minute

COOKING_RECIPES = {
    "grilled_meat": {
        "id": "grilled_meat", "name": "Grilled Meat",
        "materials": [{"item": "raw_meat", "count": 3}],
        "effect": {"atk": 10}, "duration": 1800,
        "proficiency_required": 1,
        "result_item_id": 801,
    },
    "fish_stew": {
        "id": "fish_stew", "name": "Fish Stew",
        "materials": [{"item": "fish", "count": 2}, {"item": "herb", "count": 1}],
        "effect": {"max_hp": 200, "hp_regen": 5}, "duration": 1800,
        "proficiency_required": 5,
        "result_item_id": 802,
    },
    "royal_feast": {
        "id": "royal_feast", "name": "Royal Feast",
        "materials": [{"item": "rare_meat", "count": 2}, {"item": "rare_herb", "count": 2}, {"item": "spice", "count": 1}],
        "effect": {"all_stats": 5, "exp_bonus": 0.05}, "duration": 3600,
        "proficiency_required": 20,
        "result_item_id": 803,
    },
}

ENCHANT_ELEMENTS = ["fire", "ice", "lightning", "dark", "holy", "nature"]
ENCHANT_LEVELS = {
    1: {"damage_bonus": 0.05, "material_cost": 5, "gold_cost": 1000},
    2: {"damage_bonus": 0.10, "material_cost": 10, "gold_cost": 3000},
    3: {"damage_bonus": 0.15, "material_cost": 20, "gold_cost": 10000},
}

# ---- Auction House Constants (GDD economy.yaml) ----
AUCTION_TAX_RATE = 0.05       # 5% seller tax
AUCTION_LISTING_FEE = 100     # 100 gold listing fee (non-refundable)
AUCTION_MAX_LISTINGS = 20     # max concurrent listings per player
AUCTION_DURATION_HOURS = 48   # 48h auto-expire
AUCTION_MIN_PRICE = 1
AUCTION_MAX_PRICE = 99999999

# Daily gold caps (economy.yaml inflation_control)
DAILY_GOLD_CAPS = {
    "monster": 50000,
    "dungeon": 30000,
    "quest": 20000,
    "total": 100000,
}

# ---- Tripod & Scroll Data (GDD tripod.yaml) ----
# Tier unlock levels: tier1=Lv10, tier2=Lv20, tier3=Lv30
TRIPOD_TIER_UNLOCK = {1: 10, 2: 20, 3: 30}

# Full tripod table: skill_id -> {tier -> [options]}
# Each option: {id, name, effect_type, effect_value}
# effect_type: "range_up", "penetrate", "cast_speed", "bleed_dot", "knockback",
#              "multi_hit", "element_convert", "invincible", "damage_up", "aoe_up",
#              "duration_up", "cooldown_down", "slow_enhance", "crit_up", "heal_up"
TRIPOD_TABLE = {
    # ---- Warrior (skill 2-9) ----
    2: {  # slash
        1: [
            {"id": "slash_t1_1", "name": "wide_slash", "effect_type": "range_up", "effect_value": 0.30},
            {"id": "slash_t1_2", "name": "penetrate", "effect_type": "penetrate", "effect_value": 5},
            {"id": "slash_t1_3", "name": "quick_draw", "effect_type": "cast_speed", "effect_value": 0.40},
        ],
        2: [
            {"id": "slash_t2_1", "name": "bleed_slash", "effect_type": "bleed_dot", "effect_value": 0.20},
            {"id": "slash_t2_2", "name": "crush_blow", "effect_type": "knockback", "effect_value": 0.30},
            {"id": "slash_t2_3", "name": "chain_slash", "effect_type": "multi_hit", "effect_value": 2},
        ],
        3: [
            {"id": "slash_t3_1", "name": "flame_dance", "effect_type": "element_convert", "effect_value": "fire"},
            {"id": "slash_t3_2", "name": "invincible_slash", "effect_type": "invincible", "effect_value": 1},
        ],
    },
    3: {  # guard
        1: [
            {"id": "guard_t1_1", "name": "iron_wall", "effect_type": "damage_up", "effect_value": 0.20},
            {"id": "guard_t1_2", "name": "counter", "effect_type": "damage_up", "effect_value": 1.5},
            {"id": "guard_t1_3", "name": "quick_guard", "effect_type": "cast_speed", "effect_value": 0.30},
        ],
        2: [
            {"id": "guard_t2_1", "name": "thorns", "effect_type": "damage_up", "effect_value": 0.50},
            {"id": "guard_t2_2", "name": "shield_bash", "effect_type": "knockback", "effect_value": 0.50},
            {"id": "guard_t2_3", "name": "heal_guard", "effect_type": "heal_up", "effect_value": 0.10},
        ],
        3: [
            {"id": "guard_t3_1", "name": "absolute_defense", "effect_type": "invincible", "effect_value": 1},
            {"id": "guard_t3_2", "name": "guardian_aura", "effect_type": "aoe_up", "effect_value": 0.50},
        ],
    },
    4: {  # charge
        1: [
            {"id": "charge_t1_1", "name": "long_charge", "effect_type": "range_up", "effect_value": 0.50},
            {"id": "charge_t1_2", "name": "armor_charge", "effect_type": "damage_up", "effect_value": 0.20},
            {"id": "charge_t1_3", "name": "fast_charge", "effect_type": "cast_speed", "effect_value": 0.30},
        ],
        2: [
            {"id": "charge_t2_1", "name": "stun_extend", "effect_type": "duration_up", "effect_value": 1.0},
            {"id": "charge_t2_2", "name": "aoe_charge", "effect_type": "aoe_up", "effect_value": 0.50},
            {"id": "charge_t2_3", "name": "chain_charge", "effect_type": "multi_hit", "effect_value": 2},
        ],
        3: [
            {"id": "charge_t3_1", "name": "thunder_charge", "effect_type": "element_convert", "effect_value": "lightning"},
            {"id": "charge_t3_2", "name": "unstoppable", "effect_type": "invincible", "effect_value": 1},
        ],
    },
    5: {  # war_cry
        1: [
            {"id": "warcry_t1_1", "name": "wide_cry", "effect_type": "aoe_up", "effect_value": 0.30},
            {"id": "warcry_t1_2", "name": "long_cry", "effect_type": "duration_up", "effect_value": 5.0},
            {"id": "warcry_t1_3", "name": "def_cry", "effect_type": "damage_up", "effect_value": 0.15},
        ],
        2: [
            {"id": "warcry_t2_1", "name": "battle_shout", "effect_type": "crit_up", "effect_value": 0.10},
            {"id": "warcry_t2_2", "name": "heal_shout", "effect_type": "heal_up", "effect_value": 0.05},
            {"id": "warcry_t2_3", "name": "speed_shout", "effect_type": "cast_speed", "effect_value": 0.20},
        ],
        3: [
            {"id": "warcry_t3_1", "name": "berserker_rage", "effect_type": "damage_up", "effect_value": 0.50},
            {"id": "warcry_t3_2", "name": "guardian_oath", "effect_type": "heal_up", "effect_value": 0.15},
        ],
    },
    6: {  # wind_slash
        1: [
            {"id": "windslash_t1_1", "name": "gale_force", "effect_type": "damage_up", "effect_value": 0.20},
            {"id": "windslash_t1_2", "name": "wide_wind", "effect_type": "aoe_up", "effect_value": 0.30},
            {"id": "windslash_t1_3", "name": "wind_pierce", "effect_type": "penetrate", "effect_value": 3},
        ],
        2: [
            {"id": "windslash_t2_1", "name": "tornado", "effect_type": "aoe_up", "effect_value": 0.80},
            {"id": "windslash_t2_2", "name": "crit_wind", "effect_type": "crit_up", "effect_value": 0.15},
            {"id": "windslash_t2_3", "name": "double_wind", "effect_type": "multi_hit", "effect_value": 2},
        ],
        3: [
            {"id": "windslash_t3_1", "name": "storm_blade", "effect_type": "element_convert", "effect_value": "wind"},
            {"id": "windslash_t3_2", "name": "vacuum_slash", "effect_type": "knockback", "effect_value": 1.0},
        ],
    },
    7: {  # stun_blow
        1: [
            {"id": "stunblow_t1_1", "name": "heavy_blow", "effect_type": "damage_up", "effect_value": 0.30},
            {"id": "stunblow_t1_2", "name": "quick_blow", "effect_type": "cooldown_down", "effect_value": 3.0},
            {"id": "stunblow_t1_3", "name": "wide_blow", "effect_type": "aoe_up", "effect_value": 0.30},
        ],
        2: [
            {"id": "stunblow_t2_1", "name": "stun_extend", "effect_type": "duration_up", "effect_value": 1.0},
            {"id": "stunblow_t2_2", "name": "armor_break", "effect_type": "damage_up", "effect_value": 0.50},
            {"id": "stunblow_t2_3", "name": "ground_slam", "effect_type": "knockback", "effect_value": 0.80},
        ],
        3: [
            {"id": "stunblow_t3_1", "name": "earthquake", "effect_type": "element_convert", "effect_value": "earth"},
            {"id": "stunblow_t3_2", "name": "execute", "effect_type": "damage_up", "effect_value": 1.0},
        ],
    },
    8: {  # blade_dance
        1: [
            {"id": "bladedance_t1_1", "name": "spin_extend", "effect_type": "multi_hit", "effect_value": 7},
            {"id": "bladedance_t1_2", "name": "move_dance", "effect_type": "cast_speed", "effect_value": 0.30},
            {"id": "bladedance_t1_3", "name": "crit_dance", "effect_type": "crit_up", "effect_value": 0.15},
        ],
        2: [
            {"id": "bladedance_t2_1", "name": "blood_dance", "effect_type": "bleed_dot", "effect_value": 0.15},
            {"id": "bladedance_t2_2", "name": "wide_dance", "effect_type": "aoe_up", "effect_value": 0.50},
            {"id": "bladedance_t2_3", "name": "fury_dance", "effect_type": "damage_up", "effect_value": 0.40},
        ],
        3: [
            {"id": "bladedance_t3_1", "name": "inferno_dance", "effect_type": "element_convert", "effect_value": "fire"},
            {"id": "bladedance_t3_2", "name": "phantom_dance", "effect_type": "invincible", "effect_value": 1},
        ],
    },
    9: {  # earth_shaker
        1: [
            {"id": "earthshaker_t1_1", "name": "wide_quake", "effect_type": "aoe_up", "effect_value": 0.40},
            {"id": "earthshaker_t1_2", "name": "fast_slam", "effect_type": "cast_speed", "effect_value": 0.30},
            {"id": "earthshaker_t1_3", "name": "heavy_slam", "effect_type": "damage_up", "effect_value": 0.25},
        ],
        2: [
            {"id": "earthshaker_t2_1", "name": "aftershock", "effect_type": "bleed_dot", "effect_value": 0.25},
            {"id": "earthshaker_t2_2", "name": "fissure", "effect_type": "penetrate", "effect_value": 8},
            {"id": "earthshaker_t2_3", "name": "stun_quake", "effect_type": "duration_up", "effect_value": 1.5},
        ],
        3: [
            {"id": "earthshaker_t3_1", "name": "volcanic_eruption", "effect_type": "element_convert", "effect_value": "fire"},
            {"id": "earthshaker_t3_2", "name": "world_breaker", "effect_type": "damage_up", "effect_value": 1.0},
        ],
    },
    # ---- Archer (skill 21-28) ----
    21: {  # arrow_rain
        1: [
            {"id": "arrowrain_t1_1", "name": "dense_rain", "effect_type": "damage_up", "effect_value": 0.20},
            {"id": "arrowrain_t1_2", "name": "wide_rain", "effect_type": "aoe_up", "effect_value": 0.40},
            {"id": "arrowrain_t1_3", "name": "quick_rain", "effect_type": "cast_speed", "effect_value": 0.30},
        ],
        2: [
            {"id": "arrowrain_t2_1", "name": "poison_rain", "effect_type": "bleed_dot", "effect_value": 0.15},
            {"id": "arrowrain_t2_2", "name": "slow_rain", "effect_type": "slow_enhance", "effect_value": 0.30},
            {"id": "arrowrain_t2_3", "name": "barrage", "effect_type": "multi_hit", "effect_value": 3},
        ],
        3: [
            {"id": "arrowrain_t3_1", "name": "meteor_shower", "effect_type": "element_convert", "effect_value": "fire"},
            {"id": "arrowrain_t3_2", "name": "frozen_rain", "effect_type": "element_convert", "effect_value": "ice"},
        ],
    },
    22: {  # quick_shot
        1: [
            {"id": "quickshot_t1_1", "name": "triple_shot", "effect_type": "multi_hit", "effect_value": 3},
            {"id": "quickshot_t1_2", "name": "precise_shot", "effect_type": "crit_up", "effect_value": 0.20},
            {"id": "quickshot_t1_3", "name": "long_shot", "effect_type": "range_up", "effect_value": 0.30},
        ],
        2: [
            {"id": "quickshot_t2_1", "name": "explosive_shot", "effect_type": "aoe_up", "effect_value": 0.50},
            {"id": "quickshot_t2_2", "name": "poison_shot", "effect_type": "bleed_dot", "effect_value": 0.20},
            {"id": "quickshot_t2_3", "name": "ricochet", "effect_type": "penetrate", "effect_value": 3},
        ],
        3: [
            {"id": "quickshot_t3_1", "name": "lightning_shot", "effect_type": "element_convert", "effect_value": "lightning"},
            {"id": "quickshot_t3_2", "name": "phantom_shot", "effect_type": "damage_up", "effect_value": 0.80},
        ],
    },
    23: {  # evasion_shot
        1: [
            {"id": "evasionshot_t1_1", "name": "long_evade", "effect_type": "range_up", "effect_value": 0.50},
            {"id": "evasionshot_t1_2", "name": "counter_shot", "effect_type": "damage_up", "effect_value": 0.40},
            {"id": "evasionshot_t1_3", "name": "fast_evade", "effect_type": "cooldown_down", "effect_value": 2.0},
        ],
        2: [
            {"id": "evasionshot_t2_1", "name": "smoke_bomb", "effect_type": "slow_enhance", "effect_value": 0.50},
            {"id": "evasionshot_t2_2", "name": "double_evade", "effect_type": "multi_hit", "effect_value": 2},
            {"id": "evasionshot_t2_3", "name": "stealth_evade", "effect_type": "invincible", "effect_value": 1},
        ],
        3: [
            {"id": "evasionshot_t3_1", "name": "wind_step", "effect_type": "element_convert", "effect_value": "wind"},
            {"id": "evasionshot_t3_2", "name": "shadow_step", "effect_type": "cooldown_down", "effect_value": 5.0},
        ],
    },
    24: {  # trap
        1: [
            {"id": "trap_t1_1", "name": "big_trap", "effect_type": "aoe_up", "effect_value": 0.50},
            {"id": "trap_t1_2", "name": "quick_trap", "effect_type": "cast_speed", "effect_value": 0.40},
            {"id": "trap_t1_3", "name": "damage_trap", "effect_type": "damage_up", "effect_value": 0.30},
        ],
        2: [
            {"id": "trap_t2_1", "name": "poison_trap", "effect_type": "bleed_dot", "effect_value": 0.25},
            {"id": "trap_t2_2", "name": "stun_trap", "effect_type": "duration_up", "effect_value": 2.0},
            {"id": "trap_t2_3", "name": "multi_trap", "effect_type": "multi_hit", "effect_value": 3},
        ],
        3: [
            {"id": "trap_t3_1", "name": "ice_trap", "effect_type": "element_convert", "effect_value": "ice"},
            {"id": "trap_t3_2", "name": "explosive_trap", "effect_type": "damage_up", "effect_value": 1.0},
        ],
    },
    25: {  # snipe
        1: [
            {"id": "snipe_t1_1", "name": "quick_aim", "effect_type": "cast_speed", "effect_value": 0.50},
            {"id": "snipe_t1_2", "name": "heavy_snipe", "effect_type": "damage_up", "effect_value": 0.30},
            {"id": "snipe_t1_3", "name": "long_snipe", "effect_type": "range_up", "effect_value": 0.50},
        ],
        2: [
            {"id": "snipe_t2_1", "name": "armor_pierce", "effect_type": "penetrate", "effect_value": 10},
            {"id": "snipe_t2_2", "name": "headshot", "effect_type": "crit_up", "effect_value": 0.30},
            {"id": "snipe_t2_3", "name": "double_snipe", "effect_type": "multi_hit", "effect_value": 2},
        ],
        3: [
            {"id": "snipe_t3_1", "name": "death_shot", "effect_type": "damage_up", "effect_value": 1.5},
            {"id": "snipe_t3_2", "name": "lightning_snipe", "effect_type": "element_convert", "effect_value": "lightning"},
        ],
    },
    26: {  # multi_shot
        1: [
            {"id": "multishot_t1_1", "name": "extra_arrows", "effect_type": "multi_hit", "effect_value": 7},
            {"id": "multishot_t1_2", "name": "wide_spread", "effect_type": "aoe_up", "effect_value": 0.40},
            {"id": "multishot_t1_3", "name": "fast_volley", "effect_type": "cast_speed", "effect_value": 0.30},
        ],
        2: [
            {"id": "multishot_t2_1", "name": "fire_arrows", "effect_type": "element_convert", "effect_value": "fire"},
            {"id": "multishot_t2_2", "name": "crit_volley", "effect_type": "crit_up", "effect_value": 0.15},
            {"id": "multishot_t2_3", "name": "pierce_volley", "effect_type": "penetrate", "effect_value": 5},
        ],
        3: [
            {"id": "multishot_t3_1", "name": "arrow_storm", "effect_type": "damage_up", "effect_value": 0.80},
            {"id": "multishot_t3_2", "name": "ice_volley", "effect_type": "element_convert", "effect_value": "ice"},
        ],
    },
    27: {  # piercing_arrow
        1: [
            {"id": "piercing_t1_1", "name": "long_pierce", "effect_type": "range_up", "effect_value": 0.50},
            {"id": "piercing_t1_2", "name": "heavy_pierce", "effect_type": "damage_up", "effect_value": 0.25},
            {"id": "piercing_t1_3", "name": "multi_pierce", "effect_type": "penetrate", "effect_value": 8},
        ],
        2: [
            {"id": "piercing_t2_1", "name": "bleed_arrow", "effect_type": "bleed_dot", "effect_value": 0.20},
            {"id": "piercing_t2_2", "name": "crit_pierce", "effect_type": "crit_up", "effect_value": 0.20},
            {"id": "piercing_t2_3", "name": "chain_pierce", "effect_type": "multi_hit", "effect_value": 2},
        ],
        3: [
            {"id": "piercing_t3_1", "name": "thunder_arrow", "effect_type": "element_convert", "effect_value": "lightning"},
            {"id": "piercing_t3_2", "name": "void_arrow", "effect_type": "damage_up", "effect_value": 1.2},
        ],
    },
    28: {  # arrow_storm
        1: [
            {"id": "arrowstorm_t1_1", "name": "wide_storm", "effect_type": "aoe_up", "effect_value": 0.40},
            {"id": "arrowstorm_t1_2", "name": "heavy_storm", "effect_type": "damage_up", "effect_value": 0.25},
            {"id": "arrowstorm_t1_3", "name": "fast_storm", "effect_type": "cast_speed", "effect_value": 0.30},
        ],
        2: [
            {"id": "arrowstorm_t2_1", "name": "poison_storm", "effect_type": "bleed_dot", "effect_value": 0.20},
            {"id": "arrowstorm_t2_2", "name": "slow_storm", "effect_type": "slow_enhance", "effect_value": 0.40},
            {"id": "arrowstorm_t2_3", "name": "crit_storm", "effect_type": "crit_up", "effect_value": 0.15},
        ],
        3: [
            {"id": "arrowstorm_t3_1", "name": "meteor_rain", "effect_type": "element_convert", "effect_value": "fire"},
            {"id": "arrowstorm_t3_2", "name": "blizzard_arrows", "effect_type": "element_convert", "effect_value": "ice"},
        ],
    },
    # ---- Mage (skill 41-48) ----
    41: {  # fireball
        1: [
            {"id": "fireball_t1_1", "name": "big_fireball", "effect_type": "aoe_up", "effect_value": 0.40},
            {"id": "fireball_t1_2", "name": "fast_fireball", "effect_type": "cast_speed", "effect_value": 0.40},
            {"id": "fireball_t1_3", "name": "heavy_fireball", "effect_type": "damage_up", "effect_value": 0.25},
        ],
        2: [
            {"id": "fireball_t2_1", "name": "triple_fireball", "effect_type": "multi_hit", "effect_value": 3},
            {"id": "fireball_t2_2", "name": "burn_fireball", "effect_type": "bleed_dot", "effect_value": 0.25},
            {"id": "fireball_t2_3", "name": "piercing_fire", "effect_type": "penetrate", "effect_value": 5},
        ],
        3: [
            {"id": "fireball_t3_1", "name": "inferno", "effect_type": "damage_up", "effect_value": 1.0},
            {"id": "fireball_t3_2", "name": "ice_convert", "effect_type": "element_convert", "effect_value": "ice"},
        ],
    },
    42: {  # ice_bolt
        1: [
            {"id": "icebolt_t1_1", "name": "multi_bolt", "effect_type": "multi_hit", "effect_value": 3},
            {"id": "icebolt_t1_2", "name": "heavy_bolt", "effect_type": "damage_up", "effect_value": 0.30},
            {"id": "icebolt_t1_3", "name": "long_bolt", "effect_type": "range_up", "effect_value": 0.30},
        ],
        2: [
            {"id": "icebolt_t2_1", "name": "freeze_bolt", "effect_type": "duration_up", "effect_value": 2.0},
            {"id": "icebolt_t2_2", "name": "shatter", "effect_type": "damage_up", "effect_value": 0.50},
            {"id": "icebolt_t2_3", "name": "ice_spread", "effect_type": "aoe_up", "effect_value": 0.50},
        ],
        3: [
            {"id": "icebolt_t3_1", "name": "absolute_zero", "effect_type": "damage_up", "effect_value": 1.0},
            {"id": "icebolt_t3_2", "name": "fire_convert", "effect_type": "element_convert", "effect_value": "fire"},
        ],
    },
    43: {  # mana_shield
        1: [
            {"id": "manashield_t1_1", "name": "strong_shield", "effect_type": "damage_up", "effect_value": 0.30},
            {"id": "manashield_t1_2", "name": "efficient_shield", "effect_type": "cooldown_down", "effect_value": 3.0},
            {"id": "manashield_t1_3", "name": "quick_shield", "effect_type": "cast_speed", "effect_value": 0.30},
        ],
        2: [
            {"id": "manashield_t2_1", "name": "reflect_shield", "effect_type": "damage_up", "effect_value": 0.50},
            {"id": "manashield_t2_2", "name": "aoe_shield", "effect_type": "aoe_up", "effect_value": 0.50},
            {"id": "manashield_t2_3", "name": "regen_shield", "effect_type": "heal_up", "effect_value": 0.05},
        ],
        3: [
            {"id": "manashield_t3_1", "name": "divine_barrier", "effect_type": "invincible", "effect_value": 1},
            {"id": "manashield_t3_2", "name": "mana_explosion", "effect_type": "damage_up", "effect_value": 1.0},
        ],
    },
    44: {  # lightning
        1: [
            {"id": "lightning_t1_1", "name": "chain_lightning", "effect_type": "penetrate", "effect_value": 5},
            {"id": "lightning_t1_2", "name": "heavy_bolt", "effect_type": "damage_up", "effect_value": 0.25},
            {"id": "lightning_t1_3", "name": "wide_bolt", "effect_type": "aoe_up", "effect_value": 0.40},
        ],
        2: [
            {"id": "lightning_t2_1", "name": "stun_extend", "effect_type": "duration_up", "effect_value": 1.0},
            {"id": "lightning_t2_2", "name": "overcharge", "effect_type": "damage_up", "effect_value": 0.50},
            {"id": "lightning_t2_3", "name": "ball_lightning", "effect_type": "multi_hit", "effect_value": 3},
        ],
        3: [
            {"id": "lightning_t3_1", "name": "thunder_god", "effect_type": "damage_up", "effect_value": 1.0},
            {"id": "lightning_t3_2", "name": "ice_convert", "effect_type": "element_convert", "effect_value": "ice"},
        ],
    },
    45: {  # blizzard
        1: [
            {"id": "blizzard_t1_1", "name": "wide_blizzard", "effect_type": "aoe_up", "effect_value": 0.40},
            {"id": "blizzard_t1_2", "name": "deep_freeze", "effect_type": "duration_up", "effect_value": 1.0},
            {"id": "blizzard_t1_3", "name": "fast_blizzard", "effect_type": "cast_speed", "effect_value": 0.30},
        ],
        2: [
            {"id": "blizzard_t2_1", "name": "shatter_blizzard", "effect_type": "damage_up", "effect_value": 0.40},
            {"id": "blizzard_t2_2", "name": "slow_field", "effect_type": "slow_enhance", "effect_value": 0.50},
            {"id": "blizzard_t2_3", "name": "ice_spikes", "effect_type": "multi_hit", "effect_value": 3},
        ],
        3: [
            {"id": "blizzard_t3_1", "name": "ice_age", "effect_type": "damage_up", "effect_value": 1.0},
            {"id": "blizzard_t3_2", "name": "fire_convert", "effect_type": "element_convert", "effect_value": "fire"},
        ],
    },
    46: {  # teleport
        1: [
            {"id": "teleport_t1_1", "name": "long_teleport", "effect_type": "range_up", "effect_value": 0.50},
            {"id": "teleport_t1_2", "name": "fast_teleport", "effect_type": "cooldown_down", "effect_value": 3.0},
            {"id": "teleport_t1_3", "name": "safe_teleport", "effect_type": "invincible", "effect_value": 1},
        ],
        2: [
            {"id": "teleport_t2_1", "name": "blink_strike", "effect_type": "damage_up", "effect_value": 1.5},
            {"id": "teleport_t2_2", "name": "double_blink", "effect_type": "multi_hit", "effect_value": 2},
            {"id": "teleport_t2_3", "name": "decoy", "effect_type": "slow_enhance", "effect_value": 0.30},
        ],
        3: [
            {"id": "teleport_t3_1", "name": "dimension_rift", "effect_type": "aoe_up", "effect_value": 1.0},
            {"id": "teleport_t3_2", "name": "time_warp", "effect_type": "cooldown_down", "effect_value": 8.0},
        ],
    },
    47: {  # meteor
        1: [
            {"id": "meteor_t1_1", "name": "fast_meteor", "effect_type": "cast_speed", "effect_value": 0.40},
            {"id": "meteor_t1_2", "name": "wide_meteor", "effect_type": "aoe_up", "effect_value": 0.30},
            {"id": "meteor_t1_3", "name": "heavy_meteor", "effect_type": "damage_up", "effect_value": 0.25},
        ],
        2: [
            {"id": "meteor_t2_1", "name": "meteor_shower", "effect_type": "multi_hit", "effect_value": 3},
            {"id": "meteor_t2_2", "name": "burn_field", "effect_type": "bleed_dot", "effect_value": 0.30},
            {"id": "meteor_t2_3", "name": "stun_impact", "effect_type": "duration_up", "effect_value": 1.5},
        ],
        3: [
            {"id": "meteor_t3_1", "name": "apocalypse", "effect_type": "damage_up", "effect_value": 1.5},
            {"id": "meteor_t3_2", "name": "ice_comet", "effect_type": "element_convert", "effect_value": "ice"},
        ],
    },
    48: {  # holy_light
        1: [
            {"id": "holylight_t1_1", "name": "wide_heal", "effect_type": "aoe_up", "effect_value": 0.40},
            {"id": "holylight_t1_2", "name": "strong_heal", "effect_type": "heal_up", "effect_value": 0.30},
            {"id": "holylight_t1_3", "name": "fast_heal", "effect_type": "cast_speed", "effect_value": 0.40},
        ],
        2: [
            {"id": "holylight_t2_1", "name": "regen", "effect_type": "duration_up", "effect_value": 5.0},
            {"id": "holylight_t2_2", "name": "cleanse", "effect_type": "heal_up", "effect_value": 0.50},
            {"id": "holylight_t2_3", "name": "shield_heal", "effect_type": "damage_up", "effect_value": 0.30},
        ],
        3: [
            {"id": "holylight_t3_1", "name": "divine_blessing", "effect_type": "heal_up", "effect_value": 1.0},
            {"id": "holylight_t3_2", "name": "holy_nova", "effect_type": "damage_up", "effect_value": 0.80},
        ],
    },
}

# Scroll drop rates by monster type (GDD tripod.yaml acquisition)
SCROLL_DROP_RATES = {
    "normal": 0.0,
    "elite": 0.05,       # 5%
    "dungeon_boss": 0.15, # 15%
    "raid_boss": 0.30,    # 30%
}

# Skill -> class mapping (for class-restricted scroll drops)
SKILL_CLASS_MAP = {
    2: "warrior", 3: "warrior", 4: "warrior", 5: "warrior",
    6: "warrior", 7: "warrior", 8: "warrior", 9: "warrior",
    21: "archer", 22: "archer", 23: "archer", 24: "archer",
    25: "archer", 26: "archer", 27: "archer", 28: "archer",
    41: "mage", 42: "mage", 43: "mage", 44: "mage",
    45: "mage", 46: "mage", 47: "mage", 48: "mage",
}

# Class -> skill list
CLASS_SKILLS = {
    "warrior": [2, 3, 4, 5, 6, 7, 8, 9],
    "archer": [21, 22, 23, 24, 25, 26, 27, 28],
    "mage": [41, 42, 43, 44, 45, 46, 47, 48],
}

# ---- Bounty System Data (GDD bounty.yaml) ----
# Daily bounties: 3 daily (06:00 reset), 1 weekly (Wed 06:00 reset)
BOUNTY_MAX_ACCEPTED = 3          # simultaneous accepted bounties
BOUNTY_MIN_LEVEL = 15            # level requirement for bounties
BOUNTY_WEEKLY_MIN_LEVEL = 30     # level requirement for weekly grand bounty

# Elite monsters for daily bounties (from monsters.csv)
BOUNTY_ELITE_POOL = [
    {"monster_id": 2001, "name": "elite_golem", "name_kr": "정예 골렘", "level": 20, "zone": "dark_forest",
     "gold": 1000, "exp": 2000, "bounty_token": 2},
    {"monster_id": 2002, "name": "ice_queen_elite", "name_kr": "얼음 여왕 정예", "level": 18, "zone": "frozen_peak",
     "gold": 800, "exp": 1500, "bounty_token": 2},
    {"monster_id": 2003, "name": "elite_dragon_whelp", "name_kr": "정예 와이번", "level": 25, "zone": "volcano",
     "gold": 1500, "exp": 3000, "bounty_token": 3},
]

# Weather-special bounty: bonus rewards when weather matches
BOUNTY_WEATHER_BONUS = {
    "storm": {"gold_mult": 1.5, "exp_mult": 1.5, "extra_token": 1},
    "fog": {"gold_mult": 1.3, "exp_mult": 1.3, "extra_token": 1},
    "night": {"gold_mult": 1.2, "exp_mult": 1.2, "extra_token": 0},
}

# Weekly world bosses (grand bounty)
BOUNTY_WORLD_BOSSES = [
    {"boss_id": 5001, "name": "crimson_drake", "name_kr": "홍염 비룡", "level": 40, "zone": "zone4",
     "gold": 5000, "exp": 10000, "bounty_token": 10, "min_party": 4, "recommended_party": 8},
    {"boss_id": 5002, "name": "ice_titan", "name_kr": "빙결의 거인", "level": 35, "zone": "zone3",
     "gold": 4000, "exp": 8000, "bounty_token": 8, "min_party": 4, "recommended_party": 8},
    {"boss_id": 5003, "name": "shadow_hydra", "name_kr": "그림자 히드라", "level": 50, "zone": "zone6",
     "gold": 8000, "exp": 15000, "bounty_token": 15, "min_party": 4, "recommended_party": 8},
]

# PvP bounty tiers
PVP_BOUNTY_TIERS = {
    3:  {"tier": 1, "name": "dangerous", "name_kr": "위험인물",    "gold_reward": 500,  "pvp_token": 2},
    5:  {"tier": 2, "name": "wanted",    "name_kr": "현상수배",    "gold_reward": 1500, "pvp_token": 5},
    10: {"tier": 3, "name": "villain",   "name_kr": "대악인",      "gold_reward": 3000, "pvp_token": 10},
    20: {"tier": 4, "name": "demon_king","name_kr": "마왕급 위협", "gold_reward": 5000, "pvp_token": 20},
}

# Daily completion bonus (all 3 daily bounties done)
BOUNTY_DAILY_COMPLETION_BONUS = {"gold": 500, "bounty_token": 3}

# Bounty token shop items
BOUNTY_TOKEN_SHOP = [
    {"item_id": 8001, "name": "bounty_potion",     "name_kr": "현상금 비약",   "cost": 5,   "category": "consumable"},
    {"item_id": 8002, "name": "bounty_weapon_box",  "name_kr": "현상금 무기 상자", "cost": 50,  "category": "equipment"},
    {"item_id": 8003, "name": "bounty_armor_box",   "name_kr": "현상금 방어구 상자","cost": 50,  "category": "equipment"},
    {"item_id": 8004, "name": "bounty_mount",       "name_kr": "현상금 사냥꾼의 말","cost": 200, "category": "mount"},
    {"item_id": 8005, "name": "legend_hunter_title", "name_kr": "전설의 사냥꾼 칭호","cost": 500, "category": "title"},
]

# ---- Quest Enhancement Data (GDD quests.yaml / reputation) ----
# Daily quests: 3 random from pool, reset 06:00 daily
DAILY_QUEST_POOL = [
    {"dq_id": 1, "type": "kill", "name_kr": "슬라임 퇴치",     "target_id": 101, "count": 10,
     "reward_exp": 500,  "reward_gold": 200, "reward_rep_faction": "village_guard", "reward_rep": 50},
    {"dq_id": 2, "type": "kill", "name_kr": "고블린 소탕",     "target_id": 103, "count": 8,
     "reward_exp": 600,  "reward_gold": 250, "reward_rep_faction": "village_guard", "reward_rep": 50},
    {"dq_id": 3, "type": "kill", "name_kr": "늑대 처치",       "target_id": 102, "count": 6,
     "reward_exp": 550,  "reward_gold": 220, "reward_rep_faction": "village_guard", "reward_rep": 50},
    {"dq_id": 4, "type": "collect", "name_kr": "약초 수집",    "target_id": 7001, "count": 5,
     "reward_exp": 400,  "reward_gold": 300, "reward_rep_faction": "merchant_guild", "reward_rep": 50},
    {"dq_id": 5, "type": "collect", "name_kr": "광석 채집",    "target_id": 7002, "count": 5,
     "reward_exp": 400,  "reward_gold": 300, "reward_rep_faction": "merchant_guild", "reward_rep": 50},
    {"dq_id": 6, "type": "craft", "name_kr": "포션 제작",      "target_id": 6001, "count": 3,
     "reward_exp": 450,  "reward_gold": 350, "reward_rep_faction": "merchant_guild", "reward_rep": 50},
    {"dq_id": 7, "type": "kill", "name_kr": "언데드 퇴치",     "target_id": 104, "count": 8,
     "reward_exp": 650,  "reward_gold": 280, "reward_rep_faction": "village_guard", "reward_rep": 50},
    {"dq_id": 8, "type": "kill", "name_kr": "정예 사냥",       "target_id": 2001, "count": 1,
     "reward_exp": 800,  "reward_gold": 500, "reward_rep_faction": "village_guard", "reward_rep": 100},
]
DAILY_QUEST_MAX_ACTIVE = 3   # max daily quests active at once
DAILY_QUEST_MIN_LEVEL = 5    # level requirement

# Weekly quest: 1 large quest, reset Wednesday 06:00
WEEKLY_QUEST_POOL = [
    {"wq_id": 1, "type": "dungeon_clear", "name_kr": "고블린 동굴 정복",
     "target_id": 1, "count": 3, "difficulty": "normal",
     "reward_exp": 5000, "reward_gold": 2000, "reward_rep_faction": "village_guard", "reward_rep": 200,
     "reward_dungeon_token": 5},
    {"wq_id": 2, "type": "kill", "name_kr": "월드 보스 처치",
     "target_id": 5001, "count": 1, "difficulty": "any",
     "reward_exp": 8000, "reward_gold": 3000, "reward_rep_faction": "village_guard", "reward_rep": 300,
     "reward_dungeon_token": 8},
    {"wq_id": 3, "type": "pvp_win", "name_kr": "아레나 승리",
     "target_id": 0, "count": 5, "difficulty": "any",
     "reward_exp": 4000, "reward_gold": 1500, "reward_rep_faction": "merchant_guild", "reward_rep": 200,
     "reward_dungeon_token": 3},
]
WEEKLY_QUEST_MIN_LEVEL = 15

# Reputation factions and tiers (GDD quests.yaml)
REPUTATION_FACTIONS = {
    "village_guard": {
        "name_kr": "마을 수비대",
        "tiers": [
            {"name": "neutral",  "name_kr": "중립",     "min": 0},
            {"name": "friendly", "name_kr": "우호",     "min": 500},
            {"name": "honored",  "name_kr": "존경",     "min": 2000},
            {"name": "revered",  "name_kr": "숭배",     "min": 5000},
            {"name": "exalted",  "name_kr": "숭앙",     "min": 10000},
        ],
    },
    "merchant_guild": {
        "name_kr": "상인 조합",
        "tiers": [
            {"name": "neutral",  "name_kr": "중립",     "min": 0},
            {"name": "friendly", "name_kr": "우호",     "min": 500},
            {"name": "honored",  "name_kr": "존경",     "min": 2000},
            {"name": "revered",  "name_kr": "숭배",     "min": 5000},
            {"name": "exalted",  "name_kr": "숭앙",     "min": 10000},
        ],
    },
}
REPUTATION_DAILY_CAP = 500   # daily reputation gain cap (excluding quest rewards)
REPUTATION_MONSTER_KILL = 1  # per kill in faction territory

# ---- Progression Deepening Data (GDD progression.yaml sections 5-6 + classes) ----
# Title definitions: 9 titles with conditions and stat bonuses
TITLE_LIST_DATA = [
    {"title_id": 1, "name_kr": "초보 모험가", "condition_type": "level",      "condition_value": 5,
     "bonus_type": "max_hp",      "bonus_value": 50},
    {"title_id": 2, "name_kr": "숙련 모험가", "condition_type": "level",      "condition_value": 30,
     "bonus_type": "atk_def",     "bonus_value": 10},
    {"title_id": 3, "name_kr": "전설의 용사", "condition_type": "level",      "condition_value": 60,
     "bonus_type": "all_stats",   "bonus_value": 5},
    {"title_id": 4, "name_kr": "첫 번째 던전", "condition_type": "dungeon_clear", "condition_value": 1,
     "bonus_type": "exp_bonus",   "bonus_value": 5},     # 5% exp bonus
    {"title_id": 5, "name_kr": "보스 슬레이어", "condition_type": "boss_kill",  "condition_value": 10,
     "bonus_type": "crit_rate",   "bonus_value": 2},     # 2% crit
    {"title_id": 6, "name_kr": "만물박사",     "condition_type": "all_quests",  "condition_value": 1,
     "bonus_type": "all_stats",   "bonus_value": 3},
    {"title_id": 7, "name_kr": "PvP 챔피언",  "condition_type": "pvp_rank",   "condition_value": 1,
     "bonus_type": "pvp_damage",  "bonus_value": 5},     # 5% pvp damage
    {"title_id": 8, "name_kr": "길드 마스터",  "condition_type": "guild_level", "condition_value": 10,
     "bonus_type": "leadership",  "bonus_value": 10},
    {"title_id": 9, "name_kr": "부자",         "condition_type": "gold_held",  "condition_value": 1000000,
     "bonus_type": "gold_bonus",  "bonus_value": 10},    # 10% gold bonus
]

# Monster encyclopedia categories for collection
COLLECTION_MONSTER_CATEGORIES = [
    {"cat_id": 1, "name_kr": "튜토리얼 몬스터",
     "monsters": ["slime", "goblin"],
     "bonus_type": "atk", "bonus_value": 5},
    {"cat_id": 2, "name_kr": "필드 몬스터",
     "monsters": ["wolf", "orc", "bear", "skeleton", "bandit"],
     "bonus_type": "def", "bonus_value": 10},
    {"cat_id": 3, "name_kr": "엘리트 몬스터",
     "monsters": ["elite_golem", "elite_dragon_whelp"],
     "bonus_type": "max_hp", "bonus_value": 200},
    {"cat_id": 4, "name_kr": "보스",
     "monsters": ["ancient_golem", "dragon", "demon_king"],
     "bonus_type": "all_stats", "bonus_value": 3},
]

# Equipment codex tiers
COLLECTION_EQUIP_TIERS = [
    {"tier": "common",    "tier_kr": "일반",    "bonus_type": "max_hp",    "bonus_value": 10},
    {"tier": "uncommon",  "tier_kr": "고급",    "bonus_type": "atk",       "bonus_value": 3},
    {"tier": "rare",      "tier_kr": "희귀",    "bonus_type": "def",       "bonus_value": 5},
    {"tier": "epic",      "tier_kr": "영웅",    "bonus_type": "all_stats", "bonus_value": 2},
    {"tier": "legendary", "tier_kr": "전설",    "bonus_type": "all_stats", "bonus_value": 5},
]

# Second job data per class
SECOND_JOB_TABLE = {
    "warrior": {
        "berserker": {
            "name_kr": "버서커", "desc_kr": "공격 특화, HP 소모로 데미지 증폭",
            "bonus": {"atk_pct": 20, "crit_rate_pct": 10, "def_pct": -15},
            "skills": [8, 9, 10],
        },
        "guardian": {
            "name_kr": "가디언", "desc_kr": "방어 특화, 파티 보호",
            "bonus": {"def_pct": 30, "max_hp_pct": 20, "atk_pct": -10},
            "skills": [8, 9, 10],
        },
    },
    "archer": {
        "sharpshooter": {
            "name_kr": "샤프슈터", "desc_kr": "단일 대상 극딜, 치명타 특화",
            "bonus": {"crit_rate_pct": 15, "crit_dmg_pct": 30, "attack_speed_pct": 10},
            "skills": [27, 28, 29],
        },
        "ranger": {
            "name_kr": "레인저", "desc_kr": "광역 + 기동성, 함정/다중 화살",
            "bonus": {"move_speed_pct": 15, "aoe_damage_pct": 20, "dodge_pct": 10},
            "skills": [27, 28, 29],
        },
    },
    "mage": {
        "archmage": {
            "name_kr": "아크메이지", "desc_kr": "광역 원소 마법 특화",
            "bonus": {"matk_pct": 25, "aoe_damage_pct": 30, "mp_cost_pct": 15},
            "skills": [47, 48, 49],
        },
        "priest": {
            "name_kr": "프리스트", "desc_kr": "힐러/서포터 특화",
            "bonus": {"healing_power_pct": 40, "max_mp_pct": 20, "matk_pct": -20},
            "skills": [47, 48, 49],
        },
    },
}
JOB_CHANGE_MIN_LEVEL = 20

# Milestone rewards (level -> rewards + unlocks)
MILESTONE_REWARDS = {
    5:  {"desc_kr": "일일 퀘스트 해금",        "gold": 500,   "unlock": "daily_quest"},
    10: {"desc_kr": "튜토리얼 완료",            "gold": 1000,  "unlock": "enhancement,auction"},
    15: {"desc_kr": "던전 해금",                "gold": 1500,  "unlock": "dungeon"},
    20: {"desc_kr": "2차 전직 가능",            "gold": 5000,  "unlock": "second_job,pvp_arena,mount"},
    25: {"desc_kr": "보석 시스템 해금",          "gold": 3000,  "unlock": "gem"},
    30: {"desc_kr": "길드 가입 가능",            "gold": 5000,  "unlock": "guild,ultimate_skill"},
    40: {"desc_kr": "엔드게임 진입",            "gold": 20000, "unlock": "transcend"},
    50: {"desc_kr": "레이드 입장",              "gold": 30000, "unlock": "raid,engraving"},
    60: {"desc_kr": "만렙 달성",                "gold": 50000, "unlock": "chaos_dungeon,paragon"},
}

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

# ──── PvP 아레나 상수 (P3_S01_S01) ────
PVP_MODES = {
    1: {"name": "1v1", "party_size": 1, "time_limit": 180, "overtime": 60},
    2: {"name": "3v3", "party_size": 3, "time_limit": 300, "overtime": 60},
}
PVP_NORMALIZED_STATS = {
    1: {"hp": 12000, "mp": 3000, "atk": 350, "def": 250, "name": "warrior"},  # warrior
    2: {"hp": 7000, "mp": 6000, "atk": 450, "def": 120, "name": "mage"},      # mage
    3: {"hp": 8000, "mp": 4000, "atk": 400, "def": 150, "name": "archer"},     # archer
}
PVP_DAMAGE_REDUCTION = 0.40
PVP_HEALING_REDUCTION = 0.30
PVP_CC_REDUCTION = 0.50
PVP_MIN_LEVEL = 20
PVP_ELO_INITIAL = 1000
PVP_ELO_K_BASE = 32
PVP_ELO_K_PLACEMENT = 64
PVP_ELO_K_HIGH = 16  # rating >= 2000
PVP_MATCH_RANGE_INITIAL = 100
PVP_MATCH_RANGE_EXPAND = 50
PVP_MATCH_RANGE_MAX = 500
PVP_TIERS = [
    (0, 999, "Bronze"), (1000, 1299, "Silver"), (1300, 1599, "Gold"),
    (1600, 1899, "Platinum"), (1900, 2199, "Diamond"),
    (2200, 2499, "Master"), (2500, 9999, "Grandmaster"),
]
PVP_ZONE_ID = 200  # PvP arena zone

# ──── 레이드 보스 상수 (P3_S02_S01) ────
RAID_BOSS_DATA = {
    "ancient_dragon": {
        "name": "Ancient Dragon",
        "phases": 3,
        "hp": {"normal": 2000000, "hard": 5000000},
        "atk": {"normal": 500, "hard": 800},
        "phase_thresholds": [0.70, 0.30],  # 70%, 30% HP
        "enrage_timer": {"normal": 600, "hard": 480},
        "mechanics_by_phase": {
            1: ["safe_zone", "counter_attack"],
            2: ["safe_zone", "stagger_check", "position_swap"],
            3: ["safe_zone", "stagger_check", "counter_attack", "dps_check", "cooperation"],
        },
    },
}
RAID_MECHANIC_DEFS = {
    "safe_zone":      {"id": 1, "warn_time": 3.0, "damage_pct": 0.80},
    "stagger_check":  {"id": 2, "gauge": 100, "time_limit": 10.0, "fail": "wipe"},
    "counter_attack": {"id": 3, "window": 1.5, "stun_dur": 5.0},
    "position_swap":  {"id": 4, "warn_time": 5.0, "damage_pct": 0.60},
    "dps_check":      {"id": 5, "time_limit": 15.0, "threshold_pct": 0.10, "fail": "wipe"},
    "cooperation":    {"id": 6, "tolerance": 1.0, "fail_damage_pct": 0.50},
}
RAID_CLEAR_REWARDS = {
    "normal": {"gold": 10000, "exp": 50000, "tokens": 200},
    "hard":   {"gold": 25000, "exp": 100000, "tokens": 500},
}
RAID_ZONE_ID = 103  # ancient_dragon_raid zone

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
        self.auction_listings: list = []   # [{id, seller_account, seller_name, item_id, item_count, buyout_price, bid_price, highest_bidder, highest_bidder_name, bid_account, category, listed_at, expires_at}]
        self.next_auction_id: int = 1
        self.characters: Dict[int, List[dict]] = {}  # account_id -> character list
        self.next_char_id = 1
        self.npcs: Dict[int, dict] = {}  # entity_id -> npc data
        self.instances: Dict[int, dict] = {}  # instance_id -> instance data
        self.next_instance_id = 1
        self.match_queue: Dict[int, dict] = {}  # dungeon_id -> {players: [], created_at: float}
        self.pvp_queue: Dict[int, list] = {}  # mode_id -> [{session, rating, joined_at}]
        self.pvp_matches: Dict[int, dict] = {}  # match_id -> match data
        self.next_pvp_match_id = 1
        # S041: Crafting system
        self.craft_proficiency = {}
        self.gather_energy = {}
        self.gather_proficiency = {}
        self.food_buffs = {}
        self.enchantments = {}
        self.pvp_ratings: Dict[str, dict] = {}  # username -> {rating, wins, losses, matches}
        self.raid_instances: Dict[int, dict] = {}  # instance_id -> raid data

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
            MsgType.INSTANCE_CREATE: self._on_instance_create,
            MsgType.INSTANCE_ENTER: self._on_instance_enter,
            MsgType.INSTANCE_LEAVE: self._on_instance_leave,
            MsgType.PVP_QUEUE_REQ: self._on_pvp_queue_req,
            MsgType.PVP_QUEUE_CANCEL: self._on_pvp_queue_cancel,
            MsgType.PVP_MATCH_ACCEPT: self._on_pvp_match_accept,
            MsgType.PVP_ATTACK: self._on_pvp_attack,
            MsgType.RAID_ATTACK: self._on_raid_attack,
            # S041: Crafting
            MsgType.CRAFT_LIST_REQ: self._on_craft_list_req,
            MsgType.CRAFT_EXECUTE: self._on_craft_execute,
            MsgType.GATHER_START: self._on_gather_start,
            MsgType.COOK_EXECUTE: self._on_cook_execute,
            MsgType.ENCHANT_REQ: self._on_enchant_req,

            MsgType.AUCTION_LIST_REQ: self._on_auction_list_req,
            MsgType.AUCTION_REGISTER: self._on_auction_register,
            MsgType.AUCTION_BUY: self._on_auction_buy,
            MsgType.AUCTION_BID: self._on_auction_bid,
            MsgType.TRIPOD_LIST_REQ: self._on_tripod_list_req,
            MsgType.TRIPOD_EQUIP: self._on_tripod_equip,
            MsgType.SCROLL_DISCOVER: self._on_scroll_discover,
            MsgType.BOUNTY_LIST_REQ: self._on_bounty_list_req,
            MsgType.BOUNTY_ACCEPT: self._on_bounty_accept,
            MsgType.BOUNTY_COMPLETE: self._on_bounty_complete,
            MsgType.BOUNTY_RANKING_REQ: self._on_bounty_ranking_req,
            MsgType.DAILY_QUEST_LIST_REQ: self._on_daily_quest_list_req,
            MsgType.WEEKLY_QUEST_REQ: self._on_weekly_quest_req,
            MsgType.REPUTATION_QUERY: self._on_reputation_query,
            MsgType.TITLE_LIST_REQ: self._on_title_list_req,
            MsgType.TITLE_EQUIP: self._on_title_equip,
            MsgType.COLLECTION_QUERY: self._on_collection_query,
            MsgType.JOB_CHANGE_REQ: self._on_job_change_req,
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
        """MATCH_ENQUEUE: dungeon_id(u8)+difficulty(u8) 또는 dungeon_id(u32). 매칭 큐 등록."""
        if not session.in_game or len(payload) < 1:
            return
        # 듀얼 포맷 감지: 4바이트 && byte[1]==0 && byte[2]==0 && byte[3]==0 → u32
        if len(payload) == 4 and payload[2] == 0 and payload[3] == 0:
            import struct as _st
            dungeon_id = _st.unpack("<I", payload[:4])[0]
            difficulty = 0
            is_client_format = True
        else:
            dungeon_id = payload[0]
            difficulty = payload[1] if len(payload) >= 2 else 0
            is_client_format = False
        dungeon = next((d for d in DUNGEON_LIST_DATA if d["id"] == dungeon_id), None)
        if not dungeon:
            if is_client_format:
                self._send(session, MsgType.MATCH_STATUS, struct.pack("<BI", 1, 0))
            else:
                self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 1, 0))
            return
        if session.stats.level < dungeon["min_level"]:
            if is_client_format:
                self._send(session, MsgType.MATCH_STATUS, struct.pack("<BI", 2, 0))
            else:
                self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 2, 0))
            return
        import time as _time
        queue_key = dungeon_id
        if queue_key not in self.match_queue:
            self.match_queue[queue_key] = {"players": [], "created_at": _time.time(), "difficulty": difficulty}
        queue = self.match_queue[queue_key]
        if any(p["session"] is session for p in queue["players"]):
            if is_client_format:
                self._send(session, MsgType.MATCH_STATUS, struct.pack("<BI", 3, len(queue["players"])))
            else:
                self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 3, len(queue["players"])))
            return
        queue["players"].append({"session": session, "joined_at": _time.time()})
        session._match_queue_key = queue_key
        session._match_client_format = is_client_format
        self.log(f"MatchQueue: {session.char_name} joined dungeon={dungeon_id} ({len(queue['players'])}/{dungeon['party_size']})", "GAME")
        if is_client_format:
            self._send(session, MsgType.MATCH_STATUS, struct.pack("<BI", 0, len(queue["players"])))
        else:
            self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 0, len(queue["players"])))
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
        """MATCH_DEQUEUE: dungeon_id(u8) 또는 빈 페이로드. 매칭 큐 이탈."""
        if not session.in_game:
            return
        if len(payload) >= 1:
            dungeon_id = payload[0]
            queue = self.match_queue.get(dungeon_id)
            if queue:
                queue["players"] = [p for p in queue["players"] if p["session"] is not session]
                if not queue["players"]:
                    del self.match_queue[dungeon_id]
            self.log(f"MatchQueue: {session.char_name} left dungeon={dungeon_id}", "GAME")
            self._send(session, MsgType.MATCH_STATUS, struct.pack("<BBB", dungeon_id, 4, 0))  # 4=DEQUEUED
        else:
            # 빈 페이로드: 세션이 참여 중인 모든 큐에서 제거
            removed_key = getattr(session, "_match_queue_key", None)
            for qk in list(self.match_queue.keys()):
                queue = self.match_queue[qk]
                queue["players"] = [p for p in queue["players"] if p["session"] is not session]
                if not queue["players"]:
                    del self.match_queue[qk]
            self.log(f"MatchQueue: {session.char_name} dequeued (all)", "GAME")

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

    async def _on_instance_create(self, session: PlayerSession, payload: bytes):
        """INSTANCE_CREATE: dungeon_type(u32). 즉시 인스턴스 생성 + 입장."""
        if not session.in_game or len(payload) < 4:
            return
        dungeon_type = struct.unpack("<I", payload[:4])[0]
        # 던전 데이터에서 찾기
        dungeon = next((d for d in DUNGEON_LIST_DATA if d["id"] == dungeon_type), None)
        if not dungeon:
            # 기본 던전 데이터 생성 (클라이언트 테스트용)
            dungeon = {"id": dungeon_type, "name": f"Dungeon_{dungeon_type}", "type": "party",
                       "min_level": 1, "stages": 1, "zone_id": 100, "party_size": 4,
                       "boss_id": 0, "boss_hp": 10000}
        inst_id = self.next_instance_id
        self.next_instance_id += 1
        instance = {
            "id": inst_id,
            "dungeon_id": dungeon["id"],
            "dungeon_name": dungeon["name"],
            "zone_id": dungeon.get("zone_id", 100),
            "difficulty": 0,
            "boss_hp": dungeon.get("boss_hp", 10000),
            "boss_current_hp": dungeon.get("boss_hp", 10000),
            "stage": 1,
            "max_stages": dungeon.get("stages", 1),
            "players": [session],
            "active": True,
        }
        self.instances[inst_id] = instance
        session._current_instance_id = inst_id
        session.zone_id = dungeon.get("zone_id", 100)
        session.pos.x = 50.0
        session.pos.y = 0.0
        session.pos.z = 50.0
        self.log(f"InstanceCreate: {session.char_name} -> Instance#{inst_id} dungeon={dungeon_type}", "GAME")
        # INSTANCE_ENTER 응답: result(u8) + instance_id(u32) + dungeon_type(u32)
        self._send(session, MsgType.INSTANCE_ENTER, struct.pack("<BII", 0, inst_id, dungeon_type))

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
        """INSTANCE_LEAVE: instance_id(u32) 또는 빈 페이로드. 던전 퇴장."""
        if not session.in_game:
            return
        if len(payload) >= 4:
            inst_id = struct.unpack("<I", payload[:4])[0]
            is_client_format = False
        else:
            # 빈 페이로드: 세션의 현재 인스턴스 찾기
            inst_id = getattr(session, "_current_instance_id", None)
            if inst_id is None:
                # 인스턴스에 있는지 스캔
                for iid, inst in self.instances.items():
                    if inst.get("active") and session in inst.get("players", []):
                        inst_id = iid
                        break
            if inst_id is None:
                self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<B", 1))  # 1=NOT_FOUND
                return
            is_client_format = True
        instance = self.instances.get(inst_id)
        if not instance:
            if is_client_format:
                self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<B", 1))
            else:
                self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<IB", inst_id, 1))
            return
        if session in instance["players"]:
            instance["players"].remove(session)
        if not instance["players"]:
            instance["active"] = False
            self.log(f"Instance #{inst_id} closed (no players left)", "GAME")
        session.zone_id = 10
        session.pos.x = 150.0
        session.pos.y = 0.0
        session.pos.z = 150.0
        session._current_instance_id = None
        self.log(f"InstanceLeave: {session.char_name} <- Instance#{inst_id}", "GAME")
        if is_client_format:
            self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<B", 0))  # 0=OK
        else:
            self._send(session, MsgType.INSTANCE_LEAVE_RESULT, struct.pack("<IB", inst_id, 0))  # 0=OK

    # ━━━ PvP 아레나 시스템 (P3_S01_S01) ━━━

    def _get_pvp_rating(self, username: str) -> dict:
        """PvP 레이팅 조회 (없으면 초기값 생성)"""
        if username not in self.pvp_ratings:
            self.pvp_ratings[username] = {
                "rating": PVP_ELO_INITIAL,
                "wins": 0, "losses": 0, "matches": 0,
            }
        return self.pvp_ratings[username]

    def _get_tier(self, rating: int) -> str:
        """ELO 레이팅으로 티어 문자열 반환"""
        for lo, hi, name in PVP_TIERS:
            if lo <= rating <= hi:
                return name
        return "Bronze"

    def _calc_elo(self, winner_r: int, loser_r: int, k: int) -> tuple:
        """ELO 계산 → (new_winner_rating, new_loser_rating)"""
        exp_w = 1.0 / (1.0 + 10 ** ((loser_r - winner_r) / 400.0))
        exp_l = 1.0 - exp_w
        new_w = max(0, int(winner_r + k * (1.0 - exp_w)))
        new_l = max(0, int(loser_r + k * (0.0 - exp_l)))
        return new_w, new_l

    async def _on_pvp_queue_req(self, session: PlayerSession, payload: bytes):
        """PVP_QUEUE_REQ: mode(u8). 아레나 매칭 큐 등록."""
        if not session.in_game or len(payload) < 1:
            return
        mode_id = payload[0]
        mode = PVP_MODES.get(mode_id)
        if not mode:
            self._send(session, MsgType.PVP_QUEUE_STATUS, struct.pack("<BBH", mode_id, 1, 0))  # 1=INVALID_MODE
            return
        if session.stats.level < PVP_MIN_LEVEL:
            self._send(session, MsgType.PVP_QUEUE_STATUS, struct.pack("<BBH", mode_id, 2, 0))  # 2=LEVEL_TOO_LOW
            return
        if mode_id not in self.pvp_queue:
            self.pvp_queue[mode_id] = []
        queue = self.pvp_queue[mode_id]
        if any(e["session"] is session for e in queue):
            self._send(session, MsgType.PVP_QUEUE_STATUS, struct.pack("<BBH", mode_id, 3, len(queue)))  # 3=ALREADY_QUEUED
            return
        import time as _t
        rating_info = self._get_pvp_rating(session.username)
        queue.append({"session": session, "rating": rating_info["rating"], "joined_at": _t.time()})
        self.log(f"PvPQueue: {session.char_name} joined mode={mode['name']} rating={rating_info['rating']} ({len(queue)} in queue)", "PVP")
        self._send(session, MsgType.PVP_QUEUE_STATUS, struct.pack("<BBH", mode_id, 0, len(queue)))  # 0=QUEUED
        # 매칭 시도
        needed = mode["party_size"] * 2  # 양쪽 합계
        if len(queue) >= needed:
            await self._pvp_match_found(mode_id, mode)

    async def _pvp_match_found(self, mode_id: int, mode: dict):
        """PvP 매칭 완료 → 매치 생성"""
        queue = self.pvp_queue.get(mode_id, [])
        needed = mode["party_size"] * 2
        if len(queue) < needed:
            return
        # 레이팅 가까운 순으로 정렬 후 추출
        queue.sort(key=lambda e: e["rating"])
        picked = queue[:needed]
        self.pvp_queue[mode_id] = queue[needed:]
        # 팀 분배: 짝수=Team A, 홀수=Team B (레이팅 밸런스)
        team_a = [picked[i] for i in range(0, needed, 2)]
        team_b = [picked[i] for i in range(1, needed, 2)]
        match_id = self.next_pvp_match_id
        self.next_pvp_match_id += 1
        # 스탯 정규화 적용
        match_data = {
            "id": match_id,
            "mode_id": mode_id,
            "mode": mode,
            "team_a": [e["session"] for e in team_a],
            "team_b": [e["session"] for e in team_b],
            "team_a_hp": {},  # session -> current_hp
            "team_b_hp": {},
            "active": True,
            "zone_id": 200 if mode_id == 1 else 201,
            "started": False,
        }
        # 각 플레이어에 정규화 스탯 적용
        all_players = team_a + team_b
        for entry in all_players:
            s = entry["session"]
            job = 1  # default warrior
            if hasattr(s, "job_id"):
                job = s.job_id
            norm = PVP_NORMALIZED_STATS.get(job, PVP_NORMALIZED_STATS[1])
            hp = norm["hp"]
            if s in [e["session"] for e in team_a]:
                match_data["team_a_hp"][id(s)] = hp
            else:
                match_data["team_b_hp"][id(s)] = hp
        self.pvp_matches[match_id] = match_data
        self.log(f"PvP Match #{match_id} created: {mode['name']} ({len(team_a)}v{len(team_b)})", "PVP")
        # PVP_MATCH_FOUND 전송
        for entry in all_players:
            s = entry["session"]
            team_id = 0 if s in match_data["team_a"] else 1
            self._send(s, MsgType.PVP_MATCH_FOUND, struct.pack("<IBB", match_id, mode_id, team_id))

    async def _on_pvp_queue_cancel(self, session: PlayerSession, payload: bytes):
        """PVP_QUEUE_CANCEL: mode(u8). 큐에서 이탈."""
        if not session.in_game or len(payload) < 1:
            return
        mode_id = payload[0]
        queue = self.pvp_queue.get(mode_id, [])
        self.pvp_queue[mode_id] = [e for e in queue if e["session"] is not session]
        self.log(f"PvPQueue: {session.char_name} left mode={mode_id}", "PVP")
        self._send(session, MsgType.PVP_QUEUE_STATUS, struct.pack("<BBH", mode_id, 4, 0))  # 4=CANCELLED

    async def _on_pvp_match_accept(self, session: PlayerSession, payload: bytes):
        """PVP_MATCH_ACCEPT: match_id(u32). 매치 수락 → 시작."""
        if not session.in_game or len(payload) < 4:
            return
        match_id = struct.unpack("<I", payload[:4])[0]
        match = self.pvp_matches.get(match_id)
        if not match or not match["active"]:
            return
        if not match["started"]:
            match["started"] = True
            import time as _t
            match["start_time"] = _t.time()
            # 존 전환 + 스탯 정규화 적용
            all_players = match["team_a"] + match["team_b"]
            for s in all_players:
                s.zone_id = match["zone_id"]
            # PVP_MATCH_START 전송: match_id(u32) + mode(u8) + time_limit(u16)
            for s in all_players:
                team_id = 0 if s in match["team_a"] else 1
                self._send(s, MsgType.PVP_MATCH_START, struct.pack("<IBH", match_id, team_id, match["mode"]["time_limit"]))
            self.log(f"PvP Match #{match_id} STARTED", "PVP")

    async def _on_pvp_attack(self, session: PlayerSession, payload: bytes):
        """PVP_ATTACK: match_id(u32) + target_team(u8) + target_idx(u8) + skill_id(u16) + damage(u16)."""
        if not session.in_game or len(payload) < 10:
            return
        match_id, target_team, target_idx, skill_id, raw_dmg = struct.unpack("<IBBHH", payload[:10])
        match = self.pvp_matches.get(match_id)
        if not match or not match["active"] or not match["started"]:
            return
        # PvP 데미지 감소 적용
        damage = int(raw_dmg * (1.0 - PVP_DAMAGE_REDUCTION))
        # 타겟 팀에서 대상 찾기
        target_list = match["team_b"] if target_team == 1 else match["team_a"]
        hp_map = match["team_b_hp"] if target_team == 1 else match["team_a_hp"]
        if target_idx >= len(target_list):
            return
        target = target_list[target_idx]
        target_key = id(target)
        current_hp = hp_map.get(target_key, 0)
        new_hp = max(0, current_hp - damage)
        hp_map[target_key] = new_hp
        # PVP_ATTACK_RESULT: match_id(u32) + attacker_team(u8) + target_team(u8) + target_idx(u8) + damage(u16) + remaining_hp(u32)
        attacker_team = 0 if session in match["team_a"] else 1
        result_pkt = struct.pack("<IBBBHI", match_id, attacker_team, target_team, target_idx, damage, new_hp)
        for s in match["team_a"] + match["team_b"]:
            self._send(s, MsgType.PVP_ATTACK_RESULT, result_pkt)
        # 승패 확인
        if new_hp <= 0:
            alive_a = sum(1 for s in match["team_a"] if match["team_a_hp"].get(id(s), 0) > 0)
            alive_b = sum(1 for s in match["team_b"] if match["team_b_hp"].get(id(s), 0) > 0)
            if alive_a == 0 or alive_b == 0:
                winner_team = 1 if alive_a == 0 else 0
                await self._pvp_match_end(match_id, winner_team)

    async def _pvp_match_end(self, match_id: int, winner_team: int):
        """PvP 경기 종료 → ELO 계산 → 결과 전송"""
        match = self.pvp_matches.get(match_id)
        if not match or not match["active"]:
            return
        match["active"] = False
        winners = match["team_a"] if winner_team == 0 else match["team_b"]
        losers = match["team_b"] if winner_team == 0 else match["team_a"]
        # ELO 계산
        for w in winners:
            w_info = self._get_pvp_rating(w.username)
            avg_loser_r = sum(self._get_pvp_rating(l.username)["rating"] for l in losers) // max(1, len(losers))
            k = PVP_ELO_K_PLACEMENT if w_info["matches"] < 10 else (PVP_ELO_K_HIGH if w_info["rating"] >= 2000 else PVP_ELO_K_BASE)
            new_r, _ = self._calc_elo(w_info["rating"], avg_loser_r, k)
            w_info["rating"] = new_r
            w_info["wins"] += 1
            w_info["matches"] += 1
        for l in losers:
            l_info = self._get_pvp_rating(l.username)
            avg_winner_r = sum(self._get_pvp_rating(w.username)["rating"] for w in winners) // max(1, len(winners))
            k = PVP_ELO_K_PLACEMENT if l_info["matches"] < 10 else (PVP_ELO_K_HIGH if l_info["rating"] >= 2000 else PVP_ELO_K_BASE)
            _, new_r = self._calc_elo(avg_winner_r, l_info["rating"], k)
            l_info["rating"] = new_r
            l_info["losses"] += 1
            l_info["matches"] += 1
        # PVP_MATCH_END 전송: match_id(u32) + winner_team(u8) + new_rating(u16) + rating_change(i16)
        all_players = match["team_a"] + match["team_b"]
        for s in all_players:
            r_info = self._get_pvp_rating(s.username)
            team_id = 0 if s in match["team_a"] else 1
            won = 1 if team_id == winner_team else 0
            tier_str = self._get_tier(r_info["rating"])
            tier_bytes = tier_str.encode("utf-8")[:16].ljust(16, b"\x00")
            buf = struct.pack("<IBBH", match_id, winner_team, won, r_info["rating"])
            buf += tier_bytes
            self._send(s, MsgType.PVP_MATCH_END, buf)
            # 마을로 복귀
            s.zone_id = 10
        self.log(f"PvP Match #{match_id} ended: Team {winner_team} wins", "PVP")

    # ━━━ 레이드 보스 기믹 시스템 (P3_S02_S01) ━━━

    async def _start_raid_boss(self, instance_id: int):
        """레이드 인스턴스에 보스 스폰 + 기믹 초기화"""
        instance = self.instances.get(instance_id)
        if not instance:
            return
        boss_key = "ancient_dragon"
        boss_def = RAID_BOSS_DATA[boss_key]
        diff_name = ["normal", "hard"][min(instance.get("difficulty", 0), 1)]
        import time as _t
        raid_data = {
            "instance_id": instance_id,
            "boss_key": boss_key,
            "boss_name": boss_def["name"],
            "max_hp": boss_def["hp"][diff_name],
            "current_hp": boss_def["hp"][diff_name],
            "atk": boss_def["atk"][diff_name],
            "phase": 1,
            "max_phases": boss_def["phases"],
            "phase_thresholds": boss_def["phase_thresholds"],
            "enrage_timer": boss_def["enrage_timer"][diff_name],
            "start_time": _t.time(),
            "enraged": False,
            "difficulty": diff_name,
            "mechanics": boss_def["mechanics_by_phase"],
            "stagger_gauge": 0,
            "mechanic_active": None,
            "active": True,
        }
        self.raid_instances[instance_id] = raid_data
        # RAID_BOSS_SPAWN 전송
        name_bytes = raid_data["boss_name"].encode("utf-8")[:32].ljust(32, b"\x00")
        buf = struct.pack("<I", instance_id) + name_bytes
        buf += struct.pack("<IIBB", raid_data["max_hp"], raid_data["current_hp"],
                           raid_data["phase"], raid_data["max_phases"])
        buf += struct.pack("<H", raid_data["enrage_timer"])
        for s in instance.get("players", []):
            self._send(s, MsgType.RAID_BOSS_SPAWN, buf)
        self.log(f"Raid Boss spawned: {raid_data['boss_name']} ({diff_name}) in Instance#{instance_id}", "RAID")

    async def _on_raid_attack(self, session: PlayerSession, payload: bytes):
        """RAID_ATTACK: instance_id(u32) + skill_id(u16) + damage(u32)."""
        if not session.in_game or len(payload) < 10:
            return
        inst_id = struct.unpack("<I", payload[:4])[0]
        skill_id = struct.unpack("<H", payload[4:6])[0]
        raw_dmg = struct.unpack("<I", payload[6:10])[0]
        raid = self.raid_instances.get(inst_id)
        if not raid or not raid["active"]:
            return
        instance = self.instances.get(inst_id)
        if not instance:
            return
        # 데미지 적용
        raid["current_hp"] = max(0, raid["current_hp"] - raw_dmg)
        hp_pct = raid["current_hp"] / raid["max_hp"] if raid["max_hp"] > 0 else 0
        # 스태거 게이지 증가 (스킬 공격 시)
        if raid.get("mechanic_active") == "stagger_check":
            raid["stagger_gauge"] = min(100, raid["stagger_gauge"] + 15)
            stagger_buf = struct.pack("<IB", inst_id, raid["stagger_gauge"])
            for s in instance.get("players", []):
                self._send(s, MsgType.RAID_STAGGER, stagger_buf)
            if raid["stagger_gauge"] >= 100:
                raid["mechanic_active"] = None
                raid["stagger_gauge"] = 0
                # 기믹 성공
                for s in instance.get("players", []):
                    self._send(s, MsgType.RAID_MECHANIC_RESULT, struct.pack("<IBB", inst_id, 2, 1))  # id=2(stagger), success=1
        # RAID_ATTACK_RESULT 전송
        result_buf = struct.pack("<IHI II", inst_id, skill_id, raw_dmg,
                                raid["current_hp"], raid["max_hp"])
        for s in instance.get("players", []):
            self._send(s, MsgType.RAID_ATTACK_RESULT, result_buf)
        # 페이즈 전환 체크
        thresholds = raid["phase_thresholds"]
        for i, thr in enumerate(thresholds):
            target_phase = i + 2
            if hp_pct <= thr and raid["phase"] < target_phase:
                raid["phase"] = target_phase
                phase_buf = struct.pack("<IBB", inst_id, raid["phase"], raid["max_phases"])
                for s in instance.get("players", []):
                    self._send(s, MsgType.RAID_PHASE_CHANGE, phase_buf)
                self.log(f"Raid Boss phase → {raid['phase']} (HP {hp_pct:.1%})", "RAID")
                # 새 페이즈 기믹 발동
                mechanics = raid["mechanics"].get(raid["phase"], [])
                if mechanics:
                    await self._trigger_raid_mechanic(inst_id, mechanics[0])
                break
        # 클리어 체크
        if raid["current_hp"] <= 0:
            await self._raid_clear(inst_id)

    async def _trigger_raid_mechanic(self, inst_id: int, mechanic_name: str):
        """레이드 기믹 발동"""
        raid = self.raid_instances.get(inst_id)
        instance = self.instances.get(inst_id)
        if not raid or not instance:
            return
        mech_def = RAID_MECHANIC_DEFS.get(mechanic_name)
        if not mech_def:
            return
        raid["mechanic_active"] = mechanic_name
        if mechanic_name == "stagger_check":
            raid["stagger_gauge"] = 0
        # RAID_MECHANIC 전송: instance_id(u32) + mechanic_id(u8) + phase(u8)
        buf = struct.pack("<IBB", inst_id, mech_def["id"], raid["phase"])
        for s in instance.get("players", []):
            self._send(s, MsgType.RAID_MECHANIC, buf)
        self.log(f"Raid Mechanic: {mechanic_name} (phase {raid['phase']}) in Instance#{inst_id}", "RAID")

    async def _raid_clear(self, inst_id: int):
        """레이드 클리어 → 보상 지급"""
        raid = self.raid_instances.get(inst_id)
        instance = self.instances.get(inst_id)
        if not raid or not instance:
            return
        raid["active"] = False
        diff = raid["difficulty"]
        rewards = RAID_CLEAR_REWARDS.get(diff, RAID_CLEAR_REWARDS["normal"])
        # RAID_CLEAR 전송: instance_id(u32) + gold(u32) + exp(u32) + tokens(u16)
        buf = struct.pack("<IIIH", inst_id, rewards["gold"], rewards["exp"], rewards["tokens"])
        for s in instance.get("players", []):
            s.gold += rewards["gold"]
            s.stats.add_exp(rewards["exp"])
            self._send(s, MsgType.RAID_CLEAR, buf)
        self.log(f"Raid CLEAR! Instance#{inst_id} ({diff}) - rewards: {rewards}", "RAID")

    async def _raid_wipe(self, inst_id: int):
        """레이드 전멸"""
        raid = self.raid_instances.get(inst_id)
        instance = self.instances.get(inst_id)
        if not raid or not instance:
            return
        raid["active"] = False
        buf = struct.pack("<IB", inst_id, raid["phase"])
        for s in instance.get("players", []):
            self._send(s, MsgType.RAID_WIPE, buf)
            s.zone_id = 10  # 마을로 복귀
        self.log(f"Raid WIPE at phase {raid['phase']} in Instance#{inst_id}", "RAID")

    # ━━━ 몬스터 시스템 ━━━







    # ---- Progression Deepening (TASK 7: MsgType 440-447) ----

    def _check_title_conditions(self, session):
        """Check all title conditions and unlock new titles."""
        level = session.stats.level if session.stats else 1
        gold = getattr(session, 'gold', 0)
        newly_unlocked = []

        for title in TITLE_LIST_DATA:
            tid = title["title_id"]
            if tid in session.titles_unlocked:
                continue
            ct = title["condition_type"]
            cv = title["condition_value"]
            unlocked = False
            if ct == "level" and level >= cv:
                unlocked = True
            elif ct == "dungeon_clear" and session.dungeon_clears >= cv:
                unlocked = True
            elif ct == "boss_kill" and session.boss_kills >= cv:
                unlocked = True
            elif ct == "gold_held" and gold >= cv:
                unlocked = True
            # pvp_rank, guild_level, all_quests — check when relevant data available
            if unlocked:
                session.titles_unlocked.append(tid)
                newly_unlocked.append(tid)
        return newly_unlocked

    async def _on_title_list_req(self, session, payload: bytes):
        """TITLE_LIST_REQ(440) -> TITLE_LIST(441)
        Response: equipped_id(u16) + count(u8) + [title_id(u16) + name_len(u8) + name(str) +
                  bonus_type_len(u8) + bonus_type(str) + bonus_value(u16) + unlocked(u8)]"""
        if not session.in_game:
            return

        # Re-check conditions
        self._check_title_conditions(session)

        data = struct.pack('<H B', session.title_equipped, len(TITLE_LIST_DATA))
        for title in TITLE_LIST_DATA:
            name_bytes = title["name_kr"].encode('utf-8')
            bt_bytes = title["bonus_type"].encode('utf-8')
            is_unlocked = 1 if title["title_id"] in session.titles_unlocked else 0
            data += struct.pack('<H B', title["title_id"], len(name_bytes))
            data += name_bytes
            data += struct.pack('<B', len(bt_bytes))
            data += bt_bytes
            data += struct.pack('<H B', title["bonus_value"], is_unlocked)
        self._send(session, MsgType.TITLE_LIST, data)

    async def _on_title_equip(self, session, payload: bytes):
        """TITLE_EQUIP(442) -> TITLE_EQUIP_RESULT(443)
        Request: title_id(u16) — 0 to unequip
        Response: result(u8) + title_id(u16)
        result: 0=SUCCESS, 1=NOT_UNLOCKED, 2=ALREADY_EQUIPPED"""
        if not session.in_game:
            return
        if len(payload) < 2:
            return

        title_id = struct.unpack_from('<H', payload, 0)[0]

        # Unequip
        if title_id == 0:
            session.title_equipped = 0
            self._send(session, MsgType.TITLE_EQUIP_RESULT, struct.pack('<B H', 0, 0))
            return

        # Check if unlocked
        self._check_title_conditions(session)
        if title_id not in session.titles_unlocked:
            self._send(session, MsgType.TITLE_EQUIP_RESULT, struct.pack('<B H', 1, title_id))
            return

        # Check if already equipped
        if session.title_equipped == title_id:
            self._send(session, MsgType.TITLE_EQUIP_RESULT, struct.pack('<B H', 2, title_id))
            return

        # Equip
        session.title_equipped = title_id
        self._send(session, MsgType.TITLE_EQUIP_RESULT, struct.pack('<B H', 0, title_id))

    async def _on_collection_query(self, session, payload: bytes):
        """COLLECTION_QUERY(444) -> COLLECTION_INFO(445)
        Response: monster_cat_count(u8) + [cat_id(u8) + name_len(u8) + name(str) +
                  total(u8) + registered(u8) + completed(u8) +
                  bonus_type_len(u8) + bonus_type(str) + bonus_value(u16)] +
                 equip_tier_count(u8) + [tier_len(u8) + tier(str) +
                  tier_kr_len(u8) + tier_kr(str) + registered(u8) +
                  bonus_type_len(u8) + bonus_type(str) + bonus_value(u16)]"""
        if not session.in_game:
            return

        # Monster categories
        data = struct.pack('<B', len(COLLECTION_MONSTER_CATEGORIES))
        for cat in COLLECTION_MONSTER_CATEGORIES:
            name_bytes = cat["name_kr"].encode('utf-8')
            bt_bytes = cat["bonus_type"].encode('utf-8')
            total = len(cat["monsters"])
            registered = sum(1 for m in cat["monsters"] if m in session.collection_monsters)
            completed = 1 if registered >= total else 0
            data += struct.pack('<B B', cat["cat_id"], len(name_bytes))
            data += name_bytes
            data += struct.pack('<BBB B', total, registered, completed, len(bt_bytes))
            data += bt_bytes
            data += struct.pack('<H', cat["bonus_value"])

        # Equipment tiers
        data += struct.pack('<B', len(COLLECTION_EQUIP_TIERS))
        for tier_info in COLLECTION_EQUIP_TIERS:
            tier_bytes = tier_info["tier"].encode('utf-8')
            tier_kr_bytes = tier_info["tier_kr"].encode('utf-8')
            bt_bytes = tier_info["bonus_type"].encode('utf-8')
            registered = 1 if tier_info["tier"] in session.collection_equip_tiers else 0
            data += struct.pack('<B', len(tier_bytes))
            data += tier_bytes
            data += struct.pack('<B', len(tier_kr_bytes))
            data += tier_kr_bytes
            data += struct.pack('<B B', registered, len(bt_bytes))
            data += bt_bytes
            data += struct.pack('<H', tier_info["bonus_value"])

        self._send(session, MsgType.COLLECTION_INFO, data)

    async def _on_job_change_req(self, session, payload: bytes):
        """JOB_CHANGE_REQ(446) -> JOB_CHANGE_RESULT(447)
        Request: job_name_len(u8) + job_name(str) — e.g. "berserker", "guardian"
        Response: result(u8) + job_name_len(u8) + job_name(str) + bonus_count(u8) +
                  [bonus_key_len(u8) + bonus_key(str) + bonus_value(i16)] +
                  new_skill_count(u8) + [skill_id(u16)]
        result: 0=SUCCESS, 1=LEVEL_TOO_LOW, 2=ALREADY_CHANGED, 3=INVALID_JOB, 4=WRONG_CLASS"""
        if not session.in_game:
            return
        if len(payload) < 1:
            return

        name_len = payload[0]
        if len(payload) < 1 + name_len:
            return
        job_name = payload[1:1+name_len].decode('utf-8')

        # Check level
        level = session.stats.level if session.stats else 1
        if level < JOB_CHANGE_MIN_LEVEL:
            job_bytes = job_name.encode('utf-8')
            self._send(session, MsgType.JOB_CHANGE_RESULT,
                       struct.pack('<B B', 1, len(job_bytes)) + job_bytes +
                       struct.pack('<B B', 0, 0))
            return

        # Check already changed
        if session.second_job:
            job_bytes = job_name.encode('utf-8')
            self._send(session, MsgType.JOB_CHANGE_RESULT,
                       struct.pack('<B B', 2, len(job_bytes)) + job_bytes +
                       struct.pack('<B B', 0, 0))
            return

        # Determine player class
        player_class = getattr(session, 'player_class', 'warrior')

        # Find the job in table
        if player_class not in SECOND_JOB_TABLE:
            job_bytes = job_name.encode('utf-8')
            self._send(session, MsgType.JOB_CHANGE_RESULT,
                       struct.pack('<B B', 4, len(job_bytes)) + job_bytes +
                       struct.pack('<B B', 0, 0))
            return

        class_jobs = SECOND_JOB_TABLE[player_class]
        if job_name not in class_jobs:
            job_bytes = job_name.encode('utf-8')
            # Check if it's a valid job for another class
            found_in_other = False
            for cls, jobs in SECOND_JOB_TABLE.items():
                if job_name in jobs:
                    found_in_other = True
                    break
            result_code = 4 if found_in_other else 3
            self._send(session, MsgType.JOB_CHANGE_RESULT,
                       struct.pack('<B B', result_code, len(job_bytes)) + job_bytes +
                       struct.pack('<B B', 0, 0))
            return

        # Apply job change
        job_data = class_jobs[job_name]
        session.second_job = job_name
        session.second_job_class = player_class

        # Build response
        job_bytes = job_name.encode('utf-8')
        bonus = job_data["bonus"]
        skills = job_data["skills"]

        data = struct.pack('<B B', 0, len(job_bytes))
        data += job_bytes
        data += struct.pack('<B', len(bonus))
        for bk, bv in bonus.items():
            bk_bytes = bk.encode('utf-8')
            data += struct.pack('<B', len(bk_bytes))
            data += bk_bytes
            data += struct.pack('<h', bv)  # signed i16 for negative bonuses
        data += struct.pack('<B', len(skills))
        for sid in skills:
            data += struct.pack('<H', sid)

        self._send(session, MsgType.JOB_CHANGE_RESULT, data)

    def _on_monster_kill_collection(self, session, monster_name):
        """Register monster kill in collection. Called from kill handlers."""
        if monster_name and monster_name not in session.collection_monsters:
            session.collection_monsters.append(monster_name)

    def _check_milestone_on_levelup(self, session, new_level):
        """Check and grant milestone rewards on level up."""
        if new_level in MILESTONE_REWARDS and new_level not in session.milestones_claimed:
            milestone = MILESTONE_REWARDS[new_level]
            session.milestones_claimed.append(new_level)
            # Grant gold
            session.gold = getattr(session, 'gold', 0) + milestone["gold"]
            # Check title unlocks
            self._check_title_conditions(session)
            return milestone
        return None


    # ---- Quest Enhancement (TASK 4: MsgType 400-405) ----

    def _generate_daily_quests_for_day(self):
        """Generate 3 random daily quests from pool (seeded by date)."""
        import time as _t
        import random as _rng_dq
        date_seed = int(_t.strftime("%Y%m%d"))
        _rng_dq.seed(date_seed + 4000)  # offset to not collide with bounty seed
        pool = list(DAILY_QUEST_POOL)
        _rng_dq.shuffle(pool)
        selected = pool[:DAILY_QUEST_MAX_ACTIVE]
        _rng_dq.seed()  # restore
        return selected

    def _get_weekly_quest_for_week(self):
        """Get current weekly quest (rotate by week number)."""
        import time as _t
        week_num = int(_t.time()) // (7 * 86400)
        return WEEKLY_QUEST_POOL[week_num % len(WEEKLY_QUEST_POOL)]

    def _check_daily_quest_reset(self, session):
        """Reset daily quests if new day."""
        import time as _t
        today = _t.strftime("%Y-%m-%d")
        if session.daily_quest_reset_date != today:
            session.daily_quests = []
            session.daily_quest_reset_date = today

    def _check_weekly_quest_reset(self, session):
        """Reset weekly quest if new week (Wednesday)."""
        import datetime
        now = datetime.datetime.now()
        days_since_wed = (now.weekday() - 2) % 7
        last_wed = (now - datetime.timedelta(days=days_since_wed)).strftime("%Y-%m-%d")
        if session.weekly_quest_reset_date != last_wed:
            session.weekly_quest = {}
            session.weekly_quest_reset_date = last_wed

    def _check_rep_daily_reset(self, session):
        """Reset daily reputation gain counter."""
        import time as _t
        today = _t.strftime("%Y-%m-%d")
        if session.reputation_daily_reset_date != today:
            session.reputation_daily_gained = {f: 0 for f in REPUTATION_FACTIONS}
            session.reputation_daily_reset_date = today

    def _add_reputation(self, session, faction, amount, is_quest_reward=False):
        """Add reputation to faction. Quest rewards bypass daily cap."""
        if faction not in REPUTATION_FACTIONS:
            return 0
        self._check_rep_daily_reset(session)
        if not is_quest_reward:
            # Check daily cap
            already = session.reputation_daily_gained.get(faction, 0)
            remaining = max(0, REPUTATION_DAILY_CAP - already)
            amount = min(amount, remaining)
            if amount <= 0:
                return 0
            session.reputation_daily_gained[faction] = already + amount
        current = session.reputation.get(faction, 0)
        session.reputation[faction] = current + amount
        return amount

    def _get_rep_tier(self, faction, points):
        """Get reputation tier name for given points."""
        if faction not in REPUTATION_FACTIONS:
            return "unknown", 0
        tiers = REPUTATION_FACTIONS[faction]["tiers"]
        current_tier = tiers[0]
        for tier in tiers:
            if points >= tier["min"]:
                current_tier = tier
        return current_tier["name"], current_tier["min"]

    async def _on_daily_quest_list_req(self, session, payload: bytes):
        """DAILY_QUEST_LIST_REQ(400) -> DAILY_QUEST_LIST(401)
        Response: quest_count(u8) + [dq_id(u16) + type_len(u8) + type(str) +
                  name_len(u8) + name(str) + target_id(u16) + count(u8) +
                  progress(u8) + completed(u8) +
                  reward_exp(u32) + reward_gold(u32) + rep_faction_len(u8) + rep_faction(str) + rep_amount(u16)]"""
        if not session.in_game:
            return

        level = session.stats.level if session.stats else 1
        if level < DAILY_QUEST_MIN_LEVEL:
            self._send(session, MsgType.DAILY_QUEST_LIST, struct.pack('<B', 0))
            return

        self._check_daily_quest_reset(session)

        # Generate today's daily quests
        today_quests = self._generate_daily_quests_for_day()

        # Initialize session daily quests if empty (first request of day)
        if not session.daily_quests:
            for dq in today_quests:
                session.daily_quests.append({
                    "dq_id": dq["dq_id"],
                    "type": dq["type"],
                    "target_id": dq["target_id"],
                    "count": dq["count"],
                    "progress": 0,
                    "completed": False,
                })

        # Build response
        data = struct.pack('<B', len(today_quests))
        for i, dq in enumerate(today_quests):
            # Get progress from session
            sq = session.daily_quests[i] if i < len(session.daily_quests) else {"progress": 0, "completed": False}
            type_bytes = dq["type"].encode('utf-8')
            name_bytes = dq["name_kr"].encode('utf-8')
            fac_bytes = dq["reward_rep_faction"].encode('utf-8')
            data += struct.pack('<H B', dq["dq_id"], len(type_bytes))
            data += type_bytes
            data += struct.pack('<B', len(name_bytes))
            data += name_bytes
            data += struct.pack('<HBB B II B',
                               dq["target_id"], dq["count"],
                               sq["progress"], 1 if sq["completed"] else 0,
                               dq["reward_exp"], dq["reward_gold"],
                               len(fac_bytes))
            data += fac_bytes
            data += struct.pack('<H', dq["reward_rep"])

        self._send(session, MsgType.DAILY_QUEST_LIST, data)

    async def _on_weekly_quest_req(self, session, payload: bytes):
        """WEEKLY_QUEST_REQ(402) -> WEEKLY_QUEST(403)
        Response: has_quest(u8) + [wq_id(u16) + type_len(u8) + type(str) +
                  name_len(u8) + name(str) + target_id(u16) + count(u8) +
                  progress(u8) + completed(u8) +
                  reward_exp(u32) + reward_gold(u32) + reward_dungeon_token(u8) +
                  rep_faction_len(u8) + rep_faction(str) + rep_amount(u16)]"""
        if not session.in_game:
            return

        level = session.stats.level if session.stats else 1
        if level < WEEKLY_QUEST_MIN_LEVEL:
            self._send(session, MsgType.WEEKLY_QUEST, struct.pack('<B', 0))
            return

        self._check_weekly_quest_reset(session)

        wq = self._get_weekly_quest_for_week()

        # Initialize session weekly quest if empty
        if not session.weekly_quest:
            session.weekly_quest = {
                "wq_id": wq["wq_id"],
                "type": wq["type"],
                "target_id": wq["target_id"],
                "count": wq["count"],
                "progress": 0,
                "completed": False,
            }

        sq = session.weekly_quest
        type_bytes = wq["type"].encode('utf-8')
        name_bytes = wq["name_kr"].encode('utf-8')
        fac_bytes = wq["reward_rep_faction"].encode('utf-8')

        data = struct.pack('<B H B', 1, wq["wq_id"], len(type_bytes))
        data += type_bytes
        data += struct.pack('<B', len(name_bytes))
        data += name_bytes
        data += struct.pack('<HBB B II B B',
                           wq["target_id"], wq["count"],
                           sq["progress"], 1 if sq["completed"] else 0,
                           wq["reward_exp"], wq["reward_gold"],
                           wq.get("reward_dungeon_token", 0),
                           len(fac_bytes))
        data += fac_bytes
        data += struct.pack('<H', wq["reward_rep"])

        self._send(session, MsgType.WEEKLY_QUEST, data)

    async def _on_reputation_query(self, session, payload: bytes):
        """REPUTATION_QUERY(404) -> REPUTATION_INFO(405)
        Response: faction_count(u8) + [faction_len(u8) + faction(str) +
                  name_kr_len(u8) + name_kr(str) + points(u32) +
                  tier_name_len(u8) + tier_name(str) + next_tier_min(u32)]"""
        if not session.in_game:
            return

        self._check_rep_daily_reset(session)

        factions = list(REPUTATION_FACTIONS.items())
        data = struct.pack('<B', len(factions))
        for fac_key, fac_info in factions:
            points = session.reputation.get(fac_key, 0)
            tier_name, tier_min = self._get_rep_tier(fac_key, points)

            # Find next tier min
            tiers = fac_info["tiers"]
            next_tier_min = 0
            for i, t in enumerate(tiers):
                if t["name"] == tier_name and i + 1 < len(tiers):
                    next_tier_min = tiers[i + 1]["min"]
                    break

            fac_bytes = fac_key.encode('utf-8')
            name_kr_bytes = fac_info["name_kr"].encode('utf-8')
            tier_bytes = tier_name.encode('utf-8')

            data += struct.pack('<B', len(fac_bytes))
            data += fac_bytes
            data += struct.pack('<B', len(name_kr_bytes))
            data += name_kr_bytes
            data += struct.pack('<I B', points, len(tier_bytes))
            data += tier_bytes
            data += struct.pack('<I', next_tier_min)

        self._send(session, MsgType.REPUTATION_INFO, data)

    def _on_daily_quest_progress(self, session, event_type, target_id):
        """Track daily quest progress on events (monster kill, collect, craft).
        Called from kill/craft/gather handlers."""
        if not session.daily_quests:
            return
        for dq in session.daily_quests:
            if dq["completed"]:
                continue
            if dq["type"] == event_type and dq["target_id"] == target_id:
                dq["progress"] = min(dq["progress"] + 1, dq["count"])

    def _complete_daily_quest(self, session, dq_id):
        """Complete a daily quest and give rewards."""
        for dq in session.daily_quests:
            if dq["dq_id"] == dq_id and not dq["completed"] and dq["progress"] >= dq["count"]:
                dq["completed"] = True
                # Find quest data for rewards
                for pool_q in DAILY_QUEST_POOL:
                    if pool_q["dq_id"] == dq_id:
                        if session.stats:
                            session.stats.add_exp(pool_q["reward_exp"])
                        session.gold = getattr(session, 'gold', 0) + pool_q["reward_gold"]
                        self._add_reputation(session, pool_q["reward_rep_faction"],
                                           pool_q["reward_rep"], is_quest_reward=True)
                        return True
        return False


    # ---- Bounty System (TASK 16: MsgType 530-537) ----

    def _generate_daily_bounties(self):
        """Generate 3 random daily bounties from elite pool."""
        import random as _rng2
        pool = list(BOUNTY_ELITE_POOL)
        _rng2.shuffle(pool)
        bounties = []
        for i, elite in enumerate(pool[:3]):
            bounties.append({
                "bounty_id": 10000 + i,
                "type": "daily",
                "monster_id": elite["monster_id"],
                "name": elite["name"],
                "name_kr": elite["name_kr"],
                "level": elite["level"],
                "zone": elite["zone"],
                "gold": elite["gold"],
                "exp": elite["exp"],
                "bounty_token": elite["bounty_token"],
            })
        return bounties

    def _get_weekly_boss(self):
        """Get current weekly world boss (rotate by week number)."""
        import time as _t
        week_num = int(_t.time()) // (7 * 86400)
        boss = BOUNTY_WORLD_BOSSES[week_num % len(BOUNTY_WORLD_BOSSES)]
        return {
            "bounty_id": 20000,
            "type": "weekly",
            "monster_id": boss["boss_id"],
            "name": boss["name"],
            "name_kr": boss["name_kr"],
            "level": boss["level"],
            "zone": boss["zone"],
            "gold": boss["gold"],
            "exp": boss["exp"],
            "bounty_token": boss["bounty_token"],
            "min_party": boss["min_party"],
            "recommended_party": boss["recommended_party"],
        }

    def _check_bounty_reset(self, session):
        """Reset daily/weekly bounties if time has passed."""
        import time as _t
        today = _t.strftime("%Y-%m-%d")
        if session.bounty_reset_date != today:
            session.bounty_completed_today = []
            session.bounty_accepted = [b for b in session.bounty_accepted if b.get("type") == "weekly"]
            session.bounty_reset_date = today

        # Weekly reset: check if we're in a new week (Wednesday)
        import datetime
        now = datetime.datetime.now()
        # Find last Wednesday
        days_since_wed = (now.weekday() - 2) % 7
        last_wed = (now - datetime.timedelta(days=days_since_wed)).strftime("%Y-%m-%d")
        if session.bounty_weekly_reset_date != last_wed:
            session.bounty_completed_weekly = []
            session.bounty_accepted = [b for b in session.bounty_accepted if b.get("type") != "weekly"]
            session.bounty_weekly_reset_date = last_wed
            session.bounty_score_weekly = 0

    async def _on_bounty_list_req(self, session, payload: bytes):
        """BOUNTY_LIST_REQ(530) -> BOUNTY_LIST(531)
        Response: daily_count(u8) + [bounty_id(u16) + monster_id(u16) + level(u8) + zone_len(u8) + zone(str) +
                  gold(u32) + exp(u32) + token(u8) + accepted(u8) + completed(u8)] +
                  has_weekly(u8) + [weekly bounty data if has_weekly] +
                  accepted_count(u8)"""
        if not session.in_game:
            return

        level = session.stats.level if session.stats else 1
        if level < BOUNTY_MIN_LEVEL:
            # Not high enough level: send empty list
            self._send(session, MsgType.BOUNTY_LIST, struct.pack('<BBB', 0, 0, 0))
            return

        self._check_bounty_reset(session)

        # Generate daily bounties (deterministic per day using date seed)
        import time as _t
        import random as _rng3
        date_seed = int(_t.strftime("%Y%m%d"))
        _rng3.seed(date_seed)
        daily_bounties = self._generate_daily_bounties()
        _rng3.seed()  # restore random state

        # Build daily bounty data
        accepted_ids = {b["bounty_id"] for b in session.bounty_accepted}
        completed_ids = set(session.bounty_completed_today)

        data = struct.pack('<B', len(daily_bounties))
        for b in daily_bounties:
            zone_bytes = b["zone"].encode('utf-8')
            is_accepted = 1 if b["bounty_id"] in accepted_ids else 0
            is_completed = 1 if b["bounty_id"] in completed_ids else 0
            data += struct.pack('<HHB B', b["bounty_id"], b["monster_id"], b["level"], len(zone_bytes))
            data += zone_bytes
            data += struct.pack('<IIB BB', b["gold"], b["exp"], b["bounty_token"], is_accepted, is_completed)

        # Weekly bounty
        has_weekly = 1 if level >= BOUNTY_WEEKLY_MIN_LEVEL else 0
        data += struct.pack('<B', has_weekly)
        if has_weekly:
            wb = self._get_weekly_boss()
            zone_bytes = wb["zone"].encode('utf-8')
            is_accepted = 1 if wb["bounty_id"] in accepted_ids else 0
            is_completed = 1 if wb["bounty_id"] in set(session.bounty_completed_weekly) else 0
            data += struct.pack('<HHB B', wb["bounty_id"], wb["monster_id"], wb["level"], len(zone_bytes))
            data += zone_bytes
            data += struct.pack('<IIB BB BB', wb["gold"], wb["exp"], wb["bounty_token"],
                               is_accepted, is_completed,
                               wb["min_party"], wb["recommended_party"])

        # Accepted count
        data += struct.pack('<B', len(session.bounty_accepted))

        self._send(session, MsgType.BOUNTY_LIST, data)

    async def _on_bounty_accept(self, session, payload: bytes):
        """BOUNTY_ACCEPT(532) -> BOUNTY_ACCEPT_RESULT(533)
        Payload: bounty_id(u16)
        Result: 0=SUCCESS, 1=ALREADY_ACCEPTED, 2=MAX_LIMIT, 3=ALREADY_COMPLETED, 4=LEVEL_TOO_LOW, 5=NOT_FOUND"""
        if not session.in_game:
            return

        if len(payload) < 2:
            self._send(session, MsgType.BOUNTY_ACCEPT_RESULT, struct.pack('<B', 5))
            return

        bounty_id = struct.unpack_from('<H', payload, 0)[0]

        level = session.stats.level if session.stats else 1
        if level < BOUNTY_MIN_LEVEL:
            self._send(session, MsgType.BOUNTY_ACCEPT_RESULT, struct.pack('<B', 4))
            return

        self._check_bounty_reset(session)

        # Check if already accepted
        accepted_ids = {b["bounty_id"] for b in session.bounty_accepted}
        if bounty_id in accepted_ids:
            self._send(session, MsgType.BOUNTY_ACCEPT_RESULT, struct.pack('<B', 1))
            return

        # Check max limit
        if len(session.bounty_accepted) >= BOUNTY_MAX_ACCEPTED:
            self._send(session, MsgType.BOUNTY_ACCEPT_RESULT, struct.pack('<B', 2))
            return

        # Check if already completed
        if bounty_id in set(session.bounty_completed_today) or bounty_id in set(session.bounty_completed_weekly):
            self._send(session, MsgType.BOUNTY_ACCEPT_RESULT, struct.pack('<B', 3))
            return

        # Find bounty info
        import time as _t
        import random as _rng4
        date_seed = int(_t.strftime("%Y%m%d"))
        _rng4.seed(date_seed)
        daily_bounties = self._generate_daily_bounties()
        _rng4.seed()

        found = None
        for b in daily_bounties:
            if b["bounty_id"] == bounty_id:
                found = b
                break

        # Check weekly
        if not found and bounty_id == 20000:
            if level >= BOUNTY_WEEKLY_MIN_LEVEL:
                found = self._get_weekly_boss()

        if not found:
            self._send(session, MsgType.BOUNTY_ACCEPT_RESULT, struct.pack('<B', 5))
            return

        session.bounty_accepted.append({
            "bounty_id": bounty_id,
            "monster_id": found["monster_id"],
            "type": found["type"],
            "gold": found["gold"],
            "exp": found["exp"],
            "bounty_token": found["bounty_token"],
        })

        self._send(session, MsgType.BOUNTY_ACCEPT_RESULT, struct.pack('<BH', 0, bounty_id))

    async def _on_bounty_complete(self, session, payload: bytes):
        """BOUNTY_COMPLETE(534) -- server checks on monster kill.
        Also callable by client with payload: bounty_id(u16)
        Response: result(u8) + bounty_id(u16) + gold(u32) + exp(u32) + bounty_token(u8)
        Result: 0=SUCCESS, 1=NOT_ACCEPTED, 2=ALREADY_COMPLETED"""
        if not session.in_game:
            return

        if len(payload) < 2:
            return

        bounty_id = struct.unpack_from('<H', payload, 0)[0]

        self._check_bounty_reset(session)

        # Check if accepted
        accepted = None
        accepted_idx = -1
        for i, b in enumerate(session.bounty_accepted):
            if b["bounty_id"] == bounty_id:
                accepted = b
                accepted_idx = i
                break

        if not accepted:
            self._send(session, MsgType.BOUNTY_COMPLETE,
                           struct.pack('<BH', 1, bounty_id))
            return

        # Check if already completed
        if accepted["type"] == "daily" and bounty_id in set(session.bounty_completed_today):
            self._send(session, MsgType.BOUNTY_COMPLETE,
                           struct.pack('<BH', 2, bounty_id))
            return
        if accepted["type"] == "weekly" and bounty_id in set(session.bounty_completed_weekly):
            self._send(session, MsgType.BOUNTY_COMPLETE,
                           struct.pack('<BH', 2, bounty_id))
            return

        # Complete it!
        gold = accepted["gold"]
        exp = accepted["exp"]
        token = accepted["bounty_token"]

        # Apply rewards
        if session.stats:
            session.stats.add_exp(exp)
        session.gold = getattr(session, 'gold', 0) + gold
        session.bounty_tokens += token
        session.bounty_score_weekly += 1

        # Track completion
        if accepted["type"] == "daily":
            session.bounty_completed_today.append(bounty_id)
        else:
            session.bounty_completed_weekly.append(bounty_id)

        # Remove from accepted
        session.bounty_accepted.pop(accepted_idx)

        # Check daily completion bonus (all 3 daily done)
        import time as _t
        import random as _rng5
        date_seed = int(_t.strftime("%Y%m%d"))
        _rng5.seed(date_seed)
        daily_bounties = self._generate_daily_bounties()
        _rng5.seed()
        daily_ids = {b["bounty_id"] for b in daily_bounties}
        completed_daily = set(session.bounty_completed_today)
        if daily_ids.issubset(completed_daily):
            # All 3 daily bounties completed!
            bonus = BOUNTY_DAILY_COMPLETION_BONUS
            session.gold = getattr(session, 'gold', 0) + bonus["gold"]
            session.bounty_tokens += bonus["bounty_token"]
            gold += bonus["gold"]
            token += bonus["bounty_token"]

        self._send(session, MsgType.BOUNTY_COMPLETE,
                       struct.pack('<BHIIB', 0, bounty_id, gold, exp, token))

    async def _on_bounty_ranking_req(self, session, payload: bytes):
        """BOUNTY_RANKING_REQ(535) -> BOUNTY_RANKING(536)
        Response: rank_count(u8) + [rank(u8) + name_len(u8) + name(str) + score(u16)]
                  + my_rank(u8) + my_score(u16)"""
        if not session.in_game:
            return

        # Collect all players' weekly bounty scores
        rankings = []
        for s in self.sessions.values():
            if s.in_game and s.bounty_score_weekly > 0:
                char_name = getattr(s, 'char_name', 'Unknown')
                rankings.append({"name": char_name, "score": s.bounty_score_weekly, "account": s.account_id})

        # Sort by score descending, take top 10
        rankings.sort(key=lambda x: x["score"], reverse=True)
        top10 = rankings[:10]

        # Build response
        data = struct.pack('<B', len(top10))
        for i, r in enumerate(top10):
            name_bytes = r["name"].encode('utf-8')
            data += struct.pack('<B B', i + 1, len(name_bytes))
            data += name_bytes
            data += struct.pack('<H', r["score"])

        # My rank
        my_rank = 0
        for i, r in enumerate(rankings):
            if r["account"] == session.account_id:
                my_rank = i + 1
                break

        data += struct.pack('<BH', my_rank, session.bounty_score_weekly)

        self._send(session, MsgType.BOUNTY_RANKING, data)

    def _check_pvp_bounty(self, session):
        """Check if player should get PvP bounty after kill streak.
        Called when player kills another player in PvP zone.
        Returns tier info if new tier reached, None otherwise."""
        streak = session.pvp_kill_streak
        # Find highest applicable tier
        new_tier = 0
        for kill_threshold, tier_info in sorted(PVP_BOUNTY_TIERS.items()):
            if streak >= kill_threshold:
                new_tier = tier_info["tier"]

        if new_tier > session.pvp_bounty_tier:
            session.pvp_bounty_tier = new_tier
            # Get tier info
            for kill_threshold, tier_info in PVP_BOUNTY_TIERS.items():
                if tier_info["tier"] == new_tier:
                    return tier_info
        return None

    def _notify_pvp_bounty(self, session, tier_info):
        """PVP_BOUNTY_NOTIFY(537): broadcast bounty status.
        Payload: target_entity(u64) + tier(u8) + kill_streak(u16) + gold_reward(u32) + name_len(u8) + name(str)"""
        name_bytes = getattr(session, 'char_name', 'Unknown').encode('utf-8')
        data = struct.pack('<Q B H I B',
                          session.entity_id if hasattr(session, 'entity_id') else 0,
                          tier_info["tier"],
                          session.pvp_kill_streak,
                          tier_info["gold_reward"],
                          len(name_bytes))
        data += name_bytes

        # Broadcast to all players in same zone (or all)
        for s in self.sessions.values():
            if s.in_game:
                self._send(s, MsgType.PVP_BOUNTY_NOTIFY, data)


    # ---- Tripod & Scroll System (TASK 15: MsgType 520-524) ----

    async def _on_tripod_list_req(self, session: PlayerSession, payload: bytes):
        """TRIPOD_LIST_REQ(520): no payload needed.
        Returns all unlocked tripods + equipped selections for the character's class.
        Response format: skill_count(u8) + [skill_id(u16) + tier_count(u8) + [tier(u8) + unlocked_count(u8) + [option_idx(u8)] + equipped_idx(u8)]]"""
        if not session.in_game:
            return

        # Determine class from char_class
        class_name = session.char_class if hasattr(session, 'char_class') and session.char_class else "warrior"
        class_skills = CLASS_SKILLS.get(class_name, CLASS_SKILLS.get("warrior", []))

        parts = []
        skill_entries = []
        for skill_id in class_skills:
            if skill_id not in TRIPOD_TABLE:
                continue
            skill_tiers = TRIPOD_TABLE[skill_id]
            tier_data = []
            for tier in [1, 2, 3]:
                if tier not in skill_tiers:
                    continue
                # Check unlock level requirement
                req_level = TRIPOD_TIER_UNLOCK.get(tier, 99)
                if session.stats.level < req_level:
                    continue
                # Get unlocked options for this skill+tier
                unlocked = session.tripod_unlocked.get(skill_id, {}).get(tier, [])
                # Get equipped option
                equipped_id = session.tripod_equipped.get(skill_id, {}).get(tier, "")
                # Map option_id to index
                options = skill_tiers[tier]
                unlocked_indices = []
                equipped_idx = 0xFF  # none
                for oi, opt in enumerate(options):
                    if opt["id"] in unlocked:
                        unlocked_indices.append(oi)
                    if opt["id"] == equipped_id:
                        equipped_idx = oi
                tier_data.append((tier, unlocked_indices, equipped_idx))
            if tier_data:
                skill_entries.append((skill_id, tier_data))

        # Build response
        parts.append(struct.pack("<B", len(skill_entries)))
        for skill_id, tier_data in skill_entries:
            parts.append(struct.pack("<HB", skill_id, len(tier_data)))
            for tier, unlocked_indices, equipped_idx in tier_data:
                parts.append(struct.pack("<BB", tier, len(unlocked_indices)))
                for idx in unlocked_indices:
                    parts.append(struct.pack("<B", idx))
                parts.append(struct.pack("<B", equipped_idx))

        self._send(session, MsgType.TRIPOD_LIST, b"".join(parts))
        total_unlocked = sum(
            len(opts) for sk in session.tripod_unlocked.values() for opts in sk.values()
        )
        self.log(f"TripodList: {session.char_name} class={class_name} unlocked={total_unlocked}", "TRIPOD")

    async def _on_tripod_equip(self, session: PlayerSession, payload: bytes):
        """TRIPOD_EQUIP(522): skill_id(u16) + tier(u8) + option_idx(u8).
        Result codes: 0=ok, 1=not_in_game, 2=invalid_skill, 3=tier_locked, 4=not_unlocked, 5=need_lower_tier"""
        if not session.in_game:
            self._send(session, MsgType.TRIPOD_EQUIP_RESULT, struct.pack("<B", 1))
            return
        if len(payload) < 4:
            return
        skill_id = struct.unpack_from("<H", payload, 0)[0]
        tier = payload[2]
        option_idx = payload[3]

        # Validate skill exists in tripod table
        if skill_id not in TRIPOD_TABLE or tier not in TRIPOD_TABLE[skill_id]:
            self._send(session, MsgType.TRIPOD_EQUIP_RESULT, struct.pack("<B", 2))
            return

        # Check tier level requirement
        req_level = TRIPOD_TIER_UNLOCK.get(tier, 99)
        if session.stats.level < req_level:
            self._send(session, MsgType.TRIPOD_EQUIP_RESULT, struct.pack("<B", 3))
            return

        # Check that lower tier has an equipped option (tier 2 needs tier 1, tier 3 needs tier 2)
        if tier > 1:
            lower_tier = tier - 1
            if lower_tier in TRIPOD_TABLE.get(skill_id, {}):
                lower_equipped = session.tripod_equipped.get(skill_id, {}).get(lower_tier, "")
                if not lower_equipped:
                    self._send(session, MsgType.TRIPOD_EQUIP_RESULT, struct.pack("<B", 5))
                    return

        # Check option exists and is unlocked
        options = TRIPOD_TABLE[skill_id][tier]
        if option_idx >= len(options):
            self._send(session, MsgType.TRIPOD_EQUIP_RESULT, struct.pack("<B", 4))
            return
        option_id = options[option_idx]["id"]
        unlocked = session.tripod_unlocked.get(skill_id, {}).get(tier, [])
        if option_id not in unlocked:
            self._send(session, MsgType.TRIPOD_EQUIP_RESULT, struct.pack("<B", 4))
            return

        # Equip
        if skill_id not in session.tripod_equipped:
            session.tripod_equipped[skill_id] = {}
        session.tripod_equipped[skill_id][tier] = option_id

        self._send(session, MsgType.TRIPOD_EQUIP_RESULT, struct.pack("<B", 0))
        opt_name = options[option_idx]["name"]
        self.log(f"TripodEquip: {session.char_name} skill={skill_id} tier={tier} -> {opt_name}", "TRIPOD")

    async def _on_scroll_discover(self, session: PlayerSession, payload: bytes):
        """SCROLL_DISCOVER(524): scroll_item_slot(u8).
        Uses a scroll item from inventory to permanently unlock a tripod option.
        Response (broadcast to self): SCROLL_DISCOVER(524) with result.
        Format: result(u8) + skill_id(u16) + tier(u8) + option_idx(u8)
        Result: 0=ok, 1=not_in_game, 2=no_item, 3=already_unlocked, 4=wrong_class"""
        if not session.in_game:
            self._send(session, MsgType.SCROLL_DISCOVER, struct.pack("<B", 1))
            return
        if len(payload) < 1:
            return
        slot_idx = payload[0]

        # Validate inventory slot
        if slot_idx >= len(session.inventory) or session.inventory[slot_idx].item_id == 0:
            self._send(session, MsgType.SCROLL_DISCOVER, struct.pack("<B", 2))
            return

        # Scroll items have item_id in range 9000-9999 (convention)
        # Format: 9000 + skill_id * 10 + tier * 3 + option_idx
        # Simplified: just use item_id to lookup in a reverse map
        item_id = session.inventory[slot_idx].item_id
        scroll_info = self._resolve_scroll(item_id)
        if scroll_info is None:
            self._send(session, MsgType.SCROLL_DISCOVER, struct.pack("<B", 2))
            return

        skill_id, tier, option_idx, option_id = scroll_info

        # Check class restriction
        class_name = session.char_class if hasattr(session, 'char_class') and session.char_class else "warrior"
        skill_class = SKILL_CLASS_MAP.get(skill_id, "")
        if skill_class and skill_class != class_name:
            self._send(session, MsgType.SCROLL_DISCOVER, struct.pack("<B", 4))
            return

        # Check if already unlocked
        unlocked = session.tripod_unlocked.get(skill_id, {}).get(tier, [])
        if option_id in unlocked:
            self._send(session, MsgType.SCROLL_DISCOVER, struct.pack("<B", 3))
            return

        # Consume scroll item
        session.inventory[slot_idx].count -= 1
        if session.inventory[slot_idx].count <= 0:
            session.inventory[slot_idx].item_id = 0
            session.inventory[slot_idx].count = 0

        # Unlock tripod option
        if skill_id not in session.tripod_unlocked:
            session.tripod_unlocked[skill_id] = {}
        if tier not in session.tripod_unlocked[skill_id]:
            session.tripod_unlocked[skill_id][tier] = []
        session.tripod_unlocked[skill_id][tier].append(option_id)

        # Add to scroll collection (for codex)
        session.scroll_collection.add(option_id)

        # Send success response
        self._send(session, MsgType.SCROLL_DISCOVER, struct.pack("<BHBB", 0, skill_id, tier, option_idx))
        opt_name = TRIPOD_TABLE[skill_id][tier][option_idx]["name"]
        self.log(f"ScrollDiscover: {session.char_name} unlocked skill={skill_id} tier={tier} option={opt_name}", "TRIPOD")

    def _resolve_scroll(self, item_id):
        """Resolve a scroll item_id to (skill_id, tier, option_idx, option_id).
        Scroll item_id convention: base 9000.
        Encoding: 9000 + (skill_idx_in_table * 100) + (tier * 10) + option_idx
        where skill_idx_in_table is position in sorted TRIPOD_TABLE keys.
        Returns None if not a valid scroll."""
        if item_id < 9000 or item_id >= 9000 + len(TRIPOD_TABLE) * 100 + 40:
            return None
        offset = item_id - 9000
        # Decode: skill_pos * 100 + tier * 10 + option_idx
        skill_pos = offset // 100
        remainder = offset % 100
        tier = remainder // 10
        option_idx = remainder % 10

        sorted_skills = sorted(TRIPOD_TABLE.keys())
        if skill_pos >= len(sorted_skills):
            return None
        skill_id = sorted_skills[skill_pos]
        if tier < 1 or tier > 3:
            return None
        if tier not in TRIPOD_TABLE[skill_id]:
            return None
        options = TRIPOD_TABLE[skill_id][tier]
        if option_idx >= len(options):
            return None
        return (skill_id, tier, option_idx, options[option_idx]["id"])

    def _generate_scroll_item_id(self, skill_id, tier, option_idx):
        """Generate a scroll item_id from skill_id + tier + option_idx."""
        sorted_skills = sorted(TRIPOD_TABLE.keys())
        if skill_id not in sorted_skills:
            return None
        skill_pos = sorted_skills.index(skill_id)
        return 9000 + skill_pos * 100 + tier * 10 + option_idx

    def _try_scroll_drop(self, session, monster_type="normal"):
        """Roll for scroll drop on monster kill. Returns scroll item_id or None.
        Called from monster kill handler. Class-filtered."""
        import random as _rng
        drop_rate = SCROLL_DROP_RATES.get(monster_type, 0.0)
        if drop_rate <= 0 or _rng.random() > drop_rate:
            return None

        # Pick random skill for this player's class
        class_name = session.char_class if hasattr(session, 'char_class') and session.char_class else "warrior"
        skills = CLASS_SKILLS.get(class_name, [])
        if not skills:
            return None

        skill_id = _rng.choice(skills)
        if skill_id not in TRIPOD_TABLE:
            return None

        # Pick random tier (weighted: tier1=50%, tier2=35%, tier3=15%)
        tier_roll = _rng.random()
        if tier_roll < 0.50:
            tier = 1
        elif tier_roll < 0.85:
            tier = 2
        else:
            tier = 3

        if tier not in TRIPOD_TABLE[skill_id]:
            tier = 1  # fallback

        options = TRIPOD_TABLE[skill_id][tier]
        option_idx = _rng.randint(0, len(options) - 1)

        return self._generate_scroll_item_id(skill_id, tier, option_idx)


    # ---- Auction House System (TASK 3: MsgType 390-397) ----

    def _clean_expired_auctions(self):
        """Remove expired auctions, return items/gold via mail."""
        import time as _t
        now = _t.time()
        still_active = []
        for listing in self.auction_listings:
            if now >= listing["expires_at"]:
                # Expired: return item to seller via mail
                seller_acc = listing["seller_account"]
                mail_id = self.next_mail_id
                self.next_mail_id += 1
                mail = {
                    "id": mail_id,
                    "sender_name": "Auction House",
                    "sender_account": 0,
                    "subject": "Expired Listing",
                    "body": f"Your listing has expired.",
                    "gold": 0,
                    "item_id": listing["item_id"],
                    "item_count": listing["item_count"],
                    "read": False,
                    "claimed": False,
                    "sent_time": now,
                    "expires": now + 7 * 86400,
                }
                if seller_acc not in self.mails:
                    self.mails[seller_acc] = []
                self.mails[seller_acc].append(mail)
                # If there was a highest bidder, refund them
                if listing.get("bid_account", 0) > 0:
                    bid_acc = listing["bid_account"]
                    refund_mail_id = self.next_mail_id
                    self.next_mail_id += 1
                    refund_mail = {
                        "id": refund_mail_id,
                        "sender_name": "Auction House",
                        "sender_account": 0,
                        "subject": "Bid Refund",
                        "body": "Auction expired. Your bid has been refunded.",
                        "gold": listing["bid_price"],
                        "item_id": 0,
                        "item_count": 0,
                        "read": False,
                        "claimed": False,
                        "sent_time": now,
                        "expires": now + 7 * 86400,
                    }
                    if bid_acc not in self.mails:
                        self.mails[bid_acc] = []
                    self.mails[bid_acc].append(refund_mail)
                # Decrement seller listing count
                for s in self.sessions.values():
                    if s.account_id == seller_acc:
                        s.auction_listings = max(0, s.auction_listings - 1)
                self.log(f"Auction: expired listing #{listing['id']} ({listing['item_id']})", "ECON")
            else:
                still_active.append(listing)
        self.auction_listings = still_active

    async def _on_auction_list_req(self, session: PlayerSession, payload: bytes):
        """AUCTION_LIST_REQ(390): category(u8) + page(u8) + sort_by(u8).
        category: 0xFF=all, 0=weapon, 1=armor, 2=potion, 3=gem, 4=material, 5=etc
        sort_by: 0=price_asc, 1=price_desc, 2=newest
        Returns page of 20 items."""
        if not session.in_game:
            return
        if len(payload) < 3:
            return
        category = payload[0]
        page = payload[1]
        sort_by = payload[2]

        self._clean_expired_auctions()

        # Filter by category
        filtered = []
        for listing in self.auction_listings:
            if category != 0xFF and listing.get("category", 0xFF) != category:
                continue
            filtered.append(listing)

        # Sort
        if sort_by == 0:  # price asc
            filtered.sort(key=lambda x: x["buyout_price"])
        elif sort_by == 1:  # price desc
            filtered.sort(key=lambda x: x["buyout_price"], reverse=True)
        elif sort_by == 2:  # newest
            filtered.sort(key=lambda x: x["listed_at"], reverse=True)

        # Paginate (20 per page)
        page_size = 20
        total_count = len(filtered)
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        start = page * page_size
        end = min(start + page_size, total_count)
        page_items = filtered[start:end] if start < total_count else []

        # Build response: total_count(u16) + total_pages(u8) + current_page(u8) + item_count(u8) + items
        parts = [struct.pack("<HBBB", total_count, total_pages, page, len(page_items))]
        for item in page_items:
            # auction_id(u32) + item_id(u16) + item_count(u8) + buyout_price(u32) + bid_price(u32) + seller_name_len(u8) + seller_name
            seller_bytes = item["seller_name"].encode("utf-8")[:20]
            parts.append(struct.pack("<IHBIIB", item["id"], item["item_id"], item["item_count"],
                                     item["buyout_price"], item["bid_price"], len(seller_bytes)))
            parts.append(seller_bytes)

        self._send(session, MsgType.AUCTION_LIST, b"".join(parts))
        self.log(f"AuctionList: {session.char_name} cat={category} page={page} sort={sort_by} -> {len(page_items)} items", "ECON")

    async def _on_auction_register(self, session: PlayerSession, payload: bytes):
        """AUCTION_REGISTER(392): slot_index(u8) + count(u8) + buyout_price(u32) + category(u8).
        Result codes: 0=ok, 1=not_in_game, 2=no_item, 3=max_listings, 4=no_fee_gold, 5=invalid_price"""
        if not session.in_game:
            self._send(session, MsgType.AUCTION_REGISTER_RESULT, struct.pack("<BI", 1, 0))
            return
        if len(payload) < 7:
            return
        slot_idx = payload[0]
        count = payload[1]
        buyout_price = struct.unpack_from("<I", payload, 2)[0]
        category = payload[6]

        # Validate
        if slot_idx >= len(session.inventory) or session.inventory[slot_idx].item_id == 0:
            self._send(session, MsgType.AUCTION_REGISTER_RESULT, struct.pack("<BI", 2, 0))
            return
        if session.auction_listings >= AUCTION_MAX_LISTINGS:
            self._send(session, MsgType.AUCTION_REGISTER_RESULT, struct.pack("<BI", 3, 0))
            return
        if session.gold < AUCTION_LISTING_FEE:
            self._send(session, MsgType.AUCTION_REGISTER_RESULT, struct.pack("<BI", 4, 0))
            return
        if buyout_price < AUCTION_MIN_PRICE or buyout_price > AUCTION_MAX_PRICE:
            self._send(session, MsgType.AUCTION_REGISTER_RESULT, struct.pack("<BI", 5, 0))
            return

        # Deduct listing fee
        session.gold -= AUCTION_LISTING_FEE

        # Remove item from inventory
        item_id = session.inventory[slot_idx].item_id
        item_count = min(count, session.inventory[slot_idx].count)
        session.inventory[slot_idx].count -= item_count
        if session.inventory[slot_idx].count <= 0:
            session.inventory[slot_idx].item_id = 0
            session.inventory[slot_idx].count = 0

        import time as _t
        now = _t.time()
        auction_id = self.next_auction_id
        self.next_auction_id += 1

        listing = {
            "id": auction_id,
            "seller_account": session.account_id,
            "seller_name": session.char_name,
            "item_id": item_id,
            "item_count": item_count,
            "buyout_price": buyout_price,
            "bid_price": 0,
            "highest_bidder": 0,
            "highest_bidder_name": "",
            "bid_account": 0,
            "category": category,
            "listed_at": now,
            "expires_at": now + AUCTION_DURATION_HOURS * 3600,
        }
        self.auction_listings.append(listing)
        session.auction_listings += 1

        self._send(session, MsgType.AUCTION_REGISTER_RESULT, struct.pack("<BI", 0, auction_id))
        self.log(f"AuctionReg: {session.char_name} listed item={item_id}x{item_count} buyout={buyout_price}g (id={auction_id})", "ECON")

    async def _on_auction_buy(self, session: PlayerSession, payload: bytes):
        """AUCTION_BUY(394): auction_id(u32).
        Instant buyout. Result: 0=ok, 1=not_found, 2=self_buy, 3=no_gold"""
        if not session.in_game:
            return
        if len(payload) < 4:
            return
        auction_id = struct.unpack_from("<I", payload, 0)[0]

        self._clean_expired_auctions()

        # Find listing
        listing = None
        listing_idx = -1
        for i, l in enumerate(self.auction_listings):
            if l["id"] == auction_id:
                listing = l
                listing_idx = i
                break

        if listing is None:
            self._send(session, MsgType.AUCTION_BUY_RESULT, struct.pack("<BI", 1, 0))
            return

        # Can't buy own listing
        if listing["seller_account"] == session.account_id:
            self._send(session, MsgType.AUCTION_BUY_RESULT, struct.pack("<BI", 2, 0))
            return

        price = listing["buyout_price"]
        if session.gold < price:
            self._send(session, MsgType.AUCTION_BUY_RESULT, struct.pack("<BI", 3, 0))
            return

        # Deduct gold from buyer
        session.gold -= price

        # Give item to buyer
        for slot in session.inventory:
            if slot.item_id == 0:
                slot.item_id = listing["item_id"]
                slot.count = listing["item_count"]
                break

        # Calculate seller proceeds (5% tax)
        tax = int(price * AUCTION_TAX_RATE)
        proceeds = price - tax

        # Send gold to seller via mail
        import time as _t
        seller_acc = listing["seller_account"]
        mail_id = self.next_mail_id
        self.next_mail_id += 1
        mail = {
            "id": mail_id,
            "sender_name": "Auction House",
            "sender_account": 0,
            "subject": "Item Sold",
            "body": f"Your item sold for {price}g (tax: {tax}g).",
            "gold": proceeds,
            "item_id": 0,
            "item_count": 0,
            "read": False,
            "claimed": False,
            "sent_time": _t.time(),
            "expires": _t.time() + 7 * 86400,
        }
        if seller_acc not in self.mails:
            self.mails[seller_acc] = []
        self.mails[seller_acc].append(mail)

        # If there was a previous bidder, refund them
        if listing.get("bid_account", 0) > 0:
            bid_acc = listing["bid_account"]
            refund_id = self.next_mail_id
            self.next_mail_id += 1
            refund_mail = {
                "id": refund_id,
                "sender_name": "Auction House",
                "sender_account": 0,
                "subject": "Bid Refund",
                "body": "Item was bought out. Your bid has been refunded.",
                "gold": listing["bid_price"],
                "item_id": 0,
                "item_count": 0,
                "read": False,
                "claimed": False,
                "sent_time": _t.time(),
                "expires": _t.time() + 7 * 86400,
            }
            if bid_acc not in self.mails:
                self.mails[bid_acc] = []
            self.mails[bid_acc].append(refund_mail)

        # Remove listing
        self.auction_listings.pop(listing_idx)
        # Decrement seller listing count
        for s in self.sessions.values():
            if s.account_id == seller_acc:
                s.auction_listings = max(0, s.auction_listings - 1)

        self._send(session, MsgType.AUCTION_BUY_RESULT, struct.pack("<BI", 0, auction_id))
        self.log(f"AuctionBuy: {session.char_name} bought #{auction_id} for {price}g (tax={tax}g, seller gets {proceeds}g)", "ECON")

    async def _on_auction_bid(self, session: PlayerSession, payload: bytes):
        """AUCTION_BID(396): auction_id(u32) + bid_amount(u32).
        Result: 0=ok, 1=not_found, 2=self_bid, 3=no_gold, 4=bid_too_low"""
        if not session.in_game:
            return
        if len(payload) < 8:
            return
        auction_id = struct.unpack_from("<I", payload, 0)[0]
        bid_amount = struct.unpack_from("<I", payload, 4)[0]

        self._clean_expired_auctions()

        # Find listing
        listing = None
        for l in self.auction_listings:
            if l["id"] == auction_id:
                listing = l
                break

        if listing is None:
            self._send(session, MsgType.AUCTION_BID_RESULT, struct.pack("<BI", 1, 0))
            return

        if listing["seller_account"] == session.account_id:
            self._send(session, MsgType.AUCTION_BID_RESULT, struct.pack("<BI", 2, 0))
            return

        if session.gold < bid_amount:
            self._send(session, MsgType.AUCTION_BID_RESULT, struct.pack("<BI", 3, 0))
            return

        # Must be higher than current bid (or at least 1 if no bids)
        min_bid = max(listing["bid_price"] + 1, 1)
        if bid_amount < min_bid:
            self._send(session, MsgType.AUCTION_BID_RESULT, struct.pack("<BI", 4, 0))
            return

        # Can't bid more than buyout price
        if bid_amount >= listing["buyout_price"]:
            self._send(session, MsgType.AUCTION_BID_RESULT, struct.pack("<BI", 4, 0))
            return

        # Refund previous bidder
        import time as _t
        if listing.get("bid_account", 0) > 0 and listing["bid_account"] != session.account_id:
            old_bid_acc = listing["bid_account"]
            refund_id = self.next_mail_id
            self.next_mail_id += 1
            refund_mail = {
                "id": refund_id,
                "sender_name": "Auction House",
                "sender_account": 0,
                "subject": "Outbid Refund",
                "body": f"You were outbid. Your {listing['bid_price']}g has been refunded.",
                "gold": listing["bid_price"],
                "item_id": 0,
                "item_count": 0,
                "read": False,
                "claimed": False,
                "sent_time": _t.time(),
                "expires": _t.time() + 7 * 86400,
            }
            if old_bid_acc not in self.mails:
                self.mails[old_bid_acc] = []
            self.mails[old_bid_acc].append(refund_mail)

        # Deduct gold from new bidder
        session.gold -= bid_amount

        # Update listing
        listing["bid_price"] = bid_amount
        listing["bid_account"] = session.account_id
        listing["highest_bidder"] = session.entity_id
        listing["highest_bidder_name"] = session.char_name

        self._send(session, MsgType.AUCTION_BID_RESULT, struct.pack("<BI", 0, auction_id))
        self.log(f"AuctionBid: {session.char_name} bid {bid_amount}g on #{auction_id}", "ECON")

    def _check_daily_gold_cap(self, session, source, amount):
        """Check and apply daily gold cap. Returns actual gold to give."""
        import time as _t, datetime as _dt
        today = _dt.date.today().isoformat()
        if session.daily_gold_reset_date != today:
            session.daily_gold_earned = {"monster": 0, "dungeon": 0, "quest": 0, "total": 0}
            session.daily_gold_reset_date = today

        # Check source cap
        source_cap = DAILY_GOLD_CAPS.get(source, 999999999)
        total_cap = DAILY_GOLD_CAPS["total"]

        source_remaining = max(0, source_cap - session.daily_gold_earned.get(source, 0))
        total_remaining = max(0, total_cap - session.daily_gold_earned.get("total", 0))

        actual = min(amount, source_remaining, total_remaining)
        if actual > 0:
            session.daily_gold_earned[source] = session.daily_gold_earned.get(source, 0) + actual
            session.daily_gold_earned["total"] = session.daily_gold_earned.get("total", 0) + actual
        return actual


    # ---- Crafting/Gathering/Cooking/Enchanting System (TASK 2: MsgType 380-389) ----

    def _regen_energy(self, session):
        """Energy regen (1/min)"""
        import time as _t
        now = _t.time()
        if session.energy_last_regen == 0.0:
            session.energy_last_regen = now
            return
        elapsed_min = (now - session.energy_last_regen) / 60.0
        regen = int(elapsed_min * GATHER_ENERGY_REGEN)
        if regen > 0:
            session.energy = min(GATHER_ENERGY_MAX, session.energy + regen)
            session.energy_last_regen = now

    async def _on_craft_list_req(self, session: PlayerSession, payload: bytes):
        """CRAFT_LIST_REQ(380): category(u8). proficiency_level filtered recipe list."""
        if not session.in_game:
            return
        category_filter = payload[0] if len(payload) >= 1 else 0xFF
        cat_map = {0: "weapon", 1: "armor", 2: "potion", 3: "gem", 4: "material"}
        filter_cat = cat_map.get(category_filter, None)
        recipes = []
        for rid, recipe in CRAFTING_RECIPES.items():
            if recipe["proficiency_required"] > session.crafting_level:
                continue
            if filter_cat and recipe["category"] != filter_cat:
                continue
            recipes.append(recipe)
        parts = [struct.pack("<B", len(recipes))]
        for r in recipes:
            rid_bytes = r["id"].encode("utf-8")
            parts.append(struct.pack("<B", len(rid_bytes)))
            parts.append(rid_bytes)
            parts.append(struct.pack("<BHB", r["proficiency_required"],
                                     r["gold_cost"], int(r["success_rate"] * 100)))
            parts.append(struct.pack("<HB", r["result"]["item_id"], r["result"]["count"]))
            parts.append(struct.pack("<B", len(r["materials"])))
        resp = b"".join(parts)
        self._send(session, MsgType.CRAFT_LIST, resp)
        self.log(f"CraftList: {session.char_name} got {len(recipes)} recipes (cat={category_filter})", "GAME")

    async def _on_craft_execute(self, session: PlayerSession, payload: bytes):
        """CRAFT_EXECUTE(382): recipe_id_len(u8) + recipe_id(str). Execute crafting."""
        if not session.in_game or len(payload) < 2:
            return
        rid_len = payload[0]
        if len(payload) < 1 + rid_len:
            return
        recipe_id = payload[1:1 + rid_len].decode("utf-8")
        recipe = CRAFTING_RECIPES.get(recipe_id)
        if not recipe:
            self._send(session, MsgType.CRAFT_RESULT, struct.pack("<B", 1))
            return
        if session.crafting_level < recipe["proficiency_required"]:
            self._send(session, MsgType.CRAFT_RESULT, struct.pack("<B", 2))
            return
        if session.gold < recipe["gold_cost"]:
            self._send(session, MsgType.CRAFT_RESULT, struct.pack("<B", 3))
            return
        session.gold -= recipe["gold_cost"]
        import random as _rng
        if _rng.random() > recipe["success_rate"]:
            self.log(f"Craft: {session.char_name} FAIL {recipe_id}", "GAME")
            self._send(session, MsgType.CRAFT_RESULT, struct.pack("<B", 5))
            return
        result_item_id = recipe["result"]["item_id"]
        result_count = recipe["result"]["count"]
        for slot in session.inventory:
            if slot.item_id == 0:
                slot.item_id = result_item_id
                slot.count = result_count
                break
        has_bonus = 0
        if recipe.get("bonus_option_chance", 0) > 0 and _rng.random() < recipe["bonus_option_chance"]:
            has_bonus = 1
        session.crafting_exp += recipe["proficiency_required"] * 10
        while session.crafting_exp >= session.crafting_level * 100 and session.crafting_level < 50:
            session.crafting_exp -= session.crafting_level * 100
            session.crafting_level += 1
            self.log(f"Craft: {session.char_name} proficiency UP -> Lv{session.crafting_level}", "GAME")
        self.log(f"Craft: {session.char_name} SUCCESS {recipe_id} -> item={result_item_id}x{result_count} bonus={has_bonus}", "GAME")
        self._send(session, MsgType.CRAFT_RESULT, struct.pack("<BHBB", 0, result_item_id, result_count, has_bonus))

    async def _on_gather_start(self, session: PlayerSession, payload: bytes):
        """GATHER_START(384): gather_type(u8). Gather with energy cost + loot drop."""
        if not session.in_game or len(payload) < 1:
            return
        gather_type = payload[0]
        gtype = GATHER_TYPES.get(gather_type)
        if not gtype:
            self._send(session, MsgType.GATHER_RESULT, struct.pack("<BB", 1, 0))
            return
        self._regen_energy(session)
        if session.energy < GATHER_ENERGY_COST:
            self._send(session, MsgType.GATHER_RESULT, struct.pack("<BB", 2, 0))
            return
        session.energy -= GATHER_ENERGY_COST
        import random as _rng
        dropped_items = []
        for loot in gtype["loot"]:
            if _rng.random() < loot["chance"]:
                dropped_items.append(loot)
        if not dropped_items and gtype["loot"]:
            dropped_items.append(gtype["loot"][0])
        for item in dropped_items:
            for slot in session.inventory:
                if slot.item_id == 0:
                    slot.item_id = item["item_id"]
                    slot.count = 1
                    break
        session.gathering_exp += gtype["exp"]
        while session.gathering_exp >= session.gathering_level * 50 and session.gathering_level < 30:
            session.gathering_exp -= session.gathering_level * 50
            session.gathering_level += 1
            self.log(f"Gather: {session.char_name} level UP -> Lv{session.gathering_level}", "GAME")
        self.log(f"Gather: {session.char_name} type={gtype['name']} got {len(dropped_items)} items, energy={session.energy}", "GAME")
        parts = [struct.pack("<BBB", 0, session.energy, len(dropped_items))]
        for item in dropped_items:
            parts.append(struct.pack("<H", item["item_id"]))
        self._send(session, MsgType.GATHER_RESULT, b"".join(parts))

    async def _on_cook_execute(self, session: PlayerSession, payload: bytes):
        """COOK_EXECUTE(386): recipe_id_len(u8) + recipe_id(str). Cook + apply buff."""
        if not session.in_game or len(payload) < 2:
            return
        rid_len = payload[0]
        if len(payload) < 1 + rid_len:
            return
        recipe_id = payload[1:1 + rid_len].decode("utf-8")
        recipe = COOKING_RECIPES.get(recipe_id)
        if not recipe:
            self._send(session, MsgType.COOK_RESULT, struct.pack("<B", 1))
            return
        if session.cooking_level < recipe["proficiency_required"]:
            self._send(session, MsgType.COOK_RESULT, struct.pack("<B", 2))
            return
        import time as _t
        if session.food_buff and session.food_buff.get("expires", 0) > _t.time():
            self._send(session, MsgType.COOK_RESULT, struct.pack("<B", 3))
            return
        session.food_buff = {
            "recipe_id": recipe_id,
            "effect": recipe["effect"],
            "expires": _t.time() + recipe["duration"],
            "duration": recipe["duration"],
        }
        self.log(f"Cook: {session.char_name} made {recipe_id}, buff={recipe['effect']} for {recipe['duration']}s", "GAME")
        effects = recipe["effect"]
        self._send(session, MsgType.COOK_RESULT, struct.pack("<BHB", 0, recipe["duration"], len(effects)))

    async def _on_enchant_req(self, session: PlayerSession, payload: bytes):
        """ENCHANT_REQ(388): slot_index(u8) + element_id(u8) + target_level(u8). Weapon enchant."""
        if not session.in_game or len(payload) < 3:
            return
        slot_idx = payload[0]
        element_id = payload[1]
        target_level = payload[2]
        if slot_idx >= len(session.inventory):
            self._send(session, MsgType.ENCHANT_RESULT, struct.pack("<BB", 1, 0))
            return
        item = session.inventory[slot_idx]
        if item.item_id == 0:
            self._send(session, MsgType.ENCHANT_RESULT, struct.pack("<BB", 2, 0))
            return
        if element_id >= len(ENCHANT_ELEMENTS):
            self._send(session, MsgType.ENCHANT_RESULT, struct.pack("<BB", 3, 0))
            return
        level_data = ENCHANT_LEVELS.get(target_level)
        if not level_data:
            self._send(session, MsgType.ENCHANT_RESULT, struct.pack("<BB", 4, 0))
            return
        gold_cost = level_data["gold_cost"]
        existing = session.weapon_enchant.get(slot_idx)
        if existing:
            gold_cost = int(gold_cost * 1.5)
        if session.gold < gold_cost:
            self._send(session, MsgType.ENCHANT_RESULT, struct.pack("<BB", 5, 0))
            return
        session.gold -= gold_cost
        element_name = ENCHANT_ELEMENTS[element_id]
        session.weapon_enchant[slot_idx] = {
            "element": element_name,
            "element_id": element_id,
            "level": target_level,
            "damage_bonus": level_data["damage_bonus"],
        }
        self.log(f"Enchant: {session.char_name} slot={slot_idx} -> {element_name} Lv{target_level} (cost={gold_cost}g)", "GAME")
        self._send(session, MsgType.ENCHANT_RESULT, struct.pack("<BBBB", 0, element_id, target_level, int(level_data["damage_bonus"] * 100)))

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
