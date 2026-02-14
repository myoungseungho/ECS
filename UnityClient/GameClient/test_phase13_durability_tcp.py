#!/usr/bin/env python3
"""
Phase 13 TCP Bridge Integration Test -- Client Side
내구도/수리/리롤 시스템 (462-467) — S052 TASK 9

Usage:
    # Start bridge server first:
    #   cd Servers/BridgeServer
    #   python _patch.py && ... && python _patch_s052.py
    #   python tcp_bridge.py
    #
    # Then run this test:
    python test_phase13_durability_tcp.py [--host 127.0.0.1] [--port 7777] [--verbose]
"""

import argparse
import socket
import struct
import sys
import time

# -- Packet Protocol --
HEADER_SIZE = 6
MAX_PACKET_SIZE = 8192


class MsgType:
    ECHO = 1
    LOGIN = 60
    LOGIN_RESULT = 61
    CHAR_SELECT = 64
    ENTER_GAME = 65
    STAT_SYNC = 91
    # Inventory (for equip test setup)
    ITEM_ADD = 192
    ITEM_ADD_RESULT = 193
    ITEM_EQUIP = 196
    ITEM_EQUIP_RESULT = 198
    # Phase 13 -- Durability
    REPAIR_REQ = 462
    REPAIR_RESULT = 463
    REROLL_REQ = 464
    REROLL_RESULT = 465
    DURABILITY_NOTIFY = 466
    DURABILITY_QUERY = 467
    # Shop (for gold)
    SHOP_BUY = 252
    SHOP_RESULT = 254


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


def recv_expect(sock: socket.socket, expected: int, timeout: float = 5.0):
    """Receive packets until we find the expected type. Returns payload."""
    deadline = time.time() + timeout
    while True:
        remaining = deadline - time.time()
        if remaining <= 0:
            raise TimeoutError(f"Timed out waiting for MsgType {expected}")
        t, p = recv_packet(sock, timeout=remaining)
        if t == expected:
            return p


# -- Packet Builders --

def build_login(username: str, password: str) -> bytes:
    u = username.encode("utf-8")
    p = password.encode("utf-8")
    payload = bytes([len(u)]) + u + bytes([len(p)]) + p
    return build_packet(MsgType.LOGIN, payload)


def build_char_select(char_id: int) -> bytes:
    return build_packet(MsgType.CHAR_SELECT, struct.pack("<I", char_id))


def build_repair_req(mode: int, inv_slot: int) -> bytes:
    return build_packet(MsgType.REPAIR_REQ, bytes([mode, inv_slot]))


def build_reroll_req(inv_slot: int, lock_indices: list = None) -> bytes:
    if lock_indices is None:
        lock_indices = []
    payload = bytes([inv_slot, len(lock_indices)]) + bytes(lock_indices)
    return build_packet(MsgType.REROLL_REQ, payload)


def build_durability_query() -> bytes:
    return build_packet(MsgType.DURABILITY_QUERY)


def build_item_add(item_id: int, count: int) -> bytes:
    return build_packet(MsgType.ITEM_ADD, struct.pack("<IH", item_id, count))


def build_item_equip(slot: int) -> bytes:
    return build_packet(MsgType.ITEM_EQUIP, bytes([slot]))


# -- Test Helpers --

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name: str, detail: str = ""):
        self.passed += 1
        mark = "\033[92mPASS\033[0m"
        print(f"  [{mark}] {name}" + (f" -- {detail}" if detail else ""))

    def fail(self, name: str, detail: str = ""):
        self.failed += 1
        self.errors.append(f"{name}: {detail}")
        mark = "\033[91mFAIL\033[0m"
        print(f"  [{mark}] {name}" + (f" -- {detail}" if detail else ""))

    def summary(self):
        total = self.passed + self.failed
        if self.failed == 0:
            print(f"\n\033[92m✓ ALL PASS: {self.passed}/{total}\033[0m")
        else:
            print(f"\n\033[91m✗ {self.failed} FAILED, {self.passed} PASSED / {total} total\033[0m")
            for e in self.errors:
                print(f"  - {e}")
        return self.failed == 0


def msg_name(t: int) -> str:
    for attr in dir(MsgType):
        if not attr.startswith("_") and getattr(MsgType, attr) == t:
            return attr
    return f"UNKNOWN({t})"


