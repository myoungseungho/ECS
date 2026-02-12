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
            # Broadcast appear to all in zone
            pkt = build_appear(monster.entity_id, *monster.pos)
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

        # 5) Send existing monsters in this zone
        with self.world.lock:
            for eid, m in self.world.monsters.items():
                if m.zone == self.zone and m.alive:
                    self.send_safe(build_appear(eid, *m.pos))

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
