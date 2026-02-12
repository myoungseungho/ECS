#!/usr/bin/env python3
"""
mock_server.py -- ECS MMORPG Mock Field Server (T004)

Unity 클라이언트 테스트를 위한 Python 모의 서버.
실제 C++ Field 서버 없이 전체 게임 플로우를 테스트할 수 있다:
  Login → CharSelect → EnterGame → Move → Stats → Combat → Respawn

protocol.yaml game_data 기반 계정/캐릭터/몬스터 데이터 내장.

사용법:
  python mock_server.py              # 포트 7777
  python mock_server.py --port 9999  # 커스텀 포트
"""

import argparse
import io
import os
import random
import socket
import struct
import sys
import threading
import time

# Windows 콘솔 UTF-8 출력 보장
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Constants (protocol.yaml header)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HEADER_SIZE = 6  # [length:u32][msg_type:u16]
MAX_PACKET = 8192
DEFAULT_PORT = 7777

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MsgType (protocol.yaml messages, sessions 1-13)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Msg:
    ECHO            = 1
    PING            = 2
    MOVE            = 10
    MOVE_BROADCAST  = 11
    POS_QUERY       = 12
    APPEAR          = 13
    DISAPPEAR       = 14
    CHANNEL_JOIN    = 20
    CHANNEL_INFO    = 22
    ZONE_ENTER      = 30
    ZONE_INFO       = 31
    LOGIN           = 60
    LOGIN_RESULT    = 61
    CHAR_LIST_REQ   = 62
    CHAR_LIST_RESP  = 63
    CHAR_SELECT     = 64
    ENTER_GAME      = 65
    STAT_QUERY      = 90
    STAT_SYNC       = 91
    ATTACK_REQ      = 100
    ATTACK_RESULT   = 101
    COMBAT_DIED     = 102
    RESPAWN_REQ     = 103
    RESPAWN_RESULT  = 104
    # Session 14: Monster
    MONSTER_SPAWN   = 110
    MONSTER_RESPAWN = 113
    # Session 16: Zone Transfer
    ZONE_TRANSFER_REQ    = 120
    ZONE_TRANSFER_RESULT = 121
    # Session 19: Skills
    SKILL_LIST_REQ  = 150
    SKILL_LIST_RESP = 151
    SKILL_USE       = 152
    SKILL_RESULT    = 153
    # Session 20: Party
    PARTY_CREATE    = 160
    PARTY_INVITE    = 161
    PARTY_ACCEPT    = 162
    PARTY_LEAVE     = 163
    PARTY_INFO      = 164
    PARTY_KICK      = 165
    # Session 21: Instance
    INSTANCE_CREATE       = 170
    INSTANCE_ENTER        = 171
    INSTANCE_LEAVE        = 172
    INSTANCE_LEAVE_RESULT = 173
    INSTANCE_INFO         = 174
    # Session 22: Matching
    MATCH_ENQUEUE   = 180
    MATCH_DEQUEUE   = 181
    MATCH_FOUND     = 182
    MATCH_ACCEPT    = 183
    MATCH_STATUS    = 184
    # Session 23: Inventory
    INVENTORY_REQ    = 190
    INVENTORY_RESP   = 191
    ITEM_ADD         = 192
    ITEM_ADD_RESULT  = 193
    ITEM_USE         = 194
    ITEM_USE_RESULT  = 195
    ITEM_EQUIP       = 196
    ITEM_UNEQUIP     = 197
    ITEM_EQUIP_RESULT = 198
    # Session 24: Buffs
    BUFF_LIST_REQ    = 200
    BUFF_LIST_RESP   = 201
    BUFF_APPLY_REQ   = 202
    BUFF_RESULT      = 203
    BUFF_REMOVE_REQ  = 204
    BUFF_REMOVE_RESP = 205
    # Session 28: Quests
    QUEST_LIST_REQ       = 230
    QUEST_LIST_RESP      = 231
    QUEST_ACCEPT         = 232
    QUEST_ACCEPT_RESULT  = 233
    QUEST_COMPLETE       = 235
    QUEST_COMPLETE_RESULT = 236

    _NAMES = {
        1: "ECHO", 2: "PING",
        10: "MOVE", 11: "MOVE_BROADCAST", 12: "POS_QUERY",
        13: "APPEAR", 14: "DISAPPEAR",
        20: "CHANNEL_JOIN", 22: "CHANNEL_INFO",
        30: "ZONE_ENTER", 31: "ZONE_INFO",
        60: "LOGIN", 61: "LOGIN_RESULT",
        62: "CHAR_LIST_REQ", 63: "CHAR_LIST_RESP",
        64: "CHAR_SELECT", 65: "ENTER_GAME",
        90: "STAT_QUERY", 91: "STAT_SYNC",
        100: "ATTACK_REQ", 101: "ATTACK_RESULT",
        102: "COMBAT_DIED", 103: "RESPAWN_REQ", 104: "RESPAWN_RESULT",
        110: "MONSTER_SPAWN", 113: "MONSTER_RESPAWN",
        120: "ZONE_TRANSFER_REQ", 121: "ZONE_TRANSFER_RESULT",
        150: "SKILL_LIST_REQ", 151: "SKILL_LIST_RESP",
        152: "SKILL_USE", 153: "SKILL_RESULT",
        160: "PARTY_CREATE", 161: "PARTY_INVITE", 162: "PARTY_ACCEPT",
        163: "PARTY_LEAVE", 164: "PARTY_INFO", 165: "PARTY_KICK",
        170: "INSTANCE_CREATE", 171: "INSTANCE_ENTER",
        172: "INSTANCE_LEAVE", 173: "INSTANCE_LEAVE_RESULT", 174: "INSTANCE_INFO",
        180: "MATCH_ENQUEUE", 181: "MATCH_DEQUEUE",
        182: "MATCH_FOUND", 183: "MATCH_ACCEPT", 184: "MATCH_STATUS",
        190: "INVENTORY_REQ", 191: "INVENTORY_RESP",
        192: "ITEM_ADD", 193: "ITEM_ADD_RESULT",
        194: "ITEM_USE", 195: "ITEM_USE_RESULT",
        196: "ITEM_EQUIP", 197: "ITEM_UNEQUIP", 198: "ITEM_EQUIP_RESULT",
        200: "BUFF_LIST_REQ", 201: "BUFF_LIST_RESP",
        202: "BUFF_APPLY_REQ", 203: "BUFF_RESULT",
        204: "BUFF_REMOVE_REQ", 205: "BUFF_REMOVE_RESP",
        230: "QUEST_LIST_REQ", 231: "QUEST_LIST_RESP",
        232: "QUEST_ACCEPT", 233: "QUEST_ACCEPT_RESULT",
        235: "QUEST_COMPLETE", 236: "QUEST_COMPLETE_RESULT",
    }

    @classmethod
    def name(cls, msg_id):
        return cls._NAMES.get(msg_id, f"UNKNOWN({msg_id})")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Game Data (protocol.yaml game_data)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ACCOUNTS = {
    "hero": {"id": 1, "password": "pass123"},
    "mage": {"id": 2, "password": "magic456"},
    "test": {"id": 3, "password": "test"},  # 편의용 테스트 계정
}

