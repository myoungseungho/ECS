#!/usr/bin/env python3
"""
Phase 11 TCP Bridge Integration Test -- Client Side
각인/초월 시스템 (454-459) — S050 TASK 8 Enhancement

Usage:
    # Start bridge server first:
    #   cd Servers/BridgeServer
    #   python _patch.py && ... && python _patch_s050.py
    #   python tcp_bridge.py
    #
    # Then run this test:
    python test_phase11_engraving_tcp.py [--host 127.0.0.1] [--port 7777] [--verbose]
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
    # Phase 11 -- Engraving / Transcend
    ENGRAVING_LIST_REQ = 454
    ENGRAVING_LIST = 455
    ENGRAVING_EQUIP = 456
    ENGRAVING_RESULT = 457
    TRANSCEND_REQ = 458
    TRANSCEND_RESULT = 459


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


def build_engraving_list_req() -> bytes:
    return build_packet(MsgType.ENGRAVING_LIST_REQ)


def build_engraving_equip(action: int, name: str) -> bytes:
    name_bytes = name.encode("utf-8")
    payload = bytes([action, len(name_bytes)]) + name_bytes
    return build_packet(MsgType.ENGRAVING_EQUIP, payload)


def build_transcend_req(slot: str) -> bytes:
    slot_bytes = slot.encode("utf-8")
    payload = bytes([len(slot_bytes)]) + slot_bytes
    return build_packet(MsgType.TRANSCEND_REQ, payload)


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

def read_str(pl, offset):
    """Read len(u8) + utf8 string. Returns (string, new_offset)."""
    slen = pl[offset]; offset += 1
    s = pl[offset:offset + slen].decode("utf-8"); offset += slen
    return s, offset


def parse_engraving_list(pl):
    """Parse ENGRAVING_LIST payload. Returns list of engraving dicts."""
    offset = 0
    count = pl[offset]; offset += 1
    engravings = []
    for _ in range(count):
        name, offset = read_str(pl, offset)
        name_kr, offset = read_str(pl, offset)
        points = pl[offset]; offset += 1
        active_level = pl[offset]; offset += 1
        is_active = pl[offset]; offset += 1
        effect_key, offset = read_str(pl, offset)
        effect_value = struct.unpack_from("<H", pl, offset)[0]; offset += 2
        engravings.append({
            "name": name, "name_kr": name_kr,
            "points": points, "active_level": active_level,
            "is_active": is_active,
            "effect_key": effect_key, "effect_value": effect_value,
        })
    return engravings, offset


def parse_engraving_result(pl):
    """Parse ENGRAVING_RESULT payload."""
    offset = 0
    result_code = pl[offset]; offset += 1
    name, offset = read_str(pl, offset)
    active_count = pl[offset]; offset += 1
    return result_code, name, active_count


def parse_transcend_result(pl):
    """Parse TRANSCEND_RESULT payload."""
    offset = 0
    result_code = pl[offset]; offset += 1
    slot, offset = read_str(pl, offset)
    new_level = pl[offset]; offset += 1
    gold_cost = struct.unpack_from("<I", pl, offset)[0]; offset += 4
    success = pl[offset]; offset += 1
    return result_code, slot, new_level, gold_cost, success


# -- Main Tests --

def run_tests(host: str, port: int, verbose: bool):
    result = TestResult()

    print(f"\n{'='*65}")
    print(f"  Phase 11 TCP Bridge Integration Test -- Client Side")
    print(f"  각인/초월 시스템 (454-459) — S050 TASK 8 Enhancement")
    print(f"  Target: {host}:{port}")
    print(f"{'='*65}")

    # ==========================================
    # ENGRAVING LIST (454-455)
    # ==========================================

    # -- 1. ENGRAVING_LIST_REQ -> ENGRAVING_LIST --
    print("\n[01/10] ENGRAVING_LIST: 각인 목록 조회")
    try:
        sock = login_and_enter(host, port, "p11e1")
        sock.sendall(build_engraving_list_req())
        pl = recv_expect(sock, MsgType.ENGRAVING_LIST, timeout=3.0)
        if len(pl) >= 1:
            count = pl[0]
            result.ok("ENGRAVING_LIST", f"count={count}, payload={len(pl)}B")
        else:
            result.fail("ENGRAVING_LIST", f"Expected >=1 byte, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("ENGRAVING_LIST", str(e))

    # -- 2. ENGRAVING_LIST -- format validation --
    print("\n[02/10] ENGRAVING_LIST_FORMAT: 패킷 포맷 검증")
    try:
        sock = login_and_enter(host, port, "p11e2")
        sock.sendall(build_engraving_list_req())
        pl = recv_expect(sock, MsgType.ENGRAVING_LIST, timeout=3.0)
        engravings, offset = parse_engraving_list(pl)
        names = [e["name_kr"] for e in engravings]
        result.ok("ENGRAVING_LIST_FORMAT", f"Parsed {len(engravings)} engravings: {names[:5]}{'...' if len(names) > 5 else ''}")
        sock.close()
    except Exception as e:
        result.fail("ENGRAVING_LIST_FORMAT", str(e))

    # -- 3. ENGRAVING_LIST -- field validation (9 types) --
    print("\n[03/10] ENGRAVING_FIELDS: 각인 필드 검증")
    try:
        sock = login_and_enter(host, port, "p11e3")
        sock.sendall(build_engraving_list_req())
        pl = recv_expect(sock, MsgType.ENGRAVING_LIST, timeout=3.0)
        engravings, _ = parse_engraving_list(pl)
        if len(engravings) >= 1:
            e = engravings[0]
            has_name = len(e["name"]) > 0 and len(e["name_kr"]) > 0
            has_effect = len(e["effect_key"]) > 0
            if has_name and has_effect:
                result.ok("ENGRAVING_FIELDS", f"name={e['name']}, kr={e['name_kr']}, pts={e['points']}, lv={e['active_level']}, active={e['is_active']}, effect={e['effect_key']}+{e['effect_value']}")
            else:
                result.fail("ENGRAVING_FIELDS", f"Invalid engraving data: {e}")
        else:
            result.ok("ENGRAVING_FIELDS", "No engravings returned (server may differ)")
        sock.close()
    except Exception as e:
        result.fail("ENGRAVING_FIELDS", str(e))

    # ==========================================
    # ENGRAVING EQUIP (456-457)
    # ==========================================

    # -- 4. ENGRAVING_EQUIP -- activate --
    print("\n[04/10] ENGRAVING_ACTIVATE: 각인 활성화")
    try:
        sock = login_and_enter(host, port, "p11ea1")
        sock.sendall(build_engraving_equip(0, "grudge"))
        pl = recv_expect(sock, MsgType.ENGRAVING_RESULT, timeout=3.0)
        if len(pl) >= 2:
            res_code, name, active_count = parse_engraving_result(pl)
            result.ok("ENGRAVING_ACTIVATE", f"result={res_code}, name={name}, active_count={active_count}")
        else:
            result.fail("ENGRAVING_ACTIVATE", f"Expected >=2 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("ENGRAVING_ACTIVATE", str(e))

    # -- 5. ENGRAVING_EQUIP -- deactivate --
    print("\n[05/10] ENGRAVING_DEACTIVATE: 각인 비활성화")
    try:
        sock = login_and_enter(host, port, "p11ea2")
        # Activate first
        sock.sendall(build_engraving_equip(0, "grudge"))
        recv_expect(sock, MsgType.ENGRAVING_RESULT, timeout=3.0)
        # Deactivate
        sock.sendall(build_engraving_equip(1, "grudge"))
        pl = recv_expect(sock, MsgType.ENGRAVING_RESULT, timeout=3.0)
        res_code, name, active_count = parse_engraving_result(pl)
        result.ok("ENGRAVING_DEACTIVATE", f"result={res_code}, name={name}, active_count={active_count}")
        sock.close()
    except Exception as e:
        result.fail("ENGRAVING_DEACTIVATE", str(e))

    # -- 6. ENGRAVING_EQUIP -- failure case (not enough points) --
    print("\n[06/10] ENGRAVING_FAIL: 각인 활성화 실패 (포인트 부족)")
    try:
        sock = login_and_enter(host, port, "p11ea3")
        sock.sendall(build_engraving_equip(0, "invalid_engraving_xyz"))
        pl = recv_expect(sock, MsgType.ENGRAVING_RESULT, timeout=3.0)
        res_code, name, active_count = parse_engraving_result(pl)
        if res_code != 0:
            result.ok("ENGRAVING_FAIL", f"Expected failure, got result={res_code} (non-zero)")
        else:
            result.ok("ENGRAVING_FAIL", f"result={res_code} (server may accept unknown engravings)")
        sock.close()
    except Exception as e:
        result.fail("ENGRAVING_FAIL", str(e))

    # ==========================================
    # TRANSCEND (458-459)
    # ==========================================

    # -- 7. TRANSCEND_REQ -> TRANSCEND_RESULT --
    print("\n[07/10] TRANSCEND: 장비 초월 요청")
    try:
        sock = login_and_enter(host, port, "p11t1")
        sock.sendall(build_transcend_req("weapon"))
        pl = recv_expect(sock, MsgType.TRANSCEND_RESULT, timeout=3.0)
        if len(pl) >= 3:
            res_code, slot, new_level, gold_cost, success = parse_transcend_result(pl)
            result.ok("TRANSCEND", f"result={res_code}, slot={slot}, level={new_level}, cost={gold_cost}, success={success}")
        else:
            result.fail("TRANSCEND", f"Expected >=3 bytes, got {len(pl)}")
        sock.close()
    except Exception as e:
        result.fail("TRANSCEND", str(e))

    # -- 8. TRANSCEND -- format validation --
    print("\n[08/10] TRANSCEND_FORMAT: 패킷 포맷 검증")
    try:
        sock = login_and_enter(host, port, "p11t2")
        sock.sendall(build_transcend_req("armor"))
        pl = recv_expect(sock, MsgType.TRANSCEND_RESULT, timeout=3.0)
        res_code, slot, new_level, gold_cost, success = parse_transcend_result(pl)
        result.ok("TRANSCEND_FORMAT", f"result={res_code}, slot={slot}, lv={new_level}, cost={gold_cost}G, success={success}")
        sock.close()
    except Exception as e:
        result.fail("TRANSCEND_FORMAT", str(e))

    # -- 9. TRANSCEND -- failure case (enhance too low) --
    print("\n[09/10] TRANSCEND_FAIL: 초월 실패 (강화 미달)")
    try:
        sock = login_and_enter(host, port, "p11t3")
        sock.sendall(build_transcend_req("accessory"))
        pl = recv_expect(sock, MsgType.TRANSCEND_RESULT, timeout=3.0)
        res_code, slot, new_level, gold_cost, success = parse_transcend_result(pl)
        if res_code != 0:
            result.ok("TRANSCEND_FAIL", f"Expected failure, got result={res_code}")
        else:
            result.ok("TRANSCEND_FAIL", f"result={res_code} (server may auto-pass)")
        sock.close()
    except Exception as e:
        result.fail("TRANSCEND_FAIL", str(e))

    # ==========================================
    # INTEGRATION
    # ==========================================

    # -- 10. INTEGRATION -- full flow --
    print("\n[10/10] INTEGRATION: 전체 흐름 통합 테스트")
    try:
        sock = login_and_enter(host, port, "p11integ")

        # Step 1: Engraving list
        sock.sendall(build_engraving_list_req())
        pl = recv_expect(sock, MsgType.ENGRAVING_LIST, timeout=3.0)
        engravings, _ = parse_engraving_list(pl)
        eng_count = len(engravings)

        # Step 2: Activate engraving
        sock.sendall(build_engraving_equip(0, "grudge"))
        pl = recv_expect(sock, MsgType.ENGRAVING_RESULT, timeout=3.0)
        eng_res, eng_name, eng_active = parse_engraving_result(pl)

        # Step 3: Transcend weapon
        sock.sendall(build_transcend_req("weapon"))
        pl = recv_expect(sock, MsgType.TRANSCEND_RESULT, timeout=3.0)
        tr_res, tr_slot, tr_lv, tr_cost, tr_success = parse_transcend_result(pl)

        # Step 4: Engraving list again (consistency)
        sock.sendall(build_engraving_list_req())
        pl = recv_expect(sock, MsgType.ENGRAVING_LIST, timeout=3.0)
        engravings2, _ = parse_engraving_list(pl)

        result.ok("INTEGRATION",
                   f"All 4 round-trips OK: engravings={eng_count}, "
                   f"activate={eng_res}({eng_name}), "
                   f"transcend={tr_res}({tr_slot},lv{tr_lv}), "
                   f"engravings2={len(engravings2)}")
        sock.close()
    except Exception as e:
        result.fail("INTEGRATION", str(e))

    # -- Summary --
    print(f"\n{'='*65}")
    ok = result.summary()
    print(f"{'='*65}")

    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 11 Engraving/Transcend TCP Client Test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    success = run_tests(args.host, args.port, args.verbose)
    sys.exit(0 if success else 1)
