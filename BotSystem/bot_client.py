"""
Session 15: Bot Client

Single bot that connects to the server, handles packets, and maintains game state.
Provides player action methods for the Behavior Tree to call.
"""

import socket
import struct
import select
import math
import time

HEADER_SIZE = 6


def build_packet(msg_type, payload=b''):
    total = HEADER_SIZE + len(payload)
    return struct.pack('<IH', total, msg_type) + payload


class BotClient:
    def __init__(self, bot_id, host='127.0.0.1', port=7777):
        self.bot_id = bot_id
        self.host = host
        self.port = port
        self.sock = None
        self.connected = False
        self.in_game = False

        # Identity
        self.username = f"bot_{bot_id}" if isinstance(bot_id, str) else f"bot_{bot_id:03d}"
        self.account_id = 0
        self.entity_id = 0

        # Game state
        self.position = [0.0, 0.0, 0.0]
        self.zone_id = 0
        self.stats = {
            'level': 0, 'hp': 0, 'max_hp': 0,
            'mp': 0, 'max_mp': 0,
            'atk': 0, 'def': 0,
            'exp': 0, 'exp_to_next': 0,
        }
        self.alive = True

        # World knowledge
        self.monsters = {}          # entity_id -> monster dict
        self.nearby_entities = set()

        # AI state
        self.target_entity = 0
        self.move_target = None     # (x, y) or None
        self.attack_cooldown = 0.0

        # Network buffer
        self._recv_buf = b''

    # ━━━ Connection ━━━

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5.0)
        self.sock.connect((self.host, self.port))
        self.sock.setblocking(False)
        self.connected = True

    def disconnect(self):
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        self.connected = False
        self.in_game = False

    # ━━━ Login Flow ━━━

    def login(self):
        """Send LOGIN packet. CHAR_SELECT is auto-sent on LOGIN_RESULT."""
        uname = self.username.encode()
        pw = b"bot"
        payload = bytes([len(uname)]) + uname + bytes([len(pw)]) + pw
        self._send(build_packet(60, payload))

    def _select_character(self):
        self._send(build_packet(64, struct.pack('<I', self.account_id)))

    # ━━━ Player Actions ━━━

    def send_move(self, x, y, z=0.0):
        self.position = [x, y, z]
        self._send(build_packet(10, struct.pack('<fff', x, y, z)))

    def send_attack(self, target_entity):
        if self.attack_cooldown > 0:
            return False
        self._send(build_packet(100, struct.pack('<Q', target_entity)))
        self.attack_cooldown = 1.5
        return True

    def send_respawn(self):
        self._send(build_packet(103))

    def send_stat_query(self):
        self._send(build_packet(90))

    def send_take_damage(self, amount):
        """Test utility: self-damage"""
        self._send(build_packet(93, struct.pack('<i', amount)))

    # ━━━ AI Helpers ━━━

    def move_toward(self, target_x, target_y, speed=30.0):
        """Move toward target by speed units. Returns True if arrived."""
        dx = target_x - self.position[0]
        dy = target_y - self.position[1]
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < speed:
            self.send_move(target_x, target_y, 0.0)
            return True

        ratio = speed / dist
        new_x = self.position[0] + dx * ratio
        new_y = self.position[1] + dy * ratio
        self.send_move(new_x, new_y, 0.0)
        return False

    def distance_to(self, x, y):
        dx = x - self.position[0]
        dy = y - self.position[1]
        return math.sqrt(dx * dx + dy * dy)

    def get_nearest_alive_monster(self):
        """Returns entity_id of nearest alive monster, or 0."""
        nearest = 0
        nearest_dist = float('inf')
        for eid, m in self.monsters.items():
            if not m.get('alive', True):
                continue
            d = self.distance_to(m['x'], m['y'])
            if d < nearest_dist:
                nearest_dist = d
                nearest = eid
        return nearest

    # ━━━ Update ━━━

    def update(self, dt=0.0):
        """Process packets + decrease cooldown."""
        self._process_packets()
        if self.attack_cooldown > 0:
            self.attack_cooldown = max(0.0, self.attack_cooldown - dt)

    def _process_packets(self):
        if not self.connected or not self.sock:
            return

        try:
            readable, _, _ = select.select([self.sock], [], [], 0)
            if readable:
                data = self.sock.recv(8192)
                if not data:
                    self.connected = False
                    return
                self._recv_buf += data
        except (OSError, ValueError):
            return

        while len(self._recv_buf) >= 4:
            total_len = struct.unpack('<I', self._recv_buf[:4])[0]
            if total_len > 8192 or total_len < HEADER_SIZE:
                self._recv_buf = b''
                break
            if len(self._recv_buf) < total_len:
                break

            pkt = self._recv_buf[:total_len]
            self._recv_buf = self._recv_buf[total_len:]

            msg_type = struct.unpack('<H', pkt[4:6])[0]
            payload = pkt[6:]
            self._dispatch(msg_type, payload)

    def _dispatch(self, msg_type, payload):
        handlers = {
            61: self._on_login_result,
            65: self._on_enter_game,
            91: self._on_stat_sync,
            101: self._on_attack_result,
            102: self._on_combat_died,
            104: self._on_respawn_result,
            110: self._on_monster_spawn,
            113: self._on_monster_respawn,
            13: self._on_appear,
            14: self._on_disappear,
        }
        handler = handlers.get(msg_type)
        if handler:
            handler(payload)

    # ━━━ Packet Handlers ━━━

    def _on_login_result(self, payload):
        if len(payload) < 5:
            return
        if payload[0] == 0:
            self.account_id = struct.unpack('<I', payload[1:5])[0]
            self._select_character()

    def _on_enter_game(self, payload):
        if len(payload) < 25 or payload[0] != 0:
            return
        self.entity_id = struct.unpack('<Q', payload[1:9])[0]
        self.zone_id = struct.unpack('<i', payload[9:13])[0]
        self.position[0] = struct.unpack('<f', payload[13:17])[0]
        self.position[1] = struct.unpack('<f', payload[17:21])[0]
        self.position[2] = struct.unpack('<f', payload[21:25])[0]
        self.in_game = True
        self.alive = True

    def _on_stat_sync(self, payload):
        if len(payload) < 36:
            return
        vals = struct.unpack('<iiiiiiiii', payload[:36])
        self.stats = {
            'level': vals[0], 'hp': vals[1], 'max_hp': vals[2],
            'mp': vals[3], 'max_mp': vals[4],
            'atk': vals[5], 'def': vals[6],
            'exp': vals[7], 'exp_to_next': vals[8],
        }
        self.alive = vals[1] > 0

    def _on_attack_result(self, payload):
        if len(payload) < 29:
            return
        target = struct.unpack('<Q', payload[9:17])[0]
        target_hp = struct.unpack('<i', payload[21:25])[0]
        if target in self.monsters:
            self.monsters[target]['hp'] = target_hp
            if target_hp <= 0:
                self.monsters[target]['alive'] = False
                if self.target_entity == target:
                    self.target_entity = 0

    def _on_combat_died(self, payload):
        if len(payload) < 16:
            return
        dead = struct.unpack('<Q', payload[:8])[0]
        if dead == self.entity_id:
            self.alive = False
        if dead in self.monsters:
            self.monsters[dead]['alive'] = False

    def _on_respawn_result(self, payload):
        if len(payload) < 21 or payload[0] != 0:
            return
        self.stats['hp'] = struct.unpack('<i', payload[1:5])[0]
        self.stats['mp'] = struct.unpack('<i', payload[5:9])[0]
        self.position[0] = struct.unpack('<f', payload[9:13])[0]
        self.position[1] = struct.unpack('<f', payload[13:17])[0]
        self.position[2] = struct.unpack('<f', payload[17:21])[0]
        self.alive = True

    def _on_monster_spawn(self, payload):
        if len(payload) < 36:
            return
        eid = struct.unpack('<Q', payload[0:8])[0]
        self.monsters[eid] = {
            'entity': eid,
            'monster_id': struct.unpack('<I', payload[8:12])[0],
            'level': struct.unpack('<i', payload[12:16])[0],
            'hp': struct.unpack('<i', payload[16:20])[0],
            'max_hp': struct.unpack('<i', payload[20:24])[0],
            'x': struct.unpack('<f', payload[24:28])[0],
            'y': struct.unpack('<f', payload[28:32])[0],
            'z': struct.unpack('<f', payload[32:36])[0],
            'alive': True,
        }

    def _on_monster_respawn(self, payload):
        if len(payload) < 28:
            return
        eid = struct.unpack('<Q', payload[0:8])[0]
        hp = struct.unpack('<i', payload[8:12])[0]
        max_hp = struct.unpack('<i', payload[12:16])[0]
        x = struct.unpack('<f', payload[16:20])[0]
        y = struct.unpack('<f', payload[20:24])[0]
        z = struct.unpack('<f', payload[24:28])[0]
        if eid in self.monsters:
            self.monsters[eid].update({'hp': hp, 'max_hp': max_hp,
                                       'x': x, 'y': y, 'z': z, 'alive': True})
        else:
            self.monsters[eid] = {'entity': eid, 'monster_id': 0, 'level': 0,
                                  'hp': hp, 'max_hp': max_hp,
                                  'x': x, 'y': y, 'z': z, 'alive': True}

    def _on_appear(self, payload):
        if len(payload) >= 8:
            self.nearby_entities.add(struct.unpack('<Q', payload[:8])[0])

    def _on_disappear(self, payload):
        if len(payload) >= 8:
            self.nearby_entities.discard(struct.unpack('<Q', payload[:8])[0])

    # ━━━ Internal ━━━

    def _send(self, data):
        if self.connected and self.sock:
            try:
                self.sock.sendall(data)
            except OSError:
                self.connected = False