# account_id -> character list
CHARACTERS = {
    1: [
        {"id": 100, "name": "Warrior1", "level": 10, "job": 1},
        {"id": 101, "name": "Mage1", "level": 5, "job": 2},
    ],
    2: [
        {"id": 200, "name": "Archer2", "level": 8, "job": 3},
    ],
    3: [
        {"id": 300, "name": "TestChar", "level": 1, "job": 0},
    ],
}

# char_id -> base stats
CHAR_STATS = {
    100: {"level": 10, "hp": 500, "max_hp": 500, "mp": 200, "max_mp": 200,
          "atk": 50, "def": 30, "exp": 0, "exp_next": 1000},
    101: {"level": 5,  "hp": 250, "max_hp": 250, "mp": 400, "max_mp": 400,
          "atk": 80, "def": 15, "exp": 0, "exp_next": 500},
    200: {"level": 8,  "hp": 400, "max_hp": 400, "mp": 300, "max_mp": 300,
          "atk": 60, "def": 20, "exp": 0, "exp_next": 800},
    300: {"level": 1,  "hp": 100, "max_hp": 100, "mp": 50,  "max_mp": 50,
          "atk": 10, "def": 5,  "exp": 0, "exp_next": 100},
}

SPAWN_POS = (500.0, 0.0, 500.0)
DEFAULT_ZONE = 1

# 몬스터 (NPC) — 싱글 플레이어 전투 테스트용
MONSTERS = [
    {"template_id": 1001, "name": "Slime",  "level": 1,  "hp": 50,   "max_hp": 50,
     "atk": 5,  "def": 2,  "pos": (510.0, 0.0, 510.0), "zone": 1},
    {"template_id": 1002, "name": "Wolf",   "level": 3,  "hp": 120,  "max_hp": 120,
     "atk": 15, "def": 8,  "pos": (520.0, 0.0, 520.0), "zone": 1},
]

# ━━━ Skills (session 19) ━━━
SKILLS = [
    {"id": 1, "name": "Slash",      "cd_ms": 2000,  "dmg": 30,  "mp": 10, "range": 50,  "type": 0},
    {"id": 2, "name": "Fireball",   "cd_ms": 5000,  "dmg": 80,  "mp": 40, "range": 100, "type": 1},
    {"id": 3, "name": "Heal",       "cd_ms": 8000,  "dmg": 0,   "mp": 60, "range": 0,   "type": 2},
    {"id": 4, "name": "PowerStrike","cd_ms": 10000, "dmg": 150, "mp": 80, "range": 50,  "type": 0},
]

# ━━━ Items (session 23) ━━━
STARTER_ITEMS = [
    {"slot": 0, "item_id": 1001, "count": 5,  "equipped": 0},  # HP Potion x5
    {"slot": 1, "item_id": 1002, "count": 3,  "equipped": 0},  # MP Potion x3
    {"slot": 2, "item_id": 2001, "count": 1,  "equipped": 1},  # Iron Sword (equipped)
]

# ━━━ Buffs (session 24) ━━━
BUFF_TEMPLATES = {
    1: {"name": "ATK Up",   "duration_ms": 30000, "stacks": 1},
    2: {"name": "DEF Up",   "duration_ms": 30000, "stacks": 1},
    3: {"name": "Haste",    "duration_ms": 15000, "stacks": 1},
    4: {"name": "Regen",    "duration_ms": 60000, "stacks": 3},
}

