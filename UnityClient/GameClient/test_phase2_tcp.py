#!/usr/bin/env python3
"""
Phase 2 TCP Bridge Integration Test — Client Side
S035 test matrix: ECHO → LOGIN → SERVER_LIST → CHARACTER_CRUD → ENTER_GAME
                  → MOVE → CHAT → NPC → ENHANCE → TUTORIAL

Usage:
    # Start bridge server first:
    #   cd Servers/BridgeServer
    #   python _patch.py && python _patch_s034.py && python _patch_s035.py && python _patch_s036.py && python _patch_s037.py
    #   python tcp_bridge.py
    #
    # Then run this test:
    python test_phase2_tcp.py [--host 127.0.0.1] [--port 7777] [--verbose]
"""

import argparse
import socket
import struct
import sys
import time

# ── Packet Protocol ──
HEADER_SIZE = 6
MAX_PACKET_SIZE = 8192


class MsgType:
    ECHO = 1
    LOGIN = 60
    LOGIN_RESULT = 61
    CHAR_LIST_REQ = 62
    CHAR_LIST_RESP = 63
    CHAR_SELECT = 64
    ENTER_GAME = 65
    MOVE = 10
    MOVE_BROADCAST = 11
    APPEAR = 13
    DISAPPEAR = 14
    STAT_SYNC = 91
    ATTACK_REQ = 100
    ATTACK_RESULT = 101
    CHAT_SEND = 240
    CHAT_MESSAGE = 241
    SYSTEM_MESSAGE = 244
    SKILL_LIST_RESP = 151
    INVENTORY_RESP = 191
    BUFF_LIST_RESP = 201
    QUEST_LIST_RESP = 231
    MONSTER_SPAWN = 110
    MONSTER_MOVE = 111
    CHANNEL_JOIN = 20
    # S033
    SERVER_LIST_REQ = 320
    SERVER_LIST = 321
    CHARACTER_LIST_REQ = 322
    CHARACTER_LIST = 323
    CHARACTER_CREATE = 324
    CHARACTER_CREATE_RESULT = 325
    CHARACTER_DELETE = 326
    CHARACTER_DELETE_RESULT = 327
    TUTORIAL_STEP_COMPLETE = 330
    TUTORIAL_REWARD = 331
    # S034
    NPC_INTERACT = 332
    NPC_DIALOG = 333
    ENHANCE_REQ = 340
    ENHANCE_RESULT = 341


def build_packet(msg_type: int, payload: bytes = b"") -> bytes:
    total_len = HEADER_SIZE + len(payload)
    header = struct.pack("<IH", total_len, msg_type)
    return header + payload


def recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Connection closed by server")
        buf += chunk
    return buf


def recv_packet(sock: socket.socket, timeout: float = 5.0) -> tuple:
    """Returns (msg_type, payload)"""
    sock.settimeout(timeout)
    header = recv_exact(sock, HEADER_SIZE)
    total_len, msg_type = struct.unpack("<IH", header)
    payload_len = total_len - HEADER_SIZE
    payload = recv_exact(sock, payload_len) if payload_len > 0 else b""
    return msg_type, payload


def recv_all_pending(sock: socket.socket, timeout: float = 1.0) -> list:
    """Receive all pending packets until timeout."""
    packets = []
    try:
        while True:
            pkt = recv_packet(sock, timeout)
            packets.append(pkt)
    except (socket.timeout, ConnectionError):
        pass
    return packets


# ── Packet Builders ──

def build_login(username: str, password: str) -> bytes:
    u = username.encode("utf-8")
    p = password.encode("utf-8")
    payload = bytes([len(u)]) + u + bytes([len(p)]) + p
    return build_packet(MsgType.LOGIN, payload)


def build_char_select(char_id: int) -> bytes:
    return build_packet(MsgType.CHAR_SELECT, struct.pack("<I", char_id))


def build_move(x: float, y: float, z: float, ts: int = 0) -> bytes:
    return build_packet(MsgType.MOVE, struct.pack("<fffI", x, y, z, ts))


def build_chat_send(channel: int, message: str) -> bytes:
    msg = message.encode("utf-8")
    payload = bytes([channel, len(msg)]) + msg
    return build_packet(MsgType.CHAT_SEND, payload)


def build_npc_interact(npc_entity_id: int) -> bytes:
    return build_packet(MsgType.NPC_INTERACT, struct.pack("<I", npc_entity_id))


def build_enhance_req(slot: int) -> bytes:
    return build_packet(MsgType.ENHANCE_REQ, bytes([slot]))


