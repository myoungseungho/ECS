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
    {"id": 1, "name": "Goblin", "level": 5, "hp": 100, "atk": 15, "zone": 1, "x": 200, "y": 0, "z": 200},
    {"id": 1, "name": "Goblin", "level": 5, "hp": 100, "atk": 15, "zone": 1, "x": 300, "y": 0, "z": 150},
    {"id": 2, "name": "Wolf", "level": 8, "hp": 200, "atk": 25, "zone": 1, "x": 500, "y": 0, "z": 400},
    {"id": 2, "name": "Wolf", "level": 8, "hp": 200, "atk": 25, "zone": 1, "x": 600, "y": 0, "z": 300},
    {"id": 3, "name": "Orc", "level": 12, "hp": 350, "atk": 35, "zone": 2, "x": 100, "y": 0, "z": 100},
    {"id": 3, "name": "Orc", "level": 12, "hp": 350, "atk": 35, "zone": 2, "x": 300, "y": 0, "z": 200},
    {"id": 4, "name": "Bear", "level": 15, "hp": 500, "atk": 40, "zone": 2, "x": 800, "y": 0, "z": 600},
    {"id": 5, "name": "Skeleton", "level": 18, "hp": 300, "atk": 50, "zone": 3, "x": 200, "y": 0, "z": 200},
    {"id": 5, "name": "Skeleton", "level": 18, "hp": 300, "atk": 50, "zone": 3, "x": 400, "y": 0, "z": 400},
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
    1: {"min_x": 0, "max_x": 1000, "min_z": 0, "max_z": 1000},
    2: {"min_x": 0, "max_x": 2000, "min_z": 0, "max_z": 2000},
    3: {"min_x": 0, "max_x": 3000, "min_z": 0, "max_z": 3000},
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
            self._send(session, MsgType.LOGIN_RESULT, struct.pack('<BI', 0, 0))
            return

        name_len = payload[0]
        if len(payload) < 1 + name_len + 1:
            self._send(session, MsgType.LOGIN_RESULT, struct.pack('<BI', 0, 0))
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
        self._send(session, MsgType.LOGIN_RESULT, struct.pack('<BI', 1, session.account_id))

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
            self._send(session, MsgType.ENTER_GAME, struct.pack('<B', 0) + b'\x00' * 24)
            return

        char_id = struct.unpack('<I', payload[:4])[0]
        tmpl = next((c for c in CHARACTER_TEMPLATES if c["id"] == char_id), None)
        if not tmpl:
            self._send(session, MsgType.ENTER_GAME, struct.pack('<B', 0) + b'\x00' * 24)
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
            1, session.entity_id, session.zone_id,
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
            # 실패 응답
            other_name = target_name.encode('utf-8')[:32].ljust(32, b'\x00')
            self._send(session, MsgType.WHISPER_RESULT,
                        struct.pack('<BB', 0, 0) + other_name +
                        struct.pack('<B', 0))
            return

        # 발신자에게 (direction=0: sent)
        other_name = target_name.encode('utf-8')[:32].ljust(32, b'\x00')
        self._send(session, MsgType.WHISPER_RESULT,
                    struct.pack('<BB', 1, 0) + other_name +
                    struct.pack('<B', msg_len) + message.encode('utf-8')[:msg_len])

        # 수신자에게 (direction=1: received)
        sender_name = session.char_name.encode('utf-8')[:32].ljust(32, b'\x00')
        self._send(target_session, MsgType.WHISPER_RESULT,
                    struct.pack('<BB', 1, 1) + sender_name +
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
            self._send(session, MsgType.SHOP_RESULT,
                        struct.pack('<BBIHH', 0, 1, item_id, count, 0) + struct.pack('<I', session.gold))
            return

        item_data = next((i for i in shop["items"] if i["item_id"] == item_id), None)
        if not item_data:
            self._send(session, MsgType.SHOP_RESULT,
                        struct.pack('<BBIH', 0, 1, item_id, count) + struct.pack('<I', session.gold))
            return

        total_price = item_data["price"] * count
        if session.gold < total_price:
            self._send(session, MsgType.SHOP_RESULT,
                        struct.pack('<BBIH', 0, 1, item_id, count) + struct.pack('<I', session.gold))
            return

        slot = self._find_empty_slot(session)
        if slot < 0:
            self._send(session, MsgType.SHOP_RESULT,
                        struct.pack('<BBIH', 0, 1, item_id, count) + struct.pack('<I', session.gold))
            return

        session.gold -= total_price
        session.inventory[slot].item_id = item_id
        session.inventory[slot].count = count
        self._send(session, MsgType.SHOP_RESULT,
                    struct.pack('<BBIH', 1, 1, item_id, count) + struct.pack('<I', session.gold))
        self.log(f"ShopBuy: {session.char_name} bought {item_id}x{count} (-{total_price}g)", "GAME")

    async def _on_shop_sell(self, session: PlayerSession, payload: bytes):
        if not session.in_game or len(payload) < 3:
            return
        slot = payload[0]
        count = struct.unpack('<H', payload[1:3])[0]

        if slot >= len(session.inventory) or session.inventory[slot].item_id == 0:
            self._send(session, MsgType.SHOP_RESULT,
                        struct.pack('<BBIH', 0, 2, 0, 0) + struct.pack('<I', session.gold))
            return

        item_id = session.inventory[slot].item_id
        sell_count = min(count, session.inventory[slot].count)
        sell_price = 20 * sell_count  # 기본 판매가

        session.gold += sell_price
        session.inventory[slot].count -= sell_count
        if session.inventory[slot].count <= 0:
            session.inventory[slot] = InventorySlot()

        self._send(session, MsgType.SHOP_RESULT,
                    struct.pack('<BBIH', 1, 2, item_id, sell_count) + struct.pack('<I', session.gold))

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
    print(f"            Party, Inventory, Quest, Boss, AI")
    print("=" * 50)
    print()

    server = BridgeServer(port=args.port, verbose=args.verbose)

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