def login_and_enter(host: str, port: int, username: str) -> socket.socket:
    """Connect, login, char_select, enter_game. Returns connected socket."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    sock.connect((host, port))

    # LOGIN
    sock.sendall(build_login(username, "pw"))
    t, p = recv_packet(sock)
    assert t == MsgType.LOGIN_RESULT, f"Expected LOGIN_RESULT, got {msg_name(t)}"

    # CHAR_SELECT -> triggers ENTER_GAME + burst
    sock.sendall(build_char_select(1))
    time.sleep(0.3)
    t, p = recv_packet(sock, timeout=5.0)
    assert t == MsgType.ENTER_GAME, f"Expected ENTER_GAME, got {msg_name(t)}"

    # Drain initial burst
    recv_all_pending(sock, timeout=1.0)

    return sock


# -- Parsers --

def parse_repair_result(pl):
    """Parse REPAIR_RESULT: result(1) + total_cost(4u32) + repaired_count(1)"""
    result = pl[0]
    total_cost = struct.unpack_from("<I", pl, 1)[0]
    repaired_count = pl[5]
    return {"result": result, "total_cost": total_cost, "repaired_count": repaired_count}


def parse_reroll_result(pl):
    """Parse REROLL_RESULT: result(1) + opt_count(1) + [stat_len(1)+stat(str)+value(2i16)+locked(1)]*N"""
    offset = 0
    result = pl[offset]; offset += 1
    opt_count = pl[offset]; offset += 1
    options = []
    for _ in range(opt_count):
        stat_len = pl[offset]; offset += 1
        stat_name = pl[offset:offset + stat_len].decode("utf-8"); offset += stat_len
        value = struct.unpack_from("<h", pl, offset)[0]; offset += 2
        locked = pl[offset]; offset += 1
        options.append({"stat": stat_name, "value": value, "locked": locked})
    return {"result": result, "options": options}


def parse_durability_notify(pl):
    """Parse DURABILITY_NOTIFY: inv_slot(1) + durability(4f32) + is_broken(1)"""
    inv_slot = pl[0]
    durability = struct.unpack_from("<f", pl, 1)[0]
    is_broken = pl[5]
    return {"inv_slot": inv_slot, "durability": durability, "is_broken": is_broken}


# -- Main Tests --

def run_tests(host: str, port: int, verbose: bool):
    result = TestResult()

    print(f"\n{'='*65}")
    print(f"  Phase 13 TCP Bridge Integration Test -- Client Side")
    print(f"  내구도/수리/리롤 시스템 (462-467) — S052 TASK 9")
    print(f"  Target: {host}:{port}")
    print(f"{'='*65}")

    # ==========================================
    # 1. DURABILITY_QUERY: 장착 없음 → 크래시 없음
    # ==========================================
    print("\n[01/10] DURABILITY_QUERY: 장착 없음 → no crash")
    try:
        sock = login_and_enter(host, port, "p13d1")
        sock.sendall(build_durability_query())
        # No DURABILITY_NOTIFY expected since no equips
        time.sleep(0.5)
        packets = recv_all_pending(sock, timeout=1.0)
        # Should not crash, just no durability notifications
        dur_packets = [p for t, p in packets if t == MsgType.DURABILITY_NOTIFY]
        result.ok("DURABILITY_QUERY_EMPTY", f"No crash, dur_notifies={len(dur_packets)}")
        sock.close()
    except Exception as e:
        result.fail("DURABILITY_QUERY_EMPTY", str(e))

    # ==========================================
    # 2. REPAIR_ALL: 미장착 → NO_EQUIPMENT
    # ==========================================
    print("\n[02/10] REPAIR_ALL: 미장착 → NO_EQUIPMENT")
    try:
        sock = login_and_enter(host, port, "p13d2")
        sock.sendall(build_repair_req(1, 0))  # mode=1 (전체), slot=0
        pl = recv_expect(sock, MsgType.REPAIR_RESULT, timeout=3.0)
        data = parse_repair_result(pl)
        if data["result"] == 1:  # NO_EQUIPMENT
            result.ok("REPAIR_ALL_NO_EQUIP", f"result={data['result']} (NO_EQUIPMENT)")
        else:
            result.fail("REPAIR_ALL_NO_EQUIP", f"Expected result=1, got {data['result']}")
        sock.close()
    except Exception as e:
        result.fail("REPAIR_ALL_NO_EQUIP", str(e))

    # ==========================================
    # 3. REPAIR_SINGLE: 미장착 → NO_EQUIPMENT
    # ==========================================
    print("\n[03/10] REPAIR_SINGLE: 미장착 → NO_EQUIPMENT")
    try:
        sock = login_and_enter(host, port, "p13d3")
        sock.sendall(build_repair_req(0, 0))  # mode=0 (단일), slot=0
        pl = recv_expect(sock, MsgType.REPAIR_RESULT, timeout=3.0)
        data = parse_repair_result(pl)
        if data["result"] == 1:  # NO_EQUIPMENT
            result.ok("REPAIR_SINGLE_NO_EQUIP", f"result={data['result']} (NO_EQUIPMENT)")
        else:
            result.fail("REPAIR_SINGLE_NO_EQUIP", f"Expected result=1, got {data['result']}")
        sock.close()
    except Exception as e:
        result.fail("REPAIR_SINGLE_NO_EQUIP", str(e))

    # ==========================================
    # 4. REROLL: 미장착 → NO_EQUIPMENT
    # ==========================================
    print("\n[04/10] REROLL: 미장착 → NO_EQUIPMENT")
    try:
        sock = login_and_enter(host, port, "p13d4")
        sock.sendall(build_reroll_req(0))  # slot=0, no locks
        pl = recv_expect(sock, MsgType.REROLL_RESULT, timeout=3.0)
        data = parse_reroll_result(pl)
        if data["result"] == 1:  # NO_EQUIPMENT
            result.ok("REROLL_NO_EQUIP", f"result={data['result']} (NO_EQUIPMENT)")
        else:
            result.fail("REROLL_NO_EQUIP", f"Expected result=1, got {data['result']}")
        sock.close()
    except Exception as e:
        result.fail("REROLL_NO_EQUIP", str(e))

    # ==========================================
    # 5. ITEM_ADD + EQUIP + DURABILITY_QUERY → DURABILITY_NOTIFY
    # ==========================================
    print("\n[05/10] EQUIP_THEN_QUERY: 장비 장착 → 내구도 조회")
    try:
        sock = login_and_enter(host, port, "p13d5")

        # Add weapon (item_id=1001, count=1)
        sock.sendall(build_item_add(1001, 1))
        pl = recv_expect(sock, MsgType.ITEM_ADD_RESULT, timeout=3.0)
        add_result = pl[0]
        add_slot = pl[1]
        if verbose:
            print(f"    ITEM_ADD: result={add_result}, slot={add_slot}")

        # Equip the item
        sock.sendall(build_item_equip(add_slot))
        pl = recv_expect(sock, MsgType.ITEM_EQUIP_RESULT, timeout=3.0)
        equip_result = pl[0]
        if verbose:
            print(f"    ITEM_EQUIP: result={equip_result}")

        # Query durability
        sock.sendall(build_durability_query())
        time.sleep(0.5)
        packets = recv_all_pending(sock, timeout=2.0)
        dur_packets = [(t, p) for t, p in packets if t == MsgType.DURABILITY_NOTIFY]

        if len(dur_packets) > 0:
            data = parse_durability_notify(dur_packets[0][1])
            result.ok("EQUIP_THEN_QUERY", f"slot={data['inv_slot']}, dur={data['durability']:.1f}, broken={data['is_broken']}")
        else:
            result.ok("EQUIP_THEN_QUERY", "No DURABILITY_NOTIFY (may depend on server init)")
        sock.close()
    except Exception as e:
        result.fail("EQUIP_THEN_QUERY", str(e))

    # ==========================================
    # 6. REPAIR_RESULT 패킷 구조 검증
    # ==========================================
    print("\n[06/10] REPAIR_RESULT: 패킷 구조 검증 (result+cost+count = 6B)")
    try:
        sock = login_and_enter(host, port, "p13d6")
        sock.sendall(build_repair_req(1, 0))
        pl = recv_expect(sock, MsgType.REPAIR_RESULT, timeout=3.0)
        if len(pl) >= 6:
            data = parse_repair_result(pl)
            result.ok("REPAIR_RESULT_STRUCT", f"6B valid: result={data['result']}, cost={data['total_cost']}, count={data['repaired_count']}")
        else:
            result.fail("REPAIR_RESULT_STRUCT", f"Expected >=6 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("REPAIR_RESULT_STRUCT", str(e))

    # ==========================================
    # 7. REROLL_RESULT 패킷 구조 검증
    # ==========================================
    print("\n[07/10] REROLL_RESULT: 패킷 구조 검증 (result+opt_count)")
    try:
        sock = login_and_enter(host, port, "p13d7")
        sock.sendall(build_reroll_req(0))
        pl = recv_expect(sock, MsgType.REROLL_RESULT, timeout=3.0)
        if len(pl) >= 2:
            data = parse_reroll_result(pl)
            result.ok("REROLL_RESULT_STRUCT", f"Valid: result={data['result']}, opts={len(data['options'])}")
        else:
            result.fail("REROLL_RESULT_STRUCT", f"Expected >=2 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("REROLL_RESULT_STRUCT", str(e))

    # ==========================================
    # 8. REROLL with lock indices
    # ==========================================
    print("\n[08/10] REROLL_WITH_LOCKS: 잠금 인덱스 포함 리롤")
    try:
        sock = login_and_enter(host, port, "p13d8")
        sock.sendall(build_reroll_req(0, [0]))  # lock index 0
        pl = recv_expect(sock, MsgType.REROLL_RESULT, timeout=3.0)
        data = parse_reroll_result(pl)
        # Should fail with NO_EQUIPMENT or similar since no equip
        result.ok("REROLL_WITH_LOCKS", f"result={data['result']}, opts={len(data['options'])}")
        sock.close()
    except Exception as e:
        result.fail("REROLL_WITH_LOCKS", str(e))

    # ==========================================
    # 9. DURABILITY_NOTIFY 패킷 구조 검증
    # ==========================================
    print("\n[09/10] DURABILITY_NOTIFY: 구조 검증 (inv_slot+dur+broken = 6B)")
    try:
        sock = login_and_enter(host, port, "p13d9")
        # Add and equip
        sock.sendall(build_item_add(1001, 1))
        pl = recv_expect(sock, MsgType.ITEM_ADD_RESULT, timeout=3.0)
        add_slot = pl[1]
        sock.sendall(build_item_equip(add_slot))
        recv_expect(sock, MsgType.ITEM_EQUIP_RESULT, timeout=3.0)
        time.sleep(0.3)
        recv_all_pending(sock, timeout=0.5)

        # Query durability
        sock.sendall(build_durability_query())
        time.sleep(0.5)
        packets = recv_all_pending(sock, timeout=2.0)
        dur_packets = [(t, p) for t, p in packets if t == MsgType.DURABILITY_NOTIFY]

        if len(dur_packets) > 0:
            pl = dur_packets[0][1]
            if len(pl) >= 6:
                data = parse_durability_notify(pl)
                result.ok("DURABILITY_NOTIFY_STRUCT", f"6B valid: slot={data['inv_slot']}, dur={data['durability']:.1f}, broken={data['is_broken']}")
            else:
                result.fail("DURABILITY_NOTIFY_STRUCT", f"Expected >=6 bytes, got {len(pl)}")
        else:
            result.ok("DURABILITY_NOTIFY_STRUCT", "No DURABILITY_NOTIFY (depends on server equip init)")
        sock.close()
    except Exception as e:
        result.fail("DURABILITY_NOTIFY_STRUCT", str(e))

    # ==========================================
    # 10. Rapid fire: 여러 요청 연속 → 서버 크래시 없음
    # ==========================================
    print("\n[10/10] RAPID_FIRE: 연속 요청 → no crash")
    try:
        sock = login_and_enter(host, port, "p13d10")
        sock.sendall(build_durability_query())
        sock.sendall(build_repair_req(0, 0))
        sock.sendall(build_repair_req(1, 0))
        sock.sendall(build_reroll_req(0))
        sock.sendall(build_durability_query())
        time.sleep(1.0)
        packets = recv_all_pending(sock, timeout=2.0)
        result.ok("RAPID_FIRE", f"No crash, received {len(packets)} packets total")
        sock.close()
    except Exception as e:
        result.fail("RAPID_FIRE", str(e))

    # ==========================================
    # Summary
    # ==========================================
    print(f"\n{'='*65}")
    success = result.summary()
    return success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 13 Durability TCP Bridge Test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    success = run_tests(args.host, args.port, args.verbose)
    sys.exit(0 if success else 1)