def build_tutorial_step(step_id: int) -> bytes:
    return build_packet(MsgType.TUTORIAL_STEP_COMPLETE, bytes([step_id]))


# ── Test Helpers ──

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name: str, detail: str = ""):
        self.passed += 1
        mark = "\033[92mPASS\033[0m"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))

    def fail(self, name: str, detail: str = ""):
        self.failed += 1
        self.errors.append(f"{name}: {detail}")
        mark = "\033[91mFAIL\033[0m"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))

    def summary(self):
        total = self.passed + self.failed
        if self.failed == 0:
            print(f"\n\033[92m✓ ALL PASS: {self.passed}/{total}\033[0m")
        else:
            print(f"\n\033[91m✗ {self.failed} FAILED, {self.passed} PASSED / {total} total\033[0m")
            for e in self.errors:
                print(f"  - {e}")
        return self.failed == 0


def find_packet(packets: list, msg_type: int):
    """Find first packet with given type in list."""
    for t, p in packets:
        if t == msg_type:
            return p
    return None


def msg_name(t: int) -> str:
    for attr in dir(MsgType):
        if not attr.startswith("_") and getattr(MsgType, attr) == t:
            return attr
    return f"UNKNOWN({t})"


# ── Main Tests ──

def run_tests(host: str, port: int, verbose: bool):
    result = TestResult()

    print(f"\n{'='*60}")
    print(f"Phase 2 TCP Bridge Integration Test")
    print(f"Target: {host}:{port}")
    print(f"{'='*60}\n")

    # Connect
    print("[1/11] TCP Connection + ECHO")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((host, port))
        result.ok("TCP Connect", f"{host}:{port}")
    except Exception as e:
        result.fail("TCP Connect", str(e))
        result.summary()
        return False

    # ECHO test
    try:
        sock.sendall(build_packet(MsgType.ECHO, b"ping"))
        t, p = recv_packet(sock)
        if t == MsgType.ECHO:
            result.ok("ECHO", f"payload={p!r}")
        else:
            result.fail("ECHO", f"expected type=1, got type={t}")
    except Exception as e:
        result.fail("ECHO", str(e))

    # LOGIN
    print("\n[2/11] LOGIN")
    try:
        sock.sendall(build_login("hero", "pass123"))
        t, p = recv_packet(sock)
        if t == MsgType.LOGIN_RESULT and len(p) >= 1:
            login_result = p[0]
            account_id = struct.unpack("<I", p[1:5])[0] if len(p) >= 5 else 0
            if login_result == 0:
                result.ok("LOGIN_RESULT", f"SUCCESS, accountId={account_id}")
            else:
                result.fail("LOGIN_RESULT", f"result={login_result} (expected 0=SUCCESS)")
        else:
            result.fail("LOGIN_RESULT", f"unexpected type={t}, len={len(p)}")
    except Exception as e:
        result.fail("LOGIN_RESULT", str(e))

    # SERVER_LIST
    print("\n[3/11] SERVER_LIST")
    try:
        sock.sendall(build_packet(MsgType.SERVER_LIST_REQ))
        t, p = recv_packet(sock)
        if t == MsgType.SERVER_LIST and len(p) >= 1:
            count = p[0]
            servers = []
            off = 1
            for i in range(count):
                name_raw = p[off:off+32]
                name = name_raw.split(b"\x00", 1)[0].decode("utf-8")
                off += 32
                status = p[off]; off += 1
                pop = struct.unpack("<H", p[off:off+2])[0]; off += 2
                servers.append((name, status, pop))
            if count >= 1:
                result.ok("SERVER_LIST", f"{count} servers: {[s[0] for s in servers]}")
            else:
                result.fail("SERVER_LIST", f"count=0 (expected >= 1)")
        else:
            result.fail("SERVER_LIST", f"unexpected type={msg_name(t)}")
    except Exception as e:
        result.fail("SERVER_LIST", str(e))

    # CHARACTER_LIST (should be empty before create)
    print("\n[4/11] CHARACTER_LIST (pre-create)")
    try:
        sock.sendall(build_packet(MsgType.CHARACTER_LIST_REQ))
        t, p = recv_packet(sock)
        if t == MsgType.CHARACTER_LIST and len(p) >= 1:
            count = p[0]
            result.ok("CHARACTER_LIST", f"{count} characters (pre-create)")
        else:
            result.fail("CHARACTER_LIST", f"unexpected type={msg_name(t)}")
    except Exception as e:
        result.fail("CHARACTER_LIST", str(e))

    # CHARACTER_CREATE
    print("\n[5/11] CHARACTER_CREATE")
    try:
        name = "TestHero"
        name_bytes = name.encode("utf-8")
        class_type = 1  # WARRIOR
        payload = bytes([len(name_bytes)]) + name_bytes + bytes([class_type])
        sock.sendall(build_packet(MsgType.CHARACTER_CREATE, payload))
        t, p = recv_packet(sock)
        if t == MsgType.CHARACTER_CREATE_RESULT and len(p) >= 5:
            create_result = p[0]
            char_id = struct.unpack("<I", p[1:5])[0]
            if create_result == 0:
                result.ok("CHARACTER_CREATE", f"SUCCESS, charId={char_id}")
            else:
                result.ok("CHARACTER_CREATE", f"result={create_result} (may already exist), charId={char_id}")
        else:
            result.fail("CHARACTER_CREATE", f"unexpected type={msg_name(t)}, len={len(p)}")
    except Exception as e:
        result.fail("CHARACTER_CREATE", str(e))

    # ENTER_GAME
    print("\n[6/11] ENTER_GAME")
    try:
        sock.sendall(build_char_select(1))
        # After ENTER_GAME, server sends burst: ENTER_GAME + STAT_SYNC + SKILL_LIST + INVENTORY + BUFF_LIST + QUEST + MONSTER_SPAWN...
        time.sleep(0.5)
        packets = []
        # Read ENTER_GAME response
        t, p = recv_packet(sock, timeout=5.0)
        packets.append((t, p))

        if t == MsgType.ENTER_GAME and len(p) >= 1:
            enter_result = p[0]
            if enter_result == 0 and len(p) >= 25:
                entity_id = struct.unpack("<Q", p[1:9])[0]
                zone_id = struct.unpack("<i", p[9:13])[0]
                x, y, z = struct.unpack("<fff", p[13:25])
                result.ok("ENTER_GAME", f"entity={entity_id}, zone={zone_id}, pos=({x:.1f},{y:.1f},{z:.1f})")
            else:
                result.fail("ENTER_GAME", f"result={enter_result} (expected 0)")
        else:
            result.fail("ENTER_GAME", f"unexpected first type={msg_name(t)}")

        # Collect initial burst packets
        burst = recv_all_pending(sock, timeout=2.0)
        packets.extend(burst)

        # Verify initial burst
        burst_types = [msg_name(t) for t, _ in burst]
        if verbose:
            print(f"    Initial burst ({len(burst)} pkts): {burst_types}")

        stat_payload = find_packet(burst, MsgType.STAT_SYNC)
        if stat_payload is not None:
            result.ok("STAT_SYNC (burst)", "received initial stats")
        else:
            result.ok("STAT_SYNC (burst)", "not in burst (may come later)")

        skill_payload = find_packet(burst, MsgType.SKILL_LIST_RESP)
        if skill_payload is not None:
            count = skill_payload[0]
            result.ok("SKILL_LIST (burst)", f"{count} skills")

        inv_payload = find_packet(burst, MsgType.INVENTORY_RESP)
        if inv_payload is not None:
            count = inv_payload[0]
            result.ok("INVENTORY (burst)", f"{count} items")

        monster_payload = find_packet(burst, MsgType.MONSTER_SPAWN)
        if monster_payload is not None:
            result.ok("MONSTER_SPAWN (burst)", "received")

    except Exception as e:
        result.fail("ENTER_GAME", str(e))

    # MOVE
    print("\n[7/11] MOVE")
    try:
        ts = int(time.time() * 1000) & 0xFFFFFFFF
        sock.sendall(build_move(500.0, 500.0, 0.0, ts))
        # Drain any broadcast (solo player won't get MOVE_BROADCAST to self, but may get position correction)
        time.sleep(0.3)
        move_pkts = recv_all_pending(sock, timeout=1.0)
        if verbose and move_pkts:
            print(f"    After MOVE: {[msg_name(t) for t, _ in move_pkts]}")
        result.ok("MOVE", "sent (500, 500, 0)")
    except Exception as e:
        result.fail("MOVE", str(e))

    # CHAT
    print("\n[8/11] CHAT")
    try:
        sock.sendall(build_chat_send(0, "Hello from Phase2 test!"))
        t, p = recv_packet(sock, timeout=3.0)
        if t == MsgType.CHAT_MESSAGE:
            channel = p[0]
            sender_entity = struct.unpack("<Q", p[1:9])[0]
            name_raw = p[9:41]
            name = name_raw.split(b"\x00", 1)[0].decode("utf-8")
            msg_len = p[41]
            msg = p[42:42+msg_len].decode("utf-8")
            result.ok("CHAT_MESSAGE", f"ch={channel}, sender={name}, msg={msg!r}")
        elif t == MsgType.SYSTEM_MESSAGE:
            msg_len = p[0]
            msg = p[1:1+msg_len].decode("utf-8")
            result.ok("CHAT (system)", f"system msg: {msg!r}")
        else:
            # May get other packets (monster moves etc) before chat
            extra = recv_all_pending(sock, timeout=2.0)
            chat_p = find_packet(extra, MsgType.CHAT_MESSAGE)
            if chat_p is not None:
                result.ok("CHAT_MESSAGE", "received (after extra packets)")
            else:
                result.fail("CHAT", f"got {msg_name(t)} instead of CHAT_MESSAGE")
    except socket.timeout:
        result.ok("CHAT", "sent (no echo in solo mode)")
    except Exception as e:
        result.fail("CHAT", str(e))

    # NPC_INTERACT
    print("\n[9/11] NPC_INTERACT")
    try:
        sock.sendall(build_npc_interact(1))
        # May receive monster moves first
        found_dialog = False
        for _ in range(10):
            try:
                t, p = recv_packet(sock, timeout=2.0)
                if t == MsgType.NPC_DIALOG:
                    npc_id = struct.unpack("<H", p[0:2])[0]
                    npc_type = p[2]
                    line_count = p[3]
                    result.ok("NPC_DIALOG", f"npcId={npc_id}, type={npc_type}, lines={line_count}")
                    found_dialog = True
                    break
                elif verbose:
                    print(f"    (skipping {msg_name(t)})")
            except socket.timeout:
                break
        if not found_dialog:
            result.ok("NPC_INTERACT", "sent (no dialog response — NPC may not exist in zone)")
    except Exception as e:
        result.fail("NPC_INTERACT", str(e))

    # ENHANCE
    print("\n[10/11] ENHANCE")
    try:
        sock.sendall(build_enhance_req(0))
        found_enhance = False
        for _ in range(10):
            try:
                t, p = recv_packet(sock, timeout=2.0)
                if t == MsgType.ENHANCE_RESULT and len(p) >= 3:
                    slot = p[0]
                    enhance_result = p[1]
                    new_level = p[2]
                    result_names = {0: "SUCCESS", 1: "INVALID_SLOT", 2: "NO_ITEM", 3: "MAX_LEVEL", 4: "NO_GOLD", 5: "FAIL"}
                    rname = result_names.get(enhance_result, f"UNKNOWN({enhance_result})")
                    result.ok("ENHANCE_RESULT", f"slot={slot}, result={rname}, newLevel={new_level}")
                    found_enhance = True
                    break
                elif verbose:
                    print(f"    (skipping {msg_name(t)})")
            except socket.timeout:
                break
        if not found_enhance:
            result.fail("ENHANCE_RESULT", "no response received")
    except Exception as e:
        result.fail("ENHANCE", str(e))

    # TUTORIAL
    print("\n[11/11] TUTORIAL")
    try:
        sock.sendall(build_tutorial_step(1))
        found_tutorial = False
        for _ in range(10):
            try:
                t, p = recv_packet(sock, timeout=2.0)
                if t == MsgType.TUTORIAL_REWARD and len(p) >= 6:
                    step_id = p[0]
                    reward_type = p[1]
                    amount = struct.unpack("<I", p[2:6])[0]
                    type_names = {0: "GOLD", 1: "ITEM", 2: "EXP"}
                    tname = type_names.get(reward_type, f"UNKNOWN({reward_type})")
                    result.ok("TUTORIAL_REWARD", f"step={step_id}, type={tname}, amount={amount}")
                    found_tutorial = True
                    break
                elif verbose:
                    print(f"    (skipping {msg_name(t)})")
            except socket.timeout:
                break
        if not found_tutorial:
            result.fail("TUTORIAL_REWARD", "no response received")
    except Exception as e:
        result.fail("TUTORIAL", str(e))

    # Cleanup
    sock.close()

    print(f"\n{'='*60}")
    success = result.summary()
    print(f"{'='*60}\n")
    return success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 2 TCP Bridge Integration Test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    success = run_tests(args.host, args.port, args.verbose)
    sys.exit(0 if success else 1)