# ━━━ Quests (session 28) ━━━
QUEST_TEMPLATES = {
    1: {"name": "Slime Hunt",     "target": 5,  "reward_exp": 100, "reward_item_id": 1001, "reward_count": 3},
    2: {"name": "Wolf Extermination", "target": 3,  "reward_exp": 300, "reward_item_id": 1003, "reward_count": 1},
    3: {"name": "Exploration",    "target": 1,  "reward_exp": 50,  "reward_item_id": 0,    "reward_count": 0},
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Packet Building Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_packet(msg_type, payload=b""):
    """[length:u32 LE][msg_type:u16 LE][payload]"""
    total = HEADER_SIZE + len(payload)
    return struct.pack("<IH", total, msg_type) + payload


def build_login_result(result, account_id):
    """LOGIN_RESULT(61): result(u8) account_id(u32) = 5B"""
    return build_packet(Msg.LOGIN_RESULT, struct.pack("<BI", result, account_id))


def build_char_list_resp(chars):
    """CHAR_LIST_RESP(63): count(u8) + {id(u32) name(32B) level(u32) job(u32)}*N"""
    payload = struct.pack("<B", len(chars))
    for c in chars:
        name_bytes = c["name"].encode("utf-8")[:32]
        name_fixed = name_bytes + b"\x00" * (32 - len(name_bytes))
        payload += struct.pack("<I", c["id"]) + name_fixed + struct.pack("<II", c["level"], c["job"])
    return build_packet(Msg.CHAR_LIST_RESP, payload)


def build_enter_game(result, entity_id, zone, x, y, z):
    """ENTER_GAME(65): result(u8) entity(u64) zone(u32) x(f32) y(f32) z(f32) = 25B"""
    return build_packet(Msg.ENTER_GAME, struct.pack("<BQIfff", result, entity_id, zone, x, y, z))


def build_stat_sync(stats):
    """STAT_SYNC(91): 9 x i32 = 36B"""
    return build_packet(Msg.STAT_SYNC, struct.pack("<iiiiiiiii",
        stats["level"], stats["hp"], stats["max_hp"],
        stats["mp"], stats["max_mp"],
        stats["atk"], stats["def"],
        stats["exp"], stats["exp_next"]))


def build_appear(entity_id, x, y, z):
    """APPEAR(13): entity(u64) x(f32) y(f32) z(f32) = 20B"""
    return build_packet(Msg.APPEAR, struct.pack("<Qfff", entity_id, x, y, z))


def build_disappear(entity_id):
    """DISAPPEAR(14): entity(u64) = 8B"""
    return build_packet(Msg.DISAPPEAR, struct.pack("<Q", entity_id))


def build_move_broadcast(entity_id, x, y, z):
    """MOVE_BROADCAST(11): entity(u64) x(f32) y(f32) z(f32) = 20B"""
    return build_packet(Msg.MOVE_BROADCAST, struct.pack("<Qfff", entity_id, x, y, z))


def build_channel_info(channel_id):
    """CHANNEL_INFO(22): channel_id(i32) = 4B"""
    return build_packet(Msg.CHANNEL_INFO, struct.pack("<i", channel_id))


def build_zone_info(zone_id):
    """ZONE_INFO(31): zone_id(i32) = 4B"""
    return build_packet(Msg.ZONE_INFO, struct.pack("<i", zone_id))


def build_attack_result(result, attacker, target, damage, target_hp, target_max_hp):
    """ATTACK_RESULT(101): result(u8) attacker(u64) target(u64) damage(i32) target_hp(i32) target_max_hp(i32) = 29B"""
    return build_packet(Msg.ATTACK_RESULT,
        struct.pack("<BQQiii", result, attacker, target, damage, target_hp, target_max_hp))


def build_combat_died(dead_entity, killer_entity):
    """COMBAT_DIED(102): dead_entity(u64) killer_entity(u64) = 16B"""
    return build_packet(Msg.COMBAT_DIED, struct.pack("<QQ", dead_entity, killer_entity))


def build_respawn_result(result, hp, mp, x, y, z):
    """RESPAWN_RESULT(104): result(u8) hp(i32) mp(i32) x(f32) y(f32) z(f32) = 21B"""
    return build_packet(Msg.RESPAWN_RESULT, struct.pack("<Biifff", result, hp, mp, x, y, z))


def build_monster_spawn(entity_id, monster_id, level, hp, max_hp, x, y, z):
    """MONSTER_SPAWN(110): entity(u64) monster_id(u32) level(u32) hp(i32) max_hp(i32) x(f32) y(f32) z(f32) = 36B"""
    return build_packet(Msg.MONSTER_SPAWN,
        struct.pack("<QIIiifff", entity_id, monster_id, level, hp, max_hp, x, y, z))


def build_monster_respawn(entity_id, hp, max_hp, x, y, z):
    """MONSTER_RESPAWN(113): entity(u64) hp(i32) max_hp(i32) x(f32) y(f32) z(f32) = 28B"""
    return build_packet(Msg.MONSTER_RESPAWN,
        struct.pack("<Qiifff", entity_id, hp, max_hp, x, y, z))


def build_zone_transfer_result(result, zone_id, x, y, z):
    """ZONE_TRANSFER_RESULT(121): result(u8) zone_id(u32) x(f32) y(f32) z(f32) = 17B"""
    return build_packet(Msg.ZONE_TRANSFER_RESULT, struct.pack("<BIfff", result, zone_id, x, y, z))


def build_skill_list_resp(skills):
    """SKILL_LIST_RESP(151): count(u8) + {id(u32) name(16B) cd_ms(u32) dmg(u32) mp(u32) range(u32) type(u8)}*N"""
    payload = struct.pack("<B", len(skills))
    for s in skills:
        name_bytes = s["name"].encode("utf-8")[:16]
        name_fixed = name_bytes + b"\x00" * (16 - len(name_bytes))
        payload += struct.pack("<I", s["id"]) + name_fixed + struct.pack("<IIIIB", s["cd_ms"], s["dmg"], s["mp"], s["range"], s["type"])
    return build_packet(Msg.SKILL_LIST_RESP, payload)


def build_skill_result(result, skill_id, caster, target, damage, target_hp):
    """SKILL_RESULT(153): result(u8) skill_id(u32) caster(u64) target(u64) damage(i32) target_hp(i32) = 29B"""
    return build_packet(Msg.SKILL_RESULT,
        struct.pack("<BIQQii", result, skill_id, caster, target, damage, target_hp))


def build_party_info(result, party_id, leader, members):
    """PARTY_INFO(164): result(u8) party_id(u32) leader(u64) count(u8) + {entity(u64) level(u32)}*N"""
    payload = struct.pack("<BIQ", result, party_id, leader)
    payload += struct.pack("<B", len(members))
    for m in members:
        payload += struct.pack("<QI", m["entity"], m["level"])
    return build_packet(Msg.PARTY_INFO, payload)


def build_instance_enter(result, instance_id, dungeon_type):
    """INSTANCE_ENTER(171): result(u8) instance_id(u32) dungeon_type(u32) = 9B"""
    return build_packet(Msg.INSTANCE_ENTER, struct.pack("<BII", result, instance_id, dungeon_type))


def build_instance_leave_result(result, zone_id, x, y, z):
    """INSTANCE_LEAVE_RESULT(173): result(u8) zone_id(u32) x(f32) y(f32) z(f32) = 17B"""
    return build_packet(Msg.INSTANCE_LEAVE_RESULT, struct.pack("<BIfff", result, zone_id, x, y, z))


def build_match_status(status, queue_position):
    """MATCH_STATUS(184): status(u8) queue_position(u32) = 5B"""
    return build_packet(Msg.MATCH_STATUS, struct.pack("<BI", status, queue_position))


def build_inventory_resp(items):
    """INVENTORY_RESP(191): count(u8) + {slot(u8) item_id(u32) count(u16) equipped(u8)}*N = 8B/entry"""
    payload = struct.pack("<B", len(items))
    for it in items:
        payload += struct.pack("<BIHB", it["slot"], it["item_id"], it["count"], it["equipped"])
    return build_packet(Msg.INVENTORY_RESP, payload)


def build_item_add_result(result, slot, item_id, count):
    """ITEM_ADD_RESULT(193): result(u8) slot(u8) item_id(u32) count(u16) = 8B"""
    return build_packet(Msg.ITEM_ADD_RESULT, struct.pack("<BBIH", result, slot, item_id, count))


def build_item_use_result(result, slot, item_id):
    """ITEM_USE_RESULT(195): result(u8) slot(u8) item_id(u32) = 6B"""
    return build_packet(Msg.ITEM_USE_RESULT, struct.pack("<BBI", result, slot, item_id))


def build_item_equip_result(result, slot, item_id, equipped):
    """ITEM_EQUIP_RESULT(198): result(u8) slot(u8) item_id(u32) equipped(u8) = 7B"""
    return build_packet(Msg.ITEM_EQUIP_RESULT, struct.pack("<BBIB", result, slot, item_id, equipped))


def build_buff_list_resp(buffs):
    """BUFF_LIST_RESP(201): count(u8) + {buff_id(u32) remaining_ms(u32) stacks(u8)}*N = 9B/entry"""
    payload = struct.pack("<B", len(buffs))
    for b in buffs:
        payload += struct.pack("<IIB", b["buff_id"], b["remaining_ms"], b["stacks"])
    return build_packet(Msg.BUFF_LIST_RESP, payload)


def build_buff_result(result, buff_id, stacks, duration_ms):
    """BUFF_RESULT(203): result(u8) buff_id(u32) stacks(u8) duration_ms(u32) = 10B"""
    return build_packet(Msg.BUFF_RESULT, struct.pack("<BIBI", result, buff_id, stacks, duration_ms))


def build_buff_remove_resp(result, buff_id):
    """BUFF_REMOVE_RESP(205): result(u8) buff_id(u32) = 5B"""
    return build_packet(Msg.BUFF_REMOVE_RESP, struct.pack("<BI", result, buff_id))


def build_quest_list_resp(quests):
    """QUEST_LIST_RESP(231): count(u8) + {quest_id(u32) state(u8) progress(u32) target(u32)}*N = 13B/entry"""
    payload = struct.pack("<B", len(quests))
    for q in quests:
        payload += struct.pack("<IBII", q["quest_id"], q["state"], q["progress"], q["target"])
    return build_packet(Msg.QUEST_LIST_RESP, payload)


def build_quest_accept_result(result, quest_id):
    """QUEST_ACCEPT_RESULT(233): result(u8) quest_id(u32) = 5B"""
    return build_packet(Msg.QUEST_ACCEPT_RESULT, struct.pack("<BI", result, quest_id))


def build_quest_complete_result(result, quest_id, reward_exp, reward_item_id, reward_item_count):
    """QUEST_COMPLETE_RESULT(236): result(u8) quest_id(u32) reward_exp(u32) reward_item_id(u32) reward_item_count(u16) = 15B"""
    return build_packet(Msg.QUEST_COMPLETE_RESULT,
        struct.pack("<BIIIH", result, quest_id, reward_exp, reward_item_id, reward_item_count))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Monster Entity (NPC)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MonsterEntity:
    """서버 메모리 내 몬스터. 플레이어가 공격/킬 할 수 있다."""

    def __init__(self, entity_id, template):
        self.entity_id = entity_id
        self.template_id = template["template_id"]
        self.name = template["name"]
        self.level = template["level"]
        self.hp = template["hp"]
        self.max_hp = template["max_hp"]
        self.atk = template["atk"]
        self.defense = template["def"]
        self.pos = template["pos"]
        self.zone = template["zone"]
        self.alive = True
        self.respawn_timer = None

    def take_damage(self, damage):
        self.hp = max(0, self.hp - damage)
        if self.hp <= 0:
            self.alive = False
        return self.hp

    def respawn(self):
        self.hp = self.max_hp
        self.alive = True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# World State (thread-safe)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class World:
    """전역 월드 상태. 모든 ClientSession이 공유."""

    def __init__(self):
        self.lock = threading.Lock()
        self._next_entity_id = 1000
        self.players = {}    # entity_id -> ClientSession
        self.monsters = {}   # entity_id -> MonsterEntity

    def alloc_entity_id(self):
        with self.lock:
            eid = self._next_entity_id
            self._next_entity_id += 1
            return eid

    def register_player(self, session):
        with self.lock:
            self.players[session.entity_id] = session

    def unregister_player(self, entity_id):
        with self.lock:
            self.players.pop(entity_id, None)

    def spawn_monsters(self):
        """초기 몬스터 스폰."""
        for tmpl in MONSTERS:
            eid = self.alloc_entity_id()
            m = MonsterEntity(eid, tmpl)
            self.monsters[eid] = m
            print(f"  Monster spawned: {m.name} (entity={eid}, hp={m.hp})")

    def get_target(self, entity_id):
        """entity_id에 해당하는 플레이어 또는 몬스터 반환."""
        with self.lock:
            if entity_id in self.players:
                return ("player", self.players[entity_id])
            if entity_id in self.monsters:
                return ("monster", self.monsters[entity_id])
        return (None, None)

    def broadcast_zone(self, zone, data, exclude_eid=None):
        """같은 존 내 모든 플레이어에게 패킷 전송."""
        with self.lock:
            targets = [
                s for eid, s in self.players.items()
                if s.zone == zone and eid != exclude_eid
            ]
        for s in targets:
            s.send_safe(data)

    def schedule_monster_respawn(self, monster, delay=5.0):
        """delay초 후 몬스터 리스폰."""
        def _respawn():
            time.sleep(delay)
            monster.respawn()
            print(f"  Monster respawned: {monster.name} (entity={monster.entity_id})")
            # MONSTER_RESPAWN to all in zone
            pkt = build_monster_respawn(
                monster.entity_id, monster.hp, monster.max_hp, *monster.pos)
            self.broadcast_zone(monster.zone, pkt)
        t = threading.Thread(target=_respawn, daemon=True)
        t.start()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Client Session (per-connection)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ClientSession:
    """클라이언트 1개 연결에 대한 세션."""

    def __init__(self, sock, addr, world):
        self.sock = sock
        self.addr = addr
        self.world = world
        self.account_id = None
        self.char_id = None
        self.entity_id = None
        self.stats = None
        self.pos = SPAWN_POS
        self.zone = DEFAULT_ZONE
        self.channel = 0
        self.alive = True
        self.running = True
        self._send_lock = threading.Lock()
        # Session 19-28 per-player state
        self.inventory = []        # list of item dicts
        self.buffs = {}            # buff_id -> {buff_id, remaining_ms, stacks}
        self.quests = {}           # quest_id -> {quest_id, state, progress, target}
        self.party_id = 0
        self.in_instance = False
        self.instance_id = 0
        self.in_queue = False

    def send_safe(self, data):
        """Thread-safe send."""
        with self._send_lock:
            try:
                self.sock.sendall(data)
            except Exception:
                self.running = False

    def run(self):
        """메인 수신 루프 (별도 스레드에서 실행)."""
        buf = b""
        while self.running:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                buf += chunk

                # 패킷 프레이밍: [length:u32][type:u16][payload]
                while len(buf) >= HEADER_SIZE:
                    pkt_len = struct.unpack_from("<I", buf, 0)[0]
                    if pkt_len > MAX_PACKET:
                        print(f"[{self.addr}] Packet too large ({pkt_len}), disconnecting")
                        self.running = False
                        break
                    if len(buf) < pkt_len:
                        break  # 아직 전체 패킷 미수신
                    msg_type = struct.unpack_from("<H", buf, 4)[0]
                    payload = buf[HEADER_SIZE:pkt_len]
                    buf = buf[pkt_len:]
                    self._dispatch(msg_type, payload)

            except ConnectionResetError:
                break
            except ConnectionAbortedError:
                break
            except Exception as e:
                print(f"[{self.addr}] Error: {e}")
                break

        self._cleanup()

    def _cleanup(self):
        self.running = False
        if self.entity_id:
            self.world.unregister_player(self.entity_id)
            pkt = build_disappear(self.entity_id)
            self.world.broadcast_zone(self.zone, pkt)
        try:
            self.sock.close()
        except Exception:
            pass
        print(f"[{self.addr}] Disconnected (entity={self.entity_id})")

    def _dispatch(self, msg_type, payload):
        name = Msg.name(msg_type)

        if msg_type == Msg.ECHO:
            self.send_safe(build_packet(Msg.ECHO, payload))

        elif msg_type == Msg.PING:
            self.send_safe(build_packet(Msg.PING))

        elif msg_type == Msg.LOGIN:
            self._on_login(payload)

        elif msg_type == Msg.CHAR_LIST_REQ:
            self._on_char_list()

        elif msg_type == Msg.CHAR_SELECT:
            self._on_char_select(payload)

        elif msg_type == Msg.CHANNEL_JOIN:
            ch = struct.unpack_from("<i", payload, 0)[0]
            self.channel = ch
            self.send_safe(build_channel_info(ch))
            print(f"[{self.addr}] ChannelJoin: {ch}")

        elif msg_type == Msg.ZONE_ENTER:
            z = struct.unpack_from("<i", payload, 0)[0]
            self.zone = z
            self.send_safe(build_zone_info(z))
            print(f"[{self.addr}] ZoneEnter: {z}")

        elif msg_type == Msg.MOVE:
            self._on_move(payload)

        elif msg_type == Msg.STAT_QUERY:
            if self.stats:
                self.send_safe(build_stat_sync(self.stats))

        elif msg_type == Msg.ATTACK_REQ:
            self._on_attack(payload)

        elif msg_type == Msg.RESPAWN_REQ:
            self._on_respawn()

        # Session 16: Zone Transfer
        elif msg_type == Msg.ZONE_TRANSFER_REQ:
            self._on_zone_transfer(payload)

        # Session 19: Skills
        elif msg_type == Msg.SKILL_LIST_REQ:
            self.send_safe(build_skill_list_resp(SKILLS))
        elif msg_type == Msg.SKILL_USE:
            self._on_skill_use(payload)

        # Session 20: Party
        elif msg_type == Msg.PARTY_CREATE:
            self._on_party_create()
        elif msg_type == Msg.PARTY_LEAVE:
            self._on_party_leave()
        elif msg_type in (Msg.PARTY_INVITE, Msg.PARTY_ACCEPT, Msg.PARTY_KICK):
            # Simplified: just send current party info
            self._send_party_info()

        # Session 21: Instance
        elif msg_type == Msg.INSTANCE_CREATE:
            self._on_instance_create(payload)
        elif msg_type == Msg.INSTANCE_LEAVE:
            self._on_instance_leave()

        # Session 22: Matching
        elif msg_type == Msg.MATCH_ENQUEUE:
            self.in_queue = True
            self.send_safe(build_match_status(1, 1))  # status=1(queued), pos=1
            print(f"[{self.addr}] MatchEnqueue")
        elif msg_type == Msg.MATCH_DEQUEUE:
            self.in_queue = False
            self.send_safe(build_match_status(0, 0))  # status=0(idle)
            print(f"[{self.addr}] MatchDequeue")
        elif msg_type == Msg.MATCH_ACCEPT:
            print(f"[{self.addr}] MatchAccept")

        # Session 23: Inventory
        elif msg_type == Msg.INVENTORY_REQ:
            self._on_inventory_req()
        elif msg_type == Msg.ITEM_ADD:
            self._on_item_add(payload)
        elif msg_type == Msg.ITEM_USE:
            self._on_item_use(payload)
        elif msg_type == Msg.ITEM_EQUIP:
            self._on_item_equip(payload, equip=True)
        elif msg_type == Msg.ITEM_UNEQUIP:
            self._on_item_equip(payload, equip=False)

        # Session 24: Buffs
        elif msg_type == Msg.BUFF_LIST_REQ:
            self._on_buff_list_req()
        elif msg_type == Msg.BUFF_APPLY_REQ:
            self._on_buff_apply(payload)
        elif msg_type == Msg.BUFF_REMOVE_REQ:
            self._on_buff_remove(payload)

        # Session 28: Quests
        elif msg_type == Msg.QUEST_LIST_REQ:
            self._on_quest_list_req()
        elif msg_type == Msg.QUEST_ACCEPT:
            self._on_quest_accept(payload)
        elif msg_type == Msg.QUEST_COMPLETE:
            self._on_quest_complete(payload)

        else:
            print(f"[{self.addr}] Unhandled: {name} (len={len(payload)})")

    # ── Login ──

    def _on_login(self, payload):
        uname_len = payload[0]
        username = payload[1:1 + uname_len].decode("utf-8")
        pw_off = 1 + uname_len
        pw_len = payload[pw_off]
        password = payload[pw_off + 1:pw_off + 1 + pw_len].decode("utf-8")

        account = ACCOUNTS.get(username)
        if not account:
            self.send_safe(build_login_result(1, 0))  # ACCOUNT_NOT_FOUND
            print(f"[{self.addr}] Login FAIL: account not found ({username})")
            return
        if account["password"] != password:
            self.send_safe(build_login_result(2, 0))  # WRONG_PASSWORD
            print(f"[{self.addr}] Login FAIL: wrong password ({username})")
            return

        self.account_id = account["id"]
        self.send_safe(build_login_result(0, self.account_id))  # SUCCESS
        print(f"[{self.addr}] Login OK: {username} (account={self.account_id})")

    # ── Character List ──

    def _on_char_list(self):
        chars = CHARACTERS.get(self.account_id, [])
        self.send_safe(build_char_list_resp(chars))
        print(f"[{self.addr}] CharList: {len(chars)} characters")

    # ── Character Select → Enter Game ──

    def _on_char_select(self, payload):
        char_id = struct.unpack_from("<I", payload, 0)[0]

        chars = CHARACTERS.get(self.account_id, [])
        char = next((c for c in chars if c["id"] == char_id), None)
        if not char:
            self.send_safe(build_enter_game(1, 0, 0, 0.0, 0.0, 0.0))  # CHAR_NOT_FOUND
            return

        self.char_id = char_id
        self.entity_id = self.world.alloc_entity_id()
        self.stats = dict(CHAR_STATS.get(char_id, {
            "level": 1, "hp": 100, "max_hp": 100, "mp": 50, "max_mp": 50,
            "atk": 10, "def": 5, "exp": 0, "exp_next": 100,
        }))
        self.pos = SPAWN_POS
        self.zone = DEFAULT_ZONE
        self.alive = True
        import copy
        self.inventory = copy.deepcopy(STARTER_ITEMS)

        # Register
        self.world.register_player(self)

        # 1) ENTER_GAME
        self.send_safe(build_enter_game(
            0, self.entity_id, self.zone, *self.pos))

        # 2) Auto STAT_SYNC
        self.send_safe(build_stat_sync(self.stats))

        # 3) Broadcast APPEAR to others
        self.world.broadcast_zone(self.zone,
            build_appear(self.entity_id, *self.pos),
            exclude_eid=self.entity_id)

        # 4) Send existing players to this client
        with self.world.lock:
            for eid, s in self.world.players.items():
                if eid != self.entity_id and s.zone == self.zone:
                    self.send_safe(build_appear(eid, *s.pos))

        # 5) Send existing monsters in this zone (MONSTER_SPAWN)
        with self.world.lock:
            for eid, m in self.world.monsters.items():
                if m.zone == self.zone and m.alive:
                    self.send_safe(build_monster_spawn(
                        eid, m.template_id, m.level, m.hp, m.max_hp, *m.pos))

        print(f"[{self.addr}] EnterGame: char={char_id}, entity={self.entity_id}")

    # ── Movement ──

    def _on_move(self, payload):
        x, y, z = struct.unpack_from("<fff", payload, 0)
        self.pos = (x, y, z)
        if self.entity_id:
            self.world.broadcast_zone(self.zone,
                build_move_broadcast(self.entity_id, x, y, z),
                exclude_eid=self.entity_id)

    # ── Combat ──

    def _on_attack(self, payload):
        target_eid = struct.unpack_from("<Q", payload, 0)[0]

        if not self.alive:
            self.send_safe(build_attack_result(
                5, self.entity_id, target_eid, 0, 0, 0))  # ATTACKER_DEAD
            return

        if target_eid == self.entity_id:
            self.send_safe(build_attack_result(
                6, self.entity_id, target_eid, 0, 0, 0))  # SELF_ATTACK
            return

        target_type, target = self.world.get_target(target_eid)

        if target is None:
            self.send_safe(build_attack_result(
                1, self.entity_id, target_eid, 0, 0, 0))  # TARGET_NOT_FOUND
            return

        if target_type == "player":
            self._attack_player(target)
        elif target_type == "monster":
            self._attack_monster(target)

    def _attack_player(self, target):
        if not target.alive:
            self.send_safe(build_attack_result(
                2, self.entity_id, target.entity_id, 0, 0, target.stats["max_hp"]))
            return

        atk = self.stats["atk"]
        defence = target.stats["def"]
        damage = max(1, atk - defence + random.randint(-5, 5))

        target.stats["hp"] = max(0, target.stats["hp"] - damage)

        result_pkt = build_attack_result(
            0, self.entity_id, target.entity_id,
            damage, target.stats["hp"], target.stats["max_hp"])

        # Both attacker and target receive attack result
        self.send_safe(result_pkt)
        target.send_safe(result_pkt)

        if target.stats["hp"] <= 0:
            target.alive = False
            died_pkt = build_combat_died(target.entity_id, self.entity_id)
            # Broadcast death to all in zone (includes attacker and target)
            self.world.broadcast_zone(self.zone, died_pkt)

            # Give EXP to attacker
            self.stats["exp"] += 50
            self.send_safe(build_stat_sync(self.stats))

    def _attack_monster(self, monster):
        if not monster.alive:
            self.send_safe(build_attack_result(
                2, self.entity_id, monster.entity_id,
                0, 0, monster.max_hp))
            return

        atk = self.stats["atk"]
        defence = monster.defense
        damage = max(1, atk - defence + random.randint(-3, 3))

        remaining_hp = monster.take_damage(damage)

        result_pkt = build_attack_result(
            0, self.entity_id, monster.entity_id,
            damage, remaining_hp, monster.max_hp)
        self.send_safe(result_pkt)

        if remaining_hp <= 0:
            died_pkt = build_combat_died(monster.entity_id, self.entity_id)
            # Broadcast death to all in zone (includes attacker)
            self.world.broadcast_zone(self.zone, died_pkt)

            # EXP reward (level * 10)
            exp_reward = monster.level * 10
            self.stats["exp"] += exp_reward
            self.send_safe(build_stat_sync(self.stats))

            print(f"[{self.addr}] Killed {monster.name} (+{exp_reward} EXP)")

            # Schedule respawn
            self.world.schedule_monster_respawn(monster, delay=5.0)

    # ── Respawn ──

    def _on_respawn(self):
        if self.alive:
            return

        self.alive = True
        self.stats["hp"] = self.stats["max_hp"]
        self.stats["mp"] = self.stats["max_mp"]
        self.pos = SPAWN_POS

        self.send_safe(build_respawn_result(
            0, self.stats["hp"], self.stats["mp"], *self.pos))
        self.send_safe(build_stat_sync(self.stats))

        # Broadcast appear
        self.world.broadcast_zone(self.zone,
            build_appear(self.entity_id, *self.pos),
            exclude_eid=self.entity_id)

        print(f"[{self.addr}] Respawned (entity={self.entity_id})")

    # ── Zone Transfer (session 16) ──

    def _on_zone_transfer(self, payload):
        target_zone = struct.unpack_from("<i", payload, 0)[0]
        if target_zone == self.zone:
            self.send_safe(build_zone_transfer_result(2, self.zone, *self.pos))  # ALREADY_SAME_ZONE
            return
        old_zone = self.zone
        self.zone = target_zone
        self.pos = SPAWN_POS
        self.send_safe(build_zone_transfer_result(0, target_zone, *self.pos))
        print(f"[{self.addr}] ZoneTransfer: {old_zone} -> {target_zone}")

    # ── Skill Use (session 19) ──

    def _on_skill_use(self, payload):
        skill_id = struct.unpack_from("<I", payload, 0)[0]
        target_eid = struct.unpack_from("<Q", payload, 4)[0]

        skill = next((s for s in SKILLS if s["id"] == skill_id), None)
        if not skill:
            self.send_safe(build_skill_result(1, skill_id, self.entity_id, target_eid, 0, 0))
            return

        # Check MP
        mp_cost = skill["mp"]
        if self.stats["mp"] < mp_cost:
            self.send_safe(build_skill_result(2, skill_id, self.entity_id, target_eid, 0, 0))
            return

        self.stats["mp"] -= mp_cost
        damage = skill["dmg"] + random.randint(-5, 5)

        # Apply damage to target
        target_hp = 0
        target_type, target = self.world.get_target(target_eid)
        if target_type == "monster" and target.alive:
            target_hp = target.take_damage(damage)
        elif target_type == "player" and target.alive:
            target.stats["hp"] = max(0, target.stats["hp"] - damage)
            target_hp = target.stats["hp"]

        self.send_safe(build_skill_result(0, skill_id, self.entity_id, target_eid, damage, target_hp))
        self.send_safe(build_stat_sync(self.stats))

        # Kill check for monster
        if target_type == "monster" and not target.alive:
            died_pkt = build_combat_died(target.entity_id, self.entity_id)
            self.world.broadcast_zone(self.zone, died_pkt)
            exp_reward = target.level * 10
            self.stats["exp"] += exp_reward
            self.send_safe(build_stat_sync(self.stats))
            self.world.schedule_monster_respawn(target, delay=5.0)

        print(f"[{self.addr}] SkillUse: skill={skill_id}, target={target_eid}, dmg={damage}")

    # ── Party (session 20) ──

    def _on_party_create(self):
        self.party_id = random.randint(1, 9999)
        self._send_party_info()
        print(f"[{self.addr}] PartyCreate: id={self.party_id}")

    def _on_party_leave(self):
        self.party_id = 0
        self.send_safe(build_party_info(0, 0, 0, []))
        print(f"[{self.addr}] PartyLeave")

    def _send_party_info(self):
        if self.party_id == 0:
            self.send_safe(build_party_info(0, 0, 0, []))
            return
        members = [{"entity": self.entity_id, "level": self.stats.get("level", 1) if self.stats else 1}]
        self.send_safe(build_party_info(0, self.party_id, self.entity_id, members))

    # ── Instance (session 21) ──

    def _on_instance_create(self, payload):
        dungeon_type = struct.unpack_from("<I", payload, 0)[0]
        self.in_instance = True
        self.instance_id = random.randint(1, 9999)
        self.send_safe(build_instance_enter(0, self.instance_id, dungeon_type))
        print(f"[{self.addr}] InstanceCreate: dungeon={dungeon_type}, instance={self.instance_id}")

    def _on_instance_leave(self):
        self.in_instance = False
        self.instance_id = 0
        self.send_safe(build_instance_leave_result(0, self.zone, *self.pos))
        print(f"[{self.addr}] InstanceLeave")

    # ── Inventory (session 23) ──

    def _on_inventory_req(self):
        if not self.inventory:
            import copy
            self.inventory = copy.deepcopy(STARTER_ITEMS)
        self.send_safe(build_inventory_resp(self.inventory))

    def _on_item_add(self, payload):
        item_id = struct.unpack_from("<I", payload, 0)[0]
        count = struct.unpack_from("<H", payload, 4)[0]
        slot = len(self.inventory)
        if slot >= 20:
            self.send_safe(build_item_add_result(1, 0, item_id, count))  # INVENTORY_FULL
            return
        item = {"slot": slot, "item_id": item_id, "count": count, "equipped": 0}
        self.inventory.append(item)
        self.send_safe(build_item_add_result(0, slot, item_id, count))
        print(f"[{self.addr}] ItemAdd: slot={slot}, item={item_id}, count={count}")

    def _on_item_use(self, payload):
        slot = payload[0]
        item = next((it for it in self.inventory if it["slot"] == slot), None)
        if not item:
            self.send_safe(build_item_use_result(2, slot, 0))  # EMPTY_SLOT
            return
        item["count"] -= 1
        if item["count"] <= 0:
            self.inventory.remove(item)
        self.send_safe(build_item_use_result(0, slot, item["item_id"]))
        print(f"[{self.addr}] ItemUse: slot={slot}")

    def _on_item_equip(self, payload, equip=True):
        slot = payload[0]
        item = next((it for it in self.inventory if it["slot"] == slot), None)
        if not item:
            self.send_safe(build_item_equip_result(2, slot, 0, 0))  # EMPTY_SLOT
            return
        equipped = 1 if equip else 0
        item["equipped"] = equipped
        self.send_safe(build_item_equip_result(0, slot, item["item_id"], equipped))
        print(f"[{self.addr}] Item{'Equip' if equip else 'Unequip'}: slot={slot}")

    # ── Buffs (session 24) ──

    def _on_buff_list_req(self):
        buff_list = [{"buff_id": bid, "remaining_ms": b["remaining_ms"], "stacks": b["stacks"]}
                     for bid, b in self.buffs.items()]
        self.send_safe(build_buff_list_resp(buff_list))

    def _on_buff_apply(self, payload):
        buff_id = struct.unpack_from("<I", payload, 0)[0]
        tmpl = BUFF_TEMPLATES.get(buff_id)
        if not tmpl:
            self.send_safe(build_buff_result(1, buff_id, 0, 0))  # BUFF_NOT_FOUND
            return
        self.buffs[buff_id] = {
            "remaining_ms": tmpl["duration_ms"],
            "stacks": tmpl["stacks"],
        }
        self.send_safe(build_buff_result(0, buff_id, tmpl["stacks"], tmpl["duration_ms"]))
        print(f"[{self.addr}] BuffApply: {tmpl['name']} (id={buff_id})")

    def _on_buff_remove(self, payload):
        buff_id = struct.unpack_from("<I", payload, 0)[0]
        if buff_id not in self.buffs:
            self.send_safe(build_buff_remove_resp(3, buff_id))  # INACTIVE
            return
        del self.buffs[buff_id]
        self.send_safe(build_buff_remove_resp(0, buff_id))
        print(f"[{self.addr}] BuffRemove: id={buff_id}")

    # ── Quests (session 28) ──

    def _on_quest_list_req(self):
        quest_list = [{"quest_id": qid, "state": q["state"], "progress": q["progress"], "target": q["target"]}
                      for qid, q in self.quests.items()]
        self.send_safe(build_quest_list_resp(quest_list))

    def _on_quest_accept(self, payload):
        quest_id = struct.unpack_from("<I", payload, 0)[0]
        tmpl = QUEST_TEMPLATES.get(quest_id)
        if not tmpl:
            self.send_safe(build_quest_accept_result(1, quest_id))  # QUEST_NOT_FOUND
            return
        if quest_id in self.quests:
            self.send_safe(build_quest_accept_result(2, quest_id))  # ALREADY_ACCEPTED
            return
        self.quests[quest_id] = {"state": 1, "progress": 0, "target": tmpl["target"]}  # ACCEPTED
        self.send_safe(build_quest_accept_result(0, quest_id))
        print(f"[{self.addr}] QuestAccept: {tmpl['name']} (id={quest_id})")

    def _on_quest_complete(self, payload):
        quest_id = struct.unpack_from("<I", payload, 0)[0]
        tmpl = QUEST_TEMPLATES.get(quest_id)
        if not tmpl or quest_id not in self.quests:
            self.send_safe(build_quest_complete_result(1, quest_id, 0, 0, 0))
            return
        q = self.quests[quest_id]
        if q["progress"] < q["target"]:
            self.send_safe(build_quest_complete_result(6, quest_id, 0, 0, 0))  # INCOMPLETE
            return
        q["state"] = 4  # REWARDED
        self.stats["exp"] += tmpl["reward_exp"]
        self.send_safe(build_quest_complete_result(
            0, quest_id, tmpl["reward_exp"], tmpl["reward_item_id"], tmpl["reward_count"]))
        self.send_safe(build_stat_sync(self.stats))
        print(f"[{self.addr}] QuestComplete: {tmpl['name']} (+{tmpl['reward_exp']} EXP)")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Server Main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_server(port=DEFAULT_PORT):
    world = World()

    print("━━━ ECS MMORPG Mock Field Server ━━━")
    print(f"Port      : {port}")
    print(f"Accounts  : {', '.join(f'{u}/{a['password']}' for u, a in ACCOUNTS.items())}")
    print(f"Monsters  :")
    world.spawn_monsters()
    print(f"Waiting for connections...\n")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", port))
    server.listen(16)

    try:
        while True:
            client_sock, addr = server.accept()
            client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            print(f"[{addr}] Connected")
            session = ClientSession(client_sock, addr, world)
            t = threading.Thread(target=session.run, daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ECS MMORPG Mock Field Server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Listen port (default: 7777)")
    args = parser.parse_args()
    run_server(args.port)
